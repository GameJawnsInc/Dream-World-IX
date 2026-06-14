"""Pure tests for [[battle_action]] / [[status]] CSV-delta authoring (synthetic cp1252 base CSVs, no install)."""
from __future__ import annotations

import pytest

from ff9mapkit.battle import actiondelta as AD

# SYNTHETIC base (values are NOT the real SE rows -- provenance-clean fixtures). The name column carries a
# real 0x92 curly apostrophe (Angel’s Snack) and a duplicated name (Aura @ 128 & 136) on purpose.
_ACTIONS = (
    "#! IncludeCastingTitleType\n"
    "# Comment;id;menuWindow;targets;defaultAlly;forDead;defaultOnDead;defaultCamera;animationId1;"
    "animationId2;scriptId;power;elements;rate;category;statusIndex;mp;type;commandTitle\n"
    "# ;Int32;UInt8;UInt8;Boolean;Boolean;Boolean;Boolean;Int16;UInt16;Int32;Int32;UInt8;Int32;UInt8;"
    "Int32;Int32;UInt8;UInt8\n"
    "Fire;25;None(0);ManyAny(3);0;0;0;0;111;222;9;77;1;0;19;0;6;0;255;# Fire\n"
    "Blizzard;29;None(0);ManyAny(3);0;0;0;0;112;223;9;77;2;0;19;0;6;0;255;# Blizzard\n"
    "Aura;128;Hp(1);SingleAny(0);1;0;0;0;90;0;103;0;0;255;71;0;12;0;255;# Aura\n"
    "Aura;136;Hp(1);ManyAny(3);1;0;0;0;91;0;103;0;0;255;71;0;24;0;255;# Aura\n"
    "Angel’s Snack;93;None(0);ManyAny(3);0;0;0;0;52;0;52;0;0;0;0;0;0;0;255;# Angel's Snack\n"
)
_STATUS = (
    "#! UnshiftStatuses\n#! IncludeVisuals\n"
    "# Comment;Id;Priority;OprCount;ContiCount;ClearOnApply;ImmunityProvided\n"
    "# ;Int32;UInt8;UInt8;UInt16;Status[];Status[]\n"
    "Poison;16;7;10;0;;\nSleep;17;13;0;0;;\n"
)


@pytest.fixture
def base(tmp_path, monkeypatch):
    (tmp_path / "Actions.csv").write_bytes(_ACTIONS.encode("cp1252"))      # cp1252 -> a real 0x92 apostrophe
    (tmp_path / "StatusData.csv").write_bytes(_STATUS.encode("cp1252"))
    monkeypatch.setattr(AD, "_csv_path", lambda name, game=None: tmp_path / name)
    return tmp_path


def _reparse(base, text):
    p = base / "delta.csv"
    p.write_bytes(text.encode("cp1252"))
    _o, _l, cols, rows = AD._read_raw(p)
    return cols, rows


def test_action_delta_changes_named_fields_only(base):
    text, warns = AD.build_actions_delta([{"action": "Fire", "power": 30, "element": ["Ice"], "mp": 4}])
    assert not warns
    assert "#! IncludeCastingTitleType" in text          # the load-bearing option line is preserved
    assert "Blizzard" not in text                        # only the changed row is emitted (partial delta)
    cols, rows = _reparse(base, text)
    fire = rows[25]
    assert fire[cols["power"]] == "30"
    assert fire[cols["elements"]] == "2"                 # Ice = bit 2
    assert fire[cols["mp"]] == "4"
    assert fire[cols["scriptid"]] == "9"                 # untouched column preserved from the base
    assert fire[cols["animationid1"]] == "111"           # untouched (synthetic value)


def test_apostrophe_name_resolves_and_byte_roundtrips(base):
    text, _w = AD.build_actions_delta([{"action": "Angel's Snack", "power": 5}])   # straight apostrophe matches
    assert "’" in text                               # the base's curly apostrophe is preserved in the row
    assert b"\x92" in text.encode("cp1252")               # ... and round-trips to the cp1252 byte (not U+FFFD)
    cols, rows = _reparse(base, text)
    assert rows[93][cols["power"]] == "5"


def test_ambiguous_name_raises(base):
    with pytest.raises(AD.ActionDeltaError, match="ambiguous"):
        AD.build_actions_delta([{"action": "Aura", "power": 1}])
    # the id form is unambiguous
    _t, _w = AD.build_actions_delta([{"action": 136, "mp": 99}])


def test_range_guard_rejects_out_of_byte_range(base):
    for bad in ({"action": "Fire", "category": 500}, {"action": "Fire", "type": 300},
                {"action": "Fire", "element": 9999}):
        with pytest.raises(AD.ActionDeltaError, match="range"):
            AD.build_actions_delta([bad])
    with pytest.raises(AD.ActionDeltaError, match="range"):
        AD.build_status_delta([{"status": "Poison", "tick": 300}])         # tick is Byte (0-255)
    # duration is UInt16, so 300 is fine; 99999 is not
    AD.build_status_delta([{"status": "Poison", "duration": 300}])
    with pytest.raises(AD.ActionDeltaError, match="range"):
        AD.build_status_delta([{"status": "Poison", "duration": 99999}])


def test_validate_catches_range_offline():
    assert AD.validate_entry({"action": "Fire", "category": 500}, kind="battle_action")  # no install needed
    assert AD.validate_entry({"status": "Poison", "tick": 999}, kind="status")
    assert AD.validate_entry({"action": "Fire", "power": 30}, kind="battle_action") == []


def test_install_not_found_wraps_to_actiondeltaerror(monkeypatch):
    def boom(name, game=None):
        raise RuntimeError("no FF9 install")             # config.ConfigError is a RuntimeError subclass
    monkeypatch.setattr(AD, "_csv_path", boom)
    with pytest.raises(AD.ActionDeltaError, match="needs your FF9 install"):
        AD.build_actions_delta([{"action": "Fire", "power": 1}])


def test_by_id_and_script_name(base):
    text, _w = AD.build_actions_delta([{"action": 29, "script": "PhysicalAttack"}])  # Blizzard -> scriptId 19
    cols, rows = _reparse(base, text)
    assert rows[29][cols["scriptid"]] == "19"


def test_unknown_name_and_field_raise(base):
    with pytest.raises(AD.ActionDeltaError):
        AD.build_actions_delta([{"action": "Nope", "power": 1}])
    with pytest.raises(AD.ActionDeltaError):
        AD.build_actions_delta([{"action": "Fire", "splash": 1}])


def test_non_stock_script_warns(base):
    _text, warns = AD.build_actions_delta([{"action": "Fire", "script": 64}])  # 64 = non-catalogued
    assert any("Memoria.Scripts" in w for w in warns)


def test_duplicate_entries_warn_and_merge(base):
    text, warns = AD.build_actions_delta([{"action": "Fire", "power": 5}, {"action": "Fire", "mp": 2}])
    assert any("both target" in w for w in warns)
    cols, rows = _reparse(base, text)
    assert rows[25][cols["power"]] == "5" and rows[25][cols["mp"]] == "2"   # both fields applied


def test_status_delta(base):
    text, _w = AD.build_status_delta([{"status": "Poison", "tick": 30, "duration": 5}])
    assert "#! UnshiftStatuses" in text and "#! IncludeVisuals" in text and "Sleep" not in text
    cols, rows = _reparse(base, text)
    assert rows[16][cols["oprcount"]] == "30" and rows[16][cols["conticount"]] == "5"


def test_write_battle_data_emits_both(base, tmp_path):
    from ff9mapkit.config import ModLayout
    layout = ModLayout(tmp_path / "mod")
    AD.write_battle_data(layout, actions=[{"action": "Fire", "power": 2}],
                         statuses=[{"status": "Sleep", "duration": 9}])
    assert layout.actions_csv.is_file() and layout.status_data_csv.is_file()
    assert "Fire" in layout.actions_csv.read_text(encoding="cp1252")


def test_validate_entry_structural():
    assert AD.validate_entry({"power": 5}, kind="battle_action")           # missing 'action'
    assert AD.validate_entry({"action": "Fire"}, kind="battle_action")     # no fields set
    assert AD.validate_entry({"action": "Fire", "nope": 1}, kind="battle_action")  # unknown field
    assert AD.validate_entry({"status": "Poison", "tick": 5}, kind="status") == []  # ok


# ---- niche player levers: targeting / presentation (Actions.csv) + status interaction (StatusData.csv) ----
def test_action_targeting_and_presentation_fields(base):
    text, _w = AD.build_actions_delta([{
        "action": "Fire", "targets": "AllEnemy", "menu_window": "Mp", "default_ally": True,
        "for_dead": False, "default_on_dead": 1, "camera": True, "vfx1": -5, "vfx2": 4321,
        "status_index": 70}])
    cols, rows = _reparse(base, text)
    fire = rows[25]
    assert fire[cols["targets"]] == "AllEnemy(8)" and fire[cols["menuwindow"]] == "Mp(2)"
    assert fire[cols["defaultally"]] == "1" and fire[cols["fordead"]] == "0"
    assert fire[cols["defaultondead"]] == "1" and fire[cols["defaultcamera"]] == "1"
    assert fire[cols["animationid1"]] == "-5" and fire[cols["animationid2"]] == "4321"
    assert fire[cols["statusindex"]] == "70"


def test_action_targets_by_id_and_unknown_name(base):
    _t, _w = AD.build_actions_delta([{"action": "Fire", "targets": 3}])
    cols, rows = _reparse(base, _t)
    assert rows[25][cols["targets"]] == "ManyAny(3)"
    with pytest.raises(AD.ActionDeltaError):
        AD.build_actions_delta([{"action": "Fire", "targets": "Nope"}])


def test_action_vfx1_is_signed_range_checked(base):
    AD.build_actions_delta([{"action": "Fire", "vfx1": -32768}])            # Int16 min, ok
    with pytest.raises(AD.ActionDeltaError):
        AD.build_actions_delta([{"action": "Fire", "vfx1": 40000}])         # > Int16 max


def test_status_clear_and_immunity_lists(base):
    text, _w = AD.build_status_delta([{
        "status": "Poison", "clear_on_apply": ["Defend", "Poison"], "immunity_provided": "Poison"}])
    cols, rows = _reparse(base, text)
    assert rows[16][cols["clearonapply"]] == "Defend(15), Poison(16)"      # the real base "Name(idx), ..." format
    assert rows[16][cols["immunityprovided"]] == "Poison(16)"


def test_status_clear_none_empties_the_cell(base):
    text, _w = AD.build_status_delta([{"status": "Poison", "clear_on_apply": "none"}])
    cols, rows = _reparse(base, text)
    assert rows[16][cols["clearonapply"]] == ""
    with pytest.raises(AD.ActionDeltaError):
        AD.build_status_delta([{"status": "Poison", "clear_on_apply": ["Nope"]}])
