"""STEP 13 -- are the REORDERED pairs truly the same mesh, and does buffer ORDER alone change the ground?

(a) FULL-PRECISION multiset: for every REORDERED (block, part), the sorted list of per-triangle tuples of ALL
    channel floats (pos, normal, uv, tangent xyzw) of its 3 corners (corner order canonicalised by position)
    must be identical across discs -- i.e. the same triangles, only permuted.
(b) ORDER SEMANTICS: within one mesh the engine grounds on the FIRST passing triangle in buffer order
    (placement.py rule 4, from WMBlock.Raycast), so a permutation CAN change the ground where sheets overlap
    in XZ. Sky-cast the reorder-only blocks on a 0.5u lattice, disc 1 vs disc 4, and count differing samples.
Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/disc4/reorder_check.py
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d4lib as L                                    # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
rows = json.loads((OUT / "census.json").read_text(encoding="utf-8"))
objs = L.mesh_objects()


def full_multiset(bm):
    out = []
    fi = bm.flat_index
    chans = sorted(bm.chan_arrays)
    for t in range(len(fi) // 3):
        cs = []
        for k in range(3):
            vi = fi[3 * t + k]
            cs.append(tuple(tuple(bm.chan_arrays[ci][vi]) for ci in chans))
        out.append(tuple(sorted(cs)))
    return sorted(out)


ro = [r for r in rows if r["cls"] == "REORDERED"]
same = 0
for r in ro:
    k = (r["lod"], r["x"], r["y"], r["part"])
    a = L.decode(objs[(1, *k)], 1, r["x"], r["y"], r["lod"])
    b = L.decode(objs[(4, *k)], 4, r["x"], r["y"], r["lod"])
    ok = full_multiset(a) == full_multiset(b)
    same += ok
    if not ok:
        print("   NOT a pure permutation:", k)
print(f"(a) REORDERED pairs that are an exact full-channel permutation: {same}/{len(ro)}")
print("    e.g. (9,17) object:", [r["cls"] for r in ro if (r["x"], r["y"], r["part"]) == (9, 17, "object")])

blk = defaultdict(list)
for r in rows:
    if r["lod"] == "0_1":
        blk[(r["x"], r["y"])].append(r)
ro_blocks = sorted(b for b, rs in blk.items() if any(r["cls"] == "REORDERED" for r in rs))
print(f"\n(b) ground query, 0.5u lattice, on {len(ro_blocks)} blocks carrying a REORDERED part")
res = []
for b in ro_blocks:
    g = {}
    for d in (1, 4):
        parts = {p: L.decode(o, d, x, y, lod) for (dd, lod, x, y, p), o in objs.items()
                 if dd == d and lod == "0_1" and (x, y) == b}
        ml, _ = L.meshlist_for(parts)
        g[d] = L.ground_grid(ml, 0.5)
    ndy = sum(1 for s in g[1] if abs(g[1][s][0] - g[4][s][0]) > 1e-4)
    ntopo = sum(1 for s in g[1] if g[1][s][3] != g[4][s][3])
    nid = sum(1 for s in g[1] if g[1][s][2] != g[4][s][2])
    real = [f"{r['part']}={r['cls']}" for r in blk[b] if r["cls"] not in ("IDENTICAL", "REORDERED")]
    res.append({"block": list(b), "other_real_changes": real, "samples": len(g[1]), "dy": ndy, "topo": ntopo, "idall": nid})
    print(f"   {b}: dy {ndy}, topo {ntopo}, idall {nid} of {len(g[1])}  (other real changes in block: {real})")
pure = [x for x in res if not x["other_real_changes"]]
print(f"    reorder-ONLY blocks with any ground difference: {sum(1 for x in pure if x['dy'] or x['topo'] or x['idall'])}/{len(pure)}")
(OUT / "reorder_check.json").write_text(json.dumps({"permutation_ok": [same, len(ro)], "ground": res}, indent=0),
                                        encoding="utf-8")
print("->", OUT / "reorder_check.json")
