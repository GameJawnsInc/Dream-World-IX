"""VERIFY (adversarial) -- UV-14: does Uaho's 9-patch decomposition hold at EVERY tolerance (C0 only ran 1.536 q)?
And: does a synthetic control that mixes keyed one-tile quads with non-tile tris in ONE continuous patch (the stock
(14,13) reality) come out W.keyed? (C4's S5 is a pure keyed course, so it cannot exercise the per-patch kappa
dilution.) Read-only."""
import json
from collections import Counter, defaultdict
import numpy as np
import uvc_common as C
import uvc_classify as K

d = C.load(1, "terrain")
P, UV, T, TOPO, BLK = d["P"], d["UV"], d["T"], d["TOPO"], d["BLK"]
idx = np.nonzero((BLK[:, 0] == 0) & (BLK[:, 1] == 0) & np.isin(TOPO, [49, 7, 62]))[0]
# largest edge-connected comp (as uvc_calibrate.comps_by_edges)
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
    seen |= comp; comps.append(sorted(comp))
uaho = np.array(max(comps, key=len))
out = {"uaho_tris": int(len(uaho))}
for eps in (0.25, 0.5, 1.0, 1.536, 3.0, 6.0):
    m = np.zeros(len(P), bool); m[uaho] = True
    pid = C.patches(P, UV, mask=m, eps_q=eps)
    out[f"uaho_sizes_eps{eps}"] = sorted(Counter(pid[uaho].tolist()).values(), reverse=True)

# mixed synthetic: a 6x3 grid of wall quads, irregular sizes; uv = one 128px tile per quad laid CONTINUOUSLY
# (atlas-adjacent), but 30% of quads get a projected (density-constant) window instead -> still continuous where
# windows meet? We keep continuity by building the uv per VERTEX: keyed verts on the lattice, then perturb a
# fraction of interior verts to their projected position (the non-tile tris stock carries).
rng = np.random.default_rng(11)
nx, ny = 7, 4
xs = np.concatenate([[0], np.cumsum(rng.uniform(3.6, 5.6, nx - 1))])
ys = np.concatenate([[0], np.cumsum(rng.uniform(3.2, 5.2, ny - 1))])
X_, Y_ = np.meshgrid(xs, ys)
Z_ = -0.15 * X_ ** 1.2
Uk = 1000 + 128 * np.arange(nx)[None, :] + 0 * Y_          # keyed: lattice per vertex role
Vk = 3700 - 128 * np.arange(ny)[:, None] + 0 * X_
res = {}
for frac in (0.0, 0.2, 0.4):
    U = Uk.astype(float).copy(); V = Vk.astype(float).copy()
    inner = [(i, j) for i in range(1, ny - 1) for j in range(1, nx - 1)]
    pick = rng.choice(len(inner), int(round(frac * len(inner))), replace=False) if frac else []
    for p in pick:
        i, j = inner[p]
        U[i, j] = 1000 + 31 * X_[i, j]; V[i, j] = 3700 - 31 * Y_[i, j]   # projected position for this vertex
    tris, uvs = [], []
    for i in range(ny - 1):
        for j in range(nx - 1):
            a, b, c_, e = (i, j), (i, j + 1), (i + 1, j), (i + 1, j + 1)
            for tri in ((a, b, e), (a, e, c_)):
                tris.append([(X_[q], Y_[q], Z_[q]) for q in tri])
                uvs.append([(U[q], V[q]) for q in tri])
    Ptr, Ttr = np.array(tris, float), np.array(uvs, float)
    row = C.patch_features(Ptr, Ttr)
    row["reuse_far"] = 50.0; row["decoded"] = None
    res[str(frac)] = dict(got=list(K.classify(row)), kappa=round(row.get("kappa", float("nan")), 3),
                          flow_spread=round(row.get("flow_spread", float("nan")), 1))
out["mixed_keyed_controls"] = res
print(json.dumps(out, indent=1))
(C.OUT / "verify_calib.json").write_text(json.dumps(out, indent=1))
