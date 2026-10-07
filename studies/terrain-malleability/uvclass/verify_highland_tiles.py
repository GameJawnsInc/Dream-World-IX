"""VERIFY (adversarial) -- UV-12: per highland block, how much rock (topo 49) is EXACT tile windows?
A tri that is an axis-aligned rect-half of a 128 px tile (2 distinct u, 2 distinct v among its 3 corners, both
extents 128 +- 8 px) wears a keyed tile window; the classifier's W.keyed/L share is compared per block.
Same block set as uvc_census (>= 20 topo-49 tris). Read-only."""
import json
import numpy as np
import uvc_common as C

d = C.load(1, "terrain")
P, T, TOPO, BLK = d["P"], d["T"], d["TOPO"], d["BLK"]
_, area = C.tri_normals(P)
c = json.load(open(C.OUT / "census_terrain.json"))
hl = c["highland_rock_by_block"]


def rect_half(tt):
    us = np.unique(np.round(tt[:, 0])); vs = np.unique(np.round(tt[:, 1]))
    return len(us) == 2 and len(vs) == 2 and abs(np.ptp(us) - 128) <= 8 and abs(np.ptp(vs) - 128) <= 8


rh = np.zeros(len(P), bool)
for t in np.nonzero(TOPO == 49)[0]:
    rh[t] = rect_half(T[t])
rows = {}
for k, v in hl.items():
    bx, by = map(int, k.split(","))
    m = (BLK[:, 0] == bx) & (BLK[:, 1] == by) & (TOPO == 49)
    rows[k] = dict(rect_half_area_pct=round(100 * float(area[m & rh].sum() / area[m].sum()), 1),
                   classifier_keyed_plus_L=round(v["W_keyed"] + v["L"], 1), classifier_M=v["M"])
x = np.array([r["rect_half_area_pct"] for r in rows.values()])
y = np.array([r["classifier_keyed_plus_L"] for r in rows.values()])
out = dict(blocks=len(rows), rect_half_pct_p10_50_90=[round(float(q), 1) for q in np.percentile(x, [10, 50, 90])],
           blocks_rect_half_ge50=int((x >= 50).sum()), blocks_rect_half_ge30=int((x >= 30).sum()),
           blocks_classifier_keyed_plus_L_ge50=int((y >= 50).sum()),
           mural_M_ge80_blocks_with_rect_half_ge30=int(sum(1 for r in rows.values() if r["classifier_M"] >= 80 and r["rect_half_area_pct"] >= 30)),
           corr_rect_half_vs_classifier_keyed=round(float(np.corrcoef(x, y)[0, 1]), 3),
           examples={k: rows[k] for k in ("16,12", "16,11", "16,13", "21,11", "15,13", "14,13", "6,15", "15,1", "18,11")
                     if k in rows})
print(json.dumps(out, indent=1))
(C.OUT / "verify_highland_tiles.json").write_text(json.dumps(out, indent=1))
