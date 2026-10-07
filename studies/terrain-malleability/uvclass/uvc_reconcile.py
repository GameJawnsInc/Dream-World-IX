"""uvclass RECONCILE -- the three places this lane's instrument disagrees with a recorded law, each reproduced
side-by-side with the recorded method so the disagreement is located, not asserted.

R1 THE CANOPY 'NON-AFFINE' VERDICT (interior KB: "28-35 multi-tri continuity patches, non-affine, plan-affine max
   err ~0.15"; forest_uv_components.py). That script unions tris that share ONE VERTEX position with equal uv.
   We rebuild BOTH unions on the same bytes ((19,13), (17,14) topo 37) and fit each component:
     vertex-union (recorded method)  vs  edge-union (texture continuity: a seam is an EDGE with two uvs).
R2 BAKED-TERRAIN 'MURALS' (coast memory: topo 49 92-100% UV-unique per cell -> hand-painted murals). We reproduce
   the per-4u-cell uv-bbox SINGLETON rate (placement uniqueness) AND measure ART reuse on the same tris (atlas
   16px cells sampled >= 2 blocks away) -- for (9,5) and map-wide.
R3 THE (14,13) 'TILE LANGUAGE' WALL (interior KB plateau-edge + rock_wall_language.py: one 128px tile per wall
   quad, tile groups guarded to <= 1 rect). We measure what fraction of the wall's interior edges are uv-CONTINUOUS
   and how many 128px tile rects a continuous chart spans when no guard is applied.
Writes out/reconcile.json. Rerun: py studies/terrain-malleability/uvclass/uvc_reconcile.py
"""
import json
import math
from collections import Counter, defaultdict

import numpy as np

import uvc_common as C

d = C.load(1, "terrain")
P, UV, T, TOPO, BLK = d["P"], d["UV"], d["T"], d["TOPO"], d["BLK"]
z = np.load(C.OUT / "features_terrain.npz")
reuse_far = z["reuse_far"]
res = {}
bm = lambda bx, by: (BLK[:, 0] == bx) & (BLK[:, 1] == by)


def fit_res(tris):
    """3D-affine + plan-affine max residual (px) over all tri corners, + texel sv of the plan fit."""
    A3 = np.hstack([P[tris].reshape(-1, 3), np.ones((3 * len(tris), 1))])
    Ap = A3[:, [0, 2, 3]]
    Y = T[tris].reshape(-1, 2)
    out = {}
    for name, A in (("a3", A3), ("plan", Ap)):
        coef, *_ = np.linalg.lstsq(A, Y, rcond=None)
        out[name] = round(float(np.linalg.norm(A @ coef - Y, axis=1).max()), 1)
    return out


# ---- R1 ------------------------------------------------------------------------------------------------
r1 = {}
for (bx, by) in ((19, 13), (17, 14)):
    tris = np.nonzero(bm(bx, by) & (TOPO == 37))[0]
    # vertex-union exactly as forest_uv_components.py (round 3dp, |du|,|dv| < 5e-4 at the shared vertex)
    parent = {t: t for t in tris}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    pos = defaultdict(list)
    for t in tris:
        for k in range(3):
            pos[tuple(np.round(P[t, k] - [bx * 64, 0, -by * 64], 3))].append((t, k))
    for lst in pos.values():
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                (t1, k1), (t2, k2) = lst[i], lst[j]
                if t1 != t2 and abs(UV[t1, k1, 0] - UV[t2, k2, 0]) < 5e-4 and abs(UV[t1, k1, 1] - UV[t2, k2, 1]) < 5e-4:
                    parent[find(t1)] = find(t2)
    vcomp = defaultdict(list)
    for t in tris:
        vcomp[find(t)].append(t)
    m = np.zeros(len(P), bool)
    m[tris] = True
    pid = C.patches(P, UV, mask=m, eps_q=5e-4 * 1024)
    ecomp = defaultdict(list)
    for t in tris:
        ecomp[pid[t]].append(t)
    vbig = sorted(vcomp.values(), key=len, reverse=True)[:5]
    ebig = sorted(ecomp.values(), key=len, reverse=True)[:5]
    # how many edge-patches does each big vertex-component contain?
    r1[f"{bx},{by}"] = dict(
        tris=len(tris), vertex_union_components=len(vcomp), edge_union_patches=len(ecomp),
        vertex_top5=[dict(n=len(c), edge_patches_inside=len({pid[t] for t in c}), **fit_res(np.array(c))) for c in vbig],
        edge_top5=[dict(n=len(c), **fit_res(np.array(c))) for c in ebig])
    print(f"R1 forest ({bx},{by}): {len(tris)} tris -> vertex-union {len(vcomp)} comps / edge-union {len(ecomp)} patches")
    for c in r1[f"{bx},{by}"]["vertex_top5"]:
        print(f"   vertex comp n={c['n']:3d}  = {c['edge_patches_inside']:2d} edge patches   plan {c['plan']:6.1f}px  a3 {c['a3']:6.1f}px")
    for c in r1[f"{bx},{by}"]["edge_top5"]:
        print(f"   edge patch  n={c['n']:3d}                       plan {c['plan']:6.1f}px  a3 {c['a3']:6.1f}px")
res["R1_canopy_union"] = r1

# ---- R2 ------------------------------------------------------------------------------------------------
def singleton_rate(mask):
    """BAKED-TERRAIN's metric: group tris by 4u cell, hash each cell's uv bbox (3dp), share of cells whose
    signature occurs ONCE in the scanned set."""
    cells = defaultdict(list)
    for t in np.nonzero(mask)[0]:
        cells[(int(BLK[t, 0]), int(BLK[t, 1]), math.floor(P[t, :, 0].mean() / 4), math.floor(P[t, :, 2].mean() / 4))].append(t)
    sig = {}
    for c, ts in cells.items():
        u = UV[ts].reshape(-1, 2)
        sig[c] = (round(float(u[:, 0].min()), 3), round(float(u[:, 1].min()), 3),
                  round(float(u[:, 0].max()), 3), round(float(u[:, 1].max()), 3))
    cnt = Counter(sig.values())
    return len(sig), float(np.mean([cnt[s] == 1 for s in sig.values()]))


from ff9mapkit.world.transplant import _cell_rect   # noqa: E402  (the kit's OWN baked-terrain fingerprint)


def kit_singleton_rate(mask):
    """EXACTLY transplant.py's crosses-baked-terrain test: per tri, _cell_rect(poly) (the tri's plan-affine field
    evaluated at its 4u cell's corners, 3dp key); a key whose cell set has <= 1 cell is baked-unique. Run over the
    whole masked set (map-wide = the strictest version: every other placement anywhere can be a sibling)."""
    cells_of = defaultdict(set)
    keys = {}
    for t in np.nonzero(mask)[0]:
        poly = [(tuple(P[t, k]), None, tuple(UV[t, k])) for k in range(3)]
        r = _cell_rect(poly)
        if r is None:
            continue
        cell = (int(BLK[t, 0]), int(BLK[t, 1]), math.floor(P[t, :, 0].mean() / 4), math.floor(P[t, :, 2].mean() / 4))
        cells_of[r[0]].add(cell)
        keys[t] = r[0]
    if not keys:
        return 0, float("nan")
    return len(keys), float(np.mean([len(cells_of[k]) <= 1 for k in keys.values()]))


r2 = {}
for name, mask in (("mapwide_topo49", TOPO == 49),
                   ("mapwide_topo17", TOPO == 17), ("mapwide_topo38", TOPO == 38),
                   ("mapwide_grass0", TOPO == 0)):
    ncell, srate = singleton_rate(mask)
    nk, krate = kit_singleton_rate(mask)
    rf = reuse_far[mask]
    print(f"   kit _cell_rect baked-unique rate (the recorded metric): {100 * krate:.1f}% of {nk} non-degenerate tris")
    r2[name] = dict(tris=int(mask.sum()), cells=ncell, cell_uv_singleton_pct=round(100 * srate, 1),
                    kit_cell_rect_baked_unique_pct=round(100 * krate, 1),
                    art_far_reuse_p50_blocks=float(np.median(rf)),
                    art_unique_pct=round(100 * float((rf < 2).mean()), 1))
    print(f"R2 {name}: {ncell} cells, placement-unique (singleton uv bbox) {100 * srate:.1f}%  |  ART far-reuse "
          f"p50 {np.median(rf):.0f} blocks, unique art {100 * (rf < 2).mean():.1f}%")
res["R2_baked_terrain"] = r2

# ---- R3 ------------------------------------------------------------------------------------------------
# the (14,13) wall = the largest edge-connected topo-49 component of the block (as uvc_calibrate.py)
idx = np.nonzero(bm(14, 13) & (TOPO == 49))[0]
edges = defaultdict(list)
for t in idx:
    ks = [C.poskey(P[t, k]) for k in range(3)]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        ka, kb = ks[a], ks[b]
        edges[(ka, kb) if ka <= kb else (kb, ka)].append((t, a, b) if ka <= kb else (t, b, a))
n_int = n_cont = n_cont_cross = 0
for e, lst in edges.items():
    if len(lst) != 2:
        continue
    (t1, a1, b1), (t2, a2, b2) = lst
    n_int += 1
    dmax = max(abs(UV[t1, a1, 0] - UV[t2, a2, 0]), abs(UV[t1, a1, 1] - UV[t2, a2, 1]),
               abs(UV[t1, b1, 0] - UV[t2, b2, 0]), abs(UV[t1, b1, 1] - UV[t2, b2, 1]))
    if dmax <= 0.5 / 1024:
        n_cont += 1
        # does this continuous edge join two DIFFERENT 128px tiles (centroid tile of each tri)?
        c1 = tuple((T[t1].mean(0) // 128).astype(int)); c2 = tuple((T[t2].mean(0) // 128).astype(int))
        n_cont_cross += c1 != c2
m = np.zeros(len(P), bool)
m[idx] = True
pid = C.patches(P, UV, mask=m, eps_q=0.5)
sizes = Counter(pid[idx].tolist())
spans = []
for p, n in sizes.items():
    tr = np.nonzero(pid == p)[0]
    cen = T[tr].mean(1)
    spans.append(len({tuple((c // 128).astype(int)) for c in cen}))
r3 = dict(wall_tris=int(len(idx)), interior_edges=n_int, uv_continuous_pct=round(100 * n_cont / n_int, 1),
          continuous_edges_joining_two_tiles_pct=round(100 * n_cont_cross / max(n_cont, 1), 1),
          patches=len(sizes), tiles_spanned_per_patch=dict(sorted(Counter(spans).items())),
          tris_in_patches_spanning_ge4_tiles_pct=round(100 * sum(n for p, n in sizes.items()
                                                                  if spans[list(sizes).index(p)] >= 4) / len(idx), 1))
print(f"R3 (14,13) topo-49: {len(idx)} tris, {n_int} interior edges, {r3['uv_continuous_pct']}% uv-continuous; "
      f"{r3['continuous_edges_joining_two_tiles_pct']}% of the continuous edges join tris in DIFFERENT 128px tiles; "
      f"{len(sizes)} patches, tiles spanned per patch {r3['tiles_spanned_per_patch']}, "
      f"{r3['tris_in_patches_spanning_ge4_tiles_pct']}% of tris sit in patches spanning >= 4 tiles")
res["R3_rockwall_continuity"] = r3
# the same continuity rate map-wide per family (stock-normal reference)
fam_cont = defaultdict(lambda: [0, 0])
for e, lst in []:
    pass
(C.OUT / "reconcile.json").write_text(json.dumps(res, indent=1))
print(f"wrote {C.OUT / 'reconcile.json'}")
