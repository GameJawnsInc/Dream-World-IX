"""ISLANDS WITH BUILDINGS, question 3 (2026-10-09): does a building's island sink clean? An independent check of the
finished mesh, both discs.

Each plan (`transplant.sink_auto_plan`, the building going with its island) is applied to stock over the 3x3 blocks
round it -- every part a block carries -- and checked as sh_c6_welds.py checks the clusters: open edges of the new
tris (a crack, unless on the checked area's rim or facing an open-ocean block), T-junctions on them, near misses. Plus
LEFTOVERS: a kept tri of any part that is not water with a vertex above the waterline over the new water (a piece of
the building, its waterfall or its ground left standing over the sea). Renders stock and the result with the game's
textures (Object, falls and rivers drawn as flat colour), disc 1. Writes out/sh_b3_check.json, out/sh_b3_<x>_<z>.png.
Run (from C:\\gd\\Dream-World-IX):  py studies/terrain-malleability/land2sea/sh_b3_check.py [X Z ...]
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2] / "ff9mapkit"
sys.path.insert(0, str(KIT))
sys.path.insert(0, str(HERE))
import sh_q6_render as Q6  # noqa: E402

SITES = [(425.098, -1020.0), (553.065, -1127.103), (9.909, -22.582)]
FLOW_RGB = (210, 70, 60)


def k3(v):
    return (round(v[0][0], 4), round(v[0][1], 4), round(v[0][2], 4))


def area(t):
    (a, b, c) = [(v[0][0], v[0][2]) for v in t]
    return abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2.0


def check(at, disc):
    from ff9mapkit.world import discmirror as DM, transplant as TR
    real = DM._real_parts(disc, "0_1")
    plan, rep = TR.sink_auto_plan(at, disc=disc)
    blocks = sorted(plan)
    near = sorted({(b[0] + dx, b[1] + dy) for b in blocks for dx in (-1, 0, 1) for dy in (-1, 0, 1)} & set(real))
    before = {(b, p): TR.world_tris(*b, p, disc=disc) for b in near for p in sorted(real[b])}
    soup = {k: list(v) for k, v in before.items()}
    new = []
    for b, tws in plan.items():
        for tw in tws:
            if isinstance(tw, TR.DropTris):
                soup[(b, tw.part)] = [t for t in soup[(b, tw.part)] if tw._key_set(t) not in tw.keys]
            elif isinstance(tw, TR.EmitTris):
                em = tw.emit()
                soup[(b, tw.part)] += em
                new += em
            elif isinstance(tw, TR.RetopoTris):
                pass
    allt = [t for ts in soup.values() for t in ts]
    ec = Counter()
    for t in allt:
        ks = [k3(v) for v in t]
        for i in range(3):
            if ks[i] != ks[(i + 1) % 3]:
                ec[tuple(sorted((ks[i], ks[(i + 1) % 3])))] += 1
    lo_x, hi_x = 64.0 * min(b[0] for b in near), 64.0 * (max(b[0] for b in near) + 1)
    lo_z, hi_z = -64.0 * (max(b[1] for b in near) + 1), -64.0 * min(b[1] for b in near)
    open_edges = []
    for t in new:
        if area(t) < 1e-9:
            continue
        ks = [k3(v) for v in t]
        for i in range(3):
            e = tuple(sorted((ks[i], ks[(i + 1) % 3])))
            if ec[e] == 1:
                rim = all(abs(p[0] - lo_x) < 1e-3 or abs(p[0] - hi_x) < 1e-3 or abs(p[2] - lo_z) < 1e-3
                          or abs(p[2] - hi_z) < 1e-3 for p in e)
                mx, mz = (e[0][0] + e[1][0]) / 2.0, (e[0][2] + e[1][2]) / 2.0
                cx, cz = TR._plan_centroid(t)
                ox, oz = mx + (mx - cx) * 1e-3, mz + (mz - cz) * 1e-3
                prefab = (int(math.floor(ox / 64.0)), int(math.floor(-oz / 64.0))) not in real
                if not rim and not prefab:
                    open_edges.append(e)
    vcell = defaultdict(set)
    for t in allt:
        for v in t:
            vcell[(math.floor(v[0][0] / 4.0), math.floor(v[0][2] / 4.0))].add(k3(v))
    tj = []
    for t in new:
        if area(t) < 1e-9:
            continue
        for i in range(3):
            a, b = t[i][0], t[(i + 1) % 3][0]
            cells = {(math.floor(a[0] / 4.0) + dx, math.floor(a[2] / 4.0) + dz) for dx in (-1, 0, 1) for dz in (-1, 0, 1)}
            for c in cells:
                for q in vcell.get(c, ()):
                    if q in (k3(t[i]), k3(t[(i + 1) % 3])) or abs(q[1]) > 1e-6:
                        continue
                    if TR._seg_dist((q[0], q[2]), (a[0], a[2]), (b[0], b[2])) < 1e-5:
                        tj.append(q)
    newv = {k3(v) for t in new for v in t}
    near_miss = 0
    for qv in newv:
        c = (math.floor(qv[0] / 4.0), math.floor(qv[2] / 4.0))
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for w in vcell.get((c[0] + dx, c[1] + dz), ()):
                    if w != qv and abs(w[1] - qv[1]) < 1e-6 and 0 < math.hypot(w[0] - qv[0], w[2] - qv[2]) < 0.05:
                        near_miss += 1
    # leftovers: kept non-water vertices above the waterline over the new water
    ntile = defaultdict(list)
    for t in new:
        for ij in TR._tiles_touched(t):
            ntile[ij].append(t)
    left = Counter()
    for (b, p), ts in soup.items():
        if p in TR.SINK_WATER_PARTS:
            continue
        for t in ts:
            for v in t:
                if v[0][1] <= 1e-6:
                    continue
                q = (v[0][0], v[0][2])
                cells = {(math.floor((q[0] + d) / 4.0), math.floor((q[1] + e) / 4.0)) for d in (-1e-6, 1e-6)
                         for e in (-1e-6, 1e-6)}
                if any(TR._tri_has(u, q) for ij in cells for u in ntile.get(ij, ())):
                    left[p] += 1
    out = {"at": at, "disc": disc, "fill": rep.get("fill"), "building": rep.get("building"),
           "plug_u2": rep.get("plug_u2"), "entrance_tris": rep.get("entrance_tris"), "new_tris": len(new),
           "open_edges": len(open_edges), "open_first": open_edges[:2], "t_junctions": len(set(tj)),
           "t_first": sorted(set(tj))[:2], "near_miss_pairs": near_miss // 2, "leftovers": dict(left)}
    return out, before, soup, plan


def render(at, before, soup, plan):
    from ff9mapkit.world import render as R
    rs = R.RenderSite(cells=((0, 0),), disc=1)
    names = {"sea4": "Sea4", "sea5": "Sea5", "sea3": "Sea3", "sea1": "Sea1", "sea2": "Sea2", "beach1": "Beach1",
             "terrain": "Terrain", "object": "Object"}
    tex = {p: R.tex_for(n, rs) for p, n in names.items()}
    blocks = sorted(plan)
    box = (64.0 * min(b[0] for b in blocks) - 4, 64.0 * (max(b[0] for b in blocks) + 1) + 4,
           -64.0 * (max(b[1] for b in blocks) + 1) - 4, -64.0 * min(b[1] for b in blocks) + 4)
    panels = []
    for s in (before, soup):
        soups = defaultdict(list)
        flows = []
        for (b, p), ts in s.items():
            if p in Q6.ORDER:
                soups[p] += ts
            elif p not in TR_WATER:
                flows += ts
        img, _ = Q6.raster(soups, box, tex)
        _x, fb = Q6.raster({"object": flows}, box, {})
        img[fb.sum(2) > 0] = FLOW_RGB
        panels.append(img)
    H, W = panels[0].shape[:2]
    canvas = Image.new("RGB", (2 * W + 10, H), (255, 255, 255))
    for k, im in enumerate(panels):
        canvas.paste(Image.fromarray(im), (k * (W + 10), 0))
    scale = min(1.0, 2400 / canvas.size[0])
    if scale < 1:
        canvas = canvas.resize((int(canvas.size[0] * scale), int(canvas.size[1] * scale)))
    canvas.save(HERE / "out" / f"sh_b3_{int(at[0])}_{int(-at[1])}.png")


TR_WATER = ("sea1", "sea2", "sea3", "sea4", "sea5", "sea6", "sea4f")


def main():
    import ff9mapkit
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    a = [float(v) for v in sys.argv[1:]]
    sites = [(a[k], a[k + 1]) for k in range(0, len(a), 2)] or SITES
    res = {}
    for at in sites:
        for d in (1, 4):
            out, before, soup, plan = check(at, d)
            res[f"{at[0]},{at[1]} d{d}"] = out
            print(json.dumps(out, default=str), flush=True)
            if d == 1:
                render(at, before, soup, plan)
    (HERE / "out" / "sh_b3_check.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
