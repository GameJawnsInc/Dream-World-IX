"""The PySide6-FREE half of the workspace: the QSS builder. No Qt, no display (like the editor's
headless tests). The Qt shell itself is exercised by `py apps/ff9_workspace.pyw --smoke` (offscreen)."""

from __future__ import annotations

from ff9mapkit.editor import theme
from ff9mapkit.workspace import style


def test_qss_renders_for_both_palettes():
    for pal in (theme.LIGHT, theme.DARK):
        css = style.qss(pal)
        assert isinstance(css, str) and len(css) > 500
        assert pal["accent"] in css and pal["bg"] in css and pal["text"] in css


def test_qss_leaves_no_unsubstituted_placeholders():
    css = style.qss(theme.DARK)
    assert "$" not in css                      # every $name was substituted from the palette


def test_qss_styles_the_core_widgets():
    css = style.qss(theme.LIGHT)
    for sel in ("QTreeWidget", "QTabBar::tab", "QPlainTextEdit", "QPushButton", "QScrollBar"):
        assert sel in css


def test_qss_specifies_checked_indicators():
    # once a stylesheet touches a QCheckBox/QRadioButton, Qt stops drawing the native checked dot -- so the
    # CHECKED indicator must be explicitly styled or the selected state renders invisible (the Import bug).
    css = style.qss(theme.DARK)
    assert "QRadioButton::indicator" in css and "QCheckBox::indicator" in css
    assert "::indicator:checked" in css
