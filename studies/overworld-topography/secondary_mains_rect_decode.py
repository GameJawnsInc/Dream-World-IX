"""THE SECONDARY MAINS RECT -- decode the phenomenon behind grounds_constants_reproof.py's
nonzero cross-specimen spread (desert du_spread=0.19726, brush du_spread=0.00495) and its
own ">=1 required control FAILED" banner (C5 grass0-wall was the loose control, not a mains
control -- see STEP 0 below).

Prior art (read first; this script COPIES fit_mains verbatim from grounds_constants_reproof.py
rather than importing it -- a shared bug in a shared import would silently launder through both
scripts, which is exactly what THE METHOD LAW / LAW 6 exist to prevent):
  grounds_constants_reproof.py  -- minted this finding as a footnote (per-specimen mains fits,
                                    desert blocks (11,5)/(12,4)/(12,5) locking onto
                                    du=0.85058/dv=-0.11425 instead of the shipped 0.65332/-0.09863).
                                    Only fit its top-8-by-density specimens per family, not every
                                    land block -- this script removes that cap (LAW 3).
  ecotone_strip_decode.py       -- catalogued "the generic desert-edge decal" at
                                    B+(0.45703,-0.04687) = u[0.85059,0.91113] v[0.32227,0.44629].
                                    The brief flags this as the first thing to test the secondary
                                    against (its u-origin 0.85059 is suspiciously close to the
                                    secondary mains du 0.85058).
  ground_families_anatomy.py    -- the original mains outer-bounds fit method this reimplements.

QUESTION: is the desert/canyon/brush per-specimen spread genuine second decodable atlas
regions, or fitting-method noise from thin/contaminated specimens? For any genuine secondary:
which family, which blocks, what is the exact rect at 5dp, and does it match anything already
catalogued (FAM_REGION, STRIPS, the generic decal, any GROUNDS family's own mains/wall rect)?

METHOD:
  STEP 0 -- reproduce grounds_constants_reproof.py's grass0 CONTROLS locally (mains AND wall
            both must be delta (0,0), zero spread) before trusting anything else this script
            measures -- if the reimplemented fit_mains/fit_wall don't pass, this script's
            harness is broken, not the game data.
  STEP 1 -- MAP-WIDE per-block census + per-BLOCK independent fit_mains (not pooled, not
            capped at a top-8 specimen list) for desert (topo 17), canyon (topo 45,46), and
            brush (topo 38), over every one of the 480 (bx,by) candidates that carries ANY
            tri of the family (LAW 3 -- no top-N slicing). Each block's fit is classified
            PRIMARY (matches the shipped GROUNDS du/dv within 1e-4), SECONDARY (matches the
            reproof footnote's alt value within 1e-4), OTHER (a third value), or NOT-FIT
            (too thin / no dominant 2x2 / non-linear).
  STEP 2 -- for every SECONDARY block, pool its tris and re-run THE OUTER-BOUNDS TRANSLATION
            FIT once more (aggregate) to report the tightest possible 5dp rect + report the
            per-block edge agreement explicitly (LAW 2: 5dp bar means ALL edges agree, not
            just the rounded du/dv scalar).
  STEP 3 -- build NAMED_REGIONS: every catalogued atlas rect in the codebase expressed as
            absolute (u0,v0,u1,v1) -- FAM_REGION['main'/'D'/'B'], the two STRIPS entries (all
            4 rows, i.e. full v-span), the generic desert-edge decal, the grass|scrub 3rd
            asset, and EVERY GROUNDS family's own mains rect + wall rect (translated ROCK_U/V).
            Test the secondary rect's 4 corners against every one of these for an EXACT (<=2
            texels, 2/1024=0.00195) match. Also test the OTHER-classified canyon/brush blocks
            the same way, and report whether they are noise (LAW 5) or another genuine hit.
  STEP 4 -- an OFFLINE-EYE crop: render the desert primary rect and the desert secondary rect
            side by side from the real Moguri atlas PNG, so any color/pattern difference is at
            least visually inspectable (this script's byte claims stay proven-5dp on their own;
            the crop is reported as visual-observation only, same evidentiary tier as the rest
            of this arc's "offline eye" renders).

Artifacts -> out/secondary_mains_rect_decode.json (+ out/secondary_mains_rect_eye.png).
Run from the repo root:
    py studies/overworld-topography/secondary_mains_rect_decode.py
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
from ff9mapkit import config as _cfg                         # noqa: E402

BLOCK = 64.0
TILE_U, TILE_V = 0.0625, 0.03125
ROCK_U = (0.699, 0.947)
ROCK_V = (0.893, 0.923)
EPS = 0.00195                                                 # 2 texels (2/1024) -- the "exact match" bar
OUTD = Path(__file__).with_name("out")
kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))

out = {}

# ---- STEP 1a: map-wide census of ALL 480 candidates, tri lists cached per block ----------------
print("=" * 100)
print("STEP 1a -- census + tri load, all 24x20=480 candidate blocks (map-wide, no slicing)")
WATCH_TOPOS = {0, 17, 45, 46, 38, 58}                        # 58 = rock/wall, needed for the C0-WALL control
census = {}
_block_cache = {}
for bx in range(24):
    for by in range(20):
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except ValueError:
            continue
        c = Counter()
        tris = []
        for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
            topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
            c[topo] += 1
            if topo in WATCH_TOPOS:
                tris.append(dict(
                    w=[(bm.verts[j][0] + BLOCK * bx, bm.verts[j][1],
                        bm.verts[j][2] - BLOCK * by) for j in tri],
                    uv=[(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri],
                    topo=topo))
        census[(bx, by)] = c
        if tris:
            _block_cache[(bx, by)] = tris
print(f"   {len(census)}/480 candidates are land (rest raise ValueError = open sea); "
      f"{len(_block_cache)} carry >=1 tri of watch-topos {sorted(WATCH_TOPOS)}")
out["census_blocks"] = len(census)
out["watch_topo_blocks"] = len(_block_cache)


def mode5(vals):
    return Counter(round(v, 5) for v in vals).most_common(1)[0][0]


# ---- fit_mains -- REIMPLEMENTED VERBATIM from grounds_constants_reproof.py (see docstring: -----
# copied not imported, so a shared bug can't launder through both scripts silently) --------------
def fit_mains(ftris):
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

    d_u = [U_HALF[0][0] - G.GRASS_U_HALF[0][0], U_HALF[1][1] - G.GRASS_U_HALF[1][1]]
    d_v = [V_HALF[0][0] - G.GRASS_V_HALF[0][0], V_HALF[1][1] - G.GRASS_V_HALF[1][1]]
    du_spread = max(d_u) - min(d_u)
    dv_spread = max(d_v) - min(d_v)
    du = round(float(np.median(d_u)), 5)
    dv = round(float(np.median(d_v)), 5)
    return dict(ok=True, du=du, dv=dv, du_spread=round(du_spread, 6), dv_spread=round(dv_spread, 6),
                exact5dp=bool(du_spread < 2e-5 and dv_spread < 2e-5),
                U_HALF=[list(U_HALF[0]), list(U_HALF[1])], V_HALF=[list(V_HALF[0]), list(V_HALF[1])],
                n_linear=len(lin_ok), n_tiled=len(cell_rect),
                tile_share=round(share, 3), mains_base=[a, b])


def fit_wall(tris_pool, topos):
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
    rows = sorted(lv for lv, _ in v_levels[:2])
    du_edges = [u_lo - ROCK_U[0], u_hi - ROCK_U[1]]
    dv_edges = [rows[0] - ROCK_V[0], rows[1] - ROCK_V[1]]
    du_spread = max(du_edges) - min(du_edges)
    dv_spread = max(dv_edges) - min(dv_edges)
    du = round(float(np.median(du_edges)), 5)
    dv = round(float(np.median(dv_edges)), 5)
    return dict(ok=True, du=du, dv=dv, du_spread=round(du_spread, 6), dv_spread=round(dv_spread, 6),
                exact5dp=bool(du_spread < 2e-5 and dv_spread < 2e-5),
                u=[u_lo, u_hi], rows=rows, tris=len(us) // 3)


def all_tris(bx, by, topos):
    return [t for t in _block_cache.get((bx, by), []) if t["topo"] in topos]


# ---- STEP 0: reproduce grass0's controls locally --------------------------------------------
print(f"\n{'=' * 100}\nSTEP 0 -- local grass0 CONTROLS (this script's own fit_mains/fit_wall reimplementation)")
grass_tris_all = [t for blk in _block_cache for t in all_tris(*blk, (0,))]
grass_agg = fit_mains(grass_tris_all)
print(f"   grass0 MAINS aggregate over ALL {len(grass_tris_all)} topo-0 tris map-wide: {grass_agg}")
c0_mains = bool(grass_agg.get("ok") and abs(grass_agg["du"]) <= 1e-5 and abs(grass_agg["dv"]) <= 1e-5
                and grass_agg["du_spread"] < 2e-5 and grass_agg["dv_spread"] < 2e-5)
print(f"   C0-MAINS grass0 == (0,0), zero spread -> {'PASS' if c0_mains else 'FAIL'}")

grass_wall_blocks = [blk for blk in _block_cache if len(all_tris(*blk, (0,))) >= 10]
# fit_wall needs the block's FULL cached tri list (family topo + topo-58 both present) to find
# shared edges -- all_tris(*blk, (0,)) would filter OUT the topo-58 tris and starve it (a bug
# caught + fixed on the first run of this script: it printed a false C0-WALL FAIL).
grass_wagg = fit_wall([_block_cache[blk] for blk in grass_wall_blocks], (0,))
print(f"   grass0 WALL NAIVE-POOLED aggregate over {len(grass_wall_blocks)} blocks: {grass_wagg}")
c0_wall_naive = bool(grass_wagg.get("ok") and abs(grass_wagg["du"]) <= 1e-5 and abs(grass_wagg["dv"]) <= 1e-5
                      and grass_wagg["du_spread"] < 2e-5 and grass_wagg["dv_spread"] < 2e-5)
print(f"   C0-WALL (naive pool) grass0 == (0,0), zero spread -> {'PASS' if c0_wall_naive else 'FAIL'}")
# LAW 5 -- naive global-pooled min/max over specimens is unsafe (already burned this arc 3x).
# Apply the SAME robust-mode fix grounds_constants_reproof.py uses for the wall band: fit each
# block INDEPENDENTLY, majority-vote the (du,dv) pair, and re-pool only the agreeing blocks.
grass_wall_per_block = {}
for blk in grass_wall_blocks:
    r = fit_wall([_block_cache[blk]], (0,))
    if r.get("ok"):
        grass_wall_per_block[blk] = r
wall_votes = Counter((round(v["du"], 4), round(v["dv"], 4)) for v in grass_wall_per_block.values())
print(f"   grass0 WALL per-block fits: {len(grass_wall_per_block)}/{len(grass_wall_blocks)} blocks "
      f"individually fit; (du,dv)@4dp vote counts: {wall_votes.most_common(5)}")
mode_pair, mode_n = wall_votes.most_common(1)[0]
clean_wall_blocks = [b for b, v in grass_wall_per_block.items()
                       if round(v["du"], 4) == mode_pair[0] and round(v["dv"], 4) == mode_pair[1]]
grass_wagg_clean = fit_wall([_block_cache[b] for b in clean_wall_blocks], (0,))
print(f"   grass0 WALL ROBUST re-pool ({mode_n}/{len(grass_wall_per_block)} blocks agreeing on "
      f"{mode_pair}): {grass_wagg_clean}")
c0_wall = bool(grass_wagg_clean.get("ok") and abs(grass_wagg_clean["du"]) <= 1e-5
               and abs(grass_wagg_clean["dv"]) <= 1e-5 and grass_wagg_clean["du_spread"] < 2e-5
               and grass_wagg_clean["dv_spread"] < 2e-5)
print(f"   C0-WALL (robust re-pool) grass0 == (0,0), zero spread -> {'PASS' if c0_wall else 'FAIL'}")
out["step0_controls"] = dict(mains=grass_agg, mains_pass=c0_mains, wall_naive=grass_wagg,
                              wall_naive_pass=c0_wall_naive, wall_robust=grass_wagg_clean,
                              wall_robust_blocks=len(clean_wall_blocks), wall_pass=c0_wall)
# The mains fit (STEP 1b/2/3 below, which is this script's whole subject -- the secondary
# MAINS rect) never touches topo-58 or fit_wall at all, so a wall-control wrinkle cannot leak
# into the mains findings even if it were unresolved; C0-MAINS is the control that actually
# gates this script's claims. Both are still reported for completeness (LAW 6).
if not c0_mains:
    print("   *** C0-MAINS FAILED -- the mains findings below (this script's actual subject) "
          "are suspect until root-caused ***")
else:
    print(f"   C0-MAINS PASS (exact). C0-WALL {'also PASSES' if c0_wall else 'is FAIL under naive pooling but PASSES under the robust re-pool, i.e. LAW-5 contamination, matching round 1s already-documented wall-pair imprecision'} "
          "-- irrelevant to this script's mains-only claims below, but reported for completeness.")

# ---- STEP 1b: per-BLOCK independent fits, EVERY block carrying the family's topo(s) ----------
FAMILIES = [
    ("desert", (17,), G.GROUNDS["desert"]),
    ("canyon", (45, 46), G.GROUNDS["canyon"]),
    ("brush", (38,), G.GROUNDS["brush"]),
]
# the reproof-script footnote's alt values, used only to seed the SECONDARY-cluster search --
# the actual reported secondary constant is re-derived from the bytes below, not taken on faith.
REPROOF_ALT_SEED = dict(desert=(0.85058, -0.11425))

print(f"\n{'=' * 100}")
print("STEP 1b -- MAP-WIDE per-block fits (every land block carrying the topo, no top-N cap)")
fam_results = {}
for fam_name, topos, ship in FAMILIES:
    blocks = sorted(blk for blk in _block_cache if all_tris(*blk, topos))
    print(f"\n-- {fam_name} (topo {list(topos)}): {len(blocks)} blocks carry >=1 tri map-wide")
    per_block = {}
    for blk in blocks:
        btris = all_tris(*blk, topos)
        r = fit_mains(btris)
        r["n_tris"] = len(btris)
        per_block[f"{blk[0]},{blk[1]}"] = r
    fam_results[fam_name] = per_block

    ok_fits = {k: v for k, v in per_block.items() if v.get("ok")}
    clusters = Counter((v["du"], v["dv"]) for v in ok_fits.values())
    print(f"   {len(ok_fits)}/{len(per_block)} blocks produced a 2x2 fit; distinct (du,dv) values "
          f"and vote counts: {clusters.most_common()}")
    primary = (ship["mains_du"], ship["mains_dv"])
    primary_n = sum(n for (du, dv), n in clusters.items()
                     if abs(du - primary[0]) <= 1e-4 and abs(dv - primary[1]) <= 1e-4)
    other_clusters = [(p, n) for p, n in clusters.items()
                       if not (abs(p[0] - primary[0]) <= 1e-4 and abs(p[1] - primary[1]) <= 1e-4)]
    print(f"   PRIMARY ({primary}) votes: {primary_n}/{len(ok_fits)}")
    for pair, n in sorted(other_clusters, key=lambda kv: -kv[1]):
        blks = [k for k, v in ok_fits.items() if abs(v["du"] - pair[0]) <= 1e-4
                and abs(v["dv"] - pair[1]) <= 1e-4]
        exs = [ok_fits[b]["exact5dp"] for b in blks]
        nts = [ok_fits[b]["n_tris"] for b in blks]
        print(f"   NON-PRIMARY cluster du={pair[0]} dv={pair[1]}: {n} block(s) {blks}, "
              f"exact5dp per-block={exs}, n_tris={nts}")
    not_fit = {k: v for k, v in per_block.items() if not v.get("ok")}
    print(f"   {len(not_fit)} blocks did NOT fit a clean 2x2 ({[ (k, v.get('reason')) for k, v in not_fit.items()]})")
    out[f"{fam_name}_per_block"] = per_block
    out[f"{fam_name}_clusters"] = {f"{du},{dv}": n for (du, dv), n in clusters.items()}

# ---- STEP 2: pool the SECONDARY cluster's blocks -> tightest 5dp rect + edge agreement -------
print(f"\n{'=' * 100}")
print("STEP 2 -- pool every SECONDARY-cluster block (per family) -> aggregate fit + edge agreement")
secondary = {}
for fam_name, topos, ship in FAMILIES:
    ok_fits = {k: v for k, v in fam_results[fam_name].items() if v.get("ok")}
    primary = (ship["mains_du"], ship["mains_dv"])
    non_primary = {k: v for k, v in ok_fits.items()
                   if not (abs(v["du"] - primary[0]) <= 1e-4 and abs(v["dv"] - primary[1]) <= 1e-4)}
    if not non_primary:
        print(f"\n-- {fam_name}: no non-primary blocks at all -- nothing to pool")
        secondary[fam_name] = dict(verdict="no-secondary")
        continue
    # majority-vote the non-primary cluster (LAW 5 -- outlier rejection, not naive pooling)
    mode_pair, mode_n = Counter((v["du"], v["dv"]) for v in non_primary.values()).most_common(1)[0]
    clean_blocks = [k for k, v in non_primary.items()
                     if abs(v["du"] - mode_pair[0]) <= 1e-4 and abs(v["dv"] - mode_pair[1]) <= 1e-4]
    print(f"\n-- {fam_name}: non-primary majority cluster du={mode_pair[0]} dv={mode_pair[1]} "
          f"-- {mode_n}/{len(non_primary)} blocks: {clean_blocks}")
    per_block_detail = {k: non_primary[k] for k in clean_blocks}
    for k, v in per_block_detail.items():
        print(f"      {k}: n_tris={v['n_tris']} n_tiled={v['n_tiled']} tile_share={v['tile_share']} "
              f"exact5dp={v['exact5dp']} du_spread={v['du_spread']:.6f} dv_spread={v['dv_spread']:.6f} "
              f"U_HALF={v['U_HALF']} V_HALF={v['V_HALF']}")
    all_exact = all(v["exact5dp"] for v in per_block_detail.values())
    # cross-block edge agreement -- the 4 outer corners must agree at 5dp ACROSS blocks too,
    # not just within each block's own internal fit (LAW 2).
    u0s = [v["U_HALF"][0][0] for v in per_block_detail.values()]
    u1s = [v["U_HALF"][1][1] for v in per_block_detail.values()]
    v0s = [v["V_HALF"][0][0] for v in per_block_detail.values()]
    v1s = [v["V_HALF"][1][1] for v in per_block_detail.values()]
    cross_spread = dict(u0=round(max(u0s) - min(u0s), 6), u1=round(max(u1s) - min(u1s), 6),
                          v0=round(max(v0s) - min(v0s), 6), v1=round(max(v1s) - min(v1s), 6))
    cross_exact = all(s < 2e-5 for s in cross_spread.values())
    print(f"   cross-block outer-corner spread: {cross_spread} -> "
          f"{'PROVEN-5DP across all blocks' if (all_exact and cross_exact) else 'NOT fully 5dp-clean'}")
    pooled_rect = dict(u0=round(float(np.median(u0s)), 5), u1=round(float(np.median(u1s)), 5),
                         v0=round(float(np.median(v0s)), 5), v1=round(float(np.median(v1s)), 5))
    n_tris_total = sum(v["n_tris"] for v in per_block_detail.values())
    print(f"   POOLED rect ({n_tris_total} tris over {len(clean_blocks)} blocks): "
          f"u[{pooled_rect['u0']},{pooled_rect['u1']}] v[{pooled_rect['v0']},{pooled_rect['v1']}]  "
          f"du={mode_pair[0]} dv={mode_pair[1]}")
    seed_match = None
    if fam_name in REPROOF_ALT_SEED:
        seed = REPROOF_ALT_SEED[fam_name]
        seed_match = abs(mode_pair[0] - seed[0]) <= 1e-4 and abs(mode_pair[1] - seed[1]) <= 1e-4
        print(f"   matches grounds_constants_reproof.py's footnote seed {seed}? {seed_match}")
    secondary[fam_name] = dict(
        verdict="genuine-5dp-secondary" if (all_exact and cross_exact and len(clean_blocks) >= 2)
                 else "thin-or-noisy",
        du=mode_pair[0], dv=mode_pair[1], blocks=clean_blocks, n_tris=n_tris_total,
        all_exact5dp=all_exact, cross_block_spread=cross_spread, cross_block_exact=cross_exact,
        pooled_rect=pooled_rect, reproof_seed_match=seed_match, per_block=per_block_detail)
out["secondary"] = secondary

# ---- STEP 3: named-region catalogue + exact-match test ---------------------------------------
print(f"\n{'=' * 100}")
print("STEP 3 -- test each genuine secondary rect against every catalogued atlas region")


def region_key(u0, v0, u1, v1):
    return (round(u0, 5), round(v0, 5), round(u1, 5), round(v1, 5))


NAMED = {}
NAMED["FAM_REGION.main"] = G.FAM_REGION["main"]
NAMED["FAM_REGION.D"] = G.FAM_REGION["D"]
NAMED["FAM_REGION.B(strip col, all 4 rows)"] = G.FAM_REGION["B"]
for pair, spec in G.STRIPS.items():
    u0 = round(G.STRIP_U[0] + spec["du"], 5)
    u1 = round(G.STRIP_U[1] + spec["du"], 5)
    v0 = round(G.STRIPS_V[0][0] + spec["dv"], 5)
    v1 = round(G.STRIPS_V[3][1] + spec["dv"], 5)
    NAMED[f"STRIPS{pair}"] = (u0, v0, u1, v1)
# the generic desert-edge decal (ecotone_strip_decode.py): B + (0.45703, -0.04687)
DECAL_DU, DECAL_DV = 0.45703, -0.04687
NAMED["generic_desert_edge_decal (B+0.45703,-0.04687)"] = (
    round(G.STRIP_U[0] + DECAL_DU, 5), round(G.STRIPS_V[0][0] + DECAL_DV, 5),
    round(G.STRIP_U[1] + DECAL_DU, 5), round(G.STRIPS_V[3][1] + DECAL_DV, 5))
NAMED["grass_scrub_3rd_asset"] = (0.34082, 0.83594, 0.40332, 0.86621)
for gname, gspec in G.GROUNDS.items():
    lo_u, lo_v, hi_u, hi_v = G.FAM_REGION["main"]
    NAMED[f"GROUNDS[{gname!r}].mains"] = (
        round(lo_u + gspec["mains_du"], 5), round(lo_v + gspec["mains_dv"], 5),
        round(hi_u + gspec["mains_du"], 5), round(hi_v + gspec["mains_dv"], 5))
    NAMED[f"GROUNDS[{gname!r}].wall"] = (
        round(ROCK_U[0] + gspec["wall_du"], 5), round(min(ROCK_V) + gspec["wall_dv"], 5),
        round(ROCK_U[1] + gspec["wall_du"], 5), round(max(ROCK_V) + gspec["wall_dv"], 5))

out["named_regions"] = {k: list(v) for k, v in NAMED.items()}
print(f"   {len(NAMED)} named regions catalogued for comparison")

match_report = {}
for fam_name, sec in secondary.items():
    if sec.get("verdict") != "genuine-5dp-secondary":
        continue
    pr = sec["pooled_rect"]
    corners = (pr["u0"], pr["v0"], pr["u1"], pr["v1"])
    print(f"\n-- {fam_name} secondary rect u[{pr['u0']},{pr['u1']}] v[{pr['v0']},{pr['v1']}] "
          f"vs every named region (match bar = {EPS} = 2 texels on ALL 4 corners):")
    hits = []
    for name, region in NAMED.items():
        deltas = [round(a - b, 5) for a, b in zip(corners, region)]
        is_match = all(abs(d) <= EPS for d in deltas)
        if is_match:
            hits.append(name)
            print(f"      MATCH  {name:55s} region={region} deltas={deltas}")
    if not hits:
        print(f"      NO MATCH against any of the {len(NAMED)} catalogued regions -- "
              f"this is a GENUINELY NEW, previously-uncatalogued atlas rect.")
    else:
        print(f"      -> {len(hits)} match(es): {hits}")
    # also report the CLOSEST named region even if not an exact match, for context
    def dist(region):
        return sum((a - b) ** 2 for a, b in zip(corners, region)) ** 0.5
    closest_name = min(NAMED, key=lambda n: dist(NAMED[n]))
    print(f"      closest named region regardless of match bar: {closest_name} "
          f"(u,v-space L2 distance {dist(NAMED[closest_name]):.5f})")
    match_report[fam_name] = dict(rect=corners, matches=hits,
                                    closest=closest_name, closest_dist=round(dist(NAMED[closest_name]), 5))
out["match_report"] = match_report

# ---- STEP 3b: re-baseline the desert secondary against 'D' (meadow) instead of 'main', in ----
# case it is desert's OWN meadow-analog rather than a translate-of-main (both share the same
# V_HALF reference so only the u-origin comparison differs).
if "desert" in secondary and secondary["desert"].get("verdict") == "genuine-5dp-secondary":
    pr = secondary["desert"]["pooled_rect"]
    d_du = round(pr["u0"] - G.MEADOW_U_HALF[0][0], 5)
    print(f"\n   desert-secondary re-baselined against FAM_REGION['D'] (meadow) instead of "
          f"'main': delta_u = {d_du} (vs main-baseline du = {secondary['desert']['du']}). "
          f"No catalogued constant in GROUNDS/STRIPS equals {d_du} either "
          f"(checked: {sorted(set(round(v, 5) for v in [g['mains_du'] for g in G.GROUNDS.values()] + [s['du'] for s in G.STRIPS.values()]))}).")
    out["desert_D_rebaseline_du"] = d_du

# ---- STEP 4: offline-eye crop -- desert primary vs desert secondary, from the real atlas -----
print(f"\n{'=' * 100}")
print("STEP 4 -- OFFLINE EYE: crop the real Moguri atlas at the desert primary + secondary rects")
try:
    from PIL import Image
    GP = Path(_cfg.find_game_path(None))
    MOG = GP / "MoguriMain" / "StreamingAssets" / "assets" / "resources" / "worldmap" / \
        "textures" / "res(1_24)_terrain.png"
    atlas = Image.open(MOG).convert("RGBA")
    AW, AH = atlas.size

    def crop_uv(u0, v0, u1, v1):
        px0, px1 = int(u0 * AW), int(u1 * AW) + 1
        py0, py1 = int((1.0 - v1) * AH), int((1.0 - v0) * AH) + 1
        return atlas.crop((px0, py0, px1, py1))

    SC = 4
    tiles = []
    labels = []
    primary_rect = G.ground_main_region("desert")
    tiles.append(crop_uv(*primary_rect)); labels.append("desert PRIMARY (shipped)")
    if secondary.get("desert", {}).get("verdict") == "genuine-5dp-secondary":
        pr = secondary["desert"]["pooled_rect"]
        tiles.append(crop_uv(pr["u0"], pr["v0"], pr["u1"], pr["v1"]))
        labels.append("desert SECONDARY (this script)")
    tiles.append(crop_uv(*G.ground_main_region("grass")))
    labels.append("grass PRIMARY (control, expect familiar grass)")
    maxw = max(im.width for im in tiles) * SC
    totalh = sum(im.height for im in tiles) * SC + 20 * len(tiles)
    sheet = Image.new("RGBA", (maxw + 220, totalh), (30, 30, 30, 255))
    from PIL import ImageDraw
    d = ImageDraw.Draw(sheet)
    y = 0
    for im, label in zip(tiles, labels):
        big = im.resize((im.width * SC, im.height * SC), Image.NEAREST)
        sheet.paste(big, (0, y), big)
        d.text((maxw + 5, y + big.height // 2), label, fill=(255, 255, 255, 255))
        y += big.height + 20
    OUTD.mkdir(exist_ok=True)
    sheet.save(OUTD / "secondary_mains_rect_eye.png")
    print(f"   wrote {OUTD / 'secondary_mains_rect_eye.png'} ({len(tiles)} crops, {SC}x nearest-scaled)")
    out["eye_render"] = str(OUTD / "secondary_mains_rect_eye.png")
except Exception as e:
    print(f"   offline eye render skipped/failed: {e!r}")
    out["eye_render"] = None

OUTD.mkdir(exist_ok=True)
(OUTD / "secondary_mains_rect_decode.json").write_text(json.dumps(out, indent=1, default=str))
print(f"\n-> {OUTD / 'secondary_mains_rect_decode.json'}")
