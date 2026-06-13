"""Phase-6c-ii tests: the `.eb` COMMAND ASSEMBLER (the inverse of disasm.read_code).

The load-bearing proof is the round trip against a REAL donor: every instruction (and every whole function) of a
shipping enemy AI must assemble back to its exact bytes. Synthetic tests cover the encodings, jump-label
resolution, and the error paths; the real-donor round trips are install-gated (skip without it)."""
from __future__ import annotations

import pytest

from ff9mapkit.eb import cmdasm, disasm, exprasm
from ff9mapkit.eb.cmdasm import assemble_instruction, assemble_block, CmdAsmError


# ---- per-instruction encodings (the inverse of each read_code branch) --------------------------------
def test_basic_encodings():
    assert assemble_instruction("RET", []) == bytes((0x04,))
    assert assemble_instruction("JMP", [10]) == bytes((0x01, 10, 0))          # op + signed-int16 LE offset
    assert assemble_instruction("JMP_IF", [5]) == bytes((0x03, 5, 0))
    # SET (0x05) -- forced-expr, NO argFlag byte on the wire: just 0x05 + the expression bytes
    expr = "{B_CURHP const(1) B_LT B_EXPR_END}"
    assert assemble_instruction("SET", [expr]) == bytes((0x05,)) + exprasm.assemble(expr)


def test_matches_real_encoder_and_redecodes():
    # ties to the kit's own encoder for a multi-immediate op, and round-trips through the disassembler
    from ff9mapkit.eb import opcodes
    assert assemble_instruction("InitObject", [1, 128]) == opcodes.init_object(1, 128)
    b = assemble_instruction("InitObject", [1, 128])
    ins, _ = disasm.read_code(b, 0)
    assert disasm.op_name(ins.op) == "InitObject" and ins.args == [1, 128]     # (the high-op argFlag path is
    #                                                                            covered by the donor round trip)


# ---- block assembly + jump-label resolution ----------------------------------------------------------
def test_block_forward_label():
    block = "JMP_IF(end)\nSET({B_CURHP const(1) B_LT B_EXPR_END})\nend:\nRET()"
    b = assemble_block(block)
    instrs = list(disasm.iter_code(b, 0, len(b)))
    assert instrs[0].op == 0x03                                                # JMP_IF
    assert instrs[0].end + instrs[0].imm(0) == instrs[-1].off                  # resolves to the RET (the label)


def test_block_backward_label():
    block = "loop:\nSET({B_CURHP const(1) B_LT B_EXPR_END})\nJMP(loop)"
    b = assemble_block(block)
    jmp = list(disasm.iter_code(b, 0, len(b)))[-1]
    raw = jmp.imm(0)
    signed = raw - 0x10000 if raw >= 0x8000 else raw                          # int16
    assert jmp.end + signed == 0                                              # jumps back to loop: (offset 0)


def test_block_ignores_blank_and_comment_lines():
    b = assemble_block("# a branch\n\nRET()  # done\n")
    assert b == bytes((0x04,))


def test_jmp_ifnot_forward_ok_but_backward_rejected():
    # review fix: the engine reads JMP_IFNOT (0x02, beq) offset UNSIGNED -- a FORWARD skip is fine, but a BACKWARD
    # target would execute as a ~64KB forward jump (crash). JMP (0x01) / JMP_IF (0x03) are signed (unaffected).
    fwd = assemble_block("JMP_IFNOT(end)\nSET({B_CURHP const(1) B_LT B_EXPR_END})\nend:\nRET()")
    j = list(disasm.iter_code(fwd, 0, len(fwd)))[0]
    assert j.op == 0x02 and j.end + j.imm(0) == list(disasm.iter_code(fwd, 0, len(fwd)))[-1].off
    with pytest.raises(CmdAsmError, match="BACKWARD"):
        assemble_block("loop:\nSET({B_CURHP const(1) B_LT B_EXPR_END})\nJMP_IFNOT(loop)")


def test_unbalanced_bracket_rejected():
    with pytest.raises(CmdAsmError, match="unbalanced"):
        assemble_block("JMP_IF(a], b)\nRET()")


# ---- error paths -------------------------------------------------------------------------------------
def test_unknown_mnemonic():
    with pytest.raises(CmdAsmError, match="unknown command mnemonic"):
        assemble_instruction("FLARGLE", [])


def test_set_requires_one_expr():
    with pytest.raises(CmdAsmError, match="SET"):
        assemble_instruction("SET", [5])                                      # an immediate, not a { } expr


def test_wrong_operand_count():
    with pytest.raises(CmdAsmError, match="operand"):
        assemble_instruction("JMP", [])                                       # JMP takes 1


def test_undefined_label():
    with pytest.raises(CmdAsmError, match="undefined label"):
        assemble_block("JMP(nowhere)\nRET()")


def test_duplicate_label():
    with pytest.raises(CmdAsmError, match="duplicate label"):
        assemble_block("a:\na:\nRET()")


def test_label_jump_outside_block_errors():
    with pytest.raises(CmdAsmError, match="outside assemble_block"):
        assemble_instruction("JMP", ["somelabel"])


def test_empty_block():
    with pytest.raises(CmdAsmError, match="empty block"):
        assemble_block("# only a comment\n")


# ---- REAL-DONOR round trip: every instruction of a shipping enemy AI must assemble to its exact bytes -
def _donor_eb():
    from ff9mapkit.battle import battleai
    from ff9mapkit.eb.model import EbScript
    return EbScript.from_bytes(battleai._scene_eb("EF_R007"))


def test_roundtrip_real_donor_per_instruction():
    # the strongest check: walk EF_R007's AI with the production decoder; assemble each decoded instruction and
    # assert it reproduces the original instruction bytes byte-for-byte (covers BTLCMD, SET, jumps, RET, every op
    # the AI actually uses + every argFlag/variable-count shape).
    try:
        from ff9mapkit.battle import battleai
        eb = _donor_eb()
    except Exception:                                       # noqa: BLE001 -- no install / no UnityPy -> skip
        pytest.skip("needs the FF9 install + UnityPy")
    checked = 0
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            decoded = list(battleai._decode_func_pretty(eb.data, f.abs_start, f.abs_end))
            bounds = [d[0] for d in decoded] + [f.abs_end]
            for i, (off, mnem, operands) in enumerate(decoded):
                raw_instr = bytes(eb.data[off:bounds[i + 1]])
                got = assemble_instruction(mnem, operands)
                assert got == raw_instr, (e.index, f.tag, off, mnem, operands, got.hex(), raw_instr.hex())
                checked += 1
    assert checked > 0


def test_roundtrip_real_donor_per_function_block():
    # the whole-block direction: render each AI function as a block of `Mnemonic(operands)` lines and assert
    # assemble_block reproduces the function's body bytes (jumps stay numeric -> byte-faithful, no labels needed).
    try:
        from ff9mapkit.battle import battleai
        eb = _donor_eb()
    except Exception:                                       # noqa: BLE001
        pytest.skip("needs the FF9 install + UnityPy")
    checked = 0
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            decoded = list(battleai._decode_func_pretty(eb.data, f.abs_start, f.abs_end))
            if not decoded:
                continue
            block = "\n".join(f"{mnem}({', '.join(operands)})" for _off, mnem, operands in decoded)
            body = bytes(eb.data[f.abs_start:f.abs_end])
            assert assemble_block(block) == body, (e.index, f.tag)
            checked += 1
    assert checked > 0
