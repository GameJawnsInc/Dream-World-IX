"""R3 #3 -- WAIT PARITY (memoria-patch s113), the solo bench, run unattended.

THE DEFECT (studies/battle-coop/R3-DESIGN.md 3.1.3; B4-B5 box 40). In Wait mode the host's gauges froze for as long as a
guest window was OPEN -- even at its command root, where a LOCAL window lets them run (the stock root test at the foot
of BattleHUD.IsNativeEnableAtb). The type-3 control frame's byte 1 said only "open".

THE FIX (s113). Byte 1 carries the guest window's DEPTH: 0 shut, 1 open (pre-R3 guests only), 2 at the command root or a
pick in flight, 3 below it (an Ability/Item list, the target window; any other value reads as 3). The host's Wait branch
freezes only below the root (`RemoteMenuDeep`); turn-based keeps the any-open freeze; staleness is unchanged. Levers:
`netsync bench waitparity 0` (the pre-stage host), `bench ctl auto|shut|legacy|root|deep` (the loopback / feed guest's
byte 1), `bench cfg atb wait|active|restore` (a process-local cfg.atb), `bench lapse <ms> reserve` (the transport's 2 s
re-serve of a silent sender's last frame, then silence).

THE BENCH. Field 30602 (LOCKT2), `netsync selftest 1`, `stateevery 1`.
  * HOST (leg A): a selftest OWN battle on scene 67 with `netsync guestslots 15` -- every party slot belongs to the
    loopback guest, so the host's own window never opens and only the loopback's control byte can freeze anything. The
    Wait mode is `bench cfg atb wait` (on an engine without it, the save's own cfg.atb -- the stock default is Wait).
    "Moving" = any living unit's published `atb` CHANGES between consecutive publishes (a fill, or an action's reset).
    "Flat" = no unit's gauge FILLS for the whole window: ProcessActiveTime and the declarable dequeue both wait on
    IsNativeEnableAtb, but an action dequeued BEFORE the freeze plays out through it and its FinishCommand reset lands
    regardless (btl_cmd.FinishCommand -> ResetCurrentBattlerActiveTime, ungated -- stock Wait never stops an action in
    flight). So a flat window lets through exactly that reset -- a drop from a FULL gauge (atb >= atb_max) to below it
    (6568 -> 8 under IsKeepRestTimeInBattle) -- and counts every other change; and it must open with at least one
    FILLABLE unit (living, atb < atb_max), else nothing could move and "flat" could not fail. (Run 20261014-083020: the
    A3 brief root admitted the Goblin's long-queued Knife; its reset landed 2.68 s into the legacy window with every
    other gauge flat -- W-A3 read red on a freeze that held.) Each "moving" window stops at the first change, so the
    lone Goblin swings as little as possible at an uncommanded party. At the end `guestslots 0` hands the party back
    and the battle is fought out.
  * GUEST (leg B): `dioboot 67 0` + the stage-8 bench feed (`bbench roster auto 0`, `start 0x01`, `mode refuse` -- review
    ctrl F10: under accept the commit drops the bit and reads 0), the stock window driven through its depths; read back
    at `netsync.battle.menu.feed.ctl_menu` (the EXACT frame Pump would send) and `netsync.battle.menu.ctl.src`.

WHAT IS PROVEN (design 6.3):
  W-P0/P1 the capability (`netsync.battle.host.wait`) -- CAUTION: `bench waitparity|ctl|cfg` are NEVER sent without it (an
          engine before s113 reads them as `bench 1`, the FIELD-GATE bench ON); `guestslots 15`; `bench cfg atb wait`.
  W-A1   a loopback guest slot Ready, its digit panel at the root: the gauges MOVE within 3 s; host.wait.menu 2, deep
         false; ONE "Wait parity: the guest's control frame carries its window depth" line.
  W-A2   `bench ctl deep`: menu 3, deep true, cfg.atb 1 (the Wait self-check), FLAT for >= 3 s.
  W-A3   `bench ctl legacy` (after a brief root, so the deep stretch's GuestWaitMs clock restarts): menu 1, deep true,
         legacy_seen, FLAT >= 3 s, ONE "control frame reads 1 -- a pre-R3 guest" line (old-guest compatibility).
  W-A4   `bench cfg atb active`: root AND deep both MOVE within 3 s (cfg.atb 0).
  W-A5a  (Wait, deep, flat 1 s) `bench lapse 3000`: MOVING within 0.5 s, host.wait.menu -1 -- ParseControl(null) clears
         the flag at once (review ctrl F4).
  W-A5b  (Wait, deep, flat 1 s) `bench lapse 3000 reserve`: FLAT for >= 1.7 s (the re-served deep frame), then MOVING by
         2.8 s (before the lapse's own end at 3.0 s); lapse.reserve true; the RESERVE line.
  W-B1   the guest's encode over a real walk: root -> the marker Ability list -> its target window -> back to the root ->
         Attack committed (a pick in flight under `mode refuse`) -> `bbench ready 0`: feed.ctl_menu 2, 3, 3, 2, 2, 0.
  W-B2   `bbench caps 0` (the digit panel serves wire 0) at its root: feed.ctl_menu 2, menu.ctl.src "root".
  W-R    `reset` with `bench waitparity 0` and `bench ctl deep` left pulled: "Wait parity back ON (released with the
         harness)", "bench ctl back to auto (released with the harness)", the cfg.atb override written back.
NOT PROVEN HERE (two-machine sitting A, boxes A8/A9): the laptop's real stock window driving a real host's gauges, the
feel, box 14's 4.5 s takeover on the real link.

[ff9mapkit netsync s143 re-key] THE LEADER GUARD changes this bench's PREMISE, never its claims: from s143 a guest bit that
lands on the host's leader (COOPPARTY seats Zidane -- the kit player's body -- at position 0) moves on, else DROPS, so
`guestslots 15` would leave Zidane's slot with the host and its window would open beside the loopback's. On an engine that
publishes `netsync.battle.host.guard` W-P1 therefore also pulls `bench leaderguard off` (the s143 calibration lever: the
pre-s143 positional rule, selftest role only) and wants host.guard.off true with every slot still the guest's
(host.guard.raw 15); W-R wants its release line "leader guard back ON (released with the harness)" and host.guard.off false
on the re-read with the role. An engine before s143 never gets the op (it would read `bench leaderguard` as `bench 1`).

PRECONDITION. A non-turn-based install ([Battle] Speed != 2; the desktop runs 5). Under Speed 2 the stock any-open freeze
holds at the root BY DESIGN (box A10), so W-A1 (and A4's root half) reads red there -- the run's notes print the Speed.

CALIBRATION -- a check that cannot fail is not a check.
  * THE DEPLOYED DLL AT WRITING (s110): `netsync.battle.host.wait` is absent, so `bench waitparity|ctl|cfg` and the
    4-argument lapse are NEVER sent. Leg A1 still runs on the save's own ATB mode -- the BEHAVIOURAL red: the loopback's
    root sends 1, RemoteMenuOpen freezes the Wait gauges (up to GuestWaitMs) and the window reads FLAT. Leg B still runs
    (the stage-8 feed is s107): no `ctl_menu`, and the s110 observable `feed.menu_open` reads true at the root and below it
    alike (noted). Expected RED: W-P0, W-P1 (atb never set), W-A1 (flat + no host.wait), W-A2, W-A3, W-A4, W-A5a, W-A5b
    (not reached), W-B1, W-B2 (no ctl_menu), W-R (the lever was never sent). GREEN there: W-S0 only. (s111/s112 alone
    answer exactly as s110 here.) A save in ACTIVE mode makes A1's gauges move on s110 too -- still red on its keys.
  * IN-RUN, on the new DLL: `COOP_CALIBRATE=1` pulls `bench waitparity 0` before the battle and releases it (`bench
    waitparity 1`) right after W-A1 -- so the episode's GuestWaitMs cap the lever falls back on cannot leak into the later
    legs. Predicted RED, exactly: W-A1 (the root freezes: flat, deep true). Every other check stays green.
  * W-CAL judges the set of the engine it FINDS (by probe -- design 6.1's calibrate-first run is on the DLL BEFORE the
    patch): no `netsync.battle.host.wait` -> the old-engine set above (every check but W-S0); s113 -> W-A1 alone.
  * W-R re-reads the lever WITH the role after `reset` (_coop_battle.reread_with_role): host.wait.parity_off reads false
    whenever the role is off (WaitParityOn is `BenchWaitParityOff && IsSelfTestRole`), so only a read with the role can
    see a stranded bench field.

    py tools/play.py studies/test-harness/scenarios/coop_battle_wait_parity.py --field 30602
    COOP_CALIBRATE=1 py tools/play.py studies/test-harness/scenarios/coop_battle_wait_parity.py --field 30602
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file

HarnessError = cb.HarnessError

P113 = cb.R3_PROBES[113]                 # netsync.battle.host.wait: the capability probe (HarnessAgent's header, protocol 5)
ALL_SLOTS = 0x0F                         # `guestslots 15`: every party slot is the loopback guest's
P143 = "netsync.battle.host.guard"       # [ff9mapkit netsync s143] the leader guard (its lever keeps ALL_SLOTS positional)
GUARD_REL = "leader guard back ON (released with the harness)"
CTL_SHUT, CTL_LEGACY, CTL_ROOT, CTL_DEEP = 0, 1, 2, 3
INTRO_S = 45.0
READY_S = 60.0                           # the first guest slot's ATB fill
SETTLE_S = 0.3                           # after a byte change: the next pump tick parses it (one frame late at most)
MOVE_S = 3.0                             # "moving within": the design's 2 s, plus an action's swing (a lone Goblin mid-attack
                                         # with every party slot Ready moves nothing until its reset) -- still disjoint from
FLAT_S = 3.0                             # ..."flat for >= 3 s"
PRE_FLAT_S = 1.0                         # W-A5a/b: the deep freeze holds before the lapse
LAPSE_MS = 3000
NULL_MOVE_S = 0.5                        # W-A5a: ParseControl(null) clears the flag on the next pump tick
RESERVE_FLAT_S, RESERVE_MOVE_S = 1.7, 2.8   # W-A5b: the 2000 ms re-serve (+-0.3 s), and moving before the lapse ends
FIGHT_S = 300.0

R3_LINE = "Wait parity: the guest's control frame carries its window depth"
LEGACY_LINE = "Wait parity: the guest's control frame reads 1 -- a pre-R3 guest"
RESERVE_LINE = f"bench lapse {LAPSE_MS} ms RESERVE -- the loopback host re-reads the guest's last control frame (deep)"
LEVER_OFF = "harness: Wait parity OFF -- CALIBRATION"
LEVER_REL = "Wait parity back ON (released with the harness)"
CTL_REL = "bench ctl back to auto (released with the harness)"
ATB_REL = "bench cfg atb back to "
RELEASED = "(released with the harness)"
WHY_CAPS = "host predates the command-phase gates"


def _catalog(calibrate: bool) -> dict:
    c = {
        "W-S0": "the harness forced the selftest role for this process (Memoria.ini untouched)",
        "W-P0": f"the engine publishes `{P113}` (memoria-patch s113) -- else `bench waitparity|ctl|cfg` are NEVER sent",
        "W-P1": ("`guestslots 15` + `bench cfg atb wait` -> host.guest_slots 15, host.cfg.atb 1; the lever PULLED for "
                 "calibration: `bench waitparity 0` -> host.wait.parity_off true + 'Wait parity OFF -- CALIBRATION'"
                 if calibrate else
                 "`guestslots 15` + `bench cfg atb wait` -> host.guest_slots 15, host.cfg.atb 1, host.wait.parity_off false"),
        "W-A1": f"A1 (a loopback guest slot Ready, its digit panel at the root): the gauges MOVE within {MOVE_S:.0f} s; "
                "host.wait.menu 2, deep false; ONE 'Wait parity: the guest's control frame carries its window depth' line",
        "W-A2": f"A2 (`bench ctl deep`): host.wait.menu 3, deep true, host.cfg.atb 1, the gauges FLAT for >= {FLAT_S:.0f} s",
        "W-A3": f"A3 (`bench ctl legacy`): menu 1, deep true, legacy_seen true, FLAT for >= {FLAT_S:.0f} s, ONE 'control "
                "frame reads 1 -- a pre-R3 guest' line",
        "W-A4": f"A4 (`bench cfg atb active`, cfg.atb 0): `bench ctl root` and `bench ctl deep` BOTH move within "
                f"{MOVE_S:.0f} s",
        "W-A5a": f"A5a (Wait, deep, flat {PRE_FLAT_S:.0f} s first): `bench lapse {LAPSE_MS}` -> MOVING within "
                 f"{NULL_MOVE_S} s with host.wait.menu -1 (ParseControl(null) clears the flag)",
        "W-A5b": f"A5b (Wait, deep, flat {PRE_FLAT_S:.0f} s first): `bench lapse {LAPSE_MS} reserve` -> FLAT for >= "
                 f"{RESERVE_FLAT_S} s (the re-served frame), then MOVING by {RESERVE_MOVE_S} s; handback.lapse.reserve "
                 "true; the RESERVE line",
        "W-B1": "B1 (guest, `bbench mode refuse`): feed.ctl_menu reads 2 at the root, 3 in the Ability list, 3 in its target "
                "window, 2 back at the root, 2 with the Attack pick in flight, 0 after `bbench ready 0`",
        "W-B2": "B2 (`bbench caps 0`: the digit panel serves wire 0) at its root: feed.ctl_menu 2, menu.ctl.src 'root', "
                "assist_slot 0",
        "W-R": "`reset` with `bench waitparity 0` + `bench ctl deep` left pulled: 'Wait parity back ON (released with the "
               "harness)', 'bench ctl back to auto (released with the harness)', the cfg.atb override written back "
               "(host.cfg.atb = the save's), the role released; then RE-READ WITH THE ROLE (`netsync selftest 1`, which "
               "releases nothing -- parity_off reads false while the role is off): parity_off false, cfg.atb the save's",
    }
    if calibrate:
        c["W-CAL"] = ("CALIBRATION: exactly the predicted reds of the engine FOUND -- without s113 every check but W-S0; "
                      "on s113 (`bench waitparity 0` through W-A1 only) W-A1")
    return c


#: COOP_CALIBRATE=1 on the s113 DLL: the lever's red (`bench waitparity 0` through W-A1 only).
LEVER_PREDICTED = ("W-A1",)
#: ...on an engine without s113 (the deployed s110 at writing, or s111/s112): every check but W-S0 (the module note).
OLD_PREDICTED = tuple(c for c in _catalog(True) if c not in ("W-S0", "W-CAL"))
A_LEGS = ("W-A2", "W-A3", "W-A4", "W-A5a", "W-A5b")


# ------------------------------------------------------------------------------------------- reads
def _w(x) -> dict:
    v = cb.host(x).get("wait")
    return v if isinstance(v, dict) else {}


def _cfg(x) -> dict:
    v = cb.host(x).get("cfg")
    return v if isinstance(v, dict) else {}


def _hb(x) -> dict:
    v = cb.host(x).get("handback")
    return v if isinstance(v, dict) else {}


def _feed(x) -> dict:
    v = cb.bmenu(x).get("feed")
    return v if isinstance(v, dict) else {}


def _ctl(x) -> dict:
    v = cb.bmenu(x).get("ctl")
    return v if isinstance(v, dict) else {}


def _gauges(x) -> dict:
    """{unit id: atb} for every living unit with a readable gauge."""
    out = {}
    for u in cb.units(x):
        a = u.get("atb")
        if u.get("alive", True) and isinstance(a, int) and not isinstance(a, bool) and a >= 0:
            out[int(u.get("id", -1))] = a
    return out


def _gauge_max(x) -> dict:
    """{unit id: atb_max} for every unit publishing a positive one."""
    out = {}
    for u in cb.units(x):
        m = u.get("atb_max")
        if isinstance(m, int) and not isinstance(m, bool) and m > 0:
            out[int(u.get("id", -1))] = m
    return out


def _foe_atb(x) -> list:
    return [u.get("atb") for u in cb.units(x, player=False)]


class _Mover:
    """A `watch` predicate: true from the first publish whose gauges differ from the previous publish's.

    ``excuse_resets`` (the FLAT windows): a drop from a FULL gauge (prev >= atb_max) to below it is an action's
    FinishCommand reset (btl_cmd.FinishCommand -> ResetCurrentBattlerActiveTime, applied to declarable main commands
    only, and NOT gated by IsNativeEnableAtb -- an action dequeued before a freeze plays out through it, as in stock
    Wait), so it is recorded in ``excused`` instead of counting. Every rise still counts, and so does any other drop.
    This keeps the window able to fail: a declarable command can only DEQUEUE on a tick whose IsNativeEnableAtb is
    true, and ProcessActiveTime reads the same gate in the same UpdateBattleFrame (HonoluluBattleMain: BattleMain,
    then YMenu_ManagerActiveTime), so any tick the freeze leaks fills every fillable unit -- a rise. ``fillable`` = the
    units below their max at the first publish; _flat refuses a window that has none (nothing there could fill)."""

    def __init__(self, excuse_resets: bool = False):
        self.prev = None
        self.prev_max = {}
        self.first = None
        self.n = 0
        self.excuse_resets = excuse_resets
        self.excused = []          # (unit id, atb before, atb after, the state) -- action resets let through
        self.fillable = None       # sorted unit ids below their max at the first publish

    def _counts(self, k: int, before: int, after: int) -> bool:
        if not self.excuse_resets:
            return True
        m = self.prev_max.get(k)
        return not (m is not None and before >= m and after < before)

    def __call__(self, s) -> bool:
        cur = _gauges(s)
        top = _gauge_max(s)
        self.n += 1
        if self.prev is None:
            self.fillable = sorted(k for k, a in cur.items() if k in top and a < top[k])
        elif self.first is None:
            for k in cur:
                if k not in self.prev or cur[k] == self.prev[k]:
                    continue
                if self._counts(k, self.prev[k], cur[k]):
                    self.first = s
                    break
                self.excused.append((k, self.prev[k], cur[k], s))
        self.prev, self.prev_max = cur, top
        return self.first is not None


def _moving(g, st0, seconds: float) -> tuple:
    """Every publish from ``st0`` until a gauge changes (or ``seconds`` run out). (the first changed state or None, its
    seconds after st0 or None, publishes read)."""
    mv = _Mover()
    if st0 is not None:
        mv(st0)
    samples, _ = cb.watch(g, mv, seconds)
    t = cb.elapsed(st0, mv.first) if (mv.first is not None and st0 is not None) else None
    return mv.first, t, mv.n


def _flat(g, seconds: float) -> tuple:
    """Every publish for ``seconds``. (flat, publishes read, seconds covered, the first change's seconds or None, a note
    naming the fillable units and any action reset let through). Flat = no counted change (an action's reset from a
    full gauge is excused -- _Mover) AND at least one fillable unit at the start (else the window could not fail)."""
    mv = _Mover(excuse_resets=True)
    samples = cb.hold_for(g, seconds, on_sample=mv)
    return _flat_verdict(mv, samples)


def _flat_verdict(mv: _Mover, samples: list) -> tuple:
    """_flat's verdict over a fed _Mover and its samples (split out so the predicate replays offline on a states ring)."""
    span = cb.elapsed(samples[0], samples[-1]) if len(samples) > 1 else 0.0
    t = cb.elapsed(samples[0], mv.first) if (mv.first is not None and samples) else None
    resets = ", ".join(f"unit {k} {a}->{b} @{cb.elapsed(samples[0], s):.2f} s" for k, a, b, s in mv.excused)
    note = (f"fillable {mv.fillable}" + (" (NONE: the window cannot fail)" if not mv.fillable else "")
            + (f"; action reset(s) let through: {resets}" if resets else ""))
    return mv.first is None and len(samples) >= 2 and bool(mv.fillable), len(samples), span, t, note


def _brief(x) -> str:
    return (f"host.wait={cb.pick(_w(x), 'parity_off', 'menu', 'open', 'deep', 'legacy_seen')} atb_mode={_cfg(x).get('atb')!r} "
            f"menu.ctl={cb.pick(_ctl(x), 'menu', 'src', 'hex')} ready_mask={cb.host(x).get('ready_mask')!r} "
            f"foe atb={_foe_atb(x)} turn.slot={x.turn_slot}")


# ------------------------------------------------------------------------------------------- acting
def _bench(g, *args) -> tuple:
    """`netsync bench <args>` -- ONLY when `netsync.battle.host.wait` is published: an engine before s113 reads `bench
    waitparity|ctl` as `bench 1` and turns the FIELD-GATE bench ON (never sent there). (ok, why)."""
    if not cb.has(g.state, P113):
        return False, f"never sent: the engine publishes no `{P113}` (it would read `bench {args[0]}` as `bench 1`)"
    return cb.try_ns(g, "bench", *args)


def _ctl_to(g, name: str, want: int) -> tuple:
    """`bench ctl <name>` and wait until the host has parsed byte ``want``. (ok, why, state)."""
    ok, why = _bench(g, "ctl", name)
    if not ok:
        return False, why, g.state
    st = cb.poll(g, lambda s: _w(s).get("menu") == want, 1.5, f"host.wait.menu {want}")
    if st is None:
        return False, f"`bench ctl {name}`: host.wait.menu never read {want} ({_brief(g.state)})", g.state
    cb.hold_for(g, SETTLE_S)
    return True, "", g.state


def _finish(g) -> None:
    """Hand the party back to the host (`guestslots 0`), fight the battle out and get back to the field."""
    cb.try_ns(g, "guestslots", 0)
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
    cb.poll(g, lambda s: s.on_field and s.ui_state == "FieldHUD" and cb.free(s), 30.0, "the field after the battle")
    g.wait_frames(20)


class _Ctx:
    p113 = False
    p143 = False             # [ff9mapkit netsync s143] the leader guard published: its lever was pulled at W-P1
    atb0 = None              # the save's cfg.atb before the bench override (the release must restore it)
    atb_set = False


# ------------------------------------------------------------------------------------------- the run
def run(g, field: int = cb.FIELD):
    calibrate = cb.CALIBRATE
    led = cb.Ledger(g, _catalog(calibrate), finals=("W-R", "W-CAL"))
    ctx = _Ctx()
    try:
        _run(g, led, ctx, field, calibrate)
    finally:
        g.note(f"Memoria.log archived: {cb.archive_log(g, 'wait-parity')}")
        led.close()
        try:
            if g.state.in_battle:
                _finish(g)
            if cb.dio(g.state).get("booted"):
                cb.leave(g, field)
        except HarnessError as err:
            g.note(f"could not get back to the field before the release: {str(err)[:160]}")
        _release(g, led, ctx)
        if calibrate:
            pred = LEVER_PREDICTED if ctx.p113 else OLD_PREDICTED
            g.note(f"W-CAL: s113 {'present' if ctx.p113 else 'ABSENT'} -- predicted reds {sorted(pred)}")
            led.judge_calibration("W-CAL", pred)
        led.close(final=True)


def _run(g, led: cb.Ledger, ctx: _Ctx, field: int, calibrate: bool) -> None:
    ok, why = cb.setup(g, field, label="R3 #3: Wait parity (s113), solo"
                                       + (" -- CALIBRATION (bench waitparity 0 through A1)" if calibrate else ""))
    led.check("W-S0", ok, why)
    st = g.state
    ctx.p113 = cb.has(st, P113)
    led.check("W-P0", ctx.p113, f"netsync.battle.host keys: {sorted(cb.host(st))}" if cb.has(st, "netsync.battle")
              else "no `netsync.battle`")
    absent = "ABSENT -- `bench waitparity|ctl|cfg` will NOT be sent"
    g.note(f"probe stage: {cb.stage_note(st)}; s113 {'present' if ctx.p113 else absent}; "
           f"[Netsync] GuestWaitMs={cb.ini_value(g, 'Netsync', 'GuestWaitMs')!r} [Battle] Speed="
           f"{cb.ini_value(g, 'Battle', 'Speed')!r} (read-only)")
    try:
        g.state_every(1)
    except (HarnessError, AttributeError) as err:
        g.note(f"stateevery 1 refused ({str(err)[:120]}) -- gauges read at the default cadence")
    _levers(g, led, ctx, calibrate)
    _leg_a(g, led, ctx, field, calibrate)
    _leg_b(g, led, ctx, field)


def _levers(g, led: cb.Ledger, ctx: _Ctx, calibrate: bool) -> None:
    ctx.atb0 = _cfg(g.state).get("atb")
    at = cb.mark(g)
    okg, whyg = cb.try_ns(g, "guestslots", ALL_SLOTS)
    oka, whya = _bench(g, "cfg", "atb", "wait")
    ctx.atb_set = oka
    okl, whyl = _bench(g, "waitparity", 0) if calibrate else (True, "")
    # [ff9mapkit netsync s143] the premise -- every slot the guest's -- is the positional rule: the guard's lever keeps it
    ctx.p143 = cb.has(g.state, P143)
    okp, whyp = cb.try_ns(g, "bench", "leaderguard", "off") if ctx.p143 else (True, "")
    st = cb.poll(g, lambda s: cb.host(s).get("guest_slots") == ALL_SLOTS and _cfg(s).get("atb") == 1
                 and (not ctx.p143 or (cb.host(s).get("guard") or {}).get("off") is True), 1.5,
                 "guest_slots 15 and cfg.atb 1 (and, from s143, the leader guard's lever)") or g.state
    lines = cb.new(g, at)
    off = _w(st).get("parity_off")
    gd = cb.host(st).get("guard") if isinstance(cb.host(st).get("guard"), dict) else {}
    good = okg and oka and cb.host(st).get("guest_slots") == ALL_SLOTS and _cfg(st).get("atb") == 1
    good = good and ((okl and off is True and cb.count(lines, LEVER_OFF) == 1) if calibrate else off is False)
    good = good and (not ctx.p143 or (okp and gd.get("off") is True and gd.get("raw") == ALL_SLOTS))
    led.check("W-P1", good, (whyg or whya or whyl or whyp) or f"guest_slots={cb.host(st).get('guest_slots')!r} "
                                                              f"cfg={_cfg(st)} (the save's atb {ctx.atb0!r}) wait={_w(st)}; "
                                                              f"s143 guard {'off=' + repr(gd.get('off')) if ctx.p143 else 'absent'}; "
                                                              f"{cb.grep(lines, 'bench cfg', 'Wait parity', 'GuestSlots')}")
    if not okg:
        led.unreached(("W-A1",) + A_LEGS, f"`guestslots 15` refused -- {whyg}")


# ------------------------------------------------------------------------------------------- leg A (host)
def _leg_a(g, led: cb.Ledger, ctx: _Ctx, field: int, calibrate: bool) -> None:
    if "W-A1" in led.done:
        return
    g.note("A: an own battle whose every slot is the loopback guest's -- the host's Wait gauges against the guest's byte 1")
    if cb.poll(g, lambda s: s.ui_state == "FieldHUD" and cb.free(s), 15.0, "a playable field") is None:
        led.unreached(("W-A1",) + A_LEGS, f"no playable field to start the battle from (ui {g.state.ui_state!r})")
        return
    at = cb.mark(g)
    try:
        g.start_battle(cb.SCENE)
    except HarnessError as err:
        led.unreached(("W-A1",) + A_LEGS, f"`battle {cb.SCENE}` did not start: {str(err)[:200]}")
        return
    if cb.poll(g, lambda s: s.commands_enabled, INTRO_S, "the command phase") is None:
        led.unreached(("W-A1",) + A_LEGS, "the battle never reached its command phase")
        _finish(g)
        return
    st = cb.poll(g, lambda s: cb.mask_bits(cb.host(s).get("ready_mask")) & ALL_SLOTS, READY_S, "a loopback guest slot Ready")
    if st is None:
        led.unreached(("W-A1",) + A_LEGS, f"no guest slot ever stood Ready within {READY_S:.0f}s ({_brief(g.state)})")
        _finish(g)
        return
    try:
        _a1(g, led, ctx, at)
        if calibrate:
            okl, whyl = _bench(g, "waitparity", 1)
            g.note(f"CALIBRATION: `bench waitparity 1` after A1 -> {'released' if okl else whyl}")
        if not ctx.p113:
            led.unreached(A_LEGS, f"the engine publishes no `{P113}` (s113): `bench ctl|cfg` and the reserve lapse were "
                                  "never sent")
            return
        _a2_a3(g, led, ctx, at)
        _a4(g, led, ctx)
        _a5(g, led, ctx)
    finally:
        _bench(g, "ctl", "auto")
        _finish(g)


def _a1(g, led: cb.Ledger, ctx: _Ctx, at: int) -> None:
    g.note("A1: the digit panel at its root -- Wait gauges run (s113) / freeze (the pre-stage host)")
    cb.hold_for(g, SETTLE_S)
    st0 = g.state
    hit, t, n = _moving(g, st0, MOVE_S)
    s = hit or g.state
    w = _w(s)
    lines = cb.new(g, at)
    led.check("W-A1", hit is not None and w.get("menu") == CTL_ROOT and w.get("deep") is False
              and cb.count(lines, R3_LINE) == 1,
              f"{'moved after ' + format(t, '.2f') + ' s' if hit is not None else 'FLAT for ' + str(MOVE_S) + ' s'} "
              f"({n} publishes); {_brief(s)}; {cb.grep(lines, 'Wait parity')}")


def _a2_a3(g, led: cb.Ledger, ctx: _Ctx, at: int) -> None:
    g.note("A2: `bench ctl deep` -- the Wait gauges freeze below the root")
    ok, why, st = _ctl_to(g, "deep", CTL_DEEP)
    if ok:
        flat, n, span, t, fnote = _flat(g, FLAT_S)
        s = g.state
        led.check("W-A2", flat and span >= FLAT_S - 0.2 and _w(s).get("menu") == CTL_DEEP and _w(s).get("deep") is True
                  and _cfg(s).get("atb") == 1,
                  f"flat={flat} over {span:.2f} s ({n} publishes; first change {t!r}; {fnote}); {_brief(s)}")
    else:
        led.check("W-A2", False, f"not reached: {why}")
    # The brief root RUNS the gauges by design, so it can also admit a queued declarable command (run 20261014-083020:
    # the Goblin's Knife, queued through all of A2) whose ~3 s action then ends INSIDE the legacy window -- its reset is
    # excused by _flat (a drop from a full gauge), never a fill.
    g.note("A3: a brief root (the deep stretch's GuestWaitMs clock restarts), then `bench ctl legacy` -- a pre-R3 guest")
    _ctl_to(g, "root", CTL_ROOT)
    at3 = cb.mark(g)
    ok, why, st = _ctl_to(g, "legacy", CTL_LEGACY)
    if ok:
        flat, n, span, t, fnote = _flat(g, FLAT_S)
        s = g.state
        lines = cb.new(g, at3)
        led.check("W-A3", flat and span >= FLAT_S - 0.2 and _w(s).get("menu") == CTL_LEGACY and _w(s).get("deep") is True
                  and _w(s).get("legacy_seen") is True and cb.count(cb.new(g, at), LEGACY_LINE) == 1,
                  f"flat={flat} over {span:.2f} s ({n} publishes; first change {t!r}; {fnote}); {_brief(s)}; "
                  f"{cb.grep(lines, 'Wait parity')}")
    else:
        led.check("W-A3", False, f"not reached: {why}")


def _a4(g, led: cb.Ledger, ctx: _Ctx) -> None:
    g.note("A4: Active mode -- neither the root nor a deep window freezes anything")
    ok, why = _bench(g, "cfg", "atb", "active")
    st = cb.poll(g, lambda s: _cfg(s).get("atb") == 0, 1.5, "cfg.atb 0") if ok else None
    res = []
    if st is not None:
        for name, byte in (("root", CTL_ROOT), ("deep", CTL_DEEP)):
            okc, whyc, s0 = _ctl_to(g, name, byte)
            hit, t, n = _moving(g, s0, MOVE_S) if okc else (None, None, 0)
            res.append((name, okc and hit is not None, whyc or (f"moved after {t:.2f} s" if hit is not None else
                                                              f"FLAT for {MOVE_S} s ({n} publishes)")))
    led.check("W-A4", st is not None and len(res) == 2 and all(r[1] for r in res),
              why or f"cfg.atb={_cfg(g.state).get('atb')!r}; {res}; {_brief(g.state)}")
    _bench(g, "cfg", "atb", "wait")
    cb.poll(g, lambda s: _cfg(s).get("atb") == 1, 1.5, "cfg.atb back to 1")


def _a5(g, led: cb.Ledger, ctx: _Ctx) -> None:
    g.note(f"A5a: deep, then `bench lapse {LAPSE_MS}` -- the null frame clears the freeze at once")
    ok, why, st = _ctl_to(g, "deep", CTL_DEEP)
    pre, n0, span0, _, pnote = _flat(g, PRE_FLAT_S) if ok else (False, 0, 0.0, None, "")
    if not (ok and pre):
        led.check("W-A5a", False, f"not reached: the deep freeze did not hold first ({why or 'flat=' + str(pre)}; "
                                  f"{pnote}; {_brief(g.state)})")
    else:
        try:
            ack = cb.ns_verb(g, "bench", "lapse", LAPSE_MS)
            lwhy = ""
        except HarnessError as err:
            ack, lwhy = None, str(err)[:300]
        hit, t, n = _moving(g, ack, NULL_MOVE_S + 0.5) if ack is not None else (None, None, 0)
        led.check("W-A5a", hit is not None and t is not None and t <= NULL_MOVE_S and _w(hit).get("menu") == -1,
                  lwhy or f"{'moved after ' + format(t, '.2f') + ' s' if hit is not None else 'flat'} ({n} publishes); "
                          f"at the change {_brief(hit or g.state)}")
    # the lapse runs out (a capture at 2.5 s and its hand-back at the root may come and go): back to the deep freeze
    cb.poll(g, lambda s: not cb.path(s, "netsync.battle.host.handback.lapse.active", False), (LAPSE_MS + 2000) / 1000.0,
            "the lapse to end")
    cb.poll(g, lambda s: _hb(s).get("held") in (-1, None) and _w(s).get("menu") == CTL_DEEP, 3.0,
            "the hand-back settled and the deep frames back")
    g.note(f"A5b: deep, then `bench lapse {LAPSE_MS} reserve` -- the re-served frame holds the freeze ~2 s, then silence")
    at = cb.mark(g)
    pre, n0, span0, _, pnote = _flat(g, PRE_FLAT_S)
    if not pre:
        led.check("W-A5b", False, f"not reached: the deep freeze did not hold first ({pnote}; {_brief(g.state)})")
        return
    try:
        ack = cb.ns_verb(g, "bench", "lapse", LAPSE_MS, "reserve")
        rwhy = ""
    except HarnessError as err:
        ack, rwhy = None, str(err)[:300]
    if ack is None:
        led.check("W-A5b", False, f"not reached: `bench lapse {LAPSE_MS} reserve` refused -- {rwhy}")
        return
    hit, t, n = _moving(g, ack, RESERVE_MOVE_S + 0.3)
    lines = cb.wait_log(g, at, RESERVE_LINE, 1.0)
    reserve = cb.path(ack, "netsync.battle.host.handback.lapse.reserve")
    led.check("W-A5b", hit is not None and t is not None and RESERVE_FLAT_S <= t <= RESERVE_MOVE_S and reserve is True
              and cb.count(lines, RESERVE_LINE) == 1,
              f"{'moved after ' + format(t, '.2f') + ' s' if hit is not None else 'flat throughout'} ({n} publishes; want "
              f"{RESERVE_FLAT_S}..{RESERVE_MOVE_S} s); lapse.reserve at the ack {reserve!r}; {cb.grep(lines, 'bench lapse')}")
    cb.poll(g, lambda s: not cb.path(s, "netsync.battle.host.handback.lapse.active", False), (LAPSE_MS + 2000) / 1000.0,
            "the reserve lapse to end")


# ------------------------------------------------------------------------------------------- leg B (guest)
def _expect(g, want: int, timeout: float = 1.5):
    """Wait (bounded) for feed.ctl_menu == ``want``; the state either way (the frame is built from the PREVIOUS frame's UI,
    so a depth change reaches it one frame late)."""
    return cb.poll(g, lambda s: _feed(s).get("ctl_menu") == want, timeout, f"feed.ctl_menu {want}") or g.state


def _marker(st) -> tuple:
    """(an Ability-type command menu the panel draws enabled, the row id to pick there or None): the bench roster's marker
    when it drew, else any enabled Ability1/Ability2 command."""
    br = cb.bmenu(st).get("bench_roster")
    br = br if isinstance(br, dict) else {}
    menu = br.get("marker_menu")
    row = cb.hud_cmd(st, menu) if isinstance(menu, int) else None
    if row is not None and row.get("state") == 2:
        return menu, br.get("marker_shown")
    for m in (cb.MENU_ABILITY1, cb.MENU_ABILITY2):
        r = cb.hud_cmd(st, m)
        if r is not None and r.get("state") == 2:
            return m, None
    return None, None


def _leg_b(g, led: cb.Ledger, ctx: _Ctx, field: int) -> None:
    g.note("B: the guest's encode -- a diorama + the bench feed, its stock window walked through its depths")
    booted, why = cb.boot(g)
    if not booted:
        led.unreached(("W-B1", "W-B2"), why)
        cb.back_to_field(g, field)
        return
    try:
        if cb.wait_steady(g) is None:
            led.unreached(("W-B1", "W-B2"), "the diorama never reached its command phase")
            return
        ok1, why1 = cb.try_ns(g, "bbench", "roster", "auto", 0)
        ok2, why2 = cb.try_ns(g, "bbench", "start", "0x01") if ok1 else (False, why1)
        ok3, why3 = cb.try_ns(g, "bbench", "mode", "refuse") if ok2 else (False, why2)
        if not (ok1 and ok2 and ok3):
            led.unreached(("W-B1", "W-B2"), f"the bench feed did not start -- {why1 or why2 or why3}")
            return
        _b1(g, led)
        _b2(g, led)
    finally:
        cb.try_ns(g, "bbench", "mode", "accept")
        left, lwhy = cb.leave(g, field)
        if not left:
            g.note(f"B: no clean return -- {lwhy}")
            cb.back_to_field(g, field)


def _b1(g, led: cb.Ledger) -> None:
    steps = []

    def rec(name: str, want: int, st) -> None:
        f, c = _feed(st), _ctl(st)
        steps.append((name, want, f.get("ctl_menu"), c.get("src"), f.get("menu_open")))

    def done(why: str = "") -> None:
        ok = not why and len(steps) == 6 and all(s[1] == s[2] for s in steps)
        led.check("W-B1", ok, (f"stopped: {why}; " if why else "") + "(step, want, ctl_menu, src, menu_open): "
                  + "; ".join(str(s) for s in steps))

    st0, why = None, ""
    try:
        st0 = cb.ns_verb(g, "bbench", "ready", "0x01")
    except HarnessError as err:
        why = str(err)[:200]
    if st0 is None or cb.poll(g, lambda s: s.turn_slot == 0 and cb.hud(s).get("panel") == "command", 2.0,
                               "slot 0's stock window at its root") is None:
        done(why or f"the stock window never opened at its root ({cb.hud_brief(g.state)})")
        return
    rec("root", CTL_ROOT, _expect(g, CTL_ROOT))
    menu, row_id = _marker(g.state)
    if menu is None:
        done(f"no enabled Ability-type command drawn ({cb.hud(g.state).get('commands')})")
        return
    ok, why, _ = cb.pick_command(g, menu, expect_panel="ability")
    if not ok:
        done(why)
        return
    rec("ability list", CTL_DEEP, _expect(g, CTL_DEEP))
    g.wait_frames(6)
    st = g.state
    if row_id is None or (cb.hud_row(st, row_id) or {}).get("state") != 2:
        row_id = next((r.get("id") for r in cb.hud(st).get("rows") or [] if r.get("state") == 2), None)
    ok, why = cb.pick_row(g, row_id, group=cb.ABILITY_GROUP) if row_id is not None else (False, "no enabled ability row")
    if ok:
        g.press("confirm", 4)
        ok = cb.wait_panel(g, "target", 3.0) is not None
        why = "" if ok else f"the ability pick opened no target window ({cb.hud_brief(g.state)})"
    if not ok:
        done(why)
        return
    rec("target window", CTL_DEEP, _expect(g, CTL_DEEP))
    if not cb.to_root(g):
        done(f"Cancel never reached the command root ({cb.hud_brief(g.state)})")
        return
    rec("back at the root", CTL_ROOT, _expect(g, CTL_ROOT))
    ok, why, _ = cb.pick_command(g, cb.MENU_ATTACK, expect_panel="target")
    if not ok:
        done(why)
        return
    g.press("confirm", 4)
    # under `mode refuse` the bench host leaves the Ready bit up: the pick is PENDING (window shut, the slot still Ready)
    cb.poll(g, lambda s: cb.bmenu(s).get("pending") is not None and s.turn_slot == -1, 1.5, "the pick in flight")
    rec("pick in flight", CTL_ROOT, _expect(g, CTL_ROOT, 0.5))
    ok, why = cb.try_ns(g, "bbench", "ready", "0")
    if not ok:
        done(why)
        return
    rec("ready 0", CTL_SHUT, _expect(g, CTL_SHUT))
    done()


def _b2(g, led: cb.Ledger) -> None:
    g.note("B2: a host without the caps bit -- the digit panel serves, at its root")
    ok, why = cb.try_ns(g, "bbench", "caps", 0)
    ok2, why2 = cb.try_ns(g, "bbench", "ready", "0x01") if ok else (False, why)
    st = cb.poll(g, lambda s: cb.bmenu(s).get("why") == WHY_CAPS and cb.bmenu(s).get("assist_slot") == 0, 2.0,
                 "the digit panel serving wire 0") if ok2 else None
    s = _expect(g, CTL_ROOT) if st is not None else g.state
    m = cb.bmenu(s)
    led.check("W-B2", st is not None and _feed(s).get("ctl_menu") == CTL_ROOT and _ctl(s).get("src") == "root"
              and m.get("assist_slot") == 0,
              (why or why2) or f"why={m.get('why')!r} assist_slot={m.get('assist_slot')!r} feed.ctl_menu="
                                f"{_feed(s).get('ctl_menu')!r} feed.menu_open={_feed(s).get('menu_open')!r} "
                                f"menu.ctl={cb.pick(_ctl(s), 'menu', 'src', 'hex')}")
    cb.try_ns(g, "bbench", "caps", 2)
    cb.try_ns(g, "bbench", "ready", "0")


# ------------------------------------------------------------------------------------------- the release
def _release(g, led: cb.Ledger, ctx: _Ctx) -> None:
    """The lever and a bench byte left PULLED on purpose (only on an engine that has them), then `reset`: both must come
    back, logged, and the cfg.atb override be written back."""
    ok1, why1 = _bench(g, "waitparity", 0)
    ok2, why2 = _bench(g, "ctl", "deep") if ok1 else (False, why1)
    at = cb.mark(g)
    cb.release(g)
    st = g.state
    lines = cb.new(g, at)
    missing = [n for n in (LEVER_REL, CTL_REL) + ((GUARD_REL,) if ctx.p143 else ()) if cb.count(lines, n) != 1]
    if ctx.atb_set and not any(ATB_REL in ln and RELEASED in ln for ln in lines):
        missing.append(ATB_REL + "... " + RELEASED)
    forced = (st.netsync or {}).get("forced")
    # host.wait.parity_off reads false whenever the role is off (WaitParityOn), and `reset` released the role: re-read it
    # WITH the role (re-forced, which releases nothing) -- the release lines and this re-read are the real check (R3H-3)
    rr, rwhy = cb.reread_with_role(g) if ok1 else (None, "")
    good = (ok1 and ok2 and not missing and rr is not None and _w(rr).get("parity_off") is False
            and (not ctx.atb_set or _cfg(rr).get("atb") == ctx.atb0) and forced is False
            and (not ctx.p143 or (cb.host(rr).get("guard") or {}).get("off") is False))   # [ff9mapkit netsync s143]
    led.check("W-R", good, (why1 or why2) or f"missing lines {missing}; forced after reset={forced!r}; re-read WITH the "
                                              f"role: " + (f"wait={_w(rr)} cfg.atb={_cfg(rr).get('atb')!r} (want "
                                                           f"{ctx.atb0!r})" if rr is not None else f"none ({rwhy})")
                                              + f"; {cb.grep(lines, RELEASED)}")
