"""The comp20 rim walk under the harness -- rimwalk_take8.py's proven pieces, re-aimed at comp20.

comp20 was deployed 2026-10-06 in the horseshoe's place and passed the owner's in-game look (COMP20-BENCH.md
C4: "don't see any seams, stretching, or errors in general"). So every station is a CONTROL. This walk adds what
the eye cannot judge:
  -- THE FEET: at 12 stations round the rim (one per 30 deg), rock stops him at the contact, with no climb;
  -- the published world height matches the mesh lawn (the instrument check);
  -- THE SEAM: x 1490 -> 1536|0 -> 40 at two latitudes is one continuous flat walk;
  -- THE SAFE ROAD: six legs of open grass from the landing start no battle (the R3 stamp, re-run after the carve);
  -- look-only frames from the owner-look teleport and three more standpoints.
Stations: rimwalk_comp20_stations.py -> rimwalk_comp20.json (read-only, from the deployed mesh).

    py tools/play.py studies/overworld-topography/west-seam-continent/rimwalk_comp20.py
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
import sys                                                  # noqa: E402
sys.path.insert(0, str(HERE))
import rimwalk_take8 as RW                                  # noqa: E402  (the proven station walk + helpers)

PLAN = json.loads((HERE / "rimwalk_comp20.json").read_text(encoding="utf-8"))
LANDING = tuple(PLAN["landing"])


def run(g):
    g.note("rimwalk_comp20: comp20 on the west-seam continent under the harness")
    g.newgame()
    g.warp(RW.LANDING_FIELD)
    g.wait_frames(45)
    g.calibrate_axes(hazards=[RW.DOOR])
    g.shot("00-farshore")

    # ---- the walk-out: 6603's west door -> the continent ----
    g.walk_to(*RW.EXIT_AT, strict=False, halt_on_transition=True)
    g.wait_world(timeout=90)
    g.world_settle()
    st = g.state
    dx, dz = g.world_delta(LANDING, st.world_pos)
    g.check(math.hypot(dx, dz) <= 16.0, "6603's west door lands on the continent at the landing point",
            f"world {st.world_id} at {st.world_pos}, {math.hypot(dx, dz):.1f}u from {LANDING}")
    RW._frame(g, "01-landing")

    # ---- the 12 stations: every one owner-passed, so every one a control ----
    cal: dict = {}
    rows = []
    for i, s in enumerate(PLAN["stations"]):
        try:
            rows.append(RW._station(g, i + 2, s, cal))
        except Exception as err:
            g.check(False, f"station {s['contact']} could be walked", str(err))
            if not g.state.on_world:
                g.wait_world(timeout=60)
    y_ok = "y_err" in cal and abs(cal["y_err"]) <= RW.Y_CAL_TOL
    g.check(y_ok, "the published world height matches the terrain mesh on the lawn (instrument check)",
            f"first re-grounded height minus the mesh lawn: {cal.get('y_err')}")
    walked = [r for r in rows if r.get("outcome")]
    for r in walked:
        if r["rises"]:
            g.check(r["outcome"] == "blocked" and abs(r["stop_vs_contact"]) <= RW.CONTACT_TOL,
                    f"comp20 {r['tag']}: rock stops him at the contact",
                    f"{r['outcome']}, {r['stop_vs_contact']:+.1f}u vs the contact")
            if y_ok and r["rise"] is not None:
                g.check(r["rise"] <= RW.CLIMB_MAX, f"comp20 {r['tag']}: no climb up the face",
                        f"rose {r['rise']:.2f}u above the lawn (max {RW.CLIMB_MAX})")
        else:
            g.check(r["outcome"] == "reached", f"comp20 {r['tag']}: the flat end lets him walk on",
                    f"{r['outcome']}, {r['stop_vs_contact']:+.1f}u vs the contact")
    g.check(len(walked) >= 10, "at least 10 of the 12 rim stations were walked",
            f"{len(walked)} walked")

    # ---- look-only views ----
    for v in PLAN.get("views", []):
        try:
            g.teleport(*v["at"])
            g.world_face(v["bearing"], home=tuple(v["at"]), tolerance=4.0)
            RW._frame(g, f"view-{v['name']}")
        except Exception as err:
            print(f"[rim] view {v['name']} failed: {err}")
            if not g.state.on_world:
                g.wait_world(timeout=60)

    # ---- the seam ----
    for k, line in enumerate(PLAN["seam"]):
        z = line["z"]
        g.teleport(line["from_x"], z)
        face = g.world_face(0.0, home=(line["from_x"], z), tolerance=4.0)
        dist = g.world_delta((line["from_x"], z), (line["to_x"], z))[0]
        walk = g.world_approach(0.0, dist, speed=face["speed"], burst_frames=8)
        if walk["outcome"] == "left_world":
            RW._survive(g, f"the seam at z {z}")
            continue
        RW._frame(g, f"seam-{k}")
        ys = [r["y"] for r in walk["trace"] if r.get("y") is not None]
        crossed = [r for r in walk["trace"] if r.get("x") is not None and r["x"] < 200]
        g.check(walk["outcome"] == "reached" and bool(crossed), f"the x-seam at z {z:.0f} walks through as one piece",
                f"{walk['outcome']} after {walk['progress']:.1f}u of {dist:.1f}")
        if y_ok and ys:
            g.check(max(ys) - min(ys) <= 1.5, f"the x-seam at z {z:.0f} has no step",
                    f"height {min(ys):.2f}..{max(ys):.2f} along the crossing")

    # ---- the safe road ----
    run_ = PLAN["grass_run"]
    g.teleport(*run_["start"])
    battles = 0
    for leg in range(6):
        b = (run_["bearing"] + 180.0 * (leg % 2)) % 360.0
        here = g.state.world_pos
        face = g.world_face(b, home=here, tolerance=8.0)
        walk = g.world_approach(b, run_["length"] - 8.0, speed=face["speed"], burst_frames=12)
        if walk["outcome"] == "left_world":
            battles += 1
            RW._survive(g, f"the grass run, leg {leg}")
            g.teleport(*run_["start"])
    g.check(battles == 0, "six legs of open grass from the landing start no battle (the safe road)",
            f"{battles} battle(s) over ~{6 * (run_['length'] - 8):.0f}u")
    g.shot("99-done")
    try:
        (g.run_dir / "rimwalk_comp20.json").write_text(json.dumps({"calibration": cal, "stations": rows}, indent=1),
                                                       encoding="utf-8")
    except Exception as err:
        print(f"[rim] could not write the station record: {err}")
