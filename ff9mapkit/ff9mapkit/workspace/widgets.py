"""Shared Qt widget helpers for the Workspace.

PySide6-only: the application-wide wheel guard (:class:`WheelGuard`) and the empty-state list
(:class:`PlaceholderListWidget`).
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QAbstractSpinBox, QApplication, QComboBox, QFrame, QHBoxLayout, QLabel, QListWidget, QPushButton,
    QVBoxLayout, QWidget,
)


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


def status_chip(text, kind="info", *, parent=None):
    """A small pill label. ``kind`` (info / good / warn / crit) is stamped as a property for later
    per-kind tinting; the accessible name names the kind, so status never rides on colour alone."""
    lab = role_label(text, "chip", parent=parent)
    lab.setProperty("kind", kind)
    if text:
        lab.setAccessibleName(f"{kind}: {text}")
    return lab


def empty_state(glyph, purpose, *, teach=None, actions=(), parent=None):
    """A centered TEACHING empty-state -- the antidote to a black void / a bare "nothing loaded" panel:
    a large muted glyph, a one-line purpose, an optional teaching sentence, and optional primary-action
    button(s). ``actions`` is an iterable of ``(label, callback)`` (falsy entries are skipped, so a caller
    can gate one on availability); the first surviving action is accented as the primary. The glyph is
    decorative (no accessible name) -- the purpose + teach lines carry the meaning for a screen reader.
    Returns a QWidget ready to drop into any empty host layout."""
    w = QWidget(parent)
    v = QVBoxLayout(w)
    v.setContentsMargins(24, 24, 24, 24)
    v.setSpacing(8)
    v.addStretch(1)
    g = role_label(glyph, "empty_glyph")
    g.setAlignment(Qt.AlignmentFlag.AlignCenter)
    g.setAccessibleName("")                             # decorative -- don't announce the glyph char
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
