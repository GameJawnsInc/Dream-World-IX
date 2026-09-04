"""F3 dialogue L2 lockstep -- the SOLO benches, run unattended (s83 rev 5 `netsync` verbs).

F3 (wire v12, built 2026-07-23) makes a co-located guest's copy of the host's blocking scene advance
and branch on the HOST's confirms: the host taps `Dialog.OnKeyConfirm` and pushes one 8-byte
TypeDialog frame per page; the guest's `ServiceDialogLockstep` peeks the frame until its own
frontmost window matches `(field, winnum, textId)`, then drives that window's `OnKeyConfirm` itself.
Its three solo benches were designed as ~ debug-menu buttons and had never been run -- the menu is
IMGUI, which no injected controller input can press. This scenario runs them through the same static
entry points, in a `Role=selftest` session the harness forces for this process only (Memoria.ini is
never touched; the override is released on disarm, fault and `reset`).

What is asserted, and why each is an OUTCOME rather than an ack:

  B1  ADVANCE -- one injected frame against an open plain window turns exactly ONE page, and the
      pages the lockstep walks are the SAME pages a player's own Confirm walks (the transcript is
      measured locally first, then reproduced by injection). "Never two page-skips" (B6) falls out of
      the equality: a double-advance would drop a page from the lockstep transcript.
  B2  CHOICE -- an injected choice frame forces the host's index (bounds-checked `TrySetCurrentChoice`)
      and confirms it; the window it leads to is the window a local `choose(index)` leads to. An
      OUT-OF-RANGE index is refused by the bounds check, logged once, and the menu still closes on the
      local default -- the guest is never wedged on a bad frame.
  B5  UNMATCHED -- a frame no window can match is HELD with the timeout armed, the guest's own Confirm
      keeps working while it is held (S3: a held-unmatched frame never suppresses), and the hold
      releases at DialogWaitMs (8000 ms) with the one "timed out -- local advance restored" line.
  L1  the host-event flag pins control only once the scene ENDS (pin-only-if-the-guest-still-had-
      control), and releases it when the flag falls.
  RESET -- the forced selftest, the bench lever and the L1 pin are all released by `reset`, so a
      leaked run cannot hand the next scenario -- or the next player -- a ghost or a frozen character.

⚠ WHICH WINDOWS MAY BE INJECTED INTO. A frame is only ever applied to a window the HOST confirmed
through `Dialog.OnKeyConfirm`'s Hide branch -- that is where the host tap lives. A `[NFOC]` / `[TIME]`
window sets `ignoreInputFlag`, so `OnKeyConfirm` never Hides it and the host never emits for it: on a
real link no frame can target such a window. The first run of this scenario injected into one anyway
(the journal bench's polled status pages are `[NTUR][NFOC]` + a `B_KEYON` poll + a script
`CloseWindow`), the apply "succeeded" without closing anything, and the lockstep then held `suppress`
for as long as the page stayed open. That is the bench fabricating an out-of-spec frame, not an engine
defect -- but it is exactly the class of frame the guard below refuses to fabricate. Unknown windows
are paged out LOCALLY, which for a polled page is the script's own close.

Bench 30801 (the journal dashboard): WEST (-210, -837) is a plain window, EAST (210, -837) the
15-option journal menu (it cannot be cancelled -- take a branch and page out).

    py tools/play.py studies/test-harness/scenarios/coop_dialogue_lockstep.py --field 30801
"""
import time

FIELD = 30801
WEST = (-210.0, -837.0)         # a plain text window
EAST = (210.0, -837.0)          # the choice menu
WANT = "Tetra Master"           # a named option, so the index is the engine's own, not our arithmetic
MAX_PAGES = 14
IGNORES_INPUT = ("[NFOC]", "[TIME=")    # the tags that set Dialog.ignoreInputFlag


def _log_lines(g) -> list[str]:
    p = g.engine_log()
    if p is None:
        return []
    try:
        return p.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def _new_log(g, mark: int) -> list[str]:
    return _log_lines(g)[mark:]


def _count(lines: list[str], needle: str) -> int:
    return sum(1 for ln in lines if needle in ln)


def _ignores_input(st) -> bool:
    return any(tag in raw for raw in st.raw_texts for tag in IGNORES_INPUT)


def _follow_up(g, *, timeout: float = 4.0) -> str:
    """The text of the window a closed choice LEADS TO -- waited for, since it opens a beat later.

    Sampling the state on the frame the menu closes reads an empty screen: the follow-up window is
    constructed by the script on a later tick. The first run of this scenario compared '' against the
    real follow-up and reported a branch mismatch that did not exist.
    """
    st = g.wait_for(lambda s: s.choice is None, timeout=timeout, what="the choice menu to close")
    try:
        st = g.wait_for(lambda s: s.dialog_open and bool(s.text.strip()), timeout=3.0,
                        what="the follow-up window to open with text")
    except Exception:
        return ""
    return st.text


def _page_out_locally(g, *, max_presses: int = 24) -> bool:
    """Close whatever is open with the player's OWN Confirm -- the only legitimate close for a window
    the host could never confirm (a polled `[NFOC]` page closes through the script's own key poll).
    A choice on the way is taken at its default. Returns whether the screen ended up clear."""
    for _ in range(max_presses):
        st = g.state
        if not st.dialog_open:
            return True
        g.press("confirm", 4)
        g.wait_frames(12)
    return not g.state.dialog_open


def _inject_until_closed(g, first_page: str, *, max_pages: int = MAX_PAGES) -> tuple[list[str], int]:
    """Drive the open window to its close with injected ADVANCE frames. Returns (pages, injects).

    Stops -- without injecting -- at a choice or at a window that ignores input (see the module
    note): both are windows a host frame could never legitimately target.
    """
    pages = [first_page]
    injects = 0
    for _ in range(max_pages):
        before = g.state
        if not before.dialog_open or before.choice is not None or _ignores_input(before):
            break
        g.netsync("advance")
        injects += 1
        last = pages[-1]
        st = g.wait_for(lambda s: (not s.dialog_open) or s.choice is not None
                        or (s.text.strip() and s.text != last),
                        timeout=6.0, what="the injected advance to page or close the window")
        if st.netsync["pending"] is not None:
            # A HELD frame after a match means the window was still printing on the tick the frame
            # arrived (fast-forward + hold, B6) -- it applies on the next tick, so give it one.
            st = g.wait_for(lambda s: s.netsync["pending"] is None, timeout=3.0,
                            what="the held frame to apply once the window finished printing")
        if not st.dialog_open or st.choice is not None:
            break
        pages.append(st.text)
    return pages, injects


def _open_at(g, xz, *, want_choice: bool):
    g.walk_to(*xz, tolerance=45, strict=False)
    opened = g.interact(timeout=6.0)
    ok = opened is not None and (opened.choice is not None) == want_choice
    g.check(ok, f"the {'east' if xz == EAST else 'west'} responder opened a "
                f"{'choice' if want_choice else 'plain'} window", repr(opened))
    return opened if ok else None


def _engage(g):
    """Bench ON + L1 ON, in that order, AFTER a window is open (bench ON suppresses new talks)."""
    g.netsync("bench", 1)
    return g.netsync("l1", 1)


def _disengage(g):
    st = g.netsync("l1", 0)
    g.netsync("bench", 0)
    return st


def _clear_screen(g, what: str) -> None:
    """Disengage, page out locally, and assert the screen is clear before the next bench opens."""
    _disengage(g)
    cleared = _page_out_locally(g)
    g.check(cleared, f"the screen was cleared locally after {what}", repr(g.state))
    g.wait_for(lambda s: s.control, timeout=6.0, what=f"control back after {what}")
    g.wait_frames(20)


def run(g, field: int = FIELD):
    g.note("F3 dialogue L2 lockstep: the solo benches (advance / choice / unmatched-timeout)")
    g.newgame()
    g.warp(field)
    g.wait_frames(60)
    g.calibrate_axes()

    # ---- B0: the forced selftest role, and every gate closed by default ---------------------
    mark = len(_log_lines(g))
    st = g.netsync("selftest", 1)
    ns = st.netsync
    g.check(ns is not None and ns["selftest"] and ns["instance"] and ns["forced"],
            "the harness forced the selftest role for this process (Memoria.ini untouched)", repr(ns))
    g.check(ns is not None and not ns["bench"] and not ns["l1"] and not ns["suppress"]
            and ns["pending"] is None,
            "every lockstep gate is closed by default (bench off, L1 off, no suppress, no frame)", repr(ns))
    g.wait_frames(30)
    fresh = _new_log(g, mark)
    g.check(_count(fresh, "selftest role FORCED") == 1,
            "the engine logged the override once", f"{len(fresh)} new log lines")
    g.check(_count(fresh, "gEventGlobal codec round-trip OK") == 1,
            "the selftest tick ran its own codec proof (the session is live)",
            "; ".join(ln for ln in fresh if "selftest" in ln)[:300])
    g.shot("lockstep-00-selftest")

    # ---- B3 first: the VANILLA transcript of the west window, paged by the player's own Confirm --
    opened = _open_at(g, WEST, want_choice=False)
    if opened is None:
        return
    g.check(not _ignores_input(opened),
            "the west window accepts Confirm (no [NFOC]/[TIME] -- a window the host CAN confirm)",
            repr(opened.raw_texts)[:200])
    local_pages = list(dict.fromkeys([opened.text] + g.advance(max_pages=MAX_PAGES)))
    g.check(len(local_pages) >= 1 and not g.state.dialog_open,
            "the west window paged to its close locally (the reference transcript)",
            f"{len(local_pages)} page(s): {local_pages[0][:50]!r}...")
    g.wait_frames(20)

    # ---- B1: the same window, driven by injected ADVANCE frames ---------------------------------
    opened = _open_at(g, WEST, want_choice=False)
    if opened is None:
        return
    mark = len(_log_lines(g))
    st = _engage(g)
    g.check(st.netsync["l1"] and not st.netsync["l1_forced_control"],
            "L1 ON with a window open did NOT take control (the script already holds it -- "
            "pin-only-if-the-guest-still-had-control)", repr(st.netsync))
    g.shot("lockstep-01-west-engaged")
    pages, injects = _inject_until_closed(g, opened.text)
    after = g.state
    g.check(not after.dialog_open,
            "injected advances paged the west window to its close", f"{injects} inject(s)")
    g.check(pages == local_pages,
            "the lockstep transcript equals the local transcript, page for page "
            "(one inject = exactly one page; never two page-skips)",
            f"lockstep={pages!r}\n    local={local_pages!r}")
    g.check(after.netsync["pending"] is None and not after.netsync["suppress"]
            and after.netsync["align_win"] == -1,
            "after the close: frame consumed, suppress released, no window under lockstep",
            repr(after.netsync))
    fresh = _new_log(g, mark)
    g.check(_count(fresh, "dialog lockstep: advanced win") == injects,
            "one 'dialog lockstep: advanced win' line per inject",
            f"{_count(fresh, 'dialog lockstep: advanced win')} lines for {injects} injects")
    g.check(_count(fresh, "codec round-trip FAILED") == 0 and _count(fresh, "dialog bench failed") == 0,
            "no codec or bench failure was logged", "")
    # The scene ended with L1 still ON: NOW the pin takes control (the guest had it back).
    st = g.wait_for(lambda s: s.netsync["l1_forced_control"], timeout=5.0,
                    what="the L1 pin to take control once the scene ended")
    g.check(st.netsync["l1_pinned"] and not st.control,
            "L1 pins control once the scene ends (the co-located guest waits for the host)", repr(st.netsync))
    _disengage(g)
    st = g.wait_for(lambda s: s.control, timeout=5.0, what="control to return when the L1 flag falls")
    g.check(st.control and not st.netsync["l1_pinned"] and not st.netsync["l1_forced_control"],
            "L1 OFF releases the pin and hands control back", repr(st.netsync))
    g.wait_frames(20)

    # ---- B2: a CHOICE, forced to a named index --------------------------------------------------
    opened = _open_at(g, EAST, want_choice=True)
    if opened is None:
        return
    names = g.options()
    target = WANT if WANT in names else names[min(3, len(names) - 1)]
    index = g.option_index(target)
    # Reference: what does choosing this option LOCALLY lead to?
    g.choose(index)
    local_follow = _follow_up(g)
    g.check(bool(local_follow.strip()), f"choosing {target!r} locally leads to a window",
            local_follow[:80])
    _clear_screen(g, "the local choice")

    opened = _open_at(g, EAST, want_choice=True)
    if opened is None:
        return
    mark = len(_log_lines(g))
    _engage(g)
    g.shot("lockstep-02-east-engaged")
    g.netsync("choice", index)
    follow = _follow_up(g)
    st = g.state
    g.check(st.choice is None and st.netsync["pending"] is None,
            f"an injected choice frame (index {index} = {target!r}) closed the menu and was consumed",
            repr(st.netsync))
    g.check(follow == local_follow,
            "the window the lockstep's choice leads to is the window the local choice leads to",
            f"lockstep={follow[:80]!r} local={local_follow[:80]!r}")
    fresh = _new_log(g, mark)
    g.check(_count(fresh, "dialog lockstep: choice win") == 1 and _count(fresh, f"-> index {index}") == 1,
            "the engine logged the forced choice with the host's index",
            "; ".join(ln for ln in fresh if "lockstep" in ln)[:300])
    _clear_screen(g, "the lockstep choice")

    # ---- B2b: an OUT-OF-RANGE choice index -- refused by the bounds check, never a wedge ---------
    opened = _open_at(g, EAST, want_choice=True)
    if opened is None:
        return
    count = int(opened.choice.get("count", 0))
    mark = len(_log_lines(g))
    _engage(g)
    g.netsync("choice", count + 40)
    st = g.wait_for(lambda s: s.choice is None, timeout=6.0,
                    what="the out-of-range choice frame to still close the menu on the local default")
    fresh = _new_log(g, mark)
    g.check(_count(fresh, "out of range") == 1 and "local default" in " ".join(fresh),
            f"index {count + 40} of {count} was refused by TrySetCurrentChoice and logged once",
            "; ".join(ln for ln in fresh if "range" in ln)[:300])
    g.check(st.choice is None and st.netsync["pending"] is None,
            "the bad frame still confirmed the local default -- the guest is not wedged", repr(st.netsync))
    _clear_screen(g, "the out-of-range choice")

    # ---- B5: an UNMATCHED frame -- held, local input untouched, released at DialogWaitMs --------
    opened = _open_at(g, WEST, want_choice=False)
    if opened is None:
        return
    mark = len(_log_lines(g))
    _engage(g)
    t0 = time.time()
    st = g.netsync("unmatched")
    pend = st.netsync["pending"]
    g.check(pend is not None and pend["win"] == 15 and pend["text"] == 0xFFFF,
            "the unmatched frame (win 15 / text 0xFFFF) is HELD in the one-slot holder", repr(pend))
    g.check(st.netsync["wait_armed"] and st.netsync["wait_ms"] >= 0,
            "the hold timeout is armed against a real tick baseline", repr(st.netsync))
    g.check(not st.netsync["suppress"],
            "S3: a held-UNMATCHED frame never suppresses the guest's own input", repr(st.netsync))
    # The player's OWN Confirm must still page the window while the frame is held. Pressed the way a
    # player presses -- repeatedly -- because a window still typewriting eats the FIRST Confirm as a
    # fast-forward (Dialog.OnKeyConfirm -> AdvanceProgressToMax) and closes on the next; the third
    # run of this scenario pressed once, watched the window sit there fully printed, and blamed the
    # hold. (The injected path never sees this: its apply fast-forwards, HOLDS, and re-applies.)
    page_before = st.text
    presses = 0
    for _ in range(8):
        g.press("confirm", 4)
        presses += 1
        g.wait_frames(12)
        st = g.state
        if (not st.dialog_open) or (st.text.strip() and st.text != page_before):
            break
    g.check((not st.dialog_open) or st.text != page_before,
            "the player's own Confirm still pages the window while a frame is held",
            f"{presses} press(es); {repr(st)}")
    g.check(st.netsync["pending"] is not None,
            "local paging did not consume the held frame (it matches nothing)", repr(st.netsync["pending"]))
    limit = int(st.netsync["wait_limit_ms"])
    st = g.wait_for(lambda s: s.netsync["pending"] is None, timeout=limit / 1000.0 + 6.0,
                    what=f"the held frame to time out at DialogWaitMs ({limit} ms)")
    held_for = time.time() - t0
    g.check(limit * 0.9 / 1000.0 <= held_for <= limit / 1000.0 + 4.0,
            f"the hold released at about DialogWaitMs ({limit} ms)", f"released after {held_for:.1f}s")
    g.check(not st.netsync["wait_armed"] and not st.netsync["suppress"],
            "after the timeout: the clock is disarmed and local input is restored", repr(st.netsync))
    fresh = _new_log(g, mark)
    g.check(_count(fresh, "timed out -- local advance restored") == 1,
            "exactly one 'timed out -- local advance restored' line (never per-frame spam)",
            f"{_count(fresh, 'timed out')} line(s)")
    _clear_screen(g, "the timeout bench")

    # ---- RESET releases everything the verbs did --------------------------------------------------
    g.netsync("bench", 1)
    g.netsync("l1", 1)
    st = g.wait_for(lambda s: s.netsync["l1_forced_control"], timeout=5.0,
                    what="the L1 pin to hold control before the reset")
    g.send("reset")
    st = g.wait_for(lambda s: s.netsync is not None and not s.netsync["forced"], timeout=5.0,
                    what="`reset` to release the forced selftest")
    g.check(not st.netsync["enabled"] and not st.netsync["bench"] and not st.netsync["l1"]
            and not st.netsync["l1_pinned"],
            "`reset` released the selftest override, the bench lever and the L1 pin", repr(st.netsync))
    st = g.wait_for(lambda s: s.control, timeout=5.0, what="control back after the reset released the pin")
    g.check(st.control, "the character is not left frozen by a released run", repr(st.netsync))
    g.shot("lockstep-09-released")
