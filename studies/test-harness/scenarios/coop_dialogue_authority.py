"""F3.2 C2 HOST-AUTHORITATIVE DIALOGUE -- the solo benches (s96), run unattended on bench 30801.

THE CONTRACT (`studies/field-coop/F3.2-DESIGN.md` sync_changes S1-S8, s96). A following guest's ETb lines
are LOCKED from the frame they open, at every input seam (keys/pad/turbo, mouse click, drag, cursor
select, the voice auto-dismiss). Only HOST state moves them: the host's events, applied per window key
in host order (never drained, never handed back on a timer), the orphan rule (a line the host provably
lacks auto-closes at reading pace, Cancel else Default), the link reading dead for LinkGraceMs, the
session ending, or the ~ menu panic unlock. It replaces the F3 lockstep (coop_dialogue_lockstep.py,
retired): F3's lock armed only on a MATCHED frame, any flag-0 sample drained the queue, and its 8 s
DialogWaitMs timeout handed the line back to the guest ("local advance restored").

The bench: `netsync selftest 1` forces the selftest role for this process (Memoria.ini untouched), and
`bench 1` + `lock 1` + `hostscene 1` stand in for a live followed session whose host is mid-scene. Under
the bench the player cannot start a talk himself (the F1 spectator gate), so every line under test is
opened the way a guest's lines open: by the HOST's relayed start, `netsync talk <uid>` (F3.1). The uids
and the reference transcripts are learned first from LOCAL talks with every lever off.

WHAT IS PROVEN -- every check an OUTCOME (the window on screen, its text, the published tracker, the
engine's own log line), never an ack. Unless stated, the levers are lock 1 + hostscene 1.
  A11  at selftest start the engine's pure NetSyncDialog.SelfTest (host-scene machine, settle clock,
       orphan step, inbox) logs OK -- once per process, so the WHOLE log is searched.
  A1   lock from open: before any host event the line is `suppress` + windows[].cls "locked" + the
       'following' chip; Confirm x3, a held Confirm (with the turbo key) and two `netsync click`s leave it
       OPEN ON THE SAME TEXT (the behavioural half: keys the old DLL publishes too) and on the same tracked
       page, still locked (the F3.2-key half), with no close of any kind; then injected host advances page it
       exactly once each, and that transcript EQUALS the one the player's own Confirm paged locally. No drag
       or arrow here: on a PLAIN window stock OnDrag and the arrows act on nothing -- a no-op on any engine,
       so they could not fail; A2 carries them, on a choice.
  A1v  vanilla parity -- the same-run CONTROL for A1: `lock 0`, the same relayed line is untracked, not
       suppressed, and one click pages it (stock DialogManager.OnClick); Confirm finishes the transcript.
  A2   choice: two Down presses and a `netsync drag -80` never move a locked menu's SelectChoice (the
       OnItemSelect / OnDrag gates; the highlight re-assert is not published -- the screenshot shows it);
       `netsync choice <WANT>` lands the SAME follow-up window a local choose(<WANT>) leads to. Its same-run
       controls: the reference choose() moved the cursor with Down presses, and the DRAG CONTROL at setup
       moved the unlocked cursor with the same `drag -80`. (`drag 80` is not sent: from the default row 0
       MoveCurrentChoice(-1) clamps, a no-op on any engine.)
  A2b  an out-of-range host index falls back to the menu's DEFAULT (logged once) and lands the default's
       local follow-up. The guest's Down press first is CALIBRATION's DLG-10 discriminator: the old DLL lets
       it move the cursor and its fallback commits the guest's row. Under the F3.2 lock the cursor cannot
       leave the default, so on THIS DLL "the default" and "the guest's cursor" coincide -- this run cannot
       tell them apart, and does not claim to.
  A5   an EARLY choice event: sent the instant the menu window exists (asserted: the last sample before the
       send read it NOT ready) is held through the open, the typewriter and MinShowMs, then applied exactly
       once (no 'did not advance' retry) -- same follow-up as local. This is NOT DLG-7 itself: IsChoiceReady
       rises one frame after AfterShown (Dialog.cs:652, :163-164), long before MinShowMs (350 ms) runs out,
       so the IsChoiceReady gate (NetSyncDialog.cs:590) is never the binding condition here. No solo bench
       reaches it (it needs a choice page with no type animation and MinShowMs 0); the old DLL, too, holds
       such an event to CompleteAnimation.
  A4   per-key FIFO: an event for a key no window has (`unmatched`, win 15 / text 0xFFFF) queued AHEAD of
       the open line's advance blocks nothing -- the line pages, the stranger stays queued. A regression
       check, NOT a calibration discriminator (see CALIBRATION).
  A8   the [NFOC] polled story page: tracked as input-inhibited, `suppress` stays false, the chip is
       'the host is in a scene' (a polled strip is not a conversation), the menu's applied choice event
       left the inbox (a regression guard: this bench never fabricates an event for the page -- memory LAW
       :1369), and the guest's own Confirm still closes it through its script's poll -- judged by the PAGE
       leaving and its 'closed by its own script/timer' line, not by the screen emptying (true today only
       because the bench keeper is a one-pass [[choice]]): the documented C2 gap (the KEY relay is C3).
  A3   no hand-back: with an unmatched event queued the locked menu sits QUIET (no guest input) for 9 s,
       past F3's 8 s DialogWaitMs -- no 'local advance restored' (or any dialogue timeout) in the log, and
       the event still queued; then it holds 10 s more of the guest mashing Confirm -- open (behavioural),
       still tracked locked under an engaged lock (F3.2 keys) -- with `host_settled_ms` -1 throughout. Then
       `hostscene 0`: the line turns 'orphaned' OrphanGraceMs (2 s) later with the 'closing it' chip,
       auto-closes AutoReadMs (2 s) after that on the menu's CANCEL row (Close: no reply window opens),
       one orphan line, orphan_closes +1, and not one input-driven or self-attributed close.
  A6   link dead: `stale 1` keeps the line locked (chip 'link hiccup') until LinkGraceMs (3 s), then
       releases it with one log line; the guest's own Confirm pages it.
  A7   panic unlock: `netsync unlock` drops the lock on this field (one log line) and the guest's own
       Confirm pages the line; a field reload re-arms it (one 're-armed' line) and a relayed line opens
       locked again.
  RESET  `reset` releases the override and every lever (bench, l1, lock, stale) -- a leaked run cannot hand
       the next player a swallowed Confirm.
  A12-lite  with co-op released, a local talk is stock: a click pages, the local transcript, and zero
       [NetSync] log lines meanwhile. (Its "nothing suppressed or locked" is a regression guard only: both
       reads are gated on `enabled`, which RESET already asserted False.)
SKIPPED, because a solo bench on 30801 cannot reach them: A9 (needs a field with an ATE gate and a scripted
Party()), A10 (needs a voiced field with AutoDismissDialogAfterCompletion), and A12's real half (Enabled=0
FROM LAUNCH -- zero [NetSync] lines in a whole run -- needs an ini edit, which the shared install forbids;
the two-machine package covers it). Turbo is not discriminating on 30801: the scribe carries [NTUR] and a
choice is turbo-immune, so A1's turbo hold is kept only as a regression step. Mouse HOVER over a choice row
cannot be injected (NGUI OnHover); the drag is the reachable stand-in.

SAME-RUN CONTROLS (why the lock checks can fail on THIS DLL): A1v pages the same line with the same click
and Confirm once the lock is off; the reference choose() at setup moved the menu's cursor with the same Down
presses, and the drag control there moved it with the same `drag -80`; A6 and A7 show the guest's Confirm
paging a line the moment the lock lets go.

CALIBRATION -- a check that cannot fail is not a check. Run once against the pre-F3.2 DLL (the F3 lockstep
build: no `dialogue` key, no lock/hostscene/stale/unlock/click/drag verbs) BEFORE trusting a green run.
COOP_CALIBRATE=1 forces it; an engine whose `netsync` block has no `dialogue` key gets it automatically.
In that mode the scenario spells every lever the OLD way -- the one F3 lever, `l1`, stands for both
`lock` and `hostscene` (it was the lockstep's engage gate); `netsync click` becomes a Confirm press;
`drag`, `stale` and `unlock` have no old equivalent and are skipped -- and runs the SAME assertions.
Expected red on the pre-F3.2 DLL:
  * BEHAVIOURAL (the real calibration -- each of these checks reads only keys and log lines the old DLL
    publishes too, so its red is the old BEHAVIOUR): A1's `suppress` (False: F3 armed on a matched frame)
    and A1's "left open on the same text" (the first local Confirm pages the un-injected line); A2 -- Down
    moves the cursor (no OnItemSelect gate); A2b's follow-up -- the guest's Down moved the cursor and F3's
    out-of-range fallback ('-- local default') committed it (OnKeyConfirm: IndexOf(ActiveButton)), so the
    guest's row's window opens, not the default's; A3's quiet phase -- F3's 8 s DialogWaitMs logs 'dialog
    frame ... timed out -- local advance restored' for the held-unmatched frame; A3's hold -- the first
    local Confirm closes the menu (that frame was never suppressed).
  * KEY-ABSENT (they fail, but that proves nothing about their teeth -- the same-run controls above do):
    the contract and default-gates checks, A11, every windows/inbox/chip/orphan/host_settled check and
    every apply/queue log line (F3 logged neither 'win N text T advanced (host seq' nor 'host seq N
    queued') in A1-A8 -- A4 and A5 included, A6/A7 (no old lever), RESET's lock/stale.
  * NOT discriminating: A1v and A12-lite (vanilla behaves the same on both), A2's choice landing, A5's
    landing, A4's paging, and A1's "the click seam was exercised". A4: the old bench inject wrote straight
    into F3's one-slot holder (`_dialogPending = body`), so `advance` REPLACED the held `unmatched` and
    applied -- on the bench the old engine never head-of-line-blocked (only its socket FIFO could, which a
    solo bench cannot reach), and the line pages on both DLLs. The click: in this mode a click IS a Confirm
    press; the check exists for the new DLL -- on an install with `[Control] DisableMouseForMenus` on,
    `netsync click` is refused, and A1, A1v and A12 then fail and NAME the refusal instead of passing
    without ever clicking.
On the NEW DLL in calibration mode (COOP_CALIBRATE=1 forced) A1 must ALSO fail -- `l1` alone engages no
lock there -- which proves the mode really runs the old procedure.

Bench 30801 (the journal dashboard): the scribe (a plain [NTUR] window) stands west, reached from
(-210, -837); the keeper (the 15-option journal menu: row 0 the [NFOC] polled story page, `Close` last
and the CANCEL row) stands east, reached from (210, -837).

    py tools/play.py studies/test-harness/scenarios/coop_dialogue_authority.py --field 30801
    COOP_CALIBRATE=1 py tools/play.py studies/test-harness/scenarios/coop_dialogue_authority.py --field 30801
"""
from __future__ import annotations

import os
import re
import time
from types import SimpleNamespace

try:                                     # play.py puts tools/ on sys.path before it loads a scenario
    from harness import HarnessError
except ImportError:                      # pragma: no cover - imported outside the driver (py_compile, a stub)
    HarnessError = RuntimeError          # HarnessError IS a RuntimeError

FIELD = 30801
WEST = (-210.0, -837.0)         # beside the scribe: a plain window
EAST = (210.0, -837.0)          # beside the keeper: the journal menu
WANT = "Tetra Master"           # a named option, so the index is the engine's own, not our arithmetic
STORY = "Story & treasure"      # row 0: the [NTUR][NFOC] WindowAsync + B_KEYON polled page
CLOSE = "Close"                 # the last row = the engine's CANCEL row (content/choice.py); no reply
MAX_PAGES = 14
IGNORES_INPUT = ("[NFOC]", "[TIME=")    # the tags that set Dialog.ignoreInputFlag / FlagButtonInh
CHOICE_GROUP = "Dialog.Choice"          # Session.CHOICE_GROUP: the dialog's own button group is active

# NetSyncDialog.cs -- the clocks the timed checks are judged against (wall-clock: Environment.TickCount)
LINK_GRACE_S = 3.0              # LinkGraceMs
ORPHAN_GRACE_S = 2.0            # OrphanGraceMs
AUTO_READ_S = 2.0               # AutoReadMs
QUIET_S = 9.0                   # A3's quiet phase: past F3's DialogWaitMs (8 s), the old hand-back clock --
#                                 and with HOLD_S still inside PendingTtlMs (20 s) when the inbox is read
HOLD_S = 10.0                   # A3: how long an unmatched event + a mashing guest must hold the line
SLACK_S = 0.6                   # an UPPER bound's allowance: one tick at 31 fps + the publish (every 2 frames) + our poll
EARLY_S = 0.08                  # a LOWER bound's allowance: Environment.TickCount's ~16 ms resolution + one frame

CHIP_FOLLOWING = "Co-op: following the host's conversation"
CHIP_CLOSING = "Co-op: this line isn't on the host's screen -- closing it"
CHIP_HICCUP = "Co-op: link hiccup -- holding this conversation for the host"
CHIP_HOST_SCENE = "Co-op: the host is in a scene"

#: COOP_CALIBRATE=1 forces the pre-F3.2 procedure (see the module note); unset, the scenario reads the
#: engine's own `netsync.dialogue` contract tag and falls back to it when the tag is absent.
FORCE_CALIBRATE = os.environ.get("COOP_CALIBRATE", "").strip() not in ("", "0")

_APPLIED = re.compile(r"dialogue: win (\d+) text (\d+) (advanced|closed) \(host seq (\d+)(?:, choice (-?\d+))?\)")
_QUEUED = re.compile(r"dialogue: host seq (\d+) queued \(field (\d+) win (\d+) text (\d+) kind (\d+)")


# ---------------------------------------------------------------------------------------- observing
def _log_lines(g) -> list:
    p = g.engine_log()
    if p is None:
        return []
    try:
        return p.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def _mark(g) -> int:
    return len(_log_lines(g))


def _new(g, mark: int) -> list:
    return _log_lines(g)[mark:]


def _count(lines, needle: str) -> int:
    return sum(1 for ln in lines if needle in ln)


def _grep(lines, *needles, limit: int = 300) -> str:
    return "; ".join(ln for ln in lines if any(n in ln for n in needles))[:limit]


def _applied(lines, win, text) -> list:
    """The apply lines (advanced / closed by a host event) for ONE window key: [(verb, seq, choice)]."""
    out = []
    for ln in lines:
        m = _APPLIED.search(ln)
        if m and int(m.group(1)) == win and int(m.group(2)) == text:
            out.append((m.group(3), int(m.group(4)), None if m.group(5) is None else int(m.group(5))))
    return out


def _ns(st) -> dict:
    return st.netsync or {}


def _wins(st) -> list:
    return _ns(st).get("windows") or []


def _front(st) -> dict | None:
    """The newest tracked line (the tracker appends in open order)."""
    w = _wins(st)
    return w[-1] if w else None


def _heads(st) -> list:
    return (_ns(st).get("inbox") or {}).get("heads") or []


def _key(st):
    w = _front(st)
    return (w["win"], w["text"]) if w else (None, None)


def _ignores_input(st) -> bool:
    return any(tag in raw for raw in st.raw_texts for tag in IGNORES_INPUT)


def _listener(st) -> int:
    return int((st.raw.get("player") or {}).get("listener", -1))


def _choice_ready(s) -> bool:
    return s.choice is not None and s.menu_group in (None, CHOICE_GROUP)


def _poll(g, predicate, timeout: float, what: str):
    """``g.wait_for`` that answers None on a timeout instead of raising: the check that follows carries the
    verdict. A dead game still raises -- the next send asserts the process is alive."""
    try:
        return g.wait_for(predicate, timeout=timeout, what=what)
    except HarnessError:
        return None


def _paged_by(g, act, *, tries: int = 6, frames: int = 12) -> bool:
    """Do ``act`` the way a player does -- repeatedly, reading between -- until the open line pages or closes.
    A line still typewriting eats the first Confirm/click as a fast-forward (Dialog.OnKeyConfirm)."""
    st = g.state
    if not st.dialog_open:
        return False
    first = st.text
    for _ in range(tries):
        act()
        g.wait_frames(frames)
        s = g.state
        if not s.dialog_open or (s.text.strip() and s.text != first):
            return True
    return False


def _follow_up(g, *, timeout: float = 4.0) -> str:
    """The text of the window a closed choice LEADS TO -- waited for, since it opens a beat later (sampling
    the frame the menu closes reads an empty screen: the follow-up is built on a later tick)."""
    if _poll(g, lambda s: s.choice is None, timeout, "the choice menu to close") is None:
        return ""
    st = _poll(g, lambda s: s.dialog_open and bool(s.text.strip()), 3.0, "the follow-up window to open with text")
    return st.text if st is not None else ""


# ------------------------------------------------------------------------------------------- acting
class _Levers:
    """The F3.2 bench levers -- or, in CALIBRATION mode, the pre-F3.2 equivalents (module note): the old
    engine's one lever `l1` was both the host-scene flag and the lockstep's engage gate."""

    def __init__(self, g, legacy: bool):
        self.g, self.legacy = g, legacy

    def lock(self, on: bool) -> None:
        self.g.netsync("l1" if self.legacy else "lock", 1 if on else 0)

    def scene(self, on: bool) -> None:
        self.g.netsync("l1" if self.legacy else "hostscene", 1 if on else 0)

    def stale(self, on: bool) -> None:
        if not self.legacy:              # no old equivalent: F3 had no link-dead lever
            self.g.netsync("stale", 1 if on else 0)

    def unlock(self) -> None:
        if not self.legacy:              # no old equivalent: F3 had no panic unlock
            self.g.netsync("unlock")

    def click(self) -> None:
        if self.legacy:
            self.g.press("confirm", 4)   # F3 had no click verb: its guard's own (keyboard) path
        else:
            self.g.netsync("click")

    def drag(self, dy: int) -> None:
        if not self.legacy:              # no old equivalent
            self.g.netsync("drag", dy)

    def engage(self) -> None:
        """The standard bench: bench + lock + host scene ON."""
        self.g.netsync("bench", 1)
        self.lock(True)
        self.scene(True)
        if not self.legacy:
            _poll(self.g, lambda s: _ns(s).get("lock_engaged") is True, 3.0, "the bench lock to engage")


def _try(g, what: str, fn, *args) -> str | None:
    """One input step of a barrage. A refusal (e.g. `click` with no window left to click) is evidence for
    the check that follows, not a crash of the bench. Returns None when the step ran, else the refusal."""
    try:
        fn(*args)
        return None
    except HarnessError as err:
        g.note(f"{what}: refused -- {str(err)[:160]}")
        return str(err)[:200]


def _click_pages(g, lv) -> tuple[bool, str]:
    """Click the open line the way a player clicks (see _paged_by). (paged, why-not): a refused click -- e.g.
    `[Control] DisableMouseForMenus` on this install -- is named, never read as "the click did nothing"."""
    refused = []

    def act():
        why = _try(g, "click", lv.click)
        if why:
            refused.append(why)
    paged = _paged_by(g, act)
    return paged, ("click refused: " + refused[0]) if refused else ""


def _open_by_relay(g, uid: int, *, choice: bool = False, timeout: float = 6.0):
    """Open a line the way a guest's lines open: the host's relayed start (`netsync talk`), on my copy."""
    g.netsync("talk", uid)
    if choice:
        st = _poll(g, _choice_ready, timeout, f"the relayed start (uid {uid}) to open the menu")
    else:
        st = _poll(g, lambda s: s.dialog_open and bool(s.text.strip()), timeout,
                   f"the relayed start (uid {uid}) to open its window")
    if st is None:
        raise HarnessError(f"the relayed start for uid {uid} opened nothing within {timeout:.0f}s")
    return st


def _tracked(g, *, timeout: float = 2.0):
    """The state once the tracker has registered the open line (one guest tick after it opens)."""
    return _poll(g, lambda s: bool(_wins(s)), timeout, "the tracker to register the open line") or g.state


def _inject_until_closed(g, first_page: str, *, max_pages: int = MAX_PAGES):
    """Drive the open line to its close with injected host ADVANCE events. Returns (pages, injects). Never
    injects into a choice or a script-polled ([NFOC]/[TIME]) window -- no host could emit for one."""
    pages, injects = [first_page], 0
    for _ in range(max_pages):
        before = g.state
        if not before.dialog_open or before.choice is not None or _ignores_input(before):
            break
        g.netsync("advance")
        injects += 1
        last = pages[-1]
        st = _poll(g, lambda s: (not s.dialog_open) or s.choice is not None or (s.text.strip() and s.text != last),
                   6.0, "the injected advance to page or close the line")
        if st is None or not st.dialog_open or st.choice is not None:
            break
        pages.append(st.text)
    return pages, injects


def _clear(g, close_idx: int, *, max_steps: int = 24) -> bool:
    """Clear the screen by the player's OWN input (call with the lock off): the keeper's menu on its Close row,
    anything else -- a plain page, or a polled page whose script closes it -- with Confirm."""
    for _ in range(max_steps):
        st = g.state
        if not st.dialog_open:
            return True
        if _choice_ready(st):
            try:
                g.choose(close_idx)
                continue
            except HarnessError:
                pass
        g.press("confirm", 4)
        g.wait_frames(12)
    return not g.state.dialog_open


def _settle(g, lv: _Levers, c, name: str) -> None:
    """Between benches: the lock OFF (everything local), the screen cleared by the player's own input,
    control back, then the standard bench again -- so the next line opens under a lock that PREDATES it
    (a line already open when the lock rises is marked local, by design)."""
    why = ""
    try:
        if not lv.legacy and _ns(g.state).get("stale"):
            g.netsync("stale", 0)
        lv.lock(False)
        cleared = _clear(g, c.close_idx)
        ctl = _poll(g, lambda s: s.control, 6.0, "control back between benches")
        lv.engage()
        g.wait_frames(10)
        ok = cleared and ctl is not None and not g.state.dialog_open
    except HarnessError as err:
        ok, why = False, str(err)[:300]
    g.check(ok, f"{name}: the screen was cleared and the bench re-engaged for the next bench", why or repr(g.state))


def _phase(g, lv: _Levers, c, name: str, fn, *args) -> None:
    """Run one bench. A refusal or a timeout fails THIS bench (one check), the screen is cleared, and the
    scenario goes on -- calibration mode depends on it: the old engine refuses the new verbs."""
    g.note(name)
    try:
        fn(g, lv, c, *args)
    except HarnessError as err:
        g.state                          # a dead game raises here, out of the bench
        g.check(False, f"{name}: the bench ran to completion", str(err)[:400])
    _settle(g, lv, c, name)


# ------------------------------------------------------------------------------------------ the run
def run(g, field: int = FIELD):
    g.note("F3.2 C2 host-authoritative dialogue: the solo benches (lock from open, per-key apply, orphan, release)")
    g.newgame()
    g.warp(field)
    g.wait_frames(60)
    g.calibrate_axes()

    # ---- the forced selftest role, the contract, A11 ----------------------------------------------------
    st = g.netsync("selftest", 1)
    ns = _ns(st)
    g.check(st.netsync is not None and ns.get("selftest") and ns.get("instance") and ns.get("forced"),
            "the harness forced the selftest role for this process (Memoria.ini untouched)", repr(st.netsync))
    contract = ns.get("dialogue")
    legacy = FORCE_CALIBRATE or contract != "authority"
    g.note(f"mode: {'CALIBRATION (the pre-F3.2 procedure: l1 / Confirm)' if legacy else 'F3.2 (lock/hostscene/click)'}"
           f" -- netsync.dialogue={contract!r}, COOP_CALIBRATE={'1' if FORCE_CALIBRATE else 'unset'}")
    g.check(contract == "authority",
            "the engine publishes the F3.2 dialogue contract (netsync.dialogue == 'authority')", f"dialogue={contract!r}")
    gates = ("bench", "lock", "lock_engaged", "suppress")
    g.check(all(ns.get(k) is False for k in gates),          # PUBLISHED and False: an absent key is not "closed"
            "every dialogue gate is published and closed by default (bench off, lock off, not engaged, no suppress)",
            f"missing={[k for k in gates if k not in ns]} {repr(ns)[:300]}")
    proof = _poll(g, lambda s: _count(_log_lines(g), "dialogue authority selftest:") >= 1, 8.0,
                  "the selftest proof block to log the dialogue authority self-test")
    lines = _log_lines(g)
    g.check(proof is not None and _count(lines, "dialogue authority selftest: OK (") >= 1
            and _count(lines, "dialogue authority selftest: FAIL") == 0,
            "A11: NetSyncDialog.SelfTest logged OK (host-scene machine, settle clock, orphan step, inbox)",
            _grep(lines, "selftest:", limit=400))
    lv = _Levers(g, legacy)

    # ---- the references, measured LOCALLY with every lever off -----------------------------------------
    c = _references(g, lv)
    if c is None:
        return
    lv.engage()
    st = g.state
    g.check(_ns(st).get("lock_engaged") is True and not st.dialog_open,
            "the bench lock engaged with no line open (bench + lock + hostscene)", repr(_ns(st))[:300])

    _phase(g, lv, c, "A1 lock from open", _a1_lock_from_open)
    _phase(g, lv, c, "A1v vanilla parity (lock off)", _a1v_vanilla)
    _phase(g, lv, c, "A2 choice: cursor lock + host pick", _a2_choice)
    _phase(g, lv, c, "A2b out-of-range host pick", _a2b_out_of_range)
    _phase(g, lv, c, "A5 choice event held until IsChoiceReady", _a5_choice_held)
    _phase(g, lv, c, "A4 per-key FIFO", _a4_per_key)
    _phase(g, lv, c, "A8 [NFOC] polled page", _a8_polled_page)
    _phase(g, lv, c, "A3 no hand-back, then the orphan", _a3_no_handback)
    _phase(g, lv, c, "A6 link dead", _a6_link_dead)
    _phase(g, lv, c, "A7 panic unlock", _a7_unlock, field)

    _reset_releases(g, lv)
    _a12_vanilla(g, lv, c)


def _drag_control(g, lv) -> None:
    """A2's drag CONTROL, on the keeper's menu opened LOCALLY (bench and lock off): the same `netsync drag -80` A2
    sends must move an UNLOCKED cursor (DialogManager.OnDrag: dy < -50 -> MoveCurrentChoice(+1)). Without it a drag
    seam that silently did nothing would pass A2's "the drag never moved the locked cursor". Calibration has no drag
    verb (module note): skipped there. Leaves the cursor off the default -- the caller's choose() steers back."""
    if lv.legacy:
        g.note("drag control: skipped (calibration: the pre-F3.2 DLL has no `netsync drag`)")
        return
    st = _poll(g, _choice_ready, 6.0, "the keeper's menu to be ready for the drag control")
    if st is None:
        g.check(False, "drag control: the keeper's menu was ready for it", repr(g.state))
        return
    before = int(st.choice.get("selected", -1))
    active = list(st.choice.get("active") or range(int(st.choice.get("count", 0))))
    pos = active.index(before) if before in active else -1
    if not 0 <= pos < len(active) - 1:
        g.check(False, "drag control: the menu's cursor rests on a row with one below it",
                f"selected={before} active={active}")
        return
    want = active[pos + 1]
    why = _try(g, "drag -80", lv.drag, -80)
    moved = _poll(g, lambda s: s.choice is not None and int(s.choice.get("selected", -1)) != before, 2.0,
                  "the drag to move the unlocked cursor")
    after = int(moved.choice.get("selected", -1)) if moved is not None else before
    g.check(why is None and after == want,
            "drag control: with the lock OFF `netsync drag -80` moved the cursor one row down (A2's drag can fail)",
            why or f"selected {before} -> {after} (want {want})")


def _references(g, lv):
    """Uids, transcripts and follow-ups from LOCAL talks (bench off): the yardsticks every bench compares to."""
    g.walk_to(*WEST, tolerance=45, strict=False)
    opened = g.interact(timeout=6.0)
    if opened is None or opened.choice is not None:
        g.check(False, "the scribe opened a plain window locally", repr(opened))
        return None
    west_uid = _listener(opened)
    g.check(not _ignores_input(opened), "the scribe's window accepts Confirm (no [NFOC]/[TIME])",
            repr(opened.raw_texts)[:200])
    local_pages = list(dict.fromkeys([opened.text] + g.advance(max_pages=MAX_PAGES)))
    g.check(0 <= west_uid < 255 and len(local_pages) >= 1 and not g.state.dialog_open,
            "the scribe's window paged to its close by the player's Confirm (the reference transcript)",
            f"uid={west_uid}; {len(local_pages)} page(s): {local_pages[0][:50]!r}")
    g.wait_for(lambda s: s.control, timeout=6.0, what="control back after the scribe")
    g.wait_frames(20)

    g.walk_to(*EAST, tolerance=45, strict=False)
    menu = g.interact(timeout=6.0)
    if menu is None or menu.choice is None:
        g.check(False, "the keeper opened its menu locally", repr(menu))
        return None
    keeper_uid = _listener(menu)
    ready = g.wait_for(_choice_ready, timeout=6.0, what="the keeper's menu to be ready")
    default_idx = int(ready.choice.get("selected", -1))
    names = g.options()
    want = WANT if WANT in names else names[min(3, len(names) - 1)]
    want_idx = g.option_index(want)
    story_idx = g.option_index(STORY) if STORY in names else 0
    close_idx = g.option_index(CLOSE) if CLOSE in names else int(ready.choice.get("count", 1)) - 1
    g.check(0 <= keeper_uid < 255 and keeper_uid != west_uid and default_idx >= 0,
            "the keeper's uid, its default row and its named rows were read off the live menu",
            f"uid={keeper_uid} default={default_idx} {want!r}={want_idx} {STORY!r}={story_idx} {CLOSE!r}={close_idx}")
    g.choose(want_idx)                   # the same Down presses A2 makes -- they MOVE the cursor here
    local_follow = _follow_up(g)
    g.check(bool(local_follow.strip()), f"choosing {want!r} locally leads to a window", local_follow[:80])
    g.check(_clear(g, close_idx), "the screen cleared after the local choice", repr(g.state))
    g.wait_for(lambda s: s.control, timeout=6.0, what="control back after the local choice")
    g.wait_frames(20)

    g.walk_to(*EAST, tolerance=45, strict=False)
    menu = g.interact(timeout=6.0)
    if menu is None or menu.choice is None:
        g.check(False, "the keeper re-opened its menu locally (the default's reference)", repr(menu))
        return None
    _drag_control(g, lv)                 # A2's drag control, on this unlocked menu (select() steers back after)
    g.choose(default_idx)
    local_default_follow = _follow_up(g)
    g.check(bool(local_default_follow.strip()), f"the default row ({default_idx}) locally leads to a window",
            local_default_follow[:80])
    g.check(_clear(g, close_idx), "the screen cleared after the default's reference", repr(g.state))
    g.wait_for(lambda s: s.control, timeout=6.0, what="control back after the references")
    g.wait_frames(20)
    return SimpleNamespace(west_uid=west_uid, keeper_uid=keeper_uid, local_pages=local_pages,
                           default_idx=default_idx, want=want, want_idx=want_idx, story_idx=story_idx,
                           close_idx=close_idx, local_follow=local_follow,
                           local_default_follow=local_default_follow)


# ------------------------------------------------------------------------------------------ the benches
def _a1_lock_from_open(g, lv, c):
    mark = _mark(g)
    o0 = _ns(g.state).get("orphan_closes")
    st = _open_by_relay(g, c.west_uid)
    first = st.text
    st = _tracked(g)
    w = _front(st)
    win, text = _key(st)
    g.check(_ns(st).get("suppress") is True,
            "A1: the guest's own dialogue input is swallowed from the line's first frame (suppress), before any host event",
            repr(_ns(st))[:300])
    g.check(w is not None and w.get("cls") == "locked" and not w.get("inh"),
            "A1: the relayed line opened LOCKED (windows[].cls), before any host event", repr(_wins(st)))
    g.check(_ns(st).get("chip") == CHIP_FOLLOWING, "A1: the chip reads 'following the host's conversation'",
            repr(_ns(st).get("chip")))
    fresh = _new(g, mark)
    g.check(win is not None and _count(fresh, f"dialogue lock: win {win} text {text} opened locked") == 1,
            "A1: the engine logged the line opening locked, once", _grep(fresh, "dialogue"))
    g.shot("authority-A1-locked")

    page0 = (w or {}).get("page")
    for _ in range(3):
        g.press("confirm", 4)
        g.wait_frames(12)
    # a held Confirm, with the turbo key (RightBumper: TurboDialog's synthesized confirm) held over it
    g.send("hold confirm 45", "hold r1 45", "wait 50")
    clicks = []
    for _ in range(2):
        clicks.append(_try(g, "click", lv.click))
        g.wait_frames(12)
    # (no drag / arrow here: on a PLAIN window stock OnDrag and the arrows act on nothing -- A2 carries them)
    after = g.state
    fa = _front(after)
    fresh = _new(g, mark)
    # BEHAVIOURAL half -- keys the old DLL publishes too, so calibration's red here is the old behaviour
    g.check(after.dialog_open and after.text == first,
            "A1: Confirm x3, a held Confirm (+turbo key) and two clicks left the line open on the same text",
            f"open={after.dialog_open} text_same={after.text == first} text={after.text[:60]!r}")
    # F3.2-key half
    g.check(fa is not None and fa.get("page") == page0 and fa.get("cls") == "locked",
            "A1: ...on the same tracked page, still LOCKED (windows[])",
            f"page {page0}->{(fa or {}).get('page')} cls={(fa or {}).get('cls')}")
    g.check(not any(clicks), "A1: the click seam was exercised (both `netsync click`s were accepted)",
            "; ".join(c for c in clicks if c))
    g.check(_ns(after).get("orphan_closes") == o0 and o0 is not None
            and _count(fresh, "closed by its own script/timer") == 0 and not _applied(fresh, win, text),
            "A1: no close of any kind meanwhile (no orphan close, no self-attributed close, no apply)",
            _grep(fresh, "closed", "orphan"))

    pages, injects = _inject_until_closed(g, first)
    after = g.state
    fresh = _new(g, mark)
    applied = _applied(fresh, win, text)
    g.check(not after.dialog_open and injects == len(c.local_pages) and pages == c.local_pages,
            "A1: host advances paged the line exactly once each, and the transcript equals the local Confirm one",
            f"{injects} inject(s); host={pages!r}\n    local={c.local_pages!r}")
    g.check(len(applied) == injects and injects > 0 and _count(fresh, "did not advance") == 0,
            "A1: one 'advanced/closed (host seq N)' line per host event, never a retry",
            f"{len(applied)} apply line(s) for {injects} inject(s): {applied!r}")
    # A close runs Hide -> CloseAnimation -> Reset (Idle) -> AfterHidden, and only AfterHidden takes the window out
    # of ActiveDialogList -- so for a frame or two the tracker still lists an Idle line (suppress is already
    # down). Give that one tracker tick to land; a line still listed a second later is a real leak.
    settled = _poll(g, lambda s: not _wins(s), 1.0, "the closed line to leave the tracker") or g.state
    g.check(not _wins(settled) and not _ns(settled).get("suppress") and (_ns(settled).get("inbox") or {}).get("count") == 0,
            "A1: after the close nothing is tracked, nothing suppressed, nothing left in the inbox",
            f"windows={_wins(settled)!r} suppress={_ns(settled).get('suppress')} inbox={_ns(settled).get('inbox')!r}")


def _a1v_vanilla(g, lv, c):
    lv.lock(False)
    st = _poll(g, lambda s: _ns(s).get("lock_engaged") is not True, 3.0, "the lock to disengage") or g.state
    st = _open_by_relay(g, c.west_uid)
    g.wait_frames(10)
    st = g.state
    g.check(st.dialog_open and not _ns(st).get("suppress") and not _wins(st),
            "A1v: with the lock OFF the same relayed line opens untracked and unsuppressed", repr(_ns(st))[:300])
    first = st.text
    paged, why = _click_pages(g, lv)
    s = g.state
    g.check(paged, "A1v: with the lock off a click pages the line (stock DialogManager.OnClick) -- A1's control",
            why or repr(s))
    seen = [first] + ([s.text] if s.dialog_open and s.text.strip() and s.text != first else [])
    pages = list(dict.fromkeys(seen + (g.advance(max_pages=MAX_PAGES) if g.state.dialog_open else [])))
    g.check(pages == c.local_pages and not g.state.dialog_open,
            "A1v: click + Confirm walked the same transcript as the local reference",
            f"vanilla={pages!r}\n    local={c.local_pages!r}")


def _a2_choice(g, lv, c):
    mark = _mark(g)
    st = _open_by_relay(g, c.keeper_uid, choice=True)
    st = _tracked(g)
    win, text = _key(st)
    sel0 = int(st.choice.get("selected", -1)) if st.choice else -1
    g.check(_ns(st).get("suppress") is True and (_front(st) or {}).get("cls") == "locked" and sel0 == c.default_idx,
            "A2: the relayed menu opened locked, on its default row", f"sel={sel0} default={c.default_idx} {_wins(st)!r}")
    seen, refused = [], []
    # `drag -80` only: from the default row 0, `drag 80` (MoveCurrentChoice(-1)) clamps -- a no-op on any engine
    for act in (lambda: g.press("down", 4), lambda: g.press("down", 4),
                lambda: refused.append(_try(g, "drag -80", lv.drag, -80))):
        act()
        g.wait_frames(2)
        s = g.state
        seen.append(int(s.choice.get("selected", -1)) if s.choice else None)
    g.shot("authority-A2-cursor")
    g.check(all(x == sel0 for x in seen) and not any(refused),
            "A2: Down x2 and a `drag -80` never moved the locked menu's SelectChoice (the reference choose() and the "
            "drag control moved it unlocked)",
            f"selected after each: {seen} (opened on {sel0}); {'; '.join(r for r in refused if r)}")
    g.netsync("choice", c.want_idx)
    follow = _follow_up(g)
    fresh = _new(g, mark)
    applied = _applied(fresh, win, text)
    g.check(bool(follow.strip()) and follow == c.local_follow,
            f"A2: the host's pick ({c.want!r}) lands the SAME follow-up as a local choose({c.want_idx})",
            f"host={follow[:80]!r}\n    local={c.local_follow[:80]!r}")
    g.check(len(applied) == 1 and applied[0][0] == "closed" and applied[0][2] == c.want_idx,
            f"A2: exactly one 'closed (host seq N, choice {c.want_idx})' line for the menu", repr(applied))


def _a2b_out_of_range(g, lv, c):
    mark = _mark(g)
    st = _open_by_relay(g, c.keeper_uid, choice=True)
    count = int(st.choice.get("count", 0))
    bad = count + 40
    # the guest's cursor: calibration's DLG-10 discriminator -- the OLD DLL moves it and its fallback commits it.
    # Under the F3.2 lock it cannot leave the default, so this DLL cannot show "never the guest's cursor".
    g.press("down", 4)
    g.wait_frames(8)
    g.netsync("choice", bad)
    follow = _follow_up(g)
    fresh = _new(g, mark)
    hits = [m for m in (re.search(rf"host choice {bad} is out of range on win (\d+) text (\d+) -- its default \((-?\d+)\) instead",
                                  ln) for ln in fresh) if m]
    g.check(len(hits) == 1 and int(hits[0].group(3)) == c.default_idx,
            f"A2b: index {bad} of {count} fell back to the menu's DEFAULT ({c.default_idx}), logged once",
            _grep(fresh, "out of range", "host choice"))
    g.check(bool(follow.strip()) and follow == c.local_default_follow,
            "A2b: ...and landed the default's local follow-up (on this DLL the locked cursor sits on the default "
            "anyway; the guest's-cursor case is calibration's)",
            f"host={follow[:80]!r}\n    local default={c.local_default_follow[:80]!r}")


def _a5_choice_held(g, lv, c):
    mark = _mark(g)
    g.netsync("talk", c.keeper_uid)
    st = _poll(g, lambda s: s.dialog_open, 6.0, "the keeper's menu window to exist")
    if st is None:
        raise HarnessError(f"the relayed start for uid {c.keeper_uid} opened nothing within 6s")
    ready_at_inject = _choice_ready(st)
    g.netsync("choice", c.want_idx)      # the instant the window is up -- before its choice may be ready
    follow = _follow_up(g)
    fresh = _new(g, mark)
    # the precondition: without it this run sent a LATE event and proved nothing about holding an early one
    g.check(ready_at_inject is False,
            "A5: the choice event was sent while the menu was not yet ready (the last sample before the send)",
            f"choice ready at the send: {ready_at_inject}; {st.choice!r} group={st.menu_group!r}"[:300])
    queued = [m for m in (_QUEUED.search(ln) for ln in fresh) if m and m.group(5) == "1"]
    win, text = (int(queued[0].group(3)), int(queued[0].group(4))) if queued else (None, None)
    applied = _applied(fresh, win, text)
    g.check(len(queued) == 1 and len(applied) == 1 and applied[0][0] == "closed" and applied[0][2] == c.want_idx
            and _count(fresh, f"did not advance win {win} text {text}") == 0,
            "A5: the early choice event was held through the open, the typewriter and MinShowMs, then applied "
            "exactly once (no retry) -- not DLG-7 itself (module note)",
            f"queued={len(queued)} applied={applied!r}")
    g.check(bool(follow.strip()) and follow == c.local_follow, "A5: ...and it landed the same follow-up as the local pick",
            f"host={follow[:80]!r}\n    local={c.local_follow[:80]!r}")


def _a4_per_key(g, lv, c):
    mark = _mark(g)
    st = _open_by_relay(g, c.west_uid)
    first = st.text
    st = _tracked(g)
    win, text = _key(st)
    g.netsync("unmatched")               # a stranger AHEAD in the inbox: win 15 / text 0xFFFF
    g.netsync("advance")                 # ...then the open line's own event
    st = _poll(g, lambda s: (not s.dialog_open) or (s.text.strip() and s.text != first), 4.0,
               "the open line's event to apply past the stranger")
    after = g.state
    fresh = _new(g, mark)
    stranger = [h for h in _heads(after) if h.get("win") == 15 and h.get("text") == 0xFFFF]
    # behavioural half (old-DLL keys only) -- a regression check: the OLD bench pages here too (module note)
    g.check(st is not None,
            "A4: the open line paged with an unmatched event queued AHEAD of its own (it blocked nothing)",
            f"open={after.dialog_open} text={after.text[:60]!r}")
    g.check(len(_applied(fresh, win, text)) == 1,
            "A4: ...by its own host event: one apply line for its key (per-key FIFO)", _grep(fresh, "dialogue:"))
    # ('tried' is not asserted: it is set only by an apply onto a window of key 15/0xFFFF, which cannot exist)
    g.check(len(stranger) == 1,
            "A4: the stranger is still queued -- nothing consumed it", repr(_heads(after)))


def _a8_polled_page(g, lv, c):
    st = _open_by_relay(g, c.keeper_uid, choice=True)
    mark = _mark(g)
    g.netsync("choice", c.story_idx)     # the host picks the polled story page
    page = _poll(g, lambda s: s.choice is None and s.dialog_open and _ignores_input(s), 6.0,
                 "the [NFOC] polled story page to open")
    if page is None:
        raise HarnessError(f"row {c.story_idx} ({STORY!r}) did not open a [NFOC] polled page")
    st = _poll(g, lambda s: any(w.get("inh") for w in _wins(s)), 2.0, "the tracker to register the polled page") or g.state
    inh = [w for w in _wins(st) if w.get("inh")]
    g.check(bool(inh) and _ns(st).get("suppress") is False,
            "A8: the polled page is tracked as input-inhibited and does NOT raise suppress (FlagButtonInh excluded)",
            f"windows={_wins(st)!r} suppress={_ns(st).get('suppress')!r}")
    g.check(_ns(st).get("chip") == CHIP_HOST_SCENE,
            "A8: the chip reads 'the host is in a scene' -- a polled strip is not a conversation", repr(_ns(st).get("chip")))
    g.check((_ns(st).get("inbox") or {}).get("count") == 0,
            "A8: the menu's applied choice event left the inbox (a regression guard -- this bench fabricates no event "
            "for the polled page, LAW :1369)", repr(_ns(st).get("inbox")))
    g.shot("authority-A8-polled")
    win, text = (inh[0]["win"], inh[0]["text"]) if inh else (None, None)
    # C2 GAP, documented: the guest's own Confirm still closes it. Judge the PAGE leaving (no [NFOC]/[TIME] text
    # left on screen), not the screen emptying: on the deployed bench the keeper is a one-pass [[choice]]
    # (build.py -> content.choice.speak_body), so the two coincide today -- but a handler that went back to its
    # menu (journalfield.talk_body's while latch, the `journal-dash eb` listing's shape) would re-open the menu a few
    # ticks after the page, and "the screen emptied" would then read only the gap between them.
    left = None
    for _ in range(8):
        g.press("confirm", 4)
        left = _poll(g, lambda s: not _ignores_input(s), 0.8, "the polled page to leave")
        if left is not None:
            break
    fresh = _new(g, mark)
    g.check(left is not None and _count(fresh, f"dialogue: win {win} text {text} closed by its own script/timer") == 1,
            "A8: the guest's own Confirm closed the page through its script's poll (the C2 gap; the KEY relay is C3)",
            f"page left={left is not None}; {_grep(fresh, 'closed')}")


def _a3_no_handback(g, lv, c):
    st = _open_by_relay(g, c.keeper_uid, choice=True)
    st = _tracked(g)
    win, text = _key(st)
    o0 = _ns(st).get("orphan_closes")
    mark = _mark(g)
    g.netsync("unmatched")
    settled_seen = []

    def sample():
        s = g.state
        hs = _ns(s).get("host_settled_ms")
        if hs is None or hs != -1:
            settled_seen.append(hs)
        return s

    # phase 1 -- QUIET: no guest input at all, past F3's DialogWaitMs. The old DLL logs its hand-back here ('dialog
    # frame ... timed out -- local advance restored'); mashing first would close its menu at once and the 8 s
    # clock would never be reached -- that is why the quiet phase comes first.
    t0 = time.time()
    quiet_closed = None
    while time.time() - t0 < QUIET_S:
        g.wait_frames(20)
        s = sample()
        if not s.dialog_open or s.choice is None:
            quiet_closed = round(time.time() - t0, 2)
            break
    quiet = g.state
    lines = [ln for ln in _log_lines(g) if "[NetSync]" in ln and "dialog" in ln]
    g.check(quiet_closed is None and _count(lines, "local advance restored") == 0 and _count(lines, "timed out") == 0,
            f"A3: {QUIET_S:.0f}s with no guest input, past F3's 8 s DialogWaitMs: the menu stayed up and no 'local "
            "advance restored' (or any dialogue timeout hand-back) was logged",
            f"closed after {quiet_closed}s; {_grep(lines, 'restored', 'timed out')}")
    # read inside PendingTtlMs (20 s): the stranger ages out of the inbox after that by design
    g.check(any(h.get("win") == 15 and h.get("text") == 0xFFFF for h in _heads(quiet)),
            "A3: the unmatched event is still queued after the quiet phase -- held, never drained", repr(_heads(quiet)))

    # phase 2 -- the guest mashes Confirm all through the hold
    t1 = time.time()
    closed_at = None
    while time.time() - t1 < HOLD_S:
        g.press("confirm", 4)
        g.wait_frames(20)
        s = sample()
        if not s.dialog_open or s.choice is None:
            closed_at = round(time.time() - t1, 2)
            break
    held = time.time() - t1
    s = g.state
    fs = _front(s)
    # behavioural half (old-DLL keys only) -- its calibration red: the first local Confirm closes the menu
    g.check(closed_at is None and held >= HOLD_S and s.dialog_open and s.choice is not None,
            f"A3: ...then the guest mashing Confirm for {HOLD_S:.0f}s: the menu holds",
            f"closed after {closed_at}s; held {held:.1f}s")
    # F3.2-key half
    g.check(fs is not None and fs.get("cls") == "locked" and _ns(s).get("lock_engaged") is True,
            "A3: ...still tracked LOCKED, under an engaged lock", f"front={fs!r} lock_engaged={_ns(s).get('lock_engaged')!r}")
    g.check(not settled_seen, "A3: the host never read settled while its scene was up (host_settled_ms -1 throughout)",
            f"settled samples: {settled_seen[:6]}")

    # the host's scene ends: the line is provably not on the host's screen
    t_before = time.time()
    lv.scene(False)
    t_after = time.time()
    orph = _poll(g, lambda s: (_front(s) or {}).get("cls") == "orphaned", ORPHAN_GRACE_S + 3.0,
                 "the line to turn orphaned")
    t_orph = time.time()
    g.check(orph is not None and t_orph - t_before >= ORPHAN_GRACE_S - EARLY_S
            and t_orph - t_after <= ORPHAN_GRACE_S + SLACK_S,
            f"A3: hostscene 0 -> the line turned 'orphaned' OrphanGraceMs ({ORPHAN_GRACE_S:.0f}s) later",
            f"after {t_orph - t_before:.2f}s (from the send) / {t_orph - t_after:.2f}s (from the ack)")
    if orph is not None:
        hs = _ns(orph).get("host_settled_ms")
        g.check(isinstance(hs, int) and hs >= ORPHAN_GRACE_S * 1000 and _ns(orph).get("chip") == CHIP_CLOSING,
                "A3: ...with the host read settled >= 2 s and the chip 'this line isn't on the host's screen'",
                f"host_settled_ms={_ns(orph).get('host_settled_ms')} chip={_ns(orph).get('chip')!r}")
    gone = _poll(g, lambda s: s.choice is None, AUTO_READ_S + 4.0, "the orphaned menu to auto-close")
    t_gone = time.time()
    g.check(gone is not None and t_gone - t_before >= ORPHAN_GRACE_S + AUTO_READ_S - EARLY_S
            and t_gone - t_after <= ORPHAN_GRACE_S + AUTO_READ_S + 2 * SLACK_S,
            f"A3: ...and auto-closed AutoReadMs ({AUTO_READ_S:.0f}s) after it was orphaned (reading pace)",
            f"closed {t_gone - t_orph:.2f}s after the orphan sample, {t_gone - t_before:.2f}s after the send")
    g.wait_frames(45)
    s = g.state
    fresh = _new(g, mark)
    auto = [int(m.group(1)) for m in (re.search(rf"dialogue orphan: win {win} text {text} auto-closed "
                                                r"\(host idle \d+s, choice (-?\d+)\)", ln) for ln in fresh) if m]
    g.check(auto == [c.close_idx] and not s.dialog_open,
            f"A3: one auto-close line, on the CANCEL row ({c.close_idx} = {CLOSE!r}), and no reply window opened",
            f"auto-close choices {auto}; dialog_open={s.dialog_open}; {_grep(fresh, 'orphan')}")
    g.check(o0 is not None and _ns(s).get("orphan_closes") == o0 + 1
            and _count(fresh, f"win {win} text {text} is not on the host's screen") == 1,
            "A3: orphan_closes went up by exactly one, after exactly one orphan line", f"{o0} -> {_ns(s).get('orphan_closes')}")
    g.check(_count(fresh, "closed by its own script/timer") == 0 and not _applied(fresh, win, text),
            "A3: zero input-driven or self-attributed closes -- the orphan rule closed it, nothing else",
            _grep(fresh, "closed"))
    lv.scene(True)


def _a6_link_dead(g, lv, c):
    _open_by_relay(g, c.west_uid)
    st = _tracked(g)
    g.check((_front(st) or {}).get("cls") == "locked", "A6: the relayed line opened locked", repr(_wins(st)))
    mark = _mark(g)
    t_before = time.time()
    lv.stale(True)
    t_after = time.time()
    held_late, released, hiccup = None, None, False
    while time.time() - t_before < LINK_GRACE_S + 4.0:
        s = g.state
        el = time.time() - t_before
        if _ns(s).get("lock_engaged") is True:
            if _ns(s).get("suppress") is True and s.dialog_open:
                held_late = el
            hiccup = hiccup or _ns(s).get("chip") == CHIP_HICCUP
        else:
            released = time.time()
            break
        g.wait_frames(1)
    g.check(held_late is not None and held_late >= LINK_GRACE_S - 0.25,
            f"A6: with the link reading dead the lock HOLDS the line ({LINK_GRACE_S - 0.25:.2f}s+ still locked)",
            f"last locked sample {held_late}s after the stale")
    g.check(hiccup, "A6: ...under the chip 'link hiccup -- holding this conversation for the host'", "")
    g.check(released is not None and released - t_before >= LINK_GRACE_S - EARLY_S
            and released - t_after <= LINK_GRACE_S + SLACK_S,
            f"A6: ...and released it LinkGraceMs ({LINK_GRACE_S:.0f}s) after the link died",
            f"released {None if released is None else round(released - t_before, 2)}s after the send")
    fresh = _new(g, mark)
    g.check(_count(fresh, "dialogue lock released -- the link has read dead for 3 s") == 1,
            "A6: one 'lock released -- the link has read dead' line", _grep(fresh, "dialogue lock"))
    st = g.state
    g.check(not _ns(st).get("suppress") and not _wins(st), "A6: released = nothing tracked, nothing suppressed",
            repr(_ns(st))[:300])
    g.check(_paged_by(g, lambda: g.press("confirm", 4)), "A6: the guest's own Confirm pages the released line", repr(g.state))
    lv.stale(False)


def _a7_unlock(g, lv, c, field):
    _open_by_relay(g, c.west_uid)
    st = _tracked(g)
    g.check((_front(st) or {}).get("cls") == "locked", "A7: the relayed line opened locked", repr(_wins(st)))
    mark = _mark(g)
    lv.unlock()
    st = _poll(g, lambda s: _ns(s).get("unlocked") is True and _ns(s).get("lock_engaged") is False, 2.0,
               "the panic unlock to drop the lock") or g.state
    g.check(_ns(st).get("unlocked") is True and _ns(st).get("lock_engaged") is False and not _ns(st).get("suppress"),
            "A7: `netsync unlock` dropped the lock on this field", repr(_ns(st))[:300])
    g.check(_paged_by(g, lambda: g.press("confirm", 4)), "A7: the guest's own Confirm pages the line after the unlock",
            repr(g.state))
    fresh = _new(g, mark)
    g.check(_count(fresh, f"dialogue lock released on field {field} (manual unlock)") == 1,
            "A7: one 'released on field N (manual unlock)' line", _grep(fresh, "dialogue lock"))
    _clear(g, c.close_idx)
    _poll(g, lambda s: s.control, 6.0, "control back before the reload")

    mark = _mark(g)
    if lv.legacy:
        lv.lock(False)                   # the old l1 pin holds control; the warp waits for a playable field
    g.warp(field)                        # the reload: the unlock lasts until the next field load
    if lv.legacy:
        lv.engage()
    g.wait_frames(30)
    st = _poll(g, lambda s: _ns(s).get("unlocked") is False and _ns(s).get("lock_engaged") is True, 5.0,
               "the lock to re-arm after the reload") or g.state
    fresh = _new(g, mark)
    g.check(_ns(st).get("unlocked") is False and _ns(st).get("lock_engaged") is True
            and _count(fresh, "dialogue lock re-armed (field load)") == 1,
            "A7: a field reload re-armed the lock (one 're-armed (field load)' line)", _grep(fresh, "dialogue lock"))
    _open_by_relay(g, c.west_uid)
    st = _tracked(g)
    g.check((_front(st) or {}).get("cls") == "locked" and _ns(st).get("suppress") is True,
            "A7: after the reload a relayed line opens LOCKED again", repr(_wins(st)))


def _reset_releases(g, lv):
    """`reset` releases the override AND every lever -- a leaked run must not swallow the next player's Confirm."""
    try:
        g.netsync("bench", 1)
        lv.lock(True)
        lv.scene(True)
        lv.stale(True)
        g.send("reset")
        st = _poll(g, lambda s: s.netsync is not None and not _ns(s).get("forced"), 5.0,
                   "`reset` to release the forced selftest") or g.state
    except HarnessError as err:
        g.check(False, "RESET: the levers were set and `reset` was sent", str(err)[:300])
        return
    ns = _ns(st)
    g.check(ns.get("enabled") is False and ns.get("bench") is False and ns.get("l1") is False
            and ns.get("lock") is False and ns.get("stale") is False and ns.get("lock_engaged") is False
            and ns.get("suppress") is False,
            "RESET: `reset` released the selftest override, the bench, l1, lock and stale", repr(ns)[:300])
    st = _poll(g, lambda s: s.control, 5.0, "control on after the reset") or g.state
    g.check(st.control, "RESET: the character is not left frozen by a released run", repr(_ns(st))[:200])


def _a12_vanilla(g, lv, c):
    """A12-lite: co-op released in this process (not Enabled=0 from launch -- module note)."""
    g.walk_to(*WEST, tolerance=45, strict=False)
    mark = _mark(g)
    opened = g.interact(timeout=6.0)
    if opened is None or opened.choice is not None:
        g.check(False, "A12: the scribe opened locally with co-op released", repr(opened))
        return
    st = g.state
    g.check(not _ns(st).get("suppress") and not _ns(st).get("lock_engaged"),
            "A12: with co-op released nothing is suppressed or locked (a regression guard: both reads are gated on "
            "`enabled`, which RESET asserted False)", repr(_ns(st))[:200])
    first = opened.text
    paged, why = _click_pages(g, lv)
    s = g.state
    seen = [first] + ([s.text] if s.dialog_open and s.text.strip() and s.text != first else [])
    pages = list(dict.fromkeys(seen + (g.advance(max_pages=MAX_PAGES) if g.state.dialog_open else [])))
    g.check(paged and pages == c.local_pages and not g.state.dialog_open,
            "A12: a click pages the line and click + Confirm walk the reference transcript (stock)",
            f"paged={paged} {why}; {pages!r}")
    fresh = _new(g, mark)
    g.check(_count(fresh, "[NetSync]") == 0, "A12: zero [NetSync] log lines through a stock talk with co-op released",
            _grep(fresh, "[NetSync]"))
    g.shot("authority-A12-vanilla")
