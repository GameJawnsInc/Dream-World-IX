"""In-game ROUND 9 (2026-10-09): the disc-4 replay of an in-place coast morph -- `world-transplant --in-place
--cliff-bump` on (7,13), a coast disc 4 redrew. DEPLOYS into the scratch mod folder FF9CustomMap-lab ONLY (first in
FolderNames for the round). The lab starts EMPTY; this scenario swaps r9_build's file sets in while the player is inside
field 6603 (FARSHORE), so each walk out is a fresh world load.
RUN:   py tools/play.py studies/terrain-malleability/ingame/r9_session.py --label r9-coast-disc4

ROUTE: newgame -> warp 6603 -> walk out (world 9011, disc 1) -> face north on the landing lawn -> teleport 6u south of
the cliff's top edge at (484.37, -850) -> walk 10u north -> teleport onto R and X -> back to 6603 -> ... ; the two
disc-4 stages warp to 6603 at scenario 11101, so its door leads to world 9008 on disc 4 (round 3's route).
ENCOUNTERS OFF: g.no_encounters() (engine s94, the F4 booster) after newgame and after every world load.

REGISTERED PREDICTIONS (out/r9_build.json):
  d1_stock  the walk north stops at the stock edge, z -844.0; R reads the cliff face, y 0.71
  d1_bump   it stops 2.5u further north, z -841.5; R reads the lawn, y 4.84
  d4_old    (the kit's output before this fix) disc 4 stays stock: stops at z -844.0, R 0.71
  d4_bump   (this fix) disc 4 is bumped too: stops at z -841.5, R 4.84; X reads disc 4's OWN ground (y 4.65, rock),
            not disc 1's (3.42) -- the replay edited disc 4's ground, it did not copy disc 1's
  X on every stage: disc 1 reads 3.42, disc 4 reads 4.65 (the bump changes neither)
  Memoria.log, per world load: the lab's Block[7][13] Terrain + Sea4 bound for the stage's disc in d1_bump (Disc1) and
  d4_bump (Disc4) only; no lab part in d1_stock or d4_old (OLD's Disc1 files are never read on disc 4); 0 exceptions
  Walk tolerance 0.35u on the stop; readouts 0.15u.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent.parent / "tools"))
sys.path.insert(0, str(HERE))
from harness import HarnessError                      # noqa: E402
from harness.logs import read_from                    # noqa: E402

import r3_session as R3                                # noqa: E402  (calibrate, here, FARSHORE's exit, the landing)

GAME = R3.GAME
LAB = GAME / "FF9CustomMap-lab"
BUILD = json.loads((HERE / "out" / "r9_build.json").read_text(encoding="utf-8"))
FILES = HERE / "out" / "r9_stage" / "files"
STAGES = list(BUILD["stages"])
DISC4_SCENARIO = 11101
TOL_STOP = 0.35
TOL_Y = 0.15
LOADED = re.compile(r"\[WorldMeshOverride\] loaded 'WorldMap/Disc(\d)/0_1/r13/Block\[7\]\[13\] ([A-Za-z0-9]+)' "
                    r"from ([^\n]+)")
_RECORD: dict = {"build": BUILD["files"], "stages": []}
_STAGE = [""]


def _save(g):
    try:
        (g.run_dir / "r9_coast_disc4.json").write_text(json.dumps(_RECORD, indent=1, default=str), encoding="utf-8")
    except Exception as err:                                            # noqa: BLE001
        print(f"[r9] could not write the record: {err}")


def set_lab(fset: str | None) -> list:
    LAB.mkdir(exist_ok=True)
    for child in LAB.iterdir():
        shutil.rmtree(child) if child.is_dir() else child.unlink()
    for rel, want in (BUILD["files"][fset].items() if fset else ()):
        dst = LAB / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(FILES / fset / rel, dst)
        if hashlib.sha256(dst.read_bytes()).hexdigest() != want:
            raise HarnessError(f"r9: the lab does not hold {fset}/{rel} byte for byte")
    return sorted(BUILD["files"][fset]) if fset else []


def to_field(g, first: bool, disc: int):
    scen = DISC4_SCENARIO if disc == 4 else None
    if first:
        g.newgame()
        g.no_encounters()
        g.warp(R3.FARSHORE, scenario=scen) if scen else g.warp(R3.FARSHORE)
    elif g.state.ui_state == "WorldHUD":
        g.world_warp(R3.FARSHORE, scenario=scen)
    else:
        g.warp(R3.FARSHORE, scenario=scen) if scen else g.warp(R3.FARSHORE)
    g.wait_playable(timeout=60)
    if g.state.field_id != R3.FARSHORE:
        raise HarnessError(f"r9: expected field {R3.FARSHORE}, found {R3.here(g)}")


def walk_out(g, disc: int):
    def rewarp():
        g.warp(R3.FARSHORE, scenario=DISC4_SCENARIO) if disc == 4 else g.warp(R3.FARSHORE)
    g.wait_frames(45)
    R3.calibrate(g, [R3.FS_DOOR], rewarp)
    g.walk_to(*R3.FS_EXIT, strict=False, halt_on_transition=True)
    g.wait_world(timeout=90)
    g.world_settle()
    g.no_encounters()          # s94, the F4 booster: round 8's first try died in a random battle


def log_since(mark) -> str:
    text = ""
    for path, offset in mark.values():
        try:
            text += read_from(Path(path), int(offset))
        except OSError:
            pass
    return text


def readout(g, p) -> dict:
    g.teleport(*p)
    g.world_settle()
    g.wait_frames(20)
    return {"at": list(p), "y": g.state.world_y, "x": g.state.world_x, "z": g.state.world_z}


def walk_north(g) -> dict:
    face = g.world_face(BUILD["bearing"], home=R3.FS_LANDING, tolerance=2.0)
    g.teleport(*BUILD["start"])
    g.world_settle()
    g.wait_frames(30)
    look = str(g.shot(f"r9-{_STAGE[0]}-look"))
    got = g.world_approach(BUILD["bearing"], 10.0, speed=face.get("speed"), burst_frames=6)
    trace = [{k: r.get(k) for k in ("x", "z", "y", "progress", "ui")} for r in got.get("trace", [])]
    out = {"outcome": got["outcome"], "progress": got.get("progress"), "trace": trace, "look": look,
           "end": R3.here(g)}
    if got["outcome"] != "left_world":
        g.wait_frames(20)
        out["edge_shot"] = str(g.shot(f"r9-{_STAGE[0]}-edge"))
    return out


def run(g):
    g.note("r9_session: an in-place cliff bump on (7,13) reaches disc 4 (world-transplant --in-place, disc-4 replay)")
    mark0 = g.log_mark()
    try:
        for i, stage in enumerate(STAGES):
            spec = BUILD["stages"][stage]
            disc = spec["disc"]
            rec = {"stage": stage, "files": spec["files"], "disc": disc}
            _STAGE[0] = stage
            _RECORD["stages"].append(rec)
            to_field(g, first=i == 0, disc=disc)
            rec["placed"] = set_lab(spec["files"])
            mark = g.log_mark()
            walk_out(g, disc)
            rec["at"] = R3.here(g)
            rec["world"], rec["scenario"] = g.state.world_id, g.state.scenario
            w = walk_north(g)
            rec["walk"] = w
            if w["outcome"] == "left_world":
                g.note(f"{stage}: the walk left the world (a battle?) -- not judged")
            else:
                edge = spec["walk"]["edge_z"]
                end_z = w["end"].get("z")
                g.check(w["outcome"] == "blocked" and end_z is not None and abs(end_z - edge) <= TOL_STOP,
                        f"{stage}: the walk north stops at the cliff's top edge, z {edge} (+-{TOL_STOP})",
                        json.dumps({k: v for k, v in w.items() if k != "trace"}))
            rec["R"] = readout(g, BUILD["R"])
            rec["X"] = readout(g, BUILD["X"])
            for key in ("R", "X"):
                want = spec[key]["y"]
                got = rec[key]["y"]
                g.check(got is not None and abs(got - want) <= TOL_Y,
                        f"{stage}: {key} reads y {want} (+-{TOL_Y}; topograph {spec[key]['topo']})",
                        json.dumps(rec[key]))
            log = log_since(mark)
            loads = [(int(d), part, src.strip()) for d, part, src in LOADED.findall(log)]
            rec["loads"] = loads
            lab = sorted(part for d, part, src in loads if "FF9CustomMap-lab" in src and d == disc)
            other = sorted({(d, part) for d, part, src in loads if "FF9CustomMap-lab" in src and d != disc})
            g.check(lab == spec["lab_parts"] and not other,
                    f"{stage}: Memoria.log binds the lab's Block[7][13] {spec['lab_parts'] or 'nothing'} on disc {disc}",
                    json.dumps({"lab": lab, "other_disc": other, "loads": loads}))
            _save(g)
    finally:
        set_lab(None)
        try:
            _RECORD["exceptions"] = [str(e) for e in g.exceptions_since(mark0)][:20]
        except Exception as err:                                        # noqa: BLE001
            _RECORD["exceptions_error"] = repr(err)
        _save(g)
