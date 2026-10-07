"""Vehicle session 2 -- THE CHOCOBO UNDER THE HARNESS: the canopy sink on a chocobo (vertical V3) and the chocobo's
own limit mask. NO DEPLOY. One launch, three world loads (foot calibration, yellow, light blue).

    py studies/terrain-malleability/ingame/veh_prep.py
    py tools/play.py studies/terrain-malleability/ingame/veh_session2.py --label veh-session2
    py studies/terrain-malleability/ingame/veh_post.py <run dir>

ROUTE: as veh_session1 at ScenarioCounter 10650 (-> 9007), with [190] = [191] = k (mode = owned tier: the stock board
writes [190] from [191], WORLD07 entry 2 func 1) and flags 809/810 (entry 5's Init hides the chocobo -- SetObjectFlags
(14) -- unless bit 810 is set, and an invisible object is skipped by w_movementUpdate's objIsVisible gate,
ff9.cs:5171). Main_Init spawns entry 5 because [191] != 0; its Init binds control because 1 <= [190] <= 6
(AttachObject(12, 5, 23) + DefinePlayerCharacter). The chocobo is placed from [83..91], which 6603's exit writes to
the landing itself, so it arrives where the player would. Chocobo rows 1-5 have encount 0 (TransportControls.csv
column 13): no random battles on a chocobo.

REGISTERED PREDICTIONS (out/veh_prep.json["choco"]):
  F0  (foot load, [190] = 0, the instrument) the walk speed on the landing lawn, u per game second.
  C0  (yellow load) vehicle 1, control true; the speed ratio chocobo/foot = speed_move 200/112 = 1.79 +-0.25
      (ff9.cs:6165: XZSpeed = S(speed_move); the rows differ only there) -- the controlled actor IS the chocobo.
  C1  V3 ON A CHOCOBO: forest (982.68, -1003.30), topo 37: y - ground = -1.171875 +-0.01 (chocobo indices 3-7 use
      slice_type 1, the same sink row as the party, ff9.cs:5484-5509 / sink array :19); lawn (972.18, -996.30),
      topo 0: y - ground = 0 +-0.01.
  C2  MASK, yellow (row 1 = the walking mask, no 53): from shore sand (480.37, -1120.61) (Beach1 topo 30, y 0.73),
      walking bearing 270 (south): BLOCKED at the waterline -- progress in [2.4, 3.8] = waterline 3.5 -1.1/+0.3
      (slide simulator, out/veh_prep.json choco.edge.sim: 3.28..3.42 over 2-6 tick bursts and a +-3 deg facing error,
      shore topographs only).
      [review] The first pick, (485.37, -1121.61), sat on a ~28-deg oblique shoreline: a refused chocobo takes the
      first legal of 7 slide angles each side (ff9.cs:5552-5603) and crept ESE along the sand to progress 7.2-7.5
      before world_approach called it blocked, so C2 would have failed with the mask law intact and C3's 5.0 bar
      could not tell yellow from light blue. veh_prep now requires the waterline to sit within 0.3u of the centre
      line's at lateral offsets -4..+4u (a straight shore square to the bearing) and the simulator to agree.
  C3  MASK, light blue (row 2 adds 51/53/54/55/61, flg_gake 1; shore 30-35 is neither ground nor water, so the
      ground->water refusal at ff9.cs:5703-5717 does not apply): same start, same bearing: PASSES the waterline,
      progress >= waterline + 2.0 = 5.5 (10.75u of light-blue-legal topo-53 water lie beyond it; simulated: reaches
      the 8u goal in every burst/facing case).
"""
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import veh_lib as V                                   # noqa: E402

PR = V.prep()
C = PR["choco"]
SC = 10650
_RECORD: dict = {"notes": []}


def speed_probe(g, rec_key, rec, frames=30):
    """u per game-second while holding 'up' on the landing lawn (yaw already faced, clear 32u cones)."""
    s0 = V.tp(g, *V.LANDING)
    st0 = g.state
    t0 = st0.raw.get("rt") or st0.mtime
    g.hold("up", frames)
    g.wait_frames(frames + 2)
    st1 = g.state
    t1 = st1.raw.get("rt") or st1.mtime
    d = math.hypot(st1.world_x - st0.world_x, st1.world_z - st0.world_z)
    rate = d / (t1 - t0) if t1 and t0 and t1 > t0 else None
    rec[rec_key] = {"dist": round(d, 3), "dt": None if not (t1 and t0) else round(t1 - t0, 3), "u_per_s": rate}
    V.settle3(g)
    return rate


def heights(g, at):
    rows = []
    s = V.tp(g, *at)
    rows.append({"after": "teleport", **s})
    for b in ("up", "down", "left"):
        g.hold(b, 6)
        g.wait_frames(20)
        rows.append({"after": f"hold {b} 6", **V.settle3(g)})
    return rows


def edge_walk(g, rec, key, speed):
    e = C["edge"]
    V.tp(g, *e["start"])
    w = g.world_approach(float(e["bearing"]), 8.0, burst_frames=6, speed=speed)
    rec[key] = {"outcome": w["outcome"], "progress": w["progress"], "trace": w["trace"],
                "y_min": w.get("y_min"), "y_max": w.get("y_max")}
    return w


def run(g):
    g.note("veh_session2: chocobo route, V3 on a chocobo, the chocobo limit mask (no deploy)")
    rec = _RECORD
    e = C["edge"]
    # F0 -- on foot (the instrument): face south on the landing lawn, measure the walk speed
    V.reach_world_as(g, rec.setdefault("foot", {}), scenario=SC, pokes={190: 0, 191: 0}, expect_world=9007, first=True)
    face = g.world_face(float(e["bearing"]), home=V.LANDING, tolerance=3.0)
    rec["foot"]["face"] = {k: face.get(k) for k in ("heading", "error", "speed")}
    foot = speed_probe(g, "speed", rec["foot"])
    # C0 -- yellow chocobo
    yrec = rec.setdefault("yellow", {})
    V.reach_world_as(g, yrec, scenario=SC, pokes={190: 1, 191: 1}, flags=(809, 810), expect_world=9007, first=False)
    a = yrec["arrival"]
    g.check(a["world"] == 9007 and a["vehicle"] == 1 and a["control"],
            "C0a: 9007 loaded with vehicle 1 and control", json.dumps(a))
    face = g.world_face(float(e["bearing"]), home=V.LANDING, tolerance=3.0)
    yrec["face"] = {k: face.get(k) for k in ("heading", "error", "speed")}
    rec["face_speed"] = face.get("speed")
    choco = speed_probe(g, "speed", yrec)
    ratio = (choco / foot) if (choco and foot) else None
    yrec["speed_ratio"] = ratio
    g.check(ratio is not None and abs(ratio - 200 / 112) <= 0.25,
            "C0b: the controlled actor IS the chocobo (speed ratio chocobo/foot = 200/112)",
            f"ratio {ratio} (foot {foot}, chocobo {choco} u/s)")
    # C1 -- canopy sink on the chocobo
    for k in ("forest", "lawn"):
        rows = heights(g, tuple(C[k]["world"]))
        yrec[k] = rows
        r0 = rows[0]
        dy = None if r0["y"] is None else r0["y"] - C[k]["ground"]
        g.check(dy is not None and abs(dy - C[k]["sink_pred"]) <= 0.01,
                f"C1 ({k}, topo {C[k]['topo']}): chocobo y - ground = {C[k]['sink_pred']}",
                f"y {r0['y']} ground {C[k]['ground']} dy {dy}")
    g.shot("c1-done")
    # C2 -- yellow at the shore
    w = edge_walk(g, yrec, "edge", yrec["face"]["speed"])
    g.shot("c2-yellow-edge")
    g.check(w["outcome"] == "blocked" and e["waterline"] - 1.1 <= (w["progress"] or 0) <= e["waterline"] + 0.3,
            "C2: the YELLOW chocobo (walking mask) stops at the waterline",
            f"{w['outcome']} at {w['progress']}u (waterline {e['waterline']}u, water topo {e['water_topo']})")
    # C3 -- light blue
    brec = rec.setdefault("lightblue", {})
    V.reach_world_as(g, brec, scenario=SC, pokes={190: 2, 191: 2}, flags=(809, 810), expect_world=9007, first=False)
    b = brec["arrival"]
    g.check(b["vehicle"] == 2 and b["control"], "C3a: reloaded as the light-blue chocobo (vehicle 2)", json.dumps(b))
    face = g.world_face(float(e["bearing"]), home=V.LANDING, tolerance=3.0)
    brec["face"] = {k: face.get(k) for k in ("heading", "error", "speed")}
    w = edge_walk(g, brec, "edge", brec["face"]["speed"])
    g.shot("c3-lightblue-edge")
    ys = [r.get("y") for r in w["trace"] if r.get("y") is not None]
    g.check((w["progress"] or 0) >= e["waterline"] + 2.0,
            "C3: the LIGHT-BLUE chocobo crosses the waterline into topo-53 water (its row-2 mask)",
            f"{w['outcome']} at {w['progress']}u (waterline {e['waterline']}u), y {ys[0] if ys else None} -> "
            f"min {min(ys) if ys else None}")
    V.save(g, "veh_session2.json", rec)
