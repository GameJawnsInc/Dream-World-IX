"""C3 SKEPTIC spot-read -- every free edge at five NAMED sites, dumped verbatim.

Complements curtain_c3_recheck.py (imports its own scan, nothing from the instrument under
test).  For each named world point it prints every 1-owner ("free") terrain edge within a
radius, with the classification and what the scan found below it, so a claimed per-site
edge count can be checked by eye rather than by aggregate.

Regenerate: py -X utf8 curtain_c3_spotread.py
"""
import json
import math
from collections import Counter
from pathlib import Path

import curtain_c3_recheck as R

SPOTS = {
    "b13_17_claimed_worst": (868.0, -1098.0, 10.0),
    "b12_11_named": (12 * 64 + 32.0, -11 * 64 - 32.0, 32.0),
    "b13_16_named": (13 * 64 + 32.0, -16 * 64 - 32.0, 32.0),
    "b16_1_named": (16 * 64 + 32.0, -1 * 64 - 32.0, 32.0),
    "b16_5_named": (16 * 64 + 32.0, -5 * 64 - 32.0, 32.0),
    "b6_15_void_cluster": (386.8, -1018.0, 12.0),
}


def main():
    TERR = R.load(("terrain",))
    WALL = R.load(R.SEA_PARTS + R.BEACH_PARTS)
    OBJ = R.load(("object",))
    out = {}
    for name, (cx, cz, rad) in SPOTS.items():
        blocks = sorted({(int(math.floor(x / 64.0)), int(math.floor(-z / 64.0)))
                         for x in (cx - rad, cx, cx + rad) for z in (cz - rad, cz, cz + rad)}
                        & set(TERR))
        free, seam, cnt = R.edge_pass(TERR, WALL, OBJ, blocks, 0.5)
        near = [r for r in free if math.hypot(r["px"] - cx, r["pz"] - cz) <= rad]
        nseam = [r for r in seam if math.hypot(r["px"] - cx, r["pz"] - cz) <= rad]
        out[name] = {
            "blocks": [list(b) for b in blocks],
            "free_edges_in_radius": len(near),
            "class_hist": dict(Counter(r["cls"] for r in near).most_common()),
            "hover_ground": [r for r in near if r["cls"] == "HOVER_GROUND"],
            "free_above_water_gt_1u": [r for r in near if r["cls"] == "hover_water"
                                       and r["above_water"] > 1.0],
            "free_hem_y_quantiles": sorted(round(r["y"], 2) for r in near)[::max(1, len(near) // 8)],
            "seal_edges_in_radius": len(nseam),
            "seal_face_topo": dict(Counter(r["seal_topo"] for r in nseam).most_common()),
            "seal_bottom_median": (sorted(r["seal_bottom"] for r in nseam)[len(nseam) // 2]
                                   if nseam else None),
            "seal_drop_median": (sorted(r["drop"] for r in nseam)[len(nseam) // 2]
                                 if nseam else None),
            "sealed_surface_footlegal": sum(1 for r in nseam if r["surf_foot"]),
        }
        print(name, json.dumps(out[name])[:1400], flush=True)
    p = Path(__file__).with_name("out") / "curtain_c3_spotread.json"
    p.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("wrote", p)


if __name__ == "__main__":
    main()
