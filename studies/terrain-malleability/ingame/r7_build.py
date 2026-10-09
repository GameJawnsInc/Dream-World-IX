"""BUILD + REGISTERED PREDICTIONS for in-game round 7 (2026-10-09): buildings that change with the story (engine patch
s93 on top of s92; `world-forms --building2`). Writes ONLY into staging folders under ingame/out/r7_stage/ (gitignored),
through the scratch mod folder FF9CustomMap-lab (emptied around every build; not in FolderNames while this runs).

THE CELLS, both armed on ONE condition (flag 8712 = byte 1089 bit 0) on discs 1 and 4:
  A (6,12)  has a stock building (round 6's: a walkable Object over a hole in the ground). --building2 6 12 none
            removes it in form 2: a blank Object2, and a Terrain2 whose hole is filled from the ground around it.
  B (7,12)  has none. --building2 7 12 quay_beacon.obj --at 468 -796 makes the Southern Ring beacon appear in form 2
            (render only: the engine needs s93 to show an Object2 here at all; its footprint's ground is topograph 59).
  one world-terrain --form 2 hill across their shared border (x = 448), at (448, -778.6) r8 +2: the group edit.
THE FILES (all from the kit's CLI, as a user would run them):
  FULL  everything above, both discs (each --building2 replays itself on disc 4: the cells are armed there)
  KEEP  FULL, then --building2 6 12 keep (A's Object2 deleted on both discs: A keeps its building in form 2)
THE STAGES (lab files, flag, disc -> what each cell shows):
  stock     -     off  1   stock everywhere
  off       FULL  off  1   form 1: A's building, B bare, no hill (the files are there and read, nothing switches)
  on        FULL  on   1   form 2: A's building GONE (ground under it), B's beacon, the hill on both sides of x = 448
  keep      KEEP  on   1   form 2 with A's building back (s92 carries it), B's beacon, the hill
  on_disc4  FULL  on   4   form 2 on disc 4's own ground (scenario 11101)
Read points: A's footprint per disc (R1/R2 on the building's roof, ~5u over the fill that replaces it; W on its walkable
plaza), the hill (0.63u either side of the border), ctl. The beacon: a 9u walk south into its footprint (form 1:
reached; form 2: blocked at its north face, z ~ -793.5).
Writes out/r7_build.json.
Run:  py studies/terrain-malleability/ingame/r7_build.py
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
import forms_build as FB                             # noqa: E402  (ground_at: the within-mesh rule)

STAGE = HERE / "out" / "r7_stage"
KIT = RB.KIT
LAB = "FF9CustomMap-lab"
A_CELL, B_CELL = (6, 12), (7, 12)
FLAG_COND = "(GetEventGlobalByte(1089) & 1) != 0"
BEACON = RB.REPO / "studies" / "overworld-topography" / "southern-ring" / "quay_beacon.obj"
BEACON_AT = (468.0, -796.0)
HILL = {"at": (448.0, -778.6), "radius": 8.0, "raise": 2.0}
HILL_PTS = {"H_w": (447.37, -778.63), "H_e": (448.63, -778.63)}
CTL = (431.37, -823.61)
WALK = {"start": (468.37, -787.37), "bearing": 270.0, "distance": 9.0, "north_face": -793.5}
SINK = 1.171875
STAGES = {   # name: (files, flag, disc)
    "stock": (None, False, 1),
    "off": ("FULL", False, 1),
    "on": ("FULL", True, 1),
    "keep": ("KEEP", True, 1),
    "on_disc4": ("FULL", True, 4),
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def kit(argv) -> subprocess.CompletedProcess:
    p = subprocess.run([sys.executable, "-m", "ff9mapkit"] + argv, cwd=str(KIT), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert p.returncode == 0, (argv, p.stdout[-2000:], p.stderr[-2000:])
    return p


def snapshot(dst: Path) -> dict:
    """Copy the lab's override files (no ledger, no .bak parks) to ``dst``; {relpath: sha}."""
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


def a_points(disc: int, files: Path) -> dict:
    """A's read points, off the 4u lattice, where its stock building answers: R1/R2 on the building's ROOF (topograph
    59, ~5u above the ground that replaces it: in form 1 the roof, in form 2 the fill), W on its walkable plaza (the
    largest building-vs-fill difference there; on disc 4 none, so W reads the same in both forms)."""
    from ff9mapkit.world.placement import WALK_OK
    from ff9mapkit.world.formobject import footprint_points as fp
    from ff9mapkit.world.transplant import world_tris
    rows = []
    for p in fp(world_tris(*A_CELL, "object", disc=disc), A_CELL):
        if min(abs(p[0] / 4.0 - round(p[0] / 4.0)), abs(p[1] / 4.0 - round(p[1] / 4.0))) * 4.0 <= 0.3:
            continue
        g = RB.ground(None, disc, *p)
        if g["part"] != "Object":
            continue
        f = form2_ground(files, disc, A_CELL, p)
        rows.append((g["y"] - f["y"], (round(p[0], 2), round(p[1], 2)), g["topo"]))
    roof = sorted(r for r in rows if r[2] not in WALK_OK)
    r1 = roof[-1]
    r2 = max((r for r in roof if math.dist(r[1], r1[1]) >= 1.0), key=lambda r: r[0])
    w = max((r for r in rows if r[2] in WALK_OK), key=lambda r: abs(r[0]))
    return {"R1": r1[1], "R2": r2[1], "W": w[1]}


def form2_ground(files: Path, disc: int, cell, p) -> dict:
    """The form-2 ground at world ``p`` on a switched custom cell: its Terrain2 (the Object2 there renders only, or is
    the blank) -- the canopy sink subtracted on topographs 36-38."""
    from ff9mapkit.world import mesh as M
    rel = f"FF9_Data/WorldMap/Disc{disc}/0_1/r{cell[1]}/Block[{cell[0]}][{cell[1]}] Terrain2.ff9mesh"
    bm = M.blockmesh_from_ff9mesh(files / rel, disc=disc, x=cell[0], y=cell[1], lod="0_1", part="Terrain2")
    FB.ORIGIN = (cell[0] * 64.0, -cell[1] * 64.0)
    y, idall = FB.ground_at(bm, *p)
    assert y is not None, (rel, p)
    topo = (idall & 0xFC) >> 2
    return {"y": round(y - (SINK if topo in (36, 37, 38) else 0.0), 4), "topo": topo}


def stock_ground(disc: int, p) -> dict:
    g = RB.ground(None, disc, *p)
    assert g["y"] is not None, (disc, p)
    return {"y": round(g["y"] - (SINK if g["topo"] in (36, 37, 38) else 0.0), 4), "topo": g["topo"], "part": g["part"]}


def cell_of(p):
    return (int(math.floor(p[0] / 64.0)), int(math.floor(-p[1] / 64.0)))


def main():
    import ff9mapkit
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    shutil.rmtree(STAGE, ignore_errors=True)
    files = STAGE / "files"
    res = {"cells": {"A": A_CELL, "B": B_CELL}, "condition": FLAG_COND, "hill": HILL, "beacon_at": BEACON_AT,
           "walk": WALK, "files": {}, "receipts": {}, "stages": {}, "points": {}, "predict": {}}

    # FULL: arm both cells on both discs, then the kit's own --building2 and --form 2 verbs
    RB._clear_lab()
    for d in (1, 4):
        for c in (A_CELL, B_CELL):
            kit(["world-forms", "--mod-folder", LAB, "--arm", str(c[0]), str(c[1]), "--when", FLAG_COND,
                 "--disc", str(d)])
    res["receipts"]["remove_A"] = kit(["world-forms", "--mod-folder", LAB, "--building2", "6", "12", "none"]).stdout
    res["receipts"]["beacon_B"] = kit(["world-forms", "--mod-folder", LAB, "--building2", "7", "12", str(BEACON),
                                       "--at", str(BEACON_AT[0]), str(BEACON_AT[1])]).stdout
    res["receipts"]["hill"] = kit(["world-terrain", "--mod-folder", LAB, "--form", "2", "--at", str(HILL["at"][0]),
                                   str(HILL["at"][1]), "--radius", str(HILL["radius"]), "--raise",
                                   str(HILL["raise"])]).stdout[-3000:]
    assert "REMOVED in form 2" in res["receipts"]["remove_A"] and "(Disc4)" in res["receipts"]["remove_A"]
    assert "APPEARS in form 2" in res["receipts"]["beacon_B"] and "(Disc4)" in res["receipts"]["beacon_B"]
    assert "REPLAYING the edit on disc 4" in res["receipts"]["hill"], res["receipts"]["hill"]
    res["files"]["FULL"] = snapshot(files / "FULL")
    # KEEP: the kit's own undo of A's removal
    res["receipts"]["keep_A"] = kit(["world-forms", "--mod-folder", LAB, "--building2", "6", "12", "keep"]).stdout
    res["files"]["KEEP"] = snapshot(files / "KEEP")
    RB._clear_lab()
    gone = sorted(set(res["files"]["FULL"]) - set(res["files"]["KEEP"]))
    assert gone == ["FF9_Data/WorldMap/Disc1/0_1/r12/Block[6][12] Object2.ff9mesh",
                    "FF9_Data/WorldMap/Disc4/0_1/r12/Block[6][12] Object2.ff9mesh"], gone
    assert all(res["files"]["FULL"][k] == v for k, v in res["files"]["KEEP"].items())

    # PREDICTIONS
    for d in (1, 4):
        apts = a_points(d, files / "FULL")
        pts = {**apts, **HILL_PTS, "ctl": CTL}
        res["points"][d] = pts
        stock = {k: stock_ground(d, p) for k, p in pts.items()}
        for k in apts:
            assert stock[k]["part"] == "Object", (d, k, stock[k])
        on = {}
        for k, p in pts.items():
            c = cell_of(p)
            on[k] = form2_ground(files / "FULL", d, c, p)["y"] if c in (A_CELL, B_CELL) else stock[k]["y"]
        keep = dict(on)
        for k in apts:
            keep[k] = stock[k]["y"]                           # the stock building answers first again (carried)
        res["predict"][d] = {"stock": {k: v["y"] for k, v in stock.items()}, "on": on, "keep": keep,
                             "stock_detail": stock}
        for k in HILL_PTS:
            assert on[k] - stock[k]["y"] > 0.5, (d, k, on[k], stock[k])
        for k in ("R1", "R2"):
            assert stock[k]["y"] - on[k] > 3.0, ("the roof must stand well above the fill", d, k)
        assert abs(on["H_w"] - on["H_e"]) < 0.3, ("the hill tears at the border", d, on)
        assert on["ctl"] == stock["ctl"]["y"]
    for name, (fset, flag, disc) in STAGES.items():
        src = {"stock": "stock", "off": "stock", "on": "on", "keep": "keep", "on_disc4": "on"}[name]
        res["stages"][name] = {"files": fset, "flag": flag, "disc": disc, "ground": src,
                               "beacon": name in ("on", "keep", "on_disc4"),
                               "a_removed": name in ("on", "on_disc4"),
                               "armed": fset is not None, "switched": flag and fset is not None}
        pred = res["predict"][disc][src]
        print(f"{name:9s} {fset or '-':5s} flag {int(flag)} disc {disc} -> {src:5s} "
              + " ".join(f"{k} {v}" for k, v in pred.items()))
    out = HERE / "out" / "r7_build.json"
    out.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print("->", out)


if __name__ == "__main__":
    main()
