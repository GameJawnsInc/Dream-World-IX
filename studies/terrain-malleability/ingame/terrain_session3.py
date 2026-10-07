"""In-game session 3 -- the DISC-4 crescent ridge (README section 7.1 rank 11, disc4 D4-09), NO DEPLOY.

Disc 4 without the ~ menu: a field round trip at scenario >= 11090 loads the world on disc 4 (w_frameDisc). The
ridge = disc4/out/rock_ribbons.json[0], centroid (1144.4, -395.2) near the Earth Shrine, long axis 131.4 deg,
rise mean 1.66 / max 3.04, crest topo 49 over |s| <= 1.5u of the crossing line; both sides topo 17 (disc4_prep.py).

    py studies/terrain-malleability/ingame/disc4_prep.py
    py tools/play.py studies/terrain-malleability/ingame/terrain_session3.py --label terrain-session3

REGISTERED PREDICTIONS:
  F3a disc 1, scenario 0: the two Cleyra (14,12) points read FORM-1 ground (3.471 / 2.923)
  F3b poke gEventGlobal[0..1] = 10650 ON the world map: the published counter reads 10650 at once, but the Cleyra
      ground stays FORM 1 -- w_frameScenePtr is copied from ushort_gEventGlobal(0) only at world init (ff9.cs:3652)
      and every place condition reads that copy (forms F3: decided once per world load)
  R0  the world loads with the scenario counter >= 11090 (disc 4) -- precondition
  R1  side A -> B along the perpendicular (bearing 221.4): BLOCKED at the ridge foot, progress ~5.5u of 14
      (the crest starts at s = -1.5; A sits at s = -7); the height never rises more than ~1.5u above side A
  R2  side B -> A (hold "down" on the same yaw = bearing 41.4): BLOCKED symmetrically
  R3  alongside on side A (parallel to the axis, 7u off the crest): walks >= 6u, unblocked
  LOOK  frames from side A facing the ridge, for the owner to name the feature (Iifa roots?)
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
PREP = json.loads((HERE / "out" / "disc4_prep.json").read_text(encoding="utf-8"))["ridges"][0]
CLEYRA = json.loads((HERE / "out" / "forms_stock_prep.json").read_text(encoding="utf-8"))["Cleyra (14,12)"]["picks"][:2]

LANDING_FIELD = 6603
EXIT_AT = (400.0, -1400.0)
DOOR = [[285, -352], [875, -460], [424, -2944], [-166, -2836]]
LANDING = (68.0, -444.0)
PERP = PREP["perp_bearing_deg"]
AXIS = PREP["axis_bearing_deg"]
A = tuple(PREP["sideA"])
B = tuple(PREP["sideB"])
DISC4_SCENARIO = 11100

_RECORD: dict = {"notes": []}


def here(g) -> dict:
    st = g.state
    return {"x": st.world_x, "z": st.world_z, "y": st.world_y, "world": st.world_id, "ui": st.ui_state,
            "scenario": st.scenario}


def progress(start, now, bearing):
    b = math.radians(bearing)
    return (now[0] - start[0]) * math.cos(b) + (now[1] - start[1]) * math.sin(b)


def manual_walk(g, button, bearing, distance, burst=8, max_bursts=30, absolute=False):
    """Hold `button` in bursts, scoring progress ALONG `bearing` (a wall slide keeps him moving, so distance moved
    cannot see a block). Stops when reached, or when two consecutive bursts make < 0.3u of progress."""
    st = g.state
    start = (st.world_x, st.world_z)
    trace = [here(g)]
    stalls = 0
    last = 0.0
    for _ in range(max_bursts):
        g.hold(button, burst)
        g.wait_frames(burst + 4)
        if not g.state.on_world:
            return {"outcome": "left_world", "trace": trace}
        st = g.state
        trace.append(here(g))
        p = progress(start, (st.world_x, st.world_z), bearing)
        if absolute:
            p = abs(p)
        if p >= distance:
            return {"outcome": "reached", "progress": p, "trace": trace}
        stalls = stalls + 1 if p - last < 0.3 else 0
        last = p
        if stalls >= 2:
            return {"outcome": "blocked", "progress": p, "trace": trace}
    return {"outcome": "timeout", "progress": last, "trace": trace}


def _walk_out(g):
    g.wait_frames(45)
    g.calibrate_axes(hazards=[DOOR])
    g.walk_to(*EXIT_AT, strict=False, halt_on_transition=True)
    g.wait_world(timeout=90)
    g.world_settle()


def _cleyra(g):
    rows = []
    for p in CLEYRA:
        g.teleport(*p["world"])
        g.world_settle()
        g.wait_frames(20)
        st = g.state
        rows.append({"point": p["world"], "y": st.world_y, "y_form1": p["y_form1"], "y_form2": p["y_form2"],
                     "scenario": st.scenario})
    return rows


def run(g):
    g.note("terrain_session3: the disc-4 crescent ridge, no deploy")
    g.newgame()
    g.warp(LANDING_FIELD)
    _walk_out(g)
    f3 = _RECORD["F3"] = {"before": _cleyra(g)}
    g.check(all(abs(r["y"] - r["y_form1"]) <= 0.15 for r in f3["before"]),
            "F3a: scenario 0 -- Cleyra reads FORM-1 ground", json.dumps(f3["before"]))
    g.poke(0, 10650 & 0xFF)
    g.poke(1, 10650 >> 8)
    g.wait_frames(30)
    f3["published_scenario"] = g.state.scenario
    f3["after_poke"] = _cleyra(g)
    g.check(f3["published_scenario"] == 10650, "F3b precondition: the poked counter publishes 10650",
            f"{f3['published_scenario']}")
    g.check(all(abs(r["y"] - r["y_form1"]) <= 0.15 for r in f3["after_poke"]),
            "F3b: a mid-visit scenario change leaves Cleyra on FORM 1 until the world reloads",
            json.dumps(f3["after_poke"]))
    g.world_warp(LANDING_FIELD, scenario=DISC4_SCENARIO)
    g.wait_frames(45)
    g.calibrate_axes(hazards=[DOOR])
    g.walk_to(*EXIT_AT, strict=False, halt_on_transition=True)
    g.wait_world(timeout=90)
    g.world_settle()
    st = g.state
    _RECORD["start"] = here(g)
    print(f"[t3] world {st.world_id} scenario {st.scenario} at {st.world_pos}")
    g.check(st.scenario >= 11090, "R0: the world loaded at scenario >= 11090 (disc 4)", f"scenario {st.scenario}")
    face = g.world_face(PERP, home=LANDING, tolerance=3.0)
    _RECORD["face"] = {k: face.get(k) for k in ("heading", "error", "speed")}

    # LOOK + R1: A -> B
    g.teleport(*A)
    g.world_settle()
    g.wait_frames(60)
    g.shot("ridge-from-A")
    yA = g.state.world_y
    w1 = g.world_approach(PERP, 14.0, speed=face.get("speed"), burst_frames=8)
    _RECORD["A_to_B"] = {"outcome": w1["outcome"], "progress": w1.get("progress"), "y_A": yA,
                         "y_max": w1.get("y_max"), "trace": w1.get("trace")}
    g.shot("ridge-A-stop")
    if w1["outcome"] == "left_world":
        _RECORD["notes"].append("battle during A->B")
    else:
        g.check(w1["outcome"] == "blocked" and 3.0 <= (w1.get("progress") or 0) <= 7.5,
                "R1: walking A -> B the ridge blocks at its foot",
                f"{w1['outcome']} after {w1.get('progress')}u of 14 (foot expected ~5.5u)")

    # R2: B -> A on the same yaw, holding down
    if g.state.on_world:
        g.teleport(*B)
        g.world_settle()
        g.wait_frames(30)
        w2 = manual_walk(g, "down", (PERP + 180.0) % 360.0, 14.0)
        _RECORD["B_to_A"] = {k: w2.get(k) for k in ("outcome", "progress", "trace")}
        g.shot("ridge-B-stop")
        if w2["outcome"] != "left_world":
            g.check(w2["outcome"] == "blocked" and 3.0 <= (w2.get("progress") or 0) <= 7.5,
                    "R2: walking B -> A the ridge blocks at its foot",
                    f"{w2['outcome']} after {w2.get('progress')}u of 14")

    # R3: alongside, side A, along the axis (left or right of the faced yaw -- whichever runs parallel)
    if g.state.on_world:
        best = None
        for btn in ("left", "right"):
            g.teleport(*A)
            g.world_settle()
            g.wait_frames(20)
            st0 = g.state
            w3 = manual_walk(g, btn, AXIS, 8.0, max_bursts=12, absolute=True)
            st1 = g.state
            dx, dz = st1.world_x - st0.world_x, st1.world_z - st0.world_z
            along = abs(dx * math.cos(math.radians(AXIS)) + dz * math.sin(math.radians(AXIS)))
            row = {"button": btn, "outcome": w3["outcome"], "moved_along_axis": round(along, 2),
                   "moved_total": round(math.hypot(dx, dz), 2)}
            _RECORD.setdefault("alongside", []).append(row)
            if best is None or row["moved_along_axis"] > best["moved_along_axis"]:
                best = row
        g.check(best is not None and best["moved_along_axis"] >= 6.0,
                "R3: alongside the ridge on side A he walks on (>= 6u parallel to the crest)", json.dumps(best))
    g.shot("99-done")
    try:
        (g.run_dir / "terrain_session3.json").write_text(json.dumps(_RECORD, indent=1, default=str), encoding="utf-8")
    except Exception as err:
        print(f"[t3] could not write the record: {err}")
