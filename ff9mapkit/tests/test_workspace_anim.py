"""The Phase-10 motion module (workspace.anim): motion is OFF by default and always disable-able (WCAG
2.3.3), and every helper applies its END STATE synchronously when motion is off -- so the offscreen tests
+ the --smoke path (which never enable it) are never left mid-transition."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QWidget                            # noqa: E402

from ff9mapkit.workspace import anim                                          # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _no_motion_leak():
    # a test that turns motion ON must never leak it: the next test (or the shared app) would start real
    # animations that never finish under processEvents.
    yield
    anim.set_enabled(False)


def test_motion_is_off_by_default():
    anim.set_enabled(False)
    assert anim.enabled() is False


def test_configure_resolves_the_preference():
    anim.configure("on")
    assert anim.enabled() is True
    anim.configure("off")
    assert anim.enabled() is False
    anim.configure("auto")                              # follows the OS probe -> a bool either way
    assert isinstance(anim.enabled(), bool)
    anim.configure("garbage")                           # unknown -> treated as auto, never raises
    assert isinstance(anim.enabled(), bool)


def test_os_reduced_motion_is_a_safe_bool():
    assert isinstance(anim.os_reduced_motion(), bool)   # never raises on any platform


def test_disabled_helpers_apply_end_state_synchronously(app):
    anim.set_enabled(False)
    w = QWidget()
    w.setMaximumHeight(0)
    calls = []
    a = anim.animate_height(w, 0, 120, on_finished=lambda: calls.append(1))
    assert a is None, "no animation object when motion is off"
    assert w.maximumHeight() == 120, "the end height is applied immediately"
    assert calls == [1], "on_finished still runs synchronously (a collapse still ends hidden)"
    assert anim.pop_in(w) is None, "pop-in is a no-op when motion is off"


def test_enabled_animate_height_makes_a_bounded_animation(app):
    anim.set_enabled(True)
    w = QWidget()
    a = anim.animate_height(w, 0, 100, duration=150)
    assert a is not None
    assert a.duration() == 150 and a.duration() <= 200, "motion stays <=200ms (WCAG 2.3.3)"
    assert a.endValue() == 100
    a.stop()
    anim.set_enabled(False)


def test_no_helper_may_silently_destroy_an_existing_graphics_effect(app):
    """Qt allows ONE QGraphicsEffect per widget, so installing one DESTROYS whatever was there.

    `anim.fade_in` did exactly that. It had ZERO production callers, and the one widget anyone would
    plausibly fade -- the Ctrl-K palette card -- is the app's only `attach_shadow` caller. Verified via
    shiboken: after fade_in, the shadow's C++ object is `isValid() == False`. Not detached -- DESTROYED,
    with nothing to restore, and fade_in's own finish handler then sets the effect to None, leaving the
    widget with no effect at all. A dead helper that quietly deletes a live one is worse than no helper.

    So it is gone. This test is the headstone: any future opacity/blur helper must either refuse a widget
    that already has an effect, or restore it -- and it cannot, because the original is destroyed.
    """
    import inspect
    from ff9mapkit.workspace import anim as anim_mod

    src = inspect.getsource(anim_mod)
    assert "setGraphicsEffect" not in src, (
        "a helper installs a QGraphicsEffect -- that DESTROYS any effect the widget already had "
        "(shiboken: isValid() False), and there is no way to put it back"
    )
    assert not hasattr(anim_mod, "fade_in"), "fade_in was deleted: 0 callers, and it ate palette.py's shadow"


def test_disclosure_expand_collapse_end_states_with_motion_off(app):
    """The disclosure drawer animates its height, but with motion off it must reach the SAME end states as
    the old instant show/hide -- expand ends visible, collapse ends hidden (what the smoke asserts)."""
    from ff9mapkit.workspace.widgets import disclosure                        # noqa: PLC0415
    anim.set_enabled(False)
    box = disclosure("Advanced", expanded=False)
    body = box.content_layout.parentWidget()
    box.show()
    app.processEvents()
    assert not body.isVisible(), "collapsed by default"
    box.toggle_button.setChecked(True)
    app.processEvents()
    assert body.isVisible(), "motion off -> instant expand ends visible"
    box.toggle_button.setChecked(False)
    app.processEvents()
    assert not body.isVisible(), "motion off -> instant collapse ends hidden"


def test_busy_loading_state_shows_working_and_gates_the_bar(app):
    """A running job shows a 'Working…' loading state so a long build never reads as a frozen panel; the
    animated indeterminate bar is gated on motion (reduced-motion shows just the text)."""
    from ff9mapkit.editor.theme import pick_palette                          # noqa: PLC0415
    from ff9mapkit.workspace.shell import Workspace, _apply_app_theme        # noqa: PLC0415
    _apply_app_theme(app, pick_palette("dark"))
    w = Workspace(pick_palette("dark"))
    w.show()
    app.processEvents()
    anim.set_enabled(False)
    w._set_busy(True)
    assert w._busy_label.isVisible(), "the 'Working…' label shows during a job"
    assert not w._busy_bar.isVisible(), "reduced motion -> no animated bar, just the text"
    w._set_busy(False)
    assert not w._busy_label.isVisible(), "cleared when the job ends"
    anim.set_enabled(True)
    w._set_busy(True)
    assert w._busy_bar.isVisible(), "motion on -> the indeterminate bar shows too"
    anim.set_enabled(False)
    w.close()


def test_palette_pop_in_respects_the_motion_switch(app):
    """The Ctrl-K palette fades+rises in when motion is on, and opens at full opacity (never stranded at 0)
    when it's off -- the safety property that keeps the offscreen/smoke paths correct."""
    from PySide6.QtWidgets import QWidget                                     # noqa: PLC0415
    from ff9mapkit.editor.theme import pick_palette                          # noqa: PLC0415
    from ff9mapkit.workspace.palette import CommandPalette                   # noqa: PLC0415
    parent = QWidget()
    entries = [("Open Campaign", "command", lambda: None)]
    anim.set_enabled(False)
    p = CommandPalette(parent, entries, pick_palette("dark"))
    p.show()
    app.processEvents()
    assert p.windowOpacity() == 1.0, "motion off -> opens fully opaque"
    p.close()
    anim.set_enabled(True)
    p2 = CommandPalette(parent, entries, pick_palette("dark"))
    p2.show()
    app.processEvents()
    assert p2.windowOpacity() < 1.0, "motion on -> the fade-in has begun"
    anim.set_enabled(False)
    p2.close()
