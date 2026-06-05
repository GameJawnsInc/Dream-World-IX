"""Camera-services / scrolling control (the ``BGCACTIVE`` opcode).

Larger-than-screen fields scroll the view to follow the player. Memoria's 3D scroll
(``FieldMap.SceneService3DScroll``) runs automatically for a walkable field, but only when the
field's ``Active`` flag is set — and that flag is set by the field-script opcode
``EnableCameraServices`` (``BGCACTIVE`` = 0x71, args ``isActive, frameCount, sinusOrLinear``).

A field cloned from a static (non-scrolling) base never calls it, so :func:`enable_camera_services`
injects ``EnableCameraServices(1, 0, 0)`` at the start of Main_Init. Proven in-game on the 768x448
scroll spike (field 4003): with the wide ``Range`` + scroll ``Viewport`` (see
:func:`ff9mapkit.scene.cam.scroll_bounds`) the view then pans + clamps cleanly.
"""

from __future__ import annotations

import struct

from ..eb import EbScript, edit, opcodes
from . import region as _region

BGCACTIVE_OP = 0x71      # EnableCameraServices

# The camera-state flag. VAR_GlobUInt8_24 is exactly what the real field (Gargan Roo/Passage) uses;
# our init entry resets it to 0 on every field load, so it never collides across loads.
DEFAULT_FLAG = (_region.GLOB_UINT8, 24)


def enable_camera_services(eb_bytes, *, frame_count: int = 0, scroll_type: int = 0) -> bytes:
    """Insert ``EnableCameraServices(1, frame_count, scroll_type)`` at the start of Main_Init.

    ``frame_count`` = duration (frames) of the camera's reposition-to-player when it activates
    (0 = instant; -1 defaults to 30 in the engine). ``scroll_type`` = 8 for sinusoidal, else linear.
    Uses :func:`edit.insert_bytes` (relocates jumps/fpos), so it is safe alongside other injectors.
    """
    eb = EbScript.from_bytes(eb_bytes)
    f = eb.entry(0).func_by_tag(0)
    if f is None:
        raise ValueError("entry 0 has no Main_Init (tag 0) to enable camera services in")
    code = opcodes.encode(BGCACTIVE_OP, 1, int(frame_count), int(scroll_type))
    return edit.insert_bytes(eb_bytes, f.abs_start, code)


# --------------------------------------------------------------------------- multi-camera switch
# The real-field convention (decoded byte-for-byte from Gargan Roo/Passage, evt_gargan_gr_lef_0):
# a PAIR of region zones at the boundary between two background cameras, gated by a state flag so
# each fires only on the crossing (the anti-flap discipline the engine itself had to hot-fix for
# fields that lacked it). Crossing the forward zone switches camera 0 -> target, sets the flag,
# re-tunes movement (SetControlDirection for the target camera), turns the reverse zone ON, and
# terminates itself; the reverse zone mirrors it back. An init code-entry resets the flag to 0 and
# arms the forward zone on every field load, so state is always consistent on (re)entry.

def _switch_body(cond: bytes, to_camera: int, control_value: int, flag, other_slot: int) -> bytes:
    """A switch zone's Range body: movement-gate, then `if (cond) { SetFieldCamera; set flag;
    SetControlDirection; InitRegion(other); TerminateEntry(this) }`."""
    flag_class, flag_idx = flag
    body = (opcodes.set_field_camera(to_camera)
            + _region.set_var(flag_class, flag_idx, to_camera)
            + opcodes.set_control_direction(control_value, control_value)
            + opcodes.init_region(other_slot, 0)
            + opcodes.terminate_entry(255))
    return _region.MOVEMENT_GATE + _region.if_block(cond, body) + opcodes.RETURN


def inject_camera_switch(data, *, forward_zone, reverse_zone, to_camera: int = 1,
                         control_value_0: int = -1, control_value_target: int = -1,
                         flag=DEFAULT_FLAG, spawn_wait_n: int = 2,
                         spawn_wait_occurrence: int = 0) -> bytes:
    """Inject a two-camera switch pair (the Gargan Roo convention). Returns new .eb bytes.

    ``forward_zone`` / ``reverse_zone`` are each 4 (x, z) convex corners. Crossing ``forward_zone``
    switches the active background camera ``0 -> to_camera``; crossing ``reverse_zone`` switches it
    back. ``control_value_0`` / ``control_value_target`` are the per-camera SetControlDirection
    (TWIST) values (derive from each camera's yaw) so "up" stays up-screen after a switch. Needs 3
    free entry slots (2 zones + the load-time init/arm entry)."""
    flag_class, flag_idx = flag
    eb = EbScript.from_bytes(data)
    free = eb.free_slots()
    if len(free) < 3:
        raise ValueError(f"need 3 free entry slots for a camera switch, have {len(free)}")
    fwd_slot, rev_slot, init_slot = free[0], free[1], free[2]

    fwd_body = _switch_body(_region.cond_not(flag_class, flag_idx), to_camera,
                            control_value_target, flag, rev_slot)
    rev_body = _switch_body(_region.cond_truthy(flag_class, flag_idx), 0,
                            control_value_0, flag, fwd_slot)

    # both zones appended but NOT auto-armed (the init entry arms the forward one at load)
    out, _ = _region.inject_region(data, forward_zone, fwd_body, slot=fwd_slot, activate=False)
    out, _ = _region.inject_region(out, reverse_zone, rev_body, slot=rev_slot, activate=False)

    # init/arm code entry: reset flag = 0 (camera 0) + InitRegion(forward), run from Main_Init.
    init_body = (_region.set_var(flag_class, flag_idx, 0)
                 + opcodes.init_region(fwd_slot, 0) + opcodes.RETURN)
    init_entry = bytes([0x00, 0x01]) + struct.pack("<HH", 0, 4) + init_body
    out = edit.append_entry(out, init_slot, init_entry)
    wait_off = edit.find_wait(EbScript.from_bytes(out), n=spawn_wait_n,
                              occurrence=spawn_wait_occurrence)
    out = edit.patch_bytes(out, wait_off, opcodes.init_code(init_slot, 0),
                           expect=opcodes.wait(spawn_wait_n))
    return out
