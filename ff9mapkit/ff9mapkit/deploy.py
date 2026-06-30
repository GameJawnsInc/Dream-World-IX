"""Multi-field DEPLOY -- install a built campaign (and, later, a journey) into the live game.

This is the package home of the orchestration that ``tools/deploy_campaign.py`` / ``tools/deploy_journey.py``
drive (now thin shims) and the installed ``ff9mapkit deploy-campaign`` / ``deploy-journey`` CLI calls. The
BUILD + collision + link + merge logic already lives in :mod:`campaign` / :mod:`journey` / :mod:`deploystack`;
what was repo-only is the deploy *orchestration*: ONE set-wide snapshot of the mod folder + a WHOLESALE replace
with the built dist (the install_tworoom model, NOT a per-id DictionaryPatch merge), New-Game wiring (via
:mod:`newgame`, a direct call -- no subprocess), start-state CSV promotion, and a single reversible
``revert_*.py``.

The caller supplies ``backups_dir`` + ``reverts_dir`` (where the snapshot + revert script go), so the dev loop
writes into ``backups/`` + ``tools/scroll_out/`` while an installed copy uses a per-user cache. Mechanism +
gotchas: CLAUDE.md §3/§4, memory ``project-ff9-new-game-entry``.
"""
from __future__ import annotations

import datetime
import shutil
import sys
from pathlib import Path

from . import campaign as C
from . import deploystack as DS
from . import newgame
from .config import LANGS, ModLayout, find_game_path

# Start-state learn lists (a FILE SET) read highest-priority-wins -> promoted alongside the start CSVs.
_PRESET_STEMS = {"Zidane", "Vivi", "Garnet", "Steiner", "Freya", "Quina", "Eiko", "Amarant", "Cinna1",
                 "Cinna2", "Marcus1", "Marcus2", "Blank1", "Blank2", "Beatrix1", "Beatrix2", "StageZidane",
                 "StageCinna", "StageMarcus", "StageBlank"}


class DeployError(Exception):
    """A fatal misconfiguration (e.g. a prebuilt dist with no sibling manifest). Callers map it to exit 2."""


def _emit(verbose: bool):
    """Return ``(out, err)`` print functions -- real prints when verbose, no-ops otherwise."""
    if verbose:
        return print, (lambda *a, **k: print(*a, file=sys.stderr, **k))
    noop = lambda *a, **k: None       # noqa: E731
    return noop, noop


# --------------------------------------------------------------------------- pure helpers (portable)
def expected_dist_summary(plan) -> list[str]:
    """What the built dist will contain, derived from the manifest (no build needed) -- for the dry-run."""
    scene_members = [m.name for m in plan.members if m.mode in ("native", "editable")]
    return [
        f"DictionaryPatch.txt  -- {len(plan.members)} FieldScene lines (ids "
        f"{plan.members[0].new_id}..{plan.members[-1].new_id})",
        f"EVT_<name>.eb.bytes  -- 7 langs x {len(plan.members)} members",
        f"FieldMaps/FBG_*      -- {len(scene_members)} member scene dir(s)" + (
            f" ({', '.join(scene_members)})" if scene_members else ""),
        "ModDescription.xml   -- InstallationPath = " + plan.mod_folder,
    ]


def resolve_entry(plan, entry_arg) -> int:
    """The New-Game target = the entry member's NEW field id. ``entry_arg`` may be a member NAME, an int id,
    or None (-> the manifest's entry_field, else the first member)."""
    by_name = {m.name: m for m in plan.members}
    if entry_arg is not None and str(entry_arg) != "":
        if str(entry_arg) in by_name:
            return by_name[str(entry_arg)].new_id
        return int(entry_arg)
    if plan.entry_name in by_name:
        return by_name[plan.entry_name].new_id
    if not plan.members:
        raise DeployError("campaign has no members; nothing to enter")
    return plan.members[0].new_id


def folder_order(game) -> list:
    """The Memoria.ini ``FolderNames`` priority list (highest first), or ``[]`` when it can't be read."""
    ini = Path(game) / "Memoria.ini"
    if not ini.is_file():
        return []
    return DS.parse_folder_names(ini.read_text(encoding="utf-8", errors="ignore"))


def resolve_highest_folder(order, override) -> str:
    """The folder start-state CSVs should be promoted into: the explicit override, else the highest-priority
    FolderNames folder, else the canonical primary ``FF9CustomMap`` (when the stack can't be read)."""
    return override or (order[0] if order else "FF9CustomMap")


def is_dist_dir(p) -> bool:
    p = Path(p)
    return p.is_dir() and (p / "DictionaryPatch.txt").is_file() and (p / "ModDescription.xml").is_file()


def render_revert_campaign(live_root, snap, warp_revert, name, stamp, csv_reverts=None) -> str:
    """Text of revert_campaign.py: full-restore the mod folder + (if the warp ran) undo the shared FF9CustomMap
    New-Game patch + (if start-state CSVs were promoted) restore/remove those. ``csv_reverts`` =
    ``[(dst, backup_or_None), ...]`` (a backup => restore; None => the CSV was newly created => delete it)."""
    live_root, snap = Path(live_root), Path(snap)
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
        "else:",
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
            "    if _bkp is None:",
            "        if _dst.exists(): _dst.unlink(); print('removed promoted', _dst)",
            "    elif Path(_bkp).is_file():",
            "        shutil.copyfile(_bkp, _dst); print('restored promoted', _dst)",
            "    else:",
            "        print('WARNING: backup missing -- left', _dst, 'as-is:', _bkp)",
        ]
    lines += [f'print("reverted campaign {name} {stamp}")', ""]
    return "\n".join(lines)


# --------------------------------------------------------------------------- campaign deploy
def deploy_campaign(target, *, game=None, mod_folder="FF9CustomMap", entry=None, apply=False,
                    allow_artless=False, no_warp=False, allow_name_collision=False, allow_id_collision=False,
                    flag_base=None, no_promote_csv=False, promote_csv_to=None, out_dist=None,
                    backups_dir, reverts_dir, verbose=True) -> dict:
    """Reversibly install a built campaign mod into ``<game>/<mod_folder>`` + wire New Game to its entry.

    SAFE BY DEFAULT: with ``apply=False`` it lints + prints the plan + collision preview and touches nothing.
    With ``apply=True`` it builds (unless ``target`` is a prebuilt dist dir), runs the name/id/text-shadow
    guards, snapshots the live folder to ``backups_dir``, wholesale-replaces it with the dist, retargets the
    field-70 New-Game override (unless ``no_warp``), promotes start-state CSVs to the highest folder, and writes
    ``revert_campaign.py`` into ``reverts_dir``. Returns a report dict with ``rc`` (0 ok / 2 abort) + ``revert``.
    Raises :class:`DeployError` on a fatal misconfiguration."""
    out, err = _emit(verbose)
    game = Path(game) if game is not None else find_game_path()
    backups_dir, reverts_dir = Path(backups_dir), Path(reverts_dir)
    target = Path(target)
    report: dict = {"ok": False, "rc": 2, "applied": False, "mod_folder": mod_folder,
                    "entry_id": None, "entry_name": None, "members": 0, "revert": None, "warp_revert": None}

    # --- load the plan (from a prebuilt dist's sibling manifest, or the manifest itself) ---
    if is_dist_dir(target):
        manifest = target.parent / "campaign.toml"
        if not manifest.is_file():
            raise DeployError(f"prebuilt dist {target} has no sibling campaign.toml; pass the manifest instead")
        plan = C.load_campaign(manifest)
        prebuilt_dist = target
    else:
        plan = C.load_campaign(target)
        prebuilt_dist = None

    entry_id = resolve_entry(plan, entry)
    entry_name = next((m.name for m in plan.members if m.new_id == entry_id), str(entry_id))
    live_root = game / mod_folder
    member_ids = [m.new_id for m in plan.members]
    order = folder_order(game)
    highest = resolve_highest_folder(order, promote_csv_to)
    will_promote = (not no_promote_csv) and (not no_warp) and (highest != mod_folder)
    report.update(entry_id=entry_id, entry_name=entry_name, members=len(plan.members))

    # --- lint (offline; aborts on structural errors) ---
    errors, warnings = C.lint_campaign(plan, target.parent)
    for w in warnings:
        out("  warn:", w)
    if errors:
        err("campaign lint FAILED:")
        for e in errors:
            err("  error:", e)
        return report

    # --- the plan (always printed) ---
    out(f"campaign '{plan.name}'  ->  mod folder '{mod_folder}'  ({live_root})")
    out(f"  members: {len(plan.members)}  ids {member_ids[0]}..{member_ids[-1]}")
    out(f"  New Game entry: {entry_name} (field {entry_id})")
    route = f"New Game -> field 70 override -> Field({entry_id})  (direct retarget)"
    out(f"  route: {'(skipped --no-warp)' if no_warp else route}")
    out("  dist will contain:")
    for line in expected_dist_summary(plan):
        out("    " + line)
    if no_promote_csv:
        csv_note = "skipped (--no-promote-csv)"
    elif no_warp:
        csv_note = "in place (--no-warp: this campaign doesn't claim New Game)"
    elif highest == mod_folder:
        csv_note = f"in place ('{mod_folder}' is already the highest FolderNames folder)"
    else:
        csv_note = (f"will PROMOTE to highest folder '{highest}' (reversible; single-owner -- "
                    f"clobbers that folder's prior start-state)")
    out(f"  start-state CSVs: {csv_note}")
    plan_eb = {f"EVT_{m.name}" for m in plan.members}
    cwarn = DS.name_collision_warning(
        DS.check_name_collisions(game, mod_folder, plan_eb, set(), folder_names=order), mod_folder)
    if cwarn:
        out("  !! " + cwarn.replace("\n", "\n     "))
    out("  name check: EVT names checked now vs the FolderNames stack; FBG scene names are also verified at "
        "--apply (vs the built dist), so --apply may catch a collision a clean dry-run did not.")
    out("  text-shadow check: each member's dialogue .mes block is verified at --apply (vs the built dist).")
    if plan.needs_export and not allow_artless:
        err(f"REFUSING: members need in-game art (export + re-fork, or allow_artless): {plan.needs_export}")
        return report

    if not apply:
        out("\nDRY-RUN -- no game files touched. Re-run with apply=True to install.")
        report.update(ok=True, rc=0)
        return report

    # ===================== apply: touch the game (reversibly) =====================
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    # (1) build the dist (unless a prebuilt dist was given)
    if prebuilt_dist is not None:
        dist_root = prebuilt_dist
    else:
        out_d = Path(out_dist) if out_dist else (target.parent / "dist")
        info = C.build_campaign(target, out=out_d, allow_artless=allow_artless, flag_base=flag_base)
        dist_root = Path(info["out"])
        for w in info["warnings"]:
            out("  warn:", w)
    if not (dist_root / "DictionaryPatch.txt").is_file():
        raise DeployError(f"build produced no DictionaryPatch.txt at {dist_root}")

    # (1.5) authoritative name-collision check vs the BUILT dist (EVT + FBG scene names = ground truth)
    cwarn = DS.name_collision_warning(
        DS.check_name_collisions(game, mod_folder, DS.eb_names_at(dist_root), DS.scene_names_at(dist_root),
                                 folder_names=order), mod_folder)
    if cwarn:
        out("\n  !! " + cwarn)
        if not allow_name_collision:
            err("\nABORTING before install (no game files touched). Re-fork with `import-chain --name-prefix "
                "<TAG>`, or pass allow_name_collision to install anyway.")
            return report

    # (1.6) id-collision check (GLOBAL EventDB)
    iwarn = DS.id_collision_warning(
        DS.check_id_collisions(game, mod_folder, DS.dictionary_ids_at(dist_root).keys(), folder_names=order),
        mod_folder)
    if iwarn:
        out("\n  !! " + iwarn)
        if not allow_id_collision:
            err("\nABORTING before install (no game files touched). Use ids no other stacked folder registers, "
                "or pass allow_id_collision to install anyway.")
            return report

    # (1.7) text-block SHADOW check (WARN, don't abort)
    _dist_blocks = set().union(*(DS.blocks_at(dist_root, L) for L in LANGS))
    twarn = DS.text_shadow_warning(
        DS.check_text_block_shadows(game, mod_folder, _dist_blocks, folder_names=order), mod_folder)
    if twarn:
        out("\n  !! " + twarn)

    # (2) bootstrap a fresh mod folder so the snapshot has something to copy
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
    snap = backups_dir / f"{mod_folder}.pre-{plan.name}.{stamp}"
    snap.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(live_root, snap)
    out(f"snapshot {live_root} -> {snap}")
    shutil.rmtree(live_root, ignore_errors=True)
    shutil.copytree(dist_root, live_root)
    out(f"installed dist -> {live_root}  ({len(plan.members)} fields)")
    report["applied"] = True

    # (5) New-Game wiring: retarget the SHARED FF9CustomMap field-70 override -> the entry id (direct
    #     newgame.retarget call -- no subprocess). Reversible separately; revert_campaign wraps it.
    warp_revert = None
    if not no_warp:
        out(f"wiring New Game: field-70 override -> Field({entry_id})")
        res = newgame.retarget(game, entry_id, backups_dir=backups_dir, reverts_dir=reverts_dir, verbose=verbose)
        if not res["ok"]:
            out("  WARNING: New-Game retarget did not wire (no field-70 override evt_alex1_ts_opening.eb.bytes in\n"
                "  a FolderNames folder?). The campaign is installed; wire New Game once that override exists, or\n"
                "  reach the chain via F6 -> Warp.")
        else:
            warp_revert = res["revert"]
    report["warp_revert"] = warp_revert

    # prepare the revert emitter up front (the campaign is already installed + wired -> a later partial failure
    # must still leave a COMPLETE revert for whatever was touched).
    reverts_dir.mkdir(parents=True, exist_ok=True)
    rev = reverts_dir / "revert_campaign.py"
    csv_reverts: list = []

    def _write_revert():
        rev.write_text(render_revert_campaign(live_root, snap, warp_revert, plan.name, stamp, csv_reverts),
                       encoding="utf-8", newline="\n")

    # (5.5) promote the entry field's start-state CSVs to the HIGHEST folder so they win at New Game.
    if will_promote:
        src_l, dst_l = ModLayout(live_root), ModLayout(game / highest)
        _promote = [(src_l.initial_items_csv, dst_l.initial_items_csv, "InitialItems"),
                    (src_l.default_equipment_csv, dst_l.default_equipment_csv, "DefaultEquipment"),
                    (src_l.shop_items_csv, dst_l.shop_items_csv, "ShopItems"),
                    (src_l.leveling_csv, dst_l.leveling_csv, "Leveling")]
        _abil = src_l.abilities_csv("Zidane").parent
        if _abil.is_dir():
            for _f in sorted(_abil.glob("*.csv")):
                if _f.stem in _PRESET_STEMS:
                    _promote.append((_f, dst_l.abilities_csv(_f.stem), _f.stem))
        try:
            for src_csv, dst_csv, label in _promote:
                if not src_csv.exists():
                    continue
                dst_csv.parent.mkdir(parents=True, exist_ok=True)
                bk = None
                if dst_csv.exists():
                    bk = backups_dir / f"{label}.csv.pre-{plan.name}.{stamp}"
                    shutil.copyfile(dst_csv, bk)
                shutil.copyfile(src_csv, dst_csv)
                csv_reverts.append((str(dst_csv), str(bk) if bk else None))
                out(f"  promoted {label}.csv -> {highest}" + (" (backed up prior)" if bk else " (new)"))
        except OSError as e:
            _write_revert()
            err(f"\nERROR promoting start-state CSVs to '{highest}': {e}")
            err(f"The campaign is installed + wired but CSV promotion is INCOMPLETE. Revert with: py {rev}")
            report["revert"] = rev
            return report
        if csv_reverts:
            out(f"start-state CSVs promoted to highest folder '{highest}' (revert restores its prior copies).")
        else:
            out("(no start-state CSVs in the dist to promote -- entry field has no [start_inventory]/[[equipment]])")

    # (6) emit the single full-restore revert
    _write_revert()
    report["revert"] = rev

    # (7) the manual steps this script cannot perform
    out("\n=== MANUAL STEPS (deploy cannot do these) ===")
    out(f"1. Ensure Memoria.ini [Mod] FolderNames includes \"{mod_folder}\" (else its DictionaryPatch is")
    out("   never read at launch). Deploy does NOT edit Memoria.ini -- Memoria auto-detects the folder.")
    out(f"2. RELAUNCH the game ONCE -- these are NEW ids ({member_ids[0]}..{member_ids[-1]}); their")
    out("   FieldScene lines only register on a fresh launch (F6 Reload alone won't register a new id).")
    out(f"3. New Game now lands in {entry_name} (field {entry_id}).  F6 -> Warp reaches any member.")
    out(f"Then PLAYTEST and report.   revert: py {rev}")
    report.update(ok=True, rc=0)
    return report
