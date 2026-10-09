"""ISLAND CLUSTERS, question 1 (2026-10-09): how did disc 4 remove Shimmering Island and keep its islets?

Shimmering Island and its islets share their coastal water: the kit's sink refuses it ("its coastal sea runs on into
another coast's"). Disc 4 itself removed the main island and kept the islets. This compares the two discs over the four
blocks, tri by tri (a tri is the same when its three positions match to 1e-3): per part, tris kept, removed (disc 1
only) and added (disc 4 only); for every disc-1 land component, whether disc 4 keeps it whole, and for the kept ones
whether their coast-conforming water (water tris sharing a vertex with them) is kept byte for byte or re-cut; and where
the added water meets kept water, whether on tile corners only. Renders disc 1, disc 4 and the change map (removed red,
added green) with the game's textures.
Writes out/sh_c1_shimmering.json and out/sh_c1_shimmering.png.
Run (from C:\\gd\\Dream-World-IX):  py studies/terrain-malleability/land2sea/sh_c1_shimmering.py
"""
import json
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

SHIM = [(6, 4), (7, 4), (6, 5), (7, 5)]
PARTS = ("terrain", "beach1", "sea1", "sea2", "sea3", "sea5", "sea4", "object")
WATER = ("sea1", "sea2", "sea3", "sea5", "sea4")


def key(t):
    return tuple(sorted((round(v[0][0], 3), round(v[0][1], 3), round(v[0][2], 3)) for v in t))


def vk(v):
    return (round(v[0][0], 3), round(v[0][2], 3))


def main():
    import ff9mapkit
    from ff9mapkit.world import meshedit as ME, render as R, transplant as TR
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    soup = {d: {p: [t for b in SHIM for t in TR.world_tris(*b, p, disc=d)] for p in PARTS} for d in (1, 4)}
    res = {"parts": {}}
    k4 = {p: {key(t) for t in soup[4][p]} for p in PARTS}
    k1 = {p: {key(t) for t in soup[1][p]} for p in PARTS}
    for p in PARTS:
        res["parts"][p] = {"disc1": len(soup[1][p]), "kept": len(k1[p] & k4[p]), "removed": len(k1[p] - k4[p]),
                           "added": len(k4[p] - k1[p])}
    # disc-1 land components and their fate
    land1 = soup[1]["terrain"] + soup[1]["beach1"]
    comps = ME.vertex_components(land1)
    land4 = k4["terrain"] | k4["beach1"]
    rows = []
    for c in comps:
        kept = sum(1 for t in c if key(t) in land4)
        area = sum(TR._plan_clip_area([(v[0][0], v[0][2]) for v in t], -1e9, 1e9, -1e9, 1e9) for t in c)
        vs = {vk(v) for t in c for v in t}
        coast = {p: [t for t in soup[1][p] if any(vk(v) in vs for v in t)] for p in WATER}
        rows.append({"land_tris": len(c), "u2": round(area, 1), "kept_on_disc4": kept,
                     "centroid": [round(float(np.mean([v[0][0] for t in c for v in t])), 1),
                                  round(float(np.mean([v[0][2] for t in c for v in t])), 1)],
                     "coast_water": {p: [len(ts), sum(1 for t in ts if key(t) in k4[p])] for p, ts in coast.items()
                                     if ts}})
    res["components"] = sorted(rows, key=lambda r: -r["u2"])
    # where added disc-4 water meets kept water: shared vertices on 4u corners vs mid-edge vs off-lattice
    kept_v = {vk(v) for p in WATER for t in soup[4][p] if key(t) in k1[p] for v in t}
    meet = Counter()
    for p in WATER:
        for t in soup[4][p]:
            if key(t) in k1[p]:
                continue
            for v in t:
                if vk(v) in kept_v:
                    fx, fz = v[0][0] / 4 % 1, v[0][2] / 4 % 1
                    on_x, on_z = min(fx, 1 - fx) < 1e-3, min(fz, 1 - fz) < 1e-3
                    meet["corner" if on_x and on_z else "on a lattice line" if on_x or on_z else "off lattice"] += 1
    res["added_meets_kept"] = dict(meet)
    for r in res["components"]:
        print(r)
    print(json.dumps(res["parts"]))
    print("added water meets kept water at:", res["added_meets_kept"])
    (HERE / "out" / "sh_c1_shimmering.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    # renders
    site = R.RenderSite(cells=((0, 0),), disc=1)
    names = {"sea4": "Sea4", "sea5": "Sea5", "sea3": "Sea3", "sea1": "Sea1", "sea2": "Sea2", "beach1": "Beach1",
             "terrain": "Terrain", "object": "Object"}
    tex = {p: R.tex_for(n, site) for p, n in names.items()}
    box = (384.0, 512.0, -384.0, -256.0)
    i1, _ = Q6.raster(soup[1], box, tex)
    i4, _ = Q6.raster(soup[4], box, tex)
    gone = {p: [t for t in soup[1][p] if key(t) not in k4[p]] for p in PARTS}
    new = {p: [t for t in soup[4][p] if key(t) not in k1[p]] for p in PARTS}
    _x, mg = Q6.raster(gone, box, {})
    _y, mn = Q6.raster(new, box, {})
    ch = (i4.astype(np.float32) * 0.35).astype(np.uint8)
    ch[mg.sum(2) > 0] = (200, 40, 40)
    ch[mn.sum(2) > 0] = (40, 200, 60)
    H, W = i1.shape[:2]
    canvas = Image.new("RGB", (3 * W + 20, H), (255, 255, 255))
    for k, im in enumerate((i1, i4, ch)):
        canvas.paste(Image.fromarray(im), (k * (W + 10), 0))
    canvas.save(HERE / "out" / "sh_c1_shimmering.png")


if __name__ == "__main__":
    main()
