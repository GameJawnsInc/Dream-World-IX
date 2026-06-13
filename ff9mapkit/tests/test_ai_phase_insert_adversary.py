"""LENS-4 (test adversary) additions to test_ai_phase_insert.py -- four untested paths:

1. the disassembler's ``# B_MEMBER`` ANNOTATION does not corrupt the operand text -> the annotated line still
   re-assembles to the same expression bytes (the annotation is display-only, as documented in battleai.py:29).
2. a member NAME (``B_MEMBER(cur.hp)``) used END-TO-END inside a real ``[[scene.ai_insert]]`` / ``[[scene.ai_phase]]``
   source string (the token-level test_exprasm_accepts_member_names only proves assemble_token; nothing proved the
   name survives the cmdasm.assemble_block -> splice path an authored battle.toml actually uses).
3. the ``after`` locator on the LAST instruction of a function (and the equivalent ``at = <func length>``
   append-at-end) -- exercises the ``_locate_insert`` -> ``f.abs_end`` boundary that no existing test hits.
4. ``validate_ai_edits`` on a BROKEN ``inserts=`` spec (the existing test only validates a clean ``phases=``).

Mirrors the host file's synthetic-eb harness (no install)."""
from __future__ import annotations

import struct

import pytest

from ff9mapkit.battle import aiauthor, ailint, battleai
from ff9mapkit.eb import cmdasm, exprasm
from ff9mapkit.eb.model import EbScript


def _minimal_eb(body: bytes) -> bytes:
    head = bytearray(0x80)
    head[0:2] = b"EV"
    head[3] = 1
    funcbody = bytes([0, 1]) + struct.pack("<HH", 0, 4) + body
    slot = struct.pack("<HHBBH", 8, len(funcbody), 0, 0, 0)
    return bytes(head) + slot + funcbody


_ATTACK_FN = ("SET({Instance.Byte[5] const(0) B_LET B_EXPR_END})\n"
              "Attack({Instance.Byte[5] B_EXPR_END})\n"
              "RET()")


def _eb_with_attack() -> bytes:
    return _minimal_eb(cmdasm.assemble_block(_ATTACK_FN))


# 1. ---- the # B_MEMBER annotation is display-only: the operand still round-trips through assemble -----------
def test_annotation_does_not_break_assemble_roundtrip():
    """The disassembler appends ``# B_MEMBER 36=cur.hp`` to the line, but the operand text BEFORE the ``#`` must
    re-assemble to the exact original expression bytes (battleai.py:29 promises the operand stays raw)."""
    expr = "{B_SYSLIST[1] B_MEMBER(36) const(0) B_EQ_E B_COUNT B_EXPR_END}"
    expr_bytes = exprasm.assemble(expr)
    body = cmdasm.assemble_block(f"SET({expr})\nRET()")
    text = battleai.disassemble_ai(_minimal_eb(body))

    set_line = next(ln for ln in text.splitlines() if "SET(" in ln and "B_MEMBER" in ln)
    assert "# B_MEMBER 36=cur.hp" in set_line               # the annotation is present...
    operand_part = set_line.split("#", 1)[0]                # ...but everything left of '#' is the raw operand text
    inner = operand_part[operand_part.index("{"):operand_part.rindex("}") + 1]
    assert exprasm.assemble(inner) == expr_bytes            # which re-assembles byte-for-byte (annotation inert)


# 2. ---- a member NAME flows through the real ai_insert / ai_phase source path (not just assemble_token) ------
def test_member_name_in_ai_insert_source_end_to_end():
    """``B_MEMBER(cur.hp)`` written in an authored ``[[scene.ai_insert]]`` source resolves to selector 36 in the
    spliced eb -- proving the name survives cmdasm.assemble_block + insert_in_function, the path battle.toml uses."""
    eb = _eb_with_attack()
    src = "SET({B_SYSLIST[1] B_MEMBER(cur.hp) const(0) B_EQ_E B_COUNT B_EXPR_END})"
    out = aiauthor.apply_ai_inserts(eb, [{"entry": 0, "tag": 0, "before": "Attack", "source": src}])
    s = EbScript.from_bytes(out)
    f = s.entry(0).func_by_tag(0)
    instrs = list(battleai._decode_func_pretty(s.data, f.abs_start, min(f.abs_end, len(s.data))))
    joined = " | ".join(f"{mn}({','.join(ops)})" for _, mn, ops in instrs)
    assert "B_MEMBER(36)" in joined                          # the name cur.hp encoded to the numeric selector
    assert "B_SYSLIST[1] B_MEMBER(36)" in joined.replace(", ", " ")
    assert not ailint.lint_ai(out)                           # and the composed body still lints clean


def test_member_name_in_ai_phase_source_end_to_end():
    """The ai_phase GENERATOR uses ``B_MEMBER(cur.hp)``/``(max.hp)`` internally -- assert the generated+spliced
    branch carries the resolved numeric selectors (a regression guard on the generator's member-name use)."""
    out = aiauthor.apply_ai_phases(_eb_with_attack(),
                                   [{"entry": 0, "tag": 0, "stat": "hp", "below": 0.5, "then": 2, "else": 0}])
    joined = battleai.disassemble_ai(out)
    assert "B_MEMBER(36)" in joined and "B_MEMBER(35)" in joined   # cur.hp + max.hp names resolved in the splice
    assert "# B_MEMBER 36=cur.hp 35=max.hp" in joined or "36=cur.hp" in joined


# 3. ---- the `after` locator on the LAST instruction (and `at = length`) -- the f.abs_end boundary ------------
# Append-PAST-the-end is intentionally REJECTED with a redirect (you cannot insert after a function's terminator --
# splice BEFORE it). _locate_insert catches both forms up front (cleaner than letting the splice primitive emit a
# confusing "outside func body" error). To add code at the end, use before="<terminator>" (lands before the RET).
def test_ai_insert_after_last_instruction_rejected():
    eb = _eb_with_attack()
    frag = "SET({Instance.Byte[7] const(99) B_LET B_EXPR_END})"
    with pytest.raises(aiauthor.AiAuthorError, match="LAST instruction"):
        aiauthor.apply_ai_inserts(eb, [{"entry": 0, "tag": 0, "after": "RET", "source": frag}])


def test_ai_insert_at_function_length_rejected():
    eb = _eb_with_attack()
    f = EbScript.from_bytes(eb).entry(0).func_by_tag(0)
    frag = "SET({Instance.Byte[7] const(99) B_LET B_EXPR_END})"
    with pytest.raises(aiauthor.AiAuthorError, match="outside the func body"):
        aiauthor.apply_ai_inserts(eb, [{"entry": 0, "tag": 0, "at": f.length, "source": frag}])


def test_ai_insert_mid_instruction_at_rejected():
    # a mid-instruction `at` offset (inside the first 8-byte SET) must be refused, not silently corrupt the stream
    eb = _eb_with_attack()
    with pytest.raises(aiauthor.AiAuthorError, match="not an instruction boundary"):
        aiauthor.apply_ai_inserts(eb, [{"entry": 0, "tag": 0, "at": 3, "source": "RET()"}])


def test_ai_insert_before_jump_target_attack_is_valid():
    # the headline pattern: inserting before an Attack that is itself a forward-jump target must NOT be rejected as a
    # straddle (the jump lands on the fragment, which flows into the original Attack -- the boundary-correct fix).
    body = cmdasm.assemble_block(
        "SET({Instance.Byte[5] const(0) B_LET B_EXPR_END})\n"   # +1 guard so the jump target is the Attack, not start
        "JMP_IF(LATK)\n"                                         # a forward jump whose target is the Attack
        "SET({Instance.Byte[5] const(1) B_LET B_EXPR_END})\n"
        "LATK:\nAttack({Instance.Byte[5] B_EXPR_END})\nRET()")
    out = aiauthor.apply_ai_inserts(_minimal_eb(body),
                                    [{"entry": 0, "tag": 0, "before": "Attack",
                                      "source": "SET({Instance.Byte[7] const(9) B_LET B_EXPR_END})"}])
    assert not ailint.lint_ai(out)                              # spliced + still lints clean (no corruption)


# 4. ---- validate_ai_edits surfaces a BROKEN insert (existing test only covers a clean phase) -----------------
def test_validate_ai_edits_reports_broken_insert():
    """validate_ai_edits(inserts=...) must catch a bad locator and return a non-empty error list (not raise)."""
    eb = _eb_with_attack()
    probs = aiauthor.validate_ai_edits(eb, inserts=[{"entry": 0, "tag": 0, "before": "Nope", "source": "RET()"}])
    assert probs and any("no such instruction" in p for p in probs)
    # and a well-formed insert validates clean
    ok = aiauthor.validate_ai_edits(eb, inserts=[{"entry": 0, "tag": 0, "before": "Attack",
                                                  "source": "SET({Instance.Byte[7] const(1) B_LET B_EXPR_END})"}],
                                    atk_count=6)
    assert ok == []
