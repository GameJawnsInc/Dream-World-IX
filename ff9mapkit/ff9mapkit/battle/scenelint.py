"""Offline BALANCE lint for a battle scene -- the "I can't see the game" superpower for battle tuning.

Reads a parsed :class:`~ff9mapkit.battle.scene_codec.Scene` (every enemy's stats / affinities / rewards) and
flags design problems an actual playthrough would otherwise reveal. The bar is TRUST: it must be quiet on
well-designed vanilla fights and loud only on real problems -- so every check here was validated against a
sweep of all ~562 shipped scenes to confirm it does not cry wolf (a noisy lint trains the user to ignore it).

Checks:
  * no_reward (warn)    -- a real fight that yields NOTHING (0 EXP / gil / AP / no drops or steals).
  * bad_item (warn)     -- a drop/steal references an item id that isn't a real item.
  * status_immune (info)-- the enemy resists EVERY common offensive status -> status abilities are dead choices.
  * element_wall (info) -- the enemy resists/absorbs/halves >=7/8 elements -> almost no element does full damage.
  * phys_wall / mag_wall (info) -- a defence in the weapon-power band (>=50; real enemies cap ~24, FF9 weapon
                          power caps ~108) -> attacks are heavily reduced (FF9 defence is SUBTRACTIVE).
  * level5 (info)       -- the enemy's Level is a multiple of 5 AND it isn't Death-immune -> LV5 Death one-shots it.

Severity: ``warn`` = a likely real problem; ``info`` = design awareness (an intentional choice may be fine).

NOT done here (deferred -- the kit has no live party model): a turns-to-kill / time-to-kill-a-PC estimator and
an economy-curve-vs-zone check. FF9 physical damage is `Attack(~Strength) * max(1, weaponPower - defence)` with
3-4 attackers/round, so a single-attacker turns estimate is off by ~1-2 orders of magnitude and flags ~half the
bestiary as a "sponge" -- it carries no signal without a real party model, so it is intentionally omitted.

Pure + offline; reads only the parsed scene (the offensive-status mask is built at import from committed tables).
"""
from __future__ import annotations

from dataclasses import dataclass

from .. import items
from . import battlecsv

# The common statuses a PLAYER tries to inflict -- if an enemy resists ALL of these, status-disabling
# abilities are dead choices against it. (Buffs like Haste/Protect and odd ones are excluded on purpose.)
_OFFENSIVE_STATUSES = ["Petrify", "Venom", "Silence", "Blind", "Death", "Confuse", "Berserk", "Stop",
                       "Poison", "Sleep", "Slow", "Mini"]
_OFFENSIVE_MASK = battlecsv.encode_status(_OFFENSIVE_STATUSES)
_DEATH_MASK = battlecsv.encode_status(["Death"])

_N_ELEMENTS = 8
# A subtractive-defence "wall": FF9 weapon power runs ~40-108 (Excalibur II caps at 108) and real shipped
# enemies cap at phys_def ~24, so a defence at/above this band is an AUTHORED wall that floors normal attacks.
_WALL_DEF = 50


@dataclass
class Finding:
    severity: str           # "warn" | "info"
    code: str               # a short stable id (e.g. "status_immune")
    message: str

    def __str__(self) -> str:
        return f"[{self.severity}] {self.message}"


def lint_scene(scene) -> list[Finding]:
    """Return balance :class:`Finding`s for a parsed Scene (empty => nothing flagged)."""
    out: list[Finding] = []
    combat = [m for m in scene.monsters if m.hp > 1]   # hp<=1 => a placeholder / multipart / non-fightable type

    # --- scene-level: does the whole fight reward anything? ---
    if combat:
        total_exp = sum(m.exp for m in combat)
        total_gil = sum(m.gil for m in combat)
        max_ap = max((p.ap for p in scene.patterns), default=0)
        has_item = any(i != 255 for m in combat for i in (*m.drop, *m.steal))
        if total_exp == 0 and total_gil == 0 and max_ap == 0 and not has_item:
            out.append(Finding("warn", "no_reward",
                               "this battle yields NOTHING: 0 EXP, 0 gil, 0 AP, no drops/steals"))

    # --- per-enemy-type ---
    for t, m in enumerate(scene.monsters):
        if m.hp <= 1:
            continue
        lbl = f"enemy type {t} (Lv {m.level}, HP {m.hp})"

        # counter-play: an enemy that resists/absorbs/halves nearly every element (almost no element exploits it)
        resisted = set(battlecsv.decode_elements(m.guard_element)) \
            | set(battlecsv.decode_elements(m.absorb_element)) | set(battlecsv.decode_elements(m.half_element))
        if len(resisted) >= _N_ELEMENTS - 1:
            out.append(Finding("info", "element_wall",
                               f"{lbl}: resists/absorbs/halves {len(resisted)}/{_N_ELEMENTS} elements -- almost "
                               f"no element does full damage"))

        # counter-play: immune to every offensive status -> status abilities are dead choices
        if (m.resist_status & _OFFENSIVE_MASK) == _OFFENSIVE_MASK:
            out.append(Finding("info", "status_immune",
                               f"{lbl}: immune to every common offensive status -- status abilities are dead "
                               f"choices here"))

        # LV5 Death exploit -- only when it actually lands (the level is a multiple of 5 AND Death isn't resisted)
        if m.level > 0 and m.level % 5 == 0 and not ((m.resist_status | m.auto_status) & _DEATH_MASK):
            out.append(Finding("info", "level5",
                               f"{lbl}: level {m.level} is a multiple of 5 and not Death-immune -- LV5 Death "
                               f"one-shots it"))

        # rewards: an item id that isn't a real item
        for kind, ids in (("drop", m.drop), ("steal", m.steal)):
            for i in ids:
                if i != 255 and items.name_of(i) is None:
                    out.append(Finding("warn", "bad_item",
                                       f"{lbl}: {kind} references item id {i}, which is not a known item"))

        # subtractive-defence walls (a defence in the weapon-power band floors normal attacks)
        if m.phys_def >= _WALL_DEF:
            out.append(Finding("info", "phys_wall",
                               f"{lbl}: phys_def {m.phys_def} -- physical attacks heavily reduced (FF9 weapon "
                               f"power ~40-108; subtractive defence)"))
        if m.mag_def >= _WALL_DEF:
            out.append(Finding("info", "mag_wall",
                               f"{lbl}: mag_def {m.mag_def} -- magical attacks heavily reduced"))

    return out


def format_findings(findings, *, indent: str = "  ") -> str:
    """A human-readable block (empty findings => an OK line)."""
    if not findings:
        return f"{indent}lint: no balance problems flagged."
    warns = [f for f in findings if f.severity == "warn"]
    infos = [f for f in findings if f.severity == "info"]
    lines = [f"{indent}lint: {len(warns)} warning(s), {len(infos)} note(s)"]
    for f in warns + infos:
        lines.append(f"{indent}  {f}")
    return "\n".join(lines)
