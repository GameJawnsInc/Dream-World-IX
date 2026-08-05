"""The `.eb` EXPRESSION SEMANTICS table -- per-operator ARITY + EFFECT CLASS, and the RPN stack walker.

:mod:`_exprtable` names the operators and :mod:`exprasm` encodes them, but neither knows what an operator
DOES: ``assemble()`` is a token-to-byte encoder and performs no stack-balance or arity checking at all, so
until this module existed a malformed expression assembled cleanly and only failed in-game. This module
adds the missing half:

  * :data:`OP_SEMANTICS` -- EVERY mnemonic in ``_exprtable.EXPR_OP_NAMES``, classified explicitly. Not a
    name pattern: ``"_LET" in name`` catches assignment but misses ``B_PARTYADD`` (which recruits a party
    member through the expression) and ``B_KEYON`` / ``B_SELECT`` (which mutate shared runtime state). A
    name pattern is exactly the kind of gate that silently stops matching, so the classification is
    exhaustive and ``tests/test_exprsem.py`` asserts it covers the operator table completely -- a future
    op added to ``EXPR_OP_NAMES`` FAILS THE TEST instead of defaulting to "safe".
  * :func:`analyze` -- walks a token stream tracking CalcStack depth with each operator's TRUE arity,
    refusing an underflow and requiring the stream to end at exactly one value.

THE STACK MODEL (Memoria ``EBin.expr``, EBin.cs:303-349). The evaluator is not a textbook postfix machine:
an operand token PUSHES (``_s7.push``, EBin.cs:340) and an operator POPS its operands lazily through
``EvaluateValueExpression`` (EBin.cs:1621-1687) then pushes exactly one result through
``expr_Push_v0_Int24`` (EBin.cs:1270-1274). Net effect per token is therefore ``-arity + 1`` for every
operator except the ``B_EXPR_END`` terminator, which pushes nothing (EBin.cs:1247-1253). The member-list
operators re-evaluate their member sub-expression once per set bit but restore the stack each round
(``advanceTopOfStack`` after every ``getv``), so their NET arity is still a constant -- derived below from
each operator's own implementation, never guessed.

WHY AN UNDERFLOW IS NOT A CRASH BUT IS STILL A DEFECT: ``CalcStack.pop`` on an empty stack logs
``[CalcStack.pop] topOfStackID == 0`` and yields 0 (CalcStack.cs:17-27). In a hud value -- re-evaluated
every tick -- that is one log line per frame plus a silently wrong number.

THERE IS NO DEPTH CEILING: ``CalcStack.push`` grows its backing ``List<Int32>`` on demand
(CalcStack.cs:9-15, ``stack = new List<Int32>(16)`` is a capacity hint, CalcStack.cs:76). Deepening an
expression costs nothing; only the 26-bit VALUE envelope is bounded (see ``opcodes.EXPR_VALUE_MAX``).

Provenance: derived by reading the open-source Memoria C#. No SE bytes.
"""
from __future__ import annotations

from dataclasses import dataclass

from ._exprtable import EXPR_OP_NAMES, FLEX_FN_BY_NAME
from .exprasm import (_RE_CONST, _RE_CONST4, _RE_FLEX, _RE_MEMPTR, _RE_OBJ, _RE_OPHEX, _RE_SYS,
                      _RE_VAR, AssembleError)

# ------------------------------------------------------------------ effect classes
READ = "read"       # no observable state change -- safe to re-evaluate every frame
WRITE = "write"     # ASSIGNS through the expression (SetVariableValue / putv) or mutates party state
IMPURE = "impure"   # no assignment, but perturbs shared runtime state (the RNG, the voice-request flag)

EFFECTS = (READ, WRITE, IMPURE)


class ExprSemanticError(AssembleError):
    """A token stream that ENCODES fine but cannot evaluate correctly (stack underflow, wrong final
    depth, an operator whose arity is not statically known)."""


# ------------------------------------------------------------------ the operator table
# (arity, effect) for EVERY name in EXPR_OP_NAMES. `arity` is how many CalcStack entries the operator
# CONSUMES; every operator pushes exactly one result except B_EXPR_END, which pushes none.
#
# Four routing lanes in EBin.expr_jumpToSubCommand (EBin.cs:521-1254) decide where an operator's body is:
#   (a) inline in the switch                        -- EBin.cs:574-1253
#   (b) EventEngine.DoCalcOperationExt              -- EBin.cs:528-573 -> DoCalcOperationExt.cs:11-73
#   (c) EventEngine.OperatorExtract / *1 / *Let     -- OperatorExtract.cs:5-202
#   (d) EventEngine.OperatorAll / OperatorAll1      -- OperatorAll.cs:5-138
# A lane-(b) operator with NO `case` in DoCalcOperationExt is DEAD: it consumes nothing, returns 0 and
# pushes it. Those are recorded as arity 0 rather than pretended to be unary -- the table describes the
# engine that ships, not the engine the enum implies.
OP_SEMANTICS: "dict[str, tuple[int, str]]" = {
    # --- lane (b), no case in DoCalcOperationExt -> dead, arity 0, result 0 -------------------------
    "B_PAD0": (0, READ), "B_PAD1": (0, READ), "B_PAD2": (0, READ), "B_PAD3": (0, READ),
    "B_CAST8": (0, READ), "B_CAST8U": (0, READ), "B_CAST16": (0, READ), "B_CAST16U": (0, READ),
    "B_CAST_LIST": (0, READ), "B_OBJSPEC": (0, READ),
    "pad67": (0, READ), "pad68": (0, READ), "pad69": (0, READ),
    "B_pad7b": (0, READ), "B_PAD4": (0, READ),

    # --- inc/dec through an LVALUE: Eval (pop 1) / advance / SetVariableValue (pop 1) / push --------
    # EBin.cs:574-617. Net -1: one operand (the lvalue token), one result. SetVariableValue WRITES.
    "B_POST_PLUS": (1, WRITE), "B_POST_MINUS": (1, WRITE),
    "B_PRE_PLUS": (1, WRITE), "B_PRE_MINUS": (1, WRITE),

    # --- the member-list inc/dec, lane (d) OperatorAll1 (OperatorAll.cs:86-138) --------------------
    # operands: [member-list, member-field]. Each set bit does getv/advance/putv/advance -> net 0.
    # putv (EBin.cs:2067-2074) WRITES the member field.
    "B_POST_PLUS_A": (2, WRITE), "B_POST_MINUS_A": (2, WRITE),
    "B_PRE_PLUS_A": (2, WRITE), "B_PRE_MINUS_A": (2, WRITE),

    # --- unary arithmetic / logic, lane (a) --------------------------------------------------------
    # B_SINGLE_PLUS IS ARITY 0 IN THE SHIPPING ENGINE: EBin.cs:618-622 is a bare expr_Push_v0_Int24()
    # with NO EvaluateValueExpression -- it re-pushes the STALE _v0 and leaves its operand stranded.
    # Recorded faithfully, so `E B_SINGLE_PLUS` is reported as leaving two values (which it does).
    "B_SINGLE_PLUS": (0, READ),
    "B_SINGLE_MINUS": (1, READ),                       # EBin.cs:623-629
    "B_NOT": (1, READ),                                # EBin.cs:630-637
    "B_COMP": (1, READ),                               # EBin.cs:638-644

    # --- binary arithmetic / shifts / compares / bitwise, lane (a), EBin.cs:645-830 ----------------
    "B_MULT": (2, READ), "B_DIV": (2, READ), "B_REM": (2, READ),
    "B_PLUS": (2, READ), "B_MINUS": (2, READ),
    "B_SHIFT_LEFT": (2, READ), "B_SHIFT_RIGHT": (2, READ),
    "B_LT": (2, READ), "B_GT": (2, READ), "B_LE": (2, READ), "B_GE": (2, READ),
    "B_EQ": (2, READ), "B_NE": (2, READ),
    "B_AND": (2, READ), "B_XOR": (2, READ), "B_OR": (2, READ),
    # short-circuit: Eval / retreat / (advance + Eval) -- both arms consume 2 (EBin.cs:831-865)
    "B_ANDAND": (2, READ), "B_OROR": (2, READ),

    # --- lane (c) OperatorExtract, operands [member-list, member-field, rhs] (OperatorExtract.cs:5-78)
    "B_LT_E": (3, READ), "B_GT_E": (3, READ), "B_LE_E": (3, READ), "B_GE_E": (3, READ),
    "B_EQ_E": (3, READ), "B_NE_E": (3, READ),
    "B_AND_E": (3, READ), "B_NAND_E": (3, READ), "B_XOR_E": (3, READ), "B_OR_E": (3, READ),

    # --- lane (c) OperatorExtract1, operands [member-list, member-field] (OperatorExtract.cs:80-154) -
    # B_LMAX/B_LMIN are PARTY-MEMBER argmax/argmin selectors returning a member BITMASK -- NOT numeric
    # clamps. Reaching for them as min()/max() is a documented trap.
    "B_NOT_E": (2, READ), "B_LMAX": (2, READ), "B_LMIN": (2, READ),

    # --- the member-list primitives, lane (a) ------------------------------------------------------
    "B_MEMBER": (0, READ),      # EBin.cs:866-873 -- inline operand byte, pushes a Member ref
    "B_COUNT": (1, READ),       # EventEngine.cs:255-266 -- popcount of one popped list
    "B_PICK": (2, READ),        # EventEngine.cs:222-253 -- [member-list, member-field]
    "B_SELECT": (1, IMPURE),    # EventEngine.cs:268-285 -- Comn.random8() (Comn.cs:8-11) ADVANCES the
                                # shared UnityEngine.Random stream; re-rolling it every tick is a real
                                # perturbation even though nothing is assigned.

    # --- assignment, lane (a): Eval(rhs) / Eval-or-advance(lvalue) / SetVariableValue --------------
    "B_LET": (2, WRITE),                               # EBin.cs:893-913
    "B_MULT_LET": (2, WRITE), "B_DIV_LET": (2, WRITE), "B_REM_LET": (2, WRITE),
    "B_PLUS_LET": (2, WRITE), "B_MINUS_LET": (2, WRITE),
    "B_SHIFT_LEFT_LET": (2, WRITE), "B_SHIFT_RIGHT_LET": (2, WRITE),
    "B_AND_LET": (2, WRITE), "B_XOR_LET": (2, WRITE), "B_OR_LET": (2, WRITE),

    # --- lane (d) OperatorAll, operands [member-list, member-field, rhs] (OperatorAll.cs:5-84) ------
    "B_LET_A": (3, WRITE),
    "B_MULT_LET_A": (3, WRITE), "B_DIV_LET_A": (3, WRITE), "B_REM_LET_A": (3, WRITE),
    "B_PLUS_LET_A": (3, WRITE), "B_MINUS_LET_A": (3, WRITE),
    "B_SHIFT_LEFT_LET_A": (3, WRITE), "B_SHIFT_RIGHT_LET_A": (3, WRITE),
    "B_AND_LET_A": (3, WRITE), "B_XOR_LET_A": (3, WRITE), "B_OR_LET_A": (3, WRITE),

    # --- lane (c) OperatorExtractLet: the 2 member operands + the lvalue putv pops (Extract.cs:156-202)
    "B_LET_E": (3, WRITE), "B_AND_LET_E": (3, WRITE), "B_XOR_LET_E": (3, WRITE), "B_OR_LET_E": (3, WRITE),

    # --- input reads ------------------------------------------------------------------------------
    # B_KEYON SETS VoicePlayer.scriptRequestedButtonPress (EBin.cs:1080) -- read by UIKeyTrigger.cs:984
    # and VoicePlayer.cs:259, and cleared once per event pass (ProcessEvents.cs:14). Asserting it every
    # tick from a display value is a live side effect on the dialogue/voice path.
    "B_KEYON": (1, IMPURE),
    "B_KEYOFF": (1, READ), "B_KEY": (1, READ),         # EBin.cs:1101-1114 -- pure ETb reads
    "B_KEYON2": (1, READ), "B_KEYOFF2": (1, READ), "B_KEY2": (1, READ),   # DoCalcOperationExt.cs:62-66

    # --- trig / geometry, lane (a) ----------------------------------------------------------------
    "B_SIN2": (1, READ), "B_COS2": (1, READ),          # EBin.cs:1087-1100
    "B_SIN": (1, READ), "B_COS": (1, READ),            # EBin.cs:1175-1190
    "B_ANGLE": (2, READ), "B_DISTANCE": (2, READ),     # EBin.cs:1115-1137
    "B_ANGLEA": (1, READ), "B_DISTANCEA": (1, READ),   # EBin.cs:1147-1174
    "B_ANGLE2": (2, READ),                             # EBin.cs:1191-1201
    "B_PTR": (0, READ),                                # EBin.cs:1138-1146 -- inline operand byte

    # --- party / character / field reads, lane (b) ------------------------------------------------
    "B_CURHP": (1, READ), "B_MAXHP": (1, READ),        # DoCalcOperationExt.cs:67-72
    "B_CURMP": (1, READ), "B_MAXMP": (1, READ),        # DoCalcOperationExt.cs:31-36
    "B_HAVE_ITEM": (1, READ),                          # DoCalcOperationExt.cs:13-20
    "B_BAFRAME": (1, READ), "B_FRAME": (1, READ),      # DoCalcOperationExt.cs:21-26
    "B_BGIID": (1, READ), "B_BGIFLOOR": (1, READ),     # DoCalcOperationExt.cs:37-43
    "B_SPS": (2, READ),                                # DoCalcOperationExt.cs:27-30 -- two getv, returns 0
    "B_PARTYCHK": (1, READ),                           # EBin.cs:1202-1208
    # THE ONE THE NAME PATTERN MISSED: partyadd() RECRUITS a character (EBin.cs:1209-1215). No "_LET"
    # in the name, no B_PRE_/B_POST_ prefix -- a hud value carrying it would re-recruit every frame.
    "B_PARTYADD": (1, WRITE),

    # --- operand-bearing pushes, lane (a) ---------------------------------------------------------
    "B_OBJSPECA": (0, READ),                           # EBin.cs:1216-1221 -- two inline bytes
    "B_SYSLIST": (0, READ),                            # EBin.cs:1222-1227 -- one inline byte
    "B_SYSVAR": (0, READ),                             # EBin.cs:1228-1234 -- see IMPURE_SYSVARS below
    "B_CONST": (0, READ), "B_CONST4": (0, READ),       # EBin.cs:1235-1246

    # --- the terminator ---------------------------------------------------------------------------
    "B_EXPR_END": (0, READ),                           # EBin.cs:1247-1253 -- pushes NOTHING
}

# B_SYSVAR's operand picks the reader in EventEngine.GetSysvar (GetSysvar.cs:9-107), and two of the 32
# are not pure reads. Everything else there (gil = 6, timer = 17, step count = 7 ...) is.
IMPURE_SYSVARS = {
    0: "GetSysvar(0) is Comn.random8() (GetSysvar.cs:13-14) -- it advances the shared RNG stream",
    9: "GetSysvar(9) is ETb.GetChoose() (GetSysvar.cs:31-32), which WRITES ETb.sChoose "
       "(ETb.cs:262-268) -- re-reading it every tick clobbers a pending dialogue choice",
}

# Per-operator reasons for the non-obvious ones -- what a caller quotes when it refuses the token.
# The `_LET`-family reason is uniform ("assigns through the expression") and lives in `token_sem`.
OP_WHY = {
    "B_PARTYADD": "partyadd() RECRUITS a party member (EBin.cs:1209-1215) -- it is a write with no "
                  "'_LET' in its name, which is exactly why a name-pattern gate let it through",
    "B_KEYON": "it SETS VoicePlayer.scriptRequestedButtonPress (EBin.cs:1080), which the dialogue "
               "close path and the voice player both read (UIKeyTrigger.cs:984, VoicePlayer.cs:259)",
    "B_SELECT": "OperatorSelect draws Comn.random8() (EventEngine.cs:283, Comn.cs:8-11) -- it "
                "advances the shared RNG stream on every evaluation",
}

WRITE_OPS = frozenset(n for n, (_a, e) in OP_SEMANTICS.items() if e == WRITE)
IMPURE_OPS = frozenset(n for n, (_a, e) in OP_SEMANTICS.items() if e == IMPURE)
#: every operator that is NOT safe to evaluate on a per-frame ticker.
UNSAFE_TO_REPEAT = WRITE_OPS | IMPURE_OPS


@dataclass(frozen=True)
class TokenSem:
    """One token's stack + effect contribution."""
    token: str
    pops: int
    pushes: int
    effect: str
    why: str = ""        # non-empty only for a WRITE/IMPURE token, naming the engine reason


def token_sem(tok: str) -> TokenSem:
    """Semantics of ONE :func:`exprasm.assemble_token`-shaped token. Raises :class:`ExprSemanticError`
    for a token whose arity is not statically knowable (an unnamed raw operator byte)."""
    if _RE_CONST.match(tok) or _RE_CONST4.match(tok):
        return TokenSem(tok, 0, 1, READ)
    if tok in FLEX_FN_BY_NAME:                              # B_VECTOR / B_VECTOR_SIZE / B_DICTIONARY
        _fid, argc = FLEX_FN_BY_NAME[tok]                   # -- the sugar names at canonical arity
        return TokenSem(tok, argc, 1, READ)
    m = _RE_FLEX.match(tok)
    if m:
        # THE ARITY RIDES THE WIRE: expr_customSubCommand reads `u16 id + u8 argc` and pops exactly
        # argc operands (EBin.cs:351-359), then pushes one result -- either expr_Push_v0_Int24
        # (EBin.cs:461) or, for the VECTOR/DICTIONARY lvalue trio, a single push (EBin.cs:448-459).
        # Every defined flexible_varfunc (EBin.cs:2388-2414) is a pure read; an UNDEFINED id falls
        # through the switch to _v0 = 0 and still pushes one. So: arity = argc, effect READ, always.
        return TokenSem(tok, int(m.group(2)), 1, READ)
    m = _RE_SYS.match(tok)
    if m:
        if m.group(1) == "B_SYSVAR":
            idx = int(m.group(2))
            if idx in IMPURE_SYSVARS:
                return TokenSem(tok, 0, 1, IMPURE, IMPURE_SYSVARS[idx])
        return TokenSem(tok, 0, 1, READ)
    if _RE_OBJ.match(tok) or _RE_MEMPTR.match(tok) or _RE_VAR.match(tok):
        return TokenSem(tok, 0, 1, READ)                    # operand-bearing / variable pushes
    sem = OP_SEMANTICS.get(tok)
    if sem is not None:
        arity, effect = sem
        pushes = 0 if tok == "B_EXPR_END" else 1
        why = OP_WHY.get(tok, "")
        if not why and effect == WRITE:
            why = "it assigns through the expression (SetVariableValue / putv)"
        return TokenSem(tok, arity, pushes, effect, why)
    if _RE_OPHEX.match(tok):
        raise ExprSemanticError(
            f"{tok}: a raw unnamed operator byte has no known arity, so its stack effect cannot be "
            f"checked -- name it in _exprtable.EXPR_OP_NAMES and classify it in exprsem.OP_SEMANTICS")
    raise ExprSemanticError(f"unknown expression token {tok!r}")


@dataclass(frozen=True)
class ExprAnalysis:
    """The result of :func:`analyze`."""
    tokens: tuple
    max_depth: int                   # deepest the CalcStack goes (informational -- there is no ceiling)
    writes: tuple = ()               # (TokenSem, ...) for every WRITE token, in stream order
    impure: tuple = ()               # (TokenSem, ...) for every IMPURE token

    @property
    def unsafe_to_repeat(self) -> tuple:
        """Every token that makes this expression unsafe to evaluate once per frame."""
        return self.writes + self.impure


def split_tokens(text) -> list:
    """The same tokenisation :func:`exprasm.assemble` uses (braces optional, or a token list)."""
    if isinstance(text, str):
        return text.strip().strip("{}").split()
    if isinstance(text, (list, tuple)):
        return [str(t) for t in text]
    raise ExprSemanticError("analyze() takes a '{ ... }' string or a list of token strings")


def token_sems(text) -> list:
    """``[TokenSem, ...]`` for a stream — classification ONLY, no stack walk.

    Split out from :func:`analyze` deliberately: an expression can be BOTH unbalanced and
    side-effecting, and "you wrote a save-state assignment into a per-frame value" is the more
    actionable diagnosis of the two. A caller that wants both reports effects first."""
    toks = split_tokens(text)
    if not toks:
        raise ExprSemanticError("empty expression")
    return [token_sem(t) for t in toks]


def analyze(text) -> ExprAnalysis:
    """Walk an RPN token stream, tracking CalcStack depth by each operator's TRUE arity.

    Raises :class:`ExprSemanticError` on an UNDERFLOW (an operator with fewer operands than it pops --
    ``CalcStack.pop`` logs an error and yields 0, CalcStack.cs:17-27), on a stream that does not end at
    exactly ONE value (the consumer pops exactly one, EBin.cs:1621-1623 / getv EBin.cs:2058-2065), or on
    a token whose arity is not statically knowable.

    The stream MUST end with ``B_EXPR_END`` -- same contract as :func:`exprasm.assemble`.
    """
    toks = split_tokens(text)
    if not toks:
        raise ExprSemanticError("empty expression")
    if toks[-1] != "B_EXPR_END":
        raise ExprSemanticError("an expression must end with B_EXPR_END")
    depth = 0
    max_depth = 0
    writes, impure = [], []
    for i, tok in enumerate(toks):
        sem = token_sem(tok)
        if tok == "B_EXPR_END" and i != len(toks) - 1:
            raise ExprSemanticError(
                f"B_EXPR_END must be the LAST token -- token {i} of {len(toks)} terminates the "
                f"expression and the engine stops reading there (EBin.cs:1247-1253)")
        if sem.pops > depth:
            raise ExprSemanticError(
                f"stack UNDERFLOW at token {i} ({tok!r}): it consumes {sem.pops} operand(s) but only "
                f"{depth} value(s) are on the CalcStack. The engine does not crash -- CalcStack.pop "
                f"logs '[CalcStack.pop] topOfStackID == 0' and yields 0 (CalcStack.cs:17-27) -- so this "
                f"would ship as a silently wrong number plus one log line per evaluation. "
                f"Tokens so far: {' '.join(toks[:i + 1])}")
        depth += sem.pushes - sem.pops
        max_depth = max(max_depth, depth)
        if sem.effect == WRITE:
            writes.append(sem)
        elif sem.effect == IMPURE:
            impure.append(sem)
    if depth != 1:
        raise ExprSemanticError(
            f"an expression must leave EXACTLY ONE value on the CalcStack, this one leaves {depth} "
            f"({' '.join(toks)}). The consumer pops exactly one (EBin.EvaluateValueExpression, "
            f"EBin.cs:1621-1623)" +
            (" -- an empty stack pops 0 with a log line (CalcStack.cs:17-27)" if depth < 1 else
             " -- the extra value(s) are silently discarded when the CalcStack is next emptied "
             "(EBin.cs:308)"))
    return ExprAnalysis(tuple(toks), max_depth, tuple(writes), tuple(impure))
