"""Phase-6c-i tests: the `.eb` EXPRESSION ASSEMBLER (the inverse of disasm.pretty_expr).

The load-bearing property is the ROUND TRIP: assemble(pretty_expr(bytes)) == bytes (byte-exact) and
pretty_expr(assemble(text)) == text. Pure where possible (a synthetic battery of every token shape); the
real-donor byte-identity round trip is install-gated (skips without it)."""
from __future__ import annotations

import pytest

from ff9mapkit.eb import disasm
from ff9mapkit.eb import exprasm
from ff9mapkit.eb.exprasm import assemble, AssembleError


# ---- per-token encoding (the inverse of each pretty_expr branch) -------------------------------------
def test_assemble_token_shapes():
    assert assemble("{B_CURHP const(50) B_LT B_EXPR_END}") == bytes((82, 0x7D, 50, 0, 24, 0x7F))
    assert assemble("{const4(1) B_EXPR_END}") == bytes((0x7E, 1, 0, 0, 0, 0x7F))
    assert assemble("{Global.Bit[23] B_EXPR_END}") == bytes((0xC4, 23, 0x7F))      # a story-flag read
    assert assemble("{obj(uid=5).f[8] B_EXPR_END}") == bytes((0x78, 5, 8, 0x7F))   # an obj/battle-char read
    assert assemble("{B_SYSVAR[31] B_EXPR_END}") == bytes((0x7A, 31, 0x7F))
    assert assemble("{B_SYSLIST[3] B_EXPR_END}") == bytes((0x79, 3, 0x7F))
    assert assemble("{B_MEMBER(4) B_PTR(7) B_EXPR_END}") == bytes((0x29, 4, 0x5F, 7, 0x7F))
    # a long-index variable (index > 255 -> the 0x20 bit + a 2-byte LE index), e.g. a high story flag
    assert assemble("{Global.Bit[8512] B_EXPR_END}") == bytes((0xC4 | 0x20, 0x40, 0x21, 0x7F))


def test_const_vs_const4_distinct():
    # the disambiguation that makes the round trip EXACT: const(N) -> 2-byte B_CONST, const4(N) -> 4-byte B_CONST4
    assert assemble("{const(1) B_EXPR_END}") == bytes((0x7D, 1, 0, 0x7F))
    assert assemble("{const4(1) B_EXPR_END}") == bytes((0x7E, 1, 0, 0, 0, 0x7F))


def test_accepts_token_list_and_bare_braces():
    assert assemble(["B_CURHP", "const(50)", "B_LT", "B_EXPR_END"]) == bytes((82, 0x7D, 50, 0, 24, 0x7F))
    assert assemble("B_CURHP const(50) B_LT B_EXPR_END") == bytes((82, 0x7D, 50, 0, 24, 0x7F))   # braces optional


# ---- the ROUND TRIP -- the core correctness proof ----------------------------------------------------
# every token shape (operator, 2- & 4-byte const, short & long var, obj, sysvar/syslist, member/ptr)
_BATTERY = [
    [82, 0x7D, 50, 0, 24, 0x7F],          # B_CURHP const(50) B_LT
    [0x7E, 0xFF, 0xFF, 0x3F, 0, 0x7F],    # a 4-byte const4 literal
    [0xC4, 23, 0x7F],                     # Global.Bit[23] (short index)
    [0xC4 | 0x20, 0x40, 0x21, 0x7F],      # Global.Bit[8512] (long index)
    [0x78, 5, 8, 0x7F],                   # obj(uid=5).f[8]
    [0x7A, 31, 0x7F], [0x79, 3, 0x7F],    # B_SYSVAR / B_SYSLIST
    [0x29, 4, 0x5F, 7, 0x7F],             # B_MEMBER / B_PTR
    [83, 0x7D, 0, 0, 25, 0x7D, 100, 0, 36, 0x7F],   # a compound: B_MAXHP const(0) B_GT const(100) B_AND
    [0x72, 0x7F],                         # an UNNAMED operator byte (-> "op72") must still round-trip
]


@pytest.mark.parametrize("stream", _BATTERY)
def test_roundtrip_byte_identity(stream):
    b = bytes(stream)
    text, pos = disasm.pretty_expr(b, 0)
    assert pos == len(b)
    assert assemble(text) == b, text                      # assemble(pretty_expr(b)) == b


# ---- 0xD3 flexible_varfunc (Memoria): computed array indexing over gScriptVector ---------------------
def test_vector_token_shapes():
    # the trio at canonical arity: 0xD3 + u16 id + u8 argc (args are RPN operands BEFORE the token)
    assert assemble("{const(7) const(3) B_VECTOR B_EXPR_END}") \
        == bytes((0x7D, 7, 0, 0x7D, 3, 0, 0xD3, 20, 0, 2, 0x7F))
    assert assemble("{const(7) B_VECTOR_SIZE B_EXPR_END}") == bytes((0x7D, 7, 0, 0xD3, 21, 0, 1, 0x7F))
    assert assemble("{const(7) const(9) B_DICTIONARY B_EXPR_END}") \
        == bytes((0x7D, 7, 0, 0x7D, 9, 0, 0xD3, 22, 0, 2, 0x7F))
    # the generic escape hatch for every other flexible_varfunc id
    assert assemble("{const(240) flex(11,1) B_EXPR_END}") == bytes((0x7D, 240, 0, 0xD3, 11, 0, 1, 0x7F))
    # a VECTOR WRITE is the ordinary lvalue shape: token then value then B_LET (index==size
    # appends; a missing id at index 0 creates -- both engine-side, fail-soft)
    write = assemble("{const(7) const(0) B_VECTOR const(42) B_LET B_EXPR_END}")
    assert bytes((0xD3, 20, 0, 2)) in write and write[-1] == 0x7F


@pytest.mark.parametrize("stream", [
    [0x7D, 7, 0, 0x7D, 3, 0, 0xD3, 20, 0, 2, 0x7F],           # B_VECTOR read
    [0x7D, 7, 0, 0xD3, 21, 0, 1, 0x7F],                       # B_VECTOR_SIZE
    [0x7D, 7, 0, 0x7D, 9, 0, 0xD3, 22, 0, 2, 0x7F],           # B_DICTIONARY
    [0x7D, 240, 0, 0xD3, 11, 0, 1, 0x7F],                     # flex(11,1) (ITEM_FULL_COUNT id)
    [0xD3, 20, 0, 3, 0x7F],                                   # non-canonical arity -> flex(20,3)
])
def test_vector_roundtrip_byte_identity(stream):
    b = bytes(stream)
    text, pos = disasm.pretty_expr(b, 0)
    assert pos == len(b)
    assert assemble(text) == b, text
    # the sugar names appear only at canonical arity
    if stream[:4] == [0xD3, 20, 0, 3]:
        assert "flex(20,3)" in text and "B_VECTOR" not in text


def test_vector_does_not_desync_the_offset_walkers():
    """0xD3 >= 0xC0 -- before the carve-out every kit walker read it as a 1-byte-operand
    var token and desynced by 2. Prove all four walkers now stay in step: a const and
    an obj-uid AFTER the 0xD3 token must be found at their true offsets."""
    b = assemble("{const(7) const(3) B_VECTOR obj(uid=5).f[8] B_PLUS const(99) B_MINUS B_EXPR_END}")
    # read_expr consumes to the exact end
    _raw, pos = disasm.read_expr(b, 0)
    assert pos == len(b)
    # the uid walker finds obj(uid=5)'s uid byte (right after the 0x78 token byte)
    pos2, uids = disasm._expr_uid_offsets(b, 0)
    assert pos2 == len(b) and len(uids) == 1 and b[uids[0]] == 5
    # the const walker finds all three B_CONST literals at true payload offsets
    consts: list = []
    end = disasm._expr_const_offsets(b, 0, 0, consts)
    assert end == len(b)
    assert [v for _off, v, _i in consts] == [7, 3, 99]
    for off, v, _i in consts:
        assert b[off] | (b[off + 1] << 8) == v


@pytest.mark.parametrize("stream", _BATTERY)
def test_roundtrip_text_identity(stream):
    b = bytes(stream)
    text, _ = disasm.pretty_expr(b, 0)
    text2, _ = disasm.pretty_expr(assemble(text), 0)
    assert text2 == text                                  # pretty_expr(assemble(text)) == text


# ---- error handling ----------------------------------------------------------------------------------
def test_must_end_with_expr_end():
    with pytest.raises(AssembleError, match="B_EXPR_END"):
        assemble("{B_CURHP const(50) B_LT}")


def test_unknown_token():
    with pytest.raises(AssembleError, match="unknown expression token"):
        assemble("{B_CURHP FLARGLE B_EXPR_END}")


def test_empty():
    with pytest.raises(AssembleError, match="empty"):
        assemble("{}")


def test_bare_operand_op_rejected():
    # a bare operand-op would drop its operand byte(s) and desync the stream -> must be written in operand form
    with pytest.raises(AssembleError, match="takes an operand"):
        assemble("{B_CONST B_EXPR_END}")
    with pytest.raises(AssembleError, match="takes an operand"):
        assemble("{B_SYSVAR B_EXPR_END}")


def test_var_source_must_be_0_to_3():
    # Object/System/Member/Int26 are NOT 0xC0 vars -- they have their own tokens; reject the Source.Type form
    with pytest.raises(AssembleError, match="0xC0 vars"):
        assemble("{Object.Bit[1] B_EXPR_END}")


def test_var_unknown_source_type():
    with pytest.raises(AssembleError, match="unknown variable"):
        assemble("{Glob.Bitt[1] B_EXPR_END}")


def test_out_of_range():
    with pytest.raises(AssembleError, match="index out of range"):
        assemble("{Global.Bit[70000] B_EXPR_END}")        # > 0xFFFF
    with pytest.raises(AssembleError, match="out of range"):
        assemble("{B_SYSVAR[300] B_EXPR_END}")            # > 0xFF


def test_const_range_checked():
    # review fix: const/const4 RANGE-CHECK (honoring assemble_token's docstring + matching the var/sysvar siblings
    # + the 6b B_CONST4 cap precedent), instead of silently masking a typo'd literal
    with pytest.raises(AssembleError, match="16-bit range"):
        assemble("{const(70000) B_EXPR_END}")
    with pytest.raises(AssembleError, match="32-bit range"):
        assemble("{const4(99999999999) B_EXPR_END}")
    # in-range negatives ARE accepted (the engine reads B_CONST as a signed Int16) and mask to the byte form
    assert assemble("{const(-1) B_EXPR_END}") == bytes((0x7D, 0xFF, 0xFF, 0x7F))


def test_opxx_sweep_rejects_named_and_var_bytes():
    # review HIGH fix: the opXX back-door must accept ONLY the bytes pretty_expr actually emits as opXX (an
    # UNNAMED, pure operator < 0xC0). A NAMED op (incl. the operand-bearing const/var/sys/member ops) or a 0xC0
    # variable byte assembled bare would DROP its operand and desync the stream -> the engine mis-executes.
    from ff9mapkit.eb._exprtable import EXPR_OP_NAMES
    accepted = 0
    for byte in range(256):
        expr = f"{{op{byte:02X} B_EXPR_END}}"
        if byte in EXPR_OP_NAMES or byte >= 0xC0:
            with pytest.raises(AssembleError):
                assemble(expr)
        else:                                              # a genuinely-unnamed operator byte -> accepted + round-trips
            b = assemble(expr)
            assert b == bytes((byte, 0x7F))
            text, _ = disasm.pretty_expr(b, 0)
            assert assemble(text) == b
            accepted += 1
    assert accepted == 70                                  # 0x72-0x77 (6) + 0x80-0xBF (64) -- the unnamed pure ops


def test_named_and_operand_opxx_rejected():
    with pytest.raises(AssembleError, match="write it by name"):
        assemble("{op14 B_EXPR_END}")                     # 0x14 = B_PLUS -> use the name
    with pytest.raises(AssembleError, match="write it by name"):
        assemble("{op7D B_EXPR_END}")                     # 0x7D = B_CONST (operand-bearing) -- the HIGH back-door
    with pytest.raises(AssembleError, match="variable token"):
        assemble("{opC4 B_EXPR_END}")                     # 0xC4 = a Global.Bit var token


def test_mid_stream_expr_end_rejected():
    # review fix: assemble() self-verifies the round trip -> a mid-stream B_EXPR_END (which the engine stops at,
    # leaving trailing bytes unread) is caught at the library boundary, not silently emitted
    with pytest.raises(AssembleError, match="LAST token"):
        assemble(["B_CURHP", "B_EXPR_END", "B_LT", "B_EXPR_END"])


# ---- REAL-DONOR byte identity: assemble must reproduce the game's own AI expression bytes exactly ----
def test_roundtrip_real_donor_byte_identity(monkeypatch):
    # The strongest check. Walk a real scene's AI via the production disassembler, and SPY on every pretty_expr
    # call to capture each real expression's (raw, span, text). Then assert assemble(text) == raw[span] for every
    # one -- i.e. the assembler reproduces the shipping game's AI expression bytes byte-for-byte. Reuses the exact
    # production walk (no duplicated decode), so it can't drift from how the engine reads them.
    try:
        from ff9mapkit.battle import battleai
        eb = battleai._scene_eb("EF_R007")
    except Exception:                                     # noqa: BLE001 -- no install / no UnityPy -> skip
        pytest.skip("needs the FF9 install + UnityPy")

    seen = []
    orig = disasm.pretty_expr

    def spy(raw, pos):
        text, npos = orig(raw, pos)
        seen.append((bytes(raw[pos:npos]), text))
        return text, npos

    monkeypatch.setattr(disasm, "pretty_expr", spy)
    from ff9mapkit.battle import battleai
    battleai.disassemble_ai(eb)                            # drives _decode_func_pretty -> pretty_expr on every expr
    monkeypatch.undo()                                     # restore the REAL pretty_expr BEFORE asserting: assemble()
                                                           # self-verifies via pretty_expr, and the spy mutates `seen`

    assert seen, "the donor AI had no expressions to round-trip"
    for raw_span, text in seen:
        assert assemble(text) == raw_span, text           # byte-identity vs the real game's bytes
