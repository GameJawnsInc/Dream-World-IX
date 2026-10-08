"""BUILD + REGISTERED PREDICTIONS for in-game round 4 (2026-10-08): the July 2026 Dali freeze, and an edit the
relaxed slope gate newly allows. Writes ONLY into staging folders under ingame/out/r4_stage/ (gitignored), through
the scratch mod folder FF9CustomMap-lab (emptied around every build, not in FolderNames while this runs).

THE QUESTION. On 2026-07-01 "a hill at Dali froze the player in every direction" (commit 3e388d0d), read then as the
field exit setting him down at his stored height under raised ground. Round 3 refuted that mechanism: the world load
casts every actor down from the sky (ingame/RESULTS.md section 16). The July edit itself was never recorded (no
command, no transcript survives), and the same day's notes record a second, different trap at the same spot: the
castle copied as an Object override into Dali's own block (17,12), cell (35,25), next to Dali's landing cell (34,25),
whose mesh became collision ("3D collision you snag on ... stuck"; "I first misblamed Dali").
Stages, all landing at Dali's exit (field 350 entry 31 writes (1102.855, 26.574, -812.359)):
  D_raise4       world-terrain --at 1102.855 -812.359 --radius 16 --raise 4 (today's kit). The slope gate before
                 defect 23 REFUSED this ("ONE-WAY WALL in block (17, 12): slope 90.0 deg", guard_prep.py)
  D_hill24       world-deploy --block 17 12 --hill 24 (today's kit: seam pins, default r96). The likeliest July edit:
                 world-deploy's own help example, its default radius, on the block Dali's landing sits in
  D_hill24_july  the same command run by the kit as it stood on 2026-07-01 (`git archive 08de70ac`, no pins: the
                 terrain rises through the town's Object)
Writes out/r4_build.json.
Run:  py studies/terrain-malleability/ingame/r4_build.py   (from ff9mapkit/; needs the July kit extracted at
      $R4_JULY_KIT, default the session scratchpad's july/ff9mapkit)
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r3_build as RB                                # noqa: E402  (the sky ground query, stage_files, the lab)

STAGE = HERE / "out" / "r4_stage"
LANDING = (1102.855, -812.359)                       # 282331/256, -207964/256 (EVT_DALI_V_DL_WHL)
STORED_Y = 26.574
KIT = RB.KIT
JULY = Path(os.environ.get("R4_JULY_KIT", r"C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX"
                                           r"\324819f6-218e-4b1f-83b7-fdfc01b237f8\scratchpad\july\ff9mapkit"))
STAGES = {
    "D_raise4": (KIT, ["world-terrain", "--at", "1102.855", "-812.359", "--radius", "16", "--raise", "4"]),
    "D_hill24": (KIT, ["world-deploy", "--block", "17", "12", "--hill", "24"]),
    "D_hill24_july": (JULY, ["world-deploy", "--block", "17", "12", "--hill", "24"]),
}


def build(name, kit: Path, argv) -> dict:
    st = STAGE / name
    shutil.rmtree(st, ignore_errors=True)
    st.mkdir(parents=True)
    RB._clear_lab()
    cmd = [sys.executable, "-m", "ff9mapkit"] + argv + ["--mod-folder", RB.LAB]
    p = subprocess.run(cmd, cwd=str(kit), capture_output=True, text=True, encoding="utf-8", errors="replace")
    src = RB.A.GAME / RB.LAB / "FF9_Data"
    if src.is_dir():
        shutil.copytree(src, st / "FF9_Data")
    RB._clear_lab()
    return {"kit": str(kit), "argv": cmd[2:], "rc": p.returncode, "stdout": p.stdout[-5000:],
            "stderr": p.stderr[-2000:], "files": RB.stage_files(st)}


def main():
    import ff9mapkit
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    assert (JULY / "ff9mapkit" / "cli.py").is_file(), f"extract the July kit first: {JULY}"
    res = {"landing": LANDING, "stored_y": STORED_Y, "stages": {}}
    for name, (kit, argv) in STAGES.items():
        res["stages"][name] = r = build(name, kit, argv)
        print(f"{name}: rc {r['rc']}, {len(r['files'])} files", flush=True)
        if r["rc"] != 0:
            print(r["stdout"][-1200:], r["stderr"][-1200:])
    g0 = RB.ground(None, 1, *LANDING)
    res["stock"] = {"landing": g0, "ring6": RB.ring(None, 1, *LANDING, 6.0)}
    print("stock landing", g0)
    for name in STAGES:
        st = STAGE / name
        gl = RB.ground(st, 1, *LANDING)
        res[name] = {"landing": gl, "ring6": RB.ring(st, 1, *LANDING, 6.0),
                     "above_stored": None if gl["y"] is None else round(gl["y"] - STORED_Y, 4)}
        print(f"  {name}: landing {gl} ({res[name]['above_stored']:+} vs stored {STORED_Y}); ring6 {res[name]['ring6']}")
    out = HERE / "out" / "r4_build.json"
    out.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print("->", out)


if __name__ == "__main__":
    main()
