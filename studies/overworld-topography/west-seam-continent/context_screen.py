"""THE CONTEXT SCREEN + the forest-or-datum test -- registered in FOREST-OR-DATUM.md (read it first).

Per ~1u rim station of a carry unit (`interior._mountain_blob`, exactly what world-mountain carves):
  C  home contact (global stock soup: grass / forest / crock(58) / topoN / open)
  E  seat excess: de-tilted rim height minus the de-tilted rim-ring MEDIAN (the carve's flat-lawn seat)
  R  home approach: grass-only home ground outward (2/4/8u, and the nearest grass within 24u), minus the rim
Scores H-forest / H-datum / H-context on the two verdict-bearing carries (horseshoe take 1, Uaho July), then
screens any donor.

    py -X utf8 studies/overworld-topography/west-seam-continent/context_screen.py            # the study
    py -X utf8 studies/overworld-topography/west-seam-continent/context_screen.py --donor 12,16-17
"""
import argparse
import json
import math
import statistics as S
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))
sys.path.insert(0, str(HERE))
from ff9mapkit.world import extract as X                  # noqa: E402
from ff9mapkit.world import interior as IN                # noqa: E402
from rimwalk_stations import Ground                       # noqa: E402

FOREST, GRASS, CROCK = {36, 37}, 0, 58
E_MAX = 0.75
FAILED_BOX = (1418.0, -485.0, 1433.0, -469.0)
EDGE_PAD = 3.0
CENTRE = (1462.0, -462.0)
QUALIFIED = {"uaho": ([(0, 0)], "uaho"), "crag": ([(10, 5), (10, 6)], None),
             "horseshoe": ([(5, 15), (5, 16), (6, 15), (6, 16)], None), "comp20": ([(12, 16), (12, 17)], None)}


def parse_rect(spec):
    xs, ys = spec.split(",")
    rng = lambda s: list(range(int(s.split("-")[0]), int(s.split("-")[-1]) + 1))   # noqa: E731
    return [(x, y) for x in rng(xs) for y in rng(ys)]


class Soup:
    """Every disc-1 terrain tri in one position-keyed soup (contacts across donor-block borders)."""

    def __init__(self):
        k3 = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))           # noqa: E731
        self.pos, self.P, self.T, self.TOPO = {}, [], [], []
        for bx, by in X.list_blocks(disc=1):
            try:
                bm = X.read_block(bx, by, disc=1)
            except Exception:
                continue
            ids = [((int(round(t4[0])) >> 2) & 0x3F) for t4 in bm.tangents]
            loc = []
            for v in bm.verts:
                w = (v[0] + 64 * bx, v[1], v[2] - 64 * by)
                k = k3(w)
                if k not in self.pos:
                    self.pos[k] = len(self.P)
                    self.P.append(w)
                loc.append(self.pos[k])
            for (a, b, c) in bm.tris:
                self.T.append((loc[a], loc[b], loc[c]))
                self.TOPO.append(ids[a])
        self.edges = defaultdict(list)
        for t, (a, b, c) in enumerate(self.T):
            for i, j in ((a, b), (b, c), (c, a)):
                self.edges[(min(i, j), max(i, j))].append(t)
        self.ground = Ground([(self.P[a], self.P[b], self.P[c], self.TOPO[t]) for t, (a, b, c) in enumerate(self.T)])
        self.k3 = k3

    def tri_key(self, t):
        return frozenset(self.k3(self.P[n]) for n in self.T[t])


def screen(soup, blocks, alcove=None, log=lambda *_: None):
    alc = IN.UAHO_ALCOVE if alcove == "uaho" else None
    B = IN._mountain_blob(blocks, rock_topos=frozenset({49}), alcove_box=alc, disc=1, log=log)
    dV, dtri, rim, blob = B["dV"], B["dtri"], B["rim"], B["blob"]
    c0, c1 = B["c_local"]
    ta, tb = B["ta"], B["tb"]
    unit = {frozenset(IN.kk3(dV[i]) for i in dtri[t]) for t in set(blob) | set(B["sweep"])}
    det = lambda x, y, z: y - ta * (x - c0) - tb * (z - c1)                         # noqa: E731
    rim_med = S.median(det(*p) for p in rim)
    rim_poly = [(p[0], p[2]) for p in rim]

    def home_top(x, z):
        """top stock ground at (x, z) EXCLUDING the carry unit (its rock would answer first)."""
        best = None
        x %= 1536.0
        if z > 0:
            z -= 1280.0
        for i in soup.ground.grid.get((int(x // 4), int(z // 4)), ()):
            p0, p1, p2, tp = soup.ground.tris[i]
            if tp == 49:
                continue
            d = (p1[2] - p2[2]) * (p0[0] - p2[0]) + (p2[0] - p1[0]) * (p0[2] - p2[2])
            if abs(d) < 1e-9:
                continue
            w0 = ((p1[2] - p2[2]) * (x - p2[0]) + (p2[0] - p1[0]) * (z - p2[2])) / d
            w1 = ((p2[2] - p0[2]) * (x - p2[0]) + (p0[0] - p2[0]) * (z - p2[2])) / d
            w2 = 1 - w0 - w1
            if min(w0, w1, w2) < -1e-6:
                continue
            y = w0 * p0[1] + w1 * p1[1] + w2 * p2[1]
            if best is None or y > best[0]:
                best = (y, tp)
        return best

    st = []
    for i in range(len(rim)):
        pa, pb = rim[i], rim[(i + 1) % len(rim)]
        L = math.hypot(pb[0] - pa[0], pb[2] - pa[2])
        if L < 1e-6:
            continue
        ia, ib = soup.pos.get(soup.k3(pa)), soup.pos.get(soup.k3(pb))
        across = []
        if ia is not None and ib is not None:
            across = [t for t in soup.edges.get((min(ia, ib), max(ia, ib)), []) if soup.tri_key(t) not in unit]
        tps = {soup.TOPO[t] for t in across}
        C = ("open" if not tps else "forest" if tps & FOREST else "grass" if GRASS in tps
             else "crock" if CROCK in tps else f"topo{sorted(tps)[0]}")
        ex, ez = (pb[0] - pa[0]) / L, (pb[2] - pa[2]) / L
        n = max(1, int(math.ceil(L)))
        for s in range(n):
            f = (s + 0.5) / n
            x, z, y = pa[0] + ex * L * f, pa[2] + ez * L * f, pa[1] + (pb[1] - pa[1]) * f
            ox, oz = ez, -ex
            if IN.pip(x + ox * 0.5, z + oz * 0.5, rim_poly):
                ox, oz = -ox, -oz
            E = det(x, y, z) - rim_med
            R = {}
            near = None
            d = 0.5
            while d <= 24.0:
                q = home_top(x + ox * d, z + oz * d)
                if q is not None and q[1] == GRASS:
                    rel = det(x + ox * d, q[0], z + oz * d) - det(x, y, z)
                    if near is None:
                        near = (d, rel)
                    for dd in (2.0, 4.0, 8.0):
                        if abs(d - dd) < 1e-6:
                            R[dd] = rel
                d += 0.5
            st.append({"x": x, "z": z, "len": L / n, "C": C, "E": E, "R": R, "near": near})
    return st, B


def classify(s):
    """the screen's classes (FOREST-OR-DATUM.md). SAFE-SEAT is the post-registration mechanism extension
    (any contact at/below the seat = free-base burial); the REGISTERED SAFE is grass-only."""
    raised = s["E"] > E_MAX
    if not raised:
        return "SAFE" if s["C"] == "grass" else "SAFE-SEAT"
    if s["C"] == "forest":
        return "FOREST"
    if s["C"] == "grass":
        r2 = s["R"].get(2.0)
        return "SAFE-RISING" if (r2 is not None and r2 >= -1.0) else "DATUM"
    return "UNTESTED"


def length(rows):
    return sum(r["len"] for r in rows)


def runs_of(st, cls_set):
    out, cur = [], []
    for s in st + st[:1]:
        if s["cls"] in cls_set:
            cur.append(s)
        elif cur:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def report(name, st):
    tot = length(st)
    by = Counter()
    for s in st:
        by[s["cls"]] += s["len"]
    print(f"  {name}: rim {tot:.1f}u -> " + ", ".join(f"{k} {100 * v / tot:.1f}%" for k, v in by.most_common()))
    for run in runs_of(st, {"FOREST", "DATUM", "UNTESTED"}):
        if length(run) >= 3.0:
            print(f"     flagged run {length(run):5.1f}u {Counter(s['cls'] for s in run).most_common(1)[0][0]:8s} "
                  f"contact {Counter(s['C'] for s in run).most_common(1)[0][0]:6s} E p50 {S.median(s['E'] for s in run):+.2f}"
                  f" at home ({run[0]['x']:.0f},{run[0]['z']:.0f})..({run[-1]['x']:.0f},{run[-1]['z']:.0f})")
    return by, tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--donor", help="screen one donor rect (CLI spec), skipping the study")
    a = ap.parse_args()
    soup = Soup()
    if a.donor:
        st, _ = screen(soup, parse_rect(a.donor))
        for s in st:
            s["cls"] = classify(s)
        report(a.donor, st)
        return

    # ==== the study: horseshoe (labelled) + Uaho (all passed) ====
    cal = json.loads((HERE / "sector_map.json").read_text(encoding="utf-8"))["calibration"]
    hs, Bh = screen(soup, QUALIFIED["horseshoe"][0])
    c0, c1 = Bh["c_local"]
    ta, tb = Bh["ta"], Bh["tb"]
    rot = cal["rot"] // 90

    def placed_xz(x, z):
        dx, dz = x - c0, z - c1
        for _ in range(rot):
            dx, dz = dz, -dx
        return CENTRE[0] + dx, CENTRE[1] + dz
    for s in hs:
        wx, wz = placed_xz(s["x"], s["z"])
        x0, z0, x1, z1 = FAILED_BOX
        s["label"] = ("FAILED" if x0 <= wx <= x1 and z0 <= wz <= z1 else
                      "EDGE" if x0 - EDGE_PAD <= wx <= x1 + EDGE_PAD and z0 - EDGE_PAD <= wz <= z1 + EDGE_PAD else "PASSED")
        s["cls"] = classify(s)
    ua, _ = screen(soup, QUALIFIED["uaho"][0], alcove="uaho")
    for s in ua:
        s["label"] = "PASSED"
        s["cls"] = classify(s)

    # cross-check E on the horseshoe vs the sector map (same stations, its E measured against the real lawn)
    sm = json.loads((HERE / "sector_map.json").read_text(encoding="utf-8"))["stations"]
    if len(sm) == len(hs):
        diffs = [abs(s["E"] - q["E"]) for s, q in zip(hs, sm) if q["E"] is not None]
        print(f"CROSS-CHECK horseshoe E vs the sector map's E: {len(diffs)} stations, |diff| p50 {S.median(diffs):.2f} "
              f"p90 {sorted(diffs)[int(0.9 * len(diffs))]:.2f}u (the sector map's lawn vs the rim-median seat)")
    else:
        print(f"CROSS-CHECK: station counts differ ({len(hs)} vs {len(sm)}) -- compare by distribution only")

    def share(rows, pred):
        t = length(rows)
        return length([r for r in rows if pred(r)]) / t if t else float("nan")
    hp = [s for s in hs if s["label"] == "PASSED"]
    hf = [s for s in hs if s["label"] == "FAILED"]
    print("\n==== THE REGISTERED SCORE ====")
    p1 = share(ua, lambda s: s["C"] == "grass" and s["E"] > E_MAX)
    print(f"P1  Uaho raised (E > {E_MAX}) GRASS stretches: {100 * p1:.1f}% of its rim ({length(ua):.0f}u) -> "
          f"{'HOLDS: H-datum falsified as a sufficient cause' if p1 >= 0.10 else 'FAILS: the discriminant is unavailable'}")
    print(f"    Uaho E: p10 {sorted(s['E'] for s in ua)[len(ua) // 10]:+.2f} p50 {S.median(s['E'] for s in ua):+.2f} "
          f"p90 {sorted(s['E'] for s in ua)[9 * len(ua) // 10]:+.2f} max {max(s['E'] for s in ua):+.2f}; raised by contact: "
          + str({k: round(v, 1) for k, v in Counter({c: length([s for s in ua if s['C'] == c and s['E'] > E_MAX])
                                                       for c in {s['C'] for s in ua}}).items() if v}))
    raised_hp = [s for s in hp if s["E"] > E_MAX]
    print(f"P2  horseshoe PASSED raised stretches: {length(raised_hp):.1f}u ({100 * share(hp, lambda s: s['E'] > E_MAX):.1f}% "
          f"of PASSED); by contact {dict(Counter(s['C'] for s in raised_hp))} -> "
          f"{'HOLDS' if raised_hp and share(raised_hp, lambda s: s['C'] == 'grass') >= 0.8 else 'FAILS'}")
    rg = [s for s in hs + ua if s["C"] == "grass" and s["E"] > E_MAX]
    meet = share(rg, lambda s: s["R"].get(2.0) is not None and s["R"][2.0] >= -1.0)
    ff = [s for s in hf if s["C"] == "forest"]
    below = share(ff, lambda s: s["near"] is not None and s["near"][1] <= -1.0)
    print(f"P3  raised grass stretches (both donors, {length(rg):.1f}u): home grass at 2u within 1.0u of the rim on "
          f"{100 * meet:.0f}%; horseshoe forest stretch ({length(ff):.1f}u): nearest home grass >= 1.0u BELOW the rim on "
          f"{100 * below:.0f}% -> {'HOLDS' if meet >= 0.8 and below >= 0.8 else 'FAILS'}")
    if rg:
        r2s = [s["R"][2.0] for s in rg if 2.0 in s["R"]]
        if r2s:
            print(f"    raised-grass R(2u) p10 {sorted(r2s)[len(r2s) // 10]:+.2f} p50 {S.median(r2s):+.2f}; forest-stretch "
                  f"nearest grass: d p50 {S.median(s['near'][0] for s in ff if s['near']):.1f}u rel p50 "
                  f"{S.median(s['near'][1] for s in ff if s['near']):+.2f}")
    # how each hypothesis would have predicted the two verdicts
    def pred_rate(pred):
        flagged_failed = share(hf, pred)
        flagged_passed_h = share(hp, pred)
        flagged_uaho = share(ua, pred)
        return flagged_failed, flagged_passed_h, flagged_uaho
    for name, pred in (("H-forest", lambda s: s["C"] == "forest"),
                       ("H-datum", lambda s: s["E"] > E_MAX),
                       ("H-context", lambda s: s["cls"] in ("FOREST", "DATUM"))):
        f1, f2, f3 = pred_rate(pred)
        print(f"    {name:9s} flags: horseshoe FAILED {100 * f1:.0f}% / horseshoe PASSED {100 * f2:.0f}% / Uaho (passed) {100 * f3:.0f}%")

    print("\n==== THE SCREEN -- CALIBRATION FIRST ====")
    byh, toth = report("horseshoe", hs)
    forest_run = max((length(r) for r in runs_of(hs, {"FOREST"})), default=0.0)
    byu, totu = report("uaho", ua)
    safe_u = (byu["SAFE"] + byu["SAFE-RISING"]) / totu
    safe_u_ext = safe_u + byu["SAFE-SEAT"] / totu
    cal_ok = 26.0 <= forest_run <= 32.0 and safe_u >= 0.9
    cal_ext = 26.0 <= forest_run <= 32.0 and safe_u_ext >= 0.9
    print(f"  CALIBRATION: horseshoe FOREST run {forest_run:.1f}u (want 29 +- 3); Uaho SAFE {100 * safe_u:.0f}% registered "
          f"(want >= 90) / {100 * safe_u_ext:.0f}% with SAFE-SEAT -> registered {'PASS' if cal_ok else 'FAIL'}, "
          f"extension {'PASS' if cal_ext else 'FAIL'}")
    print("\n==== THE SCREEN -- THE OTHER QUALIFIED DONORS ====")
    out = {"horseshoe": dict(byh), "uaho": dict(byu)}
    for name in ("crag", "comp20"):
        try:
            st, _ = screen(soup, QUALIFIED[name][0])
        except Exception as err:
            print(f"  {name}: no carry unit ({str(err)[:120]})")
            continue
        for s in st:
            s["cls"] = classify(s)
        by, _ = report(name, st)
        out[name] = dict(by)
    (HERE / "context_screen.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nwrote {HERE / 'context_screen.json'}")


if __name__ == "__main__":
    main()
