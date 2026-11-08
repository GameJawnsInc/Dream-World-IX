"""[ff9mapkit netsync s168] THE GUEST'S MAIN MENU, RUNG 0 (view only) -- THE KIT CORE (studies/field-coop/S168-DESIGN.md decisions 1-21 and
31-36): battlewire's twins of every s168 rule and constant the bench reads or decodes, pinned to the ENGINE's source BY STAGE; fakegame's opt-in
`guestmenu` rung; coop_peer's b3 adoption and its section-12 decoder.

  * THE TWINS (pure): every rule's truth table, the section-12 codec, the predicate's 23 terms in order, the close machine, the words, the
    fingerprint's hash -- and a one-line mutant of each key twin fails ITS OWN row.
  * THE ENGINE PINS, by stage: an s168 patch on this branch's stack, else a clone named by FF9_S168_CLONE carrying the s168 tag; else (the
    deployed s167 stage) each pin SKIPS. Constants, the closed sets' order, the words, the usage / refusal / ack literals, the catch
    literal's `guestmenu` at BW.GUEST_MENU_SENTINELS, AppendGuestMenu's key order, the proof tallies DERIVED from the source (420 / 249,
    19 / 7, 534 / 198) -- and THE PROOF'S OWN ROWS: every single-expression row whose names the namespace holds is EVALUATED against the
    twins (the _run_cs_rows pattern; block-lambda rows and rows over probe builders, seats, facts or byte arrays are skipped -- the twin
    truth tables cover those), so a row's arguments or verdict changed on either side turns a test red.
  * THE STAND-IN (guest_menu_stand_in; the default stays the deployed s167): the key in the agent's order, the press / door / seat / census /
    restore / close on the selftest bench and on a client, the levers and their release, the proof block -- and every GUEST_MENU_FAULTS
    fault turns ITS row red.
  * COOP_PEER: serve-guest's auto caps adopt b3 from an s168 host (0x000B), `--caps 3` an s167-shaped guest; section 12 decoded in the dump,
    `where --pose` and a tape census; replay-host carries a v15 tape's section 12 as recorded.
"""
import json
import os
import pathlib
import re
import sys
import tempfile

import pytest

from ._patchstack import msr

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from harness import battlewire as BW                                   # noqa: E402
from harness import coop_peer as CP                                    # noqa: E402
from harness import fakegame as FG                                     # noqa: E402
from harness.fakegame import FakeGame                                  # noqa: E402

S168_TAG = FG.S168_TAG
S168_CLONE_ENV = FG.S168_CLONE_ENV
_LIT = re.compile(r'"((?:[^"\\]|\\.)*)"')
FLD, WLD, MEN, ITM, BTL, PAU = "FieldHUD", "WorldHUD", "MainMenu", "Item", "BattleHUD", "Pause"


# ================================================================================================ THE TWINS (pure)
def test_the_caps_word_by_stage_and_the_two_argument_rule():
    """decision 2: `fp off` speaks s166's 0x0001 whatever the menu lever says; s167's 0x0003 = menu_off True; s168's 0x000B."""
    assert [BW.ww_own_caps_rule(fp, menu) for fp in (False, True) for menu in (False, True)] == [0x0B, 0x03, 0x01, 0x01]
    assert BW.WW_CAP_GUEST_MENU == 0x08 and BW.CAPS_S168 == BW.WW_OWN_CAPS_MENU == 0x0B and BW.CAPS_S167 == 0x03
    assert [BW.ww_own_caps_by_stage(s) for s in (165, 166, 167, 168)] == [1, 1, 3, 0x0B]
    assert BW.ww_own_caps_by_stage(168, menu_off=True) == 3 and BW.ww_own_caps_by_stage(168, fp_off=True) == 1
    assert BW.ww_caps_line_text(0x0B, 0x03) == BW.CAPS_LINE_S168_VS_S167
    world = {"walk": {}, "fp": {"lever": "act"}}
    assert BW.ww_own_caps_want({"world": {}}) == 1 and BW.ww_own_caps_want({"world": world}) == 3
    assert BW.ww_own_caps_want({"world": world, "guestmenu": {"lever": {"caps": "on"}}}) == 0x0B
    assert BW.ww_own_caps_want({"world": world, "guestmenu": {"lever": {"caps": "off"}}}) == 3
    assert BW.ww_own_caps_want({"world": dict(world, fp={"lever": "off"})}) == 3          # `fp off` left on is never re-keyed: still a red


def _lazy(v):
    return lambda: v


def _boom():
    raise RuntimeError("probe fault")


#: decision 6's key step, the proof's own rows re-stated: (enable, old, session, mirroring, loading, pair_on, state, why) -> (verdict, why)
KEY_ROWS = [
    ((False, False, True, True, False, True, FLD, _boom), (BW.MENU_KEY_STOCK_OFF, None)),
    ((True, True, True, True, False, True, FLD, _boom), (BW.MENU_KEY_REFUSE_AUDIBLE, None)),         # `old`: s121 exactly
    ((True, True, True, False, False, True, FLD, _boom), (BW.MENU_KEY_OPEN, None)),                  # ...its unmirrored open
    ((True, False, False, False, False, True, FLD, _boom), (BW.MENU_KEY_OPEN, None)),                # vanilla: why never read
    ((True, False, True, True, False, True, FLD, None), (BW.MENU_KEY_GUEST_OPEN, None)),
    ((True, False, True, True, False, True, FLD, BW.GM_WHY_HOST_BATTLE), (BW.MENU_KEY_REFUSE_AUDIBLE, BW.GM_WHY_HOST_BATTLE)),
    ((True, False, True, True, True, True, FLD, None), (BW.MENU_KEY_GUEST_QUIET, None)),             # a double tap inside the fade
    ((True, False, True, True, True, False, FLD, BW.GM_WHY_OLDER), (BW.MENU_KEY_REFUSE_AUDIBLE, BW.GM_WHY_OLDER)),   # W1: caps off
    ((True, False, True, True, False, True, BTL, _boom), (BW.MENU_KEY_REFUSE_SILENT, None)),         # s121's step off the HUD
    ((True, False, True, True, False, True, MEN, _boom), (BW.MENU_KEY_REFUSE_SILENT, None)),         # a press inside the open menu
    ((True, False, True, False, False, True, BTL, _boom), (BW.MENU_KEY_OPEN, None)),                 # the bench keeps s121's Open
    ((True, False, _boom, False, False, True, FLD, _boom), (BW.MENU_KEY_OPEN, None)),               # a fault before session: s121
    ((True, False, _boom, True, False, True, FLD, _boom), (BW.MENU_KEY_REFUSE_AUDIBLE, None)),
    ((True, False, True, True, False, True, FLD, _boom), (BW.MENU_KEY_REFUSE_AUDIBLE, BW.GM_WHY_FAULT)),   # inside the press: fail closed
    ((True, False, True, True, _boom, True, FLD, None), (BW.MENU_KEY_REFUSE_AUDIBLE, BW.GM_WHY_FAULT)),
]


def _key(row, step=BW.gm_key_step):
    en, old, ses, mi, lo, po, st, why = row
    return step(en, old, ses if callable(ses) else _lazy(ses), mi, lo if callable(lo) else _lazy(lo), po if callable(po) else _lazy(po), st,
                why if callable(why) else _lazy(why))


@pytest.mark.parametrize("row, want", KEY_ROWS, ids=[str(i) for i in range(len(KEY_ROWS))])
def test_the_key_step_reads_each_case(row, want):
    assert _key(row) == want


def test_each_key_step_mutant_fails_its_own_row():
    """The proof's mutants: no GuestQuiet (key_no_quiet), GuestQuiet caps-blind (W1's key_quiet_caps_blind), a fault that refuses outside a
    guest press, the why read eagerly -- each caught by the row beside it."""
    real = BW.gm_key_step

    def no_quiet(en, old, ses, mi, lo, po, st, why):
        return real(en, old, ses, mi, _lazy(False), po, st, why)

    def caps_blind(en, old, ses, mi, lo, po, st, why):
        return real(en, old, ses, mi, lo, _lazy(True), st, why)

    def fault_anywhere(en, old, ses, mi, lo, po, st, why):
        try:
            ses()
        except Exception:                                               # noqa: BLE001
            return BW.MENU_KEY_REFUSE_AUDIBLE, BW.GM_WHY_FAULT
        return real(en, old, ses, mi, lo, po, st, why)

    def eager(en, old, ses, mi, lo, po, st, why):
        w = why()
        return real(en, old, ses, mi, lo, po, st, _lazy(w))

    for mutant, row in ((no_quiet, 6), (caps_blind, 7), (fault_anywhere, 11), (eager, 3)):
        try:
            got = _key(KEY_ROWS[row][0], mutant)
        except Exception:                                               # noqa: BLE001 -- a raising mutant fails its row too
            got = "raised"
        assert got != KEY_ROWS[row][1], (mutant.__name__, row)


def test_the_press_act_the_effects_and_the_names():
    assert BW.gm_press_act_rule(BW.MENU_KEY_OPEN, None) == BW.GM_PA_STOCK
    assert BW.gm_press_act_rule(BW.MENU_KEY_GUEST_OPEN, None) == BW.GM_PA_STOCK | BW.GM_PA_DEADLINE
    assert BW.gm_press_act_rule(BW.MENU_KEY_GUEST_QUIET, None) == BW.GM_PA_STOCK
    assert BW.gm_press_act_rule(BW.MENU_KEY_REFUSE_AUDIBLE, BW.GM_WHY_LINK) == BW.GM_PA_REFUSE_GIVEN
    assert BW.gm_press_act_rule(BW.MENU_KEY_REFUSE_AUDIBLE, None) == BW.gm_press_act_rule(BW.MENU_KEY_REFUSE_SILENT, None) == BW.GM_PA_REFUSE_S121
    assert BW.gm_press_act_rule(BW.MENU_KEY_STOCK_OFF, None) == 0
    full = BW.GM_EFF_BUZZ | BW.GM_EFF_COUNT | BW.GM_EFF_LINE
    assert BW.gm_refuse_effect_rule(BW.MENU_KEY_REFUSE_AUDIBLE, True, False, FLD) == full     # the bench counts (never s121 re-run)
    assert BW.gm_refuse_effect_rule(BW.MENU_KEY_REFUSE_SILENT, True, True, BTL) == BW.GM_EFF_SILENT
    assert all(BW.gm_refuse_effect_rule(v, True, True, FLD) == 0 for v in (BW.MENU_KEY_GUEST_OPEN, BW.MENU_KEY_GUEST_QUIET, BW.MENU_KEY_OPEN))
    assert BW.menu_key_name_s168(BW.MENU_KEY_GUEST_OPEN) == BW.menu_key_name_s168(BW.MENU_KEY_GUEST_QUIET) == "guest"
    assert BW.menu_key_name_s168(BW.MENU_KEY_REFUSE_AUDIBLE) == "audible" and BW.menu_key_name(BW.MENU_KEY_GUEST_OPEN) is None
    assert BW.gm_guest_key_name(BW.MENU_KEY_GUEST_QUIET) == "guest" and BW.gm_guest_key_name(BW.MENU_KEY_OPEN) is None
    assert BW.gm_guest_session_rule(True, False, False, False) and not BW.gm_guest_session_rule(False, False, False, True)


def _host_trailer(caps=BW.CAPS_S168, place=BW.WW_PLACE_FIELD, world=0):
    return BW.ww_trailer(has=True, fmt=1, caps=caps, place=place, world=world, flags=BW.WW_FLAG_FOLLOW)


def _open_field(**kw):
    """The proof's OpenField: a mirroring guest on a field with a b3 host there, every term open."""
    f = BW.gm_facts(mirroring=True, session_held=True, own_caps=BW.CAPS_S168, latest=_host_trailer(), live=True,
                    host_dlg_flags=BW.HF_CONTROL | BW.HF_ON_FIELD, menu_data=True, witness_ok=True, control=True, my_field=100, my_world=9011,
                    last_host_field=100)
    f["close"].update(client_role=True, host_dlg_flags=f["host_dlg_flags"])
    f.update(kw)
    return f


def _open_world(**kw):
    f = _open_field(world=True, latest=_host_trailer(place=BW.WW_PLACE_WORLD, world=9011), host_dlg_flags=BW.HF_CONTROL | BW.HF_WORLD,
                    on_world_now=True, block_ready=True, ui_world_hud=True, hud_plain=True, host_field=-1, last_host_field=-1)
    f.update(kw)
    return f


#: decision 8, one row per term in its order: (the facts, the why)
WHY_ROWS = [
    (_open_field(), None), (_open_world(), None),
    (_open_field(old=True), BW.GM_WHY_LEVER),
    (_open_field(mirroring=False), BW.GM_WHY_NOT_MIRRORING),
    (_open_field(session_held=False), BW.GM_WHY_SESSION),
    (_open_field(bench=True, mirroring=False, session_held=False), None),
    (_open_field(latest=_host_trailer(caps=BW.CAPS_S167)), BW.GM_WHY_OLDER),
    (_open_field(own_caps=BW.CAPS_S167), BW.GM_WHY_OLDER),
    (_open_field(live=False), BW.GM_WHY_LINK),
    (_open_field(latest=_host_trailer(place=BW.WW_PLACE_TRANSITION)), BW.GM_WHY_HOST_BUSY),
    (_open_field(host_dlg_flags=BW.HF_BATTLE), BW.GM_WHY_HOST_BATTLE),
    (_open_field(menu_data=False), BW.GM_WHY_NO_DATA),
    (_open_field(witness_ok=False), BW.GM_WHY_DATA_DIFFERS),
    (_open_field(control=False), BW.GM_WHY_CONTROL),
    (_open_field(busy_why="follow"), BW.GM_WHY_BUSY),
    (_open_field(etb_line=True), BW.GM_WHY_UI),
    (_open_field(dialogs_visible=True), None),                          # never Dialogs.Visible
    (_open_field(last_host_field=200), BW.GM_WHY_HOST_ELSEWHERE),
    (_open_field(intent_unseen=True, intent_dest=200), BW.GM_WHY_LEAVING),
    (_open_field(intent_unseen=True, intent_dest=BW.FLDSCRPT_EVTNO_ENDING), None),   # the ending's pseudo-field never refuses
    (_open_field(host_scene_why="talk"), BW.GM_WHY_SCENE),
    (_open_field(gl_scene_field=100, gl_host_holds_input=True), BW.GM_WHY_SCENE),
    (_open_world(hud_plain=False), BW.GM_WHY_WORLD_BUSY),
    (_open_world(char_state_index=1), BW.GM_WHY_RIDING),
    (_open_world(navi_mode=2), BW.GM_WHY_WORLD_BUSY),
    (_open_world(world_out_pending=3), BW.GM_WHY_MOVE),
    (_open_world(host_field=300), BW.GM_WHY_LEAVING),
    (_open_world(latest=_host_trailer(place=BW.WW_PLACE_WORLD, world=9010)), BW.GM_WHY_LEAVING),
    (_open_world(latest=dict(_host_trailer(place=BW.WW_PLACE_WORLD, world=9011), state=BW.WW_ST_SCENE)), BW.GM_WHY_SCENE),
    (_open_world(last_host_field=200, host_scene_why="talk"), None),   # the field's terms read only their own place
]


@pytest.mark.parametrize("facts, why", WHY_ROWS, ids=[str(i) for i in range(len(WHY_ROWS))])
def test_the_predicate_reads_each_term_in_its_order(facts, why):
    assert BW.gm_why_not(facts) == why


def test_the_predicate_s_order_and_its_deletion_mutants():
    """23 terms in decision 8's order; deleting one term turns its row from its why to the next (or open)."""
    assert BW.GM_TERM_NAMES[:12] == ("lever", "who", "caps", "live", "host_place", "host_battle", "menu_data", "witness", "control", "busy",
                                     "open_mirror", "ui_quiet") and len(BW.GM_TERMS) == 23
    assert BW.gm_why_not(_open_field(old=True, mirroring=False)) == BW.GM_WHY_LEVER
    assert BW.gm_why_not(_open_field(mirroring=False, own_caps=BW.CAPS_S167)) == BW.GM_WHY_NOT_MIRRORING   # who before caps
    for name, (facts, why) in (("who", WHY_ROWS[3]), ("caps", WHY_ROWS[6]), ("live", WHY_ROWS[8]), ("menu_data", WHY_ROWS[11]),
                               ("f1", WHY_ROWS[17]), ("wt3", WHY_ROWS[23])):
        cut = tuple(t for t in BW.GM_TERMS if t[0] != name)
        assert BW.gm_why_not(facts, cut) != why, name
    c = BW.gm_close_facts(leave_intent=True)
    assert BW.gm_why_not(_open_field(close=c)) == BW.GM_WHY_LEAVING      # THE OPEN MIRROR


def test_the_close_triggers_the_request_and_the_cut_memory():
    trailer = _host_trailer(place=BW.WW_PLACE_WORLD, world=9010)
    cases = {BW.GM_CAUSE_LEAVE: BW.gm_close_facts(serial_due=True), BW.GM_CAUSE_OUT: BW.gm_close_facts(host_world_out=True),
             BW.GM_CAUSE_REJOIN: BW.gm_close_facts(rejoin_due=True), BW.GM_CAUSE_WORLD: BW.gm_close_facts(client_role=True),
             BW.GM_CAUSE_CUT: BW.gm_close_facts(battle_nonce=3), BW.GM_CAUSE_ENDING: BW.gm_close_facts(ramp_pending=True),
             BW.GM_CAUSE_TITLE: BW.gm_close_facts(host_dlg_flags=BW.HF_TITLE), BW.GM_CAUSE_SCENE: BW.gm_close_facts(ate_here=True)}
    for cause, c in cases.items():
        assert BW.gm_close_cause_rule(c, trailer, 9011) == cause, cause
        assert BW.gm_open_mirror_why(cause) is not None
    assert not BW.gm_trigger_fires(BW.GM_CAUSE_CUT, BW.gm_close_facts(battle_nonce=3, closed_nonce=3), trailer, 9011)
    assert not BW.gm_trigger_fires(BW.GM_CAUSE_WORLD, BW.gm_close_facts(client_role=True), trailer, 9010)
    assert BW.gm_close_cause_rule(BW.gm_close_facts(), trailer, 9011) == BW.GM_CAUSE_NONE
    assert BW.GM_CLOSE_IDS == ("leave", "out", "rejoin", "world", "cut", "ending", "title", "scene")
    assert [BW.gm_cause_index_rule(n) for n in BW.GM_CLOSE_IDS] == list(range(1, 9)) and BW.gm_cause_index_rule("x") == 0
    assert BW.gm_close_request_rule(True, False, BW.GM_CAUSE_CUT, ITM) and not BW.gm_close_request_rule(False, False, BW.GM_CAUSE_CUT, PAU)
    assert not BW.gm_close_request_rule(True, True, BW.GM_CAUSE_SCENE, ITM) and not BW.gm_close_request_rule(True, False, 0, MEN)
    # LC1: a boundary forgets; a different live nonce spends; staleness keeps
    assert BW.gm_cut_memory_rule(5, 5, True) == -1 and BW.gm_cut_memory_rule(5, 6, False) == -1
    assert BW.gm_cut_memory_rule(5, 5, False) == 5 and BW.gm_cut_memory_rule(5, -1, False) == 5
    never_forgets = lambda c, live, b: -1 if live >= 0 and c >= 0 and live != c else c                  # noqa: E731
    assert never_forgets(5, 5, True) != BW.gm_cut_memory_rule(5, 5, True)
    rec = BW.gm_close_record()
    assert BW.gm_request_close_over(rec, True, False, BW.GM_CAUSE_LEAVE, -1, MEN, 7, False, 300, 1000) == BW.GM_RQ_NEW
    assert rec["deadline"] == 2100 and rec["held"]
    assert BW.gm_request_close_over(rec, True, False, BW.GM_CAUSE_CUT, 9, MEN, 7, False, 300, 1100) == BW.GM_RQ_HELD and rec["cut_nonce"] == 9
    assert rec["cause"] == BW.GM_CAUSE_LEAVE                            # idempotent: the first cause stands
    assert BW.gm_request_close_over(BW.gm_close_record(), False, False, BW.GM_CAUSE_LEAVE, -1, PAU, 7, False, 300, 0) == BW.GM_RQ_NONE


def test_the_close_order_law_the_watchdog_and_the_deadlines():
    s = BW.gm_close_step_rule
    assert s(True, True, True, MEN, False, False) == BW.GM_CS_WAIT_QUIT and s(False, True, False, MEN, False, False) == BW.GM_CS_WAIT_LOADING
    assert s(False, False, True, ITM, False, False) == BW.GM_CS_PANEL_OFF and s(False, False, False, MEN, False, False) == BW.GM_CS_HIDE_ROOT
    assert s(False, False, False, "Folklore", False, False) == BW.GM_CS_HIDE_SUB and s(False, False, False, ITM, True, False) == BW.GM_CS_WAIT_HIDE
    assert s(False, False, False, FLD, True, False) == BW.GM_CS_WAIT_SHOW and s(False, False, False, FLD, True, True) == BW.GM_CS_DONE
    assert s(False, False, False, FLD, False, False) == BW.GM_CS_END
    assert BW.GM_CLOSE_STEP_NAMES[1:] == ("quit", "loading", "panel", "root", "sub", "hide", "show", "done", "end")
    assert [BW.gm_close_fault_step_rule(n) for n in BW.GM_CLOSE_FAULT_STEPS] == list(range(1, 8)) and BW.gm_close_fault_step_rule("done") == -1
    assert BW.gm_fade_ms_rule(0.3, False, 3) == 300 and BW.gm_fade_ms_rule(0.3, True, 3) == 100 and BW.gm_fade_ms_rule(9, False, 1) == 5000
    assert BW.gm_fade_ms_rule(0.3, True, 0) == 300 and BW.gm_fade_ms_rule(-1, False, 1) == 0
    assert BW.gm_close_deadline_rule(300, False) == 2100 and BW.gm_close_deadline_rule(300, True) == 1800
    assert BW.gm_watchdog_clock_rule(100, 50, BW.GM_CS_WAIT_QUIT) == 100 and BW.gm_watchdog_clock_rule(100, 50, BW.GM_CS_WAIT_HIDE) == 150
    assert BW.gm_watchdog_act_rule(2099, 2100, MEN, True, False) == BW.GM_WD_WAIT
    assert BW.gm_watchdog_act_rule(2100, 2100, ITM, True, False) == BW.GM_WD_SWEEP
    assert BW.gm_watchdog_act_rule(2100, 2100, MEN, False, False) == BW.GM_WD_END
    assert BW.gm_watchdog_act_rule(2500, 2100, FLD, True, False) == BW.GM_WD_HUD_SHOW
    assert BW.gm_watchdog_act_rule(2500, 2100, FLD, True, True) == BW.GM_WD_DONE
    # decision 9: the press deadline outlives one fade past CloseCapMs (a CloseCapMs-alone bound would not)
    assert BW.gm_press_deadline_rule(1000, 2400) == 4900 and BW.gm_press_holds_rule(True, 4900, 4000)
    assert not BW.gm_press_holds_rule(True, 4900, 4900) and not BW.gm_press_holds_rule(False, 4900, 0)
    assert BW.gm_press_holds_rule(True, BW.gm_press_deadline_rule(2 ** 31 - 100, 300), 2 ** 31 - 50 - 2 ** 32)   # tick-wrap safe
    assert not BW.gm_ramp_settle_rule(True, True, True, False, False) and BW.gm_ramp_settle_rule(True, True, True, True, False)
    assert BW.gm_ramp_settle_rule(True, False, True, False, False) and not BW.gm_ramp_settle_rule(True, False, False, False, True)
    assert BW.gm_cut_ui_free_rule(False, True, False) and not BW.gm_cut_ui_free_rule(False, True, True)
    rec = BW.gm_close_record()
    BW.gm_request_close_over(rec, True, False, BW.GM_CAUSE_LEAVE, -1, ITM, 7, False, 40, 1000)
    assert BW.gm_close_drive_rule(rec, False, False, False, ITM, False, True, 1010) == BW.GM_CA_HIDE_SUB
    rec["hide_issued"] = True
    assert BW.gm_close_drive_rule(rec, True, False, False, ITM, False, True, 1020) == BW.GM_CA_WAIT          # the quit prompt waits
    assert BW.gm_close_drive_rule(rec, False, False, False, FLD, True, True, 1100) == BW.GM_CA_DONE
    assert BW.gm_close_drive_rule(rec, False, False, False, FLD, False, False, 1110) == BW.GM_CA_SCENE_END
    assert BW.gm_close_drive_rule(rec, False, False, False, ITM, False, True, 9000) == BW.GM_CA_WD_SWEEP
    assert BW.gm_held_bits_rule(True, False, True, False, 0x40, 0x20, 0x100, 0x200) == 0x140
    assert BW.gm_held_watch_step(0x40, 0, 0x40, 0x40) == (0, 0, 1) and BW.gm_held_watch_step(0x40, 0x40, 0x40, 0x40) == (0x40, 0x40, 0)


def test_the_doors_the_restore_and_the_sites():
    assert BW.gm_open_door_rule(FLD, MEN, MEN, True, False, BW.MENU_KEY_GUEST_OPEN) and BW.gm_open_door_rule(WLD, FLD, MEN, True, False, -1)
    assert not BW.gm_open_door_rule(FLD, MEN, MEN, False, False, -1) and not BW.gm_open_door_rule(FLD, MEN, MEN, True, True, 5)
    assert BW.gm_door_verdict_rule(True, False, None) == BW.GM_WHY_FAULT and BW.gm_door_verdict_rule(True, True, "busy") == "busy"
    assert BW.gm_door_seats_rule(True, None, -1) and not BW.gm_door_seats_rule(True, "busy", 5)
    assert BW.gm_door_reshow_rule(FLD, MEN) == FLD
    assert BW.gm_door_fault_rule(BW.GM_DOOR_HALF_OPEN, False) == BW.GM_DF_STOCK and BW.gm_door_fault_rule(BW.GM_DOOR_HALF_OPEN, True) == BW.GM_DF_REFUSE
    assert BW.gm_door_fault_rule(BW.GM_DOOR_HALF_RESTORE, True) == BW.GM_DF_KEEP_STOCK
    assert BW.gm_restore_door_rule(MEN, FLD, FLD) and BW.gm_restore_door_rule(ITM, MEN, WLD) and not BW.gm_restore_door_rule(MEN, FLD, ITM)
    assert BW.gm_door_half_rule(MEN, FLD, FLD, True, True, False) == BW.GM_DOOR_HALF_RESTORE
    assert BW.gm_door_half_rule(FLD, MEN, MEN, False, True, False) == BW.GM_DOOR_HALF_OPEN
    assert BW.gm_door_half_rule(FLD, MEN, MEN, True, False, True) == BW.GM_DOOR_HALF_OPEN       # a held record retries, guest or not
    assert BW.gm_door_half_rule(FLD, MEN, MEN, False, False, False) == BW.GM_DOOR_HALF_NONE
    assert BW.gm_door_open_step(True, False, True, False, _boom) == (BW.GM_DO_REFUSE, BW.GM_WHY_FAULT)
    assert BW.gm_door_open_step(True, False, False, False, _boom) == (BW.GM_DO_STOCK, None)
    assert BW.gm_door_open_step(False, True, True, False, _lazy(None)) == (BW.GM_DO_SEAT, None)
    assert BW.gm_door_open_step(False, True, True, True, _boom) == (BW.GM_DO_STOCK, None)
    assert BW.gm_restore_identity_rule(True, True, 5, 5) == BW.GM_RV_RESTORE and BW.gm_restore_identity_rule(True, True, 5, 6) == BW.GM_RV_DROP
    assert BW.gm_restore_identity_rule(False, True, 5, 5) == BW.GM_RV_NONE
    assert BW.gm_restore_end_rule(BW.GM_RV_RESTORE, 1) == BW.GM_RE_SUB_MENUS | BW.GM_RE_ALARM
    assert BW.gm_restore_end_rule(BW.GM_RV_DROP, 0) & BW.GM_RE_DROP_LINE
    assert [BW.gm_session_ends_rule(s) for s in range(1, 14)] == [True] * 10 + [False] * 3
    assert BW.gm_backstop_line_rule(BW.GM_SITE_REPLACE_TITLE) == BW.gm_backstop_line_rule(BW.GM_SITE_RAMP_QUIT) == BW.GM_BL_QUIET
    assert BW.gm_backstop_line_rule(BW.GM_SITE_DOOR) == BW.GM_BL_PLAIN and BW.gm_backstop_line_rule(BW.GM_SITE_SCENE) == BW.GM_BL_ALARM
    assert BW.gm_close_ends_at_rule(BW.GM_SITE_LEVEL_LOADED) and not BW.gm_close_ends_at_rule(BW.GM_SITE_DOOR)
    assert BW.gm_boot_seat_rule(True, True) == BW.GM_BS_REFUSED | BW.GM_BS_WATCHING and BW.gm_boot_seat_rule(True, False) == BW.GM_BS_WATCHING
    assert BW.gm_autosave_ladder_rule(False, False, False, False, True) and not BW.gm_autosave_ladder_rule(False, False, False, False, False)
    assert BW.gm_site_name(99) == "site 99" and BW.gm_site_name(BW.GM_SITE_DOOR) == "the door"


def test_section_12_round_trips_and_refuses_what_the_reader_refuses():
    ms = [BW.gm_member(3, 3, 1, 1000, 23, list(range(48))), BW.gm_member(0, 0, 2, 2000, 21, [70000, -5]), None,
          BW.gm_member(1, 1, 3, 3000, 22, [])]
    body = BW.gm_write_menu_block(0, 0, 777777, [9, 70000, 14], ms)
    got = BW.gm_try_read_menu_block(body)
    assert got["gil"] == 777777 and got["used"] == [9, 14] and [m["char"] for m in got["members"]] == [3, 0, 1]
    assert got["members"][1]["pa"] == [65535, 0]                                         # clamped into a u16
    assert len(body) == BW.gm_menu_block_len(2, (48, 2, 0))
    for cut in range(len(body)):
        assert BW.gm_try_read_menu_block(body[:cut]) is None, cut                       # every truncation refuses
    assert BW.gm_try_read_menu_block(bytes([2]) + body[1:]) is None                     # an unknown fmt
    assert BW.gm_try_read_menu_block(body + b"\x99\x99") == got                          # an fmt-1 append is read past
    five = BW.gm_write_menu_block(0, 0, 1, [], [BW.gm_member(i, i, 1, 1, 1, []) for i in range(5)])
    assert len(BW.gm_try_read_menu_block(five)["members"]) == 4                          # the encoder writes MemberCap at most
    bad = bytearray(five)
    bad[9] = 5
    assert BW.gm_try_read_menu_block(bytes(bad)) is None                                 # memberN above MemberCap refuses
    frame = (BW.append_section(b"", BW.SECTION_KEY_ITEMS, bytes([2, 0, 9, 0, 14, 0]))
             + BW.append_section(b"", BW.SECTION_BAG, bytes([1, 0, 236, 0, 2, 0])) + BW.append_section(b"", BW.SECTION_GUEST_MENU, body))
    assert BW.gm_try_read_key_items(frame) == [9, 14] and BW.gm_try_read_bag(frame) == [(236, 2)]
    assert BW.gm_block_matches_party_rule([3, None, 0, 1], got) and not BW.gm_block_matches_party_rule([3, 0], got)
    assert not BW.gm_block_matches_party_rule([3, 3, 0, 1], got)
    assert BW.gm_member_index_rule(got, [0, None, 1, 3], 0) == 1 and BW.gm_member_index_rule(got, [0, None, 1, 3], 1) == -1
    assert BW.GM_SECTION_ORDER_S168.index(12) == BW.GM_SECTION_ORDER_S168.index(11) + 1 and BW.GM_SECTION_ORDER_S168[-2:] == (7, 8)


def test_the_content_witness_names_the_first_member_and_component():
    """decision 13 (WitnessRule): slot order, char -> preset -> pa (off section 12, keyed by CharacterId) -> equip (NoItem skipped) -> sa (a
    negative id skipped), then the bag; key items never refuse."""
    inst = {"char_known": lambda c: c <= 11, "preset_known": lambda p: p <= 15, "pa_len_of": lambda p: 48 if p <= 15 else -1,
            "item_known": lambda i: i < 255, "sa_known": lambda s: 0 <= s < 64}
    party = [{"char": 0, "name": "Zidane", "equip": [1, 255, 255, 255, 255], "sa": [12, -3]}, None,
             {"char": 1, "name": "", "equip": [255] * 5, "sa": []}, None]
    block = {"members": [BW.gm_member(1, 1, 1, 0, 0, [0] * 48), BW.gm_member(0, 0, 1, 0, 0, [0] * 48)]}
    assert BW.gm_witness_rule(party, block, [(1, 3)], inst) == (True, None, None)
    bad = lambda **kw: BW.gm_witness_rule(**kw)                                                    # noqa: E731
    assert bad(party=[dict(party[0], char=99)] + party[1:], block=block, bag=[], inst=inst)[2] == BW.GM_COMP_CHAR
    b2 = {"members": [BW.gm_member(1, 1, 1, 0, 0, [0] * 48), BW.gm_member(0, 77, 1, 0, 0, [0] * 48)]}
    assert bad(party=party, block=b2, bag=[], inst=inst) == (False, "Zidane", BW.GM_COMP_PRESET)
    b3 = {"members": [BW.gm_member(1, 1, 1, 0, 0, [0] * 47), BW.gm_member(0, 0, 1, 0, 0, [0] * 48)]}
    assert bad(party=party, block=b3, bag=[], inst=inst) == (False, "character 1", BW.GM_COMP_PA)    # MemberLabel's fallback
    assert bad(party=[dict(party[0], equip=[900, 255, 255, 255, 255])] + party[1:], block=block, bag=[], inst=inst)[2] == BW.GM_COMP_EQUIP
    assert bad(party=[dict(party[0], sa=[99])] + party[1:], block=block, bag=[], inst=inst)[2] == BW.GM_COMP_SA
    assert bad(party=party, block=block, bag=[(1, 1), (300, 1)], inst=inst) == (False, "bag", "bag")


def test_the_frame_cap_guard_the_send_rule_and_tx_bps():
    assert BW.gm_trail_reserve_of() == BW.GM_TRAIL_RESERVE == 430 and BW.gm_trail_reserve_of(dress_body_len=2) == 429
    assert BW.gm_sec12_fits_rule(8192 - 3 - 100 - 430, 100) and not BW.gm_sec12_fits_rule(8192 - 3 - 100 - 430 + 1, 100)
    assert BW.gm_sec12_fits_rule(2900, 442) and not BW.gm_sec12_fits_rule(7700, 100)
    assert BW.gm_section_send_rule(True, BW.CAPS_S168, BW.CAPS_S168, True, True)
    assert not BW.gm_section_send_rule(True, BW.CAPS_S168, BW.CAPS_S167, True, True)
    assert not BW.gm_section_send_rule(True, BW.ww_own_caps_rule(False, True), BW.CAPS_S168, True, True)
    assert not BW.gm_section_send_rule(False, BW.CAPS_S168, BW.CAPS_S168, True, True)
    assert not BW.gm_section_send_rule(True, BW.CAPS_S168, BW.CAPS_S168, False, True)
    assert not BW.gm_section_send_rule(True, BW.CAPS_S168, BW.CAPS_S168, True, False)
    book = {}
    assert BW.gm_tx_bps_step(book, 100, 5000, 500) == -1 and BW.gm_tx_bps_step(book, 115, 5500, 500) == -1
    assert BW.gm_tx_bps_step(book, 160, 7000, 500) == 15000 and BW.gm_tx_bps_step(book, 190, 8000, 500) == 15000
    assert BW.gm_tx_bps_step(book, 20, 9000, 400) == -1                                # a restarted counter opens a new window


def test_the_words_the_lines_and_the_decline_classes():
    assert BW.gm_refusal_line_rule(BW.GM_WHY_NOT_MIRRORING) == ("FF9 co-op: You'll get the menu once you've followed your partner into a "
                                                                "location.")
    assert BW.gm_refusal_line_rule(BW.GM_WHY_DATA_DIFFERS, "Vivi") == "FF9 co-op: Your game data differs from your partner's (Vivi)."
    # NetSyncGuestMenu.cs: "(" + member + ")" -- C# concatenates a null member (NetSyncClient._gmMember's "none") as empty
    assert BW.gm_refusal_line_rule(BW.GM_WHY_DATA_DIFFERS) == "FF9 co-op: Your game data differs from your partner's ()."
    assert BW.gm_refusal_line_rule(BW.GM_WHY_LEVER) is None and BW.gm_refusal_line_rule("nope") is None
    assert all(BW.gm_refusal_line_rule(w, "x") for w in BW.GM_ALL_WHYS if w != BW.GM_WHY_LEVER)
    assert BW.gm_close_line_rule(BW.GM_CAUSE_TITLE) == "FF9 co-op: menu closed -- your partner is at the title screen."
    assert BW.gm_close_line_rule(BW.GM_CAUSE_WORLD) == BW.gm_close_line_rule(BW.GM_CAUSE_LEAVE) and BW.gm_close_line_rule(0) is None
    assert BW.gm_refusal_line_live_rule(True, 3999, 1, 1) and not BW.gm_refusal_line_live_rule(True, 4000, 1, 1)
    assert not BW.gm_refusal_line_live_rule(True, 100, 1, 2) and BW.gm_close_line_live_rule(True, 3999)
    assert BW.gm_not_paired_line_rule(True, False) and not BW.gm_not_paired_line_rule(True, True)       # CR-2
    full = BW.GM_EFF_BUZZ | BW.GM_EFF_COUNT | BW.GM_EFF_LINE
    assert BW.gm_line_words_rule(full, BW.GM_WHY_SCENE) == BW.gm_refusal_line_rule(BW.GM_WHY_SCENE)
    assert BW.gm_line_words_rule(BW.GM_EFF_SILENT, BW.GM_WHY_SCENE) is None
    assert BW.gm_chip_shown_rule(True, False) and not BW.gm_chip_shown_rule(True, True) and not BW.gm_chip_shown_rule(False, False)
    assert BW.gm_decline_class_rule(BW.GM_WHY_OLDER) is None and BW.gm_decline_class_rule(BW.GM_WHY_LEVER) is None
    assert BW.gm_decline_class_rule(BW.GM_WHY_LINK) == "main menu (link)"
    assert BW.log_gm_refusal(BW.GM_WHY_OLDER, "field 100") == "[NetSync] main menu suppressed (following guest) on field 100"
    assert BW.log_gm_refusal(BW.GM_WHY_RIDING, "world map 9011") == "[NetSync] main menu (riding) suppressed (following guest) on world map 9011"
    assert BW.OVL_GUEST_MENU == 29 and BW.OVERLAY_NAME_GUEST_MENU == "guest_menu" and len(BW.GM_ALL_WHYS) == 19


def test_the_census_the_fingerprint_the_settle_and_the_poke():
    assert BW.GM_CENSUS_NAMES == ("E1", "E2", "E3", "A1", "A2", "A3", "I1", "I2") and BW.gm_census_name(8) is None
    assert BW.gm_census_rule(BW.GM_CENSUS_E1, False, False, True, True) == BW.GM_CV_STOCK                # keyed on the seat alone
    assert BW.gm_census_rule(BW.GM_CENSUS_E1, True, False, True, False) == BW.GM_CV_REFUSE
    assert BW.gm_census_rule(BW.GM_CENSUS_E1, True, True, True, False) == BW.GM_CV_PASS
    assert BW.gm_census_rule(-1, True, True, False, False) == BW.GM_CV_REFUSE                          # fail closed
    assert BW.gm_census_rule(BW.GM_CENSUS_A1, True, False, False, False) == BW.GM_CV_STOCK
    assert BW.gm_census_changes_rule(BW.GM_CENSUS_A2, BW.GM_ABILITY_TYPE_SELECTED) and not BW.gm_census_changes_rule(BW.GM_CENSUS_A1, 2)
    comps = [1, 2, 3, 4, 5]
    assert BW.gm_fp_value_rule(comps) != BW.gm_fp_value_rule([1, 2, 3, 4, 6]) and BW.gm_fp_named_rule(comps, [1, 9, 3, 4, 0]) == 1
    assert BW.gm_fp_verdict_rule(True, True, False, 5, 5) == BW.GM_FV_EQUAL and BW.gm_fp_verdict_rule(True, True, True, 5, 5) == BW.GM_FV_NONE
    assert BW.gm_fp_verdict_rule(True, False, False, 5, 0) == BW.GM_FV_NONE
    assert BW.gm_mix_u(BW.GM_FP_SEED, 0) == (BW.GM_FP_SEED * BW.GM_FP_PRIME) & 0xFFFFFFFFFFFFFFFF
    assert BW.gm_mix(0, -1) == BW.gm_mix_u(0, 0xFFFFFFFFFFFFFFFF) and BW.gm_fp_hex(255) == "0x00000000000000FF"
    assert BW.GM_FP_COMP_NAMES == ("players", "party", "bag", "gil", "keyitems") and BW.gm_fp_comp_index("gil") == 3
    assert BW.GM_OUT_COMP_NAMES == ("events", "eventstate", "achievement", "cards", "hintmap")
    assert (BW.GM_OUT_MASK_LO, BW.GM_OUT_MASK_HI) == (2032, 2041) and BW.gm_out_value_rule(comps) != BW.gm_fp_value_rule(comps)
    assert BW.gm_settle_step_rule(True, False, True) == BW.GM_SE_SAW and BW.gm_settle_step_rule(True, True, True) == BW.GM_SE_STAMP
    assert BW.gm_settle_step_rule(True, True, False) == BW.GM_SE_WAIT and BW.gm_settle_step_rule(False, True, True) == BW.GM_SE_NONE
    buf = bytes(range(16))
    assert BW.gm_vars_digest_rule(buf, 0, 16) != BW.gm_vars_digest_rule(buf, 0, 15) and BW.gm_vars_digest_rule(buf, 4, 20) is None
    assert BW.gm_vars_digest_rule(None, 0, 0) is None and BW.gm_vars_digest_rule(buf, 3, 3).startswith("0x")
    ev = bytearray(2048)
    assert BW.gm_poke_rule(ev, BW.GM_POKE_BYTE) and ev[2047] == 1 and BW.gm_poke_rule(ev, 2047) and ev[2047] == 0
    assert not BW.gm_poke_rule(ev, 2048) and not BW.gm_poke_rule(None, 0)
    assert BW.GM_POKE_BYTE > BW.GM_OUT_MASK_HI                          # above the co-op window the outside fold skips


def test_the_registry_assigns_every_id_once():
    """GM0-REGISTRY: every caps bit, section id, frame type, type-8 kind and overlay state claimed once; two claims of b1 or of section 12
    go red."""
    claims = [(space, ident, name) for space, table in BW.GM_REGISTRY.items() for ident, name in table.items()]
    assert BW.gm_registry_clashes(claims) == []
    assert BW.gm_registry_clashes(claims + [("caps", 0x02, "the guest menu")])
    assert BW.gm_registry_clashes(claims + [("sections", 12, "the quit word")])
    assert BW.GM_REGISTRY["sections"][12] == "the guest-menu block" and BW.GM_REGISTRY["caps"][0x08] == "the guest menu"


def test_the_harness_literals_and_the_sentinels():
    assert BW.GUESTMENU_USAGE.startswith("netsync guestmenu: expected old|act, caps off|on, capture off|on, close old|act or clear (any role)")
    assert BW.GUESTMENU_USAGE.endswith("fireclose <id>, events on|off, poke [off] (the selftest bench)")
    assert tuple(BW.GUEST_MENU_SENTINELS["lever"]) == tuple(BW.GUEST_MENU_LEVER_DEFAULTS) and len(BW.GUEST_MENU_LEVER_DEFAULTS) == 12
    assert set(BW.GUEST_MENU_RELEASE_SET) == set(BW.GUEST_MENU_LEVER_DEFAULTS)
    assert list(BW.GUEST_MENU_SENTINELS)[-3:] == ["outside_settled", "uid0_vars", "sysvar192"]
    assert list(BW.GUEST_MENU_SENTINELS)[2:4] == ["why", "open"] and tuple(BW.GUEST_MENU_SENTINELS["door_refused"]) == BW.GM_ALL_WHYS
    assert tuple(BW.GUEST_MENU_SENTINELS["closes"]) == BW.GM_CLOSE_IDS + ("faults",)
    assert BW.log_guestmenu_fireclose(1, BW.GM_RQ_NEW).endswith("the forced close requested without its trigger: the close order runs")
    assert BW.log_gm_restored(BW.GM_SITE_DOOR, None, 1) == ("[NetSync] guest menu: restored at the door -- every family back by reference but "
                                                           "party (`restore skip`); the session ends")
    assert BW.log_gm_restored(BW.GM_SITE_SCENE).endswith("with the guest menu still seated -- every family back by reference; the session "
                                                          "ends (should never happen)")
    assert BW.world_walk_proof_by_stage(168) == (534, 198) and BW.world_walk_proof_by_stage(167) == (532, 196)
    assert BW.PROOF_ORDER_S168 == (BW.PROOF_WORLD_WALK, BW.PROOF_SEAT_BRACKET, BW.PROOF_GUEST_MENU)
    assert re.fullmatch(BW.GUEST_MENU_PROOF_RE, BW.guest_menu_proof_line(420, 249)[len("[NetSync] "):]).groups() == ("420", "249")
    assert re.fullmatch(BW.SEAT_BRACKET_PROOF_RE, BW.seat_bracket_proof_line(19, 7)[len("[NetSync] "):]).groups() == ("19", "7")
    assert BW.GUEST_MENU_PROOF_S168 == (420, 249) and BW.SEAT_BRACKET_PROOF_S168 == (19, 7) and BW.MENU_SELFTEST_ROWS == 14


# ================================================================================================ THE ENGINE PINS (by stage)
def _s168_patch_live() -> bool:
    return any(nm.startswith("s168-") and nm not in msr.DEAD for nm in msr.stack())


def _engine_text(file_name: str) -> str:
    """The s168 post-image of ``file_name`` BY STAGE: a clone named by FF9_S168_CLONE carrying the s168 tag, else the s168 patch on the stack
    (a file it creates reads whole), else SKIP (the deployed s167)."""
    text = FG.s168_engine_source(file_name)
    if text is None and _s168_patch_live():
        from ._patchstack import stack_file
        text = "\n".join(stack_file(file_name))
    if text is None or (S168_TAG not in text and not _s168_patch_live()):
        pytest.skip(f"no s168 engine source (the deployed s167 stage) -- set {S168_CLONE_ENV}=<the clone's Assembly-CSharp>")
    return text


def _consts(text: str, names: str) -> dict:
    return {m.group(1): int(m.group(2), 0) for m in re.finditer(r"\b(" + names + r")\s*=\s*(0x[0-9A-Fa-f]+|-?\d+)\b(?![.\w])", text)}


#: C# constant -> the kit's twin (NetSyncGuestMenu.cs)
GM_CONSTANTS = {
    "KeyNone": BW.GM_KEY_NONE, "KeyGuestOpen": BW.MENU_KEY_GUEST_OPEN, "KeyGuestQuiet": BW.MENU_KEY_GUEST_QUIET, "EffBuzz": BW.GM_EFF_BUZZ,
    "EffCount": BW.GM_EFF_COUNT, "EffLine": BW.GM_EFF_LINE, "EffSilent": BW.GM_EFF_SILENT, "PaStock": BW.GM_PA_STOCK,
    "PaDeadline": BW.GM_PA_DEADLINE, "PaRefuseGiven": BW.GM_PA_REFUSE_GIVEN, "PaRefuseS121": BW.GM_PA_REFUSE_S121,
    "CauseNone": 0, "CauseLeave": 1, "CauseOut": 2, "CauseRejoin": 3, "CauseWorld": 4, "CauseCut": 5, "CauseEnding": 6, "CauseTitle": 7,
    "CauseScene": 8, "CloseCapMs": BW.GM_CLOSE_CAP_MS, "CsWaitQuit": BW.GM_CS_WAIT_QUIT, "CsWaitLoading": BW.GM_CS_WAIT_LOADING,
    "CsPanelOff": BW.GM_CS_PANEL_OFF, "CsHideRoot": BW.GM_CS_HIDE_ROOT, "CsHideSub": BW.GM_CS_HIDE_SUB, "CsWaitHide": BW.GM_CS_WAIT_HIDE,
    "CsWaitShow": BW.GM_CS_WAIT_SHOW, "CsDone": BW.GM_CS_DONE, "CsEnd": BW.GM_CS_END, "WdWait": BW.GM_WD_WAIT, "WdSweep": BW.GM_WD_SWEEP,
    "WdHudShow": BW.GM_WD_HUD_SHOW, "WdEnd": BW.GM_WD_END, "WdDone": BW.GM_WD_DONE, "RqNone": 0, "RqNew": 1, "RqHeld": 2, "CaWait": 0,
    "CaPanelOff": 1, "CaHideRoot": 2, "CaHideSub": 3, "CaDone": 4, "CaEnd": 5, "CaWdSweep": 6, "CaWdHudShow": 7, "CaWdEnd": 8,
    "CaSceneEnd": 9, "DoorHalfOpen": BW.GM_DOOR_HALF_OPEN, "DoorHalfRestore": BW.GM_DOOR_HALF_RESTORE, "DoorHalfNone": BW.GM_DOOR_HALF_NONE,
    "DfStock": BW.GM_DF_STOCK, "DfRefuse": BW.GM_DF_REFUSE, "DfKeepStock": BW.GM_DF_KEEP_STOCK, "RvNone": 0, "RvRestore": 1, "RvDrop": 2,
    "ReClear": 1, "ReSubMenus": 2, "ReAlarm": 4, "ReDropLine": 8, "SiteDoor": 1, "SiteSeatFault": 2, "SiteReplace": 3, "SiteReplaceTitle": 4,
    "SiteRampFire": 5, "SiteRampQuit": 6, "SiteLoadEntry": 7, "SiteLevelLoaded": 8, "SiteTitle": 9, "SiteScene": 10, "SiteConfigEdge": 11,
    "SiteRampArm": 12, "SiteTransportStop": 13, "BlPlain": 0, "BlQuiet": 1, "BlAlarm": 2, "SvOk": 0, "SvShort": 1, "SvBag": 2, "SvFault": 3,
    "DoStock": 0, "DoRefuse": 1, "DoSeat": 2, "BsRefused": 1, "BsWatching": 2, "MenuFmt": BW.GM_MENU_FMT, "PolicyS168": BW.GM_POLICY_S168,
    "ApplyMaskS168": BW.GM_APPLY_MASK_S168, "MenuFixedLen": BW.GM_MENU_FIXED_LEN, "MemberFixedLen": BW.GM_MEMBER_FIXED_LEN,
    "MemberCap": BW.GM_MEMBER_CAP, "PaClamp": BW.GM_PA_CLAMP, "TrailReserve": BW.GM_TRAIL_RESERVE, "PresetWireMax": BW.GM_PRESET_WIRE_MAX,
    "TxWindowMs": BW.GM_TX_WINDOW_MS, "GuestLineMs": BW.GM_GUEST_LINE_MS, "OvlGuestLine": BW.OVL_GUEST_MENU, "CensusSites": BW.GM_CENSUS_SITES,
    "CvStock": 0, "CvRefuse": 1, "CvPass": 2, "CeDone": 1, "CeNothing": 2, "CeWatchdog": 3, "CeScene": 4, "CeClearPoint": 5, "CeFault": 6,
    "FpComps": BW.GM_FP_COMPS, "FpPlayers": 0, "FpParty": 1, "FpBag": 2, "FpGil": 3, "FpKeyItems": 4, "FvNone": 0, "FvEqual": 1,
    "FvDiffers": 2, "OutComps": BW.GM_OUT_COMPS, "OutMaskLo": BW.GM_OUT_MASK_LO, "OutMaskHi": BW.GM_OUT_MASK_HI,
    "OutCounters": BW.GM_OUT_COUNTERS, "SeNone": 0, "SeWait": 1, "SeSaw": 2, "SeStamp": 3, "PokeByte": BW.GM_POKE_BYTE,
    "PokeBit": BW.GM_POKE_BIT, "BenchFrameMarker": 1, "BenchFrameWitness": 2, "BenchFrameIntent": 3,
    "CensusE1": 0, "CensusE2": 1, "CensusE3": 2, "CensusA1": 3, "CensusA2": 4, "CensusA3": 5, "CensusI1": 6, "CensusI2": 7}


def test_s168_the_constants_are_the_engines():
    gm = _engine_text("NetSyncGuestMenu.cs")
    got = _consts(gm, "|".join(GM_CONSTANTS))
    assert got == GM_CONSTANTS, {k: (got.get(k), v) for k, v in GM_CONSTANTS.items() if got.get(k) != v}
    for name, value in (("GmFpSeed", BW.GM_FP_SEED), ("GmFpPrime", BW.GM_FP_PRIME)):
        assert re.search(rf"const UInt64 {name} = {value}UL;", gm), name
    assert "UInt64 h = Mix(GmFpSeed, 0x7E0);" in gm                                     # OutValueRule's salt
    ww = _engine_text("NetSyncWorldWalk.cs")
    assert re.search(r"const Int32 CapGuestMenu = 0x08;", ww)
    assert "return fpOff ? OwnCaps : (OwnCapsWalk | (menuOff ? 0 : CapGuestMenu));" in ww
    assert "internal static Int32 OwnCapsNow { get { return NetSyncWorldWalk.OwnCapsRule(Off, NetSyncGuestMenu.LeverCapsOff); } }" in ww
    field = _engine_text("NetSyncField.cs")
    assert "public const Int32 MenuKeyGuestOpen = NetSyncGuestMenu.KeyGuestOpen;" in field
    assert "public const Int32 MenuKeyGuestQuiet = NetSyncGuestMenu.KeyGuestQuiet;" in field
    assert re.search(r'case MenuKeyGuestQuiet: return "guest";', field)
    assert re.search(r"public const Byte SectionGuestMenu = 12;", _engine_text("NetSyncState.cs"))
    assert "dest != FF9Define.FLDSCRPT_EVTNO_ENDING" in gm                # F2's ending exclusion (the stock constant, 16000)
    raw = os.environ.get(S168_CLONE_ENV, "").strip()
    hits = sorted(pathlib.Path(raw).rglob("FF9Define.cs")) if raw else []
    if hits:
        assert re.search(rf"FLDSCRPT_EVTNO_ENDING = {BW.FLDSCRPT_EVTNO_ENDING};", hits[0].read_text(encoding="utf-8-sig", errors="replace"))


def _array(text: str, name: str) -> list:
    m = re.search(name + r"\s*=\s*\{(.*?)\};", text, re.S)
    assert m, name
    return [None if tok.strip() == "null" else (_LIT.fullmatch(tok.strip()).group(1) if _LIT.fullmatch(tok.strip()) else tok.strip())
            for tok in re.sub(r"//[^\n]*", "", m.group(1)).split(",") if tok.strip()]


def test_s168_the_closed_sets_are_the_engines_in_order():
    gm = _engine_text("NetSyncGuestMenu.cs")
    whys = dict(re.findall(r'internal const String (Why\w+) = "(\w+)";', gm))
    assert tuple(whys[n] for n in _array(gm, "AllWhys")) == BW.GM_ALL_WHYS
    assert tuple(_array(gm, "CauseNames")) == BW.GM_CAUSE_NAMES
    assert tuple(_array(gm, "CloseStepNames")) == BW.GM_CLOSE_STEP_NAMES
    assert tuple(_array(gm, "CensusNames")) == BW.GM_CENSUS_NAMES
    assert tuple(_array(gm, "FpNames")) == BW.GM_FP_COMP_NAMES and tuple(_array(gm, "OutNames")) == BW.GM_OUT_COMP_NAMES
    assert tuple(_array(gm, "SiteNames")) == BW.GM_SITE_NAMES and tuple(_array(gm, "CloseEndNames")) == BW.GM_CLOSE_END_NAMES
    assert tuple(_array(gm, "SeatSubMenuNames")) == BW.GM_SEAT_SUB_MENUS
    comps = dict(re.findall(r'internal const String (Comp\w+) = "(\w+)";', gm))
    assert tuple(comps[n] for n in _array(gm, "BenchWitnessNames")) == BW.GM_BENCH_WITNESS_NAMES
    terms = _array(gm, "AllTerms")
    assert len(terms) == len(BW.GM_TERMS) == 23 and terms[:3] == ["TermLever", "TermWho", "TermCaps"] and terms[-1] == "TermWorldScene"


def test_s168_the_words_are_the_engines():
    gm = _engine_text("NetSyncGuestMenu.cs")
    for literal in (BW.GM_LINE_PREFIX, BW.GM_CLOSE_LINE_PREFIX, BW.GM_CHIP_VIEW_ONLY, BW.GM_WORDS_AGAIN, BW.GM_WORDS_FOLLOW):
        assert f'"{literal}"' in gm, literal
    for why, words in BW.GM_REFUSAL_WORDS.items():
        if words in (BW.GM_WORDS_AGAIN, BW.GM_WORDS_FOLLOW):
            assert re.search(rf"case Why\w+:\s*(case Why\w+:\s*)*w = Words(Again|Follow); break;", gm), why
        else:
            assert f'w = "{words}"; break;' in gm, why
    assert 'w = "Your game data differs from your partner\'s (" + member + ")."; break;' in gm
    for cause, words in BW.GM_CLOSE_WORDS.items():
        assert f'CloseLinePrefix + "{words}"' in gm, cause
    assert 'c[k] = AllWhys[k] == WhyOlder || AllWhys[k] == WhyLever ? null : "main menu (" + AllWhys[k] + ")";' in gm
    client = _engine_text("NetSyncClient.cs")
    assert 'case OvlGuestMenuLine: return "guest_menu";' in client


def test_s168_the_harness_literals_and_acks_are_the_engines():
    gm = _engine_text("NetSyncGuestMenu.cs")
    lits = set(_LIT.findall(gm))
    assert BW.GUESTMENU_USAGE in lits and BW.GUESTMENU_BENCH_REFUSAL in lits and BW.GUESTMENU_FRAME_SEATED in lits
    assert BW.GUESTMENU_OFF_REFUSAL in lits and BW.LOG_GUESTMENU_CLEAR in lits and BW.LOG_GUESTMENU_RELEASED in lits
    assert '"netsync guestmenu: the lever faulted (" + err.Message + ")"' in gm
    lits = {s.replace('\\"', '"') for s in lits}
    for (op, word), line in BW.GUESTMENU_ACKS.items():
        parts = line.split(str(BW.GM_POKE_BYTE)) if op == "poke" and word is None else [line]   # `poke` splices PokeByte
        assert all(p in lits for p in parts), (op, word)
    for fn, arg in ((BW.log_guestmenu_seat_fault, "bag"), (BW.log_guestmenu_restore_skip, "party"), (BW.log_guestmenu_close_fault, "root")):
        parts = fn(arg).split(arg)                                       # the C#: literal + v + literal + v + literal
        assert len(parts) == 3 and all(p in lits for p in parts), (fn.__name__, [p for p in parts if p not in lits])
    client = _engine_text("NetSyncClient.cs")
    for outcome in (BW.GM_RQ_NEW, BW.GM_RQ_HELD, "no_seat", "old"):
        assert f'"{BW.GUESTMENU_FIRECLOSE_WORDS[outcome]}"' in client, outcome
    assert BW.GUESTMENU_FRAME_INTENT_NO_BASE in set(_LIT.findall(client))
    assert '"[NetSync] harness: guestmenu host here -- the bench host stands on my field " + fld' in client
    for literal in (BW.LOG_GM_EVENTS_ON, BW.LOG_GM_POKE_NOTHING):
        assert f'"{literal}"' in client, literal


def _catch_netsync() -> dict:
    agent = _engine_text("HarnessAgent.cs")
    lines = agent.split("\n")
    catch = [ln for ln in lines if re.search(r'outer\.Append\("\\"netsync\\":\{\\"enabled', ln)]
    head = [ln for ln in lines if 'NetsyncF3Retired = "' in ln]
    tail = [ln for ln in lines if re.search(r'\+ "\\"align_win', ln)]
    if not (catch and head and tail):
        pytest.skip("this s168 HarnessAgent carries no catch literal lines")
    a, b = _LIT.findall(catch[0])
    pinned = "".join(_LIT.findall(head[0]) + _LIT.findall(tail[0]))
    return json.loads("{" + (a + pinned + b).replace('\\"', '"') + "}")["netsync"]


def test_s168_the_catch_line_closes_netsync_with_guestmenu_at_its_sentinels():
    """THE CATCH LITERAL IS PART OF EVERY KEY ADDITION: `guestmenu` netsync's LAST key (after `wire_peer`), at BW.GUEST_MENU_SENTINELS."""
    ns = _catch_netsync()
    assert list(ns)[-2:] == ["wire_peer", "guestmenu"], list(ns)[-3:]
    assert json.dumps(ns["guestmenu"]) == json.dumps(BW.GUEST_MENU_SENTINELS)
    assert ns["menu_refusal"]["now"] is None


def _flat_writer_keys(d: dict, inside=None) -> list:
    """The literal keys AppendGuestMenu writes for sentinel block ``d``, in order: a loop-written block contributes only its literal keys
    (`closes`: `faults` after the ids loop; `door_refused`: none; `fp.components`: its per-component `before` / `after`; any other
    `components`: none)."""
    out = []
    for k, v in d.items():
        if k == "components":
            out += ["before", "after"] if inside == "fp" else []
            continue
        out.append(k)
        if k == "closes":
            out.append("faults")
        elif k == "door_refused":
            pass
        elif isinstance(v, dict):
            out += _flat_writer_keys(v, k)
    return out


def test_s168_append_guest_menu_writes_the_sentinels_keys_in_order():
    """THE WRITER'S ORDER IS THE SENTINEL'S (the W1 review's static check, re-read here): every literal key AppendGuestMenu writes, in
    order, is BW.GUEST_MENU_SENTINELS' flattened -- and the agent appends the block after `wire_peer` and names the sub-verb LAST."""
    agent = _engine_text("HarnessAgent.cs")
    i = agent.index("private static void AppendGuestMenu(StringBuilder sb)")
    body = agent[i:agent.index("\n        }\n", i)]
    got = [a or b for a, b in re.findall(r'(?:Str|Num|Bool)\(sb, "(\w+)"|\\"(\w+)\\":', body) if (a or b) != "components"]
    assert got == ["guestmenu"] + _flat_writer_keys(BW.GUEST_MENU_SENTINELS), got
    assert "AppendGuestMenu(sb);" in agent and re.search(r"unknown sub-verb .*\|worldwalk\|guestmenu\)", agent)


#: guestmenu keys whose children the agent names in a loop (the cause ids, the whys): a scenario may read any of them
_LOOP_KEYS = {"closes": set(BW.GM_CLOSE_IDS) | {"faults"}, "door_refused": set(BW.GM_ALL_WHYS)}


def _in_tree(tree, path) -> bool:
    cur = tree
    for i, k in enumerate(path):
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        elif i and path[i - 1] in _LOOP_KEYS and k in _LOOP_KEYS[path[i - 1]]:
            cur = None
        elif cur is None:                                                # a null sentinel (`components`): its live keys are a loop's
            return True
        else:
            return False
    return True


def test_s168_every_key_the_guest_menu_scenarios_read_is_published():
    """A key no engine publishes reads None forever, and a judge over it can never fail (GM0-QUIT-D once read
    `netsync.battle.end.quit_open`): every literal `netsync.*` path and every guestmenu `_n` / `_d` path the two s168 scenarios read is in
    the catch literal's tree (the sentinels of every key the agent writes)."""
    ns = _catch_netsync()
    missing = []
    for name in ("coop_guest_menu.py", "coop_guest_menu_duo.py"):
        src = (REPO / "studies" / "test-harness" / "scenarios" / name).read_text(encoding="utf-8")
        reads = [("netsync", m.group(1).split("."), m.start()) for m in re.finditer(r'"netsync\.([\w.]+)"', src)]
        reads += [("guestmenu", re.findall(r'"(\w+)"', m.group(1)), m.start())
                  for m in re.finditer(r'\b_[nd]\([^()"]*?,\s*((?:"\w+"\s*,?\s*)+)', src)]
        assert len(reads) > 50, (name, len(reads))                      # the scan itself still finds the reads (142 / 79 as built)
        for root, path, at in reads:
            if not _in_tree(ns if root == "netsync" else ns["guestmenu"], path):
                missing.append(f"{name}:{src.count(chr(10), 0, at) + 1} {root}.{'.'.join(path)}")
    assert not missing, missing


def test_s168_the_proofs_tallies_are_derived_from_the_sources():
    """decision 34: 420 / 249 (the W1 review's), 19 / 7, and the world walk proof's 534 / 198 -- each DERIVED from its source (the stand-in's
    fallback equal to it), MenuRefusalSelfTest still 14 rows."""
    assert BW.selftest_proof_counts(_engine_text("NetSyncGuestMenu.cs")) == BW.GUEST_MENU_PROOF_S168
    assert BW.selftest_proof_counts(_engine_text("NetSyncSeatBracket.cs")) == BW.SEAT_BRACKET_PROOF_S168
    assert BW.world_walk_proof_counts(_engine_text("NetSyncWorldWalk.cs")) == BW.WORLD_WALK_PROOF_S168
    field = _engine_text("NetSyncField.cs")
    i = field.index("internal static Boolean MenuRefusalSelfTest(")
    assert len(re.findall(r"(?<![\w.])MenuRow\(", field[i:field.index("\n        }\n", i)])) == BW.MENU_SELFTEST_ROWS
    client = _engine_text("NetSyncClient.cs")
    a, b, c = (client.index(f'"[NetSync] {h}OK (') for h in BW.PROOF_ORDER_S168)
    assert a < b < c                                                     # the block's last three lines, in this order


# ---- THE PROOF'S OWN ROWS, EVALUATED (the _run_cs_rows pattern over NetSyncGuestMenu.Rows' single-expression rows)
_ROW = re.compile(r'row\(\(\) => (?!\{)(.*?),\s*"([a-z0-9_.]+)"\);', re.S)   # the name may sit on its own line
#: the proof's `r.<Rule>` -> its twin; a row naming anything else (a probe builder, a seat, a lambda over facts) is not evaluated here
R_TWINS = {"Session": BW.gm_guest_session_rule, "Effect": BW.gm_refuse_effect_rule, "Act": BW.gm_press_act_rule,
           "DeclineClass": BW.gm_decline_class_rule, "LineWords": BW.gm_line_words_rule, "RefusalLive": BW.gm_refusal_line_live_rule,
           "CloseLive": BW.gm_close_line_live_rule, "NotPairedLine": BW.gm_not_paired_line_rule, "Chip": BW.gm_chip_shown_rule,
           "Request": BW.gm_close_request_rule, "Step": BW.gm_close_step_rule, "Fade": BW.gm_fade_ms_rule, "Deadline": BW.gm_close_deadline_rule,
           "Clock": BW.gm_watchdog_clock_rule, "Watchdog": BW.gm_watchdog_act_rule, "Identity": BW.gm_restore_identity_rule,
           "OpenDoor": BW.gm_open_door_rule, "DoorVerdict": BW.gm_door_verdict_rule, "Reshow": BW.gm_door_reshow_rule,
           "DoorFault": BW.gm_door_fault_rule, "Line": BW.gm_refusal_line_rule, "FpVerdict": BW.gm_fp_verdict_rule,
           "Autosave": BW.gm_autosave_ladder_rule, "Census": BW.gm_census_rule, "Changes": BW.gm_census_changes_rule,
           "RampSettle": BW.gm_ramp_settle_rule, "CutUiFree": BW.gm_cut_ui_free_rule, "Settle": BW.gm_settle_step_rule,
           "Send": BW.gm_section_send_rule, "Fits": BW.gm_sec12_fits_rule, "Short": BW.gm_short_seat_rule, "DoorHalf": BW.gm_door_half_rule,
           "RestoreDoor": BW.gm_restore_door_rule, "CloseEndsAt": BW.gm_close_ends_at_rule, "BackstopLine": BW.gm_backstop_line_rule,
           "FaultStep": BW.gm_close_fault_step_rule, "CauseIndex": BW.gm_cause_index_rule, "Boot": BW.gm_boot_seat_rule,
           "DoorSeats": BW.gm_door_seats_rule, "SessionEnds": BW.gm_session_ends_rule, "HeldBits": BW.gm_held_bits_rule,
           "CutMemory": BW.gm_cut_memory_rule, "RestoreEnd": BW.gm_restore_end_rule, "CompName": BW.gm_fp_comp_name,
           "VarsDigest": BW.gm_vars_digest_rule, "PressDeadline": BW.gm_press_deadline_rule, "PressHolds": BW.gm_press_holds_rule}
R_VALUES = {"Reserve": BW.GM_TRAIL_RESERVE, "PokeAt": BW.GM_POKE_BYTE}
GM_FUNCS = {"GuestKeyName": BW.gm_guest_key_name, "CauseName": BW.gm_cause_name, "CloseStepName": BW.gm_close_step_name,
            "CloseClockRuns": BW.gm_close_clock_runs, "RefusalLineRule": BW.gm_refusal_line_rule, "CloseLineRule": BW.gm_close_line_rule,
            "TrailReserveOf": BW.gm_trail_reserve_of, "FpCompName": BW.gm_fp_comp_name, "FpCompIndex": BW.gm_fp_comp_index,
            "OutCompName": BW.gm_out_comp_name, "CensusName": BW.gm_census_name, "SiteName": BW.gm_site_name,
            "PressDeadlineRule": BW.gm_press_deadline_rule, "PressHoldsRule": BW.gm_press_holds_rule, "CutMemoryRule": BW.gm_cut_memory_rule,
            "NotPairedLineRule": BW.gm_not_paired_line_rule, "SettleStepRule": BW.gm_settle_step_rule,
            "VarsDigestRule": BW.gm_vars_digest_rule, "DeclineClassRule": BW.gm_decline_class_rule, "ChipShownRule": BW.gm_chip_shown_rule}


def _gm_ns(gm: str) -> dict:
    """The rows' namespace: every C# constant by its C# name AT THE TWINS' values (a drift shows here and in the constants pin), the
    twins by `r_<Rule>`, the local UIState / AbilityType consts the body declares, the key step through its lazy wrapper."""
    ns = {"__builtins__": {"len": len, "bytes": bytes, "Exception": Exception}}
    ns.update(GM_CONSTANTS)
    for name in re.findall(r'internal const String (Why\w+) = "\w+";', gm):
        ns[name] = re.search(rf'const String {name} = "(\w+)";', gm).group(1)
    for name, comp in re.findall(r'internal const String (Comp\w+) = "(\w+)";', gm):
        ns[name] = comp
    ns.update({"Audible": BW.MENU_KEY_REFUSE_AUDIBLE, "Silent": BW.MENU_KEY_REFUSE_SILENT, "Open": BW.MENU_KEY_OPEN,
               "CapsS168": BW.CAPS_S168, "CapsS167": BW.CAPS_S167, "SectionMenu": BW.SECTION_GUEST_MENU,
               "NetSyncField_MenuKeyStockOff": BW.MENU_KEY_STOCK_OFF, "NetSyncField_MenuKeyDialogPath": BW.MENU_KEY_DIALOG_PATH,
               "NetSyncField_MenuKeyOpen": BW.MENU_KEY_OPEN, "NetSyncField_MenuKeyRefuseAudible": BW.MENU_KEY_REFUSE_AUDIBLE,
               "NetSyncWorldWalk_CapWorldPose": BW.WW_CAP_WORLD_POSE, "NetSyncWorldWalk_CapWorldFp": BW.WW_CAP_WORLD_FP,
               "NetSyncWorldWalk_CapGuestMenu": BW.WW_CAP_GUEST_MENU, "NetSyncWorldWalk_OwnCapsRule": BW.ww_own_caps_rule,
               "NetSyncWire_MaxPayload": BW.WIRE_MAX_PAYLOAD, "NetSyncDialog_HeaderLen": BW.DIALOG_HEADER_LEN, "NetSyncDialog_OpenLen": 6,
               "NetSyncDialog_OpenCap": 4, "NetSyncDialog_EventLen": 12, "NetSyncDialog_RingCap": 32,
               "NetSyncVisitor_DressBodyLen": BW.DRESS_BODY_LEN, "NetSyncDialog_HfTitle": BW.HF_TITLE, "NetSyncDialog_HfBattle": BW.HF_BATTLE,
               "SaEnable": BW.GM_ABILITY_TYPE_ENABLE, "SaSelected": BW.GM_ABILITY_TYPE_SELECTED, "GuestLineMs": BW.GM_GUEST_LINE_MS})
    for name, state in re.findall(r"const UIManager\.UIState (\w+) = UIManager\.UIState\.(\w+);", gm):
        ns[name] = state
    ns.update({f"r_{k}": v for k, v in R_TWINS.items()})
    ns.update({f"r_{k}": v for k, v in R_VALUES.items()})
    ns.update(GM_FUNCS)

    def key(en, old, ses, mi, lo, po, st, why, out):
        verdict, w = BW.gm_key_step(en, old, ses, mi, lo, po, st, why)
        ns[out] = w
        return verdict

    def boom():
        raise RuntimeError("probe fault")
    ns.update(r_Key=key, yes=lambda: True, no=lambda: False, boom=boom, whyBoom=boom, whyOpen=lambda: None, why=None)
    return ns


def _gm_py(expr: str) -> str:
    """One C# row expression as Python (the selftest rows' subset): strings kept, `out why` by name, `() => X` a lambda, UIState / qualified
    names, literals, && / || / ! (each `!` around its whole operand)."""
    strings = []

    def keep(m):
        strings.append(repr(m.group(1).replace('\\"', '"').replace("\\\\", "\\")))
        return f"__S{len(strings) - 1}__"
    code = _LIT.sub(keep, expr)
    code = re.sub(r"\bUIManager\.UIState\.(\w+)", lambda m: repr(m.group(1)), code)
    code = re.sub(r"\bout (\w+)", lambda m: repr(m.group(1)), code)
    code = re.sub(r"\(\) => ([\w.]+)", r"(lambda: \1)", code)
    code = re.sub(r"\b(\d+)(?:UL|ul|U|u|L|f)\b", r"\1", code)
    code = re.sub(r"\b(\d+\.\d+)f\b", r"\1", code)
    code = re.sub(r"\br\.(\w+)", r"r_\1", code)
    code = re.sub(r"\b(NetSync\w+)\.(\w+)", r"\1_\2", code)
    code = re.sub(r"\btrue\b", "True", code)
    code = re.sub(r"\bfalse\b", "False", code)
    code = re.sub(r"\bnull\b", "None", code)
    code = code.replace("&&", " and ").replace("||", " or ")
    while True:
        m = re.search(r"!(?!=)", code)
        if not m:
            break
        k = m.end()
        while code[k] == " ":
            k += 1
        depth, end = 0, k
        if code[k] == "(":
            for end in range(k, len(code)):
                depth += {"(": 1, ")": -1}.get(code[end], 0)
                if depth == 0:
                    end += 1
                    break
        else:
            w = re.match(r"[\w.]+", code[k:])
            end = k + w.end()
            if end < len(code) and code[end] == "(":
                for e2 in range(end, len(code)):
                    depth += {"(": 1, ")": -1}.get(code[e2], 0)
                    if depth == 0:
                        end = e2 + 1
                        break
        code = code[:m.start()] + "(not " + code[k:end] + ")" + code[end:]
    for i, s in enumerate(strings):
        code = code.replace(f"__S{i}__", s)
    return code


def _gm_rows(gm: str) -> list:
    a, b = gm.find("private static Int32 Rows("), gm.find("private static Rules Mutant(")
    return [(m.group(2), " ".join(m.group(1).split())) for m in _ROW.finditer(gm[a:b])]


def _run_gm_rows(gm: str, ns: dict) -> tuple:
    """Every single-expression row whose names the namespace holds, evaluated: (passed names, failed (name, got), skipped names)."""
    passed, failed, skipped = [], [], []
    for name, expr in _gm_rows(gm):
        code = _gm_py(expr)
        names = set(re.findall(r"\b[A-Za-z_]\w*\b", re.sub(r"'[^']*'", "''", code))) - {"and", "or", "not", "lambda", "True", "False",
                                                                                        "None", "len", "bytes", "in"}
        if any(n not in ns for n in names):
            skipped.append(name)
            continue
        try:
            got = eval(code, ns)                                        # noqa: S307 -- the engine's own selftest rows
        except Exception as err:                                        # noqa: BLE001
            got = f"raised {type(err).__name__}: {err}"
        (passed if got is True else failed).append(name if got is True else (name, got, code))
    return passed, failed, skipped


def test_s168_the_twins_pass_the_guest_menu_proofs_own_rows():
    """THE PROOF'S OWN ROWS: every evaluable single-expression row of NetSyncGuestMenu.Rows() (the key step's included, through its lazy
    wrapper) holds for the twins -- and the families the bench decodes are all among them."""
    gm = _engine_text("NetSyncGuestMenu.cs")
    passed, failed, _skipped = _run_gm_rows(gm, _gm_ns(gm))
    assert not failed, failed
    assert len(passed) >= 145, len(passed)
    fams = {n.split(".")[0] for n in passed}
    assert {"key", "session", "effect", "act", "words", "line", "chip", "close", "step", "fade", "deadline", "clock", "wd", "door",
            "fp", "census", "ramp", "cut", "settle", "send", "frame"} <= fams, sorted(fams)
    for row in ("key.pair_on_rule", "line.never_over_connecting", "settle.one_frame_after_step5", "key.harness_names"):
        assert row in passed or row in {n for n, _e in _gm_rows(gm)}, row


@pytest.mark.parametrize("twin, mutant, row", [
    ("NotPairedLine", lambda on, lost: on, "line.never_over_connecting"),                                       # CR-2's line_over_connecting
    ("Settle", lambda a, s, h: BW.GM_SE_NONE if not a else BW.GM_SE_WAIT if not h else BW.GM_SE_STAMP, "settle.one_frame_after_step5"),
    ("Request", lambda s, o, c, st: c != 0 and not o, "close.request_without_seat_is_a_noop"),               # keyed on the UI, not the seat
    ("Act", lambda v, w: BW.GM_PA_STOCK | BW.GM_PA_DEADLINE if v in (5, 6) else BW.gm_press_act_rule(v, w), "act.quiet_never_stamps"),
    ("Chip", lambda s, off: s, "chip.lever_off_hides"),
    ("CloseEndsAt", lambda site: True, "closeend.outlives_the_restore_door"),
    ("CutMemory", lambda c, l, b: -1, "cut.memory_kept_through_the_fight"),                                   # LC1's own row
    ("Boot", lambda m, s: BW.GM_BS_WATCHING, "boot.refused_while_seated"),
])
def test_s168_a_mutant_twin_fails_the_proofs_own_row(twin, mutant, row):
    gm = _engine_text("NetSyncGuestMenu.cs")
    ns = _gm_ns(gm)
    ns[f"r_{twin}"] = mutant
    _passed, failed, _skipped = _run_gm_rows(gm, ns)
    assert row in [f[0] for f in failed], row


# ================================================================================================ THE STAND-IN
def _root():
    t = pathlib.Path(tempfile.mkdtemp(prefix="gm_"))
    (t / "x64").mkdir()
    (t / "x64" / "FF9.exe").write_bytes(b"MZ")
    (t / "Memoria.log").write_text("fake log\n", encoding="utf-8")
    return t


def _fake(*, faults=(), s168=True, field=100) -> FakeGame:
    f = FakeGame(_root(), render_fps=30.0)
    f.swap_qpc = None
    f.dir.mkdir(parents=True, exist_ok=True)
    (f.dir / "arm").write_text("", encoding="utf-8")
    f.armed = True
    f.state_every = 1 << 30
    if s168:
        FG.guest_menu_stand_in(f, faults=faults)
    f.field_id, f.ui_state, f.control = field, "FieldHUD", True
    return f


def _step(f, n=1):
    for _ in range(int(n)):
        f._frame_once()


def _gm(f) -> dict:
    return f._netsync_doc()["guestmenu"]


def _log(f) -> str:
    return (f.game_path / "Memoria.log").read_text(encoding="utf-8")


def _bench(f, marker=7):
    f._netsync(["selftest", "1"])
    f._netsync(["bench", "1"])
    _step(f, 2)
    if marker:
        f._netsync(["guestmenu", "frame", str(marker)])


def _press(f, n=4):
    f._menu_step("menu")
    _step(f, n)


def _client(f, *, mirroring=True, caps=BW.CAPS_S168, field=100, flags=BW.HF_CONTROL | BW.HF_ON_FIELD):
    f.follow_session(field, flags=flags)
    f.story_mirroring = mirroring
    f.gm_host_caps = caps
    _step(f, 2)


def test_the_default_stand_in_is_the_deployed_s167():
    f = _fake(s168=False)
    assert "guestmenu" not in f._netsync_doc() and "guestmenu" not in f._netsync_subverbs()
    assert "guestmenu" not in FG.NETSYNC_SUBVERBS and "guestmenu" not in FG.caps_through("worldwalk")
    f.world_walk_pieces = FG.FAKE_WORLD_WALK_S167_PIECES
    assert f._wwb_own_caps() == BW.CAPS_S167                                             # an s167 engine never speaks b3
    with pytest.raises(RuntimeError, match="unknown sub-verb 'guestmenu'"):
        f._netsync(["guestmenu", "clear"])


def test_the_s168_stand_in_publishes_guestmenu_last_at_the_sentinels_keys_and_the_caps_word():
    f = _fake()
    doc = f._netsync_doc()
    assert list(doc)[-2:] == ["wire_peer", "guestmenu"] and f._netsync_subverbs()[-2:] == ("worldwalk", "guestmenu")
    gm = doc["guestmenu"]
    assert list(gm) == list(BW.GUEST_MENU_SENTINELS)
    for k, v in BW.GUEST_MENU_SENTINELS.items():
        if isinstance(v, dict):
            assert list(gm[k]) == list(v), k
    assert gm["lever"] == BW.GUEST_MENU_LEVER_DEFAULTS and not gm["seated"] and not gm["open"] and gm["opens"] == 0
    assert f._wwb_own_caps() == BW.CAPS_S168 == gm["caps"]["own"]
    f._netsync(["selftest", "1"])
    f._netsync(["guestmenu", "caps", "off"])
    assert f._wwb_own_caps() == BW.CAPS_S167 and _gm(f)["lever"]["caps"] == "off"
    f._netsync(["worldwalk", "fp", "off"])
    assert f._wwb_own_caps() == 1                                        # `fp off`: s166's word whatever the menu lever says


def test_the_proof_block_ends_with_the_three_s168_lines_in_order():
    f = _fake()
    f._netsync(["selftest", "1"])
    _step(f, 4)
    text = _log(f)
    rows, mutants = FG.world_walk_proof_tallies_s168()
    lines = [f"[NetSync] {BW.PROOF_WORLD_WALK}OK ({rows} rows, {mutants} mutants)", BW.seat_bracket_proof_line(*FG.seat_bracket_proof_tallies()),
             BW.guest_menu_proof_line(*FG.guest_menu_proof_tallies())]
    at = [text.index(ln) for ln in lines]
    assert at == sorted(at)
    if not os.environ.get(S168_CLONE_ENV, "").strip() and not _s168_patch_live():
        assert (rows, mutants) == (534, 198) and FG.guest_menu_proof_tallies() == (420, 249)
    assert _gm(f)["frame"]["type5_len"] > 0 and _gm(f)["frame"]["sec12_len"] == 0      # the selftest role's own build: no section 12
    f2 = _fake(faults=("guest_menu_proof_fail",))
    f2._netsync(["selftest", "1"])
    _step(f2, 4)
    assert f"{BW.PROOF_GUEST_MENU}FAIL" in _log(f2)


def test_the_lever_refusals_in_the_engines_order():
    f = _fake()
    with pytest.raises(RuntimeError, match=re.escape(BW.GUESTMENU_USAGE)):
        f._netsync(["guestmenu", "nope"])
    with pytest.raises(RuntimeError, match=re.escape(BW.GUESTMENU_OFF_REFUSAL)):
        f._netsync(["guestmenu", "old"])
    f._netsync(["guestmenu", "clear"])                                  # `clear` works with co-op off
    assert BW.LOG_GUESTMENU_CLEAR in _log(f)
    f._netsync(["selftest", "1"])
    with pytest.raises(RuntimeError, match=re.escape(BW.GUESTMENU_BENCH_REFUSAL)):
        f._netsync(["guestmenu", "frame", "7"])                         # the selftest role without the bench
    with pytest.raises(RuntimeError, match=re.escape(BW.GUESTMENU_USAGE)):
        f._netsync(["guestmenu", "old", "now"])                         # a bad arity
    f._netsync(["guestmenu", "old"])
    assert BW.guestmenu_ack("old") in _log(f) and _gm(f)["lever"]["menu"] == "old"
    f._netsync(["bench", "1"])
    with pytest.raises(RuntimeError, match=re.escape(BW.GUESTMENU_FRAME_INTENT_NO_BASE)):
        f._netsync(["guestmenu", "frame", "intent", "200"])
    with pytest.raises(RuntimeError, match=re.escape(BW.GUESTMENU_USAGE)):
        f._netsync(["guestmenu", "frame", "0"])                         # a marker outside 1-9999


def test_gm0_release_every_lever_back_one_line_and_the_bench_frame_dropped():
    """GM0-RELEASE: all twelve set off their defaults (decision 31), then the release (a `reset`): every lever at its default, ONE line;
    a release with nothing set says nothing; `release_skip` (the mutant) leaves `seat skip` and goes red."""
    def run(faults=()):
        f = _fake(faults=faults)
        _bench(f)
        f._netsync(["guestmenu", "host", "elsewhere"])
        for op in BW.GUEST_MENU_RELEASE_SET.values():
            f._netsync(["guestmenu", *op])
        lever = _gm(f)["lever"]
        assert all(lever[k] != v for k, v in BW.GUEST_MENU_LEVER_DEFAULTS.items()), lever
        before = _log(f).count(BW.LOG_GUESTMENU_RELEASED)
        f._release_netsync()
        return f, before
    f, before = run()
    gm = _gm(f)
    assert gm["lever"] == BW.GUEST_MENU_LEVER_DEFAULTS and gm["bench"] == BW.GUEST_MENU_SENTINELS["bench"]
    assert _log(f).count(BW.LOG_GUESTMENU_RELEASED) == before + 1
    f._release_netsync()
    assert _log(f).count(BW.LOG_GUESTMENU_RELEASED) == before + 1      # nothing set: silent
    bad, _b = run(("release_skip",))
    assert _gm(bad)["lever"]["seat_skip"] == "party"                    # GM0-RELEASE red


def test_gm0_seat_browse_refuse_and_restore_on_the_bench():
    """The S route: `frame 7` (two markers), the REAL Menu press -> `guest` -> the door seats the bench frame (slot 0 BENCH7 lv99, gil and
    exp markers), the chip; Order / Party / Card / Config buzz; a confirm in Item is refused (I1, captures +1, impactful 0); the root Cancel
    restores at the door: fp_after == fp_before, the settle stamped equal one frame after the HUD's Show."""
    f = _fake()
    _bench(f, 7)
    assert f._menu_key_now() == "guest"
    _press(f)
    gm = _gm(f)
    assert gm["seated"] and gm["opens"] == 1 and gm["open"] and gm["session"] and f.ui_state == "MainMenu"
    assert gm["seat"] == {"src": "bench", "frame_age_ms": gm["seat"]["frame_age_ms"], "marker": 7} and gm["seat"]["frame_age_ms"] >= 0
    assert f.save_party[0]["name"] == "BENCH7" and f.save_party[0]["level"] == 99 and f._gm_state["gil"] == 7000007
    assert gm["chip"] == BW.GM_CHIP_VIEW_ONLY and gm["event_enable"] is False and gm["seat_fp"]["value"] and gm["fp"]["equal"] is False
    assert BW.log_gm_seated(7, 2, 4, 2, 7000007) in _log(f)
    f.menu_index = FG.FAKE_GM_MENU_ROWS.index("Order")
    f._menu_step("confirm")
    assert f.ui_state == "MainMenu"                                      # greyed: the buzz, no screen
    f.menu_index = 0
    f._menu_step("confirm")
    assert f.ui_state == "Item"
    f._menu_step("confirm")
    gm = _gm(f)
    assert gm["refused"] == {"count": 1, "last_site": "I1", "last_screen": "Item"} and gm["captures"] == 1 and gm["impactful"] == 0
    assert BW.log_gm_census(BW.GM_CENSUS_I1, "Item") in _log(f)
    f._menu_step("cancel")
    f._menu_step("cancel")
    _step(f, 6)
    gm = _gm(f)
    assert not gm["seated"] and f.ui_state == "FieldHUD" and gm["restore"]["doors"] == 1 and gm["chip"] is None
    assert gm["fp"]["equal"] and gm["fp"]["named"] is None and gm["fp"]["outside_equal"] and gm["event_enable"]
    assert gm["outside_settled"] == {"set": True, "equal": True, "named": None}
    assert f.save_party[0]["name"] == "Zidane" and f._gm_state["gil"] == FG.FAKE_GM_GIL
    assert BW.log_gm_restored(BW.GM_SITE_DOOR) in _log(f)


def test_gm0_why_rows_on_the_bench_no_frame_older_host_elsewhere_leaving_and_link():
    f = _fake()
    _bench(f, 0)
    _press(f)
    assert _gm(f)["why"] == BW.GM_WHY_OLDER                              # no bench host trailer in the cache: caps term first
    f._netsync(["guestmenu", "frame", "7"])
    f._netsync(["guestmenu", "host", "elsewhere"])
    _press(f)
    gm = _gm(f)
    assert gm["why"] == BW.GM_WHY_HOST_ELSEWHERE and not gm["seated"]
    assert gm["door_refused"]["host_elsewhere"] == 0                    # the PRESS refused (its verdict): the door never ran
    assert gm["line"]["text"] == BW.gm_refusal_line_rule(BW.GM_WHY_HOST_ELSEWHERE) and gm["line"]["age"] >= 0
    assert f._netsync_doc()["session"]["overlay"] == "off"             # the selftest role never draws state 29
    f._netsync(["guestmenu", "host", "here"])
    f._netsync(["guestmenu", "frame", "intent", "200"])
    _press(f)
    assert _gm(f)["why"] == BW.GM_WHY_LEAVING
    f._netsync(["guestmenu", "frame", "8"])
    f.netsync["stale"] = True
    _press(f)
    assert _gm(f)["why"] == BW.GM_WHY_LINK and f._menu_refusal.count >= 3


def test_gm0_witness_variants_refuse_data_differs_and_a_key_item_seats():
    for comp in ("preset", "pa", "equip", "sa", "char", "bag"):
        f = _fake()
        _bench(f, 0)
        f._netsync(["guestmenu", "frame", "witness", comp])
        _press(f)
        gm = _gm(f)
        assert gm["why"] == BW.GM_WHY_DATA_DIFFERS and not gm["seated"], comp
        assert f"component {comp}" in _log(f), comp
    f = _fake()
    _bench(f, 0)
    f._netsync(["guestmenu", "frame", "witness", "keyitem"])
    _press(f)
    assert _gm(f)["seated"] and "key item(s) this install does not know (65534)" in _log(f)


def test_gm0_seatfault_restore_skip_events_on_and_poke():
    f = _fake()
    _bench(f)
    party = list(f.save_party)
    f._netsync(["guestmenu", "seat", "fault", "bag"])
    _press(f)
    gm = _gm(f)
    assert gm["why"] == BW.GM_WHY_FAULT and not gm["seated"] and gm["opens"] == 0 and gm["lever"]["seat_fault"] == "off"   # one shot
    assert all(a is b for a, b in zip(party, f.save_party)) and f._gm_state["gil"] == FG.FAKE_GM_GIL     # every family back
    for comp in BW.GM_FP_COMP_NAMES:
        f = _fake()
        _bench(f, 0 if comp == "keyitems" else 7)
        if comp == "keyitems":
            # `frame <marker>` copies the guest's OWN key items and marks (no key-item marker): `restore skip keyitems` over it reads EQUAL
            # (the content folds the same) -- only `frame witness keyitem` (one id this install lacks) makes that leg falsifiable
            f._netsync(["guestmenu", "frame", "witness", "keyitem"])
        f._netsync(["guestmenu", "restore", "skip", comp])
        _press(f)
        f._menu_step("cancel")
        _step(f, 6)
        gm = _gm(f)
        assert not gm["fp"]["equal"] and gm["fp"]["named"] == comp, (comp, gm["fp"])
    f = _fake()
    _bench(f)
    f._netsync(["guestmenu", "events", "on"])
    f._netsync(["guestmenu", "poke"])
    _press(f)
    assert _gm(f)["event_enable"] is True and BW.LOG_GM_EVENTS_ON in _log(f) and _gm(f)["lever"]["poke"] == "off"   # GM0-FREEZE red
    f._menu_step("cancel")
    _step(f, 6)
    gm = _gm(f)
    assert not gm["fp"]["outside_equal"] and gm["fp"]["outside_named"] == "events" and gm["outside_settled"]["named"] == "events"


def test_gm0_forced_close_by_fireclose_its_line_and_last_close():
    f = _fake()
    _bench(f)
    f._netsync(["guestmenu", "fireclose", "scene"])
    assert BW.log_guestmenu_fireclose(BW.GM_CAUSE_SCENE, "no_seat") in _log(f) and _gm(f)["closes"]["scene"] == 0
    _press(f)
    f._menu_step("confirm")                                              # into Item
    f._netsync(["guestmenu", "fireclose", "scene"])
    gm = _gm(f)
    assert gm["closes"]["scene"] == 1 and gm["close_pending"] and gm["close_line"]["text"] == BW.gm_close_line_rule(BW.GM_CAUSE_SCENE)
    _step(f, 8)
    gm = _gm(f)
    assert not gm["seated"] and not gm["close_pending"] and gm["last_close"]["cause"] == "scene" and gm["last_close"]["end"] == "done"
    assert gm["last_close"]["from"] == "Item" and gm["fp"]["equal"] and f.ui_state == "FieldHUD"
    f._netsync(["guestmenu", "fireclose", "leave"])
    assert BW.log_guestmenu_fireclose(BW.GM_CAUSE_LEAVE, "no_seat") in _log(f)       # GM0-REOPEN: after the session a no-op
    f._netsync(["guestmenu", "close", "old"])
    _press(f)
    f._netsync(["guestmenu", "fireclose", "leave"])
    assert BW.log_guestmenu_fireclose(BW.GM_CAUSE_LEAVE, "old") in _log(f) and _gm(f)["seated"]
    f._netsync(["guestmenu", "close", "act"])
    f._netsync(["guestmenu", "close", "fault", "root"])
    f._netsync(["guestmenu", "fireclose", "leave"])
    _step(f, 4)
    gm = _gm(f)
    assert gm["closes"]["faults"] == 1 and gm["last_close"]["end"] == "fault" and gm["event_enable"] and not gm["seated"]


def test_gm0_quit_waits_and_quit_under_close_leaves_events_off():
    def run(faults=()):
        f = _fake(faults=faults)
        _bench(f)
        _press(f)
        f.quit_prompt = True
        f._netsync(["guestmenu", "fireclose", "leave"])
        _step(f, 6)
        waited = _gm(f)["seated"] and _gm(f)["close_pending"]
        f.quit_prompt = False
        _step(f, 8)
        return f, waited
    f, waited = run()
    assert waited and _gm(f)["event_enable"] and _gm(f)["last_close"]["end"] == "done"
    bad, waited = run(("quit_under_close",))
    assert not waited and _gm(bad)["event_enable"] is False                     # GM0-QUIT red


def test_gm0_hole_key_caps_and_the_overlay_on_a_client():
    """A client: an unmirrored session guest is refused not_mirroring (GM0-HOLE; `old`: its OWN menu opens unseated); a mirroring guest
    with a b3 host seats the host's party from the wire (GM0-KEY); `caps off` reads older, audible, as s121 (GM0-CAPS-a); state 29 on
    `session.overlay` while the refusal line lives, never over the peer-lost line (CR-2)."""
    f = _fake()
    _client(f, mirroring=False)
    assert f._menu_key_now() == "audible"
    _press(f)
    gm = _gm(f)
    assert gm["why"] == BW.GM_WHY_NOT_MIRRORING and not gm["open"] and f._menu_refusal.count == 1
    assert f._netsync_doc()["session"]["overlay"] == BW.OVERLAY_NAME_GUEST_MENU
    f.coop_follow["connected"] = False
    assert f._netsync_doc()["session"]["overlay"] != BW.OVERLAY_NAME_GUEST_MENU  # the peer lost: the connecting line outranks 29
    f.coop_follow["connected"] = True
    f._netsync(["guestmenu", "old"])
    _press(f)
    gm = _gm(f)
    assert gm["open"] and not gm["seated"] and f.ui_state == "MainMenu"
    f2 = _fake()
    _client(f2)
    assert f2._menu_key_now() == "guest"
    _press(f2)
    gm = _gm(f2)
    assert gm["seated"] and gm["seat"]["src"] == "wire" and gm["seat"]["frame_age_ms"] == -1 and f2._gm_state["gil"] == FG.FAKE_GM_HOST_GIL
    assert BW.log_gm_seated(None, 3, 2, 3, FG.FAKE_GM_HOST_GIL) in _log(f2)
    f3 = _fake()
    _client(f3)
    f3._netsync(["guestmenu", "caps", "off"])
    _press(f3)
    assert _gm(f3)["why"] == BW.GM_WHY_OLDER and f3._menu_refusal.count == 1 and "main menu suppressed (following guest)" in _log(f3)
    f4 = _fake()
    _client(f4, caps=BW.CAPS_S167)                                      # an s167 host (no b3)
    _press(f4)
    assert _gm(f4)["why"] == BW.GM_WHY_OLDER and _gm(f4)["caps"] == {"own": BW.CAPS_S168, "peer": BW.CAPS_S167, "on": False}


def test_gm0_triggers_close_a_seated_client_and_lc1_forgets_at_a_host_epoch():
    def seated():
        f = _fake()
        _client(f)
        _press(f)
        assert _gm(f)["seated"]
        return f
    f = seated()
    f.host_intent(200)
    _step(f, 10)
    assert _gm(f)["closes"]["leave"] == 1 and not _gm(f)["seated"]
    f = seated()
    f.host_at(battle=True, battle_nonce=4)
    _step(f, 10)
    assert _gm(f)["closes"]["cut"] == 1 and f._gm["cut_closed"] == 4
    f.host_at(epoch=1)
    _step(f, 1)
    assert f._gm["cut_closed"] == -1                                     # LC1: a host epoch change forgets the memory
    f = seated()
    f.host_at(flags=BW.HF_CONTROL | BW.HF_ON_FIELD | BW.HF_TITLE)
    _step(f, 10)
    assert _gm(f)["closes"]["title"] == 1
    f = seated()
    f.host_at(flags=BW.HF_CONTROL | BW.HF_ON_FIELD | BW.HF_SCENE)
    _step(f, 10)
    assert _gm(f)["closes"]["scene"] == 1
    f = seated()
    f.unfollow_ramp()
    _step(f, 10)
    assert _gm(f)["closes"]["ending"] == 1


@pytest.mark.parametrize("fault, cause, poke", [("leave_ignored", "leave", lambda f: f.host_intent(200)),
                                                ("cut_ignored", "cut", lambda f: f.host_at(battle=True, battle_nonce=4)),
                                                ("title_ignored", "title", lambda f: f.host_at(flags=BW.HF_TITLE)),
                                                ("scene_ignored", "scene", lambda f: f.host_at(flags=BW.HF_ON_FIELD | BW.HF_SCENE))])
def test_each_ignored_trigger_fault_keeps_the_menu_open(fault, cause, poke):
    f = _fake(faults=(fault,))
    _client(f)
    _press(f)
    poke(f)
    _step(f, 10)
    assert _gm(f)["closes"][cause] == 0 and _gm(f)["seated"]


def test_the_menu_faults_turn_their_rows_red():
    # unmirrored_open: GM0-HOLE seats an unmirrored session guest
    f = _fake(faults=("unmirrored_open",))
    _client(f, mirroring=False)
    _press(f)
    assert _gm(f)["seated"]
    # caps_ignored: GM0-CAPS-a under `caps off` -- the host sends no section 12 to a word without b3, so the blind predicate falls to
    # term 7 and the guest reads `no_data` and its words where s121's `older` belongs
    for faults, why in (((), BW.GM_WHY_OLDER), (("caps_ignored",), BW.GM_WHY_NO_DATA)):
        f = _fake(faults=faults)
        _client(f)
        f._netsync(["guestmenu", "caps", "off"])
        _press(f)
        assert _gm(f)["why"] == why and _gm(f)["line"]["text"] == BW.gm_refusal_line_rule(why), faults
    # stall_open: an unmirrored guest in a stall gets its OWN menu (GM0-STALL-WHO)
    for faults, opens in (((), False), (("stall_open",), True)):
        f = _fake(faults=faults)
        _client(f, mirroring=False)
        f.coop_follow["valid"] = False
        _press(f)
        assert _gm(f)["open"] is opens and not _gm(f)["seated"], faults
    # seat_at_press: an intent inside the HUD's hide fade still seats (GM0-DOOR)
    for faults, seats in (((), False), (("seat_at_press",), True)):
        f = _fake(faults=faults)
        _bench(f)
        f.gm_fade_ms = 200
        f._menu_step("menu")
        f._netsync(["guestmenu", "frame", "intent", "200"]) if not seats else None
        f._gm["intent"] = 200
        _step(f, 10)
        assert _gm(f)["seated"] is seats, faults
    # capture_leak: a seated confirm runs its stock body uncounted (GM0-REFUSE-x)
    f = _fake(faults=("capture_leak",))
    _bench(f)
    _press(f)
    assert f.gm_confirm(BW.GM_CENSUS_E1) == -1
    gm = _gm(f)
    assert gm["refused"]["count"] == 0 and gm["captures"] == 0 and gm["impactful"] == 1
    # capture off (the lever): counted as a pass, the restore still equal (GM0-RESTORE green while REFUSE red)
    f = _fake()
    _bench(f)
    f._netsync(["guestmenu", "capture", "off"])
    _press(f)
    assert f.gm_confirm(BW.GM_CENSUS_E1) == BW.GM_CV_PASS and _gm(f)["passes"] == 1 and _gm(f)["impactful"] == 1
    f._menu_step("cancel")
    _step(f, 6)
    assert _gm(f)["fp"]["equal"]
    # restore_skip (the fault): no lever, party named
    f = _fake(faults=("restore_skip",))
    _bench(f)
    _press(f)
    f._menu_step("cancel")
    _step(f, 6)
    assert _gm(f)["fp"]["named"] == "party" and _gm(f)["lever"]["restore_skip"] == "off"
    # own_values: nothing seated -- the guest's own party drawn (GM0-BROWSE / GM0-SEAT)
    f = _fake(faults=("own_values",))
    _bench(f)
    _press(f)
    assert _gm(f)["seated"] and f.save_party[0]["name"] == "Zidane"
    # slot_keyed: a party with a gap seats the wrong member's section-12 data (GM0-SEAT)
    for faults in ((), ("slot_keyed",)):
        f = _fake(faults=faults)
        f.save_party = [dict(FG.FAKE_PARTY[0]), None, dict(FG.FAKE_PARTY[1]), None]
        _bench(f)
        frame = f._gm["frame"]
        _press(f)
        vivi = f.save_party[2]
        want = next(m["exp"] for m in frame["block"]["members"] if m["char"] == 1)
        assert (vivi["exp"] == want) is (not faults), faults
    # pause_closed: a close request on Pause with no seat counts and leaves Pause (decision 18: Pause excluded)
    for faults, counted in (((), 0), (("pause_closed",), 1)):
        f = _fake(faults=faults)
        _bench(f)
        f.ui_state = "Pause"
        f._netsync(["guestmenu", "fireclose", "leave"])
        assert _gm(f)["closes"]["leave"] == counted, faults
    # dialog_drop_lifted: a mirroring guest's press under a window closes the window (GM0-DIALOG-PATH (b))
    for faults, stays in (((), True), (("dialog_drop_lifted",), False)):
        f = _fake(faults=faults)
        _client(f)
        f.texts = ["a line"]
        assert f._menu_key_now() == "dialog"
        f._menu_step("menu")
        assert bool(f.texts) is stays, faults


def test_settle_same_frame_misses_a_queued_tag4_write_on_the_world():
    """CR-3: on the world the settle restamps one frame AFTER the HUD's Show, so MenuOpenEvent's queued tag-4 write shows on
    `outside_settled` (named events) though `fp.outside_equal`, stamped at the door, cannot see it; `settle_same_frame` misses it."""
    def run(faults=()):
        f = _fake(faults=faults, field=0)
        f.ui_state = "WorldHUD"
        f.world["id"] = 9011
        f.gm_tag4_event = (100, 0x04)
        _bench(f)
        _press(f)
        assert _gm(f)["seated"]
        f._menu_step("cancel")
        _step(f, 8)
        return _gm(f)
    gm = run()
    assert gm["fp"]["outside_equal"] and gm["outside_settled"]["named"] == "events" and gm["uid0_vars"] and gm["sysvar192"] == 0
    assert run(("settle_same_frame",))["outside_settled"]["equal"] is True


def test_a_backstop_restores_and_a_load_drops_the_record():
    f = _fake()
    _bench(f)
    _press(f)
    f.gm_backstop(BW.GM_SITE_REPLACE_TITLE)
    gm = _gm(f)
    assert not gm["seated"] and gm["restore"]["backstops"]["replace"] == 1 and gm["fp"]["equal"]
    f = _fake()
    _bench(f)
    _press(f)
    f.gm_load()
    f.gm_backstop(BW.GM_SITE_LOAD_ENTRY)
    assert _gm(f)["restore"]["drops"] == 1 and BW.LOG_GM_DROPPED in _log(f)


# ================================================================================================ COOP_PEER
def _host_frame(caps, digest=0x1234ABCD, place=4):
    return CP.parse_frame(CP.build_pos_frame(0, wire=15, rot=(0.0, 0.0, 0.0, 1.0), anim_frame=0, frame_n=0,
                                             trailer=CP.build_world_trailer(caps=caps, place=place, world=9011 if place == 4 else 0,
                                                                            pos=(68.0, 0.0, -444.0), rot=(0.0, 0.0, 0.0, 1.0),
                                                                            digest=digest)))[1]


def _sent(m, now=1.0):
    return CP.parse_world_trailer(CP.parse_frame(m.outgoing(now, 15)[0])[1])


def test_serve_guests_auto_caps_adopt_b3_from_an_s168_host():
    """decision 35's T2 prerequisite: an s168 host's guest speaks 0x000B (auto); an s167 host's 0x0003; an s166's 0x0001; b3 is never
    adopted without b1 (an s168 engine never speaks one without the other); `--caps 3` pins an s167-shaped guest."""
    for host, want in ((CP.CAPS_S168, 0x0B), (CP.CAPS_S167, 0x03), (CP.CAPS_S166, 0x01), (CP.CAP_WORLD_POSE | CP.CAP_GUEST_MENU, 0x01)):
        g = CP.GuestModel()
        g.on_host_frame(CP.TYPE_POS, _host_frame(host), 0.0)
        assert g.caps_now() == want and _sent(g)["caps"] == want, hex(host)
    walk = CP.GuestModel(walk=CP.WorldWalkPlan(out_s=0.0, load_s=0.0))
    walk.on_host_frame(CP.TYPE_POS, _host_frame(CP.CAPS_S168), 0.0)
    tr = _sent(walk)
    assert tr["caps"] == 0x0B and tr["digest"] == 0x1234ABCD                     # the digest still rides b1
    pinned = CP.GuestModel(caps=CP.CAPS_S167)
    pinned.on_host_frame(CP.TYPE_POS, _host_frame(CP.CAPS_S168), 0.0)
    assert pinned.caps_now() == 3 and CP._caps_text(3).endswith("an s167-shaped guest, no guest menu)")
    assert CP._caps_text(0x0B) == "0x000B (pinned)" and "0x000B from an s168 host" in CP._caps_text("auto")
    assert CP._caps_text(1).endswith("an s166-shaped guest, no fingerprint)") and CP._parse_caps("0xB") == 0x0B


def _state_payload(with12=True):
    ms = [BW.gm_member(0, 0, 1, 4242, 20, [25, 0]), BW.gm_member(2, 2, 3, 3333, 21, [10, 0])]
    p = BW.append_section(b"", BW.SECTION_PARTY, b"\x00") + CP.fp_section_bytes(9011, [1, 2, 3, 4, 5, 6])
    if with12:
        p += CP.menu_section_bytes(99999, [9], ms)
    p = BW.append_section(p, BW.SECTION_DIALOG, bytes(BW.DIALOG_HEADER_LEN + 1))
    return BW.append_section(p, BW.SECTION_DRESS, b"\x00\x00\x00")


def test_section_12_decoded_in_the_dump_where_pose_and_a_tape_census():
    p = _state_payload()
    m = CP.menu_section_of(p)
    assert m["gil"] == 99999 and [x["char"] for x in m["members"]] == [0, 2] and m["used"] == [9] and m["len"] > 0
    text = CP.describe_frame(CP.TYPE_STATE, p)
    assert "section 12" in text and "gil 99999 members 2 [0,2] used 1" in text
    old = _state_payload(False)
    assert CP.menu_section_of(old) is None and "section 12" not in CP.describe_frame(CP.TYPE_STATE, old)
    assert CP.frame_pose(p)["menu"]["gil"] == 99999 and CP.frame_pose(old)["menu"] is None
    recs = [CP.Record(0.1 * i, CP.DIR_HOST, CP.build_frame(CP.TYPE_STATE, _state_payload(i % 2 == 0), wire=15)) for i in range(4)]
    census = CP.tape_menu_sections(recs)
    assert census["frames"] == 4 and census["with12"] == census["readable"] == census["order_ok"] == 2 and census["first"]["gil"] == 99999
    assert census["len_min"] == census["len_max"] == m["len"]


def test_replay_host_carries_a_v15_tapes_section_12_as_recorded():
    """A restamp touches the version byte only: section 12 reaches the guest as recorded (decision 35's T2 rows); an s167 guest's walker
    skips the unknown id by its length (its sections 11, 7 and 8 read as without it)."""
    frame = CP.build_frame(CP.TYPE_STATE, _state_payload(), wire=15)
    out = CP.restamp(frame, 15)
    assert out == frame and CP.menu_section_of(CP.parse_frame(out)[1]) == CP.menu_section_of(CP.parse_frame(frame)[1])
    v14 = CP.build_frame(CP.TYPE_STATE, _state_payload(), wire=14)
    up = CP.restamp(v14, 15)
    assert up[1] == 15 and up[2:] == v14[2:]
    with12, without = _state_payload(), _state_payload(False)
    for sid in (BW.SECTION_FP, BW.SECTION_DIALOG, BW.SECTION_DRESS, BW.SECTION_PARTY):
        assert BW.old_try_read_section(with12, sid) == BW.old_try_read_section(without, sid), sid
