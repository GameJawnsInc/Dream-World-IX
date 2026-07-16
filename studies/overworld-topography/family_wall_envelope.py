"""FAMILY WALL ENVELOPES -- how tall do real walls get, per ground family?

The canyon island B playtest: "I don't recall any real canyon tiles with cliffs this
high". The ground-families census measured each family's wall ATLAS BAND (topo-58 tris
edge-adjacent to the family), but never its HEIGHT envelope -- and the plateau-edge
study proved the Forgotten's tall interior walls are a COURSED 128px tile language
(one tile per ~4.7u course), not a single stretched band. If real red-band/icy-band
walls only dress SHORT faces, the retile stretches one band over the donor's ~5.5u
sea cliffs = off-language.

Per family (grass control / desert / snow / canyon): every terrain tri whose uvs sit
in the family's wall band ->
  * per-tri y-span histogram (p50/p90/max) + the tallest single FACE (welded column)
  * v-structure: distinct v-levels per wall component (1 band-row vs stacked courses)
  * coastal vs interior (any vert at/below y~0.05 = reaches the waterline)
Compare against the (10,17) island-B donor's wall faces (what the retile stretched).

Run from the repo root:  py studies/overworld-topography/family_wall_envelope.py
"""
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import grassland as G                  # noqa: E402

ROCK_U = (0.699, 0.947)
ROCK_V = (0.893, 0.923)
EPS = 0.006
FAMS = {"grass": (0,), "desert": (17, 16, 19, 20), "snow": (27, 28), "canyon": (45, 46)}


def band(fam):
    g = G.GROUNDS[fam]
    return (ROCK_U[0] + g["wall_du"], ROCK_V[0] + g["wall_dv"],
            ROCK_U[1] + g["wall_du"], ROCK_V[1] + g["wall_dv"])


def in_band(uv, b):
    return b[0] - EPS <= uv[0] <= b[2] + EPS and b[1] - EPS <= uv[1] <= b[3] + EPS


def block_tris(bx, by):
    try:
        bm = X.read_block(bx, by, disc=1, part="terrain")
    except ValueError:
        return []
    out = []
    for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
        out.append(dict(
            w=[(bm.verts[j][0] + 64.0 * bx, bm.verts[j][1], bm.verts[j][2] - 64.0 * by)
               for j in tri],
            uv=[(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri],
            topo=X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]))
    return out


def pct(vals, q):
    if not vals:
        return 0.0
    s = sorted(vals)
    return s[min(len(s) - 1, int(q * len(s)))]


def wall_stats(name, wall_tris):
    """Per-tri spans + welded-component faces + v-structure."""
    if not wall_tris:
        print(f"   {name}: NO wall tris found")
        return
    spans = [max(p[1] for p in t["w"]) - min(p[1] for p in t["w"]) for t in wall_tris]
    kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))
    # union-find over shared verts -> connected wall faces
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for ti, t in enumerate(wall_tris):
        ks = [("v", kk(p)) for p in t["w"]]
        r0 = find(("t", ti))
        for k in ks:
            parent[find(k)] = r0
    comps = defaultdict(list)
    for ti, t in enumerate(wall_tris):
        comps[find(("t", ti))].append(ti)
    face_h, face_vlevels = [], []
    for tl in comps.values():
        ys = [p[1] for ti in tl for p in wall_tris[ti]["w"]]
        vs = [uv[1] for ti in tl for uv in wall_tris[ti]["uv"]]
        face_h.append(max(ys) - min(ys))
        lv = sorted(set(round(v, 3) for v in vs))
        merged = 1
        for a, b in zip(lv, lv[1:]):
            if b - a > 0.008:                                # > band jitter = a new course row
                merged += 1
        face_vlevels.append(merged)
    coastal = sum(1 for tl in comps.values()
                  if min(p[1] for ti in tl for p in wall_tris[ti]["w"]) < 0.05)
    print(f"   {name}: {len(wall_tris)} wall tris in {len(comps)} faces; "
          f"tri y-span p50 {pct(spans,.5):.2f} p90 {pct(spans,.9):.2f} max {max(spans):.2f}; "
          f"FACE height p50 {pct(face_h,.5):.2f} p90 {pct(face_h,.9):.2f} "
          f"max {max(face_h):.2f}; v-rows/face {Counter(face_vlevels).most_common(4)}; "
          f"coastal faces {coastal}/{len(comps)}")
    return dict(n=len(wall_tris), faces=len(comps), span_p90=pct(spans, .9),
                face_max=max(face_h), face_p90=pct(face_h, .9))


# map census: specimen blocks per family (most family-ground tris)
census = {}
for bx in range(24):
    for by in range(20):
        tris = block_tris(bx, by)
        if tris:
            census[(bx, by)] = tris

for fam, topos in FAMS.items():
    b = band(fam)
    counts = {blk: sum(1 for t in tl if t["topo"] in topos) for blk, tl in census.items()}
    spec = [blk for blk, n in sorted(counts.items(), key=lambda kv: -kv[1]) if n >= 30][:8]
    print(f"\n== {fam}: band u[{b[0]:.3f},{b[2]:.3f}] v[{b[1]:.3f},{b[3]:.3f}]; "
          f"specimens {spec}")
    wall, other_band_uv = [], []
    for blk in spec:
        for t in census[blk]:
            if all(in_band(uv, b) for uv in t["uv"]):
                wall.append(t)
    wall_stats(fam, wall)
    # where else does family ground meet a DROP without this band? (tall edges dressed
    # by ANOTHER language -- e.g. the coursed mesa tiles)
    steep = [t for blk in spec for t in census[blk]
             if t["topo"] in topos or (
                 max(p[1] for p in t["w"]) - min(p[1] for p in t["w"]) > 2.0
                 and not all(in_band(uv, b) for uv in t["uv"]))]
    tall_other = [t for t in steep if t["topo"] not in topos
                  and max(p[1] for p in t["w"]) - min(p[1] for p in t["w"]) > 2.0]
    if tall_other:
        uvb = [uv for t in tall_other for uv in t["uv"]]
        tp = Counter(t["topo"] for t in tall_other)
        print(f"   tall (>2u) NON-band steep tris on the same blocks: {len(tall_other)} "
              f"(topos {dict(tp.most_common(5))}; uv bbox "
              f"[{min(u for u,_ in uvb):.3f},{min(v for _,v in uvb):.3f},"
              f"{max(u for u,_ in uvb):.3f},{max(v for _,v in uvb):.3f}])")

# the donor's walls, for comparison
print(f"\n== the (10,17)+(10,18) island-B donor (what the retile stretched)")
bgr = band("grass")
dwall = [t for blk in ((10, 17), (10, 18)) for t in census.get(blk, [])
         if all(in_band(uv, bgr) for uv in t["uv"])]
wall_stats("island-B walls", dwall)
