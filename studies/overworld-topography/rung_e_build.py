"""RUNG E BUILD -- the full offline gate suite + the would-be-deployed dry-run file set for the
2-LOBE grass|desert composition (the horseshoe massif UNCHANGED from Rung D, fused through the
reserved (0-2,12-15) corridor arm to a NEW Uaho north anchor), on top of ``rung_e_layout.py``'s
already-run, skeptic-cleared staging (site/anchor/termini/line/retile/dressing/the 4 composition
gates -- imported and RE-EXECUTED here in-process to capture the intermediate in-memory blocks this
script's own gate suite + file-set builder need). ``rung_e_layout.py`` itself is left completely
UNMODIFIED -- single source of truth, imported not duplicated, per the task brief.

Read first: ``rung_e_layout.py`` (the already-proven 2-lobe layout this script re-runs); ``rung_d_
build.py`` (the RATIO-UNIT / orphan / wang-carry / mod-overwrite / grid-bounds / flat-mesh / sea-
layer gate conventions this script mirrors -- the SAME calls, over TWO carved anchors instead of
one); ``mixed_biome_mint.py`` (generate_partition_line / sector_retile / build_dressing / make_
context_provider / _mint_sea4, all reused UNCHANGED via ``rung_e_layout``'s own imports); ``gd_seam_
dress.py`` (the dressing tool -- this script additionally re-verifies its own topo/event-area-flags/
row laws directly against the realized writes, mirroring ``gd_seam_dress.build_and_gate``'s own
post-checks at lines 371-397); ``ff9mapkit/world/interior.py`` (``carve_mountain``'s own gate
constants -- MTN_MAX_EDGE/MTN_ZIP_RISE/MTN_ZIP_NY_FLOOR/MTN_ZIP_BANK_MAX/MTN_ROCK_RIGID/MTN_APRON_
SLOPE -- every "carve gate" below checks a REAL number against one of these, never a re-typed
threshold); ``transplant.py`` (``wang_carry_gate`` / ``effective_prefab_arm`` / ``_mod_overwrite_
gate``, reused UNCHANGED); ``out/contract_gd_composition.json`` (the stock statistics GATE2/GATE3
cite, re-read live by ``rung_e_layout.stage5_composition_gates``, not re-typed here).

THE CARVE-GATE CAPTURE MECHANISM: ``interior.carve_mountain`` does not RETURN a pass/fail dict for
its own internal checks -- it raises ``ValueError`` on failure and only prints the numeric detail
(the "gates: down=... maxEdge=... nearMiss=... annulusOnce=... zipRise=... zipNyMin=... (below-
envelope X/Y) rockRigid=...% apronSlope=...deg" line, interior.py:2159) via its ``log=`` callback.
``rung_e_layout.stage2_massif_anchor``/``stage2b_north_anchor`` already wrap that callback with
``mixed_biome_mint._capturing_log`` (for r_rim only) around the MODULE-LEVEL ``log`` name -- Python
resolves that bare name at CALL time, so this script temporarily monkeypatches ``rung_e_layout.log``
(restored in a ``finally``, never left patched) to ALSO regex-capture the full "gates:" line + the
two placement-probe lines + census_gate's own "MISS=0" line, reaching carve_mountain's real log
stream WITHOUT touching rung_e_layout.py's source. This gives every "carve gate" below TWO
independent, cross-checked pass signals: (a) carve_mountain/census_gate did not raise (proves EVERY
internal condition held, including ones this script does not separately re-derive), and (b) the
captured numbers independently re-evaluated against interior.py's own MTN_* thresholds agree --
exactly the "not two definitions agreeing by coincidence" rigor ``rung_e_layout.py``'s own FIX 2
insists on.

THE "CLEAN-BOUNDARY >=1.5u" GATE NAME, HONESTLY REINTERPRETED: that literal check (``massif_spur.py``
line 332, ``sep < 1.5``) is a SPUR-GRAFT-specific mechanism -- it measures the vertical gap between a
newly-welded synthetic course's low/high chains when grafting ONE NEW course onto existing rock.
``carve_mountain`` does not graft a spur; it carries a WHOLE donor ensemble rigidly, so that literal
1.5u check does not exist in its code path (grep-confirmed: interior.py has no other "1.5" literal).
The carve-native analogue -- boundary CLEANLINESS at the carried patch's own edge -- is the annulus-
crack ("annulusOnce") open-edge count interior.py's own raise-check already gates on (must be 0), read
alongside ``MTN_CLEAR=2.5u`` (the annulus width the zip ring is CONSTRUCTED at, informational context,
not itself a post-hoc gate). Reported below as ``clean_boundary`` with this substitution stated
in-line, not silently swapped in for the schema's word.

DONOR.TXT ASSIGNMENT (a design decision, stated plainly): every footprint block gets its own Terrain
override (this is a LAND mint, not a water-only carry -- confirmed by stage 5's own arm census
below), so no cell here is water-only and ``effective_prefab_arm`` is exercised for COMPLETENESS/
RIGOR rather than because a defect is expected. The massif's own carved span gets the horseshoe
donor_ref (REQUIRED -- that carve produces real ensemble aux parts needing the divert). Every OTHER
footprint block (the Uaho arm span + the plain body/connector blocks neither anchor carved) gets the
Uaho donor (0,0) as the blanket default -- mirroring ``mixed_biome_mint.compose()``'s own identical
choice ("every non-[massif] block's Donor.txt = (0,0)", line 653) for blocks that carry zero ensemble
content of their own (harmless: every part those blocks emit is already its own explicit override, so
Donor.txt's value is inert there, but a Donor.txt file must still exist alongside a Terrain override
per THE MOD-OVERWRITE GATE's own convention).

READ-ONLY AGAINST THE GAME INSTALL. Dry-run (default) writes the complete would-be-deployed file set
to ``out/rung_e/FF9CustomMap-world/...`` (never the game install). ``--apply`` (owner-gated, NEVER
invoked by this workflow) backs up any pre-existing target file first, writes, then auto-mirrors to
Disc4, mirroring ``rung_d_build.py``'s / ``mixed_biome_mint.py``'s own conventions. ``--revert`` undoes
a prior ``--apply`` via its manifest.

Run from the repo root:  py studies/overworld-topography/rung_e_build.py
"""
from __future__ import annotations

import argparse
import re as _re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

import json  # noqa: E402  (after sys.path so `json` resolves normally -- no local shadow exists)

import rung_e_layout as REL                                  # noqa: E402  (single source of truth)

RDL = REL.RDL
MBM = REL.MBM
IN = REL.IN
ISL = REL.ISL
M = REL.M
X = REL.X
_cfg = REL._cfg
OG = MBM.OG
TP = MBM.TP
GD = MBM.GD
SNR = REL.SNR

MOD = "FF9CustomMap-world"
OUT_DIR = HERE / "out" / "rung_e"
OUT_ROOT = OUT_DIR / MOD
OUT_JSON = OUT_DIR / "rung_e_build.json"
BACKUP_ROOT = REPO_ROOT / "backups"

UAHO_DONOR = tuple(REL.UAHO_DONOR)  # (0, 0) -- the blanket Donor.txt for every non-massif block


def gate(gates: list, name, ok, detail="") -> bool:
    gates.append({"name": name, "ok": bool(ok), "detail": str(detail)[:4000]})
    print(f"GATE [{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
    return bool(ok)


def log(msg):
    print(msg)


# ================================================================================================
# STAGE A -- re-run rung_e_layout's own staging in-process (identical inputs/seeds to the already-
# recorded out/rung_e/rung_e_layout.json -- re-verified byte-identical below, not assumed), WITH the
# carve-gate capture wrapper spliced around the two carve_mountain calls.
# ================================================================================================
_GATES_LINE_RE = _re.compile(
    r"gates: down=(\d+) maxEdge=([\-\d.]+) nearMiss=(\d+) annulusOnce=(\d+) zipRise=([\-\d.]+) "
    r"zipNyMin=([\-\d.]+) \(below-envelope (\d+)/(\d+)\) rockRigid=([\-\d.]+)% apronSlope=([\-\d.]+)deg")
_PEAK_RE = _re.compile(r"carried peak grounds: y=([\-\d.]+) (\S+) topo (\d+)")
_WEST_RE = _re.compile(r"ground probe west of the rim: y=([\-\d.]+) (\S+) topo (\d+)")
_MISS0_TEXT = "placement census: MISS=0 in changed blocks"


def _run_with_carve_capture(fn, *args):
    """Temporarily monkeypatches ``rung_e_layout.log`` (see module docstring's CARVE-GATE CAPTURE
    MECHANISM) to regex-capture carve_mountain's own "gates:" line + the two placement-probe lines +
    census_gate's own MISS=0 line, while still printing everything exactly as before. Restored in a
    ``finally`` -- REL.log is never left patched, even on an exception."""
    store = {"census_miss0": False}
    orig = REL.log

    def wrapped(msg):
        orig(msg)
        s = str(msg)
        m = _GATES_LINE_RE.search(s)
        if m:
            store["gates_line"] = dict(
                down=int(m.group(1)), max_edge=float(m.group(2)), near_miss_halved=int(m.group(3)),
                annulus_once=int(m.group(4)), zip_rise=float(m.group(5)), zip_ny_min=float(m.group(6)),
                zip_below_envelope=int(m.group(7)), zip_tris_total=int(m.group(8)),
                rock_rigid_pct=float(m.group(9)), apron_slope_deg=float(m.group(10)))
        mp = _PEAK_RE.search(s)
        if mp:
            store["peak_grounds"] = dict(y=float(mp.group(1)), part=mp.group(2), topo=int(mp.group(3)))
        mw = _WEST_RE.search(s)
        if mw:
            store["west_probe"] = dict(y=float(mw.group(1)), part=mw.group(2), topo=int(mw.group(3)))
        if _MISS0_TEXT in s:
            store["census_miss0"] = True

    REL.log = wrapped
    try:
        result = fn(*args)
    finally:
        REL.log = orig
    return result, store


def run_layout_stages(game_root: Path) -> dict:
    log("#" * 100)
    log("STAGE A -- re-running rung_e_layout's own staging in-process (site/anchors/termini/line/"
        "retile/dressing/4-gates), with carve-gate detail capture around both carve_mountain calls")
    log("#" * 100)
    union = REL.build_union_outline()
    s0 = REL.stage0_site(game_root, union)
    coast_edges = RDL.build_coastline(s0["built"])
    s1 = REL.stage1_contiguity_and_fidelity(s0["built"], union)

    s2, cap2 = _run_with_carve_capture(REL.stage2_massif_anchor, s0["built"], game_root)
    s2b, cap2b = _run_with_carve_capture(REL.stage2b_north_anchor, s2["blocks_now"], game_root)

    s3 = REL.stage3_termini_line_and_retile(s2b["blocks_now"], s0["footprint"], coast_edges,
                                             s2["span_blocks"], s2b["span_blocks"])
    s3r = REL._finish_retile(s2b["blocks_now"], s3["line"], s2["center"])
    s4 = REL.stage4_dressing(s3r["blocks_retiled"], s0["footprint"], s3r["retile_touched"], game_root)
    s5 = REL.stage5_composition_gates(coast_edges, s3r["blocks_retiled"], s0["footprint"], s3["line"],
                                       s3r["retile_stats"], s4["dress"], s2, s2b)
    return dict(union=union, s0=s0, coast_edges=coast_edges, s1=s1, s2=s2, cap2=cap2, s2b=s2b,
                cap2b=cap2b, s3=s3, s3r=s3r, s4=s4, s5=s5)


def check_reproduces_recorded_layout(built_stages: dict) -> dict:
    """Independently confirm this run's own numbers match the already-committed
    ``out/rung_e/rung_e_layout.json`` -- if this script's re-run of the SAME seeded pipeline ever
    drifts from the recorded artifact, that is itself a finding, not something to paper over."""
    recorded_path = OUT_DIR / "rung_e_layout.json"
    recorded = json.loads(recorded_path.read_text(encoding="utf-8"))
    s0, s2, s2b, s3, s3r, s4, s5 = (built_stages[k] for k in ("s0", "s2", "s2b", "s3", "s3r", "s4", "s5"))
    checks = {
        "stage0.gates": (s0["gates"], recorded["stage0_site"]["gates"]),
        "stage2.report.blob_tris": (s2["res"]["report"]["blob_tris"],
                                     recorded["stage2_massif_anchor"]["report"]["blob_tris"]),
        "stage2.report.ensemble_tris": (s2["res"]["report"]["ensemble_tris"],
                                         recorded["stage2_massif_anchor"]["report"]["ensemble_tris"]),
        "stage2b.report.blob_tris": (s2b["res"]["report"]["blob_tris"],
                                      recorded["stage2b_north_anchor"]["report"]["blob_tris"]),
        "stage3.term_a": (list(s3["term_a"]), recorded["stage3_termini_line_retile"]["term_a"]),
        "stage3.term_b": (list(s3["term_b"]), recorded["stage3_termini_line_retile"]["term_b"]),
        "stage3.n_retiled": (s3r["retile_stats"]["n_retiled"],
                              recorded["stage3_termini_line_retile"]["retile_stats"]["n_retiled"]),
        "stage4.n_planned": (len(s4["dress"]["plan"]), recorded["stage4_dressing"]["n_planned"]),
        "stage4.n_writes": (len(s4["dress"]["writes"]), recorded["stage4_dressing"]["n_writes"]),
        "stage5.line_min": (round(s5["gate1_coast_standoff"]["line_min_dist_to_coast"], 2),
                             recorded["summary"]["standoff_line_min_u"]),
        "stage5.ratio_writes": (s5["gate2_dressing_ratio"]["ratio_writes"], recorded["summary"]["ratio_writes"]),
        "stage5.gate3_clean": (s5["gate3_termination_decal"]["clean"], recorded["summary"]["all_4_gates_pass"]
                                and recorded["stage5_composition_gates"]["gate3_termination_decal"]["clean"]),
    }
    mismatches = {k: v for k, v in checks.items() if v[0] != v[1]}
    ok = not mismatches
    log(f"  re-run vs recorded rung_e_layout.json: {'IDENTICAL' if ok else 'DIVERGED'}"
        + (f" -- {mismatches}" if mismatches else ""))
    return dict(ok=ok, mismatches=mismatches)


# ================================================================================================
# STAGE B -- THE CARVE-GATE REPORT (massif + north anchor), re-deriving clean-boundary/zip/apron/
# rock-rigid/holes/walk-legality/scenery-seal from the captured numbers AND from the no-exception
# fact (carve_mountain/census_gate would have raised had any internal condition failed).
# ================================================================================================
def _carve_gate_report(label: str, s: dict, cap: dict, *, ensemble_expected: bool) -> dict:
    gl = cap.get("gates_line")
    if gl is None:
        raise ValueError(f"{label}: could not capture carve_mountain's own 'gates:' log line -- the "
                          f"log line format may have changed (interior.py:2159)")
    rep = s["res"]["report"]

    zip_ok = (gl["zip_rise"] <= IN.MTN_ZIP_RISE and gl["zip_ny_min"] >= IN.MTN_ZIP_NY_FLOOR
              and gl["zip_below_envelope"] <= IN.MTN_ZIP_BANK_MAX)
    apron_ok = gl["apron_slope_deg"] <= IN.MTN_APRON_SLOPE
    rock_rigid_ok = (gl["rock_rigid_pct"] / 100.0) < IN.MTN_ROCK_RIGID
    holes_ok = gl["down"] == 0 and gl["near_miss_halved"] == 0
    clean_boundary_ok = gl["annulus_once"] == 0
    edge_ok = gl["max_edge"] < IN.MTN_MAX_EDGE
    walk_legality_ok = bool(cap.get("census_miss0")) and cap.get("west_probe", {}).get("part") == "Terrain" \
        and cap.get("peak_grounds", {}).get("part") == "Terrain"

    ensemble_parts = s["res"].get("changed_parts") or {}
    has_ensemble = bool(ensemble_parts)
    scenery_seal_bad = []
    if has_ensemble:
        expected_topo = X.decode_id(int(X.encode_id(topograph=49)))["topograph"]
        for blk, parts in ensemble_parts.items():
            for pname, bm in parts.items():
                for tri in bm.tris:
                    idall = int(round(bm.tangents[tri[0]][0]))
                    if X.decode_id(idall)["topograph"] != expected_topo:
                        scenery_seal_bad.append((list(blk), pname))
    scenery_seal_ok = not scenery_seal_bad
    ensemble_expected_matches = has_ensemble == ensemble_expected

    all_ok = all([zip_ok, apron_ok, rock_rigid_ok, holes_ok, clean_boundary_ok, edge_ok,
                  walk_legality_ok, scenery_seal_ok, ensemble_expected_matches])
    log(f"  CARVE GATES [{label}]: zip={'OK' if zip_ok else 'FAIL'} apron={'OK' if apron_ok else 'FAIL'} "
        f"rock_rigid={'OK' if rock_rigid_ok else 'FAIL'} holes={'OK' if holes_ok else 'FAIL'} "
        f"clean_boundary={'OK' if clean_boundary_ok else 'FAIL'} edge={'OK' if edge_ok else 'FAIL'} "
        f"walk_legality={'OK' if walk_legality_ok else 'FAIL'} scenery_seal={'OK' if scenery_seal_ok else 'FAIL'} "
        f"(applicable={has_ensemble}) -> {'ALL PASS' if all_ok else 'SOME FAILED'}")

    return dict(
        label=label, no_exception_raised=True, gates_line=gl,
        peak_grounds=cap.get("peak_grounds"), west_probe=cap.get("west_probe"),
        census_miss0=cap.get("census_miss0"),
        checks=dict(
            zip=dict(ok=zip_ok, zip_rise=gl["zip_rise"], ceiling=IN.MTN_ZIP_RISE,
                     zip_ny_min=gl["zip_ny_min"], floor=IN.MTN_ZIP_NY_FLOOR, envelope=IN.MTN_ZIP_NY_MIN,
                     zip_below_envelope=gl["zip_below_envelope"], bank_max=IN.MTN_ZIP_BANK_MAX,
                     zip_tris_total=gl["zip_tris_total"], report_zip_tris=rep.get("zip_tris")),
            apron=dict(ok=apron_ok, apron_slope_deg=gl["apron_slope_deg"], envelope_deg=IN.MTN_APRON_SLOPE),
            rock_rigid=dict(ok=rock_rigid_ok, rock_rigid_pct=gl["rock_rigid_pct"],
                            ceiling_pct=round(IN.MTN_ROCK_RIGID * 100, 2), report_rock_rigid=rep.get("rock_rigid")),
            holes=dict(ok=holes_ok, down=gl["down"], near_miss_halved=gl["near_miss_halved"],
                      patched_holes=rep.get("patched_holes")),
            clean_boundary=dict(ok=clean_boundary_ok, annulus_once=gl["annulus_once"],
                               construction_annulus_width_u=IN.MTN_CLEAR,
                               note="reinterpreted for a donor-ENSEMBLE carve (interior.carve_mountain "
                               "has no literal 1.5u spur-graft check -- grep-confirmed 'massif_spur.py "
                               "line 332 sep<1.5' is that OTHER mechanism's own synthetic-course-graft-"
                               "specific check, not present anywhere in interior.py). The carve-native "
                               "analogue -- boundary cleanliness at the carried patch's own edge -- is "
                               "the annulus-crack ('annulusOnce') open-edge count interior.py's own "
                               "raise-check gates on (0 required); MTN_CLEAR is the construction-time "
                               "annulus width the zip ring is built at, reported for context, not "
                               "itself a post-hoc pass/fail gate"),
            edge=dict(ok=edge_ok, max_edge=gl["max_edge"], ceiling=IN.MTN_MAX_EDGE),
            walk_legality=dict(ok=walk_legality_ok, census_miss0=cap.get("census_miss0"),
                              west_probe=cap.get("west_probe"), peak_grounds=cap.get("peak_grounds")),
            scenery_seal=dict(ok=scenery_seal_ok, applicable=has_ensemble,
                              n_aux_tris=rep.get("ensemble_tris", 0), bad=scenery_seal_bad[:6],
                              note=("checked: every carried aux-part tri's IDALL decodes to the "
                                    "blocked topo-49 SCENERY_ID (interior.py:2236)") if has_ensemble
                              else "N/A -- object-only donor, no ensemble aux parts produced"),
        ),
        ensemble_expected_matches=ensemble_expected_matches, all_ok=all_ok)


# ================================================================================================
# STAGE C -- CONTRACT CONFORMANCE on the retile (topo-16-only Law 6) + the dressing (topo-per-family/
# event-area-flags/straddle-one-row-both-tris/family-keyed-fringe-row), reading real bytes, mirroring
# gd_seam_dress.build_and_gate's own post-checks (lines 371-397) rather than trusting sector_retile's/
# assign_dressing's own claimed behaviour.
# ================================================================================================
def stage_contract_conformance(s3r: dict, s4: dict) -> dict:
    log("\n" + "#" * 100)
    log("STAGE C -- CONTRACT CONFORMANCE (topo-16-only Law 6 + dressing topo/EAF/row laws, read from "
        "the real composed bytes)")
    log("#" * 100)
    blocks_retiled = s3r["blocks_retiled"]
    bad_topo17 = []
    body_topo16_count = 0
    for blk in s3r["retile_touched"]:
        bm = blocks_retiled[blk]
        for tri in bm.tris:
            idall = int(round(bm.tangents[tri[0]][0]))
            topo = X.decode_id(idall)["topograph"]
            if topo == 16:
                body_topo16_count += 1
            elif topo == 17:
                bad_topo17.append((list(blk), list(tri)))
    topo_law_ok = not bad_topo17
    body_count_matches = body_topo16_count == s3r["retile_stats"]["n_retiled"]

    writes = s4["dress"]["writes"]
    dress_topo_ok = all(
        X.decode_id(v)["topograph"] == (GD.STRIP_GRASS_TOPO if w["fam"] == "grass" else GD.STRIP_DESERT_TOPO)
        for w in writes for v in w["new_idall"])
    eaf_ok = all(GD.CR._same_event_area_flags(o, n) for w in writes for o, n in zip(w["old_idall"], w["new_idall"]))

    by_cell = defaultdict(list)
    for w in writes:
        by_cell[(tuple(w["block"]), tuple(w["cell"]))].append(w)
    straddle_row_bad, fringe_row_bad = [], []
    n_straddle_cells = n_fringe_cells = 0
    for key, ws in by_cell.items():
        fams = {w["fam"] for w in ws}
        if fams == {"grass", "desert"}:
            n_straddle_cells += 1
            rows = {w["row"] for w in ws}
            if len(rows) != 1 or len(ws) != 2:
                straddle_row_bad.append((list(key[0]), list(key[1]), sorted(rows), len(ws)))
        else:
            n_fringe_cells += 1
            fam = next(iter(fams))
            for w in ws:
                if (fam == "grass" and w["row"] != 0) or (fam == "desert" and w["row"] != 2):
                    fringe_row_bad.append((list(key[0]), list(key[1]), fam, w["row"]))
    straddle_law_ok = not straddle_row_bad
    fringe_law_ok = not fringe_row_bad

    log(f"  LAW 6 (body topo-16-only): {body_topo16_count} body tri(s) topo==16 "
        f"(matches retile_stats.n_retiled={s3r['retile_stats']['n_retiled']}: {body_count_matches}); "
        f"topo==17 leaks: {len(bad_topo17)} -> {'CLEAN' if topo_law_ok else 'VIOLATION'}")
    log(f"  DRESSING topo-per-family: {'OK' if dress_topo_ok else 'BAD'}; event/area/flags preserved: "
        f"{'OK' if eaf_ok else 'BAD'}")
    log(f"  STRADDLE one-row-both-tris: {n_straddle_cells} straddle cell(s), {len(straddle_row_bad)} "
        f"violation(s) -> {'OK' if straddle_law_ok else 'BAD'}")
    log(f"  FRINGE family-keyed row (grass->0, desert->2): {n_fringe_cells} fringe cell(s), "
        f"{len(fringe_row_bad)} violation(s) -> {'OK' if fringe_law_ok else 'BAD'}")

    return dict(topo_law_ok=topo_law_ok, body_topo16_count=body_topo16_count,
                body_count_matches_retile_stats=body_count_matches, n_bad_topo17=len(bad_topo17),
                bad_topo17_sample=bad_topo17[:10],
                dress_topo_law_ok=dress_topo_ok, dress_eaf_law_ok=eaf_ok,
                straddle_one_row_both_tris_ok=straddle_law_ok, n_straddle_cells=n_straddle_cells,
                straddle_row_violations=straddle_row_bad[:10],
                fringe_family_row_ok=fringe_law_ok, n_fringe_cells=n_fringe_cells,
                fringe_row_violations=fringe_row_bad[:10],
                all_ok=all([topo_law_ok, dress_topo_ok, eaf_ok, straddle_law_ok, fringe_law_ok]))


# ================================================================================================
# STAGE D -- SEA (_mint_sea4 for every footprint block) + per-block DONOR ASSIGNMENT + each donor's
# OWN real bound-part inventory (probed live off disk -- never assumed). THE DIVERT-ARM LAW itself
# (effective_prefab_arm) is verified as STAGE G, against the REAL file set, after STAGE F filters it
# by this exact bound inventory (see the module docstring's DONOR.TXT ASSIGNMENT note + the finding
# this probe surfaced: NEITHER Uaho (0,0) NOR the horseshoe (5,15) donor exposes a Sea1/Sea2/Beach1
# transform of its own -- both are interior/highland land, never shipped with shallow-coast shading
# -- so a blanket Sea1/Sea2/Beach1 override at those cells would be a DEAD FILE the engine's own
# TryLoad loop never even looks for (it iterates the EFFECTIVE PREFAB's transforms, not our override
# folder -- mesh.py:705-728's own stub_terrain_mesh docstring). This is NOT the (11,19) divert-arm
# DEFECT (which was a missing-Terrain problem, HasLandOverride false); it is the mechanism working
# as documented on a donor that never had those transforms to begin with. THE FIX -- ship only what
# each cell's OWN donor can bind (STAGE F below) -- is a genuine reduction in dead files, not a
# gate threshold loosened; the after-fix pass (STAGE G) is expected to read 0/0 clean BECAUSE the
# file set now only claims parts that exist, not because the check was weakened.
# ================================================================================================
_CANDIDATE_PARTS = ("terrain", "object", "falls", "river", "riverjoint",
                    "sea1", "sea2", "sea3", "sea4", "sea5", "beach1")


def _donor_part_set(donor: tuple, disc: int, game_root: Path) -> set:
    dbx, dby = donor
    out = set()
    for p in _CANDIDATE_PARTS:
        try:
            X.read_block(dbx, dby, disc=disc, game=game_root, part=p)
            out.add(p)
        except Exception:
            pass
    return out


def stage_sea_and_arm(s2: dict, footprint, game_root: Path) -> dict:
    log("\n" + "#" * 100)
    log("STAGE D -- SEA (_mint_sea4) + per-block DONOR.TXT assignment + each donor's real bound-part "
        "inventory (probed live off disk)")
    log("#" * 100)
    plane = ISL._sea_plane(1, game=game_root)
    horseshoe_donor = tuple(s2["res"]["donor_ref"])
    massif_span = {tuple(b) for b in s2["span_blocks"]}
    cell_donors = {blk: (horseshoe_donor if blk in massif_span else UAHO_DONOR) for blk in footprint}

    donor_part_cache: dict = {}

    def donor_parts(donor):
        if donor not in donor_part_cache:
            donor_part_cache[donor] = _donor_part_set(donor, 1, game_root)
        return donor_part_cache[donor]

    bound_by_block = {blk: donor_parts(cell_donors[blk]) for blk in footprint}
    log(f"  Uaho (0,0) real bound parts: {sorted(donor_parts(UAHO_DONOR))}")
    log(f"  horseshoe {horseshoe_donor} real bound parts: {sorted(donor_parts(horseshoe_donor))}")

    sea_by_cell = {}
    for blk in footprint:
        bx, by = blk
        hidden = {p.lower(): M.hidden_block_mesh(name=f"Block[{bx}][{by}] {p}", disc=1, x=bx, y=by)
                  for p in ("Sea1", "Sea2", "Sea3", "Sea5")}
        hidden["sea4"] = MBM._mint_sea4(plane, bx, by)
        sea_by_cell[blk] = hidden

    return dict(sea_by_cell=sea_by_cell, cell_donors=cell_donors, bound_by_block=bound_by_block,
                massif_span=sorted(massif_span), horseshoe_donor=list(horseshoe_donor),
                uaho_donor=list(UAHO_DONOR),
                donor_bound_parts={"uaho_0_0": sorted(donor_parts(UAHO_DONOR)),
                                   f"horseshoe_{horseshoe_donor[0]}_{horseshoe_donor[1]}":
                                       sorted(donor_parts(horseshoe_donor))})


# ================================================================================================
# STAGE E -- THE FULL GATE SUITE over the FINAL composed set (byte-diff confinement / orphan / wang-
# carry / mod-overwrite / grid-bounds / flat-mesh / sea-layer / hidden-blank / engine-selftest) --
# mirrors rung_d_build.stage_full_gates exactly, extended to TWO carved anchors' worth of ensemble
# parts (only the massif's are non-empty; Uaho is object-only, confirmed by stage B's own
# ensemble_expected_matches check).
# ================================================================================================
def stage_full_gates(built_stages: dict, sea_info: dict, game_root: Path) -> dict:
    log("\n" + "#" * 100)
    log("STAGE E -- FULL GATE SUITE (final composed set)")
    log("#" * 100)
    gates = []
    s0, s2, s2b, s4 = built_stages["s0"], built_stages["s2"], built_stages["s2b"], built_stages["s4"]
    footprint = s0["footprint"]
    final_blocks = dict(s4["dress"]["new_blocks"])           # every footprint block's final Terrain

    # -- byte-diff confinement: retile + dress must ONLY move UV/idall, zero vertex/normal, vs the
    #    post-BOTH-carves pre-retile baseline (s2b["blocks_now"]) --
    geom_untouched = True
    bad = []
    baseline_blocks = s2b["blocks_now"]
    for blk in footprint:
        b0, b1 = baseline_blocks[blk], final_blocks[blk]
        if b0.verts != b1.verts or b0.normals != b1.normals:
            geom_untouched = False
            bad.append(list(blk))
    gate(gates, "byte-diff confinement: sector-retile + dressing move ZERO vertex/normal bytes on "
         "every footprint block (UV+idall only), vs the post-both-carves pre-retile baseline",
         geom_untouched, f"{bad}" if bad else "")

    # -- ORPHAN GATE (0/0 mandatory, ring-true) --
    final_cell_meshes = {blk: [("Terrain", bm)] for blk, bm in final_blocks.items()}
    provider = MBM.make_context_provider(final_blocks, game_root)
    orphan = OG.orphan_decal_gate(final_cell_meshes, footprint, enforce=True, redress=False,
                                   context_provider=provider)
    gate(gates, "THE ORPHAN GATE: 0 orphans / 0 ambiguous over the full final composed footprint "
         "(ring-true against the site's real neighbourhood)",
         orphan["n_orphans"] == 0 and orphan["n_ambiguous"] == 0, f"{orphan}")

    # -- WANG-CARRY GATE --
    wang = TP.wang_carry_gate(sea_info["sea_by_cell"], footprint, enforce=True)
    gate(gates, "wang-carry gate: 0 incoherent frame edges (a fresh open-ocean mint, not a Wang-"
         "region crop)", wang["ok"] and wang["incoherent"] == 0, f"{wang}")

    # -- THE DIVERT-ARM LAW (effective_prefab_arm) is verified separately as STAGE G, against the
    #    REAL about-to-deploy file set (STAGE F filters every block's parts by its own donor's real
    #    bound-part inventory first -- see stage_sea_and_arm's own docstring for why) --

    # -- MOD-OVERWRITE GATE (real disk read) --
    mod_ow = TP._mod_overwrite_gate(MOD, sea_info["cell_donors"], disc=1, game=game_root)
    gate(gates, "MOD-OVERWRITE gate (transplant._mod_overwrite_gate, real disk read against the "
         "live install)", mod_ow["ok"], f"{mod_ow}")

    # -- GRID-BOUNDS (final) --
    gate(gates, "GRID-BOUNDS (final): every block in the composed set is inside the 24x20 grid",
         all(M.block_in_grid(*b) for b in final_blocks), "")

    # -- FLAT-MESH invariant + SEA-LAYER law + hidden-blank convention --
    flat_bad = []
    for blk, bm in final_blocks.items():
        if bm.vcount != len(bm.flat_index) or len(bm.flat_index) != 3 * len(bm.tris):
            flat_bad.append((list(blk), bm.vcount, len(bm.flat_index), len(bm.tris)))
    for blk in footprint:
        s4m = sea_info["sea_by_cell"][blk]["sea4"]
        if s4m.vcount != len(s4m.flat_index) or len(s4m.flat_index) != 3 * len(s4m.tris):
            flat_bad.append((["Sea4", list(blk)], s4m.vcount, len(s4m.flat_index), len(s4m.tris)))
    ensemble_parts_by_block = s2["res"].get("changed_parts") or {}
    for blk, parts in ensemble_parts_by_block.items():
        for pname, bm in parts.items():
            if bm.vcount != len(bm.flat_index) or len(bm.flat_index) != 3 * len(bm.tris):
                flat_bad.append(([pname, list(blk)], bm.vcount, len(bm.flat_index), len(bm.tris)))
    gate(gates, "byte sanity: THE FLAT-MESH INVARIANT (vcount==len(flat_index)==3*len(tris)) on "
         "every produced Terrain + Sea4 + ensemble-aux mesh", not flat_bad, f"{flat_bad[:6]}")

    sea_y_bad = []
    for blk in footprint:
        s4m = sea_info["sea_by_cell"][blk]["sea4"]
        badv = [v[1] for v in s4m.verts if abs(v[1]) > 1e-6]
        if badv:
            sea_y_bad.append((list(blk), badv[:4]))
    gate(gates, "byte sanity: THE SEA-LAYER LAW (every Sea4 vertex Y==0)", not sea_y_bad, f"{sea_y_bad[:6]}")

    hidden_y_bad = []
    for blk in footprint:
        for pname, bm in sea_info["sea_by_cell"][blk].items():
            if pname == "sea4":
                continue
            if any(v[1] > OG.STUB_Y_FLOOR for v in bm.verts):
                hidden_y_bad.append((list(blk), pname))
    gate(gates, "byte sanity: every hidden/blanked sea part sits below the STUB_Y_FLOOR blanking "
         "convention", not hidden_y_bad, f"{hidden_y_bad[:6]}")

    # -- dressing stats vs null (the engine self-test) --
    null = SNR.part_b()
    engine_selftest = GD.engine_selftest(REL.DRESS_SEED, null)
    gate(gates, "gd_seam_dress engine self-test: realized straddle/fringe rates converge on the "
         "null-cluster targets (N=4000/phase, synthetic cell-ids)", engine_selftest["ok"],
         f"{engine_selftest}")

    n_fail = sum(1 for g in gates if not g["ok"])
    log(f"\n=== STAGE E: {len(gates)} gates, {n_fail} FAILED ===")
    return dict(gates=gates, n_gates=len(gates), n_failed=n_fail, orphan=orphan, wang=wang,
                mod_overwrite=mod_ow, engine_selftest=engine_selftest, final_blocks=final_blocks,
                changed_parts=ensemble_parts_by_block)


# ================================================================================================
# STAGE F -- THE DRY-RUN FILE SET (Terrain final + Sea4 + hidden water parts + the massif's ensemble
# aux parts + Donor.txt on every footprint block), FILTERED per block by that block's own Donor.txt
# donor's REAL bound-part inventory (``sea_info["bound_by_block"]``, stage D) -- a part the donor
# does not expose is never emitted (see stage_sea_and_arm's own docstring: shipping it would be a
# dead file the engine's divert never looks for). Terrain and Sea4 are ALWAYS emitted -- both donors
# genuinely expose them (probed live, not assumed; asserted below rather than silently trusted).
# Never writes to the game install.
# ================================================================================================
def build_file_set(built_stages: dict, full_gates: dict, sea_info: dict, footprint) -> dict:
    final_blocks = full_gates["final_blocks"]
    sea_by_cell = sea_info["sea_by_cell"]
    changed_parts = full_gates["changed_parts"]
    cell_donors = sea_info["cell_donors"]
    bound_by_block = sea_info["bound_by_block"]
    files = {}
    skipped = []
    for blk in footprint:
        bx, by = blk
        bound = bound_by_block[blk]
        assert "terrain" in bound and "sea4" in bound, \
            f"{blk}: donor {cell_donors[blk]} unexpectedly lacks terrain/sea4 -- {sorted(bound)}"
        parts = {"Terrain": final_blocks[blk], "Sea4": sea_by_cell[blk]["sea4"]}
        for p in ("Sea1", "Sea2", "Sea3", "Sea5", "Beach1"):
            if p.lower() not in bound:
                skipped.append((list(blk), p))
                continue
            parts[p] = sea_by_cell[blk].get(p.lower()) or M.hidden_block_mesh(
                name=f"Block[{bx}][{by}] {p}", disc=1, x=bx, y=by)
        for p in IN.ENSEMBLE_PARTS:                          # Object, Falls, River, RiverJoint
            if p.lower() not in bound:
                skipped.append((list(blk), p))
                continue
            carried = changed_parts.get(blk, {}).get(p)
            parts[p] = carried if carried is not None else M.hidden_block_mesh(
                name=f"Block[{bx}][{by}] {p}", disc=1, x=bx, y=by)
        files[blk] = parts
    donors = {blk: cell_donors[blk] for blk in footprint}
    log(f"  STAGE F: {sum(len(p) for p in files.values())} part-file(s) across {len(files)} block(s) "
        f"(+{len(footprint)} Donor.txt sidecars); {len(skipped)} part(s) SKIPPED as unbindable-by-"
        f"donor (would have been dead files): {skipped[:10]}{' ...' if len(skipped) > 10 else ''}")
    return {"files": files, "donors": donors, "skipped": skipped}


# ================================================================================================
# STAGE G -- THE DIVERT-ARM LAW, VERIFIED against the REAL about-to-deploy file set (post STAGE F's
# filter). Expected: 0 blocks needed a stub-Terrain arm (every block already ships real Terrain --
# this is a land mint, not a water-only carry) AND 0 unbindable parts (STAGE F only emitted what
# each donor can bind) -- a genuine, re-derived confirmation, not the same claim repeated.
# ================================================================================================
def stage_divert_arm_verify(fileset: dict, sea_info: dict, footprint) -> dict:
    log("\n" + "#" * 100)
    log("STAGE G -- THE DIVERT-ARM LAW, verified against the real (post-filter) file set")
    log("#" * 100)
    bound_by_block = sea_info["bound_by_block"]
    arm_gates = []
    n_armed = 0
    for blk in footprint:
        meshes = [(pn, None) for pn in fileset["files"][blk]]   # effective_prefab_arm only reads
        # part NAMES (mesh.py/transplant.py:2201 -- `{pn for pn, _ in meshes}`), never the mesh
        # values, so a None placeholder is safe (matches STAGE D's own established precedent)
        donor = fileset["donors"][blk]
        arm_mesh, gd = TP.effective_prefab_arm(meshes, cell=blk, sidecar_parts=bound_by_block[blk],
                                               disc=1, lod="0_1")
        if arm_mesh is not None:
            n_armed += 1
        arm_gates.append(dict(gd, block=list(blk), donor=list(donor)))
    ok = all(g["ok"] for g in arm_gates)
    unbindable = [g for g in arm_gates if g["unbindable"]]
    log(f"  effective_prefab_arm over the {len(footprint)} REAL about-to-deploy file set(s): "
        f"{n_armed} needed a stub-Terrain arm (expect 0); {len(unbindable)} block(s) with an "
        f"unbindable part (expect 0) -> {'CLEAN' if ok and n_armed == 0 else 'DEFECT'}")
    if unbindable:
        log(f"    unbindable detail: {unbindable}")
    return dict(arm_gates_sample=arm_gates[:6], n_armed=n_armed, n_unbindable_blocks=len(unbindable),
                unbindable=unbindable, ok=(ok and n_armed == 0))


def write_dry_run(fileset: dict, footprint) -> dict:
    if OUT_ROOT.exists():
        shutil.rmtree(OUT_ROOT)
    written = []
    for blk in sorted(footprint):
        bx, by = blk
        parts = fileset["files"][blk]
        for part_name, bm in parts.items():
            rel = M.override_relpath(1, bx, by, "0_1", part_name)
            path = OUT_ROOT / rel
            M.write_ff9mesh(bm, path)
            written.append(str(path))
        donor = fileset["donors"][blk]
        rel_d = M.donor_sidecar_relpath(1, bx, by, "0_1")
        dpath = OUT_ROOT / rel_d
        dpath.parent.mkdir(parents=True, exist_ok=True)
        dpath.write_text(f"{donor[0]},{donor[1]}", encoding="utf-8")
        written.append(str(dpath))
    manifest = {"mod_folder": MOD, "written": written, "footprint": [list(b) for b in footprint],
                "note": "dry-run file set -- would-be-deployed bytes under out/rung_e/"
                        f"{MOD}/... , RELATIVE-equivalent to <game>/{MOD}/... under --apply "
                        "(never invoked this session)."}
    (OUT_DIR / "rung_e_build_manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    log(f"\nDRY-RUN file set: {len(written)} file(s) -> {OUT_ROOT}")
    return manifest


# ================================================================================================
# --apply / --revert -- OWNER-GATED. Present for completeness (the redress-script convention the
# task specifies) but NEVER invoked by this session; the harness that runs this script is dry-run
# only by hard rule (CLAUDE.md Hard Constraints).
# ================================================================================================
def apply_deploy(fileset: dict, footprint, n_fail: int, game_root: Path) -> int:
    if n_fail:
        sys.exit(f"REFUSING --apply: {n_fail} gate(s) failed")
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = BACKUP_ROOT / f"rung-e-build.{ts}"
    pre_existing = []
    for blk in footprint:
        for part_name in fileset["files"][blk]:
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
            sys.exit(f"REFUSING to write: backup of {len(pre_existing)} pre-existing file(s) "
                      f"failed ({e}); nothing was touched.")
        print(f"backed up {len(pre_existing)} pre-existing file(s) -> {backup_root} "
              f"(unexpected -- MOD-OVERWRITE should have shown 0)")
    else:
        print("0 pre-existing target files (expected); no backup needed.")

    written = []
    for blk in sorted(footprint):
        for part_name, bm in fileset["files"][blk].items():
            written.append(M.deploy_override(bm, mod_folder=MOD, game=game_root, part=part_name))
        donor = fileset["donors"][blk]
        written.append(M.deploy_donor_sidecar(donor[0], donor[1], mod_folder=MOD, disc=1,
                                               x=blk[0], y=blk[1], game=game_root))
    from ff9mapkit.world import discmirror as DM
    mirror_summary = DM.auto_mirror(written, mod_folder=MOD)
    print(f"deployed {len(written)} file(s); disc-4 mirror: {mirror_summary}")
    manifest = {"mod_folder": MOD, "written": [str(p) for p in written],
                "pre_existing_backed_up": [str(p) for p in pre_existing], "backup_dir": str(backup_root),
                "mirror_summary": mirror_summary, "footprint": [list(b) for b in footprint]}
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    (BACKUP_ROOT / f"rung-e-build.{ts}.manifest.json").write_text(
        json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"revert manifest -> rung-e-build.{ts}.manifest.json (pass its stem to --revert)")
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
    ap.add_argument("--apply", action="store_true",
                     help="write + backup + mirror (OWNER-GATED; never pass this in an agent session)")
    ap.add_argument("--revert", metavar="NAME", default=None,
                     help="revert a prior --apply via its manifest stem (rung-e-build.<ts>)")
    args = ap.parse_args()

    if args.revert:
        return revert_deploy(args.revert)

    game_root = Path(_cfg.find_game_path(None))
    built_stages = run_layout_stages(game_root)
    repro = check_reproduces_recorded_layout(built_stages)

    log("\n" + "#" * 100)
    log("STAGE B -- CARVE GATES (massif + north anchor)")
    log("#" * 100)
    carve_massif = _carve_gate_report("massif (horseshoe, ensemble-class)", built_stages["s2"],
                                       built_stages["cap2"], ensemble_expected=True)
    carve_north = _carve_gate_report("north anchor (Uaho, object-only)", built_stages["s2b"],
                                      built_stages["cap2b"], ensemble_expected=False)

    contract = stage_contract_conformance(built_stages["s3r"], built_stages["s4"])

    footprint = built_stages["s0"]["footprint"]
    sea_info = stage_sea_and_arm(built_stages["s2"], footprint, game_root)
    full_gates = stage_full_gates(built_stages, sea_info, game_root)

    fileset = build_file_set(built_stages, full_gates, sea_info, footprint)
    arm_verify = stage_divert_arm_verify(fileset, sea_info, footprint)
    manifest = write_dry_run(fileset, footprint)

    s5 = built_stages["s5"]
    site_gates_ok = all(built_stages["s0"]["gates"].values())
    n_fail = (full_gates["n_failed"]
              + (0 if repro["ok"] else 1)
              + (0 if carve_massif["all_ok"] else 1)
              + (0 if carve_north["all_ok"] else 1)
              + (0 if contract["all_ok"] else 1)
              + (0 if site_gates_ok else 1)
              + (0 if built_stages["s1"]["is_one_landmass"] else 1)
              + (0 if s5["gate1_coast_standoff"]["meets_39_95u_floor"] else 1)
              + (0 if s5["gate2_dressing_ratio"]["in_band"] else 1)
              + (0 if s5["gate3_termination_decal"]["clean"] else 1)
              + (0 if built_stages["s0"]["verify"]["shape"]["ok"] else 1)
              + (0 if arm_verify["ok"] else 1))

    fails = []
    if not repro["ok"]:
        fails.append(f"re-run DIVERGED from the recorded rung_e_layout.json: {repro['mismatches']}")
    if not site_gates_ok:
        fails.append(f"stage0 site gates: {built_stages['s0']['gates']}")
    if not built_stages["s1"]["is_one_landmass"]:
        fails.append("stage1: NOT one contiguous landmass across y=-1024")
    if not carve_massif["all_ok"]:
        fails.append(f"CARVE GATES (massif): {carve_massif['checks']}")
    if not carve_north["all_ok"]:
        fails.append(f"CARVE GATES (north anchor): {carve_north['checks']}")
    if not contract["all_ok"]:
        fails.append(f"CONTRACT CONFORMANCE: {contract}")
    if not s5["gate1_coast_standoff"]["meets_39_95u_floor"]:
        fails.append(f"GATE1 coast-standoff: {s5['gate1_coast_standoff']['line_min_dist_to_coast']}u "
                     f"< the 39.95u contract floor")
    if not s5["gate2_dressing_ratio"]["in_band"]:
        fails.append(f"GATE2 dressing-ratio: {s5['gate2_dressing_ratio']['ratio_writes']} > local band "
                     f"max {s5['gate2_dressing_ratio']['local_band_max']}")
    if not s5["gate3_termination_decal"]["clean"]:
        fails.append(f"GATE3 termination-decal: {s5['gate3_termination_decal']['n_contaminating_writes']} "
                     f"contaminating write(s)")
    if not built_stages["s0"]["verify"]["shape"]["ok"]:
        fails.append(f"GATE4 macro-silhouette (verify_landmass shape): {built_stages['s0']['verify']['shape']}")
    if not arm_verify["ok"]:
        fails.append(f"THE DIVERT-ARM LAW (post-filter verification): {arm_verify['n_armed']} armed, "
                     f"{arm_verify['n_unbindable_blocks']} block(s) unbindable -- {arm_verify['unbindable']}")
    for g in full_gates["gates"]:
        if not g["ok"]:
            fails.append(f"STAGE E gate FAILED: {g['name']} -- {g['detail']}")

    report = {
        "reproduces_recorded_layout": repro,
        "stage0_site_gates": built_stages["s0"]["gates"],
        "stage0_verify_landmass": built_stages["s0"]["verify"],
        "stage1_contiguity": dict(n_components=built_stages["s1"]["n_components"],
                                   is_one_landmass=built_stages["s1"]["is_one_landmass"]),
        "carve_gates_massif": carve_massif,
        "carve_gates_north_anchor": carve_north,
        "contract_conformance": contract,
        "sea_and_divert_arm": dict(
            massif_span=sea_info["massif_span"], horseshoe_donor=sea_info["horseshoe_donor"],
            uaho_donor=sea_info["uaho_donor"], donor_bound_parts=sea_info["donor_bound_parts"],
            n_footprint_blocks_on_uaho_donor=sum(1 for d in sea_info["cell_donors"].values()
                                                 if tuple(d) == tuple(sea_info["uaho_donor"])),
            n_footprint_blocks_on_horseshoe_donor=sum(1 for d in sea_info["cell_donors"].values()
                                                       if list(d) == sea_info["horseshoe_donor"]),
            skipped_dead_files=fileset["skipped"]),
        "divert_arm_verify": arm_verify,
        "gate1_coast_standoff": s5["gate1_coast_standoff"],
        "gate2_dressing_ratio": s5["gate2_dressing_ratio"],
        "gate3_termination_decal": s5["gate3_termination_decal"],
        "gate4_macro_silhouette": s5["gate4_macro_silhouette"],
        "full_gate_suite": {"gates": full_gates["gates"], "n_gates": full_gates["n_gates"],
                            "n_failed": full_gates["n_failed"]},
        "orphan_gate": full_gates["orphan"],
        "wang_gate": full_gates["wang"],
        "mod_overwrite_gate": full_gates["mod_overwrite"],
        "engine_selftest": full_gates["engine_selftest"],
        "n_total_failed_gates": n_fail,
        "file_set_manifest": manifest,
        "apply_note": "NOT executed this session -- dry-run only, per HARD SAFETY RULES; --apply/"
                      "--revert exist in this script for the owner's hand.",
        "summary": dict(
            ok=True, gates_all_pass=(n_fail == 0),
            standoff_line_min_u=s5["gate1_coast_standoff"]["line_min_dist_to_coast"],
            standoff_body_min_u=s5["gate1_coast_standoff"]["body_min_dist_to_coast"],
            n_body_tris=built_stages["s3r"]["retile_stats"]["n_retiled"],
            n_dressing_writes=len(built_stages["s4"]["dress"]["writes"]),
            ratio_writes=s5["gate2_dressing_ratio"]["ratio_writes"],
            ratio_in_band=s5["gate2_dressing_ratio"]["in_band"],
            term_decal_clean=s5["gate3_termination_decal"]["clean"],
            silhouette_ok=bool(built_stages["s0"]["verify"]["shape"]["ok"]),
            wang_ok=full_gates["wang"]["ok"] and full_gates["wang"]["incoherent"] == 0,
            orphans=full_gates["orphan"]["n_orphans"] + full_gates["orphan"]["n_ambiguous"],
            n_orphans=full_gates["orphan"]["n_orphans"], n_ambiguous=full_gates["orphan"]["n_ambiguous"],
            fails=fails if fails else ["none"]),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    log(f"\n-> {OUT_JSON}")
    log(f"\nSUMMARY: {json.dumps(report['summary'], indent=1, default=str)}")
    log(f"\n=== TOTAL: {n_fail} failing check(s) across reproduction + carve gates + contract "
        f"conformance + the full gate suite ===")
    log("READ-ONLY throughout -- zero writes to the game install; this run never deployed.")

    if args.apply:
        return apply_deploy(fileset, footprint, n_fail, game_root)

    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
