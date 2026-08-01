"""APRON TILE PROBE -- what grass art does the donor apron actually wear, vs the
bench's own L3 family? (The playtest named 'weird brown tiles' on the collar.)"""
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from terrace_wall_strip import kk, extract_wall, GRASS_TOPO                     # noqa: F401

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world.atlas import load_atlas                                    # noqa: E402

PLATEAU_T = {10, 11, 12}
TILE_U, TILE_V = 0.0625, 0.03125

atlas = np.asarray(load_atlas("terrain").convert("RGB"), dtype=float)
AH, AW = atlas.shape[:2]

blks = [(15, 14), (14, 14), (16, 14), (15, 13), (15, 15)]
soup = []
for (bx, by) in blks:
    W = extract_wall(bx, by)
    for lt, idx in enumerate(W["tri_idx"]):
        soup.append(dict(
            w=[(W["V"][i][0] + W["ox"], W["V"][i][1], W["V"][i][2] + W["oz"]) for i in idx],
            uv=[tuple(W["U"][i]) for i in idx], topo=W["topo"][lt]))
ET = defaultdict(list)
for si, t in enumerate(soup):
    ps = [kk(p) for p in t["w"]]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        ET[tuple(sorted((ps[a], ps[b])))].append(si)

# the mesa carry set (largest crest-seeded comp in (15,14)) -- condensed
crest49 = set()
for e, ts in ET.items():
    if len(ts) == 2:
        pair = {soup[ts[0]]["topo"], soup[ts[1]]["topo"]}
        if 49 in pair and pair & PLATEAU_T:
            crest49.add(ts[0] if soup[ts[0]]["topo"] == 49 else ts[1])
adj49 = defaultdict(set)
for e, ts in ET.items():
    r = [t for t in ts if soup[t]["topo"] == 49]
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
sizes = Counter(comp_of.values())
root = sizes.most_common(1)[0][0]
carry = {t for t, r in comp_of.items() if r == root}
weld = set()
grass_s = {si for si, t in enumerate(soup) if t["topo"] in GRASS_TOPO}
seeds = set()
for e, ts in ET.items():
    w = [t for t in ts if t in carry]
    o = [t for t in ts if t in grass_s]
    if len(w) == 1 and o:
        seeds |= set(o)
        weld.update(e)
warr = np.array([[p[0], p[2]] for p in weld])
gadj = defaultdict(set)
for e, ts in ET.items():
    gg = [t for t in ts if t in grass_s]
    for i in range(len(gg)):
        for j in range(i + 1, len(gg)):
            gadj[gg[i]].add(gg[j])
            gadj[gg[j]].add(gg[i])


def ok(si):
    return min(float(np.min(np.hypot(warr[:, 0] - p[0], warr[:, 1] - p[2])))
               for p in soup[si]["w"]) <= 6.0


apron = set()
fr = {t for t in seeds if ok(t)}
while fr:
    apron |= fr
    fr = {t2 for t in fr for t2 in gadj[t] if t2 not in apron and ok(t2)}

cells = Counter()
browns = 0
for t in apron:
    us = [q[0] for q in soup[t]["uv"]]
    vs = [q[1] for q in soup[t]["uv"]]
    cell = (int(min(us) / TILE_U), int(min(vs) / TILE_V))
    cells[cell] += 1
    x0, x1 = int(min(us) * AW), int(max(us) * AW)
    y0, y1 = int(min(vs) * AH), int(max(vs) * AH)
    crop = atlas[max(0, y0):min(AH, y1 + 1), max(0, x0):min(AW, x1 + 1)]
    if crop.size:
        r, g, b = crop.reshape(-1, 3).mean(axis=0)
        if r > g * 0.92:                                    # green grass has g >> r
            browns += 1
            cells[("BROWN", cell)] += 0                     # marker only
print(f"apron: {len(apron)} tris; {browns} read BROWN-ish (r > 0.92*g)")
print(f"tile cells used: {cells.most_common(12)}")

# ---- THE SLOPE-UV LAW: does stock grass uv track PLAN or SURFACE distance? ------------------
flat_r, steep_r = [], []                                    # tiles per unit (plan, surf) pairs
for t in apron:
    ws, uvs = soup[t]["w"], soup[t]["uv"]
    a = np.array(ws[1]) - np.array(ws[0])
    b = np.array(ws[2]) - np.array(ws[0])
    n = np.cross(a, b)
    L = np.linalg.norm(n)
    if L < 1e-9:
        continue
    slope = math.degrees(math.acos(min(1.0, abs(n[1]) / L)))
    for i, j in ((0, 1), (1, 2), (2, 0)):
        plan = math.hypot(ws[j][0] - ws[i][0], ws[j][2] - ws[i][2])
        surf = math.dist(ws[i], ws[j])
        duv = math.hypot((uvs[j][0] - uvs[i][0]) / TILE_U,
                         (uvs[j][1] - uvs[i][1]) / TILE_V)
        if plan < 0.5 or duv < 1e-6:
            continue
        (steep_r if slope > 18.0 else flat_r).append((duv / plan * 4.0, duv / surf * 4.0))
for name, rows in (("flat(<18deg)", flat_r), ("steep(>18deg)", steep_r)):
    if rows:
        pp = [r[0] for r in rows]
        ss = [r[1] for r in rows]
        print(f"{name}: n={len(rows)}  tiles/4u-PLAN med {np.median(pp):.3f} "
              f"(p25 {np.percentile(pp,25):.3f} p75 {np.percentile(pp,75):.3f})  "
              f"tiles/4u-SURF med {np.median(ss):.3f} "
              f"(p25 {np.percentile(ss,25):.3f} p75 {np.percentile(ss,75):.3f})")
