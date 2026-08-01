"""S6 -- THE REGION-CARRY FEASIBILITY: can the mesa be carried inside its OWN neighbourhood,
so the only minted junction is a COAST?

Registered in studies/path-d-new-world/GROUND-JUNCTION-SYNTHESIS.md S6. READ-ONLY vs stock
disc-1 (and the container index); nothing deploys, nothing under the game install is written.

  A  PART / OBJECT / LANDMARK inventory of the donor window (what would come along).
  B  THE BLOCK-LEVEL LANDMASS COMPONENT of donor (15,14): which blocks are land-connected
     across their shared 64u borders (a border carries land iff a terrain/beach1 vert on one
     side WELDS to one on the other -- same along-coordinate and same y to 0.05u; mere
     within-1.0u reach on both sides is NOT enough, two coastlines can nearly touch). The
     component IS the exact scope of "carry out to the sea on every side".
  C  RECT LEDGER: for every rect containing (15,14) up to the window, the perimeter split into
     4u cell slots -> CUT slots (land welds across: a minted land-to-land junction, the class
     that has failed 8x) vs TOUCH (land ends at the border, nothing minted) vs WATER (a coast,
     the class with proven machinery), plus the water-band composition
     of the sea border (all-sea4 = Wang-free per THE WANG-CARRY LAW; shallow = crop seams).
  D  DONOR NEIGHBOURHOOD ANATOMY (14..16)x(13..15): per-block topo histograms + y ranges,
     forest/feature blobs, the mesa's foot weld line, and THE OUTWARD GROUND PROFILE from the
     foot (how far until the donor's own ground returns to its own local lowland) -- the S5
     radius this study needs to size the carry.

Artifacts -> out/region_carry_feasibility.json + out/region_carry.png
Regenerate: py -X utf8 region_carry_feasibility.py
"""
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import transplant as TP                 # noqa: E402
from ff9mapkit.world import locate as LOC                    # noqa: E402

OUT = Path(__file__).with_name("out") / "region_carry_feasibility.json"
PNG = Path(__file__).with_name("out") / "region_carry.png"

DONOR = (15, 14)
BLOCK = 64.0
CELL = 4.0
GRID_X, GRID_Y = 24, 20
EPS_PLANE = 1.0                     # the transplant.py tongue tolerance

ROCK = {49, 7, 62}
GRASS = {0, 1, 2, 3, 42}
PLATEAU = {10, 11, 12}
SHELF = {13}
FOREST = {36, 37}
# THE ENGINE FOOT-WALK TABLE (coast-mosaic memory): foot-legal topographs
FOOT_LEGAL = set(range(0, 8)) | {10, 11, 12, 13} | set(range(16, 24)) | {27, 28, 30, 31} \
    | set(range(32, 39)) | {41, 42, 45, 46, 52}
WATER_TOPO = {53, 54, 55, 56, 57}
LAND_PARTS = ("terrain", "beach1")


# ---------------------------------------------------------------------------- helpers
def part_blocks(disc=1, lod="0_1"):
    """{part: set((x,y))} straight off the bundle container index (the ground truth)."""
    env = X._worldmap_env(disc)
    pat = re.compile(rf"worldmap/disc{disc}/{lod}/r\d+/block\[(\d+)\]\[(\d+)\] ([a-z0-9]+)(?:\.asset)?$")
    per = defaultdict(set)
    for k in env.container:
        m = pat.search((k or "").lower())
        if m:
            per[m.group(3)].add((int(m.group(1)), int(m.group(2))))
    return {p: bs for p, bs in per.items()}


_BM = {}


def bm_of(bx, by, part="terrain"):
    key = (bx, by, part)
    if key not in _BM:
        try:
            _BM[key] = X.read_block(bx, by, part=part)
        except Exception:
            _BM[key] = None
    return _BM[key]


def tris_world(bx, by, part="terrain"):
    """[(3x3 world verts, topo)] for a block's part; [] if absent."""
    bm = bm_of(bx, by, part)
    if bm is None:
        return []
    V = bm.chan_arrays[X.CH_POS]
    T = bm.chan_arrays[X.CH_TAN]
    ox, oz = BLOCK * bx, -BLOCK * by
    out = []
    fi = bm.flat_index
    for t in range(len(fi) // 3):
        idx = fi[3 * t:3 * t + 3]
        p = [(V[i][0] + ox, V[i][1], V[i][2] + oz) for i in idx]
        topo = X.decode_id(int(round(T[idx[0]][0])))["topograph"]
        out.append((p, topo))
    return out


def reach_slots(bx, by, axis, plane, parts=LAND_PARTS):
    """The set of 4u slot indices along `plane` (axis 0 -> x=plane, slots by z; axis 2 -> by x)
    where this block's LAND reaches within EPS_PLANE of the plane. Slots are CLAMPED to the 16
    that the border itself owns -- real verts overhang their block, and an unclamped count made
    `16 - land` go negative (the first calibration catch)."""
    slots = set()
    if axis == 0:                    # plane x=const: slots run along z over THIS block's row
        lo = int(math.floor(-BLOCK * (by + 1) / CELL))
    else:                            # plane z=const: slots run along x over THIS block's column
        lo = int(math.floor(BLOCK * bx / CELL))
    for part in parts:
        for (p, topo) in tris_world(bx, by, part):
            for v in p:
                if abs(v[axis] - plane) <= EPS_PLANE:
                    other = v[2] if axis == 0 else v[0]
                    s = int(math.floor(other / CELL))
                    if lo <= s < lo + 16:
                        slots.add(s)
    return slots


def plane_pts(bx, by, axis, plane, parts=LAND_PARTS):
    """[(along, y)] for every LAND vert of this block sitting ON `plane` (within EPS_PLANE),
    clamped to the 16 slots the border owns."""
    if axis == 0:
        lo = -BLOCK * (by + 1)
    else:
        lo = BLOCK * bx
    out = []
    for part in parts:
        for (p, topo) in tris_world(bx, by, part):
            for v in p:
                if abs(v[axis] - plane) <= EPS_PLANE:
                    other = v[2] if axis == 0 else v[0]
                    if lo <= other < lo + BLOCK:
                        out.append((other, v[1]))
    return out


def weld_slots(bx, by, nb, axis, plane, tol=0.05):
    """The 4u slots where the two sides' land actually WELDS across `plane` (a vert pair matching
    in the along-coordinate AND in y). Strictly stronger than 'both sides reach the plane': two
    separate coastlines can each come within 1.0u of a block border without being one landmass
    (the fourth calibration catch -- it is what makes the CUT count honest)."""
    A = plane_pts(bx, by, axis, plane) if (bx, by) in land_blocks else []
    B = plane_pts(nb[0], nb[1], axis, plane) if nb in land_blocks else []
    if not A or not B:
        return set()
    Bk = defaultdict(list)
    for (o, y) in B:
        Bk[int(math.floor(o / tol))].append((o, y))
    hit = set()
    for (o, y) in A:
        k0 = int(math.floor(o / tol))
        for k in (k0 - 1, k0, k0 + 1):
            for (o2, y2) in Bk.get(k, ()):
                if abs(o - o2) <= tol and abs(y - y2) <= tol:
                    hit.add(int(math.floor(o / CELL)))
                    break
    return hit


def water_bands(bx, by, axis, plane):
    """Which sea/beach parts have verts on `plane` in this block (the Wang-crop question)."""
    hit = set()
    for part in ("beach1", "sea1", "sea2", "sea3", "sea5", "sea4"):
        for (p, topo) in tris_world(bx, by, part):
            if any(abs(v[axis] - plane) <= EPS_PLANE for v in p):
                hit.add(part)
                break
    return hit


def pct(a, q):
    return float(np.percentile(a, q)) if len(a) else None


# ---------------------------------------------------------------------------- A. inventory
res = {"donor": list(DONOR)}
PB = part_blocks()
land_blocks = set(PB.get("terrain", set()))
obj_blocks = set(PB.get("object", set()))
print(f"[A] parts on disc1: {sorted(PB)}  land blocks {len(land_blocks)}  object blocks {len(obj_blocks)}")

# navipos landmark names by block
landmarks = defaultdict(list)
for (loc, name, tx, ty) in LOC.NAVIPOS:
    wx, wz = tx / 256.0, ty / 256.0
    landmarks[(int(wx // BLOCK), int(-wz // BLOCK))].append(name)

WIN = [(bx, by) for by in range(11, 18) for bx in range(12, 22)]
inv = {}
for (bx, by) in WIN:
    have = sorted(p for p, bs in PB.items() if (bx, by) in bs)
    if not have:
        continue
    tw = tris_world(bx, by, "terrain")
    ys = [v[1] for (p, t) in tw for v in p]
    topo = Counter(t for (p, t) in tw)
    inv[f"{bx},{by}"] = dict(parts=have, tris=len(tw),
                             y=[round(min(ys), 2), round(max(ys), 2)] if ys else None,
                             topo=dict(sorted(topo.items())),
                             landmarks=sorted(set(landmarks.get((bx, by), []))))
res["window_inventory"] = inv
print(f"[A] window {len(inv)} blocks with data")
for k, v in inv.items():
    if v["landmarks"] or "object" in v["parts"]:
        print(f"    ({k}) parts={','.join(v['parts'])} landmarks={v['landmarks']}")

# ---------------------------------------------------------------------------- B. component
print("[B] land-connectivity over the whole 24x20 grid ...")
adj = defaultdict(set)
border_land = {}          # (axis, plane, cellA, cellB) -> shared slot count
for (bx, by) in sorted(land_blocks):
    for (nbx, nby, axis) in ((bx + 1, by, 0), (bx, by + 1, 2)):
        if (nbx, nby) not in land_blocks:
            continue
        plane = BLOCK * (bx + 1) if axis == 0 else -BLOCK * (by + 1)
        near = reach_slots(bx, by, axis, plane) & reach_slots(nbx, nby, axis, plane)
        shared = weld_slots(bx, by, (nbx, nby), axis, plane)     # the STRICT test
        border_land[f"{bx},{by}|{nbx},{nby}"] = dict(weld=len(shared), near=len(near))
        if shared:
            adj[(bx, by)].add((nbx, nby))
            adj[(nbx, nby)].add((bx, by))

seen = {DONOR}
stack = [DONOR]
while stack:
    c = stack.pop()
    for n in adj[c]:
        if n not in seen:
            seen.add(n)
            stack.append(n)
comp = sorted(seen)
cx = [c[0] for c in comp]
cy = [c[1] for c in comp]
res["landmass_component"] = dict(blocks=len(comp), bbox=[min(cx), min(cy), max(cx), max(cy)],
                                 cells=[list(c) for c in comp])
print(f"[B] donor's land-connected block component: {len(comp)} blocks, "
      f"bbox x[{min(cx)}..{max(cx)}] y[{min(cy)}..{max(cy)}]")

# how many blocks does each component in the window have (context)
allseen = {}
cid = 0
for b in sorted(land_blocks):
    if b in allseen:
        continue
    cid += 1
    st = [b]
    allseen[b] = cid
    while st:
        c = st.pop()
        for n in adj[c]:
            if n not in allseen:
                allseen[n] = cid
                st.append(n)
sizes = Counter(allseen.values())
res["all_components"] = sorted(sizes.values(), reverse=True)
print(f"[B] disc-1 land components by block count: {sorted(sizes.values(), reverse=True)}")

# THE COMPONENT CATALOG -- every self-contained stock landmass, with the relief it already
# carries. A component whose enclosing rect is small IS a ready-made region carry: zero minted
# land junction, its own coast carried whole, only water-to-water at the rect border.
by_cid = defaultdict(list)
for b, i in allseen.items():
    by_cid[i].append(b)
cat = []
for i, blocks in sorted(by_cid.items(), key=lambda kv: -len(kv[1])):
    bxs = [b[0] for b in blocks]
    bys = [b[1] for b in blocks]
    rect = (min(bxs), min(bys), max(bxs), max(bys))
    rblocks = (rect[2] - rect[0] + 1) * (rect[3] - rect[1] + 1)
    rock_tris = 0
    maxy = None
    topo_all = Counter()
    for b in blocks:
        for (p, t) in tris_world(b[0], b[1], "terrain"):
            topo_all[t] += 1
            if t in ROCK:
                rock_tris += 1
            for v in p:
                maxy = v[1] if maxy is None else max(maxy, v[1])
    lands = sorted({n for b in blocks for n in landmarks.get(b, [])})
    parts_here = sorted({p for p, bs in PB.items() for b in blocks if b in bs})
    cat.append(dict(blocks=len(blocks), rect=list(rect), rect_blocks=rblocks,
                    cells=[list(b) for b in sorted(blocks)] if len(blocks) <= 12 else None,
                    rock_tris=rock_tris, max_y=round(maxy, 1) if maxy is not None else None,
                    objects=sum(1 for b in blocks if b in obj_blocks), landmarks=lands,
                    parts=parts_here, plateau_tris=sum(topo_all[t] for t in PLATEAU),
                    shelf_tris=sum(topo_all[t] for t in SHELF),
                    forest_tris=sum(topo_all[t] for t in FOREST),
                    has_donor=bool(DONOR in set(blocks))))
res["component_catalog"] = cat
print("[B] THE COMPONENT CATALOG (self-contained stock landmasses):")
for c in cat:
    print(f"    {c['blocks']:>3} blk rect {c['rect']} ({c['rect_blocks']:>3} rect-blk) "
          f"rock={c['rock_tris']:>5} plateau={c['plateau_tris']:>4} maxy={c['max_y']:>6} "
          f"obj={c['objects']} {'<-DONOR' if c['has_donor'] else ''} {c['landmarks'][:3]}")

# ---------------------------------------------------------------------------- C. rect ledger
print("[C] rect ledger ...")


def rect_ledger(x0, y0, x1, y1):
    """LAND vs WATER slots on the rect's outer perimeter + the sea bands cropped."""
    land_slots = 0
    water_slots = 0
    total_slots = 0
    bands = set()
    detail = []
    sides = []
    for bx in range(x0, x1 + 1):
        sides.append((bx, y0, 2, -BLOCK * y0, (bx, y0 - 1), "N"))
        sides.append((bx, y1, 2, -BLOCK * (y1 + 1), (bx, y1 + 1), "S"))
    for by in range(y0, y1 + 1):
        sides.append((x0, by, 0, BLOCK * x0, (x0 - 1, by), "W"))
        sides.append((x1, by, 0, BLOCK * (x1 + 1), (x1 + 1, by), "E"))
    cut_slots = 0
    touch_slots = 0
    per_side = Counter()
    per_side_tot = Counter()
    for (bx, by, axis, plane, nb, side) in sides:
        total_slots += 16
        per_side_tot[side] += 16
        inside = reach_slots(bx, by, axis, plane) if (bx, by) in land_blocks else set()
        outside = reach_slots(nb[0], nb[1], axis, plane) if nb in land_blocks else set()
        # CUT = land WELDS across the plane -> the carry would mint a land-to-land junction.
        # TOUCH = land reaches the plane but does not weld across it -> the coastline runs along
        # the block border; the carried assembly is COMPLETE there and nothing is minted. The
        # first two runs conflated these under one "land slots" count (calibration catch 3), and
        # the third used near-reach on both sides instead of a weld (catch 4).
        wl = weld_slots(bx, by, nb, axis, plane)
        cs = len(wl)
        ts = len((inside | outside) - wl)
        cut_slots += cs
        touch_slots += ts
        land_slots += cs + ts
        per_side[side] += cs
        water_slots += 16 - cs - ts
        if cs:
            detail.append(dict(cell=[bx, by], axis=axis, cut=cs))
        for c in ((bx, by), nb):
            if c in land_blocks:
                bands |= water_bands(c[0], c[1], axis, plane)
    return dict(rect=[x0, y0, x1, y1], blocks=(x1 - x0 + 1) * (y1 - y0 + 1),
                perimeter_slots=total_slots, cut_slots=cut_slots, touch_slots=touch_slots,
                land_slots=land_slots, water_slots=water_slots,
                cut_u=round(cut_slots * CELL, 1), sea_bands=sorted(bands),
                per_side_cut={k: per_side[k] for k in "NSWE"},
                per_side_total={k: per_side_tot[k] for k in "NSWE"},
                cut_sides=detail[:40])


CANDS = [(15, 14, 15, 14), (14, 14, 15, 15), (14, 13, 16, 15), (14, 13, 16, 16),
         (13, 13, 16, 16), (13, 12, 17, 16), (12, 11, 18, 17), (12, 10, 21, 17)]
res["rect_ledger"] = [rect_ledger(*c) for c in CANDS]
for r in res["rect_ledger"]:
    print(f"    rect {r['rect']} {r['blocks']:>3} blk: CUT {r['cut_slots']:>4} slots "
          f"({r['cut_u']}u minted LAND junction)  TOUCH {r['touch_slots']:>4}  "
          f"WATER {r['water_slots']:>4}  bands {r['sea_bands']}")

# the smallest rect containing the donor with ZERO land slots on its perimeter (search all)
best = None
for x0 in range(0, DONOR[0] + 1):
    for x1 in range(DONOR[0], GRID_X):
        for y0 in range(0, DONOR[1] + 1):
            for y1 in range(DONOR[1], GRID_Y):
                # cheap necessary condition: the rect must contain the whole component
                if not (x0 <= min(cx) and x1 >= max(cx) and y0 <= min(cy) and y1 >= max(cy)):
                    continue
                area = (x1 - x0 + 1) * (y1 - y0 + 1)
                if best is None or area < best[0]:
                    best = (area, (x0, y0, x1, y1))
res["min_sea_bounded_rect"] = dict(rect=list(best[1]), blocks=best[0]) if best else None
if best:
    led = rect_ledger(*best[1])
    res["min_sea_bounded_rect"]["ledger"] = led
    print(f"[C] smallest component-enclosing rect {best[1]} = {best[0]} blocks; "
          f"CUT slots on its perimeter {led['cut_slots']} (0 = a true sea boundary), "
          f"TOUCH {led['touch_slots']}")

# ---------------------------------------------------------------------------- D. anatomy
print("[D] donor neighbourhood anatomy ...")
NB = [(bx, by) for by in range(13, 16) for bx in range(14, 17)]
nb_tris = {c: tris_world(c[0], c[1], "terrain") for c in NB}
# LOWLAND = the median of the LOWLAND BAND (y<8 per THE TERRACE LAW), not a p10 of everything:
# a p10 over all ground reads 2.15 (the bottom of the noise) and no bin can ever be within 0.5u
# of it -- the second calibration catch.
ground_y = [v[1] for c in NB for (p, t) in nb_tris[c] if t in FOOT_LEGAL and t not in FOREST
            and t not in PLATEAU and t not in SHELF for v in p]
low_band = [y for y in ground_y if y < 8.0]
lowland = pct(low_band, 50)
res["neighbourhood"] = dict(blocks=[list(c) for c in NB], ground_verts=len(ground_y),
                            lowland_band_median=round(lowland, 2), lowland_band_n=len(low_band),
                            ground_y_pct={q: round(pct(ground_y, q), 2) for q in (1, 10, 25, 50, 75, 90, 99)})
print(f"[D] neighbourhood lowland-band (y<8) median = {lowland:.2f}  "
      f"(all-ground p10={pct(ground_y,10):.2f} p50={pct(ground_y,50):.2f} p90={pct(ground_y,90):.2f})")

# the mesa: rock tris in the donor block. TWO distinct weld lines -- the CREST (rock shared with
# the enclosed PLATEAU, y~26) and the GROUND FOOT (rock shared with lowland ground). The first
# run conflated them (plateau is foot-legal) and reported a 24.7u "foot relief".
donor_tris = nb_tris[DONOR]
rock_v, low_v, plat_v = defaultdict(int), defaultdict(int), defaultdict(int)
kk = lambda v: (round(v[0], 3), round(v[1], 3), round(v[2], 3))   # noqa: E731
for (p, t) in donor_tris:
    for v in p:
        if t in ROCK:
            rock_v[kk(v)] += 1
        elif t in PLATEAU or t in SHELF:
            plat_v[kk(v)] += 1
        elif t in FOOT_LEGAL:
            low_v[kk(v)] += 1
foot = [v for v in rock_v if v in low_v]
crest = [v for v in rock_v if v in plat_v]
fy = [v[1] for v in foot]
cy_ = [v[1] for v in crest]
res["mesa"] = dict(rock_tris=sum(1 for (p, t) in donor_tris if t in ROCK),
                   rock_y=[round(min(v[1] for v in rock_v), 2), round(max(v[1] for v in rock_v), 2)],
                   foot_verts=len(foot), crest_verts=len(crest),
                   foot_weld_y=[round(min(fy), 2), round(max(fy), 2)] if fy else None,
                   foot_weld_relief=round(max(fy) - min(fy), 2) if fy else None,
                   crest_weld_y=[round(min(cy_), 2), round(max(cy_), 2)] if cy_ else None,
                   foot_weld_y_pct={q: round(pct(fy, q), 2) for q in (10, 50, 90)} if fy else None)
print(f"[D] mesa rock y {res['mesa']['rock_y']}; GROUND FOOT weld {len(foot)} verts "
      f"y {res['mesa']['foot_weld_y']} relief {res['mesa']['foot_weld_relief']}u; "
      f"CREST weld {len(crest)} verts y {res['mesa']['crest_weld_y']}")

# THE OUTWARD GROUND PROFILE: for every ground vert in the 3x3, plan distance to the nearest
# foot vert -> height profile; and which feature class first interrupts the ground, per sector.
fxz = np.array([[v[0], v[2]] for v in foot], dtype=float)
gpts = []
for c in NB:
    for (p, t) in nb_tris[c]:
        for v in p:
            gpts.append((v[0], v[2], v[1], t))
gpts = list({(round(a, 3), round(b, 3), round(y, 3), t) for (a, b, y, t) in gpts})
GX = np.array([[a, b] for (a, b, y, t) in gpts])
GY = np.array([y for (a, b, y, t) in gpts])
GT = np.array([t for (a, b, y, t) in gpts])
d = np.sqrt(((GX[:, None, :] - fxz[None, :, :]) ** 2).sum(-1)).min(1)

is_ground = np.array([bool(t in FOOT_LEGAL and t not in FOREST and t not in PLATEAU
                           and t not in SHELF) for t in GT])
bins = [(0, 4), (4, 8), (8, 12), (12, 16), (16, 20), (20, 28), (28, 36), (36, 48), (48, 64)]
prof = []
for (lo, hi) in bins:
    m = is_ground & (d >= lo) & (d < hi)
    if m.sum() < 4:
        prof.append(dict(r=[lo, hi], n=int(m.sum())))
        continue
    prof.append(dict(r=[lo, hi], n=int(m.sum()), y_med=round(float(np.median(GY[m])), 2),
                     y_p10=round(float(np.percentile(GY[m], 10)), 2),
                     y_p90=round(float(np.percentile(GY[m], 90)), 2),
                     above_lowland=round(float(np.median(GY[m]) - lowland), 2)))
res["outward_profile"] = prof
print("[D] outward ground profile from the mesa foot (plan distance -> median y):")
for p in prof:
    if "y_med" in p:
        print(f"    r {p['r'][0]:>2}-{p['r'][1]:<2}u n={p['n']:>4} y_med={p['y_med']:>5.2f} "
              f"(+{p['above_lowland']} over lowland)  p10={p['y_p10']} p90={p['y_p90']}")

# the radius at which the ground settles: first bin whose median is within 0.5u of lowland
settle = None
for p in prof:
    if "y_med" in p and p["above_lowland"] <= 0.5:
        settle = p["r"]
        break
res["lowland_return_radius"] = settle
print(f"[D] ground returns to within 0.5u of its own lowland at r = {settle} u from the foot")

# IS THE 4.6u WELD RELIEF REGIONAL OR LOCAL? Split the foot verts by their OWN y and profile the
# ground outward from EACH subset. If the HIGH-weld subset's ground stays high for 8-16u, the
# donor sits on a regional rise the bench must reproduce; if it drops to lowland immediately, the
# relief is a LOCAL skirt and no destination mound is called for.
weld_local = {}
for (name, lo, hi) in (("low_<4", -99, 4.0), ("mid_4-6", 4.0, 6.0), ("high_>6", 6.0, 99)):
    sub = np.array([[v[0], v[2]] for v in foot if lo <= v[1] < hi], dtype=float)
    if len(sub) < 3:
        weld_local[name] = dict(n=len(sub))
        continue
    dsub = np.sqrt(((GX[:, None, :] - sub[None, :, :]) ** 2).sum(-1)).min(1)
    row = dict(n=int(len(sub)), weld_y_med=round(float(np.median([v[1] for v in foot
                                                                 if lo <= v[1] < hi])), 2))
    for (a, b) in ((0, 4), (4, 8), (8, 16), (16, 24)):
        m = is_ground & (dsub >= a) & (dsub < b)
        row[f"r{a}_{b}"] = (dict(n=int(m.sum()), y_med=round(float(np.median(GY[m])), 2))
                            if m.sum() >= 4 else dict(n=int(m.sum())))
    weld_local[name] = row
res["weld_relief_locality"] = weld_local
print("[D] weld-relief locality (ground median y outward from foot verts grouped by their own y):")
for k, v in weld_local.items():
    if "weld_y_med" in v:
        print(f"    foot {k:>8} n={v['n']:>3} weld_y={v['weld_y_med']:>5} -> "
              + "  ".join(f"r{a}-{b}:{v[f'r{a}_{b}'].get('y_med','-')}"
                          for (a, b) in ((0, 4), (4, 8), (8, 16), (16, 24))))

# per-sector: from the mesa foot centroid, how far out is contiguous walkable ground before the
# first NON-ground class (water part vert / rock / forest) -- the "own ground" radius
fc = fxz.mean(0)
sector = {}
for k in range(8):
    a0 = k * 45.0 - 22.5
    a1 = a0 + 45.0
    ang = np.degrees(np.arctan2(GX[:, 1] - fc[1], GX[:, 0] - fc[0]))
    ang = (ang - a0) % 360.0
    m = (ang >= 0) & (ang < 45.0)
    dd = np.sqrt(((GX - fc) ** 2).sum(1))
    gm = m & is_ground
    sector[f"{int(k*45)}deg"] = dict(ground_max_r=round(float(dd[gm].max()), 1) if gm.any() else None,
                                     n=int(gm.sum()))
res["sector_ground_reach"] = sector

# water reach: nearest water-part vert to the mesa foot centroid, per part
wat = {}
for part in ("beach1", "sea1", "sea2", "sea3", "sea5", "sea4"):
    best_d = None
    for c in [(bx, by) for by in range(12, 18) for bx in range(12, 19)]:
        for (p, t) in tris_world(c[0], c[1], part):
            for v in p:
                dd = math.hypot(v[0] - fc[0], v[2] - fc[1])
                if best_d is None or dd < best_d:
                    best_d = dd
    if best_d is not None:
        wat[part] = round(best_d, 1)
res["nearest_water_from_foot"] = wat
res["foot_centroid"] = [round(float(fc[0]), 1), round(float(fc[1]), 1)]
print(f"[D] foot centroid world ({fc[0]:.1f},{fc[1]:.1f}); nearest water by part: {wat}")

# feature blobs coming along in the 3x3: connected topo-class components (cell granularity)
blobs = {}
for name, cls in (("forest", FOREST), ("rock", ROCK), ("plateau", PLATEAU), ("shelf", SHELF)):
    cells = set()
    for c in NB:
        for (p, t) in nb_tris[c]:
            if t in cls:
                cxx = sum(v[0] for v in p) / 3.0
                czz = sum(v[2] for v in p) / 3.0
                cells.add((int(math.floor(cxx / CELL)), int(math.floor(czz / CELL))))
    # 4-connected components
    comps = []
    left = set(cells)
    while left:
        s = left.pop()
        q = [s]
        cur = {s}
        while q:
            a = q.pop()
            for dxy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (a[0] + dxy[0], a[1] + dxy[1])
                if n in left:
                    left.discard(n)
                    cur.add(n)
                    q.append(n)
        comps.append(cur)
    blobs[name] = dict(cells=len(cells), components=len(comps),
                       sizes=sorted((len(cc) for cc in comps), reverse=True)[:8])
res["neighbourhood_blobs"] = blobs
print(f"[D] blobs in the 3x3: " + "  ".join(f"{k}={v['cells']}cells/{v['components']}comp"
                                            for k, v in blobs.items()))

# -------------------------------------------------------------- E. carry candidates in detail
print("[E] SELF-CONTAINED CARRY CANDIDATES (components whose enclosing rect is <= 8 blocks) ...")
cands = []
for c in cat:
    if c["rect_blocks"] > 8:
        continue
    (x0, y0, x1, y1) = c["rect"]
    led = rect_ledger(x0, y0, x1, y1)
    blocks = [tuple(b) for b in (c["cells"] or [])]
    per_block = {}
    rock_pts = []
    ground_area = 0.0
    for b in blocks:
        have = sorted(p for p, bs in PB.items() if b in bs)
        tw = tris_world(b[0], b[1], "terrain")
        tc = Counter(t for (p, t) in tw)
        for (p, t) in tw:
            if t in ROCK:
                rock_pts += list(p)
            if t in FOOT_LEGAL and t not in FOREST:
                ground_area += abs((p[1][0] - p[0][0]) * (p[2][2] - p[0][2])
                                   - (p[1][2] - p[0][2]) * (p[2][0] - p[0][0])) / 2.0
        ys = [v[1] for (p, t) in tw for v in p]
        per_block[f"{b[0]},{b[1]}"] = dict(parts=have, tris=len(tw),
                                           y=[round(min(ys), 2), round(max(ys), 2)] if ys else None,
                                           topo=dict(sorted(tc.items())))
    rock_ext = None
    if rock_pts:
        rx = [v[0] for v in rock_pts]
        rz = [v[2] for v in rock_pts]
        ry = [v[1] for v in rock_pts]
        rock_ext = dict(plan=[round(max(rx) - min(rx), 1), round(max(rz) - min(rz), 1)],
                        y=[round(min(ry), 2), round(max(ry), 2)],
                        height=round(max(ry) - min(ry), 1))
    cands.append(dict(rect=c["rect"], land_blocks=c["blocks"], rect_blocks=c["rect_blocks"],
                      objects=c["objects"], landmarks=c["landmarks"], rock_tris=c["rock_tris"],
                      forest_tris=c["forest_tris"], plateau_tris=c["plateau_tris"],
                      max_y=c["max_y"], rock_extent=rock_ext,
                      walkable_plan_area=round(ground_area, 0),
                      perimeter_cut_slots=led["cut_slots"], perimeter_touch_slots=led["touch_slots"],
                      perimeter_water_slots=led["water_slots"],
                      sea_bands=led["sea_bands"], per_block=per_block))
res["carry_candidates"] = cands
for c in cands:
    print(f"    rect {c['rect']} land={c['land_blocks']}blk rect={c['rect_blocks']}blk "
          f"rock={c['rock_tris']} rockext={c['rock_extent']} ground={c['walkable_plan_area']}u2 "
          f"obj={c['objects']} perim CUT={c['perimeter_cut_slots']} "
          f"TOUCH={c['perimeter_touch_slots']} bands={c['sea_bands']} "
          f"{c['landmarks']}")

# the donor mesa's own plan extent, for scale comparison against the candidates
mx = [v[0] for v in rock_v]
mz = [v[2] for v in rock_v]
res["mesa"]["plan_extent"] = [round(max(mx) - min(mx), 1), round(max(mz) - min(mz), 1)]
print(f"[E] the (15,14) donor mesa's own rock plan extent = {res['mesa']['plan_extent']}u, "
      f"crest {res['mesa']['crest_weld_y']}")

# ------------------------------------------------- F. is the "complete" mesa really self-contained?
# The mesa was carried as a COMPLETE feature from one block. If its rock touches (15,14)'s own
# block borders and welds to rock beyond, then even the 1x1 "whole feature" carry CUT the feature.
brd = {}
for (nb, axis, plane, name) in (((14, 14), 0, BLOCK * 15, "W"), ((16, 14), 0, BLOCK * 16, "E"),
                                ((15, 13), 2, -BLOCK * 14, "N"), ((15, 15), 2, -BLOCK * 15, "S")):
    on = [v for v in rock_v if abs((v[0] if axis == 0 else v[2]) - plane) <= EPS_PLANE]
    nb_tw = tris_world(nb[0], nb[1], "terrain")
    nb_rock, nb_grnd = set(), set()
    for (p, t) in nb_tw:
        for v in p:
            if abs((v[0] if axis == 0 else v[2]) - plane) <= EPS_PLANE:
                (nb_rock if t in ROCK else nb_grnd).add(kk(v))
    welded_rock = sum(1 for v in on if any(abs(v[0] - w[0]) <= 0.05 and abs(v[1] - w[1]) <= 0.05
                                           and abs(v[2] - w[2]) <= 0.05 for w in nb_rock))
    brd[name] = dict(mesa_rock_verts_on_border=len(on),
                     y=[round(min(v[1] for v in on), 2), round(max(v[1] for v in on), 2)] if on else None,
                     neighbour_rock_verts_on_border=len(nb_rock),
                     neighbour_ground_verts_on_border=len(nb_grnd),
                     mesa_rock_welded_to_neighbour_rock=welded_rock)
res["mesa_block_border_continuation"] = brd
print("[F] mesa rock on its own block borders (is the 'complete feature' actually cut?):")
for k, v in brd.items():
    print(f"    {k}: mesa rock verts on border={v['mesa_rock_verts_on_border']:>3} y={v['y']} "
          f"neighbour rock on border={v['neighbour_rock_verts_on_border']:>3} "
          f"WELDED rock-to-rock={v['mesa_rock_welded_to_neighbour_rock']}")

# ------------------------------------------------ G. what does each foot vert actually touch?
# The r0-4 profile found NO lowland ground within 4u of the HIGH weld verts, yet they are welded
# to a foot-legal tri by construction -- so the class they meet is not lowland grass. Name it.
CLS = [("grass", GRASS), ("forest", FOREST), ("plateau", PLATEAU), ("shelf", SHELF),
       ("rock", ROCK), ("dirt17_38", {17, 38}), ("lip58", {58})]
inc = defaultdict(set)
for c in NB:                                        # the donor block + its 8 neighbours
    for (p, t) in nb_tris[c]:
        for v in p:
            k = kk(v)
            if k in rock_v or k in low_v or k in plat_v:
                named = [nm for (nm, s) in CLS if t in s]
                inc[k] |= set(named) if named else {f"topo{t}"}
foot_touch = {}
for (name, lo, hi) in (("low_<4", -99, 4.0), ("mid_4-6", 4.0, 6.0), ("high_>6", 6.0, 99)):
    sub = [v for v in foot if lo <= v[1] < hi]
    cnt = Counter()
    for v in sub:
        for nm in inc.get(v, ()):
            cnt[nm] += 1
    foot_touch[name] = dict(n=len(sub), touches=dict(cnt.most_common()))
res["foot_vert_adjacency"] = foot_touch
print("[G] what the mesa's foot verts touch, by their own weld height:")
for k, v in foot_touch.items():
    print(f"    {k:>8} n={v['n']:>3}  {v['touches']}")

# THE DECOMPOSED WELD LINE: the number a build actually needs is the GRASS-only sub-line, since a
# forest contact is a canopy junction (THE CANOPY CARRY LAW), not a ground junction.
gonly = [v[1] for v in foot if "grass" in inc.get(v, ()) and "forest" not in inc.get(v, ())]
fonly = [v[1] for v in foot if "forest" in inc.get(v, ()) and "grass" not in inc.get(v, ())]
both = [v[1] for v in foot if {"grass", "forest"} <= inc.get(v, set())]
res["weld_line_decomposed"] = dict(
    all_n=len(foot), all_y=[round(min(fy), 2), round(max(fy), 2)], all_relief=round(max(fy) - min(fy), 2),
    grass_only_n=len(gonly),
    grass_only_y=[round(min(gonly), 2), round(max(gonly), 2)] if gonly else None,
    grass_only_relief=round(max(gonly) - min(gonly), 2) if gonly else None,
    grass_only_pct={q: round(pct(gonly, q), 2) for q in (10, 50, 90)} if gonly else None,
    forest_only_n=len(fonly),
    forest_only_y=[round(min(fonly), 2), round(max(fonly), 2)] if fonly else None,
    grass_and_forest_n=len(both))
w = res["weld_line_decomposed"]
print(f"[G] THE WELD LINE DECOMPOSED: all {w['all_n']} verts y {w['all_y']} relief {w['all_relief']}u"
      f"  ->  GRASS-only {w['grass_only_n']} verts y {w['grass_only_y']} relief "
      f"{w['grass_only_relief']}u (p10/50/90 {w['grass_only_pct']})  |  FOREST-only "
      f"{w['forest_only_n']} verts y {w['forest_only_y']}  |  both {w['grass_and_forest_n']}")

# ---------------------------------------------------------------------------- PNG
S = 3                     # px per world unit / 4  -> 4u cell = S*? keep simple: px per 4u cell
W0, W1 = 12, 22           # block x range
H0, H1 = 10, 18           # block y range
CPB = 16                  # cells per block
PXC = 5                   # px per 4u cell
img = Image.new("RGB", ((W1 - W0) * CPB * PXC, (H1 - H0) * CPB * PXC), (16, 24, 44))
dr = ImageDraw.Draw(img)
COL = {"rock": (150, 120, 105), "grass": (86, 140, 74), "plateau": (120, 160, 92),
       "forest": (36, 84, 52), "shelf": (150, 170, 120), "other": (170, 150, 110),
       "water": (34, 66, 120)}


def px(wx, wz):
    return ((wx - W0 * BLOCK) / CELL * PXC, (-wz - H0 * BLOCK) / CELL * PXC)


for by in range(H0, H1):
    for bx in range(W0, W1):
        for part in ("sea4", "sea5", "sea3", "sea2", "sea1", "beach1", "terrain"):
            for (p, t) in tris_world(bx, by, part):
                if part != "terrain":
                    col = COL["water"] if part.startswith("sea") else (200, 190, 150)
                else:
                    col = (COL["rock"] if t in ROCK else COL["forest"] if t in FOREST
                           else COL["plateau"] if t in PLATEAU else COL["shelf"] if t in SHELF
                           else COL["grass"] if t in GRASS else COL["other"])
                dr.polygon([px(v[0], v[2]) for v in p], fill=col)
# component outline
for (bx, by) in comp:
    x0, y0 = px(BLOCK * bx, -BLOCK * by)
    x1, y1 = px(BLOCK * (bx + 1), -BLOCK * (by + 1))
    dr.rectangle([x0, y0, x1, y1], outline=(255, 220, 90), width=1)
# candidate rects
for (i, (a, b, c2, d2)) in enumerate(CANDS[:6]):
    x0, y0 = px(BLOCK * a, -BLOCK * b)
    x1, y1 = px(BLOCK * (c2 + 1), -BLOCK * (d2 + 1))
    dr.rectangle([x0, y0, x1, y1], outline=(255, 90, 90), width=2)
# the mesa foot
for v in foot:
    x, y = px(v[0], v[2])
    dr.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(255, 255, 255))
dr.text((6, 6), "S6 region-carry: yellow=donor land component, red=candidate rects, "
                "white=mesa foot weld", fill=(240, 240, 240))
PNG.parent.mkdir(parents=True, exist_ok=True)
img.save(PNG)
print(f"[PNG] {PNG}")

# ------------------------------------------- H. do the SHIPPED region-carry gates actually pass?
# The feasibility question is only answered by the real builder. `dry_run=True` returns before any
# write (transplant.py:3446 -- every deploy_override/sidecar/mirror call is after that guard), so
# this is read-only against the install. Target = a FREE Disc9 rect (the live bench is untouched).
print("[H] dry-running the shipped transplant_region gates on the best candidate ...")
try:
    dr = TP.transplant_region("FF9CustomMap-world", cell=(17, 5), donor=(9, 5), size=(2, 3), rot=0,
                              target_disc=9, all_sea_target=True, dry_run=True)
    res["gate_dry_run"] = dict(donor=[9, 5], size=[2, 3], target_cell=[17, 5], target_disc=9,
                               clean=bool(dr["clean"]),
                               data_cells=sorted(dr["cells"]),
                               gates=[{k: v for k, v in g.items()
                                       if k in ("gate", "ok", "miss", "introduced", "inherited",
                                                "pairs", "bad", "holes", "existing", "n_orphans",
                                                "checked_by_family", "incoherent")}
                                      for g in dr["gates"]],
                               failed=[g["gate"] for g in dr["gates"] if not g.get("ok")])
    print(f"[H] clean={dr['clean']}  gates={len(dr['gates'])}  "
          f"failed={res['gate_dry_run']['failed']}  data cells={sorted(dr['cells'])}")
except Exception as e:                                   # never let the assessment die on this
    res["gate_dry_run"] = dict(error=repr(e))
    print(f"[H] dry run unavailable: {e!r}")

OUT.write_text(json.dumps(res, indent=1))
print(f"[OUT] {OUT}")
