"""Control a forked / BG-borrowed field's AREA-TITLE overlays -- the big "Ice Cavern" / "Mognet Central"
card shown on entry.

The title is a range of scene OVERLAYS (indices from :mod:`ff9mapkit.areatitle`); the DONOR field's own
``.eb`` scripts the show+fade on entry (scenario-gated). A fork or BG-borrow that doesn't carry/trigger
that script leaves the overlays in their default (active) state, so the title sits there STATICALLY. This
module injects the missing lifecycle into the field's ``Main_Init`` (entry-0 tag-0), ungated.

Mirrors :mod:`ff9mapkit.content.entry_settle`: a thin, language-identical Main_Init prepend that no-ops
when the field has no area title. A tag-0 prepend (``rel_off == 0``) is shift-safe even on jump-table
donors (:func:`ff9mapkit.eb.edit.insert_in_function`).

``hide`` (autohide) is the World-Hub case: a synthesized field that borrows an area-title room but
shouldn't claim to be that place -> hide the title from frame 1. ``fade`` (the fork-fidelity default --
show then fade out) is built on top once the autohide path is in-game proven.
"""

from __future__ import annotations

from ..eb import edit, opcodes

SHOWTILE = 0x5B          # ShowTile / BGLACTIVE: ShowTile(overlayIdx, active) -- active 0 = hide, 1 = show
SETTILECOLOR = 0x59      # SetTileColor: SetTileColor(overlayIdx, r, g, b) -- the per-overlay tint (fade lever)


def _overlays(start, end) -> "list[int]":
    if start is None or end is None:
        return []
    return list(range(int(start), int(end) + 1))


def hide(eb_bytes, start, end) -> bytes:
    """Prepend ``ShowTile(i, 0)`` for every overlay ``i`` in ``[start, end]`` to Main_Init (entry-0 tag-0)
    so the area-title overlays are suppressed from the first frame. Returns the input unchanged when the
    field has no title range (``start``/``end`` is ``None``). ``.eb``-language-identical (call once)."""
    ovr = _overlays(start, end)
    if not ovr:
        return eb_bytes
    body = b"".join(opcodes.encode(SHOWTILE, i, 0) for i in ovr)
    return edit.insert_in_function(eb_bytes, 0, 0, 0, body)


def apply(eb_bytes, start, end, *, mode: str = "hide") -> bytes:
    """Dispatch on ``mode``. ``"hide"`` = autohide (implemented). ``"fade"`` = show-then-fade (the fork
    default) -- reserved; falls back to a no-op for now so callers can wire it ahead of the fade path."""
    if mode == "hide":
        return hide(eb_bytes, start, end)
    return eb_bytes      # "fade" path lands next (after the autohide is in-game proven)
