"""In-game session 2 -- the STOCK form switch, NO DEPLOY (no file is written to any mod folder).

Drives the stock place conditions (WorldConfiguration.cs:165-193) with the harness alone:
  * gEventGlobal bits 815 / 814 (= byte 101 & 0x80 / & 0x40)  -> Mognet Central (16,1) / Chocobo's Paradise (0,0)
  * the scenario counter (warp ... scenario)                    -> Cleyra (SC >= 4990), Water Shrine (10600..10699)
All target cells are stock (no live override; forms_stock_prep.py refuses otherwise).

    py studies/terrain-malleability/ingame/forms_stock_prep.py      # Cleyra height points
    py tools/play.py studies/terrain-malleability/ingame/terrain_session2.py --label terrain-session2

REGISTERED PREDICTIONS (forms lane F1/F3/F10, before the run):
  F-C0  scenario 0: the two Cleyra (14,12) lawn points read FORM-1 ground (3.471 / 2.923, +-0.15)
  F-M1  setting bits 815+814 ON the world map changes nothing visible until the world reloads (F3: forms are
        decided once per world load) -- the Mognet/Paradise frames before and after the poke match
  F-M2  after a field round trip (world reload), Mognet Central (16,1) shows its Form-2 object (2 -> 44 tris)
  F-C3  after a round trip at scenario 10650: Cleyra reads FORM-2 ground (3.906 / 3.309) -- walk-relevant geometry
        switched with the form (F1); the Water Shrine frame shows its Form-2 structure (terrain 22->157, object
        22->124)
The frames are judged by eye (and by a frame difference against the same-yaw pre-poke frame for F-M1).
"""
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
FSP = json.loads((HERE / "out" / "forms_stock_prep.json").read_text(encoding="utf-8"))
VAN = json.loads((HERE / "out" / "vantage_prep.json").read_text(encoding="utf-8"))
CLEYRA = FSP["Cleyra (14,12)"]["picks"][:2]

LANDING_FIELD = 6603
EXIT_AT = (400.0, -1400.0)
DOOR = [[285, -352], [875, -460], [424, -2944], [-166, -2836]]
LANDING = (68.0, -444.0)
YAW = 142.13
SETTLE = 90
TOL = 0.15

_RECORD: dict = {"phases": {}, "notes": []}


def _img(path):
    im = Image.open(path).convert("L")
    w, h = im.size
    im = im.crop((int(w * 0.15), int(h * 0.15), int(w * 0.85), int(h * 0.85))).resize((224, 126))
    return np.asarray(im, dtype=np.float32)


def fdiff(a, b) -> float:
    return round(float(np.mean(np.abs(_img(a) - _img(b)))), 3)


def here(g) -> dict:
    st = g.state
    return {"x": st.world_x, "z": st.world_z, "y": st.world_y, "world": st.world_id, "ui": st.ui_state,
            "scenario": st.scenario}


def walk_out(g):
    g.wait_frames(45)
    g.calibrate_axes(hazards=[DOOR])
    g.walk_to(*EXIT_AT, strict=False, halt_on_transition=True)
    g.wait_world(timeout=90)
    g.world_settle()
    g.world_face(YAW, home=LANDING, tolerance=2.0)
    g.teleport(*LANDING)
    g.world_settle()


def cleyra_heights(g):
    rows = []
    for p in CLEYRA:
        g.teleport(*p["world"])
        g.world_settle()
        g.wait_frames(20)
        rows.append({"point": p["world"], "y_form1": p["y_form1"], "y_form2": p["y_form2"], **here(g)})
    return rows


def vantage_shots(g, tag):
    shots = {}
    for nm in ("Mognet", "Paradise", "WaterShrine"):
        g.teleport(*VAN[nm]["vantage"])
        g.world_settle()
        g.wait_frames(SETTLE)
        shots[nm] = g.shot(f"{tag}-{nm}")
    return shots


def which_form(row):
    y = row.get("y")
    if y is None:
        return None
    if abs(y - row["y_form1"]) <= TOL:
        return 1
    if abs(y - row["y_form2"]) <= TOL:
        return 2
    return 0


def run(g):
    g.note("terrain_session2: the stock form switch via flags + scenario counter, no deploy")
    g.newgame()
    g.warp(LANDING_FIELD)
    walk_out(g)
    st = g.state
    print(f"[t2] on the world: id {st.world_id} scenario {st.scenario}")

    # ---- S0: scenario 0, flags off
    p = _RECORD["phases"]["S0"] = {"start": here(g)}
    p["cleyra"] = cleyra_heights(g)
    s0 = vantage_shots(g, "s0")
    forms = [which_form(r) for r in p["cleyra"]]
    g.check(forms == [1, 1], "F-C0: scenario 0 -- Cleyra reads its FORM-1 ground",
            "; ".join(f"y {r['y']} (f1 {r['y_form1']}, f2 {r['y_form2']})" for r in p["cleyra"]))

    # ---- S1: poke the Mognet/Paradise bits ON the world map, no reload
    g.flag(815, True)
    g.flag(814, True)
    g.wait_frames(30)
    s1 = vantage_shots(g, "s1")
    p = _RECORD["phases"]["S1"] = {"diff_vs_s0": {k: fdiff(s0[k], s1[k]) for k in s1}}
    print(f"[t2] S1 frame change vs S0 (same yaw, no reload): {p['diff_vs_s0']}")
    g.check(p["diff_vs_s0"]["Mognet"] <= 2.0 and p["diff_vs_s0"]["Paradise"] <= 2.0,
            "F-M1: poking bits 815/814 changes nothing until the world reloads",
            f"frame change vs the pre-poke frame: {p['diff_vs_s0']}")

    # ---- S2: a field round trip reloads the world (scenario still 0, bits on)
    g.world_warp(LANDING_FIELD)
    walk_out(g)
    p = _RECORD["phases"]["S2"] = {"start": here(g)}
    s2 = vantage_shots(g, "s2")
    p["diff_vs_s0"] = {k: fdiff(s0[k], s2[k]) for k in s2}
    p["cleyra"] = cleyra_heights(g)
    print(f"[t2] S2 frame change vs S0 (re-faced yaw): {p['diff_vs_s0']} -- judge Mognet/Paradise by eye")
    g.check([which_form(r) for r in p["cleyra"]] == [1, 1], "S2 control: Cleyra still FORM 1 at scenario 0",
            "; ".join(f"y {r['y']}" for r in p["cleyra"]))

    # ---- S3: round trip at scenario 10650 (Cleyra >= 4990, Water Shrine 10600..10699)
    g.world_warp(LANDING_FIELD, scenario=10650)
    walk_out(g)
    p = _RECORD["phases"]["S3"] = {"start": here(g)}
    print(f"[t2] S3 world {g.state.world_id} scenario {g.state.scenario}")
    p["cleyra"] = cleyra_heights(g)
    s3 = vantage_shots(g, "s3")
    p["diff_vs_s0"] = {k: fdiff(s0[k], s3[k]) for k in s3}
    g.check(g.state.scenario == 10650, "S3 precondition: the scenario counter reads 10650", f"{g.state.scenario}")
    g.check([which_form(r) for r in p["cleyra"]] == [2, 2],
            "F-C3: scenario 10650 -- Cleyra reads its FORM-2 ground (walk geometry switched with the form)",
            "; ".join(f"y {r['y']} (f1 {r['y_form1']}, f2 {r['y_form2']})" for r in p["cleyra"]))
    g.shot("99-done")
    try:
        (g.run_dir / "terrain_session2.json").write_text(json.dumps(_RECORD, indent=1, default=str), encoding="utf-8")
    except Exception as err:
        print(f"[t2] could not write the record: {err}")
