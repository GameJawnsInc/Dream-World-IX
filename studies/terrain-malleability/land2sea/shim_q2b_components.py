"""Q2 detail: land components over the 2x2 Shimmering window (disc 1 vs disc 4) on an edge-avoiding 0.5u lattice
(offsets 0.37/0.61 so no sample sits on a 4u-lattice diagonal), what disc 4 has over the MAIN island (the disc-1
component carrying the event-1 entrance), the fate of every other islet, the new disc-4 Terrain tris that carry SEA
topographs, Sea4 multi-cover (double layers?), and an exact-point cross-check against r3_build.ground(None, ...).
Run: cd C:\\gd\\Dream-World-IX\\ff9mapkit ; py <this>   -> out/q2b_components.json
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np                                         # noqa: E402
import shim_lib as S                                       # noqa: E402
from scipy import ndimage                                  # noqa: E402

PITCH = 0.5
n = int(64 / PITCH)
px, pz = S.grid(PITCH, 0.37, 0.61)
SA = PITCH * PITCH
W = 2 * n
G = {d: {"part": np.empty((W, W), object), "ids": np.full((W, W), -1, np.int64), "y": np.full((W, W), np.nan),
         "tcov": np.zeros((W, W), np.int32), "s4cov": np.zeros((W, W), np.int32), "tymin": np.full((W, W), np.inf)}
     for d in (1, 4)}
for (bx, by) in S.SHIM:
    ox, oy = (bx - 6) * n, (by - 4) * n
    for d in (1, 4):
        part, ids, y, _o = S.ground_raster(d, bx, by, px, pz)
        G[d]["part"][ox:ox + n, oy:oy + n] = part.reshape(n, n)
        G[d]["ids"][ox:ox + n, oy:oy + n] = ids.reshape(n, n)
        G[d]["y"][ox:ox + n, oy:oy + n] = y.reshape(n, n)
        t = S.tri_arrays(S.read(bx, by, d, "terrain"))
        c, ymin, ymax, f = S.cover(t["V"], px, pz)
        G[d]["tcov"][ox:ox + n, oy:oy + n] = c.reshape(n, n)
        G[d]["tymin"][ox:ox + n, oy:oy + n] = ymin.reshape(n, n)
        s = S.tri_arrays(S.read(bx, by, d, "sea4"))
        c4, *_ = S.cover(s["V"], px, pz)
        G[d]["s4cov"][ox:ox + n, oy:oy + n] = c4.reshape(n, n)

res = {"pitch": PITCH}
for d in (1, 4):
    res[f"sea4_multicover_samples_d{d}"] = int((G[d]["s4cov"] > 1).sum())
    res[f"terrain_multicover_samples_d{d}"] = int((G[d]["tcov"] > 1).sum())
land = {d: np.isin(G[d]["part"], list(S.LAND_PARTS)) for d in (1, 4)}
lab1, n1 = ndimage.label(land[1], structure=np.ones((3, 3)))
ev1 = S.event_bits(np.where(G[1]["ids"] < 0, 0, G[1]["ids"]))
comps = []
for k in range(1, n1 + 1):
    m = lab1 == k
    ii, jj = np.nonzero(m)
    y1 = G[1]["y"][m]
    keep4 = land[4][m]
    p4 = Counter(G[4]["part"][m].tolist())
    t4 = S.topo(np.where(G[4]["ids"][m] < 0, 0, G[4]["ids"][m]))
    comps.append({"comp": k, "u2": float(m.sum() * SA),
                  "world_x": [round(64 * 6 + ii.min() * PITCH, 1), round(64 * 6 + (ii.max() + 1) * PITCH, 1)],
                  "world_z": [round(-64 * 4 - jj.max() * PITCH - PITCH, 1), round(-64 * 4 - jj.min() * PITCH, 1)],
                  "d1_ymax": round(float(np.nanmax(y1)), 2), "d1_event1_u2": float(((ev1 == 1) & m).sum() * SA),
                  "d4_still_land_u2": float(keep4.sum() * SA), "d4_ground_parts": dict(p4),
                  "d4_topo": dict(Counter(t4.tolist())),
                  "d4_terrain_cover_u2": float((G[4]["tcov"][m] > 0).sum() * SA),
                  "d4_ground_y_max": round(float(np.nanmax(G[4]["y"][m])), 2)})
comps.sort(key=lambda c: -c["u2"])
res["d1_land_components"] = comps
lab4, n4 = ndimage.label(land[4], structure=np.ones((3, 3)))
c4 = []
for k in range(1, n4 + 1):
    m = lab4 == k
    ov = Counter(lab1[m].tolist())
    t = S.topo(np.where(G[4]["ids"][m] < 0, 0, G[4]["ids"][m]))
    c4.append({"comp": k, "u2": float(m.sum() * SA), "d1_component_overlap": {str(a): float(b * SA) for a, b in ov.items()},
               "topo": dict(Counter(t.tolist())), "ymax": round(float(np.nanmax(G[4]["y"][m])), 2),
               "y_le_0.05_u2": float((m & (G[4]["y"] <= 0.05)).sum() * SA)})
c4.sort(key=lambda c: -c["u2"])
res["d4_land_components"] = c4

# disc-4 ground = Terrain with a SEA topograph: where / what was there on disc 1
t4 = S.topo(np.where(G[4]["ids"] < 0, 0, G[4]["ids"]))
seaT = land[4] & np.isin(t4, [53, 54, 55, 56, 57])
res["d4_terrain_with_sea_topo"] = {"u2": float(seaT.sum() * SA), "topo": dict(Counter(t4[seaT].tolist())),
                                   "y": S.rng(G[4]["y"][seaT]),
                                   "d1_part_there": dict(Counter(G[1]["part"][seaT].tolist())),
                                   "d1_topo_there": dict(Counter(S.topo(np.where(G[1]["ids"][seaT] < 0, 0, G[1]["ids"][seaT])).tolist()))}
# disc-4 terrain tris whose ids are sea topos: list them (world coords)
rows = []
for (bx, by) in S.SHIM:
    t = S.tri_arrays(S.read(bx, by, 4, "terrain"))
    tp = S.topo(t["ids"])
    for i in np.nonzero(np.isin(tp, [53, 54, 55, 56, 57]))[0]:
        V = t["V"][i]
        rows.append({"blk": [bx, by], "topo": int(tp[i]), "idall": int(t["ids"][i]),
                     "xz_world": [[round(64 * bx + p[0], 2), round(p[2] - 64 * by, 2)] for p in V],
                     "y": [round(float(p[1]), 3) for p in V], "uv": np.round(t["UV"][i], 4).tolist()})
res["d4_terrain_tris_sea_topo"] = rows

# cross-check: r3_build.ground(None, ns, x, z) at the EXACT raster sample points (every 4th sample per axis)
import r3_build as R3                                       # noqa: E402
agree = Counter()
bad = []
for i in range(0, W, 4):
    for j in range(0, W, 4):
        x = 64 * 6 + (i + 0.37) * PITCH
        z = -64 * 4 - (j + 0.61) * PITCH
        for d in (1, 4):
            r = R3.ground(None, d, x, z)
            mine_id = int(G[d]["ids"][i, j])
            ok = (r["part"] == G[d]["part"][i, j]) and (
                (r["topo"] is None and mine_id < 0) or (mine_id >= 0 and r["topo"] == S.topo(np.array([mine_id]))[0]
                                                         and abs(r["y"] - G[d]["y"][i, j]) < 1e-3))
            agree[(d, ok, r["src"])] += 1
            if not ok and len(bad) < 5:
                bad.append({"d": d, "x": x, "z": z, "r3": r, "mine": [G[d]["part"][i, j], mine_id, G[d]["y"][i, j]]})
res["r3_crosscheck"] = {str(k): v for k, v in agree.items()}
res["r3_crosscheck_bad_examples"] = bad
(S.OUT / "q2b_components.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
print(json.dumps({k: v for k, v in res.items() if k != "d4_terrain_tris_sea_topo"}, indent=1, default=str))
print("sea-topo terrain tris:", len(rows))
for r in rows:
    print(r)
