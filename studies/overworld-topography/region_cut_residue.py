"""THE RESIDUE ANATOMY — what exactly is the 28u of off-language cut at block (15,14)'s
N and E borders, and is it CREST or SKIRT?

This decides whether the eliminate-the-class design is buildable:
 * if the severed rock is BODY/SKIRT below the crest, THE TAPER LAW applies (42/42 real
   crest endpoints taper to ground, 0 continue) -- a measured, carried-vocabulary repair.
 * if the severed rock includes CREST (the plateau's own rim), the repair is a crest
   truncation, which stock has 0 instances of, and the design is a West-Finger repeat.

Also measures the mesa's OWN closure: does the plateau (topo 10/11/12) crest ring close
inside block (15,14)?

READ-ONLY. Writes out/region_cut_residue.json.
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
from ff9mapkit.world import extract as X  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
CELL, BLOCK, DISC = 4.0, 64.0, 1
DONOR = (15, 14)
NEIGH = [(15, 14), (15, 13), (16, 14), (14, 14), (15, 15), (16, 13), (14, 13)]

ROCKY = {49, 7, 62}
PLAT = {10, 11, 12}


def main():
    tris = []   # (bx,by,topo, world verts)
    for (bx, by) in NEIGH:
        try:
            bm = X.read_block(bx, by, disc=DISC, part="terrain")
        except Exception:
            continue
        ox, oz = BLOCK * bx, -BLOCK * by
        V, T, fi = bm.chan_arrays[X.CH_POS], bm.chan_arrays[X.CH_TAN], bm.flat_index
        for t in range(len(fi) // 3):
            idx = (fi[3 * t], fi[3 * t + 1], fi[3 * t + 2])
            try:
                topo = X.decode_id(int(round(T[idx[0]][0])))["topograph"]
            except Exception:
                topo = -1
            p = [(float(V[i][0]) + ox, float(V[i][1]), float(V[i][2]) + oz) for i in idx]
            tris.append(((bx, by), topo, p))

    # the donor block's frame in world coords
    x_lo, x_hi = BLOCK * DONOR[0], BLOCK * (DONOR[0] + 1)
    z_hi, z_lo = -BLOCK * DONOR[1], -BLOCK * (DONOR[1] + 1)
    print(f"donor block frame  x [{x_lo},{x_hi}]  z [{z_lo},{z_hi}]")

    TOL = 0.05

    def on_border(p):
        """which borders a vertex sits on"""
        s = []
        if abs(p[0] - x_lo) < TOL:
            s.append("W")
        if abs(p[0] - x_hi) < TOL:
            s.append("E")
        if abs(p[2] - z_hi) < TOL:
            s.append("N")
        if abs(p[2] - z_lo) < TOL:
            s.append("S")
        return s

    # ---- verts of the donor block's ROCK and PLATEAU that sit on each border ----
    per_side = {k: {"rock": [], "plat": [], "grass": []} for k in "NSEW"}
    for blk, topo, p in tris:
        if blk != DONOR:
            continue
        kind = "rock" if topo in ROCKY else "plat" if topo in PLAT else "grass"
        for v in p:
            for s in on_border(v):
                per_side[s][kind].append(round(v[1], 3))

    print("\nDONOR BLOCK verts sitting ON each border, by class (y stats):")
    resid = {}
    for s in "NSEW":
        row = {}
        for kind in ("rock", "plat", "grass"):
            ys = sorted(set(per_side[s][kind]))
            row[kind] = {"n_unique_y": len(ys),
                         "ymin": ys[0] if ys else None,
                         "ymax": ys[-1] if ys else None}
        resid[s] = row
        print(f"  {s}: rock  n={row['rock']['n_unique_y']:>3} y "
              f"[{row['rock']['ymin']}, {row['rock']['ymax']}]   "
              f"plateau n={row['plat']['n_unique_y']:>3} y "
              f"[{row['plat']['ymin']}, {row['plat']['ymax']}]   "
              f"grass n={row['grass']['n_unique_y']:>3} y "
              f"[{row['grass']['ymin']}, {row['grass']['ymax']}]")

    # ---- does the donor's plateau (crest) ring close inside the block? ----
    plat_pts = [v for blk, topo, p in tris if blk == DONOR and topo in PLAT for v in p]
    if plat_pts:
        px = [v[0] for v in plat_pts]
        pz = [v[2] for v in plat_pts]
        py = [v[1] for v in plat_pts]
        print(f"\ndonor PLATEAU (crest top): {len(plat_pts)} verts, "
              f"x [{min(px):.1f},{max(px):.1f}] of [{x_lo},{x_hi}], "
              f"z [{min(pz):.1f},{max(pz):.1f}] of [{z_lo},{z_hi}], "
              f"y [{min(py):.2f},{max(py):.2f}]")
        margins = {"W": min(px) - x_lo, "E": x_hi - max(px),
                   "S": min(pz) - z_lo, "N": z_hi - max(pz)}
        print(f"  crest clearance to each block border: "
              f"{ {k: round(v,2) for k,v in margins.items()} }")
        crest_closed = all(v > 0.5 for v in margins.values())
        print(f"  => CREST RING CLOSES INSIDE THE BLOCK: {crest_closed}")
    else:
        margins, crest_closed = {}, None

    # ---- the severed rock: rock verts on N/E border shared with a NEIGHBOUR block's rock
    nb_rock = {}
    for blk, topo, p in tris:
        if blk == DONOR or topo not in ROCKY:
            continue
        for v in p:
            nb_rock.setdefault((round(v[0], 2), round(v[2], 2)), []).append(round(v[1], 3))
    shared = []
    for blk, topo, p in tris:
        if blk != DONOR or topo not in ROCKY:
            continue
        for v in p:
            k = (round(v[0], 2), round(v[2], 2))
            if k in nb_rock and any(abs(y - v[1]) < 0.05 for y in nb_rock[k]):
                shared.append((k[0], k[1], round(v[1], 3), "".join(on_border(v))))
    shared = sorted(set(shared))
    print(f"\nROCK verts of the donor block that COINCIDE with neighbour-block rock: "
          f"{len(shared)}")
    bside = Counter()
    for x, z, y, sides in shared:
        for s in sides:
            bside[s] += 1
    print(f"  by border: {dict(bside)}")
    if shared:
        ys = [s[2] for s in shared]
        print(f"  y: min {min(ys):.2f} med {np.median(ys):.2f} max {max(ys):.2f}")
        for s in shared:
            print(f"    x={s[0]:>7.1f} z={s[1]:>8.1f} y={s[2]:>6.2f} on {s[3]}")

    # ---- how much of the block's border length is rock-faced vs grass-faced ----
    # sample the border every 1u and ask what the nearest donor-block surface class is
    def border_scan(side):
        out = Counter()
        heights = []
        n = 64
        for i in range(n):
            if side in "NS":
                x = x_lo + i + 0.5
                z = z_hi if side == "N" else z_lo
            else:
                z = z_lo + i + 0.5
                x = x_hi if side == "E" else x_lo
            best = None
            for blk, topo, p in tris:
                if blk != DONOR:
                    continue
                # does the triangle touch this border line near x/z?
                bv = [v for v in p if side in on_border(v)]
                if len(bv) < 2:
                    continue
                a, b = bv[0], bv[1]
                if side in "NS":
                    lo, hi = min(a[0], b[0]), max(a[0], b[0])
                    if lo - 0.5 <= x <= hi + 0.5:
                        cand = (max(a[1], b[1]), topo)
                        if best is None or cand[0] > best[0]:
                            best = cand
                else:
                    lo, hi = min(a[2], b[2]), max(a[2], b[2])
                    if lo - 0.5 <= z <= hi + 0.5:
                        cand = (max(a[1], b[1]), topo)
                        if best is None or cand[0] > best[0]:
                            best = cand
            if best is None:
                out["gap"] += 1
            else:
                k = "rock" if best[1] in ROCKY else "plat" if best[1] in PLAT else \
                    "forest" if best[1] in (36, 37) else "grass"
                out[k] += 1
                heights.append(best[0])
        return out, heights

    scan = {}
    print("\nBORDER SCAN (1u samples along each border of the donor block, "
          "class of the highest donor surface meeting it):")
    for s in "NSEW":
        cc, hs = border_scan(s)
        scan[s] = {"class_u": dict(cc),
                   "ymax_med": float(np.median(hs)) if hs else None,
                   "ymax_max": float(max(hs)) if hs else None}
        print(f"  {s}: {dict(cc)}  ymax med "
              f"{np.median(hs) if hs else None:.2f} max {max(hs) if hs else 0:.2f}")

    tot = Counter()
    for s in "NSEW":
        for k, v in scan[s]["class_u"].items():
            tot[k] += v
    print(f"\nTOTAL 256u of donor-block border: {dict(tot)}")
    nong = sum(v for k, v in tot.items() if k in ("rock", "plat", "forest"))
    print(f"  off-language coast substrate (rock/plateau/forest) = {nong}u of 256u "
          f"= {nong/256:.1%}")

    payload = {
        "instrument": "studies/overworld-topography/region_cut_residue.py",
        "donor_block": list(DONOR),
        "border_verts_by_class": resid,
        "crest_margins_to_border": {k: round(v, 3) for k, v in margins.items()},
        "crest_ring_closes_inside_block": crest_closed,
        "shared_rock_verts_with_neighbours": {
            "count": len(shared), "by_border": dict(bside),
            "y_min": min((s[2] for s in shared), default=None),
            "y_med": float(np.median([s[2] for s in shared])) if shared else None,
            "y_max": max((s[2] for s in shared), default=None),
            "verts": [{"x": s[0], "z": s[1], "y": s[2], "borders": s[3]} for s in shared],
        },
        "border_scan_1u": scan,
        "border_total_u": dict(tot),
        "off_language_coast_substrate_u": nong,
        "off_language_frac": nong / 256.0,
    }
    (OUT / "region_cut_residue.json").write_text(json.dumps(payload, indent=1))
    print("\nwrote out/region_cut_residue.json")


if __name__ == "__main__":
    main()
