"""B4/B5 STAGE 11 -- THE GUEST-SLOT HAND-BACK, BTL-1 (memoria-patch s110), the solo bench, run unattended.

THE GAP (studies/battle-coop/B4-B5-DESIGN.md 4.7, 6.2, section 7 stage 11, owner decision 4). A guest slot is
guest-owned only while the guest's control lane is fresh (the fail-safe law), so after a stall of MenuStaleMs (2.5 s)
the HOST's stock ready loop opens that slot's window LOCALLY -- and nothing ever gave it back: the returning guest's
window opened on a slot the host held, and every pick it sent was refused ("the HUD refused -- the host's local menu
owns this slot right now"). s110, host-only:
  G6  the unit the host's own window holds is NOT Ready on the wire (and a change of the held guest slot samples at
      once), so the guest's window stays closed instead of buzzing refusals;
  G3  once the guest's lane is live again the slot is handed BACK -- at the command ROOT only (SetIdle +
      SetPartySwapButtonActive(false)); mid-submenu the host finishes its own pick (deferred, logged once per hold).
Lever: `netsync bench handback 1|0`. The selftest STALL: `netsync bench lapse <ms>|hold|end` (the loopback guest sends
no control frame -- ParseControl(null), exactly Pump's call on a stale socket).

THE BENCH. A REAL selftest own battle (`battle 67`, one Goblin) with >= 2 members (COOPPARTY, 30604: +vivi +garnet
+steiner), `netsync guestslots 2` (slot 1 belongs to the loopback guest), `stateevery 1` (every frame window read on the
doc's own frame counter -- Time.frameCount, the same clock as `handback.last.frame` and `lapse.end_frame`). Before each
lapse the bench waits until slot 1 is Ready (in turn.ready, not done, peer.ready_mask bit 1) with the host's window NOT on
it -- committing any other slot the host's window opens with Defend. Battle 1: X, A, B, C; battle 2: C2, D (the hand-back
log budget is 8 lines per own battle).

CAUTION: THE PROBE COMES FIRST. An engine before s110 parses `bench lapse` / `bench handback` as `bench 1` (the stock `Arg`
fallback) and turns the FIELD-GATE bench ON. This scenario NEVER sends them unless `netsync.battle.host.handback` is
published; without it only the stand-in leg (X) runs.

WHAT IS PROVEN (S11-*):
  X   the stand-in leg both DLLs share: `guestslots 0` with slot 1 ready -> the host's window opens slot 1 and its
      host.ready_mask bit 1 reads 0 while held (G6); at the root `guestslots 2` -> turn.slot leaves 1 within 3 frames,
      and on s110 handback.returns +1 with the capture line "(a GuestSlots change)" then "handed BACK".
  A   capture + G6: `bench lapse hold` -> ~2.5 s later turn.slot 1, held 1, captures +1, owed false, the STALL line;
      every later publish while held host.ready_mask bit 1 == 0 and g6_mask bit 1 == 1; peer.ready_mask bit 1 == 0
      within 2 frames of the capture (the hold-edge sample).
  B   the root hand-back: `bench lapse end` -> returns +1, last {slot 1, why "handed back"}, last.frame - lapse.end_frame
      <= 3; turn.slot leaves 1 within 3 frames, slot 1 still ready (not done), held -1, the host's bit 1 back within 2
      frames; the "handed BACK ... sat at the command root" line.
  C   a submenu makes it wait: in the ability list `bench lapse end` -> for >= 30 frames turn.slot stays 1, returns
      flat, deferred +1 exactly once, owed true, last.why "deferred: the host's window is in a submenu (Battle.Ability)",
      one "hand-back WAITS" line; the host's own pick then commits (1 in turn.done, returns flat, "closed after N ms by
      itself").   C2 (battle 2): Cancel back to the root instead -> the hand-back fires within 3 frames.
  D   SAME-DLL CALIBRATION, the lever: `bench handback 0` -> captures still +1, but bit 1 stays 1 while held and g6_mask 0
      (G6 red), and after the lapse turn.slot stays 1 for >= 30 frames with owed true and returns flat (G3 red); `bench
      handback 1` -> the hand-back fires on the next tick.
  R   `reset` with the lever left OFF: "guest-slot hand-back (G6 + G3) back ON (released with the harness)", off false.
NOT PROVEN HERE (two-machine sitting 2, box 34): the real relay's stall timing (~2 s socket staleness + 2.5 s), the
guest-side window, the feel; the Pump reorder (ParseControl before the command drain) -- only two machines carry a pick
across a stall.

CALIBRATION -- a check that cannot fail is not a check.
  * THE DEPLOYED DLL AT WRITING (s105) -- and stage 10 (s109): `handback` is absent, so P0 is RED and every A-D check is
    RED "not reached" (bench lapse/handback NEVER sent); R RED (no lever line). The stand-in leg runs and goes RED where
    predicted: X1 (bit 1 stays 1 while the host holds slot 1), X2 (turn.slot stays 1 after `guestslots 2`; a
    `bcmd 01 01 00 00 00 00 10 00 00` then drops with "the HUD refused -- the host's local menu owns this slot right
    now" -- noted), X3 (no returns key, no lines). GREEN there: S0, P1 (`guestslots`, s100) and PRE (the party).
    Measured on the s100-s105 stand-in: S0, P1 and PRE green (3/21); X reads "not reached" there (the stand-in never
    queues the guest's slot 1 on turn.ready, so the shared precondition never holds). On the full s106-s110 stand-in:
    4/21 (+P0) for the same reason -- no hand-back leg is exercised offline; the live engine is the only proof.
  * IN-RUN, on the stage DLL: leg D is the lever's red, judged as its own checks (D1/D2 pass when the lever reverts
    exactly G6 and G3).

    py tools/play.py studies/test-harness/scenarios/coop_battle_handback.py --field 30602
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file

HarnessError = cb.HarnessError

GUEST = 1
GBIT = 1 << GUEST
READY_S = 90.0                           # slot 1's ATB fill (WAIT mode freezes the gauges while a window is open)
CAPTURE_S = 6.0                          # MenuStaleMs (2.5 s) + slack
INTRO_S = 40.0
HOLD_FRAMES = 30
FIGHT_S = 300.0
LAPSE_HOLD = "harness: bench lapse HOLD (until `bench lapse end`) -- the loopback guest sends no control frame (a guest STALL)"
LAPSE_ENDED = "harness: bench lapse ENDED ("
CAPTURE_STALL = "hand-back: the host's local window holds guest slot 1 -- the guest's control lane has been silent "
CAPTURE_G6 = "its Ready bit is withheld while the host holds it (G6)"
CAPTURE_GS = "(a GuestSlots change)"
HANDED = "hand-back: guest slot 1 handed BACK to the guest -- "
AT_ROOT = "sat at the command root (held "
WAITS = "hand-back: guest slot 1 is the guest's again, but the hand-back WAITS -- "
FINISHES = "the host finishes its own pick"
BY_ITSELF = "hand-back: the host's window on guest slot 1 closed after "
LEVER_OFF = "harness: guest-slot hand-back OFF -- CALIBRATION"
LEVER_REL = "guest-slot hand-back (G6 + G3) back ON (released with the harness)"
HUD_REFUSED = "the HUD refused -- the host's local menu owns this slot right now"
SUBMENU_WHY = "deferred: the host's window is in a submenu (Battle.Ability)"

CATALOG = {
    "S11-S0": "the harness forced the selftest role for this process (Memoria.ini untouched)",
    "S11-P0": "the engine publishes `netsync.battle.host.handback` (memoria-patch s110, stage 11) -- else `bench lapse` / "
              "`bench handback` are NEVER sent",
    "S11-P1": "`netsync guestslots 2` is accepted -- the loopback guest owns party slot 1",
    "S11-PRE": "precondition: the battle seats a member in slot 1 (COOPPARTY)",
    "S11-X1": "X (both DLLs): `guestslots 0` with slot 1 ready -> the host's window opens slot 1 (turn.slot 1) and "
              "host.ready_mask bit 1 reads 0 on every later publish while it holds it (G6)",
    "S11-X2": "X: at the root `guestslots 2` (the loopback lane fresh) -> turn.slot leaves 1 within 3 frames",
    "S11-X3": "X (s110): handback.returns +1, the capture line '... (a GuestSlots change)' then '... handed BACK ...'",
    "S11-A1": "A: `bench lapse hold` -> within ~2.5 s turn.slot 1, handback.held 1, captures +1, owed false; the 'bench "
              "lapse HOLD' line",
    "S11-A2": "A: 'hand-back: the host's local window holds guest slot 1 -- the guest's control lane has been silent N ms (a "
              "stall); its Ready bit is withheld while the host holds it (G6) ...' logged",
    "S11-A3": "A: every publish after the capture while held: host.ready_mask bit 1 == 0 and g6_mask bit 1 == 1; "
              "peer.ready_mask bit 1 == 0 within 2 frames of the capture",
    "S11-B1": "B: `bench lapse end` at the root -> returns +1, last.why 'handed back', last.slot 1, last.frame - "
              "lapse.end_frame <= 3; the 'bench lapse ENDED' line",
    "S11-B2": "B: turn.slot leaves 1 within 3 frames, slot 1 still in turn.ready and not done, held -1, host.ready_mask bit 1 "
              "back within 2 frames of the hand-back",
    "S11-B3": "B: 'hand-back: guest slot 1 handed BACK to the guest -- ... sat at the command root (held N ms) ... "
              "returns=K' logged",
    "S11-C1": "C: in the ability list `bench lapse end` -> for >= 30 frames turn.slot 1 and returns flat",
    "S11-C2": "C: ...deferred +1 exactly once, owed true, last.why 'deferred: the host's window is in a submenu "
              "(Battle.Ability)', ONE 'hand-back WAITS -- ... the host finishes its own pick' line",
    "S11-C3": "C: the host's own pick commits -- 1 in turn.done, turn.slot != 1, returns flat, '... closed after N ms by "
              "itself' logged",
    "S11-C4": "C2 (battle 2): Cancel back to the root instead -> the hand-back fires within 3 frames of the root (returns "
              "+1, last.why 'handed back')",
    "S11-D1": "D (`bench handback 0`, 'hand-back OFF -- CALIBRATION', off true): a lapse still counts the capture (+1) but "
              "host.ready_mask bit 1 stays 1 while held and g6_mask 0 -- G6 red",
    "S11-D2": "D: after `bench lapse end` turn.slot stays 1 for >= 30 frames with owed true and returns flat -- G3 red",
    "S11-D3": "D: `bench handback 1` -> the hand-back fires on the next tick (returns +1)",
    "S11-R": "`reset` with the lever left OFF: 'guest-slot hand-back (G6 + G3) back ON (released with the harness)', "
             "handback.off false",
}
STAGE_LEGS = [c for c in CATALOG if c[4:5] in ("A", "B", "C", "D")]


# ------------------------------------------------------------------------------------------- reads
def _hb(x) -> dict:
    v = cb.host(x).get("handback")
    return v if isinstance(v, dict) else {}


def _last(x) -> dict:
    v = _hb(x).get("last")
    return v if isinstance(v, dict) else {}


def _lapse(x) -> dict:
    v = _hb(x).get("lapse")
    return v if isinstance(v, dict) else {}


def _hbit(x) -> int:
    return cb.mask_bits(cb.host(x).get("ready_mask")) & GBIT


def _pbit(x) -> int:
    return cb.mask_bits(cb.peer(x).get("ready_mask")) & GBIT


def _g6(x) -> int:
    return cb.mask_bits(_hb(x).get("g6_mask")) & GBIT


def _brief(x) -> str:
    t, h = cb.turn(x), _hb(x)
    return (f"turn.slot={t.get('slot')!r} ready={t.get('ready')} done={t.get('done')} group={cb.hud(x).get('group')!r} "
            f"panel={cb.hud(x).get('panel')!r} host.ready={cb.host(x).get('ready_mask')!r} peer.ready="
            f"{cb.peer(x).get('ready_mask')!r} "
            f"handback={cb.pick(h, 'off', 'held', 'owed', 'g6_mask', 'captures', 'returns', 'deferred')}")


def _bench(g, *args) -> tuple:
    return cb.try_ns(g, "bench", *args)


def _bench_st(g, *args):
    try:
        return cb.ns_verb(g, "bench", *args), ""
    except HarnessError as err:
        return None, str(err)[:300]


def _prep(g, timeout: float = READY_S) -> tuple:
    """Slot 1 Ready (in turn.ready, not done, peer bit 1) with the host's window NOT on it -- any other slot the window
    opens is committed with Defend. (state or None, why)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = g.state
        if not st.in_battle:
            return None, f"the battle is over (result {st.battle_result_name})"
        t = cb.turn(st)
        if st.turn_slot >= 0 and st.turn_slot != GUEST:
            try:
                g.act("Defend", slot=st.turn_slot)
            except HarnessError as err:
                g.note(f"prep: Defend for slot {st.turn_slot} refused ({str(err)[:120]})")
                g.wait_frames(10)
            continue
        if (GUEST in (t.get("ready") or []) and GUEST not in (t.get("done") or []) and st.turn_slot != GUEST
                and _pbit(st)):
            return st, ""
        time.sleep(0.05)
    return None, f"slot 1 never stood ready with the window idle within {timeout:.0f}s ({_brief(g.state)})"


def _start(g, label: str) -> tuple:
    try:
        g.start_battle(cb.SCENE)
    except HarnessError as err:
        return None, f"`battle {cb.SCENE}` ({label}) did not start: {str(err)[:200]}"
    st = cb.poll(g, lambda s: s.commands_enabled, INTRO_S, f"{label}'s command phase")
    return st, ("" if st is not None else f"{label} never reached its command phase")


def _finish(g) -> None:
    """Fight the battle out and get back to the field (whatever leg ended where)."""
    try:
        if g.state.in_battle:
            g.fight(timeout=FIGHT_S, finish=False)
    except HarnessError as err:
        g.note(f"the battle did not finish cleanly: {str(err)[:160]}")
    for _ in range(40):
        st = g.state
        if not st.in_battle and st.ui_state not in ("BattleHUD", "BattleResult"):
            break
        g.press("confirm", 4)
        g.wait_frames(20)
    cb.poll(g, lambda s: s.on_field and s.ui_state == "FieldHUD", 30.0, "the field after the battle")


def _await_window(g, until, timeout: float) -> tuple:
    """Read every publish until ``until`` holds, committing (Defend) any OTHER slot the host's window opens meanwhile --
    the stock ready loop serves the queue in order, so a slot that filled during the wait would otherwise stand in front
    of slot 1. (samples, the state that ended it or None)."""
    out = []
    deadline = time.time() + timeout
    while time.time() < deadline:
        samples, hit = cb.watch(g, lambda s: until(s) or (s.turn_slot >= 0 and s.turn_slot != GUEST),
                                max(0.1, deadline - time.time()))
        out += samples
        if hit is None:
            return out, None
        if until(hit):
            return out, hit
        try:
            g.act("Defend", slot=hit.turn_slot)
        except HarnessError as err:
            g.note(f"Defend for slot {hit.turn_slot} refused ({str(err)[:120]})")
            g.wait_frames(10)
    return out, None


def _capture(g) -> tuple:
    """`bench lapse hold` and wait for the host's window to hold slot 1. (samples, the capture state or None)."""
    _bench(g, "lapse", "hold")
    return _await_window(g, lambda s: s.turn_slot == GUEST and _hb(s).get("held") == GUEST, CAPTURE_S)


def _ability_menu(g) -> tuple:
    """Slot 1's Ability-type command with an ENABLED ability (from `menus`), and that ability's id. (menu, abil) or
    (None, None)."""
    try:
        m = g.menus(GUEST)
    except HarnessError as err:
        g.note(f"menus {GUEST} refused: {str(err)[:120]}")
        return None, None
    for c in m.get("commands") or []:
        if int(c.get("type", -1)) != 1:
            continue
        ab = next((a for a in m.get("abilities") or [] if int(a.get("menu", -1)) == int(c.get("menu", -2)) and a.get("enabled")),
                  None)
        if ab is not None:
            return int(c["menu"]), int(ab["sub"])
    return None, None


# ------------------------------------------------------------------------------------------- the run
def run(g, field: int = cb.FIELD):
    led = cb.Ledger(g, CATALOG, finals=("S11-R",))
    probe = [False]
    try:
        _run(g, led, field, probe)
    finally:
        g.note(f"Memoria.log archived: {cb.archive_log(g, 'handback')}")
        led.close()
        _release(g, led, probe[0])
        led.close(final=True)


def _run(g, led: cb.Ledger, field: int, probe: list) -> None:
    ok, why = cb.setup(g, field, label="B4/B5 stage 11: the guest-slot hand-back (s110), solo")
    led.check("S11-S0", ok, why)
    st = g.state
    probe[0] = cb.has(st, cb.PROBES[11])
    led.check("S11-P0", probe[0], f"netsync.battle.host keys: {sorted(cb.host(st))}" if cb.has(st, "netsync.battle") else
              "no `netsync.battle`")
    g.note(f"probe stage: {cb.stage_note(st)}" + ("" if probe[0] else
           " -- `bench lapse` / `bench handback` will NOT be sent (a pre-s110 agent reads them as `bench 1`)"))
    ok, why = cb.try_ns(g, "guestslots", 2)
    led.check("S11-P1", ok, why or "accepted")
    if not ok:
        led.close(f"`netsync guestslots` refused -- {why}")
        return
    try:
        g.state_every(1)
    except (HarnessError, AttributeError) as err:
        g.note(f"stateevery 1 refused ({str(err)[:120]}) -- frame windows read at the default cadence")
    if not probe[0]:
        led.unreached(STAGE_LEGS, "`netsync.battle.host.handback` is absent: a pre-stage-11 engine (the probe fails closed; "
                                  "`bench lapse` / `bench handback` were never sent)")
    st, why = _start(g, "battle 1")
    if st is None:
        led.close(why)
        return
    slots = cb.player_slots(st)
    led.check("S11-PRE", GUEST in slots, f"party slots {slots}")
    if GUEST not in slots:
        led.close("no party member in slot 1 (S11-PRE)")
        _finish(g)
        return
    _leg_x(g, led, probe[0])
    if probe[0]:
        _leg_a(g, led)
        _leg_b(g, led)
        _leg_c(g, led)
    _finish(g)
    if not probe[0]:
        return
    st, why = _start(g, "battle 2")
    if st is None:
        led.unreached(("S11-C4", "S11-D1", "S11-D2", "S11-D3"), why)
        return
    _leg_c2(g, led)
    _leg_d(g, led)
    _finish(g)


# ------------------------------------------------------------------------------------------- legs
def _leg_x(g, led: cb.Ledger, have: bool) -> None:
    g.note("X: the stand-in leg (both DLLs) -- guestslots 0 hands slot 1 to the host's window, guestslots 2 asks it back")
    st, why = _prep(g)
    if st is None:
        led.unreached(("S11-X1", "S11-X2", "S11-X3"), why)
        return
    r0 = _hb(st).get("returns")
    at = cb.mark(g)
    ok, why = cb.try_ns(g, "guestslots", 0)
    samples, hit = _await_window(g, lambda s: s.turn_slot == GUEST, 6.0)
    if hit is None:
        led.unreached(("S11-X1", "S11-X2", "S11-X3"), why or f"the host's window never opened slot 1 ({_brief(g.state)})")
        cb.try_ns(g, "guestslots", 2)
        return
    held = cb.hold_for(g, 1.2)
    # with GuestSlots 0 the hold is no GUEST hold, so no edge sample: G6 reaches the wire at the next SampleMs (150 ms)
    # cadence sample -- the first 0.3 s after the open are grace, every later publish while held must read bit 1 clear
    later = [x for x in held if x.turn_slot == GUEST and cb.elapsed(hit, x) >= 0.3]
    lit = [cb.frame_of(x) for x in later if _hbit(x)]
    led.check("S11-X1", later and not lit, f"slot 1 held on {len(later)} publish(es) past the 0.3 s grace; host.ready_mask "
                                            f"bit 1 set on {lit[:5]} (G6 withholds it on s110; the pre-stage host keeps it)")
    if not cb.to_root(g):
        g.note(f"X: not at the command root before `guestslots 2` ({_brief(g.state)})")
    st0 = None
    try:
        st0 = cb.ns_verb(g, "guestslots", 2)
    except HarnessError as err:
        g.note(f"`guestslots 2` refused: {str(err)[:160]}")
    samples, off = cb.watch_from(g, st0, lambda s: s.turn_slot != GUEST, 1.0)
    f_first = cb.frame_of(samples[0]) if samples else -1
    f_off = cb.frame_of(off) if off is not None else None
    led.check("S11-X2", off is not None and f_off - f_first <= 3,
              f"turn.slot left 1 at frame {f_off!r} (first read after the verb {f_first}); {_brief(g.state)}")
    lines = cb.new(g, at)
    ic = next((i for i, ln in enumerate(lines) if "hand-back: the host's local window holds guest slot 1 -- " in ln
               and CAPTURE_GS in ln), None)
    ih = next((i for i, ln in enumerate(lines) if HANDED in ln), None)
    st = g.state
    led.check("S11-X3", have and isinstance(r0, int) and _hb(st).get("returns") == r0 + 1 and ic is not None and ih is not None
              and ic < ih, f"returns {r0!r}->{_hb(st).get('returns', 'ABSENT')!r}; lines {ic, ih}; "
                           f"{cb.grep(lines, 'hand-back')}")
    if off is None:
        # the RED path (a pre-stage host): the record the design asks for, then free the slot so the run can go on
        okc, whyc = cb.try_ns(g, "bcmd", *cb.cmd_hex(GUEST, cb.ACT_ATTACK, mask=0x10).split())
        g.wait_frames(20)
        lines = cb.new(g, at)
        g.note(f"X (red path): a bcmd for slot 1 -> {'sent' if okc else whyc}; 'the HUD refused' lines: "
               f"{cb.count(lines, HUD_REFUSED)}; {cb.grep(lines, 'peer command', limit=300)}")
        try:
            g.act("Defend", slot=GUEST)
        except HarnessError as err:
            g.note(f"X: Defend for the held slot 1 refused ({str(err)[:120]})")


def _leg_a(g, led: cb.Ledger) -> dict:
    g.note("A: a guest STALL -- the host's window captures slot 1 and G6 withholds its Ready bit")
    st, why = _prep(g)
    if st is None:
        led.unreached(("S11-A1", "S11-A2", "S11-A3", "S11-B1", "S11-B2", "S11-B3"), why)
        return {}
    c0 = _hb(st).get("captures")
    at = cb.mark(g)
    samples, cap = _capture(g)
    lines = cb.wait_log(g, at, CAPTURE_STALL, 1.0)
    s = cap or g.state
    led.check("S11-A1", cap is not None and isinstance(c0, int) and _hb(s).get("captures") == c0 + 1
              and _hb(s).get("owed") is False and cb.count(lines, LAPSE_HOLD) == 1,
              f"{_brief(s)}; {cb.grep(lines, 'bench lapse')}")
    led.check("S11-A2", any(CAPTURE_STALL in ln and "ms (a stall)" in ln and CAPTURE_G6 in ln for ln in lines),
              cb.grep(lines, "hand-back"))
    if cap is None:
        led.check("S11-A3", False, "not reached: no capture")
        return {}
    fc = cb.frame_of(cap)
    held = cb.hold_for(g, 1.0)
    after = [x for x in held if _hb(x).get("held") == GUEST]
    bad = [(cb.frame_of(x), cb.host(x).get("ready_mask"), _hb(x).get("g6_mask")) for x in after if _hbit(x) or not _g6(x)]
    f_peer = cb.first_frame(samples + held, lambda x: _hb(x).get("held") == GUEST and not _pbit(x))
    led.check("S11-A3", after and not bad and f_peer is not None and f_peer - fc <= 2,
              f"capture at frame {fc}; while held (frame, host.ready_mask, g6_mask) off-G6: {bad[:4]}; peer bit 1 clear at "
              f"{f_peer!r}")
    return {"fc": fc}


def _leg_b(g, led: cb.Ledger) -> None:
    g.note("B: the stall ends at the command root -- the slot is handed back")
    st = g.state
    if _hb(st).get("held") != GUEST or st.turn_slot != GUEST:
        led.unreached(("S11-B1", "S11-B2", "S11-B3"), f"slot 1 is not held ({_brief(st)})")
        return
    cb.to_root(g)
    r0 = _hb(g.state).get("returns")
    at = cb.mark(g)
    st0, why = _bench_st(g, "lapse", "end")
    samples, done = cb.watch_from(g, st0, lambda s: _hb(s).get("returns") == (r0 or 0) + 1 and s.turn_slot != GUEST
                                  and _hbit(s), 2.0)
    s = done or g.state
    last, lapse = _last(s), _lapse(s)
    lines = cb.new(g, at)
    led.check("S11-B1", isinstance(r0, int) and _hb(s).get("returns") == r0 + 1 and last.get("why") == "handed back"
              and last.get("slot") == GUEST and isinstance(last.get("frame"), int) and isinstance(lapse.get("end_frame"), int)
              and 0 <= last["frame"] - lapse["end_frame"] <= 3 and cb.count(lines, LAPSE_ENDED) == 1,
              why or f"returns {r0!r}->{_hb(s).get('returns')!r} last={last} lapse={lapse}; {cb.grep(lines, 'bench lapse')}")
    f_first = cb.frame_of(samples[0]) if samples else -1
    f_hb = last.get("frame") if isinstance(last.get("frame"), int) else f_first
    f_off = cb.first_frame(samples, lambda x: x.turn_slot != GUEST)
    f_bit = cb.first_frame(samples, lambda x: _hbit(x))
    base = max(f_hb, f_first)
    t = cb.turn(s)
    led.check("S11-B2", f_off is not None and f_off - base <= 3 and GUEST in (t.get("ready") or [])
              and GUEST not in (t.get("done") or []) and _hb(s).get("held") == -1 and f_bit is not None and f_bit - base <= 2,
              f"hand-back frame {f_hb!r}, first read {f_first}; slot left at {f_off!r}, bit 1 back at {f_bit!r}; {_brief(s)}")
    led.check("S11-B3", any(HANDED in ln and AT_ROOT in ln and "returns=" in ln for ln in lines), cb.grep(lines, "hand-back"))


def _to_ability(g) -> tuple:
    menu, abil = _ability_menu(g)
    if menu is None:
        return False, "slot 1 has no Ability-type command with an enabled ability", None
    ok, why, _ = cb.pick_command(g, menu, expect_panel="ability")
    return ok, why, abil


def _leg_c(g, led: cb.Ledger) -> None:
    g.note("C: the stall ends mid-submenu -- the hand-back WAITS and the host finishes its pick")
    st, why = _prep(g)
    if st is None:
        led.unreached(("S11-C1", "S11-C2", "S11-C3"), why)
        return
    at = cb.mark(g)
    samples, cap = _capture(g)
    if cap is None:
        led.unreached(("S11-C1", "S11-C2", "S11-C3"), f"no capture ({_brief(g.state)})")
        _bench(g, "lapse", "end")
        return
    ok, why, abil = _to_ability(g)
    if not ok:
        led.unreached(("S11-C1", "S11-C2", "S11-C3"), f"the ability list never opened: {why}")
        _bench(g, "lapse", "end")
        return
    h = _hb(g.state)
    r0, d0 = h.get("returns"), h.get("deferred")
    at = cb.mark(g)
    st0, why = _bench_st(g, "lapse", "end")
    end_f = _lapse(st0 or g.state).get("end_frame")
    f0 = end_f if isinstance(end_f, int) else cb.frame_of(st0 or g.state)
    samples, _ = cb.watch_from(g, st0, lambda s: cb.frame_of(s) >= f0 + HOLD_FRAMES, 4.0)
    moved = [(cb.frame_of(x), x.turn_slot, _hb(x).get("returns")) for x in samples
             if x.turn_slot != GUEST or _hb(x).get("returns") != r0]
    span = (cb.frame_of(samples[-1]) - f0) if samples else 0
    led.check("S11-C1", samples and not moved and span >= HOLD_FRAMES,
              why or f"over {span} frames from the lapse end: off-hold (frame, turn.slot, returns) {moved[:4]}")
    s = g.state
    lines = cb.new(g, at)
    led.check("S11-C2", isinstance(d0, int) and _hb(s).get("deferred") == d0 + 1 and _hb(s).get("owed") is True
              and str(_last(s).get("why") or "").startswith(SUBMENU_WHY)
              and len([ln for ln in lines if WAITS in ln and FINISHES in ln]) == 1,
              f"deferred {d0!r}->{_hb(s).get('deferred')!r} owed={_hb(s).get('owed')!r} last={_last(s)}; {cb.grep(lines, 'WAITS')}")
    at = cb.mark(g)
    ok, why = cb.pick_row(g, abil, group=cb.ABILITY_GROUP)
    if ok:
        g.press("confirm", 4)
        ok = cb.wait_panel(g, "target", 3.0) is not None
        why = "" if ok else f"the pick opened no target panel ({_brief(g.state)})"
    if ok:
        g.press("confirm", 4)
    s = cb.poll(g, lambda x: GUEST in (cb.turn(x).get("done") or []) or not x.in_battle, 3.0, "the host's own pick") or g.state
    lines = cb.wait_log(g, at, BY_ITSELF, 1.0)
    led.check("S11-C3", ok and (GUEST in (cb.turn(s).get("done") or []) or not s.in_battle) and s.turn_slot != GUEST
              and _hb(s).get("returns") == r0 and any(BY_ITSELF in ln and "by itself" in ln for ln in lines),
              why or f"{_brief(s)}; {cb.grep(lines, 'hand-back')}")


def _leg_c2(g, led: cb.Ledger) -> None:
    g.note("C2: the stall ends mid-submenu, then Cancel back to the root -- the hand-back fires")
    st, why = _prep(g)
    if st is None:
        led.check("S11-C4", False, f"not reached: {why}")
        return
    at = cb.mark(g)
    samples, cap = _capture(g)
    ok, why, _ = _to_ability(g) if cap is not None else (False, f"no capture ({_brief(g.state)})", None)
    if not ok:
        led.check("S11-C4", False, f"not reached: {why}")
        _bench(g, "lapse", "end")
        return
    r0 = _hb(g.state).get("returns")
    _bench(g, "lapse", "end")
    deferred = cb.poll(g, lambda s: str(_last(s).get("why") or "").startswith("deferred"), 2.0, "the deferral")
    g.press("cancel", 4)
    samples, done = cb.watch(g, lambda s: _hb(s).get("returns") == (r0 or 0) + 1, 2.0)
    f_root = cb.first_frame(samples, lambda s: cb.cursor_group(s) == cb.CMD_GROUP or s.turn_slot != GUEST)
    last = _last(done or g.state)
    led.check("S11-C4", deferred is not None and done is not None and last.get("why") == "handed back"
              and isinstance(last.get("frame"), int) and f_root is not None and last["frame"] - f_root <= 3,
              f"deferred first: {deferred is not None}; returns {r0!r}->{_hb(g.state).get('returns')!r}; root seen at "
              f"{f_root!r}, hand-back at {last.get('frame')!r}; {_brief(g.state)}")


def _leg_d(g, led: cb.Ledger) -> None:
    g.note("D: the lever `bench handback 0` -- the pre-stage host (G6 and G3 red), then back on")
    at = cb.mark(g)
    ok, why = _bench(g, "handback", 0)
    st, pwhy = _prep(g) if ok else (None, why)
    if st is None:
        led.unreached(("S11-D1", "S11-D2", "S11-D3"), pwhy)
        _bench(g, "handback", 1)
        return
    c0, r0 = _hb(st).get("captures"), _hb(st).get("returns")
    samples, cap = _capture(g)
    held = cb.hold_for(g, 1.0) if cap is not None else []
    after = [x for x in held if _hb(x).get("held") == GUEST]
    g6 = [(cb.frame_of(x), cb.host(x).get("ready_mask"), _hb(x).get("g6_mask")) for x in after if not _hbit(x) or _g6(x)]
    lines = cb.new(g, at)
    led.check("S11-D1", ok and cap is not None and _hb(cap).get("off") is True and isinstance(c0, int)
              and _hb(cap).get("captures") == c0 + 1 and after and not g6 and cb.count(lines, LEVER_OFF) == 1,
              f"off={_hb(cap or g.state).get('off')!r} captures {c0!r}->{_hb(cap or g.state).get('captures')!r}; G6 acting "
              f"(frame, ready_mask, g6_mask) {g6[:4]}; {cb.grep(lines, 'hand-back OFF')}")
    if cap is None:
        led.unreached(("S11-D2", "S11-D3"), f"no capture under the lever ({_brief(g.state)})")
        _bench(g, "lapse", "end")
        _bench(g, "handback", 1)
        return
    cb.to_root(g)
    st0, why = _bench_st(g, "lapse", "end")
    end_f = _lapse(st0 or g.state).get("end_frame")
    f0 = end_f if isinstance(end_f, int) else cb.frame_of(st0 or g.state)
    samples, _ = cb.watch_from(g, st0, lambda s: cb.frame_of(s) >= f0 + HOLD_FRAMES, 4.0)
    moved = [(cb.frame_of(x), x.turn_slot, _hb(x).get("returns")) for x in samples
             if x.turn_slot != GUEST or _hb(x).get("returns") != r0]
    span = (cb.frame_of(samples[-1]) - f0) if samples else 0
    s = g.state
    led.check("S11-D2", samples and not moved and span >= HOLD_FRAMES and _hb(s).get("owed") is True,
              why or f"over {span} frames: off-hold {moved[:4]}; owed={_hb(s).get('owed')!r}")
    st0, why = _bench_st(g, "handback", 1)
    _, fired = cb.watch_from(g, st0, lambda s: _hb(s).get("returns") == (r0 or 0) + 1, 1.0)
    led.check("S11-D3", fired is not None and _last(fired).get("why") == "handed back" and _hb(fired).get("off") is False,
              why or f"returns {r0!r}->{_hb(g.state).get('returns')!r}; {_brief(g.state)}")


def _release(g, led: cb.Ledger, have: bool) -> None:
    """The lever left OFF on purpose (only on an engine that has it), then `reset`: it must come back ON, logged."""
    ok, why = _bench(g, "handback", 0) if have else (False, "no `netsync.battle.host.handback` (never sent)")
    at = cb.mark(g)
    cb.release(g)
    st = g.state
    lines = cb.new(g, at)
    led.check("S11-R", ok and cb.count(lines, LEVER_REL) == 1 and _hb(st).get("off") is False
              and (st.netsync or {}).get("forced") is False,
              why or f"handback.off={_hb(st).get('off')!r}; {cb.grep(lines, 'released with the harness')}")
