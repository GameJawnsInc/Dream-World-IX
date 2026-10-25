"""gui lane, prototype: the FIRST 3D view of a session (a cold process: UnityPy env, mesh index, every decode).

    py studies/overworld-editor/perf/gui_proto_cold.py [runs]

Each timed run is a FRESH child process (`--child <variant>`) timing its first load_scene of the game's stack (what the
first "3D view" click waits for behind "Loading the map..."), with the legs split by pass-through wrappers. Variants:
  shipped  the package as it is
  fast     three prototypes, monkeypatched in the child (nothing in the package changes):
           F1 extract._find_block_part by a dict of every container stem's slash-suffixes (setdefault in _mesh_index
              order = the first match the linear _is_block_part_container scan returns), not 2199 string tests a call
           F2 extract._decode_world_mesh's vertex channels by numpy (frombuffer '<f4' -> .tolist(): the same doubles
              struct.unpack gives), every other line as shipped
           F3 the view's own reads skip extract._copy_blockmesh (render only reads a stock part: np.asarray copies)
Identity, in one process: (1) every stock part the map reads, decoded shipped vs F2 -> BlockMesh fields ==
(chan_arrays, tris, flat_index, channels, raw bytes ...); (2) the whole Packed + textures of load_scene shipped vs fast,
byte for byte.
Evidence: out/perf/gui/gui_proto_cold.json.
"""
from __future__ import annotations

import json
import os
import struct
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gui_common as C                                                # noqa: E402


def site():
    from ff9mapkit.world import mesh as M
    from ff9mapkit.world import render as R
    cells = tuple((bx, by) for by in range(M.GRID_ROWS) for bx in range(M.GRID_COLS))
    return R.RenderSite(cells=cells, disc=1, game=C.GAME, stack=R.game_stack(C.GAME))


def install_fast():
    from ff9mapkit.world import extract as X
    from ff9mapkit.world import render as R
    import numpy as np
    orig = {"find": X._find_block_part, "decode": X._decode_world_mesh, "read_block": X.read_block}

    def suffix_index(env):                                            # F1
        idx = getattr(env, "_gui_suffix_index", None)
        if idx is None:
            idx = {}
            for c, o in X._mesh_index(env).items():
                head, slash, base = c.rpartition("/")
                dot = base.rfind(".")
                if dot >= 0:
                    base = base[:dot]
                stem = head + slash + base
                idx.setdefault(stem, o)                               # stem == target
                parts = stem.split("/")
                for k in range(1, len(parts)):                        # stem.endswith("/" + target)
                    idx.setdefault("/".join(parts[k:]), o)
            env._gui_suffix_index = idx
        return idx

    def find_block_part(env, disc, lod, x, y, part):
        return suffix_index(env).get(X._block_part_target(disc, lod, x, y, part))

    def decode(mesh_pptr, *, disc, x, y, lod):                        # F2: shipped, but the channels by numpy
        md = mesh_pptr.read()
        vd = md.m_VertexData
        raw = bytes(vd.m_DataSize)
        vcount = int(vd.m_VertexCount)
        if not raw:
            raise ValueError(f"block[{x}][{y}] terrain: vertex data is streamed (m_DataSize empty) -- "
                             f"streamed-mesh decode not implemented yet")
        chans = vd.m_Channels
        channels, stride = {}, 0
        for ci, c in enumerate(chans):
            if c.dimension:
                channels[ci] = (int(c.offset), int(c.dimension))
                stride = max(stride, int(c.offset) + int(c.dimension) * 4)
        if vcount * stride != len(raw):
            raise ValueError(f"block[{x}][{y}] vertex stride mismatch (v{vcount} * s{stride} != {len(raw)})")
        if stride % 4 == 0 and all(off % 4 == 0 for off, _d in channels.values()):
            f = np.frombuffer(raw, dtype="<f4").reshape(vcount, stride // 4)
            chan_arrays = {ci: f[:, off // 4: off // 4 + dim].tolist() for ci, (off, dim) in channels.items()}
        else:                                                         # (never on disc 1: the shipped loop)
            def rd(ci, vi):
                off, dim = channels[ci]
                return list(struct.unpack_from("<%df" % dim, raw, vi * stride + off))
            chan_arrays = {ci: [rd(ci, i) for i in range(vcount)] for ci in channels}
        ib = bytes(md.m_IndexBuffer)
        use32 = getattr(md, "m_IndexFormat", None) == 1 or getattr(md, "m_Use16BitIndices", 1) in (0, False)
        ent = 4 if use32 else 2
        flat = list(struct.unpack("<%d%s" % (len(ib) // ent, "I" if use32 else "H"), ib))
        submeshes = [(int(s.firstByte), int(s.indexCount)) for s in md.m_SubMeshes]
        tris = [[flat[i], flat[i + 1], flat[i + 2]] for i in range(0, len(flat) - 2, 3)]
        return X.BlockMesh(name=md.m_Name, disc=disc, x=x, y=y, lod=lod, vcount=vcount, stride=stride,
                           channels=channels, chan_arrays=chan_arrays, flat_index=flat, tris=tris,
                           raw_vbuf=raw, raw_ibuf=ib, use32=use32, submeshes=submeshes)

    def read_master(x, y, *, disc=1, lod="0_1", part="terrain", game=None):   # F3: the memo's master, no copy
        env = X._worldmap_env(disc, game)
        key = (disc, lod, x, y, part)
        from ff9mapkit.extract import env_lock
        with env_lock:
            memo = X._block_memo(env)
            master = memo.get(key)
            if master is None:
                o = X._find_block_part(env, disc, lod, x, y, part)
                if o is None:
                    target = X._block_part_target(disc, lod, x, y, part)
                    raise ValueError(f"disc{disc} block[{x}][{y}] {part} mesh not found (looked for container "
                                     f"{target!r})")
                master = X._decode_world_mesh(o, disc=disc, x=x, y=y, lod=lod)
                memo[key] = master
                while len(memo) > X._BLOCK_MEMO_MAX:
                    memo.popitem(last=False)
            else:
                memo.move_to_end(key)
            return master

    class _XView:                                                     # render's X, read_block swapped (render only)
        def __getattr__(self, k):
            return read_master if k == "read_block" else getattr(X, k)

    X._find_block_part, X._decode_world_mesh = find_block_part, decode
    R.X = _XView()
    return orig


def child(variant):
    from ff9mapkit.workspace import worldview3d as V
    from ff9mapkit.world import extract as X
    from ff9mapkit.world import render as R
    if variant == "fast":
        install_fast()
    legs = {}

    def wrapx(name):
        orig = getattr(X, name)

        def w(*a, **k):
            t = time.perf_counter()
            try:
                return orig(*a, **k)
            finally:
                legs[name] = legs.get(name, 0.0) + time.perf_counter() - t
        setattr(X, name, w)
    for n in ("_worldmap_env", "_find_block_part", "_decode_world_mesh", "_copy_blockmesh"):
        wrapx(n)
    s = site()
    t = time.perf_counter()
    V.load_scene(s)
    total = time.perf_counter() - t
    print("RESULT", json.dumps({"variant": variant, "first_load_s": round(total, 3),
                                **{k: round(v, 3) for k, v in legs.items()}}))


def identity():
    from ff9mapkit.workspace import worldview3d as V
    from ff9mapkit.world import extract as X
    from gui_proto_reload import same_packed, same_tex
    s = site()
    read = set()
    rb = X.read_block

    def rec(x, y, *, disc=1, lod="0_1", part="terrain", game=None):
        read.add((disc, lod, x, y, part))
        return rb(x, y, disc=disc, lod=lod, part=part, game=game)
    X.read_block = rec                                                # render looks X.read_block up per call
    p0, t0 = V.load_scene(s)
    X.read_block = rb
    env = X._worldmap_env(1, C.GAME)
    shipped_decode = X._decode_world_mesh
    orig = install_fast()
    fast_decode = X._decode_world_mesh
    n = same = found_same = 0
    for (disc, lod, x, y, part) in sorted(read):                     # every stock part the map read
        o = orig["find"](env, disc, lod, x, y, part)
        found_same += int(X._find_block_part(env, disc, lod, x, y, part) is o)     # F1 == the linear scan
        if o is None:
            continue
        a = shipped_decode(o, disc=disc, x=x, y=y, lod=lod)
        b = fast_decode(o, disc=disc, x=x, y=y, lod=lod)
        n += 1
        same += int(a == b)
    if hasattr(env, "_ff9mapkit_block_memo"):                         # a cold memo: the fast load decodes it all
        delattr(env, "_ff9mapkit_block_memo")
    p1, t1 = V.load_scene(s)
    return {"stock_parts_read": len(read), "find_same_object": found_same, "decoded": n, "blockmesh_equal": same,
            "packed_identical": same_packed(p0, p1), "textures_identical": same_tex(t0, t1)}


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--child":
        child(sys.argv[2])
        return
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    env = dict(os.environ)
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    env["PYTHONPYCACHEPREFIX"] = sys.pycache_prefix
    out = {"runs": {}}
    for variant in ("shipped", "fast"):
        res = []
        for _ in range(runs):
            r = subprocess.run([sys.executable, __file__, "--child", variant], capture_output=True, text=True,
                               env=env, cwd=str(C.KIT), timeout=600)
            line = next((ln for ln in r.stdout.splitlines() if ln.startswith("RESULT ")), None)
            assert line, r.stdout[-2000:] + r.stderr[-3000:]
            res.append(json.loads(line[7:]))
            print(res[-1])
        out["runs"][variant] = res
        out[variant] = C.stats([x["first_load_s"] for x in res])
    out["identity"] = identity()
    print(out["identity"])
    C.dump("gui_proto_cold.json", out)


if __name__ == "__main__":
    main()
