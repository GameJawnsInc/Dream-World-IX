"""VERIFIER (adversarial) -- D4-04 "88.3% of triangles kept BYTE-EXACT". d4lib.compare pairs triangles by
POSITION only (kfull); a position-matched triangle can still carry an IDALL / UV / normal edit. Count the
position-kept triangles that are also attribute-identical (id, uv, normal) over the 165 really-changed terrain
blocks. Read-only. Run: py C:/gd/Dream-World-IX/studies/terrain-malleability/disc4/verify_kept_exact.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d4lib as L                                    # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
rows = json.loads((OUT / "census.json").read_text(encoding="utf-8"))
objs = L.mesh_objects()
T = [r for r in rows if r["lod"] == "0_1" and r["part"] == "terrain" and r["cls"] not in ("IDENTICAL", "REORDERED")]
t1 = kept = kept_all = 0
for r in T:
    x, y = r["x"], r["y"]
    a = L.tri_records(L.decode(objs[(1, "0_1", x, y, "terrain")], 1, x, y, "0_1"))
    b = L.tri_records(L.decode(objs[(4, "0_1", x, y, "terrain")], 4, x, y, "0_1"))
    pairs, _u1, _u4 = L._pair([q["kfull"] for q in a], [q["kfull"] for q in b])
    t1 += len(a); kept += len(pairs)
    kept_all += sum(1 for i, j in pairs if a[i]["id"] == b[j]["id"] and a[i]["uv"] == b[j]["uv"] and a[i]["nrm"] == b[j]["nrm"])
print(f"{len(T)} blocks, disc-1 tris {t1}: position-kept {kept} ({100*kept/t1:.1f}%), "
      f"position+id+uv+normal kept {kept_all} ({100*kept_all/t1:.1f}%), attr-edited among kept {kept-kept_all}")
(OUT / "verify_kept_exact.json").write_text(json.dumps({"t1": t1, "kept_pos": kept, "kept_all": kept_all}), encoding="utf-8")
