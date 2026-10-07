"""ADVERSARIAL VERIFY (GA6 / GA7 / GA8 / GA12 / GA13-AL5): the lane scores "can roll a battle" at FOG 0.

The encounter key is (zone, topograph, w_frameFog) (ff9.cs w_worldGetBattleScenePtr). w_frameFog = UseMist()
(Memoria/World/WorldConfiguration.cs:223-243): stock returns `w_frameScenePtr < 5990 || w_frameScenePtr > 11090`,
and the s75 Path-D branch returns false when the WorldDiscSpike is engaged with SuppressMist. The Southern Ring
campaign runs at scenario 4100 (DESIGN.md) -> MIST ON -> fog 1 on Disc1. Disc 4 (scenario >= 11090) -> fog 1 too
for anything > 11090. Path D (s75) -> fog 0.

This re-scores the live audit's per-cell walkable records at the fog each namespace actually runs with, from the
lane's own out/live_audit.json (which stores both fog0 and fog1 status per (cell, area, topo)).

Rerun: py studies/terrain-malleability/gap_area_layer/verify_fog.py
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import arealib as A  # noqa: E402

la = json.loads((HERE / "out" / "live_audit.json").read_text(encoding="utf-8"))
for ns in (1, 4, 9):
    agg = defaultdict(lambda: [0, 0, 0])            # area -> [walkable, live@fog0, live@fog1]
    cells_fog_diff = []
    for c in la["cells"]:
        if c["ns"] != ns:
            continue
        for ar, p in c["raster"]["areas"].items():
            w = p["walkable_u2"]
            f0 = sum(v["u2"] for v in p["walkable_topo_records"].values() if v["fog0"] == "record")
            f1 = sum(v["u2"] for v in p["walkable_topo_records"].values() if v["fog1"] == "record")
            agg[int(ar)][0] += w
            agg[int(ar)][1] += f0
            agg[int(ar)][2] += f1
            if f0 != f1:
                cells_fog_diff.append((tuple(c["cell"]), int(ar), f0, f1,
                                       {t: (v["fog0"], v["fog1"]) for t, v in p["walkable_topo_records"].items()}))
    print(f"== Disc{ns}: area -> walkable u2, encounter-live u2 @fog0, @fog1")
    for ar, (w, f0, f1) in sorted(agg.items()):
        flag = "  <-- differs" if f0 != f1 else ""
        print(f"   area {ar:>2}: walkable {w:>7}  fog0 {f0:>6}  fog1 {f1:>6}{flag}")
    for row in cells_fog_diff[:12]:
        print("     cell-level fog difference:", row)

# The record table itself: which (zone 0, topo 0) / zone 5 / zone 6 rows exist at each fog
recs1, src1 = A.record_set(1, live=True)
recs4, src4 = A.record_set(4, live=True)
for z in (0, 5, 6, 18, 23, 24):
    for nm, recs in (("disc1 live", recs1), ("disc4", recs4)):
        f0 = sorted(t for (zz, t, f) in recs if zz == z and f == 0)
        f1 = sorted(t for (zz, t, f) in recs if zz == z and f == 1)
        print(f"   zone {z:>2} {nm}: topos@fog0 {f0}  topos@fog1 {f1}")
print("record sources:", src1, "|", src4)
