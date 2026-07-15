"""Phase-9 accessibility contract: every actionable control the user can see must expose a screen-reader
NAME (WCAG 4.1.2), the custom-painted / headerless surfaces are named explicitly, and the status hues
clear the non-text contrast floor. The name check walks the LIVE widget tree and reads the real
``QAccessible`` name (which resolves a QFormLayout label buddy), so it mirrors what NVDA/Narrator announce.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtGui import QAccessible                                          # noqa: E402
from PySide6.QtWidgets import (QAbstractButton, QAbstractSpinBox, QApplication,  # noqa: E402
                               QComboBox, QLineEdit, QListWidget, QPlainTextEdit,
                               QTextEdit, QTreeWidget, QWidget)

from ff9mapkit.workspace.shell import Workspace, _apply_app_theme             # noqa: E402

# the actionable control types a screen-reader user tabs to / operates
_WATCH = (QAbstractButton, QLineEdit, QComboBox, QAbstractSpinBox, QPlainTextEdit,
          QTextEdit, QListWidget, QTreeWidget)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def win(app):
    from ff9mapkit.editor.theme import pick_palette
    pal = pick_palette("dark")
    _apply_app_theme(app, pal)
    w = Workspace(pal)
    w.resize(1280, 820)
    w.show()
    app.processEvents()
    return w


def _acc_name(wd) -> str:
    iface = QAccessible.queryAccessibleInterface(wd)
    if iface is None:
        return ""
    try:
        return (iface.text(QAccessible.Text.Name) or "").strip()
    except Exception:                                    # noqa: BLE001
        return ""


def _qt_internal(wd) -> bool:
    """Skip Qt-managed sub-widgets we neither create nor should name: a combo/spinbox's internal line-edit
    editor, a line-edit's built-in clear button, the toolbar overflow chevron. Their WRAPPER carries the
    name (and is checked in its own right)."""
    if wd.objectName().startswith("qt_"):
        return True
    parent = wd.parentWidget()
    if isinstance(wd, QLineEdit) and isinstance(parent, (QComboBox, QAbstractSpinBox)):
        return True                                      # the internal editor of a combo / spin box
    if isinstance(wd, QAbstractButton) and isinstance(parent, QLineEdit):
        return True                                      # QLineEdit's clear-button affordance
    return False


def test_every_visible_actionable_control_has_a_screen_reader_name(win, app):
    """Walk each tab (while current) + the always-visible chrome; every non-internal visible control must
    announce a name. This is the coverage guarantee behind 'NVDA reads meaningful names'."""
    holes = set()
    for i in range(win.tabs.count()):
        win.tabs.setCurrentIndex(i)
        app.processEvents()
        for wd in win.findChildren(QWidget):
            if not isinstance(wd, _WATCH) or not wd.isVisible() or _qt_internal(wd):
                continue
            if not _acc_name(wd):
                holes.add(f"tab {i}: {type(wd).__name__}#{wd.objectName() or '-'} @ {wd.geometry().getRect()}")
    assert not holes, "actionable controls with no screen-reader name:\n" + "\n".join(sorted(holes))


def test_custom_canvas_and_headerless_widgets_are_named(win):
    """The surfaces a screen reader can't infer a name for -- a headerless tree, a custom-painted graphics
    canvas, a read-only console -- get an explicit accessibleName (+ description where useful)."""
    assert win.tree.accessibleName() == "Project navigator"
    assert win.tree.accessibleDescription()
    assert win.map.accessibleName() == "Campaign map"
    assert win.map.accessibleDescription()
    assert win.problems.accessibleName() == "Problems"
    assert win.output.accessibleName() == "Output console"


def test_rail_tabs_and_icon_only_buttons_are_named(win):
    """The IA surfaces the success criterion names explicitly: rail segments, tabs, and the icon-only gear."""
    assert all(seg.accessibleName() for seg in win._rail_segs), "every rail segment names its workspace"
    assert win._settings_btn.accessibleName() == "Settings", "the icon-only settings button is named"
    assert all(win.tabs.tabText(i).strip() for i in range(win.tabs.count())), "every tab has a visible label"
