"""Phase-6c-ii tests: enemy-AI branch AUTHORING (assemble a branch + splice it into a battle .eb).

Synthetic (a hand-built minimal .eb, no install) proves the insert/replace mechanics + the byte-intact fixup;
the real-donor test proves it on a shipping enemy AI (install-gated, skips without it)."""
from __future__ import annotations

import struct

import pytest

from ff9mapkit.battle import aiauthor
from ff9mapkit.battle.aiauthor import AiAuthorError
from ff9mapkit.eb import cmdasm, opcodes
from ff9mapkit.eb.model import EbScript


def _minimal_eb(body: bytes) -> bytes:
    """A valid 1-entry / 1-func (tag 0) .eb wrapping ``body`` as the function bytecode (func code @0x8E)."""
    head = bytearray(0x80)
    head[0:2] = b"EV"
    head[3] = 1                                          # entryCount
    funcbody = bytes([0, 1]) + struct.pack("<HH", 0, 4) + body   # type=0, fc=1, (tag=0, fpos=4), then code
    slot = struct.pack("<HHBBH", 8, len(funcbody), 0, 0, 0)      # off=8 (body @0x88), sz, loc, flags, pad
    return bytes(head) + slot + funcbody


# a real little branch: a guard jump, a SET (an expression with an assignment), and the terminating RET
_BRANCH = "JMP_IF(end)\nSET({B_CURHP const(1) B_LT B_EXPR_END})\nend:\nRET()"


def test_add_ai_function_inserts_and_reparses():
    eb = _minimal_eb(opcodes.RETURN)
    new = aiauthor.add_ai_function(eb, 0, 6, _BRANCH)
    s = EbScript.from_bytes(new)                         # re-parses cleanly (codec identity holds)
    f = s.entry(0).func_by_tag(6)
    assert f is not None and f.tag == 6
    assert bytes(s.data[f.abs_start:f.abs_end]) == cmdasm.assemble_block(_BRANCH)   # the branch is byte-correct
    f0 = s.entry(0).func_by_tag(0)                       # the pre-existing func is byte-intact (fpos fixed up)
    assert bytes(s.data[f0.abs_start:f0.abs_end]) == opcodes.RETURN


def test_replace_ai_function_body():
    eb = _minimal_eb(opcodes.set_model(1, 2) + opcodes.RETURN)
    new = aiauthor.replace_ai_function(eb, 0, 0, "RET()")
    s = EbScript.from_bytes(new)
    assert bytes(s.data[s.entry(0).func_by_tag(0).abs_start:s.entry(0).func_by_tag(0).abs_end]) == bytes((0x04,))


def test_add_duplicate_tag_errors():
    with pytest.raises(AiAuthorError, match="already has a function with tag"):
        aiauthor.add_ai_function(_minimal_eb(opcodes.RETURN), 0, 0, "RET()")   # tag 0 already exists


def test_replace_missing_tag_errors():
    with pytest.raises(AiAuthorError, match="no function with tag"):
        aiauthor.replace_ai_function(_minimal_eb(opcodes.RETURN), 0, 6, "RET()")


def test_bad_entry_index_errors():
    with pytest.raises(AiAuthorError, match="out of range"):
        aiauthor.add_ai_function(_minimal_eb(opcodes.RETURN), 9, 6, "RET()")


def test_bad_source_errors():
    with pytest.raises(AiAuthorError, match="did not assemble"):
        aiauthor.add_ai_function(_minimal_eb(opcodes.RETURN), 0, 6, "FLARGLE()")


def test_branch_without_terminator_rejected():
    # review HIGH fix: a body that doesn't end in RET/TerminateEntry would run the IP off the function at runtime
    with pytest.raises(AiAuthorError, match="must END in RET"):
        aiauthor.add_ai_function(_minimal_eb(opcodes.RETURN), 0, 6,
                                 "SET({B_CURHP const(1) B_LT B_EXPR_END})")   # no terminating RET


# ---- Phase-6c-iii: the [[scene.ai_function]] build surface --------------------------------------------
_SPEC = [{"entry": 0, "tag": 6, "source": "SET({B_CURHP const(1) B_LT B_EXPR_END}); RET()"}]


def test_apply_ai_functions_adds():
    out = aiauthor.apply_ai_functions(_minimal_eb(opcodes.RETURN), _SPEC)
    assert EbScript.from_bytes(out).entry(0).func_by_tag(6) is not None       # ';' source separator works


def test_apply_ai_functions_replace():
    eb = _minimal_eb(opcodes.set_model(1, 2) + opcodes.RETURN)
    out = aiauthor.apply_ai_functions(eb, [{"entry": 0, "tag": 0, "source": "RET()", "replace": True}])
    s = EbScript.from_bytes(out)
    assert bytes(s.data[s.entry(0).func_by_tag(0).abs_start:s.entry(0).func_by_tag(0).abs_end]) == bytes((0x04,))


def test_apply_ai_functions_bad_spec():
    with pytest.raises(AiAuthorError, match="needs integer entry"):
        aiauthor.apply_ai_functions(_minimal_eb(opcodes.RETURN), [{"tag": 6, "source": "RET()"}])
    with pytest.raises(AiAuthorError, match="non-empty source"):
        aiauthor.apply_ai_functions(_minimal_eb(opcodes.RETURN), [{"entry": 0, "tag": 6, "source": ""}])


def test_validate_ai_functions_ok_and_lints():
    assert aiauthor.validate_ai_functions(_minimal_eb(opcodes.RETURN), _SPEC) == []
    # a non-terminating authored branch is caught (here by the add wrapper's RET guard, surfaced as a string)
    bad = [{"entry": 0, "tag": 6, "source": "SET({B_CURHP const(1) B_LT B_EXPR_END})"}]
    assert aiauthor.validate_ai_functions(_minimal_eb(opcodes.RETURN), bad)


def test_tag_out_of_range_clean_error():
    # review fix: an out-of-u16-range tag must surface a clean AiAuthorError, NOT a raw struct.error from eb.edit
    for bad_tag in (70000, -1):
        spec = [{"entry": 0, "tag": bad_tag, "source": "RET()"}]
        with pytest.raises(AiAuthorError, match="out of range"):
            aiauthor.apply_ai_functions(_minimal_eb(opcodes.RETURN), spec)
        v = aiauthor.validate_ai_functions(_minimal_eb(opcodes.RETURN), spec)   # validate RETURNS, never raises
        assert v and "out of range" in v[0]


def test_add_ai_function_on_real_donor():
    # add a new AI phase to a SHIPPING enemy AI; assert it re-parses, the branch is present, and every OTHER
    # function + a later entry is byte-intact (the entry-table + fpos fixup didn't corrupt anything).
    try:
        from ff9mapkit.battle import battleai
        eb0 = battleai._scene_eb("EF_R007")
    except Exception:                                   # noqa: BLE001 -- no install -> skip
        pytest.skip("needs the FF9 install + UnityPy")
    s0 = EbScript.from_bytes(eb0)
    entry_idx = next((e.index for e in s0.entries if not e.empty and e.index >= 1 and e.func_count > 0), None)
    if entry_idx is None:
        pytest.skip("donor has no per-type AI entry")
    existing = {f.tag for f in s0.entry(entry_idx).funcs}
    free_tag = next(t for t in (6, 7, 9, 1) if t not in existing)
    new = aiauthor.add_ai_function(eb0, entry_idx, free_tag, "RET()")
    s1 = EbScript.from_bytes(new)
    assert s1.entry(entry_idx).func_by_tag(free_tag) is not None
    for t in existing:                                  # the entry's pre-existing funcs are byte-identical
        a, b = s0.entry(entry_idx).func_by_tag(t), s1.entry(entry_idx).func_by_tag(t)
        assert bytes(s0.data[a.abs_start:a.abs_end]) == bytes(s1.data[b.abs_start:b.abs_end])
    later = next((e.index for e in s0.entries if not e.empty and e.index > entry_idx), None)
    if later is not None:                               # a later entry's body survived the offset fixup
        a, b = s0.entry(later), s1.entry(later)
        assert bytes(s0.data[a.abs_start:a.abs_end]) == bytes(s1.data[b.abs_start:b.abs_end])
