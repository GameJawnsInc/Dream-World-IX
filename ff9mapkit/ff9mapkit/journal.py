"""FF9 100%-completion JOURNAL -- read every completion counter a save actually stores (offline, read-only).

The game keeps "how complete am I" state in FIVE stores, and only some of them are reachable from a save
file. This module is the kit's map of that split -- one declarative row table (:data:`ROWS`), one resolver
(:func:`build_report`), and renderers. It never writes: a journal read must be safe against the owner's
live container while ~18 worktrees share one install.

  1. ``EventState.gEventGlobal`` -- the 2048-byte story heap (``EventState.cs:10``). Chocographs, beak
     level, Stellazzio, ragtime, coin toss, the Mognet mailbox, treasure-hunter points. FULLY READABLE:
     it is in the encrypted main block AND (load-authoritatively) in the Memoria extra sidecar.
  2. ``40000_Common`` in the Memoria extra -- gil, key items, per-character AP, frogs, thefts, escapes,
     battles, the 8 kill categories, ``kills_per_model`` (``JsonParser.cs:918-1010``). READABLE when the
     slot has an extra file; a VANILLA slot falls back to the encrypted main block for gil + key items.
  3. ``30000_MiniGame`` in the extra -- the whole Tetra Master deck (``JsonParser.cs:690-737``), which
     makes ``QuadMistDatabase.MiniGame_GetPlayerPoints`` / ``MiniGame_GetCollectorLevel`` exactly
     reproducible offline.
  4. ``20000_Event`` / ``95000_Setting`` -- ``gStepCount`` and the play-time Double.
  5. ``AchievementState`` (save node ``80000_Achievement``) -- ATEs seen, synthesis count, auction count,
     Stiltzkin purchases, the ever-learned ability/passive HashSets, the Quadmist win list. **NOT
     READABLE HERE.** It is a main-block-only fixed-size sentinel-padded stream and mapping its offsets is
     its own round-trip-gated pass. Every row it owns SHIPS ANYWAY, as ``status="untracked"`` with a
     ``blocked_by`` naming the exact obstacle -- a completion journal that silently drops what it cannot
     see is worse than one that names the hole.

THE FOUR TRAPS this module exists to not repeat (each cost a wrong-looking-right number elsewhere):

  * **The chocograph Int24 SIGN-EXTENDS.** ``EBin.GetVariableValueInternal`` casts the third byte to
    ``SByte`` (``EBin.cs:1858-1861``), so a completed field reads ``-1``; the engine masks it on the next
    use (``EMinigame.cs:436``). Always ``& 0xFFFFFF`` before popcounting.
  * **The treasure-hunter x2 band OVERLAPS the chocograph "opened" Int24.** ``TH_POINT_RANGES``' weight-2
    band is bytes 182-186 (``EventState.cs:69``) and chocograph-opened is bytes 184-186
    (``ChocographUI.cs:251``) -- the SAME bytes. 24 dug chocographs are already 48 treasure-hunter points.
    The two rows are not independent progress; the notes say so.
  * **"Stiltzkin" is two different counters.** ``gEventGlobal[1033]`` is the moogle fields' own tally
    (``content/mognet.py:86``, kit-decoded, no engine C# reader). The ``AllStiltzkinItem`` Target of 8
    scores ``AchievementState.StiltzkinBuy``, incremented only on one of eight exact gil prices
    (``EMinigame.cs:50-52``) and stored main-block-only. Hanging ``/8`` on byte 1033 would ship a
    plausible, checkable, WRONG number. Same class: ``party.abilities_mastered`` (party state) is not
    what ``AllAbility``=183 scores (the ever-learned HashSet).
  * **Names resolve at RUNTIME, never baked.** The owner stacks Moguri, so key-item ids/names can differ
    from stock. ``keyitems`` reads them live from the install and degrades to ``None``; the key-item
    DENOMINATOR comes from that same live table, never a constant.

Addressing (engine ``EBin.GetVariableValueInternal``, ``EBin.cs:1847-1876``): a **Bit** index N -> byte
``N>>3`` bit ``N&7``; a **Byte/Int16/UInt16/Int24** index is a raw BYTE offset. So "bit 184" and "byte
184" are different locations -- every row below says which it means.

Deliberately NOT touched: :mod:`ff9mapkit.flags` (its ``FieldEntrance`` is declared signed while the
engine reads it unsigned -- see ``meta.field_entrance``; fixing that is a separate blast radius through
``workspace/savedoc.py``), :mod:`ff9mapkit.save`'s edit surface, and any write path in
:mod:`ff9mapkit.save_items`.
"""
from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass, field

from . import flags as _flags
from . import save as _save
from . import sjbinary as _sj

# ============================ engine constants (TRANSCRIBED, not queried) ============================
# `AchievementManager.Data = GetData()` (AchievementManager.cs:2374) throws unless SharedDataBytesStorage
# is initialised, so these AchievementInfo.Target values are copied here as a compile-time table with their
# file:line. Every one re-read from `Assets/SiliconSocial/AchievementManager.cs` DataWorld (the dict starts
# at :1384); DataJapanese (:394) carries IDENTICAL Targets for all 87 keys, so the numbers are
# region-independent. test_journal.py pins this table against an accidental edit.
ENGINE_TARGETS = {
    "Defeat10000": (10000, "AchievementManager.cs:1490"),      # total kills
    "AllStiltzkinItem": (8, "AchievementManager.cs:1502"),     # AchievementState.StiltzkinBuy -- NOT byte 1033
    "AllPasssiveAbility": (63, "AchievementManager.cs:1514"),  # engine's own spelling; == MAX_PASSIVE_ABILITIES
    "AllAbility": (183, "AchievementManager.cs:1526"),         # AchievementState.abilities (ever learned)
    "ChocoboLv99": (99, "AchievementManager.cs:1560"),         # Choco's BEAK level, gEventGlobal byte 139
    "AllSandyBeach": (21, "AchievementManager.cs:1572"),       # == EMinigame.numOfSandyBeach (:763)
    "AllTreasure": (24, "AchievementManager.cs:1584"),         # == EMinigame.numOfTreasures (:762) == HintMapMax
    "Frog99": (99, "AchievementManager.cs:1618"),              # 40000_Common/frog_no
    "QueenReward10": (10, "AchievementManager.cs:1708"),       # the Stellazzio REWARD threshold, NOT the coin count
    "CardWinAll": (235, "AchievementManager.cs:1910"),         # OPPONENTS defeated, NOT card kinds
    "Steal50": (50, "AchievementManager.cs:1945"),             # 40000_Common/steal_no
    "ATE80": (79, "AchievementManager.cs:2169"),               # 79 of 83 ATE slots (a mutually exclusive pair)
    "Moonstone4": (4, "AchievementManager.cs:2181"),           # (recorded for the record; no row reads it yet)
}

# --- gEventGlobal offsets. BYTE offsets unless the name says BIT. Each carries its engine reader. ---
SCENARIO_OFF = 0            # UInt16, EventState.cs:18   -- `gEventGlobal[1] << 8 | gEventGlobal[0]`, UNSIGNED
FIELD_ENTRANCE_OFF = 2      # UInt16, EventState.cs:28   -- also UNSIGNED (flags.py:171 declares it signed)
BEAK_LEVEL_OFF = 139        # Byte,   EMinigame.cs:282   -- Choco's dig STRENGTH (capped 99)
CHOCOGRAPH_OPENED_OFF = 184  # Int24,  ChocographUI.cs:251 -- `hasGem`; OVERLAPS the TH x2 band (182-186)
CHOCOGRAPH_FOUND_OFF = 187  # Int24,  ChocographUI.cs:250 -- `hasMap`
DIG_ABILITY_OFF = 191       # Byte,   ChocographUI.cs:245 -- Choco's terrain ability (5 = every terrain)
RAGTIME_OFF = 198           # Byte,   BattleAchievement.cs:41-42 -- successes in bits 3..7
HUNT_WINNER_OFF = 313       # Byte,   EMinigame.cs:302   -- Festival of the Hunt winner (2 == Vivi)
STELLAZZIO_OFF = 355        # UInt16, EMinigame.cs:179   -- one bit per coin, low 13 bits
COIN_TOSS_OFF = 369         # Byte,   EMinigame.cs:335   -- coins thrown at the Treno fountain

SANDY_BEACH_BIT = 856       # BIT base, EMinigame.cs:478-480 -- 21 consecutive bits, one per beach
CHOCOBO_PARADISE_BIT = 814  # BIT, WorldConfiguration.cs:183 -- `ff9.byte_gEventGlobal(101) & 0x40`
MOGNET_CENTRAL_BIT = 815    # BIT, WorldConfiguration.cs:189 -- `ff9.byte_gEventGlobal(101) & 0x80`
YAN_BLESSING_BIT = 1584     # BIT, BattleAchievement.cs:50-51

# The Mognet mailbox (content/mognet.py:84-89 -- kit-decoded from fields 300/407/1102, live-save verified).
MOGNET_DELIVERED_OFF = 1032   # Byte -- lifetime letters DELIVERED
MOGNET_STILTZKIN_OFF = 1033   # Byte -- the moogle fields' Stiltzkin tally. NOT AchievementState.StiltzkinBuy.
MOGNET_SLOT_BASE = 1034       # Byte -- slot k at +4k: +0 occupied, +1 variant, +2 from, +3 to
MOGNET_SLOTS = 3
MOGNET_GIVE_LO, MOGNET_GIVE_HI = 8376, 8439   # BIT range, flags.py:274-279 -- give-side variant one-shot locks
MOGNET_READ_LO, MOGNET_READ_HI = 8440, 8503   # BIT range, flags.py:280-283 -- read-side locks

# --- engine denominators that are NOT AchievementInfo targets ---
CHOCOGRAPH_MAX = 24         # ChocographUI.HintMapMax (:428); == AllTreasure target; == EMinigame.numOfTreasures
STELLAZZIO_MAX = 13         # the loop bound at EMinigame.cs:181 (NOT QueenReward10=10, the reward threshold)
RAGTIME_MAX = 16            # BattleAchievement.cs:43 -- `successCount * 100 / 16`
COIN_TOSS_MAX = 51          # EMinigame.ThiefNPCCoinCondition (:755)
DIG_ABILITY_MAX = 5         # INFERRED: the terminal value AllTreasureCheating (:454) / AllSandyBeachCheating (:493)
                            # write. Not a declared max anywhere -- hence provenance "engine-inferred".
GIL_CAP = 9_999_999         # BattleCalculator.cs:61 -- `party.gil = Math.Min(9999999U, value)`
CARD_KINDS_MAX = 100        # CardPool.TOTAL_CARDS (:102); TetraMasterCardId ids 0-99, NONE=255 excluded
COLLECTOR_POINTS_MAX = 1700  # the top threshold of the collector ladder (QuadMistDatabase.cs:236)
COLLECTOR_LEVEL_MAX = 31    # FF9SAVE_MINIGAME.CollectorLevelMax(32) - 1 (QuadMistDatabase.cs:243)
ACHIEVEMENT_KEYS_NORMAL = 85  # 87 real keys (AcheivementKey.cs ordinals 0-86 + the AchievementKeyCount
                            # sentinel at :94) minus the 2 system-held (AchievementState.IsSystemAchievement,
                            # :77-80: CompleteGame, Blackjack)
ATE_SEEN_MAX = 79           # EMinigame.cs:521-524 counts ateCheck[i]==1 for i<83 skipping 6/7/14 -> 79 max

# Treasure-Hunter rank ladder. It exists in STOCK only as a COMMENT (EventState.cs:55-63) -- there is no
# executable copy in the shipping engine; the only one that runs is our patched Ff9mkDebugMenu.cs. Hence
# provenance "engine-comment": the numbers are the engine's, the LADDER is not code the game runs.
TH_RANKS = ("H", "G", "F", "E", "D", "C", "B", "A", "S")
TH_RANK_MIN = (0, 200, 220, 240, 260, 280, 300, 320, 340)

# QuadMistDatabase.MiniGame_GetPlayerPoints (:186) -- `Byte[] typePtsWorth = { 0, 0, 1, 2 }`, indexed by
# QuadMistCard.Type (PHYSICAL/MAGIC/FLEXIABLE/ASSAULT).
CARD_TYPE_POINTS = (0, 0, 1, 2)
# QuadMistDatabase.MiniGame_GetCollectorLevel (:204-238) -- the 32-entry Int16 threshold table, verbatim.
COLLECTOR_THRESHOLDS = (0, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1250, 1300, 1320, 1330,
                        1340, 1350, 1360, 1370, 1380, 1390, 1400, 1420, 1470, 1510, 1550, 1600, 1650,
                        1680, 1690, 1698, 1700)

# The 8 kill categories in `40000_Common` (JsonParser.cs:936-943, `data.categoryKillCount[0..7]`).
KILL_CATEGORIES = ("humanoid_no", "beast_no", "devil_no", "dragon_no", "undead_no", "stone_no",
                   "soul_no", "flight_no")


# ============================ the schema ============================
CATEGORIES = ("story", "treasure", "chocobo", "minigame", "mognet", "party", "combat", "meta")

PROVENANCE = (
    "engine-read",       # value AND denominator are engine code we replicate byte-for-byte
    "engine-derived",    # value is engine code; the denominator is an AchievementInfo.Target
    "engine-inferred",   # denominator inferred from engine BEHAVIOUR, not declared anywhere (tier b)
    "engine-comment",    # the threshold ladder exists only in an engine COMMENT
    "kit-decoded",       # decoded by the kit's 676-field census, not engine-named
    "live-install",      # denominator and/or names read from the user's install at RUNTIME
    "kit-derived",       # computed by us over other rows
    "none",              # untracked / dead -- there is nothing to have provenance FOR
)

STATUSES = (
    "tracked",       # a real number this save produced
    "unavailable",   # trackable in principle, but THIS save lacks the store (no Memoria extra, ...)
    "untracked",     # not representable from a save at ANY tier -- LABELLED, never omitted
    "dead",          # the engine declares AND saves the counter but never increments it
    # RESOLVE-TIME ONLY -- a RowSpec may never DECLARE it (lint_rows refuses that). The reader
    # RAISED. Kept distinct from `unavailable` because collapsing the two makes "our code is
    # broken" indistinguishable from "this save has no such store", and only one of those is a
    # bug we own. The exception text rides on the row (`JournalRow.error`) and the renderer
    # shows it, so a broken reader is LOUD instead of a silently missing line.
    "error",
)
#: statuses a :class:`RowSpec` is allowed to declare STATICALLY.
DECLARABLE_STATUSES = tuple(s for s in STATUSES if s not in ("unavailable", "error"))

STORES = ("geg", "extra", "main", "derived", "none")


@dataclass(frozen=True)
class RowSpec:
    """One journal row's DEFINITION.

    ``id`` is a PERMANENT CONTRACT: ``journal rows --json`` is the seed a later ``journal_catalog.toml``
    and a later in-game screen both consume, so ids are never renamed and never renumbered.
    """
    id: str
    category: str                    # in CATEGORIES
    label: str                       # English fallback label; a catalog/localization may override it.
                                     # NOT a name table -- see `name_source`.
    denom: "int | None"              # engine-native denominator, or None when no engine max exists
    denom_source: str                # file:line the denominator came from ("" iff denom is None)
    source: str                      # file:line of the READ ("" only for kit-derived rows)
    provenance: str                  # in PROVENANCE
    status: str                      # in STATUSES -- the STATIC status; a read may downgrade to "unavailable"
    store: str                       # in STORES
    read: "object | None" = None     # (JournalState) -> Read | None. Dropped on export (never serialized).
    note: str = ""
    exclusive_group: "str | None" = None   # rows a single playthrough cannot all complete
    run_mode: "str | None" = None          # only reachable under a run constraint (ExcaliburII, ...)
    name_source: "str | None" = None       # the LIVE table this row's display names come from. THE LAW:
                                           # names resolve at RUNTIME from the install, NEVER baked -- a
                                           # correct number under a wrong label is the hardest defect class
                                           # to notice (the owner stacks Moguri).
    blocked_by: "str | None" = None        # required iff status == "untracked": WHY, and what unblocks it

    # --- the IN-GAME renderer's half (T1b). Populated from :data:`EB_EXPRESSIONS` / :data:`EB_ABSENT`
    # by :func:`_attach_eb` at import; a row that appears in NEITHER table keeps both None and
    # `lint_rows` REFUSES it. See the block comment above EB_EXPRESSIONS for why the decisions live
    # in a table instead of 48 more keyword arguments.
    eb: "str | None" = None          # the .eb RPN token string WITHOUT the B_EXPR_END terminator -- the
                                     # emitter appends 0x7F, the same contract behavior.hud_expr_tokens
                                     # already enforces (content/behavior.py:762-764). Same spelling as
                                     # the proven `expr:` hud lane minus the prefix.
    eb_source: str = ""              # file:line of the ENGINE read the expression replicates. Required
                                     # iff `eb` is set, and often DIFFERENT from `source`: the offline
                                     # reader walks JsonParser/EventState, the .eb walks
                                     # EBin/GetSysvar. Two access paths, two citations.
    eb_absent: "str | None" = None   # required iff `eb` is None: WHY there is no in-game read.
    eb_scale: int = 1                # THE UNIT LAW. `eb` publishes `read(save).value // eb_scale`. 1 --
                                     # the default and the rule -- means the two renderers publish the
                                     # SAME integer, which is the whole one-catalog bet; anything else
                                     # is a DECLARED unit change that lint_rows forces you to name and
                                     # that tests/test_journal.py cross-checks numerically. Populated
                                     # from :data:`EB_SCALE` by :func:`_attach_eb`.
    eb_unit: str = ""                # the unit suffix the in-game page renders after the value ("h").
                                     # Required iff eb_scale != 1, refused otherwise. journalfield
                                     # renders it FROM HERE, so a scaled value cannot print bare.


@dataclass(frozen=True)
class Read:
    """What a row's reader returns: the value plus optional presentation extras. ``None`` from a reader
    means "this save does not carry the store" -> the row downgrades to ``unavailable``."""
    value: int
    detail: str = ""                 # human extras ("rank C", "Vivi", "W/L/D 3/9/1") -- never a parsed number
    names: tuple = ()                # RUNTIME-resolved display names; () if the install is unreachable
    denominator: "int | None" = None  # a LIVE denominator (key items); None keeps the RowSpec's


@dataclass
class JournalRow:
    """One row RESOLVED against one save. Pure data -- JSON/TOML serializable, no callables, no Qt. This
    is what a later in-game screen and a later catalog generator both eat."""
    id: str
    category: str
    label: str
    value: "int | None"              # None iff status != "tracked"
    denominator: "int | None"
    provenance: str
    status: str
    source: str
    detail: str = ""
    names: list = field(default_factory=list)
    note: str = ""
    exclusive_group: "str | None" = None
    run_mode: "str | None" = None
    blocked_by: "str | None" = None
    error: "str | None" = None       # set iff status == "error": the reader's exception, verbatim

    @property
    def complete(self) -> bool:
        return (self.status == "tracked" and self.denominator is not None
                and self.value is not None and self.value >= self.denominator)

    @property
    def pct(self):
        """Percent complete, or None when no denominator exists -- a bar MUST NOT be drawn for None."""
        if self.status != "tracked" or self.denominator in (None, 0) or self.value is None:
            return None
        return 100.0 * min(self.value, self.denominator) / self.denominator


@dataclass
class JournalState:
    """Everything one save SLOT offers a journal read, already located. Built by :func:`load_state`."""
    label: str
    geg: bytes                       # the 2048-byte gEventGlobal (zero-padded if the source was short)
    geg_source: str = "loose"        # "extra" | "main" | "loose"
    common: object = None            # 40000_Common  SJClass (Memoria extra only)
    minigame: object = None          # 30000_MiniGame
    event: object = None             # 20000_Event
    setting: object = None           # 95000_Setting
    main_pt: object = None           # the decrypted main block (vanilla fallback: gil + key items)


@dataclass
class JournalReport:
    label: str
    rows: list = field(default_factory=list)      # list[JournalRow], in ROWS order

    @property
    def broken(self) -> list:
        """Rows whose READER RAISED. Never silently empty: :func:`render_report` banners these and
        ``ff9mapkit journal report`` exits non-zero, because a broken reader is OUR bug, not the
        save's, and it must not read as "this save has no such store"."""
        return [r for r in self.rows if r.status == "error"]

    def by_id(self, rid):
        for r in self.rows:
            if r.id == rid:
                return r
        return None

    def by_category(self) -> dict:
        out: dict = {}
        for r in self.rows:
            out.setdefault(r.category, []).append(r)
        return out


@dataclass
class JournalDiff:
    label_a: str
    label_b: str
    changed: list = field(default_factory=list)   # [(JournalRow_a, JournalRow_b)] -- only rows that MOVED

    @property
    def empty(self) -> bool:
        return not self.changed


# ============================ primitive reads ============================
def _u8(geg, off) -> int:
    """A Byte at a raw byte offset (EBin.cs:1866-1868)."""
    return geg[off]


def _u16(geg, off) -> int:
    """A UInt16 at a raw byte offset (EBin.cs:1873-1875) -- little-endian, UNSIGNED."""
    return geg[off] | geg[off + 1] << 8


def _i24s(geg, off) -> int:
    """An Int24 EXACTLY as the engine reads it (EBin.cs:1858-1861): the third byte is cast to SByte, so a
    fully-set field returns -1, not 16777215. Mask with 0xFFFFFF before using it as a bitfield -- the
    engine itself does (EMinigame.cs:436)."""
    b2 = geg[off + 2]
    return geg[off] | geg[off + 1] << 8 | ((b2 - 256 if b2 > 127 else b2) << 16)


def _u24(geg, off) -> int:
    """The masked Int24 bitfield -- ``getVarManually(Int24, off) & 0xFFFFFF`` (EMinigame.cs:435-436)."""
    return _i24s(geg, off) & 0xFFFFFF


def _bit(geg, n) -> int:
    """A Bit at BIT index n: byte ``n>>3``, bit ``n&7`` (EBin.cs:1853-1855)."""
    return geg[n >> 3] >> (n & 7) & 1


def _pc(v: int) -> int:
    return bin(v).count("1")


def _num(node, default=None):
    """An SJ leaf -> int, tolerating the VALUE(string) tag SimpleJSON re-infers from (sjbinary docstring)."""
    if node is None:
        return default
    v = getattr(node, "value", node)
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (int, float)):
        return int(v)
    try:
        return int(float(str(v).strip()))
    except (TypeError, ValueError):
        return default


def _fnum(node, default=None):
    """An SJ leaf -> float (the 95000_Setting play-time Double, JsonParser.cs:78)."""
    if node is None:
        return default
    v = getattr(node, "value", node)
    if isinstance(v, bool):
        return float(v)
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return default


def _leaf(node, *path, default=None):
    return _num(_sj.get_path(node, *path), default) if node is not None else default


def treasure_hunter_points(geg) -> int:
    """``EventState.GetTreasureHunterPoints`` (EventState.cs:64-70), replicated over the kit's own copy of
    the scored ranges (``flags.TH_POINT_RANGES``, flags.py:421 -- the same three (lo, hi, weight) triples).
    NB the weight-2 band (bytes 182-186) OVERLAPS the chocograph-opened Int24 (bytes 184-186)."""
    return sum(w * _pc(geg[b]) for lo, hi, w in _flags.TH_POINT_RANGES for b in range(lo, hi + 1))


def treasure_hunter_rank(points: int) -> "tuple[int, str]":
    """``(rank_index 0-8, letter)`` from the ladder in EventState.cs:55-63 (a COMMENT in stock)."""
    idx = 0
    for i, lo in enumerate(TH_RANK_MIN):
        if points >= lo:
            idx = i
    return idx, TH_RANKS[idx]


def deck_cards(minigame) -> list:
    """``[(id, type, arrow), ...]`` from ``30000_MiniGame/MiniGameCard``, filtered EXACTLY as the engine's
    loader does (JsonParser.cs:650-654): an entry whose id is ``TetraMasterCardId.NONE`` (255) or
    ``>= CardPool.TOTAL_CARDS`` (100, CardPool.cs:102) is DISCARDED and never reaches
    ``FF9StateSystem.MiniGame.SavedData.MiniGameCard``. Reproducing that filter is what makes the point /
    collector-level replication exact -- an old-format save's 100-entry array is mostly 255-padding."""
    arr = _sj.get_path(minigame, "MiniGameCard") if minigame is not None else None
    out = []
    if not isinstance(arr, _sj.SJArray):
        return out
    for e in arr:
        cid = _leaf(e, "id")
        if cid is None or cid == 255 or cid >= CARD_KINDS_MAX:
            continue
        out.append((cid, _leaf(e, "type", default=0), _leaf(e, "arrow", default=0)))
    return out


def collector_points(cards) -> int:
    """``QuadMistDatabase.MiniGame_GetPlayerPoints`` (:185-199) verbatim: 10 per distinct card KIND, plus
    ``typePtsWorth[type]`` per card, plus 5 per distinct ARROW pattern."""
    kinds = {c[0] for c in cards}
    arrows = {c[2] for c in cards}
    type_pts = sum(CARD_TYPE_POINTS[c[1]] for c in cards if 0 <= c[1] < len(CARD_TYPE_POINTS))
    return len(kinds) * 10 + type_pts + 5 * len(arrows)


def collector_level(points: int) -> int:
    """``QuadMistDatabase.MiniGame_GetCollectorLevel`` (:202-244) verbatim over :data:`COLLECTOR_THRESHOLDS`:
    the first threshold index i (1..31) with ``points < thresholds[i]`` returns ``i-1``; else 31."""
    for i in range(1, len(COLLECTOR_THRESHOLDS)):
        if points < COLLECTOR_THRESHOLDS[i]:
            return i - 1
    return COLLECTOR_LEVEL_MAX


def _hms(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 3600}h{s % 3600 // 60:02d}m"


# ============================ per-row readers ============================
# One small pure function per row, taking a JournalState. Returning None means "this save has no such
# store" -> the row downgrades to `unavailable` (never to a fabricated 0).

def _r_scenario(st):
    # EventState.cs:16-24 -- `gEventGlobal[1] << 8 | gEventGlobal[0]`, an UNSIGNED master story value.
    sc = _u16(st.geg, SCENARIO_OFF)
    ms = _flags.nearest_milestone(sc)
    return Read(sc, f"{ms[1]} (>= {ms[0]})" if ms else "(before the first milestone)")


def _story_ladder():
    """The walkthrough spine's next-objective ladder -- loaded ONCE from the entry catalog
    (journalcatalog.main_story_ladder), which is the single source the in-game [TBLE] table and
    expression are also generated from. Cached because ROWS readers run per report row."""
    global _STORY_LADDER
    if _STORY_LADDER is None:
        from . import journalcatalog as _jc
        _STORY_LADDER = _jc.main_story_ladder()
    return _STORY_LADDER


_STORY_LADDER = None


def _r_next_objective(st):
    # The SAME bucket the in-game expression computes: sum(SC >= enter) over the spine's main
    # sections EXCLUDING the first, so a fresh save (SC below the first anchor) reads row 0.
    sc = _u16(st.geg, SCENARIO_OFF)
    enters, rows = _story_ladder()
    idx = sum(1 for t in enters[1:] if sc >= t)
    return Read(idx, rows[idx])


def _r_th_points(st):
    return Read(treasure_hunter_points(st.geg))


def _r_th_rank(st):
    idx, letter = treasure_hunter_rank(treasure_hunter_points(st.geg))
    return Read(idx, f"rank {letter}")


def _r_chocographs_found(st):
    # ChocographUI.cs:250 -- `chocographFound |= gEventGlobal[187 + i] << i*8`, then one `hasMap` bit each.
    return Read(_pc(_u24(st.geg, CHOCOGRAPH_FOUND_OFF)))


def _r_chocographs_dug(st):
    # ChocographUI.cs:251 -- the `chocographOpened` / `hasGem` Int24 at bytes 184-186.
    return Read(_pc(_u24(st.geg, CHOCOGRAPH_OPENED_OFF)))


def _r_beak_level(st):
    # EMinigame.cs:282 -- `getVarManually(Global, Byte, 139)` reported against ChocoboLv99 (target 99).
    return Read(_u8(st.geg, BEAK_LEVEL_OFF))


def _r_dig_ability(st):
    # ChocographUI.cs:245 -- `this.ability = gEventGlobal[191]` (also ItemUI.cs:48's vegetable gate).
    return Read(_u8(st.geg, DIG_ABILITY_OFF))


def _r_beaches(st):
    # EMinigame.CountVisitedSandyBeach (:474-483) -- 21 STATIC Bit reads at 856+i. There is no computed
    # bit index for gEventGlobal (EBin.cs:1853-1855 indexes a constant), so the unrolled loop IS the engine.
    return Read(sum(_bit(st.geg, SANDY_BEACH_BIT + i) for i in range(ENGINE_TARGETS["AllSandyBeach"][0])))


def _r_stellazzio(st):
    # EMinigame.cs:179-185 -- a UInt16 at byte 355, one bit per coin, counted over the low 13 bits.
    return Read(_pc(_u16(st.geg, STELLAZZIO_OFF) & ((1 << STELLAZZIO_MAX) - 1)))


def _r_ragtime(st):
    # BattleAchievement.cs:41-43 -- `genVar >> 3 & 31`; the percentage divides by 16, so 16 is the max.
    return Read((_u8(st.geg, RAGTIME_OFF) >> 3) & 31)


_HUNT_WINNERS = {1: "Zidane", 2: "Vivi", 3: "Freya"}   # EMinigame.cs:302-304 tests `== 2` for Vivi


def _r_hunt_winner(st):
    # EMinigame.ViviWinHuntAchievement (:299-306) -- Byte 313 read at Lindblum Castle/Royal Chamber (600).
    v = _u8(st.geg, HUNT_WINNER_OFF)
    return Read(v, _HUNT_WINNERS.get(v, "(undecided)"))


def _r_coin_toss(st):
    # EMinigame.SetGroupingOpponentId (:333-339) -- Byte 369 vs ThiefNPCCoinCondition (51, :755).
    return Read(_u8(st.geg, COIN_TOSS_OFF))


def _r_frogs(st):
    # 40000_Common/frog_no = `data.Frogs.Number` (JsonParser.cs:928); scored against Frog99 (target 99).
    v = _leaf(st.common, "frog_no")
    return None if v is None else Read(v)


def _r_cards_held(st):
    # QuadMistDatabase.MiniGame_GetAllCardCount (:119-122) -- the deck's length.
    if st.minigame is None:
        return None
    return Read(len(deck_cards(st.minigame)))


def _r_card_kinds(st):
    # QuadMistDatabase.MiniGame_GetCardKindCount (:111-117) -- distinct TetraMasterCardId in the deck.
    if st.minigame is None:
        return None
    return Read(len({c[0] for c in deck_cards(st.minigame)}))


def _r_collector_points(st):
    if st.minigame is None:
        return None
    cards = deck_cards(st.minigame)
    return Read(collector_points(cards),
                f"{len({c[0] for c in cards})} kinds, {len({c[2] for c in cards})} arrow patterns")


def _r_collector_level(st):
    if st.minigame is None:
        return None
    pts = collector_points(deck_cards(st.minigame))
    return Read(collector_level(pts), f"{pts} pts")


def _r_card_record(st):
    # JsonParser.cs:693-695 -- sWin/sLose/sDraw (FF9SAVE_MINIGAME:10-12).
    if st.minigame is None:
        return None
    w = _leaf(st.minigame, "sWin", default=0)
    return Read(w, f"W/L/D {w}/{_leaf(st.minigame, 'sLose', default=0)}/{_leaf(st.minigame, 'sDraw', default=0)}")


def _r_mognet_delivered(st):
    # content/mognet.py:85 DELIVERED_IDX -- the lifetime delivered counter (kit-decoded; live-save verified).
    return Read(_u8(st.geg, MOGNET_DELIVERED_OFF))


def _r_mognet_stiltzkin(st):
    # content/mognet.py:86 STILTZKIN_IDX -- the moogle fields' OWN tally. NOT AchievementState.StiltzkinBuy
    # (EMinigame.cs:50-52), so NO /8 denominator hangs here. See mognet.stiltzkin_purchases.
    return Read(_u8(st.geg, MOGNET_STILTZKIN_OFF))


def _r_mognet_carrying(st):
    # content/mognet.py:87-89 -- slot k at 1034+4k, byte +0 = occupied.
    return Read(sum(1 for k in range(MOGNET_SLOTS) if _u8(st.geg, MOGNET_SLOT_BASE + 4 * k) != 0))


def _r_mognet_give_locks(st):
    # flags.py:274-279 -- one bit per letter VARIANT (anchor 8383), not per letter.
    return Read(sum(_bit(st.geg, b) for b in range(MOGNET_GIVE_LO, MOGNET_GIVE_HI + 1)))


def _r_mognet_read_locks(st):
    # flags.py:280-283 -- the read-side twin (anchor 8447).
    return Read(sum(_bit(st.geg, b) for b in range(MOGNET_READ_LO, MOGNET_READ_HI + 1)))


def _r_mognet_central(st):
    # WorldConfiguration.cs:188-189 -- `(ff9.byte_gEventGlobal(101) & 0x80) != 0` == bit 815.
    return Read(_bit(st.geg, MOGNET_CENTRAL_BIT))


def _r_chocobo_paradise(st):
    # WorldConfiguration.cs:182-183 -- `& 0x40` == bit 814.
    return Read(_bit(st.geg, CHOCOBO_PARADISE_BIT))


def _r_yan_blessing(st):
    # BattleAchievement.cs:50-52 -- Bit 1584, checked on the Yan battle maps 920/921.
    return Read(_bit(st.geg, YAN_BLESSING_BIT))


def _r_gil(st):
    # 40000_Common/gil (JsonParser.cs:927); a VANILLA slot falls back to the encrypted main block's
    # UInt32 at save_items.MAIN_GIL_OFF (:90). Clamp source: BattleCalculator.cs:61.
    v = _leaf(st.common, "gil")
    if v is None and st.main_pt is not None:
        from .save_items import read_main_gil
        v = read_main_gil(st.main_pt)
    return None if v is None else Read(v, "" if st.common is not None else "(vanilla main block)")


def _r_key_items(st):
    """Obtained key/important items, with the denominator + names resolved LIVE from the install.

    Extra: ``40000_Common/rareItemsEx`` is SPARSE (JsonParser.cs:995-1006 emits only ids in
    ``rare_item_obtained`` UNION ``rare_item_used``), so an absent id means "never seen" -- the array
    length is NOT a denominator. Vanilla: the main block's 64-byte 2-bit field at
    ``save_items.MAIN_RAREITEMS_OFF`` (:105). Either way the denominator comes from
    ``keyitems.all_keyitems()`` (live ``<install>/StreamingAssets/Text/<lang>/KeyItems.strings``) and is
    None when the install is unreachable -- never a baked constant.
    """
    from . import keyitems as _keyitems
    from .save_items import read_keyitems, read_main_keyitems
    rows = None
    if st.common is not None:
        rows = read_keyitems(st.common)
    elif st.main_pt is not None:
        rows = read_main_keyitems(st.main_pt)
    if rows is None:
        return None
    got = [r for r in rows if r[2]]                       # (id, name, obtained, used)
    table = _keyitems.all_keyitems()
    return Read(len(got), names=tuple(n for _, n, _, _ in got if n),
                denominator=len(table) or None)


def _r_abilities_mastered(st):
    # 40000_Common/players[].pa_extended (JsonParser.cs:873-897): `cur >= ap_required` per entry. This is
    # PARTY STATE (who currently has it mastered), NOT what AllAbility=183 scores -- that is
    # AchievementState.abilities, the EVER-LEARNED HashSet (AchievementState.cs:170). Denominator stays
    # None on purpose; see party.abilities_ever.
    if st.common is None:
        return None
    from .save_items import read_abilities
    per = read_abilities(st.common)
    total = sum(len(p["mastered"]) for p in per)
    return Read(total, ", ".join(f"{p['name']} {len(p['mastered'])}" for p in per if p["mastered"]))


def _r_thefts(st):
    # 40000_Common/steal_no (JsonParser.cs:929) -> Steal50 (target 50).
    v = _leaf(st.common, "steal_no")
    return None if v is None else Read(v)


def _r_escapes(st):
    # 40000_Common/escape_no (JsonParser.cs:925). No engine max.
    v = _leaf(st.common, "escape_no")
    return None if v is None else Read(v)


def _r_battles(st):
    # 40000_Common/battle_no (JsonParser.cs:1013) -- EXTRA-ONLY: it is inside the `!oldSaveFormat` arm.
    v = _leaf(st.common, "battle_no")
    return None if v is None else Read(v)


def _r_kills_total(st):
    """``GameState.TotalKillCount`` = ``modelKillCount.Values.Sum()`` (BattleCalculator.cs:36), scored
    against Defeat10000. Saved as ``40000_Common/kills_per_model`` (JsonParser.cs:944-955) -- the
    ``!oldSaveFormat`` arm only. A MIGRATED save has an EMPTY array while the category counters are
    non-zero (the old format carried only ``dragon_no``, :932): report that as UNAVAILABLE, never as 0."""
    if st.common is None:
        return None
    arr = _sj.get_path(st.common, "kills_per_model")
    if not isinstance(arr, _sj.SJArray):
        return None
    if len(arr) == 0 and any(_leaf(st.common, k, default=0) for k in KILL_CATEGORIES):
        return None                                       # migrated save: the per-model store is empty
    return Read(sum(_leaf(e, "count", default=0) for e in arr), f"{len(arr)} model(s)")


def _r_kills_by_category(st):
    # JsonParser.cs:936-943 -- `data.categoryKillCount[0..7]`, extra-only (the `!oldSaveFormat` arm).
    if st.common is None or _sj.get_path(st.common, KILL_CATEGORIES[0]) is None:
        return None
    per = [(k[:-3], _leaf(st.common, k, default=0)) for k in KILL_CATEGORIES]
    return Read(sum(v for _, v in per), ", ".join(f"{n} {v}" for n, v in per if v))


def _r_play_time(st):
    # 95000_Setting/00001_time -- a Double of SECONDS (JsonParser.cs:74,78); GameState.GameTime rounds it
    # (BattleCalculator.cs:48).
    if st.setting is None:
        return None
    v = _fnum(_sj.get_path(st.setting, "00001_time"))
    return None if v is None else Read(int(v), _hms(v))


def _r_field_entrance(st):
    # EventState.cs:26-34 -- `gEventGlobal[3] << 8 | gEventGlobal[2]`, UNSIGNED. flags.py:171 declares this
    # var signed and `_read_word` unpacks '<h', so an entrance >= 32768 renders NEGATIVE there and positive
    # in-game. The journal follows the ENGINE; flags.py is deliberately left alone (savedoc.py:233 renders
    # it -- a separate blast radius).
    return Read(_u16(st.geg, FIELD_ENTRANCE_OFF))


# ============================ the row table ============================
# The real deliverable. Order here IS report order. Nothing is dropped: a counter the game does not keep
# ships as status="untracked" with a blocked_by naming the exact obstacle.
ROWS = [
    # --- story -------------------------------------------------------------------------------------
    RowSpec("story.scenario", "story", "ScenarioCounter", None, "", "EventState.cs:18", "engine-read",
            "tracked", "geg", _r_scenario,
            note="A CHAPTER HEADING, not progress: 7 real fields DECREMENT it (research/CENSUS_DIGEST.md:15) "
                 "and the setter (EventState.cs:19-23) is unguarded, so it is not monotonic. "
                 "flags.SCENARIO_MILESTONES is 52 anchors carrying 39 distinct AREA names -- never render "
                 "N/52, and never derive a missability verdict from it."),
    RowSpec("story.next_objective", "story", "Next objective", None, "", "EventState.cs:18",
            "engine-read", "tracked", "geg", _r_next_objective,
            note="SC bucketed on the walkthrough spine (journalcatalog.main_story_ladder): the CURRENT "
                 "main-path section's authored `objective`, or its title where the prose pass has not "
                 "reached. The index is the rank-ladder expression class over the spine's sc_enter "
                 "anchors -- a WHERE, never an N/44 (the counter is not monotonic; see story.scenario)."),

    # --- treasure ----------------------------------------------------------------------------------
    RowSpec("treasure.hunter_points", "treasure", "Treasure Hunter points", None, "",
            "EventState.cs:64-70", "engine-read", "tracked", "geg", _r_th_points,
            note="A weighted popcount over three byte ranges (flags.TH_POINT_RANGES). There is NO engine "
                 "maximum, so the denominator stays None DELIBERATELY -- the game ships a RANK, not a "
                 "fraction. The weight-2 band (bytes 182-186) OVERLAPS chocobo.chocographs_dug's Int24 "
                 "(bytes 184-186): 24 dug chocographs are already 48 of these points."),
    RowSpec("treasure.hunter_rank", "treasure", "Treasure Hunter rank", 8, "EventState.cs:55-63",
            "EventState.cs:55-63", "engine-comment", "tracked", "geg", _r_th_rank,
            note="Rank index 0-8 (H..S) from the ladder >=340 S / 320 A / 300 B / 280 C / 260 D / 240 E / "
                 "220 F / 200 G / else H. In STOCK that ladder exists only as a COMMENT -- the sole "
                 "executable copy is our patched Ff9mkDebugMenu.cs. Hence 'engine-comment'."),
    RowSpec("treasure.chest_atlas", "treasure", "Treasure chests opened", None, "", "EventState.cs:64-70",
            "none", "untracked", "none", None,
            blocked_by="FF9 keeps NO per-chest registry. The engine's only treasure metric is the blind "
                       "weighted popcount of treasure.hunter_points, whose scored ranges do not align to "
                       "any chest census: this repo's own two figures disagree (386 in "
                       "research/CENSUS_DIGEST.md:103-111 vs 327 in research/STORY_FLAGS.md:100) and the "
                       "community 446/477 does not self-reconcile. Unblocking needs a per-chest .eb "
                       "census joined to the scored bytes, not a constant.",
            note="THERE IS NO `chests N/446` ROW AND THERE MUST NEVER BE ONE. Ship the rank."),

    # --- chocobo -----------------------------------------------------------------------------------
    RowSpec("chocobo.chocographs_found", "chocobo", "Chocographs found", CHOCOGRAPH_MAX,
            "ChocographUI.cs:428 (HintMapMax)", "ChocographUI.cs:250", "engine-derived", "tracked",
            "geg", _r_chocographs_found,
            note="Int24 at bytes 187-189 (`hasMap`). Triple-sourced denominator: HintMapMax=24, "
                 "EMinigame.numOfTreasures=24 (:762), AllTreasure target 24."),
    RowSpec("chocobo.chocographs_dug", "chocobo", "Chocographs dug up", CHOCOGRAPH_MAX,
            "ChocographUI.cs:428 (HintMapMax)", "ChocographUI.cs:251", "engine-derived", "tracked",
            "geg", _r_chocographs_dug,
            note="Int24 at bytes 184-186 (`hasGem`/`chocographOpened`). THESE ARE THE TREASURE-HUNTER x2 "
                 "BAND'S UPPER THREE BYTES (EventState.cs:69 scores 182-186 at weight 2), so this row and "
                 "treasure.hunter_points are NOT independent -- a full 24 here IS 48 of those points."),
    RowSpec("chocobo.beak_level", "chocobo", "Choco's beak level", ENGINE_TARGETS["ChocoboLv99"][0],
            ENGINE_TARGETS["ChocoboLv99"][1], "EMinigame.cs:282", "engine-derived", "tracked", "geg",
            _r_beak_level),
    RowSpec("chocobo.dig_ability", "chocobo", "Choco's terrain ability", DIG_ABILITY_MAX,
            "EMinigame.cs:454 (AllTreasureCheating terminal value)", "ChocographUI.cs:245",
            "engine-inferred", "tracked", "geg", _r_dig_ability,
            note="5 is what the engine's own cheats WRITE as the terminal value (EMinigame.cs:454, :493); "
                 "it is not a declared maximum anywhere -- that is exactly what 'engine-inferred' means."),
    RowSpec("chocobo.beaches", "chocobo", "Sandy beaches visited", ENGINE_TARGETS["AllSandyBeach"][0],
            ENGINE_TARGETS["AllSandyBeach"][1], "EMinigame.cs:474-483", "engine-derived", "tracked",
            "geg", _r_beaches,
            note="21 consecutive BITS from 856 (EMinigame.numOfSandyBeach=21, :763)."),

    # --- minigame ----------------------------------------------------------------------------------
    RowSpec("minigame.stellazzio", "minigame", "Stellazzio coins", STELLAZZIO_MAX, "EMinigame.cs:181",
            "EMinigame.cs:179-185", "engine-read", "tracked", "geg", _r_stellazzio,
            note="Low 13 bits of the UInt16 at byte 355. The denominator is the engine's own loop bound -- "
                 "do NOT use QueenReward10=10, which is the REWARD threshold, not the coin count."),
    RowSpec("minigame.ragtime_quiz", "minigame", "Ragtime Mouse answers", RAGTIME_MAX,
            "BattleAchievement.cs:43", "BattleAchievement.cs:41-42", "engine-read", "tracked", "geg",
            _r_ragtime,
            note="A 5-bit field (`byte 198 >> 3 & 31`), so 17-31 are representable but unreachable in "
                 "normal play; the raw value is reported unclamped and only the bar clamps."),
    RowSpec("minigame.hunt_winner", "minigame", "Festival of the Hunt winner", None, "",
            "EMinigame.cs:302", "engine-read", "tracked", "geg", _r_hunt_winner,
            exclusive_group="festival_of_the_hunt",
            note="Byte 313; the engine tests `== 2` (Vivi) for the ViviWinHunt achievement. Three mutually "
                 "exclusive winners -- excluded from meta.index because a bar that can never fill reads "
                 "as a bug."),
    RowSpec("minigame.coin_toss", "minigame", "Treno fountain coins", COIN_TOSS_MAX,
            "EMinigame.cs:755 (ThiefNPCCoinCondition)", "EMinigame.cs:335-337", "engine-read", "tracked",
            "geg", _r_coin_toss),
    RowSpec("minigame.frogs", "minigame", "Frogs caught", ENGINE_TARGETS["Frog99"][0],
            ENGINE_TARGETS["Frog99"][1], "JsonParser.cs:928", "engine-derived", "tracked", "extra",
            _r_frogs),
    RowSpec("minigame.cards_held", "minigame", "Tetra Master cards held", None, "",
            "QuadMistDatabase.cs:119", "engine-read", "tracked", "extra", _r_cards_held,
            note="The deck's length after the engine loader's own id filter (JsonParser.cs:650-654). No "
                 "engine maximum -- Configuration.TetraMaster.MaxCardCount is a MOD setting, not a target."),
    RowSpec("minigame.card_kinds", "minigame", "Tetra Master card kinds", CARD_KINDS_MAX,
            "CardPool.cs:102 (TOTAL_CARDS)", "QuadMistDatabase.cs:111-117", "engine-derived", "tracked",
            "extra", _r_card_kinds,
            note="Distinct TetraMasterCardId, ids 0-99 (NONE=255 excluded). NOT CardWinAll=235 -- that is "
                 "the OPPONENT-defeat list."),
    RowSpec("minigame.collector_points", "minigame", "Card collector points", COLLECTOR_POINTS_MAX,
            "QuadMistDatabase.cs:236 (top threshold)", "QuadMistDatabase.cs:185-199", "engine-read",
            "tracked", "extra", _r_collector_points, run_mode="perfect-collection",
            note="kinds*10 + typePtsWorth[type] per card + 5 per distinct arrow pattern. Exactly 1700 "
                 "glitches the rank label, so 1699 is the practical maximum -- flagged run_mode so it "
                 "does not drag meta.index."),
    RowSpec("minigame.collector_level", "minigame", "Card collector level", COLLECTOR_LEVEL_MAX,
            "QuadMistDatabase.cs:243 (CollectorLevelMax-1)", "QuadMistDatabase.cs:202-244", "engine-read",
            "tracked", "extra", _r_collector_level, run_mode="perfect-collection",
            note="The 32-entry threshold ladder, transcribed verbatim (FF9SAVE_MINIGAME.CollectorLevelMax "
                 "= 32, :6)."),
    RowSpec("minigame.card_record", "minigame", "Tetra Master wins", None, "", "JsonParser.cs:693-695",
            "engine-read", "tracked", "extra", _r_card_record,
            note="Value is sWin; the detail carries W/L/D. No engine maximum."),
    RowSpec("minigame.quadmist_opponents", "minigame", "Tetra Master opponents defeated",
            ENGINE_TARGETS["CardWinAll"][0], ENGINE_TARGETS["CardWinAll"][1], "AchievementState.cs:180",
            "none", "untracked", "none", None,
            blocked_by="AchievementState.QuadmistWinList is a HashSet<Int32> (AchievementState.cs:180) "
                       "living in the main-block-only 80000_Achievement node, and ReportAchievement HARD "
                       "RETURNS for CardWinAll (AchievementManager.cs:74-75) so the engine stores no "
                       "status for it either. Unblocking = mapping the fixed-size sentinel-padded "
                       "80000_Achievement block (JsonParser.cs:1630-1681)."),

    # --- mognet ------------------------------------------------------------------------------------
    RowSpec("mognet.delivered", "mognet", "Letters delivered", None, "", "content/mognet.py:85",
            "kit-decoded", "tracked", "geg", _r_mognet_delivered,
            note="gEventGlobal Byte 1032 -- decoded from fields 300/407/1102 and live-save verified; there "
                 "is no engine C# reader, hence 'kit-decoded'. Mognet Central reads it for 'Thanks for "
                 "delivering [NUMB] letters!'."),
    RowSpec("mognet.stiltzkin_tally", "mognet", "Stiltzkin tally (moogle-side)", None, "",
            "content/mognet.py:86", "kit-decoded", "tracked", "geg", _r_mognet_stiltzkin,
            note="gEventGlobal Byte 1033 -- the moogle fields' OWN counter. THE TRAP: AllStiltzkinItem's "
                 "target of 8 scores AchievementState.StiltzkinBuy (EMinigame.cs:50-52, gated on eight "
                 "exact gil prices), NOT this byte. No /8 here. See mognet.stiltzkin_purchases."),
    RowSpec("mognet.stiltzkin_purchases", "mognet", "Stiltzkin purchases",
            ENGINE_TARGETS["AllStiltzkinItem"][0], ENGINE_TARGETS["AllStiltzkinItem"][1],
            "AchievementState.cs:178", "none", "untracked", "none", None,
            blocked_by="AchievementState.StiltzkinBuy (AchievementState.cs:178) is main-block-only "
                       "(80000_Achievement). Unblocking = mapping that fixed-size block."),
    RowSpec("mognet.letters_carried", "mognet", "Letters in hand", MOGNET_SLOTS, "content/mognet.py:88",
            "content/mognet.py:87-89", "kit-decoded", "tracked", "geg", _r_mognet_carrying,
            note="Three 4-byte slots from 1034; +0 is the occupied flag. A carry state, not progress."),
    RowSpec("mognet.give_locks", "mognet", "Letter variants handed out", 64, "flags.py:274",
            "flags.py:274-279", "kit-decoded", "tracked", "geg", _r_mognet_give_locks,
            note="One bit per letter VARIANT, not per letter (anchor 8383, bit(v) = anchor + 8*(v//8) - "
                 "(v%8)). flags.SaveReport.mognet_locks is the UNION 8376-8511; the journal splits it and "
                 "leaves flags.py untouched."),
    RowSpec("mognet.read_locks", "mognet", "Letter variants read", 64, "flags.py:280", "flags.py:280-283",
            "kit-decoded", "tracked", "geg", _r_mognet_read_locks,
            note="The read-side twin (anchor 8447); set on ARRIVAL, gating that variant's read-mail row."),
    RowSpec("mognet.central_discovered", "mognet", "Mognet Central discovered", 1,
            "WorldConfiguration.cs:189", "WorldConfiguration.cs:188-189", "engine-read", "tracked", "geg",
            _r_mognet_central,
            note="Bit 815 = byte 101 & 0x80. The only engine-grounded Mognet bit in gEventGlobal."),
    RowSpec("mognet.paradise_discovered", "mognet", "Chocobo's Paradise discovered", 1,
            "WorldConfiguration.cs:183", "WorldConfiguration.cs:182-183", "engine-read", "tracked", "geg",
            _r_chocobo_paradise,
            note="Bit 814 = byte 101 & 0x40."),

    # --- party -------------------------------------------------------------------------------------
    RowSpec("party.gil", "party", "Gil", None, "", "JsonParser.cs:927",
            "engine-read", "tracked", "extra", _r_gil,
            note="Extra 40000_Common/gil; a VANILLA slot falls back to the main block's UInt32 at "
                 "save_items.MAIN_GIL_OFF (:90). DENOMINATOR DELIBERATELY None: the engine's only bound "
                 f"is an overflow CLAMP (Math.Min({GIL_CAP}U, value), BattleCalculator.cs:62), not a "
                 "completion goal -- pooling it into meta.index would make a 10-million denominator swamp "
                 "every real target."),
    RowSpec("party.key_items", "party", "Key items obtained", None, "", "JsonParser.cs:995-1006",
            "live-install", "tracked", "extra", _r_key_items, name_source="keyitems.all_keyitems",
            note="Denominator + names resolve at RUNTIME from "
                 "<install>/StreamingAssets/Text/<lang>/KeyItems.strings (keyitems.py:30-48) and are None "
                 "/ empty when the install is unreachable -- the value is still valid. NEVER bake a name "
                 "table: the owner stacks Moguri. rareItemsEx is SPARSE (an unobtained id is ABSENT, not "
                 "obtained=false), so the array length can never be the denominator. "
                 "IN-GAME (T1b): the .eb sums B_HAVE_ITEM over item ids 256.. -- the SAME set, because "
                 "FF9Item_GetCount_Generic routes an important id to FF9Item_IsExistImportant "
                 "(ff9item.2.cs:229) which is literally `rare_item_obtained.Contains(id)` (:343-345). "
                 "But an .eb is STATIC, so the id WINDOW (journal.KEY_ITEM_EB_COUNT) is a BUILD-TIME "
                 "BAKE of what the live table reports -- the one place THE NAMES LAW is deliberately "
                 "narrowed. journalfield.lint_pages re-reads the live table and FAILS on a mismatch."),
    RowSpec("party.abilities_mastered", "party", "Abilities mastered (party)", None, "",
            "JsonParser.cs:873-897", "live-install", "tracked", "extra", _r_abilities_mastered,
            note="Per-character pa_extended entries with cur >= the live AP requirement -- PARTY STATE. "
                 "This is NOT what AllAbility=183 scores; see party.abilities_ever. Denominator None on "
                 "purpose (the per-character pool sizes come from the install)."),
    RowSpec("party.abilities_ever", "party", "Abilities ever learned", ENGINE_TARGETS["AllAbility"][0],
            ENGINE_TARGETS["AllAbility"][1], "AchievementState.cs:170", "none", "untracked", "none", None,
            blocked_by="AchievementState.abilities is a HashSet<Int32> (AchievementState.cs:170) in the "
                       "main-block-only 80000_Achievement node, and ReportAchievement hard-returns for "
                       "AllAbility (AchievementManager.cs:74-75). Unblocking = mapping that block."),
    RowSpec("party.passive_abilities_ever", "party", "Support abilities ever learned",
            ENGINE_TARGETS["AllPasssiveAbility"][0], ENGINE_TARGETS["AllPasssiveAbility"][1],
            "AchievementState.cs:172", "none", "untracked", "none", None,
            blocked_by="AchievementState.passiveAbilities (AchievementState.cs:172) is main-block-only; "
                       "the target equals AchievementState.MAX_PASSIVE_ABILITIES (:112). Unblocking = "
                       "mapping 80000_Achievement."),
    RowSpec("party.thefts", "party", "Successful steals", ENGINE_TARGETS["Steal50"][0],
            ENGINE_TARGETS["Steal50"][1], "JsonParser.cs:929", "engine-derived", "tracked", "extra",
            _r_thefts),
    RowSpec("party.escapes", "party", "Battles escaped", None, "", "JsonParser.cs:925", "engine-read",
            "tracked", "extra", _r_escapes,
            note="No engine maximum (GameState.EscapeCount, BattleCalculator.cs:38)."),
    RowSpec("party.battles", "party", "Battles fought", None, "", "JsonParser.cs:1013", "engine-read",
            "tracked", "extra", _r_battles,
            note="EXTRA-ONLY: battle_no is emitted inside the `!oldSaveFormat` arm, so a vanilla slot has "
                 "no such field at all."),
    RowSpec("party.kills_total", "party", "Enemies defeated", ENGINE_TARGETS["Defeat10000"][0],
            ENGINE_TARGETS["Defeat10000"][1], "BattleCalculator.cs:36", "engine-derived", "tracked",
            "extra", _r_kills_total,
            note="Sum of 40000_Common/kills_per_model, matching GameState.TotalKillCount. A MIGRATED save "
                 "has an empty array with non-zero category counters -- that downgrades to 'unavailable', "
                 "never to 0."),
    RowSpec("party.kills_by_category", "party", "Kills by category", None, "", "JsonParser.cs:936-943",
            "engine-read", "tracked", "extra", _r_kills_by_category,
            note="The 8 categoryKillCount leaves (humanoid/beast/devil/dragon/undead/stone/soul/flight). "
                 "Overlaps party.kills_total by construction; no engine maximum."),

    # --- combat ------------------------------------------------------------------------------------
    RowSpec("combat.yan_blessing", "combat", "Yan's blessing", 1, "BattleAchievement.cs:51",
            "BattleAchievement.cs:50-51", "engine-read", "tracked", "geg", _r_yan_blessing,
            note="Bit 1584, checked on the Yan battle maps (920/921). The ONLY engine-grounded friendly-"
                 "monster bit -- see meta.friendly_monsters."),

    # --- meta --------------------------------------------------------------------------------------
    RowSpec("meta.play_time", "meta", "Play time", None, "", "JsonParser.cs:74", "engine-read", "tracked",
            "extra", _r_play_time,
            note="95000_Setting/00001_time, a Double of SECONDS (GameState.GameTime rounds it, "
                 "BattleCalculator.cs:48). THE ROW VALUE IS SECONDS. The in-game expression publishes "
                 "HOURS -- the catalog's ONE declared unit change (journal.EB_SCALE: 3600, 'h'), "
                 "cross-checked as value // 3600 and rendered with its unit by journalfield."),
    RowSpec("meta.step_count", "meta", "Steps taken", None, "", "JsonParser.cs:519-520", "engine-read",
            "dead", "extra", None,
            note="DEAD: 20000_Event/gStepCount is declared (EventState.cs:8), saved (JsonParser.cs:578), "
                 "and sysvar-readable (EventEngine.GetSysvar.cs:34, BattleCalculator.cs:40) -- but a "
                 "whole-repo sweep finds exactly ONE assignment, `gStepCount = 0` at "
                 "EventEngine.Initialize.cs:42. Nothing increments it. Measured 0 on every real save. A "
                 "dead row renders as 'not tracked by the game', never as 0% progress."),
    RowSpec("meta.field_entrance", "meta", "Last field entrance", None, "", "EventState.cs:28",
            "engine-read", "tracked", "geg", _r_field_entrance,
            note="Diagnostic, not progress. Read UNSIGNED here because the engine reads it unsigned; "
                 "flags.py:171 declares it signed, so an entrance >= 32768 renders negative there and "
                 "positive in-game. Latent (real saves measured 35 / 211 / 10000)."),
    RowSpec("meta.ates_seen", "meta", "ATEs seen", ATE_SEEN_MAX, ENGINE_TARGETS["ATE80"][1],
            "AchievementState.cs:116", "none", "untracked", "none", None,
            exclusive_group="ate_pair",
            blocked_by="AchievementState.AteCheck is an Int32[100] (AchievementState.cs:116) in the "
                       "main-block-only 80000_Achievement node -- NOT gEventGlobal (flags.py:414-418 says "
                       "the same). The engine's own count is EMinigame.cs:521-524. Unblocking = mapping "
                       "the fixed-size block (AteCheckArray is its FIRST array, JsonParser.cs:1630+).",
            note="79 of 83 slots exists BECAUSE of a mutually exclusive pair, hence exclusive_group."),
    RowSpec("meta.bestiary", "meta", "Bestiary species seen", None, "", "AchievementState.cs:128", "none",
            "untracked", "none", None,
            blocked_by="There is no per-species registry. AchievementState.enemy_no is a SCALAR "
                       "(AchievementState.cs:128) and 40000_Common/kills_per_model counts per battle "
                       "MODEL, not per species. Unblocking needs a model->species table plus a "
                       "'seen but not killed' store the game does not have."),
    RowSpec("meta.synthesis_recipes", "meta", "Synthesis recipes made", None, "",
            "AchievementState.cs:174", "none", "untracked", "none", None,
            blocked_by="Only AchievementState.synthesisCount exists (AchievementState.cs:174, incremented "
                       "at ShopUI.cs:429) -- a TOTAL, never per recipe, and it is serialized only into "
                       "the main-block-only 80000_Achievement node (JsonParser.cs:1668)."),
    RowSpec("meta.friendly_monsters", "meta", "Friendly monsters fed", None, "",
            "BattleAchievement.cs:50-51", "none", "untracked", "none", None,
            note="The commonly quoted 9 is a COMMUNITY figure with no engine declaration -- there is no "
                 "AchievementInfo target and no counter, so no denominator is recorded here.",
            blocked_by="Only the Yan blessing bit 1584 is engine-grounded (shipped as "
                       "combat.yan_blessing); the other 8 friendly-monster states have no engine reader "
                       "and no decoded gEventGlobal home. Unblocking = an .eb census of the 8 encounter "
                       "fields, the way content/mognet.py decoded the mailbox."),
    RowSpec("meta.achievement_keys", "meta", "Achievements unlocked", ACHIEVEMENT_KEYS_NORMAL,
            "AcheivementKey.cs:7-94", "AchievementState.cs:77-80", "none", "untracked", "none", None,
            blocked_by="The normal-achievement statuses live in AchievementState's EvtReservedArray "
                       "(main-block-only). WHEN IT IS UNBLOCKED, test `!= NotUnlockYet`, NEVER "
                       "`== UnlockComplete`: UnlockComplete is only written downstream of "
                       "`if (!Social.IsSocialPlatformAuthenticated()) return;` "
                       "(AchievementManager.cs:112-113), so an offline 100% save would render 0%.",
            note="87 real keys (AcheivementKey.cs ordinals 0-86 plus the AchievementKeyCount sentinel at "
                 ":94) minus the 2 system-held (CompleteGame, Blackjack) = 85 normal."),
    RowSpec("meta.index", "meta", "Completion index", 100, "kit-derived (journal.build_report)", "",
            "kit-derived", "tracked", "derived", None,
            note="sum(min(value, denom)) / sum(denom) over TRACKED rows that have a denominator, "
                 "EXCLUDING any row with an exclusive_group or a run_mode -- a bar that can never fill "
                 "reads as a bug. Rendered beside the untracked count so the hole is always visible. "
                 "KNOWN PROPERTY, not a defect to 'fix' silently: the pool is DOMINATED by "
                 "party.kills_total (denominator 10000 against a pooled total near 10600), so this index "
                 "tracks kill count more than anything else. The per-row percentages are the honest read; "
                 "changing the weighting changes a number the catalog and a later in-game screen both "
                 "consume, so it is a deliberate decision, not a tidy-up."),
]

# ==================== the IN-GAME half: one .eb expression per row, or a reason ====================
# T1b renders this SAME catalog on a field screen. The offline `read` is a Python function over a
# JournalState; the in-game value is an RPN byte stream, so the second renderer needs a second
# representation -- a token STRING, because that is the only form BOTH `journal rows --json` (the
# permanent contract, :func:`rows_json`) and the .eb emitter can consume, and it round-trips through
# `exprasm.assemble` / `disasm.pretty_expr` so a review diff is readable.
#
# WHY A TABLE AND NOT 48 MORE KEYWORD ARGUMENTS ON THE ROWS ABOVE. Three reasons, in order of weight:
#   1. Two of the expressions are 80 and 100 terms long (:func:`_have_item_sum`) -- generated, not
#      typed. A generated value cannot be a literal kwarg.
#   2. The decision "does this row have an in-game read, and if not WHY" is one axis across all 48
#      rows, and it is the axis the exhaustiveness gate checks. Keeping it contiguous is what makes
#      "31 declared / 17 refused" readable in one screen instead of grepped out of 300 lines of prose.
#   3. The gate does not get weaker: :func:`_attach_eb` writes the fields onto the RowSpec, a row in
#      NEITHER table keeps both fields None, and `lint_rows` refuses that -- so a row added later
#      FAILS instead of defaulting to "invisible in-game", the same shape as exprsem's
#      operator-coverage assertion (eb/exprsem.py:8-13). An id in a table that is not in ROWS fails
#      too, so a rename cannot orphan a decision.
#
# The token spellings are the ones `eb/exprasm.py` assembles; `ff9mapkit journal lint` assembles AND
# stack-walks every one of them (`eb/exprsem.py`), so a malformed expression fails a CI-usable gate
# before any field references it.

# Item-id bands (ff9item.2.cs:417-427): regular < 256, IMPORTANT 256-511, cards 512-611. `B_HAVE_ITEM`
# -> `ff9item.FF9Item_GetCount_Generic` (EventEngine.DoCalcOperationExt.cs:13-20) dispatches on those.
ITEM_IMPORTANT_BASE = 256   # ff9item.2.cs:422-426 -- IsItemImportant(modId >= 256 && < 512)
ITEM_CARD_BASE = 512        # ff9item.2.cs:428-432 -- IsItemCard(modId >= 512 && < 612)
# THE ONE BUILD-TIME BAKE in this table. The key-item sum needs a STATIC id window because an `.eb` is
# a static byte stream -- runtime resolution (THE NAMES LAW, module docstring) is impossible in-game.
# 80 contiguous ids (0..79 -> item ids 256..335) is what `keyitems.all_keyitems()` reports on this
# install. journalfield.lint_pages RE-READS the live table and FAILS when it disagrees, so a Moguri
# swap cannot silently ship an 80-term sum against a different table.
KEY_ITEM_EB_COUNT = 80


def _sum_tokens(terms) -> str:
    """Sum a list of RPN sub-expressions INTERLEAVED (``t0 t1 B_PLUS t2 B_PLUS ...``) rather than
    folded at the end (``t0 t1 t2 ... B_PLUS B_PLUS``). Byte-identical either way; the interleaved
    form holds the CalcStack at depth 2 instead of depth N, which matters because the kit already
    burned a lane on CalcStack depth (the Path-B cross-product overflow, CLAUDE.md dead ends)."""
    terms = list(terms)
    if not terms:
        raise ValueError("_sum_tokens: no terms")
    return " ".join([terms[0]] + [f"{t} B_PLUS" for t in terms[1:]])


def _bit_popcount(base: int, n: int) -> str:
    """``n`` consecutive gEventGlobal BITS, summed. Each term is a `Global.Bit[i]` read -- byte
    ``i>>3`` bit ``i&7`` (EBin.cs:1851-1856).

    THIS IS ALSO THE Int24 SIGN-EXTENSION FIX, structurally. Reading the 24 chocograph bits as one
    `Global.Int24[187]` hits EBin.cs:1858-1861, where ONE case label covers Int24 AND UInt24 and casts
    the third byte to SByte -- 24/24 reads -1 and no playtest can surface it (a save with all 24 dug
    is not reachable in a test session). Summing bits never touches that path, so the defect is
    UNREPRESENTABLE here rather than merely guarded by a mask someone could later 'optimise' away."""
    return _sum_tokens(f"Global.Bit[{base + i}]" for i in range(n))


def _have_item_sum(base: int, n: int) -> str:
    """``sum(B_HAVE_ITEM(base+i))`` over ``n`` ids -- the held/obtained count for an item band."""
    return _sum_tokens(f"const({base + i}) B_HAVE_ITEM" for i in range(n))


def _have_kind_sum(base: int, n: int) -> str:
    """``sum(B_HAVE_ITEM(base+i) > 0)`` -- DISTINCT kinds, not copies. For cards this reproduces
    `QuadMistDatabase.MiniGame_GetCardKindCount` (:110-116) while :func:`_have_item_sum` over the same
    band reproduces `MiniGame_GetAllCardCount` (:119-122): `MiniGame_GetCardCount(id)` counts deck
    entries per id (:154-157), so the plain sum IS the deck length."""
    return _sum_tokens(f"const({base + i}) B_HAVE_ITEM const(0) B_GT" for i in range(n))


def _rank_ladder(value: str, thresholds) -> str:
    """``sum(value >= T)`` over the ladder's non-zero thresholds -> the rank INDEX, exactly what
    :func:`treasure_hunter_rank` returns offline (index 0-8 into TH_RANKS)."""
    return _sum_tokens(f"{value} const({t}) B_GE" for t in thresholds if t)


#: row id -> (RPN tokens, engine file:line the expression replicates). 31 of the 48 rows.
EB_EXPRESSIONS = {
    # --- story / treasure ---------------------------------------------------------------------
    "story.scenario": ("Global.UInt16[0]", "EventState.cs:18"),
    # The next-objective index: the rank-ladder class (in-game proven on the TH rank) over the
    # walkthrough spine's main-path sc_enter anchors, first excluded (fresh save -> row 0). The
    # SAME journalcatalog.main_story_ladder() feeds _r_next_objective and the [TBLE] rows, so the
    # published index and the rendered row cannot come from different ladders.
    "story.next_objective": (_rank_ladder("Global.UInt16[0]", _story_ladder()[0][1:]),
                             "EventState.cs:18"),
    # The memoria_variable lane, OWNER-CONFIRMED in-game on bench 30800 (rung 0): `Null.SBit[N]` is
    # VariableSource.Null + VariableType.Any -> GetMemoriaCustomVariable((memoria_variable)N)
    # (EBin.cs:1636-1638). N=5 read real per-save Treasure-Hunter points (0 / 178 / 215).
    "treasure.hunter_points": ("Null.SBit[5]", "EBin.cs:1703"),
    "treasure.hunter_rank": (_rank_ladder("Null.SBit[5]", TH_RANK_MIN), "EventState.cs:55-63"),

    # --- chocobo ------------------------------------------------------------------------------
    "chocobo.chocographs_found": (_bit_popcount(CHOCOGRAPH_FOUND_OFF * 8, CHOCOGRAPH_MAX),
                                  "ChocographUI.cs:250"),
    "chocobo.chocographs_dug": (_bit_popcount(CHOCOGRAPH_OPENED_OFF * 8, CHOCOGRAPH_MAX),
                                "ChocographUI.cs:251"),
    "chocobo.beak_level": (f"Global.Byte[{BEAK_LEVEL_OFF}]", "EMinigame.cs:282"),
    "chocobo.dig_ability": (f"Global.Byte[{DIG_ABILITY_OFF}]", "ChocographUI.cs:245"),
    "chocobo.beaches": (_bit_popcount(SANDY_BEACH_BIT, ENGINE_TARGETS["AllSandyBeach"][0]),
                        "EMinigame.cs:474-483"),

    # --- minigame -----------------------------------------------------------------------------
    "minigame.stellazzio": (_bit_popcount(STELLAZZIO_OFF * 8, STELLAZZIO_MAX), "EMinigame.cs:179-185"),
    "minigame.ragtime_quiz": (f"Global.Byte[{RAGTIME_OFF}] const(3) B_SHIFT_RIGHT const(31) B_AND",
                              "BattleAchievement.cs:41-42"),
    # THE UPWARD CLAMP. This value indexes a [TBLE] row, and ETb.GetStringFromTable guards the upper
    # bound by returning String.Empty (ETb.cs:278) -- a BLANK LINE, which reads as a bug. The
    # multiply-by-predicate idiom (the same one behavior.hud_row_index_clamp uses for the LOWER bound,
    # content/behavior.py:736-749) folds any byte > 3 back to row 0 ("---").
    "minigame.hunt_winner": (f"Global.Byte[{HUNT_WINNER_OFF}] Global.Byte[{HUNT_WINNER_OFF}] "
                             f"const(3) B_LE B_MULT", "EMinigame.cs:302"),
    "minigame.coin_toss": (f"Global.Byte[{COIN_TOSS_OFF}]", "EMinigame.cs:335-337"),
    "minigame.frogs": ("B_SYSVAR[16]", "EventEngine.GetSysvar.cs:51-52"),
    # NOT B_SYSVAR[19]. GetSysvar case 19 returns the raw count ONLY when
    # Configuration.TetraMaster.MaxCardCount == 100; otherwise it applies a compatibility remap
    # (Min(cardCount,95) / a MaxCardCount-relative shift, GetSysvar.cs:57-69) and would silently
    # disagree with the offline reader on the very row pair the one-catalog bet exists to keep in
    # sync. The 100-term sum equals MiniGameCard.Count exactly. That costs bytes; pay them.
    "minigame.cards_held": (_have_item_sum(ITEM_CARD_BASE, CARD_KINDS_MAX),
                            "QuadMistDatabase.cs:154-157"),
    "minigame.card_kinds": (_have_kind_sum(ITEM_CARD_BASE, CARD_KINDS_MAX),
                            "QuadMistDatabase.cs:110-116"),
    "minigame.collector_points": ("Null.SBit[3]", "EBin.cs:1699"),
    "minigame.collector_level": ("Null.SBit[4]", "EBin.cs:1701"),
    "minigame.card_record": ("Null.SBit[0]", "EBin.cs:1693"),

    # --- mognet -------------------------------------------------------------------------------
    "mognet.delivered": (f"Global.Byte[{MOGNET_DELIVERED_OFF}]", "content/mognet.py:85"),
    "mognet.stiltzkin_tally": (f"Global.Byte[{MOGNET_STILTZKIN_OFF}]", "content/mognet.py:86"),
    "mognet.letters_carried": (_sum_tokens(f"Global.Byte[{MOGNET_SLOT_BASE + 4 * k}] const(0) B_GT"
                                           for k in range(MOGNET_SLOTS)), "content/mognet.py:87-89"),
    "mognet.give_locks": (_bit_popcount(MOGNET_GIVE_LO, MOGNET_GIVE_HI - MOGNET_GIVE_LO + 1),
                          "flags.py:274-279"),
    "mognet.read_locks": (_bit_popcount(MOGNET_READ_LO, MOGNET_READ_HI - MOGNET_READ_LO + 1),
                          "flags.py:280-283"),
    "mognet.central_discovered": (f"Global.Bit[{MOGNET_CENTRAL_BIT}]", "WorldConfiguration.cs:188-189"),
    "mognet.paradise_discovered": (f"Global.Bit[{CHOCOBO_PARADISE_BIT}]", "WorldConfiguration.cs:182-183"),

    # --- party --------------------------------------------------------------------------------
    "party.gil": ("B_SYSVAR[6]", "EventEngine.GetSysvar.cs:31-32"),
    # SOURCE-OVER-DESIGN. The approved design refused this row, on the premise that B_HAVE_ITEM reads
    # HELD while the offline row counts OBTAINED. The engine says otherwise:
    # FF9Item_GetCount_Generic -> FF9Item_IsExistImportant (ff9item.2.cs:229, :343-345) is exactly
    # `rare_item_obtained.Contains(id)`, and `rare_item_used` is a SEPARATE set --
    # FF9Item_UseImportant only ADDS to `used` (:333-336) and never removes from `obtained`; only
    # FF9Item_RemoveImportant clears both (:327-331). The offline reader counts the same set
    # (`obtained` per entry, JsonParser.cs:1004 -> save_items.read_keyitems:297). SAME QUANTITY, so
    # this is one row with two renderers -- which is the whole bet -- and the design's proposed
    # `party.key_items_held` sibling would have shipped a SECOND row for ONE number.
    "party.key_items": (_have_item_sum(ITEM_IMPORTANT_BASE, KEY_ITEM_EB_COUNT), "ff9item.2.cs:343-345"),

    # --- combat / meta ------------------------------------------------------------------------
    "combat.yan_blessing": (f"Global.Bit[{YAN_BLESSING_BIT}]", "BattleAchievement.cs:50-51"),
    # HOURS -- the ONE row whose two renderers publish different UNITS, and the only reason that is
    # allowed is that :data:`EB_SCALE` declares the conversion and the cross-validation asserts it.
    # The page adds a SECOND, page-local slot for the minutes remainder (journalfield) -- the only
    # two-slot row. Dividing is for READABILITY (600h in 3 digits), NOT overflow safety:
    # Settings.time is capped at 2,160,001 s (SettingsState.cs) and GetSysvar(20) additionally clamps
    # to 8,388,607 (GetSysvar.cs:70-73), both far under the 26-bit envelope.
    "meta.play_time": ("B_SYSVAR[20] const(3600) B_DIV", "EventEngine.GetSysvar.cs:70-73"),
    # An in-game read EXISTS; the game never moves the counter. `eb` and `status` are ORTHOGONAL and
    # the schema keeps them so -- collapsing them would render a dead counter as 0% progress.
    "meta.step_count": ("B_SYSVAR[7]", "EventEngine.GetSysvar.cs:33-34"),
    "meta.field_entrance": (f"Global.UInt16[{FIELD_ENTRANCE_OFF}]", "EventState.cs:28"),
}

#: row id -> ``(scale, unit)`` for the ONE row whose ``.eb`` publishes a different UNIT from its
#: offline reader. THE UNIT LAW: ``eb_eval(row.eb) == read(save).value // scale``, exactly.
#:
#: Why this is a schema FIELD and not a comment. The catalog's bet is "one row, two renderers, one
#: number", and until this table existed ``meta.play_time`` quietly broke it: the offline reader
#: returns the ``95000_Setting`` seconds Double (27733) while the expression returns hours (7). Two
#: renderers publishing different numbers for one row id is precisely the divergence the bet exists to
#: prevent, and NOTHING tied them -- the cross-validation family excluded the row and no lint rule
#: mentioned units. Declaring the relation makes it CHECKED in three places instead of hoped: the
#: exhaustive unit cross-test (tests/test_journal.py), ``rows_json`` (a consumer gets the scale next to
#: the expression), and ``journalfield.render_page``, which renders ``eb_unit`` FROM HERE so a scaled
#: value cannot print bare next to an unscaled one.
#:
#: A row that is not in this table declares scale 1 / unit "" -- the same number, the default, the rule.
EB_SCALE = {
    # seconds -> hours. B_SYSVAR[20] is already clamped to 8,388,607 s (EventEngine.GetSysvar.cs:70-73)
    # and B_DIV truncates, so this is floor division on both sides.
    "meta.play_time": (3600, "h"),
}

#: row id -> WHY its ``B_DIV`` does NOT change the unit. The escape hatch for the rule below, and it
#: costs a written reason rather than silence. Empty today: :data:`EB_SCALE` covers the only divider.
EB_DIV_SAME_UNIT = {}

#: row id -> WHY there is no in-game read. 17 of the 48 rows. Nothing is silently dropped: every one
#: of these still gets a LABELLED line on a page ("--" = offline only, "n/a" = the game keeps nothing).
_EB_ABSENT_ACHIEVEMENT = (
    "AchievementState, the main-block-only 80000_Achievement node. The row is ALREADY status="
    "'untracked' with a blocked_by naming the same obstacle, and lint_rows refuses an eb on an "
    "untracked row -- so the two facts cannot drift apart. No expression opcode reaches it: "
    "GetSysvar has no case (EventEngine.GetSysvar.cs:8-106), memoria_variable has exactly 11 codes "
    "and none of these (EBin.cs:2416-2431), flexible_varfunc is item/ability/player/shop conversions "
    "only (EBin.cs:2388-2414). IN-GAME: 'n/a'.")
_EB_ABSENT_EXTRA_COUNTER = (
    "A GameState counter serialized ONLY into the Memoria extra 40000_Common (JsonParser.cs:925-955). "
    "No expression opcode reads it -- GetSysvar exposes gil=6, steps=7, frogs=16, cards=19, time=20 "
    "and nothing else (EventEngine.GetSysvar.cs:8-106), which is exactly why those five rows ARE "
    "readable and these are not. Unblocking needs a Memoria patch adding memoria_variable codes, "
    "i.e. a DLL -- which T1b is defined to avoid. IN-GAME: '--'.")

EB_ABSENT = {
    "treasure.chest_atlas":
        "There is nothing to read. FF9 keeps no per-chest registry; the engine's only treasure metric "
        "is the blind weighted popcount already shipped as treasure.hunter_points, and this repo's own "
        "two chest censuses disagree (386 vs 327). The catalog note says THERE MUST NEVER BE a "
        "chests-N/446 row; the in-game page must not invent one either. IN-GAME: 'n/a', directly under "
        "the rank that DOES exist.",
    "minigame.quadmist_opponents": _EB_ABSENT_ACHIEVEMENT,
    "mognet.stiltzkin_purchases": _EB_ABSENT_ACHIEVEMENT,
    "party.abilities_ever": _EB_ABSENT_ACHIEVEMENT,
    "party.passive_abilities_ever": _EB_ABSENT_ACHIEVEMENT,
    "meta.ates_seen": _EB_ABSENT_ACHIEVEMENT,
    "meta.synthesis_recipes": _EB_ABSENT_ACHIEVEMENT,
    "meta.achievement_keys": _EB_ABSENT_ACHIEVEMENT,
    "party.thefts": _EB_ABSENT_EXTRA_COUNTER,
    "party.escapes": _EB_ABSENT_EXTRA_COUNTER,
    "party.battles": _EB_ABSENT_EXTRA_COUNTER,
    "party.kills_total": _EB_ABSENT_EXTRA_COUNTER,
    "party.kills_by_category": _EB_ABSENT_EXTRA_COUNTER,
    "party.abilities_mastered":
        "An .eb path EXISTS and is REFUSED ON COST, not overlooked. flex(16,3) PLAYER_ABILITY_LEARNT "
        "is per (character, ability) (EBin.cs:421-435), so a party-wide mastered count is ~8 "
        "characters x ~100 ability ids = ~800 terms at ~13 bytes = ~10KB -- about 16% of the whole "
        "0xFFFF offset budget for ONE line -- and the per-character pool sizes come from the live "
        "install anyway. IN-GAME: '--'.",
    "meta.bestiary":
        "No per-species store exists at any tier: AchievementState.enemy_no is a SCALAR and "
        "40000_Common/kills_per_model counts battle MODELS, not species. IN-GAME: 'n/a'.",
    "meta.friendly_monsters":
        "Only the Yan blessing bit is engine-grounded, and it already ships as combat.yan_blessing "
        "(Bit 1584, BattleAchievement.cs:50-51) on the SAME page two lines above. The other 8 states "
        "have no engine reader and no decoded gEventGlobal home. IN-GAME: 'n/a' -- deliberately "
        "adjacent to the one that works, so the hole is legible.",
    "meta.index":
        "The offline index pools ~15 tracked rows and is DOMINATED by party.kills_total (10000 of a "
        "~10600 pooled total), a row the .eb cannot read at all. An in-game index over the readable "
        "subset would be a DIFFERENT number wearing the same name -- precisely the failure the "
        "one-catalog-two-renderers bet exists to prevent. IN-GAME: '--'. THE UNLOCK FOR A LATER RUNG "
        "(not T1b): a page body is ordinary .eb command flow, not a per-frame hud, so SET() writes "
        "ARE legal there; an index page could accumulate min(v,d) into MAP scratch words and divide "
        "once. That is still a different pool, so it needs its OWN row id (meta.index_eb) with its "
        "own offline reader over exactly the .eb-declared subset. Do not retrofit it onto meta.index.",
}


# ---------------------------------------------------------------- the 26-bit envelope, ENFORCED
# Every COMPUTED intermediate is 26-bit signed, not Int32: an operator result is pushed by
# `EBin.expr_Push_v0_Int24` (EBin.cs:1270-1274), which ORs the Int26 class tag into bits 26-28 with NO
# mask, and is read back as `(t0 << 6) >> 6` (EBin.cs:1682-1684). Overflow therefore does not truncate
# -- the high bits collide with the VariableSource field and the entry is re-read as a DIFFERENT
# variable class. (B_SYSVAR and B_CONST4 mask explicitly at EBin.cs:1232 / :1243, so those two
# TRUNCATE instead of corrupting; a bare terminal var token bypasses the push entirely and returns a
# full Int32 through getv, EBin.cs:1621-1687.) Ceiling: opcodes.EXPR_VALUE_MIN/MAX = +/-33,554,431.
#
# A docstring saying "mind the ceiling" is a wish (CLAUDE.md s7), so this is an INTERVAL EVALUATOR the
# lint gate runs over every declared expression. An operator or leaf it does not know RAISES -- it may
# not default to "probably fine", which is the exact defect shape `feedback-a-check-that-cannot-fail`
# names.
_EB_VARTYPE_BOUNDS = {           # EBin.GetVariableValueInternal, EBin.cs:1847-1876
    "Bit": (0, 1), "SByte": (-128, 127), "Byte": (0, 255),
    "Int16": (-32768, 32767), "UInt16": (0, 65535),
    # ONE case label covers Int24 AND UInt24 and casts the third byte to SByte (EBin.cs:1858-1861).
    "Int24": (-8388608, 8388607), "UInt24": (-8388608, 8388607),
}
_EB_MEMORIA_VAR_BOUNDS = {       # memoria_variable, EBin.cs:2416-2431 -> GetMemoriaCustomVariable :1689
    0: (0, 65535),               # TETRA_MASTER_WIN   -- SavedData.sWin
    3: (0, 65535),               # TETRA_MASTER_POINTS-- MiniGame_GetPlayerPoints (:185-199)
    4: (0, COLLECTOR_LEVEL_MAX),  # TETRA_MASTER_RANK -- MiniGame_GetCollectorLevel (:202-244)
    # TREASURE_HUNTER_POINTS -- the weighted popcount's arithmetic maximum over flags.TH_POINT_RANGES.
    5: (0, sum(w * 8 * (hi - lo + 1) for lo, hi, w in _flags.TH_POINT_RANGES)),
}
_EB_SYSVAR_BOUNDS = {            # EventEngine.GetSysvar.cs -- ONLY the codes the catalog uses
    6: (0, GIL_CAP),             # :31-32 party.gil, clamped at BattleCalculator.cs:61
    # :33-34 gStepCount. DEAD: one assignment repo-wide, `gStepCount = 0` (EventEngine.Initialize.cs:42).
    # The bound is (0,0) BECAUSE of that, not by convenience -- if the counter ever becomes live this
    # row's status changes and this bound must be revisited with it.
    7: (0, 0),
    16: (0, 65535),              # :51-52 Frogs.Number
    19: (0, 65535),              # :57-69 card count (the MaxCardCount remap -- unused by this catalog)
    20: (0, 8388607),            # :70-73 play time in SECONDS, clamped by the engine itself
}


class EbBoundsError(ValueError):
    """An expression whose value range cannot be bounded from the engine's own declarations."""


def eb_bounds(tokens: str) -> "tuple[int, int]":
    """Interval-evaluate an RPN token string -> ``(lo, hi)``, the value range it can ever produce.

    Deliberately NARROW: it knows exactly the leaves and operators this catalog uses and RAISES on
    anything else, so adding a new operator to a row forces a decision here instead of silently
    widening the envelope. ``tokens`` must NOT carry ``B_EXPR_END``."""
    import re as _re
    stack: list = []
    for tok in tokens.split():
        m = _re.match(r"^const4?\((-?\d+)\)$", tok)
        if m:
            v = int(m.group(1))
            stack.append((v, v))
            continue
        m = _re.match(r"^B_SYSVAR\[(\d+)\]$", tok)
        if m:
            c = int(m.group(1))
            if c not in _EB_SYSVAR_BOUNDS:
                raise EbBoundsError(f"B_SYSVAR[{c}]: no declared bound (EventEngine.GetSysvar.cs) -- "
                                    f"add one with its file:line rather than assuming a range")
            stack.append(_EB_SYSVAR_BOUNDS[c])
            continue
        m = _re.match(r"^(\w+)\.(\w+)\[(\d+)\]$", tok)
        if m:
            src, typ, idx = m.group(1), m.group(2), int(m.group(3))
            if src == "Null":                      # VariableSource.Null + Any -> memoria_variable
                if idx not in _EB_MEMORIA_VAR_BOUNDS:
                    raise EbBoundsError(f"{tok}: no declared bound for memoria_variable {idx}")
                stack.append(_EB_MEMORIA_VAR_BOUNDS[idx])
                continue
            if typ not in _EB_VARTYPE_BOUNDS:
                raise EbBoundsError(f"{tok}: no declared bound for VariableType {typ!r}")
            stack.append(_EB_VARTYPE_BOUNDS[typ])
            continue
        if tok == "B_HAVE_ITEM":                   # DoCalcOperationExt.cs:13-20 -> FF9Item_GetCount_Generic
            (arg,) = _pop(stack, 1, tok)
            # BAND-AWARE, because the band decides the range (ff9item.2.cs:417-432 / :226-232) and a
            # blanket over-approximation is not free: `_worst_case_width` pins each page's header
            # against these numbers, so a 4x-too-wide bound would widen every window for nothing.
            if arg[0] != arg[1]:
                raise EbBoundsError("B_HAVE_ITEM: the item id must be a CONSTANT to bound it")
            if ITEM_IMPORTANT_BASE <= arg[0] < ITEM_CARD_BASE:
                stack.append((0, 1))               # -> FF9Item_IsExistImportant (:229), a bool
            else:
                # regular -> FF9ITEM.count, a Byte; card -> deck entries of that id, capped by
                # Configuration.TetraMaster.MaxCardCount (QuadMistGame.cs:759). 255 covers both.
                stack.append((0, 255))
            continue
        if tok in ("B_GE", "B_GT", "B_LE", "B_LT", "B_EQ", "B_NE"):
            _pop(stack, 2, tok)
            stack.append((0, 1))
            continue
        if tok == "B_PLUS":
            b, a = _pop(stack, 2, tok)
            stack.append((a[0] + b[0], a[1] + b[1]))
            continue
        if tok == "B_MULT":
            b, a = _pop(stack, 2, tok)
            prod = [x * y for x in a for y in b]
            stack.append((min(prod), max(prod)))
            continue
        if tok in ("B_DIV", "B_REM", "B_SHIFT_RIGHT", "B_AND"):
            b, a = _pop(stack, 2, tok)
            if b[0] != b[1]:
                raise EbBoundsError(f"{tok}: the right operand must be a CONSTANT to bound it "
                                    f"statically (got {b})")
            k = b[0]
            if a[0] < 0:
                raise EbBoundsError(f"{tok}: the left operand can be negative ({a}) -- C# integer "
                                    f"division/shift/mask semantics on a negative are not bounded here")
            if tok == "B_DIV":
                if k <= 0:
                    raise EbBoundsError(f"B_DIV by {k}")
                stack.append((a[0] // k, a[1] // k))
            elif tok == "B_REM":
                if k <= 0:
                    raise EbBoundsError(f"B_REM by {k}")
                stack.append((0, k - 1))
            elif tok == "B_SHIFT_RIGHT":
                stack.append((a[0] >> k, a[1] >> k))
            else:
                stack.append((0, min(a[1], k if k >= 0 else a[1])))
            continue
        raise EbBoundsError(f"{tok!r}: eb_bounds has no rule for this token -- classify it (with the "
                            f"engine file:line) instead of letting the 26-bit gate widen silently")
    if len(stack) != 1:
        raise EbBoundsError(f"expression leaves {len(stack)} value(s), not 1")
    return stack[0]


def _pop(stack: list, n: int, tok: str) -> list:
    if len(stack) < n:
        raise EbBoundsError(f"{tok}: stack underflow ({len(stack)} value(s) available, needs {n})")
    return [stack.pop() for _ in range(n)]


def eb_eval(tokens: str, read) -> int:
    """Evaluate an RPN token string the way the engine would -- ``read(leaf_token)`` supplies every
    leaf. ``tokens`` must NOT carry ``B_EXPR_END``.

    THIS IS THE CROSS-VALIDATOR, and it is why it lives beside the expressions instead of in the
    tests. :func:`eb_bounds` is an INTERVAL evaluator and therefore correlation-blind: it reports
    ``minigame.hunt_winner`` as 0..255 because it cannot see that the multiplicand and the predicate
    are the SAME byte. Only evaluation over real inputs can show that the clamp actually folds every
    byte > 3 to row 0 -- and, more importantly, that each expression agrees with this module's own
    OFFLINE reader on the same gEventGlobal. Two implementations of one row, checked against each
    other offline, is the same bracket the rung-0 playtest applied in-game.

    Integer semantics follow C# (``/`` truncates toward zero), which for the non-negative operands
    this catalog uses is Python's ``//``."""
    import re as _re
    st: list = []
    for tok in tokens.split():
        m = _re.match(r"^const4?\((-?\d+)\)$", tok)
        if m:
            st.append(int(m.group(1)))
        elif tok == "B_PLUS":
            b, a = st.pop(), st.pop(); st.append(a + b)
        elif tok == "B_MULT":
            b, a = st.pop(), st.pop(); st.append(a * b)
        elif tok == "B_DIV":
            b, a = st.pop(), st.pop(); st.append(int(a / b) if b else 0)
        elif tok == "B_REM":
            b, a = st.pop(), st.pop(); st.append(a - int(a / b) * b if b else 0)
        elif tok == "B_AND":
            b, a = st.pop(), st.pop(); st.append(a & b)
        elif tok == "B_SHIFT_RIGHT":
            b, a = st.pop(), st.pop(); st.append(a >> b)
        elif tok in ("B_GE", "B_GT", "B_LE", "B_LT", "B_EQ", "B_NE"):
            b, a = st.pop(), st.pop()
            st.append(int({"B_GE": a >= b, "B_GT": a > b, "B_LE": a <= b, "B_LT": a < b,
                           "B_EQ": a == b, "B_NE": a != b}[tok]))
        elif tok == "B_HAVE_ITEM":
            st.append(read(f"B_HAVE_ITEM({st.pop()})"))
        else:
            st.append(read(tok))
    if len(st) != 1:
        raise EbBoundsError(f"eb_eval: expression leaves {len(st)} value(s), not 1")
    return st[0]


def eb_geg_reader(geg: bytes):
    """A ``read`` callback for :func:`eb_eval` backed by a gEventGlobal heap -- resolves
    ``Global.<Type>[i]`` exactly as ``EBin.GetVariableValueInternal`` does (EBin.cs:1847-1876). Any
    other leaf (a sysvar, a memoria_variable, an item probe) must be supplied by the caller through
    ``extra``, because it is NOT in the heap."""
    import re as _re

    def read(tok, extra=None):
        m = _re.match(r"^Global\.(\w+)\[(\d+)\]$", tok)
        if m:
            typ, idx = m.group(1), int(m.group(2))
            if typ == "Bit":
                return _bit(geg, idx)
            if typ == "Byte":
                return _u8(geg, idx)
            if typ == "UInt16":
                return _u16(geg, idx)
            if typ in ("Int24", "UInt24"):
                return _i24s(geg, idx)
            raise EbBoundsError(f"eb_geg_reader: no rule for VariableType {typ!r}")
        raise EbBoundsError(f"eb_geg_reader: {tok!r} is not a gEventGlobal read -- supply it yourself")
    return read


def _attach_eb(spec: "RowSpec") -> "RowSpec":
    """Write the in-game half onto a RowSpec. A row in NEITHER table keeps both fields None, which
    :func:`lint_rows` refuses -- there is no third state to default into."""
    from dataclasses import replace as _replace
    if spec.id in EB_EXPRESSIONS:
        toks, src = EB_EXPRESSIONS[spec.id]
        scale, unit = EB_SCALE.get(spec.id, (1, ""))
        return _replace(spec, eb=toks, eb_source=src, eb_scale=scale, eb_unit=unit)
    if spec.id in EB_ABSENT:
        return _replace(spec, eb_absent=EB_ABSENT[spec.id])
    return spec


ROWS = [_attach_eb(r) for r in ROWS]

_ROWS_BY_ID = {r.id: r for r in ROWS}

# Rows whose reader can populate `names` (a claim about the reader BODY, which no schema field expresses).
# lint_rows() requires each of these to declare a name_source -- the guard behind THE NAMES LAW.
NAME_BEARING_ROWS = ("party.key_items",)


def row_spec(rid):
    """The :class:`RowSpec` for a row id, or None."""
    return _ROWS_BY_ID.get(rid)


# ============================ the loader ============================
def _nodes_from_extra(path):
    """``(common, minigame, event, setting)`` from a Memoria extra file, or four Nones if it isn't one.
    READ-ONLY: only :func:`save_items.load_extra_common` (the parse) is used -- no write surface is
    imported anywhere in this module."""
    from .save_items import load_extra_common
    common, root, _ = load_extra_common(path)
    if common is None:
        return None, None, None, None
    return (common, _sj.get_path(root, "30000_MiniGame"), _sj.get_path(root, "20000_Event"),
            _sj.get_path(root, "95000_Setting"))


def _pad(blob: bytes) -> bytes:
    """gEventGlobal is a 2048-byte engine array (EventState.cs:10); tolerate a short blob, truncate a long."""
    b = bytes(blob)
    return (b + b"\x00" * (2048 - len(b)))[:2048] if len(b) < 2048 else b[:2048]


def load_state(path) -> list:
    """Locate everything a journal read needs, per save slot -- ``[JournalState, ...]``.

    Mirrors :func:`save.inspect` (save.py:240-265) including its EXTRA-FIRST rule: Memoria writes a
    per-slot extra file holding the AUTHORITATIVE gEventGlobal and RESTORES from it on load, so when the
    extra exists THAT is the state the game uses and the main block is stale. Accepts, in order:

      1. a Memoria plaintext extra file -> one state with all four nodes;
      2. an encrypted ``SavedData_ww.dat`` container -> one state per populated block, each preferring its
         extra and otherwise falling back to the decrypted main block (gil + key items only, and only when
         :func:`save_items.validate_main_block` passes -- a differently-laid-out save is refused, not
         mis-read);
      3. an open save JSON / a bare Base64 gEventGlobal -> one state with the heap only (every
         extra-backed row then reads ``unavailable``).

    Strictly read-only: nothing here opens a file for writing.
    """
    p = str(path)
    if p.lower().endswith(".dat"):
        common, minigame, event, setting = _nodes_from_extra(p)
        if common is not None:                            # case 1: the path IS an extra file
            blob = _save.read_extra_gEventGlobal(p)
            return [JournalState("Memoria extra-save", _pad(blob or b""),
                                 "extra" if blob else "loose", common, minigame, event, setting)]
        from .save_items import validate_main_block       # READ-side gate only (no write surface imported)
        sv = _save.FF9Save.load(p)                        # case 2: the encrypted container
        out = []
        for s in sv.populated():
            extra = _save.extra_file_path(p, s.block)
            has_extra = bool(extra and os.path.isfile(extra))
            eblob = _save.read_extra_gEventGlobal(extra) if has_extra else None
            common, minigame, event, setting = _nodes_from_extra(extra) if has_extra else (None,) * 4
            main_pt = None
            if common is None:                            # a VANILLA slot -> the main block is the store
                try:
                    pt = sv._decrypt_block(s.block)       # same private accessor save_items._decrypt_main uses
                    validate_main_block(pt)
                    main_pt = pt
                except (ValueError, IndexError):
                    main_pt = None                        # not this install's old-format layout -> refuse it
            geg = eblob if eblob is not None else sv.gEventGlobal(s.block)
            out.append(JournalState(
                _save._slot_label(s) + (" · Memoria extra" if common is not None else " · main (vanilla)"),
                _pad(geg), "extra" if eblob is not None else "main", common, minigame, event, setting,
                main_pt))
        if not out:
            raise ValueError("no populated save slots found in this file")
        return out
    return [JournalState("gEventGlobal", _pad(_flags.gEventGlobal_from_save(p)), "loose")]  # case 3


# ============================ the resolver ============================
def _resolve(spec: RowSpec, state: JournalState) -> JournalRow:
    """One RowSpec + one save -> one JournalRow. A spec with no reader (untracked / dead / derived) never
    invents a value.

    TWO DIFFERENT FACTS, TWO DIFFERENT STATUSES -- this is the whole point of the split:

      * the reader RETURNS ``None`` -> ``unavailable``. It looked, the store is not in this save
        (a vanilla slot with no Memoria extra, a migrated save with an empty ``kills_per_model``).
        Expected, benign, and the row says so.
      * the reader RAISES -> ``error``, with the exception text kept ON the row. That is OUR code
        failing on a shape we did not anticipate, and it must not be able to hide inside the benign
        status. It used to: the old ``except (IndexError, KeyError, TypeError, ValueError,
        AttributeError): got = None`` made a truncated main block (``read_main_keyitems`` walking off
        the end, save_items.py:1010-1019) render as "this save has no such store" -- indistinguishable
        from a vanilla slot, on a row that would otherwise have reported a number.

    The catch is now BROADER, not narrower (bare ``Exception``): the old tuple let anything else --
    ``struct.error``, a ``UnicodeDecodeError`` from a name table, a ``RecursionError`` -- take the whole
    report down. One bad row must degrade one row.
    """
    row = JournalRow(id=spec.id, category=spec.category, label=spec.label, value=None,
                     denominator=spec.denom, provenance=spec.provenance, status=spec.status,
                     source=spec.source, note=spec.note, exclusive_group=spec.exclusive_group,
                     run_mode=spec.run_mode, blocked_by=spec.blocked_by)
    if spec.read is None:
        return row
    try:
        got = spec.read(state)
    except Exception as e:                                # noqa: BLE001 -- see the docstring
        row.status = "error"
        row.error = f"{type(e).__name__}: {e}"
        return row
    if got is None:
        row.status = "unavailable"
        return row
    row.status = "tracked"
    row.value = got.value
    row.detail = got.detail
    row.names = list(got.names)
    if got.denominator is not None:
        row.denominator = got.denominator
    return row


def _index_rows(rows) -> list:
    """The rows meta.index scores: tracked, with a denominator, and neither exclusive nor run-mode gated."""
    return [r for r in rows
            if r.status == "tracked" and r.denominator not in (None, 0) and r.value is not None
            and r.exclusive_group is None and r.run_mode is None and r.id != "meta.index"]


def build_report(state: JournalState) -> JournalReport:
    """Resolve every :data:`ROWS` entry against one save -- the Qt-free, str-free seam a later Journal
    panel and a later in-game screen both hang off."""
    rows = [_resolve(spec, state) for spec in ROWS]
    scored = _index_rows(rows)
    idx = next((r for r in rows if r.id == "meta.index"), None)
    if idx is not None:
        if scored:
            got = sum(max(0, min(r.value, r.denominator)) for r in scored)
            tot = sum(r.denominator for r in scored)
            idx.value = int(round(100.0 * got / tot)) if tot else 0
            n_hidden = sum(1 for r in rows if r.status in ("untracked", "dead"))
            idx.detail = f"{len(scored)} scored row(s), {n_hidden} not tracked by the game"
        else:
            idx.status = "unavailable"
    return JournalReport(state.label, rows)


def reports(path) -> list:
    """``[JournalReport, ...]`` -- :func:`load_state` + :func:`build_report` for every populated slot."""
    return [build_report(st) for st in load_state(path)]


# ============================ rendering ============================
def _fmt_value(r: JournalRow) -> str:
    if r.status == "untracked":
        return "not tracked by the game"
    if r.status == "dead":
        return "not tracked by the game (counter never increments)"
    if r.status == "unavailable":
        return "-- (this save has no such store)"
    if r.status == "error":
        # DELIBERATELY UGLY. "this save has no such store" was a plausible-looking line that hid a
        # crash in our own reader; a broken reader must not be able to pass for a benign one.
        return "!! READER FAILED"
    v = f"{r.value:,}" if abs(r.value) >= 10000 else str(r.value)
    if r.denominator is None:
        return v
    pct = r.pct
    return f"{v}/{r.denominator:,}" + (f"  {pct:.0f}%" if pct is not None else "")


def render_report(rep: JournalReport, *, category=None, show_all: bool = False) -> str:
    """A human-readable completion journal. By default only rows this save can actually report are shown;
    ``show_all`` adds the untracked + dead rows (what the game does NOT keep). ``category`` filters."""
    head = f"FF9 completion journal -- {rep.label}"
    L = [head, "=" * len(head)]
    # THE BROKEN-READER BANNER, above everything, regardless of --category. A reader that raised is a
    # kit bug; burying it inside the section it belongs to is how it stayed invisible.
    if rep.broken:
        L.append(f"!! {len(rep.broken)} ROW READER(S) FAILED -- this is a kit bug, not missing save "
                 f"state:")
        for r in rep.broken:
            L.append(f"     {r.id} ({r.source or 'kit-derived'}): {r.error}")
        L.append("")
    hidden = [r for r in rep.rows if r.status in ("untracked", "dead")]
    for cat in CATEGORIES:
        if category and cat != category:
            continue
        rows = [r for r in rep.rows if r.category == cat
                and (show_all or r.status not in ("untracked", "dead"))]
        if not rows:
            continue
        L.append(cat)
        for r in rows:
            line = f"  {r.label:<32} {_fmt_value(r)}"
            if r.status == "error":
                line += f"   {r.error}"                    # the exception text, on the row itself
            elif r.detail:
                line += f"   {r.detail}"
            L.append(line)
    if not category and hidden and not show_all:
        L.append(f"  ({len(hidden)} row(s) not tracked by the game -- `--all` to list them)")
    return "\n".join(L)


def diff_reports(a: JournalReport, b: JournalReport) -> JournalDiff:
    """A -> B: only the rows whose VALUE moved. A row that goes tracked -> unavailable is NOT a decrease
    (the store vanished, the progress did not), so it is skipped."""
    bi = {r.id: r for r in b.rows}
    changed = []
    for ra in a.rows:
        rb = bi.get(ra.id)
        if rb is None or ra.status != "tracked" or rb.status != "tracked":
            continue
        if ra.value != rb.value:
            changed.append((ra, rb))
    return JournalDiff(a.label, b.label, changed)


def render_diff(d: JournalDiff) -> str:
    L = ["FF9 completion journal diff (A -> B)", "=" * 36, f"A: {d.label_a}", f"B: {d.label_b}", ""]
    if d.empty:
        L.append("(no completion-state difference)")
        return "\n".join(L)
    for ra, rb in d.changed:
        den = f"/{rb.denominator}" if rb.denominator is not None else ""
        L.append(f"  {rb.label:<32} {ra.value}{den}  ->  {rb.value}{den}  ({rb.value - ra.value:+d})")
    return "\n".join(L)


# ============================ export + the schema gate ============================
def rows_json(rep: "JournalReport | None" = None) -> list:
    """``[dict, ...]`` -- the catalog seed. With a report, the RESOLVED rows; without one, the bare
    :data:`ROWS` definitions (no save, no install needed). Callables are never included: a RowSpec's
    ``read`` is dropped so the output is pure JSON."""
    if rep is not None:
        return [asdict(r) for r in rep.rows]
    out = []
    for s in ROWS:
        d = {k: v for k, v in asdict(s).items() if k != "read"}
        out.append(d)
    return out


_SOURCE_RE = re.compile(r"^[\w./]+\.(cs|py|md):\d+")


def lint_rows(rows=None) -> list:
    """Validate the row table's SCHEMA -- returns a list of violation strings (empty == green).

    This is the gate ``journal lint`` runs (exit 2 on any violation), so it is a CI-usable check that a
    future row cannot quietly break the contract ``journal rows --json`` promises. Rules:

      * ids unique; category / provenance / store from the declared tuples, and ``status`` from
        :data:`DECLARABLE_STATUSES` (``unavailable`` / ``error`` are RESOLVE-time outcomes);
      * ``source`` matches ``file.ext:line`` -- empty only for a kit-derived row;
      * ``denom is None`` XOR ``denom_source`` set;
      * ``blocked_by`` set iff the row is ``untracked``;
      * an untracked / dead row has NO reader; every other row has one unless it is kit-derived;
      * any denominator taken from :data:`ENGINE_TARGETS` still equals the transcribed value;
      * ``name_source`` is set on every row that can ever return names;
      * EXACTLY ONE of ``eb`` / ``eb_absent`` -- the in-game exhaustiveness gate (see below);
      * THE UNIT LAW -- ``eb_scale`` / ``eb_unit`` set together, never on an eb-less row, so an
        expression that publishes a DIFFERENT unit from its offline reader has to say so
        (:data:`EB_SCALE`).
    """
    from .eb import exprasm as _exprasm, exprsem as _exprsem
    rows = ROWS if rows is None else rows
    bad = []
    seen = set()
    targets_by_line = {src: val for val, src in ENGINE_TARGETS.values()}
    for r in rows:
        if r.id in seen:
            bad.append(f"{r.id}: duplicate row id")
        seen.add(r.id)
        if r.category not in CATEGORIES:
            bad.append(f"{r.id}: category {r.category!r} not in CATEGORIES")
        if r.provenance not in PROVENANCE:
            bad.append(f"{r.id}: provenance {r.provenance!r} not in PROVENANCE")
        if r.status not in DECLARABLE_STATUSES:
            # `unavailable` and `error` are RESOLVE-TIME outcomes -- a row that declared either would
            # be claiming a fact about a save it has not read.
            bad.append(f"{r.id}: status {r.status!r} not in DECLARABLE_STATUSES "
                       f"{DECLARABLE_STATUSES}")
        if r.store not in STORES:
            bad.append(f"{r.id}: store {r.store!r} not in STORES")
        if r.source:
            if not _SOURCE_RE.match(r.source):
                bad.append(f"{r.id}: source {r.source!r} is not a file.ext:line citation")
        elif r.provenance != "kit-derived":
            bad.append(f"{r.id}: source is empty but the row is not kit-derived")
        if (r.denom is None) == bool(r.denom_source):
            bad.append(f"{r.id}: denom / denom_source must be set together (got {r.denom!r} / "
                       f"{r.denom_source!r})")
        if (r.status == "untracked") != bool(r.blocked_by):
            bad.append(f"{r.id}: blocked_by is required iff status == 'untracked'")
        if r.status in ("untracked", "dead"):
            if r.read is not None:
                bad.append(f"{r.id}: an {r.status} row must have no reader")
        elif r.read is None and r.provenance != "kit-derived":
            bad.append(f"{r.id}: a {r.status} row needs a reader (or must be kit-derived)")
        # A denominator citing an AchievementInfo line must still equal the transcribed target -- this is
        # what stops a plausible-looking edit from silently re-hanging a wrong /N on a row.
        if r.denom_source in targets_by_line and r.denom != targets_by_line[r.denom_source]:
            bad.append(f"{r.id}: denom {r.denom} != the transcribed target "
                       f"{targets_by_line[r.denom_source]} at {r.denom_source}")
        if r.name_source is not None and r.provenance != "live-install":
            bad.append(f"{r.id}: name_source is only meaningful on a live-install row")

        # --- THE IN-GAME EXHAUSTIVENESS GATE (T1b) --------------------------------------------
        # EXACTLY ONE of `eb` / `eb_absent`. There is deliberately no third state, so a row added
        # later cannot default to "invisible in-game" the way an unclassified operator used to
        # default to "safe" (eb/exprsem.py:8-13). "I forgot" and "there is nothing to read" are
        # indistinguishable to a reader, and both must be LOUD.
        if (r.eb is None) == (r.eb_absent is None):
            bad.append(f"{r.id}: declare EITHER an eb expression (journal.EB_EXPRESSIONS) OR a "
                       f"reason (journal.EB_ABSENT) -- exactly one, never neither and never both")
        if r.eb is not None:
            if not r.eb_source:
                bad.append(f"{r.id}: eb without eb_source (cite the engine read it replicates)")
            elif not _SOURCE_RE.match(r.eb_source):
                bad.append(f"{r.id}: eb_source {r.eb_source!r} is not a file.ext:line citation")
            if "B_EXPR_END" in r.eb.split():
                bad.append(f"{r.id}: drop B_EXPR_END -- the emitter appends the 0x7F terminator")
            # `exprasm.assemble` is a byte ENCODER and validates nothing (eb/exprsem.py:5-6);
            # `analyze` is the validator. Run both, so a malformed row fails `journal lint`
            # (exit 2, CI-usable) before any field references it.
            try:
                a = _exprsem.analyze(r.eb + " B_EXPR_END")
            except _exprsem.ExprSemanticError as e:
                bad.append(f"{r.id}: eb does not evaluate: {e}")
            else:
                if a.unsafe_to_repeat:
                    # A page body is not a per-frame hud, but a journal row still READS: a write
                    # here would corrupt save state once per page open instead of once per frame,
                    # and only one of those is not a corruption. Same classifier, one owner.
                    bad.append(f"{r.id}: eb carries "
                               f"{sorted({s.token for s in a.unsafe_to_repeat})} -- a journal row READS")
            try:
                _exprasm.assemble(r.eb + " B_EXPR_END")
            except Exception as e:                              # AssembleError (a ValueError)
                bad.append(f"{r.id}: eb does not assemble: {e}")
            try:
                lo, hi = eb_bounds(r.eb)
            except EbBoundsError as e:
                bad.append(f"{r.id}: eb value range is not bounded: {e}")
            else:
                from .eb.opcodes import EXPR_VALUE_MAX as _EVMAX, EXPR_VALUE_MIN as _EVMIN
                if not (_EVMIN <= lo and hi <= _EVMAX):
                    bad.append(f"{r.id}: eb can produce {lo}..{hi}, outside the 26-bit expression "
                               f"envelope {_EVMIN}..{_EVMAX} (EBin.cs:1270-1274) -- divide INSIDE "
                               f"the expression")
            # The Int24 sign-extension bites ONLY at a full field (23 -> 8388607, 24 -> -1), which
            # no playtest can surface. So it is guarded HERE, structurally: a raw Int24/UInt24 read
            # may only be published masked. `_bit_popcount` avoids the read entirely; this rule
            # exists for whoever later "optimises" a popcount back into one word.
            toks = r.eb.split()
            # THE UNIT LAW, at the exact site the defect appeared. An expression that DIVIDES has
            # almost certainly stopped publishing its offline reader's unit, and declaring nothing is
            # how `journal report` and the field page came to print 27733 and 7 for one row id. The
            # rule is narrow on purpose: B_SHIFT_RIGHT is NOT in it, because ragtime_quiz shifts to
            # EXTRACT a bitfield (which its offline reader does too), so a shift says nothing about
            # units either way. A divider whose reader divides identically declares that in
            # EB_DIV_SAME_UNIT -- a written reason, never silence.
            if "B_DIV" in toks and r.eb_scale == 1 and r.id not in EB_DIV_SAME_UNIT:
                bad.append(f"{r.id}: eb divides but declares eb_scale 1 -- say what that does to the "
                           f"unit its offline reader publishes (journal.EB_SCALE), or record in "
                           f"journal.EB_DIV_SAME_UNIT why the two still agree")
            for i, t in enumerate(toks):
                if re.match(r"^\w+\.U?Int24\[\d+\]$", t) and toks[i + 1:i + 3] != ["const4(16777215)",
                                                                                   "B_AND"]:
                    bad.append(f"{r.id}: {t} must be followed by `const4(16777215) B_AND` -- BOTH "
                               f"Int24 and UInt24 sign-extend the third byte (one case label, "
                               f"EBin.cs:1858-1861), so a full field reads -1")
        if r.status == "untracked" and r.eb is not None:
            # untracked == no save-side read at ANY tier; an .eb path would contradict blocked_by.
            bad.append(f"{r.id}: an untracked row cannot declare an eb expression")

        # --- THE UNIT LAW ------------------------------------------------------------------------
        # The two renderers publish ONE number per row id -- that is the bet. `eb_scale` is the only
        # way to opt out of it, and opting out is a DECLARATION: the scale is cross-checked
        # numerically against the offline reader and the unit is what the in-game page prints after
        # the value. An undeclared unit change (an .eb dividing where the reader does not) is how
        # `journal report` and the field screen came to publish 27733 and 7 for the same row.
        if not isinstance(r.eb_scale, int) or isinstance(r.eb_scale, bool) or r.eb_scale < 1:
            bad.append(f"{r.id}: eb_scale must be an int >= 1 (got {r.eb_scale!r})")
        elif (r.eb_scale != 1) != bool(r.eb_unit):
            bad.append(f"{r.id}: eb_scale / eb_unit must be set together -- an eb that publishes a "
                       f"DIFFERENT unit from the offline reader must name that unit (got scale "
                       f"{r.eb_scale!r} / unit {r.eb_unit!r}; declare it in journal.EB_SCALE)")
        if r.eb is None and (r.eb_scale != 1 or r.eb_unit):
            bad.append(f"{r.id}: eb_scale / eb_unit are meaningless without an eb expression")
    # The rows whose readers can ever populate `names` must declare where those names come from. Kept as
    # an explicit list because it is a claim about the READER bodies, which no schema field can express.
    by_id = {r.id: r for r in rows}
    for rid in NAME_BEARING_ROWS:
        s = by_id.get(rid)
        if s is not None and not s.name_source:
            bad.append(f"{rid}: returns display names but declares no name_source")
    # ...and the gate's other half: a decision that no longer has a row. Without this an id RENAME
    # orphans its expression silently and the renamed row falls back into the "neither" state, which
    # the per-row rule above would then blame on the wrong edit.
    if rows is ROWS:
        both = set(EB_EXPRESSIONS) & set(EB_ABSENT)
        for rid in sorted(both):
            bad.append(f"{rid}: appears in BOTH EB_EXPRESSIONS and EB_ABSENT")
        for rid in sorted((set(EB_EXPRESSIONS) | set(EB_ABSENT) | set(EB_SCALE)
                           | set(EB_DIV_SAME_UNIT)) - set(by_id)):
            bad.append(f"{rid}: EB_EXPRESSIONS/EB_ABSENT/EB_SCALE names a row that is not in ROWS")
        # ...and a scale whose expression was deleted: the row would fall back to scale 1 SILENTLY,
        # i.e. back to "the two renderers agree" with nothing having checked that they do.
        for rid in sorted(set(EB_SCALE) - set(EB_EXPRESSIONS)):
            bad.append(f"{rid}: EB_SCALE names a row with no EB_EXPRESSIONS entry -- a scale without "
                       f"an expression converts nothing")
    return bad
