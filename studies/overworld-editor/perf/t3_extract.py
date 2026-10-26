"""Tier 3 re-measure + identity for the cold first 3D view (PERF.md 5, C6): extract's part lookup and vertex decode
as shipped against the code before them.

    py studies/overworld-editor/perf/t3_extract.py identity      every mesh of discs 1 and 4, old vs new
    py studies/overworld-editor/perf/t3_extract.py cold N        the first load_scene of N fresh processes per arm
    (child) py studies/overworld-editor/perf/t3_extract.py child <old|new>

identity: for every Mesh object of both discs' worldmap bundles, the OLD _decode_world_mesh (extract.py of OLD_REV,
          exec'd beside the package) and the NEW one -> every BlockMesh field ==, and every float's bit pattern; and
          for every block container, OLD _find_block_part (the walk) is NEW (the suffix index) -- the same object.
cold:     fresh children alternating OLD (extract.py of OLD_REV in sys.modules before anything imports it) and NEW,
          each timing its first worldview3d.load_scene of the whole map as the World tab draws it.
Evidence: out/perf/t3/t3_extract_<mode>.json
"""
from __future__ import annotations

import json
import re
import statistics
import struct
import subprocess
import sys
import time
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import jobs_common as J                                               # noqa: E402  (pins the worktree package)

OUT = HERE.parent / "out" / "perf" / "t3"
OLD_REV = "43876935"                                                  # extract.py before the lookup + decode


def old_extract(register=False):
    rel = "ff9mapkit/ff9mapkit/world/extract.py"
    src = subprocess.run(["git", "show", f"{OLD_REV}:{rel}"], cwd=str(J.KIT.parent), capture_output=True, text=True,
                         encoding="utf-8", check=True).stdout
    name = "ff9mapkit.world.extract" if register else "ff9mapkit.world._old_extract"
    mod = types.ModuleType(name)
    mod.__file__ = str(J.KIT.parent / rel)
    mod.__package__ = "ff9mapkit.world"
    sys.modules[name] = mod
    if register:
        import ff9mapkit.world as W
        W.extract = mod
    exec(compile(src, mod.__file__, "exec"), mod.__dict__)
    return mod


def bits(v):
    return [struct.pack("<d", x) for x in v]


def identity():
    from ff9mapkit.extract import env_lock
    from ff9mapkit.world import extract as NEW
    OLD = old_extract()
    pat = re.compile(r"worldmap/disc(\d+)/([0-9_]+)/r(\d+)/block\[(\d+)\]\[(\d+)\] ([a-z0-9_]+)\.asset$")
    out = {}
    for disc in (1, 4):
        env = NEW._worldmap_env(disc, game=J.GAME)
        with env_lock:
            idx = NEW._mesh_index(env)
            meshes = same = looked = found = 0
            t_old = t_new = 0.0
            for c, o in idx.items():
                m = pat.search(c)
                if m and int(m.group(1)) == disc:
                    d, lod, _r, x, y, part = m.groups()
                    looked += 1
                    found += OLD._find_block_part(env, int(d), lod, int(x), int(y), part) is \
                        NEW._find_block_part(env, int(d), lod, int(x), int(y), part)
                kw = dict(disc=disc, x=0, y=0, lod="0_1")
                t = time.perf_counter()
                a = OLD._decode_world_mesh(o, **kw)
                t_old += time.perf_counter() - t
                t = time.perf_counter()
                b = NEW._decode_world_mesh(o, **kw)
                t_new += time.perf_counter() - t
                meshes += 1
                ok = (a.name, a.vcount, a.stride, a.channels, a.flat_index, a.tris, a.raw_vbuf, a.raw_ibuf, a.use32,
                      a.submeshes) == (b.name, b.vcount, b.stride, b.channels, b.flat_index, b.tris, b.raw_vbuf,
                                       b.raw_ibuf, b.use32, b.submeshes)
                ok = ok and set(a.chan_arrays) == set(b.chan_arrays) and all(
                    len(a.chan_arrays[ci]) == len(b.chan_arrays[ci]) and
                    all(bits(u) == bits(w) for u, w in zip(a.chan_arrays[ci], b.chan_arrays[ci]))
                    for ci in a.chan_arrays)
                same += ok
        out[disc] = {"meshes": meshes, "decode_identical": same, "lookups": looked, "lookup_same_object": found,
                     "decode_old_s": round(t_old, 3), "decode_new_s": round(t_new, 3)}
        print(disc, out[disc], flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "t3_extract_identity.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


def child(arm):
    if arm == "old":
        old_extract(register=True)
    from ff9mapkit.workspace import worldview3d as V
    from ff9mapkit.world import mesh as M
    from ff9mapkit.world import render as R
    cells = tuple((bx, by) for by in range(M.GRID_ROWS) for bx in range(M.GRID_COLS))
    site = R.RenderSite(cells=cells, disc=1, game=J.GAME, stack=R.game_stack(J.GAME))
    t = time.perf_counter()
    packed, _tex = V.load_scene(site)
    print(json.dumps({"first_load_s": round(time.perf_counter() - t, 3), "tris": packed.tris,
                      "digest": __import__("hashlib").sha256(b"".join(packed.arrays[p].tobytes()
                                                                       for p in sorted(packed.arrays))).hexdigest()}))


def cold(n):
    from jobs_wall import job_env
    got = {"old": [], "new": []}
    digests = set()
    for i in range(n):
        for arm in (("old", "new") if i % 2 == 0 else ("new", "old")):
            p = subprocess.run([sys.executable, str(Path(__file__).resolve()), "child", arm], cwd=str(J.kit_cwd()),
                               env=job_env(), capture_output=True, text=True, check=True)
            r = json.loads(p.stdout.strip().splitlines()[-1])
            got[arm].append(r["first_load_s"])
            digests.add(r["digest"])
            print(arm, r, flush=True)
    out = {"first_load_s": got, "min": {a: min(v) for a, v in got.items()},
           "median": {a: statistics.median(v) for a, v in got.items()}, "packed_identical": len(digests) == 1}
    print(json.dumps(out))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "t3_extract_cold.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "identity":
        identity()
    elif mode == "cold":
        cold(int(sys.argv[2]) if len(sys.argv) > 2 else 3)
    elif mode == "child":
        child(sys.argv[2])
