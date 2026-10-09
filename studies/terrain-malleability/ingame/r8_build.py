"""BUILD + REGISTERED PREDICTIONS for in-game round 8 (2026-10-09): entrances that change with the story
(`world-forms --entrance2`, on engine s92; no DLL change). Writes ONLY into staging folders under ingame/out/r8_stage/
(gitignored), through the scratch mod folder FF9CustomMap-lab (emptied around every build; not in FolderNames while
this runs).

THE CELL: (18,12), not one of the 26 switchable cells. It holds the Ice Cavern's walk-on entrance: two event tiles,
cell tag (37,24) event 1, dispatch case 4 -> field 300 (Ice Cavern/Entrance) with no story condition, a case every
free-roam world script carries (world 9011, where the FARSHORE route lands, included). Disc 4's (18,12) has no such
tile, so this round is disc 1 only.
THE FILES (the kit's CLI, as a user would run it): the cell armed on flag 8712, then
  OFF   --entrance2 18 12 off    Terrain2 = the form-1 ground with the two tiles' event bits cleared
  ONLY  --entrance2 18 12 only   Terrain = the form-1 ground without them (a form-1-only override), Terrain2 with them
THE STAGES (lab, flag -> does a 9u walk south across the tile enter field 300?):
  stock   -     off -> ENTERS (the control: the stock entrance fires on this route)
  off_f0  OFF   off -> ENTERS (form 1 keeps it)
  off_f1  OFF   on  -> STAYS on the world map, standing on the tile (form 2 closed it)
  only_f0 ONLY  off -> STAYS (form 1 has no entrance)
  only_f1 ONLY  on  -> ENTERS (it opened with the story)
The walk: from (1197.37, -789.63) south 9u; the tile spans z -794.99..-798.48 at x 1196..1200 (rock and topograph 59
beyond it stop a walk that does not enter).
Writes out/r8_build.json.
Run:  py studies/terrain-malleability/ingame/r8_build.py
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r3_build as RB                                # noqa: E402  (the sky ground query, the lab)

STAGE = HERE / "out" / "r8_stage"
KIT = RB.KIT
LAB = "FF9CustomMap-lab"
CELL = (18, 12)
FLAG_COND = "(GetEventGlobalByte(1089) & 1) != 0"
FIELD = 300
WALK = {"start": (1197.37, -789.63), "bearing": 270.0, "distance": 9.0, "onto_tile_z": -795.5}
STAGES = {   # name: (files, flag, enters)
    "stock": (None, False, True),
    "off_f0": ("OFF", False, True),
    "off_f1": ("OFF", True, False),
    "only_f0": ("ONLY", False, False),
    "only_f1": ("ONLY", True, True),
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def kit(argv) -> str:
    p = subprocess.run([sys.executable, "-m", "ff9mapkit"] + argv, cwd=str(KIT), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert p.returncode == 0, (argv, p.stdout[-2000:], p.stderr[-2000:])
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


def tags_in(files: Path, part: str):
    from ff9mapkit.world import mesh as M
    rel = f"FF9_Data/WorldMap/Disc1/0_1/r{CELL[1]}/Block[{CELL[0]}][{CELL[1]}] {part}.ff9mesh"
    if not (files / rel).is_file():
        return None
    return sorted(M.entrance_tags(M.blockmesh_from_ff9mesh(files / rel, disc=1, x=CELL[0], y=CELL[1], part=part)))


def main():
    import ff9mapkit
    from ff9mapkit.world import extract as X, formentrance as FE, mesh as M
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    shutil.rmtree(STAGE, ignore_errors=True)
    files = STAGE / "files"
    res = {"cell": CELL, "condition": FLAG_COND, "field": FIELD, "walk": WALK, "files": {}, "receipts": {},
           "tags": {}, "stages": {}}
    stock = X.read_block(*CELL, disc=1)
    tiles = FE.event_tris(stock)
    res["stock_tags"] = sorted(M.entrance_tags(stock))
    assert res["stock_tags"] == [(37, 24, 1)] and len(tiles) == 2, res["stock_tags"]
    # the walk lane crosses the tile: every point of x = 1197.37 between z -795.2 and -798.3 lies on it
    ox, oz = X.block_world_origin(*CELL)
    for z in (-795.2, -796.5, -798.3):
        p = (WALK["start"][0] - ox, z - oz)
        assert any(FE._inside(stock, t, p) for t, _ev in tiles), z
    for name, mode in (("OFF", "off"), ("ONLY", "only")):
        RB._clear_lab()
        kit(["world-forms", "--mod-folder", LAB, "--arm", str(CELL[0]), str(CELL[1]), "--when", FLAG_COND])
        res["receipts"][name] = kit(["world-forms", "--mod-folder", LAB, "--entrance2", str(CELL[0]), str(CELL[1]),
                                     mode])
        res["files"][name] = snapshot(files / name)
        res["tags"][name] = {"Terrain": tags_in(files / name, "Terrain"), "Terrain2": tags_in(files / name, "Terrain2")}
    RB._clear_lab()
    assert res["tags"]["OFF"] == {"Terrain": None, "Terrain2": []}, res["tags"]
    assert res["tags"]["ONLY"] == {"Terrain": [], "Terrain2": [(37, 24, 1)]}, res["tags"]
    for name, (fset, flag, enters) in STAGES.items():
        res["stages"][name] = {"files": fset, "flag": flag, "enters": enters, "armed": fset is not None,
                               "switched": flag and fset is not None, "terrain_from_lab": fset == "ONLY"}
        print(f"{name:8s} {fset or '-':5s} flag {int(flag)} -> {'ENTERS field 300' if enters else 'stays on the map'}")
    out = HERE / "out" / "r8_build.json"
    out.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print("->", out)


if __name__ == "__main__":
    main()
