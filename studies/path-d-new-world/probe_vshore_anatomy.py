"""C4 -- THE PATIENT'S ANATOMY: the two live V-shore hover sites, measured.

CURTAIN GRAMMAR study, question C4 (studies/path-d-new-world/CURTAIN-GRAMMAR.md,
questions registered BEFORE this ran). Over the DEPLOYED bench bytes (Disc9 world
9013, via walk_sim.load_world) this instrument measures, per hover cluster
(EAST (448.8,-507.8), WEST (382.4,-511.6), radius 12u):

  1. every Terrain once-edge -- edge ownership counted GLOBALLY across the six
     loaded blocks (an edge shared across a block border has 2 owners and is NOT a
     boundary): endpoints, heights, plan direction, owner tri topograph + mapid
     (tangent.x), and the hover gap to the highest surface below its midpoint in
     BOTH vocabularies -- SCAN sheets (what the walk query sees: 4078/4088/2040 and
     the 0x31EE veto skipped) and RENDER sheets (what the eye sees: everything
     up-facing, the 4078 underlay included);
  2. CARRIED vs BENCH per tri: a tri whose rounded vert triple exists in the
     pristine pre-wall Terrain backup (walk_sim.PRISTINE_BK) is BENCH, anything
     else is CARRIED/minted this arc;
  3. the bench shore's own anatomy through each centroid: the PRISTINE ground line
     from the lawn datum (LOWLAND=3.2) out past the waterline along the seaward
     ray -- terrain heights + topograph classes + sea/beach y at each step, the
     descent start, the waterline, the water y -- plus each cluster's distance to
     the block-border planes (x=384, x=448, z=-512) and whether the chain crosses;
  4. the exact boundary chain a seal would close: hover once-edges ordered into
     chains, per-chain plan length, the drop profile beneath every vertex and edge
     midpoint, and the surface part/class the seal's bottom would land on.

Artifacts -> out/vshore_anatomy.json + out/vshore_site_east.png / _west.png
(plan renders: carried tri edges red, bench once-edges blue, water verts cyan,
beach verts sand, hover chains yellow, cluster circle white, block borders grey).
READ-ONLY: no deploy, no bench mutation.
Regenerate: py -X utf8 probe_vshore_anatomy.py   (from this directory)
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import walk_sim as W                                        # noqa: E402

LOWLAND = 3.2                                               # the carried lawn datum
# (name, cx, cz, registered) -- east/west are the registration's clusters; south
# was DISCOVERED by this instrument's global hover sweep (same Sea4-slit class,
# on the same x=448 border plane, ~30u south of east) and measured identically.
SITES = [("east", 448.8, -507.8, True), ("west", 382.4, -511.6, True),
         ("south", 448.0, -538.0, False)]
R_SITE = 12.0                                               # cluster radius (task: ~12u)
HOVER_MIN = 0.5                                             # probe_vshore_gap's hover threshold
RND = 3                                                     # vert rounding (probe convention)
BORDERS_X = [384.0, 448.0]                                  # bx 5|6 and 6|7 planes
BORDERS_Z = [-512.0]                                        # by 7|8 plane
OUTD = HERE / "out"


def rv(p):
    return (round(p[0], RND), round(p[1], RND), round(p[2], RND))


def tri_key(tri):
    return tuple(sorted((rv(tri[0]), rv(tri[1]), rv(tri[2]))))


# ---------------------------------------------------------------- global terrain index
def terrain_index(world):
    """edge -> [(bk, ti), ...] over every Terrain tri of every loaded block, world
    coords rounded to RND. Also returns (bk, ti) -> tri. GLOBAL counting: an edge
    stitched across a block border collects owners from both blocks."""
    edges = defaultdict(list)
    tris = {}
    for bk in sorted(world):
        for m in world[bk]:
            if m["name"] != "Terrain":
                continue
            for ti, tri in enumerate(m["tris"]):
                tris[(bk, ti)] = tri
                vs = (rv(tri[0]), rv(tri[1]), rv(tri[2]))
                for a, b in ((0, 1), (1, 2), (2, 0)):
                    edges[tuple(sorted((vs[a], vs[b])))].append((bk, ti))
    return edges, tris


def sheets_at(world, x, z, render=False):
    """Up-facing (ny > 0.1) vertical-line intersections at (x,z), richest form:
    [(y, topo, mapid, part), ...] sorted top-down, deduped per (part, y@0.01).
    render=False reproduces the walk full-scan filters (IDALL_SKIP + veto out);
    render=True includes them -- the 4078 underlay draws even though walk skips it."""
    bk = W.block_key(x, z)
    if bk not in world:
        return []
    cell = (int(x // 4), int(z // 4))
    out = []
    for mesh in world[bk]:
        for ti in mesh["grid"].get(cell, ()):
            tri = mesh["tris"][ti]
            if tri[5] <= 0.1:
                continue
            if not render and (tri[3] in W.IDALL_SKIP or tri[3] == W.VETO):
                continue
            hy = W.bary_y(x, z, tri)
            if hy is None:
                continue
            out.append((hy, tri[4], tri[3], mesh["name"]))
    seen, ded = set(), []
    for s in sorted(out, key=lambda s: -s[0]):
        k = (s[3], round(s[0], 2))
        if k in seen:
            continue
        seen.add(k)
        ded.append(s)
    return ded


def below_at(world, x, z, y, render=False):
    """Highest sheet strictly below y (0.05 guard vs the edge's own plane).
    Returns (y, topo, mapid, part) or None."""
    for s in sheets_at(world, x, z, render=render):
        if s[0] < y - 0.05:
            return s
    return None


def seg_plan_dist(px, pz, a, b):
    ax, az, bx, bz = a[0], a[2], b[0], b[2]
    dx, dz = bx - ax, bz - az
    l2 = dx * dx + dz * dz
    if l2 < 1e-12:
        return math.hypot(px - ax, pz - az)
    t = max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / l2))
    return math.hypot(px - (ax + t * dx), pz - (az + t * dz))


# ---------------------------------------------------------------- chains
def build_chains(edge_keys):
    """Ordered polylines/cycles from hover edge keys (rounded vert triples)."""
    adj = defaultdict(set)
    for (a, b) in edge_keys:
        adj[a].add(b)
        adj[b].add(a)
    done, chains, cycles = set(), [], []

    def walk(a, b):
        ch = [a, b]
        done.add(frozenset((a, b)))
        while True:
            nxt = [q for q in adj[ch[-1]] if frozenset((ch[-1], q)) not in done]
            if len(adj[ch[-1]]) != 2 or not nxt:
                break
            done.add(frozenset((ch[-1], nxt[0])))
            ch.append(nxt[0])
        return ch

    for a in sorted(adj):
        if len(adj[a]) != 2:
            for b in sorted(adj[a]):
                if frozenset((a, b)) not in done:
                    chains.append(walk(a, b))
    for a in sorted(adj):                                   # leftover pure cycles
        for b in sorted(adj[a]):
            if frozenset((a, b)) not in done:
                cycles.append(walk(a, b))
    return chains, cycles


# ---------------------------------------------------------------- shore anatomy
def shoreward_dir(pristine, cx, cz):
    """Direction (radians) along which the PRISTINE bench terrain first LEAVES the
    lawn datum (descends below LOWLAND-0.05, or the terrain sheet ends) -- the true
    shore-descent ray. Sea sheets are useless as a beacon here: they run UNDER the
    land (measured; the SEA4-UNDER-LAND configuration). Ties on first-leave radius
    break toward the heading with the LOWEST pristine terrain 4u further out (the
    fastest-descending ray). Returns (theta, r_at_leave) or (None, None)."""
    cands = []
    for k in range(72):
        th = math.radians(k * 5.0)
        for i in range(2, 81):
            r = i * 0.5
            x, z = cx + r * math.sin(th), cz + r * math.cos(th)
            terr = [s for s in sheets_at(pristine, x, z) if s[3] == "Terrain"]
            if not terr or terr[0][0] < LOWLAND - 0.05:
                x2, z2 = cx + (r + 4) * math.sin(th), cz + (r + 4) * math.cos(th)
                t2 = [s for s in sheets_at(pristine, x2, z2) if s[3] == "Terrain"]
                cands.append((r, t2[0][0] if t2 else -99.0, th))
                break
    if not cands:
        return (None, None)
    rmin = min(c[0] for c in cands)
    r, _, th = min((c for c in cands if c[0] <= rmin + 0.5), key=lambda c: c[1])
    return (th, r)


def shore_profile(pristine, live, cx, cz, th):
    """The bench ground line through the centroid along heading th: r in [-24, +32]
    step 0.5 (negative = inland). Per sample: pristine top-Terrain y + topograph,
    Sea/Beach y, and the LIVE top render sheet (carried surface) for contrast."""
    samples = []
    for i in range(-48, 65):
        r = i * 0.5
        x, z = cx + r * math.sin(th), cz + r * math.cos(th)
        shp = sheets_at(pristine, x, z, render=True)
        terr = [s for s in shp if s[3] == "Terrain"]
        sea = [s for s in shp if s[3].startswith("Sea")]
        beach = [s for s in shp if s[3].startswith("Beach")]
        shl = sheets_at(live, x, z, render=True)
        samples.append(dict(
            r=r, x=round(x, 2), z=round(z, 2),
            terr_y=round(terr[0][0], 3) if terr else None,
            topo=terr[0][1] if terr else None,
            mapid=terr[0][2] if terr else None,
            sea_y=round(sea[0][0], 3) if sea else None,
            beach_y=round(beach[0][0], 3) if beach else None,
            live_top_y=round(shl[0][0], 3) if shl else None,
            live_top_part=shl[0][3] if shl else None,
            live_top_mapid=shl[0][2] if shl else None))
    # derived marks, scanning seaward
    desc_r = next((s["r"] for s in samples
                   if s["r"] >= -R_SITE and s["terr_y"] is not None
                   and s["terr_y"] < LOWLAND - 0.05), None)
    end_r = next((s["r"] for s in samples
                  if s["r"] >= -R_SITE and s["terr_y"] is None), None)
    wline_r = next((s["r"] for s in samples
                    if s["terr_y"] is not None and s["sea_y"] is not None
                    and s["terr_y"] <= s["sea_y"] + 0.05), None)
    water_ys = [s["sea_y"] for s in samples if s["sea_y"] is not None]
    water_y = round(sorted(water_ys)[len(water_ys) // 2], 3) if water_ys else None
    # run-length topo sequence (the class story along the line)
    rle = []
    for s in samples:
        t = s["topo"]
        if rle and rle[-1]["topo"] == t:
            rle[-1]["r1"] = s["r"]
        else:
            rle.append(dict(topo=t, r0=s["r"], r1=s["r"]))
    return samples, dict(descent_start_r=desc_r, terrain_end_r=end_r,
                         waterline_r=wline_r, water_y=water_y, topo_runs=rle)


def chain_transect(live, pristine, ch):
    """Perpendicular section through the chain's plan midpoint: the LIVE sheet stack
    (top 4: y, topo, mapid, part) and the pristine Terrain y, r in [-6,+6] step 0.25
    along the chain's left normal. Solves the border-plane blind spot: a chain lying
    ON x=448 is sampled from BOTH blocks' sides."""
    # plan midpoint at half the polyline length
    total = sum(math.hypot(ch[i + 1][0] - ch[i][0], ch[i + 1][2] - ch[i][2])
                for i in range(len(ch) - 1))
    s, tgt = 0.0, total / 2
    mx, mz = ch[0][0], ch[0][2]
    for i in range(len(ch) - 1):
        seg = math.hypot(ch[i + 1][0] - ch[i][0], ch[i + 1][2] - ch[i][2])
        if s + seg >= tgt and seg > 1e-9:
            f = (tgt - s) / seg
            mx = ch[i][0] + f * (ch[i + 1][0] - ch[i][0])
            mz = ch[i][2] + f * (ch[i + 1][2] - ch[i][2])
            break
        s += seg
    dx, dz = ch[-1][0] - ch[0][0], ch[-1][2] - ch[0][2]
    L = math.hypot(dx, dz) or 1.0
    nx, nz = -dz / L, dx / L
    rows = []
    for i in range(-24, 25):
        r = i * 0.25
        x, z = mx + r * nx, mz + r * nz
        shl = sheets_at(live, x, z, render=True)[:4]
        pt = [q for q in sheets_at(pristine, x, z, render=True) if q[3] == "Terrain"]
        rows.append(dict(r=r, x=round(x, 2), z=round(z, 2),
                         live=[[round(q[0], 3), q[1], q[2], q[3]] for q in shl],
                         pristine_terr_y=round(pt[0][0], 3) if pt else None))
    return dict(mid=[round(mx, 2), round(mz, 2)],
                normal=[round(nx, 3), round(nz, 3)], rows=rows)


def global_hover_sweep(live, edges, tris, p_edges):
    """Every GLOBAL once-edge in the loaded region whose midpoint has a sheet
    > HOVER_MIN below (scan sheets), EXCLUDING the region-rim load boundaries
    (x=320/512, z=-448/-576 -- artifacts of loading 6 blocks). Each classified:
    bench-idiom (the same edge is a pristine once-edge -- the bench coast's own
    free border, present before the wall) vs live-only (this arc's authorship).
    The guard: no live-only hover slit outside the two registered sites."""
    p_once = {k for k, own in p_edges.items() if len(own) == 1}
    out = []
    for k, own in edges.items():
        if len(own) != 1:
            continue
        va, vb = k
        on_rim = any(abs(va[c] - p) < 0.05 and abs(vb[c] - p) < 0.05
                     for c, planes in ((0, (320.0, 512.0)), (2, (-448.0, -576.0)))
                     for p in planes)
        if on_rim:
            continue
        mx, my, mz = ((va[0] + vb[0]) / 2, (va[1] + vb[1]) / 2, (va[2] + vb[2]) / 2)
        bs = below_at(live, mx, mz, my, render=False)
        if bs is None or my - bs[0] <= HOVER_MIN:
            continue
        br = below_at(live, mx, mz, my, render=True)
        d = {name: round(math.hypot(mx - cx, mz - cz), 1)
             for (name, cx, cz, _reg) in SITES}
        out.append(dict(mid=[round(mx, 2), round(my, 3), round(mz, 2)],
                        gap=round(my - bs[0], 3), below_part=bs[3], below_topo=bs[1],
                        gap_render=round(my - br[0], 3) if br else None,
                        below_render=f"{br[3]}:mapid{br[2]}" if br else None,
                        underlay_sealed=bool(br and br[2] == 4078
                                             and my - br[0] <= HOVER_MIN),
                        plan_len=round(math.hypot(va[0] - vb[0], va[2] - vb[2]), 2),
                        bench_idiom=k in p_once, dist=d,
                        in_a_site=any(v <= R_SITE for v in d.values())))
    return out


# ---------------------------------------------------------------- per-site anatomy
def site_anatomy(live, pristine, name, cx, cz, registered, edges, tris,
                 pristine_keys, p_edges):
    once = {k: own[0] for k, own in edges.items() if len(own) == 1}
    p_once = [k for k, own in p_edges.items() if len(own) == 1]
    p_once_near = [k for k in p_once
                   if math.hypot((k[0][0] + k[1][0]) / 2 - cx,
                                 (k[0][2] + k[1][2]) / 2 - cz) <= 40.0]

    # -- 1. every once-edge in radius, measured -------------------------------
    recs, hover_keys = [], []
    for k, own in sorted(once.items()):
        va, vb = k
        mx, mz = (va[0] + vb[0]) / 2, (va[2] + vb[2]) / 2
        if math.hypot(mx - cx, mz - cz) > R_SITE:
            continue
        my = (va[1] + vb[1]) / 2
        tri = tris[own]
        carried = tri_key(tri) not in pristine_keys
        bs = below_at(live, mx, mz, my, render=False)
        br = below_at(live, mx, mz, my, render=True)
        d_bench = min((seg_plan_dist(mx, mz, a, b) for (a, b) in p_once_near),
                      default=None)
        on_border, open_side = None, None
        for bxp in BORDERS_X:
            if abs(va[0] - bxp) < 0.05 and abs(vb[0] - bxp) < 0.05:
                on_border = f"x={bxp:g}"
                open_side = ("x>" if own[0][0] * 64.0 + 32.0 < bxp else "x<") + f"{bxp:g}"
        for bzp in BORDERS_Z:
            if abs(va[2] - bzp) < 0.05 and abs(vb[2] - bzp) < 0.05:
                on_border = f"z={bzp:g}"
                open_side = ("z<" if -own[0][1] * 64.0 - 32.0 > bzp else "z>") + f"{bzp:g}"
        hover = bs is not None and (my - bs[0]) > HOVER_MIN
        rec = dict(
            a=list(va), b=list(vb), y=[va[1], vb[1]],
            mid=[round(mx, 2), round(my, 2), round(mz, 2)],
            plan_len=round(math.hypot(va[0] - vb[0], va[2] - vb[2]), 3),
            plan_dir_deg=round(math.degrees(
                math.atan2(vb[2] - va[2], vb[0] - va[0])) % 180.0, 1),
            owner_block=list(own[0]), owner_tri=own[1],
            owner_topo=tri[4], owner_mapid=tri[3], owner_carried=carried,
            owner_ny=round(tri[5], 3),
            owner_face=("curtain" if abs(tri[5]) <= 0.2 else "sheet"),
            owner_verts=[[round(c, 3) for c in v] for v in (tri[0], tri[1], tri[2])],
            gap_scan=round(my - bs[0], 3) if bs else None,
            below_scan=dict(y=round(bs[0], 3), topo=bs[1], mapid=bs[2],
                            part=bs[3]) if bs else None,
            gap_render=round(my - br[0], 3) if br else None,
            below_render=dict(y=round(br[0], 3), topo=br[1], mapid=br[2],
                              part=br[3]) if br else None,
            plan_d_to_bench_once=round(d_bench, 3) if d_bench is not None else None,
            on_border=on_border, open_side=open_side, hover=hover)
        recs.append(rec)
        if hover:
            hover_keys.append(k)

    # -- calibration: probe_vshore_gap's PER-BLOCK counting, same radius ------
    calib = per_block_calibration(live, cx, cz, edges, tris)

    # -- 2. carried vs bench census in the window -----------------------------
    win_tris = [t for (bk, ti), t in tris.items()
                if math.hypot((t[0][0] + t[1][0] + t[2][0]) / 3 - cx,
                              (t[0][2] + t[1][2] + t[2][2]) / 3 - cz) <= R_SITE + 4]
    carried_tris = [t for t in win_tris if tri_key(t) not in pristine_keys]
    carried_mapids = Counter(str(t[3]) for t in carried_tris)
    carried_topos = Counter(str(t[4]) for t in carried_tris)

    # -- 3. shore anatomy + block borders -------------------------------------
    th, r_sea = shoreward_dir(pristine, cx, cz)
    profile, marks = (shore_profile(pristine, live, cx, cz, th)
                      if th is not None else ([], {}))
    hx = [v[0] for k in hover_keys for v in k]
    hz = [v[2] for k in hover_keys for v in k]
    borders = {}
    for bxp in BORDERS_X:
        borders[f"x={bxp:g}"] = dict(
            centroid_dist=round(abs(cx - bxp), 2),
            chain_crosses=bool(hx and min(hx) < bxp - 0.01 and max(hx) > bxp + 0.01))
    for bzp in BORDERS_Z:
        borders[f"z={bzp:g}"] = dict(
            centroid_dist=round(abs(cz - bzp), 2),
            chain_crosses=bool(hz and min(hz) < bzp - 0.01 and max(hz) > bzp + 0.01))

    # -- 4. the seal chains ----------------------------------------------------
    chains, cycles = build_chains(hover_keys)
    chain_recs = []
    for ch in chains + cycles:
        pts, s = [], 0.0
        prev = None
        # vertices + edge midpoints, with the drop profile beneath each
        stations = []
        for i, v in enumerate(ch):
            if prev is not None:
                mxx, myy, mzz = ((prev[0] + v[0]) / 2, (prev[1] + v[1]) / 2,
                                 (prev[2] + v[2]) / 2)
                stations.append((s + math.hypot(v[0] - prev[0], v[2] - prev[2]) / 2,
                                 mxx, myy, mzz, "mid"))
                s += math.hypot(v[0] - prev[0], v[2] - prev[2])
            stations.append((s, v[0], v[1], v[2], "vert"))
            prev = v
        drop = []
        for (ss, x, y, z, kind) in stations:
            bs = below_at(live, x, z, y, render=False)
            br = below_at(live, x, z, y, render=True)
            pt = [s for s in sheets_at(pristine, x, z) if s[3] == "Terrain"]
            drop.append(dict(
                s=round(ss, 2), kind=kind,
                x=round(x, 2), y=round(y, 3), z=round(z, 2),
                below_scan_y=round(bs[0], 3) if bs else None,
                below_scan=f"{bs[3]}:topo{bs[1]}" if bs else None,
                gap_scan=round(y - bs[0], 3) if bs else None,
                below_render_y=round(br[0], 3) if br else None,
                below_render=f"{br[3]}:topo{br[1]}:mapid{br[2]}" if br else None,
                gap_render=round(y - br[0], 3) if br else None,
                pristine_terr_y=round(pt[0][0], 3) if pt else None,
                pristine_terr_topo=pt[0][1] if pt else None))
        bottom_scan = Counter(d["below_scan"] for d in drop if d["below_scan"])
        bottom_render = Counter(d["below_render"] for d in drop if d["below_render"])
        chain_recs.append(dict(
            closed=ch in cycles, n_verts=len(ch),
            verts=[[round(c, 3) for c in v] for v in ch],
            plan_len=round(s, 2),
            y_min=round(min(v[1] for v in ch), 3),
            y_max=round(max(v[1] for v in ch), 3),
            drop_profile=drop,
            seal_bottom_scan=dict(bottom_scan),
            seal_bottom_render=dict(bottom_render),
            transect=chain_transect(live, pristine, ch)))
    chain_recs.sort(key=lambda c: -c["plan_len"])

    return dict(
        site=name, centroid=[cx, cz], radius=R_SITE, registered=registered,
        calibration_per_block=calib,
        once_edges_in_radius=len(recs),
        hover_edges=sum(1 for r in recs if r["hover"]),
        hover_total_plan_len=round(sum(r["plan_len"] for r in recs if r["hover"]), 2),
        hover_gap_scan_range=[
            round(min(r["gap_scan"] for r in recs if r["hover"]), 2),
            round(max(r["gap_scan"] for r in recs if r["hover"]), 2)]
        if any(r["hover"] for r in recs) else None,
        hover_owner_carried=sum(1 for r in recs if r["hover"] and r["owner_carried"]),
        edges=recs,
        window_tris=len(win_tris), carried_tris=len(carried_tris),
        carried_mapid_hist=dict(carried_mapids),
        carried_topo_hist=dict(carried_topos),
        shoreward_dir_deg=round(math.degrees(th), 1) if th is not None else None,
        r_shore_leaves_datum=r_sea, block_borders=borders,
        shore_marks=marks, shore_profile=profile,
        chains=chain_recs), hover_keys


def per_block_calibration(live, cx, cz, edges, tris):
    """Reproduce probe_vshore_gap's numbers (PER-BLOCK once-edges, all_sheets scan,
    >0.5 hover) inside this site radius -- ties this instrument to the registered
    east figure -- THEN classify each of those edges against the GLOBAL ownership
    map: a per-block once-edge with a second owner in ANOTHER block is a border-SEAM
    PHANTOM (the surface is stitched across the plane, no visual slit at that edge);
    a second owner in the SAME block means duplicate/overlay geometry closes it
    (render-closed if every partner is 4078-tagged); only global-once edges are the
    TRUE open boundary a seal must close."""
    n, tot, gmax = 0, 0.0, 0.0
    kinds = Counter()
    per_edge = []
    for bk in sorted(live):
        for m in live[bk]:
            if m["name"] != "Terrain":
                continue
            ec = defaultdict(list)
            for ti, tri in enumerate(m["tris"]):
                vs = [rv(p) for p in (tri[0], tri[1], tri[2])]
                for a, b in ((0, 1), (1, 2), (2, 0)):
                    ec[tuple(sorted((vs[a], vs[b])))].append(ti)
            for (va, vb), owners in ec.items():
                if len(owners) != 1:
                    continue
                mx, my, mz = ((va[0] + vb[0]) / 2, (va[1] + vb[1]) / 2,
                              (va[2] + vb[2]) / 2)
                if math.hypot(mx - cx, mz - cz) > R_SITE:
                    continue
                below = [s[0] for s in W.all_sheets(live, mx, mz) if s[0] < my - 0.5]
                if not below:
                    continue
                n += 1
                tot += math.hypot(va[0] - vb[0], va[2] - vb[2])
                gmax = max(gmax, my - max(below))
                gown = edges.get(tuple(sorted((va, vb))), [])
                if len(gown) <= 1:
                    kind = "TRUE-open"
                else:
                    partners = [o for o in gown if o[0] != bk or o[1] not in owners]
                    if any(o[0] != bk for o in partners):
                        kind = "seam-phantom(border-stitched)"
                    elif partners and all(tris[o][3] == 4078 for o in partners):
                        kind = "closed-by-4078-underlay"
                    else:
                        kind = "same-block-shared"
                kinds[kind] += 1
                per_edge.append(dict(mid=[round(mx, 2), round(my, 2), round(mz, 2)],
                                     block=list(bk), kind=kind,
                                     global_owners=len(gown)))
    return dict(hover_edges=n, total_plan_len=round(tot, 1), max_gap=round(gmax, 2),
                kinds=dict(kinds), per_edge=per_edge)


# ---------------------------------------------------------------- render
def render_site(path, name, cx, cz, live, edges, tris, pristine_keys, p_edges,
                hover_keys):
    half, sc = 16.0, 28
    wpx = int(2 * half * sc)
    img = Image.new("RGB", (wpx, wpx), (12, 12, 16))
    dr = ImageDraw.Draw(img)

    def P(x, z):
        return ((x - (cx - half)) * sc, ((cz + half) - z) * sc)

    # block borders (grey)
    for bxp in BORDERS_X:
        if abs(bxp - cx) <= half:
            dr.line([P(bxp, cz - half), P(bxp, cz + half)], fill=(90, 90, 90), width=1)
    for bzp in BORDERS_Z:
        if abs(bzp - cz) <= half:
            dr.line([P(cx - half, bzp), P(cx + half, bzp)], fill=(90, 90, 90), width=1)

    # water verts (cyan) + beach verts (sand)
    for bk in sorted(live):
        for m in live[bk]:
            if m["name"].startswith("Sea"):
                col = (0, 200, 220)
            elif m["name"].startswith("Beach"):
                col = (210, 190, 120)
            else:
                continue
            done = set()
            for tri in m["tris"]:
                for v in (tri[0], tri[1], tri[2]):
                    k = rv(v)
                    if k in done or abs(v[0] - cx) > half or abs(v[2] - cz) > half:
                        continue
                    done.add(k)
                    x, y = P(v[0], v[2])
                    dr.ellipse([x - 2, y - 2, x + 2, y + 2], fill=col)

    # carried tri edges (red)
    seen = set()
    for (bk, ti), tri in tris.items():
        if tri_key(tri) in pristine_keys:
            continue
        vs = (rv(tri[0]), rv(tri[1]), rv(tri[2]))
        for a, b in ((0, 1), (1, 2), (2, 0)):
            ek = tuple(sorted((vs[a], vs[b])))
            if ek in seen:
                continue
            seen.add(ek)
            va, vb = ek
            if (abs((va[0] + vb[0]) / 2 - cx) > half
                    or abs((va[2] + vb[2]) / 2 - cz) > half):
                continue
            dr.line([P(va[0], va[2]), P(vb[0], vb[2])], fill=(200, 40, 40), width=1)

    # bench once-edges (blue) -- pristine global once-edges
    for k, own in p_edges.items():
        if len(own) != 1:
            continue
        va, vb = k
        if abs((va[0] + vb[0]) / 2 - cx) > half or abs((va[2] + vb[2]) / 2 - cz) > half:
            continue
        dr.line([P(va[0], va[2]), P(vb[0], vb[2])], fill=(70, 120, 255), width=2)

    # hover chain (yellow, thick) + endpoint heights
    for (va, vb) in hover_keys:
        dr.line([P(va[0], va[2]), P(vb[0], vb[2])], fill=(255, 220, 40), width=3)
    labeled = set()
    for (va, vb) in hover_keys:
        for v in (va, vb):
            k = rv(v)
            if k in labeled:
                continue
            labeled.add(k)
            x, y = P(v[0], v[2])
            dr.text((x + 3, y - 10), f"{v[1]:.1f}", fill=(255, 220, 40))

    # cluster circle (white) + centroid cross
    x0, y0 = P(cx - R_SITE, cz + R_SITE)
    x1, y1 = P(cx + R_SITE, cz - R_SITE)
    dr.ellipse([x0, y0, x1, y1], outline=(240, 240, 240), width=1)
    x, y = P(cx, cz)
    dr.line([x - 5, y, x + 5, y], fill=(240, 240, 240))
    dr.line([x, y - 5, x, y + 5], fill=(240, 240, 240))

    legend = [f"V-SHORE {name.upper()}  centroid ({cx},{cz})  window +/-{half}u",
              "red=carried tri edges  blue=bench once-edges  yellow=hover chain",
              "cyan=sea verts  sand=beach verts  grey=block borders  circle=12u"]
    for i, t in enumerate(legend):
        dr.text((8, 8 + 14 * i), t, fill=(220, 220, 220))
    img.save(path)


# ---------------------------------------------------------------- main
def main():
    OUTD.mkdir(parents=True, exist_ok=True)
    print("loading LIVE deployed world (Disc9 bench) ...")
    live = W.load_world()
    tsrc = {}
    for (bx, by) in W.CELLS:
        p = W.PRISTINE_BK / f"Block[{bx}][{by}] Terrain.ff9mesh"
        if p.is_file():
            tsrc[(bx, by)] = p
    print(f"pristine Terrain files: {len(tsrc)}/6 from {W.PRISTINE_BK}")
    pristine = W.load_world(terrain_src=tsrc)

    edges, tris = terrain_index(live)
    p_edges, p_tris = terrain_index(pristine)
    pristine_keys = {tri_key(t) for t in p_tris.values()}
    print(f"live terrain tris: {len(tris)}  pristine: {len(p_tris)}  "
          f"carried (live-only): {sum(1 for t in tris.values() if tri_key(t) not in pristine_keys)}")

    sweep = global_hover_sweep(live, edges, tris, p_edges)
    outside = [e for e in sweep if not e["in_a_site"] and not e["bench_idiom"]]
    out_open = [e for e in outside if not e["underlay_sealed"]]
    print(f"\nGLOBAL HOVER SWEEP (region minus load rim): {len(sweep)} once-edges "
          f"hover >{HOVER_MIN}u; bench-idiom {sum(1 for e in sweep if e['bench_idiom'])}, "
          f"live-only {sum(1 for e in sweep if not e['bench_idiom'])}, "
          f"live-only OUTSIDE both sites: {len(outside)} "
          f"(render-open {len(out_open)}, underlay-sealed {len(outside) - len(out_open)})")
    for e in sorted(out_open, key=lambda e: -(e["gap_render"] or 0))[:12]:
        print(f"   mid={e['mid']} gapS={e['gap']} gapR={e['gap_render']} "
              f"over {e['below_render']} len={e['plan_len']} dist={e['dist']}")

    report = dict(lowland=LOWLAND, hover_min=HOVER_MIN, radius=R_SITE,
                  global_hover_sweep=sweep, sites=[])
    for (name, cx, cz, registered) in SITES:
        print(f"\n=== SITE {name.upper()} ({cx},{cz})"
              f"{'' if registered else '  [SWEEP-DISCOVERED, not in the registration]'} ===")
        site, hover_keys = site_anatomy(live, pristine, name, cx, cz, registered,
                                        edges, tris, pristine_keys, p_edges)
        report["sites"].append(site)
        c = site["calibration_per_block"]
        print(f"  calibration (per-block, probe method): {c['hover_edges']} hover edges, "
              f"{c['total_plan_len']}u, max gap {c['max_gap']}")
        print(f"    of which: {c['kinds']}")
        print(f"  GLOBAL once-edges in 12u: {site['once_edges_in_radius']}  "
              f"hover: {site['hover_edges']} ({site['hover_total_plan_len']}u, "
              f"scan-gap {site['hover_gap_scan_range']})  "
              f"owners carried: {site['hover_owner_carried']}/{site['hover_edges']}")
        print(f"  window tris: {site['window_tris']}  carried: {site['carried_tris']}  "
              f"mapids {site['carried_mapid_hist']}")
        print(f"  shoreward dir {site['shoreward_dir_deg']} deg, leaves datum at "
              f"r={site['r_shore_leaves_datum']}u; marks: "
              f"descent_r={site['shore_marks'].get('descent_start_r')} "
              f"terrain_end_r={site['shore_marks'].get('terrain_end_r')} "
              f"waterline_r={site['shore_marks'].get('waterline_r')} "
              f"water_y={site['shore_marks'].get('water_y')}")
        print(f"  borders: {site['block_borders']}")
        for ch in site["chains"]:
            print(f"  chain: {ch['n_verts']} verts, {ch['plan_len']}u, "
                  f"y {ch['y_min']}..{ch['y_max']}, closed={ch['closed']}, "
                  f"bottom(render)={ch['seal_bottom_render']}")
        png = OUTD / f"vshore_site_{name}.png"
        render_site(png, name, cx, cz, live, edges, tris, pristine_keys, p_edges,
                    hover_keys)
        print(f"  render -> {png}")

    out = OUTD / "vshore_anatomy.json"
    json.dump(report, open(out, "w"), indent=1)
    print(f"\nreport -> {out}")


if __name__ == "__main__":
    main()
