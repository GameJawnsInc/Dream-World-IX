"""uvclass PROBE -- what IS a chart, concretely? (feeds the classifier design; numbers cited in NOTES.md)

For the three calibration cases, per edge-continuous patch:
  * do individual TRIS cross a 128px tile line (the Moguri-gutter question) or do patches only TOUCH tile lines?
  * per-tri local frame: t_h = horizontal in-plane tangent (contour), t_up = in-plane uphill.
    g_h = |J.t_h| px/u along contour, g_up = |J.t_up| px/u up the surface, and the texture DIRECTION of each
    (angle in texel space). A plan projection gives g_up/g_h = cos(slope) (texture does not climb); a surface
    unroll gives a slope-independent ratio; a wall projection gives g_h ~ |cos(facing - d)|.
  * the (arclength-along-contour, height) model: does T fit affine in (s_arc, y) when s_arc is the
    patch's own contour arclength? (fit on the patch's distinct verts, s by projecting onto the patch's
    principal horizontal polyline).
Rerun: py studies/terrain-malleability/uvclass/uvc_probe_charts.py
"""
import json
import math
from collections import Counter, defaultdict

import numpy as np

import uvc_common as C

d = C.load(1, "terrain")
P, UV, T, TOPO, BLK = d["P"], d["UV"], d["T"], d["TOPO"], d["BLK"]
pid = C.patches(P, UV, eps_q=0.5)
J, sv, Jp = C.tri_jacobian(P, T)
nn, area = C.tri_normals(P)
up = np.array([0.0, 1.0, 0.0])
th = np.cross(nn, up)
thn = np.linalg.norm(th, axis=1)
th = th / np.where(thn[:, None] > 1e-9, thn[:, None], 1)
tup = up[None, :] - (nn @ up)[:, None] * nn
tup = tup / np.maximum(np.linalg.norm(tup, axis=1)[:, None], 1e-9)
gh = np.einsum("nij,nj->ni", J, th)
gu = np.einsum("nij,nj->ni", J, tup)
slope = C.slope_deg(P)


def tri_crosses_tile(t):
    us, vs = T[t, :, 0], T[t, :, 1]
    return (math.floor(us.min() / 128 + 1e-6) != math.floor(us.max() / 128 - 1e-6) or
            math.floor(vs.min() / 128 + 1e-6) != math.floor(vs.max() / 128 - 1e-6))


def report(name, tris):
    tris = np.asarray(tris)
    cross = np.array([tri_crosses_tile(t) for t in tris])
    gh_m = np.linalg.norm(gh[tris], axis=1)
    gu_m = np.linalg.norm(gu[tris], axis=1)
    ok = thn[tris] > 1e-6
    ratio = gu_m[ok] / np.maximum(gh_m[ok], 1e-9)
    cosl = np.cos(np.radians(slope[tris][ok]))
    out = dict(tris=int(len(tris)), tris_crossing_128px_tile_line=float(cross.mean()),
               slope_p50=float(np.median(slope[tris])),
               g_h_p50=float(np.median(gh_m)), g_up_p50=float(np.median(gu_m)),
               ratio_up_over_h_p50=float(np.median(ratio)) if len(ratio) else None,
               cos_slope_p50=float(np.median(cosl)) if len(cosl) else None,
               corr_ratio_cosslope=float(np.corrcoef(ratio, cosl)[0, 1]) if len(ratio) > 3 and np.std(cosl) > 1e-6 else None)
    # texture direction of the contour gradient: angle in texel space (0 = +u, 90 = +v)
    ang_h = np.degrees(np.arctan2(gh[tris][ok, 1], gh[tris][ok, 0])) % 180
    ang_u = np.degrees(np.arctan2(gu[tris][ok, 1], gu[tris][ok, 0])) % 180
    out["contour_tex_axis_hist"] = dict(Counter((np.round(ang_h / 15) * 15 % 180).astype(int).tolist()).most_common(6))
    out["uphill_tex_axis_hist"] = dict(Counter((np.round(ang_u / 15) * 15 % 180).astype(int).tolist()).most_common(6))
    print(f"\n{name}: " + json.dumps(out))
    return out


res = {}
blockmask = lambda bx, by: (BLK[:, 0] == bx) & (BLK[:, 1] == by)
grass = np.nonzero(blockmask(15, 15) & (TOPO == 0))[0]
res["grass_15_15"] = report("grass (15,15) topo0", grass)
# a broader steep-grass check: the plan law predicts ratio = cos(slope)
g_all = np.nonzero(np.isin(TOPO, [0, 1, 2, 3, 42]) & (slope > 15))[0]
res["grass_steep_mapwide"] = report("grass map-wide slope>15", g_all)

# (14,13) wall component (largest edge-connected topo49 comp in the block)
w = np.nonzero(blockmask(14, 13) & (TOPO == 49))[0]
res["rock_14_13_all49"] = report("rock (14,13) all topo49", w)
canopy = np.nonzero(blockmask(15, 15) & np.isin(TOPO, [36, 37]))[0]
res["canopy_15_15"] = report("canopy (15,15)", canopy)
uaho = np.nonzero(blockmask(0, 0) & (TOPO == 49))[0]
res["uaho_0_0"] = report("uaho (0,0) topo49", uaho)

# ---- the (arclength, height) model on the big (14,13) wall patches -----------------------------------
print("\n(14,13) wall patches: residual (px) of affine fits on DISTINCT verts: plan / a3 / wall(best az) / "
      "arc(s_arc,y) / arcq(s_arc,y + y^2,s*y)")
wp = Counter(pid[w].tolist())
rows = []
for p, n in wp.most_common(12):
    tr = np.nonzero(pid == p)[0]
    pts = {}
    for t in tr:
        for k in range(3):
            pts.setdefault(C.poskey(P[t, k]), (P[t, k], T[t, k]))
    Pp = np.array([v[0] for v in pts.values()])
    Tp = np.array([v[1] for v in pts.values()])
    f = C.fit_patch(Pp, Tp)
    # arclength: order verts along the patch's principal horizontal direction, then use a smoothed
    # polyline of the plan footprint -- here simply: s = distance along a PCA-fitted QUADRATIC plan curve
    xz = Pp[:, [0, 2]]
    c0 = xz.mean(0)
    _, _, vt = np.linalg.svd(xz - c0)
    a_ax, b_ax = vt[0], vt[1]
    pa = (xz - c0) @ a_ax
    pb = (xz - c0) @ b_ax
    cq = np.polyfit(pa, pb, 2)
    # arclength along the quadratic curve from min(pa)
    grid = np.linspace(pa.min(), pa.max(), 400)
    deriv = np.polyval(np.polyder(cq), grid)
    seg = np.sqrt(1 + deriv ** 2)
    cum = np.concatenate([[0], np.cumsum((seg[1:] + seg[:-1]) / 2 * np.diff(grid))])
    s_arc = np.interp(pa, grid, cum)
    one = np.ones(len(Pp))
    _, r_arc = C._lsq_res(np.column_stack([s_arc, Pp[:, 1], one]), Tp)
    _, r_arcq = C._lsq_res(np.column_stack([s_arc, Pp[:, 1], one, s_arc * Pp[:, 1], Pp[:, 1] ** 2, s_arc ** 2]), Tp)
    row = dict(n=n, m=len(Pp), plan=round(f["plan_max"], 1), a3=round(f["a3_max"], 1), elev=round(f["a3_elev"], 1),
               wall=round(f["wall_max"], 1), arc=round(float(r_arc.max()), 1), arcq=round(float(r_arcq.max()), 1),
               ext=[round(float(x)) for x in np.ptp(Tp, axis=0)], yspan=round(float(np.ptp(Pp[:, 1])), 1),
               bend=round(float(abs(cq[0]) * (np.ptp(pa) ** 2) / 4), 2))
    rows.append(row)
    print("  ", row)
res["wall_14_13_patch_models"] = rows
(C.OUT / "probe_charts.json").write_text(json.dumps(res, indent=1))
