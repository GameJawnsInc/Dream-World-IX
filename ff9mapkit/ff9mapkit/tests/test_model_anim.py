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

import pytest

from ff9mapkit.models import anim, gltf, _gltf_io


def _norm(q):
    n = math.sqrt(sum(c * c for c in q)) or 1.0
    return [c / n for c in q]


def _tmp(name):
    return os.path.join(tempfile.gettempdir(), name)


# --------------------------------------------------------------------------- custom_battle_anims: minted animset copy

def test_deploy_battle_animset_writes_faithful_clips_to_the_mint_folder(monkeypatch):
    """A 13th character's custom_battle_anims ships FAITHFUL copies of the donor's clips at the MINTED model's
    own Animations/<mintId>/<key>.anim -- so editing them never touches the donor's Animations/<srcId>/ clips.
    Each clip carries its OWN (src_geo_id, src_key, dst_key)."""
    src = {"name": "src", "sample_rate": 30.0,
           "bones": {"bone001": {"bone": 1, "rot": [(0.0, (0.0, 0.0, 0.0, 1.0))]}}}
    monkeypatch.setattr(anim, "_load_env5", lambda game=None: object())            # no p0data needed
    monkeypatch.setattr(anim._gltf_io, "read_clip", lambda env, gid, key: src)      # donor clip -> faithful copy
    dest = _tmp("dwix_animset_test")
    written = anim.deploy_battle_animset(6100, [(5415, 5, 1010000), (5415, 6, 1010001)], dest)
    p0 = os.path.join(dest, "StreamingAssets", "Assets", "Resources", "Animations", "6100", "1010000.anim")
    assert written[0] == p0 and os.path.isfile(p0)
    doc = json.loads(open(p0, encoding="utf-8").read())
    assert doc["transform"][0]["bone"] == "bone001"                                 # the donor clip, faithfully copied
    assert os.path.isfile(os.path.join(dest, "StreamingAssets", "Assets", "Resources",
                                       "Animations", "6100", "1010001.anim"))


def test_deploy_battle_animset_fails_loud_on_missing_clip(monkeypatch):
    """A missing/empty source clip must RAISE (not silently skip) -- registering a battle motion with no clip
    freezes the battle (btl_mot.cs:226), so the build fails rather than ship an incomplete (freezing) set."""
    monkeypatch.setattr(anim, "_load_env5", lambda game=None: object())
    monkeypatch.setattr(anim._gltf_io, "read_clip", lambda env, gid, key: None)     # simulate a missing clip
    with pytest.raises(anim.AnimsetError):
        anim.deploy_battle_animset(6100, [(5415, 5, 1010000)], _tmp("dwix_animset_fail"))


def _identity_clip(key):
    return {"name": str(key), "sample_rate": 30.0,
            "bones": {"bone001": {"bone": 1, "rot": [(0.0, (0.0, 0.0, 0.0, 1.0)), (1.0, (0.0, 0.0, 0.0, 1.0))]}}}


def _raise_keyerror(*a, **k):
    raise KeyError("no model")


def test_deploy_battle_animset_edits_routes_edited_and_faithful(monkeypatch):
    """The Blender edit loop: an edited donor .glb routes ONLY the changed clips onto the character's mint folder;
    every other clip is a FAITHFUL copy (so the animset stays complete/freeze-safe), and the DONOR is never written."""
    monkeypatch.setattr(anim, "_load_env5", lambda game=None: object())
    monkeypatch.setattr(anim._gltf_io, "read_glb", lambda p: ({"asset": {"extras": {"ff9_scale": 0.01}}}, b""))
    monkeypatch.setattr(anim.extract, "read_model", _raise_keyerror)                 # no model_bones -> splice by path
    monkeypatch.setattr(anim._gltf_io, "read_clip", lambda env, gid, key: _identity_clip(key))
    edited = {1: {"rot": [(0.0, (0.0, 0.0, 0.0, 1.0)), (1.0, (0.0, 0.707, 0.0, 0.707))]}}   # a real ~90deg change
    monkeypatch.setattr(anim, "parse_gltf_animations",
                        lambda g, b, scale=None: [{"key": 100, "label": "attack", "bones": edited}])
    dest = _tmp("dwix_rt_edits")
    clips = [(5415, 100, 1010000), (5415, 200, 1010001)]
    r = anim.deploy_battle_animset_edits(clips, 6100, "x.glb", dest)
    assert r["edited"] == [100] and r["faithful"] == [200] and len(r["written"]) == 2
    e = json.loads(open(os.path.join(dest, "StreamingAssets", "Assets", "Resources", "Animations",
                                     "6100", "1010000.anim"), encoding="utf-8").read())
    f = json.loads(open(os.path.join(dest, "StreamingAssets", "Assets", "Resources", "Animations",
                                     "6100", "1010001.anim"), encoding="utf-8").read())
    erot = e["transform"][0]["localRotation"][-1]
    assert abs(erot["y"] - 0.707) < 1e-3                                              # the edit propagated
    assert f["transform"][0]["localRotation"][-1]["y"] == 0.0                         # faithful clip unchanged
    # nothing was written under the DONOR's folder (5415)
    assert not os.path.isdir(os.path.join(dest, "StreamingAssets", "Assets", "Resources", "Animations", "5415"))


def test_deploy_battle_animset_edits_warns_unroutable_and_reports_match(monkeypatch):
    """A glb animation with no routable key WARNS (not silently lost); a glb whose clips belong to a DIFFERENT
    model matches nothing (matched==0) so the CLI can flag an export-wrong-donor mistake instead of 'no edits'."""
    monkeypatch.setattr(anim, "_load_env5", lambda game=None: object())
    monkeypatch.setattr(anim._gltf_io, "read_glb", lambda p: ({"asset": {"extras": {}}}, b""))
    monkeypatch.setattr(anim.extract, "read_model", _raise_keyerror)
    monkeypatch.setattr(anim._gltf_io, "read_clip", lambda env, gid, key: _identity_clip(key))
    # one UNROUTABLE animation (renamed, no key) + one clip for a FOREIGN model (key 999, not in the plan)
    monkeypatch.setattr(anim, "parse_gltf_animations", lambda g, b, scale=None: [
        {"key": None, "label": "myattack", "bones": {}}, {"key": 999, "label": "999", "bones": {}}])
    r = anim.deploy_battle_animset_edits([(5415, 100, 1010000)], 6100, "x.glb", _tmp("dwix_rt_warn"))
    assert r["edited"] == [] and r["faithful"] == [100] and len(r["written"]) == 1   # complete + freeze-safe
    assert r["matched"] == 0 and r["glb_anims"] == 2                                 # nothing matched this animset
    assert any("no routable key" in w for w in r["warnings"])                        # the renamed clip is flagged


def test_deploy_battle_animset_edits_fails_loud_on_missing_source(monkeypatch):
    monkeypatch.setattr(anim, "_load_env5", lambda game=None: object())
    monkeypatch.setattr(anim._gltf_io, "read_glb", lambda p: ({"asset": {"extras": {}}}, b""))
    monkeypatch.setattr(anim.extract, "read_model", _raise_keyerror)
    monkeypatch.setattr(anim._gltf_io, "read_clip", lambda env, gid, key: None)      # source clip gone
    monkeypatch.setattr(anim, "parse_gltf_animations", lambda g, b, scale=None: [])
    with pytest.raises(anim.AnimsetError):
        anim.deploy_battle_animset_edits([(5415, 100, 1010000)], 6100, "x.glb", _tmp("dwix_rt_fail"))


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


def test_is_edited_catches_a_scale_only_edit():
    """Review's HIGH finding: _is_edited had no scale arm, so a scale-only squash/stretch (rotation/position
    untouched) was judged 'unchanged' and silently dropped. It must now register as an edit."""
    src = {"bones": {"bone000": {"bone": 0, "rot": [(0.0, (0.0, 0.0, 0.0, 1.0))],
                                 "scale": [(0.0, (1.0, 1.0, 1.0)), (0.5, (1.0, 1.0, 1.0))]}}}
    edit = {0: {"rot": [(0.0, (0.0, 0.0, 0.0, 1.0))],
                "scale": [(0.0, (1.0, 1.0, 1.0)), (0.5, (1.3, 0.8, 1.3))]}}   # squash/stretch, rot unchanged
    assert anim._is_edited(edit, src)
    assert not anim._is_edited({0: {"scale": [(0.0, (1.0, 1.0, 1.0)), (0.5, (1.0, 1.0, 1.0))]}}, src)  # identical


def test_is_edited_catches_a_sub_degree_rotation():
    """Review's MEDIUM finding: eps=1e-3 gave a ~5deg dead zone that swallowed subtle edits. A 1deg tilt must
    now register (eps 1e-6 -> ~0.16deg), while float noise (a hair off) must not."""
    src = {"bones": {"bone000": {"bone": 0, "rot": [(0.0, (0.0, 0.0, 0.0, 1.0))]}}}
    a = math.radians(1.0)
    assert anim._is_edited({0: {"rot": [(0.0, (math.sin(a / 2), 0.0, 0.0, math.cos(a / 2)))]}}, src)
    assert not anim._is_edited({0: {"rot": [(0.0, (1e-9, 0.0, 0.0, 1.0))]}}, src)   # noise, not an edit


def test_clip_to_anim_json_rejects_non_finite():
    """Review's finding: json.dumps(allow_nan) would emit bare NaN/Infinity (invalid JSON the engine misreads).
    _r fails loud instead."""
    bad = {"name": "x", "sample_rate": 30.0,
           "bones": {"bone000": {"bone": 0, "rot": [(0.0, (float("nan"), 0.0, 0.0, 1.0))]}}}
    with pytest.raises(ValueError, match="non-finite"):
        anim.clip_to_anim_json(bad)


def test_parse_reads_a_scale_channel_verbatim():
    """A Blender scale channel parses verbatim (scale is mirror-invariant -- no coordinate flip, no unit bake)."""
    path = _tmp("ff9mk_anim_scale.glb")
    buf = _gltf_io.GltfBuffer()
    scales = [(1.0, 1.0, 1.0), (1.3, 0.8, 1.3)]
    tin = buf.add([0.0, 0.5], _gltf_io.FLOAT, "SCALAR", minmax=True)
    sout = buf.add([c for v in scales for c in v], _gltf_io.FLOAT, "VEC3")
    a = {"name": "9", "samplers": [{"input": tin, "output": sout, "interpolation": "LINEAR"}],
         "channels": [{"sampler": 0, "target": {"node": 0, "path": "scale"}}]}
    g = {"nodes": [{"name": "bone005"}], "animations": [a],
         "accessors": buf.accessors, "bufferViews": buf.bufferViews}
    _gltf_io.write_glb(g, buf.blob, path)
    gg, blob = _gltf_io.read_glb(path)
    pa = anim.parse_gltf_animations(gg, blob)[0]
    sc = pa["bones"][5]["scale"]
    assert abs(sc[1][1][0] - 1.3) < 1e-4 and abs(sc[1][1][1] - 0.8) < 1e-4    # verbatim, unflipped


def _mid(a, b):
    return tuple((x + y) / 2 for x, y in zip(a, b))


def test_curve_changed_ignores_resampling_but_catches_real_edits():
    """The key robustness: Blender re-samples (adds/removes keys) while preserving the motion. A curve with
    extra keys sampled ON the original linear segments must read as UNCHANGED; a key moved OFF the line reads
    as changed (compared by sampled motion, not key count)."""
    src = [(0.0, (0.0, 0.0, 0.0, 1.0)), (1.0, (0.0, 0.7071, 0.0, 0.7071))]
    resampled = [(0.0, src[0][1]), (0.5, _mid(src[0][1], src[1][1])), (1.0, src[1][1])]   # denser, same motion
    assert not anim._curve_changed(resampled, src, "rot")
    edited = [(0.0, src[0][1]), (0.5, (0.0, 0.0, 0.0, 1.0)), (1.0, src[1][1])]             # midpoint snapped back
    assert anim._curve_changed(edited, src, "rot")
    # position: same story
    ps = [(0.0, (0.0, 0.0, 0.0)), (1.0, (30.0, 0.0, 0.0))]
    assert not anim._curve_changed([(0.0, (0.0, 0.0, 0.0)), (0.5, (15.0, 0.0, 0.0)), (1.0, (30.0, 0.0, 0.0))], ps, "pos")
    assert anim._curve_changed([(0.0, (0.0, 0.0, 0.0)), (0.5, (15.0, 9.0, 0.0)), (1.0, (30.0, 0.0, 0.0))], ps, "pos")


def test_is_edited_robust_to_resampling():
    """An untouched clip round-tripped through Blender comes back re-sampled (different key COUNT, same
    motion). It must NOT read as edited (else every clip gets needlessly rewritten with the resampled copy)."""
    src = {"bones": {"bone000": {"bone": 0, "rot": [(0.0, (0.0, 0.0, 0.0, 1.0)), (1.0, (0.0, 0.7071, 0.0, 0.7071))]}}}
    resampled = {0: {"rot": [(0.0, (0.0, 0.0, 0.0, 1.0)),
                             (0.5, _mid((0.0, 0.0, 0.0, 1.0), (0.0, 0.7071, 0.0, 0.7071))),
                             (1.0, (0.0, 0.7071, 0.0, 0.7071))]}}                          # 2->3 keys, same motion
    assert not anim._is_edited(resampled, src)
    real = {0: {"rot": [(0.0, (0.0, 0.0, 0.0, 1.0)), (0.5, (0.0, 0.0, 0.0, 1.0)), (1.0, (0.0, 0.7071, 0.0, 0.7071))]}}
    assert anim._is_edited(real, src)


def test_splice_keeps_source_curve_when_only_resampled():
    """A bone whose curve Blender only RE-SAMPLED (same motion) keeps the source's byte-faithful keys -- so a
    one-bone edit doesn't rewrite every other bone with a resampled version."""
    src = {"bones": {"bone000": {"bone": 0, "rot": [(0.0, (0.0, 0.0, 0.0, 1.0)), (1.0, (0.0, 0.7071, 0.0, 0.7071))]}}}
    resampled = {0: {"rot": [(0.0, (0.0, 0.0, 0.0, 1.0)),
                             (0.5, _mid((0.0, 0.0, 0.0, 1.0), (0.0, 0.7071, 0.0, 0.7071))),
                             (1.0, (0.0, 0.7071, 0.0, 0.7071))]}}
    merged = anim.splice_edits_onto_clip(src, resampled)
    assert merged["bones"]["bone000"]["rot"] == src["bones"]["bone000"]["rot"]            # 2-key source kept, not the 3-key resample


def test_collision_prefers_the_edited_duplicate_over_pristine():
    """When duplicate actions map to the same clip key (a scene imported more than once), the deploy picks an
    EDITED candidate, not last-wins -- so a pristine/re-sampled copy can't clobber the user's edit. This is
    the exact filter the deploy loop applies (`[pa for pa in group if _is_edited(...)]` -> last)."""
    src = {"bones": {"bone000": {"bone": 0, "rot": [(0.0, (0.0, 0.0, 0.0, 1.0)), (1.0, (0.0, 0.7071, 0.0, 0.7071))]}}}
    pristine = {0: {"rot": [(0.0, (0.0, 0.0, 0.0, 1.0)),                                   # re-sampled, same motion
                            (0.5, _mid((0.0, 0.0, 0.0, 1.0), (0.0, 0.7071, 0.0, 0.7071))),
                            (1.0, (0.0, 0.7071, 0.0, 0.7071))]}}
    edited = {0: {"rot": [(0.0, (0.0, 0.0, 0.0, 1.0)), (1.0, (0.7071, 0.0, 0.0, 0.7071))]}}   # different axis
    for group in ([pristine, edited], [edited, pristine]):                                 # order must not matter
        chosen = [b for b in group if anim._is_edited(b, src)]
        assert len(chosen) == 1 and chosen[-1] is edited                                   # pristine filtered out


def test_full_faithful_write_carries_the_edit_into_engine_json():
    """End-to-end (offline): splice an edit onto the source clip, serialize, and confirm the JSON the engine
    would read carries the edit at the correct hierarchy path while the untouched bone stays put."""
    merged = anim.splice_edits_onto_clip(_src_clip(), {5: {"rot": [(0.0, (0.0, 1.0, 0.0, 0.0))]}})
    doc = json.loads(anim.clip_to_anim_json(merged))
    by_bone = {e["bone"]: e for e in doc["transform"]}
    assert by_bone["bone000/bone005"]["localRotation"][0] == {"time": 0.0, "x": 0.0, "y": 1.0, "z": 0.0, "w": 0.0}
    assert by_bone["bone000"]["localPosition"][0] == {"time": 0.0, "x": 1.0, "y": 2.0, "z": 3.0}
