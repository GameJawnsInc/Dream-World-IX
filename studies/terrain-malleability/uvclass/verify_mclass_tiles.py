"""VERIFY (adversarial) -- map-wide: how much of each classifier class is EXACT tile-window rect-halves (128 px
+- 8 both axes, axis-aligned; the coast memory's '(7,17) face tris are rect-HALVES of one tile' structure)?
Also the narrow +-2/+-4 px spike at exactly 128 vs 120/136 controls (non-circular keying evidence). Read-only."""
import json
import numpy as np
import uvc_common as C

d = C.load(1, "terrain")
P, T = d["P"], d["T"]
_, area = C.tri_normals(P)
sub = np.load(C.OUT / "classes_terrain.npz")["sub"]
us = np.round(T[..., 0]); vs = np.round(T[..., 1])
nu = np.array([len(set(r)) for r in us]); nv = np.array([len(set(r)) for r in vs])
eu = np.ptp(us, axis=1); ev = np.ptp(vs, axis=1)
rh = (nu == 2) & (nv == 2) & (np.abs(eu - 128) <= 8) & (np.abs(ev - 128) <= 8)
spike = lambda c: (np.abs(eu - c) <= 2) & (np.abs(ev - c) <= 4)
out = {}
for s in ("L.rule", "L.free", "L.keyed", "W.keyed", "M.flow", "M.free", "M.smooth", "W.proj"):
    m = sub == s
    if not m.any():
        continue
    a = area[m].sum()
    out[s] = dict(area_pct_rect_half=round(100 * float(area[m & rh].sum() / a), 1),
                  area_pct_exact128=round(100 * float(area[m & spike(128)].sum() / a), 1),
                  area_pct_exact120=round(100 * float(area[m & spike(120)].sum() / a), 1),
                  area_pct_exact136=round(100 * float(area[m & spike(136)].sum() / a), 1))
mm = np.isin(sub, ["M.flow", "M.free", "M.smooth", "M.unique"])
out["all_M_area_pct_rect_half"] = round(100 * float(area[mm & rh].sum() / area[mm].sum()), 1)
out["mapwide_area_pct_M_that_is_rect_half"] = round(100 * float(area[mm & rh].sum() / area.sum()), 1)
print(json.dumps(out, indent=1))
(C.OUT / "verify_mclass_tiles.json").write_text(json.dumps(out, indent=1))
