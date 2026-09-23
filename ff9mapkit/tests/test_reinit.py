"""Pins ``content/reinit.py::add_reinit`` -- the after-battle entry-0 tag-10 handler splice a field
cloned from a cutscene template needs (else ``ExitBattleEnd`` never un-suspends the player).

Synthetic multi-entry ``.eb`` fixtures (hand-built, mirroring ``EbScript``'s real layout -- see
``test_logic_add._eb``) pin, byte-for-byte and without touching the game install:
  * the new tag-10 body's exact bytes (fade-in + the RESTORE-NOT-GRANT gated EnableMove + return,
    prologue-first, fade-optional) -- the grant runs only when the engine-restored pre-battle
    ``usercontrol`` says control was ON and the stay-locked latch (MAP 156) is clear;
  * entry-0's PRE-EXISTING functions keep their tag, shift fpos by exactly +4, and keep their body bytes;
  * a tag-10 collision raises ``ValueError``;
  * every LATER entry's table offset shifts by exactly ``growth`` (and its body bytes ride along
    unchanged) -- except an EMPTY slot (size 0), which the relocation loop skips outright;
  * entryCount is left untouched, and the composed file stays eblint-clean + round-trips.
"""
from __future__ import annotations

import struct

import pytest

from ff9mapkit import eblint
from ff9mapkit.content import reinit as R
from ff9mapkit.eb import EbScript, opcodes

RET = opcodes.RETURN                    # 0x04, 0 args
EM = opcodes.ENABLE_MOVE                # 0x2E, 0 args
DM = opcodes.DISABLE_MOVE               # 0x2D, 0 args
EM_RET = EM + RET
FADE_IN = opcodes.fade_filter(2, 16, 0, 0, 0, 0)
# `if (IsMovementEnabled && !MAP156) { EnableMove }` -- the restore-not-grant tail (GRANT_GATE +
# JMP_FALSE over the 1-byte EnableMove). Pinned byte-for-byte: 05 7A 02 C5 9C 0E 27 7F 02 01 00 2E.
GATED_EM = R.GRANT_GATE + bytes([0x02, 0x01, 0x00]) + EM
assert GATED_EM == bytes([0x05, 0x7A, 0x02, 0xC5, 0x9C, 0x0E, 0x27, 0x7F, 0x02, 0x01, 0x00, 0x2E])


def _eb_multi(*entries) -> bytes:
    """A valid multi-entry ``.eb``. Each of ``entries`` is either ``None`` (an empty entry-table slot,
    size 0) or a list of ``(tag, body)`` functions for that entry -- same per-entry layout as
    ``test_logic_add._eb`` (fpos relative to fbase=entryStart+2, bodies follow the fc-slot func table).
    Slot offsets are relative to 128; entry bodies are packed back-to-back straight after the
    entryCount*8-byte slot table, in entry order -- this is exactly the layout ``add_reinit`` (and
    ``EbScript``) assume, so a round-trip through ``EbScript.from_bytes`` is asserted by every test that
    depends on it."""
    n = len(entries)
    bodies = []
    for funcs in entries:
        if funcs is None:
            bodies.append(b"")
            continue
        fc = len(funcs)
        table, code, fpos = b"", b"", fc * 4
        for tag, body in funcs:
            table += struct.pack("<HH", tag, fpos)
            code += body
            fpos += len(body)
        bodies.append(bytes([0, fc]) + table + code)
    head = bytearray(0x80)
    head[0:2] = b"EV"
    head[3] = n
    slots = bytearray()
    off = n * 8
    for body in bodies:
        slots += struct.pack("<HHBBH", off, len(body), 0, 0, 0)
        off += len(body)
    return bytes(head) + bytes(slots) + b"".join(bodies)


def _clean(out: bytes) -> bool:
    return eblint.errors(eblint.lint_eb(out)) == [] and EbScript.from_bytes(out).to_bytes() == out


# A 4-entry synthetic fixture used by the "normal add" + "relocation" cases:
#   entry0: tag0 (RET) + tag3 (EnableMove;RET)   -- the pre-existing functions to preserve
#   entry1: tag0 (RET)                            -- a later, non-empty entry to relocate
#   entry2: EMPTY (size 0)                        -- must NOT be relocated
#   entry3: tag0 (EnableMove;RET)                 -- a second later, non-empty entry to relocate
def _multi_fixture() -> bytes:
    return _eb_multi([(0, RET), (3, EM_RET)], [(0, RET)], None, [(0, EM_RET)])


def test_multi_fixture_round_trips():
    """Sanity: the hand-built multi-entry fixture parses byte-identically before we rely on it."""
    eb = _multi_fixture()
    s = EbScript.from_bytes(eb)
    assert eblint.errors(eblint.lint_eb(eb)) == []                    # (to_bytes() IS .data -- no round trip to assert)
    assert s.entry_count == 4
    assert not s.entry(0).empty and not s.entry(1).empty and s.entry(2).empty and not s.entry(3).empty


def test_add_reinit_normal_multi_entry():
    """The core contract on a multi-entry synthetic .eb: parses, tag-10 exists with the exact expected
    body, entry-0's PRE-EXISTING functions keep tag/body and shift fpos by +4, entryCount unchanged."""
    eb = _multi_fixture()
    orig = EbScript.from_bytes(eb)

    out = R.add_reinit(eb)
    new = EbScript.from_bytes(out)                     # must parse cleanly

    f10 = new.entry(0).func_by_tag(10)
    assert f10 is not None
    assert out[f10.abs_start:f10.abs_end] == FADE_IN + GATED_EM + RET

    new_by_tag = {f.tag: f for f in new.entry(0).funcs}
    for f in orig.entry(0).funcs:                       # every pre-existing entry-0 function...
        nf = new_by_tag[f.tag]
        assert nf.fpos == f.fpos + 4                    # ...fpos shifted by exactly +4...
        assert out[nf.abs_start:nf.abs_end] == eb[f.abs_start:f.abs_end]   # ...body byte-identical

    assert out[3] == eb[3] == 4                          # entryCount untouched
    assert _clean(out)


def test_add_reinit_tag_collision_raises():
    eb = _eb_multi([(10, RET)])
    with pytest.raises(ValueError, match=r"entry 0 already has a function with tag 10"):
        R.add_reinit(eb)


def test_add_reinit_no_fade():
    """with_fade=False -> the tag-10 body is EXACTLY the gated EnableMove;RET, no FadeFilter at all."""
    eb = _eb_multi([(0, RET)])
    out = R.add_reinit(eb, with_fade=False)
    f10 = EbScript.from_bytes(out).entry(0).func_by_tag(10)
    assert out[f10.abs_start:f10.abs_end] == GATED_EM + RET
    assert _clean(out)


def test_add_reinit_prologue_runs_first():
    """prologue= bytes are prepended before the fade-in/EnableMove/return, verbatim."""
    eb = _eb_multi([(0, RET)])
    out = R.add_reinit(eb, prologue=DM)                  # DisableMove as a stand-in prologue op
    f10 = EbScript.from_bytes(out).entry(0).func_by_tag(10)
    body = out[f10.abs_start:f10.abs_end]
    assert body.startswith(DM)
    assert body == DM + FADE_IN + GATED_EM + RET
    assert _clean(out)


def _eb_reordered() -> bytes:
    """3-entry ``.eb`` where the entry TABLE order (0, 1, 2) does not match the entries' PHYSICAL byte
    order: entry 1's body is placed first in the file, then entry 0's, then entry 2's. This makes
    entry 1's stored offset SMALLER than entry 0's (``off0``) despite entry 1 being a later table
    slot -- unlike every ``_eb_multi``-built fixture (there, bodies are always packed in table order,
    so ``off0`` is trivially the smallest offset and ``off > off0`` is never independently exercised).
    Entry 2 keeps a physically-later, ``off > off0`` body for contrast within the same fixture."""
    def body(tag):
        return bytes([0, 1]) + struct.pack("<HH", tag, 4) + RET   # fc=1, one tag-`tag` RET function

    b1, b0, b2 = body(0), body(0), body(0)
    table_size = 3 * 8
    off1 = table_size                        # entry 1 physically FIRST -> smallest offset
    off0 = table_size + len(b1)               # entry 0 physically SECOND
    off2 = table_size + len(b1) + len(b0)     # entry 2 physically THIRD -> off2 > off0
    head = bytearray(0x80)
    head[0:2] = b"EV"
    head[3] = 3
    slots = bytearray()
    slots += struct.pack("<HHBBH", off0, len(b0), 0, 0, 0)   # slot 0
    slots += struct.pack("<HHBBH", off1, len(b1), 0, 0, 0)   # slot 1
    slots += struct.pack("<HHBBH", off2, len(b2), 0, 0, 0)   # slot 2
    return bytes(head) + bytes(slots) + b1 + b0 + b2


def test_add_reinit_relocation_guard_needs_off_greater_than_off0():
    """Pins the SECOND half of the relocation guard (`u16(out, slot) > off0`) independently of the
    `size > 0` half: entry 1 is non-empty but its offset sits BEFORE off0 in the file, so it must be
    left untouched even though it is a later table slot; entry 2 (non-empty, offset after off0) still
    relocates by exactly `growth`, for contrast in the same fixture."""
    eb = _eb_reordered()
    orig = EbScript.from_bytes(eb)
    assert orig.entry(1).off < orig.entry(0).off        # the precondition this test needs: off1 < off0
    assert orig.entry(2).off > orig.entry(0).off         # ...while entry 2 sits after off0

    out = R.add_reinit(eb)
    new = EbScript.from_bytes(out)
    growth = new.entry(0).size - orig.entry(0).size

    assert new.entry(1).off == orig.entry(1).off         # off <= off0 -> guard skips relocation
    assert out[new.entry(1).abs_start:new.entry(1).abs_end] == eb[orig.entry(1).abs_start:orig.entry(1).abs_end]

    assert new.entry(2).off == orig.entry(2).off + growth   # off > off0 -> relocated by exactly growth
    assert out[new.entry(2).abs_start:new.entry(2).abs_end] == eb[orig.entry(2).abs_start:orig.entry(2).abs_end]

    assert _clean(out)


def test_add_reinit_relocates_later_entries_and_skips_empty():
    """Every later NON-empty entry's table offset shifts by exactly `growth` (with its body bytes
    riding along unchanged); the EMPTY slot (size 0) is skipped by the relocation loop outright --
    its offset/size fields are left byte-identical to the input, even though it now points at the
    wrong place in the file (harmless, since size 0 means nothing is ever read from it)."""
    eb = _multi_fixture()
    orig = EbScript.from_bytes(eb)

    out = R.add_reinit(eb)
    new = EbScript.from_bytes(out)

    growth = new.entry(0).size - orig.entry(0).size
    assert growth == len(out) - len(eb)                  # the two ways of deriving growth agree
    assert growth > 0                                    # the handler body is a net addition

    for i in (1, 3):                                     # the two non-empty later entries
        oe, ne = orig.entry(i), new.entry(i)
        assert oe.size > 0 and ne.size == oe.size         # size itself is untouched
        assert ne.off == oe.off + growth                  # offset shifted by EXACTLY growth
        assert out[ne.abs_start:ne.abs_end] == eb[oe.abs_start:oe.abs_end]   # body rode along unchanged

    oe2, ne2 = orig.entry(2), new.entry(2)                # the EMPTY entry
    assert oe2.size == 0 and ne2.size == 0
    assert ne2.off == oe2.off                             # NOT relocated (current, pinned behavior)

    assert out[3] == eb[3] == 4
    assert _clean(out)


def test_add_reinit_refuses_an_empty_entry_0():
    """REGRESSION (scout F14): the inline splice read entry 0's offset/size from an EMPTY slot (0/0) and
    returned a silently corrupt file. add_reinit now IS eb.edit.add_function's splice, which refuses."""
    eb = _eb_multi(None, [(0, RET)])
    with pytest.raises(ValueError, match=r"entry 0 is empty"):
        R.add_reinit(eb)


# ---- the past-the-end function pointer (the blank template's entry-0 Main_Loop) --------------------------
BLANK_MAIN_LOOP_MARGIN = 65     # how far past entry 0's end the blank's tag-1 fpos points


def _dangling_fixture() -> bytes:
    """Entry 0 = Main_Init (tag 0) + a tag 1 whose fpos points PAST the entry's end, the blank template's
    shape: its Main_Loop RETURN sits beyond the declared size, which the engine never loads (it reads
    exactly ``size`` bytes per entry), so the loop's IP is out of range and it just returns. Entry 1
    follows, non-empty."""
    b = bytearray(_eb_multi([(0, EM_RET), (1, RET)], [(0, RET)]))
    e0 = EbScript.from_bytes(bytes(b)).entry(0)
    slot1 = e0.abs_start + 2 + 1 * 4                     # tag 1's (tag, fpos) record
    assert struct.unpack_from("<H", b, slot1)[0] == 1
    struct.pack_into("<H", b, slot1 + 2, (e0.size - 2) + BLANK_MAIN_LOOP_MARGIN)
    return bytes(b)


def _margin(eb: bytes, tag: int = 1) -> int:
    """How far entry 0's ``tag`` pointer sits past the entry's end (> 0 = out of range, as in the blank)."""
    e0 = EbScript.from_bytes(eb).entry(0)
    return next(f.fpos for f in e0.funcs if f.tag == tag) - (e0.size - 2)


def test_add_reinit_keeps_a_past_end_pointer_past_the_end():
    """REGRESSION (the Main_Loop slide): add_function shifted EVERY fpos by the table's +4 only, so a pointer
    parked past the entry's end had the appended body slide under it -- a tag-10 longer than the blank's
    65-byte margin (the [deathrules] wipe-warp prologue alone is 52 bytes) made the engine run Main_Loop
    from the MIDDLE of Main_Reinit on every field load. It now keeps its margin for any body length, while
    an in-range function still shifts by exactly +4."""
    eb = _dangling_fixture()
    assert _margin(eb) == BLANK_MAIN_LOOP_MARGIN
    long_prologue = DM * 120                             # far longer than the margin
    out = R.add_reinit(eb, prologue=long_prologue)
    assert _margin(out) == BLANK_MAIN_LOOP_MARGIN        # still out of range -- never inside Main_Reinit
    old0 = EbScript.from_bytes(eb).entry(0).func_by_tag(0)
    new = EbScript.from_bytes(out)
    new0 = new.entry(0).func_by_tag(0)
    assert new0.fpos == old0.fpos + 4                    # the in-range Main_Init: the table growth only
    assert out[new0.abs_start:new0.abs_start + len(EM_RET)] == EM_RET
    f10 = new.entry(0).func_by_tag(10)
    assert out[f10.abs_start:f10.abs_end] == long_prologue + FADE_IN + GATED_EM + RET
    assert new.entry(1).off == EbScript.from_bytes(eb).entry(1).off + (len(out) - len(eb))


def test_add_function_leaves_an_empty_trailing_function_empty():
    """An EMPTY function at the entry's very end (fpos == end) must not come to alias the appended body --
    with the +4-only shift it pointed at the new function's first byte and would have RUN it."""
    eb = _eb_multi([(0, RET), (1, b"")], [(0, RET)])
    assert _margin(eb) == 0
    out = R.add_reinit(eb)
    e0 = EbScript.from_bytes(out).entry(0)
    assert e0.func_by_tag(1).fpos != e0.func_by_tag(10).fpos
    assert _margin(out) == 0                             # still exactly at the end: still empty


def test_reinit_prepends_carry_the_past_end_pointer():
    """The after-battle handler's later prepends -- the BGM resume and the multi-camera restore -- go through
    insert_in_function, so the past-end pointer moves WITH the bytes (the raw insert_bytes they used left it
    behind: every prepended byte ate one byte of its margin, and a 5-camera field with music ate all 65)."""
    from ff9mapkit.content import camera, music
    out = R.add_reinit(_dangling_fixture())
    out = music.add_music_to_reinit(out, 9)
    out = camera.add_camera_restore(out, {0, 1, 2, 3, 4}, [0, 1, 2, 3, 4])
    assert _margin(out) == BLANK_MAIN_LOOP_MARGIN
    f10 = EbScript.from_bytes(out).entry(0).func_by_tag(10)
    body = out[f10.abs_start:f10.abs_end]
    assert opcodes.run_sound_code(0, 9) in body
    assert body.endswith(FADE_IN + GATED_EM + RET)       # the handler's own tail rode along intact
    assert len(body) > BLANK_MAIN_LOOP_MARGIN            # long enough that the old slide would have hit it
