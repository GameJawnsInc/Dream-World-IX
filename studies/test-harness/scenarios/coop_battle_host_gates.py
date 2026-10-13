"""B4/B5 STAGE 1 -- THE HOST COMMAND-PHASE GATES (memoria-patch s100), the solo bench, run unattended.

THE DEFECT (studies/battle-coop/B4-B5-DESIGN.md 3.1, 6.1). A co-op host advertised a unit as Ready from the HUD's
stale ReadyQueue/InputFinishList and took a type-2 command in any phase. A frame left over from the victory edge or
the previous battle drained into the next intro and FROZE it (the opening camera never hands over), or raced
KillNormalCommand at the victory edge; and the roster's 1 s cadence could delay the first turn.

THE FIX (s100). One predicate, HostCommandPhaseOpen = PHASE_NORMAL && FF9BMenu_IsEnable, gates the per-unit Ready bit,
the command intake (right after the length/version check, BEFORE the ownership check; one log line per battle per
reason) and the roster (with a forced rebuild on the opening edge). Type-1 header flags bit 1 advertises it.

THE BENCH. A REAL selftest own battle (`battle 67`, one Goblin) whose loopback guest owns party slot 1
(`netsync guestslots 2`); `netsync bcmd <hex>` puts a raw 9-byte v1 frame on the loopback, drained through the real
HandleCommandPayload inside an own battle. The party needs a member in SLOT 1: the New-Game party is Zidane alone,
so the scenario warps through COOPPARTY (30604, studies/battle-coop/bench/coopparty.field.toml) when it is
registered; without it the slot-1 legs are recorded FAILED "not reached" by the precondition check.

WHAT IS PROVEN (each an OUTCOME: published counters/masks and the engine's own log lines, never an ack):
  P0-P2  the capability (`netsync.battle`), the guestslots override, the lever at rest.
  A      battle A: the phase reads open at the opening (caps bit 1 both ends); slot 1 fills; from the victory edge
         (the first publish with phase != 4 or turn.enabled false, one publish of slack) bit 1 is clear on both
         ends through the result screen; a victory bcmd is refused for the phase with exactly one log line, and a
         second one counts without a second line.
  F1     on the field the frame PARKS (loop_cmds 1): the loopback drains only inside an own battle.
  B      battle B: the intro never shows A's stale queue (ready bit 1 clear, no roster, cmd_phase false); the
         parked frame is refused as "the battle intro"; turn.enabled RISES (no freeze); the roster opens with the
         phase (roster_lag 0..2, roster_slots [1] within 2 publishes); a malformed and an empty-mask frame are each
         dropped with their named reason; then a bcmd for ready slot 1 LANDS (cmd_queued +1, 'peer command: slot 1
         Attack -> mask 0xNN', 1 in turn.done).
  PZ     (COOP_PAUSE_LEG=1) a host pause closes the phase: cmd_phase false, ready_mask 0, a bcmd refused with 'the
         command menu is disabled ...'.
  R      `reset` releases the lever, the override (guest_slots back to the pin 0) and the role.
NOT PROVEN HERE (two-machine sitting 1): an OLD guest ignoring bit 1 against a new host; the real relay timing.

ATB MODE. Run with the save's ATB set to Active (Config). In WAIT mode the loopback guest's open digit menu
(RemoteMenuOpen) freezes the gauges up to GuestWaitMs = 30 s per uncommanded slot-1 turn -- slower, not wrong.

CALIBRATION -- a check that cannot fail is not a check.
  * On the PRE-STAGE DLL (s99, the one deployed at writing) only the probe can run, and it must fail closed: P0
    (no `netsync.battle`) and P1 ("netsync: unknown sub-verb 'guestslots'") are RED, and every A/F/B check is RED
    "not reached" with that refusal. GREEN there: S0 (the forced role) and R (reset). In all, 2 green, the rest red.
  * IN-RUN, on the stage DLL: `COOP_CALIBRATE=1` pulls `netsync hostgates 0` (the pre-stage host, selftest only)
    and runs the legs in the calibration-safe order: A -> B' (no parked frame: the leak, roster_lag and the landing
    measured) -> slot 1 left ready at B''s victory -> F1 (park) -> B'' (the parked frame: THE FREEZE, last -- a
    THROWAWAY sandbox: the frozen fight is left for the session teardown to quit). Predicted reds, exactly:
      A1 (no caps bit 1), A3 (bit 1 stays set past the victory edge), A4/A5/A6 (the victory bcmd is not refused --
      it is dropped instead: every enemy is dead, "no living target left to retarget to"), B1 (A's queue leaks
      into B''s intro), B2 (the parked frame is not refused), B3 (turn.enabled never rises: the freeze);
    and B4 MAY go either way (roster_lag follows the free-running RosterMs cadence: 0..2 in ~5-10% of openings --
    judge it over several runs, never one). CAL judges that set (the run itself is red by design).

DRIVER NOTE. Session.netsync refuses sub-verbs its NETSYNC_SUBVERBS lacks; until session.py learns s100's verbs
(guestslots, bcmd, hostgates) they go as raw steps (_coop_battle.ns_verb) -- the agent's own gates apply unchanged.

    py tools/play.py studies/test-harness/scenarios/coop_battle_host_gates.py --field 30602
    COOP_CALIBRATE=1 py tools/play.py studies/test-harness/scenarios/coop_battle_host_gates.py   (throwaway save)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file

HarnessError = cb.HarnessError

PAUSE_LEG = os.environ.get("COOP_PAUSE_LEG", "").strip() not in ("", "0")
GUEST = 1                                # the loopback guest's party slot
GUEST_MASK = 1 << GUEST
INTRO_S = 40.0                           # scene 67's opening camera is a few seconds; a freeze holds it for minutes
READY_S = 75.0                           # slot 1's ATB fill (WAIT mode stretches it: see the module note)
FIGHT_S = 300.0
REFUSED = "peer command for slot 1 (Attack) refused -- not in the command phase: "
PHASE_WHYS = ("the victory", "the battle is ending (menu off)", "the battle is closing", "the defeat",
              "the command menu is disabled")


def _catalog(calibrate: bool) -> dict:
    c = {
        "S1-S0": "the harness forced the selftest role for this process (Memoria.ini untouched)",
        "S1-P0": "the engine publishes `netsync.battle` (memoria-patch s100, stage 1)",
        "S1-P1": "`netsync guestslots 2` is accepted -- the loopback guest owns party slot 1",
        "S1-P2": ("the lever is PULLED for calibration: host.gates_off true + 'host command-phase gates OFF -- "
                  "CALIBRATION' logged; host.guest_slots == 2" if calibrate else
                  "the override took and the lever is at rest: host.guest_slots == 2, host.gates_off false"),
        "S1-PRE": "precondition: the sandbox party seats a member in slot 1 (COOPPARTY, or a richer party)",
        "S1-A1": "A: at the opening the phase reads open -- host.cmd_phase, host.caps & 2, peer.caps & 2 (through "
                 "the real ParseView), peer.live",
        "S1-A2": "A: slot 1 fills -- peer.ready_mask bit 1 rises while the local HUD never opens it (turn.slot != 1)",
        "S1-A3": "A: from the victory edge (phase != 4 or turn.enabled false; one publish of slack) bit 1 is clear in "
                 "peer.ready_mask AND host.ready_mask, through the result screen",
        "S1-A4": "A: a victory bcmd is refused for the phase -- loop_cmds back to 0, cmd_refused +1 exactly, "
                 "cmd_queued unchanged, refused_why names the phase",
        "S1-A5": "A: ...with exactly ONE 'peer command for slot 1 (Attack) refused -- not in the command phase: <why> "
                 "(phase N, menu off); cmd_refused=K, logged once per battle per reason' line",
        "S1-A6": "A: a second victory bcmd counts (cmd_refused +1) and logs no second line for the same reason",
        "S1-F1": "field: a bcmd PARKS -- loop_cmds == 1 and stays (the loopback drains only inside an own battle)",
        "S1-B1": "B: every publish of the intro (battle up, turn.enabled false) reads no ready bit 1, "
                 "roster_slots [] and cmd_phase false -- A's stale ReadyQueue does not leak",
        "S1-B2": "B: the parked frame drains in the intro and is REFUSED -- loop_cmds 0, cmd_refused +1, "
                 "'... not in the command phase: the battle intro (phase N, menu off)' logged",
        "S1-B3": "B: turn.enabled RISES within the intro's normal time -- no freeze",
        "S1-B4": "B: the roster opens with the phase -- host.roster_lag in 0..2 and menu.roster_slots == [1] within "
                 "2 publishes of turn.enabled",
        "S1-B6": "B: an 8-byte frame is dropped as malformed -- cmd_dropped +1 and 'peer command dropped (malformed "
                 "command frame: len 8, ver 1 (want 9 bytes, ver 1))'",
        "S1-B7": "B: an empty-mask frame is dropped -- cmd_dropped +1 and 'peer command dropped (slot 1 Attack: "
                 "empty target mask)'",
        "S1-B5": "B: a bcmd for READY slot 1 LANDS -- cmd_queued +1, 'peer command: slot 1 Attack -> mask 0xNN', "
                 "1 in turn.done",
        "S1-R": "RESET: `reset` releases the lever, the guestslots override (guest_slots back to the pin 0) and the "
                "role",
    }
    if PAUSE_LEG:
        c["S1-PZ"] = ("B: a host PAUSE closes the phase -- cmd_phase false, ready_mask 0, a bcmd refused with 'the "
                      "command menu is disabled ...'")
    if calibrate:
        c["S1-CAL"] = ("CALIBRATION (`hostgates 0`): the lever turned EXACTLY the predicted checks red (A1, A3, A4, "
                       "A5, A6, B1, B2, B3; B4 may go either way)")
    return c


PREDICTED = ("S1-A1", "S1-A3", "S1-A4", "S1-A5", "S1-A6", "S1-B1", "S1-B2", "S1-B3")
MAYBE = ("S1-B4",)
SLOT1_LEGS = ("S1-A2", "S1-A3", "S1-B1", "S1-B4", "S1-B5")


# ------------------------------------------------------------------------------------------- helpers
def _bits(x, side: str) -> int:
    d = cb.host(x) if side == "host" else cb.peer(x)
    return cb.mask_bits(d.get("ready_mask"))


def _bcmd(g, hexstr: str) -> tuple:
    return cb.try_ns(g, "bcmd", *hexstr.split())


def _drained(g, timeout: float = 3.0):
    return cb.poll(g, lambda s: cb.host(s).get("loop_cmds") == 0, timeout, "the loopback command lane to drain")


def _results(g, *, on_sample=None) -> tuple:
    """Confirm through the result screen like Session.leave_battle, but READING every publish between presses (the
    ring would overflow on a long screen). (presses, samples, ended ui)."""
    presses, samples = [], []
    for _ in range(40):
        st = g.state
        if not st.in_battle and st.ui_state not in ("BattleHUD", "BattleResult"):
            break
        presses.append({"frame": st.frame, "ui": st.ui_state})
        g.press("confirm", 4)
        samples += cb.hold_for(g, 0.35, on_sample=on_sample)
    st = cb.poll(g, lambda s: s.on_field and s.ui_state == "FieldHUD", 30.0, "the field after the result screen") \
        or g.state
    return presses, samples, st.ui_state


def _fight(g) -> tuple:
    """fight(finish=False) -> (result or None, why)."""
    try:
        return g.fight(timeout=FIGHT_S, finish=False), ""
    except HarnessError as err:
        return None, str(err)[:300]


def _wait_ready(g, timeout: float = READY_S):
    """Slot 1's Ready bit on the peer view; records whether the local HUD ever opened slot 1 meanwhile."""
    opened = []
    samples, st = cb.watch(g, lambda s: _bits(s, "peer") & GUEST_MASK,
                           timeout, on_sample=lambda s: opened.append(s.frame) if s.turn_slot == GUEST else None)
    return st, opened, samples


# ------------------------------------------------------------------------------------------- the run
def run(g, field: int = cb.FIELD):
    calibrate = cb.CALIBRATE
    led = cb.Ledger(g, _catalog(calibrate), finals=("S1-R", "S1-CAL"))
    try:
        _run(g, led, field, calibrate)
    finally:
        g.note(f"Memoria.log archived: {cb.archive_log(g, 'host-gates')}")
        led.close()                                        # every leg check is recorded before the judge reads them
        _release(g, led, calibrate)
        if calibrate:
            led.judge_calibration("S1-CAL", PREDICTED, MAYBE)
        led.close(final=True)


def _release(g, led: cb.Ledger, calibrate: bool) -> None:
    """`reset`: the role, the lever and the guestslots override all go (HarnessSelfTest(false) ->
    NetSyncBattle.HarnessReleaseBench). On an engine without `netsync.battle` only the role is judged."""
    at = cb.mark(g)
    cb.release(g)
    st = g.state
    ns = st.netsync or {}
    h = cb.host(st)
    lines = cb.new(g, at)
    stage = cb.has(st, "netsync.battle")
    lever = (not stage) or (h.get("guest_slots") == 0 and h.get("gates_off") is False)
    line = (not calibrate) or cb.count(lines, "host command-phase gates back ON (released with the harness)") == 1
    led.check("S1-R", ns.get("forced") is False and not cb.dio(st).get("booted") and lever and line,
              f"forced={ns.get('forced')!r} guest_slots={h.get('guest_slots')!r} gates_off={h.get('gates_off')!r}; "
              f"{cb.grep(lines, 'released with the harness', 'override released', 'GuestSlots')}")


def _run(g, led: cb.Ledger, field: int, calibrate: bool) -> None:
    ok, why = cb.setup(g, field, label="B4/B5 stage 1: the host command-phase gates (s100), solo"
                                       + (" -- CALIBRATION (hostgates 0)" if calibrate else ""))
    led.check("S1-S0", ok, why)
    st = g.state
    have = cb.has(st, "netsync.battle")
    led.check("S1-P0", have, "" if have else f"absent -- a pre-s100 engine (netsync keys: {sorted(st.netsync or {})[:30]})")
    ok, why = cb.try_ns(g, "guestslots", 2)
    led.check("S1-P1", ok, why or "accepted")
    if not ok:
        led.close(f"`netsync guestslots` refused -- {why}")
        return
    at = cb.mark(g)
    if calibrate:
        lok, lwhy = cb.try_ns(g, "hostgates", 0)
        lines = cb.wait_log(g, at, "host command-phase gates OFF -- CALIBRATION")
        st = cb.poll(g, lambda s: cb.host(s).get("gates_off") is True and cb.host(s).get("guest_slots") == 2, 1.5,
                     "the lever to read OFF") or g.state
        led.check("S1-P2", lok and cb.host(st).get("gates_off") is True and cb.host(st).get("guest_slots") == 2
                  and cb.count(lines, "host command-phase gates OFF -- CALIBRATION") == 1,
                  lwhy or f"gates_off={cb.host(st).get('gates_off')!r} guest_slots={cb.host(st).get('guest_slots')!r}; "
                          f"{cb.grep(lines, 'command-phase gates')}")
        if not lok:
            led.close(f"`netsync hostgates 0` refused -- {lwhy}")
            return
    else:
        st = cb.poll(g, lambda s: cb.host(s).get("guest_slots") == 2, 1.5, "host.guest_slots to read 2") or g.state
        h = cb.host(st)
        led.check("S1-P2", h.get("guest_slots") == 2 and h.get("gates_off") is False,
                  f"guest_slots={h.get('guest_slots')!r} gates_off={h.get('gates_off')!r}")

    slot1 = _battle_a(g, led, field, calibrate)
    if slot1 is None:
        return
    if calibrate:
        # B' (no parked frame) first, then the freeze leg LAST
        if not _battle_b(g, led, field, parked=False, slot1=slot1, calibrate=True):
            return
        _park(g, led)
        _freeze_leg(g, led)
    else:
        _park(g, led)
        _battle_b(g, led, field, parked=True, slot1=slot1, calibrate=False)


def _battle_a(g, led: cb.Ledger, field: int, calibrate: bool):
    """Battle A. Returns whether slot 1 is seated (None = the run cannot go on)."""
    g.note("A: slot 1 fills, is left uncommanded, and the party wins")
    try:
        g.start_battle(cb.SCENE)
    except HarnessError as err:
        led.close(f"`battle {cb.SCENE}` did not start: {str(err)[:200]}")
        return None
    st = cb.poll(g, lambda s: s.commands_enabled, INTRO_S, "battle A's command phase (turn.enabled)")
    if st is None:
        led.close("battle A never reached its command phase (turn.enabled)")
        return None
    slots = cb.player_slots(st)
    slot1 = GUEST in slots
    led.check("S1-PRE", slot1, f"party slots {slots}; " + ("" if slot1 else
              "the New-Game party is Zidane alone -- deploy COOPPARTY (30604) or run on a save whose party seats slot 1"))
    if not slot1:
        led.unreached(SLOT1_LEGS, "no party member in slot 1 (S1-PRE)")
    # A1: within two publishes of turn.enabled
    samples, st2 = cb.watch(g, lambda s: (cb.host(s).get("cmd_phase") is True and cb.mask_bits(cb.host(s).get("caps")) & 2
                                          and cb.mask_bits(cb.peer(s).get("caps")) & 2 and cb.peer(s).get("live") is True),
                            1.5)
    s = st2 or g.state
    led.check("S1-A1", st2 is not None,
              f"cmd_phase={cb.host(s).get('cmd_phase')!r} host.caps={cb.host(s).get('caps')!r} "
              f"peer.caps={cb.peer(s).get('caps')!r} live={cb.peer(s).get('live')!r} ({len(samples)} publish(es))")
    if slot1:
        st, opened, _ = _wait_ready(g)
        led.check("S1-A2", st is not None and not opened,
                  f"ready bit 1 {'rose' if st else 'never rose'} (peer.ready_mask={cb.peer(g.state).get('ready_mask')!r}); "
                  f"turn.slot read 1 on {len(opened)} publish(es)")
    st = g.state
    frame0, epoch = st.frame, st.battle_epoch
    result, why = _fight(g)
    if result is None:
        led.close(f"battle A did not reach a result: {why}")
        return None
    # A4-A6: the victory bcmds, while the battle is still up
    _victory_bcmds(g, led)
    ring = [cb.raw(x) for x in g.states_since(frame0)]     # the fight's last ~300 publishes + the bcmds' own reads
    presses, tail, ended = _results(g)
    if slot1:
        seq = ring + [cb.raw(x) for x in tail]
        # the edge: the first publish of THIS battle that is past its command phase
        edge = next((i for i, x in enumerate(seq)
                     if cb.battle(x).get("active") and cb.battle(x).get("epoch") == epoch
                     and (cb.battle(x).get("phase") != cb.PHASE_NORMAL or not cb.turn(x).get("enabled"))), None)
        if edge is None:
            led.check("S1-A3", False, f"no victory edge in {len(seq)} sample(s) (the ring kept the fight's last ~300)")
        else:
            after = seq[edge + 1:]                        # one publish of slack
            bad = [(cb.raw(x).get("frame"), cb.mask_bits(cb.peer(x).get("ready_mask")),
                    cb.mask_bits(cb.host(x).get("ready_mask"))) for x in after
                   if (cb.mask_bits(cb.peer(x).get("ready_mask")) | cb.mask_bits(cb.host(x).get("ready_mask"))) & GUEST_MASK]
            led.check("S1-A3", not bad and len(after) > 0,
                      f"edge at frame {cb.raw(seq[edge]).get('frame')} (phase {cb.battle(seq[edge]).get('phase')}); "
                      f"{len(after)} publish(es) after; with bit 1 (frame, peer, host): {bad[:6]}")
    g.note(f"A: {len(presses)} result-screen press(es), ended on {ended}")
    if ended != "FieldHUD":
        led.close(f"battle A did not return to the field (ui {ended})")
        return None
    return slot1


def _victory_bcmds(g, led: cb.Ledger) -> None:
    st = g.state
    h = cb.host(st)
    r0, q0, d0 = h.get("cmd_refused"), h.get("cmd_queued"), h.get("cmd_dropped")
    at = cb.mark(g)
    frame = cb.cmd_hex(GUEST, cb.ACT_ATTACK, mask=0x10)
    ok, why = _bcmd(g, frame)
    if not ok:
        led.unreached(("S1-A4", "S1-A5", "S1-A6"), f"`netsync bcmd` refused -- {why}")
        return
    st = _drained(g) or g.state
    h = cb.host(st)
    why1 = h.get("refused_why")
    lines = cb.wait_log(g, at, REFUSED, 2.0)
    refusals = [ln for ln in lines if REFUSED in ln]
    led.check("S1-A4", h.get("loop_cmds") == 0 and isinstance(r0, int) and h.get("cmd_refused") == r0 + 1
              and h.get("cmd_queued") == q0 and isinstance(why1, str) and why1.startswith(PHASE_WHYS),
              f"loop_cmds={h.get('loop_cmds')!r} cmd_refused {r0!r}->{h.get('cmd_refused')!r} cmd_queued "
              f"{q0!r}->{h.get('cmd_queued')!r} cmd_dropped {d0!r}->{h.get('cmd_dropped')!r} refused_why={why1!r} "
              f"dropped_why={h.get('dropped_why')!r} battle.phase={cb.battle(st).get('phase')!r}")
    tail = f"cmd_refused={(r0 or 0) + 1}, logged once per battle per reason"
    led.check("S1-A5", len(refusals) == 1 and "(phase " in refusals[0] and "menu off" in refusals[0]
              and tail in refusals[0] and (why1 or "~") in refusals[0],
              cb.grep(lines, "peer command") or "no peer-command line")
    at2 = cb.mark(g)
    ok, why = _bcmd(g, frame)
    st = _drained(g) or g.state
    h2 = cb.host(st)
    lines2 = cb.wait_log(g, at2, REFUSED, 1.0)
    n2 = cb.count(lines2, REFUSED)
    same = h2.get("refused_why") == why1
    led.check("S1-A6", ok and isinstance(r0, int) and h2.get("cmd_refused") == r0 + 2
              and n2 == (0 if same else 1),
              why or f"cmd_refused={h2.get('cmd_refused')!r} (want {None if r0 is None else r0 + 2}); refused_why "
                     f"{why1!r}->{h2.get('refused_why')!r}; new refusal lines {n2}")


def _park(g, led: cb.Ledger) -> None:
    g.note("F: a bcmd on the field parks on the loopback")
    n0 = cb.host(g.state).get("loop_cmds")
    ok, why = _bcmd(g, cb.cmd_hex(GUEST, cb.ACT_ATTACK, mask=0x10))
    if not ok:
        led.check("S1-F1", False, f"`netsync bcmd` refused -- {why}")
        return
    held = cb.hold_for(g, 1.2)
    vals = sorted({cb.host(x).get("loop_cmds") for x in held}, key=str)
    # exactly one more frame waits, and nothing drains it on the field (n0 > 0 only if an earlier leg's frame also
    # missed its battle -- that leg is red on its own)
    led.check("S1-F1", bool(held) and isinstance(n0, int) and vals == [n0 + 1],
              f"loop_cmds {n0!r} before; over 1.2 s after: {vals}")


def _battle_b(g, led: cb.Ledger, field: int, *, parked: bool, slot1: bool, calibrate: bool) -> bool:
    g.note("B: the intro, the opening, the declines and a landing" + (" (B', no parked frame)" if not parked else ""))
    st = g.state
    r0 = cb.host(st).get("cmd_refused")
    parked0 = cb.host(st).get("loop_cmds")                 # every frame waiting on the loopback drains into B's intro
    at = cb.mark(g)
    frame0 = st.frame
    try:
        g.start_battle(cb.SCENE)
    except HarnessError as err:
        led.close(f"`battle {cb.SCENE}` (B) did not start: {str(err)[:200]}")
        return False
    samples, opened = cb.watch(g, lambda s: s.commands_enabled, INTRO_S)
    # every battle publish since the field (frame0 was read there) up to the opening: B's intro, whatever its epoch read
    # (the scene can be up a few frames before InitBattle bumps battle_no -- exactly where a stale queue would show)
    intro = [x for x in [cb.raw(r) for r in g.states_since(frame0)] + [cb.raw(s) for s in samples]
             if cb.battle(x).get("active") and not cb.battle(x).get("debug") and not cb.turn(x).get("enabled")]
    if slot1:
        bad = [(x.get("frame"), cb.peer(x).get("ready_mask"), cb.bmenu(x).get("roster_slots"), cb.host(x).get("cmd_phase"))
               for x in intro if (cb.mask_bits(cb.peer(x).get("ready_mask")) & GUEST_MASK)
               or (cb.bmenu(x).get("roster_slots") or []) or cb.host(x).get("cmd_phase") is not False]
        led.check("S1-B1", intro and not bad,
                  f"{len(intro)} intro publish(es); violations (frame, peer.ready_mask, roster_slots, cmd_phase): {bad[:6]}")
    if parked:
        st2 = _drained(g, 2.0) or g.state
        lines = cb.new(g, at)
        intro_refusals = [ln for ln in lines if REFUSED + "the battle intro (phase " in ln and "menu off" in ln]
        # one line per battle per reason, however many parked frames the intro refuses
        led.check("S1-B2", cb.host(st2).get("loop_cmds") == 0 and isinstance(r0, int) and isinstance(parked0, int)
                  and parked0 >= 1 and cb.host(st2).get("cmd_refused") == r0 + parked0 and len(intro_refusals) == 1,
                  f"parked {parked0!r}; loop_cmds={cb.host(st2).get('loop_cmds')!r} cmd_refused {r0!r}->"
                  f"{cb.host(st2).get('cmd_refused')!r} cmd_queued={cb.host(st2).get('cmd_queued')!r}; "
                  f"{cb.grep(lines, 'peer command')}")
    if opened is None:
        if not calibrate:
            led.check("S1-B3", False, f"turn.enabled never rose within {INTRO_S:.0f}s (phase {g.state.battle_phase})")
        led.close("battle B never reached its command phase")
        return False
    if not calibrate:
        led.check("S1-B3", True, f"turn.enabled rose at frame {opened.frame}")
    if slot1:
        tail, st3 = cb.watch(g, lambda s: cb.bmenu(s).get("roster_slots") == [GUEST], 0.6)
        n = len(tail)
        lag = cb.host(st3 or g.state).get("roster_lag")
        led.check("S1-B4", st3 is not None and n <= 3 and isinstance(lag, int) and 0 <= lag <= 2,
                  f"roster_slots {cb.bmenu(st3 or g.state).get('roster_slots')!r} after {n} publish(es); "
                  f"roster_lag={lag!r}")
    _declines(g, led)
    if PAUSE_LEG:
        _pause_leg(g, led)
    if slot1:
        _land(g, led)
    if calibrate:
        # B''s victory must find slot 1 READY and uncommanded, or the freeze leg's parked frame cannot reproduce
        st, _, _ = _wait_ready(g)
        g.note(f"B': slot 1 {'re-ready' if st else 'NOT re-ready'} before the win (the freeze leg needs it stale)")
    result, why = _fight(g)
    if result is None:
        led.close(f"battle B did not reach a result: {why}")
        return False
    presses, _, ended = _results(g)
    if ended != "FieldHUD":
        led.close(f"battle B did not return to the field (ui {ended})")
        return False
    return True


def _declines(g, led: cb.Ledger) -> None:
    st = g.state
    d0 = cb.host(st).get("cmd_dropped")
    at = cb.mark(g)
    ok, why = _bcmd(g, cb.hexstr(cb.cmd_bytes(GUEST, cb.ACT_ATTACK, mask=0x10)[:8]))
    st = _drained(g) or g.state
    lines = cb.wait_log(g, at, "peer command dropped (malformed command frame", 2.0)
    want = "peer command dropped (malformed command frame: len 8, ver 1 (want 9 bytes, ver 1))"
    led.check("S1-B6", ok and isinstance(d0, int) and cb.host(st).get("cmd_dropped") == d0 + 1 and cb.count(lines, want) == 1,
              why or f"cmd_dropped {d0!r}->{cb.host(st).get('cmd_dropped')!r}; {cb.grep(lines, 'peer command')}")
    d1 = cb.host(st).get("cmd_dropped")
    at = cb.mark(g)
    ok, why = _bcmd(g, cb.cmd_hex(GUEST, cb.ACT_ATTACK, mask=0))
    st = _drained(g) or g.state
    want = "peer command dropped (slot 1 Attack: empty target mask)"
    lines = cb.wait_log(g, at, want, 2.0)
    led.check("S1-B7", ok and isinstance(d1, int) and cb.host(st).get("cmd_dropped") == d1 + 1 and cb.count(lines, want) == 1,
              why or f"cmd_dropped {d1!r}->{cb.host(st).get('cmd_dropped')!r}; {cb.grep(lines, 'peer command')}")


def _pause_leg(g, led: cb.Ledger) -> None:
    g.press("start", 4)
    st = cb.poll(g, lambda s: cb.host(s).get("cmd_phase") is False, 3.0, "the pause to close the command phase")
    r0 = cb.host(g.state).get("cmd_refused")
    ok, why = _bcmd(g, cb.cmd_hex(GUEST, cb.ACT_ATTACK, mask=0x10))
    st2 = _drained(g) or g.state
    h = cb.host(st2)
    led.check("S1-PZ", st is not None and ok and cb.mask_bits(h.get("ready_mask")) == 0
              and isinstance(r0, int) and h.get("cmd_refused") == r0 + 1
              and str(h.get("refused_why") or "").startswith("the command menu is disabled"),
              why or f"cmd_phase={cb.host(st2).get('cmd_phase')!r} ready_mask={h.get('ready_mask')!r} "
                     f"cmd_refused {r0!r}->{h.get('cmd_refused')!r} refused_why={h.get('refused_why')!r}")
    g.press("start", 4)
    cb.poll(g, lambda s: s.commands_enabled, 5.0, "the battle to resume after the pause")


def _land(g, led: cb.Ledger) -> None:
    st, _, _ = _wait_ready(g)
    if st is None:
        led.check("S1-B5", False, "slot 1 never became ready again in B")
        return
    foe = cb.first_enemy(st)
    if foe is None:
        led.check("S1-B5", False, "no living enemy to aim at")
        return
    mask = int(foe.get("id", 0x10))
    q0 = cb.host(st).get("cmd_queued")
    at = cb.mark(g)
    ok, why = _bcmd(g, cb.cmd_hex(GUEST, cb.ACT_ATTACK, mask=mask))
    samples, _ = cb.watch(g, lambda s: GUEST in (cb.turn(s).get("done") or []), 2.0)
    st2 = g.state
    want = f"peer command: slot 1 Attack -> mask 0x{mask:02X}"
    lines = cb.wait_log(g, at, want, 2.0)
    seen_done = any(GUEST in (cb.turn(s).get("done") or []) for s in samples)
    led.check("S1-B5", ok and isinstance(q0, int) and cb.host(st2).get("cmd_queued") == q0 + 1
              and cb.count(lines, want) == 1 and seen_done,
              why or f"cmd_queued {q0!r}->{cb.host(st2).get('cmd_queued')!r}; 1 in turn.done: {seen_done}; "
                     f"{cb.grep(lines, 'peer command')}")


def _freeze_leg(g, led: cb.Ledger) -> None:
    """CALIBRATION, LAST: the parked frame drains into an ungated intro and queues -- THE FREEZE."""
    g.note("B'': the parked frame meets an UNGATED intro (calibration; a throwaway sandbox)")
    st = g.state
    r0, q0 = cb.host(st).get("cmd_refused"), cb.host(st).get("cmd_queued")
    parked0 = cb.host(st).get("loop_cmds")
    at = cb.mark(g)
    try:
        g.start_battle(cb.SCENE)
    except HarnessError as err:
        led.close(f"`battle {cb.SCENE}` (B'') did not start: {str(err)[:200]}")
        return
    st2 = _drained(g, 4.0) or g.state
    lines = cb.new(g, at)
    led.check("S1-B2", cb.host(st2).get("loop_cmds") == 0 and isinstance(r0, int) and isinstance(parked0, int)
              and parked0 >= 1 and cb.host(st2).get("cmd_refused") == r0 + parked0
              and cb.count(lines, REFUSED + "the battle intro (phase ") == 1,
              f"cmd_refused {r0!r}->{cb.host(st2).get('cmd_refused')!r} cmd_queued {q0!r}->{cb.host(st2).get('cmd_queued')!r}; "
              f"{cb.grep(lines, 'peer command')}")
    st3 = cb.poll(g, lambda s: s.commands_enabled, INTRO_S, "B'''s command phase")
    led.check("S1-B3", st3 is not None,
              "turn.enabled rose" if st3 else f"turn.enabled never rose in {INTRO_S:.0f}s; phase {g.state.battle_phase} "
                                               f"-- THE FREEZE (the session teardown quits this game)")
