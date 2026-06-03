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

from ..eb import EbScript, edit, opcodes

BGCACTIVE_OP = 0x71      # EnableCameraServices


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
