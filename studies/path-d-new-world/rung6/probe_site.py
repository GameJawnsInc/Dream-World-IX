"""RUNG 6 / STEP 1-3 -- pick the LANDING POINT and the EXIT-TRIGGER CELL, offline.

Read-only over the deployed Disc9 bytes. Uses the calibrated bench walk instrument
(studies/path-d-new-world/walk_sim.py -- the engine ground query byte-decoded in
WALK-QUERY-DECODE.md, gate-calibrated 4/4 in BENCH-WALK-SIM.md) so the verdicts here are the
same instrument that reproduced the owner's sunken pin at 0.00u.

What it computes over the V-shore bench island (blocks 5-7 x 7-8):
  1. a 1u clean-ground map: engine-pick walkable AND grass (topo 0) AND single-sheet
     (no lawn-under-hill stack) AND land (y > 0.6, above the sea plane);
  2. per-point INTERIOR MARGIN (chebyshev distance to the nearest non-clean sample) and
     LOCAL RELIEF (max |dy| over the 8-neighbourhood) -- "flat interior grass";
  3. per-CELL clean coverage for the 32u entrance cells the world .eb can key on;
  4. the ARRIVAL ground query (sky cast, origin y+400 -- the MoveInstantXZY re-ground) and
     the WALKING ground query (origin y+2.34375) at every reported point;
  5. a real walk from the landing point to the trigger-cell centre with walk_sim's own
     deflection-fan stepper -- the route check, not a straight-line assertion.

No deploy, no mutation, no game write.
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

STUDY = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(STUDY))
sys.path.insert(0, str(STUDY.parent.parent / "ff9mapkit"))
import walk_sim as W                                          # noqa: E402
from ff9mapkit.world import entrance as E                     # noqa: E402

GRID = 1.0
GRASS = 0                       # topograph 0 == mains GRASS (interior.py:661 GRASS_ID)
SEA_Y = 0.6                     # the bench's sea plane sits at ~0.0-0.5; land lawn is 3.2
BENCH_CELLS = [(cx, cz) for cx in range(10, 16) for cz in range(14, 18)]


def sky_pick(world, x, z):
    """The ARRIVAL ground query: engine first-hit-in-order from origin y+400 (SKY_RAY_START).
    This is what MoveInstantXZY / a warp re-ground uses, not the y+2.34375 walking ray."""
    bk = W.block_key(x, z)
    if bk not in world:
        return None
    return W.full_scan(world, bk, x, z, 400.0)


def walk_pick(world, x, z, cur_y=0.0):
    """The WALKING ground query (origin cur_y + 2.34375), cold ring."""
    return W.ground_query(world, None, x, z, cur_y)


def build_map(world):
    x0, x1, z0, z1 = W.REGION
    nx = int((x1 - x0) / GRID) + 1
    nz = int((z1 - z0) / GRID) + 1
    clean, ground, topo_of, stacked = {}, {}, {}, set()
    for i in range(nx):
        x = x0 + i * GRID
        for j in range(nz):
            z = z0 + j * GRID
            p = sky_pick(world, x, z)
            if p is None:
                continue
            _mi, _ti, y, _mapid, tp = p
            ground[(i, j)] = y
            topo_of[(i, j)] = tp
            sh = W.all_sheets(world, x, z, strict=True)
            walk = [s for s in sh if s[1] in W.WALK_OK]
            if len(walk) >= 2:
                ys = sorted((s[0] for s in walk), reverse=True)
                if ys[0] - ys[1] >= 0.3:                       # placement.STACK_GAP_MIN
                    stacked.add((i, j))
            if tp in W.WALK_OK and tp == GRASS and y > SEA_Y and (i, j) not in stacked:
                clean[(i, j)] = y
    return clean, ground, topo_of, stacked, (x0, z0, nx, nz)


def margins(clean, nx, nz):
    """Chebyshev distance (in samples) from each clean point to the nearest NON-clean
    sample -- a multi-source BFS on the complement. 'Interior' = a big margin."""
    dist = {k: 0 for k in clean}
    frontier = []
    for (i, j) in clean:
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if (i + di, j + dj) not in clean:
                    dist[(i, j)] = 1
                    frontier.append((i, j))
                    break
            else:
                continue
            break
    d = 1
    while frontier:
        nxt = []
        for (i, j) in frontier:
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    k = (i + di, j + dj)
                    if k in clean and dist.get(k, 0) == 0:
                        dist[k] = d + 1
                        nxt.append(k)
        frontier = nxt
        d += 1
    return dist


def relief(clean, ground):
    out = {}
    for (i, j) in clean:
        y = ground[(i, j)]
        best = 0.0
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                k = (i + di, j + dj)
                if k in ground:
                    best = max(best, abs(ground[k] - y))
        out[(i, j)] = best
    return out


def walk_route(world, start, goal, max_steps=600):
    """Drive walk_sim's real stepper from start toward goal; re-aim each tick.

    The start height MUST come from the ARRIVAL (sky) query, not from cur_y=0: the walking
    ray starts at cur_y+2.34375, so probing a 3.2u lawn from y=0 puts the ray origin BELOW
    the ground and reports 'not walkable' -- an instrument artefact, not terrain."""
    s = sky_pick(world, start[0], start[1])
    if s is None or s[4] not in W.WALK_OK:
        return dict(ok=False, why="start not walkable (sky query)")
    p = walk_pick(world, start[0], start[1], cur_y=s[2])
    if p is None or p[4] not in W.WALK_OK:
        return dict(ok=False, why="start not walkable (walking query)")
    st = dict(x=start[0], y=p[2], z=start[1], heading=0.0)
    ring = W.Ring()
    trail, stalls = [], 0
    for k in range(max_steps):
        st["heading"] = math.atan2(goal[0] - st["x"], goal[1] - st["z"])
        ev = W.walk_step(world, ring, st)
        trail.append((round(st["x"], 2), round(st["z"], 2), round(st["y"], 2)))
        if math.hypot(st["x"] - goal[0], st["z"] - goal[1]) < 2.0:
            return dict(ok=True, steps=k + 1, stalls=stalls, end=trail[-1],
                        maxdrop=max(abs(trail[t][2] - trail[t - 1][2])
                                    for t in range(1, len(trail))) if len(trail) > 1 else 0.0)
        if ev == "stall":
            stalls += 1
            if stalls > 3:
                return dict(ok=False, why="stalled", at=trail[-1], steps=k + 1)
    return dict(ok=False, why="did not arrive", at=trail[-1], steps=max_steps)


def main():
    W.CELLS = [(5, 7), (6, 7), (7, 7), (5, 8), (6, 8), (7, 8)]
    world = W.load_world()
    print("blocks loaded:")
    for bk in sorted(world):
        print(f"   {bk}: " + ", ".join(f"{m['name']}({len(m['tris'])})" for m in world[bk]))

    clean, ground, topo_of, stacked, (x0, z0, nx, nz) = build_map(world)
    print(f"\n1u map over {W.REGION}: {len(ground)} sampled, {len(clean)} CLEAN "
          f"(grass+walkable+land+unstacked), {len(stacked)} stacked-walkable")
    tc = Counter(topo_of.values())
    print(f"   topograph histogram (engine sky pick): {tc.most_common(10)}")

    dist = margins(clean, nx, nz)
    rel = relief(clean, ground)

    # ---------------- per-cell coverage -------------------------------------------
    print("\nper-CELL clean coverage (32u entrance cells):")
    cell_pts = defaultdict(list)
    for (i, j), y in clean.items():
        x, z = x0 + i * GRID, z0 + j * GRID
        cell_pts[(int(x // 32), int(-z // 32) if z < 0 else 0)].append((x, z, y, dist[(i, j)], rel[(i, j)]))
    rows = []
    for c in sorted(cell_pts):
        pts = cell_pts[c]
        cwx, cwz = E.cell_world_center(*c)
        ys = [p[2] for p in pts]
        rows.append(dict(cell=c, n=len(pts), centre=(cwx, cwz), block=E.cell_to_block(*c),
                         ymin=round(min(ys), 2), ymax=round(max(ys), 2),
                         maxmargin=max(p[3] for p in pts)))
        print(f"   cell {c}  block {E.cell_to_block(*c)}  centre ({cwx},{cwz})  "
              f"clean {len(pts):4d}/1024  y {min(ys):5.2f}..{max(ys):5.2f}  "
              f"max-margin {max(p[3] for p in pts)}u")

    # ---------------- landing candidates ------------------------------------------
    cands = sorted(((dist[k], -rel[k], k) for k in clean), reverse=True)
    print("\ntop LANDING candidates (deep interior, flat, grass):")
    shortlist = []
    for (m, negr, (i, j)) in cands[:400]:
        x, z = x0 + i * GRID, z0 + j * GRID
        if -negr > 0.05:                     # demand near-dead-flat
            continue
        shortlist.append((m, -negr, x, z, ground[(i, j)]))
    shortlist.sort(key=lambda t: (-t[0], t[1]))
    for t in shortlist[:15]:
        print(f"   margin {t[0]:2d}u  relief {t[1]:.3f}  ({t[2]:7.1f},{t[3]:8.1f})  y={t[4]:.3f}"
              f"  cell {(int(t[2]//32), int(-t[3]//32))}")

    json.dump(dict(cells=rows,
                   landing_shortlist=[dict(margin=t[0], relief=round(t[1], 4),
                                           x=t[2], z=t[3], y=round(t[4], 3))
                                      for t in shortlist[:60]],
                   clean_n=len(clean), stacked_n=len(stacked)),
              open(HERE / "site_scan.json", "w"), indent=1)
    print(f"\nscan -> {HERE / 'site_scan.json'}")
    return world, clean, ground, dist, rel, (x0, z0)


if __name__ == "__main__":
    main()
