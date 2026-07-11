"""Offline tests for the bone display-label layer (models/bone_labels.py) -- no install needed.

The load-bearing invariants:
  * labels are DISPLAY ONLY -- a labeled glTF imports back to the identical canonical Model struct
    (raw ``boneNNN`` names) as a plain one, so nothing engine-facing ever changes;
  * the lenient name parse accepts every form Blender can hand back (raw / labeled / ``.001`` deduped);
  * the heuristics read a synthetic humanoid the way a rigger would, and refuse (return {}) rather
    than guess on props and unparseable rigs;
  * the baked DB carries the proven anchors (Zidane's weapon hand = his RIGHT hand at bone013 --
    pinned by BattleParameters.csv WeaponBone + the Orichalcum off-hand overlay on bone006).
"""
import pytest

from ff9mapkit.models import bone_labels as BL
from ff9mapkit.models import gltf as mgltf


# ---------------------------------------------------------------- synthetic rigs

def _b(num, parent, pos):
    return {"name": f"bone{num:03d}", "parent": None if parent is None else f"bone{parent:03d}",
            "pos": list(pos), "rot": [0.0, 0.0, 0.0, 1.0], "scale": [1.0, 1.0, 1.0]}


def humanoid():
    """A Zidane-shaped biped in FF9 model space (Y-DOWN, faces -z, +x = character's RIGHT):
    root/spine/chest pivots, neck+head, two arms via chest, hips + leg pivots, a +z tail."""
    B = [
        _b(0, None, (0, -240, 0)),
        _b(1, 0, (0, 0, 0)),                    # upper pivot (at root pos)
        _b(2, 1, (0, -84, 10)),                 # chest (h 324)
        _b(3, 2, (-47, 21, 0)),                 # L shoulder joint
        _b(4, 3, (-48, 48, 0)),                 # L elbow
        _b(5, 4, (-57, 57, 0)),                 # L wrist
        _b(6, 5, (-7, 25, 0)),                  # L hand
        _b(7, 1, (0, -84, 10)),                 # neck pivot (co-located with chest)
        _b(8, 7, (0, -25, -2)),                 # head (h 349)
        _b(9, 1, (0, -84, 10)),                 # R clavicle pivot
        _b(10, 9, (47, 21, 0)),                 # R shoulder joint
        _b(11, 10, (48, 48, 0)),
        _b(12, 11, (57, 57, 0)),
        _b(13, 12, (7, 25, 0)),                 # R hand (the weapon hand)
        _b(14, 0, (0, 0, 0)),                   # lower pivot
        _b(15, 14, (0, 42, 0)),                 # L hip pivot (centre, below root)
        _b(16, 15, (-25, 0, 0)),                # L thigh
        _b(17, 16, (0, 80, 0)),                 # L knee
        _b(18, 17, (0, 74, 10)),                # L foot (h 44)
        _b(19, 14, (0, 42, 0)),                 # R hip pivot
        _b(20, 19, (25, 0, 0)),
        _b(21, 20, (0, 80, 0)),
        _b(22, 21, (0, 74, 10)),
        _b(23, 14, (0, 42, 0)),                 # tail pivot
        _b(24, 23, (0, -19, 32)),               # tail veers +z (behind)
        _b(25, 24, (0, 0, 137)),
        _b(26, 25, (0, 0, 81)),
    ]
    return B


def test_signature_is_topology_only():
    rig = humanoid()
    sig = BL.signature(rig)
    assert sig.startswith("0>-1,1>0,2>1,")
    # moving a bone does NOT change the signature; reparenting DOES
    moved = [dict(b, pos=[9, 9, 9]) for b in rig]
    assert BL.signature(moved) == sig
    rewired = [dict(b) for b in rig]
    rewired[7]["parent"] = "bone002"
    assert BL.signature(rewired) != sig


def test_humanoid_labels_read_like_a_rigger():
    labs = BL.label_skeleton(humanoid(), group="main")
    assert labs[0] == "root" and labs[1] == "spine" and labs[2] == "chest"
    assert labs[7] == "neck" and labs[8] == "head"
    assert labs[14] == "hips" and labs[15] == "L_hip" and labs[19] == "R_hip"
    # +x = the character's RIGHT (the empirically pinned convention)
    assert labs[3] == "L_upper_arm" and labs[10] == "R_upper_arm"
    assert labs[13] == "R_hand_end" and labs[6] == "L_hand_end"
    assert labs[16] == "L_thigh" and labs[17] == "L_shin" and labs[18] == "L_foot"
    assert labs[23] == "tail_base" and labs[24] == "tail_01" and labs[26] == "tail_03"
    assert labs[9] == "R_shoulder"                       # the co-located clavicle pivot


def test_props_and_unparseable_rigs_stay_unlabeled():
    # prop groups are never anatomy
    assert BL.label_skeleton(humanoid(), group="acc") == {}
    assert BL.label_skeleton(humanoid(), group="wep") == {}
    # a pure centre chain (a snake / a gate) has no limbs -> refuse rather than guess
    chain = [_b(0, None, (0, -100, 0))] + [_b(i, i - 1, (0, -10, 20)) for i in range(1, 8)]
    assert BL.label_skeleton(chain, group="mon") == {}
    # tiny rigs refuse
    assert BL.label_skeleton([_b(0, None, (0, 0, 0))], group="mon") == {}


def test_accessory_mesh_names_override_anatomy():
    labs = BL.label_skeleton(humanoid(), group="main",
                             smr_bones=[("mesh0", list(range(0, 24))),
                                        ("rubber_band", [26])])
    assert labs[26] == "rubber_band"                     # named-mesh-exclusive bone
    assert labs[24] == "tail_01"                         # generic-mesh bones keep anatomy


def test_vote_labels_majority_and_drop():
    a = {1: "chest", 2: "L_hand"}
    b = {1: "chest", 2: "R_hand"}
    c = {1: "chest", 2: "L_hand", 3: "head"}
    v = BL.vote_labels([a, b, c])
    assert v[1] == "chest"
    assert v[2] == "L_hand"                              # 2 of 3 agree
    assert 3 not in v                                    # 1 of 3 is not a majority


def test_bone_num_lenient_accepts_every_blender_form():
    assert BL.bone_num_lenient("bone012") == 12
    assert BL.bone_num_lenient("bone012_R_hand") == 12
    assert BL.bone_num_lenient("bone012_R_hand.001") == 12
    assert BL.bone_num_lenient("bone012.003") == 12
    assert BL.bone_num_lenient("bone012_tail_01") == 12
    assert BL.bone_num_lenient("Armature") is None
    assert BL.bone_num_lenient("bone") is None
    assert BL.bone_num_lenient(None) is None


def test_decorate():
    assert BL.decorate("bone012", {12: "R_hand"}) == "bone012_R_hand"
    assert BL.decorate("bone012", {}) == "bone012"
    assert BL.decorate("bone012", {3: "head"}) == "bone012"


# ---------------------------------------------------------------- baked DB anchors

def test_baked_db_carries_the_weapon_hand_anchors():
    from ff9mapkit._bonelabeldb import BONE_LABELS, PREFAB_LABELS
    assert BONE_LABELS and isinstance(next(iter(BONE_LABELS)), str)
    # Zidane's family (prefab 98): bone013 = the battle WeaponBone = his RIGHT hand;
    # bone006 = the Orichalcum off-hand (engine second-weapon Attachment 6) = his LEFT.
    zdn = [labs for labs in BONE_LABELS.values()
           if labs.get(13, "").startswith("R_hand") and labs.get(6, "").startswith("L_hand")
           and labs.get(0) == "root" and labs.get(24, "").startswith("tail")]
    assert zdn, "Zidane's family lost its weapon-hand labels -- did the L/R convention flip?"
    # Garnet's scrunchie: labeled from its MESH name, via family consensus or her prefab override
    grn_override = PREFAB_LABELS.get(185, {})
    grn_family = [labs for labs in BONE_LABELS.values() if labs.get(22) == "rubber_band"]
    assert grn_override.get(22) == "rubber_band" or grn_family


def test_labels_for_unknown_signature_falls_back_to_live_heuristics():
    # perturb the topology so the signature can't be a baked FF9 family: reparent the neck pivot
    # under the chest (the station logic still finds it) and grow the tail by one bone
    rig = humanoid()
    rig[7]["parent"] = "bone002"
    rig[7]["pos"] = [0.0, 0.0, 0.0]              # keep it co-located with the chest station
    rig.append(_b(27, 26, (0.0, 0.0, 40.0)))
    from ff9mapkit._bonelabeldb import BONE_LABELS
    assert BL.signature(rig) not in BONE_LABELS
    labs = BL.labels_for(rig, geo="GEO_MON_B3_TEST")
    assert labs.get(0) == "root" and labs.get(13) == "R_hand_end"
    assert labs.get(7) == "neck" and labs.get(27) == "tail_04"


# ---------------------------------------------------------------- glTF round-trip parity

def _tiny_model(bones):
    nb = len(bones)
    verts = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
    return {"geo": "GEO_MON_B3_TEST", "geo_id": 9999, "type_int": 3, "root_bone": "bone000",
            "prefab_geo": "GEO_MON_B3_TEST", "prefab_id": 9999, "prefab_tint": 3,
            "bones": bones,
            "meshes": [{"name": "mesh0", "verts": verts, "normals": None,
                        "uvs": [[0.0, 0.0]] * 3,
                        "submeshes": [{"material_idx": 0, "tris": [[0, 1, 2]]}],
                        "weights": [[(0, 1.0)], [(13, 1.0)], [(8, 1.0)]], "parent": None}],
            "materials": [{"name": "m0", "texture": None}], "textures": {},
            "bind_correction": None, "per_mesh_bind": [None]}


def test_labeled_glb_imports_identically_to_plain(tmp_path):
    """THE invariant: labels never change what reaches the engine. A labeled .glb and a plain .glb
    of the same model parse back to the same canonical Model struct (raw boneNNN names, same
    weights), and the labeled node names decode via the lenient parser."""
    rig = humanoid()
    p1 = tmp_path / "labeled.glb"
    p2 = tmp_path / "plain.glb"
    mgltf.export_gltf("ignored", p1, anims="none", _model=_tiny_model(rig))
    mgltf.export_gltf("ignored", p2, anims="none", _model=_tiny_model(rig), bone_labels=False)
    a = mgltf.import_gltf(p1)
    b = mgltf.import_gltf(p2)
    assert [x["name"] for x in a["bones"]] == [f"bone{i:03d}" for i in range(len(rig))]
    assert a["bones"] == b["bones"]
    assert a["meshes"][0]["weights"] == b["meshes"][0]["weights"]
    # the labeled file really is labeled (display names differ, extras carry the number)
    from ff9mapkit.models import _gltf_io
    g, _ = _gltf_io.read_glb(p1)
    named = {n["name"] for n in g["nodes"] if "extras" in n and "ff9_bone_num" in n["extras"]}
    assert "bone013_R_hand_end" in named and "bone000_root" in named
    g2, _ = _gltf_io.read_glb(p2)
    assert {n.get("name") for n in g2["nodes"] if str(n.get("name", "")).startswith("bone013")} \
        == {"bone013"}


def test_import_rejects_a_truly_foreign_bone_name(tmp_path):
    p = tmp_path / "renamed.glb"
    mgltf.export_gltf("ignored", p, anims="none", _model=_tiny_model(humanoid()))
    from ff9mapkit.models import _gltf_io
    g, blob = _gltf_io.read_glb(p)
    for n in g["nodes"]:
        if n.get("name", "").startswith("bone013"):
            n["name"] = "my_cool_hand"
            n.pop("extras", None)
    p2 = tmp_path / "broken.glb"
    _gltf_io.write_glb(g, blob, p2)
    with pytest.raises(ValueError, match="isn't named boneNNN"):
        mgltf.import_gltf(p2)
