"""STEP 3 -- ANATOMY of every disc-1 -> disc-4 change site (Form 1 = the `0_1` tree).

Per block with a real (non-reorder) change in census.json:
  * GROUND DELTA (engine-faithful): placement.place sky-cast on a 1u lattice (4096 samples) over the block's
    full Form-1 walkmesh stack (Object, Terrain, Beach*, Stream, River, RiverJoint, Falls, Sea1..6 -- the
    engine registration order), disc 1 vs disc 4: dy, which mesh grounds (Terrain -> Sea4 = land became
    sea), topograph transitions, on-foot walkability flips, entrance-tile (event bits) and area-bit changes,
    MISS changes; bbox of the changed samples in WORLD coords.
  * LATTICE: are disc-4-only triangle corners placed on disc-1's existing vertex XZ positions (re-cut on the
    same lattice) or on new XZ positions (fresh geometry)? And the 1/2/4u lattice membership of new verts.
  * PLACE: nearest navipos landmark (locate.NAVIPOS -- the engine's own landmark table) to the change centroid.
Then, map-wide:
  * WELDS: every horizontally/vertically adjacent terrain pair -- is the shared-edge vertex profile identical
    on both sides (exact weld)? Baseline on disc 1 vs disc 4, and for edges whose profile CHANGED.
  * CLUSTERS: 8-connected components of ground-changed blocks, labelled by landmark.

Writes out/anatomy.json. Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/disc4/anatomy.py   (~2-4 min)
"""
import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d4lib as L                                    # noqa: E402
from d4lib import X, P                               # noqa: E402
from ff9mapkit.world import locate as LOC            # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
t0 = time.time()
rows = json.loads((OUT / "census.json").read_text(encoding="utf-8"))
objs = L.mesh_objects()
LOD = "0_1"
by_block = defaultdict(list)
for r in rows:
    if r["lod"] == LOD:
        by_block[(r["x"], r["y"])].append(r)
changed = sorted(b for b, rs in by_block.items() if any(r["cls"] not in ("IDENTICAL", "REORDERED") for r in rs))
print(f"{len(changed)} form-1 blocks with a real change")


def parts_of(disc, b):
    out = {}
    for (d, lod, x, y, part), o in objs.items():
        if d == disc and lod == LOD and (x, y) == b:
            out[part] = L.decode(o, disc, x, y, lod)
    return out


def wpos(b, lx, lz):
    return (b[0] * 64 + lx, -b[1] * 64 + lz)


res = {}
for n, b in enumerate(changed):
    p1, p4 = parts_of(1, b), parts_of(4, b)
    ml1, drop1 = L.meshlist_for(p1)
    ml4, drop4 = L.meshlist_for(p4)
    g1 = L.ground_grid(ml1, 1.0)
    g4 = L.ground_grid(ml4, 1.0)
    dy, mesh_tr, topo_tr, walk_tr, ev_tr, area_tr, miss_tr = [], Counter(), Counter(), Counter(), Counter(), Counter(), Counter()
    ch_pts = []
    for k in g1:
        a, c = g1[k], g4[k]
        changed_here = False
        if a[1] != c[1]:
            mesh_tr[(a[1], c[1])] += 1
            changed_here = True
        if a[1] == "MISS" or c[1] == "MISS":
            if (a[1] == "MISS") != (c[1] == "MISS"):
                miss_tr["MISS->hit" if a[1] == "MISS" else "hit->MISS"] += 1
        else:
            d = c[0] - a[0]
            if abs(d) > 0.05:
                dy.append(d)
                changed_here = True
            if a[3] != c[3]:
                topo_tr[(a[3], c[3])] += 1
                changed_here = True
            w1, w4 = a[3] in P.WALK_OK, c[3] in P.WALK_OK
            if w1 != w4:
                walk_tr["walk->blocked" if w1 else "blocked->walk"] += 1
            e1, e4 = X.decode_id(a[2]), X.decode_id(c[2])
            if e1["event"] != e4["event"]:
                ev_tr[(e1["event"], e4["event"])] += 1
                changed_here = True
            if e1["area"] != e4["area"]:
                area_tr[(e1["area"], e4["area"])] += 1
        if changed_here:
            ch_pts.append(wpos(b, (k[0] + 0.5), -(k[1] + 0.5)))
    rec = {"block": list(b), "parts_changed": {r["part"]: r["cls"] for r in by_block[b] if r["cls"] != "IDENTICAL"},
           "volcano_parts_dropped": sorted(set(drop1) | set(drop4)),
           "samples": len(g1), "changed_samples": len(ch_pts)}
    if dy:
        ady = [abs(v) for v in dy]
        rec["dy"] = {"n": len(dy), "max_abs": round(max(ady), 3), "mean": round(sum(dy) / len(dy), 3),
                     "up": sum(1 for v in dy if v > 0), "down": sum(1 for v in dy if v < 0),
                     "ge1": sum(1 for v in ady if v >= 1), "ge4": sum(1 for v in ady if v >= 4)}
    rec["mesh_transitions"] = [[a, c, v] for (a, c), v in mesh_tr.most_common()]
    rec["topo_transitions"] = [[a, c, v] for (a, c), v in topo_tr.most_common(12)]
    rec["walk_flips"] = dict(walk_tr)
    rec["event_transitions"] = [[a, c, v] for (a, c), v in ev_tr.most_common()]
    rec["area_transitions"] = [[a, c, v] for (a, c), v in area_tr.most_common(6)]
    rec["miss_flips"] = dict(miss_tr)
    if ch_pts:
        xs, zs = [p[0] for p in ch_pts], [p[1] for p in ch_pts]
        rec["changed_bbox_world"] = [min(xs), max(xs), min(zs), max(zs)]
        cx, cz = sum(xs) / len(xs), sum(zs) / len(zs)
        lm = LOC.nearest_landmark(cx, cz)
        rec["centroid_world"] = [round(cx, 1), round(cz, 1)]
        rec["landmark"] = [lm["name"], round(lm["dist"], 1)]
    # ---- lattice reuse of disc-4-only triangle corners (terrain only) ----
    if "terrain" in p1 and "terrain" in p4:
        r1, r4 = L.tri_records(p1["terrain"]), L.tri_records(p4["terrain"])
        _pairs, _u1, u4 = L._pair([q["kfull"] for q in r1], [q["kfull"] for q in r4])
        xz1 = {(round(v[0], 3), round(v[2], 3)) for v in p1["terrain"].verts}
        xyz1 = {(round(v[0], 3), round(v[1], 3), round(v[2], 3)) for v in p1["terrain"].verts}
        corners = [c for j in u4 for c in r4[j]["cs"]]
        if corners:
            on_xz = sum(1 for c in corners if (round(c[0], 3), round(c[2], 3)) in xz1)
            on_xyz = sum(1 for c in corners if (round(c[0], 3), round(c[1], 3), round(c[2], 3)) in xyz1)
            lat = {s: sum(1 for c in corners if abs(c[0] / s - round(c[0] / s)) < 1e-3
                          and abs(c[2] / s - round(c[2] / s)) < 1e-3) for s in (1, 2, 4)}
            rec["new_corner_lattice"] = {"n": len(corners), "on_disc1_xz": on_xz, "on_disc1_xyz": on_xyz,
                                         "on_1u": lat[1], "on_2u": lat[2], "on_4u": lat[4]}
    res[str(b)] = rec
    if n % 20 == 0:
        print(f"  {n}/{len(changed)} {b} {time.time()-t0:.0f}s")

# ---- disc-1 vertex lattice baseline (how on-grid is stock terrain at all?) ----
base = Counter()
for b in sorted({(x, y) for (d, lod, x, y, part) in objs if d == 1 and lod == LOD and part == "terrain"})[::7]:
    bm = L.decode(objs[(1, LOD, b[0], b[1], "terrain")], 1, b[0], b[1], LOD)
    for v in bm.verts:
        base["n"] += 1
        for s in (1, 2, 4):
            if abs(v[0] / s - round(v[0] / s)) < 1e-3 and abs(v[2] / s - round(v[2] / s)) < 1e-3:
                base[f"on_{s}u"] += 1
print("disc-1 terrain vertex lattice baseline (every 7th block):", dict(base))

# ---- WELDS ----
terr = {}
for (d, lod, x, y, part), o in objs.items():
    if lod == LOD and part == "terrain":
        terr[(d, x, y)] = o
prof = {}


def eprof(d, x, y, side):
    k = (d, x, y, side)
    if k not in prof:
        bm = L.decode(terr[(d, x, y)], d, x, y, LOD)
        for s in "EWNS":
            prof[(d, x, y, s)] = L.edge_profile(bm, s)
    return prof[k]


weld = Counter()
weld_rows = []
pairs = []
for (d, x, y) in terr:
    if d != 1:
        continue
    if (1, x + 1, y) in terr:
        pairs.append(((x, y, "E"), (x + 1, y, "W")))
    if (1, x, y + 1) in terr:
        pairs.append(((x, y, "S"), (x, y + 1, "N")))
for (ax, ay, asd), (bx, by_, bsd) in pairs:
    if (4, ax, ay) not in terr or (4, bx, by_) not in terr:
        continue
    a1, b1 = eprof(1, ax, ay, asd), eprof(1, bx, by_, bsd)
    a4, b4 = eprof(4, ax, ay, asd), eprof(4, bx, by_, bsd)
    w1, w4 = a1 == b1, a4 == b4
    chg = (a1 != a4) or (b1 != b4)
    weld[("d1_exact" if w1 else "d1_open", "d4_exact" if w4 else "d4_open", "edge_changed" if chg else "edge_same")] += 1
    if chg:
        weld_rows.append({"a": [ax, ay, asd], "b": [bx, by_, bsd], "d1_exact": w1, "d4_exact": w4,
                          "a_changed": a1 != a4, "b_changed": b1 != b4,
                          "a_only_d4": len(a4 - b4), "b_only_d4": len(b4 - a4),
                          "a_only_d1": len(a1 - b1), "b_only_d1": len(b1 - a1)})
print("\nWELDS (adjacent terrain pairs present on both discs):")
for k, v in sorted(weld.items()):
    print(f"   {k}: {v}")

# ---- CLUSTERS ----
gch = [tuple(json.loads(k.replace("(", "[").replace(")", "]"))) for k, r in res.items() if r["changed_samples"] > 0]
gset = set(gch)
seen, clusters = set(), []
for b in sorted(gset):
    if b in seen:
        continue
    comp, stack = [], [b]
    seen.add(b)
    while stack:
        c = stack.pop()
        comp.append(c)
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                nb = (c[0] + dx, c[1] + dz)
                if nb in gset and nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
    tot = sum(res[str(c)]["changed_samples"] for c in comp)
    names = Counter()
    for c in comp:
        if "landmark" in res[str(c)]:
            names[res[str(c)]["landmark"][0]] += res[str(c)]["changed_samples"]
    clusters.append({"blocks": sorted(comp), "changed_samples": tot, "landmarks": names.most_common(4)})
clusters.sort(key=lambda c: -c["changed_samples"])
print(f"\nCLUSTERS of ground-changed blocks: {len(clusters)}")
for c in clusters:
    print(f"   {len(c['blocks']):3d} blocks, {c['changed_samples']:6d} changed 1u-samples, landmarks {c['landmarks']}")

(OUT / "anatomy.json").write_text(json.dumps({"blocks": res, "lattice_baseline": dict(base),
                                              "welds": [[*k, v] for k, v in weld.items()],
                                              "weld_changed_edges": weld_rows, "clusters": clusters},
                                             indent=0, default=list), encoding="utf-8")
print(f"-> {OUT/'anatomy.json'}  {time.time()-t0:.0f}s")
