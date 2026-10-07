"""STOCK AREA GEOGRAPHY -- the tile AREA layer of both discs, from the 0_1 form-1 walk meshes (exact containers),
as the engine's sky ground query sees it (arealib.raster, calibrated 5376/5376 vs placement.place).

Per disc (1, 4): a 1u raster (1536 x 1280 samples, offsets 0.37/0.61 off the 4u lattice) of the first-hit IDALL
under the engine's registration order (IsSea cells -> SeaBlockPrefab sea4f), plus tri-level histograms over EVERY
0_1 mesh (all parts, referenced or not). Produces:
  * per area: raster plan area (land parts Object/Terrain/Volcano* vs water parts), tri counts, connected components
    (4-connectivity, TOROIDAL wrap merge across x=0/1536 and z=0/1280), largest component, blocks touched,
    topograph mix, and its engine consequences (zone, camera place, beach arm, spawn weather, area-12 lock)
  * boundaries: every 4-neighbour sample pair whose area differs -- what fraction lies on a 64u BLOCK border
    (null model: 1/64 = 1.56% of all pairs straddle a border), and what fraction is also a topograph change
  * areas per block; areas UNUSED by stock (never on any 0_1 tri of either disc) and what they would get
  * out/stock_atlas.npz (label rasters) + out/stock_atlas.json + out/area_atlas.png

Rerun:  py studies/terrain-malleability/gap_area_layer/stock_atlas.py   (after calibrate.py PASSes)
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import arealib as A                                  # noqa: E402
import numpy as np                                   # noqa: E402
from scipy import ndimage                            # noqa: E402

W, H = 24 * 64, 20 * 64
WATER = {"Beach1", "Beach2", "Stream", "River", "RiverJoint", "Falls", "Sea1", "Sea2", "Sea3", "Sea4", "Sea5", "Sea6"}


def build_disc(d):
    area = np.full((W, H), -1, np.int16)
    topo = np.full((W, H), -1, np.int16)
    event = np.full((W, H), -1, np.int8)
    land = np.zeros((W, H), bool)
    yy = np.zeros((W, H), np.float32)
    part_names = Counter()
    for bx in range(24):
        for by in range(20):
            walk = A.stock_walk_list(d, bx, by)
            meshes = [(n, *A.stock_mesh(k)) for n, k in walk]
            ids, pi, ys = A.raster(meshes, 1.0)
            n = 64
            ids2 = ids.reshape(n, n)
            pi2 = pi.reshape(n, n)
            hit = ids2 >= 0
            sl = (slice(bx * 64, bx * 64 + 64), slice(by * 64, by * 64 + 64))
            a = np.where(hit, (ids2 & 0x3F00) >> 8, -1)
            t = np.where(hit, (ids2 & 0xFC) >> 2, -1)
            e = np.where(hit, (ids2 & 0xC000) >> 14, -1)
            area[sl], topo[sl], event[sl] = a, t, e
            yy[sl] = ys.reshape(n, n)
            names = np.array([w[0] for w in walk] + ["MISS"])
            pn = names[np.where(pi2 >= 0, pi2, len(walk))]
            land[sl] = np.isin(pn, list(A.LAND_PARTS))
            for k, v in Counter(pn.ravel().tolist()).items():
                part_names[k] += v
    return area, topo, event, land, yy, part_names


def tri_census(d):
    """{area: {part: tris}} over every 0_1 mesh of disc d (exact containers), + up-plan area by area."""
    objs = A._objs()
    by = defaultdict(Counter)
    plan = Counter()
    for (dd, lod, x, y, part) in objs:
        if dd != d or lod != "0_1":
            continue
        V, ids = A.stock_mesh(f"d{dd}/{lod}/{x},{y}/{part}")
        for ar, (n, nup, pl) in A.tri_hist(V, ids).items():
            by[ar][part] += n
            plan[ar] += pl
    return by, plan


def components(mask):
    lab, n = ndimage.label(mask)
    if n == 0:
        return lab, []
    parent = list(range(n + 1))

    def f(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for a_, b_ in ((lab[0, :], lab[-1, :]), (lab[:, 0], lab[:, -1])):   # toroidal wrap
        for p, q in zip(a_, b_):
            if p and q:
                rp, rq = f(p), f(q)
                if rp != rq:
                    parent[rp] = rq
    roots = np.array([f(i) for i in range(n + 1)])
    lab = roots[lab]
    sizes = Counter(lab[lab > 0].ravel().tolist())
    return lab, sorted(sizes.items(), key=lambda kv: -kv[1])


def boundaries(area, topo):
    out = {}
    for ax, nm in ((0, "x"), (1, "z")):
        nb_a = np.roll(area, -1, axis=ax)
        nb_t = np.roll(topo, -1, axis=ax)
        both = (area >= 0) & (nb_a >= 0)
        diff = both & (area != nb_a)
        idx = np.arange(area.shape[ax])
        border_line = ((idx + 1) % 64 == 0)
        border = border_line[:, None] if ax == 0 else border_line[None, :]
        border = np.broadcast_to(border, area.shape)
        out[nm] = {"pairs": int(both.sum()), "area_diff": int(diff.sum()),
                   "area_diff_on_block_border": int((diff & border).sum()),
                   "area_diff_with_topo_diff": int((diff & (topo != nb_t)).sum()),
                   "topo_diff": int((both & (topo != nb_t)).sum()),
                   "topo_diff_with_area_diff": int((both & (topo != nb_t) & diff).sum())}
    tot = {k: out["x"][k] + out["z"][k] for k in out["x"]}
    tot["frac_area_boundary_on_block_border"] = tot["area_diff_on_block_border"] / max(1, tot["area_diff"])
    tot["null_model_frac"] = 1 / 64
    tot["frac_area_boundary_also_topo_boundary"] = tot["area_diff_with_topo_diff"] / max(1, tot["area_diff"])
    tot["frac_topo_boundary_also_area_boundary"] = tot["topo_diff_with_area_diff"] / max(1, tot["topo_diff"])
    return {"by_axis": out, "total": tot}


def main():
    A.OUT.mkdir(exist_ok=True)
    res = {"discs": {}}
    rasters = {}
    ys_all = {}
    used_any = set()
    for d in (1, 4):
        area, topo, event, land, yy, pn = build_disc(d)
        rasters[d] = (area, topo, event, land)
        ys_all[d] = yy
        tri_by, tri_plan = tri_census(d)
        used_any |= set(tri_by)
        per = {}
        for ar in sorted(set(np.unique(area[area >= 0]).tolist()) | set(tri_by)):
            m = area == ar
            lab, comps = components(m)
            ml = m & land
            labl, compsl = components(ml)
            cols, rows = np.nonzero(m)
            blocks = sorted({(int(c) // 64, int(r) // 64) for c, r in zip(cols, rows)})
            tmix = Counter(topo[m].ravel().tolist())
            big = []
            for root, size in compsl[:12]:
                cc, rr = np.nonzero(labl == root)
                big.append({"u2": int(size), "centroid_block": [round(float(cc.mean()) / 64, 2), round(float(rr.mean()) / 64, 2)],
                            "block_bbox": [int(cc.min()) // 64, int(cc.max()) // 64, int(rr.min()) // 64, int(rr.max()) // 64]})
            per[ar] = {**A.consequence(ar),
                       "raster_u2": int(m.sum()), "raster_land_u2": int(ml.sum()), "raster_water_u2": int((m & ~land).sum()),
                       "tris_by_part": dict(tri_by.get(ar, {})), "tri_up_plan_u2": round(tri_plan.get(ar, 0.0), 1),
                       "components_all": len(comps), "components_land": len(compsl),
                       "largest_land_component_u2": int(compsl[0][1]) if compsl else 0,
                       "blocks_touched": len(blocks), "topo_mix_top": tmix.most_common(6), "land_components": big}
        per_block = Counter()
        for bx in range(24):
            for by_ in range(20):
                blk = area[bx * 64:(bx + 1) * 64, by_ * 64:(by_ + 1) * 64]
                blkl = land[bx * 64:(bx + 1) * 64, by_ * 64:(by_ + 1) * 64]
                vals = set(np.unique(blk[blkl]).tolist()) if blkl.any() else set()
                per_block[len(vals)] += 1
        res["discs"][d] = {"part_samples": dict(pn), "miss_samples": int((area < 0).sum()),
                           "areas": per, "boundaries": boundaries(area, topo),
                           "land_areas_per_block_hist": dict(sorted(per_block.items()))}
    unused = sorted(set(range(64)) - used_any)
    res["unused_areas_both_discs"] = [A.consequence(a) for a in unused]
    res["used_areas_any_disc"] = sorted(used_any)
    np.savez_compressed(A.OUT / "stock_atlas.npz",
                        **{f"{k}_d{d}": v for d, (a, t, e, l) in rasters.items()
                           for k, v in (("area", a), ("topo", t), ("event", e), ("land", l))},
                        **{f"y_d{d}": v for d, v in ys_all.items()})
    (A.OUT / "stock_atlas.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    render(rasters, res)
    # ---- print a digest ----
    for d in (1, 4):
        r = res["discs"][d]
        b = r["boundaries"]["total"]
        print(f"\nDISC {d}: miss={r['miss_samples']}  land-areas-per-block hist={r['land_areas_per_block_hist']}")
        print(f"  area boundary pairs={b['area_diff']}  on block border={b['frac_area_boundary_on_block_border']:.3f} "
              f"(null {b['null_model_frac']:.4f})  also topo change={b['frac_area_boundary_also_topo_boundary']:.3f}  "
              f"topo-boundaries that are area boundaries={b['frac_topo_boundary_also_area_boundary']:.3f}")
        for ar, p in r["areas"].items():
            print(f"  area {ar:>2} z{p['zone']:>2} pl{p['camera_place']} land {p['raster_land_u2']:>7} water {p['raster_water_u2']:>7} "
                  f"comps(land) {p['components_land']:>3} largest {p['largest_land_component_u2']:>7} blocks {p['blocks_touched']:>3} "
                  f"topo {p['topo_mix_top'][:3]}")
    print("\nunused areas (no 0_1 tri on either disc):", unused)
    return 0


def render(rasters, res):
    from PIL import Image, ImageDraw, ImageFont
    SEA, LAND0, P1, P2, LOCK = (238, 241, 244), (201, 200, 194), (235, 104, 52), (42, 120, 214), (74, 58, 167)
    INK, GRID = (82, 81, 78), (170, 169, 164)
    panels = []
    font = ImageFont.load_default()
    for d in (1, 4):
        area, topo, event, land = rasters[d]
        place = np.array(A.tables()["w_cameraArea2Place"])
        img = np.zeros((H, W, 3), np.uint8)
        img[:] = SEA
        a = area.T
        l = land.T
        pl = np.where(a >= 0, place[np.clip(a, 0, 63)], -1)
        img[l & (pl == 0)] = LAND0
        img[l & (pl == 1)] = P1
        img[l & (pl == 2)] = P2
        img[l & (a == 12)] = LOCK
        # water tiles whose area is non-zero: tint lightly by place
        img[~l & (a >= 0) & (pl == 1)] = (247, 205, 186)
        img[~l & (a >= 0) & (pl == 2)] = (183, 211, 246)
        bd = np.zeros_like(l)
        bd[:-1, :] |= (a[:-1, :] != a[1:, :]) & (l[:-1, :] | l[1:, :])
        bd[:, :-1] |= (a[:, :-1] != a[:, 1:]) & (l[:, :-1] | l[:, 1:])
        img[bd] = INK
        img[::64, :] = np.where(bd[::64, :, None], img[::64, :], GRID)
        img[:, ::64] = np.where(bd[:, ::64, None], img[:, ::64], GRID)
        im = Image.fromarray(img)
        dr = ImageDraw.Draw(im)
        for ar, p in res["discs"][d]["areas"].items():
            for c in p["land_components"]:
                if c["u2"] < 600:
                    continue
                cx, cy = c["centroid_block"][0] * 64, c["centroid_block"][1] * 64
                s = str(ar)
                for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    dr.text((cx + ox - 6, cy + oy - 5), s, fill=(255, 255, 255), font=font)
                dr.text((cx - 6, cy - 5), s, fill=(11, 11, 11), font=font)
        dr.text((8, 8), f"Disc {d} -- tile AREA at the sky ground query (1u)", fill=(11, 11, 11), font=font)
        panels.append(im)
    leg_h = 70
    out = Image.new("RGB", (W, 2 * H + 3 * 10 + leg_h), (252, 252, 251))
    out.paste(panels[0], (0, 0))
    out.paste(panels[1], (0, H + 10))
    dr = ImageDraw.Draw(out)
    y0 = 2 * H + 25
    items = [(LAND0, "land, camera place 0 (areas 0-26, 46-50)"), (P1, "land, camera place 1 (areas 40-45)"),
             (P2, "land, camera place 2 (areas 27-39, 51-63)"), (LOCK, "area 12: camera lock (<4990) + spawn weather"),
             (SEA, "water parts (light tint = place 1/2)"), (INK, "area boundary; grey grid = 64u blocks; numbers = area id")]
    x = 10
    for col, txt in items:
        dr.rectangle([x, y0, x + 14, y0 + 14], fill=col, outline=INK)
        dr.text((x + 20, y0 + 2), txt, fill=(11, 11, 11), font=font)
        x += 20 + 7 * len(txt) + 24
    out.save(A.OUT / "area_atlas.png")


if __name__ == "__main__":
    sys.exit(main())
