"""Vehicle session 1 -- THE AIRSHIP UNDER THE HARNESS: the DLL-free route, README rank 5's flight part (the 42.1875
ceiling over the 42.64 summit) and V13's landing rules. NO DEPLOY (stock disc-1 terrain, the live mod folders as
they are). One launch.

    py studies/terrain-malleability/ingame/veh_prep.py          # route evidence + every point below
    py tools/play.py studies/terrain-malleability/ingame/veh_session1.py --label veh-session1
    py studies/terrain-malleability/ingame/veh_post.py <run dir>  # re-scores the flight samples on the live mesh

ROUTE (veh_PLAN.md section 2): New Game -> field 6603 at ScenarioCounter 10650 -> poke gEventGlobal[190] = 8
(Hilda Garde III), [191] = 0 (no chocobo object), the airship record [74..82] = LOW at its ground height, facing 192
-> walk out of the door. The 6603 cascade (key 35, band 10400-11089) loads WORLD07 = 9007, whose Main_Init spawns
the airship (entry 6) because SC >= 10400, and entry 6's Init binds control to it because [190] == 8 (AttachObject
(12, 6, 0) + DefinePlayerCharacter). All from out/veh_prep.json["route"] (the live bytes).

REGISTERED PREDICTIONS (points and simulations: out/veh_prep.json["air"]):
  R0  world 9007, published vehicle 8, control true, and the CONTROLLED actor is the airship: world position = LOW
      (1207.37, -964.61) +-0.5 (the on-foot anchor would publish the landing (68, -444)); y = ground(LOW) 2.777 +-0.05
      (ff9.cs:5513-5517 raises a flyer to the ground it is below).
  R1  climb calibration: holding "down" raises y (InvertedFlightY = 1 inverts LY, ff9.cs:6278 / :6310-6312).
  S1  floor-raise instrument: from y ~2.8 teleport to HIGH (1034.37, -823.61): y = ground(HIGH) 28.866 +-0.05.
  S2  RANK 5: from y ~28.9 teleport to SUMMIT (1225.53, -926.47), ground 42.639 (topo 49, legal for the airship):
      the floor raise lifts it to 42.639 and the ceiling, applied AFTER it (ff9.cs:5518-5521), puts it back:
      y = 42.1875 +-0.004 -- the airship sits 0.45u INSIDE the rock. (42.64 would refute the ordering.)
  S3  holding climb on the summit for 40 frames: y stays 42.1875 +-0.004.
  S4  control: teleport to HIGH at y 42.1875: y stays 42.1875 (the ceiling applies everywhere, not only over rock);
      holding dive then brings it down to the floor, y = 28.866 +-0.05.
  S5  (scored offline by veh_post.py) throttle across the summit at the ceiling: no sample has y > 42.1875 + 0.004,
      and every sample over ground > 42.1875 reads exactly 42.1875.
  V13 landing = Cancel KEYON (WORLD07 entry 3 func 1, [190] == 8 arm): RunWorldCode(28) -> w_movementGetGetoff
      (ff9.cs:5746-5917) then the .eb's own topograph policy (lands only on topo 0..13 under the airship):
      L2  SEA (1161.9, -1036.71), topo 57: refused -- the own-tile foot check fails. Vehicle stays 8, no motion.
      L3  (1284.37, -820.61), topo 42, flat, every heading's probes foot-legal (simulated, 72 headings): the ENGINE
          accepts, the .eb policy refuses (42 not in 0..13). Vehicle stays 8.
      L1  (1262.37, -930.61), topo 12, flat: lands. The first sweep heading's 8th probe is at radius x 8/8 = 2.5u
          (ff9.cs:5858-5866), so the player is put down EXACTLY 2.50u (+-0.05) from where the airship hovered,
          whatever its heading (simulated: 72/72 headings -> 2.5); vehicle -> 0; then y = ground there +-0.1.
"""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import veh_lib as V                                   # noqa: E402

P = V.prep()["air"]
R = V.prep()["route"]
SC = 10650
_RECORD: dict = {"notes": []}


def _pt(k):
    return tuple(P[k]["world"])


def run(g):
    g.note("veh_session1: airship route, rank 5 flight, V13 landing (no deploy)")
    rec = _RECORD
    rec["route_prep"] = R["dispatchers"]["9007"]
    pokes = {190: 8, 191: 0}
    pokes.update({int(k): v for k, v in P["spawn"]["record"].items()})
    V.reach_world_as(g, rec, scenario=SC, pokes=pokes, expect_world=9007, first=True)
    a = rec["arrival"]
    lo = _pt("low")
    d0 = math.hypot(a["x"] - lo[0], a["z"] - lo[1]) if a["x"] is not None else None
    g.check(a["world"] == 9007 and a["vehicle"] == 8 and a["control"] and d0 is not None and d0 <= 0.5,
            "R0: 9007 loaded with control BOUND TO THE AIRSHIP (published position = the poked airship record)",
            json.dumps({"arrival": a, "dist_to_LOW": d0}))
    g.check(a["y"] is not None and abs(a["y"] - P["low"]["ground"]) <= 0.05,
            "R0b: the airship sits on the ground it spawned over", f"y {a['y']} vs ground {P['low']['ground']}")
    if not (a["vehicle"] == 8 and d0 is not None and d0 <= 0.5):
        g.shot("r0-failed")
        V.save(g, "veh_session1.json", rec)
        return
    g.shot("r0-airship")

    climb = V.calibrate_climb(g, rec)
    g.check(climb == "down", "R1: holding 'down' climbs (InvertedFlightY = 1)", json.dumps(rec["climb_calibration"]))
    if climb is None:
        V.save(g, "veh_session1.json", rec)
        return
    dive = "up" if climb == "down" else "down"
    rec["floor_back"] = V.plateau_y(g, dive)

    # S1 -- floor raise instrument
    s1 = V.tp(g, *_pt("high"))
    rec["S1"] = s1
    g.check(s1["y"] is not None and abs(s1["y"] - P["high"]["ground"]) <= 0.05,
            "S1: teleported low onto HIGH, the floor raise puts the airship on the ground there",
            f"y {s1['y']} vs ground {P['high']['ground']}")
    # S2 -- the summit
    s2 = V.tp(g, *_pt("summit"))
    rec["S2"] = s2
    g.shot("s2-summit")
    g.check(s2["y"] is not None and abs(s2["y"] - V.CEILING) <= 0.004,
            "S2 (RANK 5): over the 42.64 summit the airship reads the 42.1875 ceiling -- inside the rock",
            f"y {s2['y']} ground {P['summit']['ground']} (42.64 would mean the ceiling is applied before the raise)")
    # S3 -- climbing on the summit
    s3a = V.settle3(g)
    g.hold(climb, 40)
    g.wait_frames(46)
    s3 = V.settle3(g)
    rec["S3"] = {"before": s3a, "after": s3}
    g.check(s3["y"] is not None and abs(s3["y"] - V.CEILING) <= 0.004,
            "S3: climbing on the summit cannot leave the ceiling", f"{s3a['y']} -> {s3['y']}")
    # S5 -- throttle across the summit at the ceiling (scored offline by veh_post.py)
    rad = V.radial(*_pt("summit"))
    s5 = V.hold_until(g, ["confirm"], measure=rad, done=lambda s: (rad(s) or 0.0) >= 25.0,
                      stall_s=1.0, start_s=3.0, max_s=8.0)
    rec["S5"] = s5
    ymax = max((x["y"] for x in s5["samples"] if x["y"] is not None), default=None)
    g.check(ymax is not None and ymax <= V.CEILING + 0.004,
            "S5: flying off the summit at the ceiling, no sample rises above 42.1875",
            f"outcome {s5['outcome']}, {len(s5['samples'])} samples, y max {ymax}")
    # S4 -- the ceiling everywhere, then the floor
    s4a = V.tp(g, *_pt("high"))
    g.check(s4a["y"] is not None and abs(s4a["y"] - V.CEILING) <= 0.004,
            "S4a: at the ceiling over HIGH (ground 28.9) the airship stays at 42.1875", f"y {s4a['y']}")
    s4 = V.plateau_y(g, dive, max_s=10.0)
    rec["S4"] = {"at_high": s4a, "dive": {k: s4[k] for k in ("outcome", "y_start", "y_end")}}
    g.check(s4["y_end"] is not None and abs(s4["y_end"] - P["high"]["ground"]) <= 0.05,
            "S4b: diving over HIGH stops on its ground (the floor)", f"y {s4['y_end']} vs {P['high']['ground']}")

    # V13 -- landing. Refusals first (they leave the airship flying), the accepted landing last.
    for key, label in (("sea", "L2"), ("l3", "L3")):
        p = _pt(key)
        s = V.tp(g, *p)
        g.press("cancel", 2)
        g.wait_frames(150)
        e = V.settle3(g)
        moved = None if None in (s["x"], e["x"]) else math.hypot(e["x"] - s["x"], e["z"] - s["z"])
        rec[label] = {"at": s, "after": e, "moved": moved, "sim": P[key].get("sim")}
        g.check(e["vehicle"] == 8 and moved is not None and moved < 0.3,
                f"{label}: Cancel over {key} does NOT land (vehicle stays 8, no motion)",
                json.dumps({"vehicle": e["vehicle"], "moved": moved, "topo": P[key].get("topo")}))
    p = _pt("l1")
    s = V.tp(g, *p)
    g.shot("l1-before")
    g.press("cancel", 2)
    landed = None
    try:
        landed = g.wait_for(lambda st: st.vehicle == 0 and st.control and st.world_x is not None, timeout=20,
                            what="the landing to hand control to the player (vehicle 0)")
    except Exception as err:                               # noqa: BLE001
        rec["notes"].append(f"L1 landing wait: {err}")
    e = V.settle3(g)
    dist = None if None in (s["x"], e["x"]) else math.hypot(e["x"] - s["x"], e["z"] - s["z"])
    rec["L1"] = {"airship_at": s, "player_at": e, "dist": dist, "sim": P["l1"].get("sim")}
    g.shot("l1-after")
    g.check(landed is not None and e["vehicle"] == 0 and dist is not None and abs(dist - 2.5) <= 0.05,
            "L1 (V13): the airship lands and the player is put down 2.50u from it (the first sweep heading's 8th probe)",
            json.dumps({"vehicle": e["vehicle"], "dist": dist}))
    V.save(g, "veh_session1.json", rec)
