"""BUILD + REGISTERED PREDICTIONS for in-game round 12 (2026-10-09): ISLAND CLUSTERS -- `world-sink` on an island whose
water joins its neighbours'. Writes ONLY into staging folders under ingame/out/r12_stage/ (gitignored), through the
scratch mod folder FF9CustomMap-lab (emptied around every build; not in FolderNames while this runs).

THE SITES (`world-sink --list`, land2sea/sh_c5_census.py):
  A  Shimmering Island's main island, (6,4)-(7,5), `--at 441.992 -311.975 --allow-entrances`: its coastal sea runs on
     into its seven islets', so it sinks ALONE by its footprint: its land becomes water, every water tri round it and
     every islet stays -- the way disc 4 itself removed it and kept the islets. Its entrance tiles go with it (lab only).
     Disc 4 has no island there: the replay refuses and disc 4 keeps its own (already sunk) ground.
  C  the (8,16) pair, `--at 545.379 -1070.376 --cluster`: two islands whose water joins, sunk together as one.
  W  round 11's shelf-edge island (4,15), `--at 278.667 -1006.732`: the whole-tile sink again, now with THE SPLIT WELD
     (kept coastal tris running past a re-tiled tile's corner are split there): round 11's readings must hold.
THE FILES (the kit's CLI, as a user would run it, all three into one folder):
  FULL  A, C, W (Disc1 + the replays on Disc4)
  OLD   the same with --skip-mirror (Disc1 only)
THE STAGES (lab, disc / world):
  d1_stock   -     1 / 9011   on foot: the read points stand on the islands (stock heights)
  d1_sink    FULL  1 / 9011   on foot: water where the islands stood; Shimmering's islets keep their heights
  boatA_stock / boatA_sink, boatC_stock / boatC_sink   - / FULL   1 / 9003   the Blue Narciss, eastbound across A's and
             C's lanes: it STOPS at the island on stock, and sails across where it stood once sunk
  d4_old     OLD   4 / 9008   on foot: disc 4's own ground everywhere (no Shimmering main island; C and W stand)
  d4_sink    FULL  4 / 9008   on foot: C and W water; Shimmering's ground is disc 4's own (the replay refused there)
Writes out/r12_build.json.
Run:  py studies/terrain-malleability/ingame/r12_build.py
"""
from __future__ import annotations

import json
import math
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r3_build as RB                                # noqa: E402  (the sky ground query, the lab)
import r11_build as R11                              # noqa: E402  (walk sink, kit, snapshot, the boat lane)

STAGE = HERE / "out" / "r12_stage"
LAB = "FF9CustomMap-lab"
SITES = {"A": ((441.992, -311.975), ["--allow-entrances"]),
         "C": ((545.379, -1070.376), ["--cluster"]),
         "W": ((278.667, -1006.732), [])}
STAGES = {   # name: (files, disc, kind, site)
    "d1_stock": (None, 1, "foot", None),
    "d1_sink": ("FULL", 1, "foot", None),
    "boatA_stock": (None, 1, "boat", "A"),
    "boatA_sink": ("FULL", 1, "boat", "A"),
    "boatC_stock": (None, 1, "boat", "C"),
    "boatC_sink": ("FULL", 1, "boat", "C"),
    "d4_old": ("OLD", 4, "foot", None),
    "d4_sink": ("FULL", 4, "foot", None),
}


def site_plan(site):
    from ff9mapkit.world import transplant as TR
    at, extra = SITES[site]
    plan, rep = TR.sink_auto_plan(at, cluster="--cluster" in extra)
    return sorted({tuple(b) for b in rep["blocks"]} | set(plan)), rep


def water_points(full: Path, site: str, blocks, n=3) -> dict:
    """Points on the site's land on disc 1 that the FULL files turn to water: the summit, then one per new water class
    (off the 4u lattice, 2u pitch)."""
    rows = []
    for (bx, by) in blocks:
        for i in range(0, 64, 2):
            for j in range(0, 64, 2):
                x, z = bx * 64.0 + i + 0.37, -by * 64.0 - j - 0.63
                a = RB.ground(None, 1, x, z)
                if a["part"] not in ("Terrain", "Beach1"):
                    continue
                f = RB.ground(full, 1, x, z)
                if f["part"] not in ("Sea3", "Sea4", "Sea5"):
                    continue
                rows.append((a["y"], (round(x, 2), round(z, 2)), (f["part"], f["topo"])))
    rows.sort()
    pts = {f"{site}1": rows[-1][1]}
    seen = {rows[-1][2]}
    for r in reversed(rows):
        if len(pts) >= n:
            break
        if r[2] not in seen and r[0] > 0.2:
            seen.add(r[2])
            pts[f"{site}{len(pts) + 1}"] = r[1]
    if len(pts) < n:                                    # a second point on the island, far from the first
        far = max(rows, key=lambda r: math.dist(r[1], rows[-1][1]))
        pts[f"{site}{len(pts) + 1}"] = far[1]
    return pts


def kept_points(full: Path, blocks, k=2) -> dict:
    """Points on Shimmering's islets: Terrain on disc 1 both stock and with FULL, at the same height (kept), the highest
    of ``k`` islets at least 12u apart."""
    rows = []
    for (bx, by) in blocks:
        for i in range(0, 64, 2):
            for j in range(0, 64, 2):
                x, z = bx * 64.0 + i + 0.37, -by * 64.0 - j - 0.63
                a = RB.ground(None, 1, x, z)
                if a["part"] != "Terrain" or a["y"] < 0.5:
                    continue
                f = RB.ground(full, 1, x, z)
                if f["part"] != "Terrain" or abs(f["y"] - a["y"]) > 1e-4:
                    continue
                rows.append((a["y"], (round(x, 2), round(z, 2))))
    rows.sort(reverse=True)
    out = []
    for y, p in rows:
        if all(math.dist(p, q) > 12.0 for q in out):
            out.append(p)
        if len(out) == k:
            break
    return {f"K{n + 1}": p for n, p in enumerate(out)}


def main():
    import ff9mapkit
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    shutil.rmtree(STAGE, ignore_errors=True)
    files = STAGE / "files"
    res = {"sites": {s: list(v[0]) for s, v in SITES.items()}, "args": {s: v[1] for s, v in SITES.items()},
           "receipts": {}, "files": {}, "stages": {}, "blocks": {}, "plans": {}}
    for s in SITES:
        blocks, rep = site_plan(s)
        res["blocks"][s] = blocks
        res["plans"][s] = {k: rep.get(k) for k in ("fill", "tiles", "land_tris", "land_u2", "bands", "fill_tris",
                                                   "cells_whole", "cells_partial", "split_tris", "keel_to_open",
                                                   "members", "entrance_tris")}
    RB._clear_lab()
    for s, (at, extra) in SITES.items():
        out = R11.kit(["world-sink", "--mod-folder", LAB, "--at", str(at[0]), str(at[1]), "--dry-run"] + extra)
        res["receipts"][f"dry_run_{s}"] = out
        assert "dry run: gates CLEAN" in out, out[-2500:]
    for name, flag in (("FULL", []), ("OLD", ["--skip-mirror"])):
        RB._clear_lab()
        for s, (at, extra) in SITES.items():
            res["receipts"][f"{name}_{s}"] = R11.kit(["world-sink", "--mod-folder", LAB, "--at", str(at[0]),
                                                      str(at[1])] + extra + flag)
        res["files"][name] = R11.snapshot(files / name)
    RB._clear_lab()
    full, old = res["files"]["FULL"], res["files"]["OLD"]
    assert old and all("/Disc1/" in k for k in old), sorted(old)
    assert all(full[k] == old[k] for k in old)
    d4 = sorted(k for k in full if "/Disc4/" in k)
    shim = {f"Block[{b[0]}][{b[1]}]" for b in res["blocks"]["A"]}
    assert not any(any(c in k for c in shim) for k in d4), "the Shimmering replay should refuse on disc 4"
    res["all_blocks"] = sorted({b for bs in res["blocks"].values() for b in bs})
    pts = {}
    for s in SITES:
        pts.update(water_points(files / "FULL", s, res["blocks"][s], n=3 if s == "A" else 2))
    pts.update(kept_points(files / "FULL", res["blocks"]["A"]))
    res["points"] = pts
    res["boat"] = {s: R11.boat_lane(files / "FULL", s, res["blocks"][s]) for s in ("A", "C")}
    for name, (fset, disc, kind, site) in STAGES.items():
        stage = (files / fset) if fset else None
        row = {"files": fset, "disc": disc, "kind": kind, "site": site,
               "lab_files": sum(1 for k in (res["files"][fset] if fset else {}) if f"/Disc{disc}/" in k)}
        if kind == "foot":
            row["points"] = {k: dict(g, y_foot=R11.foot_y(g)) for k, p in pts.items()
                             for g in [RB.ground(stage, disc, *p)]}
        else:
            row["boat"] = {"pass": fset is not None}
        res["stages"][name] = row
        print(f"{name:12s} {fset or '-':4s} disc {disc} {kind:4s} lab files {row['lab_files']:2d}  "
              + ("  ".join(f"{k} {v['part']} t{v['topo']} {v['y_foot']}" for k, v in row.get("points", {}).items())
                 or f"boat {site} {'PASSES' if fset else 'STOPS'}"))
    for s, b in res["boat"].items():
        print(f"boat lane {s}:", {k: b[k] for k in ("start", "span", "stock_progress", "stock_stop", "sunk_progress",
                                                     "island_x", "goal", "sunk_topos")})
    print("plans:", json.dumps(res["plans"]))
    out = HERE / "out" / "r12_build.json"
    out.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print("->", out)


if __name__ == "__main__":
    main()
