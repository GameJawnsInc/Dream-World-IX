"""uvclass PROBE 4 -- IS SHADING BAKED PER FACING? (decides whether rotating a carried wall is lawful)

Ground/wall normals are render-inert (memory project-ff9-ground-junction-synthesis: WorldMap/Terrain binds vertex +
texcoord only), so every bit of light on a face is PAINTED into the atlas texels its uvs select. If the painter
picked darker windows for faces turned away from a light, a carried wall ROTATED about Y would show its light on
the wrong side relative to its unrotated neighbours. Test: for steep (>= 40 deg) rock/lip tris, the mean
luminance of the atlas texels under the tri vs the facet's FACING azimuth; fit L = a + b*cos(az - phi) and compare
the swing b with the within-sector spread. Calibrated on a synthetic injected-cosine control (the fit must
recover a known b). Reads the engine-rendered atlas READ-ONLY (atlas.load_atlas(cache=False): no cache writes).
Writes out/probe_light.json. Rerun: py studies/terrain-malleability/uvclass/uvc_probe_light.py
"""
import json
import math

import numpy as np

import uvc_common as C
from ff9mapkit.world import atlas as A

img = np.asarray(A.load_atlas("terrain", cache=False).convert("RGB"), dtype=np.float64)
H, W = img.shape[:2]
lum = 0.299 * img[..., 0] + 0.587 * img[..., 1] + 0.114 * img[..., 2]
d = C.load(1, "terrain")
P, UV, TOPO = d["P"], d["UV"], d["TOPO"]
cls = np.load(C.OUT / "classes_terrain.npz")
sub = cls["sub"]
nn, area = C.tri_normals(P)
nn = nn * np.sign(nn[:, 1:2] + 1e-12)
slope = C.slope_deg(P)
bary = np.array([(i / 4, j / 4, 1 - i / 4 - j / 4) for i in range(5) for j in range(5 - i)])
S = np.einsum("bk,nkc->nbc", bary, UV)                       # raw uv samples
px = np.clip((S[..., 0] * W).astype(int), 0, W - 1)
py = np.clip((S[..., 1] * H).astype(int), 0, H - 1)
# uv origin convention: test both v-flips and keep the one whose mains-grass texels are GREEN (calibration)
grass = np.nonzero(TOPO == 0)[0][:2000]
g_noflip = img[py[grass], px[grass]].mean(axis=(0, 1))
g_flip = img[H - 1 - py[grass], px[grass]].mean(axis=(0, 1))
flip = (g_flip[1] - g_flip[[0, 2]].mean()) > (g_noflip[1] - g_noflip[[0, 2]].mean())
if flip:
    py = H - 1 - py
tri_lum = lum[py, px].mean(axis=1)
az = np.degrees(np.arctan2(nn[:, 0], nn[:, 2])) % 360          # facing azimuth of the outward (up-ish) normal


def fit(azd, L):
    a = np.radians(azd)
    X = np.column_stack([np.ones_like(a), np.cos(a), np.sin(a)])
    c, *_ = np.linalg.lstsq(X, L, rcond=None)
    b = math.hypot(c[1], c[2])
    phi = math.degrees(math.atan2(c[2], c[1])) % 360
    pred = X @ c
    r2 = 1 - ((L - pred) ** 2).sum() / max(((L - L.mean()) ** 2).sum(), 1e-9)
    sectors = [L[((azd - s) % 360) < 45] for s in range(0, 360, 45)]
    within = float(np.median([x.std() for x in sectors if len(x) > 5]))
    return dict(n=int(len(L)), mean=round(float(L.mean()), 1), swing_b=round(b, 2), brightest_facing_deg=round(phi),
                r2=round(float(r2), 4), within_sector_std=round(within, 1),
                sector_means=[round(float(x.mean()), 1) if len(x) else None for x in sectors])


res = {"uv_v_flipped": bool(flip), "grass_mean_rgb": [round(float(x), 1) for x in (g_flip if flip else g_noflip)]}
rng = np.random.default_rng(3)
steep = (slope >= 40) & (area > 0.05)
base = steep & (TOPO == 49)
fake = rng.normal(120, 25, base.sum()) + 12 * np.cos(np.radians(az[base] - 135))
res["control_injected_b12_phi135"] = fit(az[base], fake)
print("control (injected b=12 @135deg):", res["control_injected_b12_phi135"])
for name, m in (("rock49_steep", base), ("rock49_Mflow_steep", base & (sub == "M.flow")),
                ("rock49_Wkeyed_steep", base & (sub == "W.keyed")), ("lip58_steep", steep & (TOPO == 58)),
                ("forest_curtain_steep", steep & np.isin(TOPO, [36, 37]))):
    if m.sum() < 30:
        continue
    res[name] = fit(az[m], tri_lum[m])
    print(f"{name}: {res[name]}")
(C.OUT / "probe_light.json").write_text(json.dumps(res, indent=1))
