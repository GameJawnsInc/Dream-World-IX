"""New-Game entry wiring -- point FF9's stock New Game at a custom field id, PURE MOD (no DLL).

FF9's New Game is stock (``fldMapNo = 70``, ``EVT_ALEX1_TS_OPENING`` -- the theater-ship opening: BGM +
intro FMV + fade-to-black, ending in ``Field(50)`` to Prima Vista). A mod shadows field 70's ``.eb`` so its
terminal ``Field()`` lands on a custom entry instead -- the opening FMV + fade are PRESERVED, then New Game
warps into the fork. Field 70's bytecode is language-identical (the per-lang files differ only in the cosmetic
84-byte name the engine ignores), so the one remapped script is written to all 7 lang paths.

Two operations, both a 2-byte length-preserving ``Field()`` literal swap via the proven
:func:`content.verbatim.remap_fields`:

* :func:`wire_from_stock` -- CREATE the override from STOCK field 70 (robust: works when NO override exists,
  e.g. a clean install or right after a wholesale campaign deploy wiped ``FF9CustomMap``).
* :func:`retarget` -- RE-POINT an override that already exists (patch its live ``Field()`` literal).

This is the package home of the logic the repo ``tools/wire_newgame_from_stock.py`` /
``tools/retarget_newgame_warp.py`` drive (now thin shims) and the installed ``ff9mapkit`` CLI calls. The
caller supplies the backup + revert directories, so the dev loop writes into ``backups/`` + ``tools/scroll_out/``
while an installed copy writes into a per-user cache. Mechanism: memory ``project-ff9-new-game-entry``.
"""
from __future__ import annotations

import datetime
import shutil
from pathlib import Path

from . import extract
from .content.verbatim import FIELD_OP, remap_fields
from .eb import EbScript

LANGS = ["us", "uk", "fr", "gr", "it", "es", "jp"]
NEWGAME_FIELD = 70   # stock New Game -> fldMapNo 70 (EVT_ALEX1_TS_OPENING)
DEFAULT_NAME = "evt_alex1_ts_opening"   # the field-70 opening override base name
OVERRIDE_REL = ("StreamingAssets/assets/resources/commonasset/eventengine/"
                "eventbinary/field/{lang}/evt_alex1_ts_opening.eb.bytes")


def newgame_target(data: bytes) -> int | None:
    """The opening's New-Game destination: the first ``Field()`` warp in entry-0's Main_Init (tag 0)."""
    s = EbScript.from_bytes(data)
    f0 = s.entry(0).func_by_tag(0)
    if f0 is None:
        return None
    for ins in s.instrs(f0):
        if ins.op == FIELD_OP:
            return ins.imm(0)
    return None


def _stamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


def _emit_revert(reverts_dir, name: str, body_lines: list[str]) -> Path:
    """Write a standalone revert script (pure os/shutil -- runnable via ``python <path>``) and return it."""
    reverts_dir = Path(reverts_dir)
    reverts_dir.mkdir(parents=True, exist_ok=True)
    p = reverts_dir / name
    p.write_text("\n".join(body_lines), encoding="utf-8")
    return p


def wire_from_stock(game, target: int, *, mod_folder: str = "FF9CustomMap", backups_dir, reverts_dir,
                    dry_run: bool = False, verbose: bool = True) -> dict:
    """Create the field-70 New-Game override FROM STOCK and point it at ``target`` (all 7 langs).

    Extracts stock field 70 from p0data, repoints its ``Field(<stock-dest>)`` -> ``Field(target)``, and writes
    the override into ``<game>/<mod_folder>/...`` for every language. Backs up any prior copy to ``backups_dir``
    and writes ``revert_newgame_from_stock.py`` into ``reverts_dir``. Returns a report dict
    ``{ok, target, stock_dest, new_dest, files, revert, dry_run}``. The target MUST be a registered field
    (deploy the chain first) or New Game warps to an unregistered id = black screen."""
    game = Path(game)
    out_report: dict = {"ok": False, "target": target, "stock_dest": None, "new_dest": None,
                        "files": [], "revert": None, "dry_run": dry_run}

    data = extract.EventBundle(game=str(game)).eb_for_id(NEWGAME_FIELD)
    if not data:
        if verbose:
            print(f"could not extract stock field {NEWGAME_FIELD} .eb from p0data")
        return out_report
    stock_dest = newgame_target(data)
    out_report["stock_dest"] = stock_dest
    if stock_dest is None:
        if verbose:
            print(f"stock field {NEWGAME_FIELD} has no Field() warp in Main_Init -- cannot wire")
        return out_report
    if stock_dest == target:
        if verbose:
            print(f"stock field {NEWGAME_FIELD} already warps Field({target}); writing it verbatim as the override")
        out = data
    else:
        out = remap_fields(data, {stock_dest: target})
        if out == data:
            if verbose:
                print(f"Field({stock_dest}) not found to patch (unexpected)")
            return out_report

    new_dest = newgame_target(out)
    out_report["new_dest"] = new_dest
    if verbose:
        print(f"field {NEWGAME_FIELD} override: Field({stock_dest}) -> Field({new_dest})   "
              f"(New Game -> field {NEWGAME_FIELD} opening [FMV+fade preserved] -> Field({target}))")
    if new_dest != target:
        if verbose:
            print("  verification FAILED: override does not warp to the target")
        return out_report

    paths = [game / mod_folder / OVERRIDE_REL.format(lang=L) for L in LANGS]
    out_report["files"] = [str(p) for p in paths]
    if dry_run:
        if verbose:
            print(f"[dry-run] WOULD write the override to {len(paths)} lang path(s) under {mod_folder}:")
            for p in paths:
                print(f"    {p}")
        out_report["ok"] = True
        return out_report

    backups_dir = Path(backups_dir)
    backups_dir.mkdir(parents=True, exist_ok=True)
    stamp = _stamp()
    revert_pairs: list[tuple[str, str | None]] = []   # (live_path, backup_path_or_None=delete)
    for p in paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.is_file():
            bkp = backups_dir / f"{p.parent.name}-{p.name}.preWIRE.{stamp}"
            shutil.copyfile(p, bkp)
            revert_pairs.append((str(p), str(bkp)))
        else:
            revert_pairs.append((str(p), None))         # no prior -> revert deletes it
        p.write_bytes(out)
        if verbose:
            print(f"  wrote {p.parent.name}/{p.name}  ({len(out)} bytes)")

    rl = ['"""Revert the from-stock New-Game wiring: restore/delete the field-70 override copies."""',
          "import os, shutil", "PAIRS = ["]
    rl += [f"    ({live!r}, {bkp!r})," for live, bkp in revert_pairs]
    rl += ["]", "for live, bkp in PAIRS:",
           "    if bkp: shutil.copyfile(bkp, live); print('restored', live)",
           "    elif os.path.isfile(live): os.remove(live); print('removed', live)",
           f"print('reverted newgame-from-stock {stamp}')", ""]
    out_report["revert"] = _emit_revert(reverts_dir, "revert_newgame_from_stock.py", rl)
    out_report["ok"] = True
    if verbose:
        print(f"\nNew Game -> field {NEWGAME_FIELD} -> Field({target}).  RELAUNCH + New Game to test "
              f"(target {target} must be REGISTERED -- deploy the chain first).")
    return out_report


def live_overrides(game, name: str = DEFAULT_NAME) -> list[Path]:
    """Every per-language ``<name>.eb.bytes`` under the live ``FF9CustomMap*`` mod folders of ``game``."""
    game = Path(game)
    hits: list[Path] = []
    for mod in game.glob("FF9CustomMap*"):
        hits += list(mod.rglob(f"{name}.eb.bytes"))
    return sorted(set(hits))


def _retarget_one(path: Path, target: int, frm: int | None, *, backups_dir, dry_run: bool,
                  verbose: bool) -> tuple[int, int | None, tuple[str, str] | None]:
    """Retarget one override copy. Returns (n_changed 0|1, old id detected, (live, backup) | None)."""
    data = path.read_bytes()
    old = frm if frm is not None else newgame_target(data)
    if old is None:
        if verbose:
            print(f"  {path.name}: no Field() warp in Main_Init -- not an opening override; skipped  [{path}]")
        return 0, None, None
    if old == target:
        if verbose:
            print(f"  {path.name}: already warps Field({target}) -- nothing to do")
        return 0, old, None
    out = remap_fields(data, {old: target})
    if out == data:
        if verbose:
            print(f"  {path.name}: Field({old}) not found to patch (unexpected); skipped")
        return 0, old, None
    if dry_run:
        if verbose:
            print(f"  {path.name}: WOULD retarget Field({old}) -> Field({target})  [{path}]")
        return 1, old, None
    backups_dir = Path(backups_dir)
    backups_dir.mkdir(parents=True, exist_ok=True)
    backup = backups_dir / f"{path.parent.name}-{path.name}.preRETARGET.{_stamp()}"   # lang dir avoids collisions
    shutil.copyfile(path, backup)
    path.write_bytes(out)
    if verbose:
        print(f"  {path.name}: Field({old}) -> Field({target})  (backup: {backup.name})")
    return 1, old, (str(path), str(backup))


def retarget(game, target: int, *, frm: int | None = None, name: str = DEFAULT_NAME, backups_dir, reverts_dir,
             dry_run: bool = False, verbose: bool = True) -> dict:
    """Retarget the field-70 override's ``Field()`` warp to ``target`` across every live override copy.

    Returns ``{ok, target, changed, confirmed, found, files, revert, dry_run}``. ``ok`` is False when override
    files are present but NONE warp the target (a corrupt/non-opening override -> New Game NOT wired), so a
    caller can abort instead of falsely reporting success."""
    out_report: dict = {"ok": False, "target": target, "changed": 0, "confirmed": 0, "found": 0,
                        "files": [], "revert": None, "dry_run": dry_run}
    targets = live_overrides(game, name)
    out_report["found"] = len(targets)
    if not targets:
        if verbose:
            print(f"no live override found: ensure a mod folder contains {name}.eb.bytes "
                  f"(Memoria.ini FolderNames). Nothing to do.")
        return out_report
    if verbose:
        print(f"{'[dry-run] ' if dry_run else ''}retargeting New Game -> Field({target}) "
              f"in {len(targets)} override file(s):")
    stamp = _stamp()
    changed = confirmed = 0
    backups: list[tuple[str, str]] = []
    for p in targets:
        n, old, pair = _retarget_one(p, target, frm, backups_dir=backups_dir, dry_run=dry_run, verbose=verbose)
        changed += n
        if n or old == target:                       # patched now, OR it already warps the target -> wired
            confirmed += 1
        if pair:
            backups.append(pair)
    out_report["changed"], out_report["confirmed"] = changed, confirmed
    out_report["files"] = [live for live, _ in backups]
    if backups:
        rl = ['"""Revert the New-Game retarget: restore the field-70 override backups."""',
              "import shutil", "PAIRS = ["]
        rl += [f"    ({live!r}, {bkp!r})," for live, bkp in backups]
        rl += ["]", "for live, bkp in PAIRS:", "    shutil.copyfile(bkp, live); print('restored', live)",
               f"print('reverted newgame retarget {stamp}')", ""]
        out_report["revert"] = _emit_revert(reverts_dir, "revert_newgame_retarget.py", rl)
    if verbose:
        print(f"done -- {changed} override(s) {'would be ' if dry_run else ''}retargeted to Field({target}).")
    # override file(s) present but NONE warp the target -> New Game NOT wired; fail so a caller aborts.
    if not dry_run and confirmed == 0:
        if verbose:
            print(f"ERROR: {len(targets)} override file(s) present but NONE warp Field({target}) -- none had a "
                  f"patchable Field() op (a corrupt or non-opening {name}.eb?). New Game NOT wired.")
        return out_report
    out_report["ok"] = True
    return out_report
