"""Save-point synthesis -- a functional FF9 save point as a press-to-interact region.

The FUNCTIONAL save is a single opcode: ``Menu(4, 0)`` (0x75) -> ``EventService.StartMenu`` ->
``OpenSaveMenu`` (``SaveLoadUI.SerializeType.Save``). Verified byte-exact (``75 00 04 00``) against the
real Dali save moogle (field 122 entry 5 tag 3). The real moogle's full act -- jump out of the barrel,
the Save/Shop dialogue choice, the player-pose ``RunScriptAsync`` surgery -- is COSMETIC; none of it is
needed to save the game. So instead of grafting that un-graftable 7-entry-ish cluster, the kit SYNTHESIZES
the save: a press-action region whose interact func opens the save menu.

It is the navigable cousin of :mod:`content.jump`'s ``action`` region -- same Init ``SetRegion`` / tread
``Bubble`` ("!") / action shape -- but the action dispatch is ``DisableMove; Menu(4, 0); EnableMove``
instead of a player-arc ``RunScriptSync`` (so, unlike a jump, NO player-function graft is required; the
save is a self-contained engine call). The optional visible barrel/moogle set-dressing + the cosmetic
jump-out are a separate, later layer (place a ``[[prop]]``/``[[npc]]`` over the zone); this is the
functional core.
"""
from __future__ import annotations

import struct

from ..eb import EbScript, edit, opcodes
from . import region as _region

SAVE_MENU_ID = 4          # EventService.FF9Menu_Command case 4u -> OpenSaveMenu
SAVE_SUB_ID = 0           # OpenSaveMenu requires sub_id == 0


def save_dispatch() -> bytes:
    """The interact body: ``DisableMove; Menu(4, 0); EnableMove; RETURN``. Locks control while the save
    UI is up (so the player can't walk under it) and restores it after -- mirrors the jump action's
    ``DisableMove ... EnableMove`` bracket, with the save menu in place of the arc."""
    return (opcodes.DISABLE_MOVE
            + opcodes.menu(SAVE_MENU_ID, SAVE_SUB_ID)
            + opcodes.ENABLE_MOVE + opcodes.RETURN)


def _assemble_entry(funcs) -> bytes:
    """Assemble a type-1 (region) entry from ``[(tag, body), ...]`` -- the func table (4 bytes/func:
    ``<tag:u16><fpos:u16>``) then the concatenated bodies. Same layout as :func:`content.jump`."""
    table = b""
    pos = len(funcs) * 4
    for tag, body in funcs:
        table += struct.pack("<HH", tag, pos)
        pos += len(body)
    return bytes([_region.REGION_ENTRY_TYPE, len(funcs)]) + table + b"".join(b for _, b in funcs)


def savepoint_region(zone, *, bubble: bool = True) -> bytes:
    """A type-1 region entry for a save point: Init ``SetRegion(zone)`` / tread (tag 2) ``Bubble(1)`` (the
    floating "!" prompt, if ``bubble``) / action (tag 3) :func:`save_dispatch`. Both trigger funcs are
    gated by :data:`content.region.MOVEMENT_GATE` (fire only while ``usercontrol == 1``), exactly like
    every real exit/switch/jump region."""
    init = _region.set_region([tuple(p) for p in zone]) + opcodes.RETURN
    tread = _region.MOVEMENT_GATE + (opcodes.bubble(1) if bubble else b"") + opcodes.RETURN
    action = _region.MOVEMENT_GATE + save_dispatch()
    funcs = [(0, init), (_region.RANGE_TAG, tread), (_region.INTERACT_TAG, action)]
    return _assemble_entry(funcs)


def inject_savepoint(data, zone, *, bubble: bool = True, activate: bool = True):
    """Inject one save point: append a save-point region at the next free slot and arm it (``InitRegion``
    in Main_Init). Returns ``(new_bytes, region_slot)``. ``zone`` is a 4- or 5-point quad (the press
    area); ``bubble=False`` hides the "!" prompt (e.g. when a visible model already signals the save)."""
    eb = EbScript.from_bytes(data)
    slot = eb.first_free_slot()
    data = edit.append_entry(data, slot, savepoint_region(zone, bubble=bubble))
    if activate:
        data = edit.activate(data, opcodes.init_region(slot, 0))
    return data, slot


def inject_savepoints(data, savepoints, *, activate: bool = True):
    """Inject every ``[[savepoint]]`` (each a dict with ``zone`` + optional ``bubble``). Returns
    ``(new_bytes, [slot, ...])``."""
    slots = []
    for sp in savepoints:
        data, slot = inject_savepoint(data, sp["zone"], bubble=sp.get("bubble", True), activate=activate)
        slots.append(slot)
    return data, slots
