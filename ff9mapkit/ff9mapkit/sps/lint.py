"""Offline structural validator for an authored / edited ``.sps`` effect (mirrors ``battle.seqauthor.lint_seq``:
a bare ``list[str]`` of problems, empty == OK, NEVER raises). The codec guarantees a byte-exact round-trip of a
PARSED file; this guards an AUTHORED or ``[[sps_edit]]``-edited model BEFORE serialize -> deploy, catching the
references that would corrupt the bin or crash ``SPSEffect._GenerateSPSPrims`` at runtime. -> [[project-ff9-sps-authoring]].
"""
from __future__ import annotations

from . import codec as _codec


def lint_sps(model: _codec.Sps) -> list[str]:
    """Structural problems of an :class:`codec.Sps` (empty list == OK). This is an AUTHORING-quality check
    (for from-scratch / Tier-0 display): the uv/rgb index-in-table checks flag a prim that samples a cell you
    never defined. NOTE a few real shipping effects legitimately index a nibble PAST a short table into the
    adjacent data region (valid, deterministic engine behaviour), so this is NOT asserted clean on every donor
    and is NOT used as the ``[[sps_edit]]`` gate (``edit.apply_sps_edits`` gates on encodability instead)."""
    problems: list[str] = []
    n_uv = len(model.uv_table)
    n_rgb = len(model.rgb_table)

    if not (1 <= model.frame_count <= 0x7FFF):
        problems.append(f"frame_count {model.frame_count} out of range 1..32767")
    if n_uv == 0:
        problems.append("uv_table is empty -- prims have no UV cell to sample")
    if n_uv > 0xFFFF:
        problems.append(f"uv_table has {n_uv} entries (max 65535 for the u16 rgb_offset)")
    if n_rgb == 0:
        problems.append("rgb_table is empty -- prims have no ramp colour")
    if not (1 <= model.w_raw <= 0xFF) or not (1 <= model.h_raw <= 0xFF):
        problems.append(f"size bytes h_raw={model.h_raw} w_raw={model.w_raw} must be 1..255 "
                        "(quad/UV half-size = (raw-1)*2 / (raw-1))")

    for fi, frame in enumerate(model.frames):
        if len(frame) > 0xFF:
            problems.append(f"frame {fi}: {len(frame)} prims exceeds the 255-prim u8 count")
        for pi, p in enumerate(frame):
            if not (0 <= p.uv_index < n_uv):
                problems.append(f"frame {fi} prim {pi}: uv_index {p.uv_index} out of range (uv_table has {n_uv})")
            if not (0 <= p.rgb_index < n_rgb):
                problems.append(f"frame {fi} prim {pi}: rgb_index {p.rgb_index} out of range (rgb_table has {n_rgb})")
            if not (-128 <= p.pos_x <= 127) or not (-128 <= p.pos_y <= 127):
                problems.append(f"frame {fi} prim {pi}: pos ({p.pos_x},{p.pos_y}) out of i8 range (-128..127)")

    for ri, entry in enumerate(model.rgb_table):
        r, g, b, pad = entry
        if pad != 0:
            problems.append(f"rgb_table[{ri}]: pad byte {pad} must be 0 (PSX STP bit)")
        if not all(0 <= c <= 255 for c in (r, g, b)):
            problems.append(f"rgb_table[{ri}]: colour {(r, g, b)} channel out of 0..255")
    return problems


def lint_sps_bytes(data: bytes) -> list[str]:
    """Lint raw ``.sps`` bytes -- parse then lint, degrading to a problem string on a parse failure
    (never raises, so a ``validate`` caller is build-safe)."""
    try:
        model = _codec.parse(data)
    except _codec.SpsCodecError as ex:
        return [f"unparseable .sps: {ex}"]
    return lint_sps(model)
