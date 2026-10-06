"""The take-8 rim walk under the harness -- the FIRST overworld scenario (rung 0: driver only, no DLL).

What it can judge, and what it cannot:
  CAN   -- the walk-out: 6603's west door lands on the continent at (68, -444)  (and so proves the
           field -> world crossing and the teleport, neither run in-game before)
        -- checklist 4, THE FEET: at every foot station where the massif rises, rock must STOP him at
           the contact with no climb (take 3's "the cliff face is ... walkable"); where take 8 emits
           grass instead, he must walk on with no curb
        -- checklist 7, THE SEAM: x 1490 -> 1536|0 -> 40 is one continuous walk at two latitudes
        -- checklist 8, THE SAFE ROAD: a long open-grass walk from the landing starts no battle
  CANNOT -- whether the base LOOKS right (checklist 1-3): it brings back a frame from every station
           for the owner to judge, and judges nothing about the look itself.

CALIBRATION FIRST (the brief: calibrate the instrument before you judge with it). The four CONTROL
stations sit on faces the owner already passed. If the harness says one of those is climbable, the
instrument is wrong, not take 8 -- so the window verdicts are reported only beside the controls'.

    py studies/overworld-topography/west-seam-continent/rimwalk_stations.py     # first, read-only
    py tools/play.py studies/overworld-topography/west-seam-continent/rimwalk_take8.py
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = json.loads((HERE / "rimwalk_stations.json").read_text(encoding="utf-8"))

LANDING_FIELD = 6603                 # FARSHORE, FF9CustomMap-world
EXIT_AT = (400.0, -1400.0)           # inside the door quad, ~300u west (screen-left) of the spawn (900, -1400)
LANDING = tuple(PLAN["landing"])     # the door's arrive point
OVERSHOOT = 24.0                     # how far past the contact a station walk is SENT
CONTACT_TOL = 6.0                    # a stop within this of the contact is "stopped at the contact"
CLIMB_MAX = 2.0                      # a rise above the lawn beyond this is climbing the face
CURB_MAX = 1.0                       # a grass station: any step up beyond this is a curb
Y_CAL_TOL = 0.75                     # published world height vs the mesh's lawn height
CAMERA_SETTLE = 30                   # frames: the world camera eases after a teleport (SmoothFrameUpdater_World)


def _frame(g, name: str) -> None:
    g.wait_frames(CAMERA_SETTLE)
    g.shot(name)


def _survive(g, where: str) -> None:
    """A battle mid-walk (the walk returned left_world): record it, end it, get back on the map."""
    st = g.state
    g.check(False, f"no battle starts at {where}", f"ui_state {st.ui_state} at {st.world_pos}")
    try:
        g.wait_battle(timeout=30)
        if not g.flee(timeout=90):
            g.fight()
        g.leave_battle(timeout=120)
    except Exception as err:                          # a failed escape must not hide the finding
        print(f"[rim] leaving the battle at {where} failed: {err}")
    g.wait_world(timeout=60)


def _station(g, i: int, s: dict, cal: dict) -> dict:
    kind, (cx, cz), b = s["kind"], s["contact"], s["bearing"]
    ax, az = s["approach"]
    tag = f"{i:02d}-{kind}"
    g.teleport(ax, az)
    face = g.world_face(b, home=(ax, az), tolerance=5.0)
    _frame(g, f"{tag}-approach")
    walk = g.world_approach(b, s["approach_d"] + OVERSHOOT, speed=face["speed"], burst_frames=8)
    if walk["outcome"] == "left_world":
        _survive(g, f"station {tag}")
        return {"tag": tag, "walk": walk, "face": face}
    _frame(g, f"{tag}-contact")
    lawn = s["lawn_y"]
    first = next((r for r in walk["trace"][1:] if r.get("y") is not None), None)
    if first is not None and "y_err" not in cal:
        cal["y_err"] = first["y"] - lawn                 # the first re-grounded height, on the flat lawn
    stop = walk["progress"] - s["approach_d"]          # + = past the contact, - = short of it
    rise = (walk["y_max"] - lawn) if walk["y_max"] is not None else None
    row = {"tag": tag, "kind": kind, "rises": s["rises"], "contact": s["contact"], "bearing": b,
           "outcome": walk["outcome"], "stop_vs_contact": round(stop, 2),
           "rise": None if rise is None else round(rise, 2), "face_error": face["error"],
           "trace": walk["trace"]}
    print(f"[rim] {tag} {'RISES' if s['rises'] else 'flat '} ({cx:.1f},{cz:.1f}) bearing {b:5.1f}: "
          f"{walk['outcome']}, stop {stop:+.1f}u vs contact, rise {row['rise']}")
    return row


def run(g):
    g.note("rimwalk_take8: the take-8 west-seam massif under the harness")
    g.newgame()
    g.warp(LANDING_FIELD)
    g.wait_frames(45)
    g.calibrate_axes()
    g.shot("00-farshore")

    # ---- the walk-out: field -> world (never run in-game by the harness before) ----
    g.walk_to(*EXIT_AT, strict=False, halt_on_transition=True)
    st = g.wait_world(timeout=90)
    g.world_settle()
    st = g.state
    dx, dz = g.world_delta(LANDING, st.world_pos)
    g.check(math.hypot(dx, dz) <= 16.0, "6603's west door lands on the continent at the landing point",
            f"world {st.world_id} at {st.world_pos}, {math.hypot(dx, dz):.1f}u from {LANDING}")
    _frame(g, "01-landing")
    print(f"[rim] on the world map: id {st.world_id} at {st.world_pos} y {st.world_y}")

    # ---- the stations: controls FIRST, so the instrument is calibrated before the window is judged ----
    cal: dict = {}
    rows = []
    order = ([s for s in PLAN["stations"] if s["kind"] == "control"]
             + [s for s in PLAN["stations"] if s["kind"] == "window"])
    for i, s in enumerate(order):
        if s["approach"] is None:
            print(f"[rim] skip {s['kind']} {s['contact']}: no clean lawn behind it (prep)")
            continue
        try:
            rows.append(_station(g, i + 2, s, cal))
        except Exception as err:
            g.check(False, f"station {s['kind']} {s['contact']} could be walked", str(err))
            if not g.state.on_world:
                g.wait_world(timeout=60)

    y_ok = "y_err" in cal and abs(cal["y_err"]) <= Y_CAL_TOL
    g.check(y_ok, "the published world height matches the terrain mesh on the lawn (instrument check)",
            f"first re-grounded height minus the mesh lawn: {cal.get('y_err')}")
    controls = [r for r in rows if r.get("kind") == "control" and r.get("outcome")]
    ctl_ok = bool(controls) and all(r["outcome"] == "blocked" and abs(r["stop_vs_contact"]) <= CONTACT_TOL
                                    for r in controls)
    g.check(ctl_ok, "the owner-passed control faces read as blocking (instrument check)",
            "; ".join(f"{r['tag']} {r['outcome']} {r['stop_vs_contact']:+.1f}u" for r in controls))
    for r in rows:
        if r.get("kind") != "window" or not r.get("outcome"):
            continue
        if r["rises"]:
            g.check(r["outcome"] == "blocked" and abs(r["stop_vs_contact"]) <= CONTACT_TOL,
                    f"take 8 {r['tag']}: rock stops him at the contact",
                    f"{r['outcome']}, {r['stop_vs_contact']:+.1f}u vs the contact")
            if y_ok and r["rise"] is not None:
                g.check(r["rise"] <= CLIMB_MAX, f"take 8 {r['tag']}: no climb up the face",
                        f"rose {r['rise']:.2f}u above the lawn (max {CLIMB_MAX})")
        else:
            g.check(r["outcome"] == "reached", f"take 8 {r['tag']}: the flat end lets him walk on",
                    f"{r['outcome']}, {r['stop_vs_contact']:+.1f}u vs the contact")
            if y_ok and r["rise"] is not None:
                g.check(r["rise"] <= CURB_MAX, f"take 8 {r['tag']}: no curb on the flat end",
                        f"rose {r['rise']:.2f}u above the lawn (max {CURB_MAX})")

    # ---- checklist 7: the seam ----
    for k, line in enumerate(PLAN["seam"]):
        z = line["z"]
        g.teleport(line["from_x"], z)
        face = g.world_face(0.0, home=(line["from_x"], z), tolerance=4.0)
        dist = g.world_delta((line["from_x"], z), (line["to_x"], z))[0]
        walk = g.world_approach(0.0, dist, speed=face["speed"], burst_frames=8)
        if walk["outcome"] == "left_world":
            _survive(g, f"the seam at z {z}")
            continue
        _frame(g, f"seam-{k}")
        ys = [r["y"] for r in walk["trace"] if r.get("y") is not None]
        crossed = [r for r in walk["trace"] if r.get("x") is not None and r["x"] < 200]
        g.check(walk["outcome"] == "reached" and bool(crossed),
                f"the x-seam at z {z:.0f} walks through as one piece",
                f"{walk['outcome']} after {walk['progress']:.1f}u of {dist:.1f}, now at "
                f"({walk['trace'][-1]['x']:.1f}, {walk['trace'][-1]['z']:.1f})")
        if y_ok and ys:
            g.check(max(ys) - min(ys) <= 1.5, f"the x-seam at z {z:.0f} has no step",
                    f"height {min(ys):.2f}..{max(ys):.2f} along the crossing")

    # ---- checklist 8: the safe road ----
    run_ = PLAN["grass_run"]
    g.teleport(*run_["start"])
    battles = 0
    for leg in range(6):                               # three round trips of the run
        b = (run_["bearing"] + 180.0 * (leg % 2)) % 360.0
        here = g.state.world_pos
        face = g.world_face(b, home=here, tolerance=8.0)
        walk = g.world_approach(b, run_["length"] - 8.0, speed=face["speed"], burst_frames=12)
        if walk["outcome"] == "left_world":
            battles += 1
            _survive(g, f"the grass run, leg {leg}")
            g.teleport(*run_["start"])
    g.check(battles == 0, "six legs of open grass from the landing start no battle (the safe road)",
            f"{battles} battle(s) over ~{6 * (run_['length'] - 8):.0f}u")
    g.shot("99-done")

    try:
        dest = g.run_dir / "rimwalk.json"
        dest.write_text(json.dumps({"calibration": cal, "stations": rows}, indent=1), encoding="utf-8")
        print(f"[rim] wrote {dest}")
    except Exception as err:
        print(f"[rim] could not write the station record: {err}")
