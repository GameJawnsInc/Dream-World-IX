"""A function ENDS at the next body in address order, and never past its entry's end.

The blank template's entry 0 parks Main_Loop (tag 1) 65 bytes PAST the entry's declared end, an out-of-range IP
the engine returns from (``test_main_init_prepend``). ``add_reinit`` then lists tag 10 after it in the TABLE but
places its body before it in the FILE. ``EbScript`` ended each function at the next-LISTED ``fpos``, unclamped, so
Main_Init ran 65 bytes past entry 0 (and over Main_Reinit, once there was one), and ``replace_function_body`` cut
to there. On a back-to-back layout that deleted the head of entry 1. On the blank, 68 orphan bytes follow entry 0,
so it declared entry 0 65 bytes short of the new Main_Init, or raised a misleading u16 error for a small one.
``insert_in_function`` / ``remove_in_function`` accepted offsets inside the parked margin, and moving ``fpos`` by
table index left Main_Loop behind when tag 10 grew.

Stock is untouched: all 296096 functions of the 9753-binary corpus are listed in address order inside their
entries, so the new bound is the old one there, and the splice outputs are byte-identical on every one.
Synthetic bytes, except the blank-template checks (``ff9mapkit extract-templates``).
"""
from __future__ import annotations

import struct

import pytest

from ff9mapkit import data
from ff9mapkit.content import reinit, savepoint
from ff9mapkit.eb import EbScript, edit, opcodes
from ff9mapkit.eb.model import pack_entry

RET = opcodes.RETURN
MARGIN = 65                                      # how far past entry 0's end the blank parks tag 1
MAIN_INIT = opcodes.wait(1) * 40 + RET
ENTRY1 = opcodes.wait(2) * 60 + RET


def _parked() -> bytes:
    """The blank's entry-0 shape on a BACK-TO-BACK layout: Main_Init, then a tag 1 whose ``fpos`` points MARGIN
    bytes past the entry's end -- which is inside entry 1, so a cut that runs to it eats entry 1's head."""
    head = bytearray(0x80)
    head[0:2] = b"EV"
    out = edit.append_entry(bytes(head), 0, pack_entry(0, [(0, MAIN_INIT), (1, b"")]))
    out = bytearray(edit.append_entry(out, 1, pack_entry(0, [(0, ENTRY1)])))
    e0 = EbScript.from_bytes(bytes(out)).entry(0)
    struct.pack_into("<H", out, e0.abs_start + 2 + 4 + 2, (e0.size - 2) + MARGIN)
    return bytes(out)


def _margin(eb: bytes, tag: int = 1) -> int:
    e0 = EbScript.from_bytes(eb).entry(0)
    return e0.func_by_tag(tag).fpos - (e0.size - 2)


def _body(eb: bytes, tag: int, entry: int = 0) -> bytes:
    f = EbScript.from_bytes(eb).entry(entry).func_by_tag(tag)
    return eb[f.abs_start:f.abs_end]


def _entry_bytes(eb: bytes, i: int) -> bytes:
    e = EbScript.from_bytes(eb).entry(i)
    return eb[e.abs_start:e.abs_end]


def test_the_fixture_parks_main_loop_inside_entry_1():
    eb = _parked()
    s = EbScript.from_bytes(eb)
    e0, e1 = s.entry(0), s.entry(1)
    assert _margin(eb) == MARGIN and e1.abs_start == e0.abs_end          # nothing between them
    assert e0.abs_end < e0.func_by_tag(1).abs_start < e1.abs_end


def test_main_init_ends_at_its_entry_end_and_the_parked_func_is_empty():
    eb = _parked()
    e0 = EbScript.from_bytes(eb).entry(0)
    f0, f1 = e0.func_by_tag(0), e0.func_by_tag(1)
    assert (f0.abs_end, f0.length) == (e0.abs_end, len(MAIN_INIT))      # was e0.abs_end + MARGIN
    assert f1.abs_start == e0.abs_end + MARGIN and f1.length == 0        # was -MARGIN
    assert eb[f0.abs_start:f0.abs_end] == MAIN_INIT
    assert max(i.end for i in EbScript.from_bytes(eb).instrs(f0)) == e0.abs_end   # disasm stays in entry 0


@pytest.mark.parametrize("new", [opcodes.wait(3) * 45 + RET, RET, MAIN_INIT],
                         ids=["longer", "one_byte", "same"])
def test_replacing_main_init_leaves_entry_1_whole(new):
    """The brief's repro: a longer Main_Init left entry 1 short of its first MARGIN bytes; a small one raised
    ``set_u16 ... 64KB entry-table reach`` (entry 0's size went negative)."""
    eb = _parked()
    out = edit.replace_function_body(eb, 0, 0, new)
    assert _body(out, 0) == new
    assert _entry_bytes(out, 1) == _entry_bytes(eb, 1)
    assert _margin(out) == MARGIN
    assert EbScript.from_bytes(out).entry(0).size == 2 + 2 * 4 + len(new)
    if new == MAIN_INIT:
        assert out == eb


def test_after_add_reinit_main_init_stops_at_main_reinit():
    eb = reinit.add_reinit(_parked())
    e0 = EbScript.from_bytes(eb).entry(0)
    assert [f.tag for f in e0.funcs] == [0, 1, 10]                        # listed out of address order
    f0, f10 = e0.func_by_tag(0), e0.func_by_tag(10)
    assert f0.abs_end == f10.abs_start and f10.abs_end == e0.abs_end
    assert _body(eb, 0) == MAIN_INIT
    reinit_body = _body(eb, 10)
    for new in (opcodes.wait(3) * 45 + RET, RET):
        out = edit.replace_function_body(eb, 0, 0, new)
        assert _body(out, 0) == new and _body(out, 10) == reinit_body
        assert _entry_bytes(out, 1) == _entry_bytes(eb, 1) and _margin(out) == MARGIN


def test_growing_main_reinit_carries_the_parked_main_loop():
    """By table index nothing follows tag 10, so its fpos-fix skipped the parked tag 1: a tag 10 grown past
    MARGIN bytes pulled Main_Loop's IP into the middle of Main_Reinit."""
    eb = reinit.add_reinit(_parked())
    new = opcodes.wait(4) * 40 + RET                                      # 121 bytes, well past the margin
    out = edit.replace_function_body(eb, 0, 10, new)
    assert _body(out, 10) == new and _body(out, 0) == MAIN_INIT
    assert _margin(out) == MARGIN
    assert _entry_bytes(out, 1) == _entry_bytes(eb, 1)


def test_insert_and_remove_refuse_the_parked_margin():
    eb = _parked()
    for rel in (len(MAIN_INIT), len(MAIN_INIT) + 1, len(MAIN_INIT) + MARGIN - 1):
        with pytest.raises(ValueError, match="outside func 0 body"):
            edit.insert_in_function(eb, 0, 0, rel, RET)
    with pytest.raises(ValueError, match=r"is outside func 0 body"):
        edit.remove_in_function(eb, 0, 0, len(MAIN_INIT) - 1, 4)
    out = edit.insert_in_function(eb, 0, 0, len(MAIN_INIT) - 1, opcodes.wait(9))   # before the RET: fine
    assert _body(out, 0) == MAIN_INIT[:-1] + opcodes.wait(9) + RET
    assert _entry_bytes(out, 1) == _entry_bytes(eb, 1) and _margin(out) == MARGIN


def test_replacing_the_parked_function_itself_is_byte_unchanged():
    """The save-point director graft (``savepoint.graft_director``) replaces the parked tag 1 itself. Its output is
    pinned to what it always was: entry 0 extends up to the parked ``fpos`` -- the bytes in between ride along as
    dead padding after Main_Init's RETURN -- and the new body follows; ``fpos`` stays, entry 1 moves whole."""
    eb = _parked()
    s = EbScript.from_bytes(eb)
    e0, e1, p = s.entry(0), s.entry(1), s.entry(0).func_by_tag(1).abs_start
    new = opcodes.wait(5) * 50 + RET
    grow = (p - e0.abs_end) + len(new)
    want = bytearray(eb[:p] + new + eb[e0.abs_end:])
    struct.pack_into("<H", want, 0x80 + 2, e0.size + grow)                  # entry 0's size
    struct.pack_into("<H", want, 0x80 + 8, e1.off + grow)                   # entry 1's offset
    out = edit.replace_function_body(eb, 0, 1, new)
    assert out == bytes(want)
    assert _body(out, 1) == new and _body(out, 0) == MAIN_INIT + eb[e0.abs_end:p]
    assert _entry_bytes(out, 1) == _entry_bytes(eb, 1)


# ---- the real blank template (needs `ff9mapkit extract-templates`) ---------------------------------------
@pytest.mark.parametrize("with_reinit", [False, True], ids=["blank", "blank+reinit"])
def test_blank_main_init_replace_stays_inside_entry_0(with_reinit):
    """On the blank the cut ran into the 68 orphan bytes after entry 0 rather than into entry 1, so the damage
    was the entry-0 SIZE: 65 bytes short of the new Main_Init, whose tail the engine then never loaded."""
    blank = data.blank_field_bytes("us")
    eb = reinit.add_reinit(blank) if with_reinit else blank
    assert _margin(eb) == MARGIN
    new = opcodes.wait(3) * 150 + RET
    out = edit.replace_function_body(eb, 0, 0, new)
    s = EbScript.from_bytes(out)
    f0 = s.entry(0).func_by_tag(0)
    assert _body(out, 0) == new and f0.abs_start + len(new) <= s.entry(0).abs_end
    assert _entry_bytes(out, 1) == _entry_bytes(eb, 1) and _margin(out) == MARGIN
    if with_reinit:
        assert _body(out, 10) == _body(eb, 10)


def test_blank_director_graft_is_byte_unchanged():
    blank = data.blank_field_bytes("us")
    s = EbScript.from_bytes(blank)
    e0, p = s.entry(0), s.entry(0).func_by_tag(1).abs_start
    director = opcodes.wait(6) * 20 + RET
    grow = (p - e0.abs_end) + len(director)                                 # the orphan bytes, then the body
    want = bytearray(blank[:p] + director + blank[e0.abs_end:])
    struct.pack_into("<H", want, 0x80 + 2, e0.size + grow)
    for e in s.entries[1:]:
        if not e.empty and e.off > e0.off:
            struct.pack_into("<H", want, 0x80 + e.index * 8, e.off + grow)
    out = savepoint.graft_director(blank, director)
    assert out == bytes(want)
    assert _body(out, 1) == director and _margin(out) == -len(director)    # tag 1 now the entry's last body
    for i in range(1, s.entry_count):
        assert _entry_bytes(out, i) == _entry_bytes(blank, i)
