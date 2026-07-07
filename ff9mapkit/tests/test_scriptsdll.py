"""The Scripts-DLL channel: `script = {template/body}` on a custom ability -> a minted battle FORMULA in a
mod-owned Memoria.Scripts.<Mod>.dll (project-ff9-scripts-dll, Phase-1 bind proven in-game 2026-07-07).

Offline tests pin the source emitter (templates cloned from FF9's own donors) + the 256-band scriptId
allocator; a full-build test (install + C# compiler gated) proves the .cs emits, the DLL compiles, and the
Actions.csv row's scriptId is repointed at the minted formula.
"""
from __future__ import annotations

import pytest

from ff9mapkit.battle import scriptsource as ss
from ff9mapkit.battle import actiondelta as ad
from ff9mapkit.content import playable as pl
from ff9mapkit.build import FieldProject, build_mod, validate, lint_all, BuildError
from ff9mapkit.config import ModLayout


# ---- the source emitter (no install) ----------------------------------------------------------
def test_render_template_shape():
    fname, src = ss.render_script(256, "Soul Leech", template="drain_hp")
    assert fname == "0256_SoulLeechScript.cs"
    assert "public sealed class SoulLeech256Script : IBattleScript" in src
    assert "public const Int32 Id = 256;" in src
    assert "[BattleScript(Id)]" in src
    assert "namespace Memoria.Scripts.Battle" in src
    # the drain body (cloned verbatim from FF9's 0016 DrainHpScript) heals the caster
    assert "_v.Caster.HpDamage = _v.Target.HpDamage;" in src
    assert "_v.PrepareHpDraining();" in src


def test_render_body_escape_hatch():
    fname, src = ss.render_script(300, "Quarter", body="_v.Target.HpDamage = _v.Target.MaximumHp / 4;")
    assert fname == "0300_QuarterScript.cs"
    assert "_v.Target.HpDamage = _v.Target.MaximumHp / 4;" in src
    assert "public const Int32 Id = 300;" in src


def test_render_sanitizes_class_name():
    # punctuation/spaces stripped; the id keeps the class unique across same-named abilities
    _, src = ss.render_script(257, "Fire?! v2", template="magic_damage")
    assert "public sealed class Firev2257Script" in src


def test_render_strips_sentinel_in_name():
    # a name that smuggles a shell sentinel must NOT splice the body into the doc comment (it would break the .cs)
    _, src = ss.render_script(256, "My __BODY__ Spell", template="magic_damage")
    summary = next(l for l in src.splitlines() if "<summary>" in l)
    assert "_v." not in summary                                # the Perform body did NOT leak into the 1-line comment
    assert "Spell" in summary


def test_render_unknown_template_raises():
    with pytest.raises(ss.ScriptSourceError):
        ss.render_script(256, "X", template="does_not_exist")


def test_render_empty_body_raises():
    with pytest.raises(ss.ScriptSourceError):
        ss.render_script(256, "X", body="   ")


def test_all_templates_render():
    for t in ss.TEMPLATES:
        _, src = ss.render_script(256, "T", template=t)
        assert "public void Perform()" in src and "Memoria.Scripts.Battle" in src


def test_write_scripts_wipes_stale(tmp_path):
    # a rebuild into a REUSED dir must regenerate EXACTLY the current set -- a renamed ability reusing scriptId 256
    # must not leave two [BattleScript(256)] .cs behind (the persistent-dist duplicate-id compile bug).
    layout = ModLayout(tmp_path)
    ss.write_scripts(layout, [{"id": 256, "name": "Old", "template": "drain_hp"}])
    ss.write_scripts(layout, [{"id": 256, "name": "New", "template": "drain_mp"}])
    names = {p.name for p in layout.scripts_sources_dir.glob("*.cs")}
    assert names == {"0256_NewScript.cs"}                     # the stale 0256_OldScript.cs is gone


# ---- the parse + 256-band allocator (no install) ----------------------------------------------
def _iviv(abilities):
    return {"id": 12, "name": "Iviv", "borrow": "vivi",
            "abilities": {"preset": "custom", "command1": {"name": "Spark", "abilities": abilities}}}


def test_parse_allocates_script_id():
    specs = pl.parse_all([_iviv([
        "Blizzard",
        {"name": "Soul Leech", "from": "Fire", "power": 40, "script": {"template": "drain_hp"}},
    ])])
    seeds = pl.script_seeds(specs)
    assert seeds == [{"id": ad._CUSTOM_SCRIPT_MIN, "name": "Soul Leech", "template": "drain_hp"}]
    ca = next(a for a in pl.action_seeds(specs) if a["name"] == "Soul Leech")
    assert ca["script_id"] == ad._CUSTOM_SCRIPT_MIN            # the ability id (192) and scriptId (256) are decoupled
    assert ca["id"] == ad._CUSTOM_ACTION_MIN
    assert "script" not in ca["overrides"]                     # the table `script` is pulled out, not an override


def test_scalar_script_stays_data_only_override():
    specs = pl.parse_all([_iviv([{"name": "Weird", "from": "Fire", "script": 16}])])
    assert pl.script_seeds(specs) == []                        # a scalar scriptId mints nothing
    ca = next(a for a in pl.action_seeds(specs) if a["name"] == "Weird")
    assert ca["overrides"].get("script") == 16                 # it stays an ACTION_FIELDS override (existing formula)


def test_two_scripted_abilities_get_distinct_ids():
    specs = pl.parse_all([_iviv([
        {"name": "A", "from": "Fire", "script": {"template": "drain_hp"}},
        {"name": "B", "from": "Fire", "script": {"template": "drain_mp"}},
    ])])
    ids = sorted(s["id"] for s in pl.script_seeds(specs))
    assert ids == [ad._CUSTOM_SCRIPT_MIN, ad._CUSTOM_SCRIPT_MIN + 1]


def test_parse_body_channel():
    specs = pl.parse_all([_iviv([
        {"name": "Q", "from": "Fire", "script": {"body": "_v.Target.HpDamage = 1;"}},
    ])])
    assert pl.script_seeds(specs) == [{"id": ad._CUSTOM_SCRIPT_MIN, "name": "Q", "body": "_v.Target.HpDamage = 1;"}]


def test_parse_bad_template_raises():
    with pytest.raises(pl.PlayableError):
        pl.parse_all([_iviv([{"name": "X", "from": "Fire", "script": {"template": "nope"}}])])


def test_parse_empty_body_raises():
    with pytest.raises(pl.PlayableError):
        pl.parse_all([_iviv([{"name": "X", "from": "Fire", "script": {"body": ""}}])])


# ---- the full build: emit .cs, compile the DLL, repoint the Actions scriptId (install + csc gated) ----
BASE = """
[field]
id = 4003
name = "SCRIPTROOM"
area = 11
text_block = 1073

[camera]
pitch = 45

[walkmesh]
quad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]

[player]
spawn = [0, -300]
"""


def test_full_build_compiles_dll(tmp_path):
    """A scripted custom ability -> Sources/NNNN_*.cs + Memoria.Scripts.<Mod>.dll, with the Actions.csv row's
    scriptId repointed at the minted 256-band id. Skips cleanly without the FF9 install or a C# compiler."""
    from ff9mapkit.battle import scriptcompile
    toml = (BASE + '\n[[playable]]\nname = "Iviv"\nborrow = "vivi"\nrecruit = true\n'
            '\n[playable.abilities]\nmenu_from = "vivi"\n'
            '\n[playable.abilities.command1]\nname = "Spark"\n'
            'abilities = [{ name = "Soul Leech", from = "Fire", power = 40, element = ["Dark"], mp = 12, '
            'script = { template = "drain_hp" } }]\n')
    p = tmp_path / "f.field.toml"
    p.write_text(toml, encoding="utf-8")
    assert validate(FieldProject.load(p)) == []               # lint clean offline (validates the template name)
    if not scriptcompile.toolchain_available():
        pytest.skip("no C# compiler (csc) to build the mod formula DLL")
    out = tmp_path / "mod"
    try:
        build_mod([FieldProject.load(p)], out, mod_name="FF9CustomMap")
    except BuildError as ex:
        if "install" in str(ex).lower() or "managed" in str(ex).lower():
            pytest.skip("no FF9 install for the base CSVs / managed DLLs")
        raise
    layout = ModLayout(out)
    dll = layout.scripts_dll("FF9CustomMap")
    assert dll.exists() and dll.stat().st_size > 0            # the compiled mod formula DLL
    srcs = list(layout.scripts_sources_dir.glob("*.cs"))
    assert len(srcs) == 1 and srcs[0].name.endswith("Script.cs")
    # the Actions.csv row's scriptId (field 10) is repointed at the minted 256-band formula
    arow = next(l for l in layout.actions_csv.read_text(encoding="cp1252").splitlines()
                if l.startswith("Soul Leech;192;"))
    assert int(arow.split(";")[10]) == ad._CUSTOM_SCRIPT_MIN


def test_status_plus_script_warns(tmp_path):
    """`status = [...]` + a non-status-applying `script = {...}` on ONE ability -> a build WARNING (the minted
    formula won't inflict the status). The combo silently dropped the status before the fix. Install + csc gated."""
    from ff9mapkit.battle import scriptcompile
    toml = (BASE + '\n[[playable]]\nname = "Iviv"\nborrow = "vivi"\nrecruit = true\n'
            '\n[playable.abilities]\nmenu_from = "vivi"\n'
            '\n[playable.abilities.command1]\nname = "Spark"\n'
            'abilities = [{ name = "Soul Drain", from = "Bio", status = ["Silence"], rate = 60, '
            'script = { template = "drain_hp" } }]\n')
    p = tmp_path / "f.field.toml"
    p.write_text(toml, encoding="utf-8")
    if not scriptcompile.toolchain_available():
        pytest.skip("no C# compiler (csc) to build the mod formula DLL")
    out = tmp_path / "mod"
    try:
        info = build_mod([FieldProject.load(p)], out, mod_name="FF9CustomMap")
    except BuildError as ex:
        if "install" in str(ex).lower() or "managed" in str(ex).lower():
            pytest.skip("no FF9 install for the base CSVs / managed DLLs")
        raise
    assert any("won't APPLY it" in w for w in info.get("warnings", [])), info.get("warnings")


# ---- the lint-time toolchain gate (fail at lint, not mid-build; no install needed, csc mocked) ----------
def _scripted_toml():
    return (BASE + '\n[[playable]]\nname = "Iviv"\nborrow = "vivi"\nrecruit = true\n'
            '\n[playable.abilities]\nmenu_from = "vivi"\n'
            '\n[playable.abilities.command1]\nname = "Spark"\n'
            'abilities = [{ name = "Soul Leech", from = "Fire", power = 40, '
            'script = { template = "drain_hp" } }]\n')


def test_lint_gate_flags_missing_toolchain(tmp_path, monkeypatch):
    """A scripted custom ability with NO C# compiler must FAIL at lint (early + named), not mid-build. With a
    compiler present the same field lints clean of the toolchain error. Fully offline (no FF9 install / no real
    csc needed) -- toolchain_available is mocked both ways."""
    from ff9mapkit.battle import scriptcompile
    p = tmp_path / "f.field.toml"
    p.write_text(_scripted_toml(), encoding="utf-8")
    proj = FieldProject.load(p)

    monkeypatch.setattr(scriptcompile, "toolchain_available", lambda: False)
    rep = lint_all(proj)
    assert any("C# compiler" in e for e in rep.errors), rep.errors        # the gate fires -> a build-blocking error
    assert any("Soul Leech" in e for e in rep.errors)                     # and names the offending ability

    monkeypatch.setattr(scriptcompile, "toolchain_available", lambda: True)
    assert not any("C# compiler" in e for e in lint_all(proj).errors)     # a compiler present -> no toolchain error

    # the gate does NOT touch validate() -- it stays a pure schema check (so validate() == [] holds offline)
    assert validate(proj) == []


def test_lint_gate_silent_without_scripted_ability(tmp_path, monkeypatch):
    """The gate fires ONLY when the Scripts-DLL channel is actually used: a plain field and a DATA-only
    (scalar-``script``, existing-formula) custom ability must NOT get the toolchain error even with no compiler."""
    from ff9mapkit.battle import scriptcompile
    monkeypatch.setattr(scriptcompile, "toolchain_available", lambda: False)

    plain = tmp_path / "plain.field.toml"
    plain.write_text(BASE, encoding="utf-8")
    assert not any("C# compiler" in e for e in lint_all(FieldProject.load(plain)).errors)

    data_only = (BASE + '\n[[playable]]\nname = "Iviv"\nborrow = "vivi"\nrecruit = true\n'
                 '\n[playable.abilities]\nmenu_from = "vivi"\n'
                 '\n[playable.abilities.command1]\nname = "Spark"\n'
                 'abilities = [{ name = "Weird", from = "Fire", script = 16 }]\n')
    dp = tmp_path / "data.field.toml"
    dp.write_text(data_only, encoding="utf-8")
    assert not any("C# compiler" in e for e in lint_all(FieldProject.load(dp)).errors)
