"""Re-author a battle eb's Main_Init so its enemy-AI binding matches an edited spawn composition.

A battle ``EVT_BATTLE`` eb's entry 0 (tag 0 = Main_Init) issues one ``InitObject(1+type, 0x80+slot)``
per enemy the donor spawns; the per-type AI lives in entries ``1..TypCount`` (entry ``1+T`` = type T's
AI), and the engine binds these objects POSITIONALLY to enemy slots. So if a minted battle's raw16
spawns MORE enemies than Main_Init issues InitObjects for, the extra slots get null AI objects and the
(N+1)th enemy's death misroutes into the player -> the player model twitches (root cause in
``project_ff9_battle_backgrounds``).

``rewrite_main_init`` issues exactly one InitObject per spawned slot, REUSING the donor's existing
per-type AI entries -- so the AI binding always matches the pattern and a minted battle can exceed the
donor's natural enemy count (up to the engine's hard cap of 4) using any types already in the scene.

Verified on EF_R007 / BU_E072 / AC_E031 (2026-06-09): uid = 0x80 + slot; AI entry = 1 + enemy type.
"""
from __future__ import annotations

from ..eb import opcodes
from ..eb.edit import replace_function_body
from ..eb.model import EbScript

ENEMY_UID_BASE = 0x80     # enemy object uid = 0x80 + slot index
INITOBJECT_OP = 0x09


def _ai_entry(type_no: int) -> int:
    """Entry index of enemy type ``type_no``'s AI (entry 0 = Main_Init; per-type AI = entries 1..N)."""
    return 1 + type_no


def main_init_initobject_count(eb_bytes) -> int:
    """Number of InitObject calls in Main_Init (entry 0 tag 0). For an UNCONDITIONAL Main_Init this is
    the donor's simultaneous-enemy count; for a conditional one (type-select) it's an upper bound."""
    eb = EbScript.from_bytes(eb_bytes)
    f = eb.entry(0).func_by_tag(0) if eb.entries else None
    return sum(1 for ins in eb.instrs(f) if ins.op == INITOBJECT_OP) if f else 0


def rewrite_main_init(eb_bytes, slot_types) -> bytes:
    """Rewrite Main_Init to ``InitObject(1+type, 0x80+slot)`` for each enemy in ``slot_types`` (the
    spawned slots, in order), then RETURN. Reuses the donor's per-type AI entries. Raises ValueError
    if Main_Init is absent or a needed AI entry (``1+type``) is missing/empty (a non-standard donor
    layout the kit won't re-author)."""
    eb = EbScript.from_bytes(eb_bytes)
    n = len(eb.entries)
    if n == 0 or eb.entry(0).func_by_tag(0) is None:
        raise ValueError("battle eb has no Main_Init (entry 0, tag 0) to re-author")
    for t in sorted(set(slot_types)):
        ai = _ai_entry(t)
        e = eb.entries[ai] if 0 <= ai < n else None
        if e is None or e.empty:
            raise ValueError(f"battle eb has no AI entry for enemy type {t} (expected entry {ai}); "
                             f"this donor's eb layout is non-standard -- cannot re-author its spawn "
                             f"composition. Use a donor whose entries 1..TypCount are per-type AI.")
    body = b"".join(opcodes.init_object(_ai_entry(t), ENEMY_UID_BASE + s)
                    for s, t in enumerate(slot_types))
    body += opcodes.RETURN
    return replace_function_body(eb_bytes, 0, 0, body)
