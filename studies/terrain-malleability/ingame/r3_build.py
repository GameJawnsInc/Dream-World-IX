"""BUILD + REGISTERED PREDICTIONS for in-game round 3 (2026-10-08): the three checks of the defect 5-6 / O2 fixes.
Writes ONLY into staging folders under ingame/out/r3_stage/ (gitignored); the orchestrator copies a stage into the
scratch mod folder FF9CustomMap-lab for its launch (r3_session.py).

Every stage is the exact output of the kit's CLI (`py -m ff9mapkit world-terrain --mod-folder <stage> ...`), run from
ff9mapkit/ so the worktree's package is the one under test; its stdout is kept. Predictions read the stage's own
meshes through the engine's sky ground query (the arealib raster rule, calibrated against placement.place), with the
stage FIRST and the live FolderNames stack after it, exactly the in-game priority of a lab first in FolderNames.

GUARD (defect 6's premise; guard_prep.py says why this site): the stock Burmecia/Entrance exit (field 750, entry 21)
stores the landing (963.234, 3.086, -718.910). Stages, all r16 centred on that landing:
  A_lower3  --lower 3                      (the guard passes lowering)
  A_raise1  --raise 1                      (under the guard's 1.17)
  A_raise4  --raise 4 --allow-entrances    (past the 2.34375 walk-ray start by 1.66u; refused without the flag --
                                            recorded here as the guard's own default verdict)
BEACH (defect 5, the stitch pins): world-terrain --at 480 -1120 --radius 16 --raise 3, session 5's one-way-wall edit.
REPLAY (O2): world-terrain --at 256 -872 --radius 16 --raise 4, session 6's crack edit; the auto-mirror must replay
it on disc 4 ((4,13) differs there in sea1).
Writes out/r3_build.json.
Run:  py studies/terrain-malleability/ingame/r3_build.py
"""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TM = HERE.parent
REPO = TM.parent.parent
KIT = REPO / "ff9mapkit"
sys.path.insert(0, str(TM / "gap_area_layer"))
sys.path.insert(0, str(TM / "consumption"))
import arealib as A                                  # noqa: E402
import bind_oracle as BO                             # noqa: E402
import numpy as np                                   # noqa: E402

STAGE = HERE / "out" / "r3_stage"
LANDING = (963.234, -718.910)                        # 246588/256, -184041/256 (field 750 entry 21)
STORED_Y = 3.086                                     # -(64746-65536)/256
STAGES = {
    "A_lower3": ["--at", "963.234", "-718.910", "--radius", "16", "--lower", "3"],
    "A_raise1": ["--at", "963.234", "-718.910", "--radius", "16", "--raise", "1"],
    "A_raise4": ["--at", "963.234", "-718.910", "--radius", "16", "--raise", "4", "--allow-entrances"],
    "B_beach3": ["--at", "480", "-1120", "--radius", "16", "--raise", "3"],
    "C_crack4": ["--at", "256", "-872", "--radius", "16", "--raise", "4"],
}
# session 5's lines (beach foam -> terrain, north) and session 6's border points (x = 256)
BEACH_LINES = {476.28: -1120.28, 479.64: -1120.18, 480.18: -1120.36}
CRACK_PTS = {"W": (254.37, -871.37), "E": (257.63, -871.37), "W2": (253.13, -873.61), "E2": (258.87, -873.61)}
STEP = 0.4375                                        # the on-foot step; the climb ceiling is 2.34375 per step


LAB = "FF9CustomMap-lab"


def _clear_lab():
    lab = A.GAME / LAB
    if lab.exists():
        shutil.rmtree(lab)


def run_cli(stage: Path, args) -> dict:
    """Run the CLI exactly as a user would -- ``--mod-folder FF9CustomMap-lab``, a folder NAME under the install (an
    absolute path outside it skips the disc-4 mirror: it resolves the game from the folder) -- into an EMPTY lab,
    then snapshot the lab's tree into ``stage`` and empty the lab again. The lab is not in FolderNames while this
    runs, so the live game never sees it."""
    _clear_lab()
    cmd = [sys.executable, "-m", "ff9mapkit", "world-terrain", "--mod-folder", LAB] + list(args)
    p = subprocess.run(cmd, cwd=str(KIT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    src = A.GAME / LAB / "FF9_Data"
    if src.is_dir():
        shutil.copytree(src, stage / "FF9_Data")
    _clear_lab()
    return {"argv": cmd[2:], "rc": p.returncode, "stdout": p.stdout[-6000:], "stderr": p.stderr[-3000:]}


def stage_files(stage: Path) -> dict:
    out = {}
    root = stage / "FF9_Data" / "WorldMap"
    if root.is_dir():
        for p in sorted(root.rglob("*")):
            if p.is_file() and p.suffix in (".ff9mesh", ".txt"):
                out[str(p.relative_to(stage)).replace("\\", "/")] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


_CELLS = {}
_MESH = {}


def _cells(stage):
    key = str(stage)
    if key not in _CELLS:
        folders = ([str(stage)] if stage else []) + BO.folder_names(A.GAME)
        _CELLS[key] = BO.scan_overrides(A.GAME, folders)
    return _CELLS[key]


def ground(stage, ns: int, x: float, z: float) -> dict:
    """The sky ground query at world (x, z) on namespace ``ns`` with ``stage`` (or None) first in FolderNames."""
    bx, by = int(math.floor(x / 64.0)), int(math.floor(-z / 64.0))
    key = (str(stage), ns, bx, by)
    if key not in _MESH:
        cf = _cells(stage).get((ns, bx, by), {})
        if cf:
            _pk, why, walk = A.live_walk_list(ns, bx, by, cf)
        else:
            walk, why = [(n, k, "stock") for n, k in A.stock_walk_list(ns, bx, by)], "stock"
        _MESH[key] = (A.load_walk_arrays(walk), why)
    ms, why = _MESH[key]
    lx, lz = x - bx * 64.0, z + by * 64.0
    for name, V, ids in ms:
        if V.size == 0:
            continue
        a, b, c = V[:, 0], V[:, 1], V[:, 2]
        u, v = b - a, c - a
        cy = u[:, 2] * v[:, 0] - u[:, 0] * v[:, 2]
        L = np.linalg.norm(np.cross(u, v), axis=1)
        L[L == 0] = 1.0
        d = (b[:, 2] - c[:, 2]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 2] - c[:, 2])
        ok = (cy / L > 0.1) & ~np.isin(ids, A.IDALL_SKIP) & (np.abs(d) >= 1e-12)
        dd = np.where(ok, d, 1.0)
        w0 = ((b[:, 2] - c[:, 2]) * (lx - c[:, 0]) + (c[:, 0] - b[:, 0]) * (lz - c[:, 2])) / dd
        w1 = ((c[:, 2] - a[:, 2]) * (lx - c[:, 0]) + (a[:, 0] - c[:, 0]) * (lz - c[:, 2])) / dd
        w2 = 1 - w0 - w1
        hit = np.nonzero(ok & (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9))[0]
        if hit.size == 0:
            continue
        t = hit[0]
        idv = int(ids[t])
        if idv == A.VETO:
            continue
        return {"y": round(float(w0[t] * a[t, 1] + w1[t] * b[t, 1] + w2[t] * c[t, 1]), 4), "topo": (idv & 0xFC) >> 2,
                "event": (idv & 0xC000) >> 14, "area": (idv & 0x3F00) >> 8, "part": name, "src": why}
    return {"y": None, "topo": None, "event": None, "part": "MISS", "src": why}


def ring(stage, ns, x, z, r):
    """Ground on 8 bearings at radius r (where a short walk from the landing ends)."""
    return {f"{b}": ground(stage, ns, x + r * math.cos(math.radians(b)), z + r * math.sin(math.radians(b)))["y"]
            for b in range(0, 360, 45)}


def beach_profile(stage, x, z0):
    """Ground every STEP north from the foam start: the steepest per-step rise (the climb gate) and the heights."""
    ys = [ground(stage, 1, x, z0 + k * STEP)["y"] for k in range(0, 17)]
    rises = [b - a for a, b in zip(ys, ys[1:]) if a is not None and b is not None]
    return {"start": ys[0], "end": ys[-1], "max_step_rise": round(max(rises), 4) if rises else None, "ys": ys}


def main():
    import ff9mapkit
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    res = {"landing": LANDING, "stored_y": STORED_Y, "stages": {}}
    # the guard's DEFAULT verdict on the +4 edit (no flag): it must refuse and write nothing
    probe = STAGE / "_guard_default"
    shutil.rmtree(probe, ignore_errors=True)
    probe.mkdir(parents=True)
    r = run_cli(probe, [a for a in STAGES["A_raise4"] if a != "--allow-entrances"])
    res["guard_default_raise4"] = {"rc": r["rc"], "refused": "REFUSED" in (r["stdout"] + r["stderr"]),
                                   "files": stage_files(probe), "tail": (r["stdout"] + r["stderr"])[-900:]}
    print("guard default on +4:", res["guard_default_raise4"]["rc"], res["guard_default_raise4"]["refused"],
          len(res["guard_default_raise4"]["files"]), "files")
    for name, args in STAGES.items():
        st = STAGE / name
        shutil.rmtree(st, ignore_errors=True)
        st.mkdir(parents=True)
        r = run_cli(st, args)
        res["stages"][name] = {"cli": r, "files": stage_files(st)}
        print(f"{name}: rc {r['rc']}, {len(res['stages'][name]['files'])} files", flush=True)
        if r["rc"] != 0:
            print(r["stdout"][-1500:], r["stderr"][-1500:])
    # ---- predictions
    g0 = ground(None, 1, *LANDING)
    res["guard"] = {"stock": g0, "stock_ring6": ring(None, 1, *LANDING, 6.0)}
    for name in ("A_lower3", "A_raise1", "A_raise4"):
        st = STAGE / name
        gl = ground(st, 1, *LANDING)
        res["guard"][name] = {"landing": gl, "ring6": ring(st, 1, *LANDING, 6.0),
                              "above_stored": None if gl["y"] is None else round(gl["y"] - STORED_Y, 4)}
        print(f"  {name}: new ground at the landing {gl['y']} ({res['guard'][name]['above_stored']:+} vs stored "
              f"{STORED_Y}), ring6 {res['guard'][name]['ring6']}")
    res["beach"] = {"stock": {x: beach_profile(None, x, z) for x, z in BEACH_LINES.items()},
                    "B_beach3": {x: beach_profile(STAGE / "B_beach3", x, z) for x, z in BEACH_LINES.items()}}
    for x in BEACH_LINES:
        print(f"  beach x {x}: stock max step {res['beach']['stock'][x]['max_step_rise']}  B_beach3 max step "
              f"{res['beach']['B_beach3'][x]['max_step_rise']}  start {res['beach']['B_beach3'][x]['start']} end "
              f"{res['beach']['B_beach3'][x]['end']}")
    st = STAGE / "C_crack4"
    res["replay"] = {k: {"disc1": ground(st, 1, *p)["y"], "disc4": ground(st, 4, *p)["y"],
                         "disc4_stock": ground(None, 4, *p)["y"]} for k, p in CRACK_PTS.items()}
    print("  replay:", res["replay"])
    out = HERE / "out" / "r3_build.json"
    out.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print("->", out)


if __name__ == "__main__":
    main()
