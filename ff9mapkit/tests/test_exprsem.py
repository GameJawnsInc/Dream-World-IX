"""THE EXPRESSION SEMANTICS TABLE -- exhaustive operator classification + the RPN stack walker.

Two findings live here.

FINDING 3 -- the write-op gate was derived by NAME PATTERN (``"_LET" in n`` or a
``B_POST_``/``B_PRE_`` prefix). That catches assignment and misses ``B_PARTYADD``, which
recruits a party member through the expression under a name matching neither. The fix is not
a longer pattern, it is an EXHAUSTIVE classification plus the test below, which asserts the
classification covers ``EXPR_OP_NAMES`` completely -- so an operator added to the table in a
future round FAILS THIS TEST rather than defaulting to "read-only, safe".

FINDING 4 -- ``exprasm.assemble`` was being called "the validator". It is a token-to-byte
encoder: no arity, no stack balance, nothing. Every malformed stream below encodes cleanly.
``exprsem.analyze`` walks the stream with each operator's TRUE arity, derived from the
operator's own implementation in the Memoria C# (each entry in ``OP_SEMANTICS`` cites its
file:line).
"""

from __future__ import annotations

import pytest

from ff9mapkit.eb import exprsem as S
from ff9mapkit.eb._exprtable import EXPR_OP_NAMES
from ff9mapkit.eb.exprasm import assemble


# ------------------------------------------------------------------ FINDING 3: coverage
def test_every_operator_in_the_table_is_classified():
    """THE ANTI-PATTERN-DRIFT GATE. Not "most ops are covered" -- ALL of them, both ways."""
    named = set(EXPR_OP_NAMES.values())
    assert named - set(S.OP_SEMANTICS) == set(), "unclassified op_binary mnemonic(s)"
    assert set(S.OP_SEMANTICS) - named == set(), "classified a name that is not an operator"
    assert len(S.OP_SEMANTICS) == len(EXPR_OP_NAMES)


def test_every_classification_is_a_declared_effect_and_a_plausible_arity():
    for name, (arity, effect) in S.OP_SEMANTICS.items():
        assert effect in S.EFFECTS, f"{name}: unknown effect {effect!r}"
        assert 0 <= arity <= 3, f"{name}: arity {arity} out of the engine's 0..3 range"


def test_the_write_set_is_exactly_the_engine_operators_that_assign():
    """35, not the name pattern's 34: ``partyadd()`` (EBin.cs:1209-1215) is a write with no
    ``_LET`` in its name."""
    pattern = {n for n in EXPR_OP_NAMES.values()
               if "_LET" in n or n.startswith(("B_POST_", "B_PRE_"))}
    assert len(pattern) == 34
    assert S.WRITE_OPS - pattern == {"B_PARTYADD"}
    assert pattern - S.WRITE_OPS == set()
    assert len(S.WRITE_OPS) == 35


def test_the_impure_set_names_the_two_non_assigning_mutators():
    assert S.IMPURE_OPS == {"B_KEYON", "B_SELECT"}
    assert S.UNSAFE_TO_REPEAT == S.WRITE_OPS | S.IMPURE_OPS


def test_B_SYSVAR_impurity_is_per_index():
    """``B_SYSVAR`` itself is a pure push; its OPERAND picks the reader, and two of the 32
    are not pure (GetSysvar.cs:13-14 rolls the RNG, :31-32 writes ETb.sChoose)."""
    assert S.token_sem("B_SYSVAR[6]").effect == S.READ       # gil
    assert S.token_sem("B_SYSVAR[17]").effect == S.READ      # timer
    assert S.token_sem("B_SYSVAR[0]").effect == S.IMPURE
    assert S.token_sem("B_SYSVAR[9]").effect == S.IMPURE


# ------------------------------------------------------------------ operand-token arities
@pytest.mark.parametrize("tok,pops", [
    ("const(5)", 0), ("const4(70000)", 0), ("Global.Bit[8712]", 0), ("Null.SBit[5]", 0),
    ("B_SYSVAR[6]", 0), ("B_SYSLIST[3]", 0), ("obj(uid=5).f[8]", 0),
    ("B_MEMBER(cur.hp)", 0), ("B_PTR(7)", 0),
    ("B_VECTOR", 2), ("B_VECTOR_SIZE", 1), ("B_DICTIONARY", 2),
    ("flex(16,3)", 3), ("flex(11,1)", 1), ("flex(999,0)", 0),
])
def test_operand_token_arities(tok, pops):
    """``flex``'s arity RIDES THE WIRE (``u16 id + u8 argc``, EBin.cs:351-359), so no
    per-function table is needed or trusted -- including for an id the engine does not
    define, which still pops argc and pushes one."""
    sem = S.token_sem(tok)
    assert (sem.pops, sem.pushes, sem.effect) == (pops, 1, S.READ)


def test_B_EXPR_END_pushes_nothing():
    assert S.token_sem("B_EXPR_END").pushes == 0


def test_an_unnamed_raw_operator_byte_is_refused_not_guessed():
    with pytest.raises(S.ExprSemanticError, match="no known arity"):
        S.token_sem("op6E")


# ------------------------------------------------------------------ FINDING 4: the walker
GOOD = [
    "Null.SBit[5] B_EXPR_END",
    "Global.UInt16[0] B_EXPR_END",
    "Global.Int24[187] const4(16777215) B_AND B_EXPR_END",
    "const(256) B_HAVE_ITEM B_EXPR_END",
    "const(0) const(6) const(0) flex(16,3) B_EXPR_END",
    # B_CURHP is UNARY -- it pops a party-slot index (DoCalcOperationExt.cs:67-69, and
    # content/region.py:88-93 documents the same thing independently). The bare
    # `B_CURHP const(50) B_LT` spelling in test_exprasm.py is an ENCODING fixture, not a
    # valid stream, and this walker is what tells the two apart.
    "const(0) B_CURHP const(50) B_LT B_EXPR_END",
    "const(7) const(3) B_VECTOR B_EXPR_END",
    "const(7) B_VECTOR_SIZE B_EXPR_END",
    "const(7) const(3) B_VECTOR obj(uid=5).f[8] B_PLUS const(99) B_MINUS B_EXPR_END",
    "B_SYSLIST[0] B_MEMBER(cur.hp) const(1) B_GE_E B_EXPR_END",   # arity 3, member-list
    "B_SYSLIST[0] B_MEMBER(cur.hp) B_LMAX B_EXPR_END",            # arity 2, member-list
    "B_SYSLIST[0] B_MEMBER(cur.hp) B_PICK B_EXPR_END",
    "B_SYSLIST[0] B_COUNT B_EXPR_END",
    # the clamp the emitter now writes for a [TEXT=] row slot
    "Global.UInt16[0] Global.UInt16[0] const(0) B_GE B_MULT B_EXPR_END",
]

# THE INDEPENDENT CORROBORATION for the member-list arities, which are the hardest entries in
# OP_SEMANTICS to derive (OperatorExtract re-evaluates its member sub-expression once per set bit
# and restores the stack each round). This is `battle/aiauthor.py:225` verbatim -- the kit's real,
# byte-grounded "how many members are below max.hp/N" idiom. It balances at exactly 1 only if
# B_LT_E is arity 3 and B_PICK is arity 2, which is what the table says.
GOOD.append("B_SYSLIST[1] B_MEMBER(36) B_SYSLIST[1] B_MEMBER(37) B_PICK const(4) B_DIV "
            "B_LT_E B_COUNT B_EXPR_END")


@pytest.mark.parametrize("expr", GOOD)
def test_well_formed_expressions_balance(expr):
    info = S.analyze(expr)
    assert info.max_depth >= 1
    assert not info.unsafe_to_repeat


@pytest.mark.parametrize("expr,match", [
    # FINDING 1's defeat spelling -- ONE E, so B_MULT pops into an empty stack
    ("Global.UInt16[0] const(0) B_GE B_MULT B_EXPR_END", "UNDERFLOW"),
    ("B_PLUS B_EXPR_END", "UNDERFLOW"),
    ("const(1) B_PLUS B_EXPR_END", "UNDERFLOW"),
    ("B_SYSLIST[0] B_GE_E B_EXPR_END", "UNDERFLOW"),        # arity 3, only 1 operand
    ("const(1) const(2) B_EXPR_END", "EXACTLY ONE value"),
    ("B_MEMBER(4) B_PTR(7) B_EXPR_END", "EXACTLY ONE value"),
    ("B_EXPR_END", "EXACTLY ONE value"),
    ("const(1) B_SINGLE_PLUS B_EXPR_END", "EXACTLY ONE value"),
])
def test_malformed_streams_are_caught_by_the_walker_and_NOT_by_the_encoder(expr, match):
    """The `assemble` line is the point of the test: the byte encoder accepts every one of
    these. Before the walker existed they went straight into a per-frame ticker slot."""
    assemble(expr)                                           # encodes fine -- no arity check
    with pytest.raises(S.ExprSemanticError, match=match):
        S.analyze(expr)


def test_the_walker_names_the_offending_token_index():
    with pytest.raises(S.ExprSemanticError) as e:
        S.analyze("Global.UInt16[0] const(0) B_GE B_MULT B_EXPR_END")
    msg = str(e.value)
    assert "token 3 ('B_MULT')" in msg
    assert "CalcStack.cs:17-27" in msg                       # pop-on-empty logs, does not crash


def test_a_mid_stream_terminator_is_refused():
    with pytest.raises(S.ExprSemanticError, match="must be the LAST token"):
        S.analyze(["const(1)", "B_EXPR_END", "const(2)", "B_LT", "B_EXPR_END"])


def test_every_non_read_operator_carries_a_reason():
    """A refusal that cannot say WHY sends the author to the source. Every WRITE/IMPURE token
    hands the caller an engine-cited reason."""
    for name, (_a, effect) in S.OP_SEMANTICS.items():
        if effect != S.READ:
            assert S.token_sem(name).why, name
    assert "RECRUITS" in S.token_sem("B_PARTYADD").why
    assert "scriptRequestedButtonPress" in S.token_sem("B_KEYON").why
    assert "RNG" in S.token_sem("B_SELECT").why


def test_effects_are_reported_even_when_the_stream_also_balances():
    info = S.analyze("Global.Bit[8712] const(1) B_LET B_EXPR_END")
    assert [s.token for s in info.writes] == ["B_LET"]
    info2 = S.analyze("const(1) B_PARTYADD B_EXPR_END")
    assert [s.token for s in info2.writes] == ["B_PARTYADD"]


def test_token_sems_classifies_without_walking_the_stack():
    """An expression can be BOTH unbalanced and side-effecting; the classification pass has
    to survive the stack error so the caller can report the more actionable one."""
    sems = S.token_sems("B_LET B_EXPR_END")                  # underflows, but classifies
    assert [s.effect for s in sems] == [S.WRITE, S.READ]
    with pytest.raises(S.ExprSemanticError, match="UNDERFLOW"):
        S.analyze("B_LET B_EXPR_END")
