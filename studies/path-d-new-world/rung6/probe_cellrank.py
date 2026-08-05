"""RUNG 6 -- rank EVERY bench cell as an exit-trigger candidate.

Do not assume a cell passes: run entrance._cell_openness_note (the kit's own screen) on the
DEPLOYED Terrain block for all 24 cells of the V-shore bench island, alongside the clean-grass
coverage, the largest all-clean disc that stays inside the cell, and the walk-route result from
the landing point. The screen's threshold (>20% blocked tris in the cell's +/-16 box) is a
stock-disc-1 calibration; on a ~90u ring island every cell touches shore, so the ranking is
what matters, not a pass/fail read of one cell.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(STUDY)); sys.path.insert(0, str(HERE))
sys.path.insert(0, str(STUDY.parent.parent / "ff9mapkit"))
import walk_sim as W                                          # noqa: E402
import probe_site as PS                                       # noqa: E402
import probe_finalize as PF                                   # noqa: E402
from ff9mapkit.world import entrance as E                     # noqa: E402
from ff9mapkit.world import extract as X                      # noqa: E402
from ff9mapkit.world import mesh as M                         # noqa: E402

LANDING = (425.0, -479.0)
BENCH = [(5, 7), (6, 7), (7, 7), (5, 8), (6, 8), (7, 8)]
_TER = {}


def ter_of(blk):
    if blk not in _TER:
        p = PF.DISC9 / f"r{blk[1]}" / f"Block[{blk[0]}][{blk[1]}] Terrain.ff9mesh"
        _TER[blk] = M.blockmesh_from_ff9mesh(p, disc=9, x=blk[0], y=blk[1], part="terrain")
    return _TER[blk]


def main():
    W.CELLS = BENCH
    world = W.load_world()
    clean, ground, topo_of, stacked, (x0, z0, nx, nz) = PS.build_map(world)

    def disc_ok(cx, cz, ccx, ccz, r):
        if not (cx * 32 <= ccx - r and ccx + r <= cx * 32 + 32):
            return False
        if not (-(cz * 32 + 32) <= ccz - r and ccz + r <= -(cz * 32)):
            return False
        for a in range(0, 360, 10):
            for rr in (r * 0.5, r):
                px, pz = ccx + rr * math.cos(math.radians(a)), ccz + rr * math.sin(math.radians(a))
                kk = (int(round((px - x0) / PS.GRID)), int(round((pz - z0) / PS.GRID)))
                if kk not in clean:
                    return False
        return True

    rows = []
    for cx in range(10, 16):
        for cz in range(14, 18):
            cwx, cwz = E.cell_world_center(cx, cz)
            blk = E.cell_to_block(cx, cz)
            if blk not in BENCH:
                continue
            ox, oz = X.block_world_origin(*blk)
            ter = ter_of(blk)
            walk = blocked = 0
            for tri in ter.tris:
                tcx = (ter.verts[tri[0]][0] + ter.verts[tri[1]][0] + ter.verts[tri[2]][0]) / 3.0 + ox
                tcz = (ter.verts[tri[0]][2] + ter.verts[tri[1]][2] + ter.verts[tri[2]][2]) / 3.0 + oz
                if abs(tcx - cwx) <= 16 and abs(tcz - cwz) <= 16:
                    if X.decode_id(int(round(ter.tangents[tri[0]][0])))["topograph"] in E._WALK_TOPO:
                        walk += 1
                    else:
                        blocked += 1
            tot = walk + blocked
            summary = {}
            E._cell_openness_note(ter, cwx, cwz, ox, oz, summary)
            n_clean = sum(1 for (i, j) in clean
                          if int((x0 + i * PS.GRID) // 32) == cx
                          and int(-(z0 + j * PS.GRID) // 32) == cz)
            best = (None, None, 0.0)
            for ccx in range(cx * 32 + 3, cx * 32 + 30):
                for ccz in range(-(cz * 32 + 32) + 3, -(cz * 32) - 2):
                    r = 0
                    while r < 16 and disc_ok(cx, cz, float(ccx), float(ccz), r + 1.0):
                        r += 1
                    if r > best[2]:
                        best = (float(ccx), float(ccz), float(r))
            d = math.hypot(cwx - LANDING[0], cwz - LANDING[1])
            route = None
            if best[0] is not None and best[2] >= 3:
                route = PS.walk_route(world, LANDING, (best[0], best[1]))
            rows.append(dict(cell=(cx, cz), blk=blk, centre=(cwx, cwz), tot=tot, walk=walk,
                             blocked=blocked,
                             pct=round(100 * blocked / max(1, tot), 1),
                             note=bool(summary.get("notes")), clean=n_clean, best=best,
                             d=round(d, 1),
                             route_ok=(route or {}).get("ok"),
                             route_steps=(route or {}).get("steps"),
                             route_why=(route or {}).get("why")))

    rows.sort(key=lambda r: (-r["best"][2], r["pct"]))
    print(f"{'cell':9s} {'blk':7s} {'centre':16s} {'blk%':>6s} {'note':>5s} {'clean':>6s} "
          f"{'discR':>6s} {'d(u)':>7s}  route")
    for r in rows:
        print(f"{str(r['cell']):9s} {str(r['blk']):7s} {str(r['centre']):16s} "
              f"{r['pct']:6.1f} {'POOR' if r['note'] else ' ok ':>5s} {r['clean']:6d} "
              f"{r['best'][2]:6.1f} {r['d']:7.1f}  "
              f"{'ARRIVED in ' + str(r['route_steps']) + ' steps' if r['route_ok'] else (r['route_why'] or '-')}"
              f"  @ {r['best'][0]},{r['best'][1]}")


if __name__ == "__main__":
    main()
