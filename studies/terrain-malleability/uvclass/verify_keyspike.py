"""VERIFY (adversarial) -- non-circular keying test for the M.flow / W.keyed split.
Under KEYING (uv window fixed per vertex role) a tri's uv extent sits EXACTLY on the tile size (128 px, quantized
2 px u / 4 px v) whatever its geometric extent; under PROJECTION/UNROLL the uv extent tracks the geometric extent
smoothly (a narrow +-2 px window at 128 then holds only the few tris whose geometry happens to be ~4.1u).
For each class: share of tris whose uv ptp is exactly 128 (+-2 u / +-4 v) in BOTH axes, vs a control window at
120 px and 136 px (the smooth-density expectation), and the geometric-extent spread of the exact-128 tris.
Read-only."""
import json
import numpy as np
import uvc_common as C

d = C.load(1, "terrain")
P, T, TOPO = d["P"], d["T"], d["TOPO"]
cls = np.load(C.OUT / "classes_terrain.npz")["sub"]
ext = np.ptp(T, axis=1)                       # (n,2) uv extent px
nn, area = C.tri_normals(P)
up = np.array([0, 1.0, 0])
nn_u = nn * np.sign(nn[:, 1:2] + 1e-12)
th = np.cross(nn_u, up); thn = np.linalg.norm(th, axis=1); th = th / np.where(thn[:, None] > 1e-9, thn[:, None], 1)
geo_w = np.array([np.ptp(P[t] @ th[t]) for t in range(len(P))])   # along-contour extent
geo_h = np.ptp(P[:, :, 1], axis=1)

def win(c):
    return (np.abs(ext[:, 0] - c) <= 2) & (np.abs(ext[:, 1] - c) <= 4)

out = {}
for nm, m in (("topo49_Mflow", (TOPO == 49) & (cls == "M.flow")), ("topo49_Wkeyed", (TOPO == 49) & (cls == "W.keyed")),
              ("lip58_Mflow", (TOPO == 58) & (cls == "M.flow")), ("lip58_Wkeyed", (TOPO == 58) & (cls == "W.keyed")),
              ("grass_Lrule", np.isin(TOPO, [0, 1, 2, 3, 42]) & (cls == "L.rule"))):
    r = {"tris": int(m.sum())}
    for c in (112, 120, 128, 136, 144):
        r[f"area_pct_ext_{c}"] = round(100 * float(area[m & win(c)].sum() / area[m].sum()), 1)
    k = m & win(128)
    if k.sum() > 20:
        r["exact128_geo_width_p10_50_90"] = [round(float(x), 2) for x in np.percentile(geo_w[k], [10, 50, 90])]
        r["exact128_geo_height_p10_50_90"] = [round(float(x), 2) for x in np.percentile(geo_h[k], [10, 50, 90])]
    out[nm] = r
print(json.dumps(out, indent=1))
(C.OUT / "verify_keyspike.json").write_text(json.dumps(out, indent=1))
