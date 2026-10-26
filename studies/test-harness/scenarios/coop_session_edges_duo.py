"""s153 -- THE SESSION-EDGE ROUND, the TWO-GAME bench (tools/harness/duo.py; studies/coop-review/REVIEW.md section 1).

Two real FF9s on this desktop, paired over the sittings' own bridge + relay path (topology "bridge" -- the one the
suppression defect lives on). Each leg is one fix's own in-game check:

  D1  fix 6, a host never follows: the HOST's FollowHost=1 (a stale or copied guest line) is logged as ignored, and when the
      guest stands on another field the host stays where it is. Pre-s153 the host follow-warped its own save after 1.2 s.
  D2  fix 2, the session-over diorama leave: the host fights, the guest's diorama goes LIVE, then the GUEST turns co-op
      off (Enabled=0, hot-reloaded). Green = "diorama LEAVE: the co-op session is over (co-op disabled)" and the guest back
      on a field. Pre-s153 every diorama exit sat behind the enabled gate: the guest stayed in the frozen battle.
  D3  fix 1, the suppression after the host quits: re-paired, the host's game QUITS (its bridge leg goes; the guest's
      loopback hop to its own bridge stays up). Green = the guest's exit ramp, then "encounter pause OFF". Pre-s153 the
      pause keyed on IsConnected (the loopback hop) and stayed ON for the rest of the guest's solo play.

    py tools/harness/duo.py studies/test-harness/scenarios/coop_session_edges_duo.py

Prereqs as duo.py's (both roots built, no FF9 from either, no controller, nobody at the keyboard). The guest's
SessionGraceMs is the minimum (5 s) so D3 does not wait 40 s.
"""
from __future__ import annotations

import datetime as _dt
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
from harness.duo import hits                                       # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                          # noqa: E402 - try_ns for the ~ leave

SCENE = 67                     # BSC_EF_R007, one Goblin (duo.py's BENCH_SCENE)
AWAY_FIELD = 30602             # LOCKT2 in the -msgs folder: registered on both roots, walkable

MINE = {
    "follow_ignored": re.compile(r"^\[NetSync\] FollowHost=1 ignored: this machine is the HOST"),
    "session_leave": re.compile(r"^\[NetSync\] diorama LEAVE: the co-op session is over \((.+)\)$"),
    "pause": re.compile(r"^\[NetSync\] encounter pause (ON|OFF)\b"),
    "ramp": re.compile(r"^\[NetSync\] session ended -> reloading own autosave \(Continue\)$"),
    "ramp_failed": re.compile(r"^\[NetSync\] session ended, no autosave to resume -> title screen$"),
    "paired": re.compile(r"^\[NetSync\] paired on the host's field \((\d+)\)"),
    "armed": re.compile(r"^\[NetSync\] state-mirror ARMED"),
    "live": re.compile(r"^\[NetSync\] diorama LIVE "),
    "relay_up": re.compile(r"^\[NetSync\] relay connected "),
}

#: duo.py calls d.pair(**PAIR): the guest's grace at its clamp floor (NetSyncClient.ParseSessionGrace: 5000-40000).
PAIR = {"role_extra": {"guest": {"SessionGraceMs": "5000"}}}


def _wait(d, role, name, timeout, *, after=None, pred=None):
    deadline = time.time() + timeout
    while True:
        found = hits(d.lines(role), name, after=after, pred=pred, matchers=MINE)
        if found or time.time() >= deadline:
            return found
        time.sleep(0.25)


def _show(found, n=2):
    return " || ".join(m.group(0) for _t, _l, m in found[-n:]) if found else "none"


def run_duo(d) -> None:
    _d2_session_over_leave(d)          # first: it needs the pairing PAIR built (a following, mirroring guest)
    _d1_host_never_follows(d)          # then: the guest re-enabled NOT following, so it stays where it is put
    _d3_suppression_after_host_quits(d)


def _leave_if_stuck(d):
    """A pre-s153 guest stays frozen in the diorama after co-op is turned off (D2's red): leave it the ~ menu's way so the
    calibration run still reaches D1 and D3."""
    try:
        if d.guest.state.ui_state == "BattleHUD":
            d.note("the guest is still in the battle scene -- `netsync dioleave` (the ~ menu's Leave) so the run goes on")
            cb.try_ns(d.guest, "dioleave")
            deadline = time.time() + 30.0
            while time.time() < deadline and d.guest.state.ui_state == "BattleHUD":
                time.sleep(0.3)
    except Exception as err:                                # noqa: BLE001
        d.note(f"dioleave: {err}")


def _d2_session_over_leave(d):
    at = _dt.datetime.now() - _dt.timedelta(seconds=1)
    d.host.start_battle(SCENE, group=-1, rand=False)
    live = _wait(d, "guest", "live", 40.0, after=at)
    d.check(bool(live), "D2-pre: the guest's diorama is LIVE on the host's battle", _show(live), role="guest", cid="D2-pre")
    if live:
        at = _dt.datetime.now() - _dt.timedelta(seconds=1)
        d.set_netsync("guest", {"Enabled": "0"}, timeout=3.0)      # its echo reads enabled=False: no match is expected
        left = _wait(d, "guest", "session_leave", 15.0, after=at)
        d.check(bool(left) and "co-op disabled" in _show(left), "D2a: the guest's diorama leaves: the session is over",
                _show(left), role="guest", cid="D2a")
        deadline = time.time() + 30.0
        ui = None
        while time.time() < deadline:
            try:
                ui = d.guest.state.ui_state
            except Exception:                              # noqa: BLE001
                ui = None
            if ui in ("FieldHUD", "Title", "WorldHUD"):
                break
            time.sleep(0.3)
        d.check(ui in ("FieldHUD", "Title", "WorldHUD"), "D2b: the guest is out of the battle scene", f"ui_state {ui!r}",
                role="guest", cid="D2b")
        _leave_if_stuck(d)
    try:
        d.host.fight(timeout=180.0)                         # the host's own fight ends normally (Zidane vs one Goblin)
    except Exception as err:                                # noqa: BLE001 - the next legs judge the pairing they get
        d.note(f"host fight: {err}")


def _seat_guest(d, field):
    g = d.guest
    try:
        if g.state.ui_state == "Title":
            g.newgame()
        if g.state.field_id != field:
            g.warp(field)
    except Exception as err:                                # noqa: BLE001
        d.note(f"guest re-seat on {field}: {err}")


def _d1_host_never_follows(d):
    # the guest, back on its own save after D2's ramp, re-enabled NOT following and put on another field: it stays there, so
    # a host that followed would have every second it needs (a following guest pulled itself back before an old host's
    # 1.2 s debounce ran out -- the first calibration's D1b was green on pre-s153 for that reason)
    at = _dt.datetime.now() - _dt.timedelta(seconds=1)
    _seat_guest(d, AWAY_FIELD)
    d.set_netsync("guest", {"Enabled": "1", "FollowHost": "0"}, timeout=15.0)
    connected = _wait(d, "guest", "relay_up", 30.0, after=at)
    d.note("D1: guest connected, not following: " + _show(connected))
    host_field = d.host.state.field_id
    at = _dt.datetime.now() - _dt.timedelta(seconds=1)
    d.set_netsync("host", {"FollowHost": "1"}, timeout=8.0)
    found = _wait(d, "host", "follow_ignored", 10.0, after=at)
    d.check(bool(found), "D1a: the host logs its FollowHost=1 as ignored", _show(found), role="host", cid="D1a")
    seen = set()
    deadline = time.time() + 10.0
    while time.time() < deadline:
        try:
            seen.add(d.host.state.field_id)
        except Exception:                                  # noqa: BLE001 - a load in flight reads as no field
            pass
        time.sleep(0.2)
    d.check(seen <= {host_field}, f"D1b: the host stayed on {host_field} while the guest stood on {AWAY_FIELD}",
            f"host fields seen {sorted(seen)}; guest on {d.guest.state.field_id}", role="host", cid="D1b")
    d.set_netsync("host", {"FollowHost": "0"}, timeout=8.0)
    if d.host.state.field_id != host_field:
        d.host.warp(host_field)                             # a pre-s153 host followed: put it back for D3


def _d3_suppression_after_host_quits(d):
    at = _dt.datetime.now() - _dt.timedelta(seconds=1)
    d.set_netsync("guest", {"FollowHost": "1"}, timeout=15.0)     # follow again: the guest warps to the host and re-arms
    armed = _wait(d, "guest", "armed", 60.0, after=at)
    on = _wait(d, "guest", "pause", 10.0, after=at, pred=lambda m: m.group(1) == "ON")
    d.check(bool(armed) and bool(on), "D3-pre: re-paired and mirroring, the guest's encounter pause ON",
            f"armed {_show(armed)}; pause {_show(on)}", role="guest", cid="D3-pre")
    if not armed:
        return
    at = _dt.datetime.now() - _dt.timedelta(seconds=1)
    d.host.quit(timeout=30.0)
    ramp = _wait(d, "guest", "ramp", 60.0, after=at) or _wait(d, "guest", "ramp_failed", 1.0, after=at)
    off = _wait(d, "guest", "pause", 20.0, after=at, pred=lambda m: m.group(1) == "OFF")
    d.check(bool(ramp), "D3a: the host quit ends the guest's session (the exit ramp)", _show(ramp), role="guest", cid="D3a")
    d.check(bool(off), "D3b: the guest's encounter pause goes OFF with no live host (its bridge hop still up)",
            _show(off), role="guest", cid="D3b")
