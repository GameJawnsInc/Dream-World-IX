"""CAPACITY lane, step 5 -- WHICH deployed override files does the engine actually READ? (a calibration of
the source model against in-game evidence; READ-ONLY on the install).

Source model (s34/s74 code, WMWorld.cs):
  * LoadBlock(disc, block) (WMWorld.cs:516-544): a land cell loads its OWN prefab; a sea cell (no 0_1
    terrain) loads ResolveReclaimDonor(...) iff a "Block[x][y] Terrain.ff9mesh" exists (Donor.txt -> that
    real block's prefab, else Block[12][10]), else the shared SeaBlockPrefab Block[12][0]f.
  * LoadBlock(prefab, block) (WMWorld.cs:582-810) calls RegisterBlockComponent ONLY for the prefab's
    existing child slots; RegisterBlockComponent (WMWorld.cs:812-858) TryLoads "<cell> <transform.name>".
  * RegisterBareObjectOverride (WMWorld.cs:868-884) additionally reads "<cell> Object" iff the prefab
    has TerrainForm1 and NO ObjectForm1.
=> a part file is READ iff its host prefab has a child of that NAME (or it is the bare-Object case).
   Everything else is a DEAD file the engine never opens.

Evidence: Memoria.log "[WorldMeshOverride] loaded ..." lines from the last disc-1 world entry.
Writes out/predict_reads.json.   Run:  py studies/terrain-malleability/capacity/predict_reads.py
"""
import json
import re
from collections import Counter
from pathlib import Path

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
ROOT = GAME / "FF9CustomMap-world" / "FF9_Data" / "WorldMap"
FPAT = re.compile(r"Block\[(\d+)\]\[(\d+)\] ([A-Za-z0-9_]+)\.ff9mesh$")
LPAT = re.compile(r"\[WorldMeshOverride\] loaded 'WorldMap/Disc(\d+)/0_1/r\d+/Block\[(\d+)\]\[(\d+)\] ([A-Za-z0-9_]+)'")


def main(disc=1):
    pc = json.loads((OUT / "prefab_children.json").read_text(encoding="utf-8"))[f"disc{disc}"]
    kids = {k: [n for n, _ in v] for k, v in pc.items()}
    land = {k for k, v in kids.items() if "Terrain" in v and not k.endswith("f")}
    files = {}
    donors = {}
    for p in (ROOT / f"Disc{disc}").rglob("*"):
        m = FPAT.search(p.name)
        if m:
            files[(int(m.group(1)), int(m.group(2)), m.group(3))] = p
        elif p.name.endswith("Donor.txt"):
            mm = re.search(r"Block\[(\d+)\]\[(\d+)\] Donor\.txt$", p.name)
            dx, dy = (int(s) for s in p.read_text().strip().split(",")[:2])
            donors[(int(mm.group(1)), int(mm.group(2)))] = (dx, dy)
    predicted, dead = set(), []
    for (x, y, part) in files:
        key = f"{x},{y}"
        if key in land:
            host = key
        elif (x, y, "Terrain") in files:
            d = donors.get((x, y))
            host = f"{d[0]},{d[1]}" if d else "12,10"
        else:
            host = "12,0f"
        ch = kids.get(host, [])
        read = part in ch or (part == "Object" and "Terrain" in ch and "Object" not in ch)
        (predicted.add((x, y, part)) if read else dead.append((x, y, part, host, ch)))
    logged = set()
    log = (GAME / "Memoria.log").read_text(encoding="utf-8", errors="replace")
    for m in LPAT.finditer(log):
        if int(m.group(1)) == disc:
            logged.add((int(m.group(2)), int(m.group(3)), m.group(4)))
    only_pred = sorted(predicted - logged)
    only_log = sorted(logged - predicted)
    res = {"files": len(files), "donor_sidecars": len(donors), "predicted_read": len(predicted),
           "logged_read": len(logged), "agree": len(predicted & logged),
           "predicted_not_logged": only_pred[:40], "logged_not_predicted": only_log[:40],
           "read_bytes": sum(files[k].stat().st_size for k in predicted),
           "read_vertices": sum(__import__("struct").unpack_from("<i", files[k].read_bytes()[:20], 8)[0] for k in predicted),
           "dead_bytes": sum(files[(d[0], d[1], d[2])].stat().st_size for d in dead),
           "dead_files": len(dead), "dead_by_part": dict(Counter(d[2] for d in dead)),
           "dead_sample": [list(d[:4]) for d in dead[:12]]}
    (OUT / "predict_reads.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for k, v in res.items():
        print(k, "=", v)


if __name__ == "__main__":
    main()
