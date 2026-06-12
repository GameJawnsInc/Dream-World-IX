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
from dataclasses import dataclass, field

from . import items as _items
from . import save as _save
from . import sjbinary as _sj

NO_ITEM = 255                                              # the empty-slot / list-terminator sentinel
EQUIP_SLOTS = ("weapon", "head", "wrist", "armor", "accessory")   # equip[] order (CharacterEquipment.cs)
COMMON = "40000_Common"


@dataclass
class ItemReport:
    """What a save slot's items/equipment/gil decode to (from the Memoria extra file)."""
    gil: int | None = None
    inventory: list = field(default_factory=list)         # [(id, name, count), ...]
    equipment: list = field(default_factory=list)         # [{"slot_no", "name", "equip": {slot: (id, name)|None}}]


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
