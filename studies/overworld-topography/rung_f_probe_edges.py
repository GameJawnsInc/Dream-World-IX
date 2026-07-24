"""RUNG F round-3 DIAGNOSTIC PROBE (read-only): characterize every once-edge of the STAGED composite
to decide the structural-vs-weldable question the round-2 record and the task disagree on.

For each single-owner (open) terrain edge above the sea skirt we record: midpoint XZ, min/max endpoint
height, distance from the ecotone centroid, and whether it lies on the CARRIED-WINDOW outer boundary
(the placed_R footprint perimeter -- closeable by a full apron weld) or elsewhere (true island coast /
genuine interior crack). Then we ask: if EVERY carried-window-boundary once-edge were welded closed,
what would R1 measure (ecotone -> nearest REMAINING once-edge)?
"""
from __future__ import annotations
import math, sys, json
from pathlib import Path
from collections import Counter, defaultdict

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

import contract_mass_gates as G
import seam_null_recon as SNR

STAGED = HERE / "out" / "rung_f" / "FF9CustomMap-world"
CELL = 4.0


def once_edges_3d(tris):
    """single-owner edges keyed by rounded xyz, returning both endpoints' full world pos."""
    ecnt = Counter(); esamp = {}
    for t in tris:
        w = t["w"]
        for q in range(3):
            a, b = w[q], w[(q + 1) % 3]
            ka = tuple(round(c, 3) for c in a); kb = tuple(round(c, 3) for c in b)
            if ka == kb:
                continue
            ek = tuple(sorted((ka, kb)))
            ecnt[ek] += 1; esamp[ek] = (a, b)
    return [esamp[ek] for ek, n in ecnt.items() if n == 1]


def main():
    cand = G.load_candidate("rungf_staged", STAGED, core_blocks=None)  # detect footprint from staged
    print("footprint (detected):", cand["core_blocks"])
    tris = cand["tris"]
    print("region tris:", len(tris))

    # ecotone points (the gate's own)
    boundary_pts = [G.cell_center(c) for c in cand["boundary_cells"]]
    straddle_pts = [G.cell_center(c) for c in cand["straddle_cells"]]
    lb_body, _ = G.label_blind_desert_body(cand["core_tris"])
    body_pts = [G.tri_centroid_xz(t) for (t, _c, _d) in lb_body]
    eco_pts = boundary_pts + straddle_pts + body_pts
    ecx = sum(p[0] for p in eco_pts) / len(eco_pts)
    ecz = sum(p[1] for p in eco_pts) / len(eco_pts)
    print(f"ecotone centroid XZ = ({ecx:.1f},{ecz:.1f}); n boundary={len(boundary_pts)} straddle={len(straddle_pts)} body={len(body_pts)}")

    # placed_R footprint (carried cells) from the staged tris: a tri is "carried" if its IDALL has a
    # desert/rock topo OR its cell is inside the ecotone footprint. Simpler: use the carried-window
    # boundary as the set of cells that are desert-family or topo-49 rock or topo-13/50/58 (carried).
    carried_topos = set(G.DESERT_TOPOS) | {41, 49, 13, 50, 58, 48, 51, 36, 37, 59, 45, 46}
    carried_cells = set()
    for t in cand["tris"]:
        if t["topo"] in carried_topos:
            carried_cells.add(t["cell"])
    # the carry footprint perimeter (XZ): cells adjacent to a non-carried cell
    def cell_center(c):
        return (c[0] * CELL + CELL / 2, c[1] * CELL + CELL / 2)
    perim_cells = {c for c in carried_cells
                   if any((c[0] + d[0], c[1] + d[1]) not in carried_cells for d in ((1,0),(-1,0),(0,1),(0,-1)))}
    perim_pts = [cell_center(c) for c in perim_cells]
    print(f"carried cells={len(carried_cells)} perimeter cells={len(perim_cells)}")

    oe = once_edges_3d(tris)
    oe = [e for e in oe if max(e[0][1], e[1][1]) > 0.5]   # above the sea skirt
    print(f"once-edges above skirt: {len(oe)}")

    # classify each once-edge: near the carried perimeter (XZ within ~1.5 cell) -> window-boundary
    def near_perim(mx, mz, reach=6.0):
        for (px, pz) in perim_pts:
            if abs(px - mx) <= reach and abs(pz - mz) <= reach:
                return True
        return False

    win_edges = []; other_edges = []
    for (a, b) in oe:
        mx = (a[0] + b[0]) / 2; mz = (a[2] + b[2]) / 2
        h = max(a[1], b[1])
        rec = (mx, mz, h, min(a[1], b[1]))
        (win_edges if near_perim(mx, mz) else other_edges).append(rec)

    def hist_h(recs):
        c = Counter()
        for (_, _, h, _) in recs:
            b = "0-2" if h < 2 else "2-6" if h < 6 else "6-12" if h < 12 else "12-25" if h < 25 else "25+"
            c[b] += 1
        return dict(c)
    print(f"WINDOW-boundary once-edges: {len(win_edges)}  height hist {hist_h(win_edges)}")
    print(f"OTHER once-edges: {len(other_edges)}  height hist {hist_h(other_edges)}")

    # distances from ecotone to each class of once-edge (segment distance, approx by midpoint)
    def min_d(recs):
        best = None
        for (mx, mz, _h, _) in recs:
            d = math.hypot(mx - ecx, mz - ecz)
            if best is None or d < best:
                best = d
        return best
    print(f"\necotone centroid -> nearest WINDOW once-edge: {min_d(win_edges):.2f}u")
    print(f"ecotone centroid -> nearest OTHER once-edge:  {min_d(other_edges):.2f}u" if other_edges else "no OTHER once-edges")

    # THE DECISIVE MEASUREMENT: R1 uses per-ecotone-point min-to-segment. Recompute the gate's R1 to
    # the OTHER-only silhouette (i.e., if every window-boundary once-edge were welded closed).
    segs_all = [((a[0], a[2]), (b[0], b[2])) for (a, b) in oe]
    # rebuild seg lists split by class using midpoint test again (cheap)
    win_seg = []; oth_seg = []
    for (a, b) in oe:
        mx = (a[0] + b[0]) / 2; mz = (a[2] + b[2]) / 2
        s = ((a[0], a[2]), (b[0], b[2]))
        (win_seg if near_perim(mx, mz) else oth_seg).append(s)
    def r1_to(segs, pts):
        return G._min_seg(pts, segs) if segs and pts else None
    print("\n--- R1 measured to ALL once-edges (current) ---")
    print(f"  boundary_cell {r1_to(segs_all, boundary_pts):.2f}  straddle {r1_to(segs_all, straddle_pts):.2f}  body {r1_to(segs_all, body_pts):.2f}")
    print("--- R1 measured to OTHER-only (window boundary welded closed) ---")
    for nm, pts in (("boundary_cell", boundary_pts), ("straddle", straddle_pts), ("body", body_pts)):
        v = r1_to(oth_seg, pts)
        print(f"  {nm}: {v:.2f}u" if v is not None else f"  {nm}: (no other edges)")
    print(f"\nFLOORS: boundary_cell {G.ceil('R1.boundary_cell_to_coast_floor_u')}  "
          f"straddle {G.ceil('R1.straddle_cell_to_coast_floor_u')}  body {G.ceil('R1.body_tri_to_coast_floor_u')}")


if __name__ == "__main__":
    main()
