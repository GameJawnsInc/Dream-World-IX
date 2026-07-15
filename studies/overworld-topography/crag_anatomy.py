"""THE CRAG DONOR ANATOMY -- qualify the crag island (blocks 9-10, 5-7) as a
``world-mountain --donor``, the way the Uaho/Daguerreo passes qualified theirs.

``carve_mountain`` reads ONE donor block and carries its largest massif-rock component
whole (rim ring + enclosed pockets + optional alcove floor + Object-aperture plugs), so
donor qualification is per BLOCK, not per island. Per unknown:

  A. ROCK CENSUS -- which topos the crag's rock actually uses (Uaho = 49/7/62), per
     block + merged; component sizes; does the big massif CROSS block borders (a
     cross-border component cannot be carried by the single-block pipeline)?
  B. BLOB ASSEMBLY per candidate block -- replicate the module's exact blob build
     (largest in-block rock component + enclosed-raised flood + pocket fill): does the
     once-edge rim chain into simple rings inside the block? Extra rings = apertures --
     do they match the block's Object part vertex set (THE FALLS-APERTURE LAW)?
  C. RIM STATS -- points, y-range, max adjacent-point y step (a notch oscillation like
     Uaho's 1.5<->6.3 signals an ALCOVE-floor carry need), max plan radius vs the
     in-block placement ceiling (rim + SCAN_BAND + 2 must fit in 64u => radius < ~23.5,
     and < ~20 to fit the r31 bench mint's grass pocket), de-tilt plane slope/residual.
  D. CLASS -- THE TWO MOUNTAIN CLASSES metric on the in-block blob: quad course-to-
     course vert share (lattice-sheet massif ~74% like the horseshoe / Uaho vs 0% =
     shingled escarpment strips).
  E. TILE LANGUAGE -- 128px corner-phase peakiness + phase vs ROCK_CHART_PHASE
     (the aperture-plug chart gate assumes the shared rock-band phase).
  F. DISPATCH BITS -- event/area census (informational; the DONOR-DISPATCH STRIP
     normalizes them at carve time).
  G. FEET -- rim-adjacent outside topos (grass-bounded like the mesa criterion, or
     coast/river-locked?).
  H. THE DRY CARVE (decisive) -- run the real ``interior.carve_mountain`` per candidate
     block against a fresh offline r31 bench mint (no deploy, no game writes): which
     gates pass, which refuse, and why.

Artifacts -> out/crag_anatomy.json + out/crag_map.png (top-down, rock components
colored, candidate blocks framed). Run from the repo root:
    py studies/overworld-topography/crag_anatomy.py
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import interior as IN                  # noqa: E402
from ff9mapkit.world.island import build_landmass           # noqa: E402
from ff9mapkit.world import mesh as M                       # noqa: E402

BLOCKS = [(9, 5), (10, 5), (9, 6), (10, 6), (9, 7), (10, 7)]
BLOCK = 64.0
ROCK = set(IN.MOUNTAIN_ROCK_TOPOS)
TILE_U, TILE_V = 0.0625, 0.03125
OUTD = Path(__file__).with_name("out")
kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))
out = {"blocks": {}, "region": {}}

# ---- A. the merged region: rock census + cross-block components ---------------------------------
tris = []
present = []
for (bx, by) in BLOCKS:
    try:
        bm = X.read_block(bx, by, disc=1, part="terrain")
    except ValueError:
        print(f"({bx},{by}): NO terrain mesh on disc 1 -- skipped")
        continue
    present.append((bx, by))
    idx = np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3)
    for i in idx:
        d = X.decode_id(int(round(bm.tangents[i[0]][0])))
        tris.append(dict(
            w=[(bm.verts[j][0] + BLOCK * bx, bm.verts[j][1],
                bm.verts[j][2] - BLOCK * by) for j in i],
            uv=[(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in i],
            topo=d["topograph"], ea=(d["event"], d["area"]), blk=(bx, by)))
topo_c = Counter(t["topo"] for t in tris)
ea_c = Counter(t["ea"] for t in tris if t["topo"] in ROCK)
print(f"region {BLOCKS}: {len(tris)} tris; topo census {dict(topo_c.most_common(12))}")
print(f"F. rock-tri (event,area) census: {dict(ea_c.most_common(8))}")

edge_tris = defaultdict(list)
for ti, t in enumerate(tris):
    ps = [kk(v) for v in t["w"]]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        edge_tris[tuple(sorted((ps[a], ps[b])))].append(ti)
adj = defaultdict(set)
for ts in edge_tris.values():
    r = [t for t in ts if tris[t]["topo"] in ROCK]
    for i in range(len(r)):
        for j in range(i + 1, len(r)):
            adj[r[i]].add(r[j]); adj[r[j]].add(r[i])
comps, seen = [], set()
for s in range(len(tris)):
    if tris[s]["topo"] not in ROCK or s in seen:
        continue
    comp = {s}; st = [s]
    while st:
        t = st.pop()
        for t2 in adj[t]:
            if t2 not in comp:
                comp.add(t2); st.append(t2)
    seen |= comp
    comps.append(comp)
comps.sort(key=len, reverse=True)
print(f"A. cross-block rock components: {len(comps)}, sizes {[len(c) for c in comps[:8]]}")
for ci, c in enumerate(comps[:6]):
    blks = Counter(tris[t]["blk"] for t in c)
    tps = Counter(tris[t]["topo"] for t in c)
    xs = [v[0] for t in c for v in tris[t]["w"]]
    zs = [v[2] for t in c for v in tris[t]["w"]]
    ys = [v[1] for t in c for v in tris[t]["w"]]
    print(f"   comp{ci}: {len(c):4d} tris, blocks {dict(blks)}, topos {dict(tps)}, "
          f"extent {max(xs) - min(xs):.0f}x{max(zs) - min(zs):.0f}u "
          f"y[{min(ys):.1f},{max(ys):.1f}]")
out["region"] = dict(
    topo_census={str(k): v for k, v in topo_c.items()},
    rock_ea={str(k): v for k, v in ea_c.items()},
    comps=[dict(n=len(c), blocks={str(k): v for k, v in
                                  Counter(tris[t]["blk"] for t in c).items()})
           for c in comps[:8]])

# A2. the merged component at REGION level: does its rim chain cross-block (what a
# future multi-block donor extension would carry)?
big = comps[0]
eu_r = Counter()
for t in big:
    ps = [kk(v) for v in tris[t]["w"]]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        eu_r[tuple(sorted((ps[a], ps[b])))] += 1
oe_r = [e for e, n in eu_r.items() if n == 1]
deg_r = Counter()
for a, b in oe_r:
    deg_r[a] += 1
    deg_r[b] += 1
odd_r = [p for p, n in deg_r.items() if n != 2]
if odd_r:
    print(f"A2. region-level massif rim: {len(odd_r)} odd-degree points -- does NOT "
          f"chain even cross-block (identity-weld gaps at {odd_r[:4]})")
    out["region"]["rim"] = dict(odd_points=len(odd_r))
else:
    rings_r = IN.chain_rings(oe_r, "region massif")
    rings_r.sort(key=lambda g: -abs(IN.signed_area(g)))
    rim_r = rings_r[0]
    ys_r = [p[1] for p in rim_r]
    bx_r = [v[0] for t in big for v in tris[t]["w"]]
    bz_r = [v[2] for t in big for v in tris[t]["w"]]
    c_r = ((min(bx_r) + max(bx_r)) / 2, (min(bz_r) + max(bz_r)) / 2)
    rad_r = max(math.hypot(p[0] - c_r[0], p[2] - c_r[1]) for p in rim_r)
    Am_r = np.array([[p[0] - c_r[0], p[2] - c_r[1], 1.0] for p in rim_r])
    bv_r = np.array([p[1] for p in rim_r])
    (ta_r, tb_r, tc_r), *_rest = np.linalg.lstsq(Am_r, bv_r, rcond=None)
    res_r = bv_r - Am_r @ np.array([ta_r, tb_r, tc_r])
    feet_r = Counter()
    rimset_r = set(rim_r)
    for e, ts in edge_tris.items():
        if e[0] in rimset_r and e[1] in rimset_r:
            for t in ts:
                if t not in big:
                    feet_r[tris[t]["topo"]] += 1
    print(f"A2. region-level massif rim CHAINS: rings {[len(g) for g in rings_r]}, "
          f"outer rim {len(rim_r)} pts y[{min(ys_r):.1f},{max(ys_r):.1f}] "
          f"radius {rad_r:.1f}u, de-tilt "
          f"{math.degrees(math.atan(math.hypot(ta_r, tb_r))):.1f}deg "
          f"residual [{res_r.min():+.2f},{res_r.max():+.2f}], feet {dict(feet_r.most_common(5))}")
    out["region"]["rim"] = dict(
        rings=[len(g) for g in rings_r], pts=len(rim_r),
        y=[round(min(ys_r), 1), round(max(ys_r), 1)], radius=round(rad_r, 1),
        detilt_deg=round(math.degrees(math.atan(math.hypot(ta_r, tb_r))), 1),
        residual=[round(float(res_r.min()), 2), round(float(res_r.max()), 2)],
        feet={str(k): v for k, v in feet_r.items()})

# ---- B/C/D/E/G per candidate block: the module's exact blob assembly ----------------------------
def block_blob(bx, by):
    """Replicate carve_mountain's donor section on ONE block; return findings."""
    don = X.read_block(bx, by, disc=1)
    dV = np.asarray(don.verts, dtype=np.float64) + np.array(
        [BLOCK * bx, 0.0, -BLOCK * by])
    dU = np.asarray(don.uvs, dtype=np.float64)
    dntri = len(don.flat_index) // 3
    dtri = [don.flat_index[3 * t:3 * t + 3] for t in range(dntri)]
    dtopo = [X.decode_id(int(round(don.tangents[i[0]][0])))["topograph"] for i in dtri]
    d_edge = defaultdict(list)
    for t, i in enumerate(dtri):
        for a, b in ((0, 1), (1, 2), (2, 0)):
            d_edge[tuple(sorted((kk(dV[i[a]]), kk(dV[i[b]]))))].append(t)
    adjR = defaultdict(set)
    for e, ts in d_edge.items():
        r = [t for t in ts if dtopo[t] in ROCK]
        for i in range(len(r)):
            for j in range(i + 1, len(r)):
                adjR[r[i]].add(r[j]); adjR[r[j]].add(r[i])
    comps2, seen2 = [], set()
    for s in range(dntri):
        if dtopo[s] not in ROCK or s in seen2:
            continue
        comp = {s}; st = [s]
        while st:
            t = st.pop()
            for t2 in adjR[t]:
                if t2 not in comp:
                    comp.add(t2); st.append(t2)
        seen2 |= comp
        comps2.append(comp)
    if not comps2:
        return dict(rock=0)
    comps2.sort(key=len, reverse=True)
    blob = set(comps2[0])
    r = dict(rock=sum(1 for tp in dtopo if tp in ROCK),
             comp_sizes=[len(c) for c in comps2[:5]], blob0=len(blob))

    def once_edges(tset):
        eu = Counter()
        for t in tset:
            for a, b in ((0, 1), (1, 2), (2, 0)):
                eu[tuple(sorted((kk(dV[dtri[t][a]]), kk(dV[dtri[t][b]]))))] += 1
        return [e for e, n in eu.items() if n == 1]

    # does the rim chain? (odd-degree points = the component crosses the block border)
    oe = once_edges(blob)
    deg = Counter()
    for a, b in oe:
        deg[a] += 1
        deg[b] += 1
    odd = [p for p, n in deg.items() if n != 2]
    r["rim_odd_points"] = len(odd)
    if odd:
        on_border = sum(1 for p in odd
                        if min(p[0] % BLOCK, BLOCK - p[0] % BLOCK) < 0.05
                        or min(-p[2] % BLOCK, BLOCK - (-p[2] % BLOCK)) < 0.05)
        r["odd_on_border"] = on_border
        return r                                           # cannot chain -- stop here
    rings = IN.chain_rings(oe, f"({bx},{by}) blob")
    rings.sort(key=lambda g: -abs(IN.signed_area(g)))
    # enclosed-raised flood + pocket fill (the module's steps), then re-ring
    if len(rings) > 1:
        inner_pts = {p for g in rings[1:] for p in g}
        st = [t for e in once_edges(blob) if e[0] in inner_pts and e[1] in inner_pts
              for t in d_edge[e] if t not in blob]
        while st:
            t = st.pop()
            if t in blob:
                continue
            blob.add(t)
            for a, b in ((0, 1), (1, 2), (2, 0)):
                for t2 in d_edge[tuple(sorted((kk(dV[dtri[t][a]]), kk(dV[dtri[t][b]]))))]:
                    if t2 not in blob and dtopo[t2] not in ROCK:
                        st.append(t2)
        oe = once_edges(blob)
        rings = IN.chain_rings(oe, f"({bx},{by}) blob+fill")
        rings.sort(key=lambda g: -abs(IN.signed_area(g)))
    r["blob"] = len(blob)
    r["rings"] = [len(g) for g in rings]
    r["pocket_topos"] = dict(Counter(dtopo[t] for t in blob if dtopo[t] not in ROCK))
    # apertures = extra rings; are they the Object part's verts?
    if len(rings) > 1:
        try:
            om = X.read_block(bx, by, disc=1, part="object")
            okeys = {kk(p) for p in np.asarray(om.verts, dtype=np.float64)}
            r["apertures_are_object"] = all(p in okeys for g in rings[1:] for p in g)
        except Exception:
            r["apertures_are_object"] = "NO OBJECT PART"
    rim = rings[0]
    ys = [p[1] for p in rim]
    steps = [abs(rim[(i + 1) % len(rim)][1] - rim[i][1]) for i in range(len(rim))]
    bpts = np.array([dV[i] for t in blob for i in dtri[t]])
    c_local = ((bpts[:, 0].min() + bpts[:, 0].max()) / 2,
               (bpts[:, 2].min() + bpts[:, 2].max()) / 2)
    r_rim = max(math.hypot(p[0] - c_local[0], p[2] - c_local[1]) for p in rim)
    Amat = np.array([[p[0] - c_local[0], p[2] - c_local[1], 1.0] for p in rim])
    bvec = np.array([p[1] for p in rim])
    (ta, tb, tc), *_ = np.linalg.lstsq(Amat, bvec, rcond=None)
    res = bvec - Amat @ np.array([ta, tb, tc])
    r["rim"] = dict(pts=len(rim), y=[round(min(ys), 1), round(max(ys), 1)],
                    max_step=round(max(steps), 2),
                    radius=round(r_rim, 1),
                    detilt_deg=round(math.degrees(math.atan(math.hypot(ta, tb))), 1),
                    residual=[round(float(res.min()), 2), round(float(res.max()), 2)])
    r["peak_y"] = round(float(bpts[:, 1].max()), 1)
    # G. feet: outside topos adjacent to the rim
    rimset = set(rim)
    feet = Counter()
    for e, ts in d_edge.items():
        if e[0] in rimset and e[1] in rimset:
            for t in ts:
                if t not in blob:
                    feet[dtopo[t]] += 1
    r["feet_topos"] = dict(feet.most_common(6))
    # D. the class metric: quads + course-to-course vert share (lattice vs shingle)
    e2w = defaultdict(list)
    for t in blob:
        ps = [kk(dV[i]) for i in dtri[t]]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            e2w[tuple(sorted((ps[a], ps[b])))].append(t)
    paired, quads = {}, []
    for e, ts in e2w.items():
        if len(ts) != 2 or ts[0] in paired or ts[1] in paired:
            continue
        vs = {kk(dV[i]) for t in ts for i in dtri[t]}
        if len(vs) != 4:
            continue
        vs = sorted(vs, key=lambda p: p[1])
        lo, hi = vs[:2], vs[2:]
        if abs(lo[0][1] - lo[1][1]) > 1.5 or abs(hi[0][1] - hi[1][1]) > 1.5:
            continue
        paired[ts[0]] = paired[ts[1]] = len(quads)
        quads.append(dict(lo=lo, hi=hi, y=sum(p[1] for p in lo + hi) / 4))
    hi_all = set()
    for q in quads:
        hi_all.update(q["hi"])
    vweld = sum(1 for q in quads if any(p in hi_all for p in q["lo"]))
    r["class"] = dict(quads=len(quads),
                      vweld_share=round(vweld / max(1, len(quads)), 2),
                      verdict=("lattice-sheet massif" if quads and
                               vweld / len(quads) > 0.4 else "shingled walls"))
    # E. tile language: corner phase of uv-continuous groups (cheap proxy: all rock uvs)
    cu = np.array([dU[i][0] for t in blob for i in dtri[t]
                   if dtopo[t] in ROCK]) % TILE_U
    cv = np.array([dU[i][1] for t in blob for i in dtri[t]
                   if dtopo[t] in ROCK]) % TILE_V
    hu = np.bincount((cu / TILE_U * 16).astype(int) % 16, minlength=16)
    hv = np.bincount((cv / TILE_V * 16).astype(int) % 16, minlength=16)
    puB = float(np.argmax(hu)) * TILE_U / 16
    pvB = float(np.argmax(hv)) * TILE_V / 16
    r["tile_phase"] = dict(u=round(puB, 6), v=round(pvB, 6),
                           matches_rock_chart=[abs(puB - IN.ROCK_CHART_PHASE[0]) < TILE_U / 16,
                                               abs(pvB - IN.ROCK_CHART_PHASE[1]) < TILE_V / 16],
                           peak_u=round(float(hu.max() / max(1.0, hu.mean())), 1),
                           peak_v=round(float(hv.max() / max(1.0, hv.mean())), 1))
    cols = sorted({math.floor((dU[i][0] - IN.ROCK_CHART_PHASE[0]) / TILE_U)
                   for t in blob for i in dtri[t] if dtopo[t] in ROCK})
    rows = sorted({math.floor((dU[i][1] - IN.ROCK_CHART_PHASE[1]) / TILE_V)
                   for t in blob for i in dtri[t] if dtopo[t] in ROCK})
    r["uv_cols"] = cols
    r["uv_rows"] = rows
    return r


print("\n== per-block blob assembly (the module's donor section) ==")
candidates = []
for (bx, by) in present:
    r = block_blob(bx, by)
    out["blocks"][f"{bx},{by}"] = r
    if r.get("rock", 0) == 0:
        print(f"  ({bx},{by}): no massif rock")
        continue
    if r.get("rim_odd_points"):
        print(f"  ({bx},{by}): rock {r['rock']}, blob {r['blob0']} -- rim does NOT chain "
              f"({r['rim_odd_points']} odd pts, {r.get('odd_on_border', '?')} on the block "
              f"border) => CROSS-BLOCK component, not single-block carriable")
        continue
    print(f"  ({bx},{by}): rock {r['rock']}, blob {r['blob']} (comps {r['comp_sizes']}), "
          f"rings {r['rings']}, pockets {r['pocket_topos']}, peak y {r['peak_y']}")
    print(f"      rim: {r['rim']}")
    print(f"      feet {r['feet_topos']}; class {r['class']}")
    print(f"      tiles: phase {r['tile_phase']}, cols {r['uv_cols']} rows {r['uv_rows']}")
    if len(r["rings"]) > 1:
        print(f"      apertures object-backed: {r.get('apertures_are_object')}")
    candidates.append((bx, by, r))

# ---- H. THE DRY CARVE: the real module against a fresh offline bench mint ------------------------
print("\n== H. THE DRY CARVE (offline r31 seed-42 bench mint; no writes) ==")
bench = build_landmass(center=(160.0, -1246.0), base_radius=31.0, seed=42.0,
                       lobes=1, n_patches=0)
# f32 round-trip = the deployed representation the module normally reads
import tempfile
tmp = Path(tempfile.mkdtemp(prefix="ff9_crag_"))
b219 = M.blockmesh_from_ff9mesh(
    M.write_ff9mesh(bench["blocks"][(2, 19)], tmp / "b.ff9mesh"),
    disc=1, x=2, y=19, part="terrain")
for (bx, by, r) in candidates:
    soup = IN.soup_from_blocks({(2, 19): b219})
    try:
        res = IN.carve_mountain(soup, near=(160.0, -1246.0), donor=(bx, by),
                                alcove=None, log=lambda *a: None)
        rep = res["report"]
        print(f"  donor ({bx},{by}): ALL GATES PASS -- placed {res['center']} "
              f"rot {rep['rot_deg']}deg, {rep['blob_tris']} tris (+{rep['plugs']} plugs), "
              f"zip rise {rep['zip_rise']}, rigidity {rep['rock_rigid'] * 100:.1f}%, "
              f"apron {rep['apron_slope']}deg")
        out["blocks"][f"{bx},{by}"]["dry_carve"] = {"ok": True, **{k: rep[k] for k in
                                                    ("blob_tris", "plugs", "zip_rise",
                                                     "rock_rigid", "apron_slope")}}
    except ValueError as e:
        print(f"  donor ({bx},{by}): REFUSED -- {e}")
        out["blocks"][f"{bx},{by}"]["dry_carve"] = {"ok": False, "gate": str(e)}

# ---- the eye: top-down region map -----------------------------------------------------------------
S = 3
x0 = 9 * BLOCK
z1, z0 = -5 * BLOCK, -8 * BLOCK
W, H = int(2 * BLOCK * S), int(3 * BLOCK * S)
img = Image.new("RGB", (W, H), (20, 24, 40))
px = img.load()
comp_of = {}
for ci, c in enumerate(comps):
    for t in c:
        comp_of[t] = ci
PAL = [(230, 80, 80), (80, 200, 120), (90, 140, 240), (240, 200, 70),
       (200, 100, 220), (90, 220, 220)]
order = sorted(range(len(tris)), key=lambda ti: min(v[1] for v in tris[ti]["w"]))
for ti in order:
    t = tris[ti]
    p2 = [((v[0] - x0) * S, (z1 - v[2]) * S) for v in t["w"]]
    xs = [p[0] for p in p2]; ys3 = [p[1] for p in p2]
    if t["topo"] in ROCK:
        col = PAL[comp_of.get(ti, 0) % len(PAL)]
    else:
        y = float(np.mean([v[1] for v in t["w"]]))
        g3 = int(50 + min(1.0, max(0.0, y) / 25.0) * 130)
        col = (g3 - 20, g3, g3 - 30) if t["topo"] in (0, 1, 2, 3, 42) else (g3, g3, g3)
    (ax, ay), (bx2, by2), (cx, cy) = p2
    d = (by2 - cy) * (ax - cx) + (cx - bx2) * (ay - cy)
    if abs(d) < 1e-9:
        continue
    for yy in range(max(0, int(min(ys3))), min(H - 1, int(max(ys3)) + 1) + 1):
        for xx in range(max(0, int(min(xs))), min(W - 1, int(max(xs)) + 1) + 1):
            w0 = ((by2 - cy) * (xx - cx) + (cx - bx2) * (yy - cy)) / d
            w1 = ((cy - ay) * (xx - cx) + (ax - cx) * (yy - cy)) / d
            if w0 >= -0.001 and w1 >= -0.001 and (1 - w0 - w1) >= -0.001:
                px[xx, yy] = col
for gx in range(3):
    for yy in range(H):
        if 0 <= gx * int(BLOCK * S) < W:
            px[min(W - 1, gx * int(BLOCK * S)), yy] = (255, 255, 255)
for gz in range(4):
    for xx in range(W):
        if 0 <= gz * int(BLOCK * S) < H:
            px[xx, min(H - 1, gz * int(BLOCK * S))] = (255, 255, 255)
OUTD.mkdir(exist_ok=True)
img.save(OUTD / "crag_map.png")
print(f"-> {OUTD / 'crag_map.png'}")

(OUTD / "crag_anatomy.json").write_text(json.dumps(out, indent=1, default=str))
print(f"-> {OUTD / 'crag_anatomy.json'}")
