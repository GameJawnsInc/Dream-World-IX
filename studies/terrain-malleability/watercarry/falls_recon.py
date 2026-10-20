"""FALLS.md (RECON.md R2): can `world-mountain`'s ensemble carry take cluster D's falls? A RECON -- it reads stock
bytes only and writes nothing but out/falls_recon.json and out/falls_plan.png.

Cluster D's falls drops from a plateau at 26 to the lowland. A massif carry's rim sits on lowland, so by THE
CUT-LINE LAW (a lawful cut crosses only land at y <= 6.5; high relief is cut around, never through) the smallest
lawful unit holding the falls is the whole high component it stands in. Predictions are registered in FALLS.md.

  A. THE SYSTEM: cluster D's water parts welded into one component; its two tips (graph-far ends), each with its
     nearest rock and sea, and the Terrain topographs welded to each part (the banks).
  B. THE HIGH COMPONENTS, map-wide: terrain tris whose top exceeds 6.5, joined by shared plan edges (5c's
     `high_component`, escarpment_recon.py). Seeds: each falls sheet's lip, cluster D's two tips, cluster C's source
     (5c's seed, the calibration: it must reproduce 5c's 20,904 tris), and the CONTROL, the horseshoe's falls lips.
     The x seam is not joined (no component here comes near it).
  C. THE ROCK COMPONENTS, map-wide: topo-49 terrain tris joined by shared 3D edges (the massif census's definition,
     ../mountaindonors/census.py), and the one(s) each falls welds to, ranked by size.
  D. THE FALLS, D against the horseshoe: sheets, drop, and what every sheet boundary edge welds to (top / bottom /
     side; Object read too, it owns part of the horseshoe's aperture ring), and the ground at each foot.
  E. THE SMALL COMPONENTS a falls lip also lands in (under 200 tris): what lies across each of their plan boundary
     edges -- water parts, lowland, or nothing.
  F. THE SPRAY: the engine's fixed-point world effect AlexandriaWaterfall (WorldEffect 4 = pack sub-table 41 + 4 of
     discmr.img, ff9.cs:8863-8865, records per WMBinarayReaderExtension.ReadEffectData), each emitter's distance to
     the nearest falls foot. Placed by world coordinates, so it stays home whatever a carry does.
RUN:  py studies/terrain-malleability/watercarry/falls_recon.py
"""
from __future__ import annotations

import heapq
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
from ff9mapkit.world import extract as X, river as R, worldpack as WP  # noqa: E402
from ff9mapkit.world.interior import MOUNTAIN_ROCK_TOPOS, kk3  # noqa: E402

CUT_Y = 6.5                                   # THE CUT-LINE LAW's lowland ceiling (v4_rect_scan.CUT_Y)
SEED_R = 8.0                                  # 5c's seed radius round a point
WATER = ("falls", "river", "riverjoint", "stream")
SEA = ("sea1", "sea2", "sea3", "sea4", "sea5", "beach1", "beach2")
SEAP = ("sea1", "sea2", "sea3", "beach1", "beach2")   # the termination census's sea set (sea4/5 reported apart)
ROCK = set(MOUNTAIN_ROCK_TOPOS)
SITES = {"D": [(18, 13), (19, 10), (19, 11), (19, 12), (19, 13), (20, 10), (20, 11)],
         "horseshoe": [(5, 15), (5, 16), (6, 15), (6, 16)]}
C_SOURCE = (1128.6, -917.8)                   # cluster C's source contact (RUNG5.md, 5c's seed)
FIVE_C = {"tris": 20904, "blocks": 65}        # 5c's measured component (out/escarpment_recon.json)
kxz = lambda p: (round(float(p[0]), 3), round(float(p[2]), 3))   # noqa: E731
k3 = lambda p: kk3(tuple(float(v) for v in p))                   # noqa: E731


def read_parts():
    bp = X.block_parts(disc=1)
    terrain = []
    for (bx, by), parts in sorted(bp.items()):
        if "terrain" in parts:
            terrain += R.block_tris(X.read_block(bx, by, disc=1, part="terrain"), bx, by, "terrain")
    near = set()
    for blks in SITES.values():
        for bx, by in blks:
            near |= {(bx + dx, by + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    parts = []
    for (bx, by) in sorted(near):
        for part in WATER + SEA + ("object",):
            if part in bp.get((bx, by), ()):
                parts += R.block_tris(X.read_block(bx, by, disc=1, part=part), bx, by, part)
    return terrain, parts


def components(items, keys_of):
    """Union-find over items sharing any key; returns a label per item."""
    parent = list(range(len(items)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    first = {}
    for i, it in enumerate(items):
        for k in keys_of(it):
            if k in first:
                a, b = find(i), find(first[k])
                if a != b:
                    parent[a] = b
            else:
                first[k] = i
    return [find(i) for i in range(len(items))]


def plan_edges(t):
    P = t["P"]
    return [tuple(sorted((kxz(P[a]), kxz(P[b])))) for a, b in ((0, 1), (1, 2), (2, 0))]


def edges3(t):
    P = t["P"]
    return [tuple(sorted((k3(P[a]), k3(P[b])))) for a, b in ((0, 1), (1, 2), (2, 0))]


def describe(tris, ids):
    P = np.array([tris[i]["P"] for i in ids])
    cen = P.mean(axis=1)
    area = float(sum(0.5 * abs(np.cross(p[1] - p[0], p[2] - p[0])[1]) for p in P))
    dec = [X.decode_id(tris[i]["idall"]) for i in ids]
    blks = sorted({tris[i]["blk"] for i in ids})
    return {"tris": len(ids), "blocks": len(blks), "block_list": blks if len(blks) <= 12 else None,
            "bbox_x": [round(float(cen[:, 0].min()), 1), round(float(cen[:, 0].max()), 1)],
            "bbox_z": [round(float(cen[:, 2].min()), 1), round(float(cen[:, 2].max()), 1)],
            "y_max": round(float(P[:, :, 1].max()), 2), "plan_area_u2": round(area),
            "topos": dict(Counter(d["topograph"] for d in dec).most_common(8)),
            "tower_tris": sum(1 for d in dec if d["topograph"] == 59),
            "event_tris": sum(1 for d in dec if d["event"])}


# ---- A. the system ------------------------------------------------------------------------------------------------
def system(parts, terrain, site):
    blks = set(SITES[site])
    W = [t for t in parts if t["part"] in WATER and t["blk"] in blks]
    lab = components(W, lambda t: [k3(p) for p in t["P"]])
    comps = Counter(lab)
    adj = defaultdict(dict)
    for t in W:
        for a, b in ((0, 1), (1, 2), (2, 0)):
            pa, pb = k3(t["P"][a]), k3(t["P"][b])
            d = float(np.linalg.norm(t["P"][a] - t["P"][b]))
            adj[pa][pb] = adj[pb][pa] = d

    def far(src):
        dist, pq = {src: 0.0}, [(0.0, src)]
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist[u]:
                continue
            for v, w in adj[u].items():
                if d + w < dist.get(v, 1e18):
                    dist[v] = d + w
                    heapq.heappush(pq, (d + w, v))
        v = max(dist, key=dist.get)
        return v, dist[v]
    a, _ = far(next(iter(adj)))
    b, length = far(a)
    rock = np.array([t["P"].mean(axis=0) for t in terrain if t["topo"] in ROCK])
    seap = np.vstack([t["P"] for t in parts if t["part"] in SEAP] or [np.zeros((0, 3))])
    deep = np.vstack([t["P"] for t in parts if t["part"] in ("sea4", "sea5")] or [np.zeros((0, 3))])

    def tip(p):
        dr = float(np.min(np.hypot(rock[:, 0] - p[0], rock[:, 2] - p[2])))
        ds = float(np.min(np.hypot(seap[:, 0] - p[0], seap[:, 2] - p[2]))) if len(seap) else None
        dd = float(np.min(np.hypot(deep[:, 0] - p[0], deep[:, 2] - p[2]))) if len(deep) else None
        cls = "SEA" if ds is not None and ds < 8 else "MASSIF" if dr < 8 else "OPEN" if dr > 15 and (ds or 99) > 15 \
            else "near"
        ring = [t for t in terrain if np.hypot(*(t["P"].mean(axis=0)[[0, 2]] - np.array([p[0], p[2]]))) < 8.0]
        return {"at": [round(p[0], 1), round(p[1], 2), round(p[2], 1)], "class": cls, "rock_u": round(dr, 1),
                "sea_u": None if ds is None else round(ds, 1), "deep_sea_u": None if dd is None else round(dd, 1),
                "terrain_within_8u": dict(Counter(t["topo"] for t in ring).most_common(6))}
    tv = {}
    for t in terrain:
        if t["blk"] in blks or any(abs(t["blk"][0] - x) <= 1 and abs(t["blk"][1] - y) <= 1 for x, y in blks):
            for p in t["P"]:
                tv.setdefault(k3(p), Counter())[t["topo"]] += 1
    banks = {}
    for part in WATER:
        c = Counter()
        for t in (t for t in W if t["part"] == part):
            for p in t["P"]:
                c.update(tv.get(k3(p), Counter()))
        if c:
            banks[part] = dict(c.most_common(6))
    return {"water_tris": len(W), "components": len(comps), "by_part": dict(Counter(t["part"] for t in W)),
            "length_u": round(length, 1), "tips": [tip(a), tip(b)], "welded_terrain_topos": banks}


# ---- B. high components ---------------------------------------------------------------------------------------------
def high_components(terrain):
    hi = [i for i, t in enumerate(terrain) if t["P"][:, 1].max() > CUT_Y]
    lab = components([terrain[i] for i in hi], plan_edges)
    label = {hi[j]: lab[j] for j in range(len(hi))}
    members = defaultdict(list)
    for i, l in label.items():
        members[l].append(i)
    rank = {l: r for r, l in enumerate(sorted(members, key=lambda l: -len(members[l])))}
    return label, members, rank


def seed_hits(cen, label, members, rank, pt):
    d = np.hypot(cen[:, 0] - pt[0], cen[:, 2] - pt[1])
    hit = Counter(label[i] for i in np.where(d < SEED_R)[0] if i in label)
    near_hi = min((float(d[i]) for i in label), default=None)
    return {"seeds": sum(hit.values()), "nearest_high_tri_u": None if near_hi is None else round(near_hi, 1),
            "components": [{"rank": rank[l], "tris": len(members[l]), "seed_tris": n} for l, n in hit.most_common()]}


# ---- C. rock components ---------------------------------------------------------------------------------------------
def rock_components(terrain):
    rk = [i for i, t in enumerate(terrain) if t["topo"] in ROCK]
    lab = components([terrain[i] for i in rk], edges3)
    label = {rk[j]: lab[j] for j in range(len(rk))}
    members = defaultdict(list)
    for i, l in label.items():
        members[l].append(i)
    rank = {l: r for r, l in enumerate(sorted(members, key=lambda l: -len(members[l])))}
    return label, members, rank


# ---- D. the falls -----------------------------------------------------------------------------------------------
def falls_anatomy(parts, terrain, site, rock_lab, rock_members, rock_rank):
    blks = set(SITES[site])
    F = [t for t in parts if t["part"] == "falls" and t["blk"] in blks]
    sheets = defaultdict(list)
    for t, l in zip(F, components(F, lambda t: [k3(p) for p in t["P"]])):
        sheets[l].append(t)
    others = [t for t in parts if t["part"] != "falls"] + [t for t in terrain if t["blk"] in
                                                           {(x + dx, y + dy) for x, y in blks for dx in (-1, 0, 1)
                                                            for dy in (-1, 0, 1)}]
    by_edge, by_vert = defaultdict(list), defaultdict(list)
    for t in others:
        for e in edges3(t):
            by_edge[e].append(t)
        for p in t["P"]:
            by_vert[k3(p)].append(t)
    tidx = {id(t): i for i, t in enumerate(terrain)}
    out = []
    for sh in sheets.values():
        P = np.vstack([t["P"] for t in sh])
        top, bot = float(P[:, 1].max()), float(P[:, 1].min())
        eu = Counter(e for t in sh for e in edges3(t))
        welds = {"top": Counter(), "bottom": Counter(), "side": Counter()}
        rock_comps = Counter()
        for e, n in eu.items():
            if n != 1:
                continue
            ey = (e[0][1] + e[1][1]) / 2
            where = "top" if ey >= top - 1.0 else "bottom" if ey <= bot + 1.0 else "side"
            across = by_edge.get(e, [])
            if across:
                for t in across:
                    welds[where][f"{t['part']}:{t['topo']}"] += 1
                    if t["part"] == "terrain" and t["topo"] in ROCK and tidx.get(id(t)) in rock_lab:
                        rock_comps[rock_lab[tidx[id(t)]]] += 1
            else:
                va, vb = by_vert.get(e[0], []), by_vert.get(e[1], [])
                if va and vb:
                    welds[where]["verts-only:" + "/".join(sorted({t["part"] for t in va + vb}))] += 1
                else:
                    welds[where]["open"] += 1
        foot = P[P[:, 1] <= bot + 0.5].mean(axis=0)
        lip = P[P[:, 1] >= top - 0.5].mean(axis=0)
        ring = [t for t in terrain if np.hypot(*(t["P"].mean(axis=0)[[0, 2]] - foot[[0, 2]])) < 10.0]
        out.append({"block": sorted({t["blk"] for t in sh}), "tris": len(sh), "lip_y": round(top, 2),
                    "foot_y": round(bot, 2), "drop_u": round(top - bot, 2),
                    "lip": [round(float(lip[0]), 1), round(float(lip[2]), 1)],
                    "foot": [round(float(foot[0]), 1), round(float(foot[2]), 1)],
                    "width_u": round(float(np.ptp(P[:, [0, 2]], axis=0).max()), 1),
                    "welds": {k: dict(v.most_common(6)) for k, v in welds.items()},
                    "rock_components": [{"rank": rock_rank[l], "tris": len(rock_members[l]), "edges": n}
                                        for l, n in rock_comps.most_common()],
                    "foot_ground": {"topos": dict(Counter(t["topo"] for t in ring).most_common(6)),
                                    "mean_y": round(float(np.mean([t["P"][:, 1].mean() for t in ring])), 2)
                                    if ring else None}})
    return sorted(out, key=lambda s: -s["tris"])


def ring_census(terrain, parts, ids):
    """What lies across each plan once-edge of a terrain-tri set: part:topo, with high/low for terrain."""
    mine = set(ids)
    eu = Counter(e for i in ids for e in plan_edges(terrain[i]))
    once = {e for e, n in eu.items() if n == 1}
    across = Counter()
    hits = defaultdict(list)
    for j, t in enumerate(terrain):
        if j not in mine:
            for e in plan_edges(t):
                if e in once:
                    hits[e].append(f"terrain:{t['topo']}:{'high' if t['P'][:, 1].max() > CUT_Y else 'low'}")
    for t in parts:
        for e in plan_edges(t):
            if e in once:
                hits[e].append(f"{t['part']}:{t['topo']}")
    for e in once:
        across.update(set(hits[e]) or {"nothing"})
    return {"once_edges": len(once), "across": dict(across.most_common(10))}


def spray(falls):
    import struct
    d = WP.load_discmr(1)
    pos, out = d.pack_off + d.offs[41 + 4], []
    for k in range(64):
        r = struct.unpack_from("<6i6h4h5i", d._data, pos + 64 * k)
        if r[12] < 0:                                   # NOT_REGISTERED ends the list
            break
        x, y, z = r[0] / 256, -r[1] / 256, r[2] / 256   # fixed point /256; PSX y points down
        feet = [(s["foot"], s["foot_y"], site) for site in falls for s in falls[site]]
        f, fy, site = min(feet, key=lambda f: np.hypot(f[0][0] - x, f[0][1] - z))
        out.append({"at": [round(x, 1), round(y, 2), round(z, 1)], "sps": r[12], "rnd": r[14],
                    "nearest_foot": f, "site": site, "plan_u": round(float(np.hypot(f[0] - x, f[1] - z)), 2),
                    "above_foot_u": round(y - fy, 2)})
    return out


def plan(terrain, parts, label, members, rank, falls, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    views = {"D": (1080, 1360, -940, -640), "horseshoe": (290, 470, -1100, -940)}
    fig, axs = plt.subplots(1, 2, figsize=(15, 8))
    for ax, (site, (x0, x1, z0, z1)) in zip(axs, views.items()):
        sel = [i for i, t in enumerate(terrain) if x0 - 8 < t["P"][:, 0].mean() < x1 + 8
               and z0 - 8 < t["P"][:, 2].mean() < z1 + 8]
        big = {l for l in members if rank[l] == 0}
        col = []
        for i in sel:
            if i not in label:
                col.append("#d9e8c4")
            elif label[i] in big:
                col.append("#8a6a4a")
            else:
                col.append("#c79a5a")
        ax.add_collection(PolyCollection([terrain[i]["P"][:, [0, 2]] for i in sel], facecolors=col,
                                         edgecolors="none"))
        for t in parts:
            if t["part"] in WATER:
                c = {"falls": "#00e5ff", "river": "#1f5fd0", "riverjoint": "#1f5fd0", "stream": "#4a90e2"}[t["part"]]
                ax.add_collection(PolyCollection([t["P"][:, [0, 2]]], facecolors=c, edgecolors="none"))
        for s in falls[site]:
            ax.plot(*s["lip"], "r^", ms=9)
            ax.plot(*s["foot"], "rv", ms=9)
        if site == "D":
            ax.plot(*C_SOURCE, "ko", ms=7)
        ax.set_xlim(x0, x1)
        ax.set_ylim(z0, z1)
        ax.set_aspect("equal")
        ax.set_title(f"{site}: dark = the map's largest high component, tan = other high (> {CUT_Y}), "
                     f"pale = lowland\nwater blue, falls cyan, lip ^ foot v" + (", C's source o" if site == "D" else ""),
                     fontsize=9)
    fig.savefig(path, dpi=100, bbox_inches="tight")


def main():
    terrain, parts = read_parts()
    print(f"read {len(terrain)} terrain tris map-wide, {len(parts)} part tris round the sites", flush=True)
    rep = {"cut_y": CUT_Y, "seed_r": SEED_R, "terrain_tris": len(terrain)}
    rep["system"] = {s: system(parts, terrain, s) for s in SITES}
    label, members, rank = high_components(terrain)
    rlab, rmem, rrank = rock_components(terrain)
    rep["high_largest"] = [describe(terrain, members[l]) for l in sorted(members, key=lambda l: -len(members[l]))[:5]]
    rep["rock_largest"] = [{"tris": len(rmem[l]), "blocks": len({terrain[i]["blk"] for i in rmem[l]})}
                           for l in sorted(rmem, key=lambda l: -len(rmem[l]))[:5]]
    falls = {s: falls_anatomy(parts, terrain, s, rlab, rmem, rrank) for s in SITES}
    rep["falls"] = falls
    seeds = {"C source (5c calibration)": C_SOURCE}
    for s in SITES:
        for j, sh in enumerate(falls[s]):
            seeds[f"{s} falls sheet {j} lip"] = tuple(sh["lip"])
        for j, tp in enumerate(rep["system"][s]["tips"]):
            seeds[f"{s} tip {j} ({tp['class']}, y {tp['at'][1]})"] = (tp["at"][0], tp["at"][2])
    cen = np.array([t["P"].mean(axis=0) for t in terrain])
    rep["seeds"] = {k: seed_hits(cen, label, members, rank, v) for k, v in seeds.items()}
    for k, v in rep["seeds"].items():
        for c in v["components"]:
            l = next(l for l in members if rank[l] == c["rank"])
            c.update(describe(terrain, members[l]) if c["tris"] < 3000 or c["rank"] == 0 else {})
    small = {c["rank"] for k, v in rep["seeds"].items() if "lip" in k for c in v["components"] if c["tris"] < 200}
    rep["small_lip_components"] = {r: {**describe(terrain, members[l]), **ring_census(terrain, parts, members[l])}
                                   for r in sorted(small) for l in members if rank[l] == r}
    rep["spray"] = spray(falls)
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "falls_recon.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    plan(terrain, parts, label, members, rank, falls, HERE / "out" / "falls_plan.png")
    print(json.dumps({"system": rep["system"], "seeds": rep["seeds"], "high_largest": rep["high_largest"][:3],
                      "rock_largest": rep["rock_largest"], "small_lip_components": rep["small_lip_components"],
                      "spray": rep["spray"]},
                     indent=1, default=str))
    for s in SITES:
        for sh in falls[s]:
            print(s, json.dumps(sh, default=str))


if __name__ == "__main__":
    main()
