"""F-REDEPLOY, 6603 -- the spliced Farshore landing (FARSHORE, FF9CustomMap-world): Mogdrift's talk, and the two-slot clear.

    py tools/play.py studies/story-trace/f_redeploy_6603.py --label f-redeploy-6603

6603 was spliced by tools/ambient_splice.py: its live .eb plus exactly the 38-byte ambient TAIL. Its ways in are the
world map's East Bay beacon (case 62) and the ferry's Farshore landing, both beyond the harness, so it is entered by
debug warp, as 6602 was. The spawn stands ~193u from the walk-out door's zone, so the calibration is told the zone.

Checks, registered before the run:
D0  preflight (read-only): 6603's live US .eb reads `restored` and is the spliced bytes (sha d4b74dd4...)
D1  New Game, then a debug warp out of field 70 into 6603 with control; gEventGlobal[13] == [14] == 0 there.
    Report-only: every Byte[13]/[14] row 6603 wrote
D2  the landing plays: the player walks; Mogdrift's talk opens a window whose text contains "nothing out here";
    paged out, it closes and control returns, still in 6603
D3  a frame of 6603 taken 30 ticks after control returns, for a human-eye read
D4  THE CLEAR, both slots: warp to the hub, poke [13] = [14] = 2 there, warp into 6603; 6603's Main_Init writes [13]
    and [14] 2 -> 9 at the prologue's ips and 9 -> 0 at the TAIL's ips (predicted from the live bytes), and the bits
    then read [13] == [14] == 0
D5  no exception thrown through EventEngine/EBin/StoryTrace/HarnessAgent for the whole run
"""
from __future__ import annotations

import hashlib
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from f_redeploy_4600 import THROWS, WHERE, _byte, predicted_ips        # noqa: E402
from f_redeploy_6601 import _watch                                      # noqa: E402
from f_redeploy_6602 import talk_from_my_side                           # noqa: E402

HUB, ROOM = 4600, 6603
NAME = "FARSHORE"
SPLICED_US = "d4b74dd4735cb4de"
MOGDRIFT = (1600.0, -700.0)
TWIST = 212
DOOR = [[285, -352], [875, -460], [424, -2944], [-166, -2836]]         # the walk-out gateway's zone (worldmap)
LINE = "nothing out here"


def _live_eb(g) -> bytes:
    p = next((g.game_path / "FF9CustomMap-world" / "StreamingAssets").rglob(f"field/us/EVT_{NAME}.eb.bytes"))
    return p.read_bytes()


def _rows(g, since_line: int) -> list:
    return [r for r in g.story_rows() if r.k == "w" and r.fld == ROOM and r.sid == 0 and r.tag == 0
            and r.byte in (13, 14) and r.line > since_line]


def run(g) -> None:
    from ff9mapkit.content import ambient, movement

    g.note("F-REDEPLOY 6603: the spliced Farshore landing, Mogdrift's talk, then the two-slot clear")
    live = _live_eb(g)
    sha = hashlib.sha256(live).hexdigest()
    g.check(ambient.classify(live) == "restored" and sha.startswith(SPLICED_US),
            "D0: 6603's live US .eb is the spliced one", f"{ambient.classify(live)}, sha {sha[:16]}")
    ips = predicted_ips(live)
    print(f"[6603] predicted ips {ips}")

    g.newgame()
    mark = g.log_mark()
    g.storytrace(True)
    g.warp(ROOM)
    _watch(g)
    b13, b14 = _byte(g, 13), _byte(g, 14)
    print(f"[6603] warp arrival rows: {[(r.byte, r.ip, r.old, r.new) for r in _rows(g, 0)]}")
    g.check(b13 == 0 and b14 == 0, "D1: New Game -> debug warp -> 6603 with control; [13] and [14] read 0",
            f"[13]={b13} [14]={b14}")

    g.wait_frames(g.rate().frames_for_ticks(30))
    g.shot("farshore-arrival")

    here = g.state
    basis = g.calibrate_axes(prior=movement.key_move_basis(TWIST), hazards=[DOOR])
    box = talk_from_my_side(g, basis, MOGDRIFT)
    now = g.state
    walked = math.hypot(now.player_x - here.player_x, now.player_z - here.player_z)
    text = ""
    if box is not None:
        g.wait_frames(20)
        text = g.state.text or ""
        g.shot("mogdrift-talk")
        for _ in range(12):                               # page it out like a player
            s = g.state
            if s.field_id != ROOM or (s.control and not s.dialog_open):
                break
            g.press("confirm")
            g.wait_frames(20)
    s = g.state
    g.check(box is not None and LINE in text.replace("\n", " ") and s.field_id == ROOM and s.control
            and not s.dialog_open and walked > 100,
            "D2: the landing plays -- walk, Mogdrift's line, paged out with control back",
            f"walked {walked:.0f}u; text {text[:80]!r}; after: field {s.field_id}, control {s.control}, "
            f"dialog {s.dialog_open}")

    g.warp(HUB)
    g.poke(13, 2)
    g.poke(14, 2)
    g.wait_for(lambda s: _byte(g, 13) == 2 and _byte(g, 14) == 2, timeout=5.0, what="the poke to land")
    line0 = max((r.line for r in g.story_rows()), default=0)
    g.warp(ROOM)
    a13, a14 = _byte(g, 13), _byte(g, 14)
    rows = _rows(g, line0)
    for r in rows:
        print(f"[6603] clear-path row: byte {r.byte} ip {r.ip} {r.old} -> {r.new}")

    def hit(n, kind, old, new):
        return any(r.byte == n and r.ip == ips[(n, kind)] and r.old == old and r.new == new for r in rows)

    marks = {n: hit(n, "set9", 2, 9) for n in (13, 14)}
    clears = {n: hit(n, "tail0", 9, 0) for n in (13, 14)}
    g.check(all(marks.values()) and all(clears.values()) and a13 == 0 and a14 == 0,
            "D4: arriving with [13] = [14] = 2, 6603 marks both 9 and its TAIL clears both 9 -> 0",
            f"marks {marks}, clears {clears} at predicted {ips}; bits after [13]={a13} [14]={a14}")
    g.wait_frames(g.rate().frames_for_ticks(30))
    g.shot("farshore-after-clear")

    bad = [e for e in g.exceptions_since(mark) if e.name in THROWS
           and (not e.trace or any(k in fr for fr in e.trace for k in WHERE))]
    g.check(not bad, "D5: no exception through the event engine, the whole run",
            f"{[(e.name, e.where) for e in bad[:4]]}" if bad else "none")
    g.storytrace(False)
