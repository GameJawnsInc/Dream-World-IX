"""STEP 2 -- the per-(cell, part) DISC-DIFF FOOTPRINT, the hazard layers, and the F18 vs D4-01 reconciliation.

For every real (cell, part) present on both discs: the set of triangles WITHOUT an exact all-channel
counterpart on the other disc (order-invariant, lib.tri_keys), split into
  * geometry-unmatched (the position triple itself is new/cut/re-heighted), and
  * attribute-only (same winding+positions, but UV / normal / IDALL differ).
The FOOTPRINT of a cell is the XZ union of every unmatched triangle of either disc, rasterized on a 0.5u
lattice (cell centres) -- per part and over all parts.

HAZARD LAYERS (disc-4 semantics an edit can land on), each a set of triangles with world XZ geometry:
  RIDGE       disc-4-only Terrain tri with topograph 49 whose DISC-1 ground at its centroid is walkable (D4-08)
  LAND2SEA    disc-1-only Terrain tri whose centroid grounds on a Sea* part / MISS on disc 4 (D4-11 Shimmering)
  ENTR_LOST   disc-1 Terrain tri with event!=0 whose centroid grounds on event 0 on disc 4 (D4-14 / D4-12)
  ENTR_NEW    disc-4 Terrain tri with event!=0 whose centroid grounds on event 0 on disc 1 (D4-11 / Iifa grown)
  OBJECT      any unmatched Object tri, either disc (D4-13 promotions, Cleyra adds, (13,4)/(18,11) removals)
Ground = placement.place (engine-faithful; IDALL 4078/4088/2040 skip + 0x31EE veto) over the cell's Form-1
walk parts in registration order; the Water Shrine block (219 = (3,9)) and volcano cells are sampled with
check_order_exceptions bypassed (place() itself does not refuse) -- flagged in the output.

F18 RECONCILIATION: operators/disc_tree_channels.py compares Terrain INDEX-ALIGNED on the 64 same-vcount
blocks, so a permutation reads as verts/uv/normal/tangent changes. Here: (1) reproduce its 51/44/11 block
counts from its own JSON, (2) count how many of those blocks are pure permutations, (3) recount
event/area/topograph differences ORDER-INVARIANTLY on geometry-matched triangle pairs over all 260 terrain
blocks (attribute changes on unchanged geometry), and separately on re-cut geometry.
Writes out/s2_footprint.json (counts, per-cell summaries) and lib.CACHE_DIR/s2_layers.pkl (geometry, outside repo).
Run (from C:\\gd\\Dream-World-IX\\ff9mapkit):  py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_disc4_edit_reach/s2_footprint.py
"""
import json
import pickle
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib as L                                       # noqa: E402
import numpy as np                                    # noqa: E402

data = L.load_cache()
meshes, pairs = data["meshes"], data["pairs"]
objs = L.mesh_objects()
RES = 0.5
NG = int(64 / RES)


def world_tris(d, x, y, p):
    m = meshes[(d, x, y, p)]
    V = m["V"].copy()
    V[:, 0] += 64 * x
    V[:, 2] -= 64 * y
    return V[m["T"]]                       # (T,3,3) world


def raster(tris_local):
    """0.5u cell-centre mask (NG x NG) covered by any of the block-LOCAL triangles (XZ)."""
    mask = np.zeros((NG, NG), bool)
    for tri in tris_local:
        xs, zs = tri[:, 0], tri[:, 2]
        i0, i1 = int(max(0, np.floor(xs.min() / RES - 0.5))), int(min(NG - 1, np.ceil(xs.max() / RES - 0.5)))
        j0, j1 = int(max(0, np.floor(-zs.max() / RES - 0.5))), int(min(NG - 1, np.ceil(-zs.min() / RES - 0.5)))
        if i1 < i0 or j1 < j0:
            continue
        ii, jj = np.meshgrid(np.arange(i0, i1 + 1), np.arange(j0, j1 + 1), indexing="ij")
        px, pz = (ii + 0.5) * RES, -(jj + 0.5) * RES
        a, b, c = tri[0], tri[1], tri[2]
        d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
        if abs(d) < 1e-12:
            continue
        w0 = ((b[2] - c[2]) * (px - c[0]) + (c[0] - b[0]) * (pz - c[2])) / d
        w1 = ((c[2] - a[2]) * (px - c[0]) + (a[0] - c[0]) * (pz - c[2])) / d
        w2 = 1 - w0 - w1
        inside = (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
        mask[ii[inside], jj[inside]] = True
    return mask


# ---------------------------------------------------------------- footprints per (cell, part)
cls_count = Counter()
cell_parts = defaultdict(dict)
masks_all, masks_ter, masks_geo_ter = {}, {}, {}
unmatched_geom = {}                                      # (cell) -> dict of world arrays for s5
for (x, y, p), pr in sorted(pairs.items()):
    if pr["raw_identical"]:
        c = "IDENT"
    elif pr["perm"]:
        c = "PERM"
    elif pr["g1"].all() and pr["g4"].all():
        c = "ATTR"
    else:
        c = "GEOM"
    cls_count[(p == "terrain", c)] += 1
    u1 = ~pr["m1"]; u4 = ~pr["m4"]
    gu1 = ~pr["g1"]; gu4 = ~pr["g4"]
    cell_parts[(x, y)][p] = {"cls": c, "n1": pr["n1"], "n4": pr["n4"], "u1": int(u1.sum()), "u4": int(u4.sum()),
                             "gu1": int(gu1.sum()), "gu4": int(gu4.sum())}
    if c in ("IDENT", "PERM"):
        continue
    W1, W4 = world_tris(1, x, y, p), world_tris(4, x, y, p)
    loc = lambda W: W - np.array([64 * x, 0, -64 * y])
    mk = raster(np.concatenate([loc(W1[u1]), loc(W4[u4])]))
    masks_all[(x, y)] = masks_all.get((x, y), np.zeros((NG, NG), bool)) | mk
    if p == "terrain":
        masks_ter[(x, y)] = mk
        masks_geo_ter[(x, y)] = raster(np.concatenate([loc(W1[gu1]), loc(W4[gu4])]))
    g = unmatched_geom.setdefault((x, y), {})
    g[p] = {"u1": W1[u1], "u4": W4[u4], "gu1": W1[gu1], "gu4": W4[gu4]}
# parts present on one disc only: whole part is footprint
for (d, x, y, p) in meshes:
    if (x, y, p) in pairs:
        continue
    W = world_tris(d, x, y, p)
    mk = raster(W - np.array([64 * x, 0, -64 * y]))
    masks_all[(x, y)] = masks_all.get((x, y), np.zeros((NG, NG), bool)) | mk
    g = unmatched_geom.setdefault((x, y), {})
    g[p] = {"u1": W if d == 1 else np.zeros((0, 3, 3)), "u4": W if d == 4 else np.zeros((0, 3, 3)),
            "gu1": W if d == 1 else np.zeros((0, 3, 3)), "gu4": W if d == 4 else np.zeros((0, 3, 3))}
    cell_parts[(x, y)][p] = {"cls": f"ONLY_D{d}", "n1": len(W) if d == 1 else 0, "n4": len(W) if d == 4 else 0}
print("pair classes (terrain?, class):", dict(cls_count))

# ---------------------------------------------------------------- hazard layers
grounds = {}


def ground_fn(d, x, y):
    k = (d, x, y)
    if k not in grounds:
        parts = L.blockmeshes(d, x, y, objs)
        ml = L.walk_meshlist(parts)
        grounds[k] = (ml, [L.P.build_index(bm) for _, bm in ml])
    ml, idx = grounds[k]
    return lambda lx, lz: L.P.place(ml, lx, lz, 0.0, sky=True, index=idx)


haz = defaultdict(lambda: defaultdict(list))            # cell -> layer -> [world tri (3,3)]
ex_cells = set()
for (x, y), g in sorted(unmatched_geom.items()):
    if y * 24 + x == L.P.WATER_SHRINE_BLOCK or any("volcano" in p for p in g):
        ex_cells.add((x, y))
    if "terrain" in g:
        f1, f4 = ground_fn(1, x, y), ground_fn(4, x, y)
        # classify d4-only/u4 tris
        V4, T4, I4 = meshes[(4, x, y, "terrain")]["V"], meshes[(4, x, y, "terrain")]["T"], meshes[(4, x, y, "terrain")]["idall"]
        u4 = ~pairs[(x, y, "terrain")]["m4"]
        for ti in np.nonzero(u4)[0]:
            tri = V4[T4[ti]]
            cx, cz = tri[:, 0].mean(), tri[:, 2].mean()
            wtri = tri + np.array([64 * x, 0, -64 * y])
            ida = int(I4[ti])
            if L.topo(ida) == 49:
                g1 = f1(cx, cz)
                if g1[3] is not None and g1[3] in L.P.WALK_OK:
                    haz[(x, y)]["RIDGE"].append(wtri)
            if L.event(ida):
                g1 = f1(cx, cz)
                if g1[3] is None or not L.event(g1[2]):
                    haz[(x, y)]["ENTR_NEW"].append(wtri)
        V1, T1, I1 = meshes[(1, x, y, "terrain")]["V"], meshes[(1, x, y, "terrain")]["T"], meshes[(1, x, y, "terrain")]["idall"]
        u1 = ~pairs[(x, y, "terrain")]["m1"]
        for ti in np.nonzero(u1)[0]:
            tri = V1[T1[ti]]
            cx, cz = tri[:, 0].mean(), tri[:, 2].mean()
            wtri = tri + np.array([64 * x, 0, -64 * y])
            g4 = f4(cx, cz)
            if g4[1].startswith("Sea") or g4[1] == "MISS":
                haz[(x, y)]["LAND2SEA"].append(wtri)
            if L.event(int(I1[ti])) and not L.event(g4[2]):
                haz[(x, y)]["ENTR_LOST"].append(wtri)
    for p in g:
        if p == "object":
            haz[(x, y)]["OBJECT"].extend(list(g[p]["u1"]) + list(g[p]["u4"]))
hz_count = Counter()
hz_cells = defaultdict(list)
for c, layers in haz.items():
    for k, v in layers.items():
        if v:
            hz_count[k] += len(v)
            hz_cells[k].append(c)
print("hazard tris:", dict(hz_count))
print("hazard cells:", {k: len(v) for k, v in hz_cells.items()})

# ---------------------------------------------------------------- F18 reconciliation
op = json.loads((L.LANE.parent / "operators" / "out" / "disc_tree_channels.json").read_text(encoding="utf-8"))["rows"]
f18 = Counter()
f18_blocks = defaultdict(list)
for k, v in op.items():
    for t in (v.get("tangent") or {}):
        f18[t] += 1
        f18_blocks[t].append(tuple(int(a) for a in k.split(",")))
assert (f18["topograph"], f18["area"], f18["event"]) == (51, 44, 11), "must reproduce operators F18 51/44/11"
perm_ter = {(x, y) for (x, y, p), pr in pairs.items() if p == "terrain" and pr["perm"] and not pr["raw_identical"]}
f18_perm = {t: sorted(set(b) & perm_ter) for t, b in f18_blocks.items()}


def geo_pairs(x, y):
    """Order-invariant geometry pairing of terrain tris -> list of (i1, i4)."""
    from collections import defaultdict as dd
    a = L.decode(objs[(1, "0_1", x, y, "terrain")], 1, x, y)
    b = L.decode(objs[(4, "0_1", x, y, "terrain")], 4, x, y)
    k1 = [k[0] for k in L.tri_keys(a, L._prec(a))]
    k4 = [k[0] for k in L.tri_keys(b, L._prec(b))]
    pool = dd(list)
    for j, k in enumerate(k4):
        pool[k].append(j)
    out = []
    for i, k in enumerate(k1):
        if pool.get(k):
            out.append((i, pool[k].pop()))
    return out


oi = Counter()
oi_blocks = defaultdict(list)
oi_tris = Counter()
recut_id = Counter()
for (x, y, p), pr in sorted(pairs.items()):
    if p != "terrain" or pr["perm"]:
        continue
    I1, I4 = meshes[(1, x, y, p)]["idall"], meshes[(4, x, y, p)]["idall"]
    hit = Counter()
    for i, j in geo_pairs(x, y):
        a, b = int(I1[i]), int(I4[j])
        if a != b:
            for nm, fn in (("event", L.event), ("area", L.area), ("topograph", L.topo)):
                if fn(a) != fn(b):
                    hit[nm] += 1
    for nm, n in hit.items():
        oi[nm] += 1
        oi_blocks[nm].append((x, y))
        oi_tris[nm] += n
    # re-cut geometry: does the re-cut introduce or drop a field VALUE (set compare -- tri counts differ by
    # construction on re-cut geometry, so a histogram compare would flag every re-cut block)
    gu1, gu4 = ~pr["g1"], ~pr["g4"]
    if gu1.any() or gu4.any():
        for nm, fn in (("event", L.event), ("area", L.area), ("topograph", L.topo)):
            if {fn(int(v)) for v in I1[gu1]} != {fn(int(v)) for v in I4[gu4]}:
                recut_id[nm] += 1
print("F18 (index-aligned, operators JSON):", dict(f18), "| of those blocks, pure permutations:",
      {k: len(v) for k, v in f18_perm.items()})
print("ORDER-INVARIANT, geometry-matched tris whose IDALL field differs -> blocks:", dict(oi), "tris:", dict(oi_tris))
print("re-cut geometry whose field histogram differs -> blocks:", dict(recut_id))

# ---------------------------------------------------------------- per-cell summary
cells_out = {}
for c in sorted(set(cell_parts)):
    ma, mt = masks_all.get(c), masks_ter.get(c)
    cells_out[f"{c[0]},{c[1]}"] = {
        "parts": cell_parts[c],
        "footprint_all_frac": round(float(ma.mean()), 4) if ma is not None else 0.0,
        "footprint_terrain_frac": round(float(mt.mean()), 4) if mt is not None else 0.0,
        "footprint_terrain_geom_frac": round(float(masks_geo_ter[c].mean()), 4) if c in masks_geo_ter else 0.0,
        "hazards": {k: len(v) for k, v in haz.get(c, {}).items() if v},
        "order_exception_cell": c in ex_cells,
    }
fr = [v["footprint_all_frac"] for v in cells_out.values() if v["footprint_all_frac"] > 0]
print(f"cells with a non-empty footprint: {len(fr)}; median area frac {np.median(fr):.3f}, p90 {np.percentile(fr, 90):.3f}")
out = {"pair_classes": {f"{'terrain' if k[0] else 'other'}:{k[1]}": v for k, v in cls_count.items()},
       "hazard_tris": dict(hz_count), "hazard_cells": {k: [list(c) for c in sorted(v)] for k, v in hz_cells.items()},
       "f18": {"index_aligned_blocks": dict(f18), "of_which_pure_permutation": {k: [list(c) for c in v] for k, v in f18_perm.items()},
               "orderinv_geom_matched_blocks": dict(oi), "orderinv_geom_matched_tris": dict(oi_tris),
               "orderinv_blocks_list": {k: [list(c) for c in v] for k, v in oi_blocks.items()},
               "recut_histogram_shift_blocks": dict(recut_id)},
       "order_exception_cells": [list(c) for c in sorted(ex_cells)],
       "cells": cells_out}
(L.OUT / "s2_footprint.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
with open(L.CACHE_DIR / "s2_layers.pkl", "wb") as fh:
    pickle.dump({"unmatched": unmatched_geom, "hazard": {c: dict(v) for c, v in haz.items()},
                 "masks_all": masks_all, "masks_ter": masks_ter, "masks_geo_ter": masks_geo_ter}, fh)
print("wrote out/s2_footprint.json and", L.CACHE_DIR / "s2_layers.pkl")
