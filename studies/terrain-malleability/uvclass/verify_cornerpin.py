"""VERIFY (adversarial) -- UV-04 THE CORNER-PIN ENVELOPE.

Claim: 5,282 L.rule two-tri cells carry a FULL tile window on corners moved off the 4u lattice (p90 1.51u), so
per-vertex XZ jitter of ~1.5u with carried uv is stock-normal for mains ground.
Counter-hypotheses tested here:
  H1  the off-lattice cells are mostly whole-quad TRANSLATIONS (no distortion) -> they say nothing about jitter;
  H2  only ONE corner moves (a shore/wall-conforming pin at a boundary), not interior lattice verts;
  H3  the cells sit at a component boundary (next to a wall/lip/water tri), not in open interior ground;
  H4  the 'tile window' is often a partial/half window (>= 60 px admits a 64 px half).
Also re-finds the worked example ((15,15), corner (1018.84,-1003.57), u 8..136 / v 3148..3272).
Read-only. Rerun: py verify_cornerpin.py
"""
import json
import math
from collections import defaultdict

import numpy as np

import uvc_common as C

d = C.load(1, "terrain")
P, T, TOPO = d["P"], d["T"], d["TOPO"]
z = np.load(C.OUT / "features_terrain.npz")
pid = z["pid"]
cls = np.load(C.OUT / "classes_terrain.npz")
tcls, tsub = cls["cls"], cls["sub"]
nn, area = C.tri_normals(P)
ok = area > 0.05
GROUND = set(C.FAMILY["grass"] + C.FAMILY["desert"] + C.FAMILY["plateau"] + C.FAMILY["scrub"] + C.FAMILY["dunes"]
             + C.FAMILY["brush38"] + C.FAMILY["snow"] + C.FAMILY["shelf13"] + C.FAMILY["canyon"])

# vertex -> set of (class, topo-is-ground) of incident tris
inc = defaultdict(set)
for t in range(len(P)):
    for k in range(3):
        inc[C.poskey(P[t, k])].add((str(tsub[t]), int(TOPO[t]) in GROUND))

groups = defaultdict(list)
Lm = (tsub == "L.rule") & ok
for t in np.nonzero(Lm)[0]:
    groups[(int(pid[t]), math.floor(P[t, :, 0].mean() / 4), math.floor(P[t, :, 2].mean() / 4))].append(t)
rows = []
example = None
for (p, ci, cj), ts in groups.items():
    if len(ts) != 2:
        continue
    pts = {}
    for t in ts:
        for k in range(3):
            pts.setdefault(C.poskey(P[t, k]), (P[t, k], T[t, k]))
    if len(pts) != 4:
        continue
    keys = list(pts.keys())
    Pp = np.array([v[0] for v in pts.values()])
    Tp = np.array([v[1] for v in pts.values()])
    us, vs = np.unique(np.round(Tp[:, 0])), np.unique(np.round(Tp[:, 1]))
    if len(us) != 2 or len(vs) != 2 or np.ptp(us) < 60 or np.ptp(vs) < 60:
        continue
    lat = np.array([[4 * ci, 4 * cj], [4 * ci + 4, 4 * cj], [4 * ci, 4 * cj + 4], [4 * ci + 4, 4 * cj + 4]], float)
    # assign each plan corner to its nearest lattice corner; offset vectors
    dv = np.array([lat[np.argmin(np.linalg.norm(lat - q, axis=1))] - q for q in Pp[:, [0, 2]]])
    dmin = np.linalg.norm(dv, axis=1)
    if dmin.max() < 0.02:
        continue
    resid = np.linalg.norm(dv - dv.mean(0), axis=1)
    n_off = int((dmin >= 0.02).sum())
    # boundary: does any corner touch a non-L.rule tri, or a non-ground topo?
    border = any(any((s != "L.rule") or (not g) for (s, g) in inc[k]) for k in keys)
    foreign = any(any(not g for (s, g) in inc[k]) for k in keys)
    rows.append(dict(maxoff=float(dmin.max()), maxresid=float(resid.max()), n_off=n_off, border=border,
                     foreign_topo=foreign, wu=float(np.ptp(us)), wv=float(np.ptp(vs))))
    if example is None:
        for q in Pp:
            if abs(q[0] - 1018.84) < 0.02 and abs(q[2] + 1003.57) < 0.02:
                example = dict(cell=(ci, cj), plan=[[round(float(a), 2) for a in q[[0, 2]]] for q in Pp],
                               u=[float(x) for x in us], v=[float(x) for x in vs])
off = np.array([r["maxoff"] for r in rows])
res = np.array([r["maxresid"] for r in rows])
out = dict(off_lattice_cells=len(rows),
           max_offset_p50_90_99=[round(float(x), 3) for x in np.percentile(off, [50, 90, 99])],
           H1_pure_translation_pct=round(100 * float((res < 0.05).mean()), 1),
           H1_distortion_resid_p50_90_99=[round(float(x), 3) for x in np.percentile(res, [50, 90, 99])],
           H2_n_corners_off_hist={str(k): int(sum(r["n_off"] == k for r in rows)) for k in (1, 2, 3, 4)},
           H3_touches_non_Lrule_or_foreign_pct=round(100 * float(np.mean([r["border"] for r in rows])), 1),
           H3_touches_foreign_topo_pct=round(100 * float(np.mean([r["foreign_topo"] for r in rows])), 1),
           H3_interior_only_offsets_p50_90=[round(float(x), 3) for x in np.percentile(
               [r["maxoff"] for r in rows if not r["border"]] or [np.nan], [50, 90])],
           H3_interior_only_cells=int(sum(not r["border"] for r in rows)),
           H4_window_u_hist={str(int(k)): int(v) for k, v in zip(*np.unique(np.round([r["wu"] for r in rows]), return_counts=True)) if v > 50},
           H4_window_v_hist={str(int(k)): int(v) for k, v in zip(*np.unique(np.round([r["wv"] for r in rows]), return_counts=True)) if v > 50},
           example=example)
print(json.dumps(out, indent=1))
(C.OUT / "verify_cornerpin.json").write_text(json.dumps(out, indent=1))
