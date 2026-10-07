"""uvclass PROBE 3 -- THE KEYING EXPONENT: is a chart's uv KEYED to vertex roles (tile corners: the window is fixed
whatever the geometry does) or PROJECTED (texel density fixed, the window follows the geometry)?

Within a patch, regress log(texel density) on log(tri size) (size = sqrt(surface area)):
    kappa = -slope.   kappa ~ 1  => KEYED (uv area constant; density ~ 1/size)    -- coastal lip columns, corner-pinned cells
                      kappa ~ 0  => PROJECTED/UNROLLED (density constant)            -- a parallel projection / arc unroll
Only patches whose tri sizes actually vary (std log size >= 0.05, >= 4 tris) can testify. Pooled per family as the
within-patch demeaned regression (one slope per family) + per-patch median.
Rerun: py studies/terrain-malleability/uvclass/uvc_probe_keying.py
"""
import json
from collections import defaultdict

import numpy as np

import uvc_common as C

z = np.load(C.OUT / "features_terrain.npz")
pid, topo, dens, area = z["pid"], z["topo"], z["dens"], z["area"]
size = np.sqrt(np.maximum(area, 1e-9))
members = defaultdict(list)
for t in range(len(pid)):
    members[int(pid[t])].append(t)
pool = defaultdict(lambda: ([], []))
per = defaultdict(list)
for p, tr in members.items():
    tr = np.array(tr)
    if len(tr) < 4:
        continue
    ls, ld = np.log(size[tr]), np.log(np.maximum(dens[tr], 1e-6))
    if ls.std() < 0.05:
        continue
    f = C.fam(np.bincount(topo[tr]).argmax())
    pool[f][0].extend((ls - ls.mean()).tolist())
    pool[f][1].extend((ld - ld.mean()).tolist())
    per[f].append(-np.polyfit(ls, ld, 1)[0])
res = {}
print("family    testifying patches   pooled kappa   per-patch kappa p25/p50/p75   frac kappa>=0.6")
for f in sorted(pool, key=lambda f: -len(per[f])):
    x, y = map(np.array, pool[f])
    k = -float(np.polyfit(x, y, 1)[0])
    a = np.array(per[f])
    res[f] = dict(patches=len(a), pooled_kappa=round(k, 3),
                  kappa_p25_50_75=[round(float(v), 3) for v in np.percentile(a, [25, 50, 75])],
                  frac_keyed=round(float((a >= 0.6).mean()), 3))
    print(f"{f:9s} {len(a):6d}             {k:6.2f}         {np.percentile(a, 25):5.2f}/{np.median(a):5.2f}/"
          f"{np.percentile(a, 75):5.2f}              {(a >= 0.6).mean():.2f}")
(C.OUT / "probe_keying.json").write_text(json.dumps(res, indent=1))
