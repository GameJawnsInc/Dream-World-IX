"""Verbatim-`.eb` fork -- ship a real field's WHOLE event script instead of re-synthesizing it.

The faithful realization of "entry-0 carry" (docs/FORK_FIDELITY.md): a story field's entry-0 ``Main_Init``
arms its objects/regions and gates the cast by ScenarioCounter, and the gated doors read MAP vars it sets --
so the only way those references resolve is to keep the donor's WHOLE entry layout. This mode does exactly
that: the build ships the donor's `.eb` verbatim (entry-0 + every object + every gateway, slots intact) and
only **remaps the `Field()` destinations**; the field then runs its real logic. Proven in-game on Dali Inn
(the gated door opens, the cast gates by story beat).

The declarative content blocks ([[npc]]/[[gateway]]/...) are NOT used in this mode -- the `.eb` is whole, so
there is nothing to synthesize. Pair with a `[startup]` block to boot a chosen beat. LIMITS (vs a perfect
clone): the donor `.mes` text is a separate carry (TXIDs may not resolve until then), and a fork reached by
F6-warp has no entrance fade to mask first-frame model streaming.
"""
from __future__ import annotations

import json
import struct

from ..eb import EbScript

FIELD_OP = 0x2B           # Field(dest) -- the warp; dest is a 2-byte literal at instruction offset +2


def remap_fields(eb_bytes: bytes, retarget: dict) -> bytes:
    """Patch every ``Field(id)`` literal whose id is in ``retarget`` (real destination -> fork id). Ids NOT in
    the map are left as live seams (the door warps back into the real game). Empty ``retarget`` -> unchanged."""
    if not retarget:
        return eb_bytes
    eb = EbScript.from_bytes(eb_bytes)
    buf = bytearray(eb_bytes)
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            for i in eb.instrs(f):
                if i.op == FIELD_OP and i.imm(0) in retarget:
                    struct.pack_into("<H", buf, i.off + 2, int(retarget[i.imm(0)]) & 0xFFFF)
    return bytes(buf)


def verbatim_eb(project):
    """The verbatim `.eb` to ship for ``project`` (from its ``[verbatim_eb]`` block, ``bin`` + optional
    ``retarget``), Field-remapped -- or ``None`` if the project isn't a verbatim fork (the build then
    synthesizes from the field.toml as usual). The same bytecode ships for every language (it is
    language-identical; only the cosmetic name field differs, which the donor's already carries)."""
    spec = project.raw.get("verbatim_eb")
    if not spec or not spec.get("bin"):
        return None
    retarget = {int(k): int(v) for k, v in (spec.get("retarget") or {}).items()}
    return remap_fields(project.path(spec["bin"]).read_bytes(), retarget)


def verbatim_mes(project, lang: str):
    """The donor field's WHOLE `.mes` text body to ship for ``lang`` (from the ``[verbatim_eb] text`` JSON
    sidecar, ``{lang: body}``) -- the verbatim `.eb`'s index-txids resolve straight into it. Falls back to the
    ``us`` body for a language the dialogue reader couldn't distinguish. ``None`` if the fork carries no text."""
    spec = project.raw.get("verbatim_eb") or {}
    tf = spec.get("text")
    if not tf:
        return None
    data = json.loads(project.path(tf).read_text(encoding="utf-8"))
    return data.get(lang) or data.get("us")
