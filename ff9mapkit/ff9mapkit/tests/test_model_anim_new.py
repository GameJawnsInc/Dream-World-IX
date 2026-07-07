"""Offline tests for wholly-NEW animation authoring (model-anim-new) -- no install needed.

The from-scratch path: per-bone-number curves -> a full-hierarchy-path clip struct (new_clip) ->
engine-shaped .anim JSON + an idempotent 3DModelAnimation registration (deploy_new_anim). The spin
template is the no-Blender demo of the whole mechanism.
"""
import json

import pytest

from ff9mapkit.models import anim

BONES = [{"name": "bone000", "parent": None}, {"name": "bone001", "parent": "bone000"},
         {"name": "bone002", "parent": "bone001"}]


def test_new_clip_builds_full_paths_and_length():
    curves = {0: {"rot": [(0.0, (0, 0, 0, 1)), (1.0, (0, 1, 0, 0))]},
              2: {"pos": [(0.0, (0, 0, 0)), (2.0, (0, 5, 0))]}}
    clip = anim.new_clip(BONES, curves, name="dance")
    assert set(clip["bones"]) == {"bone000", "bone000/bone001/bone002"}
    assert clip["length"] == 2.0 and clip["name"] == "dance"
    doc = json.loads(anim.clip_to_anim_json(clip))
    paths = {t["bone"] for t in doc["transform"]}
    assert "bone000/bone001/bone002" in paths           # the SetCurve relativePath the engine needs


def test_new_clip_skips_unknown_bones_and_rejects_empty():
    warns = []
    clip = anim.new_clip(BONES, {0: {"rot": [(0.0, (0, 0, 0, 1))]},
                                 99: {"rot": [(0.0, (0, 0, 0, 1))]}}, warn=warns.append)
    assert "bone000" in clip["bones"] and len(clip["bones"]) == 1
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


def test_deploy_new_anim_writes_clip_and_registers(tmp_path, monkeypatch):
    from ff9mapkit.models import extract
    monkeypatch.setattr(extract, "resolve_geo", lambda tok: ("GEO_NPC_F1_BBA", 10, 4))
    clip = anim.new_clip(BONES, anim.synth_spin_curves(frames=4), name="spin")
    man = anim.deploy_new_anim("GEO_NPC_F1_BBA", clip, tmp_path, suffix="SPIN")
    assert man["name"] == "ANH_NPC_F1_BBA_SPIN" and man["key"] == 2_001_000
    f = tmp_path / "StreamingAssets" / "Assets" / "Resources" / "Animations" / "10" / "2001000.anim"
    assert f.is_file()
    doc = json.loads(f.read_text(encoding="utf-8"))
    assert doc["frameRate"] == 30.0 and doc["transform"][0]["bone"] == "bone000"
    dp = (tmp_path / "DictionaryPatch.txt").read_text(encoding="utf-8")
    assert dp.count("3DModelAnimation 2001000 ANH_NPC_F1_BBA_SPIN") == 1
    anim.deploy_new_anim("GEO_NPC_F1_BBA", clip, tmp_path, suffix="SPIN")   # idempotent re-deploy
    dp = (tmp_path / "DictionaryPatch.txt").read_text(encoding="utf-8")
    assert dp.count("3DModelAnimation 2001000") == 1


def test_deploy_new_anim_rejects_a_bad_suffix(tmp_path, monkeypatch):
    from ff9mapkit.models import extract
    monkeypatch.setattr(extract, "resolve_geo", lambda tok: ("GEO_NPC_F1_BBA", 10, 4))
    clip = anim.new_clip(BONES, anim.synth_spin_curves(frames=2))
    with pytest.raises(ValueError, match="suffix"):
        anim.deploy_new_anim("GEO_NPC_F1_BBA", clip, tmp_path, suffix="///")
