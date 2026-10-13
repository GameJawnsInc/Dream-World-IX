"""`world-mountain --donor` offline: every census-qualified massif (census.py), carried onto a bench of its OWN ground.

The census reads each massif's feet: comp10 stands on grass and forest, comp23 and comp26 on desert (topo 17),
comp9 and comp19 on snow (topo 27). A massif carried onto a ground it never meets at home is a torn context (THE
OVERHANG-CONTEXT LAW), so each is carved onto a bench minted in its home ground family (`world-island --ground`,
`world-mountain --ground`). Uaho on grass is the control: it must pass, or the harness is wrong.

Bench: `build_landmass(center=CENTRE, base_radius=R, seed, lobes=1, n_patches=0, ground=g)`, the scan's sizing
R = ceil(radius + 28) (Uaho: r48, its in-game bench; the July scan's +16.5 left the control refusing at 4 of 6
angles where its apron met the island's block borders); written to .ff9mesh and read back, as a deploy would. Each carve runs
`carve_mountain(near=CENTRE, rot_deg=...)` + `census_gate(parts=changed_parts)`: every gate the kit runs.
  S1 the control passes at every angle;
  S2 per candidate: which angles pass, and the gate that refuses the others.
RUN:  py studies/terrain-malleability/mountaindonors/sweep.py   (writes out/sweep.json)
"""
from __future__ import annotations

import json
import math
import shutil
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CENTRE = (1380.0, -100.0)                 # open ocean, room on the grid for an r82 bench (blocks 20-22, 0-2)
# name: (donor blocks, census radius, ground)
DONORS = {
    "uaho":   ([(0, 0)], 20.0, "grass"),                                   # the control
    "comp26": ([(14, 3), (15, 3)], 19.3, "desert"),
    "comp23": ([(19, 3)], 26.1, "desert"),
    "comp19": ([(6, 2), (7, 2), (7, 3)], 35.4, "snow"),
    "comp10": ([(14, 14), (15, 14)], 37.4, "grass"),
    "comp9":  ([(8, 0), (8, 1), (9, 0), (9, 1), (10, 0)], 65.3, "snow"),
}
ROTS = (0, 90, 180, 270, 30, 200)
SEEDS = (42.0, 7.0, 11.0)                 # a bench mint that trips its own shape gates tries the next seed
_BENCH: dict = {}


def _kit():
    sys.path.insert(0, str(ROOT / "ff9mapkit"))
    import ff9mapkit
    assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__
    from ff9mapkit.world import interior as IN, mesh as M
    from ff9mapkit.world.island import build_landmass
    return IN, M, build_landmass


def bench(radius: int, ground: str):
    """The deployed-shape bench blocks (per process, cached)."""
    key = (radius, ground)
    if key not in _BENCH:
        IN, M, build_landmass = _kit()
        err = None
        for seed in SEEDS:
            tmp = Path(tempfile.mkdtemp(prefix="ff9_mtndonors_"))
            try:
                built = build_landmass(center=CENTRE, base_radius=float(radius), seed=seed, lobes=1, n_patches=0,
                                       ground=ground)
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
    name, rot = job
    IN, M, _ = _kit()
    donor, r_census, ground = DONORS[name]
    radius = math.ceil(r_census + 28.0)
    out = {"name": name, "rot": rot, "ground": ground, "bench_r": radius}
    lines: list = []
    try:
        blocks, seed = bench(radius, ground)
        out["seed"] = seed
        soup = IN.soup_from_blocks(blocks)
        res = IN.carve_mountain(soup, near=CENTRE, donor=donor, rot_deg=rot, ground=ground, log=lines.append)
        IN.census_gate(res["changed"], disc=1, baseline=blocks, parts=res.get("changed_parts"), log=lines.append)
        rep = res["report"]
        out.update(ok=True, center=res["center"],
                   **{k: rep.get(k) for k in ("blob_tris", "zip_rise", "rock_rigid", "apron_slope", "blocks")})
    except Exception as err:                                                    # noqa: BLE001
        out.update(ok=False, error=f"{type(err).__name__}: {err}"[:400])
    out["log"] = [str(x)[:200] for x in lines[-30:]]
    return out


def main():
    jobs = [(n, r) for n in DONORS for r in ROTS]
    with ProcessPoolExecutor(max_workers=4) as ex:
        rows = list(ex.map(one, jobs))
    print(f"{'donor':7s} {'ground':6s} {'bench':>5} {'rot':>4}  ok  centre              tris  zip-rise  rigid   apron")
    for r in rows:
        if not r["ok"]:
            print(f"{r['name']:7s} {r['ground']:6s} r{r['bench_r']:<4d} {r['rot']:>4}  FAIL {r['error'][:170]}")
            continue
        c = r["center"]
        print(f"{r['name']:7s} {r['ground']:6s} r{r['bench_r']:<4d} {r['rot']:>4}  ok  "
              f"({c[0]:.1f}, {c[1]:.1f})".ljust(20) + f" {r['blob_tris']:5d}  {r['zip_rise']:.2f}     "
              f"{r['rock_rigid'] * 100:.1f}%   {r['apron_slope']}")
    s1 = all(r["ok"] for r in rows if r["name"] == "uaho")
    print(f"S1 the control (uaho, grass) passes every angle: {'PASS' if s1 else 'FAIL -- the harness is wrong'}")
    for n in DONORS:
        okr = [r["rot"] for r in rows if r["name"] == n and r["ok"]]
        print(f"S2 {n}: {len(okr)}/{len(ROTS)} angles pass {okr}")
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "sweep.json").write_text(json.dumps(rows, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
