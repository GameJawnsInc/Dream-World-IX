"""The PySide6-FREE half of the workspace: the QSS builder. No Qt, no display (like the editor's
headless tests). The Qt shell itself is exercised by `py apps/ff9_workspace.pyw --smoke` (offscreen)."""

from __future__ import annotations

from ff9mapkit.editor import theme
from ff9mapkit.workspace import style


def test_qss_renders_for_every_palette():
    # qss() is a Template.substitute over the palette -> a palette missing ANY $name key would raise here.
    for mode, pal in theme.THEMES.items():
        css = style.qss(pal)
        assert isinstance(css, str) and len(css) > 500, mode
        assert pal["accent"] in css and pal["bg"] in css and pal["text"] in css, mode
        assert "$" not in css, mode             # every placeholder substituted


def test_qss_leaves_no_unsubstituted_placeholders():
    css = style.qss(theme.DARK)
    assert "$" not in css                      # every $name was substituted from the palette


def test_qss_styles_the_core_widgets():
    css = style.qss(theme.LIGHT)
    for sel in ("QTreeWidget", "QTabBar::tab", "QPlainTextEdit", "QPushButton", "QScrollBar"):
        assert sel in css


def test_qss_carries_no_dock_rules():
    # The shell has no QDockWidget any more (the console is a collapsible splitter pane), so these
    # selectors are dead -- and QMainWindow::separator is what could paint a band across the window.
    css = style.qss(theme.DARK)
    for sel in ("QDockWidget", "QMainWindow::separator"):
        assert sel not in css


def test_qss_greys_a_disabled_accent_button():
    # a disabled accent button (Save with nothing to save) must override the #accent blue -- the id
    # selector out-ranks the generic :disabled rule, so it needs its own #accent:disabled.
    css = style.qss(theme.DARK)
    assert "QPushButton#accent:disabled" in css


def test_qss_specifies_checked_indicators():
    # once a stylesheet touches a QCheckBox/QRadioButton, Qt stops drawing the native checked dot -- so the
    # CHECKED indicator must be explicitly styled or the selected state renders invisible (the Import bug).
    css = style.qss(theme.DARK)
    assert "QRadioButton::indicator" in css and "QCheckBox::indicator" in css
    assert "::indicator:checked" in css


def test_qss_styles_dropdown_menus():
    # the toolbar Field/Campaign/Journey buttons open QMenus -- they must be themed (selected item = accent)
    css = style.qss(theme.DARK)
    assert "QMenu" in css and "QMenu::item:selected" in css
