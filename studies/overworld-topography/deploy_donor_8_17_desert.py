"""THE REAL DEPLOY -- (8,17)+2x2 -> desert @ (11,18)+2x2, degenerate-sand-guard fix in effect.

NOT run by the build session (hard rule: no deploys, no install writes). This is the verbatim
command the human runs to actually deploy what ``donor_8_17_carry_prep_v2.py`` proved clean.

2026-07-20 UPDATE -- THE WRAPPER'S RAISON D'ETRE IS RETIRED: the degenerate-sand guard is now
FOLDED into the shipped ``GroundRetile`` itself (``ff9mapkit.world.transplant``), so the bare CLI
``ff9mapkit world-transplant --mod-folder FF9CustomMap-world --cell 11,18 --donor 8,17 --size 2x2
--ground desert --strips auto --shift 0,0 --land-margin 0`` now carries the fix and is EQUIVALENT
to this wrapper (``strip_aware_retile.build`` delegates to ``GroundRetile.for_donor``; a re-run
was byte-compared identical to the deployed files at fold time). Kept as the deployed carry's
exact re-deploy record.

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
