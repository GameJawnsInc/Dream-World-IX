"""FF9 walkmesh (``.bgi.bytes``) codec + a flat-floor builder.

The ``.bgi`` describes the invisible walkable geometry: a set of triangles (with vertex /
edge / neighbor links so the engine can path and detect borders), grouped into floors. This
module mirrors Memoria's ``BGI_DEF`` read/write exactly, so :meth:`BgiWalkmesh.to_bytes`
round-trips any real ``.bgi`` byte-for-byte, and adds:

  * :func:`build_flat` — construct a complete ``.bgi`` from world-space vertices + triangle
    faces (the human's Blender walkmesh, flat y=0 floor). Computes triangle centers, the
    per-triangle edge entries, the neighbor/edgeClone links, and a single floor. This removes
    the dependency on Memoria's in-editor ``ConvertToBGI``.
  * :func:`load_obj` — read a Wavefront ``.obj`` (vertices in FF9 world coords, faces).
  * :meth:`BgiWalkmesh.rebuild_neighbors` — recompute all neighbor/edgeClone links from
    shared-vertex analysis (the ``bgi_fix_neighbors`` fix: ``ConvertToBGI`` links unreliably).

File layout (little-endian; offsets in the header are relative to byte 4):
    magic u32 = 0xACDCDEAD ; dataSize u16 ;
    orgPos curPos minPos maxPos charPos : BGI_VEC (3xi16 each) ;
    activeFloor i16 ; activeTri i16 ;
    {tri,edge,anm,floor,normal,vertex} x (count u16, offset u16) ;
    sections in order: tris(40B) edges(4B) anms(16B) floors(32B) normals(16B) verts(6B)
                       then per-anm frames(8B), per-floor triNdx int32 list, per-frame triNdx.
"""

from __future__ import annotations

import struct
from collections import deque
from dataclasses import dataclass, field

MAGIC = 0xACDCDEAD
# THE FRAME (confirmed from Memoria source -- WalkMesh.cs:53,141,227):
#     world_vertex = vertexList[i] + floor.org + bgi.orgPos          (collision uses *.cur, equal
#                                                                      to *.org for a static field)
# So orgPos and each floor.org ARE a render/collision transform, NOT mere bookkeeping. A real .bgi
# stores each FLOOR's verts CORNER-ORIGIN in the floor's own frame and tiles them with floor.org,
# with bgi.orgPos placing the whole mesh in the world (== header.minPos by convention). The IMPORTER
# inverts this in BgiWalkmesh.world_verts(); this EXPORTER is its inverse: for authored/edited
# WORLD-coordinate geometry it emits orgPos=0 and every floor.org=0, so world_vertex = vertexList[i]
# verbatim -- what you author is exactly where the engine renders it. (header.minPos/maxPos and the
# per-floor min/max are loaded but UNUSED at runtime -- WavefrontObject.cs sets them, nothing reads
# them; charPos is the debug spawn. Verified in-game across GLGV/GRGR/BRMC/BMVL, 1..7 floors.)
HEADER_SIZE = 64           # magic+dataSize+5*vec(30)+activeFloor/Tri(4)+12*u16(24)
FIRST_SECTION_REL = 0x3C   # triOffset (relative to byte 4)
TRI_SIZE, EDGE_SIZE, ANM_SIZE, FLOOR_SIZE, NORMAL_SIZE, VERT_SIZE = 40, 4, 16, 32, 16, 6

# slot -> the pair of triangle-local vertex indices forming that edge (BGI convention)
SLOT_PAIRS = [(0, 2), (0, 1), (1, 2)]


def _pt_in_tri_xz(px, pz, a, b, c) -> bool:
    """(px,pz) inside-or-on triangle (a,b,c) using only X and Z (top-down). Same-sign barycentric.

    The three cross products are written out rather than folded into a helper: this is the innermost
    call of every walkmesh query (the auto-router probes it millions of times per build), and the
    operand order is kept EXACTLY as the closure computed it so the float results stay bit-identical."""
    ax, az = a[0], a[2]
    bx, bz = b[0], b[2]
    cx, cz = c[0], c[2]
    d1 = (px - bx) * (az - bz) - (ax - bx) * (pz - bz)
    d2 = (px - cx) * (bz - cz) - (bx - cx) * (pz - cz)
    d3 = (px - ax) * (cz - az) - (cx - ax) * (pz - az)
    return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))


def _pt_seg_dist_xz(px, pz, a, b) -> float:
    """Distance from (px,pz) to segment a-b in the XZ plane (Y ignored)."""
    ax, az, bx, bz = a[0], a[2], b[0], b[2]
    dx, dz = bx - ax, bz - az
    l2 = dx * dx + dz * dz
    t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / l2))
    cx, cz = ax + t * dx, az + t * dz
    return ((px - cx) ** 2 + (pz - cz) ** 2) ** 0.5


def _i16(b, o):
    return struct.unpack_from("<h", b, o)[0]


def _u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def _i32(b, o):
    return struct.unpack_from("<i", b, o)[0]


@dataclass
class Vec3:
    x: int = 0
    y: int = 0
    z: int = 0

    def pack(self) -> bytes:
        return struct.pack("<hhh", self.x, self.y, self.z)

    @classmethod
    def read(cls, b, o):
        return cls(_i16(b, o), _i16(b, o + 2), _i16(b, o + 4))


@dataclass
class FVec:
    coord: tuple = (0, 0, 0)
    one_over_y: int = 0

    def pack(self) -> bytes:
        return struct.pack("<iiii", self.coord[0], self.coord[1], self.coord[2], self.one_over_y)

    @classmethod
    def read(cls, b, o):
        return cls((_i32(b, o), _i32(b, o + 4), _i32(b, o + 8)), _i32(b, o + 12))


@dataclass
class Tri:
    tri_flags: int = 1
    tri_data: int = 0
    floor_ndx: int = 0
    normal_ndx: int = -1
    theta_x: int = 0
    theta_z: int = 0
    vtx: list = field(default_factory=lambda: [0, 0, 0])
    edge: list = field(default_factory=lambda: [0, 0, 0])
    nbr: list = field(default_factory=lambda: [-1, -1, -1])
    center: Vec3 = field(default_factory=Vec3)
    d: int = 0

    def pack(self) -> bytes:
        return (struct.pack("<HHhhhh", self.tri_flags, self.tri_data, self.floor_ndx,
                            self.normal_ndx, self.theta_x, self.theta_z)
                + struct.pack("<hhh", *self.vtx)
                + struct.pack("<hhh", *self.edge)
                + struct.pack("<hhh", *self.nbr)
                + self.center.pack()
                + struct.pack("<i", self.d))

    @classmethod
    def read(cls, b, o):
        t = cls()
        t.tri_flags, t.tri_data, t.floor_ndx, t.normal_ndx, t.theta_x, t.theta_z = \
            struct.unpack_from("<HHhhhh", b, o)
        t.vtx = list(struct.unpack_from("<hhh", b, o + 12))
        t.edge = list(struct.unpack_from("<hhh", b, o + 18))
        t.nbr = list(struct.unpack_from("<hhh", b, o + 24))
        t.center = Vec3.read(b, o + 30)
        t.d = _i32(b, o + 36)
        return t


@dataclass
class Edge:
    flags: int = 0
    clone: int = -1

    def pack(self) -> bytes:
        return struct.pack("<Hh", self.flags, self.clone)

    @classmethod
    def read(cls, b, o):
        return cls(_u16(b, o), _i16(b, o + 2))


@dataclass
class Floor:
    flags: int = 0
    ndx: int = 0
    org: Vec3 = field(default_factory=Vec3)
    cur: Vec3 = field(default_factory=Vec3)
    min: Vec3 = field(default_factory=Vec3)
    max: Vec3 = field(default_factory=Vec3)
    tri_ndx_list: list = field(default_factory=list)

    def pack_struct(self, tri_ndx_offset: int) -> bytes:
        return (struct.pack("<HH", self.flags, self.ndx)
                + self.org.pack() + self.cur.pack() + self.min.pack() + self.max.pack()
                + struct.pack("<HH", len(self.tri_ndx_list), tri_ndx_offset))


@dataclass
class Anm:
    flags: int = 0
    frame_rate: int = 0
    counter: int = 0
    cur_frame: int = 0
    frames: list = field(default_factory=list)  # list of (flags, value, tri_idx_list)


class BgiWalkmesh:
    def __init__(self):
        self.orgPos = Vec3(0, 0, 300)
        self.curPos = Vec3(0, 0, 300)
        self.minPos = Vec3(0, 0, 300)
        self.maxPos = Vec3(0, 0, 300)
        self.charPos = Vec3(0, 0, 300)
        self.activeFloor = 0
        self.activeTri = 0
        self.tris: list[Tri] = []
        self.edges: list[Edge] = []
        self.anms: list[Anm] = []
        self.floors: list[Floor] = []
        self.normals: list[FVec] = []
        self.verts: list[Vec3] = []
        self._cache: dict = {}

    # ---------------- derived-geometry cache ----------------
    # `world_verts()` / `_tri_floor()` are pure functions of (verts, floors, tris.vtx, orgPos), yet the
    # placement queries below rebuilt BOTH on every single call -- and the auto-router
    # (`content.pathfind`) probes those queries tens of thousands of times per routed leg, so a
    # 60-unit field spent ~44s of a build re-deriving the same 237 vertices. They are memoised here,
    # behind a cheap STRUCTURAL SIGNATURE: every in-repo path that changes this geometry does so while
    # BUILDING a mesh (`from_bytes` and `build` append to the section lists), so the section counts +
    # orgPos catch it. The two methods that mutate an EXISTING mesh -- `rebuild_neighbors` and
    # `apply_seams` -- touch only `nbr`/`edgeClone`, which the signature cannot see and the WALL cache
    # depends on, so they drop the cache explicitly. Anything else editing a live mesh in place must
    # call `invalidate_cache()`.
    def _sig(self):
        op = self.orgPos
        return (len(self.verts), len(self.tris), len(self.floors), len(self.edges),
                op.x, op.y, op.z)

    def invalidate_cache(self) -> None:
        """Drop the derived-geometry caches (world verts, vert/tri->floor, the point-lookup grid, the
        per-floor wall edges). Only needed after mutating verts/tris/floors/edges IN PLACE -- adding
        or removing whole entries is caught automatically by the structural signature."""
        self._cache = {}

    def _derived(self) -> dict:
        c = getattr(self, "_cache", None)
        sig = self._sig()
        if c is None or c.get("sig") != sig:
            c = self._cache = {"sig": sig}
        return c

    def _vfm(self) -> dict:
        """The SHARED `vert_floor_map()` -- internal, treat as read-only."""
        c = self._derived()
        m = c.get("vfm")
        if m is None:
            m = {}
            for fi, fl in enumerate(self.floors):
                for ti in fl.tri_ndx_list:
                    if 0 <= ti < len(self.tris):
                        for vi in self.tris[ti].vtx:
                            m[vi] = fi
            c["vfm"] = m
        return m

    def _wv(self) -> list:
        """The SHARED `world_verts()` -- internal, treat as read-only."""
        c = self._derived()
        out = c.get("wv")
        if out is None:
            vf = self._vfm()
            op = self.orgPos
            out = []
            for i, v in enumerate(self.verts):
                fi = vf.get(i)
                fo = self.floors[fi].org if (fi is not None and fi < len(self.floors)) else Vec3(0, 0, 0)
                out.append((v.x + op.x + fo.x, v.y + op.y + fo.y, v.z + op.z + fo.z))
            c["wv"] = out
        return out

    def _tf(self) -> dict:
        """The SHARED `_tri_floor()` -- internal, treat as read-only."""
        c = self._derived()
        m = c.get("tf")
        if m is None:
            m = c["tf"] = {ti: fi for fi, fl in enumerate(self.floors) for ti in fl.tri_ndx_list}
        return m

    def _grid(self):
        """Uniform XZ bucket grid over the triangles: ``(x0, z0, x1, z1, sx, sz, nx, nz, buckets)``.

        ``buckets[j * nx + i]`` lists -- in ASCENDING triangle index order -- every triangle whose XZ
        bounding box overlaps that cell. A point can only lie in a triangle whose bbox contains it, so
        testing just the point's own cell is EXACT: the bucket is a superset of the true matches,
        containment is still decided by :func:`_pt_in_tri_xz`, and triangle order is preserved -- so
        the queries below return the same FIRST match as the full scans they replace. ``None`` for an
        empty mesh (callers fall back to scanning every triangle)."""
        c = self._derived()
        if "grid" in c:
            return c["grid"]
        wv, tris = self._wv(), self.tris
        g = None
        if wv and tris:
            x0 = x1 = wv[0][0]
            z0 = z1 = wv[0][2]
            for v in wv:
                if v[0] < x0:
                    x0 = v[0]
                elif v[0] > x1:
                    x1 = v[0]
                if v[2] < z0:
                    z0 = v[2]
                elif v[2] > z1:
                    z1 = v[2]
            n = max(1, min(64, 2 * int(len(tris) ** 0.5)))
            nx = nz = n
            sx = (x1 - x0) / nx or 1.0
            sz = (z1 - z0) / nz or 1.0
            buckets = [None] * (nx * nz)
            nv = len(wv)
            for ti, t in enumerate(tris):
                a, b, cc = t.vtx[0], t.vtx[1], t.vtx[2]
                if not (0 <= a < nv and 0 <= b < nv and 0 <= cc < nv):
                    continue                       # malformed tri: it can never contain a point
                pa, pb, pc = wv[a], wv[b], wv[cc]
                i0 = int((min(pa[0], pb[0], pc[0]) - x0) / sx)
                i1 = int((max(pa[0], pb[0], pc[0]) - x0) / sx)
                j0 = int((min(pa[2], pb[2], pc[2]) - z0) / sz)
                j1 = int((max(pa[2], pb[2], pc[2]) - z0) / sz)
                i0 = 0 if i0 < 0 else (nx - 1 if i0 > nx - 1 else i0)
                i1 = 0 if i1 < 0 else (nx - 1 if i1 > nx - 1 else i1)
                j0 = 0 if j0 < 0 else (nz - 1 if j0 > nz - 1 else j0)
                j1 = 0 if j1 < 0 else (nz - 1 if j1 > nz - 1 else j1)
                for j in range(j0, j1 + 1):
                    row = j * nx
                    for i in range(i0, i1 + 1):
                        k = row + i
                        if buckets[k] is None:
                            buckets[k] = [ti]
                        else:
                            buckets[k].append(ti)
            g = (x0, z0, x1, z1, sx, sz, nx, nz, buckets)
        c["grid"] = g
        return g

    def _lookup(self):
        """``(world_verts, tri_floor, grid)`` in ONE cache probe -- the placement queries need all
        three per call, and re-deriving the cache signature for each was pure overhead at A* volume."""
        c = self._derived()
        lk = c.get("lookup")
        if lk is None:
            lk = c["lookup"] = (self._wv(), self._tf(), self._grid())
        return lk

    def _candidates(self, x, z, g=False):
        """Triangle indices that could contain (x, z), ascending. Empty when the point is outside the
        mesh bbox -- exact, since a containing triangle's own bbox would have to contain the point.

        ``g`` optionally passes an already-fetched grid (``False`` means "not supplied"; ``None`` is
        the meaningful "this mesh has no grid, scan everything" value)."""
        if g is False:
            g = self._grid()
        if g is None:
            return range(len(self.tris))
        x0, z0, x1, z1, sx, sz, nx, nz, buckets = g
        if x < x0 or x > x1 or z < z0 or z > z1:
            return ()
        i = int((x - x0) / sx)
        j = int((z - z0) / sz)
        i = 0 if i < 0 else (nx - 1 if i > nx - 1 else i)
        j = 0 if j < 0 else (nz - 1 if j > nz - 1 else j)
        return buckets[j * nx + i] or ()

    def _wall_segs(self) -> dict:
        """floor index -> its collision-WALL edges, in the exact (triangle index, slot) order
        :meth:`distance_to_boundary` scans them in, each pre-reduced to ``(ax, az, dx, dz, l2)``.

        The segment delta and its squared length depend only on the EDGE, but the old scan recomputed
        both for every probe (millions per routed build). They are lifted here; the per-probe arithmetic
        that remains is byte-for-byte the arithmetic :func:`_pt_seg_dist_xz` performs."""
        c = self._derived()
        w = c.get("walls")
        if w is None:
            wv, tf = self._wv(), self._tf()
            w = {}
            nv = len(wv)
            for ti, t in enumerate(self.tris):
                lst = w.setdefault(tf.get(ti, t.floor_ndx), [])
                for k in range(3):
                    if t.nbr[k] >= 0:              # neighbor across this edge -> not a wall
                        continue
                    i, j = SLOT_PAIRS[k]
                    a, b = t.vtx[i], t.vtx[j]
                    if 0 <= a < nv and 0 <= b < nv:
                        pa, pb = wv[a], wv[b]
                        ax, az, bx, bz = pa[0], pa[2], pb[0], pb[2]
                        dx, dz = bx - ax, bz - az
                        lst.append((ax, az, dx, dz, dx * dx + dz * dz))
            c["walls"] = w
        return w

    # ---------------- world transform (corner-origin per-floor -> world) ----------------
    def vert_floor_map(self) -> dict:
        """vert index -> floor index. A real .bgi gives each floor a DISJOINT vertex set, so this
        is well-defined; unowned verts map to floor 0."""
        return dict(self._vfm())

    def world_verts(self):
        """World (camera/art/engine) position of each vertex = vert + header.orgPos + its floor.org.

        Each FLOOR stores its verts CORNER-ORIGIN in the floor's own frame; `floor.org` tiles the
        floors and the header `orgPos` places the whole walkmesh in the world. Verified: this lands
        every GRGR vert exactly inside the header [minPos,maxPos] and tiles its 7 floors into a
        coherent centred tunnel. Single-floor fields have floor.org=(0,0,0), so this reduces to
        vert + orgPos (GLGV unchanged). This is the exact transform the EXPORTER inverts."""
        return list(self._wv())

    # ---------------- connectivity (the navmesh adjacency graph) ----------------
    def all_floors(self) -> set:
        return {t.floor_ndx for t in self.tris}

    def reachable_floors(self, start_tri: int | None = None) -> set:
        """Floor indices walk-reachable from start_tri (default activeTri) by following triangle
        neighbor links -- the SAME links the engine pathfinds over. If this is a strict subset of
        all_floors(), some floors are stranded (unreachable on foot).

        This is the build-time guard for the obj->build connectivity loss: a multi-floor walkmesh
        gives each floor a DISJOINT vertex set, so rebuild_neighbors (which links by shared vertex
        index) can only connect within a floor -- cross-floor seams vanish and the player is trapped.
        The .bgi codec itself preserves the original links; only the obj intermediate drops them."""
        start = start_tri if start_tri is not None else self.activeTri
        if not (0 <= start < len(self.tris)):
            start = 0
        seen, q = set(), deque([start])
        while q:
            t = q.popleft()
            if t in seen or not (0 <= t < len(self.tris)):
                continue
            seen.add(t)
            for n in self.tris[t].nbr:
                if n >= 0:
                    q.append(n)
        return {self.tris[t].floor_ndx for t in seen}

    def tri_components(self) -> list:
        """Connected components of triangles by neighbor links -- each a list of triangle indices. A walkmesh
        that splits into >1 component has walled-off regions (e.g. a shop counter separating the customer area
        from the behind-counter pocket); the largest on-screen component is the player's free-roam area, so a
        fork should spawn there (not stranded in a pocket). Single-region walkmesh -> one component."""
        seen, comps = set(), []
        for s in range(len(self.tris)):
            if s in seen:
                continue
            comp, q = [], deque([s])
            while q:
                t = q.popleft()
                if t in seen or not (0 <= t < len(self.tris)):
                    continue
                seen.add(t)
                comp.append(t)
                for n in self.tris[t].nbr:
                    if n >= 0:
                        q.append(n)
            comps.append(comp)
        return comps

    # ---------------- seam extract / reconcile (the editable-multi-floor sidecar; WALKMESH_EDITING.md) ----------------
    def _tri_floor(self) -> dict:
        return dict(self._tf())

    def _edge_world_pos(self, wv, ti, slot):
        """The slot's edge as a sorted pair of world positions (a stable, renumber-proof key)."""
        i, j = SLOT_PAIRS[slot]
        return tuple(sorted((wv[self.tris[ti].vtx[i]], wv[self.tris[ti].vtx[j]])))

    def extract_seams(self):
        """Cross-floor seams as (a_floor, a_edge, b_floor, b_edge); each edge a sorted world-position
        pair. This is the adjacency a geometry-only `.obj` can't carry (rebuild_neighbors links only
        within a floor, and FF9 floors use disjoint vertex sets). Pair with `apply_seams` to reconcile
        an edited obj against an imported field. Validated game-wide (tools/sweep_seams.py)."""
        wv = self._wv()
        fo = self._tf()
        seams, seen = [], set()
        for ti, t in enumerate(self.tris):
            fa = fo.get(ti)
            for k in range(3):
                nb = t.nbr[k]
                if nb < 0 or nb >= len(self.tris) or fo.get(nb) == fa:
                    continue
                key = (min(ti, nb), max(ti, nb))
                if key in seen:
                    continue
                seen.add(key)
                ec = self.edges[t.edge[k]].clone if 0 <= t.edge[k] < len(self.edges) else -1
                a = self._edge_world_pos(wv, ti, k)
                b = self._edge_world_pos(wv, nb, ec) if 0 <= ec < 3 else None
                seams.append((fa, a, fo.get(nb), b))
        return seams

    def apply_seams(self, seams):
        """Link cross-floor neighbors by matching each seam's edge endpoints by WORLD POSITION (this
        mesh already has intra-floor links from `bgi.build`). Sets `nbr` + `edgeClone` on both sides,
        the same convention as `rebuild_neighbors`. Returns (linked, missing, misses) -- a miss means
        a seam's connecting edge was moved/deleted in the edit. The v2 reconcile."""
        wv = self._wv()
        fo = self._tf()
        lut = {}
        for ti in range(len(self.tris)):
            for k in range(3):
                lut[(fo[ti], self._edge_world_pos(wv, ti, k))] = (ti, k)
        linked = missing = 0
        misses = []
        for (fa, a_edge, fb, b_edge) in seams:
            ta = lut.get((fa, a_edge))
            tb = lut.get((fb, b_edge)) if b_edge else None
            if ta and tb:
                (ia, sa), (ib, sb) = ta, tb
                self.tris[ia].nbr[sa] = ib
                self.tris[ib].nbr[sb] = ia
                self.edges[self.tris[ia].edge[sa]].clone = sb
                self.edges[self.tris[ib].edge[sb]].clone = sa
                linked += 1
            else:
                missing += 1
                misses.append((fa, a_edge, fb, b_edge))
        self.invalidate_cache()        # nbr/edgeClone moved: the wall set is now stale
        return linked, missing, misses

    # ---------------- placement / geometry validation (catch authoring mistakes pre-build) ----------------
    def point_on_walkmesh(self, x, z):
        """Floor index of the triangle whose XZ-projection contains (x, z), else None. Validates that
        authored content (NPC / player spawn / gateway zone) sits on the walkable area before build --
        a top-down point-in-triangle test (multi-floor fields can overlap in XZ; returns first match)."""
        wv, tf, grid = self._lookup()
        tris = self.tris
        for ti in self._candidates(x, z, grid):    # bbox-bucketed superset, ascending -- same first match
            t = tris[ti]
            if _pt_in_tri_xz(x, z, wv[t.vtx[0]], wv[t.vtx[1]], wv[t.vtx[2]]):
                return tf.get(ti, t.floor_ndx)
        return None

    def height_at(self, x, z):
        """The floor Y (world height) at (x, z): the triangle whose XZ-projection contains (x, z),
        barycentric-interpolated from its 3 verts. None if off-mesh. A navigable ladder's dismount must
        land at the floor's REAL height -- otherwise the jump arcs to Y=0 and SetPathing snaps you up
        (the fall+slingshot). Lets the builder auto-fill an omitted floor_landing/top_landing Y."""
        wv, _tf, grid = self._lookup()
        tris = self.tris
        for ti in self._candidates(x, z, grid):    # same ascending order as the full scan
            t = tris[ti]
            a, b, c = wv[t.vtx[0]], wv[t.vtx[1]], wv[t.vtx[2]]   # each vert = (x, y, z)
            if _pt_in_tri_xz(x, z, a, b, c):
                den = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
                if den == 0:
                    return int(round(a[1]))
                wa = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / den
                wb = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / den
                return int(round(wa * a[1] + wb * b[1] + (1 - wa - wb) * c[1]))
        return None

    def distance_to_boundary(self, x, z):
        """Min XZ distance from (x,z) to the nearest collision WALL of the floor it sits on -- a
        walkmesh-boundary edge (one with no neighbor across it). A cross-floor SEAM is NOT a wall
        (the player crosses it to the next floor), so a seamed edge is skipped. Returns None if the
        point is off the walkmesh. The player's CENTRE can't get within ~COLLISION_RADIUS_W of a
        wall, so content closer than that to an edge may be unreachable / shoved inward in-game."""
        floor = self.point_on_walkmesh(x, z)
        if floor is None:
            return None
        best = None
        for (ax, az, dx, dz, l2) in self._wall_segs().get(floor, ()):   # this floor's walls only
            # _pt_seg_dist_xz inlined against the pre-reduced segment (identical operations/order):
            # this is the innermost loop of every auto-routed build.
            if l2 == 0:
                t = 0.0
            else:
                t = ((x - ax) * dx + (z - az) * dz) / l2
                if t < 0.0:
                    t = 0.0
                elif t > 1.0:
                    t = 1.0
            cx, cz = ax + t * dx, az + t * dz
            d = ((x - cx) ** 2 + (z - cz) ** 2) ** 0.5
            if best is None or d < best:
                best = d
        return best

    def degenerate_tris(self):
        """Triangle indices with ~zero XZ area -- collinear/vertical verts make a DEAD ZONE in the
        engine's IsInQuad fan test (the player can't stand there). Almost always an editing mistake."""
        wv = self._wv()
        out = []
        for ti, t in enumerate(self.tris):
            a, b, c = wv[t.vtx[0]], wv[t.vtx[1]], wv[t.vtx[2]]
            if (b[0] - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (b[2] - a[2]) == 0:
                out.append(ti)
        return out

    # ---------------- parse ----------------
    @classmethod
    def from_bytes(cls, data: bytes) -> "BgiWalkmesh":
        b = bytes(data)
        if struct.unpack_from("<I", b, 0)[0] != MAGIC:
            raise ValueError("not a .bgi (bad magic)")
        self = cls()
        self.orgPos = Vec3.read(b, 6)
        self.curPos = Vec3.read(b, 12)
        self.minPos = Vec3.read(b, 18)
        self.maxPos = Vec3.read(b, 24)
        self.charPos = Vec3.read(b, 30)
        self.activeFloor = _i16(b, 36)
        self.activeTri = _i16(b, 38)
        triCount, triOff = _u16(b, 40), _u16(b, 42)
        edgeCount, edgeOff = _u16(b, 44), _u16(b, 46)
        anmCount, anmOff = _u16(b, 48), _u16(b, 50)
        floorCount, floorOff = _u16(b, 52), _u16(b, 54)
        normalCount, normalOff = _u16(b, 56), _u16(b, 58)
        vertexCount, vertexOff = _u16(b, 60), _u16(b, 62)
        for i in range(triCount):
            self.tris.append(Tri.read(b, 4 + triOff + i * TRI_SIZE))
        for i in range(edgeCount):
            self.edges.append(Edge.read(b, 4 + edgeOff + i * EDGE_SIZE))
        raw_anms = []
        for i in range(anmCount):
            o = 4 + anmOff + i * ANM_SIZE
            flags, fcount, frate, counter = struct.unpack_from("<HHhH", b, o)
            curframe = _i32(b, o + 8)
            foff = struct.unpack_from("<I", b, o + 12)[0]
            raw_anms.append((flags, fcount, frate, counter, curframe, foff))
        for i in range(floorCount):
            o = 4 + floorOff + i * FLOOR_SIZE
            fl = Floor()
            fl.flags, fl.ndx = struct.unpack_from("<HH", b, o)
            fl.org = Vec3.read(b, o + 4)
            fl.cur = Vec3.read(b, o + 10)
            fl.min = Vec3.read(b, o + 16)
            fl.max = Vec3.read(b, o + 22)
            tcount, toff = struct.unpack_from("<HH", b, o + 28)
            fl.tri_ndx_list = [_i32(b, 4 + toff + k * 4) for k in range(tcount)]
            self.floors.append(fl)
        for i in range(normalCount):
            self.normals.append(FVec.read(b, 4 + normalOff + i * NORMAL_SIZE))
        for i in range(vertexCount):
            self.verts.append(Vec3.read(b, 4 + vertexOff + i * VERT_SIZE))
        # anm frames (after vertices); preserved for round-trip fidelity
        for (flags, fcount, frate, counter, curframe, foff) in raw_anms:
            a = Anm(flags, frate, counter, curframe)
            for j in range(fcount):
                fo = 4 + foff + j * 8
                fflags, value, tcount, toff = struct.unpack_from("<HhHH", b, fo)
                idxs = [_i32(b, 4 + toff + k * 4) for k in range(tcount)]
                a.frames.append((fflags, value, idxs))
            self.anms.append(a)
        return self

    @classmethod
    def from_file(cls, path) -> "BgiWalkmesh":
        with open(path, "rb") as fh:
            return cls.from_bytes(fh.read())

    # ---------------- serialize (mirrors BGI_DEF.WriteData + UpdateOffsets) ----------------
    def to_bytes(self) -> bytes:
        triCount, edgeCount = len(self.tris), len(self.edges)
        anmCount, floorCount = len(self.anms), len(self.floors)
        normalCount, vertexCount = len(self.normals), len(self.verts)

        off = FIRST_SECTION_REL
        triOff = off; off += TRI_SIZE * triCount
        edgeOff = off; off += EDGE_SIZE * edgeCount
        anmOff = off; off += ANM_SIZE * anmCount
        floorOff = off; off += FLOOR_SIZE * floorCount
        normalOff = off; off += NORMAL_SIZE * normalCount
        vertexOff = off; off += VERT_SIZE * vertexCount
        # per-anm frame tables
        frame_offsets = []
        for a in self.anms:
            frame_offsets.append(off); off += 8 * len(a.frames)
        # per-floor tri-index lists
        floor_list_offsets = []
        for fl in self.floors:
            floor_list_offsets.append(off); off += 4 * len(fl.tri_ndx_list)
        # per-frame tri-index lists
        frame_list_offsets = []
        for ai, a in enumerate(self.anms):
            row = []
            for (_f, _v, idxs) in a.frames:
                row.append(off); off += 4 * len(idxs)
            frame_list_offsets.append(row)
        data_size = off

        out = bytearray()
        out += struct.pack("<IH", MAGIC, data_size & 0xFFFF)
        for v in (self.orgPos, self.curPos, self.minPos, self.maxPos, self.charPos):
            out += v.pack()
        out += struct.pack("<hh", self.activeFloor, self.activeTri)
        out += struct.pack("<HHHHHHHHHHHH",
                           triCount, triOff, edgeCount, edgeOff, anmCount, anmOff,
                           floorCount, floorOff, normalCount, normalOff, vertexCount, vertexOff)
        assert len(out) == HEADER_SIZE, len(out)
        # the writer seeks to absolute offsets; our sections are contiguous in the same order,
        # so we can simply append. Pad to data_size+4 at the end.
        for t in self.tris:
            out += t.pack()
        for e in self.edges:
            out += e.pack()
        for ai, a in enumerate(self.anms):
            out += struct.pack("<HHhHiI", a.flags, len(a.frames), a.frame_rate, a.counter,
                               a.cur_frame, frame_offsets[ai])
        for fi, fl in enumerate(self.floors):
            out += fl.pack_struct(floor_list_offsets[fi])
        for nrm in self.normals:
            out += nrm.pack()
        for v in self.verts:
            out += v.pack()
        # trailing variable-length tables, in UpdateOffsets order: anm frames, floor lists, frame lists
        for ai, a in enumerate(self.anms):
            for fj, (fflags, value, idxs) in enumerate(a.frames):
                out += struct.pack("<HhHH", fflags, value, len(idxs), frame_list_offsets[ai][fj])
        for fi, fl in enumerate(self.floors):
            for idx in fl.tri_ndx_list:
                out += struct.pack("<i", idx)
        for ai, a in enumerate(self.anms):
            for (fflags, value, idxs) in a.frames:
                for idx in idxs:
                    out += struct.pack("<i", idx)
        return bytes(out)

    # ---------------- neighbor rebuild (bgi_fix_neighbors) ----------------
    def rebuild_neighbors(self) -> None:
        """Recompute all neighbor + edgeClone links from shared-vertex analysis."""
        self.invalidate_cache()        # links change under us; also covers the non-manifold raise below
        for t in self.tris:
            t.nbr = [-1, -1, -1]
        for e in self.edges:
            e.clone = -1

        def slot_of(tri: Tri, a: int, c: int):
            s = {a, c}
            for k, (i, j) in enumerate(SLOT_PAIRS):
                if {tri.vtx[i], tri.vtx[j]} == s:
                    return k
            return None

        n = len(self.tris)
        pairings = []
        for ia in range(n):
            for ib in range(ia + 1, n):
                shared = set(self.tris[ia].vtx) & set(self.tris[ib].vtx)
                if len(shared) != 2:
                    continue
                a, c = tuple(shared)
                sa, sb = slot_of(self.tris[ia], a, c), slot_of(self.tris[ib], a, c)
                if sa is None or sb is None:
                    continue
                pairings.append((ia, sa, ib, sb))

        # a manifold edge has exactly one partner per (triangle, slot); 2+ partners means 3+
        # triangles share that vertex pair (a T-junction or a duplicate/overlapping face) --
        # linking would silently pick one partner and orphan the rest into non-reciprocal
        # neighbors (tri A points at B, but B points at C), so refuse instead of guessing.
        claims: dict = {}
        for ia, sa, ib, sb in pairings:
            claims.setdefault((ia, sa), []).append(ib)
            claims.setdefault((ib, sb), []).append(ia)
        for (ti, slot), partners in claims.items():
            if len(partners) > 1:
                tri_ids = sorted({ti, *partners})
                i, j = SLOT_PAIRS[slot]
                a, c = self.tris[ti].vtx[i], self.tris[ti].vtx[j]
                raise ValueError(
                    f"walkmesh edge (vertex {a}, vertex {c}) is shared by {len(tri_ids)} "
                    f"triangles {tri_ids}, not 2 -- a non-manifold edge (e.g. a T-junction or a "
                    f"duplicate/overlapping face); fix the mesh (Merge by Distance / remove the "
                    f"duplicate face in Blender) before rebuilding neighbor links.")

        for ia, sa, ib, sb in pairings:
            self.tris[ia].nbr[sa] = ib
            self.tris[ib].nbr[sb] = ia
            self.edges[self.tris[ia].edge[sa]].clone = sb
            self.edges[self.tris[ib].edge[sb]].clone = sa
        self.invalidate_cache()        # nbr/edgeClone rebuilt: the wall set is now stale


# ----------------------------------------------------------------------------- builders

def _bbox(verts):
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    zs = [v[2] for v in verts]
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def _check_int16(verts):
    for (x, y, z) in verts:                       # .bgi stores verts as Int16
        for v in (x, y, z):
            if not (-32768 <= round(v) <= 32767):
                raise ValueError(
                    f"walkmesh vertex coordinate {v:.0f} exceeds the .bgi Int16 range +/-32767 "
                    f"-- the room/floor is too large in world units; scale it down (FF9 rooms are "
                    f"typically a few thousand units across).")


def build(verts, faces, *, floor_ids=None, tri_flags: int = 1, floor_flags: int = 0,
          org=(0, 0, 0), header_min=None, header_max=None, char=None) -> BgiWalkmesh:
    """Build a complete walkmesh from WORLD-space verts + triangle faces (the EXPORTER).

    This is the inverse of :meth:`BgiWalkmesh.world_verts`: with ``org=(0,0,0)`` and every floor at
    ``org=(0,0,0)`` the engine renders ``world = vert + 0 + 0``, so the verts you pass ARE the
    in-game positions (see the frame note at the top of this module).

    verts     : iterable of (x, y, z) — FF9 WORLD coords (flat floor => y = 0)
    faces     : iterable of (i, j, k) — 0-based vertex indices (one triangle each)
    floor_ids : optional per-FACE floor id (len == len(faces)). ``None`` => one floor with every
                triangle (the flat case). Distinct ids => one BGI floor each — a multi-level room or
                a faithful re-export of an imported real field (e.g. GRGR's 7 floors). Tris are
                grouped by id; each floor sits at org=cur=(0,0,0) (verts already carry world height).

    Computes triangle centers, the 3-edges-per-triangle table, and neighbor/edgeClone links via
    shared-vertex analysis. header.minPos/maxPos default to the true world bounding box (informative;
    the engine ignores them — see the frame note); charPos (debug spawn) defaults to the bbox centre.
    """
    verts = [(round(x), round(y), round(z)) for (x, y, z) in verts]
    faces = [tuple(f) for f in faces]
    _check_int16(verts)
    if not verts or not faces:
        raise ValueError("walkmesh has no geometry (need at least one vertex and one triangle) -- "
                         "check the .obj has both 'v' and 'f' lines.")
    nv = len(verts)
    for ti, f in enumerate(faces):
        if len(f) != 3:
            raise ValueError(f"walkmesh face {ti} has {len(f)} vertices, expected 3 (a triangle).")
        for vi in f:
            if not (0 <= vi < nv):
                raise ValueError(f"walkmesh face {ti} references vertex index {vi}, out of range "
                                 f"0..{nv - 1} -- a malformed or mis-edited .obj.")
    if floor_ids is None:
        floor_ids = [0] * len(faces)
    if len(floor_ids) != len(faces):
        raise ValueError(f"floor_ids has {len(floor_ids)} entries for {len(faces)} faces")

    m = BgiWalkmesh()
    bmin, bmax = _bbox(verts) if verts else ((0, 0, 0), (0, 0, 0))
    hmin = tuple(header_min) if header_min is not None else bmin
    hmax = tuple(header_max) if header_max is not None else bmax
    hchar = tuple(char) if char is not None else ((bmin[0] + bmax[0]) // 2,
                                                  (bmin[1] + bmax[1]) // 2,
                                                  (bmin[2] + bmax[2]) // 2)
    m.orgPos = Vec3(*org)
    m.curPos = Vec3(*org)
    m.minPos = Vec3(*hmin)
    m.maxPos = Vec3(*hmax)
    m.charPos = Vec3(*hchar)
    m.verts = [Vec3(x, y, z) for (x, y, z) in verts]

    # distinct floor ids in first-seen order -> contiguous BGI floor indices 0..N-1
    order = []
    for fid in floor_ids:
        if fid not in order:
            order.append(fid)
    remap = {fid: i for i, fid in enumerate(order)}

    for ti, (i, j, k) in enumerate(faces):
        t = Tri(tri_flags=tri_flags, floor_ndx=remap[floor_ids[ti]], normal_ndx=-1)
        t.vtx = [i, j, k]
        t.edge = [ti * 3 + 0, ti * 3 + 1, ti * 3 + 2]
        cx = (m.verts[i].x + m.verts[j].x + m.verts[k].x) / 3.0
        cy = (m.verts[i].y + m.verts[j].y + m.verts[k].y) / 3.0
        cz = (m.verts[i].z + m.verts[j].z + m.verts[k].z) / 3.0
        t.center = Vec3(int(round(cx)), int(round(cy)), int(round(cz)))
        m.tris.append(t)
        m.edges += [Edge(0, -1), Edge(0, -1), Edge(0, -1)]

    for fi, fid in enumerate(order):              # floor.org=cur=min=max=(0,0,0): verts carry world
        tris = [ti for ti, f in enumerate(floor_ids) if f == fid]
        m.floors.append(Floor(flags=floor_flags, ndx=fi, tri_ndx_list=tris))
    m.rebuild_neighbors()
    return m


def build_flat(verts, faces, *, tri_flags: int = 1, floor_flags: int = 0,
               header_vec=(0, 0, 300)) -> BgiWalkmesh:
    """Legacy single-floor builder with a UNIFORM header vector (a thin wrapper over :func:`build`).

    Equivalent to ``build(..., org=header_vec, header_min/max=header_vec, char=header_vec)`` with one
    floor — kept so the proven HUT / auto-frame pipeline (calibrated against ``header_vec=(0,0,300)``)
    stays byte-for-byte unchanged. NEW multi-floor / world-frame authoring calls :func:`build`
    (``org`` defaults to 0, so what you author is exactly where the engine renders it).
    """
    return build(verts, faces, floor_ids=None, tri_flags=tri_flags, floor_flags=floor_flags,
                 org=header_vec, header_min=header_vec, header_max=header_vec, char=header_vec)


def quad(corners) -> BgiWalkmesh:
    """Build a 2-triangle quad floor from 4 corners (each (x, z) or (x, y, z)).

    Vertex order around the quad: v0, v1, v2, v3 (tri0 = v0v1v2, tri1 = v0v2v3, diagonal v0-v2)
    — the convention the proven HUT walkmesh uses.
    """
    verts = []
    for c in corners:
        if len(c) == 2:
            verts.append((c[0], 0, c[1]))
        else:
            verts.append(tuple(c))
    if len(verts) != 4:
        raise ValueError("quad() needs exactly 4 corners")
    return build_flat(verts, [(0, 1, 2), (0, 2, 3)])


def load_obj_floors(path):
    """Parse a Wavefront .obj into (verts, faces, floor_ids), one floor per ``o``/``g`` object.

    Each ``o <name>`` (or ``g <name>``) starts a new floor; a repeated name reuses its floor; faces
    before any object go to floor 0. Vertices are FF9 world coords (shared across floors — OBJ vertex
    indices are file-global). Faces with >3 verts are fan-triangulated; refs may be ``a/b/c``.
    """
    verts, faces, floor_ids = [], [], []
    names, cur, next_id = {}, 0, 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            s = line.split()
            if not s:
                continue
            if s[0] == "v":
                verts.append((float(s[1]), float(s[2]), float(s[3])))
            elif s[0] in ("o", "g"):
                name = s[1] if len(s) > 1 else ""
                if name not in names:
                    names[name] = next_id
                    next_id += 1
                cur = names[name]
            elif s[0] == "f":
                idx = [int(tok.split("/")[0]) - 1 for tok in s[1:]]  # 1-based -> 0-based
                for k in range(1, len(idx) - 1):
                    faces.append((idx[0], idx[k], idx[k + 1]))
                    floor_ids.append(cur)
    return verts, faces, floor_ids


def load_obj(path):
    """Parse a Wavefront .obj into (verts, faces) — floors merged. See :func:`load_obj_floors`."""
    verts, faces, _ = load_obj_floors(path)
    return verts, faces


def obj_to_bgi(path, **kwargs) -> bytes:
    """Convert a Wavefront .obj walkmesh (FF9 world coords) to .bgi bytes.

    Multiple ``o``/``g`` objects => a multi-floor world-frame walkmesh (:func:`build`, org=0); a
    single object => the legacy flat builder (:func:`build_flat`), so existing output is unchanged.
    """
    verts, faces, floor_ids = load_obj_floors(path)
    if len(set(floor_ids)) > 1:
        return build(verts, faces, floor_ids=floor_ids).to_bytes()
    return build_flat(verts, faces, **kwargs).to_bytes()
