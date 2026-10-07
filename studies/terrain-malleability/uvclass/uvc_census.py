"""uvclass THE DEFORMATION-TOLERANCE CENSUS -- classify every disc-1 Terrain (and Object) tri's UV parameterization
as L / P / W / M (uvc_classify.py) and aggregate: map-wide, per look family, per topo, per block; the 24x20 map;
the mural-dominant (carry-only) vs freely-reshapable block lists; TAU sensitivity.

Inputs : the raw cache (uvc_common.build_cache, OUTSIDE the repo) + out/features_<part>.npz (uvc_features.py).
Outputs: out/census_<part>.json, out/class_map_<part>.png (+ _legend), out/class_blocks_<part>.png
Rerun  : py studies/terrain-malleability/uvclass/uvc_features.py terrain   (once; ~70s)
         py studies/terrain-malleability/uvclass/uvc_census.py terrain      (~20s)   [same with 'object']
"""
import json
import sys
from collections import Counter, defaultdict

import numpy as np
from PIL import Image, ImageDraw

import uvc_common as C
import uvc_classify as K

PART = sys.argv[1] if len(sys.argv) > 1 else "terrain"
d = C.load(1, PART)
z = np.load(C.OUT / f"features_{PART}.npz")
pid, topo, blk, area = z["pid"], z["topo"], z["blk"], z["area"]
UV = d["UV"]
N = len(pid)
rows, order, bounds = K.patch_rows(z)
NP = len(rows)

# decoded-vocabulary vote per patch (terrain atlas only)
uvc = UV.mean(axis=1)
dec_tri = np.array([K.in_decoded(u, v) or "" for u, v in uvc]) if PART == "terrain" else np.array([""] * N)
for p in range(NP):
    tr = order[bounds[p]:bounds[p + 1]]
    names = Counter(dec_tri[tr].tolist())
    top, cnt = names.most_common(1)[0]
    rows[p]["decoded"] = top if (top and cnt * 2 > len(tr)) else None


def run(tau):
    cls = np.empty(NP, dtype=object)
    sub = np.empty(NP, dtype=object)
    for p in range(NP):
        cls[p], sub[p] = K.classify(rows[p], tau)
    return cls[pid], sub[pid]


tri_cls, tri_sub = run(K.TAU)
fam = np.array([C.fam(t) for t in topo])
res = {"part": PART, "tau_px": K.TAU, "tris": int(N), "patches": int(NP), "area_total": float(area.sum())}


def share(mask, labels, keys):
    a = area[mask]
    tot = a.sum()
    out = {}
    for k in keys:
        m = labels[mask] == k
        out[k] = dict(tris=int(m.sum()), area_pct=round(100 * float(a[m].sum()) / max(tot, 1e-9), 2))
    return out


allm = np.ones(N, bool)
res["mapwide_class"] = share(allm, tri_cls, K.CLASSES)
res["mapwide_sub"] = share(allm, tri_sub, K.SUBS)
print(f"[{PART}] map-wide class share (area %):",
      {k: v["area_pct"] for k, v in res["mapwide_class"].items()})
print("  sub:", {k: v["area_pct"] for k, v in res["mapwide_sub"].items() if v["tris"]})

# TAU sensitivity
sens = {}
for tau in (4.0, 8.0, 16.0, 32.0):
    c, s = run(tau)
    sens[str(tau)] = {k: round(100 * float(area[c == k].sum()) / float(area.sum()), 2) for k in K.CLASSES}
res["tau_sensitivity_area_pct"] = sens
print("  TAU sensitivity:", sens)

# per family / per topo
res["per_family"] = {}
for f in sorted(set(fam.tolist()), key=lambda f: -(fam == f).sum()):
    m = fam == f
    res["per_family"][f] = dict(tris=int(m.sum()), cls=share(m, tri_cls, K.CLASSES),
                                sub={k: v for k, v in share(m, tri_sub, K.SUBS).items() if v["tris"]})
res["per_topo"] = {}
for t in sorted(set(topo.tolist())):
    m = topo == t
    res["per_topo"][str(t)] = dict(tris=int(m.sum()), fam=C.fam(t),
                                   cls={k: v["area_pct"] for k, v in share(m, tri_cls, K.CLASSES).items()})
print("\nper family (area %):  L  P  W  M   | dominant subs")
for f, v in res["per_family"].items():
    subs = sorted(v["sub"].items(), key=lambda kv: -kv[1]["area_pct"])[:3]
    print(f"  {f:9s} {v['tris']:6d}  " + " ".join(f"{v['cls'][k]['area_pct']:5.1f}" for k in K.CLASSES)
          + "   " + ", ".join(f"{k} {s['area_pct']}" for k, s in subs))

# per block
blocks = sorted({(int(a), int(b)) for a, b in blk})
per_block = {}
for (bx, by) in blocks:
    m = (blk[:, 0] == bx) & (blk[:, 1] == by)
    a = area[m]
    tot = float(a.sum())
    shares = {k: round(100 * float(a[tri_cls[m] == k].sum()) / tot, 1) for k in K.CLASSES}
    subs = {k: round(100 * float(a[tri_sub[m] == k].sum()) / tot, 1) for k in K.SUBS}
    rock = m & (topo == 49)
    ra = area[rock].sum()
    per_block[f"{bx},{by}"] = dict(tris=int(m.sum()), cls=shares,
                                   sub={k: v for k, v in subs.items() if v},
                                   rock49_tris=int(rock.sum()),
                                   rock49_M_pct=round(100 * float(area[rock & (tri_cls == "M")].sum()) / ra, 1)
                                   if ra else None,
                                   L_rule_pct=subs["L.rule"])
res["per_block"] = per_block

# block verdicts (area-weighted)
#   RULE-RETILEABLE : L.rule + P >= 90%      -- every uv re-derivable by a decoded kit rule / re-projection
#   RESHAPE-FREE    : all L + P >= 90%       -- tile-scale or plan charts: pure-Y + re-decode/carry tiles lawful
#   CARRY-DOMINANT  : M >= 50%               -- most of the block's texture is a free (non-affine, unkeyed) chart
#   MIXED           : the rest
tiers = {}
for k, v in per_block.items():
    LP = v["cls"]["L"] + v["cls"]["P"]
    if v["sub"].get("L.rule", 0) + v["cls"]["P"] >= 90:
        tiers[k] = "RULE-RETILEABLE"
    elif LP >= 90:
        tiers[k] = "RESHAPE-FREE"
    elif v["cls"]["M"] >= 50:
        tiers[k] = "CARRY-DOMINANT"
    else:
        tiers[k] = "MIXED"
    v["tier"] = tiers[k]
for name in ("RULE-RETILEABLE", "RESHAPE-FREE", "CARRY-DOMINANT", "MIXED"):
    res["blocks_" + name] = sorted((k for k, t in tiers.items() if t == name),
                                   key=lambda k: (-per_block[k]["cls"]["M"], k))
print(f"\nblocks: {len(blocks)}  " + "  ".join(f"{n}: {len(res['blocks_' + n])}" for n in
      ("RULE-RETILEABLE", "RESHAPE-FREE", "CARRY-DOMINANT", "MIXED")))
for n in ("RULE-RETILEABLE", "RESHAPE-FREE", "CARRY-DOMINANT"):
    print(f"  {n}: {res['blocks_' + n]}")
# THE INTERIOR KB OPEN QUESTION #1 -- murals vs tiles per HIGHLAND block (topo 49 only, blocks with >= 20 rock tris):
#   rock area share by class: M (free chart, carry-only) vs W.keyed (role-keyed courses = a tile language) vs other
hl = {}
for k, v in per_block.items():
    bx, by = map(int, k.split(","))
    m = (blk[:, 0] == bx) & (blk[:, 1] == by) & (topo == 49)
    if m.sum() < 20:
        continue
    a = area[m]
    tot = float(a.sum())
    hl[k] = dict(rock_tris=int(m.sum()),
                 M=round(100 * float(a[tri_cls[m] == "M"].sum()) / tot, 1),
                 W_keyed=round(100 * float(a[tri_sub[m] == "W.keyed"].sum()) / tot, 1),
                 L=round(100 * float(a[tri_cls[m] == "L"].sum()) / tot, 1))
res["highland_rock_by_block"] = hl
res["highland_mural_rock_M_ge_80"] = sorted((k for k, v in hl.items() if v["M"] >= 80), key=lambda k: -hl[k]["rock_tris"])
res["highland_tiled_rock_keyed_or_L_ge_50"] = sorted((k for k, v in hl.items() if v["W_keyed"] + v["L"] >= 50),
                                                    key=lambda k: -hl[k]["rock_tris"])
Ms = np.array([v["M"] for v in hl.values()])
print(f"\nhighland blocks (>=20 topo-49 tris): {len(hl)}; rock M-share p10/p50/p90 "
      f"{np.percentile(Ms, 10):.0f}/{np.percentile(Ms, 50):.0f}/{np.percentile(Ms, 90):.0f}%; "
      f"mural rock (M>=80%): {len(res['highland_mural_rock_M_ge_80'])}; tiled rock (keyed+L>=50%): "
      f"{len(res['highland_tiled_rock_keyed_or_L_ge_50'])} -> {res['highland_tiled_rock_keyed_or_L_ge_50']}")

# ---- the map ---------------------------------------------------------------------------------------
COL = {"L.rule": (60, 170, 60), "L.free": (150, 210, 110), "L.keyed": (20, 110, 60), "W.keyed": (255, 120, 0), "P.chart": (70, 120, 220), "P.oblique": (120, 160, 235),
       "P.unique": (40, 60, 160), "P.unfit": (170, 190, 240), "W.proj": (235, 160, 40), "W.arc": (245, 200, 80),
       "W.oblique": (210, 130, 30), "W.unfit": (250, 220, 150), "M.smooth": (190, 80, 200), "M.flow": (200, 40, 40),
       "M.free": (120, 20, 20), "M.unique": (40, 0, 0)}
if PART == "terrain":
    S = 1.0                                             # px per world unit -> 1536 x 1280
    img = Image.new("RGB", (int(24 * 64 * S), int(20 * 64 * S)), (18, 30, 48))
    dr = ImageDraw.Draw(img)
    P = d["P"]
    zord = np.argsort(P[:, :, 1].mean(1))              # low first so walls/tops paint over
    for t in zord:
        pts = [(float(P[t, k, 0] * S), float(-P[t, k, 2] * S)) for k in range(3)]
        dr.polygon(pts, fill=COL[tri_sub[t]])
    for i in range(25):
        dr.line([(i * 64 * S, 0), (i * 64 * S, 20 * 64 * S)], fill=(0, 0, 0), width=1)
    for j in range(21):
        dr.line([(0, j * 64 * S), (24 * 64 * S, j * 64 * S)], fill=(0, 0, 0), width=1)
    img.save(C.OUT / "class_map_terrain.png")
    # block-level dominant-class grid
    g = Image.new("RGB", (24 * 40, 20 * 40), (18, 30, 48))
    gd = ImageDraw.Draw(g)
    BC = {"L": (60, 170, 60), "P": (70, 120, 220), "W": (235, 160, 40), "M": (200, 40, 40)}
    for k, v in per_block.items():
        bx, by = map(int, k.split(","))
        x0, y0 = bx * 40, by * 40
        acc = 0.0
        for c in K.CLASSES:                              # stacked bar inside the cell = class mix
            h = v["cls"][c] / 100 * 38
            gd.rectangle([x0 + 1, y0 + 1 + acc, x0 + 39, y0 + 1 + acc + h], fill=BC[c])
            acc += h
        gd.text((x0 + 3, y0 + 2), f"{bx},{by}", fill=(255, 255, 255))
    g.save(C.OUT / "class_blocks_terrain.png")
    leg = Image.new("RGB", (260, 18 * len(COL) + 8), (255, 255, 255))
    ld = ImageDraw.Draw(leg)
    for i, (k, c) in enumerate(COL.items()):
        ld.rectangle([6, 6 + 18 * i, 24, 20 + 18 * i], fill=c)
        ld.text((32, 7 + 18 * i), k, fill=(0, 0, 0))
    leg.save(C.OUT / "class_map_legend.png")
    print(f"wrote {C.OUT / 'class_map_terrain.png'}, class_blocks_terrain.png, class_map_legend.png")

(C.OUT / f"census_{PART}.json").write_text(json.dumps(res, indent=1))
np.savez_compressed(C.OUT / f"classes_{PART}.npz", cls=tri_cls.astype("U8"), sub=tri_sub.astype("U12"))
print(f"wrote {C.OUT / f'census_{PART}.json'}")
