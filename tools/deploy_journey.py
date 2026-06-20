#!/usr/bin/env python3
"""Deploy a multi-campaign JOURNEY manifest in-game -- the orchestration step above ``deploy_campaign.py``.

A ``journeys.toml`` (``[hub]`` + bare/multi-campaign ``[[journey]]`` rows -- see ``docs/JOURNEYS.md`` +
``ff9mapkit/journey.py``) is deployed by composing the EXISTING, individually revert-guarded tools:

  1. ``deploy_campaign.py`` per campaign -- into its OWN stacked mod folder, at the journey-assigned disjoint
     ``--flag-base`` window, ``--no-warp`` (the hub owns New Game).
  2. the cross-campaign LINK rewrites -- the one journey-unique step: byte-patch each boundary member's
     deployed ``.eb`` ``Field(seam)`` exit -> the next campaign's entry id (this tool, ``--apply-links``).
  3. ``assemble-journey`` -> the hub ``field.toml``, then ``deploy_field.py`` it into a DEDICATED journey-owned
     hub folder; ``--newgame hub|entry`` then points New Game there (``wire_newgame_from_stock.py``).

DEFAULT = a DRY-RUN: lint the manifest, print the resolved namespace + the ordered command PLAYBOOK (each
step a proven tool you run + PLAYTEST in order -- "one change per in-game test", Hard Constraint §2).

``--apply`` runs the WHOLE playbook in one shot: each campaign (the entry campaign seed-built in-process from
``[journey.seed]``) -> the link rewrites -> emit + deploy the hub field, capturing each step's own revert into
ONE ``revert_journey.py`` (reverse order). It does NOT touch New Game by default (the field-70 override is
SINGLE-OWNER -- forcing it would hijack an existing hub, e.g. a live World Hub); reach this hub via F6 -> Warp,
or pass ``--newgame hub`` (New Game -> the hub selector menu) or ``--newgame entry`` (New Game STRAIGHT into the
opening field, no menu -- single-journey only; keeps the real opening FMV). ``--apply-links`` runs ONLY the link
``.eb`` remaps (re-apply after a campaign re-deploy). Either way I cannot see the game (Hard Constraint §2):
after --apply, follow the printed manual FolderNames + relaunch steps and PLAYTEST.

Usage:
  py tools/deploy_journey.py <journeys.toml>                        # dry-run: lint + the deploy playbook
  py tools/deploy_journey.py <journeys.toml> --apply                # ONE-SHOT: campaigns + links + hub (F6 to reach)
  py tools/deploy_journey.py <journeys.toml> --apply --newgame hub   # ...and New Game -> the hub selector menu
  py tools/deploy_journey.py <journeys.toml> --apply --newgame entry # ...and New Game -> STRAIGHT into the opening
  py tools/deploy_journey.py <journeys.toml> --apply-links          # apply ONLY the cross-campaign link .eb remaps
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


def _game_or_none():
    """``find_game_path()`` RAISES ``ConfigError`` when no install resolves (it never returns None) -- but the
    OPTIONAL pre-flight / the 'no FF9 install found' messages want a soft None, not an uncaught traceback (the
    dry-run/Preview path must stay offline-safe on a machine without the game)."""
    try:
        return find_game_path()
    except Exception:
        return None


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
    game = _game_or_none()
    if game is None:
        print("no FF9 install found -- can't deploy.", file=sys.stderr)
        return 2
    if plan.hub_field_id is None:
        print("ABORT: the manifest has no [hub] id to deploy New Game into.", file=sys.stderr)
        return 2

    # PRE-FLIGHT collision sweep vs the live Memoria.ini FolderNames stack -- BEFORE building or touching
    # anything. Catches the common trap (a SUPERSEDED prior journey still in FolderNames on this id band) with a
    # crisp "remove these folder(s)" report instead of an opaque "deploy_campaign ... exited 2" mid-install. A
    # collision against one of THIS journey's OWN folders is NOT a blocker (it's wholesale-replaced) -- the sweep
    # excludes them, so what survives is a genuinely foreign folder the user must drop from FolderNames.
    hub_name = manifest.hub.get("name") if manifest.hub else None
    col = J.preflight_collisions(plan, game, hub_name=hub_name)
    if col.has_blockers:
        print("\n" + J.render_collision_report(col), file=sys.stderr)
        return 2

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    highest = _highest_folder(game)
    # the hub field + the New-Game override go into a DEDICATED journey-owned folder (NOT the ambient deploy-time
    # highest, which the user may drop when re-stacking FolderNames for the journey / to dodge a band collision;
    # and NOT a campaign folder, whose wholesale re-deploy would wipe the override). The user stacks it HIGHEST.
    # plan.hub_folder is always set here (hub_field_id was checked non-None above); `or highest` is an unreachable
    # safety net (never the orphan-prone ambient highest in practice).
    hub_folder = plan.hub_folder or highest
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

    # (0) PRE-FLIGHT (NO game files touched): BUILD every campaign to its own dist + emit/build the hub, all
    #     offline. ANY build failure (a member's missing art / a bad [[npc]] / an unbuildable hub) must abort
    #     HERE, before a single campaign/link/hub is installed -- never mid-deploy with some campaigns already
    #     live. The ENTRY campaign is seed-built (the [journey.seed] capstone merged into its entry member).
    import tempfile
    from ff9mapkit import build as B
    hub_toml = Path(args.hub_out) if args.hub_out else (manifest.path.parent / "hub.field.toml")
    print("\n=== 0. pre-flight: build every campaign + the hub offline (no game files touched) ===")
    built: dict = {}                                      # folder -> prebuilt dist dir
    for s in plan.campaign_steps:
        dist = s.campaign_path.parent / "dist"
        seednote = f" + seed {s.seed_blocks}" if s.seed_blocks else ""
        print(f"  building {s.folder} (flag_base {s.flag_base}{seednote}) -> {dist}")
        try:
            C.build_campaign(s.campaign_path, out=dist, flag_base=s.flag_base, seed_blocks=s.seed_blocks,
                             text_block_base=s.text_block_base)
        except Exception as e:                            # CampaignError / BuildError / ... -- abort cleanly
            print(f"\nABORT (no game files touched): campaign {s.folder} does not build -- {e}", file=sys.stderr)
            return 2
        built[s.folder] = dist
    try:
        info = J.generate_hub(manifest.path, out_path=hub_toml, extract_camera=True, game=game)
        with tempfile.TemporaryDirectory() as td:
            B.build_mod([B.FieldProject.load(hub_toml)], Path(td) / "mod", mod_name="preflight")
    except Exception as e:                                # any emit/extract/build failure -> abort cleanly
        print(f"\nABORT (no game files touched): the hub does not build -- {e}", file=sys.stderr)
        if any(k in str(e).lower() for k in ("borrow", "camera", "scene", ".bgx")):
            print("  Provision the hub camera: set [hub] borrow_field = <real field id> (auto-extracted via "
                  "UnityPy), or place the [hub] camera .bgx beside the journeys.toml.", file=sys.stderr)
        return 2
    print(f"  all {len(built)} campaign(s) + the hub build OK -> {hub_toml}  (camera: {info['spec'].camera})")

    # authoritative collision re-check using the BUILT dists (FBG scene names are now known too -- the pre-build
    # pass only saw ids + EVT names). Still BEFORE any install, so an abort here leaves zero game-file changes.
    col = J.preflight_collisions(plan, game, dists=built, hub_name=hub_name)
    if col.has_blockers:
        print("\n" + J.render_collision_report(col), file=sys.stderr)
        return 2
    stale_note = J.render_collision_report(col)          # no blockers left -> just the "own folders replaced" note
    if stale_note:
        print("\n" + stale_note)

    # (1) INSTALL each prebuilt campaign dist -> its own stacked folder (--no-warp; the hub owns New Game).
    #     The dists are already built (step 0) with their seed + flag_base baked in, so this only installs.
    # --allow-id-collision: the journey-level pre-flight above already proved global id-disjointness vs every
    # FOREIGN FolderNames folder, and the assembler lints internal disjointness -- so the only id collision
    # deploy_campaign's per-folder check can still see is a SIBLING folder mid-install (this journey's own folder
    # holding a prior deploy, about to be replaced). Relaxing just the id check skips that transient false abort;
    # the NAME check stays strict (it still catches a genuine cross-worktree FBG/EVT shadow).
    print("\n=== 1. install campaigns ===")
    for s in plan.campaign_steps:
        rc = _run([sys.executable, str(HERE / "deploy_campaign.py"), str(built[s.folder]),
                   "--apply", "--no-warp", "--mod-folder", s.mod_folder, "--allow-id-collision"])
        if rc != 0:
            return _abort(f"deploy_campaign install for {s.folder} exited {rc}")
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

    # (3) deploy the hub field into its DEDICATED folder (already emitted + build-checked in pre-flight step 0)
    print(f"\n=== 3. hub (folder {hub_folder}) ===")
    rc = _run([sys.executable, str(HERE / "deploy_field.py"), str(hub_toml),
               "--id", str(plan.hub_field_id), "--mod-folder", hub_folder])
    if rc != 0:
        return _abort(f"deploy_field for the hub (id {plan.hub_field_id}) exited {rc}")
    cap = _capture(f"revert_deploy_{plan.hub_field_id}.py", f"revert_journey_hub_{plan.hub_field_id}.py")
    if cap:
        captured.append(cap)
    _flush()

    # (4) OPTIONALLY point New Game at this journey -- into the SAME dedicated hub folder (so it survives a
    #     campaign re-deploy + isn't shadowed). SINGLE-OWNER, so it's OPT-IN (--newgame):
    #       none  -- New Game UNCHANGED (reach the hub via F6 -> Warp). DEFAULT.
    #       hub   -- New Game -> the HUB selector menu.
    #       entry -- New Game -> straight into the OPENING field, no menu (single-journey; keeps field-70's FMV).
    #     Both create the field-70 override from STOCK into hub_folder (retarget no-ops on a fresh journey folder).
    if args.newgame in ("hub", "entry"):
        if args.newgame == "entry" and plan.entry_field_id is None:
            return _abort("--newgame entry needs a SINGLE-journey manifest (a multi-journey hub has no single "
                          "opening to land in -- use --newgame hub).")
        target = plan.hub_field_id if args.newgame == "hub" else plan.entry_field_id
        what = "the hub menu" if args.newgame == "hub" else "the opening, no menu"
        print(f"\n=== 4. New Game -> {what} (field {target}, folder {hub_folder}) ===")
        rc = _run([sys.executable, str(HERE / "wire_newgame_from_stock.py"), str(target),
                   "--mod-folder", hub_folder])
        if rc != 0:
            return _abort(f"wire_newgame_from_stock exited {rc}")
        cap = _capture("revert_newgame_from_stock.py", "revert_journey_newgame.py")
        if cap:
            captured.append(cap)
        _flush()
    else:
        print("\n=== 4. New Game: SKIPPED (New Game UNCHANGED; --newgame hub|entry to opt in) ===")

    print("\n=== MANUAL STEPS (this tool cannot do these) ===")
    folders = [hub_folder] + [s.mod_folder for s in plan.campaign_steps]
    print("1. Memoria.ini [Mod] FolderNames -- STACK these (HIGHEST first), then your video/passthrough mods below:")
    print("   FolderNames = " + ", ".join(f'"{f}"' for f in folders) + ', "<your other mods, e.g. Moguri>"')
    if plan.campaign_steps:
        lo = min(s.id_lo for s in plan.campaign_steps)
        hi = max(s.id_hi for s in plan.campaign_steps)
        print(f"   This journey uses field ids {lo}..{hi} -- REMOVE any OTHER custom-field folder that deploys in "
              f"that range (EventDB is GLOBAL, so an overlap black-screens).")
    print("2. RELAUNCH once -- the new ids only register on a fresh launch.")
    if args.newgame == "hub":
        print(f"3. New Game now lands on the hub (field {plan.hub_field_id}); pick a journey, PLAYTEST.")
    elif args.newgame == "entry":
        print(f"3. New Game now lands STRAIGHT in the opening (field {plan.entry_field_id}) -- no menu; "
              f"PLAYTEST. (The hub still exists; reach it via F6 -> Warp {plan.hub_field_id}.)")
    else:
        print(f"3. Reach the hub via F6 -> Warp {plan.hub_field_id} (New Game is UNCHANGED). Pick a journey, "
              f"PLAYTEST.")
        print(f"   To make THIS the New-Game landing (SINGLE-OWNER -- replaces your current target): re-run with "
              f"--newgame hub (the selector menu) or --newgame entry (straight into the opening).")
    print(f"Revert EVERYTHING (reverse order): py {unified.relative_to(REPO).as_posix()}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Deploy a multi-campaign journey manifest (orchestrator).")
    ap.add_argument("journeys", help="path to a journeys.toml ([hub] + [[journey]] rows)")
    ap.add_argument("--apply", action="store_true",
                    help="ONE-SHOT: deploy every campaign (seeded entry) + links + the hub field, with one "
                         "unified revert (default is a dry-run that prints the playbook). New Game is NOT "
                         "touched unless you add --newgame hub|entry.")
    ap.add_argument("--newgame", choices=("none", "hub", "entry"), default="none",
                    help="with --apply, where New Game lands (SINGLE-OWNER: replaces the current target). "
                         "none (default) = unchanged, reach the hub via F6. hub = the hub selector menu "
                         "(seamless). entry = STRAIGHT into the opening field, no menu (single-journey only; "
                         "keeps the real opening FMV).")
    ap.add_argument("--wire-newgame", action="store_const", const="hub", dest="newgame",
                    help="back-compat alias for --newgame hub.")
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
        game = _game_or_none()
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
    # pre-flight the live FolderNames stack here too (Preview), so a superseded-folder collision shows up BEFORE
    # the user commits to --apply -- not as a mid-deploy abort. This cheap (no-build) pass sweeps ids + EVT names
    # only; an FBG-scene-name collision is verified by --apply's post-build re-check (it can't reach the game --
    # deploy_campaign's strict name check is the backstop), so a clean Preview is a strong but not total signal.
    game = _game_or_none()
    if game is not None:
        hub_name = manifest.hub.get("name") if manifest.hub else None
        rep = J.render_collision_report(J.preflight_collisions(plan, game, hub_name=hub_name))
        if rep:
            print("\n" + rep)
            print("(FBG scene-name collisions are only verified at --apply, after the offline build.)")
    print("DRY-RUN -- no game files touched. Either run the steps above one-by-one (PLAYTEST each), or run the "
          "whole thing with `--apply` (one unified revert).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
