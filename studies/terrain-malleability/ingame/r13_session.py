"""In-game ROUND 13 (2026-10-09): ISLANDS WITH BUILDINGS -- `world-sink` on an island with a building on it: the
building (its Object, a waterfall, rivers) goes with the island and the hole it plugged becomes water. D, Daguerreo, by
its footprint (its water joins its neighbours'), its Object, falls, rivers and river joints with it; L, the lagoon island
at (553, -1127), by whole tiles, its hut across the coast with it; O, the corner island at (0, 0), by its footprint, its
5-tri building with it. Every one with --allow-entrances (lab only). Replayed on disc 4 (D, L) or copied there (O).
DEPLOYS into the scratch mod folder FF9CustomMap-lab ONLY (first in FolderNames for the round). The lab starts EMPTY;
this scenario swaps r13_build's file sets in BEFORE each world load.
RUN:   py tools/play.py studies/terrain-malleability/ingame/r13_session.py --label r13-buildings

ROUTE: newgame -> 6603 -> walk out (9011, disc 1): d1_stock, d1_sink on foot -> 6603 at ScenarioCounter 9500 with the
Blue Narciss bound ([190] = 7, its record at the lane's start) -> 9003: boatD_stock, boatD_sink, boatL_stock,
boatL_sink -> 6603 at 11101, back on foot ([190] = [191] = 0) -> 9008 (disc 4): d4_old, d4_sink. Encounters off
(g.no_encounters, engine s94) after every world load.

REGISTERED PREDICTIONS (out/r13_build.json):
  on foot, teleported onto each read point, y +-0.15 (the ground minus the walk sink of its topograph):
    d1_stock   D1 31.089 (Daguerreo's summit), D2 30.675, D3 29.882, DB 28.870 (its building's roof, Object topograph
               59); L1 6.530, L2 2.998, LB 4.759 (the hut's roof); O1 12.964, O2 1.783, OB 7.667 (its roof); K1 6.547,
               K2 3.648 (Daguerreo's neighbours)
    d1_sink    D1 -0.586 (sea5 54), D2 -1.367 (sea5 57), D3 DB -0.586 (mid water 54: where the building stood); L1 L2 LB
               -0.586; O1 O2 OB -1.367 (open sea 57); K1 K2 unchanged (the neighbours stay)
    d4_old     disc 4's own ground: as d1_stock at every point
    d4_sink    as d1_sink (D and L from the disc-4 replays, O from the copy)
  the boat, eastbound at full throttle from sailable water 24u west of each island:
    boatD_stock  STOPS at Daguerreo (sim 37.4u out, x 346.9)          boatD_sink  reaches its goal 160u out
    boatL_stock  STOPS at the lagoon island (sim 19.4u out, x 539.9)  boatL_sink  reaches its goal 113u out
  Memoria.log, per world load: the lab's 54 Disc1 overrides (Object, Falls, River and RiverJoint among them: written
  under the engine's own names) in d1_sink and the boat_sink stages, its 54 Disc4 ones in d4_sink, none in the stock
  stages and d4_old; 0 exceptions
  every frame: no building, waterfall or river left standing over the sea; no hole, no seam; Daguerreo's neighbours
  standing where they stood
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
BUILD = json.loads((HERE / "out" / "r13_build.json").read_text(encoding="utf-8"))
FILES = HERE / "out" / "r13_stage" / "files"
STAGES = list(BUILD["stages"])
TOL_Y = 0.15
BLOCKS = {tuple(b) for b in BUILD["all_blocks"]}
LOADED = re.compile(r"\[WorldMeshOverride\] loaded 'WorldMap/Disc(\d)/0_1/r\d+/Block\[(\d+)\]\[(\d+)\] ([A-Za-z0-9]+)' "
                    r"from ([^\n]+)")
_RECORD: dict = {"build": BUILD["files"], "stages": []}
_STAGE = [""]


def _save(g):
    try:
        (g.run_dir / "r13_buildings.json").write_text(json.dumps(_RECORD, indent=1, default=str), encoding="utf-8")
    except Exception as err:                                            # noqa: BLE001
        print(f"[r13] could not write the record: {err}")


def set_lab(fset: str | None) -> list:
    LAB.mkdir(exist_ok=True)
    for child in LAB.iterdir():
        shutil.rmtree(child) if child.is_dir() else child.unlink()
    for rel, want in (BUILD["files"][fset].items() if fset else ()):
        dst = LAB / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(FILES / fset / rel, dst)
        if hashlib.sha256(dst.read_bytes()).hexdigest() != want:
            raise HarnessError(f"r13: the lab does not hold {fset}/{rel} byte for byte")
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
        if k in ("D1", "DB", "LB", "OB", "K1"):
            out[k]["shot"] = str(g.shot(f"r13-{_STAGE[0]}-{k}"))
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
    out["shot"] = str(g.shot(f"r13-{_STAGE[0]}-boat"))
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
    g.note("r13_session: islands with buildings -- Daguerreo, the lagoon island and the corner island sunk with their "
           "buildings (Object, waterfall, rivers)")
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
