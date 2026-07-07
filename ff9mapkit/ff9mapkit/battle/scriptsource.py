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


def write_scripts(layout, scripts) -> list:
    """Emit each minted script's ``.cs`` into ``layout.scripts_sources_dir``. ``scripts`` = a list of
    ``{id, name, template?/body?}`` (from :func:`content.playable.script_seeds`). Returns warnings (none today).
    Written UTF-8 / LF (Roslyn reads the encoding from the file; ASCII C# is encoding-agnostic)."""
    warnings: list = []
    d = layout.scripts_sources_dir
    # the Scripts sources are ENTIRELY kit-owned + regenerated every build -> WIPE first, so a rebuild into a
    # PERSISTENT out dir (campaign/journey/GUI `dist/`) can't accumulate a stale NNNN_*.cs from a renamed/removed
    # ability -- its old [BattleScript(<id>)] would duplicate a reused 256-band id and compile to two classes on the
    # same id (a build error, or a wrong/nondeterministic binding). The deploy_field test slot uses a fresh tmp dir
    # so it never hit this, but campaign/journey dist is persistent.
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    for s in scripts:
        fname, src = render_script(int(s["id"]), s["name"], template=s.get("template"), body=s.get("body"))
        (d / fname).write_text(src, encoding="utf-8", newline="\n")
    return warnings
