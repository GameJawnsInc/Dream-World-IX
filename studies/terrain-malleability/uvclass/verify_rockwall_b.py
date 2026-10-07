"""VERIFY (adversarial) -- UV-11 follow-up: per-tri UV area + per-quad corner structure on the (14,13) wall.
If quads are exact 128px tiles keyed to vertex roles, each tri's UV area is half a tile (8192 px^2) and the quad's
4 uv corners form an axis-aligned rect with corners on the learned (u 8, v 64) lattice. Read-only."""
import json
import numpy as np
import uvc_common as C

d = C.load(1, "terrain")
P, T, TOPO, BLK = d["P"], d["T"], d["TOPO"], d["BLK"]
idx = np.nonzero((BLK[:, 0] == 14) & (BLK[:, 1] == 13) & (TOPO == 49))[0]
Tt = T[idx]
uva = 0.5 * np.abs((Tt[:, 1, 0] - Tt[:, 0, 0]) * (Tt[:, 2, 1] - Tt[:, 0, 1]) - (Tt[:, 2, 0] - Tt[:, 0, 0]) * (Tt[:, 1, 1] - Tt[:, 0, 1]))
_, ga = C.tri_normals(P[idx])
half = np.abs(uva - 8192) <= 0.08 * 8192
out = dict(tris=len(idx), uv_area_px2_p10_50_90=[round(float(x)) for x in np.percentile(uva, [10, 50, 90])],
           frac_tris_half_tile_uv_area=round(float(half.mean()), 3))
# tri corners on lattice (u phase 8, v phase 64, tol 6px), both axes, all 3 corners
def lat(x, ph, tol=6):
    return np.abs(((x - ph + 64) % 128) - 64) <= tol
cl = lat(Tt[..., 0], 8) & lat(Tt[..., 1], 64)
out["frac_tris_all3_corners_on_lattice"] = round(float(cl.all(1).mean()), 3)
# axis-aligned right-tri halves of a 128 rect: 2 distinct u, 2 distinct v among the 3 corners, extents 128
def is_rect_half(tt):
    us = np.unique(np.round(tt[:, 0])); vs = np.unique(np.round(tt[:, 1]))
    return len(us) == 2 and len(vs) == 2 and abs(np.ptp(us) - 128) <= 8 and abs(np.ptp(vs) - 128) <= 8
rh = np.array([is_rect_half(t) for t in Tt])
out["frac_tris_axis_aligned_rect_halves_of_128_tile"] = round(float(rh.mean()), 3)
# kappa restricted to rect-half tris vs the rest
dens = np.sqrt(uva / np.maximum(ga, 1e-9))
size = np.sqrt(ga)
for nm, m in (("rect_halves", rh), ("others", ~rh)):
    if m.sum() > 10:
        k = -np.polyfit(np.log(size[m]), np.log(dens[m]), 1)[0]
        out[f"kappa_pooled_{nm}"] = round(float(k), 3)
        out[f"size_std_log_{nm}"] = round(float(np.log(size[m]).std()), 3)
# map-wide: rect-half fraction for topo 49 and lip58 by class
cls = np.load(C.OUT / "classes_terrain.npz")["sub"]
res = {}
for topo in (49, 58):
    mm = np.nonzero(TOPO == topo)[0]
    rhm = np.array([is_rect_half(T[t]) for t in mm])
    _, a = C.tri_normals(P[mm])
    res[str(topo)] = {"area_frac_rect_halves": round(float(a[rhm].sum() / a.sum()), 3)}
    for s in ("M.flow", "W.keyed", "M.free", "W.proj"):
        q = cls[mm] == s
        if q.sum():
            res[str(topo)][s] = dict(tris=int(q.sum()), area_frac_rect_halves=round(float(a[q & rhm].sum() / a[q].sum()), 3))
out["mapwide_rect_halves"] = res
print(json.dumps(out, indent=1))
(C.OUT / "verify_rockwall_b.json").write_text(json.dumps(out, indent=1))
