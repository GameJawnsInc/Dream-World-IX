"""Shared Qt widget helpers for the Workspace.

PySide6-only: the application-wide wheel guard (:class:`WheelGuard`) and the empty-state list
(:class:`PlaceholderListWidget`).
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QAbstractSpinBox, QApplication, QComboBox, QListWidget


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
