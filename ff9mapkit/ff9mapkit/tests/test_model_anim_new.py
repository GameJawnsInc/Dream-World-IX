"""Offline tests for wholly-NEW animation authoring (model-anim-new) -- no install needed.

The from-scratch path: per-bone-number curves -> a full-hierarchy-path clip struct (new_clip) ->
engine-shaped .anim JSON + an idempotent 3DModelAnimation registration (deploy_new_anim). The spin
template is the no-Blender demo of the whole mechanism.

Two engine facts these tests pin (learned from the first in-game spin test, 2026-07-07):
- FIELD anim ids are 16-bit end to end (.eb u16 args + engine Actor.idle UInt16) -> keys are minted
  in the 60000-65535 band; an oversized key silently truncates and NO clip attaches.
- Real FF9 clips key EVERY bone (rot+pos+scale, even 1-frame poses). Playback only resets keyed
  bones, and the engine's head-focus COMPOSES a look offset onto the neck each frame -- an unkeyed
  neck accumulates it into a continuously spinning head. So new_clip fills the whole skeleton.
"""
import json

import pytest

from ff9mapkit.models import anim

BONES = [{"name": "bone000", "parent": None}, {"name": "bone001", "parent": "bone000"},
         {"name": "bone002", "parent": "bone001"}]

RIGGED = [{"name": "bone000", "parent": None,
           "pos": (0.0, -210.0, 0.0), "rot": (0.0, -0.7071, 0.0, 0.7071), "scale": (1.0, 1.0, 1.0)},
          {"name": "bone001", "parent": "bone000",
           "pos": (0.0, 50.0, 0.0), "rot": (0.0, 0.0, 0.0, 1.0), "scale": (1.0, 2.0, 1.0)}]


def test_new_clip_keeps_authored_curves_and_length():
    curves = {0: {"rot": [(0.0, (0, 0, 0, 1)), (1.0, (0, 1, 0, 0))]},
              2: {"pos": [(0.0, (0, 0, 0)), (2.0, (0, 5, 0))]}}
    clip = anim.new_clip(BONES, curves, name="dance")
    assert clip["length"] == 2.0 and clip["name"] == "dance"
    assert clip["bones"]["bone000"]["rot"] == curves[0]["rot"]                    # authored curve verbatim
    assert clip["bones"]["bone000/bone001/bone002"]["pos"] == curves[2]["pos"]
    doc = json.loads(anim.clip_to_anim_json(clip))
    paths = {t["bone"] for t in doc["transform"]}
    assert "bone000/bone001/bone002" in paths           # the SetCurve relativePath the engine needs


def test_new_clip_keys_the_full_skeleton():
    # every skeleton bone gets rot+pos+scale (real clips do -- and an unkeyed neck lets the engine's
    # head-focus offset accumulate into a spinning head), unkeyed ones as 2-key statics at rest
    curves = {0: {"rot": [(0.0, (0, 0, 0, 1)), (1.6, (0, 1, 0, 0))]}}
    clip = anim.new_clip(RIGGED, curves)
    assert set(clip["bones"]) == {"bone000", "bone000/bone001"}
    for path, entry in clip["bones"].items():
        assert set(entry) >= {"rot", "pos", "scale"}
    b1 = clip["bones"]["bone000/bone001"]
    assert b1["rot"] == [(0.0, (0.0, 0.0, 0.0, 1.0)), (1.6, (0.0, 0.0, 0.0, 1.0))]
    assert b1["pos"] == [(0.0, (0.0, 50.0, 0.0)), (1.6, (0.0, 50.0, 0.0))]
    assert b1["scale"] == [(0.0, (1.0, 2.0, 1.0)), (1.6, (1.0, 2.0, 1.0))]
    b0 = clip["bones"]["bone000"]
    assert b0["rot"] == curves[0]["rot"]                                          # authored channel kept
    assert b0["pos"] == [(0.0, (0.0, -210.0, 0.0)), (1.6, (0.0, -210.0, 0.0))]    # missing channels filled
    # a bones list without rest TRS (older callers/tests) falls back to the identity transform
    bare = anim.new_clip(BONES, curves)
    assert bare["bones"]["bone000/bone001"]["rot"][0][1] == (0.0, 0.0, 0.0, 1.0)
    assert bare["bones"]["bone000/bone001"]["scale"][0][1] == (1.0, 1.0, 1.0)


def test_new_clip_skips_unknown_bones_and_rejects_empty():
    warns = []
    clip = anim.new_clip(BONES, {0: {"rot": [(0.0, (0, 0, 0, 1))]},
                                 99: {"rot": [(0.0, (0, 0, 0, 1))]}}, warn=warns.append)
    assert "bone000" in clip["bones"]
    assert any("bone099" in w for w in warns)
    with pytest.raises(ValueError, match="no usable bone curves"):
        anim.new_clip(BONES, {99: {"rot": [(0.0, (0, 0, 0, 1))]}})


def test_synth_spin_is_a_unit_quat_yaw():
    curves = anim.synth_spin_curves(frames=8)
    rot = curves[0]["rot"]
    assert len(rot) == 9
    for _t, q in rot:
        assert abs(sum(c * c for c in q) - 1.0) < 1e-9   # unit quaternions throughout
    assert rot[0][1][3] == pytest.approx(1.0)            # starts at identity
    assert rot[-1][1][3] == pytest.approx(-1.0)          # ends at the 360-degree twin (-identity)


def test_synth_spin_composes_onto_the_rest_pose():
    # a raw yaw would STOMP a non-identity root rest (BBA's bone000 rest is itself a -90-degree yaw)
    import math
    rest = (0.0, math.sin(math.pi / 4), 0.0, math.cos(math.pi / 4))   # +90 degrees about Y
    rot = anim.synth_spin_curves(frames=4, rest=rest)[0]["rot"]
    assert rot[0][1] == pytest.approx(rest)                           # starts AT the rest pose
    assert rot[-1][1] == pytest.approx(tuple(-c for c in rest))       # full turn = the rest's negation twin
    for _t, q in rot:
        assert abs(sum(c * c for c in q) - 1.0) < 1e-9


def test_deploy_new_anim_allocates_a_field_safe_key(tmp_path, monkeypatch):
    from ff9mapkit.models import extract
    monkeypatch.setattr(extract, "resolve_geo", lambda tok: ("GEO_NPC_F1_BBA", 10, 4))
    clip = anim.new_clip(BONES, anim.synth_spin_curves(frames=4), name="spin")
    man = anim.deploy_new_anim("GEO_NPC_F1_BBA", clip, tmp_path, suffix="SPIN")
    assert man["name"] == "ANH_NPC_F1_BBA_SPIN" and man["key"] == 60_000          # 16-bit-safe band
    f = tmp_path / "StreamingAssets" / "Assets" / "Resources" / "Animations" / "10" / "60000.anim"
    assert f.is_file()
    doc = json.loads(f.read_text(encoding="utf-8"))
    assert doc["frameRate"] == 30.0 and doc["transform"][0]["bone"] == "bone000"
    dp = (tmp_path / "DictionaryPatch.txt").read_text(encoding="utf-8")
    assert dp.count("3DModelAnimation 60000 ANH_NPC_F1_BBA_SPIN") == 1
    # idempotent re-deploy: the SAME name reuses its key, no duplicate line
    man2 = anim.deploy_new_anim("GEO_NPC_F1_BBA", clip, tmp_path, suffix="SPIN")
    assert man2["key"] == 60_000
    dp = (tmp_path / "DictionaryPatch.txt").read_text(encoding="utf-8")
    assert dp.count("3DModelAnimation 60000") == 1
    # a SECOND clip allocates the next free key
    man3 = anim.deploy_new_anim("GEO_NPC_F1_BBA", clip, tmp_path, suffix="SPIN2")
    assert man3["key"] == 60_001 and man3["name"] == "ANH_NPC_F1_BBA_SPIN2"


def test_deploy_new_anim_key_validation_and_replacement(tmp_path, monkeypatch):
    from ff9mapkit.models import extract
    monkeypatch.setattr(extract, "resolve_geo", lambda tok: ("GEO_NPC_F1_BBA", 10, 4))
    clip = anim.new_clip(BONES, anim.synth_spin_curves(frames=2))
    # an explicit key must fit the 16-bit field slot (the old 2M band truncated in the .eb)
    with pytest.raises(ValueError, match="16-bit"):
        anim.deploy_new_anim("GEO_NPC_F1_BBA", clip, tmp_path, key=2_001_000)
    # allocator skips keys other directives already use
    dp = tmp_path / "DictionaryPatch.txt"
    dp.write_text("3DModelAnimation 60000 ANH_SOMETHING_ELSE\n", encoding="utf-8")
    man = anim.deploy_new_anim("GEO_NPC_F1_BBA", clip, tmp_path, suffix="SPIN")
    assert man["key"] == 60_001
    # re-registering an explicit key REPLACES its line (no duplicate-key AnimationDB rows)
    man2 = anim.deploy_new_anim("GEO_NPC_F1_BBA", clip, tmp_path, key=60_001, suffix="SPINB")
    text = dp.read_text(encoding="utf-8")
    assert man2["key"] == 60_001
    assert text.count("3DModelAnimation 60001") == 1 and "ANH_NPC_F1_BBA_SPINB" in text
    assert "3DModelAnimation 60000 ANH_SOMETHING_ELSE" in text                    # foreign line untouched


def test_deploy_new_anim_rejects_a_bad_suffix(tmp_path, monkeypatch):
    from ff9mapkit.models import extract
    monkeypatch.setattr(extract, "resolve_geo", lambda tok: ("GEO_NPC_F1_BBA", 10, 4))
    clip = anim.new_clip(BONES, anim.synth_spin_curves(frames=2))
    with pytest.raises(ValueError, match="suffix"):
        anim.deploy_new_anim("GEO_NPC_F1_BBA", clip, tmp_path, suffix="///")


def test_deploy_new_anim_rejects_a_stock_name_collision(tmp_path, monkeypatch):
    # AnimationDB is a TwoWayDictionary: registering a REAL clip name (BBA's pose ANH_NPC_F1_BBA_B)
    # at a new key would hijack the stock name->key lookup and mis-route the real clip's folder
    from ff9mapkit.models import extract
    monkeypatch.setattr(extract, "resolve_geo", lambda tok: ("GEO_NPC_F1_BBA", 10, 4))
    clip = anim.new_clip(BONES, anim.synth_spin_curves(frames=2))
    with pytest.raises(ValueError, match="real FF9 clip name"):
        anim.deploy_new_anim("GEO_NPC_F1_BBA", clip, tmp_path, suffix="B")


def test_deploy_new_anim_moving_a_name_to_an_explicit_key_leaves_one_line(tmp_path, monkeypatch):
    from ff9mapkit.models import extract
    monkeypatch.setattr(extract, "resolve_geo", lambda tok: ("GEO_NPC_F1_BBA", 10, 4))
    clip = anim.new_clip(BONES, anim.synth_spin_curves(frames=2))
    anim.deploy_new_anim("GEO_NPC_F1_BBA", clip, tmp_path, suffix="SPIN")            # auto -> 60000
    man = anim.deploy_new_anim("GEO_NPC_F1_BBA", clip, tmp_path, key=61_000, suffix="SPIN")
    text = (tmp_path / "DictionaryPatch.txt").read_text(encoding="utf-8")
    assert man["key"] == 61_000
    assert text.count("ANH_NPC_F1_BBA_SPIN") == 1 and "3DModelAnimation 61000 ANH_NPC_F1_BBA_SPIN" in text


def test_npc_anim_setter_rejects_an_oversized_id():
    from ff9mapkit.content import npc
    assert npc._anim_op(0x33, 60_000).endswith((60_000).to_bytes(2, "little"))
    with pytest.raises(ValueError, match="16-bit"):
        npc._anim_op(0x33, 2_001_000)
