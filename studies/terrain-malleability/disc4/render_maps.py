"""STEP 4 -- MAPS + the SHAPE TEST of disc 4's new raised rock.

  out/block_class_map.png  24x20 grid, each block coloured by its most severe Form-1 (0_1) part class
                           (RETOPO > RESHAPE > ATTR > REORDERED > IDENTICAL); violet dot = a part added/removed;
                           text = changed part initials.
  out/delta_map.png        the whole world on the 1u lattice: disc-1 ground (grey by height, sea pale blue) with the
                           engine-faithful ground deltas of every changed block overlaid by category.
  out/delta_crop_<n>.png   3x crops of the four largest change clusters (from anatomy.json).
  out/rock_ribbons.json    connected components of NEW raised rock (disc-4 topo 49 where disc 1 was walkable and the
                           ground rose >0.5u): area, PCA length/width, elongation, rise -- RIBBONS (long, narrow)
                           vs BLOBS (compact) is the shape test for the "Iifa roots" reading.

Palette = dataviz reference categorical slots 1-6 (validated: all checks pass, contrast WARN -> labelled legend).
Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/disc4/render_maps.py   (~2 min)
"""
import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d4lib as L                                    # noqa: E402
from d4lib import X, P                               # noqa: E402
from ff9mapkit.world import locate as LOC            # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
t0 = time.time()
rows = json.loads((OUT / "census.json").read_text(encoding="utf-8"))
ana = json.loads((OUT / "anatomy.json").read_text(encoding="utf-8"))
objs = L.mesh_objects()
LOD = "0_1"

C = {"blue": "#2a78d6", "orange": "#eb6834", "aqua": "#1baf7a", "yellow": "#eda100", "magenta": "#e87ba4",
     "violet": "#4a3aa7", "surface": "#fcfcfb", "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#898781",
     "grid": "#e1e0d9", "neutral": "#f0efec", "sea": "#cde2fb", "reorder": "#c3c2b7"}


def hx(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


try:
    FONT = ImageFont.truetype("arial.ttf", 13)
    FONTB = ImageFont.truetype("arialbd.ttf", 16)
    FONTS = ImageFont.truetype("arial.ttf", 10)
except OSError:
    FONT = FONTB = FONTS = ImageFont.load_default()

# ======================= 1. block class map =======================
SEV = {"RETOPO": 4, "RESHAPE": 3, "ATTR": 2, "REORDERED": 1, "IDENTICAL": 0}
COL = {4: C["orange"], 3: C["aqua"], 2: C["yellow"], 1: C["reorder"], 0: C["neutral"]}
LBL = {4: "RETOPO (triangulation/footprint re-cut)", 3: "RESHAPE (same footprints, new heights)",
       2: "ATTR (same geometry: id / uv / normal)", 1: "REORDERED only (byte-different, same tris)",
       0: "IDENTICAL (all parts byte-equal)"}
ABBR = {"terrain": "T", "object": "O", "beach1": "B", "beach2": "B2", "river": "R", "riverjoint": "J", "falls": "F",
        "stream": "St", "sea1": "1", "sea2": "2", "sea3": "3", "sea4": "4", "sea5": "5", "sea6": "6"}
blk = defaultdict(list)
for r in rows:
    if r["lod"] == LOD:
        blk[(r["x"], r["y"])].append(r)
CS, M, TOP = 46, 40, 56
W, H = 24 * CS + 2 * M + 330, 20 * CS + TOP + M
img = Image.new("RGB", (W, H), hx(C["surface"]))
d = ImageDraw.Draw(img)
d.text((M, 16), "Disc 1 -> Disc 4, Form-1 meshes: most severe change per block (24x20 grid, x right, y down)",
       fill=hx(C["ink"]), font=FONTB)
counts = Counter()
for by in range(20):
    for bx in range(24):
        x0, y0 = M + bx * CS, TOP + by * CS
        rs = blk.get((bx, by))
        if not rs:
            d.rectangle([x0, y0, x0 + CS - 2, y0 + CS - 2], fill=hx(C["sea"]))
            counts["no mesh (open-ocean fallback)"] += 1
            continue
        sev = max(SEV[r["cls"].split(":")[0].split("+")[0]] if r["cls"] not in ("ADDED", "REMOVED") else 4 for r in rs)
        counts[LBL[sev]] += 1
        d.rectangle([x0, y0, x0 + CS - 2, y0 + CS - 2], fill=hx(COL[sev]))
        ch = [ABBR.get(r["part"], r["part"][:2]) for r in rs if r["cls"] not in ("IDENTICAL", "REORDERED")]
        if ch:
            d.text((x0 + 3, y0 + 3), "".join(sorted(set(ch), key=lambda s: (len(s), s)))[:7], fill=hx(C["ink"]), font=FONTS)
        if any(r["cls"] in ("ADDED", "REMOVED") for r in rs):
            d.ellipse([x0 + CS - 14, y0 + CS - 14, x0 + CS - 5, y0 + CS - 5], fill=hx(C["violet"]))
        d.text((x0 + 3, y0 + CS - 15), f"{bx},{by}", fill=hx(C["ink2"]), font=FONTS)
lx = M + 24 * CS + 20
d.text((lx, TOP), "Legend (blocks)", fill=hx(C["ink"]), font=FONTB)
yy = TOP + 28
for sev in (4, 3, 2, 1, 0):
    d.rectangle([lx, yy, lx + 18, yy + 18], fill=hx(COL[sev]))
    d.text((lx + 26, yy + 2), f"{LBL[sev]}  n={counts[LBL[sev]]}", fill=hx(C["ink"]), font=FONTS)
    yy += 26
d.rectangle([lx, yy, lx + 18, yy + 18], fill=hx(C["sea"]))
d.text((lx + 26, yy + 2), f"no block mesh (sea fallback) n={counts['no mesh (open-ocean fallback)']}",
       fill=hx(C["ink"]), font=FONTS)
yy += 26
d.ellipse([lx + 4, yy + 4, lx + 14, yy + 14], fill=hx(C["violet"]))
d.text((lx + 26, yy + 2), "a part ADDED or REMOVED", fill=hx(C["ink"]), font=FONTS)
yy += 30
d.text((lx, yy), "Cell text = changed parts:\nT terrain, O object, B beach1,\nR river, J riverjoint, F falls,\n"
       "St stream, 1-6 sea1-6", fill=hx(C["ink2"]), font=FONTS)
img.save(OUT / "block_class_map.png")
print("block map", dict(counts))

# ======================= 2. world ground-delta raster =======================
ground_blocks = sorted({(x, y) for (dd, lod, x, y, p) in objs if dd == 1 and lod == LOD})
changed = {tuple(json.loads(k.replace("(", "[").replace(")", "]"))) for k in ana["blocks"]}


def parts_of(disc, b):
    return {p: L.decode(o, disc, x, y, lod) for (dd, lod, x, y, p), o in objs.items()
            if dd == disc and lod == LOD and (x, y) == b}


SEA = {"Sea1", "Sea2", "Sea3", "Sea4", "Sea5", "Sea6"}
base = np.zeros((1280, 1536, 3), np.uint8)
base[:] = hx(C["sea"])
cat = np.zeros((1280, 1536), np.int8)          # 0 none; 1 raised rock; 2 land->sea; 3 sea->land; 4 entrance; 5 topo/walk; 6 height
dyr = np.zeros((1280, 1536), np.float32)
t49 = np.zeros((1280, 1536), bool)
land_ramp = [hx(h) for h in ("#e1e0d9", "#c3c2b7", "#a3a29b", "#898781", "#6b6a65", "#52514e")]
for b in ground_blocks:
    p1 = parts_of(1, b)
    ml1, _ = L.meshlist_for(p1)
    pitch = 1.0 if b in changed else 2.0
    g1 = L.ground_grid(ml1, pitch)
    s = int(pitch)
    for (i, j), (gy, mesh, idall, topo) in g1.items():
        px, py = b[0] * 64 + i * s, b[1] * 64 + j * s
        if mesh == "MISS":
            col = (255, 255, 255)
        elif mesh in SEA:
            col = hx(C["sea"])
        else:
            col = land_ramp[min(5, max(0, int(gy / 6)))]
        base[py:py + s, px:px + s] = col
    if b in changed:
        p4 = parts_of(4, b)
        ml4, _ = L.meshlist_for(p4)
        g4 = L.ground_grid(ml4, 1.0)
        for (i, j), a in g1.items():
            c = g4[(i, j)]
            px, py = b[0] * 64 + i, b[1] * 64 + j
            k = 0
            e1, e4 = X.decode_id(a[2]), X.decode_id(c[2])
            land1, land4 = a[1] not in SEA and a[1] != "MISS", c[1] not in SEA and c[1] != "MISS"
            dy = (c[0] - a[0]) if (a[1] != "MISS" and c[1] != "MISS") else 0.0
            if e1["event"] != e4["event"]:
                k = 4
            elif land1 and not land4:
                k = 2
            elif land4 and not land1:
                k = 3
            elif a[3] != c[3] and c[3] == 49 and a[3] in P.WALK_OK and dy > 0.5:
                k = 1
            elif a[3] != c[3] or ((a[3] in P.WALK_OK) != (c[3] in P.WALK_OK)):
                k = 5
            elif abs(dy) > 0.25:
                k = 6
            cat[py, px] = k
            dyr[py, px] = dy
            t49[py, px] = (c[3] == 49 and a[3] != 49)
print(f"rasters built {time.time()-t0:.0f}s")

CATS = [(1, "raised NEW rock: walkable -> topo 49, rose >0.5u", C["orange"]),
        (2, "land -> sea", C["blue"]),
        (3, "sea -> land", C["aqua"]),
        (4, "entrance tile changed (event bits)", C["magenta"]),
        (5, "other topograph / walkability change", C["yellow"]),
        (6, "height-only change (|dy| > 0.25u)", C["violet"])]
rgb = base.copy()
for k, _, h in CATS:
    rgb[cat == k] = hx(h)
im = Image.fromarray(rgb)
dd = ImageDraw.Draw(im)
for i in range(25):
    dd.line([(i * 64, 0), (i * 64, 1279)], fill=hx(C["grid"]), width=1)
for j in range(21):
    dd.line([(0, j * 64), (1535, j * 64)], fill=hx(C["grid"]), width=1)
seen = set()
for lm in LOC.landmarks():
    if lm["name"] in seen and lm["name"] not in ("Qu's Marsh", "Air Garden"):
        continue
    seen.add(lm["name"])
    wx, wz = lm["world"]
    dd.ellipse([wx - 3, -wz - 3, wx + 3, -wz + 3], outline=hx(C["ink"]), width=2)
    dd.text((wx + 5, -wz - 6), lm["name"], fill=hx(C["ink"]), font=FONTS)
# legend panel
pan = Image.new("RGB", (1536 + 420, 1280 + 60), hx(C["surface"]))
pan.paste(im, (0, 60))
pd = ImageDraw.Draw(pan)
pd.text((10, 18), "Disc 1 -> Disc 4 ground deltas (engine-faithful sky-cast, 1u lattice on changed blocks; "
        "grey = disc-1 land by height, pale blue = sea)", fill=hx(C["ink"]), font=FONTB)
yy = 80
for k, lbl, h in CATS:
    pd.rectangle([1556, yy, 1576, yy + 20], fill=hx(h))
    pd.text((1584, yy + 3), f"{lbl}  ({int((cat == k).sum())} u^2)", fill=hx(C["ink"]), font=FONTS)
    yy += 30
pan.save(OUT / "delta_map.png")
for n, cl in enumerate(ana["clusters"][:4]):
    bs = cl["blocks"]
    x0 = min(b[0] for b in bs) * 64; x1 = (max(b[0] for b in bs) + 1) * 64
    y0 = min(b[1] for b in bs) * 64; y1 = (max(b[1] for b in bs) + 1) * 64
    crop = im.crop((x0, y0, x1, y1))
    sc = max(1, min(3, int(1400 / max(x1 - x0, y1 - y0))))
    crop = crop.resize(((x1 - x0) * sc, (y1 - y0) * sc), Image.NEAREST)
    crop.save(OUT / f"delta_crop_{n}.png")
print(f"maps written {time.time()-t0:.0f}s")

# ======================= 3. SHAPE TEST: raised new rock components =======================
def shape(pts):
    a = np.array(pts, float)
    mu = a.mean(0)
    ev, evec = np.linalg.eigh(np.cov((a - mu).T))
    pc1 = evec[:, 1]
    proj = (a - mu) @ pc1
    length = proj.max() - proj.min() + 1
    return a, mu, pc1, length, len(pts) / length


# self-test: a 100x6 diagonal-free ribbon, a rotated 45-degree ribbon, and a 30x30 blob
_r = [(x, y) for x in range(100) for y in range(6)]
_d = [(x + k, x - k) for x in range(80) for k in range(3)] + [(x + k + 1, x - k) for x in range(80) for k in range(3)]
_b = [(x, y) for x in range(30) for y in range(30)]
for nm, pts, lo, hi in (("ribbon 100x6", _r, 14, 19), ("diag ribbon", _d, 8, 60), ("blob 30x30", _b, 0.9, 1.6)):
    _a, _mu, _p, _l, _w = shape(pts)
    assert lo <= _l / _w <= hi, f"shape self-test {nm}: elongation {_l/_w:.1f} not in [{lo},{hi}]"
print("shape self-test PASS (ribbon ~16.7, diagonal ribbon elongated, blob ~1)")

mask = cat == 1
lab = np.zeros(mask.shape, np.int32)
comps = []
nid = 0
H_, W_ = mask.shape
for y in range(H_):
    for x in range(W_):
        if mask[y, x] and not lab[y, x]:
            nid += 1
            stack, pts = [(y, x)], []
            lab[y, x] = nid
            while stack:
                cy, cx = stack.pop()
                pts.append((cx, cy))
                for dy_ in (-1, 0, 1):
                    for dx_ in (-1, 0, 1):
                        ny, nx = cy + dy_, cx + dx_
                        if 0 <= ny < H_ and 0 <= nx < W_ and mask[ny, nx] and not lab[ny, nx]:
                            lab[ny, nx] = nid
                            stack.append((ny, nx))
            if len(pts) < 20:
                continue
            a, mu, pc1, length, width = shape(pts)
            rise = dyr[a[:, 1].astype(int), a[:, 0].astype(int)]
            lm = LOC.nearest_landmark(mu[0], -mu[1])
            comps.append({"area": len(pts), "centroid_world": [round(mu[0], 1), round(-mu[1], 1)],
                          "block": [int(mu[0] // 64), int(mu[1] // 64)],
                          "length": round(float(length), 1), "width": round(float(width), 2),
                          "elongation": round(float(length / width), 1),
                          "pc1_dir_deg": round(math.degrees(math.atan2(-pc1[1], pc1[0])) % 180, 1),
                          "rise_mean": round(float(rise.mean()), 2), "rise_max": round(float(rise.max()), 2),
                          "landmark": [lm["name"], round(lm["dist"], 1)]})
comps.sort(key=lambda c: -c["area"])
print(f"\nNEW RAISED ROCK components (>=20 u^2): {len(comps)}; total area {sum(c['area'] for c in comps)}")
for c in comps[:30]:
    print("  ", c)
el = [c["elongation"] for c in comps]
if el:
    big = [c for c in comps if c["area"] >= 200]
    print(f"\n  elongation median (all) {sorted(el)[len(el)//2]}; components >=200u^2: {len(big)}, "
          f"their width median {sorted(c['width'] for c in big)[len(big)//2] if big else None}, "
          f"length median {sorted(c['length'] for c in big)[len(big)//2] if big else None}")
(OUT / "rock_ribbons.json").write_text(json.dumps(comps, indent=0), encoding="utf-8")
print(f"-> rock_ribbons.json  total {time.time()-t0:.0f}s")
