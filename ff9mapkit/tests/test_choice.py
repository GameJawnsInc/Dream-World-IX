"""Dialogue choices -- the expression sysvar primitive + the choice script builder (pure byte tests,
no game data). Grounded in the engine: ``GetSysvar(9) == ETb.GetChoose()`` (the picked row); the
expression read token is ``B_SYSVAR`` (0x7A); the prompt window is ``WindowSync`` (0x1F). The in-game
NPC-talk integration (``inject_npc(speak_body=...)``) lives in test_content.py (needs the blank field).
"""

from __future__ import annotations

from ff9mapkit.content import choice, event, region
from ff9mapkit.eb import opcodes


def test_push_sysvar_and_choice_cond_bytes():
    assert region.push_sysvar(9) == bytes([0x7A, 0x09])
    assert region.SYSVAR_CHOICE == 9
    # 05 7A 09 7D <val:i16> 20 7F  ==  if (GetSysvar(9) == val)
    assert region.cond_sysvar_eq(9, 0) == bytes([0x05, 0x7A, 0x09, 0x7D, 0x00, 0x00, 0x20, 0x7F])
    assert region.cond_sysvar_eq(9, 1) == bytes([0x05, 0x7A, 0x09, 0x7D, 0x01, 0x00, 0x20, 0x7F])


def test_branch_is_one_if_block_per_option():
    out = choice.branch([b"\xAA", b"\xBB"])
    assert out == (region.if_block(region.cond_sysvar_eq(9, 0), b"\xAA")
                   + region.if_block(region.cond_sysvar_eq(9, 1), b"\xBB"))


def test_branch_skips_options_with_no_actions():
    # option 0 has an empty body -> no block emitted; option 1 keyed on choice index 1
    assert choice.branch([b"", b"\xCC"]) == region.if_block(region.cond_sysvar_eq(9, 1), b"\xCC")


def test_speak_body_locks_movement_window_branch_unlock_return():
    out = choice.speak_body(500, [b"\xAA", b""])
    assert out.startswith(opcodes.DISABLE_MOVE)                  # lock the player first (no walking)
    assert opcodes.window_sync(1, 128, 500) in out              # the prompt window
    assert out.endswith(opcodes.ENABLE_MOVE + opcodes.RETURN)   # restore control, then return
    assert region.cond_sysvar_eq(9, 0) in out                    # branching on the pick


def test_region_body_is_speak_body_without_return():
    rb = choice.region_body(500, [b"\xAA"])
    assert rb.startswith(opcodes.DISABLE_MOVE) and rb.endswith(opcodes.ENABLE_MOVE)   # no RETURN
    assert choice.speak_body(500, [b"\xAA"]) == rb + opcodes.RETURN                    # speak = body + RETURN


def test_option_body_action_order_reply_item_gil_flag():
    opt = {"give_item": [232, 1], "gil": 50, "set_flag": [8000, 1]}
    out = choice.option_body(opt, reply_txid=501)
    assert out == (event.message(501) + event.give_item(232, 1) + event.give_gil(50)
                   + event.set_flag(8000, 1))


def test_option_body_empty_when_no_actions():
    assert choice.option_body({"text": "No"}, reply_txid=None) == b""


def test_gil_is_signed_add_or_remove():
    # gil >= 0 -> AddGil (0xCE); gil < 0 -> RemoveGil (0xCF). A negative must NOT wrap to a huge add.
    assert event.give_gil(100) == opcodes.add_gil(100)
    assert event.give_gil(-100) == opcodes.remove_gil(100)
    assert opcodes.remove_gil(100) in choice.option_body({"gil": -100}, None)
    assert opcodes.add_gil(100) in choice.option_body({"gil": 100}, None)


# --------------------------------------------------------------------- pre-choose (default/cancel/disable)

def test_enable_dialog_choices_literal_bytes_and_roundtrip():
    from ff9mapkit.eb import disasm
    # [op 7C][argFlag 00 = all literal][avail mask : 2 LE][default : 1].  mask 0b101 = rows 0,2 on / 1 off
    b = opcodes.enable_dialog_choices(0b101, 1)
    assert b == bytes([0x7C, 0x00, 0x05, 0x00, 0x01])
    ins = list(disasm.iter_code(b, 0, len(b)))
    assert len(ins) == 1 and ins[0].op == 0x7C and ins[0].length == 5 and list(ins[0].args) == [5, 1]
    assert opcodes.enable_dialog_choices(0xFFFF, 0) == bytes([0x7C, 0x00, 0xFF, 0xFF, 0x00])  # all on


def test_pre_choose_empty_when_unconfigured():
    # a plain choice (no default/cancel/disabled) emits nothing -> byte-identical to the old layout
    assert choice.pre_choose({"options": [{"text": "A"}, {"text": "B"}]}) == (b"", "")


def test_pre_choose_default_cancel_uses_pchc():
    ch = {"options": [{"text": "A"}, {"text": "B"}, {"text": "C"}], "default": 2, "cancel": 0}
    setup, tag = choice.pre_choose(ch)
    assert tag == "[PCHC=3,0]"                                   # count=3, cancel row 0
    # all-on mask = (1<<3)-1 = 0b111, NOT 0xFFFF (which sign-extends to -1 and breaks SetChooseParam)
    assert setup == opcodes.enable_dialog_choices(0b111, 2)


def test_pre_choose_cancel_defaults_to_last_row():
    _, tag = choice.pre_choose({"options": [{"text": "A"}, {"text": "B"}], "default": 1})
    assert tag == "[PCHC=2,1]"                                   # cancel omitted -> last row (index 1)


def test_pre_choose_disabled_uses_pchm_and_clears_bit():
    ch = {"options": [{"text": "A"}, {"text": "B", "disabled": True}, {"text": "C"}]}
    setup, tag = choice.pre_choose(ch)
    assert tag == "[PCHM=3,2]"                                   # PCHM applies the mask; cancel = last
    assert setup == opcodes.enable_dialog_choices(0b101, 0)      # row 1 disabled -> bit 1 clear


def test_pre_choose_all_on_mask_is_positive():
    # regression: a -1/0xFFFF availability mask makes ETb.SetChooseParam's `while availMask>0` loop
    # never run, so the default collapses to 0. The all-on mask must be (1<<n)-1 (positive as i16).
    for n in (2, 3, 5, 8):
        setup, _ = choice.pre_choose({"options": [{"text": str(i)} for i in range(n)], "default": n - 1})
        assert setup == opcodes.enable_dialog_choices((1 << n) - 1, n - 1)
        mask_le = setup[2] | (setup[3] << 8)                     # [op][flag][mask_lo][mask_hi][default]
        assert 0 < mask_le < 0x8000                              # positive as a signed 16-bit value


def test_pre_choose_setup_runs_after_lock_before_window():
    setup, _ = choice.pre_choose({"options": [{"text": "A"}, {"text": "B"}], "default": 1})
    body = choice.speak_body(500, [b"\xAA", b""], setup=setup)
    assert setup and setup in body
    assert body.index(opcodes.DISABLE_MOVE) < body.index(setup) < body.index(opcodes.window_sync(1, 128, 500))
