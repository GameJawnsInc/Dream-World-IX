"""Vehicle session 4 -- THE BOAT UNDER A SIDECAR-LESS RECLAIMED CELL (README rank 7, open hypothesis H1; latent defect
18). One launch per phase; $VEH_PHASE picks the phase and MUST match what the orchestrator deployed into the scratch
folder FF9CustomMap-lab (veh_PLAN.md section 5, deploys D2-D5):

    none     no deploy (baseline: (21,1) is open stock sea)
    flat6    world-reclaim --cells 21,1 --profile flat --height 6   --skip-mirror      (H1 proper)
    flat1.2  world-reclaim --cells 21,1 --profile flat --height 1.2 --skip-mirror      (control: below the ray origin)
    island   world-reclaim --cells 21,1 --profile island            --skip-mirror      (control: the kit default)
    cliff    world-reclaim --cells 21,1 --profile cliff             --skip-mirror      (exploratory, low confidence)

  DEFECT-18 RE-DRIVE (after the fix, 10a3758e: reclaim now ALSO writes hidden Sea1/3/4/5 stubs, so no Block[12][10]
  water rides under the land). Same deploy commands, kit at or after the fix; the lab then holds 5 files per cell.
    flat6-fixed   as flat6     REGISTERED (d18_predict.py -> out/d18_predict.json): both lanes STALL at the cell
    cliff-fixed   as cliff     edge, into -0.05 at heading 0 and at all 9 headings of the +-2 deg band (the sea-level
                               probe now MISSES inside the cell = the vehicle wall). Pre-fix the same simulator crossed
                               the cell on flat6 OPEN (123.81) and on both cliff lanes (123.54 / 118.87).

    py studies/terrain-malleability/ingame/veh_prep.py
    $env:VEH_PHASE = "flat6"; py tools/play.py studies/terrain-malleability/ingame/veh_session4.py --label veh-session4-flat6
    py studies/terrain-malleability/ingame/veh_post.py <run dir>

ROUTE: New Game -> field 6603 at ScenarioCounter 9500 (band 5990-10399, outside 9615-9790) -> [190] = 7, [191] = 0,
the boat record [74..82] = the OPEN lane start at y 0, facing byte 192 -> walk out. The cascade (key 35) loads WORLD03 =
9003; Main_Init spawns the Blue Narciss (entry 6) because SC >= 9400; its Init binds control because [190] == 7.

MECHANISM (ff9.cs:5543-5603, :5682-5727, :7296-7322; WMBlock.cs:137-212; WMPhysics.cs:6-47): each tick the boat probes
the next XZ with a NON-sky ray from its own y + 2.34375 (the hull rides at water - 0.703, ff9.cs:5489-5491, so the
origin is ~1.64 over open sea), takes the FIRST registered walk mesh with a hit and the first passing tri in buffer
order BELOW the origin (the 10-slot cache of this block tested first), and moves only onto topograph 53/54/57; else
it tries 7 slide angles each side (+rotation first = bearing - k*11.25, i.e. toward -z on a +x hull). A Terrain
override with no Donor.txt diverts the cell onto Block[12][10], whose Sea1/3/4/5 free-ride under it (consumption
C6/C7). Terrain registers first -- but a slab ABOVE the origin is never hit, so the probe falls through to the hidden
water.

REGISTERED PREDICTIONS (out/veh_prep.json["boat"]; the simulator runs the same rules over the same meshes, at heading
0 in "phases" and over the +-2 deg hull band the session accepts in "heading_scan" / "stock_control.heading_scan"):
  B0  world 9003, vehicle 7, the boat at the OPEN lane start (1324.37, -67.39) +-0.5, y = -0.703 +-0.03.
  B1  heading: holding "up" (forward, LY) from rest moves along bearing 0 (+x) +-3 deg (facing byte 192).
  C0  STOCK control (no deploy dependency): from (113.63, -582.39) at rest, +x: STALLS after 16.4 +-1.5u, stopped by
      stock topo-56 water (the stock coast grammar) -- the instrument's "blocked" calibration (band 16.37..17.40).
  per phase, two lanes from rest at x 1324.37 (19.63u west of the cell), +x; `into` = x_max - 1344; "unslid" = no
  sample 0.5u or more off the hull's own measured line:
             OPEN (z -67.39)                       RIM (z -89.39)
  none       into >= 30, unslid                    into >= 30, unslid
  flat6      into >= 30, unslid, y in cell          CONTACT with Block[12][10]'s hidden topo-56 islet rim, under the slab,
             -0.703 +-0.05 (it sails UNDER the      at into 18.5..21.5: a STALL there or a FIRST SLIDE there (scan:
             y-6 slab)                             contact 19.59..20.49 at all 9 headings; stall at 0/-1/-2 deg, slide
                                                   round the islet at -0.5/+0.5..+2 -- a step-phase knife edge, so
                                                   which of the two is recorded, not judged)
  flat1.2    STALL at into -1.0..+0.1               STALL at into -1.0..+0.1    (slab 1.2 < the 1.64 ray origin)
  island     STALL at into -1.0..+0.1               STALL at into -1.0..+0.1    (the sand ramp meets the waterline)
  cliff      (exploratory) simulated to TUNNEL the 0.5u-wide wall foot after a 45-deg slide -- sensitive to the last
             step's phase against the wall; recorded, not judged.
"""
import json
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import veh_lib as V                                   # noqa: E402

PHASE = os.environ.get("VEH_PHASE", "none")
PB = V.prep()["boat"]
SC = 9500
XB = PB["cell"][0] * 64.0
GOAL = 50.0
_RECORD: dict = {"phase": PHASE, "notes": []}

#   "pass"    reach the 50u goal with NO slide (no lateral offset >= 0.5u off the hull's own line) -- open water all along
#   "contact" [review] the RIM verdict: the hull meets Block[12][10]'s hidden islet rim inside the window -- it either
#             STALLS there or is first DEFLECTED (slid) there. Which of the two is a step-phase knife edge: the
#             registered heading_scan (out/veh_prep.json boat.heading_scan.rim.flat6) stalls at heading 0/-1/-2 and
#             slides past at -0.5/+0.5..+2, contact at into 19.59..20.49 every time. The old "stall at 19.75" claim
#             would have refuted H1 on a +0.5 deg hull. Only "neither" (no stall, no slide in the window) refutes it.
PRED = {
    "none":    {"open": ("pass", None), "rim": ("pass", None)},
    "flat6":   {"open": ("pass", None), "rim": ("contact", (18.5, 21.5))},
    "flat1.2": {"open": ("stall", (-1.0, 0.1)), "rim": ("stall", (-1.0, 0.1))},
    "island":  {"open": ("stall", (-1.0, 0.1)), "rim": ("stall", (-1.0, 0.1))},
    "cliff":   {"open": ("explore", None), "rim": ("explore", None)},
    "flat6-fixed": {"open": ("stall", (-1.0, 0.1)), "rim": ("stall", (-1.0, 0.1))},     # defect 18 fixed
    "cliff-fixed": {"open": ("stall", (-1.0, 0.1)), "rim": ("stall", (-1.0, 0.1))},
}


def drive(g, x0, z0, heading, goal=GOAL):
    V.tp(g, x0, z0)
    meas = V.along(x0, z0, 0.0)
    r = V.hold_until(g, ["up"], measure=meas, done=lambda s: (meas(s) or 0.0) >= goal, stall_s=1.0, start_s=3.0,
                     max_s=15.0)
    end = V.settle3(g)
    xs = [s["x"] for s in r["samples"] if s["x"] is not None] + ([end["x"]] if end["x"] is not None else [])
    r["end"] = end
    r["x_max"] = max(xs) if xs else None
    r["progress"] = None if r["x_max"] is None else r["x_max"] - x0
    r["into"] = None if r["x_max"] is None else r["x_max"] - XB
    r["y_in_cell"] = [s["y"] for s in r["samples"] if s["x"] is not None and s["x"] > XB and s["y"] is not None]
    # judged against the hull's MEASURED heading (B1 / hull_steer), so a +-2 deg hull is not a "slide"
    r["deflection"] = V.first_deflection(r["samples"] + [end], x0, z0, heading, XB)
    return r


def run(g):
    g.note(f"veh_session4: Blue Narciss and the sidecar-less reclaim, phase {PHASE}")
    rec = _RECORD
    pokes = {190: 7, 191: 0}
    pokes.update({int(k): v for k, v in PB["spawn"]["record"].items()})
    V.reach_world_as(g, rec, scenario=SC, pokes=pokes, expect_world=9003, first=True)
    a = rec["arrival"]
    sx, sz = PB["spawn"]["world"]
    d0 = None if a["x"] is None else math.hypot(a["x"] - sx, a["z"] - sz)
    g.check(a["world"] == 9003 and a["vehicle"] == 7 and d0 is not None and d0 <= 0.5
            and a["y"] is not None and abs(a["y"] + 0.703) <= 0.03,
            "B0: 9003 loaded with control BOUND TO THE BOAT at the poked record, riding at water - 0.703",
            json.dumps({"arrival": a, "dist": d0}))
    if not (a["vehicle"] == 7 and d0 is not None and d0 <= 0.5):
        V.save(g, "veh_session4.json", rec)
        return
    g.shot("b0")
    # B1 -- heading from rest, 25u west of the lane start (open stock sea in (20,1))
    cal = (sx - 25.0, sz)
    hd, s0, s1 = V.hull_heading(g, cal)
    rec["B1"] = {"from": s0, "to": s1, "heading": hd}
    g.check(hd is not None and abs(V.angdiff(hd, 0.0)) <= 3.0, "B1: 'up' drives the hull along bearing 0 (+x)",
            f"heading {hd}")
    if hd is None or abs(V.angdiff(hd, 0.0)) > 2.0:
        hd = V.hull_steer(g, cal, 0.0, rec)                # not a judged check: makes the lanes drivable anyway
        rec["notes"].append(f"hull steered to {hd} (facing byte 192 did not give +x within 2 deg)")
        if hd is None or abs(V.angdiff(hd, 0.0)) > 2.0:
            V.save(g, "veh_session4.json", rec)
            return
    rec["hull_heading"] = hd
    # C0 -- stock control (registered over the +-2 deg band: boat.stock_control.heading_scan, 16.37..17.40)
    ctl = PB["stock_control"]
    c0 = drive(g, *ctl["start"], hd, goal=30.0)
    rec["C0"] = {k: c0[k] for k in ("outcome", "progress", "end", "deflection")}
    g.check(c0["outcome"] == "stalled" and abs((c0["progress"] or 0) - ctl["progress"]) <= 1.5,
            "C0: the instrument -- the boat stalls where the simulator says stock topo-56 water stops it",
            f"{c0['outcome']} after {c0['progress']}u (sim {ctl['progress']}u, band "
            f"{ctl.get('heading_scan', {}).get('progress')})")
    # the two lanes
    for lane in ("open", "rim"):
        x0, z0 = PB["lanes"][lane]["start"]
        r = drive(g, x0, z0, hd)
        rec[lane] = {k: r[k] for k in ("outcome", "progress", "into", "x_max", "end", "deflection")}
        rec[lane + "_samples"] = r["samples"]
        g.shot(f"{lane}-{PHASE}")
        kind, win = PRED[PHASE][lane]
        sim = PB["phases"].get(PHASE, {}).get(lane) if PHASE != "none" else None
        scan = PB.get("heading_scan", {}).get(lane, {}).get(PHASE)
        dfl = r["deflection"]
        detail = json.dumps({"outcome": r["outcome"], "into": r["into"], "deflection": dfl, "hull": hd,
                             "sim": None if not sim else {k: sim[k] for k in ("into_cell", "stalled", "slides")},
                             "scan": None if not scan else {k: scan[k] for k in ("any_stalled", "all_contact",
                                                                                 "contact_into", "max_slides")},
                             "y_in_cell": [min(r["y_in_cell"]), max(r["y_in_cell"])] if r["y_in_cell"] else []})
        if kind == "pass":
            ys = r["y_in_cell"]
            ok = (r["outcome"] == "done" and (r["into"] or 0) >= 30.0 and dfl is None
                  and (PHASE == "none" or (ys and all(abs(y + 0.703) <= 0.05 for y in ys))))
            g.check(ok, f"{lane.upper()} lane ({PHASE}): the boat crosses into the cell at water level, unslid",
                    detail)
        elif kind == "contact":
            stalled_in = r["outcome"] == "stalled" and win[0] <= (r["into"] if r["into"] is not None else -99) <= win[1]
            slid_in = dfl is not None and win[0] <= dfl["into"] <= win[1]
            rec[lane]["contact"] = "stall" if stalled_in else ("slide" if slid_in else None)
            g.check(stalled_in or slid_in,
                    f"{lane.upper()} lane ({PHASE}): the hull meets the hidden islet rim at into {win} "
                    f"(a stall there, or a first slide there -- which one is a step-phase knife edge, not judged)",
                    detail)
        elif kind == "stall":
            ok = r["outcome"] == "stalled" and win[0] <= (r["into"] if r["into"] is not None else -99) <= win[1]
            g.check(ok, f"{lane.upper()} lane ({PHASE}): the boat stalls at into {win}", detail)
        else:
            rec["notes"].append(f"{lane} ({PHASE}) exploratory: {detail}")
    V.save(g, "veh_session4.json", rec)
