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
# Generalizes the real-field convention (decoded byte-for-byte from Gargan Roo/Passage,
# evt_gargan_gr_lef_0) to N cameras via an AREA model: a state flag holds the CURRENT camera index,
# and each zone owns the floor area where its camera should be active. Entering a zone for camera K
# while flag != K switches to camera K, stores K in the flag, and re-tunes movement
# (SetControlDirection for K's yaw). The flag guard stops re-firing while you stand in a zone;
# NON-OVERLAPPING zones can't flap. An init code-entry resets the flag to 0 + arms every zone on
# field load (state is consistent on entry); after a battle (Main_Init doesn't run) the tag-10
# restore (:func:`add_camera_restore`) re-applies the stored camera + movement.

REINIT_TAG = 10


def _zone_body(to_camera: int, control_value: int, flag) -> bytes:
    """A camera zone's Range body: movement-gate, then `if (flag != to_camera) { SetFieldCamera;
    set flag = to_camera; SetControlDirection }`."""
    flag_class, flag_idx = flag
    actions = (opcodes.set_field_camera(to_camera)
               + _region.set_var(flag_class, flag_idx, to_camera)
               + opcodes.set_control_direction(control_value, control_value))
    return (_region.MOVEMENT_GATE
            + _region.if_not_block(_region.cond_eq(flag_class, flag_idx, to_camera), actions)
            + opcodes.RETURN)


def inject_camera_zones(data, zones, control_values, *, flag=DEFAULT_FLAG, spawn_wait_n: int = 2,
                        spawn_wait_occurrence: int = 0) -> bytes:
    """Inject N camera-switch zones (the area model). Returns new .eb bytes.

    ``zones`` = list of ``(to_camera, [4 (x, z) corners])``; ``control_values[k]`` = the
    SetControlDirection (TWIST) value for camera ``k`` (derive from its yaw). Each zone owns the floor
    area where its camera is active; standing in it sets that camera. Zones SHOULD NOT overlap
    (overlapping zones flap). Needs ``len(zones) + 1`` free entry slots (the zones + one load-time
    init/arm entry that resets the flag to 0 and arms them all)."""
    flag_class, flag_idx = flag
    zones = list(zones)
    eb = EbScript.from_bytes(data)
    if len(eb.free_slots()) < len(zones) + 1:
        raise ValueError(f"need {len(zones) + 1} free entry slots for {len(zones)} camera zones, "
                         f"have {len(eb.free_slots())}")
    out = data
    slots = []
    for to_camera, corners in zones:
        body = _zone_body(int(to_camera), int(control_values[int(to_camera)]), flag)
        out, slot = _region.inject_region(out, [tuple(p) for p in corners], body, activate=False)
        slots.append(slot)
    # init/arm entry: reset flag = 0 (camera 0 at load) + arm every zone.
    init_body = _region.set_var(flag_class, flag_idx, 0)
    for s in slots:
        init_body += opcodes.init_region(s, 0)
    init_body += opcodes.RETURN
    init_entry = bytes([0x00, 0x01]) + struct.pack("<HH", 0, 4) + init_body
    init_slot = EbScript.from_bytes(out).first_free_slot()
    out = edit.append_entry(out, init_slot, init_entry)
    out = edit.activate(out, opcodes.init_code(init_slot, 0), spawn_wait_n=spawn_wait_n,
                        spawn_wait_occurrence=spawn_wait_occurrence)
    return out


def add_camera_restore(data, cameras_used, control_values, *, flag=DEFAULT_FLAG) -> bytes:
    """Add an after-battle camera restore to Main_Reinit (tag 10). Returns new .eb bytes.

    For each non-zero camera ``K`` in ``cameras_used``: ``if (flag == K) { SetFieldCamera(K);
    SetControlDirection(K) }``. After a battle the field runs tag-10 (NOT Main_Init, so the flag isn't
    reset) -- this re-applies the camera + movement the player was on. Requires an existing tag-10
    (``content.reinit.add_reinit`` / an encounter); a no-op if no non-zero camera is used."""
    flag_class, flag_idx = flag
    eb = EbScript.from_bytes(data)
    f = eb.entry(0).func_by_tag(REINIT_TAG)
    if f is None:
        raise ValueError("entry 0 has no tag-10 handler (run content.reinit.add_reinit first)")
    restore = b""
    for k in sorted({int(c) for c in cameras_used}):
        if k == 0:
            continue
        actions = opcodes.set_field_camera(k) + opcodes.set_control_direction(
            int(control_values[k]), int(control_values[k]))
        restore += _region.if_block(_region.cond_eq(flag_class, flag_idx, k), actions)
    if not restore:
        return data if isinstance(data, (bytes, bytearray)) else data.to_bytes()
    return edit.insert_bytes(data, f.abs_start, restore)
