"""VERIFY (adversarial) -- UV-11 / R3: is the (14,13) rock wall a per-quad tile language or a band sweep?

R3 counts 'continuous edges joining two different 128px tiles' and 'tiles spanned per patch' on a PHASE-0 128px
grid (T // 128). The recorded decode (interior KB, rock_wall_language.py) says the rock tile grid has a LEARNED
phase (u dual-phase, v 64/80 px). A single 128px tile at a non-zero phase straddles up to 4 phase-0 cells, so the
phase-0 counts can be inflated. This script measures the same quantities phase-invariantly and runs the direct
'one 128x128 tile per quad' test.

Read-only. Rerun: py verify_rockwall.py   (needs the uvc cache)
"""
import json
import math
from collections import Counter, defaultdict

import numpy as np

import uvc_common as C

d = C.load(1, "terrain")
P, UV, T, TOPO, BLK = d["P"], d["UV"], d["T"], d["TOPO"], d["BLK"]
bm = (BLK[:, 0] == 14) & (BLK[:, 1] == 13)
idx = np.nonzero(bm & (TOPO == 49))[0]
out = {"wall_tris_all_topo49": int(len(idx))}

# ---- best global phase (u, v) for vertex uvs on a 128px lattice ----
V = T[idx].reshape(-1, 2)


def onlat(vals, ph, tol=6.0):
    r = np.abs(((vals - ph + 64) % 128) - 64)
    return float((r <= tol).mean())


best_u = max(((onlat(V[:, 0], ph), ph) for ph in np.arange(0, 128, 2.0)))
best_v = max(((onlat(V[:, 1], ph), ph) for ph in np.arange(0, 128, 4.0)))
out["best_phase_u"] = dict(frac=round(best_u[0], 3), phase=best_u[1])
out["best_phase_v"] = dict(frac=round(best_v[0], 3), phase=best_v[1])
out["phase0_frac_u_v"] = [round(onlat(V[:, 0], 0), 3), round(onlat(V[:, 1], 0), 3)]
# chance level for this many verts: shuffle-free estimate = best phase on uniformly random values
rng = np.random.default_rng(0)
rnd = rng.uniform(0, 4096, len(V))
out["chance_best_phase_frac"] = round(max(onlat(rnd, ph) for ph in np.arange(0, 128, 2.0)), 3)

# ---- edges ----
edges = defaultdict(list)
for t in idx:
    ks = [C.poskey(P[t, k]) for k in range(3)]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        ka, kb = ks[a], ks[b]
        edges[(ka, kb) if ka <= kb else (kb, ka)].append((t, a, b) if ka <= kb else (t, b, a))


def tile_of(t, pu, pv):
    c = T[t].mean(0)
    return (int((c[0] - pu) // 128), int((c[1] - pv) // 128))


n_int = n_cont = 0
cont_pairs = []
for e, lst in edges.items():
    if len(lst) != 2:
        continue
    (t1, a1, b1), (t2, a2, b2) = lst
    n_int += 1
    dmax = max(abs(UV[t1, a1, 0] - UV[t2, a2, 0]), abs(UV[t1, a1, 1] - UV[t2, a2, 1]),
               abs(UV[t1, b1, 0] - UV[t2, b2, 0]), abs(UV[t1, b1, 1] - UV[t2, b2, 1]))
    if dmax <= 0.5 / 1024:
        n_cont += 1
        cont_pairs.append((t1, t2))
out["interior_edges"] = n_int
out["uv_continuous_pct"] = round(100 * n_cont / n_int, 1)
cross = {}
for name, (pu, pv) in (("phase0", (0, 0)), ("best_global_phase", (best_u[1], best_v[1]))):
    cross[name] = round(100 * float(np.mean([tile_of(a, pu, pv) != tile_of(b, pu, pv) for a, b in cont_pairs])), 1)
# min over ALL phases (most generous to 'same tile')
mins = 101.0
for pu in np.arange(0, 128, 8.0):
    for pv in np.arange(0, 128, 8.0):
        x = 100 * float(np.mean([tile_of(a, pu, pv) != tile_of(b, pu, pv) for a, b in cont_pairs]))
        mins = min(mins, x)
cross["min_over_phases"] = round(mins, 1)
out["continuous_edges_joining_two_tiles_pct"] = cross

# ---- patches: phase-invariant span ----
m = np.zeros(len(P), bool)
m[idx] = True
pid = C.patches(P, UV, mask=m, eps_q=0.5)
sizes = Counter(pid[idx].tolist())
rows = []
for p, n in sizes.items():
    tr = np.nonzero(pid == p)[0]
    ext = np.ptp(T[tr].reshape(-1, 2), axis=0)
    # minimal number of distinct centroid tiles over phases
    cen = T[tr].mean(1)
    mn = min(len({(int((c[0] - pu) // 128), int((c[1] - pv) // 128)) for c in cen})
             for pu in np.arange(0, 128, 8.0) for pv in np.arange(0, 128, 8.0))
    rows.append(dict(n=n, ext_u=float(ext[0]), ext_v=float(ext[1]), min_tiles=mn))
tot = len(idx)
out["patches"] = len(rows)
out["tris_in_patches_min_tiles_ge4_pct"] = round(100 * sum(r["n"] for r in rows if r["min_tiles"] >= 4) / tot, 1)
out["tris_in_patches_ext_gt_140px_pct"] = round(100 * sum(r["n"] for r in rows if max(r["ext_u"], r["ext_v"]) > 140) / tot, 1)

# ---- direct test: ONE 128x128 tile per QUAD ----
# pair each tri with a uv-continuous neighbour whose union has exactly 4 distinct verts (a quad); greedy by
# longest shared edge (the diagonal of a quad is its longest edge).
nb = defaultdict(list)
for a, b in cont_pairs:
    nb[a].append(b)
    nb[b].append(a)
used, quads = set(), []
cand = []
for a, b in cont_pairs:
    ka = {C.poskey(P[a, k]) for k in range(3)}
    kb = {C.poskey(P[b, k]) for k in range(3)}
    shared = list(ka & kb)
    if len(ka | kb) != 4 or len(shared) != 2:
        continue
    L = np.linalg.norm(np.array(shared[0], float) - np.array(shared[1], float)) / 256
    cand.append((-L, a, b))
for _, a, b in sorted(cand):
    if a in used or b in used:
        continue
    used.update((a, b))
    quads.append((a, b))
qext, qgeo = [], []
for a, b in quads:
    Tq = np.concatenate([T[a], T[b]])
    Pq = np.concatenate([P[a], P[b]])
    qext.append(np.ptp(Tq, axis=0))
    _, ar = C.tri_normals(np.stack([P[a], P[b]]))
    qgeo.append(math.sqrt(ar.sum()))
qext = np.array(qext)
qgeo = np.array(qgeo)
is_tile = (np.abs(qext[:, 0] - 128) <= 8) & (np.abs(qext[:, 1] - 128) <= 8)
out["quads"] = dict(n_quads=len(quads), tris_in_quads_pct=round(100 * 2 * len(quads) / tot, 1),
                    quad_uv_ext_u_p10_50_90=[round(float(x)) for x in np.percentile(qext[:, 0], [10, 50, 90])],
                    quad_uv_ext_v_p10_50_90=[round(float(x)) for x in np.percentile(qext[:, 1], [10, 50, 90])],
                    quads_exactly_one_128px_tile_pct=round(100 * float(is_tile.mean()), 1),
                    quad_geo_size_u_p10_50_90=[round(float(x), 2) for x in np.percentile(qgeo, [10, 50, 90])],
                    corr_quad_uv_area_vs_geo_area=round(float(np.corrcoef(np.log(qext[:, 0] * qext[:, 1] + 1),
                                                                         np.log(qgeo ** 2))[0, 1]), 3))
# vertex uvs of 'tile' quads on the learned lattice?
# ---- kappa of the wall's patches (uniform tri size -> undetermined) ----
z = np.load(C.OUT / "features_terrain.npz")
cols = list(z["cols"])
F = z["F"]
gp = z["pid"]
cls = np.load(C.OUT / "classes_terrain.npz")
sub = cls["sub"]
kap = F[:, cols.index("kappa")]
wall_p = sorted(set(gp[idx].tolist()))
mf = [p for p in wall_p if (sub[gp == p][0] == "M.flow")]
out["wall_Mflow_patches"] = len(mf)
out["wall_Mflow_patches_kappa_nan"] = int(sum(np.isnan(kap[p]) for p in mf))
out["wall_Mflow_kappa_values"] = [round(float(kap[p]), 2) for p in mf]
print(json.dumps(out, indent=1))
(C.OUT / "verify_rockwall.json").write_text(json.dumps(out, indent=1))
