"""The shipped `[siege]` example -- the productization's front door, so keep it clean.

A new user's FIRST contact with `[siege]` is `ff9mapkit lint examples/siege/...`. It must
build, and it must lint without the two false positives the example itself exposed: a
generated hire menu's `requires_flag` rows read flags the compiled TICKER writes (not an
`[[event]]`), and pooled units are PARKED off-play by design (the ARMOURY idiom).
"""

from __future__ import annotations

from pathlib import Path

from ff9mapkit.build import FieldProject, build_mod, lint_all, lint_logic, validate

SIEGE = Path(__file__).resolve().parents[1] / "examples" / "siege" / "siege.field.toml"


def test_siege_example_validates_and_desugars():
    from ff9mapkit.content import behaviortoml as BT
    p = FieldProject.load(SIEGE)
    assert validate(p) == []
    # the one block really did expand -- base + 2 raider CLASSES + 2 ally CLASSES under
    # the brains default (one shared program per type), carrying every member:
    # base + 2 raider types x2 + 4 guards + 3 archers
    units = p.raw["behavior"]["unit"]
    assert len(units) == 1 + 2 + 2
    assert sum(len(BT.row_members(u)) for u in units) == 1 + 4 + 7
    assert p.raw["behavior"]["timer"] == 60
    assert [o["text"] for o in p.raw["choice"][-1]["options"]][-1] == "Never mind."


def test_siege_example_lints_without_false_positives():
    p = FieldProject.load(SIEGE)
    logic = lint_logic(p)
    # the hire rows' requires_flag are POOL HIREABLE flags, published by the ticker
    assert not [w for w in logic if "no event sets it" in w], logic
    # pooled units park at the 9000 band on purpose -- never a placement complaint
    report = lint_all(p)
    assert not [w for w in report.placement if "far off the walkmesh" in w], \
        report.placement
    assert not report.errors, report.errors


def test_siege_example_builds(tmp_path):
    p = FieldProject.load(SIEGE)
    result = build_mod([p], tmp_path, mod_name="Siege")
    assert any("FieldScene 4810 11 SIEGE SIEGE" in line for line in result["dictionary"])
    fm = tmp_path / "StreamingAssets/assets/resources/FieldMaps/FBG_N11_SIEGE"
    assert (fm / "FBG_N11_SIEGE.bgx").is_file()
    # the siege's announces + council rows are real dialogue -> the field's own .mes
    assert (tmp_path / "FF9_Data/embeddedasset/text/us/field/4810.mes").is_file()
