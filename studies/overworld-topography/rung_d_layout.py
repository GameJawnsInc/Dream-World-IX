"""RUNG D LAYOUT -- the horseshoe bench REBUILT at a new site (SW pocket), grass|desert composition
designed in from day one, ONE anchor instead of Rung C's two.

Read first: ``GROUND-FAMILY-DECODE-2026-07-19.md`` Rung C (the castellation failure this design exists
to avoid) + Round 10/11 (the desert|grass combining language); ``contract_gd_composition.py`` /
``out/contract_gd_composition.json`` (the stock statistics this layout is seeded from); the coast-mosaic
memory's ENSEMBLE CARRY section (the horseshoe donor's own history: qualified 2026-07-15, deployed at
(1280,-1184), removed by the 2026-07-19 install reset); ``mixed_biome_mint.py`` (the exact generators
this script reuses UNCHANGED -- ``generate_partition_line``, ``sector_retile``, ``build_dressing``,
``classify_side`` -- imported, not reimplemented; only the SITE and the ANCHOR COUNT change: one
horseshoe instead of Uaho+crag).

THE KEY DIFFERENCE FROM RUNG C: Rung C planted two SEPARATE small anchors (Uaho r_rim=20, crag
r_rim=33.7) close together on a short line -- their clearance radii (35.0u + 48.7u = 83.7u) ate nearly
the whole 167u corridor before dressing even ran (96 body tris vs 240 dressing writes, INVERTED).
This design uses the horseshoe as the LINE'S ONLY ROCK ANCHOR, both termini landing on its OWN 54.3u-
radius rim -- ONE clearance zone, not two -- mirroring stock's own line, which the contract census
found terminates into ONE mesa complex at BOTH ends (4.27-7.64u nearest-topo49 at every real
termination).

THIS SCRIPT IS READ-ONLY AGAINST THE GAME INSTALL. Every stage below reads real stock/donor bytes and
composes IN-MEMORY; nothing is written to <game>/FF9CustomMap-world. Artifacts land under
``out/rung_d/`` (this study's own scratch, never the game install). No ``--apply`` path exists in this
script -- deploying Rung D (if the ratio settles in-band) is a separate, owner-gated build step that
would reuse ``mixed_biome_mint.py``'s own ``write_dry_run``/``apply_deploy``/``--revert`` machinery,
not duplicate it here.

Run from the repo root:  py studies/overworld-topography/rung_d_layout.py
"""
from __future__ import annotations

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

import mixed_biome_mint as MBM                               # noqa: E402  (generators reused verbatim)
import seam_null_recon as SNR                                 # noqa: E402  (the null-cluster targets)

OUT_DIR = HERE / "out" / "rung_d"
OUT_JSON = OUT_DIR / "rung_d_layout.json"

# ================================================================================================
# SITE (per the owner's scout pick, read-only-verified this session -- see the report's "site_scout"
# section for the live gate re-checks: bx0-4/by16-19 confirmed true open ocean, disjoint from the
# 24 live deployed override blocks, this exact r72/seed42 config reproduces the 2026-07-15 horseshoe
# deploy's own gate numbers bit-for-bit modulo translation -- see "reproduction_check" below).
# ================================================================================================
BENCH_CENTER = (170.0, -1152.0)
BENCH_RADIUS = 72.0
BENCH_SEED = 42.0
HORSESHOE_DONOR = [(5, 15), (6, 15), (5, 16), (6, 16)]

DEPTH_CAP = 16.0                     # contract Law 6: desert body stays THIN (<=3-4 cells)
ANCHOR_CLEAR_MARGIN = 3.0            # same margin mixed_biome_mint.py uses (measured per-anchor)
DESERT_SIDE = 1

LINE_SEED = "rung-d-layout:line"
DRESS_SEED = MBM.GD.DEFAULT_REDRESS_SEED

TARGET_STRAIGHTNESS = MBM.TARGET_STRAIGHTNESS      # 0.7093, contract line_geometry (main arm)
TARGET_TURN = MBM.TARGET_TURN                      # 24.9deg
STOCK_DRESS_QUARTILES = [0.9, 0.4, 0.8, 0.9]        # contract dressing_density_by_quartile_main_component
STOCK_BODY_TRIS = 422                               # contract topo_band.by_family.desert depth-bins 0-3
                                                     # (re-verified: 237+152+29+4, summed live in
                                                     # rung_d_build.py from the contract JSON, not typed in)
# CORRECTED 2026-07-23 (rung_d_build.py's own skeptic-review pass): a prior draft of this module paired
# this ratio's numerator against a "STOCK_CORE_DRESS_TRIS=110" constant claimed to be "the brief's cited
# core-strip figure at the real cluster" -- grep-verified against every leaf value in
# out/contract_gd_composition.json, 110 does NOT correspond to any dressing/strip tri count anywhere in
# that census; it is topo_band.by_family.grass["29"]["0"] (an unrelated grass depth-bin count). There is
# NO traceable whole-map stock dressing:body tri ratio in this study's own census output -- that clause
# is DROPPED, not computed here (see rung_d_build.py's ``stage_ratio_corrected`` for the full, re-derived
# analysis in CONSISTENT units against the two comparators that ARE traceable: Rung C's own same-code
# result, re-read live from out/mixed_biome_mint.json, and the real-stock render-window measurement
# below). This module keeps only the site/anchor/termini/line/retile/dressing GEOMETRY (all independently
# re-verified byte-identical by rung_d_build.py); its own ratio narrative below is now the SAME-UNITS
# writes:body figure (not the plan-entry figure a prior draft used, which does not compare like-for-like
# against Rung C's own writes:body count) -- see rung_d_build.py for the authoritative ratio verdict.
#
# a scope-matched reference: Rung C's own mixed_biome_eye_review.py measured the REAL stock grass|desert
# cluster through the SAME plan-view render window used to judge the built mint (not a whole-map sum) --
# "stock_ab_fam_counts: desert=210 against strip=392" (re-read live from
# out/mixed_biome_mint/renders/mixed_eye_review.json by rung_d_build.py, not typed in here). At
# LOCAL/single-feature scale, stock's own boundary neighbourhood runs decal-heavy too -- this is the
# fairer comparator for a one-massif ribbon composition, where "deep interior desert" barely exists by
# construction.
LOCAL_STOCK_RATIO = 392 / 210                               # 1.867 -- informational echo only; the
                                                              # authoritative in-band verdict is computed
                                                              # in rung_d_build.py against writes (not
                                                              # plan-entry) counts.
COAST_STANDOFF_TARGET = 64.0
COAST_STANDOFF_CONTRACT_WORST = 39.95


def log(msg):
    print(msg)


# ================================================================================================
# STAGE 0 -- site gates (re-verified live, read-only)
# ================================================================================================
def stage0_site(game_root: Path) -> dict:
    log("=" * 100); log("STAGE 0 -- site gates (read-only)"); log("=" * 100)
    built = ISL.build_landmass(center=BENCH_CENTER, base_radius=BENCH_RADIUS, seed=BENCH_SEED,
                               lobes=1, n_patches=0, disc=1, game=game_root)
    footprint = sorted(built["blocks"])
    log(f"  bench footprint ({len(footprint)} blocks): {footprint}")

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
    log(f"  verify_landmass clean: {verify['clean']}")

    return dict(built=built, footprint=footprint, live_deployed=live_deployed,
               gates=dict(open_ocean=ok_ocean, mod_overwrite=ok_overwrite, grid_bounds=ok_grid,
                         verify_clean=bool(verify["clean"])),
               verify={k: v for k, v in verify.items() if k != "placement"})


# ================================================================================================
# STAGE 1 -- the single anchor: dry-carve the horseshoe onto the bench (real donor bytes, in-memory)
# ================================================================================================
def stage1_anchor(built: dict, game_root: Path) -> dict:
    log("\n" + "=" * 100); log("STAGE 1 -- ANCHOR (interior.carve_mountain, donor=horseshoe (5-6,15-16))")
    log("=" * 100)
    soup = IN.soup_from_blocks(built["blocks"])
    rim_capture = {}
    res = IN.carve_mountain(soup, near=BENCH_CENTER, donor=HORSESHOE_DONOR, ground="grass",
                            disc=1, game=game_root, log=MBM._capturing_log(rim_capture, log))
    IN.census_gate(res["changed"], disc=1, game=game_root, log=log)
    r_rim = rim_capture.get("r_rim")
    if r_rim is None:
        raise ValueError("could not capture the massif's own rim radius from carve_mountain's log")
    clear_radius = r_rim + IN.MTN_GBLEND + ANCHOR_CLEAR_MARGIN
    acx, acz = tuple(res["center"])
    log(f"  realized centre {res['center']} rot {res['rot']*90}deg, r_rim {r_rim:.1f}u, "
        f"clear_radius {clear_radius:.2f}u, blocks {sorted(res['changed'])}")
    log(f"  report: {res['report']}")

    # reproduction check -- does THIS site reproduce the 2026-07-15 deploy's own gate numbers?
    rep = res["report"]
    repro = dict(
        blob_tris=(rep["blob_tris"], 713), ensemble_tris=(rep["ensemble_tris"], 122),
        rock_rigid_pct=(round(rep["rock_rigid"] * 100, 2), 0.84),
        apron_slope=(rep["apron_slope"], 9.2), zip_rise=(rep["zip_rise"], 2.13),
        r_rim=(round(r_rim, 1), 54.3), n_span_blocks=(len(res["changed"]), 10))
    repro_ok = all(abs(a - b) < 0.5 for a, b in repro.values() if isinstance(a, (int, float)))
    log(f"  reproduction vs the 2026-07-15 deploy's own recorded numbers: {repro} -> "
        f"{'MATCHES' if repro_ok else 'DIVERGES'}")

    blocks_now = dict(built["blocks"])
    for blk, bm in res["changed"].items():
        blocks_now[blk] = bm

    return dict(res=res, r_rim=r_rim, clear_radius=clear_radius, center=(acx, acz),
               blocks_now=blocks_now, reproduction=dict(repro_ok=repro_ok, values=repro))


# ================================================================================================
# STAGE 2 -- rim ring extraction on the PLACED bench geometry (real bytes, post-carve) -- used to
# pick the two line termini ACTUALLY ON the massif perimeter (not a nearby block centre).
# ================================================================================================
def _rock_rim_ring(blocks: dict, span_blocks, rock_topos=frozenset(IN.MOUNTAIN_ROCK_TOPOS)):
    """The rim of the MAIN connected rock-topo component only -- the footprint-sweep log line
    ("8 interior tris ride verbatim, topos incl. 49: 2") already told us the raw rock-topo tri set
    on the placed bench includes a couple of FREE, disconnected shingle tris (the WALL LAW's shingled
    reality) that are not part of the main welded sheet and break simple degree-2 boundary chaining --
    so this filters to the largest edge-connected rock component first, exactly like
    ``horseshoe_donor_check.py`` stage 1 does on the donor bytes."""
    kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))
    tris = []
    for blk in span_blocks:
        bm = blocks[blk]
        ox, oz = X.block_world_origin(*blk)
        for tri in bm.tris:
            idall = int(round(bm.tangents[tri[0]][0]))
            topo = X.decode_id(idall)["topograph"]
            if topo not in rock_topos:
                continue
            w = [(bm.verts[j][0] + ox, bm.verts[j][1], bm.verts[j][2] + oz) for j in tri]
            tris.append(w)
    edge_tris = defaultdict(list)
    for ti, t in enumerate(tris):
        ps = [kk(v) for v in t]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge_tris[tuple(sorted((ps[a], ps[b])))].append(ti)
    adj = defaultdict(set)
    for ts in edge_tris.values():
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                adj[ts[i]].add(ts[j]); adj[ts[j]].add(ts[i])
    comps, seen = [], set()
    for s in range(len(tris)):
        if s in seen:
            continue
        comp = {s}; st = [s]
        while st:
            t = st.pop()
            for t2 in adj[t]:
                if t2 not in comp:
                    comp.add(t2); st.append(t2)
        seen |= comp
        comps.append(comp)
    comps.sort(key=len, reverse=True)
    main = comps[0]
    edge_use = Counter()
    for ti in main:
        ps = [kk(v) for v in tris[ti]]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge_use[tuple(sorted((ps[a], ps[b])))] += 1
    once = [e for e, n in edge_use.items() if n == 1]
    rings = IN.chain_rings(once, "rung_d_rim")
    rings.sort(key=lambda g: -abs(IN.signed_area(g)))
    return (rings[0] if rings else []), len(tris), [len(c) for c in comps[:5]]


def build_coastline(built: dict):
    """The PRISTINE mint's own outer boundary edges (once-edges of the unmodified island -- read
    BEFORE the carve, so the coastline used for standoff measurement is the real sea/shore frame the
    engine will render, not an artifact of the carve's own hole-ring)."""
    kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))
    edge_use = Counter()
    edge_pts = {}
    for blk, bm in built["blocks"].items():
        ox, oz = X.block_world_origin(*blk)
        for tri in bm.tris:
            w = [(bm.verts[j][0] + ox, bm.verts[j][1], bm.verts[j][2] + oz) for j in tri]
            ps = [kk(v) for v in w]
            for a, b in ((0, 1), (1, 2), (2, 0)):
                e = tuple(sorted((ps[a], ps[b])))
                edge_use[e] += 1
                edge_pts[e] = (w[a], w[b])
    return [edge_pts[e] for e, n in edge_use.items() if n == 1]


def _dist_to_coast_fn(coast_edges):
    def dist_to_coast(px, pz):
        best = None
        for (ax, ay, az), (bx, by, bz) in coast_edges:
            ex, ez = bx - ax, bz - az
            L2 = ex * ex + ez * ez
            if L2 < 1e-9:
                d = math.hypot(px - ax, pz - az)
            else:
                t = max(0.0, min(1.0, ((px - ax) * ex + (pz - az) * ez) / L2))
                cx, cz = ax + t * ex, az + t * ez
                d = math.hypot(px - cx, pz - cz)
            if best is None or d < best:
                best = d
        return best
    return dist_to_coast


def stage2_rim_termini(blocks_now: dict, span_blocks, center, coast_edges) -> dict:
    log("\n" + "=" * 100); log("STAGE 2 -- rim ring extraction + termini selection (both ends ON the "
                              "massif perimeter, chosen for MAXIMUM coastal standoff)")
    log("=" * 100)
    rim, n_rock_tris, comp_sizes = _rock_rim_ring(blocks_now, span_blocks)
    log(f"  outer rim ring: {len(rim)} pts over {n_rock_tris} rock tris across {len(span_blocks)} blocks "
        f"(components {comp_sizes})")
    acx, acz = center
    dist_to_coast = _dist_to_coast_fn(coast_edges)

    # per-rim-point measured distance to THIS island's OWN coastline (not a per-bearing "reach from
    # centre" proxy -- the massif's 77x89u footprint is asymmetric, and a build-time check on the FIRST
    # naive termini pick (opposite-flank chord, "far from centre" heuristic) showed the proxy is
    # misleading: it produced a 20.3u worst-case standoff. This is the real, per-point ground truth.
    per_pt = [(p, dist_to_coast(p[0], p[2])) for p in rim]
    per_pt_sorted = sorted(per_pt, key=lambda pr: -pr[1])
    log(f"  rim-point-to-coast distance: best {per_pt_sorted[0][1]:.2f}u at "
        f"({per_pt_sorted[0][0][0]:.1f},{per_pt_sorted[0][0][2]:.1f}), worst "
        f"{per_pt_sorted[-1][1]:.2f}u -- i.e. NO point on this massif's perimeter clears the 64u "
        f"target on its own; {per_pt_sorted[0][1]:.2f}u is the ceiling this single r72 lobe can offer "
        f"(the brief's own 2-lobe fallback exists for exactly this shortfall).")

    # pick the termini pair maximising the WORST-CASE coastal clearance sampled along the straight
    # chord between them (5 interior samples + both endpoints) -- a direct stand-in for "how close does
    # the wandering line ever get to the coast", cheap to evaluate over all O(n^2) rim pairs without
    # running the (randomised) wandering-line generator once per candidate.
    n = len(rim)
    best = None
    for i in range(n):
        for j in range(i + 1, n):
            pa, pb = rim[i], rim[j]
            d = math.hypot(pa[0] - pb[0], pa[2] - pb[2])
            if not (50.0 <= d <= 170.0):
                continue
            samples = [(pa[0] + t * (pb[0] - pa[0]), pa[2] + t * (pb[2] - pa[2]))
                      for t in (0.0, 0.25, 0.5, 0.75, 1.0)]
            worst = min(dist_to_coast(sx, sz) for sx, sz in samples)
            score = worst
            if best is None or score > best[0]:
                best = (score, pa, pb, d)
    if best is None:
        raise ValueError("no rim-point pair found in the target separation band 50-170u")
    worst_chord_clearance, term_a3, term_b3, chord = best
    term_a = (term_a3[0], term_a3[2])
    term_b = (term_b3[0], term_b3[2])
    log(f"  termini: A={term_a} B={term_b} (chord {chord:.1f}u, both ON the outer rim ring, "
        f"worst sampled chord-to-coast clearance {worst_chord_clearance:.2f}u)")

    return dict(rim=rim, n_rim_pts=len(rim), term_a=term_a, term_b=term_b, chord=chord,
               best_single_point_clearance=per_pt_sorted[0][1],
               worst_chord_clearance=worst_chord_clearance)


# ================================================================================================
# STAGE 3 -- the seeded partition line (mixed_biome_mint.generate_partition_line, UNCHANGED) +
# sector retile (mixed_biome_mint.sector_retile, UNCHANGED FUNCTION -- called with the DELIBERATE
# deviation ``anchors_realized=[]``, see below) with the SINGLE horseshoe anchor.
#
# THE ANCHOR-CLEAR FIX (a build-time finding, this session): running Rung C's own
# ``anchors_realized=[(acx, acz, clear_radius)]`` verbatim here -- clear_radius = r_rim(54.3) +
# MTN_GBLEND(12) + margin(3) = 69.3u FROM THE MASSIF CENTRE -- excluded 1247/1462 candidate tris and
# left 0 desert-body tris: THE SAME CASTELLATION TRAP RUNG C HIT, reproduced by a mismatched tool, not
# a mismatched site. Rung C's clear_radius exists to protect a DIFFERENT anchor's own zip annulus from
# a retile meant to serve the OTHER anchor -- it is a keep-away disk between two separate features. Rung
# D has no second feature to protect FROM: the brief's own key insight ("the massif IS the terminus, not
# an obstacle with a clearance radius") means the zip annulus (still grass-mains topo==0 by construction)
# is *exactly* the ring the desert apron is SUPPOSED to retile -- the contract's own rock-termination law
# (nearest-topo49 4.27-7.64u at every real stock termination, PLAIN mains touching rock, no decal) is a
# claim that desert reaches essentially TO the rock, not that it stops 66-70u short of it. So this stage
# passes ``anchors_realized=[]`` deliberately (sector_retile's own per-tri loop then has nothing to
# exclude on that axis -- 0 anchor-clear exclusions by construction, verified in the stats below); the
# only geometric anchors on the corridor width are DEPTH_CAP (a body tri already IN the retile band, so
# rock-adjacency is fine) and DESERT_SIDE (picked as the side of the line the massif CENTRE sits on --
# i.e. the near-rock side, so retiled tris are the ones actually between the line and the massif flank,
# never the far/outward apron that should stay grass).
# ================================================================================================
def stage3_line_and_retile(blocks_now: dict, term_a, term_b, center):
    log("\n" + "=" * 100); log("STAGE 3 -- partition line + sector retile (ONE anchor, rim-touching)")
    log("=" * 100)
    line = MBM.generate_partition_line(term_a, term_b, seed=LINE_SEED,
                                       target_straightness=TARGET_STRAIGHTNESS,
                                       target_turn=TARGET_TURN)
    log(f"  line: {line['n_segments']} segments, length {line['length']:.1f}u, "
        f"straightness {line['straightness']:.4f} (target {TARGET_STRAIGHTNESS}), "
        f"mean_turn {line['mean_turn']:.1f}deg (target {TARGET_TURN}), matched={line.get('matched')}")

    acx, acz = center
    desert_side = MBM.classify_side(acx, acz, line["points"])[1]   # the side the massif itself sits on
    log(f"  desert_side resolved to {desert_side} (the side of the line the massif centre sits on -- "
        f"the near-rock side)")

    anchors_realized = []          # THE FIX -- see the module-level note above
    blocks_retiled, retile_touched, retile_stats = MBM.sector_retile(
        blocks_now, line["points"], anchors_realized, depth_cap=DEPTH_CAP, desert_side=desert_side)
    log(f"  sector retile: {retile_stats['n_retiled']} desert-body tri(s) across "
        f"{len(retile_touched)} block(s) of {retile_stats['n_main_tris_scanned']} plain-mains tris "
        f"scanned (excluded: anchor-clear {retile_stats['n_excluded_anchor_clear']} [forced 0 by design], "
        f"wrong-side {retile_stats['n_excluded_wrong_side']}, depth {retile_stats['n_excluded_depth']})")

    return dict(line=line, blocks_retiled=blocks_retiled, retile_touched=retile_touched,
               retile_stats=retile_stats, anchors_realized=anchors_realized, desert_side=desert_side)


# ================================================================================================
# STAGE 4 -- dressing (gd_seam_dress.py's own functions, UNCHANGED) + THE RATIO (the Rung-C killer)
# ================================================================================================
def stage4_dressing_and_ratio(blocks_retiled: dict, footprint, retile_touched, game_root: Path):
    log("\n" + "=" * 100); log("STAGE 4 -- dressing + THE DRESSING-VS-BODY RATIO")
    log("=" * 100)
    null = SNR.part_b()
    dress_core = retile_touched if retile_touched else footprint
    dress = MBM.build_dressing(dress_core, blocks_retiled, DRESS_SEED, null, game_root)
    n_body = sum(dress["eligible"].get("_n_retiled", 0) for _ in [0]) or None
    return dict(dress=dress, dress_core=dress_core, null=null)


# ================================================================================================
# STAGE 5 -- coast standoff: distance from the desert-body / dressing footprint to THIS mint's own
# coastline (the built island's outer boundary -- the standoff law is about proximity to open sea,
# and this is a synthetic island in open ocean, so its own shore IS the relevant sea edge).
# ================================================================================================
def stage5_coast_standoff(coast_edges, blocks_retiled: dict, retile_stats: dict, line: dict,
                          footprint) -> dict:
    log("\n" + "=" * 100); log("STAGE 5 -- coast standoff (ecotone line + desert body vs THIS island's "
                              "own shoreline)")
    log("=" * 100)
    dist_to_coast = _dist_to_coast_fn(coast_edges)

    # worst-case (nearest) distance from ANY point on the partition line to the coastline
    line_min = min(dist_to_coast(x, z) for (x, z) in line["points"])
    line_min_pt = min(line["points"], key=lambda p: dist_to_coast(p[0], p[1]))

    # worst-case from the retiled desert-body tri CENTROIDS (the actual desert footprint, not just
    # the line) -- re-derived from blocks_retiled directly (topo==16 tris) for ground truth.
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

    log(f"  min distance, ANY partition-line point -> this island's own coastline: {line_min:.2f}u "
        f"(at {line_min_pt})")
    if body_min is not None:
        log(f"  min distance, ANY desert-body (topo-16) tri centroid -> coastline: {body_min:.2f}u "
            f"over {len(body_dists)} body tris")
    log(f"  (contract's own worst REAL measurement was {COAST_STANDOFF_CONTRACT_WORST}u; "
        f"design target >= {COAST_STANDOFF_TARGET}u)")

    return dict(line_min_dist_to_coast=round(line_min, 2),
               body_min_dist_to_coast=(round(body_min, 2) if body_min is not None else None),
               coast_edges_n=len(coast_edges))


# ================================================================================================
# main
# ================================================================================================
def main():
    game_root = Path(_cfg.find_game_path(None))
    report = {"site": dict(center=list(BENCH_CENTER), radius=BENCH_RADIUS, seed=BENCH_SEED,
                          donor=HORSESHOE_DONOR)}

    s0 = stage0_site(game_root)
    report["stage0_site"] = dict(footprint=[list(b) for b in s0["footprint"]], gates=s0["gates"],
                                 verify=s0["verify"])
    coast_edges = build_coastline(s0["built"])

    s1 = stage1_anchor(s0["built"], game_root)
    report["stage1_anchor"] = dict(
        realized_center=list(s1["center"]), r_rim=round(s1["r_rim"], 2),
        clear_radius=round(s1["clear_radius"], 2), rot_deg=s1["res"]["rot"] * 90,
        changed_blocks=[list(b) for b in s1["res"]["changed"]],
        report=s1["res"]["report"], reproduction=s1["reproduction"])

    span_blocks = list(s1["res"]["changed"])
    s2 = stage2_rim_termini(s1["blocks_now"], span_blocks, s1["center"], coast_edges)
    report["stage2_rim_termini"] = dict(
        n_rim_pts=s2["n_rim_pts"], term_a=list(s2["term_a"]), term_b=list(s2["term_b"]),
        chord=round(s2["chord"], 2), best_single_point_clearance=round(s2["best_single_point_clearance"], 2),
        worst_chord_clearance=round(s2["worst_chord_clearance"], 2))

    s3 = stage3_line_and_retile(s1["blocks_now"], s2["term_a"], s2["term_b"], s1["center"])
    report["stage3_line_and_retile"] = dict(
        line={k: v for k, v in s3["line"].items() if k != "points"},
        desert_side=s3["desert_side"],
        retile_stats=s3["retile_stats"], retile_touched=[list(b) for b in s3["retile_touched"]])

    s4 = stage4_dressing_and_ratio(s3["blocks_retiled"], s0["footprint"], s3["retile_touched"], game_root)
    n_body = s3["retile_stats"]["n_retiled"]
    n_dressed = len(s4["dress"]["plan"])
    n_writes = len(s4["dress"]["writes"])
    # NOTE (corrected 2026-07-23): the LOAD-BEARING ratio is writes:body (both are individual-triangle
    # counts, the same granularity Rung C's own comparator and the real-stock render measure) -- NOT
    # plan-entries:body (a plan entry can resolve to 1 or 2 physical tri-writes, so it is not the same
    # unit as a body-tri count). This module reports BOTH for transparency; the AUTHORITATIVE verdict
    # (consistent units, live-re-read comparators) is computed in rung_d_build.py.
    ratio_planned = (n_dressed / n_body) if n_body else None
    ratio_writes = (n_writes / n_body) if n_body else None
    report["stage4_dressing"] = dict(
        n_straddle_eligible=len(s4["dress"]["eligible"]["straddle_eligible"]),
        n_fringe_eligible={k: len(v) for k, v in s4["dress"]["eligible"]["fringe_eligible"].items()},
        n_planned=n_dressed, n_writes=n_writes, footprint_bytes=s4["dress"]["footprint_bytes"],
        touched_blocks=[list(b) for b in s4["dress"]["touched"]])
    log(f"\n  DESERT-BODY tris (sector-retiled, dressing-eligible pool excluded): {n_body}")
    log(f"  DRESSING plan entries (STRIPS decals placed): {n_dressed} ({n_writes} tri-writes)")
    log(f"  RATIO (plan-entries:body, NOT the load-bearing figure) = {n_dressed}:{n_body} = "
        + (f"{ratio_planned:.4f}" if ratio_planned else "n/a (0 body tris)"))
    log(f"  RATIO (writes:body, the load-bearing SAME-UNITS figure) = {n_writes}:{n_body} = "
        + (f"{ratio_writes:.4f}" if ratio_writes else "n/a (0 body tris)"))
    log("  See rung_d_build.py's stage_ratio_corrected() for the authoritative verdict against "
       "Rung C's own writes:body count (re-read live from out/mixed_biome_mint.json) and the "
       "real-stock render-window comparator (re-read live from mixed_eye_review.json) -- the prior "
       "draft of this module compared plan-entries against Rung C's writes-count, an inconsistent-"
       "units error caught by the skeptic review and fixed there.")
    report["ratio"] = dict(n_dressed=n_dressed, n_body=n_body, ratio_planned=ratio_planned,
                           ratio_writes=ratio_writes, stock_local_ratio=LOCAL_STOCK_RATIO,
                           note="authoritative in-band verdict computed in rung_d_build.py, not here")

    s5 = stage5_coast_standoff(coast_edges, s3["blocks_retiled"], s3["retile_stats"], s3["line"],
                               s0["footprint"])
    report["stage5_coast_standoff"] = s5
    standoff_ok = s5["line_min_dist_to_coast"] >= COAST_STANDOFF_TARGET
    report["stage5_coast_standoff"]["meets_64u_target"] = standoff_ok
    log(f"  meets >=64u target: {standoff_ok} (single r72 lobe ceiling measured in stage 2: "
        f"{s2['best_single_point_clearance']:.1f}u)")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    log(f"\n-> {OUT_JSON}")
    log("\nREAD-ONLY throughout -- zero writes to the game install; this script never deploys.")
    return report


if __name__ == "__main__":
    main()
