"""Vehicle session 3 -- THE NO-FLY TOPOGRAPH (README rank 12, vertical V12). DEPLOYS into the scratch folder
FF9CustomMap-lab ONLY (veh_PLAN.md section 5, deploy D1): Disc1 `Block[1][13] Terrain.ff9mesh` from veh_build.py --
a flat slab at y 2.0 over the isolated ocean cell (1,13) carrying two identical rings (r 8..12): ring A topograph 15
(one of the 14 flight-blocked topographs stock never uses), ring B topograph 41 (legal) as the control. One launch.

    py studies/terrain-malleability/ingame/veh_prep.py && py studies/terrain-malleability/ingame/veh_build.py
    (orchestrator: deploy D1, relaunch-free if FF9CustomMap-lab is already in FolderNames -- the world reads
     .ff9mesh overrides at world load)
    py tools/play.py studies/terrain-malleability/ingame/veh_session3.py --label veh-session3

ROUTE: as veh_session1 (Hilda Garde III on 9007 at ScenarioCounter 10650), the airship record poked to ring A's
centre at y 2.0, so it LOADS inside ring A.

MECHANISM (ff9.cs:5605-5633, :5682-5727): a flyer makes ONE round check per tick, rotation 0 (no slide), a sky cast
with IgnoreExceptions at the next XZ, and moves ONLY if that tile's topograph is in its limit mask -- the altitude is
never consulted, and the vertical step (`pos4[1] += YSpeed`) sits INSIDE the same `if (flag3)`.

REGISTERED PREDICTIONS (out/veh_build.json; flight simulated from rest over 36 headings):
  N0  world 9007, vehicle 8, airship at ring A's centre (78.37, -846.61) +-0.5, y = 2.0 +-0.05 (the lab slab --
      stock sea here is y 0: this check also proves the deploy loaded).
  N1  LOW (y 2.0): full throttle from ring A's centre stalls at radius 6.65..8.02 (allow 6.3..8.4), y unchanged.
  N2  PUSHING: still holding throttle at the ring edge, add climb for 40 frames: y does not change (+-0.01) -- the
      climb is inside the refused move.
  N3  HIGH (y 42.1875): from ring A's centre, the same stall radius 6.3..8.4 -- the wall is the same at every altitude.
  K1  control HIGH: from ring B's centre (113.63, -881.39) the airship crosses ring B (topograph 41): radial progress
      >= 16 (simulated min 28.2 over 36 headings, the minimum heading being the one aimed at ring A).
  K2  control LOW (y 2.0): the same from ring B's centre, radial progress >= 16.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import veh_lib as V                                   # noqa: E402

B = V.build()
A_C = tuple(B["centres"]["A"]["world"])
B_C = tuple(B["centres"]["B"]["world"])
STOP_LO, STOP_HI = 6.3, 8.4
SC = 10650
_RECORD: dict = {"notes": [], "build": {k: B[k] for k in ("cell", "slab_y", "ring_in", "ring_out", "centres")}}


def throttle(g, centre, done_r=None):
    rad = V.radial(*centre)
    r = V.hold_until(g, ["confirm"], measure=rad, done=(lambda s: (rad(s) or 0.0) >= done_r) if done_r else None,
                     stall_s=1.0, start_s=3.0, max_s=10.0)
    r["end"] = V.settle3(g)
    r["radius"] = rad(g.state)
    return r


def run(g):
    g.note("veh_session3: no-fly topograph ring (lab deploy D1)")
    rec = _RECORD
    pokes = {190: 8, 191: 0}
    pokes.update({int(k): v for k, v in B["spawn_record"].items()})
    V.reach_world_as(g, rec, scenario=SC, pokes=pokes, expect_world=9007, first=True)
    a = rec["arrival"]
    d0 = None if a["x"] is None else ((a["x"] - A_C[0]) ** 2 + (a["z"] - A_C[1]) ** 2) ** 0.5
    g.check(a["world"] == 9007 and a["vehicle"] == 8 and d0 is not None and d0 <= 0.5
            and a["y"] is not None and abs(a["y"] - B["slab_y"]) <= 0.05,
            "N0: the airship loaded at ring A's centre ON the lab slab (y 2.0; stock sea would read 0)",
            json.dumps({"arrival": a, "dist": d0}))
    if not (a["vehicle"] == 8 and d0 is not None and d0 <= 0.5):
        V.save(g, "veh_session3.json", rec)
        return
    g.shot("n0")
    climb = V.calibrate_climb(g, rec)
    if climb is None:
        g.check(False, "climb input reaches the airship", json.dumps(rec.get("climb_calibration")))
        V.save(g, "veh_session3.json", rec)
        return
    dive = "up" if climb == "down" else "down"
    V.plateau_y(g, dive)
    # N1 low
    V.tp(g, *A_C)
    n1 = throttle(g, A_C)
    rec["N1"] = {k: n1[k] for k in ("outcome", "radius", "end")}
    rec["N1_samples"] = n1["samples"]
    g.shot("n1-low-stall")
    g.check(n1["outcome"] == "stalled" and STOP_LO <= (n1["radius"] or 0) <= STOP_HI,
            "N1: at y 2.0 the airship stops at ring A's inner edge (topograph 15)",
            f"{n1['outcome']} at r {n1['radius']} (y {n1['end']['y']})")
    # N2 pushing + climb: push FIRST (the creep to the edge ends within ~1 s), only then add the climb
    V.settle3(g)
    g.hold("confirm", 200)
    g.wait_frames(70)
    st0 = g.state
    y0, r0 = st0.world_y, V.radial(*A_C)(st0)
    g.hold(climb, 40)
    g.wait_frames(46)
    st1 = g.state
    y1, r1 = st1.world_y, V.radial(*A_C)(st1)
    g.release("confirm")
    V.settle3(g)
    rec["N2"] = {"y_before": y0, "y_after": y1, "r_before": r0, "r_after": r1}
    g.check(None not in (y0, y1) and abs(y1 - y0) <= 0.01,
            "N2: pushing into the no-fly ring, the climb is refused too (same refused move)", f"{y0} -> {y1}")
    # N3 high
    V.tp(g, *A_C)
    up = V.plateau_y(g, climb, max_s=10.0)
    rec["N3_climb"] = {k: up[k] for k in ("y_start", "y_end")}
    n3 = throttle(g, A_C)
    rec["N3"] = {k: n3[k] for k in ("outcome", "radius", "end")}
    rec["N3_samples"] = n3["samples"]
    g.shot("n3-high-stall")
    g.check(up["y_end"] is not None and abs(up["y_end"] - V.CEILING) <= 0.004 and n3["outcome"] == "stalled"
            and STOP_LO <= (n3["radius"] or 0) <= STOP_HI,
            "N3: at the 42.1875 ceiling the airship stops at the same ring edge",
            f"y {up['y_end']}, {n3['outcome']} at r {n3['radius']}")
    # K1 control high
    V.tp(g, *B_C)
    k1 = throttle(g, B_C, done_r=20.0)
    rec["K1"] = {k: k1[k] for k in ("outcome", "radius", "end")}
    g.check((k1["radius"] or 0) >= 16.0, "K1: at the ceiling the airship crosses ring B (topograph 41, legal)",
            f"{k1['outcome']} at r {k1['radius']}")
    # K2 control low
    V.tp(g, *B_C)
    V.plateau_y(g, dive, max_s=10.0)
    k2 = throttle(g, B_C, done_r=20.0)
    rec["K2"] = {k: k2[k] for k in ("outcome", "radius", "end")}
    g.check((k2["radius"] or 0) >= 16.0 and k2["end"]["y"] is not None and k2["end"]["y"] < 3.0,
            "K2: at y 2.0 the airship crosses ring B", f"{k2['outcome']} at r {k2['radius']}, y {k2['end']['y']}")
    V.save(g, "veh_session3.json", rec)
