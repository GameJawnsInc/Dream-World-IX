"""Donor battle-BGM auto-detection (FORK_FIDELITY.md #6): battle_bgm reads the install's
``BtlEncountBgmMetaData.txt`` ``(field, scene) -> song`` map (provenance-clean, live), and ``import``
prefills ``[encounter] battle_music`` with the donor's real song so a fork doesn't fall back to the
generic Battle Theme. These tests are install-free -- the parse + lookup layers are pure, and the extract
wiring is exercised with an injected map (no UnityPy / no game)."""
from pathlib import Path

import pytest

from ff9mapkit import battle_bgm, eventscan, extract
from ff9mapkit.eb import edit

ALEX100 = (Path(__file__).parent / "fixtures" / "alex100-us.eb.bytes").read_bytes()  # a real town field (no battles)


@pytest.fixture(autouse=True)
def _reset_cache():
    """battle_bgm caches the parsed map in a module global; isolate each test (so an install read or an
    injected map from one test never leaks into the next)."""
    saved = battle_bgm._CACHE
    battle_bgm._CACHE = None
    yield
    battle_bgm._CACHE = saved


# ---- parse: the SE JSON shape -> {int field: {int scene: int song}} ----------------------------
def test_parse_real_shape():
    table = battle_bgm.parse('{"257": {"303": "35"}, "250": {"67": "0"}, "100": {}}')
    assert table == {257: {303: 35}, 250: {67: 0}, 100: {}}


def test_parse_skips_non_numeric_and_tolerates_garbage():
    # the file is data, never trusted to be perfectly formed -- skip bad keys/values, don't raise
    table = battle_bgm.parse('{"257": {"303": "35", "x": "9", "304": "bad"}, "name": {"1": "2"}}')
    assert table == {257: {303: 35}}


def test_parse_empty():
    assert battle_bgm.parse("{}") == {}


# ---- song(): the (field, scene) lookup ---------------------------------------------------------
def test_song_returns_donor_song():
    battle_bgm._CACHE = {257: {303: 35}}
    assert battle_bgm.song(257, 303) == 35


def test_song_zero_is_a_real_value_distinct_from_none():
    # 0 == the standard Battle Theme is a REAL mapping; only an ABSENT pair is None ("no special song")
    battle_bgm._CACHE = {250: {67: 0}}
    assert battle_bgm.song(250, 67) == 0
    assert battle_bgm.song(250, 999) is None        # scene not mapped under this field
    assert battle_bgm.song(999, 67) is None         # field not in the map (e.g. a custom-id fork)


def test_song_none_field_id():
    battle_bgm._CACHE = {257: {303: 35}}
    assert battle_bgm.song(None, 303) is None


def test_song_degrades_when_unreadable():
    # the install/asset couldn't be read -> the cache is the _MISS sentinel -> every lookup is None
    battle_bgm._CACHE = battle_bgm._MISS
    assert battle_bgm.song(257, 303) is None
    assert battle_bgm.available() is False


def test_parse_empty_string_yields_empty_map_not_raise():
    # parse() is public + promises "never trusted to be perfectly formed" -> an unparseable blob is {}, not a raise
    assert battle_bgm.parse("") == {}
    assert battle_bgm.parse("not json {{{") == {}


# ---- _load(): memoization + the _MISS sentinel (the pure cache contract) ------------------------
def test_load_reads_once_and_memoizes(monkeypatch):
    calls = {"n": 0}
    monkeypatch.setattr(battle_bgm, "_read", lambda game=None: (calls.__setitem__("n", calls["n"] + 1)
                                                                or {257: {303: 35}}))
    assert battle_bgm.song(257, 303) == 35
    assert battle_bgm.song(257, 303) == 35       # second lookup must NOT re-read the (multi-MB) asset
    assert calls["n"] == 1


def test_load_caches_miss_and_never_retries(monkeypatch):
    calls = {"n": 0}
    monkeypatch.setattr(battle_bgm, "_read", lambda game=None: (calls.__setitem__("n", calls["n"] + 1)
                                                                or None))   # install/asset unreachable
    assert battle_bgm.song(257, 303) is None
    assert battle_bgm.available() is False
    assert battle_bgm.song(1, 2) is None
    assert calls["n"] == 1                        # the _MISS sentinel prevents re-reading every lookup
    assert battle_bgm._CACHE is battle_bgm._MISS


# ---- extract wiring: import prefills [encounter] battle_music -----------------------------------
# ---- scan_battle_scenes: the SCRIPTED Battle(0x2A)/BattleEx(0x8C) scene decode ----------------
def test_scan_battle_scenes_empty_on_a_no_battle_field():
    # a town street has no scripted Battle op -> [] (it never raises on a real .eb)
    assert eventscan.scan_battle_scenes(ALEX100) == []


def test_scan_battle_scenes_finds_inserted_battle_op_masking_high_bit():
    # Battle(rush=1, btlId=0x814A): op 2A, arg-expr-flags 00, arg0=01 (1B), arg1=4A 81 (2B LE = 0x814A). The
    # scene is btlId & 0x7FFF == 330 (bit 15 = Steiner's state, masked off).
    eb = edit.insert_in_function(ALEX100, 0, 0, 0, bytes([0x2A, 0x00, 0x01, 0x4A, 0x81]))
    assert 330 in eventscan.scan_battle_scenes(eb)


# ---- the verbatim battle-bgm carry: pairs + block render ----------------------------------------
def test_donor_battle_bgm_pairs_keeps_nonzero_skips_zero_and_unknown(monkeypatch):
    monkeypatch.setattr(eventscan, "scan_battle_scenes", lambda eb: [330, 67, 999])
    songs = {(656, 330): 35, (656, 67): 0}      # 67 -> 0 (default), 999 -> None (unmapped)
    monkeypatch.setattr(battle_bgm, "song", lambda fid, sc, game=None: songs.get((fid, sc)))
    assert extract._donor_battle_bgm_pairs(b"\x00", 656, None) == [(330, 35)]
    assert extract._donor_battle_bgm_pairs(b"\x00", None, None) == []   # no donor id -> nothing


def test_render_battle_bgm_blocks():
    assert extract._render_battle_bgm_blocks([]) == ""
    txt = extract._render_battle_bgm_blocks([(330, 35), (294, 35)])
    assert "[[battle_bgm]]\nscene = 330\nsong = 35" in txt
    assert "[[battle_bgm]]\nscene = 294\nsong = 35" in txt


def test_donor_battle_song_helper(monkeypatch):
    monkeypatch.setattr(battle_bgm, "song",
                        lambda fid, scene, game=None: 35 if (fid, scene) == (257, 303) else None)
    assert extract._donor_battle_song(257, {"scenes": [303]}, None) == 35
    assert extract._donor_battle_song(257, {"scenes": [999]}, None) is None
    assert extract._donor_battle_song(None, {"scenes": [303]}, None) is None
    assert extract._donor_battle_song(257, None, None) is None


def _content(encounter):
    """A complete scan_content dict with everything empty except the encounter under test."""
    return {"gateways": [], "music": None, "encounter": encounter, "control_direction": None,
            "ladders": [], "jumps": [], "objects": [], "objects_verbatim": []}


def test_imported_content_prefills_battle_music(monkeypatch):
    monkeypatch.setattr(extract.eventscan, "scan_content",
                        lambda eb: _content({"scenes": [303], "freq": 48, "pattern": None}))
    monkeypatch.setattr(battle_bgm, "song",
                        lambda fid, scene, game=None: 35 if (fid, scene) == (257, 303) else None)
    blocks, _control, summary = extract._imported_content_toml(b"\x00", field_id=257, game=None)
    assert "[encounter]" in blocks and "scene = 303" in blocks
    assert "battle_music = 35" in blocks
    assert summary["battle_music"] == 35


def test_imported_content_omits_battle_music_when_default_or_unknown(monkeypatch):
    # song 0 (Battle Theme) == the build's default, and an unknown pair (None) both leave battle_music unset
    monkeypatch.setattr(extract.eventscan, "scan_content",
                        lambda eb: _content({"scenes": [67], "freq": 48, "pattern": None}))
    for ret in (0, None):
        monkeypatch.setattr(battle_bgm, "song", lambda fid, scene, game=None: ret)
        blocks, _control, summary = extract._imported_content_toml(b"\x00", field_id=250, game=None)
        assert "[encounter]" in blocks
        assert "battle_music" not in blocks
        assert summary["battle_music"] == ret
