"""Battle-calc TELEMETRY via the Scripts-DLL **Overload** channel (dev tool, not shipped content).

Memoria's per-mod ``Memoria.Scripts.<Mod>.dll`` can implement ``IOverload*`` interfaces -- engine choke points
that are OVERRIDE-ONLY: a registered implementation replaces the engine's inline "// Default method" at the
call site (``ScriptsLoader.ProcessType`` walks ``GetInterfaces()``; no attribute). This module emits ONE C#
class implementing four of them to log every battle calc as a JSON line, then compiles it into the LIVE mod
folder's scripts DLL:

- ``IOverloadOnBattleInitScript``      -- battle boundary + full unit roster (pure addition, no default).
- ``IOverloadOnBattleScriptStartScript`` -- one ``calc`` event per formula invocation, BOTH directions, before
  the formula runs (a calc with no matching ``result`` = miss/guard/no-effect -> hit rates fall out for free).
  Displaces a real default (backstab/weapon-element/kill-frozen) -- transcribed VERBATIM below.
- ``IOverloadDamageModifierScript``    -- ``OnDamageFinalChanges`` = the last write to HpDamage on the HIT
  branch, both directions -> the ``result`` event (computed, PRE-cap damage). The interface's other two
  methods carry transcribed defaults (x1.5 stack / Attack=1).
- ``IOverloadOnBattleScriptEndScript`` -- the ``applied`` event (post-``SetDamage`` numbers + target HP after).
  Engine quirk: its call site sits AFTER an early return when the target is a player
  (``SBattleCalculator.cs``), so ``applied`` exists only for enemy-targeted calcs -- join on ``result`` for
  both directions.

The JSONL lands at ``<game>/ff9mk_battle_telemetry.jsonl`` (anchored beside ``StreamingAssets``). Every log
call is wrapped in ``try/catch`` -- telemetry must NEVER break a battle. RELAUNCH-scoped like the whole
scripts channel (loaded once at title; F6 won't reload it).

Source placement: ``Scripts/Sources/Telemetry/`` -- a SIBLING of ``Sources/Battle`` so a field build's
``write_scripts`` wipe (which owns ``Sources/Battle`` only) never deletes it. The stickiness hole is the
DEPLOY: ``deploy_field.py`` copies a freshly-built DLL compiled from the build's ``Sources/Battle`` alone,
which would silently drop the hook -- so deploy recompiles the live DLL WITH telemetry when it sees the
Telemetry source (:func:`installed` / :func:`recompile_live`).

Why the transcription is safe: the displaced defaults are engine code I copied line-for-line (marked in the
C#); the ONE known behavioral edge is the engine's own override-path quirk -- when ``OnBattleScriptStart``
returns true the engine skips its ``BattleVoice.CurrentCalc = null`` reset (vanilla default paths null it) --
harmless (reassigned at the next calc), documented here so nobody re-diagnoses it.
"""
from __future__ import annotations

import json
from pathlib import Path

from .scriptcompile import ScriptCompileError, compile_sources

TELEMETRY_BASENAME = "9900_BattleTelemetry.cs"
JSONL_BASENAME = "ff9mk_battle_telemetry.jsonl"

# The hook. Engine facts verified against the pinned Memoria source (6b8bb2d5):
# - the 4 interfaces + registration: Memoria/Scripts/ScriptsLoader.cs:343-365 (interface-keyed, override-only);
# - OnBattleScriptStart default transcribed from SBattleCalculator.CalcMain:74-99 ("Default method");
# - OnDamageFinalChanges default from SBattleCalculator.DamageFinalChanges:374-383 (PRIVATE there -> transcribed);
# - OnDamageModifierChange / OnDamageDrasticReduction defaults from CalcContext.cs:58-70 / :82-83;
# - OnBattleScriptEnd + OnBattleInit call sites have NO default (pure tail hooks).
_TELEMETRY_SOURCE = """\
// {basename} -- emitted by `ff9mapkit battle-telemetry` (kit {kit_version}). DEV TOOL, not shipped content.
// Logs every battle calc as one JSON line to <game>/{jsonl}. Remove with `ff9mapkit battle-telemetry --off`.
// Where a hook displaces an engine inline default, the default is transcribed VERBATIM (marked) so gameplay
// is unchanged. Every telemetry write is try/catch-swallowed -- it must never break a battle.
using System;
using System.IO;
using System.Text;
using Memoria;
using Memoria.Data;

namespace Memoria.Scripts.Telemetry
{{
    public sealed class BattleTelemetry : IOverloadOnBattleInitScript, IOverloadOnBattleScriptStartScript,
        IOverloadOnBattleScriptEndScript, IOverloadDamageModifierScript
    {{
        private static StreamWriter _writer;
        private static Int64 _battle;
        private static Int64 _calc;

        private static void Emit(String json)
        {{
            try
            {{
                if (_writer == null)
                {{
                    String dir = null;
                    try {{ dir = Path.GetDirectoryName(AssetManagerUtil.GetStreamingAssetsPath()); }} catch {{ }}
                    String path = String.IsNullOrEmpty(dir) ? "{jsonl}" : Path.Combine(dir, "{jsonl}");
                    _writer = new StreamWriter(path, true, new UTF8Encoding(false)) {{ AutoFlush = true }};
                }}
                _writer.WriteLine(json);
            }}
            catch {{ }}
        }}

        private static String Esc(String s)
        {{
            if (String.IsNullOrEmpty(s))
                return String.Empty;
            StringBuilder b = new StringBuilder(s.Length + 8);
            foreach (Char c in s)
            {{
                if (c == '"' || c == '\\\\') {{ b.Append('\\\\'); b.Append(c); }}
                else if (c < ' ') b.Append(' ');
                else b.Append(c);
            }}
            return b.ToString();
        }}

        private static void AppendUnit(StringBuilder b, BattleUnit u)
        {{
            b.Append("{{\\"id\\":").Append(u.Id);
            b.Append(",\\"name\\":\\"").Append(Esc(u.Name)).Append('"');
            b.Append(",\\"player\\":").Append(u.IsPlayer ? "true" : "false");
            b.Append(",\\"lv\\":").Append(u.Level);
            b.Append(",\\"hp\\":").Append(u.CurrentHp).Append(",\\"maxhp\\":").Append(u.MaximumHp);
            b.Append(",\\"mp\\":").Append(u.CurrentMp).Append(",\\"maxmp\\":").Append(u.MaximumMp);
            b.Append('}}');
        }}

        // Battle boundary: right after every BattleUnit is initialised. No engine default (pure addition).
        public void OnBattleInit()
        {{
            try
            {{
                _battle++;
                StringBuilder b = new StringBuilder(512);
                b.Append("{{\\"e\\":\\"battle\\",\\"b\\":").Append(_battle);
                b.Append(",\\"t\\":\\"").Append(DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")).Append('"');
                b.Append(",\\"field\\":").Append(FF9StateSystem.Common.FF9.fldMapNo);
                b.Append(",\\"scene\\":").Append(FF9StateSystem.Battle.battleMapIndex);
                b.Append(",\\"units\\":[");
                Boolean first = true;
                foreach (BattleUnit u in BattleState.EnumerateUnits())
                {{
                    if (!first)
                        b.Append(',');
                    first = false;
                    AppendUnit(b, u);
                }}
                b.Append("]}}");
                Emit(b.ToString());
            }}
            catch {{ }}
        }}

        // One event per calc, BEFORE the formula runs, both directions. A calc with no matching
        // "result" line = miss / guard / no-effect, so hit rates need no extra hook.
        public Boolean OnBattleScriptStart(BattleCalculator v)
        {{
            try
            {{
                _calc++;
                StringBuilder b = new StringBuilder(384);
                b.Append("{{\\"e\\":\\"calc\\",\\"b\\":").Append(_battle).Append(",\\"c\\":").Append(_calc);
                b.Append(",\\"script\\":").Append(v.Command.ScriptId);
                b.Append(",\\"cmd\\":").Append((Int32)v.Command.Id);
                b.Append(",\\"ability\\":\\"").Append(Esc(v.Command.AbilityName)).Append('"');
                b.Append(",\\"power\\":").Append(v.Command.Power);
                b.Append(",\\"caster\\":");
                AppendUnit(b, v.Caster);
                b.Append(",\\"target\\":");
                AppendUnit(b, v.Target);
                b.Append('}}');
                Emit(b.ToString());
            }}
            catch {{ }}
            // ---- engine default, transcribed VERBATIM from SBattleCalculator.CalcMain ("Default method") ----
            // (Engine quirk at the call site, NOT ours: on a `true` return the engine skips its
            //  BattleVoice.CurrentCalc=null reset that the inline default paths perform -- harmless,
            //  CurrentCalc is reassigned at the next calc.)
            if (Configuration.Battle.CustomBattleFlagsMeaning == 1)
            {{
                if (v.Command.IsShortRange)
                {{
                    v.BonusBackstabAndPenaltyLongDistanceVisually();
                    if ((v.Command.AbilityCategory & 8) != 0 && v.Target.IsUnderAnyStatus(BattleStatus.Vanish)) // Is Physical
                        v.Context.Flags |= BattleCalcFlags.Miss;
                }}
                if ((v.Command.AbilityType & 0x10) != 0 && v.Caster.IsPlayer) // Use weapon properties
                    v.ApplyElementFullStack(v.Caster.WeaponElement, v.Caster.WeaponElement);
                if ((v.Context.Flags & (BattleCalcFlags.Miss | BattleCalcFlags.Guard)) != 0)
                    return true;
            }}
            if ((v.Command.AbilityCategory & 8) != 0 && v.Target.TryKillFrozen()) // Is Physical
                return true;
            return false;
        }}

        // COMPUTED (pre-cap) damage -- fires on the HIT branch for BOTH directions, right before the
        // 9999-cap / SetDamage application.
        public void OnDamageFinalChanges(BattleCalculator v)
        {{
            // ---- engine default, transcribed VERBATIM from SBattleCalculator.DamageFinalChanges (private) ----
            if (v.Target.Flags != 0)
            {{
                Int32 reflectMultiplier = v.Command.GetReflectMultiplierOnTarget(v.Target.Id);
                if ((v.Target.Flags & CalcFlag.HpAlteration) != 0)
                    v.Target.HpDamage *= reflectMultiplier;
                if ((v.Target.Flags & CalcFlag.MpAlteration) != 0)
                    v.Target.MpDamage *= reflectMultiplier;
            }}
            try
            {{
                StringBuilder b = new StringBuilder(256);
                b.Append("{{\\"e\\":\\"result\\",\\"b\\":").Append(_battle).Append(",\\"c\\":").Append(_calc);
                b.Append(",\\"hpDmg\\":").Append(v.Target.HpDamage);
                b.Append(",\\"mpDmg\\":").Append(v.Target.MpDamage);
                b.Append(",\\"flags\\":").Append((Int32)v.Target.Flags);
                b.Append(",\\"ctxFlags\\":").Append((Int32)v.Context.Flags);
                b.Append(",\\"crit\\":").Append((v.Target.Flags & CalcFlag.Critical) != 0 ? "true" : "false");
                b.Append(",\\"heal\\":").Append((v.Target.Flags & CalcFlag.HpRecovery) != 0 ? "true" : "false");
                b.Append('}}');
                Emit(b.ToString());
            }}
            catch {{ }}
        }}

        // APPLIED damage + target HP after application. Engine quirk: the call site sits after an early
        // return when the TARGET is a player, so this fires for enemy-targeted calcs only. Pure tail hook
        // (no engine default to reproduce).
        public void OnBattleScriptEnd(BattleCalculator v)
        {{
            try
            {{
                StringBuilder b = new StringBuilder(192);
                b.Append("{{\\"e\\":\\"applied\\",\\"b\\":").Append(_battle).Append(",\\"c\\":").Append(_calc);
                b.Append(",\\"hpDmg\\":").Append(v.Target.HpDamage);
                b.Append(",\\"mpDmg\\":").Append(v.Target.MpDamage);
                b.Append(",\\"tHp\\":").Append(v.Target.CurrentHp);
                b.Append(",\\"flags\\":").Append((Int32)v.Target.Flags);
                b.Append('}}');
                Emit(b.ToString());
            }}
            catch {{ }}
        }}

        // ---- IOverloadDamageModifierScript's other two methods: engine defaults transcribed VERBATIM ----
        public void OnDamageModifierChange(BattleCalculator v, Int32 previousValue, Int32 bonus)
        {{
            // (CalcContext.DamageModifierCount setter "Default method": x1.5 per step up, /2 per step down)
            if (bonus >= 0)
                for (Int32 i = 0; i < bonus; i++)
                    v.Context.Attack = v.Context.Attack * 3 >> 1;
            else
                for (Int32 i = 0; i < -bonus; i++)
                    v.Context.Attack >>= 1;
        }}

        public void OnDamageDrasticReduction(BattleCalculator v)
        {{
            v.Context.Attack = 1; // (CalcContext.DecreaseAttackDrastically "Default method")
        }}
    }}
}}
"""


def telemetry_source() -> str:
    """The C# hook source (kit-version-stamped header)."""
    from .. import __version__
    return _TELEMETRY_SOURCE.format(basename=TELEMETRY_BASENAME, kit_version=__version__, jsonl=JSONL_BASENAME)


def telemetry_dir(layout) -> Path:
    """``…/Scripts/Sources/Telemetry`` -- a SIBLING of ``Sources/Battle`` so the field build's
    ``write_scripts`` wipe (which owns Battle only) never deletes the hook."""
    return layout.scripts_dir / "Sources" / "Telemetry"


def telemetry_cs(layout) -> Path:
    return telemetry_dir(layout) / TELEMETRY_BASENAME


def installed(layout) -> bool:
    """True when the telemetry SOURCE is present in this mod (the deploy-stickiness probe)."""
    return telemetry_cs(layout).is_file()


def _all_sources(layout) -> list:
    """Every ``.cs`` under the mod's ``Scripts/Sources`` (Battle formulas + Telemetry), sorted."""
    d = layout.scripts_dir / "Sources"
    return sorted(d.glob("**/*.cs")) if d.is_dir() else []


def install(mod_root, *, game=None) -> Path:
    """Write the hook source into the LIVE mod at ``mod_root`` and (re)compile the mod scripts DLL from ALL
    its sources (existing battle formulas + telemetry). The DLL name derives from the folder NAME (the
    ``FolderNames`` entry) -- a mismatch is silently never loaded, so it is not a parameter.
    Returns the DLL path. RELAUNCH to load (once at title, not F6)."""
    from ..config import ModLayout
    mod_root = Path(mod_root)
    layout = ModLayout(root=mod_root)
    cs = telemetry_cs(layout)
    cs.parent.mkdir(parents=True, exist_ok=True)
    cs.write_text(telemetry_source(), encoding="utf-8", newline="\n")
    out_dll = layout.scripts_dll(mod_root.name)
    compile_sources(_all_sources(layout), out_dll, game=game)
    return out_dll


def remove(mod_root, *, game=None) -> "Path | None":
    """Delete the hook source; recompile the DLL from the remaining battle-formula sources, or delete the
    DLL (+ its build stamp) when telemetry was the only content. Returns the DLL path if one remains."""
    from ..config import ModLayout
    from .scriptcompile import _stamp_path
    mod_root = Path(mod_root)
    layout = ModLayout(root=mod_root)
    cs = telemetry_cs(layout)
    if cs.is_file():
        cs.unlink()
    remaining = _all_sources(layout)
    out_dll = layout.scripts_dll(mod_root.name)
    if remaining:
        compile_sources(remaining, out_dll, game=game)
        return out_dll
    for p in (out_dll, _stamp_path(out_dll)):
        if p.is_file():
            p.unlink()
    return None


def recompile_live(mod_root, *, game=None) -> Path:
    """Recompile the LIVE mod DLL from all live sources -- the deploy-stickiness hook: a field deploy copies
    a DLL compiled from the build's ``Sources/Battle`` alone, silently dropping the telemetry hook; deploy
    calls this when :func:`installed` to fold it back in."""
    from ..config import ModLayout
    mod_root = Path(mod_root)
    layout = ModLayout(root=mod_root)
    out_dll = layout.scripts_dll(mod_root.name)
    compile_sources(_all_sources(layout), out_dll, game=game)
    return out_dll


# ---- the read side: parse + summarize the captured JSONL (the balance-analyzer seed) --------------------

_TEXT_TAG = None  # compiled lazily


def strip_text_tags(name: str) -> str:
    """Strip FF9 text-markup tags from a captured name (enemy names come through the engine's ``Name`` as the
    raw tagged string, e.g. ``[STRT=27,1]Fang[ENDN]``). Report-side only -- the JSONL keeps the faithful raw."""
    global _TEXT_TAG
    if _TEXT_TAG is None:
        import re
        _TEXT_TAG = re.compile(r"\[[0-9A-Za-z]+(?:=[^\]]*)?\]")
    return _TEXT_TAG.sub("", name or "").strip()


def default_jsonl_path(game=None) -> Path:
    """Where the hook writes: ``<game>/ff9mk_battle_telemetry.jsonl`` (beside StreamingAssets)."""
    from ..config import find_game_path
    return find_game_path(game) / JSONL_BASENAME


def read_events(path) -> list:
    """Parse the JSONL into event dicts. Malformed lines (a crash-truncated tail) are SKIPPED, not fatal."""
    events = []
    p = Path(path)
    if not p.is_file():
        return events
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if isinstance(ev, dict):
            events.append(ev)
    return events


def join_calcs(events) -> list:
    """Join per-calc events by calc id ``c``: each row = the ``calc`` dict + ``result`` (computed damage,
    both directions; absent = miss/guard/no-effect) + ``applied`` (post-cap, enemy-targeted only)."""
    rows = {}
    for ev in events:
        kind = ev.get("e")
        if kind == "calc":
            rows[ev.get("c")] = {"calc": ev, "result": None, "applied": None}
        elif kind in ("result", "applied"):
            row = rows.get(ev.get("c"))
            if row is not None:
                row[kind] = ev
    return [rows[c] for c in sorted(k for k in rows if k is not None)]


def summarize(events) -> str:
    """A per-ability / per-unit balance summary of a telemetry capture -- the analyzer v1."""
    battles = [ev for ev in events if ev.get("e") == "battle"]
    rows = join_calcs(events)
    if not battles and not rows:
        return "no telemetry events (fight a battle with the hook installed, then re-run)"
    out = [f"battles: {len(battles)}   calcs: {len(rows)}"]
    if battles:
        fields = sorted({ev.get("field") for ev in battles})
        scenes = sorted({ev.get("scene") for ev in battles})
        out.append(f"fields: {', '.join(str(f) for f in fields)}   battle scenes: {', '.join(str(s) for s in scenes)}")

    by_ability: dict = {}
    dealt: dict = {}
    taken: dict = {}
    for row in rows:
        calc, result = row["calc"], row["result"]
        name = strip_text_tags(calc.get("ability") or "") or f"cmd {calc.get('cmd')}"
        st = by_ability.setdefault(name, {"casts": 0, "hits": 0, "crits": 0, "dmg": []})
        st["casts"] += 1
        if result is not None:
            st["hits"] += 1
            if result.get("crit"):
                st["crits"] += 1
            hp = result.get("hpDmg") or 0
            if hp and not result.get("heal"):
                st["dmg"].append(hp)
                caster, target = calc.get("caster") or {}, calc.get("target") or {}
                cname = strip_text_tags(caster.get("name", "")) or "?"
                tname = strip_text_tags(target.get("name", "")) or "?"
                dealt[cname] = dealt.get(cname, 0) + hp
                taken[tname] = taken.get(tname, 0) + hp

    if by_ability:
        out.append("")
        out.append(f"{'ability':<24} {'casts':>5} {'hit%':>5} {'crit%':>5} {'dmg mean':>9} {'min':>6} {'max':>6}")
        for name in sorted(by_ability, key=lambda n: -by_ability[n]["casts"]):
            st = by_ability[name]
            hitp = 100.0 * st["hits"] / st["casts"] if st["casts"] else 0.0
            critp = 100.0 * st["crits"] / st["hits"] if st["hits"] else 0.0
            if st["dmg"]:
                mean, lo, hi = sum(st["dmg"]) / len(st["dmg"]), min(st["dmg"]), max(st["dmg"])
                out.append(f"{name:<24.24} {st['casts']:>5} {hitp:>4.0f}% {critp:>4.0f}% {mean:>9.1f} {lo:>6} {hi:>6}")
            else:
                out.append(f"{name:<24.24} {st['casts']:>5} {hitp:>4.0f}% {critp:>4.0f}% {'-':>9} {'-':>6} {'-':>6}")
    if dealt:
        out.append("")
        out.append("damage dealt (computed, pre-cap): "
                   + "  ".join(f"{n} {v}" for n, v in sorted(dealt.items(), key=lambda kv: -kv[1])))
    if taken:
        out.append("damage taken (computed, pre-cap): "
                   + "  ".join(f"{n} {v}" for n, v in sorted(taken.items(), key=lambda kv: -kv[1])))
    return "\n".join(out)
