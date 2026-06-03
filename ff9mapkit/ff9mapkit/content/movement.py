"""Set the player movement control direction (TWIST / SetControlDirection, opcode 0x67).

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
"""

from __future__ import annotations

from ..eb import EbScript, edit, opcodes

TWIST_OP = 0x67


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
