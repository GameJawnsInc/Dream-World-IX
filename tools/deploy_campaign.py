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

Two productionization guards (the lessons from the Dali-chain session) run automatically:
  * NAME-COLLISION CHECK -- scene (``FBG_*``) and event (``EVT_*.eb.bytes``) files resolve BY NAME,
    highest-FolderNames-folder-wins, so two worktrees that fork the SAME source field deploy identically-named
    files into different folders and the WRONG fork loads (a silent shadow -> black screen). Before install we
    compare the built dist's names against the other live FolderNames folders and ABORT on a collision (the fix
    is ``import-chain --name-prefix <TAG>``; override with ``--allow-name-collision``).
  * START-STATE CSV PROMOTION -- a campaign installs into its OWN mod folder, usually NOT the highest, so its
    new-game ``InitialItems.csv`` (read highest-priority-wins) would be shadowed. When the campaign claims New
    Game we PROMOTE the entry field's ``InitialItems/DefaultEquipment/ShopItems`` CSVs to the highest folder
    (reversibly; single-owner, like the warp). Skip with ``--no-promote-csv`` / retarget with ``--promote-csv-to``.

SAFE BY DEFAULT: prints the plan and stops. Pass ``--apply`` to actually touch the game. I cannot see the
running game (Hard Constraint §2): after --apply, follow the printed manual steps (Memoria.ini FolderNames +
one relaunch) and PLAYTEST.

Usage:
  py tools/deploy_campaign.py <campaign.toml>                 # dry-run (prints the plan + guards)
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
from ff9mapkit import deploystack as DS        # noqa: E402
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


def render_revert_campaign(live_root: Path, snap: Path, warp_revert: Path | None, name: str, stamp: str,
                           csv_reverts: list | None = None) -> str:
    """The text of tools/scroll_out/revert_campaign.py: full-restore the mod folder + (if the warp ran) undo
    the shared FF9CustomMap New-Game patch + (if start-state CSVs were promoted to the highest folder) restore
    or remove those. ``csv_reverts`` is a list of ``(dst_path, backup_path_or_None)``: a backup => restore it,
    ``None`` => the CSV was newly created, so delete it on revert."""
    lines = [
        f'"""Revert campaign {name} ({stamp}): restore {live_root.name} + undo the New-Game warp."""',
        "import shutil",
        "from pathlib import Path",
        f"live = Path(r{str(live_root)!r})",
        f"snap = Path(r{str(snap)!r})",
        "if snap.is_dir():",
        "    shutil.rmtree(live, ignore_errors=True)",
        "    shutil.copytree(snap, live)",
        '    print("restored", live)',
        "else:",          # never rmtree the live folder when there's no snapshot to restore from
        '    print("WARNING: snapshot missing -- left", live, "untouched:", snap)',
    ]
    if warp_revert is not None:
        lines += [
            "import runpy",
            f"warp_revert = Path(r{str(warp_revert)!r})",
            "if warp_revert.is_file():",
            '    runpy.run_path(str(warp_revert), run_name="__main__")',
            '    print("undid New-Game warp")',
        ]
    if csv_reverts:
        lines += ["CSV_REVERTS = ["]
        lines += [f"    ({dst!r}, {bkp!r})," for dst, bkp in csv_reverts]
        lines += [
            "]",
            "for _dst, _bkp in CSV_REVERTS:",
            "    _dst = Path(_dst)",
            "    if _bkp is None:",                                  # the CSV was newly created -> delete it
            "        if _dst.exists(): _dst.unlink(); print('removed promoted', _dst)",
            "    elif Path(_bkp).is_file():",                        # a prior copy was backed up -> restore it
            "        shutil.copyfile(_bkp, _dst); print('restored promoted', _dst)",
            "    else:",                                             # backup vanished -> don't crash the whole revert
            "        print('WARNING: backup missing -- left', _dst, 'as-is:', _bkp)",
        ]
    lines += [f'print("reverted campaign {name} {stamp}")', ""]
    return "\n".join(lines)


def folder_order(game) -> list:
    """The Memoria.ini ``FolderNames`` priority list (highest first), or ``[]`` when it can't be read."""
    ini = Path(game) / "Memoria.ini"
    if not ini.is_file():
        return []
    return DS.parse_folder_names(ini.read_text(encoding="utf-8", errors="ignore"))


def resolve_highest_folder(order: list, override: str | None) -> str:
    """The folder start-state CSVs should be promoted into: the explicit override, else the highest-priority
    FolderNames folder, else the canonical primary ``FF9CustomMap`` (when the stack can't be read)."""
    return override or (order[0] if order else "FF9CustomMap")


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
    ap.add_argument("--allow-name-collision", action="store_true", dest="allow_name_collision",
                    help="install even when EVT/FBG names collide with another FolderNames folder (default: ABORT; "
                         "the proper fix is to re-fork with `import-chain --name-prefix <TAG>`)")
    ap.add_argument("--no-promote-csv", action="store_true", dest="no_promote_csv",
                    help="do NOT promote the entry field's start-state CSVs (InitialItems/DefaultEquipment/ShopItems) "
                         "to the highest FolderNames folder (default: promote when this campaign claims New Game)")
    ap.add_argument("--promote-csv-to", dest="promote_csv_to", default=None,
                    help="folder to promote start-state CSVs into (default: the highest Memoria.ini FolderNames folder)")
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
    order = folder_order(game)
    highest = resolve_highest_folder(order, args.promote_csv_to)
    # promote start-state CSVs only when this campaign actually CLAIMS New Game (a --no-warp slice -- e.g. a World
    # Hub journey -- shares the global bag/gear and seeds per-journey via scripted give_item instead) and the
    # campaign folder isn't already the highest (in which case the wholesale install already placed them right).
    will_promote = (not args.no_promote_csv) and (not args.no_warp) and (highest != mod_folder)

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
    # start-state CSV promotion plan
    if args.no_promote_csv:
        csv_note = "skipped (--no-promote-csv)"
    elif args.no_warp:
        csv_note = "in place (--no-warp: this campaign doesn't claim New Game)"
    elif highest == mod_folder:
        csv_note = f"in place ('{mod_folder}' is already the highest FolderNames folder)"
    else:
        csv_note = (f"will PROMOTE to highest folder '{highest}' (reversible; single-owner -- "
                    f"clobbers that folder's prior start-state)")
    print(f"  start-state CSVs: {csv_note}")
    # name-collision preview: EVT names from the manifest (FBG scene names are also checked at --apply vs the
    # built dist). A same-named scene/.eb in another stacked folder serves the WRONG fork -> torn load.
    plan_eb = {f"EVT_{m.name}" for m in plan.members}
    cwarn = DS.name_collision_warning(
        DS.check_name_collisions(game, mod_folder, plan_eb, set(), folder_names=order), mod_folder)
    if cwarn:
        print("  !! " + cwarn.replace("\n", "\n     "))
    print("  name check: EVT names checked now vs the FolderNames stack; FBG scene names are also verified at "
          "--apply (vs the built dist), so --apply may catch a collision a clean dry-run did not.")
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

    # (1.5) authoritative name-collision check against the BUILT dist (EVT + FBG scene names = ground truth). A
    #       same-named file in another stacked folder silently serves the WRONG fork -> torn load / black screen
    #       (the cross-worktree shadow that --name-prefix prevents). Abort before touching any live file.
    cwarn = DS.name_collision_warning(
        DS.check_name_collisions(game, mod_folder, DS.eb_names_at(dist_root), DS.scene_names_at(dist_root),
                                 folder_names=order), mod_folder)
    if cwarn:
        print("\n  !! " + cwarn)
        if not args.allow_name_collision:
            print("\nABORTING before install (no game files touched). Re-fork with `import-chain --name-prefix "
                  "<TAG>`, or pass --allow-name-collision to install anyway.", file=sys.stderr)
            return 2

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

    # prepare the revert emitter up front: the campaign is already installed + wired, so a LATER partial failure
    # (CSV promotion) must still leave a COMPLETE revert for whatever was touched (reversibility is the contract).
    out_dir = HERE / "scroll_out"
    out_dir.mkdir(exist_ok=True)
    rev = out_dir / "revert_campaign.py"
    csv_reverts: list = []

    def _write_revert():
        rev.write_text(render_revert_campaign(live_root, snap, warp_revert, plan.name, stamp, csv_reverts),
                       encoding="utf-8", newline="\n")

    # (5.5) promote the entry field's start-state CSVs to the HIGHEST folder so they win at New Game. The
    #       campaign installs into its OWN folder, usually NOT the highest -> InitialItems.csv (read
    #       HIGHEST-PRIORITY-WINS) would be silently shadowed; the others (DefaultEquipment/ShopItems) merge,
    #       but promoting guarantees this campaign's rows win. Reversible; single-owner (the global bag/gear is
    #       shared, like the New-Game warp). Source = the dist CSVs just installed into live_root.
    if will_promote:
        src_l, dst_l = ModLayout(live_root), ModLayout(game / highest)
        try:
            for src_csv, dst_csv, label in ((src_l.initial_items_csv, dst_l.initial_items_csv, "InitialItems"),
                                            (src_l.default_equipment_csv, dst_l.default_equipment_csv, "DefaultEquipment"),
                                            (src_l.shop_items_csv, dst_l.shop_items_csv, "ShopItems")):
                if not src_csv.exists():
                    continue
                dst_csv.parent.mkdir(parents=True, exist_ok=True)
                bk = None
                if dst_csv.exists():
                    bk = snap.parent / f"{label}.csv.pre-{plan.name}.{stamp}"
                    shutil.copyfile(dst_csv, bk)
                shutil.copyfile(src_csv, dst_csv)
                csv_reverts.append((str(dst_csv), str(bk) if bk else None))
                print(f"  promoted {label}.csv -> {highest}" + (" (backed up prior)" if bk else " (new)"))
        except OSError as e:
            _write_revert()    # campaign already live + wired -> leave a usable revert for the partial state
            print(f"\nERROR promoting start-state CSVs to '{highest}': {e}", file=sys.stderr)
            print(f"The campaign is installed + wired but CSV promotion is INCOMPLETE. "
                  f"Revert with: py {rev.relative_to(REPO).as_posix()}", file=sys.stderr)
            return 2
        if csv_reverts:
            print(f"start-state CSVs promoted to highest folder '{highest}' (revert restores its prior copies).")
        else:
            print("(no start-state CSVs in the dist to promote -- entry field has no [start_inventory]/[[equipment]])")

    # (6) emit the single full-restore revert
    _write_revert()

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
    if will_promote and csv_reverts:
        print(f"   (start-state CSVs were promoted to \"{highest}\" so the New-Game bag/gear win -- also a")
        print("    SINGLE-OWNER write; revert_campaign.py restores that folder's prior CSVs.)")
    print(f"Then PLAYTEST and report.   revert: py {rev.relative_to(REPO).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
