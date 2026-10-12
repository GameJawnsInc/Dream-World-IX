"""F3.1 TALK RELAY -- the guest-side replay of a host's press-fired talk, proven solo.

The 2026-09-04 two-machine run at Dali found the gap: an NPC talk is press-fired (tag 3), the F1
spectator gate returns before the guest could ever start one, and L1 pinned the guest's control anyway
-- so the guest's copy of the talk never opened (no facing, no window) and every F3 lockstep frame for
it timed out. The relay: the host emits a state-lane section at the exact Request accept, and the
co-located guest becomes the object's listener and calls `ee.Request(obj, 1, 3)` on its own copy.

F3.2 stage C1 (S-WARP) changed the contract this scenario proves: the relay NEVER snaps the guest to
the host (Request has no position test), L1 never moves or freezes the guest (its control pin was
TALK-3's root cause -- it zeroed the usercontrol every `_SpeakBTN`'s `ifnot(IsMovementEnabled) return`
prologue reads), and a start that lands while the guest's copy can't take it DEFERS instead of
silently failing -- the nonce is consumed only on accept or decline.

This scenario proves the GUEST-SIDE APPLY solo, through the same fabricated-section bench the harness
uses for the other co-op benches (`netsync talk <uid>`):

  1. talk to the west responder LOCALLY, read the uid the engine set as the player's listener
     (`player.listener` -- published for exactly this), and record the window's pages;
  2. (T2) walk 300 units away (far outside any talk radius), inject `netsync talk <uid>`, and assert the
     SAME window opens -- the relay, not proximity, started it -- with the player NOT moved;
  3. (T1 + T2/TALK-3) with the L1 host-scene flag ON the player keeps control and stays put, and a
     relayed talk still opens (pre-F3.2 the pin made the handler's prologue bail: nothing opened);
  4. (T3) a relayed start for the talk whose window is still open on my copy logs ONE 'deferred' line,
     then opens the talk again once my copy hands control back -- inside the 4 s TTL;
  5. (T4) an unknown uid is refused once and opens nothing.

⚠ Steps 2-4's F3.2 checks are written against the design and NOT YET CALIBRATED: run them once on the
pre-C1 DLL and confirm they FAIL (the snap / the pin / the silent 'started' with nothing opening)
before trusting a green run.

The host tap (EmitTalkStartIfHost, incl. the quad promotion) and the section's ride on the wire can only
be exercised on a real link -- that is the laptop session.

    py tools/play.py studies/test-harness/scenarios/coop_talk_relay.py --field 30801
"""
import time

FIELD = 30801
WEST = (-210.0, -837.0)
FAR = (90.0, -837.0)            # 300 units east of the west responder
TTL_S = 4.0                     # NetSyncClient.TalkRelayTtlMs (F3.2: 2000 -> 4000); the bench mirrors it


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


def _moved(a, b) -> float:
    if a.player_x is None or b.player_x is None:
        return float("inf")
    return ((a.player_x - b.player_x) ** 2 + (a.player_z - b.player_z) ** 2) ** 0.5


def _page_out(g, *, max_presses=24):
    for _ in range(max_presses):
        if not g.state.dialog_open:
            return True
        g.press("confirm", 4)
        g.wait_frames(12)
    return not g.state.dialog_open


def run(g, field: int = FIELD):
    g.note("F3.1 talk relay: the guest-side replay of a press-fired talk, solo (F3.2: no snap, no pin, defer)")
    g.newgame()
    g.warp(field)
    g.wait_frames(60)
    g.calibrate_axes()
    st = g.netsync("selftest", 1)
    g.check(st.netsync is not None and st.netsync["selftest"], "selftest role forced", repr(st.netsync))

    # ---- 1. learn the NPC's uid (and its pages) from a LOCAL talk ------------------------------
    g.walk_to(*WEST, tolerance=45, strict=False)
    opened = g.interact(timeout=6.0)
    if opened is None or opened.choice is not None:
        g.check(False, "the west responder opened a plain window locally", repr(opened))
        return
    uid = int(opened.raw.get("player", {}).get("listener", -1))
    west_text = opened.text
    # Actor.listener is a Byte and 255 means "nobody" -- a real target is 0..254.
    g.check(0 <= uid < 255, "the engine published the talk target's uid as player.listener", f"uid={uid}")
    west_pages = list(dict.fromkeys([opened.text] + g.advance(max_pages=24)))
    g.check(_page_out(g), "the local window paged out", repr(g.state))
    g.wait_for(lambda s: s.control, timeout=6.0, what="control back after the local talk")
    g.wait_frames(20)
    if not 0 <= uid < 255:
        return

    # ---- 2. (T2) the relay, from far away, with no move -----------------------------------------
    g.walk_to(*FAR, tolerance=45, strict=False)
    here = g.state
    dist = abs((here.player_x or 0) - WEST[0])
    g.check(dist >= 200, "standing well outside any talk radius before the inject", f"{dist:.0f} units east of the NPC")
    mark = len(_log_lines(g))
    g.netsync("bench", 1)
    g.netsync("talk", uid)
    st = g.wait_for(lambda s: s.dialog_open and bool(s.text.strip()), timeout=6.0,
                    what="the relayed talk start to open the NPC's window")
    g.shot("talk-relay-01-opened")
    g.check(st.text == west_text,
            "the relayed start opened the SAME window the local talk opened -- from 300 units away",
            f"relay={st.text[:70]!r}\n    local={west_text[:70]!r}")
    g.check(_moved(st, here) < 1.0,
            "T2: the relayed talk did NOT move the player (F3.2: no snap to the host)",
            f"moved {_moved(st, here):.1f} units")
    g.check(int(st.raw.get("player", {}).get("listener", -1)) == uid,
            "the player is the object's listener (the NPC faces the player)", repr(st.raw.get("player")))
    fresh = _log_lines(g)[mark:]
    g.check(_count(fresh, f"talk bench: fabricated SectionTalk obj {uid}") == 1
            and _count(fresh, f"talk relay: started obj {uid} (tag 3)") == 1
            and _count(fresh, "snapped") == 0,
            "the section round-tripped the real codec, the apply logged the start, nothing snapped",
            "; ".join(ln for ln in fresh if "talk" in ln or "snap" in ln)[:300])
    g.netsync("bench", 0)
    g.check(_page_out(g), "the relayed window pages out with the player's own Confirm", repr(g.state))
    g.wait_for(lambda s: s.control, timeout=6.0, what="control back after the relayed talk")
    g.wait_frames(20)

    # ---- 3. (T1 + T2/TALK-3) the L1 host-scene flag: no snap, no pin -- and the relay still opens --
    mark = len(_log_lines(g))
    here = g.state
    g.netsync("bench", 1)
    g.netsync("l1", 1)
    g.wait_frames(30)                    # the old bench snapped + pinned within a frame or two of this
    st = g.state
    g.check(st.control and not st.netsync["l1_forced_control"] and _moved(st, here) < 1.0,
            "T1: the L1 host-scene flag neither moves nor freezes the player (THE L1 LAW)",
            f"control={st.control} moved={_moved(st, here):.1f} netsync={st.netsync!r}"[:300])
    g.netsync("talk", uid)
    st = g.wait_for(lambda s: s.dialog_open and bool(s.text.strip()), timeout=6.0,
                    what="the relayed talk to open with the L1 flag ON (TALK-3)")
    g.check(st.text == west_text and _moved(st, here) < 1.0,
            "TALK-3: a relayed talk opens under the L1 flag, from where the player stands",
            f"text={st.text[:60]!r} moved={_moved(st, here):.1f}")
    fresh = _log_lines(g)[mark:]
    g.check(_count(fresh, "snapped") == 0 and _count(fresh, "staying in place") == 1
            and _count(fresh, f"talk relay: started obj {uid} (tag 3)") == 1,
            "the bench logged the simulated scene once, the relayed start once, and never a snap",
            "; ".join(ln for ln in fresh if "scene" in ln or "talk" in ln or "snap" in ln)[:300])
    g.netsync("l1", 0)
    g.netsync("bench", 0)
    g.check(_page_out(g), "the relayed window pages out (L1 off)", repr(g.state))
    g.wait_for(lambda s: s.control, timeout=6.0, what="control back after the L1-flag talk")
    g.wait_frames(20)

    # ---- 4. (T3) DEFERRAL: my copy of the same talk still holds control -> wait, then open -------
    g.walk_to(*WEST, tolerance=45, strict=False)
    opened = g.interact(timeout=6.0)
    if opened is None:
        g.check(False, "the west responder re-opened locally for the deferral bench", "")
        return
    for _ in range(24):                  # stand on the LAST page so the deferral is short (TTL 4 s)
        st = g.state
        if not st.dialog_open or st.text == west_pages[-1]:
            break
        g.press("confirm", 4)
        g.wait_frames(12)
    st = g.state
    g.check(st.dialog_open and not st.control,
            "on the local window's last page, the talk's own handler holds control", repr(st))
    mark = len(_log_lines(g))
    g.netsync("bench", 1)
    t0 = time.time()
    g.netsync("talk", uid)
    g.wait_frames(20)
    fresh = _log_lines(g)[mark:]
    g.check(_count(fresh, f"(obj {uid}) deferred") == 1 and _count(fresh, f"started obj {uid}") == 0,
            "T3: a start that lands while my copy holds control DEFERS -- one line, nothing started",
            "; ".join(ln for ln in fresh if "talk" in ln)[:300])
    g.press("confirm", 4)                # close the local window: the handler hands control back
    st = g.wait_for(lambda s: _count(_log_lines(g)[mark:], f"talk relay: started obj {uid} (tag 3)") >= 1,
                    timeout=TTL_S + 2.0, what="the deferred start to fire once my copy is free")
    started_after = time.time() - t0
    st = g.wait_for(lambda s: s.dialog_open and bool(s.text.strip()), timeout=4.0,
                    what="the deferred talk's window to open")
    fresh = _log_lines(g)[mark:]
    g.check(st.text == west_text and started_after <= TTL_S,
            "T3: the deferred start opened the talk again once my copy was free, inside the TTL",
            f"after {started_after:.1f}s; text={st.text[:60]!r}")
    g.check(_count(fresh, f"(obj {uid}) deferred") == 1 and _count(fresh, "expired before my copy was free") == 0,
            "the deferral logged once and never expired", "; ".join(ln for ln in fresh if "talk" in ln)[:300])
    g.netsync("bench", 0)
    g.check(_page_out(g), "the deferred talk's window pages out", repr(g.state))
    g.wait_for(lambda s: s.control, timeout=6.0, what="control back after the deferred talk")
    g.wait_frames(20)

    # ---- 5. (T4) an unknown uid is refused, opens nothing ----------------------------------------
    mark = len(_log_lines(g))
    g.netsync("bench", 1)
    g.netsync("talk", 65000)
    g.wait_frames(40)
    st = g.state
    fresh = _log_lines(g)[mark:]
    g.check(not st.dialog_open and _count(fresh, "no object with uid 65000") == 1,
            "an unknown uid is declined once and opens nothing", "; ".join(ln for ln in fresh if "talk" in ln)[:200])
    g.netsync("bench", 0)
    g.netsync("selftest", 0)
    g.check(g.state.netsync is not None and not g.state.netsync["forced"], "the override was released", "")
