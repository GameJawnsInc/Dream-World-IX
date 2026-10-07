"""In-game session 1 for the terrain malleability study -- NO DEPLOY (reads the live install as it stands).

Experiment 1 (the AREA layer, README section 7.1 rank 1, parts a/c) and experiment 5 (the zero-edit VERTICAL session,
rank 5, canopy + basin parts). Points come from the offline preps (rerun them first; they read the live mesh):

    py studies/terrain-malleability/ingame/area_prep.py
    py studies/terrain-malleability/ingame/vertical_prep.py
    py tools/play.py studies/terrain-malleability/ingame/terrain_session1.py --label terrain-session1
    py studies/terrain-malleability/ingame/session1_post.py <run dir>      # scores heights against the mesh

REGISTERED PREDICTIONS (written before the run):
  A1  P14 (area 14) window title = "World Map: <id>, Lindblum Plateau"; P12 (area 12) = "..., Vube Desert"
      (ff9.cs:3745-3758, w_worldLocationName -> FF9TextTool.WorldLocationText(area)).
  A2  CONTROL: on P14, R2 toggles the camera (ff9.cs:6122 -> w_cameraChangeTrigger): the frame changes far more than
      the no-input noise between two frames.
  A3  Walking from P14 (high view) onto P12 forces the view back DOWN (ff9.cs:2771 sets upperCounterForce while
      scenario < 4990 and area == 12; :3123 drives the counter to 0) -- the P12 frame resembles the default view, not
      the high one.
  A4  On P12, R2 is REFUSED (ff9.cs:3199): the frame changes no more than the noise.
  A5  Back on P14, R2 works again (the force clears at counter 0, :3133).
  V3  Forest (topo 36/37/38): published height = ground - 1.171875; lawn (topo 0): published height = ground.
      (scored offline by session1_post.py against the live mesh at the exact x/z reached)
  V10 Basin (3,7): the actor stands at ~-5.76 on Terrain, no water part under him.
CALIBRATION: the lawn reading is the instrument check for V3; the P14 R2 toggle is the instrument check for A3/A4 --
if the control does not change the frame, A3/A4 are reported as proved-nothing, never as passes.
"""
import ctypes
import json
import math
from ctypes import wintypes
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
AREA = json.loads((HERE / "out" / "area_prep.json").read_text(encoding="utf-8"))
VERT = json.loads((HERE / "out" / "vertical_prep.json").read_text(encoding="utf-8"))

LANDING_FIELD = 6603                                   # FARSHORE (FF9CustomMap-world), the proven field -> world door
EXIT_AT = (400.0, -1400.0)
DOOR = [[285, -352], [875, -460], [424, -2944], [-166, -2836]]
P12 = tuple(AREA["P12"]["world"])
P14 = tuple(AREA["P14"]["world"])
B_14_12 = AREA["bearing_14_to_12"]
D_14_12 = AREA["distance_14_to_12"]
NAME = {12: AREA["location_text"]["12"], 14: AREA["location_text"]["14"]}
SETTLE = 90                                            # frames: >= 1.5 s at 60 fps; the counter needs 16 ticks
LOCK_SCENARIO = 4990

_RECORD: dict = {"area": {}, "vertical": {}, "notes": []}


# ------------------------------------------------------------------------------------------------ instruments
def window_titles(prefix: str = "World Map"):
    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(h, _l):
        n = user32.GetWindowTextLengthW(h)
        if n:
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(h, buf, n + 1)
            if buf.value.startswith(prefix):
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


def survive(g, where: str) -> bool:
    """A battle: record it, end it, get back on the map. Returns True when one happened."""
    st = g.state
    if st.on_world:
        return False
    _RECORD["notes"].append(f"battle (or map change) at {where}: ui {st.ui_state}")
    print(f"[t1] left the world at {where}: ui {st.ui_state}")
    try:
        g.wait_battle(timeout=30)
        if not g.flee(timeout=90):
            g.fight()
        g.leave_battle(timeout=120)
    except Exception as err:
        print(f"[t1] leaving the battle at {where} failed: {err}")
    g.wait_world(timeout=60)
    g.world_settle()
    return True


def menu_shot(g, name: str) -> None:
    """Open the main menu on the overworld, frame it (the location label), back out to WorldHUD.
    (Session.close_menu waits for the FIELD HUD, so it cannot close a world-map menu.)"""
    g.open_menu()
    snap(g, name, 30)
    for _ in range(6):
        if g.state.ui_state == "WorldHUD":
            return
        g.press("cancel", 6)
        g.wait_frames(25)
    g.wait_for(lambda s: s.ui_state == "WorldHUD", timeout=15, what="the world menu to close")


# ------------------------------------------------------------------------------------------------ parts
def area_part(g):
    rec = _RECORD["area"]
    g.teleport(*P14)
    face = g.world_face(B_14_12, home=P14, tolerance=6.0)
    g.world_settle()
    rec["P14_start"] = here(g)
    rec["face"] = {"speed": face.get("speed"), "error": face.get("error")}
    a = snap(g, "a14-default")
    rec["title_P14"] = window_titles()
    a2 = snap(g, "a14-default-noise", 60)
    noise = fdiff(a, a2)
    g.press("r2")
    b = snap(g, "a14-after-r2")
    toggled = fdiff(a, b)
    rec["P14"] = {"noise": noise, "r2_change": toggled}
    want14 = NAME[14]
    g.check(any(t.endswith(want14) for t in rec["title_P14"]), f"A1: P14 window title names '{want14}'",
            f"titles {rec['title_P14']}")
    control_ok = toggled > max(3 * noise, noise + 2.0)
    g.check(control_ok, "A2 (instrument): R2 changes the camera on area 14",
            f"frame change {toggled} vs no-input noise {noise}")

    # walk into area 12 while (if the control worked) the camera is HIGH
    walk = g.world_approach(B_14_12, D_14_12, speed=face.get("speed"), burst_frames=8)
    rec["walk_in"] = {"outcome": walk["outcome"], "progress": walk.get("progress")}
    if walk["outcome"] == "left_world" or survive(g, "the walk into area 12"):
        g.check(False, "A3-A5 walk into area 12 completed", "a battle interrupted the walk")
        return
    g.world_settle()
    rec["P12_reached"] = here(g)
    c = snap(g, "a12-arrived")
    rec["title_P12"] = window_titles()
    want12 = NAME[12]
    g.check(any(t.endswith(want12) for t in rec["title_P12"]), f"A1: P12 window title names '{want12}'",
            f"titles {rec['title_P12']} at ({rec['P12_reached']['x']}, {rec['P12_reached']['z']})")
    c_vs_default, c_vs_high = fdiff(c, a), fdiff(c, b)
    rec["P12"] = {"vs_default_P14": c_vs_default, "vs_high_P14": c_vs_high}
    g.press("r2")
    d = snap(g, "a12-after-r2")
    refused = fdiff(c, d)
    rec["P12"]["r2_change"] = refused
    if control_ok:
        g.check(c_vs_default < c_vs_high, "A3: on area 12 the view is forced back to the default (not the high one)",
                f"P12 frame vs P14 default {c_vs_default}, vs P14 high {c_vs_high}")
        g.check(refused <= max(3 * noise, noise + 2.0), "A4: R2 is refused on area 12",
                f"frame change {refused} vs noise {noise} (the P14 toggle changed {toggled})")
    else:
        rec["P12"]["verdict"] = "proved-nothing: the R2 control did not move the camera"
    try:
        menu_shot(g, "a12-menu")
    except Exception as err:
        rec["menu_error_P12"] = str(err)
        print(f"[t1] the main menu on P12 failed: {err}")

    # back onto area 14
    back = (B_14_12 + 180.0) % 360.0
    pos = (rec["P12_reached"]["x"], rec["P12_reached"]["z"])
    face2 = g.world_face(back, home=pos, tolerance=6.0)
    walk = g.world_approach(back, D_14_12, speed=face2.get("speed"), burst_frames=8)
    rec["walk_out"] = {"outcome": walk["outcome"], "progress": walk.get("progress")}
    if walk["outcome"] == "left_world" or survive(g, "the walk back to area 14"):
        return
    g.world_settle()
    rec["P14_back"] = here(g)
    e = snap(g, "a14b-arrived")
    rec["title_P14_back"] = window_titles()
    g.press("r2")
    f = snap(g, "a14b-after-r2")
    rec["P14_back_r2_change"] = fdiff(e, f)
    if control_ok:
        g.check(rec["P14_back_r2_change"] > max(3 * noise, noise + 2.0), "A5: back on area 14, R2 works again",
                f"frame change {rec['P14_back_r2_change']} vs noise {noise}")
    try:
        menu_shot(g, "a14-menu")
    except Exception as err:
        rec["menu_error_P14"] = str(err)
    g.press("r2")                                      # leave the camera where the session found it
    g.wait_frames(SETTLE)


def height_samples(g, tag: str, at, presses=("up", "down", "left")):
    """Teleport, read, then a few tiny holds (each re-grounds), reading after each. Scored offline."""
    rows = []
    g.teleport(*at)
    g.world_settle()
    rows.append({"after": "teleport", **here(g)})
    g.shot(f"{tag}-teleport")
    for k, b in enumerate(presses):
        g.hold(b, 6)
        g.wait_frames(20)
        if survive(g, f"{tag} hold {b}"):
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
    g.note("terrain_session1: area layer + vertical envelope, no deploy")
    g.newgame()
    g.warp(LANDING_FIELD)
    g.wait_frames(45)
    g.calibrate_axes(hazards=[DOOR])
    g.walk_to(*EXIT_AT, strict=False, halt_on_transition=True)
    g.wait_world(timeout=90)
    g.world_settle()
    st = g.state
    _RECORD["start"] = here(g)
    print(f"[t1] on the world: id {st.world_id} at {st.world_pos}, scenario {st.scenario}")
    g.check(0 <= st.scenario < LOCK_SCENARIO, "precondition: scenario counter below 4990 (the area-12 lock is live)",
            f"scenario {st.scenario}")
    for name, part in (("area", area_part), ("vertical", vertical_part)):
        try:
            part(g)
        except Exception as err:
            _RECORD["notes"].append(f"{name} part raised: {err!r}")
            g.check(False, f"the {name} part ran to completion", repr(err))
            if not g.state.on_world:
                try:
                    g.wait_world(timeout=60)
                except Exception:
                    pass
    g.shot("99-done")
    try:
        dest = g.run_dir / "terrain_session1.json"
        dest.write_text(json.dumps(_RECORD, indent=1, default=str), encoding="utf-8")
        print(f"[t1] wrote {dest}")
    except Exception as err:
        print(f"[t1] could not write the record: {err}")
