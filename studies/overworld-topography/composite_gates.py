"""COMPOSITE GATES -- THE FINAL-COMPOSITE RULE (L7) as ONE callable battery.

THE GENERATOR FOLD-BACK, module 2 of 2.  Rounds 1-8 scattered their acceptance criteria across
``uvf_gates.py`` / ``uvf_gates4.py`` / per-round inline asserts inside ``uvf_fix7.py`` /
``uvf_fix8.py``.  This module consolidates them into functions a GENERATOR can run on its OWN final
composite and REFUSE to emit on any red.

EVERY body here is either imported from, or lifted with attribution from, the round that proved it.
Nothing is re-derived from prose.

  gate_zero_uv_area            <- uvf_gates.gate1_uv_validity           (GATE1_FRAC_CEILING = 0.0005)
  gate_one_window_family_aware <- uvf_gates4.family_window_coherence_check  (reconstruct through the
                                  tri's OWN family's grassland.ground_uv space; >= all-but-1)
  gate_family_rect_membership  <- uvf_gates4.family_rect_membership_check    (REGION_EPS = 0.006)
  gate_sea_3predicate          <- uvf_gates.gate2_sea_plan_disjoint     (A calibrated all-3-verts
                                  submerged-TRI Y-order, B <=4x adjacent-block uniformity,
                                  C real-sea disjoint excluding the Sea4 underlay + 1-tri placeholders)
  gate_stage4_plumbing         <- rung_f_build.stage4_composite_plumbing (flat-mesh invariant, grid
                                  bounds, weld_audit 0, frame bounds, NEW down-facing 0, once-edges
                                  above the y=0 skirt 0)
  gate_stock_envelope          <- NEWLY AUTHORED for the fold (see THE ENVELOPE CALIBRATION below);
                                  the sigma_max measurement body is lifted from uvf_fix8.sigma_max /
                                  uvf_sliver_probe's stretch lane, but the pass/fail BOUNDARY did not
                                  exist anywhere before this module.
  gate_spike_step_census_empty <- uvf_fix6/uvf_fix7's census, PROMOTED from a target-finder to a
                                  post-build "0 qualifying" assertion (generic -- never a per-site count)
  gate_orphan_census_empty     <- uvf_fix8's 4-predicate orphan census, same promotion

THE ONE-WINDOW GATE'S INPUT CHANGED, DELIBERATELY.  uvf_gates4 had to RE-DERIVE which tris were
synthesized from the SPECIMEN's UV-degenerate signature (there was no other record).  A generator
KNOWS provenance, so this module takes the synthesized set and the per-tri family/window directly.
That is strictly stronger: the classifier can no longer disagree with the builder.

THE ENVELOPE CALIBRATION (out/foldback/envelope_calibration.json, measured 2026-07-25, read-only):
  ground UV-stretch = per-tri sigma_max / the same family's flat-tri (dip<10deg) median sigma_max.
    STOCK Cleyra 13-15,11-12 : p50 1.000  p95 1.166  p99 1.274  max 1.508  frac>1.41 = 0.13%
    STOCK dunes mass 18-20,3 : p50 1.001  p95 1.178  p99 1.272  max 1.457  frac>1.41 = 0.13%
    FIXED8 (ACCEPTED IN-GAME): p50 1.000  p95 1.554  p99 2.482  max 58.13  frac>1.41 = 7.19%
  READ THAT LAST ROW BEFORE TIGHTENING ANYTHING.  A hard map-wide "<=1.41x" ceiling would REFUSE the
  very build the owner accepted after 8 rounds -- uvf_fix7.py's own docstring already names the
  over-stretch population (100% synthesized fill, long plan-projected ear-clip/contour-tile slivers)
  as a SEPARATE texture-lane job.  It is structural to the ONE-WINDOW law itself: a fill tri spanning
  more than one 4u cell gets all three UVs clamped into a single window, so a large tri necessarily
  carries a large sigma.  Per CALIBRATE-THE-INSTRUMENT, the gate therefore splits:
    E1 CARRIED ground stays inside the measured stock envelope        -- HARD (it is byte-verbatim)
    E2 SYNTHESIZED ground DENSITY BAND (the population median)        -- HARD (this is the L1 defect
       class: one constant/incorrectly-scaled window over a whole patch moves the MEDIAN, and that is
       what "density within the stock band" means)
    E3 SYNTHESIZED tail fraction over the 1.41x stock ceiling         -- ADVISORY, reported with its
       number every run, named as the open texture lane.

READ-ONLY vs the game install.  This module never writes game files and never deploys.
"""
from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit.world import extract as X                       # noqa: E402
from ff9mapkit.world import mesh as M                          # noqa: E402
from ff9mapkit.world import grassland as G                     # noqa: E402

import uvf_gates as GATES1                                     # noqa: E402  (gate1 / gate2 bodies)

CELL = 4.0
BLOCK = 64.0
FAMILIES = ("grass", "desert", "dunes")

# ---- thresholds, each with its proving round -------------------------------------------------------
ZERO_UV_FRAC_CEILING = GATES1.GATE1_FRAC_CEILING          # 0.0005   (uvf_gates.py:70)
ONE_WINDOW_FRAC_CEILING = 0.0005                          # uvf_gates4.py:72 (same ceiling family)
REGION_EPS = 0.006                                        # transplant.GroundRetile._EPS, uvf_gates4:73
UV_AREA_EPS = 1e-6                                        # uvf_fix2.AREA_EPS
# --- the envelope numbers, measured (never guessed) -- see the module docstring ---------------------
STOCK_STRETCH_CEILING = 1.41                              # uvf_fix7/uvf_fix8's stock ground ceiling
STOCK_STRETCH_MAX_MEASURED = 1.508                        # stock Cleyra max, out/foldback calibration
CARRIED_STRETCH_CEILING = 1.55                            # E1: stock max 1.508 + 3% instrument slack
CARRIED_OVER_CEILING_FRAC = 0.01                          # E1: stock's own frac>1.41 is 0.0013
SYNTH_DENSITY_BAND = (0.85, 1.20)                         # E2: stock p50 1.000, p95 1.166/1.178
SYNTH_TAIL_ADVISORY_REF = 0.2035                          # E3: FIXED8's 469/2305 on the SAME
#   synth-only denominator (its 0.0719 headline uses the all-ground denominator 469/6526)
FLAT_DIP_T = 10.0                                         # "flat" for the per-family baseline


def _g(name, ok, detail="", advisory=False):
    return dict(name=("ADVISORY " + name) if advisory else name, ok=bool(ok), detail=str(detail)[:2000])


# ====================================================================================================
#  geometry helpers (lifted: uvf_fix8.sigma_max / dip_deg / uv_area, uvf_gates.uv_area)
# ====================================================================================================
def uv_area(uv3):
    (u0, v0), (u1, v1), (u2, v2) = uv3
    return abs((u1 - u0) * (v2 - v0) - (u2 - u0) * (v1 - v0)) / 2.0


def dip_deg(w3):
    a, b, c = w3
    e1 = [b[k] - a[k] for k in range(3)]
    e2 = [c[k] - a[k] for k in range(3)]
    n = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
    nl = math.sqrt(sum(v * v for v in n))
    if nl < 1e-9:
        return None
    return math.degrees(math.acos(min(1.0, abs(n[1]) / nl)))


def sigma_max(w3, uv3):
    """largest singular value (world units per UV unit) of the affine uv->world map.
    LIFTED VERBATIM from uvf_fix8.py:172-192."""
    a = uv3[1][0] - uv3[0][0]
    b = uv3[2][0] - uv3[0][0]
    c = uv3[1][1] - uv3[0][1]
    d = uv3[2][1] - uv3[0][1]
    det = a * d - b * c
    if abs(det) < 1e-12:
        return None
    inv = ((d / det, -b / det), (-c / det, a / det))
    e = [[w3[1][k] - w3[0][k], w3[2][k] - w3[0][k]] for k in range(3)]
    jm = [[e[k][0] * inv[0][0] + e[k][1] * inv[1][0],
           e[k][0] * inv[0][1] + e[k][1] * inv[1][1]] for k in range(3)]
    g00 = sum(jm[k][0] * jm[k][0] for k in range(3))
    g01 = sum(jm[k][0] * jm[k][1] for k in range(3))
    g11 = sum(jm[k][1] * jm[k][1] for k in range(3))
    tr, dt = g00 + g11, g00 * g11 - g01 * g01
    disc = max(0.0, tr * tr / 4.0 - dt)
    return math.sqrt(max(0.0, tr / 2.0 + math.sqrt(disc)))


# ====================================================================================================
#  GATE -- ZERO-UV-AREA (uvf_gates.gate1_uv_validity, run on the staged tree)
# ====================================================================================================
def gate_zero_uv_area(stage_dir, blocks):
    r = GATES1.gate1_uv_validity(sorted(blocks), Path(stage_dir), "composite")
    return r, _g("L7-1 ZERO-UV-AREA: staged Terrain zero-uv-area fraction <= "
                 f"{ZERO_UV_FRAC_CEILING} AND 0 bit-identical-UV tris (uvf_gates.gate1_uv_validity)",
                 r["passed"],
                 f"tris={r['total_tris']} zero_uv={r['total_zero_uv_area']} "
                 f"frac={r['zero_uv_area_frac']} bit_identical={r['total_bit_identical']}")


# ====================================================================================================
#  GATE -- ONE-WINDOW COHERENCE, FAMILY-AWARE (uvf_gates4.family_window_coherence_check)
# ====================================================================================================
def gate_one_window_family_aware(synth_records, decoded):
    """``synth_records`` = [dict(vw=[3 world pts], uv=[3 uv], fam=str)] for EVERY synthesized tri of
    the final composite; ``decoded`` = the (quad,ori) cell field.  A tri passes when its on-disk UVs
    are reproducible from ONE (quad,ori) window -- its centroid cell first, then each vertex own-cell
    -- through ITS OWN family's grassland.ground_uv space.  Body lifted from uvf_gates4.py:123-195."""
    n = single = multi = 0
    per_family = defaultdict(Counter)
    exc = []
    over_window = 0
    quad_diag = math.hypot(G.GRASS_U_HALF[0][1] - G.GRASS_U_HALF[0][0],
                           G.GRASS_V_HALF[0][1] - G.GRASS_V_HALF[0][0])
    for d in synth_records:
        fam = d["fam"]
        uv3 = d["uv"]
        vw = d["vw"]
        n += 1
        cx = sum(p[0] for p in vw) / 3.0
        cz = sum(p[2] for p in vw) / 3.0
        cand = [(math.floor(cx / CELL), math.floor(cz / CELL))]
        cand += [(math.floor(p[0] / CELL), math.floor(p[2] / CELL)) for p in vw]
        ok = False
        for cell in cand:
            if cell not in decoded:
                continue
            q, o = decoded[cell][0], decoded[cell][1]
            pred = [tuple(G.ground_uv(p[0], p[2], cell, q, o, fam)) for p in vw]
            if all(abs(pred[k][0] - uv3[k][0]) < 5e-6 and abs(pred[k][1] - uv3[k][1]) < 5e-6
                   for k in range(3)):
                ok = True
                break
        single += ok
        per_family[fam]["single" if ok else "multi"] += 1
        multi += (not ok)
        e = max(math.hypot(uv3[a][0] - uv3[b][0], uv3[a][1] - uv3[b][1])
                for a in range(3) for b in range(a + 1, 3))
        exc.append(e)
        if e > quad_diag + 1e-9:
            over_window += 1
    frac = (multi / n) if n else None
    passed = (n > 0 and frac is not None and frac <= ONE_WINDOW_FRAC_CEILING + 1e-12)
    exc.sort()
    r = dict(n_tris=n, single_window_reconstructed=single, multi_window_or_unreconstructed=multi,
             multi_window_frac=round(frac, 6) if frac is not None else None,
             threshold=ONE_WINDOW_FRAC_CEILING,
             per_family={f: dict(per_family[f]) for f in FAMILIES},
             one_window_scale=round(quad_diag, 6),
             excursion_p50=round(exc[len(exc) // 2], 5) if exc else None,
             excursion_max=round(exc[-1], 5) if exc else None,
             tris_spread_over_one_window_scale=over_window, passed=passed)
    return r, _g("L7-2 ONE-WINDOW (family-aware): every synthesized tri's 3 UVs reproduce from ONE "
                 "(cell,quad,ori) window in its OWN family's ground_uv space "
                 "(uvf_gates4.family_window_coherence_check)", passed,
                 f"tris={n} single={single} multi={multi} frac={r['multi_window_frac']} "
                 f"per_family={r['per_family']}")


# ====================================================================================================
#  GATE -- FAMILY MAINS-RECT MEMBERSHIP (uvf_gates4.family_rect_membership_check)
# ====================================================================================================
def gate_family_rect_membership(synth_records):
    regions = {f: G.ground_main_region(f) for f in FAMILIES}
    out_of_region = Counter()
    zero_area = Counter()
    n_checked = Counter()
    for d in synth_records:
        fam = d["fam"]
        uv3 = d["uv"]
        lo_u, lo_v, hi_u, hi_v = regions[fam]
        n_checked[fam] += 1
        for (u, v) in uv3:
            if not (lo_u - REGION_EPS <= u <= hi_u + REGION_EPS
                    and lo_v - REGION_EPS <= v <= hi_v + REGION_EPS):
                out_of_region[fam] += 1
        if uv_area(uv3) < UV_AREA_EPS:
            zero_area[fam] += 1
    passed = (not out_of_region) and (not zero_area)
    r = dict(tris_checked_by_family=dict(n_checked), out_of_region_by_family=dict(out_of_region),
             zero_area_by_family=dict(zero_area),
             regions={f: [round(x, 6) for x in regions[f]] for f in FAMILIES},
             region_eps=REGION_EPS, passed=passed)
    return r, _g("L7-3 FAMILY-RECT MEMBERSHIP: every synthesized UV inside its own family's "
                 "catalogued mains rect, 0 zero-area (uvf_gates4.family_rect_membership_check)",
                 passed, f"checked={dict(n_checked)} out_of_region={dict(out_of_region)} "
                         f"zero_area={dict(zero_area)}")


# ====================================================================================================
#  GATE -- THE 3-PREDICATE SEA GATE (uvf_gates.gate2_sea_plan_disjoint)
# ====================================================================================================
def gate_sea_3predicate(stage_dir, blocks):
    r = GATES1.gate2_sea_plan_disjoint(sorted(blocks), Path(stage_dir), "composite")
    return r, _g("L7-4 SEA 3-PREDICATE: (A) 0 fully-submerged land tris (calibrated Y-order), "
                 "(B) adjacent-block Sea4 plan-area ratio <= 4x, (C) real-sea/land plan-disjoint "
                 "with the Sea4 underlay + 1-tri placeholders excluded (uvf_gates.gate2_sea_plan_"
                 "disjoint)", r["passed"],
                 f"A={r['A_y_order']['fully_submerged_tris_GATING']} "
                 f"B_max_ratio={r['B_uniformity']['max_ratio']} "
                 f"C_overlap={r['C_real_sea_disjoint']['overlap_frac']}")


# ====================================================================================================
#  GATE -- STAGE-4 PLUMBING (rung_f_build.stage4_composite_plumbing, lifted verbatim, de-globalised)
# ====================================================================================================
def gate_stage4_plumbing(final_blocks, carried_cells, tri_provenance=None):
    """LIFTED from rung_f_build.py:243-342.  Two changes: the module-level ``gate()`` side effect is
    replaced by a returned gate list, so a generator can consume it; and (D3, 2026-07-25) the
    DOWN-FACING gate's provenance split no longer guesses from the plan.

    D3 -- THE PROVENANCE LABEL.  The lifted body split down-facing tris by ``cell in carried_cells``:
    a PLAN-POSITION heuristic.  Minted fill emitted INTO the carry footprint (the fill over the
    donor's dropped topo-59 shaft) therefore scored as "carried stock down-facing ... faithful" and
    was exempted -- 3 tris, in every historical build, invisible to 8 rounds of gates.  ``carried``
    is not a place; it is a fact the pipeline already KNOWS.  ``tri_provenance`` (``{blk: [cls, ...]}``
    aligned 1:1 with ``final_blocks[blk].tris``, cls in {carried, carried_shaved, synth, frame}) is
    the pipeline's own sentinel bookkeeping and is used when supplied; ``carried_cells`` remains the
    documented fallback for callers that have no bookkeeping to offer, and the gate says which one it
    used.  Only CARRIED classes are exempt-but-counted; synth and frame must be 0."""
    gates = []
    flat_bad = []
    grid_ok = True
    for blk, bm in final_blocks.items():
        if bm.vcount != len(bm.flat_index) or len(bm.flat_index) != 3 * len(bm.tris):
            flat_bad.append((list(blk), bm.vcount, len(bm.flat_index), len(bm.tris)))
        grid_ok = grid_ok and M.block_in_grid(blk[0], blk[1])
    gates.append(_g("L7-5a FLAT-MESH invariant (vcount==indexCount==3*tris) on every composite block",
                    not flat_bad, f"{flat_bad[:6]}"))
    gates.append(_g("L7-5b GRID BOUNDS (every composite block on the 24x20 grid)", grid_ok))

    weld_total = 0
    weld_detail = {}
    for blk, bm in final_blocks.items():
        w = len(M.weld_audit([bm]))
        if w:
            weld_detail[f"{blk[0]},{blk[1]}"] = w
        weld_total += w
    gates.append(_g("L7-5c WELD AUDIT (0 near-miss vertex pairs in every composite block frame)",
                    weld_total == 0, f"total={weld_total} per_block={weld_detail}"))

    fbad = {}
    for blk, bm in final_blocks.items():
        lx = [v[0] for v in bm.verts]
        lz = [v[2] for v in bm.verts]
        if not (-0.06 <= min(lx) and max(lx) <= BLOCK + 0.06
                and -BLOCK - 0.06 <= min(lz) and max(lz) <= 0.06):
            fbad[f"{blk[0]},{blk[1]}"] = (round(min(lx), 3), round(max(lx), 3),
                                          round(min(lz), 3), round(max(lz), 3))
    gates.append(_g("L7-5d FRAME BOUNDS (local verts inside the block frame +/- slack)",
                    not fbad, f"{fbad}"))

    prov_source = "sentinel bookkeeping" if tri_provenance else "carried_cells plan fallback"
    gpos = []
    gtris = []
    prov_mismatch = 0
    for blk, bm in final_blocks.items():
        base = len(gpos)
        ox, oz = X.block_world_origin(blk[0], blk[1])
        for v in bm.verts:
            gpos.append((v[0] + ox, v[1], v[2] + oz))
        provs = (tri_provenance or {}).get(blk)
        if provs is not None and len(provs) != len(bm.tris):
            raise AssertionError(f"tri_provenance for block {blk} is {len(provs)} long, "
                                 f"the block has {len(bm.tris)} tris -- the 1:1 alignment the "
                                 f"D3 provenance label depends on is broken")
        for ti, tri in enumerate(bm.tris):
            w = [(bm.verts[tri[q]][0] + ox, bm.verts[tri[q]][2] + oz) for q in range(3)]
            cx = sum(p[0] for p in w) / 3.0
            cz = sum(p[1] for p in w) / 3.0
            cell = (math.floor(cx / CELL), math.floor(cz / CELL))
            by_plan = cell in carried_cells
            if provs is not None:
                cls = provs[ti]
                carried = cls in ("carried", "carried_shaved")
            else:
                cls = "carried" if by_plan else "frame"
                carried = by_plan
            if carried != by_plan:
                prov_mismatch += 1
            gtris.append((base + tri[0], base + tri[1], base + tri[2], carried, cls))
    down_carried = down_grass = 0
    down_by_cls = Counter()
    for (i, j, k, carried, cls) in gtris:
        a, b, c = gpos[i], gpos[j], gpos[k]
        ny2 = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2])
        if ny2 <= 0:
            down_by_cls[cls] += 1
            if carried:
                down_carried += 1
            else:
                down_grass += 1
    gates.append(_g("L7-5e DOWN-FACING (D3 provenance): 0 downward-wound tris among the SYNTHESIZED "
                    "fill + the minted grass FRAME/weld apron; only byte-verbatim CARRIED donor tris "
                    "are exempt, and they are counted", down_grass == 0,
                    f"down_synth_or_frame={down_grass} down_carried_faithful={down_carried} "
                    f"by_class={dict(down_by_cls)} provenance={prov_source} "
                    f"plan_heuristic_disagreements={prov_mismatch}"))

    ecnt = Counter()
    for (i, j, k, _c, _cls) in gtris:
        pts = [(round(gpos[v][0], 3), round(gpos[v][1], 3), round(gpos[v][2], 3)) for v in (i, j, k)]
        for q in range(3):
            if pts[q] == pts[(q + 1) % 3]:
                continue
            ecnt[tuple(sorted((pts[q], pts[(q + 1) % 3])))] += 1
    open_bad = [e for e, nn in ecnt.items() if nn == 1
                and not (e[0][1] <= 1e-3 and e[1][1] <= 1e-3)]

    def _cls(e):
        (a, b) = e
        onbord = any(abs(p - round(p / BLOCK) * BLOCK) < 1e-2 for p in (a[0], a[2], b[0], b[2]))
        offgrid = any(abs(p - round(p / CELL) * CELL) > 1e-2 for p in (a[0], a[2], b[0], b[2]))
        return ("border" if onbord else "interior") + ("_offgrid" if offgrid else "_grid")
    open_classes = Counter(_cls(e) for e in open_bad)
    gates.append(_g("L7-5f WELD-INTEGRITY (0 once-edges above the y=0 sea skirt = watertight "
                    "composite)", len(open_bad) == 0,
                    f"open_edges={len(open_bad)} classes={dict(open_classes)} "
                    f"sample={open_bad[:3]}"))
    r = dict(flat_mesh_ok=not flat_bad, grid_ok=grid_ok, weld_near_miss=weld_total,
             frame_bounds_ok=not fbad, frame_bad=fbad,
             down_grass_or_apron=down_grass, down_carried_faithful=down_carried,
             down_by_class=dict(down_by_cls), provenance_source=prov_source,
             plan_heuristic_disagreements=prov_mismatch,
             open_edges_above_skirt=len(open_bad), open_edge_classes=dict(open_classes),
             open_edge_sample=[list(e) for e in open_bad[:6]])
    return r, gates


# ====================================================================================================
#  GATE -- STOCK ENVELOPE (NEWLY AUTHORED; measurement body lifted from uvf_fix8/uvf_sliver_probe)
# ====================================================================================================
def gate_stock_envelope(tri_rows):
    """``tri_rows`` = [(fam, w3, uv3, cls)] over every GROUND tri of the final composite, with
    ``cls`` in {"carried", "carried_shaved", "frame", "synth"}.

    THE FOUR PROVENANCE CLASSES ARE NOT INTERCHANGEABLE, and two self-test iterations proved it:
      * lumping the MINTED FRAME in with the carry read a max of 208x and redded E1.  That 208x tri
        is a ``build_landmass`` coast sliver -- the pre-fix specimen tree measures the identical
        208.2x -- i.e. it is the kit's own minted-coast vocabulary, not a carry defect;
      * lumping the L5a-SHAVED carried tris in with the untouched carry read a max of 1.97x and
        redded E1 again.  A shaved tri is byte-verbatim in UV but NOT in geometry -- moving its apex
        is the whole point of L5a -- so holding it to stock's envelope is holding the fix against
        itself.  (FIXED8, the accepted tree, measures exactly the same effect: carried dunes max
        2.14x, 2 tris, all of them round-6/7 shave sites.)
    Only UNTOUCHED CARRIED tris are byte-verbatim stock, so they are the only class E1 can gate."""
    per_fam = defaultdict(list)
    for (fam, w3, uv3, cls) in tri_rows:
        s = sigma_max(w3, uv3)
        d = dip_deg(w3)
        if s is None or d is None:
            continue
        per_fam[fam].append((s, d, cls))
    pops = {"carried": [], "carried_shaved": [], "frame": [], "synth": []}
    baselines = {}
    for fam, rows in per_fam.items():
        flat = sorted(s for (s, d, _c) in rows if d < FLAT_DIP_T)
        if not flat:
            flat = sorted(s for (s, _d, _c) in rows)
        base = flat[len(flat) // 2] if flat else None
        if not base:
            continue
        baselines[fam] = round(base, 3)
        for (s, _d, cls) in rows:
            pops[cls].append(s / base)
    for v in pops.values():
        v.sort()
    carried, shaved, frame, synth = (pops["carried"], pops["carried_shaved"],
                                     pops["frame"], pops["synth"])

    def q(a, p):
        return round(a[int(p * (len(a) - 1))], 4) if a else None

    def block(a):
        n_over = sum(1 for x in a if x > STOCK_STRETCH_CEILING)
        return dict(n=len(a), p50=q(a, 0.5), p95=q(a, 0.95), p99=q(a, 0.99), max=q(a, 1.0),
                    n_over_stock_ceiling=n_over,
                    frac_over_stock_ceiling=round((n_over / len(a)) if a else 0.0, 6))

    b_c, b_sh, b_f, b_s = block(carried), block(shaved), block(frame), block(synth)
    e1 = (bool(carried) and b_c["max"] <= CARRIED_STRETCH_CEILING
          and b_c["frac_over_stock_ceiling"] <= CARRIED_OVER_CEILING_FRAC)
    med = b_s["p50"]
    e2 = bool(synth) and (SYNTH_DENSITY_BAND[0] <= med <= SYNTH_DENSITY_BAND[1])
    s_frac = b_s["frac_over_stock_ceiling"]
    n_all = len(carried) + len(shaved) + len(frame) + len(synth)
    all_frac = round((b_c["n_over_stock_ceiling"] + b_sh["n_over_stock_ceiling"]
                      + b_f["n_over_stock_ceiling"] + b_s["n_over_stock_ceiling"]) / n_all, 6) \
        if n_all else 0.0

    r = dict(family_baselines_sigma=baselines, carried=b_c, carried_shaved=b_sh, frame=b_f,
             synthesized=b_s,
             all_ground_frac_over_stock_ceiling=all_frac,
             thresholds=dict(stock_ceiling=STOCK_STRETCH_CEILING,
                             carried_max_ceiling=CARRIED_STRETCH_CEILING,
                             carried_over_ceiling_frac=CARRIED_OVER_CEILING_FRAC,
                             synth_density_band=list(SYNTH_DENSITY_BAND),
                             synth_tail_advisory_reference=SYNTH_TAIL_ADVISORY_REF),
             E1_carried_inside_stock_envelope=e1, E2_synth_density_in_band=e2,
             E3_synth_tail_frac_over_ceiling=s_frac,
             reference_measurements=dict(
                 stock_cleyra=dict(p50=1.000, p95=1.166, p99=1.274, max=1.508, frac_over_1p41=0.0013),
                 stock_dunes=dict(p50=1.001, p95=1.178, p99=1.272, max=1.457, frac_over_1p41=0.0013),
                 fixed8_accepted_all_ground=dict(p50=1.000, p95=1.554, p99=2.482, max=58.13,
                                                 frac_over_1p41=0.0719, n_over=469, n=6526),
                 fixed8_accepted_synth_only=dict(n_over=469, n=2305,
                                                 frac_over_1p41=SYNTH_TAIL_ADVISORY_REF)))
    gates = [
        _g("L7-6a STOCK ENVELOPE / CARRIED: every UNTOUCHED CARRIED (byte-verbatim donor) ground "
           f"tri's UV-stretch stays inside the measured stock envelope (max <= "
           f"{CARRIED_STRETCH_CEILING}x, frac over {STOCK_STRETCH_CEILING}x <= "
           f"{CARRIED_OVER_CEILING_FRAC})", e1,
           f"n={b_c['n']} max={b_c['max']} p99={b_c['p99']} "
           f"frac_over={b_c['frac_over_stock_ceiling']} | L5a-shaved carried (geometry moved BY "
           f"DESIGN, reported not gated): n={b_sh['n']} max={b_sh['max']}"),
        _g("L7-6b STOCK ENVELOPE / DENSITY BAND: the synthesized ground population's MEDIAN texel "
           f"density sits in the stock band {SYNTH_DENSITY_BAND} (this is what a constant or "
           "mis-scaled window moves -- the L1 defect class)", e2,
           f"n={b_s['n']} p50={med} p95={b_s['p95']}"),
        _g("L7-6c STOCK ENVELOPE / SYNTH TAIL over the 1.41x stock ceiling -- ADVISORY, the open "
           f"texture lane named by uvf_fix7 (accepted FIXED8 measures {SYNTH_TAIL_ADVISORY_REF} on "
           "the SAME synth-only denominator, 469/2305; a hard ceiling here would refuse the "
           "ratified build)", s_frac <= SYNTH_TAIL_ADVISORY_REF + 1e-9,
           f"synth_frac={s_frac} n={b_s['n_over_stock_ceiling']}/{b_s['n']} max={b_s['max']} | "
           f"all-ground frac={all_frac} (FIXED8 all-ground 0.0719) | minted-frame max={b_f['max']}",
           advisory=True),
    ]
    return r, gates


# ====================================================================================================
#  GATE -- SPIKE/STEP CENSUS EMPTY (uvf_fix6 + uvf_fix7's rule, promoted to a post-build assertion)
# ====================================================================================================
def gate_spike_step_census_empty(census):
    n = census.get("n_spikes", None)
    ok = (n == 0)
    return _g("L7-7 SPIKE/STEP CENSUS EMPTY: 0 carried ground positions qualify post-build under the "
              "round-6/7 rule (ground topo w/ rock 58/31 exempt; residual >= 0.80u; CONE arm "
              "prominence >= 0.40u OR STEP arm prominence >= 0.0u AND welded drop >= 1.50u; outside "
              "the basin discs; Terrain-only) -- GENERIC, never a per-site count", ok,
              f"n_qualifying={n} verdicts={census.get('verdict_hist')}")


def gate_orphan_census_empty(census):
    n = census.get("n_orphaned", None)
    ok = (n == 0)
    return _g("L7-8 ORPHAN-DECAL CENSUS EMPTY: 0 carried ground tris post-build satisfy the round-8 "
              "4-predicate rule (carried AND ground topo AND uncatalogued rect AND live dip < 25deg "
              "AND own-donor dip >= 25deg) -- GENERIC, never a per-site count", ok,
              f"n_orphaned={n} n_uncatalogued_carried={census.get('n_uncatalogued_carried')}")


# ====================================================================================================
#  THE ORCHESTRATOR
# ====================================================================================================
def run_composite_gates(ctx):
    """``ctx`` keys:
        stage_dir       Path of the staged FF9CustomMap-world tree
        blocks          iterable of (bx,by) staged blocks
        final_blocks    {blk: BlockMesh} of the final composite Terrain
        carried_cells   set of 4u cells the carry occupies (the down-facing split's LEGACY fallback)
        tri_provenance  {blk: [cls, ...]} aligned 1:1 with final_blocks[blk].tris, cls in
                        {carried, carried_shaved, synth, frame} -- the pipeline's own sentinel
                        bookkeeping; supersedes carried_cells for the D3 down-facing split
        synth_records   [dict(vw, uv, fam)] one per synthesized tri
        decoded         {cell: (quad, ori, method)}
        ground_tri_rows [(fam, w3, uv3, is_synth)] over every GROUND tri
        spike_census    the post-build spike/step census result
        orphan_census   the post-build orphan-decal census result
    Returns (results, gates) -- ``gates`` is the same list-of-dicts shape rung_f_build.py's all_green
    refusal logic already consumes."""
    results = {}
    gates = []

    r, g = gate_zero_uv_area(ctx["stage_dir"], ctx["blocks"])
    results["zero_uv_area"] = r
    gates.append(g)

    r, g = gate_one_window_family_aware(ctx["synth_records"], ctx["decoded"])
    results["one_window_family_aware"] = r
    gates.append(g)

    r, g = gate_family_rect_membership(ctx["synth_records"])
    results["family_rect_membership"] = r
    gates.append(g)

    r, g = gate_sea_3predicate(ctx["stage_dir"], ctx["blocks"])
    results["sea_3predicate"] = r
    gates.append(g)

    r, gs = gate_stage4_plumbing(ctx["final_blocks"], ctx["carried_cells"],
                                 tri_provenance=ctx.get("tri_provenance"))
    results["stage4_plumbing"] = r
    gates.extend(gs)

    r, gs = gate_stock_envelope(ctx["ground_tri_rows"])
    results["stock_envelope"] = r
    gates.extend(gs)

    gates.append(gate_spike_step_census_empty(ctx["spike_census"]))
    gates.append(gate_orphan_census_empty(ctx["orphan_census"]))
    results["spike_census"] = {k: v for k, v in ctx["spike_census"].items() if k != "rows"}
    results["orphan_census"] = {k: v for k, v in ctx["orphan_census"].items() if k != "rows"}
    return results, gates


def all_green(gates):
    """A gate whose name starts with ADVISORY never reds the build (rung_f_build.py's own rule)."""
    return all(g["ok"] for g in gates if not g["name"].startswith("ADVISORY"))
