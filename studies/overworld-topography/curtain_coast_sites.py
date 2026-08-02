"""C3 WALL-MEETS-COAST -- what stock ships where an INTERIOR rock mass (topo 49/50) meets the sea.

The CURTAIN GRAMMAR study's discriminant instrument (questions registered in
studies/path-d-new-world/CURTAIN-GRAMMAR.md BEFORE this ran): the carried mesa's skirt
hovers 1.5-3.2u over the descending bench shore at two coast crossings. Stock's two known
laws pull opposite ways -- THE TAPER LAW (interior wall endpoints taper to ground; measured
inland only) vs THE FREE-BASE LAW (topo-58 coastal cliff bases terminate free at/below the
waterline; measured on the coastal cliff class only). Nobody has measured which idiom rules
where the INTERIOR rock body class runs to the coast. This census does.

Method, read-only vs stock disc-1 (ff9mapkit.world.extract):
  1. SITES -- every rock vert (a vert of a topo-49/50 terrain tri) within 8u WORLD-plan of
     any water-part vert (sea1..sea5, beach1, beach2; a missing part is skipped), clustered
     into 16u world-plan cells (one cell = one site). Rock and water are matched in the
     world frame, so cross-block-seam adjacency is caught.
  2. PER SITE -- rock min y vs the local water surface y (median of water verts near the
     members); corridor sampling rock->nearest-water for up-facing FOOT-LEGAL cover; the
     edge grammar of every near-horizontal surface boundary edge at the junction
     (sealed-down / sealed-up / ramped / t-join / free-base / HOVER / map-edge); the
     near-vertical face population at the junction by topograph class.
  3. CLASSIFY -- HIDDEN-WATER (the water sheet runs under land there; excluded from the
     primary table) / FREE-DESCENT (EXPOSED rock reaches at/below the water surface) /
     GROUND-WRAPS (foot-legal cover on >=95% of corridor samples) / CURTAIN-SEALED (a
     descending vertical seal closes the surface edge, without wrap or descent) / OTHER.
  4. ANSWER -- the dominant resolution, drop-height stats per class, the ground classes
     present, and whether ANY stock site leaves a surface edge hovering unsealed over
     lower ground (the defect class the bench shipped).

Conventions: |geometric ny| <= 0.2 = NEAR-VERTICAL; |ny| >= 0.5 = near-horizontal (the
walkable-cover test); plan area < 0.05 u^2 = PLAN-DEGENERATE. A surface boundary edge is a
3D edge with exactly ONE near-horizontal owner among all context tris (neighbor blocks are
merged into context, so block-seam edges pair up and do not read as boundaries).

Artifacts -> out/curtain_coast_sites.json + out/curtain_coast_sites.png.
Regenerate: py -X utf8 curtain_coast_sites.py     (from studies/overworld-topography/)
"""
import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402

ROCK = {49, 50}
WALKABLE = (set(range(0, 8)) | set(range(10, 14)) | set(range(16, 24)) | {27, 28, 30, 31}
            | set(range(32, 39)) | {41, 42, 45, 46, 52})
SEA_TOPO = set(range(53, 58))
CLIFF = 58
WATER_PARTS = ("sea1", "sea2", "sea3", "sea4", "sea5", "beach1", "beach2")
NEAR_W = 8.0            # rock vert -> water vert plan adjacency (the site trigger)
CELL = 16.0             # site cell size
CTX = 10.0              # junction radius around member verts (measures happen here)
CTX_TRI = 26.0          # tri-gather radius around the site center (owners stay complete)
BLOCK_R = 30.0          # block-footprint gather radius
V_NY, H_NY = 0.2, 0.5
OUT_DIR = Path(__file__).with_name("out")
OUT_JSON = OUT_DIR / "curtain_coast_sites.json"
OUT_PNG = OUT_DIR / "curtain_coast_sites.png"


def bucket(t):
    if t == 49:
        return "rock49"
    if t == 50:
        return "rock50"
    if t == CLIFF:
        return "cliff58"
    if t in SEA_TOPO:
        return "sea"
    if t in WALKABLE:
        return "walk"
    return f"topo{t}"


def summarize(vals):
    if not vals:
        return dict(n=0)
    a = np.array(vals, float)
    return dict(n=len(a), med=round(float(np.median(a)), 2),
                p25=round(float(np.percentile(a, 25)), 2),
                p75=round(float(np.percentile(a, 75)), 2),
                mx=round(float(a.max()), 2), mn=round(float(a.min()), 2))


# ---- pass 0: decode every disc-1 block (terrain + water parts) ------------------------------
t0 = time.time()
BLOCKS = X.list_blocks(disc=1)
BSET = set(BLOCKS)
TERR, WATER = {}, {}
rock_blocks = set()
for (bx, by) in BLOCKS:
    try:
        bm = X.read_block(bx, by, disc=1, part="terrain")
    except Exception:                                       # noqa: BLE001
        continue
    ox, oz = X.block_world_origin(bx, by)
    W = np.asarray(bm.verts, float) + np.array([ox, 0.0, oz])
    TRI = np.asarray(bm.flat_index, np.int64).reshape(-1, 3)
    TAN = np.asarray(bm.tangents, float)
    idall = np.rint(TAN[TRI[:, 0], 0]).astype(np.int64)
    topo = (idall & 0xFC) >> 2
    TV = W[TRI]                                             # (nt, 3, 3) world tri verts
    e1, e2 = TV[:, 1] - TV[:, 0], TV[:, 2] - TV[:, 0]
    nrm = np.cross(e1, e2)
    nl = np.linalg.norm(nrm, axis=1)
    deg = nl <= 1e-9
    nya = np.zeros(len(nl))
    nya[~deg] = np.abs(nrm[~deg, 1] / nl[~deg])
    parea = 0.5 * np.abs(e1[:, 0] * e2[:, 2] - e1[:, 2] * e2[:, 0])
    TERR[(bx, by)] = dict(TV=TV, TOPO=topo, NYA=nya, DEG=deg, PAREA=parea,
                          CEN=TV.mean(axis=1)[:, [0, 2]])
    if np.isin(topo, list(ROCK)).any():
        rock_blocks.add((bx, by))
    wl = []
    for pi, part in enumerate(WATER_PARTS):
        try:
            wm = X.read_block(bx, by, disc=1, part=part)
        except Exception:                                   # noqa: BLE001  (ValueError = missing part)
            continue
        WV = np.asarray(wm.verts, float) + np.array([ox, 0.0, oz])
        WT = WV[np.asarray(wm.flat_index, np.int64).reshape(-1, 3)] if wm.flat_index else \
            np.zeros((0, 3, 3))
        wl.append((pi, WV, WT))
    if wl:
        WATER[(bx, by)] = wl
print(f"[{time.time() - t0:5.1f}s] decoded {len(TERR)} terrain blocks; "
      f"{len(rock_blocks)} carry rock 49/50; {len(WATER)} carry a water part; "
      f"BOTH in-block: {len(rock_blocks & set(WATER))}", flush=True)

wp_l, wi_l = [], []
for wl in WATER.values():
    for pi, WV, _WT in wl:
        wp_l.append(WV)
        wi_l.append(np.full(len(WV), pi, np.int8))
WPTS = np.concatenate(wp_l)
WPART = np.concatenate(wi_l)
WHASH = defaultdict(list)
for i, p in enumerate(WPTS):
    WHASH[(int(math.floor(p[0] / NEAR_W)), int(math.floor(p[2] / NEAR_W)))].append(i)
WHASH = {k: np.asarray(v, np.int64) for k, v in WHASH.items()}


def water_near(cx, cz, rad):
    i0, i1 = int(math.floor((cx - rad) / NEAR_W)), int(math.floor((cx + rad) / NEAR_W))
    j0, j1 = int(math.floor((cz - rad) / NEAR_W)), int(math.floor((cz + rad) / NEAR_W))
    idx = [WHASH[(i, j)] for i in range(i0, i1 + 1) for j in range(j0, j1 + 1)
           if (i, j) in WHASH]
    if not idx:
        return np.empty(0, np.int64)
    idx = np.concatenate(idx)
    d2 = (WPTS[idx, 0] - cx) ** 2 + (WPTS[idx, 2] - cz) ** 2
    return idx[d2 <= rad * rad]


# ---- pass 1: rock-near-water membership -> 16u cell sites -----------------------------------
SITES = defaultdict(list)                                   # cell -> [(vert3, w_idx, dist)]
n_members_total = 0
for (bx, by) in sorted(rock_blocks):
    T = TERR[(bx, by)]
    rmask = np.isin(T["TOPO"], list(ROCK))
    RV = T["TV"][rmask].reshape(-1, 3)
    kq = np.round(RV[:, [0, 2]] * 2).astype(np.int64)       # 0.5u plan dedupe
    _, ui = np.unique(kq, axis=0, return_index=True)
    RV = RV[np.sort(ui)]
    widx = water_near(bx * 64 + 32.0, -by * 64 - 32.0, 45.3 + NEAR_W)
    if not len(widx):
        continue
    WXZ = WPTS[widx][:, [0, 2]]
    for c0 in range(0, len(RV), 800):
        rc = RV[c0:c0 + 800]
        dx = rc[:, 0][:, None] - WXZ[:, 0][None, :]
        dz = rc[:, 2][:, None] - WXZ[:, 1][None, :]
        d2 = dx * dx + dz * dz
        jn = d2.argmin(1)
        dmin = np.sqrt(d2[np.arange(len(rc)), jn])
        for k in np.nonzero(dmin <= NEAR_W)[0]:
            v = rc[k]
            cellk = (int(math.floor(v[0] / CELL)), int(math.floor(v[2] / CELL)))
            SITES[cellk].append((v, int(widx[jn[k]]), float(dmin[k])))
            n_members_total += 1
print(f"[{time.time() - t0:5.1f}s] {n_members_total} rock-near-water verts -> "
      f"{len(SITES)} sites ({CELL:.0f}u cells)", flush=True)


# ---- per-site instrument --------------------------------------------------------------------
def process_site(cellk, members, want_render=False):
    mv = np.array([m[0] for m in members])
    mw = [m[1] for m in members]
    if len(mv) > 60:
        sel60 = np.linspace(0, len(mv) - 1, 60).astype(int)
        mv, mw = mv[sel60], [mw[i] for i in sel60]
    cx, cz = float(mv[:, 0].mean()), float(mv[:, 2].mean())
    M2 = mv[:, [0, 2]]

    tv_l, to_l, ny_l, dg_l, pa_l = [], [], [], [], []
    blocks_used = []
    for (bx, by), T in TERR.items():
        if X.footprint_nearest_dist(bx, by, cx, cz) > BLOCK_R:
            continue
        m = np.linalg.norm(T["CEN"] - [cx, cz], axis=1) <= CTX_TRI
        if not m.any():
            continue
        blocks_used.append((bx, by))
        tv_l.append(T["TV"][m])
        to_l.append(T["TOPO"][m])
        ny_l.append(T["NYA"][m])
        dg_l.append(T["DEG"][m])
        pa_l.append(T["PAREA"][m])
    TVs = np.concatenate(tv_l)
    TOPOs = np.concatenate(to_l)
    NYAs = np.concatenate(ny_l)
    DEGs = np.concatenate(dg_l)
    PAs = np.concatenate(pa_l)
    kt = len(TVs)

    A2, B2, C2 = TVs[:, 0][:, [0, 2]], TVs[:, 1][:, [0, 2]], TVs[:, 2][:, [0, 2]]
    Ay, By, Cy = TVs[:, 0, 1], TVs[:, 1, 1], TVs[:, 2, 1]
    v0, v1 = C2 - A2, B2 - A2
    d00 = (v0 * v0).sum(1)
    d01 = (v0 * v1).sum(1)
    d11 = (v1 * v1).sum(1)
    denom = d00 * d11 - d01 * d01
    okd = np.abs(denom) > 1e-9

    def cover_lists(P):
        """Per plan point: (tri indices covering it, interpolated surface y per cover)."""
        out = []
        for s0 in range(0, len(P), 200):
            Pc = np.asarray(P[s0:s0 + 200], float)
            v2x = Pc[:, 0][:, None] - A2[:, 0][None, :]
            v2z = Pc[:, 1][:, None] - A2[:, 1][None, :]
            d20 = v2x * v0[:, 0][None, :] + v2z * v0[:, 1][None, :]
            d21 = v2x * v1[:, 0][None, :] + v2z * v1[:, 1][None, :]
            with np.errstate(divide="ignore", invalid="ignore"):
                u = (d11 * d20 - d01 * d21) / denom
                v = (d00 * d21 - d01 * d20) / denom
            w = 1.0 - u - v
            inside = okd[None, :] & (u >= -1e-3) & (v >= -1e-3) & (w >= -1e-3)
            yv = Ay[None, :] + u * (Cy - Ay)[None, :] + v * (By - Ay)[None, :]
            for r in range(len(Pc)):
                idx = np.nonzero(inside[r])[0]
                out.append((idx, yv[r][idx]))
        return out

    def dmin_members(P):
        dx = P[:, 0][:, None] - M2[:, 0][None, :]
        dz = P[:, 1][:, None] - M2[:, 1][None, :]
        return np.sqrt((dx * dx + dz * dz).min(1))

    # local water
    widx = water_near(cx, cz, CTX_TRI)
    if not len(widx):                                       # degenerate member spread
        widx = water_near(cx, cz, 42.0)
    WC = WPTS[widx]
    wnear = dmin_members(WC[:, [0, 2]]) <= CTX if len(WC) else np.zeros(0, bool)
    water_y = float(np.median(WC[wnear, 1])) if wnear.any() else float(np.median(WPTS[mw, 1]))
    parts_hit = Counter(WATER_PARTS[WPART[i]] for i in mw)

    # water-SHEET plan coverage (sheet tris are coarse; vert proximity alone under-detects)
    wt_l = []
    for (bxw, byw), wl in WATER.items():
        if X.footprint_nearest_dist(bxw, byw, cx, cz) > BLOCK_R:
            continue
        for _pi, _WV, WT in wl:
            if len(WT):
                wt_l.append(WT)
    WTV = np.concatenate(wt_l) if wt_l else np.zeros((0, 3, 3))
    if len(WTV):
        sel_w = ((WTV[:, :, 0].max(1) >= cx - CTX_TRI) & (WTV[:, :, 0].min(1) <= cx + CTX_TRI)
                 & (WTV[:, :, 2].max(1) >= cz - CTX_TRI) & (WTV[:, :, 2].min(1) <= cz + CTX_TRI))
        WTV = WTV[sel_w]
    if len(WTV):
        wa, wb, wc = WTV[:, 0][:, [0, 2]], WTV[:, 1][:, [0, 2]], WTV[:, 2][:, [0, 2]]
        wv0, wv1 = wc - wa, wb - wa
        wd00 = (wv0 * wv0).sum(1)
        wd01 = (wv0 * wv1).sum(1)
        wd11 = (wv1 * wv1).sum(1)
        wden = wd00 * wd11 - wd01 * wd01
        wok = np.abs(wden) > 1e-9

    def wcover(px, pz):
        if not len(WTV):
            return False
        v2x, v2z = px - wa[:, 0], pz - wa[:, 1]
        d20 = v2x * wv0[:, 0] + v2z * wv0[:, 1]
        d21 = v2x * wv1[:, 0] + v2z * wv1[:, 1]
        with np.errstate(divide="ignore", invalid="ignore"):
            u = (wd11 * d20 - wd01 * d21) / wden
            v = (wd00 * d21 - wd01 * d20) / wden
        return bool((wok & (u >= -1e-3) & (v >= -1e-3) & (1.0 - u - v >= -1e-3)).any())

    # water exposure (a sheet under land is not a coast)
    uniq_w = sorted(set(mw))
    wexp = cover_lists(WPTS[uniq_w][:, [0, 2]])
    hidden = 0
    for (i, (idx, yv)) in zip(uniq_w, wexp):
        if len(idx) and (yv > WPTS[i, 1] + 1.0).any():
            hidden += 1
    exposed_frac = 1.0 - hidden / max(1, len(uniq_w))

    # rock body stats at the junction
    rsel = np.isin(TOPOs, list(ROCK))
    RVc = TVs[rsel].reshape(-1, 3)
    if len(RVc):
        RVc = RVc[dmin_members(RVc[:, [0, 2]]) <= CTX]
    rock_min_y = float(RVc[:, 1].min()) if len(RVc) else None
    reaches = rock_min_y is not None and rock_min_y <= water_y + 0.5
    reaches_exposed = False
    if reaches:
        low = RVc[RVc[:, 1] <= water_y + 0.5]
        if len(low) > 80:
            low = low[np.linspace(0, len(low) - 1, 80).astype(int)]
        lcov = cover_lists(low[:, [0, 2]])
        nonrock = ~rsel
        for lv, (idx, yv) in zip(low, lcov):
            buried = len(idx) and (nonrock[idx] & (yv > lv[1] + 1.0)).any()
            if not buried:
                reaches_exposed = True
                break

    # corridor rock foot -> water
    n_contact = 0
    pts, ray_of = [], []
    WXZc = WC[:, [0, 2]] if len(WC) else np.zeros((0, 2))
    for m3 in mv:
        d = np.sqrt((WXZc[:, 0] - m3[0]) ** 2 + (WXZc[:, 1] - m3[2]) ** 2)
        j = int(d.argmin())
        L = float(d[j])
        if L < 1.0:
            n_contact += 1
            continue
        w3 = WC[j]
        for t in np.linspace(0.12, 0.88, 7):
            pts.append((m3[0] + t * (w3[0] - m3[0]), m3[2] + t * (w3[2] - m3[2])))
            ray_of.append(len(ray_of))
    cov = cover_lists(pts) if pts else []
    n_pts = len(pts)
    walk_any = 0
    top_hist = Counter()
    for idx, yv in cov:
        if len(idx) == 0:
            top_hist["none"] += 1
            continue
        if (np.isin(TOPOs[idx], list(WALKABLE)) & (NYAs[idx] >= H_NY)).any():
            walk_any += 1
        nz = NYAs[idx] > V_NY
        top_hist[bucket(int(TOPOs[idx[nz][int(yv[nz].argmax())]])) if nz.any()
                 else "vertical-only"] += 1
    cover_walk = walk_any / n_pts if n_pts else None

    # vertical faces at the junction
    vmask = (NYAs <= V_NY) & ~DEGs
    if vmask.any():
        vmask &= dmin_members(TVs.mean(axis=1)[:, [0, 2]]) <= CTX
    vert_hist = Counter(bucket(int(t)) for t in TOPOs[vmask])
    vert_deg = int((PAs[vmask] < 0.05).sum())

    # ---- edge grammar --------------------------------------------------------------------
    vk = np.round(TVs, 2)
    edges = defaultdict(list)
    for ti in range(kt):
        k3 = [tuple(vk[ti, 0]), tuple(vk[ti, 1]), tuple(vk[ti, 2])]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edges[tuple(sorted((k3[a], k3[b])))].append(ti)

    vert_tris = np.nonzero(vmask)[0]

    def near_vertical_seal(mx_, mz_, ey_):
        """Unstitched curtain: a near-vertical tri whose plan footprint passes within
        0.8u of the edge mid and whose y-range descends past the edge."""
        for ti in vert_tris:
            ys = TVs[ti][:, 1]
            if not (ys.max() >= ey_ - 0.6 and ys.min() <= ey_ - 0.6):
                continue
            pp = TVs[ti][:, [0, 2]]
            for a, b in ((0, 1), (1, 2), (2, 0)):
                pa, pb = pp[a], pp[b]
                ab = pb - pa
                L2 = float(ab @ ab)
                tt = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((mx_ - pa[0]) * ab[0]
                                                               + (mz_ - pa[1]) * ab[1]) / L2))
                qx, qz = pa[0] + tt * ab[0], pa[1] + tt * ab[1]
                if (qx - mx_) ** 2 + (qz - mz_) ** 2 <= 0.64:
                    return True
        return False

    ecls = Counter()
    owner_hist, seal_hist, sealed_owner_hist = Counter(), Counter(), Counter()
    drops_sealed, drops_hover, free_base_h = [], [], []
    hover_pts, pend = [], []
    sealed_pend, sealed_mids = [], []
    hover_edge_mids = []                                    # [x, y, z, owner-bucket] per hover edge
    unresolved_mids = []
    edge_marks = []                                         # (class, (p0, p1)) for render
    for (ka, kb), owners in edges.items():
        mx_, my_, mz_ = ((ka[0] + kb[0]) / 2, (ka[1] + kb[1]) / 2, (ka[2] + kb[2]) / 2)
        dx = M2[:, 0] - mx_
        dz = M2[:, 1] - mz_
        if math.sqrt(float((dx * dx + dz * dz).min())) > CTX:
            continue
        horiz = [t for t in owners if NYAs[t] >= H_NY]
        if len(horiz) != 1:
            continue
        own = horiz[0]
        ob = bucket(int(TOPOs[own]))
        vo = [t for t in owners if NYAs[t] <= V_NY and not DEGs[t]]
        mo = [t for t in owners if t != own and t not in vo]
        ecls["analyzed"] += 1
        owner_hist[ob] += 1
        ey = (ka[1] + kb[1]) / 2
        if vo:
            vymin = min(TVs[t][:, 1].min() for t in vo)
            vymax = max(TVs[t][:, 1].max() for t in vo)
            if vymin <= ey - 0.5:
                ecls["sealed_down"] += 1
                for t in vo:
                    seal_hist[bucket(int(TOPOs[t]))] += 1
                sealed_owner_hist[ob] += 1
                drops_sealed.append(float(ey - vymin))
                sealed_pend.append((own, float(ey), float(vymin)))
                sealed_mids.append((mx_, mz_))
                edge_marks.append(("sealed", (ka, kb)))
            elif vymax >= ey + 0.5:
                ecls["sealed_up"] += 1
            else:
                ecls["ramped"] += 1
        elif mo:
            ecls["ramped"] += 1
        else:
            # true once-edge: no other owner in context
            bxq, fq = int(math.floor(mx_ / 64.0)), mx_ % 64.0
            byq, fz = int(math.floor(-mz_ / 64.0)), (-mz_) % 64.0
            at_edge = ((fq < 1.2 and (bxq - 1, byq) not in BSET)
                       or (fq > 62.8 and (bxq + 1, byq) not in BSET)
                       or (fz < 1.2 and (bxq, byq - 1) not in BSET)
                       or (fz > 62.8 and (bxq, byq + 1) not in BSET))
            if at_edge:
                ecls["map_edge"] += 1
                continue
            if near_vertical_seal(mx_, mz_, ey):
                ecls["sealed_down"] += 1
                ecls["sealed_unstitched"] += 1
                edge_marks.append(("sealed", (ka, kb)))
                continue
            oc = TVs[own].mean(axis=0)
            ox_, oz_ = mx_ - oc[0], mz_ - oc[2]
            L = math.hypot(ox_, oz_)
            if L < 1e-6:
                ex_, ez_ = kb[0] - ka[0], kb[2] - ka[2]
                Le = math.hypot(ex_, ez_) or 1.0
                ox_, oz_ = -ez_ / Le, ex_ / Le
            else:
                ox_, oz_ = ox_ / L, oz_ / L
            pend.append((own, ob, mx_, mz_, ey, ka, kb))
            hover_pts.append((mx_ + 0.75 * ox_, mz_ + 0.75 * oz_))
    pcov = cover_lists(hover_pts) if hover_pts else []
    for (own, ob, mx_, mz_, ey, ka, kb), (pq, (idx, yv)) in zip(pend, zip(hover_pts, pcov)):
        keep = idx != own
        idx, yv = idx[keep], yv[keep]
        if len(idx) and (np.abs(yv - ey) < 0.75).any():
            ecls["tjoin"] += 1
            continue
        if ey <= water_y + 0.5:
            ecls["free_base"] += 1
            free_base_h.append(ey - water_y)
            edge_marks.append(("free", (ka, kb)))
            continue
        below = yv[yv <= ey - 0.75] if len(idx) else np.zeros(0)
        if len(below):
            ecls["hover"] += 1
            drops_hover.append(float(ey - below.max()))
            hover_edge_mids.append([round(mx_, 2), round(float(ey), 2), round(mz_, 2), ob])
            edge_marks.append(("hover", (ka, kb)))
            continue
        dw = (np.sqrt((WXZc[:, 0] - pq[0]) ** 2 + (WXZc[:, 1] - pq[1]) ** 2).min()
              if len(WXZc) else 1e9)
        if (wcover(pq[0], pq[1]) or dw <= 3.0) and water_y <= ey - 0.5:
            ecls["hover_water"] += 1
            drops_hover.append(float(ey - water_y))
            hover_edge_mids.append([round(mx_, 2), round(float(ey), 2), round(mz_, 2), ob])
            edge_marks.append(("hover", (ka, kb)))
        else:
            ecls["unresolved"] += 1
            unresolved_mids.append([round(mx_, 2), round(float(ey), 2), round(mz_, 2), ob])

    # where does each seal's BOTTOM end?  (at/below water = the coastal free-base idiom;
    # on lower ground = a true curtain-over-ground; the discriminant for the fix class)
    seal_end = Counter()
    seal_rel_w = []
    for (own, ey, vymin), (idx, yv) in zip(sealed_pend,
                                           cover_lists(sealed_mids) if sealed_mids else []):
        seal_rel_w.append(vymin - water_y)
        if vymin <= water_y + 0.3:
            seal_end["water"] += 1
            continue
        keep = idx != own
        yb = yv[keep]
        below = yb[yb <= ey - 0.5] if len(yb) else np.zeros(0)
        if len(below) and abs(float(below.max()) - vymin) <= 1.0:
            seal_end["ground"] += 1
        elif len(below):
            seal_end["stops-mid"] += 1
        elif wcover(*sealed_mids[len(seal_rel_w) - 1]):
            seal_end["hang-over-water"] += 1
        else:
            seal_end["hang"] += 1

    # ---- classify ------------------------------------------------------------------------
    if exposed_frac < 0.3:
        cls, reason = "HIDDEN-WATER", f"nearest water {1 - exposed_frac:.0%} under land"
    elif reaches_exposed:
        cls, reason = "FREE-DESCENT", f"exposed rock min y {rock_min_y:.1f} <= water {water_y:.1f}+0.5"
    elif n_pts >= 8 and cover_walk is not None and cover_walk >= 0.95:
        cls, reason = "GROUND-WRAPS", f"walkable cover {cover_walk:.0%} of {n_pts} corridor pts"
    elif ecls["sealed_down"] >= 1 and ecls["hover"] + ecls["hover_water"] == 0:
        cls, reason = "CURTAIN-SEALED", f"{ecls['sealed_down']} sealed-down edges, no wrap/descent"
    else:
        why = []
        if ecls["hover"] + ecls["hover_water"]:
            why.append(f"{ecls['hover'] + ecls['hover_water']} HOVER edges")
        if cover_walk is not None:
            why.append(f"wrap {cover_walk:.0%}")
        if reaches and not reaches_exposed:
            why.append("rock reaches water only BURIED")
        if n_pts < 8:
            why.append(f"corridor thin ({n_pts} pts)")
        cls, reason = "OTHER", "; ".join(why) or "no idiom matched"

    rec = dict(
        cell=list(cellk), center=[round(cx, 1), round(cz, 1)],
        blocks=sorted(blocks_used), n_members=int(len(mv)),
        water_parts=dict(parts_hit), water_y=round(water_y, 2),
        rock_min_y=None if rock_min_y is None else round(rock_min_y, 2),
        reaches=bool(reaches), reaches_exposed=bool(reaches_exposed),
        exposed_frac=round(exposed_frac, 2),
        corridor=dict(n_rays=int(len(mv)), n_contact=n_contact, n_pts=n_pts,
                      cover_walk=None if cover_walk is None else round(cover_walk, 3),
                      top_classes=dict(top_hist)),
        vert_faces=dict(n=int(vmask.sum()), plan_degenerate=vert_deg,
                        by_class=dict(vert_hist)),
        edges=dict(ecls), owner_topo=dict(owner_hist), seal_topo=dict(seal_hist),
        sealed_owner_topo=dict(sealed_owner_hist),
        seal_end=dict(seal_end), seal_rel_water=summarize(seal_rel_w),
        drops=dict(sealed=summarize(drops_sealed), hover=summarize(drops_hover),
                   free_base=summarize(free_base_h)),
        hover_drops=[round(float(d), 2) for d in drops_hover[:20]],
        hover_edge_mids=hover_edge_mids[:20], unresolved_mids=unresolved_mids[:20],
        cls=cls, reason=reason)
    if want_render:
        rec["_render"] = dict(TVs=TVs, TOPOs=TOPOs, NYAs=NYAs, M2=M2,
                              WXZ=WXZc, marks=edge_marks, center=(cx, cz))
    return rec


# ---- pass 2: run every site -----------------------------------------------------------------
site_keys = sorted(SITES)
records = []
for si, cellk in enumerate(site_keys):
    records.append(process_site(cellk, SITES[cellk]))
    if (si + 1) % 25 == 0:
        print(f"[{time.time() - t0:5.1f}s]   {si + 1}/{len(site_keys)} sites", flush=True)
print(f"[{time.time() - t0:5.1f}s] {len(records)} sites measured", flush=True)

# ---- aggregate ------------------------------------------------------------------------------
freq_all = Counter(r["cls"] for r in records)
exposed = [r for r in records if r["cls"] != "HIDDEN-WATER"]
freq = Counter(r["cls"] for r in exposed)
drop_by_cls = defaultdict(lambda: dict(sealed=[], hover=[], free_base=[]))
vert_by_cls = defaultdict(Counter)
ground_by_cls = defaultdict(Counter)
for r in exposed:
    for k in ("sealed", "hover", "free_base"):
        s = r["drops"][k]
        if s["n"]:
            drop_by_cls[r["cls"]][k].append(s["med"])
    vert_by_cls[r["cls"]].update(r["vert_faces"]["by_class"])
    ground_by_cls[r["cls"]].update(r["corridor"]["top_classes"])
hover_sites = [r for r in exposed
               if r["edges"].get("hover", 0) + r["edges"].get("hover_water", 0) > 0]
hover_ground_sites = [r for r in exposed if r["edges"].get("hover", 0) > 0]
dominant = freq.most_common(1)[0] if freq else ("NONE", 0)
seal_topo_all, seal_end_all, sealed_owner_all = Counter(), Counter(), Counter()
seal_rel_meds = []
for r in exposed:
    seal_topo_all.update(r["seal_topo"])
    seal_end_all.update(r["seal_end"])
    sealed_owner_all.update(r["sealed_owner_topo"])
    if r["seal_rel_water"]["n"]:
        seal_rel_meds.append(r["seal_rel_water"]["med"])

print("\n== C3 WALL-MEETS-COAST: frequency table (exposed-water sites) ==")
for k, n in freq.most_common():
    print(f"   {k:14s}: {n:4d}  ({n / max(1, len(exposed)):.0%})")
print(f"   [HIDDEN-WATER excluded: {freq_all.get('HIDDEN-WATER', 0)}]")

print("\n== drop-height medians per class (per-site medians summarized) ==")
for cls in freq:
    d = drop_by_cls[cls]
    print(f"   {cls:14s}: sealed {summarize(d['sealed'])}  hover {summarize(d['hover'])}  "
          f"free-base {summarize(d['free_base'])}")

print("\n== near-vertical junction faces by class ==")
for cls in freq:
    print(f"   {cls:14s}: {dict(vert_by_cls[cls].most_common(6))}")

print("\n== corridor top-cover ground classes ==")
for cls in freq:
    print(f"   {cls:14s}: {dict(ground_by_cls[cls].most_common(6))}")

print("\n== THE SEAL, anatomized (all sealed-down edges, all classes) ==")
print(f"   seal FACE class:    {dict(seal_topo_all.most_common(8))}")
print(f"   sealed SURFACE (owner) class: {dict(sealed_owner_all.most_common(8))}")
print(f"   seal BOTTOM ends:   {dict(seal_end_all.most_common(8))}")
print(f"   seal bottom rel. water (per-site medians): {summarize(seal_rel_meds)}")

others = [r for r in exposed if r["cls"] == "OTHER"]
print(f"\n== OTHER anatomized ({len(others)} sites) ==")
o_hov = sum(1 for r in others
            if r["edges"].get("hover", 0) + r["edges"].get("hover_water", 0) > 0)
o_thin = sum(1 for r in others if r["corridor"]["n_pts"] < 8)
o_fb = sum(1 for r in others if r["drops"]["free_base"]["n"] > 0)
o_buried = sum(1 for r in others if r["reaches"] and not r["reaches_exposed"])
wv = [r["corridor"]["cover_walk"] for r in others
      if r["corridor"]["cover_walk"] is not None and r["corridor"]["n_pts"] >= 8]
print(f"   with hover edges: {o_hov}; thin corridor (<8 pts): {o_thin}; "
      f"free-base edges present: {o_fb}; rock reaches water only buried: {o_buried}")
print(f"   partial-wrap cover distribution ({len(wv)} sites): {summarize(wv)}; "
      f"bins 0-50/50-80/80-95%: "
      f"{sum(1 for v in wv if v < 0.5)}/{sum(1 for v in wv if 0.5 <= v < 0.8)}/"
      f"{sum(1 for v in wv if 0.8 <= v < 0.95)}")

print(f"\n== THE ANSWER ==")
print(f"   dominant resolution: {dominant[0]} ({dominant[1]}/{len(exposed)} sites, "
      f"{dominant[1] / max(1, len(exposed)):.0%})")
print(f"   sites with a hover-over-GROUND edge (the shipped defect class): "
      f"{len(hover_ground_sites)}/{len(exposed)}")
print(f"   sites with hover-over-WATER edges (brow past the waterline): "
      f"{len(hover_sites) - len(hover_ground_sites)}")
for r in hover_sites[:12]:
    print(f"      {r['center']} blocks {r['blocks'][:2]} cls {r['cls']} "
          f"hover g{r['edges'].get('hover', 0)}+w{r['edges'].get('hover_water', 0)} "
          f"water_y {r['water_y']} drops {r['hover_drops'][:6]}")

# ---- renders: examples per class ------------------------------------------------------------
want = []
for cls in ("FREE-DESCENT", "GROUND-WRAPS", "CURTAIN-SEALED", "OTHER"):
    ex = [r for r in exposed if r["cls"] == cls]
    ex.sort(key=lambda r: -(r["edges"].get("hover", 0) + r["edges"].get("sealed_down", 0)))
    want += [(tuple(r["cell"]), cls) for r in ex[:2]]
if want:
    PW = 320
    img = Image.new("RGB", (PW * len(want), PW + 40), (24, 26, 30))
    dr = ImageDraw.Draw(img)
    COLS = dict(rock49=(150, 150, 158), rock50=(120, 120, 128), cliff58=(220, 140, 60),
                sea=(60, 90, 170), walk=(80, 165, 95))
    for pi, (cellk, cls) in enumerate(want):
        rr = process_site(cellk, SITES[cellk], want_render=True)
        rd = rr["_render"]
        cx, cz = rd["center"]
        sc = (PW - 20) / (2 * (CTX + 8.0))

        def Mp(px, pz, pi=pi, cx=cx, cz=cz, sc=sc):
            return (pi * PW + PW / 2 + (px - cx) * sc, 20 + PW / 2 + (pz - cz) * sc)

        order = np.argsort(-rd["NYAs"])                     # verticals drawn last
        for ti in order:
            p = rd["TVs"][ti][:, [0, 2]]
            if max(abs(p[:, 0] - cx).max(), abs(p[:, 1] - cz).max()) > CTX + 8.0:
                continue
            col = COLS.get(bucket(int(rd["TOPOs"][ti])), (140, 100, 170))
            if rd["NYAs"][ti] <= V_NY:
                col = tuple(min(255, c + 60) for c in col)
            dr.polygon([Mp(*q) for q in p], outline=col)
        for w in rd["WXZ"][::3]:
            x, y = Mp(w[0], w[1])
            dr.ellipse([x - 1, y - 1, x + 1, y + 1], fill=(70, 160, 255))
        for m in rd["M2"]:
            x, y = Mp(m[0], m[1])
            dr.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(230, 70, 70))
        MC = dict(sealed=(245, 220, 90), free=(240, 240, 240), hover=(255, 60, 200))
        for mk, (ka, kb) in rd["marks"]:
            dr.line([Mp(ka[0], ka[2]), Mp(kb[0], kb[2])], fill=MC[mk], width=3)
        dr.text((pi * PW + 6, 4), f"{cls} @ {rr['center']}", fill=(220, 220, 220))
    dr.text((6, PW + 24), "red=rock-near-water verts  blue=water  yellow=sealed edge  "
            "white=free-base  magenta=HOVER  (verticals bright)", fill=(170, 170, 180))
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT_PNG)
    print(f"\nrender -> {OUT_PNG}")

# ---- artifact -------------------------------------------------------------------------------
answer = dict(
    dominant=dominant[0],
    shares={k: round(n / max(1, len(exposed)), 3) for k, n in freq.items()},
    seal_face_class=dict(seal_topo_all), sealed_surface_class=dict(sealed_owner_all),
    seal_bottom_ends=dict(seal_end_all),
    seal_bottom_rel_water=summarize(seal_rel_meds),
    hover_ground_sites=len(hover_ground_sites), hover_water_sites=len(hover_sites)
    - len(hover_ground_sites),
    hover_examples=[dict(center=r["center"], blocks=r["blocks"][:3],
                         edges=r["edges"], water_y=r["water_y"],
                         drops=r["hover_drops"][:8])
                    for r in hover_sites[:12]],
    verdict=(f"{dominant[0]} dominates wall-meets-coast "
             f"({dominant[1]}/{len(exposed)}); "
             + ("ZERO stock sites leave an edge hovering unsealed over GROUND"
                if not hover_ground_sites else
                f"{len(hover_ground_sites)} stock sites DO hover over ground -- inspect "
                f"before claiming the defect class is un-stock")))
OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.write_text(json.dumps(dict(
    params=dict(near_w=NEAR_W, cell=CELL, ctx=CTX, v_ny=V_NY, h_ny=H_NY,
                water_parts=list(WATER_PARTS)),
    population=dict(blocks=len(TERR), rock_blocks=len(rock_blocks),
                    water_blocks=len(WATER),
                    both_in_block=len(rock_blocks & set(WATER)),
                    member_verts=n_members_total, sites=len(records),
                    exposed_sites=len(exposed)),
    freq_all=dict(freq_all), freq_exposed=dict(freq),
    answer=answer, sites=records), indent=0))
print(f"artifact -> {OUT_JSON}")
print(f"[{time.time() - t0:5.1f}s] done", flush=True)
