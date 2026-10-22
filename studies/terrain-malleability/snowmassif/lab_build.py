"""comp9, a snow massif, IN GAME (round 21), the build: one snow island carved three ways.

The lab island (out/lab/island, gitignored): `world-island --ground snow --center 1408,-96 --radius 88 --lobes 2
--patches 0 --seed 42`, blocks (20,0)-(22,2), open ocean no live folder touches, with world-environment's
`mist = false` Environment.txt. The offline bench (mountaindonors/sweep.py, r94 one-lobe at (1380, -100)) cannot be
deployed: no 4x4 window of disc 1 is open ocean free of live folders (it spills into real (21,3)), and a one-lobe
outline over ~r80 fails world-island's shape gate (med_turn < 8). site_probe.py found this island; grid_probe.py the
carve points (rot 0 10/36, 30 33/36, 200 5/36, 270 27/36 on a 4u grid; the rot-0 refusals are INLET.md's ny-0.093
stock face).

The CLI cannot carry comp9's inlet floor yet (`world-mountain` keeps `alcove="auto"`, Uaho's box only; INLET.md), so
each variant runs the CLI's own steps in-process with the one difference named: `read_deployed_blocks` ->
`carve_mountain(..., alcove=COMP9_INLET)` -> `census_gate(parts=census_parts, stack=)` -> `deploy_changed` +
`deploy_mountain_parts`, at each angle's near= point from grid_probe.json:
  A  --rot 0   near (1380, -88)      B  --rot 200 near (1384, -96)      C  --rot 270 near (1380, -96)
RUN:  py studies/terrain-malleability/snowmassif/lab_build.py   (then lab_prep.py)
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / "mountaindonors"))
LAB = HERE / "out" / "lab"
NAME = "FF9CustomMap-lab"
ISLAND = ["--ground", "snow", "--center", "1408,-96", "--radius", "88", "--lobes", "2", "--patches", "0",
          "--seed", "42"]
VARIANTS = {"A": (0, (1380.0, -88.0)), "B": (200, (1384.0, -96.0)), "C": (270, (1380.0, -96.0))}


def kit(*args) -> None:
    r = subprocess.run([sys.executable, "-m", "ff9mapkit", *args], cwd=ROOT / "ff9mapkit", capture_output=True,
                       text=True)
    for line in (r.stdout + r.stderr).strip().splitlines()[-6:]:
        print("   " + line[:240])
    if r.returncode:
        raise SystemExit(f"exit {r.returncode}: {' '.join(args[:1])}")


def carve(folder: Path, rot: int, near) -> dict:
    import inlet_floor as F                   # COMP9, COMP9_INLET, and the worktree-pinned kit import
    IN, _, _ = F._kit()
    from ff9mapkit.world import discmirror as DM
    blocks = IN.read_deployed_blocks(str(folder), near=near, reach=140.0, disc=1)
    lines: list = []
    res = IN.carve_mountain(IN.soup_from_blocks(blocks), near=near, donor=F.COMP9, rot_deg=rot, ground="snow",
                            alcove=F.COMP9_INLET, disc=1, log=lines.append)
    IN.census_gate(res["changed"], disc=1, baseline=blocks, parts=IN.census_parts(res), log=lines.append,
                   stack=IN.read_deployed_stack(str(folder), blocks, disc=1))
    w = list(IN.deploy_changed(res["changed"], mod_folder=str(folder), disc=1, skip_mirror=DM.DEFERRED,
                               log=lines.append))
    w += list(IN.deploy_mountain_parts(res, mod_folder=str(folder), disc=1, skip_mirror=DM.DEFERRED,
                                       log=lines.append))
    for s in lines[-8:]:
        print("   " + str(s)[:240])
    rep = res["report"]
    return {"rot": rot, "near": list(near), "center": list(res["center"]), "teleport": list(rep["teleport"]), "written": len(w),
            **{k: rep.get(k) for k in ("blob_tris", "plugs", "zip_rise", "rock_rigid", "apron_slope", "peak_y",
                                       "blocks")}}


def main():
    island = LAB / "island" / NAME
    if not (island / "FF9_Data").is_dir():
        island.mkdir(parents=True, exist_ok=True)
        print("== the island")
        kit("world-island", "--mod-folder", str(island), *ISLAND, "--skip-mirror")
        env = LAB / "mist_off.toml"
        env.write_text("[world_environment]\nmist = false\n", encoding="utf-8")
        kit("world-environment", "--mod-folder", str(island), str(env))
    built = {}
    for v, (rot, near) in VARIANTS.items():
        dst = LAB / v / NAME
        if dst.parent.exists():
            shutil.rmtree(dst.parent)
        shutil.copytree(island, dst)
        print(f"== {v} rot {rot}")
        built[v] = carve(dst, rot, near)
        print(f"   {built[v]}")
    (LAB / "build.json").write_text(json.dumps(built, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
