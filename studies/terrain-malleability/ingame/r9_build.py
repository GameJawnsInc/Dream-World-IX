"""BUILD + REGISTERED PREDICTIONS for in-game round 9 (2026-10-09): the disc-4 replay of an in-place coast morph
(`world-transplant --in-place --cliff-bump`). Writes ONLY into staging folders under ingame/out/r9_stage/ (gitignored),
through the scratch mod folder FF9CustomMap-lab (emptied around every build; not in FolderNames while this runs).

THE SITE: (7,13), a straight north-facing cliff coast (crease y 4.84), one of the terrain study's 129 coastal cells that
disc 4 redrew (`r9_site_scan.py`; gap_disc4_edit_reach/s7_morph_replay.py). The window is the scanner's certified
cliff bump, depth 2.5: its middle column moves 2.48u north. The cliff band (topograph 58) is not walkable, so a walk
north from the lawn stops at its top edge, and the bump moves that edge.
THE FILES (the kit's CLI, as a user would run it):
  FULL  world-transplant --in-place ... (this fix: Disc1, plus the morph REPLAYED on disc 4's own ground)
  OLD   the same with --skip-mirror: Disc1 only -- exactly what the kit wrote before this fix on a cell disc 4 redrew
        (its mirror skipped the cell with one SKIP line)
THE STAGES (lab, disc):
  d1_stock  -     1   the walk stops at the stock edge (the control)
  d1_bump   FULL  1   it stops ~2.5u further north
  d4_old    OLD   4   it stops at disc 4's stock edge: the edit is missing on disc 4 (the defect, reproduced)
  d4_bump   FULL  4   it stops ~2.5u further north on disc 4 too (the fix)
Read points (teleport, sky cast, settle): R, 1.25u north of the middle column's stock edge (stock: the cliff face;
bumped: the lawn), and X, where disc 4's stock ground differs most from disc 1's and the bump changes neither: disc 4
re-cut 40 of the cell's 484 Terrain triangles at the window's east end (x 500-512), and there bumped disc 4 must still
read its own ground -- a replay; a copy of disc 1's edit would read disc 1's.
Writes out/r9_build.json.
Run:  py studies/terrain-malleability/ingame/r9_build.py
"""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r3_build as RB                                # noqa: E402  (the sky ground query, the lab)

STAGE = HERE / "out" / "r9_stage"
KIT = RB.KIT
LAB = "FF9CustomMap-lab"
CELL = (7, 13)
SPEC = None                                          # filled from the site scan: "X0,Z0:X1,Z1:DEPTH"
BEARING = 90.0                                       # north: the coast's seaward normal at the middle column
LINE_X = 484.37                                      # the walk line, 0.37u off the 4u lattice the column sits on
START_BACK = 6.0                                     # the walk starts this far south of the stock edge
WALK = 10.0
SIM = 0.05
TOL_STOP = 0.35
STAGES = {   # name: (files, disc)
    "d1_stock": (None, 1),
    "d1_bump": ("FULL", 1),
    "d4_old": ("OLD", 4),
    "d4_bump": ("FULL", 4),
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def kit(argv) -> str:
    p = subprocess.run([sys.executable, "-m", "ff9mapkit"] + argv, cwd=str(KIT), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert p.returncode == 0, (argv, p.stdout[-3000:], p.stderr[-3000:])
    return p.stdout


def snapshot(dst: Path) -> dict:
    lab = RB.A.GAME / LAB
    out = {}
    for q in sorted(lab.rglob("*")):
        if not q.is_file() or q.name.startswith(".ff9world") or ".bak-" in q.name:
            continue
        rel = q.relative_to(lab).as_posix()
        (dst / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(q, dst / rel)
        out[rel] = sha(q)
    return out


def ground(stage, disc, x, z) -> dict:
    g = RB.ground(stage, disc, x, z)
    return {k: g[k] for k in ("y", "topo", "part")}


def walk_stop(stage, disc, start) -> dict:
    """Where a walk north from ``start`` along x = LINE_X stops: the first point whose ground is not walkable
    (topograph outside WALK_OK) or not Terrain, sampled every SIM u."""
    from ff9mapkit.world.placement import WALK_OK
    u = (math.cos(math.radians(BEARING)), math.sin(math.radians(BEARING)))
    k = 0
    while k * SIM <= WALK:
        x, z = start[0] + k * SIM * u[0], start[1] + k * SIM * u[1]
        g = ground(stage, disc, x, z)
        if g["part"] != "Terrain" or g["topo"] not in WALK_OK:
            return {"progress": round((k - 1) * SIM, 3), "edge_z": round(z, 3), "beyond": g}
        k += 1
    return {"progress": None, "edge_z": None, "beyond": None}


def disc_diff_point(full: Path):
    """X: the Terrain point of the cell (any topograph: a teleport reads it) where disc 4's stock ground differs most
    from disc 1's and the bump changes neither (FULL reads stock on both discs there), sampled every 0.5u off the 4u
    lattice. A replay keeps disc 4's own ground there; a copy of disc 1's edit would put disc 1's there."""
    best = None
    ox, oz = CELL[0] * 64.0, -CELL[1] * 64.0
    for i in range(128):
        for j in range(128):
            x, z = ox + i * 0.5 + 0.07, oz - j * 0.5 - 0.07
            a, b = ground(None, 1, x, z), ground(None, 4, x, z)
            if a["y"] is None or b["y"] is None or a["part"] != "Terrain" or b["part"] != "Terrain":
                continue
            d = abs(a["y"] - b["y"])
            if best is not None and d <= best[0]:
                continue
            fa, fb = ground(full, 1, x, z), ground(full, 4, x, z)
            if fa == a and fb == b:
                best = (d, (round(x, 2), round(z, 2)))
    return best


MID = None


def main():
    global SPEC, MID
    import ff9mapkit
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    scan = json.loads((HERE / "out" / "r9_site_scan.json").read_text(encoding="utf-8"))
    site = next(r for r in scan["ranked"] if tuple(r["cell"]) == CELL)
    (p0, p1), depth = site["window"], site["depth"]
    SPEC = f"{p0[0]},{p0[1]}:{p1[0]},{p1[1]}:{depth}"
    MID = (site["discs"]["1"]["crease"][0], site["discs"]["1"]["crease"][2])
    assert site["discs"]["1"]["cardinal"] == BEARING and site["discs"]["4"]["cardinal"] == BEARING, site
    shutil.rmtree(STAGE, ignore_errors=True)
    files = STAGE / "files"
    c = f"{CELL[0]},{CELL[1]}"
    base = ["world-transplant", "--mod-folder", LAB, "--in-place", "--cell", c, "--donor", c, "--cliff-bump", SPEC]
    res = {"cell": CELL, "spec": SPEC, "bearing": BEARING, "line_x": LINE_X, "mid_crease": MID,
           "d_mid": site["discs"]["1"]["d_mid"], "receipts": {}, "files": {}, "stages": {}}
    RB._clear_lab()
    res["receipts"]["dry_run"] = kit(base + ["--dry-run"])
    assert "disc 4: the replay passes its gates -- the deploy edits both discs" in res["receipts"]["dry_run"]
    for name, extra in (("FULL", []), ("OLD", ["--skip-mirror"])):
        RB._clear_lab()
        res["receipts"][name] = kit(base + extra)
        res["files"][name] = snapshot(files / name)
    RB._clear_lab()
    full, old = res["files"]["FULL"], res["files"]["OLD"]
    r = f"r{CELL[1]}/Block[{CELL[0]}][{CELL[1]}]"
    assert sorted(old) == [f"FF9_Data/WorldMap/Disc1/0_1/{r} Sea4.ff9mesh",
                           f"FF9_Data/WorldMap/Disc1/0_1/{r} Terrain.ff9mesh"], sorted(old)
    assert sorted(full) == sorted(list(old) + [k.replace("Disc1", "Disc4") for k in old]), sorted(full)
    assert all(full[k] == old[k] for k in old)                            # disc 1's bytes: the same edit
    assert full[f"FF9_Data/WorldMap/Disc4/0_1/{r} Terrain.ff9mesh"] != full[f"FF9_Data/WorldMap/Disc1/0_1/{r} Terrain.ff9mesh"]
    assert f"REPLAYED {CELL} on Disc4" in res["receipts"]["FULL"], res["receipts"]["FULL"][-2000:]
    start = (LINE_X, MID[1] - START_BACK)
    R = (LINE_X, round(MID[1] + 1.25, 2))
    X = disc_diff_point(files / "FULL")
    res["start"], res["R"], res["X"] = start, R, (X[1] if X else None)
    res["X_disc_gap"] = round(X[0], 3) if X else None
    for name, (fset, disc) in STAGES.items():
        stage = (files / fset) if fset else None
        stock = walk_stop(None, disc, start)
        w = walk_stop(stage, disc, start)
        row = {"files": fset, "disc": disc, "walk": w, "walk_stock": stock,
               "R": ground(stage, disc, *R), "R_stock": ground(None, disc, *R),
               "X": ground(stage, disc, *X[1]) if X else None,
               "lab_parts": sorted({k.split("] ")[1].split(".")[0] for k in (res["files"][fset] if fset else {})
                                    if f"/Disc{disc}/" in k})}
        res["stages"][name] = row
        print(f"{name:9s} {fset or '-':4s} disc {disc}: stop at z {w['edge_z']} (progress {w['progress']}; stock "
              f"{stock['progress']})  R y {row['R']['y']} topo {row['R']['topo']}  X y "
              f"{row['X']['y'] if row['X'] else None}  lab parts read {row['lab_parts']}")
    s = res["stages"]
    gain1 = s["d1_bump"]["walk"]["progress"] - s["d1_stock"]["walk"]["progress"]
    gain4 = s["d4_bump"]["walk"]["progress"] - s["d4_old"]["walk"]["progress"]
    res["gain"] = {"disc1": round(gain1, 3), "disc4": round(gain4, 3)}
    print(f"the bump moves the stop {gain1:.2f}u north on disc 1 and {gain4:.2f}u on disc 4; X {res['X']} (discs "
          f"differ by {res['X_disc_gap']}u there)")
    assert gain1 > 1.5 and gain4 > 1.5, res["gain"]
    assert s["d4_old"]["walk"]["progress"] == s["d4_old"]["walk_stock"]["progress"]   # OLD leaves disc 4 stock
    out = HERE / "out" / "r9_build.json"
    out.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print("->", out)


if __name__ == "__main__":
    main()
