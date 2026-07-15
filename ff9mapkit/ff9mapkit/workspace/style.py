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

# The 4px SPACING GRID, as ints -- the single vocabulary shared by the QSS below (via _SCALES, which
# stringifies these) and by Qt LAYOUT calls (via space(), which returns them raw). Layouts need the int
# form because QLayout is not QSS-styleable and has no cascade: setContentsMargins takes numbers, so
# without this the grid can only ever be spent on half the app and every margin stays a magic number.
_GRID = {"space_1": 4, "space_2": 8, "space_3": 12, "space_4": 16, "space_6": 24}
# Compact scales ~0.75 and must NOT alias rungs -- a scale whose job is rhythm loses it the moment two
# rungs collapse to the same number (a 6/6 pair cannot express "tighter than").
_GRID_COMPACT = {"space_1": 4, "space_2": 6, "space_3": 8, "space_4": 12, "space_6": 16}

# Theme-independent scales threaded into the QSS template. Values are px strings so they substitute
# straight in. THE RADIUS LANGUAGE IS THESE THREE TOKENS -- everything else in the sheet is a documented
# geometric pin (a circle's half-box, a capsule's half-height), never a fourth opinion about roundness.
# Fenced by test_qss_uses_only_the_radius_language.
_SCALES = {
    **{k: f"{v}px" for k, v in _GRID.items()},
    "radius_sm": "4px", "radius_md": "6px", "radius_lg": "8px",
    "type_display": "24px", "type_h1": "20px", "type_h2": "16px",
    "type_caption": "11px", "type_mono": "12px",
}


def space(key: str, density: str = "comfortable") -> int:
    """The 4px grid as an int, for Qt layout calls (``setContentsMargins`` / ``setSpacing``).

    QSS gets the same numbers via :data:`_SCALES`; this is the only way a layout can share them, since
    ``QLayout`` is not styleable. Keeps this module Qt-free -- it returns an ``int``, not a QMargins.
    """
    grid = _GRID_COMPACT if density == "compact" else _GRID
    return grid[key]

# UI density -- two profiles for the control paddings/spacings that set how tight the app reads. Comfortable
# (the default) matches the proven layout, with one deliberate "more whitespace" nudge: roomier tree/list
# rows. Compact tightens throughout for a power user who wants more on screen. NB: Comfortable keeps the
# toolbar + button padding as-is so the toolbar still FITS at 1280px (its hard constraint); the whitespace
# gains live in the content surfaces (rows), and Compact only ever shrinks.
_DENSITY = {
    "comfortable": {
        "tb_pad": "5px 8px", "tb_space": "6px", "btn_pad": "6px 10px",
        "input_pad": "6px 9px", "combo_pad": "4px 8px", "row_pad": "6px 8px",
        "tab_pad": "7px 16px", "menu_pad": "6px 22px",
    },
    "compact": {
        "tb_pad": "3px 6px", "tb_space": "4px", "btn_pad": "4px 8px",
        "input_pad": "4px 7px", "combo_pad": "3px 7px", "row_pad": "3px 4px",
        "tab_pad": "5px 12px", "menu_pad": "5px 16px",
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
    /* INTAGLIO -- one light, from above. A RAISED object catches the light on its top edge and shades its
       foot. The fill cannot say "this is a button" (LIGHT's surface_btn IS surface, contrast 1.0000), so
       the edge says it instead.

       Both edges are always emitted and there is deliberately no `if dark:` anywhere: $border is the one
       already-mode-aware token in the app -- above its fill in all 6 dark palettes, below it in both light
       ones, 8/8 -- so each palette's own border EATS the edge it cannot hold. Dark's lit top carries
       (d33-d43) while its foot stays quiet; light's foot carries (d40) while its lit edge lands at d8 and
       vanishes. One rule, two behaviours, no branch.

       ORDER IS LOAD-BEARING: the `border:` shorthand RESETS every per-side colour, so the two
       *-color lines MUST come after it. Any later rule that restates `border:` silently flattens the
       object again -- which is why #accent and #search restate their edges below rather than inheriting. */
    QToolButton, QPushButton {
        background: $surface_btn; color: $text; border: 1px solid $border;
        border-top-color: $border_lit; border-bottom-color: $border_shade;
        border-radius: $radius_md; padding: $btn_pad;
    }
    QToolButton:hover, QPushButton:hover { background: $hover; }
    /* PRESSED INVERTS THE EDGE -- the light source does not move, the object does. A pressed button is
       cut into the plate, so it takes the input rule's ordering. The material performs the interaction
       at the cost of one rule and zero motion. */
    QPushButton:pressed, QToolButton:pressed {
        background: $pressed;
        border-top-color: $border_shade; border-bottom-color: $border_lit;
    }
    /* A disabled object is not lit: it is not raised, it is inert. Flat edges, no light. */
    QPushButton:disabled {
        color: $muted; background: $bg;
        border-top-color: $border; border-bottom-color: $border;
    }
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
    /* The search pill is a FIELD, not a button: it takes the CUT pair (shade on top, lit at the foot) --
       the same two colours as a raised object in the opposite order. It must restate them because its own
       `border:` shorthand above resets the per-side colours it would otherwise inherit. */
    QPushButton#search {
        background: $field; color: $muted; border: 1px solid $border; border-radius: $radius_md;
        border-top-color: $border_shade; border-bottom-color: $border_lit;
        padding: 6px 12px; text-align: left;
    }
    QPushButton#search:hover { border-color: $accent; color: $text; background: $field; }
    /* The primary is the ONE most-raised object on a screen, lit from its own hue rather than from
       $border. It MUST restate its edge -- `border: 1px solid $accent` resets the per-side colours set on
       the generic QPushButton above, which silently flattened it when probed.

       ONE EDGE, NOT TWO, and this is where the border pair's trick stops working. $border is a
       desaturated grey, so mixing it toward white and toward black moves it by different amounts: one
       edge carries (d26-d34) and the other stays QUIET (d6-d13) and is eaten by the palette. $accent is
       SATURATED and has no quiet edge -- dark's #4c8dff has B=255, so mixing toward black drops B by 36
       while mixing toward white cannot move it at all. Measured, the accent pair runs carrier/quiet of
       33/29 (light), 36/25 (dark), 24/22 (nord), 36/32 (gruvbox): BOTH edges always read. Emitting the
       pair here would put a symmetric bevel on the largest, loudest object on the screen -- the one place
       Win95 would actually be visible.

       THE RULE: emit both edges only where one of them is quiet. Emit one where neither is. A lit top is
       "light from above" in either mode, so this stays consistent with the border pair rather than
       fighting it. */
    QPushButton#accent {
        background: $accent; color: $accent_fg; border: 1px solid $accent;
        border-top-color: $accent_lit;
    }
    QPushButton#accent:hover { background: $accent_hover; }
    /* pressed: the object moves, the light does not -- the lit top becomes a shaded one. */
    QPushButton#accent:pressed { background: $accent_pressed; border-top-color: $accent_shade; }
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

    /* The QUIET tier -- the bottom rung of the button ladder: #accent primary > plain default > quiet.
       An action row of four equally-filled buttons has no entry point; the eye has to read all four to
       find the verb. Quiet drops the FILL (not the text) so the row keeps one obvious start.

       `color: $text`, NOT $muted: lines above already spend *transparent + muted* as the DISABLED idiom
       (QToolButton:disabled), so a muted ghost would read as un-clickable. The hierarchy comes from the
       missing fill.

       :disabled and :pressed are NOT optional. `QPushButton[role="quiet"]` (0,0,1,1: type + attribute)
       TIES the generic `QPushButton:disabled` (0,0,1,1: type + pseudo-class) on specificity, and this
       block is declared LATER -- so source order hands it the win and a disabled quiet button would
       render pixel-identical to an enabled one. The explicit `[role="quiet"]:disabled` (0,0,2,1) outranks
       both. Same trap as #accent:disabled above. MEASURED, not reasoned: strip the :disabled rule and a
       disabled quiet button resolves to $text (#e6e8eb in dark) -- byte-identical to enabled -- instead of
       $muted (#a4acb5). It is live, not hypothetical: builddoc's `_busy()` disables `pack_btn` for the
       duration of every build/deploy run, which is exactly when the user is watching that row. */
    QPushButton[role="quiet"]          { background: transparent; border: 1px solid $border; color: $text; }
    QPushButton[role="quiet"]:hover    { background: $hover; }
    QPushButton[role="quiet"]:pressed  { background: $pressed; }
    QPushButton[role="quiet"]:focus    { border: 1px solid $focus; }
    QPushButton[role="quiet"]:disabled { color: $muted; background: $bg; border: 1px solid $border; }

    /* Indicators MUST be fully specified: once a stylesheet touches a QCheckBox/QRadioButton, Qt stops
       drawing the native checked dot, so without this the selected state renders INVISIBLE. */
    /* padding 3px lifts the clickable row to a >=24px target height (WCAG 2.5.8); the indicator itself is
       18px so it's a comfortable tap/hit -- we pad the control, not just the glyph. */
    QCheckBox, QRadioButton { background: transparent; spacing: 8px; padding: 3px 2px; }
    QCheckBox::indicator, QRadioButton::indicator {
        width: 18px; height: 18px; border: 1px solid $border; background: $field;
    }
    /* GEOMETRIC, not a token: 9px is half of the 18px box above = a CIRCLE, which is the entire signal
       that separates "pick exactly one" from the checkbox's "pick several". It tracks the box size; if
       that ever moves, this is half of whatever it becomes. Never a radius token. */
    QRadioButton::indicator { border-radius: 9px; }
    QCheckBox::indicator { border-radius: $radius_sm; }
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

    /* INPUTS ARE CUT, NOT RAISED -- the INVERTED pair. A hole in a plate is shaded where the plate's edge
       overhangs it (top) and catches light on its far lip (bottom): the same two colours as a button, in
       the opposite order. That inversion is the entire reason this reads as a material rather than as
       decoration -- one light source, two kinds of object, and the geometry does the telling.
       :focus must RESTATE the pair (in accent tones) or its `border:` shorthand flattens the field at the
       exact moment you are looking at it. */
    QLineEdit {
        background: $field; color: $text; border: 1px solid $border; border-radius: $radius_md;
        border-top-color: $border_shade; border-bottom-color: $border_lit;
        padding: $input_pad; selection-background-color: $accent; selection-color: $accent_fg;
    }
    QLineEdit:focus {
        border: 1px solid $accent;
        border-top-color: $accent_shade; border-bottom-color: $accent_lit;
    }

    /* combos + spin boxes: themed like line edits (the Fusion base style would otherwise draw them from
       the platform palette, which need not match the chosen theme) */
    QComboBox, QAbstractSpinBox {
        background: $field; color: $text; border: 1px solid $border; border-radius: $radius_md;
        border-top-color: $border_shade; border-bottom-color: $border_lit;
        padding: $combo_pad; selection-background-color: $accent; selection-color: $accent_fg;
    }
    QComboBox:focus, QAbstractSpinBox:focus {
        border: 1px solid $accent;
        border-top-color: $accent_shade; border-bottom-color: $accent_lit;
    }
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
        background: $surface; border: 1px solid $border; border-radius: $radius_lg; padding: 4px;
    }
    QTreeView::item, QListWidget::item { padding: $row_pad; border-radius: $radius_sm; }
    QTreeView::item:hover, QListWidget::item:hover { background: $hover; }
    QTreeView::item:selected, QListWidget::item:selected { background: $accent; color: $accent_fg; }
    QHeaderView::section { background: $surface_btn; color: $muted; border: 0; padding: 5px; }

    QTabWidget::pane { border: 1px solid $border; border-radius: $radius_lg; top: -1px; }
    QTabBar::tab {
        background: $surface_btn; color: $muted; padding: $tab_pad; border: 1px solid $border;
        border-bottom: 2px solid transparent; border-top-left-radius: $radius_md; border-top-right-radius: $radius_md;
        margin-right: 2px;
    }
    QTabBar::tab:selected { background: $bg; color: $text; border-bottom: 2px solid $accent; }
    QTabBar::tab:hover { color: $text; }

    /* The QGroupBox block that used to live here is GONE, along with its two density tokens. Every one of
       the app's 27 boxed sections is now a QFrame[role="card"] built by widgets.section() -- the migration
       that had to happen because QSS silently ignores font-* on QGroupBox::title (colour is that
       sub-control's only lever), so a card title could never be given any presence while Qt drew it.
       QGroupBox is constructed in exactly zero places; these rules rendered nothing.
       NB: never name a token in a comment with its leading dollar sign. string.Template has no concept
       of a CSS comment, so a placeholder inside a comment still substitutes -- and still KeyErrors once
       the key is gone. A bare dollar is worse: it is an Invalid-placeholder ValueError and takes down
       every palette at import. This comment broke the build BOTH ways while being written. */

    QPlainTextEdit, QTextEdit {
        background: $log_bg; color: $log_fg; border: 1px solid $border; border-radius: $radius_lg;
        font-family: "Cascadia Code", "Consolas", monospace; font-size: $type_mono; padding: 6px;
    }

    /* dropdown menus (the toolbar Field / Campaign / Journey buttons) */
    QMenu { background: $surface; border: 1px solid $border; border-radius: $radius_md; padding: 4px; }
    QMenu::item { padding: $menu_pad; border-radius: $radius_sm; }
    QMenu::item:selected { background: $accent; color: $accent_fg; }
    QMenu::separator { height: 1px; background: $border; margin: 4px 6px; }

    /* GEOMETRIC, not a token: the groove is 12px, so 6 is the handle's TRUE pill (exactly half-width).
       5px left a barely-eased rectangle; 4px ($radius_sm) would square off the one element Linear and
       Zed both render as a capsule. It coincides with $radius_md's 6px -- spend the token, since a
       future re-tune of the groove width is the thing that should move it, not the button radius. */
    QScrollBar:vertical { background: $bg; width: 12px; margin: 0; }
    QScrollBar::handle:vertical { background: $scroll; border-radius: $radius_md; min-height: 28px; }
    QScrollBar:horizontal { background: $bg; height: 12px; margin: 0; }
    QScrollBar::handle:horizontal { background: $scroll; border-radius: $radius_md; min-width: 28px; }
    QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
    QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

    /* the slim 'Working…' busy bar in the console header (indeterminate while a job runs) */
    /* GEOMETRIC, not a token: shell.py fixes this bar at 120x6, so 3px is EXACTLY half-height = the
       capsule. $radius_sm (4px) exceeds half-height, and Qt then either clamps it (buys nothing) or
       squashes the chunk ends. Pinned to the 6px height, not to the radius language. */
    QProgressBar { background: $surface_btn; border: 1px solid $border; border-radius: 3px; }
    QProgressBar::chunk { background: $accent; border-radius: 3px; }

    QSplitter::handle { background: $border; }
    QSplitter::handle:horizontal { width: 1px; }
    QSplitter::handle:vertical { height: 1px; }
    QLabel { background: transparent; }
    QStatusBar { background: $surface; color: $muted; border-top: 1px solid $border; }
    QStatusBar::item { border: none; }
    QToolTip { background: $surface; color: $text; border: 1px solid $border; }

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
        border-radius: $radius_md; padding: 9px;
    }
    QLabel[role="banner"][state="ok"]    { border-left: 4px solid $success; }
    QLabel[role="banner"][state="warn"]  { border-left: 4px solid $warn; }
    QLabel[role="banner"][state="error"] { border-left: 4px solid $error; }
    /* id-scoped chrome moved out of inline setStyleSheet -- retheme's setStyleSheet(qss) now re-tints these
       (they used hand re-tints or none, so several were STALE on a live theme switch; this fixes that). */
    QToolButton#hub {
        background: transparent; color: $help; border: 1px solid $help;
        border-radius: $radius_md; padding: 6px 10px; font-weight: 600;
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
        border-radius: $radius_md; padding: 5px 14px; font-weight: 600;
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
    /* GEOMETRIC, not a token: 11px is half of forms_qt.py's setFixedSize(22, 22) = a circle. */
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
    comfortable.

    The spacing grid is threaded per-DENSITY, not from the static scales: ``$space_2`` and
    ``space("space_2", density)`` must be the same number, or one name quietly means two things -- 8px in
    the sheet and 6px in a layout -- which is the exact class of drift this grid exists to end.
    """
    dens = _DENSITY.get(density, _DENSITY["comfortable"])
    grid = {k: f"{v}px" for k, v in (_GRID_COMPACT if density == "compact" else _GRID).items()}
    pal = derive(palette)
    art = {                                          # per-tint indicator art (see the module docstring)
        "check_img": _asset("check", _CHECK_SVG.format(color=pal["accent_fg"])),
        "check_img_off": _asset("check", _CHECK_SVG.format(color=pal["muted"])),
    }
    return _QSS.substitute({**_SCALES, **grid, **dens, **art, **pal})
