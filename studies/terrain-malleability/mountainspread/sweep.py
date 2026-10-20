"""`world-mountain --spread` offline: every qualified massif, widened in plan, on a bench of its own ground.

The five catalogued massifs (`world/data/donors.toml`, class massif) at spread x1.0 / x1.25 / x1.5 and four angles,
plus the uniform scale (spread = rock height) on the rock-only donors. Each carve is `carve_mountain(near=...)` +
`census_gate(parts=...)`, every gate the kit runs, on a `build_landmass` bench of the donor's HOME ground sized
R = ceil(r_census * spread + 28) (round 19's calibrated margin, scaled with the footprint), written to .ff9mesh and
read back as a deploy would.

Registered before the run (NOTES.md section 2):
  S1 the x1.0 rows reproduce round 19's verdicts (the harness is sound);
  S2 every angle that passes at x1.0 passes at x1.25 and x1.5;
  S3 the rock-rigid drift at x1.25 / x1.5 equals the x1.0 drift at the same angle to within 0.2 points;
  S4 every zip chord stays under the 9u edge gate (the RIM-GRAIN risk: rim edges grow s times).
RUN:  py studies/terrain-malleability/mountainspread/sweep.py   (writes out/sweep.json)
"""
from __future__ import annotations

import json
import math
import re
import shutil
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
# name: (donor blocks, census radius, home ground, rock-only)
DONORS = {
    "uaho":        ([(0, 0)], 20.0, "grass", True),
    "crag":        ([(10, 5), (10, 6)], 33.7, "desert", True),
    "comp20":      ([(12, 16), (12, 17)], 31.5, "grass", True),
    "desert-peak": ([(19, 3)], 26.1, "desert", True),
    "horseshoe":   ([(5, 15), (6, 15), (5, 16), (6, 16)], 54.3, "grass", False),
}
SPREADS = (1.0, 1.25, 1.5)
ROTS = (0, 90, 30, 200)
UNIFORM_ROTS = (0, 30)                     # spread = rock height = 1.5, rock-only donors
SEEDS = (42.0, 7.0, 11.0)
_BENCH: dict = {}


def centre_for(radius: int):
    """Open ocean in the NE corner (blocks 19-23, 0-4); z pulled south so the bench never crosses z = 0."""
    return (1380.0, -float(max(100, radius + 20)))


def _kit():
    sys.path.insert(0, str(ROOT / "ff9mapkit"))
    import ff9mapkit
    assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__
    from ff9mapkit.world import interior as IN, mesh as M
    from ff9mapkit.world.island import build_landmass
    return IN, M, build_landmass


def bench(radius: int, ground: str):
    key = (radius, ground)
    if key not in _BENCH:
        IN, M, build_landmass = _kit()
        err = None
        for seed in SEEDS:
            tmp = Path(tempfile.mkdtemp(prefix="ff9_mtnspread_"))
            try:
                built = build_landmass(center=centre_for(radius), base_radius=float(radius), seed=seed, lobes=1,
                                       n_patches=0, ground=ground)
                blocks = {}
                for blk, bm in built["blocks"].items():
                    p = M.write_ff9mesh(bm, tmp / f"m_{blk[0]}_{blk[1]}.ff9mesh")
                    blocks[blk] = M.blockmesh_from_ff9mesh(p, disc=1, x=blk[0], y=blk[1], part="terrain")
                _BENCH[key] = (blocks, seed)
                break
            except Exception as e:                                             # noqa: BLE001
                err = f"{type(e).__name__}: {e}"
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        else:
            raise RuntimeError(f"bench r{radius} {ground}: no seed mints clean ({err})")
    return _BENCH[key]


def one(job):
    name, spread, rot, height = job
    IN, M, _ = _kit()
    donor, r_census, ground, _ = DONORS[name]
    radius = math.ceil(r_census * spread + 28.0)
    out = {"name": name, "spread": spread, "rot": rot, "height": height, "ground": ground, "bench_r": radius}
    lines: list = []
    try:
        blocks, seed = bench(radius, ground)
        out["seed"] = seed
        soup = IN.soup_from_blocks(blocks)
        res = IN.carve_mountain(soup, near=centre_for(radius), donor=donor, rot_deg=rot, ground=ground,
                                spread=spread, rock_height=height, log=lines.append)
        IN.census_gate(res["changed"], disc=1, baseline=blocks, parts=res.get("changed_parts"), log=lines.append)
        rep = res["report"]
        chord = next((float(m.group(1)) for ln in lines
                      if (m := re.search(r"max chord ([0-9.]+)u", str(ln)))), None)
        out.update(ok=True, center=res["center"], chord=chord,
                   **{k: rep.get(k) for k in ("blob_tris", "zip_rise", "rock_rigid", "apron_slope", "peak_y",
                                              "blocks", "ensemble_tris")})
    except Exception as err:                                                    # noqa: BLE001
        out.update(ok=False, error=f"{type(err).__name__}: {err}"[:400])
    out["log"] = [str(x)[:200] for x in lines[-30:]]
    return out


def main():
    jobs = [(n, s, r, 1.0) for n in DONORS for s in SPREADS for r in ROTS]
    jobs += [(n, 1.5, r, 1.5) for n, d in DONORS.items() if d[3] for r in UNIFORM_ROTS]
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    with ProcessPoolExecutor(max_workers=workers) as ex:
        rows = list(ex.map(one, jobs))
    print(f"{'donor':12s} {'s':>4} {'h':>4} {'rot':>4} {'bench':>5}  ok   centre            chord  zipR  rigid  apron  peak")
    for r in rows:
        head = f"{r['name']:12s} {r['spread']:>4} {r['height']:>4} {r['rot']:>4} r{r['bench_r']:<4d}"
        if not r["ok"]:
            print(f"{head}  FAIL {r['error'][:150]}")
            continue
        c = r["center"]
        print(f"{head}  ok   ({c[0]:.0f}, {c[1]:.0f})".ljust(len(head) + 24)
              + f"{r['chord'] or 0:5.1f}  {r['zip_rise']:.2f}  {r['rock_rigid'] * 100:4.1f}%  {r['apron_slope']:5}"
              f"  {r['peak_y']}")
    base = {(r["name"], r["rot"]): r for r in rows if r["spread"] == 1.0 and r["height"] == 1.0}
    s2_bad, s3_bad = [], []
    for r in rows:
        b = base.get((r["name"], r["rot"]))
        if r["spread"] == 1.0 or r["height"] != 1.0 or not b or not b["ok"]:
            continue
        if not r["ok"]:
            s2_bad.append((r["name"], r["spread"], r["rot"]))
        elif abs(r["rock_rigid"] - b["rock_rigid"]) > 0.002:
            s3_bad.append((r["name"], r["spread"], r["rot"], b["rock_rigid"], r["rock_rigid"]))
    print("S1 x1.0 verdicts:", {n: [r["rot"] for r in rows if r["name"] == n and r["spread"] == 1.0
                                   and r["height"] == 1.0 and r["ok"]] for n in DONORS})
    print(f"S2 every x1.0-passing angle passes widened: {'PASS' if not s2_bad else f'FAIL {s2_bad}'}")
    print(f"S3 rigidity drift unchanged by spread (<= 0.2 pt): {'PASS' if not s3_bad else f'FAIL {s3_bad}'}")
    chords = [r["chord"] for r in rows if r["ok"] and r["chord"] is not None]
    print(f"S4 max zip chord over all clean carves: {max(chords) if chords else None} (gate 9.0)")
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "sweep.json").write_text(json.dumps(rows, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
