"""X1 IN GAME -- ROCK STRETCH TOLERANCE: stills of the Uaho rock stretched x1.25 / x1.5 / x2.0, for the owner's eye.

The bench is the verbatim Uaho block on the Path D world (Disc9 cell (13,15), FF9CustomMap-world). The lab
FF9CustomMap-lab sits first in FolderNames for this run and holds bench field 30950 (the rung-6 pad into world 9013,
with its WorldMap(9013) splice) and, per stage, one stretched `Block[13][15] Terrain.ff9mesh` from x1_build.py. The
engine re-reads every override from disk at each world load (WorldMeshOverride.TryLoad: File.Exists + ReadMesh, no
cache), so a stage swaps the lab's file at the title and the next world load serves it.

STAGES, one world load each, in this order: rigid (no lab override: the live carry), s125, s150, s200
(X1_STAGES=rigid reruns a subset). Each session first learns the camera's turn rate on the landing lawn.
Per stage: title -> newgame -> warp 30950 -> calibrate -> walk the pad -> world 9013 -> encounters off ->
  for each viewpoint (east, west: plain grass ~26u from the massif, x1_build.viewpoints): teleport home, world_face
  the massif, teleport home, settle, two stills 60 frames apart (the second shows the camera had settled);
  then THE NUMERIC CONTROL: teleport onto the rock near its summit and read world_y.

REGISTERED PREDICTIONS (x1_build.py, out/x1/build.json; the look itself is the owner's call):
  P1 the summit probe reads the served file: y 13.010 / 14.958 / 16.906 / 20.803 (+-0.15) for rigid / s125 /
     s150 / s200 -- the instrument check that each stage showed the variant it names.
  P2 every stage reaches world 9013 and both viewpoints face the massif within 6 deg.
  Owner (uvclass NOTES X1): x1.25 reads like the rigid carry; x1.5 borderline; x2.0 visibly stretched.
RUN:  py tools/play.py studies/terrain-malleability/rockstretch/x1_session.py --label x1-rockstretch
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
from harness import HarnessError                      # noqa: E402

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
LAB_NAME = "FF9CustomMap-lab"
LAB = GAME / LAB_NAME
BUILD = json.loads((HERE / "out" / "x1" / "build.json").read_text(encoding="utf-8"))
REL = "FF9_Data/WorldMap/Disc9/0_1/r15/Block[13][15] Terrain.ff9mesh"
STAGES = tuple(os.environ.get("X1_STAGES", "rigid,s125,s150,s200").split(","))   # a rerun may name a subset
LANDING = (428.362, -476.593)                          # Disc9 (6,7) lawn, 8.37u clear (d9_prep): face here first
BENCH, BENCH_NAME, WORLD = 30950, "PATHDGATE", 9013
WORLDMAP_9013 = bytes.fromhex("b6003523")             # opcodes.world_map(9013): WMAPJUMP 0xB6, arg 0x2335
EB_US = "StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/field/us/EVT_PATHDGATE.eb.bytes"
ZONE = [[-600, -1900], [600, -1900], [600, -1500], [-600, -1500]]   # inject_worldjump.ZONE_CORNERS
PAD = (0.0, -1700.0)
VIEWS = ("east", "west")
SETTLE, APART = 180, 60                                # frames: camera easing after a teleport is > 90 (RESULTS)
TOL_Y, TOL_FACE = 0.15, 6.0
_RECORD: dict = {"lane": "x1", "build": {k: BUILD[k] for k in ("live_sha256", "probe", "viewpoints")}, "stages": []}


def _save(g):
    try:
        (g.run_dir / "x1_session.json").write_text(json.dumps(_RECORD, indent=1, default=str), encoding="utf-8")
    except Exception as err:                                            # noqa: BLE001
        print(f"[x1] could not write the record: {err}")


def preflight() -> list:
    ini = (GAME / "Memoria.ini").read_text(encoding="utf-8", errors="replace")
    m = re.search(r'^\s*FolderNames\s*=\s*(.+)$', ini, re.M)
    folders = re.findall(r'"([^"]*)"', m.group(1)) if m else []
    problems = []
    if not folders or folders[0] != LAB_NAME:
        problems.append(f"{LAB_NAME} must be FIRST in FolderNames (it must outrank FF9CustomMap-world): {folders}")
    dp = (LAB / "DictionaryPatch.txt")
    if not dp.is_file() or not re.search(rf"^FieldScene {BENCH} \d+ {BENCH_NAME}\b", dp.read_text(encoding="utf-8"), re.M):
        problems.append(f"FieldScene {BENCH} {BENCH_NAME} is not registered in {LAB_NAME}")
    eb = LAB / EB_US
    if not eb.is_file() or WORLDMAP_9013 not in eb.read_bytes():
        problems.append("the WorldMap(9013) splice is missing (inject_worldjump.py after deploy_field.py)")
    if (LAB / REL).exists():
        problems.append(f"the lab already holds a {REL} -- the rigid stage must start from the live carry")
    for f in folders[1:]:
        p = GAME / f / "DictionaryPatch.txt"
        if p.is_file() and re.search(rf"^(FieldScene|WorldScene|BattleScene|MessageFile) {BENCH}\b",
                                     p.read_text(encoding="utf-8", errors="replace"), re.M):
            problems.append(f"{f} also registers id {BENCH} (EventDB is global)")
    live = GAME / "FF9CustomMap-world" / REL
    if hashlib.sha256(live.read_bytes()).hexdigest() != BUILD["live_sha256"]:
        problems.append("the live carry changed since x1_build.py ran -- rebuild the variants")
    return problems


def place(stage: str) -> str | None:
    """Put the stage's Terrain override in the lab (or none, for the rigid control). Returns the lab file's sha."""
    dst = LAB / REL
    if stage == "rigid":
        if dst.exists():
            dst.unlink()
        return None
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(HERE / "out" / "x1" / stage / REL, dst)
    sha = hashlib.sha256(dst.read_bytes()).hexdigest()
    assert sha == BUILD["variants"][stage]["sha256"], stage
    return sha


def enter_9013(g, srec):
    if g.state.ui_state != "Title":
        ok, why = g.restore_baseline()
        if not ok:
            raise HarnessError(f"cannot reach the title before the stage: {why}")
    g.newgame()
    g.warp(BENCH)
    g.wait_frames(45)
    for attempt in range(3):                       # d9_session: a frame hitch can fail a calibration probe
        try:
            g.calibrate_axes(hazards=[ZONE], recalibrate=attempt > 0)
            break
        except HarnessError as err:
            srec.setdefault("calibration_retries", []).append(str(err)[:200])
            if attempt == 2:
                raise
            g.warp(BENCH)
            g.wait_frames(90)
    g.walk_to(*PAD, strict=False, halt_on_transition=True)
    g.wait_world(timeout=90)
    st = g.world_settle()
    srec["arrival"] = {"world": st.world_id, "x": st.world_x, "z": st.world_z, "y": st.world_y}
    g.check(st.world_id == WORLD, f"{srec['stage']}: the pad lands on world {WORLD}", f"world_id={st.world_id}")
    g.no_encounters()
    if getattr(g, "world_turn_rate", None) is None:
        # WARM-UP (run 1's lesson): the first world_face of a session learns the bumper's turn rate from its first
        # correction. At the east viewpoint that correction read +0.07 deg twice (the probe slid along the rock foot)
        # and the verb refused the camera. Learn the rate on the open landing lawn instead; it stays on the session.
        try:
            srec["warmup"] = {k: v for k, v in g.world_face(0.0, home=LANDING).items() if k in ("heading", "error", "rate")}
        except HarnessError as err:
            srec["warmup"] = {"error": str(err)[:300]}


def look(g, stage: str, view: str, srec):
    vp = BUILD["viewpoints"][view]
    home = tuple(vp["world"])
    g.teleport(*home)
    try:
        face = g.world_face(vp["bearing_deg"], home=home)
    except HarnessError as err:                     # one retry: the rate it learned on the way is kept
        srec.setdefault("face_retries", []).append(str(err)[:300])
        face = g.world_face(vp["bearing_deg"], home=home)
    g.teleport(*home)
    g.wait_frames(SETTLE)
    a = g.shot(f"{stage}-{view}-a")
    g.wait_frames(APART)
    b = g.shot(f"{stage}-{view}-b")
    st = g.world_settle()
    srec["views"][view] = {"home": home, "face": {k: face[k] for k in ("heading", "error")},
                           "at": [st.world_x, st.world_y, st.world_z], "shots": [a.name, b.name]}
    g.check(abs(face["error"]) <= TOL_FACE, f"{stage}/{view}: faces the massif",
            f"heading {face['heading']:.1f} vs bearing {vp['bearing_deg']:.1f}")


def probe(g, stage: str, srec):
    px, pz = BUILD["probe"]["world"]
    want = BUILD["probe"]["y"][stage]
    g.teleport(px, pz)
    g.wait_frames(30)
    st = g.world_settle()
    srec["probe"] = {"want": want, "got": st.world_y, "at": [st.world_x, st.world_z]}
    g.check(st.world_y is not None and abs(st.world_y - want) <= TOL_Y,
            f"{stage}: the summit reads the served file (y {want})", f"world_y={st.world_y}")


def run(g):
    problems = preflight()
    if problems:
        g.check(False, "x1 preflight", "; ".join(problems))
        return
    g.note("x1: the Uaho rock stretched x1.25 / x1.5 / x2.0 on Disc9 (13,15), stills + summit heights")
    try:
        for stage in STAGES:
            srec = {"stage": stage, "t": time.time(), "views": {}}
            _RECORD["stages"].append(srec)
            if g.state.ui_state != "Title":
                ok, why = g.restore_baseline()
                if not ok:
                    raise HarnessError(f"cannot reach the title before {stage}: {why}")
            srec["lab_sha"] = place(stage)
            try:
                enter_9013(g, srec)
                for view in VIEWS:
                    look(g, stage, view, srec)
                probe(g, stage, srec)
            except HarnessError as err:
                srec["error"] = str(err)[:400]
                g.check(False, f"{stage}: stage completed", str(err)[:200])
            _save(g)
    finally:
        place("rigid")                               # never leave a stretched file in the lab
        _save(g)
