"""``[[equipment]]`` -- author a character's STARTING equipment (its new-game default loadout).

Writes a PARTIAL ``<mod>/StreamingAssets/Data/Characters/DefaultEquipment.csv`` delta -- only the characters
you specify. The engine MERGES DefaultEquipment low->high (``ff9play.LoadCharacterDefaultEquipment``), so a
partial file overrides just those characters' default sets and unspecified characters keep the base game's.

★ A slot you OMIT starts EMPTY. The row REPLACES that character's whole default set (it is not a per-slot
patch), so list the full intended loadout. Per-character default equipment is applied at new-game / when a
character JOINS (``FF9Play_SetDefEquips``), so it composes with story_flags' ``[party]`` -- an added member
joins wearing its DefaultEquipment gear. New-game scope (no mid-game retro-apply). Lives on the ENTRY field's
``field.toml``, emitted at the mod-write stage. (memory project-ff9-items-equipment / project-ff9-branch-lanes.)

    [[equipment]]
    character = "steiner"
    weapon = "Excalibur"
    head   = "Genji Helmet"
    armor  = "Genji Armor"
    # head/wrist/armor/accessory omitted -> that slot starts empty
"""
from __future__ import annotations

from .. import items as _items

# Character name -> EquipmentSetId (Memoria.Data.Characters.EquipmentSetId enum; names/ids only -> provenance-clean).
EQUIP_SET_ID = {
    "zidane": 0, "vivi": 1, "garnet": 2, "steiner": 3, "freya": 4, "quina": 5,
    "eiko": 6, "amarant": 7, "cinna": 8, "marcus": 9, "blank": 10, "beatrix": 11,
    "marcus2": 12, "beatrix2": 13, "blank2": 14,
    "dagger": 2, "salamander": 7,                      # aliases (Garnet's alias, Amarant's nickname)
}
SET_NAME = {0: "Zidane", 1: "Vivi", 2: "Garnet", 3: "Steiner", 4: "Freya", 5: "Quina", 6: "Eiko",
            7: "Amarant", 8: "Cinna", 9: "Marcus", 10: "Blank", 11: "Beatrix",
            12: "Marcus2", 13: "Beatrix2", 14: "Blank2"}
SLOTS = ("weapon", "head", "wrist", "armor", "accessory")   # the 5 DefaultEquipment.csv equip columns, in order
MAX_SET_ID = 14


def resolve_set_id(name) -> int:
    """A character name/alias (or a bare 0-14 set id) -> EquipmentSetId. Raises ValueError on unknown/out-of-range."""
    if isinstance(name, bool) or name is None:
        raise ValueError("[[equipment]] needs a 'character' (zidane..beatrix, marcus2/beatrix2/blank2)")
    if isinstance(name, int) or (isinstance(name, str) and name.strip().lstrip("-").isdigit()):
        i = int(name)
        if not 0 <= i <= MAX_SET_ID:
            raise ValueError(f"equipment character id {i} out of range (0-{MAX_SET_ID})")
        return i
    key = "".join(c for c in str(name).lower() if c.isalnum())
    if key not in EQUIP_SET_ID:
        raise ValueError(f"unknown equipment character {name!r} (zidane..beatrix, marcus2/beatrix2/blank2)")
    return EQUIP_SET_ID[key]


def _slot_id(val) -> int:
    """An equip-slot value -> item id, or -1 for empty (None / 'none' / '' / -1). Resolves names via items."""
    if val is None:
        return -1
    if isinstance(val, str) and val.strip().lower() in ("", "none", "-1"):
        return -1
    if isinstance(val, int) and val < 0:
        return -1
    return _items.resolve(val)


def equipment_rows(entries) -> list:
    """``[[equipment]]`` dicts -> sorted ``[(set_id, [weapon, head, wrist, armor, accessory]), ...]`` -- one
    COMPLETE row per character (an omitted slot = -1 empty). De-dups by set id (last wins). Resolves item +
    character names; raises ValueError on an unknown name."""
    by_id: dict = {}
    for e in entries:
        sid = resolve_set_id(e.get("character"))
        by_id[sid] = [_slot_id(e.get(s)) for s in SLOTS]
    return sorted(by_id.items())


def render_default_equipment(entries) -> str:
    """The PARTIAL ``DefaultEquipment.csv`` text (header + one row per authored character). Merged over the
    base by the engine, so it overrides only these characters' default sets."""
    lines = [
        "# ff9mapkit [[equipment]] -- a partial starting-equipment delta (merged over the base by the engine).",
        "# Comment;Id;Weapon;Head;Wrist;Armor;Accessory",
        "# ;Int32;Int32;Int32;Int32;Int32;Int32",
    ]
    for sid, slots in equipment_rows(entries):
        cmt = SET_NAME.get(sid, f"set{sid}")
        lines.append(f"{cmt};{sid};" + ";".join(str(x) for x in slots))
    return "\n".join(lines) + "\n"


def write_default_equipment(layout, entries) -> None:
    """Pure writer: emit the equipment delta into ``layout``'s mod root (``Data/Characters/DefaultEquipment.csv``)."""
    path = layout.default_equipment_csv
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_default_equipment(entries), encoding="utf-8", newline="\n")
