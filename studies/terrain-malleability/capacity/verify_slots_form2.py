"""VERIFIER for CAP-5 / CAP-3 / CAP-6 (READ-ONLY; uses out/prefab_children.json + out/census_cache.json and the
deployed Donor.txt sidecars).

 (a) CAP-5 says "max parts per cell is bounded by the richest donor (e.g. (9,17): 7 form-1 slots)". Rank every
     disc-1/disc-4 block prefab by its FORM-1 child-slot count (all children minus the Form-2 slots).
 (b) The 15 own-prefab cells that have 0_1 meshes but NO Terrain child: predict_reads.py / live_budget.py
     classify "land" by `"Terrain" in children`, while the engine branches on WMBlock.IsSea. List them and
     whether any deployed file sits on them (the 254/254 calibration cannot have exercised them otherwise).
 (c) FORM-2 BAGGAGE: a reclaimed cell hosted by a SWITCHABLE donor registers that donor's Terrain2/Object2
     (form2-only, WMWorld.cs:597-600) -- inactive (its own WMBlock is IsSwitchable=false) but resident.
     Count the hosted cells per switchable donor and the dead Form-2 tris they carry. live_budget.py counts
     Form 1 only.

Writes out/verify_slots_form2.json.  Run:  py studies/terrain-malleability/capacity/verify_slots_form2.py
"""
import json
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
ROOT = GAME / "FF9CustomMap-world" / "FF9_Data" / "WorldMap"
FORM2 = {"Terrain2", "Object2", "Sea3_2", "Sea4_2", "Sea5_2", "VolcanoCrater2", "VolcanoLava2"}
SWITCHABLE = {(18, 14), (17, 12), (19, 10), (19, 11), (20, 10), (20, 11), (7, 1), (8, 1), (14, 15),
              (13, 16), (13, 17), (14, 16), (14, 17), (13, 12), (14, 12), (14, 6), (21, 10), (22, 14),
              (3, 9), (9, 1), (16, 1), (13, 4), (14, 5), (0, 0), (16, 14), (9, 17)}


def main():
    pc = json.loads((OUT / "prefab_children.json").read_text(encoding="utf-8"))
    rows = json.loads((OUT / "census_cache.json").read_text(encoding="utf-8"))["rows"]
    res = {}
    for disc in (1, 4):
        d = pc[f"disc{disc}"]
        f1 = {k: [n for n, _ in v if n not in FORM2] for k, v in d.items() if not k.endswith("f")}
        rank = sorted(f1.items(), key=lambda kv: -len(kv[1]))
        stock01 = {(r["x"], r["y"]) for r in rows if r["disc"] == disc and r["dir"] == "0_1" and r["part"] != "sea4f"}
        noterrain = sorted(f"{x},{y}" for (x, y) in stock01 if "Terrain" not in f1.get(f"{x},{y}", []))
        deployed_cells = Counter()
        donors = {}
        for p in (ROOT / f"Disc{disc}").rglob("*"):
            m = re.search(r"Block\[(\d+)\]\[(\d+)\] ([A-Za-z0-9_]+)\.(ff9mesh|txt)$", p.name)
            if not m:
                continue
            xy = f"{m.group(1)},{m.group(2)}"
            if m.group(3) == "Donor":
                donors[xy] = p.read_text().strip().replace(" ", "")
            else:
                deployed_cells[xy] += 1
        f2tris = {(r["x"], r["y"], r["part"]): r["tris"] for r in rows if r["disc"] == disc and r["dir"] == "0_2"}
        hosted = Counter(v for v in donors.values())
        baggage = {}
        for dk, n in hosted.items():
            dx, dy = (int(s) for s in dk.split(","))
            if (dx, dy) in SWITCHABLE:
                t = f2tris.get((dx, dy, "terrain"), 0) + f2tris.get((dx, dy, "object"), 0)
                baggage[dk] = {"hosted_cells": n, "form2_tris_per_cell": t, "dead_form2_tris_total": n * t}
        res[f"disc{disc}"] = {
            "richest_form1_slots": [(k, len(v), v) for k, v in rank[:4]],
            "slots_9_17": len(f1.get("9,17", [])),
            "own_prefab_cells_without_terrain": noterrain,
            "deployed_files_on_those_cells": {c: deployed_cells[c] for c in noterrain if deployed_cells[c]},
            "donor_sidecars": len(donors),
            "switchable_donor_form2_baggage": baggage,
        }
    OUT.mkdir(exist_ok=True)
    (OUT / "verify_slots_form2.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
