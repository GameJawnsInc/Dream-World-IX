"""`world-mountain --donor 19,3` IN GAME, the build: a desert island carved three ways through the kit's own commands.

comp23 (census.py) is a desert massif: 139 rock tris (all topograph 49), radius 26.1u, peak 12.5u over its rim, on a
desert coast at home (home_render.py). It is carried onto a DESERT island, its own ground (sweep.py: 6/6 angles).
The lab island (out/lab/island, gitignored): `world-island --center 1380,-100 --radius 55 --lobes 1 --patches 0
--seed 42 --ground desert`, blocks (20,0)-(22,2), open ocean no live folder touches (the sweep's bench). Each
variant is a copy of it carved by `world-mountain --donor 19,3 --ground desert --near 1380,-100`:
  A  --rot 0                      the verbatim carry
  B  --rot 200                    a free angle (round 16 proved rotation on Uaho; this is another donor)
  C  --rot 30 --rock-height 1.5   taller, as X1 passed for Uaho
RUN:  py studies/terrain-malleability/mountaindonors/lab_build.py   (then lab_prep.py)
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LAB = HERE / "out" / "lab"
NAME = "FF9CustomMap-lab"
CENTER = "1380,-100"
ISLAND = ["--center", CENTER, "--radius", "55", "--lobes", "1", "--patches", "0", "--seed", "42", "--ground", "desert"]
CARVE = ["--donor", "19,3", "--ground", "desert", "--near", CENTER]
VARIANTS = {"A": ["--rot", "0"], "B": ["--rot", "200"], "C": ["--rot", "30", "--rock-height", "1.5"]}


def kit(*args) -> None:
    r = subprocess.run([sys.executable, "-m", "ff9mapkit", *args], cwd=ROOT / "ff9mapkit", capture_output=True,
                       text=True)
    for line in (r.stdout + r.stderr).strip().splitlines()[-5:]:
        print("   " + line[:240])
    if r.returncode:
        raise SystemExit(f"exit {r.returncode}: {' '.join(args[:1])}")


def main():
    island = LAB / "island" / NAME
    if not (island / "FF9_Data").is_dir():
        island.mkdir(parents=True, exist_ok=True)
        print("== the island")
        kit("world-island", "--mod-folder", str(island), *ISLAND, "--skip-mirror")
    for v, extra in VARIANTS.items():
        dst = LAB / v / NAME
        if dst.parent.exists():
            shutil.rmtree(dst.parent)
        shutil.copytree(island, dst)
        print(f"== {v} {' '.join(extra)}")
        kit("world-mountain", "--mod-folder", str(dst), *CARVE, *extra, "--skip-mirror")


if __name__ == "__main__":
    main()
