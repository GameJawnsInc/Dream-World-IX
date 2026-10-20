"""RUNG5.md 5c: can `world-river` carry the river's OWN birthplace? A RECON -- it reads stock bytes only and writes
nothing but out/escarpment_recon.json.

Cluster C's source is born at the continental escarpment (comp0's step from the 3.2 lowland to a ~27 plateau). A
lawful carry of that foot would be a slice that closes the way every lawful window closes: THE CUT-LINE LAW (v4
transplant census, `../../overworld-topography/README.md`): a cut crosses only lowland (land at y <= 6.5), high relief
is a component, cut around and never through. Registered prediction (RUNG5.md): NO such slice under about 6 blocks.

  A. THE RECT SCAN round the source: every rect up to 4x3 blocks holding the source block, scored by the v4 census's
     own per-edge land heights (out/v4_census.json, from stock); a rect passes when every external land crossing
     is <= 6.5.
  B. THE HIGH COMPONENT (decisive): the terrain tris whose top exceeds 6.5, joined by shared edges, from the ones
     within 8u of the source tip. A lowland-only cut must enclose ALL of it, so its extent is the smallest lawful
     slice. Also what it holds: the tower (topo 59), entrance tiles (event bits), forests.
  C. THE CUT FOR THE BEST RECT: the length of high ground its frame would sever, and how high.
RUN:  py studies/terrain-malleability/watercarry/escarpment_recon.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from itertools import product
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__
from ff9mapkit.world import extract as X, river as R  # noqa: E402

CUT_Y = 6.5                                   # THE CUT-LINE LAW's lowland ceiling (v4_rect_scan.CUT_Y)
TIP = (1128.6, -917.8)                        # the source contact (RUNG5.md, re-measured)
SRC_BLOCK = (17, 14)
WINDOW = ((9, 23), (6, 19))                   # block cols, rows read for B (comp0 spans cols 11-22, rows 9-16)
CENSUS = Path(r"C:\gd\Dream-World-IX\studies\overworld-topography\out\v4_census.json")   # main repo: out/ is untracked
EDGE_NB = {"W": (-1, 0), "E": (1, 0), "N": (0, -1), "S": (0, 1)}


def rect_scan():
    blk = {tuple(map(int, k.split(","))): v for k, v in json.loads(CENSUS.read_text())["blocks"].items()}
    out = []
    for rw, rh in product(range(1, 5), range(1, 4)):
        for x0 in range(SRC_BLOCK[0] - rw + 1, SRC_BLOCK[0] + 1):
            for y0 in range(SRC_BLOCK[1] - rh + 1, SRC_BLOCK[1] + 1):
                cells = [(x, y) for x in range(x0, x0 + rw) for y in range(y0, y0 + rh)]
                high, low = [], 0
                for c in (c for c in cells if c in blk):
                    for e, (dx, dy) in EDGE_NB.items():
                        if (c[0] + dx, c[1] + dy) in cells:
                            continue
                        ed = blk[c]["edges"][e]
                        if ed["land"]:
                            if ed["ymax"] is not None and ed["ymax"] > CUT_Y:
                                high.append((c, e, round(ed["ymax"], 1)))
                            else:
                                low += 1
                out.append({"rect": (x0, y0, rw, rh), "blocks": rw * rh, "high_crossings": len(high),
                            "high_ymax": max((h[2] for h in high), default=None), "high": high[:12],
                            "low_crossings": low, "passes": not high})
    out.sort(key=lambda r: (r["high_crossings"], r["high_ymax"] or 0, r["blocks"]))
    return out


def stock_terrain():
    bp = X.block_parts(disc=1)
    (bx0, bx1), (by0, by1) = WINDOW
    tris = []
    for bx in range(bx0, bx1 + 1):
        for by in range(by0, by1 + 1):
            if "terrain" in bp.get((bx, by), ()):
                tris += R.block_tris(X.read_block(bx, by, disc=1, part="terrain"), bx, by, "terrain")
    return tris


def high_component(tris):
    key = lambda p: (round(float(p[0]), 3), round(float(p[2]), 3))          # noqa: E731 (xz: stacked walls share)
    high = [i for i, t in enumerate(tris) if t["P"][:, 1].max() > CUT_Y]
    hset = set(high)
    by_edge = defaultdict(list)
    for i in high:
        P = tris[i]["P"]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            by_edge[tuple(sorted((key(P[a]), key(P[b]))))].append(i)
    nb = defaultdict(set)
    for ids in by_edge.values():
        for i in ids:
            nb[i].update(j for j in ids if j != i)
    cen = np.array([t["P"].mean(axis=0) for t in tris])
    seeds = [i for i in high if np.hypot(cen[i, 0] - TIP[0], cen[i, 2] - TIP[1]) < 8.0]
    comp, stack = set(seeds), list(seeds)
    while stack:
        for j in nb[stack.pop()]:
            if j not in comp and j in hset:
                comp.add(j)
                stack.append(j)
    (bx0, bx1), (by0, by1) = WINDOW
    xs, zs = cen[list(comp), 0], cen[list(comp), 2]
    on_frame = bool(len(comp)) and bool(xs.min() < 64 * bx0 + 8 or xs.max() > 64 * (bx1 + 1) - 8
                                    or zs.max() > -64 * by0 - 8 or zs.min() < -64 * (by1 + 1) + 8)
    area = sum(0.5 * abs(np.cross(tris[i]["P"][1] - tris[i]["P"][0], tris[i]["P"][2] - tris[i]["P"][0])[1])
               for i in comp)
    dec = [X.decode_id(tris[i]["idall"]) for i in comp]
    near = lambda r: [i for i in comp if np.hypot(cen[i, 0] - TIP[0], cen[i, 2] - TIP[1]) < r]   # noqa: E731
    return {"seeds": len(seeds), "tris": len(comp), "plan_area_u2": round(float(area)),
            "blocks": len({tris[i]["blk"] for i in comp}),
            "bbox_x": [round(float(xs.min()), 1), round(float(xs.max()), 1)] if len(comp) else None,
            "bbox_z": [round(float(zs.min()), 1), round(float(zs.max()), 1)] if len(comp) else None,
            "y_max": round(float(max(tris[i]["P"][:, 1].max() for i in comp)), 2) if comp else None,
            "reaches_window_frame": on_frame,
            "topos": dict(Counter(d["topograph"] for d in dec).most_common(8)),
            "tower_tris": sum(1 for d in dec if d["topograph"] == 59),
            "event_tris": sum(1 for d in dec if d["event"]),
            "within_64u": len(near(64)), "within_128u": len(near(128))}


def frame_cut(tris, rect):
    """Length of high ground (top > 6.5) along the rect's external frame, sampled every 0.5u, with its top height."""
    x0, y0, rw, rh = rect
    X0, X1, Z0, Z1 = 64.0 * x0, 64.0 * (x0 + rw), -64.0 * (y0 + rh), -64.0 * y0
    P = np.array([t["P"] for t in tris])
    lo, hi = P[:, :, [0, 2]].min(axis=1), P[:, :, [0, 2]].max(axis=1)

    def top(x, z):
        cand = np.where((lo[:, 0] <= x) & (hi[:, 0] >= x) & (lo[:, 1] <= z) & (hi[:, 1] >= z))[0]
        best = None
        for i in cand:
            a, b, c = P[i][:, [0, 2]]
            v0, v1, v2 = c - a, b - a, np.array([x, z]) - a
            d = v0[0] * v1[1] - v0[1] * v1[0]
            if abs(d) < 1e-12:
                continue
            u = (v2[0] * v1[1] - v2[1] * v1[0]) / d
            w = (v0[0] * v2[1] - v0[1] * v2[0]) / d
            if u >= -1e-6 and w >= -1e-6 and u + w <= 1 + 1e-6:
                y = P[i][0, 1] + u * (P[i][2, 1] - P[i][0, 1]) + w * (P[i][1, 1] - P[i][0, 1])
                best = y if best is None else max(best, y)
        return best
    sides = {"N": [(x, Z1) for x in np.arange(X0, X1, 0.5)], "S": [(x, Z0) for x in np.arange(X0, X1, 0.5)],
             "W": [(X0, z) for z in np.arange(Z0, Z1, 0.5)], "E": [(X1, z) for z in np.arange(Z0, Z1, 0.5)]}
    out = {}
    for s, pts in sides.items():
        ys = [top(x, z) for x, z in pts]
        hi_ = [y for y in ys if y is not None and y > CUT_Y]
        out[s] = {"high_u": len(hi_) * 0.5, "top": round(max(hi_), 1) if hi_ else None,
                  "land_u": sum(1 for y in ys if y is not None and y > 0.6) * 0.5}
    return out


def main():
    scan = rect_scan()
    tris = stock_terrain()
    comp = high_component(tris)
    best = scan[0]
    rep = {"cut_y": CUT_Y, "tip": TIP, "rects_scanned": len(scan), "rects_passing": sum(r["passes"] for r in scan),
           "best_rects": scan[:6], "high_component": comp, "window": WINDOW, "terrain_tris_read": len(tris),
           "best_rect_frame_cut": {"rect": best["rect"], **frame_cut(tris, best["rect"])}}
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "escarpment_recon.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: rep[k] for k in ("rects_scanned", "rects_passing", "high_component", "best_rect_frame_cut")},
                     indent=1, default=str))
    for r in scan[:6]:
        print(r["rect"], r["blocks"], "blocks; high crossings", r["high_crossings"], "max", r["high_ymax"], r["high"][:4])


if __name__ == "__main__":
    main()
