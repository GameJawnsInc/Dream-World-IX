"""THE CLOSURE TEST — does a coast-lawful cut line around the (15,14) mesa exist at all?

A minted coast is only in-language where stock puts coasts: lowland grass / sand.
(THE FREE-BASE LAW: topo-58 is coastal-only, cliff bases terminate free at/below the
waterline, zero cliff-face base edges land on walkable terrain. THE INTERIOR WALL !=
THE COASTAL STRIP: 0 of 76 interior wall components touch the coastal rock strip.)

So the eliminate-the-class design needs a closed footprint F such that
  (1) F contains the whole mesa,
  (2) every boundary cell of F is grass or sand at lowland y<=8,
  (3) F is small enough to carry.
This instrument tests whether such an F exists, by growing the mesa's own
NON-GRASS blob (rock/plateau/shelf/forest -- everything a coast may not cut) to
closure, then measuring the grass ring around it.

If the blob does not close inside a tractable footprint, the class is NOT deletable at
this donor and the lens must say so.

READ-ONLY. Writes out/region_cut_closure.json (+ .png).
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, deque
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
from ff9mapkit.world import extract as X  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
CELL, BLOCK, DISC = 4.0, 64.0, 1
DONOR = (15, 14)
WIN_X, WIN_Y = range(10, 21), range(9, 19)

GRASS = {0, 1, 2, 3, 42}
SAND = {31, 32, 33}
NOCUT = {49, 7, 62, 10, 11, 12, 13, 36, 37, 58, 59, 45, 46,
         16, 17, 18, 19, 20, 21, 22, 23, 41, 27, 28}


def load():
    land, blockparts = {}, {}
    for bx in WIN_X:
        for by in WIN_Y:
            try:
                bm = X.read_block(bx, by, disc=DISC, part="terrain")
            except Exception:
                continue
            parts = ["terrain"]
            for p in ("object", "river", "riverjoint", "falls", "stream",
                      "sea1", "sea2", "sea3", "sea4", "sea5", "beach1", "beach2"):
                try:
                    X.read_block(bx, by, disc=DISC, part=p)
                    parts.append(p)
                except Exception:
                    pass
            blockparts[(bx, by)] = parts
            ox, oz = BLOCK * bx, -BLOCK * by
            V, T, fi = bm.chan_arrays[X.CH_POS], bm.chan_arrays[X.CH_TAN], bm.flat_index
            for t in range(len(fi) // 3):
                i0, i1, i2 = fi[3 * t], fi[3 * t + 1], fi[3 * t + 2]
                a, b, c = V[i0], V[i1], V[i2]
                gx = int(math.floor(((a[0] + b[0] + c[0]) / 3.0 + ox) / CELL))
                gz = int(math.floor(((a[2] + b[2] + c[2]) / 3.0 + oz) / CELL))
                try:
                    topo = X.decode_id(int(round(T[i0][0])))["topograph"]
                except Exception:
                    topo = -1
                ar = abs((b[0] - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (b[2] - a[2])) / 2.0
                r = land.setdefault((gx, gz), {"w": Counter(), "ymax": -1e9, "block": (bx, by)})
                r["w"][topo] += ar
                r["ymax"] = max(r["ymax"], a[1], b[1], c[1])
    for r in land.values():
        dom = r["w"].most_common(1)[0][0]
        r["topo"] = dom
        r["cut_ok"] = (dom in GRASS or dom in SAND) and r["ymax"] <= 8.0
        r["nocut"] = dom in NOCUT
    return land, blockparts


def main():
    land, blockparts = load()
    print(f"land cells {len(land)}  blocks {len(blockparts)}")

    # mesa seed: the rock/plateau cells of the donor block
    seed = [c for c, r in land.items() if r["block"] == DONOR and r["nocut"]
            and r["topo"] in (49, 10, 11, 12)]
    print(f"mesa seed cells (rock/plateau in {DONOR}) = {len(seed)}")

    # ---- grow the NO-CUT blob to closure (8-connected: a coast cannot squeeze a diagonal)
    for conn_name, deltas in (("4conn", ((1, 0), (-1, 0), (0, 1), (0, -1))),
                              ("8conn", tuple((dx, dz) for dx in (-1, 0, 1)
                                              for dz in (-1, 0, 1) if (dx, dz) != (0, 0)))):
        blob = set(seed)
        dq = deque(seed)
        growth = []
        step = 0
        while dq:
            n_before = len(blob)
            for _ in range(len(dq)):
                c = dq.popleft()
                for d in deltas:
                    n = (c[0] + d[0], c[1] + d[1])
                    if n in blob or n not in land:
                        continue
                    if land[n]["nocut"]:
                        blob.add(n)
                        dq.append(n)
            step += 1
            if len(blob) == n_before:
                break
            if step <= 40:
                bl = sorted({land[c]["block"] for c in blob})
                growth.append({"step": step, "cells": len(blob), "blocks": len(bl)})
        bl = sorted({land[c]["block"] for c in blob})
        xs = [c[0] for c in blob]
        zs = [c[1] for c in blob]
        print(f"\n[{conn_name}] NO-CUT blob containing the mesa closes at "
              f"{len(blob)} cells / {len(bl)} blocks, "
              f"extent {(max(xs)-min(xs)+1)*CELL:.0f} x {(max(zs)-min(zs)+1)*CELL:.0f}u")
        print(f"          blocks: {bl[:30]}{' ...' if len(bl) > 30 else ''}")
        cc = Counter(land[c]["topo"] for c in blob)
        print(f"          topo hist (top): {cc.most_common(8)}")
        objb = [b for b in bl if "object" in blockparts.get(b, [])]
        print(f"          object blocks inside: {len(objb)} -> {objb[:12]}")
        if conn_name == "4conn":
            blob4, bl4, growth4 = blob, bl, growth
        else:
            blob8, bl8 = blob, bl

    # ---- what would it take to isolate the mesa: how many NO-CUT cells must be
    # severed at the block borders of (15,14) alone?
    bx, by = DONOR
    gx0 = int(bx * BLOCK / CELL)
    gz1 = int(-by * BLOCK / CELL)
    gz0 = gz1 - 16
    inside = {(gx0 + i, gz0 + j) for i in range(16) for j in range(16)} & set(land)
    sever = []
    for c in inside:
        if not land[c]["nocut"]:
            continue
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (c[0] + d[0], c[1] + d[1])
            if n in inside or n not in land:
                continue
            if land[n]["nocut"]:
                sever.append({"in": list(c), "out": list(n),
                              "in_topo": land[c]["topo"], "out_topo": land[n]["topo"],
                              "in_ymax": round(land[c]["ymax"], 2),
                              "out_ymax": round(land[n]["ymax"], 2)})
    print(f"\nNO-CUT-to-NO-CUT edges crossing block ({bx},{by})'s border: {len(sever)} "
          f"= {len(sever)*CELL:.0f}u of off-language cut")
    side = Counter()
    for s in sever:
        ix, iz = s["in"]
        ox_, oz_ = s["out"]
        side["N" if oz_ > iz else "S" if oz_ < iz else "E" if ox_ > ix else "W"] += 1
    print(f"   by side: {dict(side)}")
    print(f"   heights: in ymax med {np.median([s['in_ymax'] for s in sever]):.2f} "
          f"max {max(s['in_ymax'] for s in sever):.2f}; "
          f"out ymax max {max(s['out_ymax'] for s in sever):.2f}")

    # ---- the reciprocal question: how much LAWFUL grass ring does the mesa have,
    # per side, inside its own block?
    ring = Counter()
    for c in inside:
        if land[c]["cut_ok"]:
            ring["cut_ok"] += 1
        elif land[c]["nocut"]:
            ring["nocut"] += 1
        else:
            ring["other"] += 1
    print(f"\ndonor block ({bx},{by}) cell composition: {dict(ring)}")

    # ---- per-side: is there ANY grass between the mesa and each block border?
    per_side = {}
    for name, cells in (
        ("N", [[(gx0 + i, gz1 - 1 - k) for k in range(6)] for i in range(16)]),
        ("S", [[(gx0 + i, gz0 + k) for k in range(6)] for i in range(16)]),
        ("W", [[(gx0 + k, gz0 + j) for k in range(6)] for j in range(16)]),
        ("E", [[(gx0 + 15 - k, gz0 + j) for k in range(6)] for j in range(16)]),
    ):
        depths = []
        for ray in cells:
            d = 0
            for c in ray:
                if c in land and land[c]["cut_ok"]:
                    d += 1
                else:
                    break
            depths.append(d)
        per_side[name] = {"grass_depth_cells": depths,
                          "med": float(np.median(depths)),
                          "zero_depth_rays": int(sum(1 for d in depths if d == 0))}
        print(f"  side {name}: inward lawful-grass depth (cells of 4u) {depths} "
              f"med {np.median(depths):.1f}, rays with NO grass margin "
              f"{sum(1 for d in depths if d == 0)}/16")

    payload = {
        "instrument": "studies/overworld-topography/region_cut_closure.py",
        "land_cells": len(land), "blocks_read": len(blockparts),
        "mesa_seed_cells": len(seed),
        "nocut_blob_4conn": {"cells": len(blob4), "blocks": len(bl4),
                             "block_list": [list(b) for b in bl4],
                             "growth": growth4[:40]},
        "nocut_blob_8conn": {"cells": len(blob8), "blocks": len(bl8),
                             "block_list": [list(b) for b in bl8]},
        "donor_border_nocut_edges": {"count": len(sever), "u": len(sever) * CELL,
                                     "by_side": dict(side), "edges": sever},
        "donor_block_cells": dict(ring),
        "per_side_grass_margin": per_side,
    }
    (OUT / "region_cut_closure.json").write_text(json.dumps(payload, indent=1))
    print("\nwrote out/region_cut_closure.json")


if __name__ == "__main__":
    main()
