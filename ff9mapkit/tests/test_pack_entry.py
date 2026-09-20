"""``eb.model.pack_entry`` -- THE serializer of an entry's func table (scout F06), and the u16-fpos guard
that now lives on it (the guard only ``eb/ebsrc`` used to carry; the nine content copies raised a raw
``struct.error`` from inside ``struct.pack`` there)."""

import struct

import pytest

from ff9mapkit.content import region
from ff9mapkit.eb import EbScript, ebsrc, model, opcodes

RET = opcodes.RETURN


def _wrap(entry: bytes) -> bytes:
    """A 1-entry .eb around ``entry`` (the test_logic_add._eb layout)."""
    head = bytearray(0x80)
    head[0:2] = b"EV"
    head[3] = 1
    return bytes(head) + struct.pack("<HHBBH", 8, len(entry), 0, 0, 0) + entry


def test_pack_entry_is_the_parsers_inverse():
    funcs = [(0, RET), (3, b"\x00\x07" + RET), (10, b"")]
    packed = model.pack_entry(2, funcs)
    assert packed[:2] == bytes([2, 3])
    eb = EbScript.from_bytes(_wrap(packed))
    assert [(f.tag, eb.data[f.abs_start:f.abs_end]) for f in eb.entries[0].funcs] == funcs


def test_region_default_type_and_an_explicit_type():
    assert region.pack_entry_funcs([(0, RET)])[0] == region.REGION_ENTRY_TYPE
    assert region.pack_entry_funcs([(0, RET)], entry_type=7)[0] == 7
    assert region.pack_entry_funcs([]) == bytes([region.REGION_ENTRY_TYPE, 0])


def test_fpos_past_u16_is_a_clear_refusal():
    """REGRESSION (F06's last step): a body that pushes a later func's fpos past 0xFFFF made the nine
    content copies raise a raw struct.error; the owner refuses first, naming the tag, and that ValueError
    is what every caller (and ebsrc's EbSrcError wrap) sees. The boundary itself is legal: a func may
    start exactly at 0xFFFF."""
    with pytest.raises(ValueError, match=r"func table overflows u16 fpos at tag 3"):
        region.pack_entry_funcs([(0, b"\x00" * 70000), (3, RET)])
    ok = model.pack_entry(1, [(0, b"\x00" * (0xFFFF - 8)), (3, RET)])
    assert struct.unpack_from("<HH", ok, 6) == (3, 0xFFFF)


def test_ebsrc_assembles_through_the_owner_and_wraps_its_refusal(monkeypatch):
    eb = _wrap(model.pack_entry(0, [(0, RET)]))
    src = ebsrc.write_source(eb, enrich=False)
    assert ebsrc.assemble_source(src) == eb                    # the round trip, through pack_entry

    def boom(entry_type, funcs):
        raise ValueError("func table overflows u16 fpos at tag 0")
    monkeypatch.setattr(ebsrc, "pack_entry", boom)
    with pytest.raises(ebsrc.EbSrcError, match=r"entry 0: func table overflows u16 fpos at tag 0"):
        ebsrc.assemble_source(src)
