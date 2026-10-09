"""LAND -> SEA with shallows, question 1 (2026-10-09): which shallow water belongs to which island, and where do two
islands' shallows meet?

The bare-coast sink's unit (land plus its welded shallow ladder) welds every island with shallows into a continent:
the shallow bands are continuous meshes. This splits the water another way. Land COMPONENTS are traced over terrain and
beach1 only (vertex-connected, across block borders). Every shallow tri (sea1, sea2, sea3, sea5) goes to its NEAREST
land component (plan distance, centroid to land tri edges, the 3x3 blocks round it): that component's HALO. Then:
- where a halo meets another halo (a shared edge between two shallow tris owned by different land), by part pair;
- whether sea4 lies under the shallows (a shallow tri's centroid inside a sea4 tri);
- every non-continent component's halo: tris per part, its reach from the land, and its shared edges.
Reads stock only. Writes out/sh_q1_halos_d<disc>.json.
Run (from C:\\gd\\Dream-World-IX):  py studies/terrain-malleability/land2sea/sh_q1_halos.py [disc]
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2] / "ff9mapkit"
sys.path.insert(0, str(KIT))
SHALLOW = ("sea1", "sea2", "sea3", "sea5")


def key(v):
    return (round(v[0][0], 4), round(v[0][2], 4))


def main():
    import ff9mapkit
    from ff9mapkit.world import discmirror as DM, extract as X, meshedit as ME, transplant as TR
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    disc = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    real = DM._real_parts(disc, "0_1")
    land, shallow, sea4 = [], [], defaultdict(list)
    for b in sorted(real):
        for p in ("terrain", "beach1"):
            if p in real[b]:
                land += [(p, b, t) for t in TR.world_tris(*b, p, disc=disc)]
        for p in SHALLOW:
            if p in real[b]:
                shallow += [(p, b, t) for t in TR.world_tris(*b, p, disc=disc)]
        if "sea4" in real[b]:
            for t in TR.world_tris(*b, "sea4", disc=disc):
                for ij in TR._tiles_touched(t):
                    sea4[ij].append(t)
    comps = ME.vertex_components([t for _, _, t in land])
    comp_of, cinfo = {}, []
    for ci, c in enumerate(comps):
        for t in c:
            comp_of[id(t)] = ci
    lb = {id(t): (p, b) for p, b, t in land}
    for ci, c in enumerate(comps):
        area = sum(TR._plan_clip_area([(v[0][0], v[0][2]) for v in t], -1e9, 1e9, -1e9, 1e9) for t in c)
        cinfo.append({"comp": ci, "land_u2": round(area, 1), "land_tris": len(c),
                      "blocks": sorted({lb[id(t)][1] for t in c}),
                      "parts": sorted({lb[id(t)][0] for t in c})})
    # land edge segments per block, tagged by component
    segs = defaultdict(list)
    for p, b, t in land:
        pts = [(v[0][0], v[0][2]) for v in t]
        for k in range(3):
            segs[b].append((pts[k], pts[(k + 1) % 3], comp_of[id(t)]))
    seg_np = {b: (np.array([s[0] for s in ss]), np.array([s[1] for s in ss]), np.array([s[2] for s in ss]))
              for b, ss in segs.items()}
    owner, dist = {}, {}
    by_block = defaultdict(list)
    for p, b, t in shallow:
        by_block[b].append((p, t))
    for b, items in by_block.items():
        A, B, C = [], [], []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nb = (b[0] + dx, b[1] + dy)
                if nb in seg_np:
                    A.append(seg_np[nb][0]); B.append(seg_np[nb][1]); C.append(seg_np[nb][2])
        cents = np.array([TR._plan_centroid(t) for _, t in items])
        if not A:
            for _, t in items:
                owner[id(t)], dist[id(t)] = -1, math.inf
            continue
        a, bb, cc = np.concatenate(A), np.concatenate(B), np.concatenate(C)
        ab = bb - a
        L = (ab ** 2).sum(1)
        L[L == 0] = 1e-12
        for k0 in range(0, len(cents), 256):
            pc = cents[k0:k0 + 256]
            tt = np.clip(((pc[:, None, :] - a[None]) * ab[None]).sum(2) / L[None], 0, 1)
            q = a[None] + tt[..., None] * ab[None]
            d = np.sqrt(((pc[:, None, :] - q) ** 2).sum(2))
            j = d.argmin(1)
            for k, (jj, row) in enumerate(zip(j, d)):
                t = items[k0 + k][1]
                owner[id(t)], dist[id(t)] = int(cc[jj]), float(row[jj])
    part_of = {id(t): p for p, _b, t in shallow}
    # shared edges between differently-owned shallow tris
    edges = defaultdict(list)
    for p, b, t in shallow:
        ks = [key(v) for v in t]
        for k in range(3):
            e = tuple(sorted((ks[k], ks[(k + 1) % 3])))
            if e[0] != e[1]:
                edges[e].append(t)
    shared = defaultdict(Counter)          # comp -> Counter((own part, other part, other comp))
    for e, ts in edges.items():
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                a, b = ts[i], ts[j]
                oa, ob = owner[id(a)], owner[id(b)]
                if oa != ob:
                    shared[oa][(part_of[id(a)], part_of[id(b)], ob)] += 1
                    shared[ob][(part_of[id(b)], part_of[id(a)], oa)] += 1
    # sea4 under the shallows
    under = Counter()
    for p, b, t in shallow:
        c = TR._plan_centroid(t)
        ij = (math.floor(c[0] / 4.0), math.floor(c[1] / 4.0))
        under[(p, any(TR._tri_has(s, c) for s in sea4.get(ij, ())))] += 1
    halo = defaultdict(lambda: Counter())
    reach = defaultdict(float)
    for p, b, t in shallow:
        o = owner[id(t)]
        halo[o][p] += 1
        reach[o] = max(reach[o], dist[id(t)])
    rows = []
    for ci in cinfo:
        o = ci["comp"]
        if len(ci["blocks"]) > 9:
            ci["continent"] = True
        ci["halo"] = dict(halo.get(o, {}))
        ci["halo_reach"] = round(reach.get(o, 0.0), 2)
        sh = shared.get(o, Counter())
        ci["shared_edges"] = sum(sh.values())
        ci["shared_with"] = sorted({k[2] for k in sh})
        ci["shared_pairs"] = {f"{a}|{b}": n for (a, b), n in
                              Counter({(k[0], k[1]): 0 for k in sh}).items()}
        pairs = Counter()
        for (a, b, _o), n in sh.items():
            pairs[f"{a}|{b}"] += n
        ci["shared_pairs"] = dict(pairs)
        rows.append(ci)
    res = {"disc": disc, "components": len(comps), "shallow_tris": len(shallow),
           "unowned": sum(1 for p, b, t in shallow if owner[id(t)] < 0),
           "sea4_under": {f"{p} {'over sea4' if u else 'no sea4'}": n for (p, u), n in sorted(under.items())},
           "rows": sorted(rows, key=lambda r: -r["land_u2"])}
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / f"sh_q1_halos_d{disc}.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(f"disc {disc}: {len(comps)} land components, {len(shallow)} shallow tris ({res['unowned']} with no land "
          f"in their 3x3 blocks)")
    print("sea4 under shallows:", res["sea4_under"])
    for r in res["rows"]:
        if not r["halo"] and r["land_u2"] < 50:
            continue
        print(f"  c{r['comp']:4d} {r['land_u2']:10.1f}u2 {len(r['blocks']):3d} blk {r['blocks'][:2]} {r['parts']} "
              f"halo {r['halo']} reach {r['halo_reach']} shared {r['shared_edges']} with {r['shared_with'][:6]} "
              f"{r['shared_pairs']}")


if __name__ == "__main__":
    main()
