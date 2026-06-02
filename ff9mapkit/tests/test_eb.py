"""Phase-1 validation: the .eb library round-trips and edits exactly.

The golden-master strategy: every fixture under ``tests/fixtures/`` is an in-game-verified
``.eb`` (the blank field, the Vivi-hut exterior/interior, the Alexandria field). Parsing then
re-serializing one must reproduce it byte-for-byte; every edit primitive must match the
legacy hand-written implementation it replaces. No game required.
"""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

from ff9mapkit import data
from ff9mapkit.config import LANGS
from ff9mapkit.eb import EbScript, edit, opcodes

FIX = Path(__file__).parent / "fixtures"
ALL_FIXTURES = sorted(FIX.glob("*.eb.bytes"))


@pytest.mark.parametrize("path", ALL_FIXTURES, ids=lambda p: p.name)
def test_roundtrip_identity(path: Path):
    raw = path.read_bytes()
    assert EbScript.from_bytes(raw).to_bytes() == raw


def test_blank_field_roundtrips_all_langs():
    for lang in LANGS:
        raw = data.blank_field_bytes(lang)
        assert EbScript.from_bytes(raw).to_bytes() == raw


def test_region_template_length():
    assert len(data.region_template()) == 272


def _legacy_insert(raw: bytes, abs_off: int, ins: bytes) -> bytes:
    """The original insert_bytes (from wire_alexandria.py) — the parity oracle."""
    def u16(b, o):
        return struct.unpack_from("<H", b, o)[0]
    b = bytearray(raw)
    n = b[3]
    E = Eoff = Esz = None
    for i in range(n):
        off, sz = u16(b, 128 + i * 8), u16(b, 128 + i * 8 + 2)
        if sz > 0 and 128 + off <= abs_off < 128 + off + sz:
            E, Eoff, Esz = i, off, sz
            break
    struct.pack_into("<H", b, 128 + E * 8 + 2, Esz + len(ins))
    for j in range(n):
        if j == E:
            continue
        off = u16(b, 128 + j * 8)
        if off > Eoff:
            struct.pack_into("<H", b, 128 + j * 8, off + len(ins))
    return bytes(b[:abs_off]) + ins + bytes(b[abs_off:])


@pytest.mark.parametrize("abs_off,ins", [
    (752, bytes([0xC5, 0, 0, 0, 9, 0])),   # RunSoundCode into field 100 Main_Init
    (465, bytes([0x08, 4, 0])),            # InitRegion into an entry
    (800, b"\xAB\xCD"),                    # arbitrary
])
def test_insert_bytes_parity(abs_off, ins):
    raw = (FIX / "alex100-us.eb.bytes").read_bytes()
    assert edit.insert_bytes(raw, abs_off, ins) == _legacy_insert(raw, abs_off, ins)


def test_append_entry_registers_slot():
    raw = data.blank_field_bytes("us")
    eb = EbScript.from_bytes(raw)
    slot = eb.first_free_slot()
    body = bytes([0x02, 0x01]) + opcodes.RETURN  # trivial entry (type 2, 1 func, just return)
    # build a real func table so it parses; minimal: type, funcCount=1, (tag,fpos), code
    body = bytes([0x02, 0x01]) + struct.pack("<HH", 0, 4) + opcodes.RETURN
    out = edit.append_entry(raw, slot, body)
    eb2 = EbScript.from_bytes(out)
    assert eb2.entry(slot).size == len(body)
    assert eb2.entry(slot).abs_start == len(raw)            # appended at end of original
    assert out[len(raw):] == body                            # body is exactly at the tail
    assert eb2.to_bytes() == out                             # still round-trips


def test_find_wait_clean_base():
    eb = EbScript.from_bytes(data.blank_field_bytes("us"))
    waits = edit.find_instrs(eb, 0x22, entry_index=0, func_tag=0)
    assert [w.off for w in waits] == [458, 461]              # the two Main_Init Wait(2) fillers
    assert edit.find_wait(eb, n=2, occurrence=0) == 458


def test_encoders_known_bytes():
    assert opcodes.init_region(4, 0) == bytes([0x08, 4, 0])
    assert opcodes.init_object(2, 0) == bytes([0x09, 2, 0])
    assert opcodes.init_code(3, 0) == bytes([0x07, 3, 0])
    assert opcodes.wait(2) == bytes([0x22, 0, 2])
    assert opcodes.run_sound_code(0, 9) == bytes([0xC5, 0, 0, 0, 9, 0])
    assert opcodes.window_sync(1, 128, 500) == bytes([0x1F, 0, 1, 0x80, 0xF4, 1])
    assert opcodes.set_control_direction(-1, -1) == bytes([0x67, 0, 0xFF, 0xFF])
    assert opcodes.fade_filter(2, 16, 0, 0, 0, 0) == bytes([0xEC, 0, 2, 16, 0, 0, 0, 0])
    assert opcodes.set_model(8, 61) == bytes([0x2F, 0, 8, 0, 61])
