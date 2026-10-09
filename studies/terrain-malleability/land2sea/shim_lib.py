"""Shared read-only instruments for the Shimmering land->sea measurement (disc 1 vs disc 4).

Run every script from C:\\gd\\Dream-World-IX\\ff9mapkit with `py` so the local ff9mapkit imports.
Reads ONLY the user's install (p0data*.bin through ff9mapkit.world.extract). Writes nothing outside this folder
(arealib caches decoded meshes as .npz in its own SCRATCH dir under %TEMP%).
"""
from __future__ import annotations

import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

KIT = Path(r"C:\gd\Dream-World-IX\ff9mapkit")
TM = Path(r"C:\gd\Dream-World-IX\studies\terrain-malleability")
sys.path.insert(0, str(KIT))
sys.path.insert(0, str(TM / "disc4"))
sys.path.insert(0, str(TM / "gap_area_layer"))
sys.path.insert(0, str(TM / "consumption"))
sys.path.insert(0, str(TM / "ingame"))

import ff9mapkit                                       # noqa: E402
assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
from ff9mapkit.world import extract as X               # noqa: E402
from ff9mapkit.world import placement as P             # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)

SHIM = [(6, 4), (7, 4), (6, 5), (7, 5)]
PARTS_ALL = ["object", "terrain", "beach1", "beach2", "sea1", "sea2", "sea3", "sea4", "sea5", "sea6",
             "stream", "river", "riverjoint", "falls"]
LAND_PARTS = {"Object", "Terrain", "VolcanoCrater1", "VolcanoLava1"}


def read(bx, by, disc, part):
    try:
        return X.read_block(bx, by, disc=disc, part=part)
    except ValueError:
        return None


def tri_arrays(bm):
    """-> dict of numpy arrays per tri: V[T,3,3] block-local pos, UV[T,3,2], ids[T], N[T,3,3]."""
    fi = np.asarray(bm.flat_index, dtype=np.int64)
    V = np.asarray(bm.verts, dtype=np.float64)[fi].reshape(-1, 3, 3)
    T = np.asarray(bm.tangents, dtype=np.float64)
    ids = np.rint(T[fi[0::3], 0]).astype(np.int64)
    UV = np.asarray(bm.uvs, dtype=np.float64)[fi].reshape(-1, 3, 2) if bm.uvs else None
    N = np.asarray(bm.normals, dtype=np.float64)[fi].reshape(-1, 3, 3) if bm.normals else None
    return {"V": V, "UV": UV, "ids": ids, "N": N}


def topo(ids):
    return (ids & 0xFC) >> 2


def area_bits(ids):
    return (ids & 0x3F00) >> 8


def event_bits(ids):
    return (ids & 0xC000) >> 14


def plan_cross(V):
    """(b-a)x(c-a) y-component in x/z (the sign = plan winding) and the engine's up-facing test cy/|n| > 0.1."""
    a, b, c = V[:, 0], V[:, 1], V[:, 2]
    u, v = b - a, c - a
    n = np.cross(u, v)
    L = np.linalg.norm(n, axis=1)
    L[L == 0] = 1.0
    return n[:, 1], n[:, 1] / L


def plan_area(V):
    a, b, c = V[:, 0], V[:, 1], V[:, 2]
    return 0.5 * np.abs((b[:, 0] - a[:, 0]) * (c[:, 2] - a[:, 2]) - (c[:, 0] - a[:, 0]) * (b[:, 2] - a[:, 2]))


def tri_key(tri, r=3):
    return tuple(sorted(tuple(round(float(c), r) for c in p) for p in tri))


def xz_key(tri, r=3):
    return tuple(sorted((round(float(p[0]), r), round(float(p[2]), r)) for p in tri))


def grid(pitch=0.5, ox=0.5, oz=0.5):
    """block-local sample lattice, cell centres: x in (0,64), z in (-64,0)."""
    n = int(round(64 / pitch))
    xs = (np.arange(n) + ox) * pitch
    zs = -(np.arange(n) + oz) * pitch
    gx, gz = np.meshgrid(xs, zs, indexing="ij")
    return gx.ravel(), gz.ravel()


def cover(V, px, pz, chunk=256):
    """Plan coverage of every sample by ANY tri of V (no facing filter).
    -> (count[S], ymin[S], ymax[S], first_tri[S] (-1))."""
    S = px.size
    cnt = np.zeros(S, np.int32)
    ymin = np.full(S, np.inf)
    ymax = np.full(S, -np.inf)
    first = np.full(S, -1, np.int64)
    if V is None or V.size == 0:
        return cnt, ymin, ymax, first
    a, b, c = V[:, 0], V[:, 1], V[:, 2]
    d = (b[:, 2] - c[:, 2]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 2] - c[:, 2])
    ok = np.abs(d) >= 1e-12
    for t0 in range(0, V.shape[0], chunk):
        ti = np.arange(t0, min(V.shape[0], t0 + chunk))
        ti = ti[ok[ti]]
        if ti.size == 0:
            continue
        A, B, C, D = a[ti], b[ti], c[ti], d[ti]
        x = px[None, :]
        z = pz[None, :]
        w0 = ((B[:, 2:3] - C[:, 2:3]) * (x - C[:, 0:1]) + (C[:, 0:1] - B[:, 0:1]) * (z - C[:, 2:3])) / D[:, None]
        w1 = ((C[:, 2:3] - A[:, 2:3]) * (x - C[:, 0:1]) + (A[:, 0:1] - C[:, 0:1]) * (z - C[:, 2:3])) / D[:, None]
        w2 = 1 - w0 - w1
        ins = (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
        y = w0 * A[:, 1:2] + w1 * B[:, 1:2] + w2 * C[:, 1:2]
        cnt += ins.sum(axis=0).astype(np.int32)
        ymin = np.minimum(ymin, np.where(ins, y, np.inf).min(axis=0))
        ymax = np.maximum(ymax, np.where(ins, y, -np.inf).max(axis=0))
        hit = ins.any(axis=0) & (first < 0)
        if hit.any():
            first[hit] = ti[ins[:, hit].argmax(axis=0)]
    return cnt, ymin, ymax, first


# --------------------------------------------------------------------------- engine ground query (stock only)
_A = None


def arealib():
    global _A
    if _A is None:
        import arealib as A
        _A = A
    return _A


def stock_walk(ns, bx, by):
    """[(child_name, V, ids)] form-1 walk meshes of the STOCK cell in engine registration order."""
    A = arealib()
    return A.load_walk_arrays([(n, k, "stock") for n, k in A.stock_walk_list(ns, bx, by)])


def ground_raster(ns, bx, by, px, pz):
    """The engine sky ground query (first mesh in registration order, up-facing, skip/veto ids) at block-local
    samples px/pz -> (part_name[S] ('MISS'), idall[S] (-1), y[S] (nan))."""
    A = arealib()
    meshes = stock_walk(ns, bx, by)
    S = px.size
    out_id = np.full(S, -1, np.int64)
    out_pi = np.full(S, -1, np.int16)
    out_y = np.full(S, np.nan)
    unresolved = np.ones(S, bool)
    for pi, (name, V, ids) in enumerate(meshes):
        if not unresolved.any() or V.size == 0:
            continue
        a, b, c = V[:, 0], V[:, 1], V[:, 2]
        u, v = b - a, c - a
        n = np.cross(u, v)
        L = np.linalg.norm(n, axis=1)
        L[L == 0] = 1.0
        d = (b[:, 2] - c[:, 2]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 2] - c[:, 2])
        ok = (n[:, 1] / L > 0.1) & ~np.isin(ids, A.IDALL_SKIP) & (np.abs(d) >= 1e-12)
        ti = np.nonzero(ok)[0]
        if ti.size == 0:
            continue
        for s0 in range(0, S, 2048):
            sl = np.arange(s0, min(S, s0 + 2048))
            sl = sl[unresolved[sl]]
            if sl.size == 0:
                continue
            A_, B_, C_, D_ = a[ti], b[ti], c[ti], d[ti]
            x = px[sl][None, :]
            z = pz[sl][None, :]
            w0 = ((B_[:, 2:3] - C_[:, 2:3]) * (x - C_[:, 0:1]) + (C_[:, 0:1] - B_[:, 0:1]) * (z - C_[:, 2:3])) / D_[:, None]
            w1 = ((C_[:, 2:3] - A_[:, 2:3]) * (x - C_[:, 0:1]) + (A_[:, 0:1] - C_[:, 0:1]) * (z - C_[:, 2:3])) / D_[:, None]
            w2 = 1 - w0 - w1
            ins = (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
            hit = ins.any(axis=0)
            if not hit.any():
                continue
            f = ins.argmax(axis=0)
            hs = np.nonzero(hit)[0]
            tf = f[hs]
            tri = ti[tf]
            idv = ids[tri]
            keep = idv != A.VETO
            hs, tf, tri, idv = hs[keep], tf[keep], tri[keep], idv[keep]
            hy = w0[tf, hs] * A_[tf, 1] + w1[tf, hs] * B_[tf, 1] + w2[tf, hs] * C_[tf, 1]
            g = sl[hs]
            out_id[g] = idv
            out_pi[g] = pi
            out_y[g] = hy
            unresolved[g] = False
    names = np.array([m[0] for m in meshes] + ["MISS"], dtype=object)
    part = names[np.where(out_pi < 0, len(meshes), out_pi)]
    return part, out_id, out_y, [m[0] for m in meshes]


def hist(arr, top=12):
    return dict(Counter(arr.tolist() if hasattr(arr, "tolist") else arr).most_common(top))


def rng(a):
    a = np.asarray(a, dtype=np.float64)
    a = a[np.isfinite(a)]
    if a.size == 0:
        return None
    return [round(float(a.min()), 3), round(float(np.median(a)), 3), round(float(a.max()), 3)]
