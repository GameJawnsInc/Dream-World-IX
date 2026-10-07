"""uvclass CALIBRATION -- prove the instrument on known cases BEFORE the census judges anything.

C0  decomposition reproduces the recorded patch counts:
      forest_uv_components.py on (19,13)/(17,14) topo-37 (block-local, eps 5e-4)  -> "28-35 patches" (interior KB)
      uaho_flow_anatomy.py  on (0,0) mountain comp (ROCK {49,7,62}, eps 0.0015)      -> 9 patches 47/21/21/12/11/9/7/5/1
C1  quantization floor: an EXACTLY affine stock chart's least-squares residual (mains grass cells)
C2  the three named known cases, as the census will see them (global decomposition, eps 0.5 quanta):
      lowland grass mains  (15,15) topo 0     -> expect tile-sized patches, plan-affine at the floor, recurrent atlas
      (14,13) reference rock wall (464 tris)  -> expect tile language: ~1 tile per quad, recurrent 128px tiles
      (15,15) forest canopy blob (topo 37)    -> expect multi-tri patches that are NOT affine
Prints everything; writes out/calibration.json.  Rerun:  py studies/terrain-malleability/uvclass/uvc_calibrate.py
"""
import json
import math
from collections import Counter, defaultdict

import numpy as np

import uvc_common as C

d = C.load(1, "terrain")
P, UV, T, TOPO, BLK = d["P"], d["UV"], d["T"], d["TOPO"], d["BLK"]
res = {}


def blockmask(bx, by):
    return (BLK[:, 0] == bx) & (BLK[:, 1] == by)


def comps_by_edges(mask, topo_set):
    """edge-connected components of tris with topo in topo_set within mask (no uv test)."""
    idx = np.nonzero(mask & np.isin(TOPO, list(topo_set)))[0]
    edges = defaultdict(list)
    for t in idx:
        ks = [C.poskey(P[t, k]) for k in range(3)]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edges[tuple(sorted((ks[a], ks[b])))].append(t)
    adj = defaultdict(set)
    for ts in edges.values():
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                adj[ts[i]].add(ts[j]); adj[ts[j]].add(ts[i])
    seen, comps = set(), []
    for s in idx:
        if s in seen:
            continue
        comp = {s}; st = [s]
        while st:
            t = st.pop()
            for t2 in adj[t]:
                if t2 not in comp:
                    comp.add(t2); st.append(t2)
        seen |= comp
        comps.append(sorted(comp))
    return sorted(comps, key=len, reverse=True)


def sub_patches(tris, eps_q):
    m = np.zeros(len(P), bool)
    m[tris] = True
    pid = C.patches(P, UV, mask=m, eps_q=eps_q)
    sizes = sorted(Counter(pid[tris]).values(), reverse=True)
    return pid, sizes


# ---- C0: reproduce recorded decompositions ---------------------------------------------------------
print("== C0 decomposition reproduces recorded counts")
c0 = {}
for (bx, by) in ((19, 13), (17, 14), (15, 15)):
    tris = np.nonzero(blockmask(bx, by) & (TOPO == 37))[0]
    _, sizes = sub_patches(tris, eps_q=5e-4 * 1024)
    multi = sum(1 for s in sizes if s >= 2)
    c0[f"forest_{bx}_{by}"] = dict(tris=len(tris), patches=len(sizes), multi_tri_patches=multi, sizes=sizes[:15])
    print(f"  forest ({bx},{by}) topo37: {len(tris)} tris -> {len(sizes)} patches ({multi} multi-tri) {sizes[:12]}")
uaho = comps_by_edges(blockmask(0, 0), {49, 7, 62})[0]
_, sizes = sub_patches(np.array(uaho), eps_q=0.0015 * 1024)
c0["uaho"] = dict(tris=len(uaho), patches=len(sizes), sizes=sizes)
print(f"  uaho (0,0) mountain comp: {len(uaho)} tris -> {len(sizes)} patches {sizes}  (recorded 9: 47/21/21/12/11/9/7/5/1)")
pid_u, _ = sub_patches(np.array(uaho), eps_q=0.0015 * 1024)
up90 = []
for p, n in Counter(pid_u[np.array(uaho)].tolist()).most_common(6):
    tr = np.nonzero(pid_u == p)[0]
    A = np.hstack([P[tr].reshape(-1, 3), np.ones((3 * len(tr), 1))])
    Y = T[tr].reshape(-1, 2)
    coef, *_ = np.linalg.lstsq(A, Y, rcond=None)
    r = np.abs(A @ coef - Y)
    up90.append(dict(n=n, u_p90=round(float(np.percentile(r[:, 0], 90)), 1), v_p90=round(float(np.percentile(r[:, 1], 90)), 1)))
c0["uaho_panel_a3_residual_p90_px"] = up90
print(f"  uaho panels 3D-affine residual p90 (all tri corners, as uaho_flow_anatomy.py B): {up90}")
# C0b: is stock continuity exact-or-nothing? (decomposition sensitivity to the uv-match tolerance)
c0b = {}
for eps in (0.5, 1.5, 3.0):
    pid_e, st = C.patches(P, UV, eps_q=eps, return_edges=True)
    c0b[str(eps)] = dict(patches=int(pid_e.max() + 1), continuous_edge_frac=round(st["continuous"] / st["interior_edges"], 4))
print(f"  global decomposition vs uv tolerance (quanta): {c0b}")
c0["tolerance_sensitivity"] = c0b
res["C0"] = c0

# ---- global decomposition (the census's own) -------------------------------------------------------
pid = C.patches(P, UV, eps_q=0.5)
npatch = pid.max() + 1
psize = np.bincount(pid, minlength=npatch)


def patch_fit(p):
    tris = np.nonzero(pid == p)[0]
    Pp = P[tris].reshape(-1, 3)
    Tp = T[tris].reshape(-1, 2)
    f = C.fit_patch(Pp, Tp)
    ext = Tp.max(0) - Tp.min(0)
    f.update(n=len(tris), ext_u=float(ext[0]), ext_v=float(ext[1]),
             plan_ext=float(np.ptp(Pp[:, [0, 2]], axis=0).max()))
    return f


def describe(name, tris):
    tris = np.asarray(tris)
    ps = sorted(set(pid[tris].tolist()))
    sz = Counter(pid[tris].tolist())
    fits = [patch_fit(p) for p in ps if psize[p] >= 2]
    full = sum(1 for p in ps if psize[p] == sz[p])
    def pct(key, q):
        a = [f[key] for f in fits]
        return round(float(np.percentile(a, q)), 1) if a else None
    out = dict(tris=len(tris), patches=len(ps), patches_wholly_inside=full,
               size_top=sorted(sz.values(), reverse=True)[:15],
               ext_u_p50=pct("ext_u", 50), ext_u_p90=pct("ext_u", 90),
               ext_v_p50=pct("ext_v", 50), ext_v_p90=pct("ext_v", 90),
               plan_max_p50=pct("plan_max", 50), plan_max_p90=pct("plan_max", 90),
               a3_max_p50=pct("a3_max", 50), a3_max_p90=pct("a3_max", 90),
               wall_max_p50=pct("wall_max", 50), wall_max_p90=pct("wall_max", 90))
    print(f"  {name}: " + json.dumps(out))
    return out, fits


print("\n== C1/C2 known cases (global decomposition, eps 0.5 quanta)")
# C1: lowland grass mains (15,15) topo 0 -- the quantization floor of an exactly affine chart
grass = np.nonzero(blockmask(15, 15) & (TOPO == 0))[0]
res["grass_15_15"], gf = describe("grass mains (15,15) topo0", grass)
# the floor: residual of per-patch PLAN fit on 2-tri cells
floor = [f["plan_max"] for f in gf]
res["quant_floor_px"] = dict(p50=float(np.percentile(floor, 50)), p90=float(np.percentile(floor, 90)),
                             p99=float(np.percentile(floor, 99)), max=float(np.max(floor)))
print(f"  -> plan-affine residual floor (px): {res['quant_floor_px']}")

# (14,13) reference rock wall: the largest plateau-attached topo-49 component in the block
PLATEAU = {10, 11, 12}
comps = comps_by_edges(blockmask(14, 13), {49})
print(f"  (14,13) topo49 components: {[len(c) for c in comps[:6]]}")
wall = comps[0]
res["rockwall_14_13"], wf = describe(f"rock wall (14,13) comp {len(wall)} tris", wall)
# tile quantization: which 128px tiles does each wall patch touch?
ntiles = []
for p in sorted(set(pid[np.array(wall)].tolist())):
    tr = np.nonzero(pid == p)[0]
    Tc = T[tr].mean(axis=1)
    cells = {(int(u // 128), int(v // 128)) for u, v in T[tr].reshape(-1, 2) - 1e-6}
    ntiles.append(len(cells))
res["rockwall_14_13"]["tiles_touched_per_patch"] = dict(Counter(ntiles))
print(f"     128px tiles touched per patch: {dict(sorted(Counter(ntiles).items()))}")

# (15,15) canopy blob
canopy = comps_by_edges(blockmask(15, 15), {36, 37})
print(f"  (15,15) forest components: {[len(c) for c in canopy[:4]]}")
res["canopy_15_15"], cf = describe(f"canopy (15,15) comp {len(canopy[0])} tris", canopy[0])
big = [f for f in cf if f["n"] >= 6]
print("     canopy patches >=6 tris (n, plan_max, a3_max, wall_max, ext):")
for f in sorted(big, key=lambda f: -f["n"]):
    print(f"       n={f['n']:3d} plan={f['plan_max']:7.1f} a3={f['a3_max']:7.1f} wall={f['wall_max']:7.1f} "
          f"ext=({f['ext_u']:.0f},{f['ext_v']:.0f}) planext={f['plan_ext']:.1f}")
res["canopy_15_15"]["big_patches"] = [{k: (round(v, 1) if isinstance(v, float) else v) for k, v in f.items()}
                                      for f in big]
print("     rock-wall patches >=4 tris (n, plan_max, a3_max, a3_elev, wall_max, ext):")
for f in sorted([f for f in wf if f["n"] >= 4], key=lambda f: -f["n"])[:20]:
    print(f"       n={f['n']:3d} plan={f['plan_max']:7.1f} a3={f['a3_max']:6.1f} elev={f['a3_elev']:5.1f} "
          f"wall={f['wall_max']:6.1f} ext=({f['ext_u']:.0f},{f['ext_v']:.0f}) planext={f['plan_ext']:.1f}")

(C.OUT / "calibration.json").write_text(json.dumps(res, indent=1))
print(f"\nwrote {C.OUT / 'calibration.json'}")


# ======================================================================================================
# C3  THE CLASSIFIER ON THE KNOWN CASES (same function the census uses, uvc_classify.classify @ TAU 8)
# ======================================================================================================
import uvc_classify as K  # noqa: E402

cls_npz = np.load(C.OUT / "classes_terrain.npz")
tri_sub = cls_npz["sub"]
print("\n== C3 classifier verdicts on the known cases (area-weighted sub-class %)")
_, area_all = C.tri_normals(P)


def verdict(name, tris):
    tris = np.asarray(tris)
    a = area_all[tris]
    out = {}
    for s in K.SUBS:
        v = float(a[tri_sub[tris] == s].sum() / a.sum() * 100)
        if v > 0.05:
            out[s] = round(v, 1)
    print(f"  {name}: {out}")
    return out


res["C3"] = dict(grass_15_15=verdict("grass mains (15,15) topo0", grass),
                 rockwall_14_13=verdict("rock wall (14,13) 464-tri comp", wall),
                 canopy_15_15=verdict("canopy (15,15)", canopy[0]),
                 uaho_0_0=verdict("uaho (0,0) mountain comp", uaho))

# ======================================================================================================
# C4  SYNTHETIC CONTROLS -- each class must be RECOVERED, and a broken chart must FAIL (a check that can fail)
# ======================================================================================================
rng = np.random.default_rng(7)


def quant(Tpx):
    """stock quantization: uv to 1/1024 -> px steps of 2 (u) and 4 (v)."""
    return np.stack([np.round(Tpx[..., 0] / 2) * 2, np.round(Tpx[..., 1] / 4) * 4], axis=-1)


def grid_tris(X, Y, Z):
    """(r,c) vertex grids -> tri corner array (k,3,3)."""
    tris = []
    for i in range(X.shape[0] - 1):
        for j in range(X.shape[1] - 1):
            a = (X[i, j], Y[i, j], Z[i, j]); b = (X[i, j + 1], Y[i, j + 1], Z[i, j + 1])
            c = (X[i + 1, j], Y[i + 1, j], Z[i + 1, j]); d = (X[i + 1, j + 1], Y[i + 1, j + 1], Z[i + 1, j + 1])
            tris += [(a, b, d), (a, d, c)]
    return np.array(tris, dtype=float)


def synth(name, Ptr, Tfun, expect, reuse=50.0, decoded=None):
    Ttr = quant(Tfun(Ptr))
    row = C.patch_features(Ptr, Ttr)
    row["reuse_far"] = reuse
    row["decoded"] = decoded
    got = K.classify(row)
    ok = got[1] == expect if "." in expect else got[0] == expect
    print(f"  {'PASS' if ok else 'FAIL'} {name}: expect {expect} got {got}  "
          f"(plan {row.get('plan_max', float('nan')):.1f} wall {row.get('wall_max', float('nan')):.1f} "
          f"arc {row.get('arc_max', float('nan')):.1f} a3 {row.get('a3_max', float('nan')):.1f} "
          f"kappa {row.get('kappa', float('nan')):.2f})")
    return dict(expect=expect, got=list(got), ok=bool(ok))


print("\n== C4 synthetic controls")
c4 = {}
gx, gz = np.meshgrid(np.arange(0, 24.1, 4.0), np.arange(0, 24.1, 4.0))
dome = 5.0 * np.exp(-((gx - 12) ** 2 + (gz - 12) ** 2) / 60.0)
hill = grid_tris(gx, dome, -gz)
plan_fn = lambda Pt: np.stack([100 + 31 * Pt[..., 0], 3000 - 31 * Pt[..., 2]], axis=-1)
c4["S1_plan_hill"] = synth("S1 plan-projected uv on a 5u dome (24u chart)", hill, plan_fn, "P.chart")
warp_fn = lambda Pt: plan_fn(Pt) + np.stack([20 * np.sin(Pt[..., 0] / 3.0), 20 * np.cos(Pt[..., 2] / 3.0)], -1)
c4["S2_warped_hill"] = synth("S2 same dome, uv + 20px sinusoid warp", hill, warp_fn, "M")
# zigzag wall: vertical facets whose facing swings +-25 deg, uv = straight horizontal projection (s along x, y)
xs = np.arange(0, 25, 4.0)
zz = np.where(np.arange(len(xs)) % 2 == 0, 0.0, 1.8)
WX, WY = np.meshgrid(xs, np.arange(0, 12.1, 4.0))
WZ = np.tile(zz, (WY.shape[0], 1))
zig = grid_tris(WX, WY, -WZ)
c4["S3_wall_proj"] = synth("S3 zigzag wall, straight horizontal projection uv=(31x, 31y)", zig,
                           lambda Pt: np.stack([100 + 31 * Pt[..., 0], 3000 - 31 * Pt[..., 1]], -1), "W.proj")
# curved wall: cylinder r=12, 140 deg of arc, uv = (31*arclength, 31*y) -- curved enough that NO straight
# horizontal projection fits (the arc model must be what recovers it)
th_ = np.radians(np.arange(0, 140.1, 10.0))
CX, CY = np.meshgrid(12 * np.cos(th_), np.arange(0, 12.1, 4.0))
CZ = np.tile(12 * np.sin(th_), (CY.shape[0], 1))
cyl = grid_tris(CX, CY, CZ)


def arc_fn(Pt):
    s = 12 * np.arctan2(Pt[..., 2], Pt[..., 0])
    return np.stack([100 + 31 * s, 3000 - 31 * Pt[..., 1]], -1)


c4["S4_wall_arc"] = synth("S4 curved wall r12/140deg, arclength-unrolled uv", cyl, arc_fn, "W.arc")
# keyed coastal course: columns 4.0-6.2u wide, faces 2.2-5.9u tall, uv = one 128px tile per column, v base/top
cw = np.concatenate([[0], np.cumsum(rng.uniform(4.0, 6.2, 6))])
ht = rng.uniform(2.2, 5.9, len(cw))
tris, uvs = [], []
for i in range(len(cw) - 1):
    a = (cw[i], 0, 0); b = (cw[i + 1], 0, 0); c_ = (cw[i] + 0.3, ht[i], 0.0); d_ = (cw[i + 1] + 0.3, ht[i + 1], 0.0)
    ua, ub = 1384 - 128 * i, 1384 - 128 * (i + 1)
    tris += [(a, b, d_), (a, d_, c_)]
    uvs += [((ua, 3696), (ub, 3696), (ub, 3572)), ((ua, 3696), (ub, 3572), (ua, 3572))]
key = np.array(tris, float)
key[..., 2] = -0.2 * key[..., 0] ** 1.3 / 3                 # a gently bending shore so straight projection fails
uvk = np.array(uvs, float)
c4["S5_wall_keyed"] = synth("S5 keyed coastal course (1 tile/column, v base/top)", key, lambda Pt: uvk, "W.keyed")
# a 2-tri mains cell (plan-affine in-cell), reused art, decoded / undecoded
cell = grid_tris(np.array([[0, 4.0], [0, 4.0]]), np.zeros((2, 2)), -np.array([[0, 0], [4.0, 4.0]]))
mains = lambda Pt: np.stack([8 + 31 * Pt[..., 0], 3148 - 31 * Pt[..., 2]], -1)
c4["S6_tile_rule"] = synth("S6 mains cell, reused + decoded", cell, mains, "L.rule", decoded="mains:grass")
c4["S7_tile_free"] = synth("S7 same cell, reused, undecoded art", cell, mains, "L.free", decoded=None)
c4["S8_tile_unique"] = synth("S8 same cell, UNIQUE art (reuse_far 0)", cell, mains, "P.unique", reuse=0.0)
res["C4_synthetic"] = c4
n_ok = sum(v["ok"] for v in c4.values())
print(f"  synthetic controls: {n_ok}/{len(c4)} recovered")
(C.OUT / "calibration.json").write_text(json.dumps(res, indent=1))
print(f"wrote {C.OUT / 'calibration.json'}")
