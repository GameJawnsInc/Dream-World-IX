"""THE R4 SECTOR MAP -- the retrodiction registered in SECTOR-MAP.md (read it first; nothing here is a gate).

For every ~1u station along the donor massif's rim, read what the rock touched at HOME (stock disc-1
bytes) and place it with the deployed carve's own transform. Then score the result against the one
verdict ever given on the UNTOUCHED carry (the take-1 knoll arc failed; the rest passed).

Read-only: stock disc-1 donor blocks, the LIVE massif (only to re-derive the transform), and the
pre-massif host backup (the lawn the carry had to meet).

    py -X utf8 studies/overworld-topography/west-seam-continent/sector_map.py [--png OUT.png]
"""
import argparse
import json
import math
import statistics as S
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))
sys.path.insert(0, str(HERE))
from ff9mapkit.world import extract as X                  # noqa: E402
from ff9mapkit.world import interior as IN                # noqa: E402
from envelope_profile import read_loose, SITE_BLOCKS      # noqa: E402  (the LIVE site reader)
from rimwalk_stations import Ground                       # noqa: E402

MAIN_REPO = Path(r"C:\gd\Dream-World-IX")
HOST_PRE = MAIN_REPO / "backups" / "west-seam-continent" / "r4-pre.20260828-103332" / "Disc1"
DONOR = [(5, 15), (5, 16), (6, 15), (6, 16)]               # --donor 5-6,15-16 (cli _parse_block_rect order)
HOME_RING = [(bx, by) for bx in range(4, 8) for by in range(14, 18)]   # donor + neighbours: room to march
CENTRE = (1462.0, -462.0)                                  # the printed placement (every take)
SPAN = 1536.0
FAILED_BOX = (1418.0, -485.0, 1433.0, -469.0)              # x0, z0, x1, z1 -- the take-1 verdict
EDGE_PAD = 3.0
GRASS, FOREST = 0, 37
ROCK = frozenset({49})
TU, TV, PU, PV = 0.0625, 0.03125, 0.015625, 0.01953125
MARCH = list(range(1, 25))                                 # 1..24u outward
CLOSE_TOL = 0.5                                            # K: home ground within this of the host lawn
HIGH_MIN = 1.0                                             # H1b: home ground stays >= this above the lawn
E_MAX = 0.75                                               # H2


def read_ff9mesh(path, bx, by):
    """read_loose's decoder, for a backup tree (no 0_1 level)."""
    if not path.is_file():
        return []
    d = path.read_bytes()
    _, vc, _, fl = struct.unpack_from("<iiii", d, 4)
    off = 20
    verts = [struct.unpack_from("<fff", d, off + i * 12) for i in range(vc)]
    off += vc * 12 + (vc * 12 if fl & 1 else 0) + vc * 8
    topos = [(int(round(struct.unpack_from("<f", d, off + i * 16)[0])) >> 2) & 0x3F for i in range(vc)]
    out = []
    for t in range(vc // 3):
        i = t * 3
        p = [(bx * 64 + verts[i + k][0], verts[i + k][1], verts[i + k][2] - by * 64) for k in range(3)]
        out.append((p[0], p[1], p[2], topos[i]))
    return out


def tile(uvs):
    uc = sum(u for u, v in uvs) / 3
    vc = sum(v for u, v in uvs) / 3
    return int((vc - PV) / TV), int((uc - PU) / TU)


def in_box(x, z, box, pad=0.0):
    return box[0] - pad <= x <= box[2] + pad and box[1] - pad <= z <= box[3] + pad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--png", help="write a plan-view sector picture here (no atlas pixels)")
    ap.add_argument("--json", default=str(HERE / "sector_map.json"))
    a = ap.parse_args()

    # ---- the donor blob, exactly as the carve builds it ----
    B = IN._mountain_blob(DONOR, rock_topos=ROCK, alcove_box=None, disc=1, log=lambda *_: None)
    dV, dU, dtri, dtopo, d_edge = B["dV"], B["dU"], B["dtri"], B["dtopo"], B["d_edge"]
    blob, rim, c0, c1 = B["blob"], B["rim"], B["c_local"][0], B["c_local"][1]
    ta, tb = B["ta"], B["tb"]
    carried = set(blob) | set(B["sweep"])
    print(f"donor blob {len(blob)} tris (+{len(B['sweep'])} swept), rim {len(rim)} pts, "
          f"de-tilt {math.degrees(math.atan(math.hypot(ta, tb))):.2f} deg")

    def place(p, rot, dy):
        x, y, z = p
        yd = y - ta * (x - c0) - tb * (z - c1)
        dx, dz = x - c0, z - c1
        for _ in range(rot):
            dx, dz = dz, -dx
        return ((CENTRE[0] + dx) % SPAN, yd + dy, CENTRE[1] + dz)

    # ---- THE CALIBRATION: re-derive ROT + DY from the live mesh, or report nothing ----
    live_rock = {}
    for bx, by in SITE_BLOCKS:
        for p0, p1, p2, tp in read_loose(bx, by):
            if tp in ROCK:
                for q in (p0, p1, p2):
                    live_rock[(round(q[0] % SPAN, 2), round(q[2], 2))] = q[1]
    bverts = {tuple(dV[i]) for t in blob for i in dtri[t]}
    best = None
    for rot in range(4):
        dys = []
        for p in bverts:
            q = place(p, rot, 0.0)
            k = (round(q[0], 2), round(q[2], 2))
            if k in live_rock:
                dys.append(live_rock[k] - q[1])
        if best is None or len(dys) > len(best[1]):
            best = (rot, dys)
    rot, dys = best
    if len(dys) < 0.5 * len(bverts):
        sys.exit(f"CALIBRATION FAILED: only {len(dys)}/{len(bverts)} donor rock verts land on live rock")
    DY = S.median(dys)
    spread = sorted(abs(d - DY) for d in dys)
    rigid = sum(1 for s in spread if s < 1e-3)
    print(f"calibration: rot {rot * 90} deg, DY {DY:+.4f}, {len(dys)}/{len(bverts)} donor rock verts on live "
          f"rock, {rigid} within 1e-3 of rigid (p95 |dev| {spread[int(0.95 * len(spread))]:.4f})")
    if rigid < 0.5 * len(dys):
        sys.exit("CALIBRATION FAILED: the matched verts are not a rigid copy")

    # ---- the grounds: home (donor minus everything the carry took), host (pre-massif) ----
    home_tris = []
    for t, idx in enumerate(dtri):
        if t not in carried:
            p = [tuple(dV[i]) for i in idx]
            home_tris.append((p[0], p[1], p[2], dtopo[t]))
    for bx, by in HOME_RING:
        if (bx, by) in DONOR:
            continue
        try:
            bm = X.read_block(bx, by, disc=1)
        except Exception:
            continue
        ids = [((int(round(t4[0])) >> 2) & 0x3F) for t4 in bm.tangents]
        for (i, j, k) in bm.tris:
            p = [(bm.verts[n][0] + 64 * bx, bm.verts[n][1], bm.verts[n][2] - 64 * by) for n in (i, j, k)]
            home_tris.append((p[0], p[1], p[2], ids[i]))
    home = Ground(home_tris)
    host_tris = []
    for bx, by in SITE_BLOCKS:
        host_tris.extend(read_ff9mesh(HOST_PRE / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh", bx, by))
    host = Ground(host_tris)
    print(f"home ground tris {len(home_tris)}, pre-massif host tris {len(host_tris)}")

    rim_poly = [(p[0], p[2]) for p in rim]
    stations = []
    for i in range(len(rim)):
        pa, pb = rim[i], rim[(i + 1) % len(rim)]
        ek = tuple(sorted((pa, pb)))
        L = math.hypot(pb[0] - pa[0], pb[2] - pa[2])
        if L < 1e-6:
            continue
        outside = [t for t in d_edge.get(ek, []) if t not in blob]
        inside = [t for t in d_edge.get(ek, []) if t in blob]
        C = dtopo[outside[0]] if outside else None
        F = None
        if inside:
            r_, c_ = tile([tuple(dU[n]) for n in dtri[inside[0]]])
            F = bool(r_ == 10 and 6 <= c_ <= 9)
        ex, ez = (pb[0] - pa[0]) / L, (pb[2] - pa[2]) / L
        n_sub = max(1, int(math.ceil(L)))
        for s in range(n_sub):
            f = (s + 0.5) / n_sub
            hx, hz = pa[0] + ex * L * f, pa[2] + ez * L * f
            hy = pa[1] + (pb[1] - pa[1]) * f
            ox, oz = ez, -ex                                # a perpendicular; flip to point away from the blob
            if IN.pip(hx + ox * 0.5, hz + oz * 0.5, rim_poly):
                ox, oz = -ox, -oz
            wx, wy, wz = place((hx, hy, hz), rot, DY)
            h0 = host.top(wx, wz)
            E = None if h0 is None else wy - h0[0]
            prof, ptopo, crossed, K = {}, {}, [], None
            if E is not None and E <= CLOSE_TOL:
                K = 0
            for d in MARCH:
                t_ = home.top(hx + ox * d, hz + oz * d)
                if t_ is None:
                    continue
                q = place((hx + ox * d, t_[0], hz + oz * d), rot, DY)
                h = host.top(q[0], q[2])
                if h is None:
                    continue
                rel = q[1] - h[0]
                prof[d] = round(rel, 2)
                ptopo[d] = t_[1]
                if K is None:
                    crossed.append(t_[1])
                    if rel <= CLOSE_TOL:
                        K = d
            near = [prof[d] for d in (2, 4, 8) if d in prof]
            high = bool(len(near) == 3 and min(near) >= HIGH_MIN)
            label = ("FAILED" if in_box(wx, wz, FAILED_BOX)
                     else "EDGE" if in_box(wx, wz, FAILED_BOX, EDGE_PAD) else "PASSED")
            stations.append({"i": i, "w": [round(wx, 2), round(wz, 2)], "rim_y": round(wy, 2), "len": L / n_sub,
                             "label": label, "C": C, "F": F, "E": None if E is None else round(E, 2),
                             "prof": prof, "ptopo": ptopo, "K": K, "crossed": sorted(set(crossed)), "high": high,
                             "forest": C == FOREST, "home": [round(hx, 2), round(hz, 2)]})

    # ---- scoring, exactly as registered ----
    def length(rows):
        return sum(r["len"] for r in rows)

    def share(rows, pred):
        tot = length(rows)
        return (length([r for r in rows if pred(r)]) / tot) if tot else float("nan")

    by = defaultdict(list)
    for r in stations:
        by[r["label"]].append(r)
    print(f"\nrim length: FAILED {length(by['FAILED']):.1f}u, EDGE {length(by['EDGE']):.1f}u, "
          f"PASSED {length(by['PASSED']):.1f}u")
    for lab in ("FAILED", "EDGE", "PASSED"):
        rows = by[lab]
        if not rows:
            continue
        cc = Counter()
        for r in rows:
            cc["grass" if r["C"] == GRASS else "forest" if r["C"] == FOREST else f"topo{r['C']}"] += r["len"]
        Es = [r["E"] for r in rows if r["E"] is not None]
        Ks = [r["K"] for r in rows]
        print(f"\n{lab}:")
        print(f"  home contact C by length: " + ", ".join(f"{k} {v:.1f}u" for k, v in cc.most_common()))
        if Es:
            print(f"  E (rim above the pre-massif lawn): p10 {sorted(Es)[len(Es) // 10]:+.2f} "
                  f"p50 {S.median(Es):+.2f} p90 {sorted(Es)[9 * len(Es) // 10]:+.2f}")
        print(f"  K closure: 0 (at/below lawn) {share(rows, lambda r: r['K'] == 0):.0%}, <=6u "
              f"{share(rows, lambda r: r['K'] is not None and r['K'] <= 6):.0%}, never in 24u "
              f"{share(rows, lambda r: r['K'] is None):.0%}")
        print(f"  F donor fringe tile on the rim edge: {share(rows, lambda r: r['F'] is True):.0%}")
        print(f"  high approach (>= {HIGH_MIN}u over the lawn at 2/4/8u): {share(rows, lambda r: r['high']):.0%}")
        crossed = Counter()
        for r in rows:
            for t in r["crossed"]:
                crossed[t] += r["len"]
        print(f"  topographs crossed before closure (by length): {dict(crossed.most_common(6))}")

    scored_f = [r for r in by["FAILED"] if r["C"] in (GRASS, FOREST)]
    scored_p = [r for r in by["PASSED"] if r["C"] in (GRASS, FOREST)]
    nonbare = lambda r: r["forest"] or r["high"]           # noqa: E731
    h1f, h1p = share(scored_f, nonbare), share(scored_p, lambda r: not nonbare(r))
    h1a_f, h1a_p = share(scored_f, lambda r: r["forest"]), share(scored_p, lambda r: not r["forest"])
    h1b_f, h1b_p = share(scored_f, lambda r: r["high"]), share(scored_p, lambda r: not r["high"])
    ef = [r for r in by["FAILED"] if r["E"] is not None]
    ep = [r for r in by["PASSED"] if r["E"] is not None]
    h2f, h2p = share(ef, lambda r: r["E"] > E_MAX), share(ep, lambda r: r["E"] <= E_MAX)
    h3f, h3p = share(by["FAILED"], lambda r: r["F"] is False), share(by["PASSED"], lambda r: r["F"] is True)
    pkf = share(by["FAILED"], lambda r: r["K"] is None or r["K"] > 6 or FOREST in r["crossed"])
    pkp = share(by["PASSED"], lambda r: r["K"] is not None and r["K"] <= 6)
    verdict = lambda f, p: "HOLDS" if f >= 0.8 and p >= 0.8 else "FAILS"   # noqa: E731
    print("\n==== THE REGISTERED SCORE ====")
    print(f"H1  context  (forest OR high):  FAILED non-bare {h1f:.0%}, PASSED bare {h1p:.0%}  -> {verdict(h1f, h1p)}")
    print(f"    H1a forest contact alone:   FAILED {h1a_f:.0%}, PASSED not-forest {h1a_p:.0%}")
    print(f"    H1b high approach alone:    FAILED {h1b_f:.0%}, PASSED not-high {h1b_p:.0%}")
    print(f"H2  datum (E > {E_MAX}):          FAILED {h2f:.0%}, PASSED E <= {E_MAX} {h2p:.0%}  -> {verdict(h2f, h2p)}")
    print(f"H3  fringe:                     FAILED lacks {h3f:.0%}, PASSED has {h3p:.0%}  -> {verdict(h3f, h3p)}")
    print(f"P-K pricing:                    FAILED no close <=6u / forest {pkf:.0%}, PASSED closes <=6u {pkp:.0%}"
          f"  -> {verdict(pkf, pkp)}")

    # ==== VERIFICATION (post-registration; NOT part of the registered score) ====
    print("\n==== VERIFICATION (post-registration, not scored) ====")
    # (1) the chance baseline: slide an arc of the FAILED length around the rim -- how often would a
    #     verdict box that size land >= 80% on forest by accident?
    ring = sorted(stations, key=lambda r: (r["i"], r["home"]))
    cum, acc = [], 0.0
    for r in ring:
        cum.append(acc)
        acc += r["len"]
    total = acc
    flen = length(by["FAILED"])
    hits = trials = 0
    for k in range(len(ring)):
        s0 = cum[k]
        inside = [r for j, r in enumerate(ring) if (cum[j] - s0) % total < flen]
        trials += 1
        if share(inside, lambda r: r["forest"]) >= 0.8:
            hits += 1
    print(f"chance: an arc of {flen:.1f}u lands >= 80% on forest at {hits}/{trials} rim positions "
          f"({hits / trials:.1%})")
    # (2) where the forest contact sits, as runs along the ring
    runs, cur = [], None
    for r in ring:
        if r["forest"]:
            if cur is None:
                cur = [r]
                runs.append(cur)
            else:
                cur.append(r)
        else:
            cur = None
    if len(runs) > 1 and ring[0]["forest"] and ring[-1]["forest"]:
        runs[0] = runs.pop() + runs[0]
    for run in runs:
        labs = Counter()
        for r in run:
            labs[r["label"]] += r["len"]
        print(f"forest-contact run {length(run):5.1f}u from ({run[0]['w'][0]:.1f},{run[0]['w'][1]:.1f}) to "
              f"({run[-1]['w'][0]:.1f},{run[-1]['w'][1]:.1f}): " + ", ".join(f"{k} {v:.1f}u" for k, v in labs.items())
              + f"; rim E p50 {S.median([r['E'] for r in run if r['E'] is not None]):+.2f}")
    # (3) the outward profile along the forest run(s): height over the host lawn and what is crossed
    for run in runs:
        print(f"outward profile, forest run at ({run[0]['w'][0]:.0f},{run[0]['w'][1]:.0f}), every 4th station:")
        for r in run[::4]:
            cells = " ".join(f"{d}:{r['prof'][d]:+.1f}{'F' if r['ptopo'][d] == FOREST else 'g' if r['ptopo'][d] == GRASS else '#' + str(r['ptopo'][d])}"
                             for d in (1, 2, 4, 6, 8, 10, 12, 16, 20, 24) if d in r["prof"])
            print(f"  ({r['w'][0]:.1f},{r['w'][1]:.1f}) E {r['E']:+.2f} K {r['K']}: {cells}")
    # (4) the mechanism: does stock's forest stand UP off its ground? (a canopy rock meets at canopy height)
    edge_t = defaultdict(list)
    for t, (p0, p1, p2, tp) in enumerate(home_tris):
        for q0, q1 in ((p0, p1), (p1, p2), (p2, p0)):
            edge_t[tuple(sorted((IN.kk3(q0), IN.kk3(q1))))].append(t)
    fy, gy = [], []
    for e, ts in edge_t.items():
        tps = {home_tris[t][3] for t in ts}
        if FOREST in tps and GRASS in tps:
            for t in ts:
                ys = [home_tris[t][k][1] for k in range(3)]
                (fy if home_tris[t][3] == FOREST else gy).append(max(ys) - min(ys))
    f_tris = [t for t in home_tris if t[3] == FOREST]
    print(f"home forest: {len(f_tris)} tris in the donor ring; forest-grass edges {len([1 for e, ts in edge_t.items() if {home_tris[t][3] for t in ts} >= {FOREST, GRASS}])}")
    # the forest blob(s) touching the rim: connected topo-37 components, and their size / what bounds them
    fidx = [t for t, tri in enumerate(home_tris) if tri[3] == FOREST]
    fadj = defaultdict(set)
    for e, ts in edge_t.items():
        ff = [t for t in ts if home_tris[t][3] == FOREST]
        for a_ in ff:
            for b_ in ff:
                if a_ != b_:
                    fadj[a_].add(b_)
    rim_keys = {IN.kk3(p) for p in rim}
    seen = set()
    forest_blobs = []
    for s0 in fidx:
        if s0 in seen:
            continue
        comp, st = {s0}, [s0]
        while st:
            t = st.pop()
            for t2 in fadj[t]:
                if t2 not in comp:
                    comp.add(t2)
                    st.append(t2)
        seen |= comp
        touches = any(IN.kk3(home_tris[t][k]) in rim_keys for t in comp for k in range(3))
        if not touches:
            continue
        forest_blobs.append([home_tris[t] for t in comp])
        bound = Counter()
        side_y = defaultdict(list)                         # boundary class -> placed height over the host lawn
        for t in comp:
            tri = home_tris[t]
            for q0, q1 in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
                e = tuple(sorted((IN.kk3(q0), IN.kk3(q1))))
                others = [home_tris[t2][3] for t2 in edge_t[e] if t2 != t]
                L = math.hypot(q1[0] - q0[0], q1[2] - q0[2])
                cls = None
                if not others:
                    cls = "rim/open" if q0 in rim_keys or IN.kk3(q0) in rim_keys else "open"
                for o in others:
                    if o != FOREST:
                        cls = f"topo{o}"
                if cls is None:
                    continue
                bound[cls] += L
                for q in (q0, q1):
                    w = place(q, rot, DY)
                    h = host.top(w[0], w[2])
                    if h is not None:
                        side_y[cls].append(w[1] - h[0])
        for cls, ys_ in side_y.items():
            print(f"  forest edge vs {cls}: placed height over our lawn p10 {sorted(ys_)[len(ys_) // 10]:+.2f} "
                  f"p50 {S.median(ys_):+.2f} p90 {sorted(ys_)[9 * len(ys_) // 10]:+.2f}  (n {len(ys_)})")
        inner = [place(home_tris[t][k], rot, DY) for t in comp for k in range(3)]
        rel_in = [w[1] - h[0] for w in inner for h in [host.top(w[0], w[2])] if h is not None]
        print(f"  forest canopy (all verts) over our lawn: p50 {S.median(rel_in):+.2f}, max {max(rel_in):+.2f}")
        pts = [home_tris[t][k] for t in comp for k in range(3)]
        ys = [p[1] for p in pts]
        print(f"rim-touching forest blob: {len(comp)} tris, plan {max(p[0] for p in pts) - min(p[0] for p in pts):.0f}"
              f"x{max(p[2] for p in pts) - min(p[2] for p in pts):.0f}u, y {min(ys):.2f}..{max(ys):.2f}; "
              f"bounded by " + ", ".join(f"{k} {v:.1f}u" for k, v in bound.most_common()))

    out = {"calibration": {"rot": rot * 90, "DY": DY, "matched": len(dys), "rigid": rigid},
           "score": {"H1": [h1f, h1p], "H1a": [h1a_f, h1a_p], "H1b": [h1b_f, h1b_p], "H2": [h2f, h2p],
                     "H3": [h3f, h3p], "PK": [pkf, pkp]},
           "stations": stations}
    Path(a.json).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nwrote {a.json}")

    if a.png:
        from PIL import Image, ImageDraw
        xs = [r["w"][0] for r in stations]
        zs = [r["w"][1] for r in stations]
        x0, x1, z0, z1 = min(xs) - 30, max(xs) + 30, min(zs) - 30, max(zs) + 30
        sc = 8
        W, H = int((x1 - x0) * sc), int((z1 - z0) * sc)
        im = Image.new("RGB", (W, H), (24, 24, 28))
        dr = ImageDraw.Draw(im)
        px = lambda x, z: ((x - x0) * sc, (z1 - z) * sc)   # noqa: E731  -- north (+z) up
        for t in host_tris:
            cx = (t[0][0] + t[1][0] + t[2][0]) / 3
            cz = (t[0][2] + t[1][2] + t[2][2]) / 3
            if x0 <= cx <= x1 and z0 <= cz <= z1:
                y = (t[0][1] + t[1][1] + t[2][1]) / 3
                g = max(0, min(255, int(60 + 20 * y)))
                dr.polygon([px(p[0], p[2]) for p in t[:3]], fill=(g // 3, g // 2, g // 3))
        for fb in forest_blobs:                            # where the home forest lands if carried
            for t in fb:
                dr.polygon([px(*[place(q, rot, DY)[k] for k in (0, 2)]) for q in t[:3]],
                           fill=(30, 110, 45), outline=(60, 150, 70))
        bx0, bz0, bx1, bz1 = FAILED_BOX
        dr.rectangle([px(bx0, bz1), px(bx1, bz0)], outline=(255, 255, 255), width=2)
        for r in stations:
            col = ((40, 160, 60) if r["C"] == FOREST else (230, 200, 60) if r["C"] == GRASS else (120, 140, 230))
            if r["high"]:
                col = (230, 80, 60) if r["C"] != FOREST else (200, 60, 200)
            x, z = r["w"]
            cxp, czp = px(x, z)
            rad = 5 if r["label"] == "FAILED" else 3
            dr.ellipse([cxp - rad, czp - rad, cxp + rad, czp + rad], fill=col)
        dr.text((8, 8), "rim by HOME context -- yellow bare grass, green forest, blue other, "
                        "red high approach (non-forest), magenta forest+high; white box = take-1 failed arc; "
                        "green fill = the home forest blob placed by the carve transform",
                fill=(255, 255, 255))
        im.save(a.png)
        print(f"wrote {a.png}")


if __name__ == "__main__":
    main()
