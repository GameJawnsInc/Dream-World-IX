#!/usr/bin/env python3
"""Reversibly install a built import-chain CAMPAIGN into the live game + wire New Game to its entry field.

This generalizes ``install_tworoom.py`` (the hand-coded 2-field permanent install) to an arbitrary N-member
campaign produced by ``ff9mapkit import-chain --out`` + ``build-all``. The model is install_tworoom's, NOT
deploy_field's: ONE set-wide snapshot of the campaign mod folder + a WHOLESALE replace with the built dist
(never a per-id DictionaryPatch merge -- that's the sibling-clobber bug CLAUDE.md §3 documents) + ONE
``revert_campaign.py`` that restores the snapshot.

New-Game entry reuses the proven ``newgame_warp.py``: it patches the shared ``FF9CustomMap`` field-100 (+
field-70 with --stock) overrides to route New Game -> field 70 -> field 100 (entrance 231) -> the campaign's
entry field, so the player arrives WITH a party (NewGame() doesn't create one; field 100 does). The entry
id is globally registered (every mod folder's DictionaryPatch is merged at launch), so the warp target lands
even though it lives in a different folder than the warp. Because that warp edits FF9CustomMap (not the
campaign's mod folder), ``revert_campaign.py`` undoes BOTH the folder snapshot AND the warp.

SAFE BY DEFAULT: prints the plan and stops. Pass ``--apply`` to actually touch the game. I cannot see the
running game (Hard Constraint §2): after --apply, follow the printed manual steps (Memoria.ini FolderNames +
one relaunch) and PLAYTEST.

Usage:
  py tools/deploy_campaign.py <campaign.toml>                 # dry-run (prints the plan)
  py tools/deploy_campaign.py <campaign.toml> --apply --stock # install + wire New Game (stock+F6 engine)
"""
from __future__ import annotations

import argparse
import datetime
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
KIT = REPO / "ff9mapkit"
sys.path.insert(0, str(KIT))

from ff9mapkit import campaign as C            # noqa: E402
from ff9mapkit.config import ModLayout, find_game_path  # noqa: E402


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


def resolve_entry(plan: "C.CampaignPlan", entry_arg: str | None) -> int:
    """The New-Game target = the entry member's NEW field id. ``entry_arg`` may be a member NAME, an int id,
    or None (-> the manifest's entry_field, else the first member = id_base)."""
    by_name = {m.name: m for m in plan.members}
    if entry_arg:
        if entry_arg in by_name:
            return by_name[entry_arg].new_id
        return int(entry_arg)
    if plan.entry_name in by_name:
        return by_name[plan.entry_name].new_id
    if not plan.members:
        raise SystemExit("campaign has no members; nothing to enter")
    return plan.members[0].new_id


def expected_dist_summary(plan: "C.CampaignPlan") -> list[str]:
    """What the built dist will contain, derived from the manifest (no build needed) -- for the dry-run."""
    # native (atlas+.bgs) and editable (.bgx+layers) members ship a FieldMaps scene dir; borrow members
    # reuse the real field's art (no scene dir).
    scene_members = [m.name for m in plan.members if m.mode in ("native", "editable")]
    return [
        f"DictionaryPatch.txt  -- {len(plan.members)} FieldScene lines (ids "
        f"{plan.members[0].new_id}..{plan.members[-1].new_id})",
        f"EVT_<name>.eb.bytes  -- 7 langs x {len(plan.members)} members",
        f"FieldMaps/FBG_*      -- {len(scene_members)} member scene dir(s)" + (
            f" ({', '.join(scene_members)})" if scene_members else ""),
        "ModDescription.xml   -- InstallationPath = " + plan.mod_folder,
    ]


def render_revert_campaign(live_root: Path, snap: Path, warp_revert: Path | None, name: str, stamp: str) -> str:
    """The text of tools/scroll_out/revert_campaign.py: full-restore the mod folder + (if the warp ran) undo
    the shared FF9CustomMap New-Game patch."""
    lines = [
        f'"""Revert campaign {name} ({stamp}): restore {live_root.name} + undo the New-Game warp."""',
        "import shutil",
        "from pathlib import Path",
        f"live = Path(r{str(live_root)!r})",
        f"snap = Path(r{str(snap)!r})",
        "shutil.rmtree(live, ignore_errors=True)",
        "shutil.copytree(snap, live)",
        'print("restored", live)',
    ]
    if warp_revert is not None:
        lines += [
            "import runpy",
            f"warp_revert = Path(r{str(warp_revert)!r})",
            "if warp_revert.is_file():",
            '    runpy.run_path(str(warp_revert), run_name="__main__")',
            '    print("undid New-Game warp")',
        ]
    lines += [f'print("reverted campaign {name} {stamp}")', ""]
    return "\n".join(lines)


def _is_dist_dir(p: Path) -> bool:
    return p.is_dir() and (p / "DictionaryPatch.txt").is_file() and (p / "ModDescription.xml").is_file()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Reversibly install a campaign mod + wire New Game (P4).")
    ap.add_argument("target", help="path to campaign.toml (built fresh) OR a prebuilt dist/ directory")
    ap.add_argument("--mod-folder", dest="mod_folder", default=None,
                    help="Memoria mod folder to install into (default: .ff9deploy.toml / $FF9_MOD_FOLDER)")
    ap.add_argument("--entry", default=None, help="New-Game entry: member name, field id, or omit for the manifest entry")
    ap.add_argument("--stock", action="store_true", help="add the field-70->field-100 hop (stock + F6 engine)")
    ap.add_argument("--out-dist", dest="out_dist", default=None, help="where to stage the build (default: temp)")
    ap.add_argument("--allow-artless", action="store_true", dest="allow_artless",
                    help="install editable members that lack exported art (they render with NO background)")
    ap.add_argument("--no-warp", action="store_true", dest="no_warp", help="install the mod but skip New-Game wiring")
    ap.add_argument("--apply", action="store_true", help="ACTUALLY touch the game (default: dry-run, prints the plan)")
    args = ap.parse_args(argv)

    target = Path(args.target)
    mod_folder = resolve_mod_folder(args.mod_folder)

    # --- load the plan (from a prebuilt dist's sibling manifest, or the manifest itself) ---
    if _is_dist_dir(target):
        manifest = target.parent / "campaign.toml"
        if not manifest.is_file():
            raise SystemExit(f"prebuilt dist {target} has no sibling campaign.toml; pass the manifest instead")
        plan = C.load_campaign(manifest)
        prebuilt_dist = target
    else:
        plan = C.load_campaign(target)
        prebuilt_dist = None

    entry_id = resolve_entry(plan, args.entry)
    entry_name = next((m.name for m in plan.members if m.new_id == entry_id), str(entry_id))
    game = find_game_path()
    live_root = game / mod_folder
    member_ids = [m.new_id for m in plan.members]

    # --- lint (offline; aborts on structural errors) ---
    errors, warnings = C.lint_campaign(plan, target.parent if not _is_dist_dir(target) else target.parent.parent)
    for w in warnings:
        print("  warn:", w)
    if errors:
        print("campaign lint FAILED:", file=sys.stderr)
        for e in errors:
            print("  error:", e, file=sys.stderr)
        return 2

    # --- the plan (always printed) ---
    print(f"campaign '{plan.name}'  ->  mod folder '{mod_folder}'  ({live_root})")
    print(f"  members: {len(plan.members)}  ids {member_ids[0]}..{member_ids[-1]}")
    print(f"  New Game entry: {entry_name} (field {entry_id})")
    route = (f"New Game -> field 70 -> field 100 (entrance 231) -> field {entry_id}" if args.stock
             else f"New Game (dev engine) -> field 100 (entrance 231) -> field {entry_id}")
    print(f"  route: {'(skipped --no-warp)' if args.no_warp else route}")
    print("  dist will contain:")
    for line in expected_dist_summary(plan):
        print("    " + line)
    if plan.needs_export and not args.allow_artless:
        print(f"REFUSING: members need in-game art (export + re-fork, or --allow-artless): {plan.needs_export}",
              file=sys.stderr)
        return 2

    if not args.apply:
        print("\nDRY-RUN -- no game files touched. Re-run with --apply to install.")
        return 0

    # ===================== --apply: touch the game (reversibly) =====================
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    # (1) build the dist (unless a prebuilt dist was given)
    if prebuilt_dist is not None:
        dist_root = prebuilt_dist
    else:
        out = Path(args.out_dist) if args.out_dist else (target.parent / "dist")
        info = C.build_campaign(target, out=out, allow_artless=args.allow_artless)
        dist_root = Path(info["out"])
        for w in info["warnings"]:
            print("  warn:", w)
    if not (dist_root / "DictionaryPatch.txt").is_file():
        raise SystemExit(f"build produced no DictionaryPatch.txt at {dist_root}")

    # (2) bootstrap a fresh mod folder so the snapshot has something to copy (deploy_field pattern)
    live_root.mkdir(parents=True, exist_ok=True)
    live = ModLayout(live_root)
    if not live.mod_description.exists():
        live.mod_description.write_text(
            f"<Mod>\n    <Name>{mod_folder}</Name>\n    <Author></Author>\n"
            f"    <InstallationPath>{mod_folder}</InstallationPath>\n    <Category></Category>\n"
            f"    <Description></Description>\n</Mod>\n", encoding="utf-8", newline="\n")
    if not live.dictionary_patch.exists():
        live.dictionary_patch.write_text("", encoding="utf-8", newline="\n")

    # (3) ONE set-wide snapshot, then (4) WHOLESALE replace (install_tworoom model)
    snap = REPO / "backups" / f"{mod_folder}.pre-{plan.name}.{stamp}"
    snap.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(live_root, snap)
    print(f"snapshot {live_root} -> {snap}")
    shutil.rmtree(live_root, ignore_errors=True)
    shutil.copytree(dist_root, live_root)
    print(f"installed dist -> {live_root}  ({len(plan.members)} fields)")

    # (5) New-Game wiring via the proven newgame_warp.py (patches the SHARED FF9CustomMap field-100/70
    #     overrides; the entry id is globally registered so the warp lands). Reversible separately.
    warp_revert = None
    if not args.no_warp:
        cmd = [sys.executable, str(HERE / "newgame_warp.py"), str(entry_id)] + (["--stock"] if args.stock else [])
        print(f"wiring New Game: {' '.join(cmd)}")
        rc = subprocess.run(cmd, cwd=str(REPO)).returncode
        if rc != 0:
            print("  WARNING: newgame_warp failed (FF9CustomMap field-100/70 overrides missing?). The campaign\n"
                  "  is installed; wire New Game manually once those overrides exist, or reach fields via F6 Warp.")
        else:
            wr = HERE / "scroll_out" / "revert_newgame_warp.py"
            warp_revert = wr if wr.is_file() else None

    # (6) emit the single full-restore revert
    out_dir = HERE / "scroll_out"
    out_dir.mkdir(exist_ok=True)
    rev = out_dir / "revert_campaign.py"
    rev.write_text(render_revert_campaign(live_root, snap, warp_revert, plan.name, stamp),
                   encoding="utf-8", newline="\n")

    # (7) the manual steps this script cannot perform
    print("\n=== MANUAL STEPS (deploy_campaign cannot do these) ===")
    print(f"1. Ensure Memoria.ini [Mod] FolderNames includes \"{mod_folder}\" (else its DictionaryPatch is")
    print("   never read at launch). deploy_campaign does NOT edit Memoria.ini.")
    print(f"2. RELAUNCH the game ONCE -- these are NEW ids ({member_ids[0]}..{member_ids[-1]}); their")
    print("   FieldScene lines only register on a fresh launch (F6 Reload alone won't register a new id).")
    print(f"3. New Game now lands in {entry_name} (field {entry_id}).  F6 -> Warp reaches any member.")
    if not args.no_warp and warp_revert is not None:
        print("   (New-Game route patched the SHARED FF9CustomMap field-100/70 overrides -- only one campaign")
        print("    can own New Game at a time; revert_campaign.py undoes it.)")
    print(f"Then PLAYTEST and report.   revert: py {rev.relative_to(REPO).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
