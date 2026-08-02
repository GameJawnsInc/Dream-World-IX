"""C1 SKEPTIC re-measurement of the curtain-grammar census claims (CURTAIN GRAMMAR study).

Independent re-implementation -- shares NO code with the instrument (curtain_census.py).
Deliberate methodological differences:

  * connected components over 2-decimal-place position-keyed shared edges (instrument: 3dp),
    per block, with a separate cross-block world-frame merge count reported as sensitivity;
  * near-vertical gate sensitivity at |ny| <= 0.1 / 0.2 / 0.3 from my own geometric normals,
    plus an independent sensor from the mesh's own vertex-normal channel;
  * raw per-block near-vertical counts with no components at all;
  * plan-edge owner histograms under BOTH counting conventions (distinct plan keys per
    component; per-tri key occurrences) since the instrument's convention is not shared;
  * top/bottom boundary verts split by per-plan-key y extremes (instrument: 2u-plan local
    y band with tol max(0.3, 0.15*band));
  * direct spot-checks by mesh read at blocks (5,11), (7,16), (15,14), (8,13), (8,14).

Run from anywhere:  py -X utf8 studies/overworld-topography/curtain_skeptic_recheck.py
Writes:             studies/overworld-topography/out/curtain_skeptic_recheck.json
"""
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

KIT = r"C:\gd\Dream-World-IX\.claude\worktrees\angry-williamson-08e8bb\ff9mapkit"
sys.path.insert(0, KIT)
from ff9mapkit.world import extract as X  # noqa: E402

TILE_U, TILE_V = 0.0625, 0.03125
ROCK_TOPO, COAST_TOPO = {49, 50}, {58}
NV_GATE = 0.2          # the census gate under test
DEG_NY = 0.05          # plan-degenerate tri: |ny| <= this, or plan area < DEG_AREA
DEG_AREA = 0.01
SPOT_BLOCKS = {(5, 11), (7, 16), (15, 14), (8, 13), (8, 14)}
SHORE_NEIGHBORHOODS = {(5, 11), (7, 16)}


def q2(v: float) -> int:
    """2-decimal-place integer position key (grid spacing is >= 1/32, so lossless)."""
    return int(round(v * 100))


def med(vals):
    return statistics.median(vals) if vals else None


def p90(vals):
    if not vals:
        return None
    s = sorted(vals)
    return s[min(len(s) - 1, int(round(0.9 * (len(s) - 1))))]


class UF:
    def __init__(self):
        self.p = {}

    def find(self, a):
        p = self.p
        while p.setdefault(a, a) != a:
            p[a] = p[p[a]]
            a = p[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def main():
    blocks = X.list_blocks(disc=1)
    skipped = []
    tot_tris = 0
    nv_counts = {0.1: 0, 0.2: 0, 0.3: 0}
    nv_vertex_normal = 0            # independent sensor: mesh vertex-normal average, |ny| <= 0.2
    per_block_nv = {}               # raw per-block NV(0.2) counts, no components
    comps = []                      # per-component records
    world_edge_owner = {}           # world 3D edge key -> global comp id (cross-block merge)
    cross_uf = UF()
    shore_coastal_verts = defaultdict(list)   # neighborhood block -> world verts of topo 53..58 tris
    shore_hood = set()
    for (sx, sy) in SHORE_NEIGHBORHOODS:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                shore_hood.add((sx + dx, sy + dy))

    for (bx, by) in blocks:
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except ValueError:
            skipped.append((bx, by))
            continue
        verts, fi, tans, uvs, nrms = bm.verts, bm.flat_index, bm.tangents, bm.uvs, bm.normals
        ntri = len(fi) // 3
        tot_tris += ntri
        wox, woz = bx * 64, -by * 64

        topo = [0] * ntri
        absny = [1.0] * ntri
        plan_area = [0.0] * ntri
        degenerate = [False] * ntri
        tile = [None] * ntri
        corners = [None] * ntri
        for t in range(ntri):
            i0, i1, i2 = fi[3 * t], fi[3 * t + 1], fi[3 * t + 2]
            v0, v1, v2 = verts[i0], verts[i1], verts[i2]
            e1 = (v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
            e2 = (v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2])
            nx = e1[1] * e2[2] - e1[2] * e2[1]
            ny = e1[2] * e2[0] - e1[0] * e2[2]
            nz = e1[0] * e2[1] - e1[1] * e2[0]
            ln = math.sqrt(nx * nx + ny * ny + nz * nz)
            a = abs(ny) / ln if ln > 1e-12 else 1.0
            absny[t] = a
            pa = 0.5 * abs(e1[0] * e2[2] - e1[2] * e2[0])
            plan_area[t] = pa
            degenerate[t] = (a <= DEG_NY) or (pa < DEG_AREA)
            topo[t] = X.decode_id(int(round(tans[i0][0])))["topograph"]
            umin = min(uvs[i0][0], uvs[i1][0], uvs[i2][0])
            vmin = min(uvs[i0][1], uvs[i1][1], uvs[i2][1])
            tile[t] = (math.floor(umin / TILE_U + 1e-9), math.floor(vmin / TILE_V + 1e-9))
            corners[t] = (i0, i1, i2)
            if ln > 1e-12:
                for thr in nv_counts:
                    if a <= thr:
                        nv_counts[thr] += 1
                if nrms is not None:
                    sn = [nrms[i0][k] + nrms[i1][k] + nrms[i2][k] for k in range(3)]
                    sl = math.sqrt(sum(c * c for c in sn))
                    if sl > 1e-12 and abs(sn[1]) / sl <= 0.2:
                        nv_vertex_normal += 1

        if (bx, by) in shore_hood:
            for t in range(ntri):
                if topo[t] in {53, 54, 55, 56, 57, 58}:
                    for i in corners[t]:
                        v = verts[i]
                        shore_coastal_verts[(bx, by)].append((wox + v[0], v[1], woz + v[2]))

        nv = [t for t in range(ntri) if absny[t] <= NV_GATE and plan_area[t] is not None]
        nv = [t for t in nv if True]
        per_block_nv[(bx, by)] = len(nv)
        if not nv:
            continue

        # --- block-wide maps (ALL tris) ---
        pos_key = {}
        for t in range(ntri):
            for i in corners[t]:
                if i not in pos_key:
                    v = verts[i]
                    pos_key[i] = (q2(v[0]), q2(v[1]), q2(v[2]))
        plan_owner = defaultdict(set)     # plan edge key -> distinct tri ids
        for t in range(ntri):
            i0, i1, i2 = corners[t]
            for a, b in ((i0, i1), (i1, i2), (i2, i0)):
                va, vb = verts[a], verts[b]
                if math.hypot(va[0] - vb[0], va[2] - vb[2]) < 0.02:
                    continue
                ka = (q2(va[0]), q2(va[2]))
                kb = (q2(vb[0]), q2(vb[2]))
                plan_owner[(min(ka, kb), max(ka, kb))].add(t)
        nv_set = set(nv)
        vert_nonnv = defaultdict(set)     # position key -> non-NV tri ids touching it
        for t in range(ntri):
            if t in nv_set:
                continue
            for i in corners[t]:
                vert_nonnv[pos_key[i]].add(t)

        # --- connected components over NV tris (shared 2dp-position edges) ---
        edge_map = defaultdict(list)
        for t in nv:
            i0, i1, i2 = corners[t]
            for a, b in ((i0, i1), (i1, i2), (i2, i0)):
                ka, kb = pos_key[a], pos_key[b]
                edge_map[(min(ka, kb), max(ka, kb))].append(t)
        uf = UF()
        for ek, ts in edge_map.items():
            for t in ts[1:]:
                uf.union(ts[0], t)
        groups = defaultdict(list)
        for t in nv:
            groups[uf.find(t)].append(t)

        for root, ts in groups.items():
            gid = len(comps)
            vset = set()
            ys = []
            for t in ts:
                for i in corners[t]:
                    vset.add(pos_key[i])
                    ys.append(verts[i][1])
            drop = max(ys) - min(ys)
            th = Counter(topo[t] for t in ts)
            own_dom, own_n = th.most_common(1)[0]
            rock_share = sum(th[k] for k in ROCK_TOPO) / len(ts)
            coast_share = sum(th[k] for k in COAST_TOPO) / len(ts)
            cls = "ROCK" if rock_share >= 0.5 else ("COAST" if coast_share >= 0.5 else "OTHER")
            degf = sum(1 for t in ts if degenerate[t]) / len(ts)

            # plan-edge owner signature, both conventions
            comp_keys = set()
            pertri_hist = Counter()
            for t in ts:
                i0, i1, i2 = corners[t]
                tri_keys = set()
                for a, b in ((i0, i1), (i1, i2), (i2, i0)):
                    va, vb = verts[a], verts[b]
                    if math.hypot(va[0] - vb[0], va[2] - vb[2]) < 0.02:
                        continue
                    ka = (q2(va[0]), q2(va[2]))
                    kb = (q2(vb[0]), q2(vb[2]))
                    tri_keys.add((min(ka, kb), max(ka, kb)))
                comp_keys |= tri_keys
                for k in tri_keys:
                    pertri_hist[len(plan_owner[k])] += 1
            distinct_hist = Counter(len(plan_owner[k]) for k in comp_keys)
            once = distinct_hist.get(1, 0)

            # top/bottom vert split by per-plan-key y extremes
            by_plan = defaultdict(list)
            for (kx, ky, kz) in vset:
                by_plan[(kx, kz)].append(ky)
            cmid = (min(ys) + max(ys)) / 2 * 100
            top_v, bot_v = [], []
            for (kx, kz), kys in by_plan.items():
                kmin, kmax = min(kys), max(kys)
                if kmax - kmin >= 30:            # >= 0.3u span at this plan point
                    for ky in kys:
                        if ky >= kmax - 5:
                            top_v.append((kx, ky, kz))
                        if ky <= kmin + 5:
                            bot_v.append((kx, ky, kz))
                else:
                    for ky in kys:
                        (top_v if ky >= cmid else bot_v).append((kx, ky, kz))
            above_c, below_c = Counter(), Counter()
            for vk in top_v:
                for t in vert_nonnv.get(vk, ()):
                    above_c[topo[t]] += 1
            for vk in bot_v:
                for t in vert_nonnv.get(vk, ()):
                    below_c[topo[t]] += 1
            above = above_c.most_common(1)[0][0] if above_c else "FREE"
            below = below_c.most_common(1)[0][0] if below_c else "FREE"

            cx = sum(verts[i][0] for t in ts for i in corners[t]) / (3 * len(ts))
            cy = sum(verts[i][1] for t in ts for i in corners[t]) / (3 * len(ts))
            cz = sum(verts[i][2] for t in ts for i in corners[t]) / (3 * len(ts))
            comps.append({
                "block": (bx, by), "gid": gid, "ntri": len(ts), "drop": drop,
                "cls": cls, "own_dom": own_dom, "degf": degf, "once": once,
                "distinct_hist": dict(distinct_hist), "pertri_hist": dict(pertri_hist),
                "above": above, "below": below,
                "tiles": Counter(tile[t] for t in ts),
                "world_centroid": (wox + cx, cy, woz + cz),
                "topo_hist": dict(th),
            })
            # cross-block merge bookkeeping (world-frame 3D edges)
            for t in ts:
                i0, i1, i2 = corners[t]
                for a, b in ((i0, i1), (i1, i2), (i2, i0)):
                    va, vb = verts[a], verts[b]
                    ka = (q2(wox + va[0]), q2(va[1]), q2(woz + va[2]))
                    kb = (q2(wox + vb[0]), q2(vb[1]), q2(woz + vb[2]))
                    wk = (min(ka, kb), max(ka, kb))
                    if wk in world_edge_owner:
                        cross_uf.union(world_edge_owner[wk], gid)
                    else:
                        world_edge_owner[wk] = gid

    # ---------- aggregation ----------
    n_cross = len({cross_uf.find(c["gid"]) for c in comps})
    sub = [c for c in comps if c["drop"] >= 1.0]
    rock = [c for c in sub if c["cls"] == "ROCK"]
    coast = [c for c in sub if c["cls"] == "COAST"]
    other = [c for c in sub if c["cls"] == "OTHER"]
    curtain = [c for c in other if c["degf"] >= 0.9]
    sloped = [c for c in other if c["degf"] <= 0.1]
    mixed = [c for c in other if 0.1 < c["degf"] < 0.9]

    def agg(group):
        return {
            "comps": len(group),
            "tris": sum(c["ntri"] for c in group),
            "zero_once": sum(1 for c in group if c["once"] == 0),
            "above_cont": sum(1 for c in group if c["above"] == c["own_dom"]),
            "below_free": sum(1 for c in group if c["below"] == "FREE"),
            "below_own": sum(1 for c in group if c["below"] == c["own_dom"]),
            "drop_med": med([c["drop"] for c in group]),
            "drop_p90": p90([c["drop"] for c in group]),
            "drop_max": max((c["drop"] for c in group), default=None),
            "size_med": med([c["ntri"] for c in group]),
            "size_max": max((c["ntri"] for c in group), default=None),
        }

    def hist_sum(group, key):
        h = Counter()
        for c in group:
            for k, v in c[key].items():
                h[k] += v
        return dict(sorted(h.items()))

    def once_frac(group, key):
        h = Counter()
        for c in group:
            for k, v in c[key].items():
                h[k] += v
        tot = sum(h.values())
        return (h.get(1, 0), tot, (h.get(1, 0) / tot if tot else None))

    contexts = Counter(f'{c["above"]}|{c["below"]}' for c in curtain)
    above_totals = Counter(c["above"] for c in curtain)
    tiles_by_above = {}
    for fam, sel in (("38", lambda a: a == 38), ("36_37", lambda a: a in (36, 37)),
                     ("59", lambda a: a == 59)):
        tc = Counter()
        for c in curtain:
            if sel(c["above"]):
                tc.update(c["tiles"])
        tiles_by_above[fam] = [(str(k), v) for k, v in tc.most_common(6)]
    all3 = sum(1 for c in other
               if c["degf"] >= 0.9 and c["once"] == 0 and c["above"] == c["own_dom"])
    other_zero_once = sum(1 for c in other if c["once"] == 0)
    other_above_cont = sum(1 for c in other if c["above"] == c["own_dom"])
    sloped_ctx = Counter(f'{c["above"]}|{c["below"]}' for c in sloped)
    mixed_zero_once = sum(1 for c in mixed if c["once"] == 0)
    sloped_once_fracs = []
    for c in sloped:
        tot = sum(c["distinct_hist"].values())
        if tot:
            sloped_once_fracs.append(c["once"] / tot)
    coast_below_58 = sum(1 for c in coast if c["below"] == 58)
    curtain_dhist = hist_sum(curtain, "distinct_hist")
    curtain_phist = hist_sum(curtain, "pertri_hist")

    spot = {}
    for b in sorted(SPOT_BLOCKS):
        rows = []
        for c in comps:
            if c["block"] == tuple(b):
                rows.append({
                    "ntri": c["ntri"], "drop": round(c["drop"], 2),
                    "cls": c["cls"], "own_dom": c["own_dom"],
                    "degf": round(c["degf"], 2), "once": c["once"],
                    "above": c["above"], "below": c["below"],
                    "distinct_hist": c["distinct_hist"], "pertri_hist": c["pertri_hist"],
                    "world_centroid": [round(v, 1) for v in c["world_centroid"]],
                    "tiles": [(str(k), v) for k, v in c["tiles"].most_common(4)],
                })
        spot[str(b)] = sorted(rows, key=lambda r: -r["ntri"])

    # shore-adjacency: min distance from the named comps to coastal/sea-topo terrain verts
    shore_checks = {}
    for (b, target) in (((5, 11), (331.1, 4.1, -723.9)), ((7, 16), (474.6, 5.2, -1053.8))):
        best = None
        for c in comps:
            if c["block"] == b:
                d = math.dist(c["world_centroid"], target)
                if best is None or d < best[0]:
                    best = (d, c)
        row = {"found": best is not None}
        if best:
            d, c = best
            cw = c["world_centroid"]
            mind = None
            for nb, pts in shore_coastal_verts.items():
                for p in pts:
                    dd = math.hypot(cw[0] - p[0], cw[2] - p[2])
                    mind = dd if mind is None else min(mind, dd)
            row.update({"centroid_dist_to_claim": round(d, 2), "ntri": c["ntri"],
                        "drop": round(c["drop"], 2), "degf": round(c["degf"], 2),
                        "once": c["once"], "cls": c["cls"], "above": c["above"],
                        "below": c["below"],
                        "world_centroid": [round(v, 1) for v in cw],
                        "min_plan_dist_to_coastal_topo": (round(mind, 2) if mind is not None else None)})
        shore_checks[str(b)] = row

    out = {
        "population": {
            "blocks_listed": len(blocks), "blocks_skipped": skipped,
            "total_terrain_tris": tot_tris,
            "nv_by_gate": {str(k): v for k, v in nv_counts.items()},
            "nv_vertex_normal_sensor_0.2": nv_vertex_normal,
            "components_all": len(comps), "components_substantive": len(sub),
            "components_cross_block_merged": n_cross,
            "top10_blocks_by_nv": sorted(per_block_nv.items(), key=lambda kv: -kv[1])[:10],
            "blocks_with_nv": sum(1 for v in per_block_nv.values() if v),
        },
        "classes": {"ROCK": agg(rock), "COAST": agg(coast), "OTHER": agg(other)},
        "other_split": {
            "curtain_degf_ge_0.9": agg(curtain),
            "sloped_degf_le_0.1": agg(sloped),
            "mixed": agg(mixed),
            "other_zero_once": other_zero_once,
            "other_above_cont": other_above_cont,
            "all_three_at_once": all3,
            "mixed_zero_once": mixed_zero_once,
            "sloped_once_frac_med": med(sloped_once_fracs),
            "sloped_ctx_top": sloped_ctx.most_common(6),
        },
        "owner_signature": {
            "curtain_distinct_hist": curtain_dhist,
            "curtain_pertri_hist": curtain_phist,
            "rock_once": once_frac(rock, "distinct_hist"),
            "rock_hist": hist_sum(rock, "distinct_hist"),
            "rock_pertri_once": once_frac(rock, "pertri_hist"),
            "coast_once": once_frac(coast, "distinct_hist"),
            "coast_pertri_once": once_frac(coast, "pertri_hist"),
        },
        "contexts": {
            "above_totals": {str(k): v for k, v in above_totals.most_common(12)},
            "ctx_top": contexts.most_common(12),
            "n_distinct_ctx_other": len(set(f'{c["above"]}|{c["below"]}' for c in other)),
            "tiles_by_above": tiles_by_above,
            "coast_below_58": [coast_below_58, len(coast)],
        },
        "spot_checks": spot,
        "shore_checks": shore_checks,
    }
    od = Path(__file__).resolve().parent / "out"
    od.mkdir(exist_ok=True)
    (od / "curtain_skeptic_recheck.json").write_text(json.dumps(out, indent=1, default=str),
                                                    encoding="utf-8")
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
