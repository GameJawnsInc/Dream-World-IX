"""LEAD: the 45 area-12 / topograph-41 / event-1 triangles in the live Disc1 (and Disc4) Block[19][18] Terrain.

Explains, does not conclude:
  1. which tris, where (world cells), and what the ground query reads there (area, lock, zone record)
  2. do they ARM a dispatcher? -- their packed cell tags vs the object-0 cell tags of all 13 LIVE dispatchers
     (live mod-folder override when present, else stock), US language
  3. where they came from -- every STOCK 0_1 tri (both discs) with the same IDALL, and a translation-invariant SHAPE
     match of the 45-tri set against each stock block's tris of that IDALL (relative XZ of sorted centroids)
  4. the file's mtime + the stock area layer of the documented horseshoe donor rect (5-6,15-16)

Rerun:  py studies/terrain-malleability/gap_area_layer/lead_1918.py   -> out/lead_1918.json
"""
import datetime
import json
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import arealib as A                                  # noqa: E402
import numpy as np                                   # noqa: E402
from ff9mapkit.eb.model import EbScript              # noqa: E402
from ff9mapkit.world import entrance as EN           # noqa: E402

SUB = "StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/world/us"


def live_dispatchers():
    alld = EN.load_all_dispatchers()
    out = {}
    for n, langs in alld.items():
        src, data = "stock", langs.get("us")
        for fo in ("FF9CustomMap", "FF9CustomMap-world", "MoguriMain"):
            p = A.GAME / fo / SUB / (n.upper() + ".eb.bytes")
            if p.is_file():
                src, data = str(p), p.read_bytes()
                break
        out[n] = (src, data)
    p = A.GAME / "FF9CustomMap-world" / SUB / "EVT_WORLD_WORLD13.eb.bytes"
    if p.is_file():
        out["evt_world_world13"] = (str(p), p.read_bytes())
    return out


def tags_of(data):
    s = EbScript(data)
    res = {}
    for f in s.entry(0).funcs:
        c = EN.unpack_cell_tag(f.tag)
        if c is not None:
            res[c] = f.tag
    return res


def shape(V, cx0=0.0, cz0=0.0):
    cen = V.mean(axis=1)
    pts = sorted((round(float(c[0]) - cx0, 2), round(float(c[2]) - cz0, 2)) for c in cen)
    mx, mz = min(p[0] for p in pts), min(p[1] for p in pts)
    return [(round(p[0] - mx, 2), round(p[1] - mz, 2)) for p in pts]


def main():
    res = {}
    disp = live_dispatchers()
    dtags = {n: tags_of(d) for n, (src, d) in disp.items()}
    for ns in (1, 4):
        p = A.GAME / f"FF9CustomMap-world/FF9_Data/WorldMap/Disc{ns}/0_1/r18/Block[19][18] Terrain.ff9mesh"
        V, ids = A.read_ff9mesh_arrays(p)
        ev = ((ids & 0xC000) >> 14) > 0
        evids = Counter(ids[ev].tolist())
        Ve = V[ev]
        cen = Ve.mean(axis=1)
        wx = 19 * 64 + cen[:, 0]
        wz = -18 * 64 + cen[:, 2]
        cells = Counter((int(x // 32), int(z // -32), int((i & 0xC000) >> 14)) for x, z, i in zip(wx, wz, ids[ev]))
        hits = {}
        for (cx, cz, e), n in cells.items():
            for dn, tg in dtags.items():
                if (cx, cz, e) in tg:
                    hits.setdefault(f"{cx},{cz},e{e}", []).append(dn)
        res[f"Disc{ns}"] = {"file": str(p), "mtime": datetime.datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
                            "event_tris_by_idall": {f"{k} {A.decode(k)}": v for k, v in evids.items()},
                            "event_world_bbox": [round(float(wx.min()), 2), round(float(wx.max()), 2),
                                                 round(float(wz.min()), 2), round(float(wz.max()), 2)],
                            "event_cells": {f"{k[0]},{k[1]},e{k[2]}": v for k, v in cells.items()},
                            "dispatcher_tag_matches": hits}
    # ---- stock source search ----
    target = [k for k in res["Disc1"]["event_tris_by_idall"]]
    tid = int(target[0].split()[0])
    live_shape = None
    p1 = A.GAME / "FF9CustomMap-world/FF9_Data/WorldMap/Disc1/0_1/r18/Block[19][18] Terrain.ff9mesh"
    V1, i1 = A.read_ff9mesh_arrays(p1)
    live_shape = shape(V1[i1 == tid])
    found = []
    for (d, lod, x, y, part) in sorted(A._objs()):
        if lod != "0_1":
            continue
        V, ids = A.stock_mesh(f"d{d}/{lod}/{x},{y}/{part}")
        m = ids == tid
        if m.any():
            sh = shape(V[m])
            found.append({"disc": d, "block": [x, y], "part": part, "tris": int(m.sum()),
                          "shape_equal_to_live": sh == live_shape})
    res["stock_tris_with_same_idall"] = found
    # union shape in WORLD coords (a multi-block entrance cluster), then the exact translation that maps it to live
    allV = []
    for f in found:
        if f["disc"] != 1:
            continue
        V, ids = A.stock_mesh(f"d1/0_1/{f['block'][0]},{f['block'][1]}/{f['part']}")
        W_ = V[ids == tid].copy()
        W_[:, :, 0] += f["block"][0] * 64
        W_[:, :, 2] += -f["block"][1] * 64
        allV.append(W_)
    SW = np.concatenate(allV)
    LW = V1[i1 == tid].copy()
    LW[:, :, 0] += 19 * 64
    LW[:, :, 2] += -18 * 64
    def keyset(Wt, off):
        return sorted(tuple(sorted((round(float(c[0] - off[0]), 2), round(float(c[1] - off[1]), 2),
                                    round(float(c[2] - off[2]), 2)) for c in t)) for t in Wt)
    off = (LW[:, :, 0].min() - SW[:, :, 0].min(), 0.0, LW[:, :, 2].min() - SW[:, :, 2].min())
    same_xz = sorted(tuple(sorted((round(float(c[0]), 2), round(float(c[2]), 2)) for c in t)) for t in SW) ==         sorted(tuple(sorted((round(float(c[0] - off[0]), 2), round(float(c[2] - off[2]), 2)) for c in t)) for t in LW)
    dy = float(np.median(LW[:, :, 1]) - np.median(SW[:, :, 1]))
    from ff9mapkit.world import locate as LOC
    cen = SW.reshape(-1, 3).mean(axis=0)
    res["union_match"] = {"stock_tris": int(len(SW)), "live_tris": int(len(LW)),
                          "translation_xz": [round(float(off[0]), 3), round(float(off[2]), 3)],
                          "xz_shape_identical_after_translation": bool(same_xz), "median_dy": round(dy, 3),
                          "stock_world_centroid": [round(float(cen[0]), 2), round(float(cen[2]), 2)],
                          "stock_nearest_landmark": LOC.nearest_landmark(float(cen[0]), float(cen[2]))}
    res["idall"] = {"value": tid, **A.decode(tid)}
    z = np.load(A.OUT / "stock_atlas.npz")
    a1 = z["area_d1"]
    don = {}
    for bx, by in ((5, 15), (6, 15), (5, 16), (6, 16)):
        blk = a1[bx * 64:(bx + 1) * 64, by * 64:(by + 1) * 64]
        don[f"{bx},{by}"] = dict(Counter(blk[blk >= 0].ravel().tolist()).most_common(5))
    res["horseshoe_donor_stock_areas_disc1"] = don
    (A.OUT / "lead_1918.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, indent=1, default=str)[:6000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
