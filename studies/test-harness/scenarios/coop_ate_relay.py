"""s161 -- THE ATE RELAY (studies/field-coop/ATE-RELAY.md, memoria-patches s161), the SOLO bench. [ff9mapkit netsync s161]

THE DEFECT (the 2026-10-28 two-PC session, Dali 352, "Vivi, Confused"). Each copy draws the ATE icon itself, but the menu opens
only on a Select read with control ON (352's Code1 loop: `usercontrol == 1 && byte238 == 1 && B_KEYON(Select)`), which the host
never relayed and the guest masks on purpose (MISC-08). So the guest's copy never opened the menu (text 98), and its title card
(text 100) and white fade never ran; the follow carried the guest to 350 instead of its own script.

THE FIX (s161). The host NOTES its control-on Select hit and relays it (ring kind 3) only when that reader opens an ATE-caption
window (its own menu actually opening -- `&&` does not short-circuit, so the raw read runs every frame). The guest serves Select to
that reader's control-on reads every key tick until its OWN ATE menu opens (served is not success: the proof is the open), and once
the lock closes that menu on the host's own choice, the copy's own Field() passes the gateway redirect. ATE captions never start
the step-out.

THE BENCH. One instance root, the selftest role, real field 352 at scenario 2600 with its ATE gate set directly: byte 238 = 1 (the
availability Code2 would write) and word 241 = 2 (the enabled rows: "Vivi, Confused"; the window adds Cancel). The HOST half is the
R9 tap-record lane (bench 1, lock 0, `tap-record 1`: this copy plays the host, its REAL host taps go to the tape); the GUEST half is
`replay` into a locked copy (bench 1, lock 1, hostscene 1). The guest transport (the intent follow and its holds, the destination's
own jump out) is not on the selftest role: NetSyncAte.SelfTest's rows and the two-PC check carry it.

  K0      provenance; a fresh process; newgame; warp 352 (entrance 0, scenario 2600) with control; noencounter; `netsync selftest 1`.
  K1      "ATE relay selftest: OK (156 rows, 58 mutants caught, ...)" within 20 s; `netsync.ate.selftest` "ok".
  K2      `netsync.ate` at rest: lever null, host_armed false, pending.on false, episode.phase null.
  R-N0    RECORDING, byte 238 = 0 (the ATE unavailable): a Select press is NOTED (arms +1: the raw read ran) and relays nothing (no
          'ATE relay RECORDED' line, relayed +0, no window, the tape still empty).
  R-REC   RECORDING, the gate set: a Select opens this copy's ATE menu (win 1 text 98) and the tape takes ONE 'ATE relay RECORDED:
          uid U opened its ATE menu (win 1 text 98)' (relayed +1); the pick of "Vivi, Confused" tapes its CHO (kind 1, idx 1) and the
          title's Confirm its close (win 0 text 100). The tape holds the three in that order.
  T-TTL   REPLAY into a locked copy whose gate is FALSE (byte 238 = 0): the press is queued and served (served +N, N > 0), and after
          PressTtlMs it EXPIRES with 'its gate never passed' -- no ATE window opened. Served is not success.
  P-QUEUE REPLAY, the gate set: 'host seq S queued (field 352 uid U ...)' and 'served to uid U's Select read'.
  P-MENU  ...'opened my copy's ATE menu (win 1 text 98, uid U' and the lock's own 'win 1 text 98 opened locked'.
  P-PICK  ...the lock closed it on the host's choice ('win 1 text 98 closed (host seq N, choice 1)') and the relay noted it
          ('the host's choice 1 closed my copy's ATE menu'); `ate.episode.by_host` true.
  P-TITLE ...the title card opened locked and closed on the host's event ('win 0 text 100 opened locked', 'win 0 text 100 closed
          (host seq').
  P-JUMP  ...'my copy's own Field(350) passes -- the host's pick (choice 1) on field 352', and no 'bounced to a reload' line.
  P-LAND  ...ONE load of 350 ('Map: 350' once), 'my copy's own Field(350) landed', and the ATE's first line 'win 4 text 321 opened
          locked' (the copy plays the ATE on 350, entrance 16).
  S1      ...the step-out never went OUT from the replay to the landing, and while the menu or the title was up the step-out's base
          read the ATE term (`stepout.base.why_not` == NetSyncAte.StepOutTerm, `ate.stepout_exempt` true).
  K-R     `reset` releases the lever (its line when a calibration held one); re-read with the role: lever null.

THE CALIBRATIONS (COOP_CALIBRATE), each pulled right after R-REC (the tape is recorded on the shipping rule, so the lever's reds
are the GUEST half's alone) and held to the end:
  COOP_CALIBRATE=1 (or off)   `ate off`: the s160 rule on the guest. PREDICTED_OFF = T-TTL, P-QUEUE, P-MENU, P-PICK, P-TITLE,
                              P-JUMP, P-LAND, S1 red, each with OFF_MARKER (the 'ignored -- the ate lever is off' line, no menu).
  COOP_CALIBRATE=noexempt     `ate noexempt`: the relay on, the s158 step-out on the ATE menu. PREDICTED_NOEXEMPT = S1 red with
                              NOEXEMPT_MARKER (a step-out OUT while the menu was up).

    py tools/play.py studies/test-harness/scenarios/coop_ate_relay.py --instance C:\\gd\\ff9-inst\\host
    COOP_CALIBRATE=1 py tools/play.py studies/test-harness/scenarios/coop_ate_relay.py --instance C:\\gd\\ff9-inst\\host
    COOP_CALIBRATE=noexempt py tools/play.py studies/test-harness/scenarios/coop_ate_relay.py --instance C:\\gd\\ff9-inst\\host
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

KEY = "netsync.ate"
PROBE = KEY + ".opened"                  # key PRESENCE is the capability (protocol 5, additive)

HUB = 352                                # Dali/Inn: the "Vivi, Confused" ATE (the owner's two-PC check)
DEST = 350                               # Dali/Village Road: the ATE's field (entrance 16)
SCENARIO = 2600                          # the morning after the inn rest (the two-PC session's)
B_AVAIL = 238                            # Global.SByte[238]: Code1's availability term
B_ROWS_LO, B_ROWS_HI = 241, 242          # Global.Int16[241]: EnableDialogChoices' row mask
ROWS = 2                                 # row 1 "Vivi, Confused" (the window adds Cancel)
MENU_WIN, MENU_TEXT = 1, 98
TITLE_WIN, TITLE_TEXT = 0, 100
PICK = 1
FIRST_LINE = (4, 321)                    # 350's ATE: WindowAsync(4, 128, 321) "!"

SELFTEST_S = 20.0
ARRIVE_S = 25.0
MENU_S = 4.0
REPLAY_S = 20.0
TTL_WAIT_S = 7.5                         # PressTtlMs (5 s) and a margin
STEP_TERM = "an ATE caption is open on my copy (the menu or its title card)"
PROOF_RX = re.compile(r"ATE relay selftest: OK \((\d+) rows, (\d+) mutants caught")
LOG_RELEASE = "[NetSync] harness: ATE relay lever released (act)"

CLAIMS = {
    "K0": "the forced selftest role on 352 (newgame, warp 352 at scenario 2600 with control, noencounter, `netsync selftest 1`); "
          "a fresh process",
    "K1": "the s161 proof line 'ATE relay selftest: OK (156 rows, 58 mutants caught, ...)' within 20 s, and "
          "`netsync.ate.selftest` 'ok'",
    "K2": "`netsync.ate` at rest: lever null, host_armed false, pending.on false, episode.phase null",
    "R-N0": "recording with the ATE unavailable (byte 238 = 0): a Select is noted (arms +1) and relays nothing (no RECORDED ATE "
            "line, relayed +0, no window, the tape empty)",
    "R-REC": "recording with the gate set: one 'ATE relay RECORDED: uid U opened its ATE menu (win 1 text 98)' (relayed +1), the "
             "pick's CHO (kind 1, idx 1) and the title's close (win 0 text 100) taped after it",
    "T-TTL": "a replay into a copy whose gate is false: queued, served on N > 0 key ticks, then expired 'its gate never passed' "
             "with no ATE window opened",
    "P-QUEUE": "the replay queued the press and served it to uid U's Select read",
    "P-MENU": "the replay opened my copy's ATE menu (the relay's 'opened my copy's ATE menu (win 1 text 98' and the lock's "
              "'win 1 text 98 opened locked')",
    "P-PICK": "the lock closed the menu on the host's choice 1 and the relay noted it; episode.by_host true",
    "P-TITLE": "the title card opened locked and closed on the host's event",
    "P-JUMP": "my copy's own Field(350) passed ('the host's pick (choice 1) on field 352'), no bounce",
    "P-LAND": "one load of 350, the relay's landed line, and the ATE's first line 'win 4 text 321 opened locked'",
    "S1": "no step-out OUT from the replay to the landing; while an ATE caption was up the base read the ATE term and "
          "ate.stepout_exempt was true",
    "K-R": "`reset` releases the lever (its line when a calibration held one); re-read with the role: lever null",
}
PREDICTED_OFF = ("T-TTL", "P-QUEUE", "P-MENU", "P-PICK", "P-TITLE", "P-JUMP", "P-LAND", "S1")
PREDICTED_NOEXEMPT = ("S1",)
OFF_MARKER = "the guest ignored the press ('ignored -- the ate lever is off') and no ATE menu opened"
NOEXEMPT_MARKER = "a step-out OUT while the ATE menu was up"
FINALS = ("K-R", "K-CAL-M", "K-CAL")


def calibration() -> str | None:
    v = os.environ.get("COOP_CALIBRATE", "").strip().lower()
    if v in ("", "0"):
        return None
    return "noexempt" if v == "noexempt" else "off"


def catalog(cal: str | None) -> dict:
    cat = dict(CLAIMS)
    if cal is not None:
        marker = OFF_MARKER if cal == "off" else NOEXEMPT_MARKER
        predicted = PREDICTED_OFF if cal == "off" else PREDICTED_NOEXEMPT
        cat["K-CAL-M"] = "every predicted red carries its marker: " + marker
        cat["K-CAL"] = f"the `ate {cal}` calibration: exactly " + ", ".join(predicted) + " red"
    return cat


# --------------------------------------------------------------------------------------------- reads (pure)
def ate(x) -> dict | None:
    b = cb.path(x, KEY)
    return b if isinstance(b, dict) else None


def ate_get(x, dotted: str, default=None):
    cur = ate(x)
    for k in dotted.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def counter(x, name: str) -> int:
    v = ate_get(x, name)
    return v if isinstance(v, int) else -1


def control(x) -> bool:
    return bool((cb.raw(x).get("player") or {}).get("control", False))


def field_of(x) -> int:
    return int((cb.raw(x).get("field") or {}).get("id", -1))


def dialog_open(x) -> bool:
    return bool((cb.raw(x).get("dialog") or {}).get("open", False))


def opened_locked(lines, win: int, text: int) -> int:
    return cb.count(lines, f"dialogue lock: win {win} text {text} opened locked")


def judge_queue(lines) -> tuple:
    q = cb.matching(lines, r"ATE relay: host seq \d+ queued \(field %d uid \d+" % HUB)
    s = cb.matching(lines, r"ATE relay: host seq \d+ served to uid \d+'s Select read")
    return bool(q) and bool(s), f"queued {len(q)}, served lines {len(s)}; {cb.grep(lines, 'ATE relay', limit=500)}"


def judge_menu(lines) -> tuple:
    o = cb.matching(lines, r"ATE relay: host seq \d+ opened my copy's ATE menu \(win %d text %d, uid \d+" % (MENU_WIN, MENU_TEXT))
    lk = opened_locked(lines, MENU_WIN, MENU_TEXT)
    return len(o) == 1 and lk >= 1, f"relay opened {len(o)}, lock opened {lk}; {cb.grep(lines, 'opened', limit=500)}"


def judge_pick(lines, by_host_seen: bool) -> tuple:
    c = cb.matching(lines, r"dialogue: win %d text %d closed \(host seq \d+, choice %d\)" % (MENU_WIN, MENU_TEXT, PICK))
    n = cb.count(lines, f"ATE relay: the host's choice {PICK} closed my copy's ATE menu")
    return len(c) == 1 and n == 1 and by_host_seen, (f"lock closes {len(c)}, relay notes {n}, by_host seen {by_host_seen}; "
                                                     f"{cb.grep(lines, 'text 98', limit=400)}")


def judge_title(lines) -> tuple:
    lk = opened_locked(lines, TITLE_WIN, TITLE_TEXT)
    c = cb.matching(lines, r"dialogue: win %d text %d closed \(host seq \d+" % (TITLE_WIN, TITLE_TEXT))
    return lk >= 1 and len(c) == 1, f"opened locked {lk}, host closes {len(c)}; {cb.grep(lines, 'text 100', limit=400)}"


def judge_jump(lines) -> tuple:
    p = cb.count(lines, f"ATE relay: my copy's own Field({DEST}) passes -- the host's pick (choice {PICK}) on field {HUB}")
    b = cb.count(lines, "bounced to a reload")
    return p == 1 and b == 0, f"own-jump passes {p}, bounces {b}; {cb.grep(lines, 'Field(', 'bounced', limit=400)}"


def judge_land(lines) -> tuple:
    maps = cb.count(lines, f"Map: {DEST} ")
    landed = cb.count(lines, f"ATE relay: my copy's own Field({DEST}) landed")
    first = opened_locked(lines, *FIRST_LINE)
    return maps == 1 and landed == 1 and first >= 1, (f"Map: {DEST} x{maps}, landed {landed}, 321 opened locked {first}; "
                                                      f"{cb.grep(lines, 'Map:', 'landed', 'text 321', limit=400)}")


def judge_s1(lines, samples) -> tuple:
    outs = cb.count(lines, "step-out: OUT on field")
    term = [s for s in samples if cb.path(s, "netsync.stepout.base.why_not") == STEP_TERM]
    exempt = [s for s in samples if ate_get(s, "stepout_exempt") is True]
    return outs == 0 and bool(term) and bool(exempt), (f"OUT lines {outs}; samples with the ATE term {len(term)}, exempt "
                                                       f"{len(exempt)} of {len(samples)}; {cb.grep(lines, 'step-out', limit=300)}")


def off_marker(lines) -> tuple:
    ign = cb.count(lines, "-- the ate lever is off")
    menu = opened_locked(lines, MENU_WIN, MENU_TEXT)
    return ign >= 1 and menu == 0, f"ignored lines {ign}, menus opened {menu}"


def noexempt_marker(lines) -> tuple:
    out = cb.count(lines, "step-out: OUT on field")
    menu = opened_locked(lines, MENU_WIN, MENU_TEXT)
    return out >= 1 and menu >= 1, f"OUT lines {out}, menus opened {menu}"


# --------------------------------------------------------------------------------------------- the run
class Ctx:
    def __init__(self, cal: str | None):
        self.cal = cal
        self.k0_ok = False
        self.lever_held = False
        self.marks: dict = {}            # leg -> its fresh log lines (the calibration markers read them)


def _ns(g, sub: str, *args) -> tuple:
    return cb.try_ns(g, sub, *args)


def _must(g, sub: str, *args) -> None:
    ok, why = _ns(g, sub, *args)
    if not ok:
        raise HarnessError(f"netsync {sub} {' '.join(str(a) for a in args)} refused: {why}")


def _gate(g, avail: int) -> None:
    """The ATE gate on the copy, AFTER its load (Code2 never writes 238/241 here: its arm needs flag 2102)."""
    g.poke(B_AVAIL, avail)
    g.poke(B_ROWS_LO, ROWS & 0xFF)
    g.poke(B_ROWS_HI, (ROWS >> 8) & 0xFF)


def _arrive(g) -> tuple:
    """Warp to 352 (entrance 0, scenario 2600) and wait for control there, paging any line that opens on the way in."""
    try:
        g.warp(HUB, entrance=0, scenario=SCENARIO)
    except HarnessError as err:
        return False, f"warp {HUB} failed: {str(err)[:200]}"
    deadline = time.time() + ARRIVE_S
    st = g.state
    while time.time() < deadline:
        st = g.state
        if field_of(st) == HUB and control(st) and not dialog_open(st):
            return True, ""
        if dialog_open(st):
            g.press("confirm", 2)
        g.wait_frames(6)
    return False, f"no control on {HUB}: field {field_of(st)} control {control(st)} dialog {dialog_open(st)}"


def _fresh_hub(g, *, lock: bool, scene: bool) -> None:
    """Between legs: the lock OFF (the inbox drains with the session half), a fresh load of 352, then the bench levers."""
    _must(g, "lock", 0)
    _must(g, "hostscene", 0)
    ok, why = _arrive(g)
    if not ok:
        raise HarnessError(why)
    _must(g, "bench", 1)
    if lock:
        _must(g, "lock", 1)
        cb.poll(g, lambda s: (s.netsync or {}).get("lock_engaged") is True, 3.0, "the bench lock to engage")
    if scene:
        _must(g, "hostscene", 1)


def run(g, field: int | None = None):
    cal = calibration()
    st0 = cb.poll(g, lambda s: s.netsync is not None, 15.0, "the netsync block (protocol 5)") or g.state
    ctx = Ctx(cal)
    led = cb.Ledger(g, catalog(cal), finals=FINALS, width=1400)
    if field is not None:
        g.note(f"--field {field} is ignored: the bench uses 352 -> 350")
    if not cb.has(st0, PROBE):
        g.note("this engine publishes no `netsync.ate` (s161): every leg is red by absence")
    try:
        ctx.k0_ok = _k0(g, ctx, led)
        if not ctx.k0_ok:
            led.close("not reached: K0 (the setup) refused")
            return
        _k1_k2(g, led)
        _guard(g, led, "R-N0", lambda: _r_n0(g, ctx, led))
        _guard(g, led, "R-REC", lambda: _r_rec(g, ctx, led))
        if cal is not None:
            ok, why = _ns(g, "ate", cal)
            st = cb.poll(g, lambda s: ate_get(s, "lever") == cal, 3.0, f"the {cal} lever read back")
            ctx.lever_held = ok and st is not None
            g.note(f"CALIBRATION: `ate {cal}` {'taken' if ok else 'REFUSED: ' + why}, held to the end (after the recording); "
                   f"predicted red {', '.join(PREDICTED_OFF if cal == 'off' else PREDICTED_NOEXEMPT)}")
        _guard(g, led, "T-TTL", lambda: _t_ttl(g, ctx, led))
        _guard(g, led, "P-QUEUE", lambda: _replay(g, ctx, led))
    except HarnessError as err:
        g.note(f"the run raised: {str(err)[:400]}")
        led.close(f"not reached: the run raised ({str(err)[:200]})")
    finally:
        for sub, arg in (("tap-record", 0), ("hostscene", 0), ("lock", 0)):
            try:
                _ns(g, sub, arg)
            except HarnessError:
                pass
        if ctx.k0_ok:
            _k_r(g, ctx, led)
        else:
            led.unreached(["K-R"], "K0 refused")
        g.note(f"Memoria.log archived: {cb.archive_log(g, 'ate-relay-' + (cal or 'plain'))}")
        if cal is not None:
            led.close("not reached: the run ended before this check")
            predicted = PREDICTED_OFF if cal == "off" else PREDICTED_NOEXEMPT
            judge = off_marker if cal == "off" else noexempt_marker
            marks_ok = all(leg in ctx.marks and judge(ctx.marks[leg])[0] for leg in predicted)
            led.check("K-CAL-M", marks_ok, "; ".join(f"{leg}: {judge(ctx.marks[leg])[1] if leg in ctx.marks else 'NO RUN'}"
                                                     for leg in predicted))
            led.judge_calibration("K-CAL", predicted)
        led.close(final=True)


def _guard(g, led: cb.Ledger, leg: str, fn) -> None:
    if leg not in led.catalog or leg in led.done:
        return
    try:
        fn()
    except HarnessError as err:
        led.unreached([leg], f"the leg raised: {str(err)[:300]}")
    except Exception as err:                             # noqa: BLE001 - a BENCH bug: red and loud, the run goes on
        g.note(f"{leg} FAULTED (a bench bug, not a verdict): {err!r}"[:400])
        led.unreached([leg], f"the leg FAULTED (a bench bug): {err!r}"[:300])
    if leg not in led.done:
        led.unreached([leg], "the leg recorded nothing")


def _k0(g, ctx: Ctx, led: cb.Ledger) -> bool:
    cb.provenance(g)
    if getattr(g, "attach", False):
        led.check("K0", False, "refused: --attach (a reused process carries earlier counters and episodes)")
        return False
    try:
        g.newgame()
    except HarnessError as err:
        led.check("K0", False, f"newgame failed: {str(err)[:300]}")
        return False
    ok, why = _arrive(g)
    if not ok:
        led.check("K0", False, why)
        return False
    try:
        g.no_encounters(True)
    except (HarnessError, AttributeError) as err:
        g.note(f"noencounter refused ({str(err)[:120]})")
    ok1, why1 = _ns(g, "selftest", 1)
    st = cb.poll(g, lambda s: bool((s.netsync or {}).get("forced")) and bool((s.netsync or {}).get("selftest")), 5.0,
                 "the forced selftest role") or g.state
    ns = st.netsync or {}
    good = ok1 and bool(ns.get("forced")) and bool(ns.get("selftest")) and field_of(st) == HUB
    led.check("K0", good, f"selftest={ns.get('selftest')!r} forced={ns.get('forced')!r} field={field_of(st)}"
                          + (f"; {why1}" if why1 else ""))
    return good


def _k1_k2(g, led: cb.Ledger) -> None:
    lines = cb.wait_log(g, 0, "ATE relay selftest:", timeout=SELFTEST_S)
    m = next((PROOF_RX.search(ln) for ln in lines if PROOF_RX.search(ln)), None)
    st = cb.poll(g, lambda s: ate_get(s, "selftest") is not None, SELFTEST_S, "netsync.ate.selftest") or g.state
    led.check("K1", m is not None and ate_get(st, "selftest") == "ok",
              f"{cb.grep(lines, 'ATE relay selftest')}; ate.selftest {ate_get(st, 'selftest')!r}")
    st = g.state
    parts = [("present", ate(st) is not None), ("lever null", ate_get(st, "lever") is None),
             ("host_armed false", ate_get(st, "host_armed") is False), ("pending off", ate_get(st, "pending.on") is False),
             ("no episode", ate_get(st, "episode.phase") is None)]
    led.check("K2", all(v for _, v in parts), ", ".join(f"{k} {'ok' if v else 'NO'}" for k, v in parts))


def _record_mode(g) -> None:
    """The R9 lane: bench 1, lock 0, a fresh tape -- this copy plays the host."""
    _must(g, "bench", 1)
    _must(g, "lock", 0)
    cb.poll(g, lambda s: (s.netsync or {}).get("lock_engaged") is not True, 3.0, "the lock to disengage")
    _must(g, "tap-record", 1)


def _r_n0(g, ctx: Ctx, led: cb.Ledger) -> None:
    _record_mode(g)
    _gate(g, 0)
    g.wait_frames(10)
    st = g.state
    a0, r0 = counter(st, "arms"), counter(st, "relayed")
    at = cb.mark(g)
    g.press("select", 2)
    cb.hold_for(g, 1.0)
    st = g.state
    lines = cb.new(g, at)
    tape = (st.netsync or {}).get("tape")
    parts = [("arms +1", counter(st, "arms") == a0 + 1), ("relayed +0", counter(st, "relayed") == r0),
             ("no RECORDED ATE line", cb.count(lines, "ATE relay RECORDED") == 0), ("no window", not dialog_open(st)),
             ("tape empty", tape == 0)]
    led.check("R-N0", all(v for _, v in parts), ", ".join(f"{k} {'ok' if v else 'NO'}" for k, v in parts)
              + f"; arms {a0}->{counter(st, 'arms')}, relayed {r0}->{counter(st, 'relayed')}, tape {tape!r}")


def _r_rec(g, ctx: Ctx, led: cb.Ledger) -> None:
    _gate(g, 1)
    g.wait_frames(10)
    r0 = counter(g.state, "relayed")
    at = cb.mark(g)
    g.press("select", 2)
    st = cb.poll(g, lambda s: s.choice is not None, MENU_S, "the recording copy's ATE menu")
    picked = None
    if st is not None:
        try:
            picked = g.choose_landed(PICK)
        except HarnessError as err:
            g.note(f"R-REC: the pick refused: {str(err)[:200]}")
    title = cb.poll(g, lambda s: dialog_open(s) and "Vivi" in (s.text or ""), 4.0, "the recording copy's title card")
    if title is not None:
        g.wait_frames(20)
        g.press("confirm", 4)
    cb.hold_for(g, 2.0)
    _ns(g, "tap-record", 0)
    st = g.state
    lines = cb.new(g, at)
    rec_ate = cb.matching(lines, r"ATE relay RECORDED: uid \d+ opened its ATE menu \(win %d text %d\)" % (MENU_WIN, MENU_TEXT))
    rec_cho = cb.matching(lines, r"dialog tap RECORDED: win %d text %d kind 1 idx %d" % (MENU_WIN, MENU_TEXT, PICK))
    rec_ttl = cb.matching(lines, r"dialog tap RECORDED: win %d text %d kind 0 .* closes" % (TITLE_WIN, TITLE_TEXT))
    order = (lines.index(rec_ate[0]) < lines.index(rec_cho[0]) < lines.index(rec_ttl[0])) if rec_ate and rec_cho and rec_ttl else False
    tape = (st.netsync or {}).get("tape")
    parts = [("menu", st is not None), ("one RECORDED ATE", len(rec_ate) == 1), ("relayed +1", counter(st, "relayed") == r0 + 1),
             ("CHO taped", len(rec_cho) == 1), ("title close taped", len(rec_ttl) == 1), ("in order", order),
             ("tape >= 3", isinstance(tape, int) and tape >= 3)]
    led.check("R-REC", all(v for _, v in parts), ", ".join(f"{k} {'ok' if v else 'NO'}" for k, v in parts)
              + f"; picked {picked!r}; tape {tape!r}; {cb.grep(lines, 'RECORDED', limit=600)}")


def _t_ttl(g, ctx: Ctx, led: cb.Ledger) -> None:
    _fresh_hub(g, lock=True, scene=True)
    _gate(g, 0)                                          # the copy's gate FALSE: Code1 reads Select, never opens the menu
    g.wait_frames(10)
    st = g.state
    s0, e0 = counter(st, "served"), counter(st, "expired")
    at = cb.mark(g)
    _must(g, "replay")
    cb.hold_for(g, TTL_WAIT_S)
    st = g.state
    lines = cb.new(g, at)
    ctx.marks["T-TTL"] = lines
    exp = cb.matching(lines, r"ATE relay: host seq \d+ \(field %d uid \d+, win %d text %d\) expired -- my copy's ATE menu never "
                             r"opened \((\d+) key tick\(s\) served: its gate never passed\)" % (HUB, MENU_WIN, MENU_TEXT))
    parts = [("queued", bool(cb.matching(lines, r"ATE relay: host seq \d+ queued"))),
             ("served > 0", counter(st, "served") > s0), ("expired +1", counter(st, "expired") == e0 + 1),
             ("'its gate never passed'", len(exp) == 1), ("no ATE window", opened_locked(lines, MENU_WIN, MENU_TEXT) == 0)]
    led.check("T-TTL", all(v for _, v in parts), ", ".join(f"{k} {'ok' if v else 'NO'}" for k, v in parts)
              + f"; served {s0}->{counter(st, 'served')}; {cb.grep(lines, 'ATE relay', limit=500)}")


def _replay(g, ctx: Ctx, led: cb.Ledger) -> None:
    _fresh_hub(g, lock=True, scene=True)
    _gate(g, 1)
    g.wait_frames(10)
    at = cb.mark(g)
    _must(g, "replay")
    samples, hit = cb.watch(g, lambda s: field_of(s) == DEST and opened_locked(cb.new(g, at), *FIRST_LINE) >= 1, REPLAY_S)
    cb.hold_for(g, 0.5)
    lines = cb.new(g, at)
    for leg in ("P-QUEUE", "P-MENU", "P-PICK", "P-TITLE", "P-JUMP", "P-LAND", "S1"):
        ctx.marks[leg] = lines
    by_host_seen = any(ate_get(s, "episode.by_host") is True for s in samples)
    caption_samples = [s for s in samples if field_of(s) == HUB and dialog_open(s)]
    land_at = next((i for i, ln in enumerate(lines) if f"Map: {DEST} " in ln), len(lines))
    for leg, (ok, detail) in (("P-QUEUE", judge_queue(lines)), ("P-MENU", judge_menu(lines)),
                              ("P-PICK", judge_pick(lines, by_host_seen)), ("P-TITLE", judge_title(lines)),
                              ("P-JUMP", judge_jump(lines)), ("P-LAND", judge_land(lines)),
                              ("S1", judge_s1(lines[:land_at], caption_samples))):
        led.check(leg, ok, detail)
    if hit is None:
        g.note(f"the replay never reached {DEST}'s first ATE line in {REPLAY_S:.0f} s: field {field_of(g.state)}")


def _k_r(g, ctx: Ctx, led: cb.Ledger) -> None:
    at = cb.mark(g)
    try:
        cb.release(g)
    except HarnessError as err:
        led.check("K-R", False, f"the release raised: {str(err)[:200]}")
        return
    lines = cb.new(g, at)
    try:
        _ns(g, "selftest", 1)
        st = cb.poll(g, lambda s: bool((s.netsync or {}).get("selftest")), 5.0, "the role again") or g.state
        lever = ate_get(st, "lever")
        _ns(g, "selftest", 0)
    except HarnessError as err:
        led.check("K-R", False, f"the re-read raised: {str(err)[:200]}")
        return
    line = cb.count(lines, LOG_RELEASE) > 0
    ok = lever is None and (line or not ctx.lever_held)
    led.check("K-R", ok, f"lever {lever!r} after the release; release line {'seen' if line else 'absent'} (a lever "
                         f"{'was' if ctx.lever_held else 'was not'} held into it)")
