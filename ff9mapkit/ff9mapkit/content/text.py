"""Author field dialogue text (``.mes``).

Memoria loads field text cumulatively across mods: a mod's
``FF9_Data/embeddedasset/text/<lang>/field/<mesId>.mes`` is merged over the base block, and
explicit ``[TXID=n]`` indices let a mod *add* entries without disturbing the base text — as
long as you use indices the base block doesn't occupy (a high TXID like 500+). That is the
trick proven in Session 9: drop a ``<mesId>.mes`` with our line at a high index; the base
text is untouched, our entry is added, and an NPC's WindowSync(... , txid) resolves to it.

Format of one entry::

    _[TXID=500][STRT=10,1][TAIL=UPR]I miss you Zidane[ENDN]

The leading ``_`` (any non-``[STRT=`` character) is required so the parser treats ``[TXID=]``
as a re-index rather than the start of entry 0.
"""

from __future__ import annotations

# A safe starting index for mod-added dialogue (base field blocks don't use these).
DEFAULT_BASE_TXID = 500


def mes_entry(text: str, txid: int, *, strt: tuple = (10, 1), tail: str = "UPR") -> str:
    """One ``.mes`` entry line that ADDS dialogue at ``txid`` without touching base text."""
    strt_s = ",".join(str(v) for v in strt)
    return f"_[TXID={txid}][STRT={strt_s}][TAIL={tail}]{text}[ENDN]"


def build_mes(lines, *, start_txid: int = DEFAULT_BASE_TXID) -> tuple[str, dict]:
    """Build a ``.mes`` file body from an ordered list of dialogue strings.

    Returns ``(text, mapping)`` where ``mapping[i]`` is the TXID assigned to ``lines[i]`` (so a
    caller can point each NPC's WindowSync at the right id). TXIDs are ``start_txid + i``.
    """
    entries = []
    mapping = {}
    for i, line in enumerate(lines):
        txid = start_txid + i
        mapping[i] = txid
        entries.append(mes_entry(line, txid))
    return "\n".join(entries) + "\n", mapping
