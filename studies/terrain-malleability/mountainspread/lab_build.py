"""`world-mountain --spread` IN GAME, the build: one grass island carved four ways through the kit's own commands.

The lab island (out/lab/island, gitignored): `world-island --center 1380,-100 --radius 58 --lobes 1 --patches 0
--seed 42`, blocks (20,0)-(22,2), open ocean no live folder touches (the sweep's r58 bench, which carries Uaho at
x1.5 at every angle), with world-environment's `mist = false` Environment.txt (round 16's lesson: the mist hides
texture). Each variant is a copy carved by `world-mountain --donor 0,0` (Uaho, the one donor with a full anatomy
study and the X1 / --rot rounds behind it) at ONE exact centre and 0 deg, so every panel shares its camera:
  A  rigid                         the verbatim carry (the control)
  B  --spread 1.25
  C  --spread 1.5
  D  --spread 1.5 --rock-height 1.5   the massif scaled whole
RUN:  py studies/terrain-malleability/mountainspread/lab_build.py   (then lab_prep.py)
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
ISLAND = ["--center", "1380,-100", "--radius", "58", "--lobes", "1", "--patches", "0", "--seed", "42"]
CENTER = sys.argv[1] if len(sys.argv) > 1 else "1386,-104"      # the sweep's x1.5 0-deg placement
CARVE = ["--donor", "0,0", "--center", CENTER, "--rot", "0"]
VARIANTS = {"A": [], "B": ["--spread", "1.25"], "C": ["--spread", "1.5"],
            "D": ["--spread", "1.5", "--rock-height", "1.5"]}


def kit(*args) -> None:
    r = subprocess.run([sys.executable, "-m", "ff9mapkit", *args], cwd=ROOT / "ff9mapkit", capture_output=True,
                       text=True)
    for line in (r.stdout + r.stderr).strip().splitlines()[-6:]:
        print("   " + line[:240])
    if r.returncode:
        raise SystemExit(f"exit {r.returncode}: {' '.join(args[:1])}")


def main():
    island = LAB / "island" / NAME
    if not (island / "FF9_Data").is_dir():
        island.mkdir(parents=True, exist_ok=True)
        print("== the island")
        kit("world-island", "--mod-folder", str(island), *ISLAND, "--skip-mirror")
        env = LAB / "mist_off.toml"
        env.write_text("[world_environment]\nmist = false\n", encoding="utf-8")
        kit("world-environment", "--mod-folder", str(island), str(env))
    for v, extra in VARIANTS.items():
        dst = LAB / v / NAME
        if dst.parent.exists():
            shutil.rmtree(dst.parent)
        shutil.copytree(island, dst)
        print(f"== {v} {' '.join(extra) or 'rigid'}")
        kit("world-mountain", "--mod-folder", str(dst), *CARVE, *extra, "--skip-mirror")


if __name__ == "__main__":
    main()
