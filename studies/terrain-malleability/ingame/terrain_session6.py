"""In-game session 6 -- the DISC-4 CRACK and its replay (experiment rank 4; gap_disc4_edit_reach G3, defect 8).
DEPLOYS into the scratch mod folder FF9CustomMap-lab ONLY (owner-approved). $CRACK_PHASE selects the deploy state:

  crack   cd ff9mapkit && py -m ff9mapkit world-terrain --mod-folder FF9CustomMap-lab --radius 16 --at 256 -872 --raise 4
          -> writes Disc1 (3,13)+(4,13); auto_mirror copies (3,13) to Disc4 but SKIPS (4,13) ("real cell differs across
          discs in ['sea1']") -- so disc 4 gets half the hill
  replay  ... the same command again with --disc 4 (writes Disc4 (3,13)+(4,13) from disc-4 stock)

Points straddle the block border x = 256, off-lattice (out/crack_predict.json, the live sky query incl. the lab):
  W  (254.37, -871.37)  disc1 5.198  disc4 5.197          E  (257.63, -871.37)  disc1 5.397  disc4 1.750 (crack)
  W2 (253.13, -873.61)  disc1 4.888  disc4 4.888          E2 (258.87, -873.61)  disc1 5.460  disc4 2.088 (crack)

REGISTERED PREDICTIONS:
  crack   disc 1 reads the disc-1 column (smooth hill); disc 4 reads W/W2 raised but E/E2 STOCK -- a ~3.45u step at
          x = 256; walking WEST from E on disc 4 is refused at the border (climb > 2.34375)
  replay  disc 4 reads the disc-1 column at all four points (+-0.15) -- the replay heals the crack
"""
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRED = json.loads((HERE / "out" / "crack_predict.json").read_text(encoding="utf-8"))
PHASE = os.environ.get("CRACK_PHASE", "crack")
LANDING_FIELD = 6603
EXIT_AT = (400.0, -1400.0)
DOOR = [[285, -352], [875, -460], [424, -2944], [-166, -2836]]
LANDING = (68.0, -444.0)
TOL = 0.15
_RECORD: dict = {"phase": PHASE}


def walk_out(g):
    g.wait_frames(45)
    g.calibrate_axes(hazards=[DOOR])
    g.walk_to(*EXIT_AT, strict=False, halt_on_transition=True)
    g.wait_world(timeout=90)
    g.world_settle()


def readout(g, disc_tag):
    rows = {}
    for k, p in PRED["disc1"].items():
        g.teleport(*p["world"])
        g.world_settle()
        g.wait_frames(20)
        rows[k] = {"y": g.state.world_y, "disc1": PRED["disc1"][k]["y"], "disc4": PRED["disc4"][k]["y"]}
    _RECORD[disc_tag] = {"scenario": g.state.scenario, "world": g.state.world_id, "rows": rows}
    return rows


def run(g):
    g.note(f"terrain_session6: disc-4 crack, phase {PHASE}")
    g.newgame()
    g.warp(LANDING_FIELD)
    walk_out(g)
    r1 = readout(g, "disc1")
    g.check(all(abs(r["y"] - r["disc1"]) <= TOL for r in r1.values()), "disc 1: the hill is smooth across x = 256",
            json.dumps(r1))
    g.world_warp(LANDING_FIELD, scenario=11100)
    walk_out(g)
    r4 = readout(g, "disc4")
    if PHASE == "crack":
        g.check(all(abs(r4[k]["y"] - r4[k]["disc4"]) <= TOL for k in r4),
                "disc 4 (crack): W/W2 raised, E/E2 stock -- the mirror skipped (4,13)", json.dumps(r4))
        face = g.world_face(180.0, home=LANDING, tolerance=2.0)
        g.teleport(*PRED["disc1"]["E"]["world"])
        g.world_settle()
        g.wait_frames(15)
        w = g.world_approach(180.0, 5.0, speed=face.get("speed"), burst_frames=6)
        _RECORD["cross_west"] = {"outcome": w["outcome"], "progress": w.get("progress"), "end_x": g.state.world_x,
                                 "end_y": g.state.world_y}
        if w["outcome"] != "left_world":
            g.check(w["outcome"] == "blocked" and g.state.world_x > 255.5,
                    "disc 4 (crack): walking west from the stock side is refused at the border",
                    json.dumps(_RECORD["cross_west"]))
        g.teleport(257.63, -880.0)
        g.world_settle()
        g.wait_frames(90)
        g.shot("crack-disc4")
    else:
        g.check(all(abs(r4[k]["y"] - r4[k]["disc1"]) <= TOL for k in r4),
                "disc 4 (replay): all four points match the disc-1 hill -- the replay heals the crack", json.dumps(r4))
    (g.run_dir / "terrain_session6.json").write_text(json.dumps(_RECORD, indent=1, default=str), encoding="utf-8")
