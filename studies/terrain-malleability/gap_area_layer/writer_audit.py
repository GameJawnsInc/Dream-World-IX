"""PER-WRITER AREA AUDIT -- what every ff9mapkit world writer does to the tile AREA bits, with code citations
(re-located by needle so the line numbers survive drift) and MEASURED consequences for the two writers whose area
choice is data-dependent: world-entrance's default `area := case` stamp and the donor-carrying writers.

Classes:  STAMP-CONST (writes a fixed area, usually 0) · STAMP-HOST (copies the host/local block's area) ·
          PRESERVE (keeps each tile's own area -- donor bytes ride along on a carry) · STRIP (drops donor area -> 0) ·
          USER (a CLI flag decides; default keeps) · STAMP-CASE (world-entrance: area := dispatch case & 0x3F)

Measured here:
  * world-entrance: for EVERY case it can stamp (the stock AREA-switch cases 2-60, the surgery case 53, and the
    virgin band 61-155 minus the reserved HUD cases), area = case & 0x3F (extract.encode_id masks) and that area's
    zone / camera place / area-12 lock / spawn weather / beach arm / encounter-record status for the typical
    entrance ground topographs {0, 16, 17, 41} (fog 0, stock disc-1 table)
  * the carry donors' stock areas: forest donor (15,15) canopy, mountain donors, Path-D Donor.txt prefabs

Rerun:  py studies/terrain-malleability/gap_area_layer/writer_audit.py  -> out/writer_audit.json
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import arealib as A                                  # noqa: E402
import numpy as np                                   # noqa: E402

KIT = Path(r"C:\gd\Dream-World-IX\ff9mapkit\ff9mapkit")

# (writer / verb, class, [(relpath, needle)], note)
WRITERS = [
    ("world-island (island.py)", "STAMP-CONST 0",
     [("world/island.py", "idw = float(encode_id(topograph=CLIFF_TOPO))"),
      ("world/island.py", "idg = float(encode_id(topograph=gspec[\"topo\"]))"),
      ("world/islandbeach.py", "id_sand = float(encode_id(topograph=SAND_TOPO[ground]))")],
     "every minted tri area 0 -> zone 0 (Alexandria/Mist start fauna), place 0, label 'area 0'"),
    ("world-reclaim / synthetic emitters (terrain.reclaim -> mesh.*_block_mesh)", "STAMP-CONST 0",
     [("world/mesh.py", "idall = float(encode_id(event=0, area=0, topograph=topograph))"),
      ("world/mesh.py", "idg, ids = float(encode_id(topograph=grass_topo)), float(encode_id(topograph=shore_topo))"),
      ("world/mesh.py", "idL, idC = float(encode_id(topograph=land_topo)), float(encode_id(topograph=cliff_topo))")],
     "flat/island/cliff cells: area 0"),
    ("building (blendio.build_from_obj)", "STAMP-CONST 0 (or caller idall)",
     [("world/blendio.py", "idall = float(encode_id(event=0, area=0, topograph=topograph) if idall is None")],
     "idall=4078 (0x0FEE) recommended on donor-backed cells -> decodes as area 15 but is walk-skip, never a ground hit"),
    ("world-entrance (entrance.author_entrance)", "STAMP-HOST (default) / PRESERVE / STAMP-CASE / USER",
     [("world/entrance.py", "area = (host[\"area\"] if tile_area == \"host\" else None if tile_area == \"keep\""),
      ("world/mesh.py", "def host_area(bm, *, center, radius: float, ring: float = HOST_RING"),
      ("cli.py", "wen.add_argument(\"--tile-area\", default=None, metavar=\"host|keep|case|N\",")],
     "the trigger tiles take the walkable ground's area within 3u (defect 14 FIXED, R2; was area := case & 0x3F); "
     "keep/case/N warn when they leave the host's area"),
    ("world-retarget (mesh.retarget_tiles / split_retarget_by_polygon)", "USER (default keep)",
     [("world/mesh.py", "d[\"area\"] if area is None else area,"),
      ("cli.py", "wr.add_argument(\"--area\", type=int, help=\"set the tile's IDALL area bits -- NOT the dispatch key")],
     "the --area help names the channels since the defect-14 fix; R3's refusal/consequence row is not built"),
    ("world-mountain (interior.carve_mountain)", "STRIP -> 0",
     [("world/interior.py", "def strip_dispatch(idall_f):"),
      ("world/interior.py", "# camera's place bucket via w_cameraArea2Place -- Uaho's baked area=63 is bucket 2 =")],
     "carried rock keeps topograph+flags, event/area -> 0; the ONLY writer that already names w_cameraArea2Place"),
    ("world-forest (interior.carve_forest)", "PRESERVE donor canopy",
     [("world/interior.py", "idall = float(dtan[tri[0]][0])"),
      ("world/interior.py", "GRASS_ID = float(X.encode_id(topograph=0))")],
     "canopy blob IDALL verbatim from FOREST_DONOR; the grass zip annulus area 0"),
    ("world-hill (interior.build_hill)", "PRESERVE host",
     [("world/interior.py", "def build_hill(soup, *, center=None, near=None, height: float = HILL_H,")],
     "lifts the island soup; no IDALL write found in the function"),
    ("world-transplant (transplant.py: rect carry + ground retile)", "PRESERVE (donor bytes) / retile keeps area",
     [("world/transplant.py", "return (float(encode_id(d[\"event\"], d[\"area\"], topo, d[\"flags\"])),) + tuple(tan[1:])")],
     "a carried block brings its donor's area (and event tiles) verbatim; the ground retile rewrites topograph only"),
    ("coast morph (coastmorph.py)", "STAMP-HOST (beach-less block) / PRESERVE exemplar",
     [("world/coastmorph.py", "s_id = (float(encode_id(event=0, area=ld[\"area\"], topograph=fam[\"topo\"],"),
      ("world/coastmorph.py", "f_id = (float(encode_id(event=0, area=ld[\"area\"],")],
     "new sand/foam takes the LOCAL block's area ('encounters/entrances stay this block's')"),
    ("coast nav / rim retile / orphan gate", "PRESERVE (topograph-only writers)",
     [("world/coastnav.py", "override. **Topograph bits only**"),
      ("world/orphangate.py", "nid = encode_id(d[\"event\"], d[\"area\"], dst_topo, d[\"flags\"])")], ""),
    ("disc mirror (discmirror.py)", "PRESERVE (byte copy disc1 -> disc4)",
     [("world/discmirror.py", "and a.uvs == b.uvs and a.tangents == b.tangents and a.normals == b.normals)")], ""),
    ("Path D Donor.txt cells (engine route, s34/s74)", "PRESERVE donor prefab (all un-overridden children ride along)",
     [], "measured in live_audit.py: Disc9 carries donor areas {0,6,7,40,48,50,57,58,62,63}"),
    ("R4b SAFE-ROAD stamp (study script, not a kit verb)", "STAMP-CONST 14 (event==0 and topo not in 36-38)",
     [], "studies/overworld-topography/southern-ring/REVERT.md s26.2; event tiles deliberately untouched"),
]


def locate(rel, needle):
    p = KIT / rel
    lines = p.read_text(encoding="utf-8", errors="replace").split("\n")
    hits = [i + 1 for i, ln in enumerate(lines) if needle in ln]
    return f"ff9mapkit/ff9mapkit/{rel}:{hits[0]}" if hits else f"ff9mapkit/ff9mapkit/{rel}:NOT-FOUND"


def main():
    A.OUT.mkdir(exist_ok=True)
    rows = []
    missing = 0
    for verb, cls, sites, note in WRITERS:
        cites = [locate(r, n) for r, n in sites]
        missing += sum("NOT-FOUND" in c for c in cites)
        rows.append({"writer": verb, "class": cls, "cites": cites, "note": note})
    # ---- world-entrance: every stampable case ----
    from ff9mapkit.world import entrance as EN
    us = {n: L["us"] for n, L in EN.load_all_dispatchers().items() if "us" in L}
    stock_cases = sorted(EN.dispatcher_cases(us["evt_world_world00"]) or [])
    cases = sorted(set(stock_cases) | {EN.NAMEPLATE_SURGERY_CASE} |
                   (set(range(61, EN.VIRGIN_CASE_MAX + 1)) - set(EN.RESERVED_VIRGIN_CASES)))
    recs, _src = A.record_set(1, live=False)
    ent = []
    for c in cases:
        ar = c & 0x3F
        q = A.consequence(ar)
        enc = {t: (q["zone"], t, 0) in recs for t in (0, 16, 17, 41)}
        ent.append({"case": c, "area": ar, **q, "encounter_record_topo": enc})
    agg = {"cases": len(ent),
           "area12_lock": [e["case"] for e in ent if e["area12_lock"]],
           "spawn_weather": [e["case"] for e in ent if e["spawn_weather"]],
           "camera_place_1": [e["case"] for e in ent if e["camera_place"] == 1],
           "camera_place_2": [e["case"] for e in ent if e["camera_place"] == 2],
           "beach_arm": [e["case"] for e in ent if e["beach_arm"]],
           "encounter_live_on_topo0": [e["case"] for e in ent if e["encounter_record_topo"][0]],
           "wrapped_case_ge_64": [e["case"] for e in ent if e["case"] >= 64]}
    # ---- carry donors' stock areas ----
    z = np.load(A.OUT / "stock_atlas.npz")
    a1, t1 = z["area_d1"], z["topo_d1"]

    def blk(bx, by, topo_filter=None):
        a = a1[bx * 64:(bx + 1) * 64, by * 64:(by + 1) * 64]
        t = t1[bx * 64:(bx + 1) * 64, by * 64:(by + 1) * 64]
        m = a >= 0
        if topo_filter is not None:
            m &= np.isin(t, topo_filter)
        return dict(Counter(a[m].ravel().tolist()).most_common(4))
    from ff9mapkit.world import interior as INT
    donors = {"forest FOREST_DONOR %s canopy topo 36-38" % (INT.FOREST_DONOR,): blk(*INT.FOREST_DONOR, (36, 37, 38)),
              "mountain MOUNTAIN_DONOR %s (Uaho)" % (INT.MOUNTAIN_DONOR,): blk(*INT.MOUNTAIN_DONOR),
              "crag (10,5)": blk(10, 5), "crag (10,6)": blk(10, 6),
              "horseshoe (5,15)": blk(5, 15), "comp20 (12,16)": blk(12, 16), "comp20 (12,17)": blk(12, 17),
              "Cleyra junction (13,11)": blk(13, 11), "Cleyra junction (14,12)": blk(14, 12)}
    res = {"writers": rows, "missing_cites": missing, "entrance_cases": ent, "entrance_summary": agg,
           "donor_areas_disc1": donors}
    (A.OUT / "writer_audit.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for r in rows:
        print(f"- {r['writer']}: {r['class']}  {r['cites']}")
    print("\nworld-entrance default stamp over", agg["cases"], "stampable cases:")
    for k, v in agg.items():
        if k != "cases":
            print(f"  {k}: {len(v)} -> {v[:40]}")
    print("\ncarry donors' stock areas (disc 1, 1u samples):")
    for k, v in donors.items():
        print("  ", k, v)
    if missing:
        print("CITE CHECK FAIL:", missing, "needles not found")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
