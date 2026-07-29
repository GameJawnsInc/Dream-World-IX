"""FF9 story-flag registry + save inspector (the NAME / VIEW / UNDERSTAND layer).

FF9 keeps all save-persistent story state in one place: ``EventState.gEventGlobal``, a 2048-byte array
(the engine's ``VariableSource.Global`` space, Base64'd into the save JSON under key ``"gEventGlobal"``,
``JsonParser.cs:522,579``). This module is the kit's canonical map of that heap -- grounded in the
Memoria source + a 676-field census (see ``research/STORY_FLAGS.md``). It does three things:

1. **NAME** -- a registry of FF9's known named vars / reserved regions / scenario milestones, plus
   author-side name resolution so a ``field.toml`` can gate on a *named* flag instead of a raw index
   (a ``[[flag]]`` table: ``[[flag]] name = "switch_pulled" index = 8720``).
2. **CREATE-safely** -- the provably-safe allocation band (``FIRST_SAFE_FLAG`` = 8712, the first bit
   clear of ALL real-FF9 usage; the Mognet lock band 8376-8511, the stock read-mail payload bytes
   8512-8711, and the choice scratch are reserved). These constants are the single source of truth
   (``campaign.py`` imports them).
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
# THE TOP OF REAL FF9 USAGE (re-censused 2026-07-19, byte-addressed vars INCLUDED this time -- the
# earlier "first clear bit = 8512" claim came from a BOOL-only census and missed stock's byte writes):
#   bits 8192-8367  = the stock MOGNET MAILBOX (Byte[1024-1045]: wipe-guard 1024, delivered counter
#                     1032, Stiltzkin tally 1033, the 12 live letter-slot bytes 1034-1045) -- written
#                     by ~48 real moogle fields during ordinary give/read play (content/mognet.py).
#   bits 8376-8503  = the MOGNET variant one-shot locks (GIVE 8376-8439 / READ 8440-8503) -- long
#                     mislabelled "the treasure-chest bitfield"; the ~58 writers are the moogle fields'
#                     twin switch-64 lock tables, decoded to the instruction (content/mognet.py).
#   bits 8504-8509  = clear (the kit's deathrules wipe marker sits at 8508).
#   bits 8510-8511  = two real stock bools (byte 1063).
#   bits 8512-8591  = stock READ-MAIL row VARIANTS (Byte[1064..1073] -- whole-byte writes on every
#   bits 8632-8711    Mognet open at any moogle with known letters) and row SENDERS (Byte[1079..1088]).
#                     A custom flag here is CLOBBERED by ordinary play -- never allocate in either run.
#   bits 8592-8631  = the payload hole (bytes 1074-1078), stock-clear; the kit's outpost word lives
#                     here (battle/deathrules.py OUTPOST_BYTE = 1074, bits 8592-8607).
# The choice-visibility scratch sits at byte 2040 = bits 16320+, the netsync co-op cells
# (engine-written peer presence/position, bytes 2032-2039 = bits 16256-16319) sit just below it,
# and the [[qte]] modal scratch band (bytes 2018-2031 = bits 16144-16255, content/qte.py) just below
# THAT -- deliberately clear of the co-op cells, which the engine rewrites EVERY FRAME while co-op
# runs. So custom story flags MUST live in [8712, 16144): 8712 (start of byte 1089) is the first bit
# clear of ALL real-FF9 usage -- bools AND byte-addressed vars.
FIRST_SAFE_FLAG = 8712
MOGNET_MAILBOX_LO, MOGNET_MAILBOX_HI = 8192, 8367   # stock Mognet mailbox Byte[1024-1045] (reserved)
MOGNET_LOCK_LO, MOGNET_LOCK_HI = 8376, 8511    # the Mognet lock bands + their margin (real-FF9; reserved)
CHEST_FLAG_LO, CHEST_FLAG_HI = MOGNET_LOCK_LO, MOGNET_LOCK_HI   # deprecated alias (the old mislabel)
READMAIL_PAYLOAD_LO, READMAIL_PAYLOAD_HI = 8512, 8711   # stock read-mail scratch bytes 1064-1088 (reserved)
NAMEPLATE_EXPLORED_FLOOR = 16048               # bytes 2006-2017: the EXTENDED-NAMEPLATE explored words
                                               # (world/entrance.py EXTENDED_EXPLORED_RANGES -- 6 UInt16
                                               # words, one save-persistent "visited" bit per virgin
                                               # nameplate case 65-155; flush below the QTE scratch)
RESULT_WORD_CAP = NAMEPLATE_EXPLORED_FLOOR // 8 - 2   # 2004: the last gEventGlobal byte where a modal
                                               # result Int16 (bytes N..N+1) still clears every kit
                                               # floor above it -- the [[qte]]/[[numeric_input]]
                                               # `result` caps derive from this, so a floor move
                                               # can never strand them again (the 172c8b98 lesson)
QTE_SCRATCH_FLOOR = 16144                      # bytes 2018-2031: the [[qte]] modal scratch (content/qte.py)
COOP_CELLS_FLOOR = 16256                       # bytes 2032-2039: the netsync co-op cells (engine-written)
CHOICE_SCRATCH_FLOOR = 16320                   # byte 2040: engine/kit-owned choice mask scratch

# --- THE SAFE-BAND PARTITION (2026-07-27, the flag-band collision fix) ---
# The safe band [FIRST_SAFE_FLAG, NAMEPLATE_EXPLORED_FLOOR) is PARTITIONED so campaign/journey
# per-member auto-flag windows can never alias the kit's own standing allocators:
#   [FIRST_SAFE_FLAG, KIT_STANDING_FLOOR)           = the CAMPAIGN LANE. Per-member windows grow up
#       from `flag_base` (campaign.py enforces the ceiling at the window validator) plus any
#       campaign-shared authored [[flag]]s (also held below the floor there). The live opening
#       campaign (372 members x 16 from 8712) spans 8712-14663 -- flush under the floor, and its
#       windows are BAKED INTO A REAL SAVE: the floor must never move down, and the campaign lane
#       must never be re-based while that playthrough lives.
#   [KIT_STANDING_FLOOR, NAMEPLATE_EXPLORED_FLOOR)  = the KIT-STANDING LANE. The single-field AUTO
#       bands, the behavior Blackboard (flags + byte band), siege request flags, and future named
#       world-content flags (e.g. the boat parked-position rung). Reserved BIT_REGIONS below keep
#       authored [[flag]] indices out of the consumed sub-bands.
# History: pre-partition, the AUTO bands sat at 9100-9599, the Blackboard at flags 8860-9080 +
# bytes 1220+ (bits 9760+), and siege requests at 8840 -- ALL inside the opening campaign's window
# span (nothing observed broken: verbatim members had written no window bits yet). Standing fields
# DEPLOYED under the old bands keep their baked indices until rebuilt -- their once-flags alias
# campaign windows for members ~24-55 until then (bench-grade exposure). The still-earlier pre-b18
# legacy bands (event 8000+/cutscene 8100+/choice 8200+/on_entry+ate 8300+) sat below
# FIRST_SAFE_FLAG entirely (the 8300 band INSIDE the stock Mognet mailbox slots) -- twice moved,
# both times for the same lesson: bands need one owner and an enforced ceiling.
KIT_STANDING_FLOOR = 14664                     # first bit of the kit-standing lane; campaign windows end below

# The single-field AUTO once-flag bands (consumed by build._FlagAlloc; content modules alias them).
# A single-field build auto-allocates a GLOB once/gate flag per unflagged [[event]]/[[cutscene]]/
# [[choice]]/[[on_entry]]/[ate] block. The allocator also skips any flag index the same project
# references explicitly (collect_safe_flag_indices), so a defaulted block never aliases an authored
# story flag. Campaign members don't use these bands at all (they pack into per-member windows from
# `flag_base`, default FIRST_SAFE_FLAG).
# The lane holds 1384 bits total (14664..16047) and the Blackboard BYTE band is the scarce resource
# (the condor-scale hand map ran 113 bytes), so the budget is: AUTO 5x40 -> Blackboard flags 96 ->
# siege 16 -> named world flags 32 -> Blackboard BYTES 114 -> the modal-result home (unreserved).
AUTO_BAND_WIDTH = 40                           # per-lane band width; the allocator raises on exhaustion
                                               # (was 100 pre-partition -- no real field carries 40+
                                               # defaulted blocks of one type; explicit flags relieve it)
AUTO_EVENT_BASE = 14664                        # [[event]] auto once-flags: 14664-14703
AUTO_CUTSCENE_BASE = 14704                     # [[cutscene]] GLOB once-flags: 14704-14743
AUTO_CHOICE_BASE = 14744                       # zone-[[choice]] gate flags: 14744-14783
AUTO_ONENTRY_BASE = 14784                      # [[on_entry]] once-flags: 14784-14823
AUTO_ATE_BASE = 14824                          # the [ate] availability flag: 14824-14863

# The rest of the kit-standing lane (owners import these; flags.py is the single source of truth):
BEHAVIOR_FLAG_BASE = 14864                     # content/behavior.py Blackboard flag band: 14864-14959
BEHAVIOR_FLAG_END = 14959
SIEGE_REQUEST_BASE = 14960                     # content/siege.py request flags: 14960-14975
KIT_WORLD_FLAG_BASE = 14976                    # named standing world-content flags: 14976-15007
                                               # (reserved for e.g. the boat parked-position rung)
FERRY_DEPART_BYTE = 1872                       # scene-ladder rung 2: the ferry-departure port code
                                               # (bits 14976-14983 = the band's first byte; 0 = none,
                                               # 1-4 = Ashvale/Tidefall/Grimhorn/Larkspur -- written by
                                               # the hall's ferry arms, consumed+cleared by WORLD11's
                                               # departure director; studies/overworld-topography/
                                               # scene-ladder/rung2a_departure.py)
FERRY_ORIGIN_X_INT24 = 1873                    # scene-ladder rung 3c: the hall-entry world X (x256
                                               # fixed-point Int24, bytes 1873-1875 = the band's last 3
                                               # bytes). The depart arm caches Global.Int24[64] (the
                                               # on-foot saved-position X) here BEFORE the stage preset
                                               # clobbers it; WORLD11's departure prologue box-tests it
                                               # to classify the ORIGIN port (0/garbage -> Ashvale).
BEHAVIOR_BYTE_BASE = 1876                      # Blackboard byte band: bytes 1876-1989 (bits 15008-15919;
BEHAVIOR_BYTE_END = 1989                       # byte 1876 = bit 15008, flush after the flag sub-bands).
                                               # Ends BELOW the modal-result home: bytes 1990-2005 stay
                                               # UNRESERVED so [[qte]]/[[numeric_input]] `result` words
                                               # (canonical guidance "e.g. 2000", cap RESULT_WORD_CAP=
                                               # 2004) keep a clear heap-top landing -- the 172c8b98
                                               # lesson, nearly re-created by this very partition when
                                               # the byte band first claimed 1928-2005.


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


# Named word vars (byte-addressed). Order: low offsets first. Each is a save-persistent byte/word the
# engine C# reads at a FIXED index (so the meaning IS the engine's own var name -- tier a). Found by
# scanning every `gEventGlobal[<const>]` read in the Memoria source (the engine-reader pass).
NAMED_WORDS = [
    WordVar("ScenarioCounter", 0, 2, False, "Master story-progress value (1..12000).", "a",
            "EventState.cs:16-24; EBin.cs:34"),
    WordVar("FieldEntrance", 2, 2, True, "Last entrance / arrival map index (read by every field).", "a",
            "EventState.cs:26-34; EBin.cs:35"),
    WordVar("TranceGaugeFlag", 16, 1, False, "Trance gauge enable (0/1); also gates the Trance status UI.", "a",
            "battle.cs:38; StatusUI.cs:291"),
    WordVar("GarnetDepressFlag", 17, 1, False, "Garnet summon-depression state (summons withheld).", "a",
            "battle.cs:39"),
    WordVar("GarnetSummonFlag", 18, 1, False, "Garnet summon availability.", "a", "battle.cs:40"),
    # Worldmap Navi known-location bitmasks (bytes 92-99 = 4 UInt16 slots F0-F3, the engine's
    # keventNaviLocF0..F3). `w_naviLocationAvailable` (ff9.cs:6957-6982) reads all four as bitmasks partitioning 64
    # Navi locations into 16-per-slot groups; a set bit reveals a location on the worldmap. Previously seen
    # only as "write-only worldmap-unlock bits"; the engine reads them at these fixed indices as words.
    WordVar("WorldmapKnownLocationsF0", 92, 2, False, "Worldmap known-locations bitmask, slot F0 / locations "
            "0-15 (the engine's `knownLocations` / keventNaviLocF0); a set bit reveals a location on the Navi "
            "worldmap (the engine ORs in e.g. 0x7C0 Treno/South Gates, 0xC000 Dali).", "a",
            "ff9.cs:2315-2317,6927-6935,6960-6982"),
    WordVar("WorldmapKnownLocationsF1", 94, 2, False, "Worldmap known-locations bitmask, slot F1 / locations "
            "16-31 (keventNaviLocF1).", "a", "ff9.cs:2320-2323,6960-6982"),
    WordVar("WorldmapKnownLocationsF2", 96, 2, False, "Worldmap known-locations bitmask, slot F2 / locations "
            "32-47 (keventNaviLocF2).", "a", "ff9.cs:2325-2328,6960-6982"),
    WordVar("WorldmapKnownLocationsF3", 98, 2, False, "Worldmap known-locations bitmask, slot F3 / locations "
            "48-63 (keventNaviLocF3).", "a", "ff9.cs:2330-2333,6960-6982"),
    WordVar("NaviMode", 100, 1, False, "Worldmap Navi/cursor navigation mode.", "a", "ff9.cs:2266-2271"),
    WordVar("WorldmapTransport", 102, 1, False, "Worldmap transport id (0=on foot, 8=Invincible, ...).", "a",
            "WorldConfiguration.cs:256"),
    WordVar("VegetableItemUsed", 181, 1, False, "Dead Pepper / vegetable item used flag (gates re-use).", "a",
            "ItemUI.cs:47,960"),
    # (Choco's BEAK level -- dig strength, capped 99, DISTINCT from the byte-191 terrain ability -- is
    #  Global Byte 139, but it is field-.eb-only state with no engine C# reader, so it stays out of this
    #  engine-cited registry. -> content/chocobo.py + memory project-ff9-chocobo-hot-cold.)
    WordVar("MoveControl", 190, 1, True, "Current field/worldmap move-control (transport) index.", "a",
            "ff9.cs:5793"),
    WordVar("ChocoDigLevel", 191, 1, False, "Choco's dig ability level (set to 5 at milestones); also the "
            "chocobo-kind gate for the vegetable item.", "a", "ChocographUI.cs:245; EMinigame.cs:454; ItemUI.cs:48"),
    WordVar("TonberiCount", 192, 1, False, "Tonberry encounter/kill counter (battle).", "a", "battle.cs:41"),
    WordVar("SummonRayFlag", 193, 1, False, "Summon 'ray' animation flag (battle).", "a", "battle.cs:42"),
    WordVar("SummonAllLongFlag", 207, 1, False, "Show full-length summon animations toggle (battle).", "a",
            "battle.cs:43"),
    WordVar("MagicDisabledFlag", 227, 1, False, "Nonzero disables magic in the menu (e.g. Oeilvert's "
            "anti-magic field; set by Oeilvert fields).", "a", "AbilityUI.cs:28,881"),
    # The netsync co-op cells (kit-reserved, engine s37): while [Netsync] Enabled the engine writes the
    # PEER's presence + walkmesh position here every frame; [[coop]] gates read them as GLOB vars.
    # Save values are transient echoes (rewritten while co-op runs; never written when disabled).
    WordVar("CoopPeerPresence", 2032, 1, False, "Netsync: 1 = the co-op peer stands on my current field "
            "(engine-written every frame while co-op is on).", "a", "NetSyncClient.WriteCoopCells (s37)"),
    WordVar("CoopPeerX", 2034, 2, True, "Netsync: the co-op peer's walkmesh X (engine-written).", "a",
            "NetSyncClient.WriteCoopCells (s37)"),
    WordVar("CoopPeerZ", 2036, 2, True, "Netsync: the co-op peer's walkmesh Z (engine-written).", "a",
            "NetSyncClient.WriteCoopCells (s37)"),
]

# Reserved / named BIT regions (bit-addressed). A mod must not allocate into a reserved region.
# Specific named bits are listed BEFORE the broad band they sit inside, so bit_region() resolves the
# precise name first (e.g. bit 815 -> "mognet_central_discovered", not the broad "worldmap_unlocks").
BIT_REGIONS = [
    BitRegion("kit_auto_once_bands", AUTO_EVENT_BASE, AUTO_ATE_BASE + AUTO_BAND_WIDTH - 1,
              "The kit-standing AUTO once-flag bands (event/cutscene/choice/on_entry/ate, "
              "AUTO_BAND_WIDTH bits each): build._FlagAlloc packs a single-field build's defaulted "
              "content gates here. NOT reserved -- the documented contract is cooperative: an "
              "authored [[flag]] may claim an index here and the allocator SKIPS it "
              "(collect_safe_flag_indices), so refusal would break the skip mechanism.", False, "a",
              "flags.py safe-band partition (2026-07-27)"),
    BitRegion("behavior_blackboard_flags", BEHAVIOR_FLAG_BASE, BEHAVIOR_FLAG_END,
              "The behavior compiler's Blackboard flag band (content/behavior.py): compiled tree "
              "state, cleared/preset by the emitted Main_Init. Kit-owned.", True, "a",
              "content/behavior.py Blackboard"),
    BitRegion("siege_request_flags", SIEGE_REQUEST_BASE, KIT_WORLD_FLAG_BASE - 1,
              "The [siege] war-council request flags (content/siege.py). Kit-owned.", True, "a",
              "content/siege.py REQUEST_FLAG_BASE"),
    BitRegion("kit_world_flags", KIT_WORLD_FLAG_BASE, KIT_WORLD_FLAG_BASE + 31,
              "Named standing world-content flags (reserved ahead: the boat parked-position rung "
              "and kin allocate here by name).", True, "a", "flags.py safe-band partition"),
    BitRegion("behavior_blackboard_bytes", BEHAVIOR_BYTE_BASE * 8, BEHAVIOR_BYTE_END * 8 + 7,
              "The behavior Blackboard BYTE band (bytes 1876-1989): compiled counters/timers/vars, "
              "cleared/preset by the emitted Main_Init. A story bit here lands inside a compiled "
              "variable. Bytes 1990-2005 above it are deliberately UNRESERVED -- the modal-result "
              "home ([[qte]]/[[numeric_input]] `result` Int16s, cap RESULT_WORD_CAP).", True, "a",
              "content/behavior.py Blackboard byte band"),
    BitRegion("nameplate_explored_words", 16048, 16143, "The kit's EXTENDED-NAMEPLATE explored words "
              "(bytes 2006-2017): one save-persistent 'visited' bit per virgin nameplate case 65-155, "
              "read by the kit-extended func-0xB in every free-roam dispatcher and set by virgin-band "
              "entrance warp branches (world/entrance.py EXTENDED_EXPLORED_RANGES). Kit-owned; a "
              "custom story flag here would flip a location's explored state.", True, "a",
              "world/entrance.py extend_nameplate_band"),
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
    BitRegion("mognet_mailbox", MOGNET_MAILBOX_LO, MOGNET_MAILBOX_HI, "The stock MOGNET MAILBOX "
              "(Byte[1024-1045]): wipe-guard 1024, lifetime-delivered counter 1032, Stiltzkin tally "
              "1033, and the 12 live letter-slot bytes 1034-1045 -- read AND whole-byte-written by "
              "~48 real moogle fields during ordinary give/read play (a custom bit here corrupts a "
              "player's letters, and play clobbers the bit right back). The pre-b18 on_entry/[ate] "
              "auto band (8300+) sat inside the slot bytes -- why the auto bands moved to the safe "
              "band. NEVER allocate here.", True, "a",
              "content/mognet.py decode (fields 300/407/1102; live-save verified); census (48-field byte access)"),
    BitRegion("mognet_give_locks", 8376, 8439, "The MOGNET give-side variant one-shot locks (anchor "
              "8383, bit(v) = anchor + 8*(v//8) - (v%8)): set when a moogle hands the player letter "
              "variant v to carry. The band every moogle field's switch-64 lock table writes -- the "
              "'treasure-chest registry' this region was long mislabelled as (the byte-identical block "
              "in ~58 fields is the twin lock tables, not chests). NEVER allocate here.", True, "a",
              "content/mognet.py decode (fields 115/300/1102, instruction-cited); live-save verified"),
    BitRegion("mognet_read_locks", 8440, 8503, "The MOGNET read-side variant one-shot locks (anchor "
              "8447): set on letter ARRIVAL (accept-delivery or scenario auto-arrival); each gates that "
              "variant's row in the moogle's read-mail list. NEVER allocate here.", True, "a",
              "content/mognet.py decode; live vectors: variants 19/22/33 -> bytes 1057b4/1057b1/1059b6"),
    BitRegion("mognet_lock_margin", 8504, 8511, "The lock bands' margin byte (1063): bits 8510-8511 are "
              "real stock bools; 8508 is the kit's deathrules wipe marker (bit-disjoint). Reserved.",
              True, "a", "census 2026-07-19 (bool sweep, reference/test2); battle/deathrules.py"),
    BitRegion("mognet_readmail_payload", READMAIL_PAYLOAD_LO, READMAIL_PAYLOAD_HI, "Stock READ-MAIL menu "
              "scratch: row VARIANTS Byte[1064-1073] (bits 8512-8591) and row SENDERS Byte[1079-1088] "
              "(bits 8632-8711), whole-byte-written on every Mognet open at any moogle with known "
              "letters -- ordinary play clobbers any custom bit here. The stock-clear hole bytes "
              "1074-1078 (bits 8592-8631) holds the kit's outpost word (deathrules OUTPOST_BYTE 1074). "
              "NEVER allocate anywhere in this band.", True, "a",
              "census 2026-07-19 (byte-var sweep: 1064-1073/1079-1088 are the ONLY stock byte vars >= 1046)"),
    BitRegion("qte_scratch", QTE_SCRATCH_FLOOR, COOP_CELLS_FLOOR - 1,
              "The [[qte]] modal scratch band (bytes 2018-2031: bout state, combo/points channels; "
              "re-seeded on every open). Sits BELOW the netsync co-op cells on purpose -- the engine "
              "rewrites those every frame while co-op runs, which would clobber a bout's scoring. "
              "Kit-reserved.", True, "a", "content/qte.py scratch band"),
    BitRegion("netsync_coop_cells", COOP_CELLS_FLOOR, CHOICE_SCRATCH_FLOOR - 1,
              "Netsync co-op cells (bytes 2032-2039): the engine writes the peer's presence + walkmesh "
              "X/Z here every frame while co-op is on; [[coop]] gates read them. Kit-reserved.", True, "a",
              "NetSyncClient.WriteCoopCells (s37); content/coop.py"),
    BitRegion("choice_scratch", CHOICE_SCRATCH_FLOOR, CHOICE_SCRATCH_FLOOR + 15,
              "Choice-visibility mask scratch (kit MASK_SCRATCH_IDX); engine/kit-owned.", True, "a", "region.py:57"),
]

# Informational (NON-reserved) named story-flag clusters from the 676-field census: contiguous bit bands
# named by their dominant writer area, for ANNOTATING a decoded save's set bits (not for allocation -- they
# sit below FIRST_SAFE_FLAG anyway). These are "where these flags are written from", not a proven per-bit
# meaning. Derived + verified by the ff9-understand-layer workflow (research/gen_understand_layer.py).
STORY_REGIONS = [
    # --- Per-bit promotions from the flag-lore pass (research/gen_flag_lore.py, curated 2026-07-12).
    # Single bits (or one narrow band) whose writer + nearby dialogue + gate bodies compose into a
    # defensible meaning; listed BEFORE the broad census bands so bit_region() resolves them first.
    # Tier b = single writer field + decoded evidence (not engine-named); meanings quote the evidence.
    BitRegion("choco_paradise_fly_talk", 1043, 1043, "Chocobo's Paradise (2954): set in the scene around "
              "Mene's 'Choco can fly like me? Wow, that's great, kupo!'; gates Paradise dialogue + an "
              "object spawn / return warp on 2955.", False, "b", "flag_lore: writer 2954 + gates"),
    BitRegion("chocobo_paradise_state", 1086, 1086, "Chocobo's Paradise progress latch: written at "
              "Paradise (2954), read by ALL THREE Hot&Cold forests (2950/2951/2952 -- each says txids "
              "237-239 when set).", False, "b", "flag_lore: writer 2954, cross-read x3 forests"),
    BitRegion("bohden_gate_card", 2088, 2088, "South Gate/Bohden Gate (801): set at 'Received Card!'; "
              "when set spawns obj 12; read by Bohden Station.", False, "b", "flag_lore: writer 801"),
    BitRegion("dali_production_open_choice", 2090, 2090, "Dali/Production Area: latched at the "
              "'Let's see... Open / Don't open' choice (underground Dali); read by Storage Area.",
              False, "b", "flag_lore: writer + choice window"),
    BitRegion("morrid_coffee_quest", 2419, 2419, "Morrid's coffee sidequest completion: set at "
              "Observatory Mountain shack (457) around 'I am ready to join my dearly departed wife "
              "now.'; read by Lindblum/Hideout (2112), which gates an object spawn on it (the "
              "Mini-Prima Vista reward site).", False, "b", "flag_lore: writer 457, reader 2112"),
    BitRegion("evil_forest_swamp_door", 2447, 2447, "Evil Forest/Swamp (254) door first-crossing "
              "switch: when CLEAR the one-shot walk-through choreography plays (then sets the bit); "
              "when SET the plain fade+warp to 256. In-game proven 2026-07-12 (the gated-door carry).",
              False, "b", "flag_lore + the #3 player-call door playtest"),
    BitRegion("lindblum_lowell_theater_scene", 2495, 2495, "Lindblum/Theater: scene latch around "
              "'Poor guy... It's tough being popular.' (the Lowell arc); when set spawns objs "
              "6-11; read by Studio + Theater Ave.", False, "b", "flag_lore: writer + line"),
    BitRegion("lcastle_airship_dock_departure", 2626, 2626, "Lindblum Castle/Airship Dock once-event: "
              "when CLEAR a scene warps to 1369; read by 15 fields incl. Brahne's Fleet/Event + the "
              "castle halls.", False, "b", "flag_lore: cross-read x15"),
    BitRegion("lindblum_square_event", 2648, 2648, "Lindblum/Square (559) town-state latch: read by 12 "
              "Lindblum fields (Hunter's Gate, B.D. Station, Church Street ...); says txid 594 when "
              "set.", False, "b", "flag_lore: writer 559, cross-read x12"),
    BitRegion("mountain_oglop_caught", 2857, 2857, "Conde Petie Mt. Path/Trail: set at "
              "'Caught a mountain oglop.'; gates a 9-line dialogue set; read by Conde Petie/Corridor.",
              False, "b", "flag_lore: writer + line"),
    BitRegion("conde_petie_thief_scene", 2863, 2863, "Conde Petie/Event: scene latch around 'Thief!'; "
              "gates a 6-line dialogue set; read by Exit + Shrine.", False, "b", "flag_lore"),
    BitRegion("desert_palace_sanctum_cast", 3536, 3542, "Desert Palace per-member cast latches "
              "(cleared at Palace/Sanctum 2209; each bit gates one NPC spawn across Palace rooms; "
              "also read by Ipsen's Castle/Mural Room). One bit per held party member.", False, "b",
              "flag_lore: 7 same-shape bits, writer 2209"),
    BitRegion("desert_palace_bloodstone_choice", 3559, 3559, "Desert Palace/Lobby: latched at the "
              "'Inspect the bloodstone? Yes/No' choice; read by the Stairwell.", False, "b", "flag_lore"),
    BitRegion("cleyra_attack_path_choice", 3882, 3882, "Cleyra/Town during the Alexandrian assault: "
              "set around 'Let's go left!'; when set spawns obj 4; read by Cathedral / Observation "
              "Post / Windmill Area.", False, "b", "flag_lore: writer + line"),
    BitRegion("cleyra_attack_alert", 3883, 3883, "Cleyra/Water Mill Area during the assault: written "
              "around 'They're after the king and the high priest!'; when set spawns objs 12-13; read "
              "across Cleyra town fields.", False, "b", "flag_lore: writer + line"),
    BitRegion("acastle_brahne_chamber_scene", 3902, 3902, "Alexandria Castle/Queen's Chamber: scene "
              "latch around Brahne's 'It's okay, darling. I'm just happy that you understand.' "
              "(beats 5070-5075); read by Chapel + Guardhouse.", False, "b", "flag_lore: writer + line"),
    BitRegion("mognet_central_quest", 4046, 4046, "The Mognet Central sidequest signal: set at Mognet "
              "Central (3100), read by 59 fields game-wide -- every moogle station says txid 20 when "
              "set (the mail-network beat every kupo checks).", False, "b",
              "flag_lore: writer 3100, cross-read x59"),
    BitRegion("treno_knight_house_reward", 7346, 7346, "Treno/Knight's House (1910) reward latch: set "
              "at 'Received Gil!'; while CLEAR the weapon objects (252-254) spawn; when SET field 1904 "
              "warps to the 1916 battle room branch.", False, "b", "flag_lore: writers 1910, gate 1904"),
    # --- the broad census bands (dominant-writer clusters; the per-bit table above refines them) ---
    BitRegion("hilda_garde_invincible_events", 196, 199, "Late-game airship/event flags "
              "(Lindblum Castle / Hilda Garde 3 / Invincible).", False, "c", "census"),
    BitRegion("chocobo_dig_state", 848, 853, "Chocobo Hot & Cold / Chocograph minigame state.", False, "b",
              "census; EMinigame.cs"),
    BitRegion("chocobo_forest_state", 888, 895, "Chocobo Hot & Cold dig-spot / chocograph-found bits.", False,
              "b", "census; EMinigame.cs"),
    BitRegion("chocograph_found_opened", 1472, 1519, "Chocograph 'found'/'opened' treasure bitfields "
              "(choco-dig minigame): OPENED = bytes 184-186 (bits 1472-1495), FOUND = bytes 187-189 "
              "(bits 1496-1519), each an Int24 LE over the 24 chocographs. (Was mis-registered at "
              "1040-1087 / bytes ~130-135 by the census; the engine reads 184-189.)", False, "a",
              "ChocographUI.cs:250-251"),
    BitRegion("chocobo_garden_state", 1156, 1159, "Chocobo Hot & Cold dig-progress flags.", False, "c", "census"),
    BitRegion("chocobo_air_garden_state", 1416, 1423, "Chocobo Hot & Cold / Air Garden unlock state "
              "(top of the choco-dig band, bytes 106-177).", False, "c", "census"),
    # (byte 227 / bit 1816 was a census "Oeilvert event" cluster -> it's the MagicDisabledFlag word above,
    #  set by Oeilvert's anti-magic field. Named there, so no separate bit region.)
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


def named_word_at(bit: int):
    """The :class:`WordVar` whose byte range covers ``bit``'s byte, or None. A raw bit edit landing inside
    a named word (ScenarioCounter, TranceGaugeFlag, ...) touches a fixed offset the engine C# reads by
    BYTE, not a free story bit -- ``bit_region``/``is_reserved`` don't cover this (they only walk
    ``BIT_REGIONS``/``STORY_REGIONS``, never ``NAMED_WORDS``)."""
    byte = bit >> 3
    for w in NAMED_WORDS:
        if w.byte <= byte < w.byte + w.width:
            return w
    return None


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
# (``chest``: its ``flag`` = the opened-bit + ``requires_flag``/``requires_flag_clear`` = the appearance gate.)
_FLAG_SECTIONS = ("event", "npc", "gateway", "prop", "choice", "cutscene", "on_entry", "chest")


def _norm(s) -> str:
    return "".join(c for c in str(s).lower() if c.isalnum() or c == "_")


def collect_flag_defs(raw: dict, *, check_index_collisions: bool = True) -> dict:
    """``{normalized_name: index}`` from a project's ``[[flag]]`` table. Each entry needs a ``name`` and an
    ``index``; the index is validated into the safe custom band (clear of real-FF9 usage). Raises
    ValueError on a missing field, a duplicate name, an out-of-band index, or (when
    ``check_index_collisions``) two different names claiming the same index -- that would silently alias
    two story flags onto one gEventGlobal bit. ``check_index_collisions=False`` is for
    :func:`project_flag_names`, which must survive an already-authored ambiguous table and show it, not
    refuse to load it."""
    out = {}
    by_idx = {}                             # idx -> name, for the index-collision check
    for i, fdef in enumerate(raw.get("flag", []) or []):
        if not isinstance(fdef, dict) or "name" not in fdef or "index" not in fdef:
            raise ValueError(f"[[flag]] #{i}: needs both `name` and `index` (e.g. "
                             f'name = "switch_pulled", index = {FIRST_SAFE_FLAG}).')
        name, idx = str(fdef["name"]), int(fdef["index"])
        key = _norm(name)
        if key in out:
            raise ValueError(f"[[flag]] duplicate name {name!r}.")
        if MOGNET_LOCK_LO <= idx <= MOGNET_LOCK_HI:
            raise ValueError(f"[[flag]] {name!r}: index {idx} is inside real-FF9's Mognet lock band "
                             f"{MOGNET_LOCK_LO}-{MOGNET_LOCK_HI} (letter one-shot locks) -> save "
                             f"corruption; use [{FIRST_SAFE_FLAG}, {CHOICE_SCRATCH_FLOOR}).")
        if READMAIL_PAYLOAD_LO <= idx <= READMAIL_PAYLOAD_HI:
            raise ValueError(f"[[flag]] {name!r}: index {idx} is inside stock Mognet's read-mail "
                             f"payload bytes ({READMAIL_PAYLOAD_LO}-{READMAIL_PAYLOAD_HI}) -- ordinary "
                             f"play at any real moogle CLOBBERS these bytes; use "
                             f"[{FIRST_SAFE_FLAG}, {CHOICE_SCRATCH_FLOOR}).")
        if not (FIRST_SAFE_FLAG <= idx < CHOICE_SCRATCH_FLOOR):
            raise ValueError(f"[[flag]] {name!r}: index {idx} is outside the safe custom band "
                             f"[{FIRST_SAFE_FLAG}, {CHOICE_SCRATCH_FLOOR}); pick an index there.")
        if is_reserved(idx):
            r = bit_region(idx)
            raise ValueError(f"[[flag]] {name!r}: index {idx} is inside the reserved '{r.name}' region "
                             f"({r.lo}-{r.hi}: {r.meaning.split('.')[0]}); pick a clear index in "
                             f"[{FIRST_SAFE_FLAG}, {CHOICE_SCRATCH_FLOOR}).")
        if check_index_collisions and idx in by_idx:
            raise ValueError(f"[[flag]] {name!r} and {by_idx[idx]!r} both use index {idx} -- two "
                             f"different story flags can't share one gEventGlobal bit.")
        by_idx[idx] = name
        out[key] = idx
    return out


def project_flag_names(raw: dict) -> dict:
    """``{absolute_gEventGlobal_bit: display_name}`` from a project's ``[[flag]]`` table -- for ANNOTATING a
    save's custom-band bits with the modder's own names in the Story State view. A named ``[[flag]] index`` is
    an ABSOLUTE gEventGlobal bit: it is NEVER offset by any campaign/journey flag-window (only the nameless
    auto-flags carry a deployed base), so the save stores it at exactly ``index`` in every mode -- this is a
    pure identity map, no offset arithmetic. Fail-safe: a malformed table (``collect_flag_defs`` raises) ->
    ``{}`` (no annotation rather than a wrong one). A duplicate index under different names -> an explicit
    ambiguity sentinel (never a silent pick)."""
    try:
        # index collisions are surfaced below as the ambiguity sentinel, not refused here
        collect_flag_defs(raw, check_index_collisions=False)   # validate band + duplicate-name, as the build does
    except (ValueError, TypeError):
        return {}
    seen: dict = {}                            # idx -> [names], to flag a cross-name index collision
    for fdef in raw.get("flag", []) or []:
        try:
            idx, name = int(fdef["index"]), str(fdef["name"])
        except (KeyError, TypeError, ValueError):
            continue
        names = seen.setdefault(idx, [])
        if name not in names:
            names.append(name)
    return {idx: (names[0] if len(names) == 1 else "<ambiguous: " + " / ".join(names) + ">")
            for idx, names in seen.items()}


def _fmt_bits(bits, names=None) -> str:
    """Render a bit list (capped at 20, matching the existing summary cap) -- labelling any bit present in
    ``names`` as ``bit=name``. With ``names`` empty/None the output is byte-identical to ``str(bits[:20])`` +
    the ' ...' elision, so an un-annotated report is unchanged."""
    names = names or {}
    shown = [f"{b}={names[b]}" if b in names else str(b) for b in bits[:20]]
    return "[" + ", ".join(shown) + "]" + (" ..." if len(bits) > 20 else "")


def collect_safe_flag_indices(raw: dict) -> set:
    """Every SAFE-BAND gEventGlobal bit index the project references as a story flag -- ``[[flag]]`` defs,
    ``[startup].flags``, and every content section's flag fields (``requires_flag``/``flag``/``set_flag``/
    ``set_flags``, recursing options/steps). Assumes :func:`resolve_project_flags` already ran (references are
    ints); out-of-band / non-int values are dropped. Used to RESERVE these so an auto-allocated ``[[logic_add]]``
    once-guard never aliases an authored story flag (which would silently pre-fire the guard)."""
    out: set = set()

    def _take(v):
        if isinstance(v, int) and not isinstance(v, bool) and is_safe_custom(v):
            out.add(v)

    try:
        for idx in collect_flag_defs(raw).values():
            _take(idx)
    except ValueError:                                 # a malformed [[flag]] table -> load already failed; ignore here
        pass
    su = raw.get("startup")
    if isinstance(su, dict):
        for p in su.get("flags", []) or []:
            if isinstance(p, dict):
                _take(p.get("flag"))

    def _walk(item):
        if not isinstance(item, dict):
            return
        for k in _FLAG_INDEX_KEYS:
            _take(item.get(k))
        for k in _FLAG_PAIR_KEYS:
            pair = item.get(k)
            if isinstance(pair, list) and pair:
                _take(pair[0])
        for sf in (item.get("set_flags") or []):
            if isinstance(sf, dict):
                _take(sf.get("flag"))
        for sub in ("options", "steps"):
            for it in (item.get(sub) or []):
                _walk(it)
    for sec in _FLAG_SECTIONS:
        val = raw.get(sec)
        if isinstance(val, dict):
            _walk(val)
        elif isinstance(val, list):
            for it in val:
                _walk(it)
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


def _resolve_flag_dicts(lst, name_map: dict):
    """Resolve the ``flag`` field (name -> int) in a ``[{flag = <name|index>, value = 0|1}, ...]`` list --
    the shape used by a gateway's ``set_flags`` (on-exit advance) and ``[startup]``'s ``flags`` (presets).
    Rewrites in place; a non-list or a dict without ``flag`` is left untouched."""
    if isinstance(lst, list):
        for p in lst:
            if isinstance(p, dict) and "flag" in p:
                p["flag"] = resolve(p["flag"], name_map)


def _resolve_item(item: dict, name_map: dict):
    """Rewrite a content item's flag fields (names -> ints) in place, recursing into options/steps."""
    for k in _FLAG_INDEX_KEYS:
        if k in item:
            item[k] = resolve(item[k], name_map)
    for k in _FLAG_PAIR_KEYS:
        if k in item and isinstance(item[k], list) and item[k]:
            item[k] = [resolve(item[k][0], name_map)] + list(item[k][1:])
    _resolve_flag_dicts(item.get("set_flags"), name_map)   # gateway on-exit advance (write-side story flags)
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
    su = raw.get("startup")                        # [startup] is a single table; its `flags` presets carry names
    if isinstance(su, dict):
        _resolve_flag_dicts(su.get("flags"), name_map)
    return name_map


# ============================ save inspector (VIEW) ============================
@dataclass
class SaveReport:
    scenario_counter: int
    milestone: tuple | None          # (value, beat) of the nearest milestone <= scenario, or None
    eiko_abducted: bool
    field_entrance: int
    treasure_hunter_points: int
    mognet_locks: int                # set bits in the Mognet lock band 8376-8511 (letters given + read)
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
    chests = sum(_count_bits(blob[b]) for b in range(MOGNET_LOCK_LO >> 3, (MOGNET_LOCK_HI >> 3) + 1))
    set_bits = [byte * 8 + bit for byte in range(2048) for bit in range(8) if blob[byte] >> bit & 1]
    named = [(w, _read_word(blob, w.byte, w.width, w.signed)) for w in NAMED_WORDS
             if _read_word(blob, w.byte, w.width, w.signed) != 0]
    return SaveReport(
        scenario_counter=scenario, milestone=nearest_milestone(scenario),
        eiko_abducted=EIKO_ABDUCTED_LO <= scenario <= EIKO_ABDUCTED_HI,
        field_entrance=_read_word(blob, 2, 2, True), treasure_hunter_points=th,
        mognet_locks=chests, set_bits=set_bits, named_words=named)


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


def _group_set_bits(set_bits):
    """Group set story BITs by named region. Returns ``(by_region{name:[bits]}, custom[bits],
    unmapped[bits], n_story)``. Bits inside a named WORD var's bytes (ScenarioCounter/FieldEntrance/...)
    are EXCLUDED -- those are word data, not story bits. Shared by :func:`render_report` (single save)
    and :func:`render_diff` (the set/cleared deltas) so both classify a bit the same way."""
    word_bytes = {b for w in NAMED_WORDS for b in range(w.byte, w.byte + w.width)}
    by_region: dict = {}
    custom, unmapped, n_story = [], [], 0
    for bit in set_bits:
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
    return by_region, custom, unmapped, n_story


def render_report(rep: SaveReport, *, show_bits: bool = False, names: dict | None = None) -> str:
    """A human-readable summary of a decoded save. ``names`` (an optional ``{absolute_bit: authored_name}`` map,
    e.g. from :func:`project_flag_names` for the open project) labels matching custom-band bits; empty/None
    leaves the output byte-identical."""
    L = ["FF9 gEventGlobal (story state)", "=" * 32]
    ms = f"  ->  {rep.milestone[1]} (>= {rep.milestone[0]})" if rep.milestone else "  (before the first milestone)"
    L.append(f"ScenarioCounter : {rep.scenario_counter}{ms}")
    if rep.eiko_abducted:
        L.append("                  [IsEikoAbducted window -- Desert Palace]")
    L.append(f"FieldEntrance   : {rep.field_entrance}")
    L.append(f"Treasure-Hunter : {rep.treasure_hunter_points} pts   (chests/icons opened)")
    L.append(f"Mognet locks    : {rep.mognet_locks}   (letters given + read; bits {MOGNET_LOCK_LO}-{MOGNET_LOCK_HI})")
    if rep.named_words:
        L.append("Named vars set  :")
        for w, v in rep.named_words:
            L.append(f"  - {w.name} = {v}")
    by_region, custom, unmapped, n_story = _group_set_bits(rep.set_bits)
    L.append(f"Set story bits  : {n_story} "
             f"(in {len(by_region)} known region(s), {len(custom)} custom, {len(unmapped)} unmapped)")
    for name, bits in sorted(by_region.items()):
        L.append(f"  [{name}] {len(bits)} bit(s)")
    if custom:
        L.append(f"  [custom {FIRST_SAFE_FLAG}+] {len(custom)} bit(s): {_fmt_bits(custom, names)}")
    if show_bits and unmapped:
        L.append(f"  [unmapped] {unmapped}")
    return "\n".join(L)


@dataclass
class FlagDiff:
    """The story-state delta between two saves (A -> B): what a story beat / play session changed."""
    scenario_from: int
    scenario_to: int
    field_entrance_from: int
    field_entrance_to: int
    th_from: int
    th_to: int
    mognet_locks_from: int
    mognet_locks_to: int
    bits_set: list = field(default_factory=list)       # bits TRUE in B but not A (newly set)
    bits_cleared: list = field(default_factory=list)   # bits TRUE in A but not B (cleared)
    words_changed: list = field(default_factory=list)  # [(WordVar, old, new)] (excl. Scenario/FieldEntrance)

    @property
    def empty(self) -> bool:
        return not (self.bits_set or self.bits_cleared or self.words_changed
                    or self.scenario_from != self.scenario_to
                    or self.field_entrance_from != self.field_entrance_to
                    or self.th_from != self.th_to or self.mognet_locks_from != self.mognet_locks_to)


def diff_reports(a: SaveReport, b: SaveReport) -> FlagDiff:
    """Diff two decoded saves (A -> B). The set/cleared bit lists + the changed word vars are what a story
    beat (or a play session) wrote to ``gEventGlobal`` -- the practical way to learn what a transition does
    (save before, do the thing, save after, diff). Scenario/FieldEntrance are reported as their own deltas
    (not in ``words_changed``, to avoid double-listing)."""
    sa, sb = set(a.set_bits), set(b.set_bits)
    wa = {w.name: (w, v) for w, v in a.named_words}
    wb = {w.name: (w, v) for w, v in b.named_words}
    words = []
    for name in sorted(set(wa) | set(wb)):
        if name in ("ScenarioCounter", "FieldEntrance"):     # shown as dedicated deltas below
            continue
        w = (wa.get(name) or wb.get(name))[0]
        old = wa[name][1] if name in wa else 0
        new = wb[name][1] if name in wb else 0
        if old != new:
            words.append((w, old, new))
    return FlagDiff(
        scenario_from=a.scenario_counter, scenario_to=b.scenario_counter,
        field_entrance_from=a.field_entrance, field_entrance_to=b.field_entrance,
        th_from=a.treasure_hunter_points, th_to=b.treasure_hunter_points,
        mognet_locks_from=a.mognet_locks, mognet_locks_to=b.mognet_locks,
        bits_set=sorted(sb - sa), bits_cleared=sorted(sa - sb), words_changed=words)


def render_diff(diff: FlagDiff, *, show_bits: bool = False, names: dict | None = None) -> str:
    """A human-readable A -> B story-state delta (the output of :func:`diff_reports`). ``names`` labels matching
    custom-band bits (see :func:`render_report`); empty/None leaves the output byte-identical."""
    def beat(v):
        m = nearest_milestone(v)
        return f"{v} ({m[1]})" if m else f"{v}"
    L = ["FF9 gEventGlobal diff (A -> B)", "=" * 32]
    if diff.scenario_from != diff.scenario_to:
        L.append(f"ScenarioCounter : {beat(diff.scenario_from)}  ->  {beat(diff.scenario_to)}")
    if diff.field_entrance_from != diff.field_entrance_to:
        L.append(f"FieldEntrance   : {diff.field_entrance_from}  ->  {diff.field_entrance_to}")
    if diff.th_from != diff.th_to:
        L.append(f"Treasure-Hunter : {diff.th_from}  ->  {diff.th_to} pts  ({diff.th_to - diff.th_from:+d})")
    if diff.mognet_locks_from != diff.mognet_locks_to:
        L.append(f"Mognet locks    : {diff.mognet_locks_from}  ->  {diff.mognet_locks_to}  "
                 f"({diff.mognet_locks_to - diff.mognet_locks_from:+d})")
    if diff.words_changed:
        L.append("Named vars changed :")
        for w, old, new in diff.words_changed:
            L.append(f"  - {w.name}: {old} -> {new}")
    for tag, bits in (("SET (newly true)", diff.bits_set), ("CLEARED (now false)", diff.bits_cleared)):
        if not bits:
            continue
        by_region, custom, unmapped, n = _group_set_bits(bits)
        L.append(f"Bits {tag}: {n}")
        for name, bs in sorted(by_region.items()):
            L.append(f"  [{name}] {len(bs)} bit(s): {bs[:20]}{' ...' if len(bs) > 20 else ''}")
        if custom:
            L.append(f"  [custom {FIRST_SAFE_FLAG}+] {len(custom)} bit(s): {_fmt_bits(custom, names)}")
        if unmapped:
            L.append(f"  [unmapped] {len(unmapped)}" + (f": {unmapped}" if show_bits else " bit(s)"))
    if diff.empty:
        L.append("(no story-state difference)")
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
