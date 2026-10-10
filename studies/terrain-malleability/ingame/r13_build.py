"""BUILD + REGISTERED PREDICTIONS for in-game round 13 (2026-10-09): ISLANDS WITH BUILDINGS -- `world-sink` on an island
with a building on it: the building (its Object, a waterfall, rivers) goes with the island and the hole it plugged
becomes water. Writes ONLY into staging folders under ingame/out/r13_stage/ (gitignored), through the scratch mod folder
FF9CustomMap-lab (emptied around every build; not in FolderNames while this runs).

THE SITES (`world-sink --list`, land2sea/sh_b1_buildings.py .. sh_b3_check.py), every one with --allow-entrances (its
entrance tiles go with it; lab only):
  D  Daguerreo, (5,15)-(7,16), `--at 425.098 -1020.0`: its water joins its neighbours', so it sinks ALONE by its
     footprint; its building -- 75 Object tris, a waterfall, rivers and their joints (and 2 terrain tris the falls
     carry) -- goes with it, and the 163.67 u2 hole they plugged is water too. Disc 4: its own Daguerreo, replayed.
  L  the lagoon island at (553, -1127), (8,17)-(10,17): the whole-tile sink, its hut (26 Object tris across its coast,
     in a notch of land and water) with it. Replayed on disc 4.
  O  the corner island at (0, 0): by its footprint, its 5-tri building with it. Disc 4's block is the same: copied.
THE FILES (the kit's CLI, as a user would run it, all three into one folder):
  FULL  D, L, O (Disc1 + Disc4)
  OLD   the same with --skip-mirror (Disc1 only)
THE STAGES (lab, disc / world):
  d1_stock   -     1 / 9011   on foot: the read points stand on the islands and on the buildings' roofs (stock)
  d1_sink    FULL  1 / 9011   on foot: water where the islands and their buildings stood; Daguerreo's neighbours keep
                              their heights
  boatD_stock / boatD_sink, boatL_stock / boatL_sink   - / FULL   1 / 9003   the Blue Narciss eastbound across D's and
             L's lanes: it STOPS at the island on stock, and sails across where it stood once sunk
  d4_old     OLD   4 / 9008   on foot: disc 4's own ground everywhere (the islands and buildings stand)
  d4_sink    FULL  4 / 9008   on foot: water where they stood, from the disc-4 replays (D, L) and the copy (O)
Writes out/r13_build.json.
Run:  py studies/terrain-malleability/ingame/r13_build.py
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
import r12_build as R12                              # noqa: E402  (water points, kept points)

STAGE = HERE / "out" / "r13_stage"
LAB = "FF9CustomMap-lab"
SITES = {"D": ((425.098, -1020.0), ["--allow-entrances"]),
         "L": ((553.065, -1127.103), ["--allow-entrances"]),
         "O": ((9.909, -22.582), ["--allow-entrances"])}
STAGES = {   # name: (files, disc, kind, site)
    "d1_stock": (None, 1, "foot", None),
    "d1_sink": ("FULL", 1, "foot", None),
    "boatD_stock": (None, 1, "boat", "D"),
    "boatD_sink": ("FULL", 1, "boat", "D"),
    "boatL_stock": (None, 1, "boat", "L"),
    "boatL_sink": ("FULL", 1, "boat", "L"),
    "d4_old": ("OLD", 4, "foot", None),
    "d4_sink": ("FULL", 4, "foot", None),
}


def site_plan(site):
    from ff9mapkit.world import transplant as TR
    at, _extra = SITES[site]
    plan, rep = TR.sink_auto_plan(at)
    return sorted({tuple(b) for b in rep["blocks"]} | set(plan)), rep


def roof_point(full: Path, site: str, blocks) -> dict:
    """A point on the building's roof: the ground query answers the Object there (topograph 59, stock's building
    roof; a party stands on it at its height) on BOTH discs at the same height, and the FULL files answer water. The
    highest such point, off the 4u lattice (1u pitch)."""
    rows = []
    for (bx, by) in blocks:
        for i in range(64):
            for j in range(64):
                x, z = bx * 64.0 + i + 0.37, -by * 64.0 - j - 0.63
                a = RB.ground(None, 1, x, z)
                if a["part"] != "Object" or a["topo"] != 59:
                    continue
                b = RB.ground(None, 4, x, z)
                if b["part"] != "Object" or abs(b["y"] - a["y"]) > 0.01:
                    continue
                f = RB.ground(full, 1, x, z)
                if f["part"] not in ("Sea3", "Sea4", "Sea5"):
                    continue
                rows.append((a["y"], (round(x, 2), round(z, 2))))
    assert rows, f"site {site}: no roof point"
    rows.sort()
    return {f"{site}B": rows[-1][1]}


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
                                                   "entrance_tris", "building", "plug_u2", "shore_tris")}
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
    # the building's parts are written under the engine's own names (RiverJoint, not Riverjoint)
    parts = sorted({k.rsplit("] ", 1)[1].split(".")[0] for k in full if "] " in k})
    res["parts"] = parts
    assert "RiverJoint" in parts and "Riverjoint" not in parts and "Object" in parts and "Falls" in parts, parts
    res["all_blocks"] = sorted({b for bs in res["blocks"].values() for b in bs})
    pts = {}
    for s in SITES:
        pts.update(R12.water_points(files / "FULL", s, res["blocks"][s], n=3 if s == "D" else 2))
        pts.update(roof_point(files / "FULL", s, res["blocks"][s]))
    pts.update(R12.kept_points(files / "FULL", res["blocks"]["D"]))
    res["points"] = pts
    res["boat"] = {s: R11.boat_lane(files / "FULL", s, res["blocks"][s]) for s in ("D", "L")}
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
    print("parts written:", parts)
    out = HERE / "out" / "r13_build.json"
    out.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print("->", out)


if __name__ == "__main__":
    main()
