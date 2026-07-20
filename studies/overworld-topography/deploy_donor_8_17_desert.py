"""THE REAL DEPLOY -- (8,17)+2x2 -> desert @ (11,18)+2x2, degenerate-sand-guard fix in effect.

NOT run by this session (hard rule: no deploys, no install writes). This is the verbatim
command the human runs to actually deploy what ``donor_8_17_carry_prep_v2.py`` proved clean.

WHY THIS WRAPPER EXISTS INSTEAD OF THE BARE CLI: ``ff9mapkit world-transplant --ground desert``
builds its retile via a plain ``TR.GroundRetile.for_donor(...)`` call (``ff9mapkit/cli.py``,
``_cmd_world_transplant``) -- it has no hook to substitute a different tweak class. The
degenerate-sand-guard fix (``strip_aware_retile.DegenerateSandGuardRetile``) is a study-local
SUBCLASS composed on top of the shipped ``GroundRetile`` precisely so no shipped file needed
editing -- but that also means the bare CLI command cannot reach it. Running the bare CLI command
today would REINTRODUCE the hatched-artifact bug this round fixed. Making ``--ground`` pluggable
(or folding the guard into ``GroundRetile`` itself) is a small, clearly-scoped shipped-code
follow-up -- flagged, not made, per this session's hard constraint.

Run for real: py studies/overworld-topography/deploy_donor_8_17_desert.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ff9mapkit.world import transplant as TR      # noqa: E402
import strip_aware_retile as SAR                    # noqa: E402

MOD_FOLDER = "FF9CustomMap-world"
DONOR = (8, 17)
DONOR_SIZE = (2, 2)
TARGET = (11, 18)

if __name__ == "__main__":
    gt = SAR.build(DONOR, "desert", size=DONOR_SIZE, strips="auto", extra=8.0, disc=1)
    summary = TR.transplant_region(
        MOD_FOLDER, cell=TARGET, donor=DONOR, size=DONOR_SIZE, rot=0, shift=(0.0, 0.0),
        strips="auto", tweaks=[gt], extra=8.0, land_margin=0.0, disc=1, census_samples=24,
        dry_run=False)                              # REAL writes -- this is the actual deploy
    print(f"clean={summary['clean']}  deployed={len(summary.get('deployed', []))} files")
    for g in summary["gates"]:
        detail = "  ".join(f"{k}={v}" for k, v in g.items() if k not in ("gate", "ok"))
        print(f"  {g['gate']}: {detail} -> {'ok' if g['ok'] else 'FAIL'}")
    if not summary["clean"]:
        raise SystemExit("gate failure -- NOT deployed cleanly, inspect the summary above")
