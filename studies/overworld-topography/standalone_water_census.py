"""THE STANDALONE WATER-FEATURE CENSUS -- can a SMALL self-contained water feature
(a stream/pond/short-falls) be carried onto a minted island WITHOUT dragging a mountain?

Roadmap item 5.5. The horseshoe (5-6,15-16) proved falls/river/riverjoint aux parts carry
as part of a BIG massif ensemble (THE ENSEMBLE CARRY). The open question was whether stock
holds a water feature whose COMPLETE ensemble (terrain channel + aux water parts + apertures
+ banks) closes naturally on ALL sides inside a carriable window -- with NO amputation stumps
(a river that flows in from nowhere is a stump; sources/sinks judged honestly).

METHOD (all offline, reads your own install; ~1 min):
  1. PART UNIVERSE   -- every worldmap sub-mesh part name, both discs (the water parts are
                        named sub-meshes: river/stream/riverjoint/falls).
  2. WATER BLOCKS    -- which blocks carry each water part + tri counts + terrain context
                        (rock% and the y-range that tells lowland from two-altitude-world).
  3. TERMINATION     -- weld ALL water parts map-wide into components; per component classify
                        its two flow-axis TIPS: SEA-anchored / MASSIF-anchored / OPEN. An OPEN
                        tip (far from rock AND sea) is the ONLY thing that could enable a
                        standalone lowland carry.
  4. HIDDEN WATER    -- rule out a pond baked into terrain topo (48/50/51) instead of a part;
                        identify topo-62 (the channel bank).

RESULT (disc 1, 2026-07-22): 6 water components, **ZERO OPEN tips**. Every water-feature
terminus is anchored to the SEA or to a MASSIF (mountain rock). No stock stream has a
self-contained open-lowland source -- every river rises in a mountain (geographically
correct). => CLOSED BY CENSUS: the lawful carriable unit for ANY water feature is the whole
massif ENSEMBLE (Daguerreo-style), never a standalone lowland stream. The ENSEMBLE LAW's
stream instance, proven with numbers.

The four stock water systems:
  Daguerreo (5-6,15-16)     falls/river/riverjoint, hanging bowl y15->26  -- ALREADY CARRIED
  Plateau-B (14,17),(15,17) highland river y26-28, both ends rock, area-14 field entrance
  Cluster-D (18-20,10-13)   plateau river -> falls -> valley stream, y0.4->26.4, mountain-bound
  Cluster-C (16,14),(16,15),(17,14)  the CLOSEST: a genuine lowland river-to-sea, but its
                            SOURCE is the massif foot (3.2u from rock) -- excluding the
                            mountain leaves an upstream stump.

Run from the repo root:  py studies/overworld-topography/standalone_water_census.py
"""
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X          # noqa: E402
from ff9mapkit.world import interior as IN        # noqa: E402

BLOCK = 64.0
DISC = 1
ROCK = set(IN.MOUNTAIN_ROCK_TOPOS)
WATER = ("stream", "river", "riverjoint", "falls")
SEAP = ("sea1", "sea2", "sea3", "beach1", "beach2")
kk = lambda p: (round(float(p[0]), 1), round(float(p[1]), 1), round(float(p[2]), 1))


def _part_blocks(disc):
    # anchor to the streamed 0_1 LOD under r<Y>/ so we count DISTINCT blocks, not the
    # duplicate container keys the bundle carries per asset.
    env = X._worldmap_env(disc)
    pat = re.compile(rf"worldmap/disc{disc}/0_1/r\d+/block\[(\d+)\]\[(\d+)\] ([a-z0-9]+)(?:\.asset)?$")
    per = defaultdict(set)
    for k in env.container:
        m = pat.search((k or "").lower())
        if m:
            bx, by, part = int(m.group(1)), int(m.group(2)), m.group(3)
            per[part].add((bx, by))
    names = Counter({p: len(bs) for p, bs in per.items()})
    return names, per


# ---- 1. PART UNIVERSE ----------------------------------------------------------------------------
print("1. PART UNIVERSE (distinct worldmap sub-mesh names):")
for disc in (1, 4):
    names, _ = _part_blocks(disc)
    water = {p: n for p, n in names.items() if p in WATER}
    print(f"   disc{disc}: water parts -> {water}   (all parts: {dict(names.most_common())})")

names, per = _part_blocks(DISC)

# ---- 2. WATER BLOCKS + terrain context -----------------------------------------------------------
print("\n2. WATER BLOCKS (disc 1) with terrain context:")
allw = set().union(*(per[p] for p in WATER))
for blk in sorted(allw):
    bx, by = blk
    parts = [p for p in WATER if blk in per[p]]
    bm = X.read_block(bx, by, disc=DISC, part="terrain")
    ids = X.block_mapids(bm)
    hist = Counter(X.decode_id(i)["topograph"] for i in ids)
    rock = sum(v for k, v in hist.items() if k in ROCK)
    tot = sum(hist.values())
    yr = []
    for p in parts:
        pm = X.read_block(bx, by, disc=DISC, part=p)
        yr += [v[1] for v in pm.verts]
    print(f"   {blk} parts={','.join(parts):<28} water-y[{min(yr):.1f},{max(yr):.1f}]  "
          f"rock={100 * rock // max(tot, 1)}%")

# ---- 3. TERMINATION CENSUS -----------------------------------------------------------------------
verts, edges, vinfo = set(), set(), {}
for part in WATER:
    for (bx, by) in per[part]:
        pm = X.read_block(bx, by, disc=DISC, part=part)
        off = np.array([BLOCK * bx, 0.0, -BLOCK * by])
        V = np.asarray(pm.verts, dtype=np.float64) + off
        for t in np.asarray(pm.flat_index, dtype=np.int64).reshape(-1, 3):
            ps = [kk(V[j]) for j in t]
            for p in ps:
                verts.add(p)
                vinfo.setdefault(p, set()).add(part)
            for a, b in ((0, 1), (1, 2), (2, 0)):
                edges.add(tuple(sorted((ps[a], ps[b]))))
adj = defaultdict(set)
for a, b in edges:
    adj[a].add(b)
    adj[b].add(a)
seen, comps = set(), []
for s in verts:
    if s in seen:
        continue
    comp, st = {s}, [s]
    while st:
        u = st.pop()
        for v in adj[u]:
            if v not in comp:
                comp.add(v)
                st.append(v)
    seen |= comp
    comps.append(comp)
comps.sort(key=len, reverse=True)


def _rock_centroids(blocks):
    pts = []
    for (bx, by) in blocks:
        try:
            bm = X.read_block(bx, by, disc=DISC, part="terrain")
        except Exception:
            continue
        off = np.array([BLOCK * bx, 0.0, -BLOCK * by])
        V = np.asarray(bm.verts, dtype=np.float64) + off
        idx = np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3)
        ids = X.block_mapids(bm)
        for ti, i in enumerate(idx):
            if X.decode_id(ids[ti])["topograph"] in ROCK:
                pts.append(V[i].mean(axis=0))
    return np.array(pts) if pts else np.zeros((0, 3))


def _sea_verts(blocks):
    pts = []
    for (bx, by) in blocks:
        for part in SEAP:
            try:
                pm = X.read_block(bx, by, disc=DISC, part=part)
            except Exception:
                continue
            off = np.array([BLOCK * bx, 0.0, -BLOCK * by])
            pts.append(np.asarray(pm.verts, dtype=np.float64) + off)
    return np.vstack(pts) if pts else np.zeros((0, 3))


def _classify(p, rocks, seas):
    dr = float(np.min(np.hypot(rocks[:, 0] - p[0], rocks[:, 2] - p[2]))) if len(rocks) else 1e9
    ds = float(np.min(np.hypot(seas[:, 0] - p[0], seas[:, 2] - p[2]))) if len(seas) else 1e9
    if ds < 8:
        return "SEA", dr, ds
    if dr < 8:
        return "MASSIF", dr, ds
    if dr > 15 and ds > 15:
        return "OPEN", dr, ds
    return "near", dr, ds


print("\n3. TERMINATION CENSUS (weld all water parts -> components -> classify tips):")
open_tips = 0
for ci, comp in enumerate(comps):
    P = np.array(list(comp))
    parts = sorted({pt for p in comp for pt in vinfo[p]})
    nb = set()
    for p in comp:
        bx, by = int(p[0] // BLOCK), int((-p[2]) // BLOCK)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nb.add((bx + dx, by + dy))
    rocks, seas = _rock_centroids(nb), _sea_verts(nb)
    c = P[:, [0, 2]].mean(axis=0)
    _, _, vt = np.linalg.svd(P[:, [0, 2]] - c)
    proj = (P[:, [0, 2]] - c) @ vt[0]
    order = proj.argsort()
    kA, drA, dsA = _classify(P[order[0]], rocks, seas)
    kB, drB, dsB = _classify(P[order[-1]], rocks, seas)
    open_tips += (kA == "OPEN") + (kB == "OPEN")
    blks = sorted({(int(p[0] // BLOCK), int((-p[2]) // BLOCK)) for p in comp})
    print(f"   comp{ci} {len(comp):>3}v {','.join(parts):<26} y[{P[:, 1].min():.1f},{P[:, 1].max():.1f}] "
          f"A:{kA}(r{drA:.0f}/s{dsA:.0f}) B:{kB}(r{drB:.0f}/s{dsB:.0f})  {blks}")
print(f"\n   OPEN tips (self-contained lowland termini, far from rock AND sea): {open_tips}")

# ---- 4. HIDDEN WATER -----------------------------------------------------------------------------
WT = {48: "river", 50: "falls", 51: "stream"}
terr_water = Counter()
topo62_blocks = Counter()
for (bx, by) in X.list_blocks(disc=DISC):
    bm = X.read_block(bx, by, disc=DISC, part="terrain")
    ids = X.block_mapids(bm)
    for i in ids:
        tp = X.decode_id(i)["topograph"]
        if tp in WT:
            terr_water[(bx, by)] += 1
        if tp == 62:
            topo62_blocks[(bx, by)] += 1
print(f"\n4. HIDDEN WATER: terrain-baked water-topo tris (48/50/51) map-wide = "
      f"{sum(terr_water.values())} on {dict(terr_water)} (channel markers, no ponds).")
near = sum(1 for b in topo62_blocks
           if any(abs(b[0] - w[0]) <= 1 and abs(b[1] - w[1]) <= 1 for w in allw))
print(f"   topo-62 (channel bank): {sum(topo62_blocks.values())} tris on {len(topo62_blocks)} "
      f"blocks, {near}/{len(topo62_blocks)} within 1 block of a water part => it IS the channel.")

print("\n=> VERDICT: CLOSED BY CENSUS. Zero open lowland water termini. Every stock water\n"
      "   feature rises in a mountain (or runs sea-to-sea via a massif); the lawful carriable\n"
      "   unit is the whole massif ENSEMBLE, never a standalone stream. Do not force a build.")
