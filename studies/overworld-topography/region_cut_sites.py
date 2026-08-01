"""REGION-CARRY CUT SITES — where can the (15,14) mesa's region be cut so the only
minted junction is a COAST?

The eliminate-the-class lens: instead of welding carried donor ground to bench grass
(the junction class that has failed 8 rounds), carry a whole donor REGION and terminate
it at a coast. A coast is a junction class with proven machinery (world-coast /
coastmorph / island.landmass ring) and a first-deploy success record.

For that to be lawful the cut line must lie where stock's own coast vocabulary lives:
lowland GRASS or SAND. Two measured laws forbid the alternative:
  * THE FREE-BASE LAW (coast-mosaic D): topo-58 is coastal-only, cliff bases terminate
    free at/below the waterline; ZERO cliff-face base edges map-wide land on walkable
    terrain.
  * THE INTERIOR WALL != THE COASTAL STRIP (plateau_edge): 0 of 76 interior wall
    components touch the coastal rock strip.
So a cut through interior topo-49 rock mints an object stock never builds (an interior
50-degree battered wall running into open sea). A cut through forest is equally
unattested (topo-37 borders only grass map-wide).

This instrument therefore measures, for every candidate carried region around the mesa:
  FREE  = boundary slots whose outside is real stock SEA  -> zero mint
  LAWFUL= boundary slots to be minted through lowland grass/sand -> proven coast machinery
  FORBID= boundary slots to be minted through rock / plateau / forest / town(59)
plus the carried payload (blocks, object parts, landmarks, water parts, rivers).

READ-ONLY against stock disc-1. Writes only out/region_cut_sites.json + .png.
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
from ff9mapkit.world import extract as X  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)

BLOCK = 64.0
CELL = 4.0
DISC = 1

# donor + a generous window around it
DONOR = (15, 14)
WIN_X = range(11, 20)
WIN_Y = range(10, 19)

GRASS = {0, 1, 2, 3, 42}
PLATEAU = {10, 11, 12}
SHELF = {13}
FOREST = {36, 37}
ROCK = {49, 7, 62}
LIP = {58}
SAND = {31, 32, 33}
DESERT = {16, 17, 18, 19, 20, 21, 22, 23, 41}
TOWN = {59}
WATERTOPO = {48, 50, 51}

WATER_PARTS = ("sea1", "sea2", "sea3", "sea4", "sea5", "beach1", "beach2")


def cls_of(topo: int) -> str:
    if topo in GRASS:
        return "grass"
    if topo in SAND:
        return "sand"
    if topo in PLATEAU:
        return "plateau"
    if topo in SHELF:
        return "shelf"
    if topo in FOREST:
        return "forest"
    if topo in ROCK:
        return "rock"
    if topo in LIP:
        return "lip"
    if topo in DESERT:
        return "desert"
    if topo in TOWN:
        return "town"
    if topo in WATERTOPO:
        return "riverwater"
    return f"other{topo}"


def tri_cells(bm, ox, oz):
    """yield (cell_x, cell_z, topo, ymin, ymax, area_plan) per triangle, cell by centroid"""
    V = bm.chan_arrays[X.CH_POS]
    T = bm.chan_arrays[X.CH_TAN]
    fi = bm.flat_index
    for t in range(len(fi) // 3):
        i0, i1, i2 = fi[3 * t], fi[3 * t + 1], fi[3 * t + 2]
        a, b, c = V[i0], V[i1], V[i2]
        cx = (a[0] + b[0] + c[0]) / 3.0 + ox
        cz = (a[2] + b[2] + c[2]) / 3.0 + oz
        try:
            topo = X.decode_id(int(round(T[i0][0])))["topograph"]
        except Exception:
            topo = -1
        ys = (a[1], b[1], c[1])
        ar = abs((b[0] - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (b[2] - a[2])) / 2.0
        yield int(math.floor(cx / CELL)), int(math.floor(cz / CELL)), topo, min(ys), max(ys), ar


def main():
    # ---------- read the window ----------
    land = {}           # (gx,gz) -> dict(classes Counter, ymin, ymax, block)
    water = set()       # cells covered by any sea/beach part
    blockinfo = {}
    read_ok, read_fail = [], []
    for bx in WIN_X:
        for by in WIN_Y:
            ox, oz = BLOCK * bx, -BLOCK * by
            try:
                bm = X.read_block(bx, by, disc=DISC, part="terrain")
            except Exception:
                read_fail.append([bx, by])
                continue
            read_ok.append([bx, by])
            parts = ["terrain"]
            for pname in ("object", "river", "riverjoint", "falls", "stream") + WATER_PARTS:
                try:
                    X.read_block(bx, by, disc=DISC, part=pname)
                except Exception:
                    continue
                parts.append(pname)
            blockinfo[(bx, by)] = {"parts": parts}
            for gx, gz, topo, y0, y1, ar in tri_cells(bm, ox, oz):
                rec = land.get((gx, gz))
                if rec is None:
                    rec = land[(gx, gz)] = {"cls": Counter(), "ymin": 1e9, "ymax": -1e9,
                                            "block": (bx, by)}
                rec["cls"][cls_of(topo)] += ar
                rec["ymin"] = min(rec["ymin"], y0)
                rec["ymax"] = max(rec["ymax"], y1)
            # water parts
            for pname in WATER_PARTS:
                try:
                    wm = X.read_block(bx, by, disc=DISC, part=pname)
                except Exception:
                    continue
                for gx, gz, _t, _y0, _y1, _a in tri_cells(wm, ox, oz):
                    water.add((gx, gz))

    for k, rec in land.items():
        rec["dom"] = rec["cls"].most_common(1)[0][0]

    # a cell is SEA if it has no terrain at all, or its terrain is only lip/water and it
    # is covered by a sea part sitting at y 0
    def is_sea(cell):
        if cell in land:
            return False
        return True

    # ---------- the mesa ----------
    # rock cells of the donor block that belong to the mesa: use the donor block's rock
    bx, by = DONOR
    mesa_cells = [c for c, r in land.items()
                  if r["block"] == DONOR and r["dom"] in ("rock", "plateau")]
    mxs = [c[0] * CELL + 2 for c in mesa_cells]
    mzs = [c[1] * CELL + 2 for c in mesa_cells]
    mesa_pts = np.array(list(zip(mxs, mzs)), float)
    mesa_set = set(mesa_cells)

    def dist_to_mesa(cell):
        p = np.array([cell[0] * CELL + 2, cell[1] * CELL + 2], float)
        return float(np.min(np.hypot(mesa_pts[:, 0] - p[0], mesa_pts[:, 1] - p[1])))

    # ---------- candidate regions: land-connected flood from the mesa, capped at R ----
    # 4-connected over land cells only
    results = []
    for R in (16, 24, 32, 40, 48, 64, 80, 96, 112, 128, 160, 200):
        seen = set(mesa_set)
        dq = deque(mesa_set)
        while dq:
            c = dq.popleft()
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (c[0] + d[0], c[1] + d[1])
                if n in seen or n not in land:
                    continue
                if dist_to_mesa(n) > R:
                    continue
                seen.add(n)
                dq.append(n)
        # boundary slots
        free = 0
        mint = Counter()
        mint_y = defaultdict(list)
        for c in seen:
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (c[0] + d[0], c[1] + d[1])
                if n in seen:
                    continue
                if is_sea(n):
                    free += 1
                else:
                    # must be minted; class of the INSIDE cell (what the coast cuts through)
                    r = land[c]
                    k = r["dom"]
                    # a lowland grass/sand cell is the lawful coast substrate
                    mint[k] += 1
                    mint_y[k].append(r["ymax"])
        blocks = sorted({land[c]["block"] for c in seen})
        objs = [b for b in blocks if "object" in blockinfo.get(b, {}).get("parts", [])]
        rivers = [b for b in blocks if any(p in blockinfo.get(b, {}).get("parts", [])
                                          for p in ("river", "riverjoint", "falls", "stream"))]
        lawful = sum(v for k, v in mint.items() if k in ("grass", "sand"))
        lawful_low = 0
        for k in ("grass", "sand"):
            lawful_low += sum(1 for y in mint_y[k] if y <= 8.0)
        forbid = sum(v for k, v in mint.items() if k in ("rock", "plateau", "shelf",
                                                         "forest", "town", "lip", "desert"))
        results.append({
            "R": R,
            "cells": len(seen),
            "plan_area_u2": len(seen) * CELL * CELL,
            "blocks": len(blocks),
            "block_list": [list(b) for b in blocks],
            "object_blocks": [list(b) for b in objs],
            "river_blocks": [list(b) for b in rivers],
            "free_coast_slots": free,
            "free_coast_u": free * CELL,
            "mint_slots": int(sum(mint.values())),
            "mint_u": float(sum(mint.values()) * CELL),
            "mint_by_class": dict(mint),
            "mint_lawful_grass_sand": lawful,
            "mint_lawful_lowland_le8u": lawful_low,
            "mint_forbidden": forbid,
            "forbidden_frac": (forbid / max(1, sum(mint.values()))),
        })

    # ---------- rect variants, boundary decomposed the same way ----------
    rects = [(15, 14, 15, 14), (15, 14, 15, 15), (15, 14, 15, 16), (15, 14, 16, 15),
             (14, 14, 16, 16), (15, 13, 16, 16), (14, 13, 16, 16), (13, 13, 17, 17)]
    rect_out = []
    for (x0, y0, x1, y1) in rects:
        inside = {c for c, r in land.items()
                  if x0 <= r["block"][0] <= x1 and y0 <= r["block"][1] <= y1}
        free = 0
        mint = Counter()
        for c in inside:
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (c[0] + d[0], c[1] + d[1])
                if n in inside:
                    continue
                if is_sea(n):
                    free += 1
                else:
                    mint[land[c]["dom"]] += 1
        blocks = sorted({land[c]["block"] for c in inside})
        objs = [b for b in blocks if "object" in blockinfo.get(b, {}).get("parts", [])]
        forbid = sum(v for k, v in mint.items() if k not in ("grass", "sand"))
        rect_out.append({
            "rect": [x0, y0, x1, y1], "land_blocks": len(blocks), "cells": len(inside),
            "free_coast_slots": free, "free_coast_u": free * CELL,
            "mint_slots": int(sum(mint.values())), "mint_u": float(sum(mint.values()) * CELL),
            "mint_by_class": dict(mint), "mint_forbidden": forbid,
            "forbidden_frac": forbid / max(1, sum(mint.values())),
            "object_blocks": [list(b) for b in objs],
        })

    # ---------- the mesa's own border continuation, by class ----------
    # for each of the donor block's 4 borders, what class sits in the cells immediately
    # outside, and how high
    borders = {}
    for name, d in (("N", (0, 1)), ("S", (0, -1)), ("W", (-1, 0)), ("E", (1, 0))):
        # note: gz grows with -z; N = smaller |z|? use world: N = +z direction = gz+1
        pass
    bx, by = DONOR
    gx0 = int(bx * BLOCK / CELL)
    gz1 = int(-by * BLOCK / CELL)          # top edge (z = -64*by)
    gz0 = gz1 - 16
    for name, cells in (
        ("N_outside", [(gx0 + i, gz1) for i in range(16)]),
        ("S_outside", [(gx0 + i, gz0 - 1) for i in range(16)]),
        ("W_outside", [(gx0 - 1, gz0 + j) for j in range(16)]),
        ("E_outside", [(gx0 + 16, gz0 + j) for j in range(16)]),
    ):
        cc = Counter()
        ys = []
        for c in cells:
            if c in land:
                cc[land[c]["dom"]] += 1
                ys.append(land[c]["ymax"])
            else:
                cc["SEA"] += 1
        borders[name] = {"class": dict(cc),
                         "ymax_med": float(np.median(ys)) if ys else None,
                         "ymax_max": float(max(ys)) if ys else None}

    # ---------- the (9,5) alternative island, same decomposition ----------
    alt = {}
    alt_cells = {c for c, r in land.items()}
    # read the alt island separately
    alt_land = {}
    for (abx, aby) in [(9, 6), (9, 7), (10, 5), (10, 6), (10, 7)]:
        try:
            bm = X.read_block(abx, aby, disc=DISC, part="terrain")
        except Exception:
            continue
        ox, oz = BLOCK * abx, -BLOCK * aby
        for gx, gz, topo, y0, y1, ar in tri_cells(bm, ox, oz):
            rec = alt_land.setdefault((gx, gz), {"cls": Counter(), "ymin": 1e9, "ymax": -1e9})
            rec["cls"][cls_of(topo)] += ar
            rec["ymin"] = min(rec["ymin"], y0)
            rec["ymax"] = max(rec["ymax"], y1)
    aclass = Counter()
    for r in alt_land.values():
        aclass[r["cls"].most_common(1)[0][0]] += 1
    alt = {"cells": len(alt_land), "class_hist": dict(aclass),
           "grass_cells": aclass.get("grass", 0) + aclass.get("sand", 0)}

    payload = {
        "instrument": "studies/overworld-topography/region_cut_sites.py",
        "read_ok_blocks": len(read_ok), "read_fail_blocks": read_fail,
        "window": [min(WIN_X), min(WIN_Y), max(WIN_X), max(WIN_Y)],
        "cells_land": len(land),
        "mesa_cells": len(mesa_cells),
        "flood_regions": results,
        "rect_regions": rect_out,
        "donor_block_border_outside": borders,
        "alt_island_9_5": alt,
        "notes": [
            "SEA = a 4u cell with no terrain triangle centroid in this window; "
            "coarse (4u) and window-limited.",
            "mint_by_class keys are the INSIDE cell's dominant topograph class -- the "
            "substrate a minted coast would have to be cut through.",
            "FORBIDDEN = rock/plateau/shelf/forest/town/lip/desert, by THE FREE-BASE LAW "
            "and THE INTERIOR WALL != THE COASTAL STRIP.",
        ],
    }
    (OUT / "region_cut_sites.json").write_text(json.dumps(payload, indent=1))

    # ---------- print ----------
    print(f"read {len(read_ok)} blocks, {len(land)} land cells, mesa {len(mesa_cells)} cells")
    print("\nDONOR BLOCK BORDERS -- what sits immediately outside (16 cells each):")
    for k, v in borders.items():
        print(f"  {k:11s} {v['class']}  ymax med {v['ymax_med']} max {v['ymax_max']}")
    print("\nFLOOD REGIONS (land-connected from the mesa, capped at radius R):")
    print(f"{'R':>4} {'cells':>6} {'blks':>4} {'freeSea_u':>9} {'mint_u':>7} "
          f"{'forbid':>6} {'ffrac':>6}  mint_by_class")
    for r in results:
        print(f"{r['R']:>4} {r['cells']:>6} {r['blocks']:>4} {r['free_coast_u']:>9.0f} "
              f"{r['mint_u']:>7.0f} {r['mint_forbidden']:>6} {r['forbidden_frac']:>6.3f}  "
              f"{r['mint_by_class']}")
        print(f"      objects {r['object_blocks']} rivers {r['river_blocks']}")
    print("\nRECT REGIONS:")
    for r in rect_out:
        print(f"  {r['rect']} blks {r['land_blocks']:>2} freeSea {r['free_coast_u']:>6.0f}u "
              f"mint {r['mint_u']:>6.0f}u forbid {r['mint_forbidden']:>4} "
              f"({r['forbidden_frac']:.3f}) {r['mint_by_class']} obj {r['object_blocks']}")
    print("\nALT ISLAND (9,5):", alt)

    # ---------- picture ----------
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
        COL = {"grass": "#7fbf5f", "sand": "#e8d9a0", "plateau": "#9fd08a",
               "shelf": "#b6d6a0", "forest": "#2f6b34", "rock": "#8a7a6a",
               "lip": "#6f5f50", "desert": "#d8bf7a", "town": "#c06060",
               "riverwater": "#5f8fd0"}
        fig, ax = plt.subplots(figsize=(11, 11))
        ax.set_facecolor("#22415e")
        for c, r in land.items():
            ax.add_patch(Rectangle((c[0] * CELL, c[1] * CELL), CELL, CELL,
                                   fc=COL.get(r["dom"], "#999999"), ec="none"))
        # mesa outline
        for c in mesa_cells:
            ax.add_patch(Rectangle((c[0] * CELL, c[1] * CELL), CELL, CELL,
                                   fc="none", ec="#ff2020", lw=0.4))
        for bx in WIN_X:
            ax.axvline(bx * BLOCK, color="k", lw=0.4, alpha=0.35)
        for by in WIN_Y:
            ax.axhline(-by * BLOCK, color="k", lw=0.4, alpha=0.35)
        # radius rings
        cen = mesa_pts.mean(axis=0)
        for R in (32, 64, 96, 128):
            ax.add_patch(plt.Circle((cen[0], cen[1]), R, fill=False, ec="#ffff00",
                                    lw=0.8, ls="--"))
            ax.text(cen[0] + R * 0.7, cen[1] + R * 0.7, f"{R}u", color="#ffff00", fontsize=7)
        ax.set_xlim(min(WIN_X) * BLOCK, (max(WIN_X) + 1) * BLOCK)
        ax.set_ylim(-(max(WIN_Y) + 1) * BLOCK, -min(WIN_Y) * BLOCK)
        ax.set_aspect("equal")
        ax.set_title("donor (15,14) neighbourhood by topograph class -- red = the mesa\n"
                     "a coast cut must lie in grass/sand (light green / tan); "
                     "rock (brown) and forest (dark) are off-language cut sites")
        fig.tight_layout()
        fig.savefig(OUT / "region_cut_sites.png", dpi=110)
        print("\nwrote out/region_cut_sites.json + out/region_cut_sites.png")
    except Exception as e:  # pragma: no cover
        print("plot skipped:", e)


if __name__ == "__main__":
    main()
