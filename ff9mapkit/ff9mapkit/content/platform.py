"""Carry-platform primitive -- a rideable lift/elevator that physically CARRIES the player within one
field (no Field() re-entry warp), recreating FF9's Pandemonium-elevator mechanism.

Decoded from Pandemonium/Elevator (fields 2712 `pd_elv` / 2713 `pd_evd`). The real ride is a fully
SCRIPTED, control-locked carry -- NOT an engine attach (there is ZERO MoveTileLoop/AttachTile/SIM in
either field). The boarding region disables control and `RunScriptSync`s a function grafted onto the
PLAYER object (UID 250); that function moves the player frame-by-frame with `MoveInstantXZY` until he
reaches the destination height, then control returns:

  - region (tag 2 tread "!" / tag 3 action): ``DisableMove ; RunScriptSync(2, 250, ride_tag) ; EnableMove``
  - the ride func (``ride_tag``, on the PLAYER): a per-frame loop
      ``{ scratch = selfY +/- step ; MoveInstantXZY(line_x, scratch, line_z) ; Wait(1) ;
         while (selfY hasn't reached arrive) }`` then SetPathing(1) (or the optional fade+Field tail).

This is the kit's navigable ladder climb (:func:`ladder.navigable_climb_body`) MINUS the d-pad input
and the mount/dismount arcs: instead of reading the held direction each frame, the carry advances a
FIXED step toward the destination, so it is auto-driven and always terminates (a linear ride of
~``duration`` frames). Every byte is emitted by the same proven primitives the climb uses (the ``_Asm``
label assembler, the ``0xA1`` expression-arg snap, the ``line()`` interpolation, the ladder flag).

selfY = -worldY (op78 field 1): a HIGHER physical position is a MORE-NEGATIVE selfY, so a lift going UP
(arrive above board) advances selfY in the NEGATIVE direction. The carry derives the step sign + the
arrival test from ``arrive.y`` vs ``board.y`` (they MUST differ -- a zero-height carry never moves).

v1 emits the CARRY only; the visible platform is the human's (paint a ride surface, or drive a placed
GEO model in lockstep -- a follow-up). docs: project memory `project-ff9-moving-platforms-elevators`.
"""
from __future__ import annotations

import math
import struct

from ..eb import EbScript, edit, opcodes
from . import region as _region
from .ladder import (_Asm, _arg, _const, _selfv, _stmt, CLIMB_ANIM, F_Y, LADDER_FLAG,
                     find_player_entry, square_zone)

PLAYER_UID = 250          # the controlled player's runtime UID (standard across FF9 fields)
FIRST_PLATFORM_TAG = 56   # player ride funcs start here -- clear of ladder (17+) / jump (40+) climb tags,
                          #   below the object-carry player band (64+); one tag per platform
RUNSCRIPT_LEVEL = 2       # the script level RunScriptSync uses (matches the real ladder/jump triggers)
PLATFORM_SCRATCH = 3      # MAP.I16[3]: the per-frame ride target (transient per-field; the ladder uses [2])
DEFAULT_DURATION = 32     # ride frames -- the ride eases over ~this many frames (linear, always terminates)


def _scratch() -> bytes:
    """The ride's per-frame target var (MAP.I16[PLATFORM_SCRATCH]); re-derived from selfY each frame, so
    its transient value never matters across rides."""
    return _region._push_var(_region.MAP_INT16, PLATFORM_SCRATCH)


def _assemble_entry(funcs) -> bytes:
    """Assemble a type-1 (region) entry from ``[(tag, body), ...]`` (the ladder/jump region layout):
    the func table (``<tag:u16><fpos:u16>`` x N) then the concatenated bodies."""
    table = b""
    pos = len(funcs) * 4
    for tag, body in funcs:
        table += struct.pack("<HH", tag, pos)
        pos += len(body)
    return bytes([_region.REGION_ENTRY_TYPE, len(funcs)]) + table + b"".join(b for _, b in funcs)


def carry_body(board, arrive, *, duration: int = DEFAULT_DURATION, animation: int | None = None,
               warp_to: int | None = None, warp_entrance: int = 0) -> bytes:
    """The player's ride function: snap onto ``board`` ``(x, z, y)``, carry to ``arrive`` ``(x, z, y)``
    over ~``duration`` frames (linear), then land. Runs in the player's context (the region
    RunScriptSync's it), so ``MoveInstantXZY`` moves the PLAYER. ``board`` and ``arrive`` MUST differ in
    height (``y``). For a pure vertical lift use the same ``x``/``z``; a non-vertical ``arrive`` rides a
    straight 3D line (the X/Z interpolate with height, like the navigable ladder snap).

    If ``warp_to`` is given, the ride ENDS with the proven gateway transition (fade to black + ``Field()``
    re-entry at ``warp_entrance``) -- an inter-floor ELEVATOR (the real 2713 tail). Omit it for a pure
    in-screen ride (control simply returns at the top)."""
    bx, bz = int(board[0]), int(board[1])
    by = int(board[2]) if len(board) > 2 else 0
    ax, az = int(arrive[0]), int(arrive[1])
    ay = int(arrive[2]) if len(arrive) > 2 else 0
    duration = max(1, int(duration))
    sy_board, sy_arrive = -by, -ay                    # selfY space (op78 field 1 = -worldY)
    span = sy_arrive - sy_board
    if span == 0:
        raise ValueError("carry_body: board and arrive must differ in height (y) -- a zero-height ride never moves")
    stepmag = max(1, math.ceil(abs(span) / duration))
    sign_tok = _region.T_MINUS if span < 0 else _region.T_PLUS    # UP => selfY decreases
    test_tok = _region.T_GT if span < 0 else _region.T_LT         # loop while selfY hasn't reached arrive

    def line(base: int, slope: int) -> bytes:         # base + (scratch - sy_board) * slope / span (706 verbatim)
        return _arg(_const(base), _const(slope), _scratch(), _const(sy_board),
                    bytes([_region.T_MINUS]), bytes([_region.T_MULT]),
                    _const(span), bytes([_region.T_DIV]), bytes([_region.T_PLUS]))

    ride_anim = CLIMB_ANIM if animation is None else int(animation)   # the per-frame ride clip
    a = _Asm()
    # board: grip (ladder flag so the height isn't floor-snapped away) + detach + snap to the start point,
    # then establish the on-ride ANIMATION STATE (mirrors the climb's mount). Without an active animation the
    # engine drops the player from the character-over-overlay composite -> an INVISIBLE ride (in-game proven
    # failure); SetAnimationFlags/SetAnimationInOut + the per-frame tick below are exactly what the proven
    # navigable climb does to stay visible.
    a.raw(opcodes.add_character_attribute(LADDER_FLAG) + opcodes.set_pathing(0)
          + opcodes.move_instant_xzy(bx, bz, by)
          + opcodes.set_animation_flags(1, 0) + opcodes.set_animation_in_out(0, 0)
          + opcodes.run_animation(ride_anim))                          # start the LOOPING ride clip once
    a.label("LOOP")
    # advance the target a fixed step toward arrive, then snap the player onto the ride line for it
    a.raw(_stmt(_scratch(), _selfv(F_Y), _const(stepmag), bytes([sign_tok]), bytes([_region.T_ASSIGN])))
    a.raw(opcodes.encode(0xA1, line(bx, ax - bx), _arg(_scratch()), line(bz, az - bz), arg_flags=0b111))
    a.raw(opcodes.wait(1))                                             # one ride frame (deterministic timing)
    a.raw(_stmt(_selfv(F_Y), _const(sy_arrive), bytes([test_tok])))    # selfY still short of arrive?
    a.jmp(_region.JMP_TRUE, "LOOP")
    a.raw(opcodes.move_instant_xzy(ax, az, ay))       # exact final snap (corrects any step overshoot)
    if warp_to is not None:                           # ELEVATOR: ride then re-enter the destination floor
        a.raw(opcodes.fade_filter(6, 24, 0, 255, 255, 255) + opcodes.wait(25)
              + _region.set_field_entrance(int(warp_entrance))
              + opcodes.field(int(warp_to)) + opcodes.terminate_entry(255))
    else:                                             # in-screen ride: land + hand control back
        a.raw(opcodes.remove_character_attribute(LADDER_FLAG) + opcodes.set_pathing(1))
    a.raw(opcodes.RETURN)
    return a.assemble()


def platform_region(zone, ride_tag: int, *, trigger: str = "action", bubble: bool = True,
                    player_uid: int = PLAYER_UID) -> bytes:
    """A type-1 region entry that boards the player onto the ride (func ``ride_tag`` on the player).

    ``trigger="action"`` (default): Init ``SetRegion`` / tread ``Bubble(1)`` (if ``bubble``) / action
    ``DisableMove; RunScriptSync(player, ride_tag); EnableMove`` -- press to board. ``trigger="tread"``:
    the dispatch is on the tread func (auto-board on walk-in). Control is held for the whole ride
    (synchronous ``RunScriptSync``) -- the same proven shape as the ladder/jump trigger."""
    init = _region.set_region(zone) + opcodes.RETURN
    dispatch = (opcodes.DISABLE_MOVE
                + opcodes.run_script_sync(RUNSCRIPT_LEVEL, player_uid, ride_tag)
                + opcodes.ENABLE_MOVE + opcodes.RETURN)
    if trigger == "tread":
        body = _region.MOVEMENT_GATE + (opcodes.bubble(1) if bubble else b"") + dispatch
        funcs = [(0, init), (_region.RANGE_TAG, body)]
    else:                                             # "action" -- press-to-board (+ "!" prompt)
        tread = _region.MOVEMENT_GATE + (opcodes.bubble(1) if bubble else b"") + opcodes.RETURN
        action = _region.MOVEMENT_GATE + dispatch
        funcs = [(0, init), (_region.RANGE_TAG, tread), (_region.INTERACT_TAG, action)]
    return _assemble_entry(funcs)


def inject_platform(data, zone, board, arrive, *, ride_tag: int = FIRST_PLATFORM_TAG,
                    duration: int = DEFAULT_DURATION, animation: int | None = None,
                    trigger: str = "action", bubble: bool = True, warp_to: int | None = None,
                    warp_entrance: int = 0, player_uid: int = PLAYER_UID, activate: bool = True):
    """Inject one carry platform: graft the ride function (``ride_tag``) onto the player entry, append a
    boarding region that fires it, and arm the region. Returns ``(new_bytes, region_slot)``. For multiple
    platforms pass a distinct ``ride_tag`` each (start at :data:`FIRST_PLATFORM_TAG`)."""
    body = carry_body(board, arrive, duration=duration, animation=animation,
                      warp_to=warp_to, warp_entrance=warp_entrance)
    eb = EbScript.from_bytes(data)
    pe = find_player_entry(eb)
    data = edit.add_function(data, pe, ride_tag, body)
    eb = EbScript.from_bytes(data)
    slot = eb.first_free_slot()
    data = edit.append_entry(data, slot, platform_region([tuple(p) for p in zone], ride_tag,
                                                         trigger=trigger, bubble=bubble, player_uid=player_uid))
    if activate:
        data = edit.activate(data, opcodes.init_region(slot, 0))
    return data, slot
