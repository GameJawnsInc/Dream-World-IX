"""Declarative ``[deathrules]`` -- own the party-wipe verdict (the Overload channel's third shipped-content
feature, and the first on a RETURNING hook).

A field.toml (one per mod) declares::

    [deathrules]
    second_wind = true          # cancel the wipe ONCE per battle: the party is revived by the same engine
                                # mechanism as Eiko's auto-Phoenix (a queued system Rebirth Flame)
    chance = 60                 # OPTIONAL percent chance the second wind fires (whole 1-100; default 100)
    keep_rebirth_flame = false  # OPTIONAL: false REMOVES Eiko's vanilla auto-revive (default true = kept)
    flag = "mercy_mode"         # OPTIONAL gate: the rules apply only while this gEventGlobal BIT is set
                                # (a [[flag]] name or a bit index; omit = always on)

The build renders it into a plain static C# class (``Sources/DeathRules/9600_DeathRules.cs``) that the
kit-generated Overload hub RETURNS from ``OnGameOver`` (btl_sys.CheckBattlePhase: fires when the last player
goes down; ``true`` = cancel the game over, the engine skips its defeat tail -- SEQ_MENU_OFF_DEFEAT +
"Annihilated" + menu-off + KillAllCommand). A returning hook is SINGLE-OWNER, so unlike the void-splice
siblings this feature IS the whole verdict: owning the interface displaces the engine's inline default
(Eiko's automatic Rebirth Flame), which is therefore transcribed VERBATIM into the class and kept unless
``keep_rebirth_flame = false``.

**The second wind reuses the engine's own revive mechanism, not hand-rolled state edits:** the vanilla Eiko
default cancels a wipe by queueing ``SysLastPhoenix``/``RebirthFlame`` on a (dead) player unit and re-enabling
the battle menu -- the command system then runs the Phoenix revive. The feature queues the exact same command
on the fallen ``dyingPC``. Once per battle: a static flag, reset at ``OnBattleInit``; after the revive is
spent, the next wipe is a normal game over. A pending queued revive always cancels the wipe (the vanilla
re-entry guard, ``CheckSpecificCommand2``).

**Gate semantics (differs from the siblings on purpose):** flag CLEAR must mean fully VANILLA -- and vanilla
includes Eiko's auto-revive. So the gate cannot be the shared early-return (:func:`overload.flag_gate_cs`);
the class tests the bit into ``ruleActive`` (:func:`overload.flag_expr_cs`) and only the DEVIATIONS (second
wind, Eiko removal) read it -- the transcribed default still runs while the rule sleeps. GRANULARITY (the
law): OnGameOver fires at wipe time, so the flag toggles the rules live -- the next wipe obeys the new state,
no battle boundary needed.

Engine facts (pinned 6b8bb2d5, all verified PUBLIC): ``FF9StateBattleSystem.btl_list``/``BTL_DATA.next/bi/
cmd``; ``btl_stat.CheckStatus``; ``btl_cmd.CheckSpecificCommand/CheckSpecificCommand2/SetCommand``;
``btl_scrp.GetBattleID``; ``ff9item.FF9Item_GetCount``; ``FF9.Comn.random8/random16``;
``UIManager.Battle.FF9BMenu_EnableMenu``; ``BattleUnit.Data``. The whole body is try/catch-swallowed and the
hub's fail-safe returns ``false`` -- a deathrules bug degrades to a VANILLA defeat, never a soft-lock
(canceling a wipe without queueing a revive would stall the battle with every player down). RELAUNCH-scoped
like the whole scripts channel.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from .. import flags as _flags

DEATHRULES_BASENAME = "9600_DeathRules.cs"

_BOOL_KEYS = ("second_wind", "keep_rebirth_flame")
_KNOWN_KEYS = ("second_wind", "chance", "keep_rebirth_flame", "flag")
_FLAG_MAX = 2048 * 8 - 1                          # gEventGlobal is Byte[2048] -> bit indices 0..16383


class DeathRulesError(ValueError):
    pass


@dataclass(frozen=True)
class DeathRulesSpec:
    second_wind: bool = False
    chance: int = 100               # percent; only meaningful with second_wind (100 = no roll emitted)
    keep_rebirth_flame: bool = True
    flag: "int | None" = None       # resolved gEventGlobal bit index (gate), or None = always on
    flag_label: str = ""            # the author's spelling, for the emitted C# comment


def parse_table(table, *, name_map: "dict | None" = None) -> DeathRulesSpec:
    """Validate + resolve a raw ``[deathrules]`` table. Raises :class:`DeathRulesError` with an authoring-
    facing message; ``name_map`` is the project's ``[[flag]]`` name->index registry (for ``flag = "name"``)."""
    if not isinstance(table, dict):
        raise DeathRulesError("[deathrules] must be a table (second_wind / chance / keep_rebirth_flame / flag)")
    unknown = sorted(set(table) - set(_KNOWN_KEYS))
    if unknown:
        raise DeathRulesError(f"[deathrules] unknown key(s): {unknown} (expected {', '.join(_KNOWN_KEYS)})")
    bools = {}
    for key, default in (("second_wind", False), ("keep_rebirth_flame", True)):
        v = table.get(key, default)
        if not isinstance(v, bool):
            raise DeathRulesError(f"[deathrules] {key} must be true or false (got {v!r})")
        bools[key] = v
    chance = table.get("chance", 100)
    if isinstance(chance, bool) or not isinstance(chance, int):
        raise DeathRulesError(f"[deathrules] chance must be a whole percent 1-100 (got {chance!r})")
    if not (1 <= chance <= 100):
        raise DeathRulesError(f"[deathrules] chance = {chance} out of range 1-100 (percent; 100 = always)")
    if "chance" in table and not bools["second_wind"]:
        raise DeathRulesError("[deathrules] chance only applies to the second wind -- set second_wind = true "
                              "(or remove chance)")
    if not bools["second_wind"] and bools["keep_rebirth_flame"]:
        raise DeathRulesError("[deathrules] the block does nothing (no second wind, Eiko's Rebirth Flame "
                              "kept = vanilla); set second_wind = true and/or keep_rebirth_flame = false "
                              "(or remove the table)")
    flag = None
    label = ""
    if "flag" in table:
        label = str(table["flag"])
        try:
            flag = _flags.resolve(table["flag"], name_map or {})
        except ValueError as e:
            raise DeathRulesError(f"[deathrules] flag: {e}")
        if not (0 <= flag <= _FLAG_MAX):
            raise DeathRulesError(f"[deathrules] flag {flag} out of range 0..{_FLAG_MAX} (gEventGlobal is "
                                  f"2048 bytes); custom flags belong in the safe band >= {_flags.FIRST_SAFE_FLAG}")
    return DeathRulesSpec(second_wind=bools["second_wind"], chance=chance,
                          keep_rebirth_flame=bools["keep_rebirth_flame"], flag=flag, flag_label=label)


def collect(projects) -> "tuple[DeathRulesSpec, object] | None":
    """The mod's ONE deathrules spec from a build's projects (the Scripts-DLL is per-MOD, so ``[deathrules]``
    is mod-global like ``[difficulty]``). Multiple members may repeat an IDENTICAL block; two DIFFERENT
    blocks are a hard error. Returns (spec, carrier project) or ``None``. Raises :class:`DeathRulesError`."""
    found = []
    for p in projects:
        raw_table = p.raw.get("deathrules")
        if raw_table is None:
            continue
        names = _flags.collect_flag_defs(p.raw) if isinstance(p.raw, dict) else {}
        found.append((parse_table(raw_table, name_map=names), p))
    if not found:
        return None
    distinct = {s for s, _ in found}
    if len(distinct) > 1:
        raise DeathRulesError(
            "[deathrules] appears with DIFFERENT settings on more than one field of this build -- the "
            "game-over rules are mod-GLOBAL (one per deployed folder), so the blocks must agree (or live on "
            "only one field).")
    return found[0]


# ---- the C# feature class --------------------------------------------------------------------------------

_SOURCE = """\
// {basename} -- emitted by the ff9mapkit build from [deathrules] (kit {kit_version}). SHIPPED CONTENT.
// Owns the game-over verdict: {summary}. {gate_comment}
// RETURNING hook (single-owner): the kit-generated Overload hub RETURNS this verdict from OnGameOver --
// true = CANCEL the game over (the engine skips its defeat tail), false = the defeat proceeds. Owning the
// interface DISPLACES the engine default (Eiko's automatic Rebirth Flame), so it is transcribed below.
// Any hiccup degrades to false = a vanilla defeat, never a soft-lock (canceling a wipe without queueing a
// revive would stall the battle with every player down).
using System;
using FF9;
using Memoria;
using Memoria.Data;

namespace Memoria.Scripts.Overload
{{
    public static class DeathRulesOverload
    {{
        private static Boolean _secondWindUsed;

        public static void OnBattleInit()
        {{
            _secondWindUsed = false; // the second wind recharges each battle
        }}

        public static Boolean OnGameOver(FF9StateBattleSystem state, BattleUnit dyingPC)
        {{
            try
            {{
{gate}{eiko}{second_wind}            }}
            catch {{ }}
            return false; // fall-through / any hiccup: the vanilla defeat proceeds
        }}

        // ---- engine default, transcribed VERBATIM from btl_sys.CheckBattlePhase ("Default method"):
        //      Eiko's automatic Rebirth Flame. Its `return`s exit the engine's whole game-over path, so
        //      here true = the engine's own cancel. ----
        private static Boolean VanillaRebirthFlame(FF9StateBattleSystem state)
        {{
            for (BTL_DATA btl = state.btl_list.next; btl != null; btl = btl.next)
            {{
                if (btl.bi.player != 0 && (CharacterId)btl.bi.slot_no == CharacterId.Eiko)
                {{
                    if (!btl_stat.CheckStatus(btl, BattleStatusConst.NoRebirthFlame))
                    {{
                        if (btl_cmd.CheckSpecificCommand(btl, BattleCommandId.SysLastPhoenix))
                            return true;
                        Boolean procRebirthFlame = ff9item.FF9Item_GetCount(RegularItem.PhoenixPinion) > Comn.random8();
                        if (procRebirthFlame)
                        {{
                            UIManager.Battle.FF9BMenu_EnableMenu(true);
                            btl_cmd.SetCommand(btl.cmd[0], BattleCommandId.SysLastPhoenix, (Int32)BattleAbilityId.RebirthFlame, btl_scrp.GetBattleID(0U), 1u);
                            return true;
                        }}
                    }}
                    break;
                }}
            }}
            return false;
        }}
    }}
}}
"""

_GATE = """\
                Boolean ruleActive = {expr}; // the [deathrules] gate: bit clear (or a state hiccup) = vanilla
"""

_EIKO_KEPT = """\
                if (VanillaRebirthFlame(state)) // engine default KEPT: Eiko's auto-revive fires first
                    return true;
"""

# keep_rebirth_flame=false under a gate: the rule ASLEEP must still be fully vanilla, Eiko included
_EIKO_GATED = """\
                if (!ruleActive && VanillaRebirthFlame(state)) // rule asleep -> the vanilla Eiko still fires
                    return true;
"""

_EIKO_REMOVED = """\
                // keep_rebirth_flame = false: Eiko's vanilla auto-revive is intentionally REMOVED
"""

_RULE_ASLEEP = """\
                if (!ruleActive)
                    return false; // rule asleep: the vanilla defeat proceeds
"""

_SECOND_WIND = """\
                // ---- second wind: cancel the wipe ONCE per battle via the same engine mechanism as the
                //      Eiko default (queue the system Rebirth Flame -- the Phoenix party revive) ----
                if (btl_cmd.CheckSpecificCommand2(BattleCommandId.SysLastPhoenix))
                    return true; // a queued revive is still pending -- keep the battle alive (vanilla guard)
                if (_secondWindUsed)
                    return false; // spent this battle: a second wipe is a normal game over
{roll}                _secondWindUsed = true;
                UIManager.Battle.FF9BMenu_EnableMenu(true);
                btl_cmd.SetCommand(dyingPC.Data.cmd[0], BattleCommandId.SysLastPhoenix, (Int32)BattleAbilityId.RebirthFlame, btl_scrp.GetBattleID(0U), 1u);
                return true;
"""

_ROLL = """\
                if (Comn.random16() % 100 >= {chance})
                    return false; // the {chance}% roll failed -- the defeat proceeds
"""


def render(spec: DeathRulesSpec) -> str:
    """The C# feature-class source for a validated spec."""
    from .. import __version__
    from . import overload as _ovl
    parts = []
    if spec.second_wind:
        parts.append("second wind (once per battle"
                     + (f", {spec.chance}% chance)" if spec.chance < 100 else ")"))
    parts.append("Eiko's Rebirth Flame " + ("kept" if spec.keep_rebirth_flame else "REMOVED"))
    if spec.flag is not None:
        label = f" ({spec.flag_label})" if spec.flag_label and spec.flag_label != str(spec.flag) else ""
        gate = _GATE.format(expr=_ovl.flag_expr_cs(spec.flag))
        gate_comment = (f"Gated on gEventGlobal bit {spec.flag}{label}: bit CLEAR (or any state hiccup) = "
                        f"fully vanilla (Eiko included); toggle live via F6 -> Flags.")
    else:
        gate = ""
        gate_comment = "Always on (no flag gate)."
    if spec.keep_rebirth_flame:
        eiko = _EIKO_KEPT
    elif spec.flag is not None:
        eiko = _EIKO_GATED
    else:
        eiko = _EIKO_REMOVED
    second_wind = ""
    if spec.flag is not None:
        second_wind += _RULE_ASLEEP
    if spec.second_wind:
        roll = _ROLL.format(chance=spec.chance) if spec.chance < 100 else ""
        second_wind += _SECOND_WIND.format(roll=roll)
    return _SOURCE.format(basename=DEATHRULES_BASENAME, kit_version=__version__,
                          summary=", ".join(parts), gate_comment=gate_comment, gate=gate,
                          eiko=eiko, second_wind=second_wind)


def deathrules_dir(layout) -> Path:
    """``…/Scripts/Sources/DeathRules`` -- BUILD-owned (wiped + re-emitted each build, like Sources/Battle;
    a deploy REPLACES it)."""
    return layout.scripts_dir / "Sources" / "DeathRules"


def write_source(layout, spec: "DeathRulesSpec | None") -> "Path | None":
    """Emit (or, for ``spec=None``, REMOVE) the build's deathrules source. Wipe-first mirrors
    ``write_scripts``: a rebuild into a persistent dist dir must not keep stale game-over rules after
    ``[deathrules]`` is removed."""
    d = deathrules_dir(layout)
    shutil.rmtree(d, ignore_errors=True)
    if spec is None:
        return None
    d.mkdir(parents=True, exist_ok=True)
    cs = d / DEATHRULES_BASENAME
    cs.write_text(render(spec), encoding="utf-8", newline="\n")
    return cs
