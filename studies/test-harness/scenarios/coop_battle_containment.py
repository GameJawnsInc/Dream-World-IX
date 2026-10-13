"""B4/B5 STAGE 2 -- THE GUEST CONTAINMENT BACKSTOP, R9 + G2 (memoria-patch s101), the solo bench, run unattended.

THE RISK (studies/battle-coop/B4-B5-DESIGN.md 3.3, 4.3, 3.8 item 1). The guest's battle DIORAMA runs the stock
CommandEngine ungated, so ANY local enqueue on a player re-simulates the host's fight on the guest's REAL bag. B4
lets the stock command menu open there (stage 3), so every commit site gets a capture -- and this stage is the
layer BEHIND them: R9 at the head of btl_cmd.SetCommand refuses a player's cmd[0]/cmd[3] inside a booted diorama
(one log line per boot per cmd_no, every refusal counted), and G2 makes IsGuestOwnedSlot false there (a host
concept; the selftest loopback was the one way it could read true inside a diorama).

THE BENCH. The coop_diorama_return.py bench: field 30602 (LOCKT2), scene 67 pattern 0, `netsync selftest 1`,
`netsync dioboot 67 0` / `dioleave`. `battlecmd <slot> 1 176 <mask> 0` goes through BattleHUD.SendNetCommand ->
btl_cmd.SetCommand, the path R9 must stop; `netsync bctl <hex>` is a raw type-3 control frame through the real
ParseControl (the input G2 overrides); `netsync containment 0` is the same-DLL calibration lever (the pre-stage guest).

WHAT IS PROVEN (outcomes: the unit's queue bits, the target's raw HP, the engine's counters and log lines):
  P      the capability (`netsync.battle.menu.r9_refused`), `cmd_busy` on every unit, and the selftest proof line
         carrying r9[scope=ok lever=ok gate=ok] (once per process -- the whole log is searched).
  G      POSITIVE CONTROL on the field (G2's reading CAN be non-zero): guestslots 1 + `bctl 00 00` -> guest_owned 1
         and the "lane is FRESH" line; a 1-byte frame -> "refused (lane not stamped)".
  A      R9 refuses: a `battlecmd` Attack inside the diorama ACKS (SendNetCommand returns true -- an ack proves
         nothing) yet for 4 s cmd_busy bits 0/3 stay clear and the target's hp_raw does not move; r9_refused 1,
         r9_total +1, r9_cmd 1, r9_site BattleHUD.SendNetCommand; exactly one R9 line; a second one counts (2) with
         still one line.
  B      G2: the same `bctl 00 00` inside the diorama reads guest_owned 0 ("(inside the diorama)").
  C      SAME-DLL CALIBRATION: `containment 0` -> guest_owned 1 again (G2 off) and the Attack really queues
         (cmd_busy bit 0 EVER set) and the swing plays (hp_raw drops), with no R9 count and no R9 line; `containment
         1` restores the lever silently.
  D      the teardown line carries the boot's receipt ('diorama torn down -- state restored, isDebug cleared;
         r9_refused=2'), and it stays readable after the return (contained false).
  E      per-boot reset: a second plain boot held 60 s with no verbs reads r9_refused 0, r9_total unchanged, and its
         teardown line r9_refused=0.
  R      `reset` with the lever deliberately left at 0: 'diorama containment (R9 + G2) back ON (released with the
         harness)', containment_off false, guest_owned 0, guest_slots back to the pin.
NOT PROVEN HERE (two-machine sitting 1 box 14): R9 at 0 on a real guest (grep every teardown line for r9_refused=0),
and the status-script lanes (a seat-carried Berserk/Confuse).

CALIBRATION.
  * PRE-STAGE DLL (s100): the probe fails closed (no `menu.r9_refused`, no `cmd_busy`, `containment`/`bctl` answer
    "netsync: unknown sub-verb", the selftest line has no `r9[`): P0-P2, G0, G1 RED. Leg A runs there as the
    behavioural red: the battlecmd queues and the swing plays -- A2 RED on the target's hp_raw (cmd_busy does not
    exist there), A3-A5 RED (no counters, no R9 line). B, C, E, D1/D2 and R are RED as well (no verbs, no keys,
    no receipt). GREEN there: S0 only.
  * The DEPLOYED DLL at writing (s99) answers like s100 minus `netsync.battle` entirely: the same red set.
  * Leg C repeats A's reds on the stage DLL itself without swapping DLLs.

    py tools/play.py studies/test-harness/scenarios/coop_battle_containment.py --field 30602
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file

HarnessError = cb.HarnessError

STALE_S = 2.5                            # NetSyncBattle.MenuStaleMs: a fresh control frame keeps a slot guest-owned this long
WATCH_S = 4.0                            # leg A: nothing executes in this window
SWING_S = 6.0                            # leg C: the local swing lands within this
HOLD_E_S = 60.0                          # leg E: a plain diorama held this long with no verbs
R9_LINE = re.compile(r"diorama R9: refused a local enqueue -- unit 0x01 \(.*\) cmd\[0\] cmd_no 1 \(Attack\) sub 176 "
                     r"-> 0x[0-9A-F]{2}, from BattleHUD\.SendNetCommand")
TORN = "diorama torn down -- state restored, isDebug cleared; r9_refused="

CATALOG = {
    "S2-S0": "the harness forced the selftest role for this process (Memoria.ini untouched)",
    "S2-P0": "the engine publishes `netsync.battle.menu.r9_refused` (memoria-patch s101, stage 2)",
    "S2-P1": "inside the diorama every battle.units[] entry carries `cmd_busy`",
    "S2-P2": "the selftest proof line 'diorama containment selftest: OK (' carries r9[scope=ok lever=ok gate=ok]",
    "S2-G0": "POSITIVE CONTROL (field): guestslots 1 + `bctl 00 00` -> menu.guest_owned == 1 within 2.5 s and "
             "'control frame [00 00] through ParseControl -> the lane is FRESH ... guest_owned=0x1'",
    "S2-G1": "a 1-byte control frame (`bctl 01`) logs 'refused (lane not stamped)'",
    "S2-A0": "the diorama comes up contained in its command phase (battle.active, battle.debug, menu.contained, "
             "turn.enabled)",
    "S2-A1": "at boot: r9_refused == 0 and r9_cmd == -1",
    "S2-A2": "`battlecmd 0 1 176 <mask> 0` (it ACKS) executes NOTHING: for 4 s units[0].cmd_busy & 0x9 == 0 and the "
             "target's hp_raw is unchanged",
    "S2-A3": "R9 counted it: r9_refused == 1, r9_total == T+1, r9_cmd == 1, r9_site starts 'BattleHUD.SendNetCommand'",
    "S2-A4": "exactly ONE 'diorama R9: refused a local enqueue -- unit 0x01 (...) cmd[0] cmd_no 1 (Attack) sub 176 -> "
             "0xNN, from BattleHUD.SendNetCommand' line",
    "S2-A5": "a second identical battlecmd: r9_refused == 2 and still exactly ONE R9 line (once per boot per cmd_no)",
    "S2-B1": "G2: guestslots 1 + `bctl 00 00` INSIDE the diorama -> guest_owned == 0 while contained; the line ends "
             "'guest_owned=0x0 (inside the diorama)'",
    "S2-C1": "CALIBRATION lever: `netsync containment 0` -> menu.containment_off true",
    "S2-C2": "...G2 off: `bctl 00 00` -> guest_owned == 1 within 2.5 s",
    "S2-C3": "...R9 off: the same battlecmd really queues AND RUNS locally (units[0].cmd_busy bit 0 set, then consumed "
             "by the diorama's own CommandEngine; hp_raw is mirrored, so it is not the witness)",
    "S2-C4": "...and R9 never saw it: r9_refused / r9_total unchanged, no new R9 line",
    "S2-C5": "`netsync containment 1` -> containment_off false, with no release line (the lever, not a release)",
    "S2-D1": "`dioleave`: 'diorama torn down -- state restored, isDebug cleared; r9_refused=N' with N this boot's count",
    "S2-D2": "after the return: menu.contained false and r9_refused still N (kept until the next boot)",
    "S2-E1": "a second plain boot held 60 s with no verbs: r9_refused == 0 and r9_total unchanged",
    "S2-E2": "...its teardown line reads r9_refused=0",
    "S2-R": "`reset` with the lever left at 0: 'diorama containment (R9 + G2) back ON (released with the harness)', "
            "containment_off false, guest_owned 0, guest_slots back to the pin",
}


def _u0(st) -> dict:
    return cb.unit(st, 0) or {}


def _busy(st) -> int | None:
    v = _u0(st).get("cmd_busy")
    return None if v is None else int(v)


def _hp(st, uid: int):
    u = next((x for x in cb.units(st) if int(x.get("id", -1)) == uid), None)
    return None if u is None else u.get("hp_raw")


def _r9_lines(lines) -> list:
    return [ln for ln in lines if R9_LINE.search(ln)]


def run(g, field: int = cb.FIELD):
    led = cb.Ledger(g, CATALOG, finals=("S2-R",))
    try:
        _run(g, led, field)
    finally:
        g.note(f"Memoria.log archived: {cb.archive_log(g, 'containment')}")
        led.close()
        try:
            if cb.dio(g.state).get("booted"):
                cb.leave(g, field)
        except HarnessError as err:
            g.note(f"could not leave the diorama before the release: {str(err)[:160]}")
        _release(g, led, field)
        led.close(final=True)


def _run(g, led: cb.Ledger, field: int) -> None:
    ok, why = cb.setup(g, field, label="B4/B5 stage 2: the guest containment backstop R9 + G2 (s101), solo")
    led.check("S2-S0", ok, why)
    st = g.state
    led.check("S2-P0", cb.has(st, "netsync.battle.menu.r9_refused"),
              f"netsync.battle.menu keys: {sorted(cb.bmenu(st))}" if cb.has(st, "netsync.battle") else
              "no `netsync.battle` at all (a pre-s100 engine)")
    proof = cb.poll(g, lambda s: cb.count(cb.log_lines(g), "diorama containment selftest:") >= 1, 8.0,
                    "the selftest proof block's diorama containment line")
    lines = [ln for ln in cb.log_lines(g) if "diorama containment selftest:" in ln]
    last = lines[-1] if lines else ""
    led.check("S2-P2", proof is not None and "selftest: OK (" in last and "r9[scope=ok lever=ok gate=ok]" in last,
              last[-300:] or "no proof line")
    _positive_control(g, led)
    _boot_legs(g, led, field)
    _leg_e(g, led, field)


def _positive_control(g, led: cb.Ledger) -> None:
    g.note("G: the positive control on the field -- G2's reading can be non-zero outside a diorama")
    ok, why = cb.try_ns(g, "guestslots", 1)
    at = cb.mark(g)
    ok2, why2 = cb.try_ns(g, "bctl", "00", "00") if ok else (False, why)
    st = cb.poll(g, lambda s: cb.bmenu(s).get("guest_owned") == 1, STALE_S, "guest_owned 1 on the field") if ok2 else None
    lines = cb.wait_log(g, at, "through ParseControl", 2.0)
    want = [ln for ln in lines if "control frame [00 00] through ParseControl -> the lane is FRESH" in ln
            and "guest_owned=0x1" in ln]
    led.check("S2-G0", ok and ok2 and st is not None and len(want) == 1,
              (why or why2) or f"guest_owned={cb.bmenu(g.state).get('guest_owned')!r}; {cb.grep(lines, 'ParseControl')}")
    at = cb.mark(g)
    ok3, why3 = cb.try_ns(g, "bctl", "01")
    lines = cb.wait_log(g, at, "through ParseControl", 2.0)
    led.check("S2-G1", ok3 and cb.count(lines, "refused (lane not stamped)") == 1,
              why3 or cb.grep(lines, "ParseControl"))


def _boot_legs(g, led: cb.Ledger, field: int) -> None:
    g.note("A-D: one diorama -- R9 refuses, G2 holds, the calibration lever, the teardown receipt")
    booted, why = cb.boot(g)
    if not booted:
        led.unreached([c for c in led.pending() if c[3] in "ABCD" or c == "S2-P1"], why)
        cb.back_to_field(g, field)
        return
    st = cb.poll(g, lambda s: cb.steady(s) and cb.bmenu(s).get("contained") is True, cb.STEADY_S,
                 "the diorama contained in its command phase")
    s = st or g.state
    led.check("S2-A0", st is not None,
              f"active={cb.battle(s).get('active')!r} debug={cb.battle(s).get('debug')!r} "
              f"contained={cb.bmenu(s).get('contained')!r} phase={cb.battle(s).get('phase')!r} "
              f"turn.enabled={cb.turn(s).get('enabled')!r}")
    us = cb.units(s)
    led.check("S2-P1", bool(us) and all("cmd_busy" in u for u in us),
              f"{len(us)} unit(s); without cmd_busy: {[u.get('slot') for u in us if 'cmd_busy' not in u]}")
    if st is None:
        st = cb.poll(g, cb.steady, cb.STEADY_S, "the diorama's command phase (uncontained engine)")
        if st is None:
            led.unreached([c for c in led.pending() if c[3] in "ABC"], "the diorama never reached its command phase")
            _leg_d(g, led, field, booted_count=None)
            return
    m = cb.bmenu(st)
    led.check("S2-A1", m.get("r9_refused") == 0 and m.get("r9_cmd") == -1,
              f"r9_refused={m.get('r9_refused')!r} r9_cmd={m.get('r9_cmd')!r}")
    t0 = m.get("r9_total")
    foe = cb.first_enemy(st)
    if foe is None or _u0(st) == {}:
        led.unreached([c for c in led.pending() if c[3] in "ABC"], f"no slot-0 player or no living enemy ({cb.units(st)})")
        _leg_d(g, led, field, booted_count=None)
        return
    uid = int(foe["id"])
    step = f"battlecmd 0 {cb.CMD_ATTACK} {cb.ATTACK_SUB} {uid} 0"
    hp0 = foe.get("hp_raw")
    at = cb.mark(g)
    ok, why = cb.try_send(g, step)
    samples = cb.hold_for(g, WATCH_S)
    busy = [(cb.raw(x).get("frame"), _busy(x)) for x in samples if (_busy(x) or 0) & 0x9]
    hps = sorted({_hp(x, uid) for x in samples}, key=str)
    has_busy = any(_busy(x) is not None for x in samples)
    led.check("S2-A2", ok and samples and not busy and hps == [hp0],
              why or f"{len(samples)} publish(es) over {WATCH_S:.0f}s; cmd_busy {'published' if has_busy else 'ABSENT'}; "
                     f"bits 0/3 set on {busy[:5]}; target 0x{uid:02X} hp_raw {hp0!r} -> {hps}")
    st = g.state
    m = cb.bmenu(st)
    site = m.get("r9_site") or ""
    led.check("S2-A3", m.get("r9_refused") == 1 and isinstance(t0, int) and m.get("r9_total") == t0 + 1
              and m.get("r9_cmd") == 1 and site.startswith("BattleHUD.SendNetCommand"),
              f"r9_refused={m.get('r9_refused')!r} r9_total {t0!r}->{m.get('r9_total')!r} r9_cmd={m.get('r9_cmd')!r} "
              f"r9_site={site!r}")
    lines = cb.new(g, at)
    led.check("S2-A4", len(_r9_lines(lines)) == 1, cb.grep(lines, "diorama R9") or "no R9 line")
    ok, why = cb.try_send(g, step)
    cb.hold_for(g, 1.0)
    st = g.state
    lines = cb.new(g, at)
    led.check("S2-A5", ok and cb.bmenu(st).get("r9_refused") == 2 and len(_r9_lines(lines)) == 1,
              why or f"r9_refused={cb.bmenu(st).get('r9_refused')!r}; R9 lines {len(_r9_lines(lines))}")

    # ---- B: G2 inside the diorama
    ok, why = cb.try_ns(g, "guestslots", 1)
    at = cb.mark(g)
    ok2, why2 = cb.try_ns(g, "bctl", "00", "00") if ok else (False, why)
    samples = cb.hold_for(g, 1.0)
    lines = cb.wait_log(g, at, "through ParseControl", 2.0)
    owned = sorted({cb.bmenu(x).get("guest_owned") for x in samples}, key=str)
    tail = [ln for ln in lines if "through ParseControl" in ln and ln.rstrip().endswith("guest_owned=0x0 (inside the diorama)")]
    led.check("S2-B1", ok and ok2 and owned == [0] and all(cb.bmenu(x).get("contained") is True for x in samples)
              and len(tail) == 1,
              (why or why2) or f"guest_owned over 1 s: {owned}; {cb.grep(lines, 'ParseControl')}")

    # ---- C: the same-DLL calibration (the reds)
    st = g.state
    r9, t9 = cb.bmenu(st).get("r9_refused"), cb.bmenu(st).get("r9_total")
    at = cb.mark(g)
    ok, why = cb.try_ns(g, "containment", 0)
    st = cb.poll(g, lambda s: cb.bmenu(s).get("containment_off") is True, 2.0, "containment_off true") if ok else None
    led.check("S2-C1", ok and st is not None, why or f"containment_off={cb.bmenu(g.state).get('containment_off')!r}")
    if not ok:
        led.unreached(("S2-C2", "S2-C3", "S2-C4", "S2-C5"), f"`netsync containment 0` refused -- {why}")
    else:
        okc, whyc = cb.try_ns(g, "bctl", "00", "00")
        st = cb.poll(g, lambda s: cb.bmenu(s).get("guest_owned") == 1, STALE_S, "guest_owned 1 with G2 off") if okc else None
        led.check("S2-C2", okc and st is not None, whyc or f"guest_owned={cb.bmenu(g.state).get('guest_owned')!r}")
        st = g.state
        foe = next((u for u in cb.units(st) if int(u.get("id", -1)) == uid), None)
        hp1 = None if foe is None else foe.get("hp_raw")
        okb, whyb = cb.try_send(g, step)
        # The proof the local enqueue RAN is the slot's own command queue: cmd[0] set (busy), then CONSUMED (busy falls
        # again) by the guest diorama's ungated CommandEngine. The target's hp_raw cannot witness it: the diorama's
        # units are reconciled to the (bench) host's numbers every sample, so a local hit is overwritten before any
        # publish -- the first draft required an HP drop and read red on a swing that had run.
        ever, cleared = [], []

        def _note(s):
            if (_busy(s) or 0) & 1:
                ever.append(1)
            elif ever:
                cleared.append(1)

        samples, hit = cb.watch(g, lambda s: bool(ever) and bool(cleared), SWING_S, on_sample=_note)
        led.check("S2-C3", okb and bool(ever) and bool(cleared),
                  whyb or f"cmd_busy bit 0 set: {bool(ever)}, then consumed: {bool(cleared)}; "
                          f"target hp_raw {hp1!r} -> {_hp(g.state, uid)!r} (mirrored -- not the witness)")
        st = g.state
        lines = cb.new(g, at)
        led.check("S2-C4", cb.bmenu(st).get("r9_refused") == r9 and cb.bmenu(st).get("r9_total") == t9
                  and not _r9_lines(lines) and cb.count(lines, "diorama R9") == 0,
                  f"r9_refused {r9!r}->{cb.bmenu(st).get('r9_refused')!r} r9_total {t9!r}->{cb.bmenu(st).get('r9_total')!r}; "
                  f"{cb.grep(lines, 'diorama R9')}")
        at = cb.mark(g)
        ok5, why5 = cb.try_ns(g, "containment", 1)
        st = cb.poll(g, lambda s: cb.bmenu(s).get("containment_off") is False, 2.0, "containment_off false")
        lines = cb.new(g, at)
        led.check("S2-C5", ok5 and st is not None and cb.count(lines, "released with the harness") == 0,
                  why5 or f"containment_off={cb.bmenu(g.state).get('containment_off')!r}; {cb.grep(lines, 'containment')}")
    _leg_d(g, led, field, booted_count=cb.bmenu(g.state).get("r9_refused"))


def _leg_d(g, led: cb.Ledger, field: int, *, booted_count) -> None:
    at = cb.mark(g)
    left, why = cb.leave(g, field)
    lines = cb.wait_log(g, at, TORN, 3.0)
    torn = [ln for ln in lines if TORN in ln]
    n = booted_count
    led.check("S2-D1", left and len(torn) == 1 and isinstance(n, int) and torn[0].rstrip().endswith(f"{TORN}{n}"),
              why or f"want r9_refused={n!r}; {cb.grep(lines, 'torn down', 'diorama RETURN')}")
    st = g.state
    led.check("S2-D2", left and cb.bmenu(st).get("contained") is False and cb.bmenu(st).get("r9_refused") == n,
              why or f"contained={cb.bmenu(st).get('contained')!r} r9_refused={cb.bmenu(st).get('r9_refused')!r} (want {n!r})")
    if not left:
        cb.back_to_field(g, field)


def _leg_e(g, led: cb.Ledger, field: int) -> None:
    g.note(f"E: a second plain diorama held {HOLD_E_S:.0f} s with no verbs (the per-boot reset)")
    t0 = cb.bmenu(g.state).get("r9_total")
    booted, why = cb.boot(g)
    if not booted:
        led.unreached(("S2-E1", "S2-E2"), why)
        cb.back_to_field(g, field)
        return
    cb.wait_steady(g)
    cb.hold_for(g, HOLD_E_S)
    st = g.state
    m = cb.bmenu(st)
    led.check("S2-E1", m.get("r9_refused") == 0 and isinstance(t0, int) and m.get("r9_total") == t0,
              f"r9_refused={m.get('r9_refused')!r} r9_total {t0!r}->{m.get('r9_total')!r}")
    at = cb.mark(g)
    left, why = cb.leave(g, field)
    lines = cb.wait_log(g, at, TORN, 3.0)
    torn = [ln for ln in lines if TORN in ln]
    led.check("S2-E2", left and len(torn) == 1 and torn[0].rstrip().endswith(TORN + "0"),
              why or cb.grep(lines, "torn down"))
    if not left:
        cb.back_to_field(g, field)


def _release(g, led: cb.Ledger, field: int) -> None:
    """Leave the lever pulled ON PURPOSE, then `reset`: the release must restore it and say so."""
    ok, why = cb.try_ns(g, "containment", 0)
    at = cb.mark(g)
    cb.release(g)
    st = g.state
    lines = cb.new(g, at)
    m, h = cb.bmenu(st), cb.host(st)
    led.check("S2-R", ok and cb.count(lines, "diorama containment (R9 + G2) back ON (released with the harness)") == 1
              and m.get("containment_off") is False and m.get("guest_owned") == 0 and h.get("guest_slots") == 0
              and (st.netsync or {}).get("forced") is False,
              why or f"containment_off={m.get('containment_off')!r} guest_owned={m.get('guest_owned')!r} "
                     f"guest_slots={h.get('guest_slots')!r}; {cb.grep(lines, 'released with the harness')}")
