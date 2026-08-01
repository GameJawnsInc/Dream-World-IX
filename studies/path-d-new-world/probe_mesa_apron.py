"""APRON PROBE -- measure the (15,14) mesa's own ground apron before building the
apron-carry round (studies/path-d-new-world/APRON-CARRY-PREDICTION.md, freedoms 1-2).

Reports, per outward ring of donor ground tris from the mesa's ground-weld line:
tri count, outer-boundary y profile, topo classes -- plus donor lowland, the ring
count to flatness, outer-loop closure, block-border crossings, the (14,14)
continuation + its apron, and the foot-adjacent wall course's row histogram (the
BAND GATE's donor baseline).

Read-only. Regenerate: py -X utf8 probe_mesa_apron.py
"""
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from terrace_wall_strip import (kk, extract_wall, GRASS_TOPO, LOWLAND, BLOCK)   # noqa: F401

PLATEAU_T = {10, 11, 12}
TILE_U, TILE_V = 0.0625, 0.03125
PU, PV = json.loads((Path(__file__).resolve().parents[1] / "overworld-topography" / "out"
                     / "rock_tiles.json").read_text())["phase"]


def tile_row(uvs):
    return int(math.floor((min(q[1] for q in uvs) - PV) / TILE_V + 0.5))


def mesa_carry_set(W):
    topoD, tidD = W["topo"], W["tri_idx"]
    comp_count = Counter(W["comp_of"].values())
    root = comp_count.most_common(1)[0][0]
    mesa = {t for t, r in W["comp_of"].items() if r == root}
    ring1 = set()
    for e, ts in W["edge_tris"].items():
        if len(ts) != 2:
            continue
        w = [t for t in ts if t in mesa]
        p = [t for t in ts if topoD[t] in PLATEAU_T]
        if len(w) == 1 and len(p) == 1:
            ring1.add(p[0])
    padj = defaultdict(set)
    for e, ts in W["edge_tris"].items():
        pp = [t for t in ts if topoD[t] in PLATEAU_T]
        for i in range(len(pp)):
            for j in range(i + 1, len(pp)):
                padj[pp[i]].add(pp[j])
                padj[pp[j]].add(pp[i])
    plat = set(ring1)
    st = list(ring1)
    while st:
        t = st.pop()
        for t2 in padj[t]:
            if t2 not in plat:
                plat.add(t2)
                st.append(t2)
    return mesa | plat, mesa


W = extract_wall(15, 14)
V, U, topo, tid, ET = W["V"], W["U"], W["topo"], W["tri_idx"], W["edge_tris"]
carry, mesa = mesa_carry_set(W)
ground = {t for t in range(len(tid)) if t not in carry and topo[t] != 49
          and topo[t] not in PLATEAU_T}
print(f"donor blk (15,14): {len(carry)} carry tris ({len(mesa)} wall), "
      f"{len(ground)} non-carry ground tris; ground topo "
      f"{Counter(topo[t] for t in ground).most_common(6)}")

# ---- the ground-weld line + the band baseline -----------------------------------------------
weld_edges, weld_wall = [], set()
for e, ts in ET.items():
    w = [t for t in ts if t in carry]
    o = [t for t in ts if t in ground]
    if len(w) == 1 and o:
        weld_edges.append(e)
        if topo[w[0]] == 49:
            weld_wall.add(w[0])
wy = [p[1] for e in weld_edges for p in e]
rows = Counter(tile_row([U[i] for i in tid[t]]) for t in weld_wall)
print(f"weld line: {len(weld_edges)} edges, y {min(wy):.1f}..{max(wy):.1f} "
      f"(med {float(np.median(wy)):.1f})")
print(f"foot-adjacent WALL course rows (band baseline): {rows.most_common(6)} "
      f"-> row-10 share {rows.get(10, 0) / max(1, sum(rows.values())):.1%}")

# donor lowland: ground verts far from the mesa centroid
mc = np.mean([[V[i][0], V[i][2]] for t in mesa for i in tid[t]], axis=0)
far_y = [V[i][1] for t in ground for i in tid[t]
         if math.hypot(V[i][0] - mc[0], V[i][2] - mc[1]) > 40.0]
print(f"donor lowland (ground verts >40u out): med "
      f"{float(np.median(far_y)):.2f} p10 {float(np.percentile(far_y, 10)):.2f} "
      f"p90 {float(np.percentile(far_y, 90)):.2f} (bench LOWLAND {LOWLAND})")

# ---- apron rings ----------------------------------------------------------------------------
gadj = defaultdict(set)
for e, ts in ET.items():
    gg = [t for t in ts if t in ground]
    for i in range(len(gg)):
        for j in range(i + 1, len(gg)):
            gadj[gg[i]].add(gg[j])
            gadj[gg[j]].add(gg[i])
apron = set()
frontier = {t for e, ts in ET.items() if e in [tuple(x) for x in []] for t in ts}   # placeholder
frontier = set()
for e, ts in ET.items():
    w = [t for t in ts if t in carry]
    o = [t for t in ts if t in ground]
    if len(w) == 1 and o:
        frontier |= set(o)
ring_no = 0
ring_of = {}
while frontier and ring_no < 10:
    apron |= frontier
    for t in frontier:
        ring_of[t] = ring_no
    print(f"   ring {ring_no} topo: {Counter(topo[t] for t in frontier).most_common(5)}")
    # this ring's OUTER boundary verts: verts of the frontier not shared with carry/apron-interior
    out_edges = []
    for e, ts in ET.items():
        a = [t for t in ts if t in apron]
        rest = [t for t in ts if t not in apron and t not in carry]
        if len(a) == 1 and (rest or len(ts) == 1):
            out_edges.append((e, len(ts) == 1))
    oy = [p[1] for e, brd in out_edges for p in e]
    n_border = sum(1 for _, brd in out_edges if brd)
    deg = Counter()
    for e, _ in out_edges:
        deg[e[0]] += 1
        deg[e[1]] += 1
    open_v = sum(1 for d in deg.values() if d != 2)
    print(f"ring {ring_no}: +{len(frontier)} tris (apron {len(apron)}); outer boundary "
          f"{len(out_edges)} edges, y med {float(np.median(oy)):.2f} "
          f"p90 {float(np.percentile(oy, 90)):.2f} max {max(oy):.2f}; "
          f"block-border(open) edges {n_border}; non-degree-2 verts {open_v}")
    nxt = set()
    for t in frontier:
        for t2 in gadj[t]:
            if t2 not in apron:
                nxt.add(t2)
    frontier = nxt
    ring_no += 1

# ---- the west border + the (14,14) continuation ---------------------------------------------
border_v = sorted({kk(V[i]) for t in carry for i in tid[t] if abs(V[i][0]) < 1e-3})
print(f"\ncarry verts on the WEST block border (local x=0): {len(border_v)} "
      f"y {min(p[1] for p in border_v):.1f}..{max(p[1] for p in border_v):.1f}"
      if border_v else "\nno carry verts on the west border")
apron_border = Counter()
for t in apron:
    for i in tid[t]:
        x, z = V[i][0], V[i][2]
        if abs(x) < 1e-3:
            apron_border["W"] += 1
        if abs(x - BLOCK) < 1e-3:
            apron_border["E"] += 1
        if abs(z) < 1e-3:
            apron_border["N"] += 1
        if abs(z + BLOCK) < 1e-3:
            apron_border["S"] += 1
print(f"apron verts touching block borders: {dict(apron_border)}")

W2 = extract_wall(14, 14)
V2, U2, topo2, tid2 = W2["V"], W2["U"], W2["topo"], W2["tri_idx"]
# continuation: (14,14) wall tris sharing a WORLD-frame vert with the mesa's border verts
bset = {(round(p[0] + W["ox"], 3), round(p[1], 3), round(p[2] + W["oz"], 3)) for p in border_v}
cont = set()
for t in range(len(tid2)):
    if topo2[t] != 49:
        continue
    for i in tid2[t]:
        wp = (round(V2[i][0] + W2["ox"], 3), round(V2[i][1], 3), round(V2[i][2] + W2["oz"], 3))
        if wp in bset:
            cont.add(t)
            break
print(f"(14,14) wall continuation: {len(cont)} tris; rows "
      f"{Counter(tile_row([U2[i] for i in tid2[t]]) for t in cont).most_common(4)}")
if cont:
    cys = [V2[i][1] for t in cont for i in tid2[t]]
    print(f"   continuation y {min(cys):.1f}..{max(cys):.1f}")
    # its own ground adjacency (the continuation's apron seeds)
    ET2 = W2["edge_tris"]
    g2 = {t for t in range(len(tid2)) if topo2[t] != 49 and topo2[t] not in PLATEAU_T}
    seeds2 = set()
    for e, ts in ET2.items():
        w = [t for t in ts if t in cont]
        o = [t for t in ts if t in g2]
        if len(w) == 1 and o:
            seeds2 |= set(o)
    print(f"   (14,14) apron seeds adjacent to the continuation: {len(seeds2)} tris")

# ---- plan render: rings shaded, y-coded, borders --------------------------------------------
from PIL import Image, ImageDraw                            # noqa: E402

SCALE = 7
im = Image.new("RGB", (int(BLOCK) * SCALE + 40, int(BLOCK) * SCALE + 40), (18, 18, 22))
dr = ImageDraw.Draw(im)


def px(p):
    return (20 + p[0] * SCALE, 20 + (-p[2]) * SCALE)        # local frame; z negative going south


for t in carry:
    dr.polygon([px(V[i]) for i in tid[t]], fill=(70, 70, 78))
for t in apron:
    ys = np.mean([V[i][1] for i in tid[t]])
    heat = int(min(1.0, max(0.0, (ys - 3.2) / 4.0)) * 255)
    rn = ring_of.get(t, 9)
    base = (60 + heat // 2, 130 - rn * 8, 60) if topo[t] != 37 else (150, 90 + heat // 3, 40)
    dr.polygon([px(V[i]) for i in tid[t]], fill=base, outline=(40, 40, 40))
    if ys > 5.0 and ring_of.get(t, 0) >= 2:
        dr.polygon([px(V[i]) for i in tid[t]], outline=(255, 60, 60))
for e in weld_edges:
    dr.line([px(e[0]), px(e[1])], fill=(240, 240, 120), width=2)
dr.rectangle([20, 20, 20 + BLOCK * SCALE, 20 + BLOCK * SCALE], outline=(90, 90, 200))
dr.text((22, 4), "(15,14) apron: green=grass ring (darker=farther), orange=topo37, "
        "red outline=high tail (y>5 ring>=2), yellow=weld", fill=(220, 220, 220))
out_png = Path(__file__).with_name("out") / "mesa_apron_plan.png"
out_png.parent.mkdir(exist_ok=True)
im.save(out_png)
print(f"\nrender -> {out_png}")

import sys                                                   # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                     # noqa: E402
for cls in (0, 37, 42):
    n = X.decode_id if False else None
print("topo-37 semantic:", {k: v for k, v in
      (X.TOPOGRAPH_NAMES.items() if hasattr(X, "TOPOGRAPH_NAMES") else [])
      if k in (0, 37, 42, 49)} or "no names table on X")
