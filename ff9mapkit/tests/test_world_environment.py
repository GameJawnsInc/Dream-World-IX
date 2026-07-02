"""[world_environment] -> Memoria Environment.txt (overworld weather / effects / place forms).

Pins that the emitter renders the exact token grammar the engine parses (WorldConfiguration.cs:358/361),
the condition forms (true/false/NCalc), validation, and that write_environment lands the file at
<mod>/StreamingAssets/Data/World/Environment.txt.
"""
from __future__ import annotations

import re

import pytest

from ff9mapkit import config
from ff9mapkit.world import environment as ENV

# the engine's OWN parser (verbatim from WorldConfiguration.LoadWorldEnvironmentFile)
_TOKEN = re.compile(r"^(Place|Effect|Mist|Disc4|Rain|Light|Title)\s+(.*)$", re.M)
_ARG = re.compile(r"\s*(\[[^\]]*\]|[^\]][^\s]*)")


def _parse(txt: str):
    """Parse Environment.txt the way the engine does -> [(kind, [args...]), ...]."""
    return [(m.group(1), [a.group(1) for a in _ARG.finditer(m.group(2).strip())]) for m in _TOKEN.finditer(txt)]


def test_emits_the_full_grammar_and_parses_under_engine_regex():
    cfg = {
        "mist": False,
        "disc4": "w_frameDisc == 4",
        "rain": [{"position": [700, -800], "radius_large": 400, "radius_small": 100, "speed": 5, "strength": 200}],
        "light": [{"position": [900, -600], "radius": 300, "light": 2, "condition": True}],
        "effect": [{"name": "AlexandriaWaterfall", "on": False}],
        "place": [{"name": "Alexandria", "on": True}],
    }
    toks = _parse(ENV.build_environment_txt(cfg))
    kinds = [k for k, _ in toks]
    assert kinds == ["Mist", "Disc4", "Rain", "Light", "Effect", "Place"]
    d = dict(toks)
    assert d["Mist"] == ["[Condition=false]"]
    assert d["Disc4"] == ["[Condition=w_frameDisc == 4]"]           # multi-word NCalc stays ONE arg (inside [])
    assert d["Rain"][0] == "Add" and "[Position=(700,-800)]" in d["Rain"] and "[RainStrength=200]" in d["Rain"]
    assert d["Light"][0] == "Add" and "[Light=2]" in d["Light"] and "[Condition=true]" in d["Light"]
    assert d["Effect"] == ["AlexandriaWaterfall", "[Condition=false]"]
    assert d["Place"] == ["Alexandria", "[Condition=true]"]


def test_condition_forms_and_effect_defaults_on():
    # bool True/False -> true/false; an effect with neither on nor condition defaults to on (true)
    assert "Mist [Condition=true]" in ENV.build_environment_txt({"mist": True})
    assert "Mist [Condition=false]" in ENV.build_environment_txt({"mist": False})
    assert "Effect Windmill [Condition=true]" in ENV.build_environment_txt({"effect": [{"name": "Windmill"}]})
    # omitting a key emits nothing for it (a minimal file, no spurious lines)
    txt = ENV.build_environment_txt({"mist": True})
    assert "Disc4" not in txt and "Rain" not in txt and "Place" not in txt


def test_validation_catches_bad_input():
    probs = ENV.validate_environment({
        "mist": 3,                                   # not bool/str
        "rain": [{"position": [1]}],                 # bad position
        "light": [{"position": [0, 0], "light": "x"}],  # non-int param
        "effect": [{"name": "Nope"}],                # unknown effect
        "place": [{}],                               # missing name
    })
    assert any("mist must be" in p for p in probs)
    assert any("rain]] #0 needs position" in p for p in probs)
    assert any("light]] #0 light must be an integer" in p for p in probs)
    assert any("unknown effect name 'Nope'" in p for p in probs)
    assert any("place]] #0 needs a `name`" in p for p in probs)
    # a clean config -> no problems, and build raises on a dirty one
    assert ENV.validate_environment({"mist": True, "place": [{"name": "Cleyra", "on": True}]}) == []
    with pytest.raises(ValueError):
        ENV.build_environment_txt({"effect": [{"name": "Nope"}]})


def test_enum_name_sets_are_reasonable():
    assert {"Alexandria", "Cleyra", "Lindblum", "SouthGate_Gate"} <= ENV.WORLD_PLACES
    assert {"AlexandriaWaterfall", "SandStorm", "WindShrine", "Windmill"} <= ENV.WORLD_EFFECTS


def test_write_environment_lands_at_the_engine_path(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    dest = ENV.write_environment({"mist": False}, mod_folder="FF9CustomMap")
    assert dest == (tmp_path / "FF9CustomMap" / "StreamingAssets/Data/World/Environment.txt").resolve()
    assert dest.is_file()
    assert "Mist [Condition=false]" in dest.read_text(encoding="utf-8")
