"""Emit the C# battle-formula sources for minted **scripted abilities** (the Scripts-DLL channel).

A ``[playable]`` custom ability with ``script = {template = "..."}`` (or ``script = {body = "<C#>"}``) gets a
genuinely NEW battle FORMULA the data path can't express -- a drain (damage + self-heal), an MP-drain, a
%-of-max-HP heal, or an arbitrary hand-written body. We render one ``NNNN_<Name>Script.cs`` per minted script
into ``layout.scripts_sources_dir``; :mod:`scriptcompile` compiles the folder into
``Memoria.Scripts.<Mod>.dll`` (loaded IN ADDITION to the base by the engine -- ``ScriptsLoader``), and the
Actions.csv row's ``scriptId`` (256+, allocated in :func:`content.playable.parse_all`) binds it at cast.
Proven end-to-end in-game 2026-07-07 (project-ff9-scripts-dll).

Each template is cloned **verbatim** from a shipped ``Sources/Battle/*.cs`` donor formula (the "learn from real
bytes" rule), so it can't crash the calc and it reads the ability's OWN tuning: ``NormalMagicParams()`` pulls
the Actions.csv ``power``/``element``/``mp`` you set on the same custom ability, so ``power = 40`` still tunes a
``drain_hp`` spell. The script id space (256+, the engine's ``BattleExtendedScripts`` dict floor) is INDEPENDENT
of the ability id (192-223).
"""
from __future__ import annotations

import re
import shutil


class ScriptSourceError(ValueError):
    pass


# template name -> the C# ``Perform()`` BODY, cloned verbatim from a live donor (column-0; re-indented on emit).
# Bodies call the engine's own calc verbs, so the ability's Actions.csv tuning (power/element/mp/targets) applies.
TEMPLATES: dict[str, str] = {
    # 0009 MagicAttackScript -- standard elemental magic damage (a baseline; mostly matches the data path, but a
    # useful starting point / parity check). Point `targets` at an enemy set.
    "magic_damage": """\
_v.NormalMagicParams();
_v.Caster.EnemyTranceBonusAttack();
_v.Caster.PenaltyMini();
_v.Target.PenaltyShellAttack();
_v.PenaltyCommandDividedAttack();
_v.BonusElement();

if (_v.CanAttackMagic())
{
    _v.CalcHpDamage();
    _v.TryAlterMagicStatuses();
}""",
    # 0016 DrainHpScript -- deal magic damage AND heal the caster for the same amount (the flagship: no data-only
    # Actions.csv edit can make a spell heal its caster). Point `targets` at an enemy.
    "drain_hp": """\
if (!_v.IsCasterNotTarget() || !_v.Target.CanBeAttacked())
    return;

_v.NormalMagicParams();
_v.Caster.EnemyTranceBonusAttack();
_v.Caster.PenaltyMini();
_v.Target.PenaltyShellAttack();
_v.PrepareHpDraining();
if (_v.Context.PowerDifference < 1)
    return;

_v.CalcHpDamage();
_v.Caster.HpDamage = _v.Target.HpDamage;""",
    # 0015 DrainMpScript -- Osmose/Absorb-MP: drain the target's MP to the caster. Point `targets` at an enemy.
    "drain_mp": """\
if (!_v.IsCasterNotTarget() || !_v.Target.CanBeAttacked())
    return;

_v.NormalMagicParams();
_v.Caster.EnemyTranceBonusAttack();
_v.Caster.PenaltyMini();
_v.Target.PenaltyShellAttack();
_v.Target.Flags |= CalcFlag.MpAlteration;
_v.Caster.Flags |= CalcFlag.MpAlteration;
_v.Context.IsDrain = true;

_v.CalcMpDamage();
Int32 damage = _v.Target.MpDamage;

if (_v.Target.IsZombie)
{
    _v.Target.Flags |= CalcFlag.MpRecovery;
    if (damage > _v.Caster.CurrentMp)
        damage = (Int32)_v.Caster.CurrentMp;
}
else
{
    _v.Caster.Flags |= CalcFlag.MpRecovery;
    if (damage > _v.Target.CurrentMp)
        damage = (Int32)_v.Target.CurrentMp;
}

_v.Target.MpDamage = damage;
_v.Caster.MpDamage = damage;""",
    # 0030 WhiteWindScript -- heal the target for a FRACTION of the caster's MAX HP (power = 0 -> 1/3; else
    # power%). A "share my vitality" heal no data path can express. Point `targets` at an ally set.
    "white_wind": """\
_v.Target.Flags |= CalcFlag.HpAlteration;

if (!_v.Target.IsZombie)
    _v.Target.Flags |= CalcFlag.HpRecovery;

if (_v.Command.Power == 0)
    _v.Target.HpDamage = (Int32)(_v.Caster.MaximumHp / 3);
else
    _v.Target.HpDamage = (Int32)(_v.Caster.MaximumHp * _v.Command.Power / 100);""",
}

# The source shell. Placeholders are sentinel tokens (not str.format) so C# braces in the body pass through
# untouched. namespace/attribute/interface match the shipped donors exactly (project-ff9-scripts-dll).
_SHELL = """\
using System;
using Memoria.Data;

namespace Memoria.Scripts.Battle
{
    /// <summary>ff9mapkit minted battle formula: __NAME__ (__TMPL__). See project-ff9-scripts-dll.</summary>
    [BattleScript(Id)]
    public sealed class __CLS__ : IBattleScript
    {
        public const Int32 Id = __ID__;

        private readonly BattleCalculator _v;

        public __CLS__(BattleCalculator v)
        {
            _v = v;
        }

        public void Perform()
        {
__BODY__
        }
    }
}
"""


# ---- FIELD ability effects (the [FieldAbilityScript] surface -- an OUT-OF-BATTLE effect, project-ff9-scripts-dll P7) ----
# A field script runs when an ability/item is used from the FIELD menu (SFieldCalculator.FieldCalcMain -> GetFieldAbilityScript
# by the action's Ref.ScriptId -> Apply(FieldCalculator)). The kit pairs one with a battle FORMULA at the SAME minted scriptId
# so a custom ability behaves BOTH in and out of combat. Each template is cloned VERBATIM from a shipped
# SFieldCalculator.DefaultFieldScript arm (Memoria C# source, MIT) -- so it can't crash the field calc and reads the ability's
# OWN Actions.csv tuning (e.g. `v.Action.Ref.Power`). The body's variable is `v` (the FieldCalculator), matching the donor.
# template name -> the C# ``Apply()`` BODY, transcribed from SFieldCalculator.cs (donor case + line cited).
FIELD_TEMPLATES: dict[str, str] = {
    # case 10 "Magic Recovery" (SFieldCalculator.cs:52-60) -- heal the target's HP (spell heal). Point `targets` at an ally.
    "field_heal_hp": """\
if (v.CanBeHealed(true, false))
{
    v.SetupSpellHeal();
    v.ApplyConcentrate();
    v.ApplyMultiTarget();
    v.HealHp();
}""",
    # case 12 "Magic Cure Status" (SFieldCalculator.cs:61-63) -- cure the ability's status set off the target.
    "field_cure_status": """\
v.CureActionStatuses();""",
    # case 13 "Revive" (SFieldCalculator.cs:64-67) -- revive a KO'd ally (spell revive).
    "field_revive": """\
if (v.CanBeRevived())
    v.ReviveSpell();""",
    # case 30 "White Wind" (SFieldCalculator.cs:84-92) -- heal a fraction of the CASTER's max HP (power 0 -> 1/3, else
    # power%). The natural PAIR for the battle `white_wind` formula (heals in AND out of combat).
    "field_white_wind": """\
if (v.CanBeHealed(true, false))
{
    if (v.Action.Ref.Power == 0)
        v.TargetRecoverHp = (Int32)v.Caster.max.hp / 3;
    else
        v.TargetRecoverHp = (Int32)v.Caster.max.hp * v.Action.Ref.Power / 100;
}""",
    # case 37 "Chakra" (SFieldCalculator.cs:93-98) -- heal HP + MP by a % of the TARGET's max.
    "field_chakra": """\
if (v.CanBeHealed(true, true))
{
    v.TargetRecoverHp = (Int32)v.Target.max.hp * v.Action.Ref.Power / 100;
    v.TargetRecoverMp = (Int32)v.Target.max.mp * v.Action.Ref.Power / 100;
}""",
}

# The FIELD source shell -- the [FieldAbilityScript] twin of _SHELL. namespace Memoria.Scripts.Field (walk-up finds the
# `Memoria`-namespace FieldAbilityScript/FieldAbilityScriptBase/FieldCalculator, IFieldScript.cs). Parameterless ctor (the
# loader instantiates via GetConstructor(Type.EmptyTypes), ScriptsLoader.cs:252); the override renames the param to `v` to
# match the donor arms verbatim. `using FF9` for the PLAYER data a body may touch; sentinel tokens keep C# braces intact.
_FIELD_SHELL = """\
using System;
using FF9;
using Memoria.Data;

namespace Memoria.Scripts.Field
{
    /// <summary>ff9mapkit minted FIELD ability effect: __NAME__ (__TMPL__). See project-ff9-scripts-dll.</summary>
    [FieldAbilityScript(Id)]
    public sealed class __CLS__ : FieldAbilityScriptBase
    {
        public const Int32 Id = __ID__;

        public override void Apply(FieldCalculator v)
        {
__BODY__
        }
    }
}
"""


# ---- STATUS behaviours (the [StatusScript] surface -- a new stateful ailment, project-ff9-scripts-dll P7) ----
# A status script runs on a unit's status LIFECYCLE (btl_stat: Apply on inflict, Remove on cure) + optional hook
# interfaces. The kit binds one to a CUSTOM status (BattleStatusId.CustomStatus1..31 = 33-63, the reserved band with
# its own 64-bit BattleStatus bit) and inflicts it via an ability's `status = [{table}]`. Each template is transcribed
# VERBATIM from a Memoria.DefaultScripts donor (MIT source), the donor's own BattleStatusId swapped for the minted
# CustomStatusN (__STATUS__). NOTE: per-tick `OnOpr` (IOprStatusScript) is engine-GATED to vanilla bits by the const
# BattleStatusConst.OprCount mask (btl_stat.cs:294) -> a custom DoT is NOT reachable; the viable hooks are Apply/Remove
# + OnDeath (IDeathChangerStatusScript) / OnATB (IAutoAttackStatusScript) / OnFigurePoint / OnFinishCommand, which
# dispatch off the applied-effects dict + an interface check (STAT_INFO.cs:9-10), not the OprCount mask.
# short hook name -> the marker interface a status script implements (OnOpr per-tick is omitted: engine-gated).
STATUS_HOOKS: dict[str, str] = {
    "death_changer": "IDeathChangerStatusScript",     # OnDeath() -- fires when the unit would die (e.g. auto-revive)
    "auto_attack": "IAutoAttackStatusScript",         # OnATB() -- fires when the ATB fills (e.g. a forced action)
    "figure_point": "IFigurePointStatusScript",       # OnFigurePoint() -- the damage-display hook
    "finish_command": "IFinishCommandScript",         # OnFinishCommand() -- when a command the unit ran ends
}

# A CustomStatusN has NO battle-HUD icon (BattleHUD.Buff/DebuffIconNames hardcode only the 24 vanilla statuses,
# BattleHUD.Const.cs:54-84). The engine's DictionaryPatch `BuffIcon`/`DebuffIcon <statusId> <spriteIndex>` directive
# sets those dicts at STARTUP (DataPatchers.PatchDictionaries), so a CustomStatusN can BORROW a vanilla status's sprite
# -> the icon shows EVERYWHERE it's read (the party status panel, the target/'hover' status, resists, results) since it
# registers before any battle. vanilla status name -> (BuffIcon/DebuffIcon, its FF9UIDataTool.IconSpriteName index).
_STATUS_ICON_DONORS: dict[str, tuple] = {
    "autolife": ("Buff", 131), "reflect": ("Buff", 132), "vanish": ("Buff", 133), "protect": ("Buff", 134),
    "shell": ("Buff", 135), "float": ("Buff", 136), "haste": ("Buff", 137), "regen": ("Buff", 138),
    "slow": ("Debuff", 139), "freeze": ("Debuff", 140), "heat": ("Debuff", 141), "mini": ("Debuff", 142),
    "sleep": ("Debuff", 143), "poison": ("Debuff", 144), "stop": ("Debuff", 145), "berserk": ("Debuff", 146),
    "confuse": ("Debuff", 147), "zombie": ("Debuff", 148), "trouble": ("Debuff", 149), "blind": ("Debuff", 150),
    "silence": ("Debuff", 151), "virus": ("Debuff", 152), "venom": ("Debuff", 153), "petrify": ("Debuff", 154),
}


def status_icon_directive(status_id: int, icon) -> "str | None":
    """A DictionaryPatch ``BuffIcon``/``DebuffIcon <statusId> <spriteIndex>`` line giving a custom status (id 33-63) a
    HUD icon by borrowing a vanilla status's sprite. Registered at STARTUP (DataPatchers), so it shows in the party
    panel, the target/'hover' status, resists + results. ``icon`` = a vanilla status name; ``None``/unknown -> None."""
    hit = _STATUS_ICON_DONORS.get(str(icon).strip().lower()) if icon else None
    return f"{hit[0]}Icon {status_id} {hit[1]}" if hit else None

# template name -> {hooks: [short names], body: the class-body methods}. Cloned from Memoria.DefaultScripts (donor +
# line cited); `__STATUS__` is replaced with the minted CustomStatusN so a body can reference its OWN status id.
STATUS_TEMPLATES: dict[str, dict] = {
    # AutoLifeStatusScript (DefaultStatus/AutoLifeStatusScript.cs) -- revive the unit once when it would die (OnDeath).
    # Inflict on an ally; when they hit 0 HP the status pops and restores them (default 1 HP).
    "auto_life": {"hooks": ["death_changer"], "icon": "AutoLife", "body": """\
public Int32 HPRestore = 1;

public override UInt32 Apply(BattleUnit target, BattleUnit inflicter, params Object[] parameters)
{
    base.Apply(target, inflicter, parameters);
    HPRestore = Math.Max(HPRestore, parameters.Length > 0 ? Convert.ToInt32(parameters[0]) : 1);
    return btl_stat.ALTER_SUCCESS;
}

public override Boolean Remove()
{
    return true;
}

public Boolean OnDeath()
{
    btl_stat.RemoveStatus(Target, BattleStatusId.__STATUS__);
    if (HPRestore > 0)
    {
        Target.CurrentHp = Math.Min((UInt32)HPRestore, Target.MaximumHp);
        btl_stat.RemoveStatus(Target, BattleStatusId.Death);
    }
    return true;
}"""},
    # BerserkStatusScript (DefaultStatus/BerserkStatusScript.cs) -- force an auto-Attack each turn (OnATB). Inflict on
    # a unit; it acts on its own (loses manual control) until cured.
    "auto_attack": {"hooks": ["auto_attack"], "icon": "Berserk", "body": """\
public override UInt32 Apply(BattleUnit target, BattleUnit inflicter, params Object[] parameters)
{
    base.Apply(target, inflicter, parameters);
    if (!target.CanUseTheAttackCommand)
        return btl_stat.ALTER_RESIST;
    return btl_stat.ALTER_SUCCESS;
}

public override Boolean Remove()
{
    btl_stat.StatusCommandCancel(Target);
    return true;
}

public Boolean OnATB()
{
    if (!Target.CanUseTheAttackCommand)
    {
        btl_stat.RemoveStatus(Target, BattleStatusId.__STATUS__);
        return false;
    }
    if (Target.IsPlayer)
        btl_cmd.SetCommand(Target.ATBCommand, BattleCommandId.Attack, (Int32)BattleAbilityId.Attack, btl_util.GetRandomBtlID(0), 0u);
    else
        btl_cmd.SetEnemyCommand(Target, BattleCommandId.EnemyAtk, Target.EnemyType.p_atk_no, btl_util.GetRandomBtlID(1));
    return true;
}"""},
}

# The STATUS source shell -- the [StatusScript] twin. namespace Memoria.Scripts.Status; the `Memoria`-namespace
# StatusScriptBase + the hook interfaces (IStatusScript.cs) resolve by walk-up; btl_stat/btl_cmd (FF9) via `using FF9`.
_STATUS_SHELL = """\
using System;
using FF9;
using Memoria.Data;
using Object = System.Object;

namespace Memoria.Scripts.Status
{
    /// <summary>ff9mapkit minted STATUS behaviour: __NAME__ (__TMPL__). See project-ff9-scripts-dll.</summary>
    [StatusScript(BattleStatusId.__STATUS__)]
    public sealed class __CLS__ : StatusScriptBase__INTERFACES__
    {
__BODY__
    }
}
"""


def _ident(name: str) -> str:
    """A safe C# identifier stem from an ability name (``"Soul Leech"`` -> ``"SoulLeech"``)."""
    s = re.sub(r"[^A-Za-z0-9]", "", str(name)) or "Custom"
    if not s[0].isalpha():
        s = "Ab" + s
    return s


def _indent(body: str, spaces: int = 12) -> str:
    pad = " " * spaces
    return "\n".join((pad + ln) if ln.strip() else "" for ln in body.strip("\n").splitlines())


def render_script(sid: int, name: str, *, template: str | None = None, body: str | None = None) -> tuple[str, str]:
    """Render ONE ``.cs`` -> ``(filename, source)``. Provide either a known ``template`` or a raw ``body``
    (the C# ``Perform()`` body). The class name embeds ``sid`` so two same-named abilities can't collide."""
    stem = _ident(name)
    cls = f"{stem}{sid}Script"
    if body is not None:
        if not isinstance(body, str) or not body.strip():
            raise ScriptSourceError(f"script.body for {name!r} must be a non-empty C# Perform() body")
        perform, tname = _indent(body), "body"
    else:
        if template not in TEMPLATES:
            raise ScriptSourceError(f"unknown script template {template!r} for {name!r} "
                                    f"(known: {', '.join(sorted(TEMPLATES))}; or use script.body = \"<C#>\")")
        perform, tname = _indent(TEMPLATES[template]), template
    safe_name = re.sub(r"[\r\n]+", " ", str(name)).replace("*/", "* /")   # keep the doc-comment 1-line + closed
    safe_name = re.sub(r"__(?:CLS|ID|NAME|TMPL|BODY)__", "", safe_name)   # a name can't smuggle in a shell sentinel
    src = (_SHELL.replace("__CLS__", cls).replace("__ID__", str(sid))
           .replace("__NAME__", safe_name).replace("__TMPL__", tname).replace("__BODY__", perform))
    return f"{sid:04d}_{stem}Script.cs", src


def render_field_script(sid: int, name: str, *, template: str | None = None, body: str | None = None) -> tuple[str, str]:
    """Render ONE FIELD-effect ``.cs`` -> ``(filename, source)`` (the [FieldAbilityScript] twin of
    :func:`render_script`). Provide a known field ``template`` or a raw ``body`` (the C# ``Apply()`` body). The
    class name embeds ``sid`` + a ``FieldScript`` suffix so it never collides with the paired battle ``Script`` at
    the SAME id (both register on id ``sid``, in different engine dicts)."""
    stem = _ident(name)
    cls = f"{stem}{sid}FieldScript"
    if body is not None:
        if not isinstance(body, str) or not body.strip():
            raise ScriptSourceError(f"field script.body for {name!r} must be a non-empty C# Apply() body")
        perform, tname = _indent(body), "body"
    else:
        if template not in FIELD_TEMPLATES:
            raise ScriptSourceError(f"unknown field script template {template!r} for {name!r} "
                                    f"(known: {', '.join(sorted(FIELD_TEMPLATES))}; or use field.body = \"<C#>\")")
        perform, tname = _indent(FIELD_TEMPLATES[template]), template
    safe_name = re.sub(r"[\r\n]+", " ", str(name)).replace("*/", "* /")   # keep the doc-comment 1-line + closed
    safe_name = re.sub(r"__(?:CLS|ID|NAME|TMPL|BODY)__", "", safe_name)   # a name can't smuggle in a shell sentinel
    src = (_FIELD_SHELL.replace("__CLS__", cls).replace("__ID__", str(sid))
           .replace("__NAME__", safe_name).replace("__TMPL__", tname).replace("__BODY__", perform))
    return f"{sid:04d}_{stem}FieldScript.cs", src


def render_status_script(status_id: int, name: str, status_enum: str, *, template: str | None = None,
                         body: str | None = None, hooks=None) -> tuple[str, str]:
    """Render ONE STATUS-behaviour ``.cs`` -> ``(filename, source)`` (the [StatusScript] twin). ``status_enum`` is
    the CustomStatusN enum name the script binds to (``[StatusScript(BattleStatusId.<status_enum>)]``) AND is
    substituted for ``__STATUS__`` in the body (so a body can reference its OWN status). Provide a known ``template``
    or a raw ``body`` + ``hooks`` (short hook names -> the marker interfaces). ``status_id`` (33-63) keeps the
    class/filename unique + distinct from the 256-band battle/field scripts. (The HUD icon is a separate
    DictionaryPatch line -- :func:`status_icon_directive` -- not part of the .cs.)"""
    stem = _ident(name)
    cls = f"{stem}{status_id}StatusScript"
    if body is not None:
        if not isinstance(body, str) or not body.strip():
            raise ScriptSourceError(f"status script.body for {name!r} must be a non-empty C# class-body")
        methods, tname, hook_list = body, "body", list(hooks or [])
    else:
        tmpl = STATUS_TEMPLATES.get(template)
        if tmpl is None:
            raise ScriptSourceError(f"unknown status template {template!r} for {name!r} "
                                    f"(known: {', '.join(sorted(STATUS_TEMPLATES))}; or use body = \"<C#>\" + hooks)")
        methods, tname, hook_list = tmpl["body"], template, list(tmpl["hooks"])
    bad = [h for h in hook_list if h not in STATUS_HOOKS]
    if bad:
        raise ScriptSourceError(f"status {name!r} unknown hook(s) {bad} (known: {', '.join(sorted(STATUS_HOOKS))})")
    interfaces = "".join(f", {STATUS_HOOKS[h]}" for h in hook_list)
    perform = _indent(methods.replace("__STATUS__", status_enum), spaces=8)   # __BODY__ sits at the class-member level
    safe_name = re.sub(r"[\r\n]+", " ", str(name)).replace("*/", "* /")
    safe_name = re.sub(r"__(?:CLS|ID|NAME|TMPL|BODY|STATUS|INTERFACES)__", "", safe_name)
    src = (_STATUS_SHELL.replace("__CLS__", cls).replace("__STATUS__", status_enum)
           .replace("__NAME__", safe_name).replace("__TMPL__", tname)
           .replace("__INTERFACES__", interfaces).replace("__BODY__", perform))
    return f"{status_id:04d}_{stem}StatusScript.cs", src


def write_scripts(layout, scripts, field_scripts=(), status_scripts=()) -> list:
    """Emit every minted ``.cs`` into ``layout.scripts_sources_dir``: battle FORMULAS (``scripts``), FIELD effects
    (``field_scripts``), and STATUS behaviours (``status_scripts``) -- from :func:`content.playable`'s
    ``script_seeds`` / ``field_script_seeds`` / ``status_script_seeds``. All go in ONE pass because the dir is WIPED
    first (a second call would clobber the first's output). Returns warnings (none today). Written UTF-8 / LF (Roslyn
    reads the encoding from the file; ASCII C# is encoding-agnostic)."""
    warnings: list = []
    d = layout.scripts_sources_dir
    # the Scripts sources are ENTIRELY kit-owned + regenerated every build -> WIPE first, so a rebuild into a
    # PERSISTENT out dir (campaign/journey/GUI `dist/`) can't accumulate a stale NNNN_*.cs from a renamed/removed
    # ability -- its old [BattleScript(<id>)] would duplicate a reused 256-band id and compile to two classes on the
    # same id (a build error, or a wrong/nondeterministic binding). The deploy_field test slot uses a fresh tmp dir
    # so it never hit this, but campaign/journey dist is persistent. ONE wipe covers battle + field + status (all below).
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    for s in scripts:
        fname, src = render_script(int(s["id"]), s["name"], template=s.get("template"), body=s.get("body"))
        (d / fname).write_text(src, encoding="utf-8", newline="\n")
    for s in field_scripts:
        fname, src = render_field_script(int(s["id"]), s["name"], template=s.get("template"), body=s.get("body"))
        (d / fname).write_text(src, encoding="utf-8", newline="\n")
    for s in status_scripts:
        fname, src = render_status_script(int(s["id"]), s["name"], s["status_enum"],
                                          template=s.get("template"), body=s.get("body"), hooks=s.get("hooks"))
        (d / fname).write_text(src, encoding="utf-8", newline="\n")
    return warnings
