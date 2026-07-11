"""The Overload hub + the declarative [difficulty] feature (project-ff9-overload-hooks).

Engine fact under test: Memoria registers IOverload* implementations ONE per interface per DLL (last-wins,
type order unspecified), so the kit emits exactly one hub class and composes features as plain statics.
Offline tests pin the hub's transcribed engine defaults (moved verbatim from the in-game-proven telemetry
source), the splice order (mutators before observers), the collision gate, the [difficulty] parse/render,
and the build/deploy wiring (compile mocked). A csc+install-gated test proves the whole tree (hub +
telemetry + difficulty) compiles against the LIVE engine's managed DLLs.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from ff9mapkit.battle import difficulty, overload, telemetry
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


# ---- the money test: the WHOLE tree compiles against the LIVE engine (install + csc gated) ---------------
def test_tree_compiles_against_live_engine(tmp_path):
    """Hub + telemetry + difficulty in one DLL -- proves every emitted C# member exists PUBLIC in the
    installed Assembly-CSharp (BattleUnit.Magic, EventState.gEventGlobal, the transcribed defaults...)."""
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
    out = overload.compile_tree(layout, "FF9CustomMap")
    assert out is not None and out.is_file() and out.stat().st_size > 0
