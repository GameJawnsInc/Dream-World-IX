"""STEP 1 -- the discmirror gate, three ways, + the P3 dry-run calibration.

(a) THE GATE AS SHIPPED: discmirror's own predicates (_real_parts + _parts_identical, which reads through
    extract.read_block's substring lookup) over every real cell -> must reproduce 84 PASS / 191 SKIP
    (186 by content + 5 by part set), 189 of 260 land cells refused (disc4 D4-16, operators F6).
(b) THE SAME GATE WITH EXACT CONTAINERS (lib cache, byte-identity of the 4 override channels + index).
(c) THE ORDER-INVARIANT GATE: a cell passes iff the part sets agree and every part is an exact all-channel
    multiset permutation (lib.tri_keys: raw vertex-record bytes, winding-preserving rotation, engine IDALL).
(d) P3: discmirror.mirror(dry_run=True) on a SCRATCH mod tree holding one Terrain override at (16,13)
    (disc-differing) and one at (14,1) (identical) -> must log SKIP and mirror respectively. Nothing is written:
    the scratch tree is outside the repo and the install; dry_run copies nothing.
Writes out/s1_gate.json.
Run (from C:\\gd\\Dream-World-IX\\ff9mapkit):  py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_disc4_edit_reach/s1_gate.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib as L                                       # noqa: E402
from ff9mapkit.world import discmirror as DM         # noqa: E402
from ff9mapkit.world import mesh as M                # noqa: E402

G = L.GAME
r1, r4 = DM._real_parts(1, "0_1", game=G), DM._real_parts(4, "0_1", game=G)
cells = sorted(set(r1) | set(r4))
land = {c for c in cells if "terrain" in r1.get(c, set()) or "terrain" in r4.get(c, set())}


def gate_shipped(c):
    dst = r4.get(c, set())
    if not dst:
        return "PASS(ocean)"
    if r1.get(c, set()) != dst:
        return "SKIP(partset)"
    diff = [p for p in sorted(dst) if not DM._parts_identical(c, p, 1, 4, "0_1", game=G)]
    return "SKIP" if diff else "PASS"


data = L.load_cache()
pairs = data["pairs"]


def gate_exact(c, perm=False):
    dst = r4.get(c, set())
    if not dst:
        return "PASS(ocean)"
    if r1.get(c, set()) != dst:
        return "SKIP(partset)"
    for p in sorted(dst):
        pr = pairs[(c[0], c[1], p)]
        if not (pr["perm"] if perm else pr["raw_identical"]):
            return "SKIP"
    return "PASS"


rows = {}
for c in cells:
    rows[c] = {"shipped": gate_shipped(c), "exact": gate_exact(c), "orderinv": gate_exact(c, perm=True),
               "land": c in land}
cnt = {k: Counter(r[k].split("(")[0] for r in rows.values()) for k in ("shipped", "exact", "orderinv")}
why = Counter(r["shipped"] for r in rows.values())
land_ref = {k: sorted(c for c in land if rows[c][k].startswith("SKIP")) for k in ("shipped", "exact", "orderinv")}
print("cells:", len(cells), "land:", len(land))
for k in cnt:
    print(f"  {k:9s} PASS {cnt[k]['PASS']:3d}  SKIP {cnt[k]['SKIP']:3d}   land refused {len(land_ref[k])}/{len(land)}")
print("  shipped reasons:", dict(why))
assert cnt["shipped"]["PASS"] == 84 and cnt["shipped"]["SKIP"] == 191, "must reproduce 84/191"
assert len(land_ref["shipped"]) == 189, "must reproduce 189 refused land cells"
flip_exact = sorted(c for c in cells if rows[c]["shipped"] != rows[c]["exact"])
flip_oi = sorted(c for c in cells if rows[c]["shipped"].startswith("SKIP") and rows[c]["orderinv"] == "PASS")
print("  shipped vs exact-container disagreements:", flip_exact,
      [(rows[c]["shipped"], rows[c]["exact"]) for c in flip_exact])
print(f"  ORDER-INVARIANT gate flips {len(flip_oi)} SKIP->PASS:", flip_oi)
print("    of which land:", [c for c in flip_oi if c in land])
# which parts are permutations in the flipped cells
perm_parts = {str(c): sorted(p for p in r4.get(c, ()) if not pairs[(c[0], c[1], p)]["raw_identical"])
              for c in flip_oi}
print("    permuted parts:", perm_parts)

# ---- (d) P3 dry-run calibration on a scratch tree -------------------------------------------------------
scratch_mod = L.CACHE_DIR / "p3_mod"
objs = L.mesh_objects()
for (x, y) in ((16, 13), (14, 1)):
    bm = L.decode(objs[(1, "0_1", x, y, "terrain")], 1, x, y)
    dst = scratch_mod / M.override_relpath(1, x, y, "0_1", "Terrain")
    M.write_ff9mesh(bm, dst)
log = []
res = DM.mirror(str(scratch_mod), src_disc=1, dst_disc=4, lod="0_1", game=G, dry_run=True, log=log.append)
skipped = [tuple(s[0]) for s in res["skipped"]]
mirrored = sorted({DM._cell_of(Path(p)) for p in res["mirrored"]})
print("P3 dry-run log:", log)
assert (16, 13) in skipped and (14, 1) in mirrored and (14, 1) not in skipped, "P3 calibration failed"
assert not (scratch_mod / "FF9_Data" / "WorldMap" / "Disc4").exists(), "dry_run must write nothing"
print("P3 calibration OK: (16,13) SKIP, (14,1) mirrored; Disc4 tree not created")
print("  (16,13) order-invariant verdict:", rows[(16, 13)]["orderinv"], "| (14,1):", rows[(14, 1)]["orderinv"])

out = {"counts": {k: dict(v) for k, v in cnt.items()}, "shipped_reasons": dict(why),
       "land": len(land), "land_refused": {k: len(v) for k, v in land_ref.items()},
       "shipped_vs_exact": [[list(c), rows[c]["shipped"], rows[c]["exact"]] for c in flip_exact],
       "orderinv_flips": [list(c) for c in flip_oi], "orderinv_flips_land": [list(c) for c in flip_oi if c in land],
       "orderinv_permuted_parts": perm_parts,
       "refused_land_shipped": [list(c) for c in land_ref["shipped"]],
       "refused_land_orderinv": [list(c) for c in land_ref["orderinv"]],
       "p3": {"log": log, "skipped": [list(c) for c in skipped], "mirrored": [list(c) for c in mirrored]},
       "rows": {f"{c[0]},{c[1]}": rows[c] for c in cells}}
(L.OUT / "s1_gate.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
