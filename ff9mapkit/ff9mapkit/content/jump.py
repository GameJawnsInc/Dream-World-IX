"""Jump-navigation primitive -- FF9's ledge/gap jumps (Ice Cavern, etc.), the navigable cousin of the
ladder. Decoded byte-for-byte from Ice Cavern/Hall (field 301):

  - a JUMP REGION entry (one per ledge): Init ``SetRegion(zone)`` / tread (tag 2) ``Bubble(1)`` (the
    floating "!" prompt) / action (tag 3) ``DisableMove; RunScriptSync(player, <jump_tag>); EnableMove``.
  - the player's JUMP-ARC function (``jump_tag``): runs in the player's OWN context (so it moves the
    PLAYER), a verbatim ``TurnTowardPosition; RunJumpAnimation; SetupJump(x,y,z,steps); Jump;
    RunLandAnimation; ...; SetPathing(1)`` arc -- the EXACT, perspective-tuned world coords (they trace
    the painted ledge through the fixed camera, so they can only be COPIED, never regenerated -- same
    truth as ladder climb arcs).

Two trigger styles exist in the real game and both are supported:
  * ``action`` (Ice Cavern 301): walk to the ledge -> "!" prompt -> press the action button to jump.
  * ``tread`` (e.g. field 402): the jump auto-fires the moment you walk into the zone (no prompt).

Why the SAME region/RunScriptSync shape as a ladder (not a region->flag->player-loop scheme): while
``usercontrol == 1`` the controlled player's script loop is NOT stepped, so the region must call the
player's jump arc DIRECTLY via ``RunScriptSync`` (exactly what the real game does). This module is the
ladder mechanism minus the climb semantics (no ladder flag, no hold-to-climb loop) -- a one-shot arc.

The arc's ``RunJumpAnimation`` plays whatever ``SetJumpAnimation`` last set; the blank-field player
(the fork's player) is always Zidane (model 98,93 -- same as the real jump fields), so we splice
``SetJumpAnimation(10447, 4, 14)`` (Zidane's jump clip, from the real player Init) into the player
Init once, and every grafted arc animates correctly.
"""
from __future__ import annotations

import struct

from ..eb import EbScript, edit, opcodes
from . import region as _region
from .ladder import find_player_entry

PLAYER_UID = 250          # the controlled player's runtime UID (referenced regardless of entry index)
FIRST_JUMP_TAG = 40       # player jump-arc funcs start here -- clear of the ladder climb tags (17+)
RUNSCRIPT_LEVEL = 2       # the script level RunScriptSync uses (matches the real jump/ladder triggers)
SET_JUMP_ANIM_OP = 0x94   # SetJumpAnimation(anim, a, b)
JUMP_ANIM_DEFAULT = (10447, 4, 14)   # Zidane's jump clip + in/out frames (real Ice Cavern player Init)


def _assemble_entry(funcs) -> bytes:
    """Assemble a type-1 (region) entry from ``[(tag, body), ...]`` -- the func table (4 bytes/func:
    ``<tag:u16><fpos:u16>``) then the concatenated bodies. Same layout as ladder_region."""
    table = b""
    pos = len(funcs) * 4
    for tag, body in funcs:
        table += struct.pack("<HH", tag, pos)
        pos += len(body)
    return bytes([_region.REGION_ENTRY_TYPE, len(funcs)]) + table + b"".join(b for _, b in funcs)


def jump_region(zone, jump_tag: int, *, trigger: str = "action", bubble: bool = True,
                player_uid: int = PLAYER_UID) -> bytes:
    """A type-1 region entry that fires the player's jump arc (func ``jump_tag``).

    ``trigger="action"`` (default, Ice Cavern style): Init ``SetRegion`` / tread ``Bubble(1)`` (if
    ``bubble``) / action ``DisableMove; RunScriptSync(player, jump_tag); EnableMove`` -- press to jump.
    ``trigger="tread"``: the dispatch is on the tread func (auto-jump on walk-in); an optional ``!``.
    The dispatch is SYNCHRONOUS (``RunScriptSync``) so player control is held for the duration of the
    arc, then restored."""
    init = _region.set_region(zone) + opcodes.RETURN
    dispatch = (opcodes.DISABLE_MOVE
                + opcodes.run_script_sync(RUNSCRIPT_LEVEL, player_uid, jump_tag)
                + opcodes.ENABLE_MOVE + opcodes.RETURN)
    if trigger == "tread":
        body = _region.MOVEMENT_GATE
        if bubble:
            body += opcodes.bubble(1)
        body += dispatch
        funcs = [(0, init), (_region.RANGE_TAG, body)]
    else:                                                    # "action" -- press-to-jump (+ "!" prompt)
        tread = _region.MOVEMENT_GATE + (opcodes.bubble(1) if bubble else b"") + opcodes.RETURN
        action = _region.MOVEMENT_GATE + dispatch
        funcs = [(0, init), (_region.RANGE_TAG, tread), (_region.INTERACT_TAG, action)]
    return _assemble_entry(funcs)


def ensure_jump_animation(data, anim=JUMP_ANIM_DEFAULT):
    """Splice ``SetJumpAnimation(*anim)`` into the player Init (once), so the grafted arcs'
    ``RunJumpAnimation`` plays the right clip. No-op if the player Init already sets a jump animation
    (e.g. a field that carries its own). Spliced right after ``DefinePlayerCharacter`` (jump-safe, the
    proven re-entry-spawn splice point)."""
    eb = EbScript.from_bytes(data)
    pe = find_player_entry(eb)
    init = eb.entry(pe).func_by_tag(0)
    if init is None:
        raise ValueError("player entry has no Init (tag 0); cannot set the jump animation")
    if any(ins.op == SET_JUMP_ANIM_OP for ins in eb.instrs(init)):
        return data                                          # already sets a jump anim -- leave it
    dpc = next((i for i in eb.instrs(init) if i.op == 0x2C), None)   # DefinePlayerCharacter
    rel = (dpc.end - init.abs_start) if dpc is not None else 0       # after DPC, else prepend
    return edit.insert_in_function(data, pe, 0, rel, opcodes.set_jump_animation(*anim))


def inject_jump(data, zone, jump_bytes: bytes, *, jump_tag: int = FIRST_JUMP_TAG,
                trigger: str = "action", bubble: bool = True, player_uid: int = PLAYER_UID,
                activate: bool = True):
    """Inject one navigable jump: graft the verbatim jump-arc ``jump_bytes`` onto the player entry as
    func ``jump_tag``, append a jump region that fires it, and arm the region. Returns
    ``(new_bytes, region_slot)``. For multiple jumps pass a distinct ``jump_tag`` each.

    ``jump_bytes`` is a real jump arc extracted verbatim by ``eventscan.scan_jumps`` (exact,
    perspective-correct world coords); it's grafted as-is. Pair with :func:`ensure_jump_animation`
    once per field so the arc's ``RunJumpAnimation`` has a clip."""
    eb = EbScript.from_bytes(data)
    pe = find_player_entry(eb)
    data = edit.add_function(data, pe, jump_tag, bytes(jump_bytes))
    eb = EbScript.from_bytes(data)
    slot = eb.first_free_slot()
    data = edit.append_entry(data, slot, jump_region([tuple(p) for p in zone], jump_tag,
                                                     trigger=trigger, bubble=bubble, player_uid=player_uid))
    if activate:
        data = edit.activate(data, opcodes.init_region(slot, 0))
    return data, slot
