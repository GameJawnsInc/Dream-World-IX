"""PROBE: do our four donor strips' TOP paths have valid LATTICE HOMES? (read-only)

The rim-aware round's sharpened mechanism (RIM-AWARE-PREDICTION.md amendment) inherits
the crest<->lattice correspondence from the DONOR: stock's crest verts are displaced
lattice verts (RIM-GRAMMAR.md R1), so each strip-top vert should carry a donor lattice
home, and consecutive homes should be lattice-ADJACENT (a connected lattice path) with
few collisions. If that holds per-donor, a lattice-group pose (yaw 90deg-steps,
translation 4u-steps) transports the homes onto the bench lattice and the displaced-row
construction assembles with NO correspondence solve. This probe validates it on the
four REAL strips before the build.

Run from studies/path-d-new-world/: py -X utf8 probe_strip_lattice_homes.py
"""
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import terrace_wall_strip as TW                             # noqa: E402


def lat_res(p):
    rx = p[0] % 4.0
    rz = p[2] % 4.0
    return math.hypot(min(rx, 4.0 - rx), min(rz, 4.0 - rz))


def home(p):
    return (round(p[0] / 4.0), round(p[2] / 4.0))


for (blk, a, b, n_chain) in TW.DONORS:
    s = TW.cut_strip(blk, a, b, n_chain)
    ecnt = Counter()
    pts = {}
    for rec in s["recs"]:
        ks = []
        for (w, uv, nr, tn) in rec:
            k = (round(w[0], 3), round(w[1], 3), round(w[2], 3))
            ks.append(k)
            pts[k] = w
        for i, j in ((0, 1), (1, 2), (2, 0)):
            ecnt[tuple(sorted((ks[i], ks[j])))] += 1
    ymax = max(p[1] for p in pts.values())
    top_edges = []
    for e, n_e in ecnt.items():
        if n_e != 1:
            continue
        dy = abs(e[0][1] - e[1][1])
        dxz = math.hypot(e[0][0] - e[1][0], e[0][2] - e[1][2])
        if dy >= dxz:                                       # vertical-ish: a cut end
            continue
        if min(e[0][1], e[1][1]) > ymax - 8.0:              # the crest band (notches incl.)
            top_edges.append(e)
    adj = defaultdict(set)
    for e in top_edges:
        adj[e[0]].add(e[1])
        adj[e[1]].add(e[0])
    ends = [p for p, l in adj.items() if len(l) == 1]
    start = min(ends) if ends else next(iter(adj))
    path = [start]
    prev = None
    while True:
        nxt = [q for q in adj[path[-1]] if q != prev]
        if not nxt:
            break
        prev = path[-1]
        path.append(nxt[0])
        if len(path) > 500 or path[-1] == start:
            break
    res = [round(lat_res(p), 2) for p in path]
    homes = [home(p) for p in path]
    steps = Counter()
    bad_step = coll = 0
    for i in range(1, len(homes)):
        di = homes[i][0] - homes[i - 1][0]
        dj = homes[i][1] - homes[i - 1][1]
        if (di, dj) == (0, 0):
            coll += 1
        elif abs(di) <= 1 and abs(dj) <= 1:
            steps[(abs(di), abs(dj))] += 1
        else:
            bad_step += 1
    dup = len(homes) - len(set(homes))
    import numpy as np
    print(f"strip blk {blk} [{a}..{b}]: crest path {len(path)} verts "
          f"({len(top_edges)} top edges, {len(adj)} nodes)")
    print(f"   lattice residual: med {float(np.median(res)):.2f}u "
          f"p99 {float(np.percentile(res, 99)):.2f} max {max(res):.2f}; "
          f"on-grid(<0.3) {sum(1 for r in res if r < 0.3) / len(res):.0%}")
    print(f"   home steps: axis {steps[(1, 0)] + steps[(0, 1)]}, diag {steps[(1, 1)]}, "
          f"SAME-home {coll}, JUMP(>1 cell) {bad_step}, dup homes total {dup}")
    ok = bad_step == 0 and coll <= max(1, len(path) // 25)
    print(f"   -> lattice-path {'VALID' if ok else '!! BROKEN'}\n")
