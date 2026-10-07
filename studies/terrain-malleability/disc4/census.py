"""STEP 1 -- THE DISC-1 vs DISC-4 MESH CENSUS (every block, every part, both LODs).

For every (lod, block, part) present on either disc, classify disc1 -> disc4 as:
  IDENTICAL       vertex buffer + index buffer + channel layout + submeshes byte-equal
  ADDED / REMOVED part present on one disc only
  SAME_TOPO:<chs> same vcount + same index buffer; <chs> = the channels whose values moved
                  (pos / nrm / uv / tan.x [= the IDALL: event/area/topograph] / tan.yzw)
  REORDERED       not byte-equal, but the triangle multiset (positions+uv+id) is identical
  RETOPO          different vertex count or index buffer -- then the geometric tri match says how much
                  is shared / re-heighted / cut out / put in (d4lib.compare)

Writes out/census.json (bulky: per-key detail) and prints the headline tables.
Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/disc4/census.py      (~1-2 min)
"""
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d4lib as L                                    # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)
t0 = time.time()

objs = L.mesh_objects()
keys = sorted({(lod, x, y, part) for (_d, lod, x, y, part) in objs})
print(f"{len(objs)} mesh objects; {len(keys)} distinct (lod, block, part) keys; {time.time()-t0:.1f}s")

rows = []
for lod, x, y, part in keys:
    o1, o4 = objs.get((1, lod, x, y, part)), objs.get((4, lod, x, y, part))
    row = {"lod": lod, "x": x, "y": y, "part": part}
    if o1 is None or o4 is None:
        row["cls"] = "ADDED" if o1 is None else "REMOVED"
        o = o4 if o1 is None else o1
        bm = L.decode(o, 4 if o1 is None else 1, x, y, lod)
        row["tris"] = len(bm.tris)
        xs = [v[0] for v in bm.verts]; ys = [v[1] for v in bm.verts]; zs = [v[2] for v in bm.verts]
        row["bbox_local"] = [round(min(xs), 3), round(max(xs), 3), round(min(ys), 3), round(max(ys), 3),
                             round(min(zs), 3), round(max(zs), 3)]
        rows.append(row)
        continue
    s1, s4 = L.raw_sig(o1), L.raw_sig(o4)
    row["name_same"] = s1["name"] == s4["name"]
    row["aabb_same"] = s1["aabb"] == s4["aabb"]
    if L.sig_identical(s1, s4):
        row["cls"] = "IDENTICAL"
        rows.append(row)
        continue
    bm1 = L.decode(o1, 1, x, y, lod)
    bm4 = L.decode(o4, 4, x, y, lod)
    c = L.compare(bm1, bm4)
    row.update(c)
    # ORDER-INVARIANT classification (the meshes are UNINDEXED: a triangle re-order rewrites the whole
    # vertex buffer, so per-vertex channel diffs alone cannot tell an edit from a shuffle -- calibrate.py A4)
    geo = c["tri_only1"] or c["tri_only4"]
    attrs = [n for n, k in (("id", "shared_id_changed"), ("uv", "shared_uv_changed"),
                            ("nrm", "shared_nrm_changed")) if c[k]]
    if geo:
        row["cls"] = "RETOPO"                       # footprint / triangulation changed somewhere
    elif c["tri_reheighted"]:
        row["cls"] = "RESHAPE" + ("+" + "+".join(attrs) if attrs else "")   # same footprints, new Y
    elif attrs:
        row["cls"] = "ATTR:" + "+".join(attrs)      # same geometry, re-typed / re-UV'd / re-lit
    else:
        row["cls"] = "REORDERED"                    # identical triangle multiset, new buffer order
    row["order_kept"] = c["same_topology"] and c["tri_reordered_in_shared"] == 0
    rows.append(row)

print(f"classified in {time.time()-t0:.1f}s")
(OUT / "census.json").write_text(json.dumps(rows, indent=0), encoding="utf-8")

# ---------------- headline tables ----------------
for lod in sorted({r["lod"] for r in rows}):
    R = [r for r in rows if r["lod"] == lod]
    print(f"\n==== LOD {lod}: {len(R)} (block,part) keys on {len({(r['x'], r['y']) for r in R})} blocks ====")
    print("class counts:", dict(Counter(r["cls"] for r in R).most_common()))
    per_part = defaultdict(Counter)
    for r in R:
        per_part[r["part"]][r["cls"]] += 1
    for p in sorted(per_part):
        print(f"   {p:14s} {dict(per_part[p])}")
    blocks = defaultdict(list)
    for r in R:
        blocks[(r["x"], r["y"])].append(r)
    changed = {b: [r for r in rs if r["cls"] != "IDENTICAL"] for b, rs in blocks.items()}
    changed = {b: rs for b, rs in changed.items() if rs}
    print(f"blocks with ANY non-identical part: {len(changed)} / {len(blocks)}")
    real = {b: [r for r in rs if r["cls"] != "REORDERED"] for b, rs in changed.items()}
    real = {b: rs for b, rs in real.items() if rs}
    print(f"blocks with a REAL (non-reorder) change: {len(real)} / {len(blocks)}; "
          f"reorder-only blocks: {len(changed) - len(real)}")
    print("   real-change part counts:", dict(Counter(r["part"] for rs in real.values() for r in rs).most_common()))
    for b in sorted(changed, key=lambda b: (b[1], b[0])):
        desc = []
        for r in changed[b]:
            d = f"{r['part']}={r['cls']}"
            if "tri_shared_exact" in r and r["cls"] != "REORDERED":
                d += (f"[t {r['t1']}->{r['t4']}; sh {r['tri_shared_exact']} rh {r['tri_reheighted']} "
                      f"-{r['tri_only1']} +{r['tri_only4']} id{r['shared_id_changed']} uv{r['shared_uv_changed']}"
                      f" n{r['shared_nrm_changed']}]")
            elif r["cls"] in ("ADDED", "REMOVED"):
                d += f"[{r['tris']} tris]"
            desc.append(d)
        print(f"   {b}: " + "; ".join(desc))
print(f"\n-> {OUT/'census.json'}   total {time.time()-t0:.1f}s")
