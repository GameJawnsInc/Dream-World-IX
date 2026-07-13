"""THE V4 TRANSPLANT CENSUS -- find a REAL two-level coastal window on disc 1.

After the v3 bend-carry rejection (THE FORM LESSON: real content through a synthetic frame
is still synthesis), v4 transplants a WHOLE real two-level coastal feature verbatim via the
proven `world-transplant --size NXxNY` rigid-assembly path. That path needs the donor
landmass FULLY CONTAINED in its rect (only water may reach the rect frame -- land at a
frame plane would face prefab ocean as a raw vertical cut; the (7,17)+(8,17) proven donor
closes inside its 2x1 rect).

So the census asks, from real bytes:
  1. Which disc-1 landmasses (block-graph components connected by LAND crossing shared
     block frames) are SMALL (compact bounding rect)?
  2. Which of those have BOTH walkable lowland (y 0.5-9.5) AND walkable highland
     (y > 18; mid band 9.5-18 reported too) plus a topo-49 escarpment between?
  3. Fallback ranking: single COASTAL blocks that contain lowland+highland+escarpment
     in-block (the in-place-morph / bigger-window fallback list).

Walkable = geometric up-facing (winding ny > 0.1, the engine's own filter) AND topograph
in the engine on-foot set (w_movementCheckTopographID masks -- same set as census.py).
Land-touch at a frame = a terrain vert on the plane with y > 0.6 (above the swash band;
sub-sea skirt legally ends at frames under the waterline and must not count).

Run from the repo root:  py studies/overworld-topography/v4_transplant_census.py
Writes out/v4_census.json + prints the ranked report.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                   # noqa: E402
from ff9mapkit.world.terrain import GRID_X, GRID_Y         # noqa: E402

FOOT = set(range(0, 8)) | {10, 11, 12, 13} | set(range(16, 24)) | {27, 28, 30, 31} \
     | set(range(32, 39)) | {41, 42, 45, 46, 52}
DISC = 1
LAND_Y = 0.6            # frame-touch counts as LAND above this (swash tops ~0.5)
FRAME_EPS = 0.05
LOW_HI, MID_HI = 9.5, 18.0

out_dir = Path(__file__).parent / "out"
out_dir.mkdir(exist_ok=True)

# ---- part inventory straight from the bundle container (cheap) -------------------------
env = X._worldmap_env(DISC)
pat = re.compile(rf"worldmap/disc{DISC}/0_1/r\d+/block\[(\d+)\]\[(\d+)\] ([a-z0-9]+)(?:\.asset)?$")
parts = defaultdict(set)
for k in env.container:
    m = pat.search((k or "").lower())
    if m:
        parts[(int(m.group(1)), int(m.group(2)))].add(m.group(3))
terr_blocks = sorted(xy for xy, s in parts.items() if "terrain" in s)
print(f"disc {DISC}: {len(parts)} blocks with parts, {len(terr_blocks)} with terrain", flush=True)

# ---- per-block scan ---------------------------------------------------------------------
blk = {}
for (bx, by) in terr_blocks:
    bm = X.read_block(bx, by, disc=DISC)
    V = np.asarray(bm.verts, dtype=np.float64)
    T = np.asarray(bm.tangents, dtype=np.float64)
    idx = np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3)
    a, b, c = V[idx[:, 0]], V[idx[:, 1]], V[idx[:, 2]]
    n = np.cross(b - a, c - a)                             # geometric winding normal
    ln = np.linalg.norm(n, axis=1)
    ln[ln == 0] = 1.0
    ny = n[:, 1] / ln
    plan_area = 0.5 * np.abs(n[:, 1])
    cy = (a[:, 1] + b[:, 1] + c[:, 1]) / 3.0
    topo = np.array([X.decode_id(int(round(T[i][0])))["topograph"] for i in idx[:, 0]])

    up = ny > 0.1
    foot = np.isin(topo, sorted(FOOT))
    walk = up & foot
    low = walk & (cy >= 0.5) & (cy <= LOW_HI)
    mid = walk & (cy > LOW_HI) & (cy <= MID_HI)
    high = walk & (cy > MID_HI)
    esc = topo == 49
    t13 = walk & (topo == 13)

    # frame land-touch per edge (local frame: x 0/64, z 0/-64), with per-edge max land y
    vy = V[:, 1]
    landv = vy > LAND_Y
    edges = {}
    for name, axis, plane in (("W", 0, 0.0), ("E", 0, 64.0), ("N", 2, 0.0), ("S", 2, -64.0)):
        on = np.abs(V[:, axis] - plane) < FRAME_EPS
        touch = on & landv
        edges[name] = {"land": bool(touch.any()),
                       "ymax": float(vy[touch].max()) if touch.any() else None,
                       "any": bool(on.any())}
    blk[(bx, by)] = {
        "ntri": int(len(idx)),
        "cover": float(plan_area.sum() / 4096.0),
        "low_a": float(plan_area[low].sum()),
        "mid_a": float(plan_area[mid].sum()),
        "high_a": float(plan_area[high].sum()),
        "t13_a": float(plan_area[t13].sum()),
        "esc_a": float((0.5 * ln[esc]).sum()),             # true 3D area for walls
        "esc_yspan": [float(cy[esc].min()), float(cy[esc].max())] if esc.any() else None,
        "walk_ymax": float(cy[walk].max()) if walk.any() else None,
        "edges": edges,
        "parts": sorted(parts[(bx, by)]),
    }
    print(f"  ({bx:2},{by:2}) tris {len(idx):5} cover {blk[(bx,by)]['cover']:.2f} "
          f"low {blk[(bx,by)]['low_a']:6.0f} mid {blk[(bx,by)]['mid_a']:6.0f} "
          f"high {blk[(bx,by)]['high_a']:6.0f} esc {blk[(bx,by)]['esc_a']:6.0f}", flush=True)

# ---- landmass components: LAND crossing a shared frame connects the blocks (wrap-aware) --
DIRS = {"E": (1, 0, "W"), "W": (-1, 0, "E"), "N": (0, -1, "S"), "S": (0, 1, "N")}
# NB grid row y advances toward -Z: local z=0 is the block's NORTH (row y-1), z=-64 SOUTH.
adj = defaultdict(set)
for (bx, by), d in blk.items():
    for e, (dx, dy, opp) in DIRS.items():
        if not d["edges"][e]["land"]:
            continue
        nb = ((bx + dx) % GRID_X, (by + dy) % GRID_Y)
        if nb in blk and blk[nb]["edges"][opp]["land"]:
            adj[(bx, by)].add(nb)
        elif nb not in blk:
            d.setdefault("open_edges", []).append(e)       # land facing a terrain-less block

seen, comps = set(), []
for s in sorted(blk):
    if s in seen:
        continue
    comp, st = {s}, [s]
    while st:
        t = st.pop()
        for t2 in adj[t]:
            if t2 not in comp:
                comp.add(t2)
                st.append(t2)
    seen |= comp
    comps.append(sorted(comp))

rows = []
for comp in comps:
    xs = [p[0] for p in comp]
    ys = [p[1] for p in comp]
    # wrap-aware rect width: if the comp spans the seam, report raw span (flagged)
    rw, rh = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
    agg = {k: sum(blk[p][k] for p in comp) for k in ("low_a", "mid_a", "high_a", "t13_a", "esc_a")}
    coastal = any(blk[p]["cover"] < 0.97 for p in comp)
    open_e = sorted({(p, e) for p in comp for e in blk[p].get("open_edges", ())})
    rows.append({
        "blocks": comp, "n": len(comp), "rect": [rw, rh],
        **{k: round(v, 1) for k, v in agg.items()},
        "walk_ymax": max((blk[p]["walk_ymax"] or 0.0) for p in comp),
        "coastal": coastal,
        "open_edges": [[list(p), e] for p, e in open_e],
    })
rows.sort(key=lambda r: (r["rect"][0] * r["rect"][1], r["n"]))

print("\n==== LANDMASS COMPONENTS (smallest rect first) ====")
for r in rows:
    tag = ""
    if r["low_a"] > 150 and (r["high_a"] > 100 or r["mid_a"] > 100) and r["esc_a"] > 100:
        tag = "  << TWO-LEVEL CANDIDATE"
    if r["open_edges"]:
        tag += "  [OPEN: " + ",".join(f"({p[0]},{p[1]}){e}" for p, e in r["open_edges"]) + "]"
    print(f"rect {r['rect'][0]}x{r['rect'][1]} n={r['n']:3} "
          f"low {r['low_a']:8.0f} mid {r['mid_a']:8.0f} high {r['high_a']:8.0f} "
          f"t13 {r['t13_a']:7.0f} esc {r['esc_a']:8.0f} ymax {r['walk_ymax']:5.1f} "
          f"blocks {r['blocks'][:6]}{'...' if r['n'] > 6 else ''}{tag}")

# ---- fallback: single coastal blocks that are two-level IN-BLOCK -------------------------
print("\n==== per-BLOCK two-level coastal windows (fallback ranking) ====")
fall = []
for p, d in sorted(blk.items()):
    if d["cover"] >= 0.97:                                 # needs real water in the cell
        continue
    if d["low_a"] > 120 and (d["high_a"] > 80 or d["mid_a"] > 80) and d["esc_a"] > 80:
        score = min(d["low_a"], max(d["high_a"], d["mid_a"])) * (1.0 - d["cover"])
        fall.append((score, p, d))
fall.sort(reverse=True)
for score, p, d in fall[:25]:
    print(f"  {p} score {score:7.0f} cover {d['cover']:.2f} low {d['low_a']:6.0f} "
          f"mid {d['mid_a']:6.0f} high {d['high_a']:6.0f} t13 {d['t13_a']:6.0f} "
          f"esc {d['esc_a']:6.0f} esc_y {d['esc_yspan']} parts {','.join(d['parts'])}")

json.dump({"blocks": {f"{p[0]},{p[1]}": d for p, d in blk.items()},
           "components": rows},
          open(out_dir / "v4_census.json", "w"), indent=1)
print(f"\nwrote {out_dir / 'v4_census.json'}")
