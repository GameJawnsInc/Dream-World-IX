"""THE SEA-LAYER LAW, re-measured map-wide at the VERTEX level.

Recorded law (memory project-ff9-overworld-audit-roadmap, AUDIT-AND-ROADMAP-2026-07-18.md:332): "every FF9 sea
sub-layer sits at EXACTLY Y=0 map-wide; layers coexist by DISJOINT PLAN COVERAGE, never Y offset".
y_census.py found sea1/sea2/sea3 vertices up to +0.80u and sea4 residuals on both discs. This probe says
WHERE: per (disc, part, block) the count of off-zero verts, their y range, and -- for each raised vertex --
the stock Terrain height under/near it (is the raised sea a shore ramp climbing onto land, or a free
floating offset?), using the calibrated kit ground simulator's sheet enumerator.

Read-only; reads the install through ff9mapkit.world.extract. Writes out/sea_layer_probe.json.
Run:  py studies/terrain-malleability/vertical/sea_layer_probe.py
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
import numpy as np                                   # noqa: E402
from ff9mapkit.world import extract as X             # noqa: E402
from ff9mapkit.world import placement as P           # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
SEA = ("sea1", "sea2", "sea3", "sea4", "sea5", "sea6", "sea4f")
EPS = 1e-6


def part_blocks(disc):
    env = X._worldmap_env(disc)
    pat = re.compile(rf"worldmap/disc{disc}/0_1/r\d+/block\[(\d+)\]\[(\d+)\] ([a-z0-9_]+)(?:\.asset)?$")
    per = defaultdict(set)
    for k in env.container:
        m = pat.search((k or "").lower())
        if m:
            per[m.group(3)].add((int(m.group(1)), int(m.group(2))))
    return per


res = {}
for disc in (1, 4):
    pb = part_blocks(disc)
    rows = []
    for part in SEA:
        for (bx, by) in sorted(pb.get(part, ())):
            bm = X.read_block(bx, by, disc=disc, part=part)
            V = np.asarray(bm.verts)
            off = np.abs(V[:, 1]) > EPS
            if not off.any():
                continue
            # terrain under each raised vertex (block-local frame; all_sheets on the terrain mesh only)
            try:
                tb = X.read_block(bx, by, disc=disc, part="terrain")
                ml = [("Terrain", tb)]
                idx = P.build_meshlist_index(ml)
            except Exception:                               # noqa: BLE001
                ml, idx = None, None
            near_land, free, samples = 0, 0, []
            for v in V[off]:
                tops = []
                if ml is not None:
                    for dx, dz in ((0, 0), (0.5, 0), (-0.5, 0), (0, 0.5), (0, -0.5)):
                        sh = P.all_sheets(ml, v[0] + dx, v[2] + dz, strict=False, index=idx)
                        tops += [s[0] for s in sh]
                if tops:
                    near_land += 1
                else:
                    free += 1
                if len(samples) < 4:
                    samples.append({"local": [round(float(v[0]), 2), round(float(v[1]), 3), round(float(v[2]), 2)],
                                    "terrain_y_near": (round(max(tops), 3) if tops else None)})
            rows.append({"part": part, "block": [bx, by], "verts": int(len(V)), "off_zero": int(off.sum()),
                         "ymin": round(float(V[:, 1].min()), 4), "ymax": round(float(V[:, 1].max()), 4),
                         "off_gt_0p05": int((np.abs(V[:, 1]) > 0.05).sum()),
                         "raised_with_terrain_within_0p5u": near_land, "raised_with_no_terrain": free,
                         "samples": samples})
    res[disc] = rows

print("THE SEA-LAYER LAW re-measured (verts with |y| > 1e-6):")
for disc, rows in res.items():
    print(f"\n== disc {disc}: {len(rows)} (part, block) pairs carry off-zero sea verts")
    tot = defaultdict(lambda: [0, 0, 0, 0, -9, 9])
    for r in rows:
        t = tot[r["part"]]
        t[0] += r["off_zero"]; t[1] += r["off_gt_0p05"]; t[2] += r["raised_with_terrain_within_0p5u"]
        t[3] += r["raised_with_no_terrain"]; t[4] = max(t[4], r["ymax"]); t[5] = min(t[5], r["ymin"])
    for p, t in tot.items():
        print(f"  {p}: off-zero verts {t[0]} (>{0.05}u: {t[1]}), y range [{t[5]}, {t[4]}], "
              f"with terrain within 0.5u {t[2]}, no terrain {t[3]}")
    for r in sorted(rows, key=lambda r: -max(abs(r['ymax']), abs(r['ymin'])))[:14]:
        print(f"   {r['part']:5s} {r['block']} off {r['off_zero']:3d}/{r['verts']:4d} y[{r['ymin']},{r['ymax']}]"
              f" land-near {r['raised_with_terrain_within_0p5u']} free {r['raised_with_no_terrain']} e.g. {r['samples'][:2]}")
(OUT / "sea_layer_probe.json").write_text(json.dumps({str(k): v for k, v in res.items()}, indent=1))
print("\nwrote", OUT / "sea_layer_probe.json")
