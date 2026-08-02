"""FORESTBLOB PROBE -- THE FOREST-BLOB FEASIBILITY for the no-apron weld perimeter.

Context (the amended cell-rule design, workflow wf_fc1b51c5-2a6): the D=6 apron collar
covers 154.0u of the 189.4u donor ground-weld line; the uncovered remainder is 31.0u of
FOREST-abutted weld (8 edges -- forest excluded as a feature class by every apron probe)
plus 4.4u of coast-clip.  The adversary's only stock-lawful answer for the forest side
is OPTION A: carry the donor's abutting FOREST BLOB whole, per interior.py's
THE CANOPY CARRY LAW (canopy texture is hand-authored; carry a real topo-37 blob WHOLE
-- verbatim verts/UVs/normals/idall -- never synthesize).  OPTION B is a declared
hard-cut residual with a length bound.  This instrument measures which is honest:

  (1) EXTENT     -- the WHOLE abutting blob(s): tris, plan footprint, y range, blocks
                    spanned, whether the component even closes inside a 3x3 donor
                    neighborhood (whole-blob is the law: the commitment is the blob).
  (2) FIT        -- at the mesa pose (-576,+416) + stature seat dy -0.14: does every
                    blob vert pass the SAME clip test the apron uses (over pristine
                    bench grass AND >= 2u from the coast band), or does the blob hang
                    over coast/sea/off-island?
  (3) BOUNDARY   -- the blob's own donor boundary by abutting class (mesa weld / apron
                    collar / uncarried donor grass / rock / open at a block border),
                    and for every NON-closed class what the bench holds underneath at
                    the pose -- the MOVED-BOUNDARY problem: how much new junction does
                    carrying the blob mint, vs the 31.0u it closes?
  (4) WALK       -- forest is a walkable overworld class: internal edge rises vs the
                    2.34375u climb ceiling, tri slopes, and the rim step DOWN onto the
                    bench lawn (the pose is mesa-locked, so carve_forest's per-station
                    rim lift is NOT available -- raw steps are what the player gets).
  (5) OPTION B   -- the 31.0u forest-weld sector itself: posed weld y vs the 3.2 lawn
                    (the vertical gap a hard cut must confess), wall-side atlas v
                    (band rows without the painted lip: edge vmax vs the fringe strip
                    at v-row >= 10.875), contiguity/location of the sector -- read
                    against fringe_at_weld.json's donor/census numbers.

READ-ONLY: bench from the pristine BACKUP (the live install carries the band-seat
deploy); donor blocks from stock disc-1 via terrace_wall_strip.extract_wall.  Nothing
is written to the install.  Extraction (soup / mesa / weld / pose / apron flood /
step patches / clip test) is VERBATIM from cellrim_boundary_probe.py /
cellrim_steps_probe.py.

Run: py -X utf8 studies/overworld-topography/forestblob_probe.py
Artifact: out/forestblob_probe.json
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
TILE_V = TW.TILE_V

DONOR_BLK = (15, 14)
NEIGH = [(14, 14), (16, 14), (15, 13), (15, 15)]            # the apron probes' 5-block soup
NEIGH9 = NEIGH + [(14, 13), (16, 13), (14, 15), (16, 15)]   # +corners: the 3x3 blob soup
APRON_D = 6.0                                               # the design's collar reach
DY = -0.14                                                  # the design's stature seat (cellrim_steps.json extraction.dy)
CLIMB = 2.34375                                             # engine climb ceiling
FOREST_T = 37
EXPECT_POSE = (-576.0, 416.0)
FRINGE_LO = 10.875                                          # bright-lip strip lo (fringe_at_weld_probe)
GRID_TOL = 1e-3
BACKUP = Path(r"C:\gd\Dream-World-IX\backups\terrace-strip-prewall.20260731-220001")
OUTD = HERE / "out"

PU, PV = json.loads((OUTD / "rock_tiles.json").read_text())["phase"]


def vrow(v):
    return (v - PV) / TILE_V


def tile_row(vs):
    return int(math.floor((min(vs) - PV) / TILE_V + 0.5))


# ---------------------------------------------------------------- bench (pristine backup)
def load_bench_backup():
    """cellrim_boundary_probe's exact tri assembly from the pristine backup."""
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
def elen(e):
    return math.hypot(e[0][0] - e[1][0], e[0][2] - e[1][2])


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


def on64(v):
    r = v % 64.0
    return min(r, 64.0 - r) <= GRID_TOL


def pctl(a, q):
    return round(float(np.percentile(a, q)), 3) if len(a) else None


def cen_key(t):
    return (round(sum(p[0] for p in t["w"]) / 3.0, 3),
            round(sum(p[1] for p in t["w"]) / 3.0, 3),
            round(sum(p[2] for p in t["w"]) / 3.0, 3))


def build_soup(blocks):
    soup = []
    for (bx, by) in blocks:
        W = TW.extract_wall(bx, by)
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
    return soup, ET


def main() -> int:
    t_start = time.time()
    OUTD.mkdir(parents=True, exist_ok=True)
    R = {}

    # ---- the pristine bench -----------------------------------------------------------------
    tris = load_bench_backup()
    assert tris, f"pristine backup missing/empty at {BACKUP}"
    n_rock_in = sum(1 for t in tris if t["topo"] == ROCK)
    assert n_rock_in == 0, f"backup bench not pristine ({n_rock_in} rock tris)"
    grass_r = max(math.hypot(t["cen"][0] - CENTER[0], t["cen"][2] - CENTER[1])
                  for t in tris if t["topo"] in GRASS_TOPO)
    print(f"bench (BACKUP): {len(tris)} tris; grass reach ~{grass_r:.1f}u")

    # ---- the 5-block soup + mesa + weld + pose + apron (cellrim probes, VERBATIM) -----------
    soup, ET = build_soup([DONOR_BLK] + NEIGH)
    print(f"soup5: {len(soup)} donor tris across 5 blocks")

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
    weld_len = sum(elen(e) for e in weld_edges)
    print(f"weld line: {len(weld_edges)} edges, plan length {weld_len:.1f}u, "
          f"y {min(wy):.1f}..{max(wy):.1f}")

    mes15 = [t for t in carry if soup[t]["blk"] == DONOR_BLK]
    cvx = [p[0] for t in mes15 for p in soup[t]["w"]]
    cvz = [p[2] for t in mes15 for p in soup[t]["w"]]
    tx = CELL * round((CENTER[0] - (min(cvx) + max(cvx)) / 2.0) / CELL)
    tz = CELL * round((CENTER[1] - (min(cvz) + max(cvz)) / 2.0) / CELL)
    assert (tx, tz) == EXPECT_POSE, f"pose ({tx:+.0f},{tz:+.0f}) != expected {EXPECT_POSE}"
    print(f"pose: translate ({tx:+.0f}, {tz:+.0f}); seat dy {DY:+.2f} (design)")

    # ---- the bench clip test (apron_carry verbatim, cell-hashed) ----------------------------
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
    any_hash = defaultdict(list)
    for gi, t in enumerate(tris):
        xs = [p[0] for p in t["w"]]
        zs = [p[2] for p in t["w"]]
        for cx in range(math.floor(min(xs) / 8.0), math.floor(max(xs) / 8.0) + 1):
            for cz in range(math.floor(min(zs) / 8.0), math.floor(max(zs) / 8.0) + 1):
                any_hash[(cx, cz)].append(gi)

    def _hit(px, pz, hash_, pool):
        for gi in hash_.get((math.floor(px / 8.0), math.floor(pz / 8.0)), ()):
            t = pool[gi]
            (x1, z1), (x2, z2), (x3, z3) = ((t["w"][k][0], t["w"][k][2])
                                            for k in range(3))
            det = (x2 - x1) * (z3 - z1) - (x3 - x1) * (z2 - z1)
            if abs(det) < 1e-12:
                continue
            w2 = ((px - x1) * (z3 - z1) - (x3 - x1) * (pz - z1)) / det
            w3 = ((x2 - x1) * (pz - z1) - (px - x1) * (z2 - z1)) / det
            if w2 >= -1e-9 and w3 >= -1e-9 and w2 + w3 <= 1 + 1e-9:
                return gi
        return None

    def over_grass(px, pz):
        return _hit(px, pz, gg_hash, bench_grass) is not None

    def over_any(px, pz):
        return _hit(px, pz, any_hash, tris) is not None

    def d_banned(px, pz):
        return float(np.min(np.hypot(barr[:, 0] - px, barr[:, 1] - pz))) \
            if len(barr) else float("inf")

    def grass_y(px, pz):
        gi = _hit(px, pz, gg_hash, bench_grass)
        if gi is None:
            return None
        t = bench_grass[gi]
        return _bary_y([(p[0], p[2]) for p in t["w"]], [p[1] for p in t["w"]], px, pz)

    _fit_cache = {}

    def fits_bench(p):
        k3 = kk(p)
        got = _fit_cache.get(k3)
        if got is None:
            px, pz = p[0] + tx, p[2] + tz
            got = d_banned(px, pz) >= 2.0 and over_grass(px, pz)
            _fit_cache[k3] = got
        return got

    # ---- the apron flood at D=6 + step patches (verbatim) -----------------------------------
    wpts = sorted({p for e in weld_edges for p in e})
    warr = np.array([[p[0], p[2]] for p in wpts])

    def dist_weld(p):
        return float(np.min(np.hypot(warr[:, 0] - p[0], warr[:, 1] - p[2])))

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

    def apron_ok(si):
        if min(dist_weld(p) for p in soup[si]["w"]) > APRON_D:
            return False
        return all(fits_bench(p) for p in soup[si]["w"])

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
    while True:                                             # step-patch fixpoint (verbatim)
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
        apron |= patch
    print(f"apron flood (D={APRON_D:g}): {len(apron)} grass tris")

    # ================================================================ (5) THE FOREST-WELD
    # SECTOR (option B's stretch) -- measured FIRST because it seeds the blob hunt
    fw = []                                                 # (edge, wall_tri, forest_out_tris)
    gw = []                                                 # grass-side weld edges (comparison)
    for e in weld_edges:
        outs = [t for t in ET[e] if t not in carry]
        topos = {soup[t]["topo"] for t in outs}
        if FOREST_T in topos:
            fw.append((e, weld_tri[e], [t for t in outs if soup[t]["topo"] == FOREST_T]))
        elif topos & GRASS_TOPO:
            gw.append((e, weld_tri[e]))

    def edge_vmax(e, wt):
        ek = set(e)
        ev = [vrow(soup[wt]["uv"][k][1]) for k in range(3)
              if kk(soup[wt]["w"][k]) in ek]
        return max(ev) if ev else None

    fw_len = sum(elen(e) for e, _w, _o in fw)
    fw_y = [p[1] for e, _w, _o in fw for p in e]
    fw_rows = Counter(tile_row([q[1] for q in soup[wt]["uv"]]) for _e, wt, _o in fw)
    fw_evmax = [edge_vmax(e, wt) for e, wt, _o in fw]
    fw_gap = []
    for e, _wt, _o in fw:
        my = (e[0][1] + e[1][1]) / 2.0 + DY
        fw_gap.append(my - LOWLAND)
    # contiguity: chain runs on shared endpoints
    fadj_run = defaultdict(set)
    for e, _wt, _o in fw:
        fadj_run[e[0]].add(e[1])
        fadj_run[e[1]].add(e[0])
    runs = []
    seenp = set()
    for e, _wt, _o in fw:
        for p in e:
            if p in seenp:
                continue
            comp = {p}
            stk = [p]
            while stk:
                q = stk.pop()
                for q2 in fadj_run[q]:
                    if q2 not in comp:
                        comp.add(q2)
                        stk.append(q2)
            seenp |= comp
            L = sum(elen(e2) for e2, _w2, _o2 in fw if e2[0] in comp)
            cx = float(np.mean([pp[0] for pp in comp])) + tx
            cz = float(np.mean([pp[2] for pp in comp])) + tz
            runs.append(dict(n_pts=len(comp), length=round(L, 1),
                             posed_center=(round(cx, 1), round(cz, 1))))
    gw_evmax = [edge_vmax(e, wt) for e, wt in gw]
    print(f"\n== (5) THE FOREST-WELD SECTOR (option B's stretch) ==")
    print(f"forest-weld edges: {len(fw)}, plan length {fw_len:.1f}u "
          f"(of {weld_len:.1f}u total weld); runs: {runs}")
    print(f"weld y (donor) {min(fw_y):.2f}..{max(fw_y):.2f} -> POSED "
          f"{min(fw_y) + DY:.2f}..{max(fw_y) + DY:.2f} vs lawn {LOWLAND}")
    print(f"vertical gap over the lawn at edge midpoints: "
          f"med {pctl(fw_gap, 50)} p90 {pctl(fw_gap, 90)} max {max(fw_gap):.2f}u "
          f"(climb ceiling {CLIMB}) -- n over ceiling {sum(1 for g in fw_gap if g > CLIMB)}")
    print(f"wall-side tile rows: {dict(sorted(fw_rows.items()))}; edge vmax "
          f"p10 {pctl(fw_evmax, 10)} med {pctl(fw_evmax, 50)} max {max(fw_evmax):.2f} "
          f"(fringe strip starts {FRINGE_LO}; n edges reaching it "
          f"{sum(1 for v in fw_evmax if v >= FRINGE_LO)}/{len(fw_evmax)})")
    print(f"grass-side comparison: edge vmax p10 {pctl(gw_evmax, 10)} "
          f"med {pctl(gw_evmax, 50)} (donor grass-side edge_in_strip = 100% "
          f"per fringe_at_weld.json)")
    R["forest_weld_sector"] = dict(
        n_edges=len(fw), length=round(fw_len, 1), runs=runs,
        weld_y_donor=[round(min(fw_y), 2), round(max(fw_y), 2)],
        weld_y_posed=[round(min(fw_y) + DY, 2), round(max(fw_y) + DY, 2)],
        gap_over_lawn=dict(med=pctl(fw_gap, 50), p90=pctl(fw_gap, 90),
                           max=round(max(fw_gap), 2),
                           n_over_climb=sum(1 for g in fw_gap if g > CLIMB)),
        wall_rows={str(k): v for k, v in sorted(fw_rows.items())},
        edge_vmax=dict(p10=pctl(fw_evmax, 10), med=pctl(fw_evmax, 50),
                       max=round(max(fw_evmax), 2),
                       n_in_strip=sum(1 for v in fw_evmax if v >= FRINGE_LO)),
        grass_side_edge_vmax=dict(p10=pctl(gw_evmax, 10), med=pctl(gw_evmax, 50)))

    # ================================================================ THE 3x3 BLOB SOUP
    soup9, ET9 = build_soup([DONOR_BLK] + NEIGH9)
    print(f"\nsoup9: {len(soup9)} donor tris across 9 blocks")
    seed_keys = {cen_key(soup[t]) for _e, _wt, outs in fw for t in outs}
    carry_keys = {cen_key(soup[t]) for t in carry}
    apron_keys = {cen_key(soup[t]) for t in apron}
    carry9 = set()
    apron9 = set()
    seed9 = set()
    forest9 = set()
    for si, t in enumerate(soup9):
        ck = cen_key(t)
        if ck in carry_keys:
            carry9.add(si)
        if ck in apron_keys:
            apron9.add(si)
        if t["topo"] == FOREST_T:
            forest9.add(si)
            if ck in seed_keys:
                seed9.add(si)
    assert len(seed9) == len(seed_keys), "weld-forest seeds failed to map into soup9"
    fadj9 = defaultdict(set)
    for e, ts in ET9.items():
        ff = [t for t in ts if t in forest9]
        for i in range(len(ff)):
            for j in range(i + 1, len(ff)):
                fadj9[ff[i]].add(ff[j])
                fadj9[ff[j]].add(ff[i])
    blobs = []
    seenb = set()
    for s in sorted(seed9):
        if s in seenb:
            continue
        comp = {s}
        stk = [s]
        while stk:
            t = stk.pop()
            for t2 in fadj9[t]:
                if t2 not in comp:
                    comp.add(t2)
                    stk.append(t2)
        seenb |= comp
        blobs.append(comp)
    print(f"weld-abutting forest blob(s): {len(blobs)} "
          f"(sizes {[len(b) for b in blobs]}; total topo-37 in soup9 {len(forest9)})")

    # ================================================================ PER-BLOB MEASUREMENT
    R["blobs"] = []
    for bi, comp in enumerate(blobs):
        lbl = f"blob{bi}"
        by_blk = Counter(soup9[t]["blk"] for t in comp)
        area = sum(shoelace([(p[0], p[2]) for p in soup9[t]["w"]]) for t in comp)
        ys = [p[1] for t in comp for p in soup9[t]["w"]]
        xs = [p[0] + tx for t in comp for p in soup9[t]["w"]]
        zs = [p[2] + tz for t in comp for p in soup9[t]["w"]]

        # ---- (1) EXTENT ---------------------------------------------------------------------
        print(f"\n== {lbl}: (1) EXTENT ==")
        print(f"{len(comp)} tris, plan area {area:.0f}u2, blocks "
              f"{ {k: v for k, v in by_blk.most_common()} }")
        print(f"posed bbox x {min(xs):.0f}..{max(xs):.0f} ({max(xs) - min(xs):.0f}u), "
              f"z {min(zs):.0f}..{max(zs):.0f} ({max(zs) - min(zs):.0f}u); "
              f"y (donor) {min(ys):.2f}..{max(ys):.2f} -> posed "
              f"{min(ys) + DY:.2f}..{max(ys) + DY:.2f} (lawn {LOWLAND})")
        # 4u cell footprint at pose
        cov = defaultdict(float)
        for t in comp:
            pg = [(p[0] + tx, p[2] + tz) for p in soup9[t]["w"]]
            pxs = [p[0] for p in pg]
            pzs = [p[1] for p in pg]
            if shoelace(pg) < 1e-9:
                continue
            for cx in range(math.floor(min(pxs) / CELL), math.floor(max(pxs) / CELL) + 1):
                for cz in range(math.floor(min(pzs) / CELL),
                                math.floor(max(pzs) / CELL) + 1):
                    cp = clip_rect(pg, cx * CELL, cz * CELL,
                                   (cx + 1) * CELL, (cz + 1) * CELL)
                    if len(cp) >= 3:
                        cov[(cx, cz)] += shoelace(cp)
        A = CELL * CELL
        n_cell_maj = sum(1 for a in cov.values() if a >= 0.5 * A)
        print(f"4u cells at pose: {n_cell_maj} majority-covered "
              f"({len(cov)} touched) -- bench pristine flat lawn = 358 cells "
              f"(cellrim_steps.json)")

        # ---- (3) BOUNDARY by class + the moved boundary -------------------------------------
        ecnt = Counter()
        for t in comp:
            ps = [kk(p) for p in soup9[t]["w"]]
            for a, b in ((0, 1), (1, 2), (2, 0)):
                ecnt[tuple(sorted((ps[a], ps[b])))] += 1
        bnd = [e for e, n in ecnt.items() if n == 1 and e[0] != e[1]]
        cls_len = Counter()
        cls_edges = defaultdict(list)
        for e in bnd:
            L = elen(e)
            outs = [t for t in ET9[e] if t not in comp]
            if any(t in carry9 for t in outs):
                cls = "mesa-weld (closed by the carry)"
            elif any(t in apron9 for t in outs):
                cls = "apron-collar (closed by the carry)"
            elif outs:
                topos = {soup9[t]["topo"] for t in outs}
                if topos & GRASS_TOPO:
                    cls = "donor grass (uncarried) -> NEW junction"
                elif topos & ({ROCK} | PLATEAU_T):
                    cls = "rock/plateau (other feature) -> NEW junction"
                elif FOREST_T in topos:
                    cls = "forest (cross-component) -> NEW junction"
                else:
                    cls = f"topo-{sorted(topos)} -> NEW junction"
            else:
                border = ((on64(e[0][0]) and on64(e[1][0])
                           and abs(e[0][0] - e[1][0]) <= GRID_TOL)
                          or (on64(e[0][2]) and on64(e[1][2])
                              and abs(e[0][2] - e[1][2]) <= GRID_TOL))
                cls = ("open (interior block border T-junction) -> NEW junction"
                       if border else "OPEN AT SOUP EDGE (blob exceeds 3x3!)")
            cls_len[cls] += L
            cls_edges[cls].append(e)
        tot_bnd = sum(cls_len.values())
        closed = sum(v for k, v in cls_len.items() if "closed by the carry" in k)
        print(f"\n== {lbl}: (3) BOUNDARY ({tot_bnd:.1f}u) ==")
        for k, v in cls_len.most_common():
            print(f"   {v:7.1f}u ({v / tot_bnd:5.1%})  {k}")
        print(f"closes {closed:.1f}u against the carry; mints "
              f"{tot_bnd - closed:.1f}u of NEW boundary "
              f"(vs the {fw_len:.1f}u forest weld it answers)")
        # what the bench holds under every NEW-boundary edge midpoint
        under = Counter()
        for k, es in cls_edges.items():
            if "closed by the carry" in k:
                continue
            for e in es:
                mx = (e[0][0] + e[1][0]) / 2.0 + tx
                mz = (e[0][2] + e[1][2]) / 2.0 + tz
                if over_grass(mx, mz):
                    u = ("bench lawn" if d_banned(mx, mz) >= 2.0
                         else "bench lawn <2u of coast band")
                elif over_any(mx, mz):
                    u = "bench coast/sea mesh (NOT grass)"
                else:
                    u = "OFF-ISLAND (void)"
                under[(k, u)] += elen(e)
        print("bench under the NEW boundary (by length):")
        for (k, u), v in under.most_common():
            print(f"   {v:7.1f}u  [{k}]  over  [{u}]")

        # ---- (2) FIT at the pose (the apron's own clip test) --------------------------------
        vfit = vcoast = vgrassless = vvoid = 0
        n_tri_fit = n_tri_coast = n_tri_off = 0
        a_fit = a_coast = a_off = 0.0
        vkeys = sorted({kk(p) for t in comp for p in soup9[t]["w"]})
        vcls = {}
        for k3 in vkeys:
            px, pz = k3[0] + tx, k3[2] + tz
            if over_grass(px, pz):
                if d_banned(px, pz) >= 2.0:
                    vcls[k3] = "fit"
                    vfit += 1
                else:
                    vcls[k3] = "coastband"
                    vcoast += 1
            elif over_any(px, pz):
                vcls[k3] = "coastmesh"
                vgrassless += 1
            else:
                vcls[k3] = "void"
                vvoid += 1
        for t in comp:
            ks = [vcls[kk(p)] for p in soup9[t]["w"]]
            a = shoelace([(p[0], p[2]) for p in soup9[t]["w"]])
            if all(c == "fit" for c in ks):
                n_tri_fit += 1
                a_fit += a
            elif any(c in ("coastmesh", "void") for c in ks):
                n_tri_off += 1
                a_off += a
            else:
                n_tri_coast += 1
                a_coast += a
        print(f"\n== {lbl}: (2) FIT at the pose (the apron's clip test) ==")
        print(f"verts: {vfit} fit / {vcoast} <2u of coast band / "
              f"{vgrassless} over coast-sea mesh / {vvoid} OFF-ISLAND "
              f"of {len(vkeys)}")
        print(f"tris: {n_tri_fit} fully fit ({a_fit:.0f}u2 = "
              f"{a_fit / max(1e-9, area):.1%}), {n_tri_coast} clip at the coast band "
              f"({a_coast:.0f}u2), {n_tri_off} over coast/sea/void ({a_off:.0f}u2 = "
              f"{a_off / max(1e-9, area):.1%})")
        d_coast_all = [d_banned(k3[0] + tx, k3[2] + tz) for k3 in vkeys]
        print(f"distance to the bench coast band: min {min(d_coast_all):.1f} "
              f"p10 {pctl(d_coast_all, 10)}u (carve_forest's rehome gate wants "
              f">= 5.0u RIM_MARGIN)")

        # ---- (4) WALK -----------------------------------------------------------------------
        rises = []
        for e, n in ecnt.items():
            if e[0] == e[1]:
                continue
            rises.append(abs(e[0][1] - e[1][1]))
        slopes = []
        for t in comp:
            a3, b3, c3 = (np.array(p, dtype=float) for p in soup9[t]["w"])
            nrm = np.cross(b3 - a3, c3 - a3)
            nl = float(np.linalg.norm(nrm))
            if nl > 1e-9:
                slopes.append(math.degrees(math.acos(
                    max(-1.0, min(1.0, abs(float(nrm[1])) / nl)))))
        rim_steps = []
        for e in bnd:
            outs = [t for t in ET9[e] if t not in comp]
            if any(t in carry9 or t in apron9 for t in outs):
                continue                                    # rim onto the carry: not a lawn entry
            for p in (e[0], e[1]):
                px, pz = p[0] + tx, p[2] + tz
                gy = grass_y(px, pz)
                if gy is not None:
                    rim_steps.append(p[1] + DY - gy)
        print(f"\n== {lbl}: (4) WALK (forest = walkable class; pose is mesa-locked, "
              f"NO carve_forest rim lift) ==")
        print(f"internal edge rises: med {pctl(rises, 50)} p90 {pctl(rises, 90)} "
              f"max {max(rises):.2f}u; {sum(1 for r in rises if r > CLIMB)} over the "
              f"{CLIMB} ceiling (donor-verbatim -- stock-lawful by construction)")
        print(f"tri slopes: med {pctl(slopes, 50)} p90 {pctl(slopes, 90)} "
              f"max {max(slopes):.1f} deg")
        if rim_steps:
            print(f"rim step onto bench lawn (blob y - lawn y, {len(rim_steps)} "
                  f"stations): med {pctl(rim_steps, 50)} p90 {pctl(rim_steps, 90)} "
                  f"max {max(rim_steps):.2f}u; {sum(1 for s in rim_steps if s > CLIMB)} "
                  f"over the climb ceiling (walk-IN blocked there)")
        else:
            print("rim step onto bench lawn: NO rim stations over bench grass")

        R["blobs"].append(dict(
            label=lbl, n_tris=len(comp), area=round(area, 1),
            by_block={str(k): v for k, v in by_blk.items()},
            posed_bbox=dict(x=[round(min(xs), 1), round(max(xs), 1)],
                            z=[round(min(zs), 1), round(max(zs), 1)]),
            y_donor=[round(min(ys), 2), round(max(ys), 2)],
            y_posed=[round(min(ys) + DY, 2), round(max(ys) + DY, 2)],
            cells_majority=n_cell_maj, cells_touched=len(cov),
            boundary_len=round(tot_bnd, 1),
            boundary_by_class={k: round(v, 1) for k, v in cls_len.items()},
            closed_against_carry=round(closed, 1),
            new_boundary=round(tot_bnd - closed, 1),
            bench_under_new={f"{k} | {u}": round(v, 1)
                             for (k, u), v in under.items()},
            fit=dict(v_fit=vfit, v_coastband=vcoast, v_coastmesh=vgrassless,
                     v_void=vvoid,
                     tri_fit=n_tri_fit, tri_coast=n_tri_coast, tri_off=n_tri_off,
                     area_fit=round(a_fit, 1), area_off=round(a_off, 1),
                     area_fit_frac=round(a_fit / max(1e-9, area), 4),
                     d_coast_min=round(min(d_coast_all), 2),
                     d_coast_p10=pctl(d_coast_all, 10)),
            walk=dict(rise_p90=pctl(rises, 90), rise_max=round(max(rises), 3),
                      n_rise_over=sum(1 for r in rises if r > CLIMB),
                      slope_p90=pctl(slopes, 90),
                      slope_max=round(max(slopes), 1),
                      rim_step_med=pctl(rim_steps, 50),
                      rim_step_p90=pctl(rim_steps, 90),
                      rim_step_max=round(max(rim_steps), 3) if rim_steps else None,
                      rim_step_over=sum(1 for s in rim_steps if s > CLIMB))))

    R["pose"] = dict(tx=tx, tz=tz, dy=DY)
    R["weld"] = dict(total=round(weld_len, 1), forest=round(fw_len, 1))
    R["limits"] = [
        "blob soup is the 3x3 donor neighborhood; a boundary class 'OPEN AT SOUP EDGE' "
        "means the true blob is even larger than measured",
        "fit test = apron_carry's own clip (over pristine bench grass AND >= 2u from "
        "non-grass bench verts) at the fixed pose (-576,+416) + dy -0.14; no re-posing "
        "or rim lift is evaluated (the pose is mesa-locked by the design)",
        "bench-under classification samples edge MIDPOINTS only",
        "walkability is geometric (edge rises / tri slopes vs the 2.34375 ceiling); "
        "no engine raycast is simulated",
        "v-row numbers use out/rock_tiles.json's atlas phase, same as fringe_at_weld_probe",
    ]
    (OUTD / "forestblob_probe.json").write_text(json.dumps(R, indent=1))
    print(f"\nartifact -> {OUTD / 'forestblob_probe.json'}  "
          f"({time.time() - t_start:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
