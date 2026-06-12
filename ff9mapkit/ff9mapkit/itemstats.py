"""Item stat / effect catalog -- *what an FF9 item DOES* (weapon power, armor defence, equip stat bonuses,
consumable use-effect, price, type, who-can-equip). The enrichment layer over :mod:`ff9mapkit.items` (which
is names-only): it powers the Info Hub item detail + ``ff9mapkit items``.

PROVENANCE -- item STATS are game DATA, never committed (docs/PROVENANCE.md: the committed ``_*.py`` tables
hold names/ids ONLY). So this reads the numbers LIVE from YOUR OWN install and ships/commits nothing:

    <install>/StreamingAssets/Data/Items/{Items,Weapons,Armors,Stats,ItemEffects}.csv

-- Memoria's editable item tables (semicolon-delimited; the very tables the engine loads). They're cached
in-memory per process. If the install/CSVs aren't reachable, every accessor returns ``None`` and callers
degrade to id+name only (the Info Hub still works offline, just without the stat lines).

Column layout is read from each file's ``# <names...>`` header legend (not hard-coded indices), so it
survives Memoria's option-driven column toggles (``#! IncludeSellingPrice`` etc.).
"""
from __future__ import annotations

from dataclasses import dataclass, field as _dcfield

from . import items as _items

# Element bitmask -- Stats.csv legend ("1-Fire 2-Ice 4-Thunder 8-Earth / 16-Water 32-Wind 64-Holy 128-Dark"),
# = the engine's Memoria.Data EffectElement enum (Ice=Cold, Water=Aqua, Dark=Darkness).
ELEMENTS = [(1, "Fire"), (2, "Ice"), (4, "Thunder"), (8, "Earth"),
            (16, "Water"), (32, "Wind"), (64, "Holy"), (128, "Dark")]
# WeaponCategory bits (Memoria.Data.WeaponCategory): 128 "Default" is a no-op flag, omitted.
WEAPON_CATEGORY = [(1, "short-range"), (2, "long-range"), (4, "throw"), (8, "offset")]
# The 8 Items.csv type-bit columns -> a friendly slot/kind (one item may set several, e.g. Item+Usable).
TYPE_COLS = [("Weapon", "weapon"), ("Armlet", "wrist"), ("Helmet", "head"), ("Armor", "body"),
             ("Accessory", "accessory"), ("Item", "item"), ("Gem", "gem"), ("Usable", "usable")]
# Items.csv per-character equip-bit columns, in order (= the engine's ItemCharacter mask).
CHARS = ["Zidane", "Vivi", "Garnet", "Steiner", "Freya", "Quina", "Eiko", "Amarant",
         "Cinna", "Marcus", "Blank", "Beatrix"]


def decode_elements(mask) -> list:
    """An element bitmask -> the list of element names it sets (e.g. ``5`` -> ``['Fire', 'Thunder']``)."""
    try:
        m = int(mask)
    except (TypeError, ValueError):
        return []
    return [name for bit, name in ELEMENTS if m & bit]


def decode_category(mask) -> list:
    try:
        m = int(mask)
    except (TypeError, ValueError):
        return []
    return [name for bit, name in WEAPON_CATEGORY if m & bit]


# BattleStatus bitmask (Memoria.Data.Battle.BattleStatus) -- a consumable's use-effect carries its status
# set here (a cure item like Phoenix Down/Antidote has Power 0 and acts ENTIRELY via this mask; the add-vs-
# remove direction is the effect's ScriptId, which we don't decode -- so we name the statuses neutrally).
STATUSES = [
    (1 << 0, "Petrify"), (1 << 1, "Venom"), (1 << 2, "Virus"), (1 << 3, "Silence"),
    (1 << 4, "Blind"), (1 << 5, "Trouble"), (1 << 6, "Zombie"), (1 << 7, "EasyKill"),
    (1 << 8, "Death"), (1 << 9, "LowHP"), (1 << 10, "Confuse"), (1 << 11, "Berserk"),
    (1 << 12, "Stop"), (1 << 13, "AutoLife"), (1 << 14, "Trance"), (1 << 15, "Defend"),
    (1 << 16, "Poison"), (1 << 17, "Sleep"), (1 << 18, "Regen"), (1 << 19, "Haste"),
    (1 << 20, "Slow"), (1 << 21, "Float"), (1 << 22, "Shell"), (1 << 23, "Protect"),
    (1 << 24, "Heat"), (1 << 25, "Freeze"), (1 << 26, "Vanish"), (1 << 27, "Doom"),
    (1 << 28, "Mini"), (1 << 29, "Reflect"), (1 << 30, "Jump"), (1 << 31, "GradualPetrify"),
]


def decode_status(mask) -> list:
    """A BattleStatus bitmask -> the list of status names it sets (e.g. ``256`` -> ``['Death']``)."""
    try:
        m = int(mask)
    except (TypeError, ValueError):
        return []
    return [name for bit, name in STATUSES if m & bit]


@dataclass
class ItemStat:
    """The joined stat record for one item id (the fields that apply to its type are populated; the rest
    stay ``None``/empty). ``bonus``/``affinity`` carry only NON-zero entries (so an Empty bonus shows nothing)."""
    id: int
    name: str = ""
    types: list = _dcfield(default_factory=list)        # ['weapon'] / ['body'] / ['item','usable'] ...
    price: int = 0
    sell: int = 0
    equip: list = _dcfield(default_factory=list)         # character names that can equip it
    abilities: list = _dcfield(default_factory=list)     # raw ability tokens taught when equipped (AA:/SA:)
    # weapon (WeaponId >= 0)
    power: "int | None" = None
    elements: list = _dcfield(default_factory=list)
    category: list = _dcfield(default_factory=list)
    # armor (ArmorId >= 0)
    pdef: "int | None" = None
    peva: "int | None" = None
    mdef: "int | None" = None
    meva: "int | None" = None
    # equip stat bonuses + elemental affinity (Stats.csv via BonusId)
    bonus: dict = _dcfield(default_factory=dict)         # {'Strength': 3, ...}  non-zero only
    affinity: dict = _dcfield(default_factory=dict)      # {'absorb': ['Fire'], 'half': [...]} non-empty only
    # consumable use-effect (EffectId >= 0)
    effect_power: "int | None" = None
    effect_elements: list = _dcfield(default_factory=list)
    effect_status: int = 0
    effect_statuses: list = _dcfield(default_factory=list)   # decoded status names from effect_status

    @property
    def is_weapon(self) -> bool:
        return self.power is not None

    @property
    def is_armor(self) -> bool:
        return self.pdef is not None

    @property
    def is_consumable(self) -> bool:
        """Has an effect row (an EffectId that joined) -- structural. A row can still be empty: use
        :attr:`has_use_effect` to decide whether there is anything worth SHOWING."""
        return self.effect_power is not None

    @property
    def has_use_effect(self) -> bool:
        """True when the use-effect conveys something (non-zero power, an element, or a status) -- so an
        all-zero effect row (e.g. a stat-bonus accessory with a dummy EffectId) shows no use-effect line."""
        return bool(self.effect_power or self.effect_elements or self.effect_statuses)

    def effect_desc(self) -> str:
        """A neutral one-phrase description of the use-effect (``"power 10"`` / ``"status Death"`` /
        ``"power 20, Fire, status Poison"``); empty when :attr:`has_use_effect` is False."""
        parts = []
        if self.effect_power:
            parts.append(f"power {self.effect_power}")
        if self.effect_elements:
            parts.append("/".join(self.effect_elements))
        if self.effect_statuses:
            parts.append("status " + "/".join(self.effect_statuses))
        return ", ".join(parts)


# ---- CSV parsing ----------------------------------------------------------------------------------
def _read_csv(path) -> tuple:
    """Parse a Memoria item CSV: returns ``(name->index, [row-as-list])``. Column names come from the
    file's ``#``-legend line (the first comment line whose fields include ``Id``); data rows are the
    non-``#``-leading lines split on ``;`` (a trailing ``# nnn - Name`` comment cell is left as an extra
    field and ignored by index access). The first data column may itself be a Comment string containing a
    ``#`` (e.g. ``Bonus 0000 # Empty``) -- only a line whose first non-space char is ``#`` is a comment."""
    cols: "dict | None" = None
    rows: list = []
    # utf-8-sig strips a leading BOM if a localized install has one (else a BOM'd first line would fail the
    # `startswith("#")` legend/comment test); splitlines() handles CRLF.
    for raw in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith("#"):
            if cols is None:
                fields = [f.strip() for f in s.lstrip("#").strip().split(";")]
                if "Id" in fields and len(fields) > 1:
                    cols = {name: i for i, name in enumerate(fields)}
            continue
        rows.append([c.strip() for c in raw.split(";")])
    return (cols or {}), rows


def _i(row, cols, name, default=None):
    """Integer cell ``name`` from ``row`` (None/default on a missing column or non-int)."""
    idx = cols.get(name)
    if idx is None or idx >= len(row):
        return default
    try:
        return int(row[idx])
    except (ValueError, TypeError):
        return default


# ---- the in-memory join ---------------------------------------------------------------------------
_CACHE = None   # None = not loaded yet; False = tried + unavailable; dict = {item_id: ItemStat}


def _load(game=None):
    """Read + join the five item CSVs from the install (cached). Returns ``{id: ItemStat}`` or ``None`` if
    the install / a CSV can't be read (cached as unavailable so we don't re-probe the filesystem)."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE or None
    try:
        from .config import find_game_path
        d = find_game_path(game) / "StreamingAssets" / "Data" / "Items"
        icols, irows = _read_csv(d / "Items.csv")
        wcols, wrows = _read_csv(d / "Weapons.csv")
        acols, arows = _read_csv(d / "Armors.csv")
        scols, srows = _read_csv(d / "Stats.csv")
        ecols, erows = _read_csv(d / "ItemEffects.csv")
        if not (icols and irows):
            raise ValueError("Items.csv had no parseable header/rows")
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        _CACHE = False
        return None

    weap = {_i(r, wcols, "Id"): r for r in wrows if _i(r, wcols, "Id") is not None}
    armor = {_i(r, acols, "Id"): r for r in arows if _i(r, acols, "Id") is not None}
    stat = {_i(r, scols, "Id"): r for r in srows if _i(r, scols, "Id") is not None}
    effect = {_i(r, ecols, "Id"): r for r in erows if _i(r, ecols, "Id") is not None}

    out: dict = {}
    for r in irows:
        iid = _i(r, icols, "Id")
        if iid is None or iid == 255:                   # 255 = NoItem (the empty sentinel) -> not a real item
            continue
        try:
            out[iid] = _build(iid, r, icols, weap, wcols, armor, acols, stat, scols, effect, ecols)
        except (ValueError, IndexError, KeyError):
            continue                                    # a malformed row -> skip, don't sink the whole load
    _CACHE = out or False
    return out or None


def _build(iid, r, ic, weap, wc, armor, ac, stat, sc, effect, ec) -> ItemStat:
    st = ItemStat(id=iid, name=_items.name_of(iid) or "")
    st.types = [friendly for col, friendly in TYPE_COLS if _i(r, ic, col, 0)]
    st.price = _i(r, ic, "Price", 0) or 0
    st.sell = _i(r, ic, "SellingPrice", st.price // 2) or 0
    st.equip = [c for c in CHARS if _i(r, ic, c, 0)]
    raw_ab = r[ic["AbilityIds"]] if "AbilityIds" in ic and ic["AbilityIds"] < len(r) else ""
    st.abilities = [t.strip() for t in raw_ab.split(",") if t.strip() and t.strip() != "0"]

    wid = _i(r, ic, "WeaponId", -1)
    if wid is not None and wid >= 0 and wid in weap:
        wr = weap[wid]
        st.power = _i(wr, wc, "Power", 0)
        st.elements = decode_elements(_i(wr, wc, "Elements", 0))
        st.category = decode_category(_i(wr, wc, "Category", 0))

    aid = _i(r, ic, "ArmorId", -1)
    if aid is not None and aid >= 0 and aid in armor:
        ar = armor[aid]
        st.pdef = _i(ar, ac, "P.Def", 0)
        st.peva = _i(ar, ac, "P.Eva", 0)
        st.mdef = _i(ar, ac, "M.Def", 0)
        st.meva = _i(ar, ac, "M.Eva", 0)

    bid = _i(r, ic, "BonusId", -1)
    if bid is not None and bid in stat:
        sr = stat[bid]
        for col, label in (("Dexterity", "Speed"), ("Strength", "Strength"),
                           ("Magic", "Magic"), ("Will", "Spirit")):
            v = _i(sr, sc, col, 0) or 0
            if v:
                st.bonus[label] = v
        for col, label in (("AttackElement", "boosts"), ("GuardElement", "nullify"),
                           ("AbsorbElement", "absorb"), ("HalfElement", "halve"), ("WeakElement", "weak to")):
            els = decode_elements(_i(sr, sc, col, 0))
            if els:
                st.affinity[label] = els

    eid = _i(r, ic, "EffectId", -1)
    if eid is not None and eid >= 0 and eid in effect:
        er = effect[eid]
        st.effect_power = _i(er, ec, "Power", 0)
        st.effect_elements = decode_elements(_i(er, ec, "Element", 0))
        st.effect_status = _i(er, ec, "Status", 0) or 0
        st.effect_statuses = decode_status(st.effect_status)
    return st


# ---- public API -----------------------------------------------------------------------------------
def available(game=None) -> bool:
    """True if the install's item CSVs could be read (so stat enrichment is live)."""
    return _load(game) is not None


def for_id(item_id, *, game=None):
    """The :class:`ItemStat` for an item id, or ``None`` (unknown id, or the install isn't reachable)."""
    table = _load(game)
    if not table:
        return None
    try:
        return table.get(int(item_id))
    except (ValueError, TypeError):
        return None


def summary(item_id, *, game=None):
    """A one-line headline for an item (``"weapon - Atk 12, 320 gil"``), or ``None`` if stats aren't loaded.
    Used for the Info Hub browse row + ``ff9mapkit items``."""
    st = for_id(item_id, game=game)
    if st is None:
        return None
    kind = "/".join(st.types) if st.types else "item"
    bits = []
    if st.is_weapon:
        head = f"Atk {st.power}"
        if st.elements:
            head += " " + "/".join(st.elements)
        bits.append(head)
    if st.is_armor and (st.pdef or st.mdef):
        bits.append(f"Def {st.pdef}/{st.mdef}")
    if st.bonus:
        bits.append(", ".join(f"{k}+{v}" for k, v in st.bonus.items()))
    if st.has_use_effect:
        bits.append("effect " + st.effect_desc())
    if st.price:
        bits.append(f"{st.price} gil")
    return f"{kind} - {', '.join(bits)}" if bits else kind


def facts(item_id, *, game=None) -> list:
    """``[(label, value), ...]`` for the Info Hub item-detail pane. Empty list when stats aren't loaded."""
    st = for_id(item_id, game=game)
    if st is None:
        return []
    out = [("type", "/".join(st.types) if st.types else "item"),
           ("price", f"{st.price} gil (sell {st.sell})")]
    if st.is_weapon:
        out.append(("attack", str(st.power)))
        if st.elements:
            out.append(("element", "/".join(st.elements)))
        if st.category:
            out.append(("weapon class", "/".join(st.category)))
    if st.is_armor and (st.pdef or st.mdef):
        out.append(("defence", f"P.{st.pdef} M.{st.mdef}"))
    if st.is_armor and (st.peva or st.meva):
        out.append(("evade", f"P.{st.peva} M.{st.meva}"))
    if st.bonus:
        out.append(("stat bonus", ", ".join(f"{k}+{v}" for k, v in st.bonus.items())))
    for label, els in st.affinity.items():
        out.append((label, "/".join(els)))
    if st.has_use_effect:
        out.append(("use-effect", st.effect_desc()))
    if st.equip:
        out.append(("equippable by", ", ".join(st.equip)))
    if st.abilities:
        out.append(("teaches", ", ".join(st.abilities)))
    return out


def _reset_cache():
    """Test hook: drop the in-memory cache so a later call re-reads (e.g. after pointing at a fixture)."""
    global _CACHE
    _CACHE = None
