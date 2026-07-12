"""Declarative ``[deathrules]`` -- own the party-wipe verdict (the Overload channel's third shipped-content
feature, and the first on a RETURNING hook).

A field.toml (one per mod) declares::

    [deathrules]
    second_wind = true          # cancel the wipe ONCE per battle: the party is revived
    chance = 60                 # OPTIONAL percent chance the second wind fires (whole 1-100; default 100)
    animation = "short"         # OPTIONAL: "full" (default) = the queued Phoenix summon (the same engine
                                # mechanism as Eiko's auto-Phoenix; the ability decides the revive HP);
                                # "short" = no choreography, the party just stands up (see below)
    revive_hp = 0.25            # OPTIONAL, "short" only: revive HP as a fraction of max (0 < x <= 1),
                                # floored at 1 HP; default 0.2
    keep_rebirth_flame = false  # OPTIONAL: false REMOVES Eiko's vanilla auto-revive (default true = kept)
    flag = "mercy_mode"         # OPTIONAL gate: the rules apply only while this gEventGlobal BIT is set
                                # (a [[flag]] name or a bit index; omit = always on)
    on_defeat = { warp_to = 6000, hp = 0.2, gil_loss = 0.1 }
                                # OPTIONAL: instead of a game over, revive minimally + FLEE the battle +
                                # warp to field `warp_to` (see below). With second_wind too, the wind
                                # fires first; spent / a failed roll falls through to the warp.

**``on_defeat`` -- the warp-instead-of-game-over rule -- is a DLL + FIELD composition** (both halves built
from this one table): the DLL half revives the dead minimally (the proven short-anim death-changer recipe,
at ``hp`` x max), optionally docks ``gil_loss`` x party gil, sets a WIPE-MARKER ``gEventGlobal`` bit
(default bit ``8508``, kit-reserved; override via ``on_defeat.flag``), and ends the battle through the
engine's own FLEE sequence (the ``SysEscape`` trigger transcribed from ``btl_cmd.cs:1035-1057`` minus
``escape_no``/``BTL_FLAG_ABILITY_FLEE`` -- no flee-stat pollution, no engine gil cut; ``battle.cs``'s
``SEQ_MENU_OFF_ESCAPE`` then plays the run-away fade and returns control to the field). The FIELD half:
every kit-built field with an ``[encounter]`` gets a tag-10 (Main_Reinit) prologue -- ``if (marker) {
clear; fade; Field(warp_to) }`` (:func:`field_prologue`, injected by the build's ``add_reinit``). Clear-
first so it can never loop; tag-10 runs after EVERY battle but only the wipe sets the bit. ⚠ COVERAGE: the
DLL is mod-global -- a wipe in a field whose ``.eb`` lacks the check (no ``[deathrules]`` on it, or a
verbatim fork) revives + flees but does NOT warp and leaves the marker set, which would warp spuriously
after the next battle in a covered field; the build WARNS about uncovered encounter fields.

The build renders it into a plain static C# class (``Sources/DeathRules/9600_DeathRules.cs``) that the
kit-generated Overload hub RETURNS from ``OnGameOver`` (btl_sys.CheckBattlePhase: fires when the last player
goes down; ``true`` = cancel the game over, the engine skips its defeat tail -- SEQ_MENU_OFF_DEFEAT +
"Annihilated" + menu-off + KillAllCommand). A returning hook is SINGLE-OWNER, so unlike the void-splice
siblings this feature IS the whole verdict: owning the interface displaces the engine's inline default
(Eiko's automatic Rebirth Flame), which is therefore transcribed VERBATIM into the class and kept unless
``keep_rebirth_flame = false``.

**Both second-wind variants reuse engine-sanctioned revive mechanisms, not invented state edits.**
``animation = "full"`` (default, the in-game-proven original): the vanilla Eiko default cancels a wipe by
queueing ``SysLastPhoenix``/``RebirthFlame`` on a (dead) player unit and re-enabling the battle menu -- the
command system then runs the Phoenix revive (full summon choreography, ability-decided HP). The feature
queues the exact same command on the fallen ``dyingPC``. ``animation = "short"`` (user-requested -- the
summon "could get obnoxious in an authored context"): revive the dead players DIRECTLY the way the engine's
own death-changer statuses do -- the exact composition of ``AutoLifeStatusScript.OnDeath`` (set ``CurrentHp``,
``RemoveStatus(Death)``), ``DeathStatusScript.Remove`` (which that call triggers: ``die_seq = 0``, the
death_f/stop_anim/cmd_idle flags, texanim restart), and ``btl_mot.DecidePlayerDieSequence``'s cancel branch
(``SetDefaultIdle`` stands the unit up + ``Settings.SetHPFull`` for the booster). No choreography at all: the
party simply gets up, at ``revive_hp`` x max HP (floor 1). Only the DEAD are revived (petrify stays, like the
Phoenix ability); a wipe with nobody revivable (all petrified) falls through to a vanilla defeat. Once per
battle either way: a static flag, reset at ``OnBattleInit``; after the revive is spent, the next wipe is a
normal game over. A pending queued revive always cancels the wipe (the vanilla re-entry guard,
``CheckSpecificCommand2``).

**Gate semantics (differs from the siblings on purpose):** flag CLEAR must mean fully VANILLA -- and vanilla
includes Eiko's auto-revive. So the gate cannot be the shared early-return (:func:`overload.flag_gate_cs`);
the class tests the bit into ``ruleActive`` (:func:`overload.flag_expr_cs`) and only the DEVIATIONS (second
wind, Eiko removal) read it -- the transcribed default still runs while the rule sleeps. GRANULARITY (the
law): OnGameOver fires at wipe time, so the flag toggles the rules live -- the next wipe obeys the new state,
no battle boundary needed.

Engine facts (pinned 6b8bb2d5, all verified PUBLIC): ``FF9StateBattleSystem.btl_list``/``BTL_DATA.next/bi/
cmd/cur``; ``btl_stat.CheckStatus`` + ``RemoveStatus(BattleUnit, BattleStatusId)``;
``btl_cmd.CheckSpecificCommand/CheckSpecificCommand2/SetCommand``; ``btl_scrp.GetBattleID``;
``ff9item.FF9Item_GetCount``; ``FF9.Comn.random8/random16``; ``UIManager.Battle.FF9BMenu_EnableMenu``;
``BattleUnit(BTL_DATA)``/``.Data``/``.CurrentHp``/``.MaximumHp``; ``FF9.btl_mot.SetDefaultIdle(BTL_DATA)``;
``FF9StateSystem.Settings.SetHPFull``. The whole body is try/catch-swallowed and the
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
_KNOWN_KEYS = ("second_wind", "chance", "animation", "revive_hp", "keep_rebirth_flame", "flag", "on_defeat")
_ON_DEFEAT_KEYS = ("warp_to", "hp", "gil_loss", "flag")
_ANIMATIONS = ("full", "short")
_FLAG_MAX = 2048 * 8 - 1                          # gEventGlobal is Byte[2048] -> bit indices 0..16383
# The kit-reserved WIPE-MARKER bit (on_defeat's default `flag`): the DLL sets it at the canceled game
# over, the field's tag-10 clears it and warps. 8508 sits just below the author band (>= 8512, flags.py
# FIRST_SAFE_FLAG) and above every kit auto-band (event 8000+ / cutscene 8100 / choice 8200+ /
# on_entry 8300+ / chest 8376+).
WIPE_FLAG_DEFAULT = 8508
# The OUTPOST var ("the last outpost the player ENTERED"): a kit-reserved save-backed GLOB_UINT16 at
# gEventGlobal bytes 1060-1061 (bit band 8480-8495 -- between the chest auto-band and the 8508 wipe
# marker, below the author band 8512+) holding a FIELD ID; 0 = never visited one (gEventGlobal is zero
# on New Game). Written by `[field] outpost = true` (an unconditional startup-style Main_Init write,
# every entry -> last-write-wins); read by the wipe-warp prologue via a COMPUTED Field() (the engine's
# expression-arg lane). Register-on-save/inn policy stays modder-side: put the same word write behind an
# event instead of tagging the field.
OUTPOST_BYTE = 1060
_FIELD_ID_MAX = 32767                             # engine fldMapNo is Int16


class DeathRulesError(ValueError):
    pass


@dataclass(frozen=True)
class DeathRulesSpec:
    second_wind: bool = False
    chance: int = 100               # percent; only meaningful with second_wind (100 = no roll emitted)
    animation: str = "full"         # "full" = the queued Phoenix summon (engine-decided revive HP);
                                    # "short" = the direct death-changer-style revive (no choreography)
    revive_hp: float = 0.2          # short only: revive HP as a fraction of max (0 < x <= 1), floor 1 HP
    keep_rebirth_flame: bool = True
    flag: "int | None" = None       # resolved gEventGlobal bit index (gate), or None = always on
    flag_label: str = ""            # the author's spelling, for the emitted C# comment
    # on_defeat (warp instead of a game over): None = absent. When second_wind is ALSO on, the wind
    # fires first (once per battle); spent / a failed roll falls THROUGH to the warp.
    warp_to: "int | None" = None    # the destination field id
    warp_hp: float = 0.2            # arrival revive HP as a fraction of max (0 < x <= 1), floor 1 HP
    warp_gil_loss: float = 0.0      # fraction of PARTY gil lost on the wipe ([0, 1); 0 = no penalty)
    wipe_flag: int = WIPE_FLAG_DEFAULT   # the marker bit shared by the DLL and the field's tag-10
    wipe_flag_label: str = ""


def parse_table(table, *, name_map: "dict | None" = None) -> DeathRulesSpec:
    """Validate + resolve a raw ``[deathrules]`` table. Raises :class:`DeathRulesError` with an authoring-
    facing message; ``name_map`` is the project's ``[[flag]]`` name->index registry (for ``flag = "name"``)."""
    if not isinstance(table, dict):
        raise DeathRulesError("[deathrules] must be a table (second_wind / chance / animation / revive_hp / "
                              "keep_rebirth_flame / flag)")
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
    animation = table.get("animation", "full")
    if animation not in _ANIMATIONS:
        raise DeathRulesError(f"[deathrules] animation must be one of {'/'.join(_ANIMATIONS)} (got "
                              f"{animation!r}); full = the Phoenix summon, short = the party just stands up")
    if "animation" in table and not bools["second_wind"]:
        raise DeathRulesError("[deathrules] animation only applies to the second wind -- set second_wind = "
                              "true (or remove animation)")
    revive_hp = table.get("revive_hp", 0.2)
    if isinstance(revive_hp, bool) or not isinstance(revive_hp, (int, float)):
        raise DeathRulesError(f"[deathrules] revive_hp must be a fraction of max HP in (0, 1] (got {revive_hp!r})")
    revive_hp = float(revive_hp)
    if not (0.0 < revive_hp <= 1.0):
        raise DeathRulesError(f"[deathrules] revive_hp = {revive_hp:g} out of range (0, 1] (a fraction of "
                              f"max HP; the revive floors at 1 HP)")
    if "revive_hp" in table and animation != "short":
        raise DeathRulesError('[deathrules] revive_hp only applies to animation = "short" -- the full Phoenix '
                              "revive's HP is decided by the engine ability (or remove revive_hp)")
    od = table.get("on_defeat")
    warp_to, warp_hp, warp_gil, wipe_flag, wipe_label = None, 0.2, 0.0, WIPE_FLAG_DEFAULT, ""
    if od is not None:
        if not isinstance(od, dict):
            raise DeathRulesError("[deathrules] on_defeat must be an inline table "
                                  "{ warp_to = <field id>, hp = 0.2, gil_loss = 0.1, flag = ... }")
        od_unknown = sorted(set(od) - set(_ON_DEFEAT_KEYS))
        if od_unknown:
            raise DeathRulesError(f"[deathrules] on_defeat unknown key(s): {od_unknown} "
                                  f"(expected {', '.join(_ON_DEFEAT_KEYS)})")
        warp_to = od.get("warp_to")
        if isinstance(warp_to, bool) or not isinstance(warp_to, int):
            raise DeathRulesError(f"[deathrules] on_defeat.warp_to must be a field id (got {warp_to!r})")
        if not (1 <= warp_to <= _FIELD_ID_MAX):
            raise DeathRulesError(f"[deathrules] on_defeat.warp_to = {warp_to} out of range 1..{_FIELD_ID_MAX} "
                                  f"(fldMapNo is Int16; the id must be a REGISTERED field)")
        warp_hp = od.get("hp", 0.2)
        if isinstance(warp_hp, bool) or not isinstance(warp_hp, (int, float)):
            raise DeathRulesError(f"[deathrules] on_defeat.hp must be a fraction of max HP in (0, 1] "
                                  f"(got {warp_hp!r})")
        warp_hp = float(warp_hp)
        if not (0.0 < warp_hp <= 1.0):
            raise DeathRulesError(f"[deathrules] on_defeat.hp = {warp_hp:g} out of range (0, 1]")
        warp_gil = od.get("gil_loss", 0.0)
        if isinstance(warp_gil, bool) or not isinstance(warp_gil, (int, float)):
            raise DeathRulesError(f"[deathrules] on_defeat.gil_loss must be a fraction of party gil in "
                                  f"[0, 1) (got {warp_gil!r})")
        warp_gil = float(warp_gil)
        if not (0.0 <= warp_gil < 1.0):
            raise DeathRulesError(f"[deathrules] on_defeat.gil_loss = {warp_gil:g} out of range [0, 1)")
        if "flag" in od:
            wipe_label = str(od["flag"])
            try:
                wipe_flag = _flags.resolve(od["flag"], name_map or {})
            except ValueError as e:
                raise DeathRulesError(f"[deathrules] on_defeat.flag: {e}")
            if not (0 <= wipe_flag <= _FLAG_MAX):
                raise DeathRulesError(f"[deathrules] on_defeat.flag {wipe_flag} out of range 0..{_FLAG_MAX}")
    if not bools["second_wind"] and bools["keep_rebirth_flame"] and od is None:
        raise DeathRulesError("[deathrules] the block does nothing (no second wind, no on_defeat, Eiko's "
                              "Rebirth Flame kept = vanilla); set second_wind = true, on_defeat = {...} "
                              "and/or keep_rebirth_flame = false (or remove the table)")
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
                          animation=animation, revive_hp=revive_hp,
                          keep_rebirth_flame=bools["keep_rebirth_flame"], flag=flag, flag_label=label,
                          warp_to=warp_to, warp_hp=warp_hp, warp_gil_loss=warp_gil,
                          wipe_flag=wipe_flag, wipe_flag_label=wipe_label)


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
{warp_static}
        public static void OnBattleInit()
        {{
            _secondWindUsed = false; // the second wind recharges each battle
{warp_reset}        }}

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

_SECOND_WIND_PRELUDE = """\
                // ---- second wind: cancel the wipe ONCE per battle ----
                if (btl_cmd.CheckSpecificCommand2(BattleCommandId.SysLastPhoenix))
                    return true; // a queued revive is still pending -- keep the battle alive (vanilla guard)
                if (_secondWindUsed)
                    return false; // spent this battle: a second wipe is a normal game over
{roll}"""

# animation = "full": the same engine mechanism as the Eiko default -- queue the system Rebirth Flame
# (the Phoenix party revive, full summon choreography; the ability decides the revive HP).
_SECOND_WIND_FULL = """\
                _secondWindUsed = true;
                UIManager.Battle.FF9BMenu_EnableMenu(true);
                btl_cmd.SetCommand(dyingPC.Data.cmd[0], BattleCommandId.SysLastPhoenix, (Int32)BattleAbilityId.RebirthFlame, btl_scrp.GetBattleID(0U), 1u);
                return true;
"""

# animation = "short": revive the fallen party DIRECTLY, the way the engine's own death-changer statuses do
# (AutoLifeStatusScript.OnDeath sets HP + removes Death; DeathStatusScript.Remove does the un-death
# bookkeeping -- die_seq/flags/texanims; DecidePlayerDieSequence's cancel branch stands the unit up via
# SetDefaultIdle + calls Settings.SetHPFull for the booster). No choreography -- the party just gets up.
_SECOND_WIND_SHORT = """\
                Boolean revived = false;
                for (BTL_DATA fallen = state.btl_list.next; fallen != null; fallen = fallen.next)
                {{
                    if (fallen.bi.player == 0)
                        continue;
                    if (fallen.cur.hp != 0 && !btl_stat.CheckStatus(fallen, BattleStatus.Death))
                        continue; // petrify etc. stays -- like the Phoenix revive, only the DEAD get up
                    BattleUnit unit = new BattleUnit(fallen);
                    unit.CurrentHp = Math.Max(1u, (UInt32)(unit.MaximumHp * {hp}));
                    btl_stat.RemoveStatus(unit, BattleStatusId.Death); // die_seq/flags/texanim bookkeeping
                    btl_mot.SetDefaultIdle(fallen);                    // stand back up (the cancel-death recipe)
                    revived = true;
                }}
                if (!revived)
                    return false; // nobody revivable (e.g. a full-petrify wipe) -- the defeat proceeds
                FF9StateSystem.Settings.SetHPFull(); // the HP/MP-full booster support (no-op otherwise)
                _secondWindUsed = true;
                UIManager.Battle.FF9BMenu_EnableMenu(true);
                return true;
"""

_ROLL = """\
                if (Comn.random16() % 100 >= {chance})
                    return false; // the {chance}% roll failed -- the defeat proceeds
"""

# second wind WITH on_defeat behind it: spent (or a failed roll) must FALL THROUGH to the warp instead of
# returning false, so the act tail sits inside a guard block (the straight-line proven templates are kept
# byte-stable for the on_defeat-less case). !_defeatWarpFired: once the wipe-exit is underway, a mid-fade
# re-kill must NOT trigger a fresh Phoenix (the failed-roll case would otherwise re-roll every re-kill).
_SECOND_WIND_GUARDED = """\
                // ---- second wind: cancel the wipe ONCE per battle; spent (or a failed roll) falls
                //      THROUGH to on_defeat below; never fires mid-wipe-exit ----
                if (btl_cmd.CheckSpecificCommand2(BattleCommandId.SysLastPhoenix))
                    return true; // a queued revive is still pending -- keep the battle alive (vanilla guard)
                if (!_defeatWarpFired && !_secondWindUsed{roll_cond})
                {{
{act}                }}
"""

# on_defeat: instead of the game over, revive minimally (the proven short-anim death-changer recipe, W-
# suffixed locals so it coexists with a short second wind) + FLEE the battle + set the WIPE MARKER bit the
# field's tag-10 checks (clear + fade + Field(warp_to) -- the kit injects that check into every built
# field's after-battle handler). The battle-end is the SysEscape trigger transcribed (btl_cmd.cs:1035-1057)
# MINUS escape_no++/BTL_FLAG_ABILITY_FLEE: not a player flee -- no flee stats, no engine gil cut (the
# gil_loss knob below is deliberately a fraction of PARTY gil, unlike the flee default's fraction of the
# battle's gil bonus, which is ~empty on a wipe).
_ON_DEFEAT = """\
                // ---- on_defeat: no game over -- the QUIET DEFEAT. Revive the fallen internally but do
                //      NOT stand them up (no get-up racing the exit); the battle ends INSTANTLY over the
                //      fallen party (no run-away slide -- see the escape-fade note below), and they are
                //      on their feet at the destination because the field spawn owns motion there. Then
                //      FLEE the battle and mark the wipe (the field's tag-10 sees the mark, clears it,
                //      and warps to field {warp_to}). ----
                Boolean revivedW = false;
                for (BTL_DATA fallenW = state.btl_list.next; fallenW != null; fallenW = fallenW.next)
                {{
                    if (fallenW.bi.player == 0)
                        continue;
                    if (fallenW.cur.hp != 0 && !btl_stat.CheckStatus(fallenW, BattleStatus.Death))
                        continue; // petrify etc. stays -- only the DEAD are revived
                    BattleUnit unitW = new BattleUnit(fallenW);
                    unitW.CurrentHp = Math.Max(1u, (UInt32)(unitW.MaximumHp * {hp}));
                    btl_stat.RemoveStatus(unitW, BattleStatusId.Death); // die_seq/flags/texanim bookkeeping
                    // (deliberately NO SetDefaultIdle here -- the quiet-defeat visual)
                    revivedW = true;
                }}
                if (!revivedW)
                    return false; // nobody revivable (e.g. a full-petrify wipe) -- the defeat proceeds
                FF9StateSystem.Settings.SetHPFull(); // the HP/MP-full booster support (no-op otherwise)
                if (!_defeatWarpFired)
                {{
                    // the DOUBLE-DOCK GUARD: enemies can still act during the escape fade (vanilla lets
                    // you die while fleeing) -- a mid-fade re-kill re-runs this hook. The exit is kept
                    // alive below either way; gil docks and the marker sets ONCE per wipe-exit.
                    _defeatWarpFired = true;
{gil}{marker}                }}
                // the FLEE battle-end (SysEscape trigger, btl_cmd.cs:1035-1057, transcribed), made
                // INSTANT: btl_escape_fade = 0 skips the run-away slide/fade/sound (battle.cs:337-356 --
                // the pos[2] slide only runs while the fade counts down; at 0 units hide on the spot and
                // the close proceeds the same frame, which also all-but-closes the mid-fade re-kill
                // window). Then BTL_RESULT_ESCAPE + PHASE_CLOSE return control to the field. The counter
                // is per-battle state (InitBattleSystem resets it to 32).
                UIManager.Battle.SetIdle();
                state.btl_escape_fade = 0;
                state.btl_phase = FF9StateBattleSystem.PHASE_MENU_OFF;
                state.btl_seq = FF9StateBattleSystem.SEQ_MENU_OFF_ESCAPE;
                btl_cmd.KillAllCommand(state);
                return true;
"""

_ON_DEFEAT_MARKER = """\
                Byte[] gw = FF9StateSystem.EventState.gEventGlobal;
                gw[{fbyte}] |= {fmask}; // the WIPE MARKER (bit {wipe_flag}) the field's tag-10 checks
"""

_ON_DEFEAT_GIL = """\
                UInt32 gilLostW = (UInt32)(FF9StateSystem.Common.FF9.party.gil * {gil});
                if (FF9StateSystem.Common.FF9.party.gil > gilLostW)
                    FF9StateSystem.Common.FF9.party.gil -= gilLostW;
                else
                    FF9StateSystem.Common.FF9.party.gil = 0U;
"""


def render(spec: DeathRulesSpec) -> str:
    """The C# feature-class source for a validated spec."""
    from .. import __version__
    from . import overload as _ovl
    parts = []
    if spec.second_wind:
        bits = ["once per battle"]
        if spec.chance < 100:
            bits.append(f"{spec.chance}% chance")
        bits.append("full Phoenix summon" if spec.animation == "full"
                    else f"short (no summon, revive at {spec.revive_hp:g}x max HP)")
        parts.append(f"second wind ({', '.join(bits)})")
    if spec.warp_to is not None:
        od = f"on_defeat -> flee + warp to field {spec.warp_to} at {spec.warp_hp:g}x max HP"
        if spec.warp_gil_loss > 0:
            od += f", -{spec.warp_gil_loss:g}x party gil"
        parts.append(od)
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
        act = (_SECOND_WIND_FULL if spec.animation == "full"
               else _SECOND_WIND_SHORT.format(hp=f"{spec.revive_hp:g}"))
        if spec.warp_to is None:
            # the on_defeat-less shape: straight-line, byte-stable with the in-game-proven builds
            roll = _ROLL.format(chance=spec.chance) if spec.chance < 100 else ""
            second_wind += _SECOND_WIND_PRELUDE.format(roll=roll) + act
        else:
            # with on_defeat behind it: spent / a failed roll FALLS THROUGH to the warp
            roll_cond = (f" && Comn.random16() % 100 < {spec.chance}" if spec.chance < 100 else "")
            import textwrap
            second_wind += _SECOND_WIND_GUARDED.format(roll_cond=roll_cond,
                                                       act=textwrap.indent(act, "    "))
    if spec.warp_to is not None:
        import textwrap
        gil = (textwrap.indent(_ON_DEFEAT_GIL.format(gil=f"{spec.warp_gil_loss:g}"), "    ")
               if spec.warp_gil_loss > 0 else "")
        marker = textwrap.indent(
            _ON_DEFEAT_MARKER.format(fbyte=spec.wipe_flag >> 3, fmask=1 << (spec.wipe_flag & 7),
                                     wipe_flag=spec.wipe_flag), "    ")
        second_wind += _ON_DEFEAT.format(warp_to=spec.warp_to, hp=f"{spec.warp_hp:g}",
                                         gil=gil, marker=marker)
    has_warp = spec.warp_to is not None
    return _SOURCE.format(basename=DEATHRULES_BASENAME, kit_version=__version__,
                          summary=", ".join(parts), gate_comment=gate_comment, gate=gate,
                          eiko=eiko, second_wind=second_wind,
                          warp_static=("        private static Boolean _defeatWarpFired; // a wipe-exit "
                                       "is underway (on_defeat)" if has_warp else ""),
                          warp_reset=("            _defeatWarpFired = false; // a new battle = a fresh "
                                      "wipe-exit\n" if has_warp else ""))


def field_prologue(spec: "DeathRulesSpec | None") -> bytes:
    """The tag-10 (Main_Reinit) PROLOGUE for a field in an ``on_defeat`` mod::

        if (GLOB[wipe_flag]) {
            GLOB[wipe_flag] = 0                     # clear FIRST -- the warp can never loop
            <the proven warp fade + sound>
            if (outpost != 0) Field(<the outpost var>)   # the COMPUTED warp: the last outpost ENTERED
            Field(warp_to)                          # the fallback (wiped before reaching any outpost)
        }

    Prepended to the after-battle handler so the flee-end the DLL triggered at the canceled game over lands
    here and warps. The check lives in tag-10 (after EVERY battle), and only the deathrules DLL ever sets
    the bit, so a normal victory sees it clear. Each ``Field()`` transitions away, so the fallback only runs
    when the outpost branch didn't fire. ``b""`` when on_defeat is absent."""
    if spec is None or spec.warp_to is None:
        return b""
    from ..content import event as _event, region as _region
    from ..eb import opcodes as _op
    warp_tail = (
        _op.fade_filter(*_event.WARP_FADE) + _op.wait(25)          # the proven fade-before-Field()
        + _op.run_sound_code(*_event.WARP_SOUND)
        + _region.if_block(_region.cond_truthy(_region.GLOB_UINT16, OUTPOST_BYTE),
                           _region.field_to_var(_region.GLOB_UINT16, OUTPOST_BYTE))
        + _op.field(spec.warp_to))
    return _region.if_block(
        _region.cond_truthy(_region.GLOB_BOOL, spec.wipe_flag),
        _region.set_var(_region.GLOB_BOOL, spec.wipe_flag, 0) + warp_tail)


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
