"""ISLAND (7,17) -> DESERT: the retile census.

The ladder-mint arc closed (4 rounds, the form lesson again); the approved path is
OPTION 1: transplant FF9's only fully-in-block beach island (7,17) verbatim
(world-transplant, the proven vehicle) and RETILE the carried bytes desert via the
byte-measured translation laws. Every band-level translation is already proven
(GROUNDS mains + wall deltas in-game on the desert bench; SAND_BANDS on all 15 real
desert blocks) -- this census answers the ONE open feasibility question offline:

  does EVERY texture class on (7,17) have a proven translation, and what does the
  unmeasured content (the painted berm, meadow-D, lip rows) translate to?

  A. parts inventory -- which sub-meshes (7,17) carries + per-part topo histograms.
  B. terrain classification -- every tri into: water / sand-31 (SAND_BANDS pins) /
     grass-mains / grass-D (meadow) / wall-band (the ROCK strip) / RESIDUAL
     (per-topo uv bbox report).
  C. beach1/sea parts -- foam language + topos (universal texture per the law;
     what does a real DESERT beach's beach1 carry?).
  D. THE BERM FIT -- (7,17)'s sand back-weld band (non-sand terrain tris
     edge-welded to sand) vs the desert beach blocks' topo-0 back-welds:
     outer-bounds translation fit (the families-census method).
  E. the desert residual screen -- does real desert ground carry content OUTSIDE
     mains+delta (a meadow-D analogue) that a retile would need?

Artifacts -> out/island717_retile.json. Run from the repo root:
    py studies/overworld-topography/island717_retile_census.py
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import grassland as G                  # noqa: E402
from ff9mapkit.world import coastmorph as CM                # noqa: E402

BLOCK = 64.0
OUTD = Path(__file__).with_name("out")
DONOR = (7, 17)
EPS = 0.006                                                  # region-membership slack (uv)
WATER_TOPOS = {53, 54, 55, 56, 57}
GRASS_WALL = ((0.699, 0.947), (0.893, 0.923))                # ROCK_U / sorted ROCK_V
DES = G.GROUNDS["desert"]
DESERT_WALL = ((GRASS_WALL[0][0] + DES["wall_du"], GRASS_WALL[0][1] + DES["wall_du"]),
               (GRASS_WALL[1][0] + DES["wall_dv"], GRASS_WALL[1][1] + DES["wall_dv"]))
out = {}


def load_part(bx, by, part):
    try:
        bm = X.read_block(bx, by, disc=1, part=part)
    except ValueError:
        return None
    tris = []
    for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
        tris.append(dict(
            w=[(bm.verts[j][0] + BLOCK * bx, bm.verts[j][1],
                bm.verts[j][2] - BLOCK * by) for j in tri],
            uv=[(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri],
            topo=X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]))
    return tris


def in_rect(uv, rect, eps=EPS):
    (lo_u, hi_u), (lo_v, hi_v) = rect
    return lo_u - eps <= uv[0] <= hi_u + eps and lo_v - eps <= uv[1] <= hi_v + eps


def tri_rect_class(t, *, fam="grass"):
    """One of mains/D/wall/None for a tri, all three uvs in the region."""
    g = G.GROUNDS[fam]
    m = G.FAM_REGION["main"]
    mains = ((m[0] + g["mains_du"], m[2] + g["mains_du"]),
             (m[1] + g["mains_dv"], m[3] + g["mains_dv"]))
    d = G.FAM_REGION["D"]
    dreg = ((d[0] + g["mains_du"], d[2] + g["mains_du"]),
            (d[1] + g["mains_dv"], d[3] + g["mains_dv"]))
    wall = GRASS_WALL if fam == "grass" else DESERT_WALL
    if all(in_rect(uv, mains) for uv in t["uv"]):
        return "mains"
    if all(in_rect(uv, dreg) for uv in t["uv"]):
        return "D"
    if all(in_rect(uv, wall) for uv in t["uv"]):
        return "wall"
    return None


def sand_class(t, fam):
    """run/cap/conforming for a sand tri under the family's v pins."""
    cls = [CM._sand_vclass(uv[1], fam) for uv in t["uv"]]
    if any(c is None for c in cls):
        return "conforming"
    if all(c.startswith("run") for c in cls):
        return "run"
    if all(c.startswith("cap") for c in cls):
        return "cap"
    return "mixed-tier"


def bbox(uvs):
    us = [u for u, _ in uvs]
    vs = [v for _, v in uvs]
    return [round(min(us), 5), round(min(vs), 5), round(max(us), 5), round(max(vs), 5)]


# ---- A. parts inventory ------------------------------------------------------------------------
print(f"== A. (7,17) parts inventory")
parts = {}
for part in ("terrain", "object", "beach1", "beach2", "sea1", "sea2", "sea3", "sea4", "sea5"):
    tris = load_part(*DONOR, part)
    if tris is None:
        continue
    parts[part] = tris
    topos = Counter(t["topo"] for t in tris)
    print(f"   {part:8s} {len(tris):5d} tris  topos {dict(topos.most_common())}")
out["parts"] = {p: dict(Counter(t["topo"] for t in ts).most_common()) for p, ts in parts.items()}

# ---- B. terrain classification -----------------------------------------------------------------
print(f"\n== B. terrain classification (grass regions)")
terr = parts["terrain"]
sand_fam_g = CM.SAND_BANDS["grass"]
classes = defaultdict(list)
for ti, t in enumerate(terr):
    if t["topo"] in WATER_TOPOS:
        classes["water"].append(ti)
    elif t["topo"] == sand_fam_g["topo"]:
        classes[f"sand:{sand_class(t, sand_fam_g)}"].append(ti)
    else:
        rc = tri_rect_class(t)
        if rc:
            classes[f"{rc}:t{t['topo']}"].append(ti)
        else:
            classes[f"RESIDUAL:t{t['topo']}"].append(ti)
for name in sorted(classes):
    tl = classes[name]
    uvs = [uv for ti in tl for uv in terr[ti]["uv"]]
    print(f"   {name:16s} {len(tl):4d} tris  uv-bbox {bbox(uvs)}")
out["terrain_classes"] = {k: len(v) for k, v in classes.items()}
res_detail = {}
for name in [k for k in classes if k.startswith("RESIDUAL")]:
    tl = classes[name]
    uvs = [uv for ti in tl for uv in terr[ti]["uv"]]
    ys = [p[1] for ti in tl for p in terr[ti]["w"]]
    res_detail[name] = dict(n=len(tl), uv_bbox=bbox(uvs),
                            y=[round(min(ys), 2), round(max(ys), 2)])
out["residual_detail"] = res_detail

# ---- C. beach1 on (7,17) vs a real desert beach ------------------------------------------------
print(f"\n== C. beach1 -- (7,17) vs real desert beach blocks")
b1 = parts.get("beach1") or []
print(f"   (7,17) beach1: {len(b1)} tris, topos {dict(Counter(t['topo'] for t in b1))}, "
      f"uv-bbox {bbox([uv for t in b1 for uv in t['uv']])}")
# find the desert beach blocks from the map census (terrain carries topo 32)
desert_blocks = []
for bx in range(24):
    for by in range(20):
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except ValueError:
            continue
        tps = {X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
               for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3)}
        if 32 in tps:
            desert_blocks.append((bx, by))
print(f"   desert (topo-32) beach blocks: {desert_blocks}")
out["desert_blocks"] = [f"{b[0]},{b[1]}" for b in desert_blocks]
db1_topos = Counter()
db1_uvs = []
for blk in desert_blocks:
    dts = load_part(*blk, "beach1") or []
    db1_topos.update(t["topo"] for t in dts)
    db1_uvs += [uv for t in dts for uv in t["uv"]]
print(f"   desert beach1 union: topos {dict(db1_topos)}, "
      f"uv-bbox {bbox(db1_uvs) if db1_uvs else '--'}")
out["desert_beach1_topos"] = dict(db1_topos)

# ---- D. THE BERM FIT ---------------------------------------------------------------------------
print(f"\n== D. THE BERM FIT -- sand back-weld band, grass vs desert")


def back_weld_band(tris, sand_topo):
    """Non-sand terrain tris sharing a rounded edge with a sand tri."""
    kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))
    sand_edges = set()
    for t in tris:
        if t["topo"] != sand_topo:
            continue
        ks = [kk(p) for p in t["w"]]
        for i in range(3):
            sand_edges.add(frozenset((ks[i], ks[(i + 1) % 3])))
    band = []
    for t in tris:
        if t["topo"] == sand_topo:
            continue
        ks = [kk(p) for p in t["w"]]
        if any(frozenset((ks[i], ks[(i + 1) % 3])) in sand_edges for i in range(3)):
            band.append(t)
    return band


g_band = back_weld_band(terr, 31)
g_by_topo = defaultdict(list)
for t in g_band:
    g_by_topo[t["topo"]].append(t)
print(f"   (7,17) back-weld band: {len(g_band)} tris, topos "
      f"{ {tp: len(tl) for tp, tl in g_by_topo.items()} }")
for tp, tl in sorted(g_by_topo.items()):
    uvs = [uv for t in tl for uv in t["uv"]]
    n_mains = sum(1 for t in tl if tri_rect_class(t) == "mains")
    print(f"     topo {tp:2d}: uv-bbox {bbox(uvs)}  ({n_mains}/{len(tl)} classify as grass mains)")
out["berm_grass"] = {str(tp): dict(n=len(tl), uv_bbox=bbox([uv for t in tl for uv in t["uv"]]),
                                   mains=sum(1 for t in tl if tri_rect_class(t) == "mains"))
                     for tp, tl in g_by_topo.items()}

d_band_topo0, d_band_topo17 = [], []
for blk in desert_blocks:
    dts = load_part(*blk, "terrain")
    for t in back_weld_band(dts, 32):
        (d_band_topo0 if t["topo"] == 0 else
         d_band_topo17 if t["topo"] == 17 else []).append(t)
for name, tl in (("topo-0", d_band_topo0), ("topo-17", d_band_topo17)):
    if not tl:
        continue
    uvs = [uv for t in tl for uv in t["uv"]]
    n_mains = sum(1 for t in tl if tri_rect_class(t, fam="desert") == "mains")
    print(f"   desert back-weld {name}: {len(tl)} tris, uv-bbox {bbox(uvs)}  "
          f"({n_mains}/{len(tl)} classify as desert mains)")
out["berm_desert"] = {name: dict(n=len(tl), uv_bbox=bbox([uv for t in tl for uv in t["uv"]]),
                                 mains=sum(1 for t in tl if tri_rect_class(t, fam="desert") == "mains"))
                      for name, tl in (("topo0", d_band_topo0), ("topo17", d_band_topo17)) if tl}

# outer-bounds fit: (7,17) berm topo-0 NON-mains content vs desert non-mains back-welds
g_res = [t for t in g_by_topo.get(0, []) if tri_rect_class(t) != "mains"]
d_res = [t for t in d_band_topo0 + d_band_topo17 if tri_rect_class(t, fam="desert") != "mains"]
if g_res and d_res:
    gb = bbox([uv for t in g_res for uv in t["uv"]])
    db = bbox([uv for t in d_res for uv in t["uv"]])
    print(f"   NON-mains berm outer-bounds: grass {gb} desert {db}")
    print(f"   delta candidates: du [{db[0]-gb[0]:+.5f}, {db[2]-gb[2]:+.5f}] "
          f"dv [{db[1]-gb[1]:+.5f}, {db[3]-gb[3]:+.5f}]")
    out["berm_fit"] = dict(grass=gb, desert=db,
                           du=[round(db[0] - gb[0], 5), round(db[2] - gb[2], 5)],
                           dv=[round(db[1] - gb[1], 5), round(db[3] - gb[3], 5)])

# ---- E. desert residual screen -----------------------------------------------------------------
print(f"\n== E. desert ground residual screen (content outside mains+delta on desert blocks)")
res_ct = Counter()
res_uvs = defaultdict(list)
for blk in desert_blocks:
    dts = load_part(*blk, "terrain")
    for t in dts:
        if t["topo"] in (17, 16, 19, 20):
            if tri_rect_class(t, fam="desert") is None:
                res_ct[t["topo"]] += 1
                res_uvs[t["topo"]] += t["uv"]
        elif t["topo"] not in WATER_TOPOS and t["topo"] not in (32, 0, 58, 49, 50):
            res_ct[f"other:{t['topo']}"] += 1
print(f"   desert-ground tris OUTSIDE mains+delta: {dict(res_ct) or 'NONE'}")
for tp, uvs in res_uvs.items():
    print(f"     topo {tp}: uv-bbox {bbox(uvs)}")
out["desert_residual"] = {str(k): v for k, v in res_ct.items()}

OUTD.mkdir(exist_ok=True)
(OUTD / "island717_retile.json").write_text(json.dumps(out, indent=1, default=str))
print(f"\n-> {OUTD / 'island717_retile.json'}")
