"""In-game ROUND 3 (2026-10-08): the terrain study's defect 5-6 and O2 fixes, driven in game. DEPLOYS into the scratch
mod folder FF9CustomMap-lab ONLY (owner's go 2026-10-08, "in-game session"; the lab sits first in Memoria.ini
FolderNames for the round). Every lab file is an r3_build.py stage: the kit CLI's own output. $R3_PHASE picks the launch:

  guard   the lab starts EMPTY and this scenario swaps the stages in between field visits -- the engine File.Exists-
          checks every override at each world load (WorldMeshOverride.TryLoad, no cache): stock, A_lower3, A_raise1,
          A_raise4, in that order (the one that may freeze him last)
  beach   the orchestrator puts B_beach3 in the lab before the launch
  replay  the orchestrator puts C_crack4 (Disc1 + its REPLAYED Disc4) in the lab before the launch
RUN:   py tools/play.py studies/terrain-malleability/ingame/r3_session.py --label r3-<phase>     (R3_PHASE=<phase>)
SCORE: py studies/terrain-malleability/ingame/r3_post.py <run dir>   (the lab load lines in Memoria.log)

REGISTERED PREDICTIONS (out/r3_build.json; the site choice in guard_prep.py):

GUARD -- does a field exit set the player down at the record's stored height (the guard's premise, H-RECORD) or on
  the topmost ground (H-SKY: the load-time sky cast, ff9.cs:3700-3705 -> w_movementChrInitSlice)? Route: newgame ->
  warp(750 Burmecia/Entrance, scenario 4000: its regions arm at >= 3800, and the exit's cascade sends key 51 to
  WorldMap(9000)) -> calibrate -> walk into the world-exit region (entry 21). The exit stores (963.234, 3.086,
  -718.910). After the load NO input until x, z and y are still; then up/right/down/left, 12 frames each, until one
  moves him >= 1u (or takes him into a field: he moved onto an entrance tile).
    G0 stock     lands at (963.234, -718.910) +-0.05, y 3.088 +-0.05 -- both hypotheses (the instrument control)
    G1 A_lower3  H-SKY y 0.378 at rest | H-RECORD 3.086 until he moves (an idle re-ground would hide it: weak)
    G2 A_raise1  H-SKY y 3.992 at rest | H-RECORD 3.086, up to the ground on the first step (the ray starts 5.43)
    G3 A_raise4  DECISIVE. H-SKY y 6.701 at rest and he walks | H-RECORD y 3.086 -- 3.615u under the new ground, past
                 the 2.34375 ray start -- and no direction moves him (< 0.1u in all four)
    every phase: once he has moved, y is the ground under him (+-0.15, the sky query on the stage)
  The kit's guard REFUSES G3's edit by default (r3_build: exit 2, nothing written); --allow-entrances deployed it.
  Launch 2 (.harness-runs/20261008-154424-r3-guard, 15/16) judged "at rest" on the first WorldHUD frame, which
  precedes the all-block load (a 4.4 s stall): G1 read the stored 3.086 there, then 0.375 (the new ground) three
  frames later with no input. rest() now counts stillness in advancing frames; launch 3 is the clean record.

BEACH -- session 5's +3 edit at (7,17), now with the stitch pins (defect 5): world-terrain --at 480 -1120 --radius 16
  --raise 3. Offline the steepest per-step rise north from the foam is 0.37-0.38u on all three lines (stock
  0.10-0.15; before the fix ~3u, a one-way wall).
    K1 beach -> terrain (north, 3u) REACHED at all three lines (session 5 at +3: refused at all three)
    K2 terrain -> beach (south, 4u) REACHED at all three lines
    LOOK frames from the south at the shore.

REPLAY -- session 6's +4 edit at (256,-872) (world-terrain --at 256 -872 --radius 16 --raise 4). The auto-mirror is now
  edit-atomic and REPLAYED it on disc 4 (its log: "REPLAYED (4, 13) on Disc4 (real cell differs ... ['sea1'])").
    R1 disc 1 reads the disc-1 hill at W/E/W2/E2 (+-0.15): 5.198 / 5.397 / 4.888 / 5.460
    R2 disc 4 reads the SAME hill (+-0.15) -- session 6's crack read E 1.746, E2 2.086 (stock) before its manual replay
    R3 on disc 4, walking west from E crosses x = 256 (REACHED 5u; session 6: refused at 256.03)
A step a random battle interrupts is NOT JUDGED (its check is skipped and named), never read as evidence.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent.parent / "tools"))
sys.path.insert(0, str(HERE))
from harness import HarnessError                      # noqa: E402

import r3_build as RB                                  # noqa: E402  (the stages and the sky ground query)

PHASE = os.environ.get("R3_PHASE", "guard")
GAME = RB.A.GAME
LAB = GAME / "FF9CustomMap-lab"
BUILD = json.loads((HERE / "out" / "r3_build.json").read_text(encoding="utf-8"))
TOL = 0.05
TOL_WALK = 0.15

# guard route: Burmecia/Entrance (750)
BURMECIA, SCEN = 750, 4000
EXIT21 = [[882, -1228], [-597, -1102], [-523, -175], [466, -322]]     # entry 21 SetRegion (the world exit)
DOOR20 = [[-312, 4000], [-12, 4000], [200, 1747], [-220, 1747]]       # entry 20 SetRegion (-> field 751)
EXIT_GOAL = (-105.0, -688.0)                                         # pathfind.region_goal(stock walkmesh, EXIT21)
LANDING = tuple(BUILD["landing"])
STORED_Y = BUILD["stored_y"]
GUARD_STAGES = ("stock", "A_lower3", "A_raise1", "A_raise4")
# 6603 route (beach, replay): field 6603 FARSHORE's door, proven in sessions 4-7 and round 2
FARSHORE = 6603
FS_EXIT = (400.0, -1400.0)
FS_DOOR = [[285, -352], [875, -460], [424, -2944], [-166, -2836]]
FS_LANDING = (68.0, -444.0)

_RECORD: dict = {"phase": PHASE, "build": {k: v.get("files") for k, v in BUILD["stages"].items()}}


def _save(g):
    try:
        (g.run_dir / f"r3_{PHASE}.json").write_text(json.dumps(_RECORD, indent=1, default=str), encoding="utf-8")
    except Exception as err:                                            # noqa: BLE001
        print(f"[r3] could not write the record: {err}")


def here(g) -> dict:
    st = g.state
    return {"x": st.world_x, "z": st.world_z, "y": st.world_y, "world": st.world_id, "ui": st.ui_state,
            "scenario": st.scenario, "frame": st.frame, "field": st.field_id}


def set_lab(stage: str | None) -> dict:
    """Empty the lab's WorldMap tree, then copy ``stage``'s in (None = leave it empty). Returns the files placed."""
    root = LAB / "FF9_Data"
    if root.exists():
        shutil.rmtree(root)
    placed = {}
    if stage:
        src = RB.STAGE / stage / "FF9_Data"
        shutil.copytree(src, root)
        placed = RB.stage_files(LAB)
        want = BUILD["stages"][stage]["files"]
        if placed != want:
            raise HarnessError(f"r3: the lab does not hold stage {stage} byte for byte: {placed} != {want}")
    return placed


def calibrate(g, hazards, rewarp, prior_field: int | None = None):
    """``prior_field``: seed the probe order from that stock field's own camera twist (Session.key_prior) -- 750's
    spawn is ~56u from its world exit, so a blind probe is refused there (the 2026-10-08 first launch)."""
    prior = g.key_prior(prior_field) if prior_field is not None else None
    for attempt in range(3):
        try:
            g.calibrate_axes(hazards=hazards, recalibrate=attempt > 0, prior=prior)
            return
        except HarnessError as err:
            _RECORD.setdefault("calibration_retries", []).append(str(err)[:200])
            if attempt == 2:
                raise
            rewarp()
            g.wait_frames(90)


def rest(g, *, still_frames: int = 30, eps: float = 0.004, timeout: float = 20.0) -> list:
    """With NO input, sample world x/z/y until all three are unchanged across ``still_frames`` ADVANCING frames;
    returns every sample. ⚠ The first WorldHUD frame comes BEFORE the world's synchronous all-block load: the next
    frame arrived 4.4 s later in the 2026-10-08 run (`w_frameMainRoutine` -> LoadBlocks, then the sky cast), so a
    wall-clock stillness test read that one stalled frame as "at rest" (G1 judged the pre-load y 3.086; the first
    post-load frame read the lowered ground). Stillness is counted in frames, from a frame after the first."""
    samples, base, base_frame = [], None, None
    t_end = time.time() + timeout
    first_frame = None
    while time.time() < t_end:
        st = g.state
        if not st.on_world or st.world_x is None:
            break
        cur = (st.world_x, st.world_z, st.world_y if st.world_y is not None else 0.0)
        if first_frame is None:
            first_frame = st.frame
        if not samples or st.frame != samples[-1]["frame"]:
            samples.append({"t": round(time.time(), 3), "frame": st.frame, "x": cur[0], "z": cur[1],
                            "y": st.world_y})
        if st.frame > first_frame:
            if base is None or any(abs(a - b) > eps for a, b in zip(cur, base)):
                base, base_frame = cur, st.frame
            elif st.frame - base_frame >= still_frames:
                break
        time.sleep(0.03)
    return samples


def move_test(g, stage_path) -> dict:
    """Press up/right/down/left (12 frames each, one request) until one moves him >= 1u, or takes him off the map.
    Judges the height he ends at against the sky query on the stage."""
    out = {"tries": []}
    for b in ("up", "right", "down", "left"):
        s0 = here(g)
        epoch0 = g.state.battle_epoch
        g.walk(b, 12)
        st = g.world_settle()
        if not st.on_world or st.in_battle or st.battle_epoch > epoch0:
            out["tries"].append({"button": b, "left_world": st.ui_state, "field": st.field_id,
                                 "battle": bool(st.in_battle or st.battle_epoch > epoch0)})
            out["outcome"] = "battle" if (st.in_battle or st.battle_epoch > epoch0) else "left_world"
            return out
        s1 = here(g)
        d = math.hypot(s1["x"] - s0["x"], s1["z"] - s0["z"])
        gr = RB.ground(stage_path, 1, s1["x"], s1["z"])
        out["tries"].append({"button": b, "from": s0, "to": s1, "moved": round(d, 3), "ground": gr["y"],
                             "topo": gr["topo"]})
        if d >= 1.0:
            out["outcome"] = "moved"
            out["y_vs_ground"] = None if gr["y"] is None or s1["y"] is None else round(s1["y"] - gr["y"], 4)
            return out
    out["outcome"] = "frozen"
    return out


# ------------------------------------------------------------------------------------------------- GUARD
def to_burmecia(g, first: bool):
    """Stand him in field 750 at scenario SCEN: a new game + warp, a world warp from the map, or already there (a
    move test that stepped onto the entrance tiles took him in)."""
    if first:
        g.newgame()
        g.warp(BURMECIA, scenario=SCEN)
    elif g.state.ui_state == "WorldHUD":
        g.world_warp(BURMECIA, scenario=SCEN)
    else:
        g.wait_playable(timeout=60)
        if g.state.field_id != BURMECIA:
            raise HarnessError(f"r3 guard: expected field {BURMECIA} or the world map, found {here(g)}")


def walk_out_burmecia(g):
    g.wait_frames(45)
    calibrate(g, [EXIT21, DOOR20], lambda: g.warp(BURMECIA, scenario=SCEN), prior_field=BURMECIA)
    g.walk_to(*EXIT_GOAL, strict=False, halt_on_transition=True)
    g.wait_world(timeout=90)


def run_guard(g):
    LAB.mkdir(exist_ok=True)
    _RECORD["guard"] = []
    for i, stage in enumerate(GUARD_STAGES):
        rec = {"stage": stage}
        _RECORD["guard"].append(rec)
        to_burmecia(g, first=i == 0)
        # swap the lab while he stands in the FIELD: the next world load reads the new files
        rec["lab"] = set_lab(None if stage == "stock" else stage)
        walk_out_burmecia(g)
        samples = rest(g)
        rec["rest"] = {"first": samples[0] if samples else None, "last": samples[-1] if samples else None,
                       "n": len(samples), "world": g.state.world_id, "scenario": g.state.scenario}
        stage_path = None if stage == "stock" else RB.STAGE / stage
        want = BUILD["guard"]["stock"]["y"] if stage == "stock" else BUILD["guard"][stage]["landing"]["y"]
        rec["predict"] = {"H-SKY": want, "H-RECORD": STORED_Y}
        last = rec["rest"]["last"] or {}
        at_landing = (last.get("x") is not None
                      and math.hypot(last["x"] - LANDING[0], last["z"] - LANDING[1]) <= TOL)
        g.check(at_landing, f"G{i} {stage}: the exit set him down at the stored landing (963.234, -718.910)",
                json.dumps(last))
        y = last.get("y")
        if stage == "stock":
            g.check(y is not None and abs(y - want) <= TOL,
                    f"G0 stock: at rest y {want} (the ground; stored {STORED_Y}) -- the instrument control",
                    json.dumps(rec["rest"]))
        else:
            sky = y is not None and abs(y - want) <= TOL
            record = y is not None and abs(y - STORED_Y) <= TOL
            rec["verdict_at_rest"] = "H-SKY" if sky else ("H-RECORD" if record else "neither")
            g.check(sky, f"G{i} {stage}: at rest, before any input, y is the NEW ground {want} (H-SKY), not the "
                         f"stored {STORED_Y} (H-RECORD)", json.dumps({"y": y, "verdict": rec["verdict_at_rest"]}))
        if stage == "A_raise4":
            g.wait_frames(30)
            g.shot("G3-raise4-landed")
        mv = move_test(g, stage_path)
        rec["move"] = mv
        if mv["outcome"] == "battle":
            g.note(f"G{i} {stage}: a random battle interrupted the move test -- NOT JUDGED")
            g.check(False, f"G{i} {stage}: move test interrupted by a battle (not judged)", json.dumps(mv["tries"]))
            _save(g)
            return
        moved = mv["outcome"] in ("moved", "left_world")
        g.check(moved, f"G{i} {stage}: he can move from the landing (H-RECORD at +3.6: frozen in all four "
                       f"directions)", json.dumps(mv["tries"]))
        if mv["outcome"] == "moved":
            g.check(mv.get("y_vs_ground") is not None and abs(mv["y_vs_ground"]) <= TOL_WALK,
                    f"G{i} {stage}: after the step his y is the ground under him (+-{TOL_WALK})",
                    json.dumps(mv["tries"][-1]))
        _save(g)
    set_lab(None)


# ------------------------------------------------------------------------------------------------- BEACH
BEACH_LINES = {476.28: -1120.28, 479.64: -1120.18, 480.18: -1120.36}
TERRAIN_Z = -1117.0


def farshore_out(g, *, first: bool, scenario: int | None = None):
    def rewarp():
        if scenario is not None:
            g.warp(FARSHORE, scenario=scenario)
        else:
            g.warp(FARSHORE)
    if first:
        g.newgame()
        rewarp()
    else:
        g.world_warp(FARSHORE, scenario=scenario)
    g.wait_frames(45)
    calibrate(g, [FS_DOOR], rewarp)
    g.walk_to(*FS_EXIT, strict=False, halt_on_transition=True)
    g.wait_world(timeout=90)
    g.world_settle()


def run_beach(g):
    farshore_out(g, first=True)
    face = g.world_face(90.0, home=FS_LANDING, tolerance=2.0)
    g.teleport(476.28, -1124.0)
    g.world_settle()
    g.wait_frames(90)
    g.shot("beach-look")
    _RECORD["north"], _RECORD["south"] = [], []
    for x, z0 in BEACH_LINES.items():
        g.teleport(x, z0)
        g.world_settle()
        g.wait_frames(15)
        st0 = here(g)
        w = g.world_approach(90.0, 3.0, speed=face.get("speed"), burst_frames=6)
        _RECORD["north"].append({"x": x, "start": st0, "outcome": w["outcome"], "progress": w.get("progress"),
                                 "y_max": w.get("y_max"), "end": here(g)})
        if w["outcome"] == "left_world":
            g.note(f"beach north x {x}: left the world (a battle?) -- line not judged")
            break
    face2 = g.world_face(270.0, home=FS_LANDING, tolerance=2.0)
    for x in BEACH_LINES:
        g.teleport(x, TERRAIN_Z)
        g.world_settle()
        g.wait_frames(15)
        st0 = here(g)
        w = g.world_approach(270.0, 4.0, speed=face2.get("speed"), burst_frames=6)
        _RECORD["south"].append({"x": x, "start": st0, "outcome": w["outcome"], "progress": w.get("progress"),
                                 "end": here(g)})
        if w["outcome"] == "left_world":
            g.note(f"beach south x {x}: left the world (a battle?) -- line not judged")
            break
    north = [r for r in _RECORD["north"] if r["outcome"] != "left_world"]
    south = [r for r in _RECORD["south"] if r["outcome"] != "left_world"]
    g.check(len(north) == 3 and all(r["outcome"] == "reached" for r in north),
            "K1 beach -> terrain (north 3u) REACHED at every line (session 5 at +3: refused at all three)",
            "; ".join(f"x {r['x']}: {r['outcome']} {r['progress']}u y {r['start']['y']}->{r['end']['y']}" for r in north))
    g.check(len(south) == 3 and all(r["outcome"] == "reached" for r in south),
            "K2 terrain -> beach (south 4u) REACHED at every line",
            "; ".join(f"x {r['x']}: {r['outcome']} {r['progress']}u" for r in south))
    g.teleport(478.0, -1128.0)
    g.world_settle()
    g.wait_frames(90)
    g.shot("beach-after")


# ------------------------------------------------------------------------------------------------- REPLAY
def readout(g, tag) -> dict:
    rows = {}
    for k, p in RB.CRACK_PTS.items():
        g.teleport(*p)
        g.world_settle()
        g.wait_frames(20)
        rows[k] = {"y": g.state.world_y, "pred_disc1": BUILD["replay"][k]["disc1"],
                   "pred_disc4": BUILD["replay"][k]["disc4"], "disc4_stock": BUILD["replay"][k]["disc4_stock"]}
    _RECORD[tag] = {"world": g.state.world_id, "scenario": g.state.scenario, "rows": rows}
    return rows


def run_replay(g):
    farshore_out(g, first=True)
    r1 = readout(g, "disc1")
    g.check(all(r["y"] is not None and abs(r["y"] - r["pred_disc1"]) <= TOL_WALK for r in r1.values()),
            "R1 disc 1 reads the hill at W/E/W2/E2", json.dumps(r1))
    farshore_out(g, first=False, scenario=11101)
    r4 = readout(g, "disc4")
    g.check(all(r["y"] is not None and abs(r["y"] - r["pred_disc4"]) <= TOL_WALK for r in r4.values()),
            "R2 disc 4 reads the SAME hill (replayed; the crack read E/E2 at stock 1.75/2.09)", json.dumps(r4))
    face = g.world_face(180.0, home=FS_LANDING, tolerance=2.0)
    g.teleport(*RB.CRACK_PTS["E"])
    g.world_settle()
    g.wait_frames(15)
    w = g.world_approach(180.0, 5.0, speed=face.get("speed"), burst_frames=6)
    _RECORD["cross_west"] = {"outcome": w["outcome"], "progress": w.get("progress"), "end": here(g),
                             "trace": w.get("trace")}
    if w["outcome"] == "left_world":
        g.note("R3: left the world mid-walk (a battle?) -- not judged")
    else:
        g.check(w["outcome"] == "reached" and g.state.world_x < 255.0,
                "R3 disc 4: walking west from E crosses x = 256 (session 6's crack: refused at 256.03)",
                json.dumps({k: v for k, v in _RECORD["cross_west"].items() if k != "trace"}))
    g.teleport(257.63, -880.0)
    g.world_settle()
    g.wait_frames(90)
    g.shot("replay-disc4")


def run(g):
    g.note(f"r3_session: phase {PHASE}")
    if not LAB.is_dir() and PHASE != "guard":
        raise HarnessError(f"r3: {LAB} is missing -- the orchestrator copies the stage in before a {PHASE} launch")
    mark = g.log_mark()
    try:
        {"guard": run_guard, "beach": run_beach, "replay": run_replay}[PHASE](g)
    finally:
        try:
            _RECORD["exceptions"] = [str(e) for e in g.exceptions_since(mark)][:20]
        except Exception as err:                                        # noqa: BLE001 -- an instrument
            _RECORD["exceptions_error"] = repr(err)
        _save(g)
