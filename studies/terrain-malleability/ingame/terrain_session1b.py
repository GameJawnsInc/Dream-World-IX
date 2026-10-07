"""In-game session 1b -- the parts of session 1 a battle cut short (NO DEPLOY).

Session 1 (.harness-runs/20261007-125119-terrain-session1) proved A2-A4 (R2 toggles on area 14; walking onto the
area-12 Cleyra tiles forces the view down; R2 refused there) and -- unplanned -- rolled scene 174 (zone 5, topo 41,
fog 1) on those tiles while world_face probed, ending in a GameOver before the rest ran. Its window-title read used
the wrong prefix (Memoria titles "FINAL FANTASY IX - World Map: <id>, <loc>", PlayerWindow.cs:51).

This run avoids MOVING on encounter tiles: encounters roll only while the actor moves (ProcessEncount needs hasMoved),
so the area spots are reached by TELEPORT (w_movementChrInitSlice re-grounds; the title proves which area the engine
registered) and the camera is faced once on the proven landing lawn (yaw survives a teleport).

REGISTERED PREDICTIONS:
  A1  title at P14 ends "Lindblum Plateau"; at P12 ends "Vube Desert" (FF9TextTool.WorldLocationText(area)).
  A3' high view on P14, then TELEPORT onto P12: the view is forced back down (same lock as walking in).
  A4  R2 refused on P12.
  A5  teleport back to P14: R2 works again.
  M   the main menu's location label names the same place as the title (screenshots, judged by eye).
  V3  forest topo 36/37/38: published y = ground - 1.171875; lawn: = ground (scored by session1_post.py).
  V10 basin (3,7): y < -4 on Terrain.

    py tools/play.py studies/terrain-malleability/ingame/terrain_session1b.py --label terrain-session1b
    py studies/terrain-malleability/ingame/session1_post.py <run dir>
"""
import ctypes
import json
from ctypes import wintypes
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
AREA = json.loads((HERE / "out" / "area_prep.json").read_text(encoding="utf-8"))
VERT = json.loads((HERE / "out" / "vertical_prep.json").read_text(encoding="utf-8"))

LANDING_FIELD = 6603
EXIT_AT = (400.0, -1400.0)
DOOR = [[285, -352], [875, -460], [424, -2944], [-166, -2836]]
LANDING = (68.0, -444.0)
P12 = tuple(AREA["P12"]["world"])
P14 = tuple(AREA["P14"]["world"])
B_14_12 = AREA["bearing_14_to_12"]
NAME = {12: AREA["location_text"]["12"], 14: AREA["location_text"]["14"]}
SETTLE = 90

_RECORD: dict = {"area": {}, "vertical": {}, "notes": [], "recoveries": 0}


def window_titles():
    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(h, _l):
        n = user32.GetWindowTextLengthW(h)
        if n:
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(h, buf, n + 1)
            if buf.value.startswith("FINAL FANTASY IX"):
                found.append(buf.value)
        return True

    user32.EnumWindows(cb, 0)
    return found


def _img(path):
    im = Image.open(path).convert("L")
    w, h = im.size
    im = im.crop((int(w * 0.15), int(h * 0.15), int(w * 0.85), int(h * 0.85))).resize((224, 126))
    return np.asarray(im, dtype=np.float32)


def fdiff(a, b) -> float:
    return round(float(np.mean(np.abs(_img(a) - _img(b)))), 3)


def snap(g, name, frames=SETTLE):
    g.wait_frames(frames)
    return g.shot(name)


def here(g) -> dict:
    st = g.state
    return {"x": st.world_x, "z": st.world_z, "y": st.world_y, "world": st.world_id, "ui": st.ui_state,
            "scenario": st.scenario}


def reach_world(g):
    """Title/any state -> new game -> 6603 -> its west door -> the overworld; face B_14_12 on the landing lawn."""
    g.newgame()
    g.warp(LANDING_FIELD)
    g.wait_frames(45)
    g.calibrate_axes(hazards=[DOOR])
    g.walk_to(*EXIT_AT, strict=False, halt_on_transition=True)
    g.wait_world(timeout=90)
    g.world_settle()
    face = g.world_face(B_14_12, home=LANDING, tolerance=6.0)
    g.teleport(*LANDING)
    g.world_settle()
    return face


def recover(g, where: str) -> None:
    """Off the world map: flee/fight a battle; on a GameOver, back to the title and walk out again."""
    st = g.state
    _RECORD["notes"].append(f"left the world at {where}: ui {st.ui_state}")
    print(f"[t1b] left the world at {where}: ui {st.ui_state}")
    try:
        if st.in_battle or st.ui_state == "BattleHUD":
            if not g.flee(timeout=60):
                g.fight()
            g.leave_battle(timeout=120)
        if g.state.on_world:
            g.world_settle()
            return
    except Exception as err:
        print(f"[t1b] battle handling at {where} failed: {err}")
    ok, why = g.restore_baseline()
    print(f"[t1b] restore_baseline: {ok} {why}")
    _RECORD["recoveries"] += 1
    reach_world(g)


def menu_shot(g, name: str) -> None:
    g.open_menu()
    snap(g, name, 30)
    for _ in range(6):
        if g.state.ui_state == "WorldHUD":
            return
        g.press("cancel", 6)
        g.wait_frames(25)
    g.wait_for(lambda s: s.ui_state == "WorldHUD", timeout=15, what="the world menu to close")


def area_part(g):
    rec = _RECORD["area"]
    g.teleport(*P14)
    g.world_settle()
    rec["P14_start"] = here(g)
    a = snap(g, "a14-default")
    rec["title_P14"] = window_titles()
    a2 = snap(g, "a14-default-noise", 60)
    noise = fdiff(a, a2)
    thr = max(3 * noise, noise + 2.0)
    g.press("r2")
    b = snap(g, "a14-after-r2")
    toggled = fdiff(a, b)
    rec["P14"] = {"noise": noise, "r2_change": toggled}
    g.check(any(t.endswith(NAME[14]) for t in rec["title_P14"]), f"A1: P14 window title names '{NAME[14]}'",
            f"titles {rec['title_P14']}")
    control_ok = toggled > thr
    g.check(control_ok, "A2 (instrument): R2 changes the camera on area 14", f"change {toggled} vs noise {noise}")
    menu_shot(g, "a14-menu")

    g.teleport(*P12)                                   # high view (if the control worked) -> onto the area-12 tiles
    g.world_settle()
    rec["P12_reached"] = here(g)
    c = snap(g, "a12-teleported")
    rec["title_P12"] = window_titles()
    g.check(any(t.endswith(NAME[12]) for t in rec["title_P12"]), f"A1: P12 window title names '{NAME[12]}'",
            f"titles {rec['title_P12']}")
    rec["P12"] = {"vs_default_P14": fdiff(c, a), "vs_high_P14": fdiff(c, b)}
    g.press("r2")
    d = snap(g, "a12-after-r2")
    rec["P12"]["r2_change"] = fdiff(c, d)
    if control_ok:
        g.check(rec["P12"]["vs_default_P14"] < rec["P12"]["vs_high_P14"],
                "A3': teleported onto area 12 from the high view, the view is forced back to the default",
                f"vs P14 default {rec['P12']['vs_default_P14']}, vs P14 high {rec['P12']['vs_high_P14']}")
        g.check(rec["P12"]["r2_change"] <= thr, "A4: R2 is refused on area 12",
                f"change {rec['P12']['r2_change']} vs threshold {thr}")
    menu_shot(g, "a12-menu")

    g.teleport(*P14)
    g.world_settle()
    rec["P14_back"] = here(g)
    e = snap(g, "a14b-arrived")
    rec["title_P14_back"] = window_titles()
    g.press("r2")
    f = snap(g, "a14b-after-r2")
    rec["P14_back_r2_change"] = fdiff(e, f)
    if control_ok:
        g.check(rec["P14_back_r2_change"] > thr, "A5: back on area 14, R2 works again",
                f"change {rec['P14_back_r2_change']} vs threshold {thr}")
    g.press("r2")
    g.wait_frames(SETTLE)


def height_samples(g, tag: str, at, presses=("up", "down", "left")):
    rows = []
    g.teleport(*at)
    g.world_settle()
    rows.append({"after": "teleport", **here(g)})
    g.shot(f"{tag}-teleport")
    for b in presses:
        g.hold(b, 6)
        g.wait_frames(20)
        if not g.state.on_world:
            recover(g, f"{tag} hold {b}")
            g.teleport(*at)
            g.world_settle()
            continue
        g.world_settle()
        rows.append({"after": f"hold {b} 6", **here(g)})
    g.shot(f"{tag}-done")
    return rows


def vertical_part(g):
    rec = _RECORD["vertical"]
    can = VERT["canopy"]
    rec["forest"] = height_samples(g, "v-forest", tuple(can["forest"]["world"]))
    rec["lawn"] = height_samples(g, "v-lawn", tuple(can["lawn"]["world"]))
    bas = VERT["basin_3_7"]["teleport"]
    rec["basin"] = height_samples(g, "v-basin", tuple(bas["world"]))
    lows = [r["y"] for r in rec["basin"] if r.get("y") is not None]
    g.check(bool(lows) and min(lows) < -4.0, "V10: the actor stands below y=-4 in the (3,7) basin",
            f"published heights {lows} (offline floor {bas['ground_y']})")


def run(g):
    g.note("terrain_session1b: area layer by teleport + vertical envelope, no deploy")
    reach_world(g)
    st = g.state
    _RECORD["start"] = here(g)
    print(f"[t1b] on the world: id {st.world_id} at {st.world_pos}, scenario {st.scenario}; titles {window_titles()}")
    g.check(0 <= st.scenario < 4990, "precondition: scenario counter below 4990", f"scenario {st.scenario}")
    for name, part in (("vertical", vertical_part), ("area", area_part)):
        try:
            part(g)
        except Exception as err:
            _RECORD["notes"].append(f"{name} part raised: {err!r}")
            g.check(False, f"the {name} part ran to completion", repr(err))
            if not g.state.on_world:
                try:
                    recover(g, f"after the {name} part")
                except Exception as e2:
                    print(f"[t1b] recovery failed: {e2}")
    g.shot("99-done")
    try:
        (g.run_dir / "terrain_session1.json").write_text(json.dumps(_RECORD, indent=1, default=str), encoding="utf-8")
    except Exception as err:
        print(f"[t1b] could not write the record: {err}")
