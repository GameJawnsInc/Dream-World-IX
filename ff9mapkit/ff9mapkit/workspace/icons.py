"""The monochrome SVG icon family (Phase 8 — iconography).

A small, self-authored ("dwix") icon set drawn in the Lucide idiom: a 24×24 viewBox,
2px round-capped / round-joined strokes, geometric shapes. It is authored here (not
vendored) on purpose:

* **Zero license/attribution burden** — nothing is copied from an external set, so there
  is no third-party notice to ship or path data to keep in sync.
* **Guaranteed-correct geometry** — the shapes are primitives we control, not coordinates
  transcribed from a font/atlas that could drift or mis-copy.
* **Every criterion the icon question (Q5) asked for** — a *real* vector set that tints
  uniformly from the theme tokens, stays crisp at any DPI, and survives high-contrast mode,
  rather than the ASCII/unicode/emoji glyphs it replaces.

**Rendering.** Each entry is the inner SVG markup; the family is drawn ``fill="none"
stroke="currentColor"`` (2px round) with individual *filled* shapes overriding to
``fill="currentColor" stroke="none"``. The literal token ``currentColor`` is substituted
with the requested hex before the markup reaches :class:`QSvgRenderer` (QtSvg does not
resolve ``currentColor`` itself), so one source drawing paints in any token colour. The
result is painted onto a device-pixel-ratio-aware :class:`QPixmap` and cached per
``(name, hex, px, dpr)`` — a tree of hundreds of rows shares a handful of pixmaps, and a
live theme switch simply renders a fresh set under the new colours.

The module is import-safe without a running ``QApplication`` (the render functions need
one, like any Qt pixmap work, but importing/enumerating the set does not).
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

_VIEW = 24  # the shared viewBox all drawings use

# name -> inner SVG markup. Outlines inherit the root stroke; filled shapes opt in with
# fill="currentColor" stroke="none". Keep every drawing inside the 24×24 box with ~2u of
# optical padding so nothing clips when scaled down to 12–16px.
_ICONS: dict[str, str] = {
    # ---- domain TYPES (tree nodes / Home rows / breadcrumb) ----
    # journey — the whole arc / the front door: a start flag.
    "journey": '<path d="M6 21V4"/><path d="M6 4h11l-2 4 2 4H6"/>',
    # campaign — a connected chain of fields: stacked layers.
    "campaign": '<path d="M12 3l9 5-9 5-9-5 9-5z"/><path d="M3 13l9 5 9-5"/>',
    # field — one pre-rendered screen: a framed picture.
    "field": '<rect x="3" y="4" width="18" height="16" rx="2"/>'
             '<circle cx="8.5" cy="9.5" r="1.6"/><path d="M21 15l-5-4-8 6"/>',
    # hub — the World-Hub / journeys root: a grid of slots.
    "hub": '<rect x="3" y="3" width="7" height="7" rx="1.3"/>'
           '<rect x="14" y="3" width="7" height="7" rx="1.3"/>'
           '<rect x="3" y="14" width="7" height="7" rx="1.3"/>'
           '<rect x="14" y="14" width="7" height="7" rx="1.3"/>',
    # bare — a single-field journey leaf (warps straight to a field): a target.
    "bare": '<circle cx="12" cy="12" r="8"/>'
            '<circle cx="12" cy="12" r="2.4" fill="currentColor" stroke="none"/>',
    # save — a game save file: a floppy disk.
    "save": '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>'
            '<path d="M17 21v-8H7v8"/><path d="M7 3v5h7"/>',
    # battle — a referenced fight scene: a shield.
    "battle": '<path d="M12 3l7 3v5c0 4.2-3 7.4-7 9-4-1.6-7-4.8-7-9V6l7-3z"/>',
    # object — a generic thing inside a field (NPC / gateway / marker): a neutral rounded node.
    "object": '<rect x="5" y="5" width="14" height="14" rx="3.5"/>',
    # script — the verbatim .eb logic subtree: a lined document.
    "script": '<rect x="5" y="3" width="14" height="18" rx="2"/>'
              '<path d="M9 8h6M9 12h6M9 16h3"/>',
    # ---- extra domain glyphs ----
    # chocobo — the Hot & Cold minigame (was a color emoji): a feather.
    "chocobo": '<path d="M20 4C11 4 6 9 6 15v3l-2 2"/><path d="M16 8L4 20"/><path d="M17 15H9"/>',
    # a Blender-placed spatial object (was a color pin emoji): a map pin.
    "pin": '<path d="M12 21s7-6.3 7-11a7 7 0 1 0-14 0c0 4.7 7 11 7 11z"/>'
           '<circle cx="12" cy="10" r="2.4"/>',
    # ---- toolbar / chrome ----
    "search": '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.35-4.35"/>',
    # settings / preferences: three sliders.
    "settings": '<path d="M4 7h16"/><path d="M4 12h16"/><path d="M4 17h16"/>'
                '<circle cx="8" cy="7" r="2.3" fill="currentColor" stroke="none"/>'
                '<circle cx="16" cy="12" r="2.3" fill="currentColor" stroke="none"/>'
                '<circle cx="10" cy="17" r="2.3" fill="currentColor" stroke="none"/>',
    # deploy / ship: a rocket.
    "rocket": '<path d="M12 3c3 2.2 5 5.8 5 9.5L14.5 15h-5L7 12.5C7 8.8 9 5.2 12 3z"/>'
              '<circle cx="12" cy="10" r="1.6" fill="currentColor" stroke="none"/>'
              '<path d="M9.5 15L7.5 20l3-1.4M14.5 15l2 5-3-1.4"/>',
    # status marks -- DISTINCT SHAPES (not colour-alone): error=circle-x, warn=triangle-!, ok=circle-check,
    # info=circle-i, so severity is legible in greyscale / to a colour-blind user (WCAG 1.4.1).
    "alert-error": '<circle cx="12" cy="12" r="9"/><path d="M15 9l-6 6M9 9l6 6"/>',
    "alert-warn": '<path d="M12 3.5l9 15.5H3z"/><path d="M12 9.5v4.5"/><path d="M12 17.2v.3"/>',
    "alert-ok": '<circle cx="12" cy="12" r="9"/><path d="M8 12.4l2.6 2.6L16 9.2"/>',
    "alert-info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5.2"/><path d="M12 7.8v.3"/>',
    # a job is running (the busy crumb-Deploy button wears this, muted): an hourglass.
    "hourglass": '<path d="M6 3h12"/><path d="M6 21h12"/>'
                 '<path d="M8 3v3l4 6 4-6V3"/><path d="M8 21v-3l4-6 4 6v3"/>',
    "chevron-right": '<path d="M9 6l6 6-6 6"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "minus": '<path d="M5 12h14"/>',
    # ---- workspace RAIL groups ----
    "home": '<path d="M3 11l9-8 9 8"/><path d="M5 9.4V20h14V9.4"/>',
    # author (Editor / Map): a pencil.
    "author": '<path d="M4 20l1-4L16 5l3 3L8 19l-4 1z"/><path d="M14 7l3 3"/>',
    # assets (Import / Models / Battle): a package.
    "assets": '<path d="M21 8l-9-5-9 5v8l9 5 9-5V8z"/><path d="M3.3 7.5l8.7 5 8.7-5"/>'
              '<path d="M12 12.5V21"/><path d="M7.5 4.5l9 5"/>',
    # state (Story State / Item & Equip — the save layer): a database.
    "state": '<ellipse cx="12" cy="5.5" rx="8" ry="3"/>'
             '<path d="M4 5.5v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>'
             '<path d="M4 11.5v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
    # ship (Build & Deploy / Co-op) reuses the rocket, so the Ship rail and the Deploy
    # button wear the same glyph — the eye connects "Ship workspace" with "Deploy".
    "download": '<path d="M12 4v11"/><path d="M7 10l5 5 5-5"/><path d="M5 20h14"/>',
    # The transport family (the Behavior tab's tick-stepper) — SVG, never the unicode
    # media glyphs: U+23F1/U+23F8 fall back to the Windows EMOJI face and render as
    # dark colour blobs (snap-caught on the sim strip's timer readout).
    "play": '<path d="M8 5.5l11 6.5-11 6.5V5.5z"/>',
    "pause": '<path d="M8 5v14"/><path d="M16 5v14"/>',
    "reset": '<path d="M5.5 9A8 8 0 1 1 4 13"/><path d="M5.5 4v5H10"/>',
}


def names() -> list[str]:
    """Every icon name in the family (used by the parity test)."""
    return sorted(_ICONS)


def _svg_bytes(name: str, hex_color: str) -> bytes:
    body = _ICONS[name]
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_VIEW} {_VIEW}" '
        f'fill="none" stroke="currentColor" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    )
    return svg.replace("currentColor", hex_color).encode("utf-8")


def _dpr() -> float:
    app = QApplication.instance()
    scr = app.primaryScreen() if app is not None else None
    try:
        return float(scr.devicePixelRatio()) if scr is not None else 1.0
    except Exception:  # noqa: BLE001 -- a headless/offscreen probe must never raise
        return 1.0


_PIX_CACHE: dict[tuple, QPixmap] = {}


def pixmap(name: str, color: str, size: int = 16) -> QPixmap:
    """Render ``name`` tinted ``color`` (``#rrggbb``) at a logical ``size`` px, crisp for
    the current screen's device pixel ratio. Cached; safe to call per row."""
    dpr = _dpr()
    key = (name, color.lower(), size, dpr)
    cached = _PIX_CACHE.get(key)
    if cached is not None:
        return cached
    phys = max(1, round(size * dpr))
    img = QImage(phys, phys, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    renderer = QSvgRenderer(_svg_bytes(name, color))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer.render(p)
    p.end()
    pm = QPixmap.fromImage(img)
    pm.setDevicePixelRatio(dpr)
    _PIX_CACHE[key] = pm
    return pm


def icon(name: str, color: str, size: int = 16) -> QIcon:
    """A :class:`QIcon` of ``name`` tinted ``color`` at ``size`` px."""
    return QIcon(pixmap(name, color, size))


_DOT_K = 0.19          # the dot's radius as a fraction of the icon's logical width
_DOT_PAD = 1.0         # the transparent halo around it, so it reads ON the glyph rather than IN it


def with_corner_dot(base: QPixmap, dot_color: str) -> QPixmap:
    """Return a copy of ``base`` with a small filled status dot in the bottom-right corner
    (a transparent halo keeps it legible over the glyph). Used to fold the tree's unsaved-changes
    indicator onto a type icon without stealing the icon slot.

    KEYLINE. This was `r = w * 0.30` with an `int()`-truncated 1px halo, and it did not annotate the glyph
    -- it ATE it. At w=16 the dot plus its halo spanned 11.6px of a 16px icon: **72% of the icon's width**,
    punched out of the bottom-right corner. `field` became an amber blob with a fragment of a frame
    attached; `hub` lost two of its four squares; `chocobo`'s feather was bisected. On the row you are
    editing -- the indicator destroyed the identity of the thing it was reporting on.

    0.19 puts the dot at 6.1px across at w=16 and keeps the glyph readable underneath it.

    THE `int()` IS NOT A ROUNDING DETAIL, IT IS THE BUG'S OTHER HALF. `int(cx - r - 1)` truncates toward
    zero on the origin and `int((r + 1) * 2)` truncates the extent, so the halo lost up to a pixel on each
    side and landed asymmetrically -- and at 0.19 the pad is the whole margin, so truncation would eat it
    outright. QRectF keeps the sub-pixel geometry the antialiaser needs, and is what makes the halo a
    clean 1px ring at w=16 AND w=24 at any dpr rather than a ragged edge that happens to look fine at one.

    ONLY THE RENDER CAUGHT THIS, and it is worth knowing why the obvious measurement cannot: the punch-out
    CLEARS and the dot then FILLS, so every destroyed pixel comes back with alpha 255. An "is this pixel
    still ink?" test therefore counts the amber dot as surviving glyph and reports 98% kept. Ask what
    COLOUR survived, or look at it at 10x. (evidence/keyline_dot_before.png / _after.png.)
    """
    pm = QPixmap(base.size())
    pm.setDevicePixelRatio(base.devicePixelRatio())
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.drawPixmap(0, 0, base)
    w = base.width() / base.devicePixelRatio()
    r = w * _DOT_K
    cx = cy = w - r
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(0, 0, 0, 0))     # transparent punch-out ring so the dot reads on any glyph
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
    p.drawEllipse(QRectF(cx - r - _DOT_PAD, cy - r - _DOT_PAD,
                         (r + _DOT_PAD) * 2, (r + _DOT_PAD) * 2))
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
    p.setBrush(QColor(dot_color))
    p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))
    p.end()
    return pm


def clear_cache() -> None:
    """Drop the pixmap cache (e.g. if a DPI change should force a re-render). Retint on a
    theme switch does not need this — a new colour is simply a new cache key."""
    _PIX_CACHE.clear()
