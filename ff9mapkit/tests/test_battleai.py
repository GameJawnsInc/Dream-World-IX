"""Phase-6a tests: the EXPRESSION vocabulary (op_binary) + the battle-AI disassembler view.

Pure where possible (synthetic byte streams); the real-donor disassembly is install-gated (skips without it)."""
from __future__ import annotations

import pytest

from ff9mapkit.eb import _exprtable as ET
from ff9mapkit.eb import disasm
from ff9mapkit.battle import battleai


# ---- the op_binary table + var decode (committed, vs EBin.cs) -----------------------------------------
def test_exprtable_key_values():
    assert ET.EXPR_OP_NAMES[82] == "B_CURHP" and ET.EXPR_OP_NAMES[83] == "B_MAXHP"
    assert ET.EXPR_OP_NAMES[110] == "B_CURMP" and ET.EXPR_OP_NAMES[122] == "B_SYSVAR"
    assert ET.EXPR_OP_NAMES[121] == "B_SYSLIST" and ET.EXPR_OP_NAMES[120] == "B_OBJSPECA"
    assert ET.EXPR_OP_NAMES[24] == "B_LT" and ET.EXPR_OP_NAMES[20] == "B_PLUS" and ET.EXPR_OP_NAMES[127] == "B_EXPR_END"
    assert ET.expr_op_name(0xAA) == "opAA"                # undefined -> raw fallback


def test_decode_var():
    # 0xC4 = Global + Bit (the kit's GLOB_BOOL story-flag read); 0xC5 = Map + Bit (the transient twin)
    assert ET.decode_var(0xC4, 8512) == "Global.Bit[8512]"
    assert ET.decode_var(0xC5, 23) == "Map.Bit[23]"
    assert ET.decode_var(0xC5 | (5 << 2), 7) == "Map.Byte[7]"   # type bits 2-4 = 5 (Byte)


# ---- pretty_expr (the named expression renderer) -----------------------------------------------------
def _px(b):
    text, pos = disasm.pretty_expr(bytes(b), 0)
    assert pos == len(b)
    return text


def test_pretty_expr_operators_and_const():
    # B_CURHP, const(50), B_LT, B_EXPR_END  -> "is my current HP < 50 ?"
    assert _px([82, 0x7D, 50, 0, 24, 0x7F]) == "{B_CURHP const(50) B_LT B_EXPR_END}"
    # a 4-byte const -- B_CONST4 prints distinctly as const4(N) (so exprasm.assemble round-trips it to 0x7E)
    assert _px([0x7E, 1, 0, 0, 0, 0x7F]) == "{const4(1) B_EXPR_END}"


def test_pretty_expr_variable_and_obj():
    assert _px([0xC4, 23, 0x7F]) == "{Global.Bit[23] B_EXPR_END}"           # a story-flag read
    assert _px([0x78, 5, 8, 0x7F]) == "{obj(uid=5).f[8] B_EXPR_END}"        # an obj/battle-char read
    assert _px([0x7A, 31, 0x7F]) == "{B_SYSVAR[31] B_EXPR_END}"             # a system var read


# ---- the AI command + function decode ----------------------------------------------------------------
def test_decode_func_pretty_names_commands():
    from ff9mapkit.eb import opcodes
    body = opcodes.init_object(1, 128) + opcodes.init_object(2, 129)
    out = list(battleai._decode_func_pretty(body, 0, len(body)))
    assert out[0][1] == "InitObject" and out[0][2] == ["1", "128"]
    assert out[1][1] == "InitObject" and out[1][2] == ["2", "129"]


def test_ctrl_overlay_names():
    assert battleai._cmd_name(0x01) == "JMP" and battleai._cmd_name(0x03) == "JMP_IF"
    assert battleai._cmd_name(0x05) == "SET" and battleai._cmd_name(0x04) == "RET"
    assert battleai._tag_role(1) == "Main" and battleai._tag_role(6) == "Counter" and battleai._tag_role(9) == "Dying"


# ---- BYTE-WALK PARITY: the named decoders must consume EXACTLY the bytes the proven decoders do ------
def test_pretty_expr_byte_parity():
    # pretty_expr must end at the same position as read_expr for every token shape (else disassembly desyncs)
    for stream in ([82, 0x7D, 50, 0, 24, 0x7F], [0xC4, 23, 0x7F], [0x78, 5, 8, 0x7F], [0x7A, 31, 0x7F],
                   [0x7E, 1, 0, 0, 0, 0x7F], [0xE4, 0, 1, 0x7F], [0x29, 4, 0x5F, 7, 0x7F]):
        b = bytes(stream)
        _t1, p1 = disasm.read_expr(b, 0)
        _t2, p2 = disasm.pretty_expr(b, 0)
        assert p1 == p2 == len(b), stream


def test_decode_func_parity_with_read_code_on_real_donor():
    # the strongest check: _decode_func_pretty must yield the SAME instruction offsets as read_code (the proven
    # decoder) for every AI function in a real donor -- proving the byte-walk (incl. every pretty_expr operand) is
    # identical, so the annotated view can never mis-align.
    try:
        from ff9mapkit.battle import extract
        eb = extract.read_scene_assets("EF_R007")["eb"]["us"]
    except Exception:                                    # noqa: BLE001 -- no install -> skip
        pytest.skip("needs the FF9 install + UnityPy")
    from ff9mapkit.eb.model import EbScript
    s = EbScript.from_bytes(eb)
    checked = 0
    for e in s.entries:
        for f in e.funcs:
            pretty_offs = [off for off, _n, _o in battleai._decode_func_pretty(s.data, f.abs_start, f.abs_end)]
            code_offs = [i.off for i in s.instrs(f)]
            assert pretty_offs == code_offs, (e.index, f.tag)
            checked += 1
    assert checked > 0


# ---- the full view on a real donor (install-gated) ---------------------------------------------------
def test_analyze_scene_real_donor():
    try:
        out = battleai.analyze_scene("EF_R007")
    except Exception:                                    # noqa: BLE001 -- no install / no UnityPy -> skip
        pytest.skip("needs the FF9 install + UnityPy to read EVT_BATTLE_EF_R007.eb")
    assert "Main_Init" in out and "Enemy type 0 AI" in out
    assert "InitObject" in out and "B_" in out           # the spawn binding + named expression operators


def test_disassemble_truncated_eb_is_legible_not_indexerror():
    # a valid-header but truncated/corrupt eb must NOT IndexError-crash -- it emits a legible note (review fix)
    try:
        from ff9mapkit.battle import extract
        eb = extract.read_scene_assets("EF_R007")["eb"]["us"]
    except Exception:                                    # noqa: BLE001 -- no install -> skip
        pytest.skip("needs the FF9 install + UnityPy")
    results = [battleai.disassemble_ai(eb[:cut]) for cut in (len(eb) - 1, len(eb) // 2, 200, 160)]
    assert all(isinstance(r, str) for r in results)      # the real contract: never IndexError-crashes
    assert any("malformed" in r for r in results)        # ... and the guard emits a legible note when it trips
