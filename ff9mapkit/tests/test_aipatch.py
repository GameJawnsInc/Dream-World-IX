"""Pure tests for Phase-6b same-length AI constant patches (a hand-built minimal .eb; no install needed) +
install-gated coverage on the real EF_R007 enemy AI."""
from __future__ import annotations

import struct

import pytest

from ff9mapkit.battle import aipatch
from ff9mapkit.eb import opcodes


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
