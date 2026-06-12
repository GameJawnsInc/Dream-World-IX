"""Read a save's ITEMS / EQUIPMENT / GIL -- the #5 editor's READ surface (read-only).

Reads the Memoria EXTRA file (``SavedData_ww_Memoria_{slot}_{save}.dat``) via the :mod:`sjbinary` codec and
decodes ``40000_Common/{gil, items, players[].equip}`` into kit item names (:mod:`ff9mapkit.items`). The extra
file is the **load-authoritative** store -- it overrides the encrypted main block on load (memory
project-ff9-save-item-layout), so reading it shows what the game actually loads.

SEPARATE surface per [[project-ff9-branch-lanes]] rule 3: reuses :class:`save.FF9Save` + :mod:`sjbinary`; it
does NOT touch :func:`save.apply_story_edit` / ``edit_story_state`` (story_flags' gEventGlobal core). The WRITE
half (dual-write extra + main, backup-guarded) lands in a later step; this is read-only.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

from . import items as _items
from . import save as _save
from . import sjbinary as _sj

NO_ITEM = 255                                              # the empty-slot / list-terminator sentinel
EQUIP_SLOTS = ("weapon", "head", "wrist", "armor", "accessory")   # equip[] order (CharacterEquipment.cs)
COMMON = "40000_Common"
GIL_CAP = 9_999_999                                        # the in-game gil display cap (project-ff9-save-item-layout)


@dataclass
class ItemReport:
    """What a save slot's items/equipment/gil decode to (from the Memoria extra file)."""
    gil: int | None = None
    inventory: list = field(default_factory=list)         # [(id, name, count), ...]
    equipment: list = field(default_factory=list)         # [{"slot_no", "name", "equip": {slot: (id, name)|None}}]


@dataclass
class GilWriteReport:
    """The outcome of a :func:`set_gil` call (dry-run or applied)."""
    path: str
    old_gil: int
    new_gil: int
    bytes_changed: int                                    # how many on-disk bytes the gil edit moves (<=4)
    wrote: bool                                           # False = dry-run (nothing written)
    backup_path: "str | None" = None


# --- low-level reads off a parsed 40000_Common SJClass --------------------------------------------

def read_gil(common) -> int | None:
    n = _sj.get_path(common, "gil")
    return int(n.value) if n is not None else None


def read_inventory(common) -> list:
    """``40000_Common/items`` -> ``[(id, name, count), ...]`` (extra-file compacted list; names via the kit
    item table). NoItem (255) entries are skipped."""
    arr = _sj.get_path(common, "items")
    out = []
    if arr is None:
        return out
    for entry in arr:
        iid, cnt = _sj.get_path(entry, "id"), _sj.get_path(entry, "count")
        if iid is None or cnt is None:
            continue
        i = int(iid.value)
        if i == NO_ITEM:
            continue
        out.append((i, _items.name_of(i), int(cnt.value)))
    return out


def read_equipment(common) -> list:
    """``40000_Common/players[]`` -> ``[{slot_no, name, equip}, ...]``; ``equip`` maps each of the 5 slots
    (weapon/head/wrist/armor/accessory) to ``(id, name)`` or ``None`` (empty). The owner is the player's own
    ``name`` + ``info/slot_no`` (CharacterId), NOT the array index."""
    players = _sj.get_path(common, "players")
    out = []
    if players is None:
        return out
    for p in players:
        eq = _sj.get_path(p, "equip")
        if eq is None:
            continue
        sn, nm = _sj.get_path(p, "info", "slot_no"), _sj.get_path(p, "name")
        gear = {}
        for j, slot in enumerate(EQUIP_SLOTS):
            iid = int(eq.items[j].value) if j < len(eq.items) else NO_ITEM
            gear[slot] = None if iid == NO_ITEM else (iid, _items.name_of(iid))
        out.append({"slot_no": int(sn.value) if sn is not None else None,
                    "name": nm.value if nm is not None else None, "equip": gear})
    return out


def report_from_common(common) -> ItemReport:
    return ItemReport(gil=read_gil(common), inventory=read_inventory(common),
                      equipment=read_equipment(common))


# --- file-level helpers ---------------------------------------------------------------------------

def load_extra_common(extra_path):
    """Parse a Memoria extra file and return its ``40000_Common`` SJClass (+ the root + trailing for a future
    write), or ``(None, None, b"")`` if it's missing/unparseable/not an extra file."""
    try:
        raw = open(extra_path, "rb").read()
    except OSError:
        return None, None, b""
    try:
        root, trailing = _sj.loads(raw)
    except (ValueError, IndexError):
        return None, None, b""
    common = _sj.get_path(root, COMMON)
    return common, root, trailing


def inspect(path) -> list:
    """Decode a save's items/equipment/gil for VIEWING -- returns ``[(label, ItemReport), ...]``, one per
    populated slot, read from the Memoria EXTRA file (what the game loads). Accepts a Memoria extra file
    directly (plaintext, no crypto), OR the encrypted ``SavedData_ww.dat`` container (enumerates populated
    slots via :meth:`save.FF9Save.populated` -- needs pycryptodome -- and reads each slot's extra file). A
    populated slot with NO extra file is reported as ``None`` (the main-block decode is a later step). Raises
    with a clear message if nothing decodes."""
    p = str(path)
    # case 1: path IS a Memoria extra file (a plaintext SimpleJSON tree with 40000_Common)
    common, _, _ = load_extra_common(p)
    if common is not None:
        return [("Memoria extra-save", report_from_common(common))]
    # case 2: the encrypted container -> per populated slot, read its extra file
    sv = _save.FF9Save.load(p)
    out = []
    for s in sv.populated():
        extra = _save.extra_file_path(p, s.block)
        common = load_extra_common(extra)[0] if (extra and os.path.isfile(extra)) else None
        if common is not None:
            out.append((_save._slot_label(s) + " · Memoria extra", report_from_common(common)))
        else:
            out.append((_save._slot_label(s) + " · (no extra file -- main-block decode not yet supported)", None))
    if not out:
        raise ValueError("no populated save slots found in this file")
    return out


# --- write surface: gil (step 3 -- the first real-save WRITE, extra-only) -------------------------

def resolve_extra(save_path, *, slot=None, save=None, autosave=False):
    """Resolve the Memoria EXTRA-file path a write should target. If ``save_path`` is itself an extra file
    (a SimpleJSON tree with ``40000_Common``), return it. If it's a ``SavedData_ww.dat`` container, compute the
    extra path for ``--autosave`` or a 0-indexed ``(slot, save)`` -- 0-indexed to match the on-disk file name
    ``SavedData_ww_Memoria_{slot}_{save}.dat`` (the in-game menu shows these 1-indexed). Raises with a clear
    message if the target can't be identified or its extra file is absent."""
    p = str(save_path)
    if load_extra_common(p)[0] is not None:               # already a Memoria extra file
        return p
    if autosave and (slot is not None or save is not None):
        raise ValueError("pass --autosave OR --slot/--save-no, not both")
    if autosave:
        block = 0
    elif slot is not None and save is not None:
        block = _save.block_index(int(slot), int(save))
    else:
        raise ValueError("to edit a SavedData_ww.dat container, pass --slot and --save-no (0-indexed) or "
                         "--autosave; or pass a SavedData_ww_Memoria_*.dat extra file directly")
    extra = _save.extra_file_path(p, block)
    if extra is None:
        raise ValueError(f"{p!r} is not a .dat save container or a Memoria extra file")
    if not os.path.isfile(extra):
        raise ValueError(f"no Memoria extra file for that slot: {extra}")
    return extra


def set_gil(extra_path, gil: int, *, dry_run: bool = True, backup: bool = True) -> GilWriteReport:
    """Write ``40000_Common/gil`` in a Memoria EXTRA save file (the load-authoritative store -- memory
    project-ff9-save-item-layout), preserving every other byte. gil is a length-stable Int32 leaf (IntValue,
    tag 4), so this is the smallest possible real-save mutation: the #5 editor's FIRST write and the falsifiable
    proof of "the extra overrides the encrypted main block on load" -- write ONLY the extra, and if the in-game
    gil changes to match, the extra wins (the main block still holds the old value). The main-block mirror +
    items/equipment land in step 4; this never touches the main block or ``00001_time``.

    Safety (this writes a REAL save): re-serializes the WHOLE extra tree (siblings round-trip verbatim) but
    (gate 1) FIRST asserts the codec reproduces the on-disk bytes EXACTLY -- aborting rather than writing a file
    it can't reproduce (guards an unhandled tag / float culture-format) -- and (gate 2) asserts the new bytes
    differ from the old ONLY within the gil leaf's 4-byte value (length-stable, <=4 contiguous bytes). The write
    is ATOMIC (temp file + ``os.replace``, so the save is never half-written) and re-reads to CONFIRM the new
    gil; a timestamped ``<path>.bak.<ts>`` backup is taken first (``backup=True``, never clobbers a prior one,
    matching :func:`save.apply_story_edit`). ``dry_run`` by default (computes + verifies, writes nothing); a
    no-op (gil already == requested) writes nothing even on apply. Returns a :class:`GilWriteReport`."""
    if isinstance(gil, bool) or not isinstance(gil, int):
        raise TypeError(f"gil must be an int (got {type(gil).__name__})")
    if gil < 0 or gil > GIL_CAP:
        raise ValueError(f"gil must be in [0, {GIL_CAP:,}] (the in-game cap); got {gil:,}")
    try:
        raw = open(extra_path, "rb").read()
    except OSError as e:
        raise ValueError(f"cannot read extra save file {extra_path!r}: {e}") from e
    try:
        root, trailing = _sj.loads(raw)
    except (ValueError, IndexError) as e:
        raise ValueError(f"{extra_path!r} is not a parseable Memoria extra save file: {e}") from e
    # GATE 1: never edit a file we can't reproduce byte-for-byte (an unhandled leaf would corrupt it).
    if _sj.dumps(root, trailing) != raw:
        raise ValueError("refusing to edit: the SimpleJSON codec does not reproduce this file byte-for-byte "
                         "(editing could corrupt it). Please report this save.")
    common = _sj.get_path(root, COMMON)
    if common is None:
        raise ValueError(f"no {COMMON} module in {extra_path!r}")
    if not isinstance(common, _sj.SJClass):               # a parseable-but-non-Class 40000_Common -> refuse cleanly
        raise ValueError(f"{COMMON} is not a class node in {extra_path!r}; refusing to edit")
    gnode = common.get("gil")
    if not isinstance(gnode, _sj.SJData):
        raise ValueError(f"no {COMMON}/gil leaf in {extra_path!r}")
    if gnode.tag != _sj.INT:
        raise ValueError(f"{COMMON}/gil is not an Int32 leaf (tag {gnode.tag}); refusing to edit")
    old_gil = int(gnode.value)
    common.set("gil", _sj.SJData(_sj.INT, gil))           # preserve the on-disk tag (INT) -> length-stable
    new_bytes = _sj.dumps(root, trailing)
    # GATE 2: the edit must be surgical -- same length, only the gil value's bytes move (<=4, contiguous).
    if len(new_bytes) != len(raw):
        raise AssertionError(f"gil write changed the file length ({len(raw)} -> {len(new_bytes)}); aborting")
    diff = [i for i in range(len(raw)) if raw[i] != new_bytes[i]]
    if old_gil != gil and (len(diff) > 4 or (diff and diff[-1] - diff[0] >= 4)):
        raise AssertionError(f"gil write touched {len(diff)} non-contiguous bytes; aborting (expected <=4)")
    backup_path = None
    did_write = False
    if not dry_run and old_gil != gil:                    # a no-op (gil already == old) writes NOTHING
        if backup:                                        # timestamped, never clobbers a prior .bak (matches save.py)
            backup_path = f"{extra_path}.bak.{time.strftime('%Y%m%d-%H%M%S')}"
            with open(backup_path, "wb") as fh:
                fh.write(raw)                             # pristine original bytes
        tmp = f"{extra_path}.tmp"                          # ATOMIC: write a sibling temp, then swap in via os.replace
        with open(tmp, "wb") as fh:
            fh.write(new_bytes)
        os.replace(tmp, extra_path)                        # the real save is never observed half-written
        check = load_extra_common(extra_path)[0]           # CONFIRM the write took (mirrors apply_story_edit's re-read)
        cg = _sj.get_path(check, "gil") if check is not None else None
        if cg is None or int(cg.value) != gil:
            raise AssertionError(f"post-write check failed: gil did not read back as {gil:,}")
        did_write = True
    return GilWriteReport(path=str(extra_path), old_gil=old_gil, new_gil=gil,
                          bytes_changed=len(diff), wrote=did_write, backup_path=backup_path)


# --- rendering ------------------------------------------------------------------------------------

def render_report(rep: "ItemReport | None") -> str:
    """A human-readable items/equipment/gil report (the read surface's display; mirrors flags.render_report)."""
    if rep is None:
        return "  (no Memoria extra file for this slot)"
    lines = [f"  Gil: {rep.gil:,}" if rep.gil is not None else "  Gil: (none)"]
    lines.append(f"  Inventory ({len(rep.inventory)} stacks):")
    for iid, name, count in rep.inventory:
        lines.append(f"    {count:>3} x  {name or '?'}  (id {iid})")
    lines.append("  Equipment:")
    for pc in rep.equipment:
        worn = ", ".join(f"{slot}={pc['equip'][slot][1] or '?'}" for slot in EQUIP_SLOTS if pc["equip"].get(slot))
        lines.append(f"    {pc['name'] or '?':<10} {worn or '(nothing equipped)'}")
    return "\n".join(lines)


def render_gil_write(rep: GilWriteReport) -> str:
    """A human-readable summary of a :func:`set_gil` outcome (dry-run preview or applied write)."""
    if rep.old_gil == rep.new_gil:
        return f"  Gil already {rep.new_gil:,} in {rep.path} -- nothing to change."
    head = "WROTE" if rep.wrote else "DRY RUN -- would change"
    lines = [f"  {head} gil {rep.old_gil:,} -> {rep.new_gil:,} in {rep.path} ({rep.bytes_changed} bytes)"]
    if rep.wrote:
        if rep.backup_path:
            lines.append(f"  Backup: {rep.backup_path}")
        lines.append("  Load this save in-game and check the gil -- if it now reads the new value, the extra "
                     "file overrides the encrypted main block on load (the step-3 proof).")
    else:
        lines.append("  Re-run with --apply to write (a .bak backup is made first unless --no-backup).")
    return "\n".join(lines)
