"""Phase-6c (productized) tests: the declarative branch-INSERT + HP-PHASE battle.toml surfaces, plus the
``B_MEMBER`` selector naming (read = disassembler annotation, write = ``B_MEMBER(cur.hp)`` in authored source).

Synthetic (a hand-built minimal .eb with a variable-driven Attack, no install) -- proves the generator, the
splice, the var-inference, and the error paths byte-for-byte without the game."""
from __future__ import annotations

import struct

import pytest

from ff9mapkit.battle import aiauthor, ailint, battleai
from ff9mapkit.battle.aiauthor import AiAuthorError
from ff9mapkit.eb import cmdasm, exprasm
from ff9mapkit.eb._membertable import member_name, member_selector
from ff9mapkit.eb.model import EbScript


def _minimal_eb(body: bytes) -> bytes:
    """A valid 1-entry / 1-func (tag 0) .eb wrapping ``body`` (mirrors test_aiauthor)."""
    head = bytearray(0x80)
    head[0:2] = b"EV"
    head[3] = 1
    funcbody = bytes([0, 1]) + struct.pack("<HH", 0, 4) + body
    slot = struct.pack("<HHBBH", 8, len(funcbody), 0, 0, 0)
    return bytes(head) + slot + funcbody


# a function whose Attack reads a single variable (Instance.Byte[5]) -- the shape ai_phase requires.
_ATTACK_FN = ("SET({Instance.Byte[5] const(0) B_LET B_EXPR_END})\n"
              "Attack({Instance.Byte[5] B_EXPR_END})\n"
              "RET()")


def _eb_with_attack() -> bytes:
    return _minimal_eb(cmdasm.assemble_block(_ATTACK_FN))


_MARKER = "SET({Instance.Byte[7] const(99) B_LET B_EXPR_END})"   # a valid, identifiable insert fragment


# ---- the B_MEMBER selector name table -----------------------------------------------------------------
def test_member_table_roundtrip():
    assert member_selector("cur.hp") == 36 and member_name(36) == "cur.hp"
    assert member_selector("max.hp") == 35 and member_name(35) == "max.hp"
    assert member_selector("cur.mp") == 38 and member_selector("level") == 41
    assert member_name(9999) is None and member_selector("nope") is None
    for sel, nm in (("phys_def", 74), ("status.cur.hi", 46)):   # spot-check a few non-HP members
        assert member_selector(sel) == nm


def test_exprasm_accepts_member_names():
    assert exprasm.assemble_token("B_MEMBER(cur.hp)") == bytes((0x29, 36))   # name resolves to the selector byte
    assert exprasm.assemble_token("B_MEMBER(max.hp)") == bytes((0x29, 35))
    assert exprasm.assemble_token("B_MEMBER(36)") == bytes((0x29, 36))       # numeric still works
    with pytest.raises(exprasm.AssembleError, match="unknown member name"):
        exprasm.assemble_token("B_MEMBER(bogus.field)")
    with pytest.raises(exprasm.AssembleError, match="numeric operand"):       # B_PTR has no name table
        exprasm.assemble_token("B_PTR(cur.hp)")


def test_disassemble_annotates_members():
    # a function that reads cur.hp -> the disassembly line carries a "# B_MEMBER 36=cur.hp" annotation
    body = cmdasm.assemble_block("SET({B_SYSLIST[1] B_MEMBER(36) const(0) B_EQ_E B_COUNT B_EXPR_END})\nRET()")
    text = battleai.disassemble_ai(_minimal_eb(body))
    assert "# B_MEMBER 36=cur.hp" in text
    # a function with no named member gets no annotation
    plain = battleai.disassemble_ai(_minimal_eb(cmdasm.assemble_block("RET()")))
    assert "# B_MEMBER" not in plain


# ---- [[scene.ai_insert]] : splice a fragment ----------------------------------------------------------
def test_ai_insert_before_attack():
    eb = _eb_with_attack()
    frag = "SET({Instance.Byte[5] const(2) B_LET B_EXPR_END})"   # override the attack var (a fragment, no RET)
    out = aiauthor.apply_ai_inserts(eb, [{"entry": 0, "tag": 0, "before": "Attack", "source": frag}])
    s = EbScript.from_bytes(out)                                  # re-parses cleanly
    instrs = list(battleai._decode_func_pretty(s.data, s.entry(0).func_by_tag(0).abs_start,
                                               s.entry(0).func_by_tag(0).abs_end))
    mnems = [mn for _, mn, _ in instrs]
    assert mnems == ["SET", "SET", "Attack", "RET"]              # the fragment SET landed right before Attack
    assert not ailint.lint_ai(out)                               # composed body still lints clean


def test_ai_insert_at_offset_and_after():
    eb = _eb_with_attack()
    out = aiauthor.apply_ai_inserts(eb, [{"entry": 0, "tag": 0, "at": 0, "source": _MARKER}])  # prepend
    s = EbScript.from_bytes(out)
    first = next(battleai._decode_func_pretty(s.data, s.entry(0).func_by_tag(0).abs_start,
                                              s.entry(0).func_by_tag(0).abs_end))
    assert "Instance.Byte[7]" in first[2][0]              # the prepended marker fragment is now first
    out2 = aiauthor.apply_ai_inserts(eb, [{"entry": 0, "tag": 0, "after": "Attack", "source": _MARKER}])
    assert EbScript.from_bytes(out2).entry(0).func_by_tag(0) is not None   # after the Attack, before RET -> valid


@pytest.mark.parametrize("spec,msg", [
    ({"entry": 0, "tag": 0, "source": _MARKER}, "exactly one locator"),
    ({"entry": 0, "tag": 0, "before": "Attack", "at": 0, "source": _MARKER}, "exactly one locator"),
    ({"entry": 0, "tag": 0, "before": "Nope", "source": _MARKER}, "no such instruction"),
    ({"entry": 0, "tag": 0, "before": "Attack", "source": "FLARGLE()"}, "did not assemble"),
    ({"entry": 0, "tag": 0, "before": "Attack"}, "non-empty source"),
])
def test_ai_insert_errors(spec, msg):
    with pytest.raises(AiAuthorError, match=msg):
        aiauthor.apply_ai_inserts(_eb_with_attack(), [spec])


# ---- [[scene.ai_phase]] : generate + splice the HP-threshold branch -----------------------------------
def test_ai_phase_generates_below_half():
    eb = _eb_with_attack()
    out = aiauthor.apply_ai_phases(eb, [{"entry": 0, "tag": 0, "stat": "hp", "below": 0.5, "then": 2, "else": 0}])
    s = EbScript.from_bytes(out)
    instrs = list(battleai._decode_func_pretty(s.data, s.entry(0).func_by_tag(0).abs_start,
                                               s.entry(0).func_by_tag(0).abs_end))
    joined = " | ".join(f"{mn}({','.join(ops)})" for _, mn, ops in instrs)
    assert "B_MEMBER(36)" in joined and "B_MEMBER(35)" in joined   # reads cur.hp + max.hp
    assert "const(2) B_DIV" in joined                              # below=0.5 -> /2 (the unit-fraction idiom)
    assert "B_LT_E B_COUNT" in joined                              # the proven extract-compare idiom
    assert [mn for _, mn, _ in instrs].count("JMP_IFNOT") == 1     # one phase branch inserted
    assert not ailint.lint_ai(out)                                # composed lints clean


def test_ai_phase_threshold_quarter():
    out = aiauthor.apply_ai_phases(_eb_with_attack(),
                                   [{"entry": 0, "tag": 0, "below": 0.25, "then": 1, "else": 0}])
    s = EbScript.from_bytes(out)
    joined = battleai.disassemble_ai(out)
    assert "const(4) B_DIV" in joined                              # 1/4 -> /4


@pytest.mark.parametrize("spec,msg", [
    ({"entry": 0, "tag": 0, "then": 2, "else": 0, "below": 0.3}, "unit fraction"),
    ({"entry": 0, "tag": 0, "then": 2, "else": 0, "stat": "gil"}, "stat must be"),
    ({"entry": 0, "tag": 0, "then": 999, "else": 0}, "out of range"),
    ({"entry": 0, "tag": 0, "else": 0}, "then"),                   # missing 'then'
])
def test_ai_phase_errors(spec, msg):
    with pytest.raises(AiAuthorError, match=msg):
        aiauthor.apply_ai_phases(_eb_with_attack(), [spec])


def test_ai_phase_rejects_immediate_attack():
    # an Attack that uses an immediate index (not a variable) can't be phase-overridden -> a clear error
    eb = _minimal_eb(cmdasm.assemble_block("Attack(3)\nRET()"))
    with pytest.raises(AiAuthorError, match="must read a single variable"):
        aiauthor.apply_ai_phases(eb, [{"entry": 0, "tag": 0, "then": 2, "else": 0}])


def test_ai_phase_rejects_multiple_attacks():
    eb = _minimal_eb(cmdasm.assemble_block(
        "SET({Instance.Byte[5] const(0) B_LET B_EXPR_END})\nAttack({Instance.Byte[5] B_EXPR_END})\n"
        "Attack({Instance.Byte[5] B_EXPR_END})\nRET()"))
    with pytest.raises(AiAuthorError, match="exactly ONE Attack"):
        aiauthor.apply_ai_phases(eb, [{"entry": 0, "tag": 0, "then": 2, "else": 0}])


def test_validate_ai_edits_catches_lint():
    # validate_ai_edits dry-runs + lints; a phase on a clean fn returns no problems
    assert not aiauthor.validate_ai_edits(_eb_with_attack(),
                                          phases=[{"entry": 0, "tag": 0, "then": 2, "else": 0}], atk_count=6)
