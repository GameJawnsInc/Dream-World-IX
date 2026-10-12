"""F3.1 TALK RELAY under F3.2 C1 (S-WARP): the guest-side replay of a press-fired talk, proven solo.

The 2026-09-04 two-machine run at Dali found the gap: an NPC talk is press-fired (tag 3). The F1
spectator gate returns before the guest could start one, and L1 pinned the guest's control anyway, so
the guest's copy of the talk never opened (no facing, no window). The relay (s85): the host emits a
state-lane section at the exact Request accept, and the co-located guest becomes the object's listener
and calls `ee.Request(obj, 1, 3)` on its own copy.

F3.2 stage C1 (s95, `studies/field-coop/F3.2-DESIGN.md` warp_changes W1-W3) changed the contract:
  * the relay NEVER snaps the guest to the host -- Request has no position test (EventEngine.cs:339-349);
  * THE L1 LAW: the host-scene flag never moves or freezes the guest. Its control pin was TALK-3's root
    cause: it zeroed the usercontrol every stock `_SpeakBTN`'s `ifnot(IsMovementEnabled) return` reads;
  * a start that lands while the guest's copy cannot take it DEFERS (one 'deferred' line per start)
    instead of silently failing; the nonce is consumed only on accept or decline; TTL 2000 -> 4000 ms.

WHAT IS PROVEN, each check an OUTCOME (position, control, the window on screen, the engine's own line):
  T1   `netsync hostscene 1` (the bench's simulated section 5) neither moves nor freezes the player:
       |delta| < 1 unit, control stays on, no 'snapped' log line, one 'staying in place' line.
  T2a  `netsync talk <uid>` from ~300 units opens the SAME window the local talk opened, with the player
       not moved and set as the object's listener (the NPC faces him).
  T2b  ...and it still opens with the host scene ON (TALK-3), from where the player stands.
  T3a  DEFERRAL, another object: a start for the keeper that lands while my copy of the scribe's talk
       holds control logs ONE 'deferred' line and opens nothing; the keeper's menu opens once my copy
       hands control back, inside the 4 s TTL, with no 'expired' line.
  T3b  ...the same object twice in a row: the second start waits for the object to return to idle.
  T4   an unknown uid is declined once and opens nothing.

The host tap (EmitTalkStartIfHost, the quad promotion) and the section's ride on the wire can only be
exercised on a real link: that is the two-machine session (C1 boxes 1-6).

CALIBRATION -- a check that cannot fail is not a check. Run this once against the pre-C1 DLL (the
F3/F3.1 build that predates s95) and see it go red BEFORE trusting a green run of the new one. Set
COOP_CALIBRATE=1, or let the scenario fall back on its own: an engine whose `netsync` block carries no
`dialogue` key predates C2, so the scenario spells the simulated host scene `l1` (the only name that
engine knows -- `hostscene` arrived with C2). The ASSERTIONS ARE THE SAME in both modes; only the verb
spelling changes. Expected on the pre-C1 DLL:
  * T1 FAILS -- the old bench snapped onto the selftest mirror (player + SelfTestOffset, 250 units) and
    zeroed control the moment `l1 1` landed (log 'L1 co-locate: snapped to host event');
  * T2b FAILS on the move (that snap fired before the talk). Its window still OPENS there: the KIT's talk
    handlers carry no `ifnot(IsMovementEnabled) return` prologue, so TALK-3's no-open half needs a stock
    `_SpeakBTN` -- that is two-machine box 5;
  * T3a / T3b FAIL -- the old apply never deferred (no 'deferred' line: it consumed the nonce at once);
  * NOT discriminating there: T2a (the old BENCH never snapped a relayed talk -- only the live path passed
    the host position) and T4 (unchanged by C1). They are kept as regression checks.
On a C1-only DLL (s95 without s96: no `dialogue` key, so calibration spelling) every check should pass --
that build already lost the snap and the pin.

Bench 30801 (the journal dashboard): the scribe (plain window) stands west, reached from (-210, -837);
the keeper (the 15-option journal menu, `Close` last) stands east, reached from (210, -837).

    py tools/play.py studies/test-harness/scenarios/coop_talk_relay.py --field 30801
    COOP_CALIBRATE=1 py tools/play.py studies/test-harness/scenarios/coop_talk_relay.py --field 30801
"""
import os
import time

try:                                     # play.py puts tools/ on sys.path before it loads a scenario
    from harness import HarnessError
except ImportError:                      # pragma: no cover - imported outside the driver (py_compile, a stub)
    HarnessError = RuntimeError          # HarnessError IS a RuntimeError

FIELD = 30801
WEST = (-210.0, -837.0)         # beside the scribe: a plain window
EAST = (210.0, -837.0)          # beside the keeper: the journal menu
FAR = (90.0, -837.0)            # 300 units east of the WEST spot
TTL_S = 4.0                     # NetSyncClient.TalkRelayTtlMs (F3.2: 2000 -> 4000); the bench mirrors it
MOVE_EPS = 1.0                  # "not moved": the snap was 250 units; walking noise at rest is 0

#: COOP_CALIBRATE=1 forces the pre-F3.2 verb spellings (see the module note); unset, they are chosen
#: from the engine's own `netsync.dialogue` contract tag.
FORCE_CALIBRATE = os.environ.get("COOP_CALIBRATE", "").strip() not in ("", "0")


def _log_lines(g):
    p = g.engine_log()
    if p is None:
        return []
    try:
        return p.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def _count(lines, needle):
    return sum(1 for ln in lines if needle in ln)


def _grep(lines, *needles, limit=300):
    return "; ".join(ln for ln in lines if any(n in ln for n in needles))[:limit]


def _moved(a, b) -> float:
    if a.player_x is None or b.player_x is None:
        return float("inf")
    return ((a.player_x - b.player_x) ** 2 + (a.player_z - b.player_z) ** 2) ** 0.5


def _ns(st) -> dict:
    return st.netsync or {}


def _listener(st) -> int:
    return int((st.raw.get("player") or {}).get("listener", -1))


def _page_out(g, *, max_presses=24):
    for _ in range(max_presses):
        if not g.state.dialog_open:
            return True
        g.press("confirm", 4)
        g.wait_frames(12)
    return not g.state.dialog_open


def _close_index(g, st) -> int:
    """The keeper menu's `Close` row, by NAME (the engine's own index space); the last row as a fallback --
    with no [PCHC]/[PCHM] the engine's cancel row is the last one (content/choice.py)."""
    try:
        return g.option_index("Close")
    except HarnessError:
        return int(st.choice.get("count", 1)) - 1


def run(g, field: int = FIELD):
    g.note("F3.2 C1 talk relay: the guest-side replay of a press-fired talk, solo (no snap, no pin, defer)")
    g.newgame()
    g.warp(field)
    g.wait_frames(60)
    g.calibrate_axes()
    st = g.netsync("selftest", 1)
    g.check(st.netsync is not None and _ns(st).get("selftest"), "selftest role forced", repr(st.netsync))
    contract = _ns(st).get("dialogue")
    legacy = FORCE_CALIBRATE or contract != "authority"
    scene_verb = "l1" if legacy else "hostscene"
    g.note(f"mode: {'CALIBRATION (pre-C2 verb spelling: l1)' if legacy else 'F3.2 (hostscene)'}"
           f" -- netsync.dialogue={contract!r}, COOP_CALIBRATE={'1' if FORCE_CALIBRATE else 'unset'}")

    # ---- 1. learn both objects' uids (and the scribe's pages) from LOCAL talks ----------------------
    g.walk_to(*EAST, tolerance=45, strict=False)
    menu = g.interact(timeout=6.0)
    if menu is None or menu.choice is None:
        g.check(False, "the keeper opened its menu locally", repr(menu))
        return
    keeper = _listener(menu)
    close_idx = _close_index(g, menu)
    g.check(0 <= keeper < 255, "the engine published the keeper's uid as player.listener", f"uid={keeper}")
    g.check(_clear(g, close_idx), "the keeper's menu closed on its Close row", repr(g.state))
    g.wait_for(lambda s: s.control, timeout=6.0, what="control back after the keeper's menu")
    g.wait_frames(20)

    g.walk_to(*WEST, tolerance=45, strict=False)
    opened = g.interact(timeout=6.0)
    if opened is None or opened.choice is not None:
        g.check(False, "the scribe opened a plain window locally", repr(opened))
        return
    uid = _listener(opened)
    west_text = opened.text
    # Actor.listener is a Byte and 255 means "nobody" -- a real target is 0..254.
    g.check(0 <= uid < 255 and uid != keeper, "the engine published the scribe's uid as player.listener",
            f"uid={uid} keeper={keeper}")
    west_pages = list(dict.fromkeys([opened.text] + g.advance(max_pages=24)))
    g.check(_page_out(g), "the local window paged out", repr(g.state))
    g.wait_for(lambda s: s.control, timeout=6.0, what="control back after the local talk")
    g.wait_frames(20)
    if not (0 <= uid < 255 and 0 <= keeper < 255):
        return

    # ---- 2. (T2a) the relay, from far away, with no move --------------------------------------------
    g.walk_to(*FAR, tolerance=45, strict=False)
    here = g.state
    dist = abs((here.player_x or 0) - WEST[0])
    g.check(dist >= 200, "standing well outside any talk radius before the inject", f"{dist:.0f} units east of the spot")
    mark = len(_log_lines(g))
    g.netsync("bench", 1)
    g.netsync("talk", uid)
    st = _poll(g, lambda s: s.dialog_open and bool(s.text.strip()), 6.0,
               "the relayed talk start to open the scribe's window") or g.state
    g.shot("talk-relay-01-opened")
    g.check(st.dialog_open and st.text == west_text,
            "T2a: the relayed start opened the SAME window the local talk opened -- from 300 units away",
            f"relay={st.text[:70]!r}\n    local={west_text[:70]!r}")
    g.check(_moved(st, here) < MOVE_EPS,
            "T2a: the relayed talk did NOT move the player (no snap to the host)",
            f"moved {_moved(st, here):.1f} units")
    g.check(_listener(st) == uid, "T2a: the player is the object's listener (the NPC faces him)", repr(st.raw.get("player")))
    fresh = _log_lines(g)[mark:]
    g.check(_count(fresh, f"talk bench: fabricated SectionTalk obj {uid}") == 1
            and _count(fresh, f"talk relay: started obj {uid} (tag 3)") == 1
            and _count(fresh, "snapped") == 0,
            "T2a: the section round-tripped the real codec, the apply logged the start once, nothing snapped",
            _grep(fresh, "talk", "snap"))
    g.netsync("bench", 0)
    g.check(_page_out(g), "the relayed window pages out with the player's own Confirm", repr(g.state))
    g.wait_for(lambda s: s.control, timeout=6.0, what="control back after the relayed talk")
    g.wait_frames(20)

    # ---- 3. (T1 + T2b) the host-scene flag: no snap, no pin -- and the relay still opens ------------
    mark = len(_log_lines(g))
    here = g.state
    g.netsync("bench", 1)
    g.netsync(scene_verb, 1)
    g.wait_frames(30)                    # the pre-C1 bench snapped + pinned within a frame or two of this
    st = g.state
    fresh = _log_lines(g)[mark:]
    # (`l1_forced_control` is not asserted: every C1+ DLL pins it False, and the pre-C1 pin already reads as
    # control=False -- it could never fail on its own. It stays in the detail as evidence.)
    g.check(st.control and _moved(st, here) < MOVE_EPS,
            "T1: the host-scene flag neither moves nor freezes the player (THE L1 LAW)",
            f"control={st.control} moved={_moved(st, here):.1f} netsync={_ns(st)!r}"[:300])
    g.check(_count(fresh, "snapped") == 0 and _count(fresh, "staying in place") == 1,
            "T1: the bench logged the simulated scene once ('staying in place') and never a snap",
            _grep(fresh, "scene", "snap", "L1"))
    g.shot("talk-relay-02-hostscene")
    g.netsync("talk", uid)
    st = _poll(g, lambda s: s.dialog_open and bool(s.text.strip()), 6.0,
               "the relayed talk to open with the host scene ON (TALK-3)") or g.state
    g.check(st.dialog_open and st.text == west_text and _moved(st, here) < MOVE_EPS,
            "T2b: a relayed talk opens under the host scene, from where the player stands (TALK-3)",
            f"text={st.text[:60]!r} moved={_moved(st, here):.1f}")
    fresh = _log_lines(g)[mark:]
    g.check(_count(fresh, "snapped") == 0 and _count(fresh, f"talk relay: started obj {uid} (tag 3)") == 1,
            "T2b: the relayed start logged once, and nothing snapped", _grep(fresh, "talk", "snap"))
    g.netsync(scene_verb, 0)             # (pre-C1: this is also what hands the pinned control back)
    g.netsync("bench", 0)
    g.check(_page_out(g), "the relayed window pages out (host scene off)", repr(g.state))
    g.wait_for(lambda s: s.control, timeout=6.0, what="control back after the host-scene talk")
    g.wait_frames(20)

    # ---- 4. (T3a) DEFERRAL onto ANOTHER object: my copy of the scribe's talk still holds control ----
    _defer_bench(g, "T3a", relay_uid=keeper, west_text=west_text, west_pages=west_pages,
                 want_choice=True, close_idx=close_idx)
    # ---- 5. (T3b) the SAME object twice in a row: it waits for the object to return to idle ---------
    _defer_bench(g, "T3b", relay_uid=uid, west_text=west_text, west_pages=west_pages,
                 want_choice=False, close_idx=close_idx)

    # ---- 6. (T4) an unknown uid is refused, opens nothing -------------------------------------------
    mark = len(_log_lines(g))
    g.netsync("bench", 1)
    g.netsync("talk", 65000)
    g.wait_frames(40)
    st = g.state
    fresh = _log_lines(g)[mark:]
    g.check(not st.dialog_open and _count(fresh, "no object with uid 65000") == 1,
            "T4: an unknown uid is declined once and opens nothing", _grep(fresh, "talk", limit=200))
    g.netsync("bench", 0)
    g.netsync("selftest", 0)
    g.check(g.state.netsync is not None and not _ns(g.state).get("forced"), "the override was released", "")


def _defer_bench(g, tag, *, relay_uid, west_text, west_pages, want_choice, close_idx):
    """Open the scribe LOCALLY and stand on its last page (its handler holds control), then relay a start
    for `relay_uid`. It must defer -- one line, nothing opened -- and open once the scribe closes."""
    what = "the keeper's menu" if want_choice else "the scribe's window again"
    g.walk_to(*WEST, tolerance=45, strict=False)
    opened = g.interact(timeout=6.0)
    if opened is None:
        g.check(False, f"{tag}: the scribe re-opened locally for the deferral bench", "")
        return
    for _ in range(24):                  # stand on the LAST page so the deferral is short (TTL 4 s)
        st = g.state
        if not st.dialog_open or st.text == west_pages[-1]:
            break
        g.press("confirm", 4)
        g.wait_frames(12)
    st = g.state
    g.check(st.dialog_open and not st.control,
            f"{tag}: on the local window's last page, the talk's own handler holds control", repr(st))
    mark = len(_log_lines(g))
    g.netsync("bench", 1)
    t0 = time.time()
    g.netsync("talk", relay_uid)
    g.wait_frames(20)
    st = g.state
    fresh = _log_lines(g)[mark:]
    g.check(_count(fresh, f"(obj {relay_uid}) deferred") == 1 and _count(fresh, f"started obj {relay_uid}") == 0
            and st.choice is None and st.text == west_pages[-1],
            f"{tag}: a start that lands while my copy holds control DEFERS -- one line, nothing opened",
            _grep(fresh, "talk"))
    # Close the local window: the handler hands control back. A last page still typewriting eats the first
    # Confirm as a fast-forward, so press again -- but never once the relayed start has fired: its window
    # is the one under test, and an extra Confirm would page it.
    started_line = f"talk relay: started obj {relay_uid} (tag 3)"
    for _ in range(4):
        if _count(_log_lines(g)[mark:], started_line) or not g.state.dialog_open:
            break
        g.press("confirm", 4)
        g.wait_frames(12)
    fired = _poll(g, lambda s: _count(_log_lines(g)[mark:], started_line) >= 1, TTL_S + 2.0,
                  f"{tag}: the deferred start to fire once my copy is free")
    started_after = time.time() - t0
    st = None
    if fired is not None:
        if want_choice:
            st = _poll(g, lambda s: s.choice is not None, 4.0, f"{tag}: {what} to open")
        else:
            st = _poll(g, lambda s: s.dialog_open and bool(s.text.strip()), 4.0, f"{tag}: {what} to open")
    landed = st is not None and (st.choice is not None if want_choice else st.text == west_text)
    fresh = _log_lines(g)[mark:]
    g.check(fired is not None and landed and started_after <= TTL_S,
            f"{tag}: the deferred start opened {what} once my copy was free, inside the TTL",
            f"fired={fired is not None} after {started_after:.1f}s; "
            f"text={(st.text if st is not None else '')[:60]!r}; {_grep(fresh, 'talk', limit=200)}")
    g.check(_count(fresh, f"(obj {relay_uid}) deferred") == 1 and _count(fresh, "expired before my copy was free") == 0,
            f"{tag}: the deferral logged once and never expired", _grep(fresh, "talk"))
    g.netsync("bench", 0)
    g.check(_clear(g, close_idx), f"{tag}: the screen clears afterwards", repr(g.state))
    g.wait_for(lambda s: s.control, timeout=6.0, what=f"control back after {tag}")
    g.wait_frames(20)


def _poll(g, predicate, timeout: float, what: str):
    """``g.wait_for`` that answers None on a timeout instead of raising -- the caller's check carries the verdict
    (a dead game still raises: the next send asserts the process is alive)."""
    try:
        return g.wait_for(predicate, timeout=timeout, what=what)
    except HarnessError:
        return None


def _clear(g, close_idx, *, max_steps=24) -> bool:
    """Clear the screen locally: the keeper's menu on its Close row, any other window with Confirm."""
    for _ in range(max_steps):
        st = g.state
        if not st.dialog_open:
            return True
        if st.choice is not None:
            try:
                g.choose(close_idx)
                continue
            except HarnessError:
                pass
        g.press("confirm", 4)
        g.wait_frames(12)
    return not g.state.dialog_open
