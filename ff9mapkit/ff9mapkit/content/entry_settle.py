"""Hold the screen black briefly on entry so the camera SETTLES before it is revealed.

The Memoria engine runs a per-frame smooth-camera follower (``FieldMap.CenterCameraOnPlayer``, scaled by
``Memoria.ini``'s ``CameraStabilizer``) for EVERY field. On a warp-in it eases the camera from its
carried-over position to the spawn-centred target over many frames. Real fields hide this because the
warp's fade-out blacks the screen while the camera settles; the kit's synthesized ``Main_Init`` reveals
immediately (its FadeFilter fires right after ``EnableMove``), so on a large-delta entry -- e.g. the World
Hub entered via a New-Game / debug-menu warp -- you SEE the camera drift to rest over a few seconds.

Fix (engine-independent, ships on stock Memoria -- no DLL, no ``SmoothCamExcludeMaps`` edit): hold
Main_Init with ``DisableMove ; Wait(n)`` before its reveal fade -- on the synthesized template just before
its ``set MAP159 = 1`` "main ready" step, so the template's own control handshake grants when the hold ends
(see :func:`add_entry_settle`). The screen is still black there (the field loads black; the reveal fade is
what brings it in), so the smooth-cam converges UNSEEN during the wait; the existing fade then reveals the
already-settled camera. Control stays locked during the wait so the player can't wander blind. (memory
``project-ff9-world-hub``; ``FieldMap.cs`` ``CenterCameraOnPlayer`` / ``SmoothCamExcludeMaps`` /
``CameraStabilizer``.)
"""

from __future__ import annotations

import math

from ..eb import EbScript, edit, opcodes
from ..scene import cam as _cam

FADE_FILTER = 0xEC          # WIPERGB / "FadeFilter"; arg0 & 2 set => SUB == a fade-IN (reveal)

# ---- the "auto" estimator (rung 7 of the field-entry arc) -------------------------------------
# entry_settle = "auto" COMPUTES the hold instead of hand-copying "the hub precedent" (45). The
# engine's follower (FieldMap.CenterCameraOnPlayer, per HonoLateUpdate frame -- the same tick the
# event engine counts Wait frames in) eases geometrically:  new = target + (prev - target) * s,
# s = CameraStabilizer/100 (per-user Memoria.ini, default 85). The camera's target is the player's
# CLAMPED GTE screen position (aim = player pos + charAimHeight in y, offset = compute_offset,
# clamped to the .bgx Viewport); before the player binds it targets the bare offset (the null-player
# home). So the warp-in drift is the px distance between those two clamped points, and it decays by
# s each frame: frames-to-subpixel = ln(delta/tol) / -ln(s), plus the bind window (SmoothCamDelay
# 4-6 + the frames until playerController wires up).
#
# Calibrated 2026-07-13 against the in-game-proven holds (tol 0.25px, bind 10): hub 4500/Gargan Roo
# delta 63px -> 45 (proven 45), hub 4600/Mognet delta 61px -> 45 (60 proven clean, 90 over-tuned),
# waystation 6500/Daguerreo delta 107px -> 50 (proven 45). The Viewport clamp bounds any realistic
# delta, and the log keeps the answer flat (~45-60 even for huge scrolling canvases) -- exactly the
# proven band. Best-effort: CameraStabilizer is per-user (we bake for the default 85); the spawn's
# y is taken as 0 (a wrong floor height moves the answer by only a frame or two -- it's inside a log).
DEFAULT_ENTRY_SETTLE = 45   # the in-game-proven fallback when "auto" can't resolve a camera
DEFAULT_STABILIZER = 85     # Memoria.ini CameraStabilizer default (SmoothCamPercent = /100)
CHAR_AIM_HEIGHT = 324.0     # FieldMap.charAimHeight -- the camera aims this far above the player's feet
BIND_DELAY_FRAMES = 10      # SmoothCamDelay (4-6) + the frames until playerController binds
SETTLE_TOL_PX = 0.25        # converged = the remaining drift is sub-pixel (every later step smaller)
AUTO_MIN_FRAMES = 20        # sanity band: never compute a uselessly-short ...
AUTO_MAX_FRAMES = 90        # ... or an over-tuned hold (90 read as "very long black" in-game)


def is_auto(value) -> bool:
    """True if a ``[camera] entry_settle`` value asks for the computed hold (the string ``"auto"``)."""
    return isinstance(value, str) and value.strip().lower() == "auto"


def _clamped_cam_pos(sx, sy, camera):
    """The engine's Viewport clamp (FieldMap.SceneService3DScroll): a screen point -> where the
    camera may actually rest. Clamped in "vrp space" (aimX = sx + HalfFieldWidth, aimY = HalfFieldHeight - sy)."""
    vminx, vmaxx, vminy, vmaxy = camera.viewport
    ax = min(max(sx + _cam.HALF_FIELD_W, vminx), vmaxx)
    ay = min(max(_cam.HALF_FIELD_H - sy, vminy), vmaxy)
    return (ax - _cam.HALF_FIELD_W, _cam.HALF_FIELD_H - ay)


def warp_in_delta_px(camera, spawn, y: float = 0.0) -> float:
    """The warp-in drift (px): distance between the camera's null-player home (the clamped bare
    projection offset -- where it rests before the player binds) and its player-bound target (the
    spawn's clamped screen position, aimed ``CHAR_AIM_HEIGHT`` above the feet)."""
    off = _cam.compute_offset(camera)
    home = _clamped_cam_pos(off[0], off[1], camera)
    sx, sy, _ = _cam.project((float(spawn[0]), y + CHAR_AIM_HEIGHT, float(spawn[1])), camera, off)
    bound = _clamped_cam_pos(sx, sy, camera)
    return math.hypot(bound[0] - home[0], bound[1] - home[1])


def estimate_entry_settle(camera, spawn, *, stabilizer: int = DEFAULT_STABILIZER, y: float = 0.0) -> int:
    """Frames to hold black so the smooth-cam converges unseen: ``BIND_DELAY_FRAMES +
    ln(delta/SETTLE_TOL_PX) / -ln(s)``, rounded up to a multiple of 5 and clamped to the sane band.
    A sub-1px delta returns 0 (the camera doesn't move -- nothing to hide, and 0 keeps the build
    byte-identical). ``spawn`` is the ``[player] spawn`` (x, z); ``camera`` the field's LOAD camera
    (index 0 -- the settle hides the load-time ease, not later camera-zone switches)."""
    delta = warp_in_delta_px(camera, spawn, y=y)
    if delta < 1.0:
        return 0
    s = min(max(int(stabilizer), 0), 99) / 100.0
    ease = 0.0 if s <= 0.0 else math.log(delta / SETTLE_TOL_PX) / -math.log(s)
    frames = int(math.ceil((BIND_DELAY_FRAMES + ease) / 5.0)) * 5
    return min(max(frames, AUTO_MIN_FRAMES), AUTO_MAX_FRAMES)


# The template's control handshake (content.entrylock has the full story): Main_Init sets MAP159 = 1
# ("main ready") after spawning its objects, then re-affirms `if (MAP158 == 1) { grant }`; the player's
# Init sets MAP158 = 1 ("player ready") and grants `if (MAP159 == 1)`. Whichever runs LAST grants.
_SET_MAIN_READY = bytes([0x05, 0xC5, 159, 0x7D, 1, 0, 0x2C, 0x7F])     # set MAP159 = 1


def _handshake_hold_offset(eb: EbScript, f0, fade) -> int | None:
    """Main_Init-relative offset of the template's ``set MAP159 = 1``, when the whole handshake is present
    (that SET and the ``if (MAP158 == 1)`` re-affirm before the reveal fade, and the player Init's
    ``set MAP158 = 1`` latch); else None."""
    from .entrylock import _SET_LATCH, _TEST_LATCH
    from .ladder import find_player_entry
    body = bytes(eb.data[f0.abs_start:fade.off])
    ready = next((i.off - f0.abs_start for i in eb.instrs(f0)
                  if i.off < fade.off and bytes(eb.data[i.off:i.off + len(_SET_MAIN_READY)]) == _SET_MAIN_READY),
                 None)
    if ready is None or body.find(_TEST_LATCH, ready) < 0:
        return None
    try:
        init = eb.entry(find_player_entry(eb)).func_by_tag(0)
    except ValueError:
        return None
    if init is None or bytes(eb.data[init.abs_start:init.abs_end]).find(_SET_LATCH) < 0:
        return None
    return ready


def add_entry_settle(eb_bytes, wait_frames: int = 45, *, locked_entrances=()) -> bytes:
    """Hold Main_Init for ``wait_frames`` behind the black screen so the smooth-camera settles before the
    reveal fade. Returns the input unchanged when ``wait_frames <= 0`` or Main_Init has no reveal fade
    (nothing to hide behind).

    On the synthesized template the hold is ``DisableMove ; Wait(wait_frames)`` inserted just BEFORE
    Main_Init's ``set MAP159 = 1``: Main is "not ready" for the hold, so the player's Init (which finishes on
    its first tick) arms its MAP158 latch without granting, and Main's own ``if (MAP158 == 1)`` re-affirm
    grants when the hold ends. No extra grant is added, and [player] locked_entrances needs nothing here --
    content.entrylock already gates both template grant sites. (Placing it before the fade instead let the
    player's latch hand back control DURING the hold once its Init stopped taking ~48 ticks.)

    Anywhere without that handshake it falls back to ``DisableMove ; Wait ; EnableMove`` just before the
    reveal fade. ``locked_entrances``: that closing ``EnableMove`` is an UNCONDITIONAL grant, which would
    re-grant control on a ``[player] locked_entrances`` arrival (the arrive-locked contract says the
    on_entry hook owns that grant). Gate the EnableMove on the same entrance ids -- a locked arrival
    still gets the black hold (its own DisableMove is a harmless re-lock), just not the grant."""
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
    hold = _handshake_hold_offset(eb, f0, fade)
    if hold is not None:
        return edit.insert_in_function(eb_bytes, 0, 0, hold, opcodes.DISABLE_MOVE + opcodes.wait(wait_frames))
    rel = fade.off - f0.abs_start
    grant = opcodes.ENABLE_MOVE
    if locked_entrances:
        from . import entrylock as _entrylock
        grant = _entrylock._entrance_gate(locked_entrances, len(grant)) + grant
    body = opcodes.DISABLE_MOVE + opcodes.wait(wait_frames) + grant
    return edit.insert_in_function(eb_bytes, 0, 0, rel, body)
