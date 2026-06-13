"""Read AND edit a save's ITEMS / EQUIPMENT / GIL -- the #5 editor surface.

Reads + writes the Memoria EXTRA file (``SavedData_ww_Memoria_{slot}_{save}.dat``) via the :mod:`sjbinary`
codec, decoding/mutating ``40000_Common/{gil, items, players[].equip}`` by kit item name
(:mod:`ff9mapkit.items`). The extra file is the **load-authoritative** store -- it overrides the encrypted main
block on load (memory project-ff9-save-item-layout) -- so editing it changes what the game loads (proven
in-game). The READ surface: :func:`inspect` / :func:`report_from_common` (extra) + :func:`decode_main_block`
(the encrypted main block, for a no-extra save). The WRITE surface (all backup-guarded, ``dry_run`` by default,
with a validation gate + a scoped-change check + atomic write + post-write confirm): :func:`set_gil`/
:func:`set_item`/:func:`set_equip` on the extra; :func:`set_main_gil`/:func:`set_main_item` on the ENCRYPTED MAIN
block (so a **vanilla no-extra save is editable** -- gil + items); and :func:`set_gil_in_save`/
:func:`set_item_in_save`/:func:`set_equip_in_save`, which DUAL-WRITE the main block + the extra mirror (the extra
stays load-authoritative). So a vanilla no-extra save is now editable for gil, items AND equipment; only
key/important items remain deferred.

SEPARATE surface per [[project-ff9-branch-lanes]] rule 3: reuses :class:`save.FF9Save` + :mod:`sjbinary`; it
does NOT touch :func:`save.apply_story_edit` / ``edit_story_state`` (story_flags' gEventGlobal core).
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

from . import items as _items
from . import keyitems as _keyitems
from . import save as _save
from . import sjbinary as _sj

NO_ITEM = 255                                              # the empty-slot / list-terminator sentinel
EQUIP_SLOTS = ("weapon", "head", "wrist", "armor", "accessory")   # equip[] order (CharacterEquipment.cs)
_SLOT_ALIASES = {"body": "armor", "acc": "accessory"}      # friendly aliases for the slot names
COMMON = "40000_Common"
GIL_CAP = 9_999_999                                        # the in-game gil display cap (project-ff9-save-item-layout)
ITEM_COUNT_CAP = 99                                        # the in-game per-stack count cap

# The 4 growth stats (ff9level.cs): displayed = base + level*growth + (bonus>>5), capped per stat. `bonus` is the
# hidden EQUIPMENT accumulator; `basis` is the displayed value (recomputed from bonus only at level-up). Editing a
# save's `basis` (shows immediately) + `bonus` (holds it through level-ups) = a "set permanent stat" editor.
STAT_CAPS = {"dex": 50, "str": 99, "mgc": 99, "wpr": 50}   # Speed / Strength / Magic / Spirit
STAT_LABELS = {"dex": "Speed", "str": "Strength", "mgc": "Magic", "wpr": "Spirit"}
_STAT_ALIASES = {"speed": "dex", "spd": "dex", "dex": "dex", "strength": "str", "str": "str",
                 "magic": "mgc", "mag": "mgc", "mgc": "mgc",
                 "spirit": "wpr", "spr": "wpr", "wpr": "wpr", "will": "wpr"}


def _resolve_stat(stat) -> str:
    s = _STAT_ALIASES.get(str(stat).strip().lower())
    if s is None:
        raise ValueError(f"unknown stat {stat!r} (Speed / Strength / Magic / Spirit)")
    return s

# --- encrypted MAIN-block (old-format) layout (step 4b) -------------------------------------------
# The main AES block is a flat alpha-sorted typed stream. gil + the 256-pair item array sit at FIXED
# offsets in the OLD save format -- empirically confirmed byte-stable across this install's saves at
# scenario 0..7200 (both Memoria and VANILLA saves). NOT blindly trusted: every write first validates
# the item block parses cleanly at MAIN_ITEMS_OFF (so a differently-laid-out save is REFUSED, not corrupted).
MAIN_GIL_OFF = 5235                                        # UInt32 LE (40000_Common/gil)
MAIN_ITEMS_OFF = 5239                                      # 256 fixed {count:Byte, id:Byte} pairs (count BEFORE id)
MAIN_ITEMS_N = 256
# Old-format players: 9 fixed 244-byte structs; each holds a 5-BYTE equip array [wpn,head,wrist,armor,accy].
# Empirically byte-stable across Memoria + vanilla saves. (slots 5-7 SHARE with story temp Cinna/Marcus/Blank.)
MAIN_EQUIP_OFF = 5784                                      # old-slot 0's equip; old-slot k = +MAIN_PLAYER_STRIDE*k
MAIN_PLAYER_STRIDE = 244
MAIN_PLAYERS_N = 9
OLD_SLOT_NAMES = {0: "Zidane", 1: "Vivi", 2: "Garnet", 3: "Steiner", 4: "Freya",
                  5: "Quina", 6: "Eiko", 7: "Amarant", 8: "Beatrix"}        # old-slot -> primary character
_CHAR_TO_OLD_SLOT = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 11: 8,   # CharacterId -> old-slot
                     8: 5, 9: 6, 10: 7}                                       # Cinna/Marcus/Blank share 5/6/7
# Key items: a 64-byte bitfield, 2 bits per item (obtained at even bit, used at odd) -> 256 items. Item j is at
# byte MAIN_RAREITEMS_OFF + j//4, bits (j%4)*2 (obtained) / +1 (used). Empirically byte-stable (vanilla saves
# decode to sensible key-item sets). (FF9StateGlobal.Get/ParseRareItemByteFormat.)
MAIN_RAREITEMS_OFF = 7947
MAIN_RAREITEMS_LEN = 64
# Per-player growth stats in the old-format player struct (basis Bytes, bonus UInt16 LE; +244*old_slot). Verified:
# all 9 players' basis+bonus match the extra. Byte offsets within the struct (basis is alpha dex,[hp,mp],mgc,str,wpr):
MAIN_BASIS_OFF = 5751                                      # old-slot 0's basis.dex
MAIN_BONUS_OFF = 5759                                      # old-slot 0's bonus.dex
_BASIS_STAT_BYTE = {"dex": 0, "mgc": 5, "str": 6, "wpr": 7}   # Byte offset within basis
_BONUS_STAT_OFF = {"dex": 0, "mgc": 2, "str": 4, "wpr": 6}    # UInt16 byte offset within bonus (alpha dex,mgc,str,wpr)

# CharacterId (Memoria.Data.Characters.CharacterId) -- the key of `players[].info.slot_no` in the save. The
# equip array is keyed by THIS (not array index / EquipmentSetId, which diverges above 7). Names/ids only.
CHARACTER_NAMES = {0: "Zidane", 1: "Vivi", 2: "Garnet", 3: "Steiner", 4: "Freya", 5: "Quina",
                   6: "Eiko", 7: "Amarant", 8: "Cinna", 9: "Marcus", 10: "Blank", 11: "Beatrix"}
_CHAR_BY_NAME = {v.lower(): k for k, v in CHARACTER_NAMES.items()}
_CHAR_BY_NAME.update({"dagger": 2, "salamander": 7})       # Garnet's alias, Amarant's nickname


@dataclass
class ItemReport:
    """What a save slot's items/equipment/gil decode to (from the Memoria extra file)."""
    gil: int | None = None
    inventory: list = field(default_factory=list)         # [(id, name, count), ...]
    equipment: list = field(default_factory=list)         # [{"slot_no", "name", "equip": {slot: (id, name)|None}}]
    keyitems: list = field(default_factory=list)          # [(id, name, obtained, used), ...] (key/important items)
    stats: list = field(default_factory=list)             # [{"slot_no", "name", "stats": {Speed, Strength, ...}}]


@dataclass
class StatWriteReport:
    """The outcome of a :func:`set_stat_extra` / :func:`set_main_stat` call (dry-run or applied)."""
    path: str
    slot_no: int
    character: "str | None"
    stat: str                                             # in-game label (Speed/Strength/Magic/Spirit)
    old_value: int                                        # old displayed (basis) value
    new_value: int                                        # new displayed (basis) value
    old_bonus: int
    new_bonus: int
    wrote: bool
    backup_path: "str | None" = None


@dataclass
class KeyItemWriteReport:
    """The outcome of a :func:`set_keyitem_extra` / :func:`set_main_keyitem` call (dry-run or applied)."""
    path: str
    item_id: int
    item_name: "str | None"
    obtained: bool
    used: bool
    action: str                                           # "added" | "changed" | "removed" | "unchanged"
    wrote: bool
    backup_path: "str | None" = None


@dataclass
class GilWriteReport:
    """The outcome of a :func:`set_gil` call (dry-run or applied)."""
    path: str
    old_gil: int
    new_gil: int
    bytes_changed: int                                    # how many on-disk bytes the gil edit moves (<=4)
    wrote: bool                                           # False = dry-run (nothing written)
    backup_path: "str | None" = None


@dataclass
class ItemWriteReport:
    """The outcome of a :func:`set_item` call (dry-run or applied)."""
    path: str
    item_id: int
    item_name: "str | None"
    old_count: int
    new_count: int
    action: str                                           # "added" | "changed" | "removed" | "unchanged"
    wrote: bool
    backup_path: "str | None" = None


@dataclass
class EquipWriteReport:
    """The outcome of a :func:`set_equip` / :func:`set_main_equip` call (dry-run or applied)."""
    path: str
    slot_no: int                                          # CharacterId (extra writer) OR old-format slot 0-8 (main writer)
    character: "str | None"                               # its in-save name
    slot: str                                             # one of EQUIP_SLOTS
    old_id: int
    old_name: "str | None"
    new_id: int
    new_name: "str | None"
    wrote: bool
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


def _sjbool(node) -> bool:
    """A ``rareItemsEx`` ``obtained``/``used`` leaf -> bool. Stored as a VALUE string ``"True"``/``"False"`` (NOT
    a Bool leaf), so ``bool(value)`` would be wrong (``bool("False")`` is True); compare the text."""
    if node is None:
        return False
    v = node.value
    return v if isinstance(v, bool) else str(v).strip().lower() == "true"


def read_keyitems(common) -> list:
    """``40000_Common/rareItemsEx`` -> ``[(id, name, obtained, used), ...]`` -- the key/important items the save
    knows about (names via the live :mod:`ff9mapkit.keyitems` table, ``None`` if the install isn't reachable)."""
    arr = _sj.get_path(common, "rareItemsEx")
    out = []
    if arr is None:
        return out
    for e in arr:
        eid = _sj.get_path(e, "id")
        if eid is None:
            continue
        i = int(eid.value)
        out.append((i, _keyitems.name_of(i), _sjbool(_sj.get_path(e, "obtained")),
                    _sjbool(_sj.get_path(e, "used"))))
    return out


def report_from_common(common) -> ItemReport:
    return ItemReport(gil=read_gil(common), inventory=read_inventory(common),
                      equipment=read_equipment(common), keyitems=read_keyitems(common),
                      stats=read_stats(common))


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
    populated slot. Accepts a Memoria extra file directly (plaintext, no crypto), OR the encrypted
    ``SavedData_ww.dat`` container (enumerates populated slots via :meth:`save.FF9Save.populated` -- needs
    pycryptodome). A Memoria slot reads its EXTRA (what the game loads); a VANILLA slot (no extra) reads the
    encrypted MAIN block (:func:`decode_main_block` -- gil + inventory + the 9 players' equipment). A slot that
    decodes to neither is reported as ``None``. Raises with a clear message if nothing decodes."""
    p = str(path)
    # case 1: path IS a Memoria extra file (a plaintext SimpleJSON tree with 40000_Common)
    common, _, _ = load_extra_common(p)
    if common is not None:
        return [("Memoria extra-save", report_from_common(common))]
    # case 2: the encrypted container -> per populated slot, the extra (Memoria) or the main block (vanilla)
    sv = _save.FF9Save.load(p)
    out = []
    for s in sv.populated():
        extra = _save.extra_file_path(p, s.block)
        common = load_extra_common(extra)[0] if (extra and os.path.isfile(extra)) else None
        if common is not None:
            out.append((_save._slot_label(s) + " · Memoria extra", report_from_common(common)))
        else:
            rep = decode_main_block(p, s.block)           # a vanilla slot -> read the main block
            out.append((_save._slot_label(s) + (" · main (vanilla)" if rep is not None else " · (undecodable)"),
                        rep))
    if not out:
        raise ValueError("no populated save slots found in this file")
    return out


# --- write surface: shared machinery for the EXTRA writers (the load-authoritative store) ----------

def _atomic_write(extra_path, raw: bytes, new_bytes: bytes, *, backup: bool) -> "str | None":
    """Backup-guarded ATOMIC overwrite of a Memoria extra save file. Writes a timestamped ``<path>.bak.<ts>``
    from the PRISTINE ``raw`` first (never clobbers a prior backup -- matches :func:`save.apply_story_edit`),
    then writes ``new_bytes`` to a sibling ``.tmp`` and ``os.replace``\\ s it in (so the real save is never
    observed half-written). Returns the backup path (or None when ``backup`` is False)."""
    backup_path = None
    if backup:
        backup_path = f"{extra_path}.bak.{time.strftime('%Y%m%d-%H%M%S')}"
        with open(backup_path, "wb") as fh:
            fh.write(raw)
    tmp = f"{extra_path}.tmp"
    with open(tmp, "wb") as fh:
        fh.write(new_bytes)
    os.replace(tmp, extra_path)
    return backup_path


def _load_for_edit(extra_path):
    """Read + parse a Memoria extra file for editing: returns ``(raw, root, trailing, common)``. Runs GATE 1
    (the codec must reproduce the on-disk bytes exactly -- else refuse, never risk a corrupt write) and the
    ``40000_Common`` SJClass guards. Raises ValueError with a clear message on any problem."""
    try:
        raw = open(extra_path, "rb").read()
    except OSError as e:
        raise ValueError(f"cannot read extra save file {extra_path!r}: {e}") from e
    try:
        root, trailing = _sj.loads(raw)
    except (ValueError, IndexError) as e:
        raise ValueError(f"{extra_path!r} is not a parseable Memoria extra save file: {e}") from e
    if _sj.dumps(root, trailing) != raw:                   # GATE 1
        raise ValueError("refusing to edit: the SimpleJSON codec does not reproduce this file byte-for-byte "
                         "(editing could corrupt it). Please report this save.")
    common = _sj.get_path(root, COMMON)
    if common is None:
        raise ValueError(f"no {COMMON} module in {extra_path!r}")
    if not isinstance(common, _sj.SJClass):
        raise ValueError(f"{COMMON} is not a class node in {extra_path!r}; refusing to edit")
    return raw, root, trailing, common


def _assert_scoped(raw: bytes, root, trailing: bytes, allowed_prefixes):
    """Re-serialize the (mutated) ``root`` and assert the change is SCOPED: every path where the new tree
    differs from the pristine on-disk tree must lie under one of ``allowed_prefixes`` (tuples). Returns
    ``(new_bytes, changed_paths)``. Aborts (AssertionError) if anything outside the allowed scope moved -- the
    general analog of :func:`set_gil`'s byte-surgical gate, for variable-length (items) edits."""
    new_bytes = _sj.dumps(root, trailing)
    orig, _ = _sj.loads(raw)                               # pristine tree (GATE 1 proved this == on-disk)
    changed = list(_sj.diff_paths(orig, root))
    for p in changed:
        if not any(p[:len(pre)] == tuple(pre) for pre in allowed_prefixes):
            raise AssertionError(f"edit touched an unexpected path {p}; aborting (allowed: {allowed_prefixes})")
    return new_bytes, changed


def _resolve_slot(slot) -> int:
    """An equip slot NAME (or alias) -> its index in :data:`EQUIP_SLOTS`. Raises ValueError on an unknown slot."""
    s = str(slot).strip().lower()
    s = _SLOT_ALIASES.get(s, s)
    if s not in EQUIP_SLOTS:
        raise ValueError(f"unknown equip slot {slot!r} (expected one of {', '.join(EQUIP_SLOTS)})")
    return EQUIP_SLOTS.index(s)


def _find_player(players, character):
    """Find the ``players[]`` entry for ``character`` -- an int CharacterId (0-11, matched on ``info/slot_no``)
    or a name (matched first against each entry's in-save ``name``, then against the canonical CharacterId
    names/aliases). Returns ``(index, node, slot_no, name)``. Raises ValueError if absent."""
    if not isinstance(players, _sj.SJArray):
        raise ValueError(f"no {COMMON}/players array to equip")
    entries = []
    for i, p in enumerate(players):
        sn = _sj.get_path(p, "info", "slot_no")
        nm = _sj.get_path(p, "name")
        entries.append((i, p, int(sn.value) if sn is not None else None, nm.value if nm is not None else None))
    want_slot = None
    if isinstance(character, bool):
        raise ValueError("character cannot be a boolean")
    if isinstance(character, int):
        want_slot = character
    else:
        key = str(character).strip().lower()
        if key.isdigit():                                  # a numeric CharacterId, e.g. the CLI's "6"
            want_slot = int(key)
        else:
            for i, p, sn, nm in entries:                   # try the in-save name first (handles renamed PCs)
                if nm is not None and nm.strip().lower() == key:
                    return i, p, sn, nm
            if key in _CHAR_BY_NAME:
                want_slot = _CHAR_BY_NAME[key]
    if want_slot is not None:
        for i, p, sn, nm in entries:
            if sn == want_slot:
                return i, p, sn, nm
    have = ", ".join(f"{nm or '?'}({sn})" for _, _, sn, nm in entries)
    raise ValueError(f"no character {character!r} in this save (have: {have})")


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
    block = _resolve_block(slot=slot, save=save, autosave=autosave)
    extra = _save.extra_file_path(p, block)
    if extra is None:
        raise ValueError(f"{p!r} is not a .dat save container or a Memoria extra file")
    if not os.path.isfile(extra):
        raise ValueError(f"no Memoria extra file for that slot: {extra}")
    return extra


def _resolve_block(*, slot=None, save=None, autosave=False) -> int:
    """A container data-block index from ``--autosave`` (block 0) or a 0-indexed ``(slot, save)``
    (``block_index``). Raises ValueError on an ambiguous / missing selection."""
    if autosave and (slot is not None or save is not None):
        raise ValueError("pass --autosave OR --slot/--save-no, not both")
    if autosave:
        return 0
    if slot is not None and save is not None:
        return _save.block_index(int(slot), int(save))
    raise ValueError("to edit a SavedData_ww.dat container, pass --slot and --save-no (0-indexed) or "
                     "--autosave; or pass a SavedData_ww_Memoria_*.dat extra file directly")


def set_gil(extra_path, gil: int, *, dry_run: bool = True, backup: bool = True) -> GilWriteReport:
    """Write ``40000_Common/gil`` in a Memoria EXTRA save file (the load-authoritative store -- memory
    project-ff9-save-item-layout), preserving every other byte. gil is a length-stable Int32 leaf (IntValue,
    tag 4), so this is the smallest possible real-save mutation: the #5 editor's FIRST write and the falsifiable
    proof of "the extra overrides the encrypted main block on load" -- write ONLY the extra, and if the in-game
    gil changes to match, the extra wins (the main block still holds the old value). This writes only the extra;
    :func:`set_gil_in_save` dual-writes the main block too. Never touches ``00001_time``.

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
        backup_path = _atomic_write(extra_path, raw, new_bytes, backup=backup)
        check = load_extra_common(extra_path)[0]           # CONFIRM the write took (mirrors apply_story_edit's re-read)
        cg = _sj.get_path(check, "gil") if check is not None else None
        if cg is None or int(cg.value) != gil:
            raise AssertionError(f"post-write check failed: gil did not read back as {gil:,}")
        did_write = True
    return GilWriteReport(path=str(extra_path), old_gil=old_gil, new_gil=gil,
                          bytes_changed=len(diff), wrote=did_write, backup_path=backup_path)


# --- write surface: inventory + equipment (step 4a, extra-only) ------------------------------------

def set_item(extra_path, item, count: int, *, dry_run: bool = True, backup: bool = True) -> ItemWriteReport:
    """Set the inventory COUNT of ``item`` (a kit name or 0-254 id) in a Memoria EXTRA save file. ``count`` 0
    REMOVES the stack; otherwise it's added (in ascending-id position, matching how the engine writes the bag)
    or its count is updated. ``count`` is clamped to the in-game cap (99). The extra's ``40000_Common/items`` is
    a variable ``[{id,count}]`` list of live stacks; the engine DROPS ``NoItem``/unknown ids on load, so only a
    real id is written. Same safety as :func:`set_gil` but with a SCOPED-change check (only the ``items`` array
    may move) instead of the byte-surgical one: GATE 1 + scoped diff + atomic write + a post-write re-read that
    confirms the new count. ``dry_run`` by default; a no-op writes nothing. Returns an :class:`ItemWriteReport`."""
    iid = _items.resolve(item)                             # name/id -> 0-255, validated (raises on unknown)
    if iid == NO_ITEM:
        raise ValueError("cannot add NoItem (255); pass count=0 to REMOVE an item instead")
    if isinstance(count, bool) or not isinstance(count, int):
        raise TypeError(f"count must be an int (got {type(count).__name__})")
    if count < 0:
        raise ValueError(f"count cannot be negative (got {count}); use 0 to remove")
    count = min(count, ITEM_COUNT_CAP)                     # clamp to the in-game per-stack cap
    raw, root, trailing, common = _load_for_edit(extra_path)
    arr = common.get("items")
    if not isinstance(arr, _sj.SJArray):
        raise ValueError(f"no {COMMON}/items array in {extra_path!r}")
    idx, old_count = None, 0
    for i, e in enumerate(arr.items):                      # find the existing stack for this id (if any)
        eid = _sj.get_path(e, "id")
        if isinstance(e, _sj.SJClass) and eid is not None and int(eid.value) == iid:
            cnode = _sj.get_path(e, "count")               # guard like read_inventory does (clean ValueError, not AttributeError)
            if cnode is None:
                raise ValueError(f"malformed {COMMON}/items entry for id {iid} (no count) in {extra_path!r}; "
                                 "refusing to edit")
            idx, old_count = i, int(cnode.value)
            break
    if count == 0:
        action = "removed" if idx is not None else "unchanged"
        if idx is not None:
            del arr.items[idx]
    elif idx is not None:
        action = "unchanged" if count == old_count else "changed"
        arr.items[idx].set("count", _sj.SJData(_sj.INT, count))   # preserve key order (id, count); INT tag
    else:
        action = "added"
        entry = _sj.SJClass()                              # a new {id, count} stack, id-first (matches the engine)
        entry.add("id", _sj.SJData(_sj.INT, iid))
        entry.add("count", _sj.SJData(_sj.INT, count))
        pos = next((i for i, e in enumerate(arr.items)
                    if _sj.get_path(e, "id") is not None and int(_sj.get_path(e, "id").value) > iid), len(arr.items))
        arr.items.insert(pos, entry)
    new_bytes, changed = _assert_scoped(raw, root, trailing, [(COMMON, "items")])
    backup_path, did_write = None, False
    if not dry_run and changed:                            # `changed` empty => a true no-op => write nothing
        backup_path = _atomic_write(extra_path, raw, new_bytes, backup=backup)
        chk = read_inventory(load_extra_common(extra_path)[0])    # CONFIRM the write took
        got = next((c for i, _, c in chk if i == iid), 0)
        if got != count:
            raise AssertionError(f"post-write check failed: {iid} count read back {got}, expected {count}")
        did_write = True
    return ItemWriteReport(path=str(extra_path), item_id=iid, item_name=_items.name_of(iid),
                           old_count=old_count, new_count=count, action=action,
                           wrote=did_write, backup_path=backup_path)


def set_equip(extra_path, character, slot, item, *, dry_run: bool = True, backup: bool = True) -> EquipWriteReport:
    """Set one equip ``slot`` (weapon/head/wrist/armor/accessory, + aliases body/acc) of one ``character`` (a
    CharacterId 0-11, or a name -- the in-save name or a canonical one incl. dagger/salamander) in a Memoria
    EXTRA save file. ``item`` is a kit name/id, or ``None``/255/"empty" to UNEQUIP. The save's
    ``players[].equip`` is a 5-int array keyed by ``info/slot_no`` (CharacterId); the engine resets an unknown
    id to NoItem on load, so only a real id (or 255) is written -- and it RECOMPUTES derived defence/affinity
    from the equip, so we only touch the id. Length-stable INT edit, scoped to that one player's ``equip``.
    GATE 1 + scoped diff + atomic write + a post-write re-read confirm; ``dry_run`` by default. Returns an
    :class:`EquipWriteReport`."""
    slot_idx = _resolve_slot(slot)
    if item is None or (isinstance(item, str) and item.strip().lower() in ("none", "empty", "unequip", "")):
        iid = NO_ITEM
    else:
        iid = _items.resolve(item)                         # 0-255 (255 also allowed = unequip)
    raw, root, trailing, common = _load_for_edit(extra_path)
    players = common.get("players")
    pidx, pnode, slot_no, cname = _find_player(players, character)
    eq = pnode.get("equip")
    if not isinstance(eq, _sj.SJArray) or len(eq.items) < len(EQUIP_SLOTS):
        raise ValueError(f"{cname or character}'s equip is not a 5-slot array; refusing to edit")
    old_node = eq.items[slot_idx]
    old_id = int(old_node.value) if isinstance(old_node, _sj.SJData) else NO_ITEM
    eq.items[slot_idx] = _sj.SJData(_sj.INT, iid)          # length-stable; preserves the array shape
    new_bytes, changed = _assert_scoped(raw, root, trailing, [(COMMON, "players", pidx, "equip")])
    backup_path, did_write = None, False
    if not dry_run and changed:
        backup_path = _atomic_write(extra_path, raw, new_bytes, backup=backup)
        chk = _sj.get_path(load_extra_common(extra_path)[0], "players", pidx, "equip")  # CONFIRM
        if chk is None or int(chk.items[slot_idx].value) != iid:
            raise AssertionError(f"post-write check failed: {cname} {EQUIP_SLOTS[slot_idx]} did not read back {iid}")
        did_write = True
    return EquipWriteReport(path=str(extra_path), slot_no=slot_no, character=cname, slot=EQUIP_SLOTS[slot_idx],
                            old_id=old_id, old_name=(None if old_id == NO_ITEM else _items.name_of(old_id)),
                            new_id=iid, new_name=(None if iid == NO_ITEM else _items.name_of(iid)),
                            wrote=did_write, backup_path=backup_path)


def _new_bonus_for(target: int, old_basis: int, old_bonus: int) -> int:
    """The `bonus` accumulator that makes the level-up recompute land on ``target`` at the current level:
    ``basis = (base+level*growth) + (bonus>>5)`` and ``base+level*growth = old_basis - (old_bonus>>5)``, so
    ``new_bonus = (target - old_basis + (old_bonus>>5)) << 5`` (the base/growth terms cancel -- no game data
    needed). Clamped to a UInt16 [0, 65535] (the engine's bonus type)."""
    return max(0, min(0xFFFF, (target - old_basis + (old_bonus >> 5)) << 5))


def read_stats(common) -> list:
    """``[{slot_no, name, stats: {Speed, Strength, Magic, Spirit}}, ...]`` -- each player's displayed (basis)
    growth stats, from the extra. (basis is what the menu shows; bonus is the hidden accumulator.)"""
    players = _sj.get_path(common, "players")
    out = []
    if players is None:
        return out
    for p in players:
        basis = _sj.get_path(p, "basis")
        if basis is None:
            continue
        stats = {STAT_LABELS[f]: (int(_sj.get_path(basis, f).value) if _sj.get_path(basis, f) is not None else None)
                 for f in STAT_CAPS}
        sn, nm = _sj.get_path(p, "info", "slot_no"), _sj.get_path(p, "name")
        out.append({"slot_no": int(sn.value) if sn is not None else None,
                    "name": nm.value if nm is not None else None, "stats": stats})
    return out


def set_stat_extra(extra_path, character, stat, target: int, *, dry_run: bool = True,
                   backup: bool = True) -> StatWriteReport:
    """Set a character's permanent growth STAT (Speed/Strength/Magic/Spirit) in a Memoria EXTRA save. Writes BOTH
    ``players[].basis.<field>`` (the displayed value -- shows immediately) AND ``players[].bonus.<field>`` (the
    hidden equipment accumulator -- so the level-up recompute holds the value; see :func:`_new_bonus_for`).
    ``target`` clamps to the stat cap (Speed/Spirit 50, Strength/Magic 99). Scoped to that one player's
    basis+bonus; GATE 1 + atomic write + backup + post-write confirm; dry-run default."""
    field = _resolve_stat(stat)
    if isinstance(target, bool) or not isinstance(target, int):
        raise TypeError(f"target must be an int (got {type(target).__name__})")
    if target < 0:
        raise ValueError(f"target stat cannot be negative (got {target})")
    target = min(target, STAT_CAPS[field])
    raw, root, trailing, common = _load_for_edit(extra_path)
    players = common.get("players")
    pidx, pnode, slot_no, cname = _find_player(players, character)
    basis, bonus = pnode.get("basis"), pnode.get("bonus")
    if not isinstance(basis, _sj.SJClass) or not isinstance(bonus, _sj.SJClass):
        raise ValueError(f"{cname or character} has no basis/bonus stats; refusing to edit")
    bn, bo = basis.get(field), bonus.get(field)
    if not isinstance(bn, _sj.SJData) or not isinstance(bo, _sj.SJData):
        raise ValueError(f"{cname or character}'s {field} stat leaf is missing; refusing to edit")
    old_basis, old_bonus = int(bn.value), int(bo.value)
    new_bonus = _new_bonus_for(target, old_basis, old_bonus)
    basis.set(field, _sj.SJData(_sj.INT, target))
    bonus.set(field, _sj.SJData(_sj.INT, new_bonus))
    new_bytes, changed = _assert_scoped(raw, root, trailing,
                                        [(COMMON, "players", pidx, "basis"), (COMMON, "players", pidx, "bonus")])
    backup_path, did_write = None, False
    if not dry_run and changed:
        backup_path = _atomic_write(extra_path, raw, new_bytes, backup=backup)
        cb = _sj.get_path(load_extra_common(extra_path)[0], "players", pidx, "basis", field)   # CONFIRM
        if cb is None or int(cb.value) != target:
            raise AssertionError(f"post-write check failed: {cname} {field} basis read back {cb}, expected {target}")
        did_write = True
    return StatWriteReport(path=str(extra_path), slot_no=slot_no, character=cname, stat=STAT_LABELS[field],
                           old_value=old_basis, new_value=target, old_bonus=old_bonus, new_bonus=new_bonus,
                           wrote=did_write, backup_path=backup_path)


def render_stat_write(rep: StatWriteReport) -> str:
    """A human-readable summary of a :func:`set_stat_extra` / :func:`set_main_stat` outcome."""
    who = rep.character or f"slot {rep.slot_no}"
    if rep.old_value == rep.new_value and rep.wrote is False and rep.old_bonus == rep.new_bonus:
        return f"  {who} {rep.stat} already {rep.new_value} in {rep.path} -- nothing to change."
    head = "WROTE" if rep.wrote else "DRY RUN -- would set"
    lines = [f"  {head} {who} {rep.stat}: {rep.old_value} -> {rep.new_value} in {rep.path} "
             f"(bonus {rep.old_bonus} -> {rep.new_bonus})"]
    lines.append(f"  Backup: {rep.backup_path}" if rep.backup_path else
                 ("  (--no-backup: no backup written)" if rep.wrote else
                  "  Re-run with --apply to write (a .bak backup is made first unless --no-backup)."))
    return "\n".join(lines)


def set_keyitem_extra(extra_path, keyitem, *, obtained: bool = True, used: bool = False,
                      dry_run: bool = True, backup: bool = True) -> KeyItemWriteReport:
    """Set a KEY/important item's state in a Memoria EXTRA save's ``40000_Common/rareItemsEx`` list (each entry
    ``{id, obtained, used}`` -- the bools are VALUE strings ``"True"``/``"False"``). ``obtained``/``used`` both
    False REMOVES the entry (the engine only stores known key items); otherwise it's added (ascending-id) or
    updated. ``keyitem`` is a name (live :mod:`keyitems` table) or a 0-255 id. Same safety as :func:`set_item`:
    GATE 1 + a scoped-change check (only ``rareItemsEx`` moves) + atomic write + backup + post-write confirm +
    dry-run default."""
    iid = _keyitems.resolve(keyitem)
    raw, root, trailing, common = _load_for_edit(extra_path)
    arr = common.get("rareItemsEx")
    if not isinstance(arr, _sj.SJArray):
        raise ValueError(f"no {COMMON}/rareItemsEx in {extra_path!r} (an early save with no key items yet?)")
    idx, old_ob, old_us = None, False, False
    for i, e in enumerate(arr.items):
        eid = _sj.get_path(e, "id")
        if isinstance(e, _sj.SJClass) and eid is not None and int(eid.value) == iid:
            idx, old_ob, old_us = i, _sjbool(_sj.get_path(e, "obtained")), _sjbool(_sj.get_path(e, "used"))
            break
    sb = lambda b: _sj.SJData(_sj.VALUE, "True" if b else "False")   # noqa: E731  (the engine's bool-as-string form)
    if not obtained and not used:
        action = "removed" if idx is not None else "unchanged"
        if idx is not None:
            del arr.items[idx]
    elif idx is not None:
        action = "unchanged" if (obtained, used) == (old_ob, old_us) else "changed"
        arr.items[idx].set("obtained", sb(obtained))
        arr.items[idx].set("used", sb(used))
    else:
        action = "added"
        entry = _sj.SJClass()                              # id, obtained, used -- the engine's key order
        entry.add("id", _sj.SJData(_sj.INT, iid))
        entry.add("obtained", sb(obtained))
        entry.add("used", sb(used))
        pos = next((i for i, e in enumerate(arr.items)
                    if _sj.get_path(e, "id") is not None and int(_sj.get_path(e, "id").value) > iid), len(arr.items))
        arr.items.insert(pos, entry)
    new_bytes, changed = _assert_scoped(raw, root, trailing, [(COMMON, "rareItemsEx")])
    backup_path, did_write = None, False
    if not dry_run and changed:
        backup_path = _atomic_write(extra_path, raw, new_bytes, backup=backup)
        chk = {i: (ob, us) for i, _, ob, us in read_keyitems(load_extra_common(extra_path)[0])}
        got = chk.get(iid, (False, False))
        if got != (obtained, used) and not (obtained is False and used is False and iid not in chk):
            raise AssertionError(f"post-write check failed: key item {iid} read back {got}")
        did_write = True
    return KeyItemWriteReport(path=str(extra_path), item_id=iid, item_name=_keyitems.name_of(iid),
                              obtained=obtained, used=used, action=action, wrote=did_write, backup_path=backup_path)


# --- write surface: the encrypted MAIN block (step 4b -- edit no-extra/vanilla saves) -------------

def validate_main_block(pt) -> None:
    """Raise ValueError unless ``pt`` (a decrypted save block) is a populated OLD-format block whose 256-pair
    item array parses cleanly at :data:`MAIN_ITEMS_OFF`: every LIVE (count>=1) pair is a valid item
    (``count 1-99, id 0-254``) and the array ENDS in padding (the last slot's count is 0). count==0 entries may
    appear mid-list (FF9 doesn't always compact the inventory -- e.g. a ``{0, 196}`` gap), so padding is keyed on
    count, not position. This is the SAFETY GATE: a save whose gil/item offsets differ from this install's old
    format won't satisfy it (a wrong offset reads random bytes -> some count lands in 100-255), so we REFUSE
    rather than corrupt it."""
    if pt[:4] != b"SAVE":
        raise ValueError("not a populated save block (no 'SAVE' magic); refusing to edit the main block")
    if pt[MAIN_ITEMS_OFF + 2 * (MAIN_ITEMS_N - 1)] != 0:
        raise ValueError("main item block has no padding tail (last slot is a live item) -- not this install's "
                         "expected old-format layout; refusing to edit")
    for k in range(MAIN_ITEMS_N):
        off = MAIN_ITEMS_OFF + 2 * k
        c, i = pt[off], pt[off + 1]
        if c != 0 and not (1 <= c <= ITEM_COUNT_CAP and 0 <= i <= 254):
            raise ValueError(f"main item block: invalid live pair at slot {k} (count {c}, id {i}) -- not this "
                             "install's expected old-format layout; refusing to edit")


def read_main_gil(pt) -> int:
    return int.from_bytes(pt[MAIN_GIL_OFF:MAIN_GIL_OFF + 4], "little")


def read_main_inventory(pt) -> list:
    """``[(id, name, count), ...]`` -- every LIVE (count>=1) stack in the main block's 256-pair item array
    (count==0 entries, padding or a mid-list gap, are skipped)."""
    out = []
    for k in range(MAIN_ITEMS_N):
        off = MAIN_ITEMS_OFF + 2 * k
        c, i = pt[off], pt[off + 1]
        if c >= 1:
            out.append((i, _items.name_of(i), c))
    return out


def read_main_equipment(pt) -> list:
    """``[{slot_no, name, equip}, ...]`` for the 9 old-format player slots (same shape as :func:`read_equipment`).
    ``slot_no`` is the OLD-slot 0-8; ``name`` its primary character (slots 5-7 may instead hold the temp
    Cinna/Marcus/Blank -- the current gear disambiguates). ``equip`` maps each of the 5 slots to ``(id, name)``
    or ``None`` (255 = empty)."""
    out = []
    for k in range(MAIN_PLAYERS_N):
        base = MAIN_EQUIP_OFF + MAIN_PLAYER_STRIDE * k
        gear = {}
        for j, slot in enumerate(EQUIP_SLOTS):
            iid = pt[base + j]
            gear[slot] = None if iid == NO_ITEM else (iid, _items.name_of(iid))
        out.append({"slot_no": k, "name": OLD_SLOT_NAMES.get(k), "equip": gear})
    return out


def read_main_keyitems(pt) -> list:
    """``[(id, name, obtained, used), ...]`` from the main block's 64-byte 2-bit ``rareItems`` bitfield (only the
    items with either bit set)."""
    out = []
    for b in range(MAIN_RAREITEMS_LEN):
        bv = pt[MAIN_RAREITEMS_OFF + b]
        for k in range(4):
            ob, us = bool(bv & (1 << (k * 2))), bool(bv & (1 << (k * 2 + 1)))
            if ob or us:
                j = b * 4 + k
                out.append((j, _keyitems.name_of(j), ob, us))
    return out


def read_main_stats(pt) -> list:
    """``[{slot_no, name, stats: {Speed, Strength, Magic, Spirit}}, ...]`` -- the 9 old-format players' displayed
    (basis) growth stats from the main block."""
    out = []
    for k in range(MAIN_PLAYERS_N):
        base = MAIN_BASIS_OFF + MAIN_PLAYER_STRIDE * k
        stats = {STAT_LABELS[f]: pt[base + _BASIS_STAT_BYTE[f]] for f in STAT_CAPS}
        out.append({"slot_no": k, "name": OLD_SLOT_NAMES.get(k), "stats": stats})
    return out


def main_report(pt) -> ItemReport:
    """An :class:`ItemReport` for a decrypted main block (gil + inventory + equipment + key items + stats)."""
    return ItemReport(gil=read_main_gil(pt), inventory=read_main_inventory(pt),
                      equipment=read_main_equipment(pt), keyitems=read_main_keyitems(pt),
                      stats=read_main_stats(pt))


def decode_main_block(container, block):
    """Decrypt + decode the gil/inventory of one block of a ``SavedData_ww.dat`` container, or ``None`` if it's
    not a populated/old-format block. Needs pycryptodome (via :class:`save.FF9Save`)."""
    sv = _save.FF9Save.load(container)
    try:
        pt = bytearray(_decrypt_main(sv, block))
    except ValueError:
        return None
    if pt[:4] != b"SAVE":
        return None
    try:
        validate_main_block(pt)
    except ValueError:
        return None
    return main_report(pt)


def _decrypt_main(sv, block: int) -> bytes:
    """Decrypt save block ``block`` of ``sv`` (a :class:`save.FF9Save`), translating a bad block index into a
    clean ValueError (the module's contract -- not a raw IndexError / a wrong block from a negative index)."""
    if not isinstance(block, int) or isinstance(block, bool) or block < 0:
        raise ValueError(f"block must be a non-negative int (got {block!r})")
    try:
        return sv._decrypt_block(block)
    except IndexError as e:
        raise ValueError(f"no save block {block} in this container ({e})") from e


def set_main_gil(container, block: int, gil: int, *, dry_run: bool = True, backup: bool = True) -> GilWriteReport:
    """Write ``40000_Common/gil`` into the ENCRYPTED MAIN block (``block``) of a ``SavedData_ww.dat`` container
    -- the path to editing a save that has **no Memoria extra file** (a vanilla save), and the basis of the gil
    main-mirror. gil sits at the fixed :data:`MAIN_GIL_OFF` (UInt32 LE) in the old format; the block is
    decrypt → edit → re-encrypt (AES-CBC round-trips the untouched bytes, so only the gil's ciphertext moves).

    Same safety as the extra writers: validates the block is a clean old-format save (:func:`validate_main_block`)
    FIRST -- refusing rather than corrupting an unrecognised layout -- then an atomic, timestamped-backup,
    post-write-re-read-confirmed write of the whole container. ``dry_run`` by default; a no-op writes nothing."""
    if isinstance(gil, bool) or not isinstance(gil, int):
        raise TypeError(f"gil must be an int (got {type(gil).__name__})")
    if gil < 0 or gil > GIL_CAP:
        raise ValueError(f"gil must be in [0, {GIL_CAP:,}] (the in-game cap); got {gil:,}")
    try:
        raw = open(container, "rb").read()
    except OSError as e:
        raise ValueError(f"cannot read save container {container!r}: {e}") from e
    sv = _save.FF9Save.load(container)
    pt = bytearray(_decrypt_main(sv, block))
    validate_main_block(pt)                               # GATE: refuse an unrecognised layout
    old = read_main_gil(pt)
    pt[MAIN_GIL_OFF:MAIN_GIL_OFF + 4] = int(gil).to_bytes(4, "little")
    backup_path, did_write = None, False
    if not dry_run and old != gil:
        sv._encrypt_block(block, bytes(pt))              # re-encrypt the edited block into sv.data
        backup_path = _atomic_write(container, raw, bytes(sv.data), backup=backup)
        chk = _save.FF9Save.load(container)               # CONFIRM the write took
        if read_main_gil(bytearray(chk._decrypt_block(block))) != gil:
            raise AssertionError(f"post-write check failed: main-block gil did not read back as {gil:,}")
        did_write = True
    return GilWriteReport(path=f"{container}#block{block}", old_gil=old, new_gil=gil,
                          bytes_changed=4, wrote=did_write, backup_path=backup_path)


def set_main_item(container, block: int, item, count: int, *, dry_run: bool = True,
                  backup: bool = True) -> ItemWriteReport:
    """Set an item's COUNT in the ENCRYPTED MAIN block's 256-pair item array (for editing a vanilla/no-extra
    save). ``count`` 0 removes the stack (-> padding ``{0, 255}``, which loads cleanly); otherwise the count is
    updated in place, or the item is added at the first free slot. ``count`` clamps to 99; ``NoItem`` rejected.
    Same safety as :func:`set_main_gil`: ``validate_main_block`` gate, a scoped check that ONLY the item-array
    bytes moved, atomic container write, timestamped backup, post-write re-read confirm, dry-run default."""
    iid = _items.resolve(item)
    if iid == NO_ITEM:
        raise ValueError("cannot add NoItem (255); pass count=0 to REMOVE an item instead")
    if isinstance(count, bool) or not isinstance(count, int):
        raise TypeError(f"count must be an int (got {type(count).__name__})")
    if count < 0:
        raise ValueError(f"count cannot be negative (got {count}); use 0 to remove")
    count = min(count, ITEM_COUNT_CAP)
    try:
        raw = open(container, "rb").read()
    except OSError as e:
        raise ValueError(f"cannot read save container {container!r}: {e}") from e
    sv = _save.FF9Save.load(container)
    orig_pt = bytes(_decrypt_main(sv, block))
    pt = bytearray(orig_pt)
    validate_main_block(pt)                               # GATE
    idx, old_count = None, 0
    for k in range(MAIN_ITEMS_N):                         # find the live stack for this id
        c, i = pt[MAIN_ITEMS_OFF + 2 * k], pt[MAIN_ITEMS_OFF + 2 * k + 1]
        if c >= 1 and i == iid:
            idx, old_count = k, c
            break
    edited = idx                                          # the slot the edit touches (for a position-aware confirm)
    if count == 0:
        action = "removed" if idx is not None else "unchanged"
        if idx is not None:
            pt[MAIN_ITEMS_OFF + 2 * idx], pt[MAIN_ITEMS_OFF + 2 * idx + 1] = 0, NO_ITEM   # -> clean padding
    elif idx is not None:
        action = "unchanged" if count == old_count else "changed"
        pt[MAIN_ITEMS_OFF + 2 * idx] = count             # keep id, update count
    else:
        action = "added"                                  # reserve the last slot as the padding terminator
        edited = next((k for k in range(MAIN_ITEMS_N - 1) if pt[MAIN_ITEMS_OFF + 2 * k] == 0), None)
        if edited is None:
            raise ValueError("the inventory is full (255 stacks); cannot add another item")
        pt[MAIN_ITEMS_OFF + 2 * edited], pt[MAIN_ITEMS_OFF + 2 * edited + 1] = count, iid
    validate_main_block(pt)                               # still well-formed after the edit
    diff = [k for k in range(len(pt)) if pt[k] != orig_pt[k]]   # SCOPED: only item-array bytes may move
    if diff and (min(diff) < MAIN_ITEMS_OFF or max(diff) >= MAIN_ITEMS_OFF + 2 * MAIN_ITEMS_N):
        raise AssertionError("main item edit touched bytes outside the item array; aborting")
    backup_path, did_write = None, False
    if not dry_run and diff:
        sv._encrypt_block(block, bytes(pt))
        backup_path = _atomic_write(container, raw, bytes(sv.data), backup=backup)
        chk = bytearray(_decrypt_main(_save.FF9Save.load(container), block))   # CONFIRM the exact slot
        gc, gi = chk[MAIN_ITEMS_OFF + 2 * edited], chk[MAIN_ITEMS_OFF + 2 * edited + 1]
        ok = (gc == 0) if count == 0 else (gc == count and gi == iid)
        if not ok:
            raise AssertionError(f"post-write check failed: slot {edited} read back (count {gc}, id {gi})")
        did_write = True
    return ItemWriteReport(path=f"{container}#block{block}", item_id=iid, item_name=_items.name_of(iid),
                           old_count=old_count, new_count=count, action=action,
                           wrote=did_write, backup_path=backup_path)


def _resolve_old_slot(character) -> int:
    """A ``character`` (a CharacterId 0-11, a digit string, or a name/alias incl. Cinna/Marcus/Blank) -> its
    OLD-format slot 0-8. Quina/Cinna -> 5, Eiko/Marcus -> 6, Amarant/Blank -> 7, Beatrix -> 8 (either name targets
    that shared slot; the slot's current gear shows who actually holds it). Raises ValueError on an unknown
    name / out-of-range CharacterId."""
    if isinstance(character, bool):
        raise ValueError("character cannot be a boolean")
    if isinstance(character, str) and character.strip().isdigit():
        character = int(character.strip())
    if isinstance(character, int):
        if character in _CHAR_TO_OLD_SLOT:                # a CharacterId 0-11
            return _CHAR_TO_OLD_SLOT[character]
        raise ValueError(f"CharacterId {character} out of range (0-11)")
    key = str(character).strip().lower()
    cid = _CHAR_BY_NAME.get(key)
    if cid is None or cid not in _CHAR_TO_OLD_SLOT:
        raise ValueError(f"unknown character {character!r} (Zidane..Beatrix, Cinna/Marcus/Blank, Dagger/Salamander)")
    return _CHAR_TO_OLD_SLOT[cid]


def set_main_equip(container, block: int, character, slot, item, *, dry_run: bool = True,
                   backup: bool = True) -> EquipWriteReport:
    """Set one equip ``slot`` of one ``character`` in the ENCRYPTED MAIN block (for editing a vanilla/no-extra
    save's equipment). ``character`` is a CharacterId 0-11 / name / alias (Beatrix = CharacterId 11; old-slots
    5-7 hold Quina/Eiko/Amarant OR the story temp Cinna/Marcus/Blank, either name -> that shared slot -- check the
    slot's current gear). ``item`` is a name/id, or
    ``None``/255/"empty" to unequip. Each player's equip is 5 BYTES at :data:`MAIN_EQUIP_OFF` ``+ stride*old_slot``;
    only that one byte moves. Same safety as :func:`set_main_item`: validate gate, a scoped byte-diff, atomic
    write, timestamped backup, position-aware post-write confirm, dry-run default. The engine resets an unknown
    id to NoItem + recomputes derived stats on load, so only the id is written."""
    slot_idx = _resolve_slot(slot)
    if item is None or (isinstance(item, str) and item.strip().lower() in ("none", "empty", "unequip", "")):
        iid = NO_ITEM
    else:
        iid = _items.resolve(item)
    old_slot = _resolve_old_slot(character)
    try:
        raw = open(container, "rb").read()
    except OSError as e:
        raise ValueError(f"cannot read save container {container!r}: {e}") from e
    sv = _save.FF9Save.load(container)
    orig_pt = bytes(_decrypt_main(sv, block))
    pt = bytearray(orig_pt)
    validate_main_block(pt)                               # GATE (gil/items confirm the old-format layout)
    pos = MAIN_EQUIP_OFF + MAIN_PLAYER_STRIDE * old_slot + slot_idx
    old_id = pt[pos]
    pt[pos] = iid
    diff = [k for k in range(len(pt)) if pt[k] != orig_pt[k]]   # SCOPED: only that one equip byte may move
    if diff and diff != [pos]:
        raise AssertionError(f"main equip edit touched bytes other than slot {old_slot} {EQUIP_SLOTS[slot_idx]}; "
                             "aborting")
    backup_path, did_write = None, False
    if not dry_run and diff:
        sv._encrypt_block(block, bytes(pt))
        backup_path = _atomic_write(container, raw, bytes(sv.data), backup=backup)
        chk = bytearray(_decrypt_main(_save.FF9Save.load(container), block))   # CONFIRM the exact byte
        if chk[pos] != iid:
            raise AssertionError(f"post-write check failed: equip byte read back {chk[pos]}, expected {iid}")
        did_write = True
    return EquipWriteReport(path=f"{container}#block{block}", slot_no=old_slot, character=OLD_SLOT_NAMES.get(old_slot),
                            slot=EQUIP_SLOTS[slot_idx], old_id=old_id,
                            old_name=(None if old_id == NO_ITEM else _items.name_of(old_id)),
                            new_id=iid, new_name=(None if iid == NO_ITEM else _items.name_of(iid)),
                            wrote=did_write, backup_path=backup_path)


def set_main_keyitem(container, block: int, keyitem, *, obtained: bool = True, used: bool = False,
                     dry_run: bool = True, backup: bool = True) -> KeyItemWriteReport:
    """Set a KEY item's state in the ENCRYPTED MAIN block's 64-byte 2-bit ``rareItems`` bitfield (for a
    vanilla/no-extra save). Flips exactly the 2 bits for ``keyitem`` (a name / 0-255 id). Same safety as the
    other main writers: ``validate_main_block`` gate, a scoped byte-diff (only that one byte moves), atomic
    write, timestamped backup, post-write confirm, dry-run default."""
    iid = _keyitems.resolve(keyitem)
    try:
        raw = open(container, "rb").read()
    except OSError as e:
        raise ValueError(f"cannot read save container {container!r}: {e}") from e
    sv = _save.FF9Save.load(container)
    orig_pt = bytes(_decrypt_main(sv, block))
    pt = bytearray(orig_pt)
    validate_main_block(pt)                               # GATE (gil/items confirm the old-format layout)
    pos = MAIN_RAREITEMS_OFF + iid // 4
    shift = (iid % 4) * 2
    old = pt[pos]
    old_ob, old_us = bool(old & (1 << shift)), bool(old & (1 << (shift + 1)))
    nv = old & ~(0b11 << shift)                           # clear this item's 2 bits, then set per request
    if obtained:
        nv |= 1 << shift
    if used:
        nv |= 1 << (shift + 1)
    pt[pos] = nv
    if not obtained and not used:
        action = "removed" if (old_ob or old_us) else "unchanged"
    elif (obtained, used) == (old_ob, old_us):
        action = "unchanged"
    else:
        action = "changed" if (old_ob or old_us) else "added"
    diff = [k for k in range(len(pt)) if pt[k] != orig_pt[k]]   # SCOPED: only that one bitfield byte may move
    if diff and diff != [pos]:
        raise AssertionError("main key-item edit touched bytes other than its rareItems byte; aborting")
    backup_path, did_write = None, False
    if not dry_run and diff:
        sv._encrypt_block(block, bytes(pt))
        backup_path = _atomic_write(container, raw, bytes(sv.data), backup=backup)
        chk = bytearray(_decrypt_main(_save.FF9Save.load(container), block))   # CONFIRM the 2 bits
        cv = chk[pos]
        if (bool(cv & (1 << shift)), bool(cv & (1 << (shift + 1)))) != (obtained, used):
            raise AssertionError(f"post-write check failed: key item {iid} bits read back wrong")
        did_write = True
    return KeyItemWriteReport(path=f"{container}#block{block}", item_id=iid, item_name=_keyitems.name_of(iid),
                              obtained=obtained, used=used, action=action, wrote=did_write, backup_path=backup_path)


def set_main_stat(container, block: int, character, stat, target: int, *, dry_run: bool = True,
                  backup: bool = True) -> StatWriteReport:
    """Set a character's permanent growth STAT in the ENCRYPTED MAIN block (for a vanilla/no-extra save). Writes
    the ``basis`` Byte (displayed) + the ``bonus`` UInt16 (the equipment accumulator) for that old-slot, same as
    :func:`set_stat_extra`. ``target`` clamps to the stat cap. Validate gate + scoped byte-diff (only those <=3
    bytes move) + atomic write + backup + post-write confirm + dry-run."""
    field = _resolve_stat(stat)
    if isinstance(target, bool) or not isinstance(target, int):
        raise TypeError(f"target must be an int (got {type(target).__name__})")
    if target < 0:
        raise ValueError(f"target stat cannot be negative (got {target})")
    target = min(target, STAT_CAPS[field])
    old_slot = _resolve_old_slot(character)
    try:
        raw = open(container, "rb").read()
    except OSError as e:
        raise ValueError(f"cannot read save container {container!r}: {e}") from e
    sv = _save.FF9Save.load(container)
    orig_pt = bytes(_decrypt_main(sv, block))
    pt = bytearray(orig_pt)
    validate_main_block(pt)                               # GATE
    bpos = MAIN_BASIS_OFF + MAIN_PLAYER_STRIDE * old_slot + _BASIS_STAT_BYTE[field]
    opos = MAIN_BONUS_OFF + MAIN_PLAYER_STRIDE * old_slot + _BONUS_STAT_OFF[field]
    old_basis = pt[bpos]
    old_bonus = int.from_bytes(pt[opos:opos + 2], "little")
    new_bonus = _new_bonus_for(target, old_basis, old_bonus)
    pt[bpos] = target
    pt[opos:opos + 2] = new_bonus.to_bytes(2, "little")
    diff = [k for k in range(len(pt)) if pt[k] != orig_pt[k]]   # SCOPED: only the basis byte + the bonus UInt16
    if diff and any(k not in (bpos, opos, opos + 1) for k in diff):
        raise AssertionError(f"main stat edit touched bytes outside {field}'s basis/bonus; aborting")
    backup_path, did_write = None, False
    if not dry_run and diff:
        sv._encrypt_block(block, bytes(pt))
        backup_path = _atomic_write(container, raw, bytes(sv.data), backup=backup)
        chk = bytearray(_decrypt_main(_save.FF9Save.load(container), block))   # CONFIRM
        if chk[bpos] != target or int.from_bytes(chk[opos:opos + 2], "little") != new_bonus:
            raise AssertionError(f"post-write check failed: {field} basis/bonus read back wrong")
        did_write = True
    return StatWriteReport(path=f"{container}#block{block}", slot_no=old_slot, character=OLD_SLOT_NAMES.get(old_slot),
                           stat=STAT_LABELS[field], old_value=old_basis, new_value=target,
                           old_bonus=old_bonus, new_bonus=new_bonus, wrote=did_write, backup_path=backup_path)


def set_gil_in_save(container, block: int, gil: int, *, dry_run: bool = True, backup: bool = True,
                    mirror: bool = True) -> dict:
    """Write gil into a whole save SLOT: the ENCRYPTED MAIN block AND (when ``mirror`` and it exists) the Memoria
    EXTRA file. For a no-extra (vanilla) save only the main block is written; for a Memoria save both are written
    so the load-authoritative extra and the main block stay consistent. Returns ``{"main": GilWriteReport,
    "extra": GilWriteReport|None}``. Each leg is independently dry-run/backup-guarded by its own writer.

    ★ The EXTRA (load-authoritative) leg is written FIRST: the legs aren't transactional across files, so if the
    second (main) leg then fails, the extra already holds the new value -- the game shows the EDIT (correct), and
    only the main-block fallback is left stale (recoverable from its ``.bak``). The reverse order would silently
    show the OLD value in-game on a partial failure. An extra-leg failure raises before the main is touched."""
    extra_rep = None
    if mirror:                                            # the EXTRA is load-authoritative -> write it FIRST
        extra = _save.extra_file_path(container, block)
        if extra and os.path.isfile(extra):
            extra_rep = set_gil(extra, gil, dry_run=dry_run, backup=backup)
    main_rep = set_main_gil(container, block, gil, dry_run=dry_run, backup=backup)
    return {"main": main_rep, "extra": extra_rep}


def set_item_in_save(container, block: int, item, count: int, *, dry_run: bool = True, backup: bool = True,
                     mirror: bool = True) -> dict:
    """Set an item's count in a whole save SLOT: the ENCRYPTED MAIN block AND (when ``mirror`` + present) the
    Memoria EXTRA. Vanilla save -> main only. Returns ``{"main": ItemWriteReport, "extra": ItemWriteReport|None}``."""
    extra_rep = None
    if mirror:                                            # the EXTRA is load-authoritative -> write it first
        extra = _save.extra_file_path(container, block)
        if extra and os.path.isfile(extra):
            extra_rep = set_item(extra, item, count, dry_run=dry_run, backup=backup)
    main_rep = set_main_item(container, block, item, count, dry_run=dry_run, backup=backup)
    return {"main": main_rep, "extra": extra_rep}


def set_equip_in_save(container, block: int, character, slot, item, *, dry_run: bool = True, backup: bool = True,
                      mirror: bool = True) -> dict:
    """Set one equip slot in a whole save SLOT: the MAIN block AND (when ``mirror`` + present) the Memoria EXTRA.
    Vanilla -> main only. ★ The extra keys equip by CharacterId (12 players) and the main by OLD-slot (9); both
    resolve ``character`` independently, so the same name targets the matching player in each. Returns
    ``{"main": EquipWriteReport, "extra": EquipWriteReport|None}`` (extra written FIRST -- it's load-authoritative)."""
    extra_rep = None
    if mirror:
        extra = _save.extra_file_path(container, block)
        if extra and os.path.isfile(extra):
            extra_rep = set_equip(extra, character, slot, item, dry_run=dry_run, backup=backup)
    main_rep = set_main_equip(container, block, character, slot, item, dry_run=dry_run, backup=backup)
    return {"main": main_rep, "extra": extra_rep}


def set_keyitem_in_save(container, block: int, keyitem, *, obtained: bool = True, used: bool = False,
                        dry_run: bool = True, backup: bool = True, mirror: bool = True) -> dict:
    """Set a key item in a whole save SLOT: the MAIN block's ``rareItems`` bitfield AND (when ``mirror`` +
    present) the Memoria EXTRA's ``rareItemsEx``. Vanilla -> main only. Returns ``{"main": KeyItemWriteReport,
    "extra": KeyItemWriteReport|None}`` (extra written FIRST -- it's load-authoritative)."""
    extra_rep = None
    if mirror:
        extra = _save.extra_file_path(container, block)
        if extra and os.path.isfile(extra):
            extra_rep = set_keyitem_extra(extra, keyitem, obtained=obtained, used=used,
                                          dry_run=dry_run, backup=backup)
    main_rep = set_main_keyitem(container, block, keyitem, obtained=obtained, used=used,
                                dry_run=dry_run, backup=backup)
    return {"main": main_rep, "extra": extra_rep}


def set_stat_in_save(container, block: int, character, stat, target: int, *, dry_run: bool = True,
                     backup: bool = True, mirror: bool = True) -> dict:
    """Set a growth stat in a whole save SLOT: the MAIN block (basis+bonus) AND (when ``mirror`` + present) the
    Memoria EXTRA. Vanilla -> main only. Returns ``{"main": StatWriteReport, "extra": StatWriteReport|None}``
    (extra written FIRST -- load-authoritative)."""
    extra_rep = None
    if mirror:
        extra = _save.extra_file_path(container, block)
        if extra and os.path.isfile(extra):
            extra_rep = set_stat_extra(extra, character, stat, target, dry_run=dry_run, backup=backup)
    main_rep = set_main_stat(container, block, character, stat, target, dry_run=dry_run, backup=backup)
    return {"main": main_rep, "extra": extra_rep}


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
    if rep.keyitems:
        held = [(i, n) for i, n, ob, us in rep.keyitems if ob]
        lines.append(f"  Key items ({len(held)} held):")
        lines.append("    " + ", ".join(n or f"id {i}" for i, n in held) if held else "    (none)")
    return "\n".join(lines)


def render_keyitem_write(rep: KeyItemWriteReport) -> str:
    """A human-readable summary of a :func:`set_keyitem_extra` / :func:`set_main_keyitem` outcome."""
    name = rep.item_name or f"key item id {rep.item_id}"
    if rep.action == "unchanged":
        return f"  {name} already obtained={rep.obtained} used={rep.used} in {rep.path} -- nothing to change."
    verb = {"added": "give", "changed": "set", "removed": "remove"}[rep.action]
    head = "WROTE" if rep.wrote else "DRY RUN -- would"
    flags = "removed" if rep.action == "removed" else f"obtained={rep.obtained}, used={rep.used}"
    lines = [f"  {head} {verb} key item {name} ({flags}) in {rep.path}"]
    lines.append(f"  Backup: {rep.backup_path}" if rep.backup_path else
                 ("  (--no-backup: no backup written)" if rep.wrote else
                  "  Re-run with --apply to write (a .bak backup is made first unless --no-backup)."))
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


def render_gil_dual(res: dict) -> str:
    """Render a :func:`set_gil_in_save` outcome (the main block + the extra mirror)."""
    lines = ["  [main block]"]
    lines += ["  " + ln for ln in render_gil_write(res["main"]).splitlines()]
    if res.get("extra") is not None:
        lines.append("  [Memoria extra -- the load-authoritative store]")
        lines += ["  " + ln for ln in render_gil_write(res["extra"]).splitlines()]
    else:
        lines.append("  (no Memoria extra for this slot -- a vanilla save; the main block governs in-game)")
    return "\n".join(lines)


def render_item_dual(res: dict) -> str:
    """Render a :func:`set_item_in_save` outcome (the main block + the extra mirror)."""
    lines = ["  [main block]"]
    lines += ["  " + ln for ln in render_item_write(res["main"]).splitlines()]
    if res.get("extra") is not None:
        lines.append("  [Memoria extra -- the load-authoritative store]")
        lines += ["  " + ln for ln in render_item_write(res["extra"]).splitlines()]
    else:
        lines.append("  (no Memoria extra for this slot -- a vanilla save; the main block governs in-game)")
    return "\n".join(lines)


def render_equip_dual(res: dict) -> str:
    """Render a :func:`set_equip_in_save` outcome (the main block + the extra mirror)."""
    lines = ["  [main block]"]
    lines += ["  " + ln for ln in render_equip_write(res["main"]).splitlines()]
    if res.get("extra") is not None:
        lines.append("  [Memoria extra -- the load-authoritative store]")
        lines += ["  " + ln for ln in render_equip_write(res["extra"]).splitlines()]
    else:
        lines.append("  (no Memoria extra for this slot -- a vanilla save; the main block governs in-game)")
    return "\n".join(lines)


def render_keyitem_dual(res: dict) -> str:
    """Render a :func:`set_keyitem_in_save` outcome (the main block + the extra mirror)."""
    lines = ["  [main block]"]
    lines += ["  " + ln for ln in render_keyitem_write(res["main"]).splitlines()]
    if res.get("extra") is not None:
        lines.append("  [Memoria extra -- the load-authoritative store]")
        lines += ["  " + ln for ln in render_keyitem_write(res["extra"]).splitlines()]
    else:
        lines.append("  (no Memoria extra for this slot -- a vanilla save; the main block governs in-game)")
    return "\n".join(lines)


def render_stat_dual(res: dict) -> str:
    """Render a :func:`set_stat_in_save` outcome (the main block + the extra mirror)."""
    lines = ["  [main block]"]
    lines += ["  " + ln for ln in render_stat_write(res["main"]).splitlines()]
    if res.get("extra") is not None:
        lines.append("  [Memoria extra -- the load-authoritative store]")
        lines += ["  " + ln for ln in render_stat_write(res["extra"]).splitlines()]
    else:
        lines.append("  (no Memoria extra for this slot -- a vanilla save; the main block governs in-game)")
    return "\n".join(lines)


def render_item_write(rep: ItemWriteReport) -> str:
    """A human-readable summary of a :func:`set_item` outcome."""
    name = rep.item_name or f"id {rep.item_id}"
    if rep.action == "unchanged":
        return f"  {name} already x{rep.old_count} in {rep.path} -- nothing to change."
    verb = {"added": f"add x{rep.new_count}", "changed": f"x{rep.old_count} -> x{rep.new_count}",
            "removed": f"remove (was x{rep.old_count})"}[rep.action]
    head = "WROTE" if rep.wrote else "DRY RUN -- would"
    lines = [f"  {head} {verb} of {name} (id {rep.item_id}) in {rep.path}"]
    lines.append(f"  Backup: {rep.backup_path}" if rep.backup_path else
                 ("  (--no-backup: no backup written)" if rep.wrote else
                  "  Re-run with --apply to write (a .bak backup is made first unless --no-backup)."))
    return "\n".join(lines)


def render_equip_write(rep: EquipWriteReport) -> str:
    """A human-readable summary of a :func:`set_equip` outcome."""
    old = rep.old_name or ("(empty)" if rep.old_id == NO_ITEM else f"id {rep.old_id}")
    new = rep.new_name or ("(empty)" if rep.new_id == NO_ITEM else f"id {rep.new_id}")
    who = f"{rep.character or '?'} (slot {rep.slot_no})"
    if rep.old_id == rep.new_id:
        return f"  {who} {rep.slot} already {new} in {rep.path} -- nothing to change."
    head = "WROTE" if rep.wrote else "DRY RUN -- would set"
    lines = [f"  {head} {who} {rep.slot}: {old} -> {new} in {rep.path}"]
    lines.append(f"  Backup: {rep.backup_path}" if rep.backup_path else
                 ("  (--no-backup: no backup written)" if rep.wrote else
                  "  Re-run with --apply to write (a .bak backup is made first unless --no-backup)."))
    return "\n".join(lines)
