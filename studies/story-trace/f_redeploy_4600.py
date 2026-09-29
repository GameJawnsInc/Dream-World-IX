"""F-REDEPLOY, 4600 -- New Game into the spliced Southern Ring hub, with the story trace armed.

    py tools/play.py studies/story-trace/f_redeploy_4600.py --label f-redeploy-4600

4600 (SOUTHERN_RING_HUB, FF9CustomMap-world) was spliced by tools/ambient_splice.py: its live .eb plus exactly the
38-byte ambient TAIL, nothing else. This drives the REAL route: New Game, field 70's opening, and 70's own Field(4600)
through the New-Game override. No warp until the hub's own journey pick.

Checks, registered before the run:
A0  preflight (read-only): 4600's live US .eb reads `restored` and is the spliced bytes (sha 0653c519...)
A1  New Game lands in field 70, and field 70 leaves on its own script to 4600
A2  THE FIX: 4600's Main_Init (entry 0, tag 0) writes Global.Byte[13] 9 -> 0 at the TAIL's own ip. Report-only
    beside it: every Byte[13]/[14] row field 70 and 4600 wrote. If the prologue wrote 2 -> 9 first, that is the
    9 pre-fix bytes left behind. If it did not, the arriving value was not 2 and this route never needed the fix;
    that is reported, and A2 is then judged on "no 9 survives".
A3  once control returns in 4600, gEventGlobal[13] == 0 and [14] == 0, read from watched bits 104-119
    (independent of the trace)
A4  the hub plays: the player walks, Stiltzkin's menu offers exactly ["The Southern Ring", "Not yet, kupo..."]
    with the cursor on row 0, and the pick lands in 6601 with control back
A5  no exception thrown through EventEngine/EBin/StoryTrace/HarnessAgent from New Game to the 6601 landing
RESULT (2026-09-29, run 20260929-175641-f-redeploy-4600, archived in the MAIN repo's .harness-runs): 9/9 PASS, 150 s,
59.5 fps. The trace: field 70 ip475 Byte[13] 1 -> 2 (the New-Game override's hand-off, F-NG's flag half, first seen
in game), 4600 e0 t0 ip109 2 -> 9 (the prologue), ip275 9 -> 0 (the TAIL, as predicted); [13]=0 [14]=0 in the hub;
menu as registered; 6601 reached with control. The hall-arrival frame is black: it was taken 4 frames after control
came back, and 6601's unfixed bytes enable control after their 50-tick hold and only then fade in (16 ticks). So the
hall is proven by field and control, not seen.

The ip model, calibrated on story-rung5b2's archived P-AMBIENT rows (31113 ip109/ip275, reproduced from the live 31113
bytes before this run): a row's ip is the START of the storing instruction, relative to its ENTRY's start.
"""
from __future__ import annotations

import hashlib
import math
import sys
import time
from pathlib import Path

HUB, NG, HALL = 4600, 70, 6601
NAME = "SOUTHERN_RING_HUB"
SPLICED_US = "0653c519ef719c62"
OPTIONS = ["The Southern Ring", "Not yet, kupo..."]
STILTZKIN = (600.0, 127.0)
THROWS = {"NullReferenceException", "InvalidCastException", "IndexOutOfRangeException", "DivideByZeroException",
          "ArgumentOutOfRangeException", "OverflowException"}
WHERE = ("EventEngine", "EBin", "StoryTrace", "HarnessAgent")


def _live_eb(g) -> bytes:
    p = next((g.game_path / "FF9CustomMap-world" / "StreamingAssets").rglob(f"field/us/EVT_{NAME}.eb.bytes"))
    return p.read_bytes()


def predicted_ips(data: bytes) -> dict:
    """``{(byte, "set9"|"tail0"): ip}`` for 4600's Main_Init, from the live bytes: the prologue's ``Byte[n] := 9``
    and the TAIL's ``Byte[n] := 0``, each ip = the instruction's start minus entry 0's start."""
    from ff9mapkit.content import ambient
    from ff9mapkit.eb import EbScript
    eb = EbScript.from_bytes(data)
    f = eb.entry(0).func_by_tag(0)
    e0 = eb.entry(0).abs_start
    body = data[f.abs_start:f.abs_end]
    t = f.abs_start + body.index(ambient.TAIL)
    out = {}
    for i in eb.instrs(f):
        raw = bytes(data[i.off:i.end])
        for n in (13, 14):
            if raw == ambient._let9(n):
                out[(n, "set9")] = i.off - e0
            if raw == ambient._let0(n) and t <= i.off < t + len(ambient.TAIL):
                out[(n, "tail0")] = i.off - e0
    return out


def _byte(g, n: int):
    bits = [g.state.flag(8 * n + j) for j in range(8)]
    return None if None in bits else sum(1 << j for j, b in enumerate(bits) if b)


def run(g) -> None:
    from harness import HarnessError
    from ff9mapkit.content import ambient, movement

    g.note("F-REDEPLOY 4600: New Game into the spliced hub")
    live = _live_eb(g)
    sha = hashlib.sha256(live).hexdigest()
    g.check(ambient.classify(live) == "restored" and sha.startswith(SPLICED_US),
            "A0: 4600's live US .eb is the spliced one", f"{ambient.classify(live)}, sha {sha[:16]}")
    ips = predicted_ips(live)
    print(f"[4600] predicted ips {ips}")

    st = g.newgame()
    mark = g.log_mark()
    g.check(st.field_id == NG, "A1a: New Game lands in field 70", f"field {st.field_id}")
    g.storytrace(True)
    t0 = time.monotonic()
    g.wait_for(lambda s: s.field_id not in (NG, 0), timeout=300.0, what="field 70 to leave on its own")
    g.check(g.state.field_id == HUB, "A1b: field 70 leaves on its own script to 4600",
            f"-> {g.state.field_id} after {time.monotonic() - t0:.0f}s")
    if g.state.field_id != HUB:
        return
    g.wait_playable(timeout=90.0)
    g.watch(*range(104, 120))
    g.wait_for(lambda s: all(s.flag(b) is not None for b in range(104, 120)), timeout=5.0,
               what="bits 104-119 to be published")
    b13, b14 = _byte(g, 13), _byte(g, 14)
    g.shot("hub-arrival")

    rows = [r for r in g.story_rows() if r.k == "w" and r.fld in (NG, HUB)
            and r.byte is not None and set(r.span) & {13, 14}]
    for r in rows:
        print(f"[4600] trace: fld {r.fld} sid {r.sid} tag {r.tag} ip {r.ip} byte {r.byte} w {r.width} "
              f"{r.old} -> {r.new}")
    hub13 = [r for r in rows if r.fld == HUB and r.byte == 13 and r.sid == 0 and r.tag == 0]
    set9 = [r for r in hub13 if r.new == 9]
    clear = [r for r in hub13 if r.old == 9 and r.new == 0]
    arrived = [r for r in rows if r.fld == NG and r.byte == 13]
    print(f"[4600] field 70 wrote Byte[13]: {[(r.ip, r.old, r.new) for r in arrived]}")
    if set9:
        g.check(bool(clear) and clear[0].ip == ips[(13, "tail0")] and clear[0].line > set9[0].line,
                "A2: 4600's prologue marks Byte[13] 9 and the TAIL clears it 9 -> 0 at its own ip",
                f"set9 ip {[r.ip for r in set9]} (predicted {ips[(13, 'set9')]}), clear ip "
                f"{[r.ip for r in clear]} (predicted {ips[(13, 'tail0')]})")
    else:
        g.check(b13 is not None and b13 != 9,
                "A2: no 9 to clear on this route (the prologue never marked one) and none survives",
                f"4600 Byte[13] rows {[(r.ip, r.old, r.new) for r in hub13]}")
    g.check(b13 == 0 and b14 == 0, "A3: gEventGlobal[13] and [14] read 0 in the hub", f"[13]={b13} [14]={b14}")

    # A4 -- the hub plays: walk to Stiltzkin's talk ring, open the journey menu, pick The Southern Ring
    here = g.state
    basis = g.calibrate_axes(prior=movement.key_move_basis(255))
    objs = g.wait_for(lambda s: s.objects is not None, timeout=5.0, what="the hub's objects").objects
    talkers = [o for o in objs if o.get("talk")]
    o = min(talkers, key=lambda b: math.hypot(b["x"] - STILTZKIN[0], b["z"] - STILTZKIN[1]))
    r, tr = o["r"], o["talk_r"]
    d = max(r + 8, min(tr - 8, r + 24))
    g.walk_to(o["x"] - d, o["z"], tolerance=15, strict=False, slides=True)
    now = g.state
    moved = math.hypot(now.player_x - here.player_x, now.player_z - here.player_z)
    g.check(moved > 100, "A4a: the player walks in the hub", f"{moved:.0f}u from the spawn")
    box = None
    for _ in range(3):
        if g.state.facing_status != "cannot":
            g.turn_in_place("right" if basis["h"][0] > 0 else "left", 8)
        box = g.interact(timeout=6.0)
        if box is not None:
            break
        g.walk("right" if basis["h"][0] > 0 else "left", 2)
    if box is None:
        g.check(False, "A4b: Stiltzkin's menu opens", "no dialogue after 3 tries")
        return
    ready = g.wait_for(lambda s: g._choice_ready(s), timeout=10.0, what="the journey menu to take answers")
    names = g.options()
    g.shot("hub-menu")
    g.check(names == OPTIONS and (ready.choice or {}).get("selected") == 0,
            "A4b: the menu offers exactly the two rows, cursor on row 0",
            f"{names}, cursor {(ready.choice or {}).get('selected')}")
    g.select(g.option_index(OPTIONS[0]))
    g.press("confirm")
    try:
        g.wait_for(lambda s: s.field_id == HALL, timeout=60.0, what="the pick to land in 6601")
        g.wait_playable(timeout=60.0)
        landed = True
    except HarnessError as err:
        landed = False
        print(f"[4600] the pick did not land: {err}")
    g.shot("hall-arrival")
    g.check(landed, "A4c: The Southern Ring lands in 6601 with control", f"field {g.state.field_id}")

    bad = [e for e in g.exceptions_since(mark) if e.name in THROWS
           and (not e.trace or any(k in fr for fr in e.trace for k in WHERE))]
    g.check(not bad, "A5: no exception through the event engine, New Game to 6601",
            f"{[(e.name, e.where) for e in bad[:4]]}" if bad else "none")
    g.storytrace(False)
