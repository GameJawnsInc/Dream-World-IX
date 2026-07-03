"""Offline tests for the animation round-trip (the "edit the whole model" return half) -- no install needed.

The engine contract is fixed (``AnimationClipReader.ReadAnimationClip_JSON`` + the loose-``.anim`` override in
``AssetManager.LoadMultiple``): a JSON clip at ``Animations/{geoId}/{key}.anim`` shadows the bundled one, keyed
by each bone's FULL hierarchy path. So the tests pin (1) the emitted JSON matches that schema, (2) the glTF ->
FF9 curve parse inverts the forward FF9->glTF conversion exactly, (3) a splice keeps untouched bones verbatim,
and (4) edit-detection skips unchanged clips (and isn't fooled by a whole-quaternion sign flip)."""
import json
import math
import os
import tempfile

from ff9mapkit.models import anim, gltf, _gltf_io


def _norm(q):
    n = math.sqrt(sum(c * c for c in q)) or 1.0
    return [c / n for c in q]


def _tmp(name):
    return os.path.join(tempfile.gettempdir(), name)


# --------------------------------------------------------------------------- JSON serialization (the engine schema)

def test_clip_to_anim_json_matches_the_engine_json_schema():
    clip = {"name": "147", "sample_rate": 30.0, "bones": {
        "bone000": {"bone": 0,
                    "rot": [(0.0, (0.0, 0.0, 0.0, 1.0)), (0.5, (0.0, 0.7, 0.0, 0.7))],
                    "pos": [(0.0, (1.0, 2.0, 3.0))],
                    "scale": [(0.0, (1.0, 1.0, 1.0))]},
        "bone000/bone005": {"bone": 5, "rot": [(0.0, (0.0, 0.0, 0.0, 1.0))]}}}
    doc = json.loads(anim.clip_to_anim_json(clip))
    assert doc["name"] == "147" and doc["frameRate"] == 30.0
    by_bone = {e["bone"]: e for e in doc["transform"]}
    assert set(by_bone) == {"bone000", "bone000/bone005"}       # bone field = the SetCurve hierarchy path
    b0 = by_bone["bone000"]
    assert b0["localRotation"][1] == {"time": 0.5, "x": 0.0, "y": 0.7, "z": 0.0, "w": 0.7}
    assert b0["localPosition"][0] == {"time": 0.0, "x": 1.0, "y": 2.0, "z": 3.0}
    assert "w" not in b0["localPosition"][0]                    # position/scale are 3-comp (no w)
    assert b0["localScale"][0] == {"time": 0.0, "x": 1.0, "y": 1.0, "z": 1.0}
    b5 = by_bone["bone000/bone005"]
    assert b5["localRotation"][0]["w"] == 1.0                   # rotation carries w
    assert "localPosition" not in b5 and "localScale" not in b5  # absent channels omitted, not empty


# --------------------------------------------------------------------------- glTF animations -> FF9 curves (inverse)

def _anim_glb(path, *, key, times, quats=None, poss=None, node_name="bone005", label=None, interp="LINEAR"):
    """A minimal glTF with one bone node + one animation (rotation and/or translation channels)."""
    buf = _gltf_io.GltfBuffer()
    samplers, channels = [], []
    if quats is not None:
        tin = buf.add(list(times), _gltf_io.FLOAT, "SCALAR", minmax=True)
        rout = buf.add([c for q in quats for c in q], _gltf_io.FLOAT, "VEC4")
        samplers.append({"input": tin, "output": rout, "interpolation": interp})
        channels.append({"sampler": len(samplers) - 1, "target": {"node": 0, "path": "rotation"}})
    if poss is not None:
        tin = buf.add(list(times), _gltf_io.FLOAT, "SCALAR", minmax=True)
        pout = buf.add([c for p in poss for c in p], _gltf_io.FLOAT, "VEC3")
        samplers.append({"input": tin, "output": pout, "interpolation": interp})
        channels.append({"sampler": len(samplers) - 1, "target": {"node": 0, "path": "translation"}})
    a = {"name": label, "samplers": samplers, "channels": channels}
    if key is not None:
        a["extras"] = {"ff9_anim_key": key}
    g = {"nodes": [{"name": node_name}], "animations": [a],
         "accessors": buf.accessors, "bufferViews": buf.bufferViews}
    _gltf_io.write_glb(g, buf.blob, path)


def test_parse_gltf_animations_inverts_the_forward_conversion():
    """Build channels EXACTLY as the exporter emits (via _cquat/_cpos + sign-continuity) and prove the parse
    recovers the FF9-space curves: rotation up to a whole-quaternion sign (same rotation), position exactly."""
    times = [0.0, 0.5, 1.0]
    ff9_quats = [_norm([0.1, -0.5, 0.2, 0.8]), _norm([0.0, 0.7, 0.0, 0.7]), _norm([0.3, -0.1, 0.4, 0.85])]
    ff9_pos = [(10.0, -20.0, 30.0), (11.0, -19.0, 29.0), (12.0, -18.0, 28.0)]
    s = 0.01
    gquats = gltf._sign_continuous([gltf._cquat(list(q)) for q in ff9_quats])
    gpos = [gltf._cpos(list(p), s) for p in ff9_pos]
    path = _tmp("ff9mk_anim_inv.glb")
    _anim_glb(path, key=3, times=times, quats=gquats, poss=gpos)
    g, blob = _gltf_io.read_glb(path)
    parsed = anim.parse_gltf_animations(g, blob, scale=s)
    assert len(parsed) == 1 and parsed[0]["key"] == 3
    b5 = parsed[0]["bones"][5]                                  # node "bone005" -> bone number 5
    for (t, q), t0, q0 in zip(b5["rot"], times, ff9_quats):
        assert abs(t - t0) < 1e-6
        assert abs(sum(a * b for a, b in zip(q, q0))) > 1.0 - 1e-4    # rotation-equivalent (allow sign)
    for (t, p), t0, p0 in zip(b5["pos"], times, ff9_pos):
        assert abs(t - t0) < 1e-6 and all(abs(a - b) < 1e-3 for a, b in zip(p, p0))


def test_parse_routes_key_from_extras_then_numeric_name():
    path = _tmp("ff9mk_anim_key.glb")
    _anim_glb(path, key=7, times=[0.0], quats=[[0, 0, 0, 1]], node_name="bone000", label="IDLE")
    g, blob = _gltf_io.read_glb(path)
    pa = anim.parse_gltf_animations(g, blob)[0]
    assert pa["key"] == 7 and pa["label"] == "IDLE"             # extras stamp wins over the (renamed) label
    _anim_glb(path, key=None, times=[0.0], quats=[[0, 0, 0, 1]], node_name="bone000", label="12")
    g, blob = _gltf_io.read_glb(path)
    assert anim.parse_gltf_animations(g, blob)[0]["key"] == 12   # numeric name -> key (extras dropped)
    _anim_glb(path, key=None, times=[0.0], quats=[[0, 0, 0, 1]], node_name="bone000", label="WALK")
    g, blob = _gltf_io.read_glb(path)
    assert anim.parse_gltf_animations(g, blob)[0]["key"] is None  # no stamp + non-numeric name -> unroutable


def test_desample_cubicspline_takes_the_middle_of_each_triple():
    raw = [(1,) * 4, (2,) * 4, (3,) * 4, (4,) * 4, (5,) * 4, (6,) * 4]   # 2 keys, (in,value,out) each
    assert anim._desample(raw, "CUBICSPLINE") == [(2, 2, 2, 2), (5, 5, 5, 5)]
    assert anim._desample(raw, "LINEAR") == raw


# --------------------------------------------------------------------------- splice + edit-detection

def _src_clip():
    return {"name": "x", "sample_rate": 30.0, "bones": {
        "bone000": {"bone": 0, "rot": [(0.0, (0.0, 0.0, 0.0, 1.0))],
                    "pos": [(0.0, (1.0, 2.0, 3.0))], "scale": [(0.0, (1.0, 1.0, 1.0))]},
        "bone000/bone005": {"bone": 5, "rot": [(0.0, (0.0, 0.0, 0.0, 1.0))]}}}


def test_splice_replaces_edited_bone_and_keeps_the_rest_verbatim():
    src = _src_clip()
    edits = {5: {"rot": [(0.0, (0.0, 1.0, 0.0, 0.0)), (1.0, (0.0, 0.0, 0.0, 1.0))]}}
    merged = anim.splice_edits_onto_clip(src, edits)
    assert merged["bones"]["bone000"]["pos"] == [(0.0, (1.0, 2.0, 3.0))]         # untouched bone verbatim
    assert merged["bones"]["bone000"]["scale"] == [(0.0, (1.0, 1.0, 1.0))]
    assert merged["bones"]["bone000/bone005"]["rot"] == edits[5]["rot"]           # edited, at its source path
    assert src["bones"]["bone000/bone005"]["rot"] == [(0.0, (0.0, 0.0, 0.0, 1.0))]  # source not mutated (deep copy)


def test_splice_falls_back_to_the_skeleton_path_for_a_still_bone():
    src = {"name": "x", "sample_rate": 30.0, "bones": {}}
    model_bones = [{"name": "bone000", "parent": None}, {"name": "bone005", "parent": "bone000"}]
    merged = anim.splice_edits_onto_clip(src, {5: {"rot": [(0.0, (0.0, 0.0, 0.0, 1.0))]}}, model_bones=model_bones)
    assert "bone000/bone005" in merged["bones"]                # bone the clip didn't animate -> skeleton path


def test_bone_paths_builds_the_full_hierarchy_path():
    mb = [{"name": "bone000", "parent": None}, {"name": "bone002", "parent": "bone000"},
          {"name": "bone007", "parent": "bone002"}]
    paths = anim.bone_paths(mb)
    assert paths[0] == "bone000" and paths[2] == "bone000/bone002" and paths[7] == "bone000/bone002/bone007"


def test_is_edited_detects_change_and_ignores_sign_flip():
    src = {"bones": {"bone000": {"bone": 0, "rot": [(0.0, (0.0, 0.0, 0.0, 1.0)), (0.5, (0.0, 0.7, 0.0, 0.7))]}}}
    assert not anim._is_edited({0: {"rot": [(0.0, (0.0, 0.0, 0.0, 1.0)), (0.5, (0.0, 0.7, 0.0, 0.7))]}}, src)
    # a whole-quaternion sign flip is the SAME rotation -> NOT an edit
    assert not anim._is_edited({0: {"rot": [(0.0, (0.0, 0.0, 0.0, -1.0)), (0.5, (0.0, -0.7, 0.0, -0.7))]}}, src)
    # a genuinely different rotation -> edited
    assert anim._is_edited({0: {"rot": [(0.0, (0.0, 0.0, 0.0, 1.0)), (0.5, (0.7, 0.0, 0.0, 0.7))]}}, src)
    # a bone the source clip doesn't animate -> edited
    assert anim._is_edited({9: {"rot": [(0.0, (0.0, 0.0, 0.0, 1.0))]}}, src)


def test_full_faithful_write_carries_the_edit_into_engine_json():
    """End-to-end (offline): splice an edit onto the source clip, serialize, and confirm the JSON the engine
    would read carries the edit at the correct hierarchy path while the untouched bone stays put."""
    merged = anim.splice_edits_onto_clip(_src_clip(), {5: {"rot": [(0.0, (0.0, 1.0, 0.0, 0.0))]}})
    doc = json.loads(anim.clip_to_anim_json(merged))
    by_bone = {e["bone"]: e for e in doc["transform"]}
    assert by_bone["bone000/bone005"]["localRotation"][0] == {"time": 0.0, "x": 0.0, "y": 1.0, "z": 0.0, "w": 0.0}
    assert by_bone["bone000"]["localPosition"][0] == {"time": 0.0, "x": 1.0, "y": 2.0, "z": 3.0}
