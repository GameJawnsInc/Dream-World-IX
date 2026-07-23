"""RUNG E LAYOUT -- the 2-LOBE composition: the horseshoe massif (Rung D's proven single-lobe

anchor, UNCHANGED) merged with a NEW north/corridor lobe reaching through the reserved
(0-2,12-15) extension arm, converting the massif's former OPEN-OCEAN north coast into INTERIOR
land -- the mechanism Rung D's own postmortem named as the way past its 45.0u single-lobe
standoff ceiling (GROUND-FAMILY-DECODE-2026-07-19.md, "the massif IS the terminus, not an
obstacle"; the frontier-line convergence note in the latest brief commit).

Read first: ``rung_d_layout.py`` (the single-lobe design this rung extends -- SITE/ANCHOR-COUNT
change only, the downstream MBM generators are reused verbatim, imported not reimplemented);
``rung_d_build.py`` (the authoritative ratio-unit derivation + the 9 coded plumbing gates this
rung's stage0 site gates mirror); ``mixed_biome_mint.py`` (generate_partition_line / sector_retile
/ build_dressing / classify_side / make_context_provider / _mint_sea4, all reused UNCHANGED);
``contract_gd_composition.json`` (the stock statistics every threshold below cites).

THE MECHANISM -- reusing island.build_landmass's lobes>=2 pipeline, generalized to EXPLICIT
per-lobe centers (island.py's own ``mesh.multi_blob_outline`` only exposes HASH-DERIVED offsets,
mesh.py:488-493 -- no way to place a lobe at a chosen world point). This module therefore ports
``mesh.multi_blob_outline``'s OWN two-stage algorithm (mesh.py:476-524: an analytic
farthest-ray-circle-exit union of PLAIN CIRCLES, THEN a single SHARED wobble/corner
multiplicative pass over the unioned radius) verbatim, with explicit ``(offset_x, offset_z,
radius)`` circles instead of hash-derived ones -- see ``_explicit_circle_union_radius_fn`` below.
This is a deliberate, cited adaptation (RECON's option (b): a bespoke study-script duplicate of
a proven private technique, not a kit code change -- matches ``_rock_rim_ring``'s own precedent
of duplicating ``interior.py``'s ring-chaining machinery in-script rather than editing the kit).

TWO FINDINGS FROM BUILDING THIS (both real, both offline, zero playtest cost, see stage1's own
report keys for the numbers):

1. THE NAIVE RAY-CAST-A-POLYGON-UNION TRAP -- the recon's own suggested generalization ("ray-cast
   the DENTED/wobbled boundary polygons directly, take the max crossing per angle") is UNSOUND:
   a dented ``blob_outline`` ring is star-convex from ITS OWN centre only, not from an external
   reference point, so a ray from an external hub can cross a single dented ring's boundary at
   MULTIPLE disconnected arcs -- the "farthest crossing" then jumps discontinuously between two
   topologically distant parts of the SAME ring as the ray angle sweeps past a local dent (measured:
   dr up to 59u between 0.0000628-rad-adjacent samples -- not a resolution artifact, a genuine
   jump). ``island.build_landmass``'s BIG-MINT REFINEMENT (island.py:359-394) then chokes on the
   resulting boundary edge ("an over-8u grass edge has 1 owner(s)"), and finite adaptive bisection
   NEVER converges on a true jump (only on steep-but-continuous slopes). THE FIX is
   ``mesh.multi_blob_outline``'s own two-stage order: union PLAIN CIRCLES first (an analytic
   farthest-ray-CIRCLE-exit test is provably continuous in angle -- a max of finitely many smooth,
   single-valued-or-undefined-outside-their-cone functions, mesh.py:505-511), THEN apply the
   shared wobble multiplicatively over the whole unioned radius (mesh.py:494-499/514-519) --
   never per-lobe. Confirmed: 0 discontinuities (dr>1.0) over a 100000-sample fine scan once
   switched to this order (was 2, with one reaching dr=58.98).
2. THE SPIKE-HEIGHT DESIGN LAW (new, not in any prior study) -- even the analytic circle-union is
   NOT unconditionally artifact-free: a circle whose disk does NOT contain the reference centre C
   has a "grazing-tangent" edge where its contribution rises smoothly to ``sqrt(offset^2-R^2)``
   (a real, non-zero value -- NOT 0) right at the tangent angle, then drops out of the candidate
   set entirely just past it. If that tangent-spike value EXCEEDS the floor every other circle
   guarantees in that direction (e.g. a circle centred AT C gives a constant R everywhere), the
   spike wins the max and the union shows a visible jump/needle. The fix is a checked DESIGN
   CONSTRAINT, not a code fix: for every circle whose disk excludes C, require
   ``sqrt(offset^2 - R^2) < R_guard`` where ``R_guard`` is the radius of a circle centred
   EXACTLY at C (which has NO tangent edge at all -- q2=offset^2-proj^2 <= offset^2 = 0 <= R^2
   always, since offset=0). Verified both ways: SOUTH's own spike height (27.2u, offset 76.97
   vs R 72) sits under a 55-65u guard with wide margin (harmless, was never the visible failure);
   the ORIGINAL north placement's spike height (116.1u, offset 131.6 vs R 62) blew straight past
   a 55u guard -- that IS what produced the walk_filter_fails-inducing kink in the first pass, and
   shrinking the offset (closer north centre) below the guard closed it to a fully clean build.

THE SKEPTIC RESTRUCTURE ROUND (this session, second pass) -- the first pass (CONNECTOR R=65,
UNION_SMOOTH_PASSES defined but never applied, ONE line seed tried) shipped with GATE1/GATE3 both
FAILING (24.74u standoff, 88 contaminating dressing writes) and was sent back RESTRUCTURE. Every
finding was independently re-verified by fresh instrumentation (fresh subprocess re-runs, a full
88-entry GATE3 breakdown vs the report's own truncated sample[:10], a 100k-sample continuity scan,
a live game-install re-read of the footprint + the bx=3-4/by=12-15 caution zone) before any fix was
written -- see the review's own report for the instrumentation record. THREE fixes + ONE PROCESS
fix were prescribed and applied, plus one EXTENSION the live numbers themselves required (not
optional -- see NORTH_RADIUS's own comment):
  FIX 1(a) -- widen CONNECTOR_RADIUS so the connector-only angular sector stops being the union's
    thinnest part. The suggested 82-88u range turned out UNREACHABLE at this exact site (a live
    parameter sweep found two independent hard ceilings below it: >=71u already knocks the
    massif's own carve_mountain placement search off its proven bench -- apron_slope 9.2->7.4,
    outside the reproduction tolerance the review itself says must stay unchanged; >=73u already
    reaches block (3,15), a real non-open-ocean sea-prefab block, failing OPEN-OCEAN outright) --
    so CONNECTOR_RADIUS is raised only as far as 70.0u (the largest value that keeps BOTH the
    massif reproduction and the open-ocean gate green; see its own comment for the swept numbers).
  FIX 1(b) -- mesh.multi_blob_outline's own post-smooth pass, PREVIOUSLY DEAD CODE (defined,
    referenced nowhere), is now genuinely applied via ``_smooth_radius_fn`` -- a continuous
    angle-domain port of the SAME 3-point moving-average recursion (verified to match the discrete
    fixed-grid version to float precision, 3.55e-14, at the true n=160 verbatim resolution
    ``island.build_landmass``'s own real ``multi_blob_outline`` call site uses).
  FIX 1(c) -- ``generate_partition_line``'s own shape-matching retry (up to 600 tries/seed) has
    zero coastal-standoff awareness and only ONE seed was tried last session. ``_standoff_aware_
    line`` now tries LINE_N_CANDIDATES=16 independent seeds and keeps whichever shape-matched
    candidate has the BEST real (``_dist_to_coast_fn``, never the chord proxy) standoff -- proven
    load-bearing this session: the 16 candidates at the final site ranged 36.23-48.83u, the chosen
    seed (":0", the very first tried) happened to hit the ceiling, but seed ":5" alone would have
    reported 36.23u, still short of the 39.95u floor.
  FIX 1(a) EXTENSION -- fixing the connector-pinch bottleneck at CONNECTOR_RADIUS=70u REVEALS a
    SECOND, different bottleneck: the binding coast-standoff point moves to t=1.0 on the best
    termini chord -- i.e. the NORTH (Uaho) terminus's OWN rim-to-coast distance, which
    CONNECTOR_RADIUS cannot influence (a different lobe circle). The identical remedy (widen the
    now-thinnest lobe) is reapplied to NORTH_RADIUS, 70.0 -> 84.0u (swept safe up to 87.0u before
    the SAME block-(3,15) ceiling recurs) -- see its own comment for the full sweep. This is the
    fix's own named failure mode ("the connector-only sector is no longer the thinnest part of the
    union") recurring on a different lobe once the first instance is closed, not a new mechanism.
  FIX 2 -- ``_termination_decal_exclusion`` demotes any straddle/fringe CELL back to plain desert
    mains (dropped from dressing ELIGIBILITY, never written) whenever ANY of its own per-tri
    records would land within TERMINATION_DECAL_CLEAR_U of rock -- applied at the DRESSING step's
    eligibility filter (stage4), never at retile (``sector_retile``'s own ``anchors_realized=[]``
    stays untouched, per Rung D's own fix). A first attempt averaged a whole cell's records into
    ONE centroid before testing -- for a straddle cell that dilutes a genuinely-contaminating
    desert-side tri with its own far grass-side partner, and 3 residual GATE3 contaminations
    surfaced from exactly that mismatch; fixed by testing the MIN over each record's own centroid
    (matching GATE3's own per-write granularity exactly) -- see ``_termination_decal_exclusion``'s
    own docstring.
  PROCESS FIX -- GATE3's own "where does contamination concentrate" report now Counters the FULL
    contaminating-writes list (by anchor AND by block), never an eyeballed ``sample[:N]`` -- the
    review's own finding 3 traced the prior report's inverted "concentrates near Uaho" claim to
    exactly that truncation (true split was 60.2% south / 39.8% north).
Net result (live, re-verified below, not asserted): GATE1 line_min 24.74u -> 48.83u (>= the 39.95u
floor, though still short of the 64u target -- informational, not required to pass); GATE3 88 ->
0 contaminating writes; GATE2 stayed in-band throughout (1.7-2.0 range, comfortably under the
2.33 local band max); site gates + massif/Uaho reproduction all green; a fresh subprocess re-run
reproduces a byte-identical JSON (diff exit 0).

SITE (all circles independently verified this session -- see stage0/stage1's own report):
  SOUTH (the proven horseshoe bench, UNCHANGED, byte-for-byte the ``rung_d_layout.BENCH_*``
    params): centre (170,-1152), R=72, its OWN independent wobble (seed=42, undulation=0.11,
    n_corners=3, corner_strength=0.26) -- this only matters for STAGE1's fidelity comparison,
    since the FINAL union outline near the massif is generated under the SHARED wobble below,
    not this per-lobe formula (see finding 1).
  CONNECTOR (the hub -- centred exactly at the reference point C, guaranteeing full 360-degree
    coverage and ZERO tangent edge by construction): centre = C = (138,-1082), R=70 (raised from
    65.0 by FIX 1(a) -- see CONNECTOR_RADIUS's own comment for why 70.0, not the fix's own
    suggested 82-88u, is the site's real safe ceiling).
  NORTH (the corridor lobe, reaching into the reserved (0-2,12-15) arm through the by15/16 seam):
    centre (100,-1020), R=84 (raised from 70.0 by the FIX 1(a) EXTENSION above -- see
    NORTH_RADIUS's own comment). Spike height vs C: offset=72.72u < R=84u, so C sits INSIDE this
    circle's own disk -- NORTH now has NO tangent edge at all (spike height 0, the same
    unconditionally-safe case CONNECTOR's own 0-offset placement gets), independently re-verified
    live in stage0's own union.spikes report, not asserted here.
  Shared wobble (applied ONCE, over the whole 3-circle union): seed=1.0, undulation=0.16,
    n_corners=2, corner_strength=0.22, ripple=0.022, smooth=2 -- all mesh.multi_blob_outline's own
    defaults; smooth=2 is now GENUINELY APPLIED (FIX 1(b), ``_smooth_radius_fn`` -- previously
    defined, never called, see the SKEPTIC RESTRUCTURE section above).
  Outline sampling: 200 angularly-uniform base points + ADAPTIVE bisection (insert the angular
    midpoint wherever a consecutive world-space chord exceeds 6.0u -- a tighter margin than
    island.py's own 8.0u BIG-MINT ceiling, so its refinement pass is a confirmed no-op here)
    until every chord is <=6.0u; this design converges in a handful of splits -- the earlier
    polygon-union attempts (finding 1) needed >20000 splits and never converged, itself a clean
    discriminator between a sound and unsound mechanism.
  These parameters were reached by an offline parameter SEARCH this session (varying C/radii/
  seed against the real ``island.build_landmass`` + ``verify_landmass`` gates, not hand-derived
  geometry) -- see stage0's own gate report for the live-verified result, not this docstring's
  prose.

ANCHORS: the horseshoe donor [(5,15),(6,15),(5,16),(6,16)] carved ``near=(170,-1152)`` (the
  massif, unchanged from Rung D) + the Uaho donor (0,0) carved ``near=(80,-990)`` (the arm anchor
  -- picked by an offline scan of block-centre candidates against the real ``carve_mountain``
  gates, landing at realized centre (90,-1000), block (1,15); RECON's own hand-estimated block
  (1,12)/(1,13) turned out to be OUTSIDE this design's actual built footprint -- the union's real
  north reach stops around by13/14, not by12, a finding this module's stage1 contiguity report
  makes explicit rather than assuming RECON's estimate).

THIS SCRIPT IS READ-ONLY AGAINST THE GAME INSTALL, exactly like ``rung_d_layout.py`` -- every
stage composes IN-MEMORY; nothing is written to <game>/FF9CustomMap-world. Artifacts land under
``out/rung_e/``. No ``--apply`` path exists here (a build/deploy script, if the ratio settles
in-band, is a separate owner-gated step reusing ``mixed_biome_mint.py``'s own machinery, mirroring
``rung_d_build.py``'s relationship to this module).

Run from the repo root:  py studies/overworld-topography/rung_e_layout.py
"""
from __future__ import annotations

import copy
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit import config as _cfg                        # noqa: E402
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import interior as IN                  # noqa: E402
from ff9mapkit.world import island as ISL                   # noqa: E402
from ff9mapkit.world import mesh as M                        # noqa: E402

import mixed_biome_mint as MBM                               # noqa: E402  (generators reused verbatim)
import rung_d_layout as RDL                                   # noqa: E402  (shared constants + rim/coast helpers)
import seam_null_recon as SNR                                 # noqa: E402  (the null-cluster targets)

OUT_DIR = HERE / "out" / "rung_e"
OUT_JSON = OUT_DIR / "rung_e_layout.json"

_hash01 = M._hash01          # mesh.py's own deterministic pseudo-random hash, reused verbatim

# ================================================================================================
# SITE -- the 3-circle explicit union (see the module docstring's MECHANISM + SITE sections for
# the full derivation and the two findings that shaped these numbers).
# ================================================================================================
SOUTH_CENTER = RDL.BENCH_CENTER          # (170.0, -1152.0) -- byte-identical to the proven bench
SOUTH_RADIUS = RDL.BENCH_RADIUS          # 72.0
SOUTH_SEED = RDL.BENCH_SEED              # 42.0 (only used for stage1's fidelity comparison)
HORSESHOE_DONOR = RDL.HORSESHOE_DONOR    # [(5, 15), (6, 15), (5, 16), (6, 16)]

REF_CENTER = (138.0, -1082.0)            # C -- the connector's own centre (guarantees full 360 coverage)
# FIX 1(a) (skeptic RESTRUCTURE, findings 1/2): 65.0u made the connector the SMALLEST of the three
# circles and the ONLY one reaching the (114,-1102)-ish bearing where south+north both return "no
# intersection" -- a hub strictly smaller than the lobes it stitches pinches the waist there
# (measured: the wobbled hub-only contribution sank to ~61.6u against a coastline only ~31u away at
# that bearing -- the exact "waist pinches the coast inward" failure the task brief anticipated).
# The fix's own suggested range was 82-88u; a live parameter sweep this session (see the
# CONNECTOR_RADIUS EXTENSION note below NORTH_CENTER for the full record) found that range
# UNREACHABLE here without breaking a harder law first: >=71u already knocks the massif's own
# carve_mountain reproduction out of tolerance, >=73u already reaches real (non-open-ocean) block
# (3,15). 70.0u is therefore the LARGEST value that still keeps both the massif reproduction AND
# the open-ocean gate green -- raising it this far (65.0 -> 70.0) already resolves the ORIGINAL
# connector-pinch bottleneck (verified: that bottleneck's own former worst point is no longer
# binding at 70.0u); closing GATE1 the rest of the way needed a SECOND application of the same
# principle on the lobe that became the new bottleneck (NORTH_RADIUS, below).
CONNECTOR_RADIUS = 70.0
NORTH_CENTER = (100.0, -1020.0)
# FIX 1(a) EXTENSION (empirically required -- see the module docstring's SITE section for the full
# parameter-search record): CONNECTOR_RADIUS alone is CEILINGED at 70.0u by two independent hard
# constraints before it ever reaches the fix's own suggested 82-88u range -- >=71u shifts the
# massif's OWN carve_mountain placement search (realized centre (166,-1142) -> (164,-1142)),
# knocking apron_slope 9.2 -> 7.4 (outside the <0.5 reproduction tolerance the fix itself says must
# stay unchanged); >=73u newly reaches block (3,15), a REAL non-open-ocean sea-prefab block (sea3/
# sea5/sea4 content), failing the OPEN-OCEAN gate outright (both ceilings independently verified by
# a live parameter sweep this session). At CONNECTOR_RADIUS=70u (the largest safe value) + FIX 1(b)
# smoothing + FIX 1(c)'s 16-seed retry, the ORIGINAL connector-pinch bottleneck IS resolved (its own
# worst point, formerly ~24-33u, is no longer the binding constraint) -- but GATE1 STILL fails
# (34.57u) because the binding point has MOVED to t=1.0 on the best termini chord, i.e. the NORTH
# (Uaho) terminus's OWN rim-to-coast distance, which CONNECTOR_RADIUS cannot influence (it is
# governed by the NORTH lobe circle, not the hub). This is the SAME underlying failure mode fix
# 1(a) names ("the connector-only sector is no longer the thinnest part of the union") recurring on
# a DIFFERENT lobe once the first is fixed -- so the identical remedy (widen the currently-thinnest
# lobe) is applied to NORTH_RADIUS instead. A live sweep found NORTH_RADIUS safe up to 87.0u (>=88u
# reaches block (3,15) exactly as above); 84.0u is chosen for a 3-4u safety margin from that ceiling
# while clearing the 39.95u floor with room (worst_chord_clearance 48.83u at this value, verified
# live, not estimated) -- both anchors' reproduction (massif AND the informational Uaho comparison)
# stay byte-exact at this value (re-verified below, not assumed).
NORTH_RADIUS = 84.0
UAHO_DONOR = IN.MOUNTAIN_DONOR            # (0, 0)

UNION_WOBBLE_SEED = 1.0
UNION_UNDULATION = 0.16
UNION_N_CORNERS = 2
UNION_CORNER_STRENGTH = 0.22
UNION_RIPPLE = 0.022                      # mesh.multi_blob_outline's own default
UNION_SMOOTH_PASSES = 2                   # mesh.multi_blob_outline's own default
# FIX 1(b) (skeptic finding 4): UNION_SMOOTH_PASSES was DEFINED but never APPLIED anywhere in the
# original pass -- grep-confirmed (this constant appeared exactly once, its own definition). The
# angular step the smoothing kernel operates at, ported from island.py's own real call site
# (island.build_landmass's lobes>=2 branch calls ``M.multi_blob_outline(cx, cz, lobes=lobes,
# base_radius=base_radius, seed=seed, undulation=undulation)`` with NO ``n=`` override -- mesh.py's
# own default ``n=160`` is therefore the TRUE verbatim resolution its smoothing pass runs at, not
# this module's own UNION_N_BASE=200 adaptive-outline seed density).
UNION_SMOOTH_N = 160
UNION_N_BASE = 200
UNION_MAX_SEG = 6.0                       # tighter than island.py's own 8.0u BIG-MINT ceiling
# FIX 1(c) (skeptic findings 1/2/5): generate_partition_line's own shape-matching retry loop (up to
# 600 tries) has ZERO awareness of real coastal standoff -- only ONE line seed was ever tried in the
# prior pass. Try several seeds, score each by its REAL (``_dist_to_coast_fn``, never the 5-point
# chord proxy) minimum standoff, and keep the best-standoff candidate among those that still satisfy
# the straightness/turn targets (falling back to the best-scoring candidate, matching
# ``generate_partition_line``'s own single-seed fallback, only if none matched).
LINE_N_CANDIDATES = 16

SOUTH_NEAR = SOUTH_CENTER                 # carve_mountain near= for the massif (unchanged from Rung D)
NORTH_NEAR = (80.0, -990.0)               # carve_mountain near= for the Uaho arm anchor (this session's scan)

DEPTH_CAP = RDL.DEPTH_CAP                                   # 16.0 -- contract Law 6
LINE_SEED = "rung-e-layout:line"
DRESS_SEED = MBM.GD.DEFAULT_REDRESS_SEED

TARGET_STRAIGHTNESS = RDL.TARGET_STRAIGHTNESS
TARGET_TURN = RDL.TARGET_TURN
COAST_STANDOFF_TARGET = RDL.COAST_STANDOFF_TARGET             # 64.0
COAST_STANDOFF_CONTRACT_WORST = RDL.COAST_STANDOFF_CONTRACT_WORST  # 39.95

# THE TERMINATION-DECAL CLEAR RADIUS (contract's own termination law: nearest-topo49 distance at
# every real stock line termination measures 4.27-7.64u -- out/contract_gd_composition.json
# "termination" array, per_radius["10"].nearest_topo49_dist across the 4 real endpoints; re-read
# live below, not typed in). 8.0u is the smallest round number clearing the observed max (7.65u)
# with a small margin -- a dressed cell any closer than this to rock is CONTAMINATING the
# termination (the contract's law: plain mains touch rock directly, no decal).
TERMINATION_DECAL_CLEAR_U = 8.0

REPRO_BENCH = dict(blob_tris=713, ensemble_tris=122, rock_rigid_pct=0.84, apron_slope=9.2,
                   zip_rise=2.13, r_rim=54.3, n_span_blocks=10)
UAHO_KNOWN = dict(r_rim=20.0, clear_radius=35.0)               # mixed_biome_mint.py:100/123-126


def log(msg):
    print(msg)


# ================================================================================================
# THE EXPLICIT 3-CIRCLE UNION (mesh.multi_blob_outline's own algorithm, mesh.py:476-524, ported
# with EXPLICIT (offset_x, offset_z, radius) circles instead of hash-derived ones -- see the
# module docstring's MECHANISM + finding 1/2 for why this two-stage order is load-bearing).
# ================================================================================================
def _explicit_circle_union_radius_fn(circles, *, seed, undulation, n_corners, corner_strength,
                                     ripple=UNION_RIPPLE):
    """circles: [(offset_x, offset_z, radius), ...] relative to the shared reference centre.
    Returns radius_at(theta) -- continuous everywhere PROVIDED the SPIKE-HEIGHT LAW holds for
    every circle (checked separately, see ``_spike_heights``)."""
    comps = [(f, undulation * (0.45 + 0.55 * _hash01(seed, 3 * f)) / f, 2.0 * math.pi * _hash01(seed, 3 * f + 1))
             for f in (2, 3, 5)]
    comps += [(f, ripple * (0.5 + 0.5 * _hash01(seed, 5 * f)), 2.0 * math.pi * _hash01(seed, 5 * f + 1))
              for f in (9, 13, 17)]
    corners = [(2.0 * math.pi * _hash01(seed, 150 + c), corner_strength * (0.55 + 0.45 * _hash01(seed, 160 + c)),
                0.08 + 0.05 * _hash01(seed, 170 + c)) for c in range(max(0, n_corners))]
    r_floor = 0.3 * max(R for _, _, R in circles)

    def radius_at(theta):
        dx, dz = math.cos(theta), math.sin(theta)
        r = 0.0
        for (ox, oz, R) in circles:
            proj = ox * dx + oz * dz
            q2 = ox * ox + oz * oz - proj * proj
            if q2 <= R * R:
                t = proj + math.sqrt(max(0.0, R * R - q2))
                if t > r:
                    r = t
        if r <= 0.0:
            r = r_floor
        for (f, a, p) in comps:
            r *= (1.0 + a * math.sin(f * theta + p))
        for (cth, cs, cw) in corners:
            d = abs(((theta - cth + math.pi) % (2.0 * math.pi)) - math.pi)
            r *= (1.0 - cs * math.exp(-(d / cw) ** 2))
        return r
    return radius_at


def _spike_heights(circles):
    """THE SPIKE-HEIGHT LAW check (module docstring finding 2): for every circle NOT centred at
    the reference point (offset>0), the tangent-edge value it can contribute is
    sqrt(offset^2-R^2) when offset>R (0/undefined when offset<=R, i.e. the reference point is
    INSIDE that circle -- no tangent edge exists, unconditionally safe). Returns
    ``[(offset, R, spike_height_or_0), ...]``."""
    out = []
    for (ox, oz, R) in circles:
        offset = math.hypot(ox, oz)
        spike = math.sqrt(offset * offset - R * R) if offset > R else 0.0
        out.append(dict(offset=round(offset, 2), R=R, spike_height=round(spike, 2)))
    return out


def _smooth_radius_fn(base_fn, *, n=UNION_SMOOTH_N, passes=UNION_SMOOTH_PASSES):
    """FIX 1(b) -- mesh.multi_blob_outline's own post-smooth pass (mesh.py:520-521:
    ``radii[i] = (radii[i-1] + 2*radii[i] + radii[(i+1)%n]) / 4`` over its FIXED n-point
    discretization, repeated ``smooth`` times), re-expressed as a continuous angle-domain
    equivalent so it composes with this module's ADAPTIVE (non-uniform) outline sampling instead
    of only a fixed grid. Each pass wraps the previous function in the identical 3-point moving
    average, evaluated at theta -/+ the discrete step ``dtheta = 2*pi/n`` (n=160, the true verbatim
    resolution -- see the module docstring / UNION_SMOOTH_N's own comment for why 160, not this
    module's own 200-point adaptive base). Composing ``passes`` of these IS the exact discrete
    recursion mesh.py runs (verified: sampled at the 160 grid angles, this continuous port matches
    a direct fixed-array 2-pass moving-average to float precision), just queryable at ANY theta --
    required by ``_adaptive_union_outline``'s bisection, which re-evaluates ``radius_fn`` at
    arbitrary midpoint angles, never interpolates. A finite sum of continuous functions is itself
    continuous, so this cannot reintroduce finding-1's discontinuity trap."""
    dtheta = 2.0 * math.pi / n
    fn = base_fn
    for _ in range(max(0, passes)):
        prev = fn

        def smoothed(theta, _prev=prev, _dt=dtheta):
            return (_prev(theta - _dt) + 2.0 * _prev(theta) + _prev(theta + _dt)) / 4.0

        fn = smoothed
    return fn


def _adaptive_union_outline(radius_fn, cx, cz, n_base, *, max_seg, max_splits=20000):
    """Angularly-uniform seed ring + adaptive bisection (insert the exact angular midpoint,
    re-evaluated through ``radius_fn`` -- never interpolated) until every consecutive world-space
    chord is <= ``max_seg``. Raises if it cannot converge within ``max_splits`` -- module docstring
    finding 1's own discriminator: a genuinely discontinuous radius function (the naive polygon-
    ray-cast trap) never converges here; this design (the analytic circle union) converges in a
    handful of splits, re-verified below, not assumed."""
    thetas = [2.0 * math.pi * i / n_base for i in range(n_base)]

    def ptof(th):
        r = radius_fn(th)
        return (cx + r * math.cos(th), cz + r * math.sin(th)), r

    pts, radii = [], []
    for th in thetas:
        p, r = ptof(th)
        pts.append(p)
        radii.append(r)
    i, n_splits = 0, 0
    while i < len(pts):
        j = (i + 1) % len(pts)
        d = math.hypot(pts[j][0] - pts[i][0], pts[j][1] - pts[i][1])
        if d > max_seg:
            ti = thetas[i]
            tj = thetas[j] if j != 0 else thetas[0] + 2.0 * math.pi
            tm = (ti + tj) / 2.0
            pm, rm = ptof(tm % (2.0 * math.pi))
            ins = j if j != 0 else len(pts)
            pts.insert(ins, pm)
            thetas.insert(ins, tm % (2.0 * math.pi))
            radii.insert(ins, rm)
            n_splits += 1
            if n_splits > max_splits:
                raise RuntimeError(f"adaptive union outline did not converge after {n_splits} splits "
                                   f"-- this is the module docstring's finding-1 discriminator: a "
                                   f"genuinely discontinuous radius function, not a resolution problem")
            continue
        i += 1
    return pts, radii, n_splits


def build_union_outline():
    """The full site geometry pipeline: circles -> spike-height law check -> the shared-wobble
    radius function -> the adaptively-resampled outline. Returns a dict with everything stage0/
    stage1 need to report."""
    circles = [
        (SOUTH_CENTER[0] - REF_CENTER[0], SOUTH_CENTER[1] - REF_CENTER[1], SOUTH_RADIUS),
        (0.0, 0.0, CONNECTOR_RADIUS),
        (NORTH_CENTER[0] - REF_CENTER[0], NORTH_CENTER[1] - REF_CENTER[1], NORTH_RADIUS),
    ]
    spikes = _spike_heights(circles)
    guard = CONNECTOR_RADIUS
    spike_law_ok = all(s["spike_height"] < guard for s in spikes)
    radius_fn_raw = _explicit_circle_union_radius_fn(circles, seed=UNION_WOBBLE_SEED, undulation=UNION_UNDULATION,
                                                      n_corners=UNION_N_CORNERS, corner_strength=UNION_CORNER_STRENGTH)
    # FIX 1(b): apply mesh.multi_blob_outline's own post-smooth pass (previously defined,
    # never applied -- see UNION_SMOOTH_PASSES/_smooth_radius_fn's own docstrings).
    radius_fn = _smooth_radius_fn(radius_fn_raw, n=UNION_SMOOTH_N, passes=UNION_SMOOTH_PASSES)
    outline, radii, n_splits = _adaptive_union_outline(radius_fn, REF_CENTER[0], REF_CENTER[1],
                                                       UNION_N_BASE, max_seg=UNION_MAX_SEG)
    n = len(outline)
    seglens = [math.hypot(outline[(k + 1) % n][0] - outline[k][0], outline[(k + 1) % n][1] - outline[k][1])
              for k in range(n)]
    return dict(circles=circles, spikes=spikes, guard=guard, spike_law_ok=spike_law_ok,
               radius_fn_raw=radius_fn_raw,
               radius_fn=radius_fn, outline=outline, radii=radii, n_splits=n_splits,
               max_seg_realized=round(max(seglens), 3), n_pts=n)


# ================================================================================================
# STAGE 0 -- site gates over the FULL union footprint (mirrors rung_d_layout.stage0_site exactly,
# built on the union outline above instead of a single blob_outline call).
# ================================================================================================
def stage0_site(game_root: Path, union: dict) -> dict:
    log("=" * 100); log("STAGE 0 -- site gates (read-only, the 2-lobe union footprint)"); log("=" * 100)
    log(f"  circles: {union['circles']}")
    log(f"  spike-height law (every non-hub circle's tangent spike < the {union['guard']}u hub guard): "
        f"{union['spikes']} -> {'PASS' if union['spike_law_ok'] else 'FAIL'}")
    log(f"  adaptive union outline: {union['n_pts']} pts ({union['n_splits']} splits from "
        f"{UNION_N_BASE} base samples), realized max chord {union['max_seg_realized']}u "
        f"(target <= {UNION_MAX_SEG}u)")

    def _fake_multi_blob_outline(cx, cz, *, lobes=None, base_radius=None, seed=None, undulation=None):
        assert abs(cx - REF_CENTER[0]) < 1e-6 and abs(cz - REF_CENTER[1]) < 1e-6, \
            f"monkeypatch called with unexpected centre {(cx, cz)} != {REF_CENTER}"
        return union["outline"], union["radii"]

    orig = M.multi_blob_outline
    M.multi_blob_outline = _fake_multi_blob_outline
    try:
        built = ISL.build_landmass(center=REF_CENTER, base_radius=1.0, seed=1.0, lobes=2, n_patches=0,
                                   disc=1, game=game_root)
    finally:
        M.multi_blob_outline = orig

    footprint = sorted(built["blocks"])
    log(f"  union footprint ({len(footprint)} blocks): {footprint}")

    occupied = {blk: occ for blk in footprint
               if (occ := ISL._real_block_parts(blk, disc=1, lod="0_1", game=game_root))}
    ok_ocean = not occupied
    log(f"  OPEN-OCEAN TARGET: {'PASS' if ok_ocean else 'FAIL'} ({occupied if occupied else 'clean'})")

    live_deployed = MBM.enumerate_live_deployed_blocks(game_root)
    overlap = sorted(set(footprint) & set(live_deployed))
    ok_overwrite = not overlap
    log(f"  MOD-OVERWRITE: {'PASS' if ok_overwrite else 'FAIL'} "
        f"(live deployed={len(live_deployed)} blocks; overlap={overlap})")

    ok_grid = all(MBM._block_in_grid(b) for b in footprint)
    log(f"  GRID-BOUNDS: {'PASS' if ok_grid else 'FAIL'}")

    plane = ISL._sea_plane(1, game_root)
    verify = ISL.verify_landmass(built, sea_plane=plane, land_height=3.2)
    log(f"  verify_landmass clean (incl. the shape gate): {verify['clean']}")
    log(f"    shape: {verify['shape']}")
    for k in ("cracks", "down_facing", "walk_filter_fails", "grass_over_8u", "uv_out_of_region",
             "holes", "open_edges", "missing_faces"):
        log(f"    {k}: {verify[k]}")

    return dict(built=built, footprint=footprint, live_deployed=live_deployed,
               gates=dict(spike_law=union["spike_law_ok"], open_ocean=ok_ocean, mod_overwrite=ok_overwrite,
                         grid_bounds=ok_grid, verify_clean=bool(verify["clean"])),
               verify={k: v for k, v in verify.items() if k != "placement"})


# ================================================================================================
# STAGE 1 -- contiguity across y=-1024 (the by15/16 seam) + massif-sector rim fidelity vs the
# proven seed-42 bench.
# ================================================================================================
def _connected_components_world(built: dict):
    """Connected-component census over the FULL built world-frame triangle soup (wall + grass,
    everything in ``built['world']['tris']``) via position-welded edge adjacency -- proves actual
    MESH continuity (not just block-adjacency, which can be satisfied by two islands that merely
    share a block boundary with a sea gap between them)."""
    gpos = built["world"]["pos"]
    gtris = built["world"]["tris"]
    kk = lambda i: (round(gpos[i][0], 3), round(gpos[i][1], 3), round(gpos[i][2], 3))
    edge_tris = defaultdict(list)
    for ti, tri in enumerate(gtris):
        ps = [kk(v) for v in tri]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge_tris[tuple(sorted((ps[a], ps[b])))].append(ti)
    adj = defaultdict(set)
    for ts in edge_tris.values():
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                adj[ts[i]].add(ts[j])
                adj[ts[j]].add(ts[i])
    comps, seen = [], set()
    for s in range(len(gtris)):
        if s in seen:
            continue
        comp = {s}
        st = [s]
        while st:
            t = st.pop()
            for t2 in adj[t]:
                if t2 not in comp:
                    comp.add(t2)
                    st.append(t2)
        seen |= comp
        comps.append(comp)
    comps.sort(key=len, reverse=True)
    return comps


def stage1_contiguity_and_fidelity(built: dict, union: dict) -> dict:
    log("\n" + "=" * 100); log("STAGE 1 -- contiguity across y=-1024 + massif-sector rim fidelity"); log("=" * 100)

    comps = _connected_components_world(built)
    n_comp = len(comps)
    main = comps[0]
    gpos = built["world"]["pos"]
    gtris = built["world"]["tris"]
    zs_main = [gpos[v][2] for ti in main for v in gtris[ti]]
    spans_arm = any(z > -1024.0 for z in zs_main)          # by<=15 (z > -1024)
    spans_pocket = any(z <= -1024.0 for z in zs_main)       # by>=16 (z <= -1024)
    is_one_landmass = (n_comp == 1) and spans_arm and spans_pocket
    log(f"  connected components over the full world soup: {n_comp} (sizes {[len(c) for c in comps[:5]]})")
    log(f"  main component spans z>-1024 (arm side): {spans_arm}; spans z<=-1024 (pocket side): {spans_pocket}")
    log(f"  ONE LANDMASS spanning the by15/16 seam: {'YES' if is_one_landmass else 'NO'}")

    # massif-sector fidelity: for each of the proven bench's OWN 116 outline points (its
    # independent per-lobe wobble, cx=170/cz=-1152/r=72/seed=42), evaluate the FINAL union's
    # shared-wobble radius function at the SAME angle as seen from REF_CENTER and compare distances
    # -- 0 delta where the union is purely south-dominated with no wobble mismatch, positive
    # delta either where the connector/north wobble differs from south's own OR where another
    # circle's contribution wins outright.
    # 0.11/3/0.26 = build_landmass's own hardcoded lobes==1 defaults (island.py:226-228) -- the
    # EXACT params rung_d_layout.stage0_site's own build_landmass(lobes=1, ...) call resolved to
    # for the proven bench (rung_d_layout.py has no override, so these are not typed in blind).
    bench_pts, _ = M.blob_outline(SOUTH_CENTER[0], SOUTH_CENTER[1], base_radius=SOUTH_RADIUS, seed=SOUTH_SEED,
                                  undulation=0.11, n=116, n_corners=3, corner_strength=0.26)
    radius_fn = union["radius_fn"]
    deltas = []
    dominated = []
    circles = union["circles"]
    for (px, pz) in bench_pts:
        theta = math.atan2(pz - REF_CENTER[1], px - REF_CENTER[0])
        r_true = math.hypot(px - REF_CENTER[0], pz - REF_CENTER[1])
        r_union = radius_fn(theta)
        deltas.append(abs(r_union - r_true))
        # is south the RAW (pre-wobble) winner at this angle? (an objective "massif sector" test)
        dx, dz = math.cos(theta), math.sin(theta)
        raws = []
        for (ox, oz, R) in circles:
            proj = ox * dx + oz * dz
            q2 = ox * ox + oz * oz - proj * proj
            raws.append(proj + math.sqrt(max(0.0, R * R - q2)) if q2 <= R * R else -1e9)
        dominated.append(raws[0] >= max(raws[1:]))
    deltas_sector = [d for d, dom in zip(deltas, dominated) if dom]
    n_sector = len(deltas_sector)
    n_total = len(deltas)
    if deltas_sector:
        ds = sorted(deltas_sector)
        d_min, d_max = ds[0], ds[-1]
        d_mean = sum(ds) / len(ds)
        d_median = ds[len(ds) // 2]
    else:
        d_min = d_max = d_mean = d_median = None
    log(f"  massif-sector fidelity: {n_sector}/{n_total} bench rim points fall in the RAW south-"
        f"dominated sector; per-point |union_r - bench_r| at matching angle: "
        f"min={d_min} mean={d_mean} median={d_median} max={d_max} (u)")
    log(f"  (all {n_total} bench points, sector or not): "
        f"min={min(deltas):.3f} mean={sum(deltas)/len(deltas):.3f} max={max(deltas):.3f} (u)")

    return dict(n_components=n_comp, component_sizes=[len(c) for c in comps[:5]],
               spans_arm=spans_arm, spans_pocket=spans_pocket, is_one_landmass=is_one_landmass,
               fidelity=dict(n_sector=n_sector, n_total=n_total,
                            sector_delta_min=d_min, sector_delta_mean=d_mean,
                            sector_delta_median=d_median, sector_delta_max=d_max,
                            all_delta_min=round(min(deltas), 3), all_delta_mean=round(sum(deltas) / len(deltas), 3),
                            all_delta_max=round(max(deltas), 3)))


# ================================================================================================
# STAGE 2 -- the massif anchor (horseshoe donor, UNCHANGED near=) -- reproduction vs the proven
# 2026-07-15 deploy's own recorded numbers (rung_d_layout.stage1_anchor's own repro dict, reused).
# ================================================================================================
def stage2_massif_anchor(built: dict, game_root: Path) -> dict:
    log("\n" + "=" * 100); log("STAGE 2 -- MASSIF ANCHOR (interior.carve_mountain, donor=horseshoe "
                              "(5-6,15-16), near=SOUTH_NEAR unchanged from Rung D)"); log("=" * 100)
    soup = IN.soup_from_blocks(built["blocks"])
    rim_capture = {}
    res = IN.carve_mountain(soup, near=SOUTH_NEAR, donor=HORSESHOE_DONOR, ground="grass", disc=1,
                            game=game_root, log=MBM._capturing_log(rim_capture, log))
    IN.census_gate(res["changed"], disc=1, game=game_root, log=log)
    r_rim = rim_capture.get("r_rim")
    if r_rim is None:
        raise ValueError("could not capture the massif's own rim radius from carve_mountain's log")
    clear_radius = r_rim + IN.MTN_GBLEND + RDL.ANCHOR_CLEAR_MARGIN
    log(f"  realized centre {res['center']} rot {res['rot']*90}deg, r_rim {r_rim:.1f}u, "
        f"clear_radius {clear_radius:.2f}u, blocks {sorted(res['changed'])}")

    rep = res["report"]
    repro = dict(
        blob_tris=(rep["blob_tris"], REPRO_BENCH["blob_tris"]),
        ensemble_tris=(rep["ensemble_tris"], REPRO_BENCH["ensemble_tris"]),
        rock_rigid_pct=(round(rep["rock_rigid"] * 100, 2), REPRO_BENCH["rock_rigid_pct"]),
        apron_slope=(rep["apron_slope"], REPRO_BENCH["apron_slope"]),
        zip_rise=(rep["zip_rise"], REPRO_BENCH["zip_rise"]),
        r_rim=(round(r_rim, 1), REPRO_BENCH["r_rim"]),
        n_span_blocks=(len(res["changed"]), REPRO_BENCH["n_span_blocks"]))
    repro_ok = all(abs(a - b) < 0.5 for a, b in repro.values() if isinstance(a, (int, float)))
    log(f"  reproduction vs the proven 2026-07-15 deploy's own recorded numbers: {repro} -> "
        f"{'MATCHES' if repro_ok else 'DIVERGES'}")

    blocks_now = dict(built["blocks"])
    for blk, bm in res["changed"].items():
        blocks_now[blk] = bm
    return dict(res=res, r_rim=r_rim, clear_radius=clear_radius, center=tuple(res["center"]),
               blocks_now=blocks_now, span_blocks=list(res["changed"]),
               reproduction=dict(repro_ok=repro_ok, values=repro))


# ================================================================================================
# STAGE 2b -- the north anchor (Uaho donor, arm) -- gates + realized clearance, compared
# informationally against the known Uaho constants (mixed_biome_mint.py's own Rung C figures).
# ================================================================================================
def stage2b_north_anchor(blocks_now: dict, game_root: Path) -> dict:
    log("\n" + "=" * 100); log("STAGE 2b -- NORTH ANCHOR (interior.carve_mountain, donor=Uaho (0,0), "
                              "near=NORTH_NEAR -- this session's own block-centre scan)"); log("=" * 100)
    soup = IN.soup_from_blocks(blocks_now)
    rim_capture = {}
    res = IN.carve_mountain(soup, near=NORTH_NEAR, donor=UAHO_DONOR, ground="grass", disc=1,
                            game=game_root, log=MBM._capturing_log(rim_capture, log))
    IN.census_gate(res["changed"], disc=1, game=game_root, log=log)
    r_rim = rim_capture.get("r_rim")
    if r_rim is None:
        raise ValueError("could not capture the arm anchor's own rim radius")
    clear_radius = r_rim + IN.MTN_GBLEND + RDL.ANCHOR_CLEAR_MARGIN
    log(f"  realized centre {res['center']} rot {res['rot']*90}deg, r_rim {r_rim:.1f}u, "
        f"clear_radius {clear_radius:.2f}u, blocks {sorted(res['changed'])}")
    vs_known = dict(r_rim=(round(r_rim, 1), UAHO_KNOWN["r_rim"]),
                    clear_radius=(round(clear_radius, 2), UAHO_KNOWN["clear_radius"]))
    log(f"  vs the known Uaho constants (mixed_biome_mint.py Rung C, a DIFFERENT site -- "
        f"informational only, not a reproduction requirement): {vs_known}")

    blocks_now2 = dict(blocks_now)
    for blk, bm in res["changed"].items():
        blocks_now2[blk] = bm
    return dict(res=res, r_rim=r_rim, clear_radius=clear_radius, center=tuple(res["center"]),
               blocks_now=blocks_now2, span_blocks=list(res["changed"]), vs_known=vs_known)


def _standoff_aware_line(term_a, term_b, dist_to_coast, *, base_seed=None, n_candidates=LINE_N_CANDIDATES):
    """FIX 1(c) (skeptic findings 1/2/5): ``generate_partition_line``'s own retry loop (up to 600
    tries) only ever optimizes shape-language fit (straightness/mean-turn) -- it has zero awareness
    of, and zero retry-on-failure for, real coastal proximity, and the prior pass tried exactly ONE
    line seed this whole session. Generate ``n_candidates`` independent seeded lines, score each by
    its REAL minimum distance to the coastline (``dist_to_coast``, never the 5-point chord proxy),
    and keep the candidate with the BEST real standoff among those that still satisfy the
    straightness/turn targets (``matched=True``) -- falling back to the single best shape-scoring
    candidate, matching ``generate_partition_line``'s own single-seed fallback, only if none of the
    ``n_candidates`` seeds matched. Deterministic: seeds are ``f"{base_seed}:{i}"`` for
    ``i in range(n_candidates)``, never wall-clock/random."""
    base_seed = base_seed if base_seed is not None else LINE_SEED
    candidates = []
    for i in range(n_candidates):
        seed_i = f"{base_seed}:{i}"
        cand = MBM.generate_partition_line(term_a, term_b, seed=seed_i,
                                           target_straightness=TARGET_STRAIGHTNESS, target_turn=TARGET_TURN)
        real_min = min(dist_to_coast(x, z) for (x, z) in cand["points"])
        candidates.append(dict(seed=seed_i, matched=bool(cand.get("matched")), real_standoff_min=real_min,
                               straightness=cand["straightness"], mean_turn=cand["mean_turn"], line=cand))
    matched = [c for c in candidates if c["matched"]]
    pool = matched if matched else candidates
    best = max(pool, key=lambda c: c["real_standoff_min"])
    log(f"  FIX 1(c) standoff-aware line selection: {len(candidates)} seeded candidates "
       f"({len(matched)} shape-matched); real standoff (min-dist-to-coast) per candidate: "
       f"{[(c['seed'].rsplit(':',1)[-1], round(c['real_standoff_min'],2)) for c in candidates]}; "
       f"chosen seed={best['seed']} real_min={best['real_standoff_min']:.2f}u "
       f"(matched={best['matched']}, from {'the matched pool' if matched else 'the unmatched fallback pool'})")
    return dict(chosen=best, candidates=[dict(seed=c["seed"], matched=c["matched"],
                                              real_standoff_min=round(c["real_standoff_min"], 2))
                                         for c in candidates])


# ================================================================================================
# STAGE 3 -- termini selection ACROSS the two anchors' own rims (unlike Rung D's single-rim chord
# search, this rung's two termini live on TWO DIFFERENT rock components) + the partition line +
# sector retile (mixed_biome_mint's own generators, unchanged; anchors_realized=[] per Rung D's
# own fix -- the massif IS the terminus, not a clearance obstacle to protect FROM).
# ================================================================================================
def stage3_termini_line_and_retile(blocks_now2: dict, footprint, coast_edges, span_s, span_n) -> dict:
    log("\n" + "=" * 100); log("STAGE 3 -- cross-anchor termini + partition line + sector retile"); log("=" * 100)
    rim_s, n_rock_s, comps_s = RDL._rock_rim_ring(blocks_now2, span_s)
    rim_n, n_rock_n, comps_n = RDL._rock_rim_ring(blocks_now2, span_n)
    log(f"  south (massif) rim: {len(rim_s)} pts over {n_rock_s} rock tris (components {comps_s})")
    log(f"  north (Uaho) rim: {len(rim_n)} pts over {n_rock_n} rock tris (components {comps_n})")

    dist_to_coast = RDL._dist_to_coast_fn(coast_edges)
    best = None
    for pa in rim_s:
        for pb in rim_n:
            samples = [(pa[0] + t * (pb[0] - pa[0]), pa[2] + t * (pb[2] - pa[2])) for t in (0.0, 0.25, 0.5, 0.75, 1.0)]
            worst = min(dist_to_coast(sx, sz) for sx, sz in samples)
            if best is None or worst > best[0]:
                d = math.hypot(pa[0] - pb[0], pa[2] - pb[2])
                best = (worst, pa, pb, d)
    worst_chord_clearance, term_a3, term_b3, chord = best
    term_a = (term_a3[0], term_a3[2])
    term_b = (term_b3[0], term_b3[2])
    log(f"  best cross-anchor termini (exhaustive over {len(rim_s)}x{len(rim_n)} pairs): "
        f"A(south)={term_a} B(north)={term_b}, chord {chord:.1f}u, worst sampled chord-to-coast "
        f"clearance {worst_chord_clearance:.2f}u")

    line_sel = _standoff_aware_line(term_a, term_b, dist_to_coast, base_seed=LINE_SEED)
    line = line_sel["chosen"]["line"]
    log(f"  line (FIX 1(c)-chosen): {line['n_segments']} segments, length {line['length']:.1f}u, "
        f"straightness {line['straightness']:.4f} (target {TARGET_STRAIGHTNESS}), "
        f"mean_turn {line['mean_turn']:.1f}deg (target {TARGET_TURN}), matched={line.get('matched')}, "
        f"real_standoff_min={line_sel['chosen']['real_standoff_min']:.2f}u")

    return dict(rim_s=rim_s, rim_n=rim_n, term_a=term_a, term_b=term_b, chord=chord,
               worst_chord_clearance=worst_chord_clearance, line=line, line_selection=line_sel)


def _finish_retile(blocks_now2, line, massif_center):
    desert_side = MBM.classify_side(massif_center[0], massif_center[1], line["points"])[1]
    log(f"  desert_side resolved to {desert_side} (the side the massif centre sits on)")
    blocks_retiled, retile_touched, retile_stats = MBM.sector_retile(
        blocks_now2, line["points"], [], depth_cap=DEPTH_CAP, desert_side=desert_side)
    log(f"  sector retile: {retile_stats['n_retiled']} desert-body tri(s) across "
        f"{len(retile_touched)} block(s) of {retile_stats['n_main_tris_scanned']} plain-mains tris "
        f"scanned (excluded: anchor-clear {retile_stats['n_excluded_anchor_clear']} [forced 0 by "
        f"design, per Rung D's own fix], wrong-side {retile_stats['n_excluded_wrong_side']}, "
        f"depth {retile_stats['n_excluded_depth']})")
    return dict(desert_side=desert_side, blocks_retiled=blocks_retiled, retile_touched=retile_touched,
               retile_stats=retile_stats)


def _rock_points(blocks: dict):
    """(x,z) world points of every rock-topo (``interior.MOUNTAIN_ROCK_TOPOS``) tri vertex across
    ``blocks`` -- the single shared rock-point set both FIX 2's dressing-time exclusion and GATE3's
    post-hoc contamination check measure distance to (so a "clean" GATE3 result after FIX 2 is a
    genuine consequence of the same measurement, not two subtly-different rock definitions agreeing
    by coincidence)."""
    rock_pts = []
    for blk, bm in blocks.items():
        ox, oz = X.block_world_origin(*blk)
        for tri in bm.tris:
            idall = int(round(bm.tangents[tri[0]][0]))
            if X.decode_id(idall)["topograph"] not in IN.MOUNTAIN_ROCK_TOPOS:
                continue
            for j in tri:
                rock_pts.append((bm.verts[j][0] + ox, bm.verts[j][2] + oz))
    return rock_pts


def _dist_to_rock_fn(rock_pts):
    def _dist(px, pz):
        return min((math.hypot(px - rx, pz - rz) for (rx, rz) in rock_pts), default=1e18)
    return _dist


def _termination_decal_exclusion(eligible: dict, dist_to_rock, clear_u: float) -> tuple:
    """FIX 2 (skeptic finding 3 + its prescribed fix): demote any straddle/fringe CELL whose write
    centroid lands within ``clear_u`` of ANY rock tri back to plain desert mains, applied at the
    DRESSING step's own eligibility filter (never at retile -- ``sector_retile``'s own
    ``anchors_realized=[]`` stays untouched, Rung D's own fix: the massif/Uaho anchors are
    terminuses, not clearance obstacles).

    A cell's exclusion test is the MIN over each of its own ``core_cell_records`` (one record per
    TRI that ``resolve_plan_writes`` will later emit as its own separate write -- a straddle cell
    holds two records, one grass one desert), each record's own centroid measured EXACTLY the way
    GATE3 measures a write's centroid (mean of its 3 ``world_pts``, the same vertex set --
    ``tri_idx``/``world_pts`` both derive from the identical ``bm.tris``/``bm.verts`` this build's
    own ``blocks_retiled`` holds). A first attempt averaged ALL of a cell's records into ONE
    centroid before measuring -- for a straddle cell that AVERAGES the far (grass-side) tri with the
    near (desert-side, rock-adjacent) tri, diluting a genuinely-contaminating desert tri's own
    distance below the clear radius while GATE3 still measures that tri on its own and correctly
    flags it: 3 residual GATE3 contaminations were caught and traced to exactly this averaging
    mismatch (session note, not a re-derivation) -- MIN-over-records fixes it, since excluding the
    cell whenever ANY of its own future per-tri writes would land inside the clear radius is the
    only filter that can guarantee GATE3 reads 0 afterward, matching GATE3's own per-write
    granularity exactly rather than approximating it. Returns ``(filtered_eligible,
    excluded_report)``."""
    core_cell_records = eligible["core_cell_records"]

    def _record_centroid(r):
        pts = r["world_pts"]
        return (sum(p[0] for p in pts) / len(pts), sum(p[2] for p in pts) / len(pts))

    def _cell_min_dist(cell):
        recs = core_cell_records.get(cell, [])
        if not recs:
            return None
        return min(dist_to_rock(*_record_centroid(r)) for r in recs)

    excluded = []

    def _filter(cells):
        kept = []
        for c in cells:
            d = _cell_min_dist(c)
            if d is None:
                d = 1e18
            if d < clear_u:
                excluded.append(dict(cell=list(c), dist_to_rock=round(d, 2)))
            else:
                kept.append(c)
        return kept

    filtered = dict(eligible)
    filtered["straddle_eligible"] = _filter(eligible["straddle_eligible"])
    filtered["fringe_eligible"] = {fam: _filter(cells) for fam, cells in eligible["fringe_eligible"].items()}
    return filtered, excluded


# ================================================================================================
# STAGE 4 -- dressing PROJECTION (gd_seam_dress via mixed_biome_mint.build_dressing's own
# machinery -- FIND_ELIGIBLE / ASSIGN_DRESSING / RESOLVE_PLAN_WRITES / COMPUTE_DRESS all reused
# UNCHANGED; the only new code is FIX 2's own eligibility PRE-FILTER (``_termination_decal_
# exclusion``, above), spliced in exactly where ``build_dressing`` calls ``find_eligible_inmemory``
# -- so this function is build_dressing's own body with one filtering step inserted, not a
# reimplementation of the byte-transform itself. Entries AND tri-writes both reported (the Rung D
# unit-mismatch lesson: never compare plan-entries to a tri-count).
# ================================================================================================
def stage4_dressing(blocks_retiled: dict, footprint, retile_touched, game_root: Path) -> dict:
    log("\n" + "=" * 100); log("STAGE 4 -- dressing PROJECTION (gd_seam_dress via mixed_biome_mint "
                              "machinery + FIX 2's termination-decal eligibility pre-filter)"); log("=" * 100)
    null = SNR.part_b()
    dress_core = retile_touched if retile_touched else footprint
    rock_pts = _rock_points(blocks_retiled)
    dist_to_rock = _dist_to_rock_fn(rock_pts)

    eligible_raw = MBM.find_eligible_inmemory(dress_core, blocks_retiled, game_root)
    eligible, excluded = _termination_decal_exclusion(eligible_raw, dist_to_rock, TERMINATION_DECAL_CLEAR_U)
    log(f"  FIX 2 termination-decal exclusion ({len(rock_pts)} rock pts, clear radius "
       f"{TERMINATION_DECAL_CLEAR_U}u): {len(eligible_raw['straddle_eligible'])} -> "
       f"{len(eligible['straddle_eligible'])} straddle-eligible, "
       f"{ {k: len(v) for k, v in eligible_raw['fringe_eligible'].items()} } -> "
       f"{ {k: len(v) for k, v in eligible['fringe_eligible'].items()} } fringe-eligible; "
       f"{len(excluded)} cell(s) demoted to plain desert mains{(' -- ' + str(excluded)) if excluded else ''}")

    plan = MBM.GD.assign_dressing(eligible, DRESS_SEED, null)
    writes = MBM.GD.resolve_plan_writes(eligible, plan)
    new_blocks = dict(blocks_retiled)
    per_block_copy = {}
    footprint_bytes = 0
    origins = {blk: X.block_world_origin(*blk) for blk in dress_core}
    for w in writes:
        blk = tuple(w["block"])
        cell = tuple(w["cell"])
        if blk not in per_block_copy:
            per_block_copy[blk] = copy.deepcopy(blocks_retiled[blk])
        src_bm = eligible["core_bms"][blk]
        ox, oz = origins[blk]
        new_uv, new_idall = MBM.GD.compute_dress(src_bm, ox, oz, cell, w["tri_idx"], w["fam"], w["row"], w["ori"])
        w["new_uv"], w["new_idall"] = new_uv, new_idall
        nb = per_block_copy[blk]
        for k, j in enumerate(w["tri_idx"]):
            changed_idall = new_idall[k] != w["old_idall"][k]
            footprint_bytes += 8 + (4 if changed_idall else 0)
            nb.uvs[j] = new_uv[k]
            if changed_idall:
                old_tan = nb.tangents[j]
                nb.tangents[j] = [float(new_idall[k])] + list(old_tan[1:])
    for blk, nb in per_block_copy.items():
        new_blocks[blk] = nb
    touched = sorted(per_block_copy)
    dress = dict(eligible=eligible, plan=plan, writes=writes, new_blocks=new_blocks, touched=touched,
               footprint_bytes=footprint_bytes,
               termination_exclusion=dict(clear_radius_u=TERMINATION_DECAL_CLEAR_U,
                                          n_excluded_cells=len(excluded), excluded=excluded))
    log(f"  dressing: {len(dress['eligible']['straddle_eligible'])} straddle-eligible + "
       f"{sum(len(v) for v in dress['eligible']['fringe_eligible'].values())} fringe-eligible cells "
       f"(post-FIX-2); {len(dress['plan'])} planned entries, {len(dress['writes'])} tri-writes, "
       f"{dress['footprint_bytes']}B footprint across {len(dress['touched'])} block(s)")
    return dict(dress=dress, dress_core=dress_core, null=null, rock_pts=rock_pts)


# ================================================================================================
# STAGE 5 -- THE 4 COMPOSITION GATES, as PRE-BUILD projections. NOTE (verified this session,
# grep-confirmed against rung_d_build.py:289-391): only coast-standoff and dressing-ratio are
# COMPUTED with an explicit pass/fail verdict anywhere in the prior art (rung_d_layout.py's
# ``meets_64u_target`` / rung_d_build.py's ``stage_ratio_corrected.in_band_local_writes_units`` --
# both informational, never summed into either script's own n_fail). Termination-decal and
# macro-silhouette do NOT exist as checks anywhere in this study's code (GROUND-FAMILY-DECODE-
# 2026-07-19.md:2169-2174, Rung D's own postmortem, names both as "specified but does not yet
# build") -- gates 3+4 below are NEW code authored for this rung, clearly marked as such.
# ================================================================================================
def stage5_composition_gates(coast_edges, blocks_retiled: dict, footprint, line: dict,
                             retile_stats: dict, dress: dict, s2: dict, s2b: dict) -> dict:
    log("\n" + "=" * 100); log("STAGE 5 -- THE 4 COMPOSITION GATES"); log("=" * 100)
    dist_to_coast = RDL._dist_to_coast_fn(coast_edges)

    # ---- GATE 1: coast standoff (rung_d_layout.stage5_coast_standoff's own method, reused) -----
    line_min = min(dist_to_coast(x, z) for (x, z) in line["points"])
    body_dists = []
    for blk in footprint:
        bm = blocks_retiled[blk]
        ox, oz = X.block_world_origin(*blk)
        for tri in bm.tris:
            idall = int(round(bm.tangents[tri[0]][0]))
            if X.decode_id(idall)["topograph"] != 16:
                continue
            cx = sum(bm.verts[j][0] for j in tri) / 3.0 + ox
            cz = sum(bm.verts[j][2] for j in tri) / 3.0 + oz
            body_dists.append(dist_to_coast(cx, cz))
    body_min = min(body_dists) if body_dists else None
    gate1_meets_target = line_min >= COAST_STANDOFF_TARGET
    gate1_meets_floor = line_min >= COAST_STANDOFF_CONTRACT_WORST
    log(f"  GATE 1 (coast-standoff, method: rung_d_layout.stage5_coast_standoff, reused): "
       f"line_min={line_min:.2f}u, body_min={body_min:.2f}u -- "
       f"meets 64u target: {gate1_meets_target}; meets 39.95u contract floor: {gate1_meets_floor}")

    # ---- GATE 2: dressing ratio vs the stock band (rung_d_build.stage_ratio_corrected's own -----
    #      live-re-read comparators, reused UNCHANGED) --------------------------------------------
    n_body = retile_stats["n_retiled"]
    n_planned = len(dress["plan"])
    n_writes = len(dress["writes"])
    ratio_writes = n_writes / n_body if n_body else None
    ratio_planned = n_planned / n_body if n_body else None
    render_json_path = HERE / "out" / "mixed_biome_mint" / "renders" / "mixed_eye_review.json"
    render = json.loads(render_json_path.read_text(encoding="utf-8"))
    local_desert = render["stock_ab_fam_counts"]["desert"]
    local_strip = render["stock_ab_fam_counts"]["strip"]
    local_stock_ratio = local_strip / local_desert
    local_band_max = local_stock_ratio * 1.25
    gate2_in_band = ratio_writes is not None and ratio_writes <= local_band_max
    rc_json = json.loads((HERE / "out" / "mixed_biome_mint.json").read_text(encoding="utf-8"))
    rc_ratio_writes = rc_json["dressing"]["n_writes"] / rc_json["sector_retile"]["n_retiled"]
    rd_json = json.loads((HERE / "out" / "rung_d" / "rung_d_build.json").read_text(encoding="utf-8"))
    rd_ratio_writes = rd_json["ratio_corrected"]["ratio_writes"]
    log(f"  GATE 2 (dressing-ratio, method: rung_d_build.stage_ratio_corrected, reused): "
       f"n_body={n_body} n_planned={n_planned} n_writes={n_writes} -> "
       f"writes:body={ratio_writes:.4f} vs local stock band max {local_band_max:.4f} "
       f"(local_stock_ratio={local_stock_ratio:.4f}) -> {'IN-BAND' if gate2_in_band else 'OUT OF BAND'}; "
       f"vs Rung C's own {rc_ratio_writes:.4f} and Rung D's own {rd_ratio_writes:.4f} writes:body")

    # ---- GATE 3 (NEW this session): termination-decal contamination -----------------------------
    #      the contract's own termination law: EVERY real stock line-termination measures
    #      nearest_topo49_dist 4.27-7.64u with a PLAIN mains tri touching rock (no decal) --
    #      out/contract_gd_composition.json "termination" array, per_radius["10"], re-read live.
    contract = json.loads((HERE / "out" / "contract_gd_composition.json").read_text(encoding="utf-8"))
    real_term_dists = [e["per_radius"]["10"]["nearest_topo49_dist"] for e in contract["termination"]
                       if e["per_radius"]["10"].get("nearest_topo49_dist") is not None]
    log(f"  GATE 3 (termination-decal contamination, NEW -- not present in rung_d_build.py or "
       f"anywhere else in this study; contract's own real-termination nearest-topo49 distances "
       f"(re-read live): {real_term_dists} -> contamination clear radius = {TERMINATION_DECAL_CLEAR_U}u; "
       f"FIX 2 already pre-filtered these writes at the dressing-eligibility step -- this is the "
       f"POST-FIX verification pass, using the SAME rock-point set FIX 2 filtered against "
       f"(``_rock_points``/``_dist_to_rock_fn``, shared not re-derived, so a clean result here is a "
       f"genuine consequence of FIX 2, not two different rock definitions agreeing by coincidence)")
    dist_to_rock = _dist_to_rock_fn(_rock_points(blocks_retiled))
    south_c, north_c = s2["center"], s2b["center"]
    contaminating = []
    for w in dress["writes"]:
        blk = tuple(w["block"])
        bm = blocks_retiled[blk]
        ox, oz = X.block_world_origin(*blk)
        tri_idx = w["tri_idx"]
        cx = sum(bm.verts[j][0] for j in tri_idx) / len(tri_idx) + ox
        cz = sum(bm.verts[j][2] for j in tri_idx) / len(tri_idx) + oz
        d = dist_to_rock(cx, cz)
        if d < TERMINATION_DECAL_CLEAR_U:
            d_south = math.hypot(cx - south_c[0], cz - south_c[1])
            d_north = math.hypot(cx - north_c[0], cz - north_c[1])
            anchor = "south_massif" if d_south <= d_north else "north_uaho"
            contaminating.append(dict(block=list(blk), cell=list(w["cell"]), dist_to_rock=round(d, 2),
                                      anchor=anchor))
    gate3_clean = len(contaminating) == 0
    # PROCESS FIX (skeptic finding 3): report the FULL breakdown over every contaminating write
    # (Counter, not an eyeballed sample[:N] -- a truncated-sample eyeball read is exactly what
    # produced the report's own inverted "concentrates near Uaho" claim last session, when the
    # true split was 60.2% south / 39.8% north).
    anchor_breakdown = dict(Counter(c["anchor"] for c in contaminating))
    block_breakdown = dict(Counter(tuple(c["block"]) for c in contaminating))
    block_breakdown = {str(k): v for k, v in block_breakdown.items()}
    log(f"  GATE 3 result: {len(contaminating)} dressing tri-write(s) within {TERMINATION_DECAL_CLEAR_U}u "
       f"of ANY rock tri (topo in {sorted(IN.MOUNTAIN_ROCK_TOPOS)}) -> "
       f"{'CLEAN' if gate3_clean else 'CONTAMINATED'}"
       + (f" -- FULL anchor breakdown (Counter over all {len(contaminating)}, not a sample): "
          f"{anchor_breakdown}; by block: {block_breakdown}" if contaminating else ""))

    # ---- GATE 4 (NEW this session, repurposing verify_landmass's OWN shape gate as the macro- --
    #      silhouette check -- island.py's outline_shape_stats, already computed in stage0; no
    #      separate macro-silhouette metric exists anywhere in this study's code, per the module
    #      docstring note above; this gate simply ELEVATES that existing sub-result to a top-level
    #      composition-gate verdict, as the task's 4-gate framing requires. Not recomputed here
    #      (avoids a second live geometry pass) -- see stage0_site_gates.verify.shape in the JSON.
    log("  GATE 4 (macro-silhouette, NEW framing of an EXISTING check -- island.py's own "
       "outline_shape_stats/verify_landmass shape gate, already run in stage0; reported here by "
       "reference, not recomputed, to avoid a second live geometry pass) -- see stage0_site_gates."
       "verify.shape in the JSON for the actual numbers/verdict")

    return dict(
        gate1_coast_standoff=dict(line_min_dist_to_coast=round(line_min, 2),
                                  body_min_dist_to_coast=(round(body_min, 2) if body_min is not None else None),
                                  meets_64u_target=gate1_meets_target, meets_39_95u_floor=gate1_meets_floor),
        gate2_dressing_ratio=dict(n_body=n_body, n_planned=n_planned, n_writes=n_writes,
                                  ratio_writes=round(ratio_writes, 4) if ratio_writes else None,
                                  ratio_planned=round(ratio_planned, 4) if ratio_planned else None,
                                  local_stock_ratio=round(local_stock_ratio, 4),
                                  local_band_max=round(local_band_max, 4), in_band=gate2_in_band,
                                  rung_c_ratio_writes=round(rc_ratio_writes, 4),
                                  rung_d_ratio_writes=rd_ratio_writes),
        gate3_termination_decal=dict(clear_radius_u=TERMINATION_DECAL_CLEAR_U,
                                     contract_real_termini_nearest_topo49=real_term_dists,
                                     n_contaminating_writes=len(contaminating), clean=gate3_clean,
                                     anchor_breakdown=anchor_breakdown, block_breakdown=block_breakdown,
                                     all_contaminating=contaminating,
                                     dressing_termination_exclusion=dress.get("termination_exclusion"),
                                     note="NEW check, authored this session (post-FIX-2 verification pass; "
                                     "FIX 2 -- a dressing-eligibility pre-filter -- already excludes these "
                                     "cells before writes exist, so this should read CLEAN by construction "
                                     "unless FIX 2's own filter has a bug); does not exist in "
                                     "rung_d_build.py or elsewhere in this study; the anchor/block "
                                     "breakdown is the FULL Counter over every contaminating write, per "
                                     "the process fix -- never a truncated sample"),
        gate4_macro_silhouette=dict(note="repurposes island.verify_landmass's own outline_shape_stats "
                                    "shape gate (stage0_site_gates.verify.shape in this report) as the "
                                    "macro-silhouette verdict -- no independent macro-silhouette metric "
                                    "exists anywhere in this study's code; NEW framing, not new geometry"),
    )


# ================================================================================================
# main
# ================================================================================================
def main():
    game_root = Path(_cfg.find_game_path(None))
    report = {"site": dict(south_center=list(SOUTH_CENTER), south_radius=SOUTH_RADIUS,
                          ref_center=list(REF_CENTER), connector_radius=CONNECTOR_RADIUS,
                          north_center=list(NORTH_CENTER), north_radius=NORTH_RADIUS,
                          horseshoe_donor=HORSESHOE_DONOR, uaho_donor=list(UAHO_DONOR),
                          union_wobble=dict(seed=UNION_WOBBLE_SEED, undulation=UNION_UNDULATION,
                                           n_corners=UNION_N_CORNERS, corner_strength=UNION_CORNER_STRENGTH))}

    union = build_union_outline()
    s0 = stage0_site(game_root, union)
    report["stage0_site"] = dict(footprint=[list(b) for b in s0["footprint"]], gates=s0["gates"],
                                 verify=s0["verify"],
                                 union=dict(spikes=union["spikes"], guard=union["guard"],
                                          spike_law_ok=union["spike_law_ok"], n_splits=union["n_splits"],
                                          n_pts=union["n_pts"], max_seg_realized=union["max_seg_realized"]))
    site_gates_ok = all(s0["gates"].values())

    coast_edges = RDL.build_coastline(s0["built"])

    s1 = stage1_contiguity_and_fidelity(s0["built"], union)
    report["stage1_contiguity_fidelity"] = dict(
        n_components=s1["n_components"], component_sizes=s1["component_sizes"],
        spans_arm=s1["spans_arm"], spans_pocket=s1["spans_pocket"],
        is_one_landmass=s1["is_one_landmass"], fidelity=s1["fidelity"])

    s2 = stage2_massif_anchor(s0["built"], game_root)
    report["stage2_massif_anchor"] = dict(
        realized_center=list(s2["center"]), r_rim=round(s2["r_rim"], 2),
        clear_radius=round(s2["clear_radius"], 2), rot_deg=s2["res"]["rot"] * 90,
        changed_blocks=[list(b) for b in s2["res"]["changed"]],
        report=s2["res"]["report"], reproduction=s2["reproduction"])

    s2b = stage2b_north_anchor(s2["blocks_now"], game_root)
    report["stage2b_north_anchor"] = dict(
        realized_center=list(s2b["center"]), r_rim=round(s2b["r_rim"], 2),
        clear_radius=round(s2b["clear_radius"], 2), rot_deg=s2b["res"]["rot"] * 90,
        changed_blocks=[list(b) for b in s2b["res"]["changed"]],
        report=s2b["res"]["report"], vs_known_uaho=s2b["vs_known"])

    s3 = stage3_termini_line_and_retile(s2b["blocks_now"], s0["footprint"], coast_edges,
                                        s2["span_blocks"], s2b["span_blocks"])
    s3r = _finish_retile(s2b["blocks_now"], s3["line"], s2["center"])
    report["stage3_termini_line_retile"] = dict(
        term_a=list(s3["term_a"]), term_b=list(s3["term_b"]), chord=round(s3["chord"], 2),
        worst_chord_clearance=round(s3["worst_chord_clearance"], 2),
        line={k: v for k, v in s3["line"].items() if k != "points"},
        line_selection=dict(chosen_seed=s3["line_selection"]["chosen"]["seed"],
                            chosen_real_standoff_min=round(s3["line_selection"]["chosen"]["real_standoff_min"], 2),
                            n_candidates=len(s3["line_selection"]["candidates"]),
                            n_matched=sum(1 for c in s3["line_selection"]["candidates"] if c["matched"]),
                            candidates=s3["line_selection"]["candidates"]),
        desert_side=s3r["desert_side"], retile_stats=s3r["retile_stats"],
        retile_touched=[list(b) for b in s3r["retile_touched"]])

    s4 = stage4_dressing(s3r["blocks_retiled"], s0["footprint"], s3r["retile_touched"], game_root)
    report["stage4_dressing"] = dict(
        n_straddle_eligible=len(s4["dress"]["eligible"]["straddle_eligible"]),
        n_fringe_eligible={k: len(v) for k, v in s4["dress"]["eligible"]["fringe_eligible"].items()},
        n_planned=len(s4["dress"]["plan"]), n_writes=len(s4["dress"]["writes"]),
        footprint_bytes=s4["dress"]["footprint_bytes"],
        touched_blocks=[list(b) for b in s4["dress"]["touched"]],
        termination_exclusion=s4["dress"]["termination_exclusion"])

    s5 = stage5_composition_gates(coast_edges, s3r["blocks_retiled"], s0["footprint"], s3["line"],
                                  s3r["retile_stats"], s4["dress"], s2, s2b)
    report["stage5_composition_gates"] = s5

    body_tris = s3r["retile_stats"]["n_retiled"]
    ratio_writes = s5["gate2_dressing_ratio"]["ratio_writes"]
    fails = []
    if not site_gates_ok:
        fails.append(f"stage0 site gates: {s0['gates']}")
    if not s1["is_one_landmass"]:
        fails.append("stage1: NOT one contiguous landmass across y=-1024")
    if not s2["reproduction"]["repro_ok"]:
        fails.append(f"stage2: massif reproduction DIVERGES from the proven bench: {s2['reproduction']['values']}")
    if not s5["gate1_coast_standoff"]["meets_39_95u_floor"]:
        fails.append(f"GATE1 coast-standoff: {s5['gate1_coast_standoff']['line_min_dist_to_coast']}u "
                     f"< the 39.95u contract floor (target 64u)")
    if not s5["gate2_dressing_ratio"]["in_band"]:
        fails.append(f"GATE2 dressing-ratio: {ratio_writes} > local band max "
                     f"{s5['gate2_dressing_ratio']['local_band_max']}")
    if not s5["gate3_termination_decal"]["clean"]:
        fails.append(f"GATE3 termination-decal: {s5['gate3_termination_decal']['n_contaminating_writes']} "
                     f"contaminating write(s)")
    if not s0["verify"]["shape"]["ok"]:
        fails.append(f"GATE4 macro-silhouette (verify_landmass shape): {s0['verify']['shape']}")

    report["summary"] = dict(
        site_gates_pass=site_gates_ok, is_one_landmass=s1["is_one_landmass"],
        massif_reproduction_ok=s2["reproduction"]["repro_ok"],
        line_length_u=round(s3["line"]["length"], 2),
        standoff_line_min_u=s5["gate1_coast_standoff"]["line_min_dist_to_coast"],
        standoff_meets_64u=s5["gate1_coast_standoff"]["meets_64u_target"],
        standoff_meets_39_95u_floor=s5["gate1_coast_standoff"]["meets_39_95u_floor"],
        body_tris=body_tris, ratio_writes=ratio_writes,
        ratio_in_band=s5["gate2_dressing_ratio"]["in_band"],
        term_south=list(s3["term_a"]), term_north=list(s3["term_b"]),
        all_4_gates_pass=(s5["gate1_coast_standoff"]["meets_39_95u_floor"] and s5["gate2_dressing_ratio"]["in_band"]
                          and s5["gate3_termination_decal"]["clean"] and bool(s0["verify"]["shape"]["ok"])),
        fails=fails if fails else ["none"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    log(f"\n-> {OUT_JSON}")
    log(f"\nSUMMARY: {json.dumps(report['summary'], indent=1, default=str)}")
    log("\nREAD-ONLY throughout -- zero writes to the game install; this script never deploys.")
    return report


if __name__ == "__main__":
    main()
