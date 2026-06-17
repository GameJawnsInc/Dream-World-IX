"""Field-entry STORY-STATE presets -- the ``[startup]`` block.

A forked field boots with a **zero ``gEventGlobal``**, so every story-gated NPC / door / event / dialogue
takes the not-yet-happened branch and the field plays in its scenario-zero state. ``[startup]`` lets the
author **assert the story beat the forked field represents**: set the ScenarioCounter and/or specific
``gEventGlobal`` story bits, unconditionally, at field load. It is the first lever toward "fork a real story
field and have it boot in the right beat" (see ``docs/FORK_FIDELITY.md`` #1).

The presets run **first in Main_Init** (prepended to entry-0 tag-0) so every gate evaluated afterwards --
region triggers, gated NPCs/doors, conditional content -- sees the asserted state. They re-assert on **every
field entry** (idempotent beat assertion): right for a fork that stands for one beat. For a chain, put
``[startup]`` on the ENTRY field only and advance the story with gateway-side writes (a separate feature).

Grounded entirely in :mod:`ff9mapkit.content.region`'s byte-for-byte primitives: a story bit is
``set_var(GLOB_BOOL, idx, 0|1)``; the ScenarioCounter is the save-backed UInt16 at ``gEventGlobal`` byte 0
(the engine's ``SC_COUNTER`` token ``0xDC``), set via ``set_var(GLOB_UINT16, 0, value)``. Author-side only --
no extraction; the author asserts the beat (they have the game knowledge).
"""
from __future__ import annotations

from . import region as _region
from ..eb import edit

SCENARIO_BYTE = 0          # ScenarioCounter = the save-backed UInt16 at gEventGlobal byte 0 (token 0xDC)
SCENARIO_MAX = 32767       # set_var packs a signed int16; every real beat (<= 12000) fits with margin
WORD_BYTE_MAX = 2046       # a UInt16 word at byte N spans gEventGlobal[N..N+1]; the heap is 2048 bytes
WORD_VALUE_MAX = 0xFFFF
BYTE_BYTE_MAX = 2047       # a single byte at byte N occupies gEventGlobal[N] only; the heap is 2048 bytes
BYTE_VALUE_MAX = 0xFF


def startup_body(presets, scenario=None, words=(), byte_writes=()) -> bytes:
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
    there is nothing to preset (so a field with no ``[startup]`` stays byte-identical)."""
    out = b""
    if scenario is not None:
        out += _region.set_var(_region.GLOB_UINT16, SCENARIO_BYTE, int(scenario))
    for byte_idx, value in words:
        out += _region.set_var(_region.GLOB_UINT16, int(byte_idx), int(value) & WORD_VALUE_MAX)
    for byte_idx, value in byte_writes:
        out += _region.set_var(_region.GLOB_BYTE, int(byte_idx), int(value) & BYTE_VALUE_MAX)
    for idx, val in presets:
        out += _region.set_var(_region.GLOB_BOOL, int(idx), 1 if val else 0)
    return out


def inject_startup(eb, presets, scenario=None, words=(), byte_writes=()) -> bytes:
    """Prepend the preset sequence to **Main_Init** (entry 0, tag 0) so it runs first at field load.

    Byte-safe: inserting at function offset 0 can never be straddled by one of the function's own jumps,
    and :func:`ff9mapkit.eb.edit.insert_in_function` fixes every entry/func table offset. A no-op (returns
    the input bytes unchanged) when there is nothing to preset -- so a field without ``[startup]`` builds
    byte-for-byte as before."""
    body = startup_body(presets, scenario, words, byte_writes)
    if not body:
        return bytes(eb) if isinstance(eb, (bytes, bytearray)) else eb.to_bytes()
    return edit.insert_in_function(eb, 0, 0, 0, body)
