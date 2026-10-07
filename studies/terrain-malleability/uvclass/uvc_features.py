"""uvclass STAGE 1 -- per-patch + per-tri UV-parameterization FEATURES for every disc-1 Terrain (and Object) tri.

Writes (derived statistics only -- no positions/uvs):
  out/features_<part>.npz   per-tri: pid, topo, block, slope, density (px/u), anisotropy, reuse;
                            per-patch: n, m (distinct verts), plan/uv extents, fit residuals, a3 elevation,
                            nonplanarity, contour-axis spread
Rerun: py studies/terrain-malleability/uvclass/uvc_features.py [terrain|object]

FEATURES
  * patch      -- edge-continuous UV patch (uvc_common.patches, eps 0.5 quanta = exact-match; Uaho reproduces
                  the recorded 9 patches 47/21/21/12/11/9/7/5/1 with eps 0.0015 -- uvc_calibrate.py C0)
  * fits       -- on the patch's DISTINCT vertex positions: plan T=A(x,z)+c (3 params/axis), a3 T=M(x,y,z)+c
                  (4/axis), wall T=A(s,y)+c over the best horizontal invariant azimuth (3/axis + 1 search dof).
                  A fit is only REPORTED when m >= params+2 (else nan): a 4-vert patch is trivially 'affine'.
  * reuse      -- ART reuse: the atlas is gridded at 16px; every tri's uv triangle is sampled (21 barycentric
                  points); per atlas cell we count DISTINCT PATCHES and DISTINCT BLOCKS that sample it. A tri's
                  reuse = median over its samples. Tile languages are sampled by hundreds of patches/blocks;
                  art painted for ONE place is sampled only there.
  * density    -- per-tri texel-gradient singular values (px per world unit along the surface): sqrt(s1*s2)
                  and s1/s2 (anisotropy).
  * flow       -- per-tri texture direction of the CONTOUR (horizontal in-plane) gradient; per patch the
                  circular spread (mod 180) of that direction -- a flow-aligned chart (u along the contour)
                  has small spread.
"""
import math
import sys
import time
from collections import defaultdict

import numpy as np

import uvc_common as C

PART = sys.argv[1] if len(sys.argv) > 1 else "terrain"
t0 = time.time()
d = C.load(1, PART)
P, UV, T, TOPO, BLK = d["P"], d["UV"], d["T"], d["TOPO"], d["BLK"]
N = len(P)
pid = C.patches(P, UV, eps_q=0.5)
NP = pid.max() + 1
print(f"[{PART}] {N} tris, {NP} patches ({time.time() - t0:.1f}s)")

J, sv, Jp = C.tri_jacobian(P, T)
nn, area = C.tri_normals(P)
slope = C.slope_deg(P)
dens = np.sqrt(np.maximum(sv[:, 0] * sv[:, 1], 0))
aniso = sv[:, 0] / np.maximum(sv[:, 1], 1e-9)
up = np.array([0.0, 1.0, 0.0])
th = np.cross(nn, up)
thn = np.linalg.norm(th, axis=1)
th = th / np.where(thn[:, None] > 1e-9, thn[:, None], 1)
gh = np.einsum("nij,nj->ni", J, th)                         # texel change per unit along the contour
ang_h = np.where(thn > 1e-3, np.degrees(np.arctan2(gh[:, 1], gh[:, 0])) % 180, np.nan)
uvarea = 0.5 * np.abs((T[:, 1, 0] - T[:, 0, 0]) * (T[:, 2, 1] - T[:, 0, 1]) -
                      (T[:, 2, 0] - T[:, 0, 0]) * (T[:, 1, 1] - T[:, 0, 1]))

# ---- ART REUSE ---------------------------------------------------------------------------------------
G = 16.0
bary = []
for i in range(6):
    for j in range(6 - i):
        bary.append((i / 5, j / 5, 1 - i / 5 - j / 5))
bary = np.array(bary)                                       # 21 points
S = np.einsum("bk,nkc->nbc", bary, T)                       # (N,21,2)
cu = np.clip((S[..., 0] // G).astype(np.int64), 0, int(C.AW // G) - 1)
cv = np.clip((S[..., 1] // G).astype(np.int64), 0, int(C.AH // G) - 1)
cell = cu * 100000 + cv                                     # (N,21)
blkid = BLK[:, 0] * 100 + BLK[:, 1]
cell_patches = defaultdict(set)
cell_blocks = defaultdict(set)
for t in range(N):
    for c in set(cell[t].tolist()):
        cell_patches[c].add(int(pid[t]))
        cell_blocks[c].add(int(blkid[t]))
reuse_p = np.array([np.median([len(cell_patches[c]) for c in cell[t]]) for t in range(N)])
reuse_b = np.array([np.median([len(cell_blocks[c]) for c in cell[t]]) for t in range(N)])
# FAR reuse: blocks >= 2 blocks away (Chebyshev) from the tri's own block that sample the same atlas cell --
# robust to one mural straddling a block border (which would inflate reuse_b)
cell_barr = {c: np.array([[b // 100, b % 100] for b in bs]) for c, bs in cell_blocks.items()}
_far_memo = {}


def _far(c, bx, by):
    k = (c, bx, by)
    if k not in _far_memo:
        a = cell_barr[c]
        _far_memo[k] = int((np.maximum(np.abs(a[:, 0] - bx), np.abs(a[:, 1] - by)) >= 2).sum())
    return _far_memo[k]


reuse_far = np.array([np.median([_far(c, BLK[t, 0], BLK[t, 1]) for c in cell[t]]) for t in range(N)])
print(f"  reuse done ({time.time() - t0:.1f}s)")

# ---- per-patch fits ----------------------------------------------------------------------------------
members = defaultdict(list)
for t in range(N):
    members[int(pid[t])].append(t)
cols = list(C.FEATURE_COLS)
F = np.full((NP, len(cols)), np.nan)
for p, tr in members.items():
    tr = np.asarray(tr)
    row = C.patch_features(P[tr], T[tr])
    F[p] = [row.get(c, np.nan) for c in cols]
print(f"  fits done ({time.time() - t0:.1f}s)")

np.savez_compressed(C.OUT / f"features_{PART}.npz", pid=pid, topo=TOPO, blk=BLK, slope=slope, dens=dens,
                    aniso=aniso, area=area, ang_h=ang_h, reuse_p=reuse_p, reuse_b=reuse_b, reuse_far=reuse_far,
                    uvarea=uvarea, F=F,
                    cols=np.array(cols))
print(f"wrote {C.OUT / f'features_{PART}.npz'} ({time.time() - t0:.1f}s)")
