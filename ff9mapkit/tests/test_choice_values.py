"""A ``[[choice]]`` option's ``values`` -- the LIVE-NUMBERS lane (``content/choice.py``).

WHAT THIS LANE IS FOR. ``ETb.gMesValue`` is ``Int32[8]``, allocated once at engine init
(EventEngine.Initialize.cs:30) and never cleared on a field load, so a window whose ``[NUMB=n]`` /
``[TEXT=b,n]`` tag reads a slot nothing in this field wrote renders the LAST field's leftovers --
plausible numbers, right columns, entirely stale. ``values`` publishes those slots immediately before
the option's reply window opens.

TWO PROPERTIES THIS FILE EXISTS TO PIN, both of which have already cost a round somewhere in this kit:

  * the validation is the hud lane's, REACHED, not copied (``behavior.hud_expr_tokens`` +
    ``behavior.hud_text_table_slots``). A second copy of the write/impure refusal is the copy that
    drifts, and ``eb/exprsem.py``'s exhaustive operator table is what makes the refusal complete;
  * the ``[TEXT=]`` non-negative clamp is EMITTED by ``option_values_body``, not graded by a rule.
    A previous round shipped four syntactic gates that could not fail, one of which certified a
    single-``E`` spelling (which both defeats the clamp and underflows the CalcStack) as safe.

Pure byte tests plus ``build.validate`` -- no game data, no install, so this runs in a fresh worktree.
"""

from __future__ import annotations

import re

import pytest

from ff9mapkit.content import choice
from ff9mapkit.content.behavior import HUD_EXPR_PREFIX, hud_row_index_clamp
from ff9mapkit.eb import exprasm as EA, opcodes


def _write(slot, toks):
    return opcodes.set_text_variable_expr(slot, EA.assemble(toks + " B_EXPR_END"))


# ---- the emitter ------------------------------------------------------------------------------
def test_values_publish_slots_in_order_before_the_reply_window():
    """Order is load-bearing twice over: the engine bakes Dialog.Width ONCE at open
    (Dialog.AutomaticSize, Dialog.cs:1560-1591) and never re-sizes on a later value change, so a
    publish after the WindowSync would render at a width measured over the stale numbers."""
    opt = {"text": "Read", "reply": "A [NUMB=0] B [NUMB=1]",
           "values": ["expr:B_SYSVAR[6]", "expr:Global.UInt16[0]"]}
    body = choice.option_body(opt, reply_txid=700)
    want = _write(0, "B_SYSVAR[6]") + _write(1, "Global.UInt16[0]")
    assert body.startswith(want)                          # ...and the window follows, not precedes
    assert body == want + opcodes.window_sync(1, 128, 700)


def test_no_values_key_is_byte_identical_to_before():
    """The lane is opt-in: an option without `values` must emit exactly what it always emitted."""
    opt = {"text": "Read", "reply": "hello"}
    assert choice.option_body(opt, reply_txid=700) == opcodes.window_sync(1, 128, 700)


def test_a_TEXT_slot_is_CLAMPED_by_the_emitter_and_a_NUMB_slot_is_not():
    """ETb.GetStringFromTable (ETb.cs:270-284) bounds the slot and the UPPER row but has NO lower
    bound, so a negative indexes tableText[-n] and throws once per rendered frame. Which slots are
    table indices is read off THIS option's own reply, with the engine-faithful tag decoder."""
    opt = {"text": "Read", "reply": "Rank [TEXT=600,1] pts [NUMB=0]",
           "values": ["expr:Null.SBit[5]", "expr:Null.SBit[5] const(8) B_DIV"]}
    body = choice.option_body(opt, reply_txid=700)
    assert _write(0, "Null.SBit[5]") in body                                   # [NUMB=0]: bare
    assert _write(1, hud_row_index_clamp("Null.SBit[5] const(8) B_DIV")) in body   # [TEXT=]: clamped
    assert _write(1, "Null.SBit[5] const(8) B_DIV") not in body                 # never the raw form


def test_a_bare_TEXT_tag_clamps_slot_ZERO():
    """UIntParam(i) returns 0 when ParamCount <= i (FFIXTextTag.cs:71-76), so `[TEXT]` and `[TEXT=5]`
    both read gMesValue[0]. A decoder that only saw the two-parameter form would leave slot 0
    unclamped -- the under-approximation that ships an IndexOutOfRange."""
    opt = {"text": "R", "reply": "who: [TEXT]", "values": ["expr:Global.Byte[313]"]}
    body = choice.option_body(opt, reply_txid=700)
    assert _write(0, hud_row_index_clamp("Global.Byte[313]")) in body


def test_a_NINTH_value_is_REFUSED_at_the_emitter():
    """ETb.SetMesValue clamps scriptID to 0..7 against Int32[8] (ETb.cs:230-234): in-game a 9th write
    does not error, it overwrites slot 7. So the refusal has to be here, where it is unrepresentable."""
    opt = {"text": "R", "reply": "x", "values": ["expr:B_SYSVAR[6]"] * (choice.MES_VALUE_SLOTS + 1)}
    with pytest.raises(ValueError, match="gMesValue slots"):
        choice.option_body(opt, reply_txid=700)
    opt["values"] = ["expr:B_SYSVAR[6]"] * choice.MES_VALUE_SLOTS         # ...eight is fine
    assert choice.option_body(opt, reply_txid=700)


def test_values_with_no_reply_window_is_REFUSED():
    """gMesValue is GLOBAL engine state that outlives the field load, so publishing with no window of
    this row's own is a pure side effect on the NEXT field's numbers -- the exact mechanism that made
    the T1b mockup render another bench's slot vector."""
    with pytest.raises(ValueError, match="needs a `reply`"):
        choice.option_body({"text": "R", "values": ["expr:B_SYSVAR[6]"]})


def test_a_SCALAR_values_is_REFUSED_not_iterated_per_character():
    with pytest.raises(ValueError, match="must be a LIST"):
        choice.option_values({"values": "expr:B_SYSVAR[6]"})


def test_a_non_expr_source_is_REFUSED():
    """The hud lane's counter/`hp:`/`item:` sources name a [[behavior.unit]] this lane cannot see."""
    with pytest.raises(ValueError, match="expr:"):
        choice.option_body({"text": "R", "reply": "x", "values": ["gil"]}, reply_txid=1)


# ---- the validation is REACHED, not re-implemented ----------------------------------------------
@pytest.mark.parametrize("bad,why", [
    ("expr:Global.UInt16[0] const(1) B_LET", "ASSIGN"),        # a WRITE through the expression
    ("expr:const(3) B_PARTYADD", "ASSIGN"),                    # ...under a name no pattern matches
    ("expr:B_SYSVAR[0]", "mutate shared runtime"),             # IMPURE: advances the shared RNG
    ("expr:B_SYSVAR[6] B_PLUS", "UNDERFLOW"),                  # the encoder never checked balance
    ("expr:B_SYSVAR[6] B_SYSVAR[6]", "EXACTLY ONE value"),
    ("expr:B_SYSVAR[6] B_EXPR_END", "drop B_EXPR_END"),
    ("expr:", "needs RPN tokens"),
])
def test_every_hud_lane_refusal_applies_here_too(bad, why):
    """One validator, two lanes. `exprsem.OP_SEMANTICS` classifies all 122 operators EXHAUSTIVELY --
    B_PARTYADD recruits a character (EBin.cs:1209-1215) with no `_LET` in its name, which is the case
    a name-pattern gate silently stops matching."""
    with pytest.raises(ValueError, match=why):
        choice.option_body({"text": "R", "reply": "x", "values": [bad]}, reply_txid=1)


def test_the_refusal_message_names_the_CHOICE_surface_not_the_hud():
    with pytest.raises(ValueError, match=r"\[\[choice\]\] option values\[1\]"):
        choice.option_body({"text": "R", "reply": "x",
                            "values": ["expr:B_SYSVAR[6]", "expr:nonsense_token"]}, reply_txid=1)


# ---- THE COVERAGE RULE: keyed on the REPLY, not on `values` --------------------------------------
@pytest.mark.parametrize("reply,shown", [
    ("Scenario [NUMB=0]", "[NUMB=0]"),
    ("A [NUMB=0] B [NUMB=1]", "[NUMB=0]"),
    ("Rank [TEXT=600,1]", "[TEXT=...,1]"),
    ("who: [TEXT]", "[TEXT=...,0]"),
    ("count {Variable 2}", "[NUMB=2]"),          # the Memoria brace spelling
    ("live [NUMB=1,3]", "[NUMB=1]"),             # ...and the overlay-compare second read
])
def test_a_reply_TAG_WITH_NO_VALUES_KEY_AT_ALL_is_REFUSED(reply, shown):
    """THE ORIGINAL T1b DEFECT, and the one shape the first cut of this check could not see: it was
    nested inside `if VALUES_KEY in o`, so it only fired for rows that had already opted IN. A page
    whose reply carries [NUMB=n] and NO `values` key validated clean, built clean, and rendered the
    previous bench's leftover slot vector in-game (ETb.gMesValue is Int32[8] allocated once at engine
    init, EventEngine.Initialize.cs:30, and never cleared on a field load)."""
    with pytest.raises(ValueError, match=re.escape(f"reply {shown} has no value")):
        choice.option_body({"text": "Read", "reply": reply}, reply_txid=700)


def test_the_coverage_rule_is_the_SAME_function_the_validator_calls():
    """One rulebook: `build.validate` prefixes the row identity onto exactly these tails. A second
    copy is the copy that drifts -- which is how the emitter and the validator disagreed before."""
    tails = choice.reply_slot_problems({"text": "R", "reply": "x [NUMB=2]"})
    assert len(tails) == 1 and tails[0].startswith("reply [NUMB=2] has no value")
    assert choice.reply_slot_problems({"text": "R", "reply": "x [NUMB=0]",
                                       "values": ["expr:B_SYSVAR[6]"]}) == []


@pytest.mark.parametrize("modal", ["input", "recall", "qte"])
def test_a_MODAL_that_owns_slot_zero_covers_its_own_echo(modal):
    """`input`/`recall` load gMesValue slot 0 with the stepper's echo (numinput.py:380, :413) and a
    `qte` loads slot 0 with its score (qte.py:334), so `you bid [NUMB=0]` with no `values` is CORRECT
    -- the coverage rule must not refuse it. (option_body needs the seat maps to emit; the rule is
    checked directly.)"""
    assert choice.reply_slot_problems({"text": "Y", modal: "bid", "reply": "you bid [NUMB=0]"}) == []


def test_a_reply_with_no_tags_needs_nothing_and_a_bodiless_option_is_untouched():
    assert choice.reply_slot_problems({"text": "Y", "reply": "just words"}) == []
    assert choice.reply_slot_problems({"text": "Y"}) == []
    assert choice.option_body({"text": "Y", "reply": "just words"}, reply_txid=700)


def test_an_unknowable_slot_parameter_is_reported_not_assumed_safe():
    """`Single.TryParse` + a cast (FFIXTextTag.cs:68-74): which slot it reads is not statically
    knowable, so no lane can claim to have published it."""
    assert any("not statically knowable" in t for t in
               choice.reply_slot_problems({"text": "Y", "reply": "x [NUMB=2.5]"}))


def test_the_prefix_is_the_hud_lanes_own_constant():
    assert HUD_EXPR_PREFIX == "expr:"
    assert choice.MES_VALUE_SLOTS == 8            # ETb.cs:230-234 against Int32[8]


# ---- build.validate parity ----------------------------------------------------------------------
_TOML = """
[field]
id = 30899
name = "VALROOM"
area = 11

[camera]
pitch = 48.0
distance = 4500
fov = 42.2
[camera.frame]
back = 205
front = 432

[walkmesh]
quad = [[-1220, 257], [1220, 257], [1220, -1931], [-1220, -1931]]
frame = "world"

[player]
spawn = [0, -837]

[[npc]]
name = "keeper"
model = "GEO_NPC_F0_CSO"
pos = [400, -837]

[[choice]]
npc = "keeper"
prompt = "Read?"
%s
"""

_OK_ROWS = """
  [[choice.options]]
  text = "Yes"
  reply = "gil [NUMB=0]"
  values = ["expr:B_SYSVAR[6]"]

  [[choice.options]]
  text = "No"
"""


def _validate(rows, tmp_path):
    from ff9mapkit.build import FieldProject, validate
    p = tmp_path / "v.field.toml"
    p.write_text(_TOML % rows, encoding="utf-8")
    return validate(FieldProject.load(p))


def test_a_good_values_row_validates_clean(tmp_path):
    assert _validate(_OK_ROWS, tmp_path) == []


@pytest.mark.parametrize("rows,why", [
    # the slot ceiling, reported as well as refused
    ('  [[choice.options]]\n  text = "Y"\n  reply = "x [NUMB=0]"\n  values = ['
     + '"expr:B_SYSVAR[6]",' * 9 + ']\n\n  [[choice.options]]\n  text = "N"\n',
     "gMesValue slots"),
    # a write op -- the hud lane's refusal, reached through the same function
    ('  [[choice.options]]\n  text = "Y"\n  reply = "x [NUMB=0]"\n'
     '  values = ["expr:Global.UInt16[0] const(1) B_LET"]\n\n  [[choice.options]]\n  text = "N"\n',
     "ASSIGN"),
    # a tag with no value behind it (the hud lane's [NUMB=]/[TEXT=] coverage rule)
    ('  [[choice.options]]\n  text = "Y"\n  reply = "x [NUMB=3]"\n  values = ["expr:B_SYSVAR[6]"]\n'
     '\n  [[choice.options]]\n  text = "N"\n',
     r"\[NUMB=3\] has no value"),
    ('  [[choice.options]]\n  text = "Y"\n  reply = "x [TEXT=600,2]"\n  values = ["expr:B_SYSVAR[6]"]\n'
     '\n  [[choice.options]]\n  text = "N"\n',
     r"\[TEXT=\.\.\.,2\] has no value"),
    # a slot parameter the engine resolves through Single.TryParse -- not statically knowable, so the
    # emitter cannot promise the clamp
    ('  [[choice.options]]\n  text = "Y"\n  reply = "x [TEXT=600,-2]"\n  values = ["expr:B_SYSVAR[6]"]\n'
     '\n  [[choice.options]]\n  text = "N"\n',
     "not statically knowable"),
    # values with nothing to render into
    ('  [[choice.options]]\n  text = "Y"\n  values = ["expr:B_SYSVAR[6]"]\n'
     '\n  [[choice.options]]\n  text = "N"\n',
     "needs a `reply`"),
    # an empty list is an authoring mistake, not a no-op
    ('  [[choice.options]]\n  text = "Y"\n  reply = "x"\n  values = []\n'
     '\n  [[choice.options]]\n  text = "N"\n',
     "at least one"),
])
def test_validate_reports_what_the_emitter_refuses(rows, why, tmp_path):
    import re
    probs = _validate(rows, tmp_path)
    assert any(re.search(why, m) for m in probs), probs


def test_validate_REFUSES_a_reply_tag_with_no_values_key(tmp_path):
    """THE HOLE THIS CLOSES, at the surface an author actually builds through. The scan used to be
    nested inside `if VALUES_KEY in o`, so this exact toml -- the mockup's shape -- validated clean
    AND linted clean. Both slots are reported, not just the first."""
    rows = ('  [[choice.options]]\n  text = "Y"\n  reply = "gil [NUMB=0] pts [NUMB=1]"\n'
            '\n  [[choice.options]]\n  text = "N"\n')
    probs = _validate(rows, tmp_path)
    assert sum("has no value" in m for m in probs) == 2, probs
    assert all(m.startswith("[[choice]] #0 option 0 reply [NUMB=") for m in probs), probs


def test_values_may_not_share_a_row_with_a_MODAL_that_owns_slot_zero(tmp_path):
    """`input`/`recall` load gMesValue slot 0 with the stepper's own echo (content/numinput.py:413).
    `values` is emitted after them and starts at slot 0, so it would silently overwrite that echo."""
    rows = ('  [[choice.options]]\n  text = "Y"\n  input = "bid"\n  reply = "you bid [NUMB=0]"\n'
            '  values = ["expr:B_SYSVAR[6]"]\n\n  [[choice.options]]\n  text = "N"\n')
    extra = '\n[[numeric_input]]\nname = "bid"\nmax = 100\n'
    from ff9mapkit.build import FieldProject, validate
    p = tmp_path / "v.field.toml"
    p.write_text((_TOML % rows) + extra, encoding="utf-8")
    probs = validate(FieldProject.load(p))
    assert any("can't share a row with 'input'" in m for m in probs), probs
