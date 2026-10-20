"""`world-river` IN GAME (PLAN.md rung 4): cluster C's river, its bridge, its cove and the island in it, carried onto a
kit island on the open ocean across the world's seam, ONE launch.

The lab FF9CustomMap-lab sits first in FolderNames for this run (lab_install.py) and holds the composition on cells
(23,12-14), (0,11-15), (1,11-14) (lab_build.py), with the mist forced off. Two stages:
  FOOT  New Game -> bench 6603 -> the disc-1 world, encounters off; then
        R1 teleport onto each probe (the kit's lawn, the carried island, the carried bridge deck) and read the height;
        VIEWS bay / river / join_E / join_W / channel_deck / source: teleport home, face, two stills 60 frames apart
        (the water animates; the channel sits ~2.8u under the lawn, so only the last two show its water);
        R2 the BANK walk straight at the stream, R3 the BRIDGE walk along the deck, R5 the walk along each JOIN's
        cliff top across its column.
  BOAT  a world -> 6603 round trip at ScenarioCounter 9500 with the boat record poked onto the kit's open sea outside
        the cove (veh_session4's route: WORLD03 spawns the Blue Narciss and binds control to it, [190] = 7); steer the
        hull at the cove's beach and hold forward until it stops (R4); stills at the start and at the end.
REGISTERED PREDICTIONS (lab_prep.py, out/lab/prep.json, from the lab's own bytes by the engine's rules):
  R1 each probe height within 0.15;  R2 the bank walk stops within 1.5u of the simulated stop, never below y 2;
  R3 the bridge walk reaches the far bank;  R4 the boat stops within 3u of the simulated stop, in the cove;
  R5 each join walk never drops (min y >= 2.5) and stops within 1.5u of the simulation.
  Owner: the bay reads as stock; the river and the stream animate; both joins read as one cliff.
RUN:  py studies/terrain-malleability/watercarry/lab_install.py install
      py tools/play.py studies/terrain-malleability/watercarry/lab_session.py --label world-river
      py studies/terrain-malleability/watercarry/lab_install.py uninstall <run dir>
RIVER_STAGES=foot (or boat) runs one stage; RIVER_ITEMS=channel_deck,source runs only those foot views/walks.
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools"))
sys.path.insert(0, str(HERE.parent / "ingame"))
from harness import HarnessError                      # noqa: E402
import veh_lib as V                                   # noqa: E402  (the 6603 route out to the world, the hull steer)

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
LAB_NAME = "FF9CustomMap-lab"
LAB = GAME / LAB_NAME
SRC = HERE / "out" / "lab"
PREP = json.loads((SRC / "prep.json").read_text(encoding="utf-8"))
BUILD = json.loads((SRC / "build.json").read_text(encoding="utf-8"))
STAGES = tuple(os.environ.get("RIVER_STAGES", "foot,boat").split(","))
#: RIVER_ITEMS=name,name runs only those views/walks of the foot stage (the probes always run: they prove the install)
ITEMS = set(filter(None, os.environ.get("RIVER_ITEMS", "").split(",")))
SETTLE, APART = 180, 60
TOL_Y, TOL_STOP, TOL_BOAT, TOL_FACE = 0.15, 1.5, 3.0, 6.0
#: where every facing is done: world_face measures the heading by WALKING ~30u, and near a cliff or a bank that probe
#: slides along the wall and reads as a camera that will not turn (round 1: the E-join home on the narrow headland).
#: The kit's open lawn has 35u+ of ground every way; the camera's yaw survives the teleport to the real start.
FACE_AT = next(p["world"] for p in PREP["probes"] if p["name"] == "kit_lawn")
_RECORD: dict = {"lane": "world-river", "prep": PREP, "build": BUILD, "stages": []}


def record_bytes(x, y, z, face, base):
    """gEventGlobal bytes for a vehicle record at ``base`` (74 = boat): X int24, Y int16, Z int24, facing byte
    (ingame/veh_prep.py's, the layout every dispatcher's MoveInstantXZY/TurnInstant reads)."""
    def le(v, n):
        v = int(round(v)) & ((1 << (8 * n)) - 1)
        return [(v >> (8 * k)) & 0xFF for k in range(n)]
    b = le(x * 256, 3) + le(y * 256, 2) + le(z * 256, 3) + [int(face) & 0xFF]
    return {str(base + k): v for k, v in enumerate(b)}


def _save(g):
    try:
        (g.run_dir / "river_session.json").write_text(json.dumps(_RECORD, indent=1, default=str), encoding="utf-8")
    except Exception as err:                                            # noqa: BLE001
        print(f"[river] could not write the record: {err}")


def preflight() -> list:
    ini = (GAME / "Memoria.ini").read_text(encoding="utf-8", errors="replace")
    m = re.search(r'^\s*FolderNames\s*=\s*(.+)$', ini, re.M)
    folders = re.findall(r'"([^"]*)"', m.group(1)) if m else []
    problems = []
    if not folders or folders[0] != LAB_NAME:
        problems.append(f"{LAB_NAME} must be FIRST in FolderNames: {folders}")
    src = sorted(p.relative_to(SRC / LAB_NAME).as_posix() for p in (SRC / LAB_NAME).rglob("*") if p.is_file())
    have = sorted(p.relative_to(LAB).as_posix() for p in LAB.rglob("*") if p.is_file()) if LAB.is_dir() else []
    if src != have:
        problems.append(f"the installed lab differs from the build ({len(have)} files vs {len(src)})")
    for bx, by in BUILD["cells"]:
        for f in folders[1:]:
            hits = list((GAME / f / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / f"r{by}").glob(
                f"Block[[]{bx}[]][[]{by}[]]*"))
            if hits:
                problems.append(f"{f} also overrides cell ({bx},{by}): {[h.name for h in hits][:3]}")
    if not any(re.search(r"^FieldScene 6603 ", (GAME / f / "DictionaryPatch.txt").read_text(encoding="utf-8",
                                                                                         errors="replace"), re.M)
               for f in folders if (GAME / f / "DictionaryPatch.txt").is_file()):
        problems.append("bench 6603 (the route to the world) is not registered")
    return problems


def probe(g, p: dict, srec: dict):
    g.teleport(*p["world"])
    at = V.settle3(g)
    srec["probes"][p["name"]] = {"want": p["y"], "at": at}
    g.check(at["y"] is not None and abs(at["y"] - p["y"]) <= TOL_Y,
            f"R1 {p['name']}: stands on the lab's ground ({p['part']} topo {p['topo']}, y {p['y']})", f"y={at['y']}")


def face(g, bearing: float, home, srec: dict, tag: str) -> dict:
    try:
        f = g.world_face(bearing, home=tuple(home))
    except HarnessError as err:                     # one retry: the rate it learned on the way is kept
        srec.setdefault("face_retries", []).append(f"{tag}: {str(err)[:300]}")
        f = g.world_face(bearing, home=tuple(home))
    return f


def look(g, v: dict, srec: dict):
    home = v["home"]
    g.teleport(*FACE_AT)
    f = face(g, v["bearing_deg"], FACE_AT, srec, v["name"])
    g.teleport(*home)
    g.wait_frames(SETTLE)
    a = g.shot(f"view-{v['name']}-a")
    g.wait_frames(APART)
    b = g.shot(f"view-{v['name']}-b")
    at = V.settle3(g)
    diff = None
    try:
        from PIL import Image, ImageChops
        im = ImageChops.difference(Image.open(a).convert("L"), Image.open(b).convert("L"))
        hist = im.histogram()
        diff = round(sum(i * n for i, n in enumerate(hist)) / max(1, sum(hist)), 3)
    except Exception as err:                                            # noqa: BLE001
        srec.setdefault("notes", []).append(f"{v['name']}: still diff failed {err}")
    srec["views"][v["name"]] = {"home": home, "face": {k: f[k] for k in ("heading", "error")}, "at": at,
                                "shots": [a.name, b.name], "frame_diff": diff}
    g.check(abs(f["error"]) <= TOL_FACE, f"view {v['name']}: faced", f"heading {f['heading']:.1f}")
    g.check(at["y"] is not None and abs(at["y"] - v["ground_y"]) <= TOL_Y, f"view {v['name']}: home height",
            f"y={at['y']} want {v['ground_y']}")


def walk(g, w: dict, srec: dict):
    start, bearing, sim = w["start"], w["bearing_deg"], w["sim"]
    g.teleport(*FACE_AT)
    face(g, bearing, FACE_AT, srec, w["name"])
    g.teleport(*start)
    s0 = V.settle3(g)
    r = g.world_approach(bearing, w["dist"])
    ys = [p["y"] for p in r["trace"] if p.get("y") is not None]
    end = V.settle3(g)
    rec = {"start": s0, "outcome": r["outcome"], "progress": round(r["progress"], 2), "min_y": min(ys) if ys else None,
           "samples": len(ys), "end": end, "sim": {k: sim[k] for k in ("progress", "reached", "min_y", "end")}}
    srec["walks"][w["name"]] = rec
    n = w["name"]
    if n == "bridge":
        g.check(r["progress"] >= w["dist"] - TOL_STOP and ys and min(ys) > 2.5,
                "R3 the bridge carries the walk across the channel to the far bank",
                f"{r['outcome']} at {r['progress']:.2f}u of {w['dist']:.2f}; min y {rec['min_y']}")
    elif n == "bank":
        g.check(abs(r["progress"] - sim["progress"]) <= TOL_STOP and ys and min(ys) > 2.0,
                "R2 a bank holds: the walk at the stream stops where the simulation stops it, never in the water",
                f"{r['outcome']} at {r['progress']:.2f}u (sim {sim['progress']}); min y {rec['min_y']}")
    else:
        stop_ok = (r["progress"] >= w["dist"] - TOL_STOP) if sim["reached"] else \
            abs(r["progress"] - sim["progress"]) <= TOL_STOP
        g.check(ys and min(ys) >= 2.5 and stop_ok,
                f"R5 {n}: the cliff top across the join column never drops, and stops as simulated",
                f"{r['outcome']} at {r['progress']:.2f}u (sim {sim['progress']}, reached {sim['reached']}); "
                f"min y {rec['min_y']}")


def stage_foot(g, srec: dict, first: bool):
    V.reach_world_as(g, srec, scenario=0, pokes={}, expect_world=0, first=first)
    g.no_encounters()
    g.check(g.state.on_world, "foot: on the world map", json.dumps(srec.get("arrival")))
    arr = srec.get("arrival") or V.here(g)
    try:
        srec["warmup"] = {k: v for k, v in g.world_face(0.0, home=(arr["x"], arr["z"])).items()
                          if k in ("heading", "error", "rate")}
    except HarnessError as err:
        srec["warmup"] = {"error": str(err)[:300]}
    srec["probes"], srec["views"], srec["walks"] = {}, {}, {}
    for p in PREP["probes"]:
        probe(g, p, srec)
    for fn, items in ((look, PREP["views"]), (walk, PREP["walks"])):
        for it in items:                          # each one on its own: a failure must not cost the rest
            if ITEMS and it["name"] not in ITEMS:
                continue
            try:
                fn(g, it, srec)
            except HarnessError as err:
                srec.setdefault("item_errors", {})[it["name"]] = str(err)[:400]
                g.check(False, f"{it['name']}: completed", str(err)[:200])
            _save(g)


def stage_boat(g, srec: dict, first: bool):
    b = PREP["boat"]
    x, z = b["start"]
    pokes = {190: 7, 191: 0}
    pokes.update({int(k): v for k, v in record_bytes(x, 0.0, z, 192, 74).items()})
    V.reach_world_as(g, srec, scenario=9500, pokes=pokes, expect_world=9003, first=first)
    g.no_encounters()
    at = V.settle3(g)
    srec["spawn"] = at
    g.check(at["vehicle"] == 7 and at["x"] is not None and math.hypot(at["x"] - x, at["z"] - z) <= 0.5,
            "R4 the Blue Narciss spawns on the kit's open sea outside the cove", json.dumps(at))
    hd = V.hull_steer(g, (x, z), b["bearing_deg"], srec)
    srec["hull_heading"] = hd
    s0 = V.tp(g, x, z)
    g.wait_frames(SETTLE)
    shot0 = g.shot("boat-start")
    ux, uz = math.cos(math.radians(b["bearing_deg"])), math.sin(math.radians(b["bearing_deg"]))

    def prog(st):
        return None if st.world_x is None else (st.world_x - x) * ux + (st.world_z - z) * uz
    r = V.hold_until(g, ["up"], measure=prog, stall_s=1.5, start_s=3.0, max_s=60.0)
    end = V.settle3(g)
    g.wait_frames(SETTLE // 2)
    shot1 = g.shot("boat-end")
    p = None if end["x"] is None else (end["x"] - x) * ux + (end["z"] - z) * uz
    srec["sail"] = {"from": s0, "outcome": r["outcome"], "end": end, "progress": None if p is None else round(p, 2),
                    "sim": {k: b["sim"][k] for k in ("progress", "end", "topos")}, "shots": [shot0.name, shot1.name],
                    "samples": r["samples"][-40:]}
    g.check(p is not None and abs(p - b["sim"]["progress"]) <= TOL_BOAT and end["vehicle"] == 7,
            "R4 the boat sails across the knit seam into the cove and stops where the simulation stops it",
            f"{r['outcome']} at {p}u (sim {b['sim']['progress']}); end {end}")


def run(g):
    problems = preflight()
    if problems:
        g.check(False, "world-river preflight", "; ".join(problems))
        return
    g.note("world-river rung 4: cluster C's river, bridge, cove and island carried onto a kit island")
    mark = g.log_mark()
    try:
        for k, stage in enumerate(STAGES):
            srec = {"stage": stage, "t": time.time()}
            _RECORD["stages"].append(srec)
            try:
                (stage_foot if stage == "foot" else stage_boat)(g, srec, first=(k == 0))
            except HarnessError as err:
                srec["error"] = str(err)[:400]
                g.check(False, f"{stage}: stage completed", str(err)[:200])
            _save(g)
    finally:
        try:
            _RECORD["exceptions"] = [str(e) for e in g.exceptions_since(mark)][:20]
        except Exception as err:                                        # noqa: BLE001
            _RECORD["exceptions_error"] = repr(err)
        _save(g)
