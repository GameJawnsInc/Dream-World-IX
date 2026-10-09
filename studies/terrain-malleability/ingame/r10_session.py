"""In-game ROUND 10 (2026-10-09): LAND -> SEA -- `world-sink` turns a whole real island into open sea (five blocks,
(9,6) (9,7) (10,5) (10,6) (10,7)), replayed on disc 4. DEPLOYS into the scratch mod folder FF9CustomMap-lab ONLY (first
in FolderNames for the round). The lab starts EMPTY; this scenario swaps r10_build's file sets in BEFORE each world
load (the engine reads every loose override at world entry and never again: blocks are never streamed).
RUN:   py tools/play.py studies/terrain-malleability/ingame/r10_session.py --label r10-sink

ROUTE: newgame -> 6603 -> walk out (9011, disc 1): d1_stock, d1_sink on foot -> 6603 at ScenarioCounter 9500 with the
Blue Narciss bound ([190] = 7, its record at the lane start) -> 9003: boat_stock, boat_sink -> 6603 at 11101, back on
foot ([190] = [191] = 0) -> 9008 (disc 4): d4_old, d4_sink. Encounters off (g.no_encounters, engine s94) after every
world load.

REGISTERED PREDICTIONS (out/r10_build.json):
  on foot, teleported onto P1 (summit), P2 (mid), P3 (lowland), y +-0.15:
    d1_stock, d4_old   the island: 26.30 / 13.14 / 3.24
    d1_sink, d4_sink   open sea: -1.367 at all three (the sea at y 0 minus the party's walk sink on topograph 57,
                       350/256 -- launch 1 predicted 0.0 and missed by exactly that; launch 2 registers it)
  the boat, eastbound from (588.5, -395.63) on open sea, full throttle:
    boat_stock   STOPS at the island's west coast: stalls with its furthest x in 608.5..689.5 (sim: 59.5u out)
    boat_sink    sails across where the island was: reaches the goal 121u out (x 709.5, past its east side)
  Memoria.log, per world load: the lab's 10 Block overrides of this round bound for the stage's disc in d1_sink,
  boat_sink (Disc1) and d4_sink (Disc4); none in the stock stages and d4_old (OLD has Disc1 files only); 0 exceptions
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
import veh_lib as V                                    # noqa: E402  (the vehicle route, holds, settling)

GAME = R3.GAME
LAB = GAME / "FF9CustomMap-lab"
BUILD = json.loads((HERE / "out" / "r10_build.json").read_text(encoding="utf-8"))
FILES = HERE / "out" / "r10_stage" / "files"
STAGES = list(BUILD["stages"])
BOAT = BUILD["boat"]
TOL_Y = 0.15
BLOCKS = {tuple(b) for b in BUILD["blocks"]}
LOADED = re.compile(r"\[WorldMeshOverride\] loaded 'WorldMap/Disc(\d)/0_1/r\d+/Block\[(\d+)\]\[(\d+)\] ([A-Za-z0-9]+)' "
                    r"from ([^\n]+)")
_RECORD: dict = {"build": BUILD["files"], "stages": []}
_STAGE = [""]


def _save(g):
    try:
        (g.run_dir / "r10_sink.json").write_text(json.dumps(_RECORD, indent=1, default=str), encoding="utf-8")
    except Exception as err:                                            # noqa: BLE001
        print(f"[r10] could not write the record: {err}")


def set_lab(fset: str | None) -> list:
    LAB.mkdir(exist_ok=True)
    for child in LAB.iterdir():
        shutil.rmtree(child) if child.is_dir() else child.unlink()
    for rel, want in (BUILD["files"][fset].items() if fset else ()):
        dst = LAB / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(FILES / fset / rel, dst)
        if hashlib.sha256(dst.read_bytes()).hexdigest() != want:
            raise HarnessError(f"r10: the lab does not hold {fset}/{rel} byte for byte")
    return sorted(BUILD["files"][fset]) if fset else []


def log_since(mark) -> str:
    text = ""
    for path, offset in mark.values():
        try:
            text += read_from(Path(path), int(offset))
        except OSError:
            pass
    return text


def foot_out(g, first: bool):
    """Disc 1 on foot: newgame (first) or a world -> 6603 round trip at the new-game story point, out of the door."""
    if first:
        g.newgame()
        g.no_encounters()
        g.warp(R3.FARSHORE)
    else:
        g.world_warp(R3.FARSHORE)
    g.wait_playable(timeout=60)
    g.wait_frames(45)
    R3.calibrate(g, [R3.FS_DOOR], lambda: g.warp(R3.FARSHORE))
    g.walk_to(*R3.FS_EXIT, strict=False, halt_on_transition=True)
    g.wait_world(timeout=90)
    g.world_settle()


def readouts(g, spec) -> dict:
    out = {}
    for k, p in BUILD["points"].items():
        g.teleport(*p)
        g.world_settle()
        g.wait_frames(20)
        out[k] = {"at": p, "y": g.state.world_y, "x": g.state.world_x, "z": g.state.world_z}
        if k == "P2":
            out["shot"] = str(g.shot(f"r10-{_STAGE[0]}-P2"))
        want = spec["points"][k]["y_foot"]                    # the ground minus the party's walk sink
        got = out[k]["y"]
        g.check(got is not None and abs(got - want) <= TOL_Y,
                f"{_STAGE[0]}: {k} reads y {want} (+-{TOL_Y}; {spec['points'][k]['part']}, topograph "
                f"{spec['points'][k]['topo']})", json.dumps(out[k]))
    g.teleport(*R3.FS_LANDING)                                  # back onto land before leaving the world
    g.world_settle()
    return out


def boat_drive(g, spec) -> dict:
    x0, z0 = BOAT["start"]
    hd, s0, s1 = V.hull_heading(g, (x0, z0))
    if hd is None or abs(V.angdiff(hd, 0.0)) > 2.0:
        hd = V.hull_steer(g, (x0, z0), 0.0, _RECORD.setdefault("steer", {}))
    V.tp(g, x0, z0)
    meas = V.along(x0, z0, 0.0)
    goal = BOAT["goal"]
    r = V.hold_until(g, ["up"], measure=meas, done=lambda s: (meas(s) or 0.0) >= goal, stall_s=1.0, start_s=3.0,
                     max_s=25.0)
    end = V.settle3(g)
    xs = [s["x"] for s in r["samples"] if s["x"] is not None] + ([end["x"]] if end["x"] is not None else [])
    out = {"heading": hd, "outcome": r["outcome"], "x_max": max(xs) if xs else None, "end": end,
           "samples": r["samples"][-12:]}
    out["shot"] = str(g.shot(f"r10-{_STAGE[0]}-boat"))
    lo, hi = BOAT["island_x"][0] - 4.0, BOAT["island_x"][1] - 10.0
    if spec["boat"]["pass"]:
        g.check(r["outcome"] == "done", f"{_STAGE[0]}: the boat sails across where the island was ({goal}u, past "
                                        f"x {BOAT['island_x'][1]})", json.dumps({k: v for k, v in out.items()
                                                                                 if k != "samples"}))
    else:
        g.check(r["outcome"] == "stalled" and out["x_max"] is not None and lo <= out["x_max"] <= hi,
                f"{_STAGE[0]}: the boat STOPS at the island's coast (furthest x in {lo}..{hi}; sim "
                f"{BOAT['stock_progress']}u out)", json.dumps({k: v for k, v in out.items() if k != "samples"}))
    return out


def run(g):
    g.note("r10_session: world-sink turns a five-block island into open sea, on disc 1 and (replayed) disc 4")
    mark0 = g.log_mark()
    try:
        for i, stage in enumerate(STAGES):
            spec = BUILD["stages"][stage]
            disc, kind = spec["disc"], spec["kind"]
            rec = {"stage": stage, "files": spec["files"], "disc": disc, "kind": kind}
            _STAGE[0] = stage
            _RECORD["stages"].append(rec)
            rec["placed"] = len(set_lab(spec["files"]))            # read at the NEXT world load
            mark = g.log_mark()
            if kind == "boat":
                pokes = {190: 7, 191: 0}
                pokes.update({int(k): v for k, v in BOAT["record"].items()})
                V.reach_world_as(g, rec, scenario=9500, pokes=pokes, expect_world=9003, first=False)
                a = rec["arrival"]
                g.check(a["world"] == 9003 and a["vehicle"] == 7, f"{stage}: world 9003 with the Blue Narciss bound",
                        json.dumps(a))
                rec["boat"] = boat_drive(g, spec)
            elif disc == 4:
                V.reach_world_as(g, rec, scenario=11101, pokes={190: 0, 191: 0}, expect_world=9008, first=False)
                g.no_encounters()
                rec["at"] = R3.here(g)
                g.check(g.state.world_id == 9008, f"{stage}: disc 4 (world 9008), on foot", json.dumps(rec["at"]))
                rec["points"] = readouts(g, spec)
            else:
                foot_out(g, first=i == 0)
                g.no_encounters()
                rec["at"] = R3.here(g)
                rec["points"] = readouts(g, spec)
            log = log_since(mark)
            loads = [(int(d), (int(x), int(y)), part, src.strip()) for d, x, y, part, src in LOADED.findall(log)]
            lab = [(d, b, p) for d, b, p, src in loads if "FF9CustomMap-lab" in src]
            rec["lab_loads"] = lab
            mine = [r for r in lab if r[0] == disc and r[1] in BLOCKS]
            other = [r for r in lab if r not in mine]
            g.check(len(mine) == spec["lab_files"] and not other,
                    f"{stage}: Memoria.log binds {spec['lab_files']} of the lab's Block overrides on disc {disc}",
                    json.dumps({"bound": len(mine), "other": other[:6]}))
            _save(g)
    finally:
        set_lab(None)
        try:
            _RECORD["exceptions"] = [str(e) for e in g.exceptions_since(mark0)][:20]
        except Exception as err:                                        # noqa: BLE001
            _RECORD["exceptions_error"] = repr(err)
        _save(g)
