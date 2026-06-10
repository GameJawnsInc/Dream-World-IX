"""Tests for the story-flag registry + save inspector (ff9mapkit.flags) and the build-time name resolver."""
import base64
import struct

import pytest

from ff9mapkit import flags


# ---- registry ---------------------------------------------------------------------------
def test_safe_band_constants():
    assert flags.FIRST_SAFE_FLAG == 8512                       # first bit clear of ALL real-FF9 usage
    assert (flags.CHEST_FLAG_LO, flags.CHEST_FLAG_HI) == (8376, 8511)
    assert flags.CHOICE_SCRATCH_FLOOR == 16320


def test_bit_addressing_and_regions():
    assert flags.bit_to_byte(8376) == (1047, 0)               # chest band start
    assert flags.bit_region(8400).name == "chest_opened" and flags.bit_region(8400).reserved
    assert flags.bit_region(8512) is None                     # safe custom space is unmapped
    assert flags.is_reserved(8400) and not flags.is_reserved(8512)
    assert flags.is_safe_custom(8512) and not flags.is_safe_custom(8400)
    assert not flags.is_safe_custom(16320)                    # choice scratch floor is out of band


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


# ---- author-side name resolution --------------------------------------------------------
def test_collect_flag_defs_valid():
    nm = flags.collect_flag_defs({"flag": [{"name": "Switch Pulled", "index": 8520}]})
    assert nm == {"switchpulled": 8520}                       # normalized key (alnum/underscore, lowercased)


def test_collect_flag_defs_rejects_bad_defs():
    with pytest.raises(ValueError, match="needs both"):
        flags.collect_flag_defs({"flag": [{"name": "x"}]})    # missing index
    with pytest.raises(ValueError, match="treasure-chest"):
        flags.collect_flag_defs({"flag": [{"name": "x", "index": 8400}]})   # in the chest band
    with pytest.raises(ValueError, match="outside the safe"):
        flags.collect_flag_defs({"flag": [{"name": "x", "index": 8000}]})   # below the safe floor
    with pytest.raises(ValueError, match="duplicate"):
        flags.collect_flag_defs({"flag": [{"name": "x", "index": 8520}, {"name": "X", "index": 8521}]})


def test_resolve_passthrough_and_names():
    nm = {"lever": 8530}
    assert flags.resolve(8530, nm) == 8530                    # int passes through
    assert flags.resolve("8530", nm) == 8530                  # digit-string passes through
    assert flags.resolve("lever", nm) == 8530                 # name resolves
    with pytest.raises(ValueError, match="unknown flag name"):
        flags.resolve("levr", nm)                             # typo -> error (with a hint)


def test_resolve_project_flags_rewrites_and_is_noop_when_numeric():
    raw = {
        "flag": [{"name": "door_open", "index": 8520}],
        "event": [{"name": "e", "set_flag": ["door_open", 1]}],
        "npc": [{"name": "g", "requires_flag": "door_open"}],
        "gateway": [{"to": 4000, "requires_flag_clear": 8521}],     # numeric stays numeric
        "choice": [{"options": [{"text": "y", "requires_flag": "door_open"}]}],
    }
    flags.resolve_project_flags(raw)
    assert raw["event"][0]["set_flag"] == [8520, 1]
    assert raw["npc"][0]["requires_flag"] == 8520
    assert raw["gateway"][0]["requires_flag_clear"] == 8521
    assert raw["choice"][0]["options"][0]["requires_flag"] == 8520

    numeric = {"npc": [{"name": "g", "requires_flag": 8520}]}       # no names -> unchanged
    before = repr(numeric)
    flags.resolve_project_flags(numeric)
    assert repr(numeric) == before


def test_resolve_project_flags_campaign_names():
    raw = {"npc": [{"name": "g", "requires_flag": "shared"}]}       # name from the campaign, not local
    flags.resolve_project_flags(raw, {"shared": 8600})
    assert raw["npc"][0]["requires_flag"] == 8600


# ---- save inspector ---------------------------------------------------------------------
def _synthetic_blob():
    b = bytearray(2048)
    b[0:2] = struct.pack("<H", 9860)        # ScenarioCounter in the Eiko-abducted window
    b[2:4] = struct.pack("<h", 5)           # FieldEntrance
    b[1047] = 0xFF                          # 8 chest bits (8376-8383)
    b[896] = 0x07                           # 3 treasure-hunter points (standard region, 1pt/bit)
    b[182] = 0x03                           # 2 double-region bits -> 4 points
    b[8520 >> 3] |= 1 << (8520 & 7)         # a custom story flag in the safe band
    return bytes(b)


def test_decode_gEventGlobal():
    rep = flags.decode_gEventGlobal(_synthetic_blob())
    assert rep.scenario_counter == 9860 and rep.eiko_abducted
    assert rep.milestone == (9800, "Desert Palace")           # nearest area anchor <= 9860
    assert rep.field_entrance == 5
    assert rep.chests_opened == 8
    assert rep.treasure_hunter_points == 3 + 4                # 3 (1pt) + 2 bits *2pt
    assert (flags.NAMED_WORDS[0], 9860) in rep.named_words    # ScenarioCounter named


def test_decode_tolerates_short_blob():
    rep = flags.decode_gEventGlobal(b"\x10\x00")             # 2 bytes -> ScenarioCounter 16, rest zero
    assert rep.scenario_counter == 16 and rep.chests_opened == 0


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
    assert "Chests opened   : 8" in out and "chest_opened" in out


# ---- build integration: named flags produce IDENTICAL bytes to numeric ------------------
def _build_lever(tmp_path, gate_value, tag):
    """A one-shot lever field whose choice is gated by `gate_value` (an int OR a registered name)."""
    from ff9mapkit import build
    flagdef = ('[[flag]]\nname = "lever_pulled"\nindex = 8520\n\n'
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
        '[[choice.options]]\ntext = "Yes"\nset_flag = [8521, 1]\n'
        '[[choice.options]]\ntext = "No"\n', encoding="utf-8")
    proj = build.FieldProject.load(p)
    _, _, _, _, ctx = build.collect_text(proj)
    return build.build_script(proj, "us", {}, choice_txids=ctx)


def test_named_flag_builds_identical_to_numeric(tmp_path):
    numeric = _build_lever(tmp_path, 8520, "numeric")
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
