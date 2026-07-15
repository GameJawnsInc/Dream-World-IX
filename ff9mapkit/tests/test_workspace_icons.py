"""The Phase-8 SVG icon family (workspace.icons): every drawing renders to a non-null tinted pixmap,
the tint actually takes, results are cached, and the unsaved-dot composite preserves size — plus a
parity guard that every name the shell wires up exists in the set."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication            # noqa: E402

from ff9mapkit.workspace import icons                 # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


# The names the shell/rail/docs wire up. If a wiring site typos a name, this list keeps the test
# honest (the icon would silently KeyError at render otherwise).
REQUIRED = {
    "journey", "campaign", "field", "hub", "bare", "save", "battle",       # tree/Home types
    "chocobo", "pin",                                                       # the two former emoji
    "search", "settings", "rocket", "chevron-right", "plus", "minus",       # toolbar/chrome
    "home", "author", "assets", "state", "download",                        # rail groups (+ ship=rocket)
}


def test_every_icon_renders_non_null(app):
    for name in icons.names():
        for size in (12, 16, 20, 24):
            pm = icons.pixmap(name, "#c7ccd6", size)
            assert not pm.isNull(), (name, size)
            assert pm.width() > 0 and pm.height() > 0


def test_required_names_all_exist(app):
    missing = REQUIRED - set(icons.names())
    assert not missing, f"icon family is missing wired names: {sorted(missing)}"


def test_tint_actually_changes_the_pixels(app):
    a = icons.pixmap("field", "#ffffff", 24).toImage()
    b = icons.pixmap("field", "#ff0000", 24).toImage()
    assert a != b, "recolouring the icon produced identical pixels — the tint didn't take"


def test_pixmaps_are_cached_by_key(app):
    p1 = icons.pixmap("rocket", "#7aa2f7", 16)
    p2 = icons.pixmap("rocket", "#7aa2f7", 16)
    assert p1 is p2                                    # same (name,color,size,dpr) -> same object
    p3 = icons.pixmap("rocket", "#7aa2f7", 20)
    assert p3 is not p1                                # a different size is a different entry


def test_icon_helper_returns_a_populated_qicon(app):
    ic = icons.icon("save", "#c7ccd6", 16)
    assert not ic.isNull()
    assert not ic.availableSizes() == []               # has at least one pixmap


def test_corner_dot_preserves_size_and_alters_pixels(app):
    base = icons.pixmap("field", "#c7ccd6", 24)
    dotted = icons.with_corner_dot(base, "#e0af68")
    assert dotted.size() == base.size()
    assert dotted.toImage() != base.toImage()          # the status dot is visibly composited
    assert dotted.devicePixelRatio() == base.devicePixelRatio()


def test_clear_cache_forces_rerender(app):
    p1 = icons.pixmap("hub", "#c7ccd6", 16)
    icons.clear_cache()
    p2 = icons.pixmap("hub", "#c7ccd6", 16)
    assert p1 is not p2                                 # cache was dropped -> a fresh pixmap
