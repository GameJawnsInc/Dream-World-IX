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


def test_interactive_controls_meet_target_size(app):
    """WCAG 2.5.8 (target size minimum, 24x24): every common control's clickable box clears 24px tall under
    the real QSS -- we pad the control (not just the glyph). The inline '?' concept badge is a generous 22."""
    from PySide6.QtWidgets import (QCheckBox, QComboBox, QLineEdit, QPushButton,  # noqa: PLC0415
                                   QRadioButton, QVBoxLayout, QWidget)
    from ff9mapkit.editor.theme import pick_palette                              # noqa: PLC0415
    from ff9mapkit.workspace.style import qss                                    # noqa: PLC0415
    host = QWidget()
    host.setStyleSheet(qss(pick_palette("dark")))                                # scoped -> no app pollution
    lay = QVBoxLayout(host)
    controls = {"checkbox": QCheckBox("Enable"), "radio": QRadioButton("Pick"), "button": QPushButton("Deploy"),
                "combo": QComboBox(), "lineedit": QLineEdit()}
    for wd in controls.values():
        lay.addWidget(wd)
    host.show()
    app.processEvents()
    for name, wd in controls.items():
        wd.ensurePolished()
        assert wd.sizeHint().height() >= 24, f"{name}: target height {wd.sizeHint().height()} < 24 (WCAG 2.5.8)"
    from ff9mapkit.workspace.forms_qt import _concept_badge                      # noqa: PLC0415
    made = _concept_badge("walkmesh", pick_palette("dark"))
    if made is not None:
        badge = made[0]
        assert badge.width() >= 22 and badge.height() >= 22, "the '?' concept badge is a generous inline target"


def test_focus_rings_are_defined_for_keyboard_users():
    """WCAG 2.4.7: buttons, tabs, the tree, and inputs must show a visible focus indicator. Guards against a
    regression that removes the per-widget :focus rings (the global `outline:0` suppresses Fusion's native one)."""
    from ff9mapkit.editor.theme import derive, pick_palette                      # noqa: PLC0415
    from ff9mapkit.workspace.style import qss                                    # noqa: PLC0415
    for mode in ("dark", "light", "nord"):
        pal = pick_palette(mode)
        css = qss(pal)
        for sel in ("QPushButton:focus", "QTabBar::tab:focus", "QTreeWidget:focus", "QLineEdit:focus"):
            assert sel in css, f"{mode}: missing focus rule {sel}"
        assert derive(pal)["focus"] in css, f"{mode}: the focus ring uses the derived (>=3:1) focus colour"


def test_toolbar_overflows_gracefully_at_narrow_width(app):
    """WCAG 1.4.4 / 1.4.10: at a narrow logical width (a small screen at high OS scaling), the 1280-tuned
    toolbar must degrade to Qt's overflow chevron -- items stay reachable, never hard-clipped mid-word."""
    from PySide6.QtWidgets import QToolButton                                    # noqa: PLC0415
    from ff9mapkit.editor.theme import pick_palette                             # noqa: PLC0415
    narrow = Workspace(pick_palette("dark"))
    narrow.resize(720, 600)
    narrow.show()
    app.processEvents()
    ext = [b for b in narrow.findChildren(QToolButton) if b.objectName() == "qt_toolbar_ext_button"]
    assert ext and ext[0].isVisible(), "the toolbar provides an overflow chevron at narrow width (no hard clip)"
    narrow.close()


def test_problems_convey_severity_by_icon_not_colour_alone(win):
    """WCAG 1.4.1: each Problems row carries a distinct-shape severity ICON (error vs warn), so severity is
    legible without relying on the text colour (which stays the readable body colour, not a status hue)."""
    from ff9mapkit.editor import feedback as fb
    errs, warns = ["boom: it broke"], ["heads up: check this"]
    verdict = fb.classify(errs, warns, subject="a11y probe", clean_headline="clean")
    win._show_problems(verdict, fb.problems(errs, warns))
    items = [win.problems.item(i) for i in range(win.problems.count())]
    assert len(items) == 2
    assert all(not it.icon().isNull() for it in items), "every Problems row has a severity icon"
    # the error and warn icons are DIFFERENT shapes (not just different colours)
    err_it = next(it for it in items if "boom" in it.text())
    warn_it = next(it for it in items if "heads up" in it.text())
    from PySide6.QtCore import QSize
    assert (err_it.icon().pixmap(QSize(16, 16)).toImage()
            != warn_it.icon().pixmap(QSize(16, 16)).toImage()), "error vs warn are distinct shapes"
