"""Battle-calc TELEMETRY via the Scripts-DLL **Overload** channel (dev tool, not shipped content).

Memoria's per-mod ``Memoria.Scripts.<Mod>.dll`` can implement ``IOverload*`` interfaces -- engine choke points
that are OVERRIDE-ONLY and registered ONE implementer per interface per DLL (last-wins, silently). So the
interface plumbing lives in the kit-generated **Overload hub** (:mod:`overload`, ``Sources/Overload/``), and
this module is a plain STATIC feature class the hub calls at its splice points -- composable with other
Overload features (e.g. the declarative ``[difficulty]`` scaler, which the hub runs FIRST so the logged roster
shows the scaled stats the player actually fights). The events, one JSON line each:

- ``battle``  -- battle boundary + full unit roster (hub ``OnBattleInit``; the call site has no engine default).
- ``calc``    -- one per formula invocation, BOTH directions, before the formula runs (a calc with no matching
  ``result`` = miss/guard/no-effect -> hit rates fall out for free). The displaced engine default
  (backstab/weapon-element/kill-frozen) is transcribed VERBATIM in the hub, after this log call.
- ``result``  -- computed PRE-cap damage on the HIT branch, both directions (hub ``OnDamageFinalChanges``,
  after the verbatim reflect-multiplier default). The interface's other two methods' defaults ride the hub.
- ``applied`` -- post-``SetDamage`` numbers + target HP after. Engine quirk: the call site sits AFTER an early
  return when the target is a player, so ``applied`` exists only for enemy-targeted calcs -- join on
  ``result`` for both directions.

The JSONL lands at ``<game>/ff9mk_battle_telemetry.jsonl`` (anchored beside ``StreamingAssets``). Every log
call is wrapped in ``try/catch`` -- telemetry must NEVER break a battle. RELAUNCH-scoped like the whole
scripts channel (loaded once at title; F6 won't reload it).

Source placement: ``Scripts/Sources/Telemetry/`` -- a SIBLING of ``Sources/Battle`` so a field build's
``write_scripts`` wipe (which owns ``Sources/Battle`` only) never deletes it. The deploy-stickiness hole
(a fresh deploy copies a DLL compiled without the hook) is closed generically by ``deploy_field.py`` calling
:func:`overload.compile_live` whenever a live-owned feature is present (:func:`installed` feeds that probe).
"""
from __future__ import annotations

import json
from pathlib import Path

from .scriptcompile import ScriptCompileError  # noqa: F401  (re-exported for the CLI's error handling)

TELEMETRY_BASENAME = "9900_BattleTelemetry.cs"
JSONL_BASENAME = "ff9mk_battle_telemetry.jsonl"

# The feature class. Engine facts verified against the pinned Memoria source (6b8bb2d5); the IOverload*
# interfaces + the transcribed displaced defaults live in the hub (overload.py), not here -- this class is
# pure logging, callable from the hub's splice points.
_TELEMETRY_SOURCE = """\
// {basename} -- emitted by `ff9mapkit battle-telemetry` (kit {kit_version}). DEV TOOL, not shipped content.
// Logs every battle calc as one JSON line to <game>/{jsonl}. Remove with `ff9mapkit battle-telemetry --off`.
// A plain STATIC feature class: the engine hooks live in the kit-generated Overload hub
// (Sources/Overload/), which calls these Log* methods at its splice points -- after mutator features
// (e.g. [difficulty]), so the logged roster shows the stats the player actually fights. Every telemetry
// write is try/catch-swallowed -- it must never break a battle.
using System;
using System.IO;
using System.Text;
using Memoria;
using Memoria.Data;

namespace Memoria.Scripts.Telemetry
{{
    public static class BattleTelemetry
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

        // "battle" event: boundary + full roster. Called by the hub's OnBattleInit (no engine default there).
        public static void LogBattleInit()
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

        // "calc" event: one per calc, BEFORE the formula runs, both directions. A calc with no matching
        // "result" line = miss / guard / no-effect, so hit rates need no extra hook.
        public static void LogCalc(BattleCalculator v)
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
        }}

        // "result" event: COMPUTED (pre-cap) damage -- the hub calls this on the HIT branch for BOTH
        // directions, right after the verbatim reflect-multiplier default.
        public static void LogResult(BattleCalculator v)
        {{
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

        // "applied" event: APPLIED damage + target HP after application (enemy-targeted only -- the
        // engine's call-site quirk, see the hub).
        public static void LogApplied(BattleCalculator v)
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
    }}
}}
"""


def telemetry_source() -> str:
    """The C# feature-class source (kit-version-stamped header)."""
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


def install(mod_root, *, game=None) -> Path:
    """Write the feature source into the LIVE mod at ``mod_root`` and (re)compile the mod scripts DLL from
    ALL its sources via the Overload hub (existing battle formulas + features + the regenerated hub). The
    DLL name derives from the folder NAME (the ``FolderNames`` entry) -- a mismatch is silently never
    loaded, so it is not a parameter. Returns the DLL path. RELAUNCH to load (once at title, not F6)."""
    from ..config import ModLayout
    from . import overload
    mod_root = Path(mod_root)
    layout = ModLayout(root=mod_root)
    cs = telemetry_cs(layout)
    cs.parent.mkdir(parents=True, exist_ok=True)
    cs.write_text(telemetry_source(), encoding="utf-8", newline="\n")
    return overload.compile_live(mod_root, game=game)


def remove(mod_root, *, game=None) -> "Path | None":
    """Delete the feature source; recompile the DLL from the remaining sources (the hub regenerates without
    telemetry, or disappears too), or delete the DLL (+ its build stamp) when nothing remains. Returns the
    DLL path if one remains."""
    from ..config import ModLayout
    from . import overload
    mod_root = Path(mod_root)
    layout = ModLayout(root=mod_root)
    cs = telemetry_cs(layout)
    if cs.is_file():
        cs.unlink()
    return overload.compile_live(mod_root, game=game)


def recompile_live(mod_root, *, game=None) -> "Path | None":
    """Recompile the LIVE mod DLL from all live sources (hub regenerated) -- kept as a thin alias of
    :func:`overload.compile_live` for callers that reached telemetry directly."""
    from . import overload
    return overload.compile_live(mod_root, game=game)


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
