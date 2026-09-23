"""Reproduce a real field's LOAD-TIME engine walkmesh hotfix in a fork.

A few real fields rely on a hardcoded Memoria hotfix (keyed on the real ``fldMapNo``) that toggles
walkmesh-triangle active-state at field load -- e.g. Gulug/Room (2356) deactivates the broken-wall triangles
so the player can't walk through the gap. A verbatim/native fork runs at a custom id (>= 4000), so a RAW
``fldMapNo`` guard is false and the hotfix never fires -> the forked walkmesh is wrong there (a guard the custom
engine routes through ``EffectiveFieldId`` still fires for a fork with a donor row, so ``import`` emits no
toggles for it). See the catalog and the two tractability classes in :mod:`ff9mapkit.walkmesh_hotfixes`.

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


# The guard's condition: the player has movement control (B_SYSVAR[2], the engine's usercontrol) AND its walkmesh
# triangle reads -1 (B_BGIID of B_PTR(250); a detached actor's activeTri is -1).
REATTACH_COND = "B_SYSVAR[2] const(0) B_NE B_PTR(250) B_BGIID const(0) B_LT B_ANDAND"
# The kit template's idle player Loop: Wait(1) and a jump back to it. The guard replaces exactly this body.
IDLE_LOOP = opcodes.wait(1) + opcodes.encode(0x01, 0x10000 - 6)


def reattach_loop_body() -> bytes:
    """The player's Loop as a re-attach guard: every frame, ``SetPathing(1)`` when the player has control but no
    triangle, then ``Wait(1)``. It replaces the template's idle ``Wait(1)`` loop, so it runs for the life of the
    field at the cost of one expression a frame."""
    from ..eb import exprasm
    from ..eb.labelasm import JMP, JMP_IFNOT, asm, label
    cond = bytes([0x05]) + exprasm.assemble(REATTACH_COND + " B_EXPR_END")
    return asm([label("top"), cond, (JMP_IFNOT, "idle"), opcodes.set_pathing(1),
                label("idle"), opcodes.wait(1), (JMP, "top")])


def reattach_player(eb_bytes) -> bytes:
    """Keep a KIT-BUILT player on the walkmesh that a delayed engine hotfix detaches.

    Field 2507's ``FieldMap.DelayedActiveTri`` runs 0.5 s after load and clears the walkmesh flag of every actor
    whose ``isPlayer`` is false (``BGI_charSetActive(fac, 0)``). On a fork whose .eb the kit built, that includes
    the player, who then walks straight off the mesh. The real script re-attaches its player with
    ``SetPathing(1)``. When the pass lands relative to the script varies with the load (a fixed one-shot 30 frames
    in raced it and lost in-game), so this is a guard instead: the player's Loop -- the object's own thread, so
    ``SetPathing`` acts on the player -- re-attaches it whenever it has control and no triangle. Every kit
    sequence that turns pathing off (ladders, platforms, jumps, cutscenes) does so with movement disabled, so the
    guard never fights one. A detached actor keeps its y, and the engine re-seats it on the found triangle nearest
    that y, so the player stays on its own floor.

    Returns ``eb_bytes`` unchanged when no entry defines the player. Raises ``ValueError`` when the player's Loop
    is not the template's idle loop -- replacing it would silently drop whatever was added there."""
    from ..eb import EbScript
    from .npc import _find_player_entry
    eb = EbScript.from_bytes(eb_bytes)
    try:
        pe = _find_player_entry(eb)
    except ValueError:
        return eb_bytes
    loop = eb.entry(pe).func_by_tag(1)
    if loop is None or bytes(eb.data[loop.abs_start:loop.abs_end]) != IDLE_LOOP:
        raise ValueError(f"the player's Loop (entry {pe}, tag 1) is not the kit's idle loop; the walkmesh re-attach "
                         f"guard would replace it")
    return edit.replace_function_body(eb_bytes, pe, 1, reattach_loop_body())
