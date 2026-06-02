"""Phase-4 validation: the field.toml -> mod builder.

The example project (examples/vivi-hut/hut_int.field.toml) is the worked example AND the build
oracle: compiling it must reproduce the in-game-verified EVT_HUT_INT.eb script byte-for-byte,
emit the exact DictionaryPatch line, write the Session-9 dialogue .mes, and lay out a valid
background scene + walkmesh — all offline.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ff9mapkit.build import FieldProject, build_mod, validate
from ff9mapkit.config import LANGS, ModLayout
from ff9mapkit.scene import bgi, bgx

FIX = Path(__file__).parent / "fixtures"
EXAMPLE = Path(__file__).parents[1] / "examples" / "vivi-hut" / "hut_int.field.toml"


@pytest.fixture()
def built(tmp_path):
    proj = FieldProject.load(EXAMPLE)
    info = build_mod([proj], tmp_path, mod_name="FF9CustomMap", author="test")
    return tmp_path, info


def test_example_validates_clean():
    assert validate(FieldProject.load(EXAMPLE)) == []


def test_build_reproduces_hut_int_eb_byte_exact(built):
    out, _ = built
    eb = ModLayout(out).eb_path("us", "EVT_HUT_INT.eb.bytes").read_bytes()
    assert eb == (FIX / "hut_int-us.eb.bytes").read_bytes()


def test_build_writes_all_languages(built):
    out, _ = built
    L = ModLayout(out)
    for lang in LANGS:
        assert L.eb_path(lang, "EVT_HUT_INT.eb.bytes").is_file()


def test_build_dictionary_and_mes_and_description(built):
    out, info = built
    L = ModLayout(out)
    assert info["dictionary"] == ["FieldScene 4002 11 HUT_INT HUT_INT 1073"]
    assert L.dictionary_patch.read_text().strip() == "FieldScene 4002 11 HUT_INT HUT_INT 1073"
    assert L.mes_path("us", 1073).read_text(encoding="utf-8").strip() == \
        "_[TXID=500][STRT=10,1][TAIL=UPR]I miss you Zidane[ENDN]"
    assert "<InstallationPath>FF9CustomMap</InstallationPath>" in L.mod_description.read_text()


def test_build_scene_and_walkmesh(built):
    out, _ = built
    fm = ModLayout(out).fieldmap_dir("FBG_N11_HUT_INT")
    # walkmesh round-trips and has the quad's 2 triangles
    raw = (fm / "FBG_N11_HUT_INT.bgi.bytes").read_bytes()
    wm = bgi.BgiWalkmesh.from_bytes(raw)
    assert wm.to_bytes() == raw and len(wm.tris) == 2
    # scene has both layers + a camera, and the PNGs were copied
    scene = bgx.BgxScene.from_file(fm / "FBG_N11_HUT_INT.bgx")
    assert [o.image for o in scene.overlays] == ["back.png", "floor.png"]
    assert len(scene.cameras) == 1
    assert (fm / "back.png").is_file() and (fm / "floor.png").is_file()


def test_validate_rejects_low_area(tmp_path):
    bad = tmp_path / "bad.field.toml"
    bad.write_text('[field]\nid=4002\nname="X"\narea=7\n[camera]\npitch=48\n', encoding="utf-8")
    problems = validate(FieldProject.load(bad))
    assert any("area must be >= 10" in p for p in problems)
