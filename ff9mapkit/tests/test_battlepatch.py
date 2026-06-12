"""Pure tests for the Phase-4 BattlePatch.txt emitter ([[battle_patch]] / [[battle_enemy]] / [[battle_attack]]).

No install needed: every value is either the author's name/id or a mask from the committed element/status
tables. Asserts the emitted lines match the EXACT engine grammar Memoria.DataPatchers parses (selector lines +
`FieldName value` lines, the field names being the real C# [PatchableField] names)."""
from __future__ import annotations

import pytest

from ff9mapkit.battle import battlepatch as BP


def _lines(scene=None, enemies=None, attacks=None):
    lines, warns = BP.build_lines(scene, enemies, attacks)
    return lines, warns


# ---- scene-scoped block: ordering + name<->bit encoding ----------------------------------------------
def test_scene_block_orders_flags_then_subblocks():
    lines, warns = _lines(scene=[{
        "scene": 30055, "back_attack": True, "runaway": False,
        "enemy": [{"index": 0, "max_hp": 5000, "weak": ["Fire"], "auto_status": ["Protect"]}],
        "attack": [{"index": 2, "power": 40, "element": ["Fire"], "status_set": 7}],
        "pattern": [{"index": 0, "ap": 12}],
    }])
    assert not warns
    # the Battle: selector opens the block; scene flags bind to it and MUST precede any narrower
    assert lines[0] == "Battle: 30055"
    assert lines.index("BackAttack True") < lines.index("Pattern: 0")
    assert lines.index("Runaway False") < lines.index("Enemy: 0")
    # patterns emit before enemies before attacks (each narrower reuses the scene-applicability)
    assert lines.index("Pattern: 0") < lines.index("Enemy: 0") < lines.index("Attack: 2")
    assert "AP 12" in lines
    # enemy fields use the real engine field names + integer masks (Fire=1, Protect=1<<23)
    assert "MaxHP 5000" in lines and "WeakElement 1" in lines and "AutoStatus 8388608" in lines
    # attack fields route to BTL_REF/AA_DATA by name
    assert "Power 40" in lines and "Elements 1" in lines and "AddStatusNo 7" in lines


def test_enemy_by_name_within_scene():
    lines, _w = _lines(scene=[{"scene": "BSC_TEST", "enemy": [{"name": "Goblin", "level": 12}]}])
    assert lines[0] == "Battle: BSC_TEST"
    assert "EnemyByName: Goblin" in lines and "Level 12" in lines


# ---- global by-name blocks (the campaign-wide WIN) ----------------------------------------------------
def test_global_enemy_and_attack_by_name():
    lines, _w = _lines(enemies=[{"name": "Goblin", "max_hp": 500, "weak": ["Ice"]}],
                       attacks=[{"name": "Goblin Punch", "power": 30}])
    assert "AnyEnemyByName: Goblin" in lines
    assert "MaxHP 500" in lines and "WeakElement 2" in lines              # Ice = bit 2
    assert "AnyAttackByName: Goblin Punch" in lines and "Power 30" in lines


def test_global_enemy_requires_name_not_index():
    with pytest.raises(BP.BattlePatchError, match="needs name"):
        _lines(enemies=[{"index": 0, "max_hp": 1}])


# ---- drop/steal items + rate arrays (the BP-only reward levers) ---------------------------------------
def test_drop_steal_items_and_rates():
    lines, _w = _lines(enemies=[{
        "name": "Mu", "drop": [232, 233, "none", "none"], "drop_rates": [256, 96, 32, 1],
        "steal": [1, 2, 7, 255], "steal_rates": [256, 64, 16, 1],
    }])
    assert "WinItems 232 233 255 255" in lines                            # "none" -> 255 (NoItem)
    assert "WinItemRates 256 96 32 1" in lines
    assert "StealItems 1 2 7 255" in lines and "StealItemRates 256 64 16 1" in lines


def test_drop_needs_exactly_four():
    with pytest.raises(BP.BattlePatchError, match="exactly 4"):
        _lines(enemies=[{"name": "X", "drop": [1, 2, 3]}])
    with pytest.raises(BP.BattlePatchError, match="exactly 4"):
        _lines(enemies=[{"name": "X", "drop_rates": [256, 96]}])


# ---- BP-only fields with no raw16 slot ----------------------------------------------------------------
def test_bp_only_fields():
    lines, _w = _lines(enemies=[{"name": "Boss", "bonus_element": ["Fire"], "max_damage_limit": 99999,
                                 "win_card_rate": 64}])
    assert "BonusElement 1" in lines and "MaxDamageLimit 99999" in lines and "WinCardRate 64" in lines


# ---- range guards (the narrow engine column types) ---------------------------------------------------
def test_range_guards():
    with pytest.raises(BP.BattlePatchError, match="range"):
        _lines(enemies=[{"name": "X", "level": 300}])                     # Level is Byte (0-255)
    with pytest.raises(BP.BattlePatchError, match="range"):
        _lines(enemies=[{"name": "X", "win_card_rate": 99999}])           # UInt16
    with pytest.raises(BP.BattlePatchError, match="range"):
        _lines(scene=[{"scene": 1, "pattern": [{"index": 0, "rate": 999}]}])  # pattern Rate is Byte
    # MaxHP is UInt32 -> 70000 is fine
    lines, _w = _lines(enemies=[{"name": "X", "max_hp": 70000}])
    assert "MaxHP 70000" in lines


def test_bool_must_be_bool():
    with pytest.raises(BP.BattlePatchError, match="true or false"):
        _lines(scene=[{"scene": 1, "back_attack": 1}])


# ---- script resolution + the non-stock warning -------------------------------------------------------
def test_attack_script_name_and_warning():
    lines, warns = _lines(attacks=[{"name": "Bite", "script": "EnemyPhysicalAttack"}])
    assert "ScriptId 8" in lines and not warns                            # EnemyPhysicalAttack = scriptId 8
    _l2, warns2 = _lines(attacks=[{"name": "Bite", "script": 64}])        # 64 = not in the externalized catalog
    assert any("Memoria.Scripts" in w for w in warns2)


# ---- selector + structural rules ----------------------------------------------------------------------
def test_scene_needs_scene_id():
    with pytest.raises(BP.BattlePatchError, match="needs scene"):
        _lines(scene=[{"back_attack": True}])


def test_scene_block_must_set_something():
    with pytest.raises(BP.BattlePatchError, match="sets nothing"):
        _lines(scene=[{"scene": 30055}])


def test_scoped_enemy_needs_exactly_one_selector():
    with pytest.raises(BP.BattlePatchError, match="exactly one"):
        _lines(scene=[{"scene": 1, "enemy": [{"index": 0, "name": "X", "level": 1}]}])
    with pytest.raises(BP.BattlePatchError, match="exactly one"):
        _lines(scene=[{"scene": 1, "enemy": [{"level": 1}]}])


def test_unknown_field_raises():
    with pytest.raises(BP.BattlePatchError, match="unknown field"):
        _lines(enemies=[{"name": "X", "splash_damage": 1}])


def test_empty_subblock_raises():
    with pytest.raises(BP.BattlePatchError, match="sets no fields"):
        _lines(scene=[{"scene": 1, "enemy": [{"index": 0}]}])


# ---- robustness: bad-shape input must raise BattlePatchError, never traceback (review #3/#4) ----------
def test_scene_selector_rejects_non_id():
    for bad in (1.5, [1, 2], 2 ** 40):                                    # float / list / over-Int32
        with pytest.raises(BP.BattlePatchError, match="scene"):
            _lines(scene=[{"scene": bad, "back_attack": True}])
    assert _lines(scene=[{"scene": 30055, "back_attack": True}])[0][0] == "Battle: 30055"
    assert _lines(scene=[{"scene": "BSC_X", "back_attack": True}])[0][0] == "Battle: BSC_X"


def test_non_table_block_raises_cleanly():
    for call in (lambda: _lines(enemies=[5]),                             # a scalar where a table is expected
                 lambda: _lines(attacks=["x"]),
                 lambda: _lines(scene=["scene-40"]),
                 lambda: _lines(scene=[{"scene": 1, "enemy": [5]}]),      # bad nested sub-block
                 lambda: _lines(enemies=5)):                              # a scalar where a list is expected
        with pytest.raises(BP.BattlePatchError):                          # NOT TypeError / AttributeError
            call()
    assert BP.validate_blocks(enemies=[5])                                # surfaced as a lint message, no crash


def test_status_set_capped_at_engine_max():
    lines, _w = _lines(attacks=[{"name": "X", "status_set": 38}])         # the highest defined StatusSetId
    assert "AddStatusNo 38" in lines
    with pytest.raises(BP.BattlePatchError, match="range"):
        _lines(attacks=[{"name": "X", "status_set": 39}])                 # undefined -> in-game KeyNotFound crash


# ---- validate_blocks (offline lint) ------------------------------------------------------------------
def test_validate_blocks():
    assert BP.validate_blocks(enemies=[{"name": "X", "level": 300}])      # range error surfaced
    assert BP.validate_blocks([{"scene": 1}])                             # no-op scene block
    assert BP.validate_blocks(enemies=[{"name": "X", "level": 12}]) == []  # ok


# ---- merge_battle_patch (non-clobbering deploy) ------------------------------------------------------
def test_merge_preserves_other_lines_and_replaces_own_block():
    live = "Battle: 40\nMusic: 9\n"                                        # a co-deployed BGM line (not ours)
    block = ["AnyEnemyByName: Goblin", "MaxHP 500"]
    merged = BP.merge_battle_patch(live, block, 4003)
    assert "Battle: 40" in merged and "Music: 9" in merged                # preserved
    assert "// >>> ff9mapkit field 4003" in merged and "AnyEnemyByName: Goblin" in merged
    # re-merging a DIFFERENT block for the same id replaces ours but keeps the BGM line (idempotent shape)
    merged2 = BP.merge_battle_patch(merged, ["AnyEnemyByName: Goblin", "MaxHP 999"], 4003)
    assert "MaxHP 999" in merged2 and "MaxHP 500" not in merged2
    assert merged2.count("// >>> ff9mapkit field 4003") == 1 and "Battle: 40" in merged2


def test_merge_empty_block_strips_prior():
    live = BP.merge_battle_patch("Battle: 40\nMusic: 9\n", ["AnyEnemyByName: Goblin", "MaxHP 1"], 4003)
    stripped = BP.merge_battle_patch(live, [], 4003)
    assert "ff9mapkit field 4003" not in stripped and "Battle: 40" in stripped


def test_merge_idempotent():
    block = ["AnyEnemyByName: Goblin", "MaxHP 1"]
    once = BP.merge_battle_patch("", block, 4003)
    twice = BP.merge_battle_patch(once, block, 4003)
    assert once == twice


# ---- build.py wiring (aggregation across fields + error wrapping) -------------------------------------
def test_build_emit_battle_patch_aggregates_and_wraps_errors():
    from types import SimpleNamespace
    from ff9mapkit import build
    p1 = SimpleNamespace(raw={"battle_enemy": [{"name": "Goblin", "max_hp": 500}]})
    p2 = SimpleNamespace(raw={"battle_patch": [{"scene": 30055, "back_attack": True}]})
    lines, _warns = build._emit_battle_patch([p1, p2])                    # mod-global: aggregates across fields
    assert "AnyEnemyByName: Goblin" in lines and "Battle: 30055" in lines and "BackAttack True" in lines
    assert build._emit_battle_patch([SimpleNamespace(raw={})]) == ([], [])   # no blocks -> no contribution
    with pytest.raises(build.BuildError):                                 # a bad block -> BuildError (not a crash)
        build._emit_battle_patch([SimpleNamespace(raw={"battle_enemy": [{"name": "X", "level": 999}]})])
