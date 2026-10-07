"""uvclass lane -- shared machinery for THE DEFORMATION-TOLERANCE CENSUS (UV parameterization classes).

Read-only on the install. Raw mesh data (positions/UVs) is cached OUTSIDE the repo (provenance gate) in
%TEMP%/ff9_uvclass_cache/ ; everything written under studies/ is derived statistics.

Units: UV is reported in MOGURI ATLAS PX = (u*2048, v*4096) -- the engine-rendered HD atlas (atlas.py:17),
the unit every prior UV study in studies/overworld-topography uses (uaho_flow_anatomy.py res_u*2048/res_v*4096).
In this unit the mains grass density is isotropic (~31 px/u both axes) and one rock/mains tile is ~128 px.
Stock quantization (ground_uv_law.py M0): uv to 1/1024 = 2 px (u) / 4 px (v); position to 1/256 u.

World frame: block (bx,by) local verts are translated by (bx*64, 0, -by*64) (extract.block_world_origin).
"""
from __future__ import annotations

import math
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import extract as X  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
CACHE_DIR = Path(os.environ.get("FF9_UVCLASS_CACHE",
                                Path(os.environ.get("TEMP", HERE)) / "ff9_uvclass_cache"))

AW, AH = 2048.0, 4096.0          # Moguri atlas px
TILE = 128.0                     # px, one tile (rock 128x128 / mains quadrant ~124)


# ---------------------------------------------------------------------------------------------------
# cache
# ---------------------------------------------------------------------------------------------------
def build_cache(disc: int = 1, part: str = "terrain", force: bool = False) -> Path:
    """Flatten every block's `part` mesh into world-frame arrays: P (ntri,3,3) float64, UV (ntri,3,2) float64
    (raw uv), IDALL (ntri,), BLK (ntri,2). Stored outside the repo."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"disc{disc}_{part}.npz"
    if path.exists() and not force:
        return path
    blocks = X.list_blocks(disc=disc) if part == "terrain" else X.list_object_blocks(disc=disc)
    Ps, UVs, IDs, BLKs = [], [], [], []
    t0 = time.time()
    for (bx, by) in blocks:
        try:
            bm = X.read_block(bx, by, disc=disc, part=part)
        except Exception as e:  # noqa: BLE001
            print(f"  skip ({bx},{by}): {e}")
            continue
        if not bm.uvs or not bm.tangents:
            continue
        V = np.asarray(bm.verts, dtype=np.float64)
        U = np.asarray(bm.uvs, dtype=np.float64)[:, :2]
        Tn = np.asarray(bm.tangents, dtype=np.float64)
        idx = np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3)
        P = V[idx].copy()
        P[:, :, 0] += bx * 64.0
        P[:, :, 2] += -by * 64.0
        Ps.append(P)
        UVs.append(U[idx])
        IDs.append(np.round(Tn[idx[:, 0], 0]).astype(np.int64))
        BLKs.append(np.tile(np.array([bx, by], dtype=np.int64), (len(idx), 1)))
    np.savez_compressed(path, P=np.concatenate(Ps), UV=np.concatenate(UVs), IDALL=np.concatenate(IDs),
                        BLK=np.concatenate(BLKs))
    print(f"cache {path} built in {time.time() - t0:.1f}s ({sum(len(p) for p in Ps)} tris, {len(Ps)} blocks)")
    return path


def load(disc: int = 1, part: str = "terrain") -> dict:
    d = dict(np.load(build_cache(disc, part)))
    d["TOPO"] = (d["IDALL"] & 0xFC) >> 2
    d["T"] = np.stack([d["UV"][..., 0] * AW, d["UV"][..., 1] * AH], axis=-1)   # Moguri px
    return d


# ---------------------------------------------------------------------------------------------------
# geometry helpers
# ---------------------------------------------------------------------------------------------------
def tri_normals(P):
    n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    a = np.linalg.norm(n, axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        nn = n / a[:, None]
    return nn, 0.5 * a


def slope_deg(P):
    nn, _ = tri_normals(P)
    return np.degrees(np.arccos(np.clip(np.abs(nn[:, 1]), 0, 1)))


def tri_jacobian(P, T):
    """Per-tri 2x3 texel gradient J (px per world unit) with J.e1=d1, J.e2=d2, J.n=0.
    Returns sv (ntri,2) singular values (sigma1>=sigma2), det sign (handedness w.r.t. the up-ish normal),
    and Jp (ntri,2,2) = the PLAN jacobian d(T)/d(x,z) (nan for plan-degenerate tris)."""
    e1 = P[:, 1] - P[:, 0]
    e2 = P[:, 2] - P[:, 0]
    d1 = T[:, 1] - T[:, 0]
    d2 = T[:, 2] - T[:, 0]
    E = np.stack([e1, e2], axis=2)          # (n,3,2)
    D = np.stack([d1, d2], axis=2)          # (n,2,2)
    J = D @ np.linalg.pinv(E)               # (n,2,3)
    sv = np.linalg.svd(J, compute_uv=False)
    # plan jacobian
    Ep = np.stack([e1[:, [0, 2]], e2[:, [0, 2]]], axis=2)   # (n,2,2)
    det = np.linalg.det(Ep)
    Jp = np.full((len(P), 2, 2), np.nan)
    ok = np.abs(det) > 1e-6
    Jp[ok] = D[ok] @ np.linalg.inv(Ep[ok])
    return J, sv, Jp


# ---------------------------------------------------------------------------------------------------
# UV-continuity patch decomposition (global, cross-block)
# ---------------------------------------------------------------------------------------------------
def poskey(p):
    return (round(p[0] * 256), round(p[1] * 256), round(p[2] * 256))


def patches(P, UV, mask=None, eps_q: float = 0.5, return_edges: bool = False):
    """Union tris that share a geometric EDGE (both endpoint positions, 1/256-exact keys) AND carry matching
    uv at both shared endpoints (|du|,|dv| <= eps_q quanta of 1/1024). Returns pid (ntri,) (-1 outside mask)
    [+ edge stats]. Mirrors forest_uv_components.py / uaho_flow_anatomy.py's continuity rule."""
    n = len(P)
    if mask is None:
        mask = np.ones(n, bool)
    eps = eps_q / 1024.0
    parent = np.arange(n)

    def find(a):
        r = a
        while parent[r] != r:
            r = parent[r]
        while parent[a] != r:
            parent[a], a = r, parent[a]
        return r

    edges = defaultdict(list)
    idxs = np.nonzero(mask)[0]
    keys = {}
    for t in idxs:
        ks = [poskey(P[t, k]) for k in range(3)]
        keys[t] = ks
        for a, b in ((0, 1), (1, 2), (2, 0)):
            ka, kb = ks[a], ks[b]
            e = (ka, kb) if ka <= kb else (kb, ka)
            edges[e].append((t, a, b) if ka <= kb else (t, b, a))
    n_int = n_cont = 0
    for e, lst in edges.items():
        if len(lst) < 2:
            continue
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                (t1, a1, b1), (t2, a2, b2) = lst[i], lst[j]
                if t1 == t2:
                    continue
                n_int += 1
                d = max(abs(UV[t1, a1, 0] - UV[t2, a2, 0]), abs(UV[t1, a1, 1] - UV[t2, a2, 1]),
                        abs(UV[t1, b1, 0] - UV[t2, b2, 0]), abs(UV[t1, b1, 1] - UV[t2, b2, 1]))
                if d <= eps:
                    n_cont += 1
                    r1, r2 = find(t1), find(t2)
                    if r1 != r2:
                        parent[r1] = r2
    pid = np.full(n, -1, dtype=np.int64)
    roots = {}
    for t in idxs:
        r = find(t)
        pid[t] = roots.setdefault(r, len(roots))
    if return_edges:
        return pid, dict(interior_edges=n_int, continuous=n_cont)
    return pid


# ---------------------------------------------------------------------------------------------------
# per-patch chart fits
# ---------------------------------------------------------------------------------------------------
def _lsq_res(A, Y):
    coef, *_ = np.linalg.lstsq(A, Y, rcond=None)
    r = np.linalg.norm(A @ coef - Y, axis=1)
    return coef, r


def fit_patch(Pp, Tp):
    """Pp (m,3) world points, Tp (m,2) px. Returns dict of residuals (px) for:
       plan  : T = A.(x,z)+c        (top-down planar chart; invariant direction = +Y)
       wall  : T = A.(s,y)+c, s = horizontal axis, best over azimuth (invariant direction = horizontal normal d)
       a3    : T = M.(x,y,z)+c      (any parallel projection) + its invariant (null) direction elevation
       nonplanarity: the patch's spread of facet normals is computed by the caller."""
    m = len(Pp)
    one = np.ones((m, 1))
    out = {}
    _, r = _lsq_res(np.hstack([Pp[:, [0, 2]], one]), Tp)
    out["plan_max"], out["plan_p90"] = float(r.max()), float(np.percentile(r, 90))
    M, r3 = _lsq_res(np.hstack([Pp, one]), Tp)
    out["a3_max"], out["a3_p90"] = float(r3.max()), float(np.percentile(r3, 90))
    g = M[:3, :].T                       # (2,3) gradient rows
    d = np.cross(g[0], g[1])
    nd = np.linalg.norm(d)
    out["a3_elev"] = float(np.degrees(np.arcsin(min(1.0, abs(d[1]) / nd)))) if nd > 1e-12 else float("nan")
    # wall: scan azimuth of the invariant horizontal direction d=(cos a,0,sin a); s = coordinate across d
    best = (1e18, None, None)
    for a in np.radians(np.arange(0, 180, 3.0)):
        s = -math.sin(a) * Pp[:, 0] + math.cos(a) * Pp[:, 2]
        _, rw = _lsq_res(np.column_stack([s, Pp[:, 1], one[:, 0]]), Tp)
        if rw.max() < best[0]:
            best = (float(rw.max()), float(np.percentile(rw, 90)), float(np.degrees(a)))
    a0 = best[2]
    for da in np.arange(-3, 3.01, 0.5):
        a = math.radians(a0 + da)
        s = -math.sin(a) * Pp[:, 0] + math.cos(a) * Pp[:, 2]
        _, rw = _lsq_res(np.column_stack([s, Pp[:, 1], one[:, 0]]), Tp)
        if rw.max() < best[0]:
            best = (float(rw.max()), float(np.percentile(rw, 90)), a0 + da)
    out["wall_max"], out["wall_p90"], out["wall_az"] = best
    return out


def plan_arclength(Pp):
    """s_arc for each point: arclength along a polynomial (quartic when >=7 distinct stations) plan curve fitted in
    the patch's PCA frame (a strip-like wall's contour). Returns (s_arc, bend) where bend = the fitted curve's
    sagitta (u) -- its deviation from the chord."""
    xz = Pp[:, [0, 2]]
    c0 = xz.mean(0)
    _, _, vt = np.linalg.svd(xz - c0)
    pa = (xz - c0) @ vt[0]
    pb = (xz - c0) @ vt[1]
    if np.ptp(pa) < 1e-6:
        return pa, 0.0
    deg = 4 if len(np.unique(np.round(pa, 2))) >= 7 else (2 if len(pa) >= 4 else 1)
    cq = np.polyfit(pa, pb, deg)                            # quartic: a <=~150 deg arc stays a graph over its chord
    grid = np.linspace(pa.min(), pa.max(), 200)
    seg = np.sqrt(1 + np.polyval(np.polyder(cq), grid) ** 2)
    cum = np.concatenate([[0], np.cumsum((seg[1:] + seg[:-1]) / 2 * np.diff(grid))])
    sag = float(np.ptp(np.polyval(cq, grid) - np.interp(grid, [grid[0], grid[-1]], np.polyval(cq, [grid[0], grid[-1]]))))
    return np.interp(pa, grid, cum), sag


def fit_extra(Pp, Tp):
    """arc : T = A.(s_arc, y)+c  (a wall unrolled ALONG ITS OWN CURVE -- the kit's coastal arc-length band form)
       quad: T = full quadratic in (x,y,z) (10/axis) -- is a non-affine chart a SMOOTH field or jitter?"""
    m = len(Pp)
    out = {"arc_max": np.nan, "quad_max": np.nan, "bend": np.nan}
    one = np.ones(m)
    if m >= 5:
        s, bend = plan_arclength(Pp)
        _, r = _lsq_res(np.column_stack([s, Pp[:, 1], one]), Tp)
        out["arc_max"], out["bend"] = float(r.max()), bend
    if m >= 13:
        c = Pp - Pp.mean(0)
        x, y, z = c[:, 0], c[:, 1], c[:, 2]
        A = np.column_stack([one, x, y, z, x * x, y * y, z * z, x * y, x * z, y * z])
        _, r = _lsq_res(A, Tp)
        out["quad_max"] = float(r.max())
    return out


FAMILY = {  # look families (interior KB + mural_partition_settle.py DOCUMENTED + ground_uv_law FAMILIES)
    "grass": (0, 1, 2, 3, 42), "plateau": (10, 11, 12), "shelf13": (13,), "bldg59": (59,),
    "scrub": (4, 5, 6), "desert": (16, 17, 18, 19, 20, 21, 22, 23), "dunes": (41,), "brush38": (38,),
    "snow": (27, 28), "canyon": (45, 46), "forest": (36, 37), "rock49": (49,), "flat7": (7,),
    "bank62": (62,), "sand": (31, 32, 33), "lip58": (58,), "water": (48, 50, 51, 53, 54, 57),
}
FAM_OF = {t: f for f, ts in FAMILY.items() for t in ts}


def fam(topo: int) -> str:
    return FAM_OF.get(int(topo), f"t{int(topo)}")


# ---------------------------------------------------------------------------------------------------
# THE PER-PATCH FEATURE ROW (one code path for the census AND the synthetic calibration controls)
# ---------------------------------------------------------------------------------------------------
FEATURE_COLS = ("n", "m", "plan_ext", "uv_ext_u", "uv_ext_v", "plan_max", "plan_p90", "a3_max", "a3_p90", "a3_elev",
                "wall_max", "wall_p90", "wall_az", "nonplanar_deg", "flow_spread", "slope_p50", "area",
                "arc_max", "quad_max", "bend", "cell_plan_max", "cv_dens", "cv_uvarea", "cv_area", "kappa", "pin")


def _pin(vals):
    best = 0.0
    for ph in np.arange(0, 128, 2.0):
        r = np.abs(((vals - ph + 64) % 128) - 64)
        best = max(best, float((r <= 6.0).mean()))
    return best


def patch_features(Ptr, Ttr) -> dict:
    """Ptr (k,3,3) world tri corners, Ttr (k,3,2) Moguri px -- ONE edge-continuous patch. Returns the feature row:
      fits on DISTINCT verts (plan 3/axis needs m>=5; a3 4/axis needs m>=6; quad needs m>=13), per-CELL plan fit,
      nonplanarity, contour-flow spread, density/uv-area CVs, the KEYING EXPONENT kappa (-dlog density/dlog size),
      and the 128px tile-lattice PIN fraction."""
    k = len(Ptr)
    _, sv, _ = tri_jacobian(Ptr, Ttr)
    dens = np.sqrt(np.maximum(sv[:, 0] * sv[:, 1], 0))
    nn, area = tri_normals(Ptr)
    slope = np.degrees(np.arccos(np.clip(np.abs(nn[:, 1]), 0, 1)))
    J, _, _ = tri_jacobian(Ptr, Ttr)
    up = np.array([0.0, 1.0, 0.0])
    th = np.cross(nn, up)
    thn = np.linalg.norm(th, axis=1)
    th = th / np.where(thn[:, None] > 1e-9, thn[:, None], 1)
    gh = np.einsum("nij,nj->ni", J, th)
    ang_h = np.where(thn > 1e-3, np.degrees(np.arctan2(gh[:, 1], gh[:, 0])) % 180, np.nan)
    uvarea = 0.5 * np.abs((Ttr[:, 1, 0] - Ttr[:, 0, 0]) * (Ttr[:, 2, 1] - Ttr[:, 0, 1]) -
                          (Ttr[:, 2, 0] - Ttr[:, 0, 0]) * (Ttr[:, 1, 1] - Ttr[:, 0, 1]))
    pts = {}
    for t in range(k):
        for c in range(3):
            pts.setdefault(poskey(Ptr[t, c]), (Ptr[t, c], Ttr[t, c]))
    Pp = np.array([v[0] for v in pts.values()])
    Tp = np.array([v[1] for v in pts.values()])
    m = len(Pp)
    row = dict(n=k, m=m, plan_ext=float(np.ptp(Pp[:, [0, 2]], axis=0).max()),
               uv_ext_u=float(np.ptp(Tp[:, 0])), uv_ext_v=float(np.ptp(Tp[:, 1])),
               slope_p50=float(np.median(slope)), area=float(area.sum()))
    nr = nn * np.sign(nn[:, 1:2] + 1e-12)
    row["nonplanar_deg"] = math.degrees(math.acos(float(np.clip((nr @ nr.T).min(), -1, 1))))
    a = ang_h[~np.isnan(ang_h)]
    if len(a) >= 2:
        z = np.exp(2j * np.radians(a))
        row["flow_spread"] = math.degrees(math.sqrt(max(0.0, -2 * math.log(max(abs(z.mean()), 1e-9))))) / 2
    if m >= 5:
        f = fit_patch(Pp, Tp)
        row.update({kk: f[kk] for kk in ("plan_max", "plan_p90", "wall_max", "wall_p90", "wall_az")})
        if m >= 6:
            row.update({kk: f[kk] for kk in ("a3_max", "a3_p90", "a3_elev")})
        row.update(fit_extra(Pp, Tp))
    groups = defaultdict(list)
    for t in range(k):
        groups[(math.floor(Ptr[t, :, 0].mean() / 4.0), math.floor(Ptr[t, :, 2].mean() / 4.0))].append(t)
    worst = float("nan")
    for g in groups.values():
        gp = {}
        for t in g:
            for c in range(3):
                gp.setdefault(poskey(Ptr[t, c]), (Ptr[t, c], Ttr[t, c]))
        if len(gp) < 4:
            continue
        Pg = np.array([v[0] for v in gp.values()])
        Tg = np.array([v[1] for v in gp.values()])
        A = np.column_stack([Pg[:, 0], Pg[:, 2], np.ones(len(Pg))])
        if np.linalg.matrix_rank(A) < 3:
            continue
        _, r = _lsq_res(A, Tg)
        worst = float(r.max()) if math.isnan(worst) else max(worst, float(r.max()))
    row["cell_plan_max"] = worst
    if k >= 3:
        cvf = lambda x: float(np.std(x) / max(np.mean(x), 1e-9))
        row["cv_dens"], row["cv_uvarea"], row["cv_area"] = cvf(dens), cvf(uvarea), cvf(area)
    if k >= 4:
        ls = np.log(np.sqrt(np.maximum(area, 1e-9)))
        if ls.std() >= 0.05:
            row["kappa"] = float(-np.polyfit(ls, np.log(np.maximum(dens, 1e-6)), 1)[0])
    if m >= 4:
        row["pin"] = min(_pin(Tp[:, 0]), _pin(Tp[:, 1]))
    return row
