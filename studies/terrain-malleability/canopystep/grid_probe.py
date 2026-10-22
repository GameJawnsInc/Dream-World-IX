"""comp26 with its canopy (mountaindonors/STEP.md), the carve points: on the lab island, which near= points carve it at
each angle. The island is round 19's desert lab (world-island --ground desert --center 1380,-100 --radius 55 --lobes 1
--patches 0 --seed 42), minted once into a temp folder; every (near, rot) on a 4u grid is carved with every gate, as
lab_build.py carves. Writes out/grid_probe.json.
RUN:  py studies/terrain-malleability/canopystep/grid_probe.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / "mountaindonors"))
import step_carry as C  # noqa: E402  (the donor, its canopy spec, the worktree-pinned kit)

ISLAND = ["--ground", "desert", "--center", "1380,-100", "--radius", "55", "--lobes", "1", "--patches", "0",
          "--seed", "42"]
DONOR = C.DONORS["comp26"][0]
ROTS = (0, 90, 200, 270)
XS = (1372.0, 1376.0, 1380.0, 1384.0, 1388.0)
ZS = (-108.0, -104.0, -100.0, -96.0, -92.0)
_FOLDER = None


def _init(folder):
    global _FOLDER
    _FOLDER = folder


def one(job):
    (x, z), rot = job
    IN, _, _ = C.S._kit()
    spec, _ = C.canopy_spec(DONOR)
    try:
        blocks = IN.read_deployed_blocks(_FOLDER, near=(x, z), reach=140.0, disc=1)
        res = IN.carve_mountain(IN.soup_from_blocks(blocks), near=(x, z), donor=DONOR, rot_deg=rot, ground="desert",
                                alcove=spec, disc=1, log=lambda *a: None)
        IN.census_gate(res["changed"], disc=1, baseline=blocks, parts=IN.census_parts(res), log=lambda *a: None)
        rep = res["report"]
        return {"near": [x, z], "rot": rot, "ok": True, "center": list(res["center"]), "zip_rise": rep["zip_rise"],
                "rock_rigid": rep["rock_rigid"], "apron_slope": rep["apron_slope"]}
    except Exception as e:                                                   # noqa: BLE001
        return {"near": [x, z], "rot": rot, "ok": False, "error": f"{type(e).__name__}: {str(e)[:160]}"}


def main():
    tmp = Path(tempfile.mkdtemp(prefix="ff9_canopygrid_"))
    try:
        r = subprocess.run([sys.executable, "-m", "ff9mapkit", "world-island", "--mod-folder", str(tmp), *ISLAND,
                            "--skip-mirror"], cwd=ROOT / "ff9mapkit", capture_output=True, text=True)
        if r.returncode:
            raise SystemExit((r.stdout + r.stderr)[-400:])
        jobs = [((x, z), rot) for rot in ROTS for x in XS for z in ZS]
        with ProcessPoolExecutor(max_workers=6, initializer=_init, initargs=(str(tmp),)) as ex:
            rows = list(ex.map(one, jobs))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for rot in ROTS:
        ok = [r for r in rows if r["rot"] == rot and r["ok"]]
        why = Counter(r["error"][:80] for r in rows if r["rot"] == rot and not r["ok"])
        print(f"rot {rot:>3}: {len(ok)}/{len(XS) * len(ZS)} pass; centres "
              f"{sorted({tuple(round(v) for v in r['center']) for r in ok})[:8]}")
        for w, n in why.most_common(3):
            print(f"          {n:>2} x {w}")
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "grid_probe.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
