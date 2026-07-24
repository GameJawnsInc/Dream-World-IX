"""RUNG F DROP PROBE -- measure the tri-level DROP topology BEFORE building.

Loads the 6-block ecotone core, applies the tri-level DROP filter, and measures:
  - fully-dropped vs partially-dropped cells (partial cells leave within-cell holes)
  - internal once-edges of the KEPT soup (edges owned by exactly one KEPT tri that are NOT on the
    outer window perimeter) -- these are the DROP-boundary rim the fill must weld
  - the kept-set height envelope (must be lowland)
READ-ONLY. Writes out/rung_f/drop_probe.json.
"""
import sys, io, contextlib, math, json
from pathlib import Path
from collections import defaultdict, Counter
sys.path.insert(0, '../../ff9mapkit'); sys.path.insert(0, '.')
import contract_mass_gates as G

HERE = Path(__file__).resolve().parent
CELL = 4.0; BLOCK = 64.0
DROP = {49, 50, 58, 7, 62, 45, 46, 36, 37, 27, 28, 48, 51, 10, 59}


def main():
    core = [(x, y) for x in (13, 14, 15) for y in (11, 12)]
    with contextlib.redirect_stdout(io.StringIO()):
        cand = G.load_candidate('stock', None, core_blocks=core)
    all_tris = cand['core_tris']
    kept = [t for t in all_tris if t['topo'] not in DROP]
    drop = [t for t in all_tris if t['topo'] in DROP]
    print(f"core tris: {len(all_tris)}  kept: {len(kept)}  dropped: {len(drop)}")

    # cell -> kept/dropped tri counts
    cell_kept = Counter(t['cell'] for t in kept)
    cell_drop = Counter(t['cell'] for t in drop)
    kept_cells = set(cell_kept)
    fully_dropped = set(cell_drop) - kept_cells      # cells with ONLY dropped tris -> grass frame fills
    partial = {c for c in kept_cells if cell_drop.get(c, 0) > 0}  # kept + some dropped -> within-cell hole
    print(f"kept cells: {len(kept_cells)}  fully-dropped cells (grass-fills): {len(fully_dropped)}  "
          f"partial cells (within-cell hole): {len(partial)}")

    # height envelope of the KEPT soup
    ys = [v[1] for t in kept for v in t['w']]
    ys.sort()

    def pct(p):
        return round(ys[min(len(ys) - 1, int(p / 100 * len(ys)))], 2)
    print(f"kept height: min {ys[0]:.2f} p50 {pct(50)} p90 {pct(90)} p99 {pct(99)} max {ys[-1]:.2f}")

    # edge census over KEPT tris (world XZ rounded). classify once-edges as outer-window-perimeter vs
    # internal (drop-boundary). window perimeter = an edge on the 6-block outer rect boundary
    # (world x in {832,1024} or z in {-832,-704}). Actually the ecotone window outer rect:
    wx0, wx1 = 832.0, 1024.0    # blocks 13..15 => x[832,1024]
    wz0, wz1 = -832.0, -704.0   # blocks 11..12 => z[-832,-704]

    def on_window_perim(a, b):
        for coord, lo, hi in (((a[0], b[0]), wx0, wx1),):
            pass
        # an edge lies on the window perimeter if both endpoints share an extreme x or z
        for lohi in (wx0, wx1):
            if abs(a[0] - lohi) < 0.1 and abs(b[0] - lohi) < 0.1:
                return True
        for lohi in (wz0, wz1):
            if abs(a[2] - lohi) < 0.1 and abs(b[2] - lohi) < 0.1:
                return True
        return False

    ecnt = Counter()
    esample = {}
    for t in kept:
        w = t['w']
        for q in range(3):
            a, b = w[q], w[(q + 1) % 3]
            ka = (round(a[0], 3), round(a[1], 3), round(a[2], 3))
            kb = (round(b[0], 3), round(b[1], 3), round(b[2], 3))
            if ka == kb:
                continue
            ek = tuple(sorted((ka, kb)))
            ecnt[ek] += 1
            esample[ek] = (a, b)
    once = [ek for ek, n in ecnt.items() if n == 1]
    outer = 0; internal = 0; internal_heights = []
    for ek in once:
        a, b = esample[ek]
        if on_window_perim(a, b):
            outer += 1
        else:
            internal += 1
            internal_heights.append(max(a[1], b[1]))
    internal_heights.sort()
    print(f"once-edges: {len(once)}  outer-window-perimeter: {outer}  internal(drop-boundary): {internal}")
    if internal_heights:
        print(f"  internal once-edge heights: min {internal_heights[0]:.2f} "
              f"p50 {internal_heights[len(internal_heights)//2]:.2f} max {internal_heights[-1]:.2f}")

    out = dict(core_tris=len(all_tris), kept_tris=len(kept), dropped_tris=len(drop),
               kept_cells=len(kept_cells), fully_dropped_cells=len(fully_dropped),
               partial_cells=len(partial), kept_h_p50=pct(50), kept_h_p99=pct(99), kept_h_max=ys[-1],
               once_edges=len(once), outer_perim_once=outer, internal_drop_once=internal,
               internal_once_h_max=(internal_heights[-1] if internal_heights else 0),
               partial_cell_list=sorted(list(partial))[:60])
    (HERE / "out" / "rung_f" / "drop_probe.json").write_text(json.dumps(out, indent=1))
    print("wrote out/rung_f/drop_probe.json")


if __name__ == "__main__":
    main()
