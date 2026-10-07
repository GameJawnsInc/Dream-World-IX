"""In-game session 4b -- replicate session 4's E1 at OFF-LATTICE points (FF9CustomMap-lab deploy as in session 4).

Session 4's east point (1444, -928) sat exactly on a shared triangle edge and read y = 0.0 in Form 2: the
LATTICE-EDGE TELEPORT TRAP (memory project-ff9-overworld-placement-rules section 2 -- an exact-lattice sky cast can
float-miss both edge tris). This reads four mid-triangle points instead, predicted offline from the deployed
Terrain2 bytes and the stock Form-1 terrain (out/forms_midcell.json):
  m1 (1441.37, -929.61)  F1 19.661  F2 24.375
  m2 (1444.37, -928.61)  F1 16.741  F2 22.965
  m3 (1436.63, -926.39)  F1 27.537  F2 26.437
  m4 (1443.13, -932.29)  F1 17.229  F2 21.736
REGISTERED: flag off -> all four read F1 (+-0.15); flag 8712 on + a world reload -> all four read F2.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PTS = json.loads((HERE / "out" / "forms_midcell.json").read_text(encoding="utf-8"))
LANDING_FIELD = 6603
EXIT_AT = (400.0, -1400.0)
DOOR = [[285, -352], [875, -460], [424, -2944], [-166, -2836]]
FLAG = 8712
TOL = 0.15
_RECORD: dict = {}


def walk_out(g):
    g.wait_frames(45)
    g.calibrate_axes(hazards=[DOOR])
    g.walk_to(*EXIT_AT, strict=False, halt_on_transition=True)
    g.wait_world(timeout=90)
    g.world_settle()


def read(g, tag, form):
    rows = {}
    for k, p in PTS.items():
        g.teleport(*p["world"])
        g.world_settle()
        g.wait_frames(20)
        y = g.state.world_y
        rows[k] = {"y": y, "form1": p["form1"], "form2": p["form2"]}
    _RECORD[tag] = rows
    want = f"form{form}"
    g.check(all(r["y"] is not None and abs(r["y"] - r[want]) <= TOL for r in rows.values()),
            f"{tag}: all four off-lattice points read Form-{form} ground", json.dumps(rows))


def run(g):
    g.note("terrain_session4b: Terrain2 binding at off-lattice points")
    g.newgame()
    g.warp(LANDING_FIELD)
    walk_out(g)
    read(g, "flag-off", 1)
    g.flag(FLAG, True)
    g.world_warp(LANDING_FIELD)
    walk_out(g)
    read(g, "flag-on", 2)
    g.teleport(1441.37, -929.61)
    g.world_settle()
    g.wait_frames(90)
    g.shot("bmv-plateau-form2")
    (g.run_dir / "terrain_session4b.json").write_text(json.dumps(_RECORD, indent=1), encoding="utf-8")
