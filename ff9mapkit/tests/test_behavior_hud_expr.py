"""THE HUD ``expr:`` SEAM -- the one new authoring surface the completion-journal probe needs.

A ``[[behavior.hud]]`` value can name ``gil`` / ``timer`` / ``hp:<unit>`` / ``item:<id>`` /
a counter. None of those can name a Memoria custom variable (``Null.SBit[5]`` =
TREASURE_HUNTER_POINTS), a raw ``gEventGlobal`` field (``Global.Int24[187]`` = the
chocograph FOUND bitfield) or a ``flexible_varfunc`` read (``flex(16,3)`` =
PLAYER_ABILITY_LEARNT). ``expr:<RPN tokens>`` does, and the emitter is unchanged: the HUD
live pass already encodes 0x66 with the value operand as an expression.

The seam has to enforce three things AT THE CALL SITE, because a hud value is re-evaluated
every tick and a rule in a docstring is a wish:
  * no assigning operators (``B_LET`` & friends) and no impure ones (``B_PARTYADD``
    recruits; ``B_KEYON`` / ``B_SELECT`` mutate shared runtime state) -- they would rewrite
    save state or perturb the game every frame the ticker runs. Classified EXHAUSTIVELY in
    ``eb/exprsem.py``, never by name pattern;
  * the RPN must actually BALANCE -- ``exprasm.assemble`` is a byte encoder and checks no
    arity at all, so until ``exprsem.analyze`` existed a malformed expression shipped;
  * a value published into a slot a ``[TEXT=...]`` tag reads must be clamped non-negative --
    ``ETb.GetStringFromTable`` (ETb.cs:270-284) bounds the slot and the UPPER row but has NO
    lower bound, and a hud row re-parses every RENDERED frame, so a negative is per-frame
    ``IndexOutOfRangeException`` spam. THE EMITTER WRAPS IT (``hud_row_index_clamp``); the
    author is not asked to spell the clamp and then graded on the spelling.

The compile test at the bottom needs NO templates (verified: ``FieldBehavior.compile()``
is pure logic) -- it does not skip.
"""

from __future__ import annotations

import pytest

from ff9mapkit.content import behavior as B
from ff9mapkit.content import behaviortoml as BT
from ff9mapkit.eb import exprasm
from ff9mapkit.eb._exprtable import EXPR_OP_NAMES as _EXPR_OP_NAMES

PROBE_VALUES = [
    "expr:Null.SBit[5]",
    "expr:Global.UInt16[0]",
    "expr:Global.Int24[187]",
    "expr:Global.Int24[187] const4(16777215) B_AND",
    "expr:const(256) B_HAVE_ITEM",
    "expr:const(0) const(6) const(0) flex(16,3)",
    "expr:Global.UInt16[0] const(1000) B_DIV Global.UInt16[0] const(1000) B_DIV "
    "const(0) B_GE B_MULT",
]
PROBE_TEXT = ("[MPOS=8,8]=== COMPLETION PROBE / RUNG 0 ====\n"
              "TH POINTS      [NUMB=0]\nSCENARIO       [NUMB=1]\n"
              "CHOCO RAW      [NUMB=2]\nCHOCO MASKED   [NUMB=3]\n"
              "KEY ITEM 0     [NUMB=4]\nZIDANE AA:6    [NUMB=5]\n"
              "CLAMPED ROW    [NUMB=6]")


def _probe_toml() -> dict:
    """The probe's [behavior] shape as a raw dict -- one dummy unit + the strip."""
    return {
        "npc": [{"name": "keeper", "model": "GEO_NPC_F0_CSO", "pos": [400, -837]}],
        "behavior": {
            "warmup": 30,
            "unit": [{"npc": "keeper", "branch": [{"do": {"hold": [400, -837]}}]}],
            "hud": [{"window": 6, "digits": [3, 5, 5, 5, 1, 1, 5],
                     "values": list(PROBE_VALUES), "text": PROBE_TEXT}],
        },
    }


# ------------------------------------------------------------------ the source resolver
def _bare() -> B.FieldBehavior:
    """A minimal roster — one unit standing still, the same compile gate the probe's
    dummy [[behavior.unit]] exists to satisfy."""
    fb = B.FieldBehavior([B.UnitSpec("keeper", entry=2, spawn=(400, -837))])
    fb.units["keeper"].tree = B.Do(B.Hold((400, -837)))
    return fb


def test_hud_ref_returns_the_tokens_verbatim():
    fb = _bare()
    for v in PROBE_VALUES:
        assert fb._hud_ref(v) == v[len(B.HUD_EXPR_PREFIX):]


@pytest.mark.parametrize("bad,match", [
    ("expr:", "needs RPN tokens"),
    ("expr:   ", "needs RPN tokens"),
    ("expr:Null.SBit[5] B_EXPR_END", "drop B_EXPR_END"),
    ("expr:Bogus.Thing[1]", "unknown variable Source.Type"),
    ("expr:B_CONST", "takes an operand"),
])
def test_hud_expr_rejects_bad_tokens_at_build(bad, match):
    with pytest.raises(B.BehaviorError, match=match):
        B.hud_expr_tokens(bad)


# ------------------------------------------------------------------ the write-op refusal
def test_write_op_set_is_the_exhaustive_classification_not_a_name_pattern():
    """FINDING 3. The old set was ``"_LET" in n or n.startswith(("B_POST_","B_PRE_"))`` --
    34 names. It missed ``B_PARTYADD``, which RECRUITS a party member through the
    expression (EBin.cs:1209-1215) under a name no pattern matches. The set is now the
    WRITE half of ``exprsem.OP_SEMANTICS``, which ``test_exprsem.py`` proves covers the
    whole operator table."""
    old_pattern = {n for n in _EXPR_OP_NAMES.values()
                   if "_LET" in n or n.startswith(("B_POST_", "B_PRE_"))}
    assert len(old_pattern) == 34
    assert B.HUD_EXPR_WRITE_OPS - old_pattern == {"B_PARTYADD"}    # the miss, named
    assert not old_pattern - B.HUD_EXPR_WRITE_OPS                  # nothing lost
    assert B.HUD_EXPR_IMPURE_OPS == {"B_KEYON", "B_SELECT"}
    for read_op in ("B_AND", "B_GE", "B_MULT", "B_HAVE_ITEM", "B_CURHP", "B_EXPR_END"):
        assert read_op not in B.HUD_EXPR_WRITE_OPS
        assert read_op not in B.HUD_EXPR_IMPURE_OPS


@pytest.mark.parametrize("expr,tok", [
    ("expr:Global.Bit[8712] const(1) B_LET", "B_LET"),
    ("expr:Global.Bit[8712] const(1) B_PLUS_LET", "B_PLUS_LET"),
    ("expr:Global.Bit[8712] B_POST_PLUS", "B_POST_PLUS"),
    ("expr:B_SYSLIST[0] B_MEMBER(cur.hp) B_PRE_MINUS_A", "B_PRE_MINUS_A"),
    ("expr:B_SYSLIST[0] B_MEMBER(cur.hp) const(1) B_OR_LET_E", "B_OR_LET_E"),
])
def test_hud_expr_refuses_every_write_op(expr, tok):
    """A hud value re-evaluates EVERY TICK: one assigning operator here would write save
    state on every frame. Refused at the seam, not in prose."""
    with pytest.raises(B.BehaviorError, match="ASSIGN through the expression") as e:
        B.hud_expr_tokens(expr)
    assert tok in str(e.value)


def test_hud_expr_refuses_B_PARTYADD_the_op_the_name_pattern_missed():
    """FINDING 3, END TO END. ``B_PARTYADD`` used to sail through the gate: it has no
    ``_LET`` and no ``B_PRE_``/``B_POST_`` prefix. It calls ``partyadd()``
    (EBin.cs:1209-1215), so the old seam would have re-recruited a character on every
    ticker frame."""
    with pytest.raises(B.BehaviorError, match="ASSIGN through the expression"):
        B.hud_expr_tokens("expr:const(1) B_PARTYADD")


@pytest.mark.parametrize("expr,why", [
    ("expr:const(1) B_KEYON", "B_KEYON"),
    ("expr:B_SYSLIST[0] B_SELECT", "B_SELECT"),
    ("expr:B_SYSVAR[0]", "advances the shared RNG"),
    ("expr:B_SYSVAR[9]", "ETb.sChoose"),
])
def test_hud_expr_refuses_impure_reads(expr, why):
    """Not assignments, but not repeatable either: ``B_KEYON`` asserts
    VoicePlayer.scriptRequestedButtonPress (EBin.cs:1080), ``B_SELECT`` and
    ``B_SYSVAR[0]`` roll the shared RNG, ``B_SYSVAR[9]`` writes ETb.sChoose."""
    with pytest.raises(B.BehaviorError, match="mutate shared runtime state") as e:
        B.hud_expr_tokens(expr)
    assert why in str(e.value)


# ------------------------------------------------------- the RPN stack-balance validator
@pytest.mark.parametrize("expr,match", [
    # FINDING 1's exact defeat spelling: ONE E instead of two. It ends in the three tokens
    # the old syntactic gate matched, so it was certified SAFE -- and it underflows.
    ("expr:Global.UInt16[0] const(0) B_GE B_MULT", "UNDERFLOW"),
    ("expr:const(1) B_PLUS", "UNDERFLOW"),
    ("expr:B_MULT", "UNDERFLOW"),
    ("expr:const(1) const(2)", "EXACTLY ONE value"),
    # B_SINGLE_PLUS pushes the STALE _v0 and evaluates nothing (EBin.cs:618-622)
    ("expr:const(1) B_SINGLE_PLUS", "EXACTLY ONE value"),
])
def test_hud_expr_rejects_an_unbalanced_stream(expr, match):
    """FINDING 4. ``exprasm.assemble`` encodes every one of these without complaint -- it
    is a token-to-byte encoder, not a validator. ``exprsem.analyze`` is what makes the
    build-time-failure claim true."""
    from ff9mapkit.eb.exprasm import assemble
    assemble(expr[len(B.HUD_EXPR_PREFIX):] + " B_EXPR_END")        # the encoder is happy
    with pytest.raises(B.BehaviorError, match=match):
        B.hud_expr_tokens(expr)


# ---------------------------------------------------------------------- the clamp
def test_hud_text_table_slots_finds_the_row_indices():
    assert B.hud_text_table_slots("a [TEXT=1,6] b") == {6}
    assert B.hud_text_table_slots("[TEXT=0,2][NUMB=3][TEXT=1,7]") == {2, 7}
    assert B.hud_text_table_slots("[NUMB=0] no table tags") == set()


@pytest.mark.parametrize("text,slots", [
    ("[TEXT=1]", {0}),               # FINDING 2: ONE param -> UIntParam(1) == 0 -> slot 0
    ("[TEXT]", {0}),                 # no '=' at all -> Param is null -> bank 0, slot 0
    ("[TEXT= 1 , 3 ]", {3}),         # Single.TryParse eats surrounding whitespace
    ("[TEXT=1,3,99]", {3}),          # extra params ignored (UIntParam only reads 0 and 1)
    ("[TEXT=,3]", {0}),              # RemoveEmptyEntries drops the empty field -> "3" is the BANK
    ("{Text 1,4}", {4}),             # the Memoria brace spelling
    ("{Text 1}", {0}),
    ("{Text}", {0}),
    ("[text=1,5]", {5}),             # over-approximated on case (safe direction)
    ("[TEXT=1,2][TEXT=0]", {0, 2}),
])
def test_hud_text_table_slots_covers_every_spelling_the_engine_accepts(text, slots):
    """FINDING 2. The old regex was ``\\[TEXT=\\s*-?\\d+\\s*,\\s*(\\d+)`` -- two parameters
    only. Every row above resolves to a real gMesValue slot in the engine
    (FFIXTextTag.TryRead :87-153 + UIntParam :71-76 -> ETb.GetStringFromTable), and every
    one of them was INVISIBLE to both the clamp gate and the slot-arity check."""
    assert B.hud_text_table_slots(text) == slots


@pytest.mark.parametrize("text", ["[TEXT=1,-2]", "[TEXT=1,x]", "[TEXT=1,2.5]", "{Text 1,-1}"])
def test_a_slot_parameter_that_is_not_statically_knowable_is_refused(text):
    """``UIntParam`` goes through ``Single.TryParse`` + a ``(UInt32)`` cast whose
    out-of-range behaviour is unspecified, so the emitter cannot promise to clamp what it
    cannot resolve. Refused rather than guessed."""
    with pytest.raises(B.BehaviorError, match="not statically knowable"):
        B.hud_text_table_slots(text)


def test_a_TEXT_row_is_AUTO_CLAMPED_by_the_emitter():
    """FINDING 1, THE FIX. The author writes the bare value; the EMITTER emits
    ``E E const(0) B_GE B_MULT``. An unclamped publish is not rejected -- it is
    unrepresentable."""
    fb = _bare()
    fb.hud("row [NUMB=0] -> [TEXT=1,0]", ["expr:Global.UInt16[0]"], txid=900)
    body = fb.compile().ticker_body
    want = exprasm.assemble("Global.UInt16[0] Global.UInt16[0] const(0) B_GE B_MULT B_EXPR_END")
    assert bytes((0x66, 0x02, 0)) + want in body


def test_a_named_source_feeding_a_TEXT_row_is_clamped_too():
    """The old gate refused every non-``expr:`` source on a [TEXT=] slot ("only an
    'expr:' source can carry the clamp"). Auto-wrapping makes that restriction pointless:
    the emitter clamps whatever fragment the source resolves to."""
    fb = _bare()
    fb.hud("[NUMB=0] [TEXT=1,0]", ["gil"], txid=900)
    body = fb.compile().ticker_body
    want = exprasm.assemble("B_SYSVAR[6] B_SYSVAR[6] const(0) B_GE B_MULT B_EXPR_END")
    assert bytes((0x66, 0x02, 0)) + want in body


def test_a_non_TEXT_slot_is_NOT_clamped():
    """The wrap is scoped to row-index slots -- a plain ``[NUMB=]`` readout keeps showing
    negatives (a debt counter, a relative offset), which is the whole point of scoping it."""
    fb = _bare()
    fb.hud("[NUMB=0]", ["expr:Global.Int24[187]"], txid=900)
    body = fb.compile().ticker_body
    assert bytes((0x66, 0x02, 0)) + exprasm.assemble("Global.Int24[187] B_EXPR_END") in body


def test_TEXT_slot_out_of_range_is_refused():
    fb = _bare()
    with pytest.raises(B.BehaviorError, match=r"\[TEXT=…,3\] has no value"):
        fb.hud("[NUMB=0] [TEXT=1,3]", ["expr:Null.SBit[5]"], txid=900)


# ------------------------------------------------------------- the [NUMB=] decoder
@pytest.mark.parametrize("text,slots", [
    ("a [NUMB=6] b", {6}),
    ("[NUMB]", {0}),                 # IntParam(0) -> 0 when ParamCount <= 0 (FFIXTextTag.cs:68-74)
    ("[NUMB=]", {0}),                # RemoveEmptyEntries leaves no params at all
    ("[NUMB= 3 ]", {3}),             # Single.TryParse eats surrounding whitespace
    ("[NUMB=1,2]", {1, 2}),          # param1 is the overlay compare -- a SECOND read
    ("{Variable 4}", {4}),           # Memoria's own export spelling (ExportFieldTags.cs:35)
    ("{Variable}", {0}),
    ("[numb=5]", {5}),               # over-approximated on case (the safe direction)
    ("[TEXT=1,6] no NUMB tag", set()),
    ("[NUMB=0][NUMB=2]", {0, 2}),
])
def test_hud_numb_slots_covers_every_spelling_the_engine_accepts(text, slots):
    """The `\\[NUMB=(\\d+)` pattern this decoder replaced saw ONE of these. Each other row is a real
    gMesValue READ in the engine (FFIXTextTag.TryRead :88-150 + IntParam :68-74 ->
    DialogBoxSymbols.ParseVariableTextReplaceTags :154-170), and the read is UNCLAMPED against
    Int32[8], so a slot nothing published is the last field's leftovers -- or an IndexOutOfRange."""
    assert B.hud_numb_slots(text) == slots


@pytest.mark.parametrize("text", ["[NUMB=-2]", "[NUMB=x]", "[NUMB=2.5]", "{Variable 0,-1}"])
def test_a_NUMB_parameter_that_is_not_statically_knowable_is_refused(text):
    with pytest.raises(B.BehaviorError, match="not statically knowable"):
        B.hud_numb_slots(text)


@pytest.mark.parametrize("text,slot", [
    ("[NUMB=0] {Variable 3}", 3),     # the brace spelling
    ("[NUMB=0,5]", 5),                # the overlay-compare parameter -- a real second read
])
def test_a_NUMB_SPELLING_THE_OLD_REGEX_MISSED_is_refused_by_hud(text, slot):
    """Both rows publish one value and render a slot nothing wrote. `\\[NUMB=(\\d+)` matched neither,
    so both used to compile and then render the previous field's leftover number."""
    fb = _bare()
    with pytest.raises(B.BehaviorError, match=rf"\[NUMB={slot}\] has no value"):
        fb.hud(text, ["expr:Null.SBit[5]"], txid=900)


# ----------------------------------------------- the refusal PREFIX, pinned exactly
@pytest.mark.parametrize("src,tail", [
    ("item:abc", "item: takes a resolved item ID (the TOML lane resolves names)"),
    ("item:900", "item id must be 0..254"),
    ("hp:ghost", "unknown unit 'ghost'"),
])
def test_hud_ref_refusals_are_prefixed_with_the_SURFACE_not_a_function_repr(src, tail):
    """THE DEFECT THIS PINS. ``_hud_ref``'s four refusals interpolated a bare ``label`` -- which is
    not a parameter of that method, so it resolved to the ``eb.labelasm.label`` FUNCTION imported at
    behavior.py:59 and rendered ``<function label at 0x...> 'hp:ghost': unknown unit 'ghost'``. A
    substring match on the tail cannot see that; the assertion is anchored at the start of the
    message for exactly that reason. (tests/test_source_fstring_capture.py fails the whole package on
    the shape, not just this call site.)"""
    fb = _bare()
    with pytest.raises(B.BehaviorError) as e:
        fb._hud_ref(src)
    assert str(e.value) == f"{B.HUD_VALUE_LABEL} {src!r}: {tail}"


def test_hud_ref_refusals_take_the_CALLERS_label():
    """The same seam `hud_expr_tokens` exposes, so a second surface reuses the resolver as-is."""
    fb = _bare()
    with pytest.raises(B.BehaviorError) as e:
        fb._hud_ref("item:900", label="[[choice]] option values[2]")
    assert str(e.value).startswith("[[choice]] option values[2] 'item:900': ")
    with pytest.raises(B.BehaviorError) as e:                # ...and it reaches the expr: lane too
        fb._hud_ref("expr:", label="[[choice]] option values[2]")
    assert str(e.value).startswith("[[choice]] option values[2] 'expr:': ")


# ------------------------------------------------------- the SILENT-IGNORE precondition
def test_a_hud_only_behavior_block_compiles_to_nothing_and_lints_clean():
    """``behaviortoml.table()`` is ``return b if isinstance(b, dict) and b.get("unit")
    else None`` -- so a ``[behavior]`` block carrying ONLY a hud is SILENTLY IGNORED and
    ``validate`` still returns []. Ship the probe without a ``[[behavior.unit]]`` and the
    playtest reports "no window appeared", which is indistinguishable from "every read
    returned 0". Turned from a trap into a CHECKED PRECONDITION here."""
    raw = _probe_toml()
    del raw["behavior"]["unit"]
    assert BT.table(raw) is None
    assert BT.hud_lines(raw) == []
    assert BT.validate(raw) == []                 # clean -- and compiles to NOTHING
    # ... and the probe as authored does NOT have that shape
    assert BT.table(_probe_toml()) is not None
    assert len(BT.hud_lines(_probe_toml())) == 1


def test_probe_toml_validates_clean():
    assert BT.validate(_probe_toml()) == []


def test_validate_reports_a_bad_expr_source():
    raw = _probe_toml()
    raw["behavior"]["hud"][0]["values"][0] = "expr:Global.Bit[8712] const(1) B_LET"
    problems = BT.validate(raw)
    assert any("ASSIGN through the expression" in p for p in problems), problems


def test_validate_reports_an_out_of_range_TEXT_slot():
    """Lint parity with the ``hud()`` gate -- ``ff9mapkit lint`` must catch it too. The
    CLAMP is no longer lintable (nothing can express an unclamped publish); the slot-arity
    check still is, and it now sees the SINGLE-PARAMETER spelling."""
    raw = _probe_toml()
    raw["behavior"]["hud"][0]["text"] = PROBE_TEXT + " -> [TEXT=1,7]"
    assert any("[TEXT=…,7] has no value" in p for p in BT.validate(raw)), BT.validate(raw)


def test_validate_reports_an_unresolvable_TEXT_slot():
    raw = _probe_toml()
    raw["behavior"]["hud"][0]["text"] = PROBE_TEXT + " -> [TEXT=1,-2]"
    assert any("not statically knowable" in p for p in BT.validate(raw)), BT.validate(raw)


def test_validate_reports_an_unbalanced_expr_source():
    raw = _probe_toml()
    raw["behavior"]["hud"][0]["values"][0] = "expr:Global.UInt16[0] const(0) B_GE B_MULT"
    assert any("UNDERFLOW" in p for p in BT.validate(raw)), BT.validate(raw)


# --------------------------------------------------- the compiled bytes (NO templates)
def _compile_probe():
    fb = B.FieldBehavior([B.UnitSpec("keeper", entry=2, spawn=(400, -837))], warmup=30)
    fb.units["keeper"].tree = B.Do(B.Hold((400, -837)))
    fb.hud(PROBE_TEXT, PROBE_VALUES, window=6, txid=501,
           digits=[3, 5, 5, 5, 1, 1, 5])
    return fb.compile()


def test_compiled_ticker_carries_seven_expression_valued_settextvariables():
    """THE GENERATOR'S OWN ASSERTION, as a test: the compiled ticker must contain a 0x66
    whose argFlag byte is 0x02 for every probe row. A hud that compiled to nothing, or a
    lane that silently fell back to the immediate form, fails here."""
    from ff9mapkit.eb.disasm import pretty_expr
    body = _compile_probe().ticker_body
    found = {}
    i = 0
    while True:
        i = body.find(b"\x66\x02", i)
        if i < 0:
            break
        slot = body[i + 2]
        try:
            txt, end = pretty_expr(body, i + 3)
        except (IndexError, KeyError, ValueError):
            i += 1
            continue
        if slot <= 7 and end - i <= 40:
            found[slot] = (body[i:end], txt)
            i = end
        else:
            i += 1
    assert sorted(found) == [0, 1, 2, 3, 4, 5, 6]
    for slot, src in enumerate(PROBE_VALUES):
        raw, txt = found[slot]
        assert raw[:3] == bytes((0x66, 0x02, slot))
        assert raw[3:] == exprasm.assemble(src[len(B.HUD_EXPR_PREFIX):] + " B_EXPR_END")
        assert txt == "{" + src[len(B.HUD_EXPR_PREFIX):] + " B_EXPR_END}"


def test_open_pass_sentinels_stay_immediate():
    """The open pass still feeds max-width sentinels through the IMMEDIATE form
    (``66 00 <slot> <u16>``) -- the new lane is additive, not a replacement."""
    body = _compile_probe().ticker_body
    assert body.count(b"\x66\x00") >= 7
    # digits [3,5,5,5,1,1,5] -> 999, 65535 x3, 9, 9, 65535
    assert bytes((0x66, 0x00, 0, 0xE7, 0x03)) in body       # 999
    assert bytes((0x66, 0x00, 4, 0x09, 0x00)) in body       # 9
