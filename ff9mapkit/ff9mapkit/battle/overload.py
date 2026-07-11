"""The Overload-channel COORDINATOR: one hub class per mod DLL, features as plain static classes.

Engine fact (pinned 6b8bb2d5, ``ScriptsLoader.ProcessType``): Memoria registers ``IOverload*`` implementations
into a ``Dictionary<Type, Type>`` keyed BY INTERFACE -- within one DLL the LAST-processed type silently wins an
interface, and ``Assembly.GetTypes()`` order is unspecified. So exactly ONE class per interface may exist across
a mod's sources, or behavior is nondeterministic. This module makes that structural: features (battle telemetry,
``[difficulty]``, ``[rebalance]``, ``[deathrules]``) are PLAIN STATIC classes with no interfaces, and the
kit regenerates a single ``Sources/Overload/0000_OverloadHub.cs`` -- the only ``IOverload*`` implementer --
composing them at hand-authored splice points (mutators before observers, so telemetry's roster log shows
difficulty-scaled stats). VOID hooks compose any number of features; a RETURNING hook (OnGameOver -> the
cancel-the-game-over verdict) is SINGLE-OWNER -- the hub returns the one owning feature's expression. Where a hook displaces an engine inline "// Default method", the hub carries the
VERBATIM transcription (moved here from the in-game-proven telemetry source).

Every compile of the mod scripts DLL funnels through :func:`compile_tree` / :func:`compile_live`: refresh the
kit-owned feature sources -> regenerate (or remove) the hub -> refuse foreign ``IOverload*`` implementers that
would collide -> compile ALL sources. The build (``build._emit_scripts``), the telemetry CLI, and the deploy
stickiness step all share this one path. RELAUNCH-scoped like the whole channel (DLL loads once at title).
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from .scriptcompile import ScriptCompileError, compile_sources, _stamp_path

HUB_DIRNAME = "Overload"
HUB_BASENAME = "0000_OverloadHub.cs"

# hook method -> the engine interface that carries it (interface granularity: claiming OnDamageFinalChanges
# forces the whole IOverloadDamageModifierScript, so the hub emits its other two methods' defaults too).
_HOOK_IFACE = {
    "OnBattleInit": "IOverloadOnBattleInitScript",
    "OnBattleScriptStart": "IOverloadOnBattleScriptStartScript",
    "OnBattleScriptEnd": "IOverloadOnBattleScriptEndScript",
    "OnDamageFinalChanges": "IOverloadDamageModifierScript",
    "OnGameOver": "IOverloadOnGameOverScript",
}

# RETURNING hooks: the engine acts on the hook's return value (OnGameOver: true = cancel the game over), so
# two features can't both decide -- the hook is SINGLE-OWNER (render_hub enforces it) and the registry value
# is a C# EXPRESSION the hub returns, not a spliced statement. UnitCheckPoint (-> BattleStatus) joins here
# when its feature lands.
RETURNING_HOOKS = frozenset({"OnGameOver"})

# The feature registry. Each entry:
#   dir/file   -- Sources/<dir>/<file>; the file's PRESENCE marks the feature active (the deploy probe).
#   order      -- splice order within a hook slot: MUTATORS (scale stats) before OBSERVERS (log them).
#   live_owned -- True = installed into the LIVE mod by a CLI tool (survives deploys via the stickiness
#                 recompile); False = BUILD-owned declarative content (rides the built DLL; deploy REPLACES it).
#   hooks      -- {hook method: the C# the hub emits (fully qualified, so the hub needs no usings)}. For a
#                 VOID hook the value is a spliced STATEMENT (any number compose, in order); for a RETURNING
#                 hook (RETURNING_HOOKS) it is the EXPRESSION the hub returns -- one owner only.
#   render     -- optional zero-arg callable returning the CURRENT kit's source text; compile paths re-render
#                 it so a live file left by an older kit is refreshed (the old telemetry .cs implemented the
#                 interfaces itself -- re-rendering is what upgrades it past the collision gate).
def _telemetry_render() -> str:
    from . import telemetry
    return telemetry.telemetry_source()


FEATURES = (
    {
        "name": "difficulty",
        "dir": "Difficulty",
        "file": "9800_Difficulty.cs",
        "order": 10,                     # mutator: scales enemy stats before observers read them
        "live_owned": False,
        "hooks": {"OnBattleInit": "Memoria.Scripts.Overload.DifficultyOverload.OnBattleInit();"},
        "render": None,                  # knobs are baked from [difficulty] at build time -- not re-renderable
    },
    {
        "name": "rebalance",
        "dir": "Rebalance",
        "file": "9700_Rebalance.cs",
        "order": 20,                     # mutator: scales the final HP damage before observers log it
        "live_owned": False,
        "hooks": {"OnDamageFinalChanges": "Memoria.Scripts.Overload.RebalanceOverload.OnDamageFinalChanges(v);"},
        "render": None,                  # knobs are baked from [rebalance] at build time -- not re-renderable
    },
    {
        "name": "deathrules",
        "dir": "DeathRules",
        "file": "9600_DeathRules.cs",
        "order": 30,                     # after the stat/damage mutators; owns the RETURNING OnGameOver verdict
        "live_owned": False,
        "hooks": {
            "OnBattleInit": "Memoria.Scripts.Overload.DeathRulesOverload.OnBattleInit();",
            # RETURNING hook: an EXPRESSION, not a statement -- the hub emits `return <this>;`
            "OnGameOver": "Memoria.Scripts.Overload.DeathRulesOverload.OnGameOver(state, dyingPC)",
        },
        "render": None,                  # knobs are baked from [deathrules] at build time -- not re-renderable
    },
    {
        "name": "telemetry",
        "dir": "Telemetry",
        "file": "9900_BattleTelemetry.cs",
        "order": 90,                     # observer: logs AFTER mutators (the roster event shows scaled stats)
        "live_owned": True,
        "hooks": {
            "OnBattleInit": "Memoria.Scripts.Telemetry.BattleTelemetry.LogBattleInit();",
            "OnBattleScriptStart": "Memoria.Scripts.Telemetry.BattleTelemetry.LogCalc(v);",
            "OnDamageFinalChanges": "Memoria.Scripts.Telemetry.BattleTelemetry.LogResult(v);",
            "OnBattleScriptEnd": "Memoria.Scripts.Telemetry.BattleTelemetry.LogApplied(v);",
        },
        "render": _telemetry_render,
    },
)


def feature_cs(layout, feat: dict) -> Path:
    """``…/Scripts/Sources/<dir>/<file>`` for a registry entry."""
    return layout.scripts_dir / "Sources" / feat["dir"] / feat["file"]


def hub_cs(layout) -> Path:
    return layout.scripts_dir / "Sources" / HUB_DIRNAME / HUB_BASENAME


def active_features(layout) -> list:
    """Registry entries whose source file is present in this layout, in splice order."""
    return sorted((f for f in FEATURES if feature_cs(layout, f).is_file()), key=lambda f: f["order"])


def has_live_extras(layout) -> bool:
    """True when a LIVE-owned feature (e.g. battle telemetry) is installed in this mod -- the deploy
    stickiness probe: a freshly copied build DLL lacks it, so deploy must recompile from all live sources."""
    return any(f["live_owned"] for f in active_features(layout))


def live_extras(layout) -> list:
    """The LIVE-owned features installed in this mod (deploy's message + probe detail)."""
    return [f for f in active_features(layout) if f["live_owned"]]


def build_owned_dirs() -> tuple:
    """``Sources/`` subdir names the BUILD owns: deploy REPLACES these in the live mod (a stale live copy
    would resurrect removed declarative content at the next live recompile), while LIVE-owned feature dirs
    (telemetry) survive a deploy untouched."""
    return ("Battle",) + tuple(f["dir"] for f in FEATURES if not f["live_owned"]) + (HUB_DIRNAME,)


def flag_expr_cs(flag_index: int) -> str:
    """The bare C# CONDITION testing a save-backed ``gEventGlobal`` bit (true = set) -- the same bit math as
    :func:`flag_gate_cs`, for a feature that can't early-return on a clear flag because its VANILLA path must
    still run then (e.g. [deathrules] keeps the transcribed Eiko default alive while the rule sleeps)."""
    byte, mask = flag_index >> 3, 1 << (flag_index & 7)
    return f"(FF9StateSystem.EventState.gEventGlobal[{byte}] & {mask}) != 0"


def flag_gate_cs(flag_index, *, label: str = "", indent: str = " " * 16) -> str:
    """The shared C# early-return gate a flag-gateable feature emits at the TOP of its hook body: run only
    while a save-backed ``gEventGlobal`` BIT is set (a "hard mode" the author toggles via [startup]/an event
    /F6 -> Flags). ``flag_index`` None -> ``""`` (always-on, no gate). Sits inside the feature's own
    try/catch, so an out-of-range index throws -> caught -> vanilla. ``label`` is the author's raw flag
    spelling (wrapped in parens for the comment when it differs from the index). Cross-feature: both
    [difficulty] and [rebalance] emit an identical gate, so the codegen lives here once."""
    if flag_index is None:
        return ""
    lbl = f" ({label})" if label and label != str(flag_index) else ""
    byte, mask = flag_index >> 3, 1 << (flag_index & 7)
    return (f"{indent}// hard-mode gate: scale only while gEventGlobal bit {flag_index} is set{lbl}\n"
            f"{indent}Byte[] g = FF9StateSystem.EventState.gEventGlobal;\n"
            f"{indent}if ((g[{byte}] & {mask}) == 0)\n"
            f"{indent}    return;\n")


# ---- the hub C# ----------------------------------------------------------------------------------------

_HUB_HEADER = """\
// {basename} -- REGENERATED by ff9mapkit (kit {kit_version}) on every scripts compile; DO NOT EDIT.
// The ONE class implementing this mod's engine Overload hooks. Memoria registers overloads BY INTERFACE
// (ScriptsLoader.ProcessType, a last-wins dict) -- so exactly one implementer may exist per interface per
// DLL. Features are plain static classes; this hub composes them (mutators before observers). Where a hook
// displaces an engine inline default, the default is transcribed VERBATIM (marked) so gameplay is unchanged.
// Active features: {features}.
using System;
using Memoria;
using Memoria.Data;

namespace Memoria.Scripts.Overload
{{
    public sealed class OverloadHub : {interfaces}
    {{
{methods}
    }}
}}
"""

# Per-hook method templates. __CALLS__ is the splice point; its POSITION is semantic (before/after the
# verbatim default) and hand-authored per hook -- do not generalize it away.
_M_ONBATTLEINIT = """\
        // Battle boundary: right after every BattleUnit is initialised. No engine default (pure addition).
        public void OnBattleInit()
        {
__CALLS__
        }"""

_M_ONBATTLESCRIPTSTART = """\
        // One hook per calc, BEFORE the formula runs (both directions). Feature calls first, then the
        // engine default -- its early returns must stay LAST so observers always see the calc.
        public Boolean OnBattleScriptStart(BattleCalculator v)
        {
__CALLS__
            // ---- engine default, transcribed VERBATIM from SBattleCalculator.CalcMain ("Default method") ----
            // (Engine quirk at the call site, NOT ours: on a `true` return the engine skips its
            //  BattleVoice.CurrentCalc=null reset that the inline default paths perform -- harmless,
            //  CurrentCalc is reassigned at the next calc.)
            if (Configuration.Battle.CustomBattleFlagsMeaning == 1)
            {
                if (v.Command.IsShortRange)
                {
                    v.BonusBackstabAndPenaltyLongDistanceVisually();
                    if ((v.Command.AbilityCategory & 8) != 0 && v.Target.IsUnderAnyStatus(BattleStatus.Vanish)) // Is Physical
                        v.Context.Flags |= BattleCalcFlags.Miss;
                }
                if ((v.Command.AbilityType & 0x10) != 0 && v.Caster.IsPlayer) // Use weapon properties
                    v.ApplyElementFullStack(v.Caster.WeaponElement, v.Caster.WeaponElement);
                if ((v.Context.Flags & (BattleCalcFlags.Miss | BattleCalcFlags.Guard)) != 0)
                    return true;
            }
            if ((v.Command.AbilityCategory & 8) != 0 && v.Target.TryKillFrozen()) // Is Physical
                return true;
            return false;
        }"""

_M_ONDAMAGEFINALCHANGES = """\
        // The last write to HpDamage on the HIT branch, both directions, PRE-9999-cap. Default first
        // (reflect multiplier), then feature calls -- observers read the post-reflect number.
        public void OnDamageFinalChanges(BattleCalculator v)
        {
            // ---- engine default, transcribed VERBATIM from SBattleCalculator.DamageFinalChanges (private) ----
            if (v.Target.Flags != 0)
            {
                Int32 reflectMultiplier = v.Command.GetReflectMultiplierOnTarget(v.Target.Id);
                if ((v.Target.Flags & CalcFlag.HpAlteration) != 0)
                    v.Target.HpDamage *= reflectMultiplier;
                if ((v.Target.Flags & CalcFlag.MpAlteration) != 0)
                    v.Target.MpDamage *= reflectMultiplier;
            }
__CALLS__
        }

        public void OnDamageModifierChange(BattleCalculator v, Int32 previousValue, Int32 bonus)
        {
            // (CalcContext.DamageModifierCount setter "Default method": x1.5 per step up, /2 per step down)
            if (bonus >= 0)
                for (Int32 i = 0; i < bonus; i++)
                    v.Context.Attack = v.Context.Attack * 3 >> 1;
            else
                for (Int32 i = 0; i < -bonus; i++)
                    v.Context.Attack >>= 1;
        }

        public void OnDamageDrasticReduction(BattleCalculator v)
        {
            v.Context.Attack = 1; // (CalcContext.DecreaseAttackDrastically "Default method")
        }"""

_M_ONBATTLESCRIPTEND = """\
        // Tail of CalcResult (no engine default). Call-site quirk (theirs): sits after an early return when
        // the TARGET is a player, so it fires for enemy-targeted calcs only.
        public void OnBattleScriptEnd(BattleCalculator v)
        {
__CALLS__
        }"""

# RETURNING-hook template: __OWNER__ is the ONE owning feature's verdict expression. No verbatim engine
# default here -- when no feature owns the interface the hub doesn't implement it at all (the engine's
# inline default runs untouched), and when one does, reproducing the displaced default is the FEATURE's
# job (it decides how much of it to keep).
_M_ONGAMEOVER = """\
        // Game-over boundary (btl_sys.CheckBattlePhase: the LAST player just went down). RETURNING hook,
        // single-owner: the owning feature's verdict is the return value -- true = CANCEL the game over
        // (the engine skips its defeat tail: SEQ_MENU_OFF_DEFEAT + "Annihilated" + menu-off +
        // KillAllCommand), false = the defeat proceeds. Claiming this interface DISPLACES the engine
        // default (Eiko's automatic Rebirth Flame, btl_sys.cs "Default method") -- the feature transcribes
        // whatever part of it it keeps.
        public Boolean OnGameOver(FF9StateBattleSystem state, BattleUnit dyingPC)
        {
            try { return __OWNER__; } catch { }
            return false; // fail-safe: the vanilla defeat runs (canceling with no revive queued would stall)
        }"""

_HOOK_TEMPLATES = {
    "OnBattleInit": _M_ONBATTLEINIT,
    "OnBattleScriptStart": _M_ONBATTLESCRIPTSTART,
    "OnDamageFinalChanges": _M_ONDAMAGEFINALCHANGES,
    "OnBattleScriptEnd": _M_ONBATTLESCRIPTEND,
    "OnGameOver": _M_ONGAMEOVER,
}

# fixed emission order (stable output; interface list + method order deterministic)
_HOOK_ORDER = ("OnBattleInit", "OnBattleScriptStart", "OnDamageFinalChanges", "OnBattleScriptEnd",
               "OnGameOver")


def hub_interfaces(features) -> list:
    """The engine interfaces the hub must implement for these features, in emission order."""
    claimed = {h for f in features for h in f["hooks"]}
    seen: list = []
    for h in _HOOK_ORDER:
        if h in claimed and _HOOK_IFACE[h] not in seen:
            seen.append(_HOOK_IFACE[h])
    return seen


def render_hub(features) -> "str | None":
    """The hub C# for these active features, or ``None`` when no feature claims a hook (no hub -> the
    engine's inline defaults run untouched, exactly like a mod with no Overload content)."""
    from .. import __version__
    features = sorted(features, key=lambda f: f["order"])
    ifaces = hub_interfaces(features)
    if not ifaces:
        return None
    methods = []
    for hook in _HOOK_ORDER:
        if _HOOK_IFACE[hook] not in ifaces:
            continue
        owners = [f for f in features if hook in f["hooks"]]
        if hook in RETURNING_HOOKS:
            # the engine acts on the return value -- two features can't both decide, so refuse loudly
            # (the registry is kit-owned, but this is the invariant a future feature must not break)
            if len(owners) > 1:
                raise ScriptCompileError(
                    f"Overload hook {hook} RETURNS a verdict, so it is single-owner -- but "
                    f"{', '.join(f['name'] for f in owners)} all claim it. One feature must own a "
                    f"returning hook; compose behaviors inside that feature instead.")
            methods.append(_HOOK_TEMPLATES[hook].replace("__OWNER__", owners[0]["hooks"][hook]))
            continue
        calls = [f["hooks"][hook] for f in owners]
        # each spliced call is try/catch-wrapped: a feature must never break a battle, even if its own
        # guards are missing (belt and suspenders -- the feature bodies swallow too)
        spliced = "\n".join(f"            try {{ {c} }} catch {{ }}" for c in calls)
        methods.append(_HOOK_TEMPLATES[hook].replace("__CALLS__", spliced))
    return _HUB_HEADER.format(
        basename=HUB_BASENAME, kit_version=__version__,
        features=", ".join(f["name"] for f in features) or "none",
        interfaces=", ".join(ifaces), methods="\n\n".join(methods))


def write_hub(layout) -> list:
    """Refresh the kit-owned Overload sources in this layout: re-render every active feature that has a
    renderer (upgrades a live file left by an older kit), then regenerate ``Sources/Overload/`` -- or REMOVE
    it when no feature is active (the engine defaults then run inline, untouched). Returns the active
    registry entries (splice order)."""
    feats = active_features(layout)
    for f in feats:
        if f["render"] is not None:
            feature_cs(layout, f).write_text(f["render"](), encoding="utf-8", newline="\n")
    hub = hub_cs(layout)
    src = render_hub(feats)
    if src is None:
        shutil.rmtree(hub.parent, ignore_errors=True)
    else:
        hub.parent.mkdir(parents=True, exist_ok=True)
        hub.write_text(src, encoding="utf-8", newline="\n")
    return feats


# ---- the collision gate --------------------------------------------------------------------------------

_IFACE_TOKEN = re.compile(r"\bIOverload\w*Script\b")
_LINE_COMMENT = re.compile(r"//[^\n]*")


def check_interface_collisions(sources, hub_path) -> None:
    """Refuse a source tree where a NON-hub ``.cs`` implements (or names, comments stripped) an ``IOverload*``
    interface that would collide -- either with the hub or with another foreign source. The engine registers
    per-interface last-wins with UNSPECIFIED type order, so a collision is a silent coin flip; failing the
    compile with names is the honest behavior. Kit-emitted feature classes are plain statics (no interface
    tokens), so this only fires on hand-dropped C# or a stale pre-hub kit file the renderer couldn't refresh."""
    hub_path = Path(hub_path)
    hub_ifaces = set()
    if hub_path.is_file():
        hub_ifaces = set(_IFACE_TOKEN.findall(_LINE_COMMENT.sub("", hub_path.read_text(encoding="utf-8"))))
    by_iface: dict = {}
    for s in sources:
        s = Path(s)
        if s == hub_path:
            continue
        text = _LINE_COMMENT.sub("", s.read_text(encoding="utf-8", errors="replace"))
        for tok in set(_IFACE_TOKEN.findall(text)):
            by_iface.setdefault(tok, []).append(s.name)
    problems = []
    for iface, files in sorted(by_iface.items()):
        if iface in hub_ifaces:
            problems.append(f"{iface}: {', '.join(files)} collides with the kit's {HUB_BASENAME}")
        elif len(files) > 1:
            problems.append(f"{iface}: implemented by more than one source ({', '.join(files)})")
    if problems:
        raise ScriptCompileError(
            "Overload interface collision -- the engine registers ONE implementer per IOverload* interface "
            "per DLL (last-wins, silently), so this tree would behave nondeterministically:\n  "
            + "\n  ".join(problems)
            + "\nRemove the conflicting .cs (kit features belong to the hub: telemetry via `ff9mapkit "
              "battle-telemetry`, difficulty via [difficulty]), or keep a hand-written hook only for an "
              "interface the hub does not implement.")


# ---- the one compile path ------------------------------------------------------------------------------

def all_sources(layout) -> list:
    """Every ``.cs`` under the mod's ``Scripts/Sources`` (Battle formulas + features + the hub), sorted."""
    d = layout.scripts_dir / "Sources"
    return sorted(d.glob("**/*.cs")) if d.is_dir() else []


def compile_tree(layout, mod_name: str, *, game=None) -> "Path | None":
    """THE compile path for a mod scripts DLL: refresh feature sources + the hub (:func:`write_hub`), gate
    foreign ``IOverload*`` implementers, compile ALL sources -> ``layout.scripts_dll(mod_name)``. An EMPTY
    tree deletes the DLL (+ its build stamp) and returns ``None`` -- a fully de-scripted mod ships no DLL."""
    write_hub(layout)
    srcs = all_sources(layout)
    out_dll = layout.scripts_dll(mod_name)
    if not srcs:
        for p in (out_dll, _stamp_path(out_dll)):
            if p.is_file():
                p.unlink()
        return None
    check_interface_collisions(srcs, hub_cs(layout))
    compile_sources(srcs, out_dll, game=game)
    return out_dll


def compile_live(mod_root, *, game=None) -> "Path | None":
    """:func:`compile_tree` against a LIVE mod folder (DLL name derives from the folder name -- the
    ``FolderNames`` entry). The deploy-stickiness hook and the telemetry install/remove path."""
    from ..config import ModLayout
    mod_root = Path(mod_root)
    return compile_tree(ModLayout(root=mod_root), mod_root.name, game=game)
