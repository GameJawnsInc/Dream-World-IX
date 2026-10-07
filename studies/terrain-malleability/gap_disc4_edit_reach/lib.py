"""Shared instruments for lane `gap_disc4_edit_reach` (terrain-malleability study).

READ-ONLY on the install. Every reader here uses EXACT container matching (the disc4 lane's MESH_RE), never
`extract.read_block`'s substring lookup, which collides sea4/sea4f and river/riverjoint
(disc4/verify_prefix_collision.py, D4-17).

Instruments:
  * mesh_objects()         {(disc, lod, x, y, part_lower): ObjectReader}, exact container match.
  * load_cache()           decoded Form-1 (0_1) meshes of BOTH discs, every real (cell, part), plus an
                           order-invariant all-channel triangle match. Built once, pickled OUTSIDE the repo
                           (it holds vertex positions = raw-ish geometry; provenance gate).
  * tri_key(...)           the all-channel triangle key: the 3 corners' raw vertex-record BYTES (every channel,
                           exactly as stored), rotated to a canonical start that PRESERVES winding, plus the
                           engine-read IDALL (tangent.x of buffer corner 0). Two meshes are an exact
                           permutation iff their key multisets are equal.
  * geo_key(...)           the same with POSITION bytes only (geometry match; attributes may differ).
  * ground(meshlist, x, z) placement.place (engine-faithful: registration order, first-hit buffer order,
                           IDALL 4078/4088/2040 skip, 0x31EE veto, ny>0.1 winding filter).
"""
from __future__ import annotations

import os
import pickle
import re
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
import numpy as np                                  # noqa: E402
from ff9mapkit.world import extract as X           # noqa: E402
from ff9mapkit.world import placement as P         # noqa: E402

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX"
LANE = Path(__file__).resolve().parent
OUT = LANE / "out"
OUT.mkdir(exist_ok=True)
D4OUT = LANE.parent / "disc4" / "out"
_SCRATCH = Path(r"C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX"
                r"\8b61f6d3-b0c2-4ade-9f22-b2bc267b1c8d\scratchpad")
CACHE_DIR = Path(os.environ.get("GAP_DISC4_CACHE") or
                 (_SCRATCH / "gap_disc4" if _SCRATCH.is_dir() else Path(tempfile.gettempdir()) / "gap_disc4"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE = CACHE_DIR / "cache_v2.pkl"

MESH_RE = re.compile(r"worldmap/disc(\d)/([0-9_]+)/r(\d+)/block\[(\d+)\]\[(\d+)\] ([a-z0-9_]+)(?:\.asset)?$")
WALK_PARTS = {p.lower() for p in P.REGISTRATION_ORDER}
CH = (X.CH_POS, X.CH_NRM, X.CH_UV, X.CH_TAN)   # the 4 channels a .ff9mesh override carries


def mesh_objects():
    env = X._worldmap_env(1, GAME)
    out = {}
    for c, o in X._mesh_index(env).items():
        m = MESH_RE.search(c)
        if m:
            d, lod, _r, x, y, part = m.groups()
            out[(int(d), lod, int(x), int(y), part)] = o
    return out


def decode(o, disc, x, y, lod="0_1"):
    from ff9mapkit.extract import env_lock
    with env_lock:
        return X._decode_world_mesh(o, disc=disc, x=x, y=y, lod=lod)


def raw_identical(a, b) -> bool:
    """discmirror._parts_identical's predicate, on decoded meshes (vcount, verts, index, uv, tangents, normals)."""
    return (a.vcount == b.vcount and a.verts == b.verts and a.flat_index == b.flat_index
            and a.uvs == b.uvs and a.tangents == b.tangents and a.normals == b.normals)


def _vrec(bm):
    """Per-vertex record bytes: the 4 override channels, float32-packed exactly as decoded."""
    import struct
    recs = []
    chans = [bm.chan_arrays.get(ci) for ci in CH]
    for i in range(bm.vcount):
        b = b""
        for arr in chans:
            if arr is not None:
                b += struct.pack("<%df" % len(arr[i]), *arr[i])
        recs.append(b)
    return recs


def _prec(bm):
    import struct
    return [struct.pack("<3f", *v) for v in bm.verts]


def _canon(c0, c1, c2):
    """Rotation to the lexicographically smallest start; preserves the cyclic (winding) order."""
    r = [(c0, c1, c2), (c1, c2, c0), (c2, c0, c1)]
    return min(r)


def tri_keys(bm, recs):
    fi = bm.flat_index
    tan = bm.tangents
    out = []
    for t in range(len(fi) // 3):
        a, b, c = fi[3 * t], fi[3 * t + 1], fi[3 * t + 2]
        idall = int(round(tan[a][0])) if tan else None
        out.append((_canon(recs[a], recs[b], recs[c]), idall))
    return out


def multiset_match(k1, k4):
    """Pair equal keys (multiset). Returns bool arrays m1, m4 (True = has an exact counterpart)."""
    pool = defaultdict(list)
    for j, k in enumerate(k4):
        pool[k].append(j)
    m1 = np.zeros(len(k1), bool)
    m4 = np.zeros(len(k4), bool)
    for i, k in enumerate(k1):
        lst = pool.get(k)
        if lst:
            j = lst.pop()
            m1[i] = True
            m4[j] = True
    return m1, m4


def _arrays(bm):
    V = np.asarray(bm.verts, dtype=np.float64)
    T = np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3)
    tan = bm.tangents
    ida = np.array([int(round(tan[T[t, 0]][0])) for t in range(len(T))], dtype=np.int64) if tan else None
    return V, T, ida


def build_cache(verbose=True):
    import time
    t0 = time.time()
    objs = mesh_objects()
    keys = sorted({(x, y, p) for (d, lod, x, y, p) in objs if lod == "0_1"})
    cells = sorted({(x, y) for (x, y, p) in keys})
    data = {"meshes": {}, "pairs": {}, "layout_mismatch": [], "extra_channels": Counter()}
    for (x, y, p) in keys:
        bms = {}
        for d in (1, 4):
            o = objs.get((d, "0_1", x, y, p))
            if o is None:
                continue
            bm = decode(o, d, x, y)
            bms[d] = bm
            for ci in bm.chan_arrays:
                if ci not in CH:
                    data["extra_channels"][ci] += 1
            V, T, ida = _arrays(bm)
            data["meshes"][(d, x, y, p)] = {"V": V, "T": T, "idall": ida, "name": bm.name,
                                            "vcount": bm.vcount}
        if len(bms) == 2:
            a, b = bms[1], bms[4]
            if a.channels != b.channels:
                data["layout_mismatch"].append((x, y, p))
            r1, r4 = _vrec(a), _vrec(b)
            k1, k4 = tri_keys(a, r1), tri_keys(b, r4)
            m1, m4 = multiset_match(k1, k4)
            g1k, g4k = tri_keys(a, _prec(a)), tri_keys(b, _prec(b))
            # geometry keys drop the idall component (position only)
            g1, g4 = multiset_match([k[0] for k in g1k], [k[0] for k in g4k])
            data["pairs"][(x, y, p)] = {
                "raw_identical": raw_identical(a, b),
                "n1": len(k1), "n4": len(k4), "m1": m1, "m4": m4, "g1": g1, "g4": g4,
                "perm": bool(m1.all() and m4.all()),
            }
        if verbose and len(data["meshes"]) % 200 < 2:
            print(f"  ... {len(data['meshes'])} meshes, {time.time() - t0:.0f}s", flush=True)
    data["cells"] = cells
    with open(CACHE, "wb") as fh:
        pickle.dump(data, fh, protocol=pickle.HIGHEST_PROTOCOL)
    if verbose:
        print(f"cache built: {len(data['meshes'])} meshes, {len(data['pairs'])} pairs, "
              f"{time.time() - t0:.0f}s -> {CACHE}")
    return data


def load_cache(rebuild=False):
    if CACHE.is_file() and not rebuild:
        with open(CACHE, "rb") as fh:
            return pickle.load(fh)
    return build_cache()


def blockmeshes(disc, x, y, objs=None, parts=None):
    """{part_lower: BlockMesh} for a real cell (exact containers), Form-1 tree."""
    objs = objs or mesh_objects()
    out = {}
    for (d, lod, xx, yy, p), o in objs.items():
        if d == disc and lod == "0_1" and (xx, yy) == (x, y) and (parts is None or p in parts):
            out[p] = decode(o, d, x, y)
    return out


def walk_meshlist(parts):
    keep = {k: v for k, v in parts.items() if k in WALK_PARTS}
    return P.build_meshlist(keep)


def topo(idall):
    return (idall & 0xFC) >> 2


def event(idall):
    return (idall & 0xC000) >> 14


def area(idall):
    return (idall & 0x3F00) >> 8


# ------------------------------------------------------------------------------------------------ delta transfer
def _pos_bytes(bm, vi):
    import struct
    return struct.pack("<3f", *bm.verts[vi])


def unmatched_positions(s1, s4):
    """World-free (block-local) vertex-position byte set of every triangle WITHOUT an exact all-channel
    counterpart on the other disc (S1-only and S4-only), i.e. the disc-diff footprint's vertices."""
    k1, k4 = tri_keys(s1, _vrec(s1)), tri_keys(s4, _vrec(s4))
    m1, m4 = multiset_match(k1, k4)
    out = set()
    for bm, m in ((s1, m1), (s4, m4)):
        fi = bm.flat_index
        for t in np.nonzero(~m)[0]:
            for k in range(3):
                out.add(_pos_bytes(bm, fi[3 * t + k]))
    return out


def delta_transfer(s1, e1, s4, *, forbidden=None, ring=1, support=None):
    """Strategy (iii): carry the disc-1 edit (s1 -> e1, same cell, same part) onto disc-4 stock s4 as a
    TRIANGLE delta: R = s1 tris not in e1 (multiset), A = e1 tris not in s1.

    Lawful iff (a) every R tri has an exact all-channel counterpart in s4, and (b) the edit's vertex
    footprint misses the disc-diff footprint: ring=1 -> no position of any R or A corner is a corner of an
    unmatched (S1-only / S4-only) tri; ring=0 -> only MOVED/ADDED positions (corners whose record changed)
    are tested -- the exact condition for a position-parametric edit. ``forbidden`` adds extra positions
    (block-local bytes) that must not be touched, e.g. a neighbour cell's unmatched border corners.

    ``support=(cx, cz, r)`` (block-LOCAL centre + radius) adds the geometric test a POSITION-PARAMETRIC edit
    needs: no unmatched corner strictly inside r. Vertex-sharing closure alone misses disc-4 OVERLAY geometry
    (new tris whose corners are shared with nothing) -- found by calibration K5 at (19,11).

    Result layout: s4's own vertex/index layout is kept; a topology-preserving edit (len(e1)==len(s1), the
    in-place reshape/retarget case) writes e1's corner bytes into the matched s4 slots corner-by-corner
    (so the output is BYTE-identical to replaying the same parametric op on s4); otherwise R counterparts
    are dropped and A appended. Returns (ok, reason, result_bm_or_None, stats)."""
    import copy
    import struct
    r1 = _vrec(s1)
    re1 = _vrec(e1)
    r4 = _vrec(s4)
    k1, ke, k4 = tri_keys(s1, r1), tri_keys(e1, re1), tri_keys(s4, r4)
    n1, n4 = len(k1), len(k4)
    topo_same = (len(ke) == n1 and e1.flat_index == s1.flat_index)
    if topo_same:
        R = [t for t in range(n1) if k1[t] != ke[t]]
        A = R[:]
    else:
        pool = defaultdict(list)
        for j, k in enumerate(ke):
            pool[k].append(j)
        R = []
        for i, k in enumerate(k1):
            if pool.get(k):
                pool[k].pop()
            else:
                R.append(i)
        A = sorted(j for lst in pool.values() for j in lst)
    stats = {"R": len(R), "A": len(A), "topology_preserving": topo_same}
    if not R and not A:
        return True, "identity", copy.deepcopy(s4), stats
    # pair S1 tris with S4 counterparts (exact all-channel multiset)
    pool4 = defaultdict(list)
    for j, k in enumerate(k4):
        pool4[k].append(j)
    for k in pool4:
        pool4[k].reverse()
    m1, m4 = multiset_match(k1, k4)
    pair = {}
    pool4b = {k: v[:] for k, v in pool4.items()}
    for i, k in enumerate(k1):
        if pool4b.get(k):
            pair[i] = pool4b[k].pop()
    miss = [i for i in R if i not in pair]
    if miss:
        return False, f"R-unmatched: {len(miss)} removed tri(s) have no disc-4 counterpart", None, stats
    fi1, fie, fi4 = s1.flat_index, e1.flat_index, s4.flat_index
    # footprint positions
    um = set()
    for bm, m in ((s1, m1), (s4, m4)):
        fi = bm.flat_index
        for t in np.nonzero(~m)[0]:
            for kk in range(3):
                um.add(_pos_bytes(bm, fi[3 * t + kk]))
    if forbidden:
        um |= set(forbidden)
    touched = set()
    if ring >= 1:
        for i in R:
            for kk in range(3):
                touched.add(_pos_bytes(s1, fi1[3 * i + kk]))
        for j in A:
            for kk in range(3):
                touched.add(_pos_bytes(e1, fie[3 * j + kk]))
    else:
        for i in R:                                       # only corners whose record changed / new corners
            for kk in range(3):
                a, b = fi1[3 * i + kk], (fie[3 * i + kk] if topo_same else None)
                if b is None or r1[a] != re1[b]:
                    touched.add(_pos_bytes(s1, a))
                    if b is not None:
                        touched.add(_pos_bytes(e1, b))
        if not topo_same:
            for j in A:
                for kk in range(3):
                    touched.add(_pos_bytes(e1, fie[3 * j + kk]))
    hit = touched & um
    stats["touched_positions"] = len(touched)
    stats["footprint_hits"] = len(hit)
    if hit:
        return False, f"footprint: the edit touches {len(hit)} disc-diff vertex position(s) (ring={ring})", None, stats
    if support is not None:
        # THE OVERLAY CASE: a disc-4-only tri whose corners are NEW positions shared with nothing (geometry laid
        # OVER the ground, e.g. a D4-08 ridge) is invisible to vertex-sharing closure; a parametric edit's
        # support must also contain no unmatched corner at all (strictly inside the radius = would move)
        import math as _m
        cx, cz, rr = support
        inside = 0
        for bm, m in ((s1, m1), (s4, m4)):
            fi = bm.flat_index
            for t in np.nonzero(~m)[0]:
                for kk in range(3):
                    v = bm.verts[fi[3 * t + kk]]
                    if _m.hypot(v[0] - cx, v[2] - cz) < rr:
                        inside += 1
        stats["unmatched_corners_in_support"] = inside
        if inside:
            return False, f"support: {inside} unmatched corner(s) strictly inside the edit radius", None, stats
    out = copy.deepcopy(s4)
    chans = [ci for ci in CH if ci in out.chan_arrays]
    if topo_same:
        for i in R:
            j = pair[i]
            src = {}
            for kk in range(3):
                src.setdefault(r1[fi1[3 * i + kk]], []).append(fie[3 * i + kk])
            for kk in range(3):
                slot = fi4[3 * j + kk]
                lst = src[r4[slot]]
                evi = lst.pop(0) if len(lst) > 1 else lst[0]
                for ci in chans:
                    out.chan_arrays[ci][slot] = list(e1.chan_arrays[ci][evi])
        return True, "ok", out, stats
    drop = {pair[i] for i in R}
    new_ca = {ci: [] for ci in chans}
    for j in range(n4):
        if j in drop:
            continue
        for kk in range(3):
            for ci in chans:
                new_ca[ci].append(list(s4.chan_arrays[ci][fi4[3 * j + kk]]))
    for j in A:
        for kk in range(3):
            for ci in chans:
                new_ca[ci].append(list(e1.chan_arrays[ci][fie[3 * j + kk]]))
    nv = len(new_ca[chans[0]])
    out.chan_arrays = new_ca
    out.flat_index = list(range(nv))
    out.tris = [out.flat_index[i:i + 3] for i in range(0, nv, 3)]
    out.vcount = nv
    return True, "ok", out, stats
