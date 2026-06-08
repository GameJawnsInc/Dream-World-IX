"""Ladder primitive -- a region the player climbs, replicating FF9's REAL ladder mechanism.

Decoded byte-for-byte from Treno/Residence (the real game; entry 15 = the ladder region, entry 19 =
the player):

  - tread  (tag 2): ``ifnot(usercontrol) return ; Bubble(1)``            -> the floating "!" prompt
  - action (tag 3): ``ifnot(usercontrol) return ; DisableMove ;
                     RunScriptSync(2, 250, <climb_tag>) ; EnableMove``    -> run the PLAYER's climb
  - the player's climb function (``climb_tag``): runs in the player's OWN context (UID 250), so its
    moves move the PLAYER; ``RunScriptSync`` waits for it.

Why this shape (the hard-won truth): the controlled player's script loop is NOT stepped while
``usercontrol == 1``, so a region -> flag -> player-loop scheme can't drive a climb during free
walking. The region must call the player's climb DIRECTLY via ``RunScriptSync`` (which is exactly what
the real game does). The real climb is bespoke per-ladder jump arcs (hard-coded coords) -- not
generalizable -- so the kit's climb is a simple teleport to the destination (+ an optional climb
gesture). The TRIGGER is faithful; the climb body is simplified.
"""
from __future__ import annotations

import struct

from ..eb import EbScript, edit, opcodes
from ..eb.disasm import iter_code
from . import region as _region

PLAYER_UID = 250          # the controlled player's object UID (standard across FF9 fields)
FIRST_CLIMB_TAG = 17      # the real Treno player ladder funcs start at tag 17; one tag per ladder
RUNSCRIPT_LEVEL = 2       # the script level arg the real ladder uses for RunScriptSync
WAIT = 0x22
STARTSEQ = 0x43           # RunSharedScript -- launches "entry arg0 of this field" as a concurrent Seq
SETUP_JUMP = 0xE2         # SetupJump(x, y, z, arc): the climb's per-rung jump arcs (absolute dest)
LADDER_FLAG = 4           # AddCharacterAttribute(4) = "on a ladder": don't floor-snap during a climb
ZONE_MARGIN = 150         # padding (world units) around the climb's span when auto-sizing a zone


def _s16(v: int) -> int:
    return v - 65536 if v >= 32768 else v


def climb_landings(climb_bytes: bytes) -> list:
    """Every ``SetupJump`` (X, Z) destination in a climb -- the absolute world points the player
    lands on while climbing (top, bottom, and any intermediate rungs)."""
    from ..eb.disasm import read_code
    out, pos = [], 0
    while pos < len(climb_bytes):
        try:
            ins, nxt = read_code(climb_bytes, pos)
        except Exception:
            break
        if ins.op == SETUP_JUMP and len(ins.args) >= 3:
            out.append((_s16(ins.args[0]), _s16(ins.args[2])))   # args = (jumpX, jumpY, jumpZ, steps)
        pos = nxt
    return out


def widen_zone_for_climb(zone, climb_bytes: bytes, margin: int = ZONE_MARGIN) -> list:
    """Return a 4-corner bbox quad covering BOTH the real entry zone AND every climb landing point.

    An imported real ladder's ``SetRegion`` zone only covers the side the player normally approaches
    from, so a FORK (where the player can end up at either end) gets no '!' prompt at the far end and
    can't climb back. Unioning the zone with the climb's ``SetupJump`` destinations (+ margin) makes
    the trigger span the whole ladder, so it's bidirectional. (Proven in-game: CPMP simple ladder.)"""
    pts = [tuple(p) for p in (zone or [])] + climb_landings(climb_bytes)
    if not pts:
        return zone
    xs = [p[0] for p in pts]
    zs = [p[1] for p in pts]
    x0, x1 = min(xs) - margin, max(xs) + margin
    z0, z1 = min(zs) - margin, max(zs) + margin
    return [[x0, z1], [x1, z1], [x1, z0], [x0, z0]]


def find_player_entry(eb: EbScript) -> int:
    """Index of the player entry -- the one running DefinePlayerCharacter (opcode 0x2C)."""
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            for ins in eb.instrs(f):
                if ins.op == 0x2C:
                    return e.index
    raise ValueError("no player entry (DefinePlayerCharacter) found -- can't attach a climb function")


def climb_body(dest, *, animation: int | None = None, anim_hold: int = 40) -> bytes:
    """The player's climb function body: an optional climb gesture, then teleport to ``dest``
    ``(x, z)`` or ``(x, z, y)`` + re-enable walkmesh pathing. Runs in the player's context (via
    RunScriptSync), so ``MoveInstantXZY`` moves the player."""
    x, z = int(dest[0]), int(dest[1])
    y = int(dest[2]) if len(dest) > 2 else 0
    body = b""
    if animation is not None:
        body += opcodes.run_animation(int(animation)) + opcodes.encode(WAIT, int(anim_hold))
    body += opcodes.move_instant_xzy(x, z, y) + opcodes.set_pathing(1) + opcodes.RETURN
    return body


def climb_arc_body(arc_from, arc_to, *, rungs: int = 4, steps: int = 6) -> bytes:
    """DEPRECATED -- superseded by :func:`navigable_climb_body`. This auto-plays a fixed rung-hop
    sequence end-to-end, which is NOT how FF9 ladders work (real ladders are navigable: you hold the
    d-pad to climb up/down rung-by-rung). Kept only for back-compat; use the navigable climb instead.

    An ANIMATED generic climb: interpolated `SetupJump`/`Jump` rung-hops from ``arc_from`` to
    ``arc_to``, each ``(x, z)`` or ``(x, z, height)`` (height defaults 0 = on the floor). Runs in the
    player's context (RunScriptSync), so each rung moves the PLAYER; the engine projects every world
    rung through the camera, so the climb traces the painted/borrowed ladder for free -- the faithful
    jump-arc behavior, auto-generated from two endpoints (no hand-authored coords). Direction-agnostic:
    pass (bottom, top) to ascend or (top, bottom) to descend. `rungs` = hops, `steps` = frames/hop.
    Ends with `SetPathing(1)` to re-enable walkmesh collision at the destination."""
    fx, fz = int(arc_from[0]), int(arc_from[1])
    fy = int(arc_from[2]) if len(arc_from) > 2 else 0
    tx, tz = int(arc_to[0]), int(arc_to[1])
    ty = int(arc_to[2]) if len(arc_to) > 2 else 0
    rungs = max(1, int(rungs))
    body = opcodes.add_character_attribute(LADDER_FLAG)   # ladder flag: don't snap to floor mid-climb
    for i in range(1, rungs + 1):
        f = i / rungs
        x = round(fx + (tx - fx) * f)
        z = round(fz + (tz - fz) * f)
        y = round(fy + (ty - fy) * f)
        body += opcodes.setup_jump(x, z, y, steps) + opcodes.jump()
    if ty != 0:                                           # ending ABOVE the (flat) walkmesh: hold here,
        body += opcodes.set_pathing(0)                    # keep collision off so it isn't snapped down
    else:                                                 # ending ON the floor: dismount to normal walking
        body += opcodes.remove_character_attribute(LADDER_FLAG) + opcodes.set_pathing(1)
    body += opcodes.RETURN
    return body


# ---------------------------------------------------------------------------
# The NAVIGABLE climb -- FF9's real ladder mechanism, recreated from two endpoints.
#
# Decoded byte-for-byte from field 706 (EVT_GIZ_TO_WORLD, the Gizamaluke vine; entry 14 = player,
# func tag 11). The real ladder is a per-frame state machine, NOT an auto-played sequence: mount onto
# the vine, then a loop that reads the HELD d-pad + the player's world-Y each frame, advances a scratch
# target +/-step, and snaps the player onto the 3D line between the two endpoints (MoveInstantXZY with
# X/Z linear in height); leaving the height band ends the loop and a height-keyed selector dismounts at
# whichever end you left from. The per-vine constants (the line equation, the band) are DERIVED here
# from the two world endpoints, so it reproduces 706's loop verbatim for 706's endpoints yet works for
# any new painted vine -- the truthful from-scratch ladder. See project memory + the Session 22 decode.
# ---------------------------------------------------------------------------
SELF = 255
F_Y = 1                  # op78 field 1 = world-Y-up (= -pos.y); the climb tracks this
F_ANIMFRAME = 7
CLIMB_SCRATCH = 2        # MAP.I16[2]: the per-frame climb target (matches 706; transient per-field)
CLIMB_ANIM = 10539       # the per-frame climb-cycle animation (model-specific; Zidane in 706)
MOUNT_ANIM = 10687       # SetJumpAnimation for the mount arc
DISMOUNT_ANIM = 11453    # SetJumpAnimation for the dismount arc


def _const(v: int) -> bytes:
    return bytes([_region.T_CONST]) + struct.pack("<h", int(v))


def _selfv(field: int) -> bytes:
    return _region.obj_var(SELF, field)


def _scratch() -> bytes:
    return _region._push_var(_region.MAP_INT16, CLIMB_SCRATCH)


def _stmt(*toks: bytes) -> bytes:
    """A complete expression statement: ``05 <tokens> 7F``."""
    return bytes([_region.EXPR_OP]) + b"".join(toks) + bytes([_region.T_END])


def _arg(*toks: bytes) -> bytes:
    """A bare expression operand (for an opcode arg with its arg_flags bit set): ``<tokens> 7F``."""
    return b"".join(toks) + bytes([_region.T_END])


class _Asm:
    """A tiny label assembler for the climb's mixed forward+backward jumps. Every jump's operand is
    ``target_off - (jmp_off + 3)`` as a signed i16 (verified: the engine does ``ip = A + 3 + offset``),
    so one rule covers the forward if-skips AND the loop back-edge -- computed after layout."""

    def __init__(self):
        self._items = []     # ('raw', bytes) | ('lbl', name) | ('jmp', op, target)

    def raw(self, b: bytes):
        if b:
            self._items.append(("raw", bytes(b)))
        return self

    def label(self, name: str):
        self._items.append(("lbl", name))
        return self

    def jmp(self, op: int, target: str):
        self._items.append(("jmp", op, target))
        return self

    def assemble(self) -> bytes:
        labels, off = {}, 0
        for it in self._items:
            if it[0] == "lbl":
                labels[it[1]] = off
            elif it[0] == "raw":
                off += len(it[1])
            else:
                off += 3
        out, off = bytearray(), 0
        for it in self._items:
            if it[0] == "raw":
                out += it[1]
                off += len(it[1])
            elif it[0] == "jmp":
                _, op, tgt = it
                out += bytes([op]) + struct.pack("<h", labels[tgt] - (off + 3))
                off += 3
        return bytes(out)


def _dismount(anim: int, x: int, z: int, y: int = 0, steps: int = 6, frames=(2, 8)) -> bytes:
    """Jump off the vine onto the floor at height ``y``, re-enable walkmesh collision + clear the
    ladder flag + restore the animation flags -- the clean dismount (706's floor walk-off, leaned out).
    Real floors are often elevated (non-zero ``y``); ``frames`` = the jump anim's in/out window."""
    return (opcodes.set_jump_animation(anim, frames[0], frames[1]) + opcodes.run_jump_animation()
            + opcodes.wait_animation() + opcodes.setup_jump(x, z, y, steps) + opcodes.jump()
            + opcodes.run_land_animation() + opcodes.wait_animation()
            + opcodes.set_pathing(1) + opcodes.remove_character_attribute(LADDER_FLAG)
            + opcodes.set_animation_flags(0, 0))


def navigable_climb_body(bottom, top, *, floor_landing=None, top_landing=None, step: int = 20,
                         up_mask: int = 0x10, down_mask: int = 0x40, right_alias: bool = False,
                         climb_anim: int = CLIMB_ANIM, climb_frames: int = 12,
                         mount_anim: int = MOUNT_ANIM, dismount_anim: int = DISMOUNT_ANIM,
                         mount_steps: int = 4, dismount_steps: int = 6,
                         face_angle: int | None = None, top_action: str = "floor",
                         top_field: int | None = None, top_entrance: int = 0,
                         top_worldmap: int | None = None) -> bytes:
    """Recreate FF9's NAVIGABLE ladder climb for a vine between two world endpoints.

    ``bottom`` / ``top`` = ``(x, z, y)`` world points (``y`` = up-positive height; they MUST differ in
    ``y``). The player mounts at ``bottom`` and climbs by holding the d-pad: each frame the loop reads
    the held direction (``B_KEY``) + the player's world-Y, advances the scratch target +/- ``step``,
    and snaps the player onto the 3D line between the endpoints (``MoveInstantXZY``, X/Z linear in
    height). Leaving the band ends the loop; a height-keyed selector dismounts to the floor at the end
    you left from (``floor_landing`` for the bottom end, ``top_landing`` for the top -- both default to
    the vine's own x/z at floor level). Runs in the player's own context (the region RunScriptSync's
    it), so its moves move the PLAYER.

    The line equation + height band are DERIVED from the two endpoints, so passing 706's endpoints
    reproduces 706's loop byte-for-byte, while any new painted vine just supplies its own two points
    (read off the paint guide, same as walkmesh placement). ``up_mask`` / ``down_mask`` are the
    ``B_KEY`` button bits (vertical ladder default Up=0x10 / Down=0x40; pass ``right_alias`` for a
    diagonal screen vine that also climbs on Right). Returns the climb function body."""
    bx, bz = int(bottom[0]), int(bottom[1])
    by = int(bottom[2]) if len(bottom) > 2 else 0
    tx, tz = int(top[0]), int(top[1])
    ty = int(top[2]) if len(top) > 2 else 0
    if ty == by:
        raise ValueError("navigable ladder: top and bottom must differ in height (y)")
    # selfY = -worldY (op78 field 1). Band = [lo, hi] in selfY space; the line is anchored at bottom.
    sy_bottom, sy_top = -by, -ty
    lo, hi = min(sy_bottom, sy_top), max(sy_bottom, sy_top)
    exit_threshold = (lo + hi) // 2
    anchor, slope_den = sy_bottom, sy_top - sy_bottom
    x_slope, z_slope = tx - bx, tz - bz
    fl = floor_landing if floor_landing else (bx, bz)
    flx, flz = int(fl[0]), int(fl[1]); fly = int(fl[2]) if len(fl) > 2 else 0
    tl = top_landing if top_landing else (tx, tz)
    tlx, tlz = int(tl[0]), int(tl[1]); tly = int(tl[2]) if len(tl) > 2 else 0
    if top_action == "field" and top_field is None:
        raise ValueError('navigable ladder top_action="field" needs top_field')
    if top_action == "worldmap" and top_worldmap is None:
        raise ValueError('navigable ladder top_action="worldmap" needs top_worldmap')

    def line(base, slope):   # base + (target - anchor) * slope / slope_den (reproduces 706 verbatim)
        return _arg(_const(base), _const(slope), _scratch(), _const(anchor),
                    bytes([_region.T_MINUS]), bytes([_region.T_MULT]),
                    _const(slope_den), bytes([_region.T_DIV]), bytes([_region.T_PLUS]))

    def band():   # (selfY <= hi) && (selfY >= lo) -- still on the vine
        return _stmt(_selfv(F_Y), _const(hi), bytes([_region.T_LE]),
                     _selfv(F_Y), _const(lo), bytes([_region.T_GE]), bytes([_region.T_ANDAND]))

    def anim_window(advance):   # SetAnimationInOut((animFrame+advance)%N, ...): step the climb anim
        # a ONE-frame window = the climb's clock. advance=1 plays it FORWARD (ascending), advance=N-1
        # (= -1 mod N) plays it BACKWARD (descending) so the hands match the down motion (real GZML).
        w = _arg(_selfv(F_ANIMFRAME), _const(advance), bytes([_region.T_PLUS]),
                 _const(climb_frames), bytes([_region.T_MOD]))
        return opcodes.encode(0x3D, w, w, arg_flags=0b11)

    def set_target(sign):   # MAP.I16[2] = selfY (+/- step); sign=None just holds (= selfY, no move)
        if sign is None:
            return _stmt(_scratch(), _selfv(F_Y), bytes([_region.T_ASSIGN]))
        return _stmt(_scratch(), _selfv(F_Y), _const(step), bytes([sign]), bytes([_region.T_ASSIGN]))

    a = _Asm()
    # MOUNT (gated like 706): only jump onto the vine when arriving near the BASE (selfY past the
    # mid-band threshold). On RE-ENTRY the player-init spawns you already high on the vine (with the
    # ladder flag + SetPathing(0) set), so selfY is below the threshold -> skip the mount -> drop
    # straight into the loop and climb DOWN. Faithful to 706's `if (selfY > -500) { mount }` gate.
    a.raw(_stmt(_selfv(F_Y), _const(exit_threshold), bytes([_region.T_GT])))
    a.jmp(_region.JMP_FALSE, "LOOP")           # high on the vine (re-entry) -> skip the mount
    if face_angle is not None:
        a.raw(opcodes.turn_instant(int(face_angle)))
    a.raw(opcodes.set_jump_animation(mount_anim, 2, 6) + opcodes.run_jump_animation()
          + opcodes.wait_animation())
    a.raw(opcodes.add_character_attribute(LADDER_FLAG))
    a.raw(opcodes.setup_jump(bx, bz, by, mount_steps) + opcodes.jump())
    a.raw(opcodes.run_land_animation() + opcodes.wait_animation()
          + opcodes.set_pathing(0) + opcodes.set_animation_flags(1, 0)
          + opcodes.set_animation_in_out(0, 0))
    # NAVIGATE LOOP
    a.label("LOOP")
    # input: a FIRST-MATCH-WINS else-if chain (like the real GZML loop). Each held direction advances
    # the climb anim one frame, sets the target +/- step, and JUMPS to the snap (skipping the rest) --
    # so an up-diagonal climbs UP even though the down mask (Down|Left) can overlap it. No input -> HOLD
    # (target = selfY; the anim window is NOT advanced, so it freezes on a grip pose rather than looping).
    dirs = [(up_mask, _region.T_MINUS), (down_mask, _region.T_PLUS)]
    if right_alias:
        dirs.append((0x20, _region.T_MINUS))                            # Right = a second 'up' binding
    for i, (mask, sign) in enumerate(dirs):
        adv = 1 if sign == _region.T_MINUS else climb_frames - 1       # up = forward, down = backward
        a.raw(_stmt(_const(mask), bytes([_region.T_KEY])))             # if (mask held)
        a.jmp(_region.JMP_FALSE, f"DIR{i}")
        a.raw(anim_window(adv) + set_target(sign))
        a.jmp(0x01, "SNAP")
        a.label(f"DIR{i}")
    a.raw(set_target(None))                                            # HOLD: no direction held
    a.label("SNAP")
    # snap the player onto the vine line for the new height (X/Z exprs; middle arg = bare target)
    a.raw(opcodes.encode(0xA1, line(bx, x_slope), _arg(_scratch()), line(bz, z_slope),
                         arg_flags=0b111))
    # climb-cycle anim while on the vine, else a 1-frame wait
    a.raw(band())
    a.jmp(_region.JMP_FALSE, "OFFVINE")
    a.raw(opcodes.run_animation(climb_anim) + opcodes.wait_animation())
    a.jmp(0x01, "ANIMDONE")
    a.label("OFFVINE")
    a.raw(opcodes.wait(1))
    a.label("ANIMDONE")
    # loop while still on the vine
    a.raw(band())
    a.jmp(_region.JMP_TRUE, "LOOP")
    # EXIT: selfY > midpoint -> BOTTOM (floor) dismount; else -> the TOP end (per top_action)
    a.raw(_stmt(_selfv(F_Y), _const(exit_threshold), bytes([_region.T_GT])))
    a.jmp(_region.JMP_FALSE, "TOP_END")
    a.raw(_dismount(dismount_anim, flx, flz, fly, dismount_steps))      # bottom -> floor dismount
    a.jmp(0x01, "END")
    a.label("TOP_END")
    if top_action == "field":                                          # top -> a Field() gateway
        # The engine's field transition: fade out, WAIT for the fade to finish, set the arrival
        # entrance, then Field(). We do NOT emit PreloadField -- it is opcode 0xFD (HINT), "ignored in
        # the non-PSX versions" (a no-op on Steam); and crucially it must NOT be confused with 0x2A =
        # Battle (emitting 0x2A here literally fired a battle using the field id as the scene). Move/menu
        # are already disabled by the region that RunScriptSync'd this climb.
        a.raw(opcodes.fade_filter(6, 24, 0, 255, 255, 255) + opcodes.wait(25)
              + _region.set_field_entrance(int(top_entrance))
              + opcodes.field(int(top_field)) + opcodes.terminate_entry(255))
    elif top_action == "worldmap":                                     # top -> the world map
        a.raw(opcodes.fade_filter(6, 24, 0, 255, 255, 255) + opcodes.wait(25)
              + _region.set_field_entrance(int(top_entrance))
              + opcodes.world_map(int(top_worldmap)) + opcodes.terminate_entry(255))
    else:                                                              # "floor": dismount onto a top floor
        a.raw(_dismount(dismount_anim, tlx, tlz, tly, dismount_steps))
    a.label("END")
    a.raw(opcodes.RETURN)
    return a.assemble()


def ladder_region(zone, climb_tag: int, *, player_uid: int = PLAYER_UID) -> bytes:
    """A type-1 region entry: Init ``SetRegion(zone)`` / tread ``Bubble(1)`` / action ``DisableMove;
    RunScriptSync(player climb); EnableMove`` -- the real FF9 ladder trigger."""
    init = _region.set_region(zone) + opcodes.RETURN
    tread = _region.MOVEMENT_GATE + opcodes.bubble(1) + opcodes.RETURN
    action = (_region.MOVEMENT_GATE + opcodes.DISABLE_MOVE
              + opcodes.run_script_sync(RUNSCRIPT_LEVEL, player_uid, climb_tag)
              + opcodes.ENABLE_MOVE + opcodes.RETURN)
    funcs = [(0, init), (_region.RANGE_TAG, tread), (_region.INTERACT_TAG, action)]
    table = b""
    pos = len(funcs) * 4
    for tag, body in funcs:
        table += struct.pack("<HH", tag, pos)
        pos += len(body)
    return bytes([_region.REGION_ENTRY_TYPE, len(funcs)]) + table + b"".join(b for _, b in funcs)


def inject_ladder(data, zone, dest=None, *, climb_bytes: bytes | None = None,
                  arc_from=None, arc_to=None, rungs: int = 4, steps: int = 6,
                  sequences: dict | None = None, climb_tag: int = FIRST_CLIMB_TAG,
                  player_uid: int = PLAYER_UID, animation: int | None = None, activate: bool = True):
    """Inject a ladder: add a climb function (``climb_tag``) to the player entry + a ladder region
    (tread "!" prompt + action -> RunScriptSync the climb), and arm the region. Returns
    ``(new_bytes, region_slot)``. For multiple ladders pass a distinct ``climb_tag`` each.

    The climb is either FAITHFUL or EMULATED:
      * ``climb_bytes`` -- a real ladder's climb function extracted verbatim by
        ``eventscan.scan_ladders`` (exact jump arcs, perspective-correct). Grafted as-is; its internal
        jumps are function-relative so they survive the move. This is what ``import`` emits for a fork.
      * ``dest`` -- ``(x, z[, y])``; ``climb_body`` builds a teleport (+ optional gesture). The simple
        generic climb when you have no real ladder to copy.

    ``sequences`` (``{original_entry_index: entry_bytes}``, from ``scan_ladders``) are the concurrent
    helper entries the climb launches via STARTSEQ (e.g. the SetPitchAngle forward-lean). Each is
    appended at a free slot and the climb's STARTSEQ entry-args are remapped to those slots (a
    same-length 1-byte patch -- the climb stays byte-for-byte otherwise). Empty for simple ladders."""
    animated = arc_from is not None and arc_to is not None
    if climb_bytes is None and dest is None and not animated:
        raise ValueError("inject_ladder needs climb_bytes (faithful), arc_from+arc_to (animated arc), or dest (teleport)")
    if animated:
        body = bytearray(climb_arc_body(arc_from, arc_to, rungs=rungs, steps=steps))
    elif climb_bytes is not None:
        body = bytearray(climb_bytes)
    else:
        body = bytearray(climb_body(dest, animation=animation))
    if sequences:                                            # graft the STARTSEQ helper entries + remap
        ei2slot = {}
        for ei in sorted(sequences):
            slot = EbScript.from_bytes(data).first_free_slot()
            data = edit.append_entry(data, slot, sequences[ei])
            ei2slot[ei] = slot
        for ins in iter_code(bytes(body), 0, len(body)):
            if ins.op == STARTSEQ and ins.args and ins.args[0] in ei2slot:
                body[ins.off + 2] = ei2slot[ins.args[0]]     # STARTSEQ = 0x43, argflag, entry-arg
    body = bytes(body)
    eb = EbScript.from_bytes(data)
    pe = find_player_entry(eb)
    data = edit.add_function(data, pe, climb_tag, body)
    eb = EbScript.from_bytes(data)
    slot = eb.first_free_slot()
    data = edit.append_entry(data, slot, ladder_region([tuple(p) for p in zone], climb_tag,
                                                       player_uid=player_uid))
    if activate:
        data = edit.activate(data, opcodes.init_region(slot, 0))
    return data, slot


def square_zone(center, radius: int = 150) -> list:
    """A 5-point IsInQuad-safe square trigger zone (side 2*radius) centred on ``(x, z)``."""
    cx, cz = int(center[0]), int(center[1])
    r = int(radius)
    c = [[cx - r, cz + r], [cx + r, cz + r], [cx + r, cz - r], [cx - r, cz - r]]
    return c + [c[-1]]                                    # double last vertex (IsInQuad fan safety)


def inject_bidirectional_ladder(data, top, bottom, *, radius: int = 150, rungs: int = 4,
                                steps: int = 6, animation: int | None = None,
                                first_tag: int = FIRST_CLIMB_TAG):
    """A from-scratch BIDIRECTIONAL ladder with no real climb to copy: a trigger zone at EACH end, the
    player's location picks the direction (top zone -> down to ``bottom``, bottom zone -> up to
    ``top``), so it climbs both ways WITHOUT reading runtime position. ``top``/``bottom`` are the
    trigger-zone centre + landing point for each end.

    If EITHER endpoint carries a height (``(x, z, y)``, y>0) the climb is ANIMATED -- interpolated
    `SetupJump`/`Jump` rung-hops that the engine projects so they trace the painted/borrowed ladder
    (the faithful behavior, auto-generated). If both are flat ``(x, z)`` it falls back to an instant
    teleport (the zero-info generic). Returns ``(new_bytes, next_tag)`` (consumes two climb tags)."""
    animated = len(top) > 2 or len(bottom) > 2
    if animated:                                        # arc DOWN from the top zone, arc UP from the bottom
        data, _ = inject_ladder(data, square_zone(top, radius), arc_from=top, arc_to=bottom,
                                rungs=rungs, steps=steps, climb_tag=first_tag)
        data, _ = inject_ladder(data, square_zone(bottom, radius), arc_from=bottom, arc_to=top,
                                rungs=rungs, steps=steps, climb_tag=first_tag + 1)
    else:                                               # flat endpoints -> instant teleport fallback
        data, _ = inject_ladder(data, square_zone(top, radius), dest=bottom,
                                climb_tag=first_tag, animation=animation)
        data, _ = inject_ladder(data, square_zone(bottom, radius), dest=top,
                                climb_tag=first_tag + 1, animation=animation)
    return data, first_tag + 2


def inject_navigable_ladder(data, bottom, top, *, floor_landing=None, top_landing=None, zone=None,
                            radius: int = 200, climb_tag: int = FIRST_CLIMB_TAG,
                            player_uid: int = PLAYER_UID, activate: bool = True, **climb_kw):
    """A from-scratch NAVIGABLE ladder between two world endpoints -- FF9's REAL ladder mechanism,
    recreated (NOT the deprecated auto-hop): ONE trigger zone at the vine base -> press action -> hold
    the d-pad to climb up/down, snapped onto the painted vine, dismount at either end.

    ``bottom`` / ``top`` = ``(x, z, y)`` world points (``y`` = up-positive height). The trigger ``zone``
    defaults to a square at the floor step-off point (``floor_landing`` or the bottom's x/z) -- where
    the player stands to mount. Extra climb params (``step``, ``up_mask`` / ``down_mask``,
    ``right_alias``, ``climb_anim`` / ``mount_anim`` / ``dismount_anim``, ``face_angle`` ...) pass
    through to :func:`navigable_climb_body`. The generated body is grafted exactly like a faithful
    climb (it IS a climb body), so it reuses the proven trigger/region machinery. Returns
    ``(new_bytes, region_slot)``. One climb function => one ladder; pass a distinct ``climb_tag`` each."""
    body = navigable_climb_body(bottom, top, floor_landing=floor_landing, top_landing=top_landing,
                                **climb_kw)
    if zone is None:
        base = floor_landing if floor_landing is not None else (int(bottom[0]), int(bottom[1]))
        zone = square_zone(base, radius)
    return inject_ladder(data, zone, climb_bytes=body, climb_tag=climb_tag,
                         player_uid=player_uid, activate=activate)


def reentry_spawn_block(x: int, z: int, y: int, *, face: int = 0,
                        climb_anim: int = CLIMB_ANIM) -> bytes:
    """The on-vine RE-ENTRY placement (no RETURN -- meant to be inlined as an ``if`` body in the
    player-init): place the player ON THE VINE at world ``(x, z)`` height ``y``, gripping (ladder flag
    + detached from the walkmesh + the climb idle pose) and facing ``face``. So when you return to the
    field from the ladder's top gateway you appear high on the vine and climb DOWN to get off (706's
    re-entry pattern). ``y`` is the up-positive height; the encoder negates it like the climb does."""
    return (opcodes.add_character_attribute(LADDER_FLAG)
            + opcodes.move_instant_xzy(int(x), int(z), int(y))
            + opcodes.turn_instant(int(face) & 0xFF)
            + opcodes.set_pathing(0)
            + opcodes.set_animation_flags(1, 0) + opcodes.set_animation_in_out(0, 0)
            + opcodes.run_animation(int(climb_anim)))


REENTRY_TAG = 90    # the player's re-entry placement function tag (distinct from climb tags 17+)


def inject_reentry_spawn(data, entrance: int, x: int, z: int, y: int, *, face: int = 0,
                         climb_anim: int = CLIMB_ANIM, reentry_tag: int = REENTRY_TAG,
                         player_uid: int = PLAYER_UID, activate: bool = True):
    """Make the field spawn the player ON THE VINE (high, gripping) when entered via ``entrance`` -- the
    return from a ladder-top ``Field()`` gateway, so you climb DOWN to get off (706's re-entry).

    Adds a player function (``reentry_tag``) that does the on-vine placement (runs in the player's
    context), + a code entry ``if (D8:2 == entrance) { RunScriptSync(player, reentry_tag) }`` armed at
    field load. This runs AFTER the player-init's normal spawn (so it overrides the position) and uses
    only the proven add_function/append_entry/RunScriptSync mechanisms (no fragile mid-func insert).
    A one-shot field-load check, so it can't re-fire mid-visit. Returns ``(new_bytes, code_slot)``.
    ``entrance`` must match what the destination field's return gateway sets (D8:2)."""
    eb = EbScript.from_bytes(data)
    pe = find_player_entry(eb)
    data = edit.add_function(data, pe, reentry_tag,
                             reentry_spawn_block(x, z, y, face=face, climb_anim=climb_anim) + opcodes.RETURN)
    body = (_region.if_block(
                _region.cond_eq(_region.GLOB_INT16, _region.FIELD_ENTRANCE_IDX, int(entrance)),
                opcodes.run_script_sync(RUNSCRIPT_LEVEL, player_uid, reentry_tag))
            + opcodes.RETURN)
    code_entry = bytes([0, 1]) + struct.pack("<HH", 0, 4) + body     # type-0 entry, 1 func (tag 0)
    eb = EbScript.from_bytes(data)
    slot = eb.first_free_slot()
    data = edit.append_entry(data, slot, code_entry)
    if activate:
        data = edit.activate(data, opcodes.init_code(slot, 0))
    return data, slot
