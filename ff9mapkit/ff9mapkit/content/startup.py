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


def startup_body(presets, scenario=None) -> bytes:
    """The Main_Init preset sequence (the bare bytecode, no entry/return wrapper -- it is prepended INTO
    Main_Init). ``scenario`` (int, or None) sets the ScenarioCounter; ``presets`` is an iterable of
    ``(bit_index, value)`` pairs (value truthy -> set the bit, falsy -> clear it). Returns ``b""`` when
    there is nothing to preset (so the caller stays byte-identical to a field with no ``[startup]``)."""
    out = b""
    if scenario is not None:
        out += _region.set_var(_region.GLOB_UINT16, SCENARIO_BYTE, int(scenario))
    for idx, val in presets:
        out += _region.set_var(_region.GLOB_BOOL, int(idx), 1 if val else 0)
    return out


def inject_startup(eb, presets, scenario=None) -> bytes:
    """Prepend the preset sequence to **Main_Init** (entry 0, tag 0) so it runs first at field load.

    Byte-safe: inserting at function offset 0 can never be straddled by one of the function's own jumps,
    and :func:`ff9mapkit.eb.edit.insert_in_function` fixes every entry/func table offset. A no-op (returns
    the input bytes unchanged) when there is nothing to preset -- so a field without ``[startup]`` builds
    byte-for-byte as before."""
    body = startup_body(presets, scenario)
    if not body:
        return bytes(eb) if isinstance(eb, (bytes, bytearray)) else eb.to_bytes()
    return edit.insert_in_function(eb, 0, 0, 0, body)
