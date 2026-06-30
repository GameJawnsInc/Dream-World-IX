"""Shared Qt widget helpers for the Workspace.

PySide6-only. The one thing here today is the application-wide wheel guard -- see :class:`WheelGuard`.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QAbstractSpinBox, QApplication, QComboBox


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
