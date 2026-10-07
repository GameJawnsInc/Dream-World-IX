"""VERIFY -- UV-04: uvc_deform's 'plan texel stretch p5-p95 0.81-1.41' pools ALL L sub-classes (8,562 off-lattice
cells); recompute for L.rule only (the 5,282 cells the claim cites) and for interior-only L.rule cells. Read-only."""
import json, math
from collections import defaultdict
import numpy as np
import uvc_common as C

d = C.load(1, "terrain"); P, T = d["P"], d["T"]
pid = np.load(C.OUT / "features_terrain.npz")["pid"]
sub = np.load(C.OUT / "classes_terrain.npz")["sub"]
_, sv, Jp = C.tri_jacobian(P, T)
_, area = C.tri_normals(P)
inc = defaultdict(set)
for t in range(len(P)):
    for k in range(3):
        inc[C.poskey(P[t, k])].add(str(sub[t]))
groups = defaultdict(list)
for t in np.nonzero((sub == "L.rule") & (area > 0.05))[0]:
    groups[(int(pid[t]), math.floor(P[t, :, 0].mean() / 4), math.floor(P[t, :, 2].mean() / 4))].append(t)
st_all, st_int = [], []
for (p, ci, cj), ts in groups.items():
    if len(ts) != 2:
        continue
    pts = {}
    for t in ts:
        for k in range(3):
            pts.setdefault(C.poskey(P[t, k]), (P[t, k], T[t, k]))
    if len(pts) != 4:
        continue
    Pp = np.array([v[0] for v in pts.values()]); Tp = np.array([v[1] for v in pts.values()])
    us, vs = np.unique(np.round(Tp[:, 0])), np.unique(np.round(Tp[:, 1]))
    if len(us) != 2 or len(vs) != 2 or np.ptp(us) < 60 or np.ptp(vs) < 60:
        continue
    lat = np.array([[4 * ci, 4 * cj], [4 * ci + 4, 4 * cj], [4 * ci, 4 * cj + 4], [4 * ci + 4, 4 * cj + 4]], float)
    dmin = np.array([np.min(np.linalg.norm(lat - q, axis=1)) for q in Pp[:, [0, 2]]])
    if dmin.max() < 0.02:
        continue
    interior = all(inc[k] <= {"L.rule"} for k in pts)
    for t in ts:
        if np.all(np.isfinite(Jp[t])):
            s = np.linalg.svd(Jp[t], compute_uv=False) / 31.0
            st_all += list(s)
            if interior:
                st_int += list(s)
out = dict(Lrule_offlattice_stretch_p1_5_50_95_99=[round(float(x), 3) for x in np.percentile(st_all, [1, 5, 50, 95, 99])],
           Lrule_interior_offlattice_stretch_p1_5_50_95_99=[round(float(x), 3) for x in np.percentile(st_int, [1, 5, 50, 95, 99])])
print(json.dumps(out, indent=1))
(C.OUT / "verify_cornerpin_stretch.json").write_text(json.dumps(out, indent=1))
