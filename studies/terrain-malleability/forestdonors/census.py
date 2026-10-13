"""Every disc-1 forest blob, as a `world-forest` donor: which ones can be carried whole onto open grass?

`world-forest` carries one canopy: (15,15)'s, the one blob the July study found grass-bounded. A blob here is a
position-connected component of topograph 36/37 tris in the welded disc-1 soup (all blocks, world frame), of at least
MIN_TRIS. Per blob it reports:
  - size: tris, the blocks it spans, plan extent, topographs;
  - RINGS: its outer once-edges chained into closed rings (1 = a simple outline; more = a clearing inside, or a
    blob pinched into two outlines at a vertex);
  - CONTACT: its rim length by what lies across each rim edge -- grass (topo 0), other ground, rock (49/7/62/58),
    nothing on a block border (the next block's mesh) or nothing at all (an open edge);
  - CURTAIN: the share of its ground-contact rim where the forest tri on the edge is a wall (ny <= 0.1; the
    stock canopy is walled all round), and that wall's rise;
  - LEVEL: the spread (p10-p90) of its rim's base heights;
  - OBJECT: whether a stock Object mesh of any block it spans reaches into its plan bbox.
QUALIFIED (a donor `world-forest` can carry as it carries (15,15)): one ring, >= 95% of rim length against grass,
>= 90% of the grass contact walled, rim spread <= 1.5u, no Object in its bbox, and topograph 37 (lowland) only.
(15,15) is the positive control: it must qualify, or the screen is wrong.
RUN:  py studies/terrain-malleability/forestdonors/census.py   (writes out/census.json)
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__
from ff9mapkit.world import extract as X  # noqa: E402

FOREST = {36, 37}
ROCK = {49, 7, 62, 58}
GRASS = 0
MIN_TRIS = 20


def main():
    pos_id, P, T, TOPO, BLK = {}, [], [], [], []
    blocks = X.list_blocks(disc=1)
    for bx, by in blocks:
        bm = X.read_block(bx, by, disc=1)
        loc = []
        for v in bm.verts:
            w = (v[0] + 64 * bx, v[1], v[2] - 64 * by)
            k = (round(w[0], 3), round(w[1], 3), round(w[2], 3))
            if k not in pos_id:
                pos_id[k] = len(P)
                P.append(w)
            loc.append(pos_id[k])
        for (a, b, c) in bm.tris:
            T.append((loc[a], loc[b], loc[c]))
            TOPO.append(X.decode_id(int(round(bm.tangents[a][0])))["topograph"])
            BLK.append((bx, by))
    P = np.asarray(P)
    print(f"soup: {len(T)} tris over {len(blocks)} blocks")
    edges = defaultdict(list)
    for t, (a, b, c) in enumerate(T):
        for i, j in ((a, b), (b, c), (c, a)):
            edges[(min(i, j), max(i, j))].append(t)

    # forest components by shared edge
    adj = defaultdict(set)
    for e, ts in edges.items():
        f = [t for t in ts if TOPO[t] in FOREST]
        for x in f:
            adj[x].update(y for y in f if y != x)
    seen, blobs = set(), []
    for t in range(len(T)):
        if TOPO[t] not in FOREST or t in seen:
            continue
        comp, st = {t}, [t]
        while st:
            u = st.pop()
            for v in adj[u]:
                if v not in comp:
                    comp.add(v)
                    st.append(v)
        seen |= comp
        if len(comp) >= MIN_TRIS:
            blobs.append(comp)

    objects = {}
    for bx, by in blocks:
        try:
            ob = X.read_block(bx, by, disc=1, part="object")
            objects[(bx, by)] = np.asarray(ob.verts, float) + np.array([64.0 * bx, 0.0, -64.0 * by])
        except Exception:                                   # noqa: BLE001 -- most blocks have none
            pass

    def plen(i, j):
        return math.hypot(P[i][0] - P[j][0], P[i][2] - P[j][2])

    def on_border(i, j):
        for ax in (0, 2):
            a, b = P[i][ax] % 64.0, P[j][ax] % 64.0
            if min(a, 64 - a) < 1e-3 and min(b, 64 - b) < 1e-3 and abs(P[i][ax] - P[j][ax]) < 1e-3:
                return True
        return False

    def ny(t):
        a, b, c = (P[k] for k in T[t])
        n = np.cross(b - a, c - a)
        ln = float(np.linalg.norm(n))
        return abs(float(n[1])) / ln if ln > 1e-12 else 0.0

    rows = []
    for comp in sorted(blobs, key=len, reverse=True):
        cnt = Counter()
        for t in comp:
            a, b, c = T[t]
            for i, j in ((a, b), (b, c), (c, a)):
                cnt[(min(i, j), max(i, j))] += 1
        once = [e for e, n in cnt.items() if n == 1]
        # rings: chain the once-edges (a vertex used by >2 once-edges = a pinch; counted, chained greedily)
        nb = defaultdict(list)
        for i, j in once:
            nb[i].append(j)
            nb[j].append(i)
        pinch = sum(1 for k, v in nb.items() if len(v) > 2)
        left, rings = set(once), 0
        while left:
            i, j = left.pop()
            rings += 1
            start, cur, prev = i, j, i
            while cur != start:
                nxt = [k for k in nb[cur] if k != prev and (min(cur, k), max(cur, k)) in left]
                if not nxt:
                    break
                left.discard((min(cur, nxt[0]), max(cur, nxt[0])))
                prev, cur = cur, nxt[0]
        contact = Counter()
        wall_len = rise_sum = grass_len = 0.0
        base_y = []
        for e in once:
            i, j = e
            L = plen(i, j)
            across = [t for t in edges[e] if t not in comp]
            inside = [t for t in edges[e] if t in comp][0]
            if not across:
                contact["border" if on_border(i, j) else "open"] += L
                continue
            tops = {TOPO[t] for t in across}
            kind = "grass" if tops == {GRASS} else "rock" if tops & ROCK else "ground"
            contact[kind] += L
            if kind != "rock":
                base_y += [P[i][1], P[j][1]]
            if kind == "grass":
                grass_len += L
                if ny(inside) <= 0.1:
                    wall_len += L
                    rise_sum += L * (max(P[k][1] for k in T[inside]) - (P[i][1] + P[j][1]) / 2)
        rim_len = sum(contact.values())
        pts = P[sorted({k for t in comp for k in T[t]})]
        x0, x1, z0, z1 = pts[:, 0].min(), pts[:, 0].max(), pts[:, 2].min(), pts[:, 2].max()
        blks = sorted({BLK[t] for t in comp})
        obj = any(((V[:, 0] >= x0) & (V[:, 0] <= x1) & (V[:, 2] >= z0) & (V[:, 2] <= z1)).any()
                  for b in blks if (V := objects.get(b)) is not None)
        topos = sorted({TOPO[t] for t in comp})
        spread = (float(np.percentile(base_y, 90) - np.percentile(base_y, 10)) if base_y else None)
        row = {"tris": len(comp), "blocks": [list(b) for b in blks], "topos": topos,
               "extent": [round(float(x1 - x0), 1), round(float(z1 - z0), 1)],
               "centre": [round(float(x0 + x1) / 2, 1), round(float(z0 + z1) / 2, 1)],
               "rings": rings, "pinches": pinch,
               "contact": {k: round(v, 1) for k, v in contact.items()},
               "grass_share": round(contact["grass"] / rim_len, 3) if rim_len else 0.0,
               "walled_share": round(wall_len / grass_len, 3) if grass_len else 0.0,
               "wall_rise": round(rise_sum / wall_len, 2) if wall_len else None,
               "rim_spread": None if spread is None else round(spread, 2),
               "base_y": round(float(np.median(base_y)), 2) if base_y else None,
               "object_in_bbox": bool(obj)}
        row["qualified"] = (rings == 1 and pinch == 0 and row["grass_share"] >= 0.95 and row["walled_share"] >= 0.90
                            and spread is not None and spread <= 1.5 and not obj and topos == [37])
        rows.append(row)
    print(f"{len(rows)} forest blobs of >= {MIN_TRIS} tris")
    print(f"{'tris':>5} {'blocks':22s} {'extent':12s} {'topo':8s} {'rings':>5} {'grass':>6} {'walled':>6} {'rise':>5} "
          f"{'spread':>6} {'baseY':>6} obj  Q   contact")
    for r in rows:
        print(f"{r['tris']:5d} {str([tuple(b) for b in r['blocks']])[:22]:22s} {str(r['extent']):12s} "
              f"{str(r['topos']):8s} {r['rings']:>3}{'+p' if r['pinches'] else '  '} {r['grass_share']:6.2f} "
              f"{r['walled_share']:6.2f} {r['wall_rise'] if r['wall_rise'] is not None else '-':>5} "
              f"{r['rim_spread'] if r['rim_spread'] is not None else '-':>6} {r['base_y'] if r['base_y'] is not None else '-':>6} "
              f"{'Y' if r['object_in_bbox'] else '.':>3}  {'Q' if r['qualified'] else '.'}  {r['contact']}")
    ctl = [r for r in rows if [15, 15] in r["blocks"] and r["tris"] >= 100]
    print("positive control (15,15):", "QUALIFIES" if ctl and ctl[0]["qualified"] else "FAILS -- the screen is wrong",
          ctl[0] if ctl else None)
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "census.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
