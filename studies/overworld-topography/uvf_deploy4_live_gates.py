"""RUNG F UV-FIX ROUND 4 (THE ROOTS RE-CLOTHE) -- DEPLOY-TIME LIVE GATES.

Re-runs the deploy-mandated checks DIRECTLY against the LIVE install path (post-write), to confirm
what actually landed on disk matches what was verified offline (uvf_gates4.py, on the staged FIXED4
tree). Reuses uvf_gates.py (gate1a zero-degenerate UV / gate2 sea-plan-disjoint) and uvf_gates4.py's
own family-aware one-window-coherence machinery (family_window_coherence_check + build_reference_state)
verbatim, pointed at LIVE_DIR. Also re-runs the Sea4-uniformity invariant (Sea4 was never touched by
this UV-only fix, must not have been touched by the write either).

Read-only against the live install (and the staged/report trees it reads to build the reference
state). Writes only out/rung_f/uvf_deploy4_live_gates.json. Zero git.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

import uvf_gates as G               # noqa: E402
import uvf_gates4 as G4             # noqa: E402
from ff9mapkit.world import mesh as M  # noqa: E402

OUT_DIR = HERE / "out" / "rung_f"
OUT = OUT_DIR / "uvf_deploy4_live_gates.json"

LIVE_DIR = Path("C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/FF9CustomMap-world")
FOOTPRINT = G.FOOTPRINT


def log(m):
    print(m, flush=True)


def sea4_uniformity_check(live_dir):
    """Sea4 files across the 20 touched blocks must all share ONE uniform bytes/sha (the standing
    invariant -- Sea4 was never touched by the UV-only fix, and must not have been touched by the
    deploy write either)."""
    import hashlib
    shas = {}
    for (bx, by) in FOOTPRINT:
        p = live_dir / M.override_relpath(1, bx, by, part="Sea4")
        if not p.exists():
            shas[f"{bx},{by}"] = None
            continue
        shas[f"{bx},{by}"] = hashlib.sha256(p.read_bytes()).hexdigest()
    uniq = set(v for v in shas.values() if v is not None)
    missing = [k for k, v in shas.items() if v is None]
    return dict(
        n_blocks=len(FOOTPRINT), n_present=len(FOOTPRINT) - len(missing), missing=missing,
        n_unique_sha=len(uniq), unique_shas=sorted(uniq),
        passed=(len(missing) == 0 and len(uniq) == 1))


def main():
    assert LIVE_DIR.exists(), f"missing live dir: {LIVE_DIR}"
    result = {}

    log("=" * 100)
    log("LIVE GATE 1a -- zero-degenerate UV-validity, directly on LIVE Disc1")
    log("=" * 100)
    g1_live = G.gate1_uv_validity(FOOTPRINT, LIVE_DIR, "live_disc1")
    log(f"  zero_uv_area_frac={g1_live['zero_uv_area_frac']} (<= {G.GATE1_FRAC_CEILING}) "
        f"bit_identical={g1_live['total_bit_identical']} passed={g1_live['passed']}")
    result["gate1a_uv_validity_live"] = g1_live

    log("=" * 100)
    log("LIVE GATE 2 -- sea-plan-disjoint, directly on LIVE Disc1 (full A/B/C battery)")
    log("=" * 100)
    g2_live = G.gate2_sea_plan_disjoint(FOOTPRINT, LIVE_DIR, "live_disc1")
    log(f"  A={g2_live['A_y_order']['passed']} B={g2_live['B_uniformity']['passed']} "
        f"C={g2_live['C_real_sea_disjoint']['passed']} overall={g2_live['passed']}")
    result["gate2_sea_plan_disjoint_live"] = g2_live

    log("=" * 100)
    log("LIVE GATE 1c -- ONE-WINDOW-COHERENCE, FAMILY-AWARE, directly on LIVE Disc1")
    log("=" * 100)
    ref = G4.build_reference_state()
    wc_live = G4.family_window_coherence_check(LIVE_DIR, "live_disc1", ref)
    log(f"  n={wc_live['n_tris']} single={wc_live['single_window_reconstructed']} "
        f"multi={wc_live['multi_window_or_unreconstructed']} frac={wc_live['multi_window_frac']} "
        f"per_family={wc_live['per_family']} passed={wc_live['passed']}")
    result["gate1c_family_aware_window_coherence_live"] = wc_live

    log("=" * 100)
    log("LIVE -- FAMILY MAINS-RECT MEMBERSHIP, directly on LIVE Disc1")
    log("=" * 100)
    rect_live = G4.family_rect_membership_check(LIVE_DIR, "live_disc1", ref)
    log(f"  checked={rect_live['tris_checked_by_family']} out_of_region={rect_live['out_of_region_by_family']} "
        f"zero_area={rect_live['zero_area_by_family']} passed={rect_live['passed']}")
    result["family_rect_membership_live"] = rect_live

    log("=" * 100)
    log("LIVE GATE -- Sea4 uniformity, directly on LIVE Disc1 (untouched-by-fix invariant)")
    log("=" * 100)
    sea4_live = sea4_uniformity_check(LIVE_DIR)
    log(f"  n_present={sea4_live['n_present']}/{sea4_live['n_blocks']} "
        f"n_unique_sha={sea4_live['n_unique_sha']} passed={sea4_live['passed']}")
    result["sea4_uniformity_live"] = sea4_live

    overall = (g1_live["passed"] and g2_live["passed"] and wc_live["passed"]
               and rect_live["passed"] and sea4_live["passed"])
    result["overall"] = "PASS" if overall else "FAIL"
    result["meta"] = dict(
        script="uvf_deploy4_live_gates.py", target=str(LIVE_DIR), base_report="uvf_gates4.py",
        note="re-runs zero-degenerate / sea-plan-disjoint / family-aware one-window-coherence / "
             "family mains-rect membership / Sea4-uniformity directly on the LIVE install post-write; "
             "read-only. build_reference_state() re-derives the family/window field from the staged "
             "FIXED3A/uvf_forensics.json bookkeeping (position-only, tree-independent -- positions are "
             "byte-identical across specimen/FIXED3A/FIXED4/live by construction of this round).")

    OUT.write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    log("\n" + "=" * 100)
    log(f"OVERALL: {result['overall']}")
    log(f"-> {OUT}")
    return result


if __name__ == "__main__":
    main()
