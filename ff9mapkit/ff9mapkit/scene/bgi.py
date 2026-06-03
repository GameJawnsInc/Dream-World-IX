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
from dataclasses import dataclass, field

MAGIC = 0xACDCDEAD
HEADER_SIZE = 64           # magic+dataSize+5*vec(30)+activeFloor/Tri(4)+12*u16(24)
FIRST_SECTION_REL = 0x3C   # triOffset (relative to byte 4)
TRI_SIZE, EDGE_SIZE, ANM_SIZE, FLOOR_SIZE, NORMAL_SIZE, VERT_SIZE = 40, 4, 16, 32, 16, 6

# slot -> the pair of triangle-local vertex indices forming that edge (BGI convention)
SLOT_PAIRS = [(0, 2), (0, 1), (1, 2)]


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
        for ia in range(n):
            for ib in range(ia + 1, n):
                shared = set(self.tris[ia].vtx) & set(self.tris[ib].vtx)
                if len(shared) != 2:
                    continue
                a, c = tuple(shared)
                sa, sb = slot_of(self.tris[ia], a, c), slot_of(self.tris[ib], a, c)
                if sa is None or sb is None:
                    continue
                self.tris[ia].nbr[sa] = ib
                self.tris[ib].nbr[sb] = ia
                self.edges[self.tris[ia].edge[sa]].clone = sb
                self.edges[self.tris[ib].edge[sb]].clone = sa


# ----------------------------------------------------------------------------- builders

def build_flat(verts, faces, *, tri_flags: int = 1, floor_flags: int = 0,
               header_vec=(0, 0, 300)) -> BgiWalkmesh:
    """Build a complete single-floor walkmesh from world-space verts + triangle faces.

    verts : iterable of (x, y, z) — FF9 world coords (flat floor => y = 0)
    faces : iterable of (i, j, k) — 0-based vertex indices (one triangle each)
    Computes triangle centers, the 3-edges-per-triangle table, neighbor/edgeClone links via
    shared-vertex analysis, and one floor covering all triangles. Reproduces the structure
    Memoria's editor emits, byte-for-byte, for the proven flat-quad case.
    """
    m = BgiWalkmesh()
    hv = Vec3(*header_vec)
    m.orgPos, m.curPos, m.minPos, m.maxPos, m.charPos = (Vec3(*header_vec) for _ in range(5))
    verts = list(verts)
    for (x, y, z) in verts:                       # .bgi stores verts as Int16
        for v in (x, y, z):
            if not (-32768 <= round(v) <= 32767):
                raise ValueError(
                    f"walkmesh vertex coordinate {v:.0f} exceeds the .bgi Int16 range +/-32767 "
                    f"-- the room/floor is too large in world units; scale it down (FF9 rooms are "
                    f"typically a few thousand units across).")
    m.verts = [Vec3(int(round(x)), int(round(y)), int(round(z))) for (x, y, z) in verts]
    for ti, (i, j, k) in enumerate(faces):
        t = Tri(tri_flags=tri_flags, floor_ndx=0, normal_ndx=-1)
        t.vtx = [i, j, k]
        t.edge = [ti * 3 + 0, ti * 3 + 1, ti * 3 + 2]
        cx = (m.verts[i].x + m.verts[j].x + m.verts[k].x) / 3.0
        cy = (m.verts[i].y + m.verts[j].y + m.verts[k].y) / 3.0
        cz = (m.verts[i].z + m.verts[j].z + m.verts[k].z) / 3.0
        t.center = Vec3(int(round(cx)), int(round(cy)), int(round(cz)))
        m.tris.append(t)
        m.edges += [Edge(0, -1), Edge(0, -1), Edge(0, -1)]
    floor = Floor(flags=floor_flags, ndx=0, tri_ndx_list=list(range(len(m.tris))))
    m.floors.append(floor)
    m.rebuild_neighbors()
    return m


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


def load_obj(path):
    """Parse a Wavefront .obj into (verts, faces). Vertices are FF9 world coords.

    Faces with >3 vertices are fan-triangulated. ``v``/``f`` lines only; ``vn``/``vt``/``o``
    are ignored (all walkpaths merge into one flat floor). Face vertex refs may be ``a//n``.
    """
    verts, faces = [], []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            s = line.split()
            if not s:
                continue
            if s[0] == "v":
                verts.append((float(s[1]), float(s[2]), float(s[3])))
            elif s[0] == "f":
                idx = [int(tok.split("/")[0]) - 1 for tok in s[1:]]  # 1-based -> 0-based
                for k in range(1, len(idx) - 1):
                    faces.append((idx[0], idx[k], idx[k + 1]))
    return verts, faces


def obj_to_bgi(path, **kwargs) -> bytes:
    """Convert a Wavefront .obj walkmesh (FF9 world coords) to .bgi bytes."""
    verts, faces = load_obj(path)
    return build_flat(verts, faces, **kwargs).to_bytes()
