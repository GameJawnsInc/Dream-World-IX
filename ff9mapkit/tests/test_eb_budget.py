"""The `.eb` u16 budget must fail LOUDLY, never wrap silently.

The defect class: a binary writer that MASKS a caller-supplied value (``& 0xFFFF``) instead of
validating it. For an entry-table offset that produces a file whose entries point at garbage
function tags, with no error at the write site -- the black-screen-at-playtest class. ``set_u16``
was hardened first; ``pu16`` carried the same bug one function over.

These tests are deliberately game-data free (a synthetic entry table, not a real field) so the
budget contract stays covered on a fresh public clone.
"""

from __future__ import annotations

import pytest

from ff9mapkit.binutils import (EB_ENTRY_SIZE_MAX, EB_FILE_BUDGET, eb_budget_used, pu8, pu16, pu32,
                                set_u16)
from ff9mapkit.eb import edit, opcodes
from ff9mapkit.eb.model import ENTRY_SLOT_SIZE, ENTRY_TABLE_OFF


def _stub_eb(entry_count: int = 2, body: bytes = b"") -> bytes:
    """A minimal buffer with a readable header + empty entry table, then ``body``.

    ``append_entry`` only reads the entry count (header byte 3) and the slot records, so this is
    enough to exercise the budget checks without any FF9-derived bytes."""
    b = bytearray(ENTRY_TABLE_OFF + entry_count * ENTRY_SLOT_SIZE)
    b[0:2] = b"EV"
    b[3] = entry_count
    return bytes(b) + body


# --------------------------------------------------------------------------- the packers

@pytest.mark.parametrize("v", [0x10000, 0x1FFFF, 70_000, -1])
def test_pu16_rejects_out_of_range(v):
    with pytest.raises(ValueError, match="pu16"):
        pu16(v)


@pytest.mark.parametrize("v", [0, 1, 0x1234, EB_FILE_BUDGET])
def test_pu16_still_packs_every_in_range_value(v):
    assert pu16(v) == v.to_bytes(2, "little")


@pytest.mark.parametrize("v", [0x10000, -1, 70_000])
def test_set_u16_still_rejects_out_of_range(v):
    with pytest.raises(ValueError, match="set_u16"):
        set_u16(bytearray(4), 0, v)


def test_pu32_rejects_out_of_range():
    assert pu32(0xFFFFFFFF) == b"\xff\xff\xff\xff"
    with pytest.raises(ValueError, match="pu32"):
        pu32(0x1_0000_0000)


def test_pu8_rejects_out_of_range():
    assert pu8(0xFF) == b"\xff"
    with pytest.raises(ValueError, match="pu8"):
        pu8(256)


# --------------------------------------------------------------------------- instruction immediates

def test_encode_rejects_an_immediate_that_does_not_fit():
    """``opcodes._imm`` masked too -- a model id of 70000 encoded as a DIFFERENT, valid model."""
    with pytest.raises(ValueError, match="does not fit"):
        opcodes.encode(0x2F, 70_000, 0)                       # SetModel(model, animset)


def test_encode_still_writes_negatives_as_twos_complement():
    """The mask is INTENTIONAL for an in-window negative -- that must not have changed."""
    assert opcodes.encode(0x2F, -1, 0)[-3:] == b"\xff\xff\x00"


# --------------------------------------------------------------------------- the budget

def test_eb_budget_used_is_the_table_relative_offset():
    """NOT raw ``len(eb)`` -- the budget is measured from the entry table."""
    eb = _stub_eb(body=b"\x00" * 1000)
    assert eb_budget_used(eb) == len(eb) - ENTRY_TABLE_OFF


def test_eb_budget_used_agrees_with_what_append_entry_enforces():
    """The meter and the write-site check must never be able to disagree (§3.1)."""
    entry = b"\x02\x01\x00\x00\x04\x00\x04"
    at_wall = _stub_eb(body=b"\x00" * (EB_FILE_BUDGET - ENTRY_SLOT_SIZE * 2))
    assert eb_budget_used(at_wall) == EB_FILE_BUDGET
    edit.append_entry(at_wall, 1, entry)                     # exactly at the wall -> still legal

    over = at_wall + b"\x00"
    assert eb_budget_used(over) == EB_FILE_BUDGET + 1
    with pytest.raises(ValueError) as e:
        edit.append_entry(over, 1, entry)
    assert str(eb_budget_used(over)) in str(e.value)         # the message names the measured number


def test_append_entry_rejects_an_over_budget_offset():
    eb = _stub_eb(body=b"\x00" * 70_000)
    with pytest.raises(ValueError, match="file is too large"):
        edit.append_entry(eb, 1, b"\x02\x01\x00\x00\x04\x00\x04")


def test_append_entry_rejects_an_over_size_entry():
    """A DIFFERENT limit from the file budget: the slot record's own size field."""
    eb = _stub_eb()
    with pytest.raises(ValueError, match="entry size"):
        edit.append_entry(eb, 1, b"\x00" * (EB_ENTRY_SIZE_MAX + 1))
