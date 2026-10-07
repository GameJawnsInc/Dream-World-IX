"""STEP 5 -- what ARE disc 4's scattered raised-rock crescents, and how did Square make the big sites?

(a) CROSS-SECTIONS: for the 15 largest "new raised rock" components (rock_ribbons.json), sky-cast a line
    through the centroid PERPENDICULAR to the component's long axis (-10..+10u, 0.25u step) on disc 1 and
    disc 4. Reports the ridge height above the disc-1 ground, its width at half height, and the ground
    change OUTSIDE the ridge (is the surrounding ground untouched?).
(b) UV NOVELTY: are the disc-4-only terrain triangles textured from atlas UV triplets that exist ANYWHERE in
    disc 1's terrain (re-used art), or from triplets disc 1 never uses (art painted for disc 4)?
    Calibration: disc-4 terrain tris of byte-IDENTICAL blocks must be 100% found in the disc-1 set.
(c) FORM PROMOTION: at the 26 Form-2 blocks, is disc 4's FORM-1 mesh (0_1) equal to disc 1's FORM-2 mesh
    (0_2)? (= Square baked the alternate/after-event state into disc 4's default). Only noted, the form
    switch itself belongs to another lane.

Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/disc4/crescent_probe.py
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d4lib as L                                    # noqa: E402
from d4lib import X, P                               # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
rows = json.loads((OUT / "census.json").read_text(encoding="utf-8"))
comps = json.loads((OUT / "rock_ribbons.json").read_text(encoding="utf-8"))
objs = L.mesh_objects()
res = {}

_ml = {}


def meshlist(disc, b):
    k = (disc, b)
    if k not in _ml:
        parts = {p: L.decode(o, disc, x, y, lod) for (d, lod, x, y, p), o in objs.items()
                 if d == disc and lod == "0_1" and (x, y) == b}
        ml, _ = L.meshlist_for(parts)
        _ml[k] = (ml, [P.build_index(bm) for _, bm in ml])
    return _ml[k]


def ground(disc, wx, wz):
    b = (int(wx // 64), int((-wz) // 64))
    if not (0 <= b[0] < 24 and 0 <= b[1] < 20):
        return None
    ml, idx = meshlist(disc, b)
    if not ml:
        return (0.0, "MISS", 0, None)
    return P.place(ml, wx - b[0] * 64, wz + b[1] * 64, 0.0, sky=True, index=idx)


# ---------------- (a) cross-sections ----------------
print("(a) CROSS-SECTIONS perpendicular to the 15 largest new-rock components")
xs_out = []
for c in comps[:15]:
    cx, cz = c["centroid_world"]
    th = math.radians(c["pc1_dir_deg"])            # pc1 direction in (x, -z) image frame -> world (x, z)
    ux, uz = math.cos(th), math.sin(th)            # along-axis (world x, world z)
    nx, nz = -uz, ux                               # perpendicular
    prof = []
    for k in range(-40, 41):
        t = k * 0.25
        wx, wz = cx + nx * t, cz + nz * t
        a, b = ground(1, wx, wz), ground(4, wx, wz)
        if a is None or b is None:
            continue
        prof.append((t, a[0], b[0], a[3], b[3], a[1], b[1]))
    d = [(t, y4 - y1, t1, t4) for t, y1, y4, t1, t4, m1, m4 in prof]
    rise = [v for v in d if v[1] > 0.05]
    peak = max(d, key=lambda v: v[1]) if d else None
    half = [v for v in d if peak and v[1] >= peak[1] / 2]
    outside = [abs(v[1]) for v in d if abs(v[0]) > 6]
    rec = {"centroid": [cx, cz], "landmark": c["landmark"], "peak_rise": round(peak[1], 2) if peak else None,
           "width_at_half": round((max(v[0] for v in half) - min(v[0] for v in half)) + 0.25, 2) if half else None,
           "rise_span": round(len(rise) * 0.25, 2),
           "outside_6u_max_abs_dy": round(max(outside), 3) if outside else None,
           "disc1_topos_under": dict(Counter(v[2] for v in d if v[1] > 0.05)),
           "disc4_topos_on": dict(Counter(v[3] for v in d if v[1] > 0.05)),
           "disc1_y_under_range": [round(min(p[1] for p in prof if p[2] - p[1] > 0.05), 2),
                                   round(max(p[1] for p in prof if p[2] - p[1] > 0.05), 2)] if rise else None}
    xs_out.append(rec)
    print("  ", rec)
res["cross_sections"] = xs_out

# ---------------- (b) UV novelty ----------------
print("\n(b) UV NOVELTY of disc-4-only terrain triangles")


def uvkey(rec):
    return tuple(sorted(rec["uv"])) if rec["uv"] else None


uv1 = Counter()
blocks = sorted({(x, y) for (d, lod, x, y, p) in objs if d == 1 and lod == "0_1" and p == "terrain"})
recs1, recs4 = {}, {}
for b in blocks:
    bm = L.decode(objs[(1, "0_1", b[0], b[1], "terrain")], 1, b[0], b[1], "0_1")
    recs1[b] = L.tri_records(bm)
    for r in recs1[b]:
        uv1[uvkey(r)] += 1
cls = {(r["x"], r["y"]): r["cls"] for r in rows if r["lod"] == "0_1" and r["part"] == "terrain"}
cal_n = cal_hit = 0
new_by_topo = defaultdict(lambda: [0, 0])          # topo -> [n, found_in_disc1]
new_uv_rect = defaultdict(list)
for b in blocks:
    if (4, "0_1", b[0], b[1], "terrain") not in objs:
        continue
    bm4 = L.decode(objs[(4, "0_1", b[0], b[1], "terrain")], 4, b[0], b[1], "0_1")
    r4 = L.tri_records(bm4)
    if cls.get(b) == "IDENTICAL":
        for r in r4:
            cal_n += 1
            cal_hit += uvkey(r) in uv1
        continue
    pairs, u1, u4 = L._pair([q["kfull"] for q in recs1[b]], [q["kfull"] for q in r4])
    for j in u4:
        t = X.decode_id(r4[j]["id"])["topograph"]
        new_by_topo[t][0] += 1
        hit = uvkey(r4[j]) in uv1
        new_by_topo[t][1] += hit
        if not hit:
            us = [u for u, _ in r4[j]["uv"]]; vs = [v for _, v in r4[j]["uv"]]
            new_uv_rect[t].append((min(us), max(us), min(vs), max(vs)))
print(f"  CALIBRATION: disc-4 tris of IDENTICAL blocks found in the disc-1 UV set: {cal_hit}/{cal_n}")
tot = sum(v[0] for v in new_by_topo.values()); hit = sum(v[1] for v in new_by_topo.values())
print(f"  disc-4-only terrain tris: {tot}; UV triplet re-used from disc 1: {hit} ({100*hit/max(tot,1):.1f}%)")
for t, (n, h) in sorted(new_by_topo.items(), key=lambda kv: -kv[1][0])[:12]:
    rect = new_uv_rect.get(t)
    rb = None
    if rect:
        rb = [round(min(r[0] for r in rect), 3), round(max(r[1] for r in rect), 3),
              round(min(r[2] for r in rect), 3), round(max(r[3] for r in rect), 3)]
    print(f"    topo {t:2d}: {n:5d} new tris, {h:5d} re-used UV ({100*h/n:.0f}%), novel-UV bbox u/v {rb}")
res["uv_novelty"] = {"calibration": [cal_hit, cal_n], "total_new": tot, "reused": hit,
                     "by_topo": {str(t): v for t, v in new_by_topo.items()}}

# ---------------- (c) form promotion ----------------
print("\n(c) FORM PROMOTION: disc-4 Form-1 (0_1) vs disc-1 Form-2 (0_2), the 26 switchable blocks")
f2 = sorted({(x, y, p) for (d, lod, x, y, p) in objs if d == 1 and lod == "0_2"})
promo = []
for x, y, p in f2:
    a = objs.get((1, "0_2", x, y, p)); b4 = objs.get((4, "0_1", x, y, p)); b1 = objs.get((1, "0_1", x, y, p))
    if a is None or b4 is None:
        promo.append((x, y, p, "no disc-4 form-1 counterpart"))
        continue
    s_f2, s_d4, s_d1 = L.raw_sig(a), L.raw_sig(b4), L.raw_sig(b1) if b1 else None
    if L.sig_identical(s_f2, s_d4):
        v = "disc4 F1 == disc1 F2 (byte)"
    else:
        c = L.compare(L.decode(a, 1, x, y, "0_2"), L.decode(b4, 4, x, y, "0_1"))
        tot1 = c["t1"]
        v = (f"disc4F1 vs disc1F2: shared {c['tri_shared_exact']}/{tot1} rh {c['tri_reheighted']} "
             f"-{c['tri_only1']} +{c['tri_only4']}")
        if s_d1 is not None:
            c2 = L.compare(L.decode(b1, 1, x, y, "0_1"), L.decode(b4, 4, x, y, "0_1"))
            v += f" | vs disc1F1: shared {c2['tri_shared_exact']}/{c2['t1']}"
    promo.append((x, y, p, v))
    print(f"   ({x},{y}) {p}: {v}")
res["form_promotion"] = promo
(OUT / "crescent_probe.json").write_text(json.dumps(res, indent=0, default=str), encoding="utf-8")
print("->", OUT / "crescent_probe.json")
