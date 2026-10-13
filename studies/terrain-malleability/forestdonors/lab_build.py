"""`world-forest --donor` IN GAME, the build: five carves of the lab island through the kit's own command.

The lab island (out/lab/island, gitignored): `world-island --center 1372,-84 --radius 58 --lobes 1 --patches 0
--seed 42 --mod-folder <out/lab/island/FF9CustomMap-lab>`, blocks (20,0)-(22,2), open ocean no live folder touches
(a x1.5 canopy needs ~11.5u of clear grass round its 44 x 62u: radius 48 had no lawful pocket for it).
The island is canopyspread's (copied from its out/lab/island). Each variant is a copy of it carved with one
census-qualified canopy (census.py), verbatim, at ONE shared centre (so the viewpoints are shared):
  A  --donor 15,15  the July donor, the control     B  --donor 3,12   long (85 tris, crosses a block border)
  C  --donor 19,8   round (75 tris, crosses one)     D  --donor 18,15  small (59 tris; a rock-touching blob that
  E  --donor 13,15  the grove (41 tris, crosses one)                    shares its block is skipped)
RUN:  py studies/terrain-malleability/forestdonors/lab_build.py   (then lab_prep.py)
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
CENTER = "1380,-92"            # the shared canopy centre: lawful for every donor (out/sweep.json)
VARIANTS = {"A": ["--donor", "15,15"], "B": ["--donor", "3,12"], "C": ["--donor", "19,8"],
            "D": ["--donor", "18,15"], "E": ["--donor", "13,15"]}


def main():
    island = LAB / "island" / NAME
    if not island.is_dir():
        shutil.copytree(HERE.parent / "canopyspread" / "out" / "lab" / "island" / NAME, island)
    assert (island / "FF9_Data").is_dir(), f"mint the island first: {island}"
    for v, extra in VARIANTS.items():
        dst = LAB / v / NAME
        if dst.parent.exists():
            shutil.rmtree(dst.parent)
        shutil.copytree(island, dst)
        cmd = [sys.executable, "-m", "ff9mapkit", "world-forest", "--mod-folder", str(dst), "--center", CENTER,
               "--skip-mirror", *extra]
        r = subprocess.run(cmd, cwd=ROOT / "ff9mapkit", capture_output=True, text=True)
        tail = (r.stdout + r.stderr).strip().splitlines()[-4:]
        print(f"== {v} {' '.join(extra) or '(verbatim)'}: exit {r.returncode}")
        for line in tail:
            print("   " + line[:240])
        if r.returncode:
            raise SystemExit(f"{v} failed")


if __name__ == "__main__":
    main()
