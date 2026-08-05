"""THE EXPRESSION-VALUED SetTextVariable lane -- byte oracle + the arg-flag derivation.

``SetTextVariable`` (0x66, MESVALUE) can take its VALUE operand as a runtime expression
instead of an immediate. The kit already emitted that encoding at three in-game-proven
call sites (``content/behavior.py`` the HUD live pass, ``content/numinput.py:413``,
``content/mognet.py:292``); :func:`opcodes.set_text_variable_expr` only NAMES it. These
tests pin the encoding against the engine's reader so a future refactor cannot drift:

  * ``EventEngine.DoEventCode.cs:43`` reads ``gArgFlag`` unconditionally, right after the
    opcode byte and before any operand.
  * ``MESVALUE`` (DoEventCode.cs:520-527) reads arg0 with ``getv1`` and arg1 with
    ``getv2``; each (EventEngine.cs:1331-1345 / :1347-1362) tests ``gArgFlag & 1`` and
    then SHIFTS RIGHT. So the flag bit index is the OPERAND index, consumed left to
    right: bit0 -> slot, bit1 -> value. **0b10, not 0b01.**
  * A clear bit on arg1 is a SIGN-EXTENDED Int16 (``(geti() | geti()<<8) << 16 >> 16``)
    -- the +/-32767 cap the expression form exists to escape.

Every assertion here is pure logic: no templates, no game install, NEVER skips.
"""

from __future__ import annotations

import pytest

from ff9mapkit.eb import exprasm, opcodes
from ff9mapkit.eb._exprtable import VAR_SOURCE, VAR_TYPE
from ff9mapkit.eb.disasm import pretty_expr

# The rung-0 completion-journal probe's seven reads, as (tokens, expr bytes, full
# instruction). These byte strings were derived from the engine source and confirmed
# against the built .eb of studies/completion-journal/bench/journal_probe.field.toml.
PROBE_READS = [
    # slot, tokens, expr bytes, instruction bytes
    (0, "Null.SBit[5]",
     "c3 05 7f", "66 02 00 c3 05 7f"),
    (1, "Global.UInt16[0]",
     "dc 00 7f", "66 02 01 dc 00 7f"),
    (2, "Global.Int24[187]",
     "c8 bb 7f", "66 02 02 c8 bb 7f"),
    (3, "Global.Int24[187] const4(16777215) B_AND",
     "c8 bb 7e ff ff ff 00 24 7f", "66 02 03 c8 bb 7e ff ff ff 00 24 7f"),
    (4, "const(256) B_HAVE_ITEM",
     "7d 00 01 64 7f", "66 02 04 7d 00 01 64 7f"),
    (5, "const(0) const(6) const(0) flex(16,3)",
     "7d 00 00 7d 06 00 7d 00 00 d3 10 00 03 7f",
     "66 02 05 7d 00 00 7d 06 00 7d 00 00 d3 10 00 03 7f"),
    (6, "Global.UInt16[0] const(1000) B_DIV Global.UInt16[0] const(1000) B_DIV "
        "const(0) B_GE B_MULT",
     "dc 00 7d e8 03 12 dc 00 7d e8 03 12 7d 00 00 1b 11 7f",
     "66 02 06 dc 00 7d e8 03 12 dc 00 7d e8 03 12 7d 00 00 1b 11 7f"),
]


@pytest.mark.parametrize("slot,tokens,expr_hex,instr_hex", PROBE_READS,
                         ids=[r[1].split()[0] + f"@{r[0]}" for r in PROBE_READS])
def test_probe_read_bytes(slot, tokens, expr_hex, instr_hex):
    """Token string -> expression bytes -> full instruction, byte-exact, and the
    disassembler decodes the blob back to the SAME tokens (the round trip is the
    identity, so a wrong encoding cannot hide behind a matching decode)."""
    expr = exprasm.assemble(tokens + " B_EXPR_END")
    assert expr.hex(" ") == expr_hex
    instr = opcodes.set_text_variable_expr(slot, expr)
    assert instr.hex(" ") == instr_hex
    assert pretty_expr(expr, 0)[0] == "{" + tokens + " B_EXPR_END}"


def test_argflag_bit_is_the_value_operand_not_the_slot():
    """THE ONE ASSERTION THE WHOLE LANE RESTS ON.

    getv1/getv2 shift ``gArgFlag`` right after each operand, so the bit INDEX is the
    OPERAND index. Value-as-expression is therefore bit1 (0b10). If it were emitted as
    0b01 the engine would CalcExpr the SLOT (reading the expression bytes as an
    expression for arg0), then read the remaining bytes as a 2-byte immediate value --
    a garbage slot and a garbage value, with no crash to point at it.

    Break-it check: replacing ``0b10`` with ``0b01`` in ``set_text_variable_expr`` makes
    this assert fail on the flag byte (``01`` != ``02``) AND makes the byte-oracle test
    above fail on all seven rows. Verified by deliberately flipping it."""
    expr = exprasm.assemble("Null.SBit[5] B_EXPR_END")
    instr = opcodes.set_text_variable_expr(3, expr)
    assert instr[0] == 0x66                    # opcode
    assert instr[1] == 0b10, ("argFlag must set bit1 (the VALUE operand), not bit0 (the "
                              "SLOT) -- getv1 consumes bit0 then shifts")
    assert instr[2] == 3                       # arg0 stays an IMMEDIATE slot byte
    assert instr[3:] == expr                   # arg1 is the raw token blob


def test_immediate_form_is_byte_identical_and_untouched():
    """The new lane is ADDITIVE. The immediate helper still emits ``66 00 <slot> <u16>``
    -- the real-field-verified field-407 chest form ``66 00 00 ec 00``."""
    assert opcodes.set_text_variable(0, 236).hex(" ") == "66 00 00 ec 00"
    assert opcodes.set_text_variable(7, 65535).hex(" ") == "66 00 07 ff ff"
    # ... and the two forms differ ONLY in the argFlag byte + the operand encoding
    assert opcodes.set_text_variable(0, 236)[1] == 0x00


def test_unterminated_expression_is_refused():
    """CalcExpr walks to the 0x7F terminator; an unterminated blob runs off into the
    next instruction's bytes. Refuse at the encoder, not in-game."""
    with pytest.raises(ValueError, match="B_EXPR_END"):
        opcodes.set_text_variable_expr(0, bytes([0xC3, 0x05]))
    with pytest.raises(ValueError, match="B_EXPR_END"):
        opcodes.set_text_variable_expr(0, b"")


# --------------------------------------------------------------------- var packing
def _engine_get_var_operation(src: int, typ: int, index: int) -> int:
    """EBin.getVarOperation, EBin.cs:511-519, transcribed:

        varOperation = (index << 8) | ((Int32)varType << 2) | ((Int32)varSrc) | 0xC0;
        if (index > 0xFF) varOperation |= 0x20;
    """
    op = (index << 8) | (typ << 2) | src | 0xC0
    if index > 0xFF:
        op |= 0x20
    return op


def _engine_wire_bytes(var_operation: int) -> bytes:
    """The bytes ``expr_varSpec`` (EBin.cs:464-478) consumes for that varOperation:
    the token byte, then a 1-byte index, or -- when bit 0x20 is set -- a LOW byte then a
    HIGH byte (the second is ``<<= 8``)."""
    token = var_operation & 0xFF
    index = var_operation >> 8
    if token & 0x20:
        return bytes((token, index & 0xFF, (index >> 8) & 0xFF))
    return bytes((token, index & 0xFF))


@pytest.mark.parametrize("src_name,src", sorted(
    ((n, v) for v, n in VAR_SOURCE.items() if v <= 3), key=lambda t: t[1]))
@pytest.mark.parametrize("typ_name,typ", sorted(
    ((n, v) for v, n in VAR_TYPE.items()), key=lambda t: t[1]))
@pytest.mark.parametrize("index", [0, 1, 5, 187, 254, 255, 256, 1000, 8712, 0xFFFF])
def test_var_token_matches_engine_getvaroperation(src_name, src, typ_name, typ, index):
    """The kit's 0xC0 var packing (eb/exprasm.py) recomputed independently from
    EBin.getVarOperation + expr_varSpec. This is the assertion that would have caught a
    wrong ``C3`` for ``Null.SBit[5]``: get the type/source shift wrong and the engine
    reads a different variable class entirely, silently returning 0 (EBin.cs:1672)."""
    if (src, typ, index <= 0xFF) == (3, 4, True):
        pytest.skip("Null.SByte[<=255] packs to 0xD3, which Memoria STEALS for "
                    "flexible_varfunc -- see the dedicated test below")
    got = exprasm.assemble(f"{src_name}.{typ_name}[{index}] B_EXPR_END")[:-1]
    assert got == _engine_wire_bytes(_engine_get_var_operation(src, typ, index))


def test_null_sbyte_short_index_is_the_stolen_0xd3_token():
    """A HOLE IN THE VAR-TOKEN SPACE, found by the sweep above.

    ``getVarOperation(Null, SByte, i)`` packs to 0xC0 | (4 << 2) | 3 = **0xD3** for a
    short index -- and ``EBin.expr`` (EBin.cs:330-333) tests ``varOperation == 0xD3``
    BEFORE falling through to ``expr_varSpec``, so Memoria's flexible_varfunc
    sub-command has taken that encoding. Emitting it would make the engine read the
    following bytes as ``u16 id + u8 argc`` and pop that many CalcStack operands --
    silent garbage, no crash.

    The kit already refuses it: ``exprasm.assemble`` re-parses its own output and the
    stream desyncs. Pinned here so the refusal stays a checked property rather than an
    accident of the round-trip guard."""
    assert _engine_get_var_operation(3, 4, 5) & 0xFF == 0xD3
    with pytest.raises(exprasm.AssembleError):
        exprasm.assemble("Null.SByte[5] B_EXPR_END")
    # the LONG-index form is 0xD3 | 0x20 = 0xF3 and is unaffected
    assert exprasm.assemble("Null.SByte[256] B_EXPR_END")[0] == 0xF3


def test_treasure_hunter_points_token_is_c3_05():
    """Spelled out, because this read has ZERO precedent in the kit and one wrong nibble
    is a silent 0. ``Null`` = VariableSource 3, ``SBit`` = VariableType 0 (the kit's
    VAR_TYPE names index 0 "SBit"; ``Null.Any[5]`` does not assemble), index 5 ->
    0xC0 | (0 << 2) | 3 = 0xC3, then a 1-byte index 0x05. The engine's Null arm
    (EBin.cs:1634-1638) routes VariableType.Any to
    GetMemoriaCustomVariable((memoria_variable)(t0 & 0xFFFF)), and
    memoria_variable.TREASURE_HUNTER_POINTS is enum index 5 (EBin.cs:2416-2431)."""
    assert exprasm.assemble("Null.SBit[5] B_EXPR_END") == bytes((0xC3, 0x05, 0x7F))
    assert _engine_get_var_operation(3, 0, 5) & 0xFF == 0xC3


def test_expression_ceiling_is_26_bit_signed_not_int32():
    """DOCUMENTED CEILING, pinned so the number cannot drift apart from the behavior
    tables that already carry it. A COMPUTED intermediate goes through
    ``EBin.expr_Push_v0_Int24`` (EBin.cs:1270-1274), which ORs the Int26 class tag
    (7 << 26) into ``_v0`` with NO mask, and is read back as ``(t0 << 6) >> 6``
    (EBin.cs:1682-1684) -- so overflow does not truncate, it lands in the
    VariableSource field and the entry is re-read as a different variable class."""
    from ff9mapkit.content.behavior import TABLE_VALUE_MAX, TABLE_VALUE_MIN
    assert opcodes.EXPR_VALUE_MAX == (1 << 25) - 1 == 33_554_431
    assert opcodes.EXPR_VALUE_MIN == -(1 << 25)
    assert (opcodes.EXPR_VALUE_MIN, opcodes.EXPR_VALUE_MAX) == (TABLE_VALUE_MIN,
                                                                TABLE_VALUE_MAX)
