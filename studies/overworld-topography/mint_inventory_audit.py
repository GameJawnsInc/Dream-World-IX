"""MINT INVENTORY AUDIT -- read-only forensics on the LIVE round-8 apron carry.

The code audit (apron_carry.py + terrace_wall_strip.py) enumerates every place the
builder creates or modifies a position / uv / normal / topograph tag. This instrument
MEASURES the ones whose effect is readable in the deployed bytes, and CALIBRATES each
number against two baselines the same reader produces:

  * STOCK  -- the donor neighborhood on disc 1 (what the language actually does)
  * BENCH  -- the pristine pre-wall bench (backups/terrace-strip-prewall.20260731-220001)

Nothing is written to the game. Artifacts: out/mint_inventory_audit.json (+ .png plan).

py -X utf8 mint_inventory_audit.py
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(r"C:\gd\Dream-World-IX\.claude\worktrees\angry-williamson-08e8bb")
sys.path.insert(0, str(ROOT / "ff9mapkit"))

from ff9mapkit import config                                # noqa: E402
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import mesh as M                       # noqa: E402

GAME = Path(config.find_game_path(None))
MOD = "FF9CustomMap-world"
DISC = 9
CELLS = [(5, 7), (6, 7), (7, 7), (5, 8), (6, 8), (7, 8)]
CENTER = (416.0, -512.0)
LOWLAND = 3.2
BLOCK, CELL = 64.0, 4.0
TILE_U, TILE_V = 0.0625, 0.03125
GRASS_TOPO = {0, 1, 2, 3, 42}
PLATEAU_T = {10, 11, 12}
ROCK = 49
STEP_CEIL = 2.34375                                         # engine foot step ceiling
DONOR_BLK = (15, 14)
NEIGH = [(14, 14), (16, 14), (15, 13), (15, 15)]
PREWALL = Path(r"C:\gd\Dream-World-IX\backups\terrace-strip-prewall.20260731-220001")
OUTD = Path(__file__).resolve().parent / "out"

kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))     # noqa: E731
k2 = lambda p: (round(p[0], 3), round(p[2], 3))                     # noqa: E731


def read_mesh_tris(path, bx, by):
    bm = M.blockmesh_from_ff9mesh(path, disc=DISC, x=bx, y=by, part="terrain")
    pos = bm.chan_arrays[X.CH_POS]
    nrm = bm.chan_arrays[X.CH_NRM]
    uv = bm.chan_arrays[X.CH_UV]
    tan = bm.chan_arrays[X.CH_TAN]
    ox, oz = BLOCK * bx, -BLOCK * by
    out = []
    for t in bm.tris:
        w = [(pos[i][0] + ox, pos[i][1], pos[i][2] + oz) for i in t]
        raw = [float(tan[i][0]) for i in t]
        out.append(dict(blk=(bx, by), w=w,
                        n=[tuple(float(v) for v in nrm[i]) for i in t],
                        uv=[tuple(float(v) for v in uv[i]) for i in t],
                        tanx=raw,
                        topo=X.decode_id(int(round(raw[0])))["topograph"]))
    return out


def read_stock_tris(bx, by):
    bm = X.read_block(bx, by, disc=1, part="terrain")
    V = bm.chan_arrays[X.CH_POS]
    N = bm.chan_arrays[X.CH_NRM]
    U = bm.chan_arrays[X.CH_UV]
    T = bm.chan_arrays[X.CH_TAN]
    ox, oz = BLOCK * bx, -BLOCK * by
    n = len(bm.flat_index) // 3
    out = []
    for t in range(n):
        idx = bm.flat_index[3 * t:3 * t + 3]
        w = [(V[i][0] + ox, V[i][1], V[i][2] + oz) for i in idx]
        raw = [float(T[i][0]) for i in idx]
        out.append(dict(blk=(bx, by), w=w,
                        n=[tuple(float(v) for v in N[i]) for i in idx],
                        uv=[tuple(float(v) for v in U[i]) for i in idx],
                        tanx=raw,
                        topo=X.decode_id(int(round(raw[0])))["topograph"]))
    return out


def tri_area_plan(t):
    (x1, _, z1), (x2, _, z2), (x3, _, z3) = t["w"]
    return abs((x2 - x1) * (z3 - z1) - (x3 - x1) * (z2 - z1)) / 2.0


def tri_area_3d(t):
    a, b, c = (np.array(p) for p in t["w"])
    return float(np.linalg.norm(np.cross(b - a, c - a))) / 2.0


def face_n(t):
    a, b, c = (np.array(p) for p in t["w"])
    f = np.cross(b - a, c - a)
    L = float(np.linalg.norm(f))
    return (f / L) if L > 1e-12 else np.array([0.0, 1.0, 0.0])


def ang(a, b):
    a1, a2 = np.array(a, dtype=float), np.array(b, dtype=float)
    L1, L2 = np.linalg.norm(a1), np.linalg.norm(a2)
    if L1 < 1e-9 or L2 < 1e-9:
        return None
    return math.degrees(math.acos(max(-1.0, min(1.0, float(a1 @ a2) / (L1 * L2)))))


def slope_deg(t):
    fn = face_n(t)
    ny = abs(float(fn[1]))
    return math.degrees(math.acos(max(-1.0, min(1.0, ny))))


# ------------------------------------------------------------------ shared-edge analysis
def edge_report(tris, tag, ground_only=True):
    """Per shared edge (2 tris, 2 shared positions): uv split, normal split, rise."""
    ET = defaultdict(list)
    for i, t in enumerate(tris):
        ps = [kk(p) for p in t["w"]]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            ET[tuple(sorted((ps[a], ps[b])))].append(i)
    uv_bins = Counter()
    uv_len = defaultdict(float)
    nsplit = []
    nsplit_len = 0.0
    worst_uv = []
    rise_bad = []
    n_shared = 0
    for e, ts in ET.items():
        if len(ts) != 2:
            continue
        t1, t2 = tris[ts[0]], tris[ts[1]]
        if ground_only and not (t1["topo"] in GRASS_TOPO and t2["topo"] in GRASS_TOPO):
            continue
        n_shared += 1
        L = math.dist(e[0], e[1])
        du_max = dv_max = 0.0
        ang_max = 0.0
        for P in e:
            uv1 = next((t1["uv"][k] for k in range(3) if kk(t1["w"][k]) == P), None)
            uv2 = next((t2["uv"][k] for k in range(3) if kk(t2["w"][k]) == P), None)
            n1 = next((t1["n"][k] for k in range(3) if kk(t1["w"][k]) == P), None)
            n2 = next((t2["n"][k] for k in range(3) if kk(t2["w"][k]) == P), None)
            if uv1 and uv2:
                du_max = max(du_max, abs(uv1[0] - uv2[0]) / TILE_U)
                dv_max = max(dv_max, abs(uv1[1] - uv2[1]) / TILE_V)
            if n1 and n2:
                a1 = np.array(n1)
                a2 = np.array(n2)
                L1, L2 = np.linalg.norm(a1), np.linalg.norm(a2)
                if L1 > 1e-9 and L2 > 1e-9:
                    c = float(a1 @ a2) / (L1 * L2)
                    ang_max = max(ang_max, math.degrees(
                        math.acos(max(-1.0, min(1.0, c)))))
        d = max(du_max, dv_max)
        b = ("exact" if d < 0.02 else
             "sub-tile" if d < 0.9 else
             "1 tile" if d < 1.9 else
             "2 tiles" if d < 2.9 else
             ">2 tiles")
        uv_bins[b] += 1
        uv_len[b] += L
        if d >= 0.9:
            worst_uv.append((round(d, 2), round(du_max, 2), round(dv_max, 2),
                             kk(e[0]), kk(e[1])))
        nsplit.append(ang_max)
        if ang_max > 8.0:
            nsplit_len += L
        rise = abs(e[0][1] - e[1][1])
        if rise > STEP_CEIL:
            rise_bad.append((round(rise, 2), kk(e[0]), kk(e[1])))
    ns = np.array(nsplit) if nsplit else np.zeros(1)
    worst_uv.sort(reverse=True)
    rise_bad.sort(reverse=True)
    return dict(tag=tag, n_shared_ground_edges=n_shared,
                uv_bins=dict(uv_bins),
                uv_len_u={k: round(v, 1) for k, v in uv_len.items()},
                uv_break_examples=worst_uv[:12],
                normal_split_deg=dict(
                    med=round(float(np.median(ns)), 2),
                    p90=round(float(np.percentile(ns, 90)), 2),
                    p99=round(float(np.percentile(ns, 99)), 2),
                    max=round(float(ns.max()), 2),
                    frac_over_8deg=round(float((ns > 8).mean()), 4)),
                normal_seam_len_u=round(nsplit_len, 1),
                edges_over_step_ceiling=len(rise_bad),
                step_examples=rise_bad[:8])


def straddle_report(tris, tag):
    """Tris whose verts fall on both sides of a 64u block border line."""
    n_x = n_z = 0
    area = 0.0
    hits = []
    for t in tris:
        xs = [p[0] for p in t["w"]]
        zs = [p[2] for p in t["w"]]
        bx = [math.floor(x / BLOCK) for x in xs]
        bz = [math.floor(-z / BLOCK) for z in zs]
        # ignore verts exactly ON the line (they belong to both)
        def spans(vals, blocks):
            lo, hi = min(blocks), max(blocks)
            if lo == hi:
                return False
            # a vert exactly on the line reads as the higher block; require a real span
            edge_only = all(abs(v / BLOCK - round(v / BLOCK)) < 1e-4
                            for v in vals if math.floor(v / BLOCK) != lo)
            return not edge_only
        sx = spans(xs, bx)
        sz = spans([-z for z in zs], bz)
        if sx or sz:
            n_x += 1 if sx else 0
            n_z += 1 if sz else 0
            area += tri_area_plan(t)
            hits.append((round(tri_area_plan(t), 2),
                         tuple(round(v, 1) for v in t["w"][0]), t["topo"]))
    hits.sort(reverse=True)
    return dict(tag=tag, n_tris=len(tris), straddling_x=n_x, straddling_z=n_z,
                straddle_area_u2=round(area, 1), examples=hits[:8])


def frac_idall_report(tris, tag):
    n_frac = 0
    n_mixed = 0
    frac_ex = []
    for t in tris:
        raw = t["tanx"]
        if any(abs(v - round(v)) > 1e-6 for v in raw):
            n_frac += 1
            if len(frac_ex) < 8:
                frac_ex.append([round(v, 4) for v in raw])
        if len({int(round(v)) for v in raw}) > 1:
            n_mixed += 1
    return dict(tag=tag, tris_with_fractional_idall=n_frac,
                tris_with_mixed_idall=n_mixed, examples=frac_ex)


def main() -> int:
    OUTD.mkdir(parents=True, exist_ok=True)
    rep = {}

    # ---- the three reads ------------------------------------------------------------
    live = []
    root = GAME / MOD / "FF9_Data" / "WorldMap" / f"Disc{DISC}" / "0_1"
    for (bx, by) in CELLS:
        p = root / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
        if p.is_file():
            live += read_mesh_tris(p, bx, by)
    pre = []
    for (bx, by) in CELLS:
        p = PREWALL / f"Block[{bx}][{by}] Terrain.ff9mesh"
        if p.is_file():
            pre += read_mesh_tris(p, bx, by)
    stock = []
    for (bx, by) in [DONOR_BLK] + NEIGH:
        stock += read_stock_tris(bx, by)
    print(f"live {len(live)} tris / prewall {len(pre)} tris / stock donor soup "
          f"{len(stock)} tris")
    rep["reads"] = dict(live_tris=len(live), prewall_tris=len(pre),
                        stock_soup_tris=len(stock),
                        prewall_rock_tris=sum(1 for t in pre if t["topo"] == ROCK))

    # ---- the pose (solve dy from x/z-matched verts) ----------------------------------
    tx, tz = -576.0, 416.0
    dmap = defaultdict(list)
    for t in stock:
        for p in t["w"]:
            dmap[(round(p[0] + tx, 3), round(p[2] + tz, 3))].append(p[1])
    dcand = []
    dys = Counter()
    for t in live:
        for p in t["w"]:
            ys = dmap.get(k2(p))
            if ys:
                d = p[1] - min(ys, key=lambda y: abs(p[1] - y))
                if abs(d) < 1.0:
                    dcand.append(d)
                    dys[round(d, 2)] += 1
    dy = float(np.median(dcand)) if dcand else 0.0
    print(f"pose: tx {tx:+.0f} tz {tz:+.0f}; solved seat dy {dy:+.5f} "
          f"(n={len(dcand)}, top-3 {dys.most_common(3)})")
    rep["pose"] = dict(tx=tx, tz=tz, dy_solved=round(dy, 5),
                       dy_histogram=dys.most_common(5))

    # ---- classify live tris by UV-PLANE PROVENANCE ------------------------------------
    # Every ground/wall tri in this engine carries uv that is affine in (x, z) within its
    # own tile window. A carried tri -- even one the builder REFINED into sub-tris or
    # centroid-fanned -- keeps its parent's uv PLANE exactly (both the builder's
    # refine_wall and affine_attr interpolate along that plane). So: fit uv = A + B*x +
    # C*z per live tri, and compare the GRADIENT (B, C) against every candidate donor /
    # pristine-bench tri covering it in plan. Gradient match = provenance; a leftover
    # OFFSET in A = a uv MINT (the dirt re-row shifts A by exact tile multiples).
    def uv_plane(t):
        (x1, _, z1), (x2, _, z2), (x3, _, z3) = t["w"]
        det = (x2 - x1) * (z3 - z1) - (x3 - x1) * (z2 - z1)
        if abs(det) < 1e-9:
            return None
        out = []
        for ch in range(2):
            u1, u2, u3 = (t["uv"][k][ch] for k in range(3))
            B = ((u2 - u1) * (z3 - z1) - (u3 - u1) * (z2 - z1)) / det
            C = ((x2 - x1) * (u3 - u1) - (x3 - x1) * (u2 - u1)) / det
            A = u1 - B * x1 - C * z1
            out.append((A, B, C))
        return out

    def plan_cells(t, pad=0.0):
        xs = [p[0] for p in t["w"]]
        zs = [p[2] for p in t["w"]]
        return [(cx, cz)
                for cx in range(int((min(xs) - pad) // CELL), int((max(xs) + pad) // CELL) + 1)
                for cz in range(int((min(zs) - pad) // CELL), int((max(zs) + pad) // CELL) + 1)]

    def index_by_cell(tris, posed):
        idx = defaultdict(list)
        for i, t in enumerate(tris):
            tt = t
            if posed:
                tt = dict(t, w=[(p[0] + tx, p[1] + dy, p[2] + tz) for p in t["w"]])
            for c in plan_cells(tt):
                idx[c].append((i, tt))
        return idx

    d_idx = index_by_cell(stock, True)
    p_idx = index_by_cell(pre, False)
    d_plane = {}
    p_plane = {}

    def gmatch(pl_a, pl_b):
        if pl_a is None or pl_b is None:
            return None
        for ch in range(2):
            if abs(pl_a[ch][1] - pl_b[ch][1]) > 3e-6 or abs(pl_a[ch][2] - pl_b[ch][2]) > 3e-6:
                return None
        return (pl_a[0][0] - pl_b[0][0], pl_a[1][0] - pl_b[1][0])     # dA_u, dA_v

    donor_vert_n = defaultdict(list)                    # plan key -> [(y, normal, topo)]
    for t in stock:
        for k in range(3):
            p = t["w"][k]
            donor_vert_n[k2((p[0] + tx, 0, p[2] + tz))].append(
                (p[1] + dy, t["n"][k], t["topo"]))

    def contains(tt, px, pz):
        (x1, _, z1), (x2, _, z2), (x3, _, z3) = tt["w"]
        det = (x2 - x1) * (z3 - z1) - (x3 - x1) * (z2 - z1)
        if abs(det) < 1e-9:
            return False
        w2 = ((px - x1) * (z3 - z1) - (x3 - x1) * (pz - z1)) / det
        w3 = ((x2 - x1) * (pz - z1) - (px - x1) * (z2 - z1)) / det
        return w2 >= -1e-6 and w3 >= -1e-6 and w2 + w3 <= 1 + 1e-6

    donor_vpos = {}                                 # posed donor vert -> y list
    for t in stock:
        for p in t["w"]:
            donor_vpos.setdefault(k2((p[0] + tx, 0, p[2] + tz)), []).append(p[1] + dy)
    pre_vpos = {}
    for t in pre:
        for p in t["w"]:
            pre_vpos.setdefault(k2(p), []).append(p[1])

    # A child's own plane fit is ill-conditioned on slivers, so never fit the child:
    # evaluate the PARENT's plane at the child's verts and compare to the child's uv.
    def match_parent(t, cands, cache):
        out = None
        for (j, tt) in cands:
            if j not in cache:
                cache[j] = uv_plane(tt)
            pl = cache[j]
            if pl is None:
                continue
            d = [(t["uv"][k][ch] - (pl[ch][0] + pl[ch][1] * t["w"][k][0]
                                    + pl[ch][2] * t["w"][k][2]))
                 for k in range(3) for ch in range(2)]
            du = [d[2 * k] for k in range(3)]
            dv = [d[2 * k + 1] for k in range(3)]
            worst = max(abs(v) for v in d)
            spread = max(max(du) - min(du), max(dv) - min(dv))
            cand = (worst, spread, float(np.mean(du)), float(np.mean(dv)), j)
            if out is None or cand[0] < out[0]:
                out = cand
        return out

    klass = {}
    rerow = []
    prov = {}                                       # i -> (src, worst, spread, du, dv)
    n_vert_carried = n_vert_minted = 0
    for i, t in enumerate(live):
        cx = float(np.mean([p[0] for p in t["w"]]))
        cz = float(np.mean([p[2] for p in t["w"]]))
        cell = (int(cx // CELL), int(cz // CELL))
        if tri_area_plan(t) < 0.02:                 # plan-degenerate (a vertical facet)
            ok = all(any(abs(y - p[1]) < 0.02
                         for y in donor_vpos.get(k2(p), ()))
                     for p in t["w"])
            klass[i] = ("carried_vertical_facet" if ok else "MINTED_vertical_facet")
            n_vert_carried += 1 if ok else 0
            n_vert_minted += 0 if ok else 1
            continue
        best = None                                 # (src, worst, spread, du, dv)
        for src, idx, cache in (("donor", d_idx, d_plane), ("bench", p_idx, p_plane)):
            cands = [(j, tt) for (j, tt) in idx.get(cell, ()) if contains(tt, cx, cz)]
            m = match_parent(t, cands, cache)
            if m is None:
                continue
            # prefer a verbatim fit; else the one whose offset is most tile-exact
            sc = (0 if m[0] < 1e-4 else 1, m[1], m[0])
            if best is None or sc < best[0]:
                best = (sc, src, m[0], m[1], m[2], m[3], m[4])
        if best is not None:
            _sc, src, worst, spread, dAu, dAv, pj = best
            best = (src, worst, spread, dAu, dAv)
            prov[i] = (src, pj, worst, spread, dAu, dAv)
        if best is None:
            klass[i] = ("UNMATCHED_rock" if t["topo"] == ROCK else
                        "UNMATCHED_ground" if t["topo"] in GRASS_TOPO else
                        "UNMATCHED_other")
            continue
        src, worst, spread, dAu, dAv = best
        if worst > 1e-4 and spread < 2e-4:          # a CONSTANT uv offset = a uv mint
            rerow.append((i, round(dAu / TILE_U, 2), round(dAv / TILE_V, 2)))
            klass[i] = f"{src}_UV_MINTED"
        elif worst > 1e-4:
            klass[i] = ("UV_REASSIGNED_ground" if t["topo"] in GRASS_TOPO
                        else "UV_REASSIGNED_other")
        elif src == "donor":
            klass[i] = ("carried_wall" if t["topo"] == ROCK else
                        "carried_plateau" if t["topo"] in PLATEAU_T else
                        "carried_apron" if t["topo"] in GRASS_TOPO else
                        "carried_other")
        else:
            lifted = any(p[1] > LOWLAND + 1e-4 for p in t["w"])
            klass[i] = "bench_lifted" if lifted else "bench_flat"
    print(f"vertical facets: {n_vert_carried} carried verbatim, {n_vert_minted} minted")
    n_carried = sum(1 for v in klass.values() if v.startswith("carried"))
    inv = Counter(klass.values())
    area_plan = defaultdict(float)
    area_3d = defaultdict(float)
    for i, t in enumerate(live):
        area_plan[klass[i]] += tri_area_plan(t)
        area_3d[klass[i]] += tri_area_3d(t)
    print("\nclass inventory (tris / plan u2 / 3d u2):")
    for k in sorted(inv, key=lambda q: -area_3d[q]):
        print(f"   {k:32s} {inv[k]:6d}  {area_plan[k]:9.1f}  {area_3d[k]:9.1f}")
    rep["inventory"] = {k: dict(tris=inv[k], plan_u2=round(area_plan[k], 1),
                                area3d_u2=round(area_3d[k], 1)) for k in inv}
    rep["carried_matched"] = n_carried

    # sliver hygiene, calibrated
    sl = {}
    for tris, tag in ((live, "LIVE"), (pre, "PRISTINE"), (stock, "STOCK")):
        n_s = sum(1 for t in tris if tri_area_3d(t) < 0.05)
        sl[tag] = dict(n_tris=len(tris), slivers_under_0p05_u2=n_s,
                       frac=round(n_s / max(1, len(tris)), 4))
    print("slivers (<0.05u2 3d): " + "; ".join(
        f"{k} {v['slivers_under_0p05_u2']}/{v['n_tris']}" for k, v in sl.items()))
    rep["slivers"] = sl

    # how far off-plane is the uv on the reassigned class (in TILE units)?
    ra = [max(abs(prov[i][4]), abs(prov[i][5])) / TILE_U
          for i in klass if klass[i].startswith("UV_REASSIGNED") and i in prov]
    if ra:
        big = [v for v in ra if v > 0.25]
        print(f"uv-reassigned class: n={len(ra)} offset med "
              f"{float(np.median(ra)):.4f} tiles, max {max(ra):.4f} tiles; "
              f"{len(big)} tris are off by > 1/4 tile (a visibly wrong texel window)")
        rep["uv_reassigned_offset_tiles"] = dict(
            n=len(ra), med=round(float(np.median(ra)), 5), max=round(max(ra), 5),
            n_over_quarter_tile=len(big))

    # the rock|grass weld line: how LONG is the crease the normal pass created?
    wl = 0.0
    wl_bad = 0.0
    ET0 = defaultdict(list)
    for i, t in enumerate(live):
        ps = [kk(p) for p in t["w"]]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            ET0[tuple(sorted((ps[a], ps[b])))].append(i)
    for e, ts in ET0.items():
        if len(ts) != 2:
            continue
        tp = {live[ts[0]]["topo"], live[ts[1]]["topo"]}
        if ROCK not in tp or not (tp & GRASS_TOPO):
            continue
        L = math.dist(e[0], e[1])
        wl += L
        worst = 0.0
        for P in e:
            for (ia, ib) in ((ts[0], ts[1]),):
                na = next((live[ia]["n"][k] for k in range(3)
                           if kk(live[ia]["w"][k]) == P), None)
                nb = next((live[ib]["n"][k] for k in range(3)
                           if kk(live[ib]["w"][k]) == P), None)
                if na and nb:
                    a = ang(na, nb)
                    if a:
                        worst = max(worst, a)
        if worst > 8.0:
            wl_bad += L
    print(f"rock|grass weld line in the live build: {wl:.1f}u total, of which "
          f"{wl_bad:.1f}u carries a >8deg normal crease")
    rep["weld_line"] = dict(total_u=round(wl, 1), creased_u=round(wl_bad, 1))

    # who owns the grass-on-grass steps that break the engine's climb ceiling?
    steps = []
    for e, ts in ET0.items():
        if len(ts) != 2:
            continue
        if not all(live[i]["topo"] in GRASS_TOPO for i in ts):
            continue
        rise = abs(e[0][1] - e[1][1])
        if rise > STEP_CEIL:
            steps.append((round(rise, 2), round(math.dist(e[0], e[1]), 2),
                          sorted({klass.get(ts[0], "?"), klass.get(ts[1], "?")}),
                          kk(e[0]), kk(e[1])))
    steps.sort(reverse=True)
    print(f"grass-on-grass steps over the {STEP_CEIL}u climb ceiling: {len(steps)}")
    for s in steps[:10]:
        print(f"   rise {s[0]}u over {s[1]}u  {s[2]}  {s[3]} -- {s[4]}")
    rep["grass_steps_over_ceiling"] = [dict(rise=s[0], edge_len=s[1], classes=s[2],
                                            a=list(s[3]), b=list(s[4]))
                                       for s in steps[:20]]

    # ---- THE DIRT RE-ROW, detected by ATLAS TILE (independent of the plane fit) ------
    PU, PV = json.loads((Path(__file__).resolve().parent / "out" /
                         "rock_tiles.json").read_text())["phase"]

    def tile_of(uvs):
        return (int(math.floor((min(q[0] for q in uvs) - PU) / TILE_U + 0.5)),
                int(math.floor((min(q[1] for q in uvs) - PV) / TILE_V + 0.5)))

    donor_tile_hist = Counter()
    for t in stock:
        donor_tile_hist[tile_of(t["uv"])] += 1
    pairs = Counter()
    n_dirt_donor = 0
    for t in stock:
        c, r = tile_of(t["uv"])
        if c == 5 and 8 <= r <= 11 and t["topo"] in GRASS_TOPO:
            n_dirt_donor += 1
    n_dirt_live = 0
    exact_rerow = Counter()
    for i, t in enumerate(live):
        if t["topo"] not in GRASS_TOPO or i not in prov or prov[i][0] != "donor":
            continue
        tt = dict(stock[prov[i][1]])
        dt = tile_of(tt["uv"])
        lt = tile_of(t["uv"])
        if dt == (5, 8) or (dt[0] == 5 and 8 <= dt[1] <= 11):
            n_dirt_live += 1
        if dt != lt:
            pairs[(dt, lt)] += 1
        du_t = prov[i][4] / TILE_U
        dv_t = prov[i][5] / TILE_V
        if abs(du_t + 5) < 0.1 and min(abs(dv_t - 14), abs(dv_t - 16)) < 0.1:
            exact_rerow[(round(du_t), round(dv_t))] += 1
    print(f"\ndirt band: {n_dirt_donor} donor grass-class tris wear atlas col 5 rows "
          f"8-11 across the 5-block soup; {n_dirt_live} of the CARRIED apron's tris "
          f"have such a donor parent")
    print(f"   donor->live tile changes on donor-parented ground: {pairs.most_common(8)}")
    print(f"   exact (-5 col, +14/+16 row) re-row signature: {dict(exact_rerow)}")
    rep["dirt_reRow"] = dict(donor_dirt_band_tris=n_dirt_donor,
                             carried_tris_with_dirt_parent=n_dirt_live,
                             exact_rerow_signature={str(k): v for k, v in
                                                    exact_rerow.items()},
                             tile_changes=[dict(donor=list(k[0]), live=list(k[1]), n=v)
                                           for k, v in pairs.most_common(12)])

    # ---- the re-row: what it did, and what it broke ---------------------------------
    dv_groups = Counter((r[1], r[2]) for r in rerow)
    print(f"\nuv MINT on carried tris: {len(rerow)} tris; (du,dv) in tiles -> "
          f"{dv_groups.most_common(6)}")
    rerow_set = {r[0] for r in rerow}
    rep["rerow"] = dict(n_tris=len(rerow), delta_groups=[
        dict(du_tiles=k[0], dv_tiles=k[1], n=v) for k, v in dv_groups.most_common()],
        plan_u2=round(sum(tri_area_plan(live[i]) for i in rerow_set), 1),
        area3d_u2=round(sum(tri_area_3d(live[i]) for i in rerow_set), 1),
        slope_deg_med=round(float(np.median([slope_deg(live[i]) for i in rerow_set]))
                            if rerow_set else 0.0, 1),
        slope_deg_max=round(max([slope_deg(live[i]) for i in rerow_set], default=0.0), 1))

    # boundary of the re-rowed patch: shared edges re-rowed|not-re-rowed, and internal
    # edges between different dv groups
    dvof = {r[0]: (r[1], r[2]) for r in rerow}
    ET = defaultdict(list)
    for i, t in enumerate(live):
        ps = [kk(p) for p in t["w"]]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            ET[tuple(sorted((ps[a], ps[b])))].append(i)
    b_len = 0.0
    b_n = 0
    i_len = 0.0
    i_n = 0
    for e, ts in ET.items():
        if len(ts) != 2:
            continue
        a, b = ts
        ina, inb = a in rerow_set, b in rerow_set
        gr = live[a]["topo"] in GRASS_TOPO and live[b]["topo"] in GRASS_TOPO
        if not gr:
            continue
        L = math.dist(e[0], e[1])
        if ina != inb:
            b_len += L
            b_n += 1
        elif ina and inb and dvof[a] != dvof[b]:
            i_len += L
            i_n += 1
    nb_tiles = Counter()
    for e, ts in ET.items():
        if len(ts) != 2:
            continue
        a, b = ts
        if (a in rerow_set) == (b in rerow_set):
            continue
        other = b if a in rerow_set else a
        nb_tiles[tile_of(live[other]["uv"])] += 1
    print(f"   re-row boundary: {b_n} shared ground edges ({b_len:.1f}u) between a "
          f"re-rowed tri and an untouched one; the untouched side's tiles "
          f"{nb_tiles.most_common(6)}")
    rep["rerow_boundary_neighbour_tiles"] = [dict(tile=list(k), n=v)
                                             for k, v in nb_tiles.most_common(10)]

    # ---- how much of the ground had its NORMALS rewritten? --------------------------
    n_up = n_mod = 0
    a_up = a_mod = 0.0
    for i, t in enumerate(live):
        if t["topo"] not in GRASS_TOPO:
            continue
        flat = all(abs(nn[0]) < 1e-3 and abs(nn[2]) < 1e-3 and nn[1] > 0.999
                   for nn in t["n"])
        if flat:
            n_up += 1
            a_up += tri_area_3d(t)
        else:
            n_mod += 1
            a_mod += tri_area_3d(t)
    print(f"\nground normals: {n_up} tris still hard-up (0,1,0) [{a_up:.0f}u2], "
          f"{n_mod} tris carry a non-up normal [{a_mod:.0f}u2]")
    rep["ground_normals"] = dict(hard_up_tris=n_up, hard_up_area=round(a_up, 1),
                                 non_up_tris=n_mod, non_up_area=round(a_mod, 1))

    # THE SHADING-vs-GEOMETRY CHECK, calibrated: on NEAR-FLAT ground (face slope < 10
    # deg), how far does the shipped vertex normal lean away from the face it sits on?
    for tris, tag in ((live, "LIVE round-8"), (pre, "PRISTINE bench"),
                      (stock, "STOCK donor soup")):
        lean = []
        nup2 = ntot2 = 0
        low = 0
        for t in tris:
            if t["topo"] not in GRASS_TOPO:
                continue
            fn = face_n(t)
            if fn[1] < 0:
                fn = -fn
            flat = math.degrees(math.acos(max(-1.0, min(1.0, abs(float(fn[1])))))) < 10.0
            for nn in t["n"]:
                ntot2 += 1
                if abs(nn[0]) < 1e-4 and abs(nn[2]) < 1e-4 and nn[1] > 0.9999:
                    nup2 += 1
                if nn[1] < 0.8:
                    low += 1
                if flat:
                    a = ang(nn, fn)
                    if a is not None:
                        lean.append(a)
        arr = np.array(lean) if lean else np.zeros(1)
        print(f"   [{tag}] grass verts {ntot2}, hard-up {nup2} ({nup2 / max(1, ntot2):.1%}), "
              f"ny<0.8 {low}; on NEAR-FLAT faces the normal leans off the face by med "
              f"{float(np.median(arr)):.1f} p90 {float(np.percentile(arr, 90)):.1f} max "
              f"{float(arr.max()):.1f} deg")
        rep.setdefault("shading_vs_geometry", []).append(dict(
            tag=tag, grass_verts=ntot2, hard_up=nup2, ny_below_0p8=low,
            flatface_lean_med=round(float(np.median(arr)), 1),
            flatface_lean_p90=round(float(np.percentile(arr, 90)), 1),
            flatface_lean_max=round(float(arr.max()), 1)))
    print(f"   re-row INTERNAL parity break: {i_n} shared edges ({i_len:.1f}u) between "
          f"two re-rowed tris with DIFFERENT dv")
    rep["rerow"]["boundary_edges"] = b_n
    rep["rerow"]["boundary_len_u"] = round(b_len, 1)
    rep["rerow"]["internal_parity_break_edges"] = i_n
    rep["rerow"]["internal_parity_break_len_u"] = round(i_len, 1)

    # ---- uv / normal / step reports, three-way calibrated ---------------------------
    for tris, tag in ((live, "LIVE round-8"), (pre, "PRISTINE bench"),
                      (stock, "STOCK donor soup")):
        r = edge_report(tris, tag)
        rep.setdefault("edges", []).append(r)
        print(f"\n[{tag}] ground shared edges {r['n_shared_ground_edges']}")
        print(f"   uv split bins {r['uv_bins']}  (len u {r['uv_len_u']})")
        print(f"   normal split deg {r['normal_split_deg']}  seam len "
              f"{r['normal_seam_len_u']}u")
        print(f"   edges above the {STEP_CEIL}u step ceiling: "
              f"{r['edges_over_step_ceiling']} {r['step_examples'][:3]}")
        if r["uv_break_examples"]:
            print(f"   worst uv breaks {r['uv_break_examples'][:4]}")

    # ---- the lift: geometry the builder minted --------------------------------------
    lift_verts = {}
    for t in live:
        if t["topo"] not in GRASS_TOPO:
            continue
        for p in t["w"]:
            if p[1] > LOWLAND + 1e-4:
                lift_verts[kk(p)] = p
    prev = {kk(p) for t in pre for p in t["w"]}
    n_moved = sum(1 for k in lift_verts if (k[0], round(LOWLAND, 3), k[2]) in prev)
    rads = [math.hypot(p[0] - CENTER[0], p[2] - CENTER[1]) for p in lift_verts.values()]
    ys = [p[1] for p in lift_verts.values()]
    print(f"\nlift: {len(lift_verts)} grass verts above LOWLAND (y max {max(ys):.2f}); "
          f"{n_moved} of them were pristine-bench verts at 3.2 (moved in place); "
          f"radius {min(rads):.1f}..{max(rads):.1f}u from CENTER")
    # the coast-ban crease: an edge from a lifted vert to a vert still at 3.2
    crease = []
    for e, ts in ET.items():
        if not ts:
            continue
        if not all(live[i]["topo"] in GRASS_TOPO | {53, 54, 55, 56} for i in ts):
            continue
        y0, y1 = e[0][1], e[1][1]
        if abs(min(y0, y1) - LOWLAND) < 1e-3 and max(y0, y1) > LOWLAND + 0.2:
            crease.append((round(max(y0, y1) - LOWLAND, 2), math.dist(e[0], e[1]),
                           kk(e[0]), kk(e[1])))
    crease.sort(reverse=True)
    gslope = [(round(slope_deg(t), 1), klass.get(i, "?"),
               tuple(round(v, 1) for v in t["w"][0]),
               round(math.hypot(t["w"][0][0] - CENTER[0], t["w"][0][2] - CENTER[1]), 1))
              for i, t in enumerate(live) if t["topo"] in GRASS_TOPO]
    gslope.sort(reverse=True)
    slope_by_class = defaultdict(list)
    for s, cl, _p, _r in gslope:
        slope_by_class[cl].append(s)
    print("   grass slope by provenance class (deg): "
          + "; ".join(f"{cl} n={len(v)} med {float(np.median(v)):.1f} p99 "
                      f"{float(np.percentile(v, 99)):.1f} max {max(v):.1f}"
                      for cl, v in sorted(slope_by_class.items())))
    print(f"   steepest grass tris: {gslope[:6]}")
    rep["grass_slope_by_class"] = {
        cl: dict(n=len(v), med=round(float(np.median(v)), 1),
                 p99=round(float(np.percentile(v, 99)), 1), max=round(max(v), 1))
        for cl, v in slope_by_class.items()}
    rep["grass_slope_worst"] = gslope[:12]
    pslope = [slope_deg(t) for t in pre if t["topo"] in GRASS_TOPO]
    print(f"   lift/coast crease edges (lifted vert -> a vert still at 3.2): "
          f"{len(crease)}; worst rise {crease[0][0] if crease else 0}u over "
          f"{crease[0][1]:.1f}u" if crease else "   no crease edges")
    rep["lift"] = dict(n_verts_above_lowland=len(lift_verts),
                       n_pristine_verts_moved=n_moved,
                       y_max=round(max(ys), 2),
                       radius_min=round(min(rads), 1), radius_max=round(max(rads), 1),
                       crease_edges=len(crease), crease_worst=crease[:6],
                       pristine_grass_slope_max=round(max(pslope), 1))

    # ---- normals: did harmonization move the DONOR's own shading? --------------------
    dev = []
    for i, t in enumerate(live):
        if klass.get(i) not in ("carried_apron", "apron_UV_MINTED"):
            continue
        for k in range(3):
            cands = [n0 for (y0, n0, tp) in donor_vert_n.get(k2(t["w"][k]), ())
                     if abs(y0 - t["w"][k][1]) < 0.25 and tp in GRASS_TOPO]
            if not cands:
                continue
            best = min((a for a in (ang(t["n"][k], n0) for n0 in cands)
                        if a is not None), default=None)
            if best is not None:
                dev.append(best)
    dv = np.array(dev) if dev else np.zeros(1)
    print(f"\napron normals vs the DONOR's own: n={len(dev)} med "
          f"{float(np.median(dv)):.2f} p90 {float(np.percentile(dv, 90)):.2f} max "
          f"{float(dv.max()):.2f} deg; frac >5deg {float((dv > 5).mean()):.3f}")
    rep["apron_normal_deviation_deg"] = dict(
        n=len(dev), med=round(float(np.median(dv)), 2),
        p90=round(float(np.percentile(dv, 90)), 2), max=round(float(dv.max()), 2),
        frac_over_5deg=round(float((dv > 5).mean()), 4))

    # the foot weld: wall-side normal vs ground-side normal at the same position
    def foot_split(tris, tag, posed):
        wall_n = defaultdict(list)
        grnd_n = defaultdict(list)
        for t in tris:
            tgt = wall_n if t["topo"] == ROCK else (grnd_n if t["topo"] in GRASS_TOPO
                                                   else None)
            if tgt is None:
                continue
            for k in range(3):
                p = t["w"][k]
                key = k2((p[0] + tx, 0, p[2] + tz)) if posed else k2(p)
                yv = p[1] + dy if posed else p[1]
                tgt[key].append((yv, t["n"][k]))
        angs = []
        for p, ws in wall_n.items():
            gs = grnd_n.get(p)
            if not gs:
                continue
            best = 180.0
            for (ya, a) in ws:
                for (yb, b) in gs:
                    if abs(ya - yb) > 0.05:
                        continue
                    v = ang(a, b)
                    if v is not None:
                        best = min(best, v)
            if best < 180.0:
                angs.append(best)
        arr = np.array(angs) if angs else np.zeros(1)
        print(f"   [{tag}] rock|grass shared-position normal split: n={len(angs)} med "
              f"{float(np.median(arr)):.1f} p90 {float(np.percentile(arr, 90)):.1f} "
              f"max {float(arr.max()):.1f} deg")
        return dict(tag=tag, n=len(angs), med=round(float(np.median(arr)), 1),
                    p90=round(float(np.percentile(arr, 90)), 1),
                    max=round(float(arr.max()), 1))
    print("the donor's own foot weld, stock vs live:")
    rep["foot_weld_normal_split"] = [foot_split(stock, "STOCK donor", True),
                                     foot_split(live, "LIVE round-8", False)]

    # ---- block-border straddling + idall integrity ----------------------------------
    print()
    for tris, tag in ((live, "LIVE round-8"), (pre, "PRISTINE bench"),
                      (stock, "STOCK donor soup")):
        s = straddle_report(tris, tag)
        rep.setdefault("straddle", []).append(s)
        print(f"[{tag}] tris crossing a 64u block border: x {s['straddling_x']} / z "
              f"{s['straddling_z']} ({s['straddle_area_u2']}u2 plan)")
    print()
    for tris, tag in ((live, "LIVE round-8"), (pre, "PRISTINE bench"),
                      (stock, "STOCK donor soup")):
        f = frac_idall_report(tris, tag)
        rep.setdefault("idall", []).append(f)
        print(f"[{tag}] tris with FRACTIONAL idall {f['tris_with_fractional_idall']}, "
              f"MIXED idall across verts {f['tris_with_mixed_idall']} "
              f"{f['examples'][:2]}")

    # ---- plan render, class-coloured ------------------------------------------------
    COL = dict(carried_wall=(120, 108, 96), carried_plateau=(96, 132, 88),
               carried_apron=(70, 150, 70), donor_UV_MINTED=(235, 60, 60),
               bench_lifted=(240, 190, 60), bench_flat=(60, 90, 140),
               bench_UV_MINTED=(255, 140, 0),
               carried_vertical_facet=(150, 130, 110),
               MINTED_vertical_facet=(255, 255, 90),
               UNMATCHED_rock=(200, 40, 160), UNMATCHED_ground=(170, 60, 200),
               UNMATCHED_other=(120, 40, 140), carried_other=(200, 200, 200))
    HW, SC = 60.0, 9
    RW = int(2 * HW * SC)
    img = Image.new("RGB", (RW, RW), (18, 20, 24))
    dr = ImageDraw.Draw(img)
    order = sorted(range(len(live)), key=lambda i: float(np.mean([p[1] for p in live[i]["w"]])))
    for i in order:
        t = live[i]
        pts = [((p[0] - CENTER[0] + HW) * SC, (p[2] - CENTER[1] + HW) * SC)
               for p in t["w"]]
        dr.polygon(pts, fill=COL.get(klass.get(i, "bench_flat"), (255, 255, 255)))
    for r in (rads and [max(rads)] or []):
        pass
    img.save(OUTD / "mint_inventory_audit.png")
    print(f"\nplan render -> {OUTD / 'mint_inventory_audit.png'}")

    (OUTD / "mint_inventory_audit.json").write_text(json.dumps(rep, indent=1),
                                                    encoding="utf-8")
    print(f"artifact -> {OUTD / 'mint_inventory_audit.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
