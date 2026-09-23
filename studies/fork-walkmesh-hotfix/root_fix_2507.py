"""The root-cause fix, in-game: a kit-built 2507 fork keeps its player with NO re-attach guard.

FINDINGS.md traced the detach to the kit, not the engine: the template player's Init had its eight stale
`RunSoundCode(4616, 912)` ops zero-filled, and 0x00 is a one-tick yield, so `DefinePlayerCharacter` ran ~48 ticks
after `SetModel` -- inside the window where 2507's delayed pass (`FieldMap.DelayedActiveTri`, 0.5 s) detaches every
controller that is not yet the player. The fix jumps over those ops instead, so the player binds on its first Init
tick like the real one, and moves the entry-settle hold ahead of Main_Init's `set MAP159 = 1` so the template's own
handshake -- not the now-early player latch -- hands control back when the hold ends. The guard is gone.

All four fields, entered at entrance 128 on the upper walkway, then 12 run frames toward its east edge:

    30991  --editable fork, no donor row (the control: the pass never runs)
    30990  --editable fork, row -> 2507, NO guard (+ the HUD: P / CA / CB = player / chest tris)
    30992  --native fork,   row -> 2507, NO guard
    2507   the real field

CHECKS
  walk    every field stops at the platform edge, on the walkway (a detached player covers ~360u)
  hud     30990: the chests still read -1 (the hotfix fired) and the player reads a real triangle
  bind    each kit field publishes its player (GetControlChar) well BEFORE control returns -- bound at the
          first Init tick, control withheld until the settle hold ends. Before the fix both landed in the same
          sample, ~1.7 s after the load.

    py tools/deploy_field.py <bench>/IPSN_EDIT.field.toml --id 30990      (and 30991, 30992 -- see FINDINGS.md)
    py tools/play.py studies/fork-walkmesh-hotfix/root_fix_2507.py --label root-fix-2507
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit.config import ModLayout, find_game_path  # noqa: E402
from ff9mapkit.scene import bgi  # noqa: E402
from ff9mapkit.scene.bgi import _pt_in_tri_xz  # noqa: E402

NO_ROW, WITH_ROW, NATIVE, REAL = 30991, 30990, 30992, 2507
KIT = (NO_ROW, WITH_ROW, NATIVE)
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


def _arrival(path, fid) -> dict:
    """From a flushed ring: seconds from the switch to `fid` until the player is published, and until control."""
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    rows = [(r["t"] - r.get("age", 0), r["state"]) for r in rows]
    i0 = next((i for i, (_, s) in enumerate(rows) if s["field"]["id"] == fid), None)
    if i0 is None:
        return {}
    t0 = rows[i0][0]
    bound = next(((t, s["frame"]) for t, s in rows[i0:] if s["player"]["x"] is not None
                  and abs(s["player"]["x"] - START[0]) < 2 and abs(s["player"]["z"] - START[1]) < 2), None)
    ctl = next(((t, s["frame"]) for t, s in rows[i0:] if s["player"]["control"]), None)
    if bound is None or ctl is None:
        return {"switch_frame": rows[i0][1]["frame"]}
    return {"switch_frame": rows[i0][1]["frame"], "bound_frame": bound[1], "control_frame": ctl[1],
            "bound_s": round(bound[0] - t0, 2), "control_s": round(ctl[0] - t0, 2),
            "lead_frames": ctl[1] - bound[1]}


def _hud(g) -> dict:
    hud = {}
    for text in g.state.texts:
        for label in ("P", "CA", "CB"):
            m = re.search(r"(?<![A-Z])" + label + r"\s+(-?\d+)", text)
            if m:
                hud[label] = int(m.group(1))
    return hud


def _probe(g, wm, fid) -> dict:
    g.warp(fid, entrance=ENTRANCE)                   # returns once the field is playable (control is back)
    ring = g.flush_states(f"arrive-{fid}")
    g.wait_frames(60)
    s0 = g.settle()
    g.walk("right", FRAMES)
    s1 = g.settle()
    g.shot(f"{fid}-after-right")
    out = {"start": (s0.player_x, s0.player_z), "end": (s1.player_x, s1.player_z),
           "moved": round(((s1.player_x - s0.player_x) ** 2 + (s1.player_z - s0.player_z) ** 2) ** 0.5),
           "on_walkway": _on_upper(wm, s1.player_x, s1.player_z), "field": s1.field_id,
           "arrival": _arrival(ring, fid) if ring else {}}
    if fid == WITH_ROW:
        out["hud"] = _hud(g)
    print(f"[rootfix] {fid}: {out}")
    return out


def run(g) -> None:
    wm = _mesh()
    g.check(_on_upper(wm, *START) and not _on_upper(wm, START[0] + 300, START[1]),
            "PRE: the arrival is on the upper walkway and 300u east of it is off every walkway tri")
    g.newgame()
    mark = g.log_mark()
    res = {}
    for fid in (NO_ROW, WITH_ROW, NATIVE, REAL):
        try:
            res[fid] = _probe(g, wm, fid)
        except Exception as err:                     # noqa: BLE001 - one slot failing must not hide the others
            print(f"[rootfix] {fid}: probe failed: {err}")
            res[fid] = None
    for fid in (NO_ROW, WITH_ROW, NATIVE, REAL):
        r = res[fid]
        g.check(r is not None and r["on_walkway"] and r["moved"] < 300,
                f"walk {fid}: stops at the platform edge, on the walkway (a detached player moves ~360u)", str(r))
    h = (res[WITH_ROW] or {}).get("hud", {})
    g.check(h.get("CA") in (-1, 65535) and h.get("CB") in (-1, 65535) and 0 <= h.get("P", -1) < 65535,
            f"hud {WITH_ROW}: the chests are detached (the hotfix fired) and the player is on a triangle, with no "
            f"guard", str(h))
    for fid in KIT:
        a = (res[fid] or {}).get("arrival", {})
        g.check(a.get("lead_frames", 0) >= 30,
                f"bind {fid}: the player is published well before control returns (bound on its first Init tick, "
                f"control held to the settle's end)", str(a))
    tally: dict = {}
    for e in g.exceptions_since(mark):
        tally[str(e)] = tally.get(str(e), 0) + 1
    print(f"[rootfix] exceptions: {tally or 'none'}")
