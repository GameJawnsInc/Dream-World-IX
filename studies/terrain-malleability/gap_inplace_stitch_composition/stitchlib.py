"""Shared instruments for lane gap_inplace_stitch_composition (terrain-malleability study).

READ-ONLY on the install. The decoded vertex cache is a RAW-DERIVED dump (world-frame positions + per-tri IDALL),
so it lives in the session SCRATCHPAD, never in the repo (provenance gate).

Instruments:
  * load_disc(disc)        -- every EXACT worldmap/disc{d}/0_1 block sub-mesh (anchored container regex, the
                              disc4/d4lib.mesh_objects pattern -- extract.read_block's substring lookup resolves
                              sea4->sea4f and river->riverjoint, disc4/verify_prefix_collision.py), decoded to
                              {(x, y, part): Mesh} with world-frame float64 positions, per-tri IDALL, and the
                              local-frame verts kept for walk queries. Cached as a pickle in SCRATCH.
  * wrap_key(p)            -- fold a world position onto the x/z torus (frames.wrap_world_xz semantics) and key it
                              EXACTLY (float64 of float32 data + integer block offsets is exact, no rounding).
  * neighbours(x, y)       -- the 4-neighbour blocks INCLUDING the x-seam (23<->0) and z-seam (19<->0) wraps.
"""
from __future__ import annotations

import math
import os
import pickle
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import extract as X          # noqa: E402

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX"
LANE = Path(__file__).resolve().parent
OUT = LANE / "out"
SCRATCH = Path(os.environ.get("STITCH_SCRATCH",
                              r"C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX"
                              r"\8b61f6d3-b0c2-4ade-9f22-b2bc267b1c8d\scratchpad\stitch"))
MESH_RE = re.compile(r"worldmap/disc(\d)/([0-9_]+)/r(\d+)/block\[(\d+)\]\[(\d+)\] ([a-z0-9_]+)(?:\.asset)?$")
GX, GY, B = 24, 20, 64.0
WX, WZ = GX * B, GY * B
TOL = 0.05                     # transplant/mesh.weld_audit near-miss tolerance
WATER = {"beach1", "beach2", "sea1", "sea2", "sea3", "sea4", "sea4f", "sea5", "sea6"}
RIVERISH = {"river", "riverjoint", "falls", "stream"}


class Mesh:
    __slots__ = ("disc", "x", "y", "part", "name", "lv", "wv", "idall", "fi")

    def __init__(self, disc, x, y, part, name, lv, idall, fi):
        self.disc, self.x, self.y, self.part, self.name = disc, x, y, part, name
        self.lv = lv                                          # local-frame verts (block frame)
        ox, oz = x * B, -y * B
        self.wv = [(v[0] + ox, v[1], v[2] + oz) for v in lv]  # world frame (unwrapped)
        self.idall = idall                                    # per vertex tangent.x (int)
        self.fi = fi                                          # flat index

    @property
    def ntri(self):
        return len(self.fi) // 3

    def tri_idall(self, t):
        return self.idall[self.fi[3 * t]]


def _exact_objects(disc):
    env = X._worldmap_env(disc, GAME)
    out = {}
    for c, o in X._mesh_index(env).items():
        m = MESH_RE.search(c)
        if m:
            d, lod, _r, x, y, part = m.groups()
            if int(d) == disc and lod == "0_1":
                out[(int(x), int(y), part)] = o
    return out


def load_disc(disc: int, *, verbose=True) -> dict:
    """{(x, y, part_lower): Mesh} for disc ``disc`` lod 0_1 -- exact containers. Pickle-cached in SCRATCH."""
    SCRATCH.mkdir(parents=True, exist_ok=True)
    cache = SCRATCH / f"disc{disc}_0_1.pkl"
    if cache.is_file():
        with open(cache, "rb") as fh:
            raw = pickle.load(fh)
        return {k: Mesh(*v) for k, v in raw.items()}
    t0 = time.time()
    from ff9mapkit.extract import env_lock
    objs = _exact_objects(disc)
    raw = {}
    for (x, y, part), o in sorted(objs.items()):
        with env_lock:
            bm = X._decode_world_mesh(o, disc=disc, x=x, y=y, lod="0_1")
        if not bm.verts:
            continue
        lv = [tuple(v) for v in bm.verts]
        ida = [int(round(t[0])) for t in bm.tangents] if bm.tangents else [0] * len(lv)
        raw[(x, y, part)] = (disc, x, y, part, bm.name, lv, ida, list(bm.flat_index))
    with open(cache, "wb") as fh:
        pickle.dump(raw, fh, protocol=pickle.HIGHEST_PROTOCOL)
    if verbose:
        print(f"[stitchlib] decoded disc {disc}: {len(raw)} meshes in {time.time() - t0:.1f}s -> {cache}")
    return {k: Mesh(*v) for k, v in raw.items()}


def wrap_key(p):
    """Exact torus fold of a world position: x -> [0,1536), z -> (-1280,0]; -0.0 normalized."""
    x = p[0] % WX
    z = -((-p[2]) % WZ)
    return (x + 0.0, p[1] + 0.0, z + 0.0)


def wrap_xz(x, z):
    return (x % WX) + 0.0, -((-z) % WZ) + 0.0


def neighbours(x, y):
    """4-neighbours on the torus: E, W, S, N (S = row+1 = -z)."""
    return [((x + 1) % GX, y, "E"), ((x - 1) % GX, y, "W"), (x, (y + 1) % GY, "S"), (x, (y - 1) % GY, "N")]


def decode(idall):
    return X.decode_id(int(idall))


def topo(idall):
    return (int(idall) & 0xFC) >> 2


def event(idall):
    return (int(idall) & 0xC000) >> 14


def blocks_with(meshes, part):
    return sorted({(x, y) for (x, y, p) in meshes if p == part})


def land_blocks(meshes):
    return blocks_with(meshes, "terrain")


def unique_positions(m: Mesh, wrap=True):
    s = set()
    for p in m.wv:
        s.add(wrap_key(p) if wrap else p)
    return s


def mesh_edges(m: Mesh):
    """Unique undirected edges of a flat mesh as (posA, posB) world-frame (unwrapped) tuples, plus
    the tri ids that own each edge (by exact position)."""
    owner = defaultdict(list)
    fi, V = m.fi, m.wv
    for t in range(len(fi) // 3):
        a, b, c = V[fi[3 * t]], V[fi[3 * t + 1]], V[fi[3 * t + 2]]
        for p, q in ((a, b), (b, c), (c, a)):
            k = (p, q) if p <= q else (q, p)
            owner[k].append(t)
    return owner


def seg_point_dist(p, a, b):
    """3D distance from p to segment ab, and the parameter t of the foot."""
    ax, ay, az = a
    dx, dy, dz = b[0] - ax, b[1] - ay, b[2] - az
    L2 = dx * dx + dy * dy + dz * dz
    if L2 <= 0:
        return math.dist(p, a), 0.0
    t = ((p[0] - ax) * dx + (p[1] - ay) * dy + (p[2] - az) * dz) / L2
    tc = min(1.0, max(0.0, t))
    fx, fy, fz = ax + tc * dx, ay + tc * dy, az + tc * dz
    return math.sqrt((p[0] - fx) ** 2 + (p[1] - fy) ** 2 + (p[2] - fz) ** 2), t


def seg_point_dist_xz(p, a, b):
    ax, az = a[0], a[2]
    dx, dz = b[0] - ax, b[2] - az
    L2 = dx * dx + dz * dz
    if L2 <= 0:
        return math.hypot(p[0] - ax, p[2] - az), 0.0, a[1]
    t = ((p[0] - ax) * dx + (p[2] - az) * dz) / L2
    tc = min(1.0, max(0.0, t))
    fx, fz = ax + tc * dx, az + tc * dz
    return math.hypot(p[0] - fx, p[2] - fz), t, a[1] + tc * (b[1] - a[1])


def save_json(name, obj):
    import json
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / name
    p.write_text(json.dumps(obj, indent=1, default=str), encoding="utf-8")
    return p
