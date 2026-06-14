"""Suppress a BG-borrowed field's inherited AREA-TITLE overlays -- the big "Ice Cavern" / "Mognet Central"
card.

The title is a range of scene OVERLAYS (indices from :mod:`ff9mapkit.areatitle`). In the real game the
DONOR field's own ``.eb`` owns the title's whole lifecycle: ``Main_Init`` hides the overlays at load, and a
*scenario-gated* block later shows + fades them (and, on a transition field, warps onward). A ``--verbatim``
fork carries that script byte-for-byte, so a forked field replays the stock show+fade on its own when the
journey seeds the trigger scenario -- the kit does NOT script the title for forks (doing so would double
the card and re-fire the donor's warp).

The gap this module fills is the OTHER case: a SYNTHESIZED field that BG-borrows an area-title room (the
World Hub borrows Mognet Central's room) inherits those overlays Active-by-default, with no donor ``.eb`` to
retire them -- so the title sits there statically claiming to be that place. :func:`hide` prepends
``ShowTile(i, 0)`` for the title overlays to ``Main_Init`` (entry-0 tag-0) so it never shows. A tag-0
prepend (``rel_off == 0``) is shift-safe even on jump-table donors; the injection is language-identical
and no-ops when the field has no area title. Mirrors :mod:`ff9mapkit.content.entry_settle`.
"""

from __future__ import annotations

from ..eb import edit, opcodes

SHOWTILE = 0x5B          # ShowTile / BGLACTIVE: ShowTile(overlayIdx, active) -- active 0 = hide, 1 = show


def hide(eb_bytes, start, end) -> bytes:
    """Prepend ``ShowTile(i, 0)`` for every overlay ``i`` in ``[start, end]`` to Main_Init (entry-0 tag-0)
    so the area-title overlays are suppressed from the first frame. Returns the input unchanged when the
    field has no title range (``start``/``end`` is ``None``). ``.eb``-language-identical (call once)."""
    if start is None or end is None:
        return eb_bytes
    ovr = list(range(int(start), int(end) + 1))
    if not ovr:
        return eb_bytes
    body = b"".join(opcodes.encode(SHOWTILE, i, 0) for i in ovr)
    return edit.insert_in_function(eb_bytes, 0, 0, 0, body)
