"""s161 -- THE ATE RELAY, the TWO-GAME bench (tools/harness/duo.py; studies/field-coop/ATE-RELAY.md). [ff9mapkit netsync s161]
[ff9mapkit netsync s162] + THE LANDING START (GUEST-TRAVERSAL-TWO-PC.md Finding 9): rows D10-D12, D8's hub slice, the calibrations.

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
  D8      no guest step-out OUT while an ATE caption was up on the guest (the solo S1, on a client). [ff9mapkit netsync s162] THE
          HUB SLICE: from the press to the FIRST of the guest's 'my copy's own Field(350) landed' and its 'Map: 350' (s162's landing
          OUT comes right after the landed line and can precede 'Map: 350', logged at LateUpdate) -- the menu and the title only.
  D9      THE HOST HALF of the caption exemption: sampled on the host while its menu is up and again while its title card is up,
          `netsync.stepout.host_plain_scene` reads false (option C does not hide the guest's ghost over the relay's own captions) and,
          while the menu is up, `netsync.ate.stepout_exempt` reads true (the positive control: the latch is set). A missing sample is
          red.
  D10     [ff9mapkit netsync s162] THE LANDING START on the guest (the solo S-LAND, on a client): after its 'my copy's own Field(350)
          landed' and before its 'win 4 text 321 opened locked', ONE 'step-out: OUT on field 350 (...) -- ate' (the first OUT on 350),
          and the guest's `stepout.out_why.ate` rose over the run (an absent key is red).
  D11     [ff9mapkit netsync s162] THE HOST'S SCREEN: every distinct host frame is read from the title's close (not from the moment
          the bench sees the guest's landed line -- a late log flush must not empty the window) until WATCH_TAIL_S after the guest's
          first ATE line, and judged on 350 only. Every sample that drives the guest's ghost (`stepout.ghost.hide` non-null) hides it
          FOR THE GUEST'S ZERO WIRE MASK ('mask0' -- not the host's own option C, 'host_scene', which only rises on the host's own
          line), no sample shows it (`dress.ghost.shown_mask` > 0), and at least MIN_DRIVEN samples drove it (else vacuous: red). The
          guest's landed line must have been seen (the gate: else no landing happened, red).
  D12     [ff9mapkit netsync s162] THE GUEST'S SCREEN, D11's mirror: the guest's own frames over the same window, judged on 350.
          Every sample that drives the host's ghost hides it by 'landing' (the landing term, before the step-out's base holds) or
          'step_out' (the episode, once it does), none shows it, at least MIN_DRIVEN drove it. The guest's paired block runs only
          with its body bound on the host's field (else the ghost is despawned: hide null, not judged).

THE CALIBRATION (COOP_CALIBRATE=1): run on the s160 DLL (no `netsync.ate`). PREDICTED_S160 = D1, D2, D3, D4, D7, D9 red. D5 is green
there too (the FOLLOW lands the guest on 350 with the host's entrance, as on 2026-10-28). D6 and D8 are maybes: at 1x the follow
may land the guest early enough to show some closing lines, and with no menu on the guest there is no caption to step out on. A
red outside those voids the run. [ff9mapkit netsync s162] + D10, D11 and D12 (no own-jump landing: the guest never logs one).
[ff9mapkit netsync s162] COOP_CALIBRATE=s161: run on the s161 DLL. PREDICTED_S161 = D10, D11, D12 red (no `out_why.ate`, the OUT
waits for 321's line; until then the guest's wire mask is non-zero, so the host's ghost of it is SHOWN or hidden only by the host's
own option C, never 'mask0' -- and the guest's GhostHide sees the host's non-zero mask with no step-out, so it SHOWS the host's
ghost); D1-D9 stay green (s161's own 22/22, D8 on the hub slice).
[ff9mapkit netsync s162] COOP_CALIBRATE=noland is REFUSED AT LOAD, before the pair boots: `stepout noland` is a SELFTEST-ROLE lever
(NetSyncStepOut.LeverNoLand reads IsSelfTestRole) and the duo's guest is a CLIENT, so it could never be taken -- the duo calibrates
s162 by DLL swap (COOP_CALIBRATE=s161); the solo bench carries the noland lever.

    py tools/harness/duo.py studies/test-harness/scenarios/coop_ate_relay_duo.py
    COOP_CALIBRATE=1 py tools/harness/duo.py studies/test-harness/scenarios/coop_ate_relay_duo.py     (on the s160 DLL)
    COOP_CALIBRATE=s161 py tools/harness/duo.py studies/test-harness/scenarios/coop_ate_relay_duo.py  (on the s161 DLL)

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
import coop_ate_relay as solo                                      # noqa: E402 - [s162] the landing's shared log judge
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
LAND_WATCH_S = JUMP_S + 8.0              # [ff9mapkit netsync s162] the title's close to the guest's first ATE line
#: [ff9mapkit netsync s162] D11/D12's window runs this long past the guest's first ATE line: long enough for MIN_DRIVEN samples when
#: the host loads 350 late (a longer tail never hides a red: the window's START is the title's close, and every sample is judged)
WATCH_TAIL_S = 2.0
MIN_DRIVEN = 3                           # [ff9mapkit netsync s162] D11 / D12 need this many samples that drove the peer's ghost
HOST_HIDES = ("mask0",)                  # [ff9mapkit netsync s162] D11: the guest's zero wire mask, never the host's option C
GUEST_HIDES = ("landing", "step_out")    # [ff9mapkit netsync s162] D12: the landing term, then the episode

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
    "D10": "THE LANDING START on the guest (s162): one 'step-out: OUT on field 350 (...) -- ate' after its landed line and before "
           "its 321 (the first OUT on 350); its stepout.out_why.ate rose",
    "D11": "THE HOST'S SCREEN from the title's close to 2 s past the guest's first ATE line (the guest's landing seen): every host "
           "sample on 350 that drives the guest's ghost hides it by the guest's zero wire mask ('mask0'), none shows it, at least 3 "
           "drove it",
    "D12": "THE GUEST'S SCREEN over the same window: every guest sample on 350 that drives the host's ghost hides it by 'landing' "
           "or 'step_out', none shows it, at least 3 drove it",
}
PREDICTED_S160 = ("D1", "D2", "D3", "D4", "D7", "D9",
                  "D10", "D11", "D12")              # [ff9mapkit netsync s162] no own-jump landing on s160
MAYBE_S160 = ("D6", "D8")
PREDICTED_S161 = ("D10", "D11", "D12")              # [ff9mapkit netsync s162] the s161 DLL
CAL_ID = "D-CAL"
#: [ff9mapkit netsync s162] COOP_CALIBRATE's values: None (no calibration), "s160" (1 or anything else: the s160 DLL), "s161" (the
#: s161 DLL); "noland" is refused at load (calibration())
CAL_PREDICTED = {"s160": (PREDICTED_S160, MAYBE_S160), "s161": (PREDICTED_S161, ())}
NOLAND_REFUSAL = ("coop_ate_relay_duo: COOP_CALIBRATE=noland is refused -- `stepout noland` is a selftest-role lever and the duo's "
                  "guest is a client, so the engine could never take it. Calibrate s162 on the duo with COOP_CALIBRATE=s161 on the "
                  "swapped-in s161 DLL; the solo bench (coop_ate_relay.py) carries the noland lever.")


def calibration() -> str | None:
    v = os.environ.get("COOP_CALIBRATE", "").strip().lower()
    if v in ("", "0"):
        return None
    if v == "noland":                                   # [ff9mapkit netsync s162] at load: before duo.py boots the pair
        raise SystemExit(NOLAND_REFUSAL)
    return v if v == "s161" else "s160"


CAL_MODE = calibration()


def catalog(calibrate) -> dict:
    """``calibrate``: a CAL_PREDICTED mode, or True (the s160 run, as before s162), or falsy."""
    cat = dict(CLAIMS)
    mode = "s160" if calibrate is True else calibrate
    if mode:
        predicted, maybe = CAL_PREDICTED[mode]
        what = {"s160": "the s160 calibration", "s161": "the s161 calibration (the s161 DLL)"}[mode]
        cat[CAL_ID] = f"{what}: exactly " + ", ".join(predicted) + " red" + (" (maybe " + ", ".join(maybe) + ")" if maybe else "")
    return cat


def judge_ghost(samples, t_land, t_first, allowed, who: str) -> tuple:
    """[ff9mapkit netsync s162] D11 / D12 (PURE): ``samples`` = one game's distinct frames from the title's close
    ({t, field, hide, shown, plain}, ``t`` in seconds since the close); ``t_land`` / ``t_first`` = when the guest's landed / first
    ATE line was seen (same clock; None = never). Judged: the samples on 350 up to WATCH_TAIL_S past the first line. Green only when
    the landing was seen, the window ran through the first line, at least MIN_DRIVEN of them drove the peer's ghost, every one hid it
    by a reason in ``allowed``, and none showed it."""
    if t_land is None:
        return False, "the guest never logged its landing: no window"
    if t_first is None:
        return False, f"the guest's first ATE line never came: the window ({len(samples)} {who} samples) did not run through it"
    end = t_first + WATCH_TAIL_S
    win = [x for x in samples if x.get("field") == DEST and x.get("t", 0.0) <= end]
    driven = [x for x in win if x.get("hide") is not None]
    shown = [x for x in win if isinstance(x.get("shown"), int) and not isinstance(x.get("shown"), bool) and x["shown"] > 0]
    wrong = [x for x in driven if x.get("hide") not in allowed]
    hides = sorted({str(x.get("hide")) for x in win})
    ok = len(driven) >= MIN_DRIVEN and not shown and not wrong
    first_bad = (wrong or shown or [None])[0]
    return ok, (f"{len(win)} {who} samples on {DEST} up to {end:.2f} s after the title's close (landing seen at {t_land:.2f} s, "
                f"first line at {t_first:.2f} s), {len(driven)} drove the ghost (want >= {MIN_DRIVEN}), {len(wrong)} not "
                f"{'/'.join(allowed)}, {len(shown)} SHOWN; hides seen {hides}"
                + (f"; first bad at +{first_bad.get('t', 0.0):.2f} s: {first_bad}" if first_bad else ""))


def judge_host_ghost(samples, t_land, t_first) -> tuple:
    """[ff9mapkit netsync s162] D11: the host's screen -- the guest's ghost hidden by the guest's zero wire mask only."""
    return judge_ghost(samples, t_land, t_first, HOST_HIDES, "host")


def judge_guest_ghost(samples, t_land, t_first) -> tuple:
    """[ff9mapkit netsync s162] D12: the guest's screen -- the host's ghost hidden by the landing term or the episode."""
    return judge_ghost(samples, t_land, t_first, GUEST_HIDES, "guest")


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


def _ghost_read(st, t: float) -> dict:
    return {"t": t, "field": st.field_id, "hide": cb.path(st, "netsync.stepout.ghost.hide"),
            "shown": cb.path(st, "netsync.dress.ghost.shown_mask"), "plain": cb.path(st, "netsync.stepout.host_plain_scene")}


def _landing_watch(d, host, guest, g1: int, timeout: float) -> dict:
    """[ff9mapkit netsync s162] From the title's close: read every distinct HOST and GUEST frame (field, `stepout.ghost.hide`,
    `dress.ghost.shown_mask`, `host_plain_scene`), each stamped with its seconds since the close, and poll the guest's log for its
    landed line and its first ATE line (same clock); stop WATCH_TAIL_S past the first ATE line or at ``timeout``. Sampling from the
    close, not from the landed line, keeps a late log flush from emptying the window."""
    out = {"t_land": None, "t_first": None, "host": [], "guest": []}
    t0 = time.time()
    deadline = t0 + timeout
    seen = {"host": None, "guest": None}
    stop = None
    while time.time() < deadline:
        now = time.time()
        for role, g in (("host", host), ("guest", guest)):
            st = g.state
            if st.frame != seen[role]:
                seen[role] = st.frame
                out[role].append(_ghost_read(st, now - t0))
        gm = _msgs(d, "guest", g1)
        if out["t_land"] is None and _count(gm, solo.LANDED) > 0:
            out["t_land"] = now - t0
        if out["t_land"] is not None and out["t_first"] is None and _count(gm, solo.FIRST_LINE_LOCKED) > 0:
            out["t_first"] = now - t0
            stop = now + WATCH_TAIL_S
        if stop is not None and now >= stop:
            break
        time.sleep(0.02)
    return out


def run_duo(d) -> None:
    led = cb.Ledger(_DuoG(d), catalog(CAL_MODE), finals=(CAL_ID,) if CAL_MODE else (), width=1400)
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
        if CAL_MODE:
            led.close("not reached: the run ended before this check")
            predicted, maybe = CAL_PREDICTED[CAL_MODE]
            led.judge_calibration(CAL_ID, predicted, maybe=maybe)
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
    ate0 = cb.path(guest.state, "netsync.stepout.out_why.ate")    # [ff9mapkit netsync s162] D10's baseline (None: s161 or older)

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
    # ---- D4/D5: both to 350 -- [ff9mapkit netsync s162] both games' views of the peer's ghost, read from the title's close (D11/D12)
    watch = _landing_watch(d, host, guest, g1, LAND_WATCH_S)
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
    # D8 reads the guest's log from the press to the landing on 350 (the menu and the title are the only captions there) --
    # [ff9mapkit netsync s162] the HUB SLICE: up to the FIRST of the landed line and 'Map: 350' (the landing's OUT follows the former)
    land = solo.hub_end(gm)
    led.check("D8", _count(gm[:land], "step-out: OUT on field") == 0, _grep(gm[:land], "step-out", limit=300))
    # [ff9mapkit netsync s162] D10: the guest's landing OUT by `ate`, between its landed line and its first ATE line; its counter
    ok10, parts10, reasons = solo.landing_out(gm)
    rose, top = solo.counter_rose(ate0, [guest.state], "netsync.stepout.out_why.ate")
    parts10 = parts10 + [("out_why.ate rose", rose)]
    led.check("D10", ok10 and rose, ", ".join(f"{k} {'ok' if v else 'NO'}" for k, v in parts10)
              + f"; OUTs on {DEST} {reasons}; out_why.ate {ate0!r} -> {top!r}; {_grep(gm, 'landed', 'step-out', 'text 321', limit=500)}")
    # [ff9mapkit netsync s162] D11: the host's screen from the guest's landing through its first ATE line
    ok11, why11 = judge_host_ghost(watch["host"], watch["t_land"], watch["t_first"])
    led.check("D11", ok11, why11)
    # [ff9mapkit netsync s162] D12: the guest's screen over the same window
    ok12, why12 = judge_guest_ghost(watch["guest"], watch["t_land"], watch["t_first"])
    led.check("D12", ok12, why12)

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
