"""Review probe (kernels slice): a float32 signalling NaN through the two numpy decodes (e806d22d, fd635112).

Both commits say numpy widens float32 to a Python float "as struct does, bit for bit (-0.0, NaN, inf, subnormals)".
On CPython 3.14 struct.unpack('<f') keeps a signalling NaN signalling (gh-130317); numpy's float32 -> float64 cast
quiets it. So the decoded double differs, and re-encoding it (struct.pack('<f'), what ff9mesh_bytes does) writes a
different float32 than the file held.

Run from the worktree's ff9mapkit/:  py ../studies/overworld-editor/perf/review_kernels_snan.py
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _P
_KIT = _P(__file__).resolve().parents[3] / "ff9mapkit"
_sys.path.insert(0, str(_KIT))
import ff9mapkit as _fk
assert _P(_fk.__file__).resolve().is_relative_to(_KIT), _fk.__file__

import struct
import sys
import tempfile
from pathlib import Path

from ff9mapkit.world import extract as X
from ff9mapkit.world import mesh as M

SNAN = [0x7F800001, 0xFFA00000, 0x7FBFFFFF]           # float32 signalling NaNs (quiet bit 22 clear)


def f32(bits):
    return struct.unpack("<f", struct.pack("<I", bits))[0]


def bits32(v):
    return struct.unpack("<I", struct.pack("<f", v))[0]


def main():
    print(sys.version.split()[0])
    # ---- mesh.read_ff9mesh (fd635112): one triangle, its first vert's x a signalling NaN
    out = bytearray(M.MAGIC) + struct.pack("<iiii", M.VERSION, 3, 3, 0)
    vals = [f32(SNAN[0]), 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, -1.0]
    raw = struct.pack("<I", SNAN[0]) + struct.pack("<8f", *vals[1:])
    out += raw + struct.pack("<3i", 0, 1, 2)
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "Block[1][2] Terrain.ff9mesh"
        p.write_bytes(bytes(out))
        got = M.read_ff9mesh(p)["verts"][0][0]
        by_struct = struct.unpack_from("<f", bytes(out), 20)[0]
        print("read_ff9mesh  file f32 %08x | struct-lane double %016x -> repack %08x | numpy-lane double %016x -> "
              "repack %08x" % (SNAN[0], struct.unpack("<Q", struct.pack("<d", by_struct))[0], bits32(by_struct),
                               struct.unpack("<Q", struct.pack("<d", got))[0], bits32(got)))
    # ---- extract._decode_world_mesh (e806d22d): the aligned whole-buffer lane
    chans = [type("C", (), {"offset": 0, "dimension": 3})(), type("C", (), {"offset": 12, "dimension": 1})()]
    vraw = b"".join(struct.pack("<I", b) for b in SNAN) + struct.pack("<f", 0.5)

    class Pptr:
        def read(self):
            sub = type("S", (), {"firstByte": 0, "indexCount": 3})()
            vd = type("VD", (), {"m_DataSize": vraw, "m_VertexCount": 1, "m_Channels": chans})()
            return type("MD", (), {"m_VertexData": vd, "m_IndexBuffer": b"\x00\x00\x00\x00\x00\x00",
                                   "m_SubMeshes": [sub], "m_Name": "x", "m_Use16BitIndices": 1})()
    bm = X._decode_world_mesh(Pptr(), disc=1, x=1, y=2, lod="0_1")
    want = list(struct.unpack_from("<3f", vraw, 0))
    print("decode_world_mesh pos: file", ["%08x" % b for b in SNAN],
          "| struct lane repacks", ["%08x" % bits32(v) for v in want],
          "| numpy lane repacks", ["%08x" % bits32(v) for v in bm.verts[0]])
    same = [struct.pack("<d", a) == struct.pack("<d", b) for a, b in zip(bm.verts[0], want)]
    print("bit-identical to the struct lane:", same)


if __name__ == "__main__":
    main()
