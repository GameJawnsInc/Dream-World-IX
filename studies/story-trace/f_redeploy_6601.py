"""F-REDEPLOY, 6601 -- the spliced Lantern Hall (TEST6601, FF9CustomMap-world), reached the real way and then made to
clear an arriving ambient mark in BOTH slots.

    py tools/play.py studies/story-trace/f_redeploy_6601.py --label f-redeploy-6601

6601 was spliced by tools/ambient_splice.py: its live .eb plus exactly the 38-byte ambient TAIL. Its real ways in
(the hub's pick, the worldmap quay, the ferry) all arrive with Byte[13] = 0 as far as is known: the hub clears its own
mark before its warp. So the natural route can only show the TAIL does no harm. The clear itself is exercised the way
story-rung5b2's P-AMBIENT did, but in both slots: gEventGlobal[13] and [14] are poked to 2 (the "ambient still playing"
value; field 70 wrote exactly that in f_redeploy_4600) in the hub, after its own Main_Init, and the harness's debug
warp (which, like any kit warp, skips stock's exit idiom) then enters 6601.

Checks, registered before the run:
B0  preflight (read-only): 6601's live US .eb reads `restored` and is the spliced bytes (sha cf6bce36...)
B1  the natural route: New Game -> 70 -> 4600 -> "The Southern Ring" -> 6601 with control; there
    gEventGlobal[13] == [14] == 0 (watched bits). Report-only: every Byte[13]/[14] row 6601 wrote.
B2  the hall plays: the player walks; the Purser's menu lists the five "Sail to ..." rows and ends with
    "Nothing for now."; picking that last row keeps him in 6601 and gives control back once its reply is paged out
B3  a frame of 6601 taken 30 ticks after control returns (after its 16-tick fade-in), for a human-eye read
B4  THE CLEAR, both slots: after a warp to the hub, poking [13] = [14] = 2 there, and a debug warp into 6601, 6601's
    Main_Init (entry 0,
    tag 0) writes [13] 2 -> 9 and [14] 2 -> 9 at the prologue's ips, then [13] 9 -> 0 and [14] 9 -> 0 at the TAIL's
    ips (all four predicted from the live bytes), and the bits then read [13] == [14] == 0
B5  no exception thrown through EventEngine/EBin/StoryTrace/HarnessAgent for the whole run
RESULT (2026-09-29, run 20260929-180801-f-redeploy-6601, archived in the MAIN repo's .harness-runs): 5/5 PASS, 171 s.
Natural arrival: 6601 wrote [13] 0 -> 0 (ip131) and [14] 0 -> 0 (ip212), the prologue's own none-branch, and the TAIL
had nothing to clear. The Purser's menu read the five Sail rows, "Log the passage." and "Nothing for now."; the
decline left him in 6601 with control. The clear path wrote [13] 2 -> 9 ip109, [14] 2 -> 9 ip190, [13] 9 -> 0 ip275,
[14] 9 -> 0 ip294 -- all four as predicted -- and the bits read 0: slot 1's clear, first seen in game. Both hall
frames show the room after its fade-in.

The ip model is f_redeploy_4600's (calibrated on story-rung5b2's archived rows, and it held there).
"""
from __future__ import annotations

import hashlib
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from f_redeploy_4600 import THROWS, WHERE, _byte, predicted_ips        # noqa: E402

HUB, NG, HALL = 4600, 70, 6601
NAME = "TEST6601"
SPLICED_US = "cf6bce369390357e"
STILTZKIN, PURSER = (600.0, 127.0), (130.0, -1650.0)
HUB_TWIST, HALL_TWIST = 255, 246
SAILS = ["Sail to Ashvale", "Sail to Tidefall", "Sail to Grimhorn", "Sail to Larkspur", "Sail to Farshore"]
DECLINE = "Nothing for now."
BITS = range(104, 120)                                   # gEventGlobal[13] and [14]


def _live_eb(g) -> bytes:
    p = next((g.game_path / "FF9CustomMap-world" / "StreamingAssets").rglob(f"field/us/EVT_{NAME}.eb.bytes"))
    return p.read_bytes()


def _pad_toward(basis: dict, vec) -> str:
    """The pad direction whose calibrated world vector points most nearly along ``vec`` (rung5_hub's rule)."""
    n = math.hypot(*vec) or 1.0
    ux, uz = vec[0] / n, vec[1] / n
    cand = [("up", basis["v"]), ("down", (-basis["v"][0], -basis["v"][1])),
            ("right", basis["h"]), ("left", (-basis["h"][0], -basis["h"][1]))]
    return max(cand, key=lambda c: c[1][0] * ux + c[1][1] * uz)[0]


def talk_to(g, basis: dict, spot, *, tries: int = 3):
    """Walk to the talker nearest ``spot`` (its west side, inside its talk ring), face it, Confirm. The box or None."""
    objs = g.wait_for(lambda s: s.objects is not None, timeout=5.0, what="the field's objects").objects
    o = min((b for b in objs if b.get("talk")), key=lambda b: math.hypot(b["x"] - spot[0], b["z"] - spot[1]))
    r, tr = o["r"], o["talk_r"]
    d = max(r + 8, min(tr - 8, r + 24))
    g.walk_to(o["x"] - d, o["z"], tolerance=15, strict=False, slides=True)
    for _ in range(tries):
        now = g.state
        pad = _pad_toward(basis, (o["x"] - now.player_x, o["z"] - now.player_z))
        if now.facing_status != "cannot":
            g.turn_in_place(pad, 8)
        box = g.interact(timeout=6.0)
        if box is not None:
            return box
        g.walk(pad, 2)
    return None


def _hall_rows(g, since_line: int) -> list:
    return [r for r in g.story_rows() if r.k == "w" and r.fld == HALL and r.sid == 0 and r.tag == 0
            and r.byte in (13, 14) and r.line > since_line]


def _watch(g) -> None:
    g.watch(*BITS)
    g.wait_for(lambda s: all(s.flag(b) is not None for b in BITS), timeout=5.0, what="bits 104-119")


def run(g) -> None:
    from harness import HarnessError
    from ff9mapkit.content import ambient, movement

    g.note("F-REDEPLOY 6601: the spliced Lantern Hall, natural route then the two-slot clear")
    live = _live_eb(g)
    sha = hashlib.sha256(live).hexdigest()
    g.check(ambient.classify(live) == "restored" and sha.startswith(SPLICED_US),
            "B0: 6601's live US .eb is the spliced one", f"{ambient.classify(live)}, sha {sha[:16]}")
    ips = predicted_ips(live)
    print(f"[6601] predicted ips {ips}")

    st = g.newgame()
    mark = g.log_mark()
    g.storytrace(True)
    g.wait_for(lambda s: s.field_id not in (NG, 0), timeout=300.0, what="field 70 to leave on its own")
    if g.state.field_id != HUB:
        g.check(False, "B1: the natural route reaches the hub", f"field 70 left to {g.state.field_id}")
        return
    g.wait_playable(timeout=90.0)

    # B1 -- the hub's pick into the hall
    hub_basis = g.calibrate_axes(prior=movement.key_move_basis(HUB_TWIST))
    if talk_to(g, hub_basis, STILTZKIN) is None:
        g.check(False, "B1: the natural route reaches 6601", "Stiltzkin's menu never opened")
        return
    g.wait_for(lambda s: g._choice_ready(s), timeout=10.0, what="the journey menu")
    g.select(g.option_index("The Southern Ring"))
    g.press("confirm")
    try:
        g.wait_for(lambda s: s.field_id == HALL, timeout=60.0, what="the pick to land in 6601")
        g.wait_playable(timeout=60.0)
    except HarnessError as err:
        g.check(False, "B1: the natural route reaches 6601 with control", str(err)[:200])
        return
    _watch(g)
    b13, b14 = _byte(g, 13), _byte(g, 14)
    nat = _hall_rows(g, 0)
    print(f"[6601] natural arrival rows: {[(r.byte, r.ip, r.old, r.new) for r in nat]}")
    g.check(b13 == 0 and b14 == 0, "B1: New Game -> hub -> 6601 with control; [13] and [14] read 0 in the hall",
            f"[13]={b13} [14]={b14}")

    # B3 -- a frame after the fade-in
    g.wait_frames(g.rate().frames_for_ticks(30))
    g.shot("hall-natural")

    # B2 -- the hall plays: walk, the Purser's menu, the decline row
    here = g.state
    basis = g.calibrate_axes(prior=movement.key_move_basis(HALL_TWIST))
    box = talk_to(g, basis, PURSER)
    now = g.state
    walked = math.hypot(now.player_x - here.player_x, now.player_z - here.player_z)
    ok_menu, detail = False, f"walked {walked:.0f}u; no dialogue after 3 tries"
    if box is not None:
        g.wait_for(lambda s: g._choice_ready(s), timeout=10.0, what="the Purser's menu")
        names = g.options()
        g.shot("purser-menu")
        g.select(len(names) - 1)
        g.press("confirm")
        for _ in range(12):                               # page out the decline reply like a player
            g.wait_frames(20)
            s = g.state
            if s.field_id != HALL or (s.control and not s.dialog_open):
                break
            if s.dialog_open and g._choice_ready(s) is False:
                g.press("confirm")
        s = g.state
        ok_menu = (all(n in names for n in SAILS) and names[-1] == DECLINE and s.field_id == HALL and s.control
                   and walked > 100)
        detail = f"walked {walked:.0f}u; options {names}; after the decline: field {s.field_id}, control {s.control}"
    g.check(ok_menu, "B2: the hall plays -- walk, the Purser's ferry menu, the decline row stays", detail)

    # B4 -- THE CLEAR in both slots: arrive with 2 (ambient playing, no exit idiom) and watch 6601 clear it. The poke
    # is made in the hub, AFTER its Main_Init ran, so nothing there touches it; a same-field warp would not do --
    # warp() waits on the field id, which a re-entry of 6601 satisfies before the reload even starts.
    g.warp(HUB)
    g.poke(13, 2)
    g.poke(14, 2)
    g.wait_for(lambda s: _byte(g, 13) == 2 and _byte(g, 14) == 2, timeout=5.0, what="the poke to land")
    line0 = max((r.line for r in g.story_rows()), default=0)
    g.warp(HALL)
    a13, a14 = _byte(g, 13), _byte(g, 14)
    rows = _hall_rows(g, line0)
    for r in rows:
        print(f"[6601] clear-path row: byte {r.byte} ip {r.ip} {r.old} -> {r.new}")

    def hit(n, kind, old, new):
        return any(r.byte == n and r.ip == ips[(n, kind)] and r.old == old and r.new == new for r in rows)

    marks = {n: hit(n, "set9", 2, 9) for n in (13, 14)}
    clears = {n: hit(n, "tail0", 9, 0) for n in (13, 14)}
    g.check(all(marks.values()) and all(clears.values()) and a13 == 0 and a14 == 0,
            "B4: arriving with [13] = [14] = 2, 6601 marks both 9 and its TAIL clears both 9 -> 0",
            f"marks {marks}, clears {clears} at predicted {ips}; bits after [13]={a13} [14]={a14}")
    g.wait_frames(g.rate().frames_for_ticks(30))
    g.shot("hall-after-clear")

    bad = [e for e in g.exceptions_since(mark) if e.name in THROWS
           and (not e.trace or any(k in fr for fr in e.trace for k in WHERE))]
    g.check(not bad, "B5: no exception through the event engine, the whole run",
            f"{[(e.name, e.where) for e in bad[:4]]}" if bad else "none")
    g.storytrace(False)
