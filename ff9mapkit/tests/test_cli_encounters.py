"""The ``encounters`` CLI verb (rung 7) + ``battle-scene``'s "found in"/real-name enrichment (rung 8) --
both wired on top of :mod:`battle.locate` in ``cli.py`` only.

Two lanes, like ``test_battle_locate.py``:
  * OFFLINE -- a synthetic :class:`battle.locate.BattleMap` injected into the in-process memo (the same
    trick ``test_battle_locate.py`` uses), plus monkeypatched private census helpers for the ``--no-names``
    path (which deliberately bypasses ``build_map``/the memo -- see ``cli._cmd_encounters``).
  * GAME-GATED -- the documented anchors against the user's real install: scene 67 = Goblin/Fang @ Evil
    Forest (field 250, random), ``battle-scene EF_R007``'s enriched output.
"""
from __future__ import annotations

import pytest

from ff9mapkit import cli, config
from ff9mapkit.battle import locate as loc


def _game_ready():
    try:
        import UnityPy  # noqa: F401
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


@pytest.fixture(autouse=True)
def _clean_memo():
    loc._MEMO.clear()
    yield
    loc._MEMO.clear()


def _fake_map() -> loc.BattleMap:
    """A tiny, install-independent BattleMap: one placed scene (67, 'Evil Forest' arc, random @ field 250),
    one scripted scene (42) on an ARC-LESS field (999, mirroring real field 70's documented gap), and one
    of each other classification bucket so the summary/--unresolved totals are all non-trivial."""
    census = {
        250: {"random": [67], "scripted": [], "computed": False},
        999: {"random": [], "scripted": [42], "computed": False},
    }
    field_arc = {250: "evil_forest"}                                  # 999 deliberately absent -> unmapped
    arcs = {"evil_forest": {"name": "Evil Forest", "zone": "evft"}}
    classification = {67: "placed", 42: "placed", 900: "model-bucket", 901: "overworld", 902: "unplaced"}
    scene_sites = {67: [(250, "random")], 42: [(999, "scripted")]}
    names = {67: {"typecount": 2, "atkcount": 1,
                  "names": {"us": ["Goblin", "Fang"]}, "attacks": {"us": ["Slash"]}}}
    return loc.BattleMap(version=loc.CACHE_VERSION, census=census, computed_fields=[],
                          scene_sites=scene_sites, field_arc=field_arc, arcs=arcs,
                          classification=classification, junk_ids=[220, 238], names=names, name_gaps=[],
                          scene_count=10, field_count=len(census))


def _inject(bm: loc.BattleMap, game=None):
    loc._MEMO[loc._memo_key(game)] = bm


# ------------------------------------------------------------------------------------------- offline ---
def test_encounters_summary_offline(capsys):
    _inject(_fake_map())
    assert cli.main(["encounters"]) == 0
    out = capsys.readouterr().out
    assert "2 place(s) with battle content" in out
    assert "Evil Forest" in out
    assert "(unmapped field)" in out
    assert "2 placed, 1 model-bucket, 1 overworld, 1 unplaced" in out


def test_encounters_place_query_offline(capsys):
    _inject(_fake_map())
    assert cli.main(["encounters", "Evil Forest"]) == 0
    out = capsys.readouterr().out
    assert "[place]" in out
    assert "scene 67" in out and "BSC_EF_R007" in out
    assert "field 250" in out
    assert "Goblin, Fang" in out


def test_encounters_monster_query_auto_detect_offline(capsys):
    _inject(_fake_map())
    assert cli.main(["encounters", "Goblin"]) == 0
    out = capsys.readouterr().out
    assert "[monster]" in out
    assert "scene 67" in out
    assert "Goblin, Fang" in out


def test_encounters_monster_flag_forces_axis_offline(capsys):
    # "Evil Forest" would ALSO match the place axis, but --monster forces monster-only (no hit -> no match).
    _inject(_fake_map())
    rc = cli.main(["encounters", "--monster", "Evil Forest"])
    assert rc == 1
    assert "no place, monster, or scene matches" in capsys.readouterr().err


def test_encounters_place_flag_forces_axis_offline(capsys):
    # "Goblin" would ALSO match the monster axis, but --place forces place-only (no arc named 'Goblin').
    _inject(_fake_map())
    rc = cli.main(["encounters", "--place", "Goblin"])
    assert rc == 1
    assert "no place, monster, or scene matches" in capsys.readouterr().err


def test_encounters_monster_and_place_flags_are_mutually_exclusive():
    with pytest.raises(SystemExit) as exc:
        cli.main(["encounters", "--monster", "--place", "Goblin"])
    assert exc.value.code == 2


def test_encounters_scene_flag_by_id_offline(capsys):
    _inject(_fake_map())
    assert cli.main(["encounters", "--scene", "67"]) == 0
    out = capsys.readouterr().out
    assert "scene 67  (BSC_EF_R007)  [placed]" in out            # BSC name is a baked catalog lookup
    assert "Evil Forest" in out and "field(s) 250" in out and "(random)" in out
    assert "monsters: Goblin, Fang" in out
    assert "attacks:  Slash" in out


def test_encounters_scene_auto_detected_from_bare_query_offline(capsys):
    _inject(_fake_map())
    assert cli.main(["encounters", "67"]) == 0
    assert "scene 67  (BSC_EF_R007)  [placed]" in capsys.readouterr().out


def test_encounters_scene_unplaced_shows_honest_gap_offline(capsys):
    _inject(_fake_map())
    assert cli.main(["encounters", "--scene", "902"]) == 0
    out = capsys.readouterr().out
    assert "[unplaced]" in out
    assert "not reached by any real field's census" in out


def test_encounters_unknown_scene_name_errors_offline(capsys):
    _inject(_fake_map())
    rc = cli.main(["encounters", "--scene", "NOT_A_REAL_SCENE_NAME"])
    assert rc == 2
    assert "unknown battle scene" in capsys.readouterr().err


def test_encounters_unresolved_offline(capsys):
    _inject(_fake_map())
    assert cli.main(["encounters", "--unresolved"]) == 0
    out = capsys.readouterr().out
    assert "placed         2" in out
    assert "model-bucket   1" in out
    assert "overworld      1" in out
    assert "unplaced       1" in out
    assert "engine-skipped 'Junk?' scene id(s): [220, 238]" in out


def test_encounters_no_matches_message_offline(capsys):
    _inject(_fake_map())
    rc = cli.main(["encounters", "zzz_definitely_not_a_place_or_monster"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "no place, monster, or scene matches" in err
    assert "ff9mapkit scenes" in err and "--unresolved" in err


def test_encounters_no_names_bypasses_build_map_and_skips_monster_names(monkeypatch, capsys):
    """--no-names must use the PRIVATE, install-cheap helpers (never build_map/the memo -- proven here by
    monkeypatching them instead of injecting a memo) and must never print monster/attack names."""
    census = {250: {"random": [67], "scripted": [], "computed": False}}
    monkeypatch.setattr(loc, "_census", lambda game=None: (census, []))
    monkeypatch.setattr(loc, "_zone_join",
                        lambda: ({250: "evil_forest"}, {"evil_forest": {"name": "Evil Forest", "zone": "evft"}}))
    monkeypatch.setattr(loc, "_classify_scenes", lambda c: ({67: "placed"}, []))

    def _boom(*a, **k):
        raise AssertionError("--no-names must not touch build_map")
    monkeypatch.setattr(loc, "build_map", _boom)

    assert cli.main(["encounters", "--scene", "67", "--no-names"]) == 0
    out = capsys.readouterr().out
    assert "Evil Forest" in out
    assert "monsters:" not in out and "attacks:" not in out


def test_encounters_no_names_and_monster_flag_conflict_is_cheap(monkeypatch, capsys):
    """The --monster/--no-names conflict must be caught BEFORE any census work (so it's a pure argparse-ish
    validation, not an install probe) -- proven by making the census helpers explode if ever called."""
    def _boom(*a, **k):
        raise AssertionError("must not reach the census with --monster --no-names")
    monkeypatch.setattr(loc, "_census", _boom)
    monkeypatch.setattr(loc, "build_map", _boom)

    rc = cli.main(["encounters", "--no-names", "--monster", "Goblin"])
    assert rc == 2
    assert "--monster needs monster-name data" in capsys.readouterr().err


def test_encounters_no_names_monster_axis_skipped_with_note(monkeypatch, capsys):
    # a bare query (no --monster flag) under --no-names can't search names either -- silently skipped, with
    # an explanatory note in the "no matches" message (not a crash / not a silent false negative).
    census = {250: {"random": [67], "scripted": [], "computed": False}}
    monkeypatch.setattr(loc, "_census", lambda game=None: (census, []))
    monkeypatch.setattr(loc, "_zone_join",
                        lambda: ({250: "evil_forest"}, {"evil_forest": {"name": "Evil Forest", "zone": "evft"}}))
    monkeypatch.setattr(loc, "_classify_scenes", lambda c: ({67: "placed"}, []))
    rc = cli.main(["encounters", "--no-names", "Goblin"])
    assert rc == 1
    assert "drop --no-names" in capsys.readouterr().err


# ---------------------------------------------------------------------------------------- game-gated ---
@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_encounters_scene_67_matches_battle_locate_anchor(capsys):
    rc = cli.main(["encounters", "--scene", "67"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "BSC_EF_R007" in out and "[placed]" in out
    assert "Evil Forest" in out and "field(s) 250" in out and "(random)" in out
    assert "monsters: Goblin, Fang" in out


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_encounters_goblin_query_finds_evil_forest(capsys):
    rc = cli.main(["encounters", "Goblin"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "scene 67" in out
    assert "Evil Forest" in out
    assert "Goblin, Fang" in out


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_encounters_summary_lists_evil_forest(capsys):
    rc = cli.main(["encounters"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "place(s) with battle content" in out
    assert "Evil Forest" in out
    assert "scene coverage:" in out


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_battle_scene_enrichment_shows_found_in_and_names(capsys):
    rc = cli.main(["battle-scene", "EF_R007"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "enemy type 0 -- Goblin" in out
    assert "enemy type 1 -- Fang" in out
    assert "found in: Evil Forest (field 250, random)" in out
