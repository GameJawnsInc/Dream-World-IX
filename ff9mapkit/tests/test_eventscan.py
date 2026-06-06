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
