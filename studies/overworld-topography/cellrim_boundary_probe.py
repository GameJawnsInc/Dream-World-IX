"""CELLRIM BOUNDARY PROBE -- THE BOUNDARY GRID axis of the cell-rule design. READ-ONLY.

Design under evaluation (NOT built): stature seat (dy ~ -0.14) + the donor apron
collar carried VERBATIM, junction to the flat bench lawn by THE CELL RULE -- every
4u cell wholly donor-apron or wholly bench; shared lattice corners take the DONOR's
corner float; bench boundary cells tilt (the S5 short-lip, expected <= ~10-12 deg
over one 4u cell). NO lift field, NO slicing, NO stitch passes, NO per-point moves
on carried bytes. Off-grid apron boundary verts would each need ONE conforming
split on the adjacent bench cell edge.

This instrument reproduces apron_carry.py's extraction (donor (15,14) + 4
neighbors via extract_wall, crest-seeded mesa component, weld edges, grass-class
adjacency flood with the bench-grass clip, step-patch fixpoint, whisker-trimmed
rim loops) at the DESIGN's APRON_D = 6.0 (apron_carry.py shipped 10.0), posed
tx=-576 tz=+416, and measures:

  * the apron's OUTER boundary rim: total plan length; the apron-owned share vs
    the bare-weld share (uncovered weld = no junction answer yet);
  * % of apron-boundary verts ON the posed 4u lattice (both coords within 1e-3
    of a multiple of 4); OFF-grid verts (= conforming splits), split
    on-a-lattice-LINE vs off-line entirely (no cell-edge home at all);
  * boundary EDGE classes by length: axis / cell-diagonal / off-grid;
  * the boundary's 4u cell count (bench-side = the short-lip cells), and whether
    those bench cells actually hold all 4 lattice corners as bench verts;
  * PARTIAL-coverage cells (carried surface covers part of a 4u cell -- each one
    the cell rule must round to wholly-donor or wholly-bench);
  * the short-lip: |posed rim y - LOWLAND| -> implied tilt over one 4u cell;
  * WHY the boundary stops where it does (outside = clip-rejected grass /
    donor's own class edge / forest / soup border) -- decides whether MORE rings
    can ever move it;
  * +1 and +2 RINGS: extra adjacency steps (still grass-clipped, the APRON_D
    distance test dropped) -- does the on-grid rate rise?
  * WELD COVERAGE: covered vs clipped-grass vs forest-excluded plan length.

READ-ONLY: the bench loads from the pristine BACKUP (the live install currently
carries the band-seat deploy and would fail the pristine gate); donor blocks load
from stock disc-1 via extract_wall. Nothing is written to the install.

Run: py -X utf8 studies/overworld-topography/cellrim_boundary_probe.py
"""
from __future__ import annotations

import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent                      # studies/overworld-topography
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "studies" / "path-d-new-world"))

import terrace_wall_strip as TW                             # noqa: E402  the shared, proven module

kk = TW.kk
GRASS_TOPO = TW.GRASS_TOPO
PLATEAU_T = TW.PLATEAU                                      # {10, 11, 12}
CENTER, LOWLAND = TW.CENTER, TW.LOWLAND
BLOCK, CELL = TW.BLOCK, TW.CELL
ROCK = TW.ROCK

DONOR_BLK = (15, 14)
NEIGH = [(14, 14), (16, 14), (15, 13), (15, 15)]
APRON_D = 6.0                                               # THE DESIGN's collar reach
EXPECT_POSE = (-576.0, 416.0)
GRID_TOL = 1e-3
BACKUP = Path(r"C:\gd\Dream-World-IX\backups\terrace-strip-prewall.20260731-220001")
OUTD = HERE / "out"


# ---------------------------------------------------------------- bench (pristine backup)
def load_bench_backup():
    """TW.load_bench's exact tri assembly, but from the pristine backup's flat files."""
    tris = []
    for (bx, by) in TW.CELLS:
        p = BACKUP / f"Block[{bx}][{by}] Terrain.ff9mesh"
        if not p.is_file():
            continue
        bm = TW.M.blockmesh_from_ff9mesh(p, disc=TW.DISC, x=bx, y=by, part="terrain")
        pos = bm.chan_arrays[TW.X.CH_POS]
        tan = bm.chan_arrays[TW.X.CH_TAN]
        ox, oz = BLOCK * bx, -BLOCK * by
        for t in bm.tris:
            w = [(pos[i][0] + ox, pos[i][1], pos[i][2] + oz) for i in t]
            topo = TW.X.decode_id(int(round(tan[t[0]][0])))["topograph"]
            tris.append(dict(blk=(bx, by), w=w, topo=topo,
                             cen=tuple(np.mean([w[k][j] for k in range(3)])
                                       for j in range(3))))
    return tris


# ---------------------------------------------------------------- small geometry helpers
def m4(v):
    r = v % 4.0
    return min(r, 4.0 - r) <= GRID_TOL


def shoelace(pg):
    s = 0.0
    for i in range(len(pg)):
        a, b = pg[i], pg[(i + 1) % len(pg)]
        s += a[0] * b[1] - b[0] * a[1]
    return abs(s) / 2.0


def _ix(a, b, ax, v):
    t = (v - a[ax]) / (b[ax] - a[ax])
    return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))


def clip_rect(poly, x0, z0, x1, z1):
    pts = list(poly)
    for test, isect in (
            (lambda p: p[0] >= x0 - 1e-12, lambda a, b: _ix(a, b, 0, x0)),
            (lambda p: p[0] <= x1 + 1e-12, lambda a, b: _ix(a, b, 0, x1)),
            (lambda p: p[1] >= z0 - 1e-12, lambda a, b: _ix(a, b, 1, z0)),
            (lambda p: p[1] <= z1 + 1e-12, lambda a, b: _ix(a, b, 1, z1))):
        if not pts:
            return []
        nxt = []
        n = len(pts)
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            ia, ib = test(a), test(b)
            if ia:
                nxt.append(a)
            if ia != ib:
                nxt.append(isect(a, b))
        pts = nxt
    return pts


def elen(e):
    return math.hypot(e[0][0] - e[1][0], e[0][2] - e[1][2])


def main() -> int:
    t_start = time.time()
    OUTD.mkdir(parents=True, exist_ok=True)

    # ---- the pristine bench ---------------------------------------------------------------
    tris = load_bench_backup()
    assert tris, f"pristine backup missing/empty at {BACKUP}"
    n_rock_in = sum(1 for t in tris if t["topo"] == ROCK)
    assert n_rock_in == 0, f"backup bench not pristine ({n_rock_in} rock tris)"
    grass_r = max(math.hypot(t["cen"][0] - CENTER[0], t["cen"][2] - CENTER[1])
                  for t in tris if t["topo"] in GRASS_TOPO)
    print(f"bench (BACKUP): {len(tris)} tris; grass reach ~{grass_r:.1f}u")
    # calibration: is the bench lawn itself lattice-built where the junction lands?
    for R in (40.0, 60.0):
        bgv = {kk(p) for t in tris if t["topo"] in GRASS_TOPO for p in t["w"]
               if math.hypot(p[0] - CENTER[0], p[2] - CENTER[1]) < R}
        n_on = sum(1 for p in bgv if m4(p[0]) and m4(p[2]))
        print(f"calibration: bench grass verts <{R:.0f}u of center on the 4u lattice "
              f"{n_on}/{len(bgv)} = {n_on / max(1, len(bgv)):.1%}")
    bench_plan_hash = defaultdict(list)
    for t in tris:
        for p in t["w"]:
            bench_plan_hash[(math.floor(p[0]), math.floor(p[2]))].append((p[0], p[2]))

    def bench_vert_at(px, pz):
        for cx in (math.floor(px) - 1, math.floor(px), math.floor(px) + 1):
            for cz in (math.floor(pz) - 1, math.floor(pz), math.floor(pz) + 1):
                for (qx, qz) in bench_plan_hash.get((cx, cz), ()):
                    if abs(qx - px) <= GRID_TOL and abs(qz - pz) <= GRID_TOL:
                        return True
        return False

    # ---- THE MERGED DONOR SOUP (5 blocks, world frame) -- apron_carry.py verbatim ----------
    soup = []
    for (bx, by) in [DONOR_BLK] + NEIGH:
        W = TW.extract_wall(bx, by)
        VD = W["V"]
        for lt, idx in enumerate(W["tri_idx"]):
            soup.append(dict(
                w=[(VD[i][0] + W["ox"], VD[i][1], VD[i][2] + W["oz"]) for i in idx],
                topo=W["topo"][lt], blk=(bx, by)))
    ET = defaultdict(list)
    for si, t in enumerate(soup):
        ps = [kk(p) for p in t["w"]]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            ET[tuple(sorted((ps[a], ps[b])))].append(si)
    print(f"soup: {len(soup)} donor tris across 5 blocks")

    # ---- THE MESA (crest-seeded rock component on the merged graph) ------------------------
    crest49 = set()
    for e, ts in ET.items():
        if len(ts) == 2:
            pair = {soup[ts[0]]["topo"], soup[ts[1]]["topo"]}
            if 49 in pair and pair & PLATEAU_T:
                crest49.add(ts[0] if soup[ts[0]]["topo"] == 49 else ts[1])
    adj49 = defaultdict(set)
    for e, ts in ET.items():
        r = [t for t in ts if soup[t]["topo"] == 49]
        for i in range(len(r)):
            for j in range(i + 1, len(r)):
                adj49[r[i]].add(r[j])
                adj49[r[j]].add(r[i])
    comp_of = {}
    seen = set()
    for s in crest49:
        if s in seen:
            continue
        comp = {s}
        st = [s]
        while st:
            t = st.pop()
            for t2 in adj49[t]:
                if t2 not in comp:
                    comp.add(t2)
                    st.append(t2)
        seen |= comp
        for t in comp:
            comp_of[t] = s
    comp_tris = defaultdict(list)
    for t, r in comp_of.items():
        comp_tris[r].append(t)
    root = max(comp_tris, key=lambda r: sum(1 for t in comp_tris[r]
                                            if soup[t]["blk"] == DONOR_BLK))
    mesa = set(comp_tris[root])

    ring1 = set()
    for e, ts in ET.items():
        if len(ts) != 2:
            continue
        w = [t for t in ts if t in mesa]
        p = [t for t in ts if soup[t]["topo"] in PLATEAU_T]
        if len(w) == 1 and len(p) == 1:
            ring1.add(p[0])
    padj = defaultdict(set)
    for e, ts in ET.items():
        pp = [t for t in ts if soup[t]["topo"] in PLATEAU_T]
        for i in range(len(pp)):
            for j in range(i + 1, len(pp)):
                padj[pp[i]].add(pp[j])
                padj[pp[j]].add(pp[i])
    plat = set(ring1)
    st = list(ring1)
    while st:
        t = st.pop()
        for t2 in padj[t]:
            if t2 not in plat:
                plat.add(t2)
                st.append(t2)
    carry = mesa | plat
    print(f"mesa: {len(mesa)} wall tris + {len(plat)} plateau tris")

    # ---- the ground-weld line --------------------------------------------------------------
    weld_edges = []
    for e, ts in ET.items():
        w = [t for t in ts if t in carry]
        o = [t for t in ts if t not in carry]
        if len(w) == 1 and o and all(soup[t]["topo"] != 49 and
                                     soup[t]["topo"] not in PLATEAU_T for t in o):
            weld_edges.append(e)
    wy = [p[1] for e in weld_edges for p in e]
    weld_len = sum(elen(e) for e in weld_edges)
    print(f"weld line: {len(weld_edges)} edges, plan length {weld_len:.1f}u, "
          f"y {min(wy):.1f}..{max(wy):.1f}")

    # ---- pose (apron_carry.py verbatim: (15,14) mesa-tris bbox, 4u-snapped) ----------------
    mes15 = [t for t in carry if soup[t]["blk"] == DONOR_BLK]
    cvx = [p[0] for t in mes15 for p in soup[t]["w"]]
    cvz = [p[2] for t in mes15 for p in soup[t]["w"]]
    tx = CELL * round((CENTER[0] - (min(cvx) + max(cvx)) / 2.0) / CELL)
    tz = CELL * round((CENTER[1] - (min(cvz) + max(cvz)) / 2.0) / CELL)
    assert (tx, tz) == EXPECT_POSE, f"pose ({tx:+.0f},{tz:+.0f}) != expected {EXPECT_POSE}"
    print(f"pose: translate ({tx:+.0f}, {tz:+.0f}) [4u lattice]")

    # ---- THE APRON FLOOD at APRON_D=6 with the bench-grass clip (apron_carry verbatim) -----
    wpts = sorted({p for e in weld_edges for p in e})
    warr = np.array([[p[0], p[2]] for p in wpts])

    def dist_weld(p):
        return float(np.min(np.hypot(warr[:, 0] - p[0], warr[:, 1] - p[2])))

    banned0 = {kk(p) for t in tris if t["topo"] not in GRASS_TOPO for p in t["w"]}
    barr = np.array([[p[0], p[2]] for p in banned0]) if banned0 else np.zeros((0, 2))
    bench_grass = [t for t in tris if t["topo"] in GRASS_TOPO]
    gg_hash = defaultdict(list)
    for gi, t in enumerate(bench_grass):
        xs = [p[0] for p in t["w"]]
        zs = [p[2] for p in t["w"]]
        for cx in range(math.floor(min(xs) / 8.0), math.floor(max(xs) / 8.0) + 1):
            for cz in range(math.floor(min(zs) / 8.0), math.floor(max(zs) / 8.0) + 1):
                gg_hash[(cx, cz)].append(gi)

    def over_grass(px, pz):
        # apron_carry's barycentric test, cell-hashed for speed (identical accept set)
        for gi in gg_hash.get((math.floor(px / 8.0), math.floor(pz / 8.0)), ()):
            t = bench_grass[gi]
            (x1, z1), (x2, z2), (x3, z3) = ((t["w"][k][0], t["w"][k][2])
                                            for k in range(3))
            det = (x2 - x1) * (z3 - z1) - (x3 - x1) * (z2 - z1)
            if abs(det) < 1e-12:
                continue
            w2 = ((px - x1) * (z3 - z1) - (x3 - x1) * (pz - z1)) / det
            w3 = ((x2 - x1) * (pz - z1) - (px - x1) * (z2 - z1)) / det
            if w2 >= -1e-9 and w3 >= -1e-9 and w2 + w3 <= 1 + 1e-9:
                return True
        return False

    _fit_cache = {}

    def fits_bench(p):
        k3 = kk(p)
        got = _fit_cache.get(k3)
        if got is None:
            px, pz = p[0] + tx, p[2] + tz
            got = (float(np.min(np.hypot(barr[:, 0] - px, barr[:, 1] - pz))) >= 2.0
                   if len(barr) else True) and over_grass(px, pz)
            _fit_cache[k3] = got
        return got

    grass_s = {si for si, t in enumerate(soup) if t["topo"] in GRASS_TOPO}
    gadj = defaultdict(set)
    for e, ts in ET.items():
        gg = [t for t in ts if t in grass_s]
        for i in range(len(gg)):
            for j in range(i + 1, len(gg)):
                gadj[gg[i]].add(gg[j])
                gadj[gg[j]].add(gg[i])
    n_forest_weld = 0
    seeds = set()
    for e, ts in ET.items():
        w = [t for t in ts if t in carry]
        o = [t for t in ts if t not in carry]
        if len(w) == 1 and o:
            for t in o:
                if t in grass_s:
                    seeds.add(t)
                elif soup[t]["topo"] == 37:
                    n_forest_weld += 1

    n_clip = [0]

    def apron_ok(si):
        if min(dist_weld(p) for p in soup[si]["w"]) > APRON_D:
            return False
        if not all(fits_bench(p) for p in soup[si]["w"]):
            n_clip[0] += 1
            return False
        return True

    apron = set()
    frontier = {t for t in seeds if apron_ok(t)}
    while frontier:
        apron |= frontier
        nxt = set()
        for t in frontier:
            for t2 in gadj[t]:
                if t2 not in apron and apron_ok(t2):
                    nxt.add(t2)
        frontier = nxt
    print(f"apron flood (D={APRON_D}): {len(apron)} grass tris; {n_clip[0]} clip "
          f"rejections (may recount per frontier visit); forest weld edges "
          f"{n_forest_weld}")

    def step_patches(apron_set, label):
        apron_set = set(apron_set)
        while True:
            got_c = apron_set | carry
            av = {kk(p) for t in got_c for p in soup[t]["w"]}
            shared_e = Counter()
            for e, ts in ET.items():
                ins = [t for t in ts if t in got_c]
                outs = [t for t in ts if t not in got_c]
                if ins and outs:
                    for t in outs:
                        shared_e[t] += 1
            patch = {si for si in range(len(soup)) if si not in got_c
                     and (all(kk(p) in av for p in soup[si]["w"])
                          or shared_e.get(si, 0) >= 2)}
            if not patch:
                return apron_set
            print(f"   [{label}] step patches: {len(patch)} tris (topo "
                  f"{Counter(soup[t]['topo'] for t in patch).most_common(4)})")
            apron_set |= patch

    apron = step_patches(apron, "base")

    # ---- weld coverage ----------------------------------------------------------------------
    def weld_coverage(apron_set, label):
        cov = un_forest = un_clip = un_other = 0.0
        for e in weld_edges:
            L = elen(e)
            outs = [t for t in ET[e] if t not in carry]
            if any(t in apron_set for t in outs):
                cov += L
                continue
            topos = {soup[t]["topo"] for t in outs}
            if topos & GRASS_TOPO:
                un_clip += L
            elif 37 in topos:
                un_forest += L
            else:
                un_other += L
        tot = cov + un_forest + un_clip + un_other
        print(f"weld coverage [{label}]: {tot:.1f}u total = covered {cov:.1f}u "
              f"({cov / tot:.1%}) + clipped-grass {un_clip:.1f}u ({un_clip / tot:.1%}) "
              f"+ forest-excluded {un_forest:.1f}u ({un_forest / tot:.1%}) "
              f"+ other-topo {un_other:.1f}u ({un_other / tot:.1%})")
        return dict(total=round(tot, 1), covered=round(cov, 1),
                    clipped=round(un_clip, 1), forest=round(un_forest, 1),
                    other=round(un_other, 1))

    # ---- rim loops: apron_carry's own machinery (whisker trim eats the border-mismatch
    # lips, which are open chains; the real rim is the closed loops) -------------------------
    def rim_loops(carrall):
        bcnt = Counter()
        owner = {}
        for t in carrall:
            ps = [kk(p) for p in soup[t]["w"]]
            for a, b in ((0, 1), (1, 2), (2, 0)):
                e = tuple(sorted((ps[a], ps[b])))
                bcnt[e] += 1
                owner[e] = t
        bnd_edges = [e for e, n2 in bcnt.items() if n2 == 1 and e[0] != e[1]]
        padjR = defaultdict(list)
        for e in bnd_edges:
            padjR[e[0]].append(e[1])
            padjR[e[1]].append(e[0])

        def trim():
            n_t = 0
            trimmed = True
            while trimmed:
                trimmed = False
                for p in list(padjR):
                    if p not in padjR:
                        continue
                    if len(padjR[p]) == 1:
                        q = padjR[p][0]
                        if q in padjR and p in padjR[q]:
                            padjR[q].remove(p)
                        del padjR[p]
                        n_t += 1
                        trimmed = True
                    elif len(padjR[p]) == 0:
                        del padjR[p]
                        trimmed = True
            return n_t

        n_trim = trim()
        bad = [p for p, l3 in padjR.items() if len(l3) != 2]
        n_pinch = len(bad)
        if bad:                                             # probe tolerance: cut + re-trim
            for p in bad:
                for q in padjR.pop(p, []):
                    if q in padjR and p in padjR[q]:
                        padjR[q].remove(p)
            n_trim += trim()
        loops = []
        vis = set()
        for start in list(padjR):
            if start in vis or start not in padjR:
                continue
            loop = [start]
            prev = None
            while True:
                nxts = [p for p in padjR[loop[-1]] if p != prev]
                if not nxts or nxts[0] == start:
                    break
                prev = loop[-1]
                loop.append(nxts[0])
            vis.update(loop)
            if len(loop) >= 3:
                loops.append(loop)
        loops.sort(key=lambda l3: -TW.poly_area2([(p[0], p[2]) for p in l3]))
        if loops:
            outer = loops[0]
            oe = [tuple(sorted((outer[i], outer[(i + 1) % len(outer)])))
                  for i in range(len(outer))]
            hole_len = sum(elen(tuple(sorted((l3[i], l3[(i + 1) % len(l3)]))))
                           for l3 in loops[1:] for i in range(len(l3)))
            return oe, len(loops) - 1, hole_len, owner, n_trim, n_pinch, "loops"
        # FALLBACK (a border-mismatch break opened the outer loop and the trim ate it):
        # components of the UNTRIMMED boundary graph; outer = max total edge length
        vadj = defaultdict(set)
        for e in bnd_edges:
            vadj[e[0]].add(e[1])
            vadj[e[1]].add(e[0])
        comp_id = {}
        cid = 0
        for v in vadj:
            if v in comp_id:
                continue
            stk = [v]
            comp_id[v] = cid
            while stk:
                q = stk.pop()
                for q2 in vadj[q]:
                    if q2 not in comp_id:
                        comp_id[q2] = cid
                        stk.append(q2)
            cid += 1
        comp_edges = defaultdict(list)
        for e in bnd_edges:
            comp_edges[comp_id[e[0]]].append(e)
        comp_len = {c: sum(elen(e) for e in es) for c, es in comp_edges.items()}
        outer_c = max(comp_len, key=comp_len.get)
        rest_len = sum(v for c, v in comp_len.items() if c != outer_c)
        return (comp_edges[outer_c], len(comp_len) - 1, rest_len, owner,
                n_trim, n_pinch, "components")

    # ---- THE BOUNDARY-GRID MEASUREMENT ------------------------------------------------------
    def measure(apron_set, label):
        carrall = carry | apron_set
        oe, n_holes, hole_len, owner, n_trim, n_pinch, mode = rim_loops(carrall)
        L_out = sum(elen(e) for e in oe)
        outer_verts = sorted({p for e in oe for p in e})

        ow_apron = [e for e in oe if e in owner and owner[e] in apron_set]
        L_ap = sum(elen(e) for e in ow_apron)
        L_ca = L_out - L_ap

        # the seat (apron_carry's stature formula: outer-rim median y -> LOWLAND)
        dy = LOWLAND - float(np.median([p[1] for p in outer_verts]))

        # vert grid stats (posed) on the APRON-owned outer boundary
        av = sorted({p for e in ow_apron for p in e})
        on_corner = on_line = off_line = 0
        off_samples = []
        for p in av:
            px, pz = p[0] + tx, p[2] + tz
            cx, cz2 = m4(px), m4(pz)
            if cx and cz2:
                on_corner += 1
            elif cx or cz2:
                on_line += 1
                if len(off_samples) < 12:
                    off_samples.append((round(px, 3), round(pz, 3), "on-line"))
            else:
                off_line += 1
                if len(off_samples) < 12:
                    off_samples.append((round(px, 3), round(pz, 3), "OFF-line"))
        n_av = len(av)

        # edge classes by length (apron-owned outer boundary, posed) x stop cause --
        # the cross tells whether MORE rings can ever land the off-grid share
        L_axis = L_diag = L_off = 0.0
        L_grow = L_stuck = L_stuck_off = 0.0
        why = Counter()
        for e in ow_apron:
            (xa, _, za), (xb, _, zb) = e
            pa = (xa + tx, za + tz)
            pb = (xb + tx, zb + tz)
            L = math.hypot(pa[0] - pb[0], pa[1] - pb[1])
            axis = ((abs(pa[0] - pb[0]) < 1e-3 and m4(pa[0]))
                    or (abs(pa[1] - pb[1]) < 1e-3 and m4(pa[1])))
            corners = (m4(pa[0]) and m4(pa[1]) and m4(pb[0]) and m4(pb[1]))
            if axis:
                L_axis += L
            elif corners:
                L_diag += L
            else:
                L_off += L
            outs = [t for t in ET.get(e, []) if t not in carrall]
            if not outs:
                cause = "no-neighbor (soup border/mismatch)"
            else:
                topos = {soup[t]["topo"] for t in outs}
                if topos & GRASS_TOPO:
                    ok = any(t in grass_s and all(fits_bench(p) for p in soup[t]["w"])
                             for t in outs)
                    cause = ("next-ring grass (fits clip)" if ok
                             else "grass CLIP-rejected")
                elif 37 in topos:
                    cause = "forest (excluded class)"
                else:
                    cause = "donor class edge (non-grass)"
            why[cause] += L
            if cause == "next-ring grass (fits clip)":
                L_grow += L
            else:
                L_stuck += L
                if not axis and not corners:
                    L_stuck_off += L

        # boundary cells (apron-owned outer edges): bench-side = the short-lip cells
        bench_cells = set()
        apron_cells = set()
        for e in ow_apron:
            t = owner[e]
            c = soup[t]["w"]
            ccx = sum(p[0] for p in c) / 3.0
            ccz = sum(p[2] for p in c) / 3.0
            mx = (e[0][0] + e[1][0]) / 2.0
            mz = (e[0][2] + e[1][2]) / 2.0
            dxo, dzo = mx - ccx, mz - ccz
            Ld = math.hypot(dxo, dzo) or 1.0
            for sgn, acc in ((+1.0, bench_cells), (-1.0, apron_cells)):
                qx = mx + sgn * 0.6 * dxo / Ld + tx
                qz = mz + sgn * 0.6 * dzo / Ld + tz
                acc.add((math.floor(qx / CELL), math.floor(qz / CELL)))
        # do the receiving bench cells hold all 4 lattice corners as bench verts?
        n_bc_ok = 0
        for (cx, cz) in bench_cells:
            if all(bench_vert_at(cx * CELL + dx2, cz * CELL + dz2)
                   for dx2 in (0.0, CELL) for dz2 in (0.0, CELL)):
                n_bc_ok += 1

        # partial-coverage cells: carried plan area per boundary-adjacent 4u cell
        cover = defaultdict(float)
        for t in carrall:
            pg = [(p[0] + tx, p[2] + tz) for p in soup[t]["w"]]
            xs = [p[0] for p in pg]
            zs = [p[1] for p in pg]
            if shoelace(pg) < 1e-9:
                continue
            for cx in range(math.floor(min(xs) / CELL), math.floor(max(xs) / CELL) + 1):
                for cz in range(math.floor(min(zs) / CELL),
                                math.floor(max(zs) / CELL) + 1):
                    cp = clip_rect(pg, cx * CELL, cz * CELL,
                                   (cx + 1) * CELL, (cz + 1) * CELL)
                    if len(cp) >= 3:
                        cover[(cx, cz)] += shoelace(cp)
        near = bench_cells | apron_cells
        partial = {c: cover.get(c, 0.0) / (CELL * CELL) for c in near
                   if 0.02 < cover.get(c, 0.0) / (CELL * CELL) < 0.98}

        # the short-lip: shared-corner float vs LOWLAND at this variant's own seat
        devs = [abs(p[1] + dy - LOWLAND) for p in av]
        tilt = [math.degrees(math.atan(d / CELL)) for d in devs]

        print(f"\n== BOUNDARY [{label}] ==")
        print(f"rim [{mode}]: outer {len(outer_verts)} verts / {L_out:.1f}u plan "
              f"(apron-owned {L_ap:.1f}u, bare-weld {L_ca:.1f}u); "
              f"{n_holes} other loop(s)/component(s) {hole_len:.1f}u; {n_trim} "
              f"whisker edges trimmed, {n_pinch} pinch verts cut")
        print(f"seat: dy {dy:+.2f} (stature: outer-rim median -> LOWLAND)")
        print(f"apron-boundary verts: {n_av}; ON-lattice {on_corner} "
              f"({on_corner / max(1, n_av):.1%}); OFF-grid {n_av - on_corner} "
              f"(= conforming splits): on-a-lattice-line {on_line}, OFF-line {off_line}")
        if off_samples:
            print(f"   off-grid samples (posed x,z): {off_samples}")
        print(f"edge classes (by length): axis {L_axis:.1f}u "
              f"({L_axis / max(1e-9, L_ap):.1%}), diagonal {L_diag:.1f}u "
              f"({L_diag / max(1e-9, L_ap):.1%}), off-grid {L_off:.1f}u "
              f"({L_off / max(1e-9, L_ap):.1%})")
        print(f"boundary cells: bench-side {len(bench_cells)} (short-lip cells; "
              f"{n_bc_ok} hold all 4 lattice corners as bench verts), apron-side "
              f"{len(apron_cells)}")
        print(f"partial-coverage cells: {len(partial)} of {len(near)} "
              f"boundary-adjacent in (2%,98%) "
              f"(frac hist {dict(Counter(round(f2, 1) for f2 in partial.values()))})")
        print(f"boundary-stop census (by length): "
              f"{ {k: round(v, 1) for k, v in why.most_common()} }")
        print(f"STUCK boundary (clip/forest/class/border -- no ring count moves it): "
              f"{L_stuck:.1f}u of {L_ap:.1f}u ({L_stuck / max(1e-9, L_ap):.1%}); "
              f"stuck AND off-grid {L_stuck_off:.1f}u "
              f"({L_stuck_off / max(1e-9, L_ap):.1%} of the apron boundary)")
        print(f"short-lip at this seat: |y-{LOWLAND}| p50 "
              f"{float(np.percentile(devs, 50)):.2f} p90 "
              f"{float(np.percentile(devs, 90)):.2f} max {max(devs):.2f}u -> tilt "
              f"p50 {float(np.percentile(tilt, 50)):.1f} p90 "
              f"{float(np.percentile(tilt, 90)):.1f} max {max(tilt):.1f} deg "
              f"(design expects <= ~10-12)")
        return dict(label=label, n_apron=len(apron_set), rim_mode=mode,
                    outer_verts=len(outer_verts),
                    outer_len=round(L_out, 1), apron_len=round(L_ap, 1),
                    bare_weld_len=round(L_ca, 1), holes=n_holes,
                    hole_len=round(hole_len, 1), n_trim=n_trim, n_pinch=n_pinch,
                    L_grow=round(L_grow, 1), L_stuck=round(L_stuck, 1),
                    L_stuck_off=round(L_stuck_off, 1),
                    dy=round(dy, 3), n_verts=n_av, on_corner=on_corner,
                    on_line=on_line, off_line=off_line,
                    on_rate=round(on_corner / max(1, n_av), 4),
                    L_axis=round(L_axis, 1), L_diag=round(L_diag, 1),
                    L_off=round(L_off, 1), bench_cells=len(bench_cells),
                    bench_cells_4corner=n_bc_ok, apron_cells=len(apron_cells),
                    partial_cells=len(partial),
                    partial_fracs=sorted(round(f2, 3) for f2 in partial.values()),
                    why={k: round(v, 1) for k, v in why.items()},
                    dev_p90=round(float(np.percentile(devs, 90)), 2),
                    dev_max=round(float(max(devs)), 2),
                    tilt_p90=round(float(np.percentile(tilt, 90)), 1),
                    tilt_max=round(float(max(tilt)), 1))

    cov0 = weld_coverage(apron, "base")
    r0 = measure(apron, f"APRON_D={APRON_D}")

    # ---- +1 / +2 RINGS: extra adjacency steps, still grass-clipped, distance dropped -------
    def ring_grow(apron_set, label):
        add = set()
        for t in list(apron_set):
            for t2 in gadj.get(t, ()):
                if t2 not in apron_set and t2 not in carry \
                        and all(fits_bench(p) for p in soup[t2]["w"]):
                    add.add(t2)
        grown = step_patches(apron_set | add, label)
        print(f"\n{label}: {len(add)} grass tris added by one adjacency step "
              f"(clip kept, distance dropped); apron {len(apron_set)} -> {len(grown)}")
        return grown

    apron1 = ring_grow(apron, "ring+1")
    cov1 = weld_coverage(apron1, "ring+1")
    r1 = measure(apron1, "ring+1")
    apron2 = ring_grow(apron1, "ring+2")
    cov2 = weld_coverage(apron2, "ring+2")
    r2 = measure(apron2, "ring+2")

    print(f"\nON-GRID RATE: base {r0['on_rate']:.1%} -> ring+1 {r1['on_rate']:.1%} "
          f"-> ring+2 {r2['on_rate']:.1%}; conforming splits "
          f"{r0['n_verts'] - r0['on_corner']} -> {r1['n_verts'] - r1['on_corner']} "
          f"-> {r2['n_verts'] - r2['on_corner']}; partial cells "
          f"{r0['partial_cells']} -> {r1['partial_cells']} -> {r2['partial_cells']}")
    out = dict(apron_d=APRON_D, pose=(tx, tz), weld_len=round(weld_len, 1),
               weld_coverage=dict(base=cov0, ring1=cov1, ring2=cov2),
               base=r0, ring1=r1, ring2=r2)
    (OUTD / "cellrim_boundary_probe.json").write_text(json.dumps(out, indent=1))
    print(f"\nartifact -> {OUTD / 'cellrim_boundary_probe.json'}  "
          f"({time.time() - t_start:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
