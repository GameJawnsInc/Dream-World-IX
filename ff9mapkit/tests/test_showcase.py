"""The SHOWCASE example is the breadth demo -- keep it valid + buildable as the kit evolves.

It exercises NPCs + dialogue, a flag-gated NPC, a chest event, an encounter + music, and a narration
cutscene in one project, with the placeholder art shipped in examples/SHOWCASE/art. If a content
change breaks the showcase, this fails.
"""

from __future__ import annotations

from pathlib import Path

from ff9mapkit.build import FieldProject, build_mod, lint_logic, validate

SHOWCASE = Path(__file__).resolve().parents[1] / "examples" / "SHOWCASE" / "showcase.field.toml"


def test_showcase_lints_clean():
    p = FieldProject.load(SHOWCASE)
    assert validate(p) == []
    assert lint_logic(p) == []


def test_showcase_builds(tmp_path):
    p = FieldProject.load(SHOWCASE)
    result = build_mod([p], tmp_path, mod_name="Showcase")
    assert any("FieldScene 4800 11 SHOWCASE SHOWCASE" in line for line in result["dictionary"])
    fm = tmp_path / "StreamingAssets/assets/resources/FieldMaps/FBG_N11_SHOWCASE"
    assert (fm / "FBG_N11_SHOWCASE.bgx").is_file()
    assert (fm / "FBG_N11_SHOWCASE.bgi.bytes").is_file()
    # encounter -> a BattlePatch entry; cutscene/NPC/event dialogue -> a .mes
    assert (tmp_path / "BattlePatch.txt").is_file()
    assert (tmp_path / "FF9_Data/embeddedasset/text/us/field/1073.mes").is_file()
