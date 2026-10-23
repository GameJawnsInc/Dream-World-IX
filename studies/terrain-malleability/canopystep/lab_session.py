"""comp26 IN GAME (mountaindonors/STEP.md): a desert massif carried with its walled canopy onto a desert island.

The lab FF9CustomMap-lab sits first in FolderNames for this run (lab_install.py) and holds the scratch island
(lab_build.py). Each stage puts that variant's whole disc-1 override tree in the lab, then reaches the disc-1 world
through bench 6603 (newgame first, a world->6603 round trip after): the engine re-reads every override at each load.

STAGES, in this order: A (rot 0), B (rot 90), C (rot 200), D (rot 270). snowmassif/lab_session.py's run, with the
inlet stage replaced by THE CANOPY (canopyspread's model: on canopy the party stands CANOPY_SINK below its surface).
Per stage, encounters off, then:
  - the first stage learns the camera's turn rate on the 6603 landing lawn (round 15's lesson);
  - VIEWS (the variant's own: east, north, west, south): teleport home, face the massif, two stills 60 frames apart,
    the home's height; from west and east, a walk straight at the rock centroid;
  - CANOPY: teleport onto each of 5 canopy points, read the height; then INTO: teleport to the desert home beyond
    the canopy, face the rock, two stills, and walk in across the canopy to the rock;
  - SUMMIT: teleport beside the peak, read the height;
  - RING: the 12 desert points 2u outside the carried blob (rock or canopy), each height.
REGISTERED PREDICTIONS (lab_prep.py, out/lab/prep.json), tolerance 0.15 on every height:
  P1 every stage reaches the world, and the summit reads the variant's peak;
  P2 all 12 ring points read the built ground: the zip seam holds all round, the canopy's wall foot included;
  P3 each walk keeps to the built ground (judge the trace): every sample stands within 0.15 of a built surface under
     him that is not rock -- on canopy, that surface less the sink -- and none dips below y 1.5;
  P4 each home reads its predicted ground height;
  P5 THE CANOPY: every canopy point reads its surface less 1.171875; the walk in climbs onto the canopy (samples on
     it) and gets at least to the canopy's far half (canopy_from + half the canopy run) without stalling.
  Owner: comp26 reads as a stock desert massif with its scrub canopy, at 0, 90, 200 and 270 deg.
RUN:  py studies/terrain-malleability/canopystep/lab_install.py install
      py tools/play.py studies/terrain-malleability/canopystep/lab_session.py --label canopy-step
      (CANOPY_DONOR=comp10 on all three for round 23)
      py studies/terrain-malleability/canopystep/lab_install.py uninstall <run dir>
MTN_STILLS=1 = views and stills only.
"""
from __future__ import annotations

import hashlib
import json
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
import lab_prep as P                                  # noqa: E402  (the variants' own down-ray)

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
LAB_NAME = "FF9CustomMap-lab"
LAB = GAME / LAB_NAME
import rounds  # noqa: E402  ($CANOPY_DONOR)
SRC = rounds.LAB
PREP = json.loads((SRC / "prep.json").read_text(encoding="utf-8"))
STAGES = tuple(os.environ.get("MTN_STAGES", ",".join(PREP["variants"])).split(","))
STILLS_ONLY = os.environ.get("MTN_STILLS") == "1"
ENV = LAB / "StreamingAssets" / "Data" / "World" / "Environment.txt"
VIEWS = ("west", "east", "north", "south")
WALKS = ("west", "east")
SETTLE, APART = 180, 60
TOL_Y, TOL_FACE = 0.15, 6.0
TREE = Path("FF9_Data") / "WorldMap" / "Disc1"
_RECORD: dict = {"lane": rounds.R["label"], "prep": PREP, "stages": []}


def _save(g):
    try:
        (g.run_dir / "mountain_session.json").write_text(json.dumps(_RECORD, indent=1, default=str), encoding="utf-8")
    except Exception as err:                                            # noqa: BLE001
        print(f"[mountain] could not write the record: {err}")


def all_blocks() -> list:
    return sorted({tuple(b) for v in PREP["variants"].values() for b in v["blocks"]})


def preflight() -> list:
    ini = (GAME / "Memoria.ini").read_text(encoding="utf-8", errors="replace")
    m = re.search(r'^\s*FolderNames\s*=\s*(.+)$', ini, re.M)
    folders = re.findall(r'"([^"]*)"', m.group(1)) if m else []
    problems = []
    if not folders or folders[0] != LAB_NAME:
        problems.append(f"{LAB_NAME} must be FIRST in FolderNames: {folders}")
    for bx, by in all_blocks():
        if not (LAB / TREE / "0_1" / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh").is_file():
            problems.append(f"the lab has no island Terrain at ({bx},{by})")
        for f in folders[1:]:
            hits = list((GAME / f / TREE / "0_1" / f"r{by}").glob(f"Block[[]{bx}[]][[]{by}[]]*"))
            if hits:
                problems.append(f"{f} also overrides block ({bx},{by}): {[h.name for h in hits][:3]}")
    if not any(re.search(r"^FieldScene 6603 ", (GAME / f / "DictionaryPatch.txt").read_text(encoding="utf-8",
                                                                                         errors="replace"), re.M)
               for f in folders if (GAME / f / "DictionaryPatch.txt").is_file()):
        problems.append("bench 6603 (the route to the world) is not registered")
    return problems


def place(stage: str) -> dict:
    """The variant's whole disc-1 override tree into the lab (the previous stage's removed first); returns the
    files' shas, each checked against its source."""
    src, dst = SRC / stage / LAB_NAME / TREE, LAB / TREE
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    out = {}
    for p in sorted(src.rglob("*")):
        if p.is_file():
            q = dst / p.relative_to(src)
            a, b = (hashlib.sha256(x.read_bytes()).hexdigest() for x in (p, q))
            assert a == b, (stage, p)
            out[str(p.relative_to(src))] = a[:12]
    return out


_GROUND: dict = {}


def ground(stage: str):
    if stage not in _GROUND:
        _GROUND[stage] = P.SP.Ground(*P.load(stage))
    return _GROUND[stage]


def standing(gr, x, z, y):
    """The built surface under (x, z) the player's height y fits, the canopy sink applied: (y_surface, topo) or None."""
    hs = gr.hits(x, z)
    return min(hs, key=lambda h: abs(P.expect_y(h) - y)) if hs else None


def settle_y(g, wait=30):
    g.wait_frames(wait)
    return V.settle3(g)


def judge_walk(g, stage, walk, label, need=None, want_canopy=False):
    gr = ground(stage)
    bad, ys, on_canopy = [], [], 0
    for r in walk["trace"]:
        if r.get("x") is None or r.get("y") is None:
            continue
        ys.append(r["y"])
        s = standing(gr, r["x"], r["z"], r["y"])
        if s is None or abs(r["y"] - P.expect_y(s)) > TOL_Y or P.is_rock(s[1]):
            bad.append({"x": r["x"], "z": r["z"], "y": r["y"], "surface": s})
        elif s[1] == P.CANOPY:
            on_canopy += 1
    rec = {"outcome": walk["outcome"], "progress": walk["progress"], "min_y": min(ys) if ys else None,
           "samples": len(ys), "off_surface": bad[:6], "on_canopy": on_canopy, "end": walk["trace"][-1]}
    ok = (bool(ys) and not bad and min(ys) > 1.5 and (need is None or walk["progress"] >= need)
          and (not want_canopy or on_canopy > 0))
    g.check(ok, f"{stage}/{label}: the walk keeps to the built ground, never on rock"
            + (", climbs onto the canopy" if want_canopy else "")
            + (f", and gets {need:.1f}u in" if need is not None else ""),
            f"{walk['outcome']} at {walk['progress']:.2f}u over {len(ys)} samples; off-surface/rock {len(bad)}"
            f" {bad[:2]}; min y {min(ys) if ys else None}")
    return rec


def shoot(g, stage, label, home, bearing, srec):
    g.teleport(*home)
    try:
        face = g.world_face(bearing, home=home)
    except HarnessError as err:                     # one retry: the rate it learned on the way is kept
        srec.setdefault("face_retries", []).append(str(err)[:300])
        face = g.world_face(bearing, home=home)
    g.teleport(*home)
    g.wait_frames(SETTLE)
    a = g.shot(f"{stage}-{label}-a")
    g.wait_frames(APART)
    b = g.shot(f"{stage}-{label}-b")
    at = V.settle3(g)
    g.check(abs(face["error"]) <= TOL_FACE, f"{stage}/{label}: faces the massif",
            f"heading {face['heading']:.1f} vs bearing {bearing:.1f}")
    return {"home": home, "face": {k: face[k] for k in ("heading", "error")}, "at": at, "shots": [a.name, b.name]}


def look(g, stage: str, view: str, srec: dict):
    pv = PREP["variants"][stage]["views"].get(view)
    if pv is None:
        srec["views"][view] = {"skipped": "prep found no lawful home in this sector"}
        return
    home = tuple(pv["world"])
    vrec = shoot(g, stage, view, home, pv["bearing_deg"], srec)
    srec["views"][view] = vrec
    at = vrec["at"]
    g.check(at["y"] is not None and abs(at["y"] - pv["ground_y"]) <= TOL_Y, f"{stage}/{view}: home height",
            f"y={at['y']} want {pv['ground_y']}")
    if view in WALKS and not STILLS_ONLY:
        walk = g.world_approach(pv["bearing_deg"], (pv["first_rock"] or pv["dist"]) + 4.0)
        vrec["walk"] = judge_walk(g, stage, walk, f"{view} walk")


def canopy(g, stage: str, srec: dict):
    v = PREP["variants"][stage]
    rec = srec["canopy"] = {"points": []}
    if not STILLS_ONLY:
        for p in v["canopy"]:
            g.teleport(*p["world"])
            at = settle_y(g, 20)
            rec["points"].append({"want": p["y"], "got": at["y"],
                                  "ok": at["y"] is not None and abs(at["y"] - p["y"]) <= TOL_Y})
        bad = [r for r in rec["points"] if not r["ok"]]
        g.check(len(v["canopy"]) == 5 and not bad, f"{stage}: every canopy point reads its surface less the sink",
                "; ".join(f"got {r['got']} want {r['want']}" for r in bad) or f"{len(rec['points'])}/5")
    into = v.get("into")
    g.check(into is not None, f"{stage}: prep found a desert home to walk into the canopy from", json.dumps(into))
    if not into:
        return
    hm = tuple(into["world"])
    rec["view"] = shoot(g, stage, "into", hm, into["bearing_deg"], srec)
    at = rec["view"]["at"]
    g.check(at["y"] is not None and abs(at["y"] - into["ground_y"]) <= TOL_Y, f"{stage}/into: home height",
            f"y={at['y']} want {into['ground_y']}")
    if not STILLS_ONLY:
        need = into["canopy_from"] + (into["rock_from"] - into["canopy_from"]) / 2
        walk = g.world_approach(into["bearing_deg"], into["rock_from"] + 2.0)
        rec["walk"] = judge_walk(g, stage, walk, "walk into the canopy", need=need, want_canopy=True)


def probes(g, stage: str, srec: dict):
    v = PREP["variants"][stage]
    g.teleport(*v["summit"]["world"])
    at = settle_y(g)
    srec["summit"] = {"want": v["summit"]["y"], "at": at}
    g.check(at["y"] is not None and abs(at["y"] - v["summit"]["y"]) <= TOL_Y,
            f"{stage}: the summit reads the served file (y {v['summit']['y']})", f"y={at['y']}")
    ring = []
    for p in v["ring"]:
        g.teleport(*p["world"])
        at = settle_y(g, 20)
        ok = at["y"] is not None and abs(at["y"] - p["y"]) <= TOL_Y
        ring.append({"deg": p["deg"], "want": p["y"], "got": at["y"], "ok": ok, "at": [at["x"], at["z"]]})
    srec["ring"] = ring
    bad = [r for r in ring if not r["ok"]]
    g.check(not bad, f"{stage}: all 12 points round the foot read the built ground",
            "; ".join(f"{r['deg']}deg got {r['got']} want {r['want']}" for r in bad) or "12/12")


def run(g):
    problems = preflight()
    if problems:
        g.check(False, "canopy-step preflight", "; ".join(problems))
        return
    _RECORD["stills_only"] = STILLS_ONLY
    _RECORD["environment"] = ENV.read_text(encoding="utf-8") if ENV.is_file() else None
    g.check(ENV.is_file() and "Mist [Condition=false]" in ENV.read_text(encoding="utf-8"),
            "the mist is forced off for the stills (the lab's Environment.txt)", str(_RECORD["environment"]))
    g.note(f"{rounds.R['label']}: {rounds.R['what']} -- rot "
           + ", ".join(f"{s} {PREP['variants'][s]['rot']}" for s in STAGES)
           + (" (stills, mist off)" if STILLS_ONLY else ""))
    mark = g.log_mark()
    try:
        for k, stage in enumerate(STAGES):
            srec = {"stage": stage, "rot": PREP["variants"][stage]["rot"], "t": time.time(), "views": {}}
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
                canopy(g, stage, srec)
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
