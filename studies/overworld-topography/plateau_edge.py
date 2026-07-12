"""THE PLATEAU-EDGE ANATOMY STUDY -- the 27u rim onto topo-49 walls, disc 1.

The interior sibling of the coast cliff-lip laws. Questions it answers, per crest edge /
wall component across every disc-1 block with plateau grass (topo 10/11/12/13):

1. CREST anatomy -- where plateau grass meets rock 49: crest heights, the grass-rock
   dihedral (is the coastal ~66-deg sharp crease the interior language too?), the grass
   roll-in slope, and the grass-side V at the crest (the coastal LIP-ROW pins grass to
   texel row 0.893 -- do interior crests reuse it?).
2. WALL profile -- from the crest down: total drop, faces stacked per descent (single
   curtain vs terraced), base landing (what topo the wall foot welds to; the coastal
   FREE-BASE law has no interior analog -- interior bases must land somewhere).
3. THE MURAL-VS-TILE VERDICT -- the mintability question. Coastal walls speak a tile
   language (rock strip U 0.699-0.947 x V 0.893-0.923, V-as-corner-role, column
   quantization). The BAKED-TERRAIN LAW says highland 49 is often hand-painted MURALS
   (92-100% UV-unique, NO tile language). Which do PLATEAU-EDGE walls speak? Measured:
   per-wall UV-rect repetition (tile evidence) + coastal-strip-band membership.
4. PASSES -- where foot-legal land threads the 10-26u terrace gap (topo + location
   inventory: how the game itself connects the two altitude worlds).

Artifacts -> out/plateau_edge.json + printed tables. Regenerate: py plateau_edge.py
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
SHELF = {13}
FOOT = set(range(0, 8)) | {10, 11, 12, 13} | set(range(16, 24)) | {27, 28, 30, 31} | \
    set(range(32, 39)) | {41, 42, 45, 46, 52}
ROCK_U = (0.699, 0.947)
ROCK_V = (0.893, 0.923)
OUT = Path(__file__).with_name("out") / "plateau_edge.json"
kk = lambda v: (round(v[0], 3), round(v[1], 3), round(v[2], 3))

blocks = X.list_blocks(disc=1)
crest_rows = []                                            # per crest edge
wall_rows = []                                             # per wall descent component
pass_rows = []                                             # foot-legal gap-threaders
mural_rows = []                                            # per block: wall-49 uv stats

for (bx, by) in blocks:
    try:
        bm = X.read_block(bx, by, disc=1)
    except Exception:
        continue
    V = bm.verts
    U = bm.uvs
    T = bm.tangents
    ntri = len(bm.flat_index) // 3
    tri_idx = [bm.flat_index[3*t:3*t+3] for t in range(ntri)]
    topo = [X.decode_id(int(round(T[idx[0]][0])))["topograph"] for idx in tri_idx]
    if not any(t in PLATEAU for t in topo):
        continue

    # edge map: rounded vert-pair -> [(tri, corner pair)]
    edge_tris = defaultdict(list)
    for t, idx in enumerate(tri_idx):
        for a, b in ((0, 1), (1, 2), (2, 0)):
            e = tuple(sorted((kk(V[idx[a]]), kk(V[idx[b]]))))
            edge_tris[e].append(t)

    def tri_normal(t):
        a, b, c = (np.asarray(V[i], dtype=float) for i in tri_idx[t])
        n = np.cross(b - a, c - a)
        L = np.linalg.norm(n) or 1.0
        return n / L

    # ---- 1. crest edges: plateau grass | rock 49 ----------------------------------------
    crest_edges = []
    for e, ts in edge_tris.items():
        if len(ts) != 2:
            continue
        t1, t2 = ts
        pair = {topo[t1], topo[t2]}
        if 49 in pair and pair & PLATEAU:
            g = t1 if topo[t1] in PLATEAU else t2
            r = t2 if g == t1 else t1
            crest_edges.append((e, g, r))
    for (e, g, r) in crest_edges:
        cy = (e[0][1] + e[1][1]) / 2
        ng, nr = tri_normal(g), tri_normal(r)
        dih = math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(ng, nr))))))
        slope_g = math.degrees(math.acos(min(1.0, abs(float(ng[1])))))
        slope_r = math.degrees(math.acos(min(1.0, abs(float(nr[1])))))
        # grass V at the crest verts (lip-row test)
        gvs = [U[i][1] for i in tri_idx[g] if kk(V[i]) in (e[0], e[1])]
        # rock V at the crest verts (corner-role test)
        rvs = [U[i][1] for i in tri_idx[r] if kk(V[i]) in (e[0], e[1])]
        crest_rows.append(dict(blk=[bx, by], y=round(cy, 1), dih=round(dih, 1),
                               slope_g=round(slope_g, 1), slope_r=round(slope_r, 1),
                               g_v=[round(v, 4) for v in gvs], r_v=[round(v, 4) for v in rvs]))

    # ---- 2. wall descent components (49 tris connected below crests) ---------------------
    crest_49 = {r for (_, _, r) in crest_edges}
    adj49 = defaultdict(set)
    for e, ts in edge_tris.items():
        r49 = [t for t in ts if topo[t] == 49]
        for i in range(len(r49)):
            for j in range(i + 1, len(r49)):
                adj49[r49[i]].add(r49[j])
                adj49[r49[j]].add(r49[i])
    seen = set()
    for start in crest_49:
        if start in seen:
            continue
        comp = {start}
        stack = [start]
        while stack:
            t = stack.pop()
            for t2 in adj49[t]:
                if t2 not in comp:
                    comp.add(t2)
                    stack.append(t2)
        seen |= comp
        ys = [V[i][1] for t in comp for i in tri_idx[t]]
        # base partners: non-49 tris sharing an edge with the component's lowest tris
        base_partners = Counter()
        base_v = []
        for t in comp:
            for a, b in ((0, 1), (1, 2), (2, 0)):
                e = tuple(sorted((kk(V[tri_idx[t][a]]), kk(V[tri_idx[t][b]]))))
                for t2 in edge_tris[e]:
                    if topo[t2] != 49 and (e[0][1] + e[1][1]) / 2 < min(ys) + 3.0:
                        base_partners[topo[t2]] += 1
                        base_v += [U[i][1] for i in tri_idx[t] if kk(V[i]) in (e[0], e[1])]
        # stacked faces: max per-tri rise + the descent ladder count (crest y -> base y)
        rises = [max(V[i][1] for i in tri_idx[t]) - min(V[i][1] for i in tri_idx[t]) for t in comp]
        wall_rows.append(dict(blk=[bx, by], ntris=len(comp),
                              top=round(max(ys), 1), base=round(min(ys), 1),
                              drop=round(max(ys) - min(ys), 1),
                              max_face_rise=round(max(rises), 1),
                              med_face_rise=round(float(np.median(rises)), 1),
                              base_topos=dict(base_partners),
                              base_v=[round(v, 4) for v in base_v[:6]]))
        # mural-vs-tile: uv-rect repetition within the component
        rects = Counter()
        for t in comp:
            us = [U[i][0] for i in tri_idx[t]]
            vs = [U[i][1] for i in tri_idx[t]]
            rects[(round(min(us), 3), round(min(vs), 3), round(max(us), 3), round(max(vs), 3))] += 1
        uniq = sum(1 for c in rects.values() if c == 1)
        in_strip = sum(1 for t in comp
                       if all(ROCK_U[0] - 0.01 <= U[i][0] <= ROCK_U[1] + 0.01 and
                              ROCK_V[0] - 0.012 <= U[i][1] <= ROCK_V[1] + 0.012
                              for i in tri_idx[t]))
        mural_rows.append(dict(blk=[bx, by], ntris=len(comp),
                               uv_rects=len(rects), unique_rects=uniq,
                               uniq_frac=round(uniq / max(1, len(rects)), 2),
                               in_coastal_strip=in_strip,
                               strip_frac=round(in_strip / len(comp), 2)))

    # ---- 4. passes: foot-legal tris threading the 10-26u gap ------------------------------
    for t in range(ntri):
        if topo[t] not in FOOT:
            continue
        cy = sum(V[i][1] for i in tri_idx[t]) / 3
        if 10.0 <= cy <= 26.0:
            cx = sum(V[i][0] for i in tri_idx[t]) / 3 + 64 * bx
            cz = sum(V[i][2] for i in tri_idx[t]) / 3 - 64 * by
            pass_rows.append((topo[t], bx, by, round(cx), round(cz), round(cy, 1)))

# ---- report ---------------------------------------------------------------------------------
print(f"crest edges (plateau|49): {len(crest_rows)} across "
      f"{len({tuple(r['blk']) for r in crest_rows})} blocks")
if crest_rows:
    dihs = np.array([r["dih"] for r in crest_rows])
    sg = np.array([r["slope_g"] for r in crest_rows])
    ys = np.array([r["y"] for r in crest_rows])
    print(f"  crest y: p10={np.percentile(ys,10):.1f} med={np.median(ys):.1f} "
          f"p90={np.percentile(ys,90):.1f}")
    print(f"  dihedral grass-rock: med={np.median(dihs):.0f} p10={np.percentile(dihs,10):.0f} "
          f"p90={np.percentile(dihs,90):.0f}  (coastal crease ~66)")
    print(f"  grass roll-in slope: med={np.median(sg):.1f} p90={np.percentile(sg,90):.1f} "
          f"(coastal ~9)")
    gv = np.array([v for r in crest_rows for v in r["g_v"]])
    print(f"  grass crest V: med={np.median(gv):.4f} p10={np.percentile(gv,10):.4f} "
          f"p90={np.percentile(gv,90):.4f}  (coastal lip row 0.893)")
    rv = np.array([v for r in crest_rows for v in r["r_v"]])
    print(f"  rock crest V: med={np.median(rv):.4f}  (coastal crest role 0.8926)")

print(f"\nwall components below crests: {len(wall_rows)}")
if wall_rows:
    drops = np.array([w["drop"] for w in wall_rows])
    print(f"  drop: med={np.median(drops):.1f} p90={np.percentile(drops,90):.1f} "
          f"max={drops.max():.1f}")
    mfr = np.array([w["max_face_rise"] for w in wall_rows])
    print(f"  max face rise per wall: med={np.median(mfr):.1f} p90={np.percentile(mfr,90):.1f}")
    base_topo_all = Counter()
    for w in wall_rows:
        base_topo_all.update(w["base_topos"])
    print(f"  base landing topos: {dict(base_topo_all.most_common(8))}")
    bv = np.array([v for w in wall_rows for v in w["base_v"]])
    if len(bv):
        print(f"  rock base V: med={np.median(bv):.4f}  (coastal base role 0.9229)")

print(f"\nMURAL-vs-TILE verdict over {len(mural_rows)} plateau-wall components:")
if mural_rows:
    uf = np.array([m["uniq_frac"] for m in mural_rows])
    sf = np.array([m["strip_frac"] for m in mural_rows])
    print(f"  UV-rect unique fraction: med={np.median(uf):.2f} p10={np.percentile(uf,10):.2f} "
          f"(>=0.9 = mural; coastal tiles repeat)")
    print(f"  coastal-strip-band membership: med={np.median(sf):.2f} "
          f"frac of components >50% in-strip: {(sf > 0.5).mean():.2f}")
    for m in sorted(mural_rows, key=lambda m: -m["ntris"])[:10]:
        print(f"   blk {m['blk']} ntris={m['ntris']} uniq={m['uniq_frac']} strip={m['strip_frac']}")

pc = Counter((t, ) for (t, *_r) in pass_rows)
print(f"\nfoot-legal gap-threaders (y 10-26): {len(pass_rows)} tris; by topo: "
      f"{dict(Counter(t for (t, *_r) in pass_rows).most_common(10))}")
locs = sorted({(bxx, byy) for (_t, bxx, byy, *_r) in pass_rows})
print(f"  blocks with passes: {locs}")

OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(dict(crests=crest_rows, walls=wall_rows, murals=mural_rows,
                               passes=pass_rows), indent=1))
print(f"\nartifacts -> {OUT}")
