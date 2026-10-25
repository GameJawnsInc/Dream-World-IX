"""reads_soup: what CarryTool._read_soup costs (the island soup every carry card reads on open, after each Accept,
undo, redo, rescan), split into its parts, and two prototypes compared against the unpatched code on real data:

  FAST   -- mesh.blockmesh_from_ff9mesh decoded with numpy (frombuffer -> float64 -> tolist) instead of a
            struct.unpack_from per vertex; identity: the BlockMesh dicts, the soup dicts and every SoupIndex array ==.
  INCR   -- a per-file memo keyed by the file's BYTES (sha1 of the content: the same bytes always parse the same),
            plus a per-block soup fragment memo, concatenated with base offsets; identity: == against a cold read of
            the same draft after a block file changed.

Run:  py studies/overworld-editor/perf/reads_soup.py
Writes out/perf/reads/reads_soup.json and reads_soup.pstats. Reads the install READ ONLY (the draft is a copy)."""
from __future__ import annotations

import cProfile
import hashlib
import pstats
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reads_common import GAME, OUT, dump, lane_draft, stat, timeit  # noqa: E402

import numpy as np  # noqa: E402

from ff9mapkit.world import extract as X  # noqa: E402
from ff9mapkit.world import forestedit as FE  # noqa: E402
from ff9mapkit.world import interior as IN  # noqa: E402
from ff9mapkit.world import mesh as M  # noqa: E402
from ff9mapkit.world import mountainedit as ME  # noqa: E402
from ff9mapkit.workspace import worldforest as WF  # noqa: E402


class _Card:                                   # just what CarryTool._read_soup touches: the real method runs on it
    FE = FE

    def _game_fn(self):
        return GAME


def card_read(folder, seam):
    return WF.CarryTool._read_soup(_Card(), folder, seam=seam)


def ix_equal(a, b):
    for k in ("pos", "tris", "corner", "cent", "grass", "coast", "lo", "hi"):
        x, y = getattr(a, k), getattr(b, k)
        if x.shape != y.shape or x.dtype != y.dtype or not np.array_equal(x, y):
            return f"{k} differs"
    if a.what != b.what or a._meta != b._meta or a.blocks != b.blocks:
        return "what/meta/blocks differ"
    return None


# ------------------------------------------------------------------ prototype FAST: numpy decode, same floats
_orig_bfm = M.blockmesh_from_ff9mesh


def fast_blockmesh_from_ff9mesh(path, *, disc, x, y, lod="0_1", part="terrain", data=None):
    from ff9mapkit.world.extract import BlockMesh, CH_POS, CH_NRM, CH_UV, CH_TAN
    data = Path(path).read_bytes() if data is None else data
    if data[:4] != M.MAGIC:
        raise ValueError("not a .ff9mesh (bad magic)")
    version, vcount, icount, flags = np.frombuffer(data, "<i4", 4, 4).tolist()
    if version != M.VERSION:
        raise ValueError(f"unsupported .ff9mesh version {version}")
    off = 20

    def take(dim):
        nonlocal off
        a = np.frombuffer(data, "<f4", vcount * dim, off).astype(np.float64).reshape(vcount, dim).tolist()
        off += vcount * dim * 4
        return a
    chan = {CH_POS: take(3)}
    channels = {CH_POS: (0, 3)}
    if flags & 1:
        chan[CH_NRM] = take(3)
        channels[CH_NRM] = (12, 3)
    if flags & 2:
        chan[CH_UV] = take(2)
        channels[CH_UV] = (24, 2)
    if flags & 4:
        chan[CH_TAN] = take(4)
        channels[CH_TAN] = (32, 4)
    ia = np.frombuffer(data, "<i4", icount, off)
    idx = ia.tolist()
    n3 = (icount // 3) * 3 if icount >= 3 else 0
    tris = ia[:n3].reshape(-1, 3).tolist()
    return BlockMesh(name=f"Block[{x}][{y}] {part.capitalize()}", disc=disc, x=x, y=y, lod=lod, vcount=vcount,
                     stride=48, channels=channels, chan_arrays=chan, flat_index=idx, tris=tris,
                     raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


# ------------------------------------------------------------------ prototype INCR: memo by the file's bytes
class SoupMemo:
    """Per-file parse memo + per-(unwrapped block) soup-fragment memo, keyed by the file's content digest."""

    def __init__(self, decode=None):
        self.parse = {}                         # (path, digest) -> BlockMesh
        self.frag = {}                          # (bx, by, digest) -> fragment
        self.decode = decode
        self.hits = self.misses = 0

    def blocks(self, folder, near, reach, game):
        rtarget = 1
        root = Path(folder) / "FF9_Data" / "WorldMap" / f"Disc{rtarget}" / "0_1"
        wx, wz = near
        import math
        bx0, bx1 = int(math.floor((wx - reach) / IN.BLOCK)), int(math.floor((wx + reach) / IN.BLOCK))
        by0, by1 = int(math.floor(-(wz + reach) / IN.BLOCK)), int(math.floor(-(wz - reach) / IN.BLOCK))
        out = {}
        for bx in range(bx0, bx1 + 1):
            wbx = M.wrap_block_col(bx)
            for by in range(by0, by1 + 1):
                p = root / f"r{by}" / f"Block[{wbx}][{by}] Terrain.ff9mesh"
                try:
                    data = p.read_bytes()
                except OSError:
                    continue
                dg = hashlib.sha1(data).digest()
                out[(bx, by)] = (p, dg, data)
        return out

    def soup(self, folder, seam):
        (near, reach) = WF.SEAM_MAP if seam else WF.WHOLE_MAP
        files = self.blocks(folder, near, reach, GAME)
        if not files:
            raise IN.CarveRefused("footprint", "no deployed Terrain overrides", [near])
        lo, hi = IN.G.FAM_REGION["main"][0], IN.G.FAM_REGION["main"][2]
        pos, nrm, tan, tris, meta, coast = [], [], [], [], [], []
        blocks = {}
        for blk in sorted(files):
            p, dg, data = files[blk]
            bx, by = blk
            bm = self.parse.get((str(p), dg))
            if bm is None:
                self.misses += 1
                bm = (self.decode or (lambda pp, **k: _orig_bfm(pp, **k)))(p, disc=1, x=bx, y=by, lod="0_1",
                                                                       part="terrain")
                self.parse[(str(p), dg)] = bm
            else:
                self.hits += 1
            # NOTE the key/identity of a seam-side BlockMesh is the UNWRAPPED bx (read_deployed_blocks' contract)
            if bm.x != bx:
                import dataclasses
                bm = dataclasses.replace(bm, x=bx, name=f"Block[{bx}][{by}] Terrain")
            blocks[blk] = bm
            fk = (bx, by, dg)
            fr = self.frag.get(fk)
            if fr is None:
                fr = _fragment(bm, bx, by, lo, hi)
                self.frag[fk] = fr
            base = len(pos)
            fp, fn, ft, ftris, fmeta, fcoast = fr
            pos.extend(fp)
            nrm.extend(fn)
            tan.extend(ft)
            tris.extend([[a + base, b + base, c + base] for a, b, c in ftris])
            meta.extend(fmeta)
            coast.extend(fcoast)
        soup = {"pos": pos, "nrm": nrm, "tan": tan, "tris": tris, "meta": meta, "blocks": dict(blocks),
                "coast": coast}
        return FE.SoupIndex(soup), soup


def _fragment(bm, bx, by, lo, hi):
    """soup_from_blocks' body for ONE block, with base 0 (verbatim arithmetic)."""
    BLOCK = IN.BLOCK
    pos, nrm, tan, tris, meta, coast = [], [], [], [], [], []
    ps = bm.chan_arrays[X.CH_POS]
    ns = bm.chan_arrays[X.CH_NRM]
    us = bm.chan_arrays[X.CH_UV]
    ts = bm.chan_arrays[X.CH_TAN]
    for k in range(bm.vcount):
        v = ps[k]
        pos.append([v[0] + BLOCK * bx, v[1], v[2] - BLOCK * (by + 1) + BLOCK])
        nrm.append(list(ns[k]))
        tan.append(list(ts[k]))
    for tri in bm.tris:
        idall = float(ts[tri[0]][0])
        topo = X.decode_id(int(round(idall)))["topograph"]
        if topo == 37:
            fam = "forest"
        elif topo == 58:
            fam = "rock"
            for i in tri:
                w = pos[i]
                coast.append((w[0], w[2]))
        elif topo != 0:
            fam = f"topo{topo}"
        else:
            fam = "main" if all(lo - 0.02 <= us[i][0] <= hi + 0.02 for i in tri) else "stamp"
        tris.append([tri[0], tri[1], tri[2]])
        meta.append(((bx, by), idall, fam, [(us[i][0], us[i][1]) for i in tri]))
    return pos, nrm, tan, tris, meta, coast


def main():
    draft = lane_draft()
    res = {"draft": str(draft), "python": sys.version, "notes": "wall = time.perf_counter; min is the headline "
           "(three other lanes share the 12-core machine)"}
    root = draft / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
    terr = sorted(root.rglob("*Terrain.ff9mesh"))
    res["terrain_files"] = len(terr)
    res["terrain_bytes"] = sum(p.stat().st_size for p in terr)

    # --- parts, warm OS cache (one untimed warm-up) ---
    (near, reach) = WF.WHOLE_MAP
    ts, blocks = timeit(lambda: IN.read_deployed_blocks(str(draft), near=near, reach=reach, game=GAME), 5, 1)
    res["read_deployed_blocks_east"] = stat(ts)
    res["blocks_east"] = len(blocks)
    res["verts_east"] = sum(b.vcount for b in blocks.values())
    res["tris_east"] = sum(len(b.tris) for b in blocks.values())
    ts, soup = timeit(lambda: IN.soup_from_blocks(blocks), 5, 0)
    res["soup_from_blocks_east"] = stat(ts)
    ts, ix = timeit(lambda: FE.SoupIndex(soup), 5, 0)
    res["SoupIndex_east"] = stat(ts)
    # just the parse vs the probes
    ts, _ = timeit(lambda: [M.read_ff9mesh(p) for p in terr], 5, 0)
    res["read_ff9mesh_all_terrain"] = stat(ts)
    ts, _ = timeit(lambda: [p.exists() for bx in range(24) for by in range(-2, 22)
                            for p in [root / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"]], 5, 0)
    res["exists_probes_576"] = stat(ts)

    # --- the card's own method, both frames (what an open / an island_changed costs on the worker) ---
    ts, ix_e = timeit(lambda: card_read(draft, False), 5, 1)
    res["card_read_soup_east"] = stat(ts)
    ts, ix_s = timeit(lambda: card_read(draft, True), 5, 1)
    res["card_read_soup_seam"] = stat(ts)
    # the mountain card's first ground() after a read lands: _massif_arrays builds per-tri arrays (GUI thread)
    def massif():
        ix_e._mtn = None
        return ME._massif_arrays(ix_e)
    ts, _ = timeit(massif, 5, 0)
    res["mountain_massif_arrays_first_call_gui"] = stat(ts)

    # --- cProfile one east read for shares ---
    pr = cProfile.Profile()
    pr.enable()
    card_read(draft, False)
    pr.disable()
    pr.dump_stats(str(OUT / "reads_soup.pstats"))
    st = pstats.Stats(pr)
    st.sort_stats("cumulative")
    import io
    buf = io.StringIO()
    st.stream = buf
    st.print_stats(18)
    res["pstats_top"] = buf.getvalue().splitlines()[:45]

    # --- prototype FAST (numpy decode) vs unpatched, identity on real data ---
    M.blockmesh_from_ff9mesh = fast_blockmesh_from_ff9mesh
    try:
        ts, blocks_f = timeit(lambda: IN.read_deployed_blocks(str(draft), near=near, reach=reach, game=GAME), 5, 1)
        res["FAST_read_deployed_blocks_east"] = stat(ts)
        ts, ixf_e = timeit(lambda: card_read(draft, False), 5, 0)
        res["FAST_card_read_soup_east"] = stat(ts)
        ixf_s = card_read(draft, True)
    finally:
        M.blockmesh_from_ff9mesh = _orig_bfm
    res["FAST_identity_blocks"] = blocks_f == blocks
    res["FAST_identity_soup"] = IN.soup_from_blocks(blocks_f) == soup
    res["FAST_identity_ix_east"] = ix_equal(ixf_e, ix_e) or "identical"
    res["FAST_identity_ix_seam"] = ix_equal(ixf_s, ix_s) or "identical"

    # --- prototype INCR: first read cold memo, repeat with nothing changed, repeat after ONE block changed ---
    memo = SoupMemo()
    ts, (ixm, soupm) = timeit(lambda: memo.soup(draft, False), 1, 0)
    res["INCR_first_read_east"] = stat(ts)
    res["INCR_identity_first"] = (ix_equal(ixm, ix_e) or "identical", soupm == soup)
    ts, (ixm2, _s) = timeit(lambda: memo.soup(draft, False), 5, 0)
    res["INCR_repeat_unchanged_east"] = stat(ts)
    ts, (ixm2s, _s) = timeit(lambda: memo.soup(draft, True), 1, 0)
    res["INCR_seam_after_east_memo"] = stat(ts)
    res["INCR_identity_seam"] = ix_equal(ixm2s, ix_s) or "identical"
    ts, _ = timeit(lambda: memo.soup(draft, True), 5, 0)
    res["INCR_repeat_unchanged_seam"] = stat(ts)
    # change ONE block in the lane's draft (its bytes become another block's: still a valid mesh), then compare
    # the memo's read against the unpatched card read of the changed draft
    a, b = terr[0], terr[1]
    keep = b.read_bytes()
    try:
        shutil.copyfile(a, b)
        t0 = time.perf_counter()
        ixc, _s = memo.soup(draft, False)
        res["INCR_after_one_block_changed_east_s"] = round(time.perf_counter() - t0, 4)
        ref = card_read(draft, False)
        res["INCR_identity_after_change"] = ix_equal(ixc, ref) or "identical"
        res["INCR_changed_block"] = str(b.relative_to(draft))
        res["INCR_hits_misses"] = (memo.hits, memo.misses)
    finally:
        b.write_bytes(keep)
    after = card_read(draft, False)
    res["draft_restored_identity"] = ix_equal(after, ix_e) or "identical"

    # FAST + INCR together: the changed-block read decodes one file with numpy
    memo2 = SoupMemo(decode=fast_blockmesh_from_ff9mesh)
    memo2.soup(draft, False)
    ts, (ixb, _s) = timeit(lambda: memo2.soup(draft, False), 5, 0)
    res["FAST_INCR_repeat_unchanged_east"] = stat(ts)
    res["FAST_INCR_identity"] = ix_equal(ixb, ix_e) or "identical"
    dump("reads_soup.json", res)
    for k, v in res.items():
        if k != "pstats_top":
            print(k, v)
    print("\n".join(res["pstats_top"]))


if __name__ == "__main__":
    main()
