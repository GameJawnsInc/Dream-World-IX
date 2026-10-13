"""B4/B5 STAGES 9 + 10 -- THE HOST RESULT MANIFEST (memoria-patch s108) AND THE GUEST'S WRITE-NOTHING RESULT-SCREEN
REPLAY (s109), the solo bench, run unattended.

THE GAP (studies/battle-coop/B4-B5-DESIGN.md 3.5, 5.5-5.7, section 7 stages 9-10). After stages 5-6 a victorious guest
held black through the host's whole reward screen until the host's Hide; its own stock screen would have computed
rewards from its stand-in party and WRITTEN them into the guest's save.
  s108 (stage 9): at the tail of BattleResultUI.InitialNormal the HOST captures what its stock screen is about to pay
    -- per RAW party slot charId, needExp/needAp/draw, levelBefore/After, expBefore/Gain, apGain, status and the AP learn
    schedule; defaultExp/Ap, gilGain/Before, <= 6 items, the card -- and ships it in the end block (flags b1) until the
    battle ends; the guest decodes and stores it per battle nonce. Lever: `endbench manifest host off`.
  s109 (stage 10): inside a booted diorama the guest's stock result screen opens on that manifest as a WRITE-NOTHING
    replay: the host's values, stepping only when the host's result state steps (the chase), the guest's own Confirm
    inert, its Quit prompt never answered, and a WRITE GUARD (`replay.fp`, re-taken at every step) that logs ERROR "WRITE
    DETECTED" on any change. Levers: `endbench replay on|off|local`; ops `endbench quit on|off`, `endbench fieldsong 0|1`.

THE BENCH. `netsync selftest 1` (saves sandboxed), the party seeded through COOPPARTY (30604), field 30602.
  PART 9 (S9-*): the codec through the REAL ParseView on the field (`endbench manifest 0|1|2|3|4`, the two-marker preset
  against the sandbox autosave's party/bag/cards), then a REAL own battle (`battle 67`, through the selftest loopback)
  whose host capture is compared with the peer's decode and with the live result screen (`battle.result_ui`) at states
  0, 2 and 3 -- ONE short Confirm at state 0 (the screen waits there; held < 500 ms so BattleAutoConfirm never repeats
  it), then NOTHING until state 2 (the natural tick path, the only one on which `host.learned` must equal the schedule);
  then the lever's battle. S9-C4L records whether that learn equality was EXERCISED: `battle 67` with the COOPPARTY
  party may teach nothing (schedule [] == learned [] holds vacuously), and then C4L is RED "not reached" by design --
  equip an ability whose remaining AP is at most the fight's AP to make it a teaching fight.
  PART 10 (S10-*): `dioboot 67 0` with the guest's REAL party seated; `endbench manifest 1` + `victory` + `ui 1` opens
  the replay; every page is stepped ONLY by `endbench state <n> [loading]` (the bench host's state) and photographed:
      s10-1-start.png  s10-2-levelup.png  s10-3-gil-items.png  s10-4-item-full.png  s10-5-end.png  -- READ them.
  The write guard's live fingerprint (`netsync.battle.end.replay.fp`) is read on the field (FP0), after the boot (FP1)
  and at EVERY page; the sandbox autosave fingerprint is compared setup -> end (S10-INV). Then the quit guard (R2 --
  NEVER a Confirm while the guest's own quit prompt is up: its Yes quits the game), the refusal (R3), the abort (R4),
  the negatives (R5), the fixer's field-song leg (R6) and the stage's two levers (L1 `replay off`, L2 `replay local`).
`COOP_REPLAY_PART=9` or `=10` runs one part only (the catalog shrinks to it); the default runs both. `COOP_REPLAY_OVERFLOW=1`
adds S9-D (a 99-drop overflow; needs a sandbox save that already holds 99 of the fight's drop -- else two-machine box 27).

NOT PROVEN HERE (two-machine sitting 2, boxes 24-33): a non-identity charId/slot mapping, the relay lane carrying the
manifest, mouse routing on the real screen, the screen composing over the host-driven diorama, the watcher's S10-B2
deferral (a `dioboot` has no wire nonce, so the watcher returns early).

CALIBRATION -- a check that cannot fail is not a check.
  * THE DEPLOYED DLL AT WRITING (s105): neither probe key exists. Part 9: P0 RED; `endbench manifest 1` FAILS ("the
    result manifest is stage 9 -- this engine ships the end block only"), so every B check is RED "not reached"; the
    real battle still runs and C1-C8 (and C4L) go RED on the absent keys (peer.end.flags & 2 == 0, manifest_len 0, rows 0, no
    "battle result manifest" line, no result_ui labels); E RED (no lever). Part 10: P0 RED; R0 RED (the SelfTest detail
    ends at "exit 280"); the walk still runs where it can -- every replay/fp check RED (`replay` absent), the stage-6
    end-leave at `state 7` then runs with music_shut/wipe_lifted true; R2-R6, L1, L2 RED ("unknown op" for quit /
    replay / fieldsong). GREEN there: S0, S9-PRE, S10-W3 (no "WRITE DETECTED": a DLL that opens no screen cannot write)
    and S10-INV (the autosave fingerprint is unchanged). On the s100-s105 stand-in: S0 and S10-W3 green (the stand-in
    writes no autosave and its default battle skips the result screen, so PRE/INV/C read red there too).
    On the full s106-s110 stand-in (a green-path smoke, not an oracle): part 10 alone 17/29 -- every red is the stand-in's
    own gap (no [NetSync] log lines: R0 R1a R1b R1d R1h R1k R2 R3 R4 R6 and S910-R read theirs; no autosave: INV); the
    walk, the fingerprints, the quit guard's behaviour, the refusal, the abort, the negatives, R6's song and both levers
    all read as designed. Part 9's B needs the autosave and C/E a result screen the default stand-in never shows.
  * THE PREVIOUS DLL (s108 for part 10): `replay.fp` and `replay` absent -> the probe fails closed; R1 red from step 5 on
    (battle.result_ui stays null, no REPLAY lines, r8_hits rising through the black hold; at `state 7` the stage-6 end-
    leave runs with music_shut and wipe_lifted true); the write-nothing assertions W3/INV green.
  * IN-RUN, on the stage DLLs (judged as their own checks): S9-E (`manifest host off`: the capture still records,
    nothing ships); S10-L1 (`replay off`: verdict 1, no screen); S10-L2 (`replay local`: the guest's own Confirm steps
    the replay -- local_steps > 0, steps 0 -- while writes stay 0 and the fingerprint holds).
  The write guard's sensitivity is pinned offline (SelfTest's replay section: the FpMix pins + the mutants).

DRIVER NOTE. A Session.netsync whose endbench op table predates s109's `replay` / `quit` / `fieldsong` refuses them
before sending: _coop_battle.ns_verb then sends them as raw steps, so the ENGINE's answer decides. A driver that knows
them refuses them first on an engine without `netsync.battle.end.replay` ("publishes no ..."): the probe's red, never a
pass.

    py tools/play.py studies/test-harness/scenarios/coop_battle_result_replay.py --field 30602
"""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file

HarnessError = cb.HarnessError

_PART = os.environ.get("COOP_REPLAY_PART", "").strip()
PART9 = _PART in ("", "9", "all", "both")
PART10 = _PART in ("", "10", "all", "both")
OVERFLOW_LEG = os.environ.get("COOP_REPLAY_OVERFLOW", "").strip() not in ("", "0")

FIGHT_S = 300.0
POISON, BLIND = 0x10000, 0x10            # BattleStatus.Poison (1 << 16), BattleStatus.Blind (1 << 4)
GIL_MARK, GIL_ALT, GIL_GAIN, ESC_GIL = 1234567, 1234566, 4321, 321
SELFTEST10 = ("battle end-block selftest OK (classify 23, chase 162 + pins, codec 46, present 48, exit 280, manifest 708, "
              "replay ")
REPLAY_PINS = 86                         # SelfTest's replay section after the stage-10 fixer (memoria-patches/README.md s109)
FAB_MANIFEST = "; manifest (preset 1, "
CAPTURED = "battle result manifest (host): captured rows "
RIDES = "; rides the end block (flags b1) until the battle ends"
PEER_HELD = "battle result manifest (peer, nonce "
PEER_STORED = "stored for the result-screen replay (rx="
HOST_OFF = "CALIBRATION: `endbench manifest host off` ships nothing"
OVERFLOW_HOST = "battle result (host): item overflow -- the sticky end-block flag b2 rides every frame until the battle ends"
WAIT5 = "diorama replay-wait: the result-screen replay waits -- the host is not on its result screen"
ARMED = "diorama REPLAY ARMED"
OPENED = "result replay: OPENED the stock result screen write-nothing"
INERT = "result replay: the guest's own Confirm is inert"
OVERFLOWED = "result replay: items -- the host OVERFLOWED"
WAITS = "end-leave waits up to 5000 ms"
CLOSED_OWN = "result replay: CLOSED (its own hide tail"
WAIT_ENDED = "the end-leave's wait for the replay ended after "
WAIT_OWN = "the replay closed through its own hide tail"
MUSIC_REPLAY = "the replay's own hide tail already shut the songs"
QUIT_ON = "harness: endbench quit ON"
REFUSED = "diorama REPLAY REFUSED"
ABORTED_DIO = "diorama REPLAY aborted"
ABORTED_SCREEN = "result replay: ABORTED"
SONG_KEPT = "the song KEPT"
HOST_KEEPS = "the host keeps its field song"
WRITE = "WRITE DETECTED"
REL_MANIFEST = "result manifest host back ON (released with the harness)"
REL_REPLAY = "result-screen replay guest back ON (released with the harness)"
V_GO, V_LEVER, V_HOST_NOT_ON, V_AFTER_EVENT, V_NO_MANIFEST, V_NO_ROW = 0, 1, 5, 7, 8, 10
FOLLOW_QUIT, FOLLOW_IN_STEP = 3, 6


def _catalog() -> dict:
    c = {"S910-S0": "the harness forced the selftest role for this process (Memoria.ini untouched)"}
    if PART9:
        c.update({
            "S9-P0": "the engine publishes `netsync.battle.host.manifest_captures` (memoria-patch s108, stage 9)",
            "S9-PRE": "the two-marker baselines are readable from the sandbox autosave (gil, the bag, the cards, each seated "
                      "member's level/exp)",
            "S9-B1": "B: `endbench manifest 1` + `ui 1` + `state 0` through the real ParseView -- peer.end bench true, flags & 2, "
                     "manifest_len > 0, manifest_why null, rows == the seated count; the fabricate line names '; manifest "
                     "(preset 1, N B)'",
            "S9-B2": "B: the totals are the TWO markers -- gil_before 1234567 (1234566 if the party holds exactly that), "
                     "gil_gain 4321, items == [{X, 7}] with X held 0 in the bag, the card held 0 in the collection; "
                     "bench_manifest 1, bench_manifest_note null",
            "S9-B3": "B: the rows -- each row's char == its seated member, lv_before/exp_before the member's, ap_gain 5; the "
                     "first seated row lv_after == lv_before + 2, its status gains Poison (else Blind), ONE learn at ap_at 3",
            "S9-B4": "B: `manifest 3` -- every row's char matches NO seated member",
            "S9-B5": "B: `manifest 2` -- flags & 8 (escape gil), every exp_gain and ap_gain 0, gil_gain 321, items [], card 255",
            "S9-B6": "B: `manifest 0` -- manifest null, flags & 2 == 0, manifest_len 0, rows 0",
            "S9-B7": "B: `manifest 4` FAILS the verb ('needs 0 (none), 1 ...')",
            "S9-B8": "B: `endbench clear` -> peer.end null, and the baselines unchanged (the bench writes nothing)",
            "S9-C1": "C (a real own battle through the loopback), at result state 0: manifest_captures +1, manifest_why null, "
                     "manifest_bytes > 0, host.end.flags & 2, host.end.manifest_len == manifest_bytes",
            "S9-C2": "C: peer.end.bench false and peer.end.manifest deep-equal to host.manifest (host-only truncated/"
                     "learn_capped aside), peer.end.rows == its rows, peer.manifest_nonce == peer.nonce, manifest_rx +1",
            "S9-C3": "C: the manifest == the live screen at state 0 -- the exp/ap labels, every row's level/exp/dim/need flags/"
                     "exp_value/ap_value, the model's default exp/ap, gil_value, party_gil, card and items",
            "S9-C4": "C: ONE short Confirm at state 0 -> state 1 at once; at the natural state 2 each row reads level lv_after "
                     "with level_ups lv_after - lv_before, and host.learned == the rows' learn schedule (no unscheduled learn)",
            "S9-C4L": "C: the learn half is EXERCISED -- the fight teaches (the manifest's learn schedule is non-empty) and "
                      "host.learned on the natural tick path == that schedule, ap_at for ap_at; a fight that teaches nothing "
                      "records this RED 'not reached' (equip an ability whose remaining AP <= the fight's AP)",
            "S9-C5": "C: Confirm to state 3 -- the gil-received label carries gil_gain, gil-current gil_before, the items shown "
                     "with their counts, the card shown when card != 255",
            "S9-C6": "C: plausibility (no reward support abilities) -- gil_gain == battle.bonus.gil and default_exp == "
                     "bonus.exp // the rows needing exp",
            "S9-C7": "C: the logs -- 'battle result manifest (host): captured rows ... ; rides the end block (flags b1) until "
                     "the battle ends' and 'battle result manifest (peer, nonce n): held rows ... stored for the result-screen "
                     "replay (rx=...)'",
            "S9-C8": "C: after the field load host.manifest_bytes 0, host.manifest still readable, peer.live false",
            "S9-E1": "E (`endbench manifest host off` = the pre-stage host) at state 0: manifest_mode 'off', host.manifest "
                     "populated (the instrument), host.end.flags & 2 == 0 and manifest_len 0, peer.end.manifest null and rows "
                     "0, manifest_rx unchanged, the capture line carries 'CALIBRATION: `endbench manifest host off` ships "
                     "nothing'",
            "S9-E2": "E: `endbench manifest host on` -> manifest_mode 'on'",
        })
        if OVERFLOW_LEG:
            c["S9-D1"] = ("D (a 99-drop save): host.overflow, host.end.flags & 4 and peer.end.flags & 4 within one sample, the "
                          "'item overflow -- the sticky end-block flag b2 ...' line, result_ui.state 4")
    if PART10:
        c.update({
            "S10-P0": "the engine publishes `netsync.battle.end.replay` (memoria-patch s109, stage 10)",
            "S10-R0": f"`endbench selftest` -> 'battle end-block selftest OK (... exit 280, manifest 708, replay "
                      f"{REPLAY_PINS})'",
            "S10-W0": "FP1 (the write guard's live fingerprint after `dioboot`) == FP0 (on the field), component by component",
            "S10-R1a": "R1: `manifest 1` + `victory` -> injected and R8 within 12 s; replay.armed false, verdict 5 (the host "
                       "not on its result screen), the replay-wait line",
            "S10-R1b": "R1: `ui 1` -> within 2 s armed + opened, verdict 0, host_state_at_arm 0, row_mask == seated_mask, "
                       "manifest_rows == M's rows; battle.result_ui.replay true at state 0; 'diorama REPLAY ARMED' then "
                       "'result replay: OPENED ... (fingerprint 0x'",
            "S10-R1c": "R1: page 1 shows the HOST's numbers -- the exp/ap labels == M's defaults, every manifest row shown with "
                       "level == lv_before, exp == exp_before, dim == !draw (PNG s10-1-start)",
            "S10-R1d": "R1: the guest's own Confirm is INERT -- 3 short presses + a 2 s hold: screen.state 0, steps 0, "
                       "local_confirms >= 3, the inert line exactly once",
            "S10-R1e": "R1: `state 1` -> steps 1, trail ['0>1'], state 1; the first row reaches lv_after with level_ups 2; "
                       "screen.learned == [{slot, M's learn, ap 3}] (PNG s10-2-levelup)",
            "S10-R1f": "R1: `state 2` (no loading) -> the local ticks end naturally at state 2: steps still 1, follow 6",
            "S10-R1g": "R1: `state 2 loading` -> steps 2, trail[1] '2>2L', state 3 after the fade; page 2 shows gil received "
                       "4321, current 1234567, the items [{marker, 7}] shown, the card shown; screen.gil == gil_before while "
                       "result_ui.model.party_gil == FP0.gil (PNG s10-3-gil-items)",
            "S10-R1h": "R1: `overflow 1` + `state 4` -> steps 3, overflow_shown, state 4, 'items -- the host OVERFLOWED' "
                       "(PNG s10-4-item-full)",
            "S10-R1i": "R1: `state 5` -> state 5 and the shadow gil rises",
            "S10-R1j": "R1: `state 6` -> state 6 and screen.gil == gil_before + gil_gain (1238888) (PNG s10-5-end)",
            "S10-R1k": "R1: `state 7` -> trigger 'result-hide', the trail ends '6>7', replay.closed, exit_waited with "
                       "exit_wait_ms < 5000, aborted false; the wait / CLOSED / wait-ended lines in order; music_why 'the "
                       "replay's own hide tail already shut the songs...', wipe_lifted false",
            "S10-R1l": "R1: a warm return -- netsync.diorama.returns +1 and battle.result 1 on the field",
            "S10-W1": "WRITE NOTHING (in the diorama, where the teardown's Restore cannot mask it): at every page read from the "
                      "open to state 6, replay.fp.hash == FP1.hash and screen.writes == 0",
            "S10-W2": "WRITE NOTHING: after the return replay.fp == FP0, component by component",
            "S10-R2": "R2 (quit guard): with the guest's own quit prompt up (`endbench quit on`), `state 1` does not step for "
                      ">= 2 s (state 0, steps 0, follow 3); Cancel closes it and the step lands within 1 s; `state 7` leaves",
            "S10-R3": "R3 (refusal): `manifest 3` (foreign charIds) -> replay.refused, verdict 10, opened false, "
                      "battle.result_ui null, 'diorama REPLAY REFUSED'; `state 7` leaves cleanly with fp == FP0",
            "S10-R4": "R4 (abort): a `dioleave` mid-tick -> replay.aborted with abort_why 'a leave of the diorama', "
                      "screen.aborted, 'diorama REPLAY aborted' + 'result replay: ABORTED ... tick loops 105/109 stopped'; "
                      "music_shut and wipe_lifted true; fp == FP0 after the return",
            "S10-R5a": "R5: `afterevent 1` -> verdict 7 and nothing arms (armed false, no screen, for 2 s after `ui 1`)",
            "S10-R5b": "R5: `manifest 0` -> verdict 8, a black hold (no screen for 2 s), then `state 7` runs the stage-6 exit "
                       "unchanged (result-hide, music_shut and wipe_lifted true)",
            "S10-R6": "R6 (fixer S10-R1): `fieldsong 1` before `state 7` -> the CLOSED line says 'the song KEPT', music_why "
                      "'the host keeps its field song ...', music_shut false, wipe_lifted false",
            "S10-L1": "L1 (lever `replay off` = the pre-stage guest): after `ui 1` armed false, verdict 1, no result screen "
                      "for 2 s",
            "S10-L2": "L2 (lever `replay local`): the guest's own Confirm STEPS the replay -- local_steps > 0, steps 0 -- while "
                      "writes stay 0 and replay.fp.hash == FP1.hash",
            "S10-W3": "WRITE NOTHING: Memoria.log carries no 'WRITE DETECTED' line for the whole run",
            "S10-INV": "the guest's save/party/bag fingerprint (sandbox autosave) is byte-identical, part 10's start to end",
        })
    c["S910-R"] = ("`reset` with the levers left pulled: " + " and ".join(
        ([f"'{REL_MANIFEST}'"] if PART9 else []) + ([f"'{REL_REPLAY}'"] if PART10 else [])) + " logged")
    return c


# ------------------------------------------------------------------------------------------- reads
def _peer_end(x) -> dict | None:
    e = cb.peer(x).get("end")
    return e if isinstance(e, dict) else None


def _host_end(x) -> dict | None:
    e = cb.host(x).get("end")
    return e if isinstance(e, dict) else None


def _man(e) -> dict | None:
    m = (e or {}).get("manifest")
    return m if isinstance(m, dict) else None


def _rep(x) -> dict:
    r = cb.bend(x).get("replay")
    return r if isinstance(r, dict) else {}


def _scr(x) -> dict:
    s = _rep(x).get("screen")
    return s if isinstance(s, dict) else {}


def _fp(x) -> dict | None:
    f = _rep(x).get("fp")
    return f if isinstance(f, dict) else None


def _ru(x) -> dict | None:
    r = cb.battle(x).get("result_ui")
    return r if isinstance(r, dict) else None


def _el(x) -> dict:
    v = cb.bend(x).get("end_leave")
    return v if isinstance(v, dict) else {}


def _status(row) -> int:
    try:
        return int(str(row.get("status")), 16)
    except (TypeError, ValueError):
        return -1


def _strip_host_only(m: dict | None) -> dict | None:
    if m is None:
        return None
    return {k: v for k, v in m.items() if k not in ("truncated", "learn_capped")}


def _eb(g, *args) -> tuple:
    return cb.try_ns(g, "endbench", *args)


def _tree_facts(tree) -> dict:
    """From the decoded autosave: gil, {item id: count}, the card ids, and per seated RAW slot (char, level, exp)."""
    c = (tree or {}).get("40000_Common") or {}
    mg = (tree or {}).get("30000_MiniGame") or {}
    bag = {}
    for i in c.get("items") or []:
        if isinstance(i, dict) and isinstance(i.get("id"), int):
            bag[i["id"]] = bag.get(i["id"], 0) + int(i.get("count") or 0)
    cards = sorted({int(e.get("id")) for e in mg.get("MiniGameCard") or [] if isinstance(e, dict)
                    and isinstance(e.get("id"), int) and e.get("id") != 255})
    players = {}
    for p in c.get("players") or []:
        info = p.get("info") or {}
        if isinstance(info.get("slot_no"), int):
            players[info["slot_no"]] = (p.get("level"), p.get("exp"))
    seats = {}
    for i, ch in enumerate(cb.seated_party(tree)):
        if ch is not None:
            seats[i] = (ch,) + tuple(players.get(ch, (None, None)))
    return {"gil": c.get("gil"), "bag": bag, "cards": cards, "seats": seats}


# ------------------------------------------------------------------------------------------- the run
def run(g, field: int = cb.FIELD):
    led = cb.Ledger(g, _catalog(), finals=("S10-W3", "S10-INV", "S910-R"))
    ctx = {"fp_inv": None, "fp_inv_why": "", "at0": 0}
    try:
        _run(g, led, field, ctx)
    finally:
        g.note(f"Memoria.log archived: {cb.archive_log(g, 'result-replay')}")
        led.close()
        try:
            if cb.dio(g.state).get("booted"):
                cb.leave(g, field)
            if PART10:
                lines = cb.new(g, ctx["at0"])
                led.check("S10-W3", cb.count(lines, WRITE) == 0, cb.grep(lines, WRITE) or f"{len(lines)} line(s), none")
                if ctx["fp_inv"] is not None:
                    fpn, why = cb.fingerprint(g, field=field)
                    diff = cb.fp_diff(ctx["fp_inv"], fpn) if fpn is not None else ["unreadable"]
                    led.check("S10-INV", fpn is not None and not diff, why or (f"changed: {diff}" if diff else
                                                                              f"identical (gil {fpn.get('gil')})"))
                else:
                    led.check("S10-INV", False, f"not reached: no part-10 baseline ({ctx['fp_inv_why']})")
        except HarnessError as err:
            g.note(f"the final reads failed: {str(err)[:160]}")
        _release(g, led)
        led.close(final=True)


def _run(g, led: cb.Ledger, field: int, ctx: dict) -> None:
    ok, why = cb.setup(g, field, label="B4/B5 stages 9-10: the host result manifest (s108) + the guest's result-screen "
                                       "replay (s109), solo")
    led.check("S910-S0", ok, why)
    ctx["at0"] = cb.mark(g)
    g.note(f"probe stage: {cb.stage_of(g.state)}")
    if PART9:
        _part9(g, led, field)
    if PART10:
        _part10(g, led, field, ctx)


# =========================================================================================== PART 9
def _part9(g, led: cb.Ledger, field: int) -> None:
    st = g.state
    led.check("S9-P0", cb.has(st, cb.PROBES[9]),
              f"netsync.battle.host keys: {sorted(cb.host(st))}" if cb.has(st, "netsync.battle") else "no `netsync.battle`")
    tree, twhy = cb.extra_tree(g, field=field)
    facts = _tree_facts(tree) if tree is not None else None
    led.check("S9-PRE", facts is not None and facts["seats"] and isinstance(facts["gil"], int),
              twhy or f"gil {facts['gil']}, seats {facts['seats']}, {len(facts['bag'])} bag ids, {len(facts['cards'])} cards")
    _leg_b(g, led, field, facts)
    _leg_c(g, led)
    if OVERFLOW_LEG:
        _leg_d(g, led)
    _leg_e(g, led)


def _leg_b(g, led: cb.Ledger, field: int, facts: dict | None) -> None:
    g.note("S9-B: the manifest codec through the real ParseView (the bench seam)")
    cids = [c for c in led.catalog if c.startswith("S9-B")]
    if facts is None:
        led.unreached(cids, "no autosave baseline to hold the two markers against (S9-PRE)")
        return
    _eb(g, "clear")
    at = cb.mark(g)
    ok, why = _eb(g, "manifest", 1)
    if not ok:
        led.unreached(cids, f"`endbench manifest 1` refused -- {why}")
        return
    ok2, why2 = _eb(g, "ui", 1)
    ok3, why3 = _eb(g, "state", 0)
    st = g.state
    e = _peer_end(st) or {}
    m = _man(e) or {}
    rows = m.get("rows") or []
    seats = facts["seats"]
    lines = cb.wait_log(g, at, FAB_MANIFEST, 2.0)
    led.check("S9-B1", ok2 and ok3 and e.get("bench") is True and cb.mask_bits(e.get("flags")) & 2
              and (e.get("manifest_len") or 0) > 0 and e.get("manifest_why") is None and e.get("rows") == len(seats)
              and len(rows) == len(seats)
              and any("harness: endbench state -- fabricated" in ln and FAB_MANIFEST in ln for ln in lines),
              (why2 or why3) or f"peer.end {({k: e.get(k) for k in ('bench', 'flags', 'manifest_len', 'manifest_why', 'rows')})}; "
                                f"seats {seats}; {cb.grep(lines, 'endbench state')}")
    want_gil = GIL_ALT if facts["gil"] == GIL_MARK else GIL_MARK
    items = m.get("items") or []
    pe = cb.peer(st)
    led.check("S9-B2", m.get("gil_before") == want_gil and m.get("gil_gain") == GIL_GAIN and len(items) == 1
              and items[0].get("count") == 7 and facts["bag"].get(items[0].get("id"), 0) == 0
              and isinstance(m.get("card"), int) and m["card"] != 255 and m["card"] not in facts["cards"]
              and pe.get("bench_manifest") == 1 and pe.get("bench_manifest_note") is None,
              f"gil_before {m.get('gil_before')!r} (party gil {facts['gil']!r}) gain {m.get('gil_gain')!r}; items {items} "
              f"(bag holds {[facts['bag'].get(i.get('id'), 0) for i in items]}); card {m.get('card')!r} (held "
              f"{facts['cards'][:12]}...); bench_manifest {pe.get('bench_manifest')!r} note {pe.get('bench_manifest_note')!r}")
    first = min(seats) if seats else None
    bad = []
    for r in rows:
        s = r.get("slot")
        seat = seats.get(s)
        if seat is None or r.get("char") != seat[0] or r.get("lv_before") != seat[1] or r.get("exp_before") != seat[2] \
                or r.get("ap_gain") != 5:
            bad.append(f"slot {s}: {({k: r.get(k) for k in ('char', 'lv_before', 'exp_before', 'ap_gain')})} vs seat {seat}")
    r0 = next((r for r in rows if r.get("slot") == first), {})
    learns = r0.get("learns") or []
    led.check("S9-B3", not bad and rows and r0 and r0.get("lv_after") == (r0.get("lv_before") or -9) + 2
              and _status(r0) & (POISON | BLIND) and len(learns) == 1 and learns[0].get("ap_at") == 3,
              f"mismatches {bad[:4]}; first row (slot {first}) lv {r0.get('lv_before')!r}->{r0.get('lv_after')!r} status "
              f"{r0.get('status')!r} learns {learns}")
    ok, why = _eb(g, "manifest", 3)
    m3 = _man(_peer_end(g.state)) or {}
    chars = {s[0] for s in seats.values()}
    hit = [r.get("char") for r in m3.get("rows") or [] if r.get("char") in chars]
    led.check("S9-B4", ok and m3.get("rows") and not hit, why or f"rows' chars {[r.get('char') for r in m3.get('rows') or []]} vs "
                                                                f"seated {sorted(chars)}")
    ok, why = _eb(g, "manifest", 2)
    e2 = _peer_end(g.state) or {}
    m2 = _man(e2) or {}
    led.check("S9-B5", ok and cb.mask_bits(e2.get("flags")) & 8 and m2.get("rows")
              and all(r.get("exp_gain") == 0 and r.get("ap_gain") == 0 for r in m2.get("rows") or [])
              and m2.get("gil_gain") == ESC_GIL and m2.get("items") == [] and m2.get("card") == 255,
              why or f"flags {e2.get('flags')!r}; manifest {m2}")
    ok, why = _eb(g, "manifest", 0)
    e0 = _peer_end(g.state) or {}
    led.check("S9-B6", ok and "manifest" in e0 and e0.get("manifest") is None and not cb.mask_bits(e0.get("flags")) & 2
              and e0.get("manifest_len") == 0 and e0.get("rows") == 0,
              why or f"peer.end {({k: e0.get(k, 'ABSENT') for k in ('manifest', 'flags', 'manifest_len', 'rows')})}")
    ok, why = _eb(g, "manifest", 4)
    led.check("S9-B7", not ok and "needs 0 (none), 1" in why, f"accepted" if ok else why)
    ok, why = _eb(g, "clear")
    cleared = cb.poll(g, lambda s: _peer_end(s) is None, 2.0, "peer.end to read null")
    tree2, twhy2 = cb.extra_tree(g, field=field)
    f2 = _tree_facts(tree2) if tree2 is not None else None
    led.check("S9-B8", ok and cleared is not None and f2 is not None and f2 == facts,
              twhy2 or f"peer.end={_peer_end(g.state)!r}; baselines {'unchanged' if f2 == facts else f'CHANGED {facts} -> {f2}'}")


def _battle_to_state0(g) -> tuple:
    """`battle 67` fought to the win, then the result screen at state 0. (state or None, why, frame before the battle)."""
    st0 = g.state
    try:
        g.start_battle(cb.SCENE)
    except HarnessError as err:
        return None, f"`battle {cb.SCENE}` did not start: {str(err)[:200]}", st0.frame
    try:
        g.fight(timeout=FIGHT_S, finish=False)
    except HarnessError as err:
        return None, f"the battle reached no result: {str(err)[:200]}", st0.frame
    st = cb.poll(g, lambda s: (_ru(s) or {}).get("state") == 0 and not (_ru(s) or {}).get("loading"), 30.0,
                 "the result screen at state 0")
    if st is None:
        return None, f"no result screen at state 0 (result_ui={_ru(g.state)!r} ui={g.state.ui_state!r})", st0.frame
    g.wait_frames(10)
    return g.state, "", st0.frame


def _confirm_out(g) -> str:
    for _ in range(40):
        st = g.state
        if not st.in_battle and st.ui_state not in ("BattleHUD", "BattleResult"):
            break
        g.press("confirm", 4)
        g.wait_frames(20)
    st = cb.poll(g, lambda s: s.on_field and s.ui_state == "FieldHUD", 30.0, "the field after the result screen") or g.state
    return st.ui_state


def _row(ru: dict, slot) -> dict:
    return next((r for r in (ru or {}).get("rows") or [] if r.get("slot") == slot), {})


def _leg_c(g, led: cb.Ledger) -> None:
    g.note("S9-C: a real own battle -- the host capture, the loopback decode and the live result screen")
    cids = [c for c in led.catalog if c.startswith("S9-C")]
    _eb(g, "clear")
    h0, p0 = cb.host(g.state), cb.peer(g.state)
    cap0, rx0 = h0.get("manifest_captures"), p0.get("manifest_rx")
    at = cb.mark(g)
    st, why, _ = _battle_to_state0(g)
    if st is None:
        led.unreached(cids, why)
        if g.state.in_battle or g.state.ui_state == "BattleResult":
            _confirm_out(g)
        return
    h, p = cb.host(st), cb.peer(st)
    he, pe = _host_end(st) or {}, _peer_end(st) or {}
    hm = h.get("manifest") if isinstance(h.get("manifest"), dict) else None
    pm = _man(pe)
    ru = _ru(st) or {}
    led.check("S9-C1", isinstance(cap0, int) and h.get("manifest_captures") == cap0 + 1 and h.get("manifest_why") is None
              and (h.get("manifest_bytes") or 0) > 0 and cb.mask_bits(he.get("flags")) & 2
              and he.get("manifest_len") == h.get("manifest_bytes"),
              f"captures {cap0!r}->{h.get('manifest_captures')!r} why={h.get('manifest_why')!r} bytes={h.get('manifest_bytes')!r}; "
              f"host.end flags={he.get('flags')!r} manifest_len={he.get('manifest_len')!r}")
    led.check("S9-C2", hm is not None and pe.get("bench") is False and _strip_host_only(pm) == _strip_host_only(hm)
              and pe.get("rows") == len(hm.get("rows") or []) and p.get("manifest_nonce") == p.get("nonce")
              and isinstance(rx0, int) and p.get("manifest_rx") == rx0 + 1,
              f"peer.end bench={pe.get('bench')!r} rows={pe.get('rows')!r}; manifests equal: "
              f"{_strip_host_only(pm) == _strip_host_only(hm)}; nonce {p.get('manifest_nonce')!r}/{p.get('nonce')!r} rx "
              f"{rx0!r}->{p.get('manifest_rx')!r}")
    _c3(led, hm, ru)
    _c4(g, led, hm)
    _c5(g, led, hm)
    bonus = cb.battle(g.state).get("bonus") or {}
    need = [r for r in (hm or {}).get("rows") or [] if r.get("need_exp")]
    led.check("S9-C6", hm is not None and hm.get("gil_gain") == bonus.get("gil") and need
              and hm.get("default_exp") == (bonus.get("exp") or 0) // len(need),
              f"gil_gain {(hm or {}).get('gil_gain')!r} vs bonus.gil {bonus.get('gil')!r}; default_exp "
              f"{(hm or {}).get('default_exp')!r} vs bonus.exp {bonus.get('exp')!r} // {len(need)}")
    lines = cb.new(g, at)
    led.check("S9-C7", any(CAPTURED in ln and RIDES in ln for ln in lines)
              and any(PEER_HELD in ln and "): held rows " in ln and PEER_STORED in ln for ln in lines),
              cb.grep(lines, "battle result manifest", limit=900))
    ended = _confirm_out(g)
    st = cb.poll(g, lambda s: cb.peer(s).get("live") is False, 5.0, "the lane to fall") or g.state
    h = cb.host(st)
    led.check("S9-C8", ended == "FieldHUD" and h.get("manifest_bytes") == 0 and isinstance(h.get("manifest"), dict)
              and cb.peer(st).get("live") is False,
              f"ended on {ended}; manifest_bytes={h.get('manifest_bytes')!r} manifest kept: {isinstance(h.get('manifest'), dict)}; "
              f"peer.live={cb.peer(st).get('live')!r}")


def _c3(led: cb.Ledger, hm: dict | None, ru: dict) -> None:
    if hm is None or not ru:
        led.check("S9-C3", False, f"not reached: manifest {'present' if hm else 'absent'}, result_ui "
                                  f"{'present' if ru else 'absent'}")
        return
    bad = []
    lab, model = ru.get("labels") or {}, ru.get("model") or {}
    if cb.digits(lab.get("exp")) != str(hm.get("default_exp")):
        bad.append(f"exp label {lab.get('exp')!r} vs {hm.get('default_exp')}")
    if cb.digits(lab.get("ap")) != str(hm.get("default_ap")):
        bad.append(f"ap label {lab.get('ap')!r} vs {hm.get('default_ap')}")
    for r in hm.get("rows") or []:
        w = _row(ru, r.get("slot"))
        want = {"level": str(r.get("lv_before")), "exp": str(r.get("exp_before")), "dim": not r.get("draw"),
                "need_exp": r.get("need_exp"), "need_ap": r.get("need_ap"), "exp_value": r.get("exp_gain"),
                "ap_value": r.get("ap_gain")}
        got = {"level": cb.digits(w.get("level")), "exp": cb.digits(w.get("exp")), "dim": w.get("dim"),
               "need_exp": w.get("need_exp"), "need_ap": w.get("need_ap"), "exp_value": w.get("exp_value"),
               "ap_value": w.get("ap_value")}
        if got != want:
            bad.append(f"row {r.get('slot')}: {got} vs {want}")
    mwant = {"default_exp": hm.get("default_exp"), "default_ap": hm.get("default_ap"), "gil_value": hm.get("gil_gain"),
             "party_gil": hm.get("gil_before"), "card": hm.get("card")}
    mgot = {k: model.get(k) for k in mwant}
    if mgot != mwant:
        bad.append(f"model {mgot} vs {mwant}")
    its = [{"id": i.get("id"), "count": i.get("count")} for i in ru.get("items") or []]
    if its != (hm.get("items") or []):
        bad.append(f"items {its} vs {hm.get('items')}")
    led.check("S9-C3", not bad, "; ".join(bad)[:900] or "every label, row, model value and item agrees")


def _c4(g, led: cb.Ledger, hm: dict | None) -> None:
    st = g.state
    if hm is None or (_ru(st) or {}).get("state") != 0:
        led.unreached(("S9-C4", "S9-C4L"), f"manifest {'present' if hm else 'absent'}, result state "
                                           f"{(_ru(st) or {}).get('state')!r}")
        return
    g.press("confirm", 4)                    # ONE short press (< 500 ms: BattleAutoConfirm never repeats it)
    s1 = cb.poll(g, lambda s: (_ru(s) or {}).get("state") == 1, 2.0, "state 1 at once")
    s2 = cb.poll(g, lambda s: (_ru(s) or {}).get("state") == 2, 60.0, "the natural end of the ticks (state 2)")
    ru = _ru(s2 or g.state) or {}
    bad = []
    for r in hm.get("rows") or []:
        w = _row(ru, r.get("slot"))
        if cb.digits(w.get("level")) != str(r.get("lv_after")) \
                or w.get("level_ups") != (r.get("lv_after") or 0) - (r.get("lv_before") or 0):
            bad.append(f"row {r.get('slot')}: level {w.get('level')!r} ups {w.get('level_ups')!r} vs {r.get('lv_before')}->"
                       f"{r.get('lv_after')}")
    sched = sorted((r.get("slot"), l.get("abil"), l.get("ap_at")) for r in hm.get("rows") or [] for l in r.get("learns") or [])
    fired = sorted((x.get("slot"), x.get("abil"), x.get("ap_at")) for x in cb.host(g.state).get("learned") or [])
    led.check("S9-C4", s1 is not None and s2 is not None and not bad and fired == sched,
              f"state 1 {'seen' if s1 else 'NOT seen'}, state 2 {'reached' if s2 else 'NOT reached'}; {bad[:4]}; "
              f"learned {fired} vs schedule {sched}")
    # The sheet singles out the learn half (host.learned == the schedule ON THE NATURAL TICK PATH), and an empty schedule
    # makes that equality hold vacuously ([] == []). Record it as its own check so a fight that teaches nothing is visible.
    if not sched:
        g.note("S9-C4: this fight taught nothing (the manifest's learn schedule is empty) -- the learn half is NOT proven; "
               "equip an ability whose remaining AP <= the fight's AP for a teaching fight")
        led.check("S9-C4L", False, f"not reached: the fight taught nothing (schedule [], host.learned {fired}) -- the "
                                   f"natural-tick learn equality is untested; use a teaching fight")
    else:
        led.check("S9-C4L", s2 is not None and fired == sched,
                  f"state 2 {'reached' if s2 else 'NOT reached'}; learned {fired} vs schedule {sched}")


def _c5(g, led: cb.Ledger, hm: dict | None) -> None:
    if hm is None or (_ru(g.state) or {}).get("state") != 2:
        led.check("S9-C5", False, f"not reached: result state {(_ru(g.state) or {}).get('state')!r}")
        return
    g.press("confirm", 4)
    st = cb.poll(g, lambda s: (_ru(s) or {}).get("state") == 3 and not (_ru(s) or {}).get("loading"), 10.0, "state 3")
    ru = _ru(st or g.state) or {}
    lab = ru.get("labels") or {}
    shown = [{"id": i.get("id"), "count": i.get("count")} for i in ru.get("items") or [] if i.get("shown")]
    card_ok = hm.get("card") == 255 or (ru.get("card_shown") is True and bool(lab.get("card")))
    led.check("S9-C5", st is not None and cb.digits(lab.get("gil_receive")) == str(hm.get("gil_gain"))
              and cb.digits(lab.get("gil_current")) == str(hm.get("gil_before")) and shown == (hm.get("items") or [])
              and card_ok,
              f"labels {lab}; shown items {shown} vs {hm.get('items')}; card {hm.get('card')!r} shown {ru.get('card_shown')!r}")


def _leg_d(g, led: cb.Ledger) -> None:
    g.note("S9-D: the item overflow (a 99-drop sandbox save)")
    at = cb.mark(g)
    st, why, _ = _battle_to_state0(g)
    if st is None:
        led.check("S9-D1", False, f"not reached: {why}")
        return
    seen = []
    for _ in range(30):
        g.press("confirm", 4)
        samples = cb.hold_for(g, 0.4)
        hit = next((x for x in samples if cb.host(x).get("overflow") is True), None)
        if hit is not None:
            seen.append(hit)
            break
        if (_ru(g.state) or {}).get("state") in (None, 7, 8):
            break
    s = seen[0] if seen else g.state
    lines = cb.new(g, at)
    led.check("S9-D1", bool(seen) and cb.mask_bits((_host_end(s) or {}).get("flags")) & 4
              and cb.mask_bits((_peer_end(s) or {}).get("flags")) & 4 and cb.count(lines, OVERFLOW_HOST) == 1
              and (_ru(s) or {}).get("state") == 4,
              f"overflow seen {bool(seen)}; host flags {(_host_end(s) or {}).get('flags')!r} peer flags "
              f"{(_peer_end(s) or {}).get('flags')!r} state {(_ru(s) or {}).get('state')!r}; {cb.grep(lines, 'overflow')}")
    _confirm_out(g)


def _leg_e(g, led: cb.Ledger) -> None:
    g.note("S9-E: the stage's lever -- `endbench manifest host off` ships nothing (the capture still records)")
    ok, why = _eb(g, "manifest", "host", "off")
    if not ok:
        led.unreached(("S9-E1", "S9-E2"), f"`endbench manifest host off` refused -- {why}")
        return
    rx0 = cb.peer(g.state).get("manifest_rx")
    at = cb.mark(g)
    st, bwhy, _ = _battle_to_state0(g)
    if st is None:
        led.check("S9-E1", False, f"not reached: {bwhy}")
    else:
        h, he, pe = cb.host(st), _host_end(st) or {}, _peer_end(st) or {}
        lines = cb.new(g, at)
        led.check("S9-E1", h.get("manifest_mode") == "off" and isinstance(h.get("manifest"), dict)
                  and not cb.mask_bits(he.get("flags")) & 2 and he.get("manifest_len") == 0 and "manifest" in pe
                  and pe.get("manifest") is None and pe.get("rows") == 0 and cb.peer(st).get("manifest_rx") == rx0
                  and any(CAPTURED in ln and HOST_OFF in ln for ln in lines),
                  f"mode={h.get('manifest_mode')!r} host.manifest kept={isinstance(h.get('manifest'), dict)} host.end flags="
                  f"{he.get('flags')!r} len={he.get('manifest_len')!r}; peer.end manifest={pe.get('manifest', 'ABSENT')!r} "
                  f"rows={pe.get('rows')!r} rx {rx0!r}->{cb.peer(st).get('manifest_rx')!r}; {cb.grep(lines, 'manifest (host)')}")
        _confirm_out(g)
    ok, why = _eb(g, "manifest", "host", "on")
    led.check("S9-E2", ok and cb.host(g.state).get("manifest_mode") == "on", why or
              f"manifest_mode={cb.host(g.state).get('manifest_mode')!r}")


# =========================================================================================== PART 10
class _R:
    """One replay walk's facts."""
    def __init__(self):
        self.fp0 = None
        self.fp1 = None
        self.w1 = []                 # (where, hash, writes) violations
        self.w1_reads = 0


def _w1(r: _R, st, where: str) -> None:
    f, s = _fp(st), _scr(st)
    r.w1_reads += 1
    if r.fp1 is None or f is None or f.get("hash") != r.fp1.get("hash") or s.get("writes") not in (0,):
        r.w1.append((where, (f or {}).get("hash"), s.get("writes")))


def _boot(g, field: int) -> tuple:
    _eb(g, "clear")
    ok, why = cb.boot(g)
    if not ok:
        cb.back_to_field(g, field)
        return None, why
    st = cb.wait_steady(g)
    if st is None:
        cb.leave(g, field)
        return None, "the diorama never reached its command phase"
    return st, ""


def _victory_r8(g, timeout: float = 12.0):
    ok, why = _eb(g, "victory")
    if not ok:
        return None, f"`endbench victory` refused -- {why}"
    st = cb.poll(g, lambda s: cb.bend(s).get("injected") is True and (cb.bend(s).get("r8_hits") or 0) > 0, timeout,
                 "the injection and the first R8 hit")
    return st, ("" if st is not None else f"no injection + R8 within {timeout:.0f}s "
                                          f"(end={cb.pick(cb.bend(g.state), 'injected', 'r8_hits', 'why')})")


def _open(g, field: int, *pre) -> tuple:
    """A fresh boot -> `manifest 1` (+ ``pre`` ops) -> victory + R8 -> `ui 1` -> the replay open. (state, M, why)."""
    st, why = _boot(g, field)
    if st is None:
        return None, None, why
    for args in (("manifest", "1"),) + tuple(pre):
        ok, w = _eb(g, *args)
        if not ok:
            return None, None, f"`endbench {' '.join(args)}` refused -- {w}"
    m = _man(_peer_end(g.state))
    st, why = _victory_r8(g)
    if st is None:
        return None, m, why
    ok, w = _eb(g, "ui", "1")
    if not ok:
        return None, m, f"`endbench ui 1` refused -- {w}"
    st = cb.poll(g, lambda s: _rep(s).get("opened") is True and (_ru(s) or {}).get("state") == 0, 4.0, "the replay open")
    return st, m, ("" if st is not None else f"the replay never opened "
                                             f"(replay={cb.pick(_rep(g.state), 'armed', 'opened', 'verdict', 'why')})")


def _leave_with_hide(g, field: int) -> tuple:
    """`state 7` and the end-leave's return (or a manual leave if none comes). (returned via the end-leave, why)."""
    _eb(g, "state", "7")
    st = cb.poll(g, lambda s: not cb.dio(s).get("booted") and s.field_id == field and cb.free(s), 20.0, "the end-leave return")
    if st is not None:
        cb.arrive(g, field)
        return True, ""
    cb.leave(g, field)
    return False, "no end-leave within 20 s (left by hand)"


def _part10(g, led: cb.Ledger, field: int, ctx: dict) -> None:
    st = g.state
    have = cb.has(st, cb.PROBES[10])
    led.check("S10-P0", have, f"netsync.battle.end keys: {sorted(cb.bend(st))}")
    fp_inv, why = cb.fingerprint(g, field=field)
    ctx["fp_inv"], ctx["fp_inv_why"] = fp_inv, why
    at = cb.mark(g)
    ok, why = _eb(g, "selftest")
    lines = cb.wait_log(g, at, "harness: battle end-block selftest", 2.0)
    hit = next((ln for ln in lines if "harness: " + SELFTEST10 in ln), "")
    m = re.search(r"replay (\d+)\)", hit)
    led.check("S10-R0", ok and m is not None and int(m.group(1)) == REPLAY_PINS,
              why or cb.grep(lines, "end-block selftest") + f" (want replay {REPLAY_PINS})")
    r = _R()
    _r1(g, led, field, r)
    _r2(g, led, field)
    _r3(g, led, field, r)
    _r4(g, led, field, r)
    _r5(g, led, field)
    _r6(g, led, field)
    _l1(g, led, field)
    _l2(g, led, field, r)


def _r1(g, led: cb.Ledger, field: int, r: _R) -> None:
    g.note("S10-R1: the full walk -- every page stepped only by the bench host's state")
    cids = [c for c in led.catalog if c.startswith("S10-R1") or c in ("S10-W0", "S10-W1", "S10-W2")]
    r.fp0 = _fp(g.state)
    r0 = cb.dio(g.state).get("returns")
    st, why = _boot(g, field)
    if st is None:
        led.unreached(cids, why)
        return
    r.fp1 = _fp(g.state)
    led.check("S10-W0", r.fp0 is not None and r.fp1 == r.fp0,
              f"FP0 {r.fp0}; FP1 {r.fp1}; differing components "
              f"{[k for k in (r.fp0 or {}) if (r.fp0 or {}).get(k) != (r.fp1 or {}).get(k)]}")
    ok, mwhy = _eb(g, "manifest", "1")
    if not ok:
        # an engine before stage 9 (or a refusal): the walk goes on WITHOUT a manifest, so the calibration still records
        # what the pre-stage guest does at the host's victory and Hide (the black hold, then the stage-6 exit)
        g.note(f"R1: `endbench manifest 1` refused -- {mwhy} -- walking on with no manifest (the pre-stage record)")
    M = _man(_peer_end(g.state)) or {}
    at = cb.mark(g)
    st, why8 = _victory_r8(g)
    if st is not None:
        # The first doc with r8_hits > 0 can still read verdict 3 (ArmNoR8): NoteR8 runs in the battle update
        # (btl_sys.ManageBattleEnd), ReplayArmTick in NetSyncClient.Update's EndTick, and their order within a frame is
        # Unity's. Judge the verdict once the arm tick has seen the R8 hit (bounded; it stays 5 until `ui 1`).
        st = cb.poll(g, lambda s: _rep(s).get("verdict") == V_HOST_NOT_ON, 2.0, "the replay-wait verdict 5") or st
    lines = cb.wait_log(g, at, WAIT5, 2.0)
    rp = _rep(st or g.state)
    led.check("S10-R1a", ok and st is not None and rp.get("armed") is False and rp.get("verdict") == V_HOST_NOT_ON
              and cb.count(lines, WAIT5) == 1,
              ("" if ok else f"`endbench manifest 1` refused -- {mwhy}; ") + (why8 or f"replay="
              f"{({k: rp.get(k) for k in ('armed', 'verdict', 'why')})}; {cb.grep(lines, 'replay-wait')}"))
    if st is None:
        led.unreached([c for c in cids if c not in led.done], why8)
        _leave_with_hide(g, field)
        _note_pre_stage(g)
        return
    at = cb.mark(g)
    _eb(g, "ui", "1")
    st = cb.poll(g, lambda s: _rep(s).get("opened") is True and (_ru(s) or {}).get("state") == 0, 2.0, "the replay open")
    s = st or g.state
    rp, ru = _rep(s), _ru(s) or {}
    lines = cb.wait_log(g, at, OPENED, 1.5)
    ia = next((i for i, ln in enumerate(lines) if ARMED in ln), None)
    io = next((i for i, ln in enumerate(lines) if OPENED in ln and "(fingerprint 0x" in ln), None)
    led.check("S10-R1b", st is not None and rp.get("armed") is True and rp.get("verdict") == V_GO
              and rp.get("host_state_at_arm") == 0 and rp.get("row_mask") == rp.get("seated_mask")
              and rp.get("manifest_rows") == len(M.get("rows") or []) and ru.get("replay") is True and ru.get("state") == 0
              and ia is not None and io is not None and ia < io,
              f"replay={cb.pick(rp, 'armed', 'opened', 'verdict', 'why', 'host_state_at_arm', 'row_mask', 'seated_mask')} "
              f"manifest_rows={rp.get('manifest_rows')!r} "
              f"result_ui replay={ru.get('replay')!r} state={ru.get('state')!r}; {cb.grep(lines, 'REPLAY', 'result replay')}")
    if st is None:
        r8a = cb.bend(g.state).get("r8_hits")
        held = cb.hold_for(g, 2.0)
        r8b = cb.bend(g.state).get("r8_hits")
        g.note(f"R1 (no replay): over 2 s battle.result_ui {'stayed null' if all(_ru(x) is None for x in held) else 'SHOWED'}; "
               f"r8_hits {r8a!r} -> {r8b!r} (rising = the black hold)")
        led.unreached([c for c in cids if c not in led.done], "the replay never opened")
        _leave_with_hide(g, field)
        _note_pre_stage(g)
        return
    g.wait_frames(10)
    s = g.state
    _w1(r, s, "page 1")
    ru = _ru(s) or {}
    lab = ru.get("labels") or {}
    bad = []
    for x in M.get("rows") or []:
        w = _row(ru, x.get("slot"))
        if not (w.get("shown") is True and cb.digits(w.get("level")) == str(x.get("lv_before"))
                and cb.digits(w.get("exp")) == str(x.get("exp_before")) and w.get("dim") == (not x.get("draw"))):
            bad.append(f"row {x.get('slot')}: {w}")
    p1, pw = cb.shot(g, "s10-1-start")
    led.check("S10-R1c", cb.digits(lab.get("exp")) == str(M.get("default_exp"))
              and cb.digits(lab.get("ap")) == str(M.get("default_ap"))
              and not bad and p1 is not None and cb.png_not_blank(p1),
              f"labels exp {lab.get('exp')!r} ap {lab.get('ap')!r} vs M {M.get('default_exp')}/{M.get('default_ap')}; "
              f"rows off {bad[:3]}; "
              f"{p1 or pw}")
    at = cb.mark(g)
    for _ in range(3):
        g.press("confirm", 4)
        g.wait_frames(12)
    g.hold("confirm", 120)                       # ~2 s at 60 fps (~4 s at 31): BattleAutoConfirm repeats every 100 ms
    g.wait_frames(10)
    s = g.state
    _w1(r, s, "after the inert presses")
    sc = _scr(s)
    lines = cb.new(g, at)
    led.check("S10-R1d", sc.get("state") == 0 and sc.get("steps") == 0 and (sc.get("local_confirms") or 0) >= 3
              and cb.count(lines, INERT) == 1,
              f"screen state={sc.get('state')!r} steps={sc.get('steps')!r} local_confirms={sc.get('local_confirms')!r}; "
              f"{cb.grep(lines, 'inert')}")
    first = min((x.get("slot") for x in M.get("rows") or []), default=None)
    x0 = next((x for x in M.get("rows") or [] if x.get("slot") == first), {})
    learn = (x0.get("learns") or [{}])[0]
    _eb(g, "state", "1")
    # the EXP and the AP tick side by side: wait for BOTH the first row's shadow level and its scheduled learn (or the
    # natural end of the ticks, state 2 -- the check then says which one never came)
    st = cb.poll(g, lambda s: (next((w for w in _scr(s).get("rows") or [] if w.get("slot") == first), {}).get("level")
                               == x0.get("lv_after") and len(_scr(s).get("learned") or []) >= 1) or _scr(s).get("state") == 2,
                 25.0, "the first row's shadow level to reach lv_after and its learn to fire")
    s = st or g.state
    _w1(r, s, "state 1")
    sc, ru = _scr(s), _ru(s) or {}
    p2, pw = cb.shot(g, "s10-2-levelup")
    # state 1 (EXPAndAPTick) -- or already 2 when the ticks ran out between two reads: the trail is the step's receipt
    led.check("S10-R1e", st is not None and sc.get("steps") == 1 and sc.get("trail") == ["0>1"] and sc.get("state") in (1, 2)
              and _row(ru, first).get("level_ups") == 2
              and sc.get("learned") == [{"slot": first, "abil": learn.get("abil"), "ap": 3}] and _shown(p2),
              f"steps={sc.get('steps')!r} trail={sc.get('trail')!r} state={sc.get('state')!r} learned={sc.get('learned')!r} "
              f"(want {[{'slot': first, 'abil': learn.get('abil'), 'ap': 3}]}); level_ups={_row(ru, first).get('level_ups')!r}; "
              f"{p2 or pw}")
    _eb(g, "state", "2")
    st = cb.poll(g, lambda s: _scr(s).get("state") == 2, 30.0, "the natural end of the ticks")
    s = st or g.state
    _w1(r, s, "state 2")
    sc = _scr(s)
    led.check("S10-R1f", st is not None and sc.get("steps") == 1 and sc.get("follow") == FOLLOW_IN_STEP,
              f"state={sc.get('state')!r} steps={sc.get('steps')!r} follow={sc.get('follow')!r} ({sc.get('follow_why')!r})")
    _eb(g, "state", "2", "loading")
    st = cb.poll(g, lambda s: _scr(s).get("state") == 3 and not (_ru(s) or {}).get("loading"), 10.0, "state 3 after the fade")
    g.wait_frames(10)
    s = g.state
    _w1(r, s, "state 3")
    sc, ru = _scr(s), _ru(s) or {}
    lab = ru.get("labels") or {}
    shown = [{"id": i.get("id"), "count": i.get("count")} for i in ru.get("items") or [] if i.get("shown")]
    p3, pw = cb.shot(g, "s10-3-gil-items")
    trail = sc.get("trail") or []
    led.check("S10-R1g", st is not None and sc.get("steps") == 2 and len(trail) >= 2 and trail[1] == "2>2L"
              and cb.digits(lab.get("gil_receive")) == str(M.get("gil_gain"))
              and cb.digits(lab.get("gil_current")) == str(M.get("gil_before"))
              and shown == (M.get("items") or []) and ru.get("card_shown") is True and sc.get("gil") == M.get("gil_before")
              and (ru.get("model") or {}).get("party_gil") == (r.fp0 or {}).get("gil") and _shown(p3),
              f"steps={sc.get('steps')!r} trail={trail} labels={lab} shown={shown} (M {M.get('items')}) card_shown="
              f"{ru.get('card_shown')!r} screen.gil={sc.get('gil')!r} party_gil={(ru.get('model') or {}).get('party_gil')!r} "
              f"(FP0 gil {(r.fp0 or {}).get('gil')!r}); {p3 or pw}")
    at = cb.mark(g)
    _eb(g, "overflow", "1")
    _eb(g, "state", "4")
    st = cb.poll(g, lambda s: _scr(s).get("state") == 4 and _scr(s).get("overflow_shown") is True, 6.0, "the ItemFullDialog")
    g.wait_frames(10)
    s = g.state
    _w1(r, s, "state 4")
    sc = _scr(s)
    p4, pw = cb.shot(g, "s10-4-item-full")
    lines = cb.new(g, at)
    led.check("S10-R1h", st is not None and sc.get("steps") == 3 and cb.count(lines, OVERFLOWED) == 1 and _shown(p4),
              f"state={sc.get('state')!r} steps={sc.get('steps')!r} overflow_shown={sc.get('overflow_shown')!r}; "
              f"{cb.grep(lines, 'items --')}; {p4 or pw}")
    _eb(g, "state", "5")
    st = cb.poll(g, lambda s: _scr(s).get("state") == 5 and (_scr(s).get("gil") or 0) > (M.get("gil_before") or 0), 6.0,
                 "state 5 and the gil rising")
    s = st or g.state
    _w1(r, s, "state 5")
    led.check("S10-R1i", st is not None, f"state={_scr(s).get('state')!r} gil={_scr(s).get('gil')!r} (from {M.get('gil_before')!r})")
    _eb(g, "state", "6")
    want_gil = (M.get("gil_before") or 0) + (M.get("gil_gain") or 0)
    st = cb.poll(g, lambda s: _scr(s).get("state") == 6 and _scr(s).get("gil") == want_gil, 10.0, "state 6 with the whole gil")
    s = st or g.state
    _w1(r, s, "state 6")
    p5, pw = cb.shot(g, "s10-5-end")
    led.check("S10-R1j", st is not None and _shown(p5), f"state={_scr(s).get('state')!r} gil={_scr(s).get('gil')!r} "
                                                             f"(want {want_gil}); {p5 or pw}")
    led.check("S10-W1", r.w1_reads >= 7 and not r.w1, f"{r.w1_reads} page read(s); violations (where, hash, writes) {r.w1[:4]} "
                                                       f"(FP1 hash {(r.fp1 or {}).get('hash')!r})")
    at = cb.mark(g)
    _eb(g, "state", "7")
    end = cb.poll(g, lambda s: _rep(s).get("closed") is True or not cb.dio(s).get("booted"), 8.0, "the replay's own close")
    s = end or g.state
    rp, sc, el = _rep(s), _scr(s), _el(s)
    back = cb.poll(g, lambda x: not cb.dio(x).get("booted") and x.field_id == field and cb.free(x), 20.0, "the end-leave return")
    if back is None:
        cb.leave(g, field)
    else:
        cb.arrive(g, field)
    lines = cb.new(g, at)
    el = _el(g.state)
    rp = _rep(g.state) or rp
    iw = next((i for i, ln in enumerate(lines) if WAITS in ln), None)
    ic = next((i for i, ln in enumerate(lines) if CLOSED_OWN in ln), None)
    ie = next((i for i, ln in enumerate(lines) if WAIT_ENDED in ln and WAIT_OWN in ln), None)
    trail = (sc.get("trail") or [])
    led.check("S10-R1k", el.get("trigger") == "result-hide" and trail[-1:] == ["6>7"] and rp.get("closed") is True
              and rp.get("exit_waited") is True and isinstance(rp.get("exit_wait_ms"), int) and 0 <= rp["exit_wait_ms"] < 5000
              and rp.get("aborted") is False and None not in (iw, ic, ie) and iw < ic < ie
              and str(el.get("music_why") or "").startswith(MUSIC_REPLAY) and el.get("wipe_lifted") is False,
              f"trigger={el.get('trigger')!r} trail={trail} "
              f"replay={cb.pick(rp, 'closed', 'exit_waited', 'exit_wait_ms', 'aborted', 'abort_why')} "
              f"music_why={el.get('music_why')!r} wipe_lifted={el.get('wipe_lifted')!r}; line order {iw, ic, ie}; "
              f"{cb.grep(lines, 'end-leave', 'result replay: CLOSED', limit=700)}")
    s = g.state
    led.check("S10-R1l", back is not None and isinstance(r0, int) and cb.dio(s).get("returns") == r0 + 1
              and cb.dio(s).get("last_return") == "warm" and cb.battle(s).get("result") == 1,
              f"returned via the end-leave: {back is not None}; returns {r0!r}->{cb.dio(s).get('returns')!r} "
              f"last={cb.dio(s).get('last_return')!r} battle.result={cb.battle(s).get('result')!r}")
    fpn = _fp(g.state)
    led.check("S10-W2", r.fp0 is not None and fpn == r.fp0,
              f"FP0 {r.fp0}; after {fpn}; differing {[k for k in (r.fp0 or {}) if (r.fp0 or {}).get(k) != (fpn or {}).get(k)]}")
    _eb(g, "clear")


def _note_pre_stage(g) -> None:
    """The calibration record of a walk that never opened a replay: what the stage-6 exit did on the field."""
    el = _el(g.state)
    g.note(f"R1 (pre-stage record): end_leave trigger={el.get('trigger')!r} music_shut={el.get('music_shut')!r} "
           f"wipe_lifted={el.get('wipe_lifted')!r} music_why={el.get('music_why')!r}; returns="
           f"{cb.dio(g.state).get('returns')!r} battle.result={cb.battle(g.state).get('result')!r}")


def _r2(g, led: cb.Ledger, field: int) -> None:
    g.note("S10-R2: the quit guard -- a host step never answers the guest's own quit prompt (NO Confirm while it is up)")
    st, M, why = _open(g, field)
    if st is None:
        led.check("S10-R2", False, f"not reached: {why}")
        if cb.dio(g.state).get("booted"):
            _leave_with_hide(g, field)
        return
    at = cb.mark(g)
    r0 = cb.dio(g.state).get("returns")
    ok, qwhy = _eb(g, "quit", "on")
    up = cb.poll(g, lambda s: cb.quit_prompt_up(s), 2.0, "the quit prompt") if ok else None
    if up is None:
        if ok:
            _eb(g, "quit", "off")
        led.check("S10-R2", False, qwhy or f"not reached: the quit prompt never showed (ui {g.state.ui_state!r})")
        _leave_with_hide(g, field)
        return
    _eb(g, "state", "1")
    samples = cb.hold_for(g, 2.0)
    moved = [(cb.frame_of(x), _scr(x).get("state"), _scr(x).get("steps"), _scr(x).get("follow")) for x in samples
             if _scr(x).get("state") != 0 or _scr(x).get("steps") != 0 or _scr(x).get("follow") != FOLLOW_QUIT]
    g.press("cancel", 4)
    closed = cb.poll(g, lambda s: not cb.quit_prompt_up(s), 2.0, "the prompt to close")
    if closed is None:
        _eb(g, "quit", "off")                         # never a Confirm: its Yes quits the game
    stepped = cb.poll(g, lambda s: _scr(s).get("steps") == 1, 1.0, "the step after the prompt") if closed else None
    lines = cb.new(g, at)
    left, lwhy = _leave_with_hide(g, field)
    led.check("S10-R2", samples and not moved and closed is not None and stepped is not None
              and cb.count(lines, QUIT_ON) == 1 and isinstance(r0, int) and cb.dio(g.state).get("returns") == r0 + 1,
              f"while the prompt was up (frame, state, steps, follow) off-hold: {moved[:4]}; closed by Cancel: "
              f"{closed is not None}; stepped within 1 s: {stepped is not None}; returns {r0!r}->{cb.dio(g.state).get('returns')!r} "
              f"{lwhy}; {cb.grep(lines, 'quit')}")
    _eb(g, "clear")


def _r3(g, led: cb.Ledger, field: int, r: _R) -> None:
    g.note("S10-R3: a manifest whose charIds match no seated member is REFUSED")
    st, why = _boot(g, field)
    if st is None:
        led.check("S10-R3", False, f"not reached: {why}")
        return
    r0 = cb.dio(g.state).get("returns")
    ok, w = _eb(g, "manifest", "3")
    at = cb.mark(g)
    st, why = _victory_r8(g) if ok else (None, w)
    _eb(g, "ui", "1")
    s = cb.poll(g, lambda x: _rep(x).get("refused") is True, 3.0, "the refusal") or g.state
    rp = _rep(s)
    no_screen = all(_ru(x) is None for x in cb.hold_for(g, 1.0))
    lines = cb.new(g, at)
    left, lwhy = _leave_with_hide(g, field)
    fpn = _fp(g.state)
    led.check("S10-R3", st is not None and rp.get("refused") is True and rp.get("verdict") == V_NO_ROW
              and rp.get("opened") is False and no_screen and cb.count(lines, REFUSED) == 1 and left
              and isinstance(r0, int) and cb.dio(g.state).get("returns") == r0 + 1 and r.fp0 is not None and fpn == r.fp0,
              why or f"replay={({k: rp.get(k) for k in ('refused', 'verdict', 'opened')})} screen absent: {no_screen}; left "
                     f"{left} {lwhy}; fp == FP0: {fpn == r.fp0}; {cb.grep(lines, 'REPLAY')}")
    _eb(g, "clear")


def _r4(g, led: cb.Ledger, field: int, r: _R) -> None:
    g.note("S10-R4: a dioleave mid-tick ABORTS the replay")
    st, M, why = _open(g, field)
    if st is None:
        led.check("S10-R4", False, f"not reached: {why}")
        if cb.dio(g.state).get("booted"):
            cb.leave(g, field)
        return
    _eb(g, "state", "1")
    cb.poll(g, lambda s: _scr(s).get("state") == 1, 3.0, "the tick page")
    at = cb.mark(g)
    left, lwhy = cb.leave(g, field)
    lines = cb.new(g, at)
    s = g.state
    rp, sc, el = _rep(s), _scr(s), _el(s)
    fpn = _fp(s)
    led.check("S10-R4", left and rp.get("aborted") is True and rp.get("abort_why") == "a leave of the diorama"
              and sc.get("aborted") is True and cb.count(lines, ABORTED_DIO) == 1
              and any(ABORTED_SCREEN in ln and "tick loops 105/109 stopped" in ln for ln in lines)
              and el.get("music_shut") is True and el.get("wipe_lifted") is True and r.fp0 is not None and fpn == r.fp0,
              lwhy or f"replay aborted={rp.get('aborted')!r} why={rp.get('abort_why')!r} screen.aborted={sc.get('aborted')!r}; "
                      f"music_shut={el.get('music_shut')!r} wipe_lifted={el.get('wipe_lifted')!r}; fp == FP0: {fpn == r.fp0}; "
                      f"{cb.grep(lines, 'ABORTED', 'aborted')}")
    _eb(g, "clear")


def _shown(p) -> bool:
    """A page shot was taken and decodes non-blank (READ it after the run: the numbers on it are the host's)."""
    return p is not None and cb.png_not_blank(p)


def _no_arm(g, verdict: int, field: int) -> tuple:
    """After `ui 1`: for 2 s nothing arms and no screen shows, the verdict ``verdict``. (ok, detail)."""
    _eb(g, "ui", "1")
    samples = cb.hold_for(g, 2.0)
    armed = [cb.frame_of(x) for x in samples if _rep(x).get("armed") or _ru(x) is not None]
    rp = _rep(g.state)
    return (samples and not armed and rp.get("verdict") == verdict,
            f"armed/screen on {armed[:4]}; verdict={rp.get('verdict')!r} ({rp.get('why')!r})")


def _r5(g, led: cb.Ledger, field: int) -> None:
    g.note("S10-R5: the negatives -- AfterEvent, and no manifest")
    st, why = _boot(g, field)
    if st is None:
        led.check("S10-R5a", False, f"not reached: {why}")
    else:
        ok1, w1 = _eb(g, "manifest", "1")
        ok2, w2 = _eb(g, "afterevent", "1")
        s, why = _victory_r8(g) if ok1 and ok2 else (None, w1 or w2)
        good, detail = _no_arm(g, V_AFTER_EVENT, field) if s is not None else (False, why)
        led.check("S10-R5a", good, detail)
        _leave_with_hide(g, field)
        _eb(g, "clear")
    st, why = _boot(g, field)
    if st is None:
        led.check("S10-R5b", False, f"not reached: {why}")
        return
    ok, w = _eb(g, "manifest", "0")
    s, why = _victory_r8(g) if ok else (None, w)
    good, detail = _no_arm(g, V_NO_MANIFEST, field) if s is not None else (False, why)
    left, lwhy = _leave_with_hide(g, field)
    el = _el(g.state)
    led.check("S10-R5b", good and left and el.get("trigger") == "result-hide" and el.get("music_shut") is True
              and el.get("wipe_lifted") is True,
              f"{detail}; left via the end-leave {left} {lwhy}; "
              f"end_leave {cb.pick(el, 'trigger', 'music_shut', 'wipe_lifted', 'music_why')}")
    _eb(g, "clear")


def _walk_to_end(g) -> bool:
    """Step an open replay to state 6 the R1 way (state 1, 2 loading, 6), no assertions. True when it got there."""
    _eb(g, "state", "1")
    cb.poll(g, lambda s: _scr(s).get("steps") == 1, 4.0, "step 1")
    _eb(g, "state", "2", "loading")
    cb.poll(g, lambda s: _scr(s).get("state") == 3 and not (_ru(s) or {}).get("loading"), 30.0, "state 3")
    _eb(g, "state", "6")
    return cb.poll(g, lambda s: _scr(s).get("state") == 6, 15.0, "state 6") is not None


def _r6(g, led: cb.Ledger, field: int) -> None:
    g.note("S10-R6: the host keeps its field song -- the replay's hide tail keeps it too (fixer S10-R1)")
    st, M, why = _open(g, field)
    if st is None:
        led.check("S10-R6", False, f"not reached: {why}")
        if cb.dio(g.state).get("booted"):
            _leave_with_hide(g, field)
        return
    at_end = _walk_to_end(g)
    ok, w = _eb(g, "fieldsong", "1")
    at = cb.mark(g)
    left, lwhy = _leave_with_hide(g, field)
    lines = cb.new(g, at)
    el = _el(g.state)
    led.check("S10-R6", at_end and ok and left and any(CLOSED_OWN in ln and SONG_KEPT in ln for ln in lines)
              and str(el.get("music_why") or "").startswith(HOST_KEEPS) and el.get("music_shut") is False
              and el.get("wipe_lifted") is False,
              (w or "") + f" reached state 6: {at_end}; left {left} {lwhy}; end_leave "
                          f"{({k: el.get(k) for k in ('music_shut', 'wipe_lifted', 'music_why')})}; {cb.grep(lines, 'CLOSED')}")
    _eb(g, "clear")


def _l1(g, led: cb.Ledger, field: int) -> None:
    g.note("S10-L1: the lever `endbench replay off` -- the pre-stage guest holds black")
    ok, why = _eb(g, "replay", "off")
    if not ok:
        led.check("S10-L1", False, f"not reached: `endbench replay off` refused -- {why}")
        return
    st, why = _boot(g, field)
    if st is None:
        led.check("S10-L1", False, f"not reached: {why}")
    else:
        ok1, w1 = _eb(g, "manifest", "1")
        s, why = _victory_r8(g) if ok1 else (None, w1)
        good, detail = _no_arm(g, V_LEVER, field) if s is not None else (False, why)
        led.check("S10-L1", good and _rep(g.state).get("mode") == "off", f"{detail}; mode={_rep(g.state).get('mode')!r}")
        _eb(g, "replay", "on")
        _leave_with_hide(g, field)
    _eb(g, "replay", "on")
    _eb(g, "clear")


def _l2(g, led: cb.Ledger, field: int, r: _R) -> None:
    g.note("S10-L2: the lever `endbench replay local` -- the guest's own Confirm steps the replay (writers still closed)")
    ok, why = _eb(g, "replay", "local")
    if not ok:
        led.check("S10-L2", False, f"not reached: `endbench replay local` refused -- {why}")
        return
    st, M, why = _open(g, field)
    if st is None:
        led.check("S10-L2", False, f"not reached: {why}")
        _eb(g, "replay", "on")
        if cb.dio(g.state).get("booted"):
            _leave_with_hide(g, field)
        return
    fp_open = _fp(g.state)
    g.press("confirm", 4)
    s = cb.poll(g, lambda x: (_scr(x).get("local_steps") or 0) > 0, 3.0, "a local step") or g.state
    sc = _scr(s)
    fpn = _fp(s)
    led.check("S10-L2", (sc.get("local_steps") or 0) > 0 and sc.get("steps") == 0 and sc.get("writes") == 0
              and fpn is not None and fp_open is not None and fpn.get("hash") == fp_open.get("hash")
              and (r.fp1 is None or fpn.get("hash") == r.fp1.get("hash")) and _rep(s).get("mode") == "local",
              f"local_steps={sc.get('local_steps')!r} steps={sc.get('steps')!r} writes={sc.get('writes')!r} state="
              f"{sc.get('state')!r}; fp hash {(fp_open or {}).get('hash')!r} -> {(fpn or {}).get('hash')!r}")
    _eb(g, "replay", "on")
    _leave_with_hide(g, field)
    _eb(g, "clear")


def _release(g, led: cb.Ledger) -> None:
    """The levers left PULLED on purpose, then `reset`: each must be released with its line."""
    pre = []
    if PART9:
        ok, why = _eb(g, "manifest", "host", "off")
        pre += [] if ok else [why]
    if PART10:
        ok, why = _eb(g, "replay", "off")
        pre += [] if ok else [why]
    at = cb.mark(g)
    cb.release(g)
    st = g.state
    lines = cb.new(g, at)
    need = ([REL_MANIFEST] if PART9 else []) + ([REL_REPLAY] if PART10 else [])
    missing = [n for n in need if cb.count(lines, n) != 1]
    led.check("S910-R", not pre and not missing and (st.netsync or {}).get("forced") is False,
              "; ".join(pre) + f" missing lines {missing}; {cb.grep(lines, 'released with the harness')}")
