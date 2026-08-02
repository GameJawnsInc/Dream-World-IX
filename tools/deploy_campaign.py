#!/usr/bin/env python3
"""Reversibly install a built import-chain CAMPAIGN into the live game + wire New Game to its entry field.

Thin repo shim over :func:`ff9mapkit.deploy.deploy_campaign` (the orchestration now lives in the package so
the installed ``ff9mapkit deploy-campaign`` CLI shares it). This wrapper supplies the repo-flavored backup +
revert dirs (``backups/`` + ``tools/scroll_out/``) and the worktree ``.ff9deploy.toml`` mod-folder default.

The model is install_tworoom's: ONE set-wide snapshot of the campaign mod folder + a WHOLESALE replace with the
built dist + ONE ``revert_campaign.py``. New Game is wired by retargeting the shared FF9CustomMap field-70
override (-> the campaign's entry id). SAFE BY DEFAULT: prints the plan and stops; pass ``--apply`` to install.

Usage:
  py tools/deploy_campaign.py <campaign.toml>                 # dry-run (prints the plan + guards)
  py tools/deploy_campaign.py <campaign.toml> --apply         # install + wire New Game (retarget field-70)
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
KIT = REPO / "ff9mapkit"
sys.path.insert(0, str(KIT))

from ff9mapkit import deploy                       # noqa: E402
from ff9mapkit.deploy import DeployError           # noqa: E402


def _worktree_cfg() -> dict:
    """The worktree's gitignored .ff9deploy.toml (mod_folder + campaign_id_base), or {}."""
    import tomllib
    f = REPO / ".ff9deploy.toml"
    try:
        return tomllib.loads(f.read_text(encoding="utf-8")) if f.is_file() else {}
    except Exception:
        return {}


def resolve_mod_folder(cli_value: str | None) -> str:
    """--mod-folder > $FF9_MOD_FOLDER > .ff9deploy.toml mod_folder > FF9CustomMap (deploy_field precedence)."""
    return cli_value or os.environ.get("FF9_MOD_FOLDER") or _worktree_cfg().get("mod_folder") or "FF9CustomMap"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Reversibly install a campaign mod + wire New Game (P4).")
    ap.add_argument("target", help="path to campaign.toml (built fresh) OR a prebuilt dist/ directory")
    ap.add_argument("--mod-folder", dest="mod_folder", default=None,
                    help="Memoria mod folder to install into (default: .ff9deploy.toml / $FF9_MOD_FOLDER)")
    ap.add_argument("--entry", default=None, help="New-Game entry: member name, field id, or omit for the manifest entry")
    ap.add_argument("--stock", action="store_true", help=argparse.SUPPRESS)  # deprecated/no-op
    ap.add_argument("--out-dist", dest="out_dist", default=None, help="where to stage the build (default: temp)")
    ap.add_argument("--allow-artless", action="store_true", dest="allow_artless",
                    help="install editable members that lack exported art (they render with NO background)")
    ap.add_argument("--no-warp", action="store_true", dest="no_warp", help="install the mod but skip New-Game wiring")
    ap.add_argument("--allow-name-collision", action="store_true", dest="allow_name_collision",
                    help="install even when EVT/FBG names collide with another FolderNames folder (default: ABORT)")
    ap.add_argument("--allow-id-collision", action="store_true", dest="allow_id_collision",
                    help="install even when a field/scene id collides with another FolderNames folder (default: ABORT)")
    ap.add_argument("--flag-base", type=int, default=None, dest="flag_base",
                    help="override the campaign's flag_base (the JOURNEY assembler's disjoint-window lever)")
    ap.add_argument("--no-promote-csv", action="store_true", dest="no_promote_csv",
                    help="do NOT promote the entry field's start-state CSVs to the highest FolderNames folder")
    ap.add_argument("--promote-csv-to", dest="promote_csv_to", default=None,
                    help="folder to promote start-state CSVs into (default: the highest Memoria.ini FolderNames folder)")
    ap.add_argument("--reflow-flags", action="store_true", dest="reflow_flags",
                    help="accept a build that MOVES an existing member's story-flag window or text "
                         "block vs this folder's last build (refused by default: those bits are "
                         "save-persistent, so a move invalidates every save made before it)")
    ap.add_argument("--apply", action="store_true", help="ACTUALLY touch the game (default: dry-run, prints the plan)")
    args = ap.parse_args(argv)
    if args.stock:
        print("note: --stock is deprecated and ignored -- deploy_campaign now retargets the field-70 override "
              "directly (New Game -> field 70 -> Field(entry)); there is no field-100 hop.", file=sys.stderr)

    try:
        report = deploy.deploy_campaign(
            args.target, mod_folder=resolve_mod_folder(args.mod_folder), entry=args.entry, apply=args.apply,
            allow_artless=args.allow_artless, no_warp=args.no_warp,
            allow_name_collision=args.allow_name_collision, allow_id_collision=args.allow_id_collision,
            flag_base=args.flag_base, no_promote_csv=args.no_promote_csv, promote_csv_to=args.promote_csv_to,
            out_dist=args.out_dist, allow_reflow=args.reflow_flags,
            backups_dir=REPO / "backups", reverts_dir=HERE / "scroll_out")
    except DeployError as e:
        print(str(e), file=sys.stderr)
        return 2
    return report["rc"]


if __name__ == "__main__":
    raise SystemExit(main())
