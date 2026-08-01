"""ADVERSARIAL RE-MEASUREMENT of THE FAMILY-BOUNDARY LAW (S2).

The claim under attack (ground_family_boundary.py):
  (1) BRIDGED PAIR   -- grass.main|grass.D shares 0 edges map-wide; only 5 registered
                        art-set pairs exist; snow/canyon/dunes/brush.main have ZERO
                        registered neighbours.
  (2) PATCH PERIMETER -- 67.7% of registered boundary is in open flat ground, but the
                        smaller side's patch is med 8.0u / 93.8% <=32u / 1.2% >64u.
  (3) NO VISIBLE STEP -- boundary dL med 7.50 vs within-cell control 6.82 (ratio 1.10);
                        the UNBRIDGED main|D pair is dL 11.8 = "~2x the bridged ones".
  COROLLARY           -- round 8 mints grass.main|grass.D (INFERRED from the build path,
                        their declared limit 6: the deployed bench was never read).

FIVE DELIBERATELY DIFFERENT MEASUREMENTS:

  T1 THE LIVE BENCH READ (closes their limit 6 -- read-only, nothing written).
     Read the DEPLOYED round-8 Disc9 bench blocks (5..7)x(7..8) straight off the
     install as loose .ff9mesh and count the art-set pairs that actually exist there.
     If the bench holds no grass.D, FORBIDDEN clause (a) targets a boundary that
     is not in the build.

  T2 A DIFFERENT SAMPLE -- DISC 4. X.list_blocks(disc=4) is also 260 blocks, and 178
     of them differ from disc 1 (different vert counts, not a copy). The claim was
     measured on disc 1 ONLY yet is stated "map-wide" and used as a build gate.

  T3 A DIFFERENT ASSIGNMENT -- uv CENTROID in the registry rect, no EPS slack, no
     all-3-verts requirement. Their set_of() demands all three uvs inside a rect
     widened by EPS=0.006; a cell whose free fractional window straddles the
     0.00684 main/D gutter falls to the RESIDUAL SINK on both sides, which is
     exactly the population that could produce a main|D butt. Plus grass.D's PATCH
     PERIMETER COMPOSITION (what does D actually butt, residual included) and the
     THICKNESS of the claimed grass.B bridge.

  T4 EFFECT SIZE, not medians. AUC = P(boundary dL > control dL) and the exceedance
     P(control dL >= 11.8) -- the number clause 3 uses in BOTH directions.

  T5 COUNTEREXAMPLE HUNT for build_implication (b): registered boundaries in open
     featureless ground where the SMALLER side's patch is >64u across, and the
     longest contiguous open-ground boundary chain. Thresholds deliberately
     DIFFERENT from theirs (6u feature radius, 2u/8u level test).

Read-only. Nothing under the game install is written; no deploy script is run.
Artifact -> out/verify_s2_family_boundary.json
Run: cd studies/overworld-topography && py -X utf8 verify_s2_family_boundary.py
"""
import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
from ff9mapkit import config                                   # noqa: E402
from ff9mapkit.world import atlas as A                         # noqa: E402
from ff9mapkit.world import extract as X                       # noqa: E402
from ff9mapkit.world import grassland as G                     # noqa: E402
from ff9mapkit.world import mesh as MSH                        # noqa: E402

OUT = Path(__file__).with_name("out") / "verify_s2_family_boundary.json"

FAM_OF = {}
for t in (0, 1, 2, 3, 10, 11, 12, 13, 42, 59):
    FAM_OF[t] = "grass"
for t in (4, 5, 6):
    FAM_OF[t] = "scrub"
for t in (16, 17, 18, 19, 20, 21, 22, 23):
    FAM_OF[t] = "desert"
for t in (27, 28):
    FAM_OF[t] = "snow"
for t in (45, 46):
    FAM_OF[t] = "canyon"
for t in (36, 37):
    FAM_OF[t] = "forest"
for t in (31, 32, 33):
    FAM_OF[t] = "shore"
FAM_OF[38] = "brush"
FAM_OF[41] = "dunes"
WALL_TOPO = {49, 7, 62, 58}
WATER_TOPO = {48, 50, 51}
PLATEAU_TOPO = {10, 11, 12}

SETS = {}
for fam, g in G.GROUNDS.items():
    m = G.FAM_REGION["main"]
    SETS[f"{fam}.main"] = (m[0] + g["mains_du"], m[1] + g["mains_dv"],
                           m[2] + g["mains_du"], m[3] + g["mains_dv"])
SETS["grass.D"] = tuple(G.FAM_REGION["D"])
SETS["grass.B"] = tuple(G.FAM_REGION["B"])
SET_ORDER = list(SETS)

# ---- T3's ASSIGNMENT: the uv CENTROID, NO eps, NO all-3 requirement -------------------------
def set_centroid(uvs):
    u = sum(q[0] for q in uvs) / 3.0
    v = sum(q[1] for q in uvs) / 3.0
    for name in SET_ORDER:
        r = SETS[name]
        if r[0] <= u <= r[2] and r[1] <= v <= r[3]:
            return name
    return None


# ---- their assignment, reimplemented for a side-by-side on the SAME tris --------------------
EPS = 0.006


def set_theirs(uvs):
    for name in SET_ORDER:
        r = SETS[name]
        if all(r[0] - EPS <= u <= r[2] + EPS and r[1] - EPS <= v <= r[3] + EPS for (u, v) in uvs):
            return name
    return None


# how many verts of the tri land in each rect -- the straddle detector
def rect_votes(uvs):
    c = Counter()
    for (u, v) in uvs:
        for name in SET_ORDER:
            r = SETS[name]
            if r[0] <= u <= r[2] and r[1] <= v <= r[3]:
                c[name] += 1
                break
    return c


_im = A.load_atlas("terrain")
if isinstance(_im, tuple):
    _im = _im[0]
AR = np.asarray(_im.convert("RGB"), dtype=float)
AH, AW = AR.shape[:2]


def tri_L(uvs):
    """ONE sample at the uv centroid (their instrument averaged 4) -- a different estimator."""
    u = sum(q[0] for q in uvs) / 3.0
    v = sum(q[1] for q in uvs) / 3.0
    px = int((u % 1.0) * AW) % AW
    py = int((1.0 - (v % 1.0)) * AH) % AH
    r, g, b = AR[py, px]
    return 0.299 * r + 0.587 * g + 0.114 * b


kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))       # noqa: E731
pct = lambda a, q: round(float(np.percentile(a, q)), 2) if len(a) else None   # noqa: E731

R_FEAT, LEVEL_Y, LEVEL_WIN = 6.0, 2.0, 8.0        # deliberately NOT their 4/8u and 4u/12u


def scan(blocks, reader, label):
    """One global cross-block welded edge map over `blocks`. reader(bx,by) -> BlockMesh|None."""
    g = dict(topo=[], fam=[], s_c=[], s_t=[], v=[], uv=[], L=[], straddle=0, both_rects=0)
    edge_ground = defaultdict(list)
    edge_all = defaultdict(int)
    feat = defaultdict(list)          # 4u cell -> list of (x,z) feature points
    ycell = {}
    nread = ntris = 0
    for (bx, by) in blocks:
        try:
            bm = reader(bx, by)
        except Exception:                                          # noqa: BLE001
            continue
        if bm is None:
            continue
        nread += 1
        V, U, T, fi = bm.verts, bm.uvs, bm.tangents, bm.flat_index
        ox, oz = 64.0 * bx, -64.0 * by
        for t in range(len(fi) // 3):
            idx = fi[3 * t:3 * t + 3]
            topo = X.decode_id(int(round(T[idx[0]][0])))["topograph"]
            w = [(V[j][0] + ox, V[j][1], V[j][2] + oz) for j in idx]
            ks = [kk(p) for p in w]
            ntris += 1
            for i in range(3):
                e = tuple(sorted((ks[i], ks[(i + 1) % 3])))
                if e[0] != e[1]:
                    edge_all[e] += 1
            fam = FAM_OF.get(topo)
            if topo in WALL_TOPO or topo in WATER_TOPO:
                cls = "rock" if topo in WALL_TOPO else "water"
                for p in w:
                    feat[(cls, int(p[0] // 4), int(p[2] // 4))].append((p[0], p[2]))
                continue
            if fam is None:
                continue
            uv = [(float(U[j][0]), float(U[j][1])) for j in idx]
            gi = len(g["topo"])
            g["topo"].append(topo)
            g["fam"].append(fam)
            sc, st = set_centroid(uv), set_theirs(uv)
            g["s_c"].append(sc)
            g["s_t"].append(st)
            g["v"].append(w)
            g["uv"].append(uv)
            g["L"].append(tri_L(uv))
            vt = rect_votes(uv)
            if len(vt) > 1:
                g["straddle"] += 1
                if {"grass.main", "grass.D"} <= set(vt):
                    g["both_rects"] += 1
            if fam in ("forest", "shore"):
                cls = "forest" if fam == "forest" else "coast"
                for p in w:
                    feat[(cls, int(p[0] // 4), int(p[2] // 4))].append((p[0], p[2]))
            for i in range(3):
                e = tuple(sorted((ks[i], ks[(i + 1) % 3])))
                if e[0] != e[1]:
                    edge_ground[e].append(gi)
            for p in w:
                c = (int(p[0] // 4), int(p[2] // 4))
                r = ycell.get(c)
                if r is None:
                    ycell[c] = [p[1], p[1]]
                else:
                    r[0] = min(r[0], p[1])
                    r[1] = max(r[1], p[1])
    n_open = 0
    for e, n in edge_all.items():
        if n == 1:
            n_open += 1
            for p in e:
                feat[("coast", int(p[0] // 4), int(p[2] // 4))].append((p[0], p[2]))
    print(f"[{label}] blocks read {nread}/{len(blocks)}; tris {ntris}; ground tris "
          f"{len(g['topo'])}; open edges {n_open}")
    return g, edge_ground, feat, ycell, nread, ntris


def near(feat, cls, m, R):
    cx, cz = int(m[0] // 4), int(m[2] // 4)
    rr = int(R // 4) + 1
    best = R + 1.0
    for i in range(cx - rr, cx + rr + 1):
        for j in range(cz - rr, cz + rr + 1):
            for (px, pz) in feat.get((cls, i, j), ()):
                d = math.hypot(px - m[0], pz - m[2])
                if d < best:
                    best = d
                    if best < 0.05:
                        return best
    return best


def analyse(g, edge_ground, feat, ycell, label, key="s_c"):
    NG = len(g["topo"])
    S = g[key]
    # ---- same-set patches (union-find over the chosen assignment) ---------------------------
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for e, o in edge_ground.items():
        if len(o) == 2 and S[o[0]] is not None and S[o[0]] == S[o[1]]:
            a, b = find(o[0]), find(o[1])
            if a != b:
                parent[a] = b
    comps = defaultdict(list)
    for i in range(NG):
        if S[i] is not None:
            comps[find(i)].append(i)
    p_ext = [0.0] * NG
    per_set = defaultdict(list)
    for tl in comps.values():
        xs = [p[0] for i in tl for p in g["v"][i]]
        zs = [p[2] for i in tl for p in g["v"][i]]
        ext = max(max(xs) - min(xs), max(zs) - min(zs))
        for i in tl:
            p_ext[i] = ext
        per_set[S[tl[0]]].append(ext)

    pair_len = Counter()
    pair_n = Counter()
    pair_dL = defaultdict(list)
    pair_open = Counter()
    ctrl_dL = []
    nbr = defaultdict(Counter)
    perim = defaultdict(Counter)          # set -> what it butts (incl. residual/open)
    big_open = []
    open_edges = []
    for e, o in edge_ground.items():
        if len(o) != 2:
            if len(o) == 1 and S[o[0]] is not None:
                perim[S[o[0]]]["OPEN_MESH_EDGE"] += 1
            continue
        a, b = o
        sa, sb = S[a], S[b]
        for x, y in ((sa, sb), (sb, sa)):
            if x is not None:
                perim[x][y if y is not None else "RESIDUAL"] += 1
        if sa is None or sb is None:
            continue
        dL = abs(g["L"][a] - g["L"][b])
        if sa == sb:
            ctrl_dL.append(dL)
            continue
        pa, pb = e
        p = tuple(sorted((sa, sb)))
        L = math.dist(pa, pb)
        pair_len[p] += L
        pair_n[p] += 1
        pair_dL[p].append(dL)
        nbr[sa][sb] += 1
        nbr[sb][sa] += 1
        # co-location with MY OWN thresholds
        m = ((pa[0] + pb[0]) / 2.0, (pa[1] + pb[1]) / 2.0, (pa[2] + pb[2]) / 2.0)
        cx, cz = int(m[0] // 4), int(m[2] // 4)
        rr = int(LEVEL_WIN // 4)
        ylo, yhi = 1e9, -1e9
        for i in range(cx - rr, cx + rr + 1):
            for j in range(cz - rr, cz + rr + 1):
                r = ycell.get((i, j))
                if r:
                    ylo = min(ylo, r[0])
                    yhi = max(yhi, r[1])
        yr = 0.0 if ylo > yhi else yhi - ylo
        onb = any(abs(q[0] / 64.0 - round(q[0] / 64.0)) < 1e-3 or
                  abs(q[2] / 64.0 - round(q[2] / 64.0)) < 1e-3 for q in e)
        featless = (g["fam"][a] not in ("forest", "shore") and
                    g["fam"][b] not in ("forest", "shore") and
                    near(feat, "forest", m, R_FEAT) > R_FEAT and
                    near(feat, "rock", m, R_FEAT) > R_FEAT and
                    near(feat, "coast", m, R_FEAT) > R_FEAT and
                    near(feat, "water", m, R_FEAT) > R_FEAT and
                    yr < LEVEL_Y and not onb and
                    (g["topo"][a] in PLATEAU_TOPO) == (g["topo"][b] in PLATEAU_TOPO))
        if featless:
            pair_open[p] += L
            open_edges.append((e, p, min(p_ext[a], p_ext[b]), dL))
            if min(p_ext[a], p_ext[b]) > 64.0:
                big_open.append((p, round(m[0], 1), round(m[2], 1),
                                 round(min(p_ext[a], p_ext[b]), 1)))
    tot = sum(pair_len.values())
    op = sum(pair_open.values())
    print(f"\n[{label}/{key}] art-set boundary {tot:.0f}u over {sum(pair_n.values())} edges; "
          f"FEATURELESS-open {op:.0f}u = {op / max(1e-9, tot):.1%} (my thresholds: "
          f"R={R_FEAT}u, y-range<{LEVEL_Y}u in {LEVEL_WIN}u, off block lines)")
    print(f"   pairs found ({len(pair_len)}):")
    pairs_out = []
    for p, l in pair_len.most_common(20):
        print(f"      {p[0]:12s}|{p[1]:12s} {l:8.0f}u n={pair_n[p]:5d} dL med "
              f"{pct(pair_dL[p], 50):6} p90 {pct(pair_dL[p], 90):6}  open "
              f"{pair_open[p] / max(1e-9, l):5.1%}")
        pairs_out.append(dict(pair=list(p), length=round(l, 1), edges=pair_n[p],
                              dL_med=pct(pair_dL[p], 50), dL_p90=pct(pair_dL[p], 90),
                              open_share=round(pair_open[p] / max(1e-9, l), 4)))
    md = pair_n.get(("grass.D", "grass.main"), 0) + pair_n.get(("grass.main", "grass.D"), 0)
    print(f"   *** grass.main|grass.D shared edges = {md} ***")

    # ---- grass.D perimeter composition + bridge thickness ----------------------------------
    per_out = {}
    for s in ("grass.D", "grass.B", "grass.main"):
        c = perim.get(s)
        if not c:
            continue
        tt = sum(c.values())
        print(f"   PERIMETER of {s} ({tt} tri-edges): " +
              ", ".join(f"{k}={v}({v / tt:.1%})" for k, v in c.most_common(6)))
        per_out[s] = {str(k): v for k, v in c.most_common(10)}

    # bridge thickness: for each grass.D tri, plan distance to the nearest grass.main tri
    dcent = [(sum(p[0] for p in g["v"][i]) / 3.0, sum(p[2] for p in g["v"][i]) / 3.0)
             for i in range(NG) if S[i] == "grass.D"]
    mgrid = defaultdict(list)
    for i in range(NG):
        if S[i] == "grass.main":
            cx = sum(p[0] for p in g["v"][i]) / 3.0
            cz = sum(p[2] for p in g["v"][i]) / 3.0
            mgrid[(int(cx // 8), int(cz // 8))].append((cx, cz))
    dmin = []
    for (cx, cz) in dcent:
        best = 1e9
        for rr in range(1, 7):
            gi, gj = int(cx // 8), int(cz // 8)
            for i in range(gi - rr, gi + rr + 1):
                for j in range(gj - rr, gj + rr + 1):
                    for (mx, mz) in mgrid.get((i, j), ()):
                        best = min(best, math.hypot(mx - cx, mz - cz))
            if best < 8.0 * (rr - 0.5):
                break
        if best < 1e8:
            dmin.append(best)
    if dmin:
        print(f"   grass.D tri -> nearest grass.main tri (plan): n={len(dmin)} "
              f"med {pct(dmin, 50)}u p10 {pct(dmin, 10)}u min {min(dmin):.2f}u; "
              f"<=4u {sum(1 for q in dmin if q <= 4.0) / len(dmin):.1%}  "
              f"<=8u {sum(1 for q in dmin if q <= 8.0) / len(dmin):.1%}")

    # ---- T4 effect size --------------------------------------------------------------------
    bl = [x for p in pair_len for x in pair_dL[p]]
    auc = ex118 = None
    if bl and ctrl_dL:
        cs = np.sort(np.asarray(ctrl_dL))
        auc = float(np.mean(np.searchsorted(cs, np.asarray(bl), side="left") / len(cs)))
        ex118 = float(np.mean(cs >= 11.8))
        print(f"   dL: boundary med {pct(bl, 50)} (n={len(bl)}) vs within-set control med "
              f"{pct(ctrl_dL, 50)} (n={len(ctrl_dL)});  AUC=P(bnd>ctrl)={auc:.3f} "
              f"(0.50=indistinguishable);  P(control dL >= 11.8)={ex118:.1%}")
        print(f"   control dL p75 {pct(ctrl_dL, 75)} p90 {pct(ctrl_dL, 90)} "
              f"p99 {pct(ctrl_dL, 99)}")

    # ---- T5 counterexample hunt ------------------------------------------------------------
    ex = [q for q in open_edges if q[2] > 64.0]
    print(f"   T5: featureless-open boundary edges whose SMALLER side's patch is >64u "
          f"across: {len(ex)} edges / {sum(1 for _ in ex) and sum(math.dist(*q[0]) for q in ex):.0f}u"
          f"  ({len(ex) / max(1, len(open_edges)):.1%} of open edges)")
    if big_open:
        cnt = Counter((q[0], int(q[1] // 64), int(-q[2] // 64)) for q in big_open)
        print(f"      top sites: {[(f'{p[0][0]}|{p[0][1]}', f'blk({p[1]},{p[2]})', n) for p, n in cnt.most_common(6)]}")
    # longest contiguous open-ground chain
    adj = defaultdict(set)
    for (e, p, _, _) in open_edges:
        adj[e[0]].add(e[1])
        adj[e[1]].add(e[0])
    seen = set()
    chains = []
    for a in list(adj):
        for b in list(adj[a]):
            if frozenset((a, b)) in seen:
                continue
            ch = [a, b]
            seen.add(frozenset((a, b)))
            while True:
                nx = [q for q in adj[ch[-1]] if frozenset((ch[-1], q)) not in seen]
                if not nx:
                    break
                seen.add(frozenset((ch[-1], nx[0])))
                ch.append(nx[0])
            chains.append(sum(math.dist(ch[i], ch[i + 1]) for i in range(len(ch) - 1)))
    if chains:
        print(f"      open-ground chains n={len(chains)} med {pct(chains, 50)}u "
              f"p90 {pct(chains, 90)}u MAX {max(chains):.0f}u; >64u "
              f"{sum(1 for c in chains if c > 64) } chains")
    ext_all = [q[2] for q in open_edges]
    return dict(
        ground_tris=NG, boundary_length=round(tot, 1), boundary_edges=sum(pair_n.values()),
        featureless_open_length=round(op, 1),
        featureless_open_share=round(op / max(1e-9, tot), 4),
        pairs=pairs_out, n_pairs=len(pair_len), main_D_edges=md,
        straddle_tris=g["straddle"], straddle_main_D=g["both_rects"],
        perimeter=per_out,
        bridge_dmin=dict(n=len(dmin), med=pct(dmin, 50), p10=pct(dmin, 10),
                         min=round(min(dmin), 2) if dmin else None,
                         le4=round(sum(1 for q in dmin if q <= 4.0) / len(dmin), 4) if dmin else None)
        if dmin else None,
        dL=dict(boundary_med=pct(bl, 50), boundary_n=len(bl), control_med=pct(ctrl_dL, 50),
                control_n=len(ctrl_dL), control_p75=pct(ctrl_dL, 75),
                control_p90=pct(ctrl_dL, 90), auc=round(auc, 4) if auc else None,
                p_control_ge_11_8=round(ex118, 4) if ex118 is not None else None),
        open_ext_min=dict(med=pct(ext_all, 50), p90=pct(ext_all, 90),
                          gt64=round(sum(1 for q in ext_all if q > 64.0) / max(1, len(ext_all)), 4),
                          n=len(ext_all)) if ext_all else None,
        open_chains=dict(n=len(chains), med=pct(chains, 50), p90=pct(chains, 90),
                         max=round(max(chains), 1)) if chains else None,
        big_open_sites=big_open[:40],
        per_set_patch_extent={s: dict(n=len(v), med=pct(v, 50), max=round(max(v), 1))
                              for s, v in per_set.items() if s},
    )


# =============================================================================================
t0 = time.time()
RES = {}

# ---- T1 THE LIVE BENCH -----------------------------------------------------------------------
print("=" * 92)
print("T1  THE LIVE ROUND-8 BENCH (deployed Disc9 blocks) -- closes their limit (6)")
print("=" * 92)
GAME = config.find_game_path(None)
MODF = "FF9CustomMap-world"
BENCH = [(bx, by) for bx in (5, 6, 7) for by in (7, 8)]


def bench_reader(bx, by):
    p = GAME / MODF / MSH.override_relpath(9, bx, by, "0_1", "Terrain")
    if not p.is_file():
        return None
    return MSH.blockmesh_from_ff9mesh(p, disc=9, x=bx, y=by, lod="0_1", part="terrain")


for (bx, by) in BENCH:
    p = GAME / MODF / MSH.override_relpath(9, bx, by, "0_1", "Terrain")
    print(f"   {p.name}: {'exists' if p.is_file() else 'MISSING'}"
          + (f"  mtime {time.strftime('%Y-%m-%d %H:%M', time.localtime(p.stat().st_mtime))}"
             if p.is_file() else ""))
bg, be, bf, byc, bnr, bnt = scan(BENCH, bench_reader, "BENCH d9")
bench_sets_c = Counter(s for s in bg["s_c"] if s)
bench_sets_t = Counter(s for s in bg["s_t"] if s)
bench_res = sum(1 for s in bg["s_c"] if s is None)
print(f"   bench ground tris {len(bg['topo'])}; CENTROID sets {dict(bench_sets_c)}; "
      f"residual {bench_res}")
print(f"   bench THEIR-assignment sets {dict(bench_sets_t)}")
RES["T1_bench"] = dict(blocks_read=bnr, all_tris=bnt, ground_tris=len(bg["topo"]),
                       sets_centroid=dict(bench_sets_c), sets_theirs=dict(bench_sets_t),
                       residual=bench_res)
RES["T1_bench"]["analysis"] = analyse(bg, be, bf, byc, "BENCH d9")

# ---- T2 DISC 4 --------------------------------------------------------------------------------
print("\n" + "=" * 92)
print("T2  A DIFFERENT SAMPLE -- STOCK DISC 4 (260 blocks; 178 differ from disc 1)")
print("=" * 92)
B4 = X.list_blocks(disc=4)
g4, e4, f4, y4, n4, t4 = scan(B4, lambda a, b: X.read_block(a, b, disc=4), "DISC4")
RES["T2_disc4"] = dict(blocks=len(B4), blocks_read=n4, all_tris=t4)
RES["T2_disc4"]["centroid"] = analyse(g4, e4, f4, y4, "DISC4", key="s_c")
RES["T2_disc4"]["theirs"] = analyse(g4, e4, f4, y4, "DISC4", key="s_t")

# ---- T3 DISC 1 with the centroid assignment (their own sample, my method) ---------------------
print("\n" + "=" * 92)
print("T3  THEIR SAMPLE (disc 1), MY ASSIGNMENT (uv centroid, no EPS, no all-3)")
print("=" * 92)
B1 = X.list_blocks(disc=1)
g1, e1, f1, y1, n1, t1 = scan(B1, lambda a, b: X.read_block(a, b, disc=1), "DISC1")
RES["T3_disc1"] = dict(blocks=len(B1), blocks_read=n1, all_tris=t1)
RES["T3_disc1"]["centroid"] = analyse(g1, e1, f1, y1, "DISC1", key="s_c")
RES["T3_disc1"]["theirs"] = analyse(g1, e1, f1, y1, "DISC1", key="s_t")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(RES, indent=0, default=str))
print(f"\nartifact -> {OUT}\ntotal {time.time() - t0:.0f}s")
