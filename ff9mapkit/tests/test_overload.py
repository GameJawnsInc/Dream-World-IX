"""The Overload hub + the declarative [difficulty] / [rebalance] features (project-ff9-overload-hooks).

Engine fact under test: Memoria registers IOverload* implementations ONE per interface per DLL (last-wins,
type order unspecified), so the kit emits exactly one hub class and composes features as plain statics.
Offline tests pin the hub's transcribed engine defaults (moved verbatim from the in-game-proven telemetry
source), the splice order (mutators before observers), the collision gate, the shared flag gate, the
[difficulty] + [rebalance] parse/render, and the build/deploy wiring (compile mocked). A csc+install-gated
test proves the whole tree (hub + telemetry + difficulty + rebalance) compiles against the LIVE engine.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from ff9mapkit.battle import deathrules, difficulty, lowhp, overload, rebalance, telemetry
from ff9mapkit.battle.scriptcompile import ScriptCompileError
from ff9mapkit.config import ModLayout


def _feat(name):
    return next(f for f in overload.FEATURES if f["name"] == name)


def _mock_compiles(monkeypatch):
    calls = []
    def fake(srcs, out_dll, *, game=None):
        calls.append(([str(s) for s in srcs], str(out_dll)))
        Path(out_dll).parent.mkdir(parents=True, exist_ok=True)
        Path(out_dll).write_bytes(b"MZ fake dll")
    monkeypatch.setattr(overload, "compile_sources", fake)
    return calls


# ---- hub rendering -------------------------------------------------------------------------------------
def test_hub_telemetry_only_pins_defaults():
    """Telemetry claims 4 hooks; the hub must implement the 4 interfaces and carry every displaced engine
    default VERBATIM (else installing telemetry would change gameplay): backstab/kill-frozen (Start),
    reflect multiplier (FinalChanges), x1.5 stack + Attack=1 (the DamageModifier pair)."""
    src = overload.render_hub([_feat("telemetry")])
    for interf in ("IOverloadOnBattleInitScript", "IOverloadOnBattleScriptStartScript",
                   "IOverloadOnBattleScriptEndScript", "IOverloadDamageModifierScript"):
        assert interf in src
    assert "TryKillFrozen()" in src
    assert "BonusBackstabAndPenaltyLongDistanceVisually()" in src
    assert "GetReflectMultiplierOnTarget" in src
    assert "v.Context.Attack = v.Context.Attack * 3 >> 1;" in src
    assert "v.Context.Attack = 1;" in src
    # the spliced feature calls, each guarded
    assert "try { Memoria.Scripts.Telemetry.BattleTelemetry.LogCalc(v); } catch { }" in src
    assert src.count("{") == src.count("}")
    # the calc log runs BEFORE the default's early returns (a miss must still produce a `calc` event)
    assert src.index("LogCalc(v)") < src.index("TryKillFrozen")
    # the result log runs AFTER the verbatim reflect default (observers read the post-reflect number)
    assert src.index("GetReflectMultiplierOnTarget") < src.index("LogResult(v)")


def test_hub_difficulty_only_claims_one_interface():
    src = overload.render_hub([_feat("difficulty")])
    assert "IOverloadOnBattleInitScript" in src
    for interf in ("IOverloadOnBattleScriptStartScript", "IOverloadOnBattleScriptEndScript",
                   "IOverloadDamageModifierScript"):
        assert interf not in src                          # unclaimed -> the engine inline defaults run untouched
    assert "DifficultyOverload.OnBattleInit();" in src
    assert src.count("{") == src.count("}")


def test_hub_composes_mutators_before_observers():
    """[difficulty] scales enemies BEFORE telemetry logs the roster -- the logged stats are the fought ones."""
    src = overload.render_hub([_feat("telemetry"), _feat("difficulty")])   # any input order
    assert src.index("DifficultyOverload.OnBattleInit()") < src.index("BattleTelemetry.LogBattleInit()")


def test_hub_none_when_no_features(tmp_path):
    assert overload.render_hub([]) is None
    layout = ModLayout(root=tmp_path / "FF9CustomMap")
    overload.hub_cs(layout).parent.mkdir(parents=True)
    overload.hub_cs(layout).write_text("// stale hub", encoding="utf-8")
    assert overload.write_hub(layout) == []
    assert not overload.hub_cs(layout).parent.exists()    # a feature-less mod carries NO hub dir


def test_write_hub_rerenders_live_owned_feature(tmp_path):
    """A live telemetry .cs left by an OLDER kit (it used to implement the interfaces itself) is refreshed to
    the current static-class source on every compile -- the upgrade path past the collision gate."""
    layout = ModLayout(root=tmp_path / "FF9CustomMap")
    cs = overload.feature_cs(layout, _feat("telemetry"))
    cs.parent.mkdir(parents=True)
    cs.write_text("// OLD KIT: public sealed class BattleTelemetry : IOverloadOnBattleInitScript {}",
                  encoding="utf-8")
    overload.write_hub(layout)
    fresh = cs.read_text(encoding="utf-8")
    assert "public static class BattleTelemetry" in fresh
    assert "IOverload" not in fresh
    assert overload.hub_cs(layout).is_file()


# ---- the collision gate ---------------------------------------------------------------------------------
def test_collision_gate(tmp_path):
    hub = tmp_path / overload.HUB_BASENAME
    hub.write_text("class OverloadHub : IOverloadOnBattleInitScript { }", encoding="utf-8")
    foreign = tmp_path / "9999_Custom.cs"
    # implements an interface the hub also implements -> refuse with names
    foreign.write_text("class Mine : IOverloadOnBattleInitScript { }", encoding="utf-8")
    with pytest.raises(ScriptCompileError, match="9999_Custom.cs"):
        overload.check_interface_collisions([hub, foreign], hub)
    # an interface the hub does NOT implement -> allowed (additive hand-written hook)
    foreign.write_text("class Mine : IOverloadOnGameOverScript { }", encoding="utf-8")
    overload.check_interface_collisions([hub, foreign], hub)
    # two foreign sources on the SAME interface -> refuse even without the hub in play
    other = tmp_path / "9998_Other.cs"
    other.write_text("class Yours : IOverloadOnGameOverScript { }", encoding="utf-8")
    with pytest.raises(ScriptCompileError, match="more than one source"):
        overload.check_interface_collisions([hub, foreign, other], hub)
    # a COMMENT mention never trips the gate
    foreign.write_text("// talks about IOverloadOnBattleInitScript only in a comment\nclass Mine { }",
                       encoding="utf-8")
    overload.check_interface_collisions([hub, foreign], hub)


# ---- compile_tree / compile_live --------------------------------------------------------------------------
def test_compile_tree_empty_deletes_dll(tmp_path, monkeypatch):
    _mock_compiles(monkeypatch)
    layout = ModLayout(root=tmp_path / "FF9CustomMap")
    dll = layout.scripts_dll("FF9CustomMap")
    dll.parent.mkdir(parents=True)
    dll.write_bytes(b"stale")
    from ff9mapkit.battle.scriptcompile import _stamp_path
    _stamp_path(dll).write_text("{}", encoding="utf-8")
    assert overload.compile_tree(layout, "FF9CustomMap") is None
    assert not dll.exists() and not _stamp_path(dll).exists()


def test_compile_tree_regenerates_hub_and_compiles_all(tmp_path, monkeypatch):
    calls = _mock_compiles(monkeypatch)
    mod = tmp_path / "FF9CustomMap"
    layout = ModLayout(root=mod)
    layout.scripts_sources_dir.mkdir(parents=True)                       # Sources/Battle
    (layout.scripts_sources_dir / "0256_XScript.cs").write_text("// formula", encoding="utf-8")
    difficulty.write_source(layout, difficulty.DifficultySpec(hp=2.0))
    out = overload.compile_tree(layout, "FF9CustomMap")
    assert out == layout.scripts_dll("FF9CustomMap")
    srcs, _ = calls[-1]
    assert any("0256_XScript.cs" in s for s in srcs)
    assert any(difficulty.DIFFICULTY_BASENAME in s for s in srcs)
    assert any(overload.HUB_BASENAME in s for s in srcs)
    hub = overload.hub_cs(layout).read_text(encoding="utf-8")
    assert "DifficultyOverload.OnBattleInit();" in hub and "BattleTelemetry" not in hub


def test_build_owned_dirs():
    """Deploy replaces exactly these; the live-owned Telemetry dir must NOT be in the list."""
    dirs = overload.build_owned_dirs()
    assert "Battle" in dirs and "Difficulty" in dirs and overload.HUB_DIRNAME in dirs
    assert "Telemetry" not in dirs


# ---- [difficulty] parse ----------------------------------------------------------------------------------
def test_parse_scales_and_flag_name():
    spec = difficulty.parse_table({"enemy_hp": 1.5, "enemy_attack": 1.25, "flag": "Hard_Mode"},
                                  name_map={"hard_mode": 8600})   # resolve() is case/spacing-insensitive
    assert spec.hp == 1.5 and spec.attack == 1.25 and spec.magic == 1.0
    assert spec.flag == 8600 and spec.flag_label == "Hard_Mode"


def test_parse_rejects():
    with pytest.raises(difficulty.DifficultyError, match="unknown key"):
        difficulty.parse_table({"enemy_hp": 1.5, "player_hp": 2.0})
    with pytest.raises(difficulty.DifficultyError, match="must be a number"):
        difficulty.parse_table({"enemy_hp": True})
    with pytest.raises(difficulty.DifficultyError, match="out of range"):
        difficulty.parse_table({"enemy_hp": 50.0})
    with pytest.raises(difficulty.DifficultyError, match="does nothing"):
        difficulty.parse_table({"enemy_hp": 1.0})
    with pytest.raises(difficulty.DifficultyError, match="unknown flag name"):
        difficulty.parse_table({"enemy_hp": 1.5, "flag": "nope"})
    with pytest.raises(difficulty.DifficultyError, match="out of range"):
        difficulty.parse_table({"enemy_hp": 1.5, "flag": 99999})


def test_collect_dedupes_and_conflicts():
    a = SimpleNamespace(raw={"difficulty": {"enemy_hp": 1.5}})
    b = SimpleNamespace(raw={"difficulty": {"enemy_hp": 1.5}})
    c = SimpleNamespace(raw={"difficulty": {"enemy_hp": 3.0}})
    plain = SimpleNamespace(raw={})
    assert difficulty.collect([plain]) is None
    spec, carrier = difficulty.collect([plain, a, b])     # identical twins are a campaign convenience
    assert spec.hp == 1.5 and carrier is a
    with pytest.raises(difficulty.DifficultyError, match="DIFFERENT settings"):
        difficulty.collect([a, c])


# ---- [difficulty] render ----------------------------------------------------------------------------------
def test_render_gate_math_and_clamps():
    src = difficulty.render(difficulty.DifficultySpec(hp=1.5, attack=1.25, flag=8600, flag_label="hard_mode"))
    assert f"g[{8600 >> 3}] & {1 << (8600 & 7)}" in src   # bit 8600 -> byte 1075, mask 1
    assert "if (u.IsPlayer)" in src                       # enemies only
    assert "Math.Min(9999999.0" in src                    # HP cap
    assert "(Byte)Math.Min(255.0" in src                  # Byte stat cap
    assert "u.Magic" not in src                           # magic left at 1.0 -> not emitted
    assert "hard_mode" in src                             # the author's flag spelling survives into the comment
    assert src.count("{") == src.count("}")
    assert "IOverload" not in src                         # a plain static feature class (the hub owns interfaces)


def test_render_ungated_is_always_on():
    src = difficulty.render(difficulty.DifficultySpec(magic=2.0))
    assert "gEventGlobal" not in src and "Always on" in src
    assert "u.Magic" in src and "u.Strength" not in src and "maxHp" not in src


def test_write_source_lifecycle(tmp_path):
    layout = ModLayout(root=tmp_path / "FF9CustomMap")
    cs = difficulty.write_source(layout, difficulty.DifficultySpec(hp=2.0))
    assert cs.is_file()
    assert difficulty.write_source(layout, None) is None  # de-difficultied rebuild removes the stale scaler
    assert not difficulty.difficulty_dir(layout).exists()


# ---- build + validate wiring -------------------------------------------------------------------------------
BASE = """
[field]
id = 4003
name = "DIFFROOM"
area = 11
text_block = 1073

[camera]
pitch = 45

[walkmesh]
quad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]

[player]
spawn = [0, -300]
"""


def test_validate_reports_bad_difficulty(tmp_path):
    from ff9mapkit.build import FieldProject, validate
    p = tmp_path / "f.field.toml"
    p.write_text(BASE + "\n[difficulty]\nenemy_hp = 99.0\n", encoding="utf-8")
    assert any("out of range" in x for x in validate(FieldProject.load(p)))
    p.write_text(BASE + '\n[difficulty]\nenemy_hp = 1.5\nflag = "hard_mode"\n'
                 '\n[[flag]]\nname = "hard_mode"\nindex = 8600\n', encoding="utf-8")
    assert validate(FieldProject.load(p)) == []           # named flag resolves through the [[flag]] registry


def test_lint_gate_fires_for_difficulty(tmp_path, monkeypatch):
    from ff9mapkit.battle import scriptcompile
    from ff9mapkit.build import FieldProject, lint_all
    p = tmp_path / "f.field.toml"
    p.write_text(BASE + "\n[difficulty]\nenemy_hp = 1.5\n", encoding="utf-8")
    proj = FieldProject.load(p)
    monkeypatch.setattr(scriptcompile, "toolchain_available", lambda: False)
    rep = lint_all(proj)
    assert any("C# compiler" in e and "difficulty" in e for e in rep.errors), rep.errors
    monkeypatch.setattr(scriptcompile, "toolchain_available", lambda: True)
    assert not any("C# compiler" in e for e in lint_all(proj).errors)


def test_emit_scripts_difficulty_only(tmp_path, monkeypatch):
    """[difficulty] with NO scripted abilities still builds the DLL (hub + scaler), and a de-difficultied
    rebuild drops the whole Scripts tree. Compile mocked (offline)."""
    calls = _mock_compiles(monkeypatch)
    from ff9mapkit.build import _emit_scripts
    layout = ModLayout(root=tmp_path / "mod")
    proj = SimpleNamespace(raw={"difficulty": {"enemy_hp": 1.5}})
    warnings = _emit_scripts([proj], layout, "FF9CustomMap")
    assert any("difficulty" in w for w in warnings)
    srcs, out = calls[-1]
    assert any(difficulty.DIFFICULTY_BASENAME in s for s in srcs) and any(overload.HUB_BASENAME in s for s in srcs)
    assert out.endswith("Memoria.Scripts.FF9CustomMap.dll")
    # de-difficultied rebuild: the Scripts tree (stale DLL included) is dropped
    assert _emit_scripts([SimpleNamespace(raw={})], layout, "FF9CustomMap") == []
    assert not layout.scripts_dir.exists()


# ---- the shared flag gate ---------------------------------------------------------------------------------
def test_flag_gate_shared_helper():
    """difficulty + rebalance emit an IDENTICAL gEventGlobal-bit gate -- the codegen lives once in overload."""
    assert overload.flag_gate_cs(None) == ""             # None -> always-on, no gate
    g = overload.flag_gate_cs(8600, label="hard_mode")
    assert "g[1075] & 1" in g and "(hard_mode)" in g and g.endswith("return;\n")
    # a numeric label (== the index) is not parenthesized twice
    assert "(8600)" not in overload.flag_gate_cs(8600, label="8600")
    # the two features' rendered gates match byte-for-byte
    d = difficulty.render(difficulty.DifficultySpec(hp=2.0, flag=8600, flag_label="hard_mode"))
    r = rebalance.render(rebalance.RebalanceSpec(player=2.0, flag=8600, flag_label="hard_mode"))
    assert g in d and g in r


# ---- [rebalance] parse ------------------------------------------------------------------------------------
def test_rebalance_parse_and_rejects():
    spec = rebalance.parse_table({"player_damage": 1.5, "enemy_damage": 0.75, "flag": "Hard_Mode"},
                                 name_map={"hard_mode": 8600})
    assert spec.player == 1.5 and spec.enemy == 0.75 and spec.flag == 8600
    with pytest.raises(rebalance.RebalanceError, match="unknown key"):
        rebalance.parse_table({"player_damage": 1.5, "enemy_hp": 2.0})   # a difficulty key here is unknown
    with pytest.raises(rebalance.RebalanceError, match="out of range"):
        rebalance.parse_table({"player_damage": 99.0})
    with pytest.raises(rebalance.RebalanceError, match="does nothing"):
        rebalance.parse_table({"player_damage": 1.0, "enemy_damage": 1.0})
    with pytest.raises(rebalance.RebalanceError, match="must be a number"):
        rebalance.parse_table({"enemy_damage": True})
    with pytest.raises(rebalance.RebalanceError, match="unknown flag name"):
        rebalance.parse_table({"player_damage": 1.5, "flag": "nope"})


def test_rebalance_collect_dedupes_and_conflicts():
    a = SimpleNamespace(raw={"rebalance": {"player_damage": 1.5}})
    b = SimpleNamespace(raw={"rebalance": {"player_damage": 1.5}})
    c = SimpleNamespace(raw={"rebalance": {"player_damage": 2.0}})
    assert rebalance.collect([SimpleNamespace(raw={})]) is None
    spec, carrier = rebalance.collect([a, b])
    assert spec.player == 1.5 and carrier is a
    with pytest.raises(rebalance.RebalanceError, match="DIFFERENT settings"):
        rebalance.collect([a, c])


# ---- [rebalance] render -----------------------------------------------------------------------------------
def test_rebalance_render_direction_and_guards():
    src = rebalance.render(rebalance.RebalanceSpec(player=1.5, enemy=0.75))
    # direction chosen by the caster; both scales baked in
    assert "v.Caster.IsPlayer ? 1.5 : 0.75" in src
    # only pure HP damage -- heal/recover skipped
    assert "CalcFlag.HpAlteration) == 0" in src and "CalcFlag.HpRecovery) != 0" in src
    assert "v.Target.HpDamage = (Int32)scaled;" in src
    assert "scaled > 9999999.0" in src               # overflow clamp
    assert "BreakDamageLimit" in src                 # the 9999-cap caveat is documented in-source
    assert "IOverload" not in src                    # a plain static feature class (the hub owns interfaces)
    assert src.count("{") == src.count("}")
    # a 1.0 scale is elided from the summary but the C# still guards scale==1.0 at runtime
    solo = rebalance.render(rebalance.RebalanceSpec(enemy=2.0))
    assert "enemy x2" in solo and "player x" not in solo
    assert "v.Caster.IsPlayer ? 1 : 2" in solo       # player stays 1.0 -> the runtime scale==1.0 guard no-ops it


def test_rebalance_write_source_lifecycle(tmp_path):
    layout = ModLayout(root=tmp_path / "FF9CustomMap")
    cs = rebalance.write_source(layout, rebalance.RebalanceSpec(player=1.5))
    assert cs.is_file()
    assert rebalance.write_source(layout, None) is None
    assert not rebalance.rebalance_dir(layout).exists()


# ---- [rebalance] hub composition + build wiring -----------------------------------------------------------
def test_hub_rebalance_before_telemetry_in_damage_hook():
    """rebalance MUTATES HpDamage, telemetry OBSERVES it -- so in OnDamageFinalChanges the rebalance call must
    come before telemetry's LogResult, and both after the verbatim reflect-multiplier default."""
    src = overload.render_hub([_feat("telemetry"), _feat("rebalance")])   # any input order
    i_reflect = src.index("GetReflectMultiplierOnTarget")
    i_reb = src.index("RebalanceOverload.OnDamageFinalChanges(v)")
    i_tel = src.index("BattleTelemetry.LogResult(v)")
    assert i_reflect < i_reb < i_tel
    assert "IOverloadDamageModifierScript" in src


def test_rebalance_in_build_owned_dirs():
    assert "Rebalance" in overload.build_owned_dirs()


def test_validate_reports_bad_rebalance(tmp_path):
    from ff9mapkit.build import FieldProject, validate
    p = tmp_path / "f.field.toml"
    p.write_text(BASE + "\n[rebalance]\nplayer_damage = 99.0\n", encoding="utf-8")
    assert any("out of range" in x for x in validate(FieldProject.load(p)))
    p.write_text(BASE + '\n[rebalance]\nenemy_damage = 0.5\nflag = "hard_mode"\n'
                 '\n[[flag]]\nname = "hard_mode"\nindex = 8600\n', encoding="utf-8")
    assert validate(FieldProject.load(p)) == []


def test_emit_scripts_rebalance_only(tmp_path, monkeypatch):
    """[rebalance] alone (no scripted abilities, no [difficulty]) still builds the DLL (hub + scaler)."""
    calls = _mock_compiles(monkeypatch)
    from ff9mapkit.build import _emit_scripts
    layout = ModLayout(root=tmp_path / "mod")
    proj = SimpleNamespace(raw={"rebalance": {"player_damage": 1.5}})
    warnings = _emit_scripts([proj], layout, "FF9CustomMap")
    assert any("rebalance" in w for w in warnings)
    srcs, out = calls[-1]
    assert any(rebalance.REBALANCE_BASENAME in s for s in srcs) and any(overload.HUB_BASENAME in s for s in srcs)
    # de-rebalanced rebuild drops the tree
    assert _emit_scripts([SimpleNamespace(raw={})], layout, "FF9CustomMap") == []
    assert not layout.scripts_dir.exists()


def test_emit_scripts_difficulty_and_rebalance_coexist(tmp_path, monkeypatch):
    """Both blocks on one mod -> both feature sources + the hub, one DLL."""
    calls = _mock_compiles(monkeypatch)
    from ff9mapkit.build import _emit_scripts
    layout = ModLayout(root=tmp_path / "mod")
    proj = SimpleNamespace(raw={"difficulty": {"enemy_hp": 2.0}, "rebalance": {"player_damage": 1.5}})
    warnings = _emit_scripts([proj], layout, "FF9CustomMap")
    srcs, _ = calls[-1]
    assert any(difficulty.DIFFICULTY_BASENAME in s for s in srcs)
    assert any(rebalance.REBALANCE_BASENAME in s for s in srcs)
    assert any(overload.HUB_BASENAME in s for s in srcs)
    assert any("difficulty" in w and "rebalance" in w for w in warnings)


# ---- the RETURNING-hook hub mode + [deathrules] -----------------------------------------------------------
def test_hub_deathrules_returning_hook():
    """OnGameOver is a RETURNING hook: the hub must RETURN the one owner's verdict expression (no void
    splice), carry the soft-lock-safe false fallback, and claim the OnBattleInit reset too."""
    src = overload.render_hub([_feat("deathrules")])
    assert "IOverloadOnGameOverScript" in src and "IOverloadOnBattleInitScript" in src
    assert "try { return Memoria.Scripts.Overload.DeathRulesOverload.OnGameOver(state, dyingPC); } catch { }" in src
    assert "return false;" in src                         # the fail-safe: a vanilla defeat, never a stall
    assert "try { Memoria.Scripts.Overload.DeathRulesOverload.OnBattleInit(); } catch { }" in src
    # unclaimed calc interfaces stay unclaimed -> the engine inline defaults run untouched
    assert "IOverloadDamageModifierScript" not in src
    assert src.count("{") == src.count("}")


def test_hub_returning_hook_is_single_owner():
    """Two features claiming a RETURNING hook is a hard error (the engine acts on ONE verdict)."""
    a = {"name": "a", "order": 1, "hooks": {"OnGameOver": "A.OnGameOver(state, dyingPC)"}}
    b = {"name": "b", "order": 2, "hooks": {"OnGameOver": "B.OnGameOver(state, dyingPC)"}}
    with pytest.raises(ScriptCompileError, match="single-owner"):
        overload.render_hub([a, b])
    assert "A.OnGameOver" in overload.render_hub([a])     # one owner renders fine


def test_deathrules_in_build_owned_dirs():
    assert "DeathRules" in overload.build_owned_dirs()


# ---- [deathrules] parse -----------------------------------------------------------------------------------
def test_deathrules_parse_and_rejects():
    spec = deathrules.parse_table({"second_wind": True, "chance": 60, "keep_rebirth_flame": False,
                                   "flag": "Mercy_Mode"}, name_map={"mercy_mode": 8601})
    assert spec.second_wind and spec.chance == 60 and not spec.keep_rebirth_flame and spec.flag == 8601
    with pytest.raises(deathrules.DeathRulesError, match="unknown key"):
        deathrules.parse_table({"second_wind": True, "revive": True})
    with pytest.raises(deathrules.DeathRulesError, match="true or false"):
        deathrules.parse_table({"second_wind": 1})
    with pytest.raises(deathrules.DeathRulesError, match="whole percent"):
        deathrules.parse_table({"second_wind": True, "chance": 0.5})
    with pytest.raises(deathrules.DeathRulesError, match="out of range"):
        deathrules.parse_table({"second_wind": True, "chance": 0})
    with pytest.raises(deathrules.DeathRulesError, match="chance only applies"):
        deathrules.parse_table({"keep_rebirth_flame": False, "chance": 50})
    with pytest.raises(deathrules.DeathRulesError, match="does nothing"):
        deathrules.parse_table({"second_wind": False})
    with pytest.raises(deathrules.DeathRulesError, match="does nothing"):
        deathrules.parse_table({})
    with pytest.raises(deathrules.DeathRulesError, match="unknown flag name"):
        deathrules.parse_table({"second_wind": True, "flag": "nope"})
    with pytest.raises(deathrules.DeathRulesError, match="out of range"):
        deathrules.parse_table({"second_wind": True, "flag": 99999})


def test_deathrules_collect_dedupes_and_conflicts():
    a = SimpleNamespace(raw={"deathrules": {"second_wind": True}})
    b = SimpleNamespace(raw={"deathrules": {"second_wind": True}})
    c = SimpleNamespace(raw={"deathrules": {"second_wind": True, "chance": 50}})
    assert deathrules.collect([SimpleNamespace(raw={})]) is None
    spec, carrier = deathrules.collect([a, b])
    assert spec.second_wind and carrier is a
    with pytest.raises(deathrules.DeathRulesError, match="DIFFERENT settings"):
        deathrules.collect([a, c])


# ---- [deathrules] render ----------------------------------------------------------------------------------
def test_deathrules_render_pins_eiko_transcription():
    """Owning OnGameOver DISPLACES the engine default -- the Eiko Rebirth Flame block must be transcribed
    VERBATIM (btl_sys.CheckBattlePhase 'Default method') or installing [deathrules] would change vanilla
    gameplay for parties carrying Eiko."""
    src = deathrules.render(deathrules.DeathRulesSpec(second_wind=True))
    for verbatim in (
        "(CharacterId)btl.bi.slot_no == CharacterId.Eiko",
        "btl_stat.CheckStatus(btl, BattleStatusConst.NoRebirthFlame)",
        "btl_cmd.CheckSpecificCommand(btl, BattleCommandId.SysLastPhoenix)",
        "ff9item.FF9Item_GetCount(RegularItem.PhoenixPinion) > Comn.random8()",
        "UIManager.Battle.FF9BMenu_EnableMenu(true);",
        "btl_cmd.SetCommand(btl.cmd[0], BattleCommandId.SysLastPhoenix, (Int32)BattleAbilityId.RebirthFlame, btl_scrp.GetBattleID(0U), 1u);",
    ):
        assert verbatim in src, verbatim
    assert "if (VanillaRebirthFlame(state))" in src        # default KEPT by default
    assert src.count("{") == src.count("}")
    assert "IOverload" not in src                          # a plain static feature class (the hub owns interfaces)


def test_deathrules_render_second_wind_mechanism():
    """The second wind reuses the ENGINE's revive mechanism (queue SysLastPhoenix/RebirthFlame on the fallen
    unit + re-enable the menu), once per battle, with the vanilla pending-revive guard FIRST."""
    src = deathrules.render(deathrules.DeathRulesSpec(second_wind=True))
    i_pending = src.index("btl_cmd.CheckSpecificCommand2(BattleCommandId.SysLastPhoenix)")
    i_used = src.index("if (_secondWindUsed)")
    assert i_pending < i_used                              # a queued revive cancels the wipe even when spent
    assert "dyingPC.Data.cmd[0]" in src                    # the fallen unit carries the command (vanilla: dead Eiko)
    assert "_secondWindUsed = false;" in src               # OnBattleInit recharge
    assert "Comn.random16()" not in src                    # chance=100 -> no roll emitted
    solo = deathrules.render(deathrules.DeathRulesSpec(second_wind=True, chance=60))
    assert "Comn.random16() % 100 >= 60" in solo


def test_deathrules_render_gate_and_eiko_matrix():
    """Flag semantics: bit CLEAR = fully VANILLA, Eiko included -- so the gate is a tested CONDITION
    (flag_expr_cs), never the shared early-return, and Eiko-removal is suspended while the rule sleeps."""
    expr = overload.flag_expr_cs(8600)
    assert expr == "(FF9StateSystem.EventState.gEventGlobal[1075] & 1) != 0"
    gated = deathrules.render(deathrules.DeathRulesSpec(second_wind=True, flag=8600, flag_label="mercy"))
    assert f"Boolean ruleActive = {expr};" in gated
    assert "if (!ruleActive)\n                    return false;" in gated   # asleep -> vanilla defeat
    # keep=false under a gate: vanilla Eiko still fires while the rule sleeps
    gated_no_eiko = deathrules.render(deathrules.DeathRulesSpec(second_wind=True, keep_rebirth_flame=False,
                                                                flag=8600, flag_label="mercy"))
    assert "if (!ruleActive && VanillaRebirthFlame(state))" in gated_no_eiko
    # keep=false with NO gate: the removal is unconditional (and commented as intentional)
    no_eiko = deathrules.render(deathrules.DeathRulesSpec(second_wind=True, keep_rebirth_flame=False))
    assert "intentionally REMOVED" in no_eiko
    assert "if (VanillaRebirthFlame(state))" not in no_eiko
    for src in (gated, gated_no_eiko, no_eiko):
        assert src.count("{") == src.count("}")


def test_deathrules_parse_animation_and_revive_hp():
    spec = deathrules.parse_table({"second_wind": True, "animation": "short", "revive_hp": 0.25})
    assert spec.animation == "short" and spec.revive_hp == 0.25
    assert deathrules.parse_table({"second_wind": True}).animation == "full"   # the proven default
    with pytest.raises(deathrules.DeathRulesError, match="animation must be one of"):
        deathrules.parse_table({"second_wind": True, "animation": "none"})
    with pytest.raises(deathrules.DeathRulesError, match="animation only applies"):
        deathrules.parse_table({"keep_rebirth_flame": False, "animation": "short"})
    with pytest.raises(deathrules.DeathRulesError, match='revive_hp only applies to animation = "short"'):
        deathrules.parse_table({"second_wind": True, "revive_hp": 0.5})
    with pytest.raises(deathrules.DeathRulesError, match="out of range"):
        deathrules.parse_table({"second_wind": True, "animation": "short", "revive_hp": 0.0})
    with pytest.raises(deathrules.DeathRulesError, match="out of range"):
        deathrules.parse_table({"second_wind": True, "animation": "short", "revive_hp": 1.5})
    with pytest.raises(deathrules.DeathRulesError, match="must be a fraction"):
        deathrules.parse_table({"second_wind": True, "animation": "short", "revive_hp": True})


def test_deathrules_render_short_animation():
    """animation="short" replaces the queued Phoenix with the engine's own death-changer revive recipe
    (AutoLifeStatusScript.OnDeath + DeathStatusScript.Remove + DecidePlayerDieSequence's cancel branch):
    set HP -> RemoveStatus(Death) -> SetDefaultIdle, dead players only, fall through when nobody revives."""
    src = deathrules.render(deathrules.DeathRulesSpec(second_wind=True, animation="short", revive_hp=0.25))
    for line in (
        "unit.CurrentHp = Math.Max(1u, (UInt32)(unit.MaximumHp * 0.25));",
        "btl_stat.RemoveStatus(unit, BattleStatusId.Death);",
        "btl_mot.SetDefaultIdle(fallen);",
        "FF9StateSystem.Settings.SetHPFull();",
        "if (!revived)",
    ):
        assert line in src, line
    # only the DEAD revive (petrify stays), and the full-variant Phoenix queue is absent
    assert "fallen.cur.hp != 0 && !btl_stat.CheckStatus(fallen, BattleStatus.Death)" in src
    assert "dyingPC.Data.cmd[0]" not in src
    # the shared prelude + once-per-battle machinery still present
    assert "btl_cmd.CheckSpecificCommand2(BattleCommandId.SysLastPhoenix)" in src
    assert "_secondWindUsed = true;" in src
    assert src.count("{") == src.count("}")
    # the FULL variant is unchanged: Phoenix queue present, no direct-revive loop
    full = deathrules.render(deathrules.DeathRulesSpec(second_wind=True))
    assert "dyingPC.Data.cmd[0]" in full and "SetDefaultIdle" not in full
    assert full.count("{") == full.count("}")


def test_deathrules_write_source_lifecycle(tmp_path):
    layout = ModLayout(root=tmp_path / "FF9CustomMap")
    cs = deathrules.write_source(layout, deathrules.DeathRulesSpec(second_wind=True))
    assert cs.is_file()
    assert deathrules.write_source(layout, None) is None
    assert not deathrules.deathrules_dir(layout).exists()


# ---- [deathrules] build + validate wiring -----------------------------------------------------------------
def test_validate_reports_bad_deathrules(tmp_path):
    from ff9mapkit.build import FieldProject, validate
    p = tmp_path / "f.field.toml"
    p.write_text(BASE + "\n[deathrules]\nsecond_wind = true\nchance = 200\n", encoding="utf-8")
    assert any("out of range" in x for x in validate(FieldProject.load(p)))
    p.write_text(BASE + '\n[deathrules]\nsecond_wind = true\nflag = "mercy_mode"\n'
                 '\n[[flag]]\nname = "mercy_mode"\nindex = 8601\n', encoding="utf-8")
    assert validate(FieldProject.load(p)) == []            # named flag resolves through the [[flag]] registry


def test_emit_scripts_deathrules_only(tmp_path, monkeypatch):
    """[deathrules] alone (no scripted abilities, no scalers) still builds the DLL (hub + rules)."""
    calls = _mock_compiles(monkeypatch)
    from ff9mapkit.build import _emit_scripts
    layout = ModLayout(root=tmp_path / "mod")
    proj = SimpleNamespace(raw={"deathrules": {"second_wind": True}})
    warnings = _emit_scripts([proj], layout, "FF9CustomMap")
    assert any("deathrules" in w for w in warnings)
    srcs, _ = calls[-1]
    assert any(deathrules.DEATHRULES_BASENAME in s for s in srcs) and any(overload.HUB_BASENAME in s for s in srcs)
    hub = overload.hub_cs(layout).read_text(encoding="utf-8")
    assert "return Memoria.Scripts.Overload.DeathRulesOverload.OnGameOver(state, dyingPC);" in hub
    # de-ruled rebuild drops the tree
    assert _emit_scripts([SimpleNamespace(raw={})], layout, "FF9CustomMap") == []
    assert not layout.scripts_dir.exists()


# ---- [deathrules] on_defeat (warp instead of a game over) -------------------------------------------------
def test_deathrules_parse_on_defeat():
    spec = deathrules.parse_table({"on_defeat": {"warp_to": 6000, "hp": 0.3, "gil_loss": 0.1}})
    assert (spec.warp_to, spec.warp_hp, spec.warp_gil_loss) == (6000, 0.3, 0.1)
    assert spec.wipe_flag == deathrules.WIPE_FLAG_DEFAULT      # the kit-reserved marker bit
    assert not spec.second_wind                                # on_defeat alone is a legal block
    both = deathrules.parse_table({"second_wind": True, "on_defeat": {"warp_to": 6000}})
    assert both.second_wind and both.warp_to == 6000 and both.warp_hp == 0.2
    with pytest.raises(deathrules.DeathRulesError, match="must be an inline table"):
        deathrules.parse_table({"on_defeat": 6000})
    with pytest.raises(deathrules.DeathRulesError, match="unknown key"):
        deathrules.parse_table({"on_defeat": {"warp_to": 6000, "field": 1}})
    with pytest.raises(deathrules.DeathRulesError, match="must be a field id"):
        deathrules.parse_table({"on_defeat": {}})
    with pytest.raises(deathrules.DeathRulesError, match="out of range"):
        deathrules.parse_table({"on_defeat": {"warp_to": 40000}})    # past the Int16 fldMapNo cap
    with pytest.raises(deathrules.DeathRulesError, match="hp = 0 out of range"):
        deathrules.parse_table({"on_defeat": {"warp_to": 6000, "hp": 0.0}})
    with pytest.raises(deathrules.DeathRulesError, match="gil_loss = 1 out of range"):
        deathrules.parse_table({"on_defeat": {"warp_to": 6000, "gil_loss": 1.0}})
    with pytest.raises(deathrules.DeathRulesError, match="unknown flag name"):
        deathrules.parse_table({"on_defeat": {"warp_to": 6000, "flag": "nope"}})


def test_deathrules_render_on_defeat():
    """on_defeat = the QUIET-DEFEAT revive (W-suffixed locals, deliberately NO stand-up: the battle fades
    over the fallen party) + the double-dock guard + the transcribed FLEE end + the wipe marker -- and NO
    flee-stat pollution (no escape_no++, no BTL_FLAG_ABILITY_FLEE)."""
    src = deathrules.render(deathrules.DeathRulesSpec(warp_to=1055, warp_gil_loss=0.1))
    for line in (
        "unitW.CurrentHp = Math.Max(1u, (UInt32)(unitW.MaximumHp * 0.2));",
        "btl_stat.RemoveStatus(unitW, BattleStatusId.Death);",
        f"gw[{deathrules.WIPE_FLAG_DEFAULT >> 3}] |= {1 << (deathrules.WIPE_FLAG_DEFAULT & 7)};",
        "UIManager.Battle.SetIdle();",
        "state.btl_escape_fade = 0;",
        "state.btl_phase = FF9StateBattleSystem.PHASE_MENU_OFF;",
        "state.btl_seq = FF9StateBattleSystem.SEQ_MENU_OFF_ESCAPE;",
        "btl_cmd.KillAllCommand(state);",
        "UInt32 gilLostW = (UInt32)(FF9StateSystem.Common.FF9.party.gil * 0.1);",
    ):
        assert line in src, line
    # the QUIET DEFEAT: no stand-up call in the on_defeat revive (the second-wind SHORT variant keeps its own)
    assert "btl_mot.SetDefaultIdle(" not in src
    # the DOUBLE-DOCK GUARD: gil + marker sit inside the once-per-wipe-exit block; the exit re-asserts
    # unconditionally; the flag has its static + per-battle reset
    assert "if (!_defeatWarpFired)" in src
    assert src.index("_defeatWarpFired = true;") < src.index("gilLostW")
    assert "private static Boolean _defeatWarpFired;" in src
    assert "_defeatWarpFired = false;" in src
    assert src.index("UIManager.Battle.SetIdle();") > src.index("}")  # the exit tail is OUTSIDE the guard
    assert "escape_no" not in src and "BTL_FLAG_ABILITY_FLEE" not in src
    assert src.count("{") == src.count("}")
    # no gil_loss -> no gil block at all
    assert "gilLostW" not in deathrules.render(deathrules.DeathRulesSpec(warp_to=1055))
    # WITHOUT on_defeat the guard machinery is entirely absent (byte-stable proven builds)
    assert "_defeatWarpFired" not in deathrules.render(deathrules.DeathRulesSpec(second_wind=True))


def test_deathrules_render_second_wind_falls_through_to_on_defeat():
    """With on_defeat behind it, the second wind's spent/failed-roll paths FALL THROUGH to the warp (no
    `return false` early-outs), and the two revive loops' locals don't collide."""
    src = deathrules.render(deathrules.DeathRulesSpec(second_wind=True, animation="short", chance=60,
                                                      warp_to=1055))
    # the wind never fires mid-wipe-exit (a re-kill during the fade must not re-roll a fresh Phoenix)
    assert "if (!_defeatWarpFired && !_secondWindUsed && Comn.random16() % 100 < 60)" in src
    assert "return false; // spent this battle" not in src     # the straight-line early-out is gone
    assert "revived = " in src and "revivedW = " in src        # both loops coexist
    i_sw = src.index("_secondWindUsed = true;")
    i_od = src.index("// ---- on_defeat")
    assert i_sw < i_od                                         # the wind fires first; on_defeat is the tail
    assert src.count("{") == src.count("}")
    # WITHOUT on_defeat the proven straight-line shape is byte-stable (the guard block is absent)
    plain = deathrules.render(deathrules.DeathRulesSpec(second_wind=True, chance=60))
    assert "return false; // spent this battle" in plain and "revivedW" not in plain


def test_emit_scripts_on_defeat_coverage_warning(tmp_path, monkeypatch):
    """The DLL half is mod-global but the field half only lands on fields carrying the block -- the build
    must NAME uncovered encounter fields."""
    _mock_compiles(monkeypatch)
    from ff9mapkit.build import _emit_scripts
    layout = ModLayout(root=tmp_path / "mod")
    covered = SimpleNamespace(raw={"field": {"name": "HUBROOM"}, "encounter": {"scene": 67},
                                   "deathrules": {"on_defeat": {"warp_to": 6000}}})
    uncovered = SimpleNamespace(raw={"field": {"name": "WILDS"}, "encounter": {"scene": 67}})
    peaceful = SimpleNamespace(raw={"field": {"name": "TOWN"}})
    warnings = _emit_scripts([covered, uncovered, peaceful], layout, "FF9CustomMap")
    assert any("WILDS" in w and "wipe-warp" in w for w in warnings)
    assert not any("TOWN" in w for w in warnings)              # no encounters -> no wipe possible -> no gap


# ---- the OUTPOST system (on_defeat "last outpost visited") ------------------------------------------------
def test_field_to_var_encoding_roundtrips():
    """The COMPUTED Field() warp: opcode 0x2B, argFlag 0x01, the outpost var pushed as an expression --
    and the kit's own decoder (which parses real fields' argFlag lane) must read our emission back
    byte-exactly: one instruction, op 0x2B, a single EXPR operand."""
    from ff9mapkit.content import region
    from ff9mapkit.eb import disasm
    b = region.field_to_var(region.GLOB_UINT16, deathrules.OUTPOST_BYTE)
    # 1060 > 0xFF -> the long-index var token: class 0xDC|0x20, u16 LE index, then the expr terminator
    assert b == bytes([0x2B, 0x01, 0xDC | 0x20]) + (1060).to_bytes(2, "little") + bytes([0x7F])
    instr, pos = disasm.read_code(b, 0)
    assert pos == len(b) and instr.op == 0x2B
    assert instr.arg_is_expr == [True]                     # the one operand decoded as an expression


def test_field_prologue_outpost_dispatch():
    """The wipe-warp tail: computed Field(<outpost>) when the var is nonzero, literal Field(warp_to) as
    the fallback -- outpost branch FIRST (each Field transitions away)."""
    from ff9mapkit.content import region
    pro = deathrules.field_prologue(deathrules.DeathRulesSpec(warp_to=407))
    computed = region.field_to_var(region.GLOB_UINT16, deathrules.OUTPOST_BYTE)
    literal = bytes([0x2B, 0x00]) + (407).to_bytes(2, "little")
    assert computed in pro and literal in pro
    assert pro.index(computed) < pro.index(literal)


# (the `[field] outpost = true` REGISTRATION test lives in test_content.py -- it needs the real blank-field
#  template for the Main_Init injection)


# ---- [lowhp] on the UnitCheckPoint returning hook ---------------------------------------------------------
def test_hub_lowhp_returning_hook():
    """UnitCheckPoint is the second RETURNING hook: single-owner verdict expression, fail-safe 0 (no forced
    status -- the caller only acts on the Death bit, and the side effects retry at the next checkpoint)."""
    src = overload.render_hub([_feat("lowhp")])
    assert "IOverloadUnitCheckPointScript" in src
    assert "try { return Memoria.Scripts.Overload.LowHPOverload.UpdatePointStatus(unit); } catch { }" in src
    assert "return 0;" in src
    assert "IOverloadOnGameOverScript" not in src         # unclaimed -> the engine inline default runs
    assert src.count("{") == src.count("}")
    assert "LowHP" in overload.build_owned_dirs()


# ---- [lowhp] parse ----------------------------------------------------------------------------------------
def test_lowhp_parse_fractions_and_rejects():
    assert (lambda s: (s.num, s.den))(lowhp.parse_table({"threshold": "1/3"})) == (1, 3)
    assert (lambda s: (s.num, s.den))(lowhp.parse_table({"threshold": 0.5})) == (1, 2)
    assert (lambda s: (s.num, s.den))(lowhp.parse_table({"threshold": 0.333})) == (1, 3)   # floats snap
    spec = lowhp.parse_table({"threshold": "2/5", "flag": "Hard_Mode"}, name_map={"hard_mode": 8600})
    assert (spec.num, spec.den, spec.flag) == (2, 5, 8600)
    with pytest.raises(lowhp.LowHPError, match="threshold is required"):
        lowhp.parse_table({})
    with pytest.raises(lowhp.LowHPError, match="vanilla 1/6"):
        lowhp.parse_table({"threshold": "1/6"})
    with pytest.raises(lowhp.LowHPError, match="out of range"):
        lowhp.parse_table({"threshold": 1.0})
    with pytest.raises(lowhp.LowHPError, match="out of range"):
        lowhp.parse_table({"threshold": "0/3"})
    with pytest.raises(lowhp.LowHPError, match="too fine-grained"):
        lowhp.parse_table({"threshold": "7/200"})         # an explicit fine string refuses (floats snap)
    with pytest.raises(lowhp.LowHPError, match="must look like"):
        lowhp.parse_table({"threshold": "a third"})
    with pytest.raises(lowhp.LowHPError, match="must be a fraction"):
        lowhp.parse_table({"threshold": True})
    with pytest.raises(lowhp.LowHPError, match="unknown key"):
        lowhp.parse_table({"threshold": "1/3", "mp": 0.5})
    with pytest.raises(lowhp.LowHPError, match="unknown flag name"):
        lowhp.parse_table({"threshold": "1/3", "flag": "nope"})


def test_lowhp_collect_dedupes_and_conflicts():
    a = SimpleNamespace(raw={"lowhp": {"threshold": "1/3"}})
    b = SimpleNamespace(raw={"lowhp": {"threshold": "1/3"}})
    c = SimpleNamespace(raw={"lowhp": {"threshold": "1/2"}})
    assert lowhp.collect([SimpleNamespace(raw={})]) is None
    spec, carrier = lowhp.collect([a, b])
    assert (spec.num, spec.den) == (1, 3) and carrier is a
    with pytest.raises(lowhp.LowHPError, match="DIFFERENT settings"):
        lowhp.collect([a, c])


# ---- [lowhp] render ---------------------------------------------------------------------------------------
def test_lowhp_render_pins_default_and_compare():
    """Owning UnitCheckPoint displaces the whole default -- the LowHP/UI side effects must be transcribed
    VERBATIM (btl_para.CheckPointDataStatus 'Default method') with only the threshold comparison changed."""
    src = lowhp.render(lowhp.LowHPSpec(num=1, den=3))
    assert "unit.CurrentHp * 3 <= unit.MaximumHp;" in src  # num=1 keeps the vanilla `* den <= Max` shape
    for verbatim in (
        "unit.UIColorHP = FF9TextTool.Yellow;",
        "if (!btl_stat.CheckStatus(unit, BattleStatus.LowHP))",
        "btl_stat.AlterStatus(unit, BattleStatusId.LowHP);",
        "unit.UIColorHP = FF9TextTool.White;",
        "btl_stat.RemoveStatus(unit, BattleStatusId.LowHP);",
        "unit.UIColorMP = unit.CurrentMp <= unit.MaximumMp / 6f ? FF9TextTool.Yellow : FF9TextTool.White;",
        "return isLowHP ? BattleStatus.LowHP : 0;",
    ):
        assert verbatim in src, verbatim
    assert "IOverload" not in src                          # a plain static feature class (the hub owns interfaces)
    assert "try {" not in src                              # deliberately bare: the hub's wrapper is the fail-safe
    assert src.count("{") == src.count("}")
    # a non-unit numerator multiplies both sides
    both = lowhp.render(lowhp.LowHPSpec(num=2, den=5))
    assert "unit.CurrentHp * 5 <= unit.MaximumHp * 2" in both


def test_lowhp_render_gate_picks_threshold():
    """Flag semantics: bit CLEAR = the vanilla 1/6 (the same transcribed side effects still run) -- the gate
    only picks the comparison, and its own try/catch degrades to vanilla."""
    src = lowhp.render(lowhp.LowHPSpec(num=1, den=2, flag=8600, flag_label="hard_mode"))
    assert f"ruleActive = {overload.flag_expr_cs(8600)};" in src
    assert "(ruleActive ? unit.CurrentHp * 2 <= unit.MaximumHp : unit.CurrentHp * 6 <= unit.MaximumHp)" in src
    assert src.count("{") == src.count("}")


def test_lowhp_write_source_lifecycle(tmp_path):
    layout = ModLayout(root=tmp_path / "FF9CustomMap")
    cs = lowhp.write_source(layout, lowhp.LowHPSpec(num=1, den=3))
    assert cs.is_file()
    assert lowhp.write_source(layout, None) is None
    assert not lowhp.lowhp_dir(layout).exists()


# ---- [lowhp] build + validate wiring ----------------------------------------------------------------------
def test_validate_reports_bad_lowhp(tmp_path):
    from ff9mapkit.build import FieldProject, validate
    p = tmp_path / "f.field.toml"
    p.write_text(BASE + '\n[lowhp]\nthreshold = "1/6"\n', encoding="utf-8")
    assert any("vanilla 1/6" in x for x in validate(FieldProject.load(p)))
    p.write_text(BASE + '\n[lowhp]\nthreshold = "1/3"\nflag = "hard_mode"\n'
                 '\n[[flag]]\nname = "hard_mode"\nindex = 8600\n', encoding="utf-8")
    assert validate(FieldProject.load(p)) == []            # named flag resolves through the [[flag]] registry


def test_emit_scripts_lowhp_only(tmp_path, monkeypatch):
    """[lowhp] alone still builds the DLL (hub + threshold class)."""
    calls = _mock_compiles(monkeypatch)
    from ff9mapkit.build import _emit_scripts
    layout = ModLayout(root=tmp_path / "mod")
    proj = SimpleNamespace(raw={"lowhp": {"threshold": "1/3"}})
    warnings = _emit_scripts([proj], layout, "FF9CustomMap")
    assert any("lowhp" in w for w in warnings)
    srcs, _ = calls[-1]
    assert any(lowhp.LOWHP_BASENAME in s for s in srcs) and any(overload.HUB_BASENAME in s for s in srcs)
    hub = overload.hub_cs(layout).read_text(encoding="utf-8")
    assert "return Memoria.Scripts.Overload.LowHPOverload.UpdatePointStatus(unit);" in hub
    # de-thresholded rebuild drops the tree
    assert _emit_scripts([SimpleNamespace(raw={})], layout, "FF9CustomMap") == []
    assert not layout.scripts_dir.exists()


# ---- the money test: the WHOLE tree compiles against the LIVE engine (install + csc gated) ---------------
def test_tree_compiles_against_live_engine(tmp_path):
    """Hub + telemetry + difficulty + rebalance + deathrules in one DLL -- proves every emitted C# member
    exists PUBLIC in the installed Assembly-CSharp (BattleUnit.Magic/IsPlayer/HpDamage/Data,
    EventState.gEventGlobal, CalcFlag.HpAlteration/HpRecovery, btl_cmd.SetCommand/CheckSpecificCommand2,
    btl_scrp.GetBattleID, ff9item.FF9Item_GetCount, Comn.random8/16, the transcribed defaults...)."""
    from ff9mapkit.battle import scriptcompile
    if not scriptcompile.toolchain_available():
        pytest.skip("no C# compiler (csc) to build the hook DLL")
    try:
        scriptcompile._managed_dir(None)
    except Exception:
        pytest.skip("no FF9 install for the managed DLLs")
    layout = ModLayout(root=tmp_path / "FF9CustomMap")
    cs = overload.feature_cs(layout, _feat("telemetry"))
    cs.parent.mkdir(parents=True)
    cs.write_text(telemetry.telemetry_source(), encoding="utf-8", newline="\n")
    difficulty.write_source(layout, difficulty.DifficultySpec(hp=1.5, attack=1.25, magic=1.1,
                                                              flag=8600, flag_label="hard_mode"))
    rebalance.write_source(layout, rebalance.RebalanceSpec(player=1.5, enemy=0.75,
                                                           flag=8600, flag_label="hard_mode"))
    # every deathrules construct: gate expr + chance roll + FULL second wind + the gated-Eiko branch
    deathrules.write_source(layout, deathrules.DeathRulesSpec(second_wind=True, chance=60,
                                                              keep_rebirth_flame=False,
                                                              flag=8601, flag_label="mercy_mode"))
    # [lowhp] gated + non-unit numerator (UIColor/FF9TextTool/AlterStatus surface + the compare ternary)
    lowhp.write_source(layout, lowhp.LowHPSpec(num=2, den=5, flag=8602, flag_label="hard_mode"))
    out = overload.compile_tree(layout, "FF9CustomMap")
    assert out is not None and out.is_file() and out.stat().st_size > 0
    # ...and the SHORT-animation + on_defeat surface (BattleUnit ctor, RemoveStatus(BattleUnit,
    # BattleStatusId), btl_mot.SetDefaultIdle, Settings.SetHPFull, btl.cur.hp, Common.FF9.party.gil,
    # UIManager.Battle.SetIdle, btl_phase/btl_seq + the PHASE/SEQ consts, KillAllCommand) -- recompile
    deathrules.write_source(layout, deathrules.DeathRulesSpec(second_wind=True, animation="short",
                                                              revive_hp=0.25, chance=60,
                                                              warp_to=1055, warp_gil_loss=0.1))
    out = overload.compile_tree(layout, "FF9CustomMap")
    assert out is not None and out.is_file() and out.stat().st_size > 0
