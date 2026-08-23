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


# ---- the owner token: an int still renders as `field N`, and a battle can own a block too -------------
def test_int_owner_renders_byte_identical_to_the_historical_marker():
    # LOAD-BEARING: every live BattlePatch.txt on disk already carries blocks under THIS exact string, and
    # tools/deploy_field.py finds-and-replaces its own block by it. A changed marker orphans those blocks --
    # the next deploy appends a second one instead of replacing, and the old one patches forever. Pinned as
    # a literal, not built from the format string, so a "harmless" reword cannot pass.
    begin, end = BP._markers(4003)
    assert begin == "// >>> ff9mapkit field 4003 BattlePatch (auto -- edit the field.toml, not here)"
    assert end == "// <<< ff9mapkit field 4003"


def test_battle_owner_token_and_a_field_block_coexist_in_one_file():
    # A campaign ships fields AND battles into one folder, so both must be able to own a block in the same
    # BattlePatch.txt without either clobbering the other.
    live = BP.merge_battle_patch("", ["AnyEnemyByName: Goblin", "MaxHP 500"], 4003)
    live = BP.merge_battle_patch(live, ["Battle: 12000", "Music: 35"], BP.battle_owner("BBG_B013", 12000))
    assert "ff9mapkit field 4003" in live and "MaxHP 500" in live          # the field block survived
    assert "Battle: 12000" in live and "Music: 35" in live                 # the battle block landed
    # ...and re-merging the battle block replaces only its own
    again = BP.merge_battle_patch(live, ["Battle: 12000", "Music: 7"], BP.battle_owner("BBG_B013", 12000))
    assert "Music: 7" in again and "Music: 35" not in again
    assert "MaxHP 500" in again and again.count("ff9mapkit field 4003 ") == 1


def test_battle_owner_is_distinct_per_bbg_and_per_scene():
    # two battles in one campaign must not share an owner token, or the second strips the first
    a, b = BP.battle_owner("BBG_B013", 12000), BP.battle_owner("BBG_B014", 12000)
    assert a != b
    assert BP.battle_owner("BBG_B013", 12000) != BP.battle_owner("BBG_B013", 12001)
    live = BP.merge_battle_patch("", ["Battle: 12000", "Music: 1"], a)
    live = BP.merge_battle_patch(live, ["Battle: 12001", "Music: 2"], b)
    assert "Music: 1" in live and "Music: 2" in live


def test_battle_merge_is_idempotent():
    owner = BP.battle_owner("BBG_B013", 12000)
    block = ["Battle: 12000", "Music: 35"]
    once = BP.merge_battle_patch("", block, owner)
    assert BP.merge_battle_patch(once, block, owner) == once


# ---- revert_splice / has_block (the SURGICAL deploy-revert -- Lane B 2026-08) -------------------------
def test_revert_splice_preserves_a_coowner_block_added_since_the_backup():
    """THE defect this replaces: the generated revert was `shutil.copyfile(backup, live)`. Field 30500
    deploys (backup taken), battle 30510 splices its tuning in, field 30500 redeploys -- the prelude revert
    restored the snapshot and the battle's block silently vanished (no guard watches BattlePatch, and the
    loss only shows at the NEXT relaunch). The surgical revert touches only its own block."""
    backup = BP.merge_battle_patch("Music: 9\n", ["MaxHP 1"], 30500)      # our OLD block, at backup time
    live = BP.merge_battle_patch(backup, ["MaxHP 2"], 30500)              # the deploy replaced it...
    owner_b = BP.battle_owner("BBG_B013", 30510)
    live = BP.merge_battle_patch(live, ["Battle: 30510", "Music: 35"], owner_b)  # ...then a battle co-deployed
    out = BP.revert_splice(live, backup, 30500)
    assert "MaxHP 1" in out and "MaxHP 2" not in out                      # our pre-deploy block is back
    assert "Battle: 30510" in out and "Music: 35" in out                  # the co-owner SURVIVES
    assert "Music: 9" in out                                              # unmarked lines survive too


def test_revert_splice_with_no_backup_strips_only_our_block():
    live = BP.merge_battle_patch("", ["MaxHP 2"], 30500)
    live = BP.merge_battle_patch(live, ["Battle: 30510"], BP.battle_owner("BBG_B013", 30510))
    out = BP.revert_splice(live, "", 30500)                               # the file did not exist pre-deploy
    assert "MaxHP 2" not in out and "ff9mapkit field 30500" not in out
    # the old not-had branch UNLINKED the whole file here -- taking the foreign block with it
    assert "Battle: 30510" in out


def test_revert_splice_empty_result_signals_delete():
    live = BP.merge_battle_patch("", ["MaxHP 2"], 30500)                  # we are the only owner
    assert BP.revert_splice(live, "", 30500) == ""                        # "" -> the caller unlinks the file


def test_extract_block_reads_back_what_merge_wrote():
    block = ["AnyEnemyByName: Goblin", "MaxHP 500"]
    live = BP.merge_battle_patch("Battle: 40\n", block, 4003)
    assert BP.extract_block(live, 4003) == block
    assert BP.extract_block(live, 4004) == []                             # exact owner only
    assert BP.extract_block("", 4003) == []


def test_has_block_is_exact_never_substring():
    """The old deploy trigger was `\"ff9mapkit field 300\" in text` -- which also matches field 3000's
    marker, arming a spurious snapshot-restoring revert for a field that owned nothing. And a bare
    battle_owner token is a PREFIX of the same battle's with-scene token."""
    live = BP.merge_battle_patch("", ["MaxHP 1"], 3000)
    assert BP.has_block(live, 3000)
    assert not BP.has_block(live, 300)
    scoped = BP.merge_battle_patch("", ["Battle: 1"], BP.battle_owner("BBG_B013", 12000))
    assert BP.has_block(scoped, BP.battle_owner("BBG_B013", 12000))
    assert not BP.has_block(scoped, BP.battle_owner("BBG_B013"))


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


# ---- tools/deploy_battle.py's live splice ------------------------------------------------------------
# The script runs at MODULE scope (no installed twin like ff9mapkit.deploy.deploy_field), so its live
# splice cannot be exercised in-process. HONEST GAP: the merge itself is fenced above; these assert the
# script actually SPENDS it, so a regression to the blind append cannot land silently. Same source-text
# idiom test_deploy_campaign.py uses for its generated revert script. Behaviour is playtest-verified.
def _deploy_battle_src():
    from pathlib import Path
    p = Path(__file__).resolve().parents[2] / "tools" / "deploy_battle.py"
    if not p.is_file():
        import pytest
        pytest.skip("repo-only tools/ script not present (installed-package layout)")
    return p.read_text(encoding="utf-8")


def test_deploy_battle_splices_the_battlepatch_instead_of_appending():
    src = _deploy_battle_src()
    assert "merge_battle_patch" in src and "battle_owner" in src
    assert 'cur += info["battle_patch"]' not in src, \
        "the blind append is back -- deploying the same battle twice would duplicate its block"
    # the trigger must be the exact-marker helper: a bare battle_owner token is a PREFIX of the same
    # battle's with-scene token, so the substring test armed on a block this deploy does not own.
    assert "has_block" in src and "_bp_owner in _live_bp_text" not in src


def test_deploy_battle_revert_undoes_the_battlepatch_splice_surgically():
    """Lane B 2026-08: the revert must re-splice its OWN pre-deploy block into the file as it stands at
    revert time (revert_splice), never restore the whole snapshot -- that re-clobbered every block another
    deploy spliced in between. The old restore was ALSO broken outright: it looked for the backup under the
    generated script's BK (= bk_dir, the per-deploy overwrite dir) while the deploy wrote it to the backups
    ROOT, so the restore branch crashed on FileNotFoundError whenever it was actually needed."""
    src = _deploy_battle_src()
    assert "bp_revert_code" in src and "revert_splice" in src
    assert 'shutil.copyfile(BK/"BattlePatch.txt.preBATTLE' not in src, \
        "the wholesale (and wrong-dir) snapshot restore is back"
    assert "_bpl.exists(): _bpl.unlink()" in src, "no revert branch for a BattlePatch.txt this deploy created"
    assert "sys.path.insert" in src, "the generated revert imports ff9mapkit -- it needs the kit on sys.path"
