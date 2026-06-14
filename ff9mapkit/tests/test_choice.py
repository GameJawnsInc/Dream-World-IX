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


def test_warp_entrance_sets_field_entrance():
    # a choice warp with an entrance writes the arrival-entrance var (D8:2) before the Field().
    assert event.warp(6200) == opcodes.run_sound_code(265, 65535) + opcodes.field(6200)   # bare: unchanged
    assert event.warp(6200, entrance=3) == region.set_field_entrance(3) + event.warp(6200)
    assert region.set_field_entrance(2) in choice.option_body({"warp": 6200, "entrance": 2})
    assert region.set_field_entrance(0) not in choice.option_body({"warp": 6200})           # no key -> no write


def test_warp_fade_prepends_proven_fadeout():
    # fade=True prepends the proven transition fade-out (FadeFilter SUB->white = fade to BLACK, then
    # Wait(25)) so the destination loads black and its camera-init frames are hidden -- the fix for the
    # World-Hub static-screen-on-spawn bug. Byte-identical to what content.ladder emits for a Field() top.
    fade = opcodes.fade_filter(6, 24, 0, 255, 255, 255) + opcodes.wait(25)
    assert event.warp(6200, fade=True) == fade + opcodes.run_sound_code(265, 65535) + opcodes.field(6200)
    assert event.warp(6200, fade=False) == event.warp(6200)                          # default off = bare
    assert event.warp(6200, entrance=3, fade=True) == fade + region.set_field_entrance(3) \
        + opcodes.run_sound_code(265, 65535) + opcodes.field(6200)                    # fade, THEN entrance


def test_choice_warp_always_fades_out():
    # a choice option that warps is a field transition -> it always fades out first (no static screen).
    fade = opcodes.fade_filter(6, 24, 0, 255, 255, 255) + opcodes.wait(25)
    assert choice.option_body({"warp": 6200}).startswith(fade)
    assert region.set_field_entrance(2) in choice.option_body({"warp": 6200, "entrance": 2})


def test_instant_choice_appends_imme_tag(tmp_path):
    # [[choice]] instant=true appends FF9's [IMME] tag so the menu pops fully drawn (no type-on), like the
    # Treno Weapon Shop's "What can I do for you?" Buy/Sell menu. Default (no instant) stays byte-identical.
    from ff9mapkit.build import FieldProject, collect_text
    base = {"field": {"id": 4500, "name": "X"}, "npc": [{"name": "Narr"}],
            "choice": [{"npc": "Narr", "prompt": "Pick?", "options": [{"text": "A"}, {"text": "B"}]}]}
    mes_plain = collect_text(FieldProject(base, tmp_path))[0]
    assert "[CHOO]" in mes_plain and "[IMME]" not in mes_plain        # default: types out, no [IMME]
    base_i = {**base, "choice": [{**base["choice"][0], "instant": True}]}
    mes_imme = collect_text(FieldProject(base_i, tmp_path))[0]
    assert "[IMME]" in mes_imme and "[CHOO]" in mes_imme              # instant: [IMME] appended


def test_option_body_remove_item_trade():
    # a trade option: give one item, take another (order: give_item -> remove_item per option_body)
    out = choice.option_body({"give_item": ["Potion", 1], "remove_item": ["Dagger", 1]}, None)
    assert out == event.give_item("Potion", 1) + event.take_item("Dagger", 1)
    assert opcodes.remove_item(1, 1) in out


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


# --------------------------------------------------------- v2: flag-gated (dynamic) hide

def test_region_or_var_and_var_expr_bytes():
    # VAR |= value  ->  05 <var> 7D <i16> 3F 7F  (B_OR_LET = 0x3F; real-field verified, Dali/Storage 407)
    assert region.or_var(region.GLOB_BOOL, 5, 2) == (bytes([0x05]) + region._push_var(region.GLOB_BOOL, 5)
                                                     + bytes([0x7D, 0x02, 0x00, 0x3F, 0x7F]))
    # bare var expression-arg: <var> 7F  (no leading 0x05 statement byte)
    assert region.var_expr(region.GLOB_BOOL, 5) == region._push_var(region.GLOB_BOOL, 5) + bytes([0x7F])
    assert region.GLOB_UINT16 == 0xDC                            # Global + UInt16


def test_dynamic_mask_setup_builds_then_passes_expression():
    from ff9mapkit.eb import disasm
    opts = [{"text": "Buy"}, {"text": "Use key", "requires_flag": 8001}, {"text": "Leave"}]
    setup = choice.dynamic_mask_setup(opts, default=0)
    sc = region.MASK_SCRATCH_IDX
    assert region.set_var(region.GLOB_UINT16, sc, 0b101) in setup     # base = rows 0,2 always on
    assert region.if_block(region.cond_truthy(region.GLOB_BOOL, 8001),
                           region.or_var(region.GLOB_UINT16, sc, 1 << 1)) in setup   # row 1 ORs bit on flag set
    ins = [i for i in disasm.iter_code(setup, 0, len(setup)) if i.op == 0x7C]
    assert ins and ins[-1].arg_is_expr[0] is True                    # mask passed as an EXPRESSION, not literal


def test_pre_choose_flag_gated_uses_dynamic_mask_and_pchm():
    ch = {"options": [{"text": "Buy"}, {"text": "Use key", "requires_flag": 8001}, {"text": "Leave"}]}
    setup, tag = choice.pre_choose(ch)
    assert tag == "[PCHM=3,2]"                                       # masked menu, cancel = last
    assert setup == choice.dynamic_mask_setup(ch["options"], 0)


def test_pre_choose_requires_flag_clear_uses_not_condition():
    ch = {"options": [{"text": "A"}, {"text": "Secret", "requires_flag_clear": 8005}]}
    setup, _ = choice.pre_choose(ch)
    # row 1 shows only while flag 8005 is CLEAR -> cond_not gate around its or_var
    assert region.if_block(region.cond_not(region.GLOB_BOOL, 8005),
                           region.or_var(region.GLOB_UINT16, region.MASK_SCRATCH_IDX, 1 << 1)) in setup
