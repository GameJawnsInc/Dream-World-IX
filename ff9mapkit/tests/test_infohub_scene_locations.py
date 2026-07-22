"""``infohub.detail()``'s scene-kind enrichment (rung 6) -- the ``scene_usage_fn`` hook that keeps the
Info Hub spine install-free while letting a frontend add "where does this fight actually happen" facts
(classification / enemy names / places) plus ``d.locations`` to a battle-scene entry, and ``forms_qt``'s
real wiring of that hook through :mod:`battle.locate`.

Two lanes, like ``test_battle_locate.py``:
  * OFFLINE -- a fake hook proves the ``infohub`` contract: facts populated, ``d.locations`` shaped
    ``[(field_id, name), ...]``, per-key graceful degrade, and the ID-SPACE DISCRIMINATION between
    ``usage_fn`` (model ids) and ``scene_usage_fn`` (scene ids) -- neither hook fires for the other kind's
    entry, since a bare int can't tell which table it came from.
  * GAME-GATED -- the REAL ``forms_qt._scene_usage`` hook, wired through ``infohub.detail`` for scene 67,
    anchored against the same Evil Forest / Goblin facts ``test_battle_locate.py`` proves directly against
    :mod:`battle.locate`.
"""
from __future__ import annotations

import pytest

from ff9mapkit import config, infohub


def _game_ready():
    try:
        import UnityPy  # noqa: F401
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


def _scene_entry():
    """A stable scene Entry, independent of install content -- id 67's BSC name is a baked ``_scenedb``
    table lookup (install-free), same anchor ``test_battle_locate.py`` uses for the game-gated lane."""
    e = infohub.find("BSC_EF_R007", kind="scene")
    assert e is not None and e.ident == 67
    return e


# --------------------------------------------------------------------------------------------- offline ---
def test_scene_detail_has_no_locations_without_a_hook():
    e = _scene_entry()
    d = infohub.detail(e)
    assert d.kind == "scene"
    assert d.locations is None                                          # install-free by default
    assert ("kind", "battle scene") in d.facts
    assert ("id", "67") in d.facts
    assert ("bsc name", "BSC_EF_R007") in d.facts                       # baked lookup, no hook needed


def test_scene_detail_enriched_via_fake_hook():
    e = _scene_entry()
    seen = []

    def fake_hook(sid):
        seen.append(sid)
        return {"classification": "placed", "enemies": ["Goblin", "Fang"],
                "attacks": ["Knife", "Goblin Punch"],
                "places": ["Evil Forest (field 250, random)"],
                "locations": [(250, "Evil Forest")]}

    d = infohub.detail(e, scene_usage_fn=fake_hook)
    assert seen == [67]                                                  # called with the SCENE id
    assert ("classification", "placed") in d.facts
    assert any(lbl == "enemies" and val == "Goblin, Fang" for lbl, val in d.facts)
    assert any(lbl == "attacks" and val == "Knife, Goblin Punch" for lbl, val in d.facts)
    assert ("place", "Evil Forest (field 250, random)") in d.facts
    assert d.locations == [(250, "Evil Forest")]                         # shape forms_qt's render expects


def test_scene_detail_hook_exception_degrades_gracefully():
    e = _scene_entry()

    def boom(_sid):
        raise RuntimeError("no install")

    d = infohub.detail(e, scene_usage_fn=boom)                           # same degrade shape as usage_fn
    assert d.locations is None
    assert not any(lbl == "classification" for lbl, _ in d.facts)
    assert not any(lbl == "enemies" for lbl, _ in d.facts)


def test_scene_detail_hook_missing_keys_degrade_per_key():
    e = _scene_entry()
    d = infohub.detail(e, scene_usage_fn=lambda sid: {"enemies": ["Goblin"]})
    assert not any(lbl == "classification" for lbl, _ in d.facts)        # key absent -> fact simply omitted
    assert not any(lbl == "attacks" for lbl, _ in d.facts)              # attacks absent -> no attacks fact
    assert any(lbl == "enemies" and val == "Goblin" for lbl, val in d.facts)
    assert d.locations is None                                           # "locations" key absent -> stays None


def test_scene_detail_hook_returning_none_is_a_noop():
    e = _scene_entry()
    d = infohub.detail(e, scene_usage_fn=lambda sid: None)
    assert d.locations is None
    assert d.facts == [("kind", "battle scene"), ("id", "67"), ("bsc name", "BSC_EF_R007")]


def test_scene_usage_fn_does_not_leak_into_model_branch():
    # the ID-SPACE DISCRIMINATION: a scene_usage_fn passed alongside a MODEL-kind entry must never fire --
    # model details are keyed by usage_fn only (scene ids and model ids are disjoint tables, same int space).
    e = infohub.find("black_mage", kind="archetype")
    called = []
    d = infohub.detail(e, scene_usage_fn=lambda sid: called.append(sid) or {"locations": [(1, "x")]})
    assert called == []
    assert d.locations is None


def test_usage_fn_does_not_leak_into_scene_branch():
    e = _scene_entry()
    called = []
    d = infohub.detail(e, usage_fn=lambda mid: called.append(mid) or [(1, "x")])
    assert called == []
    assert d.locations is None


def test_model_branch_usage_fn_behavior_is_unchanged():
    # regression: adding scene_usage_fn must not disturb the existing model-kind usage_fn contract.
    e = infohub.find("black_mage", kind="archetype")
    assert infohub.detail(e).locations is None
    assert infohub.detail(e, usage_fn=lambda mid: [(401, "Dali/Underground")]).locations \
        == [(401, "Dali/Underground")]


# ---------------------------------------------------------------------------------------- game-gated ---
@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_scene67_detail_shows_evil_forest_and_goblin_via_real_hook():
    pytest.importorskip("PySide6")
    from ff9mapkit.battle import locate as loc
    from ff9mapkit.workspace import forms_qt

    loc._MEMO.clear()                                       # drop any synthetic map a sibling test injected
    loc.build_map()                                         # warm the REAL map ourselves: _scene_usage is
    #                                                         warm-only by design, and nothing guarantees
    #                                                         another test has written the shared disk cache
    #                                                         yet (fresh worktree + xdist: the builder runs
    #                                                         in a different worker)
    e = _scene_entry()
    d = infohub.detail(e, scene_usage_fn=forms_qt._scene_usage)
    assert ("classification", "placed") in d.facts
    assert any(lbl == "enemies" and val == "Goblin, Fang" for lbl, val in d.facts)
    assert any(lbl == "place" and "Evil Forest" in val and "field 250" in val for lbl, val in d.facts)
    assert d.locations == [(250, "Evil Forest")]
