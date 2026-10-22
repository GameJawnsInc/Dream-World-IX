"""Round 21's site: where on disc 1 a snow island can hold comp9 with its inlet, at the lab's three angles.

The offline bench (mountaindonors/sweep.py: r94 at (1380, -100)) cannot deploy: no 4x4 window of disc 1 is open
ocean that no live folder touches, and r94 spills into real block (21,3). The lawful window is blocks (19,0)-(23,2).
For each island radius and seed: mint with the CLI (dry run refuses as the real mint would), then carve comp9 at
rot 0 / 200 / 270 exactly as lab_build.py does, every gate in-process, nothing written outside a temp folder.
RUN:  py studies/terrain-malleability/snowmassif/site_probe.py CX,CZ R[,R...] [LOBES [SEED,...] [CARVE_X,CARVE_Z]]
A one-lobe outline over ~r80 fails world-island's shape gate (med_turn < 8: too smooth for a stock coast).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / "mountaindonors"))
import inlet_floor as F  # noqa: E402

SEEDS = tuple(sys.argv[4].split(",")) if len(sys.argv) > 4 else ("42", "7", "11", "3", "5", "13", "17", "23")
LOBES = sys.argv[3] if len(sys.argv) > 3 else "1"
CARVE_AT = tuple(float(v) for v in sys.argv[5].split(",")) if len(sys.argv) > 5 else None   # the carve's near=, when it is not the mint centre
ROTS = (0, 200, 270)


def mint(folder: Path, centre: str, r: int, seed: str) -> str | None:
    p = subprocess.run([sys.executable, "-m", "ff9mapkit", "world-island", "--mod-folder", str(folder), "--ground",
                        "snow", "--center", centre, "--radius", str(r), "--lobes", LOBES, "--patches", "0", "--seed",
                        seed, "--skip-mirror"], cwd=ROOT / "ff9mapkit", capture_output=True, text=True)
    return None if p.returncode == 0 else (p.stdout + p.stderr).strip().splitlines()[-1][:110]


def carve(folder: Path, centre, rot: int) -> str:
    IN, _, _ = F._kit()
    try:
        blocks = IN.read_deployed_blocks(str(folder), near=centre, reach=140.0, disc=1)
        res = IN.carve_mountain(IN.soup_from_blocks(blocks), near=centre, donor=F.COMP9, rot_deg=rot, ground="snow",
                                alcove=F.COMP9_INLET, disc=1, log=lambda *a: None)
        IN.census_gate(res["changed"], disc=1, baseline=blocks, parts=IN.census_parts(res), log=lambda *a: None)
        rep = res["report"]
        return f"ok {tuple(round(v, 1) for v in res['center'])} zip {rep['zip_rise']} blocks {rep['blocks']}"
    except Exception as e:                                                   # noqa: BLE001
        return f"FAIL {type(e).__name__}: {str(e)[:150]}"


def main():
    centre_s = sys.argv[1]
    centre = tuple(float(v) for v in centre_s.split(","))
    for r in (int(v) for v in sys.argv[2].split(",")):
        for seed in SEEDS:
            tmp = Path(tempfile.mkdtemp(prefix="ff9_snowsite_"))
            try:
                err = mint(tmp, centre_s, r, seed)
                if err:
                    print(f"r{r} s{seed}: mint refused: {err}")
                    continue
                rows = {rot: carve(tmp, CARVE_AT or centre, rot) for rot in ROTS}
                n = sum(v.startswith("ok") for v in rows.values())
                print(f"r{r} s{seed}: {n}/3")
                for rot, v in rows.items():
                    print(f"   rot {rot:>3}: {v}")
                if n == 3:
                    return
            finally:
                shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
