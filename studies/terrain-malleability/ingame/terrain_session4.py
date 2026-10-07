"""In-game session 4 -- the DATA-DRIVEN form switch (experiment rank 2, rungs F0 + F1). DEPLOYS into the scratch
mod folder FF9CustomMap-lab ONLY (owner-approved; first in FolderNames; removed after the study).

Deployed (forms_build.py, then copied into FF9CustomMap-lab):
  StreamingAssets/Data/World/Environment.txt
      Place WaterShrine      [Condition=WorldDisc == 1 && (GetEventGlobalByte(1089) & 1) != 0]
      Place BlackMageVillage [Condition=WorldDisc == 1 && (GetEventGlobalByte(1089) & 1) != 0]
  FF9_Data/WorldMap/Disc1/0_1/r14/Block[22][14] Terrain2.ff9mesh
      the cell's stock FORM-2 terrain with a disc of radius 12 about (1440, -928) flattened to y 26.0

REGISTERED PREDICTIONS (forms F6/F13/F14, before the run):
  E0  flag 8712 OFF, scenario 0: Water Shrine Form 1 (open sea at the vantage); BMV centre reads STOCK 21.5625
      (Form 1 walks TerrainForm1 -- our Terrain2 file is loaded but inactive)
  E1  flag 8712 ON + a world reload (field round trip), STILL scenario 0: the Water Shrine shows its Form-2 spire --
      a mod-folder condition replaced the stock scenario window (F6); BMV centre reads 26.0 (our Terrain2 binds by
      its child name under 0_1 and walks as Form 2 -- F13, never loaded in-game before) and the 4u-east point reads
      23.32 (stock 17.42)
  E2  flag OFF + reload: back to Form 1 at both (the switch is reversible per load)
  LOG Memoria.log carries "[WorldMeshOverride] loaded 'WorldMap/Disc1/0_1/r14/Block[22][14] Terrain2'"
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILD = json.loads((HERE / "out" / "forms_build.json").read_text(encoding="utf-8"))
VAN = json.loads((HERE / "out" / "vantage_prep.json").read_text(encoding="utf-8"))

LANDING_FIELD = 6603
EXIT_AT = (400.0, -1400.0)
DOOR = [[285, -352], [875, -460], [424, -2944], [-166, -2836]]
LANDING = (68.0, -444.0)
YAW = 142.13
FLAG = BUILD["flag"]
PROBES = BUILD["predicted"]["probes"]
TOL = 0.15

_RECORD: dict = {"phases": {}}


def here(g) -> dict:
    st = g.state
    return {"x": st.world_x, "z": st.world_z, "y": st.world_y, "world": st.world_id, "scenario": st.scenario}


def walk_out(g):
    g.wait_frames(45)
    g.calibrate_axes(hazards=[DOOR])
    g.walk_to(*EXIT_AT, strict=False, halt_on_transition=True)
    g.wait_world(timeout=90)
    g.world_settle()
    g.world_face(YAW, home=LANDING, tolerance=2.0)
    g.teleport(*LANDING)
    g.world_settle()


def read_phase(g, tag):
    rec = {"start": here(g), "bmv": {}}
    for name in ("center", "e4"):
        pr = PROBES[name]
        g.teleport(*pr["world"])
        g.world_settle()
        g.wait_frames(20)
        rec["bmv"][name] = {"y": g.state.world_y, "stock": pr["stock"], "flattened": pr["flattened"]}
    g.teleport(*VAN["WaterShrine"]["vantage"])
    g.world_settle()
    g.wait_frames(90)
    rec["shot"] = str(g.shot(f"{tag}-WaterShrine"))
    g.teleport(*PROBES["center"]["world"])
    g.world_settle()
    g.wait_frames(60)
    g.shot(f"{tag}-BMV")
    _RECORD["phases"][tag] = rec
    return rec


def form_of(rec):
    out = []
    for name, r in rec["bmv"].items():
        y = r["y"]
        out.append(2 if y is not None and abs(y - r["flattened"]) <= TOL else
                   1 if y is not None and abs(y - r["stock"]) <= TOL else 0)
    return out


def run(g):
    g.note("terrain_session4: Environment.txt flag condition + a Terrain2 override, FF9CustomMap-lab")
    g.newgame()
    g.warp(LANDING_FIELD)
    walk_out(g)
    e0 = read_phase(g, "e0-flag-off")
    g.check(form_of(e0) == [1, 1], "E0: flag off -- BMV reads STOCK ground (Terrain2 loaded but Form 1 active)",
            json.dumps(e0["bmv"]))

    g.flag(FLAG, True)
    g.world_warp(LANDING_FIELD)
    walk_out(g)
    e1 = read_phase(g, "e1-flag-on")
    g.check(e1["start"]["scenario"] == 0, "E1 precondition: still scenario 0", f"{e1['start']['scenario']}")
    g.check(form_of(e1) == [2, 2],
            "E1: flag on + reload -- BMV walks OUR Terrain2 (flattened plateau 26.0; east point 23.32)",
            json.dumps(e1["bmv"]))

    g.flag(FLAG, False)
    g.world_warp(LANDING_FIELD)
    walk_out(g)
    e2 = read_phase(g, "e2-flag-off-again")
    g.check(form_of(e2) == [1, 1], "E2: flag off + reload -- back to stock (reversible per load)",
            json.dumps(e2["bmv"]))
    g.shot("99-done")
    try:
        (g.run_dir / "terrain_session4.json").write_text(json.dumps(_RECORD, indent=1, default=str), encoding="utf-8")
    except Exception as err:
        print(f"[t4] could not write the record: {err}")
