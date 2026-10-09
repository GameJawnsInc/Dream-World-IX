"""Q2/Q3/Q4/Q6: the engine ground query (stock, both discs) + per-part plan coverage over the four Shimmering
blocks on a 0.5u lattice. Footprint F = samples whose disc-1 ground is a LAND part (Terrain/Object).
Reports: registration order; per-disc ground (part, topo, y) over F and over the whole 2x2; plan overlap of
Sea4 x Terrain on each disc with their y; what lies under F on disc 4 (any terrain tri at all?); land components;
event tiles; a cross-check against r3_build.ground(None, ns, x, z) on a 2u grid. Writes out/q23_ground.json and
out/q23_map.png (left disc 1, right disc 4).
Run: cd C:\\gd\\Dream-World-IX\\ff9mapkit ; py <this>
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np                                         # noqa: E402
import shim_lib as S                                       # noqa: E402

PITCH = 0.5
px, pz = S.grid(PITCH)
res = {"pitch": PITCH, "sample_area_u2": PITCH * PITCH, "blocks": {}}
SA = PITCH * PITCH
tot = Counter()
maps = {}
for (bx, by) in S.SHIM:
    rb = {}
    g = {}
    for d in (1, 4):
        part, ids, y, order = S.ground_raster(d, bx, by, px, pz)
        g[d] = (part, ids, y)
        rb[f"d{d}_registration_order"] = order
    land1 = np.isin(g[1][0], list(S.LAND_PARTS))
    land4 = np.isin(g[4][0], list(S.LAND_PARTS))
    rb["footprint_d1_land_u2"] = float(land1.sum() * SA)
    rb["d4_land_u2"] = float(land4.sum() * SA)
    rb["land_to_sea_u2"] = float((land1 & ~land4).sum() * SA)
    rb["sea_to_land_u2"] = float((~land1 & land4).sum() * SA)
    tot["F"] += land1.sum(); tot["L4"] += land4.sum(); tot["l2s"] += (land1 & ~land4).sum(); tot["s2l"] += (~land1 & land4).sum()

    def ghist(d, sel):
        part, ids, y = g[d]
        if not sel.any():
            return {}
        t = S.topo(np.where(ids < 0, 0, ids))
        e = S.event_bits(np.where(ids < 0, 0, ids))
        return {"part": S.hist(part[sel]), "topo": S.hist(t[sel]), "event": S.hist(e[sel]),
                "y[min,med,max]": S.rng(y[sel]), "y>0.01": int((y[sel] > 0.01).sum())}

    rb["ground_over_F_d1"] = ghist(1, land1)
    rb["ground_over_F_d4"] = ghist(4, land1)
    rb["ground_lost_d4"] = ghist(4, land1 & ~land4)
    rb["ground_lost_d1"] = ghist(1, land1 & ~land4)
    rb["ground_whole_d1"] = ghist(1, np.ones_like(land1))
    rb["ground_whole_d4"] = ghist(4, np.ones_like(land1))
    # per-part plan coverage (any tri, any facing) on each disc
    cov = {}
    for d in (1, 4):
        cd = {}
        for p in ("terrain", "sea1", "sea2", "sea3", "sea4", "sea5", "sea6", "beach1", "object"):
            bm = S.read(bx, by, d, p)
            if bm is None:
                continue
            t = S.tri_arrays(bm)
            c, ymin, ymax, first = S.cover(t["V"], px, pz)
            cd[p] = (c, ymin, ymax, first, t)
        cov[d] = cd
    pc = {}
    for d in (1, 4):
        pc[f"d{d}"] = {p: {"cover_u2": float((v[0] > 0).sum() * SA), "multi_cover_samples": int((v[0] > 1).sum()),
                           "cover_over_F_u2": float(((v[0] > 0) & land1).sum() * SA)}
                       for p, v in cov[d].items()}
    rb["part_coverage"] = pc
    # Sea4 x Terrain overlap on each disc
    ov = {}
    for d in (1, 4):
        if "sea4" in cov[d] and "terrain" in cov[d]:
            s4 = cov[d]["sea4"][0] > 0
            tr = cov[d]["terrain"][0] > 0
            both = s4 & tr
            ty = cov[d]["terrain"][2]
            ov[f"d{d}"] = {"sea4_u2": float(s4.sum() * SA), "terrain_u2": float(tr.sum() * SA),
                           "both_u2": float(both.sum() * SA),
                           "terrain_ymax_where_both[min,med,max]": S.rng(ty[both]),
                           "both_with_terrain_y>0.05_u2": float((both & (ty > 0.05)).sum() * SA),
                           "neither_u2": float((~s4 & ~tr).sum() * SA)}
        # other sea parts x terrain
        for p in ("sea1", "sea3", "sea5"):
            if p in cov[d] and "terrain" in cov[d]:
                sp = cov[d][p][0] > 0
                tr = cov[d]["terrain"][0] > 0
                ov.setdefault(f"d{d}", {})[f"{p}&terrain_u2"] = float((sp & tr).sum() * SA)
                ov[f"d{d}"][f"{p}&sea4_u2"] = float((sp & (cov[d]["sea4"][0] > 0)).sum() * SA)
    rb["overlap"] = ov
    # what lies under the lost footprint on disc 4, by part coverage (not just ground)
    lost = land1 & ~land4
    under = {}
    for p, v in cov[4].items():
        c = v[0] > 0
        under[p] = {"covers_lost_u2": float((c & lost).sum() * SA), "ymin_under_lost": S.rng(v[1][c & lost]),
                    "ymax_under_lost": S.rng(v[2][c & lost])}
    rb["d4_parts_under_lost_footprint"] = under
    # sunk-terrain test: any disc-4 terrain tri with any vert below 0?
    t4 = cov[4]["terrain"][4]
    rb["d4_terrain_verts_below0"] = int((t4["V"][:, :, 1] < -1e-6).sum())
    rb["d4_terrain_tris_over_lost"] = int(len(set(cov[4]["terrain"][3][lost & (cov[4]["terrain"][0] > 0)].tolist())))
    # event tiles (ground query) on each disc
    for d in (1, 4):
        part, ids, y = g[d]
        e = S.event_bits(np.where(ids < 0, 0, ids))
        sel = e > 0
        rb[f"event_tiles_d{d}"] = {"u2": float(sel.sum() * SA), "part": S.hist(part[sel]), "event": S.hist(e[sel]),
                                   "topo": S.hist(S.topo(ids[sel])), "y": S.rng(y[sel]),
                                   "over_F_u2": float((sel & land1).sum() * SA),
                                   "outside_F_u2": float((sel & ~land1).sum() * SA)}
    res["blocks"][f"{bx},{by}"] = rb
    maps[(bx, by)] = (g, land1, land4)

res["totals_u2"] = {k: float(v * SA) for k, v in tot.items()}

# --- cross-check against the study's r3_build.ground(None, ns, x, z) on a 2u grid (it reads the LIVE stack too)
import r3_build as R3                                       # noqa: E402
xc = Counter()
srcs = Counter()
for (bx, by) in S.SHIM:
    g, land1, land4 = maps[(bx, by)]
    for i in range(0, 32):
        for j in range(0, 32):
            lx, lz = 1.0 + 2 * i, -(1.0 + 2 * j)
            # nearest raster sample of the 0.5 grid: index
            ii, jj = int(lx / PITCH), int(-lz / PITCH)
            k = ii * int(64 / PITCH) + jj
            for d in (1, 4):
                r = R3.ground(None, d, 64 * bx + lx, lz - 64 * by)
                srcs[r["src"]] += 1
                mine = (g[d][0][k], int(S.topo(np.array([max(g[d][1][k], 0)]))[0]) if g[d][1][k] >= 0 else None)
                theirs = (r["part"], r["topo"])
                same = mine == theirs and (r["y"] is None or abs(r["y"] - g[d][2][k]) < 1e-3)
                xc[(d, same)] += 1
res["r3_crosscheck_2u"] = {"agree": {f"d{d}": xc[(d, True)] for d in (1, 4)},
                           "disagree": {f"d{d}": xc[(d, False)] for d in (1, 4)}, "r3_src": dict(srcs)}

(S.OUT / "q23_ground.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
print(json.dumps(res, indent=1, default=str))

# --- map png: part colours, 2x2 blocks per disc, 1px = 0.5u
try:
    from PIL import Image
    n = int(64 / PITCH)
    col = {"Terrain": (150, 120, 70), "Object": (120, 90, 60), "Sea1": (120, 200, 230), "Sea2": (90, 180, 220),
           "Sea3": (60, 140, 210), "Sea4": (20, 60, 150), "Sea5": (40, 110, 190), "Beach1": (240, 230, 160),
           "MISS": (255, 0, 255)}
    img = Image.new("RGB", (4 * n + 8, 2 * n), (0, 0, 0))
    pix = img.load()
    for (bx, by), (g, land1, land4) in maps.items():
        for di, d in enumerate((1, 4)):
            part, ids, y = g[d]
            ev = S.event_bits(np.where(ids < 0, 0, ids))
            ox = di * (2 * n + 8) + (bx - 6) * n
            oy = (by - 4) * n
            for k in range(part.size):
                i, j = divmod(k, n)
                c = col.get(part[k], (128, 128, 128))
                if part[k] in S.LAND_PARTS:
                    s = min(1.0, 0.4 + y[k] / 12.0)
                    c = tuple(int(v * s) for v in c)
                if ev[k]:
                    c = (255, 60, 60) if ev[k] == 1 else (255, 200, 0)
                pix[ox + i, oy + j] = c
    img = img.resize((img.width * 2, img.height * 2), Image.NEAREST)
    img.save(S.OUT / "q23_map.png")
    print("wrote", S.OUT / "q23_map.png")
except ImportError:
    pass
