"""A plain BG-borrow fork of 2356, in-game: does the walkmesh-hotfix prepend the borrow path now writes block the
floor the real field's engine hotfix blocks?

2356 (Gulug/Room) has a LOAD-TIME engine hotfix on the raw fldMapNo (FieldMap.cs:112-117: BGI_triSetActive on tris
78/79/80), which no ForkDonorPatch row can fire on a custom id. `import --native`/`--editable` have always prepended
it (`[field] walkmesh_tri_toggles`, IN-GAME PROVEN on native forks 30003/30004); the borrow path wrote no hotfix
line at all, so a borrow of 2356 lost it. It now writes the same line. A borrow runs on the donor's own .bgi, so the
toggled ids are exactly the donor's.

A/B, one launch, two slots built from ONE `import 2356`, identical except the toggle line:

    30995  walkmesh_tri_toggles = [[78, 0], [79, 0], [80, 0]]  (the import as written)
    30996  no toggle line                                       (the old import output)

Both drop the donor's [encounter] AND its carried chest, and carry a [[behavior.hud]] reading B_BGIID/B_BGIFLOOR
for the player (B_PTR(250)), plus the keeper NPC the unit gate needs (south end of the room, off the route).

WHY THE CHEST IS DROPPED: the first two runs kept it, and in both slots the walk stalled at a point exactly
267.7u from the chest (CreateObject(-426, 1664)) -- at (-570.5, 1438.7) on one route and (-658.3, 1530.9) on
another, inside walkable, linked, active triangles. That is the chest's actor collision, and it covers the whole
tri 78-80 patch (tri 80's centroid is 117u from it), so walking cannot observe the hotfix while it stands there.
The 2507 bench met the same wall (~261u from its chests). The native A/B of 2356 teleported into the patch
instead, and the real field keeps its chest, so it is not walked here. The chest is not part of the hotfix, so
dropping it from both slots keeps the toggle the only difference.

Route, from the spawn (-721, 1359, tri 0), crossing at shared edges: walk_to (-650, 1500) (tri 6) ->
(-600, 1600) (tri 5) -> (-580, 1690) (tri 80, across the tri-5 edge at z ~1629).

    py tools/deploy_field.py <A>/GLGV_FORK.field.toml --id 30995
    py tools/deploy_field.py <B>/GLGV_FORK.field.toml --id 30996
    py tools/play.py studies/fork-walkmesh-hotfix/borrow_2356_ingame.py --label borrow-2356-prepend

PRE  30995's deployed Main_Init carries EnablePathTriangle(78/79/80, 0) and 30996's does not; neither carries the chest
B    30996 (no toggle): the player reaches tri 80 (the HUD reads P 80)
A    30995 (toggle):    the player stops on tri 5, short of the tri-80 edge, and never stands on 78/79/80
X    exceptions, tallied by name
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit.config import ModLayout, find_game_path  # noqa: E402
from ff9mapkit.eb import EbScript  # noqa: E402

WITH_TOGGLE, NO_TOGGLE = 30995, 30996
HOTFIX_TRIS = (78, 79, 80)
ROUTE = ((-650, 1500), (-600, 1600))
TARGET = (-580, 1690)                   # inside tri 80
EDGE_Z = 1629                           # the tri 5 / tri 80 edge on x = -580
SENTINEL = 65535
ENABLE_PATH_TRIANGLE = 0x9A
LIVE = ModLayout(find_game_path() / "FF9CustomMap")
ROWS = ("P", "F")


def _eb(fid) -> EbScript:
    p = LIVE.root / "StreamingAssets" / "assets" / "resources" / "commonasset" / "eventengine" / "eventbinary" \
        / "field" / "us" / f"EVT_TEST{fid}.eb.bytes"
    return EbScript.from_bytes(p.read_bytes())


def _main_init_toggles(fid) -> list:
    eb = _eb(fid)
    return [list(i.args or []) for i in eb.instrs(eb.entry(0).func_by_tag(0)) if i.op == ENABLE_PATH_TRIANGLE]


def _chest_entries(fid) -> list:
    return [i for i, e in enumerate(_eb(fid).entries) if not e.empty and [f.tag for f in e.funcs] == [0, 19, 20, 21, 22]]


def _parse(text: str) -> dict:
    out = {}
    for label in ROWS:
        m = re.search(r"(?<![A-Z])" + label + r"\s+(-?\d+)", text)
        if m:
            out[label] = int(m.group(1))
    return out


def _read_hud(g, fid) -> dict | None:
    seen: dict = {}

    def ready(st):
        for text in st.texts:
            vals = _parse(text)
            if len(vals) == len(ROWS) and vals["P"] != SENTINEL:
                seen.clear()
                seen.update(vals)
                return True
        return False

    try:
        g.wait_for(ready, timeout=20, what=f"{fid}'s HUD strip to render live values")
    except Exception as err:                     # noqa: BLE001 - reported as a check, never raised
        print(f"[borrow-2356] {fid}: HUD not readable: {err}; texts {g.state.texts!r}")
        return None
    return seen


def _probe(g, fid, *, hud=True) -> dict:
    g.warp(fid)
    s0 = g.settle()
    g.wait_frames(60)                            # 2 s: past the HUD warmup
    out: dict = {"start": (s0.player_x, s0.player_z), "hud_start": _read_hud(g, fid) if hud else None, "legs": []}
    for x, z in ROUTE:
        ok = g.walk_to(x, z, strict=False)
        s = g.settle()
        out["legs"].append(((x, z), ok, (s.player_x, s.player_z), _read_hud(g, fid) if hud else None))
    out["arrived"] = g.walk_to(*TARGET, strict=False)
    s1 = g.settle()
    g.wait_frames(10)
    out.update({"end": (s1.player_x, s1.player_z), "field": s1.field_id,
                "hud_end": _read_hud(g, fid) if hud else None})
    g.shot(f"{fid}-at-patch")
    print(f"[borrow-2356] {fid}: {out}")
    return out


def run(g) -> None:
    a_t, b_t = _main_init_toggles(WITH_TOGGLE), _main_init_toggles(NO_TOGGLE)
    g.check(all([t, 0] in a_t for t in HOTFIX_TRIS) and not b_t,
            f"PRE: {WITH_TOGGLE}'s Main_Init toggles 78/79/80 off and {NO_TOGGLE}'s toggles nothing",
            f"{WITH_TOGGLE} {a_t}, {NO_TOGGLE} {b_t}")
    chests = {fid: _chest_entries(fid) for fid in (WITH_TOGGLE, NO_TOGGLE)}
    g.check(not any(chests.values()), "PRE: neither slot carries the chest (its collision would wall off the patch)",
            str(chests))
    g.note("plain BG-borrow fork of 2356: the borrow path's walkmesh-hotfix prepend decides whether tri 80 is walkable")
    g.newgame()
    mark = g.log_mark()
    res = {}
    for fid in (NO_TOGGLE, WITH_TOGGLE):
        try:
            res[fid] = _probe(g, fid)
        except Exception as err:                 # noqa: BLE001 - one slot failing must not hide the other
            print(f"[borrow-2356] {fid}: probe failed: {err}")
            res[fid] = None

    b, a = res[NO_TOGGLE], res[WITH_TOGGLE]
    bh, ah = (b or {}).get("hud_end"), (a or {}).get("hud_end")
    g.check(b is not None and b["arrived"] and bh is not None and bh["P"] == 80,
            f"B {NO_TOGGLE} (no toggle): the player walks onto tri 80", str(b))
    g.check(a is not None and not a["arrived"] and ah is not None and ah["P"] not in HOTFIX_TRIS
            and a["end"][1] is not None and a["end"][1] < EDGE_Z,
            f"A {WITH_TOGGLE} (toggle): the player stops short of the tri-80 edge (z < {EDGE_Z}), off 78/79/80",
            str(a))

    tally: dict = {}
    for e in g.exceptions_since(mark):
        tally[str(e)] = tally.get(str(e), 0) + 1
    print(f"[borrow-2356] exceptions: {tally or 'none'}")
    g.check(True, "X: exceptions tallied", str(tally or "none"))
