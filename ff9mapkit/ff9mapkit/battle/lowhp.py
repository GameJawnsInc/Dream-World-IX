"""Declarative ``[lowhp]`` -- reparameterize the LowHP threshold (the Overload channel's second feature on
a RETURNING hook, and the smallest).

A field.toml (one per mod) declares::

    [lowhp]
    threshold = "1/3"     # the LowHP fraction of max HP (vanilla = 1/6): at or below it, a player gains
                          # the LowHP status and the HP number turns yellow. "N/D" string or a number in
                          # (0, 1); resolved to an exact fraction (denominator <= 100).
    flag = "hard_mode"    # OPTIONAL gate: the custom threshold applies only while this gEventGlobal BIT
                          # is set (a [[flag]] name or a bit index; omit = always on)

The build renders it into a plain static C# class (``Sources/LowHP/9500_LowHP.cs``) that the kit-generated
Overload hub RETURNS from ``UnitCheckPoint`` (btl_para.CheckPointDataStatus -- fires on every unit HP/MP
change). Facts from the source-dive (btl_para.cs:94-116, pinned 6b8bb2d5):

- ``cur.hp == 0`` returns ``Death`` BEFORE the hook -- a feature cannot save a 0-HP unit here.
- The caller acts ONLY on the returned status's **Death bit** (``CheckPointData`` checks ``& Death`` ->
  ``AlterStatus(Death)``); returning ``LowHP`` vs ``0`` changes nothing at the call site.
- Everything else is SIDE EFFECTS of the displaced default, reproduced VERBATIM here with only the
  threshold reparameterized: players-only ``CurrentHp * 6 <= MaximumHp`` -> add/remove
  ``BattleStatus.LowHP`` + the HP UI color (yellow/white) + the MP UI color (at ``MaximumMp / 6f``,
  untouched by this feature).

Why the threshold matters: ``BattleStatus.LowHP`` is a real engine status -- supporting abilities and AI
that key on "HP is low" read it -- and the yellow HP number is the player's danger signal. Raising the
fraction (e.g. ``1/3``) makes both fire earlier. The comparison is EXACT integer math (``CurrentHp * den <=
MaximumHp * num``), the same shape as the vanilla ``* 6`` form, so there is no float-boundary drift; the
denominator cap (100) keeps ``UInt32`` arithmetic overflow-free at the 9,999,999 logical-HP ceiling.

**Gate semantics (like ``[deathrules]``):** flag CLEAR must mean fully VANILLA -- and here the vanilla path
is the SAME code at the 1/6 threshold, so the class tests the bit (:func:`overload.flag_expr_cs`) and picks
the threshold with it; the transcribed side effects always run. GRANULARITY (the law): the hook fires per
HP/MP change (effectively per hit/heal), so the flag toggles LIVE, mid-battle.

**Fail-safe (differs from the void siblings on purpose):** the feature body is NOT try/catch-swallowed --
it IS the vanilla body, which runs unprotected at the same site in a stock game; swallowing it would skip
the default's side effects. The hub's returning-hook wrapper is the safety net (an exception -> ``0`` = no
forced status; the side effects retry at the very next checkpoint). Engine facts (all verified PUBLIC):
``BattleUnit.IsPlayer/CurrentHp/MaximumHp/CurrentMp/MaximumMp/UIColorHP/UIColorMP``; ``FF9TextTool.Yellow/
White``; ``btl_stat.CheckStatus(BTL_DATA, BattleStatus)`` (via the public implicit ``BattleUnit->BTL_DATA``
operator, exactly how the vanilla line compiles) + ``AlterStatus/RemoveStatus(BattleUnit, BattleStatusId)``.
RELAUNCH-scoped like the whole scripts channel.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from .. import flags as _flags

LOWHP_BASENAME = "9500_LowHP.cs"

_KNOWN_KEYS = ("threshold", "flag")
_FLAG_MAX = 2048 * 8 - 1                          # gEventGlobal is Byte[2048] -> bit indices 0..16383
# den <= 100 keeps `CurrentHp * den` inside UInt32 at the engine's 9,999,999 logical-HP ceiling
_DEN_MAX = 100
_VANILLA = Fraction(1, 6)


class LowHPError(ValueError):
    pass


@dataclass(frozen=True)
class LowHPSpec:
    num: int = 1                    # the exact LowHP fraction num/den (vanilla 1/6)
    den: int = 6
    flag: "int | None" = None       # resolved gEventGlobal bit index (gate), or None = always on
    flag_label: str = ""            # the author's spelling, for the emitted C# comment
    threshold_label: str = ""       # the author's spelling, for the emitted C# comment


def _parse_threshold(raw) -> Fraction:
    """An exact ``Fraction`` in (0, 1) with denominator <= 100, from a ``"N/D"`` string or a number.
    Numbers are resolved to the nearest <=1/100-granularity fraction (they are approximate by nature);
    an explicit string keeps the author's exact fraction and refuses a too-fine denominator."""
    if isinstance(raw, str):
        try:
            f = Fraction(raw.replace(" ", ""))
        except (ValueError, ZeroDivisionError):
            raise LowHPError(f'[lowhp] threshold string must look like "1/3" (got {raw!r})')
        if f.denominator > _DEN_MAX:
            raise LowHPError(f"[lowhp] threshold {raw!r} is too fine-grained (denominator "
                             f"{f.denominator} > {_DEN_MAX}; the comparison is exact UInt32 math)")
    elif isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise LowHPError(f'[lowhp] threshold must be a fraction of max HP -- a "N/D" string or a number '
                         f"in (0, 1) (got {raw!r})")
    else:
        f = Fraction(raw).limit_denominator(_DEN_MAX)
    if not (0 < f < 1):
        raise LowHPError(f"[lowhp] threshold = {raw!r} out of range (0, 1) (a fraction of max HP; "
                         f"vanilla is 1/6)")
    return f


def parse_table(table, *, name_map: "dict | None" = None) -> LowHPSpec:
    """Validate + resolve a raw ``[lowhp]`` table. Raises :class:`LowHPError` with an authoring-facing
    message; ``name_map`` is the project's ``[[flag]]`` name->index registry (for ``flag = "name"``)."""
    if not isinstance(table, dict):
        raise LowHPError("[lowhp] must be a table (threshold / flag)")
    unknown = sorted(set(table) - set(_KNOWN_KEYS))
    if unknown:
        raise LowHPError(f"[lowhp] unknown key(s): {unknown} (expected {', '.join(_KNOWN_KEYS)})")
    if "threshold" not in table:
        raise LowHPError("[lowhp] threshold is required (the block exists to change the vanilla 1/6)")
    f = _parse_threshold(table["threshold"])
    if f == _VANILLA:
        raise LowHPError("[lowhp] threshold resolves to the vanilla 1/6 -- the block does nothing "
                         "(set a different fraction or remove the table)")
    flag = None
    label = ""
    if "flag" in table:
        label = str(table["flag"])
        try:
            flag = _flags.resolve(table["flag"], name_map or {})
        except ValueError as e:
            raise LowHPError(f"[lowhp] flag: {e}")
        if not (0 <= flag <= _FLAG_MAX):
            raise LowHPError(f"[lowhp] flag {flag} out of range 0..{_FLAG_MAX} (gEventGlobal is "
                             f"2048 bytes); custom flags belong in the safe band >= {_flags.FIRST_SAFE_FLAG}")
    return LowHPSpec(num=f.numerator, den=f.denominator, flag=flag, flag_label=label,
                     threshold_label=str(table["threshold"]))


def collect(projects) -> "tuple[LowHPSpec, object] | None":
    """The mod's ONE lowhp spec from a build's projects (the Scripts-DLL is per-MOD, so ``[lowhp]`` is
    mod-global like its siblings). Multiple members may repeat an IDENTICAL block; two DIFFERENT blocks are
    a hard error. Returns (spec, carrier project) or ``None``. Raises :class:`LowHPError`."""
    found = []
    for p in projects:
        raw_table = p.raw.get("lowhp")
        if raw_table is None:
            continue
        names = _flags.collect_flag_defs(p.raw) if isinstance(p.raw, dict) else {}
        found.append((parse_table(raw_table, name_map=names), p))
    if not found:
        return None
    distinct = {s for s, _ in found}
    if len(distinct) > 1:
        raise LowHPError(
            "[lowhp] appears with DIFFERENT settings on more than one field of this build -- the LowHP "
            "threshold is mod-GLOBAL (one per deployed folder), so the blocks must agree (or live on only "
            "one field).")
    return found[0]


# ---- the C# feature class --------------------------------------------------------------------------------

_SOURCE = """\
// {basename} -- emitted by the ff9mapkit build from [lowhp] (kit {kit_version}). SHIPPED CONTENT.
// Reparameterizes the LowHP threshold: vanilla 1/6 -> {summary}. {gate_comment}
// RETURNING hook (single-owner): the kit-generated Overload hub RETURNS this from UnitCheckPoint
// (btl_para.CheckPointDataStatus, fires on every unit HP/MP change). The caller acts only on the returned
// DEATH bit (cur.hp == 0 already returned Death before the hook); the LowHP status + UI colors below are
// the displaced default's SIDE EFFECTS, transcribed VERBATIM with only the threshold changed. The body is
// deliberately bare (it IS the vanilla body); the hub's try/catch is the fail-safe (exception -> 0, and
// the side effects retry at the next checkpoint).
using System;
using Assets.Sources.Scripts.UI.Common; // FF9TextTool (the same using btl_para.cs itself carries)
using Memoria;
using Memoria.Data;

namespace Memoria.Scripts.Overload
{{
    public static class LowHPOverload
    {{
        public static BattleStatus UpdatePointStatus(BattleUnit unit)
        {{
{gate}            // ---- engine default, transcribed VERBATIM from btl_para.CheckPointDataStatus
            //      ("Default method"), with ONLY the LowHP threshold reparameterized ----
            Boolean isLowHP = unit.IsPlayer && {compare};
            if (isLowHP)
            {{
                unit.UIColorHP = FF9TextTool.Yellow;
                if (!btl_stat.CheckStatus(unit, BattleStatus.LowHP))
                    btl_stat.AlterStatus(unit, BattleStatusId.LowHP);
            }}
            else
            {{
                unit.UIColorHP = FF9TextTool.White;
                btl_stat.RemoveStatus(unit, BattleStatusId.LowHP);
            }}
            unit.UIColorMP = unit.CurrentMp <= unit.MaximumMp / 6f ? FF9TextTool.Yellow : FF9TextTool.White;
            return isLowHP ? BattleStatus.LowHP : 0;
        }}
    }}
}}
"""

_GATE = """\
            Boolean ruleActive = false;
            try {{ ruleActive = {expr}; }} catch {{ }} // gate hiccup -> vanilla threshold
"""


def _cmp(num: int, den: int) -> str:
    """The exact integer LowHP comparison -- the vanilla ``* 6`` shape, reparameterized."""
    rhs = "unit.MaximumHp" if num == 1 else f"unit.MaximumHp * {num}"
    return f"unit.CurrentHp * {den} <= {rhs}"


def render(spec: LowHPSpec) -> str:
    """The C# feature-class source for a validated spec."""
    from .. import __version__
    from . import overload as _ovl
    summary = f"{spec.num}/{spec.den}"
    if spec.threshold_label and spec.threshold_label != summary:
        summary += f" (from {spec.threshold_label})"
    if spec.flag is not None:
        label = f" ({spec.flag_label})" if spec.flag_label and spec.flag_label != str(spec.flag) else ""
        gate = _GATE.format(expr=_ovl.flag_expr_cs(spec.flag))
        gate_comment = (f"Gated on gEventGlobal bit {spec.flag}{label}: bit CLEAR (or any state hiccup) = "
                        f"the vanilla 1/6; toggles LIVE (the hook fires per HP/MP change).")
        compare = (f"(ruleActive ? {_cmp(spec.num, spec.den)}"
                   f" : {_cmp(1, 6)})")
    else:
        gate = ""
        gate_comment = "Always on (no flag gate)."
        compare = _cmp(spec.num, spec.den)
    return _SOURCE.format(basename=LOWHP_BASENAME, kit_version=__version__,
                          summary=summary, gate_comment=gate_comment, gate=gate, compare=compare)


def lowhp_dir(layout) -> Path:
    """``…/Scripts/Sources/LowHP`` -- BUILD-owned (wiped + re-emitted each build, like Sources/Battle;
    a deploy REPLACES it)."""
    return layout.scripts_dir / "Sources" / "LowHP"


def write_source(layout, spec: "LowHPSpec | None") -> "Path | None":
    """Emit (or, for ``spec=None``, REMOVE) the build's lowhp source. Wipe-first mirrors ``write_scripts``:
    a rebuild into a persistent dist dir must not keep a stale threshold after ``[lowhp]`` is removed."""
    d = lowhp_dir(layout)
    shutil.rmtree(d, ignore_errors=True)
    if spec is None:
        return None
    d.mkdir(parents=True, exist_ok=True)
    cs = d / LOWHP_BASENAME
    cs.write_text(render(spec), encoding="utf-8", newline="\n")
    return cs
