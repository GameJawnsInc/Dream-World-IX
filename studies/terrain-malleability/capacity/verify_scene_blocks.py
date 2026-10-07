"""VERIFIER for CAP-2/CAP-3/CAP-5 (READ-ONLY on the install): the RUNTIME WMBlock flags serialized in the world
scene (x64/FF9_Data/level7 and level19 hold the 480 WMBlock MonoBehaviours, no typetree), decoded by layout.

The engine branches on WMBlock.IsSea (LoadBlock, WMWorld.cs:521) and gates SetForm on WMBlock.IsSwitchable
(WMBlock.cs:99) -- the SCENE flags, not the prefab children the lane's scripts used as a proxy. This reads them.

Layout (found empirically, then cross-checked): the 480 block MonoBehaviours are each 160 bytes; int32 words
22/23 = InitialX/InitialY, 24 = Number (= y*24+x), 25/26 = CurrentX/CurrentY; words 10/11/12 are the first three
bools (IsSea, HasSpecialObject, IsSwitchable in WMBlock.cs:243-245 declaration order, 4-byte aligned).
Calibration (asserted): Number == InitialY*24+InitialX for all 480, (InitialX,InitialY) covers the 24x20 grid
exactly once.

Checks: IsSwitchable set == the 26 blocks of ff9.cs w_worldChangeBlockSet; IsSea set == the 205 cells with no
0_1 mesh (i.e. the 15 terrain-less own-prefab open-water cells are IsSea=FALSE -> they take the own-prefab
branch and can never be reclaimed by the s34 sea divert).

Writes out/verify_scene_blocks.json.  Run:  py studies/terrain-malleability/capacity/verify_scene_blocks.py
"""
import json
import struct
from pathlib import Path

import UnityPy

G = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
OUT = Path(__file__).resolve().parent / "out"
SWITCHABLE = {(18, 14), (17, 12), (19, 10), (19, 11), (20, 10), (20, 11), (7, 1), (8, 1), (14, 15),
              (13, 16), (13, 17), (14, 16), (14, 17), (13, 12), (14, 12), (14, 6), (21, 10), (22, 14),
              (3, 9), (9, 1), (16, 1), (13, 4), (14, 5), (0, 0), (16, 14), (9, 17)}


def main():
    cen = json.loads((OUT / "census_cache.json").read_text(encoding="utf-8"))["rows"]
    has01 = {(r["x"], r["y"]) for r in cen if r["disc"] == 1 and r["dir"] == "0_1" and r["part"] != "sea4f"}
    has_terrain = {(r["x"], r["y"]) for r in cen if r["disc"] == 1 and r["dir"] == "0_1" and r["part"] == "terrain"}
    res = {}
    for lv in ("level7", "level19"):
        env = UnityPy.load(str(G / "x64" / "FF9_Data" / lv))
        blocks = [o.get_raw_data() for o in env.objects if o.type.name == "MonoBehaviour"]
        blocks = [b for b in blocks if len(b) == 160]
        w = lambda b, i: struct.unpack_from("<i", b, 4 * i)[0]
        cells = {}
        for b in blocks:
            x, y, num = w(b, 22), w(b, 23), w(b, 24)
            assert num == y * 24 + x, f"layout calibration failed: Number {num} != {y}*24+{x}"
            cells[(x, y)] = {"IsSea": w(b, 10), "HasSpecialObject": w(b, 11), "IsSwitchable": w(b, 12)}
        assert len(cells) == 480 and set(cells) == {(x, y) for x in range(24) for y in range(20)}, "grid coverage"
        sea = {c for c, f in cells.items() if f["IsSea"]}
        sw = {c for c, f in cells.items() if f["IsSwitchable"]}
        open_water_own = sorted(has01 - has_terrain)
        res[lv] = {
            "n_blocks": len(cells), "IsSea_count": len(sea), "IsSwitchable_count": len(sw),
            "IsSwitchable_equals_w_worldChangeBlockSet_26": sw == SWITCHABLE,
            "IsSea_equals_cells_without_0_1_mesh": sea == ({(x, y) for x in range(24) for y in range(20)} - has01),
            "terrainless_own_prefab_cells": [f"{x},{y}" for x, y in open_water_own],
            "their_IsSea_flags": sorted({cells[c]["IsSea"] for c in open_water_own}),
        }
    OUT.mkdir(exist_ok=True)
    (OUT / "verify_scene_blocks.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
