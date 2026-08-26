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


def test_read_clip_builds_the_bundle_index_once_and_reuses_it():
    """A per-clip loop (a battle animset's ~34 motions) must only pay for ONE full container pass, not one
    per clip -- the index is built on first use and cached on the bundle instance."""
    class _FakePtr:
        type = type("T", (), {"name": "AnimationClip"})()
        def __init__(self, tt):
            self._tt = tt
        def read_typetree(self):
            return self._tt

    def _tt(name):
        return {"m_Name": name, "m_SampleRate": 30.0,
                "m_RotationCurves": [{"path": "bone000", "curve": {"m_Curve": [
                    {"time": 0.0, "value": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}}]}}],
                "m_PositionCurves": [], "m_ScaleCurves": []}

    class _CountingContainer(dict):
        scans = 0
        def items(self):
            self.scans += 1
            return dict.items(self)

    container = _CountingContainer({
        "assets/resources/animations/8/1.anim": _FakePtr(_tt("one")),
        "assets/resources/animations/8/2.anim": _FakePtr(_tt("two")),
        "assets/resources/animations/9/1.anim": _FakePtr(_tt("nine-one")),
    })

    class _Bundle:
        pass
    bundle = _Bundle()
    bundle.container = container

    assert _gltf_io.read_clip(bundle, 8, 1)["name"] == "one"
    assert _gltf_io.read_clip(bundle, 8, 2)["name"] == "two"
    assert _gltf_io.read_clip(bundle, 9, 1)["name"] == "nine-one"
    assert container.scans == 1                       # one pass builds the index; all 3 lookups reused it
    assert _gltf_io.read_clip(bundle, 8, 999) is None  # a genuine miss still resolves to None


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


def _armature_wrapped_glb(path, *, translation=None, rotation=None, scale=None):
    """The minimal skinned glb, but with bone000 re-parented under an 'Armature' node carrying the given
    transform (as a Blender re-export structures a skeleton) -- to exercise the root-parent-transform guard."""
    _min_skinned_glb(path)
    g, blob = _gltf_io.read_glb(path)
    arm = {"name": "Armature", "children": [0]}                 # node 0 is bone000
    if translation is not None:
        arm["translation"] = translation
    if rotation is not None:
        arm["rotation"] = rotation
    if scale is not None:
        arm["scale"] = scale
    arm_i = len(g["nodes"])
    g["nodes"].append(arm)
    g["scenes"][0]["nodes"] = [arm_i, 1]                        # armature + the mesh node
    _gltf_io.write_glb(g, blob, path)


def test_import_accepts_an_identity_armature_parent():
    """A normal Blender re-export wraps the root bone in an IDENTITY Armature node (viviexport.glb/Untitled.glb
    do exactly this) -- that must import cleanly, no false positive on the proven round-trip."""
    import os
    import tempfile
    path = os.path.join(tempfile.gettempdir(), "ff9mk_arm_id.glb")
    _armature_wrapped_glb(path)                                 # no transform on the Armature -> identity
    m = gltf.import_gltf(path, scale=1.0)
    assert m["bones"][0]["name"] == "bone000" and m["bones"][0]["parent"] is None
    # an explicit unit transform (what some exporters emit) is still identity
    _armature_wrapped_glb(path, translation=[0.0, 0.0, 0.0], rotation=[0.0, 0.0, 0.0, 1.0], scale=[1.0, 1.0, 1.0])
    assert gltf.import_gltf(path, scale=1.0)["bones"][0]["name"] == "bone000"


@pytest.mark.parametrize("kw", [
    {"scale": [2.0, 2.0, 2.0]},                                # a uniform armature scale (the common "grow the model")
    {"scale": [1.0, 2.0, 1.0]},                                # a non-uniform armature scale (the engine-TODO shear risk)
    {"translation": [0.0, 5.0, 0.0]},                          # a moved armature
    {"rotation": [0.70710678, 0.0, 0.0, 0.70710678]},          # a 90deg-rotated armature
])
def test_import_rejects_a_live_armature_transform(kw, tmp_path):
    """A live (un-applied) transform on the Armature above bone000 is silently un-carryable -> import must
    refuse it and point at Object > Apply > All Transforms, not import a wrong-scale/orientation model."""
    path = str(tmp_path / "live.glb")                          # tmp_path is per-case -> safe under pytest-xdist
    _armature_wrapped_glb(path, **kw)
    with pytest.raises(ValueError, match="Apply|Ctrl\\+A|root bone"):
        gltf.import_gltf(path, scale=1.0)


def test_looks_identity_and_root_parent_matrix_units():
    """The two pure helpers behind the guard: identity detection tolerances + ancestor-matrix composition."""
    I = [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]
    assert gltf._looks_identity(I)
    noisy = [row[:] for row in I]
    noisy[0][0] = 1.0 + 5e-4                                    # sub-tolerance float noise -> still identity
    noisy[2][3] = 5e-4
    assert gltf._looks_identity(noisy)
    scaled = [row[:] for row in I]
    scaled[1][1] = 2.0                                          # a real 2x scale -> not identity
    assert not gltf._looks_identity(scaled)
    # a translated armature composes into the root-parent matrix's translation column
    nodes = [{"name": "bone000"}, {"name": "Armature", "children": [0], "translation": [1.0, 2.0, 3.0]}]
    m = gltf._root_parent_matrix(0, {0: 1}, nodes, {0})
    assert [m[i][3] for i in range(3)] == [1.0, 2.0, 3.0]
    assert gltf._root_parent_matrix(0, {}, [{"name": "bone000"}], {0}) == I   # no ancestor -> identity


def _two_part_skinned_glb(path, node_names, mesh_names=None, extras=None):
    """A skinned glTF with 1 bone + TWO mesh parts (distinct POSITION accessors), so import must split + name
    them. ``node_names``/``mesh_names`` set the node/mesh names; ``extras`` sets each mesh node's extras."""
    buf = _gltf_io.GltfBuffer()
    tri = [0, 2, 1]
    meshes, nodes = [], [{"name": "bone000", "translation": [0.0, 0.0, 0.0], "rotation": [0.0, 0.0, 0.0, 1.0]}]
    for i in range(2):
        n = 3 + i                                                # distinct vert counts (3 and 4) -> distinct accessors
        flat = [x for k in range(n) for x in (float(k), 0.0, 0.0)]
        pos = buf.add(flat, _gltf_io.FLOAT, "VEC3", minmax=True)
        joints = buf.add([0, 0, 0, 0] * n, _gltf_io.UNSIGNED_SHORT, "VEC4")
        weights = buf.add([1, 0, 0, 0] * n, _gltf_io.FLOAT, "VEC4")
        idx = buf.add(tri, _gltf_io.UNSIGNED_INT, "SCALAR")
        meshes.append({"name": (mesh_names or node_names)[i],
                       "primitives": [{"attributes": {"POSITION": pos, "JOINTS_0": joints, "WEIGHTS_0": weights},
                                       "indices": idx}]})
        node = {"name": node_names[i], "mesh": i, "skin": 0}
        if extras:
            node["extras"] = extras[i]
        nodes.append(node)
    ibm = buf.add([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1], _gltf_io.FLOAT, "MAT4")
    g = {"scene": 0, "scenes": [{"nodes": [0, 1, 2]}], "nodes": nodes, "meshes": meshes,
         "skins": [{"joints": [0], "inverseBindMatrices": ibm, "skeleton": 0}],
         "accessors": buf.accessors, "bufferViews": buf.bufferViews}
    _gltf_io.write_glb(g, buf.blob, path)


def test_import_carries_part_names_from_nodes():
    """Each FF9 part is its own named glTF mesh/node; import must re-key each kit mesh to that part name
    (Blender's .001 dedup suffix stripped) -- the load-bearing bit for the engine's NAME-keyed branches."""
    import os
    import tempfile
    path = os.path.join(tempfile.gettempdir(), "ff9mk_parts.glb")
    _two_part_skinned_glb(path, ["long_hair", "rubber_band.001"])
    m = gltf.import_gltf(path, scale=1.0)
    assert sorted(me["name"] for me in m["meshes"]) == ["long_hair", "rubber_band"]


def test_import_prefers_ff9_mesh_extra_over_node_name():
    """If Blender renamed the object but kept the ff9_mesh custom property, the extra wins (survives edits)."""
    import os
    import tempfile
    path = os.path.join(tempfile.gettempdir(), "ff9mk_partsx.glb")
    _two_part_skinned_glb(path, ["Cube", "Cube.001"],
                          extras=[{"ff9_mesh": "mesh0"}, {"ff9_mesh": "short_hair"}])
    m = gltf.import_gltf(path, scale=1.0)
    assert sorted(me["name"] for me in m["meshes"]) == ["mesh0", "short_hair"]


def test_import_nameless_part_gets_synthetic_placeholder():
    """A genuinely nameless part must NOT be called 'mesh0' (a real, common FF9 part name) -- it gets a
    synthetic '__part' placeholder so the re-rig routes it through the order-independent count fallback."""
    import os
    import tempfile
    path = os.path.join(tempfile.gettempdir(), "ff9mk_noname.glb")
    _two_part_skinned_glb(path, [None, None], mesh_names=[None, None])
    m = gltf.import_gltf(path, scale=1.0)
    assert all(me["name"].startswith("__part") for me in m["meshes"])


def test_restore_mesh_names_by_name_then_count():
    """Name-match wins (incl. real 'mesh0'); unnamed synthetic placeholders fall to the vertex-count match --
    and a '__part' placeholder never false-matches the real 'mesh0'."""
    orig = [{"name": "long_hair", "verts": [0] * 904}, {"name": "rubber_band", "verts": [0] * 38},
            {"name": "mesh0", "verts": [0] * 1542}, {"name": "short_hair", "verts": [0] * 680}]
    # names present (possibly reordered + a .001 suffix) -> matched by name, not position
    edited = [{"name": "mesh0", "verts": [0] * 1500}, {"name": "short_hair.001", "verts": [0] * 690},
              {"name": "rubber_band", "verts": [0] * 40}, {"name": "long_hair", "verts": [0] * 920}]
    gltf._restore_mesh_names(edited, orig)
    assert [e["name"] for e in edited] == ["mesh0", "short_hair", "rubber_band", "long_hair"]
    # nameless placeholders -> count fallback (920~long_hair, 40~rubber_band, 1500~mesh0, 690~short_hair)
    edited2 = [{"name": "__part0", "verts": [0] * 920}, {"name": "__part1", "verts": [0] * 40},
               {"name": "__part2", "verts": [0] * 1500}, {"name": "__part3", "verts": [0] * 690}]
    gltf._restore_mesh_names(edited2, orig)
    assert [e["name"] for e in edited2] == ["long_hair", "rubber_band", "mesh0", "short_hair"]


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


# ------------------------------------------------- the emit_model_gltf factor-out (p0data-free emission core)
# emit_model_gltf(model, clips, buf, out) is the pure emission body export_gltf delegates to, so a non-p0data
# source (a custom summon built from local ef### bytes) can reuse the proven writer by feeding PRE-DECODED
# clips. These lock its contract offline; the byte-for-byte behavior-preservation vs the public export_gltf is
# the game-gated test below.

def _synthetic_animated_model():
    """A minimal 2-bone / 1-part / untextured model struct (the shape extract.read_model yields) -- enough to
    exercise emit_model_gltf with zero install data."""
    bones = [
        {"name": "bone000", "parent": None, "pos": [0.0, 0.0, 0.0], "rot": [0.0, 0.0, 0.0, 1.0],
         "scale": [1.0, 1.0, 1.0]},
        {"name": "bone001", "parent": "bone000", "pos": [0.0, -10.0, 0.0], "rot": [0.0, 0.0, 0.0, 1.0],
         "scale": [1.0, 1.0, 1.0]},
    ]
    meshes = [{"name": "mesh0", "verts": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
               "normals": None, "uvs": [[0.0, 0.0]] * 3,
               "submeshes": [{"material_idx": 0, "tris": [[0, 1, 2]]}],
               "weights": [[(0, 1.0)], [(1, 1.0)], [(0, 1.0)]]}]
    return {"geo": "GEO_MON_B3_TEST", "geo_id": 9999, "root_bone": "bone000", "prefab_id": 9999,
            "bones": bones, "meshes": meshes, "materials": [{"name": "m0", "texture": None}], "textures": {}}


def _synthetic_clip():
    """A read_clip-shaped struct: one rotating bone (a 90deg yaw over 0.5s)."""
    return {"name": "idle", "sample_rate": 30.0, "length": 0.5,
            "bones": {"bone000": {"bone": 0, "rot": [(0.0, (0.0, 0.0, 0.0, 1.0)),
                                                     (0.5, (0.0, 0.70710678, 0.0, 0.70710678))]}}}


def test_emit_model_gltf_embeds_predecoded_clips_without_p0data(tmp_path):
    """The summons contract: emit_model_gltf writes a valid skinned .glb + embeds an animation from a
    PRE-DECODED (label, key, folder, clip) tuple -- no read_model / _select_anim_keys / read_clip / p0data."""
    out = tmp_path / "synth.glb"
    model = _synthetic_animated_model()
    clips = [("idle", 77, model["geo_id"], _synthetic_clip())]          # folder == geo_id -> not a donor clip
    man = gltf.emit_model_gltf(model, clips, _gltf_io.GltfBuffer(), out, bone_labels=False)
    assert man["anims"] == ["idle"] and man["donor_anims"] == []
    g, _ = _gltf_io.read_glb(out)
    assert len(g["skins"][0]["joints"]) == 2 and len(g["meshes"]) == 1  # skeleton + mesh still emitted
    assert len(g["animations"]) == 1
    a0 = g["animations"][0]
    assert a0["name"] == "idle" and a0["extras"]["ff9_anim_key"] == 77
    assert [c["target"]["path"] for c in a0["channels"]] == ["rotation"]  # a 2-key constant pos is skipped
    assert a0["channels"][0]["target"]["node"] == 0                       # rotation drives bone000 (node 0)


def test_emit_model_gltf_none_clip_is_skipped_like_an_unresolved_read(tmp_path):
    """A None clip in the list is skipped (parity with read_clip returning None before the factor-out); an
    empty clip list -> no animations block at all."""
    model = _synthetic_animated_model()
    a = gltf.emit_model_gltf(model, [("gone", 5, 9999, None)], _gltf_io.GltfBuffer(), tmp_path / "a.glb",
                             bone_labels=False)
    assert a["anims"] == []
    g, _ = _gltf_io.read_glb(tmp_path / "a.glb")
    assert "animations" not in g
    b = gltf.emit_model_gltf(model, [], _gltf_io.GltfBuffer(), tmp_path / "b.glb", bone_labels=False)
    assert b["anims"] == []


def test_emit_model_gltf_label_overrides_and_donor_folder(tmp_path):
    """label_overrides[key] renames the Action; a clip whose folder != model geo_id is reported as a DONOR
    clip in the manifest (both behaviors carried verbatim from export_gltf's emission loop)."""
    out = tmp_path / "donor.glb"
    model = _synthetic_animated_model()
    clips = [("idle", 77, 4242, _synthetic_clip())]                     # folder 4242 != geo_id 9999 -> donor
    man = gltf.emit_model_gltf(model, clips, _gltf_io.GltfBuffer(), out,
                               label_overrides={77: "23_attack"}, bone_labels=False)
    assert man["anims"] == ["23_attack"]
    assert [d["folder"] for d in man["donor_anims"]] == [4242]
    assert man["donor_anims"][0]["labels"] == ["23_attack"]
    g, _ = _gltf_io.read_glb(out)
    assert g["animations"][0]["name"] == "23_attack"
    assert g["animations"][0]["extras"]["ff9_anim_label"] == "23_attack"


def test_export_gltf_equals_emit_from_predecoded_clips(tmp_path):
    """THE seam (game-gated): the public export_gltf(token) must be BYTE-IDENTICAL to emit_model_gltf(model,
    clips, buf) fed clips resolved the exact way the wrapper resolves them (read_model + p0data5
    _select_anim_keys + read_clip). Proves the p0data factor-out is behavior-preserving on a real, animated
    model. Skips cleanly without the install."""
    pytest.importorskip("UnityPy")
    from ff9mapkit import config
    from ff9mapkit.models import extract
    try:
        game = config.find_game_path()
    except config.ConfigError:
        pytest.skip("no FF9 install configured")
    if not all((game / "StreamingAssets" / n).exists() for n in ("p0data4.bin", "p0data5.bin")):
        pytest.skip("FF9 install missing StreamingAssets/p0data4.bin or p0data5.bin")

    token, anims = "GEO_MAIN_F0_ZDN", "auto"
    # (A) the factored core, fed clips resolved identically to export_gltf's wrapper (sites 1-3, by hand)
    model = extract.read_model(token)
    env5 = extract._unitypy().load(str(game / "StreamingAssets" / "p0data5.bin"))
    selected = gltf._select_anim_keys(model["geo"], model["geo_id"], anims, env5)
    clips = [(lbl, key, folder, _gltf_io.read_clip(env5, folder, key)) for lbl, key, folder in selected]
    a = tmp_path / "core.glb"
    man_a = gltf.emit_model_gltf(model, clips, _gltf_io.GltfBuffer(), a)
    # (B) the public path
    b = tmp_path / "public.glb"
    man_b = gltf.export_gltf(token, b, anims=anims)
    assert a.read_bytes() == b.read_bytes()                            # byte-identical -> the seam preserves it
    assert man_a["anims"] == man_b["anims"] and len(man_a["anims"]) >= 1   # and the clip path was exercised
