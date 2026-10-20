"""LAKES.md: which stock sea patches are joined to the open ocean? A RECON -- it reads stock disc-1 bytes only and
writes nothing but out/lakes_recon.json and out/lakes_plan.png. Predictions are registered in LAKES.md.

  A. THE WATER GRAPH: every sea tri (sea1-6, sea4f) of every prefab block, joined by a shared plan vertex (keys wrap:
     x mod 1536, z mod 1280). Each prefab-less block (the engine's SeaBlockPrefab = open ocean) is one node, joined to
     its prefab-less 4-neighbours (wrapped) and to every sea tri with an edge on their common border.
  B. THE PARTITION: the component holding the prefab-less blocks is THE OCEAN; any component without one is an
     enclosed body, described by its water, its shore ring (terrain / beach tris sharing a plan vertex with it), its
     plan distance to the ocean, water parts within 8u and entrance tiles within 16u.
  C. HIDDEN JOINS: the same partition from EXPOSED sea tris only (hidden = terrain above y + 0.05 at the centroid).
  D. THE REACH: for each named site, the water-path length (Dijkstra over shared-vertex tri centroids) from the open
     ocean's border tris, against the straight plan distance to the nearest prefab-less block.
  The controls: cluster C's mouth water at (16,15) must land in THE OCEAN; and THE BREAK-IT -- drop the sea tris of
  a site's 8 neighbour blocks and its own water must come out enclosed (unless it borders a prefab-less block), or the
  instrument cannot find a lake at all.
RUN:  py studies/terrain-malleability/watercarry/lakes_recon.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__
from ff9mapkit.world import extract as X, river as R  # noqa: E402

W, H, NBX, NBY, B = 1536.0, 1280.0, 24, 20, 64.0
SEA = ("sea1", "sea2", "sea3", "sea4", "sea4f", "sea5", "sea6")
BEACH = ("beach1", "beach2")
WATERP = ("river", "stream", "riverjoint", "falls")
CUT_Y = 6.5
HIDE_EPS = 0.05
Y02_SHORES = [(3, 12), (4, 13), (5, 13), (7, 17), (9, 17)]
OPEN_BAYS = [(17, 10), (14, 4), (4, 8)]
CONTROL = (16, 15)


def wkey(p):
    return (round(float(p[0]) % W, 3) % W, round(float(-p[2]) % H, 3) % H)


class UF:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, i):
        while self.p[i] != i:
            self.p[i] = self.p[self.p[i]]
            i = self.p[i]
        return i

    def union(self, a, b):
        a, b = self.find(a), self.find(b)
        if a != b:
            self.p[a] = b


def read_all():
    bp = X.block_parts(disc=1)
    sea, shore, water, terrain = [], [], [], []
    for (bx, by), parts in sorted(bp.items()):
        for part in parts:
            if part in SEA or part in BEACH or part in WATERP or part == "terrain":
                tris = R.block_tris(X.read_block(bx, by, disc=1, part=part), bx, by, part)
                (sea if part in SEA else shore if part in BEACH else water if part in WATERP else terrain).extend(tris)
    return bp, sea, shore, water, terrain


def hidden_mask(sea, terrain):
    """Per sea tri: terrain above the water (> y + HIDE_EPS) at its centroid, tested within its own block."""
    by_blk = defaultdict(list)
    for t in terrain:
        by_blk[t["blk"]].append(t["P"])
    idx = defaultdict(list)
    for i, t in enumerate(sea):
        idx[t["blk"]].append(i)
    hid = np.zeros(len(sea), bool)
    top = np.full(len(sea), np.nan)
    for blk, ids in idx.items():
        if blk not in by_blk:
            continue
        T = np.array(by_blk[blk])                                    # (N,3,3)
        C = np.array([sea[i]["P"].mean(axis=0) for i in ids])        # (S,3)
        A, Bv, Cv = T[:, 0], T[:, 1], T[:, 2]
        v0, v1 = (Cv - A)[:, [0, 2]], (Bv - A)[:, [0, 2]]
        d = v0[:, 0] * v1[:, 1] - v0[:, 1] * v1[:, 0]
        ok = np.abs(d) > 1e-12
        dd = np.where(ok, d, 1.0)
        v2 = C[:, None, [0, 2]] - A[None, :, [0, 2]]                 # (S,N,2)
        u = (v2[..., 0] * v1[None, :, 1] - v2[..., 1] * v1[None, :, 0]) / dd[None]
        w = (v0[None, :, 0] * v2[..., 1] - v0[None, :, 1] * v2[..., 0]) / dd[None]
        inside = ok[None] & (u >= -1e-6) & (w >= -1e-6) & (u + w <= 1 + 1e-6)
        y = A[None, :, 1] + u * (Cv - A)[None, :, 1] + w * (Bv - A)[None, :, 1]
        ymax = np.where(inside, y, -np.inf).max(axis=1)
        for k, i in enumerate(ids):
            if np.isfinite(ymax[k]):
                top[i] = ymax[k]
                hid[i] = ymax[k] > C[k, 1] + HIDE_EPS
    return hid, top


def border_edges(sea, bp):
    """{tri: [prefab-less neighbour block]} for every sea tri with an edge on a prefab-less block's border."""
    out = defaultdict(list)
    for i, t in enumerate(sea):
        bx, by = t["blk"]
        P = t["P"]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            pa, pb = P[a], P[b]
            for ax, val, nb in (("x", B * bx, (bx - 1, by)), ("x", B * (bx + 1), (bx + 1, by)),
                                ("z", B * by, (bx, by - 1)), ("z", B * (by + 1), (bx, by + 1))):
                ca, cb = (pa[0], pb[0]) if ax == "x" else (-pa[2], -pb[2])
                nbw = (nb[0] % NBX, nb[1] % NBY)
                if abs(ca - val) < 1e-3 and abs(cb - val) < 1e-3 and nbw not in bp:
                    out[i].append(nbw)
    return out


def partition(sea, bp, keep, border=None):
    """Union-find over the kept sea tris + one node per prefab-less block. Returns (label per tri, ocean labels)."""
    n = len(sea)
    open_blocks = [(bx, by) for bx in range(NBX) for by in range(NBY) if (bx, by) not in bp]
    onode = {b: n + k for k, b in enumerate(open_blocks)}
    uf = UF(n + len(open_blocks))
    border = border_edges(sea, bp) if border is None else border
    for (bx, by), i in onode.items():
        for dx, dy in ((1, 0), (0, 1)):
            nb = ((bx + dx) % NBX, (by + dy) % NBY)
            if nb in onode:
                uf.union(i, onode[nb])
    first = {}
    for i, t in enumerate(sea):
        if not keep[i]:
            continue
        for p in t["P"]:
            k = wkey(p)
            if k in first:
                uf.union(i, first[k])
            else:
                first[k] = i
        for nbw in border.get(i, ()):
            uf.union(i, onode[nbw])
    lab = [uf.find(i) if keep[i] else None for i in range(n)]
    ocean = Counter(uf.find(j) for j in onode.values())
    return lab, ocean, open_blocks


def reach(sea, border):
    """Water-path length from the ocean's border tris to every sea tri (shared-vertex adjacency, centroid steps)."""
    import heapq
    by_v = defaultdict(list)
    for i, t in enumerate(sea):
        for p in t["P"]:
            by_v[wkey(p)].append(i)
    cen = np.array([[t["P"][:, 0].mean() % W, -t["P"][:, 2].mean() % H] for t in sea])
    dist = np.full(len(sea), np.inf)
    pq = [(0.0, i) for i in border]
    for _, i in pq:
        dist[i] = 0.0
    heapq.heapify(pq)
    while pq:
        d, i = heapq.heappop(pq)
        if d > dist[i]:
            continue
        for j in {j for p in sea[i]["P"] for j in by_v[wkey(p)]}:
            dx = abs(cen[i, 0] - cen[j, 0])
            dz = abs(cen[i, 1] - cen[j, 1])
            nd = d + float(np.hypot(min(dx, W - dx), min(dz, H - dz)))
            if nd < dist[j]:
                dist[j] = nd
                heapq.heappush(pq, (nd, j))
    return dist


def open_dist(blk, bp):
    """Plan distance (u) from a block's square to the nearest prefab-less block's square (wrapped)."""
    best = np.inf
    for bx in range(NBX):
        for by in range(NBY):
            if (bx, by) in bp:
                continue
            dx = abs(blk[0] - bx)
            dz = abs(blk[1] - by)
            dx, dz = min(dx, NBX - dx), min(dz, NBY - dz)
            best = min(best, float(np.hypot(max(0, dx - 1), max(0, dz - 1))) * B)
    return round(best, 1)


def footprint(tris):
    """Plan area of the union of the tris, on a 0.5u raster (cell centres inside any tri)."""
    P = np.array([t["P"][:, [0, 2]] for t in tris])
    lo, hi = P.reshape(-1, 2).min(axis=0), P.reshape(-1, 2).max(axis=0)
    xs = np.arange(lo[0] + 0.25, hi[0], 0.5)
    zs = np.arange(lo[1] + 0.25, hi[1], 0.5)
    if not len(xs) or not len(zs):
        return 0.0
    G = np.stack(np.meshgrid(xs, zs), -1).reshape(-1, 2)
    hit = np.zeros(len(G), bool)
    for a, b, c in P:
        m = (G[:, 0] >= min(a[0], b[0], c[0])) & (G[:, 0] <= max(a[0], b[0], c[0])) & \
            (G[:, 1] >= min(a[1], b[1], c[1])) & (G[:, 1] <= max(a[1], b[1], c[1])) & ~hit
        if not m.any():
            continue
        g = G[m]
        v0, v1, v2 = c - a, b - a, g - a
        d = v0[0] * v1[1] - v0[1] * v1[0]
        if abs(d) < 1e-12:
            continue
        u = (v2[:, 0] * v1[1] - v2[:, 1] * v1[0]) / d
        w = (v0[0] * v2[:, 1] - v0[1] * v2[:, 0]) / d
        hit[np.where(m)[0][(u >= -1e-6) & (w >= -1e-6) & (u + w <= 1 + 1e-6)]] = True
    return float(hit.sum()) * 0.25


def min_plan(A, Bp):
    if not len(A) or not len(Bp):
        return None
    best = np.inf
    for k in range(0, len(A), 512):
        a = A[k:k + 512]
        dx = np.abs(a[:, None, 0] - Bp[None, :, 0])
        dx = np.minimum(dx, W - dx)
        dz = np.abs(a[:, None, 1] - Bp[None, :, 1])
        dz = np.minimum(dz, H - dz)
        best = min(best, float(np.sqrt(dx ** 2 + dz ** 2).min()))
    return round(best, 1)


def describe(ids, sea, shore, water, terrain, ocean_xz, tkey):
    tris = [sea[i] for i in ids]
    V = np.vstack([t["P"] for t in tris])
    keys = {wkey(p) for p in V}
    ring_t = [t for t in terrain if any(wkey(p) in keys for p in t["P"])] if len(ids) < 5000 else []
    ring_b = [t for t in shore if any(wkey(p) in keys for p in t["P"])] if len(ids) < 5000 else []
    xz = V[:, [0, 2]]
    wxz = np.vstack([t["P"][:, [0, 2]] for t in water])
    ev = np.array([t["P"].mean(axis=0)[[0, 2]] for t in terrain if X.decode_id(t["idall"])["event"]])
    ring_y = np.vstack([t["P"][:, 1] for t in ring_t]) if ring_t else np.zeros((0, 3))
    return {"tris": len(tris), "blocks": sorted({t["blk"] for t in tris}),
            "parts": dict(Counter(t["part"] for t in tris)), "topos": dict(Counter(t["topo"] for t in tris)),
            "y": [round(float(V[:, 1].min()), 3), round(float(V[:, 1].max()), 3)],
            "bbox_x": [round(float(xz[:, 0].min()), 1), round(float(xz[:, 0].max()), 1)],
            "bbox_z": [round(float(xz[:, 1].min()), 1), round(float(xz[:, 1].max()), 1)],
            "footprint_u2": round(footprint(tris)) if len(tris) < 5000 else None,
            "areas": dict(Counter(X.decode_id(t["idall"])["area"] for t in tris).most_common(4)),
            "shore_terrain_topos": dict(Counter(t["topo"] for t in ring_t).most_common(8)),
            "shore_terrain_tris": len(ring_t),
            "shore_high_tris": sum(1 for t in ring_t if t["P"][:, 1].max() > CUT_Y),
            "shore_y_median_max": [round(float(np.median(ring_y)), 2), round(float(ring_y.max()), 2)]
            if len(ring_y) else None,
            "shore_beach": dict(Counter(f"{t['part']}:{t['topo']}" for t in ring_b)),
            "ocean_u": min_plan(xz, ocean_xz),
            "water_part_u": min_plan(xz, wxz),
            "entrance_tiles_16u": int(sum(1 for e in ev if min_plan(xz, e[None]) < 16.0)) if len(ev) else 0}


def plan(sea, terrain, lab, ocean_labs, bodies, path, sites=()):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    panels = [(f"body {k}: {b['blocks'][:3]} {b['footprint_u2']} u2, y {b['y']}", np.mean(b["bbox_x"]),
               np.mean(b["bbox_z"]), max(b["bbox_x"][1] - b["bbox_x"][0], b["bbox_z"][1] - b["bbox_z"][0]) / 2 + 24)
              for k, b in enumerate(bodies)] + [(f"site {blk}", (blk[0] + 0.5) * B, -(blk[1] + 0.5) * B, 72.0)
                                                for blk in sites]
    n = len(panels)
    fig = plt.figure(figsize=(16, 9 + 4 * ((n + 2) // 3)))
    ax = fig.add_subplot(1 + (n + 2) // 3, 1, 1)
    land = [t["P"][:, [0, 2]] for t in terrain]
    ax.add_collection(PolyCollection(land, facecolors="#cfc6b0", edgecolors="none"))
    col = ["#2a6fdb" if lab[i] in ocean_labs else "#e0115f" for i in range(len(sea))]
    ax.add_collection(PolyCollection([t["P"][:, [0, 2]] for t in sea], facecolors=col, edgecolors="none"))
    for k, b in enumerate(bodies):
        ax.annotate(str(k), (np.mean(b["bbox_x"]), np.mean(b["bbox_z"])), color="k", fontsize=11, weight="bold")
    ax.set_xlim(0, W)
    ax.set_ylim(-H, 0)
    ax.set_aspect("equal")
    for blk in sites:
        ax.annotate(f"{blk}", ((blk[0] + 0.5) * B, -(blk[1] + 0.5) * B), color="#b00000", fontsize=8)
    ax.set_title("disc 1 sea parts: blue = joined to the open ocean (prefab-less blocks are blank ocean), "
                 "red = enclosed; land tan", fontsize=10)
    for k, (title, cx, cz, r) in enumerate(panels):
        a2 = fig.add_subplot(1 + (n + 2) // 3, 3, 4 + k)
        sel = [t for t in terrain if abs(t["P"][:, 0].mean() - cx) < r + 8 and abs(t["P"][:, 2].mean() - cz) < r + 8]
        a2.add_collection(PolyCollection([t["P"][:, [0, 2]] for t in sel], facecolors=[
            "#8a6a4a" if t["P"][:, 1].max() > CUT_Y else "#d9e8c4" for t in sel], edgecolors="#ffffff22", lw=0.2))
        ss = [i for i, t in enumerate(sea) if abs(t["P"][:, 0].mean() - cx) < r + 8
              and abs(t["P"][:, 2].mean() - cz) < r + 8]
        a2.add_collection(PolyCollection([sea[i]["P"][:, [0, 2]] for i in ss], facecolors=[
            "#2a6fdb" if lab[i] in ocean_labs else "#e0115f" for i in ss], edgecolors="none"))
        a2.set_xlim(cx - r, cx + r)
        a2.set_ylim(cz - r, cz + r)
        a2.set_aspect("equal")
        a2.set_title(title + "  (dark = high ground, pale = lowland)", fontsize=8)
    fig.savefig(path, dpi=90, bbox_inches="tight")


def main():
    bp, sea, shore, water, terrain = read_all()
    print(f"{len(sea)} sea tris, {len(shore)} beach, {len(water)} river/stream/falls, {len(terrain)} terrain", flush=True)
    hid, top = hidden_mask(sea, terrain)
    rep = {"sea_tris": len(sea), "prefab_blocks": len(bp), "hidden_sea_tris": int(hid.sum()),
           "hidden_by_part": dict(Counter(sea[i]["part"] for i in np.where(hid)[0]))}
    border = border_edges(sea, bp)
    rep["ocean_border_tris"] = len(border)
    out = {}
    for name, keep in (("all", np.ones(len(sea), bool)), ("exposed", ~hid)):
        lab, ocean, open_blocks = partition(sea, bp, keep, border)
        ocean_labs = set(ocean)
        comps = defaultdict(list)
        for i, l in enumerate(lab):
            if l is not None:
                comps[l].append(i)
        main_ocean = max(ocean, key=ocean.get)
        in_ocean = sum(len(comps[l]) for l in ocean_labs)
        kept = int(keep.sum())
        bodies_ids = sorted((ids for l, ids in comps.items() if l not in ocean_labs), key=len, reverse=True)
        ocean_xz = np.vstack([sea[i]["P"][:, [0, 2]] for l in ocean_labs for i in comps[l]])
        out[name] = {"lab": lab, "ocean_labs": ocean_labs, "bodies_ids": bodies_ids}
        rep[name] = {
            "kept_tris": kept, "open_blocks": len(open_blocks),
            "ocean_components": len(ocean_labs),
            "ocean_component_open_blocks": sorted(ocean.values(), reverse=True),
            "main_ocean_holds_all_open_blocks": ocean[main_ocean] == len(open_blocks),
            "ocean_tri_share": round(in_ocean / max(1, kept), 5),
            "enclosed_bodies": len(bodies_ids),
            "bodies": [describe(ids, sea, shore, water, terrain, ocean_xz, None) for ids in bodies_ids],
        }

        def where(blk):
            ids = [i for i, t in enumerate(sea) if t["blk"] == blk and lab[i] is not None]
            c = Counter("ocean" if lab[i] in ocean_labs else
                        f"body {next(k for k, b in enumerate(bodies_ids) if i in set(b))}" for i in ids)
            return dict(c)
        rep[name]["control_16_15"] = where(CONTROL)
        rep[name]["y02_shores"] = {f"{b}": where(b) for b in Y02_SHORES}
        rep[name]["open_bays"] = {f"{b}": where(b) for b in OPEN_BAYS}
        cen = json.loads((HERE / "out" / "census.json").read_text()) if (HERE / "out" / "census.json").exists() else {}
        rep[name]["census_inland_sea"] = {k: where(tuple(map(int, k.split(",")))) for k in cen.get("inland_sea", {})}
        print(f"[{name}] kept {kept}; ocean comps {len(ocean_labs)} {sorted(ocean.values(), reverse=True)[:5]}; "
              f"ocean share {rep[name]['ocean_tri_share']}; enclosed bodies {len(bodies_ids)} "
              f"{[len(b) for b in bodies_ids]}", flush=True)
    dist = reach(sea, border)
    rep["reach"] = {}
    for blk in Y02_SHORES + OPEN_BAYS + [CONTROL]:
        ids = [i for i, t in enumerate(sea) if t["blk"] == blk]
        rep["reach"][f"{blk}"] = {"sea_tris": len(ids),
                                  "water_path_u": round(float(dist[ids].min()), 1) if ids else None,
                                  "water_path_u_max": round(float(dist[ids].max()), 1) if ids else None,
                                  "straight_to_open_block_u": open_dist(blk, bp),
                                  "borders_open_block": any(i in border for i in ids)}
    rep["break_it"] = {}
    for blk in Y02_SHORES + [CONTROL]:
        nbs = {((blk[0] + dx) % NBX, (blk[1] + dy) % NBY) for dx in (-1, 0, 1) for dy in (-1, 0, 1)} - {blk}
        keep = np.array([t["blk"] not in nbs for t in sea])
        lab, ocean, _ = partition(sea, bp, keep, border)
        ids = [i for i, t in enumerate(sea) if t["blk"] == blk]
        enclosed = {lab[i] for i in ids if lab[i] not in ocean}
        rep["break_it"][f"{blk}"] = {"own_tris": len(ids), "borders_open_block": any(i in border for i in ids),
                                     "enclosed_tris": sum(1 for i in ids if lab[i] not in ocean),
                                     "enclosed_bodies": len(enclosed)}
    print("reach:", json.dumps(rep["reach"]), flush=True)
    print("break-it:", json.dumps(rep["break_it"]), flush=True)
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "lakes_recon.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    plan(sea, terrain, out["all"]["lab"], out["all"]["ocean_labs"], rep["all"]["bodies"], HERE / "out" / "lakes_plan.png",
         sites=Y02_SHORES + OPEN_BAYS + [CONTROL])
    for name in ("all", "exposed"):
        r = rep[name]
        print(f"\n== {name}: control {r['control_16_15']}\n   y0.2 shores {r['y02_shores']}\n   open bays {r['open_bays']}"
              f"\n   census inland_sea {r['census_inland_sea']}")
        for k, b in enumerate(r["bodies"]):
            print(f"   body {k}: " + json.dumps(b, default=str))
    print("\nhidden sea tris:", rep["hidden_sea_tris"], rep["hidden_by_part"])


if __name__ == "__main__":
    main()
