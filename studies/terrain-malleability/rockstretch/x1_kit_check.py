"""X1 -> the kit: `world-mountain --rock-height` on the REAL Uaho donor, checked against the in-game build.

Carves the real Uaho massif (read from the install, alcove + aperture plug included) onto a flat 2x2-block grass
bench (the test suite's mains grid, interior seat) at x1.0 / x1.25 / x1.5 / x2.0, dry (nothing written), and checks:
  K1 every gate passes at every scale, and the rigidity drift stays within 0.001 of the rigid carry's (the gate
     measures against the declared stretched shape, so only the de-tilt's own distortion remains);
  K2 the kit pins the same 30 rock positions the in-game round pinned and stretches the same 53;
  K3 the largest rise equals the in-game variant's largest rise, per scale (the same map: X1 stretched the raw
     block, the kit the de-tilted blob, and b absorbs the tilt plane);
  K4 the rim, the plug and the apron are byte-identical to the rigid carry: only rock entries move, in y only.
Rerun: py studies/terrain-malleability/rockstretch/x1_kit_check.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
sys.path.insert(0, str(ROOT / "ff9mapkit" / "tests"))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__
from ff9mapkit.world import interior as IN, extract as X, mesh as M  # noqa: E402
import test_world_interior as TW  # noqa: E402  (the suite's mains-grid bench)

BUILD = json.loads((HERE / "out" / "x1" / "build.json").read_text(encoding="utf-8"))
SCALES = {"rigid": 1.0, "s125": 1.25, "s150": 1.5, "s200": 2.0}


def bench():
    return IN.soup_from_blocks({(bx, by): TW._grid_block(bx, by) for bx in (3, 4) for by in (3, 4)})


def main():
    out, fails = {}, []
    res = {}
    for name, s in SCALES.items():
        res[name] = IN.carve_mountain(bench(), center=(256.0, -256.0), rock_height=s, log=lambda *a: None)
        r = res[name]["report"]
        out[name] = {"rock_rigid": r["rock_rigid"], "peak_y": r["peak_y"], "rock_height": r["rock_height"],
                     "plugs": r["plugs"], "blob_tris": r["blob_tris"]}
    base = res["rigid"]
    for name, s in SCALES.items():
        r = res[name]["report"]
        if abs(r["rock_rigid"] - base["report"]["rock_rigid"]) > 1e-3 or r["rock_rigid"] >= IN.MTN_ROCK_RIGID:
            fails.append(f"K1 {name}: drift {r['rock_rigid']} vs rigid {base['report']['rock_rigid']}")
        if s == 1.0:
            continue
        rh = r["rock_height"]
        if (rh["pinned"], rh["free"]) != (BUILD["pinned"], BUILD["free"]):
            fails.append(f"K2 {name}: pinned/free {rh['pinned']}/{rh['free']} vs in-game {BUILD['pinned']}/{BUILD['free']}")
        live = M.read_ff9mesh(BUILD["live"])["verts"]
        var = M.read_ff9mesh(BUILD["variants"][name]["path"])["verts"]
        want = max(b[1] - a[1] for a, b in zip(live, var))
        if abs(rh["rise_max"] - want) > 0.01:
            fails.append(f"K3 {name}: largest rise {rh['rise_max']} vs in-game {want:.3f}")
        out[name]["x1_build_rise"] = round(want, 3)
        moved_other = 0
        for blk, bm in base["changed"].items():
            b2 = res[name]["changed"][blk]
            pa, pb = bm.chan_arrays[X.CH_POS], b2.chan_arrays[X.CH_POS]
            ta = bm.chan_arrays[X.CH_TAN]
            if len(pa) != len(pb) or bm.flat_index != b2.flat_index or bm.chan_arrays[X.CH_UV] != b2.chan_arrays[X.CH_UV]:
                fails.append(f"K4 {name} {blk}: topology or uv changed")
                continue
            for k in range(len(pa)):
                if pa[k] != pb[k]:
                    topo = X.decode_id(int(round(ta[k][0])))["topograph"]
                    if topo not in IN.MOUNTAIN_ROCK_TOPOS or (pa[k][0], pa[k][2]) != (pb[k][0], pb[k][2]):
                        moved_other += 1
        if moved_other:
            fails.append(f"K4 {name}: {moved_other} non-rock or plan moves")
    print(json.dumps(out, indent=1))
    print("K1-K4:", "PASS" if not fails else "FAIL")
    for f in fails:
        print("  ", f)
    (HERE / "out" / "x1" / "kit_check.json").write_text(json.dumps({"results": out, "fails": fails}, indent=1),
                                                         encoding="utf-8")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
