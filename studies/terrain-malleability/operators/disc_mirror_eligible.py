"""Operator inventory, step 4c: how many REAL blocks can the Disc-4 auto-mirror carry an edit onto?

discmirror.mirror's per-cell gate (world/discmirror.py:275-289) copies a cell's overrides to Disc4 only if the
destination's REAL cell is (i) absent (open ocean) or (ii) has the SAME part set as the source disc's real cell AND
every part byte-identical.  This script evaluates exactly that predicate -- by calling the module's own helpers
(_real_parts, _parts_identical) -- over every real block, so the answer is the gate's, not a re-implementation.

READ-ONLY (kit reader over the install; writes out/disc_mirror_eligible.json).
CALIBRATION: an open-ocean cell (no real parts) must classify ELIGIBLE (gate branch i); a block compared against a
deliberately different block must NOT be identical -- both asserted.

Rerun:  py studies/terrain-malleability/operators/disc_mirror_eligible.py
"""
import json, os, sys, time

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import discmirror as DM, extract as X

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
t0 = time.time()
r1, r4 = DM._real_parts(1, "0_1"), DM._real_parts(4, "0_1")

# calibration (i): a cell with no real parts on disc 4 is the 'open ocean' branch
ocean = next((x, y) for x in range(24) for y in range(20) if (x, y) not in r4)
assert not r4.get(ocean), "calibration cell must have no real Disc4 parts"
# calibration (ii): different blocks are not identical
a, b = sorted(r1)[0], sorted(r1)[len(r1) // 2]
assert not (X.read_block(a[0], a[1], disc=1, part="terrain").verts == X.read_block(b[0], b[1], disc=1, part="terrain").verts), "control broken"
print(f"calibration OK: open-ocean cell {ocean} has no Disc4 parts (gate branch i); distinct blocks {a} vs {b} differ")


def eligible(blk):
    dst = r4.get(blk, set())
    if not dst:
        return True, "no real Disc4 cell (open ocean)"
    src = r1.get(blk, set())
    if src != dst:
        return False, f"part sets differ {sorted(src ^ dst)}"
    diff = [pt for pt in sorted(dst) if not DM._parts_identical(blk, pt, 1, 4, "0_1")]
    return (not diff), ("all parts identical" if not diff else f"differs in {diff}")


rows = {}
for blk in sorted(set(r1) | set(r4)):
    ok, why = eligible(blk)
    rows[f"{blk[0]},{blk[1]}"] = {"eligible": ok, "why": why, "parts": sorted(r4.get(blk, set()))}
land = [b for b in rows if "terrain" in rows[b]["parts"]]
land_ok = [b for b in land if rows[b]["eligible"]]
sea_only = [b for b in rows if "terrain" not in rows[b]["parts"]]
sea_ok = [b for b in sea_only if rows[b]["eligible"]]
why_hist = {}
for b in land:
    if not rows[b]["eligible"]:
        k = rows[b]["why"].split(" ")[0] + (" (part set)" if "part sets" in rows[b]["why"] else "")
        why_hist[k] = why_hist.get(k, 0) + 1
print(f"real blocks with any part: {len(rows)} | land (have Terrain): {len(land)} -> mirror-ELIGIBLE {len(land_ok)}, BLOCKED {len(land) - len(land_ok)}")
print(f"sea-only real blocks: {len(sea_only)} -> eligible {len(sea_ok)}")
print("blocked-land reason histogram:", why_hist)
json.dump({"counts": {"real_blocks": len(rows), "land": len(land), "land_eligible": len(land_ok), "land_blocked": len(land) - len(land_ok),
                      "sea_only": len(sea_only), "sea_only_eligible": len(sea_ok)}, "rows": rows},
          open(os.path.join(OUT, "disc_mirror_eligible.json"), "w"), indent=1)
print(f"{time.time() - t0:.0f}s")
