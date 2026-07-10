"""Chocobo Hot & Cold -- the [chocobo] dig prize-pool / timer lane (content/chocobo.py).

Synthetic tests prove the scan (pool discovery, sentinel exclusion, nth on duplicate slots, tier
annotation, timer-seed pick), the export->resolve round-trip (an unedited export emits ZERO edits =
byte-identical), the authoring keys (item/gil/nothing/value + timer), and every refusal. The
install-gated tests pin the REAL forests: 35 slots + timer 60 on 2950/2951/2952, 2950's proven
coordinates (entry 8 tag 41, slots [15642..16401], timer @4312), and a real slot patch that lands on
exactly the payload bytes and lints clean. -> project memory: project-ff9-chocobo-hot-cold.
"""
from __future__ import annotations

import struct
import tomllib

import pytest

from ff9mapkit import eblint
from ff9mapkit import logic_edit as LE
from ff9mapkit.content import chocobo as CH


def _eb(body: bytes) -> bytes:
    """A valid 1-entry / 1-func (tag 0) .eb wrapping ``body`` as Main_Init's bytecode."""
    head = bytearray(0x80)
    head[0:2] = b"EV"
    head[3] = 1
    funcbody = bytes([0, 1]) + struct.pack("<HH", 0, 4) + body
    slot = struct.pack("<HHBBH", 8, len(funcbody), 0, 0, 0)
    return bytes(head) + slot + funcbody


def _assign(var_tok: int, var_idx: int, value: int) -> bytes:
    """``{opVAR(idx) op7D(value) op2C op7F}`` -- the pure-literal-assign shape (slot / tier marker)."""
    return bytes([0x05, var_tok, var_idx, 0x7D, value & 0xFF, value >> 8, 0x2C, 0x7F])


def _slot(value: int) -> bytes:
    return _assign(0xDE, 20, value)


TIMER = bytes([0x69, 0x01, 0x7D, 60, 0, 0xD1, 36, 0x12, 0x7D, 1, 0, 0x14, 0x7F])  # {60*difficulty+1}
RET = bytes([0x04])

# 9 slots (values incl. gil / a 0 / three identical 30001 "nothing"s) + a 30000 sentinel init +
# interleaved tier markers (opD5(53) = 5,3,1 -- strictly descending) + the timer seed.
_POOL_VALUES = (236, 218, 30001, 30001, 1500, 87, 0, 30001, 239)
_BODY = (_slot(CH.SPECIAL)                       # sentinel init -- must NOT become a slot
         + _assign(0xD5, 53, 5) + _slot(236) + _slot(218) + _slot(30001)
         + _assign(0xD5, 53, 3) + _slot(30001) + _slot(1500) + _slot(87)
         + _assign(0xD5, 53, 1) + _slot(0) + _slot(30001) + _slot(239)
         + TIMER + RET)
SRC = _eb(_BODY)


# ------------------------------------------------------------------- scan --
def test_scan_finds_pool_and_timer():
    sc = CH.scan(SRC)
    assert sc is not None and sc.pool_var == "opDE(20)" and (sc.pool_entry, sc.pool_tag) == (0, 0)
    assert tuple(s.value for s in sc.slots) == _POOL_VALUES          # sentinel init excluded, byte order
    assert sc.timer is not None and sc.timer.value == 60
    assert [s.tier for s in sc.slots] == [5, 5, 5, 3, 3, 3, 1, 1, 1]


def test_scan_nth_disambiguates_identical_slots():
    sc = CH.scan(SRC)
    nothings = [s for s in sc.slots if s.value == CH.NOTHING]
    assert [s.nth for s in nothings] == [0, 1, 2]                    # identical expr -> ordered nth
    uniques = [s for s in sc.slots if s.value == 236]
    assert uniques[0].nth is None                                    # unique -> no nth needed


def test_scan_none_on_a_plain_field():
    assert CH.scan(_eb(bytes([0x05, 0xDE, 20, 0x7D, 1, 0, 0x2C, 0x7F]) + RET)) is None


# --------------------------------------------------------- export / resolve --
def test_fresh_export_resolves_to_zero_edits():
    sc = CH.scan(SRC)
    cfg = tomllib.loads(CH.export_toml(sc))["chocobo"]
    assert CH.resolve_edits(SRC, cfg) == []


def test_resolve_and_apply_each_key_kind():
    cfg = {"tuning": {"timer": 120},
           "prize": [{"slot": 0, "item": "Elixir"},                  # 236 -> 239 by name
                     {"slot": 4, "gil": 777},                        # 1500 -> 1777
                     {"slot": 1, "nothing": True},                   # 218 -> 30001
                     {"slot": 6, "value": 30001}]}                   # raw escape hatch
    edits = CH.resolve_edits(SRC, cfg)
    assert len(edits) == 4 + 1 and all(e["kind"] == "expr_literal" for e in edits)
    out = LE.apply_logic_edits(SRC, edits)
    assert len(out) == len(SRC) and eblint.errors(eblint.lint_eb(out)) == []
    sc2 = CH.scan(out)
    assert tuple(s.value for s in sc2.slots) == (239, 30001, 30001, 30001, 1777, 87, 30001, 30001, 239)
    assert sc2.timer.value == 120


def test_unchanged_values_emit_no_edit():
    assert CH.resolve_edits(SRC, {"prize": [{"slot": 0, "value": 236}], "tuning": {"timer": 60}}) == []


def test_editing_one_of_identical_slots_targets_it_alone():
    sc = CH.scan(SRC)
    middle = [s for s in sc.slots if s.value == CH.NOTHING][1]       # nth=1 of the three 30001s
    out = LE.apply_logic_edits(SRC, CH.resolve_edits(SRC, {"prize": [{"slot": middle.index, "gil": 50}]}))
    vals = tuple(s.value for s in CH.scan(out).slots)
    assert vals == (236, 218, 30001, 1050, 1500, 87, 0, 30001, 239)


# --------------------------------------------------------------- refusals --
@pytest.mark.parametrize("cfg, msg", [
    ({"bogus": 1}, "unknown key"),
    ({"prize": {"slot": 0}}, "array of tables"),
    ({"tuning": {"bogus": 1}}, "unknown key"),
    ({"prize": [{"slot": 0}]}, "exactly ONE"),
    ({"prize": [{"slot": 0, "item": "Potion", "gil": 5}]}, "exactly ONE"),
    ({"prize": [{"slot": 0, "elixir": True}]}, "unknown key"),
    ({"prize": [{"slot": 99, "gil": 5}]}, "slot must be"),
    ({"prize": [{"slot": True, "gil": 5}]}, "slot must be"),
    ({"prize": [{"slot": 0, "gil": 5}, {"slot": 0, "gil": 6}]}, "authored twice"),
    ({"prize": [{"slot": 0, "gil": 0}]}, "gil must be"),
    ({"prize": [{"slot": 0, "gil": CH.GIL_MAX + 1}]}, "gil must be"),
    ({"prize": [{"slot": 0, "nothing": False}]}, "nothing = true"),
    ({"prize": [{"slot": 0, "value": -1}]}, "value must be"),
    ({"prize": [{"slot": 0, "item": "NotARealItemName"}]}, "unknown item"),
    ({"tuning": {"timer": 0}}, "timer must be"),
    ({"tuning": {"timer": True}}, "timer must be"),
])
def test_resolve_refusals(cfg, msg):
    with pytest.raises(CH.ChocoboError, match=msg):
        CH.resolve_edits(SRC, cfg)


def test_resolve_refuses_on_a_poolless_field():
    plain = _eb(RET)
    with pytest.raises(CH.ChocoboError, match="no dig-prize pool"):
        CH.resolve_edits(plain, {"prize": [{"slot": 0, "gil": 5}]})
    assert CH.resolve_edits(plain, {}) == []                         # empty block: nothing to do, no scan


# ------------------------------------------------------------ real forests --
def _real_eb(fid: int):
    try:
        from ff9mapkit.extract import EventBundle
        return EventBundle().eb_for_id(fid)
    except Exception:                                                # noqa: BLE001
        pytest.skip("no game install")


@pytest.mark.parametrize("fid, coords", [(2950, (8, 41)), (2951, (12, 38)), (2952, (8, 46))])
def test_real_forest_pools(fid, coords):
    """All three Hot & Cold forests: 35 slots on the opDE(20) pool + the 60s timer seed."""
    sc = CH.scan(_real_eb(fid))
    assert sc is not None and (sc.pool_entry, sc.pool_tag) == coords and sc.pool_var == "opDE(20)"
    assert len(sc.slots) == 35 and sc.timer is not None and sc.timer.value == 60
    assert {s.tier for s in sc.slots} == {1, 2, 3, 4, 5}


def test_real_2950_proven_offsets_and_patch():
    """2950's spike-proven coordinates hold; a slot->Elixir patch lands on exactly the payload byte(s),
    stays lint-clean, and a fresh export still resolves to zero edits (byte-identical discipline)."""
    data = _real_eb(2950)
    sc = CH.scan(data)
    assert sc.slots[0].off == 15642 and sc.slots[-1].off == 16401 and sc.timer.off == 4312
    cfg = tomllib.loads(CH.export_toml(sc))["chocobo"]
    assert CH.resolve_edits(data, cfg) == []
    edits = CH.resolve_edits(data, {"prize": [{"slot": 0, "item": "Elixir"}]})
    out = LE.apply_logic_edits(data, edits)
    diffs = [i for i, (a, b) in enumerate(zip(data, out)) if a != b]
    assert set(diffs) <= {sc.slots[0].payload_off, sc.slots[0].payload_off + 1}
    assert eblint.errors(eblint.lint_eb(out)) == []
    assert CH.scan(out).slots[0].value == 239
