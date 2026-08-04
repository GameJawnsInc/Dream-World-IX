"""The eblint LOCK-HYGIENE checks (studies/movement/SURVEY.md 10 Tier-2 item 6).

Calibration facts these tests encode (the all-818-real-field sweep, 2026-08-03): the gate-under-lock
checks trip ZERO stock sites; the unpaired-lock check trips only stock's own cross-object-choreography
residue (71 sites -- the survey's ~92 "unresolved" tail); and the naive tread-freeze signature was
FALSIFIED by stock (518 working lock+Wait tag-2 sites, e.g. field 51's exit region) and deliberately
does not exist. Kit emissions must lint with zero lock warnings -- pinned here."""
from __future__ import annotations

import pytest

from ff9mapkit import data, eblint
from ff9mapkit.content import cutscene as _cutscene
from ff9mapkit.content import conductor as _conductor
from ff9mapkit.content import event as _event
from ff9mapkit.content import region as _region
from ff9mapkit.eb import EbScript, edit, opcodes

ZONE = [(-100, -100), (100, -100), (100, 100), (-100, 100)]


def _lock_warnings(issues):
    """Just the new lock-hygiene classes (not the pre-existing dangling-call / structural warnings)."""
    keys = ("DisableMove with no EnableMove", "IsMovementEnabled guard", "dispatches (while locked)")
    return [i for i in issues if i.severity == "warning" and any(k in i.message for k in keys)]


def _player_entry(eb_bytes) -> int:
    from ff9mapkit.content.ladder import find_player_entry
    return find_player_entry(EbScript.from_bytes(eb_bytes))


# ------------------------------------------------------------------ kit emissions are clean ---

def test_blank_field_has_no_lock_warnings():
    assert _lock_warnings(eblint.lint_eb(data.blank_field_bytes())) == []


def test_kit_lock_lanes_are_clean():
    # every Tier-1 lock emitter in one field: a locked press event (inline bracket), a locked tread
    # event (player-func delegation), and an NPC talk bracket -- zero lock warnings
    from ff9mapkit.content import npc as _npc
    out = data.blank_field_bytes()
    out = _npc.inject_npc(out, 0, -500, talk_text_id=62)
    out = _event.inject_events(out, [
        {"zone": ZONE, "body": _event.message(63), "once_flag": None, "action": True, "lock": True},
        {"zone": [(300, 300), (500, 300), (500, 500), (300, 500)],
         "body": _event.message(64), "once_flag": None, "lock": True, "lock_menu": True},
    ])
    assert _lock_warnings(eblint.lint_eb(out)) == []


def test_forced_ate_is_clean_and_terminated():
    # the region locks and delegates to a player func that WARPS -- the callee credit; and the tread
    # body is structurally terminated (the trailing runtime-unreachable RETURN)
    out = _cutscene.inject_forced_ate(data.blank_field_bytes(), ZONE, 4005)
    issues = eblint.lint_eb(out)
    assert _lock_warnings(issues) == []
    assert not [i for i in eblint.errors(issues) if "runs off the end" in i.message]


def test_watchdog_and_grant_spin_are_clean():
    # the watchdog: DisableMove in an infinite poller with an unreachable RETURN -> exempt by
    # construction; the narration grant-spin: reads sysvar 2 under its own lock to CATCH the entry
    # grant -- must never match the verbatim-guard pattern
    out = _conductor.inject_watchdog(data.blank_field_bytes())
    steps = [_cutscene.say(70), _cutscene.wait(10)]
    out = _cutscene.inject_cutscene(out, steps, grant_spin=True,
                                    watchdog_flag=_conductor.WATCHDOG_MAP_FLAG)
    assert _lock_warnings(eblint.lint_eb(out)) == []


# ------------------------------------------------------------------ the defect classes fire ---

def test_unpaired_lock_warns():
    body = opcodes.DISABLE_MOVE + opcodes.wait(30) + opcodes.RETURN
    out = edit.add_function(data.blank_field_bytes(), 0, 30, body)
    hits = [i for i in _lock_warnings(eblint.lint_eb(out)) if "DisableMove with no EnableMove" in i.message]
    assert len(hits) == 1 and "entry0/tag30" in hits[0].where


def test_unpaired_lock_exempts_a_called_subroutine():
    # the same unbalanced body, but INVOKED via RunScriptSync from a balanced caller -- the caller
    # owns the bracket (stock's lock-in-callee / enable-in-caller split), so no warning
    raw = data.blank_field_bytes()
    pe = _player_entry(raw)
    out = edit.add_function(raw, pe, 61, opcodes.DISABLE_MOVE + opcodes.wait(30) + opcodes.RETURN)
    caller = (opcodes.run_script_sync(2, 250, 61) + opcodes.ENABLE_MOVE + opcodes.RETURN)
    out = edit.add_function(out, 0, 31, caller)
    assert [i for i in _lock_warnings(eblint.lint_eb(out))
            if "DisableMove with no EnableMove" in i.message] == []


def test_unpaired_lock_credits_a_delegated_enable():
    # lock here, EnableMove in the statically-resolved callee -- stock's B3 (889 brackets): no warning
    raw = data.blank_field_bytes()
    pe = _player_entry(raw)
    out = edit.add_function(raw, pe, 61, opcodes.wait(10) + opcodes.ENABLE_MOVE + opcodes.RETURN)
    trigger = opcodes.DISABLE_MOVE + opcodes.run_script_sync(2, 250, 61) + opcodes.RETURN
    out = edit.add_function(out, 0, 30, trigger)
    assert [i for i in _lock_warnings(eblint.lint_eb(out))
            if "DisableMove with no EnableMove" in i.message] == []


def test_gate_under_lock_warns():
    # the shipped gate-inside-talk class: the verbatim MOVEMENT_GATE embedded inside a lock bracket
    # always early-returns (the Lantern Hall ferry bug shape)
    body = _event.lock_bracket(_region.MOVEMENT_GATE + opcodes.wait(5)) + opcodes.RETURN
    out = edit.add_function(data.blank_field_bytes(), 0, 30, body)
    hits = [i for i in _lock_warnings(eblint.lint_eb(out)) if "guard reached under" in i.message]
    assert len(hits) == 1


def test_callee_head_gate_warns():
    # dispatching (while locked) into a function that OPENS with the guard -- the delegated flavor
    raw = data.blank_field_bytes()
    pe = _player_entry(raw)
    out = edit.add_function(raw, pe, 61, _region.MOVEMENT_GATE + opcodes.wait(5) + opcodes.RETURN)
    out = edit.add_function(out, 0, 30, _event.locked_dispatch(61) + opcodes.RETURN)
    hits = [i for i in _lock_warnings(eblint.lint_eb(out)) if "dispatches (while locked)" in i.message]
    assert len(hits) == 1


def test_gate_before_the_lock_is_clean():
    # the correct stock shape -- guard at the head, THEN the bracket: no warning
    body = _region.MOVEMENT_GATE + _event.lock_bracket(opcodes.wait(5)) + opcodes.RETURN
    out = edit.add_function(data.blank_field_bytes(), 0, 30, body)
    assert [i for i in _lock_warnings(eblint.lint_eb(out)) if "guard" in i.message] == []


# ------------------------------------------------------------------ cross-field warp grants ---

def _strip_enable_move(eb_bytes) -> bytes:
    """Rewrite every EnableMove instruction to DisableMove (same length) -- a structurally-clean field
    that never grants control."""
    from ff9mapkit.eb import disasm
    eb = EbScript.from_bytes(eb_bytes)
    out = bytearray(eb_bytes)
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            for ins in disasm.iter_code(eb.data, f.abs_start, f.abs_end):
                if ins.op == 0x2E:
                    out[ins.off] = 0x2D
    return bytes(out)


def test_enables_movement():
    raw = data.blank_field_bytes()
    assert eblint.enables_movement(raw) is True
    assert eblint.enables_movement(_strip_enable_move(raw)) is False
    assert eblint.enables_movement(b"\x00\x01") is None


def test_warp_grants_cross_check():
    src = edit.add_function(data.blank_field_bytes(), 0, 30,
                            _event.warp(30991) + opcodes.RETURN)
    dst_ok = data.blank_field_bytes()
    dst_bad = _strip_enable_move(dst_ok)
    assert eblint.lint_warp_grants({30990: src, 30991: dst_ok}) == []
    bad = eblint.lint_warp_grants({30990: src, 30991: dst_bad})
    assert len(bad) == 1 and "Field(30991)" in bad[0].message and "field 30990" in bad[0].where
    # a destination OUTSIDE the set is out of scope
    assert eblint.lint_warp_grants({30990: src}) == []


def test_warp_targets_reads_literals_only():
    src = edit.add_function(data.blank_field_bytes(), 0, 30, _event.warp(4005) + opcodes.RETURN)
    assert 4005 in eblint.warp_targets(src)
