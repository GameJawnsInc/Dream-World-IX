"""In-game ROUND 8 (2026-10-09): entrances that change with the story -- `world-forms --entrance2` on engine s92 (no DLL
change). DEPLOYS into the scratch mod folder FF9CustomMap-lab ONLY (first in FolderNames for the round). The lab starts
EMPTY; this scenario swaps r8_build's file sets in while the player is inside field 6603 (FARSHORE), so each walk out
is a fresh world load.
RUN:   py tools/play.py studies/terrain-malleability/ingame/r8_session.py --label r8-entrances

ENCOUNTERS OFF (g.no_encounters, engine s94 = the F4 cheat): the first try (run 20261009-125210) met a random battle
on the walk to the tile and died at level 1.
ROUTE: newgame -> warp 6603 -> walk out (world 9011) -> face south on the landing lawn -> teleport 5u north of the Ice
Cavern tile on (18,12) -> walk 9u south onto it -> shot -> Confirm -> (entered: field 300) -> warp 6603 -> swap the
lab, set flag 8712 -> walk out -> ...

REGISTERED PREDICTIONS (out/r8_build.json):
  stock, off_f0, only_f1   on the tile, the "Enter with X" prompt shows and Confirm ENTERS field 300 (Ice Cavern)
  off_f1, only_f0          the walk crosses onto the tile (z <= -795.5), no prompt, Confirm does nothing: he STAYS
  Memoria.log, per world load: "[CustomFormCells] armed Block[18][12]" in every stage but stock; "switched to form 2"
  exactly in off_f1 and only_f1; the Terrain2 bound from the lab in every armed stage, the form-1 Terrain only with
  ONLY; 0 exceptions
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
BUILD = json.loads((HERE / "out" / "r8_build.json").read_text(encoding="utf-8"))
FILES = HERE / "out" / "r8_stage" / "files"
STAGES = list(BUILD["stages"])
FLAG = 8712
FIELD = BUILD["field"]
ARMED = re.compile(r"\[CustomFormCells\] armed Block\[18\]\[12\][^\n]*")
SWITCHED = re.compile(r"\[CustomFormCells\] Block\[18\]\[12\] switched to form 2[^\n]*")
LOADED = re.compile(r"\[WorldMeshOverride\] loaded '([^']*Block\[18\]\[12\][^']*)' from ([^\n]+)")
_RECORD: dict = {"build": BUILD["files"], "stages": []}
_STAGE = [""]


def _save(g):
    try:
        (g.run_dir / "r8_entrances.json").write_text(json.dumps(_RECORD, indent=1, default=str), encoding="utf-8")
    except Exception as err:                                            # noqa: BLE001
        print(f"[r8] could not write the record: {err}")


def set_lab(fset: str | None) -> list:
    LAB.mkdir(exist_ok=True)
    for child in LAB.iterdir():
        shutil.rmtree(child) if child.is_dir() else child.unlink()
    for rel, want in (BUILD["files"][fset].items() if fset else ()):
        dst = LAB / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(FILES / fset / rel, dst)
        if hashlib.sha256(dst.read_bytes()).hexdigest() != want:
            raise HarnessError(f"r8: the lab does not hold {fset}/{rel} byte for byte")
    return sorted(BUILD["files"][fset]) if fset else []


def to_field(g, first: bool):
    if first:
        g.newgame()
        g.no_encounters()
        g.warp(R3.FARSHORE)
    elif g.state.ui_state == "WorldHUD":
        g.world_warp(R3.FARSHORE)
    else:
        g.warp(R3.FARSHORE)
    g.wait_playable(timeout=60)
    if g.state.field_id != R3.FARSHORE:
        raise HarnessError(f"r8: expected field {R3.FARSHORE}, found {R3.here(g)}")


def walk_out(g):
    g.wait_frames(45)
    R3.calibrate(g, [R3.FS_DOOR], lambda: g.warp(R3.FARSHORE))
    g.walk_to(*R3.FS_EXIT, strict=False, halt_on_transition=True)
    g.wait_world(timeout=90)
    g.world_settle()
    g.no_encounters()          # s94, the F4 booster: the first try died in a random battle outside the Ice Cavern


def log_since(mark) -> str:
    text = ""
    for path, offset in mark.values():
        try:
            text += read_from(Path(path), int(offset))
        except OSError:
            pass
    return text


def walk_across(g) -> dict:
    w = BUILD["walk"]
    face = g.world_face(w["bearing"], home=R3.FS_LANDING, tolerance=2.0)
    g.teleport(*w["start"])
    g.world_settle()
    g.wait_frames(15)
    got = g.world_approach(w["bearing"], w["distance"], speed=face.get("speed"), burst_frames=6)
    trace = [{k: r.get(k) for k in ("x", "z", "y", "progress", "ui")} for r in got.get("trace", [])]
    out = {"outcome": got["outcome"], "progress": got.get("progress"), "trace": trace}
    zs = [r["z"] for r in trace if r.get("z") is not None]
    out["min_z"] = min(zs) if zs else None
    if got["outcome"] != "left_world":
        # an overworld entrance is a PROMPT ("Enter with X", the place's nameplate, a "!" balloon): standing on the
        # tile shows it, Confirm takes it (the first passing try walked onto the live tile and only saw the prompt)
        g.wait_frames(20)
        out["prompt_shot"] = str(g.shot(f"r8-{_STAGE[0]}-prompt"))
        g.press("confirm")
        try:
            g.wait_for(lambda s: s.field_id == FIELD and s.ui_state != "WorldHUD", timeout=20, what=f"field {FIELD}")
        except HarnessError:
            pass
    if got["outcome"] == "left_world":
        try:
            g.wait_for(lambda s: s.field_id == FIELD and s.ui_state != "WorldHUD", timeout=40,
                       what=f"field {FIELD}")
        except HarnessError:
            pass
        g.wait_frames(30)
    out["end"] = R3.here(g)
    out["entered"] = out["end"].get("field") == FIELD and out["end"].get("ui") != "WorldHUD"
    return out


def run(g):
    g.note("r8_session: the Ice Cavern entrance on (18,12) opens / closes with the story (world-forms --entrance2)")
    mark0 = g.log_mark()
    try:
        for i, stage in enumerate(STAGES):
            spec = BUILD["stages"][stage]
            rec = {"stage": stage, **spec}
            _STAGE[0] = stage
            _RECORD["stages"].append(rec)
            to_field(g, first=i == 0)
            rec["placed"] = set_lab(spec["files"])
            g.flag(FLAG, spec["flag"])
            mark = g.log_mark()
            walk_out(g)
            rec["at"] = R3.here(g)
            walk = walk_across(g)
            rec["walk"] = walk
            if walk["outcome"] == "left_world" and not walk["entered"]:
                g.note(f"{stage}: the walk left the world but not into field {FIELD} (a battle?) -- not judged")
            elif spec["enters"]:
                g.check(walk["entered"], f"{stage}: the walk across the tile ENTERS field {FIELD} (Ice Cavern)",
                        json.dumps({k: v for k, v in walk.items() if k != "trace"}))
            else:
                ok = (not walk["entered"] and walk["outcome"] != "left_world" and walk["min_z"] is not None
                      and walk["min_z"] <= BUILD["walk"]["onto_tile_z"])
                g.check(ok, f"{stage}: on the tile, Confirm does nothing -- he STAYS on the world map",
                        json.dumps({k: v for k, v in walk.items() if k != "trace"}))
            log = log_since(mark)
            rec["armed"], rec["switched"] = ARMED.findall(log), SWITCHED.findall(log)
            rec["loads"] = [(k, src.strip()) for k, src in LOADED.findall(log)]

            def bound(part):
                return any(k.endswith(f"Block[18][12] {part}") and "FF9CustomMap-lab" in src for k, src in rec["loads"])
            ok = (bool(rec["armed"]) == spec["armed"] and bool(rec["switched"]) == spec["switched"]
                  and bound("Terrain2") == spec["armed"] and bound("Terrain") == spec["terrain_from_lab"])
            g.check(ok, f"{stage}: Memoria.log -- armed {spec['armed']}, switched {spec['switched']}, Terrain2 bound "
                        f"{spec['armed']}, form-1 Terrain bound {spec['terrain_from_lab']}",
                    json.dumps({"armed": rec["armed"], "switched": rec["switched"], "loads": rec["loads"]}))
            _save(g)
    finally:
        set_lab(None)
        try:
            g.flag(FLAG, False)
        except Exception:                                                # noqa: BLE001
            pass
        try:
            _RECORD["exceptions"] = [str(e) for e in g.exceptions_since(mark0)][:20]
        except Exception as err:                                        # noqa: BLE001
            _RECORD["exceptions_error"] = repr(err)
        _save(g)
