"""Offline tests for the custom-model exporter (no install / UnityPy needed).

Covers the load-bearing pure logic: the quaternion<->euler(XYZ) conversion is the EXACT inverse of
Memoria's ``SetupFromEulerAngles`` (q = qz*qy*qx), and the skinned FBX-ASCII emitter produces the node
tree + connections the engine's ``FbxAsciiReader``/``FbxDocument`` parse. Extraction from p0data is
covered by the in-game fidelity test (a human playtest), not here.
"""
import math

import pytest

from ff9mapkit.models import fbx_skin


def _norm(q):
    n = math.sqrt(sum(c * c for c in q)) or 1.0
    return tuple(c / n for c in q)


# a spread of rotations incl. near-identity, axis-aligned, and arbitrary
_QUATS = [
    (0.0, 0.0, 0.0, 1.0),
    _norm((0.5, 0.5, -0.5, 0.5)),
    _norm((0.0, -0.7071, 0.0, 0.7071)),
    _norm((0.4469, 0.0, 0.0, 0.8946)),
    _norm((0.13, -0.62, 0.41, 0.66)),
    _norm((0.9, 0.1, -0.2, 0.35)),
    _norm((0.0005, -0.7071, -0.0005, 0.7071)),
]


@pytest.mark.parametrize("q", _QUATS)
def test_euler_xyz_roundtrips_through_engine_composition(q):
    """quat -> euler(XYZ) -> SetupFromEulerAngles must reproduce the SAME rotation (double-cover)."""
    e = fbx_skin.quat_to_euler_xyz(q)
    recomposed = fbx_skin.setup_from_euler_xyz(*e)
    dot = sum(a * b for a, b in zip(_norm(recomposed), q))
    assert abs(abs(dot) - 1.0) < 1e-5, f"euler round-trip drifted: {q} -> {e} -> {recomposed} (dot {dot})"


def test_setup_from_euler_matches_known_axis_rotation():
    """A pure 90deg X rotation composes to the expected quaternion."""
    q = fbx_skin.setup_from_euler_xyz(90.0, 0.0, 0.0)
    assert abs(q[0] - math.sin(math.radians(45))) < 1e-6
    assert abs(q[3] - math.cos(math.radians(45))) < 1e-6
    assert abs(q[1]) < 1e-6 and abs(q[2]) < 1e-6


def _synthetic_model():
    """A tiny 2-bone, 1-mesh skinned model in the extractor's output shape."""
    return {
        "geo": "GEO_NPC_F0_TST", "geo_id": 9999, "type_int": 4, "root_bone": "bone000",
        "bones": [
            {"name": "bone000", "parent": None, "pos": [0.0, 0.0, 0.0],
             "rot": [0.0, 0.0, 0.0, 1.0], "scale": [1.0, 1.0, 1.0]},
            {"name": "bone005", "parent": "bone000", "pos": [0.0, 10.0, 0.0],
             "rot": list(_norm((0.4469, 0.0, 0.0, 0.8946))), "scale": [1.0, 1.0, 1.0]},
        ],
        "meshes": [{
            "name": "mesh0",
            "verts": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]],
            "normals": [[0, 0, 1]] * 4,
            "uvs": [[0, 0], [1, 0], [0, 1], [1, 1]],
            "submeshes": [{"material_idx": 0, "tris": [[0, 1, 2], [1, 3, 2]]}],
            "weights": [[(0, 1.0)], [(0, 1.0)], [(5, 1.0)], [(5, 1.0)]],
        }],
        "materials": [{"name": "mesh0_mat0", "texture": "9999_0"}],
        "textures": {},
    }


def test_emit_skinned_fbx_structure():
    text, meta = fbx_skin.emit_skinned_fbx(_synthetic_model())
    assert meta["bones"] == 2 and meta["meshes"] == 1
    assert meta["euler_max_err"] < 1e-5
    # balanced braces
    assert text.count("{") == text.count("}")
    # the root bone is typed Root (engine forces its BoneId=0); the other is a LimbNode
    assert '"Model::bone000", "Root"' in text
    assert '"Model::bone005", "LimbNode"' in text
    # geometry + skin + clusters + connections present
    assert 'Geometry: ' in text and 'Objects: {' in text and 'Connections: {' in text
    assert '"Deformer", "Skin"' in text and '"SubDeformer", "Cluster"' in text
    # polygon-end convention: the last index of a face is negated (2 -> -3)
    assert 'PolygonVertexIndex' in text
    # a bone parent connection + a texture OP connection exist
    assert 'C: "OO"' in text and 'C: "OP"' in text


def test_emitted_fbx_validates_against_engine_reader():
    """The emitter's own self-check must accept its output (parse via the FbxAsciiReader port)."""
    from ff9mapkit.models import fbx_validate
    text, _ = fbx_skin.emit_skinned_fbx(_synthetic_model())
    fbx_validate.validate(text)   # raises on any syntax / structural problem


def test_validator_rejects_missing_node_colon_like_the_engine():
    """Regression: a node name without a colon (the bug that returned a null Vivi) must be rejected at the
    same spot the engine reports -- `Properties70 {` (no colon) -> 'Unexpected {, expected :'."""
    from ff9mapkit.models import fbx_validate
    bad = ('; FBX 7.4.0 project file\nObjects: {\n    Model: 1, "M", "Root" {\n'
           '        Version: 232\n        Properties70 {\n        }\n    }\n}\n')
    with pytest.raises(fbx_validate.FbxParseError) as ei:
        fbx_validate.parse(bad)
    assert "expected ':'" in str(ei.value)
    assert ei.value.line == 5   # the `Properties70 {` line


def test_cluster_links_to_bone_via_engine_lookup():
    """Regression (the T-pose bug): the cluster->bone connection must be `C: "OO", boneId, clusterId` so
    the engine's GetFirstConnectedIndex(clusterId, asChild=false) resolves it (matches Properties[2]==
    clusterId, takes the bone from Properties[1]). The reversed direction links NO subdeformers, so
    GetBoneWeights returns null, hasAnim=false, anim=null, and the ENTIRE skeleton is dropped (model
    renders as raw un-skinned verts / T-pose)."""
    from ff9mapkit.models import fbx_validate
    text, _ = fbx_skin.emit_skinned_fbx(_synthetic_model())
    nodes = fbx_validate.parse(text)
    top = {n.name: n for n in nodes}
    objs, conns = top["Objects"], top["Connections"]

    def nid(n):
        return int(n.props[0])
    bone_ids = {nid(n) for n in objs.children
                if n and n.name == "Model" and len(n.props) >= 3 and n.props[2] in ("LimbNode", "Root")}
    cluster_ids = {nid(n) for n in objs.children
                   if n and n.name == "Deformer" and len(n.props) >= 3 and n.props[2] == "Cluster"}
    assert cluster_ids, "synthetic skinned model should emit clusters"
    oo = [c for c in conns.children if c and c.name == "C" and len(c.props) == 3 and c.props[0] == "OO"]
    for cid in cluster_ids:
        # engine lookup: connection whose Properties[2] == clusterId, bone from Properties[1]
        linked = [int(c.props[1]) for c in oo if int(c.props[2]) == cid and int(c.props[1]) in bone_ids]
        assert linked, f"cluster {cid} has no bone linked via the engine's asChild=false lookup"


def test_polygon_index_negates_last_vertex():
    text, _ = fbx_skin.emit_skinned_fbx(_synthetic_model())
    # extract the PolygonVertexIndex array body
    i = text.index("PolygonVertexIndex")
    seg = text[i:i + 120]
    # tri [0,1,2] -> 0,1,-3 ; tri [1,3,2] -> 1,3,-3
    assert "-3" in seg, seg
