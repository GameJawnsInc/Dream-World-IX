"""s160 -- THE CHEST RELAY, the WIRE half (studies/field-coop/CHEST-RELAY.md, memoria-patches s160): two games on one machine.
[ff9mapkit netsync s160]

The solo bench (coop_chest_relay.py) fabricates section 9 on the guest's own copy. This duo runs the REAL host: the host's harness
walks into field 200's ChestA push range and presses Confirm; the host's chest body reads the press with control on, ArmChestStart
stamps a chest start at once, the state lane carries it in section 9, and the following guest's copy opens the same chest.

Both games: New Game, the env-slot pokes, flag 2471 = 1 (no Nero), flag 7244 = 0 (the chest closed), warp 200 at scenario 2000 entrance
0, then the duo pairs them on 200 (the guest reloads 200 under the host's mirrored story). The guest stays at the spawn (FAR).

  W0     paired on 200, the guest mirroring, both engines publish `netsync.chest`; the chest closed on both copies (7244 clear).
  W1     the host stamps exactly ONE chest start at its press ("chest relay: host opened chest 9 on field 200", host.stamped +1).
  W2     the guest accepts and serves it exactly once (one "opening chest 9" line, accepted +1, served +1, expired +0, declined +0) --
         THE SAME NONCE IS APPLIED ONCE, judged by the counters, never by a window.
  W3     both windows are open at the same time (the guest one network delay behind, not a turn + kneel + lid behind), each naming the
         item, and the guest's opened flag rises on its own copy.
  W4     the host's Confirm closes the HOST's window, and the guest's closes with no guest input (the lockstep's ADV), and the guest's
         control comes back.
  W5     option C: the host's sticky scene is a talk's while the chest runs (host_plain_scene never true), and the guest never steps out.
  W6     the guest's latency: accept within 1500 ms of the host's stamp (the out-of-band push).

NOT HERE: the version gate against an s159 guest (an instance root junctions Managed to the install: both games run one DLL -- see
CHEST-RELAY.md "The version gate"), a JP-language pair, a late (deferred / climb-held) accept's bag (R8's first frame).

    py tools/harness/duo.py studies/test-harness/scenarios/coop_chest_relay_duo.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file
import coop_chest_relay as cr                              # noqa: E402 - the field-200 recipe and the pure reads

HarnessError = cb.HarnessError

NEAR = cr.NEAR
OPEN_S = 8.0
CLOSE_S = 8.0
ACCEPT_MS = 1500

LINE_STAMP = "[NetSync] chest relay: host opened chest {u} on field {f}"
LINE_ACCEPT = "[NetSync] chest relay: opening chest {u} on my copy of field {f}"


def _setup(g) -> str:
    g.poke(13, 0)
    g.poke(14, 0)
    g.flag(cr.FLAG_NO_NERO, True)
    g.flag(cr.FLAG_OPENED, False)
    g.warp(cr.FIELD, entrance=cr.ENTRANCE, scenario=cr.SCENARIO)
    g.wait_frames(45)
    try:
        g.watch(cr.FLAG_OPENED, cr.FLAG_NO_NERO)
    except HarnessError:
        pass
    return f"chest recipe: 200 at scenario {cr.SCENARIO}, 2471 set, 7244 clear"


PAIR = {"field": cr.FIELD, "host_setup": _setup, "guest_setup": _setup}


def _msgs(lines) -> list:
    """Duo.lines() rows are (datetime, level, msg): the messages."""
    return [ln[2] if isinstance(ln, tuple) else str(ln) for ln in lines]


def _count(lines, needle) -> int:
    return sum(1 for m in _msgs(lines) if needle in m)


def _first_time(lines, needle):
    return next((ln[0] for ln in lines if isinstance(ln, tuple) and needle in ln[2]), None)


def run_duo(d) -> None:
    d.strict = False
    host, guest = d.host, d.guest
    hs0, gs0 = host.state, guest.state
    pre = (cb.has(hs0, cr.PROBE) and cb.has(gs0, cr.PROBE) and cb.path(gs0, "netsync.session.mirroring") is True
           and cr.flag(hs0, cr.FLAG_OPENED) is not True and cr.flag(gs0, cr.FLAG_OPENED) is not True)
    d.check(pre, "W0: paired on 200, the guest mirroring, both publish netsync.chest, the chest closed on both",
            f"host chest {cb.has(hs0, cr.PROBE)} guest chest {cb.has(gs0, cr.PROBE)} mirroring "
            f"{cb.path(gs0, 'netsync.session.mirroring')!r}; 7244 host {cr.flag(hs0, cr.FLAG_OPENED)!r} guest "
            f"{cr.flag(gs0, cr.FLAG_OPENED)!r}", cid="W0")
    if not pre:
        return
    hc0, gc0 = cr.chest(hs0), cr.counters(gs0)
    stamped0 = int((hc0.get("host") or {}).get("stamped", 0) or 0)
    h_at, g_at = len(d.lines("host")), len(d.lines("guest"))
    try:
        host.walk_to(NEAR[0], NEAR[1], tolerance=cr.NEAR_TOL, strict=False)
    except HarnessError as err:
        d.check(False, "W1: the host reached NEAR", str(err)[:300], role="host", cid="W1")
        return
    hp = cb.raw(host.state).get("player") or {}
    dist = cr.gt.dist_xz((hp.get("x"), hp.get("z")), cr.CHEST_XZ)
    d.note(f"host at {dist:.0f} u from the chest (push radius {cr.RANGE_R:.0f})")
    t_press = time.time()
    host.press("confirm", 4)
    both_open, h_open_seen, g_open_seen, g_flag = None, False, False, False
    plain_seen, step_seen = False, False
    deadline = time.time() + OPEN_S
    while time.time() < deadline:
        hs, gs = host.state, guest.state
        h_open_seen = h_open_seen or cr.dialog_open(hs)
        g_open_seen = g_open_seen or cr.dialog_open(gs)
        g_flag = g_flag or cr.flag(gs, cr.FLAG_OPENED) is True
        plain_seen = plain_seen or cb.path(hs, "netsync.stepout.host_plain_scene") is True
        step_seen = step_seen or cb.path(gs, "netsync.stepout.active") is True
        if cr.dialog_open(hs) and cr.dialog_open(gs) and both_open is None:
            both_open = (cr.dialog_text(hs), cr.dialog_text(gs), time.time() - t_press)
            break
        time.sleep(0.05)
    hl, gl = d.lines("host")[h_at:], d.lines("guest")[g_at:]
    n_stamp = _count(hl, LINE_STAMP.format(u=cr.CHEST_UID, f=cr.FIELD))
    stamped = int(((cr.chest(host.state).get("host") or {}).get("stamped", 0)) or 0) - stamped0
    d.check(n_stamp == 1 and stamped == 1, "W1: the host stamps exactly one chest start at its press",
            f"stamp lines {n_stamp}, host.stamped +{stamped}: {cb.grep(_msgs(hl), 'chest relay:')}", role="host", cid="W1")
    time.sleep(1.0)
    gl = d.lines("guest")[g_at:]
    dg = cr.delta(gc0, cr.counters(guest.state))
    n_acc = _count(gl, LINE_ACCEPT.format(u=cr.CHEST_UID, f=cr.FIELD))
    d.check(n_acc == 1 and dg == {"accepted": 1, "served": 1, "expired": 0, "declined": 0},
            "W2: the guest accepts and serves it exactly once (the same nonce applied once)",
            f"opening lines {n_acc}; deltas {dg}; {cb.grep(_msgs(gl), 'chest relay:')}", role="guest", cid="W2")
    named = both_open is not None and all(any(w in t for w in cr.ITEM_WORDS) for t in both_open[:2])
    d.check(both_open is not None and named and g_flag,
            "W3: both windows open at once, each naming the item; the guest's opened flag rises on its own copy",
            f"both open {both_open!r}; host saw open {h_open_seen}, guest saw open {g_open_seen}; guest 7244 {g_flag}", cid="W3")
    # W4: the host closes; the guest's closes by itself
    host.press("confirm", 2)
    closed, g_ctl = None, False
    deadline = time.time() + CLOSE_S
    while time.time() < deadline:
        hs, gs = host.state, guest.state
        plain_seen = plain_seen or cb.path(hs, "netsync.stepout.host_plain_scene") is True
        step_seen = step_seen or cb.path(gs, "netsync.stepout.active") is True
        if cr.dialog_open(hs):
            host.press("confirm", 2)
        if not cr.dialog_open(hs) and not cr.dialog_open(gs) and cr.gt.control(gs):
            closed = time.time() - t_press
            g_ctl = True
            break
        time.sleep(0.1)
    g_pressed = list(guest.state.held)                 # the guest pressed nothing (the harness holds no key there)
    d.check(closed is not None and g_ctl, "W4: the host's Confirm closes both windows; the guest's control comes back",
            f"closed at {closed!r} s after the press; guest control {g_ctl}; guest held {g_pressed}", cid="W4")
    d.check(not plain_seen and not step_seen, "W5: option C keeps the guest (no plain host scene) and the guest never steps out",
            f"host_plain_scene seen {plain_seen}; guest stepout.active seen {step_seen}", cid="W5")
    th = _first_time(hl, LINE_STAMP.format(u=cr.CHEST_UID, f=cr.FIELD))
    tg = _first_time(gl, LINE_ACCEPT.format(u=cr.CHEST_UID, f=cr.FIELD))
    acc_ms = int((tg - th).total_seconds() * 1000) if th is not None and tg is not None else None
    d.check(acc_ms is not None and acc_ms <= ACCEPT_MS, "W6: the guest accepts within 1500 ms of the host's stamp (1 s log grain)",
            f"stamp -> accept {acc_ms!r} ms (whole-second log stamps)", cid="W6")
    d.note(f"Memoria logs: host {cb.archive_log(host, 'chest-duo-host')}, guest {cb.archive_log(guest, 'chest-duo-guest')}")
