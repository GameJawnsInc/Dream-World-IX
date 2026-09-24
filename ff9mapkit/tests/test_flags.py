"""Tests for the story-flag registry + save inspector (ff9mapkit.flags) and the build-time name resolver."""
import base64
import struct

import pytest

from ff9mapkit import flags


# ---- registry ---------------------------------------------------------------------------
def test_safe_band_constants():
    assert flags.FIRST_SAFE_FLAG == 8712                       # first bit clear of ALL real-FF9 usage
    assert (flags.MOGNET_LOCK_LO, flags.MOGNET_LOCK_HI) == (8376, 8511)
    assert (flags.CHEST_FLAG_LO, flags.CHEST_FLAG_HI) == (8376, 8511)   # the deprecated alias
    assert (flags.READMAIL_PAYLOAD_LO, flags.READMAIL_PAYLOAD_HI) == (8512, 8711)
    assert flags.CHOICE_SCRATCH_FLOOR == 16320
    # the safe floor sits exactly one byte past stock's highest byte-addressed var (1088)
    assert flags.FIRST_SAFE_FLAG == 1089 * 8


def test_bit_addressing_and_regions():
    assert flags.bit_to_byte(8376) == (1047, 0)               # Mognet lock band start
    assert flags.bit_region(8400).name == "mognet_give_locks" and flags.bit_region(8400).reserved
    assert flags.bit_region(8460).name == "mognet_read_locks" and flags.bit_region(8460).reserved
    assert flags.bit_region(8520).name == "mognet_readmail_payload" and flags.bit_region(8520).reserved
    assert flags.bit_region(8650).name == "mognet_readmail_payload"   # the sender run 8632-8711
    assert flags.bit_region(8712) is None                     # safe custom space is unmapped
    assert flags.is_reserved(8400) and not flags.is_reserved(8712)
    assert flags.is_safe_custom(8712) and not flags.is_safe_custom(8400)
    assert not flags.is_safe_custom(8520)                     # the payload band is NOT allocatable
    assert not flags.is_safe_custom(16320)                    # choice scratch floor is out of band


def test_named_word_at():
    """A bit landing inside a NAMED_WORDS byte range resolves to that word -- BIT_REGIONS/STORY_REGIONS
    don't cover these (they're a separate axis), so this is the only way to catch a raw edit into one."""
    assert flags.named_word_at(128).name == "TranceGaugeFlag"        # byte 16, bit 128-135
    assert flags.named_word_at(135).name == "TranceGaugeFlag"        # top of the same byte
    assert flags.named_word_at(0).name == "ScenarioCounter"          # byte 0 (width 2 -> bits 0-15)
    assert flags.named_word_at(15).name == "ScenarioCounter"
    assert flags.named_word_at(32) is None                           # byte 4 -- the gap before TranceGaugeFlag
    assert flags.named_word_at(2600) is None                         # far outside any named word
    # the argument is a BIT index; a byte offset (bit // 8) silently checks byte bit // 64 instead
    assert flags.named_word_at(1816).name == "MagicDisabledFlag"     # byte 227 = bits 1816-1823
    assert flags.named_word_at(1816 // 8) is None                    # ...the byte form lands on byte 28
    assert flags.named_word_at(200) is None                          # byte 25 -- no word
    assert flags.named_word_at(200 // 8).name == "FieldEntrance"     # ...the byte form lands on byte 3


def test_lock_band_is_disjoint_from_engine_treasure_hunter_scoring():
    """The Mognet lock band (8376-8511, bytes 1047-1063) is a SEPARATE region from the engine's
    Treasure-Hunter scoring bytes (182-186 + 896-975). The kit must not conflate them: the lock band
    is reserved on field-script grounds (the moogle fields' switch-64 lock tables), NOT because
    GetTreasureHunterPoints reads it -- the band's old 'treasure-chest' name was exactly that
    conflation."""
    # TH scoring matches the engine method exactly (EventState.GetTreasureHunterPoints).
    assert flags.TH_POINT_RANGES == [(896, 960, 1), (966, 975, 1), (182, 186, 2)]
    # Those TH bytes are all BELOW the lock band's first byte (1047) -> the two regions never overlap.
    th_bytes = {b for lo, hi, _ in flags.TH_POINT_RANGES for b in range(lo, hi + 1)}
    lock_bytes = set(range(flags.MOGNET_LOCK_LO >> 3, (flags.MOGNET_LOCK_HI >> 3) + 1))
    assert th_bytes.isdisjoint(lock_bytes)
    assert max(th_bytes) < min(lock_bytes)
    # The region's provenance must NOT (re-)claim the engine TH method -- it is the mognet decode.
    src = flags.bit_region(8400).source
    assert "GetTreasureHunterPoints" not in src and "mognet" in src


def test_scenario_milestones_and_eiko():
    assert flags.nearest_milestone(2510) == (2500, "Ice Cavern")
    assert flags.nearest_milestone(7200) == (7200, "Alexandria Castle")    # in-game-validated anchor
    assert flags.nearest_milestone(1) is None                 # before the first milestone (1000)
    assert flags.EIKO_ABDUCTED_LO <= 9860 <= flags.EIKO_ABDUCTED_HI
    assert not (flags.EIKO_ABDUCTED_LO <= 9990 <= flags.EIKO_ABDUCTED_HI)   # engine uses `< 9990`


def test_scenario_milestones_census_verified():
    """The 52-anchor census-grounded table: the labels the old zone-coded table got wrong, + monotonicity."""
    m = flags.SCENARIO_MILESTONES
    assert sorted(m) == list(m) and len(m) >= 50           # sorted (nearest_milestone relies on it) + fuller
    assert m[5900] == "Fossil Roo"                          # was wrongly "Iifa Tree" (zone-code error)
    assert m[9990] == "Mount Gulug"                         # was wrongly "Outer Continent"
    assert m[9400] == "Blue Narciss"                        # was wrongly "Hilda Garde"
    assert m[11610] == "Memoria" and m[11765] == "Crystal World"   # was conflated as "Crystal World"
    assert m[3800] == "Burmecia"                            # a real beat the old table lost
    assert flags.nearest_milestone(5950) == (5900, "Fossil Roo")


def test_engine_reader_named_words():
    """The engine-reader pass: byte vars the Memoria C# reads at a fixed index (all tier-a, cited)."""
    byname = {w.name: w for w in flags.NAMED_WORDS}
    assert byname["NaviMode"].byte == 100 and byname["WorldmapTransport"].byte == 102
    assert byname["MoveControl"].byte == 190 and byname["MoveControl"].signed       # SByte transport idx
    assert byname["MagicDisabledFlag"].byte == 227                                  # Oeilvert anti-magic
    assert all(w.tier == "a" for w in flags.NAMED_WORDS)                            # every named word engine-cited
    # byte 227 (bit 1816) is now the MagicDisabledFlag word, not a separate Oeilvert bit region
    assert not any(r.name == "oeilvert_events" for r in flags.STORY_REGIONS)
    rep = flags.decode_gEventGlobal(bytes(bytearray(2048)[:102]) + b"\x08" + bytes(2048 - 103))
    assert any(w.name == "WorldmapTransport" and v == 8 for w, v in rep.named_words)  # 8 = Invincible


def test_worldmap_navi_location_words():
    """Engine-reader DEPTH pass: bytes 92-99 are the worldmap Navi known-location bitmasks
    (keventNaviLocF0..F3), read at those fixed indices -> named UInt16 word vars (tier a), not the loose
    'write-only worldmap-unlock bits' they previously read as."""
    byname = {w.name: w for w in flags.NAMED_WORDS}
    for name, byte in (("WorldmapKnownLocationsF0", 92), ("WorldmapKnownLocationsF1", 94),
                       ("WorldmapKnownLocationsF2", 96), ("WorldmapKnownLocationsF3", 98)):
        assert byname[name].byte == byte and byname[name].width == 2 and byname[name].tier == "a"
    b = bytearray(2048)
    b[92:94] = struct.pack("<H", 0x07C0)            # the engine's "Treno & South Gates" known-locations mask
    rep = flags.decode_gEventGlobal(bytes(b))
    assert any(w.name == "WorldmapKnownLocationsF0" and v == 0x07C0 for w, v in rep.named_words)
    # the value's set bits are now recognized as WORD data, NOT counted as loose story/unmapped bits
    _by_region, _custom, unmapped, n_story = flags._group_set_bits(rep.set_bits)
    assert n_story == 0 and unmapped == []


def test_story_regions_and_named_bits():
    """Informational story clusters annotate set bits; engine-grounded named bits beat the broad band."""
    assert all(not r.reserved for r in flags.STORY_REGIONS)         # informational, never block allocation
    assert flags.bit_region(2600).name == "lindblum_events"        # a story cluster (byte 325)
    assert not flags.is_reserved(2600) and not flags.is_safe_custom(2600)   # named but below the safe band
    assert flags.bit_region(815).name == "mognet_central_discovered"        # specific name wins
    assert flags.bit_region(814).name == "chocobo_paradise_discovered"
    assert flags.bit_region(815).reserved                          # engine save state -> reserved
    assert flags.bit_region(770).name == "worldmap_unlocks"        # rest of the band keeps the broad name
    assert "AteCheck" in flags.ATE_STATE_LOCATION                  # ATE-seen is NOT in the heap (recorded)


def test_outpost_word_sits_in_the_stock_clear_hole():
    """THE 2026-07-19 REGRESSION PIN. The deathrules outpost word (a GLOB_UINT16 field id) once sat at
    bytes 1060-1061 -- INSIDE the Mognet READ-lock band, where reading letter variants 40-55 mutated the
    stored field id (a wipe-warp to a garbage field) and entering an outpost rewrote real letters' lock
    state. It now lives in the read-mail payload's stock-clear hole (bytes 1074-1078), and this test
    keeps it there: disjoint from BOTH lock tables (all 64 variants, both anchors), from both stock
    payload byte runs, and below the author band."""
    from ff9mapkit.battle import deathrules
    from ff9mapkit.content import mognet
    ob = deathrules.OUTPOST_BYTE
    assert ob == 1074
    word_bytes = {ob, ob + 1}
    for v in range(mognet.VARIANT_LIMIT):                       # neither lock table touches the word
        assert mognet.give_lock_bit(v) >> 3 not in word_bytes
        assert mognet.read_lock_bit(v) >> 3 not in word_bytes
    assert word_bytes.isdisjoint(range(1064, 1074))             # the stock variant-payload run
    assert word_bytes.isdisjoint(range(1079, 1089))             # the stock sender-payload run
    assert (ob + 1) * 8 <= flags.FIRST_SAFE_FLAG                # below the author band
    # and the wipe marker stays bit-disjoint from the two real stock bools sharing byte 1063
    from ff9mapkit.battle.deathrules import WIPE_FLAG_DEFAULT
    assert WIPE_FLAG_DEFAULT not in (8510, 8511) and flags.is_reserved(WIPE_FLAG_DEFAULT)


def test_lock_band_formula_covers_exactly_the_reserved_bands():
    """Every variant's give/read lock bit falls inside its named reserved region -- the attribution the
    band carried for months ('treasure chests') could never have passed this."""
    from ff9mapkit.content import mognet
    for v in range(mognet.VARIANT_LIMIT):
        assert flags.bit_region(mognet.give_lock_bit(v)).name == "mognet_give_locks"
        assert flags.bit_region(mognet.read_lock_bit(v)).name == "mognet_read_locks"


def test_byte23_is_named_bit_by_bit():
    """Byte 23 has no anonymous bits. The 2026-09-24 var sweep (818 field, 13 world, 562 battle .eb,
    every var type incl. byte/word spans) found stock touching only 184 (the menu guard), 189 (the
    save-point tent-rest guard, 65 fields) and 191 (boot scratch); 185-188 + 190 are stock-clear, named
    as such and NOT reserved (they were in no region, so nothing that allocates or lints moves)."""
    assert [flags.bit_region(b).name for b in range(184, 192)] == [
        "field_menu_guard", "byte23_spare", "byte23_spare", "byte23_spare", "byte23_spare",
        "savepoint_tent_guard", "byte23_spare", "boot_scratch"]
    assert flags.is_reserved(189)                                    # every rest rewrites it
    assert not any(flags.is_reserved(b) for b in (185, 186, 187, 188, 190))


def test_lock_margin_byte_is_named_bit_by_bit():
    """Byte 1063: the kit's wipe marker (8508) and stock's moogle-talk latches (8510-8511, 58 moogle
    fields) carry their own names; 8504-8507 + 8509 keep the margin name. The whole byte stays reserved."""
    from ff9mapkit.battle.deathrules import WIPE_FLAG_DEFAULT
    assert flags.bit_region(WIPE_FLAG_DEFAULT).name == "deathrules_wipe_marker"
    assert flags.bit_region(8510).name == flags.bit_region(8511).name == "mognet_moogle_latches"
    assert {flags.bit_region(b).name for b in (8504, 8505, 8506, 8507, 8509)} == {"mognet_lock_margin"}
    assert all(flags.is_reserved(b) for b in range(8504, 8512))


def test_readmail_payload_hole_is_named():
    """The payload band's stock-clear hole (bytes 1074-1078; the 2026-09-24 sweep of 818 field, 13 world
    and 562 battle .eb found no access at any width) is not payload scratch: bytes 1074-1075 are the kit's
    save-backed OUTPOST word, the rest is clear. Both keep the band's reservation."""
    from ff9mapkit.battle.deathrules import OUTPOST_BYTE
    word = range(OUTPOST_BYTE * 8, OUTPOST_BYTE * 8 + 16)
    assert {flags.bit_region(b).name for b in word} == {"deathrules_outpost_word"}
    assert {flags.bit_region(b).name for b in range(1076 * 8, 1079 * 8)} == {"readmail_payload_hole"}
    assert flags.bit_region(1074 * 8 - 1).name == flags.bit_region(1079 * 8).name == "mognet_readmail_payload"
    assert all(flags.is_reserved(b) for b in range(flags.READMAIL_PAYLOAD_LO, flags.READMAIL_PAYLOAD_HI + 1))


# ---- the story-noise mask (studies/story-trace/PLAN.md, owner decision 6) ----------------------
def test_story_noise_mask_members():
    """The ONE noise mask every story analysis drops: the stock handshakes, the Mognet letter network
    (mailbox, lock tables, read-mail payload runs), and the kit's runtime scratch -- including every bit
    of bytes 2032-2041, the engine's own NetSyncState mask."""
    noise = flags.story_noise_bits()
    assert {184, 189, 191} <= noise                                  # byte-23 handshakes
    assert {8192, 8367, 8376, 8439, 8440, 8503, 8512, 8591, 8632, 8711} <= noise   # Mognet, end to end
    assert flags.READMAIL_PAYLOAD_LO in noise and flags.READMAIL_PAYLOAD_HI in noise
    from ff9mapkit.battle.deathrules import WIPE_FLAG_DEFAULT
    assert WIPE_FLAG_DEFAULT in noise
    assert {flags.BEHAVIOR_FLAG_BASE, flags.BEHAVIOR_FLAG_END, flags.SIEGE_REQUEST_BASE,
            flags.BEHAVIOR_BYTE_BASE * 8, flags.BEHAVIOR_BYTE_END * 8 + 7, flags.QTE_SCRATCH_FLOOR} <= noise
    netsync = set(range(2032 * 8, 2042 * 8))                         # NetSyncState.MaskLo..MaskHi
    assert netsync <= noise and {b for b in noise if b >= flags.COOP_CELLS_FLOOR} == netsync
    assert isinstance(noise, frozenset) and noise is flags.story_noise_bits()


def test_story_noise_mask_exclusions():
    """Chosen by region NAME, never by ``reserved``: reserved bands that are live progression stay story,
    and a stock-clear bit with no owner stays visible (a write there is a surprise, not noise)."""
    noise = flags.story_noise_bits()
    for lo, hi in ((736, 823),                                                   # worldmap_unlocks
                   (flags.KIT_WORLD_FLAG_BASE, flags.KIT_WORLD_FLAG_BASE + 31),  # the ferry words
                   (flags.NAMEPLATE_EXPLORED_FLOOR, flags.QTE_SCRATCH_FLOOR - 1)):
        assert all(flags.is_reserved(b) for b in range(lo, hi + 1))
        assert noise.isdisjoint(range(lo, hi + 1))
    assert noise.isdisjoint({185, 186, 187, 188, 190})               # byte23_spare
    assert noise.isdisjoint(range(8368, 8376))                       # byte 1046, between mailbox + locks
    assert noise.isdisjoint({8504, 8505, 8506, 8507, 8509})          # the lock margin's clear bits
    assert noise.isdisjoint({8510, 8511})                            # moogle latches: real save state
    assert noise.isdisjoint(range(1074 * 8, 1079 * 8))               # the payload hole: outpost word + clear
    assert noise.isdisjoint(range(flags.AUTO_EVENT_BASE, flags.BEHAVIOR_FLAG_BASE))   # kit once-bands
    assert noise.isdisjoint({flags.FIRST_SAFE_FLAG, 2600, 3458, 3718})               # story proper
    # the WIDE Blackboard ([behavior] byte_band = "wide", every [siege]) is NOT masked: its flags 9520+
    # and bytes 1220+ sit in the campaign lane, where a global region would hide real campaign bits
    from ff9mapkit.content import behavior
    assert noise.isdisjoint(range(behavior.WIDE_FLAG_BASE, flags.KIT_STANDING_FLOOR))
    # exactly the listed names resolve into the mask -- nothing else, nothing missing
    names = set(flags.STORY_NOISE_REGION_NAMES)
    for b in range(2048 * 8):
        r = flags.bit_region(b)
        assert (b in noise) == bool(r and r.name in names), b


def test_non_story_bits_is_the_noise_plus_the_side_state():
    """The story POPULATIONS (the census falsifier's sites, fork-report's seed candidates) drop the noise
    AND the side state -- real save state that is not story progression (the moogle-talk latches; 8511
    is the first-meeting Mognet explanation). story-seed and a trace drop only the noise, so a latch
    read is still refused by name and a latch write is still a compared key."""
    noise, non_story = flags.story_noise_bits(), flags.non_story_bits()
    assert non_story - noise == {8510, 8511}
    assert noise < non_story and non_story is flags.non_story_bits()
    assert not set(flags.STORY_NOISE_REGION_NAMES) & set(flags.STORY_SIDE_STATE_REGION_NAMES)
    # over the Mognet run the populations drop what the census's old 8192-8711 did, less the stock-clear
    # bits that are now named and visible: byte 1046, the margin's clear bits and the payload hole
    clear = set(range(8368, 8376)) | {8504, 8505, 8506, 8507, 8509} | set(range(1074 * 8, 1079 * 8))
    assert non_story & set(range(8192, 8712)) == set(range(8192, 8712)) - clear


def test_story_noise_names_are_checked_where_the_mask_is_built(monkeypatch):
    """A misspelled name, a region wholly shadowed by an earlier one, or a name in both tiers would mask
    the wrong bits without a sound -- story_noise_bits / non_story_bits refuse all three (the overlap in
    story_noise_bits itself: it is what story-seed and the trace call, and they would lose the side state)."""
    def clear():
        flags.story_noise_bits.cache_clear()
        flags.non_story_bits.cache_clear()
    clear()
    try:
        monkeypatch.setattr(flags, "STORY_NOISE_REGION_NAMES", ("field_menu_guard", "handshake"))
        with pytest.raises(ValueError, match="not a BIT_REGIONS name"):
            flags.story_noise_bits()
        ghost = flags.BitRegion("ghost", 184, 184, "", True, "a", "")
        monkeypatch.setattr(flags, "BIT_REGIONS", flags.BIT_REGIONS + [ghost])
        monkeypatch.setattr(flags, "STORY_NOISE_REGION_NAMES", ("ghost",))
        with pytest.raises(ValueError, match="shadowed"):
            flags.story_noise_bits()
        monkeypatch.setattr(flags, "STORY_NOISE_REGION_NAMES", ("field_menu_guard",))
        monkeypatch.setattr(flags, "STORY_SIDE_STATE_REGION_NAMES", ("latches",))
        clear()
        with pytest.raises(ValueError, match="not a BIT_REGIONS name"):
            flags.non_story_bits()
        monkeypatch.setattr(flags, "STORY_SIDE_STATE_REGION_NAMES", ("field_menu_guard",))
        clear()
        with pytest.raises(ValueError, match="both"):
            flags.story_noise_bits()
        with pytest.raises(ValueError, match="both"):
            flags.non_story_bits()
    finally:
        monkeypatch.undo()
        clear()
    assert 184 in flags.story_noise_bits() and 8511 in flags.non_story_bits()


# ---- author-side name resolution --------------------------------------------------------
def test_collect_flag_defs_valid():
    nm = flags.collect_flag_defs({"flag": [{"name": "Switch Pulled", "index": 8720}]})
    assert nm == {"switchpulled": 8720}                       # normalized key (alnum/underscore, lowercased)


def test_collect_flag_defs_rejects_bad_defs():
    with pytest.raises(ValueError, match="needs both"):
        flags.collect_flag_defs({"flag": [{"name": "x"}]})    # missing index
    with pytest.raises(ValueError, match="Mognet lock band"):
        flags.collect_flag_defs({"flag": [{"name": "x", "index": 8400}]})   # in the lock band
    with pytest.raises(ValueError, match="read-mail payload"):
        flags.collect_flag_defs({"flag": [{"name": "x", "index": 8560}]})   # in the payload band
    with pytest.raises(ValueError, match="outside the safe"):
        flags.collect_flag_defs({"flag": [{"name": "x", "index": 8000}]})   # below the safe floor
    with pytest.raises(ValueError, match="duplicate"):
        flags.collect_flag_defs({"flag": [{"name": "x", "index": 8720}, {"name": "X", "index": 8721}]})


def test_collect_flag_defs_rejects_duplicate_index():
    """Two different names claiming the same index would silently alias two story flags onto one
    gEventGlobal bit -- refused just like a duplicate name."""
    with pytest.raises(ValueError, match="both use index"):
        flags.collect_flag_defs({"flag": [{"name": "quest_a_done", "index": 8800},
                                          {"name": "quest_b_done", "index": 8800}]})


def test_collect_flag_defs_index_collision_check_can_be_disabled():
    """`project_flag_names` opts out (it must survive + display an already-authored ambiguous table, not
    refuse to load it) -- with the check off, both names resolve, same index, no error."""
    nm = flags.collect_flag_defs({"flag": [{"name": "a", "index": 8730}, {"name": "b", "index": 8730}]},
                                 check_index_collisions=False)
    assert nm == {"a": 8730, "b": 8730}


def test_resolve_passthrough_and_names():
    nm = {"lever": 8730}
    assert flags.resolve(8730, nm) == 8730                    # int passes through
    assert flags.resolve("8730", nm) == 8730                  # digit-string passes through
    assert flags.resolve("lever", nm) == 8730                 # name resolves
    with pytest.raises(ValueError, match="unknown flag name"):
        flags.resolve("levr", nm)                             # typo -> error (with a hint)


def test_resolve_project_flags_rewrites_and_is_noop_when_numeric():
    raw = {
        "flag": [{"name": "door_open", "index": 8720}],
        "event": [{"name": "e", "set_flag": ["door_open", 1]}],
        "npc": [{"name": "g", "requires_flag": "door_open"}],
        "gateway": [{"to": 4000, "requires_flag_clear": 8721}],     # numeric stays numeric
        "choice": [{"options": [{"text": "y", "requires_flag": "door_open"}]}],
    }
    flags.resolve_project_flags(raw)
    assert raw["event"][0]["set_flag"] == [8720, 1]
    assert raw["npc"][0]["requires_flag"] == 8720
    assert raw["gateway"][0]["requires_flag_clear"] == 8721
    assert raw["choice"][0]["options"][0]["requires_flag"] == 8720

    numeric = {"npc": [{"name": "g", "requires_flag": 8720}]}       # no names -> unchanged
    before = repr(numeric)
    flags.resolve_project_flags(numeric)
    assert repr(numeric) == before


def test_resolve_project_flags_campaign_names():
    raw = {"npc": [{"name": "g", "requires_flag": "shared"}]}       # name from the campaign, not local
    flags.resolve_project_flags(raw, {"shared": 8800})
    assert raw["npc"][0]["requires_flag"] == 8800


# ---- save inspector ---------------------------------------------------------------------
def _synthetic_blob():
    b = bytearray(2048)
    b[0:2] = struct.pack("<H", 9860)        # ScenarioCounter in the Eiko-abducted window
    b[2:4] = struct.pack("<h", 5)           # FieldEntrance
    b[1047] = 0xFF                          # 8 chest bits (8376-8383)
    b[896] = 0x07                           # 3 treasure-hunter points (standard region, 1pt/bit)
    b[182] = 0x03                           # 2 double-region bits -> 4 points
    b[8720 >> 3] |= 1 << (8720 & 7)         # a custom story flag in the safe band
    return bytes(b)


def test_decode_gEventGlobal():
    rep = flags.decode_gEventGlobal(_synthetic_blob())
    assert rep.scenario_counter == 9860 and rep.eiko_abducted
    assert rep.milestone == (9800, "Desert Palace")           # nearest area anchor <= 9860
    assert rep.field_entrance == 5
    assert rep.mognet_locks == 8
    assert rep.treasure_hunter_points == 3 + 4                # 3 (1pt) + 2 bits *2pt
    assert (flags.NAMED_WORDS[0], 9860) in rep.named_words    # ScenarioCounter named


def test_decode_tolerates_short_blob():
    rep = flags.decode_gEventGlobal(b"\x10\x00")             # 2 bytes -> ScenarioCounter 16, rest zero
    assert rep.scenario_counter == 16 and rep.mognet_locks == 0


def test_gEventGlobal_from_save_forms(tmp_path):
    b = _synthetic_blob()
    b64 = base64.b64encode(b).decode()
    js = '{"profile": {"gEventGlobal": "%s"}}' % b64
    assert flags.gEventGlobal_from_save(js) == b              # JSON text
    assert flags.gEventGlobal_from_save(b64) == b             # bare Base64
    p = tmp_path / "save.json"
    p.write_text(js, encoding="utf-8")
    assert flags.gEventGlobal_from_save(str(p)) == b          # JSON file path
    pb = tmp_path / "blob.b64"
    pb.write_text(b64 + "\n", encoding="utf-8")
    assert flags.gEventGlobal_from_save(str(pb)) == b          # file holding a bare Base64 blob (+ trailing nl)
    with pytest.raises(ValueError, match="no 'gEventGlobal'"):
        flags.gEventGlobal_from_save('{"profile": {}}')


def test_render_report_smoke():
    out = flags.render_report(flags.decode_gEventGlobal(_synthetic_blob()))
    assert "ScenarioCounter : 9860" in out and "Desert Palace" in out
    assert "Mognet locks    : 8" in out and "mognet_give_locks" in out


def test_project_flag_names_identity_and_failsafe():
    # a named [[flag]] index is an ABSOLUTE gEventGlobal bit -> identity map (never flag-window offset)
    raw = {"flag": [{"name": "got_sword", "index": 8720}, {"name": "door_open", "index": 8721}]}
    assert flags.project_flag_names(raw) == {8720: "got_sword", 8721: "door_open"}
    # fail-safe: a malformed / out-of-band table yields {} (no annotation, never a WRONG one)
    assert flags.project_flag_names({}) == {}
    assert flags.project_flag_names({"flag": [{"name": "x"}]}) == {}                  # missing index
    assert flags.project_flag_names({"flag": [{"name": "y", "index": 100}]}) == {}    # outside the safe band
    # two names on the SAME index -> an explicit ambiguity sentinel, never a silent pick
    assert flags.project_flag_names({"flag": [{"name": "a", "index": 8730},
                                              {"name": "b", "index": 8730}]}) == {8730: "<ambiguous: a / b>"}


def test_render_report_annotates_named_flag_and_is_byte_identical_without_names():
    b = bytearray(2048)
    b[8720 >> 3] |= 1 << (8720 & 7)                   # set custom-band bit 8720
    rep = flags.decode_gEventGlobal(bytes(b))
    assert 8720 in rep.set_bits
    bare = flags.render_report(rep)
    assert flags.render_report(rep, names=None) == bare == flags.render_report(rep, names={})  # no-project unchanged
    assert "8720" in bare and "got_sword" not in bare
    assert "8720=got_sword" in flags.render_report(rep, names={8720: "got_sword"})
    assert "ghost" not in flags.render_report(rep, names={9000: "ghost"})             # never label an UNSET bit
    # the diff renderer annotates the same way (and stays byte-identical with no names)
    rep0 = flags.decode_gEventGlobal(bytes(2048))
    diff = flags.diff_reports(rep0, rep)
    assert flags.render_diff(diff) == flags.render_diff(diff, names={})
    assert "8720=got_sword" in flags.render_diff(diff, names={8720: "got_sword"})


# ---- flags-diff: the A -> B story-state delta (what a beat / session wrote) --------------
def test_diff_reports_set_cleared_scenario_words_chests():
    a = bytearray(2048)
    a[0:2] = struct.pack("<H", 1000)        # scenario 1000
    a[1047] = 0xFF                          # 8 chest bits set in A (8376-8383)
    a[8720 >> 3] |= 1 << (8720 & 7)         # custom flag 8720 set in A (and B)
    a[16] = 1                               # TranceGaugeFlag = 1 in A (named word @ byte 16)
    b = bytearray(a)
    b[0:2] = struct.pack("<H", 2500)        # scenario 1000 -> 2500
    b[1047] = 0x0F                          # chest bits 8380-8383 CLEARED (8 -> 4)
    b[8721 >> 3] |= 1 << (8721 & 7)         # custom flag 8721 newly SET in B
    b[16] = 0                               # TranceGaugeFlag 1 -> 0
    diff = flags.diff_reports(flags.decode_gEventGlobal(bytes(a)), flags.decode_gEventGlobal(bytes(b)))
    assert (diff.scenario_from, diff.scenario_to) == (1000, 2500)
    assert 8721 in diff.bits_set and 8720 not in diff.bits_set       # 8720 was already set in A
    assert {8380, 8381, 8382, 8383} <= set(diff.bits_cleared)        # the 4 cleared chest bits
    assert (diff.mognet_locks_from, diff.mognet_locks_to) == (8, 4)
    assert ("TranceGaugeFlag", 1, 0) in [(w.name, o, n) for w, o, n in diff.words_changed]
    assert not diff.empty


def test_diff_excludes_scenario_field_entrance_from_words():
    a = bytearray(2048); a[0:2] = struct.pack("<H", 100); a[2:4] = struct.pack("<h", 1)
    b = bytearray(2048); b[0:2] = struct.pack("<H", 200); b[2:4] = struct.pack("<h", 3)
    diff = flags.diff_reports(flags.decode_gEventGlobal(bytes(a)), flags.decode_gEventGlobal(bytes(b)))
    names = {w.name for w, _o, _n in diff.words_changed}
    assert "ScenarioCounter" not in names and "FieldEntrance" not in names   # shown as dedicated deltas
    assert diff.field_entrance_from == 1 and diff.field_entrance_to == 3


def test_render_diff_smoke_and_empty():
    rep = flags.decode_gEventGlobal(_synthetic_blob())
    same = flags.diff_reports(rep, rep)
    assert same.empty and "no story-state difference" in flags.render_diff(same)
    out = flags.render_diff(flags.diff_reports(flags.decode_gEventGlobal(bytes(2048)), rep))
    assert "ScenarioCounter" in out and "->" in out and "Bits SET" in out


# ---- build integration: named flags produce IDENTICAL bytes to numeric ------------------
def _build_lever(tmp_path, gate_value, tag):
    """A one-shot lever field whose choice is gated by `gate_value` (an int OR a registered name)."""
    from ff9mapkit import build
    flagdef = ('[[flag]]\nname = "lever_pulled"\nindex = 8720\n\n'
               if isinstance(gate_value, str) else "")
    gate = f'"{gate_value}"' if isinstance(gate_value, str) else gate_value
    p = tmp_path / f"{tag}.field.toml"
    p.write_text(
        '[field]\nid = 4003\nname = "Z"\narea = 11\ntext_block = 1073\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nquad = [[-100,-100],[100,-100],[100,100],[-100,100]]\n\n'
        + flagdef +
        f'[[choice]]\nzone = [[10,-10],[50,-10],[50,-50],[10,-50]]\nprompt = "Pull?"\n'
        f'requires_flag_clear = {gate}\n'
        '[[choice.options]]\ntext = "Yes"\nset_flag = [8721, 1]\n'
        '[[choice.options]]\ntext = "No"\n', encoding="utf-8")
    proj = build.FieldProject.load(p)
    _, _, _, _, ctx, _, _, _, _gw9, _co10, _sp11, _bh12, _ni13 = build.collect_text(proj)
    return build.build_script(proj, "us", {}, choice_txids=ctx)


def test_named_flag_builds_identical_to_numeric(tmp_path):
    numeric = _build_lever(tmp_path, 8720, "numeric")
    named = _build_lever(tmp_path, "lever_pulled", "named")
    assert named == numeric                                  # name resolution is byte-transparent


def test_unknown_flag_name_errors_on_load(tmp_path):
    from ff9mapkit import build
    p = tmp_path / "z.field.toml"
    p.write_text(
        '[field]\nid = 4003\nname = "Z"\narea = 11\n\n[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nquad = [[-100,-100],[100,-100],[100,100],[-100,100]]\n\n'
        '[[npc]]\nname = "g"\npreset = "vivi"\npos = [0,-50]\ndialogue = "hi"\n'
        'requires_flag = "never_defined"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="unknown flag name"):
        build.FieldProject.load(p)


# ---- the kit_world_flags band is FULLY CONSUMED by the ferry words (Lane D, 2026-08) ------
def test_kit_world_flags_band_is_fully_consumed_by_the_ferry_words():
    """The band's old registry note said 'reserved ahead: allocate here by name' while the ferry
    departure byte + origin Int24 had already consumed all 32 bits -- an invitation to mint a new
    named world flag straight into LIVE ferry state. The words must tile the band exactly, be
    visible to named_word_at (so a raw edit warns), and the region text must say so."""
    assert flags.FERRY_DEPART_BYTE * 8 == flags.KIT_WORLD_FLAG_BASE
    assert flags.FERRY_ORIGIN_X_INT24 == flags.FERRY_DEPART_BYTE + 1
    assert (flags.FERRY_ORIGIN_X_INT24 + 2) * 8 + 7 == flags.KIT_WORLD_FLAG_BASE + 31
    assert flags.named_word_at(flags.KIT_WORLD_FLAG_BASE).name == "FerryDepartPort"
    assert flags.named_word_at(flags.KIT_WORLD_FLAG_BASE + 31).name == "FerryOriginXInt24"
    region = flags.bit_region(flags.KIT_WORLD_FLAG_BASE)
    assert region.name == "kit_world_flags" and region.reserved
    assert "FULLY CONSUMED" in region.meaning


def test_read_word_int24():
    # the ferry-origin word is a signed little-endian Int24 (x256 fixed-point world X)
    blob = bytearray(2048)
    blob[1873:1876] = (-70000).to_bytes(3, "little", signed=True)
    w = next(w for w in flags.NAMED_WORDS if w.name == "FerryOriginXInt24")
    assert flags._read_word(bytes(blob), w.byte, w.width, w.signed) == -70000
