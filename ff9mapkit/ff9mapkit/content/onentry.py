"""Field-ENTRY one-shot hooks -- the ``[[on_entry]]`` block.

A real FF9 field's entry cutscene runs from the field's OWN ``.eb`` (entry-0 + actor sequences), so a
``--verbatim`` fork already carries it. (NOT a C# ``NarrowMapList`` table -- that's the engine's per-field
camera-WIDTH table, no cutscene logic; the old "fires from NarrowMapList, the .eb can't carry it" framing
was a misread -- ``docs/FORK_FIDELITY.md`` #10.) This block is for a **synthesize** fork (which doesn't ship
the donor ``.eb``) and for ADDING a new gated entry beat: fire a lightweight beat (a narration ``message``
and/or story-state writes) the moment the player ENTERS the field, **once**, optionally **gated by the
story state** -- so a fork can fire "the entry cutscene the real field plays at scenario N".

It sits between the existing field-load levers, filling the gap each leaves:

* ``[startup]``    -- presets story state UNCONDITIONALLY on EVERY entry (the flat beat assert).
* ``[cutscene]``   -- a control-locked ordered SEQUENCE (actor choreography), fires once, but UNGATED.
* ``[[event]]``    -- fires on a TREAD / talk zone, not on entry.
* ``[[on_entry]]`` -- fires on field LOAD, **gated by ``requires_flag`` / ``requires_scenario``**, once.

The gating is the new capability: neither ``[startup]`` (unconditional) nor ``[cutscene]`` (ungated)
can say "fire this beat only when the ScenarioCounter is N / story bit B is set".

It arms like a narration cutscene (:func:`ff9mapkit.content.cutscene.inject_cutscene`): a standalone
code entry run by an ``InitCode`` in Main_Init. So it runs at field load, *before* Main_Init re-enables
control -- which is why it has **no movement gate** (an event's ``MOVEMENT_GATE`` would never pass
here, since usercontrol is still 0). A ``message`` beat reuses the cutscene's reorder-``Wait`` +
``DisableMove`` / ``EnableMove`` dance so the window shows cleanly during the entry fade and the player
can't wander while it's up.

Byte-identical when absent: a field with no ``[[on_entry]]`` blocks injects nothing.
"""
from __future__ import annotations

import struct

from ..eb import EbScript, edit, opcodes
from . import region as _region
from . import cutscene as _cutscene
from . import startup as _startup

# Auto once-flag band for a single-field build (a campaign member must pass an explicit `flag = N` --
# its per-member block is fully reserved for cutscene/events/choices). 8300+ sits clear of the event
# (8000+), cutscene (8100) and choice (8200+) auto-bands and below the chest region (8376+).
ONENTRY_FLAG_BASE = 8300


def scenario_gate(value: int) -> bytes:
    """``ifnot (ScenarioCounter == value) { return }`` -- the entry-condition prologue. Same shape as
    :func:`ff9mapkit.content.region.flag_gate` but tests the save-backed UInt16 ScenarioCounter
    (``GLOB_UINT16`` at byte 0) for equality: push ``SC == value``; if TRUE skip the early ``return``."""
    cond = _region.cond_eq(_region.GLOB_UINT16, _startup.SCENARIO_BYTE, int(value))
    return cond + bytes([_region.JMP_TRUE]) + struct.pack("<h", 1) + opcodes.RETURN


def on_entry_body(*, message_txid: int | None = None, set_flag_pairs=(), scenario: int | None = None,
                  once_flag: int | None = None, requires_flag: int | None = None,
                  requires_set: bool = True, requires_scenario: int | None = None) -> bytes:
    """The bytecode for ONE on-entry hook (no entry/return wrapper beyond the trailing ``RETURN``).

    Shape::

        [ifnot requires_flag { return }]          # optional story-bit gate
        [ifnot SC == requires_scenario { return }] # optional beat gate
        if (!once_flag) {                          # once -- omitted when once_flag is None (fires every entry)
            once_flag = 1                          # dedup BEFORE the beat (treasure-chest convention)
            [Wait(2); DisableMove]                 # only when there's a message (lock outlives Main_Init's EnableMove)
            [WindowSync(message_txid)]             # the narration beat
            <set_scenario>; <set_flags...>         # the story-state advance
            [EnableMove]
        }
        return

    The gates sit OUTSIDE the once-block, so a hook whose condition isn't met yet returns without
    spending its once-flag -- it can still fire on a LATER entry once the beat is reached. Returns
    ``b""``-safe building blocks only; raises nothing."""
    gates = b""
    if requires_flag is not None:
        gates += _region.flag_gate(_region.GLOB_BOOL, int(requires_flag), require_set=requires_set)
    if requires_scenario is not None:
        gates += scenario_gate(int(requires_scenario))

    writes = b""
    if scenario is not None:
        writes += _region.set_var(_region.GLOB_UINT16, _startup.SCENARIO_BYTE, int(scenario))
    for idx, val in set_flag_pairs:
        writes += _region.set_var(_region.GLOB_BOOL, int(idx), 1 if val else 0)

    actions = (opcodes.window_sync(1, 128, int(message_txid)) if message_txid is not None else b"") + writes
    if message_txid is not None:
        # mirror the narration cutscene: yield a couple of frames so the lock outlives Main_Init's
        # own EnableMove (which runs in the first frame after this InitCode), then lock for the window.
        inner = (opcodes.wait(_cutscene.REORDER_WAIT) + opcodes.DISABLE_MOVE + actions
                 + opcodes.ENABLE_MOVE)
    else:
        inner = actions

    if once_flag is not None:
        core = _region.if_block(_region.cond_not(_region.GLOB_BOOL, int(once_flag)),
                                _region.set_var(_region.GLOB_BOOL, int(once_flag), 1) + inner)
    else:
        core = inner
    return gates + core + opcodes.RETURN


def inject_on_entries(data, hooks, *, spawn_wait_n: int = 2, spawn_wait_occurrence: int = 0):
    """Inject any number of on-entry hooks. Each becomes a standalone code entry (the body from
    :func:`on_entry_body`) armed by an ``InitCode`` in Main_Init -- the proven narration-cutscene
    arming, run sequentially so each successive ``InitCode`` consumes the next Main_Init ``Wait``
    filler and then INSERTS once the two fillers are spent (safe via the fpos-fixing fallback in
    :func:`ff9mapkit.eb.edit.activate`).

    ``hooks`` is a list of dicts with the resolved keys of :func:`on_entry_body` (``message_txid``,
    ``set_flag_pairs``, ``scenario``, ``once_flag``, ``requires_flag``, ``requires_set``,
    ``requires_scenario``). Returns new ``.eb`` bytes; a no-op (input unchanged) when ``hooks`` is empty."""
    hooks = list(hooks)
    if not hooks:
        return data if isinstance(data, (bytes, bytearray)) else data.to_bytes()
    out = data if isinstance(data, (bytes, bytearray)) else data.to_bytes()
    for h in hooks:
        body = on_entry_body(**h)
        entry = bytes([0x00, 0x01]) + struct.pack("<HH", 0, 4) + body
        slot = EbScript.from_bytes(out).first_free_slot()
        out = edit.append_entry(out, slot, entry)
        out = edit.activate(out, opcodes.init_code(slot, 0), spawn_wait_n=spawn_wait_n,
                            spawn_wait_occurrence=spawn_wait_occurrence)
    return out
