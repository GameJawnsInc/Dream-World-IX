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

# The dialogue window's TAIL — the little pointer that aims at the speaker (FF9's "who's talking"
# cue; there's no separate name-box). Codes map to Dialog.TailPosition (FFIXTextTag.GetTailPosition):
#   UPR/UPL upper-right/left · LOR/LOL lower-right/left · UPC/LOC upper/lower-center
#   ...F variants force that corner · DEFT = engine default/auto-position
TAIL_CODES = {"UPR", "UPL", "LOR", "LOL", "UPC", "LOC",
              "UPRF", "UPLF", "LORF", "LOLF", "DEFT"}
DEFAULT_TAIL = "UPR"

# How a `speaker` name is prefixed onto a line. FF9 has no name-box, so a name is just part of the
# text; ": " is the common readable form. Use a name-variable tag in the speaker for a renameable
# party member, e.g. speaker = "[VIVI]" -> renders the player's chosen name for Vivi.
SPEAKER_SEP = ": "


def with_speaker(speaker, text: str) -> str:
    """Prefix ``speaker`` onto a dialogue line (``"Vivi: ...">``), or return ``text`` unchanged when no
    speaker. ``speaker`` may be a plain name or an FF9 name tag like ``[ZDNE]`` / ``[VIVI]``."""
    return f"{speaker}{SPEAKER_SEP}{text}" if speaker else text


def mes_entry(text: str, txid: int, *, strt: tuple = (10, 1), tail: str = DEFAULT_TAIL) -> str:
    """One ``.mes`` entry line that ADDS dialogue at ``txid`` without touching base text."""
    strt_s = ",".join(str(v) for v in strt)
    return f"_[TXID={txid}][STRT={strt_s}][TAIL={tail}]{text}[ENDN]"


def build_mes(lines, *, start_txid: int = DEFAULT_BASE_TXID, tails=None) -> tuple[str, dict]:
    """Build a ``.mes`` file body from an ordered list of dialogue strings.

    Returns ``(text, mapping)`` where ``mapping[i]`` is the TXID assigned to ``lines[i]`` (so a
    caller can point each NPC's WindowSync at the right id). TXIDs are ``start_txid + i``.
    ``tails`` (optional) is a per-line list of TAIL codes; ``None``/missing entries use
    :data:`DEFAULT_TAIL`, so existing callers stay byte-identical.
    """
    entries = []
    mapping = {}
    for i, line in enumerate(lines):
        txid = start_txid + i
        mapping[i] = txid
        tail = (tails[i] if tails and i < len(tails) and tails[i] else DEFAULT_TAIL)
        entries.append(mes_entry(line, txid, tail=tail))
    return "\n".join(entries) + "\n", mapping
