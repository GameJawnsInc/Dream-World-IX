"""uvclass PROBE 2 -- is a non-affine steep chart a UNIFORM UNROLL (u per unit contour, v per unit uphill constant
across the patch = the kit's coastal arc-length rule) or a free/varying field? Per tri, the surface jacobian is
expressed in the local frame (t_h = horizontal contour tangent, t_up = in-plane uphill):
        G = [J.t_h , J.t_up]  (2x2, texel px per world unit)
A uniform unroll keeps G CONSTANT over the patch whatever the wall's plan curve does; a plan projection makes the
uphill column shrink with cos(slope); a free mural varies arbitrarily. Also: the 'tile-corner pin' fraction
(vertex uvs on a 128px tile-edge lattice of learned phase, tol 6px) -- keyed walls (coastal rect-halves) pin.
Prints per family (patches with >= 6 tris, slope p50 >= 30): G-variation p50, contour rate p50, uphill rate p50,
pin fraction p50.  Rerun: py studies/terrain-malleability/uvclass/uvc_probe_flow.py
"""
import json
from collections import defaultdict

import numpy as np

import uvc_common as C

d = C.load(1, "terrain")
P, T, TOPO = d["P"], d["T"], d["TOPO"]
z = np.load(C.OUT / "features_terrain.npz")
pid = z["pid"]
J, sv, Jp = C.tri_jacobian(P, T)
nn, area = C.tri_normals(P)
nn = nn * np.sign(nn[:, 1:2] + 1e-12)
up = np.array([0.0, 1.0, 0.0])
th = np.cross(nn, up)
thn = np.linalg.norm(th, axis=1)
th = th / np.where(thn[:, None] > 1e-9, thn[:, None], 1)
tup = up[None, :] - (nn @ up)[:, None] * nn
tup = tup / np.maximum(np.linalg.norm(tup, axis=1)[:, None], 1e-9)
Gh = np.einsum("nij,nj->ni", J, th)
Gu = np.einsum("nij,nj->ni", J, tup)
slope = C.slope_deg(P)


def pin_frac(vals, tol=6.0):
    best = 0.0
    for ph in np.arange(0, 128, 2.0):
        r = np.abs(((vals - ph + 64) % 128) - 64)
        best = max(best, float((r <= tol).mean()))
    return best


members = defaultdict(list)
for t in range(len(P)):
    members[int(pid[t])].append(t)
out = defaultdict(lambda: defaultdict(list))
for p, tr in members.items():
    tr = np.array(tr)
    if len(tr) < 6 or np.median(slope[tr]) < 30:
        continue
    ok = tr[thn[tr] > 1e-3]
    if len(ok) < 6:
        continue
    # sign-align contour direction within the patch (t_h is defined up to the face's facing; align to median)
    g = np.concatenate([Gh[ok], Gu[ok]], axis=1)      # (k,4)
    ref = np.median(g, axis=0)
    flip = (g[:, :2] @ ref[:2]) < 0
    g[flip, :2] *= -1
    gm = np.median(g, axis=0)
    scale = max(np.linalg.norm(gm[:2]), np.linalg.norm(gm[2:]), 1e-6)
    var = float(np.median(np.linalg.norm(g - gm, axis=1)) / scale)
    pts = {}
    for t in tr:
        for k in range(3):
            pts.setdefault(C.poskey(P[t, k]), T[t, k])
    Tp = np.array(list(pts.values()))
    pin = min(pin_frac(Tp[:, 0]), pin_frac(Tp[:, 1]))
    f = C.fam(np.bincount(TOPO[tr]).argmax())
    o = out[f]
    o["G_var"].append(var)
    o["contour_rate"].append(float(np.linalg.norm(gm[:2])))
    o["uphill_rate"].append(float(np.linalg.norm(gm[2:])))
    o["pin"].append(pin)
    o["n"].append(len(tr))
res = {}
print("family   patches  G_var p25/p50/p75   contour px/u p50  uphill px/u p50   pin p50 (frac verts on tile lattice)")
for f, o in sorted(out.items(), key=lambda kv: -len(kv[1]["n"])):
    a = {k: np.array(v) for k, v in o.items()}
    res[f] = {k: [round(float(x), 3) for x in np.percentile(v, [25, 50, 75])] for k, v in a.items()}
    print(f"{f:8s} {len(a['n']):6d}   {np.percentile(a['G_var'], 25):.2f}/{np.median(a['G_var']):.2f}/"
          f"{np.percentile(a['G_var'], 75):.2f}        {np.median(a['contour_rate']):6.1f}          "
          f"{np.median(a['uphill_rate']):6.1f}        {np.median(a['pin']):.2f}")
(C.OUT / "probe_flow.json").write_text(json.dumps(res, indent=1))
