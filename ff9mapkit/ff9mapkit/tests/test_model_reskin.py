"""Offline tests for the texture-reskin flow (no install needed for the pure parts).

The engine probe is by NAME (``ModelFactory.cs:100-116``: ``<model dir>/{mat.mainTexture.name}.png``)
-- so name validation is the load-bearing piece: a mis-named PNG deploys fine and then silently
never loads. ``validate_reskin_names`` is pure and pinned here; the deploy path's PIL gate and the
Zidane-alt-costume opt-out warning are covered via small fakes/monkeypatching.
"""
from pathlib import Path

import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image

from ff9mapkit.models import reskin


def test_validate_names_accepts_known_stems(tmp_path):
    a = tmp_path / "8_0.png"
    a.write_bytes(b"x")
    ok, errors = reskin.validate_reskin_names({"8_0", "8_1"}, [a])
    assert [p.name for p in ok] == ["8_0.png"] and not errors


def test_validate_names_rejects_unknown_and_nonpng(tmp_path):
    bad = tmp_path / "vivi_hat.png"
    bad.write_bytes(b"x")
    notpng = tmp_path / "8_0.jpg"
    notpng.write_bytes(b"x")
    ok, errors = reskin.validate_reskin_names({"8_0"}, [bad, notpng])
    assert not ok and len(errors) == 2
    assert "no texture named 'vivi_hat'" in errors[0]
    assert "8_0" in errors[0]                       # the error lists the valid stems
    assert "not a .png" in errors[1]


def _fake_model(monkeypatch, *, geo="GEO_NPC_F1_BBA", geo_id=10, type_int=4, stems=("10_0",)):
    tex = {s: Image.new("RGBA", (64, 64)) for s in stems}
    model = {"geo": geo, "geo_id": geo_id, "type_int": type_int, "textures": tex}
    monkeypatch.setattr(reskin.extract, "read_model", lambda tok, game=None: model)
    return model


def test_deploy_reskin_lands_at_the_override_dir(tmp_path, monkeypatch):
    _fake_model(monkeypatch)
    png = tmp_path / "10_0.png"
    Image.new("RGBA", (128, 128), (255, 0, 0, 255)).save(png)   # an upscale -- allowed, noted
    mod = tmp_path / "mod"
    man = reskin.deploy_reskin("GEO_NPC_F1_BBA", [png], mod)
    dest = mod / "StreamingAssets" / "Assets" / "Resources" / "Models" / "4" / "10" / "10_0.png"
    assert dest.is_file()
    assert man["deployed"] == ["10_0.png"]
    assert any("128x128" in w and "64x64" in w for w in man["warnings"])


def test_deploy_reskin_weapon_takes_the_battlemodel_path(tmp_path, monkeypatch):
    _fake_model(monkeypatch, geo="GEO_WEP_B1_021", geo_id=516, type_int=6, stems=("516_0",))
    png = tmp_path / "516_0.png"
    Image.new("RGBA", (64, 64)).save(png)
    mod = tmp_path / "mod"
    man = reskin.deploy_reskin("GEO_WEP_B1_021", [png], mod)
    assert (mod / "StreamingAssets" / "Assets" / "Resources" / "BattleMap" / "BattleModel"
            / "6" / "516" / "516_0.png").is_file()
    assert not man["warnings"]


def test_deploy_reskin_refuses_a_bad_name(tmp_path, monkeypatch):
    _fake_model(monkeypatch)
    png = tmp_path / "wrong.png"
    Image.new("RGBA", (8, 8)).save(png)
    with pytest.raises(ValueError, match="reskin refused"):
        reskin.deploy_reskin("GEO_NPC_F1_BBA", [png], tmp_path / "mod")


def test_deploy_reskin_refuses_a_corrupt_image(tmp_path, monkeypatch):
    _fake_model(monkeypatch)
    png = tmp_path / "10_0.png"
    png.write_bytes(b"not a png at all")
    with pytest.raises(ValueError, match="not a readable image"):
        reskin.deploy_reskin("GEO_NPC_F1_BBA", [png], tmp_path / "mod")


def test_export_textures_writes_stems(tmp_path, monkeypatch):
    _fake_model(monkeypatch, stems=("10_0", "10_1"))
    man = reskin.export_textures("GEO_NPC_F1_BBA", tmp_path / "tex")
    assert sorted(t["name"] for t in man["textures"]) == ["10_0.png", "10_1.png"]
    assert (tmp_path / "tex" / "10_0.png").is_file()


def test_zidane_alt_costume_optout_is_warned(tmp_path, monkeypatch):
    _fake_model(monkeypatch, geo="GEO_MAIN_F4_ZDN", geo_id=669, type_int=2, stems=("669_0",))
    man = reskin.export_textures("GEO_MAIN_F4_ZDN", tmp_path / "tex")
    assert any("SKIPS the loose-PNG probe" in w for w in man["warnings"])


def test_textureless_model_fails_loud(monkeypatch):
    monkeypatch.setattr(reskin.extract, "read_model",
                        lambda tok, game=None: {"geo": "GEO_X", "geo_id": 1, "type_int": 4,
                                                "textures": {}})
    with pytest.raises(ValueError, match="no textures"):
        reskin.export_textures("GEO_X", ".")
