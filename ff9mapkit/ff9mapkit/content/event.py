"""One-shot field EVENTS -- walk-into-a-zone triggers that fire authored logic, optionally once.

This is the conditional-region primitive (:mod:`ff9mapkit.content.region`) cashed in as authorable
content. An event is a region whose ``_Range`` runs a composed sequence -- show a message, give an
item / gil, set a story flag -- gated by a GlobBool so an ``once`` event (a looted chest, a one-time
line, an ATE) never re-fires. Same shape the real game uses for treasure (decoded from a real chest
handler: ``AddItem`` + a "received X" ``WindowSync``) and the same flag-gated ``if (!done){..;
done=1}`` the camera-switch zones use.

Compose a body from the part builders (:func:`message` / :func:`give_item` / :func:`give_gil` /
:func:`set_flag`); :func:`inject_events` adds any number of events through a SINGLE arming entry (so
they don't each consume a Main_Init ``Wait`` filler).
"""

from __future__ import annotations

import struct

from .. import items as _items
from ..eb import EbScript, edit, opcodes
from . import region as _region

# 'once' flags live in the SAVE-PERSISTENT Global bool (region.GLOB_BOOL) so a looted chest / one-time
# event stays done across field reloads + saves. The base is high in gEventGlobal (byte ~1000) to stay
# clear of the base game's flags (which sit low); override per event with `flag = N`.
EVENT_FLAG_CLASS = _region.GLOB_BOOL
EVENT_FLAG_BASE = 8000


def message(text_id: int, *, window: int = 1, flags: int = 128) -> bytes:
    """Body part: open a dialogue window (WindowSync) showing text ``text_id``."""
    return opcodes.window_sync(window, flags, text_id)


def give_item(item_id, count: int = 1) -> bytes:
    """Body part: AddItem(item, count). ``item_id`` may be a numeric id OR a name ("Potion") --
    resolved via :mod:`ff9mapkit.items` so authors don't have to memorize ids. Works for ANY item,
    including weapons/armor ("Excalibur") -- the engine renders the name in the "Received X" box."""
    return opcodes.add_item(_items.resolve(item_id), count)


def take_item(item_id, count: int = 1) -> bytes:
    """Body part: RemoveItem(item, count) -- the symmetric counterpart of :func:`give_item` (a trade,
    a quest-item consume). ``item_id`` may be a numeric id OR a name; the engine clamps to what's held."""
    return opcodes.remove_item(_items.resolve(item_id), count)


def give_gil(amount: int) -> bytes:
    """Body part: change the party's gil by ``amount`` -- positive ADDS (AddGil), negative SUBTRACTS
    (RemoveGil). The two opcodes both take an unsigned amount, so we pick by sign here (a negative
    ``amount`` would otherwise wrap to a huge ADD and max out gil)."""
    return opcodes.add_gil(amount) if amount >= 0 else opcodes.remove_gil(-amount)


def set_flag(flag_idx: int, value: int = 1, *, flag_class=EVENT_FLAG_CLASS) -> bytes:
    """Body part: set a GlobBool story flag (gate other content on it)."""
    return _region.set_var(flag_class, flag_idx, value)


def reveal_object(slot: int) -> bytes:
    """Body part: re-run an object's Init (``InitObject``). Used after :func:`set_flag` to make a
    flag-gated NPC appear (or vanish) LIVE in the same room -- its Init re-evaluates the gate with the
    flag's new value (without this, a gated NPC only updates on field re-entry, since Init runs once
    at spawn)."""
    return opcodes.init_object(slot, 0)


# RunSoundCode(265, 65535): the field-transition whoosh present byte-identically in EVERY real warp
# (verified in the airship 455<->457, the Dali innkeeper 351->352, Gargan Roo 950->914 talk handlers).
WARP_SOUND = (265, 65535)


def warp(target: int) -> bytes:
    """Body part: warp the player to ``Field(target)``. Grounded in real *talk-handler* warps -- a Field
    op TRANSITIONS directly from an event / tag-3 _SpeakBTN context (unlike a bare Field in Main_Init,
    which no-ops -- see memory project_ff9_field_warp_pattern); 14+ shipping fields warp the player from a
    tag-3 handler this way (the Dali innkeeper, the airship, Gargan Roo...). Plays the transition sound,
    then warps. The warp TRANSITIONS AWAY, so this MUST be the LAST part of a body (anything after is
    unreachable). (The real warps also run a fade -- constant writes to the screen-fade vars + step ops;
    omitted here as cosmetic polish. If the cut reads abrupt in-game, splice the proven fade tail.)"""
    return opcodes.run_sound_code(*WARP_SOUND) + opcodes.field(int(target))


def set_scenario(value: int) -> bytes:
    """Body part: set the ScenarioCounter (the story beat) -- the save-backed gEventGlobal UInt16 @0.
    Reuses :func:`ff9mapkit.content.startup.startup_body` (story_flags' lever) so an event/choice can
    advance the beat (e.g. a hub journey-pick seeds the destination's beat before the warp)."""
    from . import startup as _startup
    return _startup.startup_body([], scenario=int(value))


def event_range_body(body: bytes, once_flag: int | None, flag_class=EVENT_FLAG_CLASS,
                     requires_flag: int | None = None, requires_set: bool = True,
                     space_item: int | None = None) -> bytes:
    """The region ``_Range`` body for an event: a movement gate, an optional ``requires_flag`` story
    gate (the event only fires when that flag is in-state), then ``body`` -- gated
    ``if (!flag) { flag = 1; body }`` when ``once_flag`` is set, so it fires once. The once-flag is set
    BEFORE the body, matching FF9's treasure-chest convention (``if(!opened){ opened=1; reward; msg }``):
    the dedup flag lands the instant the event fires, before any (movement-unblocking) reward message --
    so it can't double-fire even if the reward window is left open.

    ``space_item`` (a chest nicety) wraps everything in ``if (GetItemCount(item) < 99) { ... }`` so the
    reward is skipped (and the once-flag NOT set -> retryable) when the bag is full -- exactly FF9's
    item-chest guard, with the space check OUTERMOST."""
    parts = [_region.MOVEMENT_GATE]
    if requires_flag is not None:
        parts.append(_region.flag_gate(flag_class, requires_flag, require_set=requires_set))
    if once_flag is not None:
        core = _region.if_block(_region.cond_not(flag_class, once_flag),
                                _region.set_var(flag_class, once_flag, 1) + body)
    else:
        # No once flag = the raw region trigger: tag 2 is LEVEL-triggered (the engine fires it every
        # frame the player treads the quad -- TreadQuad is a pure position test, no edge detection), so
        # a `once=false` message re-fires as soon as it closes while still inside. Correct for a
        # continuous effect; edge-triggered "once per visit" would need a leave-detecting re-arm zone.
        core = body
    if space_item is not None:                       # FF9 chest: only give if there's room (space outermost)
        core = _region.if_block(_region.cond_item_count_lt(space_item), core)
    parts.append(core)
    parts.append(opcodes.RETURN)
    return b"".join(parts)


def inject_event(data, *, zone, body: bytes, once_flag: int | None = None,
                 requires_flag: int | None = None, requires_set: bool = True,
                 flag_class=EVENT_FLAG_CLASS, slot=None, spawn_wait_n: int = 2,
                 spawn_wait_occurrence: int = 0):
    """Inject ONE walk-in event region (armed at load via InitRegion-over-Wait). Returns
    ``(new_bytes, slot)``. For several events prefer :func:`inject_events` (one shared arm entry)."""
    range_body = event_range_body(body, once_flag, flag_class, requires_flag, requires_set)
    return _region.inject_region(data, zone, range_body, slot=slot, activate=True,
                                 spawn_wait_n=spawn_wait_n, spawn_wait_occurrence=spawn_wait_occurrence)


def inject_events(data, events, *, flag_class=EVENT_FLAG_CLASS, spawn_wait_n: int = 2,
                  spawn_wait_occurrence: int = 0) -> bytes:
    """Inject many events through a single arming entry. ``events`` is a list of dicts with keys
    ``zone`` (corners), ``body`` (composed action bytes), ``once_flag`` (int or None).

    Each event becomes a region (appended, not auto-armed); one type-0 code entry then ``InitRegion``s
    them all and is activated once via ``InitCode`` over a Main_Init ``Wait`` filler -- so N events
    cost ONE filler, not N. Returns new .eb bytes."""
    events = list(events)
    if not events:
        return data if isinstance(data, (bytes, bytearray)) else data.to_bytes()
    out = data if isinstance(data, (bytes, bytearray)) else data.to_bytes()
    region_slots = []
    for ev in events:
        rb = event_range_body(ev["body"], ev.get("once_flag"), flag_class,
                              ev.get("requires_flag"), ev.get("requires_set", True),
                              space_item=ev.get("space_item"))
        out, slot = _region.inject_region(out, ev["zone"], rb, activate=False)
        region_slots.append(slot)

    arm = b"".join(opcodes.init_region(s, 0) for s in region_slots) + opcodes.RETURN
    arm_entry = bytes([0x00, 0x01]) + struct.pack("<HH", 0, 4) + arm
    arm_slot = EbScript.from_bytes(out).first_free_slot()
    out = edit.append_entry(out, arm_slot, arm_entry)
    out = edit.activate(out, opcodes.init_code(arm_slot, 0), spawn_wait_n=spawn_wait_n,
                        spawn_wait_occurrence=spawn_wait_occurrence)
    return out
