"""Is the fringe tile CONTINUOUS across shared positions in stock -- and in take 8's window? (read-only)

Worldmap meshes share no vertex entries: a weld is two entries at one position. For every position
where two or more fringe (r10 c6-9) tris meet, the spread of their v (in tile units) is a seam: 0 =
continuous texture, ~1 = one tri shows the fringe where its neighbour shows the rock top. Also the FAN
census: incident fringe tris per contact position (take 8's SE corner fans 5 rock tris off one dip
vertex). Reported for every disc-1 stock block and for the deployed take-8 window.

    py studies/overworld-topography/west-seam-continent/stock_fringe_continuity.py
"""
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                     # noqa: E402
from stock_fringe_census import TV, PV, tile, pct           # noqa: E402
from take8_defect_census import load                         # noqa: E402

WINDOW = (1412.0, -494.0, 1446.0, -458.0)


def spreads(tris):
    """tris: iterable of (positions[3], uvs[3]) for fringe tris -> (v spreads, fan counts) per position."""
    at = defaultdict(list)
    for ps, uvs in tris:
        tr, tc = tile(uvs)
        vb = PV + tr * TV
        for p, uv in zip(ps, uvs):
            at[(round(p[0], 2), round(p[1], 2), round(p[2], 2))].append((uv[1] - vb) / TV)
    sp = [max(v) - min(v) for v in at.values() if len(v) >= 2]
    fans = [len(v) for v in at.values()]
    return sp, fans


def is_fringe(uvs):
    tr, tc = tile(uvs)
    return tr == 10 and 6 <= tc <= 9


def main():
    stock = []
    for bx in range(24):
        for by in range(20):
            try:
                bm = X.read_block(bx, by, disc=1)
            except Exception:
                continue
            for a, b, c in bm.tris:
                uvs = [bm.uvs[i] for i in (a, b, c)]
                if is_fringe(uvs):
                    stock.append(([bm.verts[i] for i in (a, b, c)], uvs))
    sp, fans = spreads(stock)
    print(f"STOCK fringe tris {len(stock)}: shared positions {len(sp)}; v spread p50 {pct(sp, 50):.3f} "
          f"p90 {pct(sp, 90):.3f} p99 {pct(sp, 99):.3f} max {max(sp):.3f}; "
          f"{sum(s > 0.25 for s in sp)} seams > 0.25")
    print(f"  fan: tris per position p50 {pct(fans, 50)} p99 {pct(fans, 99)} max {max(fans)}")
    win = [(r["w"], r["uv"]) for r in load() if is_fringe(r["uv"])
           and WINDOW[0] <= sum(p[0] for p in r["w"]) / 3 <= WINDOW[2]
           and WINDOW[1] <= sum(p[2] for p in r["w"]) / 3 <= WINDOW[3]]
    sp, fans = spreads(win)
    print(f"TAKE 8 window fringe tris {len(win)}: shared positions {len(sp)}; v spread p50 {pct(sp, 50):.3f} "
          f"p90 {pct(sp, 90):.3f} max {max(sp):.3f}; {sum(s > 0.25 for s in sp)} seams > 0.25")
    print(f"  fan: tris per position p50 {pct(fans, 50)} p99 {pct(fans, 99)} max {max(fans)}")


if __name__ == "__main__":
    main()
