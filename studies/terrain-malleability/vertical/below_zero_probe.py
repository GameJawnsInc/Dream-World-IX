"""LAND BELOW Y=0 -- what the engine grounds on, and whether any water sheet lies over it.

For every block whose Terrain dips below 0 (y_census.py: 7 blocks disc 1, 9 disc 4) this builds the block's
full walkmesh stack in ENGINE REGISTRATION ORDER (placement.build_meshlist) and sky-casts a 0.5u grid with
the calibrated kit simulator `placement.place` (the engine ground query: first mesh, first up-facing tri in
buffer order, miss -> 0). For each sample whose ENGINE GROUND is < 0 it records the winning mesh/topo and
every other sheet on that vertical line (`placement.all_sheets`, strict=False), so we can answer:
  * does any Sea*/Beach* sheet lie ABOVE sub-zero ground (the "walk underwater" class -- placement rule (c)
    in project-ff9-overworld-placement-rules says real blocks never do this)?
  * is the sub-zero ground foot-legal (topo in the mode-0 mask) -- i.e. is "below sea level" walkable?
  * how deep, which topo, where (world coords)?
Also emits the per-block deepest WALKABLE point and the rim (max ground within 12u) for context.

CALIBRATION: the simulator is the one placement-rules memory validated against in-game (Uaho centre etc.);
we additionally assert, on a known open-ocean block (12,0), that every sample grounds on a Sea sheet at y=0.

Read-only. Writes out/below_zero_probe.json.
Run:  py studies/terrain-malleability/vertical/below_zero_probe.py
"""
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
import numpy as np                                   # noqa: E402
from ff9mapkit.world import extract as X             # noqa: E402
from ff9mapkit.world import placement as P           # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
STEP = 0.5


def block_parts(disc):
    env = X._worldmap_env(disc)
    pat = re.compile(rf"worldmap/disc{disc}/0_1/r\d+/block\[(\d+)\]\[(\d+)\] ([a-z0-9_]+)(?:\.asset)?$")
    per = defaultdict(set)
    for k in env.container:
        m = pat.search((k or "").lower())
        if m:
            per[(int(m.group(1)), int(m.group(2)))].add(m.group(3))
    return per


def meshlist_for(disc, bx, by, parts):
    by_name = {}
    for p in parts:
        if P.canonical_part(p) is None:          # sea4f etc: not a registered walkmesh name
            continue
        by_name[p] = X.read_block(bx, by, disc=disc, part=p)
    ml = P.build_meshlist(by_name)
    return ml, P.build_meshlist_index(ml)


def sweep(ml, idx):
    pts = []
    n = int(64 / STEP)
    for i in range(n):
        for j in range(n):
            x = (i + 0.5) * STEP
            z = -(j + 0.5) * STEP
            gy, mesh, idall, topo = P.place(ml, x, z, 0.0, sky=True, index=idx)
            pts.append((x, z, gy, mesh, topo))
    return pts


# ---- calibration: open ocean block (12,0) grounds on sea at 0 everywhere --------------------------------
bp1 = block_parts(1)
ml, idx = meshlist_for(1, 12, 0, bp1[(12, 0)])
cal_pts = sweep(ml, idx)
cal = Counter((m, round(g, 3)) for _, _, g, m, _ in cal_pts)
print("CALIBRATION open-ocean (12,0):", dict(cal.most_common(5)))
cal_ok = all(m.startswith("Sea") and abs(g) < 1e-6 for _, _, g, m, _ in cal_pts if m != "MISS")
print("  every non-miss sample on a Sea sheet at y=0:", cal_ok,
      "| misses:", sum(1 for p in cal_pts if p[3] == "MISS"), "(the recorded one-quad hole at (15,-12) region)")

res = {"calibration": {"block": [12, 0], "counts": {f"{k[0]}@{k[1]}": v for k, v in cal.items()}, "ok": cal_ok}}
for disc in (1, 4):
    bp = block_parts(disc)
    cand = []
    for (bx, by), parts in sorted(bp.items()):
        if "terrain" not in parts:
            continue
        if any("volcano" in p for p in parts) or by * 24 + bx == 219:
            continue
        tb = X.read_block(bx, by, disc=disc, part="terrain")
        if min(v[1] for v in tb.verts) < 0:
            cand.append((bx, by))
    out = []
    for (bx, by) in cand:
        ml, idx = meshlist_for(disc, bx, by, bp[(bx, by)])
        pts = sweep(ml, idx)
        sub = [p for p in pts if p[2] < -1e-6 and p[3] != "MISS"]
        rec = {"block": [bx, by], "parts": sorted(bp[(bx, by)]), "samples": len(pts), "sub_zero_ground": len(sub)}
        if sub:
            water_above, walkable, deepest = 0, 0, None
            win = Counter()
            for (x, z, g, mesh, topo) in sub:
                sheets = P.all_sheets(ml, x, z, strict=False, index=idx)
                wet = [s for s in sheets if (s[1].startswith("Sea") or s[1].startswith("Beach")) and s[0] > g + 0.01]
                water_above += bool(wet)
                if topo in P.WALK_OK:
                    walkable += 1
                    if deepest is None or g < deepest[2]:
                        deepest = (x, z, g, mesh, topo)
                win[(mesh, topo)] += 1
            ox, oz = X.block_world_origin(bx, by)
            rec.update({
                "min_ground": round(min(p[2] for p in sub), 3),
                "area_u2": len(sub) * STEP * STEP,
                "with_water_sheet_above": water_above,
                "foot_legal": walkable,
                "winner_mesh_topo": {f"{m}/{t}": c for (m, t), c in win.most_common()},
                "deepest_walkable_world": (None if deepest is None else
                                           [round(deepest[0] + ox, 2), round(deepest[2], 3), round(deepest[1] + oz, 2),
                                            deepest[3], deepest[4]]),
            })
            if deepest is not None:
                rim = max(p[2] for p in pts if math.hypot(p[0] - deepest[0], p[1] - deepest[1]) <= 12.0)
                rec["rim_max_ground_within_12u"] = round(rim, 3)
        out.append(rec)
    res[disc] = out

for disc in (1, 4):
    print(f"\n== disc {disc}: blocks with sub-zero Terrain verts")
    for r in res[disc]:
        print(f"  {r['block']} parts={r['parts']}")
        print(f"     engine ground < 0 at {r['sub_zero_ground']}/{r['samples']} samples"
              + (f" (area {r['area_u2']}u2, min {r['min_ground']}), water sheet ABOVE: {r['with_water_sheet_above']}, "
                 f"foot-legal: {r['foot_legal']}, winners {r['winner_mesh_topo']}, deepest walkable "
                 f"{r['deepest_walkable_world']}, rim max within 12u {r.get('rim_max_ground_within_12u')}"
                 if r['sub_zero_ground'] else ""))
tot = {d: sum(r.get("with_water_sheet_above", 0) for r in res[d]) for d in (1, 4)}
print("\nTOTAL sub-zero samples with a water sheet above:", tot)
(OUT / "below_zero_probe.json").write_text(json.dumps({str(k): v for k, v in res.items()}, indent=1))
print("wrote", OUT / "below_zero_probe.json")
