"""A Qt Style Sheet (QSS) for the workspace shell, generated from a theme palette.

PySide6-FREE -- a ``str``-building function over a palette dict, so it's unit-testable on a headless
machine (the same discipline as :mod:`..editor.theme`, whose ``LIGHT``/``DARK`` palettes this consumes).
QSS uses ``{`` / ``}`` heavily, so the template uses ``string.Template``'s ``$name`` placeholders (which
leave braces alone) rather than ``str.format``.

One side effect, and the reason it is not *quite* pure: the checkbox tick is an SVG on disk. QSS cannot
draw a checkmark -- it has no ``transform`` (so the two-borders-rotated-45deg CSS trick is out), no
``::before``/content, and Qt has no ``text-transform``. ``image: url(...)`` is the only lever, and it needs
a real file. So :func:`qss` writes a per-tint SVG into a temp cache and substitutes its path. Writing a
text file needs no Qt, so the headless-testability property that matters is preserved.
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from string import Template

from ..editor.theme import derive

# --- indicator art ---------------------------------------------------------------------------
# A checked checkbox used to be a solid accent square and a checked radio a solid accent circle -- they
# differed ONLY by corner radius, so "pick several" and "pick exactly one" looked identical, and a filled
# swatch reads as a colour chip rather than as "checked". The radio's dot is pure QSS (a radial gradient);
# the tick has to be an image (see the module docstring).

_CHECK_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" fill="none" '
    'stroke="{color}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M3.5 8.4l3.1 3.1 5.9-6.4"/></svg>'
)


def _asset(name: str, text: str) -> str:
    """Write ``text`` to a content-addressed file in a temp cache and return a QSS-safe path.

    Content-addressed on purpose: a tint is a new FILENAME, never a rewrite of an existing one. Qt caches
    images by path, so overwriting ``check.svg`` on a theme switch would keep serving the stale pixmap.
    """
    cache = Path(tempfile.gettempdir()) / "ff9mapkit-qss"
    cache.mkdir(parents=True, exist_ok=True)
    dest = cache / f"{name}-{hashlib.sha1(text.encode('utf-8')).hexdigest()[:10]}.svg"
    if not dest.exists():                          # cheap: one write per distinct tint, ever
        dest.write_text(text, encoding="utf-8")
    return dest.as_posix()                         # QSS url() wants forward slashes, even on Windows

# Theme-independent scales threaded into the QSS template (and, in later phases, into Qt layout calls).
# Values are px strings so they substitute straight in. Spacing is a 4px grid; type is the modern ramp.
_SCALES = {
    "space_1": "4px", "space_2": "8px", "space_3": "12px", "space_4": "16px", "space_6": "24px",
    "radius_sm": "4px", "radius_md": "6px", "radius_lg": "8px",
    "type_display": "24px", "type_h1": "20px", "type_h2": "16px",
    "type_label": "13px", "type_body": "13px", "type_caption": "11px", "type_mono": "12px",
}

# UI density -- two profiles for the control paddings/spacings that set how tight the app reads. Comfortable
# (the default) matches the proven layout, with one deliberate "more whitespace" nudge: roomier tree/list
# rows. Compact tightens throughout for a power user who wants more on screen. NB: Comfortable keeps the
# toolbar + button padding as-is so the toolbar still FITS at 1280px (its hard constraint); the whitespace
# gains live in the content surfaces (rows), and Compact only ever shrinks.
_DENSITY = {
    "comfortable": {
        "tb_pad": "5px 8px", "tb_space": "6px", "btn_pad": "6px 10px",
        "input_pad": "6px 9px", "combo_pad": "4px 8px", "row_pad": "6px 8px",
        "tab_pad": "7px 16px", "gb_margin_top": "12px", "gb_pad_top": "10px", "menu_pad": "6px 22px",
    },
    "compact": {
        "tb_pad": "3px 6px", "tb_space": "4px", "btn_pad": "4px 8px",
        "input_pad": "4px 7px", "combo_pad": "3px 7px", "row_pad": "3px 4px",
        "tab_pad": "5px 12px", "gb_margin_top": "10px", "gb_pad_top": "8px", "menu_pad": "5px 16px",
    },
}

# Every $name below must be a key in the palette (editor.theme LIGHT/DARK provide them all).
_QSS = Template(
    """
    * { outline: 0; }
    QWidget { background-color: $bg; color: $text; font-family: "Segoe UI"; font-size: 13px; }

    /* Toolbar metrics are deliberately COMPACT (spacing 6 / button padding 10): every action plus the
       search pill and the gear menu must FIT at the default 1280px window -- overflowing items land in
       Qt's hidden extension chevron, which is how the Ctrl-K search and Preferences went invisible. */
    QToolBar { background: $surface; border: 0; border-bottom: 1px solid $border; padding: $tb_pad; spacing: $tb_space; }
    QToolBar::separator { background: $border; width: 1px; margin: 5px 4px; }
    QToolButton, QPushButton {
        background: $surface_btn; color: $text; border: 1px solid $border;
        border-radius: 6px; padding: $btn_pad;
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
    /* The primary needs its OWN focus ring. `QPushButton#accent` (specificity 0,1,0,1) out-ranks the
       generic `QPushButton:focus` (0,0,1,1) -- exactly the trap the :disabled rule above documents -- so
       every accent button in the app had NO focus indication at all, including the crumb-row Deploy F9,
       the primary action of the whole application. Measured: 0 px changed on focus, before this rule.
       $accent_fg, not $focus: $focus == $accent in 6 of 7 palettes, so a $focus ring on an $accent fill
       would be invisible. */
    QPushButton#accent:focus { border: 1px solid $accent_fg; }

    /* Indicators MUST be fully specified: once a stylesheet touches a QCheckBox/QRadioButton, Qt stops
       drawing the native checked dot, so without this the selected state renders INVISIBLE. */
    /* padding 3px lifts the clickable row to a >=24px target height (WCAG 2.5.8); the indicator itself is
       18px so it's a comfortable tap/hit -- we pad the control, not just the glyph. */
    QCheckBox, QRadioButton { background: transparent; spacing: 8px; padding: 3px 2px; }
    QCheckBox::indicator, QRadioButton::indicator {
        width: 18px; height: 18px; border: 1px solid $border; background: $field;
    }
    QRadioButton::indicator { border-radius: 9px; }
    QCheckBox::indicator { border-radius: 4px; }
    QCheckBox::indicator:hover, QRadioButton::indicator:hover { border: 1px solid $accent; }
    /* CHECKED must say WHICH KIND of control this is. A bare `background: $accent` (what shipped) made a
       checked checkbox a solid square and a checked radio a solid circle -- identical but for the corner
       radius, so pick-several and pick-exactly-one looked the same, and a filled swatch reads as a colour
       chip, not as "checked". The tick and the dot are the whole signal; restore both. */
    QCheckBox::indicator:checked { background: $accent; border: 1px solid $accent; image: url($check_img); }
    /* The radio's dot is pure QSS -- no asset. The gradient radius is a fraction of the 18px indicator, so
       stop 0.40 => a ~7px dot, the classic proportion. Keep the two stops adjacent (0.40 -> 0.46) or the
       dot fades into the fill instead of reading as a disc. */
    QRadioButton::indicator:checked {
        border: 1px solid $accent;
        background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
                    stop:0 $accent_fg, stop:0.40 $accent_fg, stop:0.46 $accent, stop:1 $accent);
    }
    QCheckBox::indicator:disabled, QRadioButton::indicator:disabled { border: 1px solid $muted; background: $bg; }
    /* A disabled+checked control still has to show WHAT it is set to (it is state, not decoration) -- but
       in $muted, so it reads as unavailable rather than active. Specificity 0x31 out-ranks :checked's 0x21. */
    QCheckBox::indicator:checked:disabled {
        background: $bg; border: 1px solid $muted; image: url($check_img_off);
    }
    QRadioButton::indicator:checked:disabled {
        border: 1px solid $muted;
        background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
                    stop:0 $muted, stop:0.40 $muted, stop:0.46 $bg, stop:1 $bg);
    }

    QLineEdit {
        background: $field; color: $text; border: 1px solid $border; border-radius: 6px;
        padding: $input_pad; selection-background-color: $accent; selection-color: $accent_fg;
    }
    QLineEdit:focus { border: 1px solid $accent; }

    /* combos + spin boxes: themed like line edits (the Fusion base style would otherwise draw them from
       the platform palette, which need not match the chosen theme) */
    QComboBox, QAbstractSpinBox {
        background: $field; color: $text; border: 1px solid $border; border-radius: 6px;
        padding: $combo_pad; selection-background-color: $accent; selection-color: $accent_fg;
    }
    QComboBox:focus, QAbstractSpinBox:focus { border: 1px solid $accent; }
    QComboBox:disabled, QAbstractSpinBox:disabled { color: $muted; background: $bg; }
    QComboBox QAbstractItemView {
        background: $surface; color: $text; border: 1px solid $border;
        selection-background-color: $accent; selection-color: $accent_fg;
    }

    /* Visible keyboard focus (WCAG 2.4.7). The global `outline: 0` at the top suppresses Fusion's
       inconsistent native focus rectangle; these rules give every interactive control ONE deliberate
       accent ring instead. No 1px->2px reflow -- the resting border is already 1px, `:focus` only
       recolours it to the accent (inputs already do this above). */
    QPushButton:focus, QToolButton:focus, QPushButton#search:focus { border: 1px solid $focus; }
    QTabBar::tab:focus { border-color: $focus; color: $text; }
    QTreeWidget:focus, QTreeView:focus, QListWidget:focus { border: 1px solid $focus; }
    /* NB: pseudo-ELEMENT before pseudo-CLASS -- `::indicator:focus`, NEVER `:focus::indicator`. Qt does
       not reject the wrong order: `Selector::pseudoElement()` reads the FIRST pseudo, sees the known class
       `focus`, and returns ""; `pseudoClass()` then returns 0 on the unknown `indicator`, so the match test
       `(0 & state) == 0` is true in EVERY state. The rule silently degenerates to an unconditional
       `QRadioButton, QCheckBox { border: 1px solid $focus; }` -- which shipped, and boxed every radio and
       checkbox in the app in a permanent accent rect while giving them NO focus ring at all.
       test_qss_has_no_malformed_subcontrol_selectors now guards the whole class of typo. */
    QCheckBox::indicator:focus, QRadioButton::indicator:focus { border: 1px solid $focus; }
    /* A CHECKED indicator is already filled $accent, and $focus == $accent in 6 of 7 palettes, so the rule
       above would be invisible exactly when a radio is clicked or arrowed into. $accent_fg is the one token
       guaranteed legible ON $accent. Specificity (0x31 > 0x21) wins this, not source order. */
    QCheckBox::indicator:checked:focus, QRadioButton::indicator:checked:focus { border: 1px solid $accent_fg; }

    QTreeWidget, QTreeView, QListWidget {
        background: $surface; border: 1px solid $border; border-radius: 8px; padding: 4px;
    }
    QTreeView::item, QListWidget::item { padding: $row_pad; border-radius: 4px; }
    QTreeView::item:hover, QListWidget::item:hover { background: $hover; }
    QTreeView::item:selected, QListWidget::item:selected { background: $accent; color: $accent_fg; }
    QHeaderView::section { background: $surface_btn; color: $muted; border: 0; padding: 5px; }

    QTabWidget::pane { border: 1px solid $border; border-radius: 8px; top: -1px; }
    QTabBar::tab {
        background: $surface_btn; color: $muted; padding: $tab_pad; border: 1px solid $border;
        border-bottom: 2px solid transparent; border-top-left-radius: 6px; border-top-right-radius: 6px;
        margin-right: 2px;
    }
    QTabBar::tab:selected { background: $bg; color: $text; border-bottom: 2px solid $accent; }
    QTabBar::tab:hover { color: $text; }

    /* boxed form sections (Build & Deploy / Import): a RAISED panel (elevation ladder -- surface_2 on the
       page bg reads as lifted) with a floating caption. The title bg matches the panel so it cuts the
       border cleanly. Roomier padding gives the dense docs' content air. */
    QGroupBox {
        background: $surface_2; border: 1px solid $border; border-radius: 8px;
        margin-top: $gb_margin_top; padding-top: $gb_pad_top;
    }
    /* NB: no left/right padding -- a long, non-wrapping QRadioButton label (Build & Deploy's New-Game
       radio) would overflow into a horizontal scroll. Content is inset by its own layout margins. */
    QGroupBox::title {
        subcontrol-origin: margin; left: 10px; padding: 0 6px;
        color: $muted; font-weight: 600; background: $surface_2;
    }

    QPlainTextEdit, QTextEdit {
        background: $log_bg; color: $log_fg; border: 1px solid $border; border-radius: 8px;
        font-family: "Cascadia Code", "Consolas", monospace; font-size: $type_mono; padding: 6px;
    }

    /* dropdown menus (the toolbar Field / Campaign / Journey buttons) */
    QMenu { background: $surface; border: 1px solid $border; border-radius: 6px; padding: 4px; }
    QMenu::item { padding: $menu_pad; border-radius: 4px; }
    QMenu::item:selected { background: $accent; color: $accent_fg; }
    QMenu::separator { height: 1px; background: $border; margin: 4px 6px; }

    QScrollBar:vertical { background: $bg; width: 12px; margin: 0; }
    QScrollBar::handle:vertical { background: $scroll; border-radius: 5px; min-height: 28px; }
    QScrollBar:horizontal { background: $bg; height: 12px; margin: 0; }
    QScrollBar::handle:horizontal { background: $scroll; border-radius: 5px; min-width: 28px; }
    QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
    QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

    /* the slim 'Working…' busy bar in the console header (indeterminate while a job runs) */
    QProgressBar { background: $surface_btn; border: 1px solid $border; border-radius: 3px; }
    QProgressBar::chunk { background: $accent; border-radius: 3px; }

    QSplitter::handle { background: $border; }
    QSplitter::handle:horizontal { width: 1px; }
    QSplitter::handle:vertical { height: 1px; }
    QLabel { background: transparent; }
    QStatusBar { background: $surface; color: $muted; border-top: 1px solid $border; }
    QStatusBar::item { border: none; }
    QToolTip { background: $surface; color: $text; border: 1px solid $border; }

    /* Home-page entry cards */
    QFrame#card { background: $surface; border: 1px solid $border; border-radius: 10px; }

    /* --- component roles (Phase 1 substrate) -- these match ONLY widgets that set a dynamic `role`
       property (via workspace.widgets factories), so they are INERT until Phase 2 adopts them. They give
       the modern type ramp, elevation ladder, and chip a single named home instead of ad-hoc inline CSS. */
    QLabel[role="display"] { font-size: $type_display; font-weight: 700; color: $text; }
    QLabel[role="h1"]      { font-size: $type_h1; font-weight: 600; color: $text; }
    QLabel[role="h2"]      { font-size: $type_h2; font-weight: 600; color: $text; }
    QLabel[role="label"]   { font-weight: 500; }
    QLabel[role="muted"]   { color: $muted; }                 /* secondary text, unchanged size */
    QLabel[role="accent"]  { color: $accent; }                /* an actionable value (e.g. a deploy target) */
    /* TEXT gets the derived *_text rung (AA 4.5 on the card fill); SHAPES below keep the canonical hue,
       where the 3.0 non-text floor is the right bar. Lifting the hues themselves was measured and
       rejected -- it needs +38% toward white on nord's and solarized's reds, washing them out. */
    QLabel[role="ok"]      { color: $success_text; }          /* a done/healthy status mark (e.g. a ✓) */
    QLabel[role="muted"][state="warn"]  { color: $warn_text; } /* a status line that turns cautionary */
    QLabel[role="caption"] { font-size: $type_caption; color: $muted; }
    /* A state on a plain (roleless) value label -- e.g. a definition-list value that IS the answer to
       "why is this broken" ("netsync MISSING"). The role-scoped rules above carry more attributes and so
       out-rank this, which is what we want: a muted hint keeps its own warn tint. Never demote a
       diagnostic to 11px grey -- demote the EXPLANATION, never the answer. */
    QLabel[state="warn"]  { color: $warn_text; }
    QLabel[state="error"] { color: $error_text; }
    QLabel[role="caption"][state="error"] { color: $error_text; } /* a live parse error turns the hint red */
    QLabel[role="caption"][state="warn"]  { color: $warn_text; } /* a soft warning (e.g. text may overflow) */
    QLabel[role="subtle"]  { color: $text_subtle; }
    /* teaching empty-states (workspace.widgets.empty_state): a large decorative glyph + a title, over the
       caption teaching line + optional action buttons -- replaces black-void / bare 'nothing loaded' panels */
    QLabel[role="empty_glyph"] { font-size: 34px; color: $text_subtle; }
    QLabel[role="empty_title"] { font-size: $type_h2; font-weight: 600; color: $text; }
    QFrame[role="card"] { background: $surface_2; border: 1px solid $border; border-radius: $radius_lg; }
    /* THE MONO REGISTER. This app's whole subject is machine tokens -- 4003, 30110, ff9-XXXXXXXX,
       FF9CustomMap, C:/.../FF9CustomMap. Set in the body face they read as prose and the eye slides off
       them; set in mono they read as things you copy, and it is the one real texture in the composition.
       FAMILY ONLY -- no font-size, so it inherits 13px and neither row heights nor 24px hit targets move.
       An orthogonal `mono` property, NOT a role= value: role is single-valued across ~111 call sites, so
       role="id" on a label would silently drop its existing role="muted".
       Cascadia ships with VS / Windows Terminal, NOT with Windows -- on a clean machine this falls to
       Consolas, which is fine. The register is the win, not the letterforms. Do not bundle a font. */
    QLabel[mono="true"], QLineEdit[mono="true"] {
        font-family: "Cascadia Code", "Consolas", monospace;
    }

    QLabel[role="chip"] {
        background: $surface_3; border: 1px solid $border; border-radius: $radius_sm;
        padding: 2px $space_2; color: $muted; font-size: $type_caption;
    }

    /* --- shell.py chrome roles (Phase 2, file 7/7) --- */
    QLabel[role="strong"]   { font-weight: 600; }                                   /* 600-weight body text */
    QLabel[role="h3"]       { font-size: 15px; font-weight: 600; }                  /* a sub-h2 section title */
    QLabel[role="overline"] { font-size: $type_caption; font-weight: 600; color: $muted; letter-spacing: 1px; }
    QToolButton[role="link"] { border: none; font-weight: 600; text-align: left; } /* flat link-style header btn */
    /* the lint verdict banner: a static frame with a per-verdict accent stripe (state set at runtime) */
    QLabel[role="banner"] {
        background: $surface; color: $text; border-left: 4px solid $muted;
        border-radius: 6px; padding: 9px;
    }
    QLabel[role="banner"][state="ok"]    { border-left: 4px solid $success; }
    QLabel[role="banner"][state="warn"]  { border-left: 4px solid $warn; }
    QLabel[role="banner"][state="error"] { border-left: 4px solid $error; }
    /* id-scoped chrome moved out of inline setStyleSheet -- retheme's setStyleSheet(qss) now re-tints these
       (they used hand re-tints or none, so several were STALE on a live theme switch; this fixes that). */
    QToolButton#hub {
        background: transparent; color: $help; border: 1px solid $help;
        border-radius: 6px; padding: 6px 10px; font-weight: 600;
    }
    QToolButton#hub:hover { background: $hover; color: $help_hover; border-color: $help_hover; }
    QToolButton#hub:focus { border: 1px solid $accent; }
    QWidget#crumbRow    { background: $surface; border-bottom: 1px solid $border; }
    QWidget#consoleHead { background: $surface; border-top: 1px solid $border; }
    QToolButton#consoleToggle       { background: transparent; border: 0; padding: 5px 6px; color: $muted; font-weight: 600; }
    QToolButton#consoleToggle:hover { color: $text; }
    /* the cohesion SPINE (Phase 7): a slim 'what do I do next' guidance strip below the breadcrumb. */
    QWidget#spineRow { background: $surface_2; border-bottom: 1px solid $border; }

    /* the workspace RAIL (Phase 6): a segmented control above the tabs that swaps which tab set shows, so
       the strip never overflows. The active segment is a raised pill (distinct from a tab's underline). */
    QWidget#railBar { background: $surface; border-bottom: 1px solid $border; }
    QToolButton#railSeg {
        background: transparent; color: $muted; border: 1px solid transparent;
        border-radius: 7px; padding: 5px 14px; font-weight: 600;
    }
    QToolButton#railSeg:hover   { color: $text; background: $hover; }
    QToolButton#railSeg:checked { color: $text; background: $surface_3; border: 1px solid $border; }
    QToolButton#railSeg:focus   { border: 1px solid $focus; }

    /* progressive-disclosure toggle (widgets.disclosure): a flat, left-aligned 'advanced' section header */
    QToolButton#disclosureToggle {
        background: transparent; border: none; color: $muted; font-weight: 600;
        padding: 6px 2px; text-align: left;
    }
    QToolButton#disclosureToggle:hover   { color: $text; }
    QToolButton#disclosureToggle:checked { color: $text; }
    QToolButton#disclosureToggle:focus   { color: $text; }

    /* the "?" concept badge next to a jargon form label -- a small circular help affordance */
    QToolButton#conceptBadge {
        background: transparent; color: $muted; border: 1px solid $border; border-radius: 11px;
        padding: 0; font-weight: 700; font-size: 11px;
    }
    QToolButton#conceptBadge:hover { color: $accent; border-color: $accent; }
    QToolButton#conceptBadge:focus { border: 1px solid $focus; }
    """
)


def qss(palette: dict, density: str = "comfortable") -> str:
    """Render the workspace stylesheet for ``palette`` (an :mod:`..editor.theme` LIGHT/DARK dict).

    Derives the semantic tokens (elevation ladder, focus, tinted selection, ...) and merges the theme-
    independent scales + the chosen ``density`` profile (``"comfortable"`` default / ``"compact"``), so the
    template may reference any of them. ``derive`` is idempotent, so a base OR an already-derived palette
    both work -- callers (tests, the shell) need not derive up front. An unknown density falls back to
    comfortable."""
    dens = _DENSITY.get(density, _DENSITY["comfortable"])
    pal = derive(palette)
    art = {                                          # per-tint indicator art (see the module docstring)
        "check_img": _asset("check", _CHECK_SVG.format(color=pal["accent_fg"])),
        "check_img_off": _asset("check", _CHECK_SVG.format(color=pal["muted"])),
    }
    return _QSS.substitute({**_SCALES, **dens, **art, **pal})
