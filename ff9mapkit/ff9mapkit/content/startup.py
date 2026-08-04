"""Field-entry STORY-STATE presets -- the ``[startup]`` block.

A forked field boots with a **zero ``gEventGlobal``**, so every story-gated NPC / door / event / dialogue
takes the not-yet-happened branch and the field plays in its scenario-zero state. ``[startup]`` lets the
author **assert the story beat the forked field represents**: set the ScenarioCounter and/or specific
``gEventGlobal`` story bits, unconditionally, at field load. It is the first lever toward "fork a real story
field and have it boot in the right beat" (see ``docs/FORK_FIDELITY.md`` #1).

The presets run **first in Main_Init** (prepended to entry-0 tag-0) so every gate evaluated afterwards --
region triggers, gated NPCs/doors, conditional content -- sees the asserted state. By default they
re-assert on **every field entry** (idempotent beat assertion): right for a single fork that stands for
one beat. For a CHAIN that is a progression killer -- the player's own advances (the resident scripts
writing a new ScenarioCounter, once-bits latching) get REWOUND at every door (the Dali round-5 lesson:
the shop scene advanced 2600 -> 2610 and leaving the shop stamped 2600 back). ``once = <flag>`` wraps
the whole stamp in a sentinel GLOB-bit guard: the FIRST entry into any member stamps the beat and sets
the sentinel; every later entry leaves the running story alone. Share ONE sentinel across a chain's
members. New Game zeroes ``gEventGlobal``, so a fresh run re-stamps.

Grounded entirely in :mod:`ff9mapkit.content.region`'s byte-for-byte primitives: a story bit is
``set_var(GLOB_BOOL, idx, 0|1)``; the ScenarioCounter is the save-backed UInt16 at ``gEventGlobal`` byte 0
(the engine's ``SC_COUNTER`` token ``0xDC``), set via ``set_var(GLOB_UINT16, 0, value)``. Author-side only --
no extraction; the author asserts the beat (they have the game knowledge).
"""
from __future__ import annotations

from . import region as _region
from ..eb import edit, opcodes

SCENARIO_BYTE = 0          # ScenarioCounter = the save-backed UInt16 at gEventGlobal byte 0 (token 0xDC)
SCENARIO_MAX = 32767       # set_var packs a signed int16; every real beat (<= 12000) fits with margin
WORD_BYTE_MAX = 2046       # a UInt16 word at byte N spans gEventGlobal[N..N+1]; the heap is 2048 bytes
WORD_VALUE_MAX = 0xFFFF
BYTE_BYTE_MAX = 2047       # a single byte at byte N occupies gEventGlobal[N] only; the heap is 2048 bytes
BYTE_VALUE_MAX = 0xFF


def scenario_window_conds(scenario_min=None, scenario_max=None) -> list:
    """The beat window ``[scenario_min, scenario_max)`` as CALL-SITE guard conds -- a list of
    ``(cond_bytes, proceed_when_true)`` for :func:`ff9mapkit.content.region.guarded_call` around an
    ``InitObject`` (the stock rotating-cast idiom: gate the ACTIVATION in Main_Init, so out-of-window
    the object is never created).

    - ``scenario_min``: proceed only while ``SC >= min`` -> absent before the beat opens.
    - ``scenario_max``: proceed only while ``SC < max``  -> absent once the beat has passed (EXCLUSIVE
      upper bound, so adjacent members tile seamlessly: ``[a, b)`` then ``[b, c)``).

    Both optional (a one-sided window is fine); ``[]`` when neither bound is given. Each cond is the
    SIMPLE ``05 DC 00 7D <u16> <cmp> 7F`` shape ``forkreport._sc_cond`` decodes, so ``fork-report``'s
    per-beat roster evaluates these guards exactly.

    ⚠ Replaces the retired init-prologue ``scenario_window_gate``: a gate INSIDE an object's Init
    (returning before ``SetModel``) is a stock-unexercised path that loads the object PERMANENTLY
    HIDDEN when the gate passes -- see the OBJECT-INIT GATE LAW on ``region.guarded_call`` (the
    invisible-innkeeper bisect, in-game proven 2026-07-12)."""
    conds = []
    if scenario_min is not None:
        conds.append((_region.cond_cmp(_region.GLOB_UINT16, SCENARIO_BYTE, int(scenario_min), ">="), True))
    if scenario_max is not None:
        conds.append((_region.cond_cmp(_region.GLOB_UINT16, SCENARIO_BYTE, int(scenario_max), "<"), True))
    return conds


def startup_body(presets, scenario=None, words=(), byte_writes=(), once_flag=None) -> bytes:
    """The Main_Init preset sequence (the bare bytecode, no entry/return wrapper -- it is prepended INTO
    Main_Init). ``scenario`` (int, or None) sets the ScenarioCounter; ``presets`` is an iterable of
    ``(bit_index, value)`` story-bit pairs (truthy -> set, falsy -> clear). Two width-distinct word levers:

    - ``words``: ``(byte_index, value)`` pairs writing a save-backed **UInt16** to ``gEventGlobal[byte_index]``
      -- a 16-bit value spanning bytes ``[N, N+1]`` (the lever for a 16-bit mask the scenario counter doesn't
      cover, e.g. the **ATE-availability bitmask at byte 236**; see docs/ATE_SYSTEM.md). ⚠ Because it is two
      bytes, a UInt16 write to ``N`` also sets byte ``N+1`` (to ``value >> 8``) -- so ``value < 256`` ZEROES
      the neighbour. To set a single byte without touching its neighbour, use ``byte_writes``.
    - ``byte_writes``: ``(byte_index, value)`` pairs writing a save-backed **single byte** (0..255) to
      ``gEventGlobal[byte_index]`` ONLY -- no neighbour clobber. The right lever for adjacent independent
      config bytes (e.g. the Pandemonium lift pair byte361=4 + byte362=6).

    Writes run scenario -> words -> byte_writes -> bits, so a later, narrower write refines an earlier wider
    one (a ``byte`` can fix one byte of a seeded ``word``; a ``flag`` can refine one bit). Returns ``b""`` when
    there is nothing to preset (so a field with no ``[startup]`` stays byte-identical).

    ``once_flag`` (a GLOB bit index): wrap the whole stamp in the once-sentinel guard --
    ``if (Bit[once_flag] == 0) { <stamp>; Bit[once_flag] = 1 }`` -- so the state is asserted exactly
    once per save and the player's own progression is never rewound (the chain lever)."""
    out = b""
    if scenario is not None:
        out += _region.set_var(_region.GLOB_UINT16, SCENARIO_BYTE, int(scenario))
    for byte_idx, value in words:
        out += _region.set_var(_region.GLOB_UINT16, int(byte_idx), int(value) & WORD_VALUE_MAX)
    for byte_idx, value in byte_writes:
        out += _region.set_var(_region.GLOB_BYTE, int(byte_idx), int(value) & BYTE_VALUE_MAX)
    for idx, val in presets:
        out += _region.set_var(_region.GLOB_BOOL, int(idx), 1 if val else 0)
    if out and once_flag is not None:
        out = _region.if_block(
            _region.cond_eq(_region.GLOB_BOOL, int(once_flag), 0),
            out + _region.set_var(_region.GLOB_BOOL, int(once_flag), 1))
    return out


def inject_startup(eb, presets, scenario=None, words=(), byte_writes=(), once_flag=None,
                   always_words=()) -> bytes:
    """Prepend the preset sequence to **Main_Init** (entry 0, tag 0) so it runs first at field load.

    Byte-safe: inserting at function offset 0 can never be straddled by one of the function's own jumps,
    and :func:`ff9mapkit.eb.edit.insert_in_function` fixes every entry/func table offset. A no-op (returns
    the input bytes unchanged) when there is nothing to preset -- so a field without ``[startup]`` builds
    byte-for-byte as before. ``once_flag`` guards the seed writes (see :func:`startup_body`);
    ``always_words`` are word writes that stay OUTSIDE the guard and run every entry (the ``outpost``
    registration is last-write-wins by contract)."""
    body = startup_body(presets, scenario, words, byte_writes, once_flag)
    body += startup_body([], None, always_words)
    if not body:
        return bytes(eb) if isinstance(eb, (bytes, bytearray)) else eb.to_bytes()
    return edit.insert_in_function(eb, 0, 0, 0, body)
