"""`world-mountain --rot` IN GAME: the Uaho massif carried at 0 deg, 45 deg, and 30 deg x1.5 tall, on one island.

The lab FF9CustomMap-lab sits first in FolderNames for this run and holds the scratch island on blocks
(20,0)-(21,1), open ocean no live folder touches (rot_prep.py). Each stage puts that variant's four Terrain
overrides in the lab, then reaches the disc-1 world through bench 6603 (newgame first, a world->6603 round trip
after): the engine re-reads every override at each world load.

STAGES, in this order: A (--rot 0, the rigid carry: the control), B (--rot 45), C (--rot 30 --rock-height 1.5).
Per stage, encounters off, then:
  - the first stage learns the camera's turn rate on the 6603 landing lawn (round 15's lesson);
  - VIEWS west, east, north: teleport home, face that variant's massif, two stills 60 frames apart, the home's
    height; from west and east, a walk straight at the massif;
  - SUMMIT: teleport beside the peak, read the height;
  - RING: the 12 grass points 2u outside the rock foot, one per 30 deg, each height.
REGISTERED PREDICTIONS (rot_prep.py, out/rotlab/prep.json), tolerance 0.15 on every height:
  P1 every stage reaches the world, and the summit reads the variant's peak (A 12.053, B 12.003, C 16.131);
  P2 all 12 ring points read the built ground in every variant: the foot seam holds the player all round, at the
     non-quarter angles too (a crack drops him to the sea, a wrong file reads another height);
  P3 each walk at the massif is BLOCKED at its foot: it ends on the built grass (its height within 0.15 of the
     variant's down-ray there), within 1.5u of rock, and never dips below y 2 on the way;
  P4 each home reads its predicted ground height.
  Owner: the foot seam at 45 and 30 deg reads like the 0-deg carry's, and C's rock reads like X1's x1.5.
RUN:  py tools/play.py studies/terrain-malleability/rockstretch/rot_session.py --label rot-mountain
The lab also carries world-environment's `mist = false` Environment.txt (re-read at every world load): the mist
hides texture, and round 16's first run took its stills in it. ROT_STILLS=1 = views and stills only.
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
import rot_prep as P                                  # noqa: E402  (the variants' own down-ray, for the walk's end)

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
LAB_NAME = "FF9CustomMap-lab"
LAB = GAME / LAB_NAME
SRC = HERE / "out" / "rotlab"
PREP = json.loads((SRC / "prep.json").read_text(encoding="utf-8"))
BLOCKS = [(20, 0), (21, 0), (20, 1), (21, 1)]
STAGES = tuple(os.environ.get("ROT_STAGES", "A,B,C").split(","))
STILLS_ONLY = os.environ.get("ROT_STILLS") == "1"          # the mist-off pass: views and stills, no walks/probes
ENV = LAB / "StreamingAssets" / "Data" / "World" / "Environment.txt"
VIEWS = ("west", "east", "north")
WALKS = ("west", "east")
SETTLE, APART = 180, 60
TOL_Y, TOL_FACE = 0.15, 6.0
_RECORD: dict = {"lane": "rot", "prep": PREP, "stages": []}


def rel(bx, by):
    return f"FF9_Data/WorldMap/Disc1/0_1/r{by}/Block[{bx}][{by}] Terrain.ff9mesh"


def _save(g):
    try:
        (g.run_dir / "rot_session.json").write_text(json.dumps(_RECORD, indent=1, default=str), encoding="utf-8")
    except Exception as err:                                            # noqa: BLE001
        print(f"[rot] could not write the record: {err}")


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
        _GROUND[stage] = P.Ground(*P.load(stage))
    return _GROUND[stage]


def rock_within(gr, x, z, r) -> bool:
    import math
    return any((gr(x + rr * math.cos(a), z + rr * math.sin(a)) or (0, -1))[1] == P.ROCK
               for rr in (0.25, 0.5, 0.75, 1.0, 1.25, 1.5) for a in [k * math.pi / 8 for k in range(16)])


def settle_y(g, wait=30):
    g.wait_frames(wait)
    return V.settle3(g)


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
    g.check(abs(face["error"]) <= TOL_FACE, f"{stage}/{view}: faces the massif",
            f"heading {face['heading']:.1f} vs bearing {pv['bearing_deg']:.1f}")
    g.check(at["y"] is not None and abs(at["y"] - pv["ground_y"]) <= TOL_Y, f"{stage}/{view}: home height",
            f"y={at['y']} want {pv['ground_y']}")
    if view in WALKS and not STILLS_ONLY:
        walk = g.world_approach(pv["bearing_deg"], pv["first_rock"] + 4.0)
        ys = [r.get("y") for r in walk["trace"] if r.get("y") is not None]
        end = walk["trace"][-1]
        gr = ground(stage)
        hit = gr(end["x"], end["z"]) if end.get("x") is not None else None
        near = rock_within(gr, end["x"], end["z"], 1.5) if hit else None
        vrec["walk"] = {"outcome": walk["outcome"], "progress": walk["progress"], "min_y": min(ys) if ys else None,
                        "end": end, "ground_at_end": hit, "rock_within_1.5u": near}
        # THE FOOT: blocked, standing on the built grass at the rock foot (a slide along a slanted foot still
        # gains progress along the bearing, so where he stops -- not how far he got -- is the measure), and he
        # never dropped toward the sea on the way (a crack in the seam would).
        g.check(walk["outcome"] == "blocked" and hit is not None and hit[1] == P.GRASS
                and abs(end["y"] - hit[0]) <= TOL_Y and near and ys and min(ys) > 2.0,
                f"{stage}/{view}: the walk at the massif stops at its foot, on the built ground",
                f"{walk['outcome']} at {walk['progress']:.2f}u, end ({end.get('x')}, {end.get('z')}) y {end.get('y')} "
                f"vs built {hit}, rock within 1.5u: {near}, min y {min(ys) if ys else None}")


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
        g.check(False, "rot preflight", "; ".join(problems))
        return
    _RECORD["stills_only"] = STILLS_ONLY
    _RECORD["environment"] = ENV.read_text(encoding="utf-8") if ENV.is_file() else None
    g.check(ENV.is_file() and "Mist [Condition=false]" in ENV.read_text(encoding="utf-8"),
            "the mist is forced off for the stills (the lab's Environment.txt)", str(_RECORD["environment"]))
    g.note("rot: world-mountain --rot on a scratch island -- 0 deg, 45 deg, 30 deg x1.5"
           + (" (stills, mist off)" if STILLS_ONLY else ""))
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
