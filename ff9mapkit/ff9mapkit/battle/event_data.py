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


def rewrite_main_init(eb_bytes, slot_types, ai_entries=None) -> bytes:
    """Rewrite Main_Init to one ``InitObject(<ai entry>, 0x80+slot)`` per enemy in ``slot_types`` (the spawned
    slots, in order), then RETURN. The AI entry defaults to ``1+type`` (the standard donor layout) but can be
    OVERRIDDEN per slot via ``ai_entries`` (a list parallel to ``slot_types``; a None element keeps the default).

    The override is what makes an OFFSET-entry donor forkable: EF_R007 binds its Goblin (type 0) to entry **2**
    via a ``SWITCH(B_SYSVAR[31])`` (entry 1 is a different type's AI), so the generic ``1+type`` rebind would run
    the WRONG AI on the spawned model. ``[[scene.enemy]] ai_entry = 2`` pins the right one (read it from
    ``battle-ai``). Raises ValueError if Main_Init is absent or a chosen AI entry is missing/empty."""
    eb = EbScript.from_bytes(eb_bytes)
    n = len(eb.entries)
    if n == 0 or eb.entry(0).func_by_tag(0) is None:
        raise ValueError("battle eb has no Main_Init (entry 0, tag 0) to re-author")
    if ai_entries is None:
        ai_entries = [None] * len(slot_types)
    resolved = []
    for s, t in enumerate(slot_types):
        override = ai_entries[s] if s < len(ai_entries) else None
        ai = int(override) if override is not None else _ai_entry(t)
        if override is not None and ai < 1:                  # entry 0 IS Main_Init (always non-empty -> dodges the
            raise ValueError(f"slot {s}: ai_entry = {ai} is invalid; entry 0 is Main_Init -- per-type enemy AI "
                             f"starts at entry 1 (use `battle-ai <scene>` to find the right one)")   # empty check)
        e = eb.entries[ai] if 0 <= ai < n else None
        if e is None or e.empty:
            if override is not None:
                raise ValueError(f"slot {s}: ai_entry = {ai} is not a valid AI entry (the eb has {n} entries; "
                                 f"entry {ai} is out of range or empty). Use `battle-ai <scene>` to find the entry.")
            raise ValueError(f"battle eb has no AI entry for enemy type {t} (expected entry {ai}); this donor's "
                             f"eb layout is non-standard -- pin it with [[scene.enemy]] ai_entry = <entry>, or use "
                             f"a donor whose entries 1..TypCount are per-type AI.")
        resolved.append(ai)
    body = b"".join(opcodes.init_object(resolved[s], ENEMY_UID_BASE + s) for s in range(len(slot_types)))
    body += opcodes.RETURN
    return replace_function_body(eb_bytes, 0, 0, body)
