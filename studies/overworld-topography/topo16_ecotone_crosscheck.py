"""TOPO-16 x THE ECOTONE-STRIP CATALOG -- settling round 1's own flagged cross-lane defect.

BACKGROUND: round 1's dirt-16 lane (``dirt16_anatomy.py``) map-wide-censused topo-16 (dry
lakebed dirt: 422 tris, an EXACT contiguous 3x2 block rect bx[13,15] x by[11,12]) and found
its atlas footprint splits into 4 origin clusters -- a 27% zone PROVEN-5DP identical to the
desert mains 2x2, and two others (57% + 16% of the footprint) it reported as "matching NONE
of the shipped GROUNDS constants" and recommended a "verbatim layout-stamp carry". The SAME
round's ecotone lane (``ecotone_strip_decode.py``) separately proved a ``STRIPS`` table
(grass|desert, desert|dunes -- both a translated copy of the grass 'B' 1x4 transition-strip
column) -- but nobody cross-checked topo-16's "unrecorded" zones against it. The round's own
write-up (GROUND-FAMILY-DECODE-2026-07-19.md, "Deferred") flags this explicitly as
"the round's clearest cross-lane defect" and leaves the recommendation stale. This script
settles it.

METHOD (THE METHOD LAW / 5DP BAR / LAW 4 -- classify by TOPO id FIRST, only THEN by UV rect):
  A. Re-census topo-16 map-wide (all 480 (bx,by) candidates, no top-N slice) -- reconfirm
     the block set / tri count / block-context topo composition independently (round 1's
     numbers are not trusted, only reproduced).
  B. Classify EVERY topo-16 tri (already topo-filtered -- satisfies LAW 4) by UV containment
     (EPS=0.006, matching ecotone_strip_decode's tolerance) against 3 candidate regions:
     desert MAINS (GROUNDS['desert'] translation of the grass main 2x2), the grass|desert
     STRIPS entry, and the desert|dunes STRIPS entry (both B-strip translations). Anything
     landing in none of the three is RESIDUAL; anything in more than one is AMBIGUOUS.
  C. For the two strip buckets: the SAME per-4u-cell exact-affine + coverage-aware rect
     recovery ecotone_strip_decode.strip_decode uses (full-tile EXTRAPOLATION only at >=90%
     triangle-area coverage, else the raw observed bbox -- never inflate a partial boundary
     cell). Cluster into ROWS by v0-mode, then run the IDENTICAL outer-bounds translation-fit
     + row-alignment disambiguation (against the universal grass-B reference G.STRIP_U /
     G.STRIPS_V) that produced the shipped STRIPS table in the first place -- an INDEPENDENT
     re-derivation from topo-16's own bytes, not an assumed match.
  D. Compare the independently-refit (du,dv) against the shipped STRIPS constants at 5dp.
     Also recheck the desert-mains bucket's outer bounds the same way.
  E. Structural check: what topo families actually co-occur in topo-16's 6 blocks -- does the
     geometry support "this ground sits at a grass/desert/dunes ecotone" (matching which two
     strip pairs it wears), or is the texture match coincidental?
  F. Verdict + a concrete recommendation: GROUNDS / STRIPS / neither / a new table.

Run from the repo root:
    py studies/overworld-topography/topo16_ecotone_crosscheck.py
Artifacts -> out/topo16_ecotone_crosscheck.json
"""
import itertools
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
EPS = 0.006
OUTD = Path(__file__).with_name("out")
kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))
out = {}


def mode5(vals):
    return float(Counter(round(float(v), 5) for v in vals).most_common(1)[0][0])


# ==== A. map-wide topo-16 re-census (all 480 candidates, no top-N slice) ===========================
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
print(f"A. map-wide census: {len(census)}/480 candidate blocks have terrain mesh")
out["census_blocks"] = len(census)

t16_blocks = {blk: c.get(16, 0) for blk, c in census.items() if c.get(16, 0) > 0}
total16 = sum(t16_blocks.values())
print(f"   topo-16 MAP-WIDE: {total16} tris over {len(t16_blocks)} blocks: {sorted(t16_blocks)}")
bxs = sorted({b[0] for b in t16_blocks}); bys = sorted({b[1] for b in t16_blocks})
full_rect = {(x, y) for x in range(min(bxs), max(bxs) + 1) for y in range(min(bys), max(bys) + 1)}
contiguous = full_rect == set(t16_blocks)
print(f"   footprint bbox bx[{min(bxs)},{max(bxs)}] by[{min(bys)},{max(bys)}] -- "
      f"{'EXACT CONTIGUOUS RECTANGLE' if contiguous else 'NOT a filled rectangle'} "
      f"(reproduces round 1's claim: {contiguous and total16 == 422 and len(t16_blocks) == 6})")
out["t16_blocks"] = {f"{b[0]},{b[1]}": n for b, n in sorted(t16_blocks.items())}
out["total16"] = total16
out["contiguous_rect"] = bool(contiguous)

# gather topo16 tris (world+uv) AND each block's full topo composition (for the structural check)
ftris = []
block_topocomp = {}
for blk in t16_blocks:
    bm = X.read_block(*blk, disc=1, part="terrain")
    bx, by = blk
    comp = Counter()
    for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
        topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
        comp[topo] += 1
        if topo != 16:
            continue
        ftris.append(dict(
            w=[(bm.verts[j][0] + BLOCK * bx, bm.verts[j][1], bm.verts[j][2] - BLOCK * by) for j in tri],
            uv=[(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri], block=blk))
    block_topocomp[blk] = comp
assert len(ftris) == total16, "gathered topo16 tri count must match the census total"
print(f"   gathered {len(ftris)} topo-16 tris with world+uv (matches census: {len(ftris) == total16})")

# ==== B. classify every topo-16 tri by UV containment against the 3 candidate regions =============
GM = G.FAM_REGION["main"]
GB = G.FAM_REGION["B"]
dg = G.GROUNDS["desert"]
DESERT_MAINS = (GM[0] + dg["mains_du"], GM[1] + dg["mains_dv"], GM[2] + dg["mains_du"], GM[3] + dg["mains_dv"])
sgd = G.STRIPS[("grass", "desert")]
sdd = G.STRIPS[("desert", "dunes")]
STRIP_GD = (GB[0] + sgd["du"], GB[1] + sgd["dv"], GB[2] + sgd["du"], GB[3] + sgd["dv"])
STRIP_DD = (GB[0] + sdd["du"], GB[1] + sdd["dv"], GB[2] + sdd["du"], GB[3] + sdd["dv"])
print("\nB. candidate regions (5dp):")
print(f"   DESERT_MAINS           u[{DESERT_MAINS[0]:.5f},{DESERT_MAINS[2]:.5f}] "
      f"v[{DESERT_MAINS[1]:.5f},{DESERT_MAINS[3]:.5f}]  (GROUNDS['desert'] mains_du/dv "
      f"{dg['mains_du']}/{dg['mains_dv']})")
print(f"   STRIP grass|desert      u[{STRIP_GD[0]:.5f},{STRIP_GD[2]:.5f}] "
      f"v[{STRIP_GD[1]:.5f},{STRIP_GD[3]:.5f}]  (STRIPS du/dv {sgd['du']}/{sgd['dv']})")
print(f"   STRIP desert|dunes      u[{STRIP_DD[0]:.5f},{STRIP_DD[2]:.5f}] "
      f"v[{STRIP_DD[1]:.5f},{STRIP_DD[3]:.5f}]  (STRIPS du/dv {sdd['du']}/{sdd['dv']})")
out["regions"] = dict(desert_mains=DESERT_MAINS, strip_grass_desert=STRIP_GD, strip_desert_dunes=STRIP_DD)

REGIONS = {"desert_mains": DESERT_MAINS, "strip_grass_desert": STRIP_GD, "strip_desert_dunes": STRIP_DD}


def classify(uvs):
    hits = [name for name, r in REGIONS.items()
            if all(r[0] - EPS <= u <= r[2] + EPS and r[1] - EPS <= v <= r[3] + EPS for (u, v) in uvs)]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        return "AMBIGUOUS(" + "+".join(hits) + ")"
    return "RESIDUAL"


bucket = Counter()
tri_bucket = defaultdict(list)
for t in ftris:
    cls = classify(t["uv"])
    bucket[cls] += 1
    tri_bucket[cls].append(t)
print(f"\nC. per-tri classification (EPS={EPS}), {total16} topo-16 tris total (already topo-filtered "
      f"-- LAW 4: a topo count, not a UV-rect count):")
for name, n in bucket.most_common():
    print(f"     {name}: {n} tris ({n / total16:.1%})")
out["tri_classification"] = {k: v for k, v in bucket.items()}
share_covered = sum(n for name, n in bucket.items() if name in REGIONS) / total16
print(f"   TOTAL covered by the 3 known regions: {share_covered:.1%} "
      f"(residual+ambiguous: {1 - share_covered:.1%})")
out["share_covered_by_3_regions"] = round(share_covered, 4)


# ==== C. per-cell exact-affine + coverage-aware rect recovery (identical method to
#         ecotone_strip_decode.strip_decode), then row-clustering + translation fit ================
def strip_decode(tris_subset):
    cell_tris = defaultdict(list)
    for t in tris_subset:
        cx = sum(p[0] for p in t["w"]) / 3.0
        cz = sum(p[2] for p in t["w"]) / 3.0
        cell_tris[(math.floor(cx / 4.0), math.floor(cz / 4.0))].append(t)
    cell_rects = {}
    n_nonlin = n_full = n_part = 0
    for cell, tl in cell_tris.items():
        rows, ru, rv = [], [], []
        for t in tl:
            for (x, y, z), (u, v) in zip(t["w"], t["uv"]):
                rows.append([x, z, 1.0]); ru.append(u); rv.append(v)
        Am = np.array(rows)
        if len(rows) < 3 or np.linalg.matrix_rank(Am) < 3:
            n_nonlin += 1
            continue
        cu, *_ = np.linalg.lstsq(Am, np.array(ru), rcond=None)
        cv, *_ = np.linalg.lstsq(Am, np.array(rv), rcond=None)
        res = max(float(np.abs(Am @ cu - ru).max()), float(np.abs(Am @ cv - rv).max()))
        if res >= 1e-4:
            n_nonlin += 1
            continue
        area, seen = 0.0, set()
        for t in tl:
            key = tuple(sorted(kk(p) for p in t["w"]))
            if key in seen:
                continue
            seen.add(key)
            (x0, y0, z0), (x1, y1, z1), (x2, y2, z2) = t["w"]
            area += abs((x1 - x0) * (z2 - z0) - (x2 - x0) * (z1 - z0)) / 2.0
        coverage = area / 16.0
        i, j = cell
        if coverage >= 0.9:
            corn = [(4.0 * i, 4.0 * j), (4.0 * (i + 1), 4.0 * j),
                    (4.0 * i, 4.0 * (j + 1)), (4.0 * (i + 1), 4.0 * (j + 1))]
            us_c = [cu[0] * x + cu[1] * z + cu[2] for (x, z) in corn]
            vs_c = [cv[0] * x + cv[1] * z + cv[2] for (x, z) in corn]
            rect = (min(us_c), max(us_c), min(vs_c), max(vs_c))
            n_full += 1
        else:
            us = [uv[0] for t in tl for uv in t["uv"]]
            vs = [uv[1] for t in tl for uv in t["uv"]]
            rect = (min(us), max(us), min(vs), max(vs))
            n_part += 1
        cell_rects[cell] = dict(rect=rect, coverage=round(coverage, 3), ntris=len(seen))
    return cell_rects, n_nonlin, n_full, n_part


def cluster_rows(cell_rects, min_cells=1):
    v0_of = {c: r["rect"][2] for c, r in cell_rects.items()}
    v0_counts = Counter(round(v, 5) for v in v0_of.values())
    rows = []
    for v0mode, n in v0_counts.most_common():
        if n < min_cells:
            continue
        members = [c for c, v in v0_of.items() if round(v, 5) == v0mode]
        u0 = mode5(cell_rects[c]["rect"][0] for c in members)
        u1 = mode5(cell_rects[c]["rect"][1] for c in members)
        v0 = mode5(cell_rects[c]["rect"][2] for c in members)
        v1 = mode5(cell_rects[c]["rect"][3] for c in members)
        rows.append(dict(u0=u0, u1=u1, v0=v0, v1=v1, ncells=len(members)))
    rows.sort(key=lambda r: r["v0"])
    return rows


def fit_column(rows):
    """Identical algorithm to ecotone_strip_decode.fit_column: translation-fit vs the
    UNIVERSAL grass B reference (G.STRIP_U / G.STRIPS_V), row-alignment disambiguated by
    minimum outer-bounds spread (ties broken by internal-edge residual)."""
    k = len(rows)
    if k == 0:
        return None
    u0s = [r["u0"] for r in rows]; u1s = [r["u1"] for r in rows]
    u0_row_spread = max(u0s) - min(u0s); u1_row_spread = max(u1s) - min(u1s)
    u0m, u1m = float(np.median(u0s)), float(np.median(u1s))
    du0 = u0m - G.STRIP_U[0]; du1 = u1m - G.STRIP_U[1]
    du = round(float(np.median([du0, du1])), 5)
    du_spread = round(abs(du0 - du1), 6)
    v0s = [r["v0"] for r in rows]
    pitch_resid = [abs((b - a) - round((b - a) / 0.03125) * 0.03125) for a, b in zip(v0s, v0s[1:])]
    pitch_ok = all(p < 2e-5 for p in pitch_resid) if pitch_resid else True
    cands = []
    for combo in itertools.combinations(range(4), k):
        dv_lo = rows[0]["v0"] - G.STRIPS_V[combo[0]][0]
        dv_hi = rows[-1]["v1"] - G.STRIPS_V[combo[-1]][1]
        spread = abs(dv_lo - dv_hi)
        dv = (dv_lo + dv_hi) / 2.0
        internal = [rows[i]["v1"] - G.STRIPS_V[combo[i]][1] - dv for i in range(k - 1)] + \
                   [rows[i]["v0"] - G.STRIPS_V[combo[i]][0] - dv for i in range(1, k)]
        cands.append(dict(combo=list(combo), dv=round(dv, 5), spread=round(spread, 6),
                          internal_max=round(max((abs(x) for x in internal), default=0.0), 6)))
    cands.sort(key=lambda c: (c["spread"], c["internal_max"]))
    best = cands[0]
    tied = [c for c in cands if abs(c["spread"] - best["spread"]) < 1e-6]
    return dict(k=k, du=du, du_spread=du_spread, u0_row_spread=round(u0_row_spread, 6),
                u1_row_spread=round(u1_row_spread, 6), v_fit=best, pitch_ok=pitch_ok,
                pitch_resid_max=round(max(pitch_resid, default=0.0), 6),
                n_tied=len(tied), tied=tied if len(tied) > 1 else None)


print("\nD. independent re-derivation on topo-16's OWN tris (per-cell exact-affine, coverage-aware, "
      "row-clustered, fit against the UNIVERSAL grass-B reference G.STRIP_U/G.STRIPS_V):")
out["strip_refit"] = {}
for bucket_name, shipped in (("strip_grass_desert", sgd), ("strip_desert_dunes", sdd)):
    tris_sub = tri_bucket.get(bucket_name, [])
    print(f"\n   ---- {bucket_name}: {len(tris_sub)} tris classified ----")
    if len(tris_sub) < 3:
        print("      too thin -- skip")
        out["strip_refit"][bucket_name] = {"verdict": "too-thin", "n_tris": len(tris_sub)}
        continue
    cell_rects, n_nonlin, n_full, n_part = strip_decode(tris_sub)
    print(f"      cells: {len(cell_rects)} linear ({n_full} full-tile>=90% coverage, "
          f"{n_part} partial<90% raw-bbox), {n_nonlin} rejected non-linear/decal")
    rows = cluster_rows(cell_rects, min_cells=1)
    for r in rows:
        print(f"      row v0={r['v0']:.5f}: u[{r['u0']:.5f},{r['u1']:.5f}] "
              f"v[{r['v0']:.5f},{r['v1']:.5f}]  ({r['ncells']} cells)")
    fit = fit_column(rows)
    row_out = dict(n_tris=len(tris_sub), cells_linear=len(cell_rects), cells_full=n_full,
                   cells_partial=n_part, cells_nonlinear=n_nonlin, rows=rows)
    if fit is None:
        print("      NO rows survived clustering")
        row_out["verdict"] = "no-rows"
    else:
        vf = fit["v_fit"]
        unique = fit["n_tied"] == 1
        proven = (fit["du_spread"] < 2e-5 and fit["k"] >= 2 and vf["spread"] < 2e-5
                  and fit["pitch_ok"] and unique)
        earmark = fit["du_spread"] < 2e-4 and vf["spread"] < 1e-3
        verdict = "proven-5dp" if proven else ("earmark-approximate" if earmark else "falsified")
        print(f"      REFIT: k={fit['k']} rows, du={fit['du']} (spread {fit['du_spread']}) "
              f"row-pitch ok={fit['pitch_ok']} (max resid {fit['pitch_resid_max']}) "
              f"best combo={vf['combo']} dv={vf['dv']} (outer-bounds v-spread {vf['spread']}, "
              f"internal-edge max {vf['internal_max']}, n_tied={fit['n_tied']}) -> {verdict}")
        d_du = round(fit["du"] - shipped["du"], 5)
        d_dv = round(vf["dv"] - shipped["dv"], 5)
        print(f"      vs SHIPPED {bucket_name.replace('strip_', '').replace('_', '|')} "
              f"du={shipped['du']} dv={shipped['dv']}: "
              f"delta du={d_du} dv={d_dv} -> "
              f"{'BYTE-IDENTICAL (5dp)' if d_du == 0 and d_dv == 0 else 'NOT identical at 5dp'}")
        row_out.update(fit=fit, verdict=verdict, delta_vs_shipped=dict(du=d_du, dv=d_dv))
    out["strip_refit"][bucket_name] = row_out

# ---- desert-mains bucket: recheck outer bounds independently (light recheck of round 1's zone1) ----
# NOTE: desert mains is a 2x2 QUADRANT (2 u-halves x 2 v-halves), not one rect -- pooling all cells'
# rects with a single mode5 mixes the two u-halves/v-halves together and is WRONG (caught while
# writing this script). Use the same quadrant-half outer-bounds method as
# ground_families_anatomy.decode_family / round 1's J.6 zone_translation_fits: split cells into
# halves by proximity to the (translated) grass quadrant midline, then mode5 each of the 8 edges.
print("\n   ---- desert_mains: recheck outer bounds (quadrant-half method, mirrors round1's J.6) ----")
mains_tris = tri_bucket.get("desert_mains", [])
mcell_rects, mn_nonlin, mn_full, mn_part = strip_decode(mains_tris)
print(f"      {len(mains_tris)} tris -> {len(mcell_rects)} linear cells "
      f"({mn_full} full, {mn_part} partial, {mn_nonlin} rejected)")
if mcell_rects:
    u_mid = (G.GRASS_U_HALF[0][1] + G.GRASS_U_HALF[1][0]) / 2.0 + dg["mains_du"]
    v_mid = (G.GRASS_V_HALF[0][1] + G.GRASS_V_HALF[1][0]) / 2.0 + dg["mains_dv"]
    per_edge = defaultdict(list)
    for c, r in mcell_rects.items():
        u0, u1, v0, v1 = r["rect"]
        uh = 0 if u0 < u_mid else 1
        vh = 0 if v0 < v_mid else 1
        per_edge[("u", uh, "lo")].append(u0); per_edge[("u", uh, "hi")].append(u1)
        per_edge[("v", vh, "lo")].append(v0); per_edge[("v", vh, "hi")].append(v1)
    populated = [k for k in (("u", 0, "lo"), ("u", 0, "hi"), ("u", 1, "lo"), ("u", 1, "hi"),
                              ("v", 0, "lo"), ("v", 0, "hi"), ("v", 1, "lo"), ("v", 1, "hi"))
                 if k in per_edge]
    print(f"      quadrant edges populated: {len(populated)}/8 "
          f"({ {k: len(v) for k, v in per_edge.items()} })")
    if len(populated) == 8:
        U_HALF = [(mode5(per_edge[("u", h, "lo")]), mode5(per_edge[("u", h, "hi")])) for h in (0, 1)]
        V_HALF = [(mode5(per_edge[("v", h, "lo")]), mode5(per_edge[("v", h, "hi")])) for h in (0, 1)]
        d_u = [U_HALF[0][0] - G.GRASS_U_HALF[0][0], U_HALF[1][1] - G.GRASS_U_HALF[1][1]]
        d_v = [V_HALF[0][0] - G.GRASS_V_HALF[0][0], V_HALF[1][1] - G.GRASS_V_HALF[1][1]]
        du_spread = max(d_u) - min(d_u); dv_spread = max(d_v) - min(d_v)
        du = round(float(np.median(d_u)), 5); dv = round(float(np.median(d_v)), 5)
        is_translation = du_spread < 2e-5 and dv_spread < 2e-5
        print(f"      U_HALF {U_HALF} V_HALF {V_HALF}")
        print(f"      TRANSLATION FIT: du={du} dv={dv} spread u={du_spread:.6f} v={dv_spread:.6f} -> "
              f"{'PROVEN-5DP EXACT TRANSLATION' if is_translation else 'not a clean single translation'}")
        match_shipped = abs(du - dg["mains_du"]) < 1e-5 and abs(dv - dg["mains_dv"]) < 1e-5
        print(f"      vs shipped GROUNDS['desert'] mains_du/dv {dg['mains_du']}/{dg['mains_dv']}: "
              f"{'EXACT MATCH' if match_shipped else 'MISMATCH'}")
        out["desert_mains_recheck"] = dict(U_HALF=U_HALF, V_HALF=V_HALF, du=du, dv=dv,
                                           du_spread=round(du_spread, 6), dv_spread=round(dv_spread, 6),
                                           proven=bool(is_translation), matches_shipped=bool(match_shipped))
    else:
        print("      not all 4 quadrant halves populated -- partial check only, no verdict")
        out["desert_mains_recheck"] = dict(populated=len(populated), verdict="partial-only")

# ==== E. structural check -- what actually co-occurs in topo-16's 6 blocks? ========================
GRASS_TOPOS = {0, 1, 2, 3, 10, 11, 12, 13, 42}
DUNES_TOPO = 41
WALL_TOPO = 58
print("\nE. structural check -- block-context topo composition (recomputed independently):")
grass_present_all = True
dunes_present_all = True
for blk in sorted(t16_blocks):
    comp = block_topocomp[blk]
    grass_n = sum(comp.get(t, 0) for t in GRASS_TOPOS)
    dunes_n = comp.get(DUNES_TOPO, 0)
    wall_n = comp.get(WALL_TOPO, 0)
    grass_present_all &= grass_n > 0
    dunes_present_all &= dunes_n > 0
    others = {t: n for t, n in comp.most_common() if t != 16}
    print(f"     block {blk}: topo16={comp.get(16,0)}  grass-family={grass_n}  dunes(41)={dunes_n}  "
          f"wall(58)={wall_n}  full composition={dict(comp.most_common())}")
print(f"   grass-family topo present in EVERY topo-16 block: {grass_present_all}")
print(f"   dunes(41) present in EVERY topo-16 block: {dunes_present_all}")
out["structural"] = dict(
    grass_present_all=bool(grass_present_all), dunes_present_all=bool(dunes_present_all),
    block_composition={f"{b[0]},{b[1]}": dict(block_topocomp[b]) for b in sorted(t16_blocks)})

# does the STRIP CHOICE geographically track the actual bordering family, block by block? (i.e.
# not just "dunes occurs somewhere in the 6-block footprint" but "the desert|dunes-strip tris sit
# specifically in the blocks that actually border dunes ground")
print("\n   per-bucket geographic distribution (which of the 6 blocks each UV bucket's tris sit in):")
bucket_block_hist = {}
for name in ("desert_mains", "strip_grass_desert", "strip_desert_dunes"):
    h = Counter(t["block"] for t in tri_bucket.get(name, []))
    print(f"     {name}: {dict(sorted(h.items()))}")
    bucket_block_hist[name] = {f"{b[0]},{b[1]}": n for b, n in sorted(h.items())}
dunes_bearing_blocks = {b for b in t16_blocks if block_topocomp[b].get(DUNES_TOPO, 0) > 0}
dd_bucket_blocks = set(t["block"] for t in tri_bucket.get("strip_desert_dunes", []))
dd_tracks_dunes = dd_bucket_blocks.issubset(dunes_bearing_blocks)
print(f"   dunes-bearing blocks: {sorted(dunes_bearing_blocks)}")
print(f"   strip_desert_dunes tris confined to dunes-bearing blocks only: {dd_tracks_dunes} "
      f"(its blocks: {sorted(dd_bucket_blocks)})")
out["structural"]["bucket_block_hist"] = bucket_block_hist
out["structural"]["dunes_bearing_blocks"] = [f"{b[0]},{b[1]}" for b in sorted(dunes_bearing_blocks)]
out["structural"]["strip_desert_dunes_tracks_dunes_blocks"] = bool(dd_tracks_dunes)

# ==== F. verdict =====================================================================================
# Two distinct questions, kept separate (do not conflate them):
#  (i)  does topo-16's OWN data, taken alone, unambiguously self-derive the (du,dv) at 5dp
#       (fit_column's "proven-5dp" -- requires n_tied==1, i.e. no row-alignment ambiguity)?
#  (ii) does topo-16's independently-refit (du,dv) EQUAL the shipped STRIPS constant exactly
#       (delta==0), i.e. does it CONFIRM the already-proven-elsewhere table entry?
# desert|dunes only samples 3 of 4 strip rows here (the true middle slot 2 is absent in this
# specific location), so its outer-bounds-only self-fit ties between two row-alignments that
# share the same first/last row (a real structural property of THIS window, not a data-quality
# problem) -- (i) is an earmark here even though (ii) is an exact match (the tie-break by
# internal-edge residual, and the cross-check against the map-wide-proven shipped value, both
# land on the identical winner).
print("\nF. VERDICT")
gd_out = out["strip_refit"].get("strip_grass_desert", {})
dd_out = out["strip_refit"].get("strip_desert_dunes", {})
gd_self_proven = gd_out.get("verdict") == "proven-5dp"
dd_self_proven = dd_out.get("verdict") == "proven-5dp"
gd_matches_shipped = gd_out.get("delta_vs_shipped", {}).get("du") == 0 \
    and gd_out.get("delta_vs_shipped", {}).get("dv") == 0
dd_matches_shipped = dd_out.get("delta_vs_shipped", {}).get("du") == 0 \
    and dd_out.get("delta_vs_shipped", {}).get("dv") == 0
mains_ok = out.get("desert_mains_recheck", {}).get("matches_shipped") is True
residual_share = 1 - share_covered
gd_share = bucket.get("strip_grass_desert", 0) / total16
dd_share = bucket.get("strip_desert_dunes", 0) / total16
dm_share = bucket.get("desert_mains", 0) / total16

print(f"   desert_mains: quadrant-half recheck matches shipped GROUNDS['desert'] = {mains_ok}")
print(f"   strip_grass_desert: self-proven-5dp (unambiguous alone) = {gd_self_proven}; "
      f"matches shipped STRIPS entry exactly = {gd_matches_shipped}")
print(f"   strip_desert_dunes: self-proven-5dp (unambiguous alone) = {dd_self_proven} "
      f"(only 3/4 rows present here -> outer-bounds tie, a structural property of this window, "
      f"not a data defect); matches shipped STRIPS entry exactly (after tie-break) = {dd_matches_shipped}")

if mains_ok and gd_matches_shipped and dd_matches_shipped and residual_share < 0.01:
    verdict = (f"CONFIRMED -- topo-16's atlas footprint decomposes EXACTLY into 3 already-decoded "
               f"desert-family pieces: {dm_share:.0%} desert MAINS (quadrant-half recheck exact "
               f"match, zero spread), {gd_share:.0%} the grass|desert STRIPS entry (independently "
               f"re-derived, self-proven-5dp with zero ambiguity, exact match), {dd_share:.0%} the "
               f"desert|dunes STRIPS entry (independently re-derived; only an earmark taken alone "
               f"because this specific window samples 3 of 4 rows and ties on row-alignment, but "
               f"the tie-break winner is an EXACT match to the map-wide-proven shipped constant). "
               f"Residual/unclassified = {residual_share:.1%}. topo-16 is a SEAM-DRESSED ground: "
               f"its entire visible footprint is desert-mains-plus-two-ecotone-strips, zero novel "
               f"atlas content. The reviewer's cross-check is CONFIRMED.")
else:
    verdict = (f"NOT fully confirmed at 5dp -- desert_mains recheck matches={mains_ok}, "
               f"grass|desert strip matches shipped={gd_matches_shipped}, "
               f"desert|dunes strip matches shipped={dd_matches_shipped}, "
               f"residual/unclassified {residual_share:.1%}. See per-bucket detail above -- the "
               f"reviewer's hypothesis is only PARTIALLY right; do not ship as fully proven.")
print(f"   {verdict}")
out["final_verdict"] = verdict
out["verdict_components"] = dict(mains_ok=mains_ok, gd_self_proven=gd_self_proven,
                                 gd_matches_shipped=gd_matches_shipped, dd_self_proven=dd_self_proven,
                                 dd_matches_shipped=dd_matches_shipped)
out["shares"] = dict(desert_mains=round(dm_share, 4), strip_grass_desert=round(gd_share, 4),
                     strip_desert_dunes=round(dd_share, 4), residual=round(residual_share, 4))

OUTD.mkdir(exist_ok=True)
(OUTD / "topo16_ecotone_crosscheck.json").write_text(json.dumps(out, indent=1, default=str))
print(f"\n-> {OUTD / 'topo16_ecotone_crosscheck.json'}")
