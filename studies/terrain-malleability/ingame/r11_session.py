"""In-game ROUND 11 (2026-10-09): LAND -> SEA IN SHALLOW WATER -- `world-sink` on two islands that stand in mid water:
A (16,16)+(17,16), a beach island in a lagoon (its beach water goes with it, its tiles re-band as mid water), and B
(4,15), an island on a shelf edge (its tiles re-band as mid water, transition and deep sea, the transition band carried
across where it stood); replayed on disc 4. DEPLOYS into the scratch mod folder FF9CustomMap-lab ONLY (first in
FolderNames for the round). The lab starts EMPTY; this scenario swaps r11_build's file sets in BEFORE each world load
(the engine reads every loose override at world entry and never again: blocks are never streamed).
RUN:   py tools/play.py studies/terrain-malleability/ingame/r11_session.py --label r11-shallows

ROUTE: newgame -> 6603 -> walk out (9011, disc 1): d1_stock, d1_sink on foot -> 6603 at ScenarioCounter 9500 with the
Blue Narciss bound ([190] = 7, its record at the lane's start) -> 9003: boatA_stock, boatA_sink, boatB_stock,
boatB_sink -> 6603 at 11101, back on foot ([190] = [191] = 0) -> 9008 (disc 4): d4_old, d4_sink. Encounters off
(g.no_encounters, engine s94) after every world load.

REGISTERED PREDICTIONS (out/r11_build.json):
  on foot, teleported onto each read point, y +-0.15:
    d1_stock, d4_old   the islands: A1 3.38 (summit), A2 0.23 (its beach), B1 3.95 / 3.94 on disc 4, B2 3.58, B3 3.53,
                       B4 3.02
    d1_sink, d4_sink   water, each at its new class's walk sink (w_movementSinkArray row 1, ff9.cs:19): mid water
                       topograph 54 reads -0.586 (A1, A2, B1 on sea3; B2 on a sea5 transition tile's mid-water tri),
                       open sea 57 reads -1.367 (B3 on a transition tile's deep tri, B4 on sea4). 54's sink is this
                       round's first read; 57's was round 10's.
  the boat, eastbound at full throttle from sailable water 24u west of each island:
    boatA_stock  STOPS at the island (sim: 20.2u out, x 1067.7, at its standoff belt) -- furthest x in 1067.5..1088.5
    boatA_sink   sails across where it stood: reaches the goal 61u out (x 1108.5)
    boatB_stock  STOPS at the island (sim: 20.8u out, x 263.3) -- furthest x in 262.5..284.5
    boatB_sink   sails across: reaches the goal 62u out (x 304.5)
  Memoria.log, per world load: the lab's 13 Block overrides of this round bound for the stage's disc in d1_sink and the
  two boat_sink stages (Disc1) and d4_sink (Disc4); none in the stock stages and d4_old (OLD has Disc1 files only);
  0 exceptions
  every frame: no floating land, no hole, no seam where the new water meets the kept water (the shots, by eye)
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
BUILD = json.loads((HERE / "out" / "r11_build.json").read_text(encoding="utf-8"))
FILES = HERE / "out" / "r11_stage" / "files"
STAGES = list(BUILD["stages"])
TOL_Y = 0.15
BLOCKS = {tuple(b) for b in BUILD["all_blocks"]}
LOADED = re.compile(r"\[WorldMeshOverride\] loaded 'WorldMap/Disc(\d)/0_1/r\d+/Block\[(\d+)\]\[(\d+)\] ([A-Za-z0-9]+)' "
                    r"from ([^\n]+)")
_RECORD: dict = {"build": BUILD["files"], "stages": []}
_STAGE = [""]


def _save(g):
    try:
        (g.run_dir / "r11_shallows.json").write_text(json.dumps(_RECORD, indent=1, default=str), encoding="utf-8")
    except Exception as err:                                            # noqa: BLE001
        print(f"[r11] could not write the record: {err}")


def set_lab(fset: str | None) -> list:
    LAB.mkdir(exist_ok=True)
    for child in LAB.iterdir():
        shutil.rmtree(child) if child.is_dir() else child.unlink()
    for rel, want in (BUILD["files"][fset].items() if fset else ()):
        dst = LAB / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(FILES / fset / rel, dst)
        if hashlib.sha256(dst.read_bytes()).hexdigest() != want:
            raise HarnessError(f"r11: the lab does not hold {fset}/{rel} byte for byte")
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
        if k in ("A1", "B1", "B3"):
            out[k]["shot"] = str(g.shot(f"r11-{_STAGE[0]}-{k}"))
        want = spec["points"][k]["y_foot"]                    # the ground minus the party's walk sink
        got = out[k]["y"]
        g.check(got is not None and abs(got - want) <= TOL_Y,
                f"{_STAGE[0]}: {k} reads y {want} (+-{TOL_Y}; {spec['points'][k]['part']}, topograph "
                f"{spec['points'][k]['topo']})", json.dumps(out[k]))
    g.teleport(*R3.FS_LANDING)                                  # back onto land before leaving the world
    g.world_settle()
    return out


def boat_drive(g, spec, lane) -> dict:
    x0, z0 = lane["start"]
    hd, s0, s1 = V.hull_heading(g, (x0, z0))
    if hd is None or abs(V.angdiff(hd, 0.0)) > 2.0:
        hd = V.hull_steer(g, (x0, z0), 0.0, _RECORD.setdefault("steer", {}))
    V.tp(g, x0, z0)
    meas = V.along(x0, z0, 0.0)
    goal = lane["goal"]
    r = V.hold_until(g, ["up"], measure=meas, done=lambda s: (meas(s) or 0.0) >= goal, stall_s=1.0, start_s=3.0,
                     max_s=25.0)
    end = V.settle3(g)
    xs = [s["x"] for s in r["samples"] if s["x"] is not None] + ([end["x"]] if end["x"] is not None else [])
    out = {"heading": hd, "outcome": r["outcome"], "x_max": max(xs) if xs else None, "end": end,
           "samples": r["samples"][-12:]}
    out["shot"] = str(g.shot(f"r11-{_STAGE[0]}-boat"))
    lo, hi = lane["stock_stop"][0] - 0.2, lane["island_x"][1] - 10.0
    if spec["boat"]["pass"]:
        g.check(r["outcome"] == "done", f"{_STAGE[0]}: the boat sails across where the island was ({goal}u, past "
                                        f"x {lane['island_x'][1]})", json.dumps({k: v for k, v in out.items()
                                                                                 if k != "samples"}))
    else:
        g.check(r["outcome"] == "stalled" and out["x_max"] is not None and lo <= out["x_max"] <= hi,
                f"{_STAGE[0]}: the boat STOPS at the island (furthest x in {lo}..{hi}; sim "
                f"{lane['stock_progress']}u out)", json.dumps({k: v for k, v in out.items() if k != "samples"}))
    return out


def run(g):
    g.note("r11_session: world-sink in shallow water -- a lagoon beach island and a shelf-edge island re-banded, on "
           "disc 1 and (replayed) disc 4")
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
                lane = BUILD["boat"][spec["site"]]
                pokes = {190: 7, 191: 0}
                pokes.update({int(k): v for k, v in lane["record"].items()})
                V.reach_world_as(g, rec, scenario=9500, pokes=pokes, expect_world=9003, first=False)
                a = rec["arrival"]
                g.check(a["world"] == 9003 and a["vehicle"] == 7, f"{stage}: world 9003 with the Blue Narciss bound",
                        json.dumps(a))
                rec["boat"] = boat_drive(g, spec, lane)
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
