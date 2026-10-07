"""In-game session 5 -- the BEACH-SEAM TEAR (experiment rank 3; stitch lane S5/S6, probe P1). DEPLOYS into the
scratch mod folder FF9CustomMap-lab ONLY (owner-approved).

Deploy (one at a time, one launch each; the amount is passed to the scenario as $TEAR_RAISE):
    cd ff9mapkit && py -m ff9mapkit world-terrain --mod-folder FF9CustomMap-lab --radius 16 --at 480 -1120 --raise 3
    (control run: --raise 1)
`terrain.reshape` writes ONLY the Terrain part of (7,17) (+ its Disc4 mirror, inside the lab folder), so the
Terrain|Beach1 welds along the shore tear by exactly the raise there (S5).

The seam runs along z ~ -1120 at x 476-480: Beach1 (topo 30, ground 0.36-0.77) to the south, Terrain (topo 31) to
the north. Crossings start on the foam and walk NORTH (bearing 90) 3u; the reverse starts on the terrain at
z = -1117 and walks SOUTH (bearing 270) 4u. Yaw is set on the landing lawn (clear 32u cones at both bearings).

REGISTERED PREDICTIONS (probe_detail.json P1_A3, S6):
  +3  beach -> terrain REFUSED at all three lines (seam rise 2.53-3.0 > the 2.34375 climb ceiling; progress < 1u);
      terrain -> beach LEGAL (descent is always legal) -- a ONE-WAY WALL along the shore
  +1  beach -> terrain LEGAL at all three lines (the slit is ~1u, under the ceiling); terrain -> beach legal
  LOOK frames at the seam from the south for the slit
"""
import json
import os
from pathlib import Path

RAISE = float(os.environ.get("TEAR_RAISE", "3"))
LANDING_FIELD = 6603
EXIT_AT = (400.0, -1400.0)
DOOR = [[285, -352], [875, -460], [424, -2944], [-166, -2836]]
LANDING = (68.0, -444.0)
LINES_X = (476.28, 479.64, 480.18)
BEACH_Z = {476.28: -1120.28, 479.64: -1120.18, 480.18: -1120.36}
TERRAIN_Z = -1117.0

_RECORD: dict = {"raise": RAISE, "north": [], "south": []}


def here(g) -> dict:
    st = g.state
    return {"x": st.world_x, "z": st.world_z, "y": st.world_y, "ui": st.ui_state}


def run(g):
    g.note(f"terrain_session5: beach-seam tear at (7,17), raise {RAISE}")
    g.newgame()
    g.warp(LANDING_FIELD)
    g.wait_frames(45)
    g.calibrate_axes(hazards=[DOOR])
    g.walk_to(*EXIT_AT, strict=False, halt_on_transition=True)
    g.wait_world(timeout=90)
    g.world_settle()

    face = g.world_face(90.0, home=LANDING, tolerance=2.0)
    g.teleport(476.28, -1124.0)
    g.world_settle()
    g.wait_frames(90)
    g.shot(f"seam-look-raise{RAISE:g}")
    for x in LINES_X:
        start = (x, BEACH_Z[x])
        g.teleport(*start)
        g.world_settle()
        g.wait_frames(15)
        st0 = here(g)
        w = g.world_approach(90.0, 3.0, speed=face.get("speed"), burst_frames=6)
        _RECORD["north"].append({"x": x, "start": st0, "outcome": w["outcome"], "progress": w.get("progress"),
                                 "y_max": w.get("y_max"), "end": here(g)})
        if w["outcome"] == "left_world":
            return
    face2 = g.world_face(270.0, home=LANDING, tolerance=2.0)
    for x in LINES_X:
        g.teleport(x, TERRAIN_Z)
        g.world_settle()
        g.wait_frames(15)
        st0 = here(g)
        w = g.world_approach(270.0, 4.0, speed=face2.get("speed"), burst_frames=6)
        _RECORD["south"].append({"x": x, "start": st0, "outcome": w["outcome"], "progress": w.get("progress"),
                                 "end": here(g)})
        if w["outcome"] == "left_world":
            return

    north_ok = [r["outcome"] == "reached" for r in _RECORD["north"]]
    south_ok = [r["outcome"] == "reached" for r in _RECORD["south"]]
    detail = "; ".join(f"x {r['x']}: {r['outcome']} {r['progress']:.2f}u (y {r['start']['y']}->{r['end']['y']})"
                       for r in _RECORD["north"])
    if RAISE >= 2.5:
        g.check(not any(north_ok), f"+{RAISE:g}: beach -> terrain is REFUSED at every line (one-way wall)", detail)
    else:
        g.check(all(north_ok), f"+{RAISE:g} control: beach -> terrain stays LEGAL at every line", detail)
    g.check(all(south_ok), f"+{RAISE:g}: terrain -> beach is LEGAL at every line (descent)",
            "; ".join(f"x {r['x']}: {r['outcome']} {r['progress']:.2f}u" for r in _RECORD["south"]))
    g.teleport(476.28, -1124.0)
    g.world_settle()
    g.wait_frames(60)
    g.shot(f"99-done-raise{RAISE:g}")
    try:
        (g.run_dir / "terrain_session5.json").write_text(json.dumps(_RECORD, indent=1, default=str), encoding="utf-8")
    except Exception as err:
        print(f"[t5] could not write the record: {err}")
