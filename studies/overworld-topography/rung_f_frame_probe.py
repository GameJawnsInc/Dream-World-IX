"""RUNG F FRAME BUILD -- outer-ring feasibility probe (READ-ONLY).

Before widening the carry to the 4x4 window (blocks 12-15,10-13) that the round-2 frame design
approved, measure the ONE thing that decides whether the true-mesh weld is even feasible: the
HEIGHT + TOPO of the window's OUTER PERIMETER cells. OPTION (a) only works if the window's outer
boundary is LOWLAND (weldable to a minted flat-grass coast at land_height); if the enclosing rock
walls TOUCH the outer edge, the coast would have to weld to a 20-40u rock face (off-language, the
CARRIED_ROCK_HEIGHT_WELD risk becomes structural).

Also reports the window's land-cell footprint completeness (holes/ocean inside the 4x4 rect) and the
per-side outer-ring height profile.

Run: cd studies/overworld-topography && py rung_f_frame_probe.py
"""
from __future__ import annotations
import json, math, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

import seam_null_recon as SNR                         # noqa: E402
from ff9mapkit.world import extract as X             # noqa: E402

CELL = 4.0
BLOCK = 64.0
OUT = HERE / "out" / "rung_f" / "frame_probe.json"

ROCK_TOPOS = frozenset(t for t, f in SNR.FAM_OF.items() if f == "rock")
MASS_TOPOS = frozenset({16, 17, 19, 20, 41})

# the 4x4 window = blocks 12-15, 10-13 (the round-2 PRIMARY)
WIN_BLOCKS = [(bx, by) for bx in range(12, 16) for by in range(10, 14)]
# window cell rect
WIN_CELL_X = (192, 255)
WIN_CELL_Y = (-224, -161)


def log(m): print(m, flush=True)


def main():
    log("=" * 90); log("RUNG F FRAME BUILD -- 4x4 WINDOW OUTER-RING FEASIBILITY PROBE (read-only)"); log("=" * 90)
    # gather per-cell: dominant topo, mean height, tri count
    cell_topo = defaultdict(Counter)
    cell_ys = defaultdict(list)
    for (bx, by) in WIN_BLOCKS:
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except (ValueError, FileNotFoundError):
            continue
        ox, oz = X.block_world_origin(bx, by)
        for tri in bm.tris:
            topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
            cx = sum(bm.verts[j][0] + ox for j in tri) / 3.0
            cz = sum(bm.verts[j][2] + oz for j in tri) / 3.0
            y = sum(bm.verts[j][1] for j in tri) / 3.0
            cell = (math.floor(cx / CELL), math.floor(cz / CELL))
            if WIN_CELL_X[0] <= cell[0] <= WIN_CELL_X[1] and WIN_CELL_Y[0] <= cell[1] <= WIN_CELL_Y[1]:
                cell_topo[cell][topo] += 1
                cell_ys[cell].append(y)

    all_cells = set(cell_topo)
    nx = WIN_CELL_X[1] - WIN_CELL_X[0] + 1
    ny = WIN_CELL_Y[1] - WIN_CELL_Y[0] + 1
    total_slots = nx * ny
    log(f"window {nx}x{ny} = {total_slots} cell slots; land cells present: {len(all_cells)}; "
        f"holes/ocean inside rect: {total_slots - len(all_cells)}")

    def dom(c):
        tc = cell_topo.get(c)
        return tc.most_common(1)[0][0] if tc else None

    def meany(c):
        ys = cell_ys.get(c)
        return sum(ys) / len(ys) if ys else None

    # outer-ring cells = window cells on the rect perimeter (x==min/max OR y==min/max)
    ring = {}
    for cx in range(WIN_CELL_X[0], WIN_CELL_X[1] + 1):
        for cz in range(WIN_CELL_Y[0], WIN_CELL_Y[1] + 1):
            on_perim = (cx in WIN_CELL_X or cz in WIN_CELL_Y)
            if not on_perim:
                continue
            c = (cx, cz)
            ring[c] = dict(present=c in all_cells, topo=dom(c), y=meany(c))

    # per-side summary
    def side_cells(side):
        out = []
        for c, r in ring.items():
            cx, cz = c
            if side == "W" and cx == WIN_CELL_X[0]: out.append((c, r))
            if side == "E" and cx == WIN_CELL_X[1]: out.append((c, r))
            # z more-negative = south in this world (see basin_envelope), z-max(-161)=north
            if side == "N" and cz == WIN_CELL_Y[1]: out.append((c, r))
            if side == "S" and cz == WIN_CELL_Y[0]: out.append((c, r))
        return out

    sides = {}
    log("-" * 90); log("OUTER-RING per side (present / rock-frac / height p50 / height max):")
    for s in ("N", "S", "E", "W"):
        sc = side_cells(s)
        present = [r for (_c, r) in sc if r["present"]]
        n_present = len(present)
        n_rock = sum(1 for r in present if r["topo"] in ROCK_TOPOS)
        ys = sorted(r["y"] for r in present if r["y"] is not None)
        p50 = ys[len(ys) // 2] if ys else None
        ymax = max(ys) if ys else None
        n_high = sum(1 for r in present if r["y"] is not None and r["y"] > 8.0)
        sides[s] = dict(n_ring_cells=len(sc), n_present=n_present, n_ocean_gap=len(sc) - n_present,
                        n_rock=n_rock, rock_frac=round(n_rock / max(1, n_present), 2),
                        height_p50=round(p50, 2) if p50 is not None else None,
                        height_max=round(ymax, 2) if ymax is not None else None,
                        n_cells_over_8u=n_high)
        log(f"  {s}: ring={len(sc)} present={n_present} ocean_gap={len(sc)-n_present} "
            f"rock={n_rock}({sides[s]['rock_frac']*100:.0f}%) y_p50={sides[s]['height_p50']} "
            f"y_max={sides[s]['height_max']} cells>8u={n_high}")

    # overall outer-ring verdict: weldable iff every side is predominantly lowland (<8u) and low rock
    ring_present = [r for r in ring.values() if r["present"]]
    n_ring_high = sum(1 for r in ring_present if r["y"] is not None and r["y"] > 8.0)
    n_ring_rock = sum(1 for r in ring_present if r["topo"] in ROCK_TOPOS)
    log("-" * 90)
    log(f"OUTER RING TOTAL: present={len(ring_present)} rock={n_ring_rock} over_8u={n_ring_high} "
        f"ocean_gaps={sum(1 for r in ring.values() if not r['present'])}")

    # topo histogram of the whole window
    topo_hist = Counter()
    for c in all_cells:
        topo_hist[dom(c)] += 1
    fam_hist = Counter(str(SNR.FAM_OF.get(t)) for t in (dom(c) for c in all_cells))
    n_rock_win = sum(1 for c in all_cells if dom(c) in ROCK_TOPOS)
    n_mass_win = sum(1 for c in all_cells if dom(c) in MASS_TOPOS)
    log(f"WINDOW families: {dict(fam_hist)}")
    log(f"WINDOW rock cells: {n_rock_win}  mass(ecotone/desert/dunes) cells: {n_mass_win}")

    verdict = ("WELDABLE (outer ring lowland grass all round)" if n_ring_high == 0 and n_ring_rock < 10
               else "OUTER-RING ROCK/HEIGHT PRESENT -- weld to minted coast is off-language on those cells")
    log("-" * 90); log(f"VERDICT: {verdict}")

    res = dict(rung="F", step="frame build -- 4x4 window outer-ring feasibility (read-only)",
               window_blocks="12-15,10-13", cell_rect=dict(x=list(WIN_CELL_X), y=list(WIN_CELL_Y)),
               total_slots=total_slots, n_land_cells=len(all_cells),
               holes_inside_rect=total_slots - len(all_cells),
               outer_ring=dict(n_present=len(ring_present), n_rock=n_ring_rock, n_over_8u=n_ring_high,
                               n_ocean_gaps=sum(1 for r in ring.values() if not r["present"])),
               per_side=sides, window_family_hist=dict(fam_hist),
               window_topo_hist={str(k): v for k, v in topo_hist.most_common()},
               n_rock_cells=n_rock_win, n_mass_cells=n_mass_win, verdict=verdict)
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    log(f"-> {OUT}")
    return res


if __name__ == "__main__":
    main()
