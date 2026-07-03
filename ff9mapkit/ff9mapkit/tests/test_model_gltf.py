"""Offline tests for the glTF exporter (the Blender edit loop's forward half) -- no install/UnityPy needed.

The exporter's load-bearing convention is the Unity(LH,Y-up)->glTF(RH,Y-up) change = a negate-X mirror with
the quaternion remap (x,-y,-z,w). That's the error-prone part, so the key test proves the quaternion remap
is the correct COMPANION to the point mirror (mirror(rot(q,p)) == rot(cquat(q), mirror(p))). The binary
machinery (accessor builder + .glb writer) is validated by writing + parsing back. The full skinned export +
rest-pose identity is covered by the in-Blender check + the on-disc gltf_check probe (needs the install).
"""
import json
import math
import struct

import pytest

from ff9mapkit.models import gltf, _gltf_io
from ff9mapkit.models.fbx_skin import _quat_to_matrix


def _norm(q):
    n = math.sqrt(sum(c * c for c in q)) or 1.0
    return [c / n for c in q]


def _rot(q, p):
    """Rotate point p by quaternion q (xyzw)."""
    R = _quat_to_matrix(q)
    return [sum(R[i][k] * p[k] for k in range(3)) for i in range(3)]


_MIRROR_X = lambda v: [-v[0], v[1], v[2]]

_QUATS = [
    [0.0, 0.0, 0.0, 1.0],
    _norm([0.0, math.sin(math.radians(45)), 0.0, math.cos(math.radians(45))]),   # 90deg yaw
    _norm([math.sin(math.radians(30)), 0.0, 0.0, math.cos(math.radians(30))]),   # 60deg about X
    _norm([0.2, -0.5, 0.3, 0.78]),
    _norm([0.13, -0.62, 0.41, 0.66]),
]
_POINTS = [[1.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 3.0], [1.5, -2.0, 0.7], [-1.0, 1.0, -1.0]]


def test_cquat_is_the_negate_x_mirror_companion():
    """The core correctness proof: for the negate-X coordinate mirror M, the rotation q becomes _cquat(q) so
    that M(q·p) == _cquat(q)·M(p) for all p. If this holds, the skeleton + animation transform consistently
    under the handedness flip (this is exactly what keeps the rig from twisting)."""
    for q in _QUATS:
        for p in _POINTS:
            lhs = _MIRROR_X(_rot(q, p))
            rhs = _rot(gltf._cquat(q), _MIRROR_X(p))
            assert all(abs(a - b) < 1e-6 for a, b in zip(lhs, rhs)), f"q={q} p={p}: {lhs} != {rhs}"


def test_cquat_maps_90_yaw_to_minus_90_yaw():
    """Sanity check from the spec: a Unity +90deg yaw about +Y mirrors to a -90deg yaw about +Y."""
    q = _norm([0.0, math.sin(math.radians(45)), 0.0, math.cos(math.radians(45))])
    c = gltf._cquat(q)
    assert abs(c[1] + q[1]) < 1e-9 and abs(c[3] - q[3]) < 1e-9   # y negated, w kept -> opposite-sign yaw
    assert abs(c[0]) < 1e-9 and abs(c[2]) < 1e-9


def test_cpos_and_cnrm_negate_x_only():
    assert gltf._cpos([2.0, 3.0, 4.0], 1.0) == [-2.0, 3.0, 4.0]
    assert gltf._cpos([2.0, 3.0, 4.0], 0.01) == [-0.02, 0.03, 0.04]   # scale bake
    assert gltf._cnrm([2.0, 3.0, 4.0]) == [-2.0, 3.0, 4.0]            # no scale on normals


def test_mat4_colmajor_transposes_row_major():
    m = [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11], [12, 13, 14, 15]]
    # column-major: first column (0,4,8,12), then (1,5,9,13)...
    assert gltf._mat4_colmajor(m) == [0, 4, 8, 12, 1, 5, 9, 13, 2, 6, 10, 14, 3, 7, 11, 15]


def test_sign_continuous_keeps_neighbours_in_one_hemisphere():
    q0 = _norm([0.0, 0.1, 0.0, 0.99])
    flipped = [-c for c in q0]                     # same rotation, opposite hemisphere
    out = gltf._sign_continuous([q0, flipped, q0])
    # each consecutive pair must have non-negative dot
    for a, b in zip(out, out[1:]):
        assert sum(x * y for x, y in zip(a, b)) >= -1e-9


def test_gltfbuffer_accessor_shape_and_minmax_and_alignment():
    buf = _gltf_io.GltfBuffer()
    a = buf.add([1.0, -2.0, 3.0, 0.0, 5.0, -6.0], _gltf_io.FLOAT, "VEC3", minmax=True)
    acc = buf.accessors[a]
    assert acc["type"] == "VEC3" and acc["componentType"] == 5126 and acc["count"] == 2
    assert acc["min"] == [0.0, -2.0, -6.0] and acc["max"] == [1.0, 5.0, 3.0]
    # a second add must start 4-byte aligned
    b = buf.add([7, 8, 9], _gltf_io.UNSIGNED_INT, "SCALAR")
    assert buf.bufferViews[buf.accessors[b]["bufferView"]]["byteOffset"] % 4 == 0


def test_write_glb_is_a_valid_parseable_container():
    buf = _gltf_io.GltfBuffer()
    pos = buf.add([0, 0, 0, 1, 1, 1], _gltf_io.FLOAT, "VEC3", minmax=True)
    gltf_doc = {"asset": {"version": "2.0"}, "accessors": buf.accessors, "bufferViews": buf.bufferViews,
                "meshes": [{"primitives": [{"attributes": {"POSITION": pos}}]}]}
    import tempfile
    import os
    path = os.path.join(tempfile.gettempdir(), "ff9mk_test.glb")
    _gltf_io.write_glb(gltf_doc, buf.blob, path)
    data = open(path, "rb").read()
    magic, ver, total = struct.unpack_from("<III", data, 0)
    assert magic == 0x46546C67 and ver == 2 and total == len(data)   # 'glTF', v2, self-consistent length
    jlen, jtype = struct.unpack_from("<II", data, 12)
    assert jtype == 0x4E4F534A                                       # 'JSON'
    doc = json.loads(data[20:20 + jlen])
    assert doc["asset"]["version"] == "2.0" and doc["buffers"][0]["byteLength"] == len(buf.blob)
    blen, btype = struct.unpack_from("<II", data, 20 + jlen)
    assert btype == 0x004E4942                                       # 'BIN\0'
    assert (20 + jlen) % 4 == 0 and len(data) % 4 == 0               # chunk alignment


def test_read_clip_shape_contract():
    """read_clip's output contract (the shape the exporter consumes), checked structurally on a hand-built
    typetree stand-in so it needs no install."""
    class _FakePtr:
        type = type("T", (), {"name": "AnimationClip"})()
        def __init__(self, tt):
            self._tt = tt
        def read_typetree(self):
            return self._tt
    tt = {"m_Name": "147", "m_SampleRate": 30.0,
          "m_RotationCurves": [{"path": "bone000/bone005", "curve": {"m_Curve": [
              {"time": 0.0, "value": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}},
              {"time": 0.5, "value": {"x": 0.0, "y": 0.7, "z": 0.0, "w": 0.7}}]}}],
          "m_PositionCurves": [{"path": "bone000", "curve": {"m_Curve": [
              {"time": 0.0, "value": {"x": 1.0, "y": 2.0, "z": 3.0}}]}}],
          "m_ScaleCurves": []}

    class _Bundle:
        container = {"assets/resources/animations/8/147.anim": _FakePtr(tt)}
    clip = _gltf_io.read_clip(_Bundle(), 8, 147)
    assert clip["name"] == "147" and clip["sample_rate"] == 30.0 and abs(clip["length"] - 0.5) < 1e-9
    b = clip["bones"]["bone000/bone005"]
    assert b["bone"] == 5 and len(b["rot"]) == 2
    assert b["rot"][1] == (0.5, (0.0, 0.7, 0.0, 0.7))
    assert clip["bones"]["bone000"]["pos"][0] == (0.0, (1.0, 2.0, 3.0))
    assert _gltf_io.read_clip(_Bundle(), 8, 999) is None            # missing clip -> None
