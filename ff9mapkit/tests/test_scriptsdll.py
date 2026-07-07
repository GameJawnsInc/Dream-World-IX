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
    st = scriptcompile.read_engine_stamp(dll)                 # the build stamped which engine it compiled against
    assert st is not None and "engine_file_version" in st and st.get("kit_version")
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


# ---- the engine-version stamp + drift warning (mocked; no install / no csc) ----------------------------
def test_engine_stamp_roundtrip_and_drift(tmp_path, monkeypatch):
    """The compile stamps the DLL with the installed engine's FileVersion; the drift check stays silent when the
    installed engine matches and WARNS (naming both versions) when it has moved."""
    from ff9mapkit.battle import scriptcompile as sc
    import ff9mapkit.memoria as mem
    dll = tmp_path / "Memoria.Scripts.FF9CustomMap.dll"
    dll.write_bytes(b"MZ")
    managed = tmp_path / "Managed"
    managed.mkdir()
    (managed / "Assembly-CSharp.dll").write_bytes(b"engine")

    monkeypatch.setattr(sc, "_managed_dir", lambda game=None: managed)
    monkeypatch.setattr(mem, "read_assembly_version", lambda p: "1.1.1000.1")
    sc._write_engine_stamp(dll, managed)
    stamp = sc.read_engine_stamp(dll)
    assert stamp and stamp["engine_file_version"] == "1.1.1000.1" and stamp["kit_version"]

    assert sc.engine_drift_warning(dll, game=None) is None                # installed == built -> quiet

    monkeypatch.setattr(mem, "read_assembly_version", lambda p: "1.1.2000.2")
    w = sc.engine_drift_warning(dll, game=None)                           # the engine moved -> drift
    assert w and "1.1.1000.1" in w and "1.1.2000.2" in w and "MissingMemberException" in w


def test_engine_drift_quiet_on_missing_data(tmp_path, monkeypatch):
    """Best-effort: no DLL / no stamp / a version-less stamp / an unresolvable install all stay silent (never a
    false alarm on missing data)."""
    from ff9mapkit.battle import scriptcompile as sc
    import ff9mapkit.memoria as mem
    assert sc.engine_drift_warning(tmp_path / "absent.dll", game=None) is None       # no DLL

    dll = tmp_path / "Memoria.Scripts.FF9CustomMap.dll"
    dll.write_bytes(b"MZ")
    assert sc.engine_drift_warning(dll, game=None) is None                            # no stamp sidecar

    managed = tmp_path / "Managed"
    managed.mkdir()
    (managed / "Assembly-CSharp.dll").write_bytes(b"x")
    monkeypatch.setattr(sc, "_managed_dir", lambda game=None: managed)
    monkeypatch.setattr(mem, "read_assembly_version", lambda p: None)                 # off-Windows / no version
    sc._write_engine_stamp(dll, managed)
    assert sc.read_engine_stamp(dll)["engine_file_version"] is None                   # a version-less stamp
    assert sc.engine_drift_warning(dll, game=None) is None                            # -> nothing to compare

    monkeypatch.setattr(mem, "read_assembly_version", lambda p: "1.1.9.9")
    sc._write_engine_stamp(dll, managed)

    def _boom(game=None):
        raise sc.ScriptCompileError("no install")
    monkeypatch.setattr(sc, "_managed_dir", _boom)
    assert sc.engine_drift_warning(dll, game=None) is None                            # can't resolve the install


# ---- P7: the FIELD-effect channel ([FieldAbilityScript], paired at the same scriptId) ------------------
def test_render_field_template_shape():
    fname, src = ss.render_field_script(256, "Lifewell", template="field_white_wind")
    assert fname == "0256_LifewellFieldScript.cs"                          # distinct from the battle 0256_LifewellScript.cs
    assert "public sealed class Lifewell256FieldScript : FieldAbilityScriptBase" in src
    assert "[FieldAbilityScript(Id)]" in src
    assert "public const Int32 Id = 256;" in src
    assert "public override void Apply(FieldCalculator v)" in src
    assert "namespace Memoria.Scripts.Field" in src
    assert "v.TargetRecoverHp" in src                                      # the white_wind field-heal body (donor case 30)


def test_render_field_body_and_errors():
    fname, src = ss.render_field_script(300, "Warp", body="v.TargetRecoverHp = (Int32)v.Target.max.hp;")
    assert fname == "0300_WarpFieldScript.cs" and "v.TargetRecoverHp = (Int32)v.Target.max.hp;" in src
    with pytest.raises(ss.ScriptSourceError):
        ss.render_field_script(256, "X", template="does_not_exist")
    with pytest.raises(ss.ScriptSourceError):
        ss.render_field_script(256, "X", body="   ")


def test_all_field_templates_render():
    for t in ss.FIELD_TEMPLATES:
        _, src = ss.render_field_script(256, "T", template=t)
        assert "public override void Apply(FieldCalculator v)" in src and "Memoria.Scripts.Field" in src


def test_write_scripts_battle_and_field_coexist(tmp_path):
    # a paired ability writes BOTH a battle Script.cs and a field FieldScript.cs at the SAME id, distinct files;
    # a rebuild with a different set WIPES both stale files (one wipe covers battle + field).
    layout = ModLayout(tmp_path)
    ss.write_scripts(layout, [{"id": 256, "name": "Lifewell", "template": "white_wind"}],
                     [{"id": 256, "name": "Lifewell", "template": "field_white_wind"}])
    names = {p.name for p in layout.scripts_sources_dir.glob("*.cs")}
    assert names == {"0256_LifewellScript.cs", "0256_LifewellFieldScript.cs"}
    ss.write_scripts(layout, [{"id": 256, "name": "New", "template": "drain_hp"}], [])
    assert {p.name for p in layout.scripts_sources_dir.glob("*.cs")} == {"0256_NewScript.cs"}


def test_parse_field_pairs_scriptid():
    specs = pl.parse_all([_iviv([
        {"name": "Lifewell", "from": "Cure",
         "script": {"template": "white_wind", "field": {"template": "field_white_wind"}}},
    ])])
    assert pl.script_seeds(specs) == [{"id": ad._CUSTOM_SCRIPT_MIN, "name": "Lifewell", "template": "white_wind"}]
    assert pl.field_script_seeds(specs) == [{"id": ad._CUSTOM_SCRIPT_MIN, "name": "Lifewell",
                                             "template": "field_white_wind"}]       # SAME id, field half split out


def test_field_requires_paired_battle_script():
    with pytest.raises(pl.PlayableError):                                  # script.field alone has no id to bind to
        pl.parse_all([_iviv([{"name": "X", "from": "Cure", "script": {"field": {"template": "field_heal_hp"}}}])])


def test_field_unknown_template_raises():
    with pytest.raises(pl.PlayableError):
        pl.parse_all([_iviv([{"name": "X", "from": "Cure",
                              "script": {"template": "white_wind", "field": {"template": "nope"}}}])])


def test_full_build_compiles_field_and_battle(tmp_path):
    """A paired battle+field scripted ability -> BOTH .cs compiled into the ONE Memoria.Scripts.<Mod>.dll, sharing
    the minted 256-band scriptId (so the ability behaves in AND out of combat). Skips without the install / csc."""
    from ff9mapkit.battle import scriptcompile
    toml = (BASE + '\n[[playable]]\nname = "Iviv"\nborrow = "vivi"\nrecruit = true\n'
            '\n[playable.abilities]\nmenu_from = "vivi"\n'
            '\n[playable.abilities.command1]\nname = "Spark"\n'
            'abilities = [{ name = "Lifewell", from = "Cure", '
            'script = { template = "white_wind", field = { template = "field_white_wind" } } }]\n')
    p = tmp_path / "f.field.toml"
    p.write_text(toml, encoding="utf-8")
    assert validate(FieldProject.load(p)) == []               # lint clean offline (validates both template names)
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
    assert dll.exists() and dll.stat().st_size > 0
    srcs = {s.name for s in layout.scripts_sources_dir.glob("*.cs")}
    assert any(n.endswith("FieldScript.cs") for n in srcs)    # the [FieldAbilityScript]
    assert any(n.endswith("Script.cs") and not n.endswith("FieldScript.cs") for n in srcs)   # the [BattleScript]
    arow = next(l for l in layout.actions_csv.read_text(encoding="cp1252").splitlines()
                if l.startswith("Lifewell;192;"))
    assert int(arow.split(";")[10]) == ad._CUSTOM_SCRIPT_MIN  # ONE scriptId binds both


# ---- P7: the STATUS-behaviour channel ([StatusScript] + a minted CustomStatusN + its StatusData row) ---
def test_render_status_template_shape():
    fn, src = ss.render_status_script(33, "Rebirth", "CustomStatus1", template="auto_life")
    assert fn == "0033_RebirthStatusScript.cs"
    assert "public sealed class Rebirth33StatusScript : StatusScriptBase, IDeathChangerStatusScript" in src
    assert "[StatusScript(BattleStatusId.CustomStatus1)]" in src
    assert "namespace Memoria.Scripts.Status" in src
    assert "public Boolean OnDeath()" in src
    assert "btl_stat.RemoveStatus(Target, BattleStatusId.CustomStatus1);" in src   # __STATUS__ substituted in the body
    assert "__STATUS__" not in src


def test_render_status_body_with_hooks():
    fn, src = ss.render_status_script(34, "Doomed", "CustomStatus2",
                                      body="public Boolean OnDeath() { return false; }", hooks=["death_changer"])
    assert fn == "0034_DoomedStatusScript.cs"
    assert ": StatusScriptBase, IDeathChangerStatusScript" in src and "return false;" in src
    with pytest.raises(ss.ScriptSourceError):
        ss.render_status_script(33, "X", "CustomStatus1", template="nope")
    with pytest.raises(ss.ScriptSourceError):
        ss.render_status_script(33, "X", "CustomStatus1", body="void F(){}", hooks=["not_a_hook"])


def test_all_status_templates_render():
    for t in ss.STATUS_TEMPLATES:
        _, src = ss.render_status_script(33, "T", "CustomStatus1", template=t)
        assert "[StatusScript(BattleStatusId.CustomStatus1)]" in src and "Memoria.Scripts.Status" in src


def test_encode_custom_status_names():
    from ff9mapkit.battle import battlecsv as bc
    assert bc.encode_status_list(["CustomStatus1"]) == "CustomStatus1(33)"
    assert bc.encode_status_list(["CustomStatus31"]) == "CustomStatus31(63)"        # top of the band
    assert bc.encode_status_list(["Silence", "CustomStatus1"]) == "Silence(3), CustomStatus1(33)"


def test_mint_status_data_row():
    # a synthetic base (no install): clone the column structure; behaviour neutralised, on-model visual off/inherited.
    cols = {"comment": 0, "id": 1, "oprcount": 2, "conticount": 3, "clearonapply": 4, "immunityprovided": 5,
            "spseffect": 6, "shpeffect": 7, "colorkind": 8, "colorpriority": 9, "colorbase": 10}
    rows = {0: ["Petrify", "0", "5", "0", "Venom", "Petrify", "3", "-1", "1", "2", "3", "# Petrify"],
            19: ["Haste", "19", "0", "40", "", "", "-1", "1", "-1", "0", "0", "# Haste"]}   # SHPEffect=1 (over-model)
    # no over_model -> a neutral base with the visual OFF (behaviour = [StatusScript], panel icon = the BuffIcon line)
    assert ad._mint_status_rows([{"id": 33, "name": "Rebirth"}], rows, cols) == [33]
    r = rows[33]
    assert r[cols["id"]] == "33" and r[cols["comment"]] == "Rebirth" and r[-1] == "# Rebirth"
    assert r[cols["oprcount"]] == "0" and r[cols["clearonapply"]] == "" and r[cols["shpeffect"]] == "-1"
    # over_model -> INHERIT that status's on-model visual (Haste's SHPEffect=1 = the over-model chevron), behaviour off
    ad._mint_status_rows([{"id": 34, "name": "Frenzy", "over_model": "Haste"}], rows, cols)
    assert rows[34][cols["shpeffect"]] == "1" and rows[34][cols["oprcount"]] == "0"
    with pytest.raises(ad.ActionDeltaError):                                         # out of the 33-63 band
        ad._mint_status_rows([{"id": 10, "name": "X"}], rows, cols)
    with pytest.raises(ad.ActionDeltaError):                                         # unknown over_model donor
        ad._mint_status_rows([{"id": 35, "name": "X", "over_model": "NotAStatus"}], rows, cols)


def _iviv_status(status):
    return {"id": 12, "name": "Iviv", "borrow": "vivi",
            "abilities": {"preset": "custom", "command1": {"name": "Spark", "abilities": [
                {"name": "Guardian", "from": "Cure", "status": status}]}}}


def test_parse_custom_status_allocates():
    specs = pl.parse_all([_iviv_status([{"name": "Rebirth", "template": "auto_life"}])])
    assert pl.status_script_seeds(specs) == [{"id": 33, "status_enum": "CustomStatus1", "name": "Rebirth",
                                              "template": "auto_life", "icon": "AutoLife"}]   # template default icon resolved
    assert pl.status_data_seeds(specs) == [{"id": 33, "name": "Rebirth", "over_model": "AutoLife"}]   # -> a StatusData row
    ca = next(a for a in pl.action_seeds(specs) if a["name"] == "Guardian")
    assert ca["status"] == ["CustomStatus1"]                                        # inflict list enriched
    assert any("CustomStatus1" in s["statuses"] for s in pl.status_set_seeds(specs))  # a StatusSets inflicts it


def test_status_string_and_table_mix():
    specs = pl.parse_all([_iviv_status(["Silence", {"name": "Rebirth", "template": "auto_life"}])])
    ca = next(a for a in pl.action_seeds(specs) if a["name"] == "Guardian")
    assert ca["status"] == ["Silence", "CustomStatus1"]                             # string kept + custom appended
    assert len(pl.status_script_seeds(specs)) == 1


def test_custom_status_errors():
    with pytest.raises(pl.PlayableError):
        pl.parse_all([_iviv_status([{"name": "X", "template": "nope"}])])           # unknown template
    with pytest.raises(pl.PlayableError):
        pl.parse_all([_iviv_status([{"template": "auto_life"}])])                   # needs a name
    with pytest.raises(pl.PlayableError):
        pl.parse_all([_iviv_status([{"name": "X", "body": "void F(){}", "hooks": ["nope"]}])])  # bad hook


def test_full_build_compiles_status(tmp_path):
    """A custom-status ability -> a [StatusScript] .cs compiled into the DLL + a minted StatusData row (33-63) + a
    StatusSets row inflicting CustomStatus1. Skips without the install / csc."""
    from ff9mapkit.battle import scriptcompile
    toml = (BASE + '\n[[playable]]\nname = "Iviv"\nborrow = "vivi"\nrecruit = true\n'
            '\n[playable.abilities]\nmenu_from = "vivi"\n'
            '\n[playable.abilities.command1]\nname = "Spark"\n'
            'abilities = [{ name = "Guardian", from = "Cure", '
            'status = [{ name = "Rebirth", template = "auto_life" }] }]\n')
    p = tmp_path / "f.field.toml"
    p.write_text(toml, encoding="utf-8")
    assert validate(FieldProject.load(p)) == []               # lint clean offline (validates the status template)
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
    assert dll.exists() and dll.stat().st_size > 0            # the [StatusScript] compiled into the DLL
    assert any(s.name.endswith("StatusScript.cs") for s in layout.scripts_sources_dir.glob("*.cs"))
    sd = layout.status_data_csv.read_text(encoding="cp1252")  # a StatusData row minted at the custom band (33)
    assert any(l.split(";")[1].strip() == "33" for l in sd.splitlines() if ";" in l and not l.startswith("#"))
    assert "CustomStatus1(33)" in layout.status_sets_csv.read_text(encoding="cp1252")   # a StatusSets inflicts it
    assert "BuffIcon 33 131" in layout.dictionary_patch.read_text(encoding="utf-8")     # the custom-status HUD icon


def test_status_icon_directive():
    assert ss.status_icon_directive(33, "AutoLife") == "BuffIcon 33 131"     # borrow AutoLife's buff sprite
    assert ss.status_icon_directive(34, "Berserk") == "DebuffIcon 34 146"    # a debuff -> DebuffIcon
    assert ss.status_icon_directive(33, "Regen") == "BuffIcon 33 138"
    assert ss.status_icon_directive(33, None) is None                       # no icon -> no line
    assert ss.status_icon_directive(33, "NotAStatus") is None               # unknown donor -> no line
    # the .cs itself carries NO icon code (the icon is a DictionaryPatch line, registered at startup for every consumer)
    _, src = ss.render_status_script(33, "Rebirth", "CustomStatus1", template="auto_life")
    assert "BattleHUD" not in src and "static " not in src


def test_status_power_knob():
    # auto_life revives at power% of max HP (default 50); an override flows into the emitted C#
    _, d = ss.render_status_script(33, "R", "CustomStatus1", template="auto_life")
    assert "Target.MaximumHp * 50 / 100" in d and "__POWER__" not in d
    _, d2 = ss.render_status_script(33, "R", "CustomStatus1", template="auto_life", power=25)
    assert "Target.MaximumHp * 25 / 100" in d2
    # parse carries `power` into the seed + validates it (integer 1-100)
    specs = pl.parse_all([_iviv_status([{"name": "Rebirth", "template": "auto_life", "power": 30}])])
    assert pl.status_script_seeds(specs)[0]["power"] == 30
    for bad in (0, 101, 50.0, True):
        with pytest.raises(pl.PlayableError):
            pl.parse_all([_iviv_status([{"name": "X", "template": "auto_life", "power": bad}])])


def test_status_icon_directive_lines():
    # a template's default icon -> a BuffIcon line (auto_life borrows AutoLife = sprite 131)
    specs = pl.parse_all([_iviv_status([{"name": "Rebirth", "template": "auto_life"}])])
    assert pl.status_icon_directive_lines(specs) == ["BuffIcon 33 131"]
    assert pl.status_script_seeds(specs)[0]["icon"] == "AutoLife"            # the template default resolved
    # an explicit icon override wins (Regen = sprite 138)
    specs2 = pl.parse_all([_iviv_status([{"name": "Rebirth", "template": "auto_life", "icon": "Regen"}])])
    assert pl.status_icon_directive_lines(specs2) == ["BuffIcon 33 138"]
    with pytest.raises(pl.PlayableError):                                    # a bad icon donor fails lint
        pl.parse_all([_iviv_status([{"name": "X", "template": "auto_life", "icon": "Nope"}])])
