"""In-game ROUND 6 (2026-10-09): story terrain on a cell stock never switches -- engine patch s92 + `world-forms --arm` +
`world-terrain --form 2` (terrain study P1). DEPLOYS into the scratch mod folder FF9CustomMap-lab ONLY (first in
FolderNames for the round). The lab starts EMPTY; this scenario swaps r6_build's stages in while the player is inside
field 6603 (FARSHORE), so each walk out is a fresh world load (s92 arms cells and reads Form.txt then).
RUN:   py tools/play.py studies/terrain-malleability/ingame/r6_session.py --label r6-anycell

ROUTE: newgame -> warp 6603 -> walk out (round 3's FARSHORE exit) -> the world at scenario 0 -> teleport to four read
points on/by cell (6,12) -> world_warp 6603 -> swap (and, for flag_on, set flag 8712) -> walk out -> ...

REGISTERED PREDICTIONS (out/r6_build.json; tolerance 0.15):
  stock, armed_false, flag_off, no_form: STOCK -- O 2.9623 (the Object), T 2.9688, T2 2.9688, ctl 12.4129
  armed_true, flag_on: FORM2 -- O 2.9623 (the form-1 Object CARRIED into form 2; without the carry O has no ground at
      all), T 4.4563, T2 7.3466 (the kit's Terrain2), ctl 12.4129
  Memoria.log, per world load: "[CustomFormCells] armed Block[6][12]" in every stage but stock; "... switched to form
  2" exactly in armed_true and flag_on; the Terrain2 bound from the lab in every armed stage
  0 exceptions in either log
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

import r3_session as R3                                # noqa: E402  (calibrate, here, FARSHORE's exit)

GAME = R3.GAME
LAB = GAME / "FF9CustomMap-lab"
BUILD = json.loads((HERE / "out" / "r6_build.json").read_text(encoding="utf-8"))
FILES = HERE / "out" / "r6_stage" / "files"
STAGES = list(BUILD["stages"])
FLAG = 8712
TOL = 0.15
ARMED = re.compile(r"\[CustomFormCells\] armed Block\[6\]\[12\][^\n]*")
SWITCHED = re.compile(r"\[CustomFormCells\] Block\[6\]\[12\] switched to form 2[^\n]*")
LOADED = re.compile(r"\[WorldMeshOverride\] loaded '([^']*Block\[6\]\[12\][^']*)' from ([^\n]+)")
_RECORD: dict = {"build": {k: {kk: v.get(kk) for kk in ("rel", "sha", "text")} for k, v in BUILD["files"].items()},
                 "stages": []}


def _save(g):
    try:
        (g.run_dir / "r6_anycell.json").write_text(json.dumps(_RECORD, indent=1, default=str), encoding="utf-8")
    except Exception as err:                                            # noqa: BLE001
        print(f"[r6] could not write the record: {err}")


def set_lab(stage: str | None) -> dict:
    LAB.mkdir(exist_ok=True)
    for child in LAB.iterdir():
        shutil.rmtree(child) if child.is_dir() else child.unlink()
    placed = {}
    for name in (BUILD["stages"][stage]["lab"] if stage else ()):
        rel = BUILD["files"][name]["rel"]
        dst = LAB / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(FILES / name / rel, dst)
        got = hashlib.sha256(dst.read_bytes()).hexdigest()
        if got != BUILD["files"][name]["sha"]:
            raise HarnessError(f"r6: the lab does not hold {name} byte for byte")
        placed[rel] = got
    return placed


def to_field(g, first: bool):
    if first:
        g.newgame()
        g.warp(R3.FARSHORE)
    else:
        g.world_warp(R3.FARSHORE)
    g.wait_playable(timeout=60)
    if g.state.field_id != R3.FARSHORE:
        raise HarnessError(f"r6: expected field {R3.FARSHORE}, found {R3.here(g)}")


def walk_out(g):
    g.wait_frames(45)
    R3.calibrate(g, [R3.FS_DOOR], lambda: g.warp(R3.FARSHORE))
    g.walk_to(*R3.FS_EXIT, strict=False, halt_on_transition=True)
    g.wait_world(timeout=90)
    g.world_settle()


def log_since(mark) -> str:
    text = ""
    for path, offset in mark.values():
        try:
            text += read_from(Path(path), int(offset))
        except OSError:
            pass
    return text


def run(g):
    g.note("r6_session: story terrain on cell (6,12), which stock never switches (engine s92)")
    mark0 = g.log_mark()
    try:
        for i, stage in enumerate(STAGES):
            spec = BUILD["stages"][stage]
            rec = {"stage": stage, "source": spec["ground"], "flag": spec["flag"]}
            _RECORD["stages"].append(rec)
            to_field(g, first=i == 0)
            rec["placed"] = set_lab(None if stage == "stock" else stage)
            g.flag(FLAG, spec["flag"])
            mark = g.log_mark()
            walk_out(g)
            rec["at"] = R3.here(g)
            log = log_since(mark)
            rec["armed"], rec["switched"] = ARMED.findall(log), SWITCHED.findall(log)
            rec["loads"] = [(k, src.strip()) for k, src in LOADED.findall(log)]
            rec["read"] = {}
            for k, p in BUILD["points"].items():
                g.teleport(*p)
                g.world_settle()
                g.wait_frames(20)
                rec["read"][k] = g.state.world_y
            pred = BUILD["predict"][stage]
            rec["predict"] = pred
            g.check(all(rec["read"][k] is not None and abs(rec["read"][k] - pred[k]) <= TOL for k in pred),
                    f"{stage}: the read points stand on {spec['ground'].upper()} ground",
                    json.dumps({k: [rec["read"][k], pred[k]] for k in pred}))
            armed_want, switch_want = stage != "stock", spec["ground"] == "form2"
            t2_bound = any(k.endswith("Block[6][12] Terrain2") and "FF9CustomMap-lab" in src for k, src in rec["loads"])
            g.check(bool(rec["armed"]) == armed_want and bool(rec["switched"]) == switch_want
                    and t2_bound == armed_want,
                    f"{stage}: Memoria.log -- armed {armed_want}, switched {switch_want}, Terrain2 bound {armed_want}",
                    json.dumps({"armed": rec["armed"], "switched": rec["switched"], "loads": rec["loads"]}))
            if stage in ("armed_false", "armed_true"):
                g.teleport(*BUILD["points"]["T2"])
                g.world_settle()
                g.wait_frames(90)
                g.shot(f"r6-{stage}")
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
