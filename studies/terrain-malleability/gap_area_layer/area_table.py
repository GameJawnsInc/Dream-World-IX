"""THE AREA CONSEQUENCE TABLE -- all 64 area values x every consumer, the input to the kit AREA POLICY (NOTES.md E).

Per area: zone (w_worldAreaZone), the WORLD .eb ENCRATE for that zone (the sysvar-207 ladder, read from the stock
WORLD00 dispatcher with world/encounter.freq_writes) and the battle frequency relative to zone 0 (ProcessEncount
accumulates, so frequency ~ sqrt(encratio) -- memory project-ff9-overworld-worlds), camera place, area-12 lock,
spawn weather, beach arm, the stock disc-1 encounter-record topographs of its zone, and -- for the topographs kit
ground actually carries (union of walkable topographs on live authored cells, out/live_audit.json) -- whether every
one of them is a TABLE HOLE (fog 0 and 1) under s60: a SAFE-ROAD candidate. Stock land area per area (out/stock_atlas.json)
tells how much stock geography already wears each label.

Rerun:  py studies/terrain-malleability/gap_area_layer/area_table.py   -> out/area_table.json
"""
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import arealib as A                                  # noqa: E402
from ff9mapkit.world import encounter as ENC         # noqa: E402
from ff9mapkit.world import entrance as EN           # noqa: E402


def main():
    t = A.tables()
    us = EN.load_all_dispatchers()["evt_world_world00"]["us"]
    ladder = {w["zone"]: w["value"] for w in ENC.freq_writes(us) if w["kind"] == "zone"}
    recs, _ = A.record_set(1, live=False)
    live = json.loads((A.OUT / "live_audit.json").read_text(encoding="utf-8"))
    kit_topos = set()
    for c in live["cells"]:
        for ar, p in c["raster"]["areas"].items():
            kit_topos |= {int(k) for k in p["walkable_topo_records"]}
    # the open-ground topographs the proven safe road (live Disc1 area 14, R4b) actually carries
    t14 = set()
    for c in live["cells"]:
        if c["ns"] == 1 and "14" in c["raster"]["areas"]:
            t14 |= {int(k) for k in c["raster"]["areas"]["14"]["walkable_topo_records"]}
    atlas = json.loads((A.OUT / "stock_atlas.json").read_text(encoding="utf-8"))
    rows = []
    for a in range(64):
        q = A.consequence(a)
        z = q["zone"]
        ztopos = sorted({tp for (zz, tp, f) in recs if zz == z})
        holes = [tp for tp in sorted(kit_topos) if (z, tp, 0) not in recs and (z, tp, 1) not in recs]
        enc = ladder.get(z)
        holes14 = [tp for tp in sorted(t14) if (z, tp, 0) not in recs and (z, tp, 1) not in recs]
        rows.append({**q, "encratio": enc,
                     "rel_freq_vs_zone0": round(math.sqrt(enc / ladder[0]), 3) if enc else None,
                     "zone_record_topos": ztopos, "kit_topos_that_are_holes": holes,
                     "safe_road_candidate": len(holes14) == len(t14) and not (q["area12_lock"] or q["spawn_weather"]),
                     "safe_road_topos_with_records": [tp for tp in sorted(t14) if tp not in holes14],
                     "stock_land_u2_d1": atlas["discs"]["1"]["areas"].get(str(a), {}).get("raster_land_u2", 0)})
    by_place = {p: [r["area"] for r in rows if r["camera_place"] == p and r["safe_road_candidate"]] for p in (0, 1, 2)}
    res = {"kit_ground_topos": sorted(kit_topos), "safe_road_topos_live_area14": sorted(t14), "encrate_ladder_world00": ladder, "rows": rows,
           "safe_road_candidates_by_place": by_place,
           "safe_road_candidates_no_beach_by_place": {p: [a for a in v if not rows[a]["beach_arm"]] for p, v in by_place.items()}}
    (A.OUT / "area_table.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("kit ground topographs:", sorted(kit_topos), " live area-14 safe-road topographs:", sorted(t14))
    print("ENCRATE ladder (zone: value):", ladder)
    for r in rows:
        print(f"area {r['area']:>2} zone {r['zone']:>2} enc {r['encratio']} x{r['rel_freq_vs_zone0']} place {r['camera_place']} "
              f"lock={int(r['area12_lock'])} wx={int(r['spawn_weather'])} beach={int(r['beach_arm'])} "
              f"zone-topos={r['zone_record_topos']} safe={int(r['safe_road_candidate'])} "
              f"road-topos-with-records={r['safe_road_topos_with_records']} stock_land={r['stock_land_u2_d1']}")
    print("safe-road candidates by place:", by_place)
    print("  ... excluding beach arms:", res["safe_road_candidates_no_beach_by_place"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
