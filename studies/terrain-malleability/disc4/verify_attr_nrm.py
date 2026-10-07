"""VERIFIER (adversarial) -- D4-01: are the normal-only (ATTR:nrm) and uv-only "real edits" real, or float
re-export noise? For each ATTR key, pair triangles by position (d4lib) and report the max per-corner normal /
uv delta. Also: which BLOCKS count as "real change" only because of such keys. Read-only.
Run: py C:/gd/Dream-World-IX/studies/terrain-malleability/disc4/verify_attr_nrm.py
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d4lib as L                                    # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
rows = json.loads((OUT / "census.json").read_text(encoding="utf-8"))
objs = L.mesh_objects()
res = []
for r in rows:
    if r["lod"] != "0_1" or not r["cls"].startswith("ATTR"):
        continue
    k = ("0_1", r["x"], r["y"], r["part"])
    a = L.decode(objs[(1, *k)], 1, r["x"], r["y"], "0_1")
    b = L.decode(objs[(4, *k)], 4, r["x"], r["y"], "0_1")
    ra, rb = L.tri_records(a), L.tri_records(b)
    pairs, _x, _y = L._pair([q["kfull"] for q in ra], [q["kfull"] for q in rb])
    dn = du = 0.0
    nn = nu = 0
    for i, j in pairs:
        if ra[i]["nrm"] != rb[j]["nrm"]:
            nn += 1
            dn = max(dn, max(abs(p - q) for c1, c2 in zip(ra[i]["nrm"], rb[j]["nrm"]) for p, q in zip(c1, c2)))
        if ra[i]["uv"] != rb[j]["uv"]:
            nu += 1
            du = max(du, max(abs(p - q) for c1, c2 in zip(ra[i]["uv"], rb[j]["uv"]) for p, q in zip(c1, c2)))
    res.append({"key": [r["x"], r["y"], r["part"]], "cls": r["cls"], "nrm_tris": nn, "nrm_max": round(dn, 4),
                "uv_tris": nu, "uv_max": round(du, 5), "id_tris": r["shared_id_changed"]})
blk = defaultdict(list)
for r in rows:
    if r["lod"] == "0_1" and r["cls"] not in ("IDENTICAL", "REORDERED"):
        blk[(r["x"], r["y"])].append(r)
tiny = [x for x in res if x["id_tris"] == 0 and x["nrm_max"] < 0.01 and x["uv_max"] < 1e-3]
print(f"{len(res)} ATTR keys; keys whose only change is a normal delta <0.01 and uv delta <1e-3: {len(tiny)}")
for x in sorted(res, key=lambda x: (x["nrm_max"] + x["uv_max"])):
    print("  ", x)
tk = {tuple(x["key"]) for x in tiny}
only_tiny = [b for b, rs in blk.items() if all((r["x"], r["y"], r["part"]) in tk for r in rs)]
print("blocks counted as 'real change' ONLY through such tiny ATTR keys:", sorted(only_tiny))
(OUT / "verify_attr_nrm.json").write_text(json.dumps({"keys": res, "only_tiny_blocks": sorted(only_tiny)}, indent=0),
                                          encoding="utf-8")
