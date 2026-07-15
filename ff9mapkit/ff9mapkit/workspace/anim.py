"""The workspace's ONE motion module (Phase 10 -- polish & motion).

A tiny, sanctioned set of ≤200ms transitions, all gated behind a single ``enabled()`` switch so motion is
**opt-in and always disable-able** (WCAG 2.3.3):

* **Default OFF.** Nothing animates until :func:`configure` (or :func:`set_enabled`) turns it on -- which the
  production entry point does after ``show()``. So the ``--smoke`` path and the offscreen tests (which never
  call it, and drive the UI with short ``processEvents`` bursts, not a running event loop) get **instant
  end-states**: every helper below applies its final value synchronously when motion is off, so a widget is
  never left stranded mid-transition.
* **Respects the OS + the user.** :func:`configure` resolves ``"auto"`` against the platform's reduce-motion
  setting (Windows ``SPI_GETCLIENTAREAANIMATION``); ``"on"`` / ``"off"`` force it. A Preferences toggle +
  a Ctrl-K command write the ``motion`` pref.
* **Bounded.** Durations are 120-160ms with a standard ease; there is no looping / auto-playing motion.

Keep new motion HERE (2-3 uses), not scattered across the docs -- that's the whole point of one module.
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation

_ENABLED = False                                   # opt-in; the production launch flips it on (see shell.main)
_EASE = QEasingCurve.Type.OutCubic                 # a calm decelerating ease for every transition
_DELETE_WHEN_STOPPED = QPropertyAnimation.DeletionPolicy.DeleteWhenStopped


def enabled() -> bool:
    """Is motion currently on? Every helper is a synchronous no-op-to-end-state when this is False."""
    return _ENABLED


def set_enabled(on: bool) -> None:
    global _ENABLED
    _ENABLED = bool(on)


def configure(pref: str = "auto") -> None:
    """Resolve a ``motion`` preference (``"on"`` / ``"off"`` / ``"auto"``) into the on/off switch. ``"auto"``
    follows the OS reduce-motion setting."""
    if pref == "on":
        set_enabled(True)
    elif pref == "off":
        set_enabled(False)
    else:                                           # "auto" (or anything unknown) -> follow the OS
        set_enabled(not os_reduced_motion())


def os_reduced_motion() -> bool:
    """True if the OS asks apps to minimise animation. Windows exposes SPI_GETCLIENTAREAANIMATION; elsewhere
    (or on any error) we assume motion is fine and let the in-app toggle decide. Never raises."""
    try:
        import ctypes                              # noqa: PLC0415 -- Windows-only, imported lazily

        val = ctypes.c_int()
        SPI_GETCLIENTAREAANIMATION = 0x1042
        if ctypes.windll.user32.SystemParametersInfoW(SPI_GETCLIENTAREAANIMATION, 0, ctypes.byref(val), 0):
            return val.value == 0                   # 0 == "animations off" -> reduced
    except Exception:                               # noqa: BLE001 -- non-Windows / no ctypes / probe failure
        pass
    return False


def pop_in(window, *, dy: int = 10, duration: int = 150):
    """A subtle fade + upward slide for a top-level overlay (the Ctrl-K palette): the window rises ``dy`` px
    into place as it fades in, using ``windowOpacity`` + ``pos`` (both real for a frameless dialog). No-op
    when motion is off -- the caller has already positioned + shown the window, so nothing else is needed."""
    if not _ENABLED:
        return None
    end = window.pos()
    window.setWindowOpacity(0.0)
    window.move(QPoint(end.x(), end.y() + dy))
    fade = QPropertyAnimation(window, b"windowOpacity", window)
    fade.setDuration(duration)
    fade.setStartValue(0.0)
    fade.setEndValue(1.0)
    fade.setEasingCurve(_EASE)
    slide = QPropertyAnimation(window, b"pos", window)
    slide.setDuration(duration)
    slide.setStartValue(QPoint(end.x(), end.y() + dy))
    slide.setEndValue(end)
    slide.setEasingCurve(_EASE)
    fade.start(_DELETE_WHEN_STOPPED)
    slide.start(_DELETE_WHEN_STOPPED)
    return fade, slide


def animate_height(widget, start: int, end: int, *, duration: int = 160, on_finished=None):
    """Animate ``widget``'s ``maximumHeight`` ``start`` -> ``end`` (an expand/collapse). When motion is off,
    the end height is applied immediately and ``on_finished`` runs synchronously -- so a collapse still ends
    hidden and an expand still ends full-height with no visible jump-frame. Returns the animation or None."""
    if not _ENABLED:
        widget.setMaximumHeight(end)
        if on_finished is not None:
            on_finished()
        return None
    a = QPropertyAnimation(widget, b"maximumHeight", widget)
    a.setDuration(duration)
    a.setStartValue(start)
    a.setEndValue(end)
    a.setEasingCurve(_EASE)
    if on_finished is not None:
        a.finished.connect(on_finished)
    a.start(_DELETE_WHEN_STOPPED)
    return a
