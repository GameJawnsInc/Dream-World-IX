"""CELLRIM RETREAT PROBE -- amendment 6 of the amended cell-rule design. READ-ONLY.

THE AMENDED DESIGN (adversary workflow wf_fc1b51c5-2a6): stature seat + D=6 grass
apron collar carried verbatim + THE CELL RULE with RETREAT -- every 4u cell wholly
donor or wholly bench; PARTIAL cells are resolved by WHOLE-TRI DROP of the apron
tris that stick into them (bench keeps the cell), never by growing; boundary
corners take the donor's GRASS-CLASS float only; the no-apron weld perimeter gets
a per-sector answer (carry the abutting forest blob whole, or a declared hard cut).

This instrument APPLIES the retreat rule offline (drop apron tris protruding into
any 4u cell not wholly covered by carried surface; whole-tri drops only; iterate
to fixpoint, since a drop can expose new partial cells) and re-measures ON THE
RETREATED COLLAR:

  (1) off-lattice boundary vert count  -- MUST be 0 for the design to be buildable
      (the on-a-lattice-LINE one-split class is legal, counted separately; rim
      verts that ARE weld verts belong to the per-sector no-apron answer and are
      counted as their own class);
  (2) partial cells remaining          -- MUST be 0 beyond the declared bare-weld
      class (wall-only partials that pre-exist the retreat); NEW wall-only
      partials exposed by the retreat grow the hard-cut perimeter and are counted
      apart;
  (3) corner-step and skirt-tilt distributions on the retreated boundary
      (donor GRASS float vs bench 3.2; per-cell max slope over the bench cell's
      own diagonal) + implied climb-ceiling (2.34375u) violations -- MUST be 0
      for bench_audit green;
  (4) collar survival: tris / plan area / weld-coverage length after retreat, and
      the BARE-WELD TOTAL (anemia check -- the design dies if retreat eats the
      collar);
  (5) the corner-less coast-fan cells (bench boundary cells whose 4 lattice
      corners are NOT all bench verts -- 19 pre-retreat): do they still border
      the retreated collar, and what would retreating AWAY from them cost
      (measured as a second fixpoint variant).

Extraction is VERBATIM from cellrim_boundary_probe.py / cellrim_steps_probe.py
(donor (15,14)+4 neighbors via extract_wall, crest-seeded mesa, weld line, D=6
grass flood with the bench-grass clip, step-patch fixpoint, whisker-trimmed rim
loops); the bench loads from the pristine BACKUP (the live install carries the
band-seat deploy). Nothing is written to the install.

Run: py -X utf8 cellrim_retreat_probe.py     (from studies/overworld-topography)
Artifact: out/cellrim_retreat.json
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
CLIMB = 2.34375                                             # engine climb ceiling (u rise per edge)
A = CELL * CELL
PART_LO, PART_HI = 0.01 * A, 0.99 * A                       # cellrim_steps' partial convention
STICK = 1e-3                                                # u^2 -- "sticks into" a cell
STRICT = 1e-3 * A                                           # sliver census threshold
MAX_IT = 60
BACKUP = Path(r"C:\gd\Dream-World-IX\backups\terrace-strip-prewall.20260731-220001")
OUTD = HERE / "out"


# ---------------------------------------------------------------- bench (pristine backup)
def load_bench_backup():
    """cellrim_boundary_probe's exact loader: TW tri assembly from the backup files."""
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


def pct(a, q):
    return float(np.percentile(a, q)) if len(a) else float("nan")


def dist_stats(v):
    av = [abs(x) for x in v]
    return dict(n=len(v), med=round(pct(av, 50), 3) if av else None,
                p90=round(pct(av, 90), 3) if av else None,
                max=round(max(av), 3) if av else None,
                signed_min=round(min(v), 3) if v else None,
                signed_max=round(max(v), 3) if v else None,
                n_over_climb=sum(1 for x in av if x > CLIMB))


def corner_cells(ix, iz):
    return [(ix - 1, iz - 1), (ix, iz - 1), (ix - 1, iz), (ix, iz)]


def tri_slope(p1, p2, p3):
    a, b, c = (np.array(p) for p in (p1, p2, p3))
    n3 = np.cross(b - a, c - a)
    L = float(np.linalg.norm(n3))
    if L < 1e-12:
        return 0.0
    return math.degrees(math.acos(min(1.0, abs(float(n3[1])) / L)))


def main() -> int:
    t_start = time.time()
    OUTD.mkdir(parents=True, exist_ok=True)

    # ---- the pristine bench -----------------------------------------------------------------
    tris = load_bench_backup()
    assert tris, f"pristine backup missing/empty at {BACKUP}"
    n_rock_in = sum(1 for t in tris if t["topo"] == ROCK)
    assert n_rock_in == 0, f"backup bench not pristine ({n_rock_in} rock tris)"
    grass_r = max(math.hypot(t["cen"][0] - CENTER[0], t["cen"][2] - CENTER[1])
                  for t in tris if t["topo"] in GRASS_TOPO)
    print(f"bench (BACKUP): {len(tris)} tris; grass reach ~{grass_r:.1f}u")

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

    _fan_cache = {}

    def fan_bench(c):
        """A corner-less bench cell: not all 4 lattice corners exist as bench verts."""
        got = _fan_cache.get(c)
        if got is None:
            got = not all(bench_vert_at(c[0] * CELL + dx2, c[1] * CELL + dz2)
                          for dx2 in (0.0, CELL) for dz2 in (0.0, CELL))
            _fan_cache[c] = got
        return got

    # bench cell coverage (lawn / any) -- cellrim_steps_probe verbatim
    bcov = defaultdict(float)
    anyb = defaultdict(float)
    ydev = defaultdict(float)
    for t in tris:
        pl = [(p[0], p[2]) for p in t["w"]]
        dev = max(abs(p[1] - LOWLAND) for p in t["w"])
        xs = [p[0] for p in pl]
        zs = [p[1] for p in pl]
        for cx in range(math.floor(min(xs) / CELL), math.floor(max(xs) / CELL) + 1):
            for cz in range(math.floor(min(zs) / CELL), math.floor(max(zs) / CELL) + 1):
                cp = clip_rect(pl, cx * CELL, cz * CELL, (cx + 1) * CELL, (cz + 1) * CELL)
                if len(cp) >= 3:
                    a2 = shoelace(cp)
                    anyb[(cx, cz)] += a2
                    if t["topo"] in GRASS_TOPO:
                        bcov[(cx, cz)] += a2
                        ydev[(cx, cz)] = max(ydev[(cx, cz)], dev)
    lawn = {c for c in bcov if bcov[c] >= 0.99 * A and ydev[c] <= 0.02}
    print(f"bench cells: {len(lawn)} pristine flat-lawn cells")

    # ---- THE MERGED DONOR SOUP (5 blocks, world frame) -- apron_carry.py verbatim -----------
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

    # ---- THE MESA (crest-seeded rock component; verbatim) -----------------------------------
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

    # ---- the ground-weld line ---------------------------------------------------------------
    weld_edges = []
    for e, ts in ET.items():
        w = [t for t in ts if t in carry]
        o = [t for t in ts if t not in carry]
        if len(w) == 1 and o and all(soup[t]["topo"] != 49 and
                                     soup[t]["topo"] not in PLATEAU_T for t in o):
            weld_edges.append(e)
    wy = [p[1] for e in weld_edges for p in e]
    weld_len = sum(elen(e) for e in weld_edges)
    wpts_set = {p for e in weld_edges for p in e}
    print(f"weld line: {len(weld_edges)} edges, plan length {weld_len:.1f}u, "
          f"y {min(wy):.1f}..{max(wy):.1f}")

    # ---- pose (verbatim) --------------------------------------------------------------------
    mes15 = [t for t in carry if soup[t]["blk"] == DONOR_BLK]
    cvx = [p[0] for t in mes15 for p in soup[t]["w"]]
    cvz = [p[2] for t in mes15 for p in soup[t]["w"]]
    tx = CELL * round((CENTER[0] - (min(cvx) + max(cvx)) / 2.0) / CELL)
    tz = CELL * round((CENTER[1] - (min(cvz) + max(cvz)) / 2.0) / CELL)
    assert (tx, tz) == EXPECT_POSE, f"pose ({tx:+.0f},{tz:+.0f}) != expected {EXPECT_POSE}"
    print(f"pose: translate ({tx:+.0f}, {tz:+.0f}) [4u lattice]")

    # ---- THE APRON FLOOD at APRON_D=6 with the bench-grass clip (verbatim) ------------------
    wpts = sorted(wpts_set)
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
    # step patches (verbatim fixpoint)
    n_patch_total = 0
    while True:
        got_c = apron | carry
        av0 = {kk(p) for t in got_c for p in soup[t]["w"]}
        shared_e = Counter()
        for e, ts in ET.items():
            ins = [t for t in ts if t in got_c]
            outs = [t for t in ts if t not in got_c]
            if ins and outs:
                for t in outs:
                    shared_e[t] += 1
        patch = {si for si in range(len(soup)) if si not in got_c
                 and (all(kk(p) in av0 for p in soup[si]["w"])
                      or shared_e.get(si, 0) >= 2)}
        if not patch:
            break
        n_patch_total += len(patch)
        apron |= patch
    apron0 = set(apron)
    print(f"apron flood (D={APRON_D}): {len(apron0)} tris; {n_patch_total} step patches; "
          f"{n_clip[0]} clip rejections (per-visit recount)")

    # ---- THE STATURE SEAT dy from the PRE-retreat outer rim (apron_carry formula) -----------
    def rim_loops(carrall):
        """cellrim_boundary_probe verbatim: whisker-trimmed closed rim loops + owner."""
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
        if bad:
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
        # component fallback (verbatim)
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

    oe0, _h0, _hl0, _own0, _tr0, _pi0, _md0 = rim_loops(carry | apron0)
    rim0_verts = sorted({p for e in oe0 for p in e})
    dy = LOWLAND - float(np.median([p[1] for p in rim0_verts]))
    assert abs(dy - (-0.14)) < 0.05, f"stature seat drifted: dy {dy:+.3f} (expect ~-0.14)"
    print(f"stature seat dy {dy:+.3f} (rim median -> LOWLAND; the design's declared -0.14)")

    def posed(p):
        return (p[0] + tx, p[1] + dy, p[2] + tz)

    # ---- per-tri 4u-cell coverage (posed plan), precomputed once ----------------------------
    carrall0 = carry | apron0
    tri_cells = {}                                          # si -> {cell: plan area}
    for si in carrall0:
        pg = [(p[0] + tx, p[2] + tz) for p in soup[si]["w"]]
        if shoelace(pg) < 1e-9:
            tri_cells[si] = {}
            continue
        xs = [p[0] for p in pg]
        zs = [p[1] for p in pg]
        d = {}
        for cx in range(math.floor(min(xs) / CELL), math.floor(max(xs) / CELL) + 1):
            for cz in range(math.floor(min(zs) / CELL), math.floor(max(zs) / CELL) + 1):
                cp = clip_rect(pg, cx * CELL, cz * CELL, (cx + 1) * CELL, (cz + 1) * CELL)
                if len(cp) >= 3:
                    a2 = shoelace(cp)
                    if a2 > 1e-9:
                        d[(cx, cz)] = a2
        tri_cells[si] = d
    carry_cov = defaultdict(float)
    wall_area = defaultdict(float)
    for si in carry:
        for c, a2 in tri_cells[si].items():
            carry_cov[c] += a2
            wall_area[c] += a2

    def coverage(surv):
        cov = defaultdict(float, carry_cov)
        for si in surv:
            for c, a2 in tri_cells[si].items():
                cov[c] += a2
        return cov

    def partial_of(cov):
        return {c for c, a2 in cov.items() if PART_LO <= a2 < PART_HI}

    cov_pre = coverage(apron0)
    partial_pre = partial_of(cov_pre)
    partial_pre_wall = {c for c in partial_pre if wall_area.get(c, 0.0) > STICK}
    print(f"pre-retreat cells: {sum(1 for a2 in cov_pre.values() if a2 >= PART_HI)} full, "
          f"{len(partial_pre)} partial ({len(partial_pre_wall)} with wall area = the "
          f"declared bare-weld class candidates); expect 28 partial per cellrim_steps")

    # =========================================================================================
    #  THE RETREAT FIXPOINT
    # =========================================================================================
    surv = set(apron0)
    it_log = []
    for it in range(1, MAX_IT + 1):
        cov = coverage(surv)
        part = partial_of(cov)
        kill = set()
        for si in surv:
            for c, a2 in tri_cells[si].items():
                if a2 > STICK and c in part:
                    kill.add(si)
                    break
        it_log.append(dict(it=it, partial=len(part), killed=len(kill),
                           surviving=len(surv) - len(kill)))
        print(f"  retreat it{it}: {len(part)} partial cells -> drop {len(kill)} apron tris "
              f"(collar {len(surv)} -> {len(surv) - len(kill)})")
        if not kill:
            break
        surv -= kill
    else:
        print("  WARNING: retreat did not reach fixpoint within MAX_IT")

    # =========================================================================================
    #  MEASUREMENT ON A COLLAR STATE
    # =========================================================================================
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

    def report(surv_set, label, fan19=None):
        surv_set = set(surv_set)
        carrall = carry | surv_set
        cov = coverage(surv_set)
        donor_full = {c for c, a2 in cov.items() if a2 >= PART_HI}
        part = partial_of(cov)
        part_apron = {c for c in part
                      if any(tri_cells[si].get(c, 0.0) > STICK for si in surv_set)}
        part_wall_pre = {c for c in part - part_apron
                         if wall_area.get(c, 0.0) > STICK and c in partial_pre}
        part_wall_new = {c for c in part - part_apron
                         if wall_area.get(c, 0.0) > STICK and c not in partial_pre}
        part_other = part - part_apron - part_wall_pre - part_wall_new
        # strict sliver census (sub-threshold protrusions the 1%-partial rule hides)
        sliv_lo = {c: a2 for c, a2 in cov.items() if STRICT < a2 < PART_LO}
        sliv_hi = {c: a2 for c, a2 in cov.items() if PART_HI <= a2 < A - STRICT}
        overfull = sum(1 for a2 in cov.values() if a2 > 1.02 * A)

        # ---- rim + grid classes -------------------------------------------------------------
        oe, n_holes, hole_len, owner, n_trim, n_pinch, mode = rim_loops(carrall)
        L_out = sum(elen(e) for e in oe)
        ow_apron = [e for e in oe if e in owner and owner[e] in surv_set]
        L_ap = sum(elen(e) for e in ow_apron)
        av = sorted({p for e in ow_apron for p in e})
        on_corner = on_line = off_line = n_weld_end = 0
        off_samples = []
        for p in av:
            if p in wpts_set:
                n_weld_end += 1                             # the per-sector (no-apron) class
                continue
            px, pz = p[0] + tx, p[2] + tz
            cx, cz2 = m4(px), m4(pz)
            if cx and cz2:
                on_corner += 1
            elif cx or cz2:
                on_line += 1
            else:
                off_line += 1
                if len(off_samples) < 12:
                    off_samples.append((round(px, 3), round(pz, 3)))
        L_axis = L_diag = L_off = 0.0
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

        # ---- bench-side boundary cells + the coast-fan class --------------------------------
        bench_cells = set()
        for e in ow_apron:
            t = owner[e]
            c = soup[t]["w"]
            ccx = sum(p[0] for p in c) / 3.0
            ccz = sum(p[2] for p in c) / 3.0
            mx = (e[0][0] + e[1][0]) / 2.0
            mz = (e[0][2] + e[1][2]) / 2.0
            dxo, dzo = mx - ccx, mz - ccz
            Ld = math.hypot(dxo, dzo) or 1.0
            qx = mx + 0.6 * dxo / Ld + tx
            qz = mz + 0.6 * dzo / Ld + tz
            bench_cells.add((math.floor(qx / CELL), math.floor(qz / CELL)))
        fan_now = {c for c in bench_cells if fan_bench(c)}

        # fan adjacency of the collar (static bench property, donor_full cells)
        fan_adj_edge = set()
        fan_adj_corner = set()
        for c in donor_full:
            for dx2 in (-1, 0, 1):
                for dz2 in (-1, 0, 1):
                    if dx2 == 0 and dz2 == 0:
                        continue
                    nc = (c[0] + dx2, c[1] + dz2)
                    if nc in donor_full or anyb.get(nc, 0.0) <= 0.01 * A:
                        continue
                    if fan_bench(nc):
                        fan_adj_corner.add(nc)
                        if dx2 == 0 or dz2 == 0:
                            fan_adj_edge.add(nc)
        fan19_edge = fan19_corner = None
        if fan19 is not None:
            fan19_edge = sorted(fan19 & fan_adj_edge)
            fan19_corner = sorted(fan19 & fan_adj_corner)

        # ---- weld coverage after this collar state ------------------------------------------
        cov_w = eaten_w = clip_w = forest_w = other_w = 0.0
        for e in weld_edges:
            L = elen(e)
            outs = [t for t in ET[e] if t not in carry]
            if any(t in surv_set for t in outs):
                cov_w += L
            elif any(t in apron0 for t in outs):
                eaten_w += L
            else:
                topos = {soup[t]["topo"] for t in outs}
                if topos & GRASS_TOPO:
                    clip_w += L
                elif 37 in topos:
                    forest_w += L
                else:
                    other_w += L
        bare_w = eaten_w + clip_w + forest_w + other_w
        area_surv = sum(sum(tri_cells[si].values()) for si in surv_set)

        # ---- grass-class corner floats (the amended float rule) -----------------------------
        surv_posed = []
        apron_hash = defaultdict(list)
        for si in sorted(surv_set):
            pw = [posed(p) for p in soup[si]["w"]]
            pl = [(p[0], p[2]) for p in pw]
            ys = [p[1] for p in pw]
            surv_posed.append((pl, ys))
            xs = [p[0] for p in pl]
            zs = [p[1] for p in pl]
            for cx in range(math.floor(min(xs) / CELL), math.floor(max(xs) / CELL) + 1):
                for cz in range(math.floor(min(zs) / CELL),
                                math.floor(max(zs) / CELL) + 1):
                    apron_hash[(cx, cz)].append(len(surv_posed) - 1)
        Vg = np.array(sorted({posed(p) for si in surv_set for p in soup[si]["w"]})) \
            if surv_set else np.zeros((0, 3))

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

        def grass_ys(x, z):
            got = []
            cs = {(math.floor((x + dxx) / CELL), math.floor((z + dzz) / CELL))
                  for dxx in (-1e-6, 1e-6) for dzz in (-1e-6, 1e-6)}
            idx = set()
            for c in cs:
                idx.update(apron_hash.get(c, ()))
            for i in idx:
                pl, ys = surv_posed[i]
                y = _bary_y(pl, ys, x, z)
                if y is not None:
                    got.append(y)
            return got

        corner_ids = set()
        for c in donor_full:
            for cr in ((c[0], c[1]), (c[0] + 1, c[1]),
                       (c[0], c[1] + 1), (c[0] + 1, c[1] + 1)):
                corner_ids.add(cr)
        cfloat = {}
        n_multi = 0
        for (ix, iz) in sorted(corner_ids):
            cx, cz = ix * CELL, iz * CELL
            if len(Vg):
                d = np.hypot(Vg[:, 0] - cx, Vg[:, 2] - cz)
                near = Vg[d <= 5e-3]
                if len(near):
                    ys = sorted(float(y) for y in near[:, 1])
                    if ys[-1] - ys[0] > 0.05:
                        n_multi += 1
                    cfloat[(ix, iz)] = (ys[0], "vertex")
                    continue
            got = grass_ys(cx, cz)
            if got:
                cfloat[(ix, iz)] = (min(got), "interp")
                continue
            best = None
            for cc in corner_cells(ix, iz):
                if cc not in donor_full:
                    continue
                mx = cc[0] * CELL + CELL / 2
                mz = cc[1] * CELL + CELL / 2
                nx = cx + 0.05 * (1 if mx > cx else -1)
                nz = cz + 0.05 * (1 if mz > cz else -1)
                got = grass_ys(nx, nz)
                if got:
                    best = min(got) if best is None else min(best, min(got))
            if best is not None:
                cfloat[(ix, iz)] = (best, "nudge")

        # ---- steps at boundary corners (grass float vs bench 3.2) ---------------------------
        steps_lawn = []
        steps_coast = []
        over_climb_corners = []
        n_bare_corners = 0
        for (ix, iz) in sorted(corner_ids):
            cells4 = corner_cells(ix, iz)
            has_donor = any(c in donor_full for c in cells4)
            nond = [c for c in cells4 if c not in donor_full]
            if not has_donor or not nond:
                continue
            cls = ("lawn" if any(c in lawn for c in nond)
                   else "coast" if any(anyb.get(c, 0) > 0.01 * A for c in nond)
                   else "void")
            if cls == "void":
                continue
            if (ix, iz) not in cfloat:
                n_bare_corners += 1                         # no grass float -> per-sector class
                continue
            stp = cfloat[(ix, iz)][0] - LOWLAND
            (steps_lawn if cls == "lawn" else steps_coast).append(stp)
            if abs(stp) > CLIMB:
                over_climb_corners.append((ix * CELL, iz * CELL, round(stp, 3), cls))
        st_l = dist_stats(steps_lawn)
        st_c = dist_stats(steps_coast)

        # ---- skirt-cell tilt + walkability --------------------------------------------------
        tilts = []
        edge_rises = []
        n_walk_cells = 0
        n_diag_unknown = 0
        high_cells = []
        n_skirt = 0
        for c in sorted(lawn):
            if c in donor_full:
                continue
            if not any((c[0] + dx2, c[1] + dz2) in donor_full
                       for dx2, dz2 in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                continue
            n_skirt += 1
            x0, z0 = c[0] * CELL, c[1] * CELL
            hs = {}
            for (jx, jz), tag in (((c[0], c[1]), "00"), ((c[0] + 1, c[1]), "10"),
                                  ((c[0], c[1] + 1), "01"),
                                  ((c[0] + 1, c[1] + 1), "11")):
                shared = any(cc in donor_full for cc in corner_cells(jx, jz))
                hs[tag] = cfloat[(jx, jz)][0] if (shared and (jx, jz) in cfloat) \
                    else LOWLAND
            P = {"00": (x0, hs["00"], z0), "10": (x0 + CELL, hs["10"], z0),
                 "01": (x0, hs["01"], z0 + CELL),
                 "11": (x0 + CELL, hs["11"], z0 + CELL)}
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
            if tl > 11.6:
                high_cells.append((c[0] * CELL, c[1] * CELL, round(tl, 1),
                                   sorted(round(v, 2) for v in hs.values())))
        n_rises_over = sum(1 for r2 in edge_rises if r2 > CLIMB)

        # ---- conforming-split crack on the on-line class ------------------------------------
        cracks = []
        for p in av:
            if p in wpts_set:
                continue
            q = posed(p)
            lx, lz = m4(q[0]), m4(q[2])
            if lx == lz:                                    # corner or fully off -> skip
                continue
            if lx:
                ix = round(q[0] / CELL)
                iz = math.floor(q[2] / CELL)
                c0, c1 = (ix, iz), (ix, iz + 1)
                t2 = (q[2] - iz * CELL) / CELL
            else:
                iz = round(q[2] / CELL)
                ix = math.floor(q[0] / CELL)
                c0, c1 = (ix, iz), (ix + 1, iz)
                t2 = (q[0] - ix * CELL) / CELL
            if c0 in cfloat and c1 in cfloat:
                yl = cfloat[c0][0] + t2 * (cfloat[c1][0] - cfloat[c0][0])
                cracks.append(q[1] - yl)
        ac = [abs(x) for x in cracks]

        # ---- print + pack -------------------------------------------------------------------
        n_av = on_corner + on_line + off_line
        print(f"\n== [{label}] ==")
        print(f"collar: {len(surv_set)}/{len(apron0)} apron tris survive "
              f"({area_surv:.0f}u2 plan); rim [{mode}] {L_out:.1f}u "
              f"(apron-owned {L_ap:.1f}u), {n_holes} hole loop(s), {n_trim} whiskers, "
              f"{n_pinch} pinch")
        print(f"cells: {len(donor_full)} donor-full; PARTIAL {len(part)} = "
              f"apron-stuck {len(part_apron)} + wall-pre(declared) {len(part_wall_pre)} "
              f"+ wall-NEW(retreat-exposed) {len(part_wall_new)} + other {len(part_other)}")
        print(f"  strict slivers (hidden by the 1% rule): {len(sliv_lo)} low "
              f"(max {max(sliv_lo.values()) if sliv_lo else 0:.3f}u2), {len(sliv_hi)} high "
              f"(worst gap {A - min(sliv_hi.values()) if sliv_hi else 0:.3f}u2); "
              f"{overfull} cells over-covered >1.02A (wall fold-over)")
        print(f"boundary verts (apron-owned, non-weld): {n_av}; ON-corner {on_corner} "
              f"({on_corner / max(1, n_av):.1%}), on-LINE {on_line} (legal one-split), "
              f"OFF-lattice {off_line}; +{n_weld_end} weld-endpoint verts (per-sector class)")
        if off_samples:
            print(f"  off-lattice samples (posed): {off_samples}")
        print(f"edge classes: axis {L_axis:.1f}u ({L_axis / max(1e-9, L_ap):.1%}), "
              f"diag {L_diag:.1f}u, off-grid {L_off:.1f}u "
              f"({L_off / max(1e-9, L_ap):.1%})")
        print(f"weld {weld_len:.1f}u: covered {cov_w:.1f}u ({cov_w / weld_len:.1%}); "
              f"BARE {bare_w:.1f}u ({bare_w / weld_len:.1%}) = retreat-eaten {eaten_w:.1f} "
              f"+ clip {clip_w:.1f} + forest {forest_w:.1f} + other {other_w:.1f}")
        print(f"steps lawn: {st_l}")
        print(f"steps coast: {st_c}")
        print(f"  bare corners (no grass float -> per-sector): {n_bare_corners}; "
              f"multi-y grass corners: {n_multi}")
        for oc in sorted(over_climb_corners, key=lambda o: -abs(o[2])):
            print(f"    OVER-CLIMB corner ({oc[0]:.0f},{oc[1]:.0f}) step {oc[2]:+.2f} "
                  f"[{oc[3]}]")
        print(f"tilt over {n_skirt} skirt cells: med {pct(tilts, 50):.1f} / "
              f"p90 {pct(tilts, 90):.1f} / max {max(tilts) if tilts else 0:.1f} deg; "
              f"over-11.6 {sum(1 for t in tilts if t > 11.6)}, "
              f"diag-unknown {n_diag_unknown}")
        for hc in sorted(high_cells, key=lambda h: -h[2])[:10]:
            print(f"    HIGH-TILT cell ({hc[0]:.0f},{hc[1]:.0f}) {hc[2]} deg corners {hc[3]}")
        print(f"WALK: {n_rises_over} skirt edge rises over {CLIMB}u "
              f"(worst {max(edge_rises) if edge_rises else 0:.2f}u) in {n_walk_cells} cells; "
              f"{st_l['n_over_climb'] + st_c['n_over_climb']} over-climb corner steps")
        print(f"crack on the on-line split class: n {len(ac)}, med {pct(ac, 50):.3f} / "
              f"p90 {pct(ac, 90):.3f} / max {max(ac) if ac else 0:.3f}u")
        print(f"coast-fan: {len(fan_now)} corner-less bench cells on the boundary now; "
              f"collar borders {len(fan_adj_edge)} fan cells edge-wise / "
              f"{len(fan_adj_corner)} corner-wise"
              + (f"; of the pre-retreat 19: edge {len(fan19_edge)}, corner "
                 f"{len(fan19_corner)}" if fan19 is not None else ""))
        return dict(
            label=label, n_surv=len(surv_set), n_apron0=len(apron0),
            area_surv=round(area_surv, 1), rim_mode=mode, outer_len=round(L_out, 1),
            apron_owned_len=round(L_ap, 1), holes=n_holes, hole_len=round(hole_len, 1),
            n_trim=n_trim, n_pinch=n_pinch,
            donor_full=len(donor_full), partial=len(part),
            partial_apron=len(part_apron), partial_wall_pre=len(part_wall_pre),
            partial_wall_new=len(part_wall_new), partial_other=len(part_other),
            partial_wall_new_cells=sorted([c[0] * CELL, c[1] * CELL]
                                          for c in part_wall_new),
            slivers_low=len(sliv_lo), slivers_high=len(sliv_hi),
            sliver_low_max=round(max(sliv_lo.values()), 4) if sliv_lo else 0.0,
            sliver_high_gap=round(A - min(sliv_hi.values()), 4) if sliv_hi else 0.0,
            n_boundary_verts=n_av, on_corner=on_corner, on_line=on_line,
            off_line=off_line, weld_end_verts=n_weld_end,
            on_rate=round(on_corner / max(1, n_av), 4),
            off_samples=off_samples,
            L_axis=round(L_axis, 1), L_diag=round(L_diag, 1), L_off=round(L_off, 1),
            weld=dict(total=round(weld_len, 1), covered=round(cov_w, 1),
                      bare=round(bare_w, 1), eaten=round(eaten_w, 1),
                      clip=round(clip_w, 1), forest=round(forest_w, 1),
                      other=round(other_w, 1),
                      bare_frac=round(bare_w / weld_len, 4)),
            steps_lawn=st_l, steps_coast=st_c, n_bare_corners=n_bare_corners,
            n_multi_y=n_multi,
            over_climb_corners=over_climb_corners,
            n_skirt=n_skirt,
            tilt=dict(med=round(pct(tilts, 50), 2) if tilts else None,
                      p90=round(pct(tilts, 90), 2) if tilts else None,
                      max=round(max(tilts), 2) if tilts else None,
                      n_over_11p6=sum(1 for t in tilts if t > 11.6),
                      n_diag_unknown=n_diag_unknown),
            high_tilt_cells=sorted(high_cells, key=lambda h: -h[2]),
            walk=dict(n_rises_over=n_rises_over,
                      worst_rise=round(max(edge_rises), 3) if edge_rises else None,
                      n_cells=n_walk_cells,
                      n_corner_steps_over=st_l["n_over_climb"] + st_c["n_over_climb"]),
            crack=dict(n=len(ac), med=round(pct(ac, 50), 3) if ac else None,
                       p90=round(pct(ac, 90), 3) if ac else None,
                       max=round(max(ac), 3) if ac else None),
            fan=dict(boundary_fan_cells=len(fan_now),
                     adj_edge=len(fan_adj_edge), adj_corner=len(fan_adj_corner),
                     adj_edge_cells=sorted([c[0] * CELL, c[1] * CELL]
                                           for c in fan_adj_edge),
                     fan19_edge=[[c[0] * CELL, c[1] * CELL] for c in fan19_edge]
                     if fan19_edge is not None else None,
                     fan19_corner=[[c[0] * CELL, c[1] * CELL] for c in fan19_corner]
                     if fan19_corner is not None else None),
            _donor_full=donor_full)

    # ---- pre-retreat fan-19 identification (cellrim_boundary_probe's sampled bench side) ----
    oe0b, _h, _hl, own0, _t, _p, _m = rim_loops(carry | apron0)
    bench_cells0 = set()
    for e in [e for e in oe0b if e in own0 and own0[e] in apron0]:
        t = own0[e]
        c = soup[t]["w"]
        ccx = sum(p[0] for p in c) / 3.0
        ccz = sum(p[2] for p in c) / 3.0
        mx = (e[0][0] + e[1][0]) / 2.0
        mz = (e[0][2] + e[1][2]) / 2.0
        dxo, dzo = mx - ccx, mz - ccz
        Ld = math.hypot(dxo, dzo) or 1.0
        qx = mx + 0.6 * dxo / Ld + tx
        qz = mz + 0.6 * dzo / Ld + tz
        bench_cells0.add((math.floor(qx / CELL), math.floor(qz / CELL)))
    fan19 = {c for c in bench_cells0 if fan_bench(c)}
    print(f"\npre-retreat bench-side boundary cells: {len(bench_cells0)}; corner-less "
          f"(coast-fan) {len(fan19)} (the boundary probe measured 53/19)")

    r_pre = report(apron0, "PRE-RETREAT (cell rule, no retreat)", fan19=fan19)
    r_post = report(surv, "RETREAT FIXPOINT", fan19=fan19)

    # ---- variant: ALSO retreat away from the coast-fan cells --------------------------------
    r_fan = None
    fan_irreducible = []
    if r_post["fan"]["adj_corner"] > 0:
        surv2 = set(surv)
        for it in range(1, MAX_IT + 1):
            cov = coverage(surv2)
            donor_full = {c for c, a2 in cov.items() if a2 >= PART_HI}
            bad = set()
            for c in donor_full:
                for dx2 in (-1, 0, 1):
                    for dz2 in (-1, 0, 1):
                        if dx2 == 0 and dz2 == 0:
                            continue
                        nc = (c[0] + dx2, c[1] + dz2)
                        if nc in donor_full or anyb.get(nc, 0.0) <= 0.01 * A:
                            continue
                        if fan_bench(nc):
                            bad.add(c)
        # (a donor cell that borders any corner-less bench cell must give the cell back)
            kill = set()
            for si in surv2:
                for c, a2 in tri_cells[si].items():
                    if a2 > STICK and c in bad:
                        kill.add(si)
                        break
            if not kill:
                fan_irreducible = sorted([c[0] * CELL, c[1] * CELL] for c in bad
                                         if wall_area.get(c, 0.0) > STICK)
                if bad:
                    print(f"\nfan-retreat: {len(bad)} fan-adjacent donor cells remain, "
                          f"{len(fan_irreducible)} wall-caused (irreducible without "
                          f"touching the mesa): {fan_irreducible}")
                break
            surv2 -= kill
            print(f"  fan-retreat it{it}: {len(bad)} fan-adjacent donor cells -> "
                  f"drop {len(kill)} more apron tris")
            # re-run the partial fixpoint after the fan drops
            for it2 in range(1, MAX_IT + 1):
                cov = coverage(surv2)
                part = partial_of(cov)
                kill2 = set()
                for si in surv2:
                    for c, a2 in tri_cells[si].items():
                        if a2 > STICK and c in part:
                            kill2.add(si)
                            break
                if not kill2:
                    break
                surv2 -= kill2
        r_fan = report(surv2, "RETREAT + FAN-RETREAT variant", fan19=fan19)

    # ---- verdict ----------------------------------------------------------------------------
    R = r_post
    fails = []
    if R["off_line"] > 0:
        fails.append(f"{R['off_line']} OFF-lattice boundary verts (must be 0)")
    if R["partial_apron"] + R["partial_other"] > 0:
        fails.append(f"{R['partial_apron'] + R['partial_other']} unresolved partial cells")
    if R["partial_wall_new"] > 0:
        fails.append(f"{R['partial_wall_new']} NEW wall-only partial cells "
                     f"(retreat grew the hard-cut perimeter)")
    if R["walk"]["n_rises_over"] > 0 or R["walk"]["n_corner_steps_over"] > 0:
        fails.append(f"{R['walk']['n_rises_over']} climb-ceiling edge rises + "
                     f"{R['walk']['n_corner_steps_over']} over-climb corner steps "
                     f"(must be 0 for bench_audit)")
    if R["n_surv"] == 0:
        fails.append("retreat ate the whole collar (anemia)")
    if R["fan"]["adj_corner"] > 0:
        fails.append(f"collar still borders {R['fan']['adj_corner']} corner-less "
                     f"coast-fan cells (no corner to float)")
    verdict = "BUILDABLE AS AMENDED" if not fails else "NOT BUILDABLE AS AMENDED"
    print(f"\n================ VERDICT: {verdict} ================")
    for f2 in fails:
        print(f"  FAIL: {f2}")
    if not fails:
        print(f"  collar survives {R['n_surv']}/{len(apron0)} tris, weld covered "
              f"{R['weld']['covered']}/{R['weld']['total']}u, bare {R['weld']['bare']}u")

    for r in (r_pre, r_post) + ((r_fan,) if r_fan else ()):
        r.pop("_donor_full", None)
    out = dict(
        design="stature seat + D=6 apron collar + CELL RULE with RETREAT "
               "(adversary amendment 6, wf_fc1b51c5-2a6)",
        pose=[tx, tz], dy=round(dy, 4), weld_len=round(weld_len, 1),
        thresholds=dict(partial=[0.01, 0.99], stick_u2=STICK, strict_u2=STRICT,
                        climb=CLIMB, grid_tol=GRID_TOL),
        retreat_iterations=it_log,
        pre=r_pre, post=r_post, fan_variant=r_fan,
        fan_irreducible_cells=fan_irreducible,
        fan19_cells=sorted([c[0] * CELL, c[1] * CELL] for c in fan19),
        verdict=verdict, fails=fails,
        limits=[
            "partial-cell rule uses cellrim_steps' 1%/99% area convention: protrusions "
            "under 0.16u2 into a cell are invisible to the fixpoint (the strict-sliver "
            "census reports them separately)",
            "coverage is posed PLAN area: near-vertical wall faces contribute ~0, so a "
            "cell containing only cliff face reads empty (over-covered cells reported)",
            "corner floats sample the surviving apron GRASS surface only (the amended "
            "rule); corners with no grass float are counted bare, not stepped",
            "offline instrument: no render, no engine walk query -- climb violations are "
            "edge-rise arithmetic, the same test bench_audit runs",
        ])
    (OUTD / "cellrim_retreat.json").write_text(json.dumps(out, indent=1))
    print(f"\nartifact -> {OUTD / 'cellrim_retreat.json'}  ({time.time() - t_start:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
