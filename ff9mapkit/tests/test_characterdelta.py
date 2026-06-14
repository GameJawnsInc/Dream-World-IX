"""Pure tests for [[character]] / [[leveling]] -- the Phase-5 player-side CSV deltas (synthetic CSVs, no install).

BaseStats = per-id PARTIAL delta; Leveling = WHOLE-FILE (all 99 rows re-emitted). Asserts the emitted CSVs
match the engine's column layout (BaseStats: Comment;Id;Dexterity;Strength;Magic;Will;Gems / Leveling:
Experience;BonusHP;BonusMP) and the merge model."""
from __future__ import annotations

import pytest

from ff9mapkit.battle import characterdelta as CD

# SYNTHETIC base -- deliberately-fake values that match NO real character (provenance: the repo ships ZERO SE
# stat bytes; the emitter reads the real values live from the install, never committed).
_BASESTATS = (
    "# This file contains base stats of characters.\n"
    "# Comment;Id;Dexterity;Strength;Magic;Will;Gems\n"
    "# ;Int32;UInt8;UInt8;UInt8;UInt8;UInt32\n"
    "Zidane;0;10;20;30;40;5\n"
    "Vivi;1;15;25;35;45;7\n"
)
# Leveling needs >= 99 data rows (the engine gate); generate them.
_LEVELING = (
    "# This file contains amount of experience to the next level and bonus for HP and MP.\n"
    "# Experience;BonusHP;BonusMP\n"
    "# UInt32;UInt16;UInt16\n"
    + "".join(f"{n * 100};{200 + n};{100 + n};# Level {n}\n" for n in range(1, 100))
)
# SYNTHETIC AbilityGems: deliberately-fake gem costs (77/88/66 -- real costs are single/low-double digits, so
# these match NO real ability) + the open-source ENUM names as the Comment (not the SE display strings). The
# Boosted column (4th) is empty here; the `#! IncludeBoosted` line is load-bearing (the engine parses Boosted
# only when it is present). Provenance: the repo ships ZERO SE values; the emitter reads real costs live.
_ABILITYGEMS = (
    "#! IncludeBoosted\n"
    "# Comment;Id;Gems;BoostedVersion(s)\n"
    "# ;Int32;Int32;Int32[]\n"
    "AutoReflect;0;77;\n"
    "AutoHaste;2;88;\n"
    "HP10;5;66;\n"
)


# SYNTHETIC CharacterParameters (8 cols, ALL Byte despite the legend "Int32;Boolean") + a comment cell.
_CHARPARAMS = (
    "# This file contains character parameters.\n"
    "# Id;DefaultRow;DefaultWinPose;DefaultCategory;DefaultMenuType;DefaultEquipmentSet;SerialNumberFormula;NameKeyword\n"
    "# Int32;Boolean;Byte;Byte;Byte;Byte;String;String\n"
    "0;0;0;1;0;0;1;ZIDANE;# Zidane\n"
    "1;0;1;5;1;1;2;VIVI;# Vivi\n"
)
# SYNTHETIC CommandSets (Id + 12 slots), TAB-PADDED like the real file (to prove the strip) + a colliding
# Attack(Trance) legend name (proves we index by fixed position, not the legend).
_COMMANDSETS = (
    "#! IncludeId\n#! IncludeFullSet\n"
    "# Id;Attack;Defend;Ability1;Ability2;Item;Change;Attack(Trance);Defend(Trance);Ability1(Trance);"
    "Ability2(Trance);Item(Trance);Change(Trance)\n"
    "0;1;2;3;4;5;6;1;2;3;4;5;6;# Zidane\n"
    "1\t;1\t;2\t;30\t;31\t;5\t;6\t;1\t;2\t;30\t;31\t;5\t;6\t;# Vivi\n"
)


# SYNTHETIC learn list (col0 = ability token, col1 = AP, + a comment cell) -- the real per-preset format.
_VIVI_LEARN = (
    "# This file contains a set of learnable Vivi's abilities.\n"
    "# Use 0 for a void ability, AA:X for active abilities and SA:X for passive abilities.\n"
    "# Id;AP\n"
    "# Ability;Int32\n"
    "AA:25;25;# Fire\n"
    "AA:26;30;# Fira\n"
    "SA:2;0;# Auto-Haste\n"
)


@pytest.fixture
def base(tmp_path, monkeypatch):
    (tmp_path / "BaseStats.csv").write_bytes(_BASESTATS.encode("cp1252"))
    (tmp_path / "Leveling.csv").write_bytes(_LEVELING.encode("cp1252"))
    (tmp_path / "CharacterParameters.csv").write_bytes(_CHARPARAMS.encode("cp1252"))
    (tmp_path / "CommandSets.csv").write_bytes(_COMMANDSETS.encode("cp1252"))
    (tmp_path / "Abilities").mkdir()
    (tmp_path / "Abilities" / "AbilityGems.csv").write_bytes(_ABILITYGEMS.encode("cp1252"))
    (tmp_path / "Abilities" / "Vivi.csv").write_bytes(_VIVI_LEARN.encode("cp1252"))
    monkeypatch.setattr(CD, "_csv_path", lambda name, game=None: tmp_path / name)
    return tmp_path


def _reparse(base, text, name="d.csv"):
    p = base / name
    p.write_bytes(text.encode("cp1252"))
    return CD._read_csv(p)


# ---- [[character]] -> BaseStats.csv (partial) --------------------------------------------------------
def test_character_partial_delta_changes_named_fields_only(base):
    text, warns = CD.build_basestats_delta([{"character": "Vivi", "strength": 99, "magic": 50}])
    assert not warns
    assert "Zidane" not in text                          # partial delta -> only the changed row
    assert "# Comment;Id;Dexterity;Strength;Magic;Will;Gems" in text   # the legend header is preserved
    header, cols, rows = _reparse(base, text)
    row = next(r for r in rows if r[cols["id"]] == "1")
    assert row[cols["strength"]] == "99" and row[cols["magic"]] == "50"
    assert row[cols["dexterity"]] == "15" and row[cols["will"]] == "45"   # untouched preserved (synthetic base)
    assert row[cols["comment"]] == "Vivi"


def test_character_by_id_and_aliases(base):
    text, _w = CD.build_basestats_delta([{"character": 0, "str": 40, "dex": 30}])   # id + aliases
    _h, cols, rows = _reparse(base, text)
    row = next(r for r in rows if r[cols["id"]] == "0")
    assert row[cols["strength"]] == "40" and row[cols["dexterity"]] == "30"


def test_character_range_guards(base):
    for bad in ({"character": "Vivi", "strength": 300}, {"character": "Vivi", "magic": 256}):
        with pytest.raises(CD.CharacterDeltaError, match="range"):
            CD.build_basestats_delta([bad])
    # gems is UInt32 -> 300000 ok, 5e9 not
    CD.build_basestats_delta([{"character": "Vivi", "gems": 300000}])
    with pytest.raises(CD.CharacterDeltaError, match="range"):
        CD.build_basestats_delta([{"character": "Vivi", "gems": 5_000_000_000}])


def test_character_unknown_name_and_field(base):
    with pytest.raises(CD.CharacterDeltaError, match="unknown character"):
        CD.build_basestats_delta([{"character": "Kuja", "strength": 1}])
    with pytest.raises(CD.CharacterDeltaError, match="unknown field"):
        CD.build_basestats_delta([{"character": "Vivi", "luck": 1}])
    with pytest.raises(CD.CharacterDeltaError, match="out of range"):
        CD.build_basestats_delta([{"character": 12, "strength": 1}])     # id 12 > 11


def test_character_duplicate_warns_and_merges(base):
    text, warns = CD.build_basestats_delta([{"character": "Vivi", "strength": 5},
                                            {"character": "Vivi", "magic": 7}])
    assert any("both target id 1" in w for w in warns)
    _h, cols, rows = _reparse(base, text)
    row = next(r for r in rows if r[cols["id"]] == "1")
    assert row[cols["strength"]] == "5" and row[cols["magic"]] == "7"


# ---- [[leveling]] -> Leveling.csv (WHOLE-FILE) -------------------------------------------------------
def test_leveling_emits_all_99_rows_and_patches_one(base):
    text, warns = CD.build_leveling_file([{"level": 5, "bonus_hp": 4000, "exp": 12345}])
    assert any("WHOLE-FILE" in w for w in warns)          # the shadow/whole-file hazard is surfaced
    _h, cols, rows = _reparse(base, text)
    assert len(rows) == 99                                # the COMPLETE curve is re-emitted
    assert rows[4][0] == "12345" and rows[4][1] == "4000"  # level 5 (index 4): exp + BonusHP patched
    assert rows[4][2] == "105"                            # BonusMP untouched (base 100+5)
    assert rows[0][1] == "201" and rows[98][1] == "299"   # other levels preserved
    assert rows[4][3] == "# Level 5"                      # the trailing comment cell is preserved


def test_leveling_range_guards(base):
    with pytest.raises(CD.CharacterDeltaError, match="range"):
        CD.build_leveling_file([{"level": 5, "bonus_hp": 99999}])        # UInt16
    CD.build_leveling_file([{"level": 5, "exp": 4_000_000_000}])         # UInt32 ok
    with pytest.raises(CD.CharacterDeltaError, match="range"):
        CD.build_leveling_file([{"level": 5, "exp": 5_000_000_000}])     # UInt32 overflow


def test_leveling_level_out_of_range(base):
    for bad in (0, 100, 200):
        with pytest.raises(CD.CharacterDeltaError, match="out of range"):
            CD.build_leveling_file([{"level": bad, "exp": 1}])


def test_leveling_no_fields_raises(base):
    with pytest.raises(CD.CharacterDeltaError, match="sets no fields"):
        CD.build_leveling_file([{"level": 5}])


def test_leveling_short_base_raises(base, tmp_path):
    (tmp_path / "Leveling.csv").write_bytes(b"# h\n0;1;1;# Level 1\n")   # only 1 row
    with pytest.raises(CD.CharacterDeltaError, match=">= 99"):
        CD.build_leveling_file([{"level": 1, "exp": 1}])


# ---- [[ability_gem]] -> AbilityGems.csv (partial, per-SupportAbility) --------------------------------
def test_ability_gem_partial_delta(base):
    text, warns = CD.build_ability_gems_delta([{"ability": "Auto-Haste", "gems": 4}])
    assert not warns
    assert "#! IncludeBoosted" in text                   # the load-bearing option line is preserved
    assert "Auto-Reflect" not in text                    # partial delta -> only the changed row
    _h, cols, rows = CD._read_csv(base / "Abilities" / "AbilityGems.csv")   # re-parse via the same reader
    # the emitted delta's Auto-Haste row (id 2) has gems = 4, Boosted col preserved (empty)
    p = base / "d.csv"; p.write_bytes(text.encode("cp1252"))
    _h2, c2, r2 = CD._read_csv(p)
    row = next(r for r in r2 if r[c2["id"]] == "2")
    assert row[c2["gems"]] == "4" and row[c2["comment"]] == "AutoHaste"


def test_ability_gem_name_forms_and_id(base):
    for form in ("Auto-Haste", "AutoHaste", "auto haste", 2):   # CSV display / enum name / spaced / id all -> 2
        text, _w = CD.build_ability_gems_delta([{"ability": form, "gems": 1}])
        p = base / "d.csv"; p.write_bytes(text.encode("cp1252"))
        _h, c, r = CD._read_csv(p)
        assert any(row[c["id"]] == "2" for row in r), form


def test_ability_gem_odins_sword_apostrophe():
    # id 60's CSV display name "Odin's Sword" (the only possessive) must resolve in every form the catalog prints
    for form in ("Odin's Sword", "Odin’s Sword", "OdinSword", "odin sword", 60, "60"):
        assert CD._resolve_sa_id(form) == 60, form


def test_ability_gem_errors(base):
    with pytest.raises(CD.CharacterDeltaError, match="unknown ability"):
        CD.build_ability_gems_delta([{"ability": "Megaflare", "gems": 1}])
    with pytest.raises(CD.CharacterDeltaError, match="unknown field"):
        CD.build_ability_gems_delta([{"ability": "HP10", "cost": 1}])
    with pytest.raises(CD.CharacterDeltaError, match="sets no fields"):
        CD.build_ability_gems_delta([{"ability": "HP10"}])
    with pytest.raises(CD.CharacterDeltaError, match="out of range"):
        CD.build_ability_gems_delta([{"ability": 99, "gems": 1}])      # id 99 > 63
    with pytest.raises(CD.CharacterDeltaError):                         # non-dict element
        CD.build_ability_gems_delta([5])


def test_ability_gem_validate_offline():
    assert CD.validate_ability_gem({"ability": "Megaflare", "gems": 1})      # unknown name
    assert CD.validate_ability_gem({"gems": 1})                              # missing ability
    assert CD.validate_ability_gem({"ability": "HP10"})                      # no fields
    assert CD.validate_ability_gem({"ability": [1], "gems": 1})              # non-int/str ability
    assert CD.validate_ability_gem({"ability": "Auto-Haste", "gems": 4}) == []


# ---- offline validation + write + install-missing ---------------------------------------------------
def test_validate_offline():
    assert CD.validate_character({"character": "Vivi", "strength": 300})   # range, no install
    assert CD.validate_character({"strength": 1})                          # missing character
    assert CD.validate_character({"character": "Vivi"})                    # no stats
    assert CD.validate_character({"character": "Nope", "strength": 1})     # unknown name
    assert CD.validate_character({"character": [1, 2], "strength": 3})     # non-int/str character flagged
    assert CD.validate_character({"character": "Vivi", "strength": 30}) == []
    assert CD.validate_leveling({"level": 0, "exp": 1})                    # level range
    assert CD.validate_leveling({"level": 5, "bonus_hp": 99999})           # field range
    assert CD.validate_leveling({"level": 5})                              # no fields
    assert CD.validate_leveling({"level": 5, "bonus_hp": 4000}) == []


def test_write_character_data_emits_all_three(base, tmp_path):
    from ff9mapkit.config import ModLayout
    layout = ModLayout(tmp_path / "mod")
    CD.write_character_data(layout, characters=[{"character": "Vivi", "strength": 2}],
                            levelings=[{"level": 10, "bonus_mp": 999}],
                            ability_gems=[{"ability": "HP10", "gems": 1}])
    assert layout.base_stats_csv.is_file() and layout.leveling_csv.is_file() and layout.ability_gems_csv.is_file()
    assert "Vivi" in layout.base_stats_csv.read_text(encoding="cp1252")
    _h, _c, rows = CD._read_csv(layout.leveling_csv)
    assert len(rows) == 99 and rows[9][2] == "999"        # whole 99-row file written, level 10 patched
    _h2, c2, r2 = CD._read_csv(layout.ability_gems_csv)
    assert any(row[c2["id"]] == "5" and row[c2["gems"]] == "1" for row in r2)   # HP10 (id 5) re-costed


def test_install_not_found_wraps(monkeypatch):
    def boom(name, game=None):
        raise RuntimeError("no FF9 install")
    monkeypatch.setattr(CD, "_csv_path", boom)
    with pytest.raises(CD.CharacterDeltaError, match="needs your FF9 install"):
        CD.build_basestats_delta([{"character": "Vivi", "strength": 1}])
    with pytest.raises(CD.CharacterDeltaError, match="needs your FF9 install"):
        CD.build_leveling_file([{"level": 1, "exp": 1}])


def test_non_table_block_raises_cleanly(base):
    for call in (lambda: CD.build_basestats_delta([5]),         # a scalar where a table is expected
                 lambda: CD.build_basestats_delta("x"),         # not a list
                 lambda: CD.build_leveling_file([5]),
                 lambda: CD.build_leveling_file({"level": 1})):  # a dict, not a list
        with pytest.raises(CD.CharacterDeltaError):             # NOT TypeError / AttributeError
            call()


def test_build_emit_character_data_wiring():
    from types import SimpleNamespace
    from ff9mapkit import build
    # no blocks -> no contribution; a bad block -> BuildError (not a raw crash). (Uses no install: validation
    # of the wiring path only; the SimpleNamespace carries the raw dict like a FieldProject.)
    assert build._emit_character_data([SimpleNamespace(raw={})], layout=None) == []


# ---- [[character_param]] -> CharacterParameters.csv (partial, FIXED-INDEX cols) ----
def test_character_param_partial_fixed_index(base):
    text, _w = CD.build_character_params_delta(
        [{"character": "Vivi", "row": 1, "menu_type": "Steiner", "category": 18}])
    _h, _c, rows = _reparse(base, text)
    vivi = next(r for r in rows if r[0] == "1")
    assert vivi[1] == "1" and vivi[3] == "18" and vivi[4] == "3"        # row / category / menu_type(Steiner=3)
    assert vivi[2] == "1" and vivi[7] == "VIVI"                         # untouched cols verbatim
    assert not any(r[0] == "0" for r in rows)                          # Zidane not emitted (partial)


def test_character_param_string_and_range(base):
    text, _w = CD.build_character_params_delta([{"character": "Vivi", "serial_formula": "1 + 2"}])
    assert next(r for r in _reparse(base, text)[2] if r[0] == "1")[6] == "1 + 2"   # String passthrough
    with pytest.raises(CD.CharacterDeltaError):
        CD.build_character_params_delta([{"character": "Vivi", "serial_formula": "a;b"}])    # ';' illegal in a String
    with pytest.raises(CD.CharacterDeltaError):
        CD.build_character_params_delta([{"character": "Vivi", "row": 256}])                 # Byte over-range
    assert CD.validate_character_param({"character": "Vivi", "row": 256})                    # over-range -> a problem


# ---- [[command_set]] -> CommandSets.csv (partial, tab-stripped, fixed-index slots) ----
def test_command_set_repoints_slots_strips_tabs(base):
    text, _w = CD.build_command_set_delta([{"preset": "Vivi", "ability1": 8, "ability2": 30}])
    _h, _c, rows = _reparse(base, text)
    vivi = next(r for r in rows if r[0] == "1")
    assert "\t" not in text                                            # tab-padding stripped on emit
    assert vivi[3] == "8" and vivi[4] == "30"                          # ability1 / ability2 by FIXED index
    assert vivi[1] == "1"                                              # attack slot untouched


def test_command_set_range_preset_and_validate(base):
    with pytest.raises(CD.CharacterDeltaError):
        CD.build_command_set_delta([{"preset": "Vivi", "ability1": 50}])      # > 47
    with pytest.raises(CD.CharacterDeltaError):
        CD.build_command_set_delta([{"preset": "Cinna", "attack": 1}])        # ambiguous preset
    assert CD.validate_command_set({"preset": "Vivi", "ability1": 8}) == []
    assert any("ambiguous" in p for p in CD.validate_command_set({"preset": "Marcus", "attack": 1}))


# ---- [[learn]] -> Abilities/<Preset>.csv (WHOLE-FILE per preset) ----
def test_learn_override_append_remove(base):
    text, warns = CD.build_learn_file(
        "Vivi",
        [{"ability": "AA:25", "ap": 99},                       # override an existing token's AP
         {"ability": "Auto-Haste"},                            # an SA NAME -> SA:2 (exists) -> AP 0 default
         {"ability": "SA:36", "ap": 50, "name": "Counter"}],   # a NEW token -> append
        ["AA:26"], game=None)                                  # remove Fira
    assert any("WHOLE-FILE" in w for w in warns)
    _h, _c, rows = _reparse(base, text)
    by_tok = {r[0]: r for r in rows}
    assert by_tok["AA:25"][1] == "99" and by_tok["AA:25"][2] == "# Fire"    # AP overridden, comment kept
    assert "AA:26" not in by_tok                                            # removed
    assert by_tok["SA:2"][1] == "0"                                         # Auto-Haste -> SA:2
    assert by_tok["SA:36"][1] == "50" and by_tok["SA:36"][2] == "# Counter"  # appended new w/ name comment


def test_learn_token_forms_and_ranges(base):
    assert CD._resolve_learn_token("0") == "0" and CD._resolve_learn_token("AA:25") == "AA:25"
    assert CD._resolve_learn_token("Auto-Haste") == "SA:2"                  # SA name (committed table)
    with pytest.raises(CD.CharacterDeltaError):
        CD._resolve_learn_token("AA:999")                                  # AA out of range
    with pytest.raises(CD.CharacterDeltaError):
        CD.build_learn_file("Vivi", [{"ability": "AA:25", "ap": -1}], [], game=None)   # AP < 0


def test_learn_preset_ambiguous_and_validate(base):
    with pytest.raises(CD.CharacterDeltaError):
        CD._group_learns([{"preset": "Cinna", "ability": []}])             # ambiguous guest preset
    assert CD.validate_learn({"preset": "Vivi", "ability": [{"ability": "AA:25", "ap": 5}]}) == []
    assert any("ambiguous" in p for p in CD.validate_learn({"preset": "Marcus"}))
