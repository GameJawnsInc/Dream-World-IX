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

from .. import flags as _flags
from ..eb import EbScript, edit, opcodes
from . import region as _region
from . import cutscene as _cutscene
from . import startup as _startup

# Auto once-flag band for a single-field build (a campaign member must pass an explicit `flag = N` --
# its per-member block is fully reserved for cutscene/events/choices). In the safe-band auto bands,
# clear of the event/cutscene/choice/[ate] lanes (the map lives in flags.py; the legacy 8300 base sat
# INSIDE the stock Mognet mailbox slot bytes -- a live save-corrupter).
ONENTRY_FLAG_BASE = _flags.AUTO_ONENTRY_BASE


def scenario_gate(value: int) -> bytes:
    """``ifnot (ScenarioCounter == value) { return }`` -- the entry-condition prologue. Same shape as
    :func:`ff9mapkit.content.region.flag_gate` but tests the save-backed UInt16 ScenarioCounter
    (``GLOB_UINT16`` at byte 0) for equality: push ``SC == value``; if TRUE skip the early ``return``."""
    cond = _region.cond_eq(_region.GLOB_UINT16, _startup.SCENARIO_BYTE, int(value))
    return cond + bytes([_region.JMP_TRUE]) + struct.pack("<h", 1) + opcodes.RETURN


def entrance_gate(entrances) -> bytes:
    """``ifnot (FieldEntrance in entrances) { return }`` -- gate a hook on HOW the player arrived
    (the ``D8:2`` arrival-entrance var every kit warp sets before ``Field()``). One ``if == e skip``
    per value, all landing past the shared early ``return`` -- the beat fires only for a matching
    arrival and burns no once-flag otherwise. This is also what keeps a locked-arrival unlock hook
    OUT of a plain entry: two concurrent entry beats' lock brackets interleave (the first EnableMove
    frees the player mid-scene -- the WINSTYLE intro-dim leak, in-game 2026-08-03), so the unlock
    beat must not run alongside a load cutscene."""
    vals = [int(e) for e in ((entrances,) if isinstance(entrances, int) else entrances)]
    conds = [_region.cond_eq(_region.GLOB_INT16, _region.FIELD_ENTRANCE_IDX, v) for v in vals]
    hop = 3                                        # JMP_TRUE + i16
    out = b""
    for i, cond in enumerate(conds):
        rest = sum(len(c) + hop for c in conds[i + 1:]) + 1          # + the shared RETURN
        out += cond + bytes([_region.JMP_TRUE]) + struct.pack("<h", rest)
    return out + opcodes.RETURN


def on_entry_body(*, message_txid: int | None = None, set_flag_pairs=(), scenario: int | None = None,
                  item_pairs=(), gil: int | None = None,
                  once_flag: int | None = None, requires_flag: int | None = None,
                  requires_set: bool = True, requires_scenario: int | None = None,
                  message_window: int = 1, message_flags: int = 128,
                  message_actor_uid: int | None = None, message_dim=False,
                  message_dim_tint=None, message_lock: bool = True,
                  grant_control: bool = False, entrance=None) -> bytes:
    """The bytecode for ONE on-entry hook (no entry/return wrapper beyond the trailing ``RETURN``).

    Shape::

        [ifnot requires_flag { return }]          # optional story-bit gate
        [ifnot SC == requires_scenario { return }] # optional beat gate
        if (!once_flag) {                          # once -- omitted when once_flag is None (fires every entry)
            once_flag = 1                          # dedup BEFORE the beat (treasure-chest convention)
            [Wait(2); DisableMove]                 # only when there's a message (lock outlives Main_Init's EnableMove)
            [WindowSync(message_txid)]             # the narration beat
            <set_scenario>; <set_flags...>         # the story-state advance
            <give_item...>; <give_gil>             # per-entry starting bag/gil (scripted, not the global CSV)
            [EnableMove]
        }
        return

    The gates sit OUTSIDE the once-block, so a hook whose condition isn't met yet returns without
    spending its once-flag -- it can still fire on a LATER entry once the beat is reached. Returns
    ``b""``-safe building blocks only; raises nothing."""
    gates = b""
    if entrance is not None:
        gates += entrance_gate(entrance)
    if requires_flag is not None:
        gates += _region.flag_gate(_region.GLOB_BOOL, int(requires_flag), require_set=requires_set)
    if requires_scenario is not None:
        gates += scenario_gate(int(requires_scenario))

    writes = b""
    if scenario is not None:
        writes += _region.set_var(_region.GLOB_UINT16, _startup.SCENARIO_BYTE, int(scenario))
    for idx, val in set_flag_pairs:
        writes += _region.set_var(_region.GLOB_BOOL, int(idx), 1 if val else 0)
    # Per-entry STARTING ITEMS (a journey's per-destination bag/gil, scripted -- not the mod-GLOBAL
    # New-Game CSV that a whole hub shares). They sit inside the once-block, so they're given exactly
    # ONCE per save (the once-flag dedups), and behind the optional requires_scenario beat gate.
    if item_pairs or gil is not None:
        from . import event as _event
        for item_id, count in item_pairs:
            writes += _event.give_item(item_id, int(count))
        if gil is not None:
            writes += _event.give_gil(int(gil))

    if message_txid is not None:
        from . import event as _event
        win_op = _event.message(int(message_txid), window=int(message_window),
                                flags=int(message_flags), actor_uid=message_actor_uid,
                                dim=message_dim, dim_tint=message_dim_tint)
    else:
        win_op = b""
    actions = win_op + writes
    if message_txid is not None and message_lock:
        # mirror the narration cutscene: yield a couple of frames so the lock outlives Main_Init's
        # own EnableMove (which runs in the first frame after this InitCode), then lock for the window.
        # message_lock=False is the passive-banner opt-out (stock's 6 lock-free WindowAsync banners):
        # the beat shows with the player free to walk -- no reorder dance needed.
        inner = (opcodes.wait(_cutscene.REORDER_WAIT) + opcodes.DISABLE_MOVE + actions
                 + opcodes.ENABLE_MOVE)
    else:
        inner = actions

    if once_flag is not None:
        core = _region.if_block(_region.cond_not(_region.GLOB_BOOL, int(once_flag)),
                                _region.set_var(_region.GLOB_BOOL, int(once_flag), 1) + inner)
    else:
        core = inner
    if grant_control:
        # the ARRIVE-LOCKED grant ([player] locked_entrances): the field-entry grant was entrance-
        # gated away, so THIS hook owns handing control back -- unconditionally, OUTSIDE the once
        # block (a revisit that skips the once'd beat must still grant, or the player arrives frozen
        # forever). The stock enable-macro shape: re-arm the MAP-158 latch (Main_Reinit's re-affirm
        # reads it), EnableMove, unmask the walkmesh triangles, EnableMenu.
        core += (_region.set_var(_region.MAP_BOOL, 158, 1) + opcodes.ENABLE_MOVE
                 + opcodes.encode(0x27, 255) + opcodes.ENABLE_MENU)
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
