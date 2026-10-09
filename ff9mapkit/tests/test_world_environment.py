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


def _engine_stack(files):
    """WorldConfiguration.PatchWorldEnvironment over ``files`` (the base file first, then the folders from the LOWEST
    priority to the highest) -> ({place: [cond]}, {effect: [cond]}, {"Mist"/"Disc4": [cond]}): the Dictionary/Simple
    token rules of LoadWorldEnvironmentDictionaryToken / LoadWorldEnvironmentSimpleToken (:395-442)."""
    places, effects, simple = {}, {}, {"Mist": [], "Disc4": []}
    for txt in files:
        for kind, args in _parse(txt):
            if kind in ("Place", "Effect") and args:
                d = places if kind == "Place" else effects
                if args[0] == "Clear":
                    d.clear()
                elif len(args) >= 2 and args[1] == "Clear":
                    d.pop(args[0], None)
                elif len(args) >= 2 and args[1].startswith("[Condition=") and args[1].endswith("]"):
                    d.setdefault(args[0], []).append(args[1][len("[Condition="):-1])
            elif kind in simple and args:
                if args[0] == "Clear":
                    simple[kind].clear()
                elif args[0].startswith("[Condition=") and args[0].endswith("]"):
                    simple[kind].append(args[0][len("[Condition="):-1])
    return places, effects, simple


def _conds(toks):
    """The non-Clear lines, kind -> args (a Clear line precedes each keyed line by default)."""
    return {k: a for k, a in toks if "Clear" not in a}


def test_emits_the_full_grammar_and_parses_under_engine_regex():
    cfg = {
        "mist": False,
        "disc4": "ScenarioCounter >= 11090",
        "rain": [{"position": [700, -800], "radius_large": 400, "radius_small": 100, "speed": 5, "strength": 200}],
        "light": [{"position": [900, -600], "radius": 300, "light": 2, "condition": True}],
        "effect": [{"name": "AlexandriaWaterfall", "on": False}],
        "place": [{"name": "Alexandria", "on": True}],
    }
    toks = _parse(ENV.build_environment_txt(cfg))
    kinds = [k for k, a in toks if "Clear" not in a]
    assert kinds == ["Mist", "Disc4", "Rain", "Light", "Effect", "Place"]
    d = _conds(toks)
    assert d["Mist"] == ["[Condition=false]"]
    assert d["Disc4"] == ["[Condition=ScenarioCounter >= 11090]"]   # multi-word NCalc stays ONE arg (inside [])
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
    assert set(ENV.FORM_PLACES) <= ENV.WORLD_PLACES and len(ENV.FORM_PLACES) == 9


# ---- THE STACK (terrain study defect 20): conditions for one key OR across mod folders unless a Clear drops them

LOWER = "Place Cleyra [Condition=true]\nPlace Alexandria [Condition=true]\nMist [Condition=true]\n"


def test_each_keyed_line_follows_its_clear_and_replaces_lower_folders():
    cfg = {"mist": False, "place": [{"name": "Cleyra", "condition": "ScenarioCounter >= 9999"}],
           "effect": [{"name": "Windmill", "on": False}]}
    txt = ENV.build_environment_txt(cfg)
    lines = [ln for ln in txt.splitlines() if not ln.startswith("#")]
    assert lines == ["Mist Clear", "Mist [Condition=false]", "Effect Windmill Clear", "Effect Windmill [Condition=false]",
                     "Place Cleyra Clear", "Place Cleyra [Condition=ScenarioCounter >= 9999]"]
    places, effects, simple = _engine_stack([LOWER, txt])
    assert places == {"Cleyra": ["ScenarioCounter >= 9999"], "Alexandria": ["true"]}   # surgical: Alexandria kept
    assert simple["Mist"] == ["false"] and effects == {"Windmill": ["false"]}


def test_stack_combine_ors_with_lower_folders_as_the_engine_does():
    txt = ENV.build_environment_txt({"stack": "combine", "mist": False, "place": [{"name": "Cleyra", "on": False}]})
    assert "Clear" not in txt
    places, _e, simple = _engine_stack([LOWER, txt])
    assert places["Cleyra"] == ["true", "false"] and simple["Mist"] == ["true", "false"]   # true OR false = on


def test_a_place_without_a_form_a_duplicate_and_a_bad_stack_refuse():
    probs = ENV.validate_environment({"stack": "or", "place": [{"name": "Treno"}, {"name": "Cleyra"},
                                                               {"name": "Cleyra"}]})
    assert any("stack must be one of" in p for p in probs)
    assert any("'Treno' has no alternate form" in p and "ChocoboParadise" in p for p in probs)
    assert any("'Cleyra' is listed twice" in p for p in probs)
    assert all(ENV.validate_environment({"place": [{"name": n}]}) == [] for n in ENV.FORM_PLACES)


def _stacked_game(tmp_path, files: dict, order=("HIGH", "MINE", "LOW")):
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "Memoria.ini").write_text("[Mod]\nFolderNames = " + ", ".join(f'"{f}"' for f in order) + "\n",
                                          encoding="utf-8")
    for folder, txt in files.items():
        p = tmp_path / (folder if folder else "") / ENV.ENVIRONMENT_REL_PATH
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt, encoding="utf-8")
    return tmp_path


def test_stack_report_names_lower_higher_and_clean_lines(tmp_path):
    game = _stacked_game(tmp_path, {"": "## Place Alexandria Clean (a comment: not parsed)\n",
                                    "HIGH": "Place Cleyra [Condition=x]\nEffect Windmill [Condition=true]\n",
                                    "LOW": "Place Cleyra [Condition=y]\r\nMist Clean\r\nPlace Lindblum Clean\r\n"})
    cfg = {"place": [{"name": "Cleyra", "on": True}]}
    rep = ENV.stack_report(cfg, mod_folder="MINE", game_dir=game)
    assert rep["in_stack"] is True
    assert rep["below"] == [("LOW", "Place Cleyra [Condition=y]")]
    assert rep["above"] == [("HIGH", "Place Cleyra [Condition=x]")]                    # Windmill: not our key
    assert rep["clean"] == [("LOW", "Mist Clean"), ("LOW", "Place Lindblum Clean")]
    assert ENV.stack_report(cfg, mod_folder="ELSEWHERE", game_dir=game)["in_stack"] is False
    wipe = _stacked_game(tmp_path / "w", {"LOW": "Place Clear\n"})
    assert ENV.stack_report(cfg, mod_folder="MINE", game_dir=wipe)["below"] == [("LOW", "Place Clear")]


def test_world_environment_cli_prints_the_stack(tmp_path, monkeypatch, capsys):
    from ff9mapkit import cli
    game = _stacked_game(tmp_path, {"HIGH": "Place Cleyra [Condition=x]\n", "LOW": "Place Cleyra [Condition=y]\n"})
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    toml = tmp_path / "env.toml"
    toml.write_text('[world_environment]\n[[world_environment.place]]\nname = "Cleyra"\non = false\n', encoding="utf-8")
    ns = cli.build_parser().parse_args(["world-environment", str(toml), "--mod-folder", "MINE"])
    assert cli._cmd_world_environment(ns) == 0
    out = capsys.readouterr().out
    assert "replaces LOW: `Place Cleyra [Condition=y]`" in out
    assert "!! WARNING: HIGH is higher priority and is read after this file" in out
    written = (game / "MINE" / ENV.ENVIRONMENT_REL_PATH).read_text(encoding="utf-8")
    places, _e, _s = _engine_stack([(game / "LOW" / ENV.ENVIRONMENT_REL_PATH).read_text(encoding="utf-8"), written,
                                    (game / "HIGH" / ENV.ENVIRONMENT_REL_PATH).read_text(encoding="utf-8")])
    assert places["Cleyra"] == ["false", "x"]                       # LOW replaced; HIGH, read later, still ORs in
    toml.write_text('[world_environment]\n[[world_environment.place]]\nname = "Treno"\n', encoding="utf-8")
    assert cli._cmd_world_environment(cli.build_parser().parse_args(
        ["world-environment", str(toml), "--mod-folder", "MINE"])) == 2
    assert "has no alternate form" in capsys.readouterr().err


def test_write_environment_lands_at_the_engine_path(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    dest = ENV.write_environment({"mist": False}, mod_folder="FF9CustomMap")
    assert dest == (tmp_path / "FF9CustomMap" / "StreamingAssets/Data/World/Environment.txt").resolve()
    assert dest.is_file()
    assert "Mist [Condition=false]" in dest.read_text(encoding="utf-8")
