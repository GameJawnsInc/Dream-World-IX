"""comp26 with its canopy IN GAME (mountaindonors/STEP.md), the build: one desert island carved four ways.

The lab island (out/lab/island, gitignored) is round 19's desert lab: `world-island --ground desert --center 1380,-100
--radius 55 --lobes 1 --patches 0 --seed 42`, blocks (20,0)-(22,2), open ocean no live folder touches, with
world-environment's `mist = false` Environment.txt. It holds STEP.md's r51 bench footprint.

The CLI cannot carry comp26's canopy yet (it is not catalogued), so each variant runs the CLI's own steps in-process
with the one difference named, as snowmassif/lab_build.py does: `read_deployed_blocks` -> `carve_mountain(...,
alcove=<the canopy spec>)` -> `census_gate(parts=census_parts, stack=)` -> `deploy_changed` + `deploy_mountain_parts`.
The spec is mountaindonors/step_carry.py's registered rule (the walled topo-38 canopy behind the rim's step).
grid_probe.py found every angle carving from near= the island centre (rot 0 11/25, 90 17/25, 200 14/25, 270 19/25):
  A  --rot 0      B  --rot 90      C  --rot 200      D  --rot 270      all near (1380, -100)
RUN:  py studies/terrain-malleability/canopystep/lab_build.py   (then lab_prep.py)
      CANOPY_DONOR=comp10 for round 23 (rounds.py: a grass island r66 at (1380, -96), comp10 on 14-16,14)
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
sys.path.insert(0, str(HERE))
import rounds  # noqa: E402  ($CANOPY_DONOR: comp26 = round 22, the default; comp10 = round 23)
LAB = rounds.LAB
NAME = "FF9CustomMap-lab"
ISLAND = rounds.R["island"]
NEAR = rounds.R["near"]
VARIANTS = rounds.R["variants"]


def kit(*args) -> None:
    r = subprocess.run([sys.executable, "-m", "ff9mapkit", *args], cwd=ROOT / "ff9mapkit", capture_output=True,
                       text=True)
    for line in (r.stdout + r.stderr).strip().splitlines()[-6:]:
        print("   " + line[:240])
    if r.returncode:
        raise SystemExit(f"exit {r.returncode}: {' '.join(args[:1])}")


def carve(folder: Path, rot: int) -> dict:
    import step_carry as C                    # the donor, its canopy spec, and the worktree-pinned kit import
    IN, _, _ = C.S._kit()
    from ff9mapkit.world import discmirror as DM
    donor = C.DONORS[rounds.NAME][0]
    spec, ncomp = C.canopy_spec(donor)
    blocks = IN.read_deployed_blocks(str(folder), near=NEAR, reach=140.0, disc=1)
    lines: list = []
    res = IN.carve_mountain(IN.soup_from_blocks(blocks), near=NEAR, donor=donor, rot_deg=rot, ground=rounds.R["ground"],
                            alcove=spec, disc=1, log=lines.append)
    IN.census_gate(res["changed"], disc=1, baseline=blocks, parts=IN.census_parts(res), log=lines.append,
                   stack=IN.read_deployed_stack(str(folder), blocks, disc=1))
    w = list(IN.deploy_changed(res["changed"], mod_folder=str(folder), disc=1, skip_mirror=DM.DEFERRED,
                               log=lines.append))
    w += list(IN.deploy_mountain_parts(res, mod_folder=str(folder), disc=1, skip_mirror=DM.DEFERRED,
                                       log=lines.append))
    for s in lines[-6:]:
        print("   " + str(s)[:240])
    rep = res["report"]
    return {"rot": rot, "near": list(NEAR), "spec": spec, "canopy_tris": ncomp, "center": list(res["center"]),
            "teleport": list(rep["teleport"]), "written": len(w),
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
    for v, rot in VARIANTS.items():
        dst = LAB / v / NAME
        if dst.parent.exists():
            shutil.rmtree(dst.parent)
        shutil.copytree(island, dst)
        print(f"== {v} rot {rot}")
        built[v] = carve(dst, rot)
        print(f"   {built[v]}")
    (LAB / "build.json").write_text(json.dumps(built, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
