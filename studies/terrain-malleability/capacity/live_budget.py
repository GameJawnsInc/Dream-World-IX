"""CAPACITY lane, step 8 -- THE LIVE GEOMETRY BUDGET: how many triangles the engine actually has resident
(Form 1) for the stock world vs the world as currently DEPLOYED (READ-ONLY on the install), and the
densest effective blocks. Uses the effective-prefab model calibrated 254/254 in predict_reads.py.

  stock:     every cell -> its own prefab (land) or SeaBlockPrefab Block[12][0]f (sea, Sea4f = 512 tris)
  deployed:  a sea cell with a "Terrain.ff9mesh" -> its Donor.txt prefab (else Block[12][10]); every
             Form-1 child whose "<cell> <child name>.ff9mesh" exists is replaced by that file's tri count
             (header icount/3); + the bare-Object case (RegisterBareObjectOverride).
Form-1 children = every prefab child except Terrain2/Object2/Sea*_2/VolcanoCrater2/VolcanoLava2.

Writes out/live_budget.json.  Run:  py studies/terrain-malleability/capacity/live_budget.py [disc]
"""
import json
import re
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
ROOT = GAME / "FF9CustomMap-world" / "FF9_Data" / "WorldMap"
FORM2 = {"Terrain2", "Object2", "Sea3_2", "Sea4_2", "Sea5_2", "VolcanoCrater2", "VolcanoLava2"}
MNAME = re.compile(r"Block\[(\d+)\]\[(\d+)\] ([A-Za-z0-9_]+)")


def main(disc=1):
    pc = json.loads((OUT / "prefab_children.json").read_text(encoding="utf-8"))[f"disc{disc}"]
    cen = json.loads((OUT / "census_cache.json").read_text(encoding="utf-8"))["rows"]
    stock = {(r["x"], r["y"], r["part"]): r["tris"] for r in cen if r["disc"] == disc and r["dir"] == "0_1"}

    def child_tris(host_key):
        out = []
        for name, mesh in pc.get(host_key, []):
            if name in FORM2 or mesh is None:
                continue
            m = MNAME.search(mesh)
            out.append((name, stock.get((int(m.group(1)), int(m.group(2)), m.group(3).lower()), 0)))
        return out

    land = {k for k, v in pc.items() if any(n == "Terrain" for n, _ in v) and not k.endswith("f")}
    files, donors = {}, {}
    for p in (ROOT / f"Disc{disc}").rglob("*"):
        m = re.search(r"Block\[(\d+)\]\[(\d+)\] ([A-Za-z0-9_]+)\.ff9mesh$", p.name)
        if m:
            ic = struct.unpack_from("<i", p.read_bytes()[:20], 12)[0]
            files[(int(m.group(1)), int(m.group(2)), m.group(3))] = ic // 3
        else:
            m = re.search(r"Block\[(\d+)\]\[(\d+)\] Donor\.txt$", p.name)
            if m:
                donors[(int(m.group(1)), int(m.group(2)))] = p.read_text().strip().replace(" ", "")
    tot_stock = tot_live = 0
    per_live, per_stock = {}, {}
    for y in range(20):
        for x in range(24):
            key = f"{x},{y}"
            host_s = key if key in land else "12,0f"
            s = sum(t for _, t in child_tris(host_s))
            if key in land:
                host_l = key
            elif (x, y, "Terrain") in files:
                host_l = donors.get((x, y), "12,10")
            else:
                host_l = "12,0f"
            kids = child_tris(host_l)
            names = {n for n, _ in kids}
            live = sum(files.get((x, y, n), t) for n, t in kids)
            if "Object" not in names and "Terrain" in names and (x, y, "Object") in files:
                live += files[(x, y, "Object")]                         # bare-Object override (render only)
            tot_stock += s
            tot_live += live
            per_live[key], per_stock[key] = live, s
    top = sorted(per_live.items(), key=lambda kv: -kv[1])[:10]
    biggest_part = max(((k, t) for k, t in files.items()), key=lambda kv: kv[1])
    res = {"disc": disc, "stock_form1_tris_resident": tot_stock, "deployed_form1_tris_resident": tot_live,
           "ratio": round(tot_live / tot_stock, 3),
           "stock_max_block": max(per_stock.values()), "deployed_max_block": top[0],
           "deployed_top10_blocks": top, "largest_deployed_part_file_tris": biggest_part,
           "headroom_vs_part_cap_21666": round(21666 / biggest_part[1], 1)}
    (OUT / f"live_budget_disc{disc}.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
