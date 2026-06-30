#!/usr/bin/env python3
"""Deploy a multi-campaign JOURNEY manifest in-game -- the orchestration step above ``deploy_campaign``.

Thin repo shim over :func:`ff9mapkit.deploy.deploy_journey` (the orchestration now lives in the package so
the installed ``ff9mapkit deploy-journey`` CLI shares it). This wrapper supplies the repo-flavored backup +
revert dirs (``backups/`` + ``tools/scroll_out/``).

DEFAULT = a DRY-RUN: lint + print the resolved namespace + the ordered deploy PLAYBOOK. ``--apply`` runs the
whole playbook in one shot (each campaign -> the link rewrites -> the hub field) with ONE unified revert; it
does NOT touch New Game unless you add ``--newgame hub|entry`` (the field-70 override is SINGLE-OWNER).
``--single-folder`` merges the journey into one stacked folder; ``--apply-links`` re-applies only the link
``.eb`` remaps. I cannot see the game (Hard Constraint §2): after --apply, follow the printed FolderNames +
relaunch steps and PLAYTEST.

Usage:
  py tools/deploy_journey.py <journeys.toml>                         # dry-run: lint + the deploy playbook
  py tools/deploy_journey.py <journeys.toml> --apply                 # ONE-SHOT: campaigns + links + hub (F6 to reach)
  py tools/deploy_journey.py <journeys.toml> --apply --newgame hub    # ...and New Game -> the hub selector menu
  py tools/deploy_journey.py <journeys.toml> --apply-links           # apply ONLY the cross-campaign link .eb remaps
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
KIT = REPO / "ff9mapkit"
sys.path.insert(0, str(KIT))

from ff9mapkit import deploy                       # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Deploy a multi-campaign journey manifest (orchestrator).")
    ap.add_argument("journeys", help="path to a journeys.toml ([hub] + [[journey]] rows)")
    ap.add_argument("--apply", action="store_true",
                    help="ONE-SHOT: deploy every campaign (seeded entry) + links + the hub field, with one "
                         "unified revert (default is a dry-run that prints the playbook). New Game is NOT "
                         "touched unless you add --newgame hub|entry.")
    ap.add_argument("--newgame", choices=("none", "hub", "entry"), default="none",
                    help="with --apply, where New Game lands (SINGLE-OWNER). none (default) = unchanged, reach "
                         "the hub via F6. hub = the hub selector menu. entry = STRAIGHT into the opening field "
                         "(single-journey only; keeps the real opening FMV).")
    ap.add_argument("--wire-newgame", action="store_const", const="hub", dest="newgame",
                    help="back-compat alias for --newgame hub.")
    ap.add_argument("--apply-links", action="store_true", dest="apply_links",
                    help="EXECUTE ONLY the cross-campaign link .eb remaps (re-run after any campaign re-deploy)")
    ap.add_argument("--single-folder", dest="single_folder", nargs="?", const="", default=None,
                    help="with --apply, MERGE the whole journey into ONE stacked mod folder (a single FolderNames "
                         "entry). Optional NAME (default: FF9CustomMap-<hub>).")
    ap.add_argument("--allow-collision", action="store_true", dest="allow_collision",
                    help="(single-folder) install even if the merged journey collides with another FolderNames folder")
    ap.add_argument("--hub-out", dest="hub_out", default=None,
                    help="path for the emitted hub field.toml (default: hub.field.toml beside the journeys.toml)")
    args = ap.parse_args(argv)

    report = deploy.deploy_journey(
        args.journeys, apply=args.apply, newgame=args.newgame, apply_links=args.apply_links,
        single_folder=args.single_folder, allow_collision=args.allow_collision, hub_out=args.hub_out,
        backups_dir=REPO / "backups", reverts_dir=HERE / "scroll_out")
    return report["rc"]


if __name__ == "__main__":
    raise SystemExit(main())
