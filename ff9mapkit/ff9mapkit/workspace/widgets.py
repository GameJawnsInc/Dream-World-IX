"""Shared Qt widget helpers for the Workspace.

PySide6-only: the application-wide wheel guard (:class:`WheelGuard`) and the empty-state list
(:class:`PlaceholderListWidget`).
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QAbstractSpinBox, QApplication, QComboBox, QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel,
    QListWidget, QPushButton, QToolButton, QVBoxLayout, QWidget,
)

from . import anim

_QWIDGETSIZE_MAX = 16777215                        # Qt's max size -- 'release the height pin' so a widget tracks content

# The gap BETWEEN cards (see `section`). The card draws its own boundary, so this gap does not have to
# carry the grouping by itself -- but it must still clearly exceed the 8px gap between rows INSIDE a card,
# or the page reads as one undifferentiated stack. 14 sits between the old 10 and the borderless 24.
SECTION_GAP = 14


class WheelGuard(QObject):
    """App-wide event filter: ignore the mouse wheel on an UNFOCUSED combo / spin box.

    Qt's combos and spin boxes change their value on ``wheelEvent`` while merely HOVERED, so scrolling a
    tall panel silently flips whatever control the cursor passes over -- a genuine data hazard on the save
    editors (5 combos stacked in a scroll area) and a friction everywhere else. Installed once on the
    QApplication, a stray wheel over an unfocused control is dropped; the control only responds to the
    wheel once the user has clicked or tabbed INTO it. One install covers every combo -- present and
    future -- with no per-widget wiring.

    Deliberately guards only ``QComboBox`` / ``QAbstractSpinBox``: sliders and (crucially) scroll bars are
    ``QAbstractSlider``s that MUST keep their wheel, so they are left alone. Trade-off: a wheel directly
    over an unfocused combo is consumed (the panel won't scroll under that exact footprint) -- which is why
    the combos are also kept narrow; scroll in the surrounding space.
    """

    _GUARDED = (QComboBox, QAbstractSpinBox)

    def eventFilter(self, obj, ev):                # noqa: N802 (Qt override)
        if ev.type() == QEvent.Type.Wheel and isinstance(obj, self._GUARDED) and not obj.hasFocus():
            ev.ignore()
            return True
        return False


class PlaceholderListWidget(QListWidget):
    """A QListWidget that paints a muted hint while it is empty (the QLineEdit-placeholder idiom, which
    plain list views lack) -- so an empty Problems panel says what will appear there instead of sitting as
    a silent grey box. Set ``placeholder`` / ``placeholder_color`` (a '#rrggbb' string) any time; the
    shell's retheme updates the colour."""

    def __init__(self, placeholder="", color="#808080", parent=None):
        super().__init__(parent)
        self.placeholder = placeholder
        self.placeholder_color = color

    def paintEvent(self, ev):                      # noqa: N802 (Qt override)
        super().paintEvent(ev)
        if self.count() == 0 and self.placeholder:
            painter = QPainter(self.viewport())
            painter.setPen(QColor(self.placeholder_color))
            rect = self.viewport().rect().adjusted(12, 8, -12, -8)
            painter.drawText(rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
                             | Qt.TextFlag.TextWordWrap, self.placeholder)
            painter.end()


# --- component factories (Phase 1 token foundation) ----------------------------------------
# Thin QLabel/QFrame factories that stamp a dynamic `role` property (styled by the component QSS in
# workspace.style) and fold in an accessible name -- so a heading / caption / card / chip is ONE call
# with the a11y hook baked in, replacing the ad-hoc inline stylesheets adopted incrementally from Phase 2.

def role_label(text="", role="body", *, parent=None):
    """A QLabel carrying a ``role`` (display / h1 / h2 / caption / subtle / chip) for the component QSS,
    with its text as the accessible name."""
    lab = QLabel(text, parent)
    lab.setProperty("role", role)
    if text:
        lab.setAccessibleName(text)
    return lab


def heading(text, level=1, *, parent=None):
    """A titled label -- level 0 = display, 1 = h1, 2 = h2."""
    return role_label(text, "display" if level == 0 else f"h{level}", parent=parent)


def caption(text="", *, parent=None):
    """A small muted caption label (the 11px type role)."""
    return role_label(text, "caption", parent=parent)


def card(*, parent=None):
    """An elevated container frame (surface_2 + a rounded border) for grouped content."""
    frame = QFrame(parent)
    frame.setProperty("role", "card")
    return frame


# Max measure for a wrapped sentence, px. It caps a real problem: a full-window paragraph on a 1180px pane
# runs ~200 chars/line and reads as unformatted output rather than as text somebody wrote.
#
# HONEST RECEIPT (an earlier comment here claimed "~75-85 chars" -- that was simply wrong, and measured):
# real prose averages 5.691 px/char at 13px Segoe UI on a NATIVE font DB, so 620px is ~109 chars/line --
# ABOVE the classic 45-75ch band (which would be 256-427px). 620 is a deliberate compromise for a dense
# settings pane rather than a typographic ideal, and it is the value that was reviewed and approved on the
# Co-op tab. Narrowing it toward ~440 (~77ch) is an open design call, not a bug fix -- it re-wraps every
# adopted caption, so it wants a look before it lands.
# NB: measure this on the NATIVE platform only. QT_QPA_PLATFORM=offscreen stubs the font DB and inflates
# advances 2-3x, which is how the dossier invented a horizontal-scroll emergency that never existed.
PROSE_W = 620


class Prose(QLabel):
    """A word-wrapped label with a REAL measure cap.

    A raw ``setMaximumWidth`` on a wrapped QLabel silently CLIPS: ``QBoxLayout::calcHfw`` asks
    ``heightForWidth()`` at the full CELL width (say 900px -> "2 lines please"), then lays the label out at
    its capped 620px, where the text actually needs 4. The bottom two lines are cut off. Overriding
    ``heightForWidth`` to answer for the *capped* width -- never the cell's -- is what makes the cap honest.

    Do NOT "fix" this with an HBox + addStretch wrapper: that collapses the label to its sizeHint (its
    natural single-line width) and throws the measure away entirely.
    """

    def __init__(self, text="", width=PROSE_W, parent=None):
        super().__init__(text, parent)
        self._cap = width
        self.setWordWrap(True)
        self.setMaximumWidth(width)

    def heightForWidth(self, w):                   # noqa: N802 (Qt override)
        return super().heightForWidth(min(w, self._cap))

    def sizeHint(self):                            # noqa: N802 (Qt override)
        s = super().sizeHint()
        s.setWidth(min(s.width(), self._cap))
        s.setHeight(self.heightForWidth(self._cap))
        return s


def prose(text, width=PROSE_W, *, parent=None):
    """A wrapped sentence held to a readable measure (see :class:`Prose`)."""
    return Prose(text, width, parent)


def section(title, *, parent=None):
    """A titled CARD -- the QGroupBox replacement.

    The card stays: it is a genuinely useful logical section indicator, and the measurements say the box
    was never the problem. What was ugly is specific and fixable:

    1. **The caption sat ON the border**, breaking the stroke around itself -- the Win32 ``fieldset``
       idiom every modern design language dropped. It is also the one thing QSS cannot fix: ``font-*`` on
       ``QGroupBox::title`` is silently ignored (colour is its only lever), so the title could never be
       given weight while Qt was drawing it. Hence a real QLabel, INSIDE the card, at the top.
    2. **The title had no presence** -- ``$muted`` at the same 13px as the body it labelled. Now the
       11px/600/+1px-tracking overline role, which reads as a marker rather than as weak body text.
    3. **No horizontal padding** (``style.py``: "NB: no left/right padding") -- content ran to the edge.
       That amputation was defending against an h-scroll bug that never existed at the claimed magnitude
       (the offscreen QPA inflates text advances 2-3x; the widest real control is 642px against ~1080px
       of pane). Padding restored.

    NOT changed: the fill. ``surface_2`` on ``bg`` measures 1.31 in DARK -- a *stronger* step than
    GitHub's dark card (1.09). The elevation was fine; the research's "the fills do nothing" measured
    ``surface -> surface_2`` (1.17), which is not the pair a card on a page is seen against.

    Call shape mirrors :func:`disclosure` (the established idiom here)::

        st = widgets.section("Status")      # was: st = QGroupBox("Status")
        sv = st.content_layout              # was: sv = QVBoxLayout(st)
        sv.addWidget(...)                   # unchanged
        v.addWidget(st)                     # unchanged

    The title is upper-cased at the call site because Qt has no ``text-transform``.

    **Pair every adoption with a name.** Qt derives an unnamed control's screen-reader name from its
    enclosing QGroupBox TITLE; a card has no title for it to find, so any control that was leaning on the
    box goes silent. Give each one a ``setBuddy(label)`` (better names than the box gave anyway).
    """
    box = QFrame(parent)
    box.setProperty("role", "card")                  # $surface_2 + $radius_lg + a 1px $border edge
    v = QVBoxLayout(box)
    v.setContentsMargins(16, 12, 16, 16)             # the padding the fieldset never had
    v.setSpacing(10)                                 # title -> its rows
    lab = role_label(title.upper(), "overline")
    lab.setAccessibleName(title)                     # announce the real title, not the shouty form
    v.addWidget(lab)
    # The content host is a LAYOUT, never a wrapper QWidget. The stylesheet opens with a universal
    # `QWidget { background-color: $bg; }`, so a bare QWidget in here paints the PAGE colour on top of the
    # card's fill -- a visible darker rectangle inside every card, i.e. the exact box-in-box this is meant
    # to kill. It hides on a borderless section (bg on bg) and only surfaces once the card has a fill.
    body_lay = QVBoxLayout()
    body_lay.setContentsMargins(0, 0, 0, 0)
    body_lay.setSpacing(8)
    v.addLayout(body_lay)
    box.content_layout = body_lay
    box.title_label = lab
    return box


def status_chip(text, kind="info", *, parent=None):
    """A small pill label. ``kind`` (info / good / warn / crit) is stamped as a property for later
    per-kind tinting; the accessible name names the kind, so status never rides on colour alone."""
    lab = role_label(text, "chip", parent=parent)
    lab.setProperty("kind", kind)
    if text:
        lab.setAccessibleName(f"{kind}: {text}")
    return lab


def empty_state(glyph, purpose, *, teach=None, actions=(), parent=None, icon_pixmap=None):
    """A centered TEACHING empty-state -- the antidote to a black void / a bare "nothing loaded" panel:
    a large decorative icon/glyph, a one-line purpose, an optional teaching sentence, and optional
    primary-action button(s). ``actions`` is an iterable of ``(label, callback)`` (falsy entries are
    skipped, so a caller can gate one on availability); the first surviving action is accented as the
    primary. ``icon_pixmap`` (Phase 8) shows an SVG icon instead of the text ``glyph``; either way the
    mark is decorative (no accessible name) -- the purpose + teach lines carry the meaning for a screen
    reader. Returns a QWidget ready to drop into any empty host layout."""
    w = QWidget(parent)
    v = QVBoxLayout(w)
    v.setContentsMargins(24, 24, 24, 24)
    v.setSpacing(8)
    v.addStretch(1)
    g = role_label("", "empty_glyph") if icon_pixmap is not None else role_label(glyph, "empty_glyph")
    if icon_pixmap is not None:
        g.setPixmap(icon_pixmap)
    g.setAlignment(Qt.AlignmentFlag.AlignCenter)
    g.setAccessibleName("")                             # decorative -- don't announce the glyph/icon
    v.addWidget(g)
    p = role_label(purpose, "empty_title")
    p.setAlignment(Qt.AlignmentFlag.AlignCenter)
    p.setWordWrap(True)
    v.addWidget(p)
    if teach:
        t = caption(teach)
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setWordWrap(True)
        t.setMinimumWidth(380)                          # a word-wrapped label between stretches collapses to
        t.setMaximumWidth(460)                          # its hint width -- pin a readable measure (~2 lines)
        trow = QHBoxLayout()
        trow.addStretch(1)
        trow.addWidget(t)
        trow.addStretch(1)
        v.addLayout(trow)
    acts = [a for a in actions if a]
    if acts:
        brow = QHBoxLayout()
        brow.addStretch(1)
        for i, (label, cb) in enumerate(acts):
            b = QPushButton(label)
            if i == 0:                                  # the first action is the primary -> accented
                b.setObjectName("accent")
            if cb is not None:
                b.clicked.connect(lambda _=False, c=cb: c())
            brow.addWidget(b)
        brow.addStretch(1)
        v.addLayout(brow)
    v.addStretch(1)
    return w


def attach_shadow(widget, *, blur=32, dy=8, alpha=110):
    """Give a FLOATING layer (a Ctrl-K palette card, a frameless popover) real depth via a
    QGraphicsDropShadowEffect. Apply to a ROUNDED card that sits inside a transparent, margined host so the
    blur has room to spill and the rounded corners don't bleed a hard rectangle (Report F-§2). No-op-safe:
    returns the widget. Not for native top-level menus/dialogs -- those already get an OS shadow on Windows."""
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(blur)
    eff.setXOffset(0)
    eff.setYOffset(dy)
    eff.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(eff)
    return widget


def disclosure(title, *, expanded=False, parent=None):
    """A collapsible 'advanced' section (progressive disclosure): a flat toggle header (▸/▾ + ``title``) over
    a hidden-by-default content area. The caller fills ``box.content_layout``; ``box.toggle_button`` is the
    header. Reusable for the Import secondary jobs + the Build advanced drawer -- keeps the routine path front
    and centre while the power-user controls stay one click away."""
    box = QWidget(parent)
    v = QVBoxLayout(box)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(0)
    btn = QToolButton()
    btn.setObjectName("disclosureToggle")
    btn.setCheckable(True)
    btn.setChecked(expanded)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setText(("▾  " if expanded else "▸  ") + title)
    btn.setAccessibleName(title)
    body = QWidget()
    body_lay = QVBoxLayout(body)
    body_lay.setContentsMargins(2, 6, 0, 0)
    body_lay.setSpacing(8)
    body.setVisible(expanded)

    def _toggle(on):
        btn.setText(("▾  " if on else "▸  ") + title)
        if on:                                          # expand: reveal, then grow 0 -> content height,
            body.setVisible(True)                       # then release the pin so it tracks content again
            target = max(body.sizeHint().height(), 1)
            anim.animate_height(body, 0, target, on_finished=lambda: body.setMaximumHeight(_QWIDGETSIZE_MAX))
        else:                                           # collapse: shrink current -> 0, THEN hide
            anim.animate_height(body, body.height(), 0, on_finished=lambda: body.setVisible(False))
    btn.toggled.connect(_toggle)
    v.addWidget(btn)
    v.addWidget(body)
    box.content_layout = body_lay
    box.toggle_button = btn
    return box


def repolish(widget):
    """Re-evaluate ``widget``'s QSS after a dynamic property (role / state / kind) changed -- Qt does NOT
    restyle automatically on a setProperty. Cheap; call it right after flipping a selector-affecting
    property (e.g. a form hint toggling state='error')."""
    st = widget.style()
    st.unpolish(widget)
    st.polish(widget)
    widget.update()


def tabular(widget):
    """Turn ON tabular (fixed-width) figures on ``widget``'s font so ids / coordinates / byte offsets line
    up in columns. Uses the Qt 6.7+ font-feature API; a silent no-op on older Qt. Returns the widget."""
    try:
        font = widget.font()
        font.setFeature(QFont.Tag("tnum"), 1)
        widget.setFont(font)
    except Exception:       # noqa: BLE001  (older Qt lacks setFeature/Tag -> skip, non-fatal)
        pass
    return widget


def install_wheel_guard(app=None):
    """Install the shared :class:`WheelGuard` on the running QApplication (idempotent; parented to the app
    so it outlives every widget). No-op returning ``None`` if there is no QApplication yet."""
    app = app or QApplication.instance()
    if app is None:
        return None
    guard = app.findChild(WheelGuard)              # already installed (e.g. a second window)? reuse it
    if guard is None:
        guard = WheelGuard(app)
        app.installEventFilter(guard)
    return guard
