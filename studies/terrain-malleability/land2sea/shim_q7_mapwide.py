"""Q7: every cell on disc 4 where LAND became SEA (and the reverse), map-wide, classified the Shimmering way.
Candidates = the disc4 study's census blocks with any non-identical 0_1 part, plus any cell whose IsSea prefab flag
differs between discs. Engine ground query (stock, registration order) on a 1u edge-avoiding lattice per block.
  land (d1) = ground part in Terrain/Object/Volcano* AND topo not in 53-57
  sea  (d4) = ground part Sea*/Beach* OR land part carrying a water topo 53-57 (sea painted into Terrain) OR MISS
Per block: land->sea u2 by disc-4 part/topo; under those samples, does ANY disc-4 Terrain/Object tri remain (plan
cover, any facing) and at what y (y<0 = SUNK under the sea; none = REMOVED-AND-FILLED); disc-1 height there;
entrance (event-bit) samples d1 vs d4. Writes out/q7_mapwide.json.
Run: cd C:\\gd\\Dream-World-IX\\ff9mapkit ; py <this>
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np                                         # noqa: E402
import shim_lib as S                                       # noqa: E402

WATER = [53, 54, 55, 56, 57]
census = json.loads((S.TM / "disc4" / "out" / "census.json").read_text(encoding="utf-8"))
cand = {(r["x"], r["y"]) for r in census if r["lod"] == "0_1" and r["cls"] not in ("IDENTICAL", "REORDERED")}
A = S.arealib()
E = A._engine()
seaflip = [(x, y) for x in range(24) for y in range(20) if E.is_sea(1, x, y) != E.is_sea(4, x, y)]
cand |= set(seaflip)
px, pz = S.grid(1.0, 0.37, 0.61)
rows = []
for (bx, by) in sorted(cand):
    g = {}
    for d in (1, 4):
        part, ids, y, order = S.ground_raster(d, bx, by, px, pz)
        tp = S.topo(np.where(ids < 0, 0, ids))
        ev = S.event_bits(np.where(ids < 0, 0, ids))
        isl = np.isin(part, list(S.LAND_PARTS))
        g[d] = dict(part=part, ids=ids, y=y, tp=tp, ev=ev, land=isl & ~np.isin(tp, WATER),
                    sea=(~isl) | (isl & np.isin(tp, WATER)))
    l2s = g[1]["land"] & g[4]["sea"]
    s2l = g[1]["sea"] & g[4]["land"]
    r = {"block": [bx, by], "land_to_sea_u2": int(l2s.sum()), "sea_to_land_u2": int(s2l.sum()),
         "d1_entrance_u2": int((g[1]["ev"] > 0).sum()), "d4_entrance_u2": int((g[4]["ev"] > 0).sum()),
         "d1_entrance_parts": S.hist(g[1]["part"][g[1]["ev"] > 0]), "d4_entrance_parts": S.hist(g[4]["part"][g[4]["ev"] > 0]),
         "d1_entrance_topo": S.hist(g[1]["tp"][g[1]["ev"] > 0]), "d4_entrance_topo": S.hist(g[4]["tp"][g[4]["ev"] > 0])}
    if l2s.any():
        r["d4_ground_part"] = S.hist(g[4]["part"][l2s])
        r["d4_ground_topo"] = S.hist(g[4]["tp"][l2s])
        r["d4_ground_y"] = S.rng(g[4]["y"][l2s])
        r["d1_ground_topo"] = S.hist(g[1]["tp"][l2s])
        r["d1_ground_y"] = S.rng(g[1]["y"][l2s])
        under = {}
        for p in ("terrain", "object"):
            bm = S.read(bx, by, 4, p)
            if bm is None:
                continue
            t = S.tri_arrays(bm)
            c, ymin, ymax, f = S.cover(t["V"], px, pz)
            sel = l2s & (c > 0)
            under[p] = {"covered_u2": int(sel.sum()), "ymin": S.rng(ymin[sel]), "ymax": S.rng(ymax[sel])}
        r["d4_land_mesh_under_lost"] = under
        sunk = sum(v["covered_u2"] for v in under.values())
        r["class"] = ("SUNK-UNDER-SEA" if sunk and all((v["ymax"] or [0, 0, 0])[2] < 0 for v in under.values() if v["covered_u2"])
                      else ("LAND-MESH-PAINTED-SEA" if sunk else "REMOVED-AND-FILLED"))
    if s2l.any():
        r["s2l_d1_part"] = S.hist(g[1]["part"][s2l])
        r["s2l_d4_topo"] = S.hist(g[4]["tp"][s2l])
        r["s2l_d4_y"] = S.rng(g[4]["y"][s2l])
    rows.append(r)

tot = Counter()
for r in rows:
    tot["land_to_sea_u2"] += r["land_to_sea_u2"]
    tot["sea_to_land_u2"] += r["sea_to_land_u2"]
    if r["land_to_sea_u2"]:
        tot[r["class"]] += r["land_to_sea_u2"]
res = {"candidates": len(cand), "isSea_prefab_flips": seaflip, "totals": dict(tot), "blocks": rows}
(S.OUT / "q7_mapwide.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
print("candidates", len(cand), "isSea flips", seaflip, dict(tot))
for r in rows:
    if r["land_to_sea_u2"] or r["d1_entrance_u2"] != r["d4_entrance_u2"] and r["block"] in ([21, 10],):
        print(r["block"], "L->S", r["land_to_sea_u2"], r.get("class"), "d4", r.get("d4_ground_part"), r.get("d4_ground_topo"),
              "y4", r.get("d4_ground_y"), "| d1 topo", r.get("d1_ground_topo"), "y1", r.get("d1_ground_y"),
              "| under", r.get("d4_land_mesh_under_lost"), "| S->L", r["sea_to_land_u2"],
              "| ent d1", r["d1_entrance_u2"], r["d1_entrance_parts"], r["d1_entrance_topo"], "d4", r["d4_entrance_u2"],
              r["d4_entrance_parts"], r["d4_entrance_topo"])
print("[21,10]:", [r for r in rows if r["block"] == [21, 10]])
