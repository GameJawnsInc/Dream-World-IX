"""UAHO'S JULY RECORD AGAINST ITS STRETCHES -- registered in UAHO-JULY-STRETCHES.md (read it first).

Rebuild the July bench (a scratch re-mint of world-island r31 seed 42 at (160,-1246), then
carve_mountain(near=(160,-1246)) IN MEMORY, exactly like test_carve_mountain_reproduces_deployed_uaho_bench),
calibrate on the recorded placement (rot 0, centre (162,-1246), clearance 11.1u), then read every Uaho rim
station (context_screen classes) against the CARVED bench: notch vs outer rim, and the open lawn in front.

    py -X utf8 studies/overworld-topography/west-seam-continent/uaho_july_stretches.py
"""
import json
import math
import re
import statistics as S
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))
sys.path.insert(0, str(HERE))
from ff9mapkit.world import interior as IN                # noqa: E402
from ff9mapkit.world import mesh as M                     # noqa: E402
from context_screen import Soup, screen, classify         # noqa: E402
from rimwalk_stations import Ground                       # noqa: E402

SCRATCH = Path(r"C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX\4defe9bc-0f55-44e7-952d-bd74e20446f5"
               r"\scratchpad\bench-uaho\FF9CustomMap-world\FF9_Data\WorldMap\Disc1\0_1")
SEED = (160.0, -1246.0)
REC_CENTRE, REC_CLEAR = (162.0, -1246.0), 11.1
NOTCH_R = 12.0
LAWN_Y, LAWN_TOL = 3.2, 0.6


def tris_of(bm, bx, by):
    ids = [((int(round(t4[0])) >> 2) & 0x3F) for t4 in bm.tangents]
    V = [(v[0] + 64 * bx, v[1], v[2] - 64 * by) for v in bm.verts]
    return [(V[a], V[b], V[c], ids[a]) for (a, b, c) in bm.tris]


def main():
    p19 = SCRATCH / "r19" / "Block[2][19] Terrain.ff9mesh"
    p18 = SCRATCH / "r18" / "Block[2][18] Terrain.ff9mesh"
    bm19 = M.blockmesh_from_ff9mesh(p19, disc=1, x=2, y=19, part="terrain")
    bm18 = M.blockmesh_from_ff9mesh(p18, disc=1, x=2, y=18, part="terrain")
    soup = IN.soup_from_blocks({(2, 19): bm19})
    logs = []
    res = IN.carve_mountain(soup, near=SEED, log=lambda *a: logs.append(" ".join(str(x) for x in a)))
    line = next((l for l in logs if l.startswith("placement:")), "")
    m = re.search(r"rot (\d+)deg, blob centre -> \(([-\d.]+),([-\d.]+)\) \(clearance ([\d.]+)u\)", line)
    rot, cx, cz, clr = (int(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4))) if m else (None,) * 4
    ok = (m is not None and rot == 0 and math.hypot(cx - REC_CENTRE[0], cz - REC_CENTRE[1]) <= 2.0
          and abs(clr - REC_CLEAR) <= 1.5)
    print(f"CALIBRATION: rebuilt carve '{line}' vs the record rot 0 / centre {REC_CENTRE} / clearance {REC_CLEAR}u -> "
          f"{'PASS' if ok else 'FAIL -- nothing below is read'}")
    if not ok:
        print("\n".join(logs[-12:]))
        return
    carved = res["changed"][(2, 19)]
    bench = Ground(tris_of(carved, 2, 19) + tris_of(bm18, 2, 18))

    stock = Soup()
    st, B = screen(stock, [(0, 0)], alcove="uaho")
    c0, c1 = B["c_local"]
    # rot 0: bench = home - blob centre (the carve's c_local) + the placed centre; plan only
    for s in st:
        s["cls"] = classify(s)
        s["r"] = math.hypot(s["x"] - c0, s["z"] - c1)
        bx, bz = s["x"] - c0 + cx, s["z"] - c1 + cz
        ox, oz = s.get("ox"), s.get("oz")
        s["bench"] = (bx, bz)
    # outward normals were not kept by screen(): recompute them from the stations' own ring order
    n = len(st)
    for i, s in enumerate(st):
        a_, b_ = st[i - 1], st[(i + 1) % n]
        tx, tz = b_["x"] - a_["x"], b_["z"] - a_["z"]
        L = math.hypot(tx, tz) or 1.0
        ox, oz = tz / L, -tx / L
        rim_poly = [(q[0], q[2]) for q in B["rim"]]
        if IN.pip(s["x"] + ox * 0.5, s["z"] + oz * 0.5, rim_poly):
            ox, oz = -ox, -oz
        # open lawn in front, on the CARVED bench: grass within LAWN_TOL of the lawn, from the foot outward
        lawn, first, d = 0.0, None, 0.5
        while d <= 40.0:
            t = bench.top(s["bench"][0] + ox * d, s["bench"][1] + oz * d)
            kind = ("sea" if t is None else "rock" if t[1] in (49, 7, 62) else "coast" if t[1] == 58
                    else "grass" if t[1] == 0 else f"topo{t[1]}")
            if kind == "grass":
                if abs(t[0] - LAWN_Y) <= LAWN_TOL:
                    lawn += 0.5
            elif kind in ("coast", "sea"):
                first = first or kind
                break
            elif kind == "rock" and d > 2.0:
                first = first or "rock"
                break
            d += 0.5
        s["lawn"], s["stop"], s["stop_d"] = lawn, first, d

    def length(rows):
        return sum(r["len"] for r in rows)
    print(f"\nUaho rim {length(st):.1f}u, {n} stations; blob centre (home) ({c0:.1f},{c1:.1f}) -> bench ({cx},{cz})")
    groups = {"buried coastal rock (crock, E<=0.75)": [s for s in st if s["C"] == "crock" and s["E"] <= 0.75],
              "raised coastal rock (crock, E>0.75)": [s for s in st if s["C"] == "crock" and s["E"] > 0.75],
              "grass": [s for s in st if s["C"] == "grass"],
              "forest": [s for s in st if s["C"] == "forest"],
              "other": [s for s in st if s["C"] not in ("crock", "grass", "forest")]}
    for name, rows in groups.items():
        if not rows:
            continue
        outer = [s for s in rows if s["r"] >= NOTCH_R]
        faced = [s for s in outer if s["lawn"] >= 6.0]
        print(f"  {name:38s} {length(rows):5.1f}u: outer rim {100 * length(outer) / length(rows):3.0f}%; outer AND >= 6u open lawn "
              f"in front {100 * length(faced) / length(rows):3.0f}%; lawn in front p50 {S.median(s['lawn'] for s in rows):.1f}u; "
              f"stops at {dict(Counter(s['stop'] for s in rows))}")
    bc = groups["buried coastal rock (crock, E<=0.75)"]
    share = (length([s for s in bc if s["r"] >= NOTCH_R and s["lawn"] >= 6.0]) / length(bc)) if bc else 0.0
    print(f"\nP-U1 buried coastal rock on the outer rim facing >= 6u of open lawn: {100 * share:.0f}% of "
          f"{length(bc):.1f}u -> {'HOLDS' if share >= 0.7 else 'FAILS'}")
    (HERE / "uaho_july_stretches.json").write_text(json.dumps(
        {"calibration": {"line": line, "ok": ok},
         "stations": [{k: (list(v) if isinstance(v, tuple) else v) for k, v in s.items() if k in
                       ("x", "z", "len", "C", "E", "cls", "r", "bench", "lawn", "stop", "stop_d")} for s in st]},
        indent=1, default=float), encoding="utf-8")


if __name__ == "__main__":
    main()
