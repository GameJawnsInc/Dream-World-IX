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


def test_speak_body_is_window_then_branch_then_return():
    out = choice.speak_body(500, [b"\xAA", b""])
    assert out.startswith(opcodes.window_sync(1, 128, 500))     # the prompt window opens first
    assert out.endswith(opcodes.RETURN)                          # and the speak func returns
    assert region.cond_sysvar_eq(9, 0) in out                    # branching on the pick


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
