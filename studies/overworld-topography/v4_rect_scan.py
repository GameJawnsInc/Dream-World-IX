"""V4 RECT SCAN -- find windows whose external land crossings are ALL LOWLAND.

Uses out/v4_census.json (per-block per-edge land ymax). A rect passes when every
block-edge on its perimeter either has no land at the frame or crosses at ymax <= CUT_Y
(the cut-line law's territory -- sealable by the proven shore vocabulary). Rank passing
rects by raised walkable content (mid+high) inside.

Run from the repo root:  py studies/overworld-topography/v4_rect_scan.py
"""
import json
from itertools import product
from pathlib import Path

CUT_Y = 6.5
data = json.load(open(Path(__file__).parent / "out" / "v4_census.json"))
blk = {tuple(map(int, k.split(","))): v for k, v in data["blocks"].items()}

# NB: grid row y advances toward -Z; a block's local z=0 edge ("N") faces row y-1.
EDGE_NB = {"W": (-1, 0), "E": (1, 0), "N": (0, -1), "S": (0, 1)}

results = []
for rw, rh in product(range(1, 5), range(1, 4)):
    for x0 in range(0, 24 - rw + 1):
        for y0 in range(0, 20 - rh + 1):
            cells = [(x, y) for x in range(x0, x0 + rw) for y in range(y0, y0 + rh)]
            present = [c for c in cells if c in blk]
            if not present:
                continue
            agg = {k: sum(blk[c][k] for c in present)
                   for k in ("low_a", "mid_a", "high_a", "t13_a", "esc_a")}
            if agg["mid_a"] + agg["high_a"] < 300 or agg["low_a"] < 300:
                continue
            ok, crossings = True, []
            for c in present:
                for e, (dx, dy) in EDGE_NB.items():
                    nb = (c[0] + dx, c[1] + dy)
                    if nb in cells:
                        continue                            # interior border
                    ed = blk[c]["edges"][e]
                    if ed["land"]:
                        if ed["ymax"] is not None and ed["ymax"] > CUT_Y:
                            ok = False
                            break
                        crossings.append((c, e, round(ed["ymax"] or 0, 1)))
                if not ok:
                    break
            if not ok:
                continue
            coastal = any(blk[c]["cover"] < 0.9 for c in present)
            results.append({
                "rect": (x0, y0, rw, rh), **{k: round(v) for k, v in agg.items()},
                "coastal": coastal, "cross": crossings,
                "cover": round(sum(blk[c]["cover"] for c in present) / len(cells), 2),
            })

results.sort(key=lambda r: -(r["mid_a"] + r["high_a"]))
print(f"{len(results)} rects pass the lowland-cut rule (CUT_Y={CUT_Y})")
seen_anchor = set()
for r in results[:40]:
    x0, y0, rw, rh = r["rect"]
    key = (x0 // 2, y0 // 2)                                # thin out overlapping repeats
    print(f"rect ({x0},{y0}) {rw}x{rh} cover {r['cover']:.2f} "
          f"low {r['low_a']:6} mid {r['mid_a']:6} high {r['high_a']:6} "
          f"t13 {r['t13_a']:5} esc {r['esc_a']:6} coastal {r['coastal']} "
          f"cuts {[(f'{c[0]},{c[1]}', e, y) for c, e, y in r['cross']]}")
