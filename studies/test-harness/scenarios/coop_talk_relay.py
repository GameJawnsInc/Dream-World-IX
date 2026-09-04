"""F3.1 TALK RELAY -- the guest-side replay of a host's press-fired talk, proven solo.

The 2026-09-04 two-machine run at Dali found the gap: an NPC talk is press-fired (tag 3), the F1
spectator gate returns before the guest could ever start one, and L1 pins the guest's control anyway
-- so the guest's copy of the talk never opened (no facing, no window) and every F3 lockstep frame for
it timed out. The relay: the host emits a state-lane section at the exact Request accept, and the
co-located guest becomes the object's listener and calls `ee.Request(obj, 1, 3)` on its own copy.

This scenario proves the GUEST-SIDE APPLY solo, through the same fabricated-section bench the harness
uses for the other co-op benches (`netsync talk <uid>`):

  1. talk to the west responder LOCALLY, read the uid the engine set as the player's listener
     (`player.listener` -- published for exactly this), and record the window's text;
  2. walk 300 units away (far outside any talk radius), inject `netsync talk <uid>`, and assert the
     SAME window opens -- the relay, not proximity, started it;
  3. an unknown uid is refused once and opens nothing.

The host tap (EmitTalkStartIfHost) and the section's ride on the wire can only be exercised on a real
link -- that is the laptop session.

    py tools/play.py studies/test-harness/scenarios/coop_talk_relay.py --field 30801
"""

FIELD = 30801
WEST = (-210.0, -837.0)
FAR = (90.0, -837.0)            # 300 units east of the west responder


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


def _page_out(g, *, max_presses=24):
    for _ in range(max_presses):
        if not g.state.dialog_open:
            return True
        g.press("confirm", 4)
        g.wait_frames(12)
    return not g.state.dialog_open


def run(g, field: int = FIELD):
    g.note("F3.1 talk relay: the guest-side replay of a press-fired talk, solo")
    g.newgame()
    g.warp(field)
    g.wait_frames(60)
    g.calibrate_axes()
    st = g.netsync("selftest", 1)
    g.check(st.netsync is not None and st.netsync["selftest"], "selftest role forced", repr(st.netsync))

    # ---- 1. learn the NPC's uid from a LOCAL talk -------------------------------------------
    g.walk_to(*WEST, tolerance=45, strict=False)
    opened = g.interact(timeout=6.0)
    if opened is None or opened.choice is not None:
        g.check(False, "the west responder opened a plain window locally", repr(opened))
        return
    uid = int(opened.raw.get("player", {}).get("listener", -1))
    west_text = opened.text
    # Actor.listener is a Byte and 255 means "nobody" -- a real target is 0..254.
    g.check(0 <= uid < 255, "the engine published the talk target's uid as player.listener", f"uid={uid}")
    g.check(_page_out(g), "the local window paged out", repr(g.state))
    g.wait_for(lambda s: s.control, timeout=6.0, what="control back after the local talk")
    g.wait_frames(20)
    if not 0 <= uid < 255:
        return

    # ---- 2. the relay, from far away ---------------------------------------------------------
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
    g.check(int(st.raw.get("player", {}).get("listener", -1)) == uid,
            "the player is the object's listener (the NPC faces the player)", repr(st.raw.get("player")))
    fresh = _log_lines(g)[mark:]
    g.check(_count(fresh, f"talk bench: fabricated SectionTalk obj {uid}") == 1
            and _count(fresh, f"talk relay: started obj {uid} (tag 3)") == 1,
            "the section round-tripped the real codec and the apply logged the start",
            "; ".join(ln for ln in fresh if "talk" in ln)[:300])
    g.netsync("bench", 0)
    g.check(_page_out(g), "the relayed window pages out with the player's own Confirm", repr(g.state))
    g.wait_for(lambda s: s.control, timeout=6.0, what="control back after the relayed talk")
    g.wait_frames(20)

    # ---- 3. an unknown uid is refused, opens nothing -----------------------------------------
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
