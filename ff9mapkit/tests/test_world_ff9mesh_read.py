"""mesh.read_ff9mesh reads a .ff9mesh's channels whole (PERF.md 5, c8): it unpacked every vertex's every channel by
struct -- most of a card's island read (126 loose override files, about 0.28 s of 0.59 s) and of every verb that
stacks on deployed overrides. numpy reads each channel block at once: the same doubles bit for bit (float32 widened
to a Python float as struct does), the same refusals; without numpy, the loop."""
from __future__ import annotations

import struct

import pytest

from ff9mapkit.world import mesh as M

pytest.importorskip("numpy")

VALS = [0.0, -0.0, 1.5, float("inf"), float("-inf"), 7.25, 1e-45, 3.4e38, -2.25]   # (a NaN: the loop, below)


def _file(tmp_path, flags=7, vcount=3, icount=4):
    out = bytearray(M.MAGIC) + struct.pack("<iiii", M.VERSION, vcount, icount, flags)
    k = 0
    for dim, on in ((3, True), (3, flags & 1), (2, flags & 2), (4, flags & 4)):
        if on:
            for _ in range(vcount * dim):
                out += struct.pack("<f", VALS[k % len(VALS)])
                k += 1
    out += struct.pack("<%di" % icount, *range(icount))
    p = tmp_path / "Block[1][2] Terrain.ff9mesh"
    p.write_bytes(bytes(out))
    return p


def _by_vertex(path):
    """read_ff9mesh as it was: a struct.unpack per vertex and channel (the oracle)."""
    data = path.read_bytes()
    _v, vcount, icount, flags = struct.unpack_from("<iiii", data, 4)
    off, out = 20, {}
    for key, dim, on in (("verts", 3, True), ("normals", 3, flags & 1), ("uvs", 2, flags & 2),
                         ("tangents", 4, flags & 4)):
        if on:
            out[key] = [list(struct.unpack_from("<%df" % dim, data, off + j * dim * 4)) for j in range(vcount)]
            off += vcount * dim * 4
        else:
            out[key] = None
    out["indices"] = list(struct.unpack_from("<%di" % icount, data, off))
    return out


def _bits(rows):
    return None if rows is None else [[struct.pack("<d", v) for v in r] for r in rows]


@pytest.mark.parametrize("flags", [0, 1, 2, 4, 7])
def test_a_ff9mesh_is_read_whole_with_the_same_floats(tmp_path, monkeypatch, flags):
    p = _file(tmp_path, flags=flags)
    want = _by_vertex(p)
    calls = []

    class _Counting:                                        # mesh's NAME swapped, never the struct module
        def unpack_from(self, fmt, *a):
            if fmt.endswith("f"):
                calls.append(fmt)
            return struct.unpack_from(fmt, *a)

        def __getattr__(self, name):
            return getattr(struct, name)
    monkeypatch.setattr(M, "struct", _Counting())
    got = M.read_ff9mesh(p)
    assert calls == []                                      # no per-vertex unpack
    for key in ("verts", "normals", "uvs", "tangents"):
        assert _bits(got[key]) == _bits(want[key]), key
        assert got[key] is None or all(type(v) is float for r in got[key] for v in r)
    assert got["indices"] == want["indices"] and got["vcount"] == 3


def test_the_refusals_stand(tmp_path):
    p = _file(tmp_path)
    data = p.read_bytes()
    p.write_bytes(b"XXXX" + data[4:])
    with pytest.raises(ValueError, match="bad magic"):
        M.read_ff9mesh(p)
    p.write_bytes(data[:4] + struct.pack("<i", 2) + data[8:])
    with pytest.raises(ValueError, match="unsupported .ff9mesh version 2"):
        M.read_ff9mesh(p)


def test_a_cut_short_file_refuses_as_it_always_did(tmp_path):
    """A .ff9mesh cut short (an interrupted write) raised struct.error by the per-vertex unpack and a ValueError by
    numpy's whole read -- and coastnav's stacked loader reads a ValueError as "no such part", so a corrupt override
    went quietly absent (review of the perf commits, K2). The whole read refuses as the loop does."""
    p = _file(tmp_path, flags=7)
    p.write_bytes(p.read_bytes()[:60])                                   # positions half there, the rest gone
    with pytest.raises(struct.error):
        M.read_ff9mesh(p)


def test_a_signalling_nan_reads_as_the_loop_reads_it(tmp_path):
    """On CPython 3.14 struct keeps a float32 signalling NaN signalling and numpy's widening quiets it, so the whole
    read was not the loop's bit for bit for that one input (review of the perf commits, K4). A block holding a NaN
    goes through the loop: the same doubles for every input, in both decoders."""
    from ff9mapkit.world import extract as X
    bits = (0x7F800001, 0xFFA00000, 0x7FC00000)                           # two signalling NaNs and a quiet one
    snan = [struct.unpack("<f", struct.pack("<I", u))[0] for u in bits]
    raw = b"".join(struct.pack("<I", u) for u in bits)
    out = bytearray(M.MAGIC) + struct.pack("<iiii", M.VERSION, 1, 0, 0) + raw
    p = tmp_path / "Block[1][2] Terrain.ff9mesh"
    p.write_bytes(bytes(out))
    assert _bits(M.read_ff9mesh(p)["verts"]) == _bits([snan])
    from .test_world_block_part_lookup import _Chan, _Pptr
    bm = X._decode_world_mesh(_Pptr(raw, 1, [_Chan(0, 3)]), disc=1, x=1, y=2, lod="0_1")
    assert _bits(bm.chan_arrays[0]) == _bits([snan])
