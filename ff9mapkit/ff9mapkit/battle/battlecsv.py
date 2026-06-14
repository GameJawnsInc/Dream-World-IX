"""Read-live battle catalogs -- the externalized CSV side of battle tuning:

  * ``Data/Battle/Actions.csv``    -- the 192 shared PLAYER abilities (id 0-191): scriptId/power/elements/
                                      rate/status/mp + targeting. (Enemy attacks are NOT here -- they live
                                      per-scene in the raw16 atk[] block; see :mod:`scene_codec`.)
  * ``Data/Battle/StatusData.csv`` -- the 33 status definitions (tick/duration).
  * ``Data/Battle/StatusSets.csv`` -- named multi-status bundles an action's ``statusIndex`` points at.

PROVENANCE -- these are Square-Enix game DATA (the very tables the engine loads), so -- exactly like
:mod:`ff9mapkit.itemstats` -- the numbers are read LIVE from YOUR OWN install and nothing is committed.
The ONLY committed battle data here is the **scriptId formula catalog** (:data:`SCRIPT_IDS`), which is
names/ids transcribed from the open-source Memoria ``Memoria.Scripts/Sources/Battle`` filenames -- and a
data-vs-DLL flag (re-pointing an action to an EXISTING scriptId is pure CSV; a NEW formula needs a
``Memoria.Scripts.<Mod>.dll`` rebuild, NOT the engine DLL).

If the install/CSVs aren't reachable every accessor returns ``None``/empty (offline-safe).
"""
from __future__ import annotations

from dataclasses import dataclass, field as _dcfield

# Reuse the single committed element/status name tables (identical bitmask space, EffectElement /
# BattleStatus). encode_* (name -> bit) are added here for the Phase-1 raw16 authoring side.
from ..itemstats import ELEMENTS, STATUSES, decode_elements, decode_status

# ---- scriptId formula catalog (COMMITTED: names/ids from Memoria.Scripts/Sources/Battle/00NN_*.cs) ----
# The number = the battle-calc formula a player action / enemy attack dispatches to (ScriptsLoader's
# BattleBaseScripts[]). These are the EXTERNALIZED Memoria formulas -- re-pointing an action at one of THESE
# is pure CSV. A handful of legacy ids (47, 64, 78, 79, 81, 82) are NOT externalized here yet ARE used by
# shipping enemy attacks (base-engine-handled), so an uncatalogued id is reported neutrally, NOT as "needs a
# DLL" -- only AUTHORING a brand-new formula needs a Memoria.Scripts.<Mod>.dll (not the engine DLL).
SCRIPT_IDS = {
    1: "SimpleWeapon", 2: "WillWeapon", 3: "DexterityWeapon", 4: "MagicWeapon", 5: "RandomWeapon",
    6: "BloodSwordWeapon", 7: "LevelWeapon", 8: "EnemyPhysicalAttack", 9: "MagicAttack",
    10: "MagicRecovery", 11: "MagicApplyNegativeStatus", 12: "MagicCureStatus", 13: "Revive", 14: "Death",
    15: "DrainMp", 16: "DrainHp", 17: "MagicGravityDamage", 18: "Meteorite", 19: "PhysicalAttack",
    20: "OriginalMagicAttack", 21: "GoblinPunch", 22: "LvDirectHPDamage", 23: "LvHoly",
    24: "LvReduceDefence", 25: "PreciseDirectHPDamage", 26: "ThousandNeedles", 27: "DirectHPDamage",
    28: "LimitGlove", 29: "DifferentCasterHpAttack", 30: "WhiteWind", 31: "RandomMpDamage", 32: "Darkside",
    33: "ArmourBreak", 34: "PowerBreak", 35: "MentalBreak", 36: "MagicBreak", 37: "Chakra",
    38: "SpareChange", 39: "Lancer", 40: "DragonBreath", 41: "WhiteDraw", 42: "Throw", 43: "Might",
    44: "Focus", 45: "Sacrifice", 46: "SoulBlade", 48: "Spear", 49: "Phoenix", 50: "SixDragons",
    51: "Curse", 52: "AngelSnack", 53: "LuckySeven", 54: "WhatIsThat", 55: "ChangeRow", 56: "FleeIteration",
    57: "Flee", 58: "Steal", 59: "Scan", 60: "Detect", 61: "Charge", 62: "ItemSoft", 63: "MagicSwordAttack",
    65: "Eat", 66: "FrogDrop", 67: "Thievery", 68: "DragonCrest", 69: "ItemPotion", 70: "ItemEther",
    71: "ItemElixir", 72: "ItemPhoenix", 73: "ItemCureStatus", 74: "ItemGem", 75: "DeadPepper", 76: "Tent",
    77: "DarkMatter", 80: "DoubleCastSpecial", 83: "MassSpear", 84: "Jewel", 85: "Summon", 86: "Atomos",
    87: "Odin", 88: "Melt", 89: "HPSwitching", 90: "HalfDefence", 91: "Cannon", 92: "ItemAdd",
    93: "Maelstrom", 94: "AbsorbMagic", 95: "AbsorbStrength", 96: "TranceFull", 97: "Entice",
    98: "SimpleAttackGaia", 99: "FlareStar", 100: "PreciseEnemyPhysicalAttack", 101: "EnemySteal",
    102: "EnemyMug", 103: "MagicApplyPositiveStatus", 104: "TonberryKarma", 105: "GrandCross",
    106: "Swallow", 107: "PreciseEnemyPhysicalAttackAndChangeRow", 108: "IaiStrike", 109: "Mini",
}


def script_name(script_id) -> str:
    """Formula name for a scriptId, or a neutral ``"scriptId N"`` when it isn't in the externalized catalog
    (which does NOT imply it's unhandled -- a few legacy ids are base-engine-handled; see the table comment)."""
    try:
        sid = int(script_id)
    except (TypeError, ValueError):
        return "scriptId ?"
    return SCRIPT_IDS.get(sid, f"scriptId {sid}")


def is_stock_script(script_id) -> bool:
    """True if this scriptId is in the externalized Memoria.Scripts catalog (freely re-pointable, no DLL)."""
    try:
        return int(script_id) in SCRIPT_IDS
    except (TypeError, ValueError):
        return False


# ---- name <-> bit helpers (committed; the encode side powers Phase-1 raw16 authoring) ------------------
_ELEM_BY_NAME = {name.lower(): bit for bit, name in ELEMENTS}
_STATUS_BY_NAME = {name.lower(): bit for bit, name in STATUSES}


def encode_elements(names) -> int:
    """A list of element names (or a bitmask int) -> the bitmask. Unknown names raise ValueError."""
    if isinstance(names, int):
        return names
    mask = 0
    for n in names or []:
        if isinstance(n, int):
            mask |= n
            continue
        bit = _ELEM_BY_NAME.get(str(n).strip().lower())
        if bit is None:
            raise ValueError(f"unknown element {n!r} (known: {', '.join(nm for _, nm in ELEMENTS)})")
        mask |= bit
    return mask


def encode_status(names) -> int:
    """A list of status names (or a bitmask int) -> the BattleStatus bitmask. Unknown names raise."""
    if isinstance(names, int):
        return names
    mask = 0
    for n in names or []:
        if isinstance(n, int):
            mask |= n
            continue
        bit = _STATUS_BY_NAME.get(str(n).strip().lower())
        if bit is None:
            raise ValueError(f"unknown status {n!r} (known: {', '.join(nm for _, nm in STATUSES)})")
        mask |= bit
    return mask


# ---- TargetType / TargetDisplay (Memoria.Data enums; the Actions.csv cell format is "Name(value)") -------
# Committed open-source enum NAMES (TargetType.cs / TargetDisplay.cs); the value is the enum's int.
TARGET_TYPES = ("SingleAny", "SingleAlly", "SingleEnemy", "ManyAny", "ManyAlly", "ManyEnemy", "All", "AllAlly",
                "AllEnemy", "Random", "RandomAlly", "RandomEnemy", "Everyone", "Self", "Automatic", "Special")
TARGET_DISPLAYS = ("None", "Hp", "Mp", "Debuffs", "Buffs")


def _encode_enum(value, names, label) -> str:
    """A name (case-insensitive) or a 0..N-1 id -> the ``Name(value)`` CSV cell. ValueError on a bad value."""
    if isinstance(value, bool):
        raise ValueError(f"{label} can't be a boolean")
    if isinstance(value, int) or (isinstance(value, str) and value.strip().lstrip("-").isdigit()):
        i = int(value)
    else:
        i = {n.lower(): k for k, n in enumerate(names)}.get(str(value).strip().lower())
        if i is None:
            raise ValueError(f"unknown {label} {value!r} (known: {', '.join(names)})")
    if not 0 <= i < len(names):
        raise ValueError(f"{label} id {i} out of range (0-{len(names) - 1})")
    return f"{names[i]}({i})"


def encode_target_type(value) -> str:
    """A TargetType name (``SingleEnemy``/``AllEnemy``/…) or 0-15 id -> the ``Name(value)`` Actions.csv cell."""
    return _encode_enum(value, TARGET_TYPES, "targets")


def encode_target_display(value) -> str:
    """A TargetDisplay name (``None``/``Hp``/``Mp``/``Debuffs``/``Buffs``) or 0-4 id -> the ``Name(value)`` cell."""
    return _encode_enum(value, TARGET_DISPLAYS, "menu_window")


# StatusData ClearOnApply/ImmunityProvided cells are a ``Name(bitIndex), ...`` list (BattleStatusId, the
# ``#! UnshiftStatuses`` format); the index = the status's bit position (Petrify=0 … GradualPetrify=31).
_STATUS_INDEX_BY_NAME = {nm.lower(): (bm.bit_length() - 1, nm) for bm, nm in STATUSES}


def encode_status_list(value) -> str:
    """A list of status names (or ``None``/``""``/``"none"``) -> the ``Name(idx), Name(idx)`` cell for a
    StatusData BattleStatus column. ValueError on an unknown name."""
    if value is None:
        return ""
    if isinstance(value, str):
        value = [] if value.strip().lower() in ("", "none", "-") else [value]
    out = []
    for n in value or []:
        hit = _STATUS_INDEX_BY_NAME.get(str(n).strip().lower())
        if hit is None:
            raise ValueError(f"unknown status {n!r} (known: {', '.join(nm for _, nm in STATUSES)})")
        out.append(f"{hit[1]}({hit[0]})")
    return ", ".join(out)


# ---- CSV parsing (mirrors itemstats._read_csv; legend keyed on an 'id' column, parens stripped) --------
def _read_csv(path) -> tuple:
    """Parse a Memoria battle CSV -> ``(cols, rows)``. ``cols`` maps each header name (normalized:
    lower-cased, ``Foo(bar)`` -> ``foo``) to its column index, taken from the first ``#``-legend line that
    has an ``id`` field. Data rows are ``;``-split (a trailing ``# name`` comment cell is left as an extra
    field, ignored by name access)."""
    cols: "dict | None" = None
    rows: list = []
    # cp1252 (the install's real encoding -- a few action names carry a 0x92 curly apostrophe; reading them as
    # UTF-8 would mangle the name). Strip a stray UTF-8 BOM if one ever appears.
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    for raw in data.decode("cp1252", errors="replace").splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith("#"):
            if cols is None and not s.startswith("#!"):
                fields = [f.strip().split("(")[0].strip().lower() for f in s.lstrip("#").strip().split(";")]
                if "id" in fields and len(fields) > 1:
                    cols = {name: i for i, name in enumerate(fields)}
            continue
        rows.append([c.strip() for c in raw.split(";")])
    return (cols or {}), rows


def _cell(row, cols, name, default=None):
    idx = cols.get(name)
    if idx is None or idx >= len(row):
        return default
    return row[idx]


def _int(row, cols, name, default=None):
    v = _cell(row, cols, name)
    try:
        return int(v)
    except (ValueError, TypeError):
        return default


def _name_cell(row):
    """The first column (Comment) is the human name; strip a trailing inline ``# ...`` if it leaked in."""
    return (row[0].split("#")[0].strip() if row else "") or ""


# ---- records -----------------------------------------------------------------------------------------
@dataclass
class Action:
    """One Actions.csv row -- a shared player ability (white/black magic, skill, summon, ...)."""
    id: int
    name: str
    script_id: int
    power: int
    elements: list = _dcfield(default_factory=list)     # decoded names
    rate: int = 0
    category: int = 0
    status_index: int = 0                                # -> StatusSets.csv id (resolve via status_set)
    mp: int = 0
    type: int = 0
    targets: str = ""
    menu_window: str = ""

    def summary(self) -> str:
        bits = [script_name(self.script_id)]
        if self.power:
            bits.append(f"pow {self.power}")
        if self.elements:
            bits.append("/".join(self.elements))
        if self.rate not in (0, 255):
            bits.append(f"rate {self.rate}")
        if self.mp:
            bits.append(f"{self.mp} MP")
        return f"{self.name} -- " + ", ".join(bits)


@dataclass
class Status:
    """One StatusData.csv row -- a status ailment/buff definition."""
    id: int
    name: str
    tick: int = 0                                        # OprCount (per-tick effect counter)
    duration: int = 0                                    # ContiCount (0 = permanent until cured)


@dataclass
class StatusSet:
    """One StatusSets.csv row -- a named bundle of statuses an action inflicts/cures."""
    id: int
    name: str
    statuses: list = _dcfield(default_factory=list)      # status names


# ---- the in-memory load (cached) ---------------------------------------------------------------------
_CACHE = None    # None = not loaded; False = unavailable; dict with 'actions'/'statuses'/'sets'


def _battle_dir(game=None):
    from ..config import find_game_path
    return find_game_path(game) / "StreamingAssets" / "Data" / "Battle"


def _parse_status_tokens(field) -> list:
    """``"Silence(3), Blind(4)"`` -> ``["Silence", "Blind"]`` (the name before each paren)."""
    out = []
    for tok in (field or "").split(","):
        tok = tok.strip()
        if not tok:
            continue
        out.append(tok.split("(")[0].strip())
    return out


def _load(game=None):
    global _CACHE
    if _CACHE is not None:
        return _CACHE or None
    try:
        d = _battle_dir(game)
        acols, arows = _read_csv(d / "Actions.csv")
        scols, srows = _read_csv(d / "StatusData.csv")
        tcols, trows = _read_csv(d / "StatusSets.csv")
        if not (acols and arows):
            raise ValueError("Actions.csv had no parseable header/rows")
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        _CACHE = False
        return None

    sets = {}
    for r in trows:
        sid = _int(r, tcols, "id")
        if sid is None:
            continue
        sets[sid] = StatusSet(id=sid, name=_name_cell(r), statuses=_parse_status_tokens(_cell(r, tcols, "statuses")))

    statuses = {}
    for r in srows:
        sid = _int(r, scols, "id")
        if sid is None:
            continue
        statuses[sid] = Status(id=sid, name=_name_cell(r),
                               tick=_int(r, scols, "oprcount", 0) or 0,
                               duration=_int(r, scols, "conticount", 0) or 0)

    actions = {}
    for r in arows:
        aid = _int(r, acols, "id")
        if aid is None:
            continue
        actions[aid] = Action(
            id=aid, name=_name_cell(r),
            script_id=_int(r, acols, "scriptid", 0) or 0,
            power=_int(r, acols, "power", 0) or 0,
            elements=decode_elements(_int(r, acols, "elements", 0) or 0),
            rate=_int(r, acols, "rate", 0) or 0,
            category=_int(r, acols, "category", 0) or 0,
            status_index=_int(r, acols, "statusindex", 0) or 0,
            mp=_int(r, acols, "mp", 0) or 0,
            type=_int(r, acols, "type", 0) or 0,
            targets=_cell(r, acols, "targets", "") or "",
            menu_window=_cell(r, acols, "menuwindow", "") or "")

    _CACHE = {"actions": actions, "statuses": statuses, "sets": sets}
    return _CACHE


# ---- public API --------------------------------------------------------------------------------------
def available(game=None) -> bool:
    return _load(game) is not None


def action(action_id, *, game=None):
    t = _load(game)
    try:
        return t and t["actions"].get(int(action_id))
    except (ValueError, TypeError):
        return None


def actions(*, game=None) -> list:
    t = _load(game)
    return sorted(t["actions"].values(), key=lambda a: a.id) if t else []


def action_by_name(name, *, game=None):
    t = _load(game)
    if not t:
        return None
    key = str(name).strip().lower()
    for a in t["actions"].values():
        if a.name.lower() == key:
            return a
    return None


def status(status_id, *, game=None):
    t = _load(game)
    try:
        return t and t["statuses"].get(int(status_id))
    except (ValueError, TypeError):
        return None


def statuses(*, game=None) -> list:
    t = _load(game)
    return sorted(t["statuses"].values(), key=lambda s: s.id) if t else []


def status_set(set_id, *, game=None):
    t = _load(game)
    try:
        return t and t["sets"].get(int(set_id))
    except (ValueError, TypeError):
        return None


def status_set_names(set_id, *, game=None) -> list:
    """The status names an action's ``statusIndex`` inflicts/cures (empty if unknown/unloaded)."""
    s = status_set(set_id, game=game)
    return list(s.statuses) if s else []


def _reset_cache():
    """Test hook -- drop the cache so a later call re-reads (e.g. after pointing at a fixture)."""
    global _CACHE
    _CACHE = None
