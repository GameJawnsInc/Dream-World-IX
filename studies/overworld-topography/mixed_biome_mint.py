"""THE FIRST MIXED-BIOME MINT -- a minted landmass containing a genuine grass|desert boundary,
composed ENTIRELY from proven generators (2026-07-22, the owner's pick task).

Read first: ``GROUND-FAMILY-DECODE-2026-07-19.md`` Round 10/11 (the desert|grass COMBINING LANGUAGE
decode -- the 3-rect vocabulary, THE TERMINATION LAW, THE COAST-STANDOFF LAW, THE TOPO-16-ONLY LAW);
``contract_gd_composition.py`` (the read-only bytes census this build's four measured constraints come
from, ``out/contract_gd_composition.json``); ``gd_seam_dress.py`` (the dressing tool this script's
dressing step is a direct, unmodified reuse of -- only the ``--core`` target changes); and
``ff9mapkit/world/orphangate.py`` (the law-checker every composed block is graded against).

THE PIPELINE (every step a call into an already-proven generator; the only NEW code is the sector-
retile cell-membership predicate + the partition-line generator -- both pure data/geometry, zero new
byte-transform primitives):

  1. MINT     -- :func:`ff9mapkit.world.island.build_landmass` (the exact ``world-island`` mechanism),
                 IN-MEMORY (never deployed): a 17-block grass landmass, --flat (byte-frozen mains),
                 centred at the read-only-verified open-ocean site (190,-1120) r=95 seed=728.0 lobes=2.
  2. ANCHORS  -- :func:`ff9mapkit.world.interior.carve_mountain` (the exact ``world-mountain``
                 mechanism), called TWICE in-memory directly on the freshly-built soup
                 (:func:`ff9mapkit.world.interior.soup_from_blocks` accepts a freshly-built blocks dict
                 -- "one code path" per its own docstring, so no deploy-then-reread round-trip is
                 needed): Uaho (0,0) at terminus A, the crag (10,5-6) at terminus B -- BOTH qualified
                 donors, per the study arc's own donor census.
  3. SECTOR RETILE -- the one genuinely NEW component (below): a seeded partition-line cell-walk +
                 a per-triangle cell-membership predicate that selects which ALREADY-topo-0 grass-mains
                 triangles sit on the desert side of the line, within the measured depth cap, and OUTSIDE
                 each anchor's own carved footprint (built-time finding, see the module docstring's
                 ORDERING NOTE) -- then applies the SAME byte transform every ``--ground desert`` mint /
                 :class:`~ff9mapkit.world.transplant.GroundRetile` already ships (the desert mains UV
                 delta), with the ONE disclosed deviation Law 6 requires: topo forced to 16 (the
                 boundary-desert topo), never desert's own far-interior mains topo 17.
  4. DRESSING -- ``gd_seam_dress.py``'s own ``assign_dressing``/``resolve_plan_writes``/``compute_dress``
                 functions, called UNCHANGED (imported, not reimplemented) against the retiled in-memory
                 blocks via a small IN-MEMORY adapter (:func:`find_eligible_inmemory`, replacing only the
                 disk-load half of ``gd_seam_dress.find_eligible`` -- the eligibility/assignment/byte-
                 transform logic itself is the identical function object).
  5. GATES    -- verify_landmass (the pristine pre-retile mint), the orphan-decal gate (0/0 mandatory),
                 the wang-carry gate, the mod-overwrite gate, the grid-bounds check, dressing statistics
                 vs the null bands, and byte-level sanity (the FLAT-MESH invariant + the sea-layer law).

ORDERING NOTE (a build-time finding, not in the design doc): the design pipeline lists SECTOR RETILE
before ANCHORS. Building it that order first surfaces a real hazard: ``carve_mountain``'s own
plain-grass-mains classifier (``interior.py``'s ``plain[]``, the ``band_clean`` placement gate) checks
each tri's UV against the GRASS family region only -- a tri already retiled to the desert UV rect reads
as "non-plain" and can trip ``band_clean``'s "footprint not clear of plain-grass mains" refusal if it
falls inside the anchor's clearance band, and even where it doesn't fail outright, retiling INSIDE the
zip annulus a mountain carve is about to build would corrupt cells before the carve had a chance to see
them as plain grass. This script therefore runs ANCHORS BEFORE SECTOR RETILE: the retile then only ever
touches tris that carve_mountain has already left as plain grass-topo-0 (a rock/zip tri never re-reads
topo 0 with a grass-mains UV -- rock is topo 49, the zip annulus stays grass, but the retile ALSO excludes
any tri within ``ANCHOR_CLEAR`` of the realized anchor centre, so the freshly-built zip annulus is never
touched even though it shares the same topo id).

Conventions match ``comp1_orphan_redress.py`` / ``gd_seam_dress.py`` exactly:
  DRY-RUN (default -- reads real stock+donor bytes only, ZERO writes to the game install; builds the
  would-be-deployed file set into ``out/mixed_biome_mint/<mod_folder>/...``):
    py studies/overworld-topography/mixed_biome_mint.py
  APPLY (owner-gated; backs up any pre-existing target file first (refuses on backup failure), writes,
  then auto-mirrors to Disc4 -- NOT run by this workflow; the harness this script ships in is dry-run-only
  by hard rule):
    py studies/overworld-topography/mixed_biome_mint.py --apply
  REVERT a prior --apply (deletes newly-written files, restores any backed-up pre-existing ones):
    py studies/overworld-topography/mixed_biome_mint.py --revert mixed-biome-mint.<timestamp>
  Artifacts -> out/mixed_biome_mint.json (the full gate report) + out/mixed_biome_mint/ (the file set).
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import random
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit import config as _cfg                       # noqa: E402
from ff9mapkit.world import discmirror as DM                # noqa: E402
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import grassland as GL                 # noqa: E402
from ff9mapkit.world import interior as IN                  # noqa: E402
from ff9mapkit.world import island as ISL                   # noqa: E402
from ff9mapkit.world import mesh as M                        # noqa: E402
from ff9mapkit.world import orphangate as OG                 # noqa: E402
from ff9mapkit.world import transplant as TP                 # noqa: E402

import gd_seam_dress as GD                                  # noqa: E402  (the dressing tool, reused verbatim)
import seam_null_recon as SNR                                # noqa: E402  (the TRANSPLANT-NULL census)

MOD = "FF9CustomMap-world"
OUT_ROOT = HERE / "out" / "mixed_biome_mint"
OUT_JSON = HERE / "out" / "mixed_biome_mint.json"
BACKUP_ROOT = REPO_ROOT / "backups"

# ================================================================================================
# SITE + DESIGN CONSTANTS (cited from the design doc; the two endpoints are TIGHTENED from the
# design's own 55u-half-length claim after this build independently re-measured the site's real
# per-bearing coastline reach -- see the module docstring's coast-standoff finding in the report).
# ================================================================================================
CENTER = (190.0, -1120.0)
RADIUS = 95.0
SEED = 728.0
LOBES = 2
GROUND = "grass"

# partition-line endpoints, world coords -- along the mint's own Z axis (bearing 90/270 in the
# probe's convention). BUILD-TIME FINDING (see the module docstring): the design's claimed endpoints
# (190,-1076)/(190,-1164), 55u/44u half-length off the mint centre, sit only ~2u from a block edge in
# X -- carve_mountain's single-block span pipeline needs its blob (radius+band ~26.5u for Uaho) to fit
# WHOLLY inside ONE 64u block, which forces the anchor's --near point close to that block's OWN
# centre (a ~7x7u tolerance window). Re-picked to the centres of two footprint blocks 2 rows apart
# (128u line length, closer to the real cluster's own 134u endpoint separation than either design
# draft): block (2,16) centre and block (2,18) centre, both independently re-verified (this build) to
# sit >60u from the mint's own coastline on every lateral bearing.
TERM_A = (160.0, -1056.0)                                   # block (2,16) centre -- Uaho anchor
# the crag donor's rim radius (33.7u, measured this build) needs a 6-block span; x=140 keeps that
# span inside columns {1,2} (x=160 would need column 3, whose row 19 block is outside the mint's
# own 17-block footprint -- a build-time finding, see the module docstring)
TERM_B = (140.0, -1184.0)                                   # near block (1-2,18) centre -- crag anchor

ANCHOR_A_DONOR = (0, 0)                                     # Uaho -- qualified donor
ANCHOR_B_DONOR = [(10, 5), (10, 6)]                          # the crag -- qualified donor

DEPTH_CAP = 16.0                # desert body perpendicular depth cap (contract Law 6: thin, ~3-4 cells)
ANCHOR_CLEAR_MARGIN = 3.0       # added on top of each anchor's OWN measured max carried-vertex reach
                                 # (Uaho r_rim=20 and the crag r_rim=33.7 differ a lot -- a fixed guess
                                 # would either starve Uaho's line room or under-clear the crag's zip
                                 # annulus, so this is measured per-anchor after each carve, not fixed)
DESERT_SIDE = 1                 # which side of the (signed) line is desert -- arbitrary, fixed here

LINE_SEED = "mixed-biome-mint:line"
DRESS_SEED = GD.DEFAULT_REDRESS_SEED    # 0xF93, the same seed gd_seam_dress.py / GroundRetile use

TARGET_STRAIGHTNESS = 0.7093    # contract_gd_composition.json line_geometry (main arm)
STRAIGHTNESS_TOL = 0.10
TARGET_TURN = 24.9
TURN_TOL = 8.0
LINE_CELL = 4.0                 # the lattice cell size the walk steps on


# ================================================================================================
# 0. helpers
# ================================================================================================
def _block_in_grid(blk):
    return M.block_in_grid(blk[0], blk[1])


def gate(gates: list, name, ok, detail=""):
    gates.append({"name": name, "ok": bool(ok), "detail": str(detail)[:4000]})
    print(f"GATE [{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
    return bool(ok)


import re as _re                                            # noqa: E402
_RIM_RADIUS_RE = _re.compile(r"max plan radius ([\d.]+)u")


def _capturing_log(store: dict, inner=print):
    """Wrap ``carve_mountain``'s own ``log=`` callback to ALSO capture its "max plan radius Xu"
    line (the massif's real ``r_rim``, printed but not returned in ``res['report']``) -- used to
    compute each anchor's OWN sector-retile clearance radius (see the ANCHOR loop)."""
    def _log(msg):
        inner(msg)
        m = _RIM_RADIUS_RE.search(str(msg))
        if m:
            store["r_rim"] = float(m.group(1))
    return _log


# ================================================================================================
# 1. THE PARTITION-LINE GENERATOR (the one genuinely new geometry primitive -- gated against the
#    measured stock line-shape statistics, contract_gd_composition.json's own line_geometry numbers)
# ================================================================================================
def _angle_between(v1, v2):
    l1 = math.hypot(*v1)
    l2 = math.hypot(*v2)
    if l1 < 1e-9 or l2 < 1e-9:
        return 0.0
    cosang = max(-1.0, min(1.0, (v1[0]*v2[0] + v1[1]*v2[1]) / (l1 * l2)))
    return math.degrees(math.acos(cosang))


def _one_walk(ca, cb, rng, *, forward_bias=0.65):
    """One seeded 8-connected cell walk from ``ca`` to ``cb`` (lattice cells) -- a wandering, not
    straight, path (real turns + occasional lateral steps), forced to terminate exactly at ``cb``."""
    dirs8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    cur = list(ca)
    path = [tuple(cur)]
    max_steps = int(3 * (abs(cb[0]-ca[0]) + abs(cb[1]-ca[1])) + 24)
    for _ in range(max_steps):
        if tuple(cur) == tuple(cb):
            break
        dx, dy = cb[0]-cur[0], cb[1]-cur[1]
        if rng.random() < forward_bias:
            step = (1 if dx > 0 else -1 if dx < 0 else 0, 1 if dy > 0 else -1 if dy < 0 else 0)
            if step == (0, 0):
                step = dirs8[rng.randrange(8)]
        else:
            step = dirs8[rng.randrange(8)]
        cur = [cur[0] + step[0], cur[1] + step[1]]
        path.append(tuple(cur))
    while tuple(cur) != tuple(cb):                          # force-terminate (guarantees reaching cb)
        dx, dy = cb[0]-cur[0], cb[1]-cur[1]
        step = (1 if dx > 0 else -1 if dx < 0 else 0, 1 if dy > 0 else -1 if dy < 0 else 0)
        cur = [cur[0] + step[0], cur[1] + step[1]]
        path.append(tuple(cur))
    dedup = [path[0]]
    for p in path[1:]:
        if p != dedup[-1]:
            dedup.append(p)
    return dedup


def generate_partition_line(a, b, *, seed, cell: float = LINE_CELL,
                            target_straightness=TARGET_STRAIGHTNESS, straightness_tol=STRAIGHTNESS_TOL,
                            target_turn=TARGET_TURN, turn_tol=TURN_TOL, max_tries=600) -> dict:
    ca = (math.floor(a[0] / cell), math.floor(a[1] / cell))
    cb = (math.floor(b[0] / cell), math.floor(b[1] / cell))
    straight_dist = math.hypot(b[0]-a[0], b[1]-a[1])
    rng = random.Random(seed)
    best = None
    for attempt in range(max_tries):
        cellpath = _one_walk(ca, cb, rng)
        pts = [((i + 0.5) * cell, (j + 0.5) * cell) for (i, j) in cellpath]
        pts[0] = a
        pts[-1] = b
        length = sum(math.hypot(pts[k+1][0]-pts[k][0], pts[k+1][1]-pts[k][1]) for k in range(len(pts)-1))
        straightness = straight_dist / length if length else 0.0
        turns = []
        for k in range(1, len(pts) - 1):
            v1 = (pts[k][0]-pts[k-1][0], pts[k][1]-pts[k-1][1])
            v2 = (pts[k+1][0]-pts[k][0], pts[k+1][1]-pts[k][1])
            turns.append(_angle_between(v1, v2))
        mean_turn = sum(turns) / len(turns) if turns else 0.0
        score = abs(straightness - target_straightness) / max(straightness_tol, 1e-6) \
            + abs(mean_turn - target_turn) / max(turn_tol, 1e-6)
        rec = dict(points=pts, straightness=straightness, mean_turn=mean_turn, length=length,
                  n_segments=len(pts) - 1, tries=attempt + 1)
        if best is None or score < best[0]:
            best = (score, rec)
        if (abs(straightness - target_straightness) <= straightness_tol
                and abs(mean_turn - target_turn) <= turn_tol):
            rec["matched"] = True
            return rec
    best[1]["matched"] = False
    return best[1]


def classify_side(px, pz, points):
    """Perpendicular signed distance from ``(px,pz)`` to the NEAREST segment of the polyline
    ``points`` (clamped to the segment), + which side (+1/-1, the sign of the local cross product)."""
    best = None
    for k in range(len(points) - 1):
        ax, az = points[k]
        bx, bz = points[k + 1]
        ex, ez = bx - ax, bz - az
        L2 = ex * ex + ez * ez
        if L2 < 1e-9:
            continue
        t = ((px - ax) * ex + (pz - az) * ez) / L2
        tc = max(0.0, min(1.0, t))
        cx, cz = ax + tc * ex, az + tc * ez
        d2 = (px - cx) ** 2 + (pz - cz) ** 2
        cross = ex * (pz - az) - ez * (px - ax)
        if best is None or d2 < best[0]:
            best = (d2, cross, k, tc)
    d2, cross, k, tc = best
    return math.sqrt(d2), (1 if cross > 0 else -1), k, tc


# ================================================================================================
# 2. THE SECTOR RETILE (the one new byte-transform CALL SITE -- the transform itself is the exact,
#    already-shipped desert mains UV translation every --ground desert mint uses; the only deviation
#    is the topo target, per Law 6)
# ================================================================================================
def sector_retile(blocks: dict, line_points, anchors_realized, *, depth_cap=DEPTH_CAP,
                  desert_side=DESERT_SIDE) -> tuple:
    """Reclassify plain-grass-mains (topo==0) triangles within ``depth_cap`` of the desert side of
    ``line_points``, EXCLUDING anything inside a realized anchor's OWN measured clearance radius (the
    module docstring's ORDERING NOTE), to desert: UV += GROUNDS['desert']'s mains delta (the exact,
    already-shipped translation), topo forced to 16 (Law 6 -- never desert's own plain-mains topo
    17), event/area/flags preserved bit-for-bit. Zero geometry; only existing triangles' UV+idall
    move. ``anchors_realized``: ``[(ax, az, clear_radius), ...]`` -- one entry per anchor, its own
    measured max carried-vertex reach + :data:`ANCHOR_CLEAR_MARGIN`. Returns
    ``(new_blocks, touched_blocks, stats)``."""
    du, dv = GL.GROUNDS["desert"]["mains_du"], GL.GROUNDS["desert"]["mains_dv"]
    dst_topo = 16
    new_blocks = {}
    touched = set()
    n_main = n_retiled = n_excl_anchor = n_excl_depth = n_excl_side = 0
    per_block = {}
    for blk, bm in blocks.items():
        ox, oz = X.block_world_origin(*blk)
        nb = copy.deepcopy(bm)
        cnt = 0
        for tri in nb.tris:
            idall0 = int(round(nb.tangents[tri[0]][0]))
            d0 = X.decode_id(idall0)
            if d0["topograph"] != 0:                        # only plain grass mains are eligible
                continue
            n_main += 1
            cx = sum(nb.verts[j][0] for j in tri) / 3.0 + ox
            cz = sum(nb.verts[j][2] for j in tri) / 3.0 + oz
            if any(math.hypot(cx - ax, cz - az) < clr for (ax, az, clr) in anchors_realized):
                n_excl_anchor += 1
                continue
            dist, side, _seg, _t = classify_side(cx, cz, line_points)
            if side != desert_side:
                n_excl_side += 1
                continue
            if dist > depth_cap:
                n_excl_depth += 1
                continue
            for j in tri:
                u, v = nb.uvs[j]
                nb.uvs[j] = [u + du, v + dv]
                old = int(round(nb.tangents[j][0]))
                dd = X.decode_id(old)
                new_id = X.encode_id(dd["event"], dd["area"], dst_topo, dd["flags"])
                old_tan = nb.tangents[j]
                nb.tangents[j] = [float(new_id)] + list(old_tan[1:])
            cnt += 1
            n_retiled += 1
        new_blocks[blk] = nb
        if cnt:
            touched.add(blk)
            per_block[f"{blk}"] = cnt
    stats = dict(n_main_tris_scanned=n_main, n_retiled=n_retiled, n_excluded_anchor_clear=n_excl_anchor,
                n_excluded_wrong_side=n_excl_side, n_excluded_depth=n_excl_depth,
                per_block_retiled=per_block)
    return new_blocks, sorted(touched), stats


# ================================================================================================
# 3. IN-MEMORY DRESSING ADAPTER -- reuses gd_seam_dress's OWN assign_dressing/resolve_plan_writes/
#    compute_dress function objects unchanged; only the disk-load half of its find_eligible is
#    replaced by an in-memory + ring-aware equivalent (this mint is never deployed, so there is
#    nothing on disk to load).
# ================================================================================================
def _read_block_context_one(blk, game_root: Path):
    bx, by = blk
    path = game_root / MOD / M.override_relpath(1, bx, by, "0_1", "Terrain")
    if path.is_file():
        return [("Terrain", M.blockmesh_from_ff9mesh(path, disc=1, x=bx, y=by, lod="0_1", part="terrain"))]
    try:
        bm = X.read_block(bx, by, disc=1, lod="0_1", part="terrain", game=game_root)
    except Exception:
        return None
    return [("Terrain", bm)]


def make_context_provider(all_blocks: dict, game_root: Path):
    """A ring-context provider for :func:`orphangate.orphan_decal_gate` / this script's own
    eligibility scan: a ring block that is part of THIS mint (in-memory, never deployed) reads from
    ``all_blocks``; any other ring block falls back to deployed-else-stock disk bytes (read-only,
    matches ``orphangate.default_context_provider``'s own fallback exactly)."""
    def provider(region_cells):
        ring = OG._ring_blocks(region_cells)
        out = {}
        for blk in ring:
            if blk in all_blocks:
                out[blk] = [("Terrain", all_blocks[blk])]
                continue
            ctx = _read_block_context_one(blk, game_root)
            if ctx is not None:
                out[blk] = ctx
        return out
    return provider


def find_eligible_inmemory(core, all_blocks: dict, game_root: Path) -> dict:
    """The in-memory analogue of ``gd_seam_dress.find_eligible`` -- identical eligibility logic
    (straddle = Law 2 same-cell split; fringe = ``orphangate.row_lawfulness`` forward direction),
    sourced from ``all_blocks`` (this build's own composed meshes) instead of deployed disk files."""
    core_bms = {blk: all_blocks[blk] for blk in core}
    cell_meshes_core = {blk: [("Terrain", bm)] for blk, bm in core_bms.items()}
    core_records = OG.flatten_terrain_records(cell_meshes_core)
    provider = make_context_provider(all_blocks, game_root)
    ring_meshes = provider(core)
    ring_records = OG.flatten_terrain_records(ring_meshes)
    cell_fams = GD.cell_fams_from_records(core_records + ring_records)

    dressed_cells = set()
    for r in core_records:
        cls = OG.classify_strip_tri(r["world_pts"], r["uv"], r["cell"])
        if cls is not None and cls[0] == GD.GD_PAIR:
            dressed_cells.add(r["cell"])

    core_cell_records = defaultdict(list)
    for r in core_records:
        if r["fam"] in ("grass", "desert"):
            core_cell_records[r["cell"]].append(r)

    straddle_eligible = sorted(
        c for c, recs in core_cell_records.items()
        if {r["fam"] for r in recs} == {"grass", "desert"} and c not in dressed_cells)

    fringe_eligible = {"grass": [], "desert": []}
    for c, recs in core_cell_records.items():
        fams_here = {r["fam"] for r in recs}
        if len(fams_here) != 1 or c in dressed_cells:
            continue
        fam = next(iter(fams_here))
        row = 0 if fam == "grass" else 2
        lawful, _detail = OG.row_lawfulness(c, GD.GD_PAIR, row, fam, cell_fams, accept_radius=GD.ACCEPT_RADIUS)
        if lawful:
            fringe_eligible[fam].append(c)
    for fam in fringe_eligible:
        fringe_eligible[fam].sort()

    return dict(core=list(core), core_bms=core_bms, cell_meshes_core=cell_meshes_core,
               core_records=core_records, ring_meshes=ring_meshes, cell_fams=cell_fams,
               dressed_cells=sorted(dressed_cells), core_cell_records=core_cell_records,
               straddle_eligible=straddle_eligible, fringe_eligible=fringe_eligible)


def build_dressing(core, all_blocks: dict, seed, null: dict, game_root: Path) -> dict:
    eligible = find_eligible_inmemory(core, all_blocks, game_root)
    plan = GD.assign_dressing(eligible, seed, null)
    writes = GD.resolve_plan_writes(eligible, plan)
    new_blocks = dict(all_blocks)
    per_block_copy = {}
    footprint_bytes = 0
    origins = {blk: X.block_world_origin(*blk) for blk in core}
    for w in writes:
        blk = tuple(w["block"])
        cell = tuple(w["cell"])
        if blk not in per_block_copy:
            per_block_copy[blk] = copy.deepcopy(all_blocks[blk])
        src_bm = eligible["core_bms"][blk]                  # unmutated read source (pre-dressing bytes)
        ox, oz = origins[blk]
        new_uv, new_idall = GD.compute_dress(src_bm, ox, oz, cell, w["tri_idx"], w["fam"], w["row"], w["ori"])
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
    return dict(eligible=eligible, plan=plan, writes=writes, new_blocks=new_blocks,
               touched=touched, footprint_bytes=footprint_bytes)


# ================================================================================================
# 4. FULL COMPOSITION
# ================================================================================================
def compose(game_root: Path, *, log=print) -> dict:
    gates = []
    report: dict = {"site": {"center": list(CENTER), "radius": RADIUS, "seed": SEED, "lobes": LOBES,
                             "ground": GROUND}}

    # ---- step 0: OPEN-OCEAN + MOD-OVERWRITE pre-checks (before spending any build time) ----------
    log("=" * 100)
    log("STEP 0 -- site pre-checks")
    log("=" * 100)
    plane = ISL._sea_plane(1, game_root)

    # ---- step 1: MINT (build_landmass, in-memory; the exact world-island mechanism) --------------
    log("\nSTEP 1 -- MINT (island.build_landmass, --flat equivalent)")
    built = ISL.build_landmass(center=CENTER, base_radius=RADIUS, seed=SEED, lobes=LOBES,
                               ground=GROUND, stamps=None, disc=1, game=game_root)
    footprint = sorted(built["blocks"])
    report["footprint_blocks"] = [list(b) for b in footprint]
    log(f"  footprint: {len(footprint)} blocks: {footprint}")

    occupied = {blk: occ for blk in footprint
               if (occ := ISL._real_block_parts(blk, disc=1, lod="0_1", game=game_root))}
    gate(gates, "OPEN-OCEAN TARGET: every footprint block is true open ocean (0 real assets)",
        not occupied, f"{occupied}" if occupied else "")

    live_deployed = enumerate_live_deployed_blocks(game_root)
    overlap = sorted(set(footprint) & set(live_deployed))
    gate(gates, "MOD-OVERWRITE (pre-check): footprint disjoint from the live deployed override inventory",
        not overlap, f"live deployed={len(live_deployed)} blocks in "
                     f"{len(connected_components(live_deployed))} cluster(s); overlap={overlap}")

    gate(gates, "GRID-BOUNDS: every footprint block is inside the 24x20 overworld grid",
        all(_block_in_grid(b) for b in footprint), f"{[b for b in footprint if not _block_in_grid(b)]}")

    verify = ISL.verify_landmass(built, sea_plane=plane, land_height=3.2)
    gate(gates, "verify_landmass: the pristine mint (geometry/UV-region/slope-envelope/shape/"
        "placement-census) is CLEAN", verify["clean"],
        f"{ {k: v for k, v in verify.items() if k != 'placement'} }")
    report["verify_landmass"] = {k: v for k, v in verify.items() if k != "placement"}
    report["verify_landmass"]["placement_miss_total"] = sum(
        e.get("miss", 0) for e in verify.get("placement", {}).values())

    # ---- step 2: ANCHORS (carve_mountain x2, in-memory, on the freshly-built soup) ----------------
    log("\nSTEP 2 -- ANCHORS (interior.carve_mountain x2, --ground grass, in-memory)")
    blocks_now = dict(built["blocks"])
    anchor_reports = []
    anchor_realized = []                     # [(ax, az, clear_radius), ...] for the sector retile
    for label, term, donor in (("A (Uaho)", TERM_A, ANCHOR_A_DONOR), ("B (crag)", TERM_B, ANCHOR_B_DONOR)):
        soup = IN.soup_from_blocks(blocks_now)
        # EXACT placement (center=, not near=): term is already chosen as its host block's own
        # centre (the module docstring's build-time finding) -- a near= scan actually drifted OFF
        # that safe centre chasing a local "clearance" metric that does not account for the full
        # apron-blend reach to the block edge, and produced a weld crack at the block boundary.
        rim_capture = {}
        res = IN.carve_mountain(soup, center=term, donor=donor, ground=GROUND, disc=1, game=game_root,
                                log=_capturing_log(rim_capture, log))
        IN.census_gate(res["changed"], disc=1, game=game_root, log=log)
        for blk, bm in res["changed"].items():
            blocks_now[blk] = bm
        acx, acz = tuple(res["center"])
        # the anchor's OWN measured rim radius + the apron blend reach (Uaho r_rim=20 vs the crag's
        # 33.7 differ a lot -- measured per-anchor from carve_mountain's own log line, never a fixed
        # guess; a naive "max vertex distance across every span block" over-counts hugely for a
        # multi-block span, since most of a span block's re-emitted mesh is untouched pristine grass
        # far from the actual carved footprint -- a build-time finding, first measured 122.4u wrong)
        r_rim = rim_capture.get("r_rim")
        if r_rim is None:
            raise ValueError(f"could not capture the massif's own rim radius from carve_mountain's "
                             f"log for anchor {label} -- the log line format may have changed")
        clear_radius = r_rim + IN.MTN_GBLEND + ANCHOR_CLEAR_MARGIN
        anchor_realized.append((acx, acz, clear_radius))
        anchor_reports.append({"label": label, "requested_center": list(term), "donor": donor,
                               "realized_center": [acx, acz], "rot_deg": res["rot"] * 90,
                               "measured_r_rim": r_rim, "clear_radius": round(clear_radius, 2),
                               "report": res["report"], "changed_blocks": [list(b) for b in res["changed"]],
                               "has_ensemble_parts": bool(res.get("changed_parts"))})
        gate(gates, f"ANCHOR {label}: carve_mountain + census_gate CLEAN (in-process gates raise on "
            f"failure -- reaching here means every one passed)", True,
            f"realized center {res['center']}, {res['report']['blob_tris']} donor tris, "
            f"{res['report']['zip_tris']} zip tris, rock rigidity {res['report']['rock_rigid']*100:.2f}%")
        log(f"  ANCHOR {label}: requested centre {term} -> realized centre {res['center']} "
           f"rot {res['rot']*90}deg, blocks {sorted(res['changed'])}, measured r_rim {r_rim:.1f}u "
           f"(retile clearance {clear_radius:.1f}u)")
    report["anchors"] = anchor_reports
    gate(gates, "neither anchor produced ENSEMBLE aux parts (Uaho + the crag are both object-only "
        "donors -- build_file_set does not write Falls/River/RiverJoint overrides; a future donor "
        "swap to an ensemble-class massif would need that written, not silently dropped)",
        not any(a["has_ensemble_parts"] for a in anchor_reports),
        f"{[a['label'] for a in anchor_reports if a['has_ensemble_parts']]}")

    # ---- step 3: SECTOR RETILE (the one new component) --------------------------------------------
    log("\nSTEP 3 -- SECTOR RETILE (the desert|grass partition line)")
    line = generate_partition_line(TERM_A, TERM_B, seed=LINE_SEED)
    report["partition_line"] = {k: v for k, v in line.items() if k != "points"}
    report["partition_line"]["endpoints"] = [list(TERM_A), list(TERM_B)]
    log(f"  line: {line['n_segments']} segments, length {line['length']:.1f}u, "
       f"straightness {line['straightness']:.4f} (target {TARGET_STRAIGHTNESS} +/-{STRAIGHTNESS_TOL}), "
       f"mean turn {line['mean_turn']:.1f}deg (target {TARGET_TURN} +/-{TURN_TOL}), matched={line.get('matched')}")
    gate(gates, "partition-line shape lands within the measured stock line-geometry tolerance band",
        line.get("matched", False),
        f"straightness={line['straightness']:.4f} mean_turn={line['mean_turn']:.1f} "
        f"(tries={line['tries']})")

    blocks_retiled, retile_touched, retile_stats = sector_retile(
        blocks_now, line["points"], anchor_realized)
    report["sector_retile"] = dict(retile_stats, touched_blocks=[list(b) for b in retile_touched])
    log(f"  sector retile: {retile_stats['n_retiled']} tri(s) retiled across "
       f"{len(retile_touched)} block(s) of {retile_stats['n_main_tris_scanned']} plain-mains tris scanned "
       f"(excluded: anchor-clear {retile_stats['n_excluded_anchor_clear']}, "
       f"wrong-side {retile_stats['n_excluded_wrong_side']}, depth {retile_stats['n_excluded_depth']})")
    gate(gates, "sector retile touched >=1 triangle (a genuine grass|desert contact was created)",
        retile_stats["n_retiled"] > 0, f"n_retiled={retile_stats['n_retiled']}")

    # byte-diff confinement check on the retile itself (UV+idall only, zero geometry)
    geom_untouched = True
    for blk in retile_touched:
        b0, b1 = blocks_now[blk], blocks_retiled[blk]
        if b0.verts != b1.verts or b0.normals != b1.normals:
            geom_untouched = False
    gate(gates, "sector retile: zero vertex/normal motion on every touched block (UV+idall only)",
        geom_untouched)

    # ---- step 4: DRESSING (gd_seam_dress.py's own functions, unchanged) ---------------------------
    log("\nSTEP 4 -- DRESSING (gd_seam_dress.assign_dressing / resolve_plan_writes / compute_dress)")
    null = SNR.part_b()
    dress_core = retile_touched if retile_touched else footprint
    dress = build_dressing(dress_core, blocks_retiled, DRESS_SEED, null, game_root)
    report["dressing"] = dict(
        core=[list(b) for b in dress_core],
        n_straddle_eligible=len(dress["eligible"]["straddle_eligible"]),
        n_fringe_eligible={k: len(v) for k, v in dress["eligible"]["fringe_eligible"].items()},
        n_planned=len(dress["plan"]), n_writes=len(dress["writes"]),
        footprint_bytes=dress["footprint_bytes"], touched_blocks=[list(b) for b in dress["touched"]])
    log(f"  dressing: {len(dress['eligible']['straddle_eligible'])} straddle-eligible + "
       f"{sum(len(v) for v in dress['eligible']['fringe_eligible'].values())} fringe-eligible cells; "
       f"{len(dress['plan'])} planned, {dress['footprint_bytes']}B footprint across "
       f"{len(dress['touched'])} block(s)")
    gate(gates, "dressing plan is non-empty (STRIPS(grass,desert) decals were actually placed)",
        len(dress["plan"]) > 0, f"n_planned={len(dress['plan'])}")

    straddle_plan = [p for p in dress["plan"] if p["kind"] == "straddle"]
    row1_ct = sum(1 for p in straddle_plan if p["row"] == 1)
    row3_ct = sum(1 for p in straddle_plan if p["row"] == 3)
    fringe_dressed = {fam: sum(1 for p in dress["plan"] if p["kind"] == "fringe" and p["fam"] == fam)
                      for fam in ("grass", "desert")}
    fringe_elig_n = {fam: len(dress["eligible"]["fringe_eligible"].get(fam, [])) for fam in ("grass", "desert")}
    stats_vs_null = dict(
        straddle_row1=row1_ct, straddle_row3=row3_ct,
        straddle_ratio=(round(row1_ct / row3_ct, 4) if row3_ct else None),
        null_straddle_ratio=null["straddle_row1_row3_ratio"],
        fringe_dressed=fringe_dressed, fringe_eligible=fringe_elig_n,
        realized_coverage={fam: (round(fringe_dressed[fam] / fringe_elig_n[fam], 4) if fringe_elig_n[fam] else None)
                           for fam in ("grass", "desert")},
        null_coverage={fam: null["per_family_depth1_coverage"][fam]["rate"] for fam in ("grass", "desert")})
    report["dressing_stats_vs_null"] = stats_vs_null
    log(f"  dressing stats vs null bands: {stats_vs_null}")

    engine_selftest = GD.engine_selftest(DRESS_SEED, null)
    report["engine_selftest"] = engine_selftest
    gate(gates, "gd_seam_dress engine self-test: realized straddle/fringe rates converge on the "
        "null-cluster targets (N=4000/phase, synthetic cell-ids)", engine_selftest["ok"],
        f"{engine_selftest}")

    final_blocks = dress["new_blocks"]
    report["final_blocks_touched_total"] = len(set(retile_touched) | set(dress["touched"]))

    # ---- step 5: GATE SUITE over the FINAL composed set --------------------------------------------
    log("\nSTEP 5 -- GATE SUITE (final composed set)")

    # 5a. THE ORPHAN GATE (0/0 mandatory, ring-true)
    final_cell_meshes = {blk: [("Terrain", bm)] for blk, bm in final_blocks.items() if blk in footprint}
    provider = make_context_provider(final_blocks, game_root)
    orphan = OG.orphan_decal_gate(final_cell_meshes, footprint, enforce=True, redress=False,
                                  context_provider=provider)
    gate(gates, "THE ORPHAN GATE: 0 orphans / 0 ambiguous over the FULL final composed footprint "
        "(ring-true against the mint's own neighbourhood)",
        orphan["n_orphans"] == 0 and orphan["n_ambiguous"] == 0, f"{orphan}")
    report["orphan_gate"] = orphan

    # 5b. wang-carry gate (this mint's own sea-layer composition: hidden Sea1/2/3/5 + the real
    #     hole-patched full-cell Sea4 plane -- identical structure to every prior world-island mint;
    #     a fresh mint is not a CROP of a Wang region, so this is the expected-and-confirmed-clean case)
    sea_by_cell = {}
    for blk in footprint:
        bx, by = blk
        hidden = {p.lower(): M.hidden_block_mesh(name=f"Block[{bx}][{by}] {p}", disc=1, x=bx, y=by)
                 for p in ("Sea1", "Sea2", "Sea3", "Sea5")}
        hidden["sea4"] = _mint_sea4(plane, bx, by)
        sea_by_cell[blk] = hidden
    wang = TP.wang_carry_gate(sea_by_cell, footprint, enforce=True)
    gate(gates, "wang-carry gate: 0 incoherent frame edges (a fresh mint, not a Wang-region crop)",
        wang["ok"] and wang["incoherent"] == 0, f"{wang}")
    report["wang_gate"] = wang

    # 5c. MOD-OVERWRITE gate (transplant._mod_overwrite_gate, real reader)
    cell_donors = {blk: ANCHOR_A_DONOR for blk in footprint}   # every non-beach block's Donor.txt = (0,0)
    mod_ow = TP._mod_overwrite_gate(MOD, cell_donors, disc=1, game=game_root)
    gate(gates, "MOD-OVERWRITE gate (transplant._mod_overwrite_gate, real disk read)", mod_ow["ok"],
        f"{mod_ow}")
    report["mod_overwrite_gate"] = mod_ow

    # 5d. GRID-BOUNDS (final)
    gate(gates, "GRID-BOUNDS (final): every block in the composed set is inside the 24x20 grid",
        all(_block_in_grid(b) for b in final_blocks), "")

    # 5e. byte-level sanity: THE FLAT-MESH INVARIANT + THE SEA-LAYER LAW
    flat_bad = []
    for blk, bm in final_blocks.items():
        if bm.vcount != len(bm.flat_index) or len(bm.flat_index) != 3 * len(bm.tris):
            flat_bad.append((blk, bm.vcount, len(bm.flat_index), len(bm.tris)))
    for blk in footprint:
        s4 = sea_by_cell[blk]["sea4"]
        if s4.vcount != len(s4.flat_index) or len(s4.flat_index) != 3 * len(s4.tris):
            flat_bad.append((("Sea4", blk), s4.vcount, len(s4.flat_index), len(s4.tris)))
    gate(gates, "byte sanity: THE FLAT-MESH INVARIANT (vcount==len(flat_index)==3*len(tris)) on every "
        "produced Terrain + Sea4 mesh", not flat_bad, f"{flat_bad[:6]}")

    sea_y_bad = []
    for blk in footprint:
        s4 = sea_by_cell[blk]["sea4"]
        bad = [v[1] for v in s4.verts if abs(v[1]) > 1e-6]
        if bad:
            sea_y_bad.append((blk, bad[:4]))
    gate(gates, "byte sanity: THE SEA-LAYER LAW (every Sea4 vertex Y==0)", not sea_y_bad, f"{sea_y_bad[:6]}")

    hidden_y_bad = []
    for blk in footprint:
        for pname, bm in sea_by_cell[blk].items():
            if pname == "sea4":
                continue
            if any(v[1] > OG.STUB_Y_FLOOR for v in bm.verts):
                hidden_y_bad.append((blk, pname))
    gate(gates, "byte sanity: every hidden/blanked sea part sits below the STUB_Y_FLOOR blanking "
        "convention (never real terrain)", not hidden_y_bad, f"{hidden_y_bad[:6]}")

    n_fail = sum(1 for g in gates if not g["ok"])
    report["gates"] = gates
    report["n_gates"] = len(gates)
    report["n_failed"] = n_fail
    log(f"\n=== {len(gates)} gates, {n_fail} FAILED ===")

    return dict(report=report, footprint=footprint, final_blocks=final_blocks, sea_by_cell=sea_by_cell,
               cell_donors=cell_donors, n_fail=n_fail, built=built)


def _mint_sea4(plane, bx, by):
    import dataclasses
    return dataclasses.replace(plane, x=bx, y=by, name=f"Block[{bx}][{by}] Sea4")


def enumerate_live_deployed_blocks(game_root: Path) -> list:
    return GD.enumerate_deployed_terrain_blocks(game_root)


def connected_components(blocks: list) -> list:
    return GD.connected_components(blocks)


# ================================================================================================
# 5. WRITE THE FILE SET -- dry-run: out/mixed_biome_mint/<mod_folder>/... (never the game install);
#    --apply: the real game install, backup-first, then auto_mirror.
# ================================================================================================
def _hidden_parts_for(bx, by):
    return {p: M.hidden_block_mesh(name=f"Block[{bx}][{by}] {p}", disc=1, x=bx, y=by)
           for p in ISL.HIDDEN_PARTS}


def build_file_set(comp: dict) -> dict:
    """{(bx,by): {part_name: BlockMesh}} + {(bx,by): "dx,dy"} for the Donor.txt sidecars -- the
    COMPLETE would-be-deployed file set for this mint (Terrain + Sea4 + the blanked HIDDEN_PARTS +
    Donor.txt on every footprint block; the anchors' own ensemble parts too, if any)."""
    files = {}
    for blk in comp["footprint"]:
        bx, by = blk
        parts = {"Terrain": comp["final_blocks"][blk], "Sea4": comp["sea_by_cell"][blk]["sea4"]}
        for p in ISL.HIDDEN_PARTS:
            parts[p] = comp["sea_by_cell"][blk].get(p.lower()) or M.hidden_block_mesh(
                name=f"Block[{bx}][{by}] {p}", disc=1, x=bx, y=by)
        files[blk] = parts
    donors = {blk: comp["cell_donors"][blk] for blk in comp["footprint"]}
    # NOTE -- anchor ENSEMBLE aux parts (Object/Falls/River/RiverJoint): Uaho + the crag are both
    # object-only donors (confirmed this build -- report["anchors"][i]["has_ensemble_parts"] reads
    # False for both), so neither anchor produced any. A future donor swap to an ensemble-class
    # massif (e.g. the horseshoe) would need those parts written too -- deliberately NOT implemented
    # here since it is dead code against the two donors this composition actually uses; the report's
    # ``has_ensemble_parts`` flag makes a silent gap impossible to miss.
    return {"files": files, "donors": donors}


def write_dry_run(comp: dict) -> dict:
    fileset = build_file_set(comp)
    if OUT_ROOT.exists():
        shutil.rmtree(OUT_ROOT)
    written = []
    for blk, parts in sorted(fileset["files"].items()):
        bx, by = blk
        for part_name, bm in parts.items():
            rel = M.override_relpath(1, bx, by, "0_1", part_name)
            path = OUT_ROOT / MOD / rel
            M.write_ff9mesh(bm, path)
            written.append(str(path))
        donor = fileset["donors"][blk]
        rel_d = M.donor_sidecar_relpath(1, bx, by, "0_1")
        dpath = OUT_ROOT / MOD / rel_d
        dpath.parent.mkdir(parents=True, exist_ok=True)
        dpath.write_text(f"{donor[0]},{donor[1]}", encoding="utf-8")
        written.append(str(dpath))
    manifest = {"mod_folder": MOD, "written": written, "footprint": [list(b) for b in comp["footprint"]],
               "note": "dry-run file set -- would-be-deployed bytes, written under out/mixed_biome_mint/ "
                       "instead of the game install. Every path here is RELATIVE-equivalent to "
                       f"<game>/{MOD}/... under --apply."}
    (HERE / "out" / "mixed_biome_mint_manifest.json").write_text(
        json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"\nDRY-RUN file set: {len(written)} file(s) -> {OUT_ROOT}")
    return manifest


# ================================================================================================
# --apply / --revert (owner-gated; NOT invoked by this workflow)
# ================================================================================================
def apply_deploy(comp: dict, game_root: Path) -> int:
    if comp["n_fail"]:
        sys.exit(f"REFUSING --apply: {comp['n_fail']} dry-run gate(s) failed")
    fileset = build_file_set(comp)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = BACKUP_ROOT / f"mixed-biome-mint.{ts}"
    # THE MOD-OVERWRITE GATE already proved every target block is virgin (0 pre-existing files), so
    # a 0-file backup here is the EXPECTED good outcome (unlike comp1_orphan_redress.py's/
    # gd_seam_dress.py's "modify existing content" convention, where 0 backed-up files is a hard
    # refuse) -- this loop still backs up ANY file that unexpectedly already exists, as a defense-in-
    # depth net, and refuses on a backup failure exactly like the precedent scripts.
    pre_existing = []
    for blk, parts in fileset["files"].items():
        for part_name in parts:
            p = game_root / MOD / M.override_relpath(1, blk[0], blk[1], "0_1", part_name)
            if p.exists():
                pre_existing.append(p)
        dp = game_root / MOD / M.donor_sidecar_relpath(1, blk[0], blk[1], "0_1")
        if dp.exists():
            pre_existing.append(dp)
    if pre_existing:
        backup_root.mkdir(parents=True, exist_ok=True)
        try:
            for p in pre_existing:
                rel = p.relative_to(game_root)
                dst = backup_root / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, dst)
        except Exception as e:
            sys.exit(f"REFUSING to write: backup of {len(pre_existing)} pre-existing file(s) failed "
                     f"({e}); nothing was touched.")
        print(f"backed up {len(pre_existing)} pre-existing file(s) -> {backup_root} "
             f"(unexpected -- MOD-OVERWRITE should have shown 0)")
    else:
        print("0 pre-existing target files (expected -- MOD-OVERWRITE confirmed virgin territory); "
             "no backup needed, deploying brand-new content.")

    written = []
    for blk, parts in sorted(fileset["files"].items()):
        for part_name, bm in parts.items():
            written.append(M.deploy_override(bm, mod_folder=MOD, game=game_root, part=part_name))
        donor = fileset["donors"][blk]
        written.append(M.deploy_donor_sidecar(donor[0], donor[1], mod_folder=MOD, disc=1,
                                              x=blk[0], y=blk[1], game=game_root))
    mirror_summary = DM.auto_mirror(written, mod_folder=MOD)
    print(f"deployed {len(written)} file(s); disc-4 mirror: {mirror_summary}")

    manifest = {"mod_folder": MOD, "written": [str(p) for p in written],
               "pre_existing_backed_up": [str(p) for p in pre_existing], "backup_dir": str(backup_root),
               "mirror_summary": mirror_summary, "footprint": [list(b) for b in comp["footprint"]]}
    (BACKUP_ROOT / f"mixed-biome-mint.{ts}.manifest.json").parent.mkdir(parents=True, exist_ok=True)
    (BACKUP_ROOT / f"mixed-biome-mint.{ts}.manifest.json").write_text(
        json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"revert manifest -> mixed-biome-mint.{ts}.manifest.json (pass its stem to --revert)")
    return 0


def revert_deploy(name: str) -> int:
    manifest_path = BACKUP_ROOT / f"{name}.manifest.json"
    if not manifest_path.is_file():
        sys.exit(f"no such manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    game_root = Path(_cfg.find_game_path(None))
    backup_root = Path(manifest["backup_dir"])
    backed_up = {str(Path(p)) for p in manifest.get("pre_existing_backed_up", [])}
    n_restored = n_deleted = 0
    for p_str in manifest["written"]:
        p = Path(p_str)
        if p_str in backed_up and backup_root.is_dir():
            rel = p.relative_to(game_root)
            src = backup_root / rel
            if src.is_file():
                p.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, p)
                n_restored += 1
                continue
        if p.exists():
            p.unlink()
            n_deleted += 1
    print(f"reverted: {n_restored} file(s) restored from backup, {n_deleted} brand-new file(s) deleted")
    return 0


# ================================================================================================
# main
# ================================================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write + backup + mirror (owner-gated)")
    ap.add_argument("--revert", metavar="NAME", default=None,
                    help="revert a prior --apply via its manifest stem (mixed-biome-mint.<ts>)")
    args = ap.parse_args()

    if args.revert:
        return revert_deploy(args.revert)

    game_root = Path(_cfg.find_game_path(None))
    comp = compose(game_root)
    report = comp["report"]

    write_dry_run(comp)

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    print(f"\n-> {OUT_JSON}")

    if args.apply:
        return apply_deploy(comp, game_root)

    print("\nDRY-RUN only -- nothing written to the game install.")
    return 0 if comp["n_fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
