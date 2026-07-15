"""THE DESERT BEACH ANATOMY -- does stock FF9 have sand shorelines on non-grass ground?

The ground-families arc closed with desert/snow/canyon island-class mints whose only
coast is the cliff ring. The beach-mint (coastmorph.beach_mint, rungs 1-3) is a GRASS
vocabulary: THE BERM LAW measured beach berms as topo-0 in 664/702 map-wide L-chain
welds. This study asks what the OTHER 38 are, and whether any stock beach ever backs
onto the desert/dirt family -- i.e. whether "a desert beach" has stock precedent or
must be composed.

  A. All beach1 blocks: the topo histogram of Terrain tris near the foam ribbon
     (which topos make up a beach assembly: sand apron, berm, transitions).
  B. Per block: the BACK-GROUND family -- the first walkable non-sand/non-sea topo
     landward of the sand band; the map-wide histogram of beach-backing families.
  C. The sand apron itself: which topo ids, which atlas region (is sand one universal
     tile set, or does it vary by the flanking family/region?).
  D. Regional split: beach blocks on desert-family coasts (Outer/Forgotten) vs grass
     coasts -- if NO beach ever meets dirt-family ground, the desert beach is a
     composition (sand assembly + a chosen sand->desert seam), not a translation.

Artifacts -> out/desert_beach.json. Run from the repo root:
    py studies/overworld-topography/desert_beach_anatomy.py
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402

BLOCK = 64.0
OUTD = Path(__file__).with_name("out")
out = {}

# ---- A. find every beach1 block ----------------------------------------------------------------
beach_blocks = []
for bx in range(24):
    for by in range(20):
        try:
            X.read_block(bx, by, disc=1, part="beach1")
            beach_blocks.append((bx, by))
        except ValueError:
            continue
print(f"A. beach1 blocks: {len(beach_blocks)}: {beach_blocks}")
out["beach_blocks"] = [f"{b[0]},{b[1]}" for b in beach_blocks]

SAND_TOPOS = {30, 31, 32, 33}
SEA_TOPOS = {48, 50, 51, 53, 54, 55, 56, 57, 61}
LIP_CLIFF = {58, 49, 7, 62}

back_hist = Counter()                                       # back-ground topo -> weld count
back_by_block = {}
sand_uv_by_topo = defaultdict(list)
sand_topo_hist = Counter()

for (bx, by) in beach_blocks:
    fb = X.read_block(bx, by, disc=1, part="beach1")
    foam_pts = [(v[0] + BLOCK * bx, v[2] - BLOCK * by) for v in fb.verts]
    fp = np.array(foam_pts)
    bm = X.read_block(bx, by, disc=1, part="terrain")
    tris = np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3)

    # terrain tris near the foam ribbon (the beach assembly)
    near = []
    for tri in tris:
        topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
        ws = [(bm.verts[j][0] + BLOCK * bx, bm.verts[j][1],
               bm.verts[j][2] - BLOCK * by) for j in tri]
        cx = sum(p[0] for p in ws) / 3
        cz = sum(p[2] for p in ws) / 3
        d2 = ((fp[:, 0] - cx) ** 2 + (fp[:, 1] - cz) ** 2).min()
        if d2 < 12.0 ** 2:
            near.append((tri, topo, ws))
        if topo in SAND_TOPOS:
            sand_topo_hist[topo] += 1
            for j in tri:
                sand_uv_by_topo[topo].append((float(bm.uvs[j][0]), float(bm.uvs[j][1])))

    # the back-ground: walkable non-sand/non-sea topos edge-welded to sand tris
    kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))
    edge_owner = defaultdict(list)
    for idx, (tri, topo, ws) in enumerate(near):
        ps = [kk(w) for w in ws]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge_owner[tuple(sorted((ps[a], ps[b])))].append(idx)
    backs = Counter()
    for e, owners in edge_owner.items():
        tp = {near[i][1] for i in owners}
        if tp & SAND_TOPOS:
            for q in tp - SAND_TOPOS - SEA_TOPOS - LIP_CLIFF:
                backs[q] += 1
    if backs:
        back_by_block[(bx, by)] = dict(backs)
        back_hist.update(backs)

print(f"\nB. beach BACK-GROUND welds map-wide (sand tile <-> walkable ground):")
for topo, n in back_hist.most_common():
    print(f"   topo {topo:2d}: {n} welds")
print("   per block (non-grass backs only):")
for blk, bs in sorted(back_by_block.items()):
    ng = {t: n for t, n in bs.items() if t != 0}
    if ng:
        print(f"     {blk}: {ng}")
out["back_hist"] = {str(t): n for t, n in back_hist.most_common()}
out["back_by_block"] = {f"{b[0]},{b[1]}": bs for b, bs in back_by_block.items()}

# ---- C. the sand apron's own vocabulary ---------------------------------------------------------
print(f"\nC. sand-apron topo histogram (all beach blocks): {dict(sand_topo_hist)}")
for topo, uvs in sorted(sand_uv_by_topo.items()):
    ua = np.array([u for u, v in uvs])
    va = np.array([v for u, v in uvs])
    print(f"   topo {topo}: {len(uvs)} corners, u [{ua.min():.4f},{ua.max():.4f}] "
          f"v [{va.min():.4f},{va.max():.4f}]")
    out[f"sand_uv_{topo}"] = dict(u=[round(float(ua.min()), 4), round(float(ua.max()), 4)],
                                  v=[round(float(va.min()), 4), round(float(va.max()), 4)],
                                  corners=len(uvs))
out["sand_topos"] = {str(t): n for t, n in sand_topo_hist.items()}

# ---- D. do the shore-sand topos exist AWAY from beach1 blocks (desert coasts)? ------------------
sand_elsewhere = Counter()
sand_elsewhere_blocks = defaultdict(Counter)
for bx in range(24):
    for by in range(20):
        if (bx, by) in beach_blocks:
            continue
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except ValueError:
            continue
        for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
            topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
            if topo in SAND_TOPOS:
                sand_elsewhere[topo] += 1
                sand_elsewhere_blocks[(bx, by)][topo] += 1
print(f"\nD. sand topos OUTSIDE beach1 blocks: {dict(sand_elsewhere)}")
for blk, c in sorted(sand_elsewhere_blocks.items()):
    print(f"   {blk}: {dict(c)}")
out["sand_outside_beach"] = {f"{b[0]},{b[1]}": {str(t): n for t, n in c.items()}
                             for b, c in sand_elsewhere_blocks.items()}

OUTD.mkdir(exist_ok=True)
(OUTD / "desert_beach.json").write_text(json.dumps(out, indent=1, default=str))
print(f"\n-> {OUTD / 'desert_beach.json'}")
