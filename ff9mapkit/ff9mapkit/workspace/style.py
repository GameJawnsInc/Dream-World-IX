"""A Qt Style Sheet (QSS) for the workspace shell, generated from a theme palette.

PySide6-FREE -- a pure ``str``-building function over a palette dict, so it's unit-testable on a headless
machine (the same discipline as :mod:`..editor.theme`, whose ``LIGHT``/``DARK`` palettes this consumes).
QSS uses ``{`` / ``}`` heavily, so the template uses ``string.Template``'s ``$name`` placeholders (which
leave braces alone) rather than ``str.format``.
"""

from __future__ import annotations

from string import Template

# Every $name below must be a key in the palette (editor.theme LIGHT/DARK provide them all).
_QSS = Template(
    """
    * { outline: 0; }
    QWidget { background-color: $bg; color: $text; font-family: "Segoe UI"; font-size: 13px; }
    QMainWindow::separator { background: $border; width: 1px; height: 1px; }

    /* Toolbar metrics are deliberately COMPACT (spacing 6 / button padding 10): every action plus the
       search pill and the gear menu must FIT at the default 1280px window -- overflowing items land in
       Qt's hidden extension chevron, which is how the Ctrl-K search and Preferences went invisible. */
    QToolBar { background: $surface; border: 0; border-bottom: 1px solid $border; padding: 5px 8px; spacing: 6px; }
    QToolBar::separator { background: $border; width: 1px; margin: 5px 4px; }
    QToolButton, QPushButton {
        background: $surface_btn; color: $text; border: 1px solid $border;
        border-radius: 6px; padding: 6px 10px;
    }
    QToolButton:hover, QPushButton:hover { background: $hover; }
    QPushButton:pressed, QToolButton:pressed { background: $pressed; }
    QPushButton:disabled { color: $muted; background: $bg; }
    /* a disabled toolbar action recedes to flat ghost text (it used to look identical to enabled) */
    QToolButton:disabled { color: $muted; background: transparent; border-color: transparent; }
    /* dropdown tool-buttons (Field / Campaign / Journey / gear): keep the chevron inside the rounded
       border, vertically centred (the default bottom-right corner position clips against the radius) */
    QToolButton[popupMode="2"] { padding-right: 20px; }
    QToolButton::menu-indicator {
        subcontrol-origin: padding; subcontrol-position: center right; right: 5px;
    }
    /* the gear (settings) menu: icon-only -- no chevron, compact padding */
    QToolButton#gear { padding: 6px 9px; }
    QToolButton#gear::menu-indicator { image: none; width: 0; }
    /* the Ctrl-K palette opener is a button DRESSED as a search field */
    QPushButton#search {
        background: $field; color: $muted; border: 1px solid $border; border-radius: 7px;
        padding: 6px 12px; text-align: left;
    }
    QPushButton#search:hover { border-color: $accent; color: $text; background: $field; }
    QPushButton#accent { background: $accent; color: $accent_fg; border: 1px solid $accent; }
    QPushButton#accent:hover { background: $accent_hover; }
    QPushButton#accent:pressed { background: $accent_pressed; }
    /* a disabled accent button (e.g. Save with nothing to save) must grey out -- the #accent id
       selector otherwise out-ranks the generic :disabled rule and would stay blue. */
    QPushButton#accent:disabled { background: $surface_btn; color: $muted; border: 1px solid $border; }

    /* Indicators MUST be fully specified: once a stylesheet touches a QCheckBox/QRadioButton, Qt stops
       drawing the native checked dot, so without this the selected state renders INVISIBLE. */
    QCheckBox, QRadioButton { background: transparent; spacing: 7px; }
    QCheckBox::indicator, QRadioButton::indicator {
        width: 15px; height: 15px; border: 1px solid $border; background: $field;
    }
    QRadioButton::indicator { border-radius: 8px; }
    QCheckBox::indicator { border-radius: 4px; }
    QCheckBox::indicator:hover, QRadioButton::indicator:hover { border: 1px solid $accent; }
    QCheckBox::indicator:checked, QRadioButton::indicator:checked {
        background: $accent; border: 1px solid $accent;
    }
    QCheckBox::indicator:disabled, QRadioButton::indicator:disabled { border: 1px solid $muted; background: $bg; }

    QLineEdit {
        background: $field; color: $text; border: 1px solid $border; border-radius: 6px;
        padding: 6px 9px; selection-background-color: $accent; selection-color: $accent_fg;
    }
    QLineEdit:focus { border: 1px solid $accent; }

    /* combos + spin boxes: themed like line edits (the Fusion base style would otherwise draw them from
       the platform palette, which need not match the chosen theme) */
    QComboBox, QAbstractSpinBox {
        background: $field; color: $text; border: 1px solid $border; border-radius: 6px;
        padding: 4px 8px; selection-background-color: $accent; selection-color: $accent_fg;
    }
    QComboBox:focus, QAbstractSpinBox:focus { border: 1px solid $accent; }
    QComboBox:disabled, QAbstractSpinBox:disabled { color: $muted; background: $bg; }
    QComboBox QAbstractItemView {
        background: $surface; color: $text; border: 1px solid $border;
        selection-background-color: $accent; selection-color: $accent_fg;
    }

    QTreeWidget, QTreeView, QListWidget {
        background: $surface; border: 1px solid $border; border-radius: 8px; padding: 4px;
    }
    QTreeView::item, QListWidget::item { padding: 5px 4px; border-radius: 4px; }
    QTreeView::item:hover, QListWidget::item:hover { background: $hover; }
    QTreeView::item:selected, QListWidget::item:selected { background: $accent; color: $accent_fg; }
    QHeaderView::section { background: $surface_btn; color: $muted; border: 0; padding: 5px; }

    QTabWidget::pane { border: 1px solid $border; border-radius: 8px; top: -1px; }
    QTabBar::tab {
        background: $surface_btn; color: $muted; padding: 7px 16px; border: 1px solid $border;
        border-bottom: 2px solid transparent; border-top-left-radius: 6px; border-top-right-radius: 6px;
        margin-right: 2px;
    }
    QTabBar::tab:selected { background: $bg; color: $text; border-bottom: 2px solid $accent; }
    QTabBar::tab:hover { color: $text; }

    /* boxed form sections (Build & Deploy / Import): a quiet rounded outline with a floating caption */
    QGroupBox {
        border: 1px solid $border; border-radius: 8px; margin-top: 10px; padding-top: 8px;
    }
    QGroupBox::title {
        subcontrol-origin: margin; left: 10px; padding: 0 5px;
        color: $muted; font-weight: 600; background: $bg;
    }

    QPlainTextEdit, QTextEdit {
        background: $log_bg; color: $log_fg; border: 1px solid $border; border-radius: 8px;
        font-family: "Cascadia Code", "Consolas", monospace; font-size: 12px; padding: 6px;
    }

    /* dropdown menus (the toolbar Field / Campaign / Journey buttons) */
    QMenu { background: $surface; border: 1px solid $border; border-radius: 6px; padding: 4px; }
    QMenu::item { padding: 6px 22px; border-radius: 4px; }
    QMenu::item:selected { background: $accent; color: $accent_fg; }
    QMenu::separator { height: 1px; background: $border; margin: 4px 6px; }

    QDockWidget { color: $muted; }
    QDockWidget::title { background: $surface; padding: 6px 9px; border-bottom: 1px solid $border; }

    QScrollBar:vertical { background: $bg; width: 12px; margin: 0; }
    QScrollBar::handle:vertical { background: $scroll; border-radius: 5px; min-height: 28px; }
    QScrollBar:horizontal { background: $bg; height: 12px; margin: 0; }
    QScrollBar::handle:horizontal { background: $scroll; border-radius: 5px; min-width: 28px; }
    QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
    QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

    QSplitter::handle { background: $border; }
    QSplitter::handle:horizontal { width: 1px; }
    QSplitter::handle:vertical { height: 1px; }
    QLabel { background: transparent; }
    QStatusBar { background: $surface; color: $muted; border-top: 1px solid $border; }
    QStatusBar::item { border: none; }
    QToolTip { background: $surface; color: $text; border: 1px solid $border; }

    /* Home-page entry cards */
    QFrame#card { background: $surface; border: 1px solid $border; border-radius: 10px; }
    """
)


def qss(palette: dict) -> str:
    """Render the workspace stylesheet for ``palette`` (an :mod:`..editor.theme` LIGHT/DARK dict)."""
    return _QSS.substitute(palette)
