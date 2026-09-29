"""New-Game entry wiring -- point FF9's stock New Game at a custom field id, PURE MOD (no DLL).

FF9's New Game is stock (``fldMapNo = 70``, ``EVT_ALEX1_TS_OPENING`` -- the theater-ship opening: BGM +
intro FMV + fade-to-black, ending in ``Field(50)`` to Prima Vista). A mod shadows field 70's ``.eb`` so its
terminal ``Field()`` lands on a custom entry instead -- the opening FMV + fade are PRESERVED, then New Game
warps into the fork. Field 70's bytecode is language-identical (the per-lang files differ only in the cosmetic
84-byte name the engine ignores), so the one remapped script is written to all 7 lang paths.

THE HANDOFF. Right before its ``Field(50)`` stock 70 marks ``Byte[13] := 2``, starts its own ambient 643 and
sets the keep-playing flag ``Map.Bit[162]``: a same-id handoff, because field 50 owns 643 too. Stock hands a
playing ambient only to a field that owns the same id (1040 of 1059 keep-flag warps, by a linear scan of the
US scripts). Pointed anywhere else, that handoff leaves 643 playing in the target and the target's prologue
turns the 2 into the error mark 9. So the override follows stock's exit rule, decided by the TARGET's own
script (:func:`target_ambient`, :func:`set_handoff`):

* the target owns 643 (its Main_Init prologue sets ``Int16[9] := 643`` -- a fork of 50, like the faithful
  opening's entry 6000) -> stock's handoff; only the ``Field()`` literal changes;
* anything else (a hub, a synthesized field, another donor's fork, a target whose script cannot be read) ->
  70's own exit stop (:func:`content.ambient.exit_stop`, byte for byte 70's disc-change branch, Main_Init
  rel 812-839) is INSERTED right before ``Int16[2] := 0; Field(target)``, where every stock exit seats it.
  643 stops, and the target arrives with ``Byte[13] = 3``, which every prologue turns into 0.

Two operations, both through :func:`content.verbatim.remap_fields` for the literal:

* :func:`wire_from_stock` -- CREATE the override from STOCK field 70 (robust: works when NO override exists,
  e.g. a clean install or right after a wholesale campaign deploy wiped ``FF9CustomMap``).
* :func:`retarget` -- RE-POINT an override that already exists: swap its ``Field()`` literal and set the
  handoff for the new target -- insert the stop, or remove it (``eb.edit.remove_in_function``) when the new
  target owns 643. An override not in stock 70's warp shape is refused, never half-wired.

Both back up the whole file and their reverts restore the whole file, so undoing the insertion needs nothing
new. This is the package home of the logic the repo ``tools/wire_newgame_from_stock.py`` /
``tools/retarget_newgame_warp.py`` drive (now thin shims) and the installed ``ff9mapkit`` CLI calls. The
caller supplies the backup + revert directories, so the dev loop writes into ``backups/`` + ``tools/scroll_out/``
while an installed copy writes into a per-user cache. Mechanism: memory ``project-ff9-new-game-entry``.
"""
from __future__ import annotations

import datetime
import shutil
from pathlib import Path

from . import extract
from .config import ModLayout
from .content import ambient as _ambient
from .content.verbatim import FIELD_OP, remap_fields
from .eb import EbScript
from .eb import edit as _edit

LANGS = ["us", "uk", "fr", "gr", "it", "es", "jp"]
NEWGAME_FIELD = 70   # stock New Game -> fldMapNo 70 (EVT_ALEX1_TS_OPENING)
DEFAULT_NAME = "evt_alex1_ts_opening"   # the field-70 opening override base name
OVERRIDE_REL = ("StreamingAssets/assets/resources/commonasset/eventengine/"
                "eventbinary/field/{lang}/evt_alex1_ts_opening.eb.bytes")
_ENTRANCE = bytes([0x05, 0xD8, 0x02, 0x7D])   # ``Int16[2] := <u16>`` ... ``2c 7f`` -- set just before Field()


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


def _main_init(data: bytes):
    s = EbScript.from_bytes(data)
    f = s.entry(0).func_by_tag(0)
    if f is None:
        raise ValueError("no Main_Init (entry 0, function tag 0)")
    return f, list(s.instrs(f))


def _entrance_rel(data: bytes) -> int:
    """Main_Init-relative offset of the ``Int16[2] := N`` statement immediately before the New-Game ``Field()``
    -- the seat of every stock exit's stop. Raises ValueError when the warp is not in stock 70's shape."""
    f, instrs = _main_init(data)
    k = next((k for k, i in enumerate(instrs) if i.op == FIELD_OP), None)
    if k:
        prev = data[instrs[k - 1].off:instrs[k - 1].end]
        if len(prev) == 8 and prev[:4] == _ENTRANCE and prev[6:] == b"\x2c\x7f":
            return instrs[k - 1].off - f.abs_start
    raise ValueError("its New-Game Field() is not preceded by `Int16[2] := N` -- not stock field 70's warp shape")


def _own_stop(data: bytes) -> bytes:
    """The override's exit stop for its OWN ambient (70's 643); ValueError when it owns none."""
    k = _ambient.ambient_id(data)
    if k is None or k == _ambient.NO_AMBIENT:
        raise ValueError("it owns no slot-0 ambient to stop -- not stock field 70's opening")
    return _ambient.exit_stop(k)


def handoff(data) -> str:
    """``"stop"`` when the override stops its own ambient right before its warp (the exit stop seated
    immediately before ``Int16[2] := N; Field(N)``), else ``"keep"`` -- stock's same-id handoff."""
    b = bytes(data)
    stop, rel = _own_stop(b), _entrance_rel(b)
    f, instrs = _main_init(b)
    seat = f.abs_start + rel - len(stop)
    on_boundary = any(i.off == seat for i in instrs)
    return "stop" if on_boundary and b[seat:seat + len(stop)] == stop else "keep"


def set_handoff(data, stop: bool) -> bytes:
    """Return the override with its handoff set: ``stop=True`` inserts the exit stop right before
    ``Int16[2] := N; Field(N)``; ``stop=False`` removes it (stock's keep-playing handoff). Unchanged when it is
    already so. Raises ValueError when the override is not in stock 70's shape (template drift must fail
    loudly, never leave the handoff half-set)."""
    b = bytes(data)
    have = handoff(b) == "stop"
    rel, blk = _entrance_rel(b), _own_stop(b)
    if stop and not have:
        return _edit.insert_in_function(b, 0, 0, rel, blk)
    if have and not stop:
        return _edit.remove_in_function(b, 0, 0, rel - len(blk), len(blk))
    return b


def target_script(game, target: int, *, mod_folder: str | None = None, lang: str = "us") -> bytes | None:
    """The ``.eb`` the game runs for field ``target``, or None when it cannot be read. The id's name comes from
    the first ``Memoria.ini`` FolderNames folder (then ``mod_folder``, when it is not listed yet) whose
    DictionaryPatch registers it -- the file is ``EVT_<NAME>.eb.bytes``, served by the first folder that ships
    it. A stock id no folder registers runs a folder's override of its stock script, else the install's own."""
    from .deploystack import dictionary_ids_at, parse_folder_names
    game = Path(game)
    ini = game / "Memoria.ini"
    try:
        order = parse_folder_names(ini.read_text(encoding="utf-8", errors="ignore")) if ini.is_file() else []
    except OSError:
        order = []
    if mod_folder and mod_folder not in order:
        order = order + [mod_folder]
    roots = [game / f for f in order if (game / f).is_dir()]
    name = next((reg[target][1] for reg in map(dictionary_ids_at, roots)
                 if reg.get(target, ("", ""))[0] == "FieldScene"), None)
    evt = f"EVT_{name}" if name else extract.ID_TO_EVT.get(int(target))
    if evt is None:
        return None
    for root in roots:
        for L in [lang] + [x for x in LANGS if x != lang]:
            p = ModLayout(root).eb_path(L, f"{evt}.eb.bytes")
            if p.is_file():
                return p.read_bytes()
    if name is not None:
        return None                                   # registered, but its script is nowhere to be read
    try:
        return extract.EventBundle(game=str(game)).eb_for_id(int(target)) or None
    except Exception:                                 # noqa: BLE001 -- no bundle/UnityPy: simply unknown
        return None


def target_ambient(game, target: int, *, mod_folder: str | None = None) -> int | None:
    """The slot-0 ambient id field ``target``'s own prologue sets (65535 = none), or None when its script
    cannot be read or carries no prologue."""
    data = target_script(game, target, mod_folder=mod_folder)
    if data is None:
        return None
    try:
        return _ambient.ambient_id(data)
    except ValueError:
        return None


def _handoff_note(stop: bool, own: int, tk: int | None, target: int) -> str:
    if not stop:
        return f"handoff: keep {own} playing -- field {target} owns {own} (stock's same-id handoff)"
    why = ("its script could not be read" if tk is None else
           "it owns no ambient" if tk == _ambient.NO_AMBIENT else f"it owns {tk}, not {own}")
    return f"handoff: stop {own} before Field({target}) -- {why} (stock's exit stop)"


def _stamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


def _emit_revert(reverts_dir, name: str, body_lines: list[str]) -> Path:
    """Write a standalone revert script (pure os/shutil -- runnable via ``python <path>``) and return it."""
    reverts_dir = Path(reverts_dir)
    reverts_dir.mkdir(parents=True, exist_ok=True)
    p = reverts_dir / name
    p.write_text("\n".join(body_lines), encoding="utf-8")
    return p


def build_override(stock: bytes, target: int, tk: int | None) -> bytes:
    """Stock field 70's script pointed at ``target``, given the target's own ambient ``tk`` (None: unknown):
    the ``Field()`` literal swapped, and 70's exit stop inserted unless the target owns 70's ambient. Stock
    verbatim when ``target`` IS stock's destination. Raises ValueError when ``stock`` is not 70's shape."""
    stock_dest = newgame_target(stock)
    if stock_dest is None:
        raise ValueError(f"stock field {NEWGAME_FIELD} has no Field() warp in Main_Init")
    if stock_dest == target:
        return stock
    out = remap_fields(stock, {stock_dest: target})
    if out == stock:
        raise ValueError(f"Field({stock_dest}) not found to patch")
    return set_handoff(out, stop=tk != _ambient.ambient_id(stock))


def wire_from_stock(game, target: int, *, mod_folder: str = "FF9CustomMap", backups_dir, reverts_dir,
                    dry_run: bool = False, verbose: bool = True) -> dict:
    """Create the field-70 New-Game override FROM STOCK and point it at ``target`` (all 7 langs).

    Extracts stock field 70 from p0data, repoints its ``Field(<stock-dest>)`` -> ``Field(target)``, sets the
    handoff for the target (see the module docstring), and writes the override into ``<game>/<mod_folder>/...``
    for every language. Backs up any prior copy to ``backups_dir`` and writes ``revert_newgame_from_stock.py``
    into ``reverts_dir``. Returns a report dict ``{ok, target, stock_dest, new_dest, handoff, target_ambient,
    files, revert, dry_run}``. The target MUST be a registered field (deploy the chain first) or New Game warps
    to an unregistered id = black screen."""
    game = Path(game)
    out_report: dict = {"ok": False, "target": target, "stock_dest": None, "new_dest": None, "handoff": None,
                        "target_ambient": None, "files": [], "revert": None, "dry_run": dry_run}

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
    tk = target_ambient(game, target, mod_folder=mod_folder)
    out_report["target_ambient"] = tk
    try:
        out = build_override(data, target, tk)
    except ValueError as e:
        if verbose:
            print(f"cannot wire from stock field {NEWGAME_FIELD}: {e}")
        return out_report
    if verbose and stock_dest == target:
        print(f"stock field {NEWGAME_FIELD} already warps Field({target}); writing it verbatim as the override")

    new_dest = newgame_target(out)
    out_report["new_dest"] = new_dest
    out_report["handoff"] = handoff(out)
    if verbose:
        print(f"field {NEWGAME_FIELD} override: Field({stock_dest}) -> Field({new_dest})   "
              f"(New Game -> field {NEWGAME_FIELD} opening [FMV+fade preserved] -> Field({target}))")
        print("  " + _handoff_note(out_report["handoff"] == "stop", _ambient.ambient_id(data), tk, target))
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


def _retarget_one(path: Path, target: int, frm: int | None, tk: int | None, *, backups_dir, dry_run: bool,
                  verbose: bool) -> tuple[int, bool, tuple[str, str] | None]:
    """Retarget one override copy to ``target`` (whose own ambient is ``tk``). Returns
    ``(n_changed 0|1, wired: it now warps the target with the right handoff, (live, backup) | None)``."""
    data = path.read_bytes()
    old = frm if frm is not None else newgame_target(data)
    if old is None:
        if verbose:
            print(f"  {path.name}: no Field() warp in Main_Init -- not an opening override; skipped  [{path}]")
        return 0, False, None
    out = data if old == target else remap_fields(data, {old: target})
    if out == data and old != target:
        if verbose:
            print(f"  {path.name}: Field({old}) not found to patch (unexpected); skipped")
        return 0, False, None
    try:
        stop = tk != _ambient.ambient_id(data)
        out = set_handoff(out, stop=stop)
    except ValueError as e:
        if verbose:
            print(f"  {path.name}: cannot set the ambient handoff -- {e}; skipped (rewire it from stock: "
                  f"tools/wire_newgame_from_stock.py {target})  [{path}]")
        return 0, False, None
    note = _handoff_note(stop, _ambient.ambient_id(data), tk, target)
    warp = f"Field({old}) -> Field({target})" if old != target else f"Field({target}) kept"
    if out == data:
        if verbose:
            print(f"  {path.name}: already warps Field({target}), {note.split(' -- ')[0]} -- nothing to do")
        return 0, True, None
    if dry_run:
        if verbose:
            print(f"  {path.name}: WOULD rewire: {warp}; {note}  [{path}]")
        return 1, True, None
    backups_dir = Path(backups_dir)
    backups_dir.mkdir(parents=True, exist_ok=True)
    backup = backups_dir / f"{path.parent.name}-{path.name}.preRETARGET.{_stamp()}"   # lang dir avoids collisions
    shutil.copyfile(path, backup)
    path.write_bytes(out)
    if verbose:
        print(f"  {path.name}: {warp}; {note}  (backup: {backup.name})")
    return 1, True, (str(path), str(backup))


def retarget(game, target: int, *, frm: int | None = None, name: str = DEFAULT_NAME, backups_dir, reverts_dir,
             dry_run: bool = False, verbose: bool = True) -> dict:
    """Retarget the field-70 override's ``Field()`` warp to ``target`` across every live override copy, and set
    each copy's ambient handoff for that target (the module docstring's rule).

    Returns ``{ok, target, changed, confirmed, found, target_ambient, files, revert, dry_run}``. ``ok`` is False
    when override files are present but NONE end up warping the target with the right handoff (a corrupt,
    non-opening or hand-reshaped override -> New Game NOT wired), so a caller can abort instead of falsely
    reporting success."""
    out_report: dict = {"ok": False, "target": target, "changed": 0, "confirmed": 0, "found": 0,
                        "target_ambient": None, "files": [], "revert": None, "dry_run": dry_run}
    targets = live_overrides(game, name)
    out_report["found"] = len(targets)
    if not targets:
        if verbose:
            print(f"no live override found: ensure a mod folder contains {name}.eb.bytes "
                  f"(Memoria.ini FolderNames). Nothing to do.")
        return out_report
    tk = target_ambient(game, target)
    out_report["target_ambient"] = tk
    if verbose:
        print(f"{'[dry-run] ' if dry_run else ''}retargeting New Game -> Field({target}) "
              f"in {len(targets)} override file(s):")
    stamp = _stamp()
    changed = confirmed = 0
    backups: list[tuple[str, str]] = []
    for p in targets:
        n, wired, pair = _retarget_one(p, target, frm, tk, backups_dir=backups_dir, dry_run=dry_run,
                                       verbose=verbose)
        changed += n
        confirmed += wired
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
    # override file(s) present but NONE wired to the target -> New Game NOT wired; fail so a caller aborts.
    if not dry_run and confirmed == 0:
        if verbose:
            print(f"ERROR: {len(targets)} override file(s) present but NONE warps Field({target}) with its "
                  f"ambient handoff set -- none was stock field 70's warp shape (a corrupt or non-opening "
                  f"{name}.eb?). New Game NOT wired.")
        return out_report
    out_report["ok"] = True
    return out_report
