"""Pure tests for Phase-6b same-length AI constant patches (a hand-built minimal .eb; no install needed) +
install-gated coverage on the real EF_R007 enemy AI."""
from __future__ import annotations

import struct

import pytest

from ff9mapkit.battle import aipatch
from ff9mapkit.eb import opcodes
from ff9mapkit.eb.model import EbScript


def _minimal_eb(body: bytes) -> bytes:
    """A valid 1-entry / 1-func (tag 0) .eb wrapping ``body`` as the function bytecode (the func code starts at
    0x8E). Enough for the disassembler/patcher to walk."""
    head = bytearray(0x80)
    head[0:2] = b"EV"
    head[3] = 1                                          # entryCount
    funcbody = bytes([0, 1]) + struct.pack("<HH", 0, 4) + body   # type=0, fc=1, (tag=0, fpos=4), then code
    slot = struct.pack("<HHBBH", 8, len(funcbody), 0, 0, 0)      # off=8 (body @0x88), sz, loc, flags, pad
    return bytes(head) + slot + funcbody


# body = set_model(0x1234, 0x56) [2F 00 34 12 56] + menu(7, 2) [75 00 07 02] + RETURN [04]
_BODY = opcodes.set_model(0x1234, 0x56) + opcodes.menu(7, 2) + opcodes.RETURN
_EB = _minimal_eb(_BODY)
# the func code starts at 0x8E: set_model @0x8E -> 2-byte 0x1234 @0x90, 1-byte 0x56 @0x92;
# menu @0x93 -> 1-byte 7 @0x95, 1-byte 2 @0x96.
_OFF = 0x8E


def test_constant_sites_finds_command_immediates():
    sites = {s.offset: s for s in aipatch.constant_sites(_EB)}
    assert sites[_OFF + 2].width == 2 and sites[_OFF + 2].value == 0x1234   # set_model arg0 (2-byte)
    assert sites[_OFF + 4].width == 1 and sites[_OFF + 4].value == 0x56     # set_model arg1 (1-byte)
    assert sites[_OFF + 7].value == 7 and sites[_OFF + 8].value == 2        # menu args
    assert all("entry0/tag0" in s.where for s in sites.values())


def test_apply_patch_is_same_length_and_guarded():
    out, warns = aipatch.apply_ai_patches(_EB, [{"at": _OFF + 2, "old": 0x1234, "new": 0x4321}])
    assert not warns
    assert len(out) == len(_EB)                          # SAME length (no byte moved)
    assert out[:_OFF + 2] == _EB[:_OFF + 2] and out[_OFF + 4:] == _EB[_OFF + 4:]   # only the 2 const bytes changed
    assert struct.unpack_from("<H", out, _OFF + 2)[0] == 0x4321
    # re-reading the patched eb's site shows the new value (round-trip)
    assert {s.offset: s.value for s in aipatch.constant_sites(out)}[_OFF + 2] == 0x4321


def test_patch_guards():
    with pytest.raises(aipatch.AiPatchError, match="no patchable constant"):
        aipatch.apply_ai_patches(_EB, [{"at": _OFF + 3, "old": 0, "new": 1}])    # mid-constant offset
    with pytest.raises(aipatch.AiPatchError, match="expected old"):
        aipatch.apply_ai_patches(_EB, [{"at": _OFF + 2, "old": 999, "new": 1}])  # old mismatch
    with pytest.raises(aipatch.AiPatchError, match="does not fit"):
        aipatch.apply_ai_patches(_EB, [{"at": _OFF + 4, "old": 0x56, "new": 300}])  # 1-byte can't hold 300
    with pytest.raises(aipatch.AiPatchError, match="needs integer"):
        aipatch.apply_ai_patches(_EB, [{"at": _OFF + 4, "old": 0x56}])           # missing new
    with pytest.raises(aipatch.AiPatchError):
        aipatch.apply_ai_patches(_EB, [5])                                        # non-dict
    with pytest.raises(aipatch.AiPatchError):
        aipatch.apply_ai_patches(_EB, "x")                                        # non-list


def test_noop_patch_is_byte_identical():
    out, _w = aipatch.apply_ai_patches(_EB, [{"at": _OFF + 4, "old": 0x56, "new": 0x56}])
    assert out == _EB                                    # old == new -> nothing moves, byte-identical


def test_duplicate_offset_warns():
    out, warns = aipatch.apply_ai_patches(_EB, [{"at": _OFF + 4, "old": 0x56, "new": 1},
                                                {"at": _OFF + 4, "old": 0x56, "new": 2}])
    assert any("both patch offset" in w for w in warns) and out[_OFF + 4] == 2   # later wins


def test_validate_patches_offline():
    assert aipatch.validate_patches(_EB, [{"at": _OFF + 2, "old": 0x1234, "new": 0x4321}]) == []
    assert aipatch.validate_patches(_EB, [{"at": 99999, "old": 0, "new": 0}])    # bad offset surfaced


# ---- review fixes: malformed-eb guard, B_CONST4 26-bit mask, generic width ---------------------------
def test_malformed_eb_raises_aipatcherror_not_indexerror():
    head = bytearray(0x80); head[0:2] = b"EV"; head[3] = 1
    body = bytes([0, 200])                               # type=0, funcCount=200 -> the func table overruns
    bad = bytes(head) + struct.pack("<HHBBH", 8, len(body), 0, 0, 0) + body
    with pytest.raises(aipatch.AiPatchError, match="malformed/truncated"):
        aipatch.constant_sites(bad)                      # a CLEAN error, not a raw IndexError
    assert aipatch.validate_patches(bad, [{"at": 0, "old": 0, "new": 0}])   # surfaced as a lint message, no crash
    with pytest.raises(aipatch.AiPatchError):
        aipatch.apply_ai_patches(bad, [{"at": 0, "old": 0, "new": 0}])


def test_b_const4_capped_to_26_bits():
    # body = set(0x05) with expression [B_CONST4(1000), B_EXPR_END]  ->  05 7E E8 03 00 00 7F
    eb = _minimal_eb(bytes([0x05, 0x7E]) + struct.pack("<I", 1000) + bytes([0x7F]))
    site = next(s for s in aipatch.constant_sites(eb) if "expr-const4" in s.where)
    assert site.value == 1000 and site.width == 4 and site.vmax == 0x3FFFFFF
    aipatch.apply_ai_patches(eb, [{"at": site.offset, "old": 1000, "new": 0x3FFFFFF}])   # at the cap: ok
    with pytest.raises(aipatch.AiPatchError, match="masks this B_CONST4"):
        aipatch.apply_ai_patches(eb, [{"at": site.offset, "old": 1000, "new": 0x04000000}])  # past 26 bits


# ---- install-gated: the real EF_R007 enemy AI -------------------------------------------------------
def test_real_donor_ai_sites_and_roundtrip():
    try:
        from ff9mapkit.battle import extract
        eb = extract.read_scene_assets("EF_R007")["eb"]["us"]
    except Exception:                                    # noqa: BLE001 -- no install / UnityPy -> skip
        pytest.skip("needs the FF9 install + UnityPy")
    sites = aipatch.constant_sites(eb)
    assert len(sites) > 0
    s = sites[0]
    out, _w = aipatch.apply_ai_patches(eb, [{"at": s.offset, "old": s.value, "new": s.value}])
    assert out == eb                                     # a no-op patch on real AI is byte-identical


# ---- per-language: a battle eb's bytecode is NOT language-identical ----------------------------------
# 41 of the 562 stock scenes differ in LENGTH between languages (35 jp-only). A `[[scene.ai_patch]]` `at` is a
# constant in the us donor (`battle-ai --sites`); each language locates THAT constant structurally, never the
# offset. These fixtures are one-function ebs (entry 0 / tag 0, code at 0x8E) standing in for us and jp.
_W7, _T0, _M0 = opcodes.wait(7), opcodes.turn_instant(0), opcodes.menu(0, 0)


def _rows(eb):
    return aipatch.func_rows(EbScript.from_bytes(eb), 0, 0)


def test_a_longer_jp_eb_is_patched_at_the_counterpart_not_the_us_offset():
    us = _minimal_eb(_W7 + _W7 + opcodes.RETURN)            # patch the SECOND Wait(7): its arg is at 0x93
    jp = _minimal_eb(_T0 + _W7 + _W7 + opcodes.RETURN)      # a jp-only instruction first: 0x93 is jp's FIRST Wait(7)
    at = _OFF + 5
    assert us[at] == 7 and jp[at] == 7                      # the old offset rule wrote jp's first Wait -- same value,
    out, _ = aipatch.apply_ai_patches(jp, [{"at": at, "old": 7, "new": 8}], ref=us, lang="jp")   # wrong constant
    assert out[_OFF + 3 + 5] == 8                           # the counterpart: jp's second Wait
    assert out[at] == 7 and len(out) == len(jp)             # jp's first Wait is untouched
    assert aipatch.correspond(_rows(us), _rows(jp)) == [1, 2, 3]


def test_the_reference_patches_itself_by_offset_exactly_as_before():
    us = _minimal_eb(_W7 + _W7 + opcodes.RETURN)
    a, _ = aipatch.apply_ai_patches(us, [{"at": _OFF + 5, "old": 7, "new": 8}])
    b, _ = aipatch.apply_ai_patches(us, [{"at": _OFF + 5, "old": 7, "new": 8}], ref=bytes(us))   # equal, not identical
    assert a == b and a[_OFF + 5] == 8 and a[_OFF + 2] == 7
    assert aipatch.correspond(_rows(us), _rows(us)) == [0, 1, 2]


def test_a_constant_inside_the_differing_stretch_is_refused():
    us = _minimal_eb(opcodes.wait(3) + opcodes.wait(4) + opcodes.RETURN)
    jp = _minimal_eb(opcodes.wait(3) + _T0 + _T0 + opcodes.RETURN)
    assert aipatch.correspond(_rows(us), _rows(jp)) == [0, None, 3]
    with pytest.raises(aipatch.AiPatchError, match="cannot be patched in jp's battle script.*no provable counterpart"):
        aipatch.apply_ai_patches(jp, [{"at": _OFF + 5, "old": 4, "new": 9}], ref=us, lang="jp")
    out, _ = aipatch.apply_ai_patches(jp, [{"at": _OFF + 2, "old": 3, "new": 9}], ref=us, lang="jp")
    assert out[_OFF + 2] == 9                               # the matched Wait before the stretch still patches


def test_a_counterpart_holding_another_value_is_refused():
    us, jp = _minimal_eb(opcodes.wait(3) + opcodes.RETURN), _minimal_eb(opcodes.wait(9) + opcodes.RETURN)
    assert aipatch.correspond(_rows(us), _rows(jp)) == [0, 1]    # the same instruction (values aside) ...
    with pytest.raises(aipatch.AiPatchError, match="holds 9 in jp's battle script, not 3"):   # ... per-lang value
        aipatch.apply_ai_patches(jp, [{"at": _OFF + 2, "old": 3, "new": 5}], ref=us, lang="jp")


@pytest.mark.parametrize("us_body, jp_body, want", [
    (_W7 + opcodes.RETURN, _W7 + _W7 + opcodes.RETURN, [None, 2]),              # jp longer: which Wait is new?
    (_W7 + _W7 + opcodes.RETURN, _W7 + opcodes.RETURN, [None, None, 1]),         # jp SHORTER: the overlap sits on
])                                                                               # jp's side (AC_E031's shape)
def test_a_length_difference_inside_a_repeated_run_is_ambiguous_on_either_side(us_body, jp_body, want):
    us, jp = _minimal_eb(us_body), _minimal_eb(jp_body)
    assert aipatch.correspond(_rows(us), _rows(jp)) == want
    with pytest.raises(aipatch.AiPatchError, match="no provable counterpart"):
        aipatch.apply_ai_patches(jp, [{"at": _OFF + 2, "old": 7, "new": 8}], ref=us, lang="jp")


def _jmp(rel: int) -> bytes:
    return bytes([0x01]) + struct.pack("<h", rel)


def test_a_matched_jump_that_lands_elsewhere_cuts_the_match_back():
    # us: Wait(1); JMP -> RET; Wait(7); Turn(3); RET      jp: the same, plus a jp-only Menu the jump lands on.
    # Prefix/suffix alone match jp's Wait(7) (same shape, same value) -- but the jumps disagree (us skips the Turn,
    # jp does not), so the edit starts at the jump and nothing after it in the prefix is provably the same.
    us = _minimal_eb(opcodes.wait(1) + _jmp(6) + _W7 + opcodes.turn_instant(3) + opcodes.RETURN)
    jp = _minimal_eb(opcodes.wait(1) + _jmp(3) + _W7 + _M0 + opcodes.turn_instant(3) + opcodes.RETURN)
    assert aipatch.correspond(_rows(us), _rows(jp)) == [0, None, None, 4, 5]
    with pytest.raises(aipatch.AiPatchError, match="no provable counterpart"):
        aipatch.apply_ai_patches(jp, [{"at": _OFF + 8, "old": 7, "new": 8}], ref=us, lang="jp")


def test_an_insertion_at_a_jump_landing_keeps_the_match():
    # the join point: jp inserts a Menu exactly where both jumps land -- us's jump reaches its (matched) Turn, jp's
    # the inserted Menu. Both land at the edge of the same edit, so the jump and the code before it still match.
    us = _minimal_eb(opcodes.wait(1) + _jmp(3) + _W7 + opcodes.turn_instant(3) + opcodes.RETURN)
    jp = _minimal_eb(opcodes.wait(1) + _jmp(3) + _W7 + _M0 + opcodes.turn_instant(3) + opcodes.RETURN)
    assert aipatch.correspond(_rows(us), _rows(jp)) == [0, 1, 2, 4, 5]
    out, _ = aipatch.apply_ai_patches(jp, [{"at": _OFF + 8, "old": 7, "new": 8}], ref=us, lang="jp")
    assert out[_OFF + 8] == 8
