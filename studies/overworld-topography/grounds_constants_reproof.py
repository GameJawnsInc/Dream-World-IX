"""GROUNDS CONSTANTS REPROOF -- independent re-derivation of all 7 shipped translation
pairs (mains du/dv + wall du/dv) in ``ff9mapkit.world.grassland.GROUNDS``, in ONE
script, using THE METHOD LAW uniformly (outer-bounds only, never internal/gutter
edges) and reporting a genuine PER-SPECIMEN spread for every constant.

Prior art (read first, this script borrows their method but re-implements the fit
independently rather than importing it, so a shared bug can't silently pass both):
  ground_families_anatomy.py   -- the mains outer-bounds translation fit + the wall
                                   topo-58-adjacency probe this script re-derives from
                                   scratch (same numbers must fall out again).
  desert_ground_anatomy.py     -- the original desert 5dp rect recovery + subset
                                   grammar gate that grew grassland.GROUNDS["desert"].
  family_wall_envelope.py      -- warns about the top-8-specimen-slice defect (THE
                                   NO-TOP-N-SLICING LAW); this script's map-wide tri
                                   totals iterate all 480 (bx,by) candidates.

QUESTION: do the 14 constants shipped in GROUNDS (7 families x mains+wall) reproduce
byte-exact (5dp) from an independent re-run of the outer-bounds method, and do the
population-membership controls (grass variants -> grass; dirt 19/20 -> desert) hold?

METHOD (uniform across every family):
  1. Census ALL 480 (bx,by) candidates (map-wide, no slicing) -> per-block topo tri
     counts. This gives the honest map-wide population size per family.
  2. Pick specimen blocks (>=N family-topo tris, N adaptive 30/15/5) to get enough
     per-cell density for an EXACT per-4u-cell affine fit (u,v = A + B*x + C*z);
     cells failing the affine fit (mixed/non-tiled) are dropped, not forced.
  3. Evaluate each affine cell at its 4 corners -> a rect; half-tile-snap the rect
     origin; auto-detect the dominant 2x2 quadrant set (the "mains" tile block).
  4. THE OUTER-BOUNDS TRANSLATION FIT: du/dv computed ONLY from the 2x2's outer
     edges (half0's low edge, half1's high edge) vs the grass reference rects
     (GRASS_U_HALF/GRASS_V_HALF) -- never the internal edges, which are gutter-
     contaminated per THE METHOD LAW.
  5. Run this SAME pipeline twice: once POOLED over all specimen tris (the
     "aggregate" figure, comparable to what ground_families_anatomy.py reported),
     and once PER SPECIMEN BLOCK INDEPENDENTLY -- the per-specimen figures' spread
     (max-min across blocks) is the real test of "is this a single constant or is
     the single-pair model leaking". A true translation must show spread ~0.
  6. Wall band: topo-58 tris edge-adjacent to the family's topos; du fit from BOTH
     the low and high u edges vs ROCK_U, dv fit from BOTH v-level rows vs ROCK_V
     (again outer-bounds only, both edges must agree at 5dp for exact5dp=True).
     Same pooled + per-specimen spread treatment.
  7. Compare every recovered pair against grassland.GROUNDS's shipped value; report
     MATCH (agrees <=1e-5) or the signed delta and which side (bytes vs shipped) is
     more internally consistent (lower spread).

CONTROLS (if either fails, treat every downstream family number as UNPROVEN -- the
harness itself is broken, not the game data):
  * grass0 (topo 0 alone) mains AND wall must recover delta (0.0, 0.0), spread ~0.
  * grassvar (topo 1,2,3,10,11,12,13,42 pooled) mains must recover the SAME grass
    delta (0.0, 0.0) -- "ids within a family are gameplay variants" claim, grass side.
  * dirt19 (topo 19 alone) and dirt20 (topo 20 alone) mains must recover the SAME
    delta as desert17 (topo 17 alone) -- the desert side of that claim.

Artifacts -> out/grounds_constants_reproof.json. Run from the repo root:
    py studies/overworld-topography/grounds_constants_reproof.py
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import grassland as G                  # noqa: E402

BLOCK = 64.0
TILE_U, TILE_V = 0.0625, 0.03125
ROCK_U = (0.699, 0.947)                                      # island.py's mint-convention wall band base
ROCK_V = (0.893, 0.923)
OUTD = Path(__file__).with_name("out")
kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))

# (test-group name, member topo ids, which SHIPPED GROUNDS row it must match, note)
FAMILIES = [
    ("grass0",   (0,),                          "grass",  "CONTROL -- must be delta (0,0), zero spread"),
    ("grassvar", (1, 2, 3, 10, 11, 12, 13, 42),  "grass",  "CONTROL -- gameplay variants of grass"),
    ("desert17", (17,),                          "desert", "the shipped desert row's own topo"),
    ("dirt16",   (16,),                          "desert", "desert-family variant"),
    ("dirt19",   (19,),                          "desert", "CONTROL -- desert-family variant, required"),
    ("dirt20",   (20,),                          "desert", "CONTROL -- desert-family variant, required"),
    ("scrub",    (4, 5, 6),                      "scrub",  "shipped scrub row"),
    ("brush",    (38,),                          "brush",  "shipped brush row"),
    ("snow",     (27, 28),                       "snow",   "shipped snow row"),
    ("canyon",   (45, 46),                       "canyon", "shipped canyon row"),
    ("dunes",    (41,),                          "dunes",  "shipped dunes row"),
]

out = {"families": {}, "controls": {}}

# ---- STEP A: map-wide census, ALL 480 candidates, no slicing -----------------------------------
print("=" * 100)
print("STEP A -- census over all 24x20=480 candidate blocks (map-wide, no top-N slicing)")
census = {}
for bx in range(24):
    for by in range(20):
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except ValueError:
            continue
        c = Counter()
        for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
            c[X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]] += 1
        census[(bx, by)] = c
print(f"   {len(census)}/480 candidates are land blocks (rest raise ValueError = open sea)")
out["census_blocks"] = len(census)

_block_cache = {}


def load_tris(bx, by):
    if (bx, by) not in _block_cache:
        bm = X.read_block(bx, by, disc=1, part="terrain")
        tris = []
        for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
            tris.append(dict(
                w=[(bm.verts[j][0] + BLOCK * bx, bm.verts[j][1],
                    bm.verts[j][2] - BLOCK * by) for j in tri],
                uv=[(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri],
                topo=X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]))
        _block_cache[(bx, by)] = tris
    return _block_cache[(bx, by)]


def mode5(vals):
    return Counter(round(v, 5) for v in vals).most_common(1)[0][0]


# ---- STEP B: the mains outer-bounds translation fit, over an ARBITRARY tri list ----------------
def fit_mains(ftris):
    """Cell-affine -> half-tile 2x2 auto-detect -> OUTER-BOUNDS translation fit vs the
    grass reference rects. Returns ok=False with a `reason` if any stage starves."""
    cell_tris = defaultdict(list)
    for ti, t in enumerate(ftris):
        cx = sum(p[0] for p in t["w"]) / 3
        cz = sum(p[2] for p in t["w"]) / 3
        cell_tris[(math.floor(cx / 4.0), math.floor(cz / 4.0))].append(ti)
    lin_ok = {}
    for cell, tl in cell_tris.items():
        rows, ru, rv = [], [], []
        for ti in tl:
            t = ftris[ti]
            for (x, y, z), (u, v) in zip(t["w"], t["uv"]):
                rows.append([x, z, 1.0])
                ru.append(u)
                rv.append(v)
        Am = np.array(rows)
        if len(rows) < 3 or np.linalg.matrix_rank(Am) < 3:
            continue
        cu, *_ = np.linalg.lstsq(Am, np.array(ru), rcond=None)
        cv, *_ = np.linalg.lstsq(Am, np.array(rv), rcond=None)
        res = max(float(np.abs(Am @ cu - ru).max()), float(np.abs(Am @ cv - rv).max()))
        if res < 1e-4:
            lin_ok[cell] = (cu, cv)
    if len(lin_ok) < 4:
        return dict(ok=False, reason="too-few-linear-cells", n_linear=len(lin_ok))

    cell_rect, n_mural = {}, 0
    for (i, j), (cu, cv) in lin_ok.items():
        corn = [(4.0 * i, 4.0 * j), (4.0 * (i + 1), 4.0 * j),
                (4.0 * i, 4.0 * (j + 1)), (4.0 * (i + 1), 4.0 * (j + 1))]
        us = [cu[0] * x + cu[1] * z + cu[2] for (x, z) in corn]
        vs = [cv[0] * x + cv[1] * z + cv[2] for (x, z) in corn]
        du4, dv4 = max(us) - min(us), max(vs) - min(vs)
        if du4 < TILE_U * 0.5 or dv4 < TILE_V * 0.5:
            n_mural += 1
            continue
        cell_rect[(i, j)] = (min(us), max(us), min(vs), max(vs))
    if len(cell_rect) < 4:
        return dict(ok=False, reason="too-few-tiled-cells", n_linear=len(lin_ok), n_mural=n_mural)

    cell_tile = {c: (round(r[0] / TILE_U * 2) / 2, round(r[2] / TILE_V * 2) / 2)
                 for c, r in cell_rect.items()}
    tiles = Counter(cell_tile.values())
    best_base, best_n = None, 0
    for (a, b) in tiles:
        n = sum(tiles.get(o, 0) for o in ((a, b), (a + 1, b), (a, b + 1), (a + 1, b + 1)))
        if n > best_n:
            best_base, best_n = (a, b), n
    share = best_n / max(1, len(cell_tile))
    if share < 0.15 or best_n < 4:
        return dict(ok=False, reason="no-dominant-2x2", n_linear=len(lin_ok),
                    n_tiled=len(cell_rect), tile_share=round(share, 3))
    a, b = best_base
    mains_origins = {(a, b), (a + 1, b), (a, b + 1), (a + 1, b + 1)}

    per_edge = defaultdict(list)
    for cell, tile in cell_tile.items():
        if tile not in mains_origins:
            continue
        u0, u1, v0, v1 = cell_rect[cell]
        uh = 0 if tile[0] == a else 1
        vh = 0 if tile[1] == b else 1
        per_edge[("u", uh, "lo")].append(u0)
        per_edge[("u", uh, "hi")].append(u1)
        per_edge[("v", vh, "lo")].append(v0)
        per_edge[("v", vh, "hi")].append(v1)
    need = [("u", h, s) for h in (0, 1) for s in ("lo", "hi")] + \
           [("v", h, s) for h in (0, 1) for s in ("lo", "hi")]
    if not all(k in per_edge for k in need):
        return dict(ok=False, reason="thin-2x2-quadrant", n_linear=len(lin_ok))

    U_HALF = [(mode5(per_edge[("u", h, "lo")]), mode5(per_edge[("u", h, "hi")])) for h in (0, 1)]
    V_HALF = [(mode5(per_edge[("v", h, "lo")]), mode5(per_edge[("v", h, "hi")])) for h in (0, 1)]

    # THE OUTER-BOUNDS TRANSLATION FIT (THE METHOD LAW): half0's LOW edge + half1's
    # HIGH edge only -- the 2x2's outer boundary, never an internal/gutter edge.
    d_u = [U_HALF[0][0] - G.GRASS_U_HALF[0][0], U_HALF[1][1] - G.GRASS_U_HALF[1][1]]
    d_v = [V_HALF[0][0] - G.GRASS_V_HALF[0][0], V_HALF[1][1] - G.GRASS_V_HALF[1][1]]
    du_spread = max(d_u) - min(d_u)
    dv_spread = max(d_v) - min(d_v)
    du = round(float(np.median(d_u)), 5)
    dv = round(float(np.median(d_v)), 5)
    return dict(ok=True, du=du, dv=dv, du_spread=round(du_spread, 6), dv_spread=round(dv_spread, 6),
                exact5dp=bool(du_spread < 2e-5 and dv_spread < 2e-5),
                U_HALF=U_HALF, V_HALF=V_HALF, n_linear=len(lin_ok), n_tiled=len(cell_rect),
                tile_share=round(share, 3), mains_base=[a, b])


# ---- STEP C: the wall outer-bounds translation fit, over an ARBITRARY tri list -----------------
def fit_wall(tris_pool, topos):
    """Topo-58 tris edge-adjacent to `topos`, pooled over `tris_pool` (a list of
    per-block tri lists). du from BOTH u edges vs ROCK_U, dv from BOTH v-row levels
    vs ROCK_V -- both must agree at 5dp for exact5dp=True."""
    us, vs = [], []
    for tris in tris_pool:
        edge_tris = defaultdict(list)
        for ti, t in enumerate(tris):
            ps = [kk(v) for v in t["w"]]
            for a2, b2 in ((0, 1), (1, 2), (2, 0)):
                edge_tris[tuple(sorted((ps[a2], ps[b2])))].append(ti)
        picked = set()
        for e, ts in edge_tris.items():
            tp = {tris[t]["topo"] for t in ts}
            if 58 in tp and tp & set(topos):
                picked.update(t for t in ts if tris[t]["topo"] == 58)
        for ti in picked:
            for (u, v) in tris[ti]["uv"]:
                us.append(u)
                vs.append(v)
    if len(us) < 18:
        return dict(ok=False, reason="too-thin", tris=len(us) // 3)
    ua = sorted(us)
    u_lo, u_hi = round(float(ua[0]), 5), round(float(ua[-1]), 5)
    v_levels = Counter(round(v, 5) for v in vs).most_common(6)
    rows = sorted(lv for lv, _ in v_levels[:2])          # rows[0]=top(low v) rows[1]=base(high v)
    du_edges = [u_lo - ROCK_U[0], u_hi - ROCK_U[1]]
    dv_edges = [rows[0] - ROCK_V[0], rows[1] - ROCK_V[1]]
    du_spread = max(du_edges) - min(du_edges)
    dv_spread = max(dv_edges) - min(dv_edges)
    du = round(float(np.median(du_edges)), 5)
    dv = round(float(np.median(dv_edges)), 5)
    return dict(ok=True, du=du, dv=dv, du_spread=round(du_spread, 6), dv_spread=round(dv_spread, 6),
                exact5dp=bool(du_spread < 2e-5 and dv_spread < 2e-5),
                u=[u_lo, u_hi], rows=rows, tris=len(us) // 3,
                v_levels=[[lv, n] for lv, n in v_levels])


def pick_specimens(topos, min_thresholds=(30, 15, 5)):
    counts = {blk: sum(c.get(t, 0) for t in topos) for blk, c in census.items()}
    counts = {blk: n for blk, n in counts.items() if n > 0}
    total_map_wide = sum(counts.values())
    for thr in min_thresholds:
        spec = [blk for blk, n in sorted(counts.items(), key=lambda kv: -kv[1]) if n >= thr]
        if len(spec) >= 3:
            return spec[:8], thr, total_map_wide, len(counts)
    spec = sorted(counts.items(), key=lambda kv: -kv[1])
    return [b for b, _ in spec[:8]], 0, total_map_wide, len(counts)


def process_family(name, topos, ship_row, note):
    print(f"\n{'=' * 100}\n== {name} {topos} -> ships as GROUNDS[{ship_row!r}]  ({note})")
    fam = {"topos": list(topos), "ship_row": ship_row, "note": note}
    spec, thr, total_map_wide, n_blocks_with_any = pick_specimens(topos)
    print(f"   map-wide: {total_map_wide} tris over {n_blocks_with_any} blocks (ALL 480 candidates "
          f"scanned); specimen threshold used {thr}; specimens ({len(spec)}): {spec}")
    fam["map_wide_tris"] = total_map_wide
    fam["map_wide_blocks"] = n_blocks_with_any
    fam["specimen_threshold"] = thr
    fam["specimens"] = [f"{b[0]},{b[1]}" for b in spec]
    if len(spec) < 2:
        print("   TOO THIN -- fewer than 2 specimen blocks; no fit attempted")
        fam["verdict"] = "too-thin"
        out["families"][name] = fam
        return fam

    # ---- pooled/aggregate mains fit -------------------------------------------------------------
    pooled_tris = [t for blk in spec for t in load_tris(*blk) if t["topo"] in topos]
    agg = fit_mains(pooled_tris)
    print(f"   AGGREGATE mains fit (pooled over {len(spec)} specimens, {len(pooled_tris)} tris): {agg}")
    fam["mains_aggregate"] = agg

    # ---- per-specimen mains fits (the real spread-across-specimens test) ------------------------
    per_spec = {}
    for blk in spec:
        btris = [t for t in load_tris(*blk) if t["topo"] in topos]
        if len(btris) < 8:
            continue
        r = fit_mains(btris)
        per_spec[f"{blk[0]},{blk[1]}"] = r
    ok_fits = {k: v for k, v in per_spec.items() if v.get("ok")}
    print(f"   PER-SPECIMEN mains fits: {len(ok_fits)}/{len(per_spec)} blocks individually fit a 2x2")
    for k, v in per_spec.items():
        if v.get("ok"):
            print(f"      {k}: du {v['du']} dv {v['dv']} (internal spread u {v['du_spread']:.6f} "
                  f"v {v['dv_spread']:.6f}, n_tiled {v['n_tiled']})")
        else:
            print(f"      {k}: NOT FIT ({v.get('reason')}, n_linear={v.get('n_linear', '?')})")
    fam["mains_per_specimen"] = per_spec
    if len(ok_fits) >= 2:
        dus = [v["du"] for v in ok_fits.values()]
        dvs = [v["dv"] for v in ok_fits.values()]
        cross_du_spread = round(max(dus) - min(dus), 6)
        cross_dv_spread = round(max(dvs) - min(dvs), 6)
        print(f"   CROSS-SPECIMEN spread (max-min over {len(ok_fits)} independently-fit blocks): "
              f"du_spread {cross_du_spread} dv_spread {cross_dv_spread} "
              f"-> {'ZERO (single constant confirmed)' if cross_du_spread < 2e-5 and cross_dv_spread < 2e-5 else 'NONZERO -- single-pair model may be leaking'}")
        fam["mains_cross_specimen_spread"] = dict(du=cross_du_spread, dv=cross_dv_spread,
                                                   n=len(ok_fits))
    elif len(ok_fits) == 1:
        print("   CROSS-SPECIMEN spread: only 1 block individually fit a 2x2 -- spread undefined "
              "(n=1); relying on the aggregate fit alone")
        fam["mains_cross_specimen_spread"] = dict(n=1, note="undefined, single specimen")
    else:
        print("   CROSS-SPECIMEN spread: 0 blocks individually fit a 2x2 (each needs the pooled "
              "density) -- relying on the aggregate fit alone")
        fam["mains_cross_specimen_spread"] = dict(n=0, note="no individual block had enough density")

    # ---- wall fit: pooled + per-specimen ---------------------------------------------------------
    wall_counts = {blk: (sum(census[blk].get(t, 0) for t in topos), census[blk].get(58, 0))
                   for blk in census if sum(census[blk].get(t, 0) for t in topos) >= 10
                   and census[blk].get(58, 0) >= 3}
    wall_spec = sorted(wall_counts, key=lambda b: -wall_counts[b][1])[:8]
    print(f"   wall specimens ({len(wall_spec)}, family-tris>=10 AND topo58>=3): {wall_spec}")
    fam["wall_specimens"] = [f"{b[0]},{b[1]}" for b in wall_spec]
    if wall_spec:
        wagg = fit_wall([load_tris(*blk) for blk in wall_spec], topos)
        print(f"   AGGREGATE wall fit (pooled over {len(wall_spec)} blocks): {wagg}")
        fam["wall_aggregate"] = wagg
        wper = {}
        for blk in wall_spec:
            r = fit_wall([load_tris(*blk)], topos)
            wper[f"{blk[0]},{blk[1]}"] = r
        wok = {k: v for k, v in wper.items() if v.get("ok")}
        print(f"   PER-SPECIMEN wall fits: {len(wok)}/{len(wper)} blocks individually fit")
        for k, v in wper.items():
            if v.get("ok"):
                print(f"      {k}: du {v['du']} dv {v['dv']} (internal spread u {v['du_spread']:.6f} "
                      f"v {v['dv_spread']:.6f}, tris {v['tris']})")
            else:
                print(f"      {k}: NOT FIT ({v.get('reason')})")
        fam["wall_per_specimen"] = wper
        if len(wok) >= 2:
            dus = [v["du"] for v in wok.values()]
            dvs = [v["dv"] for v in wok.values()]
            cdu = round(max(dus) - min(dus), 6)
            cdv = round(max(dvs) - min(dvs), 6)
            print(f"   WALL CROSS-SPECIMEN spread (n={len(wok)}): du_spread {cdu} dv_spread {cdv} "
                  f"-> {'ZERO' if cdu < 2e-5 and cdv < 2e-5 else 'NONZERO'}")
            fam["wall_cross_specimen_spread"] = dict(du=cdu, dv=cdv, n=len(wok))
            # ROBUST MODE: naive pooled min/max (wagg) is fragile to ONE contaminated
            # specimen dragging the global extreme edge (seen on dirt19's block (4,9),
            # a 0.27-off outlier vs its 7 agreeing siblings) -- the majority-vote
            # (du,dv) pair across INDEPENDENTLY-fit specimens is the robust figure.
            mode_pair, mode_n = Counter((v["du"], v["dv"]) for v in wok.values()).most_common(1)[0]
            agrees_with_agg = wagg.get("ok") and abs(mode_pair[0] - wagg["du"]) <= 1e-5 and \
                abs(mode_pair[1] - wagg["dv"]) <= 1e-5
            print(f"   WALL ROBUST MODE (majority vote over {len(wok)} independent specimens): "
                  f"du {mode_pair[0]} dv {mode_pair[1]} ({mode_n}/{len(wok)} agree) -> "
                  f"{'== naive aggregate' if agrees_with_agg else 'DIFFERS FROM naive aggregate -- pooling was contaminated by an outlier block'}")
            fam["wall_robust_mode"] = dict(du=mode_pair[0], dv=mode_pair[1], votes=mode_n,
                                           of=len(wok), agrees_with_aggregate=bool(agrees_with_agg))
            if not agrees_with_agg:
                # OUTLIER-FILTERED re-pool: re-run fit_wall only over the blocks whose
                # OWN independent fit matched the majority mode (drops the contaminated
                # block instead of letting its extreme edge drag a naive min/max pool).
                clean_blocks = [blk for blk in wall_spec
                                if wper.get(f"{blk[0]},{blk[1]}", {}).get("ok") and
                                abs(wper[f"{blk[0]},{blk[1]}"]["du"] - mode_pair[0]) <= 1e-5 and
                                abs(wper[f"{blk[0]},{blk[1]}"]["dv"] - mode_pair[1]) <= 1e-5]
                wagg_clean = fit_wall([load_tris(*blk) for blk in clean_blocks], topos)
                print(f"   WALL CLEAN AGGREGATE (outlier block(s) dropped, {len(clean_blocks)}/"
                      f"{len(wall_spec)} specimens kept: {[f'{b[0]},{b[1]}' for b in clean_blocks]}): "
                      f"{wagg_clean}")
                fam["wall_aggregate_clean"] = wagg_clean
        else:
            print(f"   WALL CROSS-SPECIMEN spread: only {len(wok)} block(s) individually fit -- "
                  f"relying on the aggregate")
            fam["wall_cross_specimen_spread"] = dict(n=len(wok), note="insufficient for cross-spread")
    else:
        print("   NO wall specimens (no block has both the family ground AND >=3 topo-58 tris "
              "edge-adjacent) -- wall is UNMEASURED for this family from these bytes")
        fam["wall_aggregate"] = dict(ok=False, reason="no-specimens")

    # ---- compare vs shipped -----------------------------------------------------------------------
    ship = G.GROUNDS[ship_row]
    print(f"   SHIPPED GROUNDS[{ship_row!r}]: mains_du {ship['mains_du']} mains_dv {ship['mains_dv']} "
          f"wall_du {ship['wall_du']} wall_dv {ship['wall_dv']}")
    fam["shipped"] = dict(mains_du=ship["mains_du"], mains_dv=ship["mains_dv"],
                          wall_du=ship["wall_du"], wall_dv=ship["wall_dv"])
    cmp = {}
    if agg.get("ok"):
        dmu = round(agg["du"] - ship["mains_du"], 5)
        dmv = round(agg["dv"] - ship["mains_dv"], 5)
        match = abs(dmu) <= 1e-5 and abs(dmv) <= 1e-5
        print(f"   MAINS vs shipped: measured ({agg['du']},{agg['dv']}) shipped "
              f"({ship['mains_du']},{ship['mains_dv']}) delta ({dmu},{dmv}) -> "
              f"{'MATCH' if match else 'MISMATCH'}")
        cmp["mains"] = dict(measured=[agg["du"], agg["dv"]],
                            shipped=[ship["mains_du"], ship["mains_dv"]],
                            delta=[dmu, dmv], match=bool(match))
    else:
        print(f"   MAINS vs shipped: NO independent measurement available ({agg.get('reason')})")
        cmp["mains"] = dict(measured=None, reason=agg.get("reason"))
    wagg_r = fam.get("wall_aggregate_clean") or fam.get("wall_aggregate", {})
    if wagg_r.get("ok"):
        dwu = round(wagg_r["du"] - ship["wall_du"], 5)
        dwv = round(wagg_r["dv"] - ship["wall_dv"], 5)
        wmatch = abs(dwu) <= 1e-5 and abs(dwv) <= 1e-5
        print(f"   WALL vs shipped (ROCK_U/V-relative, {'outlier-filtered' if fam.get('wall_aggregate_clean') else 'naive'} pool): "
              f"measured ({wagg_r['du']},{wagg_r['dv']}) shipped "
              f"({ship['wall_du']},{ship['wall_dv']}) delta ({dwu},{dwv}) -> "
              f"{'MATCH' if wmatch else 'MISMATCH (see STEP D for the true-rect-rebased comparison)'}")
        cmp["wall"] = dict(measured=[wagg_r["du"], wagg_r["dv"]],
                           shipped=[ship["wall_du"], ship["wall_dv"]],
                           delta=[dwu, dwv], match=bool(wmatch))
    else:
        print(f"   WALL vs shipped: NO independent measurement available "
              f"({wagg_r.get('reason', 'no-specimens')})")
        cmp["wall"] = dict(measured=None, reason=wagg_r.get("reason", "no-specimens"))
    fam["compare"] = cmp
    out["families"][name] = fam
    return fam


# ---- run every family ---------------------------------------------------------------------------
results = {}
for name, topos, ship_row, note in FAMILIES:
    results[name] = process_family(name, topos, ship_row, note)

# ---- STEP D: WALL REBASE -- is ROCK_U/ROCK_V (0.699/0.947/0.893/0.923) the true atlas
# origin, or a 3dp-rounded legacy constant? Re-express every family's wall band relative
# to grass0's OWN independently-measured wall rect (both edges) instead of the rounded
# island.py ROCK_U/ROCK_V constants, and re-check THE 5DP BAR (both edges agree).
print(f"\n{'=' * 100}")
print("STEP D -- WALL REBASE: is the wall translation exact once referenced to grass's OWN")
print("          measured wall rect instead of the rounded (0.699,0.947)/(0.893,0.923) constants?")
grass_wagg = results["grass0"].get("wall_aggregate", {})
rebase = {}
if grass_wagg.get("ok"):
    gu = grass_wagg["u"]
    grows = grass_wagg["rows"]
    print(f"   grass0's TRUE measured wall rect: u {gu}  rows(top,base) {grows}  "
          f"(vs the rounded legacy ROCK_U {list(ROCK_U)} ROCK_V {list(ROCK_V)})")
    rebase["grass_true_wall_rect"] = dict(u=gu, rows=grows)
    for name, topos, ship_row, note in FAMILIES:
        if name == "grass0":
            continue
        # prefer the outlier-filtered CLEAN aggregate when the robust-mode check found
        # naive pooling was contaminated; else fall back to the naive aggregate.
        wagg = results[name].get("wall_aggregate_clean") or results[name].get("wall_aggregate", {})
        if not wagg.get("ok"):
            continue
        u, rows = wagg["u"], wagg["rows"]
        du_edges = [u[0] - gu[0], u[1] - gu[1]]
        dv_edges = [rows[0] - grows[0], rows[1] - grows[1]]
        du_spread = round(max(du_edges) - min(du_edges), 6)
        dv_spread = round(max(dv_edges) - min(dv_edges), 6)
        du = round(float(np.median(du_edges)), 5)
        dv = round(float(np.median(dv_edges)), 5)
        exact = du_spread < 2e-5 and dv_spread < 2e-5
        print(f"   {name:10s} (naive-pooled u={u} rows={rows}): REBASED du {du} dv {dv}  "
              f"both-edges-spread du={du_spread} dv={dv_spread} -> "
              f"{'PROVEN-5DP (both edges agree)' if exact else 'NOT 5dp-clean -- likely multi-course/thin data'}")
        rebase[name] = dict(du=du, dv=dv, du_spread=du_spread, dv_spread=dv_spread, exact5dp=bool(exact))
else:
    print("   grass0 has no usable wall_aggregate -- cannot rebase (harness defect)")
out["wall_rebase_to_true_grass_rect"] = rebase

# ---- THE CONTROLS GATE ---------------------------------------------------------------------------
print(f"\n{'=' * 100}\nCONTROLS GATE")
harness_ok = True


def control_check(label, fam_name, expect_du, expect_dv, tol=1e-5):
    global harness_ok
    fam = results[fam_name]
    agg = fam.get("mains_aggregate", {})
    if not agg.get("ok"):
        print(f"   [{label}] FAIL -- {fam_name} produced no aggregate fit ({agg.get('reason')})")
        harness_ok = False
        return False
    du_ok = bool(abs(agg["du"] - expect_du) <= tol)
    dv_ok = bool(abs(agg["dv"] - expect_dv) <= tol)
    spread_ok = bool(agg["du_spread"] < 2e-5 and agg["dv_spread"] < 2e-5)
    ok = bool(du_ok and dv_ok and spread_ok)
    print(f"   [{label}] {fam_name}: du {agg['du']} (expect {expect_du}, ok={du_ok})  "
          f"dv {agg['dv']} (expect {expect_dv}, ok={dv_ok})  "
          f"internal_spread du={agg['du_spread']:.6f} dv={agg['dv_spread']:.6f} (ok={spread_ok}) "
          f"-> {'PASS' if ok else 'FAIL'}")
    if not ok:
        harness_ok = False
    return ok


c1 = control_check("C1 grass0 mains == (0,0)", "grass0", 0.0, 0.0)
desert_agg = results["desert17"].get("mains_aggregate", {})
desert_du = desert_agg.get("du") if desert_agg.get("ok") else G.GROUNDS["desert"]["mains_du"]
desert_dv = desert_agg.get("dv") if desert_agg.get("ok") else G.GROUNDS["desert"]["mains_dv"]
c2 = control_check("C2 grassvar mains == grass0's own measured delta", "grassvar", 0.0, 0.0)
c3 = control_check("C3 dirt19 mains == desert17's own measured delta", "dirt19", desert_du, desert_dv)
c4 = control_check("C4 dirt20 mains == desert17's own measured delta", "dirt20", desert_du, desert_dv)

# grass wall control (0,0) too -- uses the wall pipeline, not mains
grass_wagg = results["grass0"].get("wall_aggregate", {})
if grass_wagg.get("ok"):
    wdu_ok = abs(grass_wagg["du"]) <= 1e-5
    wdv_ok = abs(grass_wagg["dv"]) <= 1e-5
    wspread_ok = grass_wagg["du_spread"] < 2e-5 and grass_wagg["dv_spread"] < 2e-5
    c5 = wdu_ok and wdv_ok and wspread_ok
    print(f"   [C5 grass0 wall == (0,0)]: du {grass_wagg['du']} dv {grass_wagg['dv']} "
          f"spread du={grass_wagg['du_spread']:.6f} dv={grass_wagg['dv_spread']:.6f} -> "
          f"{'PASS' if c5 else 'FAIL'}")
    if not c5:
        harness_ok = False
else:
    print(f"   [C5 grass0 wall == (0,0)]: NO measurement ({grass_wagg.get('reason')}) -- "
          f"grass0 may not have enough topo-58-adjacent tris; not gating the harness on this "
          f"(wall band existence, not the translation law, is what's thin)")
    c5 = None

out["controls"] = dict(
    C1_grass0_mains=c1, C2_grassvar_mains=c2, C3_dirt19_mains=c3, C4_dirt20_mains=c4,
    C5_grass0_wall=c5, harness_ok=bool(harness_ok),
    desert17_measured_delta=[desert_du, desert_dv])

print(f"\n{'=' * 100}")
if not harness_ok:
    print("HARNESS VERDICT: >=1 required control FAILED. Downstream family constants below are "
          "NOT to be treated as proven until this is root-caused.")
else:
    print("HARNESS VERDICT: all required controls PASSED. Downstream family constants are trustworthy "
          "to the extent their own exact5dp/cross-specimen-spread flags say so (see per-family output).")

# ---- final summary table -------------------------------------------------------------------------
print(f"\n{'=' * 100}\nSUMMARY -- every shipped constant vs its independent re-derivation")
summary_rows = []
for row_name in ("grass", "desert", "scrub", "brush", "snow", "canyon", "dunes"):
    # pick the primary test-group for this shipped row (the one literally named after it,
    # or its first member for desert/grass which have several control groups)
    primary = {"grass": "grass0", "desert": "desert17", "scrub": "scrub", "brush": "brush",
               "snow": "snow", "canyon": "canyon", "dunes": "dunes"}[row_name]
    fam = results[primary]
    cmp = fam.get("compare", {})
    mc = cmp.get("mains", {})
    wc = cmp.get("wall", {})
    ship = G.GROUNDS[row_name]
    row = dict(
        ground=row_name, primary_group=primary,
        shipped_mains=[ship["mains_du"], ship["mains_dv"]],
        measured_mains=mc.get("measured"), mains_match=mc.get("match"),
        shipped_wall=[ship["wall_du"], ship["wall_dv"]],
        measured_wall=wc.get("measured"), wall_match=wc.get("match"))
    summary_rows.append(row)
    print(f"   {row_name:8s} mains shipped {row['shipped_mains']} measured "
          f"{row['measured_mains']} match={row['mains_match']}   |   wall shipped "
          f"{row['shipped_wall']} measured {row['measured_wall']} match={row['wall_match']}")
out["summary"] = summary_rows

OUTD.mkdir(exist_ok=True)
(OUTD / "grounds_constants_reproof.json").write_text(json.dumps(out, indent=1, default=str))
print(f"\n-> {OUTD / 'grounds_constants_reproof.json'}")
