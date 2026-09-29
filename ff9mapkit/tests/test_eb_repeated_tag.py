"""A function tag is NOT unique inside an ``.eb`` entry, and the splice primitives must not assume it is.

Stock repeats a tag in 15 entries across 14 of the 818 US field EVTs -- ``evt_alex5_at_center`` (field 2452)
entry 4 lists tag 1 twice, ``evt_eforest1_ef_dep_0`` (field 257) entry 16 tag 26 twice. ``insert_in_function``
used to move the OTHER functions' ``fpos`` by skipping every function carrying the edited TAG, so a prepend
to the first tag-1 left the second tag-1's ``fpos`` where it was: it then started INSIDE the inserted bytes
(on 2452 the first tag 1 stayed 6 bytes long while the second grew by the insert). The primitives now move
``fpos`` by function INDEX and take a ``func_index`` to address a namesake past the first, sharing one
selector with ``replace_function_body``. Synthetic bytes -- no game install needed.
"""
from __future__ import annotations

import pytest

from ff9mapkit.eb import EbScript, edit, opcodes
from ff9mapkit.eb.model import pack_entry

RET = opcodes.RETURN
W1 = opcodes.wait(1)
A = W1 + RET                                        # the first tag-1 body
B = opcodes.wait(2) + opcodes.wait(3) + RET          # the second tag-1 body (a different length, so a slip shows)
INS = opcodes.wait(9)


def _eb() -> bytes:
    """Entry 1 has 2452 entry 4's shape: tag 0, tag 1, tag 1 again, then a later tag -- so the namesake and a
    function after it both have an ``fpos`` to move. Entries 0 and 2 frame it, so a bad relayout shows."""
    head = bytearray(0x80)
    head[0:2] = b"EV"
    out = edit.append_entry(bytes(head), 0, pack_entry(0, [(0, RET)]))
    out = edit.append_entry(out, 1, pack_entry(0, [(0, RET), (1, A), (1, B), (3, RET)]))
    return edit.append_entry(out, 2, pack_entry(0, [(0, RET)]))


def _bodies(data: bytes, entry: int = 1) -> list[tuple[int, bytes]]:
    return [(f.tag, data[f.abs_start:f.abs_end]) for f in EbScript.from_bytes(data).entry(entry).funcs]


def test_fixture_really_repeats_a_tag():
    assert _bodies(_eb()) == [(0, RET), (1, A), (1, B), (3, RET)]


@pytest.mark.parametrize("func_index, rel_off, want", [
    (None, 0, [(0, RET), (1, INS + A), (1, B), (3, RET)]),              # by tag = the FIRST namesake, prepend
    (None, len(W1), [(0, RET), (1, W1 + INS + RET), (1, B), (3, RET)]),  # ... and mid-function
    (1, 0, [(0, RET), (1, INS + A), (1, B), (3, RET)]),                 # the first, by index
    (2, 0, [(0, RET), (1, A), (1, INS + B), (3, RET)]),                 # the SECOND namesake, by index
    (2, len(B) - 1, [(0, RET), (1, A), (1, B[:-1] + INS + RET), (3, RET)]),
], ids=["first-by-tag", "first-mid", "first-by-index", "second-by-index", "second-mid"])
def test_insert_moves_the_namesakes_fpos(func_index, rel_off, want):
    raw = _eb()
    kw = {} if func_index is None else {"func_index": func_index}    # by tag = the plain positional call
    out = edit.insert_in_function(raw, 1, 1, rel_off, INS, **kw)
    assert _bodies(out) == want
    before = EbScript.from_bytes(raw).entry(1).funcs
    after = EbScript.from_bytes(out).entry(1).funcs
    edited = 1 if func_index is None else func_index
    for f0, f1 in zip(before, after):                  # every function AFTER the edited one moved -- by index
        assert f1.fpos == f0.fpos + (len(INS) if f0.index > edited else 0), (f0.index, f0.tag)
    assert _bodies(out, 0) == _bodies(out, 2) == [(0, RET)]


def test_first_namesake_prepend_leaves_the_second_intact():
    """The measured bug, stated directly: after a prepend to the first tag 1 the second tag 1 starts past the
    inserted bytes, not inside them, and keeps its own length."""
    raw = _eb()
    out = edit.insert_in_function(raw, 1, 1, 0, INS)
    first, second = EbScript.from_bytes(out).entry(1).funcs[1:3]
    assert second.fpos == EbScript.from_bytes(raw).entry(1).funcs[2].fpos + len(INS)
    assert (first.length, second.length) == (len(INS) + len(A), len(B))


def test_replace_addresses_the_second_namesake_by_index():
    new = opcodes.wait(4) + opcodes.wait(5) + opcodes.wait(6) + RET
    out = edit.replace_function_body(_eb(), 1, 1, new, func_index=2)
    assert _bodies(out) == [(0, RET), (1, A), (1, new), (3, RET)]
    assert _bodies(out, 0) == _bodies(out, 2) == [(0, RET)]


@pytest.mark.parametrize("prim", ["insert", "replace"])
@pytest.mark.parametrize("func_index, match", [(3, "not the expected 1"), (4, "out of range"),
                                               (-1, "out of range")])
def test_func_index_is_checked_against_the_tag(prim, func_index, match):
    with pytest.raises(ValueError, match=match):
        if prim == "insert":
            edit.insert_in_function(_eb(), 1, 1, 0, INS, func_index=func_index)
        else:
            edit.replace_function_body(_eb(), 1, 1, RET, func_index=func_index)
