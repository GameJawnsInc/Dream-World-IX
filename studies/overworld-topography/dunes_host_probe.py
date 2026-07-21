"""HOST-SITING PROBE for the real-scale comp[1] dunes stamp (rung 5).

Resolves the siting tension between the two design reports EMPIRICALLY on real bytes:
 - HOST CENSUS recommends center (608,-1376) r48 seed 11 (near the (8,19) desert islet) via a
   bbox-fit proxy (footprint 185 < int2 270).
 - STAMP DESIGN recommends center (1248,-1184) r52 seed 2 via the STRICTER footprint+ring+2-margin
   (= dilate3(footprint) subset of regular) test, and found r44/48 FAIL that margin.

This probe implements the strict test (dilate the footprint 3x, require it all land on clean 4u
regular desert cells) across a candidate ladder, preferring the census's coherent-archipelago
siting first, then the stamp site, at radii large enough to clear the 2-cell wall margin. It
prints the winning (center,radius,seed,dihedral,origin) for the full mint to consume. No writes.

Run from repo root:  py studies/overworld-topography/dunes_host_probe.py
"""
from __future__ import annotations

import math
import sys
from collections import defaultdict, deque
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit.world import island as I   # noqa: E402
from ff9mapkit.world import extract as X  # noqa: E402

import dunes_mint_eye as EYE              # noqa: E402  (one census; gives COMP1, strip_cells, judge)

BLOCK = 64.0
CELL_U = 4.0
NEI4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
GROUND = "desert"


def dilate(cells, exclude):
    nxt = set()
    for c in cells:
        for di, dj in NEI4:
            n = (c[0] + di, c[1] + dj)
            if n not in exclude:
                nxt.add(n)
    return nxt


def dilate_n(cells, n):
    """cells U n concentric 4-neighbour shells (footprint + n-cell margin)."""
    full = set(cells)
    frontier = set(cells)
    for _ in range(n):
        ring = dilate(frontier, full)
        full |= ring
        frontier = ring
    return full


# ---- comp[1] footprint (130 dunes cells), its enclosed hole, boundary, in WORLD frame ----------
COMP1 = EYE.COMP1
strip_cells = EYE.strip_cells


def enclosed_hole(cellset):
    """Non-cellset cells enclosed by cellset's outer boundary (flood 'outside' from a bbox-pad
    border through non-cellset cells; anything unreached and not in cellset is an enclosed hole)."""
    xs = [c[0] for c in cellset]; zs = [c[1] for c in cellset]
    x0, x1, z0, z1 = min(xs) - 1, max(xs) + 1, min(zs) - 1, max(zs) + 1
    outside = set()
    q = deque()
    for i in range(x0, x1 + 1):
        for seed in ((i, z0), (i, z1)):
            if seed not in cellset and seed not in outside:
                outside.add(seed); q.append(seed)
    for j in range(z0, z1 + 1):
        for seed in ((x0, j), (x1, j)):
            if seed not in cellset and seed not in outside:
                outside.add(seed); q.append(seed)
    while q:
        c = q.popleft()
        for di, dj in NEI4:
            n = (c[0] + di, c[1] + dj)
            if x0 <= n[0] <= x1 and z0 <= n[1] <= z1 and n not in cellset and n not in outside:
                outside.add(n); q.append(n)
    hole = set()
    for i in range(x0, x1 + 1):
        for j in range(z0, z1 + 1):
            c = (i, j)
            if c not in cellset and c not in outside:
                hole.add(c)
    return hole


HOLE = enclosed_hole(COMP1)
FOOTPRINT = COMP1 | HOLE                       # 130 + hole
BOUNDARY = {c for c in COMP1 if any((c[0]+di, c[1]+dj) not in COMP1 for di, dj in NEI4)}
OUTER = dilate(FOOTPRINT, FOOTPRINT)           # desert-side 1-cell ring
D3 = dilate_n(FOOTPRINT, 3)                     # footprint + ring + 2-cell wall margin

# what topo are the hole cells in stock? (expect all topo-59)
hole_fams = defaultdict(int)
for c in HOLE:
    fc = EYE.fams_at.get(c)
    hole_fams[fc.most_common(1)[0][0] if fc else None] += 1

print("=" * 90)
print(f"comp[1]: {len(COMP1)} dunes cells | hole {len(HOLE)} cells | footprint {len(FOOTPRINT)} | "
      f"boundary(dune-side) {len(BOUNDARY)} | outer-ring {len(OUTER)} | dilate3 {len(D3)}")
print(f"   hole cell families (stock): {dict(hole_fams)}")
bx0 = min(c[0] for c in FOOTPRINT); bz0 = min(c[1] for c in FOOTPRINT)
bw = max(c[0] for c in FOOTPRINT) - bx0 + 1; bh = max(c[1] for c in FOOTPRINT) - bz0 + 1
print(f"   footprint bbox {bw}x{bh} cells")
# verbatim strip rows present on comp[1]'s dune-side + desert-side (from map-wide census)
dune_side_rows = {c: strip_cells[c] for c in BOUNDARY if c in strip_cells}
desert_side_rows = {c: strip_cells[c] for c in OUTER if c in strip_cells}
print(f"   verbatim dune-side strip cells (in boundary) = {len(dune_side_rows)}, "
      f"desert-side strip cells (in outer ring) = {len(desert_side_rows)}")
print("=" * 90)


# ---- multi-block regular-cell gathering -------------------------------------------------------
def build_regular(center, radius, seed):
    """Build a desert host; return (built, {world_cell: (block, [tri_idx])}, regular_cell_set) or
    raise/return None on a non-open-ocean or build failure."""
    try:
        built = I.build_landmass(center=center, base_radius=radius, seed=seed, ground=GROUND,
                                 stamps=None, disc=1)
    except Exception as e:  # noqa: BLE001
        return None, f"build raised: {e}"
    occ = {blk: o for blk in built["blocks"] if (o := I._real_block_parts(blk, disc=1, game=None))}
    if occ:
        return None, f"not open ocean: {sorted(occ)}"
    mains = {}
    regular = set()
    for blk, bm in built["blocks"].items():
        bx, by = blk
        wp = [(v[0] + BLOCK * bx, v[1], v[2] - BLOCK * by) for v in bm.verts]
        tris = np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3)
        cellt = defaultdict(list)
        for ti, tri in enumerate(tris):
            topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
            if topo != 17:
                continue
            cx = sum(wp[j][0] for j in tri) / 3.0
            cz = sum(wp[j][2] for j in tri) / 3.0
            cellt[(math.floor(cx / CELL_U), math.floor(cz / CELL_U))].append(ti)
        for cell, tl in cellt.items():
            mains[cell] = (blk, tl)
            ci, cj = cell
            ok = True
            for ti in tl:
                for j in tris[ti]:
                    fx = (wp[j][0] - CELL_U * ci) / CELL_U
                    fz = (wp[j][2] - CELL_U * cj) / CELL_U
                    if min(abs(fx), abs(fx - 1)) > 0.02 or min(abs(fz), abs(fz - 1)) > 0.02:
                        ok = False
                        break
                if not ok:
                    break
            if ok:
                regular.add(cell)
    return dict(built=built, mains=mains, regular=regular, blocks=sorted(built["blocks"])), None


def search(regular, host_center, *, need_margin=True):
    """Find the placement: dihedral k + translation putting dilate3(footprint) (or just
    footprint+ring if need_margin=False) entirely on regular cells. Prefer k=0, then nearest-center.
    Returns list of (score, k, oi, oj) sorted best-first."""
    if not regular:
        return []
    xs = sorted({c[0] for c in regular}); zs = sorted({c[1] for c in regular})
    fp_norm = {(c[0] - bx0, c[1] - bz0) for c in FOOTPRINT}
    cand = []
    for k in range(8):
        pts = [EYE_dihedral(i, j, k) for (i, j) in fp_norm]
        ti0 = min(p[0] for p in pts); tj0 = min(p[1] for p in pts)
        fpn = {(p[0] - ti0, p[1] - tj0) for p in pts}
        w = max(p[0] for p in fpn) + 1; h = max(p[1] for p in fpn) + 1
        for oi in range(xs[0] - 3, xs[-1] - w + 4):
            for oj in range(zs[0] - 3, zs[-1] - h + 4):
                fp = {(oi + a, oj + b) for (a, b) in fpn}
                if not fp <= regular:
                    continue
                test = dilate_n(fp, 3) if need_margin else dilate(fp, fp) | fp
                if not test <= regular:
                    continue
                wx = CELL_U * (oi + w / 2.0); wz = CELL_U * (oj + h / 2.0)
                d = math.hypot(wx - host_center[0], wz - host_center[1])
                cand.append((round(d, 3), k, oi, oj))
    # prefer k=0 (identity) among near-best, else nearest center
    cand.sort(key=lambda c: (0 if c[1] == 0 else 1, c[0], c[1], c[2], c[3]))
    return cand


def EYE_dihedral(i, j, k):
    if k >= 4:
        i = -i
    r = k % 4
    return (i, j) if r == 0 else (-j, i) if r == 1 else (-i, -j) if r == 2 else (j, -i)


# candidate ladder: census siting FIRST (near the (8,19) islet), at radii clearing the 2-margin;
# then the stamp-design verified site; a couple of census alternates.
def blk_center(bx, by):
    return (BLOCK * bx + BLOCK / 2.0, -(BLOCK * by + BLOCK / 2.0))


CANDIDATES = [
    ("census (9,21) r52 s11", (608.0, -1376.0), 52.0, 11.0),
    ("census (9,21) r56 s11", (608.0, -1376.0), 56.0, 11.0),
    ("census (9,21) r52 s2", (608.0, -1376.0), 52.0, 2.0),
    ("census (9,21) r56 s2", (608.0, -1376.0), 56.0, 2.0),
    ("stamp (19,18) r52 s2", (1248.0, -1184.0), 52.0, 2.0),
    ("stamp (19,18) r56 s2", (1248.0, -1184.0), 56.0, 2.0),
    ("census-alt (10,22) r52 s11", blk_center(10, 22), 52.0, 11.0),
    ("census-alt (8,22) r52 s11", blk_center(8, 22), 52.0, 11.0),
    ("census-alt (13,21) r52 s2", blk_center(13, 21), 52.0, 2.0),
    ("census-alt (15,20) r52 s2", blk_center(15, 20), 52.0, 2.0),
]

print("\nCANDIDATE LADDER (strict: dilate3(footprint) subset of regular = footprint+ring+2-margin)\n")
winners = []
for label, center, radius, seed in CANDIDATES:
    host, err = build_regular(center, radius, seed)
    if host is None:
        print(f"  [{label}] REJECT -- {err}")
        continue
    cand_strict = search(host["regular"], center, need_margin=True)
    cand_loose = search(host["regular"], center, need_margin=False)
    tag = ""
    if cand_strict:
        d, k, oi, oj = cand_strict[0]
        tag = f"STRICT OK k={k} origin=({oi},{oj}) d={d:.1f}u ({len(cand_strict)} placements)"
        winners.append((label, center, radius, seed, k, oi, oj, len(host["regular"]), host["blocks"]))
    elif cand_loose:
        d, k, oi, oj = cand_loose[0]
        tag = f"loose-only (footprint+ring, NO 2-margin) k={k} d={d:.1f}u -- 2-margin FAILS"
    else:
        tag = "NO placement (footprint+ring doesn't fit)"
    print(f"  [{label}] blocks={host['blocks']} regular={len(host['regular'])} -> {tag}")

print("\n" + "=" * 90)
if winners:
    label, center, radius, seed, k, oi, oj, nreg, blocks = winners[0]
    print(f"WINNER (first strict pass, census-siting-preferred): {label}")
    print(f"  center={center} radius={radius} seed={seed} dihedral={k} origin=({oi},{oj})")
    print(f"  regular_cells={nreg} blocks={blocks}")
else:
    print("NO strict winner in the ladder -- widen radius or revisit siting.")
print("=" * 90)
