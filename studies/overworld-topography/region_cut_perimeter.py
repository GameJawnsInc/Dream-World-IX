"""THE 1x2 ISLAND PERIMETER — the exact substrate a minted coast would be cut through,
for the candidate carry footprint blocks (15,14)+(15,15).

Perimeter = 6 sides of 64u = 384u:  N/E/W of (15,14)  +  E/W/S of (15,15).
For each 1u sample: the class and height of the HIGHEST carried surface meeting the line.
Lawful coast substrate = grass/sand at lowland (the coast machinery's proven case).
Off-language = rock / plateau / forest (THE FREE-BASE LAW, THE INTERIOR WALL != THE
COASTAL STRIP, and topo-37 borders only grass map-wide).

Also reports the same scan for the 1x1 (mesa block alone) and for a 1x3 variant, so the
scope choice is a measured trade and not a preference.

READ-ONLY. Writes out/region_cut_perimeter.json.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
from ff9mapkit.world import extract as X  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
BLOCK, DISC, TOL = 64.0, 1, 0.05
ROCKY, PLAT, FOR = {49, 7, 62}, {10, 11, 12, 13}, {36, 37}
SANDY = {31, 32, 33}


def read_tris(blk):
    bx, by = blk
    bm = X.read_block(bx, by, disc=DISC, part="terrain")
    ox, oz = BLOCK * bx, -BLOCK * by
    V, T, fi = bm.chan_arrays[X.CH_POS], bm.chan_arrays[X.CH_TAN], bm.flat_index
    out = []
    for t in range(len(fi) // 3):
        idx = (fi[3 * t], fi[3 * t + 1], fi[3 * t + 2])
        try:
            topo = X.decode_id(int(round(T[idx[0]][0])))["topograph"]
        except Exception:
            topo = -1
        out.append((topo, [(float(V[i][0]) + ox, float(V[i][1]), float(V[i][2]) + oz)
                           for i in idx]))
    return out


def kind(topo):
    if topo in ROCKY:
        return "rock"
    if topo in PLAT:
        return "plateau"
    if topo in FOR:
        return "forest"
    if topo in SANDY:
        return "sand"
    if topo == 58:
        return "lip"
    if topo == 59:
        return "town"
    return "grass"


def scan_side(tris, blk, side):
    """1u samples along one border of one block; returns list of (kind, ymax)"""
    bx, by = blk
    x_lo, x_hi = BLOCK * bx, BLOCK * (bx + 1)
    z_hi, z_lo = -BLOCK * by, -BLOCK * (by + 1)
    res = []
    # pre-collect border edges
    edges = []
    for topo, p in tris:
        bv = []
        for v in p:
            on = ((side == "W" and abs(v[0] - x_lo) < TOL) or
                  (side == "E" and abs(v[0] - x_hi) < TOL) or
                  (side == "N" and abs(v[2] - z_hi) < TOL) or
                  (side == "S" and abs(v[2] - z_lo) < TOL))
            if on:
                bv.append(v)
        if len(bv) >= 2:
            edges.append((topo, bv[0], bv[1]))
    for i in range(64):
        if side in "NS":
            t = x_lo + i + 0.5
        else:
            t = z_lo + i + 0.5
        best = None
        for topo, a, b in edges:
            if side in "NS":
                lo, hi = min(a[0], b[0]), max(a[0], b[0])
            else:
                lo, hi = min(a[2], b[2]), max(a[2], b[2])
            if lo - 0.5 <= t <= hi + 0.5:
                y = max(a[1], b[1])
                if best is None or y > best[0]:
                    best = (y, topo)
        res.append((kind(best[1]), best[0]) if best else ("gap", None))
    return res


def report(name, footprint, sides):
    tris = {}
    for b in footprint:
        tris[b] = read_tris(b)
    tot = Counter()
    ys = []
    detail = {}
    for blk, side in sides:
        s = scan_side(tris[blk], blk, side)
        cc = Counter(k for k, _ in s)
        hs = [y for k, y in s if y is not None]
        detail[f"{blk[0]},{blk[1]}:{side}"] = {
            "class_u": dict(cc),
            "ymax_med": round(float(np.median(hs)), 2) if hs else None,
            "ymax_max": round(float(max(hs)), 2) if hs else None,
        }
        for k, v in cc.items():
            tot[k] += v
        ys += hs
    per = sum(tot.values())
    off = sum(v for k, v in tot.items() if k in ("rock", "plateau", "forest", "town"))
    lawful = sum(v for k, v in tot.items() if k in ("grass", "sand", "lip"))
    print(f"\n=== {name}: {len(footprint)} block(s), perimeter {per}u")
    for k, v in sorted(detail.items()):
        print(f"   {k:>12s} {v['class_u']}  ymax med {v['ymax_med']} max {v['ymax_max']}")
    print(f"   TOTAL {dict(tot)}")
    print(f"   LAWFUL coast substrate (grass/sand/lip) {lawful}u = {lawful/per:.1%}")
    print(f"   OFF-LANGUAGE (rock/plateau/forest/town) {off}u = {off/per:.1%}")
    return {"name": name, "footprint": [list(b) for b in footprint],
            "perimeter_u": per, "class_u": dict(tot),
            "lawful_u": lawful, "lawful_frac": lawful / per,
            "off_language_u": off, "off_language_frac": off / per,
            "per_side": detail,
            "ymax_med_all": round(float(np.median(ys)), 2) if ys else None}


def main():
    out = []
    out.append(report("1x1  mesa block alone", [(15, 14)],
                      [((15, 14), "N"), ((15, 14), "E"), ((15, 14), "S"),
                       ((15, 14), "W")]))
    out.append(report("1x2  THE PENINSULA-TIP ISLAND", [(15, 14), (15, 15)],
                      [((15, 14), "N"), ((15, 14), "E"), ((15, 14), "W"),
                       ((15, 15), "E"), ((15, 15), "W"), ((15, 15), "S")]))
    out.append(report("1x3  + (15,16)", [(15, 14), (15, 15), (15, 16)],
                      [((15, 14), "N"), ((15, 14), "E"), ((15, 14), "W"),
                       ((15, 15), "E"), ((15, 15), "W"),
                       ((15, 16), "E"), ((15, 16), "W"), ((15, 16), "S")]))
    out.append(report("2x2  + Chocobo's Forest column", [(15, 14), (15, 15), (16, 14),
                                                         (16, 15)],
                      [((15, 14), "N"), ((15, 14), "W"), ((16, 14), "N"),
                       ((16, 14), "E"), ((16, 15), "E"), ((16, 15), "S"),
                       ((15, 15), "S"), ((15, 15), "W")]))

    payload = {"instrument": "studies/overworld-topography/region_cut_perimeter.py",
               "note": "class = the HIGHEST carried surface meeting each 1u of the "
                       "footprint's outer border; that surface is what a minted coast "
                       "would have to be cut through.",
               "candidates": out}
    (OUT / "region_cut_perimeter.json").write_text(json.dumps(payload, indent=1))
    print("\nwrote out/region_cut_perimeter.json")


if __name__ == "__main__":
    main()
