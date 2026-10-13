"""`world-forest --spread / --rot` IN GAME: the (15,15) canopy carried four ways onto one scratch island.

The lab FF9CustomMap-lab sits first in FolderNames for this run and holds the scratch island on blocks
(20,0)-(22,2), open ocean no live folder touches (lab_build.py). Each stage puts that variant's four Terrain
overrides in the lab, then reaches the disc-1 world through bench 6603 (newgame first, a world->6603 round trip
after): the engine re-reads every override at each world load. The lab also carries world-environment's
`mist = false` Environment.txt (round 16: the mist hides texture).

STAGES, in this order: A (the verbatim carry: the control), B (--rot 45), C (--spread 1.25), D (--spread 1.5).
Per stage, encounters off, then:
  - the first stage learns the camera's turn rate on the 6603 landing lawn (round 15's lesson);
  - VIEWS west, east, north: teleport home, face the canopy's centre, two stills 60 frames apart, the home's height,
    then WALK THROUGH: hold up, judged by nothing mid-walk but a stall (3 bursts in a row under 1e-4u: the creep
    walker, round 3's lesson -- a climb onto canopy is a slow step, not a wall) until he stands on grass past the
    canopy's far side;
  - CANOPY: 9 points on the canopy, each height; RING: 12 grass points 2u outside it, each height.
REGISTERED PREDICTIONS (lab_prep.py, out/lab/prep.json), tolerance 0.15 on every height:
  P1 every stage reaches the world, and every canopy point reads its built surface minus the canopy sink 1.171875;
  P2 all 12 ring points read the built ground in every variant (the zip holds the player all round);
  P3 every walk climbs onto the canopy, crosses it and steps off the far side onto grass -- never stalled (the
     perimeter walk-in gate's promise: no single step climbs more than 2.30), never below y 2 (no crack);
  P4 each home reads its predicted ground height.
  Owner: the canopy at 45 deg and wider reads like the verbatim carry; at what spread does it start to look stretched?
RUN:  py tools/play.py studies/terrain-malleability/canopyspread/lab_session.py --label canopy-spread
FOREST_STAGES=A,C picks stages; FOREST_STILLS=1 = views and stills only.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools"))
sys.path.insert(0, str(HERE.parent / "ingame"))
sys.path.insert(0, str(HERE))
from harness import HarnessError                      # noqa: E402
import veh_lib as V                                   # noqa: E402  (the 6603 route out to the world)
import lab_prep as P                                  # noqa: E402  (the variants' own down-ray, for the walks)

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
LAB_NAME = "FF9CustomMap-lab"
LAB = GAME / LAB_NAME
SRC = HERE / "out" / "lab"
PREP = json.loads((SRC / "prep.json").read_text(encoding="utf-8"))
BLOCKS = P.BLOCKS
STAGES = tuple(os.environ.get("FOREST_STAGES", "A,B,C,D").split(","))
STILLS_ONLY = os.environ.get("FOREST_STILLS") == "1"
ENV = LAB / "StreamingAssets" / "Data" / "World" / "Environment.txt"
VIEWS = ("west", "east", "north")
SETTLE, APART = 180, 60
TOL_Y, TOL_FACE = 0.15, 6.0
BURST, MAX_BURSTS = 10, 160
_RECORD: dict = {"lane": "canopy-spread", "prep": PREP, "stages": []}


def rel(bx, by):
    return f"FF9_Data/WorldMap/Disc1/0_1/r{by}/Block[{bx}][{by}] Terrain.ff9mesh"


def _save(g):
    try:
        (g.run_dir / "forest_session.json").write_text(json.dumps(_RECORD, indent=1, default=str), encoding="utf-8")
    except Exception as err:                                            # noqa: BLE001
        print(f"[forest] could not write the record: {err}")


def preflight() -> list:
    ini = (GAME / "Memoria.ini").read_text(encoding="utf-8", errors="replace")
    m = re.search(r'^\s*FolderNames\s*=\s*(.+)$', ini, re.M)
    folders = re.findall(r'"([^"]*)"', m.group(1)) if m else []
    problems = []
    if not folders or folders[0] != LAB_NAME:
        problems.append(f"{LAB_NAME} must be FIRST in FolderNames: {folders}")
    for bx, by in BLOCKS:
        if not (LAB / rel(bx, by)).is_file():
            problems.append(f"the lab has no island Terrain at ({bx},{by})")
        for f in folders[1:]:
            hits = list((GAME / f / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / f"r{by}").glob(f"Block[[]{bx}[]][[]{by}[]]*"))
            if hits:
                problems.append(f"{f} also overrides block ({bx},{by}): {[h.name for h in hits][:3]}")
    if not any(re.search(r"^FieldScene 6603 ", (GAME / f / "DictionaryPatch.txt").read_text(encoding="utf-8",
                                                                                         errors="replace"), re.M)
               for f in folders if (GAME / f / "DictionaryPatch.txt").is_file()):
        problems.append("bench 6603 (the route to the world) is not registered")
    return problems


def place(stage: str) -> dict:
    """The variant's four Terrain overrides into the lab; returns their shas (checked against the source)."""
    out = {}
    for bx, by in BLOCKS:
        src = SRC / stage / LAB_NAME / rel(bx, by)
        dst = LAB / rel(bx, by)
        shutil.copyfile(src, dst)
        a, b = (hashlib.sha256(p.read_bytes()).hexdigest() for p in (src, dst))
        assert a == b, (stage, bx, by)
        out[f"{bx},{by}"] = a[:12]
    return out


_GROUND: dict = {}


def ground(stage: str):
    if stage not in _GROUND:
        _GROUND[stage] = P.RP.Ground(*P.load(stage))
    return _GROUND[stage]


def settle_y(g, wait=30):
    g.wait_frames(wait)
    return V.settle3(g)


def walk_through(g, stage: str, home, pv: dict, vrec: dict):
    """Hold up from the home along the bearing (already faced) until he stands on grass 1.5u past the canopy's far
    side; stop only on a stall (3 bursts in a row under 1e-4u) or leaving the world."""
    gr = ground(stage)
    ux, uz = math.cos(math.radians(pv["bearing_deg"])), math.sin(math.radians(pv["bearing_deg"]))
    rows = []
    still, outcome = 0, "max_bursts"
    prev = V.here(g)
    for _ in range(MAX_BURSTS):
        g.send(f"hold up {BURST}", f"wait {BURST + 2}")
        g.world_settle()
        if not g.state.on_world:
            outcome = "left_world"
            break
        now = V.here(g)
        d = math.hypot(now["x"] - prev["x"], now["z"] - prev["z"])
        a = (now["x"] - home[0]) * ux + (now["z"] - home[1]) * uz
        hit = gr(now["x"], now["z"])
        rows.append({"x": now["x"], "z": now["z"], "y": now["y"], "along": round(a, 3), "moved": round(d, 5),
                     "topo": hit[1] if hit else None})
        prev = now
        if a >= pv["grass_after"] + 1.5 and hit and hit[1] == P.GRASS:
            outcome = "through"
            break
        still = still + 1 if d < 1e-4 else 0
        if still >= 3:
            outcome = "stalled"
            break
    on_canopy = [r for r in rows if r["topo"] == P.CANOPY]
    ys = [r["y"] for r in rows if r.get("y") is not None]
    vrec["walk"] = {"outcome": outcome, "rows": rows, "min_y": min(ys) if ys else None,
                    "canopy_rows": len(on_canopy),
                    "max_along": max((r["along"] for r in rows), default=None)}
    end = rows[-1] if rows else {}
    g.check(outcome == "through" and on_canopy and ys and min(ys) > 2.0,
            f"{stage}: the walk climbs onto the canopy, crosses it and steps off onto grass",
            f"{outcome} at along {end.get('along')} (canopy {pv['canopy_from']}..{pv['canopy_to']}, grass "
            f"{pv['grass_after']}), {len(on_canopy)} bursts on canopy, min y {min(ys) if ys else None}")


def look(g, stage: str, view: str, srec: dict):
    vp = PREP["views"][view]
    pv = vp["per_variant"][stage]
    home = tuple(vp["world"])
    g.teleport(*home)
    try:
        face = g.world_face(pv["bearing_deg"], home=home)
    except HarnessError as err:                     # one retry: the rate it learned on the way is kept
        srec.setdefault("face_retries", []).append(str(err)[:300])
        face = g.world_face(pv["bearing_deg"], home=home)
    g.teleport(*home)
    g.wait_frames(SETTLE)
    a = g.shot(f"{stage}-{view}-a")
    g.wait_frames(APART)
    b = g.shot(f"{stage}-{view}-b")
    at = V.settle3(g)
    vrec = {"home": home, "face": {k: face[k] for k in ("heading", "error")}, "at": at, "shots": [a.name, b.name]}
    srec["views"][view] = vrec
    g.check(abs(face["error"]) <= TOL_FACE, f"{stage}/{view}: faces the canopy",
            f"heading {face['heading']:.1f} vs bearing {pv['bearing_deg']:.1f}")
    g.check(at["y"] is not None and abs(at["y"] - pv["ground_y"]) <= TOL_Y, f"{stage}/{view}: home height",
            f"y={at['y']} want {pv['ground_y']}")
    if not STILLS_ONLY:
        walk_through(g, stage, home, pv, vrec)


def probes(g, stage: str, srec: dict):
    v = PREP["variants"][stage]
    for what, pts in (("canopy", v["canopy"]), ("ring", v["ring"])):
        got = []
        for p in pts:
            g.teleport(*p["world"])
            at = settle_y(g, 20)
            ok = at["y"] is not None and abs(at["y"] - p["y"]) <= TOL_Y
            got.append({"deg": p["deg"], "want": p["y"], "got": at["y"], "ok": ok, "at": [at["x"], at["z"]]})
        srec[what] = got
        bad = [r for r in got if not r["ok"]]
        g.check(not bad, f"{stage}: all {len(got)} {what} points read the built ground"
                + (" minus the canopy sink" if what == "canopy" else ""),
                "; ".join(f"{r['deg']}deg got {r['got']} want {r['want']}" for r in bad) or f"{len(got)}/{len(got)}")


def run(g):
    problems = preflight()
    if problems:
        g.check(False, "forest preflight", "; ".join(problems))
        return
    _RECORD["stills_only"] = STILLS_ONLY
    _RECORD["environment"] = ENV.read_text(encoding="utf-8") if ENV.is_file() else None
    g.check(ENV.is_file() and "Mist [Condition=false]" in ENV.read_text(encoding="utf-8"),
            "the mist is forced off for the stills (the lab's Environment.txt)", str(_RECORD["environment"]))
    g.note("canopy-spread: world-forest --spread/--rot on a scratch island -- verbatim, 45 deg, x1.25, x1.5"
           + (" (stills)" if STILLS_ONLY else ""))
    mark = g.log_mark()
    try:
        for k, stage in enumerate(STAGES):
            srec = {"stage": stage, "t": time.time(), "views": {}}
            _RECORD["stages"].append(srec)
            srec["lab"] = place(stage)
            try:
                V.reach_world_as(g, srec, scenario=0, pokes={}, expect_world=0, first=(k == 0))
                g.no_encounters()
                g.check(g.state.on_world, f"{stage}: on the world map", json.dumps(srec.get("arrival")))
                if getattr(g, "world_turn_rate", None) is None:
                    arr = srec.get("arrival") or V.here(g)
                    try:
                        srec["warmup"] = {k2: v2 for k2, v2 in g.world_face(0.0, home=(arr["x"], arr["z"])).items()
                                          if k2 in ("heading", "error", "rate")}
                    except HarnessError as err:
                        srec["warmup"] = {"error": str(err)[:300]}
                for view in VIEWS:
                    look(g, stage, view, srec)
                if not STILLS_ONLY:
                    probes(g, stage, srec)
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
