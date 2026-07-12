"""THE INTERIOR ROCK-WALL TILE LANGUAGE -- the tile-neighbor decode (disc 1).

The plateau-edge study proved interior plateau walls speak a QUANTIZED tile language
(128x128px lattice-snapped rects over a large mountain-rock atlas region) that is neither
the coastal rock strip nor a per-block mural. This study decodes HOW the tiles are laid --
the prerequisite for synthesizing a from-scratch terrace wall. The competing hypotheses,
each implying a different synthesis recipe:

  A. CONTIGUOUS ATLAS WINDOWS -- geometric neighbors are ATLAS neighbors (the wall unrolls
     a big painted rock region continuously; the 'flowing' look of the unrolled render).
     Synthesis = slide contiguous windows over the wall surface.
  B. A WANG TABLE -- tiles constrain their partners per edge (the sea-strip model).
     Synthesis = solve the table.
  C. FREE MIXING -- any tile anywhere (unlikely given the flow).

Measured per plateau-wall component (the plateau_edge.py component logic), aggregated over
every disc-1 block with plateau grass: tile-group union-find (uv-equal shared edges, one
<=128px rect per group -- the ROW-BOUNDARY GROUPING GUARD), the tile lattice phase learned
from the data, the geometric-neighbor -> atlas-offset distribution (the hypothesis test),
per-tile positional roles (crest / base / mid), and group orientation stats.

Artifacts -> out/rock_tiles.json. Regenerate: py rock_wall_language.py
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X

PLATEAU = {10, 11, 12}
TILE_U = 0.0625                                            # 128px of the 2048-wide atlas
TILE_V = 0.03125                                           # 128px of the 4096-tall atlas
OUT = Path(__file__).with_name("out") / "rock_tiles.json"
kk = lambda v: (round(v[0], 3), round(v[1], 3), round(v[2], 3))

blocks = X.list_blocks(disc=1)
all_groups = []                                            # dicts: blk, tris, bbox, tile, roles
edge_pairs = []                                            # (tileA, tileB, du_tiles, dv_tiles)
corner_u_all = []
corner_v_all = []

for (bx, by) in blocks:
    try:
        bm = X.read_block(bx, by, disc=1)
    except Exception:
        continue
    V, U, T = bm.verts, bm.uvs, bm.tangents
    ntri = len(bm.flat_index) // 3
    tri_idx = [bm.flat_index[3*t:3*t+3] for t in range(ntri)]
    topo = [X.decode_id(int(round(T[idx[0]][0])))["topograph"] for idx in tri_idx]
    if not any(t in PLATEAU for t in topo):
        continue

    edge_tris = defaultdict(list)
    for t, idx in enumerate(tri_idx):
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge_tris[tuple(sorted((kk(V[idx[a]]), kk(V[idx[b]]))))].append(t)

    # plateau-wall 49 components (only walls attached to a plateau crest)
    crest49 = set()
    for e, ts in edge_tris.items():
        if len(ts) == 2:
            pair = {topo[ts[0]], topo[ts[1]]}
            if 49 in pair and pair & PLATEAU:
                crest49.add(ts[0] if topo[ts[0]] == 49 else ts[1])
    adj49 = defaultdict(set)
    for e, ts in edge_tris.items():
        r = [t for t in ts if topo[t] == 49]
        for i in range(len(r)):
            for j in range(i+1, len(r)):
                adj49[r[i]].add(r[j]); adj49[r[j]].add(r[i])
    comp_of = {}
    seen = set()
    for s in crest49:
        if s in seen:
            continue
        comp = {s}; st = [s]
        while st:
            t = st.pop()
            for t2 in adj49[t]:
                if t2 not in comp:
                    comp.add(t2); st.append(t2)
        seen |= comp
        for t in comp:
            comp_of[t] = s

    wall_tris = set(comp_of)
    if not wall_tris:
        continue

    # ---- tile groups: union-find over uv-EQUAL shared edges, guarded to one 128px rect ----
    parent = {t: t for t in wall_tris}
    def find(t):
        while parent[t] != t:
            parent[t] = parent[parent[t]]
            t = parent[t]
        return t
    def bbox_of(ts):
        us = [U[i][0] for t in ts for i in tri_idx[t]]
        vs = [U[i][1] for t in ts for i in tri_idx[t]]
        return min(us), min(vs), max(us), max(vs)
    members = {t: {t} for t in wall_tris}
    for e, ts in edge_tris.items():
        w = [t for t in ts if t in wall_tris]
        if len(w) != 2:
            continue
        t1, t2 = w
        uv1 = {kk(V[i]): tuple(np.round(U[i], 5)) for i in tri_idx[t1]}
        uv2 = {kk(V[i]): tuple(np.round(U[i], 5)) for i in tri_idx[t2]}
        if not all(uv1.get(p) == uv2.get(p) for p in e):
            continue                                       # a UV seam -- different tiles
        r1, r2 = find(t1), find(t2)
        if r1 == r2:
            continue
        u0, v0, u1, v1 = bbox_of(members[r1] | members[r2])
        if (u1 - u0) > TILE_U + 1e-4 or (v1 - v0) > TILE_V + 1e-4:
            continue                                       # the grouping guard
        parent[r2] = r1
        members[r1] |= members[r2]
        del members[r2]

    # ---- per group: snapped tile id + roles + neighbor context -----------------------------
    group_of_tri = {}
    blk_groups = {}
    for r, ts in members.items():
        u0, v0, u1, v1 = bbox_of(ts)
        corner_u_all += [u0, u1]
        corner_v_all += [v0, v1]
        # roles: what the group's tris touch (crest grass? base grass? shelf?)
        touch = Counter()
        for t in ts:
            for a, b in ((0, 1), (1, 2), (2, 0)):
                e = tuple(sorted((kk(V[tri_idx[t][a]]), kk(V[tri_idx[t][b]]))))
                for t2 in edge_tris[e]:
                    if t2 not in wall_tris and topo[t2] != 49:
                        touch[topo[t2]] += 1
        ys = [V[i][1] for t in ts for i in tri_idx[t]]
        g = dict(blk=[bx, by], n=len(ts), u0=u0, v0=v0, du=round(u1-u0, 5), dv=round(v1-v0, 5),
                 ymin=round(min(ys), 1), ymax=round(max(ys), 1),
                 touch={str(k): v for k, v in touch.items()})
        blk_groups[r] = g
        all_groups.append(g)
        for t in ts:
            group_of_tri[t] = r

    # ---- geometric-neighbor -> atlas-offset (the hypothesis test) --------------------------
    seen_pairs = set()
    for e, ts in edge_tris.items():
        w = [t for t in ts if t in wall_tris]
        if len(w) != 2:
            continue
        r1, r2 = group_of_tri[w[0]], group_of_tri[w[1]]
        if r1 == r2 or (r1, r2) in seen_pairs or (r2, r1) in seen_pairs:
            continue
        seen_pairs.add((r1, r2))
        g1, g2 = blk_groups[r1], blk_groups[r2]
        du = (g2["u0"] - g1["u0"]) / TILE_U
        dv = (g2["v0"] - g1["v0"]) / TILE_V
        edge_pairs.append((round(du, 2), round(dv, 2)))

# ---- report ----------------------------------------------------------------------------------
print(f"tile groups: {len(all_groups)} across "
      f"{len({tuple(g['blk']) for g in all_groups})} blocks")
dus = np.array([g["du"] for g in all_groups])
dvs = np.array([g["dv"] for g in all_groups])
full_u = float((np.abs(dus - TILE_U) < 0.004).mean())
full_v = float((np.abs(dvs - TILE_V) < 0.004).mean())
print(f"group rect size: FULL 128px in u for {full_u:.0%}, in v for {full_v:.0%} "
      f"(u med {np.median(dus):.4f} / v med {np.median(dvs):.4f})")

# the tile lattice phase, learned from the data
cu = np.array(corner_u_all) % TILE_U
cv = np.array(corner_v_all) % TILE_V
hu = np.histogram(cu, bins=16, range=(0, TILE_U))[0]
hv = np.histogram(cv, bins=16, range=(0, TILE_V))[0]
print(f"corner phase u (16 bins over 128px): {list(hu)}")
print(f"corner phase v: {list(hv)}")

# distinct tiles (snap u0,v0 to the dominant phase lattice)
pu = float(np.bincount((cu / TILE_U * 16).astype(int), minlength=16).argmax()) * TILE_U / 16
pv = float(np.bincount((cv / TILE_V * 16).astype(int), minlength=16).argmax()) * TILE_V / 16
tile_ids = Counter()
for g in all_groups:
    col = round((g["u0"] - pu) / TILE_U)
    row = round((g["v0"] - pv) / TILE_V)
    tile_ids[(col, row)] += 1
print(f"\ndistinct snapped tile ids: {len(tile_ids)}; "
      f"top 12: {tile_ids.most_common(12)}")
cols = [c for (c, r) in tile_ids]
rows = [r for (c, r) in tile_ids]
print(f"tile grid span: cols {min(cols)}..{max(cols)}, rows {min(rows)}..{max(rows)}")

# THE HYPOTHESIS TEST: atlas offsets between geometric neighbors
off = Counter(edge_pairs)
n_pairs = len(edge_pairs)
adj_atlas = sum(c for (du, dv), c in off.items()
                if (abs(abs(du) - 1) < 0.15 and abs(dv) < 0.15) or
                   (abs(du) < 0.15 and abs(abs(dv) - 1) < 0.15))
same_tile = sum(c for (du, dv), c in off.items() if abs(du) < 0.15 and abs(dv) < 0.15)
print(f"\ngeometric-neighbor pairs: {n_pairs}")
print(f"  ATLAS-ADJACENT (+-1 col/row): {adj_atlas} ({adj_atlas/max(1,n_pairs):.0%})  "
      f"<- hypothesis A evidence")
print(f"  SAME tile id (repeat): {same_tile} ({same_tile/max(1,n_pairs):.0%})")
print(f"  top offsets: {off.most_common(10)}")

# positional roles per tile row (crest vs base bands in the atlas?)
crest_rows_c = Counter()
base_rows_c = Counter()
for g in all_groups:
    row = round((g["v0"] - pv) / TILE_V)
    touch = {int(k): v for k, v in g["touch"].items()}
    if any(k in PLATEAU for k in touch):
        crest_rows_c[row] += 1
    if 0 in touch or 2 in touch:
        base_rows_c[row] += 1
print(f"\ncrest-touching groups by atlas row: {dict(sorted(crest_rows_c.items()))}")
print(f"base-touching groups by atlas row:  {dict(sorted(base_rows_c.items()))}")

OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(dict(groups=all_groups, edge_pairs=edge_pairs,
                               tiles={f"{c},{r}": n for (c, r), n in tile_ids.items()},
                               phase=[pu, pv]), indent=1))
print(f"\nartifacts -> {OUT}")
