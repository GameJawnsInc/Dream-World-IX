"""Reproduce a real field's LOAD-TIME engine walkmesh hotfix in a fork.

A few real fields rely on a hardcoded Memoria hotfix (keyed on the real ``fldMapNo``) that toggles
walkmesh-triangle active-state at field load -- e.g. Gulug/Room (2356) deactivates the broken-wall triangles
so the player can't walk through the gap. A verbatim/native fork runs at a custom id (>= 4000), so that
``fldMapNo`` guard is false and the hotfix never fires -> the forked walkmesh is wrong there. See the catalog
and the two tractability classes in :mod:`ff9mapkit.walkmesh_hotfixes`.

This module reproduces the AUTO (load-time, unconditional) class: it prepends ``EnablePathTriangle(tri, state)``
-- opcode 0x9A, whose engine handler IS ``WalkMesh.BGI_triSetActive`` -- to ``Main_Init`` (entry-0 tag-0), so
the triangles are in the right state from the first frame, exactly as the engine sets them at load. The
``.bgi`` stays byte-verbatim (the fix lives in the script layer). A tag-0 prepend (``rel_off == 0``) is
shift-safe even on a jump-table donor, and ``EnablePathTriangle`` is language-identical. No toggles -> the eb
is returned unchanged. Mirrors :mod:`ff9mapkit.content.areatitle` / :mod:`ff9mapkit.content.startup`.
"""
from __future__ import annotations

from ..eb import edit, opcodes

ENABLE_PATH_TRIANGLE = 0x9A   # EnablePathTriangle(triId, active) -- the engine handler is BGI_triSetActive


def toggles_body(toggles) -> bytes:
    """The bare ``EnablePathTriangle(tri, state)`` sequence for ``toggles`` (an iterable of ``(tri, state)``),
    or ``b""`` when there are none. ``state`` is coerced to 0/1 (1 = active/walkable)."""
    out = b""
    for tri, state in (toggles or ()):
        out += opcodes.encode(ENABLE_PATH_TRIANGLE, int(tri), 1 if int(state) else 0)
    return out


def apply_tri_toggles(eb_bytes, toggles) -> bytes:
    """Prepend the load-time triangle toggles to ``Main_Init`` (entry-0 tag-0). Returns ``eb_bytes`` unchanged
    when ``toggles`` is empty (so a field with no walkmesh hotfix builds byte-for-byte as before)."""
    body = toggles_body(toggles)
    if not body:
        return eb_bytes
    return edit.insert_in_function(eb_bytes, 0, 0, 0, body)
