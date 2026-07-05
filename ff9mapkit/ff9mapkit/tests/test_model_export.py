"""Offline tests for the custom-model exporter (no install / UnityPy needed).

Covers the load-bearing pure logic: the quaternion<->euler(XYZ) conversion is the EXACT inverse of
Memoria's ``SetupFromEulerAngles`` (q = qz*qy*qx), and the skinned FBX-ASCII emitter produces the node
tree + connections the engine's ``FbxAsciiReader``/``FbxDocument`` parse. Extraction from p0data is
covered by the in-game fidelity test (a human playtest), not here.
"""
import math

import pytest

from ff9mapkit.models import export, fbx_skin


# --------------------------------------------------------------------- deploy path (weapon special-case)
def test_weapon_deploys_to_battlemodel_tree():
    """GEO_WEP_* (type 6) must go to BattleMap/BattleModel/6/{id}/, NOT Models/6/ -- matching the engine's
    GetRenameModelPath GEO_WEP special-case (ModelFactory.cs:26-34). The wrong path never loads in-game."""
    assert export.model_dir_parts(6, 123) == ("BattleMap", "BattleModel", "6", "123")
    assert export.engine_rel_path(6, 123) == "StreamingAssets/Assets/Resources/BattleMap/BattleModel/6/123/123.fbx"


@pytest.mark.parametrize("type_int", [1, 2, 3, 4, 5])   # acc / main / mon / npc / sub
def test_nonweapon_deploys_to_models_tree(type_int):
    assert export.model_dir_parts(type_int, 456) == ("Models", str(type_int), "456")
    assert export.engine_rel_path(type_int, 456) == \
        f"StreamingAssets/Assets/Resources/Models/{type_int}/456/456.fbx"


def test_weapon_reads_from_p0data2_bundle():
    """Weapons live in p0data2 (battlemap/battlemodel/6/), not p0data4 — the EXTRACTOR must pick the right
    bundle (the deploy-path fix is only half; the read side needs the weapon special-case too)."""
    from ff9mapkit.models import extract
    assert extract._model_bundle_index(6) == 2               # weapon
    for t in (1, 2, 3, 4, 5):
        assert extract._model_bundle_index(t) == 4           # everything else


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


# --------------------------------------------------------------------------- bind correction (robust)
# The engine's ModelImporter recomputes each bone's bindpose from the emitted REST pose
# (bindpose = bone.worldToLocalMatrix) and DISCARDS the mesh's stored m_BindPose. FF9 baked a
# coordinate transform into m_BindPose that the rest pose doesn't reproduce, so the exporter re-bakes
# it into the verts. These tests simulate BOTH skinning pipelines -- the original (bone world * stored
# m_BindPose) and the engine's (bone world * worldToLocal-of-rest, on the re-baked verts) -- and assert
# they agree through animation, so the algebra is verified independently of the extractor.

from ff9mapkit.models import extract  # noqa: E402
from ff9mapkit.models.fbx_skin import _mat_trs, _mat_mul, _mat_inv  # noqa: E402


def _world_mats(bones, locals_by_name):
    """Accumulate each bone's world 4x4 from a name->local-4x4 map (parent-composed)."""
    by = {b["name"]: b for b in bones}
    cache = {}

    def w(name):
        if name in cache:
            return cache[name]
        b = by[name]
        cache[name] = locals_by_name[name] if b["parent"] is None \
            else _mat_mul(w(b["parent"]), locals_by_name[name])
        return cache[name]

    return {b["name"]: w(b["name"]) for b in bones}


def _rest_locals(bones):
    return {b["name"]: _mat_trs(b["pos"], b["rot"], b["scale"]) for b in bones}


def _skin_vertex(v, infl, world_by_name, bindpose_by_name):
    """P = sum_i w_i * boneWorld_i * bindpose_i * v  (the Unity linear-blend skin, one vertex)."""
    out = [0.0, 0.0, 0.0]
    for bnum, wt in infl:
        name = f"bone{bnum:03d}"
        m = _mat_mul(world_by_name[name], bindpose_by_name[name])
        out = [out[k] + wt * (m[k][0] * v[0] + m[k][1] * v[1] + m[k][2] * v[2] + m[k][3])
               for k in range(3)]
    return out


def _two_bone_skeleton():
    """Root bone (rotated, so worldToLocal != identity) + one child; a non-trivial rest frame."""
    return [
        {"name": "bone000", "parent": None, "pos": [1.0, 2.0, -3.0],
         "rot": list(_norm((0.13, -0.62, 0.41, 0.66))), "scale": [1.0, 1.0, 1.0]},
        {"name": "bone005", "parent": "bone000", "pos": [0.0, 10.0, 0.0],
         "rot": list(_norm((0.4469, 0.0, 0.0, 0.8946))), "scale": [1.0, 1.0, 1.0]},
    ]


def _bindposes_for(bones, G):
    """m_BindPose per bone consistent with rest AND a baked transform G:
    bindpose_i = worldToLocal(rest_i) * G  =>  boneWorld_i * bindpose_i = G (the recovered correction)."""
    world = _world_mats(bones, _rest_locals(bones))
    return {name: _mat_mul(_mat_inv(world[name]), G) for name in world}


def _apply_engine_pipeline(bones, mesh_infl, mesh_verts, samples):
    """Run the exporter's per-mesh correction (extract._bind_correction + _affine bake) then simulate
    the ENGINE skin (bindpose = worldToLocal of rest) at a given pose. Returns a fn(pose_locals)->verts."""
    G = extract._bind_correction(bones, samples)
    baked = [extract._affine(G, v) if G is not None else list(v) for v in mesh_verts]
    rest = _rest_locals(bones)

    def render(pose_locals):
        world = _world_mats(bones, pose_locals)
        eng_bind = {b["name"]: _mat_inv(_world_mats(bones, rest)[b["name"]]) for b in bones}
        return [_skin_vertex(baked[i], mesh_infl[i], world, eng_bind) for i in range(len(baked))]

    return G, render


def _original_render(bones, mesh_infl, mesh_verts, G, pose_locals):
    world = _world_mats(bones, pose_locals)
    orig_bind = _bindposes_for(bones, G)
    return [_skin_vertex(mesh_verts[i], mesh_infl[i], world, orig_bind) for i in range(len(mesh_verts))]


def _animated_pose(bones):
    """A non-rest pose: rotate/translate every bone's local so worldToLocal(rest) is genuinely exercised."""
    loc = _rest_locals(bones)
    out = {}
    for b in bones:
        m = [row[:] for row in loc[b["name"]]]
        # nudge the child bone (bone005) with an extra rotation via a fresh TRS
        if b["name"] == "bone005":
            m = _mat_trs([0.5, 9.0, 1.0], list(_norm((0.2, 0.1, -0.5, 0.83))), [1.0, 1.0, 1.0])
        out[b["name"]] = m
    return out


def _close(a, b, eps=1e-6):
    return all(abs(x - y) < eps for va, vb in zip(a, b) for x, y in zip(va, vb))


def test_bind_correction_recovers_a_global_flip():
    """G = diag(1,-1,-1) (Vivi's 180deg-X bake) is recovered from the mesh's bindposes and reproduces the
    original skin at rest AND animated -- the constant-G path (unchanged by the per-mesh refactor)."""
    bones = _two_bone_skeleton()
    G = [[1, 0, 0, 0], [0, -1, 0, 0], [0, 0, -1, 0], [0, 0, 0, 1]]
    verts = [[3.0, 4.0, 5.0], [-2.0, 1.0, 7.0], [0.0, -6.0, 2.0]]
    infl = [[(0, 1.0)], [(5, 1.0)], [(0, 0.5), (5, 0.5)]]
    samples = [(name, bp) for name, bp in _bindposes_for(bones, G).items()]
    recovered, render = _apply_engine_pipeline(bones, infl, verts, samples)
    assert recovered is not None
    for pose in (_rest_locals(bones), _animated_pose(bones)):
        assert _close(render(pose), _original_render(bones, infl, verts, G, pose))


def test_per_mesh_correction_handles_divergent_G_on_a_shared_bone():
    """The Garnet case: two meshes share the skeleton but were baked with DIFFERENT transforms (one
    identity, one 180deg-X flip). A single global bake mis-orients the odd mesh out; the per-mesh bake
    (each mesh corrected by its OWN recovered G) reproduces BOTH meshes' original skin -- even though
    they weight a SHARED bone whose engine bindpose is identical for both."""
    bones = _two_bone_skeleton()
    G_body = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]           # identity
    G_hair = [[1, 0, 0, 0], [0, -1, 0, 0], [0, 0, -1, 0], [0, 0, 0, 1]]         # 180deg X
    # both meshes weight the SHARED root bone000 (plus the child) -- the crux of the shared-bone proof
    verts = [[2.0, 3.0, 4.0], [-1.0, 5.0, 0.5]]
    infl = [[(0, 0.7), (5, 0.3)], [(0, 1.0)]]

    for G in (G_body, G_hair):
        samples = list(_bindposes_for(bones, G).items())
        recovered, render = _apply_engine_pipeline(bones, infl, verts, samples)
        assert recovered is not None
        # recovered G matches the mesh's own bake (rotation 3x3)
        assert all(abs(recovered[r][c] - G[r][c]) < 1e-6 for r in range(3) for c in range(3))
        for pose in (_rest_locals(bones), _animated_pose(bones)):
            got = render(pose)
            want = _original_render(bones, infl, verts, G, pose)
            assert _close(got, want), f"G={G} pose-mismatch: {got} != {want}"


def test_within_mesh_split_with_no_majority_is_left_unbaked():
    """A 50/50 split (one bone identity, one flipped) has no majority family -> _bind_correction returns
    None and the verts ship unbaked, rather than gamble on one family."""
    bones = _two_bone_skeleton()
    world = _world_mats(bones, _rest_locals(bones))
    Gid = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    Gflip = [[1, 0, 0, 0], [0, -1, 0, 0], [0, 0, -1, 0], [0, 0, 0, 1]]
    samples = [("bone000", _mat_mul(_mat_inv(world["bone000"]), Gid)),
               ("bone005", _mat_mul(_mat_inv(world["bone005"]), Gflip))]
    assert extract._bind_correction(bones, samples) is None


def _three_bone_skeleton():
    return _two_bone_skeleton() + [
        {"name": "bone009", "parent": "bone000", "pos": [3.0, -1.0, 2.0],
         "rot": list(_norm((0.0, 0.3, 0.0, 0.95))), "scale": [1.0, 1.0, 1.0]}]


def test_dominant_family_wins_when_a_majority_agrees():
    """The EFM/MRC fix: 2 bones flipped + 1 identity outlier -> the dominant (flip) family is baked, so
    a mostly-flipped mesh is corrected instead of shipping un-baked (which left it 180deg wrong)."""
    bones = _three_bone_skeleton()
    world = _world_mats(bones, _rest_locals(bones))
    Gid = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    Gflip = [[1, 0, 0, 0], [0, -1, 0, 0], [0, 0, -1, 0], [0, 0, 0, 1]]
    samples = [("bone000", _mat_mul(_mat_inv(world["bone000"]), Gflip)),
               ("bone005", _mat_mul(_mat_inv(world["bone005"]), Gflip)),
               ("bone009", _mat_mul(_mat_inv(world["bone009"]), Gid))]
    G = extract._bind_correction(bones, samples)
    assert G is not None
    assert all(abs(G[r][c] - Gflip[r][c]) < 1e-6 for r in range(3) for c in range(3))


def test_small_per_bone_jitter_still_bakes_one_family():
    """EFM's real shape: every bone is the same flip family but with a few-degree per-bone jitter. The
    old all-or-nothing (dev < 1e-2) rejected the whole mesh; the family clustering still bakes it."""
    bones = _three_bone_skeleton()
    world = _world_mats(bones, _rest_locals(bones))
    # a flip plus a ~2deg wobble baked slightly differently into each bone's bindpose
    def wobble(eps):
        s = math.sin(math.radians(eps))
        c = math.cos(math.radians(eps))
        return [[1, 0, 0, 0], [0, -c, s, 0], [0, -s, -c, 0], [0, 0, 0, 1]]
    samples = [("bone000", _mat_mul(_mat_inv(world["bone000"]), wobble(0.0))),
               ("bone005", _mat_mul(_mat_inv(world["bone005"]), wobble(2.0))),
               ("bone009", _mat_mul(_mat_inv(world["bone009"]), wobble(-1.5)))]
    G = extract._bind_correction(bones, samples)
    assert G is not None                                   # one family -> baked (old rule returned None)
    assert G[1][1] < -0.9 and G[2][2] < -0.9               # it's the flip family


# --------------------------------------------------------------- nested-child mesh merge (engine drop fix)

def _mesh(name, nverts, mat_idx, parent=None, base=0):
    """A minimal mesh dict: nverts verts, one submesh of nverts//3 tris pointing at mat_idx."""
    verts = [[float(base + i), 0.0, 0.0] for i in range(nverts)]
    tris = [[i, i + 1, i + 2] for i in range(0, nverts - 2, 3)]
    return {"name": name, "verts": verts, "normals": [[0.0, 1.0, 0.0]] * nverts,
            "uvs": [[0.0, 0.0]] * nverts, "submeshes": [{"material_idx": mat_idx, "tris": tris}],
            "weights": [[(0, 1.0)]] * nverts, "parent": parent}


def test_merge_folds_nested_child_into_same_texture_sibling():
    """Garnet's case: a nested child (rubber_band, tex 185_0) merges into the largest same-texture top-level
    mesh (body), tris re-based by the body's vert count; the child is removed."""
    model = {"materials": [{"texture": "185_1"}, {"texture": "185_0"}, {"texture": "185_0"}, {"texture": "185_2"}],
             "meshes": [_mesh("long_hair", 9, 0), _mesh("rubber_band", 6, 1, parent="long_hair"),
                        _mesh("mesh0", 12, 2, base=100), _mesh("short_hair", 9, 3)]}
    merged = extract.merge_nested_child_meshes(model)
    assert merged == [("rubber_band", "mesh0")]
    names = [m["name"] for m in model["meshes"]]
    assert names == ["long_hair", "mesh0", "short_hair"]     # rubber_band folded away
    body = next(m for m in model["meshes"] if m["name"] == "mesh0")
    assert len(body["verts"]) == 18                          # 12 body + 6 scrunchie
    # the child's triangle got re-based by the body's original vert count (12)
    assert [12, 13, 14] in body["submeshes"][0]["tris"]


def test_merge_leaves_child_with_no_same_texture_target_and_warns():
    """A nested child whose texture no top-level sibling shares (GEO_MON_F0_EFM) is left standalone + warned
    -- merging would repaint it (one-material-per-mesh)."""
    warned = []
    model = {"materials": [{"texture": "A"}, {"texture": "B"}],
             "meshes": [_mesh("mesh0", 12, 0), _mesh("mesh1", 6, 1, parent="mesh0")]}
    merged = extract.merge_nested_child_meshes(model, warn=warned.append)
    assert merged == []
    assert [m["name"] for m in model["meshes"]] == ["mesh0", "mesh1"]   # untouched
    assert warned and "mesh1" in warned[0]


def test_merge_is_a_noop_without_nesting():
    """Every model without nested meshes (517 of 520) passes through unchanged."""
    model = {"materials": [{"texture": "T"}],
             "meshes": [_mesh("mesh0", 12, 0), _mesh("mesh1", 9, 0)]}
    before = [m["name"] for m in model["meshes"]]
    assert extract.merge_nested_child_meshes(model) == []
    assert [m["name"] for m in model["meshes"]] == before
