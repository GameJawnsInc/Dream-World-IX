"""Jump-navigation primitive -- FF9's ledge/gap jumps (Ice Cavern, etc.), the navigable cousin of the
ladder. Decoded byte-for-byte from Ice Cavern/Hall (field 301):

  - a JUMP REGION entry (one per ledge): Init ``SetRegion(zone)`` / tread (tag 2) ``Bubble(1)`` (the
    floating "!" prompt) / action (tag 3) ``DisableMove; RunScriptSync(player, <jump_tag>); EnableMove``.
  - the player's JUMP-ARC function (``jump_tag``): runs in the player's OWN context (so it moves the
    PLAYER) -- per hop ``TurnTowardPosition; WaitTurn; RunJumpAnimation; sfx; SetupJump(x,z,y,steps);
    Jump; StopAnimation; sfx; RunLandAnimation; WaitAnimation``, then ``SetPathing(1)``. A FORK grafts
    the real arc verbatim; a from-scratch jump GENERATES the same template from just the landing
    point(s) (:func:`jump_arc_body` -- the arc coords are world-space and the engine projects them
    through the fixed camera, so like ladder endpoints they come off the paint guide; byte-identical
    to field 301's arcs for the same inputs).

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

# From-scratch arc constants -- grounded in a full-game census (2026-07-22: 51 navigable hops over 15
# fields, scan_jumps over every field's .eb). The Ice Cavern hop template is the game-wide MODAL shape,
# and its sfx pair is the dominant one everywhere (leap 1324 x52, land 2342 x34; a few fields swap the
# land thud for a surface-specific id -- overridable). `steps` is per-gap tuning in the real game
# (5..16; 11 = the mode and every Ice Cavern hop), not a universal constant.
SFX_BANK = 53248          # RunSoundCode3 bank -- every navigable-hop sfx in the census uses it
JUMP_SFX_LEAP = 1324      # the leap whoosh (played right before SetupJump)
JUMP_SFX_LAND = 2342      # the landing thud (played right after Jump)
JUMP_SFX_VOL = 125        # the census-modal volume (a few fields use 99)
JUMP_STEPS_DEFAULT = 11   # jump duration in frames (the census mode; tune per gap like the real game)


def _sfx(sound_id: int, vol: int = JUMP_SFX_VOL) -> bytes:
    """``RunSoundCode3(53248, id, 0, 128, vol)`` (opcode 0xC8, widths [2,2,3,1,1]) -- the arc sfx.
    Ground truth: ``c8 00 00 d0 2c 05 00 00 00 80 7d`` = (53248, 1324, 0, 128, 125), field 301."""
    return opcodes.encode(0xC8, SFX_BANK, int(sound_id), 0, 128, int(vol))


def jump_arc_body(to, *, via=(), steps=JUMP_STEPS_DEFAULT, sfx: bool = True,
                  leap_sfx: int = JUMP_SFX_LEAP, land_sfx: int = JUMP_SFX_LAND,
                  sfx_vol: int = JUMP_SFX_VOL) -> bytes:
    """A FROM-SCRATCH navigable jump arc -- the real Ice Cavern hop template generated from the landing
    point(s), closing FORK_FIDELITY's "jumps are copy-only" gap. Byte-grounded: for a real hop's
    coords/steps this reproduces field 301's arc byte-for-byte (the census-modal template, all 6 IC
    arcs; per hop: ``TurnTowardPosition; WaitTurn; RunJumpAnimation; sfx(leap); SetupJump(x,z,y,steps);
    Jump; StopAnimation; sfx(land); RunLandAnimation; WaitAnimation``, then ``SetPathing(1)``).

    ``to`` = the landing point ``(x, z)`` or ``(x, z, y)`` -- ``y`` is the up-positive world height of
    the landing FLOOR (multi-floor fields: the destination floor's height, read off the paint guide
    like walkmesh placement; the engine floor-snaps after the arc, so ``to`` must land on the
    walkmesh). ``via`` = optional intermediate landing points for a multi-hop crossing (the real
    two-hop Ice Cavern gap: ``via=[mid_ledge]``). ``steps`` = frames per hop (scalar, or a list with
    one entry per hop for per-gap tuning). The engine interpolates each parabola from the actor's
    CURRENT position, so no take-off point is needed -- the arc works from anywhere in the trigger
    zone, exactly like the real ledges. Runs in the player's context (region ``RunScriptSync``)."""
    hops = [tuple(p) for p in via] + [tuple(to)]
    steps_list = list(steps) if isinstance(steps, (list, tuple)) else [steps] * len(hops)
    if len(steps_list) != len(hops):
        raise ValueError(f"jump steps list has {len(steps_list)} entries for {len(hops)} hop(s)")
    body = b""
    for hop, st in zip(hops, steps_list):
        x, z = int(hop[0]), int(hop[1])
        y = int(hop[2]) if len(hop) > 2 else 0
        body += (opcodes.turn_toward_position(x, z) + opcodes.wait_turn()
                 + opcodes.run_jump_animation()
                 + (_sfx(leap_sfx, sfx_vol) if sfx else b"")
                 + opcodes.setup_jump(x, z, y, int(st)) + opcodes.jump()
                 + opcodes.stop_animation()
                 + (_sfx(land_sfx, sfx_vol) if sfx else b"")
                 + opcodes.run_land_animation() + opcodes.wait_animation())
    return body + opcodes.set_pathing(1) + opcodes.RETURN


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


def inject_jump(data, zone, jump_bytes: bytes | None = None, *, to=None, via=(), steps=None,
                jump_tag: int = FIRST_JUMP_TAG, trigger: str = "action", bubble: bool = True,
                player_uid: int = PLAYER_UID, activate: bool = True):
    """Inject one navigable jump: graft a jump arc onto the player entry as func ``jump_tag``, append
    a jump region that fires it, and arm the region. Returns ``(new_bytes, region_slot)``. For
    multiple jumps pass a distinct ``jump_tag`` each.

    The arc is either FAITHFUL or GENERATED (exactly one):
      * ``jump_bytes`` -- a real jump arc extracted verbatim by ``eventscan.scan_jumps`` (exact,
        perspective-correct world coords); grafted as-is. What ``import`` emits for a fork.
      * ``to`` (+ optional ``via``/``steps``) -- :func:`jump_arc_body` generates the census-modal
        Ice Cavern hop template from the landing point(s) -- the from-scratch lane (byte-identical
        to the real template for a real hop's coords).

    Pair with :func:`ensure_jump_animation` once per field so the arc's ``RunJumpAnimation`` has a
    clip."""
    if (jump_bytes is None) == (to is None):
        raise ValueError("inject_jump needs exactly one of jump_bytes (faithful) or to= (generated)")
    if jump_bytes is None:
        jump_bytes = jump_arc_body(to, via=via,
                                   steps=JUMP_STEPS_DEFAULT if steps is None else steps)
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
