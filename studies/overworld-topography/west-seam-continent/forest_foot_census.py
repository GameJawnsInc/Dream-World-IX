"""THE FOREST-FOOT CENSUS -- registered in FOREST-FOOT-CENSUS.md (read it first; nothing here is a gate).

Every disc-1 terrain block, welded into one soup by world position. Massifs = topo-49 rock components
(>= 40 tris); forests = topo-36/37 blobs. Measures, per massif, where the rim meets forest vs grass and
how high (P1/P1b + the screen), and per forest blob how stock builds its outer edge (P2 weld, P3 rise,
P4 uv pin, P5 the ground around it). Calibration first: the horseshoe (R4's donor) must reproduce the
sector map, or nothing else is reported.

    py -X utf8 studies/overworld-topography/west-seam-continent/forest_foot_census.py
"""
import json
import math
import statistics as S
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))
sys.path.insert(0, str(HERE))
from ff9mapkit.world import extract as X                  # noqa: E402
from rimwalk_stations import Ground                       # noqa: E402

ROCK = {49}
NOT_GROUND = {49, 7, 62, 58}                               # massif + coastal rock: not a curtain's ground
FOREST = {36, 37}
GRASS = 0
MIN_MASSIF = 40
SPAN = 1536.0
ATLAS_H = 4096                                             # res(1_24)_terrain.png is 2048 x 4096
QUALIFIED = {"uaho": [(0, 0)], "crag": [(10, 5), (10, 6)],
             "horseshoe": [(5, 15), (5, 16), (6, 15), (6, 16)], "comp20": [(12, 16), (12, 17)]}


def pct(vals, p, w=None):
    """Percentile; length-weighted when w is given."""
    if not vals:
        return float("nan")
    if w is None:
        v = sorted(vals)
        return v[min(len(v) - 1, int(p / 100 * len(v)))]
    pairs = sorted(zip(vals, w))
    tot = sum(w)
    acc = 0.0
    for v, ww in pairs:
        acc += ww
        if acc >= p / 100 * tot:
            return v
    return pairs[-1][0]


def main():
    # ---- the soup ----
    pos_id, P, UV = {}, [], []
    T, TOPO, BLK = [], [], []
    for bx, by in X.list_blocks(disc=1):
        try:
            bm = X.read_block(bx, by, disc=1)
        except Exception:
            continue
        ids = [((int(round(t4[0])) >> 2) & 0x3F) for t4 in bm.tangents]
        loc = []
        for n, v in enumerate(bm.verts):
            w = (v[0] + 64 * bx, v[1], v[2] - 64 * by)
            k = (round(w[0], 3), round(w[1], 3), round(w[2], 3))
            if k not in pos_id:
                pos_id[k] = len(P)
                P.append(w)
                UV.append(tuple(bm.uvs[n]))
            loc.append(pos_id[k])
        for (a, b, c) in bm.tris:
            T.append((loc[a], loc[b], loc[c]))
            TOPO.append(ids[a])
            BLK.append((bx, by))
    P = np.asarray(P)
    print(f"soup: {len(T)} tris, {len(P)} positions")

    # NB: UV per POSITION is the first entry's uv -- stock does not share vertex entries, and a curtain's
    # base position can carry different uvs in the ground tri and the forest tri. For P4 the forest tri's
    # OWN uvs are needed, so they are re-read per tri below.
    tri_uv = {}

    edges = defaultdict(list)
    for t, (a, b, c) in enumerate(T):
        for i, j in ((a, b), (b, c), (c, a)):
            edges[(min(i, j), max(i, j))].append(t)

    def comps(member):
        seen, out = set(), []
        adj = defaultdict(set)
        for e, ts in edges.items():
            m = [t for t in ts if member(t)]
            for x in m:
                for y in m:
                    if x != y:
                        adj[x].add(y)
        for t in range(len(T)):
            if not member(t) or t in seen:
                continue
            c, st = {t}, [t]
            while st:
                u = st.pop()
                for v2 in adj[u]:
                    if v2 not in c:
                        c.add(v2)
                        st.append(v2)
            seen |= c
            out.append(c)
        return out

    massifs = [c for c in comps(lambda t: TOPO[t] in ROCK) if len(c) >= MIN_MASSIF]
    blobs = comps(lambda t: TOPO[t] in FOREST)
    blob_of = {}
    for bi, c in enumerate(blobs):
        for t in c:
            blob_of[t] = bi
    print(f"massifs (topo 49, >= {MIN_MASSIF} tris): {len(massifs)}; forest blobs: {len(blobs)}")

    def plen(i, j):
        return math.hypot(P[i][0] - P[j][0], P[i][2] - P[j][2])

    def on_border(i, j):
        for ax in (0, 2):
            a, b = P[i][ax] % 64.0, P[j][ax] % 64.0
            if min(a, 64 - a) < 1e-3 and min(b, 64 - b) < 1e-3 and abs(P[i][ax] - P[j][ax]) < 1e-3:
                return True
        return False

    def once_edges(comp):
        cnt = Counter()
        for t in comp:
            a, b, c = T[t]
            for i, j in ((a, b), (b, c), (c, a)):
                cnt[(min(i, j), max(i, j))] += 1
        return [e for e, n in cnt.items() if n == 1]

    # ---- forest blob outer edges: base heights (for P1b), weld (P2), rise (P3), pin (P4), ground (P5) ----
    blob_base = defaultdict(list)                          # blob -> [(x, z, y)] curtain-base positions
    curtain = []                                           # per ground-boundary edge of a forest blob
    open_nonborder = open_border = 0.0
    for bi, c in enumerate(blobs):
        for e in once_edges(c):
            i, j = e
            L = plen(i, j)
            inside = [t for t in edges[e] if t in c]
            across = [t for t in edges[e] if t not in c]
            if across and all(TOPO[t] in NOT_GROUND for t in across):
                continue                                   # rock contact: P1's business, not a curtain
            if not across:
                if on_border(i, j):
                    open_border += L
                    continue
                open_nonborder += L
            base_y = (P[i][1] + P[j][1]) / 2
            t_in = inside[0]
            top = max(P[k][1] for k in T[t_in])
            for k in (i, j):
                blob_base[bi].append((P[k][0], P[k][2], P[k][1]))
            curtain.append({"blob": bi, "L": L, "welded": bool(across), "rise": top - base_y,
                            "tri": t_in, "e": e, "across": across})
    weld_len = sum(r["L"] for r in curtain if r["welded"])
    print(f"forest outer edges: {len(curtain)} ({sum(r['L'] for r in curtain):.0f}u); welded {weld_len:.0f}u, "
          f"open non-border {open_nonborder:.1f}u, open on a block border {open_border:.1f}u (excluded)")

    # ---- per massif ----
    def unwrap(xs, ref):
        return [x - SPAN if x - ref > SPAN / 2 else x + SPAN if ref - x > SPAN / 2 else x for x in xs]

    rows = []
    for mi, c in enumerate(massifs):
        oe = once_edges(c)
        blks = sorted({BLK[t] for t in c})
        cls_len = Counter()
        gv, fv, fcontacts = set(), set(), []
        for e in oe:
            i, j = e
            L = plen(i, j)
            across = [t for t in edges[e] if t not in c]
            if not across:
                cls = "open"
            else:
                tps = {TOPO[t] for t in across}
                cls = ("forest" if tps & FOREST else "grass" if GRASS in tps else f"topo{sorted(tps)[0]}")
            cls_len[cls] += L
            if cls == "grass":
                gv.update(e)
            elif cls == "forest":
                fv.update(e)
                ft = next(t for t in across if TOPO[t] in FOREST)
                fcontacts.append((e, L, ft))
        rim_len = sum(cls_len.values())
        row = {"id": mi, "tris": len(c), "blocks": blks, "rim": round(rim_len, 1),
               "len": {k: round(v, 1) for k, v in cls_len.items()},
               "forest_share": cls_len["forest"] / rim_len if rim_len else 0.0}
        ref = P[next(iter(gv or fv or {T[next(iter(c))][0]}))][0]
        if len(gv) >= 3:
            g = sorted(gv)
            gx = unwrap([P[k][0] for k in g], ref)
            A = np.array([[x, P[k][2], 1.0] for x, k in zip(gx, g)])
            yv = np.array([P[k][1] for k in g])
            coef, *_ = np.linalg.lstsq(A, yv, rcond=None)
            res_g = yv - A @ coef
            row["grass_spread"] = round(float(pct(list(res_g), 90) - pct(list(res_g), 10)), 2)
            if fv:
                f = sorted(fv)
                fx = unwrap([P[k][0] for k in f], ref)
                Af = np.array([[x, P[k][2], 1.0] for x, k in zip(fx, f)])
                res_f = np.array([P[k][1] for k in f]) - Af @ coef
                row["delta"] = round(float(np.median(res_f)), 2)
        # P1b: rim over the forest blob's own curtain base within 24u; and rim vs the canopy tri's top
        lifts, lw, tops = [], [], []
        for (i, j), L, ft in fcontacts:
            mx, mz, my = (P[i][0] + P[j][0]) / 2, (P[i][2] + P[j][2]) / 2, (P[i][1] + P[j][1]) / 2
            base = [y for x, z, y in blob_base.get(blob_of[ft], [])
                    if math.hypot(unwrap([x], mx)[0] - mx, z - mz) <= 24.0]
            tops.append(my - max(P[k][1] for k in T[ft]))
            if base:
                lifts.append(my - S.median(base))
                lw.append(L)
        if lifts:
            row["lift_p50"] = round(pct(lifts, 50, lw), 2)
            row["lift_ge15"] = sum(w for v, w in zip(lifts, lw) if v >= 1.5) / sum(lw)
            row["lift_n"] = (lifts, lw)
            row["rim_minus_canopy_top_p50"] = round(S.median(tops), 2)
        for name, qb in QUALIFIED.items():
            if any(b in qb for b in blks) and len(c) >= 60:
                row.setdefault("qualified", []).append(name)
        rows.append(row)

    # ---- CALIBRATION: the horseshoe must reproduce the sector map ----
    hs = [r for r in rows if "horseshoe" in r.get("qualified", [])]
    hs.sort(key=lambda r: -r["tris"])
    print("\n==== CALIBRATION (the horseshoe vs the sector map: forest 29 +- 3u, delta +1.2..+1.8) ====")
    ok = False
    for r in hs[:2]:
        print(f"  massif {r['id']}: {r['tris']} tris, blocks {r['blocks']}, rim {r['rim']}u, contact {r['len']}, "
              f"delta {r.get('delta')}, lift p50 {r.get('lift_p50')}")
    if hs:
        r = hs[0]
        ok = 26.0 <= r["len"].get("forest", 0) <= 32.0 and r.get("delta") is not None and 1.2 <= r["delta"] <= 1.8
    print(f"  -> {'CALIBRATED' if ok else 'CALIBRATION FAILED -- nothing below is a finding'}")

    # ---- P1 / P1b ----
    q = [r for r in rows if r["len"].get("forest", 0) >= 4 and r["len"].get("grass", 0) >= 8 and "delta" in r]
    ds = [r["delta"] for r in q]
    print(f"\n==== P1 THE CANOPY-FOOT LAW (paired): {len(q)} massifs with >= 4u forest + >= 8u grass contact ====")
    if ds:
        pos = sum(1 for d in ds if d > 0) / len(ds)
        print(f"  delta > 0 in {pos:.0%}; median delta {S.median(ds):+.2f}u (p10 {pct(ds, 10):+.2f}, p90 {pct(ds, 90):+.2f})"
              f"  -> {'HOLDS' if pos >= 0.75 and S.median(ds) >= 1.0 else 'FAILS'}")
    L_all, W_all = [], []
    for r in rows:
        if "lift_n" in r:
            L_all += r["lift_n"][0]
            W_all += r["lift_n"][1]
    if L_all:
        share = sum(w for v, w in zip(L_all, W_all) if v >= 1.5) / sum(W_all)
        print(f"P1b local: rim over the forest's own curtain base, by length: p10 {pct(L_all, 10, W_all):+.2f} "
              f"p50 {pct(L_all, 50, W_all):+.2f} p90 {pct(L_all, 90, W_all):+.2f}; >= +1.5u on {share:.0%} "
              f"of {sum(W_all):.0f}u  -> {'HOLDS' if share >= 0.75 else 'FAILS'}")
    tops_all = [r["rim_minus_canopy_top_p50"] for r in rows if "rim_minus_canopy_top_p50" in r]
    if tops_all:
        print(f"  rim minus the touching canopy tri's top (per massif p50): median {S.median(tops_all):+.2f}u")

    # ---- P2 / P3 / P4 ----
    tot = weld_len + open_nonborder
    print(f"\n==== P2 curtain welded: {weld_len / tot:.2%} of {tot:.0f}u (non-border)"
          f"  -> {'HOLDS' if weld_len / tot >= 0.99 else 'FAILS'}")
    rises = [r["rise"] for r in curtain]
    rw = [r["L"] for r in curtain]
    short = sum(w for v, w in zip(rises, rw) if v <= 1.4) / sum(rw)
    p05 = pct(rises, 5, rw)
    print(f"==== P3 curtain rise (by length): p05 {p05:.2f} p10 {pct(rises, 10, rw):.2f} p50 {pct(rises, 50, rw):.2f} "
          f"p90 {pct(rises, 90, rw):.2f}; <= 1.4u on {short:.1%}  -> {'HOLDS' if p05 >= 1.6 and short < 0.05 else 'FAILS'}")
    # P4: the forest tri's OWN uvs, re-read per block (positions do not share vertex entries)
    need = defaultdict(set)
    for r in curtain:
        need[BLK[r["tri"]]].add(r["tri"])
    tri_index = defaultdict(dict)                          # block -> soup tri -> local tri index
    base_off = {}
    off = 0
    for bx, by in X.list_blocks(disc=1):
        try:
            bm = X.read_block(bx, by, disc=1)
        except Exception:
            continue
        base_off[(bx, by)] = off
        if (bx, by) in need:
            for t in need[(bx, by)]:
                lt = t - off
                a, b, c = bm.tris[lt]
                tri_uv[t] = {pos: tuple(bm.uvs[n]) for pos, n in zip(T[t], (a, b, c))}
        off += len(bm.tris)
    bv, tv, pw = [], [], []
    for r in curtain:
        uvm = tri_uv.get(r["tri"])
        if not uvm:
            continue
        i, j = r["e"]
        top_k = next(k for k in T[r["tri"]] if k not in (i, j))
        bv.append(round((uvm[i][1] + uvm[j][1]) / 2 * ATLAS_H))
        tv.append(round(uvm[top_k][1] * ATLAS_H))
        pw.append(r["L"])

    def mode_share(vals, w):
        acc = Counter()
        for v, ww in zip(vals, w):
            acc[v] += ww
        top = acc.most_common(4)
        tot_ = sum(w)
        near = sum(ww for v, ww in zip(vals, w) if abs(v - top[0][0]) <= 0.5)
        return near / tot_, [(v, round(x / tot_, 3)) for v, x in top]

    sb, mb = mode_share(bv, pw)
    st_, mt = mode_share(tv, pw)
    print(f"==== P4 curtain uv pin: base v within 0.5 texel of its mode on {sb:.0%} (modes {mb}); "
          f"top v on {st_:.0%} (modes {mt})  -> {'HOLDS' if sb >= 0.9 and st_ >= 0.9 else 'FAILS'}")

    # ---- P5: the ground around each forest ----
    ground = Ground([(tuple(P[a]), tuple(P[b]), tuple(P[c]), TOPO[t]) for t, (a, b, c) in enumerate(T)
                     if TOPO[t] not in FOREST and TOPO[t] not in NOT_GROUND])
    per_blob = defaultdict(lambda: {8: [], 16: []})
    for r in curtain:
        if not r["welded"]:
            continue
        i, j = r["e"]
        mx, mz, my = (P[i][0] + P[j][0]) / 2, (P[i][2] + P[j][2]) / 2, (P[i][1] + P[j][1]) / 2
        ex, ez = P[j][0] - P[i][0], P[j][2] - P[i][2]
        L = math.hypot(ex, ez) or 1.0
        nx, nz = ez / L, -ex / L
        ac = r["across"][0]
        cx = sum(P[k][0] for k in T[ac]) / 3 - mx
        cz = sum(P[k][2] for k in T[ac]) / 3 - mz
        if nx * cx + nz * cz < 0:
            nx, nz = -nx, -nz
        for d in (8, 16):
            g = ground.top(mx + nx * d, mz + nz * d)
            if g is not None:
                per_blob[r["blob"]][d].append(g[0] - my)
    med16 = [S.median(v[16]) for v in per_blob.values() if len(v[16]) >= 4]
    med8 = [S.median(v[8]) for v in per_blob.values() if len(v[8]) >= 4]
    hollow = sum(1 for m in med16 if m >= 0.75) / len(med16) if med16 else float("nan")
    rise_ = sum(1 for m in med16 if m <= -0.75) / len(med16) if med16 else float("nan")
    print(f"==== P5 ground around forests ({len(med16)} blobs): outward rise at 8u p50 {S.median(med8):+.2f}, "
          f"at 16u p50 {S.median(med16):+.2f} (p10 {pct(med16, 10):+.2f}, p90 {pct(med16, 90):+.2f}); "
          f"in a hollow >= 0.75u {hollow:.0%}, on a rise >= 0.75u {rise_:.0%}"
          f"  -> {'HOLDS' if abs(S.median(med16)) <= 0.3 and hollow < 0.2 else 'FAILS'}")
    # post-registration: the forests that TOUCH a massif -- what does the ground do beyond them?
    rock_blobs = set()
    for mi, c in enumerate(massifs):
        for e in once_edges(c):
            for t in edges[e]:
                if t not in c and TOPO[t] in FOREST:
                    rock_blobs.add(blob_of[t])
    for bi in sorted(rock_blobs):
        v = per_blob.get(bi, {8: [], 16: []})
        if v[16]:
            print(f"  rock-touching forest blob {bi} ({len(blobs[bi])} tris): outward at 16u p50 "
                  f"{S.median(v[16]):+.2f} (n {len(v[16])}), share falling >= 0.75u "
                  f"{sum(1 for x in v[16] if x <= -0.75) / len(v[16]):.0%}")

    # ---- P6 + the screen ----
    print("\n==== P6 + THE SCREEN (qualified donors first, then every massif >= 100 tris by size) ====")
    def line(r):
        return (f"  #{r['id']:<4} {r['tris']:5d} tris rim {r['rim']:6.1f}u  forest {100 * r['forest_share']:5.1f}%"
                f"  delta {r.get('delta', float('nan')):+5.2f}  lift p50 {r.get('lift_p50', float('nan')):+5.2f}"
                f"  grass spread {r.get('grass_spread', float('nan')):4.2f}  blocks {r['blocks'][:4]}"
                f"{'...' if len(r['blocks']) > 4 else ''}  {','.join(r.get('qualified', []))}")
    qual = sorted([r for r in rows if r.get("qualified")], key=lambda r: -r["tris"])
    for r in qual:
        print(line(r))
    ua = [r for r in qual if "uaho" in r["qualified"]]
    if ua:
        u = max(ua, key=lambda r: r["tris"])
        raised = u.get("delta") is not None and u["delta"] > 1.0
        print(f"  P6 Uaho: forest {100 * u['forest_share']:.1f}% of its rim, delta {u.get('delta')}"
              f"  -> {'HOLDS' if (u['forest_share'] < 0.10 or not raised) else 'FAILS (or alcove -- check)'}")
    print("  --")
    for r in sorted([r for r in rows if r["tris"] >= 100 and not r.get("qualified")], key=lambda r: -r["tris"]):
        print(line(r))
    fs = [r["forest_share"] for r in rows if r["tris"] >= 100]
    print(f"  massifs >= 100 tris: {len(fs)}; with no forest contact {sum(1 for f in fs if f == 0)}; "
          f"forest share p50 {100 * S.median(fs):.1f}%")

    # ---- POST-REGISTRATION: the CARRY-UNIT screen (what world-mountain actually carries per donor) ----
    # The census rows above are GLOBAL rock components; the carve takes the largest topo-49 component
    # INSIDE the donor blocks (+ enclosed floods), so its rim can differ at block borders. Classify each
    # carry unit's rim by the GLOBAL soup (contacts across a donor-block border are visible here), and
    # measure the forest-contact rim against two planes: grass contacts only (the census's method) and
    # the WHOLE rim (the carve's own de-tilt -- what the sector map's E measured against).
    from ff9mapkit.world import interior as IN
    print("\n==== CARRY-UNIT SCREEN (post-registration; the four qualified donors as world-mountain carves them) ====")
    screen = {}
    for name, qb in QUALIFIED.items():
        alc = IN.UAHO_ALCOVE if name == "uaho" else None
        try:
            B = IN._mountain_blob(qb, rock_topos=frozenset(ROCK), alcove_box=alc, disc=1, log=lambda *_: None)
        except Exception as err:
            print(f"  {name}: no carry unit ({err})")
            continue
        dV, dtri = B["dV"], B["dtri"]
        unit = {frozenset(IN.kk3(dV[i]) for i in dtri[t]) for t in set(B["blob"]) | set(B["sweep"])}
        rim = B["rim"]
        c0, c1 = B["c_local"]
        lens, ptcls = Counter(), defaultdict(set)
        for k in range(len(rim)):
            a, b = rim[k], rim[(k + 1) % len(rim)]
            ia, ib = pos_id.get(a), pos_id.get(b)
            across = []
            if ia is not None and ib is not None:
                across = [t for t in edges.get((min(ia, ib), max(ia, ib)), [])
                          if frozenset((round(P[n][0], 3), round(P[n][1], 3), round(P[n][2], 3)) for n in T[t])
                          not in unit]
            tps = {TOPO[t] for t in across}
            cls = ("open" if not tps else "forest" if tps & FOREST else "grass" if GRASS in tps
                   else f"topo{sorted(tps)[0]}")
            lens[cls] += math.hypot(b[0] - a[0], b[2] - a[2])
            for p in (a, b):
                ptcls[p].add(cls)
        tot_ = sum(lens.values())
        g = [p for p, s in ptcls.items() if s == {"grass"}]
        f = [p for p, s in ptcls.items() if "forest" in s]

        def fit(pts):
            A = np.array([[p[0] - c0, p[2] - c1, 1.0] for p in pts])
            co, *_ = np.linalg.lstsq(A, np.array([p[1] for p in pts]), rcond=None)
            return co

        def resid(co, pts):
            return [p[1] - (co[0] * (p[0] - c0) + co[1] * (p[2] - c1) + co[2]) for p in pts]
        d_g = d_all = None
        if len(g) >= 3 and f:
            d_g = float(np.median(resid(fit(g), f)))
            call = fit(list(rim))
            d_all = float(np.median(resid(call, f)) - np.median(resid(call, g)))
        screen[name] = {"tris": len(B["blob"]), "rim": round(tot_, 1), "len": {k: round(v, 1) for k, v in lens.items()},
                        "forest_share": lens["forest"] / tot_ if tot_ else 0.0, "delta_grass_plane": d_g,
                        "delta_all_rim_plane": d_all}
        print(f"  {name:9s} {len(B['blob']):4d} tris rim {tot_:6.1f}u  forest {100 * screen[name]['forest_share']:5.1f}%"
              f"  contacts {dict(lens.most_common())}"
              + (f"  forest rim vs grass plane {d_g:+.2f}, vs the carve's all-rim de-tilt {d_all:+.2f}" if d_g is not None else ""))

    for r in rows:
        r.pop("lift_n", None)
    out = HERE / "forest_foot_census.json"
    out.write_text(json.dumps({"rows": rows, "carry_unit_screen": screen}, indent=1, default=str), encoding="utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
