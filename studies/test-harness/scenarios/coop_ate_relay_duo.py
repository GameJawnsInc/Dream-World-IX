"""s161 -- THE ATE RELAY, the TWO-GAME bench (tools/harness/duo.py; studies/field-coop/ATE-RELAY.md). [ff9mapkit netsync s161]

Two real FF9s on this desktop, paired by duo.py (the guest FOLLOWING, its state mirror ARMED). The solo bench (coop_ate_relay.py)
proves the relay, the serve, the lock's pick and the own jump on the selftest role; it cannot reach the GUEST TRANSPORT. This bench
plays the owner's two-PC check end to end with a real host and a real client: 352's "Vivi, Confused" ATE, the host's own menu, the
title card and white fade on BOTH copies, the guest's own Field(350) with the follow held, the ATE on 350, its closing lines (324,
325, 324) on the guest, and the guest's own way back to 352 with the follow held again.

THE SETUP. Paired on 250; the host warps to 352 (entrance 0, scenario 2600) and the guest follows. 352's own load CLEARS the gate
(Zidane_Init writes byte 238 = 0 and word 241 = 0 when no ATE is unlocked: a New Game's VARL bits), so the gate is poked AFTER both
copies settle -- the guest first, the host last, right before its press: byte 238 = 1, word 241 = 2 (the "Vivi, Confused" row).
Nothing on an idle 352 rewrites them (the other writes are scripted event cases). Both copies watch bytes 238, 241 and 242 (the
watch adds to duo.py's marker watch). The host is driven at 1x: it presses Select, picks the row, closes the title, then pages
every line on 350 as soon as it is ready.

  D0      both on 352 with control (the guest by ONE follow); the host's own 238 read 0 after its load (the instrument: the load did
          wipe it), and after the pokes both copies read 238 = 1, 241 = 2, 242 = 0.
  D1      THE MENU: the host's 'ATE relay: my ATE menu (win 1 text 98) opened from uid U's Select -- relayed (seq S)'; the guest's
          'opened my copy's ATE menu (win 1 text 98' and 'win 1 text 98 opened locked'.
  D2      THE PICK: the guest's 'win 1 text 98 closed (host seq N, choice 1)' and 'the host's choice 1 closed my copy's ATE menu'.
  D3      THE TITLE: the guest's 'win 0 text 100 opened locked' and 'win 0 text 100 closed (host seq'.
  D4      THE OWN JUMP: the guest's 'my copy's own Field(350) passes', no 'intent: following the peer to field 350', no
          'following the peer to field 350', no bounce line, ONE 'Map: 350' after the pick.
  D5      THE ATE ON 350: the guest's 'win 4 text 321 opened locked' (the copy plays it, entrance 16).
  D6      THE CLOSING LINES: the guest opened 324 and 325 locked and the host's events closed them (the 2026-10-28 session
          dropped all three).
  D7      THE WAY BACK: the guest's 'the follow to field 352 waits -- my copy still plays the ATE', no follow to 352 fired, ONE
          'Map: 352' after the ATE, the episode over on the landing.
  D8      no guest step-out OUT while an ATE caption was up on the guest (the solo S1, on a client).
  D9      THE HOST HALF of the caption exemption: sampled on the host while its menu is up and again while its title card is up,
          `netsync.stepout.host_plain_scene` reads false (option C does not hide the guest's ghost over the relay's own captions) and,
          while the menu is up, `netsync.ate.stepout_exempt` reads true (the positive control: the latch is set). A missing sample is
          red.

THE CALIBRATION (COOP_CALIBRATE=1): run on the s160 DLL (no `netsync.ate`). PREDICTED_S160 = D1, D2, D3, D4, D7, D9 red. D5 is green
there too (the FOLLOW lands the guest on 350 with the host's entrance, as on 2026-10-28). D6 and D8 are maybes: at 1x the follow
may land the guest early enough to show some closing lines, and with no menu on the guest there is no caption to step out on. A
red outside those voids the run.

    py tools/harness/duo.py studies/test-harness/scenarios/coop_ate_relay_duo.py
    COOP_CALIBRATE=1 py tools/harness/duo.py studies/test-harness/scenarios/coop_ate_relay_duo.py     (on the s160 DLL)

Prereqs as duo.py's: no FF9 running from either root, no controller connected, nobody at the keyboard (THE UNATTENDED LAW).
NOT PROVEN HERE: a same-field ATE (no bench field carries one with a reachable gate); the host faster than 1x (Finding 4's rate).
"""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                          # noqa: E402 - Ledger, CALIBRATE
from harness import duo as duo_mod                                 # noqa: E402 - watched_byte

HarnessError = cb.HarnessError
CALIBRATE = cb.CALIBRATE

HUB, DEST, SCENARIO = 352, 350, 2600
B_AVAIL, B_ROWS_LO, B_ROWS_HI, ROWS = 238, 241, 242, 2
PICK = 1
ARRIVE_S = 30.0
MENU_S = 5.0
JUMP_S = 20.0
ATE_S = 150.0                            # the whole ATE on 350 at 1x, paged as fast as the host's lines allow
BACK_S = 25.0

CLAIMS = {
    "D0": "both on 352 with control (the guest by ONE follow), the gate bytes equal on both",
    "D1": "the host relayed its own ATE menu's press and the guest's copy opened its menu locked",
    "D2": "the guest's lock closed the menu on the host's choice 1 and the relay noted it",
    "D3": "the guest's title card (text 100) opened locked and closed on the host's event",
    "D4": "the guest's own Field(350) passed: no follow to 350, no bounce, one load of 350",
    "D5": "the guest's copy played the ATE on 350 (win 4 text 321 opened locked)",
    "D6": "the guest showed the ATE's closing lines (324 and 325 opened locked, closed by the host's events)",
    "D7": "the guest went back to 352 by its own Field(): the follow waited, none fired, one load of 352",
    "D8": "no guest step-out OUT while an ATE caption was up on the guest",
    "D9": "the host's option C keeps the guest's ghost through its relayed menu and title (host_plain_scene false; the host's "
          "ate.stepout_exempt true while the menu is up)",
}
PREDICTED_S160 = ("D1", "D2", "D3", "D4", "D7", "D9")
MAYBE_S160 = ("D6", "D8")
CAL_ID = "D-CAL"


def catalog(calibrate: bool) -> dict:
    cat = dict(CLAIMS)
    if calibrate:
        cat[CAL_ID] = "the s160 calibration: exactly " + ", ".join(PREDICTED_S160) + " red (maybe " + ", ".join(MAYBE_S160) + ")"
    return cat


class _DuoG:
    """cb.Ledger's ``g``: each row recorded on the duo (and the guest's report), its id the catalog's."""

    def __init__(self, d):
        self.d = d

    def check(self, ok, what, detail=""):
        return self.d.check(bool(ok), str(what), str(detail), role="guest", cid=str(what).split(":", 1)[0])

    def note(self, msg):
        self.d.note(str(msg))


def _msgs(d, role: str, at: int = 0) -> list:
    return [m for _t, _l, m in d.lines(role)[at:]]


def _count(msgs, needle: str) -> int:
    return sum(1 for m in msgs if needle in m)


def _rx(msgs, pattern: str) -> list:
    rx = re.compile(pattern)
    return [m for m in msgs if rx.search(m)]


def _grep(msgs, *needles, limit: int = 500) -> str:
    return " || ".join(m for m in msgs if any(n in m for n in needles))[:limit]


def _field(g) -> int:
    return g.state.field_id


def _wait(g, pred, timeout: float, what: str):
    return cb.poll(g, pred, timeout, what)


def _settle_on(g, fid: int, timeout: float) -> bool:
    """On `fid` with control and no line open, paging any line on the way in."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = g.state
        if st.field_id == fid and st.control and not st.dialog_open:
            return True
        if st.field_id == fid and st.dialog_open:
            g.press("confirm", 2)
        g.wait_frames(6)
    return False


def _gate(g) -> None:
    g.poke(B_AVAIL, 1)
    g.poke(B_ROWS_LO, ROWS & 0xFF)
    g.poke(B_ROWS_HI, (ROWS >> 8) & 0xFF)


GATE_BYTES = (B_AVAIL, B_ROWS_LO, B_ROWS_HI)


def _watch_gate(g) -> None:
    """Publish bytes 238, 241, 242 in every state sample (the agent's watch ADDS to its list: duo.py's marker watch stays)."""
    g.watch(*(b * 8 + i for b in GATE_BYTES for i in range(8)))


def _gate_reads(g) -> tuple:
    st = g.state
    return tuple(duo_mod.watched_byte(st, b) for b in GATE_BYTES)


def run_duo(d) -> None:
    led = cb.Ledger(_DuoG(d), catalog(CALIBRATE), finals=(CAL_ID,) if CALIBRATE else (), width=1400)
    strict, d.strict = d.strict, False
    try:
        _run(d, led)
    except HarnessError as err:
        d.note(f"the run raised: {str(err)[:400]}")
        led.close(f"not reached: the run raised ({str(err)[:200]})")
    finally:
        try:
            d.note(f"logs archived: {d.archive('ate-relay')}")
        except Exception as err:                            # noqa: BLE001 - teardown must not mask the verdicts
            d.note(f"archive failed: {err}")
        if CALIBRATE:
            led.close("not reached: the run ended before this check")
            led.judge_calibration(CAL_ID, PREDICTED_S160, maybe=MAYBE_S160)
        led.close(final=True)
        d.strict = strict


def _run(d, led) -> None:
    host, guest = d.host, d.guest
    if not cb.has(guest.state, "netsync.ate.opened"):
        d.note("the guest's engine publishes no `netsync.ate` (s161): the s160 run -- every relay row is red by design")

    # ---- D0: both to 352, then the gate (352's own load clears it): the guest first, the host last, right before its press
    for g in (host, guest):
        _watch_gate(g)
    g0, h0 = len(d.lines("guest")), len(d.lines("host"))
    host.warp(HUB, entrance=0, scenario=SCENARIO)
    ok_h = _settle_on(host, HUB, ARRIVE_S)
    ok_g = _settle_on(guest, HUB, ARRIVE_S)
    host_before = _gate_reads(host)[0]                   # the instrument: 352's load wiped the host's 238 (else the gate proves nothing)
    _gate(guest)
    _gate(host)
    want = (1, ROWS & 0xFF, (ROWS >> 8) & 0xFF)
    rh = cb.poll(host, lambda s: tuple(duo_mod.watched_byte(s, b) for b in GATE_BYTES) == want, 3.0, "the host's gate bytes")
    rg = cb.poll(guest, lambda s: tuple(duo_mod.watched_byte(s, b) for b in GATE_BYTES) == want, 3.0, "the guest's gate bytes")
    gm = _msgs(d, "guest", g0)
    loads = _count(gm, f"Map: {HUB} ")
    led.check("D0", ok_h and ok_g and loads == 1 and host_before == 0 and rh is not None and rg is not None,
              f"host on {_field(host)} ctl {host.state.control}, guest on {_field(guest)} ctl {guest.state.control}, guest "
              f"'Map: {HUB}' x{loads}; host 238 after its load {host_before!r}; gate host {_gate_reads(host)} guest "
              f"{_gate_reads(guest)}; {_grep(gm, 'following the peer', 'Map:', limit=300)}")
    if not (ok_h and ok_g):
        raise HarnessError("D0: the pair never settled on 352")

    # ---- D1-D3: the host's menu, its pick, its title
    g1, h1 = len(d.lines("guest")), len(d.lines("host"))
    host.press("select", 2)
    menu = _wait(host, lambda s: s.choice is not None, MENU_S, "the host's ATE menu")
    if menu is None:
        raise HarnessError("D1: the host's ATE menu never opened (the gate bytes?)")
    _wait(guest, lambda s: False, 1.5, "a moment for the guest's copy")    # the relay + the guest's serve
    host_menu = host.state                               # D9: the host's view with its relayed menu up
    landed = host.choose_landed(PICK)
    title = _wait(host, lambda s: s.dialog_open and "Vivi" in (s.text or ""), 5.0, "the host's title card")
    if title is not None:
        host.wait_frames(25)
        host.press("confirm", 4)
    plain_menu = cb.path(host_menu, "netsync.stepout.host_plain_scene")
    plain_title = cb.path(title, "netsync.stepout.host_plain_scene") if title is not None else None
    exempt_menu = cb.path(host_menu, "netsync.ate.stepout_exempt")
    led.check("D9", plain_menu is False and plain_title is False and exempt_menu is True,
              f"host_plain_scene menu {plain_menu!r} title {plain_title!r} (None = no sample); ate.stepout_exempt at the menu "
              f"{exempt_menu!r}")
    # ---- D4/D5: both to 350
    _wait(host, lambda s: s.field_id == DEST, JUMP_S, "the host on 350")
    _wait(guest, lambda s: s.field_id == DEST, JUMP_S, "the guest on 350")
    t_g = time.time() + 8.0
    while time.time() < t_g and _count(_msgs(d, "guest", g1), "win 4 text 321 opened locked") == 0:
        time.sleep(0.25)
    gm, hm = _msgs(d, "guest", g1), _msgs(d, "host", h1)
    relayed = _rx(hm, r"ATE relay: my ATE menu \(win 1 text 98\) opened from uid \d+'s Select -- relayed \(seq \d+\)")
    opened = _rx(gm, r"ATE relay: host seq \d+ opened my copy's ATE menu \(win 1 text 98")
    led.check("D1", len(relayed) == 1 and len(opened) == 1 and _count(gm, "win 1 text 98 opened locked") >= 1,
              f"host relayed {len(relayed)}, guest opened {len(opened)}; {_grep(gm, 'ATE relay', 'text 98', limit=500)}")
    closed = _rx(gm, r"dialogue: win 1 text 98 closed \(host seq \d+, choice %d\)" % PICK)
    led.check("D2", len(closed) == 1 and _count(gm, f"the host's choice {PICK} closed my copy's ATE menu") == 1,
              f"host pick {landed!r}; lock closes {len(closed)}; {_grep(gm, 'text 98', 'choice', limit=400)}")
    led.check("D3", _count(gm, "win 0 text 100 opened locked") >= 1 and len(_rx(gm, r"dialogue: win 0 text 100 closed \(host seq")) == 1,
              _grep(gm, "text 100", limit=400))
    led.check("D4", _count(gm, f"my copy's own Field({DEST}) passes") == 1 and _count(gm, f"following the peer to field {DEST}") == 0
              and _count(gm, "bounced to a reload") == 0 and _count(gm, f"Map: {DEST} ") == 1,
              f"Map: {DEST} x{_count(gm, f'Map: {DEST} ')}; {_grep(gm, 'Field(', 'following the peer', 'bounced', 'waits', limit=500)}")
    led.check("D5", _count(gm, "win 4 text 321 opened locked") >= 1, _grep(gm, "text 321", "Map:", limit=300))
    # D8 reads the guest's log from the press to the landing on 350 (the menu and the title are the only captions there)
    land = next((i for i, m in enumerate(gm) if f"Map: {DEST} " in m), len(gm))
    led.check("D8", _count(gm[:land], "step-out: OUT on field") == 0, _grep(gm[:land], "step-out", limit=300))

    # ---- D6/D7: the host pages the ATE on 350 at 1x; the guest's copy follows the lines and its own way back
    g2 = len(d.lines("guest"))
    deadline = time.time() + ATE_S
    while time.time() < deadline and _field(host) == DEST:
        st = host.state
        if st.dialog_open and st.choice is None:
            host.press("confirm", 2)
        host.wait_frames(8)
    back_h = _settle_on(host, HUB, BACK_S)
    back_g = _wait(guest, lambda s: s.field_id == HUB, BACK_S, "the guest back on 352") is not None
    time.sleep(1.5)
    gm = _msgs(d, "guest", g2)
    t324 = _count(gm, "win 2 text 324 opened locked")
    t325 = _count(gm, "win 2 text 325 opened locked")
    c324 = len(_rx(gm, r"dialogue: win 2 text 324 closed \(host seq"))
    c325 = len(_rx(gm, r"dialogue: win 2 text 325 closed \(host seq"))
    drops = _count(gm, "text 324) dropped") + _count(gm, "text 325) dropped")
    led.check("D6", t324 >= 2 and t325 >= 1 and c324 >= 2 and c325 >= 1 and drops == 0,
              f"324 opened {t324} closed {c324}, 325 opened {t325} closed {c325}, dropped {drops}; "
              f"{_grep(gm, 'text 324', 'text 325', limit=500)}")
    held = _count(gm, f"the follow to field {HUB} waits -- my copy still plays the ATE")
    fired = _count(gm, f"following the peer to field {HUB}")
    led.check("D7", back_h and back_g and held >= 1 and fired == 0 and _count(gm, f"Map: {HUB} ") == 1
              and _count(gm, "ATE relay: episode over") >= 1,
              f"host back {back_h}, guest back {back_g}; holds {held}, follows fired {fired}, Map: {HUB} x{_count(gm, f'Map: {HUB} ')}; "
              f"{_grep(gm, 'waits', 'following the peer', 'episode over', 'Field(', limit=500)}")
