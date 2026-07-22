"""``battle.locate`` -- the field<->scene census, zone join, classification, and monster-name join.

Two lanes, like ``test_eventscan.py``:
  * OFFLINE -- the join/classify/cache logic exercised against synthetic census dicts and the packaged
    ``region_catalog.toml`` (no install needed, no monkeypatched game bytes).
  * GAME-GATED -- the documented anchors against the user's real install (scene 67 = Goblin/Fang @ Evil
    Forest, field 50 -> scripted [336], the classification totals, the ~562 US text pools).
"""
from __future__ import annotations

import json

import pytest

from ff9mapkit import config
from ff9mapkit.battle import locate as loc


def _game_ready():
    try:
        import UnityPy  # noqa: F401
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


@pytest.fixture(autouse=True)
def _clean_memo():
    """Every test starts from a clean in-process memo so an injected/synthetic BattleMap in one test
    never leaks into another (the module-level ``_MEMO`` is otherwise long-lived by design)."""
    loc._MEMO.clear()
    yield
    loc._MEMO.clear()


def _inject(bm: loc.BattleMap, game=None):
    """Seed the in-process memo directly with a synthetic map -- the offline testing trick for the public
    API: ``build_map`` returns ``_MEMO`` on a hit before it ever touches disk or the install."""
    loc._MEMO[loc._memo_key(game)] = bm


# ------------------------------------------------------------------------------------------- offline ---
def test_field_record_honesty_none_scenes(monkeypatch):
    # no SetRandomBattles at all + no scripted battles -> a genuinely encounter-less field -> None
    monkeypatch.setattr(loc.eventscan, "scan_encounter", lambda eb: None)
    monkeypatch.setattr(loc, "_srb_status", lambda eb: "none")
    monkeypatch.setattr(loc.eventscan, "scan_battle_scenes", lambda eb: [])
    assert loc._field_record(b"fake") is None


def test_field_record_computed_operand_honesty(monkeypatch):
    # SetRandomBattles IS present but its operand is a runtime expression -- scan_encounter declines (None),
    # but the field must NOT be silently treated as encounter-less: computed=True, not dropped.
    monkeypatch.setattr(loc.eventscan, "scan_encounter", lambda eb: None)
    monkeypatch.setattr(loc, "_srb_status", lambda eb: "computed")
    monkeypatch.setattr(loc.eventscan, "scan_battle_scenes", lambda eb: [])
    rec = loc._field_record(b"fake")
    assert rec == {"random": [], "scripted": [], "computed": True}


def test_field_record_scripted_only_is_not_computed(monkeypatch):
    monkeypatch.setattr(loc.eventscan, "scan_encounter", lambda eb: None)
    monkeypatch.setattr(loc, "_srb_status", lambda eb: "none")
    monkeypatch.setattr(loc.eventscan, "scan_battle_scenes", lambda eb: [336])
    rec = loc._field_record(b"fake")
    assert rec == {"random": [], "scripted": [336], "computed": False}


def test_scene_site_index_dedups_repeated_slots():
    # field 250's real SetRandomBattles table repeats scene 67 across all 4 slots -- one row, not four.
    census = {250: {"random": [67, 67, 67, 67], "scripted": []}}
    idx = loc._scene_site_index(census)
    assert idx[67] == [(250, "random")]


def test_scene_site_index_keeps_both_kinds_for_a_dual_scene():
    # 4 real scenes (6, 893, 897, 901) are BOTH random and scripted somewhere -- kind is part of the dedup
    # key, so a (field, scene) pair firing both ways keeps BOTH rows.
    census = {900: {"random": [901], "scripted": [901]}}
    idx = loc._scene_site_index(census)
    assert idx[901] == [(900, "random"), (900, "scripted")]


def test_scene_site_index_distinct_fields_both_present():
    census = {
        10: {"random": [5], "scripted": []},
        20: {"random": [], "scripted": [5]},
    }
    idx = loc._scene_site_index(census)
    assert idx[5] == [(10, "random"), (20, "scripted")]


def test_zone_join_field_70_is_the_one_documented_gap():
    field_arc, arcs = loc._zone_join()
    assert 70 not in field_arc                       # the one real field id no arc's `members` names
    assert len(arcs) >= 70                            # ~73 arcs in the packaged catalog
    assert field_arc.get(250) in arcs                 # a normal field DOES resolve to a real arc key
    assert arcs[field_arc[250]]["name"] == "Evil Forest"


def test_classify_scenes_placed_wins_over_model_bucket():
    # pick a real BSC_B3_* name/id from the table and pretend the census reached it -- 'placed' must win
    # over the name-derived 'model-bucket' bucket (reached-ness never loses to a name heuristic).
    b3_name, b3_id = next((n, i) for n, i in loc.SCENES.items() if n.upper().startswith("BSC_B3_"))
    census = {1: {"random": [b3_id], "scripted": []}}
    cls, _junk = loc._classify_scenes(census)
    assert cls[b3_id] == "placed"


def test_classify_scenes_unreached_buckets():
    b3_name, b3_id = next((n, i) for n, i in loc.SCENES.items() if n.upper().startswith("BSC_B3_"))
    wm_name, wm_id = next((n, i) for n, i in loc.SCENES.items() if n.upper().startswith("BSC_WM_"))
    other_name, other_id = next((n, i) for n, i in loc.SCENES.items()
                                if not n.upper().startswith(("BSC_B3_", "BSC_WM_")))
    cls, junk = loc._classify_scenes({})                # nothing reached
    assert cls[b3_id] == "model-bucket"
    assert cls[wm_id] == "overworld"
    assert cls[other_id] == "unplaced"
    assert junk == sorted(i for i in (220, 238) if i in loc.SCENES.values())


def test_scene_places_groups_by_arc_and_field70_is_arc_none():
    bm = loc.BattleMap(
        version=loc.CACHE_VERSION,
        census={},
        scene_sites={99: [(250, "random"), (70, "scripted")]},
        field_arc={250: "evil_forest"},
        arcs={"evil_forest": {"name": "Evil Forest", "zone": "evft"}},
        names={},
    )
    _inject(bm)
    places = loc.scene_places(99)
    by_arc = {g["arc"]: g for g in places}
    assert by_arc["evil_forest"]["fields"] == [250]
    assert by_arc["evil_forest"]["kinds"] == ["random"]
    assert by_arc[None]["arc_name"] is None
    assert by_arc[None]["fields"] == [70]


def test_field_battles_and_classify_and_monster_lookup_via_injected_map():
    bm = loc.BattleMap(
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
    _inject(bm)
    assert loc.field_battles(250) == {"random": [67], "scripted": [], "computed": False}
    assert loc.field_battles(99999) == {"random": [], "scripted": [], "computed": False}
    assert loc.classify(67) == "placed"
    assert loc.classify(424242) == "unplaced"          # an id the table has never heard of -> honest default
    assert loc.monster_names(67) == ["Goblin", "Fang"]
    assert loc.monster_names(67, lang="fr") == ["Goblin", "Fang"]   # missing lang -> falls back to 'us'
    assert loc.attack_names(67) == ["Knife", "Goblin Punch", None]
    assert loc.monster_names(424242) is None
    assert loc.find_monster("gob") == [(67, "Goblin")]
    assert loc.find_monster("") == []
    label = loc.scene_label(67)
    assert label == "Goblin, Fang -- Evil Forest (field 250, random)"
    report = loc.unresolved_report()
    assert report["scene_count"] == 856 and report["field_count"] == 1


def test_scene_label_unplaced_scene_falls_back_to_bsc_name():
    any_name, any_id = next(iter(loc.SCENES.items()))
    bm = loc.BattleMap(version=loc.CACHE_VERSION, census={}, scene_sites={}, field_arc={}, arcs={}, names={})
    _inject(bm)
    label = loc.scene_label(any_id)
    assert label.endswith("-- unplaced")
    assert any_name in label or f"scene {any_id}" in label


def test_cache_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("FF9MAPKIT_DATA", str(tmp_path))
    calls = {"n": 0}
    synthetic = loc.BattleMap(
        version=loc.CACHE_VERSION,
        census={250: {"random": [67], "scripted": [], "computed": False}},
        computed_fields=[],
        scene_sites={67: [(250, "random")]},
        field_arc={250: "evil_forest"},
        arcs={"evil_forest": {"name": "Evil Forest", "zone": "evft"}},
        classification={67: "placed"},
        junk_ids=[220, 238],
        names={67: {"typecount": 2, "atkcount": 0, "names": {"us": ["Goblin", "Fang"]}, "attacks": {"us": []}}},
        name_gaps=[],
        scene_count=856, field_count=1,
    )

    def _fake_build(game=None):
        calls["n"] += 1
        return synthetic

    monkeypatch.setattr(loc, "_build_fresh", _fake_build)

    bm1 = loc.build_map(force=True)                    # forces a fresh build + writes the cache
    assert calls["n"] == 1
    assert bm1.names[67]["names"]["us"] == ["Goblin", "Fang"]
    assert (tmp_path / "battlemap" / "battlemap.json").is_file()

    loc._MEMO.clear()                                   # drop the in-process memo -- force a disk-cache read
    bm2 = loc.build_map()                               # NOT force=True -- must load from disk, not rebuild
    assert calls["n"] == 1                               # _build_fresh was NOT called again
    assert bm2.census == bm1.census
    assert bm2.scene_sites == bm1.scene_sites
    assert bm2.names[67]["names"]["us"] == ["Goblin", "Fang"]
    assert bm2.field_arc == bm1.field_arc


def test_cache_ignores_a_stale_version(tmp_path, monkeypatch):
    monkeypatch.setenv("FF9MAPKIT_DATA", str(tmp_path))
    d = tmp_path / "battlemap"
    d.mkdir(parents=True)
    (d / "battlemap.json").write_text(json.dumps({"version": loc.CACHE_VERSION - 1}), encoding="utf-8")
    calls = {"n": 0}

    def _fake_build(game=None):
        calls["n"] += 1
        return loc.BattleMap(version=loc.CACHE_VERSION, census={}, scene_sites={}, field_arc={}, arcs={}, names={})

    monkeypatch.setattr(loc, "_build_fresh", _fake_build)
    loc.build_map()
    assert calls["n"] == 1                               # the stale-version cache file was ignored, rebuilt


def test_write_cache_failure_never_kills_the_build(tmp_path, monkeypatch):
    """A denied cache write (Windows ``os.replace`` vs a concurrent xdist worker / CLI run holding
    battlemap.json open) is DROPPED, not raised: build_map still returns + memoizes the fresh map --
    the disk file is pure acceleration for the next process."""
    monkeypatch.setenv("FF9MAPKIT_DATA", str(tmp_path))
    synthetic = loc.BattleMap(version=loc.CACHE_VERSION, census={}, scene_sites={}, field_arc={},
                              arcs={}, names={})
    monkeypatch.setattr(loc, "_build_fresh", lambda game=None: synthetic)

    def _deny(*_a, **_k):
        raise PermissionError("battlemap.json is open in another process")
    monkeypatch.setattr(loc, "atomic_write_text", _deny)

    bm = loc.build_map(force=True)
    assert bm is synthetic                               # the build survived the dropped write
    assert loc._MEMO[loc._memo_key(None)] is synthetic   # and this process stays warm
    assert not (tmp_path / "battlemap" / "battlemap.json").is_file()


def test_cached_map_memo_then_disk_never_builds(tmp_path, monkeypatch):
    """cached_map is the 'reuse if warm, else None' probe: memo first, then the disk cache -- and it must
    NEVER trigger a fresh build (that's what makes it safe for `encounters --no-names` to consult)."""
    monkeypatch.setenv("FF9MAPKIT_DATA", str(tmp_path))

    def _boom(*a, **k):
        raise AssertionError("cached_map must never build")
    monkeypatch.setattr(loc, "_build_fresh", _boom)

    assert loc.cached_map() is None                      # nothing warm anywhere -> None, no build

    synthetic = loc.BattleMap(version=loc.CACHE_VERSION,
                              census={250: {"random": [67], "scripted": [], "computed": False}},
                              scene_sites={67: [(250, "random")]}, field_arc={}, arcs={}, names={})
    _inject(synthetic)
    assert loc.cached_map() is synthetic                 # memo hit

    loc._MEMO.clear()
    loc._write_cache(synthetic)
    got = loc.cached_map()                               # disk hit (re-memoized), still no build
    assert got is not None and got.scene_sites == {67: [(250, "random")]}


def test_unresolved_report_threads_force(monkeypatch):
    """unresolved_report(force=True) must reach build_map with force=True (the CLI's --unresolved --force
    was a silent no-op before this parameter existed)."""
    seen = {}

    def _record(game=None, *, force=False):
        seen["force"] = force
        return loc.BattleMap(version=loc.CACHE_VERSION, census={}, scene_sites={}, field_arc={}, arcs={},
                             names={})
    monkeypatch.setattr(loc, "build_map", _record)

    loc.unresolved_report(force=True)
    assert seen["force"] is True
    loc.unresolved_report()
    assert seen["force"] is False


# ---------------------------------------------------------------------------------------- game-gated ---
@pytest.fixture(scope="module")
def real_map():
    return loc.build_map()


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_anchor_scene67_evil_forest(real_map):
    assert loc.scene_sites(67) == [(250, "random")]
    places = loc.scene_places(67)
    assert len(places) == 1
    assert places[0]["arc"] == "evil_forest"
    assert places[0]["arc_name"] == "Evil Forest"
    assert places[0]["fields"] == [250]
    assert places[0]["kinds"] == ["random"]


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_anchor_field50_scripted_battle(real_map):
    assert loc.field_battles(50)["scripted"] == [336]


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_anchor_goblin_names(real_map):
    assert loc.monster_names(67) == ["Goblin", "Fang"]
    assert loc.scene_label(67) == "Goblin, Fang -- Evil Forest (field 250, random)"


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_classification_totals(real_map):
    from collections import Counter
    totals = Counter(real_map.classification.values())
    assert totals["placed"] == 284
    assert totals["model-bucket"] == 176
    assert totals["overworld"] == 274


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_us_text_pool_count_is_roughly_562(real_map):
    us_pools = sum(1 for rec in real_map.names.values() if "us" in rec["names"])
    assert 550 <= us_pools <= 575


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_find_monster_reverse_lookup_real_install(real_map):
    hits = loc.find_monster("goblin")
    assert (67, "Goblin") in hits
    assert all("goblin" in nm.lower() for _sid, nm in hits)


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_unresolved_report_shape(real_map):
    report = loc.unresolved_report()
    assert report["cache_version"] == loc.CACHE_VERSION
    assert report["scene_count"] == 856
    assert 70 in report["fields_without_arc"]
    assert set(report["classification_totals"]) <= {"placed", "model-bucket", "overworld", "unplaced"}
