#!/usr/bin/env python3
"""Deploy a multi-campaign JOURNEY manifest in-game -- the orchestration step above ``deploy_campaign.py``.

A ``journeys.toml`` (``[hub]`` + bare/multi-campaign ``[[journey]]`` rows -- see ``docs/JOURNEYS.md`` +
``ff9mapkit/journey.py``) is deployed by composing the EXISTING, individually revert-guarded tools:

  1. ``deploy_campaign.py`` per campaign -- into its OWN stacked mod folder, at the journey-assigned disjoint
     ``--flag-base`` window, ``--no-warp`` (the hub owns New Game).
  2. the cross-campaign LINK rewrites -- the one journey-unique step: byte-patch each boundary member's
     deployed ``.eb`` ``Field(seam)`` exit -> the next campaign's entry id (this tool, ``--apply-links``).
  3. ``assemble-journey`` -> the hub ``field.toml``, then ``deploy_field.py`` it + ``retarget_newgame_warp.py``
     -> the hub.

DEFAULT = a DRY-RUN: lint the manifest, print the resolved namespace + the ordered command PLAYBOOK (each
step a proven tool you run + PLAYTEST in order -- "one change per in-game test", Hard Constraint §2). The only
step this tool EXECUTES is ``--apply-links`` (the link ``.eb`` remap), which is journey-specific and
revert-guarded. The campaign/hub/New-Game deploys are run via their own proven drivers from the playbook.

Usage:
  py tools/deploy_journey.py <journeys.toml>                 # dry-run: lint + the deploy playbook
  py tools/deploy_journey.py <journeys.toml> --apply-links   # apply ONLY the cross-campaign link .eb remaps
"""
from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
KIT = REPO / "ff9mapkit"
sys.path.insert(0, str(KIT))

from ff9mapkit import journey as J            # noqa: E402
from ff9mapkit.config import find_game_path   # noqa: E402


def _render_revert(results: list, stamp: str) -> str:
    """A revert script that restores every backed-up boundary .eb the link step patched."""
    pairs = [(live, bkp) for r in results for live, bkp in r.get("backups", [])]
    lines = [f'"""Revert journey link rewrites ({stamp}): restore the boundary .eb backups."""',
             "import shutil", "from pathlib import Path", "PAIRS = ["]
    lines += [f"    ({live!r}, {bkp!r})," for live, bkp in pairs]
    lines += ["]", "for live, bkp in PAIRS:",
              "    if Path(bkp).is_file(): shutil.copyfile(bkp, live); print('restored', live)",
              "    else: print('WARNING: backup missing --', bkp)",
              f"print('reverted journey links {stamp}')", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Deploy a multi-campaign journey manifest (orchestrator).")
    ap.add_argument("journeys", help="path to a journeys.toml ([hub] + [[journey]] rows)")
    ap.add_argument("--apply-links", action="store_true", dest="apply_links",
                    help="EXECUTE the cross-campaign link .eb remaps (the one journey-unique in-game step); "
                         "default is a dry-run that only prints the playbook")
    ap.add_argument("--hub-out", dest="hub_out", default=None,
                    help="path for the emitted hub field.toml referenced in the playbook (default: beside the "
                         "journeys.toml)")
    args = ap.parse_args(argv)

    jpath = Path(args.journeys)
    try:
        manifest = J.load_journeys(jpath)
        errors, warnings = J.lint_manifest(manifest)
    except (J.JourneyError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    for w in warnings:
        print("  warn:", w)
    if errors:
        print("journey lint FAILED:", file=sys.stderr)
        for e in errors:
            print("  error:", e, file=sys.stderr)
        return 2

    plan = J.build_deploy_plan(manifest)
    print(J.render_journey_plan(manifest))

    # --- link step (the only thing this tool executes) ---
    if args.apply_links:
        wirable = [lk for lk in plan.links if lk.retargetable]
        if not wirable:
            print("no auto-wirable cross-campaign links (overworld-only / ambiguous boundaries -- see the "
                  "playbook notes). Nothing to apply.")
            return 0
        game = find_game_path()
        if game is None:
            print("no FF9 install found -- can't apply link rewrites.", file=sys.stderr)
            return 2
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        bdir = REPO / "backups" / f"journey-links.{stamp}"
        results = J.apply_link_rewrites(plan, game, dry_run=False, backup_dir=bdir)
        any_found = False
        for r in results:
            if r["found"]:
                any_found = True
                print(f"  linked {r['eb']}: {r['remap']}  ({r['langs']} lang file(s))")
            else:
                print(f"  !! {r['eb']}: no Field({list(r['remap'])[0]}) found in the deployed .eb -- is the "
                      f"campaign deployed yet, and is the boundary a VERBATIM fork (ships its donor .eb)?")
        if any_found:
            out = HERE / "scroll_out"
            out.mkdir(exist_ok=True)
            rev = out / "revert_journey_links.py"
            rev.write_text(_render_revert(results, stamp), encoding="utf-8", newline="\n")
            print(f"link rewrites applied. RELAUNCH + PLAYTEST.  revert: py {rev.relative_to(REPO).as_posix()}")
        return 0

    # --- dry-run: the playbook ---
    hub_out = args.hub_out or str((jpath.parent / "hub.field.toml"))
    print(J.render_deploy_playbook(manifest, hub_toml=hub_out))
    print("DRY-RUN -- no game files touched. Run the playbook steps above (apply + PLAYTEST each in order).")
    print("This tool's --apply-links executes step 2 (the link .eb remaps); the rest use their own drivers.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
