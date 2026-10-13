"""B4/B5 STAGE 8 -- THE PRODUCTION READY MIRROR + [Netsync] GuestStockMenu (memoria-patch s107), the solo bench
("coop_stock_menu part 3"), run unattended.

THE GAP (studies/battle-coop/B4-B5-DESIGN.md 4.6, 6.3, section 7 stage 8). Stages 3 and 7 proved the stock panels
compose, take input and draw the host's roster inside BattleMapDebug -- but only the selftest `bmenu open` opener ever
put a slot on the stock ReadyQueue; a real guest still commanded through the digit panel. s107's StockMenuTick maps
each host Ready bit (type-1 info bit 2, command-phase gated on a caps-bit-1 host) WIRE -> LOCAL by character id and
feeds the stock ReadyQueue; a forwarded commit goes PENDING until the bit falls (accepted), the nonce changes or the
unit dies (obsolete), or the bit stays up >= 2500 ms and >= 3 host samples (refused or lost: buzzer + reopen); an
unseated or feeder-refused slot is STRANDED to the digit panel (G7); `[Netsync] GuestStockMenu` (default 1) is the
live knob.

THE BENCH FEED (why it is needed). A selftest machine is NOT the host of its own diorama (`dioboot` runs gMode 1, so
SelfTestPump never samples it): `netsync bbench start <mask>` builds a type-1 frame every 150 ms (and at once on any
lever change) in SampleOwnBattle's v10 layout FROM THE DIORAMA'S OWN UNITS, runs it through the REAL ParseView into the
production `_peerView` / PeerBattleLive, then Pump's guest branch (the control frame recorded as `feed.menu_open`,
GuestAssistTick); a BENCH HOST decodes every forwarded frame with the host's own TryDecodeCommand (`mode accept` drops
that wire slot's Ready bit at once, `mode refuse` leaves it up). So a wire Ready bit travels: bytes -> ParseView ->
UnitView.Ready -> the mirror -> AddPlayerToReady(LocalIndexForWire(w)) -> the stock ready loop opens the panel.

THE RUN. `netsync selftest 1`, the party seeded through COOPPARTY (30604), field 30602, `dioboot 67 0`, the steady
command phase; `stateevery 1` so every "within N frames" claim is read on the doc's own frame counter (Time.frameCount;
the release restores 2). `bbench roster auto 0` (stage 7's two-marker roster -- it rides the feed's lane) and
`bbench start 0x01`.

WHAT IS PROVEN (S8-*):
  P   the capability (`menu.stock_owns`); the no-feed baseline (stock_owns false, why one of the two gates the feed
      satisfies -- "no live peer battle lane", what s107 answers once the diorama's party bench has armed the
      mirror, or "the party mirror is not active ..." -- feed null, mirror.serving false, turn.slot -1, peer.live
      false); the feed starts.
  A   opens on the wire bit: before `ready`, a live lane with caps 2 serving and nothing open; `bbench ready 0x01` ->
      within 3 frames of the bit turn.slot 0 / panel "command" / mirror.open 1 / fed +1, the digit panel idle
      (assist_slot -1) while the control frame reads open; both log lines; a PNG of the STOCK window (s8-A-stock-window).
  B   accept: Attack committed -> captured, sent +1, the bench host ACCEPTS (taken/accepted +1, the bit falls), the
      mirror counts accepted, nothing pending, the slot off both queues; shut 1 s later; the bit again reopens it.
  C   refuse: at ~1.5 s still pending (shut, refused unchanged); by ~3.5 s refused +1, reopened at the root, ONE line.
  D   the bit falls with the target panel open: within 3 frames shut (panel none, off ReadyQueue), closed +1, no capture.
  E   freeze: open 1 s more, then by ~2.5 s the lane is dead (peer.live / feed.live false, mirrored [], stock_owns false
      "no live peer battle lane", shut, the close-all line); thaw reopens.
  F   caps 0: "host predates the command-phase gates", shut, the digit panel serves wire 0 (assist_slot 0; PNG
      s8-F-digit-panel); caps 2 brings the stock window back.
  G   the right slot: a roster for slot 1 only (armed with wire 0's bit DOWN -- `ready 0` first -- so the once-per-boot
      wait line belongs to this leg) + the bit on wire 0 -> no_roster 1, shut, the digit panel NOT serving yet
      (the bounded wait); after >= 2.5 s STRANDED [0] and assist_slot 0 (the fixer's bound); the bit on wire 1 opens
      slot 1 (mirror.open 2).
  H   unmap: wire 1 unseated -> shut, stranded [1], assist_slot 1, closed +1, the STRANDED line; `unmap none` reopens.
  I   the knob: `bbench knob 0` -> "the knob is off ([Netsync] GuestStockMenu=0, the bench override)", shut, the digit
      panel serves wire 1; `knob ini` restores the ini's value (Memoria.ini is READ, never written).
  PZ  (fixer) pause, drop the bit, resume: the panel stays "none" and a Confirm throws nothing (no stale command group).
  Q   (fixer; needs stage 10's `endbench quit`) the guest's Quit prompt HOLDS the slot (mirror.open kept, its line),
      Cancel restores the window at the root; a drop under the prompt + Cancel closes cleanly, Confirm throws nothing.
      NEVER a Confirm while the prompt is up (its Yes quits the game).
  J   end coupling: `endbench victory` with a slot open -> shut from the injection on, why "waiting: the diorama is in
      phase ...", mirror.open 0, never reopened while the bit stays up.
  K   `dioleave`: "bench feed stopped (its diorama ended)", menu.feed null, peer.live false.
  R9 / INV / R   r9_refused 0 for the boot; the guest's save/party/bag fingerprint byte-identical; `reset` with the knob
      pulled clears it (its line).
NOT PROVEN HERE (two-machine sitting 1, boxes 1-14): a non-identity wire/local mapping, the live MirrorActive gate, the
socket drain, the relay's Ready-bit timing against the 2.5 s refusal window, how often G7 fires.

CALIBRATION -- a check that cannot fail is not a check.
  * THE DEPLOYED DLL AT WRITING (s105): `netsync bbench start` answers "netsync: unknown sub-verb 'bbench'" and
    `menu.stock_owns` is absent, so the probe fails closed: P0, P1, P2 and every A-K check RED ("not reached"), R RED.
    GREEN there: S0, R9 (no leg ran, nothing enqueued) and INV. Measured on the s100-s105 stand-in: S0 + R9 green (INV
    red there: the stand-in writes no autosave). On the full s106-s110 stand-in (a green-path smoke, not an oracle):
    18/40, every red the stand-in's own gap -- no [NetSync] log lines (P2 A4 B4 C3 D1 E2 F1 G1 G2 K1 R read theirs), no
    slot 1 seated in the diorama (G3 H I PZ Q J), no autosave (INV).
  * s106 (if deployed alone): `bbench roster auto 0` works but `bbench start` answers "netsync bbench: unknown op
    'start' (roster|content; stage 8 adds start|ready|caps|mode|unmap|stop)"; the same red set.
  * IN-RUN, on the stage DLL: `COOP_CALIBRATE=1` pulls `bbench knob 0` (exactly the pre-stage-8 guest) before leg A and
    runs only legs A-D: predicted RED A1-A5, B1-B5, C1-C3, D1 (after `ready 0x01` turn.slot stays -1 for >= 1 s,
    assist_slot 0 -- the digit panel serves -- mirror.fed does not move, nothing is captured); then `knob ini` and
    S8-CALA (leg A's opening) must PASS. S8-CAL judges that set.

    py tools/play.py studies/test-harness/scenarios/coop_stock_menu_live.py --field 30602
    COOP_CALIBRATE=1 py tools/play.py studies/test-harness/scenarios/coop_stock_menu_live.py --field 30602
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file

HarnessError = cb.HarnessError

OPEN_FRAMES = 3                          # a Ready bit -> the stock window, read on the doc's frame counter
CLOSE_FRAMES = 3
SERVING = "stock menu: the ready mirror is SERVING"
FED0 = "stock menu: wire slot 0 Ready -> local slot 0 is on the stock ReadyQueue"
TOOK = "bench feed: the bench host took a stock menu ["
ACCEPTED_LINE = "the forwarded command was ACCEPTED"
REFUSED_LINE = "REFUSED or lost -- buzzer, the slot reopens at the root"
CLOSED0 = "stock menu: local slot 0 (wire 0) closed"
CLOSED_STALE = "closed all (ready mirror: no live peer battle lane)"
PREDATES = "the ready mirror is not serving -- host predates the command-phase gates"
NO_ROSTER0 = "wire slot 0 is Ready but the menu roster does not carry it yet"
BOUND0 = "stock menu: wire slot 0 has been Ready "
UNMAP1 = "wire slot 1 is Ready but has no local seat in this diorama (the bench `unmap` lever) -- STRANDED"
QUIT_HOLD = "the guest's Quit prompt is up -- the ready mirror holds its slots"
FEED_STOP = "bench feed stopped (its diorama ended)"
STARTED = "harness: bench feed STARTED"
KNOB_REL = "the GuestStockMenu override cleared -- the ini's value rules again (released with the harness)"
WHY_NO_MIRROR = "the party mirror is not active"
WHY_STALE = "no live peer battle lane"
WHY_CAPS = "host predates the command-phase gates"
WHY_KNOB = "the knob is off ([Netsync] GuestStockMenu=0, the bench override)"
WHY_PHASE = "waiting: the diorama is in phase"

PREDICTED = ("S8-A1", "S8-A2", "S8-A3", "S8-A4", "S8-A5", "S8-B1", "S8-B2", "S8-B3", "S8-B4", "S8-B5", "S8-C1", "S8-C2",
             "S8-C3", "S8-D1")


def _catalog(calibrate: bool) -> dict:
    c = {
        "S8-S0": "the harness forced the selftest role for this process (Memoria.ini untouched)",
        "S8-P0": "the engine publishes `netsync.battle.menu.stock_owns` (memoria-patch s107, stage 8)",
        "S8-P1": "no feed: stock_owns false, why a gate the feed satisfies ('no live peer battle lane' or 'the party "
                 "mirror is not active ...'), feed null, mirror.serving false, turn.slot -1, peer.live false",
        "S8-P2": "`bbench roster auto 0` and `bbench start 0x01` are accepted; 'harness: bench feed STARTED' logged",
        "S8-A1": "A (before ready): peer.live, peer.caps 2, peer.ready_mask 0, stock_owns true, why null, mirror.serving "
                 "true, turn.slot -1, assist_slot -1, feed.menu_open false",
        "S8-A2": f"A: `bbench ready 0x01` -> within {OPEN_FRAMES} frames of the wire bit: turn.slot 0, 0 in turn.ready, "
                 f"hud.panel 'command'; peer.ready_mask 1, mirror.open 1, mirror.fed +1",
        "S8-A3": "A: the digit panel stays idle -- assist_slot -1 -- while the control frame reads open (feed.menu_open "
                 "true)",
        "S8-A4": "A: 'stock menu: the ready mirror is SERVING' logged once since the feed start (P2: it needs no Ready "
                 "bit) and 'wire slot 0 Ready -> local slot 0 is on the stock ReadyQueue' once since the bit",
        "S8-A5": "A: an in-engine PNG of the STOCK command window (turn.slot 0 when shot), decoded non-blank",
        "S8-B1": "B: Attack committed -> captured {slot 0, action 0, the target's mask} (its hex decodes to that in "
                 "Python), menu.sent +1",
        "S8-B2": "B: the bench host ACCEPTS -- feed.taken +1, feed.accepted +1, feed.ready 0, peer.ready_mask 0",
        "S8-B3": "B: mirror.accepted +1, pending null, turn.slot -1, slot 0 neither in turn.ready nor turn.done",
        "S8-B4": "B: 'bench feed: the bench host took a stock menu [<hex>] ... ACCEPTED' and '... the forwarded command was "
                 "ACCEPTED' logged",
        "S8-B5": "B: still shut 1 s later (turn.slot -1 throughout); `bbench ready 0x01` reopens it (turn.slot 0, fed +1)",
        "S8-C1": "C (`mode refuse`): ~1.5 s after the commit the slot is PENDING -- pending.slot 0, pending.ms < 2500, "
                 "turn.slot -1, menu.refused unchanged",
        "S8-C2": "C: by ~3.5 s REFUSED -- menu.refused +1, pending null, turn.slot 0 again, feed.refused +1",
        "S8-C3": "C: exactly ONE 'REFUSED or lost -- buzzer, the slot reopens at the root' line",
        "S8-D1": f"D: the bit falls with the TARGET panel open -> within {CLOSE_FRAMES} frames turn.slot -1, hud.panel "
                 f"'none', 0 off turn.ready; mirror.closed +1; captures unchanged; 'local slot 0 (wire 0) closed' logged",
    }
    if calibrate:
        c["S8-CALA"] = (f"CALIBRATION flip: `bbench knob ini` with the bit still up -> the stock window opens (turn.slot 0 "
                        f"within {OPEN_FRAMES} frames of the flip's ack, stock_owns true, assist_slot -1)")
        c["S8-CAL"] = ("CALIBRATION (`bbench knob 0` = the pre-stage-8 guest): legs A-D went red EXACTLY as predicted "
                       "(A1-A5, B1-B5, C1-C3, D1)")
    else:
        c.update({
            "S8-E1": "E (`bbench freeze 1`): the open window holds 1 s (turn.slot 0 on every publish)",
            "S8-E2": "E: by ~2.5 s the lane is dead -- peer.live false, feed.live false, menu.mirrored [], stock_owns false, "
                     "why 'no live peer battle lane', turn.slot -1, 'closed all (ready mirror: no live peer battle lane)'",
            "S8-E3": "E: `bbench freeze 0` reopens it (peer.live, turn.slot 0)",
            "S8-F1": "F (`bbench caps 0`): stock_owns false, why 'host predates the command-phase gates', turn.slot -1, "
                     "assist_slot 0, 'the ready mirror is not serving -- host predates the command-phase gates' logged",
            "S8-F2": "F: an in-engine PNG with the digit panel serving, decoded non-blank (s8-F-digit-panel)",
            "S8-F3": "F: `bbench caps 2` brings the stock window back (stock_owns true, turn.slot 0)",
            "S8-G1": "G (roster for slot 1 only, `start 0x03`, `ready 0x01`): mirror.no_roster 1 within 2.5 s while "
                     "turn.slot -1 and assist_slot -1 (the bounded wait); 'wire slot 0 is Ready but the menu roster does not "
                     "carry it yet' logged",
            "S8-G2": "G (the fixer's bound): after >= 2.5 s stranded == [0] and assist_slot 0, the 'has been Ready ... "
                     "STRANDED for this turn' line",
            "S8-G3": "G: `bbench ready 0x02` -> turn.slot 1, mirror.open 2",
            "S8-H1": "H (`bbench unmap 1`): turn.slot -1, stranded == [1], assist_slot 1, mirror.closed +1, 'wire slot 1 is "
                     "Ready but has no local seat in this diorama (the bench `unmap` lever) -- STRANDED' logged",
            "S8-H2": "H: `bbench unmap none` reopens slot 1 (turn.slot 1)",
            "S8-I1": "I (`bbench knob 0`): stock_owns false, why 'the knob is off ([Netsync] GuestStockMenu=0, the bench "
                     "override)', turn.slot -1, assist_slot 1, knob 0, knob_bench 0",
            "S8-I2": "I: `bbench knob ini` restores the ini's value (knob_bench -1; stock_owns and slot 1 back when the ini "
                     "leaves GuestStockMenu on)",
            "S8-PZ": "PZ (fixer): pause, drop the bit, resume -> hud.panel 'none', turn.slot -1, and two Confirms throw "
                     "nothing (no exception line), the UI still BattleHUD",
            "S8-Q1": "Q (fixer; `endbench quit on`): the guest's Quit prompt HOLDS the open slot -- mirror.open keeps bit 1 for "
                     "1 s -- and 'the guest's Quit prompt is up -- the ready mirror holds its slots' logged",
            "S8-Q2": "Q: Cancel closes the prompt and restores the window at the root (turn.slot 1, hud.panel 'command')",
            "S8-Q3": "Q: under a second prompt the bit drops; Cancel then leaves it closed cleanly (turn.slot -1, panel "
                     "'none') and two Confirms throw nothing",
            "S8-J1": "J (`endbench victory` with slot 1 open): from the injection on turn.slot -1 and mirror.open 0, why "
                     "'waiting: the diorama is in phase ...', never reopened over 3 s while the bit stays up",
            "S8-K1": "K (`dioleave`): 'bench feed stopped (its diorama ended)', menu.feed null, peer.live false",
        })
    c.update({
        "S8-R9": "r9_refused 0 for the boot (read before the leave) -- the mirror never enqueued locally",
        "S8-INV": "the guest's save/party/bag fingerprint (sandbox autosave) is byte-identical, setup to end",
        "S8-R": "`reset` with the knob left forced: 'the GuestStockMenu override cleared -- the ini's value rules again "
                "(released with the harness)', knob_bench -1",
    })
    return c


# ------------------------------------------------------------------------------------------- reads
def _m(x) -> dict:
    return cb.bmenu(x)


def _mir(x) -> dict:
    v = _m(x).get("mirror")
    return v if isinstance(v, dict) else {}


def _feed(x) -> dict:
    v = _m(x).get("feed")
    return v if isinstance(v, dict) else {}


def _no_feed_baseline(m: dict, peer_live, turn_slot) -> tuple:
    """S8-P1's predicate on `netsync.battle.menu` before `bbench start`. (ok, which reason answered).

    StockMenuOwns (NetSyncBattle.StockMenu.cs) answers the FIRST missing gate, in this order: the knob, a live diorama,
    the party mirror (NetSyncParty.MirrorActive || BenchFeedArmed), a peer view, caps bit 1, not faulted. Two of those
    gates are the feed's to satisfy -- BenchFeedArmed is the mirror gate's second leg, and the feed is what fills the
    peer view -- so with no feed either one can be the first gate missing, and both are the no-feed baseline. On the
    selftest role the diorama's own B3.2 party bench (HonoluluBattleMain.Start -> NetSyncParty.SelfTestMirror, logged
    "diorama party BENCH: armed") sets MirrorActive, so the s107 run passed the mirror gate and answered the LATER one,
    "no live peer battle lane". A build or role where that bench does not arm answers the mirror gate instead.
    Still RED: the knob or diorama reason (the knob is the ini's and the diorama is up and steady, so either is a real
    fault), caps or faulted (no view exists to read them from), any other text, owns true, a feed object (or no `feed`
    key), serving, an open slot, or a live peer lane."""
    why = str(m.get("why") or "")
    if why == WHY_STALE:
        which = "the lane gate: 'no live peer battle lane' (the mirror gate passed: the diorama's party bench arms it)"
    elif why.startswith(WHY_NO_MIRROR):
        which = "the mirror gate: 'the party mirror is not active ...'"
    else:
        return False, f"NOT a reason the feed satisfies: {why!r}"
    mir = m.get("mirror") if isinstance(m.get("mirror"), dict) else {}
    ok = (m.get("stock_owns") is False and "feed" in m and m.get("feed") is None and mir.get("serving") is False
          and turn_slot == -1 and peer_live is False)
    return ok, which


def _bb(g, *args) -> tuple:
    return cb.try_ns(g, "bbench", *args)


def _bb_st(g, *args):
    """`bbench ...` -> (the state it returned or None, why)."""
    try:
        return cb.ns_verb(g, "bbench", *args), ""
    except HarnessError as err:
        return None, str(err)[:300]


def _brief(x) -> str:
    m, t = _m(x), cb.turn(x)
    return (f"turn.slot={t.get('slot')!r} ready={t.get('ready')} done={t.get('done')} panel={cb.hud(x).get('panel')!r} "
            f"stock_owns={m.get('stock_owns')!r} why={m.get('why')!r} assist={m.get('assist_slot')!r} "
            f"stranded={m.get('stranded')} pending={m.get('pending')} "
            f"mirror={cb.pick(_mir(x), 'serving', 'open', 'fed', 'accepted', 'closed', 'no_roster')} "
            f"peer.live={cb.peer(x).get('live')!r} peer.ready={cb.peer(x).get('ready_mask')!r}")


def _open_after(g, st0, slot: int, timeout: float = 2.0) -> tuple:
    """After a verb that should open ``slot``: (opened, frames from the verb's ack, samples)."""
    f0 = cb.frame_of(st0) if st0 is not None else cb.frame_of(g.state)
    samples, hit = cb.watch_from(g, st0, lambda s: s.turn_slot == slot and cb.hud(s).get("panel") == "command", timeout)
    return hit is not None, (cb.frame_of(hit) - f0) if hit is not None else None, samples


def _commit_attack(g) -> tuple:
    """Attack through the stock window at the first enemy. (ok, why, the target mask)."""
    ok, why, st = cb.pick_command(g, cb.MENU_ATTACK, expect_panel="target")
    if not ok:
        return False, why, None
    mask, name = cb.target_mask(g.state)
    g.press("confirm", 4)
    return True, "", mask


class _Ctx:
    ini_knob = None


# ------------------------------------------------------------------------------------------- the run
def run(g, field: int = cb.FIELD):
    calibrate = cb.CALIBRATE
    led = cb.Ledger(g, _catalog(calibrate), finals=("S8-INV", "S8-R", "S8-CAL"))
    fp0 = [None, ""]
    ctx = _Ctx()
    try:
        _run(g, led, ctx, field, fp0, calibrate)
    finally:
        g.note(f"Memoria.log archived: {cb.archive_log(g, 'stock-menu-live')}")
        led.close()
        try:
            if cb.dio(g.state).get("booted"):
                cb.leave(g, field)
            fpn, why = cb.fingerprint(g, field=field)
            if fp0[0] is None or fpn is None:
                led.check("S8-INV", False, f"not reached: the invariant snapshot failed ({fp0[1] or why})")
            else:
                diff = cb.fp_diff(fp0[0], fpn)
                led.check("S8-INV", not diff, f"changed: {diff}" if diff else f"identical (gil {fpn.get('gil')})")
        except HarnessError as err:
            g.note(f"the final invariant read failed: {str(err)[:160]}")
        _release(g, led)
        if calibrate:
            led.judge_calibration("S8-CAL", PREDICTED)
        led.close(final=True)


def _run(g, led: cb.Ledger, ctx: _Ctx, field: int, fp0: list, calibrate: bool) -> None:
    ok, why = cb.setup(g, field, label="B4/B5 stage 8: the production ready mirror (s107), solo"
                                       + (" -- CALIBRATION (bbench knob 0)" if calibrate else ""))
    led.check("S8-S0", ok, why)
    ctx.ini_knob = cb.ini_value(g, "Netsync", "GuestStockMenu")
    fp, fwhy = cb.fingerprint(g, field=field)
    fp0[0], fp0[1] = fp, fwhy
    st = g.state
    g.note(f"probe stage: {cb.stage_of(st)}; [Netsync] GuestStockMenu in Memoria.ini (read-only): {ctx.ini_knob!r}")
    led.check("S8-P0", cb.has(st, cb.PROBES[8]),
              f"netsync.battle.menu keys: {sorted(_m(st))}" if cb.has(st, "netsync.battle") else "no `netsync.battle`")
    try:
        g.state_every(1)
    except (HarnessError, AttributeError) as err:
        g.note(f"stateevery 1 refused ({str(err)[:120]}) -- frame windows read at the default cadence")
    booted, bwhy = cb.boot(g)
    if not booted:
        led.close(bwhy)
        cb.back_to_field(g, field)
        return
    st = cb.wait_steady(g)
    if st is None:
        led.close("the diorama never reached its command phase (PHASE_NORMAL + turn.enabled)")
        cb.leave(g, field)
        return
    m = _m(st)
    p1_ok, p1_which = _no_feed_baseline(m, cb.peer(st).get("live"), st.turn_slot)
    led.check("S8-P1", p1_ok, f"{p1_which}; " + _brief(st) + f" feed={m.get('feed', 'ABSENT')!r}")
    at = cb.mark(g)
    ok1, why1 = _bb(g, "roster", "auto", 0)
    ok2, why2 = _bb(g, "start", "0x01") if ok1 else (False, why1)
    lines = cb.wait_log(g, at, STARTED, 2.0)
    led.check("S8-P2", ok1 and ok2 and cb.count(lines, STARTED) == 1, (why1 or why2) or cb.grep(lines, "bench feed"))
    if not (ok1 and ok2):
        _r9(g, led)                                        # a whole-boot invariant: judged even when no leg can run
        led.close(f"the bench feed cannot start on this engine -- {why1 or why2}")
        cb.leave(g, field)
        return
    if calibrate:
        okk, whyk = _bb(g, "knob", 0)
        g.note(f"CALIBRATION: `bbench knob 0` -> {'pulled' if okk else whyk}")
    _leg_a(g, led, at)
    _leg_b(g, led)
    _leg_c(g, led)
    _leg_d(g, led)
    if calibrate:
        _cal_flip(g, led)
        _r9(g, led)
        cb.leave(g, field)
        return
    _leg_e(g, led)
    _leg_f(g, led)
    _leg_g(g, led)
    _leg_h(g, led)
    _leg_i(g, led, ctx)
    _leg_pz(g, led)
    _leg_q(g, led)
    _leg_j(g, led)
    _r9(g, led)
    _leg_k(g, led, field)


def _r9(g, led: cb.Ledger) -> None:
    v = _m(g.state).get("r9_refused")
    led.check("S8-R9", v == 0, f"r9_refused={v!r} (site {_m(g.state).get('r9_site')!r})")


# ------------------------------------------------------------------------------------------- legs
def _leg_a(g, led: cb.Ledger, feed_at: int) -> None:
    """``feed_at``: the log mark taken before P2's `roster auto 0` + `start` -- the SERVING line's window (see A4)."""
    g.note("A: the wire Ready bit opens the stock window")
    st = cb.poll(g, lambda s: cb.peer(s).get("live") is True and _mir(s).get("serving") is True, 2.0,
                 "the feed's lane and the mirror serving") or g.state
    m, p, f = _m(st), cb.peer(st), _feed(st)
    led.check("S8-A1", p.get("live") is True and p.get("caps") == 2 and p.get("ready_mask") == 0 and m.get("stock_owns") is True
              and m.get("why") is None and _mir(st).get("serving") is True and st.turn_slot == -1
              and m.get("assist_slot") == -1 and f.get("menu_open") is False,
              _brief(st) + f" caps={p.get('caps')!r} feed.menu_open={f.get('menu_open')!r}")
    fed0 = _mir(st).get("fed")
    at = cb.mark(g)
    st0, why = _bb_st(g, "ready", "0x01")
    if st0 is None:
        led.unreached(("S8-A2", "S8-A3", "S8-A4", "S8-A5"), f"`bbench ready 0x01` refused -- {why}")
        return
    samples, hit = cb.watch_from(g, st0, lambda s: s.turn_slot == 0 and cb.hud(s).get("panel") == "command", 1.5)
    f_bit = cb.first_frame(samples, lambda s: cb.mask_bits(cb.peer(s).get("ready_mask")) & 1)
    f_open = cb.frame_of(hit) if hit is not None else None
    s = hit or g.state
    led.check("S8-A2", hit is not None and f_bit is not None and f_open - f_bit <= OPEN_FRAMES
              and 0 in (cb.turn(s).get("ready") or []) and cb.peer(s).get("ready_mask") == 1 and _mir(s).get("open") == 1
              and isinstance(fed0, int) and _mir(s).get("fed") == fed0 + 1,
              f"bit at frame {f_bit!r}, open at {f_open!r}; fed {fed0!r}->{_mir(s).get('fed')!r}; {_brief(s)}")
    led.check("S8-A3", hit is not None and _m(s).get("assist_slot") == -1 and _feed(s).get("menu_open") is True,
              f"assist_slot={_m(s).get('assist_slot')!r} feed.menu_open={_feed(s).get('menu_open')!r}")
    lines = cb.wait_log(g, at, FED0, 1.5)
    # SERVING is logged once per boot (MirrorLogFirst "serving") on the FIRST tick the mirror owns the slots with the
    # gate open -- that needs no Ready bit, only the feed's live lane, so it lands while P2's `start` blocks (A1 even
    # polls for mirror.serving before this leg's mark). Its window is the feed's (P2's mark); FED0 is this leg's own.
    lines_feed = cb.new(g, feed_at)
    led.check("S8-A4", cb.count(lines_feed, SERVING) == 1 and cb.count(lines, FED0) == 1,
              f"since the feed start: {cb.grep(lines_feed, 'ready mirror is SERVING')}; since the bit: "
              + cb.grep(lines, "Ready ->", "stock menu: wire"))
    g.wait_frames(8)
    shot_slot = g.state.turn_slot
    p_, pwhy = cb.shot(g, "s8-A-stock-window")
    g.note(f"shot s8-A-stock-window: {p_ or pwhy} -- READ it (the stock command window, no digit-panel text)")
    led.check("S8-A5", shot_slot == 0 and p_ is not None and cb.png_not_blank(p_),
              f"turn.slot at the shot {shot_slot}; {p_ or pwhy}")


def _leg_b(g, led: cb.Ledger) -> None:
    g.note("B: accept -- the bench host takes the forwarded Attack and drops the bit")
    st = g.state
    if st.turn_slot != 0:
        led.unreached(("S8-B1", "S8-B2", "S8-B3", "S8-B4", "S8-B5"), f"no stock window open for slot 0 ({_brief(st)})")
        return
    m0, f0, mir0 = _m(st), _feed(st), _mir(st)
    c0, sent0, taken0, acc0, macc0 = m0.get("captures"), m0.get("sent"), f0.get("taken"), f0.get("accepted"), mir0.get("accepted")
    at = cb.mark(g)
    ok, why, mask = _commit_attack(g)
    if not ok:
        led.unreached(("S8-B1", "S8-B2", "S8-B3", "S8-B4", "S8-B5"), f"the Attack never reached its target: {why}")
        return
    st = cb.poll(g, lambda s: _m(s).get("captures") == (c0 or 0) + 1, 3.0, "the capture") or g.state
    cap = cb.captured(st)
    dec = cb.decode_cmd(cap.get("hex", ""))
    led.check("S8-B1", isinstance(c0, int) and _m(st).get("captures") == c0 + 1 and cap.get("slot") == 0
              and cap.get("action") == cb.ACT_ATTACK and mask is not None and cap.get("mask") == mask and dec is not None
              and dec.get("slot") == 0 and dec.get("action") == cb.ACT_ATTACK and dec.get("mask") == mask
              and isinstance(sent0, int) and _m(st).get("sent") == sent0 + 1,
              f"captured={cap} decoded={dec} (target mask {mask!r}); sent {sent0!r}->{_m(st).get('sent')!r}")
    st = cb.poll(g, lambda s: _feed(s).get("accepted") == (acc0 or 0) + 1 and cb.peer(s).get("ready_mask") == 0, 2.0,
                 "the bench host's accept") or g.state
    f = _feed(st)
    led.check("S8-B2", isinstance(taken0, int) and f.get("taken") == taken0 + 1 and f.get("accepted") == (acc0 or 0) + 1
              and f.get("ready") == 0 and cb.peer(st).get("ready_mask") == 0,
              f"feed taken {taken0!r}->{f.get('taken')!r} accepted {acc0!r}->{f.get('accepted')!r} ready={f.get('ready')!r} "
              f"last={f.get('last')!r}; peer.ready_mask={cb.peer(st).get('ready_mask')!r}")
    st = cb.poll(g, lambda s: _mir(s).get("accepted") == (macc0 or 0) + 1 and _m(s).get("pending") is None, 2.0,
                 "the mirror to count the accept") or g.state
    t = cb.turn(st)
    led.check("S8-B3", isinstance(macc0, int) and _mir(st).get("accepted") == macc0 + 1 and _m(st).get("pending") is None
              and st.turn_slot == -1 and 0 not in (t.get("ready") or []) and 0 not in (t.get("done") or []), _brief(st))
    lines = cb.wait_log(g, at, ACCEPTED_LINE, 2.0)
    hexs = cap.get("hex") or "?"
    led.check("S8-B4", any(TOOK + hexs + "]" in ln and "ACCEPTED" in ln for ln in lines) and cb.count(lines, ACCEPTED_LINE) == 1,
              cb.grep(lines, "bench feed: the bench host took", "was ACCEPTED"))
    samples = cb.hold_for(g, 1.0)
    reopened = [cb.frame_of(x) for x in samples if x.turn_slot != -1]
    fed0 = _mir(g.state).get("fed")
    st0, why = _bb_st(g, "ready", "0x01")
    opened, frames, _ = _open_after(g, st0, 0) if st0 is not None else (False, None, [])
    led.check("S8-B5", samples and not reopened and opened and isinstance(fed0, int) and _mir(g.state).get("fed") == fed0 + 1,
              why or f"reopened on {reopened[:4]} during the 1 s; `ready 0x01` reopened: {opened} ({frames!r} frames); fed "
                     f"{fed0!r}->{_mir(g.state).get('fed')!r}")


def _leg_c(g, led: cb.Ledger) -> None:
    g.note("C: refuse -- the bit stays up, the slot reopens with one buzzer line")
    st = g.state
    if st.turn_slot != 0:
        led.unreached(("S8-C1", "S8-C2", "S8-C3"), f"no stock window open for slot 0 ({_brief(st)})")
        return
    ok, why = _bb(g, "mode", "refuse")
    r0, fr0 = _m(g.state).get("refused"), _feed(g.state).get("refused")
    at = cb.mark(g)
    ok2, why2, _ = _commit_attack(g) if ok else (False, why, None)
    if not ok2:
        led.unreached(("S8-C1", "S8-C2", "S8-C3"), f"the refused commit never happened: {why2}")
        return
    t0 = time.time()
    cb.hold_for(g, max(0.0, 1.5 - (time.time() - t0)))
    st = g.state
    p = _m(st).get("pending") or {}
    led.check("S8-C1", p.get("slot") == 0 and isinstance(p.get("ms"), int) and p["ms"] < 2500 and st.turn_slot == -1
              and _m(st).get("refused") == r0, f"pending={_m(st).get('pending')!r} refused {r0!r}->{_m(st).get('refused')!r}; "
                                               f"{_brief(st)}")
    st = cb.poll(g, lambda s: _m(s).get("refused") == (r0 or 0) + 1 and s.turn_slot == 0, max(0.5, 5.0 - (time.time() - t0)),
                 "the refusal and the reopen") or g.state
    led.check("S8-C2", isinstance(r0, int) and _m(st).get("refused") == r0 + 1 and _m(st).get("pending") is None
              and st.turn_slot == 0 and isinstance(fr0, int) and _feed(st).get("refused") == fr0 + 1,
              f"{time.time() - t0:.1f}s after the commit: refused {r0!r}->{_m(st).get('refused')!r} feed.refused {fr0!r}->"
              f"{_feed(st).get('refused')!r}; {_brief(st)}")
    lines = cb.new(g, at)
    led.check("S8-C3", cb.count(lines, REFUSED_LINE) == 1, cb.grep(lines, "REFUSED"))
    _bb(g, "mode", "accept")


def _leg_d(g, led: cb.Ledger) -> None:
    g.note("D: the bit falls while the target panel is open")
    st = g.state
    if st.turn_slot != 0:
        led.unreached(("S8-D1",), f"no stock window open for slot 0 ({_brief(st)})")
        return
    _bb(g, "mode", "accept")
    ok, why, _ = cb.pick_command(g, cb.MENU_ATTACK, expect_panel="target")
    if not ok:
        led.unreached(("S8-D1",), f"the target panel never opened: {why}")
        return
    c0, cl0 = _m(g.state).get("captures"), _mir(g.state).get("closed")
    at = cb.mark(g)
    st0, why = _bb_st(g, "ready", "0")
    if st0 is None:
        led.check("S8-D1", False, f"`bbench ready 0` refused -- {why}")
        return
    samples, hit = cb.watch_from(g, st0, lambda s: s.turn_slot == -1 and cb.hud(s).get("panel") == "none", 1.5)
    f_drop = cb.first_frame(samples, lambda s: not cb.mask_bits(cb.peer(s).get("ready_mask")) & 1)
    s = hit or g.state
    lines = cb.wait_log(g, at, CLOSED0, 1.0)
    led.check("S8-D1", hit is not None and f_drop is not None and cb.frame_of(hit) - f_drop <= CLOSE_FRAMES
              and 0 not in (cb.turn(s).get("ready") or []) and isinstance(cl0, int) and _mir(s).get("closed") == cl0 + 1
              and _m(s).get("captures") == c0 and cb.count(lines, CLOSED0) == 1,
              f"bit fell at frame {f_drop!r}, shut at {cb.frame_of(hit) if hit is not None else None!r}; closed {cl0!r}->"
              f"{_mir(s).get('closed')!r} captures {c0!r}->{_m(s).get('captures')!r}; {_brief(s)}; {cb.grep(lines, 'closed')}")


def _cal_flip(g, led: cb.Ledger) -> None:
    g.note("CALIBRATION flip: `bbench knob ini` with the bit up -- leg A's opening must now pass")
    _bb(g, "ready", "0x01")
    g.wait_frames(10)
    st0, why = _bb_st(g, "knob", "ini")
    opened, frames, samples = _open_after(g, st0, 0) if st0 is not None else (False, None, [])
    s = g.state
    led.check("S8-CALA", opened and frames is not None and frames <= OPEN_FRAMES + 2 and _m(s).get("stock_owns") is True
              and _m(s).get("assist_slot") == -1,
              why or f"opened {opened} after {frames!r} frames; {_brief(s)}")


def _leg_e(g, led: cb.Ledger) -> None:
    g.note("E: freeze -- the lane goes stale, the window closes, a thaw reopens it")
    st0, why = _bb_st(g, "ready", "1")
    opened, _, _ = _open_after(g, st0, 0) if st0 is not None else (False, None, [])
    if not opened:
        led.unreached(("S8-E1", "S8-E2", "S8-E3"), why or f"the window never opened ({_brief(g.state)})")
        return
    at = cb.mark(g)
    ok, why = _bb(g, "freeze", "1")
    samples = cb.hold_for(g, 1.0)
    shut = [cb.frame_of(x) for x in samples if x.turn_slot != 0]
    led.check("S8-E1", ok and samples and not shut, why or f"shut on {shut[:4]} within the first second")
    st = cb.poll(g, lambda s: cb.peer(s).get("live") is False and s.turn_slot == -1, 3.5, "the stale lane") or g.state
    m = _m(st)
    lines = cb.new(g, at)
    led.check("S8-E2", cb.peer(st).get("live") is False and _feed(st).get("live") is False and m.get("mirrored") == []
              and m.get("stock_owns") is False and m.get("why") == WHY_STALE and st.turn_slot == -1
              and any(CLOSED_STALE in ln for ln in lines),
              f"mirrored={m.get('mirrored')!r} feed.live={_feed(st).get('live')!r}; {_brief(st)}; {cb.grep(lines, 'closed all')}")
    st0, why = _bb_st(g, "freeze", "0")
    opened, frames, _ = _open_after(g, st0, 0, 2.5) if st0 is not None else (False, None, [])
    led.check("S8-E3", opened and cb.peer(g.state).get("live") is True, why or f"reopened {opened}; {_brief(g.state)}")


def _leg_f(g, led: cb.Ledger) -> None:
    g.note("F: a host without the caps bit -- the digit panel serves")
    at = cb.mark(g)
    ok, why = _bb(g, "caps", 0)
    st = cb.poll(g, lambda s: _m(s).get("why") == WHY_CAPS and s.turn_slot == -1, 1.5, "the caps refusal") or g.state
    lines = cb.wait_log(g, at, PREDATES, 1.0)
    led.check("S8-F1", ok and _m(st).get("stock_owns") is False and _m(st).get("why") == WHY_CAPS and st.turn_slot == -1
              and _m(st).get("assist_slot") == 0 and cb.count(lines, PREDATES) == 1,
              why or f"{_brief(st)}; {cb.grep(lines, 'not serving')}")
    g.wait_frames(8)
    p_, pwhy = cb.shot(g, "s8-F-digit-panel")
    g.note(f"shot s8-F-digit-panel: {p_ or pwhy} -- READ it (the digit panel '[1] Attack   [2] Defend ...')")
    led.check("S8-F2", p_ is not None and cb.png_not_blank(p_), p_ or pwhy)
    st0, why = _bb_st(g, "caps", 2)
    opened, frames, _ = _open_after(g, st0, 0) if st0 is not None else (False, None, [])
    led.check("S8-F3", opened and _m(g.state).get("stock_owns") is True, why or f"reopened {opened}; {_brief(g.state)}")


def _leg_g(g, led: cb.Ledger) -> None:
    g.note("G: the right slot -- a roster for slot 1 only, the bit on wire 0 waits, then strands; wire 1 opens slot 1")
    # Drop wire 0's bit FIRST (F3 left it up with slot 0 open). Re-arming the roster for slot 1 while wire 0 is still
    # Ready would make the very next serving tick log G1's once-per-boot line ('wire slot 0 is Ready but the menu roster
    # does not carry it yet', MirrorLogFirst "noroster 0") BEFORE this leg's mark -- spent, and G1 red on a correct
    # engine. With the bit down, the roster change is silent and the line belongs to `ready 0x01` below.
    ok0, why0 = _bb(g, "ready", "0")
    cb.poll(g, lambda s: s.turn_slot == -1 and not cb.mask_bits(cb.peer(s).get("ready_mask")) & 1, 1.5,
            "wire 0's bit to fall before the roster change")
    ok1, why1 = _bb(g, "roster", "auto", 1) if ok0 else (False, why0)
    ok2, why2 = _bb(g, "start", "0x03") if ok1 else (False, why1)
    if not (ok1 and ok2):
        led.unreached(("S8-G1", "S8-G2", "S8-G3"), f"ready 0 / roster for slot 1 / restart refused -- {why1 or why2}")
        return
    cb.poll(g, lambda s: s.turn_slot == -1, 1.5, "the restart to shut slot 0")
    at = cb.mark(g)
    st_bit, why3 = _bb_st(g, "ready", "0x01")
    ok3 = st_bit is not None
    st_bit = st_bit or g.state
    t0 = time.time()
    opened = []
    samples, hit = cb.watch(g, lambda s: _mir(s).get("no_roster") == 1, 2.5,
                            on_sample=lambda s: opened.append(cb.frame_of(s)) if s.turn_slot != -1 else None)
    s = hit or g.state
    lines = cb.new(g, at)
    led.check("S8-G1", ok3 and hit is not None and not opened and _m(s).get("assist_slot") == -1
              and cb.count(lines, NO_ROSTER0) == 1,
              why3 or f"no_roster={_mir(s).get('no_roster')!r} after {time.time() - t0:.1f}s; opened on {opened[:3]}; {_brief(s)}; "
                      f"{cb.grep(lines, 'menu roster')}")
    st = cb.poll(g, lambda x: _m(x).get("stranded") == [0] and _m(x).get("assist_slot") == 0, max(0.5, 5.0 - (time.time() - t0)),
                 "the bounded wait to strand wire 0") or g.state
    lines = cb.new(g, at)
    took = cb.elapsed(st_bit, st)                          # the game's clock when published, else the reads'
    led.check("S8-G2", _m(st).get("stranded") == [0] and _m(st).get("assist_slot") == 0 and took >= 2.4
              and any(BOUND0 in ln and "STRANDED for this turn" in ln for ln in lines),
              f"{took:.1f}s after the bit: {_brief(st)}; {cb.grep(lines, 'has been Ready')}")
    st0, why = _bb_st(g, "ready", "0x02")
    opened1, frames, _ = _open_after(g, st0, 1) if st0 is not None else (False, None, [])
    led.check("S8-G3", opened1 and _mir(g.state).get("open") == 2, why or f"slot 1 opened {opened1}; {_brief(g.state)}")


def _leg_h(g, led: cb.Ledger) -> None:
    g.note("H: unmap wire 1 -- stranded to the digit panel")
    if g.state.turn_slot != 1:
        led.unreached(("S8-H1", "S8-H2"), f"slot 1 is not open ({_brief(g.state)})")
        return
    cl0 = _mir(g.state).get("closed")
    at = cb.mark(g)
    ok, why = _bb(g, "unmap", 1)
    # assist_slot is in the predicate too: the engine computes it (BenchFeedTick -> GuestAssistTick -> AssistSlot, from
    # the PREVIOUS tick's _strandedMask) before MirrorServe strands wire 1, so the first doc showing stranded [1] still
    # reads assist_slot -1; it follows one frame later (as G2 waits for both).
    st = cb.poll(g, lambda s: s.turn_slot == -1 and _m(s).get("stranded") == [1] and _m(s).get("assist_slot") == 1, 1.5,
                 "the unmap strand (and the digit panel taking wire 1)") or g.state
    lines = cb.wait_log(g, at, UNMAP1, 1.0)
    led.check("S8-H1", ok and st.turn_slot == -1 and _m(st).get("stranded") == [1] and _m(st).get("assist_slot") == 1
              and isinstance(cl0, int) and _mir(st).get("closed") == cl0 + 1 and cb.count(lines, UNMAP1) == 1,
              why or f"closed {cl0!r}->{_mir(st).get('closed')!r}; {_brief(st)}; {cb.grep(lines, 'no local seat')}")
    st0, why = _bb_st(g, "unmap", "none")
    opened, frames, _ = _open_after(g, st0, 1) if st0 is not None else (False, None, [])
    led.check("S8-H2", opened, why or f"slot 1 reopened {opened}; {_brief(g.state)}")


def _leg_i(g, led: cb.Ledger, ctx: _Ctx) -> None:
    g.note("I: the knob -- forced off for this process, then back to the ini")
    ok, why = _bb(g, "knob", 0)
    st = cb.poll(g, lambda s: _m(s).get("why") == WHY_KNOB and s.turn_slot == -1, 1.5, "the knob to stand the mirror down") \
        or g.state
    m = _m(st)
    led.check("S8-I1", ok and m.get("stock_owns") is False and m.get("why") == WHY_KNOB and st.turn_slot == -1
              and m.get("assist_slot") == 1 and m.get("knob") == 0 and m.get("knob_bench") == 0,
              why or f"knob={m.get('knob')!r} knob_bench={m.get('knob_bench')!r}; {_brief(st)}")
    ini_on = str(ctx.ini_knob or "1").split(";", 1)[0].strip() != "0"
    st0, why = _bb_st(g, "knob", "ini")
    if ini_on:
        opened, frames, _ = _open_after(g, st0, 1) if st0 is not None else (False, None, [])
        ok2 = opened and _m(g.state).get("stock_owns") is True
    else:
        ok2 = st0 is not None and _m(g.state).get("stock_owns") is False
    led.check("S8-I2", st0 is not None and ok2 and _m(g.state).get("knob_bench") == -1
              and _m(g.state).get("knob") == (1 if ini_on else 0),
              why or f"ini GuestStockMenu={ctx.ini_knob!r}; {_brief(g.state)} knob={_m(g.state).get('knob')!r} "
                     f"knob_bench={_m(g.state).get('knob_bench')!r}")


def _leg_pz(g, led: cb.Ledger) -> None:
    g.note("PZ: pause, drop the bit, resume -- the window stays closed and Confirm throws nothing")
    if g.state.turn_slot != 1:
        _bb(g, "ready", "0x02")
        cb.poll(g, lambda s: s.turn_slot == 1, 1.5, "slot 1's window")
    if g.state.turn_slot != 1:
        led.check("S8-PZ", False, f"not reached: slot 1 is not open ({_brief(g.state)})")
        return
    at = cb.mark(g)
    g.press("start", 4)
    paused = cb.poll(g, lambda s: s.ui_state == "Pause" or not s.commands_enabled, 3.0, "the pause")
    if paused is None:
        led.check("S8-PZ", False, f"not reached: the pause never engaged (ui {g.state.ui_state!r}, "
                                  f"enabled {g.state.commands_enabled})")
        return
    ok, why = _bb(g, "ready", "0")
    g.wait_frames(10)
    g.press("start", 4)
    resumed = cb.poll(g, lambda s: s.ui_state == "BattleHUD" and s.commands_enabled, 3.0, "the resume")
    g.wait_frames(10)
    st = g.state
    for _ in range(2):
        g.press("confirm", 4)
        g.wait_frames(12)
    st2 = g.state
    bad = cb.exception_lines(cb.new(g, at))
    led.check("S8-PZ", ok and resumed is not None and cb.hud(st).get("panel") == "none" and st.turn_slot == -1
              and st2.ui_state == "BattleHUD" and not bad,
              why or f"after the resume {_brief(st)}; ui after 2 Confirms {st2.ui_state!r}; exception lines {bad[:3]}")


def _leg_q(g, led: cb.Ledger) -> None:
    g.note("Q: the guest's own Quit prompt holds the slot (NEVER Confirm while it is up)")
    if not cb.has(g.state, cb.PROBES[10]):
        led.unreached(("S8-Q1", "S8-Q2", "S8-Q3"), "`endbench quit` is stage 10 (s109): no `netsync.battle.end.replay` here")
        return
    _bb(g, "ready", "0x02")
    if cb.poll(g, lambda s: s.turn_slot == 1 and cb.hud(s).get("panel") == "command", 2.0, "slot 1's window") is None:
        led.unreached(("S8-Q1", "S8-Q2", "S8-Q3"), f"slot 1 is not open ({_brief(g.state)})")
        return
    at = cb.mark(g)
    ok, why = cb.try_ns(g, "endbench", "quit", "on")
    up = cb.poll(g, lambda s: cb.quit_prompt_up(s), 2.0, "the quit prompt") if ok else None
    if not ok or up is None:
        if ok:
            cb.try_ns(g, "endbench", "quit", "off")
        led.unreached(("S8-Q1", "S8-Q2", "S8-Q3"), why or f"the quit prompt never showed (ui {g.state.ui_state!r}, group "
                                                         f"{cb.cursor_group(g.state)!r})")
        return
    samples = cb.hold_for(g, 1.0)
    lost = [cb.frame_of(x) for x in samples if not cb.mask_bits(_mir(x).get("open")) & 2]
    lines = cb.new(g, at)
    led.check("S8-Q1", samples and not lost and cb.count(lines, QUIT_HOLD) == 1,
              f"mirror.open lost bit 1 on {lost[:4]}; {cb.grep(lines, 'Quit prompt')}")
    g.press("cancel", 4)
    st = cb.poll(g, lambda s: s.ui_state == "BattleHUD" and not cb.quit_prompt_up(s) and s.turn_slot == 1
                 and cb.hud(s).get("panel") == "command", 2.0,
                 "the window restored at the root")
    if cb.quit_prompt_up(g.state):
        cb.try_ns(g, "endbench", "quit", "off")
    led.check("S8-Q2", st is not None, f"after Cancel: ui {g.state.ui_state!r}; {_brief(g.state)}")
    at = cb.mark(g)
    ok, why = cb.try_ns(g, "endbench", "quit", "on")
    up = cb.poll(g, lambda s: cb.quit_prompt_up(s), 2.0, "the second quit prompt") if ok else None
    if up is None:
        if ok:
            cb.try_ns(g, "endbench", "quit", "off")
        led.check("S8-Q3", False, why or f"not reached: the second quit prompt never showed (ui {g.state.ui_state!r})")
        return
    _bb(g, "ready", "0")
    g.wait_frames(10)
    g.press("cancel", 4)
    st = cb.poll(g, lambda s: s.ui_state == "BattleHUD" and not cb.quit_prompt_up(s) and s.turn_slot == -1
                 and cb.hud(s).get("panel") == "none", 2.0,
                 "the clean close")
    if cb.quit_prompt_up(g.state):
        cb.try_ns(g, "endbench", "quit", "off")
        led.check("S8-Q3", False, "the prompt stayed up after Cancel (hidden by `endbench quit off`; no Confirm pressed)")
        return
    for _ in range(2):
        g.press("confirm", 4)
        g.wait_frames(12)
    bad = cb.exception_lines(cb.new(g, at))
    led.check("S8-Q3", st is not None and g.state.ui_state == "BattleHUD" and not bad,
              f"after Cancel: {_brief(g.state)} ui {g.state.ui_state!r}; exception lines {bad[:3]}")


def _leg_j(g, led: cb.Ledger) -> None:
    g.note("J: the end coupling -- an injected victory closes the window and it never reopens")
    _bb(g, "ready", "0x02")
    if cb.poll(g, lambda s: s.turn_slot == 1, 2.0, "slot 1's window") is None:
        led.check("S8-J1", False, f"not reached: slot 1 is not open ({_brief(g.state)})")
        return
    ok, why = cb.try_ns(g, "endbench", "victory")
    samples = cb.hold_for(g, 3.0)
    inj = next((i for i, x in enumerate(samples) if cb.bend(x).get("injected") is True), None)
    after = samples[inj:] if inj is not None else []
    bad = [(cb.frame_of(x), x.turn_slot, _mir(x).get("open")) for x in after if x.turn_slot != -1 or _mir(x).get("open") != 0]
    st = g.state
    led.check("S8-J1", ok and inj is not None and after and not bad and str(_m(st).get("why") or "").startswith(WHY_PHASE)
              and _feed(st).get("ready") == 2,
              why or f"injected at sample {inj!r}; open after it (frame, slot, mirror.open) {bad[:4]}; why={_m(st).get('why')!r} "
                     f"feed.ready={_feed(st).get('ready')!r}")
    cb.try_ns(g, "endbench", "clear")


def _leg_k(g, led: cb.Ledger, field: int) -> None:
    g.note("K: dioleave -- the feed stops with its diorama")
    at = cb.mark(g)
    left, why = cb.leave(g, field)
    lines = cb.wait_log(g, at, FEED_STOP, 2.0)
    st = g.state
    led.check("S8-K1", left and cb.count(lines, FEED_STOP) == 1 and "feed" in _m(st) and _m(st).get("feed") is None
              and cb.peer(st).get("live") is False,
              why or f"feed={_m(st).get('feed', 'ABSENT')!r} peer.live={cb.peer(st).get('live')!r}; {cb.grep(lines, 'bench feed')}")


def _release(g, led: cb.Ledger) -> None:
    """The knob left FORCED on purpose, then `reset`: the release must clear it and say so."""
    ok, why = _bb(g, "knob", 0)
    at = cb.mark(g)
    cb.release(g)
    st = g.state
    lines = cb.new(g, at)
    led.check("S8-R", ok and cb.count(lines, KNOB_REL) == 1 and _m(st).get("knob_bench") == -1
              and (st.netsync or {}).get("forced") is False,
              why or f"knob_bench={_m(st).get('knob_bench')!r}; {cb.grep(lines, 'released with the harness')}")
