"""DEFECT 23 CALIBRATION (2026-10-08): which one-way-wall rule should `world-terrain` use?

The gate (`terrain._walk_gate`) refuses a reshape when any edge of a triangle the edit touches is steeper than the
walk ceiling (rise/run > WALK_RAY_START / WALK_SPEED, ~79.4 deg). G12 (VERIFY.md) found the worst such edge was
already over the ceiling in stock in 98.9% of refusals: town walls, cliffs. Four rules, scored on the SAME edits run
through the REAL kit code (`terrain.reshape(dry_run=True)`: stacked reads, stitch pins, every other gate), by a spy
that replaces `_walk_gate` and judges each edge before and after:
  old  any touched edge over the slope ceiling after the edit (the gate as shipped)
  A    an over-ceiling edge the edit made STEEPER (post > pre): G12's candidate, 62.6% of its refusals pass.
       Hole: a vertical edge (run 0) is infinitely steep before and after, so a climbable lip raised into a wall
       never counts
  B    an edge the edit took from at-or-under the ceiling to over it
  D    C, on a triangle whose topograph the walker may enter (placement.WALK_OK): a cliff tile (topo 49) is a wall by
       its topograph whatever its slope. On canopy (topographs 36-38) the reach is 2.34375 - 1.171875 (the sink)
  C    an edge the edit turned into a CLIMB BARRIER that was not one before. Barrier = the walker cannot climb it:
       rise > WALK_RAY_START * max(run, WALK_SPEED) / WALK_SPEED -- the slope ceiling on an edge longer than one
       0.4375u step, the walk ray's 2.34375u reach on a shorter one. In game (RESULTS section 6) a ~1u vertical step
       was climbed at all three lines and a 2.5-3u one refused at all three: the slope ceiling called both walls.
Populations: (1) a seeded sample of 8u-lattice land points on stock disc 1, r 8/16/24, +4 and -4; (2) the 43 stock
door arrivals, r16, +1/+4/-3 (guard_prep.py: the old gate refused 28 of them outright).
Registered predictions: C refuses fewer edits than old on both populations; C refuses no edit that old passes
except where a vertical (run < WALK_SPEED) edge gains rise past 2.34375 (A's hole); on population 1 the share of
old refusals C passes is at least G12's 62.6%. Added after the first run (C's 75 lattice refusals were all on
non-walkable cliff tiles, 67 within 0.25u of the limit): D, and population (3), steep sculpts (r 4/6, +12/+20/-20)
as the control that D still refuses real walls (registered: D refuses most of them, old refuses at least as many).
Writes out/d23_wallgate_rules.json.
Run (from ff9mapkit/):  py ../studies/terrain-malleability/gap_disc4_edit_reach/d23_wallgate_rules.py [--n 400]
"""
from __future__ import annotations

import argparse
import copy
import functools
import json
import math
import random
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
TM = HERE.parent
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
sys.path.insert(0, str(TM.parent.parent / "ff9mapkit"))
from ff9mapkit.world import extract as X, mesh as M, terrain as T   # noqa: E402
from ff9mapkit.world.extract import CH_POS                          # noqa: E402
from ff9mapkit.world.placement import WALK_RAY_START as R, WALK_SPEED as S, WALK_OK   # noqa: E402

WALL = R / S
RULES = ("old", "A", "B", "C", "D")


def slope(rise, run):
    return rise / run if run > 1e-9 else (math.inf if rise > 1e-9 else 0.0)


CANOPY, SINK = (36, 37, 38), 1.171875         # on canopy the player stands 1.171875u sunk: his reach is R - SINK


def barrier(rise, run, reach=R):
    return rise > reach * max(run, S) / S


def judge(ter, pre_y) -> dict:
    """Every rule's verdict on one deformed block, from the same edges the shipped gate reads."""
    ca = getattr(ter, "chan_arrays", None)
    if not isinstance(ca, dict) or CH_POS not in ca or not ter.tris:
        return {}
    pos = ca[CH_POS]
    moved = {i for i, v in enumerate(pos) if v[1] != pre_y[i]}
    if not moved:
        return {}
    out = {r: False for r in RULES}
    worst = {}
    margins = {"C": [], "D": []}
    seen = set()
    tan = getattr(ter, "tangents", None)
    for tri in ter.tris:
        topo = None if tan is None else X.decode_id(int(round(tan[tri[0]][0])))["topograph"]
        walk_tri = topo is None or topo in WALK_OK
        reach = R - SINK if topo in CANOPY else R
        if not (moved & set(tri)):
            continue
        for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            if (a, b) in seen or (b, a) in seen:
                continue
            seen.add((a, b))
            va, vb = pos[a], pos[b]
            run = math.hypot(vb[0] - va[0], vb[2] - va[2])
            r1, r0 = abs(vb[1] - va[1]), abs(pre_y[b] - pre_y[a])
            t1, t0 = slope(r1, run), slope(r0, run)
            hit = {"old": t1 > WALL, "A": t1 > WALL and t1 > t0 + 1e-9, "B": t1 > WALL and t0 <= WALL,
                   "C": barrier(r1, run) and not barrier(r0, run)}
            hit["D"] = walk_tri and barrier(r1, run, reach) and not barrier(r0, run, reach)
            for k, rk in (("C", R), ("D", reach)):
                if hit[k]:
                    margins[k].append((round(r1 - rk * max(run, S) / S, 4), round(r1 - r0, 4)))
            for k, v in hit.items():
                if v:
                    out[k] = True
                    if k not in worst or r1 > worst[k]["rise"]:
                        worst[k] = {"rise": round(r1, 3), "pre_rise": round(r0, 3), "run": round(run, 3),
                                    "at": [round(va[0], 1), round(va[2], 1)]}
    out["worst"] = worst
    out["margins"] = margins
    return out


def land_points(seed: int, n: int) -> list:
    pts = []
    for (bx, by, *_r) in X.list_blocks(disc=1, game=GAME):
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain", game=GAME)
        except (ValueError, FileNotFoundError):
            continue
        ox, oz = X.block_world_origin(bx, by)
        tan = bm.tangents
        for t in bm.tris:
            if X.decode_id(int(round(tan[t[0]][0])))["topograph"] in WALK_OK:
                v = bm.verts[t[0]]
                pts.append((math.floor((v[0] + ox) / 8) * 8 + 4.37, math.floor((v[2] + oz) / 8) * 8 + 4.61))
    pts = sorted(set(pts))
    random.Random(seed).shuffle(pts)
    return pts[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--seed", type=int, default=23)
    a = ap.parse_args()
    import ff9mapkit
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    real_read = X.read_block

    @functools.lru_cache(maxsize=None)
    def _cached(bx, by, disc, lod, part):
        return real_read(bx, by, disc=disc, lod=lod, part=part, game=GAME)

    def read_block(bx, by, disc=1, lod="0_1", part="terrain", game=None, **k):
        return copy.deepcopy(_cached(bx, by, disc, lod, part))     # reshape deforms in place: hand out copies
    X.read_block = read_block
    verdict = {}

    def spy(ter, pre_y, blk, summary, *, allow_steep):
        j = judge(ter, pre_y)
        if j:
            verdict.setdefault("blocks", []).append((list(blk), j))
    T._walk_gate = spy
    pops = {"lattice": [(p, r, amt) for p in land_points(a.seed, a.n) for r in (8.0, 16.0, 24.0)
                        for amt in (4.0, -4.0)]}
    arr = json.loads((TM / "gap_inplace_stitch_composition/out/door_arrivals.json").read_text(encoding="utf-8"))
    pops["door_arrivals"] = [((d["x"], d["z"]), 16.0, amt) for d in arr["arrivals"] for amt in (1.0, 4.0, -3.0)]
    # the CONTROL: sculpts steep enough that a working rule must refuse (a +12 r4 smooth hill tops ~77 deg)
    pops["steep_sculpts"] = [(p, r, amt) for p in land_points(a.seed + 1, 60) for r in (4.0, 6.0)
                             for amt in (12.0, 20.0, -20.0)]
    res = {"n_points": a.n, "seed": a.seed, "wall_tan": WALL}
    t0 = time.time()
    with tempfile.TemporaryDirectory() as empty:
        for name, edits in pops.items():
            cnt, other, examples, margin_rows = Counter(), Counter(), [], {}
            for k, (p, r, amt) in enumerate(edits):
                verdict.clear()
                try:
                    T.reshape(empty, at=p, radius=r, amount=amt, dry_run=True, allow_entrances=True,
                              skip_mirror=True, game=GAME)
                except Exception as e:                                    # noqa: BLE001 -- another gate refused
                    other[type(e).__name__ + ": " + str(e)[:40]] += 1
                    continue
                cnt["edits"] += 1
                blocks = verdict.get("blocks", [])
                ref = {rule: any(j[rule] for _b, j in blocks) for rule in RULES}
                for rule in RULES:
                    cnt[rule] += ref[rule]
                cnt["old_and_not_C"] += ref["old"] and not ref["C"]
                cnt["C_and_not_old"] += ref["C"] and not ref["old"]
                cnt["C_and_not_A"] += ref["C"] and not ref["A"]
                cnt["A_and_not_C"] += ref["A"] and not ref["C"]
                cnt["C_and_not_D"] += ref["C"] and not ref["D"]
                for rule in ("C", "D"):
                    if ref[rule]:
                        # the edit's LARGEST crossing in this edit: how far past the limit, how much it added
                        mx = max((m for _b, j in blocks for m in j["margins"][rule]), key=lambda m: m[0])
                        margin_rows.setdefault(rule, []).append(mx)
                if (ref["C"] and not ref["A"]) or (ref["C"] and not ref["old"]) or (len(examples) < 6 and ref["C"]):
                    examples.append({"at": p, "r": r, "amt": amt, "ref": ref,
                                     "worst": {b2: {k2: v for k2, v in j["worst"].items()} for b2, j in
                                               ((str(b), j) for b, j in blocks)}})
                if k % 200 == 0:
                    print(f"  {name} {k}/{len(edits)} {dict(cnt)} {time.time() - t0:.0f}s", flush=True)
            res[name] = {"counts": dict(cnt), "other_refusals": dict(other.most_common(8)),
                         "old_refusals_C_passes": (round(cnt["old_and_not_C"] / cnt["old"], 4) if cnt["old"] else None),
                         "old_refusals_A_passes": (round((cnt["old"] - cnt["A"]) / cnt["old"], 4) if cnt["old"] else None),
                         "examples": examples[:20],
                         "refusal_margins": {k: {"n": len(v), "past_limit_lt_0.05": sum(1 for m in v if m[0] < 0.05),
                                                 "past_limit_lt_0.25": sum(1 for m in v if m[0] < 0.25),
                                                 "edit_added_lt_0.05": sum(1 for m in v if m[1] < 0.05),
                                                 "median_past_limit": sorted(m[0] for m in v)[len(v) // 2] if v else None}
                                             for k, v in margin_rows.items()}}
            print(name, json.dumps(res[name]["counts"]), "C passes", res[name]["old_refusals_C_passes"],
                  "of old refusals; A passes", res[name]["old_refusals_A_passes"], flush=True)
    res["seconds"] = round(time.time() - t0)
    out = HERE / "out" / "d23_wallgate_rules.json"
    out.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print("->", out)


if __name__ == "__main__":
    main()
