"""The multi-window scene verbs + text-synchronized signals (studies/messages/SURVEY.md §11 Tier-2
items 8 and 7).

What is pinned here, and why each pin exists:

* the four raw opcode wrappers, byte-exact (0x21 / 0x54 / 0x8E / 0xE3 -- all four existed only as raw
  ``encode`` calls buried in mognet/numinput before this);
* the ``[INCS]`` / ``[SIGL=n]`` / ``[TIME=-1]`` text tags, and specifically the PAIR ``[INCS][TIME=-1]``
  that stock's unison entries carry -- the bracket-format ``[INCS]`` signals but does NOT inhibit the
  dismiss button (FFIXTextTag OriginalTagNames maps it to IncreaseSignalEx), so the pair is load-bearing
  rather than redundant;
* the guarded spin-wait's exact shape, including that the backward jump lands on the CONDITION and not
  on the counter seed (a loop that re-seeds never terminates);
* THE SIGNAL-TIMEOUT LAW -- there is no unguarded form to author;
* the window ledger: every way to leak or strand a window is refused;
* that a scene with none of these keys still emits byte-identical bytes to before they existed.
"""
from __future__ import annotations

import pytest

from ff9mapkit.build import FieldProject, validate
from ff9mapkit.content import cutscene as _cutscene
from ff9mapkit.content import region as _region
from ff9mapkit.content import text as _text
from ff9mapkit.eb import disasm, opcodes

BASE = """
[field]
id = 30603
name = "MESGT2"
area = 11

[camera]
pitch = 45

[walkmesh]
quad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]

[player]
spawn = [0, -300]
"""


def _project(tmp_path, toml: str) -> FieldProject:
    p = tmp_path / "f.field.toml"
    p.write_text(toml, encoding="utf-8")
    return FieldProject.load(p)


def _problems(tmp_path, toml: str):
    return validate(_project(tmp_path, toml))


# --- the opcode wrappers -----------------------------------------------------------------------

def test_window_opcode_wrappers_are_byte_exact():
    # ops >= 0x10 carry an arg_flags byte before their operands; RaiseWindows takes none at all
    assert opcodes.close_window(2) == bytes([0x21, 0x00, 0x02])
    assert opcodes.wait_window(7) == bytes([0x54, 0x00, 0x07])
    assert opcodes.raise_windows() == bytes([0x8E])
    assert opcodes.set_dialog_progression(0) == bytes([0xE3, 0x00, 0x00])
    assert opcodes.set_dialog_progression(2) == bytes([0xE3, 0x00, 0x02])


def test_open_window_uses_the_ex_form_only_when_attributed():
    plain = _cutscene.open_window(500, window=3, flags=0)
    assert plain == opcodes.window_async(3, 0, 500)
    attributed = _cutscene.open_window(500, window=3, flags=128, actor_uid=4)
    assert attributed == opcodes.window_async_ex(4, 3, 128, 500)


def test_raise_is_not_folded_into_open_by_default():
    # stock emits RaiseWindows as its own op after the async, and the Treno keypad (5 windows) never
    # raises at all -- so an open must not smuggle one in
    assert opcodes.raise_windows() not in _cutscene.open_window(500)
    assert _cutscene.open_window(500, raise_after=True).endswith(opcodes.raise_windows())


def test_no_window_sentinel_is_named():
    assert opcodes.NO_WINDOW == 255


# --- the text side -----------------------------------------------------------------------------

def test_signal_tag_spellings():
    assert _text.signal_tag("+") == "[INCS]"
    assert _text.signal_tag(True) == "[INCS]"
    assert _text.signal_tag(-1) == "[INCS]"      # OnSignal increments on ANY negative value
    assert _text.signal_tag(0) == "[SIGL=0]"
    assert _text.signal_tag(2) == "[SIGL=2]"
    assert _text.signal_tag(None) == ""
    assert _text.signal_tag(False) == ""


def test_hold_emits_the_undismissable_time_tag():
    line, _, _ = _text.dress_window({"hold": True}, "x")
    assert line == "x[TIME=-1]"


def test_stocks_unison_pair_is_what_a_signalled_hold_emits():
    # field 41's Zorn & Thorn entries end `[INCS][TIME=-1]` -- Memoria's own importer collapses exactly
    # that pair into one modern token (Import/Fields/FieldTags.cs:45), which is the ground truth here.
    line, _, _ = _text.dress_window({"signal": "+", "hold": True}, "We'll be very grateful!")
    assert line == "We'll be very grateful![INCS][TIME=-1]"


def test_signal_lands_before_the_time_tag():
    # the signal must fire when the last GLYPH appears, not after the close
    line, _, _ = _text.dress_window({"signal": 2, "duration": 90}, "x")
    assert line == "x[SIGL=2][TIME=90]"


def test_hold_wins_over_duration_in_the_emission():
    # validation refuses the combination; if it ever reaches the emitter, only one tag may be written
    line, _, _ = _text.dress_window({"hold": True, "duration": 90}, "x")
    assert line == "x[TIME=-1]"
    assert "[TIME=90]" not in line


def test_no_new_keys_is_byte_identical():
    assert _text.dress_window({}, "plain line") == ("plain line", None, None)


# --- the guarded wait --------------------------------------------------------------------------

def test_wait_signal_compiles_stocks_guarded_shape():
    b = _cutscene.wait_signal(2)
    ins = list(disasm.iter_code(b, 0, len(b)))
    names = [disasm.op_name(i.op) for i in ins]
    # seed, condition, exit jump, Wait(1), decrement, back jump
    assert names == ["op_05", "op_05", "op_02", "op_22", "op_05", "op_01"]
    assert _region.SYSVAR_MES_SIGNAL == 8
    assert disasm.pretty_expr(b, ins[1].off + 1)[0] == (
        "{B_SYSVAR[8] const(2) B_LT Map.Int16[3] const(0) B_GT B_ANDAND B_EXPR_END}")


def test_the_back_jump_lands_on_the_condition_not_the_seed():
    # THE termination pin: if the loop jumped back to the seed it would re-arm the countdown every
    # iteration and spin forever, and nothing else in the build would notice
    b = _cutscene.wait_signal(2)
    ins = list(disasm.iter_code(b, 0, len(b)))
    seed, cond, back = ins[0], ins[1], ins[-1]
    assert disasm.jump_target(back) == cond.off
    assert disasm.jump_target(back) != seed.off


def test_the_exit_jump_clears_the_whole_loop():
    b = _cutscene.wait_signal(2)
    ins = list(disasm.iter_code(b, 0, len(b)))
    assert disasm.jump_target(ins[2]) == len(b)


def test_the_timeout_is_stocks_seed_and_is_authorable():
    assert _cutscene.SIGNAL_GUARD_FRAMES == 250
    assert bytes([0xFA, 0x00]) in _cutscene.wait_signal(1)                    # 250
    assert bytes([0x3C, 0x00]) in _cutscene.wait_signal(1, timeout=60)


def test_there_is_no_unguarded_signal_wait():
    # THE SIGNAL-TIMEOUT LAW: 117 of stock's 319 signal waits carry a frame guard and every guarded
    # site seeds 250; a wait that can never end is not an authorable shape
    with pytest.raises(ValueError, match="positive frame count"):
        _cutscene.wait_signal(1, timeout=0)
    with pytest.raises(ValueError, match="positive frame count"):
        _cutscene.wait_signal(1, timeout=-1)


def test_while_block_uses_the_signed_op_for_the_back_hop():
    # 0x02 reads its operand UNSIGNED (forward-only); only 0x01 can express a negative offset
    body = opcodes.wait(1)
    b = _region.while_block(_region.cond_truthy(_region.MAP_BOOL, 3), body)
    assert b[-3] == _region.JMP_UNCOND
    assert int.from_bytes(b[-2:], "little", signed=True) < 0


def test_while_block_refuses_an_unencodable_body():
    with pytest.raises(ValueError, match="backward jump"):
        _region.while_block(_region.cond_truthy(_region.MAP_BOOL, 3), b"\x00" * 33000)


def test_dec_var_is_the_post_minus_form():
    assert _region.dec_var(_region.MAP_INT16, 3) == bytes([0x05, 0xD9, 0x03, 0x05, 0x7F])


# --- the step vocabulary -----------------------------------------------------------------------

UNISON = BASE + """
[[npc]]
name = "zorn"
preset = "vivi"
pos = [-300, -800]
dialogue = "..."

[[npc]]
name = "thorn"
preset = "vivi"
pos = [300, -800]
dialogue = "..."

[[cutscene]]
actors = ["zorn", "thorn"]
steps = [
  { set_signal = 0 },
  { actor = "zorn",  open = "A!", speaker = "Zorn",  window = 2, signal = "+", hold = true },
  { actor = "thorn", open = "B!", speaker = "Thorn", window = 3, signal = "+", hold = true },
  { wait_signal = 2 },
  { wait = 60 },
  { close = 2 },
  { close = 3 },
  { set_signal = 0 },
]
"""


def test_the_unison_scene_validates_clean(tmp_path):
    assert _problems(tmp_path, UNISON) == []


def test_open_steps_consume_a_txid_like_say_steps():
    # the six independent `"say" in s` tests are the reason this predicate exists: a miscount does not
    # fail a build, it shifts every later line onto the wrong .mes entry
    steps = [{"open": "a"}, {"wait": 5}, {"say": "b"}, {"close": 1}, {"set_signal": 0}]
    assert [_cutscene.step_text(s) for s in steps] == ["a", None, "b", None, None]
    assert len(_cutscene.text_steps(steps)) == 2


def test_narration_flavor_takes_the_window_verbs_too(tmp_path):
    # NB the `hold` here is not decoration -- see THE BROADCAST-CONFIRM LAW below. This test asserted
    # the un-held shape was legal until the bench proved it isn't.
    toml = BASE + """
[[cutscene]]
steps = [
  { open = "A hint that stays up.", window = 3, style = "transparent", hold = true },
  { say = "Rolling dialogue underneath." },
  { close = 3 },
]
"""
    assert _problems(tmp_path, toml) == []


def test_conductor_open_is_attributed_and_narration_open_is_not():
    from ff9mapkit.content import conductor as _conductor
    uids = {"zorn": 4}
    b, ti = _conductor._emit_sequential_step(
        0, {"actor": "zorn", "open": "x", "window": 2}, uids, [500], 0, 128, {})
    assert b == opcodes.window_async_ex(4, 2, 128, 500)
    assert ti == 1
    plain = _cutscene.compile_steps([{"open": "x", "window": 2}], [500])
    assert plain == opcodes.window_async(2, 128, 500)


def test_every_window_verb_emits_its_opcode():
    got = _cutscene.compile_steps(
        [{"close": 2}, {"wait_window": 3}, {"raise": True}, {"set_signal": 4}], [])
    assert got == (opcodes.close_window(2) + opcodes.wait_window(3)
                   + opcodes.raise_windows() + opcodes.set_dialog_progression(4))


# --- the window ledger -------------------------------------------------------------------------

def test_a_held_window_that_is_never_closed_is_refused(tmp_path):
    toml = BASE + """
[[cutscene]]
steps = [
  { open = "You cannot dismiss me.", window = 2, hold = true },
  { wait = 60 },
]
"""
    assert any("hold = true on window 2 is never closed" in p for p in _problems(tmp_path, toml))


def test_an_unclosed_window_is_refused(tmp_path):
    toml = BASE + """
[[cutscene]]
steps = [
  { open = "I outlive the scene.", window = 2 },
  { wait = 60 },
]
"""
    assert any("opened and never closed" in p for p in _problems(tmp_path, toml))


def test_wait_window_counts_as_closing_it(tmp_path):
    toml = BASE + """
[[cutscene]]
steps = [
  { open = "Dismiss me.", window = 2 },
  { wait_window = 2 },
]
"""
    assert _problems(tmp_path, toml) == []


def test_reissuing_a_window_id_is_not_a_double_leak(tmp_path):
    # replace-in-place is stock's HUD-refresh idiom; only the FINAL open is outstanding
    toml = BASE + """
[[cutscene]]
steps = [
  { open = "one", window = 6 },
  { open = "two", window = 6 },
  { close = 6 },
]
"""
    assert _problems(tmp_path, toml) == []


def test_a_stray_close_is_reported(tmp_path):
    toml = BASE + """
[[cutscene]]
steps = [
  { say = "hi" },
  { close = 6 },
]
"""
    assert any("never opens window 6" in p for p in _problems(tmp_path, toml))


def test_a_signal_wait_with_no_source_is_reported(tmp_path):
    toml = BASE + """
[[cutscene]]
steps = [
  { open = "no tag on me", window = 2 },
  { wait_signal = 1 },
  { close = 2 },
]
"""
    assert any("no line in this scene carries a `signal` tag" in p
               for p in _problems(tmp_path, toml))


def test_a_signal_wait_beyond_reach_is_reported(tmp_path):
    toml = BASE + """
[[cutscene]]
steps = [
  { open = "a", window = 2, signal = "+", hold = true },
  { wait_signal = 3 },
  { close = 2 },
]
"""
    assert any("only reach 1" in p for p in _problems(tmp_path, toml))


def test_the_trailing_cleanup_does_not_read_as_a_missing_source(tmp_path):
    # stock re-zeroes the signal AFTER each handshake; counting that against the wait would flag every
    # correctly-written scene (it did, until the reach was scoped to the steps BEFORE the wait)
    assert _problems(tmp_path, UNISON) == []


def test_an_unheld_window_across_a_blocking_say_is_refused(tmp_path):
    """★ THE BROADCAST-CONFIRM LAW (bench 30603 round 1 -- this exact toml shipped, linted clean, and
    the hint vanished on the first Action press). DialogManager.OnKeyConfirm:335-341 delivers a confirm
    to EVERY active dialog; each closes itself unless `ignoreInputFlag` is set, and that field IS
    `FlagButtonInh`, written only by the [TIME] and [NFOC] tags. So an unheld async window cannot
    survive any other window's dismissal."""
    toml = BASE + """
[[cutscene]]
steps = [
  { open = "a hint", window = 3, style = "transparent" },
  { say = "the press that advances me also kills the hint" },
  { close = 3 },
]
"""
    probs = _problems(tmp_path, toml)
    assert any("window 3 (opened at step 0) is still up" in p and "EVERY open window" in p
               for p in probs)


def test_holding_it_is_what_makes_that_legal(tmp_path):
    toml = BASE + """
[[cutscene]]
steps = [
  { open = "a hint", window = 3, style = "transparent", hold = true },
  { say = "I advance; the hint stays." },
  { close = 3 },
]
"""
    assert _problems(tmp_path, toml) == []


def test_the_window_being_waited_on_may_itself_be_unheld(tmp_path):
    # `open` + `wait_window` on the SAME id is the async twin of `say` -- the player is supposed to
    # dismiss it, so the law must not fire on the very window the wait is for
    toml = BASE + """
[[cutscene]]
steps = [
  { open = "dismiss me", window = 2 },
  { wait_window = 2 },
]
"""
    assert _problems(tmp_path, toml) == []


def test_hold_plus_wait_window_on_the_same_id_is_refused(tmp_path):
    # the deadlock the law's own fix would otherwise invite: a held window cannot be dismissed, so a
    # wait_window on it never returns
    toml = BASE + """
[[cutscene]]
steps = [
  { open = "you cannot dismiss me", window = 2, hold = true },
  { wait_window = 2 },
]
"""
    assert any("HANGS" in p for p in _problems(tmp_path, toml))


def test_hold_with_duration_is_refused(tmp_path):
    toml = BASE + """
[[cutscene]]
steps = [
  { open = "x", window = 2, hold = true, duration = 90 },
  { close = 2 },
]
"""
    assert any("same engine tag with opposite meanings" in p for p in _problems(tmp_path, toml))


def test_a_bad_signal_value_is_refused(tmp_path):
    toml = BASE + """
[[cutscene]]
steps = [
  { open = "x", window = 2, signal = "yes" },
  { close = 2 },
]
"""
    assert any("signal must be" in p for p in _problems(tmp_path, toml))


def test_a_bad_timeout_is_refused(tmp_path):
    toml = BASE + """
[[cutscene]]
steps = [
  { open = "x", window = 2, signal = "+" },
  { wait_signal = 1, timeout = 0 },
  { close = 2 },
]
"""
    assert any("positive frame count" in p for p in _problems(tmp_path, toml))
