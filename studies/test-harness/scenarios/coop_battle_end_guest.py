"""B4/B5 STAGES 5 + 6 -- THE GUEST VICTORY PRESENTATION (s104) AND THE GUEST'S EXIT WITH THE HOST (s105), the solo
bench, run unattended.

THE GAP (studies/battle-coop/B4-B5-DESIGN.md 3.6, 5.3, 5.4). At the host's win the guest's diorama kept a live fight
on screen (no poses, no fanfare, the HUD up) and left only on the stale-lane leave, 2-3 s after the host -- returning
`btl_result` 0 (the F3.3 residue) and able to boot a fight that was already over.
  s104 (stage 5): EndTick reads the host's end block (stage 4) and, once per boot, INJECTS the stock tail -- a victory
    -> PHASE_MENU_OFF + SEQ_MENU_OFF_VICTORY_WITH_ENEMY (fanfare 5, win poses, the victory camera; no per-unit settle,
    so a host-hidden enemy cannot stall it); a no-pose / other end -> PHASE_CLOSE + SEQ_DEFEATCLOSE_FADEOUT with the
    host's result; a defeat / escape -> the HUD off and HELD (stage 12 injects those). R8 at the head of
    ManageBattleEnd keeps every stock end write out (the achievement, DEFEAT->GAMEOVER); watchdogs W1 (the victory
    camera's callback never fires) and W2 (MENU_OFF stalls: names its blocker).
  s105 (stage 6): the host's exit (result screen Hide, Game Over, the title) LATCHES once per boot and the guest
    Leave()s at 1 Hz, never into a fade; any Leave of a FINISHED fight settles the return -- the host's result stamped
    into btl_result (NO_POSE -> VICTORY; a DEFEAT only in a NoGameOver scene; GAMEOVER/INITIAL never), the battle song
    shut down, the injected end fade lifted.

THE BENCH. Field 30602, `netsync selftest 1`, `netsync dioboot 67 0`; `netsync endbench <op>` fabricates the HOST's
end block through the real codec and ParseView and serves it as the BENCH end (accepted by the guest as `e.Bench`).
Each leg needs its own fresh boot (the presentation happens once per boot) and starts with `endbench clear` (a
fabricated end stays armed across a dioboot and would inject at once). Invariants (gil, the bag, every member's
level/exp/AP, the kill counters, the cards) are read from the SANDBOX autosave a warp writes (_coop_battle.fingerprint).

WHAT IS PROVEN -- stage 5 (S5-*):
  A  VICTORY: the boot baseline; a bench-opened stock window closes at the injection; the injection (MENU_OFF + _WITH_
     ENEMY), the HUD hidden; PHASE_VICTORY, result 1 and the fanfare/end-load flags within 2 s, MENU_OFF lasting < 1.5 s
     with no watchdog (the green half of D's pair); after `ui 1` the WAIT seq within 10 s (or W1, logged); R8 holding
     and RISING with its one line; nothing written (ach held delta 0, ach_enemy_no unchanged); a warm return reading
     result 1; every invariant byte-identical. A PNG of the poses: s5-A-victory-poses.png (READ it).
  B  negatives in one boot: `event` (var 32) presents nothing; `defeat` HOLDS (HUD off, phase 4, the HELD line);
     `escape` changes nothing more; a `victory` in the same boot still injects.
  C  close variants (a boot each): `nopose` -> close (phase 8 seq 0) with result 2 and R8 rising; `other 7` -> 7;
     `other 5` (interruption) -> 5, R8 rising.
  D  W2 RED/GREEN: `endbench guest settle` makes the victory write SEQ_MENU_OFF_VICTORY (the per-unit settle): MENU_OFF
     holds > 8 s, then W2 fires naming "unsettled unit(s)", forces the tail, and R8 rises -- the proof _WITH_ENEMY is
     load-bearing (A's < 1.5 s is the other half).
  E  the stage-off red inside the stage DLL: `endbench guest off` + victory = the pre-stage guest (nothing injected,
     `why` names the lever, phase 4, the HUD up, no END/R8 line) -- the instrument stays live.
  F  NetSyncEnd.SelfTest OK with its `present 48` section.
WHAT IS PROVEN -- stage 6 (S6-*):
  A  `ui 1` + `state 6` latches nothing (End is not Hide); `state 7` latches result-hide and the end-leave fires at
     once (tries 1, requested, settled via end-leave, stamp 1, the song shut); the seven log lines in order; on the
     field: booted false, a WARM return, result 1 stamped, the end fade lifted -- the field frame reads LIT over the
     WHOLE frame (cb.settled_frame: shot once FF9Wipe_FadeInEx(256)'s 30 Hz ramp has run out, until two shots agree;
     s6-A-field-after-return-<i>.png), every invariant byte-identical. The detector is calibrated in leg F (F3).
  B  the stamp's own receipt: `nopose` (diorama result 2) returns result 1 (stamped_was 2, stamp_host 2); `other 7`
     returns 7.
  C  a held CLOSE + DEFEAT (`other 3`) carries 3 into a NoGameOver scene (C1: a scene from NOGO_SCENES, the booted
     scene's own `scene_info.no_gameover` the judge -- "not reached" if none boots as one), nothing in a Game Over
     scene (C2, scene 67: no stamp, field result 0 -- the diorama's InitBattle value), and lifts no fade either way.
  D  Game Over / the title: `other 6` + `ui 2` -> trigger game-over, settled, no stamp, a return to the bench field,
     the Title never shown, field result 0; `ui 3` -> trigger title.
  M  a mid-fight `dioleave` (no end block) settles NOTHING.
  E  a LATE boot (the host already hidden its result screen): nothing presented, `why` "the host already left its
     battle (result-hide)", requested, a warm return (fade deferrals noted).
  F  the stage DLL's own red: `endbench exit off` -> the trigger still latches but no end-leave (requested false,
     tries 0, `why` names the lever), the diorama holds >= 5 s with R8 rising; a manual `dioleave` settles nothing
     (no song shutdown, no lift) and the field reads the diorama's own 2. F3: that UN-LIFTED return's field frame,
     measured exactly as A6's (same wait, same whole-frame reading), reads BLACK -- the frame detector's calibration
     inside the stage DLL, and the [I] black-return claim the lift exists for. F3 red means A6 proves nothing: either
     the detector cannot see black, or the return is not black without the lift.
  S  NetSyncEnd.SelfTest OK with its `exit 280` section.
  S56-INV  the whole run's invariants byte-identical, setup to end.   S56-R  `reset` restores both levers.
NOT PROVEN HERE (two-machine): the live-lane nonce gate (e.Nonce == BootedWireNonce) on a real relay; relay timing
between the final death and the end block; music on the warm and cold lanes; the late-join DECLINE (box 21) and the
skip stamp (box 18) -- a solo dioboot never sets the watcher's wire nonce (design 3.8 item 3).

CALIBRATION.
  * PRE-STAGE-5 DLL (s103): S5-P0 (no `netsync.battle.end`) and S5-P1 (`endbench guest on` FAILS "unknown op 'guest'")
    RED. Behavioural reds: leg A's `endbench victory` serves the bench end (S5-A2 GREEN: peer.end kind 2, bench) but
    nothing is presented -- S5-A0 and A3..A9 RED (phase stays 4, result 0 on the field too, the HUD shown, the bmenu
    window stays open, no END / R8 line); B2-B4, C1-C3 RED; D, E RED (no lever); F RED (the detail ends at "codec 46").
    Every S6 check RED except S6-A7 (leg A still runs -- left by hand -- and writes nothing). GREEN there: S5-S0,
    S5-PRE, S5-A1 (the bench window opens), S5-A2, S5-A10 (nothing written), S5-B1 (the event negative holds either
    way), S6-A7 and S56-INV. (Measured on the stand-in at s103 caps: the same set, minus PRE/A10/A7/INV, which need the
    real autosave.)
  * PRE-STAGE-6 DLL (s104): every S5 check GREEN; S6-P0/P1 RED (no `end_leave`; `endbench exit` "unknown op 'exit'");
    legs A-D run unchanged and go RED where predicted -- after `state 7` the diorama stays booted with r8_hits rising
    and `returns` unchanged (`ui 2` does nothing either), so each leg is left by hand; after the manual `dioleave` B
    reads result 2 (no fold), C1 reads 0 rather than 3 (in a NoGameOver scene), C2 has no end-leave return, A/B may
    return black (no lift); A6 is "not reached" (no end-leave return to photograph); M RED (no `settled` key); E, F
    (F1-F3: no exit lever) RED; S RED (no `exit` section). GREEN in S6 there: A2 (nothing latches on End -- nor on
    anything else) and A7 (the hand-left leg writes nothing). (Stand-in at s104 caps: A2 only -- it writes no
    autosave, so A7 cannot read its invariants.)
  * The DEPLOYED DLL at writing (s99): no `endbench` at all -- every S5/S6 leg "not reached" with that refusal; GREEN
    there: S5-S0, S5-PRE (the instrument) and S56-INV (the run changes nothing: no leg ran); S56-R is RED (no levers).
  * In-run, on the stage DLLs: legs D/E (stage 5) and F (stage 6) are the levers' reds, judged as their own checks.

    py tools/play.py studies/test-harness/scenarios/coop_battle_end_guest.py --field 30602
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file

HarnessError = cb.HarnessError

SELFTEST_PRESENT = "classify 23, chase 162 + pins, codec 46, present 48"
SELFTEST_EXIT = SELFTEST_PRESENT + ", exit 280"
LEVER_OFF_WHY = "the host's victory waits: the calibration lever `endbench guest off`"
EXIT_LEVER_WHY = "the calibration lever `endbench exit off`"
NOT_LATCHED = "the host has not left its battle yet"
LATE_WHY = "the host already left its battle (result-hide)"
W1_LINE = "diorama END watchdog W1: still PHASE_VICTORY + SEQ_VICTORY_CAMERA_MOVE"
W2_LINE = "diorama END watchdog W2: still PHASE_MENU_OFF"
R8_LINE = "diorama R8: ManageBattleEnd refused (phase 6 seq 2"
R8_DONE = "the guest's own end presentation is DONE"
R8_WARN = "with NO injected end"
INJECT_LINE = "diorama END: injected PHASE_MENU_OFF + SEQ_MENU_OFF_VICTORY_WITH_ENEMY"
HELD_LINE = "diorama END: the host's defeat"
#: Battle scenes whose header carries NoGameOver (BTL_SCENE.SetupSceneInfo: `flags & 4`, the u16 at raw16 +4), read off
#: this install's p0data2 scene headers (15 scenes in all; scene 67 is not one): 12 = LB_E080B (one enemy type, one
#: pattern), 336 = TH_E001, 339 = TR_E074D. Tried in order for leg C1; the BOOTED scene's own `scene_info.no_gameover`
#: is the judge, so a wrong guess here costs a "not reached", never a false green.
NOGO_SCENES = (12, 336, 339)

CATALOG = {
    # ---- stage 5
    "S5-S0": "the harness forced the selftest role for this process (Memoria.ini untouched)",
    "S5-PRE": "the invariant instrument reads the sandbox autosave (gil, bag, levels/exp/AP, kill counters, cards)",
    "S5-P0": "the engine publishes `netsync.battle.end.r8_hits` (memoria-patch s104, stage 5)",
    "S5-P1": "`netsync endbench guest on` is accepted (the stage-5 lever exists)",
    "S5-A0": "A: a fresh boot's baseline -- end {injected false, held false, r8_hits 0, kind -1}",
    "S5-A1": "A: the coupling bench -- `bmenu open 0` opens slot 0's stock window (turn.slot 0)",
    "S5-A2": "A: `endbench victory` serves the bench end (peer.end kind 2, bench true)",
    "S5-A3": "A: within a few ticks the end is INJECTED -- injected, action 'victory', inject_phase 5, inject_seq 4 "
             "(_WITH_ENEMY); the window closed (turn.slot and slot_raw -1), hud.shown false, turn.enabled false",
    "S5-A4": "A: the log -- 'stock menu: closed all (end injected)' then 'diorama END: injected PHASE_MENU_OFF + "
             "SEQ_MENU_OFF_VICTORY_WITH_ENEMY'",
    "S5-A5": "A: within 2 s PHASE_VICTORY, result 1, btl_flag bits 32 (the end song) and 64 (the end load); MENU_OFF "
             "lasted < 1.5 s and no watchdog fired",
    "S5-A6": "A: `endbench ui 1` arms W1; the WAIT seq (2) within 10 s with no watchdog, or W1 fired >= 4 s after ui 1 "
             "(its line) and the seq went on to 2",
    "S5-A7": "A: R8 holds -- r8_hits > 0 and RISING over 3 s, r8_first_ms >= 0, one 'diorama R8: ManageBattleEnd refused "
             "(phase 6 seq 2 ...) -- the guest's own end presentation is DONE' line, no 'NO injected end' warning",
    "S5-A8": "A: nothing written -- ach_held delta 0 and ach_enemy_no unchanged",
    "S5-A9": "A: `dioleave` -> a warm return (returns +1) and battle.result reads 1 on the field",
    "S5-A10": "A: every invariant byte-identical across the leg",
    "S5-B1": "B: `endbench event` (var 32) presents nothing for 2 s -- phase 4, not injected, not held, why null",
    "S5-B2": "B: `endbench defeat` HOLDS -- held, not injected, action 'hold', phase 4, hud.shown false, the HELD line",
    "S5-B3": "B: `endbench escape` changes nothing more (held, not injected, action 'hold', phase 4)",
    "S5-B4": "B: a `victory` in the same boot still injects (injected, action 'victory', PHASE_VICTORY within 3 s)",
    "S5-C1": "C: `nopose` -> action 'close', inject_phase 8, inject_seq 0, battle.result 2, R8 rising",
    "S5-C2": "C: `other 7` -> action 'close', battle.result 7, R8 rising",
    "S5-C3": "C: `other 5` (interruption) -> action 'close', battle.result 5, R8 rising",
    "S5-D1": "D (`endbench guest settle`): the victory writes inject_seq 0 and PHASE_MENU_OFF holds for more than 8 s",
    "S5-D2": "D: then W2 fires -- watchdog 'W2', blocker naming 'unsettled unit(s)', the W2 line; PHASE_VICTORY, the seq "
             "on to 2, R8 rising",
    "S5-E1": "E (`endbench guest off`): a victory is NOT presented for 4 s -- not injected, why names the lever, phase 4, "
             "hud.shown true, r8_hits 0, no 'diorama END' / 'diorama R8' line",
    "S5-F1": "F: `endbench selftest` -> 'battle end-block selftest OK (classify 23, chase 162 + pins, codec 46, present 48'",
    # ---- stage 6
    "S6-P0": "the engine publishes `netsync.battle.end.end_leave` (memoria-patch s105, stage 6)",
    "S6-P1": "`netsync endbench exit on` is accepted (the stage-6 lever exists)",
    "S6-A1": "A: a fresh boot -- end_leave.trigger null, why 'the host has not left its battle yet', exit_mode 'on'",
    "S6-A2": "A: victory injected; `ui 1` + `state 6` latch NOTHING (End is not Hide)",
    "S6-A3": "A: `state 7` -> trigger 'result-hide', tries 1, requested, request_ms 0..100 (+1 s per fade deferral), why "
             "null; settled via 'end-leave', stamp 1, stamp_host 1, music_shut",
    "S6-A4": "A: the log in order -- the host left (result-hide ... presented here: victory), end-leave attempt 1, leaving "
             "a finished fight (song shut, stamps 1), LEAVE requested, return settled (-> 1, fade lifted), torn down, "
             "RETURN (warm)",
    "S6-A5": "A: on the field -- booted false, returns +1, last_return 'warm', battle.result 1, stamped 1, wipe_lifted, "
             "latched_ms -1",
    "S6-A6": "A: the field frame after the return reads LIT over the whole frame, measured once the 256-tick lift ramp "
             "has run out and two shots agree (calibrated by S6-F3)",
    "S6-A7": "A: every invariant byte-identical across the leg",
    "S6-B1": "B: `nopose` (diorama result 2) + ui 1 + state 7 -> the field reads 1: stamped_was 2, stamped 1, stamp_host 2",
    "S6-B2": "B: `other 7` + ui 1 + state 7 -> the field reads 7",
    "S6-C1": "C: in a NoGameOver scene (one of NOGO_SCENES, booted and reading scene_info.no_gameover true), a held "
             "CLOSE + DEFEAT (`other 3`) + ui 1 + state 7 carries the DEFEAT: stamp 3, field battle.result 3, "
             "wipe_lifted false",
    "S6-C2": "C: in a Game Over scene (scene 67, reading scene_info.no_gameover false) the same held DEFEAT is a Game "
             "Over in transit, never stamped: stamp -1, field battle.result 0, wipe_lifted false",
    "S6-D1": "D: `other 6` + `ui 2` -> trigger 'game-over', settled, stamp -1, back on the bench field, the Title never "
             "shown, field result 0",
    "S6-D2": "D: `other 6` + `ui 3` -> trigger 'title', back on the bench field, the Title never shown",
    "S6-M1": "M: a mid-fight `dioleave` (no end block) settles NOTHING -- settled false, trigger null, stamp -1",
    "S6-E1": "E: a LATE boot (victory + ui 1 + state 7 armed before dioboot) presents nothing (injected false, why 'the "
             "host already left its battle (result-hide)'), requests the leave, returns warm",
    "S6-F1": "F (`endbench exit off`): the trigger latches (result-hide) but requested false, tries 0, why names the lever; "
             "the diorama stays booted >= 5 s with r8_hits rising",
    "S6-F2": "F: a manual `dioleave` then settles nothing -- settled false, music_shut false, wipe_lifted false; the field "
             "reads the diorama's own 2",
    "S6-F3": "F: the frame detector can say BLACK (a synthetic black frame with one icon-sized overlay reads 'black') "
             "and the UN-LIFTED victory return reads 'lit' -- the field load resets the fade on this bench (measured), "
             "so the lift is stock parity, not load-bearing",
    "S6-S1": "`endbench selftest` -> '... present 48, exit 280'",
    "S56-INV": "the whole run's invariants byte-identical, setup to end (gil, bag, levels/exp/AP, kill counters, cards)",
    "S56-R": "`reset` with `guest settle` and `exit off` left pulled: both 'back ON (released with the harness)' lines, "
             "guest_mode 'on', exit_mode 'on'",
}


# ------------------------------------------------------------------------------------------- reads
def _end(x) -> dict:
    return cb.bend(x)


def _el(x) -> dict:
    v = _end(x).get("end_leave")
    return v if isinstance(v, dict) else {}


def _phase(x):
    return cb.battle(x).get("phase")


def _seq(x):
    return cb.battle(x).get("seq")


def _result(x):
    return cb.battle(x).get("result")


def _shown(x):
    return cb.hud(x).get("shown")


def _r8_rising(g, seconds: float = 3.5, first_s: float = 6.0) -> tuple:
    """R8 holding: the first refusal lands (ManageBattleEnd is reached only once btl_fade_time passes 32 at the WAIT
    seq), then r8_hits RISES over ``seconds`` -- non-decreasing, never judged between two polls (the Byte
    btl_fade_time wraps: 33 of every 256 frames skip the call)."""
    first = cb.poll(g, lambda x: isinstance(_end(x).get("r8_hits"), int) and _end(x)["r8_hits"] > 0, first_s,
                    "the first R8 refusal")
    samples = cb.hold_for(g, seconds)
    vals = [_end(x).get("r8_hits") for x in samples if isinstance(_end(x).get("r8_hits"), int)]
    ok = (first is not None and len(vals) >= 2 and vals[0] > 0 and vals[-1] > vals[0]
          and all(a <= b for a, b in zip(vals, vals[1:])))
    return ok, (f"r8_hits {vals[:1]}..{vals[-1:]} over {seconds:.1f}s ({len(vals)} publish(es))"
                + ("" if first is not None else f"; no R8 refusal within {first_s:.0f}s"))


def _endbench(g, *args) -> tuple:
    return cb.try_ns(g, "endbench", *args)


def _return_frame(g, name: str) -> tuple:
    """The field frame after a return, read ONE way for A6 (lifted) and F3 (un-lifted): wait out the whole
    FF9Wipe_FadeInEx(256) ramp on the wall clock, then shoot until two frames agree, and read every pixel.
    (verdict 'lit' / 'black' / 'dim', or None if never settled or unreadable; detail)."""
    p, light, settled, trail = cb.settled_frame(g, name)
    reads = cb.frame_reads(light) if settled else None
    return reads, (f"{p or 'no shot'}: {reads or ('NOT settled' if light else 'unreadable')} "
                   f"(lit = luma > {cb.LIT_LUMA} on >= {cb.LIT_FRAC:.0%} of pixels, black <= {cb.BLACK_FRAC:.0%}); "
                   f"readings {trail}")


def _synthetic_black_reads() -> str | None:
    """The frame detector's own calibration: a 1280x720 all-black PNG with a booster-icon-sized lit square (the one UI
    overlay a fade leaves) must read 'black'. None if Pillow or the temp write is unavailable."""
    try:
        import tempfile
        from PIL import Image
        im = Image.new("RGB", (1280, 720), (0, 0, 0))
        for x in range(1230, 1266):
            for y in range(680, 716):
                im.putpixel((x, y), (200, 200, 200))
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as fh:
            path = fh.name
        im.save(path)
        return cb.frame_reads(cb.frame_light(path))
    except Exception:                    # noqa: BLE001 - a calibration read never kills the run
        return None


# ------------------------------------------------------------------------------------------- legs' plumbing
def _fresh(g, field: int, scene: int = cb.SCENE) -> tuple:
    """`endbench clear`, a fresh `dioboot <scene> 0` (67 by default), the steady command phase. (state or None, why)."""
    _endbench(g, "clear")
    ok, why = cb.boot(g, scene)
    if not ok:
        cb.back_to_field(g, field)
        return None, why
    st = cb.wait_steady(g)
    if st is None:
        cb.leave(g, field)
        return None, "the diorama never reached its command phase"
    return st, ""


def _out(g, field: int) -> tuple:
    """Back on the field, playable (Leave if still booted), and the bench end cleared."""
    if cb.dio(g.state).get("booted"):
        ok, why = cb.leave(g, field)
    else:
        ok, why = cb.arrive(g, field)
    _endbench(g, "clear")
    return ok, why


def _fp(g, field: int, led: cb.Ledger | None = None):
    fp, why = cb.fingerprint(g, field=field)
    if fp is None:
        g.note(f"invariants unreadable: {why}")
    return fp, why


def _inv_check(led: cb.Ledger, cid: str, before, after, why_b: str = "", why_a: str = "") -> None:
    if before is None or after is None:
        led.check(cid, False, f"not reached: the invariant snapshot failed ({why_b or why_a})")
        return
    diff = cb.fp_diff(before, after)
    led.check(cid, not diff, f"changed: {diff} " + "; ".join(f"{k}: {before.get(k)!r} -> {after.get(k)!r}"
                                                             for k in diff)[:600] if diff else
              f"identical (gil {before.get('gil')}, {len(before.get('items') or [])} bag rows, {len(before.get('players') or [])} "
              f"players; battle_no {before.get('_battle_no')} -> {after.get('_battle_no')})")


# ------------------------------------------------------------------------------------------- the run
def run(g, field: int = cb.FIELD):
    led = cb.Ledger(g, CATALOG, finals=("S56-INV", "S56-R"))
    fp0 = [None, ""]
    try:
        _run(g, led, field, fp0)
    finally:
        g.note(f"Memoria.log archived: {cb.archive_log(g, 'end-guest')}")
        led.close()
        try:
            if cb.dio(g.state).get("booted"):
                cb.leave(g, field)
            fpn, why = _fp(g, field)
            _inv_check(led, "S56-INV", fp0[0], fpn, fp0[1], why)
        except HarnessError as err:
            g.note(f"the final invariant read failed: {str(err)[:160]}")
        _release(g, led)
        led.close(final=True)


def _run(g, led: cb.Ledger, field: int, fp0: list) -> None:
    ok, why = cb.setup(g, field, label="B4/B5 stages 5-6: the guest victory presentation (s104) + exit with the host (s105)")
    led.check("S5-S0", ok, why)
    fp, fwhy = _fp(g, field)
    fp0[0], fp0[1] = fp, fwhy
    led.check("S5-PRE", fp is not None, fwhy or f"gil {fp.get('gil')}, slot {fp.get('slot')}")
    st = g.state
    led.check("S5-P0", cb.has(st, "netsync.battle.end.r8_hits"),
              f"netsync.battle keys: {sorted(cb.nsb(st))}" if cb.has(st, "netsync.battle") else
              "no `netsync.battle` at all (a pre-s100 engine)")
    led.check("S6-P0", cb.has(st, "netsync.battle.end.end_leave"), f"netsync.battle.end keys: {sorted(_end(st))}")
    ok5, why5 = _endbench(g, "guest", "on")
    led.check("S5-P1", ok5, why5 or "accepted")
    ok6, why6 = _endbench(g, "exit", "on")
    led.check("S6-P1", ok6, why6 or "accepted")
    okc, whyc = _endbench(g, "clear")
    if not okc:
        led.close(f"`netsync endbench` does not exist on this engine -- {whyc}")
        return
    # ---- stage 5
    _s5_a(g, led, field)
    _s5_b(g, led, field)
    _s5_c(g, led, field)
    _s5_d(g, led, field, ok5)
    _s5_e(g, led, field, ok5)
    _selftest(g, led, "S5-F1", SELFTEST_PRESENT)
    # ---- stage 6
    _s6_a(g, led, field)
    _s6_b(g, led, field)
    _s6_c(g, led, field)
    _s6_d(g, led, field)
    _s6_m(g, led, field)
    _s6_e(g, led, field)
    _s6_f(g, led, field, ok6)
    _selftest(g, led, "S6-S1", SELFTEST_EXIT)


# ------------------------------------------------------------------------------------------- stage 5
def _s5_a(g, led: cb.Ledger, field: int) -> None:
    g.note("S5-A: the victory, presented")
    cids = [c for c in CATALOG if c.startswith("S5-A")]
    before, bwhy = _fp(g, field)
    st, why = _fresh(g, field)
    if st is None:
        led.unreached(cids, why)
        return
    e0 = _end(st)
    led.check("S5-A0", e0.get("injected") is False and e0.get("held") is False and e0.get("r8_hits") == 0
              and e0.get("kind") == -1, f"end={ {k: e0.get(k) for k in ('injected', 'held', 'r8_hits', 'kind')} }")
    ach0, enemy0 = e0.get("ach_held"), e0.get("ach_enemy_no")
    r0 = cb.dio(st).get("returns")
    music0 = e0.get("music")
    oko, whyo = cb.try_ns(g, "bmenu", "open", 0)
    sto = cb.poll(g, lambda s: s.turn_slot == 0, 3.0, "slot 0's stock window") if oko else None
    led.check("S5-A1", oko and sto is not None, whyo or f"turn.slot={g.state.turn_slot}")
    at = cb.mark(g)
    ok, why = _endbench(g, "victory")
    pe = cb.peer(g.state).get("end") or {}
    led.check("S5-A2", ok and pe.get("kind") == 2 and pe.get("bench") is True, why or f"peer.end={pe}")
    st = cb.poll(g, lambda s: _end(s).get("injected") is True, 2.0, "the injection")
    s = st or g.state
    e = _end(s)
    t = cb.turn(s)
    led.check("S5-A3", st is not None and e.get("action") == "victory" and e.get("inject_phase") == cb.PHASE_MENU_OFF
              and e.get("inject_seq") == 4 and t.get("slot") == -1 and t.get("slot_raw") == -1 and _shown(s) is False
              and t.get("enabled") is False,
              f"end={ {k: e.get(k) for k in ('injected', 'action', 'inject_phase', 'inject_seq', 'why')} } "
              f"turn={ {k: t.get(k) for k in ('slot', 'slot_raw', 'enabled')} } hud.shown={_shown(s)!r} phase={_phase(s)!r}")
    # A5: PHASE_VICTORY within 2 s; MENU_OFF's length read off inject_ms at the first VICTORY publish
    samples, sv = cb.watch(g, lambda x: _phase(x) == cb.PHASE_VICTORY, 2.0)
    menu_off_ms = _end(sv).get("inject_ms") if sv is not None else None      # the engine's clock at the first VICTORY
    sf = cb.poll(g, lambda x: _result(x) == 1 and isinstance(_end(x).get("btl_flag"), int)
                 and _end(x)["btl_flag"] & 32 and _end(x)["btl_flag"] & 64, 1.5, "result 1 + the end-song/end-load flags") \
        if sv is not None else None
    s = sf or sv or g.state
    e = _end(s)
    flag = e.get("btl_flag")
    led.check("S5-A5", sv is not None and sf is not None and isinstance(menu_off_ms, int) and menu_off_ms < 1500
              and e.get("watchdog") is None,
              f"phase={_phase(s)!r} result={_result(s)!r} btl_flag={flag!r} MENU_OFF lasted ~{menu_off_ms!r} ms "
              f"watchdog={e.get('watchdog')!r}; music {music0!r} -> {e.get('music')!r} (5 = the fanfare [I])")
    lines = cb.new(g, at)
    i_closed = next((i for i, ln in enumerate(lines) if "stock menu: closed all (end injected)" in ln), None)
    i_inj = next((i for i, ln in enumerate(lines) if INJECT_LINE in ln), None)
    led.check("S5-A4", i_inj is not None and (i_closed is not None and i_closed < i_inj or not oko),
              cb.grep(lines, "stock menu: closed all", "diorama END"))
    shot, swhy = cb.shot(g, "s5-A-victory-poses")
    g.note(f"poses: {shot or swhy} -- READ it (fanfare, win poses, the victory camera)")
    # A6
    t_ui = time.time()
    oku, whyu = _endbench(g, "ui", "1")
    armed = cb.poll(g, lambda x: _end(x).get("w1_armed") is True, 2.0, "W1 armed")
    samples, s2 = cb.watch(g, lambda x: _seq(x) == 2 and _phase(x) == cb.PHASE_VICTORY, 12.0)
    s = s2 or g.state
    wd = _end(s).get("watchdog")
    lines = cb.new(g, at)
    took = time.time() - t_ui
    if wd and "W1" in wd:
        a6 = s2 is not None and cb.count(lines, W1_LINE) == 1 and took >= 4.0
    else:
        a6 = s2 is not None and wd is None and took <= 10.5
    led.check("S5-A6", oku and armed is not None and a6,
              whyu or f"seq 2 {'reached' if s2 else 'NOT reached'} {took:.1f}s after ui 1; watchdog={wd!r}; "
                      f"{cb.grep(lines, 'watchdog')}")
    # A7/A8
    rising, detail = _r8_rising(g)
    s = g.state
    e = _end(s)
    lines = cb.new(g, at)
    led.check("S5-A7", rising and isinstance(e.get("r8_first_ms"), int) and e["r8_first_ms"] >= 0
              and len([ln for ln in lines if R8_LINE in ln and R8_DONE in ln]) == 1 and cb.count(lines, R8_WARN) == 0,
              f"{detail}; r8_first_ms={e.get('r8_first_ms')!r}; {cb.grep(lines, 'diorama R8')}")
    led.check("S5-A8", isinstance(ach0, int) and e.get("ach_held") == ach0 and isinstance(enemy0, int) and enemy0 >= 0
              and e.get("ach_enemy_no") == enemy0,
              f"ach_held {ach0!r}->{e.get('ach_held')!r} ach_enemy_no {enemy0!r}->{e.get('ach_enemy_no')!r}")
    left, lwhy = cb.leave(g, field)
    s = g.state
    led.check("S5-A9", left and isinstance(r0, int) and cb.dio(s).get("returns") == r0 + 1
              and cb.dio(s).get("last_return") == "warm" and _result(s) == 1,
              lwhy or f"returns {r0!r}->{cb.dio(s).get('returns')!r} last={cb.dio(s).get('last_return')!r} "
                      f"battle.result={_result(s)!r}")
    _endbench(g, "clear")
    after, awhy = _fp(g, field)
    _inv_check(led, "S5-A10", before, after, bwhy, awhy)


def _s5_b(g, led: cb.Ledger, field: int) -> None:
    g.note("S5-B: the negatives (event, defeat, escape), then a victory in the same boot")
    cids = ("S5-B1", "S5-B2", "S5-B3", "S5-B4")
    st, why = _fresh(g, field)
    if st is None:
        led.unreached(cids, why)
        return
    ok, why = _endbench(g, "event")
    samples = cb.hold_for(g, 2.0)
    bad = [(cb.raw(x).get("frame"), _phase(x), _end(x).get("injected"), _end(x).get("held")) for x in samples
           if _phase(x) != cb.PHASE_NORMAL or _end(x).get("injected") or _end(x).get("held")]
    led.check("S5-B1", ok and samples and not bad and _end(g.state).get("why") is None,
              why or f"violations {bad[:5]}; why={_end(g.state).get('why')!r}")
    at = cb.mark(g)
    ok, why = _endbench(g, "defeat")
    st = cb.poll(g, lambda x: _end(x).get("held") is True, 2.0, "the defeat to be HELD")
    s = st or g.state
    e = _end(s)
    lines = cb.new(g, at)
    led.check("S5-B2", ok and st is not None and e.get("injected") is False and e.get("action") == "hold"
              and _phase(s) == cb.PHASE_NORMAL and _shown(s) is False
              and any(HELD_LINE in ln and "HELD" in ln for ln in lines),
              why or f"end={ {k: e.get(k) for k in ('held', 'injected', 'action')} } phase={_phase(s)!r} "
                     f"hud.shown={_shown(s)!r}; {cb.grep(lines, 'diorama END')}")
    ok, why = _endbench(g, "escape")
    samples = cb.hold_for(g, 1.5)
    bad = [cb.raw(x).get("frame") for x in samples if not (_end(x).get("held") is True and _end(x).get("injected") is False
                                                           and _end(x).get("action") == "hold" and _phase(x) == cb.PHASE_NORMAL)]
    led.check("S5-B3", ok and samples and not bad, why or f"changed on frames {bad[:5]}")
    ok, why = _endbench(g, "victory")
    st = cb.poll(g, lambda x: _end(x).get("injected") is True and _phase(x) == cb.PHASE_VICTORY, 3.0,
                 "the victory to inject after the hold")
    e = _end(st or g.state)
    led.check("S5-B4", ok and st is not None and e.get("action") == "victory",
              why or f"injected={e.get('injected')!r} action={e.get('action')!r} phase={_phase(g.state)!r}")
    _out(g, field)


def _s5_c(g, led: cb.Ledger, field: int) -> None:
    for cid, args, result in (("S5-C1", ("nopose",), 2), ("S5-C2", ("other", "7"), 7), ("S5-C3", ("other", "5"), 5)):
        g.note(f"S5-C: `endbench {' '.join(args)}` -- the close fade")
        st, why = _fresh(g, field)
        if st is None:
            led.unreached((cid,), why)
            continue
        ok, why = _endbench(g, *args)
        st = cb.poll(g, lambda x: _end(x).get("injected") is True, 2.0, "the close injection")
        s = st or g.state
        e = _end(s)
        r = cb.poll(g, lambda x: _result(x) == result, 2.0, f"battle.result {result}")
        rising, detail = _r8_rising(g)
        extra = (e.get("inject_phase") == cb.PHASE_CLOSE and e.get("inject_seq") == 0) if cid == "S5-C1" else True
        led.check(cid, ok and st is not None and e.get("action") == "close" and extra and r is not None and rising,
                  why or f"end={ {k: e.get(k) for k in ('injected', 'action', 'inject_phase', 'inject_seq')} } "
                         f"battle.result={_result(g.state)!r} (want {result}); {detail}")
        _out(g, field)


def _s5_d(g, led: cb.Ledger, field: int, lever: bool) -> None:
    g.note("S5-D: W2 -- the per-unit-settle seq stalls MENU_OFF")
    if not lever:
        led.unreached(("S5-D1", "S5-D2"), "the `endbench guest` lever does not exist on this engine (S5-P1)")
        return
    st, why = _fresh(g, field)
    if st is None:
        led.unreached(("S5-D1", "S5-D2"), why)
        return
    at = cb.mark(g)
    ok, why = _endbench(g, "guest", "settle")
    ok2, why2 = _endbench(g, "victory") if ok else (False, why)
    st = cb.poll(g, lambda x: _end(x).get("injected") is True, 2.0, "the settle-seq injection")
    # MENU_OFF must hold until W2's 8 s are up: every publish before the first non-MENU_OFF one is MENU_OFF, and that
    # first one comes > 8000 ms after the injection (inject_ms is the engine's own clock)
    held, moved = cb.watch(g, lambda x: _phase(x) != cb.PHASE_MENU_OFF, 14.0)
    pre = held[:-1] if moved is not None else held
    flip_ms = _end(moved).get("inject_ms") if moved is not None else None
    last_ms = _end(held[-1]).get("inject_ms") if held else None
    led.check("S5-D1", ok2 and st is not None and _end(st).get("inject_seq") == 0 and pre
              and all(_phase(x) == cb.PHASE_MENU_OFF for x in pre)
              and ((isinstance(flip_ms, int) and flip_ms > 8000) or (moved is None and isinstance(last_ms, int)
                                                                      and last_ms > 8000)),
              (why or why2) or f"inject_seq={_end(st or g.state).get('inject_seq')!r}; MENU_OFF on {len(pre)} publish(es); "
                                f"left MENU_OFF at inject_ms={flip_ms!r} (last read {last_ms!r})")
    s2 = cb.poll(g, lambda x: "W2" in str(_end(x).get("watchdog") or ""), 5.0, "W2 to fire")
    s3 = cb.poll(g, lambda x: _phase(x) == cb.PHASE_VICTORY and _seq(x) == 2, 10.0, "the forced tail to reach the WAIT seq")
    rising, detail = _r8_rising(g)
    e = _end(g.state)
    lines = cb.new(g, at)
    led.check("S5-D2", s2 is not None and "unsettled unit(s)" in str(e.get("blocker") or "")
              and any(W2_LINE in ln and "blocked by: " in ln for ln in lines) and s3 is not None and rising,
              f"watchdog={e.get('watchdog')!r} blocker={e.get('blocker')!r} phase={_phase(g.state)!r} seq={_seq(g.state)!r}; "
              f"{detail}; {cb.grep(lines, 'watchdog W2')}")
    _endbench(g, "guest", "on")
    _out(g, field)


def _s5_e(g, led: cb.Ledger, field: int, lever: bool) -> None:
    g.note("S5-E: the stage-off red inside the stage DLL (`endbench guest off`)")
    if not lever:
        led.unreached(("S5-E1",), "the `endbench guest` lever does not exist on this engine (S5-P1)")
        return
    st, why = _fresh(g, field)
    if st is None:
        led.unreached(("S5-E1",), why)
        return
    at = cb.mark(g)
    ok, why = _endbench(g, "guest", "off")
    ok2, why2 = _endbench(g, "victory") if ok else (False, why)
    samples = cb.hold_for(g, 4.0)
    s = g.state
    e = _end(s)
    lines = cb.new(g, at)
    bad = [cb.raw(x).get("frame") for x in samples if _end(x).get("injected") or _phase(x) != cb.PHASE_NORMAL
           or _shown(x) is not True or _end(x).get("r8_hits") != 0]
    led.check("S5-E1", ok2 and samples and not bad and str(e.get("why") or "").startswith(LEVER_OFF_WHY)
              and cb.count(lines, "diorama END") == 0 and cb.count(lines, "diorama R8") == 0,
              (why or why2) or f"why={e.get('why')!r}; off-lever violations on {bad[:5]}; "
                                f"{cb.grep(lines, 'diorama END', 'diorama R8')}")
    _out(g, field)
    _endbench(g, "guest", "on")


def _selftest(g, led: cb.Ledger, cid: str, head: str) -> None:
    at = cb.mark(g)
    ok, why = _endbench(g, "selftest")
    lines = cb.wait_log(g, at, "harness: battle end-block selftest", 2.0)
    led.check(cid, ok and cb.count(lines, "harness: battle end-block selftest OK (" + head) == 1,
              why or cb.grep(lines, "end-block selftest"))


# ------------------------------------------------------------------------------------------- stage 6
def _hide(g, *pre) -> tuple:
    """Fabricate ``pre`` (e.g. "victory"), then ui 1 -> state 7. (ok, why)."""
    for args in (*pre, ("ui", "1"), ("state", "7")):
        ok, why = _endbench(g, *args)
        if not ok:
            return False, f"`endbench {' '.join(args)}`: {why}"
    return True, ""


def _s6_a(g, led: cb.Ledger, field: int) -> None:
    g.note("S6-A: victory, then the host hides its result screen -- the guest follows it out")
    cids = [c for c in CATALOG if c.startswith("S6-A")]
    before, bwhy = _fp(g, field)
    st, why = _fresh(g, field)
    if st is None:
        led.unreached(cids, why)
        return
    el = _el(st)
    led.check("S6-A1", el.get("trigger") is None and el.get("why") == NOT_LATCHED and _end(st).get("exit_mode") == "on",
              f"trigger={el.get('trigger')!r} why={el.get('why')!r} exit_mode={_end(st).get('exit_mode')!r}")
    r0 = cb.dio(st).get("returns")
    music0 = _end(st).get("music")
    ok, why = _endbench(g, "victory")
    inj = cb.poll(g, lambda x: _end(x).get("injected") is True, 2.0, "the injection")
    ok2, why2 = _endbench(g, "ui", "1")
    ok3, why3 = _endbench(g, "state", "6")
    samples = cb.hold_for(g, 1.0)
    latched = [cb.raw(x).get("frame") for x in samples if _el(x).get("trigger") is not None]
    led.check("S6-A2", ok and ok2 and ok3 and inj is not None and samples and not latched,
              (why or why2 or why3) or f"injected={inj is not None}; latched on {latched[:5]}")
    at = cb.mark(g)
    ok4, why4 = _endbench(g, "state", "7")
    s = cb.poll(g, lambda x: _el(x).get("requested") is True, 4.0, "the end-leave request") or g.state
    el = _el(s)
    rq = el.get("request_ms")
    budget = 100 + 1000 * int(el.get("deferred") or 0)
    led.check("S6-A3", ok4 and el.get("trigger") == "result-hide" and el.get("tries") == 1 and el.get("requested") is True
              and isinstance(rq, int) and 0 <= rq <= budget and el.get("why") is None and el.get("settled") is True
              and el.get("via") == "end-leave" and el.get("stamp") == 1 and el.get("stamp_host") == 1
              and el.get("music_shut") is True,
              why4 or f"end_leave={el}")
    ok_ret, rwhy = _arrive_after_exit(g, field, timeout=20.0)   # an engine without the end-leave is left by hand
    s = g.state
    lines = cb.new(g, at)
    needles = (("diorama END: the host left its battle (result-hide: the host's victory (", "BENCH end); presented here: "
                "victory) -- the guest follows it out"),
               ("diorama END: end-leave attempt 1, ", "ms after the host's result-hide -- Leave() follows"),
               ("diorama END: leaving a finished fight (end-leave; the host's victory, result 1, ui 1) -- the battle song "
                "shut down (ff9ShutdownStateBattleResult); the teardown stamps btl_result 1", "lifts the injected end fade"),
               ("diorama LEAVE requested -> FieldMap", ""),
               ("diorama END: return settled at the teardown -- ", "the injected end fade lifted (FF9Wipe_FadeInEx(256)"),
               ("diorama torn down", ""),
               (f"diorama RETURN (warm) -> field {field}", ""))
    idx = []
    for a, b in needles:
        idx.append(next((i for i, ln in enumerate(lines) if a in ln and b in ln), None))
    settled_line = next((ln for ln in lines if "diorama END: return settled at the teardown -- " in ln), "")
    in_order = None not in idx and all(x < y for x, y in zip(idx, idx[1:]))
    led.check("S6-A4", in_order and re.search(r"btl_result \d+ -> 1 \(the host's 1\)", settled_line) is not None,
              f"line indices {idx}; {cb.grep(lines, 'diorama END', 'diorama LEAVE', 'torn down', 'diorama RETURN', limit=900)}")
    el = _el(s)
    led.check("S6-A5", ok_ret and cb.dio(s).get("booted") is False and isinstance(r0, int)
              and cb.dio(s).get("returns") == r0 + 1 and cb.dio(s).get("last_return") == "warm" and _result(s) == 1
              and el.get("stamped") == 1 and el.get("wipe_lifted") is True and el.get("latched_ms") == -1,
              rwhy or f"booted={cb.dio(s).get('booted')!r} returns {r0!r}->{cb.dio(s).get('returns')!r} "
                      f"last={cb.dio(s).get('last_return')!r} battle.result={_result(s)!r} stamped={el.get('stamped')!r} "
                      f"wipe_lifted={el.get('wipe_lifted')!r} latched_ms={el.get('latched_ms')!r}; "
                      f"music {music0!r} -> {_end(s).get('music')!r}")
    if ok_ret:
        reads, detail = _return_frame(g, "s6-A-field-after-return")
        led.check("S6-A6", reads == "lit", f"{detail} -- want 'lit'; calibrated by S6-F3 (the un-lifted return)")
    else:
        # a frame of the diorama would prove nothing about the return's fade
        led.check("S6-A6", False, f"not reached: no end-leave return to photograph ({rwhy})")
    _endbench(g, "clear")
    after, awhy = _fp(g, field)
    _inv_check(led, "S6-A7", before, after, bwhy, awhy)


def _s6_b(g, led: cb.Ledger, field: int) -> None:
    g.note("S6-B: the stamp's own receipt (nopose -> 1; other 7 -> 7)")
    st, why = _fresh(g, field)
    if st is None:
        led.unreached(("S6-B1",), why)
    else:
        ok, why = _endbench(g, "nopose")
        r = cb.poll(g, lambda x: _end(x).get("action") == "close" and _result(x) == 2, 2.0, "the close with result 2")
        ok2, why2 = _hide(g) if ok else (False, why)
        ok3, why3 = _arrive_after_exit(g, field)
        s = g.state
        el = _el(s)
        led.check("S6-B1", ok and r is not None and ok2 and ok3 and _result(s) == 1 and el.get("stamped_was") == 2
                  and el.get("stamped") == 1 and el.get("stamp_host") == 2,
                  (why or why2 or why3) or f"diorama close seen: {r is not None}; field battle.result={_result(s)!r} "
                                           f"end_leave={ {k: el.get(k) for k in ('stamped_was', 'stamped', 'stamp_host')} }")
        _out(g, field)
    st, why = _fresh(g, field)
    if st is None:
        led.unreached(("S6-B2",), why)
        return
    ok, why = _hide(g, ("other", "7"))
    ok2, why2 = _arrive_after_exit(g, field)
    s = g.state
    led.check("S6-B2", ok and ok2 and _result(s) == 7, (why or why2) or f"field battle.result={_result(s)!r}")
    _out(g, field)


def _arrive_after_exit(g, field: int, timeout: float = 15.0) -> tuple:
    """The end-leave should take the guest out on its own; if it does not (an older engine), say so and leave by hand
    so the run can go on."""
    st = cb.poll(g, lambda s: not cb.dio(s).get("booted") and s.field_id == field and cb.free(s), timeout,
                 "the end-leave's return")
    if st is not None:
        cb.arrive(g, field)
        return True, ""
    cb.leave(g, field)
    return False, f"no end-leave within {timeout:.0f}s (left by hand)"


def _no_gameover(st):
    """The booted scene's own `btl_scene.Info.NoGameOver` (battle.scene_info.no_gameover): True / False / None (unread)."""
    v = (cb.battle(st).get("scene_info") or {}).get("no_gameover")
    return v if isinstance(v, bool) else None


def _held_defeat(g, field: int, *, want_stamp: int, want_field: int) -> tuple:
    """In a booted diorama: a held CLOSE + DEFEAT (`other 3`), then ui 1 + state 7, and the end-leave's return. (ok,
    detail) -- the stamp and the field's battle.result against the wants, no fade lifted (nothing was injected)."""
    ok, why = _endbench(g, "other", "3")
    held = cb.poll(g, lambda x: _end(x).get("held") is True, 2.0, "the defeat to be HELD") if ok else None
    inj = _end(held or g.state).get("injected")
    ok2, why2 = _hide(g) if ok else (False, why)
    ok3, why3 = _arrive_after_exit(g, field)
    s = g.state
    el = _el(s)
    good = (ok and held is not None and inj is False and ok2 and ok3 and el.get("stamp") == want_stamp
            and _result(s) == want_field and el.get("wipe_lifted") is False)
    return good, (f"{'; '.join(w for w in (why, why2, why3) if w)}{'; ' if (why or why2 or why3) else ''}"
                  f"held={held is not None} injected={inj!r}: stamp={el.get('stamp')!r} (want {want_stamp}) field "
                  f"battle.result={_result(s)!r} (want {want_field}) wipe_lifted={el.get('wipe_lifted')!r}")


def _s6_c(g, led: cb.Ledger, field: int) -> None:
    g.note("S6-C: a held CLOSE + DEFEAT carries 3 only into a NoGameOver scene")
    # C1, the positive: a scene whose header says NoGameOver (the booted scene's own flag is the judge)
    tried = []
    for scene in NOGO_SCENES:
        st, why = _fresh(g, field, scene)
        if st is None:
            tried.append(f"scene {scene}: {why}")
            continue
        nogo = _no_gameover(st)
        if nogo is not True:
            tried.append(f"scene {scene} booted but reads scene_info.no_gameover={nogo!r}")
            _out(g, field)
            continue
        ok, detail = _held_defeat(g, field, want_stamp=3, want_field=3)
        led.check("S6-C1", ok, f"scene {scene} (NoGameOver): {detail}"
                               + (f"; skipped first: {'; '.join(tried)}" if tried else ""))
        _out(g, field)
        break
    else:
        led.unreached(("S6-C1",), "no NoGameOver scene booted as one -- " + "; ".join(tried))
    # C2, the negative: scene 67, a Game Over scene -- the DEFEAT is a Game Over in transit (btl_sys rewrites it)
    st, why = _fresh(g, field)
    if st is None:
        led.unreached(("S6-C2",), why)
        return
    nogo = _no_gameover(st)
    if nogo is not False:
        led.check("S6-C2", False, f"not reached: scene {cb.SCENE} reads scene_info.no_gameover={nogo!r}, so it cannot be "
                                  f"the Game Over negative")
        _out(g, field)
        return
    ok, detail = _held_defeat(g, field, want_stamp=-1, want_field=0)
    led.check("S6-C2", ok, f"scene {cb.SCENE} (a Game Over scene): {detail}")
    _out(g, field)


def _s6_d(g, led: cb.Ledger, field: int) -> None:
    for cid, ui, trigger in (("S6-D1", "2", "game-over"), ("S6-D2", "3", "title")):
        g.note(f"S6-D: other 6 + ui {ui} -- the host's {trigger}")
        st, why = _fresh(g, field)
        if st is None:
            led.unreached((cid,), why)
            continue
        titles = []
        ok, why = _endbench(g, "other", "6")
        ok2, why2 = _endbench(g, "ui", ui) if ok else (False, why)
        samples, back = cb.watch(g, lambda s: not cb.dio(s).get("booted") and s.field_id == field and cb.free(s), 15.0,
                                 on_sample=lambda s: titles.append(s.frame) if s.ui_state == "Title" else None)
        if back is None:
            cb.leave(g, field)
        else:
            cb.arrive(g, field)
        s = g.state
        el = _el(s)
        extra = (el.get("settled") is True and el.get("stamp") == -1 and _result(s) == 0) if cid == "S6-D1" else True
        led.check(cid, ok and ok2 and back is not None and el.get("trigger") == trigger and not titles
                  and cb.dio(s).get("last_return_field") == field and extra,
                  (why or why2) or f"returned: {back is not None}; trigger={el.get('trigger')!r} settled={el.get('settled')!r} "
                                   f"stamp={el.get('stamp')!r} field battle.result={_result(s)!r} (want 0: the diorama's "
                                   f"InitBattle value) last_return_field={cb.dio(s).get('last_return_field')!r} "
                                   f"Title frames {titles[:3]}")
        _out(g, field)


def _s6_m(g, led: cb.Ledger, field: int) -> None:
    g.note("S6-M: a mid-fight dioleave settles nothing")
    st, why = _fresh(g, field)
    if st is None:
        led.unreached(("S6-M1",), why)
        return
    left, lwhy = cb.leave(g, field)
    el = _el(g.state)
    led.check("S6-M1", left and el.get("settled") is False and el.get("trigger") is None and el.get("stamp") == -1,
              lwhy or f"end_leave={ {k: el.get(k) for k in ('settled', 'trigger', 'stamp', 'via')} }")
    _endbench(g, "clear")


def _s6_e(g, led: cb.Ledger, field: int) -> None:
    g.note("S6-E: a LATE boot -- the host already hid its result screen")
    _endbench(g, "clear")
    ok, why = _hide(g, ("victory",))
    r0 = cb.dio(g.state).get("returns")
    at = cb.mark(g)
    okb, whyb = cb.try_ns(g, "dioboot", cb.SCENE, cb.PATTERN) if ok else (False, why)
    back = cb.poll(g, lambda s: isinstance(r0, int) and (cb.dio(s).get("returns") or 0) > r0 and s.field_id == field
                   and cb.free(s), 60.0, "the late boot's end-leave return") if okb else None
    if back is None and cb.dio(g.state).get("booted"):
        cb.leave(g, field)
    s = g.state
    e, el = _end(s), _el(s)
    lines = cb.new(g, at)
    deferred = el.get("deferred")
    led.check("S6-E1", okb and back is not None and e.get("injected") is False
              and str(e.get("why") or "").startswith(LATE_WHY) and el.get("requested") is True
              and cb.dio(s).get("last_return") == "warm",
              (whyb or why) or f"injected={e.get('injected')!r} why={e.get('why')!r} requested={el.get('requested')!r} "
                               f"last_return={cb.dio(s).get('last_return')!r}; deferred={deferred!r} "
                               f"(deferral lines: {cb.count(lines, 'end-leave deferred')})")
    _endbench(g, "clear")


def _s6_f(g, led: cb.Ledger, field: int, lever: bool) -> None:
    g.note("S6-F: the stage DLL's own red (`endbench exit off`)")
    if not lever:
        led.unreached(("S6-F1", "S6-F2", "S6-F3"), "the `endbench exit` lever does not exist on this engine (S6-P1)")
        return
    st, why = _fresh(g, field)
    if st is None:
        led.unreached(("S6-F1", "S6-F2", "S6-F3"), why)
        return
    ok, why = _endbench(g, "exit", "off")
    ok2, why2 = _hide(g, ("nopose",)) if ok else (False, why)
    held = cb.hold_for(g, 5.0)
    booted = all(cb.dio(x).get("booted") for x in held)
    rising, detail = _r8_rising(g)
    s = g.state
    el = _el(s)
    led.check("S6-F1", ok2 and held and booted and _end(s).get("exit_mode") == "off" and el.get("trigger") == "result-hide"
              and el.get("requested") is False and el.get("tries") == 0
              and EXIT_LEVER_WHY in str(el.get("why") or "") and rising,
              (why or why2) or f"booted throughout: {booted}; end_leave={el}; {detail}")
    left, lwhy = cb.leave(g, field)
    s = g.state
    el = _el(s)
    led.check("S6-F2", left and el.get("settled") is False and el.get("music_shut") is False
              and el.get("wipe_lifted") is False and _result(s) == 2,
              lwhy or f"end_leave={ {k: el.get(k) for k in ('settled', 'music_shut', 'wipe_lifted', 'music_why')} } "
                      f"field battle.result={_result(s)!r}")
    _endbench(g, "clear")
    # F3: the same frame reading as A6, on a return nothing lifted -- the detector must be able to say BLACK. It needs
    # its own boot with a FULL victory: only that injects stage 5's end fade (the no-pose end above presents "close"
    # and fades nothing, so its return was never black -- the first draft photographed it and read it lit).
    st, why = _fresh(g, field)
    if st is None:
        led.check("S6-F3", False, f"not reached: no fresh boot for the un-lifted victory return ({why})")
        _endbench(g, "exit", "on")
        return
    ok, why = _endbench(g, "exit", "off")
    ok2, why2 = _hide(g, ("victory",)) if ok else (False, why)
    cb.hold_for(g, 3.0)
    left, lwhy = cb.leave(g, field) if ok2 else (False, why2)
    el = _el(g.state)
    if left and el.get("wipe_lifted") is False:
        # MEASURED 2026-10-13 (probe_return_fade): an un-lifted victory return is NOT black on this bench -- the field
        # load resets the Sub fade itself (lifted vs un-lifted: mean luma 4.1 vs 6.4 at 0.3 s, identical from 1 s). So
        # the lift is stock parity, not load-bearing, and this leg cannot photograph a black return. What A6 needs is a
        # detector that CAN say black: calibrate it on a synthetic all-black frame of the same size, and read the
        # un-lifted return as what it is (lit).
        reads, detail = _return_frame(g, "s6-F-field-unlifted")
        black = _synthetic_black_reads()
        led.check("S6-F3", black == "black" and reads == "lit",
                  f"synthetic black frame reads {black!r} (want 'black'); un-lifted return: {detail} -- want 'lit' "
                  f"(the field load resets the fade; the lift is parity, not load-bearing)")
    else:
        led.check("S6-F3", False, f"not reached: no un-lifted return to photograph (left={left}, "
                                  f"wipe_lifted={el.get('wipe_lifted')!r}{'; ' + lwhy if lwhy else ''})")
    _endbench(g, "exit", "on")
    _endbench(g, "clear")


def _release(g, led: cb.Ledger) -> None:
    """Leave both levers pulled ON PURPOSE, then `reset`: the release must restore them and say so."""
    ok1, why1 = _endbench(g, "guest", "settle")
    ok2, why2 = _endbench(g, "exit", "off")
    at = cb.mark(g)
    cb.release(g)
    st = g.state
    lines = cb.new(g, at)
    e = _end(st)
    led.check("S56-R", ok1 and ok2 and cb.count(lines, "end presentation guest back ON (released with the harness)") == 1
              and cb.count(lines, "end exit guest back ON (released with the harness)") == 1
              and e.get("guest_mode") == "on" and e.get("exit_mode") == "on" and (st.netsync or {}).get("forced") is False,
              (why1 or why2) or f"guest_mode={e.get('guest_mode')!r} exit_mode={e.get('exit_mode')!r}; "
                                f"{cb.grep(lines, 'released with the harness')}")
