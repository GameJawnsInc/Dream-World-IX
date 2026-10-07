"""THE CANOPY SINK -- does the forest-class slice change the on-foot climb ceiling in stock forests?

SOURCE FACTS (engine_bounds.py, all stock Memoria):
  * the controlled walker's ray origin is its CURRENT y + 2.34375 (ff9.cs:5554 `Vector3 pos = w_moveActorPtr.pos`,
    w_movementRoundCheck -> w_cellHit -> w_nwpHit origin.y += rayStartOffsetY);
  * its current y is ground_height + slice_height (ff9.cs:5509, w_movementSetheight), applied every frame;
  * slice for slice_type 1 (index 1/2 = Zidane/Dagger on foot, 3-7 chocobos) on terrain class 0 = topo
    36/37/38 is S(-(400-100)) = -1.171875u, and class 0 is the ONLY class flagged immediate (imd = num2<=0)
    -> the walker sinks 1.17u into forest/hillside the frame it lands there;
  => effective climb ceiling while standing on 36/37/38 = 2.34375 - 1.171875 = 1.171875u (half the lawn's).
(The recorded walk decode, studies/path-d-new-world/walk-decode-claims.md:147/189, states slice is 0 "for
ground classes"; that holds for lawn/rock (class 8) but not for the forest/hillside class.)

THIS PROBE (stock, read-only): on every disc-1 block carrying forest/hillside terrain, sample standing points
whose ENGINE ground (sky cast, calibrated kit simulator) is topo 36/37/38; for 16 headings take one full foot
step (0.4375u, placement.WALK_SPEED) and run the engine WALK query from the actor's y twice:
    A) y = ground - 1.171875  (the source reading: sink applied)
    B) y = ground             (the recorded "slice 0" reading)
and compare against the sky-cast surface at the step target. A step "lands" if the walk query returns the
surface the sky cast sees (|dy| < 0.01) and its topo is foot-legal. We count steps that land under B but NOT
under A (the sink makes them unclimbable), fully-trapped points (all 16 headings fail) under each reading,
and the per-step climb distribution forest->forest. CONTROL: the same on lawn (topo 0) samples, where A==B
by construction (sink 0) -- a check that cannot "fail" would be meaningless, so we also report how many
lawn steps are rejected at all (expected ~0).

Run:  py studies/terrain-malleability/vertical/canopy_sink_probe.py            (~2-5 min)
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
SINK = 1.171875                 # S(-(400-100)), engine_bounds.py sink_table_u slice_type 1 class 0
STEP = P.WALK_SPEED             # 0.4375
GRID = 1.5
HEADINGS = 16
FOREST = {36, 37, 38}


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
    by_name = {p: X.read_block(bx, by, disc=disc, part=p) for p in parts if P.canonical_part(p) is not None}
    ml = P.build_meshlist(by_name)
    return ml, P.build_meshlist_index(ml)


def lands(ml, idx, qx, qz, actor_y):
    """engine walk query from actor_y at (qx,qz) -> (landed_on_top, walk_result, sky_result)"""
    sky = P.place(ml, qx, qz, 0.0, sky=True, index=idx)
    wk = P.place(ml, qx, qz, actor_y, sky=False, index=idx)
    ok = (wk[1] != "MISS" and abs(wk[0] - sky[0]) < 0.01 and wk[3] in P.WALK_OK)
    return ok, wk, sky


disc = 1
bp = block_parts(disc)
blocks = []
for (bx, by), parts in sorted(bp.items()):
    if "terrain" not in parts or any("volcano" in p for p in parts) or by * 24 + bx == 219:
        continue
    tb = X.read_block(bx, by, disc=disc, part="terrain")
    topos = Counter(X.decode_id(i)["topograph"] for i in X.block_mapids(tb))
    if sum(topos[t] for t in FOREST) >= 20:
        blocks.append((bx, by))
print(f"{len(blocks)} disc-1 blocks with >=20 forest/hillside (36/37/38) terrain tris")

stats = {"forest": Counter(), "lawn": Counter()}
climbs = {"forest->forest": [], "forest->other": [], "lawn->lawn": []}
examples = []
per_block = {}
for (bx, by) in blocks:
    ml, idx = meshlist_for(disc, bx, by, bp[(bx, by)])
    pb = Counter()
    n = int(64 / GRID)
    for i in range(n):
        for j in range(n):
            x = 1.0 + i * GRID
            z = -(1.0 + j * GRID)
            if x > 63 or z < -63:
                continue
            gy, mesh, idall, topo = P.place(ml, x, z, 0.0, sky=True, index=idx)
            if mesh == "MISS":
                continue
            kind = "forest" if topo in FOREST else ("lawn" if topo == 0 else None)
            if kind is None:
                continue
            trapA = trapB = True
            for h in range(HEADINGS):
                a = 2 * math.pi * h / HEADINGS
                qx, qz = x + STEP * math.sin(a), z + STEP * math.cos(a)
                okA, wkA, sky = lands(ml, idx, qx, qz, gy - (SINK if kind == "forest" else 0.0))
                okB, wkB, _ = lands(ml, idx, qx, qz, gy)
                climb = sky[0] - gy
                if kind == "forest":
                    climbs["forest->forest" if sky[3] in FOREST else "forest->other"].append(climb)
                elif sky[3] == 0:
                    climbs["lawn->lawn"].append(climb)
                stats[kind]["steps"] += 1
                stats[kind]["landA"] += okA
                stats[kind]["landB"] += okB
                if okB and not okA:
                    stats[kind]["B_only"] += 1
                    pb["B_only"] += 1
                    if len(examples) < 12:
                        ox, oz = X.block_world_origin(bx, by)
                        examples.append({"block": [bx, by], "from_world": [round(x + ox, 2), round(gy, 3), round(z + oz, 2)],
                                         "from_topo": topo, "to_topo": sky[3], "climb": round(climb, 3),
                                         "walkA": [round(wkA[0], 3), wkA[1], wkA[3]], "sky": [round(sky[0], 3), sky[1]]})
                trapA &= not okA
                trapB &= not okB
            stats[kind]["points"] += 1
            stats[kind]["trappedA"] += trapA
            stats[kind]["trappedB"] += trapB
            pb[kind] += 1
    per_block[f"{bx},{by}"] = dict(pb)


def pct(a, qs=(50, 90, 99, 99.9, 100)):
    a = np.asarray(a)
    return {f"p{q}": round(float(np.percentile(a, q)), 3) for q in qs} if len(a) else {}


summary = {
    "sink_u": SINK, "step_u": STEP, "grid_u": GRID, "headings": HEADINGS, "blocks": len(blocks),
    "stats": {k: dict(v) for k, v in stats.items()},
    "climb_pcts": {k: pct(v) for k, v in climbs.items()},
    "climb_in_sink_band_(1.172,2.344]": {k: int(((np.asarray(v) > SINK) & (np.asarray(v) <= 2.34375)).sum()) for k, v in climbs.items()},
    "climb_over_2.344": {k: int((np.asarray(v) > 2.34375).sum()) for k, v in climbs.items()},
    "examples_B_only": examples, "per_block": per_block,
}
print(json.dumps({k: summary[k] for k in ("stats", "climb_pcts", "climb_in_sink_band_(1.172,2.344]", "climb_over_2.344")}, indent=1))
print("examples (land without sink, refused with sink):")
for e in examples[:8]:
    print("  ", e)
(OUT / "canopy_sink_probe.json").write_text(json.dumps(summary, indent=1))
print("wrote", OUT / "canopy_sink_probe.json")
