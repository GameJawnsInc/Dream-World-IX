"""Hold the screen black briefly on entry so the camera SETTLES before it is revealed.

The Memoria engine runs a per-frame smooth-camera follower (``FieldMap.CenterCameraOnPlayer``, scaled by
``Memoria.ini``'s ``CameraStabilizer``) for EVERY field. On a warp-in it eases the camera from its
carried-over position to the spawn-centred target over many frames. Real fields hide this because the
warp's fade-out blacks the screen while the camera settles; the kit's synthesized ``Main_Init`` reveals
immediately (its FadeFilter fires right after ``EnableMove``), so on a large-delta entry -- e.g. the World
Hub entered via a New-Game / F6 warp -- you SEE the camera drift to rest over a few seconds.

Fix (engine-independent, ships on stock Memoria -- no DLL, no ``SmoothCamExcludeMaps`` edit): insert
``DisableMove ; Wait(n) ; EnableMove`` immediately BEFORE Main_Init's reveal fade. The screen is still
black at that point (the field loads black; the reveal fade is what brings it in), so the smooth-cam
converges UNSEEN during the wait; the existing fade then reveals the already-settled camera. Control is
locked during the wait so the player can't wander blind. (memory ``project-ff9-world-hub``;
``FieldMap.cs`` ``CenterCameraOnPlayer`` / ``SmoothCamExcludeMaps`` / ``CameraStabilizer``.)
"""

from __future__ import annotations

from ..eb import EbScript, edit, opcodes

FADE_FILTER = 0xEC          # WIPERGB / "FadeFilter"; arg0 & 2 set => SUB == a fade-IN (reveal)


def add_entry_settle(eb_bytes, wait_frames: int = 45) -> bytes:
    """Insert ``DisableMove ; Wait(wait_frames) ; EnableMove`` just before Main_Init's reveal fade so the
    smooth-camera settles behind the black screen. Returns the input unchanged when ``wait_frames <= 0`` or
    Main_Init has no reveal fade (nothing to hide behind)."""
    if wait_frames <= 0:
        return eb_bytes
    eb = EbScript.from_bytes(eb_bytes)
    e0 = eb.entry(0)
    f0 = e0.func_by_tag(0) if e0 is not None else None
    if f0 is None:
        return eb_bytes
    fade = None
    for i in eb.instrs(f0):
        if i.op == FADE_FILTER and i.args:
            try:
                mode = int(i.args[0])
            except (TypeError, ValueError):
                continue                      # an expression-mode fade: not the template reveal -- skip
            if mode & 2:                      # SUB == fade-IN (reveal); ADD (fade-out) would not help
                fade = i
                break
    if fade is None:
        return eb_bytes
    rel = fade.off - f0.abs_start
    body = opcodes.DISABLE_MOVE + opcodes.wait(wait_frames) + opcodes.ENABLE_MOVE
    return edit.insert_in_function(eb_bytes, 0, 0, rel, body)
