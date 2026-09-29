"""F-REDEPLOY, 6602 -- the spliced Lamplight (LAMPLIGHT, FF9CustomMap-world): Moglow's talk, and the two-slot clear.

    py tools/play.py studies/story-trace/f_redeploy_6602.py --label f-redeploy-6602

6602 was spliced by tools/ambient_splice.py: its live .eb plus exactly the 38-byte ambient TAIL. Its only way in is the
world-map beacon (case 52), which the harness cannot walk to, so it is entered by the harness's debug warp. Moglow's talk
handler is the one master's REBUILD would have changed (a DisableMove/EnableMove around his WindowSync); the splice
leaves it as deployed, and C2 checks it still plays.

Checks, registered before the run:
C0  preflight (read-only): 6602's live US .eb reads `restored` and is the spliced bytes (sha c414380e...)
C1  New Game, then a debug warp out of field 70 into 6602 with control; gEventGlobal[13] == [14] == 0 there
    (watched bits). Report-only: every Byte[13]/[14] row 6602 wrote (field 70's own ambient arrives as 1, not 2)
C2  the room plays: the player walks; Moglow's talk opens a window whose text contains "Lamplight"; paged out,
    it closes and control returns, still in 6602
C3  a frame of 6602 taken 30 ticks after control returns, for a human-eye read
C4  THE CLEAR, both slots: warp to the hub, poke [13] = [14] = 2 there (after its Main_Init), warp into 6602; 6602's
    Main_Init (entry 0, tag 0) writes [13] and [14] 2 -> 9 at the prologue's ips and 9 -> 0 at the TAIL's ips (all
    four predicted from the live bytes), and the bits then read [13] == [14] == 0
C5  no exception thrown through EventEngine/EBin/StoryTrace/HarnessAgent for the whole run

RESULT (2026-09-29, run 20260929-181555-f-redeploy-6602, archived in the MAIN repo's .harness-runs): 5/5 PASS, 37 s.
Warp arrival from field 70: 6602 wrote [13] 1 -> 0 (ip123, field 70's own ambient mark taken by the prologue's
none-branch) and [14] 0 -> 0 (ip204). Moglow's window read "Kupo! I keep the Lamplight lit -- ..." and paged out with
control back (walked 572u). The clear path wrote [13] 2 -> 9 ip101, [14] 2 -> 9 ip182, [13] 9 -> 0 ip267, [14] 9 -> 0
ip286, all as predicted, and the bits read 0. The frames show the tower after its fade-in.
"""
from __future__ import annotations

import hashlib
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from f_redeploy_4600 import THROWS, WHERE, _byte, predicted_ips        # noqa: E402
from f_redeploy_6601 import _pad_toward, _watch                         # noqa: E402

HUB, ROOM = 4600, 6602
NAME = "LAMPLIGHT"
SPLICED_US = "c414380e58ba6797"
MOGLOW = (-450.0, 200.0)
TWIST = 255
DOOR = [[804, -471], [553, -646], [1228, -1456], [1460, -1222]]      # the walk-out gateway's zone (worldmap)


def _live_eb(g) -> bytes:
    p = next((g.game_path / "FF9CustomMap-world" / "StreamingAssets").rglob(f"field/us/EVT_{NAME}.eb.bytes"))
    return p.read_bytes()


def _rows(g, since_line: int) -> list:
    return [r for r in g.story_rows() if r.k == "w" and r.fld == ROOM and r.sid == 0 and r.tag == 0
            and r.byte in (13, 14) and r.line > since_line]


def talk_from_my_side(g, basis: dict, spot, *, tries: int = 3):
    """Walk to the talker nearest ``spot``, stopping inside its talk ring on the line toward where the player stands
    (Moglow sits on the platform's west edge: an approach from his west would be off the floor), face it, Confirm."""
    objs = g.wait_for(lambda s: s.objects is not None, timeout=5.0, what="the field's objects").objects
    o = min((b for b in objs if b.get("talk")), key=lambda b: math.hypot(b["x"] - spot[0], b["z"] - spot[1]))
    r, tr = o["r"], o["talk_r"]
    d = max(r + 8, min(tr - 8, r + 24))
    here = g.state
    vx, vz = here.player_x - o["x"], here.player_z - o["z"]
    n = math.hypot(vx, vz) or 1.0
    g.walk_to(o["x"] + d * vx / n, o["z"] + d * vz / n, tolerance=15, strict=False, slides=True)
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


def run(g) -> None:
    from ff9mapkit.content import ambient, movement

    g.note("F-REDEPLOY 6602: the spliced Lamplight, Moglow's talk, then the two-slot clear")
    live = _live_eb(g)
    sha = hashlib.sha256(live).hexdigest()
    g.check(ambient.classify(live) == "restored" and sha.startswith(SPLICED_US),
            "C0: 6602's live US .eb is the spliced one", f"{ambient.classify(live)}, sha {sha[:16]}")
    ips = predicted_ips(live)
    print(f"[6602] predicted ips {ips}")

    g.newgame()
    mark = g.log_mark()
    g.storytrace(True)
    g.warp(ROOM)
    _watch(g)
    b13, b14 = _byte(g, 13), _byte(g, 14)
    print(f"[6602] warp arrival rows: {[(r.byte, r.ip, r.old, r.new) for r in _rows(g, 0)]}")
    g.check(b13 == 0 and b14 == 0, "C1: New Game -> debug warp -> 6602 with control; [13] and [14] read 0",
            f"[13]={b13} [14]={b14}")

    g.wait_frames(g.rate().frames_for_ticks(30))
    g.shot("lamplight-arrival")

    here = g.state
    basis = g.calibrate_axes(prior=movement.key_move_basis(TWIST), hazards=[DOOR])
    box = talk_from_my_side(g, basis, MOGLOW)
    now = g.state
    walked = math.hypot(now.player_x - here.player_x, now.player_z - here.player_z)
    text = ""
    if box is not None:
        g.wait_frames(20)
        text = g.state.text or ""
        g.shot("moglow-talk")
        for _ in range(12):                               # page it out like a player
            s = g.state
            if s.field_id != ROOM or (s.control and not s.dialog_open):
                break
            g.press("confirm")
            g.wait_frames(20)
    s = g.state
    g.check(box is not None and "Lamplight" in text and s.field_id == ROOM and s.control and not s.dialog_open
            and walked > 100,
            "C2: the room plays -- walk, Moglow's line, paged out with control back",
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
        print(f"[6602] clear-path row: byte {r.byte} ip {r.ip} {r.old} -> {r.new}")

    def hit(n, kind, old, new):
        return any(r.byte == n and r.ip == ips[(n, kind)] and r.old == old and r.new == new for r in rows)

    marks = {n: hit(n, "set9", 2, 9) for n in (13, 14)}
    clears = {n: hit(n, "tail0", 9, 0) for n in (13, 14)}
    g.check(all(marks.values()) and all(clears.values()) and a13 == 0 and a14 == 0,
            "C4: arriving with [13] = [14] = 2, 6602 marks both 9 and its TAIL clears both 9 -> 0",
            f"marks {marks}, clears {clears} at predicted {ips}; bits after [13]={a13} [14]={a14}")
    g.wait_frames(g.rate().frames_for_ticks(30))
    g.shot("lamplight-after-clear")

    bad = [e for e in g.exceptions_since(mark) if e.name in THROWS
           and (not e.trace or any(k in fr for fr in e.trace for k in WHERE))]
    g.check(not bad, "C5: no exception through the event engine, the whole run",
            f"{[(e.name, e.where) for e in bad[:4]]}" if bad else "none")
    g.storytrace(False)
