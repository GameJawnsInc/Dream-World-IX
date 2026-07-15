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
    assert anim.fade_in(w) is None, "fade is a no-op when motion is off"
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


def test_enabled_fade_in_returns_an_animation(app):
    anim.set_enabled(True)
    w = QWidget()
    a = anim.fade_in(w, duration=140)
    assert a is not None and a.duration() <= 200
    a.stop()
    anim.set_enabled(False)


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
