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
# QUARTO P1 -- THE TYPE FLOOR. Two rungs moved, and the receipts are worth keeping:
#
# type_caption 11 -> 12: the Windows system font is Segoe UI 9pt, which RESOLVES TO 12px (QFontInfo, not
#   QFont -- the app font carries pointSize=9 and pixelSize=-1). So the tier whose entire job is to TEACH
#   was set one pixel below what the OS itself calls text. 12 is not a taste call: it is the floor.
# type_body 13 -> 14: measured cost, measured buyback. At 1280px a 14px body pushes one toolbar button
#   into Qt's hidden extension chevron (15/15 -> 14/15) -- the exact bug the comment at QToolBar guards.
#   tb_space 6 -> 4 buys it back to 15/15. 15px does NOT recover (13/15), which is why this rung stops at
#   14. Reproduced natively under Fusion: evidence/probe_toolbar_budget.py.
#
# type_body EXISTS so that role="cardtitle" can BE the body rung rather than repeat its number (RUBRIC).
# The remaining literals (26px name, 15px h3, 34px glyph, 11px badge) are still hard-typed in the sheet
# below -- collapsing all eight onto one table is QUARTO P3, and CALIBRE is load-bearing on it: _SCALES
# owns 3 of the 8 sizes, so scaling it alone would INVERT the ramp (hints outgrowing the body).
# THE TYPE TABLE (QUARTO P3) -- every size the sheet sets, in ONE place, as ints.
#
# It was split before this: 3 sizes were tokens here and 5 were anonymous px typed into the sheet below.
# That made "nudge the type up" a scavenger hunt rather than an edit -- but the real cost is that a SCALE
# could not exist. Multiplying _SCALES alone would raise the hint to 15px while the body stayed frozen at
# 14: the annotation outgrowing the thing it annotates. CALIBRE is load-bearing on this table, which is
# why it exists before CALIBRE does.
#
# TWO ENTRIES ARE NOT RUNGS OF THE READING RAMP, and the distinction is load-bearing for anything that
# iterates this table:
#   type_glyph -- role="empty_glyph". A large DECORATIVE glyph: an icon that happens to be drawn by the
#     font. Never read as text, so it is exempt from the ramp fences (which name it explicitly).
#   type_badge -- the "?" concept badge's glyph. It sits inside forms_qt's setFixedSize(22, 22), whose
#     border-radius (11px) is HALF THAT BOX -- a geometric pin that shares the number 11 with this type
#     value for completely unrelated reasons. DO NOT WELD THEM. Measured: the glyph fits its pin at 11 and
#     12 and OVERFLOWS at 13 (sizeHint 19x23 vs 22), and setFixedSize clips rather than grows. So scaling
#     the glyph without the box clips the "?" at 1.25x; scaling the box without the radius turns the
#     circle into a rounded square. Any scale must move all three together.
# THE RAMP IS NOT OPTICALLY LINEAR, and that is deliberate -- do not "fix" it by reading these numbers.
# They are NOMINAL px; the eye reads X-HEIGHT, and the faces differ. Measured natively
# (evidence/probe_optical.py): Segoe UI is flat at x/px 0.500 at EVERY size (one master, linearly scaled),
# but the crown wears Sitka Display at 0.439 and the hero's wordmark wears Sitka Banner at 0.430 -- real
# display cuts from a real six-cut optical family (Small .503 / Text .477 / Subheading .462 / Heading .449
# / Display .439 / Banner .430, all installed, each itself scale-invariant). So the app already spends the
# optical axis where it pays, at the top, and the crown's true size over the body is 1.63x -- NOT the 1.86x
# these two numbers imply.
#
# CONSEQUENCE WORTH KNOWING BEFORE MOVING type_body: the crown's optical dominance moves INVERSELY with the
# body and its own number never changes. QUARTO P1 (body 13 -> 14) quietly took the nameplate from 1.76x to
# 1.63x. Nobody noticed, because 26 stayed 26.
_TYPE = {
    "type_name": 26,          # the nameplate crown (role="name"), Sitka Display -- x/px 0.439, not 0.500
    # QUARTO P2 -- ONE head rung, 18. Was h2=16 AND h3=15: two roles, 1px apart, for ONE job.
    #
    # 15 vs 16 is a 6.7% CAP-HEIGHT step (10.50 vs 11.20, measured) where a legible tier is 15-25%. It was
    # a hierarchy Segoe cannot draw -- the size analogue of the PER-FAMILY CUT LIST law about weights, and
    # exactly RUBRIC's defect mirrored: there ONE token did three jobs, here TWO roles did one.
    # And the distinction it claimed was fiction. h3's docstring said "a sub-h2 section title"; ALL FOUR
    # sites are top-level titles of independent containers -- a QDialog (the concept card), the models
    # detail pane, the Inspector panel, the lede card. ZERO sit under an h2. There was no nesting to name.
    #
    # 18, not 16: at 16 the head was only 1.14x the body -- a 14% nominal step that draws as ~11% of cap.
    # 18 makes it 1.286 (cap 12.59 vs 9.80 = a 28.5% step, real). The ramp is now FOUR rungs and every one
    # of them is visible: 12 -> 14 -> 18 -> 26, steps 1.167 / 1.286 / 1.444, zero dead. Fenced.
    "type_head": 18,
    "type_body": 14,          # the QWidget base; every other rung is read against this
    "type_caption": 12,       # THE FLOOR: Segoe UI 9pt (the Windows default) resolves to exactly 12px
    "type_mono": 12,
    "type_glyph": 34,         # not a rung -- see above
    "type_badge": 12,         # not a rung, but it IS text: 11 -> 12 joins the floor (see below)
}

_SCALES = {
    **{k: f"{v}px" for k, v in _GRID.items()},
    "radius_sm": "4px", "radius_md": "6px", "radius_lg": "8px",
    **{k: f"{v}px" for k, v in _TYPE.items()},
}


def space(key: str, density: str = "comfortable", scale: int = 100) -> int:
    """The 4px grid as an int, for Qt layout calls (``setContentsMargins`` / ``setSpacing``).

    QSS gets the same numbers via :data:`_SCALES`; this is the only way a layout can share them, since
    ``QLayout`` is not styleable. Keeps this module Qt-free -- it returns an ``int``, not a QMargins.

    ``scale`` is the text dial, and it belongs here for the same reason it belongs in the sheet: SPACE IS
    PART OF TYPE. A 21px line in padding sized for a 14px one is not the same design at a different size,
    it is a worse design. Measured before this existed: at 150% a card's ink grew 50% and its air grew
    0px, taking it from 56% whitespace to 45%.
    """
    grid = _GRID_COMPACT if density == "compact" else _GRID
    return scale_px(grid[key], scale)


# THE TOOLBAR DOES NOT SCALE, AND THIS IS MEASURED RATHER THAN ARGUED. Its metrics are the one place in
# the sheet where padding competes with a hard constraint: every action plus the search pill and the gear
# must FIT at 1280, and what does not fit disappears into Qt's hidden extension chevron -- which is how
# Ctrl-K and Preferences went invisible once already.
#
# Counted natively at 1280 (evidence/probe_breathe.py), from the TYPE scale alone, before spacing joined:
#     100% -> 15/15      110% -> 14/15      125% -> 13/15      150% -> 11/15
# The budget is not "spent if we grow this" -- it is ALREADY spent, by the text. Growing tb_pad/tb_space
# on top would take more items for no legibility gain: toolbar padding is space around an ICON, not
# around prose, so it buys nothing at the setting a low-vision user actually turned the dial for.
_NO_SCALE = ("tb_pad", "tb_space", "tb_btn_pad")


def _pad_px(value: str, scale: int = 100) -> str:
    """Scale a CSS padding shorthand -- "6px 10px" -> "9px 15px" at 150%.

    Per-COMPONENT, because a shorthand is 1-4 independent lengths and they scale independently. Uses
    scale_px, so it inherits the floor-at-100% rule: the dial may only ever GROW a box.
    """
    return " ".join(f"{scale_px(int(p.removesuffix('px')), scale)}px" for p in value.split())

# UI density -- two profiles for the control paddings/spacings that set how tight the app reads. Comfortable
# (the default) matches the proven layout, with one deliberate "more whitespace" nudge: roomier tree/list
# rows. Compact tightens throughout for a power user who wants more on screen. NB: Comfortable keeps the
# toolbar + button padding as-is so the toolbar still FITS at 1280px (its hard constraint); the whitespace
# gains live in the content surfaces (rows), and Compact only ever shrinks.
_DENSITY = {
    "comfortable": {
        "tb_pad": "5px 8px", "tb_space": "4px", "btn_pad": "6px 10px",   # 6 -> 4: QUARTO P1's body bump
        "tb_btn_pad": "6px 10px",                        # == btn_pad at 100%, but exempt from the dial
        "input_pad": "6px 9px", "combo_pad": "4px 8px", "row_pad": "6px 8px",
        "tab_pad": "7px 16px", "menu_pad": "6px 22px",
    },
    "compact": {
        "tb_pad": "3px 6px", "tb_space": "4px", "btn_pad": "4px 8px",
        "tb_btn_pad": "4px 8px",
        "input_pad": "4px 7px", "combo_pad": "3px 7px", "row_pad": "3px 4px",
        "tab_pad": "5px 12px", "menu_pad": "5px 16px",
    },
}

# Every $name below must be a key in the palette (editor.theme LIGHT/DARK provide them all).
_QSS = Template(
    """
    * { outline: 0; }
    QWidget { background-color: $bg; color: $text; font-family: "Segoe UI"; font-size: $type_body; }

    /* Toolbar metrics are deliberately COMPACT (spacing 4 / button padding 10): every action plus the
       search pill and the gear menu must FIT at the default 1280px window -- overflowing items land in
       Qt's hidden extension chevron, which is how the Ctrl-K search and Preferences went invisible.
       SPACING WAS 6 AND IS NOW 4 -- that is QUARTO P1's body bump being paid for, not a free tidy. The
       14px body costs exactly one button at 1280 (15/15 -> 14/15) and this rung buys it back (15/15),
       measured natively under Fusion by evidence/probe_toolbar_budget.py. Compact density already shipped
       4px, so this is a rung the app owns, not a new number. If a future round grows the body again:
       15px loses two items and tightening does NOT recover them -- the budget is spent. */
    QToolBar { background: $surface; border: 0; border-bottom: 1px solid $border; padding: $tb_pad; spacing: $tb_space; }
    /* A TOOLBAR BUTTON IS NOT A CARD BUTTON, and one token was doing both jobs. btn_pad (no dollar --
       THE COMMENT-PLACEHOLDER LAW, and writing THIS comment tripped its fence for the 7th time) is
       padding around PROSE on a card, where it must grow with the dial, AND padding around an ICON up
       here, where it must not. Exempting tb_pad/tb_space alone did not hold: the generic rule above hands
       every toolbar button btn_pad, so at 150% each grew 6px 10px -> 9px 15px -- +10px across x15 items,
       ~150px of toolbar. COUNTED, which is the only reason this rule exists: exempting the toolbar's own
       two metrics and stopping there made the budget WORSE than before BREATHE:
           tb_pad/tb_space exempt only:   110% 13/15   125% 11/15   150% 10/15
           ...plus this rule:             110% 14/15   125% 13/15   150% 11/15  (= the type-only baseline)
       Descendant selector = specificity (0,0,0,2), which out-ranks the generic (0,0,0,1) and loses to
       #gear / #search (0,1,0,1) -- both of which already pin their own literal padding, so they are
       untouched either way. */
    QToolBar QToolButton, QToolBar QPushButton { padding: $tb_btn_pad; }
    QToolBar::separator { background: $border; width: 1px; margin: 5px 4px; }
    /* INTAGLIO -- one light, from above. A RAISED object catches the light on its top edge and shades its
       foot. The fill cannot say "this is a button" (LIGHT's surface_btn IS surface, contrast 1.0000), so
       the edge says it instead.

       Both edges are always emitted and there is deliberately no `if dark:` anywhere: border is the one
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
        background: $pressed; color: $pressed_fg;
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
    /* :pressed IS NOT OPTIONAL ON AN id RULE -- the same trap #accent:disabled and [role=quiet] below each
       document and fix at their own site, shipped at six more. `#search` (0,1,0,1) out-ranks the generic
       `QPushButton:pressed` (0,0,1,1), so this pill -- the Ctrl-K opener, in the toolbar, clicked all day
       -- changed NOTHING on click. Measured 0 px, against #gear's 3905: #gear is the one id-scoped button
       that does not restate `background`, and the one that still worked. A cascade shadow, not Qt.
       The fill, not the edge: this is already a CUT object (shade on top, lit at the foot), so there is no
       raised edge left to invert -- pressing deepens the well. Same move as [role="quiet"]:pressed. */
    QPushButton#search:pressed { background: $pressed; border-color: $accent; color: $pressed_fg; }
    /* The primary is the ONE most-raised object on a screen, lit from its own hue rather than from
       border. It MUST restate its edge -- `border: 1px solid accent` resets the per-side colours set on
       the generic QPushButton above, which silently flattened it when probed.

       ONE EDGE, NOT TWO, and this is where the border pair's trick stops working. border is a
       desaturated grey, so mixing it toward white and toward black moves it by different amounts: one
       edge carries (d26-d34) and the other stays QUIET (d6-d13) and is eaten by the palette. accent is
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
       accent_fg, not focus: focus == accent in 6 of 7 palettes, so a focus ring on an accent fill
       would be invisible. */
    QPushButton#accent:focus { border: 1px solid $accent_fg; }

    /* The QUIET tier -- the bottom rung of the button ladder: #accent primary > plain default > quiet.
       An action row of four equally-filled buttons has no entry point; the eye has to read all four to
       find the verb. Quiet drops the FILL (not the text) so the row keeps one obvious start.

       `color: text`, NOT muted: lines above already spend *transparent + muted* as the DISABLED idiom
       (QToolButton:disabled), so a muted ghost would read as un-clickable. The hierarchy comes from the
       missing fill.

       :disabled and :pressed are NOT optional. `QPushButton[role="quiet"]` (0,0,1,1: type + attribute)
       TIES the generic `QPushButton:disabled` (0,0,1,1: type + pseudo-class) on specificity, and this
       block is declared LATER -- so source order hands it the win and a disabled quiet button would
       render pixel-identical to an enabled one. The explicit `[role="quiet"]:disabled` (0,0,2,1) outranks
       both. Same trap as #accent:disabled above. MEASURED, not reasoned: strip the :disabled rule and a
       disabled quiet button resolves to text (#e6e8eb in dark) -- byte-identical to enabled -- instead of
       muted (#a4acb5). It is live, not hypothetical: builddoc's `_busy()` disables `pack_btn` for the
       duration of every build/deploy run, which is exactly when the user is watching that row. */
    QPushButton[role="quiet"]          { background: transparent; border: 1px solid $border; color: $text; }
    QPushButton[role="quiet"]:hover    { background: $hover; }
    QPushButton[role="quiet"]:pressed  { background: $pressed; color: $pressed_fg; }
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
    /* CHECKED must say WHICH KIND of control this is. A bare `background: accent` (what shipped) made a
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
       in muted, so it reads as unavailable rather than active. Specificity 0x31 out-ranks :checked's 0x21. */
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
    /* THE READ-ONLY WELLS -- the main Output console, the Co-op bridge log, the save-slot detail pane.
       The comment above says "every interactive control", and for one round it meant "every BUTTON": these
       are real tab stops (StrongFocus) and measured 0 px on focus, so a keyboard user landed in the app's
       largest reading surface with no way to tell. They are not a special case and never were -- the rest
       rule already gives them a 1px border (no dollar -- THE COMMENT-PLACEHOLDER LAW, 8th instance, caught
       by its own fence while writing THIS), so this is the same free recolour the comment
       describes, and it was simply never written. (Read-only is why it hid: an EDITABLE QPlainTextEdit
       shows a text CARET, which looks like feedback and is not a focus ring; suppress the caret and the
       control goes silent.) Like the tree above, the shorthand resets the well's per-side cut edges while
       focused -- deliberate and consistent: the ring IS the state, and it replaces the material for as
       long as it is on. */
    QPlainTextEdit:focus, QTextEdit:focus { border: 1px solid $focus; }
    /* The campaign MAP -- a QGraphicsView you can pan and zoom from the keyboard, and the only doc that is
       ITSELF the tab stop. Free, like the wells: Qt gives it a 1px StyledPanel frame (frameWidth == 1), so
       this only recolours what is already drawn. */
    QGraphicsView:focus { border: 1px solid $focus; }
    /* THE SCROLL AREAS ARE THE ONE PLACE THE RING IS NOT FREE, because they are the one place with no
       border to recolour: the shell builds them `setFrameShape(NoFrame)` so the panes read edge-to-edge.
       So the border is RESERVED TRANSPARENT at rest and only coloured on focus -- the same move #railSeg
       and #consoleToggle use, and the only one that does not make the pane JUMP 2px when you tab to it.
       (A scroll area is a real stop: it is how a keyboard user scrolls a long document, and the Inspector
       has no focusable children at all, so tabbing to it is the ONLY way to read it.) */
    QScrollArea { border: 1px solid transparent; }
    QScrollArea:focus { border: 1px solid $focus; }
    /* NB: pseudo-ELEMENT before pseudo-CLASS -- `::indicator:focus`, NEVER `:focus::indicator`. Qt does
       not reject the wrong order: `Selector::pseudoElement()` reads the FIRST pseudo, sees the known class
       `focus`, and returns ""; `pseudoClass()` then returns 0 on the unknown `indicator`, so the match test
       `(0 & state) == 0` is true in EVERY state. The rule silently degenerates to an unconditional
       `QRadioButton, QCheckBox { border: 1px solid focus; }` -- which shipped, and boxed every radio and
       checkbox in the app in a permanent accent rect while giving them NO focus ring at all.
       test_qss_has_no_malformed_subcontrol_selectors now guards the whole class of typo. */
    QCheckBox::indicator:focus, QRadioButton::indicator:focus { border: 1px solid $focus; }
    /* A CHECKED indicator is already filled accent, and focus == accent in 6 of 7 palettes, so the rule
       above would be invisible exactly when a radio is clicked or arrowed into. accent_fg is the one token
       guaranteed legible ON accent. Specificity (0x31 > 0x21) wins this, not source order. */
    QCheckBox::indicator:checked:focus, QRadioButton::indicator:checked:focus { border: 1px solid $accent_fg; }

    /* A CONTAINER OF CONTENT IS A WELL -- cut into the plate, never sitting on it. That is the material's
       one rule, and it is what makes the light read as a light rather than as trim: a control is RAISED
       (lit on top), a well is CUT (the exact inverse). Every tree and list in this app holds content --
       the project tree, the catalogs, Problems, the palette picker -- so they are all wells. */
    QTreeWidget, QTreeView, QListWidget {
        background: $surface; border: 1px solid $border; border-radius: $radius_lg; padding: 4px;
        border-top-color: $border_shade; border-bottom-color: $border_lit;
    }
    /* The rail is RESERVED on every row, transparent until selected. Without this the border appears on
       selection, the content box shrinks, and every row jogs 3px sideways as you arrow through the tree. */
    QTreeView::item, QListWidget::item {
        padding: $row_pad; border-radius: $radius_sm; border-left: 3px solid transparent;
    }
    QTreeView::item:hover, QListWidget::item:hover { background: $hover; }
    /* THE SELECTION STOPS SHOUTING. This used to paint the FULL accent -- the identical fill as the
       primary CTA, on a PERSISTENT selection, three feet from the gold signet. "One corner, once" is a
       claim about scarcity, and the loudest colour in the app was being spent on "which row is under the
       cursor". This is the one place SIGNET's own contract was written down and never applied, and the
       fix enforces it by SUBTRACTION: after this the crumb-row Deploy is the only full-accent object in
       the window.

       selection_bg finally renders. It has existed as a derived token since Phase 1 with ZERO rules --
       tinted exactly for this job and never once spent.

       The rail carries the signal the fill gives up: selection_rail is the accent lifted to clear 3:1 ON
       the tinted fill (nord 3.19, solarized-dark 3.13; the other six already clear). Fill says "this row
       is special", rail says "and it is THE one". */
    QTreeView::item:selected, QListWidget::item:selected {
        background: $selection_bg; color: $text; border-left: 3px solid $selection_rail;
    }
    /* Pinned: without it the generic :hover above wins on a selected row and the tint disappears under
       the cursor -- exactly the row you are looking at. */
    QTreeView::item:selected:hover, QListWidget::item:selected:hover {
        background: $selection_bg; color: $text; border-left: 3px solid $selection_rail;
    }
    /* THE EXCEPTION, and it is a real distinction rather than a carve-out: in a TRANSIENT MODAL the
       selection IS the interface -- the Ctrl-K palette is one list and one highlighted row, and there is
       no CTA on screen for it to compete with. In a tree the selection is persistent state you leave
       sitting there for an hour. An id selector (0,1,0,1) outranks the type+pseudo rule above (0,0,1,1). */
    QListWidget#paletteList::item:selected { background: $accent; color: $accent_fg; border-left: 3px solid $accent; }
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

    /* log_bg IS the well material -- always the deepest fill in the palette, never named for what it was
       doing. It is a well: cut, like every other container of content.
       (An earlier draft proposed a DERIVED well token; measurement killed it -- it regressed its own
       exemplars, dracula 1.383 -> 1.281 and mist 1.343 -> 1.306. The depth was never the problem; the
       missing edge was. NB the token names in this comment carry no leading dollar ON PURPOSE: Template
       has no concept of a CSS comment, so naming a dead token as a placeholder here KeyErrors every
       palette at import. This exact comment did that once.) */
    QPlainTextEdit, QTextEdit {
        background: $log_bg; color: $log_fg; border: 1px solid $border; border-radius: $radius_lg;
        border-top-color: $border_shade; border-bottom-color: $border_lit;
        font-family: "Cascadia Code", "Consolas", monospace; font-size: $type_mono; padding: 6px;
    }

    /* dropdown menus (the toolbar Field / Campaign / Journey buttons) */
    QMenu { background: $surface; border: 1px solid $border; border-radius: $radius_md; padding: 4px; }
    QMenu::item { padding: $menu_pad; border-radius: $radius_sm; }
    QMenu::item:selected { background: $accent; color: $accent_fg; }
    QMenu::separator { height: 1px; background: $border; margin: 4px 6px; }

    /* GEOMETRIC, not a token: the groove is 12px, so 6 is the handle's TRUE pill (exactly half-width).
       5px left a barely-eased rectangle; 4px (radius_sm) would square off the one element Linear and
       Zed both render as a capsule. It coincides with radius_md's 6px -- spend the token, since a
       future re-tune of the groove width is the thing that should move it, not the button radius. */
    QScrollBar:vertical { background: $bg; width: 12px; margin: 0; }
    QScrollBar::handle:vertical { background: $scroll; border-radius: $radius_md; min-height: 28px; }
    QScrollBar:horizontal { background: $bg; height: 12px; margin: 0; }
    QScrollBar::handle:horizontal { background: $scroll; border-radius: $radius_md; min-width: 28px; }
    QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
    QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

    /* the slim 'Working…' busy bar in the console header (indeterminate while a job runs) */
    /* GEOMETRIC, not a token: shell.py fixes this bar at 120x6, so 3px is EXACTLY half-height = the
       capsule. radius_sm (4px) exceeds half-height, and Qt then either clamps it (buys nothing) or
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
    /* THE NAMEPLATE. Every working screen names its subject ONCE, at display size, and this is the only
       rule in the sheet allowed to name a serif -- fenced by test_only_the_nameplate_wears_the_serif.

       WHY A SERIF, and why this is not a renegotiation of the identity contract: hero.py already
       separated the two halves of the front door -- "the wordmark is pal['text'], NEVER gold; a gold
       'Dream World IX' is a fan-logo". SIGNET kept GOLD as the identity and left the serif neutral. This
       spends the neutral half. Nothing here carries FF9; it carries size.

       WHY Sitka Display 26 and not Segoe 24: within one family, nominal ratio IS optical ratio (Segoe
       24/13 = 1.85 nominal, cap 16.80/9.09 = 1.85 optical). Across families it is not, and the gap is
       where a type ramp quietly dies -- an 18px serif declares 1.38x and delivers cap 1.23x, optically
       identical to an h2. Measured here: Sitka Display 26 caps at 16.03 against the body's 9.09 = 1.76x,
       real. Sitka ships SIX optical sizes and this is exactly what they are for: the hero's Banner 40
       had a 2.5x hole under it, and Display 26 fills it -- Banner 40 > Display 26 > h2 16 > body 13 >
       caption 11. The front door stops being an outlier and becomes the crown of a ramp.

       Weight 400: a display-optical serif is already dark at 26px, and Sitka Display Semibold is a
       separate FAMILY (not a weight), so asking for 600 here would silently synthesise. FALLBACK is one
       property -- delete the font-family line and this is Segoe 24/700 at 1.85x. */
    QLabel[role="name"] {
        font-family: "Sitka Display", "Sitka Text", "Georgia", "Segoe UI";
        font-size: $type_name; font-weight: 400; color: $text;
    }
    /* role="display" (24/700) and role="h1" (20/600) lived here and rendered ZERO pixels for three
       rounds -- no widget ever set either. They were kept alive only by tests that tested them, which
       is the argument backwards: the tests existed because the code existed, not because anyone used
       it. role="name" is the top rung now, and it has call sites. */
    /* THE HEAD -- the title of a panel, a card, or a dialog. ONE rung, because there is ONE job here.
       Was role="h2" (16) AND role="h3" (15): two roles a pixel apart, which Segoe draws as a 6.7%
       cap-height step -- a distinction the code claimed and the screen could not show. h3's own docstring
       named the nesting that justified it ("a sub-h2 section title") and no such nesting existed: all
       four sites were top-level titles of independent containers. The roles are merged, not aliased --
       an alias would keep two names for one thing and invite the split to grow back. */
    QLabel[role="head"]    { font-size: $type_head; font-weight: 600; color: $text; }
    /* 600, NOT 500. Segoe UI ships no Medium -- measured natively, weights 400/450/500 render
       BYTE-IDENTICAL (advance 63.22 each) and 550 is the first that reaches Semibold (65.97). So this
       tier spent three rounds declaring a distinction the font cannot draw: every form label in the
       Editor rendered as plain body text while a comment two files away called it "the type ramp".
       Fenced by test_every_declared_weight_is_a_weight_segoe_can_draw. */
    QLabel[role="label"]   { font-weight: 600; }
    QLabel[role="muted"]   { color: $muted; }                 /* secondary text, unchanged size */
    /* An inline keyboard-reachable cross-link (builddoc/coopdoc header wayfinding). Its <a> makes it a Tab
       stop (LinksAccessibleByKeyboard), so the a11y law says it MUST paint where the keyboard is. Reserve a
       transparent 1px border at rest so :focus only RECOLOURS it -- no reflow between states. */
    QLabel#headerXlink          { border: 1px solid transparent; border-radius: $radius_sm; padding: 1px 4px; }
    QLabel#headerXlink:focus    { border: 1px solid $focus; }
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
    QLabel[role="caption"][state="warn"]  { color: $warn_text; } /* a soft warning (e.g. text may overflow) */

    /* DICTION -- THE NOTICE. The comment four lines up has stated this law since Phase 2: "Never demote a
       diagnostic to 11px grey -- demote the EXPLANATION, never the answer." The rule immediately BELOW it
       was `QLabel[role="caption"][state="error"]`: an error, at the caption rung, in the tier reserved for
       explanations. The law and its violation were adjacent lines, and the law lost for three rounds.
       So the diagnostic gets its own tier, and the split is ONE question -- IS IT READ, OR IS IT GLANCED?
         caption -> READ.    Prose attached to a control. Small, muted, measured (COLUMN).
         notice  -> GLANCED. Anything that REPORTS. Body rung, state-coloured, never smaller than the
                    field it is about -- because you do not read an error, you are interrupted by one.
         chip/overline -> a TAG. Stays at the caption rung; a label is not prose.
       The tier this replaces was doing all three jobs at once, which is why it got both axes backwards:
       the LONGEST text got the SMALLEST face, and a warning was filed at 11px grey because "small = quiet"
       was the only tool in the box.
       NO CHIP, NO BADGE, NO GROUND OF ITS OWN -- deliberately. A notice is state-coloured text on the card
       it belongs to. Measured over all 8 palettes: error/warn on surface_2 (where a form lives) pass
       4.54-10.22, but on surface_3 they are SUB-AA IN 6 OF 8 (error 3.84-4.23). That is zero pixels today
       because nothing grounds state text there -- and giving a notice a chip would light it up in six
       palettes at once. THE NINTH-GROUND LAW: invent a ground, you owe it a fence. This tier declines the
       ground instead. */
    QLabel[role="notice"] { font-size: $type_body; color: $text; }
    QLabel[role="notice"][state="error"] { color: $error_text; }
    QLabel[role="notice"][state="warn"]  { color: $warn_text; }
    QLabel[role="subtle"]  { color: $text_subtle; }
    /* teaching empty-states (workspace.widgets.empty_state): a large decorative glyph + a title, over the
       caption teaching line + optional action buttons -- replaces black-void / bare 'nothing loaded' panels */
    QLabel[role="empty_glyph"] { font-size: $type_glyph; color: $text_subtle; }
    QLabel[role="empty_title"] { font-size: $type_head; font-weight: 600; color: $text; }
    QFrame[role="card"] { background: $surface_2; border: 1px solid $border; border-radius: $radius_lg; }
    /* THE MONO REGISTER. This app's whole subject is machine tokens -- 4003, 30110, ff9-XXXXXXXX,
       FF9CustomMap, C:/.../FF9CustomMap. Set in the body face they read as prose and the eye slides off
       them; set in mono they read as things you copy, and it is the one real texture in the composition.
       FAMILY ONLY -- no font-size, so it inherits the body rung and neither row heights nor 24px hit
       targets move. (This said "13px" until QUARTO P1 moved the body to 14. The RULE was always
       "inherit"; the number was the stale part, and naming it here is what made it able to go stale.
       Do not write the token name here either -- a placeholder in a QSS comment still substitutes.)
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
    /* (h3 lived here: 1px under h2, a 6.7% cap-height step the font could not draw, glossed as "a sub-h2
       section title" for a nesting that never existed. QUARTO P2 merged it into role="head" above.) */
    QLabel[role="overline"] { font-size: $type_caption; font-weight: 600; color: $muted; letter-spacing: 1px; }
    /* RUBRIC -- a card's title is a TITLE. widgets.section() titled all 25 cards with role="overline":
       the caption rung, 600, muted. role="caption" -- the hint text INSIDE those cards -- is the caption
       rung, 400, muted. Same size. Same colour. The title out-ranked its own explanation by one weight
       step, which Segoe draws at +4.5% of advance, plus a pixel of tracking. A card's whole hierarchy
       spanned two pixels, and its top and bottom rung were the same pixel.
       QUARTO P1 alone would have made that WORSE, not better: body -> 14 and hint -> 12 while the title
       stayed pinned to the caption token at 12 -- the title tying the smallest text on its own card.
       So: the body rung (a real step over the hint), 600, and the full text ink -- a colour step, not a
       weight's worth of grey. Contrast RISES everywhere (muted -> text over a card ground is 5.31 -> 6.20
       worst-case, solarized-light); this is about RANK, and nothing here is a compliance fix.
       (No token names in this comment on purpose -- a placeholder inside a QSS comment still substitutes,
       and writing THIS paragraph is exactly when you reach for one. That law has now bitten four times.)
       A NEW role rather than an edit to overline, because overline still has a job: the nameplate's
       kicker, a small-caps eyebrow OVER a big title -- a tier SIGNET already got right. Uppercase +
       tracking is a convention that works BECAUSE it is small. Promoted to the body rung it stops being
       an eyebrow and starts being a shout, which is why the .upper() goes with it (see widgets.section). */
    QLabel[role="cardtitle"] { font-size: $type_body; font-weight: 600; color: $text; }
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
    /* PRESSED FILLS, because no ink clears AA on the `pressed` GROUND. This shipped as
       `background: pressed; color: help_hover` and measured 2.23:1 on solarized-dark -- sub-AA in 7 of 8,
       on a button with a real text label. `help` is lifted per palette to clear 4.5 AS TEXT; `help_hover`
       never was, so I propagated an unfenced pair rather than minting one. (Its `:hover` sibling above has
       the same flaw, pre-dating this: dark 3.12, solarized-dark 2.82.)
       Measured, NOTHING is legible on `pressed`: text 6/8, accent_fg 1/8, help_fg 0/8, muted 1/8 -- because
       `pressed` is a ground derive() has never solved anything against (_grounds is bg/surface/surface_2).
       So the press spends the pair the palette ALREADY fences: help_fg on help, worst 5.19, guarded by
       test_a_filled_ground_carries_its_ink. The affordance fills instead of tinting -- a stronger press
       than a background swap, and the only one that is legible in all 8. */
    QToolButton#hub:pressed { background: $help; color: $help_fg; border-color: $help; }
    QToolButton#hub:focus { border: 1px solid $accent; }
    /* NO border-bottom. THE LAW: a border belongs to the band whose existence it is CONDITIONAL ON.
       The band under this one is the spine, and the spine HIDES (shell.py: setVisible(bool(guidance or
       actions))) -- so this line's job depends on a widget that is usually not there. Measured: with the
       spine hidden, which is the common case, this border separated surface from surface -- contrast
       1.000, a line between a colour and itself. The line that delineates the spine now belongs to the
       SPINE, below, as a border-top: it exists exactly when the thing it delineates does.
       NB a naive adjacency check does not see this. It reads crumb|spine as surface|surface_2 (1.168 --
       a real boundary) and concludes the border is earning its keep. */
    QWidget#crumbRow    { background: $surface; }
    /* THE LIP. The console is a hole cut into the bottom of the app, and this strip is the plate's near
       edge above it -- so it catches the light, exactly like a button's top edge. It is the one band in
       the chrome that is a MATERIAL boundary rather than a grouping rule, which is why it takes
       border_lit while every other band keeps the flat border. */
    QWidget#consoleHead { background: $surface; border-top: 1px solid $border_lit; }
    /* the console head's Wrap / Copy / Clear. Pinned height so the head stays a thin strip -- but the pin
       is a box around text, so it scales (style.CONSOLE_H). It was a bare setFixedHeight(24) in shell.py,
       which CALIBRE could not reach: audited, the label's line box outgrows a frozen 24 at 125%. 24 is
       also the WCAG 2.5.8 target floor, so scale_px only ever grows it. */
    QPushButton#consoleHeadBtn { min-height: $console_h; max-height: $console_h; }
    /* THE FOCUS RING RESERVES ITS OWN SPACE. This was `border: 0; padding: 5px 6px` and had NO :focus
       rule at all -- the ONLY id-scoped QToolButton missing one (its 4 siblings #hub/#railSeg/
       #disclosureToggle/#conceptBadge all have theirs), so the console's own show/hide toggle was a real
       tab stop with ZERO focus indication: measured 0 px, a WCAG 2.4.7 failure that `* { outline: 0 }`
       created and its replacement never covered.
       A ring cannot be added to `border: 0` without moving the box 2px in each axis on focus -- a control
       that JUMPS when you tab to it. So the border is reserved TRANSPARENT at rest and only coloured on
       focus, which is exactly what #railSeg below already does; the padding drops 5/6 -> 4/5 to pay for
       the 1px, keeping the rendered box byte-identical (asserted: probe_state_delta.py). */
    QToolButton#consoleToggle       { background: transparent; border: 1px solid transparent; padding: 4px 5px; color: $muted; font-weight: 600; }
    QToolButton#consoleToggle:hover { color: $text; }
    QToolButton#consoleToggle:pressed { background: $pressed; color: $pressed_fg; }
    QToolButton#consoleToggle:focus { border: 1px solid $focus; color: $text; }
    /* the cohesion SPINE (Phase 7): a slim 'what do I do next' guidance strip below the breadcrumb.
       BOTH edges, and it owns them. This band hides, so the line above it must come and go WITH it --
       that line used to live on the crumb row, where it outlived the thing it delineated and spent the
       rest of its time separating surface from surface (1.000).
       It needs both because tone cannot carry it alone: surface_2 against surface is 1.168 in dark and
       1.046 in LIGHT, so with no edges an inset strip would simply not exist in half the palettes. This
       is the one band in the chrome that is a delineated inset rather than part of the plate. */
    QWidget#spineRow {
        background: $surface_2;
        border-top: 1px solid $border; border-bottom: 1px solid $border;
    }

    /* the workspace RAIL (Phase 6): a segmented control above the tabs that swaps which tab set shows, so
       the strip never overflows. The active segment is a raised pill (distinct from a tab's underline). */
    QWidget#railBar { background: $surface; border-bottom: 1px solid $border; }
    QToolButton#railSeg {
        background: transparent; color: $muted; border: 1px solid transparent;
        border-radius: $radius_md; padding: 5px 14px; font-weight: 600;
    }
    QToolButton#railSeg:hover   { color: $text; background: $hover; }
    QToolButton#railSeg:checked { color: $text; background: $surface_3; border: 1px solid $border; }
    /* AFTER :checked, AND THAT ORDER IS THE WHOLE RULE. Both selectors are (0,1,1,1) -- an id, a
       pseudo-class, a type -- so they TIE, and on a tie the LATER rule wins the property. Written before
       :checked (as it first was), the ACTIVE segment -- the one you are on, the one most likely to be
       clicked -- rendered 0 changed pixels on press, while its inactive siblings changed 2968. The exact
       defect this round exists to kill, reintroduced inside the fix for it, one tie down.
       Proven by reordering the rendered string alone: 0 -> 2368.
       The press fence missed it because it called setCheckable(True) and never setChecked(True); it does
       both now. (#disclosureToggle survived the same shape only by luck -- its :checked sets `color`, not
       `background`, so there was nothing to lose.) */
    QToolButton#railSeg:pressed { color: $pressed_fg; background: $pressed; }
    QToolButton#railSeg:focus   { border: 1px solid $focus; }

    /* progressive-disclosure toggle (widgets.disclosure): a flat, left-aligned 'advanced' section header */
    /* The border is reserved TRANSPARENT so the focus ring costs no layout (same move as #consoleToggle
       and #railSeg); padding pays the 1px back (6/2 -> 5/1) so the box is unchanged. */
    QToolButton#disclosureToggle {
        background: transparent; border: 1px solid transparent; color: $muted; font-weight: 600;
        padding: 5px 1px; text-align: left;
    }
    QToolButton#disclosureToggle:hover   { color: $text; }
    QToolButton#disclosureToggle:pressed { color: $pressed_fg; background: $pressed; }
    QToolButton#disclosureToggle:checked { color: $text; }
    /* :focus WAS `color: text` -- byte-identical to :hover above, so focus was visible but INDISTINGUISH-
       ABLE from hovering: a keyboard user could not tell where they were from a passing mouse. A state
       that renders as another state is not a state. The ring is what makes it its own.
       (No leading dollar on that `text`, deliberately -- THE COMMENT-PLACEHOLDER LAW. string.Template has
       no concept of a CSS comment, so a dollar-prefixed token named in PROSE still substitutes, and still
       KeyErrors the moment that token is renamed or removed.
       Instances 5 AND 6 of that law are this very comment. #5: it shipped `color: [dollar]text` and
       test_no_placeholder_hides_in_a_qss_comment went red -- the law's own fence catching a comment ABOUT
       the law. #6: the sentence you are reading FIXED #5 by explaining the rule using a literal
       [dollar]name as the example, which Template then tried to substitute -- KeyError 'name', 68 tests
       down, every palette dead. The law has now broken the build twice from inside its own explanation.
       There is no way to write the token in prose. Say "dollar-prefixed" and move on.) */
    QToolButton#disclosureToggle:focus   { color: $text; border: 1px solid $focus; }

    /* the "?" concept badge next to a jargon form label -- a small circular help affordance.
       TWO ELEVENS, AND THEY ARE NOT THE SAME ELEVEN. The border-radius is GEOMETRIC: half of forms_qt's
       setFixedSize(22, 22), i.e. the definition of a circle -- it must never become a type token. The
       font-size IS type -- and it was the last text in the app under the 12px OS floor, a leftover from
       QUARTO P1, which moved the caption rung and left this behind because nothing connected them. Now
       12, and free: measured, the glyph fits its pin at 12 (sizeHint 17x21) and only overflows at 13
       (19x23), and setFixedSize CLIPS rather than grows -- so the circle is untouched.
       THIS IS THE WHOLE ARGUMENT FOR THE TABLE. The rung was invisible while it was an anonymous 11 in a
       rule 500 lines from the ramp; the moment every size sat in one dict, a value below the floor was
       impossible not to see. Fenced by test_no_text_rung_sits_below_the_os_floor.
       THE BOX IS QSS NOW, not forms_qt's setFixedSize -- so one sheet re-render resizes it and the glyph,
       together, and CALIBRE cannot leave a big "?" in a small circle. That is also why the radius is a
       token: it must stay exactly half the box at every scale (style.badge_box keeps the box even so it
       can). Audited: the glyph overflows a frozen 22px box at 150%. */
    QToolButton#conceptBadge {
        background: transparent; color: $muted; border: 1px solid $border;
        border-radius: $badge_radius;
        min-width: $badge_box; max-width: $badge_box;
        min-height: $badge_box; max-height: $badge_box;
        padding: 0; font-weight: 700; font-size: $type_badge;
    }
    QToolButton#conceptBadge:hover { color: $accent; border-color: $accent; }
    /* Same fix, same reason: this shipped as `color: accent; background: pressed` and measured 1.59:1 on
       nord -- pressing the badge erased its own glyph AND its ring into the fill, in 7 of 8 palettes. The
       glyph is 12px/700 and weight does NOT buy the large-text bar (that needs 18.66px bold), so the bar
       is 4.5. accent_fg on accent is worst 4.56 and already fenced. */
    QToolButton#conceptBadge:pressed { color: $accent_fg; border-color: $accent; background: $accent; }
    QToolButton#conceptBadge:focus { border: 1px solid $focus; }
    """
)


def type_px(name: str, scale: int = 100) -> int:
    """One rung of the type table at ``scale`` percent -- THE single definition of that arithmetic.

    A function, not an inline expression, because three places need the identical answer: the sheet (via
    :func:`qss`), any Python that pins geometry around text (``setFixedHeight`` on a caption), and the
    fences. Two of those computing it slightly differently is how a glyph ends up 1px taller than the box
    someone sized for it.

    HALF-UP, NOT ``round()``. Python's ``round`` is BANKER'S rounding: it breaks ties toward even, so
    ``round(16.5) == 16`` while ``round(17.5) == 18``. The table hits exact .5 ties constantly -- h3 (15)
    at 110% is exactly 16.5, and body (14) at 125% is exactly 17.5 -- so banker's would shrink one rung
    and grow the next from the same tie, silently collapsing steps. ``int(x + 0.5)`` is half-up and
    monotonic, which is the only property a type ramp actually needs from its rounding.
    """
    return int(_TYPE[name] * scale / 100 + 0.5)


# CALIBRE's geometry half. A box drawn AROUND text must grow WITH the text, or the box wins and the text
# is cut -- setFixedSize clips, it never grows. Audited natively (evidence/audit_text_scale.py): the whole
# app has exactly TWO such boxes, not the ~75 setFixed* sites a static count suggests. The other ~73 pin
# panel geometry that owes the font nothing.
#
#   BADGE_HALF -- the "?" concept badge. Its box is 2x this and its border-radius IS this, which is what
#     makes it a circle rather than a rounded square. Kept EVEN by construction (2 * a rounded half) so
#     the radius stays exactly half at every scale; an odd box would round-off into a squircle.
#   CONSOLE_H -- the Wrap/Copy/Clear head buttons. 24 is also the WCAG 2.5.8 target floor, so this may
#     grow and must never shrink.
BADGE_HALF = 11
CONSOLE_H = 24


def scale_px(px: int, scale: int = 100) -> int:
    """A pinned geometry value at ``scale``. Half-up and floored at the 100% value: a text-size dial may
    only ever GROW a box (shrinking one would clip at the setting that is provably fine today)."""
    return max(px, int(px * scale / 100 + 0.5))


def badge_box(scale: int = 100) -> int:
    """The "?" badge's pinned circle at ``scale`` -- always even, so ``badge_box // 2`` is exactly half."""
    return max(2 * BADGE_HALF, 2 * int(BADGE_HALF * scale / 100 + 0.5))


def qss(palette: dict, density: str = "comfortable", scale: int = 100) -> str:
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
    # BREATHE -- the space scales with the text, because SPACE IS PART OF TYPE. These two dicts used to be
    # the only ones `scale` could not reach: `typ` went through type_px and `grid`/`dens` did not, so the
    # dial grew every letter and left every gap. Measured on a real section() card: at 150% the ink grew
    # 50% and the air grew 0px (56% whitespace -> 45%); btn_pad against its own label halved. And nobody
    # opted in to that -- prefs.text_scale() SEEDS from the Windows slider, so a user who told Windows they
    # want 150% text gets a MORE cramped app on first launch, without ever finding Preferences.
    #
    # `_NO_SCALE` exempts the toolbar; see its comment for the count that decided it.
    dens = {k: (v if k in _NO_SCALE else _pad_px(v, scale))
            for k, v in _DENSITY.get(density, _DENSITY["comfortable"]).items()}
    grid = {k: f"{space(k, density, scale)}px"
            for k in (_GRID_COMPACT if density == "compact" else _GRID)}
    # CALIBRE: the type table at `scale` percent. At 100 this is provably inert -- int(px * 100/100 + 0.5)
    # == px for every int -- so the default path renders byte-identical to a sheet with no scale at all,
    # and that is fenced rather than asserted. Scaling here (not per-rule) is what makes it impossible to
    # scale HALF the ramp: P3 put all eight sizes in one table precisely so this loop could reach them.
    typ = {k: f"{type_px(k, scale)}px" for k in _TYPE}
    # the two boxes drawn around text (see BADGE_HALF / CONSOLE_H). The badge's box is QSS rather than a
    # setFixedSize so that ONE re-render resizes it: a Python pin would have to be hunted down and re-set
    # on every live scale change, and any badge built before the change would keep the stale circle.
    _bb = badge_box(scale)
    typ["badge_box"] = f"{_bb - 2}px"                # QSS min/max-width sizes the CONTENTS box; the 1px
    typ["badge_radius"] = f"{_bb // 2}px"            # border on each side makes the widget _bb again
    typ["console_h"] = f"{scale_px(CONSOLE_H, scale)}px"
    pal = derive(palette)
    art = {                                          # per-tint indicator art (see the module docstring)
        "check_img": _asset("check", _CHECK_SVG.format(color=pal["accent_fg"])),
        "check_img_off": _asset("check", _CHECK_SVG.format(color=pal["muted"])),
    }
    # `typ` after `_SCALES`: _SCALES carries the type table at 100% for callers that never scale, and the
    # scaled values must win. Order is the whole mechanism here, so do not "tidy" these into one dict.
    return _QSS.substitute({**_SCALES, **grid, **typ, **dens, **art, **pal})
