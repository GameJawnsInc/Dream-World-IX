"""In-game ROUND 4 (2026-10-08): THE JULY DALI FREEZE, and an edit the relaxed slope gate newly allows. DEPLOYS into
the scratch mod folder FF9CustomMap-lab ONLY (owner's go 2026-10-08, "in-game session"; the lab first in Memoria.ini
FolderNames for the round). The lab starts EMPTY and this scenario swaps r4_build's stages in between Dali visits
(the engine File.Exists-checks every override at each world load): stock, D_raise4, D_hill24, D_hill24_july -- the
one predicted to trap him last.
RUN:   py tools/play.py studies/terrain-malleability/ingame/r4_session.py --label r4-dali
SCORE: py studies/terrain-malleability/ingame/r3_post.py <run dir>   (the lab load lines)

ROUTE: newgame -> warp(350 Dali/Village Road, scenario 9500: Zidane, the revisit cast, the world exit (entry 31) armed
and NOT one of its story windows 2600-2639 / 2730-2819) -> calibrate (prior = 350's own twist: the spawn is ~30u from
the exit) -> walk into entry 31 -> the world. The exit stores (1102.855, 26.574, -812.359).

REGISTERED PREDICTIONS (out/r4_build.json; the July edit is a reconstruction -- see r4_build.py):
  R1 every stage: at rest, before any input (stillness in advancing frames), y is the stage's ground at the landing
     (+-0.05): stock 26.578, D_raise4 29.790 (+3.2 over the stored height), D_hill24 43.746 (+17.2),
     D_hill24_july 47.592 (+21.0) -- the load's sky cast again (RESULTS section 16), now at Dali itself
  R2 every stage: he moves off the landing, and his y is then the ground under him (+-0.15). D_raise4 is an edit the
     slope gate refused before defect 23 (a 90-deg stock sliver in the town footprint)
  THE WALK ONTO THE PLATE. The town's walkable Object plate (about x -6..+4, z +6..+12 from the landing, at 26.5)
  fills a HOLE in the Terrain (the object pose law); Dali's entrance tiles ring it on the north and west, so the walk
  comes from the east: camera faced WEST (180) at HOME (+12, -4 from the landing: no tile, object or blocked ground
  within 13u in any stage), then from START (+10, +8) 8u west. A long drop collapses the step (3D-normalised:
  RESULTS section 6's creep), so a walk that reads "blocked" is held on 150 more frames before it is judged.
  Escape holds from where it ends, in sequence, 30 frames each: down (east), left, right, up (west, toward the tiles).
  R3 D_hill24_july (no seam pins: the hole's rim rose 21-24u, the plate did not): the walk ends ON the plate
     (y < 27.5) and no escape hold that stays on the map brings him above y 30 -- TRAPPED in a 21u shaft: THE
     CANDIDATE FOR THE JULY FREEZE (his re-exit from Dali sets him on the hilltop beside it; the July notes also
     record "entrance props sunk in a visible pit"). A hold that walks him into a field is an escape, not a trap
  R4 D_hill24 (today's kit holds the rim at the plate's height): the walk ends on the plate, and an escape hold
     climbs above y 28: NOT trapped
  stock / D_raise4: the walk is recorded as the instrument control (flat ground: no trap to judge)
A step a random battle interrupts is NOT JUDGED (named, never read as evidence).
ENCOUNTERS OFF: launch 1 (.harness-runs/20261008-185811-r4-dali, R1+R2 stock passed) lost the run to a random battle
during the facing probes near Dali. For the session the lab ALSO carries `world-encounter-frequency --peaceful`
(encratio 0 in every free-roam dispatcher, all languages; it reads stock, so the Southern Ring's dispatcher edits are
shadowed for the launch -- nothing here uses them). It touches no geometry, and the stage swaps only replace the lab's
FF9_Data tree.
"""
from __future__ import annotations

import json
import math
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent.parent / "tools"))
sys.path.insert(0, str(HERE))
from harness import HarnessError                      # noqa: E402

import r3_session as R3                                # noqa: E402  (rest, move_test, calibrate, here)
import r4_build as R4                                  # noqa: E402

RB = R4.RB
LAB = RB.A.GAME / "FF9CustomMap-lab"
BUILD = json.loads((HERE / "out" / "r4_build.json").read_text(encoding="utf-8"))
DALI, SCEN = 350, 9500
EXIT31 = [[544, -991], [-596, -991], [-686, -451], [423, -421]]
DOOR18 = [[569, 195], [662, -63], [438, -134], [253, -87], [325, 122]]
DOOR19 = [[-1285, 441], [-1330, 263], [-748, 109], [-600, 257], [-696, 397]]
EXIT_GOAL = (-218.0, -715.0)                            # pathfind.region_goal(stock walkmesh 350, EXIT31)
LANDING = tuple(BUILD["landing"])
STORED_Y = BUILD["stored_y"]
STAGES = ("stock", "D_raise4", "D_hill24", "D_hill24_july")
TOL, TOL_WALK = 0.05, 0.15
_RECORD: dict = {"build": {k: v["files"] for k, v in BUILD["stages"].items()}, "phases": []}


def _save(g):
    try:
        (g.run_dir / "r4_dali.json").write_text(json.dumps(_RECORD, indent=1, default=str), encoding="utf-8")
    except Exception as err:                                            # noqa: BLE001
        print(f"[r4] could not write the record: {err}")


def set_lab(stage: str | None) -> dict:
    root = LAB / "FF9_Data"
    if root.exists():
        shutil.rmtree(root)
    if not stage:
        return {}
    shutil.copytree(R4.STAGE / stage / "FF9_Data", root)
    placed, want = RB.stage_files(LAB), BUILD["stages"][stage]["files"]
    if placed != want:
        raise HarnessError(f"r4: the lab does not hold stage {stage} byte for byte")
    return placed


def to_dali(g, first: bool):
    if first:
        g.newgame()
        g.warp(DALI, scenario=SCEN)
    elif g.state.ui_state == "WorldHUD":
        g.world_warp(DALI, scenario=SCEN)
    else:
        g.wait_playable(timeout=60)
        if g.state.field_id != DALI:
            raise HarnessError(f"r4: expected field {DALI} or the world map, found {R3.here(g)}")


def walk_out(g):
    g.wait_frames(45)
    R3.calibrate(g, [EXIT31, DOOR18, DOOR19], lambda: g.warp(DALI, scenario=SCEN), prior_field=DALI)
    g.walk_to(*EXIT_GOAL, strict=False, halt_on_transition=True)
    g.wait_world(timeout=90)


def left(st, epoch0) -> bool:
    return (not st.on_world) or st.in_battle or st.battle_epoch > epoch0


HOME = (LANDING[0] + 12.37, LANDING[1] - 3.79)      # r4 prep: clear of tiles/objects/blocked ground within 13u
START = (LANDING[0] + 10.37, LANDING[1] + 8.21)     # 8u east of the plate, on open ground in every stage


def walk_onto_plate_and_escape(g, rec) -> str:
    """Face west at HOME, walk 8u west from START onto the plate (held on through a creep), then four escape holds.
    Returns 'ok' or why it stopped."""
    epoch0 = g.state.battle_epoch
    face = g.world_face(180.0, home=HOME, tolerance=4.0)
    rec["face"] = {"heading": face.get("heading"), "speed": face.get("speed")}
    g.teleport(*START)
    g.world_settle()
    g.wait_frames(15)
    rec["start"] = R3.here(g)
    w = g.world_approach(180.0, 8.0, speed=face.get("speed"), burst_frames=6, max_bursts=30)
    rec["west"] = {"outcome": w["outcome"], "progress": w.get("progress"), "end": R3.here(g),
                   "trace": [{k: r.get(k) for k in ("x", "z", "y")} for r in w.get("trace", [])]}
    if w["outcome"] == "left_world" or left(g.state, epoch0):
        return "left the world on the walk west"
    if w["outcome"] == "blocked":                                  # a creep at a long drop: hold on before judging
        g.walk("up", 150)
        st = g.world_settle()
        if left(st, epoch0):
            return "left the world while holding on"
        rec["west"]["held_on"] = R3.here(g)
    end = R3.here(g)
    rec["west"]["final"] = end
    holds = []
    for b in ("down", "left", "right", "up"):
        g.walk(b, 30)
        st = g.world_settle()
        if left(st, epoch0):
            holds.append({"button": b, "left_world": st.ui_state, "field": st.field_id,
                          "battle": bool(st.in_battle or st.battle_epoch > epoch0)})
            break
        h = R3.here(g)
        holds.append({"button": b, "to": h, "from_end": round(math.hypot(h["x"] - end["x"], h["z"] - end["z"]), 2)})
    rec["escape"] = holds
    rec["escape_max_y"] = max((h["to"]["y"] for h in holds if h.get("to") and h["to"]["y"] is not None),
                              default=None)
    rec["escape_left_world"] = next((h for h in holds if h.get("left_world")), None)
    return "ok"


def run(g):
    g.note("r4_session: the July Dali freeze + a newly allowed edit")
    LAB.mkdir(exist_ok=True)
    mark = g.log_mark()
    try:
        for i, stage in enumerate(STAGES):
            rec = {"stage": stage}
            _RECORD["phases"].append(rec)
            to_dali(g, first=i == 0)
            rec["lab"] = set_lab(None if stage == "stock" else stage)
            walk_out(g)
            samples = R3.rest(g)
            first, last = (samples[0], samples[-1]) if samples else ({}, {})
            want = BUILD["stock"]["landing"]["y"] if stage == "stock" else BUILD[stage]["landing"]["y"]
            rec["rest"] = {"first": first, "last": last, "world": g.state.world_id, "scenario": g.state.scenario,
                           "predict": want}
            y = last.get("y")
            at = last.get("x") is not None and math.hypot(last["x"] - LANDING[0], last["z"] - LANDING[1]) <= TOL
            g.check(at and y is not None and abs(y - want) <= TOL,
                    f"R1 {stage}: the exit set him down at the landing, at rest on the ground {want} "
                    f"(stored {STORED_Y})", json.dumps(rec["rest"]))
            stage_path = None if stage == "stock" else R4.STAGE / stage
            mv = R3.move_test(g, stage_path)
            rec["move"] = mv
            if mv["outcome"] == "battle":
                g.check(False, f"R2 {stage}: a battle interrupted the move test (NOT JUDGED)", json.dumps(mv))
                _save(g)
                return
            g.check(mv["outcome"] in ("moved", "left_world")
                    and (mv["outcome"] == "left_world" or abs(mv.get("y_vs_ground") or 9) <= TOL_WALK),
                    f"R2 {stage}: he moves off the landing and stands on the ground", json.dumps(mv["tries"]))
            if g.state.ui_state != "WorldHUD":                     # stepped onto Dali's tiles (0.4u off the landing)
                g.wait_playable(timeout=60)
                if g.state.field_id != DALI:
                    g.note(f"{stage}: the move test entered field {g.state.field_id}: no plate walk")
                    continue
                walk_out(g)                                        # same lab: back to the landing, then the walk
                rec["re_exit"] = R3.here(g)
            g.teleport(*HOME)                                      # never start a facing probe beside the tiles
            g.world_settle()
            why = walk_onto_plate_and_escape(g, rec)
            rec["walk"] = why
            if why != "ok":
                g.note(f"{stage}: {why} -- the walk onto the plate is NOT JUDGED")
            elif stage == "D_hill24_july":
                end_y = rec["west"]["final"]["y"]
                esc = rec["escape_left_world"]
                g.check(end_y is not None and end_y < 27.5 and not esc and (rec["escape_max_y"] or 99) <= 30.0,
                        "R3 D_hill24_july: the walk drops him onto the plate at the bottom of the shaft and no escape "
                        "hold gets him out -- TRAPPED (the July freeze candidate)",
                        json.dumps({"west": {k: v for k, v in rec["west"].items() if k != "trace"},
                                    "escape": rec["escape"]}))
                g.shot("R3-july-trapped")
            elif stage == "D_hill24":
                end_y = rec["west"]["final"]["y"]
                g.check(end_y is not None and end_y < 27.5 and (rec["escape_max_y"] or 0) > 28.0,
                        "R4 D_hill24: the walk ends on the plate and an escape hold climbs above y 28 -- NOT trapped "
                        "(the pins keep the plate's rim at its height)",
                        json.dumps({"west": {k: v for k, v in rec["west"].items() if k != "trace"},
                                    "escape": rec["escape"]}))
                g.shot("R4-today-plate")
            if g.state.ui_state == "WorldHUD":
                g.teleport(*HOME)                                  # out of any trap: the next stage leaves from here
                g.world_settle()
            _save(g)
    finally:
        set_lab(None)
        try:
            _RECORD["exceptions"] = [str(e) for e in g.exceptions_since(mark)][:20]
        except Exception as err:                                        # noqa: BLE001
            _RECORD["exceptions_error"] = repr(err)
        _save(g)
