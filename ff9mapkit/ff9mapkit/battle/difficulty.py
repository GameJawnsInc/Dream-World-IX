"""Declarative ``[difficulty]`` -- enemy-stat scaling at battle init (the Overload channel's first
SHIPPED-CONTENT feature; battle telemetry is its dev-tool sibling).

A field.toml (one per mod) declares::

    [difficulty]
    enemy_hp = 1.5        # x max+current HP of every enemy, once per battle
    enemy_attack = 1.25   # x Strength (physical)
    enemy_magic = 1.25    # x Magic
    flag = "hard_mode"    # OPTIONAL gate: scale only while this gEventGlobal BIT is set
                          # (a [[flag]] name or a bit index; omit = always on)

The build renders it into a plain static C# class (``Sources/Difficulty/9800_Difficulty.cs``) that the
kit-generated Overload hub calls at ``OnBattleInit`` -- a call site with NO engine default (pure addition:
nothing vanilla is displaced, the safest hook in the channel). It runs BEFORE observer features (telemetry
logs the scaled roster). Engine facts (pinned 6b8bb2d5): ``BattleUnit.MaximumHp/CurrentHp`` are the LOGICAL
HP properties (``btl_para.Get/SetLogicalHP`` -- they transparently carry the engine's +10000 non-dying-boss
convention, so scaling through them is safe where raw ``max.hp`` writes would not be); ``Strength``/``Magic``
are settable Bytes; ``FF9StateSystem.EventState.gEventGlobal`` is a public ``Byte[2048]`` (bit N -> byte
``N>>3`` mask ``1<<(N&7)``). Players (and monster-transformed players) are never touched: the loop skips
``u.IsPlayer``. The whole body is try/catch-swallowed -- a difficulty bug must degrade to VANILLA, never
break a battle (an EventState hiccup means the gate reads closed -> no scaling).

Flag-gated mode is the journey author's "hard mode": seed the bit via ``[startup]``/``[[flag]]``/an event,
toggle it live via the debug menu (~) -> Flags for testing. RELAUNCH-scoped like the whole scripts channel.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from .. import flags as _flags

DIFFICULTY_BASENAME = "9800_Difficulty.cs"

# sane authoring band for a scale knob: 0.05x (a 20x nerf) .. 20x. Outside this is almost certainly a typo,
# and extreme HP scales walk into cap territory (the C# clamps at 9,999,999 logical HP / 255 for Byte stats).
SCALE_MIN, SCALE_MAX = 0.05, 20.0
_SCALE_KEYS = ("enemy_hp", "enemy_attack", "enemy_magic")
_KNOWN_KEYS = _SCALE_KEYS + ("flag",)

# gEventGlobal is Byte[2048] -> bit indices 0..16383. Real-game bits are legal on purpose (gating hard mode
# on a vanilla story beat is a valid design); the safe CUSTOM band starts at flags.FIRST_SAFE_FLAG.
_FLAG_MAX = 2048 * 8 - 1


class DifficultyError(ValueError):
    pass


@dataclass(frozen=True)
class DifficultySpec:
    hp: float = 1.0
    attack: float = 1.0
    magic: float = 1.0
    flag: "int | None" = None       # resolved gEventGlobal bit index (gate), or None = always on
    flag_label: str = ""            # the author's spelling, for the emitted C# comment


def parse_table(table, *, name_map: "dict | None" = None) -> DifficultySpec:
    """Validate + resolve a raw ``[difficulty]`` table. Raises :class:`DifficultyError` with an authoring-
    facing message; ``name_map`` is the project's ``[[flag]]`` name->index registry (for ``flag = "name"``)."""
    if not isinstance(table, dict):
        raise DifficultyError("[difficulty] must be a table (enemy_hp / enemy_attack / enemy_magic / flag)")
    unknown = sorted(set(table) - set(_KNOWN_KEYS))
    if unknown:
        raise DifficultyError(f"[difficulty] unknown key(s): {unknown} (expected {', '.join(_KNOWN_KEYS)})")
    scales = {}
    for key in _SCALE_KEYS:
        v = table.get(key, 1.0)
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise DifficultyError(f"[difficulty] {key} must be a number (got {v!r})")
        v = float(v)
        if not (SCALE_MIN <= v <= SCALE_MAX):
            raise DifficultyError(f"[difficulty] {key} = {v:g} out of range [{SCALE_MIN:g}, {SCALE_MAX:g}]")
        scales[key] = v
    if all(v == 1.0 for v in scales.values()):
        raise DifficultyError("[difficulty] every scale is 1.0 -- the block does nothing; set at least one "
                              "of enemy_hp / enemy_attack / enemy_magic (or remove the table)")
    flag = None
    label = ""
    if "flag" in table:
        label = str(table["flag"])
        try:
            flag = _flags.resolve(table["flag"], name_map or {})
        except ValueError as e:
            raise DifficultyError(f"[difficulty] flag: {e}")
        if not (0 <= flag <= _FLAG_MAX):
            raise DifficultyError(f"[difficulty] flag {flag} out of range 0..{_FLAG_MAX} (gEventGlobal is "
                                  f"2048 bytes); custom flags belong in the safe band >= {_flags.FIRST_SAFE_FLAG}")
    return DifficultySpec(hp=scales["enemy_hp"], attack=scales["enemy_attack"], magic=scales["enemy_magic"],
                          flag=flag, flag_label=label)


def collect(projects) -> "tuple[DifficultySpec, object] | None":
    """The mod's ONE difficulty spec from a build's projects (the Scripts-DLL is per-MOD, so ``[difficulty]``
    is mod-global like ``[start_inventory]``). Multiple members may repeat an IDENTICAL block (a campaign
    convenience); two DIFFERENT blocks are a hard error -- there is only one hook. Returns (spec, carrier
    project) or ``None``. Raises :class:`DifficultyError`."""
    found = []
    for p in projects:
        raw_table = p.raw.get("difficulty")
        if raw_table is None:
            continue
        names = _flags.collect_flag_defs(p.raw) if isinstance(p.raw, dict) else {}
        spec = parse_table(raw_table, name_map=names)
        found.append((spec, p))
    if not found:
        return None
    distinct = {s for s, _ in found}
    if len(distinct) > 1:
        raise DifficultyError(
            "[difficulty] appears with DIFFERENT settings on more than one field of this build -- the "
            "scaling hook is mod-GLOBAL (one per deployed folder), so the blocks must agree (or live on "
            "only one field).")
    return found[0]


# ---- the C# feature class --------------------------------------------------------------------------------

_SOURCE = """\
// {basename} -- emitted by the ff9mapkit build from [difficulty] (kit {kit_version}). SHIPPED CONTENT.
// Scales ENEMY stats once per battle: {summary}.
// {gate_comment}
// A plain STATIC feature class: the kit-generated Overload hub calls OnBattleInit() at battle init (a call
// site with NO engine default -- nothing vanilla is displaced), BEFORE observer features like telemetry.
// The whole body is try/catch-swallowed: any hiccup degrades to VANILLA scaling, never a broken battle.
using System;
using Memoria;
using Memoria.Data;

namespace Memoria.Scripts.Overload
{{
    public static class DifficultyOverload
    {{
        public static void OnBattleInit()
        {{
            try
            {{
{gate}                foreach (BattleUnit u in BattleState.EnumerateUnits())
                {{
                    if (u.IsPlayer)
                        continue;
{body}                }}
            }}
            catch {{ }}
        }}
    }}
}}
"""

# LOGICAL HP (btl_para.Get/SetLogicalHP under the properties): max first, then current clamped to it.
_HP = """\
                    UInt32 maxHp = (UInt32)Math.Min(9999999.0, Math.Max(1.0, u.MaximumHp * {s}));
                    UInt32 curHp = (UInt32)Math.Min((Double)maxHp, Math.Max(1.0, u.CurrentHp * {s}));
                    u.MaximumHp = maxHp;
                    u.CurrentHp = curHp;
"""

_STR = """\
                    u.Strength = (Byte)Math.Min(255.0, Math.Max(1.0, u.Strength * {s}));
"""

_MGC = """\
                    u.Magic = (Byte)Math.Min(255.0, Math.Max(1.0, u.Magic * {s}));
"""


def _num(x: float) -> str:
    """A C# double literal for a validated scale (repr keeps 1.5 as '1.5'; range-checked upstream)."""
    return f"{x:.6g}"


def render(spec: DifficultySpec) -> str:
    """The C# feature-class source for a validated spec."""
    from .. import __version__
    parts = []
    if spec.hp != 1.0:
        parts.append(f"HP x{_num(spec.hp)}")
    if spec.attack != 1.0:
        parts.append(f"Strength x{_num(spec.attack)}")
    if spec.magic != 1.0:
        parts.append(f"Magic x{_num(spec.magic)}")
    if spec.flag is not None:
        from . import overload as _ovl
        label = f" ({spec.flag_label})" if spec.flag_label and spec.flag_label != str(spec.flag) else ""
        gate = _ovl.flag_gate_cs(spec.flag, label=spec.flag_label)
        gate_comment = (f"Gated on gEventGlobal bit {spec.flag}{label}: bit CLEAR (or any state hiccup) = "
                        f"vanilla; toggle live via the debug menu (~) -> Flags.")
    else:
        gate = ""
        gate_comment = "Always on (no flag gate)."
    body = ""
    if spec.hp != 1.0:
        body += _HP.format(s=_num(spec.hp))
    if spec.attack != 1.0:
        body += _STR.format(s=_num(spec.attack))
    if spec.magic != 1.0:
        body += _MGC.format(s=_num(spec.magic))
    return _SOURCE.format(basename=DIFFICULTY_BASENAME, kit_version=__version__,
                          summary=", ".join(parts), gate_comment=gate_comment, gate=gate, body=body)


def difficulty_dir(layout) -> Path:
    """``…/Scripts/Sources/Difficulty`` -- BUILD-owned (wiped + re-emitted each build, like Sources/Battle;
    unlike the live-owned Telemetry sibling, a deploy REPLACES it)."""
    return layout.scripts_dir / "Sources" / "Difficulty"


def write_source(layout, spec: "DifficultySpec | None") -> "Path | None":
    """Emit (or, for ``spec=None``, REMOVE) the build's difficulty source. The wipe-first mirrors
    ``write_scripts``: a rebuild into a persistent dist dir must not keep a stale scaler after the author
    deletes/changes ``[difficulty]``."""
    d = difficulty_dir(layout)
    shutil.rmtree(d, ignore_errors=True)
    if spec is None:
        return None
    d.mkdir(parents=True, exist_ok=True)
    cs = d / DIFFICULTY_BASENAME
    cs.write_text(render(spec), encoding="utf-8", newline="\n")
    return cs
