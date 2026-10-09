"""Q4/Q6 extras: (a) what water ringed the MAIN island on disc 1 (0-6u and 6-16u bands) and what is there on disc 4;
(b) entrance tiles: event-1 (d1) vs event-2 (d4) polygons -- centroid, bbox, area, which tris (new vs kept);
(c) the idiom check: Terrain tris carrying water topographs (53-57) at y=0, map-wide, disc 1 vs disc 4;
(d) Alexandria Harbour (21,10) entrance tiles: event value / part / topo on each disc.
Run: cd C:\\gd\\Dream-World-IX\\ff9mapkit ; py <this>   -> out/q8_ring_idioms.json
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
G = {d: {"part": np.empty((W, W), object), "ids": np.full((W, W), -1, np.int64), "y": np.full((W, W), np.nan)}
     for d in (1, 4)}
for (bx, by) in S.SHIM:
    ox, oy = (bx - 6) * n, (by - 4) * n
    for d in (1, 4):
        part, ids, y, _o = S.ground_raster(d, bx, by, px, pz)
        G[d]["part"][ox:ox + n, oy:oy + n] = part.reshape(n, n)
        G[d]["ids"][ox:ox + n, oy:oy + n] = ids.reshape(n, n)
        G[d]["y"][ox:ox + n, oy:oy + n] = y.reshape(n, n)
res = {}
land1 = np.isin(G[1]["part"], list(S.LAND_PARTS))
lab, nl = ndimage.label(land1, structure=np.ones((3, 3)))
ev1 = S.event_bits(np.where(G[1]["ids"] < 0, 0, G[1]["ids"]))
main = lab == np.bincount(lab[ev1 == 1]).argmax()
dist = ndimage.distance_transform_edt(~main) * PITCH
for lo, hi in ((0, 6), (6, 16)):
    band = (dist > lo) & (dist <= hi) & ~land1
    for d in (1, 4):
        t = S.topo(np.where(G[d]["ids"][band] < 0, 0, G[d]["ids"][band]))
        res[f"ring_{lo}-{hi}u_d{d}"] = {"u2": float(band.sum() * SA), "part": S.hist(G[d]["part"][band]),
                                       "topo": S.hist(t)}
# (b) entrance polygons
for d in (1, 4):
    e = S.event_bits(np.where(G[d]["ids"] < 0, 0, G[d]["ids"]))
    m = e > 0
    ii, jj = np.nonzero(m)
    wx = 64 * 6 + (ii + 0.37) * PITCH
    wz = -64 * 4 - (jj + 0.61) * PITCH
    res[f"entrance_d{d}"] = {"u2": float(m.sum() * SA), "event": S.hist(e[m]),
                             "centroid": [round(float(wx.mean()), 2), round(float(wz.mean()), 2)],
                             "bbox_x": [round(float(wx.min()), 1), round(float(wx.max()), 1)],
                             "bbox_z": [round(float(wz.min()), 1), round(float(wz.max()), 1)],
                             "on_main_island_footprint_u2": float((m & main).sum() * SA),
                             "outside_main_footprint_u2": float((m & ~main).sum() * SA),
                             "part": S.hist(G[d]["part"][m])}
res["main_island"] = {"u2": float(main.sum() * SA), "d1_y_max": round(float(np.nanmax(G[1]["y"][main])), 2),
                      "d1_y_mean": round(float(np.nanmean(G[1]["y"][main])), 2),
                      "d4_ground_part": S.hist(G[4]["part"][main]),
                      "d4_y": S.rng(G[4]["y"][main])}
# event-2 tris: geometry (lattice? clean?) and the IDALL
ev_tris = Counter()
for (bx, by) in S.SHIM:
    t = S.tri_arrays(S.read(bx, by, 4, "sea4"))
    e = S.event_bits(t["ids"])
    for V, i, ee in zip(t["V"], t["ids"], e):
        if ee:
            onl = all(abs(p[0] / 4 - round(p[0] / 4)) < 1e-4 and abs(p[2] / 4 - round(p[2] / 4)) < 1e-4 for p in V)
            ev_tris[(int(i), S.decode_id_str(int(i)) if hasattr(S, "decode_id_str") else str(S.X.decode_id(int(i))),
                     "lattice" if onl else "offlattice")] += 1
res["event2_tris"] = {str(k): v for k, v in ev_tris.items()}
# (c) idiom: terrain tris with water topographs, map-wide
idiom = {}
for d in (1, 4):
    c = Counter()
    blocks = Counter()
    for bx in range(24):
        for by in range(20):
            bm = S.read(bx, by, d, "terrain")
            if bm is None:
                continue
            t = S.tri_arrays(bm)
            tp = S.topo(t["ids"])
            sel = np.isin(tp, [53, 54, 55, 56, 57])
            if sel.any():
                flat0 = np.all(np.abs(t["V"][sel][:, :, 1]) < 1e-6, axis=1)
                c["tris"] += int(sel.sum())
                c["flat_y0"] += int(flat0.sum())
                for tt in tp[sel]:
                    c[f"topo{tt}"] += 1
                blocks[(bx, by)] += int(sel.sum())
    idiom[f"d{d}"] = {"counts": dict(c), "blocks": {str(k): v for k, v in sorted(blocks.items())}}
res["terrain_with_water_topo_mapwide"] = idiom
# (d) Alexandria Harbour (21,10)
pxx, pzz = S.grid(1.0, 0.37, 0.61)
for d in (1, 4):
    part, ids, y, order = S.ground_raster(d, 21, 10, pxx, pzz)
    e = S.event_bits(np.where(ids < 0, 0, ids))
    m = e > 0
    res[f"alex_harbour_21_10_d{d}"] = {"u2": int(m.sum()), "event": S.hist(e[m]), "part": S.hist(part[m]),
                                      "idall": S.hist(ids[m]), "y": S.rng(y[m]), "order": order}
    if d == 1:
        alex_m = m
part4, ids4, y4, _ = S.ground_raster(4, 21, 10, pxx, pzz)
res["alex_harbour_21_10_d4_at_d1_tiles"] = {"part": S.hist(part4[alex_m]), "idall": S.hist(ids4[alex_m]),
                                            "y": S.rng(y4[alex_m])}
(S.OUT / "q8_ring_idioms.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
print(json.dumps(res, indent=1, default=str))
