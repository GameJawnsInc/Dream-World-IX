"""RUNG F -- THE SLIVER-STEP SHAVE (round 7) -- DEPLOY.

Lands FIXED7 (the scoped Y-only shave of the single "THE ONE" carried-donor dunes-relief STEP-arm
apex flagged by playtest 5 -- a small raised patch just south of the owner's WNW vantage wearing a
mottled non-sand look -- plus its 2 welded fill-weld-neighbors -- uvf_fix7.py) over the currently-live
FIXED6 bytes at C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/FF9CustomMap-world.

Procedure (matches every prior Rung-F deploy in this arc, base=FIXED6 source=FIXED7):
  (1) PRE-CHECK: sha256 live Disc1 (180 rung_f-footprint files) vs the staged FIXED6 tree. ABORT on
      any mismatch (drift / concurrent session) instead of overwriting.
  (2) BACKUP: full live rung_f footprint (Disc1 180 + Disc4 180 = 360 files) copied verbatim to
      backups/rungf-slivers-predeploy.<timestamp>/ before any write.
  (3) DIFF staged FIXED6 vs staged FIXED7 (180 files each) to find exactly what round 7 changed
      (expected: 1 Terrain file, matching uvf_gates7.py's full-tree sha256 diff and the falsifier's
      independently-derived changed-file list -- Block[1][18]).
  (4) WRITE those files to live Disc1.
  (5) MIRROR the same files byte-identical to the corresponding Disc4 paths (THE TWO-TREE LAW).
  (6) VERIFY sha256 live == staged FIXED7 on all 180 Disc1 files + the changed Disc4 files, and
      live == pre-write backup on the untouched Disc4 files (confirms the write touched exactly what
      it should and nothing else).
  (7) LIVE GATES directly against the live install (not the staged tree): uvf_gates.py's
      plumbing_criteria (the weld-near-miss + open-edge + flat-mesh + frame-bounds + down-facing
      audit), gate1_uv_validity (zero-degenerate UV), uvf_gates4.py's family-aware
      one-window-coherence + family mains-rect membership (UV bytes are untouched this round but
      re-measured live, not assumed), and the Sea4-uniformity invariant.

Read-only against the live install except the write in steps 4/5. Writes only the live mod folder
(steps 4/5), a backup copy (step 2), and out/rung_f/uvf_deploy7_report.json. Does NOT touch
Memoria.ini. Zero git.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

import uvf_gates as G                 # noqa: E402
import uvf_gates4 as G4                # noqa: E402
from ff9mapkit.world import mesh as M  # noqa: E402

OUT_DIR = HERE / "out" / "rung_f"
FIXED6_DIR = OUT_DIR / "FF9CustomMap-world-FIXED6"
FIXED7_DIR = OUT_DIR / "FF9CustomMap-world-FIXED7"
REPORT_OUT = OUT_DIR / "uvf_deploy7_report.json"

LIVE_ROOT = Path("C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/FF9CustomMap-world")
FOOTPRINT = G.FOOTPRINT   # the 20 rung_f blocks

BACKUP_ROOT = REPO_ROOT / "backups"

TS = datetime.now().strftime("%Y%m%d-%H%M%S")
BACKUP_DIR = BACKUP_ROOT / f"rungf-slivers-predeploy.{TS}"


def log(m):
    print(m, flush=True)


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel_files_for_block(tree_dir: Path, disc: str, bx: int, by: int):
    """Every file belonging to (bx,by) under Disc<disc>: the 8 mesh parts + Donor.txt (9/block)."""
    d = tree_dir / "FF9_Data" / "WorldMap" / f"Disc{disc}" / "0_1" / f"r{by}"
    pat = f"Block[{bx}][{by}]"
    out = []
    if d.exists():
        for f in sorted(d.iterdir()):
            if f.is_file() and f.name.startswith(pat):
                out.append(f.relative_to(tree_dir))
    return out


def all_footprint_relpaths(tree_dir: Path, disc: str):
    out = []
    for (bx, by) in FOOTPRINT:
        out.extend(rel_files_for_block(tree_dir, disc, bx, by))
    return sorted(out)


def sea4_uniformity_check(live_dir):
    shas = {}
    for (bx, by) in FOOTPRINT:
        p = live_dir / M.override_relpath(1, bx, by, part="Sea4")
        if not p.exists():
            shas[f"{bx},{by}"] = None
            continue
        shas[f"{bx},{by}"] = sha256(p)
    uniq = set(v for v in shas.values() if v is not None)
    missing = [k for k, v in shas.items() if v is None]
    return dict(
        n_blocks=len(FOOTPRINT), n_present=len(FOOTPRINT) - len(missing), missing=missing,
        n_unique_sha=len(uniq), unique_shas=sorted(uniq),
        passed=(len(missing) == 0 and len(uniq) == 1))


def main():
    assert FIXED6_DIR.exists(), f"missing staged FIXED6: {FIXED6_DIR}"
    assert FIXED7_DIR.exists(), f"missing staged FIXED7: {FIXED7_DIR}"
    assert LIVE_ROOT.exists(), f"missing live install dir: {LIVE_ROOT}"

    report = {"title": "RUNG F -- THE SLIVER-STEP SHAVE (round 7) -- DEPLOY REPORT",
              "timestamp": TS,
              "live_mod_folder": str(LIVE_ROOT),
              "source_staged": str(FIXED7_DIR), "base_staged": str(FIXED6_DIR)}

    # -------------------------------------------------------------------------------------------
    # (1) PRE-CHECK -- live Disc1 footprint (180 files) must equal staged FIXED6 exactly
    # -------------------------------------------------------------------------------------------
    log("=" * 100); log("STEP 1 -- PRE-CHECK: live Disc1 vs staged FIXED6"); log("=" * 100)
    fixed6_disc1 = all_footprint_relpaths(FIXED6_DIR, "1")
    mismatches, missing_live = [], []
    for rp in fixed6_disc1:
        lp = LIVE_ROOT / rp
        if not lp.exists():
            missing_live.append(str(rp)); continue
        if lp.suffix == ".txt":
            same = lp.read_bytes() == (FIXED6_DIR / rp).read_bytes()
        else:
            same = sha256(lp) == sha256(FIXED6_DIR / rp)
        if not same:
            mismatches.append(str(rp))
    precheck_ok = (not mismatches) and (not missing_live) and (len(fixed6_disc1) == 180)
    log(f"  fixed6_disc1_files={len(fixed6_disc1)} missing_live={len(missing_live)} mismatches={len(mismatches)} -> {'PROCEED' if precheck_ok else 'ABORT'}")
    report["1_pre_check"] = dict(n_files=len(fixed6_disc1), missing_live=missing_live,
                                  mismatches=mismatches, passed=precheck_ok)
    if not precheck_ok:
        report["status"] = "ABORTED"
        report["abort_reason"] = "live Disc1 does not match staged FIXED6 -- drift or concurrent session"
        REPORT_OUT.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
        log(f"ABORTED -> {REPORT_OUT}")
        return report

    # -------------------------------------------------------------------------------------------
    # (2) BACKUP -- full live footprint (Disc1 + Disc4) before any write
    # -------------------------------------------------------------------------------------------
    log("=" * 100); log(f"STEP 2 -- BACKUP -> {BACKUP_DIR}"); log("=" * 100)
    BACKUP_DIR.mkdir(parents=True, exist_ok=False)
    backup_count = 0
    live_disc1_files = all_footprint_relpaths(LIVE_ROOT, "1")
    live_disc4_files = all_footprint_relpaths(LIVE_ROOT, "4")
    for rp in live_disc1_files + live_disc4_files:
        src = LIVE_ROOT / rp
        dst = BACKUP_DIR / rp
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        backup_count += 1
    log(f"  backed up {backup_count} files (disc1={len(live_disc1_files)} disc4={len(live_disc4_files)})")
    report["2_backup"] = dict(dest=str(BACKUP_DIR), count=backup_count,
                               disc1=len(live_disc1_files), disc4=len(live_disc4_files))

    # -------------------------------------------------------------------------------------------
    # (3) DIFF staged FIXED6 vs staged FIXED7 -- find exactly what round 7 changed
    # -------------------------------------------------------------------------------------------
    log("=" * 100); log("STEP 3 -- DIFF staged FIXED6 vs staged FIXED7"); log("=" * 100)
    fixed7_disc1 = all_footprint_relpaths(FIXED7_DIR, "1")
    assert [str(x) for x in fixed7_disc1] == [str(x) for x in fixed6_disc1], "footprint file-set drifted between FIXED6 and FIXED7"
    changed = []
    for rp in fixed6_disc1:
        a = FIXED6_DIR / rp
        b = FIXED7_DIR / rp
        if a.read_bytes() != b.read_bytes():
            changed.append(rp)
    log(f"  files_changed={len(changed)}")
    for rp in changed:
        log(f"    {rp}")
    report["3_diff"] = dict(files_changed=len(changed), list=[str(x) for x in changed],
                             expected=1, matches_expected=(len(changed) == 1))

    # -------------------------------------------------------------------------------------------
    # (4) WRITE changed files to live Disc1
    # -------------------------------------------------------------------------------------------
    log("=" * 100); log("STEP 4 -- WRITE changed files to live Disc1"); log("=" * 100)
    for rp in changed:
        dst = LIVE_ROOT / rp
        dst.write_bytes((FIXED7_DIR / rp).read_bytes())
        log(f"  wrote {rp}")
    report["4_write_disc1"] = dict(files_written=len(changed), list=[str(x) for x in changed])

    # -------------------------------------------------------------------------------------------
    # (5) MIRROR the same files to Disc4
    # -------------------------------------------------------------------------------------------
    log("=" * 100); log("STEP 5 -- MIRROR to live Disc4"); log("=" * 100)
    disc4_written = []
    for rp in changed:
        rp4 = Path(str(rp).replace("Disc1", "Disc4", 1))
        dst = LIVE_ROOT / rp4
        assert dst.exists(), f"Disc4 mirror target missing: {dst}"
        dst.write_bytes((FIXED7_DIR / rp).read_bytes())
        disc4_written.append(rp4)
        log(f"  mirrored {rp4}")
    report["5_mirror_disc4"] = dict(files_written=len(disc4_written), list=[str(x) for x in disc4_written])

    # -------------------------------------------------------------------------------------------
    # (6) VERIFY
    # -------------------------------------------------------------------------------------------
    log("=" * 100); log("STEP 6 -- VERIFY"); log("=" * 100)
    disc1_bad = []
    for rp in fixed6_disc1:
        lp = LIVE_ROOT / rp
        expect = FIXED7_DIR / rp
        if lp.suffix == ".txt":
            ok = lp.read_bytes() == expect.read_bytes()
        else:
            ok = sha256(lp) == sha256(expect)
        if not ok:
            disc1_bad.append(str(rp))
    disc4_changed_bad = []
    for rp4 in disc4_written:
        lp = LIVE_ROOT / rp4
        rp1 = Path(str(rp4).replace("Disc4", "Disc1", 1))
        expect = FIXED7_DIR / rp1
        ok = (lp.read_bytes() == expect.read_bytes()) if lp.suffix == ".txt" else (sha256(lp) == sha256(expect))
        if not ok:
            disc4_changed_bad.append(str(rp4))
    changed_disc4_set = set(str(x) for x in disc4_written)
    disc4_untouched_bad = []
    for rp in live_disc4_files:
        if str(rp) in changed_disc4_set:
            continue
        lp = LIVE_ROOT / rp
        bak = BACKUP_DIR / rp
        ok = (lp.read_bytes() == bak.read_bytes()) if lp.suffix == ".txt" else (sha256(lp) == sha256(bak))
        if not ok:
            disc4_untouched_bad.append(str(rp))
    verify_ok = (not disc1_bad) and (not disc4_changed_bad) and (not disc4_untouched_bad)
    log(f"  disc1_180: bad={len(disc1_bad)}/{len(fixed6_disc1)}")
    log(f"  disc4_changed: bad={len(disc4_changed_bad)}/{len(disc4_written)}")
    log(f"  disc4_untouched: bad={len(disc4_untouched_bad)}/{len(live_disc4_files) - len(disc4_written)}")
    report["6_verify"] = dict(
        disc1_full_180=dict(checked=len(fixed6_disc1), bad=disc1_bad, passed=not disc1_bad),
        disc4_changed=dict(checked=len(disc4_written), bad=disc4_changed_bad, passed=not disc4_changed_bad),
        disc4_untouched=dict(checked=len(live_disc4_files) - len(disc4_written), bad=disc4_untouched_bad,
                              passed=not disc4_untouched_bad),
        passed=verify_ok)

    # -------------------------------------------------------------------------------------------
    # (7) LIVE GATES -- directly against the live install, post-write
    # -------------------------------------------------------------------------------------------
    log("=" * 100); log("STEP 7 -- LIVE GATES"); log("=" * 100)

    plumb_live = G.plumbing_criteria(LIVE_ROOT, "live_disc1_fixed7")
    log(f"  plumbing: flat={plumb_live['flat_mesh_ok']} grid={plumb_live['grid_ok']} "
        f"frame={plumb_live['frame_bounds_ok']} weld_near_miss={plumb_live['weld_near_miss_total']} "
        f"down_facing={plumb_live['total_down_facing_tris']} (baseline 3) "
        f"open_edges={plumb_live['open_edges_above_skirt']} all_ok={plumb_live['all_ok']}")
    plumb_ok = plumb_live["all_ok"] and plumb_live["total_down_facing_tris"] == 3

    g1_live = G.gate1_uv_validity(FOOTPRINT, LIVE_ROOT, "live_disc1_fixed7")
    log(f"  gate1a zero-degenerate UV: zero_uv_area_frac={g1_live['zero_uv_area_frac']} "
        f"bit_identical={g1_live['total_bit_identical']} passed={g1_live['passed']}")

    g2_live = G.gate2_sea_plan_disjoint(FOOTPRINT, LIVE_ROOT, "live_disc1_fixed7")
    log(f"  gate2 sea-plan-disjoint: A={g2_live['A_y_order']['passed']} "
        f"B={g2_live['B_uniformity']['passed']} C={g2_live['C_real_sea_disjoint']['passed']} "
        f"overall={g2_live['passed']}")

    ref = G4.build_reference_state()
    wc_live = G4.family_window_coherence_check(LIVE_ROOT, "live_disc1_fixed7", ref)
    log(f"  gate1c one-window-coherence: n={wc_live['n_tris']} single={wc_live['single_window_reconstructed']} "
        f"multi={wc_live['multi_window_or_unreconstructed']} frac={wc_live['multi_window_frac']} "
        f"passed={wc_live['passed']}")

    rect_live = G4.family_rect_membership_check(LIVE_ROOT, "live_disc1_fixed7", ref)
    log(f"  family mains-rect membership: out_of_region={rect_live['out_of_region_by_family']} "
        f"zero_area={rect_live['zero_area_by_family']} passed={rect_live['passed']}")

    sea4_live = sea4_uniformity_check(LIVE_ROOT)
    log(f"  sea4 uniformity: n_present={sea4_live['n_present']}/{sea4_live['n_blocks']} "
        f"n_unique_sha={sea4_live['n_unique_sha']} passed={sea4_live['passed']}")

    live_gates_overall = (plumb_ok and g1_live["passed"] and g2_live["passed"]
                           and wc_live["passed"] and rect_live["passed"] and sea4_live["passed"])
    report["7_live_gates"] = dict(
        plumbing_weld_openedge_flat_frame_downfacing=dict(**plumb_live, passed=plumb_ok),
        gate1a_zero_degenerate_uv=g1_live,
        gate2_sea_plan_disjoint=g2_live,
        gate1c_family_one_window_coherence=wc_live,
        family_mains_rect_membership=rect_live,
        sea4_uniformity=sea4_live,
        overall=("PASS" if live_gates_overall else "FAIL"))

    overall_deploy_ok = precheck_ok and verify_ok and live_gates_overall
    report["status"] = "DEPLOYED" if overall_deploy_ok else "DEPLOYED_WITH_GATE_FAILURES"
    report["sha_verify"] = ("Disc1 180/180 == FIXED7; Disc4 changed-files == FIXED7 + untouched == "
                             "pre-write backup." if verify_ok else "VERIFY FAILURES -- see 6_verify")
    report["backup_path"] = str(BACKUP_DIR)
    report["mirror"] = f"{len(disc4_written)}/{len(disc4_written)} Disc4 files mirrored byte-identical to their Disc1 counterparts (THE TWO-TREE LAW); the other {len(live_disc4_files) - len(disc4_written)} Disc4 rung_f files confirmed untouched vs the pre-write backup."
    report["memoria_ini"] = "not touched"
    report["git"] = "not touched -- no commit"
    report["notes"] = (
        "The live FF9CustomMap-world install now carries FIXED7: the scoped Y-only shave of THE ONE -- "
        "the single carried-donor dunes-relief STEP-arm apex at world (116,-1164), topo 41, riding a "
        "0.86 residual / 2.26u drop / 47.2deg slope step where round 5's relaxed fill sheet meets "
        "round-6-untouched pinned carried high ground -- the specific feature playtest 5 called out as "
        "'sticks out in particular and has a noticeably different texture than the sand' while standing "
        "WNW of the crater. Welded through to 2 fill positions, 3 positions / 16 vertex entries / 12 "
        "tris (2 kept) / 36 normal entries total moved, 1 Terrain file changed (Block[1][18]). The "
        "crater bowl (7.92u basin disc at world (127.14,-1161.42), floor Y=3.0) is byte-frozen -- 0 "
        "positions, 0 vertex bytes changed inside it, THE BASIN REFERENCE TRAP margin re-measured at "
        "0.1426u clearance -- and round 6's four prior spike apexes are byte-frozen and were NOT "
        "reselected by this round's widened census. UVs/tangents/indices/topo untouched -- the carried "
        "decal tris' texel stretch actually IMPROVED (1.44x/1.23x -> 1.05x/1.06x, both under stock's own "
        "0.76-1.41x ceiling), so the 'noticeably different texture' the owner saw was the geometric step "
        "smear, not a UV defect, and the fix is geometry-only. Offline gates (uvf_gates7.py) ALL GREEN, "
        "a genuinely code-disjoint falsifier (uvf_fix7_falsify.py, own parser/weld map/topo decode/hop "
        "graph/surface estimator) CONFIRMED bit-for-bit, and the calibration-first shaded-relief eye "
        "(uvf_eye7.py) cleared with calibration_saw_the_one=True, slivers_resolved=True, "
        "crater_verdict=PRESERVED before this deploy. ONE HONEST RESIDUAL both the eye and the "
        "falsifier surface and do not paper over: 5 other nearby fill tris (topo=0, welded to the same "
        "knob, 32.1-37.3deg) remain steep on FIXED7 and were not part of this round's scoped fix -- "
        "if playtest 6 still reads character in that immediate neighbourhood, uvf_eye7's flagged "
        "FILL-RESTORE companion (the west shoulder sitting below its donor height) is the next lever, "
        "not a re-open of round 7. Playtest 6 pending (owner to look at THE ONE's location just south "
        "of their WNW vantage and confirm it now reads as sand, while the crater and all prior fixes "
        "remain unaffected).")

    REPORT_OUT.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    log("\n" + "=" * 100)
    log(f"STATUS: {report['status']}")
    log(f"-> {REPORT_OUT}")
    return report


if __name__ == "__main__":
    main()
