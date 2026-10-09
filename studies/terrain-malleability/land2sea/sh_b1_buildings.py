"""ISLANDS WITH BUILDINGS, question 1 (2026-10-09): what stands on the islands the sink refuses for a building?

The census (sh_c5) refuses 7 islands because an Object tri welds to the island's ground. For each: the island's land
(terrain + beach1, traced across block borders), every Object component (Object tris joined by shared vertices) in the
3x3 blocks round it that welds to the island or lies over its footprint, and for each component: its tris, plan area,
height, IDALL classes (topograph / event / area), what else it welds to (other land, water, falls/river/stream), and
how much of it lies over the island. The island's holes (inner boundary cycles of its land) and whether an Object
plugs each; entrance tris on the island and the Object; falls/river tris on the island; the nearest navipos marker;
disc 4's copy (land and Object tri sets, kept or not). Renders stock with the game's textures and the Object outlined.
Writes out/sh_b1_buildings.json and out/sh_b1_<x>_<z>.png.
Run (from C:\\gd\\Dream-World-IX):  py studies/terrain-malleability/land2sea/sh_b1_buildings.py
"""
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2] / "ff9mapkit"
sys.path.insert(0, str(KIT))
sys.path.insert(0, str(HERE))
import sh_q6_render as Q6  # noqa: E402

SITES = [(425.098, -1020.0), (553.065, -1127.103), (9.909, -22.582), (325.897, -238.419), (1260.026, -722.982),
         (326.902, -249.447), (380.646, -1023.332)]
LAND = ("terrain", "beach1")
WATER = ("sea1", "sea2", "sea3", "sea5", "sea4", "sea6", "sea4f")
FLOW = ("falls", "river", "stream", "riverjoint")


def k3(v):
    return (round(v[0][0], 4), round(v[0][1], 4), round(v[0][2], 4))


def area2(t):
    return 0.5 * abs((t[1][0][0] - t[0][0][0]) * (t[2][0][2] - t[0][0][2])
                     - (t[2][0][0] - t[0][0][0]) * (t[1][0][2] - t[0][0][2]))


def ida(t):
    from ff9mapkit.world.extract import decode_id
    return decode_id(int(round(t[0][3][0])))


def site(at, disc=1):
    from ff9mapkit.world import discmirror as DM, locate as LO, meshedit as ME, transplant as TR
    real = DM._real_parts(disc, "0_1")
    home = (int(math.floor(at[0] / 64.0)), int(math.floor(-at[1] / 64.0)))
    cache = {}

    def tris(b, p):
        if (b, p) not in cache:
            cache[(b, p)] = TR.world_tris(*b, p, disc=disc) if p in real.get(b, ()) else []
        return cache[(b, p)]
    # the island: the land component under the point, traced until it closes
    blocks = {home}
    while True:
        land_all = [t for b in sorted(blocks) for p in LAND for t in tris(b, p)]
        island = next((c for c in ME.vertex_components(land_all) if any(TR._tri_has(t, at) for t in c)), None)
        if island is None:
            return {"at": at, "disc": disc, "island": None}
        grow = {(int(math.floor(v[0][0] / 64.0 + d)), int(math.floor(-v[0][2] / 64.0 + e)))
                for t in island for v in t for d in (-1e-6, 1e-6) for e in (-1e-6, 1e-6)} & set(real)
        if grow <= blocks:
            break
        blocks |= grow
    near = sorted({(b[0] + dx, b[1] + dy) for b in blocks for dx in (-1, 0, 1) for dy in (-1, 0, 1)} & set(real))
    iid = {id(t) for t in island}
    ikeys = {k3(v) for t in island for v in t}
    keys_of = {}
    for b in near:
        for p in real[b]:
            if p == "object":
                continue
            for t in tris(b, p):
                if id(t) in iid:
                    continue
                for v in t:
                    keys_of.setdefault(k3(v), set()).add(p)
    other_land = {k for k, ps in keys_of.items() if ps & set(LAND)}

    def over_island(q):
        return any(TR._tri_has(t, q) for t in island)
    xs = [v[0][0] for t in island for v in t]
    zs = [v[0][2] for t in island for v in t]
    ibox = (min(xs), max(xs), min(zs), max(zs))
    objs = [(b, t) for b in near for t in tris(b, "object")]
    comps = ME.vertex_components([t for _b, t in objs])
    oblock = {id(t): b for b, t in objs}
    rows = []
    for c in comps:
        ck = {k3(v) for t in c for v in t}
        weld_island = len(ck & ikeys)
        cx = [v[0][0] for t in c for v in t]
        cz = [v[0][2] for t in c for v in t]
        inbox = not (max(cx) < ibox[0] - 4 or min(cx) > ibox[1] + 4 or max(cz) < ibox[2] - 4 or min(cz) > ibox[3] + 4)
        if not weld_island and not inbox:
            continue
        cents = [TR._plan_centroid(t) for t in c]
        a = [area2(t) for t in c]
        over = sum(ai for ci, ai in zip(cents, a) if over_island(ci))
        if not weld_island and over == 0 and not any(over_island((v[0][0], v[0][2])) for t in c for v in t):
            # near the island but not on it: report only that it is there
            rows.append({"near_only": True, "tris": len(c), "bbox": [round(min(cx), 1), round(max(cx), 1),
                                                                      round(min(cz), 1), round(max(cz), 1)]})
            continue
        welds = Counter()
        for k in ck:
            for p in keys_of.get(k, ()):
                welds[p] += 1
        rows.append({
            "tris": len(c), "blocks": sorted({oblock[id(t)] for t in c}),
            "bbox": [round(min(cx), 1), round(max(cx), 1), round(min(cz), 1), round(max(cz), 1)],
            "y": [round(min(v[0][1] for t in c for v in t), 3), round(max(v[0][1] for t in c for v in t), 3)],
            "plan_u2": round(sum(a), 1), "over_island_u2": round(over, 1),
            "weld_island_verts": weld_island, "weld_other_land_verts": len(ck & other_land),
            "welds": dict(welds),
            "topo": dict(Counter(ida(t)["topograph"] for t in c).most_common(8)),
            "event": dict(Counter(ida(t)["event"] for t in c)),
            "area": dict(Counter(ida(t)["area"] for t in c).most_common(4)),
            "idall": dict(Counter(int(round(t[0][3][0])) for t in c).most_common(4)),
        })
    # the island's boundary: the coast and its holes; a hole every vertex of which is an Object vertex is a plug
    okeys = {(round(v[0][0], 3), round(v[0][2], 3)) for _b, t in objs for v in t}
    cyc = ME.boundary_cycles(island)
    holes = []
    for r in cyc:
        P = [(p[0], p[2]) if len(p) == 3 else (p[0][0], p[0][2]) for p in r]
        ar = 0.5 * sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(P, P[1:] + P[:1]))
        holes.append({"verts": len(P), "signed_u2": round(ar, 2),
                      "object_verts": sum(1 for p in P if (round(p[0], 3), round(p[1], 3)) in okeys),
                      "y_max": round(max((p[1] if len(p) == 3 else p[0][1]) for p in r), 3)})
    holes.sort(key=lambda h: -abs(h["signed_u2"]))
    flow = {p: sum(1 for b in near for t in tris(b, p) if any(k3(v) in ikeys for v in t)) for p in FLOW}
    lm = LO.nearest_landmark(*at)
    out = {"at": at, "disc": disc, "blocks": sorted(blocks), "island_tris": len(island),
           "island_u2": round(sum(area2(t) for t in island), 1),
           "island_y": round(max(v[0][1] for t in island for v in t), 2),
           "island_topo": dict(Counter(ida(t)["topograph"] for t in island).most_common(8)),
           "island_area": dict(Counter(ida(t)["area"] for t in island).most_common(4)),
           "entrance_tris": dict(Counter(ida(t)["event"] for t in island if ida(t)["event"])),
           "weld_other_land_verts": len(ikeys & other_land),
           "weld_water_verts": len({k for k in ikeys if keys_of.get(k, set()) & set(WATER)}),
           "boundary": holes, "flow_welded": {p: n for p, n in flow.items() if n},
           "landmark": {"name": lm.get("name"), "dist": round(lm.get("dist", 0), 1)},
           "objects": rows}
    return out, island, [t for c in comps for t in c if any(k3(v) in ikeys for v in t) or
                         any(over_island(TR._plan_centroid(u)) for u in c[:1])], near, tris


def render(at, near, tris, obj_on, island):
    from ff9mapkit.world import render as R
    rs = R.RenderSite(cells=((0, 0),), disc=1)
    names = {"sea4": "Sea4", "sea5": "Sea5", "sea3": "Sea3", "sea1": "Sea1", "sea2": "Sea2", "beach1": "Beach1",
             "terrain": "Terrain", "object": "Object"}
    tex = {p: R.tex_for(n, rs) for p, n in names.items()}
    soup = {p: [t for b in near for t in tris(b, p)] for p in Q6.ORDER}
    xs = [v[0][0] for t in island for v in t]
    zs = [v[0][2] for t in island for v in t]
    box = (min(xs) - 16, max(xs) + 16, min(zs) - 16, max(zs) + 16)
    i0, _ = Q6.raster(soup, box, tex)
    _x, ob = Q6.raster({"object": obj_on}, box, {})
    _y, lb = Q6.raster({"terrain": island}, box, {})
    i1 = (i0.astype(np.float32) * 0.45).astype(np.uint8)
    i1[lb.sum(2) > 0] = (70, 150, 60)
    i1[ob.sum(2) > 0] = (220, 60, 50)
    H, W = i0.shape[:2]
    canvas = Image.new("RGB", (2 * W + 10, H), (255, 255, 255))
    canvas.paste(Image.fromarray(i0), (0, 0))
    canvas.paste(Image.fromarray(i1), (W + 10, 0))
    canvas.save(HERE / "out" / f"sh_b1_{int(at[0])}_{int(-at[1])}.png")


def main():
    import ff9mapkit
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    res = {}
    for at in SITES:
        r1 = site(at, 1)
        out, island, obj_on, near, tris = r1
        r4 = site(at, 4)
        d4 = r4 if isinstance(r4, dict) else r4[0]
        # disc 4 against disc 1: the island's land and the Object on it, tri for tri
        if not isinstance(r4, dict):
            key = lambda t: tuple(sorted(k3(v) for v in t))  # noqa: E731
            _o4, isl4, obj4, _n4, _t4 = r4
            out["disc4"] = {"island_tris": len(isl4), "land_same": len({key(t) for t in island} ^ {key(t) for t in isl4}),
                            "object_tris": len(obj4), "object_diff": len({key(t) for t in obj_on}
                                                                         ^ {key(t) for t in obj4})}
        else:
            out["disc4"] = d4
        res[f"{at[0]},{at[1]}"] = out
        print(json.dumps(out, default=str))
        render(at, near, tris, obj_on, island)
    (HERE / "out" / "sh_b1_buildings.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
