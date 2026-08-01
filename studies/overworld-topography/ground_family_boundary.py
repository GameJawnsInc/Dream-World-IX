"""THE FAMILY-BOUNDARY LAW -- S2 of the GROUND-JUNCTION SYNTHESIS.

Registered question (studies/path-d-new-world/GROUND-JUNCTION-SYNTHESIS.md S2):
our carried-sheet seams survived BOTH uv schemes (donor tiles, then a continuous
destination retile), so they are the BOUNDARY, not the tiling. In stock disc-1:

  B1 THE ART SETS -- group every ground tri by the ATLAS ART SET its uvs sample.
     THREE TIERS, deliberately, because the grouping is the instrument's weakest
     joint and a single choice would hide the error bar:
       R  REGISTERED  -- only the byte-measured registry rects (per-family mains
          2x2, the grass meadow-D 2x2, the grass B strip). Zero grouping ambiguity;
          covers 34.7k of 47.4k ground tris. THE HEADLINE TIER.
       M  MERGED      -- registry + unregistered tris clustered by CONNECTED
          COMPONENTS of used 128px atlas cells (8-neighbour). Under-splits (two
          painted regions that touch in the atlas merge) -> a LOWER bound on
          boundary count.
       S  STRICT      -- registry + one group per used 128px atlas cell.
          Over-splits (free fractional windows put neighbouring CELLS of one
          painted set in different atlas cells) -> an UPPER bound.
     Justification for working at the art-set level at all: the BIOME level
     (topograph -> grass/desert/...) was already censused (biome_adjacency_census.py)
     and cannot see our defect -- our seam is grass-on-grass. The per-CELL tile
     identity level is where stock butts freely everywhere, and our seams survived
     a continuous retile, so that is not the defect either. The art set -- a
     contiguous painted rect of ~4 quadrants -- is the level at which the LOOK
     changes, and "weird meadowy corner tiles" names one (grass.D) against another
     (grass.main).
  B2 THE BOUNDARY CENSUS -- every welded edge between two different art sets,
     map-wide and CROSS-BLOCK (one global world-space edge map, not per-block),
     classified by CO-LOCATION: wall/rock foot, coast (the land outline + shore
     sand), water part, forest blob, town/object mesh, level change, block border,
     or NOTHING (open walkable ground with no feature near).
  B3 THE "NOTHING" SET -- length, local slope, chains, straightness, clustering.
  B4 TRANSITION VOCABULARY -- per-set boundary enrichment, the registered-set
     NEIGHBOUR matrix, and the interposition test.
  B5 UV PHASE ACROSS A BOUNDARY -- uv jump at the shared verts vs the WITHIN-SET
     control (is a uv discontinuity even special at a boundary?).
  B6 THE VISIBLE STEP -- real atlas pixels: luminance / RGB step across a boundary
     vs the within-set control, per co-location class and per pair.
  B7 THE DONOR/BENCH CASE -- block (15,14)'s own ground art sets; the exact pair
     our round-8 boundary creates (the mint's meadow stamps are grass.D) and its
     measured step vs stock's own.

Read-only vs stock disc-1. Nothing is written outside this study's out/.
Artifacts -> out/ground_family_boundary.json + out/ground_family_boundary.png
Regenerate: py -X utf8 ground_family_boundary.py
"""
import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import grassland as G                  # noqa: E402

OUTDIR = Path(__file__).with_name("out")
OUT = OUTDIR / "ground_family_boundary.json"
PNG = OUTDIR / "ground_family_boundary.png"

TILE_U, TILE_V = 0.0625, 0.03125
EPS = 0.006                                                 # the prior art's rect slack

FAM_OF = {}
for t in (0, 1, 2, 3, 10, 11, 12, 13, 42, 59):
    FAM_OF[t] = "grass"
for t in (4, 5, 6):
    FAM_OF[t] = "scrub"
for t in (16, 17, 18, 19, 20, 21, 22, 23):
    FAM_OF[t] = "desert"
for t in (27, 28):
    FAM_OF[t] = "snow"
for t in (45, 46):
    FAM_OF[t] = "canyon"
for t in (36, 37):
    FAM_OF[t] = "forest"
for t in (31, 32, 33):
    FAM_OF[t] = "shore"
FAM_OF[38] = "brush"
FAM_OF[41] = "dunes"

WALL_TOPO = {49, 7, 62, 58}
WATER_TOPO = {48, 50, 51}
PLATEAU_TOPO = {10, 11, 12}
SHELF_TOPO = {13}

SETS = {}
for fam, g in G.GROUNDS.items():
    m = G.FAM_REGION["main"]
    SETS[f"{fam}.main"] = (m[0] + g["mains_du"], m[1] + g["mains_dv"],
                           m[2] + g["mains_du"], m[3] + g["mains_dv"])
SETS["grass.D"] = G.FAM_REGION["D"]
SETS["grass.B"] = G.FAM_REGION["B"]
SET_ORDER = list(SETS)
REGISTERED = set(SET_ORDER)


def set_of(uvs):
    for name in SET_ORDER:
        r = SETS[name]
        if all(r[0] - EPS <= u <= r[2] + EPS and r[1] - EPS <= v <= r[3] + EPS for (u, v) in uvs):
            return name
    return None


def atlas_cell(uvs):
    u = sum(q[0] for q in uvs) / 3.0
    v = sum(q[1] for q in uvs) / 3.0
    return (int(math.floor((u % 1.0) / TILE_U)), int(math.floor((v % 1.0) / TILE_V)))


kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))      # noqa: E731


def pct(a, q):
    return round(float(np.percentile(a, q)), 2) if len(a) else None


def dist(a, unit=""):
    return (f"n={len(a)} med {pct(a, 50)}{unit} p10 {pct(a, 10)} p25 {pct(a, 25)} "
            f"p75 {pct(a, 75)} p90 {pct(a, 90)}")


from ff9mapkit.world import atlas as A                       # noqa: E402
_im = A.load_atlas("terrain")
if isinstance(_im, tuple):
    _im = _im[0]
AR = np.asarray(_im.convert("RGB"), dtype=float)
AH, AW = AR.shape[:2]


def tri_rgb(uvs):
    cu = sum(q[0] for q in uvs) / 3.0
    cv = sum(q[1] for q in uvs) / 3.0
    pts = [(cu, cv)] + [(0.4 * q[0] + 0.6 * cu, 0.4 * q[1] + 0.6 * cv) for q in uvs]
    acc = np.zeros(3)
    for u, v in pts:
        px = int((u % 1.0) * AW) % AW
        py = int((1.0 - (v % 1.0)) * AH) % AH
        acc += AR[py, px]
    return acc / len(pts)


def lum(rgb):
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


def tri_slope(a, b, c):
    n = np.cross(np.subtract(b, a), np.subtract(c, a))
    L = float(np.linalg.norm(n))
    return 90.0 if L < 1e-9 else math.degrees(math.acos(min(1.0, abs(float(n[1])) / L)))


# ============================================================================================
# PASS 1 -- read every block, build the global tri table
# ============================================================================================
t0 = time.time()
BLOCKS = X.list_blocks(disc=1)
OBJ_BLOCKS = set(X.list_object_blocks(disc=1))

g_topo, g_fam, g_reg, g_cell, g_v, g_uv, g_rgb, g_slope = [], [], [], [], [], [], [], []
edge_owner = defaultdict(list)
edge_ground = defaultdict(list)
feat = {c: defaultdict(list) for c in ("rock", "coast", "water", "forest", "object")}
gcell = {}
fam_tris = Counter()
n_all_tris = 0


def add_feat(cls, p):
    feat[cls][(int(math.floor(p[0] / 4.0)), int(math.floor(p[2] / 4.0)))].append((p[0], p[2]))


for (bx, by) in BLOCKS:
    try:
        bm = X.read_block(bx, by, disc=1)
    except Exception:                                       # noqa: BLE001
        continue
    V, U, T, fi = bm.verts, bm.uvs, bm.tangents, bm.flat_index
    ox, oz = 64.0 * bx, -64.0 * by
    for t in range(len(fi) // 3):
        idx = fi[3 * t:3 * t + 3]
        topo = X.decode_id(int(round(T[idx[0]][0])))["topograph"]
        w = [(V[j][0] + ox, V[j][1], V[j][2] + oz) for j in idx]
        ks = [kk(p) for p in w]
        n_all_tris += 1
        for i in range(3):
            e = tuple(sorted((ks[i], ks[(i + 1) % 3])))
            if e[0] != e[1]:
                edge_owner[e].append(topo)
        fam = FAM_OF.get(topo)
        if topo in WALL_TOPO:
            for p in w:
                add_feat("rock", p)
            continue
        if topo in WATER_TOPO:
            for p in w:
                add_feat("water", p)
            continue
        if fam is None:
            continue
        uv = [(float(U[j][0]), float(U[j][1])) for j in idx]
        gi = len(g_topo)
        g_topo.append(topo)
        g_fam.append(fam)
        g_reg.append(set_of(uv))
        g_cell.append(atlas_cell(uv))
        g_v.append(w)
        g_uv.append(uv)
        g_rgb.append(tri_rgb(uv))
        sl = tri_slope(*w)
        g_slope.append(sl)
        fam_tris[fam] += 1
        if fam == "forest":
            for p in w:
                add_feat("forest", p)
        if fam == "shore":
            for p in w:
                add_feat("coast", p)
        for i in range(3):
            e = tuple(sorted((ks[i], ks[(i + 1) % 3])))
            if e[0] != e[1]:
                edge_ground[e].append(gi)
        for p in w:
            c = (int(math.floor(p[0] / 4.0)), int(math.floor(p[2] / 4.0)))
            r = gcell.get(c)
            if r is None:
                gcell[c] = [p[1], p[1], sl]
            else:
                r[0] = min(r[0], p[1])
                r[1] = max(r[1], p[1])
                r[2] = max(r[2], sl)

for (bx, by) in sorted(OBJ_BLOCKS):
    try:
        om = X.read_block(bx, by, disc=1, part="object")
    except Exception:                                       # noqa: BLE001
        continue
    ox, oz = 64.0 * bx, -64.0 * by
    for p in om.verts:
        add_feat("object", (p[0] + ox, p[1], p[2] + oz))

n_open = n_open_on_border = 0
for e, owners in edge_owner.items():
    if len(owners) != 1:
        continue
    n_open += 1
    if any(abs(p[0] / 64.0 - round(p[0] / 64.0)) < 1e-3 or
           abs(p[2] / 64.0 - round(p[2] / 64.0)) < 1e-3 for p in e):
        n_open_on_border += 1
    for p in e:
        add_feat("coast", p)

NG = len(g_topo)
t_read = time.time() - t0
print(f"read {len(BLOCKS)} blocks / {n_all_tris} tris in {t_read:.1f}s; ground tris {NG}; "
      f"object blocks {len(OBJ_BLOCKS)}")
print(f"weld check: 1-owner (open) edges {n_open}, of which on a 64u block line "
      f"{n_open_on_border} ({n_open_on_border / max(1, n_open):.1%}) -- a high share would "
      f"mean cross-block welding FAILED")
n_reg = sum(1 for s in g_reg if s)
print(f"registry coverage: {n_reg}/{NG} ground tris land in a byte-measured registry rect "
      f"({n_reg / max(1, NG):.1%})")

# ---- the three grouping tiers ---------------------------------------------------------------
used_cells = Counter(g_cell[i] for i in range(NG) if g_reg[i] is None)
cparent = {}


def cfind(x):
    while cparent.setdefault(x, x) != x:
        cparent[x] = cparent[cparent[x]]
        x = cparent[x]
    return x


for c in used_cells:
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            d = (c[0] + dx, c[1] + dz)
            if d in used_cells:
                ra, rb = cfind(c), cfind(d)
                if ra != rb:
                    cparent[ra] = rb
clus = defaultdict(list)
for c in used_cells:
    clus[cfind(c)].append(c)
cname = {}
for root, cells in clus.items():
    big = max(cells, key=lambda q: used_cells[q])
    for c in cells:
        cname[c] = f"M[{big[0]},{big[1]}]x{len(cells)}"
print(f"residual (unregistered) tris {NG - n_reg} in {len(used_cells)} atlas cells -> "
      f"{len(clus)} MERGED clusters (sizes "
      f"{sorted((len(v) for v in clus.values()), reverse=True)[:8]})")

s_reg = [g_reg[i] for i in range(NG)]
s_mrg = [g_reg[i] or cname[g_cell[i]] for i in range(NG)]
s_str = [g_reg[i] or f"A[{g_cell[i][0]},{g_cell[i][1]}]" for i in range(NG)]
set_tris = Counter(s_str)
set_mean_rgb = {}
for s in set(s_str) | set(s_mrg):
    idxs = [i for i in range(NG) if s_str[i] == s or s_mrg[i] == s]
    if idxs:
        set_mean_rgb[s] = np.mean([g_rgb[i] for i in idxs], axis=0)

# ============================================================================================
# PASS 2 -- the boundary census (candidate = STRICT-different)
# ============================================================================================
def near(cls, m, R):
    cx, cz = int(math.floor(m[0] / 4.0)), int(math.floor(m[2] / 4.0))
    rr = int(R // 4) + 1
    g = feat[cls]
    best = R + 1.0
    for i in range(cx - rr, cx + rr + 1):
        for j in range(cz - rr, cz + rr + 1):
            for (px, pz) in g.get((i, j), ()):
                d = math.hypot(px - m[0], pz - m[2])
                if d < best:
                    best = d
                    if best < 0.05:
                        return best
    return best


def local_ground(m):
    cx, cz = int(math.floor(m[0] / 4.0)), int(math.floor(m[2] / 4.0))
    ylo, yhi, sl = 1e9, -1e9, 0.0
    for i in range(cx - 1, cx + 2):
        for j in range(cz - 1, cz + 2):
            r = gcell.get((i, j))
            if r:
                ylo = min(ylo, r[0])
                yhi = max(yhi, r[1])
                sl = max(sl, r[2])
    return (0.0 if ylo > yhi else yhi - ylo), sl


ALTW = lambda t: ("plateau" if t in PLATEAU_TOPO else                            # noqa: E731
                  "shelf" if t in SHELF_TOPO else "lowland")
R_MAIN, R_WIDE, LEVEL_YRANGE = 4.0, 8.0, 4.0

# ---- same-set PATCH components first: a boundary edge's two sides each belong to a patch, and
# ---- "does stock draw a family boundary ACROSS an open field, or only AROUND a small patch?"
# ---- is answered by the patch EXTENT on the two sides.
parent = {}


def find(x):
    while parent.setdefault(x, x) != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


for e, owners in edge_ground.items():
    if len(owners) == 2 and s_str[owners[0]] == s_str[owners[1]]:
        ra, rb = find(owners[0]), find(owners[1])
        if ra != rb:
            parent[ra] = rb
comps = defaultdict(list)
for i in range(NG):
    comps[find(i)].append(i)
p_ext = [0.0] * NG
p_n = [0] * NG
per_set = defaultdict(list)
for tl in comps.values():
    xs = [p[0] for i in tl for p in g_v[i]]
    zs = [p[2] for i in tl for p in g_v[i]]
    ext = max(max(xs) - min(xs), max(zs) - min(zs))
    for i in tl:
        p_ext[i] = ext
        p_n[i] = len(tl)
    per_set[s_str[tl[0]]].append((len(tl), ext))

bnd = []
ctrl_uvjump, ctrl_dL, ctrl_dE = [], [], []
ctrl_dL_by_set = defaultdict(list)
nbr = defaultdict(Counter)                                  # registered-set neighbour matrix
n_multi = 0
for e, owners in edge_ground.items():
    if len(owners) < 2:
        continue
    if len(owners) > 2:
        n_multi += 1
        continue
    a, b = owners
    pa, pb = e
    dL = abs(lum(g_rgb[a]) - lum(g_rgb[b]))
    dE = float(np.linalg.norm(g_rgb[a] - g_rgb[b]))
    if s_reg[a] and s_reg[b]:
        nbr[s_reg[a]][s_reg[b]] += 1
        nbr[s_reg[b]][s_reg[a]] += 1

    def uv_jump(ai, bi):
        out = []
        for p in (pa, pb):
            ua = [g_uv[ai][i] for i in range(3) if kk(g_v[ai][i]) == p]
            ub = [g_uv[bi][i] for i in range(3) if kk(g_v[bi][i]) == p]
            if ua and ub:
                out.append(math.hypot(ua[0][0] - ub[0][0], ua[0][1] - ub[0][1]))
        return out

    if s_str[a] == s_str[b]:
        ctrl_uvjump += uv_jump(a, b)
        ctrl_dL.append(dL)
        ctrl_dE.append(dE)
        ctrl_dL_by_set[s_str[a]].append(dL)
        continue

    m = ((pa[0] + pb[0]) / 2.0, (pa[1] + pb[1]) / 2.0, (pa[2] + pb[2]) / 2.0)
    yr, mslope = local_ground(m)
    fa, fb = g_fam[a], g_fam[b]
    bnd.append(dict(
        e=e, L=math.dist(pa, pb), fa=fa, fb=fb, fpair=tuple(sorted((fa, fb))),
        sr=(s_reg[a], s_reg[b]), sm=tuple(sorted((s_mrg[a], s_mrg[b]))),
        ss=tuple(sorted((s_str[a], s_str[b]))),
        reg=bool(s_reg[a] and s_reg[b] and s_reg[a] != s_reg[b]),
        mrg=(s_mrg[a] != s_mrg[b]), intra=(fa == fb),
        d_rock=near("rock", m, R_WIDE), d_coast=near("coast", m, R_WIDE),
        d_water=near("water", m, R_WIDE), d_forest=near("forest", m, R_WIDE),
        d_obj=near("object", m, R_WIDE),
        on_border=any(abs(p[0] / 64.0 - round(p[0] / 64.0)) < 1e-3 or
                      abs(p[2] / 64.0 - round(p[2] / 64.0)) < 1e-3 for p in e),
        level=(ALTW(g_topo[a]) != ALTW(g_topo[b])) or yr >= LEVEL_YRANGE,
        yrange=yr, mslope=mslope, eslope=max(g_slope[a], g_slope[b]),
        dy=abs(pa[1] - pb[1]), dL=dL, dE=dE, uvj=uv_jump(a, b), mid=m,
        ext_min=min(p_ext[a], p_ext[b]), ext_max=max(p_ext[a], p_ext[b]),
        n_min=min(p_n[a], p_n[b])))


def classify(r, R):
    if r["fa"] == "forest" or r["fb"] == "forest" or r["d_forest"] <= R:
        return "forest"
    if r["d_rock"] <= R:
        return "rock_foot"
    if r["fa"] == "shore" or r["fb"] == "shore" or r["d_coast"] <= R:
        return "coast"
    if r["d_water"] <= R:
        return "water"
    if r["d_obj"] <= R:
        return "object"
    if r["level"]:
        return "level"
    if r["on_border"]:
        return "block_border"
    return "NOTHING"


for r in bnd:
    r["cls"] = classify(r, R_MAIN)
    r["cls_wide"] = classify(r, R_WIDE)

TIERS = dict(R=[r for r in bnd if r["reg"]],
             M=[r for r in bnd if r["mrg"]],
             S=bnd)
print(f"\ncandidate edges (STRICT-different art set) {len(bnd)}; within-cell control edges "
      f"{len(ctrl_dL)}; >2-owner edges skipped {n_multi}")

print("\n== B2 THE BOUNDARY CENSUS -- co-location of every art-set boundary edge")
CLS = ["rock_foot", "coast", "forest", "level", "water", "object", "block_border", "NOTHING"]
tier_out = {}
for tag, rs in (("R  REGISTERED-only (headline)", TIERS["R"]),
                ("M  MERGED residuals (lower bound)", TIERS["M"]),
                ("S  STRICT per-atlas-cell (upper bound)", TIERS["S"])):
    tot = sum(r["L"] for r in rs)
    L = Counter()
    N = Counter()
    for r in rs:
        L[r["cls"]] += r["L"]
        N[r["cls"]] += 1
    Lw = Counter()
    for r in rs:
        Lw[r["cls_wide"]] += r["L"]
    print(f"\n   TIER {tag}: {len(rs)} edges, {tot:.0f}u")
    for c in CLS:
        if N[c]:
            print(f"      {c:13s} {L[c]:9.0f}u {L[c] / max(1e-9, tot):6.1%}  "
                  f"({N[c]:5d} edges)   [R=8u: {Lw[c] / max(1e-9, tot):5.1%}]")
    intra = sum(r["L"] for r in rs if r["intra"])
    print(f"      INTRA-family (same biome, different art set) {intra:.0f}u "
          f"{intra / max(1e-9, tot):.1%}")
    tier_out[tag.split()[0]] = dict(
        edges=len(rs), length=round(tot, 1), intra_length=round(intra, 1),
        by_class={c: dict(length=round(L[c], 1), edges=N[c],
                          share=round(L[c] / max(1e-9, tot), 4)) for c in CLS if N[c]},
        by_class_wide={c: round(Lw[c] / max(1e-9, tot), 4) for c in CLS if Lw[c]})

print("\n   top REGISTERED-tier pairs by boundary length:")
pl = Counter()
for r in TIERS["R"]:
    pl[tuple(sorted(r["sr"]))] += r["L"]
top_pairs = []
for p, l in pl.most_common(14):
    rs = [r for r in TIERS["R"] if tuple(sorted(r["sr"])) == p]
    cc = Counter(r["cls"] for r in rs)
    nl = sum(q["L"] for q in rs if q["cls"] == "NOTHING")
    print(f"      {p[0]:14s}|{p[1]:14s} {l:8.0f}u n={len(rs):5d}  dL med "
          f"{pct([r['dL'] for r in rs], 50):5}  NOTHING {nl / max(1e-9, l):5.1%}  "
          f"cls {dict(cc.most_common(3))}")
    top_pairs.append(dict(pair=list(p), length=round(l, 1), edges=len(rs),
                          dL_med=pct([r["dL"] for r in rs], 50),
                          nothing_share=round(nl / max(1e-9, l), 4),
                          cls=dict(cc.most_common(4))))

# ============================================================================================
# B3 -- THE "NOTHING" SET (per tier)
# ============================================================================================
print("\n== B3 THE 'NOTHING' BOUNDARIES (no feature within 4u, no level change, "
      "not on a block line)")
noth_out = {}
for tag in ("R", "M", "S"):
    rs = TIERS[tag]
    tot = sum(r["L"] for r in rs)
    noth = [r for r in rs if r["cls"] == "NOTHING"]
    nw = [r for r in rs if r["cls_wide"] == "NOTHING"]
    NL = sum(r["L"] for r in noth)
    print(f"\n   TIER {tag}: {len(noth)} edges, {NL:.0f}u = {NL / max(1e-9, tot):.1%} of "
          f"that tier's boundary; at R=8u {sum(r['L'] for r in nw):.0f}u "
          f"({sum(r['L'] for r in nw) / max(1e-9, tot):.1%})")
    if not noth:
        noth_out[tag] = dict(edges=0, length=0.0)
        continue
    print(f"      local ground slope (max tri in ~12u): {dist([r['mslope'] for r in noth], 'deg')}")
    print(f"      the two tris' own slope:              {dist([r['eslope'] for r in noth], 'deg')}")
    print(f"      local y-range (~12u window):          {dist([r['yrange'] for r in noth], 'u')}")
    print(f"      |dy| across the edge:                 {dist([r['dy'] for r in noth], 'u')}")
    print(f"      nearest rock {dist([r['d_rock'] for r in noth], 'u')}")
    print(f"      luminance step dL {dist([r['dL'] for r in noth])}")
    nb = Counter((int(r["mid"][0] // 64), int(-r["mid"][2] // 64)) for r in noth)
    print(f"      spread over {len(nb)} of {len(BLOCKS)} blocks; top "
          f"{[(b, n) for b, n in nb.most_common(6)]}; top-5 share "
          f"{sum(n for _, n in nb.most_common(5)) / max(1, sum(nb.values())):.1%}")
    pc = Counter(tuple(sorted(r["ss"])) for r in noth)
    for p, n in pc.most_common(6):
        rr = [q for q in noth if tuple(sorted(q["ss"])) == p]
        print(f"      pair {p[0]:14s}|{p[1]:14s} n={n:5d} {sum(q['L'] for q in rr):7.0f}u "
              f"dL med {pct([q['dL'] for q in rr], 50)} intra={rr[0]['intra']}")

    # coherence: chains, straightness, turn -- does the boundary read as a LINE?
    adj = defaultdict(set)
    for r in noth:
        a, b = r["e"]
        adj[a].add(b)
        adj[b].add(a)
    seen_e = set()
    chains = []
    for a in list(adj):
        for b in list(adj[a]):
            if frozenset((a, b)) in seen_e:
                continue
            ch = [a, b]
            seen_e.add(frozenset((a, b)))
            while True:
                nxt = [q for q in adj[ch[-1]] if frozenset((ch[-1], q)) not in seen_e]
                if not nxt:
                    break
                seen_e.add(frozenset((ch[-1], nxt[0])))
                ch.append(nxt[0])
            chains.append(ch)
    clen = [sum(math.dist(ch[i], ch[i + 1]) for i in range(len(ch) - 1)) for ch in chains]
    straight = [math.dist(ch[0], ch[-1]) / L for ch, L in zip(chains, clen) if L > 4.0]
    turns = []
    for ch in chains:
        for i in range(1, len(ch) - 1):
            v1 = (ch[i][0] - ch[i - 1][0], ch[i][2] - ch[i - 1][2])
            v2 = (ch[i + 1][0] - ch[i][0], ch[i + 1][2] - ch[i][2])
            L1 = math.hypot(*v1)
            L2 = math.hypot(*v2)
            if L1 > 1e-6 and L2 > 1e-6:
                turns.append(math.degrees(math.acos(max(-1.0, min(1.0,
                             (v1[0] * v2[0] + v1[1] * v2[1]) / (L1 * L2))))))
    print(f"      CHAINS {len(chains)}: length {dist(clen, 'u')} max {max(clen):.0f}u; "
          f"single-edge {sum(1 for c in chains if len(c) == 2) / max(1, len(chains)):.1%}; "
          f"CLOSED loops {sum(1 for c in chains if c[0] == c[-1]) / max(1, len(chains)):.1%}")
    print(f"      straightness (end-to-end / path, chains >4u): {dist(straight)}")
    print(f"      plan turn per interior node: {dist(turns, 'deg')}; "
          f">60deg {sum(1 for t in turns if t > 60) / max(1, len(turns)):.1%}")
    # PATCH PERIMETER vs PARTITION LINE: the SMALLER side's same-set patch extent
    em = [r["ext_min"] for r in noth]
    print(f"      the SMALLER side's same-set patch extent: {dist(em, 'u')}; "
          f"<=16u {sum(1 for q in em if q <= 16.0) / len(em):.1%}  "
          f"<=32u {sum(1 for q in em if q <= 32.0) / len(em):.1%}  "
          f">64u {sum(1 for q in em if q > 64.0) / len(em):.1%}")
    print(f"      the SMALLER side's patch tri count: {dist([r['n_min'] for r in noth])}")
    noth_extra = dict(ext_min=dict(med=pct(em, 50), p90=pct(em, 90),
                                   le16=round(sum(1 for q in em if q <= 16.0) / len(em), 4),
                                   le32=round(sum(1 for q in em if q <= 32.0) / len(em), 4),
                                   gt64=round(sum(1 for q in em if q > 64.0) / len(em), 4)),
                      n_min_med=pct([r["n_min"] for r in noth], 50),
                      closed_loop_frac=round(sum(1 for c in chains if c[0] == c[-1]) /
                                             max(1, len(chains)), 3))
    noth_out[tag] = dict(
        edges=len(noth), length=round(NL, 1), share=round(NL / max(1e-9, tot), 4),
        length_wide=round(sum(r["L"] for r in nw), 1),
        mslope=dict(med=pct([r["mslope"] for r in noth], 50),
                    p90=pct([r["mslope"] for r in noth], 90)),
        eslope_med=pct([r["eslope"] for r in noth], 50),
        yrange_med=pct([r["yrange"] for r in noth], 50),
        dL=dict(med=pct([r["dL"] for r in noth], 50), p90=pct([r["dL"] for r in noth], 90)),
        blocks=len(nb), top5_share=round(sum(n for _, n in nb.most_common(5)) /
                                         max(1, sum(nb.values())), 4),
        top_blocks=[[list(b), n] for b, n in nb.most_common(8)],
        pairs=[dict(pair=list(p), n=n) for p, n in pc.most_common(8)],
        chains=dict(n=len(chains), med=pct(clen, 50), p90=pct(clen, 90),
                    max=round(max(clen), 1),
                    single=round(sum(1 for c in chains if len(c) == 2) / max(1, len(chains)), 3)),
        straightness_med=pct(straight, 50), turn_med=pct(turns, 50), **noth_extra)

# ============================================================================================
# B4 -- TRANSITION VOCABULARY
# ============================================================================================
print("\n== B4 IS THERE A TRANSITION VOCABULARY?")
set_bnd_edges = Counter()
for r in bnd:
    set_bnd_edges[r["ss"][0]] += 1
    set_bnd_edges[r["ss"][1]] += 1
set_all_edges = Counter()
for e, owners in edge_ground.items():
    for gi in owners:
        set_all_edges[s_str[gi]] += 1
rows = []
for s in REGISTERED:
    n = set_tris.get(s, 0)
    if n < 40:
        continue
    be, ae = set_bnd_edges.get(s, 0), max(1, set_all_edges.get(s, 0))
    rows.append((be / ae, s, n, be, ae))
base = sum(r[3] for r in rows) / max(1, sum(r[4] for r in rows))
print(f"   REGISTERED sets -- share of a set's tri-edges that are art-set boundaries "
      f"(base {base:.1%}):")
for frac, s, n, be, ae in sorted(rows, reverse=True):
    rgb = set_mean_rgb[s]
    ic = ctrl_dL_by_set.get(s, [])
    print(f"      {s:14s} tris {n:6d}  boundary-edge share {frac:6.1%} "
          f"(x{frac / max(1e-9, base):4.1f})  L={lum(rgb):5.1f}  "
          f"OWN internal dL med {pct(ic, 50)} p90 {pct(ic, 90)}")

print("\n   the REGISTERED-set NEIGHBOUR matrix (shared edges; diagonal = within-set):")
regs = [s for _, s, _, _, _ in sorted(rows, reverse=True)]
print("      " + "".join(f"{s.split('.')[0][:6]:>8s}" for s in regs))
for s in regs:
    print(f"      {s:14s}" + "".join(f"{nbr[s].get(q, 0):8d}" for q in regs))

print("\n   INTERPOSITION -- for each family pair, direct main|main vs a third set between:")
fpl = Counter()
for r in bnd:
    fpl[r["fpair"]] += r["L"]
touch = defaultdict(set)
for r in bnd:
    touch[r["ss"][0]].add(r["fb"] if r["ss"][0] == r["ss"][0] else r["fa"])
touch = defaultdict(set)
for r in bnd:
    a, b = r["e"]
    touch[r["ss"][0]].add(r["fa"])
    touch[r["ss"][0]].add(r["fb"])
    touch[r["ss"][1]].add(r["fa"])
    touch[r["ss"][1]].add(r["fb"])
interp = []
for fp, l in fpl.most_common(12):
    fa, fb = fp
    if fa == fb:
        continue
    direct = sum(r["L"] for r in bnd if r["fpair"] == fp and r["reg"]
                 and set(r["sr"]) == {f"{fa}.main", f"{fb}.main"})
    mids = sorted(s for s, fs in touch.items() if {fa, fb} <= fs
                  and not s.startswith(fa) and not s.startswith(fb))
    print(f"      {fa:8s}|{fb:8s} total {l:8.0f}u  direct main|main {direct:8.0f}u "
          f"({direct / max(1e-9, l):5.1%})  sets touching BOTH: {mids[:5]}")
    interp.append(dict(pair=[fa, fb], total=round(l, 1), direct_main=round(direct, 1),
                       mids=mids[:8]))

# ============================================================================================
# B5 / B6
# ============================================================================================
bj = [x for r in bnd for x in r["uvj"]]
bjr = [x for r in TIERS["R"] for x in r["uvj"]]
print("\n== B5 UV PHASE ACROSS THE BOUNDARY (|d uv| between the two tris at the SHARED verts)")
print(f"   REGISTERED-set boundaries: {dist(bjr)}")
print(f"   any art-set boundary:      {dist(bj)}")
print(f"   WITHIN one atlas cell (control): {dist(ctrl_uvjump)}")
for nm, a in (("registered boundary", bjr), ("within-cell", ctrl_uvjump)):
    if a:
        print(f"      {nm}: CONTINUOUS (<0.0005) {sum(1 for q in a if q < 0.0005) / len(a):.1%}; "
              f">0.01 {sum(1 for q in a if q > 0.01) / len(a):.1%}")

print("\n== B6 THE VISIBLE STEP (real atlas pixels, L in 0-255)")
print(f"   WITHIN one atlas cell (control): dL {dist(ctrl_dL)} | dE med {pct(ctrl_dE, 50)}")
print(f"   REGISTERED-set boundaries:      dL {dist([r['dL'] for r in TIERS['R']])} | "
      f"dE med {pct([r['dE'] for r in TIERS['R']], 50)}")
step_by_cls = {}
for c in CLS:
    rs = [r for r in TIERS["R"] if r["cls"] == c]
    if rs:
        step_by_cls[c] = dict(dL_med=pct([r["dL"] for r in rs], 50),
                              dL_p90=pct([r["dL"] for r in rs], 90),
                              dE_med=pct([r["dE"] for r in rs], 50), n=len(rs))
        print(f"   {c:13s} dL {dist([r['dL'] for r in rs])} | dE med "
              f"{pct([r['dE'] for r in rs], 50)}")

# ============================================================================================
# B7 -- THE DONOR / BENCH CASE
# ============================================================================================
print("\n== B7 THE DONOR / BENCH CASE")
donor = Counter(s_str[i] for i in range(NG)
                if 15 * 64 <= g_v[i][0][0] < 16 * 64 and -15 * 64 <= g_v[i][0][2] < -14 * 64)
dtot = max(1, sum(donor.values()))
print("   block (15,14) ground art sets (the mesa donor):")
for s, n in donor.most_common(8):
    print(f"      {s:14s} {n:5d} tris {n / dtot:6.1%}  L={lum(set_mean_rgb[s]):5.1f}")
b7 = {}
for pair in (("grass.main", "grass.D"), ("grass.main", "grass.B"), ("grass.B", "grass.D")):
    key = tuple(sorted(pair))
    rs = [r for r in TIERS["R"] if tuple(sorted(r["sr"])) == key]
    dLm = abs(lum(set_mean_rgb[pair[0]]) - lum(set_mean_rgb[pair[1]]))
    dEm = float(np.linalg.norm(set_mean_rgb[pair[0]] - set_mean_rgb[pair[1]]))
    cc = Counter(r["cls"] for r in rs)
    nl = sum(r["L"] for r in rs if r["cls"] == "NOTHING")
    tl = sum(r["L"] for r in rs)
    print(f"   {pair[0]}|{pair[1]}: set-mean dL {dLm:.1f} dE {dEm:.1f}; stock has "
          f"{len(rs)} edges / {tl:.0f}u; cls {dict(cc.most_common(4))}; "
          f"NOTHING {nl / max(1e-9, tl):.1%}" if rs else
          f"   {pair[0]}|{pair[1]}: set-mean dL {dLm:.1f} dE {dEm:.1f}; "
          f"stock has ZERO such boundary edges map-wide")
    b7[f"{pair[0]}|{pair[1]}"] = dict(set_dL=round(dLm, 1), set_dE=round(dEm, 1),
                                      stock_edges=len(rs), stock_length=round(tl, 1),
                                      cls=dict(cc.most_common(5)),
                                      nothing_share=round(nl / max(1e-9, tl), 4) if rs else None)

print("\n== B7b ART-SET PATCH FORM (contiguous same-set components, map-wide)")
patches = {}
for s in sorted(per_set, key=lambda q: -sum(a for a, _ in per_set[q]))[:14]:
    v = per_set[s]
    print(f"      {s:14s} {len(v):5d} patches; tris med {pct([a for a, _ in v], 50)} "
          f"max {max(a for a, _ in v)}; extent med {pct([b for _, b in v], 50)}u "
          f"max {max(b for _, b in v):.0f}u")
    patches[s] = dict(n=len(v), tris_med=pct([a for a, _ in v], 50),
                      tris_max=max(a for a, _ in v), extent_med=pct([b for _, b in v], 50),
                      extent_max=round(max(b for _, b in v), 1))

# ============================================================================================
# RENDER
# ============================================================================================
OUTDIR.mkdir(parents=True, exist_ok=True)
SC = 0.55
W_, H_ = int(24 * 64 * SC) + 2, int(20 * 64 * SC) + 2
img = Image.new("RGB", (W_, H_ + 150), (18, 20, 24))
dr = ImageDraw.Draw(img)
M = lambda x, z: (1 + x * SC, 1 + (-z) * SC)                 # noqa: E731
FCOL = dict(grass=(44, 70, 38), desert=(94, 80, 52), scrub=(60, 76, 44),
            snow=(118, 124, 132), canyon=(94, 52, 44), brush=(74, 66, 42),
            dunes=(102, 94, 64), forest=(26, 46, 28), shore=(108, 102, 80))
for i in range(NG):
    dr.polygon([M(p[0], p[2]) for p in g_v[i]], fill=FCOL.get(g_fam[i], (60, 60, 60)))
CCOL = dict(rock_foot=(150, 150, 158), coast=(70, 130, 210), forest=(60, 190, 90),
            level=(210, 165, 60), water=(60, 200, 210), object=(190, 90, 200),
            block_border=(110, 110, 110), NOTHING=(255, 55, 55))
for r in sorted(TIERS["R"], key=lambda q: q["cls"] == "NOTHING"):
    a, b = r["e"]
    dr.line([M(a[0], a[2]), M(b[0], b[2])], fill=CCOL.get(r["cls"], (255, 255, 255)),
            width=3 if r["cls"] == "NOTHING" else 1)
yy = H_ + 6
totR = sum(r["L"] for r in TIERS["R"])
dr.text((6, yy), "STOCK DISC-1 -- GROUND ART-SET BOUNDARIES, REGISTERED TIER  "
                 f"({len(TIERS['R'])} edges, {totR:.0f}u).  fill = biome family; "
                 "line colour = CO-LOCATION", fill=(232, 232, 232))
yy += 16
Lr = Counter()
Nr = Counter()
for r in TIERS["R"]:
    Lr[r["cls"]] += r["L"]
    Nr[r["cls"]] += 1
for c, l in Lr.most_common():
    dr.rectangle([6, yy + 3, 22, yy + 11], fill=CCOL.get(c, (255, 255, 255)))
    dr.text((28, yy), f"{c}   {l:.0f}u   {l / max(1e-9, totR):.1%}   ({Nr[c]} edges)",
            fill=(212, 212, 216))
    yy += 13
img.save(PNG)
print(f"\nrender -> {PNG}")

OUT.write_text(json.dumps(dict(
    population=dict(blocks=len(BLOCKS), all_tris=n_all_tris, ground_tris=NG,
                    registry_coverage=round(n_reg / max(1, NG), 4),
                    open_edges=n_open, open_on_block_line=n_open_on_border,
                    residual_atlas_cells=len(used_cells), merged_clusters=len(clus),
                    read_secs=round(t_read, 1)),
    sets={s: dict(tris=n, L=round(float(lum(set_mean_rgb[s])), 1),
                  rgb=[round(float(q), 1) for q in set_mean_rgb[s]])
          for s, n in set_tris.most_common(30)},
    fam_tris=dict(fam_tris),
    tiers=tier_out,
    top_pairs_registered=top_pairs,
    nothing=noth_out,
    neighbour_matrix={s: dict(nbr[s]) for s in regs},
    interposition=interp,
    uv=dict(registered_boundary=dict(med=pct(bjr, 50), p90=pct(bjr, 90),
                                     continuous=round(sum(1 for q in bjr if q < 0.0005) /
                                                      max(1, len(bjr)), 4)),
            within_cell=dict(med=pct(ctrl_uvjump, 50), p90=pct(ctrl_uvjump, 90),
                             continuous=round(sum(1 for q in ctrl_uvjump if q < 0.0005) /
                                              max(1, len(ctrl_uvjump)), 4))),
    step=dict(within_cell=dict(dL_med=pct(ctrl_dL, 50), dL_p90=pct(ctrl_dL, 90),
                               dE_med=pct(ctrl_dE, 50)),
              registered_boundary=dict(dL_med=pct([r["dL"] for r in TIERS["R"]], 50),
                                       dL_p90=pct([r["dL"] for r in TIERS["R"]], 90),
                                       dE_med=pct([r["dE"] for r in TIERS["R"]], 50)),
              by_class=step_by_cls,
              per_set_internal={s: dict(dL_med=pct(v, 50), dL_p90=pct(v, 90))
                                for s, v in ctrl_dL_by_set.items() if s in REGISTERED}),
    donor_15_14=dict(donor.most_common(12)),
    our_pairs=b7,
    patches=patches,
), indent=0))
print(f"artifacts -> {OUT}")
print(f"total runtime {time.time() - t0:.0f}s")
