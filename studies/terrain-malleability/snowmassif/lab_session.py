"""comp9 IN GAME (round 21): a snow massif carried with its inlet floor onto a snow island, three angles.

The lab FF9CustomMap-lab sits first in FolderNames for this run (lab_install.py) and holds the scratch island
(lab_build.py). Each stage puts that variant's whole disc-1 override tree in the lab (Terrain, the ensemble parts and
their Donor.txt: comp9 carries an Object plate as a plug, which a Terrain-only swap would leave behind), then
reaches the disc-1 world through bench 6603 (newgame first, a world->6603 round trip after): the engine re-reads
every override at each world load.

STAGES, in this order: A (rot 0), B (rot 200), C (rot 270). mountainspread/lab_session.py's run, with per-variant
views and one stage added, THE INLET. Per stage, encounters off, then:
  - the first stage learns the camera's turn rate on the 6603 landing lawn (round 15's lesson);
  - VIEWS (the variant's own: east, north, west, south of its rock): teleport home, face the massif, two stills 60
    frames apart, the home's height; from west and east, a walk straight at the massif;
  - INLET: teleport onto the carried inlet floor, read its height; teleport to the inlet home, face the mouth, two
    stills, and walk in;
  - SUMMIT: teleport beside the peak, read the height;
  - RING: the 12 snow points 2u outside the rock foot, one per 30 deg, each height.
REGISTERED PREDICTIONS (lab_prep.py, out/lab/prep.json), tolerance 0.15 on every height:
  P1 every stage reaches the world, and the summit reads the variant's peak;
  P2 all 12 ring points read the built ground in every variant;
  P3 each walk at the massif keeps to the built ground (judge the trace): every sample stands within 0.15 of a
     built surface under him that is not rock, and none dips below y 2;
  P4 each home reads its predicted ground height;
  P5 THE INLET: the floor probe reads the carried floor's height, and the walk in keeps to the built ground and
     gets at least as far as prep's walk_stop (or the probe) less 1.5u -- the closed mouth lets him onto the floor.
  Owner: comp9 reads as a stock FF9 snow mountain at 0, 200 and 270 deg, and its inlet floor reads as the massif's
  own snow, not a patch.
RUN:  py studies/terrain-malleability/snowmassif/lab_install.py install
      py tools/play.py studies/terrain-malleability/snowmassif/lab_session.py --label snow-massif
      py studies/terrain-malleability/snowmassif/lab_install.py uninstall <run dir>
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
SRC = HERE / "out" / "lab"
PREP = json.loads((SRC / "prep.json").read_text(encoding="utf-8"))
STAGES = tuple(os.environ.get("MTN_STAGES", ",".join(PREP["variants"])).split(","))
STILLS_ONLY = os.environ.get("MTN_STILLS") == "1"
ENV = LAB / "StreamingAssets" / "Data" / "World" / "Environment.txt"
VIEWS = ("west", "east", "north", "south")
WALKS = ("west", "east")
SETTLE, APART = 180, 60
TOL_Y, TOL_FACE = 0.15, 6.0
TREE = Path("FF9_Data") / "WorldMap" / "Disc1"
_RECORD: dict = {"lane": "snow-massif", "prep": PREP, "stages": []}


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
    hs = gr.hits(x, z)
    return min(hs, key=lambda h: abs(h[0] - y)) if hs else None


def settle_y(g, wait=30):
    g.wait_frames(wait)
    return V.settle3(g)


def judge_walk(g, stage, walk, label, need=None):
    gr = ground(stage)
    bad, ys = [], []
    for r in walk["trace"]:
        if r.get("x") is None or r.get("y") is None:
            continue
        ys.append(r["y"])
        s = standing(gr, r["x"], r["z"], r["y"])
        if s is None or abs(r["y"] - s[0]) > TOL_Y or P.is_rock(s[1]):
            bad.append({"x": r["x"], "z": r["z"], "y": r["y"], "surface": s})
    rec = {"outcome": walk["outcome"], "progress": walk["progress"], "min_y": min(ys) if ys else None,
           "samples": len(ys), "off_surface": bad[:6], "end": walk["trace"][-1]}
    ok = bool(ys) and not bad and min(ys) > 2.0 and (need is None or walk["progress"] >= need)
    g.check(ok, f"{stage}/{label}: the walk keeps to the built ground, never on rock"
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
        walk = g.world_approach(pv["bearing_deg"], pv["first_rock"] + 4.0)
        vrec["walk"] = judge_walk(g, stage, walk, f"{view} walk")


def inlet(g, stage: str, srec: dict):
    il = PREP["variants"][stage]["inlet"]
    rec = srec["inlet"] = {"prep": il}
    pr, home = il.get("probe"), il.get("home")
    g.check(pr is not None and home is not None, f"{stage}: prep located the carried inlet floor and a home",
            json.dumps({"probe": pr, "home": home}))
    if not (pr and home):
        return
    if not STILLS_ONLY:
        g.teleport(*pr["world"])
        at = settle_y(g)
        rec["probe_at"] = at
        g.check(at["y"] is not None and abs(at["y"] - pr["y"]) <= TOL_Y,
                f"{stage}: the inlet floor reads the carried snow (y {pr['y']})", f"y={at['y']}")
    hm = tuple(home["world"])
    rec["view"] = shoot(g, stage, "inlet", hm, home["bearing_deg"], srec)
    at = rec["view"]["at"]
    g.check(at["y"] is not None and abs(at["y"] - home["ground_y"]) <= TOL_Y, f"{stage}/inlet: home height",
            f"y={at['y']} want {home['ground_y']}")
    if not STILLS_ONLY:
        stop = home["walk_stop"] if home["walk_stop"] > 0 else home["to_probe"] + 4.0
        need = min(stop, home["to_probe"]) - 1.5
        walk = g.world_approach(home["bearing_deg"], min(stop, home["to_probe"] + 4.0))
        rec["walk"] = judge_walk(g, stage, walk, "inlet walk", need=need)


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
        g.check(False, "snow-massif preflight", "; ".join(problems))
        return
    _RECORD["stills_only"] = STILLS_ONLY
    _RECORD["environment"] = ENV.read_text(encoding="utf-8") if ENV.is_file() else None
    g.check(ENV.is_file() and "Mist [Condition=false]" in ENV.read_text(encoding="utf-8"),
            "the mist is forced off for the stills (the lab's Environment.txt)", str(_RECORD["environment"]))
    g.note("snow-massif: comp9 carried with its inlet floor onto a snow island -- rot "
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
                inlet(g, stage, srec)
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
