"""LIVE AREA AUDIT -- the tile AREA layer of every live overworld override cell, and what the engine does with it.

READ-ONLY on the install: lists and parses <game>/<FolderNames>/FF9_Data/WorldMap/Disc{1,4,9}/0_1 files; nothing is
written outside this lane's out/ dir.

For every cell with a loose override (namespaces 1, 4, 9):
  * the bind decision through the consumption lane's calibrated bind-oracle Engine (81/81 receipts on disc 1): the
    effective prefab, which form-1 walk slots bind an override and which ride along as stock free riders
  * per BOUND override file: the per-area triangle histogram (1-tri blanks are reported, never counted as content)
    and the areas of its EVENT tiles
  * the engine's SKY ground query at 1u over the whole cell (arealib.raster, calibrated 5376/5376) -> the area
    histogram of what a player/vehicle actually stands on, split land / water / walkable
  * per area present: encounter zone, and for every walkable topograph present the (zone, topo, fog 0/1) record
    status against the LIVE discmr table (a HOLE = no battle under s60), camera place, the area-12 lock, spawn
    weather (9/12/13), the beach arm, and the location label (printed only; names are not written to the repo)
  * for disc 1/4 cells: the delta vs the STOCK area layer of the same cell (out/stock_atlas.npz)
Mosaic checks per namespace (live cells over the stock/BLANK background): walkable<->walkable CAMERA-PLACE seams
(stock has ZERO on both discs, camera_place_effect.py) and walkable area-12 / weather area.

Rerun:  py studies/terrain-malleability/gap_area_layer/live_audit.py   -> out/live_audit.json
        (needs out/stock_atlas.npz from stock_atlas.py)
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import arealib as A                                  # noqa: E402
import numpy as np                                   # noqa: E402
from ff9mapkit.world import placement as P           # noqa: E402

WALK_OK = np.array(sorted(P.WALK_OK))
RECORD_DISC = {1: 1, 4: 4, 9: 1}     # Path D (ns 9) runs with w_frameDisc 1 (s74 sentinel namespace, currentDisc stays 1)


def audit_cell(ns, x, y, files, stock_area):
    pk, why, walk = A.live_walk_list(ns, x, y, files)
    out = {"ns": ns, "cell": [x, y], "effective_prefab": pk, "why": why,
           "walk": [[n, Path(s).name if k == "override" else s, k] for n, s, k in walk], "files": {}}
    meshes = []
    for name, src, kind in walk:
        V, ids = A.read_ff9mesh_arrays(src) if kind == "override" else A.stock_mesh(src)
        meshes.append((name, V, ids))
        if kind == "override":
            if len(ids) <= 1:
                out["files"][name] = {"blank": True, "tris": int(len(ids))}
                continue
            ev = ids[((ids & 0xC000) >> 14) > 0]
            out["files"][name] = {"tris": int(len(ids)), "area_hist": A.tri_hist(V, ids),
                                  "event_tris_by_idall": {int(k): int(v) for k, v in Counter(ev.tolist()).items()}}
    ids, pi, ys = A.raster(meshes, 1.0)
    hit = ids >= 0
    names = [m[0] for m in meshes]
    land = np.array([(names[p] in A.LAND_PARTS) if p >= 0 else False for p in pi])
    area = np.where(hit, (ids & 0x3F00) >> 8, -1)
    topo = np.where(hit, (ids & 0xFC) >> 2, -1)
    event = np.where(hit, (ids & 0xC000) >> 14, -1)
    walkable = hit & np.isin(topo, WALK_OK)
    recs, src = A.record_set(RECORD_DISC[ns], live=True)
    per = {}
    for ar in sorted(set(area[hit].tolist())):
        m = area == ar
        c = A.consequence(ar)
        tw = Counter(topo[m & walkable].tolist())
        rec = {}
        for tp, n in sorted(tw.items()):
            st = ["record" if (c["zone"], tp, fog) in recs else "HOLE" for fog in (0, 1)]
            rec[tp] = {"u2": n, "fog0": st[0], "fog1": st[1]}
        per[ar] = {**c, "u2": int(m.sum()), "land_u2": int((m & land).sum()), "walkable_u2": int((m & walkable).sum()),
                   "event_u2": int((m & (event > 0)).sum()), "walkable_topo_records": rec,
                   "encounter_live_u2": int(sum(v["u2"] for v in rec.values() if v["fog0"] == "record"))}
    out["raster"] = {"samples": int(ids.size), "miss": int((~hit).sum()), "areas": per}
    if stock_area is not None:
        st = stock_area[x * 64:(x + 1) * 64, y * 64:(y + 1) * 64].ravel()       # [i(x), j(row)] order == raster order
        lv = area
        out["delta_vs_stock"] = {"changed_samples": int((st != lv).sum()),
                                 "stock_hist": dict(Counter(st.tolist()).most_common()),
                                 "transitions": [[int(a), int(b), int(n)] for (a, b), n in
                                                 Counter(zip(st[st != lv].tolist(), lv[st != lv].tolist())).most_common(12)]}
    return out, area.reshape(64, 64), topo.reshape(64, 64), walkable.reshape(64, 64), land.reshape(64, 64)


def mosaic_checks(ns, cell_rasters, base):
    """Assemble the namespace mosaic (live cells over the stock (1/4) or BLANK-sea (9) background); count walkable
    camera-place seams and the pairs that involve at least one live cell."""
    W, H = 24 * 64, 20 * 64
    if base is not None:
        area, topo, land = base["area"].copy(), base["topo"].copy(), base["land"].copy()
        walk = land & (area >= 0) & np.isin(topo, WALK_OK)
    else:
        area = np.zeros((W, H), np.int16)            # BLANK Path-D grid: sea4f, area 0 topo 57 (not walkable)
        walk = np.zeros((W, H), bool)
    live = np.zeros((W, H), bool)
    for (x, y), (a, t, wk, ld) in cell_rasters.items():
        sl = (slice(x * 64, x * 64 + 64), slice(y * 64, y * 64 + 64))
        area[sl] = a
        walk[sl] = wk & ld
        live[sl] = True
    place_lut = np.array(A.tables()["w_cameraArea2Place"])
    pl = np.where(area >= 0, place_lut[np.clip(area, 0, 63)], -1)
    seams, ex = 0, []
    zseams = 0
    zone_lut = np.array(A.tables()["w_worldAreaZone"])
    zn = np.where(area >= 0, zone_lut[np.clip(area, 0, 63)], -1)
    for ax in (0, 1):
        nb = np.roll(pl, -1, axis=ax)
        nw = np.roll(walk, -1, axis=ax)
        nl = np.roll(live, -1, axis=ax)
        na = np.roll(area, -1, axis=ax)
        nz = np.roll(zn, -1, axis=ax)
        both = walk & nw & (live | nl)
        d = both & (pl != nb)
        seams += int(d.sum())
        zseams += int((both & (zn != nz)).sum())
        cc, rr = np.nonzero(d)
        for c, r in list(zip(cc, rr))[:200]:
            ex.append((int(c) // 64, int(r) // 64, int(area[c, r]), int(na[c, r])))
    exc = Counter(ex)
    return {"walkable_place_seam_pairs": seams, "walkable_zone_seam_pairs": zseams,
            "place_seam_cells_areas": [[*k, v] for k, v in exc.most_common(20)],
            "walkable_area12_u2_live": int((walk & live & (area == 12)).sum()),
            "walkable_weather_u2_live": int((walk & live & np.isin(area, (9, 12, 13))).sum())}


def main():
    A.OUT.mkdir(exist_ok=True)
    z = np.load(A.OUT / "stock_atlas.npz")
    stock = {d: {"area": z[f"area_d{d}"], "topo": z[f"topo_d{d}"], "land": z[f"land_d{d}"]} for d in (1, 4)}
    cells = A.live_cells()
    res = {"cells": [], "record_sources": {}, "mosaic": {}}
    rasters = defaultdict(dict)
    for (ns, x, y), files in sorted(cells.items()):
        if ns not in (1, 4, 9):
            continue
        r, a, t, wk, ld = audit_cell(ns, x, y, files, stock[ns]["area"] if ns in stock else None)
        res["cells"].append(r)
        rasters[ns][(x, y)] = (a, t, wk, ld)
    for ns in (1, 4, 9):
        res["record_sources"][ns] = A.record_set(RECORD_DISC[ns], live=True)[1]
        if rasters.get(ns):
            res["mosaic"][ns] = mosaic_checks(ns, rasters[ns], stock.get(ns))
    # ---- global summaries ----
    summ = {}
    for ns in (1, 4, 9):
        cs = [c for c in res["cells"] if c["ns"] == ns]
        agg = defaultdict(lambda: Counter())
        file_area = Counter()
        file_event_area = Counter()
        for c in cs:
            for ar, p in c["raster"]["areas"].items():
                agg[ar]["u2"] += p["u2"]
                agg[ar]["walkable_u2"] += p["walkable_u2"]
                agg[ar]["encounter_live_u2"] += p["encounter_live_u2"]
                agg[ar]["cells"] += 1
            for part, f in c["files"].items():
                if f.get("blank"):
                    continue
                for ar, (n, nup, pl) in f["area_hist"].items():
                    file_area[(part, ar)] += n
                for idall, n in f["event_tris_by_idall"].items():
                    file_event_area[(part, (idall & 0x3F00) >> 8, (idall & 0xFC) >> 2, (idall & 0xC000) >> 14)] += n
        summ[ns] = {"cells": len(cs), "areas": {ar: dict(v) for ar, v in sorted(agg.items())},
                    "bound_file_tris_by_part_area": [[p, a, n] for (p, a), n in sorted(file_area.items())],
                    "bound_event_tris": [[p, a, t, e, n] for (p, a, t, e), n in sorted(file_event_area.items())]}
    res["summary"] = summ
    (A.OUT / "live_audit.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    names = A.location_names()
    for ns in (1, 4, 9):
        s = summ[ns]
        print(f"\n===== namespace Disc{ns}: {s['cells']} live cells; record table: {res['record_sources'][ns]}")
        print("  bound EVENT tris (part, area, topo, event, n):", s["bound_event_tris"])
        print("  bound file tris by (part, area):", s["bound_file_tris_by_part_area"])
        print("  ground-query area totals:")
        for ar, v in s["areas"].items():
            c = A.consequence(ar)
            print(f"    area {ar:>2} [{names.get(ar, '?')[:22]:<22}] zone {c['zone']:>2} place {c['camera_place']} "
                  f"lock={c['area12_lock']!s:<5} weather={c['spawn_weather']!s:<5} beach={c['beach_arm']!s:<5} "
                  f"u2={v['u2']:>7} walkable={v['walkable_u2']:>7} enc-live={v['encounter_live_u2']:>7} cells={v['cells']}")
        if ns in res["mosaic"]:
            print("  MOSAIC:", json.dumps(res["mosaic"][ns]))
    print("\n===== per-cell rows (cells whose walkable ground carries >1 area, or a lock/weather/place-1/2 area)")
    for c in res["cells"]:
        ars = {int(a): p for a, p in c["raster"]["areas"].items() if p["walkable_u2"] > 0}
        flag = len(ars) > 1 or any(p["area12_lock"] or p["spawn_weather"] or p["camera_place"] for p in ars.values())
        if flag:
            desc = " ".join(f"{a}(z{p['zone']},pl{p['camera_place']},w{p['walkable_u2']},enc{p['encounter_live_u2']})"
                            for a, p in sorted(ars.items()))
            print(f"  Disc{c['ns']} {tuple(c['cell'])} {c['why'][:28]:<28} {desc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
