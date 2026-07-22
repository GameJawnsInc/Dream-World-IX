"""The Info Hub ``encounter`` kind -- the install-backed, PICKER-ONLY sibling of the static ``scene`` kind.

The whole point of the kind is the load-bearing constraint from the UI design: it is build-free. It reads
``battle.locate.cached_map()`` ONLY (warm memo/disk) and NEVER triggers the ~9s cold census -- warm it
labels rows with real monsters + place, cold it degrades to the baked ``BSC_`` names. So, like
``test_battle_locate.py``, two lanes:
  * OFFLINE -- a synthetic ``BattleMap`` injected into ``locate._MEMO`` proves the warm/cold labels, the
    picker-only-ness, the search axes (a monster query AND a place query both hit the one warm row), the
    snippet, and the detail (via a fake ``scene_usage_fn``, incl. the new ``attacks`` fact + the id-space
    discrimination the ``scene`` kind already guards).
  * GAME-GATED -- the documented scene-67 = Goblin/Fang @ Evil Forest anchor against the real install.
"""
from __future__ import annotations

import pytest

from ff9mapkit import config, infohub
from ff9mapkit.battle import locate as loc


def _game_ready():
    try:
        import UnityPy  # noqa: F401
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path, monkeypatch):
    """A clean in-process memo AND an empty on-disk cache dir, so a synthetic warm map in one test never
    leaks, and a 'cold' test really is cold (no stray battlemap.json from a prior real build on this box)."""
    monkeypatch.setenv("FF9MAPKIT_DATA", str(tmp_path))
    loc._MEMO.clear()
    yield
    loc._MEMO.clear()


def _warm_map():
    """The documented Evil-Forest anchor as a synthetic BattleMap (same shape test_battle_locate injects)."""
    return loc.BattleMap(
        version=loc.CACHE_VERSION,
        census={250: {"random": [67], "scripted": [], "computed": False}},
        scene_sites={67: [(250, "random")]},
        field_arc={250: "evil_forest"},
        arcs={"evil_forest": {"name": "Evil Forest", "zone": "evft"}},
        classification={67: "placed"},
        names={67: {"typecount": 2, "atkcount": 3,
                    "names": {"us": ["Goblin", "Fang"]},
                    "attacks": {"us": ["Knife", "Goblin Punch", None]}}},
        scene_count=856, field_count=1,
    )


def _inject(bm):
    loc._MEMO[loc._memo_key(None)] = bm


# --------------------------------------------------------------------------------------------- offline ---
def test_encounter_entries_cold_is_the_baked_bsc_fallback():
    # cold cache (empty memo + empty disk): a NEVER-EMPTY baked list, every row an encounter, ident an int,
    # and the summary invites the one-time build. No census is triggered (cached_map returned None).
    ents = infohub.encounter_entries()
    assert ents, "the cold fallback still lists every scene (baked BSC names)"
    assert all(e.kind == "encounter" and isinstance(e.ident, int) for e in ents)
    assert any("build the battle index" in e.summary for e in ents)


def test_encounter_entries_cold_never_builds(monkeypatch):
    # the load-bearing guarantee: encounter_entries reads cached_map, never build_map -- monkeypatch the
    # cold builder to explode, and prove the cold path still returns the baked fallback without calling it.
    def _boom(*a, **k):
        raise AssertionError("encounter_entries must never trigger a cold build")
    monkeypatch.setattr(loc, "_build_fresh", _boom)
    ents = infohub.encounter_entries()
    assert ents and all(e.kind == "encounter" for e in ents)


def test_encounter_entries_warm_are_rich_labeled():
    _inject(_warm_map())
    ents = infohub.encounter_entries()
    assert [e.ident for e in ents] == [67], "warm lists only the reached (scene_sites) scenes, one per id"
    e = ents[0]
    assert e.kind == "encounter"
    assert "Goblin" in e.name and "Evil Forest" in e.name, "the rich label carries monster AND place"
    assert e.summary == "battle scene #67 -- placed"


def test_browse_encounter_is_picker_only_not_in_the_kitchen_sink():
    _inject(_warm_map())
    assert "encounter" not in infohub.KINDS
    assert not any(e.kind == "encounter" for e in infohub.browse("", kinds=None, limit=None))
    assert [e.ident for e in infohub.browse("", kinds=["encounter"])] == [67]


def test_browse_matches_both_a_monster_and_a_place_query():
    # ONE warm row, two search axes -- the rich name folds monster + place, so both queries hit it with
    # zero new search code (infohub.browse's existing name/summary substring match).
    _inject(_warm_map())
    assert [e.ident for e in infohub.browse("goblin", kinds=["encounter"])] == [67]
    assert [e.ident for e in infohub.browse("evil forest", kinds=["encounter"])] == [67]


def test_snippet_encounter_is_the_id_first_block_with_a_label_comment():
    _inject(_warm_map())
    e = infohub.browse("", kinds=["encounter"])[0]
    assert infohub.snippet(e) == f"[encounter]\nscene = 67  # {e.name}"


def test_detail_encounter_rich_via_fake_hook_includes_attacks():
    e = infohub.Entry("encounter", "Goblin, Fang -- Evil Forest", None, "battle scene #67 -- placed", 67)
    seen = []

    def fake_hook(sid):
        seen.append(sid)
        return {"classification": "placed", "enemies": ["Goblin", "Fang"],
                "attacks": ["Knife", "Goblin Punch"], "places": ["Evil Forest (field 250, random)"],
                "locations": [(250, "Evil Forest")]}

    d = infohub.detail(e, scene_usage_fn=fake_hook)
    assert seen == [67]                                                  # called with the SCENE id
    assert d.kind == "encounter"
    assert ("classification", "placed") in d.facts
    assert any(lbl == "enemies" and val == "Goblin, Fang" for lbl, val in d.facts)
    assert any(lbl == "attacks" and val == "Knife, Goblin Punch" for lbl, val in d.facts)
    assert ("place", "Evil Forest (field 250, random)") in d.facts
    assert d.locations == [(250, "Evil Forest")]


def test_detail_encounter_without_a_hook_degrades_to_bare_scene_facts():
    e = infohub.Entry("encounter", "BSC_EF_R007", None, "battle scene #67", 67)
    d = infohub.detail(e, scene_usage_fn=None)                           # encounter rides the scene branch
    assert d.locations is None
    assert d.facts == [("kind", "battle scene"), ("id", "67"), ("bsc name", "BSC_EF_R007")]


def test_detail_encounter_usage_fn_does_not_fire_for_an_encounter():
    # id-space discrimination: an encounter's ident is a SCENE id -- the model-keyed usage_fn must never fire.
    e = infohub.Entry("encounter", "x", None, "", 67)
    called = []
    d = infohub.detail(e, usage_fn=lambda mid: called.append(mid) or [(1, "x")])
    assert called == []
    assert d.locations is None


# ---------------------------------------------------------------------------------------- game-gated ---
@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_encounter_entries_warm_real_install_has_evil_forest_goblin():
    loc.build_map()                                                     # a real cold build warms the memo
    ents = {e.ident: e for e in infohub.encounter_entries()}
    assert 67 in ents
    assert "Goblin" in ents[67].name and "Evil Forest" in ents[67].name
