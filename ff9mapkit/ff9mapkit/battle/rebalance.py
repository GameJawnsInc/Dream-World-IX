"""Declarative ``[rebalance]`` -- a global HP-damage multiplier (the Overload channel's second
shipped-content feature; sibling to ``[difficulty]``).

A field.toml (one per mod) declares::

    [rebalance]
    player_damage = 1.5   # x HP damage DEALT BY players (make the party hit harder)
    enemy_damage = 0.75   # x HP damage dealt by enemies (soften incoming hits)
    flag = "hard_mode"    # OPTIONAL gate: scale only while this gEventGlobal BIT is set
                          # (a [[flag]] name or a bit index; omit = always on)

The build renders it into a plain static C# class (``Sources/Rebalance/9700_Rebalance.cs``) the Overload hub
calls at ``OnDamageFinalChanges`` -- the LAST write to ``HpDamage`` before the engine applies it (both
directions, hit branch). The scale is chosen by the CASTER: player-caster damage x ``player_damage``,
enemy-caster damage x ``enemy_damage``. Only PURE HP damage is touched (``HpAlteration`` set,
``HpRecovery`` clear) -- healing/recovery/MP are left alone.

**Relationship to ``[difficulty]`` (they compose, differently):** ``[difficulty]`` scales enemy STATS at
battle init (Strength/Magic feed the whole damage formula, ENEMIES only, with variance + defense
interaction). ``[rebalance]`` is a flat post-formula multiplier on the final number, works in BOTH
directions -- so it is the only way to scale what the PARTY deals. Use difficulty to make enemies tankier/
tougher; use rebalance to dial the raw damage numbers up or down predictably.

**The 9999 cap (honest limit):** the hook fires PRE-cap, and the engine clamps ``HpDamage`` to
``MaxDamageLimit`` (9999 by default) right after -- UNLESS the player set ``[Battle] BreakDamageLimit = 1``
in Memoria.ini. So a multiplier reads through below 9999 and is clamped above it; exceeding 9999 needs that
engine toggle (the kit does NOT force a global engine config from a mod hook). Also, if the ``IsDmg9999``
settings cheat is on, PLAYER damage is forced to 9999 by the engine after this hook regardless of the scale.

Engine facts (pinned 6b8bb2d5): ``BattleUnit.HpDamage`` is a settable ``Int32``; ``BattleUnit.IsPlayer`` /
``.Flags`` (``CalcFlag.HpAlteration`` / ``.HpRecovery``) are public; ``FF9StateSystem.EventState.gEventGlobal``
is a public ``Byte[2048]``. The whole body is try/catch-swallowed -- a rebalance bug degrades to VANILLA
damage, never a broken battle. RELAUNCH-scoped like the whole scripts channel.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from .. import flags as _flags

REBALANCE_BASENAME = "9700_Rebalance.cs"

# same authoring band as [difficulty]: 0.05x (a 20x nerf) .. 20x. Outside is almost certainly a typo.
SCALE_MIN, SCALE_MAX = 0.05, 20.0
_SCALE_KEYS = ("player_damage", "enemy_damage")
_KNOWN_KEYS = _SCALE_KEYS + ("flag",)
_FLAG_MAX = 2048 * 8 - 1                          # gEventGlobal is Byte[2048] -> bit indices 0..16383
# clamp the scaled damage to a sane ceiling (avoids Int32 overflow when BreakDamageLimit lifts the 9999 cap
# and a huge multiplier lands on a big hit); mirrors the difficulty HP clamp.
_DAMAGE_CEIL = 9999999


class RebalanceError(ValueError):
    pass


@dataclass(frozen=True)
class RebalanceSpec:
    player: float = 1.0
    enemy: float = 1.0
    flag: "int | None" = None       # resolved gEventGlobal bit index (gate), or None = always on
    flag_label: str = ""            # the author's spelling, for the emitted C# comment


def parse_table(table, *, name_map: "dict | None" = None) -> RebalanceSpec:
    """Validate + resolve a raw ``[rebalance]`` table. Raises :class:`RebalanceError` with an authoring-facing
    message; ``name_map`` is the project's ``[[flag]]`` name->index registry (for ``flag = "name"``)."""
    if not isinstance(table, dict):
        raise RebalanceError("[rebalance] must be a table (player_damage / enemy_damage / flag)")
    unknown = sorted(set(table) - set(_KNOWN_KEYS))
    if unknown:
        raise RebalanceError(f"[rebalance] unknown key(s): {unknown} (expected {', '.join(_KNOWN_KEYS)})")
    scales = {}
    for key in _SCALE_KEYS:
        v = table.get(key, 1.0)
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise RebalanceError(f"[rebalance] {key} must be a number (got {v!r})")
        v = float(v)
        if not (SCALE_MIN <= v <= SCALE_MAX):
            raise RebalanceError(f"[rebalance] {key} = {v:g} out of range [{SCALE_MIN:g}, {SCALE_MAX:g}]")
        scales[key] = v
    if all(v == 1.0 for v in scales.values()):
        raise RebalanceError("[rebalance] every scale is 1.0 -- the block does nothing; set player_damage "
                             "and/or enemy_damage (or remove the table)")
    flag = None
    label = ""
    if "flag" in table:
        label = str(table["flag"])
        try:
            flag = _flags.resolve(table["flag"], name_map or {})
        except ValueError as e:
            raise RebalanceError(f"[rebalance] flag: {e}")
        if not (0 <= flag <= _FLAG_MAX):
            raise RebalanceError(f"[rebalance] flag {flag} out of range 0..{_FLAG_MAX} (gEventGlobal is "
                                 f"2048 bytes); custom flags belong in the safe band >= {_flags.FIRST_SAFE_FLAG}")
    return RebalanceSpec(player=scales["player_damage"], enemy=scales["enemy_damage"],
                         flag=flag, flag_label=label)


def collect(projects) -> "tuple[RebalanceSpec, object] | None":
    """The mod's ONE rebalance spec from a build's projects (the Scripts-DLL is per-MOD, so ``[rebalance]``
    is mod-global like ``[difficulty]``). Multiple members may repeat an IDENTICAL block; two DIFFERENT
    blocks are a hard error. Returns (spec, carrier project) or ``None``. Raises :class:`RebalanceError`."""
    found = []
    for p in projects:
        raw_table = p.raw.get("rebalance")
        if raw_table is None:
            continue
        names = _flags.collect_flag_defs(p.raw) if isinstance(p.raw, dict) else {}
        found.append((parse_table(raw_table, name_map=names), p))
    if not found:
        return None
    distinct = {s for s, _ in found}
    if len(distinct) > 1:
        raise RebalanceError(
            "[rebalance] appears with DIFFERENT settings on more than one field of this build -- the damage "
            "multiplier is mod-GLOBAL (one per deployed folder), so the blocks must agree (or live on only "
            "one field).")
    return found[0]


# ---- the C# feature class --------------------------------------------------------------------------------

_SOURCE = """\
// {basename} -- emitted by the ff9mapkit build from [rebalance] (kit {kit_version}). SHIPPED CONTENT.
// Scales the final HP damage: {summary}. Chosen by the CASTER (player vs enemy); pure HP damage only
// (heal/recover/MP untouched). {gate_comment}
// NOTE: the engine clamps to MaxDamageLimit (9999) right AFTER this hook unless [Battle] BreakDamageLimit=1
// in Memoria.ini; and the IsDmg9999 cheat forces player damage to 9999 after this regardless of the scale.
// A plain STATIC feature class: the kit-generated Overload hub calls OnDamageFinalChanges(v) after the
// verbatim reflect-multiplier default, BEFORE observer features like telemetry (so a capture logs the
// rebalanced number). The whole body is try/catch-swallowed: any hiccup degrades to VANILLA damage.
using System;
using Memoria;
using Memoria.Data;

namespace Memoria.Scripts.Overload
{{
    public static class RebalanceOverload
    {{
        public static void OnDamageFinalChanges(BattleCalculator v)
        {{
            try
            {{
{gate}                if ((v.Target.Flags & CalcFlag.HpAlteration) == 0)   // no HP change on this calc
                    return;
                if ((v.Target.Flags & CalcFlag.HpRecovery) != 0)          // healing / recovery -- leave it
                    return;
                Double scale = v.Caster.IsPlayer ? {player} : {enemy};
                if (scale == 1.0)
                    return;
                Double scaled = v.Target.HpDamage * scale;
                if (scaled < 0.0) scaled = 0.0;
                if (scaled > {ceil}.0) scaled = {ceil}.0;
                v.Target.HpDamage = (Int32)scaled;
            }}
            catch {{ }}
        }}
    }}
}}
"""


def _num(x: float) -> str:
    """A C# double literal for a validated scale (repr keeps 1.5 as '1.5'; range-checked upstream)."""
    return f"{x:.6g}"


def render(spec: RebalanceSpec) -> str:
    """The C# feature-class source for a validated spec."""
    from .. import __version__
    from . import overload as _ovl
    parts = []
    if spec.player != 1.0:
        parts.append(f"player x{_num(spec.player)}")
    if spec.enemy != 1.0:
        parts.append(f"enemy x{_num(spec.enemy)}")
    if spec.flag is not None:
        label = f" ({spec.flag_label})" if spec.flag_label and spec.flag_label != str(spec.flag) else ""
        gate = _ovl.flag_gate_cs(spec.flag, label=spec.flag_label, indent=" " * 16)
        gate_comment = (f"Gated on gEventGlobal bit {spec.flag}{label}: bit CLEAR (or any state hiccup) = "
                        f"vanilla; toggle live via the debug menu (~) -> Flags.")
    else:
        gate = ""
        gate_comment = "Always on (no flag gate)."
    return _SOURCE.format(basename=REBALANCE_BASENAME, kit_version=__version__,
                          summary=", ".join(parts), gate_comment=gate_comment, gate=gate,
                          player=_num(spec.player), enemy=_num(spec.enemy), ceil=_DAMAGE_CEIL)


def rebalance_dir(layout) -> Path:
    """``…/Scripts/Sources/Rebalance`` -- BUILD-owned (wiped + re-emitted each build, like Sources/Battle;
    a deploy REPLACES it)."""
    return layout.scripts_dir / "Sources" / "Rebalance"


def write_source(layout, spec: "RebalanceSpec | None") -> "Path | None":
    """Emit (or, for ``spec=None``, REMOVE) the build's rebalance source. Wipe-first mirrors ``write_scripts``:
    a rebuild into a persistent dist dir must not keep a stale multiplier after ``[rebalance]`` is removed."""
    d = rebalance_dir(layout)
    shutil.rmtree(d, ignore_errors=True)
    if spec is None:
        return None
    d.mkdir(parents=True, exist_ok=True)
    cs = d / REBALANCE_BASENAME
    cs.write_text(render(spec), encoding="utf-8", newline="\n")
    return cs
