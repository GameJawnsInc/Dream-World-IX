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
from . import dictpatch as DP
from . import newgame
from .config import LANGS, ModLayout, find_game_path


def _foreign_regs_wiped(live, dist_root) -> list:
    """The FOREIGN ``3DModel``/``3DModelAnimation`` DictionaryPatch registrations a wholesale replace of
    ``live`` (a :class:`ModLayout`) with ``dist_root`` would silently drop -- present in the live folder,
    absent from the dist. A safety net for the ``model-anim-new``-between-deploys footgun."""
    live_dp = live.dictionary_patch
    dist_dp = Path(dist_root) / "DictionaryPatch.txt"
    if not live_dp.exists():
        return []
    before = live_dp.read_text(encoding="utf-8").splitlines()
    after = dist_dp.read_text(encoding="utf-8").splitlines() if dist_dp.exists() else []
    return DP.foreign_registrations_dropped(before, after)


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
    # foreign-registration guard: a WHOLESALE replace drops any 3DModel/3DModelAnimation line the dist doesn't
    # carry -- e.g. a clip `ff9mapkit model-anim-new` wrote directly into this folder's DictionaryPatch. The
    # snapshot restores them on REVERT, but the forward install silently loses them -> WARN loudly (CLAUDE.md
    # deploy footgun, 2026-07-08). Only reported; the wholesale replace is the campaign-owns-the-folder model.
    _lost = _foreign_regs_wiped(live, dist_root)
    if _lost:
        out("  !! WARNING: this wholesale install DROPS DictionaryPatch registration(s) not in the built dist "
            "(e.g. `model-anim-new` clips added to this folder since the last deploy). RE-ADD them after, or "
            "author them into the campaign. Reversible via the snapshot. Lost:")
        for _l in _lost:
            out(f"       {_l}")
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


# --------------------------------------------------------------------------- journey deploy
def _stamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


def _game_or_none():
    """``find_game_path`` RAISES when no install resolves; the dry-run / offline path wants a soft None."""
    try:
        return find_game_path()
    except Exception:
        return None


def _render_link_revert(results, stamp) -> str:
    """A revert that restores every backed-up boundary .eb the link step patched."""
    pairs = [(live, bkp) for r in results for live, bkp in r.get("backups", [])]
    lines = [f'"""Revert journey link rewrites ({stamp}): restore the boundary .eb backups."""',
             "import shutil", "from pathlib import Path", "PAIRS = ["]
    lines += [f"    ({live!r}, {bkp!r})," for live, bkp in pairs]
    lines += ["]", "for live, bkp in PAIRS:",
              "    if Path(bkp).is_file(): shutil.copyfile(bkp, live); print('restored', live)",
              "    else: print('WARNING: backup missing --', bkp)",
              f"print('reverted journey links {stamp}')", ""]
    return "\n".join(lines)


def _render_unified_revert(captured, stamp) -> str:
    """ONE revert that runs each captured per-step revert in REVERSE deploy order (undo New Game -> hub ->
    links -> campaigns). Each child revert is a complete, self-contained script run via runpy."""
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


def _render_folder_revert(live_root, snap, stamp) -> str:
    """A revert that restores a wholesale/overlay folder install from its pre-install snapshot."""
    return "\n".join([
        f'"""Revert journey folder install ({stamp}): restore {Path(live_root).name}."""',
        "import shutil", "from pathlib import Path",
        f"live = Path(r{str(live_root)!r})", f"snap = Path(r{str(snap)!r})",
        "if snap.is_dir():",
        "    shutil.rmtree(live, ignore_errors=True)",
        "    shutil.copytree(snap, live)",
        "    print('restored', live)",
        "else:",
        "    print('WARNING: snapshot missing -- left', live, 'untouched:', snap)",
        f"print('reverted folder install {stamp}')", ""])


def _capture_path(src, reverts_dir, dst_name):
    """Copy a step's returned revert script to a per-step name (so the next step's same-named revert can't
    overwrite it). Returns the captured path str, or None if the source wasn't written."""
    if not src:
        return None
    src = Path(src)
    if not src.is_file():
        return None
    reverts_dir = Path(reverts_dir)
    reverts_dir.mkdir(parents=True, exist_ok=True)
    dst = reverts_dir / dst_name
    shutil.copyfile(src, dst)
    return str(dst)


def _run_links(plan, game, stamp, *, backups_dir, reverts_dir, mod_folder_override=None, out=print):
    """Apply the cross-campaign link .eb rewrites. Returns ``(revert_path_or_None, all_wirable_links_found)``."""
    from . import journey as J
    wirable = [lk for lk in plan.links if lk.retargetable]
    if not wirable:
        out("  (no auto-wirable cross-campaign links -- overworld-only/ambiguous; see the playbook notes)")
        return None, True
    bdir = Path(backups_dir) / f"journey-links.{stamp}"
    results = J.apply_link_rewrites(plan, game, dry_run=False, backup_dir=bdir,
                                    mod_folder_override=mod_folder_override)
    ok = True
    for r in results:
        if r["found"] and r["mode"] == "worldmap_inject":
            out(f"  linked {r['eb']}: overworld exit -> Field({r['dst_id']}) region  "
                f"({r['regions']} region(s), {r['langs']} lang file(s))")
        elif r["found"]:
            out(f"  linked {r['eb']}: {r['remap']}  ({r['langs']} lang file(s))")
        elif r["mode"] == "worldmap_inject":
            ok = False
            out(f"  !! {r['eb']}: no tag-2 WorldMap walk-out region in the deployed .eb -- boundary a VERBATIM fork?")
        else:
            ok = False
            out(f"  !! {r['eb']}: no Field({list(r['remap'])[0] if r['remap'] else '?'}) in the deployed "
                f".eb -- boundary a VERBATIM fork?")
    if not any(r["found"] for r in results):
        return None, ok
    reverts_dir = Path(reverts_dir)
    reverts_dir.mkdir(parents=True, exist_ok=True)
    rev = reverts_dir / "revert_journey_links.py"
    rev.write_text(_render_link_revert(results, stamp), encoding="utf-8", newline="\n")
    return str(rev), ok


def _single_folder_name(manifest, single_folder) -> str:
    """The one merged ``FF9CustomMap-*`` folder name: an explicit ``single_folder`` if non-empty, else derived
    from the hub name (distinct from any campaign's own folder)."""
    from . import hub as _hub
    if isinstance(single_folder, str) and single_folder:
        nm = single_folder
        return nm if nm.startswith("FF9CustomMap") else f"FF9CustomMap-{nm}"
    token = _hub.name_token(manifest.hub.get("name", "journey")).lower() if manifest.hub else "journey"
    return f"FF9CustomMap-{token}"


def _install_hub(hub_toml, hub_id, hub_folder, game, *, backups_dir, reverts_dir, stamp, out):
    """Build the hub field.toml and install it into its DEDICATED folder via a non-destructive OVERLAY (so a
    prior New-Game override in that folder survives -- matching deploy_field's per-id merge spirit), snapshotting
    first. Returns the per-step revert path."""
    import tempfile

    from . import build as B
    live_root = Path(game) / hub_folder
    tmp = Path(tempfile.mkdtemp(prefix="ff9-hub-"))
    dist = tmp / "mod"
    B.build_mod([B.FieldProject.load(hub_toml)], dist, mod_name=hub_folder)
    live_root.mkdir(parents=True, exist_ok=True)
    snap = Path(backups_dir) / f"{hub_folder}.pre-hub-{hub_id}.{stamp}"
    snap.parent.mkdir(parents=True, exist_ok=True)
    if snap.exists():
        shutil.rmtree(snap, ignore_errors=True)
    shutil.copytree(live_root, snap)
    shutil.copytree(dist, live_root, dirs_exist_ok=True)    # overlay -- preserves a prior New-Game override
    out(f"installed hub field {hub_id} -> {live_root}  (snapshot {snap.name})")
    reverts_dir = Path(reverts_dir)
    reverts_dir.mkdir(parents=True, exist_ok=True)
    rev = reverts_dir / f"revert_journey_hub_{hub_id}.py"
    rev.write_text(_render_folder_revert(live_root, snap, stamp), encoding="utf-8", newline="\n")
    return str(rev)


def _apply_journey(manifest, plan, *, game, newgame, hub_out, backups_dir, reverts_dir, out, err):
    """The ONE-SHOT in-game deploy: each campaign (seeded entry) -> links -> hub -> New Game, with ONE unified
    revert. Returns ``(rc, unified_revert_path_or_None)``."""
    import tempfile

    from . import build as B
    from . import campaign as C
    from . import journey as J
    from . import newgame as _ng
    if plan.folder_conflicts:
        err("ABORT: campaigns share a mod_folder (deploy wholesale-replaces it):")
        for mf, a, b in plan.folder_conflicts:
            err(f"  {a!r} and {b!r} both -> {mf!r} -- give each its OWN mod_folder.")
        return 2, None
    if game is None:
        err("no FF9 install found -- can't deploy.")
        return 2, None
    if plan.hub_field_id is None:
        err("ABORT: the manifest has no [hub] id to deploy New Game into.")
        return 2, None

    hub_name = manifest.hub.get("name") if manifest.hub else None
    col = J.preflight_collisions(plan, game, hub_name=hub_name)
    if col.has_blockers:
        err("\n" + J.render_collision_report(col))
        return 2, None

    stamp = _stamp()
    highest = resolve_highest_folder(folder_order(game), None)
    hub_folder = plan.hub_folder or highest
    captured: list = []
    reverts_dir = Path(reverts_dir)
    reverts_dir.mkdir(parents=True, exist_ok=True)
    unified = reverts_dir / "revert_journey.py"

    def _flush():
        unified.write_text(_render_unified_revert(captured, stamp), encoding="utf-8", newline="\n")

    def _abort(msg):
        _flush()
        err(f"\nABORT mid-deploy: {msg}")
        err(f"Partial state is reversible: py {unified}")
        return 2, str(unified)

    # (0) PRE-FLIGHT (NO game files touched): build every campaign + emit/build the hub, all offline.
    hub_toml = Path(hub_out) if hub_out else (manifest.path.parent / "hub.field.toml")
    out("\n=== 0. pre-flight: build every campaign + the hub offline (no game files touched) ===")
    built: dict = {}
    for s in plan.campaign_steps:
        dist = s.campaign_path.parent / "dist"
        seednote = f" + seed {s.seed_blocks}" if s.seed_blocks else ""
        out(f"  building {s.folder} (flag_base {s.flag_base}{seednote}) -> {dist}")
        try:
            C.build_campaign(s.campaign_path, out=dist, flag_base=s.flag_base, seed_blocks=s.seed_blocks,
                             text_block_base=s.text_block_base, extra_flag_names=J.manifest_flag_names(manifest))
        except Exception as e:                            # noqa: BLE001
            err(f"\nABORT (no game files touched): campaign {s.folder} does not build -- {e}")
            return 2, None
        built[s.folder] = dist
    try:
        info = J.generate_hub(manifest.path, out_path=hub_toml, extract_camera=True, game=game)
        with tempfile.TemporaryDirectory() as td:
            B.build_mod([B.FieldProject.load(hub_toml)], Path(td) / "mod", mod_name="preflight")
    except Exception as e:                                # noqa: BLE001
        err(f"\nABORT (no game files touched): the hub does not build -- {e}")
        if any(k in str(e).lower() for k in ("borrow", "camera", "scene", ".bgx")):
            err("  Provision the hub camera: set [hub] borrow_field = <real field id> (auto-extracted via "
                "UnityPy), or place the [hub] camera .bgx beside the journeys.toml.")
        return 2, None
    out(f"  all {len(built)} campaign(s) + the hub build OK -> {hub_toml}  (camera: {info['spec'].camera})")

    col = J.preflight_collisions(plan, game, dists=built, hub_name=hub_name)
    if col.has_blockers:
        err("\n" + J.render_collision_report(col))
        return 2, None
    stale_note = J.render_collision_report(col)
    if stale_note:
        out("\n" + stale_note)

    # (1) INSTALL each prebuilt campaign dist -> its own stacked folder (no_warp; the hub owns New Game).
    out("\n=== 1. install campaigns ===")
    for s in plan.campaign_steps:
        rep = deploy_campaign(built[s.folder], game=game, mod_folder=s.mod_folder, apply=True, no_warp=True,
                              allow_id_collision=True, backups_dir=backups_dir, reverts_dir=reverts_dir,
                              verbose=(out is print))
        if rep["rc"] != 0:
            return _abort(f"campaign install for {s.folder} failed (rc {rep['rc']})")
        cap = _capture_path(rep["revert"], reverts_dir, f"revert_journey_campaign_{s.folder}.py")
        if cap:
            captured.append(cap)
        _flush()

    # (2) cross-campaign links (LAST relative to campaign deploys -- the wholesale-replace gotcha)
    out("\n=== 2. links ===")
    link_rev, links_ok = _run_links(plan, game, stamp, backups_dir=backups_dir, reverts_dir=reverts_dir, out=out)
    if link_rev:
        captured.append(link_rev)
        _flush()
    if not links_ok:
        return _abort("a cross-campaign link did not apply (see !! above)")

    # (3) deploy the hub field into its DEDICATED folder
    out(f"\n=== 3. hub (folder {hub_folder}) ===")
    try:
        hub_rev = _install_hub(hub_toml, plan.hub_field_id, hub_folder, game, backups_dir=backups_dir,
                               reverts_dir=reverts_dir, stamp=stamp, out=out)
    except Exception as e:                                # noqa: BLE001
        return _abort(f"hub install (id {plan.hub_field_id}) failed -- {e}")
    captured.append(hub_rev)
    _flush()

    # (4) OPTIONALLY point New Game at this journey -- into the SAME dedicated hub folder. SINGLE-OWNER, opt-in.
    if newgame in ("hub", "entry"):
        if newgame == "entry" and plan.entry_field_id is None:
            return _abort("newgame='entry' needs a SINGLE-journey manifest (a multi-journey hub has no single "
                          "opening -- use newgame='hub').")
        target = plan.hub_field_id if newgame == "hub" else plan.entry_field_id
        what = "the hub menu" if newgame == "hub" else "the opening, no menu"
        out(f"\n=== 4. New Game -> {what} (field {target}, folder {hub_folder}) ===")
        res = _ng.wire_from_stock(game, target, mod_folder=hub_folder, backups_dir=backups_dir,
                                  reverts_dir=reverts_dir, verbose=(out is print))
        if not res["ok"]:
            return _abort("New-Game wiring (wire_from_stock) failed")
        cap = _capture_path(res["revert"], reverts_dir, "revert_journey_newgame.py")
        if cap:
            captured.append(cap)
        _flush()
    else:
        out("\n=== 4. New Game: SKIPPED (New Game UNCHANGED; newgame='hub'|'entry' to opt in) ===")

    out("\n=== MANUAL STEPS (this tool cannot do these) ===")
    folders = [hub_folder] + [s.mod_folder for s in plan.campaign_steps]
    out("1. Memoria.ini [Mod] FolderNames -- STACK these (HIGHEST first), then your video/passthrough mods below:")
    out("   FolderNames = " + ", ".join(f'"{f}"' for f in folders) + ', "<your other mods, e.g. Moguri>"')
    if plan.campaign_steps:
        lo = min(s.id_lo for s in plan.campaign_steps)
        hi = max(s.id_hi for s in plan.campaign_steps)
        out(f"   This journey uses field ids {lo}..{hi} -- REMOVE any OTHER custom-field folder that deploys in "
            f"that range (EventDB is GLOBAL, so an overlap black-screens).")
    out("2. RELAUNCH once -- the new ids only register on a fresh launch.")
    if newgame == "hub":
        out(f"3. New Game now lands on the hub (field {plan.hub_field_id}); pick a journey, PLAYTEST.")
    elif newgame == "entry":
        out(f"3. New Game now lands STRAIGHT in the opening (field {plan.entry_field_id}) -- no menu; "
            f"PLAYTEST. (The hub still exists; reach it via F6 -> Warp {plan.hub_field_id}.)")
    else:
        out(f"3. Reach the hub via F6 -> Warp {plan.hub_field_id} (New Game is UNCHANGED). Pick a journey, PLAYTEST.")
    out(f"Revert EVERYTHING (reverse order): py {unified}")
    return 0, str(unified)


_JOURNEY_MARKER = ".ff9journey"     # written into a single-folder deploy so a re-deploy knows the folder is its own


def _journey_signature(manifest) -> str:
    """A stable id for a manifest's journey set, written into a single-folder deploy as ``.ff9journey``. A later
    re-deploy of the SAME journey reads it back to recognize its OWN folder -- even when a re-fork changed campaign
    ids (so the old ids would otherwise read as a 'foreign mod' to the wholesale-replace guard)."""
    ids = sorted(j.id for j in getattr(manifest, "journeys", []) or [])
    return ",".join(ids) if ids else "(bare)"


def _folder_is_ours(live_root, manifest) -> bool:
    """True if ``live_root`` carries a ``.ff9journey`` marker matching this manifest -- i.e. it's THIS journey's
    prior single-folder deploy (safe to wholesale-replace), not an unrelated mod that happens to share the name."""
    marker = Path(live_root) / _JOURNEY_MARKER
    try:
        return marker.is_file() and marker.read_text(encoding="utf-8").strip() == _journey_signature(manifest)
    except OSError:
        return False


def _apply_journey_single(manifest, plan, *, game, newgame, single_folder, allow_collision, hub_out,
                          backups_dir, reverts_dir, out, err):
    """ONE-SHOT single-folder deploy: build every campaign + the hub offline, MERGE them into ONE mod folder,
    install it (snapshot + wholesale-replace), apply the links IN that folder, optionally wire New Game. Returns
    ``(rc, unified_revert_path_or_None)``."""
    import tempfile

    from . import build as B
    from . import campaign as C
    from . import deploystack as DS
    from . import journey as J
    from . import newgame as _ng
    if game is None:
        err("no FF9 install found -- can't deploy.")
        return 2, None
    if plan.hub_field_id is None:
        err("ABORT: the manifest has no [hub] id to deploy New Game into.")
        return 2, None
    folder = _single_folder_name(manifest, single_folder)
    stamp = _stamp()
    live_root = Path(game) / folder
    captured: list = []
    reverts_dir = Path(reverts_dir)
    reverts_dir.mkdir(parents=True, exist_ok=True)
    unified = reverts_dir / "revert_journey.py"

    def _flush():
        unified.write_text(_render_unified_revert(captured, stamp), encoding="utf-8", newline="\n")

    def _abort(msg):
        _flush()
        err(f"\nABORT mid-deploy: {msg}")
        err(f"Partial state is reversible: py {unified}")
        return 2, str(unified)

    # (0) PRE-FLIGHT: build every campaign + the hub to its own dist, all OFFLINE.
    out("\n=== 0. pre-flight: build every campaign + the hub offline (no game files touched) ===")
    hub_toml = Path(hub_out) if hub_out else (manifest.path.parent / "hub.field.toml")
    built: dict = {}
    for s in plan.campaign_steps:
        dist = s.campaign_path.parent / "dist"
        out(f"  building {s.folder} (flag_base {s.flag_base}) -> {dist}")
        try:
            C.build_campaign(s.campaign_path, out=dist, flag_base=s.flag_base, seed_blocks=s.seed_blocks,
                             text_block_base=s.text_block_base, extra_flag_names=J.manifest_flag_names(manifest))
        except Exception as e:                            # noqa: BLE001
            err(f"\nABORT (no game files touched): campaign {s.folder} does not build -- {e}")
            return 2, None
        built[s.folder] = dist
    tmp = Path(tempfile.mkdtemp(prefix="ff9-journey-merge-"))
    hub_dist = tmp / "hub_dist"
    try:
        J.generate_hub(manifest.path, out_path=hub_toml, extract_camera=True, game=game)
        B.build_mod([B.FieldProject.load(hub_toml)], hub_dist, mod_name="hub")
    except Exception as e:                                # noqa: BLE001
        err(f"\nABORT (no game files touched): the hub does not build -- {e}")
        return 2, None
    out(f"  all {len(built)} campaign(s) + the hub build OK")

    # (1) MERGE every dist (+ the hub) into one merged dist (entry campaign LAST so its start-state wins).
    entry_step = next((s for s in plan.campaign_steps if s.seed_blocks), None) or (
        plan.campaign_steps[0] if plan.campaign_steps else None)
    entry_dist = built.get(entry_step.folder) if entry_step else None
    all_dists = [hub_dist] + [built[s.folder] for s in plan.campaign_steps]
    merged = tmp / "merged"
    info = J.merge_dists(all_dists, out=merged, folder_name=folder, entry_dist=entry_dist)
    (merged / _JOURNEY_MARKER).write_text(_journey_signature(manifest), encoding="utf-8")   # so a re-deploy knows it's ours
    out(f"\n=== 1. merge -> one folder '{folder}' ({info['fields']} fields, {info['dists_merged']} dist(s)) ===")

    # (1.5) collision guards vs the FOREIGN FolderNames stack (the merged folder's own ids/names are fine).
    order = folder_order(game)
    nwarn = DS.name_collision_warning(
        DS.check_name_collisions(game, folder, DS.eb_names_at(merged), DS.scene_names_at(merged),
                                 folder_names=order), folder)
    iwarn = DS.id_collision_warning(
        DS.check_id_collisions(game, folder, DS.dictionary_ids_at(merged).keys(), folder_names=order), folder)
    for w in (nwarn, iwarn):
        if w:
            out("\n  !! " + w)
    if (nwarn or iwarn) and not allow_collision:
        err("\nABORT before install (no game files touched): the merged journey collides with another "
            "FolderNames folder. Drop the foreign folder from FolderNames, or pass allow_collision=True.")
        return 2, None

    # (1.6) wholesale-replace TARGET guard: a DIFFERENT mod already under that folder name. A folder THIS journey
    # deployed before carries our `.ff9journey` marker -> it is OURS (a re-fork may have changed campaign ids, so the
    # foreign-id heuristic alone would false-abort) -> overwrite freely; the snapshot below keeps it revertable.
    if live_root.is_dir():
        ours = _folder_is_ours(live_root, manifest)
        foreign_ids = set(DS.dictionary_ids_at(live_root).keys()) - set(DS.dictionary_ids_at(merged).keys())
        if foreign_ids and ours:
            shown = sorted(foreign_ids)
            out(f"  note: '{folder}' is this journey's prior deploy ({_JOURNEY_MARKER} matches); its now-stale id(s) "
                f"{shown[:8]}{'...' if len(shown) > 8 else ''} (e.g. a re-forked campaign) will be replaced.")
        elif foreign_ids and not allow_collision:
            shown = sorted(foreign_ids)
            err(f"\nABORT (no game files touched): folder '{folder}' already holds an UNRELATED mod (no "
                f"'{_JOURNEY_MARKER}' marker for this journey) -- it registers field ids "
                f"{shown[:8]}{'...' if len(shown) > 8 else ''} this journey doesn't. Pick a different single_folder "
                f"NAME, remove that folder, or pass allow_collision=True to overwrite it.")
            return 2, None

    # (2) install: snapshot, script the snapshot-restore revert FIRST, then wholesale-replace.
    live_root.mkdir(parents=True, exist_ok=True)
    snap = Path(backups_dir) / f"{folder}.pre-journey.{stamp}"
    snap.parent.mkdir(parents=True, exist_ok=True)
    if snap.exists():
        shutil.rmtree(snap, ignore_errors=True)
    shutil.copytree(live_root, snap)
    rev = reverts_dir / "revert_journey_single_folder.py"
    rev.write_text(_render_folder_revert(live_root, snap, stamp), encoding="utf-8", newline="\n")
    captured.append(str(rev))
    _flush()
    _lost = _foreign_regs_wiped(ModLayout(live_root), merged)   # model-anim-new-between-deploys footgun (snapshot reverts it)
    if _lost:
        out("  !! WARNING: this wholesale install DROPS DictionaryPatch registration(s) not in the merged dist "
            "(e.g. `model-anim-new` clips added to this folder since the last deploy). RE-ADD them after. Lost:")
        for _l in _lost:
            out(f"       {_l}")
    try:
        shutil.rmtree(live_root, ignore_errors=True)
        shutil.copytree(merged, live_root)
    except OSError as e:
        return _abort(f"install copy failed mid-write ({e}) -- run the revert to restore the snapshot")
    out(f"=== 2. installed merged dist -> {live_root}  (snapshot {snap.name}) ===")

    # (3) cross-campaign links -- all .eb live in the ONE merged folder now.
    out("\n=== 3. links ===")
    link_rev, links_ok = _run_links(plan, game, stamp, backups_dir=backups_dir, reverts_dir=reverts_dir,
                                    mod_folder_override=folder, out=out)
    if link_rev:
        captured.append(link_rev)
        _flush()
    if not links_ok:
        return _abort("a cross-campaign link did not apply (see !! above)")

    # (4) OPTIONAL New Game -> the merged folder (single-owner).
    if newgame in ("hub", "entry"):
        if newgame == "entry" and plan.entry_field_id is None:
            return _abort("newgame='entry' needs a SINGLE-journey manifest (use newgame='hub').")
        target = plan.hub_field_id if newgame == "hub" else plan.entry_field_id
        what = "the hub menu" if newgame == "hub" else "the opening, no menu"
        out(f"\n=== 4. New Game -> {what} (field {target}, folder {folder}) ===")
        res = _ng.wire_from_stock(game, target, mod_folder=folder, backups_dir=backups_dir,
                                  reverts_dir=reverts_dir, verbose=(out is print))
        if not res["ok"]:
            return _abort("New-Game wiring (wire_from_stock) failed")
        cap = _capture_path(res["revert"], reverts_dir, "revert_journey_newgame.py")
        if cap:
            captured.append(cap)
        _flush()
    else:
        out("\n=== 4. New Game: SKIPPED (newgame='hub'|'entry' to opt in) ===")

    out("\n=== MANUAL STEPS (this tool cannot do these) ===")
    out("1. Memoria.ini [Mod] FolderNames -- this whole journey is now ONE folder. Put it HIGHEST:")
    out(f'   FolderNames = "{folder}", "<your other mods, e.g. Moguri>"')
    if plan.campaign_steps:
        lo = min(s.id_lo for s in plan.campaign_steps)
        hi = max(s.id_hi for s in plan.campaign_steps)
        out(f"   This journey uses field ids {lo}..{hi} -- REMOVE any OTHER custom-field folder in that range "
            f"(incl. this journey's OLD per-campaign folders, now superseded).")
    out("2. RELAUNCH once -- the new ids only register on a fresh launch.")
    if newgame in ("hub", "entry"):
        tgt = plan.hub_field_id if newgame == "hub" else plan.entry_field_id
        out(f"3. New Game lands on field {tgt}; PLAYTEST.")
    else:
        out(f"3. Reach the hub via F6 -> Warp {plan.hub_field_id} (New Game UNCHANGED). PLAYTEST.")
    out(f"Revert EVERYTHING (reverse order): py {unified}")
    return 0, str(unified)


def deploy_journey(journeys, *, game=None, apply=False, newgame="none", apply_links=False, single_folder=None,
                   allow_collision=False, hub_out=None, backups_dir, reverts_dir, verbose=True) -> dict:
    """Deploy (or dry-run) a multi-campaign journey manifest. SAFE BY DEFAULT: with ``apply=False`` it lints +
    prints the resolved namespace + the ordered deploy playbook and touches nothing. ``apply=True`` runs the
    whole playbook in one shot (each campaign -> links -> hub -> optional New Game) with ONE unified revert;
    ``single_folder`` (a name or ``""``) merges the journey into ONE folder; ``apply_links`` re-applies only the
    cross-campaign link rewrites. Returns ``{ok, rc, revert}``."""
    from . import journey as J
    out, err = _emit(verbose)
    report: dict = {"ok": False, "rc": 2, "revert": None}
    jpath = Path(journeys)
    try:
        manifest = J.load_journeys(jpath)
        errors, warnings = J.lint_manifest(manifest)
    except (J.JourneyError, FileNotFoundError, ValueError) as e:
        err(str(e))
        return report
    for w in warnings:
        out("  warn:", w)
    if errors:
        err("journey lint FAILED:")
        for e in errors:
            err("  error:", e)
        return report

    plan = J.build_deploy_plan(manifest)
    out(J.render_journey_plan(manifest))
    game = game if game is not None else _game_or_none()

    if apply:
        if single_folder is not None:
            rc, rev = _apply_journey_single(manifest, plan, game=game, newgame=newgame, single_folder=single_folder,
                                            allow_collision=allow_collision, hub_out=hub_out,
                                            backups_dir=backups_dir, reverts_dir=reverts_dir, out=out, err=err)
        else:
            rc, rev = _apply_journey(manifest, plan, game=game, newgame=newgame, hub_out=hub_out,
                                     backups_dir=backups_dir, reverts_dir=reverts_dir, out=out, err=err)
        report.update(ok=(rc == 0), rc=rc, revert=rev)
        return report

    if apply_links:
        if game is None:
            err("no FF9 install found -- can't apply link rewrites.")
            return report
        stamp = _stamp()
        rev, _ok = _run_links(plan, game, stamp, backups_dir=backups_dir, reverts_dir=reverts_dir, out=out)
        if rev:
            out(f"link rewrites applied. RELAUNCH + PLAYTEST.  revert: py {rev}")
        report.update(ok=True, rc=0, revert=rev)
        return report

    # --- dry-run: the playbook ---
    hub_o = hub_out or str((jpath.parent / "hub.field.toml"))
    out(J.render_deploy_playbook(manifest, hub_toml=hub_o, journeys_ref=str(jpath)))
    if single_folder is not None:
        folder = _single_folder_name(manifest, single_folder)
        out(f"\n*** single_folder: with apply=True, the whole journey MERGES into ONE folder '{folder}' "
            f"(one FolderNames entry) instead of the per-campaign folders above. ***")
    if game is not None:
        hub_name = manifest.hub.get("name") if manifest.hub else None
        rep = J.render_collision_report(J.preflight_collisions(plan, game, hub_name=hub_name))
        if rep:
            out("\n" + rep)
            out("(FBG scene-name collisions are only verified at apply, after the offline build.)")
    out("DRY-RUN -- no game files touched. Re-run with apply=True for the one-shot install (one unified revert).")
    report.update(ok=True, rc=0)
    return report
