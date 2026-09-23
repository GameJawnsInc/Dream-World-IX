"""An --editable fork's donor row, in-game: does field 2507's DELAYED walkmesh hotfix fire on it?

2507 (Ipsen's Castle stairwell) has an engine hotfix that runs 0.5 s AFTER load (FieldMap.DelayedActiveTri). In
one frame it detaches every non-player actor from the walkmesh (BGI_charSetActive(fac, 0): activeTri -> -1) and
deactivates the landing tris 174/175/177/178 (floor 4, y -2540), which the two chest props settled onto. s29 routes
its gate through EffectiveFieldId, so on a fork it fires only when ForkDonorPatch maps the fork's id to 2507, and
only a toml that records its donor gets that row. `import --editable` now writes `[field] source_field = 2507`; it
used to write nothing, so the hotfix was lost, and no Main_Init prepend can time it.

A/B, one launch, two slots built from ONE `import 2507 --editable`, identical except the key:

    30990  source_field = 2507  -> ForkDonorPatch `30990 2507` -> the engine's gate fires
    30991  no source_field      -> no row                      -> the gate stays false (the old --editable output)

Both copies carry the same test instrument, so the donor row is the only difference: the donor's [encounter] is
dropped, and a [[behavior.hud]] reads B_BGIID/B_BGIFLOOR -- the live walkmesh triangle/floor -- for the player
(B_PTR(250)) and the two chests (entries 7/8; the unit-gate NPC `keeper` stands at entry 2, on the ground floor).

WHY NOT WALK IT: the first run of this bench walked the upper walkway toward the landing and stopped ~261u from
the nearer chest in BOTH slots. The chests' actor collision covers the whole landing, and BGI_charSetActive does
not remove actor collision, so the player can never reach the tris the hotfix removes. The chests' own triangle
is the observable the coroutine changes.

    py tools/deploy_field.py <A>/IPSN_EDIT.field.toml --id 30990
    py tools/deploy_field.py <B>/IPSN_EDIT.field.toml --id 30991
    py tools/play.py studies/fork-walkmesh-hotfix/editable_2507_ingame.py --label editable-2507-donor-row

PRE  ForkDonorPatch maps 30990 -> 2507 and not 30991; both deployed .eb carry the chests at entries 7/8; both
     deployed walkmeshes keep the donor's tri ids (174/175/177/178 on floor 4 at y -2540)
B    30991 (no row): the chests stay attached on the landing (a floor-4 tri, floor 4)
A    30990 (row):    the chests read -1/-1 (detached by DelayedActiveTri); the player stays attached
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
from ff9mapkit.scene import bgi  # noqa: E402

WITH_ROW, NO_ROW = 30990, 30991
DONOR = 2507
HOTFIX_TRIS = (174, 175, 177, 178)
LANDING = (174, 175, 176, 177, 178)    # floor 4
CHESTS = (7, 8)                         # entry == uid; tags [0, 23, 24, 25, 26] (the carried props)
ENTRANCE = 128                          # the donor's arrival at (2019, -1077): floor 1 alone in XZ
UPPER_Y = 2540                          # the walkmesh's -2540, sign-flipped in the published state
SENTINEL = 65535                        # a 5-digit HUD slot's open-pass placeholder (a u16)
DETACHED = (-1, 65535)                  # -1 as the Int32 expression renders it, or truncated to u16
LIVE = ModLayout(find_game_path() / "FF9CustomMap")
ROWS = ("P", "CA", "CB", "FA")


def _mesh(fid) -> bgi.BgiWalkmesh:
    d = LIVE.fieldmap_dir(f"FBG_N43_TEST{fid}")
    return bgi.BgiWalkmesh.from_bytes((d / f"FBG_N43_TEST{fid}.bgi.bytes").read_bytes())


def _eb(fid) -> EbScript:
    p = LIVE.root / "StreamingAssets" / "assets" / "resources" / "commonasset" / "eventengine" / "eventbinary" \
        / "field" / "us" / f"EVT_TEST{fid}.eb.bytes"
    return EbScript.from_bytes(p.read_bytes())


def _preflight(g) -> None:
    rows = {}
    fdp = LIVE.root / "ForkDonorPatch.txt"
    for ln in (fdp.read_text(encoding="utf-8-sig").splitlines() if fdp.exists() else []):
        parts = ln.split()
        if len(parts) == 2 and parts[0].isdigit():
            rows[int(parts[0])] = int(parts[1])
    g.check(rows.get(WITH_ROW) == DONOR and NO_ROW not in rows,
            f"PRE: ForkDonorPatch maps {WITH_ROW} -> {DONOR} and has no row for {NO_ROW}", f"rows {rows}")
    for fid in (WITH_ROW, NO_ROW):
        eb = _eb(fid)
        props = tuple(i for i, e in enumerate(eb.entries)
                      if not e.empty and [f.tag for f in e.funcs] == [0, 23, 24, 25, 26])
        g.check(props == CHESTS, f"PRE: {fid}'s deployed .eb carries the chests at entries {CHESTS}", str(props))
        wm = _mesh(fid)
        wv = wm.world_verts()
        tf = wm._tri_floor()
        ok = all(tf.get(t) == 4 and all(round(wv[i][1]) == -UPPER_Y for i in wm.tris[t].vtx) for t in HOTFIX_TRIS)
        g.check(ok, f"PRE: {fid}'s deployed walkmesh keeps the donor's hotfix tris on floor 4 at y -{UPPER_Y}",
                str({t: tf.get(t) for t in HOTFIX_TRIS}))


def _parse(text: str) -> dict:
    out = {}
    for label in ROWS:
        m = re.search(r"(?<![A-Z])" + label + r"\s+(-?\d+)", text)
        if m:
            out[label] = int(m.group(1))
    return out


def _read_hud(g, fid) -> dict | None:
    """The strip's four values once its live pass has landed: the player row (a real tri in both slots) stops
    showing the open-pass sentinel. Every slot is written in the same pass, so the other three are live too."""
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
        print(f"[editable-2507] {fid}: HUD not readable: {err}; texts {g.state.texts!r}")
        return None
    return seen


def _probe(g, fid) -> dict | None:
    g.warp(fid, entrance=ENTRANCE)
    s = g.settle()
    g.check(s.player_y is not None and abs(s.player_y - UPPER_Y) < 120,
            f"{fid}: arrives at entrance {ENTRANCE} on the upper walkway", f"at ({s.player_x}, {s.player_y}, {s.player_z})")
    g.wait_frames(90)                            # 3 s: well past the 0.5 s coroutine and the HUD warmup
    vals = _read_hud(g, fid)
    g.shot(f"{fid}-hud")
    print(f"[editable-2507] {fid}: HUD {vals}")
    return vals


def run(g) -> None:
    _preflight(g)
    g.note("editable fork of 2507: the donor row decides whether DelayedActiveTri fires")
    g.newgame()
    mark = g.log_mark()

    b = _probe(g, NO_ROW)
    g.check(b is not None and b["CA"] in LANDING and b["CB"] in LANDING and b["FA"] == 4,
            f"B {NO_ROW} (no row): both chests stay attached to the landing (floor 4) -- the hotfix did not run",
            str(b))

    a = _probe(g, WITH_ROW)
    g.check(a is not None and a["CA"] in DETACHED and a["CB"] in DETACHED and a["FA"] in DETACHED
            and a["P"] not in DETACHED,
            f"A {WITH_ROW} (row -> {DONOR}): both chests detached (-1), the player still attached -- "
            f"DelayedActiveTri fired, and with it the 174/175/177/178 deactivation", str(a))

    g.press("menu")                              # the s33 location label: the donor's name with the row
    g.wait_frames(45)
    g.shot(f"{WITH_ROW}-menu")
    g.close_ui()

    tally: dict = {}
    for e in g.exceptions_since(mark):
        tally[str(e)] = tally.get(str(e), 0) + 1
    print(f"[editable-2507] exceptions: {tally or 'none'}")
    g.check(True, "X: exceptions tallied", str(tally or "none"))
