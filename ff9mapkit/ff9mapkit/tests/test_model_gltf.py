"""Offline tests for the glTF exporter (the Blender edit loop's forward half) -- no install/UnityPy needed.

The exporter's load-bearing convention is the FF9(LH,Y-DOWN)->glTF(RH,Y-up) change = a negate-Y mirror with
the quaternion remap (-x,y,-z,w). That's the error-prone part, so the key test proves the quaternion remap
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


_MIRROR_Y = lambda v: [v[0], -v[1], v[2]]

_QUATS = [
    [0.0, 0.0, 0.0, 1.0],
    _norm([0.0, math.sin(math.radians(45)), 0.0, math.cos(math.radians(45))]),   # 90deg yaw
    _norm([math.sin(math.radians(30)), 0.0, 0.0, math.cos(math.radians(30))]),   # 60deg about X
    _norm([0.2, -0.5, 0.3, 0.78]),
    _norm([0.13, -0.62, 0.41, 0.66]),
]
_POINTS = [[1.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 3.0], [1.5, -2.0, 0.7], [-1.0, 1.0, -1.0]]


def test_cquat_is_the_negate_y_mirror_companion():
    """The core correctness proof: for the negate-Y coordinate mirror M, the rotation q becomes _cquat(q) so
    that M(q·p) == _cquat(q)·M(p) for all p. If this holds, the skeleton + animation transform consistently
    under the handedness flip (this is exactly what keeps the rig from twisting)."""
    for q in _QUATS:
        for p in _POINTS:
            lhs = _MIRROR_Y(_rot(q, p))
            rhs = _rot(gltf._cquat(q), _MIRROR_Y(p))
            assert all(abs(a - b) < 1e-6 for a, b in zip(lhs, rhs)), f"q={q} p={p}: {lhs} != {rhs}"


def test_cquat_preserves_a_yaw_about_the_flipped_axis():
    """A rotation ABOUT the flipped (Y) axis is preserved under a negate-Y mirror (Y is the mirror's normal),
    so its quaternion is unchanged -- a targeted check of the remap's fixed axis."""
    q = _norm([0.0, math.sin(math.radians(45)), 0.0, math.cos(math.radians(45))])   # 90deg yaw about +Y
    c = gltf._cquat(q)
    assert all(abs(a - b) < 1e-9 for a, b in zip(c, q))


def test_cpos_and_cnrm_negate_y_only():
    assert gltf._cpos([2.0, 3.0, 4.0], 1.0) == [2.0, -3.0, 4.0]
    assert gltf._cpos([2.0, 3.0, 4.0], 0.01) == [0.02, -0.03, 0.04]   # scale bake
    assert gltf._cnrm([2.0, 3.0, 4.0]) == [2.0, -3.0, 4.0]            # no scale on normals


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


# --------------------------------------------------------------------------- return path (glTF -> struct)

def test_inverse_conversions_undo_the_forward():
    """The return path's axis flip must invert the forward one exactly (negate-Y is an involution; scale /s)."""
    for v in ([1.0, 2.0, 3.0], [-1.5, 0.5, -2.0]):
        assert all(abs(a - b) < 1e-9 for a, b in zip(gltf._icpos(gltf._cpos(v, 0.01), 0.01), v))
        assert all(abs(a - b) < 1e-9 for a, b in zip(gltf._icnrm(gltf._cnrm(v)), v))
    for q in _QUATS:
        assert all(abs(a - b) < 1e-9 for a, b in zip(gltf._icquat(gltf._cquat(q)), q))


def test_read_glb_and_decode_accessor_roundtrip():
    buf = _gltf_io.GltfBuffer()
    a = buf.add([1.0, -2.0, 3.0, 4.0, 5.0, -6.0], _gltf_io.FLOAT, "VEC3", minmax=True)
    b = buf.add([7, 8, 9], _gltf_io.UNSIGNED_INT, "SCALAR")
    import tempfile
    import os
    path = os.path.join(tempfile.gettempdir(), "ff9mk_rt.glb")
    _gltf_io.write_glb({"accessors": buf.accessors, "bufferViews": buf.bufferViews}, buf.blob, path)
    g, blob = _gltf_io.read_glb(path)
    assert _gltf_io.decode_accessor(g, blob, a) == [(1.0, -2.0, 3.0), (4.0, 5.0, -6.0)]
    assert _gltf_io.decode_accessor(g, blob, b) == [(7,), (8,), (9,)]


def _min_skinned_glb(path):
    """A minimal skinned glTF (1 bone, 1 triangle, weighted to bone000) via the writer -- for import tests."""
    buf = _gltf_io.GltfBuffer()
    pos = buf.add([0, 0, 0, 1, 0, 0, 0, 1, 0], _gltf_io.FLOAT, "VEC3", minmax=True)
    joints = buf.add([0, 0, 0, 0] * 3, _gltf_io.UNSIGNED_SHORT, "VEC4")
    weights = buf.add([1, 0, 0, 0] * 3, _gltf_io.FLOAT, "VEC4")
    idx = buf.add([0, 2, 1], _gltf_io.UNSIGNED_INT, "SCALAR")           # already reverse-wound (as the exporter emits)
    ibm = buf.add([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1], _gltf_io.FLOAT, "MAT4")
    g = {"scene": 0, "scenes": [{"nodes": [0, 1]}],
         "nodes": [{"name": "bone000", "translation": [1.0, 2.0, 3.0], "rotation": [0.0, 0.0, 0.0, 1.0]},
                   {"name": "Mesh", "mesh": 0, "skin": 0}],
         "meshes": [{"primitives": [{"attributes": {"POSITION": pos, "JOINTS_0": joints, "WEIGHTS_0": weights},
                                     "indices": idx}]}],
         "skins": [{"joints": [0], "inverseBindMatrices": ibm, "skeleton": 0}],
         "accessors": buf.accessors, "bufferViews": buf.bufferViews}
    _gltf_io.write_glb(g, buf.blob, path)


def test_import_gltf_rebuilds_the_model_struct():
    import tempfile
    import os
    path = os.path.join(tempfile.gettempdir(), "ff9mk_min.glb")
    _min_skinned_glb(path)
    m = gltf.import_gltf(path, scale=1.0)
    assert [b["name"] for b in m["bones"]] == ["bone000"] and m["bones"][0]["parent"] is None
    assert m["bones"][0]["pos"] == [1.0, -2.0, 3.0]                      # negate-Y inverse of translation
    assert len(m["meshes"]) == 1
    me = m["meshes"][0]
    assert me["verts"] == [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, -1.0, 0.0]]   # negate-Y on positions
    assert me["submeshes"][0]["tris"] == [[0, 1, 2]]                    # winding un-reversed (0,2,1 -> 0,1,2)
    assert me["weights"] == [[(0, 1.0)], [(0, 1.0)], [(0, 1.0)]]        # JOINTS_0 -> FF9 bone number 0
    # the reconstructed struct must emit a valid FBX (the same gate the forward path passes)
    from ff9mapkit.models import fbx_skin as _fs
    m["root_bone"] = "bone000"
    text, meta = _fs.emit_skinned_fbx(m)
    assert meta["bones"] == 1 and meta["meshes"] == 1


def test_import_rejects_a_non_bone_joint_name():
    import tempfile
    import os
    path = os.path.join(tempfile.gettempdir(), "ff9mk_badbone.glb")
    _min_skinned_glb(path)
    g, blob = _gltf_io.read_glb(path)
    g["nodes"][0]["name"] = "Spine_01"          # a Blender-renamed bone the kit can't map to an FF9 number
    _gltf_io.write_glb(g, blob, path)
    with pytest.raises(ValueError, match="boneNNN|bone000"):
        gltf.import_gltf(path, scale=1.0)


def test_source_stamp_auto_detected_from_gltf():
    """model-import auto-detects the source model from the glTF's asset.extras stamp -- so a round-tripped
    edit needs no --like. A foreign glTF (no stamp) -> (None, None)."""
    import tempfile
    import os
    buf = _gltf_io.GltfBuffer()
    pos = buf.add([0, 0, 0, 1, 0, 0, 0, 1, 0], _gltf_io.FLOAT, "VEC3", minmax=True)
    common = {"accessors": buf.accessors, "bufferViews": buf.bufferViews,
              "meshes": [{"primitives": [{"attributes": {"POSITION": pos}}]}]}
    path = os.path.join(tempfile.gettempdir(), "ff9mk_stamp.glb")
    _gltf_io.write_glb({"asset": {"version": "2.0", "extras":
                        {"ff9_geo": "GEO_MAIN_F0_VIV", "ff9_geo_id": 8, "ff9_scale": 0.02}}, **common},
                       buf.blob, path)
    assert gltf.source_from_gltf(path) == ("GEO_MAIN_F0_VIV", 0.02)
    # node extras (Blender keeps these as object custom properties across a round-trip)
    _gltf_io.write_glb({"asset": {"version": "2.0"},
                        "nodes": [{"name": "x", "extras": {"ff9_geo": "GEO_MAIN_F0_ZDN", "ff9_scale": 0.01}}],
                        **common}, buf.blob, path)
    assert gltf.source_from_gltf(path) == ("GEO_MAIN_F0_ZDN", 0.01)
    # NAME fallback: Blender drops extras but keeps the mesh name (+ a .001 dedup suffix)
    _gltf_io.write_glb({"asset": {"version": "2.0", "generator": "Khronos glTF Blender I/O"},
                        "meshes": [{"name": "GEO_MAIN_F0_VIV.001", "primitives": [{"attributes": {"POSITION": pos}}]}],
                        "accessors": buf.accessors, "bufferViews": buf.bufferViews}, buf.blob, path)
    assert gltf.source_from_gltf(path) == ("GEO_MAIN_F0_VIV", None)
    # a truly foreign glTF -> nothing
    _gltf_io.write_glb({"asset": {"version": "2.0"}, **common}, buf.blob, path)
    assert gltf.source_from_gltf(path) == (None, None)
