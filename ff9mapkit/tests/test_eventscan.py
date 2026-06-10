"""Read side of the .eb: extracting gateways / music / encounters / movement from a real field.

Two oracles:
  * a REAL field -- Alexandria/Main Street (field 100, ``alex100-us.eb.bytes``) has three real exits
    (101/107/114) plus the door we injected in Session 12 (-> 4000), field BGM song 9, head-on
    movement, and no encounters. The scanner must recover all of that.
  * ROUND-TRIP against the kit's own injectors -- inject a gateway / encounter into the blank field,
    scan it back, and the values must match (the scanner is the exact inverse of the injectors).
"""

from __future__ import annotations

from pathlib import Path

from ff9mapkit import data, eventscan
from ff9mapkit.content import encounter as _enc
from ff9mapkit.content import gateway as _gw

FIX = Path(__file__).parent / "fixtures"
ALEX100 = (FIX / "alex100-us.eb.bytes").read_bytes()
CLEAN = data.blank_field_bytes("us")


# --- real field (field 100) ---------------------------------------------------------------
def test_scan_gateways_real_field():
    gws = eventscan.scan_gateways(ALEX100)
    by_to = {g["to"]: g for g in gws}
    assert {101, 107, 114, 4000} <= set(by_to)            # 3 real exits + our injected door
    assert by_to[101]["entrance"] == 200                  # the real arrival entrance
    for g in gws:
        assert len(g["zone"]) in (3, 4)                   # normalised to quad corners
        assert all(len(p) == 2 for p in g["zone"])


def test_scan_injected_door_roundtrips_through_real_field():
    # the Session-12 Alexandria door we injected into field 100 -> our custom field 4000
    door = next(g for g in eventscan.scan_gateways(ALEX100) if g["to"] == 4000)
    assert door["entrance"] == 0
    assert door["zone"] == [[-700, 2200], [200, 2200], [200, 3400], [-700, 3400]]


def test_scan_music_real_field():
    assert eventscan.scan_music(ALEX100) == 9             # Vivi's Theme (Disc 1)


def test_scan_control_direction_real_field():
    assert eventscan.scan_control_direction(ALEX100) == 0  # head-on town camera


def test_scan_encounter_none_in_town():
    assert eventscan.scan_encounter(ALEX100) is None       # towns have no random battles


# --- GLOB flag scanners (P5) --------------------------------------------------------------
def test_glob_var_token():
    assert eventscan._glob_var_token(bytes([0xC4, 191]), 0) == (191, 2)          # short GLOB bool
    assert eventscan._glob_var_token(bytes([0xE4, 0x71, 0x20]), 0) == (8305, 3)  # long GLOB bool (LE)
    assert eventscan._glob_var_token(bytes([0xC5, 5]), 0) is None                # MAP bool = transient
    assert eventscan._glob_var_token(bytes([0xE5, 0, 1]), 0) is None             # MAP long = transient
    assert eventscan._glob_var_token(bytes([0x7D, 0, 0]), 0) is None             # not a var token


def test_flag_gate_scanners_roundtrip():
    Z = [[-700, 2200], [200, 2200], [200, 3400], [-700, 3400], [-700, 3400]]   # quad + doubled last vertex
    eb = _gw.inject_gateway(CLEAN, 4000, entrance=0, zone=Z, gate_flag=8305, gate_require_set=True)
    assert eventscan.scan_edge_flag_gates(eb) == [(8305, True)]      # the exact region.flag_gate prologue
    assert (8305, True) in eventscan.scan_required_flags(eb)         # general read form catches it too
    # a gate READS its flag, never WRITES it (the template's own housekeeping writes 184/191 stay separate)
    assert 8305 not in {idx for idx, _op in eventscan.scan_flags_set(eb)}

    eb2 = _gw.inject_gateway(CLEAN, 4000, entrance=0, zone=Z, gate_flag=8305, gate_require_set=False)
    assert eventscan.scan_edge_flag_gates(eb2) == [(8305, False)]    # polarity flips with require_set


def test_scan_content_aggregate():
    c = eventscan.scan_content(ALEX100)
    assert c["music"] == 9 and c["control_direction"] == 0 and c["encounter"] is None
    assert len(c["gateways"]) >= 4


# --- round-trips against the kit's own injectors ------------------------------------------
def test_gateway_roundtrip():
    zone = _gw.quad_zone([(-200, 200), (200, 200), (200, 400), (-200, 400)])
    eb = _gw.inject_gateway(CLEAN, 1234, entrance=42, zone=zone)
    gws = eventscan.scan_gateways(eb)
    assert len(gws) == 1
    g = gws[0]
    assert g["to"] == 1234 and g["entrance"] == 42
    assert g["zone"] == [[-200, 200], [200, 200], [200, 400], [-200, 400]]   # doubled vertex dropped


def test_encounter_roundtrip():
    eb = _enc.inject_encounter(CLEAN, scene=67, freq=200)
    enc = eventscan.scan_encounter(eb)
    assert enc is not None
    assert enc["scenes"] == [67, 67, 67, 67]
    assert enc["freq"] == 200


def test_encounter_distinct_scenes_roundtrip():
    eb = _enc.inject_encounter(CLEAN, scene=67, scenes=(10, 11, 12, 13), freq=128)
    enc = eventscan.scan_encounter(eb)
    assert enc["scenes"] == [10, 11, 12, 13] and enc["freq"] == 128


# --- import emission (the field.toml blocks ff9mapkit import writes) ----------------------
def test_imported_content_toml_is_valid_and_complete():
    import tomllib
    from ff9mapkit import extract
    blocks, cd, summary = extract._imported_content_toml(ALEX100)
    assert cd == 0
    assert summary == {"gateways": 4, "encounter": False, "music": 9, "control_direction": 0,
                       "ladders": 0, "jumps": 0,              # field 100 (a town) has no ladders/jumps
                       "gateways_retargeted": 0, "gateways_seamed": 0}   # no id_remap -> retarget counters 0
    # embed in a complete borrow field.toml -> it must be valid TOML with the right structures
    toml = ('[field]\nid=4003\nname="T"\narea=2\nborrow_bg="X"\n\n'
            f'[camera]\nborrow="c.bgx"\ncontrol_direction={cd}\n\n[player]\nspawn=[0,0]\n\n{blocks}')
    d = tomllib.loads(toml)
    assert {g["to"] for g in d["gateway"]} == {101, 107, 114, 4000}
    assert all(len(g["zone"]) == 4 for g in d["gateway"])
    assert d["music"]["song"] == 9


def test_content_section_falls_back_to_commented_stub_when_empty():
    from ff9mapkit import extract
    assert extract._content_section("", 5, 7).lstrip().startswith("# [[gateway]]")
    assert extract._content_section("[[gateway]]\nto = 9", 0, 0).startswith("[[gateway]]")


def test_fieldtable_maps_known_fields_to_event_names():
    from ff9mapkit._fieldtable import FBG_TO_EVT
    assert len(FBG_TO_EVT) > 600
    assert FBG_TO_EVT["fbg_n21_grgr_map420_gr_cen_0"][1] == "EVT_GARGAN_GR_CEN_0"
    assert FBG_TO_EVT["fbg_n36_glgv_map792_gv_rm1_0"][1] == "EVT_GULUGU_GV_RM1_0"
