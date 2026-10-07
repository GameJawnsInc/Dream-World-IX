"""VERIFY (adversarial) -- UV-10: what drives the kit's _cell_rect 'baked-unique' flag?
(a) grass: is the 43% unique driven by off-lattice (corner-pinned) or sloped tris, i.e. plan-affine extrapolation
    to the lattice cell corners from a tri that is not a lattice-aligned tile?
(b) rock: is the 98% driven by steepness (a near-vertical tri's plan-affine field, extrapolated to its 4u cell
    corners, gives arbitrary values -- unique by construction)?
Runs ff9mapkit.world.transplant._cell_rect exactly as uvc_reconcile R2 does. Read-only."""
import json
import math
from collections import defaultdict
import numpy as np
import uvc_common as C
from ff9mapkit.world.transplant import _cell_rect

d = C.load(1, "terrain")
P, UV, TOPO, BLK = d["P"], d["UV"], d["TOPO"], d["BLK"]
slope = C.slope_deg(P)
onlat = (np.abs(P[:, :, [0, 2]] / 4 - np.round(P[:, :, [0, 2]] / 4)) < 1e-3).all(axis=(1, 2))   # all 3 corners on 4u lattice


def flags(mask):
    cells_of = defaultdict(set); keys = {}
    for t in np.nonzero(mask)[0]:
        r = _cell_rect([(tuple(P[t, k]), None, tuple(UV[t, k])) for k in range(3)])
        if r is None:
            continue
        cell = (int(BLK[t, 0]), int(BLK[t, 1]), math.floor(P[t, :, 0].mean() / 4), math.floor(P[t, :, 2].mean() / 4))
        cells_of[r[0]].add(cell); keys[t] = r[0]
    ts = np.array(list(keys))
    uq = np.array([len(cells_of[keys[t]]) <= 1 for t in ts])
    return ts, uq


out = {}
for name, mask in (("grass0", TOPO == 0), ("topo17", TOPO == 17), ("topo49", TOPO == 49)):
    ts, uq = flags(mask)
    r = dict(n=int(len(ts)), unique_pct=round(100 * float(uq.mean()), 1))
    for lab, sel in (("lattice_aligned_flat(<10deg)", onlat[ts] & (slope[ts] < 10)),
                     ("off_lattice_flat(<10deg)", (~onlat[ts]) & (slope[ts] < 10)),
                     ("slope_10_45", (slope[ts] >= 10) & (slope[ts] < 45)),
                     ("steep_ge45", slope[ts] >= 45)):
        if sel.sum():
            r[lab] = dict(n=int(sel.sum()), unique_pct=round(100 * float(uq[sel].mean()), 1))
    out[name] = r
print(json.dumps(out, indent=1))
(C.OUT / "verify_baked_metric.json").write_text(json.dumps(out, indent=1))
