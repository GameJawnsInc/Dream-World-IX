"""In-game ROUND 7 (2026-10-09): buildings that change with the story -- engine patch s93 (on s92) + `world-forms
--building2`. DEPLOYS into the scratch mod folder FF9CustomMap-lab ONLY (first in FolderNames for the round). The lab
starts EMPTY; this scenario swaps r7_build's file sets in while the player is inside field 6603 (FARSHORE), so each walk
out is a fresh world load (s92/s93 arm cells, register their Object2 and read Form.txt then).
RUN:   py tools/play.py studies/terrain-malleability/ingame/r7_session.py --label r7-buildings

ROUTE: newgame -> warp 6603 -> walk out -> per stage: read points on A (6,12) and the hill, face south on the landing
lawn, walk 9u into B (7,12)'s beacon footprint -> world_warp 6603 (scenario 11101 for the disc-4 stage) -> swap the
lab, set flag 8712 -> walk out -> ...

REGISTERED PREDICTIONS (out/r7_build.json; tolerance 0.15):
  stock, off   form 1 everywhere: A's roof R1 8.84 / R2 8.28, plaza W 3.01; the hill H_w 3.29 / H_e 3.00; the walk REACHES
  on           form 2: A's building GONE -- R1 3.33 / R2 3.28 / W 3.62 (the kit's fill); the hill 4.92 / 4.63; the walk is
               BLOCKED at the beacon's north face (z ~ -793.5)
  keep         form 2 with A's building back (s92 carries it: R1/R2/W as stock), the hill raised, the walk BLOCKED
  on_disc4     disc 4's own form 2: R1 2.99 / R2 3.03 / W 3.55, the hill raised, the walk BLOCKED
  Memoria.log, per world load: "[CustomFormCells] armed" for Block[6][12] and Block[7][12] in every stage but stock;
  "switched to form 2" for both exactly in on, keep, on_disc4; B's Object2 bound from the lab in every armed stage (the
  s93 path), A's in off, on and on_disc4 (not keep); 0 exceptions
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
BUILD = json.loads((HERE / "out" / "r7_build.json").read_text(encoding="utf-8"))
FILES = HERE / "out" / "r7_stage" / "files"
STAGES = list(BUILD["stages"])
FLAG = 8712
TOL = 0.15
DISC4_SCENARIO = 11101
ARMED = re.compile(r"\[CustomFormCells\] armed Block\[(\d+)\]\[12\] \(Disc(\d+)\)[^\n]*")
SWITCHED = re.compile(r"\[CustomFormCells\] Block\[(\d+)\]\[12\] switched to form 2[^\n]*")
LOADED = re.compile(r"\[WorldMeshOverride\] loaded '([^']*Block\[[67]\]\[12\][^']*)' from ([^\n]+)")
_RECORD: dict = {"build": {k: v for k, v in BUILD["files"].items()}, "stages": []}


def _save(g):
    try:
        (g.run_dir / "r7_buildings.json").write_text(json.dumps(_RECORD, indent=1, default=str), encoding="utf-8")
    except Exception as err:                                            # noqa: BLE001
        print(f"[r7] could not write the record: {err}")


def set_lab(fset: str | None) -> dict:
    LAB.mkdir(exist_ok=True)
    for child in LAB.iterdir():
        shutil.rmtree(child) if child.is_dir() else child.unlink()
    placed = {}
    for rel, want in (BUILD["files"][fset].items() if fset else ()):
        dst = LAB / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(FILES / fset / rel, dst)
        if hashlib.sha256(dst.read_bytes()).hexdigest() != want:
            raise HarnessError(f"r7: the lab does not hold {fset}/{rel} byte for byte")
        placed[rel] = want
    return placed


def to_field(g, first: bool, disc: int):
    scen = DISC4_SCENARIO if disc == 4 else None
    if first:
        g.newgame()
        g.warp(R3.FARSHORE)
    elif scen is not None:
        g.world_warp(R3.FARSHORE, scenario=scen)
    else:
        g.world_warp(R3.FARSHORE)
    g.wait_playable(timeout=60)
    if g.state.field_id != R3.FARSHORE:
        raise HarnessError(f"r7: expected field {R3.FARSHORE}, found {R3.here(g)}")


def walk_out(g, disc: int):
    def rewarp():
        if disc == 4:
            g.warp(R3.FARSHORE, scenario=DISC4_SCENARIO)
        else:
            g.warp(R3.FARSHORE)
    g.wait_frames(45)
    R3.calibrate(g, [R3.FS_DOOR], rewarp)
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


def beacon_walk(g) -> dict:
    w = BUILD["walk"]
    face = g.world_face(w["bearing"], home=R3.FS_LANDING, tolerance=2.0)
    g.teleport(*w["start"])
    g.world_settle()
    g.wait_frames(15)
    got = g.world_approach(w["bearing"], w["distance"], speed=face.get("speed"), burst_frames=6)
    return {"outcome": got["outcome"], "progress": got.get("progress"), "end": R3.here(g),
            "trace": [{k: r.get(k) for k in ("x", "z", "y", "progress")} for r in got.get("trace", [])]}


def run(g):
    g.note("r7_session: buildings that change with the story on (6,12) + (7,12) (engine s93)")
    mark0 = g.log_mark()
    try:
        for i, stage in enumerate(STAGES):
            spec = BUILD["stages"][stage]
            disc = spec["disc"]
            rec = {"stage": stage, **spec}
            _RECORD["stages"].append(rec)
            to_field(g, first=i == 0, disc=disc)
            rec["placed"] = sorted(set_lab(spec["files"]))
            g.flag(FLAG, spec["flag"])
            mark = g.log_mark()
            walk_out(g, disc)
            rec["at"] = R3.here(g)
            pts, pred = BUILD["points"][str(disc)], BUILD["predict"][str(disc)][spec["ground"]]
            rec["read"] = {}
            for k, p in pts.items():
                g.teleport(*p)
                g.world_settle()
                g.wait_frames(20)
                rec["read"][k] = g.state.world_y
            rec["predict"] = pred
            g.check(all(rec["read"][k] is not None and abs(rec["read"][k] - pred[k]) <= TOL for k in pred),
                    f"{stage}: A's footprint, the hill and ctl stand on the predicted ground "
                    f"({'A removed' if spec['a_removed'] else 'A standing'}, "
                    f"{'hill' if spec['switched'] else 'no hill'})",
                    json.dumps({k: [rec["read"][k], pred[k]] for k in pred}))
            g.teleport(*pts["W"])
            g.world_settle()
            g.wait_frames(90)
            g.shot(f"r7-{stage}-A")
            walk = beacon_walk(g)
            rec["walk"] = walk
            if walk["outcome"] == "left_world":
                g.note(f"{stage}: the beacon walk left the world (a battle?) -- not judged")
            else:
                end_z = walk["end"]["z"] if isinstance(walk["end"], dict) else None
                if spec["beacon"]:
                    ok = walk["outcome"] == "blocked" and end_z is not None \
                        and end_z > BUILD["walk"]["north_face"] - 0.6
                    want = "BLOCKED at the beacon's north face"
                else:
                    ok = walk["outcome"] == "reached"
                    want = "REACHES the beacon's spot (no beacon)"
                g.check(ok, f"{stage}: the 9u walk south into B's footprint {want}",
                        json.dumps({k: v for k, v in walk.items() if k != "trace"}))
            g.wait_frames(90)
            g.shot(f"r7-{stage}-beacon")
            log = log_since(mark)
            armed = {(int(x), int(d)) for x, d in ARMED.findall(log)}
            switched = {int(x) for x in SWITCHED.findall(log)}
            loads = [(k, src.strip()) for k, src in LOADED.findall(log)]
            rec["armed"], rec["switched"], rec["loads"] = sorted(armed), sorted(switched), loads

            def bound(cell_x, part):
                return any(k.endswith(f"Block[{cell_x}][12] {part}") and f"Disc{disc}/" in k
                           and "FF9CustomMap-lab" in src for k, src in loads)
            want_armed = {(6, disc), (7, disc)} if spec["armed"] else set()
            want_switch = {6, 7} if spec["switched"] else set()
            a_obj2 = spec["files"] == "FULL"
            ok = (armed == want_armed and switched == want_switch
                  and bound(7, "Object2") == spec["armed"] and bound(6, "Object2") == a_obj2
                  and bound(6, "Terrain2") == spec["armed"] and bound(7, "Terrain2") == spec["armed"])
            g.check(ok, f"{stage}: Memoria.log -- armed {sorted(want_armed)}, switched {sorted(want_switch)}, "
                        f"B's Object2 bound {spec['armed']}, A's Object2 bound {a_obj2}",
                    json.dumps({"armed": rec["armed"], "switched": rec["switched"], "loads": loads}))
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
