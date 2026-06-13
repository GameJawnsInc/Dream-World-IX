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
step a proven tool you run + PLAYTEST in order -- "one change per in-game test", Hard Constraint §2).

``--apply`` runs the WHOLE playbook in one shot: each campaign (the entry campaign seed-built in-process from
``[journey.seed]``) -> the link rewrites -> emit + deploy the hub field, capturing each step's own revert into
ONE ``revert_journey.py`` (reverse order). It does NOT touch New Game (the field-70 override is SINGLE-OWNER --
forcing it would hijack an existing hub, e.g. a live World Hub); reach this hub via F6 -> Warp, or add
``--wire-newgame`` to opt into making it the New-Game landing. ``--apply-links`` runs ONLY the link ``.eb``
remaps (re-apply after a campaign re-deploy). Either way I cannot see the game (Hard Constraint §2): after
--apply, follow the printed manual FolderNames + relaunch steps and PLAYTEST.

Usage:
  py tools/deploy_journey.py <journeys.toml>                       # dry-run: lint + the deploy playbook
  py tools/deploy_journey.py <journeys.toml> --apply               # ONE-SHOT: campaigns + links + hub (F6 to reach)
  py tools/deploy_journey.py <journeys.toml> --apply --wire-newgame # ...and make this hub the New-Game landing
  py tools/deploy_journey.py <journeys.toml> --apply-links         # apply ONLY the cross-campaign link .eb remaps
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


def _highest_folder(game) -> str:
    """The highest-priority Memoria.ini FolderNames folder (the hub + start-state CSVs go here), or the
    canonical default when the stack can't be read."""
    from ff9mapkit import deploystack as DS
    ini = Path(game) / "Memoria.ini"
    order = DS.parse_folder_names(ini.read_text(encoding="utf-8", errors="ignore")) if ini.is_file() else []
    return order[0] if order else "FF9CustomMap"


SCROLL = HERE / "scroll_out"


def _run(argv: list) -> int:
    """Run a child tool from the repo root, streaming its output. Returns the exit code."""
    import subprocess
    print(f"  $ {' '.join(Path(a).name if a.endswith('.py') else a for a in argv[1:])}")
    return subprocess.run(argv, cwd=str(REPO)).returncode


def _capture(src_name: str, dst_name: str) -> "str | None":
    """Copy a child tool's just-written (fixed-name) revert script to a per-step name BEFORE the next call
    overwrites it. Returns the captured path (str) or None if the source wasn't written."""
    import shutil
    src = SCROLL / src_name
    if not src.is_file():
        return None
    SCROLL.mkdir(exist_ok=True)
    dst = SCROLL / dst_name
    shutil.copyfile(src, dst)
    return str(dst)


def _run_links(plan, game, stamp: str) -> "tuple[str | None, bool]":
    """Apply the cross-campaign link .eb rewrites (field_remap + worldmap_inject). Returns
    ``(revert_path_or_None, all_wirable_links_found)``."""
    wirable = [lk for lk in plan.links if lk.retargetable]
    if not wirable:
        print("  (no auto-wirable cross-campaign links -- overworld-only/ambiguous; see the playbook notes)")
        return None, True
    bdir = REPO / "backups" / f"journey-links.{stamp}"
    results = J.apply_link_rewrites(plan, game, dry_run=False, backup_dir=bdir)
    ok = True
    for r in results:
        if r["found"] and r["mode"] == "worldmap_inject":
            print(f"  linked {r['eb']}: overworld exit -> Field({r['dst_id']}) region  "
                  f"({r['regions']} region(s), {r['langs']} lang file(s))")
        elif r["found"]:
            print(f"  linked {r['eb']}: {r['remap']}  ({r['langs']} lang file(s))")
        elif r["mode"] == "worldmap_inject":
            ok = False
            print(f"  !! {r['eb']}: no tag-2 WorldMap walk-out region in the deployed .eb -- campaign deployed "
                  f"yet, boundary a VERBATIM fork?")
        else:
            ok = False
            print(f"  !! {r['eb']}: no Field({list(r['remap'])[0] if r['remap'] else '?'}) in the deployed "
                  f".eb -- campaign deployed, boundary a VERBATIM fork?")
    if not any(r["found"] for r in results):
        return None, ok
    SCROLL.mkdir(exist_ok=True)
    rev = SCROLL / "revert_journey_links.py"
    rev.write_text(_render_revert(results, stamp), encoding="utf-8", newline="\n")
    return str(rev), ok


def _render_unified_revert(captured: list, stamp: str) -> str:
    """ONE revert that runs each captured per-step revert in REVERSE deploy order (undo New Game -> hub ->
    links -> campaigns). Each child revert is a complete, self-contained script (folder snapshot restore /
    .eb backup restore / etc.) run via runpy."""
    lines = [f'"""Revert journey deploy ({stamp}): run each step\'s revert in reverse order."""',
             "import runpy", "from pathlib import Path", "REVERTS = ["]
    lines += [f"    r{p!r}," for p in reversed(captured) if p]
    lines += ["]", "for _r in REVERTS:",
              "    _p = Path(_r)",
              "    if _p.is_file():",
              "        print('--- reverting', _p.name)",
              "        runpy.run_path(str(_p), run_name='__main__')",
              "    else:",
              "        print('WARNING: revert missing --', _p)",
              f"print('reverted journey deploy {stamp}')", ""]
    return "\n".join(lines)


def _apply_journey(manifest, plan, args) -> int:
    """The ONE-SHOT in-game deploy: each campaign (seeded entry) -> links -> hub -> New Game, with ONE unified
    revert. Mirrors deploy_campaign's safety model (each sub-step is its own revert-guarded driver). I cannot
    see the game (Hard Constraint §2) -- it ends by printing the manual FolderNames + relaunch + PLAYTEST steps."""
    from ff9mapkit import campaign as C
    if plan.folder_conflicts:
        print("ABORT: campaigns share a mod_folder (deploy_campaign wholesale-replaces it):", file=sys.stderr)
        for mf, a, b in plan.folder_conflicts:
            print(f"  {a!r} and {b!r} both -> {mf!r} -- give each its OWN mod_folder.", file=sys.stderr)
        return 2
    game = find_game_path()
    if game is None:
        print("no FF9 install found -- can't deploy.", file=sys.stderr)
        return 2
    if plan.hub_field_id is None:
        print("ABORT: the manifest has no [hub] id to deploy New Game into.", file=sys.stderr)
        return 2
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    highest = _highest_folder(game)
    captured: list = []                                   # per-step revert paths, in forward order
    SCROLL.mkdir(exist_ok=True)
    unified = SCROLL / "revert_journey.py"

    def _flush():                                         # rewrite the unified revert after every landed step
        unified.write_text(_render_unified_revert(captured, stamp), encoding="utf-8", newline="\n")

    def _abort(msg: str) -> int:
        _flush()
        print(f"\nABORT mid-deploy: {msg}", file=sys.stderr)
        print(f"Partial state is reversible: py {unified.relative_to(REPO).as_posix()}", file=sys.stderr)
        return 2

    # (1) each campaign -> its own stacked folder (--no-warp); the ENTRY campaign is seed-built in-process
    print("\n=== 1. campaigns ===")
    for s in plan.campaign_steps:
        if s.seed_blocks:                                 # seeded entry: build in-process, then install the dist
            dist = s.campaign_path.parent / "dist"
            print(f"  building {s.folder} with seed {s.seed_blocks} -> {dist}")
            try:
                C.build_campaign(s.campaign_path, out=dist, flag_base=s.flag_base, seed_blocks=s.seed_blocks)
            except (C.CampaignError, ValueError) as e:
                return _abort(f"seed-build of {s.folder} failed: {e}")
            rc = _run([sys.executable, str(HERE / "deploy_campaign.py"), str(dist),
                       "--apply", "--no-warp", "--mod-folder", s.mod_folder])
        else:
            rc = _run([sys.executable, str(HERE / "deploy_campaign.py"), str(s.campaign_path),
                       "--apply", "--no-warp", "--mod-folder", s.mod_folder, "--flag-base", str(s.flag_base)])
        if rc != 0:
            return _abort(f"deploy_campaign for {s.folder} exited {rc}")
        cap = _capture("revert_campaign.py", f"revert_journey_campaign_{s.folder}.py")
        if cap:
            captured.append(cap)
        _flush()

    # (2) cross-campaign links (LAST relative to campaign deploys -- the wholesale-replace gotcha)
    print("\n=== 2. links ===")
    link_rev, links_ok = _run_links(plan, game, stamp)
    if link_rev:
        captured.append(link_rev)
        _flush()
    if not links_ok:
        return _abort("a cross-campaign link did not apply (see !! above)")

    # (3) emit + deploy the hub field
    print("\n=== 3. hub ===")
    hub_toml = Path(args.hub_out) if args.hub_out else (manifest.path.parent / "hub.field.toml")
    try:
        J.generate_hub(manifest.path, out_path=hub_toml)
    except (J.JourneyError, ValueError) as e:
        return _abort(f"hub emit failed: {e}")
    print(f"  emitted hub -> {hub_toml}")
    rc = _run([sys.executable, str(HERE / "deploy_field.py"), str(hub_toml),
               "--id", str(plan.hub_field_id), "--mod-folder", highest])
    if rc != 0:
        return _abort(f"deploy_field for the hub (id {plan.hub_field_id}) exited {rc}")
    cap = _capture(f"revert_deploy_{plan.hub_field_id}.py", f"revert_journey_hub_{plan.hub_field_id}.py")
    if cap:
        captured.append(cap)
    _flush()

    # (4) OPTIONALLY point New Game at this hub. The field-70 override is SINGLE-OWNER (only one hub can own
    #     New Game), so this is OPT-IN -- otherwise --apply would silently hijack an existing New-Game hub
    #     (e.g. a live World Hub). Default: reach this hub via F6 -> Warp, New Game untouched.
    if args.wire_newgame:
        print("\n=== 4. New Game -> hub ===")
        rc = _run([sys.executable, str(HERE / "retarget_newgame_warp.py"), str(plan.hub_field_id)])
        if rc != 0:
            return _abort(f"retarget_newgame_warp exited {rc}")
        cap = _capture("revert_newgame_retarget.py", "revert_journey_newgame.py")
        if cap:
            captured.append(cap)
        _flush()
    else:
        print("\n=== 4. New Game -> hub: SKIPPED (New Game UNCHANGED; pass --wire-newgame to opt in) ===")

    print("\n=== MANUAL STEPS (this tool cannot do these) ===")
    print(f"1. Memoria.ini [Mod] FolderNames must STACK every campaign folder + the hub folder "
          f"({highest!r} highest).")
    print("2. RELAUNCH once -- the new ids only register on a fresh launch.")
    if args.wire_newgame:
        print(f"3. New Game now lands on the hub (field {plan.hub_field_id}); pick a journey, PLAYTEST.")
    else:
        print(f"3. Reach the hub via F6 -> Warp {plan.hub_field_id} (New Game is UNCHANGED). Pick a journey, "
              f"PLAYTEST.")
        print(f"   To make THIS hub the New-Game landing (SINGLE-OWNER -- replaces your current New-Game "
              f"target), re-run with --wire-newgame.")
    print(f"Revert EVERYTHING (reverse order): py {unified.relative_to(REPO).as_posix()}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Deploy a multi-campaign journey manifest (orchestrator).")
    ap.add_argument("journeys", help="path to a journeys.toml ([hub] + [[journey]] rows)")
    ap.add_argument("--apply", action="store_true",
                    help="ONE-SHOT: deploy every campaign (seeded entry) + links + the hub field, with one "
                         "unified revert (default is a dry-run that prints the playbook). New Game is NOT "
                         "touched unless you add --wire-newgame.")
    ap.add_argument("--wire-newgame", action="store_true", dest="wire_newgame",
                    help="with --apply, ALSO retarget New Game -> this manifest's hub. SINGLE-OWNER: replaces "
                         "the current New-Game landing (e.g. a live World Hub). Off by default -- otherwise "
                         "reach the hub via F6 -> Warp.")
    ap.add_argument("--apply-links", action="store_true", dest="apply_links",
                    help="EXECUTE ONLY the cross-campaign link .eb remaps (re-run after any campaign re-deploy)")
    ap.add_argument("--hub-out", dest="hub_out", default=None,
                    help="path for the emitted hub field.toml (default: hub.field.toml beside the journeys.toml)")
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

    if args.apply:
        return _apply_journey(manifest, plan, args)

    if args.apply_links:
        game = find_game_path()
        if game is None:
            print("no FF9 install found -- can't apply link rewrites.", file=sys.stderr)
            return 2
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        rev, _ok = _run_links(plan, game, stamp)
        if rev:
            print(f"link rewrites applied. RELAUNCH + PLAYTEST.  revert: py {Path(rev).relative_to(REPO).as_posix()}")
        return 0

    # --- dry-run: the playbook ---
    hub_out = args.hub_out or str((jpath.parent / "hub.field.toml"))
    print(J.render_deploy_playbook(manifest, hub_toml=hub_out, journeys_ref=args.journeys))
    print("DRY-RUN -- no game files touched. Either run the steps above one-by-one (PLAYTEST each), or run the "
          "whole thing with `--apply` (one unified revert).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
