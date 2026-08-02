"""CELLRIM STEPS PROBE -- corner steps + the skirt-cell lip for the proposed CELL-RULE junction.

READ-ONLY instrument. Nothing deploys and the live install is never opened for write --
the pristine bench is read from the MAIN repo's backups/terrace-strip-prewall.20260731-220001
(the live Disc9 blocks hold the band-seat build, NOT the pristine lawn this design
would be built on).

Reproduces the apron extraction exactly as apron_carry.py (donor blk (15,14) + 4
neighbors, grass-class flood from the weld line, bench-grass clip, step-patch
fixpoint) but at the PROPOSED collar reach APRON_D = 6, and the stature seat computed
the apron_carry way: dy = LOWLAND - median(outer rim y).

Then measures, for the design under evaluation (cell rule, no blend, no lift):
  (1) STEPS  -- for every posed 4u lattice corner on the apron's outer boundary, the
               donor corner float vs the bench's 3.2 (med/p90/max, signed range).
  (2) TILT   -- for every bench cell adjacent to the boundary: boundary corners take
               donor floats, far corners stay 3.2 -> per-cell max tri slope (deg),
               vs S5's lip envelope (donor's own 0-4u band ~11.6 deg; stock
               feature-median 0.5 deg beyond).
  (3) WALK   -- implied skirt-cell edge rises vs the engine climb ceiling 2.34375u.
  (4) GRID   -- off-grid apron boundary verts (donor mid-edge verts): each needs one
               conforming split on the adjacent bench cell edge; plus the crack height
               that split must absorb (donor mid-vert y vs the corner-float lerp).
  (5) WELD   -- fraction of the donor weld line (and the fringe strip: bottom-course
               wall tris with atlas v-row >= 11) sitting at-or-above the local ground
               surface the cell rule would build (carried apron / tilted skirt / lawn).

Run:  py -X utf8 cellrim_steps_probe.py        (from studies/overworld-topography/)
Artifact: out/cellrim_steps.json
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "path-d-new-world"))

from terrace_wall_strip import (                            # noqa: E402
    kk, poly_area2, clip_cell, extract_wall, load_bench,    # noqa: F401
    CELLS, CENTER, BLOCK, CELL, TILE_U, TILE_V, LOWLAND, GRASS_TOPO, ROCK,
    DECODE, M, X, DISC)

DONOR_BLK = (15, 14)
NEIGH = [(14, 14), (16, 14), (15, 13), (15, 15)]
APRON_D = 6.0                                               # the PROPOSED collar (apron_carry shipped 10)
PLATEAU_T = {10, 11, 12}
CLIMB = 2.34375                                             # engine climb ceiling (u rise per edge)
EPS_BURY = 0.05                                             # tolerance for "at-or-above"
BACKUP = Path(r"C:\gd\Dream-World-IX\backups\terrace-strip-prewall.20260731-220001")
OUT = HERE / "out" / "cellrim_steps.json"


# ---------------------------------------------------------------- pristine bench (backup)
def load_bench_pristine():
    tris = []
    for (bx, by) in CELLS:
        p = BACKUP / f"Block[{bx}][{by}] Terrain.ff9mesh"
        assert p.is_file(), f"backup block missing: {p}"
        bm = M.blockmesh_from_ff9mesh(p, disc=DISC, x=bx, y=by, part="terrain")
        pos = bm.chan_arrays[X.CH_POS]
        tan = bm.chan_arrays[X.CH_TAN]
        ox, oz = BLOCK * bx, -BLOCK * by
        for t in bm.tris:
            w = [(pos[i][0] + ox, pos[i][1], pos[i][2] + oz) for i in t]
            topo = X.decode_id(int(round(tan[t[0]][0])))["topograph"]
            tris.append(dict(blk=(bx, by), w=w, topo=topo,
                             cen=tuple(float(np.mean([w[k][j] for k in range(3)]))
                                       for j in range(3))))
    return tris


def cells_overlapping(poly):
    xs = [p[0] for p in poly]
    zs = [p[1] for p in poly]
    for ix in range(math.floor(min(xs) / CELL), math.floor(max(xs) / CELL) + 1):
        for iz in range(math.floor(min(zs) / CELL), math.floor(max(zs) / CELL) + 1):
            yield (ix, iz)


def pct(a, q):
    return float(np.percentile(a, q)) if len(a) else float("nan")


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    R = {}

    tris = load_bench_pristine()
    n_rock_in = sum(1 for t in tris if t["topo"] == ROCK)
    assert n_rock_in == 0, f"backup bench not pristine ({n_rock_in} rock tris)"
    grass_r = max(math.hypot(t["cen"][0] - CENTER[0], t["cen"][2] - CENTER[1])
                  for t in tris if t["topo"] in GRASS_TOPO)
    print(f"pristine bench (backup): {len(tris)} tris; grass reach ~{grass_r:.1f}u")

    pu_ph, pv_ph = json.loads(DECODE.read_text())["phase"]

    def tile_row(uvs):
        return int(math.floor((min(q[1] for q in uvs) - pv_ph) / TILE_V + 0.5))

    # ---- THE MERGED DONOR SOUP (verbatim from apron_carry.py) ---------------------------
    soup = []
    for (bx, by) in [DONOR_BLK] + NEIGH:
        W = extract_wall(bx, by)
        VD, UD = W["V"], W["U"]
        for lt, idx in enumerate(W["tri_idx"]):
            soup.append(dict(
                w=[(VD[i][0] + W["ox"], VD[i][1], VD[i][2] + W["oz"]) for i in idx],
                uv=[tuple(UD[i]) for i in idx], topo=W["topo"][lt], blk=(bx, by)))
    ET = defaultdict(list)
    for si, t in enumerate(soup):
        ps = [kk(p) for p in t["w"]]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            ET[tuple(sorted((ps[a], ps[b])))].append(si)

    # ---- the mesa (crest-seeded rock component + ring-1 + plateau; verbatim) ------------
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
    print(f"mesa: {len(mesa)} wall + {len(plat)} plateau tris")

    # ---- weld line (verbatim) -----------------------------------------------------------
    weld_edges = []
    weld_tri = {}
    for e, ts in ET.items():
        w = [t for t in ts if t in carry]
        o = [t for t in ts if t not in carry]
        if len(w) == 1 and o and all(soup[t]["topo"] != 49 and
                                     soup[t]["topo"] not in PLATEAU_T for t in o):
            weld_edges.append(e)
            weld_tri[e] = w[0]
    wy = [p[1] for e in weld_edges for p in e]
    print(f"weld line: {len(weld_edges)} edges, y {min(wy):.2f}..{max(wy):.2f}")

    # ---- pose plan (verbatim: donor-blk carry bbox -> 4u lattice) -----------------------
    mes15 = [t for t in carry if soup[t]["blk"] == DONOR_BLK]
    cvx = [p[0] for t in mes15 for p in soup[t]["w"]]
    cvz = [p[2] for t in mes15 for p in soup[t]["w"]]
    tx = CELL * round((CENTER[0] - (min(cvx) + max(cvx)) / 2.0) / CELL)
    tz = CELL * round((CENTER[1] - (min(cvz) + max(cvz)) / 2.0) / CELL)

    # ---- the apron flood at D=6 (verbatim machinery, bench-grass clip on PRISTINE) ------
    wpts = sorted({p for e in weld_edges for p in e})
    warr = np.array([[p[0], p[2]] for p in wpts])

    def dist_weld(p):
        return float(np.min(np.hypot(warr[:, 0] - p[0], warr[:, 1] - p[2])))

    banned0 = {kk(p) for t in tris if t["topo"] not in GRASS_TOPO for p in t["w"]}
    barr = np.array([[p[0], p[2]] for p in banned0]) if banned0 else np.zeros((0, 2))
    bench_grass = [t for t in tris if t["topo"] in GRASS_TOPO]

    def over_grass(px, pz):
        for t in bench_grass:
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
    seeds = set()
    for e, ts in ET.items():
        w = [t for t in ts if t in carry]
        o = [t for t in ts if t not in carry]
        if len(w) == 1 and o:
            for t in o:
                if t in grass_s:
                    seeds.add(t)

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
    print(f"apron (D={APRON_D:g}): {len(apron)} grass tris "
          f"(by block {dict(Counter(soup[t]['blk'] for t in apron))}); "
          f"{n_clip[0]} clipped at the bench grass edge")
    # step patches (verbatim fixpoint)
    n_patch_total = 0
    while True:
        got_c = apron | carry
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
            break
        n_patch_total += len(patch)
        apron |= patch
    if n_patch_total:
        print(f"   step patches: {n_patch_total} donor tris included")
    carrall = carry | apron

    # ---- rim loops + THE STATURE SEAT (dy = LOWLAND - rim median) -----------------------
    bcnt = Counter()
    for t in carrall:
        ps = [kk(p) for p in soup[t]["w"]]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            bcnt[tuple(sorted((ps[a], ps[b])))] += 1
    bnd_edges = [e for e, n2 in bcnt.items() if n2 == 1]
    padjR = defaultdict(list)
    for e in bnd_edges:
        padjR[e[0]].append(e[1])
        padjR[e[1]].append(e[0])
    changed = True
    n_trim = 0
    while changed:
        changed = False
        for p in list(padjR):
            if len(padjR[p]) == 1:
                q = padjR[p][0]
                padjR[q].remove(p)
                del padjR[p]
                n_trim += 1
                changed = True
            elif len(padjR[p]) == 0:
                del padjR[p]
                changed = True
    n_pinch = sum(1 for p, l3 in padjR.items() if len(l3) != 2)
    edges_left = set()
    for p, l3 in padjR.items():
        for q in l3:
            edges_left.add(tuple(sorted((p, q))))
    loops = []
    while edges_left:
        e0 = next(iter(edges_left))
        edges_left.discard(e0)
        loop = [e0[0], e0[1]]
        while True:
            cur = loop[-1]
            nxts = [q for q in padjR[cur]
                    if tuple(sorted((cur, q))) in edges_left]
            if not nxts:
                break
            q = nxts[0]
            edges_left.discard(tuple(sorted((cur, q))))
            if q == loop[0]:
                break
            loop.append(q)
        if len(loop) >= 3:
            loops.append(loop)
    loops.sort(key=lambda l3: -poly_area2([(p[0], p[2]) for p in l3]))
    assert loops, "no rim loop"
    outer_loop = loops[0]
    rim_med = float(np.median([p[1] for p in outer_loop]))
    dy = LOWLAND - rim_med
    weld_pt_set = set(wpts)
    n_rim_on_weld = sum(1 for p in outer_loop if p in weld_pt_set)
    print(f"rim: outer {len(outer_loop)} verts (y med {rim_med:.2f}, "
          f"p90 {pct([p[1] for p in outer_loop], 90):.2f}, "
          f"max {max(p[1] for p in outer_loop):.2f}); {len(loops) - 1} hole loop(s); "
          f"{n_pinch} pinch verts; {n_rim_on_weld} outer-rim verts ARE weld verts "
          f"(clip sectors where bench meets the wall directly)")
    print(f"pose: translate ({tx:+.0f}, {tz:+.0f}), STATURE SEAT dy {dy:+.3f} "
          f"(rim median -> LOWLAND; the D=10 apron build shipped -0.14)")
    R["extraction"] = dict(
        apron_d=APRON_D, n_apron=len(apron), n_carry=len(carry),
        n_patches=n_patch_total, n_clip=n_clip[0], tx=tx, tz=tz, dy=round(dy, 4),
        rim_med=round(rim_med, 4), n_outer_rim=len(outer_loop),
        n_hole_loops=len(loops) - 1, n_pinch=n_pinch,
        n_rim_on_weld=n_rim_on_weld,
        weld_y_posed=[round(min(wy) + dy, 3), round(max(wy) + dy, 3)])

    def posed(p):
        return (p[0] + tx, p[1] + dy, p[2] + tz)

    # ---- posed carried geometry + interpolators -----------------------------------------
    carr_tris = []                                          # (plan_poly, ys, topo)
    for t in sorted(carrall):
        pw = [posed(p) for p in soup[t]["w"]]
        carr_tris.append(([(p[0], p[2]) for p in pw], [p[1] for p in pw],
                          soup[t]["topo"]))
    tri_hash = defaultdict(list)
    apron_hash = defaultdict(list)
    for i, (pl, ys, topo) in enumerate(carr_tris):
        for c in cells_overlapping(pl):
            tri_hash[c].append(i)
            if topo in GRASS_TOPO:
                apron_hash[c].append(i)

    def _bary_y(pl, ys, x, z):
        (x1, z1), (x2, z2), (x3, z3) = pl
        det = (x2 - x1) * (z3 - z1) - (x3 - x1) * (z2 - z1)
        if abs(det) < 1e-12:
            return None
        w2 = ((x - x1) * (z3 - z1) - (x3 - x1) * (z - z1)) / det
        w3 = ((x2 - x1) * (z - z1) - (x - x1) * (z2 - z1)) / det
        if w2 >= -1e-7 and w3 >= -1e-7 and w2 + w3 <= 1 + 1e-7:
            return (1 - w2 - w3) * ys[0] + w2 * ys[1] + w3 * ys[2]
        return None

    def surf_ys(x, z, hash_):
        got = []
        cs = {(math.floor((x + dx) / CELL), math.floor((z + dz) / CELL))
              for dx in (-1e-6, 1e-6) for dz in (-1e-6, 1e-6)}
        idx = set()
        for c in cs:
            idx.update(hash_.get(c, ()))
        for i in idx:
            pl, ys, _t = carr_tris[i]
            y = _bary_y(pl, ys, x, z)
            if y is not None:
                got.append(y)
        return got

    Vp = np.array(sorted({posed(p) for t in carrall for p in soup[t]["w"]}))

    # pristine bench surface interpolator (for coast cells in the ground model)
    ben_tris = [([(p[0], p[2]) for p in t["w"]], [p[1] for p in t["w"]])
                for t in tris]
    ben_hash = defaultdict(list)
    for i, (pl, ys) in enumerate(ben_tris):
        for c in cells_overlapping(pl):
            ben_hash[c].append(i)

    def bench_y(x, z):
        for c in {(math.floor((x + dx) / CELL), math.floor((z + dz) / CELL))
                  for dx in (-1e-6, 1e-6) for dz in (-1e-6, 1e-6)}:
            for i in ben_hash.get(c, ()):
                y = _bary_y(ben_tris[i][0], ben_tris[i][1], x, z)
                if y is not None:
                    return y
        return None

    # ---- cell classification -------------------------------------------------------------
    cov = defaultdict(float)
    for pl, ys, topo in carr_tris:
        for c in cells_overlapping(pl):
            cp = clip_cell(pl, c[0] * CELL, c[1] * CELL)
            if len(cp) >= 3:
                cov[c] += poly_area2(cp)
    A = CELL * CELL
    donor_any = {c for c, a in cov.items() if a >= 0.01 * A}
    donor_maj = {c for c, a in cov.items() if a >= 0.50 * A}
    donor_full = {c for c, a in cov.items() if a >= 0.99 * A}
    partial = {c for c, a in cov.items() if 0.01 * A <= a < 0.99 * A}

    bcov = defaultdict(float)
    anyb = defaultdict(float)
    ydev = defaultdict(float)
    for t in tris:
        pl = [(p[0], p[2]) for p in t["w"]]
        dev = max(abs(p[1] - LOWLAND) for p in t["w"])
        for c in cells_overlapping(pl):
            cp = clip_cell(pl, c[0] * CELL, c[1] * CELL)
            if len(cp) >= 3:
                a = poly_area2(cp)
                anyb[c] += a
                if t["topo"] in GRASS_TOPO:
                    bcov[c] += a
                    ydev[c] = max(ydev[c], dev)
    lawn = {c for c in bcov if bcov[c] >= 0.99 * A and ydev[c] <= 0.02}
    print(f"cells: {len(donor_maj)} donor (majority rule; {len(donor_any)} any-coverage, "
          f"{len(donor_full)} full), {len(partial)} PARTIAL cells the cell rule must "
          f"round; {len(lawn)} pristine flat-lawn cells")

    # completion feasibility for partial cells: can the donor's OWN grass (the "extra
    # apron ring" clause) fill the uncovered remainder, and does it fit over bench grass?
    avail_g = defaultdict(float)
    fit_fail = defaultdict(float)
    for si in grass_s:
        if si in carrall:
            continue
        pl = [((p[0] + tx), (p[2] + tz)) for p in soup[si]["w"]]
        fit = all(fits_bench(p) for p in soup[si]["w"])
        for c in cells_overlapping(pl):
            if c not in partial:
                continue
            cp = clip_cell(pl, c[0] * CELL, c[1] * CELL)
            if len(cp) >= 3:
                a2 = poly_area2(cp)
                avail_g[c] += a2
                if not fit:
                    fit_fail[c] += a2
    n_completable = n_off_bench = n_no_donor = 0
    for c in partial:
        need = A - cov[c]
        if avail_g[c] >= need - 0.02 * A:
            if fit_fail[c] <= 0.01 * A:
                n_completable += 1
            else:
                n_off_bench += 1
        else:
            n_no_donor += 1
    print(f"  partial-cell completion: {n_completable} completable with donor grass "
          f"over bench grass, {n_off_bench} only with donor grass OVER THE COAST BAND "
          f"(clip sectors), {n_no_donor} with NO donor grass available (donor "
          f"forest/rock there)")
    R["cells"] = dict(donor_maj=len(donor_maj), donor_any=len(donor_any),
                      donor_full=len(donor_full), partial=len(partial),
                      lawn=len(lawn), partial_completable=n_completable,
                      partial_only_off_bench=n_off_bench,
                      partial_no_donor=n_no_donor)

    # ---- corner floats -------------------------------------------------------------------
    def corner_cells(ix, iz):
        return [(ix - 1, iz - 1), (ix, iz - 1), (ix - 1, iz), (ix, iz)]

    corner_ids = set()
    for c in donor_maj:
        for (ix, iz) in ((c[0], c[1]), (c[0] + 1, c[1]),
                         (c[0], c[1] + 1), (c[0] + 1, c[1] + 1)):
            corner_ids.add((ix, iz))

    cfloat = {}                                             # (ix,iz) -> (y, kind, spread)
    n_multi = 0
    multi_spreads = []
    n_unresolved = 0
    for (ix, iz) in sorted(corner_ids):
        cx, cz = ix * CELL, iz * CELL
        d = np.hypot(Vp[:, 0] - cx, Vp[:, 2] - cz)
        near = Vp[d <= 5e-3]
        if len(near):
            ys = sorted(float(y) for y in near[:, 1])
            spread = ys[-1] - ys[0]
            if spread > 0.05:
                n_multi += 1
                multi_spreads.append(spread)
            cfloat[(ix, iz)] = (ys[0], "vertex", spread)
            continue
        got = surf_ys(cx, cz, tri_hash)
        if got:
            cfloat[(ix, iz)] = (min(got), "interp", max(got) - min(got))
            continue
        # nudge toward incident donor cells
        best = None
        for cc in corner_cells(ix, iz):
            if cc not in donor_maj:
                continue
            mx = cc[0] * CELL + CELL / 2
            mz = cc[1] * CELL + CELL / 2
            nx = cx + 0.05 * (1 if mx > cx else -1)
            nz = cz + 0.05 * (1 if mz > cz else -1)
            got = surf_ys(nx, nz, tri_hash)
            if got:
                best = min(got) if best is None else min(best, min(got))
        if best is not None:
            cfloat[(ix, iz)] = (best, "nudge", 0.0)
        else:
            n_unresolved += 1

    # ---- (1) STEPS at boundary corners ---------------------------------------------------
    steps_lawn = []
    steps_coast = []
    boundary_corners = []
    for (ix, iz), (y, kind, spread) in cfloat.items():
        cells4 = corner_cells(ix, iz)
        has_donor = any(c in donor_maj for c in cells4)
        nond = [c for c in cells4 if c not in donor_maj]
        if not has_donor or not nond:
            continue
        cls = ("lawn" if any(c in lawn for c in nond)
               else "coast" if any(anyb.get(c, 0) > 0.01 * A for c in nond)
               else "void")
        if cls == "void":
            continue
        stp = y - LOWLAND
        boundary_corners.append(dict(ix=ix, iz=iz, x=ix * CELL, z=iz * CELL,
                                     y=round(y, 3), step=round(stp, 3), cls=cls,
                                     kind=kind))
        (steps_lawn if cls == "lawn" else steps_coast).append(stp)

    def dist_stats(v):
        av = [abs(x) for x in v]
        return dict(n=len(v), med=round(pct(av, 50), 3), p90=round(pct(av, 90), 3),
                    max=round(max(av), 3) if av else None,
                    signed_min=round(min(v), 3) if v else None,
                    signed_max=round(max(v), 3) if v else None,
                    n_over_climb=sum(1 for x in av if x > CLIMB))

    st_l = dist_stats(steps_lawn)
    st_c = dist_stats(steps_coast)
    print(f"\nSTEPS at boundary lattice corners (donor float vs bench {LOWLAND}):")
    print(f"  lawn-adjacent : {st_l}")
    print(f"  coast-adjacent: {st_c}")
    big = sorted((c for c in boundary_corners if abs(c["step"]) > CLIMB),
                 key=lambda c: -abs(c["step"]))
    for c in big:
        print(f"    OVER-CLIMB corner ({c['x']:.0f},{c['z']:.0f}) float y {c['y']} "
              f"step {c['step']:+.2f} [{c['cls']},{c['kind']}]")
    print(f"  corner floats: {n_multi} corners over a vertical donor face "
          f"(multi-y, spread max {max(multi_spreads) if multi_spreads else 0:.2f}u; "
          f"MIN y taken), {n_unresolved} unresolved")
    R["steps"] = dict(lawn=st_l, coast=st_c, n_multi_y=n_multi,
                      n_unresolved=n_unresolved,
                      over_climb_corners=[(c["x"], c["z"], c["step"]) for c in big])

    # ---- (2) TILT of bench skirt cells + (3) walkability --------------------------------
    def cell_diag(c):
        x0, z0 = c[0] * CELL, c[1] * CELL
        for t in tris:
            if t["topo"] not in GRASS_TOPO:
                continue
            if not (x0 <= t["cen"][0] < x0 + CELL and z0 <= t["cen"][2] < z0 + CELL):
                continue
            keys = {(round((p[0] - x0) / CELL, 2), round((p[2] - z0) / CELL, 2))
                    for p in t["w"]}
            if (0.0, 0.0) in keys and (1.0, 1.0) in keys:
                return "00-11"
            if (1.0, 0.0) in keys and (0.0, 1.0) in keys:
                return "10-01"
        return None

    def tri_slope(p1, p2, p3):
        a, b, c = (np.array(p) for p in (p1, p2, p3))
        n3 = np.cross(b - a, c - a)
        L = float(np.linalg.norm(n3))
        if L < 1e-12:
            return 0.0
        return math.degrees(math.acos(min(1.0, abs(float(n3[1])) / L)))

    skirt = {}                                              # cell -> dict
    tilts = []
    edge_rises = []
    n_walk_cells = 0
    n_diag_unknown = 0
    for c in sorted(lawn):
        if c in donor_maj:
            continue
        if not any((c[0] + dx, c[1] + dz) in donor_maj
                   for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            continue
        x0, z0 = c[0] * CELL, c[1] * CELL
        hs = {}
        for (jx, jz), tag in (((c[0], c[1]), "00"), ((c[0] + 1, c[1]), "10"),
                              ((c[0], c[1] + 1), "01"), ((c[0] + 1, c[1] + 1), "11")):
            shared = any(cc in donor_maj for cc in corner_cells(jx, jz))
            if shared and (jx, jz) in cfloat:
                hs[tag] = cfloat[(jx, jz)][0]
            else:
                hs[tag] = LOWLAND
        P = {"00": (x0, hs["00"], z0), "10": (x0 + CELL, hs["10"], z0),
             "01": (x0, hs["01"], z0 + CELL), "11": (x0 + CELL, hs["11"], z0 + CELL)}
        diag = cell_diag(c)
        if diag is None:
            n_diag_unknown += 1
            diag = "00-11"
        if diag == "00-11":
            tris2 = [("00", "10", "11"), ("00", "11", "01")]
            dedge = ("00", "11")
        else:
            tris2 = [("00", "10", "01"), ("10", "11", "01")]
            dedge = ("10", "01")
        tl = max(tri_slope(P[a], P[b], P[cc]) for a, b, cc in tris2)
        tilts.append(tl)
        edges = [("00", "10"), ("10", "11"), ("11", "01"), ("01", "00"), dedge]
        rises = [abs(hs[a] - hs[b]) for a, b in edges]
        edge_rises.extend(rises)
        viol = sum(1 for r2 in rises if r2 > CLIMB)
        if viol:
            n_walk_cells += 1
        skirt[c] = dict(hs=hs, diag=diag, tilt=tl, viol=viol)

    print(f"\nTILT of {len(skirt)} bench skirt cells (boundary corners -> donor float, "
          f"far corners {LOWLAND}):")
    print(f"  deg med {pct(tilts, 50):.1f} / p90 {pct(tilts, 90):.1f} / "
          f"max {max(tilts) if tilts else 0:.1f}  "
          f"(S5 envelope: donor's own 0-4u band ~11.6 deg; stock median 0.5 deg beyond)")
    n_over_lip = sum(1 for t in tilts if t > 12.0)
    n_over_band = sum(1 for t in tilts if t > 11.6)
    print(f"  cells over 11.6 deg: {n_over_band}/{len(tilts)}; over 12 deg: "
          f"{n_over_lip}; diag unknown (defaulted): {n_diag_unknown}")
    for c, d2 in sorted(skirt.items(), key=lambda kv: -kv[1]["tilt"]):
        if d2["tilt"] <= 11.6:
            continue
        print(f"    HIGH-TILT cell ({c[0] * CELL:.0f}..{c[0] * CELL + 4:.0f}, "
              f"{c[1] * CELL:.0f}..{c[1] * CELL + 4:.0f}) tilt {d2['tilt']:.1f} deg "
              f"corner y {sorted(round(v, 2) for v in d2['hs'].values())}")
    print(f"WALKABILITY: {sum(1 for r2 in edge_rises if r2 > CLIMB)} skirt-cell edge "
          f"rises over the {CLIMB}u climb ceiling "
          f"(worst {max(edge_rises) if edge_rises else 0:.2f}u) in {n_walk_cells} cells")
    R["tilt"] = dict(n_cells=len(skirt), med=round(pct(tilts, 50), 2),
                     p90=round(pct(tilts, 90), 2),
                     max=round(max(tilts), 2) if tilts else None,
                     n_over_11p6=n_over_band, n_over_12=n_over_lip,
                     n_diag_unknown=n_diag_unknown)
    R["walk"] = dict(n_edge_rises_over=sum(1 for r2 in edge_rises if r2 > CLIMB),
                     worst_rise=round(max(edge_rises), 3) if edge_rises else None,
                     n_cells_violating=n_walk_cells)

    # ---- (4) GRID: off-grid rim verts + the conforming-split crack ----------------------
    def lat(v):
        return abs(v - CELL * round(v / CELL)) <= 1e-3

    on_corner, on_edge, off_lat = [], [], []
    for p in outer_loop:
        q = posed(p)
        if lat(q[0]) and lat(q[2]):
            on_corner.append(q)
        elif lat(q[0]) or lat(q[2]):
            on_edge.append(q)
        else:
            off_lat.append(q)
    cracks = []
    for q in on_edge:
        if lat(q[0]):
            ix = round(q[0] / CELL)
            iz = math.floor(q[2] / CELL)
            c0, c1 = (ix, iz), (ix, iz + 1)
            t = (q[2] - iz * CELL) / CELL
        else:
            iz = round(q[2] / CELL)
            ix = math.floor(q[0] / CELL)
            c0, c1 = (ix, iz), (ix + 1, iz)
            t = (q[0] - ix * CELL) / CELL
        if c0 in cfloat and c1 in cfloat:
            yl = cfloat[c0][0] + t * (cfloat[c1][0] - cfloat[c0][0])
            cracks.append(q[1] - yl)
    ac = [abs(x) for x in cracks]
    print(f"\nGRID: outer rim verts: {len(on_corner)} on-corner, {len(on_edge)} "
          f"ON-EDGE (one conforming split each), {len(off_lat)} OFF-LATTICE "
          f"(cannot be fixed by one cell-edge split)")
    print(f"  conforming-split crack (donor mid-vert y vs corner-float lerp): "
          f"med {pct(ac, 50):.2f} / p90 {pct(ac, 90):.2f} / "
          f"max {max(ac) if ac else 0:.2f}u over {len(ac)} measurable")
    R["grid"] = dict(on_corner=len(on_corner), on_edge=len(on_edge),
                     off_lattice=len(off_lat), n_crack=len(ac),
                     crack_med=round(pct(ac, 50), 3) if ac else None,
                     crack_p90=round(pct(ac, 90), 3) if ac else None,
                     crack_max=round(max(ac), 3) if ac else None)

    # ---- (5) WELD + FRINGE survival above the cell-rule ground --------------------------
    def skirt_y(c, x, z):
        d2 = skirt[c]
        hs = d2["hs"]
        x0, z0 = c[0] * CELL, c[1] * CELL
        P = {"00": (x0, hs["00"], z0), "10": (x0 + CELL, hs["10"], z0),
             "01": (x0, hs["01"], z0 + CELL), "11": (x0 + CELL, hs["11"], z0 + CELL)}
        u = (x - x0) / CELL
        w = (z - z0) / CELL
        if d2["diag"] == "00-11":
            tri = ("00", "10", "11") if u > w else ("00", "11", "01")
        else:
            tri = ("00", "10", "01") if u + w < 1 else ("10", "11", "01")
        pl = [(P[k][0], P[k][2]) for k in tri]
        ys = [P[k][1] for k in tri]
        y = _bary_y(pl, ys, x, z)
        return y if y is not None else LOWLAND

    def ground(x, z):
        got = surf_ys(x, z, apron_hash)
        if got:
            return ("apron", min(got))
        c = (math.floor(x / CELL), math.floor(z / CELL))
        if c in skirt:
            return ("skirt", skirt_y(c, x, z))
        if c in donor_maj:
            return ("hole", LOWLAND)                        # cell-rule gap: uncovered
        if c in lawn:
            return ("lawn", LOWLAND)
        if anyb.get(c, 0) > 0:
            by = bench_y(x, z)
            return ("coast", by if by is not None else LOWLAND)
        return ("void", None)

    tot_len = 0.0
    buried_len = 0.0
    tag_len = Counter()
    tag_buried = Counter()
    buried_depths = []
    n_edges_intact = 0
    for e in weld_edges:
        a, b = posed(e[0]), posed(e[1])
        L = math.hypot(b[0] - a[0], b[2] - a[2])
        if L < 1e-9:
            continue
        wt = weld_tri[e]
        cen = np.mean([[p[0], p[2]] for p in
                       [posed(p) for p in soup[wt]["w"]]], axis=0)
        mid = ((a[0] + b[0]) / 2, (a[2] + b[2]) / 2)
        od = np.array([mid[0] - cen[0], mid[1] - cen[1]])
        nL = float(np.hypot(*od))
        od = od / nL if nL > 1e-9 else np.array([1.0, 0.0])
        tot_len += L
        edge_ok = True
        worst = 0.0
        wtag = None
        for tpar in (0.1, 0.3, 0.5, 0.7, 0.9):
            px = a[0] + tpar * (b[0] - a[0])
            pz = a[2] + tpar * (b[2] - a[2])
            py = a[1] + tpar * (b[1] - a[1])
            qx, qz = px + 0.15 * od[0], pz + 0.15 * od[1]
            tag, gy = ground(qx, qz)
            if gy is None:
                continue
            amt = gy - py
            if amt > worst:
                worst = amt
                wtag = tag
            if amt > EPS_BURY:
                edge_ok = False
        tag0, _g0 = ground(mid[0] + 0.15 * od[0], mid[1] + 0.15 * od[1])
        tag_len[tag0] += L
        if edge_ok:
            n_edges_intact += 1
        else:
            buried_len += L
            tag_buried[wtag or tag0] += L
            buried_depths.append(worst)
    frac_intact = 1.0 - buried_len / tot_len if tot_len else float("nan")
    print(f"\nWELD SURVIVAL: {n_edges_intact}/{len(weld_edges)} edges fully "
          f"at-or-above the cell-rule ground; {frac_intact:.1%} of weld length intact "
          f"({buried_len:.1f}/{tot_len:.1f}u buried > {EPS_BURY}u)")
    print(f"  weld length by outside-ground class: "
          f"{ {k: round(v, 1) for k, v in tag_len.items()} }")
    if buried_depths:
        print(f"  burial depth med {pct(buried_depths, 50):.2f} / "
              f"max {max(buried_depths):.2f}u; buried length by class "
              f"{ {k: round(v, 1) for k, v in tag_buried.items()} }")
    R["weld"] = dict(n_edges=len(weld_edges), n_intact=n_edges_intact,
                     frac_len_intact=round(frac_intact, 4),
                     len_by_class={k: round(v, 1) for k, v in tag_len.items()},
                     buried_by_class={k: round(v, 1) for k, v in tag_buried.items()},
                     bury_med=round(pct(buried_depths, 50), 3) if buried_depths else None,
                     bury_max=round(max(buried_depths), 3) if buried_depths else None)

    # fringe strip: bottom-course wall tris with atlas v-row >= 11
    weld_touch = set()
    for e in weld_edges:
        weld_touch.add(weld_tri[e])
    rows_hist = Counter()
    fringe = []
    band = []
    for t in weld_touch:
        if soup[t]["topo"] != 49:
            continue
        r2 = tile_row(soup[t]["uv"])
        rows_hist[r2] += 1
        if r2 >= 11:
            fringe.append(t)
        if r2 >= 10:
            band.append(t)

    def strip_survival(ts):
        n_ok = 0
        burys = []
        for t in ts:
            pw = [posed(p) for p in soup[t]["w"]]
            cen = np.mean([[p[0], p[2]] for p in pw], axis=0)
            ok = True
            worst = 0.0
            for p in pw:
                od = np.array([p[0] - cen[0], p[2] - cen[1]])
                nL = float(np.hypot(*od))
                od = od / nL if nL > 1e-9 else np.array([1.0, 0.0])
                tag, gy = ground(p[0] + 0.15 * od[0], p[2] + 0.15 * od[1])
                if gy is None:
                    continue
                amt = gy - p[1]
                worst = max(worst, amt)
                if amt > EPS_BURY:
                    ok = False
            if ok:
                n_ok += 1
            else:
                burys.append(worst)
        return n_ok, burys

    n_fr_intact, fr_bury = strip_survival(fringe)
    n_bd_intact, bd_bury = strip_survival(band)
    print(f"FRINGE STRIP (bottom-course rock tris, v-row >= 11): "
          f"{n_fr_intact}/{len(fringe)} fully above the ground "
          f"({(n_fr_intact / len(fringe)):.1%})" if fringe else
          "FRINGE STRIP: no v-row>=11 bottom-course tris found")
    print(f"  whole band course (rows 10+11): {n_bd_intact}/{len(band)} fully above "
          f"({(n_bd_intact / len(band)):.1%})" if band else "  no band tris")
    print(f"  bottom-course row histogram: {dict(sorted(rows_hist.items()))}")
    if fr_bury or bd_bury:
        allb = sorted(set(fr_bury) | set(bd_bury))
        print(f"  burial depths (u): {[round(b, 2) for b in allb]}")
    R["fringe"] = dict(n=len(fringe), n_intact=n_fr_intact,
                       frac=round(n_fr_intact / len(fringe), 4) if fringe else None,
                       band_n=len(band), band_intact=n_bd_intact,
                       band_frac=round(n_bd_intact / len(band), 4) if band else None,
                       rows=dict(sorted(rows_hist.items())),
                       bury_med=round(pct(bd_bury, 50), 3) if bd_bury else None,
                       bury_max=round(max(bd_bury), 3) if bd_bury else None)

    OUT.write_text(json.dumps(R, indent=1))
    print(f"\nartifact -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
