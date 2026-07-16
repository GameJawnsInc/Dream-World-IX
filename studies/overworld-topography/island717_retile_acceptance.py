"""THE (7,17)->DESERT RETILE -- offline acceptance.

Gates the GroundRetile tweak byte-for-byte before any deploy:

  1. positions/normals VERBATIM on every poly (the retile touches only uv + tangent.x)
  2. water topos + sea parts byte-identical (the tweak returns them untouched)
  3. mains/wall uvs = source uv + the exact GROUNDS delta (recomputed op, float-equal)
  4. sand: u + the SAND_BANDS du; classified v EXACTLY on the target pin; conforming
     v strictly inside the target tier; topo 31->32
  5. foam: uv identical, topo 30->34; event/area/flags preserved on every relabel
  6. recovered path tris: uvs inside the desert mains rect, topo -> 17
  7. the gate: ok, zero unclassified, counts == the prescan expectations

Run from the repo root:  py studies/overworld-topography/island717_retile_acceptance.py
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import transplant as TR                 # noqa: E402
from ff9mapkit.world import coastmorph as CM                 # noqa: E402
from ff9mapkit.world import grassland as G                   # noqa: E402
from ff9mapkit.world.extract import decode_id                # noqa: E402

DONOR = (7, 17)
gt = TR.GroundRetile.for_donor(DONOR, "desert")
print(f"retile {gt.src}->{gt.dst}: anchors {gt.sand_anchors}")
print(f"recover cells {sorted(gt.recover_cells)} budget {gt.recover_budget}")
print(f"expected {gt.expected}")

# regather exactly what transplant() feeds through apply()
(dbx, dby) = DONOR
extra = 8.0
polys = {p: [list(t) for t in TR.world_tris(dbx, dby, p)] for p in TR.PARTS}
strip_specs = {"E": ((dbx + 1, dby), 0, 64.0 * (dbx + 1) + extra, True),
               "W": ((dbx - 1, dby), 0, 64.0 * dbx - extra, False),
               "N": ((dbx, dby - 1), 2, -64.0 * dby + extra, True),
               "S": ((dbx, dby + 1), 2, -64.0 * (dby + 1) - extra, False)}
for ((nx2, ny2), axis, plane, below) in strip_specs.values():
    for p in TR.PARTS:
        for tri in TR.world_tris(nx2, ny2, p):
            cp = TR.clip_poly(list(tri), axis, plane, below)
            if len(cp) >= 3:
                polys[p].append(cp)

des = G.GROUNDS["desert"]
dsand = CM.SAND_BANDS["desert"]
dpins = {dsand["v_land"][0], dsand["v_seam"][0], dsand["v_cap_land"][0], dsand["v_cap_seam"][0]}
mrect = G.ground_main_region("desert")
n_checked = 0
fails = []


def ck(cond, msg):
    global n_checked
    n_checked += 1
    if not cond:
        fails.append(msg)


for p, pl in polys.items():
    for poly in pl:
        out = gt.apply(p, poly)
        topo_in = decode_id(int(round(poly[0][3][0])))["topograph"]
        topo_out = decode_id(int(round(out[0][3][0])))["topograph"]
        # 1. geometry verbatim
        ck(all(a[0] == b[0] and a[1] == b[1] for a, b in zip(poly, out)),
           f"{p} t{topo_in}: geometry changed")
        # per-vertex event/area/flags preserved
        for a, b in zip(poly, out):
            da, db = decode_id(int(round(a[3][0]))), decode_id(int(round(b[3][0])))
            ck((da["event"], da["area"], da["flags"]) == (db["event"], db["area"], db["flags"]),
               f"{p} t{topo_in}: event/area/flags changed")
            ck(tuple(a[3][1:]) == tuple(b[3][1:]), f"{p}: tangent tail changed")
        if p.startswith("sea") or topo_in in TR.GroundRetile._WATER:
            ck(out is poly, f"{p} t{topo_in}: water poly not returned untouched")
            continue
        if p == "beach1":
            ck(topo_in == 30 and topo_out == 34, f"beach1 topo {topo_in}->{topo_out}")
            ck(all(a[2] == b[2] for a, b in zip(poly, out)), "foam uv changed")
            continue
        if topo_in == 31:                                    # sand
            ck(topo_out == 32, f"sand topo -> {topo_out}")
            for a, b in zip(poly, out):
                ck(b[2][0] == a[2][0] + gt.sand_du, "sand u not du-translated")
                c = CM._sand_vclass(a[2][1], CM.SAND_BANDS["grass"])
                if c:
                    ck(round(b[2][1], 5) in {round(x, 5) for x in dpins},
                       f"classified sand v {a[2][1]:.5f}->{b[2][1]:.5f} off-pin")
                else:
                    ck(dsand["v_land"][0] <= b[2][1] <= dsand["v_cap_seam"][0],
                       f"conforming sand v {b[2][1]:.5f} outside the desert band")
            continue
        # wall or mains or recovered -- discriminate by the OUTPUT delta
        du0 = out[0][2][0] - poly[0][2][0]
        if abs(du0 - gt.wall_d[0]) < 1e-9 and topo_in == topo_out == 58:
            for a, b in zip(poly, out):
                ck(b[2] == (a[2][0] + gt.wall_d[0], a[2][1] + gt.wall_d[1]),
                   "wall uv not delta-translated")
            continue
        ck(topo_out == 17, f"land topo {topo_in} -> {topo_out} (want 17)")
        if abs(du0 - gt.mains_d[0]) < 1e-9 and \
                all(gt._in(a[2], gt.mains_rect) for a in poly):
            for a, b in zip(poly, out):
                ck(b[2] == (a[2][0] + gt.mains_d[0], a[2][1] + gt.mains_d[1]),
                   "mains uv not delta-translated")
        else:                                                # the recovered path/strip cells
            ck(topo_in in TR.GroundRetile.GRASS_TOPOS,
               f"unexpected recover source topo {topo_in}")
            for b in out:
                ck(mrect[0] - 1e-6 <= b[2][0] <= mrect[2] + 1e-6
                   and mrect[1] - 1e-6 <= b[2][1] <= mrect[3] + 1e-6,
                   f"recovered uv {b[2]} outside the desert mains rect {mrect}")

g = gt.gate()
print(f"gate: {g}")
ck(g["ok"], "gate not ok")
ck(g["unclassified"] == 0, f"unclassified content: {g['unclassified']}")

print(f"\n{n_checked} checks, {len(fails)} failures")
for f in fails[:12]:
    print("  FAIL:", f)
sys.exit(1 if fails else 0)
