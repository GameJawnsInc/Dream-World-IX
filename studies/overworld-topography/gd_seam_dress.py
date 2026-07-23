"""THE SEAM DRESSING -- RUNG B of the desert|grass seam-dressing arc (2026-07-22).

Read first: ``GROUND-FAMILY-DECODE-2026-07-19.md`` Round 10 ("THE DESERT|GRASS COMBINING LANGUAGE
DECODED", its 8 laws) + its 3 redress addenda; ``comp1_orphan_redress.py`` (the FIX-G precedent this
script's dressing pass is the MIRROR IMAGE of); ``ff9mapkit/world/orphangate.py`` (the productized
law-checker this script both consults for ELIGIBILITY and is graded against for CORRECTNESS); and
this same directory's ``seam_null_recon.py`` (the read-only bytes pass that first measured the
things this script needs: the live (7,19)/(8,19) target's actual geometry, and the TRANSPLANT-NULL
statistics at the real grass|desert cluster (13-15,11-12)).

THE HEADLINE FINDING THIS SCRIPT REPRODUCES INDEPENDENTLY (see ``find_eligible`` / ``build_and_gate``
below -- run fresh from CURRENT deployed bytes every invocation, never trusted from a cached JSON):
block(7,19) [grass islet] and block(8,19) [the "plain desert islet"] do NOT touch. Each is its own
rock/cliff-walled landmass; live mesh-content footprints leave a 32-world-unit open-water gap between
them (``seam_null_recon.py``'s own ``ground_truth_geometry`` block). Consequently there is ZERO
straddle cell and ZERO fringe cell eligible for a lawful ``STRIPS(grass,desert)`` decal at that pair
under Round-10's own Laws 2/3/6 -- run through the SAME ``ff9mapkit.world.orphangate.row_lawfulness``
the productized orphan gate itself calls to judge an EXISTING decal's legitimacy. Dressing a seam
that structurally does not exist would fabricate a decal with no lawful donor context -- exactly the
comp[1] orphan-decal defect class, in reverse. So THE TOOL BELOW IS GENERIC (parameterized on
``--core``, never hand-picked to any one pair of blocks): it correctly finds 0 eligible cells for the
brief's own nominal target and REFUSES to write anything there, while remaining ready to dress a
GENUINE touching grass|desert seam the moment one exists in the deployed mod (none currently does --
see the full-deployed-footprint sweep this script also runs, below).

THE ASSIGNMENT RULE (deterministic, seeded -- the ``grassland.assign_mains`` precedent, never a
per-cell hand pick):
  * ELIGIBILITY (which cells even qualify) is the SAME instrument the orphan gate itself judges
    existing decals with: ``orphangate.row_lawfulness(cell, ('grass','desert'), row, fam, cell_fams)``
    -- called here in the FORWARD direction ("if I placed this row here, would the gate call it
    lawful?") instead of the REVERSE direction the gate itself uses ("is this EXISTING decal
    lawful?"). Using the identical function guarantees self-consistency: any cell this script chooses
    to dress is, by construction, a cell the gate will read back as lawful.
      - straddle rows {1,3}: eligible iff the cell is a genuine same-cell grass+desert split
        (Law 2) and not already dressed.
      - fringe rows {0,2}: eligible iff the partner family sits within the gate's own
        ``ACCEPT_RADIUS`` (2 cells -- Law 4's modal-1, generously re-verified) and not already
        dressed.
  * ASSIGNMENT (which row / whether to dress at all a fringe cell) is a SEEDED draw, one
    ``random.Random`` stream per phase (``f"{seed}:straddle"`` / ``f"{seed}:fringe"``), consumed in
    ``sorted(cell)`` order (matching ``assign_mains``'s own determinism-by-sorted-iteration
    convention) -- NEVER by cell identity or hand pick:
      - straddle: draw row 1 with probability p1 = null_row1 / (null_row1 + null_row3) (the
        TRANSPLANT-NULL's own measured ratio, 67:36 = 0.6505), else row 3. Per Law 2's own finding
        ("row0 a rare, unexplained exception; row2 NEVER observed on a straddle") this script
        deliberately synthesizes ONLY the two dominant rows -- the documented exceptions are real
        stock content, not a rule this tool is asked to reproduce.
      - fringe: draw Bernoulli(p = null per-family depth-1 coverage rate: grass 0.7438, desert
        0.8945) per eligible cell; only dress on a hit. This is what keeps the result from reading as
        "mechanically over-regular" (risk #4 in the arc's own brief) -- real stock dressing is
        75-90%, not 100%, of its eligible fringe band.
      - orientation (``ori``) for every dressed cell: ``grassland.assign_mains({cell},
        seed=orphangate.DEFAULT_REDRESS_SEED)`` -- the SAME 0xF93 seed and the SAME per-cell call the
        shipped ``GroundRetile`` "recovered" path and the FIX-G precedent both use, so a synthesized
        cell's orientation is drawn from the identical policy an adjacent RECOVERED cell in the same
        build would use.

THE REDRESS SHAPE (FIX-G, reversed): UV + topo ONLY, zero geometry -- vertex positions, normals, and
tangent[1:] (y/z/w) are never touched, on EXISTING triangles only (the walkmesh's own diagonal split
already there; no new vertex, no new triangle, no carried content). UV comes from
``orphangate._strip_uv_for_pair`` (the EXACT inverse of the gate's own ``classify_strip_tri`` forward
decode -- a tri this script writes and then re-classifies through that SAME function will read back
its OWN intended (pair, row)). Topo follows **LAW 6** (`GROUND-FAMILY-DECODE-2026-07-19.md:1706-1712`,
"THE FLUSH-LOWLAND / TOPO-16-ONLY SCOPE LAW"): at a genuine grass|desert boundary the desert side is
topo **16** (never 17/19/20 -- 17 is desert's own FAR-INTERIOR mains topo, the opposite direction of
``comp1_orphan_redress``'s own fix, which pushed an ORPHANED decal's topo 16->17 because THAT region
had no genuine boundary at all) and the grass side stays topo **0** unconditionally ("grass is
topo-0"). event/area/flags are read off the tri's own existing idall and carried through unchanged.

POST-CHECKS (in-process, every run):
  (a) ``orphangate.orphan_decal_gate`` over the in-memory dressed result (+ its own real 1-block
      Moore ring, read-only) must read 0 orphans / 0 ambiguous -- the SAME law-checker that judged
      all 3 in-game-proven comp[1] redress rounds.
  (b) the realized dressing statistics (straddle row ratio, per-family fringe coverage) are reported
      against the null-cluster bands; because the brief's own nominal target has 0 eligible cells,
      this script ALSO runs a synthetic-cell-id ENGINE SELF-TEST (``engine_selftest`` -- explicitly
      NOT real content, N=4000 fake straddle + N=4000x2 fake fringe cells) that validates the
      assignment function's REALIZED rates converge on the null-cluster targets it was calibrated
      from, within tolerance.
  (c) byte-diff confinement: only the UV(8B)+idall(4B) window of each touched vertex may change
      (checked in-memory pre-write via the exact-verts/-normals-untouched + every-OTHER-vertex-
      untouched gates ``comp1_orphan_redress.py`` uses, and on-disk post-``--apply`` via
      ``comp1_orphan_redress._byte_diff_ranges`` / ``_expected_byte_windows``).

ALSO RUNS EVERY INVOCATION -- ``sweep_all_deployed``: a full census of every CURRENTLY deployed
Terrain override block (enumerated fresh off disk, never a hardcoded list), grouped into connected
(block-grid-adjacent) components, each run through the SAME ``find_eligible`` this script uses for
its named ``--core`` target. This directly answers whether Rung B is applicable ANYWHERE in the
current install, not just at the brief's one named pair -- see the printed/JSON report.

SAFETY / CONVENTIONS -- matches ``comp1_orphan_redress.py`` EXACTLY:
  Run (DRY-RUN, default -- reads only, touches nothing):
    py studies/overworld-topography/gd_seam_dress.py
    py studies/overworld-topography/gd_seam_dress.py --core 7,19 8,19     (explicit, == the default)
  APPLY (backs up first, refuses on backup failure, writes + mirrors + post-checks -- NOT run by this
  workflow; the harness this script ships in is dry-run-only by hard rule):
    py studies/overworld-topography/gd_seam_dress.py --apply
  REVERT a prior --apply from its backup dir:
    py studies/overworld-topography/gd_seam_dress.py --revert gd-seam-dress.20260722-140501
  Artifact -> out/gd_seam_dress.json
"""
from __future__ import annotations

import argparse
import copy
import json
import random
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit import config as _cfg                    # noqa: E402
from ff9mapkit.world import discmirror as DM             # noqa: E402
from ff9mapkit.world import extract as X                 # noqa: E402
from ff9mapkit.world import grassland as GL              # noqa: E402
from ff9mapkit.world import mesh as M                     # noqa: E402
from ff9mapkit.world import orphangate as OG              # noqa: E402

import comp1_orphan_redress as CR                        # noqa: E402  (backup/diff/revert plumbing)
import seam_null_recon as SNR                             # noqa: E402  (the TRANSPLANT-NULL census)

MOD = "FF9CustomMap-world"
OUT = HERE / "out" / "gd_seam_dress.json"
BACKUP_ROOT = REPO_ROOT / "backups"

GD_PAIR = ("grass", "desert")
STRIP_GRASS_TOPO = GL.GROUNDS["grass"]["topo"]     # == 0, unconditionally (Law 6: "grass is topo-0")
STRIP_DESERT_TOPO = 16                             # Law 6: desert AT a genuine boundary is topo-16,
                                                    # NEVER 17/19/20 (17 = desert's far-interior mains
                                                    # topo -- the opposite direction of comp1's own fix)
DEFAULT_REDRESS_SEED = OG.DEFAULT_REDRESS_SEED     # 0xF93, the FIX-G precedent's own seed
ACCEPT_RADIUS = OG.ACCEPT_RADIUS                   # 2 cells, the gate's own fringe-row search radius
REGION_TOL = 0.005                                 # UV-rect containment slack (comp1_orphan_redress's)

DEFAULT_CORE = [(7, 19), (8, 19)]                  # the brief's own nominal target


# ================================================================================================
# eligibility -- reuses the productized gate's OWN row_lawfulness as the forward-direction check
# ================================================================================================
def load_core_bms(core, game_root: Path) -> dict:
    bms = {}
    for (bx, by) in core:
        rel = M.override_relpath(1, bx, by, part="Terrain")
        path = game_root / MOD / rel
        if not path.exists():
            raise FileNotFoundError(f"expected deployed override missing: {path}")
        bms[(bx, by)] = M.blockmesh_from_ff9mesh(path, disc=1, x=bx, y=by, part="terrain")
    return bms


def cell_fams_from_records(records: list) -> dict:
    cf = defaultdict(set)
    for r in records:
        if r["fam"]:
            cf[r["cell"]].add(r["fam"])
    return cf


def find_eligible(core, game_root: Path) -> dict:
    """The ONLY place this script decides "which cells qualify". `core`: list of (bx,by) blocks --
    OURS to write. Reads: the core blocks' LIVE deployed bytes + their real 1-block Moore ring
    (deployed-override-else-stock, via `orphangate.default_context_provider` -- the exact reader
    `--census3` and the gate itself use). READ-ONLY."""
    core_bms = load_core_bms(core, game_root)
    cell_meshes_core = {blk: [("Terrain", bm)] for blk, bm in core_bms.items()}
    core_records = OG.flatten_terrain_records(cell_meshes_core)
    ring_meshes = OG.default_context_provider(core, mod_folder=MOD, game=game_root)
    ring_records = OG.flatten_terrain_records(ring_meshes)
    cell_fams = cell_fams_from_records(core_records + ring_records)

    # cells already wearing ANY grass|desert decal -- never re-dressed (idempotent by construction)
    dressed_cells = set()
    for r in core_records:
        cls = OG.classify_strip_tri(r["world_pts"], r["uv"], r["cell"])
        if cls is not None and cls[0] == GD_PAIR:
            dressed_cells.add(r["cell"])

    core_cell_records = defaultdict(list)   # cell -> [record,...], CORE-only, grass|desert family only
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
        lawful, _detail = OG.row_lawfulness(c, GD_PAIR, row, fam, cell_fams, accept_radius=ACCEPT_RADIUS)
        if lawful:
            fringe_eligible[fam].append(c)
    for fam in fringe_eligible:
        fringe_eligible[fam].sort()

    return dict(core=list(core), core_bms=core_bms, cell_meshes_core=cell_meshes_core,
               core_records=core_records, ring_meshes=ring_meshes, cell_fams=cell_fams,
               dressed_cells=sorted(dressed_cells), core_cell_records=core_cell_records,
               straddle_eligible=straddle_eligible, fringe_eligible=fringe_eligible)


# ================================================================================================
# assignment -- deterministic, seeded, never hand-picked
# ================================================================================================
def assign_dressing(eligible: dict, seed, null: dict) -> list:
    row1_n = null["straddle_row_tally"]["row1"]
    row3_n = null["straddle_row_tally"]["row3"]
    p_row1 = row1_n / (row1_n + row3_n) if (row1_n + row3_n) else 0.5
    cov = {fam: null["per_family_depth1_coverage"][fam]["rate"] for fam in ("grass", "desert")}

    rng_s = random.Random(f"{seed}:straddle")
    rng_f = random.Random(f"{seed}:fringe")
    plan = []
    for cell in sorted(eligible["straddle_eligible"]):
        row = 1 if rng_s.random() < p_row1 else 3
        _cq, co = GL.assign_mains({cell}, seed=DEFAULT_REDRESS_SEED)
        plan.append(dict(cell=list(cell), kind="straddle", row=row, ori=co[cell],
                         rule=f"seeded draw p(row1)={p_row1:.4f} vs null straddle {row1_n}:{row3_n}"))
    for fam, row in (("grass", 0), ("desert", 2)):
        for cell in sorted(eligible["fringe_eligible"].get(fam, [])):
            draw = rng_f.random()
            if draw < cov[fam]:
                _cq, co = GL.assign_mains({cell}, seed=DEFAULT_REDRESS_SEED)
                plan.append(dict(cell=list(cell), kind="fringe", fam=fam, row=row, ori=co[cell],
                                 rule=f"seeded Bernoulli draw={draw:.4f} < null coverage[{fam}]={cov[fam]:.4f}"))
    return plan


def resolve_plan_writes(eligible: dict, plan: list) -> list:
    writes = []
    for p in plan:
        cell = tuple(p["cell"])
        for r in eligible["core_cell_records"].get(cell, []):
            blk = tuple(r["block"])
            bm = eligible["core_bms"][blk]
            old_uv = [list(bm.uvs[j]) for j in r["tri_idx"]]
            old_idall = [int(round(bm.tangents[j][0])) for j in r["tri_idx"]]
            writes.append(dict(cell=list(cell), block=list(blk), tri_idx=list(r["tri_idx"]),
                               fam=r["fam"], row=p["row"], ori=p["ori"],
                               old_uv=old_uv, old_idall=old_idall, rule=p["rule"]))
    return writes


def strip_row_rect(row: int):
    u0, u1 = GL.STRIP_U
    v0, v1 = GL.STRIPS_V[row]
    du, dv = GL.STRIPS[GD_PAIR]["du"], GL.STRIPS[GD_PAIR]["dv"]
    return (round(u0 + du, 5), round(v0 + dv, 5), round(u1 + du, 5), round(v1 + dv, 5))


def compute_dress(bm, ox: float, oz: float, cell, tri_idx: list, fam: str, row: int, ori: int):
    dst_topo = STRIP_GRASS_TOPO if fam == "grass" else STRIP_DESERT_TOPO
    new_uv, new_idall = [], []
    for j in tri_idx:
        wx = bm.verts[j][0] + ox
        wz = bm.verts[j][2] + oz
        uv = list(OG._strip_uv_for_pair(GD_PAIR, wx, wz, cell, row, ori))
        old_idall = int(round(bm.tangents[j][0]))
        d = X.decode_id(old_idall)
        nid = old_idall if d["topograph"] == dst_topo else X.encode_id(d["event"], d["area"], dst_topo, d["flags"])
        new_uv.append(uv)
        new_idall.append(nid)
    return new_uv, new_idall


# ================================================================================================
# build + gate (dry-run always; --apply reuses this, then writes)
# ================================================================================================
def build_and_gate(core, seed, game_root: Path) -> dict:
    GATES: list = []

    def gate(name, ok, detail=""):
        GATES.append((name, bool(ok), detail))
        print(f"GATE [{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
        return bool(ok)

    print("=" * 100)
    print(f"THE SEAM DRESSING -- core={core} seed={seed:#x}")
    print("=" * 100)

    null = SNR.part_b()

    eligible = find_eligible(core, game_root)
    n_straddle = len(eligible["straddle_eligible"])
    n_fringe = sum(len(v) for v in eligible["fringe_eligible"].values())
    n_elig = n_straddle + n_fringe
    print(f"\nELIGIBLE for core {core}: {n_straddle} straddle + {n_fringe} fringe = {n_elig} total "
         f"(already-dressed cells, skipped: {eligible['dressed_cells']})")
    print(f"  straddle_eligible={eligible['straddle_eligible']}")
    print(f"  fringe_eligible={eligible['fringe_eligible']}")

    gate_pre = OG.orphan_decal_gate(eligible["cell_meshes_core"], core, enforce=False, redress=False,
                                    mod_folder=MOD, game=game_root)
    gate("PRE-STATE: the kit orphan gate over the UNCHANGED core reads 0 orphans / 0 ambiguous",
        gate_pre["n_orphans"] == 0 and gate_pre["n_ambiguous"] == 0, f"{gate_pre}")

    if n_elig == 0:
        print("\n*** 0 eligible cells -- no cell in this core passes Round-10 Law 2 (straddle) or "
             "Law 3/4/6 (fringe -- run through the SAME orphangate.row_lawfulness the productized "
             "gate itself calls to judge an EXISTING decal). Nothing is planned or written for this "
             "core. This is the correct, non-fabricating result for a target lacking genuine "
             "family-boundary context -- inventing a decal here would repeat the comp[1] "
             "orphan-decal defect class in reverse (a decal with no lawful donor context). ***")
        n_fail = sum(1 for _, ok, _ in GATES if not ok)
        out = dict(core=[list(b) for b in core], seed=seed, n_eligible=0,
                  straddle_eligible=[], fringe_eligible={"grass": [], "desert": []},
                  plan=[], writes=[], footprint_bytes=0, gate_pre=gate_pre,
                  n_gates=len(GATES), n_failed=n_fail,
                  gates=[{"name": n, "ok": ok, "detail": str(d)} for n, ok, d in GATES], deployed=False)
        return dict(core=core, n_eligible=0, plan=[], writes=[], bms={}, new_bms={}, blocks=[],
                   n_fail=n_fail, null=null, out=out)

    plan = assign_dressing(eligible, seed, null)
    writes = resolve_plan_writes(eligible, plan)
    elig_set = set(eligible["straddle_eligible"]) | {c for v in eligible["fringe_eligible"].values() for c in v}
    gate("every planned write's cell is inside the eligibility set (no write outside it)",
        all(tuple(w["cell"]) in elig_set for w in writes))

    blocks = sorted({tuple(w["block"]) for w in writes})
    bms = eligible["core_bms"]
    new_bms = {blk: copy.deepcopy(bm) for blk, bm in bms.items() if blk in blocks}
    origins = {blk: X.block_world_origin(*blk) for blk in blocks}
    footprint_bytes = 0
    for w in writes:
        blk, cell, tri_idx = tuple(w["block"]), tuple(w["cell"]), w["tri_idx"]
        ox, oz = origins[blk]
        new_uv, new_idall = compute_dress(bms[blk], ox, oz, cell, tri_idx, w["fam"], w["row"], w["ori"])
        w["new_uv"], w["new_idall"] = new_uv, new_idall
        nb = new_bms[blk]
        for k, j in enumerate(tri_idx):
            changed_idall = new_idall[k] != w["old_idall"][k]
            footprint_bytes += 8 + (4 if changed_idall else 0)
            nb.uvs[j] = new_uv[k]
            if changed_idall:
                old_tan = nb.tangents[j]
                nb.tangents[j] = [float(new_idall[k])] + list(old_tan[1:])
        print(f"  cell{cell} block{blk} fam={w['fam']} row={w['row']} ori={w['ori']} "
             f"tri{tri_idx}: idall {w['old_idall']}->{new_idall}")
    print(f"\ntotal byte footprint: {footprint_bytes} bytes across {len(writes)} touched tri-corners")
    gate(f"byte footprint <= 12B/corner (8B uv + 4B idall): {footprint_bytes}B / {len(writes)} corners",
        footprint_bytes <= len(writes) * 3 * 12)

    geom_ok, other_ok = True, True
    other_detail = {}
    for blk in blocks:
        bm0, bm1 = bms[blk], new_bms[blk]
        if bm0.verts != bm1.verts or bm0.normals != bm1.normals:
            geom_ok = False
        changed = {j for w in writes if tuple(w["block"]) == blk for j in w["tri_idx"]}
        bad = [j for j in range(bm0.vcount) if j not in changed
              and (bm0.uvs[j] != bm1.uvs[j] or bm0.tangents[j] != bm1.tangents[j])]
        if bad:
            other_ok = False
            other_detail[str(blk)] = bad[:8]
    gate("zero vertex/normal motion anywhere (verts+normals byte-identical, every touched block)", geom_ok)
    gate("every OTHER vertex's uv+tangent is byte-identical pre/post (only planned corners move)",
        other_ok, f"{other_detail}")

    out_of_region = []
    for w in writes:
        rect = strip_row_rect(w["row"])
        for uv in w["new_uv"]:
            if not (rect[0] - REGION_TOL <= uv[0] <= rect[2] + REGION_TOL
                   and rect[1] - REGION_TOL <= uv[1] <= rect[3] + REGION_TOL):
                out_of_region.append((w["cell"], uv))
    gate("every new UV corner lands inside its assigned STRIPS(grass,desert) row rect (+/-tol)",
        not out_of_region, f"{out_of_region}")

    reclass_bad = []
    for w in writes:
        blk = tuple(w["block"])
        ox, oz = origins[blk]
        wpts = [(bms[blk].verts[j][0] + ox, 0.0, bms[blk].verts[j][2] + oz) for j in w["tri_idx"]]
        cls = OG.classify_strip_tri(wpts, w["new_uv"], tuple(w["cell"]))
        if cls is None or cls[0] != GD_PAIR or cls[1] != w["row"]:
            reclass_bad.append((w["cell"], cls))
    gate("every dressed tri re-classifies, via the SAME OG.classify_strip_tri the gate itself uses, "
        "as (grass,desert) row==the planned row", not reclass_bad, f"{reclass_bad}")

    topo_ok = all(X.decode_id(v)["topograph"] == (STRIP_GRASS_TOPO if w["fam"] == "grass" else STRIP_DESERT_TOPO)
                 for w in writes for v in w["new_idall"])
    gate("new topo == Law 6's boundary topo per family (grass->0, desert->16) for every redressed corner",
        topo_ok)
    eaf_ok = all(CR._same_event_area_flags(o, n) for w in writes for o, n in zip(w["old_idall"], w["new_idall"]))
    gate("event/area/flags preserved bit-for-bit (topo is the only idall field that changes)", eaf_ok)

    full_new_cell_meshes = {blk: [("Terrain", new_bms.get(blk, bms[blk]))] for blk in core}
    gate_post = OG.orphan_decal_gate(full_new_cell_meshes, core, enforce=False, redress=False,
                                     mod_folder=MOD, game=game_root)
    gate("POST-STATE (in-memory, pre-write): the kit orphan gate reads 0 orphans / 0 ambiguous over "
        "the DRESSED result", gate_post["n_orphans"] == 0 and gate_post["n_ambiguous"] == 0, f"{gate_post}")

    straddle_plan = [p for p in plan if p["kind"] == "straddle"]
    row1_ct = sum(1 for p in straddle_plan if p["row"] == 1)
    row3_ct = sum(1 for p in straddle_plan if p["row"] == 3)
    fringe_dressed = {fam: sum(1 for p in plan if p["kind"] == "fringe" and p["fam"] == fam)
                      for fam in ("grass", "desert")}
    fringe_elig_n = {fam: len(eligible["fringe_eligible"].get(fam, [])) for fam in ("grass", "desert")}
    stats_report = dict(
        straddle_row1=row1_ct, straddle_row3=row3_ct,
        straddle_ratio=(round(row1_ct / row3_ct, 4) if row3_ct else None),
        null_straddle_ratio=null["straddle_row1_row3_ratio"],
        fringe_dressed=fringe_dressed, fringe_eligible=fringe_elig_n,
        realized_coverage={fam: (round(fringe_dressed[fam] / fringe_elig_n[fam], 4) if fringe_elig_n[fam] else None)
                           for fam in ("grass", "desert")},
        null_coverage={fam: null["per_family_depth1_coverage"][fam]["rate"] for fam in ("grass", "desert")})
    print(f"\nDRESSING STATS vs NULL BANDS (informational -- n this small makes an exact-match gate "
         f"meaningless; report only): {stats_report}")

    n_fail = sum(1 for _, ok, _ in GATES if not ok)
    print(f"\n=== {len(GATES)} gates, {n_fail} FAILED ===")

    out = dict(core=[list(b) for b in core], seed=seed, n_eligible=n_elig,
              straddle_eligible=[list(c) for c in eligible["straddle_eligible"]],
              fringe_eligible={k: [list(c) for c in v] for k, v in eligible["fringe_eligible"].items()},
              plan=plan, writes=writes, footprint_bytes=footprint_bytes,
              stats_vs_null=stats_report, gate_pre=gate_pre, gate_post=gate_post,
              n_gates=len(GATES), n_failed=n_fail,
              gates=[{"name": n, "ok": ok, "detail": str(d)} for n, ok, d in GATES], deployed=False)
    return dict(core=core, n_eligible=n_elig, plan=plan, writes=writes, bms=bms, new_bms=new_bms,
               blocks=blocks, n_fail=n_fail, null=null, out=out)


# ================================================================================================
# engine self-test -- synthetic cell ids ONLY (never real content), validates the assignment
# function's realized rates converge on the null-cluster targets it draws from
# ================================================================================================
def engine_selftest(seed, null: dict) -> dict:
    N = 4000
    fake_eligible = dict(
        straddle_eligible=[(1_000_000 + i, 0) for i in range(N)],
        fringe_eligible={"grass": [(2_000_000 + i, 0) for i in range(N)],
                         "desert": [(3_000_000 + i, 0) for i in range(N)]})
    plan = assign_dressing(fake_eligible, seed, null)
    row1 = sum(1 for p in plan if p["kind"] == "straddle" and p["row"] == 1)
    row3 = sum(1 for p in plan if p["kind"] == "straddle" and p["row"] == 3)
    grass_dressed = sum(1 for p in plan if p["kind"] == "fringe" and p["fam"] == "grass")
    desert_dressed = sum(1 for p in plan if p["kind"] == "fringe" and p["fam"] == "desert")
    target_p1 = null["straddle_row_tally"]["row1"] / (null["straddle_row_tally"]["row1"] + null["straddle_row_tally"]["row3"])
    target_cov = {fam: null["per_family_depth1_coverage"][fam]["rate"] for fam in ("grass", "desert")}
    got_p1 = row1 / (row1 + row3) if (row1 + row3) else None
    got_cov = {"grass": grass_dressed / N, "desert": desert_dressed / N}
    print(f"\nENGINE SELF-TEST (synthetic integer cell-ids, N={N} per phase -- validates the "
         f"assignment function's CALIBRATION only, claims nothing about real terrain):")
    print(f"  straddle row1:row3 ratio -- target p(row1)={target_p1:.4f}  got={got_p1:.4f}")
    print(f"  fringe coverage -- target={target_cov}  got={got_cov}")
    ok = (got_p1 is not None and abs(got_p1 - target_p1) < 0.03
         and all(abs(got_cov[f] - target_cov[f]) < 0.03 for f in target_cov))
    print(f"  self-test {'PASS' if ok else 'FAIL'} (within 3 percentage points at N={N})")
    return dict(n=N, target_p1=target_p1, got_p1=got_p1, target_coverage=target_cov,
               got_coverage=got_cov, ok=ok)


# ================================================================================================
# full-deployed-footprint sweep -- is Rung B applicable ANYWHERE in the current install?
# ================================================================================================
def enumerate_deployed_terrain_blocks(game_root: Path) -> list:
    root = game_root / MOD / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
    if not root.is_dir():
        return []
    pat = re.compile(r"^Block\[(-?\d+)\]\[(-?\d+)\] Terrain\.ff9mesh$")
    blocks = []
    for p in root.rglob("*"):
        if p.is_file():
            m = pat.match(p.name)
            if m:
                blocks.append((int(m.group(1)), int(m.group(2))))
    return sorted(set(blocks))


def connected_components(blocks: list) -> list:
    blockset = set(blocks)
    seen = set()
    comps = []
    for b in sorted(blockset):
        if b in seen:
            continue
        comp = []
        stack = [b]
        seen.add(b)
        while stack:
            c = stack.pop()
            comp.append(c)
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (c[0] + d[0], c[1] + d[1])
                if n in blockset and n not in seen:
                    seen.add(n)
                    stack.append(n)
        comps.append(sorted(comp))
    return comps


def sweep_all_deployed(game_root: Path) -> dict:
    blocks = enumerate_deployed_terrain_blocks(game_root)
    comps = connected_components(blocks)
    print(f"\n{'=' * 100}\nFULL-MOD SWEEP -- {len(blocks)} deployed terrain blocks in {len(comps)} "
         f"connected component(s) (fresh off-disk enumeration), each scanned for grass|desert "
         f"dress-eligibility via the SAME find_eligible this script uses for --core\n{'=' * 100}")
    results = []
    total_eligible = 0
    for comp in comps:
        elig = find_eligible(comp, game_root)
        n_s = len(elig["straddle_eligible"])
        n_f = sum(len(v) for v in elig["fringe_eligible"].values())
        n = n_s + n_f
        total_eligible += n
        print(f"  component {comp}: n_eligible={n} (straddle={n_s} fringe={n_f}) "
             f"straddle_cells={elig['straddle_eligible']} fringe_cells={elig['fringe_eligible']}")
        results.append(dict(blocks=[list(b) for b in comp], n_eligible=n, n_straddle=n_s, n_fringe=n_f,
                            straddle_eligible=[list(c) for c in elig["straddle_eligible"]],
                            fringe_eligible={k: [list(c) for c in v] for k, v in elig["fringe_eligible"].items()}))
    print(f"\nTOTAL eligible grass|desert dress cells across ALL {len(blocks)} deployed terrain "
         f"blocks: {total_eligible}")
    return dict(n_blocks=len(blocks), n_components=len(comps), total_eligible=total_eligible,
               components=results)


# ================================================================================================
# --apply: backup -> write -> mirror -> post-checks (NOT invoked by this workflow -- dry-run only)
# ================================================================================================
def apply_dress(game_root: Path, res: dict, out: dict) -> int:
    writes, blocks = res["writes"], res["blocks"]
    bms, new_bms = res["bms"], res["new_bms"]
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = BACKUP_ROOT / f"gd-seam-dress.{ts}"
    try:
        n_bk = CR.backup_files(game_root, blocks, backup_root)
    except Exception as e:
        sys.exit(f"REFUSING to write: backup failed ({e}); nothing was touched.")
    if n_bk == 0:
        sys.exit("REFUSING to write: backup copied 0 files (unexpected); aborting before any write.")
    print(f"\nbacked up {n_bk} file(s) -> {backup_root}")

    before_bytes = {}
    written = []
    for blk in blocks:
        rel = M.override_relpath(1, blk[0], blk[1], part="Terrain")
        path = game_root / MOD / rel
        before_bytes[blk] = path.read_bytes()
        p = M.deploy_override(new_bms[blk], mod_folder=MOD, part="Terrain")
        written.append(p)
        print(f"  wrote {p}")

    mirror_summary = DM.auto_mirror(written, mod_folder=MOD)
    print(f"  disc-4 mirror summary: {mirror_summary}")

    post_gates = []

    def pg(name, ok, detail=""):
        post_gates.append({"name": name, "ok": bool(ok), "detail": str(detail)})
        print(f"POST [{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))

    core = res["core"]
    core_bms_post = {blk: M.blockmesh_from_ff9mesh(
        game_root / MOD / M.override_relpath(1, blk[0], blk[1], part="Terrain"),
        disc=1, x=blk[0], y=blk[1], part="terrain") for blk in core}
    cell_meshes_post = {blk: [("Terrain", bm)] for blk, bm in core_bms_post.items()}
    gate_post_disk = OG.orphan_decal_gate(cell_meshes_post, core, enforce=False, redress=False,
                                          mod_folder=MOD, game=game_root)
    pg("POST re-classify (disk read-back): 0 orphans / 0 ambiguous",
      gate_post_disk["n_orphans"] == 0 and gate_post_disk["n_ambiguous"] == 0, f"{gate_post_disk}")

    diff_report = {}
    all_diffs_ok = True
    for blk in blocks:
        rel = M.override_relpath(1, blk[0], blk[1], part="Terrain")
        after = (game_root / MOD / rel).read_bytes()
        before = before_bytes[blk]
        diffs = CR._byte_diff_ranges(before, after)
        touched = {j for w in writes if tuple(w["block"]) == blk for j in w["tri_idx"]}
        windows = CR._expected_byte_windows(bms[blk], touched)
        bad = CR._bytes_outside_windows(diffs, windows)
        diff_report[str(blk)] = dict(n_diff_ranges=len(diffs), n_expected_windows=len(windows),
                                     n_diff_bytes=sum(e - s for s, e in diffs),
                                     n_window_bytes=sum(w1 - w0 for w0, w1 in windows),
                                     out_of_expected_bytes=bad)
        if bad:
            all_diffs_ok = False
    pg("byte-diff vs backup confined to the UV(8B)+idall(4B) windows of the dressed corners",
      all_diffs_ok, f"{diff_report}")

    n_post_fail = sum(1 for g in post_gates if not g["ok"])
    out["deployed"] = True
    out["backup_dir"] = str(backup_root)
    out["written"] = [str(p) for p in written]
    out["mirror_summary"] = mirror_summary
    out["post_gates"] = post_gates
    print(f"\n=== APPLY complete: {len(post_gates)} post-gates, {n_post_fail} FAILED ===")
    return n_post_fail


# ================================================================================================
# main
# ================================================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--core", nargs="+", default=None,
                    help="target block(s) as 'x,y' tokens; default: 7,19 8,19 (the brief's own "
                         "nominal seam)")
    ap.add_argument("--seed", type=lambda s: int(s, 0), default=DEFAULT_REDRESS_SEED,
                    help="seed for the deterministic row/coverage draws (default 0xF93)")
    ap.add_argument("--apply", action="store_true", help="write + backup + mirror + post-check")
    ap.add_argument("--revert", metavar="BACKUP_DIR", default=None,
                    help="restore every file from a prior --apply's backup dir")
    ap.add_argument("--no-sweep", action="store_true",
                    help="skip the full-deployed-footprint eligibility sweep")
    args = ap.parse_args()

    if args.revert:
        return CR.revert_from_backup(args.revert)

    game_root = Path(_cfg.find_game_path(None))
    core = DEFAULT_CORE
    if args.core:
        core = [tuple(int(x) for x in tok.split(",")) for tok in args.core]

    res = build_and_gate(core, args.seed, game_root)
    selftest = engine_selftest(args.seed, res["null"])
    sweep = None if args.no_sweep else sweep_all_deployed(game_root)

    out = dict(res["out"])
    out["engine_selftest"] = selftest
    if sweep:
        out["full_mod_sweep"] = sweep

    if args.apply:
        if not res["writes"]:
            print("\nnothing to apply for this core (0 eligible cells / 0 planned writes) -- "
                 "exiting cleanly.")
        else:
            if res["n_fail"]:
                sys.exit(f"REFUSING --apply: {res['n_fail']} dry-run gate(s) failed")
            n_post_fail = apply_dress(game_root, res, out)
            OUT.parent.mkdir(parents=True, exist_ok=True)
            OUT.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
            print(f"\n-> {OUT}")
            return 0 if n_post_fail == 0 else 1
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
        print(f"\n-> {OUT}")
        return 0 if res["n_fail"] == 0 else 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(f"\nDRY-RUN only -- nothing written to the game. Report -> {OUT}")
    return 0 if res["n_fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
