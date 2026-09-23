"""Does 2507's DelayedActiveTri detach the PLAYER from the walkmesh -- on the editable fork, and on the real field?

editable_2507_ingame.py found the donor row working (the chests read -1 on 30990 and a landing tri on 30991), and
also found the PLAYER reading -1 on 30990. The coroutine skips `isPlayer` controllers, so a -1 player means it
treated the player as an NPC and cleared its walkmesh flag. A detached controller's SetPosition skips the
triangle check (FieldMapActorController.SetPosition: `(charFlags & 1) == 0` -> curPos = pos), so the player would
walk off the mesh. This bench tests that directly, against the real field as the reference.

From the donor's entrance-128 arrival (2019, -1077) -- a small upper platform whose east edge is ~150u away, with
no floor of any kind beyond it -- hold `right` for 12 run frames (~360u east-north-east, short of the gateway-1
zone, which starts at x 2623). A walkmesh-bound player stops at the edge; a detached one keeps going.

    30991  editable fork, no row (the control)
    30990  editable fork, row -> 2507
    2507   the real field (warped at scenario 0)

    py tools/play.py studies/fork-walkmesh-hotfix/editable_2507_detach.py --label editable-2507-detach
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit.config import ModLayout, find_game_path  # noqa: E402
from ff9mapkit.scene import bgi  # noqa: E402
from ff9mapkit.scene.bgi import _pt_in_tri_xz  # noqa: E402

WITH_ROW, NO_ROW, REAL = 30990, 30991, 2507
NATIVE = 30992                           # `import 2507 --native` (records source_field since it was introduced)
ENTRANCE = 128
START = (2019, -1077)
FRAMES = 12
LIVE = ModLayout(find_game_path() / "FF9CustomMap")


def _mesh() -> bgi.BgiWalkmesh:
    d = LIVE.fieldmap_dir(f"FBG_N43_TEST{NO_ROW}")
    return bgi.BgiWalkmesh.from_bytes((d / f"FBG_N43_TEST{NO_ROW}.bgi.bytes").read_bytes())   # == the donor's


def _on_upper(wm, x, z) -> bool:
    wv = wm.world_verts()
    tf = wm._tri_floor()
    for t, tri in enumerate(wm.tris):
        vs = [wv[i] for i in tri.vtx]
        if tf[t] != 2 and abs(sum(v[1] for v in vs) / 3 + 2540) < 300 and _pt_in_tri_xz(x, z, *vs):
            return True
    return False


def _probe(g, wm, fid) -> dict:
    g.warp(fid, entrance=ENTRANCE)
    g.wait_frames(60)                            # 2 s: well past the 0.5 s coroutine
    s0 = g.settle()
    g.walk("right", FRAMES)
    s1 = g.settle()
    g.shot(f"{fid}-after-right")
    out = {"start": (s0.player_x, s0.player_z), "end": (s1.player_x, s1.player_z), "y": s1.player_y,
           "moved": round(((s1.player_x - s0.player_x) ** 2 + (s1.player_z - s0.player_z) ** 2) ** 0.5),
           "on_walkway": _on_upper(wm, s1.player_x, s1.player_z), "field": s1.field_id}
    print(f"[detach] {fid}: {out}")
    return out


def run(g) -> None:
    import os
    if os.environ.get("DETACH_ORDER") == "row-first":
        return _row_first(g)
    if os.environ.get("DETACH_ORDER") == "fixed":
        return _fixed(g)
    wm = _mesh()
    g.check(_on_upper(wm, *START) and not _on_upper(wm, START[0] + 300, START[1]),
            "PRE: the arrival is on the upper walkway and 300u east of it is off every walkway tri")
    g.newgame()
    mark = g.log_mark()
    res = {}
    for fid in (NO_ROW, WITH_ROW, REAL):
        try:
            res[fid] = _probe(g, wm, fid)
        except Exception as err:                 # noqa: BLE001 - one slot failing must not hide the others
            print(f"[detach] {fid}: probe failed: {err}")
            res[fid] = None
    b, a, r = res[NO_ROW], res[WITH_ROW], res[REAL]
    g.check(b is not None and b["start"] == START and b["on_walkway"],
            f"{NO_ROW} (no row): the player stops at the platform edge", str(b))
    g.check(r is not None, f"{REAL} (real): probed", str(r))
    g.check(a is not None and r is not None and a["on_walkway"] == r["on_walkway"],
            f"{WITH_ROW} (row) matches the real field: both {'on' if r and r['on_walkway'] else 'off'} the walkway",
            f"fork {a}, real {r}")
    tally: dict = {}
    for e in g.exceptions_since(mark):
        tally[str(e)] = tally.get(str(e), 0) + 1
    print(f"[detach] exceptions: {tally or 'none'}")


def _row_first(g) -> None:
    """DETACH_ORDER=row-first: is the detach tied to what the player walked in FROM? The first run entered 30990
    from 30991, whose player is also uid 1 (every kit field's is). Here 30990 is entered first (from New Game), then
    after the real field (player uid 13), then after 30991 again."""
    wm = _mesh()
    g.newgame()
    seq = [(WITH_ROW, "from New Game"), (REAL, "from 30990"), (WITH_ROW, "from real 2507 (uid 13)"),
           (NO_ROW, "from 30990"), (WITH_ROW, "from 30991 (uid 1)"),
           (NATIVE, "NATIVE fork, row (from 30990)"), (REAL, "from the native fork")]
    for fid, how in seq:
        try:
            r = _probe(g, wm, fid)
        except Exception as err:                 # noqa: BLE001
            print(f"[detach] {fid} {how}: probe failed: {err}")
            r = None
        g.check(r is not None, f"{fid} {how}: {'OFF' if r and not r['on_walkway'] else 'on'} the walkway after "
                f"{FRAMES} frames right", str(r))


def _fixed(g) -> None:
    """DETACH_ORDER=fixed: the build now guards a kit-built player wherever 2507's pass will run
    (content.walkmesh_hotfix.reattach_player: its Loop re-attaches it whenever it has control and no triangle).
    30990 and 30992 are rebuilt with it; 30991 (no row) is unchanged. Every slot must now stop at the platform edge,
    and 30990's HUD must still show the chests detached -- the hotfix fires, only the player is restored.
    (The first fix, a one-shot `Wait(30); SetPathing(1)`, passed one launch and failed the next: the pass lands
    at a load-dependent moment, so a fixed delay races it.)"""
    import re as _re
    wm = _mesh()
    g.newgame()
    res = {}
    for fid in (NO_ROW, WITH_ROW, NATIVE, REAL):
        try:
            res[fid] = _probe(g, wm, fid)
        except Exception as err:                 # noqa: BLE001
            print(f"[detach] {fid}: probe failed: {err}")
            res[fid] = None
        if fid == WITH_ROW and res[fid] is not None:
            hud = {}
            for text in g.state.texts:
                for label in ("P", "CA", "CB", "FA"):
                    m = _re.search(r"(?<![A-Z])" + label + r"\s+(-?\d+)", text)
                    if m:
                        hud[label] = int(m.group(1))
            print(f"[detach] {fid} HUD after the walk: {hud}")
            g.check(hud.get("CA") in (-1, 65535) and hud.get("CB") in (-1, 65535) and hud.get("P", -1) >= 0
                    and hud.get("P") != 65535,
                    f"{fid}: the chests are still detached (the hotfix fired) and the player is back on a tri",
                    str(hud))
    # Attached vs detached, not an exact stop point: a bound player slides along the platform edge and comes to
    # rest at (2157, -870) or (2142, -907) from run to run -- the unchanged no-row 30991 has landed on both --
    # while a detached one covers the full 360u into the void.
    for fid in (NO_ROW, WITH_ROW, NATIVE, REAL):
        r = res[fid]
        g.check(r is not None and r["on_walkway"] and r["moved"] < 300,
                f"{fid}: stops at the platform edge, on the walkway (a detached player moves 360u)", str(r))
