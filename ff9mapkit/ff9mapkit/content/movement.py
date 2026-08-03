"""Player-control shaping: the TWIST control direction, and the PARTIAL-CONTROL pad-mask lane.

FF9 rotates raw WASD/stick input (x = right, z = forward) about world-Y by an angle BEFORE
applying it, so "up" on the controller matches "up the screen" for the field's camera. The engine
stores the angle as ``angle = (value + 1) / 256 * 360`` degrees (FieldState.SetTwistAD), with the
raw value a signed byte. A front-facing (yaw-0) camera uses value ``-1`` (= 0 deg) — the kit's blank
default. For a camera ORBITED by ``yaw`` degrees about the scene centre, the player's forward must
rotate by that same yaw so W still goes up the screen (verified in-game): ``value = round(yaw/360 *
256) - 1``. Real FF9 fields do exactly this — e.g. the ~90 deg-yawed Treno shop camera ships a
matching TWIST.

This is the missing half of authoring a yawed custom field: :mod:`ff9mapkit.scene.guide`/``cam``
place the camera + walkmesh correctly at any yaw, and this makes the controls match.

PARTIAL CONTROL (movement survey 1/ 2, Tier-2 item 7): ``AddControllerMask`` (0xB9) ORs button
bits into ``EventInput.PSXCntlPadMask[0]`` -- a masked button simply stops arriving, and masking
any DIRECTION bit stops walking **independently of the DisableMove lock** (EventInput.cs:397:
``isMovementControl=false`` whenever the mask covers a movement bit). ``RemoveControllerMask``
(0xBA) clears bits. This is stock's tutorial / minigame lane -- the only control shaping that can
freeze WALKING while leaving chosen BUTTONS live: Marsh/Chocobo tutorials mask 240 (the four
directions), field 178 masks 255 (directions+Select+Start), field 95 unmasks Select alone. Note
``DisableMenu`` is this same mechanism (the engine masks the menu bit); the mask survives a
``DisableMove``/``EnableMove`` bracket (EnableMove's menu re-grant checks it, survey 1).
"""

from __future__ import annotations

from ..eb import EbScript, edit, opcodes

TWIST_OP = 0x67

# The engine's physical-button bits (EventInput.cs:537-550) by author-facing name, plus the group
# stock's tutorials actually use. The script operand is a u16, so only the physical page is
# reachable (the logical Cancel/Confirm/Menu bits at 0x10000+ are engine-internal).
BUTTONS = {
    "select": 0x0001, "start": 0x0008,
    "up": 0x0010, "right": 0x0020, "down": 0x0040, "left": 0x0080,
    "l2": 0x0100, "r2": 0x0200, "l1": 0x0400, "r1": 0x0800,
    "triangle": 0x1000, "circle": 0x2000, "cross": 0x4000, "square": 0x8000,
    # groups
    "directions": 0x00F0,        # Up|Right|Down|Left -- the walk freeze (stock's 240)
}


def button_mask(names) -> int:
    """OR the named buttons into one pad-mask value. ``names`` = a name, an int mask, or a list of
    either. Raises on an unknown name (the validator surfaces this as a build problem)."""
    if isinstance(names, (int,)) and not isinstance(names, bool):
        return int(names)
    if isinstance(names, str):
        names = [names]
    m = 0
    for n in names:
        if isinstance(n, int) and not isinstance(n, bool):
            m |= n
            continue
        key = str(n).strip().lower()
        if key not in BUTTONS:
            raise ValueError(f"unknown button {n!r} -- one of {', '.join(sorted(BUTTONS))} (or a raw mask)")
        m |= BUTTONS[key]
    if not 0 < m <= 0xFFFF:
        raise ValueError(f"pad mask {m:#x} out of the u16 operand range")
    return m


def mask_pad(buttons) -> bytes:
    """Body part: ``AddControllerMask(0, mask)`` -- the named buttons stop arriving (directions =
    walking stops). Standing state: pair with a later :func:`unmask_pad` (another event, a scene end)."""
    return opcodes.encode(0xB9, 0, button_mask(buttons))


def unmask_pad(buttons) -> bytes:
    """Body part: ``RemoveControllerMask(0, mask)`` -- re-enable the named buttons."""
    return opcodes.encode(0xBA, 0, button_mask(buttons))


def control_value_for_angle(angle_deg: float) -> int:
    """Signed-byte SetControlDirection value whose decoded angle ~= ``angle_deg`` (mod 360).

    Inverse of ``(value+1)/256*360``. The angle is normalised to (-180, 180] first, then clamped to
    the signed-byte range so any yaw maps to a valid operand."""
    a = ((float(angle_deg) + 180.0) % 360.0) - 180.0      # normalise to (-180, 180]
    v = int(round(a / 360.0 * 256.0)) - 1
    if v < -128:
        v += 256
    elif v > 127:
        v -= 256
    return v


def set_control_direction(eb_bytes, value: int, *, entry_index: int = 0,
                          func_tag: int | None = 0) -> bytes:
    """Overwrite the existing TWIST args (both analog + digital) with ``value``, in place.

    The blank field carries exactly one ``SetControlDirection`` in Main_Init (the kit default
    ``-1, -1`` = 0 deg). This is a same-length patch (``67 00 vv vv``), so there is no bytecode
    shift and no jump relocation — safe to run first, before any appends.
    """
    eb = EbScript.from_bytes(eb_bytes)
    hits = edit.find_instrs(eb, TWIST_OP, entry_index=entry_index, func_tag=func_tag)
    if not hits:
        raise ValueError("no SetControlDirection (TWIST 0x67) in Main_Init to set")
    if len(hits) > 1:
        raise ValueError(f"expected exactly one TWIST in Main_Init, found {len(hits)}")
    off = hits[0].off
    new = opcodes.set_control_direction(int(value), int(value))
    return edit.patch_bytes(eb_bytes, off, new, expect=eb_bytes[off:off + len(new)])
