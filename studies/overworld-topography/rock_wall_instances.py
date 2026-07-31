"""THE ROCK-WALL INSTANCE ANATOMY -- per-instance orientation / mirror / transition decode.

The terrace-wall T1 round-1 failure (2026-07-30, studies/path-d-new-world/
TERRACE-WALL-PREDICTION.md) traced to questions the first decode (rock_wall_language.py)
never asked. Its groups ARE tile instances; this study reuses that grouping VERBATIM (same
component logic, same uv-equal union-find, same <=128px guard) and measures, per instance:

  1. V-ORIENTATION -- sign of cov(world y, atlas v) over the instance's vertices. Is a
     tile's vertical orientation FIXED across stock instances, or do instances flip?
     (T1 applied ONE exemplar's orientation to every use and shipped upside-down
     grass-cliff transition tiles.)
  2. U-MIRRORING -- for each horizontally-adjacent instance PAIR, whether u advances in
     the same sense along the shared wall direction or reflects. Is T1's mirror-butterfly
     part of the language or off-language?
  3. VERTICAL TRANSITIONS -- the (tile below -> tile above) table across course
     boundaries, with both sides' v-orientations. The crest grass-fringe tiles' behaviour
     falls out of this + the crest-touch roles.

Artifacts -> out/rock_tile_instances.json + a printed LAW summary. Read-only vs stock.
Regenerate: py -X utf8 rock_wall_instances.py
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402

PLATEAU = {10, 11, 12}
TILE_U = 0.0625
TILE_V = 0.03125
OUT = Path(__file__).with_name("out") / "rock_tile_instances.json"
kk = lambda v: (round(v[0], 3), round(v[1], 3), round(v[2], 3))   # noqa: E731

phase = json.loads((Path(__file__).with_name("out") / "rock_tiles.json").read_text())["phase"]
PU, PV = phase

instances = []                                              # one dict per tile instance
h_pairs = []                                                # horizontal adjacency records
v_pairs = []                                                # vertical adjacency records

for (bx, by) in X.list_blocks(disc=1):
    try:
        bm = X.read_block(bx, by, disc=1)
    except Exception:                                       # noqa: BLE001
        continue
    V, U, T = bm.verts, bm.uvs, bm.tangents
    ntri = len(bm.flat_index) // 3
    tri_idx = [bm.flat_index[3 * t:3 * t + 3] for t in range(ntri)]
    topo = [X.decode_id(int(round(T[idx[0]][0])))["topograph"] for idx in tri_idx]
    if not any(t in PLATEAU for t in topo):
        continue

    edge_tris = defaultdict(list)
    for t, idx in enumerate(tri_idx):
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge_tris[tuple(sorted((kk(V[idx[a]]), kk(V[idx[b]]))))].append(t)

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
            for j in range(i + 1, len(r)):
                adj49[r[i]].add(r[j])
                adj49[r[j]].add(r[i])
    comp_of = {}
    seen = set()
    for s in crest49:
        if s in seen:
            continue
        comp = {s}
        st = [s]
        while st:
            t = st.pop()
            for t2 in adj49[t]:
                if t2 not in comp:
                    comp.add(t2)
                    st.append(t2)
        seen |= comp
        for t in comp:
            comp_of[t] = s
    wall_tris = set(comp_of)
    if not wall_tris:
        continue

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
            continue
        r1, r2 = find(t1), find(t2)
        if r1 == r2:
            continue
        u0, v0, u1, v1 = bbox_of(members[r1] | members[r2])
        if (u1 - u0) > TILE_U + 1e-4 or (v1 - v0) > TILE_V + 1e-4:
            continue
        parent[r2] = r1
        members[r1] |= members[r2]
        del members[r2]

    # ---- per-instance measurements ----------------------------------------------------------
    inst_of_tri = {}
    inst_local = {}
    for r, ts in members.items():
        pts = []                                            # (x, y, z, u, v) samples
        for t in ts:
            for i in tri_idx[t]:
                pts.append((V[i][0], V[i][1], V[i][2], U[i][0], U[i][1]))
        P = np.array(pts)
        u0, v0, u1, v1 = bbox_of(ts)
        col = round((u0 - PU) / TILE_U)
        row = round((v0 - PV) / TILE_V)
        yspan = float(P[:, 1].max() - P[:, 1].min())
        # v-orientation: cov(world y, atlas v); |corr| gates degenerate (flat) instances
        vy = float(np.cov(P[:, 1], P[:, 4])[0, 1]) if len(P) > 2 else 0.0
        sy, sv = float(P[:, 1].std()), float(P[:, 4].std())
        v_corr = vy / (sy * sv) if sy > 1e-6 and sv > 1e-9 else 0.0
        # principal horizontal direction (for the pairwise u-sense test)
        XZ = P[:, [0, 2]] - P[:, [0, 2]].mean(axis=0)
        if len(P) > 2 and float(np.abs(XZ).sum()) > 1e-9:
            w_, vec = np.linalg.eigh(np.cov(XZ.T))
            hdir = vec[:, int(np.argmax(w_))]
        else:
            hdir = np.array([1.0, 0.0])
        s = XZ @ hdir
        us = P[:, 3] - P[:, 3].mean()
        ss, su = float(np.std(s)), float(np.std(us))
        u_corr = float(np.mean(s * us)) / (ss * su) if ss > 1e-6 and su > 1e-9 else 0.0
        touch = Counter()
        for t in ts:
            for a, b in ((0, 1), (1, 2), (2, 0)):
                e = tuple(sorted((kk(V[tri_idx[t][a]]), kk(V[tri_idx[t][b]]))))
                for t2 in edge_tris[e]:
                    if t2 not in wall_tris and topo[t2] != 49:
                        touch[topo[t2]] += 1
        idx_ = len(instances)
        cen = P[:, :3].mean(axis=0)
        instances.append(dict(
            blk=[bx, by], tile=[col, row], n=len(ts), yspan=round(yspan, 2),
            v_corr=round(v_corr, 3), u_corr=round(u_corr, 3),
            hdir=[round(float(hdir[0]), 4), round(float(hdir[1]), 4)],
            cen=[round(float(c), 2) for c in cen],
            crest_touch=bool(set(touch) & PLATEAU), base_touch=bool(set(touch) - PLATEAU - {49}),
        ))
        inst_local[r] = idx_
        for t in ts:
            inst_of_tri[t] = idx_

    # ---- instance adjacency (any shared edge between different instances) -------------------
    seen_pairs = set()
    for e, ts in edge_tris.items():
        w = sorted({inst_of_tri[t] for t in ts if t in inst_of_tri})
        if len(w) != 2 or tuple(w) in seen_pairs:
            continue
        seen_pairs.add(tuple(w))
        A, B = instances[w[0]], instances[w[1]]
        d = np.array(B["cen"]) - np.array(A["cen"])
        horiz = math.hypot(d[0], d[2]) >= abs(d[1])
        if horiz:
            # common along-wall direction = the centroid delta; each side's u-sense w.r.t. it
            hd = np.array([d[0], d[2]])
            L = np.linalg.norm(hd)
            if L < 1e-6:
                continue
            hd /= L
            senses = []
            for inst in (A, B):
                own = np.array(inst["hdir"])
                sgn = 1.0 if float(own @ hd) >= 0 else -1.0
                senses.append(inst["u_corr"] * sgn)
            if abs(senses[0]) < 0.3 or abs(senses[1]) < 0.3:
                continue                                    # degenerate u on one side
            h_pairs.append(dict(a=A["tile"], b=B["tile"],
                                mirrored=bool(senses[0] * senses[1] < 0)))
        else:
            lo, hi = (A, B) if A["cen"][1] <= B["cen"][1] else (B, A)
            v_pairs.append(dict(below=lo["tile"], above=hi["tile"],
                                v_below=lo["v_corr"], v_above=hi["v_corr"]))

print(f"instances: {len(instances)}   horizontal pairs: {len(h_pairs)}   "
      f"vertical pairs: {len(v_pairs)}")

# ---- LAW 1: is v-orientation fixed per tile? ------------------------------------------------
by_tile = defaultdict(list)
for inst in instances:
    if abs(inst["v_corr"]) >= 0.3 and inst["yspan"] >= 1.0:
        by_tile[tuple(inst["tile"])].append(inst["v_corr"])
flip_rows = []
n_fixed = n_flippy = 0
for tile, cs in sorted(by_tile.items()):
    up = sum(1 for c in cs if c < 0)                        # atlas v DECREASES upward -> c<0 = "up"
    dn = len(cs) - up
    frac_min = min(up, dn) / len(cs)
    if len(cs) >= 5:
        if frac_min <= 0.1:
            n_fixed += 1
        else:
            n_flippy += 1
            flip_rows.append((tile, up, dn))
print(f"\nLAW 1 (v-orientation), tiles with >=5 oriented instances: "
      f"{n_fixed} FIXED (<=10% minority) vs {n_flippy} MIXED")
for tile, up, dn in flip_rows[:10]:
    print(f"   mixed: tile {tile}: v-up {up} / v-down {dn}")

# ---- LAW 2: is horizontal u-mirroring part of the language? ---------------------------------
n_mir = sum(1 for p in h_pairs if p["mirrored"])
same_tile = [p for p in h_pairs if p["a"] == p["b"]]
n_mir_same = sum(1 for p in same_tile if p["mirrored"])
print(f"\nLAW 2 (u-mirroring): {n_mir}/{len(h_pairs)} horizontal pairs mirrored "
      f"({(n_mir / len(h_pairs)) if h_pairs else 0:.1%}); same-tile pairs "
      f"{n_mir_same}/{len(same_tile)} mirrored")

# ---- LAW 3: vertical transitions ------------------------------------------------------------
vt = Counter((tuple(p["below"]), tuple(p["above"])) for p in v_pairs)
print(f"\nLAW 3 (vertical transitions): {len(vt)} distinct (below -> above) pairs; top 12:")
for (b, a), n in vt.most_common(12):
    print(f"   {b} -> {a}   x{n}")

OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(dict(instances=instances, h_pairs=h_pairs, v_pairs=v_pairs,
                               phase=[PU, PV]), indent=0))
print(f"\nartifacts -> {OUT}")
