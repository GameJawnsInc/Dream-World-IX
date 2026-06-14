"""Tests for the [[ability_feature]] -> AbilityFeatures.txt emitter (the no-DLL ability-effect DSL).

Offline: SA/CMD-id + AA-id resolution, header forms, structural validation, the cumulate/replace merge flag,
cp1252/LF write, the deferred `##`-marker merge. AA-by-name resolution (install-gated) is exercised with a
monkeypatched Actions.csv resolver.
"""
from __future__ import annotations

import pytest

from ff9mapkit.battle import abilityfeatures as af
from ff9mapkit.battle.abilityfeatures import AbilityFeatureError


def _one(blk, *, game=None):
    return af.build_lines([blk], game=game)[0]


# ---------------------------------------------------------------- header forms + resolution ---
def test_sa_by_name_and_id():
    lines, _ = af.build_lines([{"kind": "SA", "ability": "Auto-Haste", "features": "StatusInit AutoStatus Haste"}])
    assert lines[0] == af._FILE_HEADER and lines[2] == ">SA 2+ AutoHaste"      # AutoHaste = index 2, default cumulate
    assert ">SA 8+ MP20" in _one({"kind": "SA", "ability": 8, "features": "Permanent [code=MaxMP] 1 [/code]"})
    assert ">SA 60+ OdinSword" in _one({"ability": "Odin's Sword", "features": "Ability [code=Condition] 1 [/code]"})


def test_sa_id_out_of_range():
    with pytest.raises(AbilityFeatureError):
        _one({"kind": "SA", "ability": 64, "features": "StatusInit AutoStatus Haste"})


def test_replace_drops_the_plus_and_uses_comment():
    out = _one({"kind": "SA", "ability": 8, "cumulate": False, "comment": "MP+20% full replace",
                "features": "Permanent [code=MaxMP] MaxMP + MaxMP / 5 [/code]"})
    assert ">SA 8 MP+20% full replace" in out                                  # no '+', custom comment


def test_replace_alias_equals_no_cumulate():
    a = _one({"kind": "SA", "ability": 2, "replace": True, "features": "StatusInit AutoStatus Haste"})
    b = _one({"kind": "SA", "ability": 2, "cumulate": False, "features": "StatusInit AutoStatus Haste"})
    assert a == b and ">SA 2 " in "\n".join(a)


def test_cumulate_replace_contradiction():
    with pytest.raises(AbilityFeatureError):
        _one({"kind": "SA", "ability": 2, "cumulate": True, "replace": True, "features": "StatusInit X"})


def test_aa_by_id_and_cmd_by_id():
    assert ">AA 82+ 82" in _one({"kind": "AA", "ability": 82, "features": "[code=Target] X [/code]"})
    assert ">CMD 31 Magic Sword" in _one({"kind": "CMD", "ability": 31, "cumulate": False,
                                          "comment": "Magic Sword", "features": "[code=HardDisable] 1 [/code]"})


def test_aa_id_out_of_range_and_cmd_zero():
    with pytest.raises(AbilityFeatureError):
        _one({"kind": "AA", "ability": 192, "features": "[code=Power] 1 [/code]"})
    with pytest.raises(AbilityFeatureError):
        _one({"kind": "CMD", "ability": 0, "features": "[code=Disable] 1 [/code]"})


def test_cmd_by_name_rejected():
    with pytest.raises(AbilityFeatureError):
        _one({"kind": "CMD", "ability": "Magic Sword", "features": "[code=Disable] 1 [/code]"})


def test_aa_by_name_resolves_via_actions_csv(monkeypatch):
    from ff9mapkit.battle import actiondelta as ad
    monkeypatch.setattr(ad, "_csv_path", lambda name, game: "x")
    monkeypatch.setattr(ad, "_read_raw", lambda path: ({}, [], {"comment": 0}, {82: ["Roulette"]}))
    monkeypatch.setattr(ad, "_name_index", lambda rows, cols: {"roulette": [82]})
    monkeypatch.setattr(ad, "_resolve_id", lambda tok, rows, names, *, kind, max_id: 82)
    out = _one({"kind": "AA", "ability": "Roulette", "features": "[code=Target] X [/code]"}, game="x")
    assert ">AA 82+ Roulette" in out


def test_aa_by_name_defers_offline():
    # validate (offline, no game) must NOT fail on an AA name -- it defers id resolution to build
    assert af.validate_blocks([{"kind": "AA", "ability": "Roulette", "features": "[code=Target] X [/code]"}]) == []


# ---------------------------------------------------------------- special-id words ---
def test_special_words_per_kind():
    assert ">SA GlobalLast+ GlobalLast" in _one({"kind": "SA", "ability": "GlobalLast",
                                                 "features": "Permanent [code=Strength] 1 [/code]"})
    assert ">AA Global+ Global" in _one({"kind": "AA", "ability": "Global", "features": "[code=Power] 1 [/code]"})


def test_special_word_illegal_for_kind():
    with pytest.raises(AbilityFeatureError):                                    # GlobalEnemy only acts for >SA
        _one({"kind": "AA", "ability": "GlobalEnemy", "features": "[code=Power] 1 [/code]"})
    with pytest.raises(AbilityFeatureError):                                    # GlobalLast no-ops for >CMD
        _one({"kind": "CMD", "ability": "GlobalLast", "features": "[code=Disable] 1 [/code]"})


# ---------------------------------------------------------------- structural validation ---
def test_unbalanced_and_nested_code_tags():
    with pytest.raises(AbilityFeatureError):
        _one({"kind": "AA", "ability": 1, "features": "[code=Power] 1"})        # missing [/code]
    with pytest.raises(AbilityFeatureError):
        _one({"kind": "AA", "ability": 1, "features": "[code=A] [code=B] 1 [/code] [/code]"})   # nested


def test_nested_header_in_body_rejected():
    with pytest.raises(AbilityFeatureError):
        _one({"kind": "SA", "ability": 2, "features": "StatusInit AutoStatus Haste\n>SA 3 Auto-Regen"})


def test_empty_body_rejected():
    with pytest.raises(AbilityFeatureError):
        _one({"kind": "SA", "ability": 2, "features": "   \n  "})


def test_features_alias_conflict():
    with pytest.raises(AbilityFeatureError):
        _one({"kind": "SA", "ability": 2, "features": "StatusInit X", "code": "StatusInit Y"})


def test_unknown_aa_tag_warns_not_errors():
    lines, warns = af.build_lines([{"kind": "AA", "ability": 1, "features": "[code=Elemnt] 1 [/code]"}])
    assert lines and any("Elemnt" in w and "ignores" in w for w in warns)       # typo -> warn, still emits


def test_cross_kind_tag_hint():
    _l, warns = af.build_lines([{"kind": "CMD", "ability": 5, "features": "[code=Power] 1 [/code]"}])
    assert any("Power" in w and "AA" in w for w in warns)                       # Power is an >AA tag, not >CMD


def test_sa_first_line_not_a_keyword_warns():
    _l, warns = af.build_lines([{"kind": "SA", "ability": 2, "features": "[code=MaxMP] 1 [/code]"}])
    assert any("feature type" in w for w in warns)                              # missing the Permanent/StatusInit verb


# ---------------------------------------------------------------- write (encoding) + merge ---
def test_write_is_cp1252_lf(tmp_path):
    from ff9mapkit.config import ModLayout
    layout = ModLayout(tmp_path)
    w = af.write_ability_features(layout, [{"kind": "SA", "ability": 60, "comment": "Odin’s Sword",
                                            "features": "Ability [code=Condition] 1 [/code]"}])
    p = layout.ability_features_txt
    assert p.is_file()
    raw = p.read_bytes()
    assert b"\r\n" not in raw and b"\x92" in raw                                # LF only; cp1252 curly apostrophe
    assert p.read_text(encoding="cp1252").splitlines()[2].startswith(">SA 60+ Odin")


def test_write_nothing_when_empty(tmp_path):
    from ff9mapkit.config import ModLayout
    layout = ModLayout(tmp_path)
    assert af.write_ability_features(layout, []) == []
    assert not layout.ability_features_txt.exists()                            # no blocks -> no file


def test_indented_sa_verb_lands_at_column_0():
    # the natural triple-quoted (indented) authoring style must emit feature verbs at column 0 -- the engine's
    # `^verb` matcher is Multiline but not whitespace-tolerant, so an indented verb is silently dropped.
    out = _one({"kind": "SA", "ability": 2,
                "features": "\n    StatusInit AutoStatus Haste\n    Permanent [code=MaxHP] 1 [/code]\n"})
    body = [ln for ln in out if ln and not ln.startswith((">", "#"))]
    assert body and all(not ln.startswith(" ") for ln in body)
    assert ">SA 2+ AutoHaste" in out and "StatusInit AutoStatus Haste" in out


def test_replace_with_no_body_clears_features():
    out = _one({"kind": "SA", "ability": 36, "replace": True, "comment": "disable Counter"})
    assert ">SA 36 disable Counter" in out                                     # header only, no '+', no body (clear)


def test_cumulate_with_no_body_errors():
    with pytest.raises(AbilityFeatureError):
        _one({"kind": "SA", "ability": 36, "cumulate": True})                  # '+' with nothing patches nothing


def test_multiline_code_block_warns():
    _l, warns = af.build_lines([{"kind": "AA", "ability": 1, "features": "[code=Power]\n1 + 2\n[/code]"}])
    assert any("multiple lines" in w for w in warns)                           # engine [code] regex isn't multiline


def test_aa_id_zero_warns():
    _l, warns = af.build_lines([{"kind": "AA", "ability": 0, "features": "[code=Power] 1 [/code]"}])
    assert any("Void" in w for w in warns)


def test_emit_tolerates_single_table(tmp_path):
    # a single [ability_feature] table (a dict, not the [[...]] array) must BUILD, not crash -- match the lint path
    from ff9mapkit import build as B
    from ff9mapkit.config import ModLayout

    class _P:
        raw = {"ability_feature": {"kind": "SA", "ability": 2, "features": "StatusInit AutoStatus Haste"}}

    layout = ModLayout(tmp_path)
    B._emit_ability_features([_P()], layout)
    assert layout.ability_features_txt.is_file()


def test_merge_replaces_prior_block_idempotent():
    block = [">SA 2+ AutoHaste", "StatusInit AutoStatus Haste", ""]
    once = af.merge_ability_features("# base\n>SA 0 keep\n", block, 4003)
    assert "keep" in once and ">SA 2+ AutoHaste" in once and "## >>> ff9mapkit ability_feature 4003" in once
    twice = af.merge_ability_features(once, block, 4003)                        # idempotent
    assert twice == once
    stripped = af.merge_ability_features(once, [], 4003)                        # empty -> strips our block
    assert ">SA 2+ AutoHaste" not in stripped and "keep" in stripped
