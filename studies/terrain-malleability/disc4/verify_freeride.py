"""VERIFIER (adversarial) -- D4-19 "no clobbers in the live state". mirror_risk.py checks each deployed
(cell, part) file against the REAL part at that same cell. It does not look at Donor.txt sidecars: a sidecar
cell loads its DONOR's prefab, so every donor part the cell does NOT override free-rides in from the donor --
and on disc 4 that is the DISC-4 donor prefab. If a free-riding donor part differs across discs and is not
pinned on Disc4, the mirrored cell renders differently on disc 4. Read-only on the install.
Run: py C:/gd/Dream-World-IX/studies/terrain-malleability/disc4/verify_freeride.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit import config                         # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
rows = json.loads((OUT / "census.json").read_text(encoding="utf-8"))
cls = {(r["x"], r["y"], r["part"]): r["cls"] for r in rows if r["lod"] == "0_1"}
gp = Path(config.find_game_path(None)) / "FF9CustomMap-world" / "FF9_Data" / "WorldMap"
BR = re.compile(r"^Block\[(\d+)\]\[(\d+)\] (.+?)\.(ff9mesh|txt)$")
files = {1: {}, 4: {}}
for d in (1, 4):
    for p in (gp / f"Disc{d}" / "0_1").rglob("Block[[]*"):
        m = BR.match(p.name)
        if m:
            files[d].setdefault((int(m.group(1)), int(m.group(2))), {})[m.group(3).lower()] = p
issues, checked = [], 0
for cell, parts in sorted(files[1].items()):
    if "donor" not in parts:
        continue
    dx, dy = (int(v) for v in parts["donor"].read_text().strip().split(","))
    donor_parts = sorted(p for (x, y, p) in cls if (x, y) == (dx, dy))
    for p in donor_parts:
        checked += 1
        if p in parts:                     # overridden at the cell on disc 1
            continue
        c = cls[(dx, dy, p)]
        pinned = p in files[4].get(cell, {})
        if c != "IDENTICAL":
            issues.append({"cell": cell, "donor": (dx, dy), "free_ride_part": p, "donor_part_class": c,
                           "pinned_on_disc4": pinned})
print(f"sidecar cells checked; donor part slots examined: {checked}")
print(f"free-riding donor parts that are NOT identical across discs: {len(issues)}")
for i in issues:
    print("   ", i)
(OUT / "verify_freeride.json").write_text(json.dumps(issues, indent=1, default=str), encoding="utf-8")
