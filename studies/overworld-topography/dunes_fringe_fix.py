"""THE FRINGE FIX -- rung 7 of the dunes arc (2026-07-21): DEPLOY the two-defect fringe fix the
forensics (dunes_fringe_census.py) proved, repairing the two playtest fringe defects the TRUE MESH
CARRY (rung 6, dunes_true_carry.py) left behind.

WHAT THE USER SAW (two ground-level screenshots, the ecotone APPROVED)
  1. "Lifted or shrunken seams in the ground" -- long thin BLUE SLIVERS (sea/void through the
     terrain), one at (1220,-1152) EXACTLY on the block border z=-1152.
  2. "Hard-edged grass ecotone tiles" -- carried green fragments reading as triangular shards.

THE MECHANISM (forensics, proven to the vertex -- see dunes_fringe_census.py + the Round 7 addendum
in GROUND-FAMILY-DECODE-2026-07-19.md):
  * HOLES  = THE PHASE-SHIFTED NOTCH: a sub-cell donor conform vert lands just off a phase-shifted
             block border; interior to one block it notches the boundary off the border, in the
             neighbour the SAME geometry clips straight at the border -> a thin void.
  * STEPS  = THE BLOCK-LOCAL WELD-SNAP MISS: the carry's conform-snap is keyed per-block, so a
             carried border vert is registered only in the block owning its cell; the neighbour
             host flat vert never welds UP to the elevated carried margin.
  * SHARDS = orphan-grass-stumps (THE ENSEMBLE LAW): 7 carried topo-0 desert|grass ECOTONE decals
             whose grass side the all-desert carry amputated (the 62 topo-49 brown mesa murals are
             faithful ensemble content -- KEPT).

THE FIX lives at the CARRY level (dunes_true_carry.carry(), always-on): FIX-H pre-quantizes notch
verts ONTO the border before the re-partition; FIX-S mirror-registers carried border-corner weld
targets into the ADJACENT block (rebuilding even the flat-host [18][18] so its border verts weld
up); FIX-G re-dresses the 7 topo-0 stumps to plain desert (UV/topo only, zero geometry moved). This
script is the DEPLOY ORCHESTRATOR + the ANTI-TEST harness: it re-derives byte-faithful geometry via
the corrected carry (which re-asserts ALL 10 carry gates + the frozen eye A/B/C at stock-exact + the
rung-7 cross-block seam/step/orphan-grass/eye-preserved gates), proves the CURRENT deployed bytes
FAIL the new gates and the REBUILT PASS, backs up both discs, deploys, and re-censuses the DEPLOYED
bytes to 0 steps / 0 holes / 0 stumps. Idempotent (a re-run rebuilds byte-identically).

  py studies/overworld-topography/dunes_fringe_fix.py            # dry run: anti-test + gates + render, NO write
  py studies/overworld-topography/dunes_fringe_fix.py --deploy   # + backups (both discs) + deploy + verify deployed
Artifacts -> out/dunes_fringe_fix.json + the carry's out/dunes_fringe_frame_*.png
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit import config as _cfg          # noqa: E402
from ff9mapkit.world import mesh as M          # noqa: E402

import dunes_true_carry as TC                  # noqa: E402  (the corrected carry + build_and_gate + deploy)
import dunes_fringe_census as FC               # noqa: E402  (the cross-block seam census + green-shard census)

OUTD = HERE / "out"
OUTD.mkdir(exist_ok=True)
MOD = TC.MOD
BACKUP_DIR = HERE.parents[1] / "backups" / "dunes-fringe-fix.20260721"

# the frozen defect set this fix must drive to zero (dunes_fringe_census.py, 2026-07-21)
KNOWN_STEPS, KNOWN_HOLES, KNOWN_STUMPS = 2, 2, 7


# ============================================================================================
# deployed fringe state (the anti-test read: the current bytes, cross-block seams + green stumps)
# ============================================================================================
def deployed_fringe_state():
    _recs, tot = FC.run_crack_census(FC.deployed_world_tris, FC.MINT_BLOCKS, "DEPLOYED mint region")
    shard = FC.green_shard_census()
    return dict(steps=tot["steps"], holes=tot["holes"], stumps=shard["n_stump"])


def _classify(state):
    if (state["steps"], state["holes"], state["stumps"]) == (0, 0, 0):
        return "CLEAN"
    if (state["steps"], state["holes"], state["stumps"]) == (KNOWN_STEPS, KNOWN_HOLES, KNOWN_STUMPS):
        return "KNOWN-DEFECTS"
    return "UNEXPECTED"


# ============================================================================================
# backup (preserve the PRE-FIX bytes; never overwrite an existing backup on a re-run)
# ============================================================================================
def backup_predeploy(blocks):
    game_root = Path(_cfg.find_game_path(None))
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    n_new = n_skip = 0
    for (bx, by) in sorted(blocks):
        for disc in (1, 4):
            rel = M.override_relpath(disc, bx, by, part="Terrain")
            src = game_root / MOD / rel
            if not src.exists():
                continue
            dst = BACKUP_DIR / rel
            if dst.exists():                                  # keep the FIRST (pre-fix) backup
                n_skip += 1
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            n_new += 1
    print(f"  backup -> {BACKUP_DIR}: {n_new} new, {n_skip} preserved (pre-fix bytes kept)")
    return n_new, n_skip


# ============================================================================================
# main
# ============================================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deploy", action="store_true", help="back up + deploy both discs + verify deployed")
    args = ap.parse_args()

    print("=" * 96)
    print("THE FRINGE FIX -- rung 7: deploy the two-defect fringe fix + the ANTI-TEST harness")
    print("=" * 96)

    # ---- 1) ANTI-TEST 'before': the CURRENT deployed bytes must FAIL the new cross-block gates ----
    print("\n--- ANTI-TEST (the current DEPLOYED bytes, before the fix) ---")
    before = deployed_fringe_state()
    before_cls = _classify(before)
    print(f"  deployed fringe state: steps={before['steps']} holes={before['holes']} "
          f"stumps={before['stumps']}  -> {before_cls}")
    if before_cls == "KNOWN-DEFECTS":
        print(f"  ANTI-TEST CONFIRMED: the current deploy FAILS the new gates with the frozen defect "
              f"set ({KNOWN_STEPS} steps + {KNOWN_HOLES} holes + {KNOWN_STUMPS} stumps).")
    elif before_cls == "CLEAN":
        print("  (already clean -- the fix is deployed; this run is idempotent.)")
    else:
        print(f"  WARN: UNEXPECTED deployed state (neither the frozen 4-defect set nor clean). "
              f"Investigate before deploying.")

    # ---- 2) BUILD + GATE (the corrected carry re-asserts ALL gates + the frozen eye) ----
    print("\n--- BUILD + GATE (the corrected carry: 10 carry gates + eye A/B/C + rung-7 fringe gates) ---")
    res = TC.build_and_gate(render=True)
    built_bms, n_fail = res["built_bms"], res["n_fail"]
    fringe = res["fringe_info"]
    rebuilt_ok = (fringe["built"]["steps"] == 0 and fringe["built"]["holes"] == 0
                  and fringe["n_green"] == 0 and fringe["eye_preserved"])
    print(f"\n  REBUILT fringe state: steps={fringe['built']['steps']} holes={fringe['built']['holes']} "
          f"stumps(topo-0)={fringe['n_green']} eye_preserved={fringe['eye_preserved']}  "
          f"-> {'PASS' if rebuilt_ok else 'FAIL'}")

    # ---- 3) the ANTI-TEST verdict: current deployed FAILS (or already clean) AND rebuilt PASSES ----
    anti_ok = rebuilt_ok and n_fail == 0 and before_cls in ("KNOWN-DEFECTS", "CLEAN")
    print("\n--- ANTI-TEST VERDICT ---")
    print(f"  current deployed FAILS the new gates: {before_cls in ('KNOWN-DEFECTS',)} "
          f"(state={before_cls})")
    print(f"  the REBUILT fix PASSES the new gates : {rebuilt_ok} (all {res['out']['n_gates']} gates, "
          f"{n_fail} failed)")

    deployed = False
    after = None
    if args.deploy:
        if n_fail:
            sys.exit(f"REFUSING --deploy: {n_fail} gate(s) failed on the rebuild")
        print("\n--- BACKUP (both discs -> the fringe-fix backup dir, pre-fix bytes preserved) ---")
        backup_predeploy(built_bms.keys())
        print("\n--- DEPLOY (both discs via the carry's guarded deploy + Disc4 mirror) ---")
        written = TC.deploy(built_bms)
        deployed = True
        print(f"  deployed {len(written)} Disc1 Terrain files (+ Disc4 mirror); blocks {sorted(built_bms)}")

        # ---- 6) VERIFY: re-census the DEPLOYED bytes -> 0 steps / 0 holes / 0 stumps ----
        print("\n--- VERIFY (re-census the DEPLOYED bytes after the fix) ---")
        after = deployed_fringe_state()
        after_cls = _classify(after)
        print(f"  deployed fringe state AFTER: steps={after['steps']} holes={after['holes']} "
              f"stumps={after['stumps']}  -> {after_cls}")
        if after_cls != "CLEAN":
            sys.exit(f"POST-DEPLOY VERIFY FAILED: deployed still shows {after} (expected 0/0/0)")
        print("  VERIFIED: the deployed carry ring censuses 0 steps / 0 holes / 0 orphan-grass stumps.")

    out = dict(
        before=before, before_class=before_cls,
        rebuilt=dict(steps=fringe["built"]["steps"], holes=fringe["built"]["holes"],
                     stumps=fringe["n_green"], eye_preserved=fringe["eye_preserved"],
                     n_gates=res["out"]["n_gates"], n_failed=n_fail),
        anti_test=dict(current_fails=before_cls == "KNOWN-DEFECTS", rebuilt_passes=rebuilt_ok,
                       ok=anti_ok),
        touched_blocks=res["out"]["touched_blocks"],
        deployed=deployed, after=after, after_class=(_classify(after) if after else None),
        min_dist_core=fringe.get("min_dist_core"), min_dist_topo41=fringe.get("min_dist_topo41"),
        renders=res["out"].get("fringe_renders", []),
    )
    (OUTD / "dunes_fringe_fix.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"\n-> {OUTD / 'dunes_fringe_fix.json'}")

    if args.deploy:
        ok = deployed and after and _classify(after) == "CLEAN" and n_fail == 0
        print(f"\n=== FRINGE FIX {'DEPLOYED + VERIFIED' if ok else 'INCOMPLETE'} ===")
        return 0 if ok else 1
    print(f"\n=== DRY RUN complete (anti-test {'OK' if anti_ok else 'CHECK'}); pass --deploy to ship ===")
    return 0 if anti_ok else 1


if __name__ == "__main__":
    sys.exit(main())
