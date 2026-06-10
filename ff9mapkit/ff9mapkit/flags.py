"""FF9 story-flag registry + save inspector (the NAME / VIEW / UNDERSTAND layer).

FF9 keeps all save-persistent story state in one place: ``EventState.gEventGlobal``, a 2048-byte array
(the engine's ``VariableSource.Global`` space, Base64'd into the save JSON under key ``"gEventGlobal"``,
``JsonParser.cs:522,579``). This module is the kit's canonical map of that heap -- grounded in the
Memoria source + a 676-field census (see ``research/STORY_FLAGS.md``). It does three things:

1. **NAME** -- a registry of FF9's known named vars / reserved regions / scenario milestones, plus
   author-side name resolution so a ``field.toml`` can gate on a *named* flag instead of a raw index
   (a ``[[flag]]`` table: ``[[flag]] name = "switch_pulled" index = 8520``).
2. **CREATE-safely** -- the provably-safe allocation band (``FIRST_SAFE_FLAG`` = 8512, the first bit
   clear of ALL real-FF9 usage; the chest band 8376-8511 + the choice scratch are reserved). These
   constants are the single source of truth (``campaign.py`` imports them).
3. **VIEW / UNDERSTAND** -- decode a save's ``gEventGlobal`` blob into a human report (ScenarioCounter
   + nearest story beat, FieldEntrance, treasure-hunter points, opened-chest count, set story bits
   annotated by region).

Addressing reminder (engine ``EBin.GetVariableValueInternal``): a **Bit** index N -> byte ``N>>3`` bit
``N&7``; a **Byte/Int16/UInt16** index is a raw byte offset. So "bit 184" = byte 23, but "byte 184" is a
different location -- the registry keeps the two kinds apart.
"""
from __future__ import annotations

import base64
import difflib
import json
import struct
from dataclasses import dataclass, field

# --- the provably-safe story-flag allocation band (single source of truth; campaign.py imports these) ---
# Real FF9 uses save-persistent bit-flags up to bit 8511 (the treasure-chest "opened" bitfield, bits
# 8376-8511). The choice-visibility scratch sits at byte 2040 = bits 16320+. So custom story flags MUST
# live in [8512, 16320). 8512 (start of byte 1064) is the first bit clear of ALL real-FF9 usage.
FIRST_SAFE_FLAG = 8512
CHEST_FLAG_LO, CHEST_FLAG_HI = 8376, 8511      # real-FF9 treasure-chest "opened" bitfield
CHOICE_SCRATCH_FLOOR = 16320                   # byte 2040: engine/kit-owned choice mask scratch


# ============================ the registry ============================
@dataclass(frozen=True)
class WordVar:
    """A named multi-byte var at a fixed BYTE offset (ScenarioCounter, FieldEntrance, ...)."""
    name: str
    byte: int          # starting byte offset
    width: int         # bytes (1, 2)
    signed: bool
    meaning: str
    tier: str          # a=engine-grounded, b=empirical, c=uncertain
    source: str


@dataclass(frozen=True)
class BitRegion:
    """A named/reserved range of BIT indices (worldmap unlocks, chest block, byte-23 handshake, ...)."""
    name: str
    lo: int            # inclusive bit index
    hi: int            # inclusive bit index
    meaning: str
    reserved: bool     # a mod must NOT allocate here
    tier: str
    source: str


# Named word vars (byte-addressed). Order: low offsets first.
NAMED_WORDS = [
    WordVar("ScenarioCounter", 0, 2, False, "Master story-progress value (1..12000).", "a",
            "EventState.cs:16-24; EBin.cs:34"),
    WordVar("FieldEntrance", 2, 2, True, "Last entrance / arrival map index (read by every field).", "a",
            "EventState.cs:26-34; EBin.cs:35"),
    WordVar("TranceGaugeFlag", 16, 1, False, "Trance gauge enable (0/1).", "a", "battle.cs:38"),
    WordVar("GarnetSummonAvailable", 17, 2, False, "Garnet summon depression/reserve state.", "a",
            "battle.cs:39-40"),
    WordVar("ChocoDigLevel", 191, 1, False, "Choco's dig ability level (set to 5 at milestones).", "a",
            "ChocographUI.cs:245; EMinigame.cs:454"),
]

# Reserved / named BIT regions (bit-addressed). A mod must not allocate into a reserved region.
# Specific named bits are listed BEFORE the broad band they sit inside, so bit_region() resolves the
# precise name first (e.g. bit 815 -> "mognet_central_discovered", not the broad "worldmap_unlocks").
BIT_REGIONS = [
    BitRegion("field_menu_guard", 184, 184, "Engine handshake: 'in-field menu/transition in progress'. "
              "Re-checked + cleared every Main_Init.", True, "a", "disassembly fields 50/100/300"),
    BitRegion("boot_scratch", 191, 191, "Companion scratch bit zeroed on every boot.", True, "a",
              "disassembly"),
    BitRegion("chocobo_paradise_discovered", 814, 814, "Chocobo's Paradise discovered (byte 101 & 0x40); "
              "gates its world-map alternate form.", True, "a", "WorldConfiguration.cs:183-184"),
    BitRegion("mognet_central_discovered", 815, 815, "Mognet Central discovered (byte 101 & 0x80); gates its "
              "world-map alternate form. The only engine-grounded Mognet bit in gEventGlobal.", True, "a",
              "WorldConfiguration.cs:183-184"),
    BitRegion("worldmap_unlocks", 736, 823, "Worldmap/Navi cursor + location-unlock/first-visit bits "
              "(consumed by engine C#; mostly write-only on the field side).", True, "a/b",
              "ff9.cs:2259-2333; census"),
    BitRegion("chest_opened", CHEST_FLAG_LO, CHEST_FLAG_HI, "Global treasure-chest 'opened' bitfield "
              "(48 chest fields, every bit a 48-writer computed index -> per-chest identity is NOT static). "
              "NEVER allocate here.", True, "a/b", "census; EventState.GetTreasureHunterPoints"),
    BitRegion("choice_scratch", CHOICE_SCRATCH_FLOOR, CHOICE_SCRATCH_FLOOR + 15,
              "Choice-visibility mask scratch (kit MASK_SCRATCH_IDX); engine/kit-owned.", True, "a", "region.py:57"),
]

# Informational (NON-reserved) named story-flag clusters from the 676-field census: contiguous bit bands
# named by their dominant writer area, for ANNOTATING a decoded save's set bits (not for allocation -- they
# sit below FIRST_SAFE_FLAG anyway). These are "where these flags are written from", not a proven per-bit
# meaning. Derived + verified by the ff9-understand-layer workflow (research/gen_understand_layer.py).
STORY_REGIONS = [
    BitRegion("hilda_garde_invincible_events", 196, 199, "Late-game airship/event flags "
              "(Lindblum Castle / Hilda Garde 3 / Invincible).", False, "c", "census"),
    BitRegion("chocobo_dig_state", 848, 853, "Chocobo Hot & Cold / Chocograph minigame state.", False, "b",
              "census; EMinigame.cs"),
    BitRegion("chocobo_forest_state", 888, 895, "Chocobo Hot & Cold dig-spot / chocograph-found bits.", False,
              "b", "census; EMinigame.cs"),
    BitRegion("chocograph_found_opened", 1040, 1087, "Chocograph 'found'/'opened' treasure bitfields "
              "(choco-dig minigame).", False, "b", "census; ChocographUI.cs"),
    BitRegion("chocobo_garden_state", 1156, 1159, "Chocobo Hot & Cold dig-progress flags.", False, "c", "census"),
    BitRegion("chocobo_air_garden_state", 1416, 1423, "Chocobo Hot & Cold / Air Garden unlock state "
              "(top of the choco-dig band, bytes 106-177).", False, "c", "census"),
    BitRegion("oeilvert_events", 1816, 1816, "Oeilvert ruin event/progress flag (single Oeilvert-only bit).",
              False, "b", "census"),
    BitRegion("dali_madain_iifa_events", 2048, 2128, "Early-mid story band (Dali / Madain Sari / Iifa Tree).",
              False, "b", "census"),
    BitRegion("prima_vista_evil_forest_events", 2418, 2495, "Prologue band (Prima Vista / Evil Forest / North "
              "Gate). NB: corrects the report's 'Lindblum festival @ 304-335' -- those bits are the prologue; "
              "the Hunt-Festival score is the separate UInt16 words at bytes 314/316.", False, "b", "census"),
    BitRegion("lindblum_events", 2592, 2663, "The true Lindblum cluster (25 Lindblum fields; town/festival "
              "event flags).", False, "b", "census"),
    BitRegion("disc2_3_dungeon_events", 2817, 2983, "Disc-2/3 dungeon/town band (Treno / Conde Petie / Bran "
              "Bal / Black Mage Village).", False, "b", "census"),
    BitRegion("outer_continent_events", 3228, 3263, "Outer-Continent traversal (Mount Gulug / Fossil Roo / "
              "Qu's Marsh).", False, "b", "census"),
    BitRegion("ipsen_ice_cavern_events", 3457, 3471, "Mixed: Ipsen's Castle + Ice Cavern (name with caution).",
              False, "c", "census"),
    BitRegion("desert_palace_lindblum_events", 3536, 3671, "Disc-3 Kuja-stronghold + Hilda-search flags "
              "(Desert Palace / Lindblum Castle).", False, "b", "census"),
    BitRegion("alexandria_events", 3712, 3718, "Alexandria-town event flags (clean single-area cluster).",
              False, "b", "census"),
    BitRegion("cleyra_alexandria_gizamaluke_events", 3784, 3905, "Disc-2 Burmecia-war / Cleyra-assault arc "
              "(Cleyra / Alexandria / Gizamaluke's Grotto).", False, "b", "census"),
    BitRegion("alexandria_castle_events", 3948, 3967, "Alexandria Castle interior event flags.", False, "c",
              "census"),
    BitRegion("mognet_central_state", 4046, 4047, "Mognet (moogle-mail) sidequest progress -- written only by "
              "Mognet Central (field 3100). Dominant-writer inference; exact per-bit meaning empirical.", False,
              "c", "census"),
]

# UNDERSTAND note (ff9-understand-layer workflow, engine-verified): ATE ("Active Time Event") seen-state is
# NOT in this 2048-byte heap -- it lives in AchievementState.AteCheck (Int32[100], save key "AteCheckArray").
# ATE selection is a per-field .eb script branch keyed on (fldLocNo, fldMapNo, ScenarioCounter, chosen choice)
# via the hardcoded EMinigame.MappingATEID switch. So there is NO gEventGlobal "ATE flag index" to name.
ATE_STATE_LOCATION = "AchievementState.AteCheck (Int32[100], save key 'AteCheckArray') -- not gEventGlobal"

# Treasure-Hunter scoring byte ranges (EventState.GetTreasureHunterPoints): (byte_lo, byte_hi, weight).
TH_POINT_RANGES = [(896, 960, 1), (966, 975, 1), (182, 186, 2)]

# ScenarioCounter -> story AREA progression: the value where the game enters each area, derived from a
# field-granular census x field-manifest join (research/gen_understand_layer.py: each value -> its setter
# field -> that field's manifest room) and curated/verified by the ff9-understand-layer workflow (3
# adversarial lenses + research). Use nearest_milestone(sc) for "what story beat is this". In-game-validated
# (SC 7200 -> Alexandria Castle). This 52-anchor table supersedes the earlier 43-anchor zone-coded one, which
# mislabelled several beats (5900 was "Iifa Tree" -> really Fossil Roo; 9990 "Outer Continent" -> Mount Gulug;
# 9400 "Hilda Garde" -> Blue Narciss; 11610 "Crystal World" -> Memoria) and lost real beats (Burmecia, Oeilvert,
# the second shrine, Pandemonium, Memoria).
SCENARIO_MILESTONES = {
    1000: "Prima Vista", 2020: "Evil Forest", 2300: "Evil Forest", 2500: "Ice Cavern",
    2600: "Dali", 2700: "Dali (underground)", 2800: "Observatory Mountain", 2910: "Cargo Ship",
    3000: "Lindblum Castle", 3100: "Lindblum", 3710: "Gizamaluke's Grotto", 3750: "South Gate",
    3800: "Burmecia", 4445: "Treno", 4500: "Gargan Roo", 4600: "Alexandria Castle",
    4650: "Cleyra", 4990: "Red Rose", 5030: "Alexandria Castle", 5510: "Pinnacle Rocks",
    5660: "Lindblum", 5900: "Fossil Roo", 6100: "Conde Petie", 6300: "Conde Petie Mountain Path",
    6600: "Madain Sari", 6700: "Iifa Tree", 6800: "Madain Sari", 6900: "Iifa Tree",
    7010: "Alexandria", 7200: "Alexandria Castle", 7550: "Treno", 8000: "Alexandria",
    8400: "Alexandria Castle", 9000: "Lindblum", 9400: "Blue Narciss", 9510: "Desert Palace",
    9605: "Oeilvert", 9800: "Desert Palace", 9990: "Mount Gulug", 10000: "Lindblum Castle",
    10400: "Alexandria Castle", 10500: "Ipsen's Castle", 10600: "Hilda Garde 3", 10620: "Water Shrine",
    10670: "Earth Shrine", 10830: "Terra", 10900: "Bran Bal", 10930: "Pandemonium",
    11100: "Invincible", 11610: "Memoria", 11765: "Crystal World", 12000: "Crystal World (ending)",
}
# IsEikoAbducted (EventState.cs:36): 9860 <= ScenarioCounter < 9990.
EIKO_ABDUCTED_LO, EIKO_ABDUCTED_HI = 9860, 9989


def bit_to_byte(bit: int) -> tuple:
    """Bit index -> (byte, bit-within-byte). Engine: byte = bit>>3, bit = bit&7."""
    return (bit >> 3, bit & 7)


def bit_region(bit: int):
    """The :class:`BitRegion` a bit falls in, or None (unmapped = free/custom space). Reserved bands are
    checked first, then the informational story clusters -- so a reserved verdict always wins."""
    for r in BIT_REGIONS:
        if r.lo <= bit <= r.hi:
            return r
    for r in STORY_REGIONS:
        if r.lo <= bit <= r.hi:
            return r
    return None


def is_reserved(bit: int) -> bool:
    """True if ``bit`` is in a reserved region (chest band, worldmap unlocks, byte-23 handshake, scratch)."""
    r = bit_region(bit)
    return bool(r and r.reserved)


def is_safe_custom(bit: int) -> bool:
    """True if ``bit`` is in the provably-safe custom band [FIRST_SAFE_FLAG, CHOICE_SCRATCH_FLOOR) and not
    inside a reserved region."""
    return FIRST_SAFE_FLAG <= bit < CHOICE_SCRATCH_FLOOR and not is_reserved(bit)


def nearest_milestone(scenario: int):
    """(value, beat) of the highest milestone <= ``scenario``, or None (before the first)."""
    below = [v for v in SCENARIO_MILESTONES if v <= scenario]
    if not below:
        return None
    v = max(below)
    return (v, SCENARIO_MILESTONES[v])


def resolve_scenario(token) -> int:
    """A ScenarioCounter VALUE from an int / digit-string, or an area name (the lowest value whose beat
    matches, case/substring-insensitive -- so 'ice' -> 2500 'Ice Cavern'). Raises on an unknown name."""
    s = str(token).strip()
    if s.lstrip("-").isdigit():
        return int(s)
    hits = sorted(v for v, beat in SCENARIO_MILESTONES.items() if s.lower() in beat.lower())
    if not hits:
        opts = ", ".join(sorted(set(SCENARIO_MILESTONES.values())))
        raise ValueError(f"unknown scenario area {token!r}. Known areas: {opts}")
    return hits[0]


# ============================ author-side name resolution ============================
# field.toml content keys whose value is a single flag INDEX (a name or an int).
_FLAG_INDEX_KEYS = ("requires_flag", "requires_flag_clear", "flag")
# keys whose value is a [index, value] pair (resolve element 0).
_FLAG_PAIR_KEYS = ("set_flag",)
# the content sections whose items (and nested options/steps) carry flag fields.
_FLAG_SECTIONS = ("event", "npc", "gateway", "prop", "choice", "cutscene")


def _norm(s) -> str:
    return "".join(c for c in str(s).lower() if c.isalnum() or c == "_")


def collect_flag_defs(raw: dict) -> dict:
    """``{normalized_name: index}`` from a project's ``[[flag]]`` table. Each entry needs a ``name`` and an
    ``index``; the index is validated into the safe custom band (clear of real-FF9 usage). Raises
    ValueError on a missing field, a duplicate name, or an out-of-band index."""
    out = {}
    for i, fdef in enumerate(raw.get("flag", []) or []):
        if not isinstance(fdef, dict) or "name" not in fdef or "index" not in fdef:
            raise ValueError(f"[[flag]] #{i}: needs both `name` and `index` (e.g. "
                             f'name = "switch_pulled", index = {FIRST_SAFE_FLAG}).')
        name, idx = str(fdef["name"]), int(fdef["index"])
        key = _norm(name)
        if key in out:
            raise ValueError(f"[[flag]] duplicate name {name!r}.")
        if CHEST_FLAG_LO <= idx <= CHEST_FLAG_HI:
            raise ValueError(f"[[flag]] {name!r}: index {idx} is inside real-FF9's treasure-chest band "
                             f"{CHEST_FLAG_LO}-{CHEST_FLAG_HI} -> save corruption; use "
                             f"[{FIRST_SAFE_FLAG}, {CHOICE_SCRATCH_FLOOR}).")
        if not (FIRST_SAFE_FLAG <= idx < CHOICE_SCRATCH_FLOOR):
            raise ValueError(f"[[flag]] {name!r}: index {idx} is outside the safe custom band "
                             f"[{FIRST_SAFE_FLAG}, {CHOICE_SCRATCH_FLOOR}); pick an index there.")
        out[key] = idx
    return out


def resolve(value, name_map: dict) -> int:
    """Resolve a flag reference (an int, a digit-string, or a registered name) to its index. An int /
    digit-string passes through unchanged; a name is looked up case/spacing-insensitively in ``name_map``
    (the project's ``[[flag]]`` defs). Raises ValueError (with near-miss hints) on an unknown name."""
    if isinstance(value, bool):
        raise ValueError("a flag reference cannot be a boolean")
    if isinstance(value, int):
        return value
    s = str(value).strip()
    if s.lstrip("-").isdigit():
        return int(s)
    key = _norm(s)
    if key in name_map:
        return name_map[key]
    hints = difflib.get_close_matches(key, list(name_map), n=5, cutoff=0.4)
    extra = (f" Did you mean: {', '.join(hints)}?" if hints
             else " Define it in a [[flag]] table (name + index).")
    raise ValueError(f"unknown flag name {value!r}.{extra}")


def _resolve_item(item: dict, name_map: dict):
    """Rewrite a content item's flag fields (names -> ints) in place, recursing into options/steps."""
    for k in _FLAG_INDEX_KEYS:
        if k in item:
            item[k] = resolve(item[k], name_map)
    for k in _FLAG_PAIR_KEYS:
        if k in item and isinstance(item[k], list) and item[k]:
            item[k] = [resolve(item[k][0], name_map)] + list(item[k][1:])
    for sub in ("options", "steps"):
        if isinstance(item.get(sub), list):
            for it in item[sub]:
                if isinstance(it, dict):
                    _resolve_item(it, name_map)


def resolve_project_flags(raw: dict, extra_names: dict | None = None) -> dict:
    """Rewrite all flag-name references in a project dict to integer indices, IN PLACE, using the
    project's own ``[[flag]]`` table merged with ``extra_names`` (e.g. campaign-level shared flags).
    Returns the merged name map. A project with no named flags is left byte-for-byte unchanged (every
    numeric flag passes through), so this is a no-op for existing projects. Call once at load."""
    name_map = dict(extra_names or {})
    name_map.update(collect_flag_defs(raw))
    for sec in _FLAG_SECTIONS:
        val = raw.get(sec)
        if isinstance(val, dict):                  # [cutscene] is a single table
            _resolve_item(val, name_map)
        elif isinstance(val, list):                # [[event]]/[[npc]]/... are arrays of tables
            for it in val:
                if isinstance(it, dict):
                    _resolve_item(it, name_map)
    return name_map


# ============================ save inspector (VIEW) ============================
@dataclass
class SaveReport:
    scenario_counter: int
    milestone: tuple | None          # (value, beat) of the nearest milestone <= scenario, or None
    eiko_abducted: bool
    field_entrance: int
    treasure_hunter_points: int
    chests_opened: int               # set bits in the chest band 8376-8511
    set_bits: list = field(default_factory=list)   # all set bit indices (sorted)
    named_words: list = field(default_factory=list)  # [(WordVar, value)] for non-zero named words


def _read_word(blob: bytes, byte: int, width: int, signed: bool) -> int:
    chunk = blob[byte:byte + width]
    if len(chunk) < width:
        chunk = chunk + b"\x00" * (width - len(chunk))
    fmt = {1: "b" if signed else "B", 2: "<h" if signed else "<H"}[width]
    return struct.unpack(fmt, chunk)[0]


def _count_bits(byte_val: int) -> int:
    return bin(byte_val).count("1")


def decode_gEventGlobal(blob: bytes) -> SaveReport:
    """Decode a 2048-byte ``gEventGlobal`` blob into a :class:`SaveReport`. Shorter blobs are tolerated
    (zero-padded); longer ones are truncated to 2048 (the engine array size)."""
    if len(blob) < 2048:
        blob = blob + b"\x00" * (2048 - len(blob))
    blob = blob[:2048]
    scenario = _read_word(blob, 0, 2, False)
    th = 0
    for lo, hi, weight in TH_POINT_RANGES:
        for b in range(lo, hi + 1):
            th += weight * _count_bits(blob[b])
    chests = sum(_count_bits(blob[b]) for b in range(CHEST_FLAG_LO >> 3, (CHEST_FLAG_HI >> 3) + 1))
    set_bits = [byte * 8 + bit for byte in range(2048) for bit in range(8) if blob[byte] >> bit & 1]
    named = [(w, _read_word(blob, w.byte, w.width, w.signed)) for w in NAMED_WORDS
             if _read_word(blob, w.byte, w.width, w.signed) != 0]
    return SaveReport(
        scenario_counter=scenario, milestone=nearest_milestone(scenario),
        eiko_abducted=EIKO_ABDUCTED_LO <= scenario <= EIKO_ABDUCTED_HI,
        field_entrance=_read_word(blob, 2, 2, True), treasure_hunter_points=th,
        chests_opened=chests, set_bits=set_bits, named_words=named)


def gEventGlobal_from_save(text_or_path) -> bytes:
    """Extract + Base64-decode the ``gEventGlobal`` blob from a Memoria save. Accepts: a path to a save
    JSON, raw JSON text, or a bare Base64 string. (The on-disk ``EncryptedSavedData`` must be decrypted
    to JSON first -- out of scope here; this reads the open JSON/Base64 form, JsonParser.cs:522.)"""
    s = str(text_or_path)
    raw = None
    if "{" in s and '"' in s:                       # looks like JSON text
        raw = s
    else:
        try:
            with open(s, "r", encoding="utf-8") as fh:
                raw = fh.read()
        except (OSError, ValueError):
            raw = None
    if raw is not None and "{" in raw:
        obj = json.loads(raw)
        b64 = _find_key(obj, "gEventGlobal")
        if b64 is None:
            raise ValueError("no 'gEventGlobal' key found in the save JSON")
        return base64.b64decode(b64)
    # bare Base64: the FILE CONTENT if we read one (raw), else the input string itself.
    return base64.b64decode((raw if raw is not None else s).strip())


def _find_key(obj, key):
    """Depth-first search for ``key`` in a nested dict/list (the save JSON nests gEventGlobal under a
    profile object), returning its value or None."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = _find_key(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _find_key(v, key)
            if r is not None:
                return r
    return None


def render_report(rep: SaveReport, *, show_bits: bool = False) -> str:
    """A human-readable summary of a decoded save."""
    L = ["FF9 gEventGlobal (story state)", "=" * 32]
    ms = f"  ->  {rep.milestone[1]} (>= {rep.milestone[0]})" if rep.milestone else "  (before the first milestone)"
    L.append(f"ScenarioCounter : {rep.scenario_counter}{ms}")
    if rep.eiko_abducted:
        L.append("                  [IsEikoAbducted window -- Desert Palace]")
    L.append(f"FieldEntrance   : {rep.field_entrance}")
    L.append(f"Treasure-Hunter : {rep.treasure_hunter_points} pts   (chests/icons opened)")
    L.append(f"Chests opened   : {rep.chests_opened}   (bits {CHEST_FLAG_LO}-{CHEST_FLAG_HI})")
    if rep.named_words:
        L.append("Named vars set  :")
        for w, v in rep.named_words:
            L.append(f"  - {w.name} = {v}")
    # group set BIT-flags by region; skip bits that belong to a named WORD var (those aren't story bits)
    word_bytes = {b for w in NAMED_WORDS for b in range(w.byte, w.byte + w.width)}
    by_region: dict = {}
    custom, unmapped, n_story = [], [], 0
    for bit in rep.set_bits:
        if (bit >> 3) in word_bytes:                # part of a named word var (ScenarioCounter/FieldEntrance/..)
            continue
        n_story += 1
        r = bit_region(bit)
        if r is not None:
            by_region.setdefault(r.name, []).append(bit)
        elif is_safe_custom(bit):
            custom.append(bit)
        else:
            unmapped.append(bit)
    L.append(f"Set story bits  : {n_story} "
             f"(in {len(by_region)} known region(s), {len(custom)} custom, {len(unmapped)} unmapped)")
    for name, bits in sorted(by_region.items()):
        L.append(f"  [{name}] {len(bits)} bit(s)")
    if custom:
        L.append(f"  [custom 8512+] {len(custom)} bit(s): {custom[:20]}{' ...' if len(custom) > 20 else ''}")
    if show_bits and unmapped:
        L.append(f"  [unmapped] {unmapped}")
    return "\n".join(L)


# ============================ registry browse (NAME) ============================
def registry_rows() -> list:
    """``[(kind, name, location, meaning, tier)]`` for the CLI / docs -- named vars + reserved regions +
    scenario milestones + the safe band, in one flat listing."""
    rows = []
    for w in NAMED_WORDS:
        loc = f"byte {w.byte}" + (f"-{w.byte + w.width - 1}" if w.width > 1 else "")
        rows.append(("var", w.name, loc, w.meaning, w.tier))
    for r in BIT_REGIONS:
        tag = "RESERVED" if r.reserved else "region"
        rows.append((tag, r.name, f"bits {r.lo}-{r.hi}", r.meaning, r.tier))
    for r in STORY_REGIONS:
        rows.append(("story", r.name, f"bits {r.lo}-{r.hi}", r.meaning, r.tier))
    for v, beat in sorted(SCENARIO_MILESTONES.items()):
        rows.append(("scenario", str(v), "ScenarioCounter", beat, "a"))
    rows.append(("band", "safe_custom", f"bits {FIRST_SAFE_FLAG}-{CHOICE_SCRATCH_FLOOR - 1}",
                 "Allocate custom story flags here (clear of all real-FF9 usage).", "a"))
    return rows
