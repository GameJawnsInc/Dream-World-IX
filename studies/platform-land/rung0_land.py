"""RUNG 0 of the platform-land check -- a [[platform]] LAND ride in-game, sampled frame by frame.

    py tools/deploy_field.py studies/platform-land/bench/land.field.toml --id 30960 --name PLTLAND --text-block 30960
    py tools/play.py studies/platform-land/rung0_land.py --label platform-land

The land ride captures the boarding x / z / selfY into Map Int16 scratch, then each frame steps selfY toward
the landing and places the player at   x = start_x + (land_x - start_x) * (cur - start_y) / (land_y - start_y)
(z likewise). A Map var index is a BYTE OFFSET into EventContext.mapvar, so the ride's old slots 3/4/5/6 overlapped
and start_x read back as a mix of selfY's and z's bytes. The byte-offset model in tests/test_mapvar_layout.py
predicts, for THIS bench's numbers: old layout -> first ride frame at x ~ 7203 (off the whole mesh); fixed layout
-> x ~ -519, on the straight line from the boarding point.

Bench studies/platform-land/bench/land.field.toml (30960): a ground floor (height 0, x -1220..-200) and a deck
200 up (x 200..1220), no triangles or links between them. Press Confirm in the boarding zone and the ride carries
the player to land = (700, -1200) at height 200, at speed 5 = 40 ride frames. The ride's published y is pos[1],
which is -selfY, so it climbs 0 -> 200.

PRE  P0 30960 is served by FF9CustomMap alone
     P1 the DEPLOYED ride function's Map Int16 offsets -- REPORTED, so the verdict names the build under test
A0   boot on the ground: control, height 0
A1   board: walk into the zone, press Confirm -> control drops and the height starts to climb
A2   THE CHECK THAT FAILS ON THE OLD LAYOUT: every ride sample lies on the straight segment from the MEASURED
     boarding point to the landing, at the fraction its own height says (within 20 units), and x never leaves
     the segment's span
A3   the landing: at land (x, z within 5), height 200, control back
A4   standing on the deck: a walk east keeps height 200 (a real floor under him, not a floor-snap)
A5   no NullReference / InvalidCast / IndexOutOfRange in either log
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit.content import platform as P  # noqa: E402
from ff9mapkit.content.ladder import find_player_entry  # noqa: E402
from ff9mapkit.eb import EbScript  # noqa: E402
from ff9mapkit.eb import disasm as D  # noqa: E402

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
LIVE = GAME / "FF9CustomMap" / "StreamingAssets" / "Assets" / "Resources"
FIELD, NAME = 30960, "PLTLAND"
ZONE_C = (-550, -450)                    # the boarding zone's centre (zone x -700..-400, z -600..-300)
LAND = (700, -1200, 200)                 # x, z, height -- from the bench toml
DECK_WALK = (1000, -900)
THROWS = {"NullReferenceException", "InvalidCastException", "IndexOutOfRangeException"}


def _ride_offsets() -> list:
    """The Map Int16 byte offsets the DEPLOYED ride function reads/writes (player entry, the first platform tag)."""
    data = (LIVE / "CommonAsset" / "EventEngine" / "EventBinary" / "Field" / "us" / f"EVT_{NAME}.eb.bytes").read_bytes()
    s = EbScript.from_bytes(data)
    f = s.entry(find_player_entry(s)).func_by_tag(P.FIRST_PLATFORM_TAG)
    offs = set()
    for ins in D.iter_code(data, f.abs_start, f.abs_end):
        for toks in D.instr_expr_tokens(data, ins):
            offs |= {arg for op, arg in toks or () if op == 0xD9}
    return sorted(offs)


def _sample_ride(g, seconds: float = 12.0) -> list:
    """Every distinct published frame from now until the player is back in control at the landing height.

    Reads the channel directly: at one publication per frame a fast poller WILL catch state.json mid-write,
    and `g.state` turns that one torn read into a fatal "no state published" (the first run died that way,
    mid-ride). A miss here just means the next poll; the deadline bounds a genuinely dead channel."""
    rows, last, deadline = [], None, time.time() + seconds
    while time.time() < deadline:
        st = g.channel.state()
        if st is not None and st.frame != last and st.player_x is not None:
            last = st.frame
            rows.append((st.frame, st.player_x, st.player_y, st.player_z, st.control))
            if st.control and abs(st.player_y - LAND[2]) < 1 and len(rows) > 5:
                break
        time.sleep(0.004)
    return rows


def run(g) -> None:
    folders = [p.parent.name for p in GAME.glob("*/DictionaryPatch.txt")
               if re.search(rf"FieldScene {FIELD}\b", p.read_text(encoding="utf-8", errors="replace"))]
    g.check(folders == ["FF9CustomMap"], f"P0: {FIELD} is served by FF9CustomMap alone", str(folders))
    offs = _ride_offsets()
    overlap = [(a, b) for a, b in zip(offs, offs[1:]) if b - a < 2]
    g.note(f"deployed ride Map Int16 offsets {offs} overlapping={overlap}")
    g.check(len(offs) == 4, "P1: the deployed ride uses four Map Int16 slots (a land ride was built)",
            f"offsets {offs}, partial overlaps {overlap}")

    mark = g.log_mark()
    g.newgame()
    g.warp(FIELD)
    st = g.wait_control()
    g.check(st.field_id == FIELD and abs(st.player_y) < 1, "A0: control on the ground floor (height 0)",
            f"field {st.field_id} y {st.player_y}")

    g.walk_to(*ZONE_C, tolerance=40)
    b = g.settle()
    bx, by, bz = b.player_x, b.player_y, b.player_z
    g.check(-700 < bx < -400 and -600 < bz < -300 and abs(by) < 1, "A1: standing in the boarding zone",
            f"({bx:.0f}, {by:.0f}, {bz:.0f})")
    g.shot("before-ride")

    g.state_every(1)
    g.press("confirm")
    rows = _sample_ride(g)
    g.state_every(2)
    ride = [r for r in rows if by + 1 < r[2] < LAND[2] - 1]          # strictly between the two heights
    g.note("ride samples (frame, x, y, z, control): " + "; ".join(
        f"{f} {x:.0f} {y:.0f} {z:.0f} {int(c)}" for f, x, y, z, c in rows[:80]))
    g.check(len(ride) >= 8 and not any(r[4] for r in ride),
            "A1: Confirm boarded -- control dropped and the height climbed through the ride",
            f"{len(ride)} in-ride samples of {len(rows)}")

    lx, lz, ly = LAND
    worst, off_span = 0.0, []
    for f, x, y, z, _c in ride:
        t = (y - by) / (ly - by)
        ex, ez = bx + (lx - bx) * t, bz + (lz - bz) * t
        worst = max(worst, abs(x - ex), abs(z - ez))
        if not (min(bx, lx) - 20 <= x <= max(bx, lx) + 20):
            off_span.append((f, round(x), round(z)))
    first = ride[0] if ride else None
    g.check(bool(ride) and worst <= 20 and not off_span,
            "A2: every ride frame is on the straight line from the boarding point to the landing",
            f"worst off-line {worst:.0f}u; first ride frame "
            f"{None if first is None else (round(first[1]), round(first[2]), round(first[3]))}; "
            f"off the x span: {off_span[:6]}")

    end = g.wait_control()
    g.check(abs(end.player_x - lx) <= 5 and abs(end.player_z - lz) <= 5 and abs(end.player_y - ly) <= 2,
            "A3: landed at the landing point, height 200, control back",
            f"({end.player_x:.0f}, {end.player_y:.0f}, {end.player_z:.0f})")
    g.shot("landed")

    g.walk_to(*DECK_WALK, tolerance=40, strict=False)
    d = g.settle()
    g.check(abs(d.player_x - lx) + abs(d.player_z - lz) > 150 and abs(d.player_y - ly) <= 2,
            "A4: walked on the deck and stayed at height 200 -- a real floor under the landing",
            f"({d.player_x:.0f}, {d.player_y:.0f}, {d.player_z:.0f})")
    g.shot("on-deck")

    bad = [e for e in g.exceptions_since(mark) if e.name in THROWS]
    g.check(not bad, "A5: no NullReference / InvalidCast / IndexOutOfRange in either log",
            "; ".join(f"{e.name} at {e.where}" for e in bad[:3]))
