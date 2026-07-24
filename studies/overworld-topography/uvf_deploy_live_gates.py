"""RUNG F UV-FIX ROUND 3 -- DEPLOY-TIME LIVE GATES.

Re-runs the three deploy-mandated checks (zero-degenerate UV, one-window-coherence, Sea4 uniformity)
DIRECTLY against the LIVE install path (not the staged FIXED3A tree), post-write, to confirm what
actually landed on disk matches what was verified offline. Reuses uvf_gates.py / uvf_gates3.py
functions verbatim, pointed at the live Disc1 tree via its FF9_Data-rooted Path (same relpath
convention as every staged tree, so `M.override_relpath` resolves identically).

Read-only against the live install (and the staged/specimen trees it cross-checks against). Writes
only out/rung_f/uvf_deploy_live_gates.json. Zero git.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

import uvf_gates as G             # noqa: E402
import uvf_gates3 as G3           # noqa: E402
from ff9mapkit.world import mesh as M  # noqa: E402

OUT_DIR = HERE / "out" / "rung_f"
OUT = OUT_DIR / "uvf_deploy_live_gates.json"

LIVE_DIR = Path("C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/FF9CustomMap-world")
FOOTPRINT = G.FOOTPRINT


def log(m):
    print(m, flush=True)


def sea4_uniformity_check(live_dir):
    """Sea4 files across the 20 touched blocks must all share ONE uniform bytes/sha (the standing
    invariant from the falsifier -- Sea4 was never touched by the UV-only fix, and must not have
    been touched by the deploy write either)."""
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
    log("LIVE GATE 1 -- zero-degenerate UV-validity, directly on LIVE Disc1")
    log("=" * 100)
    g1_live = G.gate1_uv_validity(FOOTPRINT, LIVE_DIR, "live_disc1")
    log(f"  zero_uv_area_frac={g1_live['zero_uv_area_frac']} (<= {G.GATE1_FRAC_CEILING}) "
        f"bit_identical={g1_live['total_bit_identical']} passed={g1_live['passed']}")
    result["gate1_uv_validity_live"] = g1_live

    log("=" * 100)
    log("LIVE GATE 1c -- one-window-coherence, directly on LIVE Disc1")
    log("=" * 100)
    ref = G3.build_reference_state()
    wc_live = G3.window_coherence_check(LIVE_DIR, "live_disc1", ref)
    log(f"  n={wc_live['n_tris']} single_window={wc_live['single_window_reconstructed']} "
        f"multi/unrecon={wc_live['multi_window_or_unreconstructed']} frac={wc_live['multi_window_frac']} "
        f"exc_p50={wc_live['excursion_p50']} exc_max={wc_live['excursion_max']} passed={wc_live['passed']}")
    result["gate1c_one_window_coherence_live"] = wc_live

    log("=" * 100)
    log("LIVE GATE -- Sea4 uniformity, directly on LIVE Disc1 (untouched-by-fix invariant)")
    log("=" * 100)
    sea4_live = sea4_uniformity_check(LIVE_DIR)
    log(f"  n_present={sea4_live['n_present']}/{sea4_live['n_blocks']} "
        f"n_unique_sha={sea4_live['n_unique_sha']} passed={sea4_live['passed']}")
    result["sea4_uniformity_live"] = sea4_live

    log("=" * 100)
    log("LIVE GATE 2 -- sea-plan-disjoint, directly on LIVE Disc1 (full A/B/C battery)")
    log("=" * 100)
    g2_live = G.gate2_sea_plan_disjoint(FOOTPRINT, LIVE_DIR, "live_disc1")
    log(f"  A={g2_live['A_y_order']['passed']} B={g2_live['B_uniformity']['passed']} "
        f"C={g2_live['C_real_sea_disjoint']['passed']} overall={g2_live['passed']}")
    result["gate2_sea_plan_disjoint_live"] = g2_live

    overall = (g1_live["passed"] and wc_live["passed"] and sea4_live["passed"] and g2_live["passed"])
    result["overall"] = "PASS" if overall else "FAIL"
    result["meta"] = dict(script="uvf_deploy_live_gates.py", target=str(LIVE_DIR),
                           note="re-runs zero-degenerate / one-window-coherence / Sea4-uniformity / "
                                "sea-plan-disjoint directly on the LIVE install post-write; read-only")

    OUT.write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    log("\n" + "=" * 100)
    log(f"OVERALL: {result['overall']}")
    log(f"-> {OUT}")
    return result


if __name__ == "__main__":
    main()
