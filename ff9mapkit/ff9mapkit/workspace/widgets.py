"""Shared Qt widget helpers for the Workspace.

PySide6-only: the application-wide wheel guard (:class:`WheelGuard`) and the empty-state list
(:class:`PlaceholderListWidget`).
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontInfo, QFontMetricsF, QPainter
from PySide6.QtWidgets import (
    QAbstractSpinBox, QApplication, QComboBox, QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel,
    QListWidget, QPushButton, QSizePolicy, QToolButton, QVBoxLayout, QWidget,
)

from . import anim, style

_QWIDGETSIZE_MAX = 16777215                        # Qt's max size -- 'release the height pin' so a widget tracks content

# The gap BETWEEN cards (see `section`). The card draws its own boundary, so this gap does not have to
# carry the grouping by itself -- but it must still clearly exceed the 8px gap between rows INSIDE a card,
# or the page reads as one undifferentiated stack. 14 sits between the old 10 and the borderless 24.
# DELIBERATELY OFF-GRID, and the one number here that is: the grid's neighbours are 12 (too close to the
# 8px in-card row gap to read as a different KIND of gap) and 16 (which ties the card's own 16px interior
# padding, so a card would sit as far from its neighbour as its content sits from its own edge). The grid
# does not have to own every number -- it has to stop numbers being anonymous. This one has a reason.
SECTION_GAP = 14

# A form doc's PAGE padding -- the frame around the scrolling column of cards. One rung above the card's
# own 16px interior (widgets.section), so the page frame reads as the outer container rather than tying
# it: 24 outside, 16 inside. Applies to the form docs (Build & Deploy / Import / Co-op: a single scrolling
# column, no splitter). NOT to the splitter browsers (Models / Battle), where the panes are the page and
# edge-to-edge is the convention -- an outer margin there just eats pane width.
PAGE_PAD = style.space("space_6")


# A container that must not paint the page colour over what is behind it. THE EXACT-CLASS SELECTOR IS
# LOAD-BEARING: a bare `setStyleSheet("background: transparent;")` has an implicit universal selector,
# and a widget sheet out-ranks the app sheet regardless of specificity -- so it cascades down and beats
# `QPushButton#accent { background: $accent }`, leaving accent-fg ink on the bare page. Home's
# get-started CTA shipped that way once (1.00:1 in dracula/gruvbox -- shell.py carries the full
# history)... and then `page_column` below RECOMMITTED the bare form and silently unfilled EVERY
# button -- accent, default and quiet -- on all three form docs for two rounds. Nobody saw it because
# a default button's ink is $text (light on dark, readable on the bare page); the accent tier's dark
# ink was the tell, found by the round-9 co-op snaps. `.QWidget` matches a plain QWidget and NOT its
# subclasses, so a container goes transparent while every real control keeps its styling.
TRANSPARENT = ".QWidget { background: transparent; }"


# THE PAGE COLUMN. Home has always had one -- `body.setMaximumWidth(860)`, centred -- and the form docs
# never did, so their cards stretched to the window: measured 640 / 1102 / 1136 at a 1920 window.
#
# That was invisible until COLUMN gave the hints a real measure. A correct 380px hint inside an 1102px
# card reads at 3:1 -- a narrow ribbon stranded in a wide pane -- and the instinct is to widen the hint.
# That instinct is wrong and the arithmetic says so: 480px reads 94 characters to the line, back over the
# 75 ceiling. THE HINT WAS NEVER TOO NARROW; THE PAGE WAS TOO WIDE. A reading column is the fix, and the
# app already had one and only spent it on one screen.
#
# 860, the same number Home uses, for the reason a shared number is better than a defensible one: the two
# surfaces are the same kind of thing (a scrolling column of cards you read), and a page that is 860 here
# and 900 there has no column at all -- it has two opinions.
PAGE_W = 860


def page_column(host):
    """Home's centred reading column, for a form doc. Returns the layout to build the page INTO.

    Replaces the bare `QVBoxLayout(inner)` the three form docs each built. The sandwich is
    ``host -> centring row -> capped column -> your layout``, and the host still fills the scroll area
    (``setWidgetResizable(True)`` requires that) while the column inside it does not.

    THE STRETCH IS 20, NOT 4, AND HOME'S COMMENT IS THE RECEIPT -- this is a copied solution, not a
    copied number. At 4:1:1 the column takes 4/6 of the width, which targets 435px at the 1280 default;
    Home's was rescued only by its own 512px minimumSizeHint, which is itself propped up by
    un-word-wrapped labels. So the moment a round wrapped those labels the column would silently collapse
    to ~398. Factor 20 pins it to the cap as early as geometry allows: 604 at 1280, 860 from 1600.

    (That trap is now LIVE for these docs and was not before: COLUMN just wrapped every hint on them.)
    """
    row = QHBoxLayout(host)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(0)
    row.addStretch(1)
    col = QWidget()
    col.setStyleSheet(TRANSPARENT)                  # the universal QWidget{background-color:$bg} rule would
    #                                                 otherwise paint the page colour over the scroll's ground
    #                                                 (EXACT-CLASS, never the bare form -- see TRANSPARENT above)
    col.setMaximumWidth(PAGE_W)
    row.addWidget(col, 20)
    row.addStretch(1)
    v = QVBoxLayout(col)
    page_margins(v)
    v.setSpacing(SECTION_GAP)
    return v


def fit_dialog(dlg, *, ch=64, list_rows=12, lines=0) -> None:
    """TAILOR -- size a modal from its CONTENT, in text units, clamped to the screen.

    THE LAW: A POPUP'S SIZE IS A FUNCTION OF ITS CONTENT, AND A PX CONSTANT IS NOT A FUNCTION.
    Two failure modes shipped side by side, one per direction:

      * no size at all -- Qt sums the children's sizeHints, and a QLineEdit's hint is ~17 characters
        while a QListWidget's is 256x192 REGARDLESS of its rows. Measured: New Campaign opened 309px
        wide with its Folder path truncated to "-mestorf-205c97"; the FF9 region catalog showed 6 of
        its regions behind two scrollbars in a 385x409 box.
      * resize(W, H) -- right for one font at one scale, and DEAF to the CALIBRE text dial by
        construction (the same deafness style.py documents for setFixedSize: a px constant cannot
        hear a font change).

    So the dialog asks for ``ch`` characters of its own POLISHED body font (the QSS base rule puts
    $type_body on every QWidget, so the metric moves with the dial and the fence can assert the
    relationship instead of a number); each populated QListWidget asks to show its real content up to
    ``list_rows`` rows wide enough for its longest row; ``lines`` (optional) asks for that many text
    lines of height for viewer dialogs whose content arrives after open. Everything is clamped to the
    available screen, so 150% text means a proportionally wider dialog on a monitor with the room --
    never a clipped one.

    Call it AFTER the layout is built (it reads the children), on a dialog PARENTED into the
    Workspace: the base font arrives via the parent chain, and an ORPHAN dialog would measure Qt's
    default font instead of the app's. Widths set here are MINIMUMS -- content that needs more still
    gets more, and the user can still resize.
    """
    dlg.ensurePolished()
    fm = QFontMetricsF(dlg.font())
    screen = dlg.screen() or QApplication.primaryScreen()
    avail = screen.availableGeometry() if screen is not None else None
    max_w = int(avail.width() * 0.92) if avail is not None else 4000
    max_h = int(avail.height() * 0.85) if avail is not None else 3000
    lay = dlg.layout()
    m = lay.contentsMargins() if lay is not None else dlg.contentsMargins()
    want_w = round(fm.averageCharWidth() * ch) + m.left() + m.right()
    dlg.setMinimumWidth(min(want_w, max_w))
    if lines:
        dlg.setMinimumHeight(min(round(fm.height() * lines) + m.top() + m.bottom(), max_h))
    fitted = []
    for lst in dlg.findChildren(QListWidget):
        if not lst.count():
            continue
        lst.ensurePolished()
        frame = 2 * lst.frameWidth()
        # The v-scrollbar allowance is unconditional: when the list DOES overflow list_rows, the bar
        # must not steal width from the longest row (that is the h-scrollbar the old box grew).
        col = lst.sizeHintForColumn(0) + frame + lst.verticalScrollBar().sizeHint().width() + 8
        lst.setMinimumWidth(min(col, int(max_w * 0.9)))
        row_h = lst.sizeHintForRow(0)
        if row_h > 0:
            rows = min(lst.count(), int(list_rows))
            lst.setMinimumHeight(min(rows * row_h + frame + 4, int(max_h * 0.7)))
            fitted.append((lst, row_h, frame))
    # A SQUEEZED DIALOG DOES NOT SHRINK, IT OVERPAINTS: a word-wrapped QLabel (height-for-width) draws
    # its FULL text whatever rect the layout squeezed it into -- measured at 150%, the region catalog's
    # footer painted straight across the list. So the height that does not fit the screen is given back
    # by the LIST (it scrolls; prose does not), never by squeezing, and never via adjustSize() -- which
    # silently caps a window to ~2/3 of the screen and thereby CAUSES the squeeze it should prevent.
    over = dlg.sizeHint().height() - max_h
    if over > 0 and fitted:
        share = round(over / len(fitted))                   # split the deficit, don't charge it to each list
        for lst, row_h, frame in fitted:
            floor = 4 * row_h + frame + 4                  # never fewer than 4 visible rows
            lst.setMinimumHeight(max(floor, lst.minimumHeight() - share))
    hint = dlg.sizeHint()
    dlg.resize(min(hint.width(), max_w), min(hint.height(), max_h))


def notice(text="", *, kind="", parent=None):
    """A REPORT: something the app is telling you went wrong, or nearly did.

    DICTION's other half. A notice is not a hint and the difference is not importance, it is POSTURE: a
    hint is READ (prose you consult), a notice is GLANCED (you are interrupted by it). They had been the
    same tier -- `role="caption"` with a `state` -- which put every error at the caption rung, in grey's
    little sibling, breaking a law the sheet had written down four lines above the offending rule.

    Body rung, state-coloured, and NEVER smaller than the field it is about. `kind` is "" / "warn" /
    "error". Deliberately NOT capped to a measure: a notice is one line you glance at, and a wrapped
    column would make it prose.
    """
    lab = QLabel(text, parent)
    lab.setProperty("role", "notice")
    if kind:
        lab.setProperty("state", kind)
    lab.setWordWrap(True)
    if text:
        lab.setAccessibleName(text)
    return lab


def page_margins(lay) -> None:
    """Apply the page rung to a form doc's page-level layout.

    One definition, three call sites: the three form docs had drifted to 16 / 16 / (18,14,18,18), which
    is the whole reason this is a function and not a number typed three times.

    NB: comfortable-only. Layout density fan-out is not wired -- the docs are constructed without knowing
    the density, and threading it through every doc + `_apply_density` + `_finish`'s Cancel path is a
    separate job. `style.space` takes a density for when it is.
    """
    lay.setContentsMargins(PAGE_PAD, PAGE_PAD, PAGE_PAD, PAGE_PAD)


class WheelGuard(QObject):
    """App-wide event filter: ignore the mouse wheel on an UNFOCUSED combo / spin box.

    Qt's combos and spin boxes change their value on ``wheelEvent`` while merely HOVERED, so scrolling a
    tall panel silently flips whatever control the cursor passes over -- a genuine data hazard on the save
    editors (5 combos stacked in a scroll area) and a friction everywhere else. Installed once on the
    QApplication, a stray wheel over an unfocused control is dropped; the control only responds to the
    wheel once the user has clicked or tabbed INTO it. One install covers every combo -- present and
    future -- with no per-widget wiring.

    Deliberately guards only ``QComboBox`` / ``QAbstractSpinBox``: sliders and (crucially) scroll bars are
    ``QAbstractSlider``s that MUST keep their wheel, so they are left alone. Trade-off: a wheel directly
    over an unfocused combo is consumed (the panel won't scroll under that exact footprint) -- which is why
    the combos are also kept narrow; scroll in the surrounding space.
    """

    _GUARDED = (QComboBox, QAbstractSpinBox)

    def eventFilter(self, obj, ev):                # noqa: N802 (Qt override)
        if ev.type() == QEvent.Type.Wheel and isinstance(obj, self._GUARDED) and not obj.hasFocus():
            ev.ignore()
            return True
        return False


class PlaceholderListWidget(QListWidget):
    """A QListWidget that paints a muted hint while it is empty (the QLineEdit-placeholder idiom, which
    plain list views lack) -- so an empty Problems panel says what will appear there instead of sitting as
    a silent grey box. Set ``placeholder`` / ``placeholder_color`` (a '#rrggbb' string) any time; the
    shell's retheme updates the colour.

    ``color`` IS REQUIRED, and used to default to ``"#808080"``. All three real call sites pass
    ``pal["muted"]``, so that default never fired -- it was dead, and loaded: a palette-blind grey that any
    fourth call site would have picked up silently, landing sub-AA on most of the 8 grounds. The sibling
    law is that a defensive default whose value IS the shipped behaviour is not a default but the code; a
    default that can never fire is the same coin's other face -- it reads as a convenience and is really an
    unexploded one. This widget paints with QPainter, where no QSS rule and no fence can reach it."""

    def __init__(self, placeholder, color, parent=None):
        super().__init__(parent)
        self.placeholder = placeholder
        self.placeholder_color = color

    def paintEvent(self, ev):                      # noqa: N802 (Qt override)
        super().paintEvent(ev)
        if self.count() == 0 and self.placeholder:
            painter = QPainter(self.viewport())
            painter.setPen(QColor(self.placeholder_color))
            rect = self.viewport().rect().adjusted(12, 8, -12, -8)
            painter.drawText(rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
                             | Qt.TextFlag.TextWordWrap, self.placeholder)
            painter.end()


# --- component factories (Phase 1 token foundation) ----------------------------------------
# Thin QLabel/QFrame factories that stamp a dynamic `role` property (styled by the component QSS in
# workspace.style) and fold in an accessible name -- so a heading / caption / card / chip is ONE call
# with the a11y hook baked in, replacing the ad-hoc inline stylesheets adopted incrementally from Phase 2.

def role_label(text="", role="body", *, parent=None):
    """A QLabel carrying a ``role`` (display / h1 / h2 / caption / subtle / chip) for the component QSS,
    with its text as the accessible name."""
    lab = QLabel(text, parent)
    lab.setProperty("role", role)
    if text:
        lab.setAccessibleName(text)
    return lab


def caption(text="", *, parent=None, width=None):
    """THE HINT. The app's explaining tier -- and now the only way to build one.

    COLUMN. This returned a bare `role_label`: no wrap, no cap, no measure. 37 sites built their hints by
    hand instead (`QLabel(...)`, `setWordWrap(True)`, `setProperty("role", "caption")`), and a wrapped
    QLabel with no maximumWidth takes whatever the pane hands it. Measured live on the real labels, the
    Import hints ran **103 ch/line at a 1280 window, 198 at 1920, 314 at 2560** -- growing 1:1 with the
    monitor, against a 45-75 band. The tier whose whole job is to explain the app to a newcomer was the
    least readable text in it, and the wider your screen the worse it got.

    Returns a :class:`Prose`, so a hint now gets all three things the hand-rolled version could not:
      * a real measure (CAPTION_W, resolved against the CAPTION rung -- see GAUGE),
      * the silent-clip fix (a raw setMaximumWidth on a wrapped QLabel CLIPS -- see Prose),
      * and the text-size dial (the cap scales with the font; the column holds its character count).

    NOT for a fixed-height note. `Prose` wraps, and wrapping inside a `setFixedHeight` clips -- silently.
    The two such sites (forms_qt's overflow note and preview footer) keep bare labels ON PURPOSE and say
    so at their own call sites.
    """
    p = Prose(text, CAPTION_W if width is None else width, parent, base="caption")
    p.setProperty("role", "caption")
    if text:
        p.setAccessibleName(text)
    return p


class NameLabel(QLabel):
    """The screen's subject, at display size, elided to fit instead of forcing a horizontal scroll.

    A 26px name of an arbitrary user string (a field id, a campaign title, a save path) can be far wider
    than the pane. Qt's default is to demand its full width, so the pane grows a horizontal scrollbar and
    the whole doc gets wider than the window.

    THE TRAP, and why the sizeHint is deliberately NOT the elided text: eliding inside ``resizeEvent`` is
    a classic infinite relayout -- shorten the text, the hint shrinks, the layout re-runs, the widget
    resizes, elide again. It is avoided here by PINNING ``sizeHint`` to the FULL string and never letting
    it move. The layout's question ("how much do you want?") always gets the same answer, so eliding can
    never trigger a relayout. ``minimumSizeHint`` returns the width of a single ellipsis, so the widget
    yields all the way down rather than pushing a scrollbar.

    ``QLabel::paintEvent`` is kept on purpose -- no custom paint. The full text must survive in
    ``accessibleName`` and the tooltip, which a QPainter-drawn string cannot do.
    """

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._full = text
        self.setProperty("role", "name")
        self.setText(text)
        self.setAccessibleName(text)
        self.setToolTip(text)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)

    def setFullText(self, text: str) -> None:
        self._full = text
        self.setAccessibleName(text)
        self.setToolTip(text)
        self._relayout_free_elide()
        self.updateGeometry()

    def sizeHint(self):                       # PINNED to the full string -- see the class docstring
        fm = self.fontMetrics()
        return QSize(int(fm.horizontalAdvance(self._full)) + 2, fm.height())

    def minimumSizeHint(self):                # yield to the pane; never push a horizontal scrollbar
        fm = self.fontMetrics()
        return QSize(int(fm.horizontalAdvance("…")) + 2, fm.height())

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._relayout_free_elide()

    def _relayout_free_elide(self):
        fm = self.fontMetrics()
        w = max(0, self.width() - 2)
        super().setText(fm.elidedText(self._full, Qt.TextElideMode.ElideRight, w) if w else self._full)


def nameplate(kicker: str, name: str, note: str = "", *, parent=None):
    """A screen's crown: a quiet KICKER, the subject's NAME at display size, and an optional note.

    The app already computed both halves of this and posted each to the wrong address -- the SUBJECT went
    to a 24-char-truncated tab label while the BREADCRUMB was stamped as the panel's header. The kicker is
    the breadcrumb's job (where you are); the name is the tab's (what this is).

    Returns ``(widget, name_label)`` so a caller can re-point the name later without rebuilding the row.
    """
    host = QWidget(parent)
    v = QVBoxLayout(host)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(2)
    if kicker:
        v.addWidget(role_label(kicker, "overline"))
    lab = NameLabel(name, host)
    v.addWidget(lab)
    if note:
        v.addWidget(prose(note))
    rule = QFrame(host)
    rule.setFrameShape(QFrame.Shape.HLine)
    rule.setFixedHeight(1)
    v.addSpacing(style.space("space_1"))
    v.addWidget(rule)
    return host, lab


def card(*, parent=None):
    """An elevated container frame (surface_2 + a rounded border) for grouped content."""
    frame = QFrame(parent)
    frame.setProperty("role", "card")
    return frame


# THE MEASURE. A px cap is NOT a measure -- it is a measure only for ONE font size, which is why there are
# two of these and why there had to be. Measured on a NATIVE font DB (offscreen stubs it and inflates
# advances 2-3x -- that artifact is how an earlier round invented a horizontal-scroll emergency):
#
#     13px Segoe UI, real prose:  ~5.59-5.72 px/char
#     11px Segoe UI, real prose:  ~4.73-4.84 px/char
#
# So ONE 620px cap is ~109 chars at 13px and ~130 at 11px: the same number is WORSE on the smaller face,
# which is the whole receipt for splitting the token. The classic readable band is 45-75ch.
#
# 420, not 430: at the worst measured rate (5.72) a 430 cap lands 75.2ch and fails its own fence by a
# fifth of a character. 420 gives 73.4-75.1. Fenced by test_prose_w_is_a_real_measure.
PROSE_W = 420          # ...OF BODY-RUNG TEXT. See _BASE below -- that clause is the whole of GAUGE.

# The 11px caption face, and DELIBERATELY still 620 -- an unchanged number, not an oversight.
#
# It is the value reviewed and approved on Build & Deploy and Co-op, and at 11px the real captions are
# ~107-112 chars, so the cap does not even bind: they render as single lines and lowering it would re-wrap
# every one of them. That is a design call needing an eye, not a bug fix -- so this phase SPLITS the token
# (the 13px face gets its real measure) and moves the 11px face zero pixels. The receipt above is recorded
# so a future round can act on it deliberately rather than discover it again.
# 380, and 620 was never a measure -- COLUMN retires it. Measured on all 23 REAL caption strings, on the
# labels the app actually builds, at the real 12px rung (rate band 5.113-5.661 px/char):
#
#     620px -> 121 ch/line   62% OVER the 75 ceiling, EVEN WHERE IT BINDS
#     420px ->  82 ch        still over
#     380px ->  74.3 ch      the widest cap that holds <=75 on EVERY real caption
#
# The ceiling is set by the NARROWEST rate (fewest px per char = most characters on the line), so 5.113
# is what 380 is chosen against -- not the median, which would let the tightest strings run over.
# 380 @ 12px holds 74.3ch; PROSE_W 420 @ 14px holds 71.9. The same posture, one rung down.
#
# THE 620 HAD TWO DEFENCES AND BOTH WERE FALSE. It was called "the reviewed-and-approved value" -- the
# approval was real, but it was given to PROSE_W at 13px; LEDE cut prose to 420 and moved the 620 onto
# the caption rung, where the same number is strictly worse, and the fence kept citing the approval for a
# tier it was never granted to. And it was called inert ("the cap does not bind") -- true only because
# `option()` is 3 of 37 caption sites and its strings are short. The instant a real hint is capped by it,
# 620 renders 121 characters to the line.
CAPTION_W = 380

# GAUGE. Both numbers above are the APPROVED design and NEITHER moves here -- what changes is that they
# stop being "420px" and become "420px OF 14px TEXT". A px cap is a measure for exactly ONE font size;
# this module has said so, at length, since the tokens split, and then defined two px constants anyway.
# CALIBRE's dial made the comment's own point: at 150% the letters grew and the column did not.
#
# THE FIX IS TO SCALE, NOT TO RE-DERIVE -- and that is not a shortcut, it is exact. Segoe's advance is
# LINEAR in pixel size (measured 12..28px: max error 0.065%, evidence/probe_measure_rate.py), so
#
#       chars = (cap * k) / (rate * k) = cap / rate
#
# the measure in CHARACTERS is INVARIANT under scaling. Widen the column exactly as fast as the letters
# grow and the line still holds the same number of them. Re-deriving a cap from a "characters" target
# would instead need a calibrated rate, and every honest candidate misses 420: averageCharWidth reads
# 5.953 at 13px, ABOVE every real string in this app (5.42-5.89), because it averages a glyph set nobody
# types. Scaling needs no rate at all.
#
# THE MEASURE WAS NEVER THE DEFECT THE ROUND EXPECTED, and the numbers are worth keeping because two
# instruments lied about them first:
#   * A synthetic rate (the bare alphabet) said 61.9ch -- "comfortably fine". It has ONE space in 27
#     where English has ~1 in 6, and the space is the narrowest glyph in the face, so it overstates
#     px/char and understates the measure by ~9%.
#   * Round 5's audit said 77.5ch -- "already out of band". True at the time, at the 13px body.
#   Measured on the REAL strings at the REAL rung: 420px is 67.6-71.9ch. QUARTO P1 FIXED IT BY ACCIDENT:
#   raising the body 13 -> 14 NARROWS the measure in characters, because every character got wider.
#   And at 150% it reads 45.0ch -- exactly ON the 45 floor, passing with zero headroom, by luck.
#
# So GAUGE ships for the reason that survived: nothing could TELL. The old fence divided a constant by a
# constant (WORST_13PX = 5.72, a rate from a font size the app no longer sets) and could not see the app
# at all. The measure held at every dial setting by accident, and nobody would have known when it stopped.
_BASE = {"prose": "type_body", "caption": "type_caption"}


class Prose(QLabel):
    """A word-wrapped label with a REAL measure cap.

    A raw ``setMaximumWidth`` on a wrapped QLabel silently CLIPS: ``QBoxLayout::calcHfw`` asks
    ``heightForWidth()`` at the full CELL width (say 900px -> "2 lines please"), then lays the label out at
    its capped 620px, where the text actually needs 4. The bottom two lines are cut off. Overriding
    ``heightForWidth`` to answer for the *capped* width -- never the cell's -- is what makes the cap honest.

    Do NOT "fix" this with an HBox + addStretch wrapper: that collapses the label to its sizeHint (its
    natural single-line width) and throws the measure away entirely.
    """

    def __init__(self, text="", width=PROSE_W, parent=None, base="prose"):
        super().__init__(text, parent)
        self._base_cap = width
        self._base_px = style.type_px(_BASE[base], 100)   # the rung `width` was chosen against
        self._cap = width
        self.setWordWrap(True)
        self.setMaximumWidth(width)
        self._resolve_cap()

    def _resolve_cap(self):
        """Re-resolve the px cap against the font this label is ACTUALLY wearing.

        The label does not need to be told the text-size scale, and deliberately is not: it reads its own
        polished font, so it is right no matter WHO changed the type -- the dial, a density switch, a
        stylesheet a future round has not written yet. A cap threaded from the shell would be a second
        source of truth for the same fact, and the two would drift the first time one of them was missed.

        BOTH sources, in this order, and each covers the other's blind spot:

        * ``QFont.pixelSize()`` is the EXPLICIT size. The stylesheet sets `font-size: 21px`, so this is 21
          -- exact, and available even where the font DB is stubbed.
        * ``QFontInfo.pixelSize()`` RESOLVES a font that carries a point size instead (the Windows system
          font is Segoe UI 9pt and reports QFont.pixelSize() == -1). Multiply a cap by -1 and every Prose
          in the app collapses to a negative width.

        Neither alone is enough, and the discovery cost a wrong fence: under QT_QPA_PLATFORM=offscreen --
        which is how the whole suite runs -- QFontInfo returns -1 even for a font with an explicit
        pixelSize, because offscreen stubs the font engine QFontInfo asks. A QFontInfo-only version
        therefore fell back to k=1.0 for every test, held the cap at 420 forever, and the fence written to
        catch exactly that failure reported it as a pass. The harness lies about fonts; it lies here too.
        """
        px = self.font().pixelSize()                      # explicit (QSS px) -- survives the stub
        if px <= 0:
            px = QFontInfo(self.font()).pixelSize()        # resolved (a point-size font, e.g. Segoe 9pt)
        k = px / self._base_px if px > 0 and self._base_px > 0 else 1.0
        cap = int(self._base_cap * k + 0.5)               # k == 1.0 at 100% -> the approved px, exactly
        if cap == self._cap:
            return
        self._cap = cap
        self.setMaximumWidth(cap)
        self.updateGeometry()

    def changeEvent(self, ev):                     # noqa: N802 (Qt override)
        # FontChange is the signal the stylesheet cannot send: QSS re-renders the sheet, Qt re-polishes
        # the label, and THIS fires. Without it the cap would be correct only for whatever scale happened
        # to be set when the widget was constructed -- and these are built once, at startup.
        if ev.type() == QEvent.Type.FontChange:
            self._resolve_cap()
        super().changeEvent(ev)

    def heightForWidth(self, w):                   # noqa: N802 (Qt override)
        return super().heightForWidth(min(w, self._cap))

    def sizeHint(self):                            # noqa: N802 (Qt override)
        s = super().sizeHint()
        s.setWidth(min(s.width(), self._cap))
        s.setHeight(self.heightForWidth(self._cap))
        return s


def prose(text, width=PROSE_W, *, parent=None):
    """A wrapped sentence held to a readable measure (see :class:`Prose`)."""
    return Prose(text, width, parent)


OPT_INDENT = 30    # the radio/checkbox TEXT column, so a caption lines up under the label and not under
                   # the indicator. MEASURED: style().subElementRect(SE_RadioButtonContents).x(), identical
                   # in both densities. Do NOT derive it arithmetically from the indicator width + spacing
                   # -- that lands a pixel out (the plan said 31), because QSS puts the indicator's border
                   # OUTSIDE its width and the control carries its own padding.


def option(rb, description, lay, *, width=CAPTION_W):
    """A choice is a NAME; its consequence is a caption BENEATH it, on the label's own column.

    The third law: never put prose inside a widget. `QRadioButton("Test slot 4003 -- quick + reversible;
    play via ~ -> Warp  (or New Game -> hut door)")` is a label doing a description's job -- it makes every
    option the same visual weight as its own explanation, so nothing on the card can be scanned. Split it:
    13px `$text` for what you pick, 11px `$muted` for what it means.

    The caption is a `Prose` (not a raw wrapped QLabel with a maximumWidth) because it is NESTED, and a
    nested wrapped label with a raw cap silently clips -- see :class:`Prose`.

    Also sets the radio's accessible DESCRIPTION, so a screen reader still reads the consequence that used
    to live in the label. (Name = the choice; description = the caption. That is the correct split.)
    """
    lay.addWidget(rb)
    if description:
        # base="caption": CAPTION_W was chosen against the 12px caption rung, not the 14px body. Passing
        # the wrong base here would not be a rounding error -- it would scale this cap by 14/12 at every
        # setting, silently, including at 100%.
        cap = Prose(description, width, base="caption")
        cap.setProperty("role", "caption")
        cap.setContentsMargins(OPT_INDENT, 0, 0, 6)
        lay.addWidget(cap)
        rb.setAccessibleDescription(description)
        rb.description_label = cap
    return rb


class _KvKey(QLabel):
    """The key column of a definition list, sized from its OWN polished font.

    kv() first took a px ``key_width`` the CALLER measured at construction -- i.e. in whatever font the
    widget wore BEFORE the QSS landed, and never again. At a 150% text dial the keys rendered wider than
    their frozen column and Qt clipped them mid-word ("gameC:", "enginnetsync" -- the round-9 snaps).
    Same law as GAUGE/fit_dialog: a width computed from a font must be recomputed when the font changes,
    and the only widget that reliably hears that is the one wearing it (FontChange).
    """

    _PAD = 14

    def __init__(self, text, widest):
        super().__init__(text)
        self._widest = widest
        self._fit()

    def _fit(self):
        self.setFixedWidth(round(self.fontMetrics().horizontalAdvance(self._widest)) + self._PAD)

    def changeEvent(self, ev):                         # noqa: N802 (Qt override)
        super().changeEvent(ev)
        if ev.type() == QEvent.Type.FontChange:
            self._fit()


def kv(key, lay, *, widest, mono=False, placeholder="…"):
    """One row of a definition list: a MUTED key in a fixed column, the value beside it.

    `game: C:\\Program Files (x86)\\...` as a single 13px label makes the key and the answer the same
    weight, so four such rows are a wall you read linearly instead of a table you scan. Splitting them
    puts the labels in one muted column and the answers in another at full weight -- the key names the
    question, the value IS the information.

    ``widest`` is the longest key STRING in the list (not a px width -- see :class:`_KvKey`): every row
    passes the same string, so every value lands on one left edge at any text scale.

    ``mono`` is for values that are machine tokens (a path, an id) -- NOT for prose. Mono on a sentence
    reads as a bug.

    Returns the VALUE label. Callers keep their existing ``self.lbl_x.setText(...)`` sites; they just stop
    writing the ``"key: "`` prefix into the text.
    """
    row = QHBoxLayout()
    row.setSpacing(0)
    k = _KvKey(key, widest)
    k.setProperty("role", "muted")
    if key:
        k.setAccessibleName(key)
    k.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
    val = QLabel(placeholder)
    val.setWordWrap(True)
    if mono:
        val.setProperty("mono", True)
    val.setAccessibleName(key)          # a screen reader still hears "game" for this value
    row.addWidget(k)
    row.addWidget(val, 1)
    lay.addLayout(row)
    val.key_label = k
    return val


def set_state(label, state=""):
    """Set a label's ``state`` (``""`` / ``warn`` / ``error``) and restyle it.

    ``setProperty`` alone does NOT re-evaluate the QSS -- a status line would keep its old colour. Always
    pair them; that is what this exists for.
    """
    label.setProperty("state", state)
    repolish(label)
    return label


def section(title, *, parent=None):
    """A titled CARD -- the QGroupBox replacement.

    The card stays: it is a genuinely useful logical section indicator, and the measurements say the box
    was never the problem. What was ugly is specific and fixable:

    1. **The caption sat ON the border**, breaking the stroke around itself -- the Win32 ``fieldset``
       idiom every modern design language dropped. It is also the one thing QSS cannot fix: ``font-*`` on
       ``QGroupBox::title`` is silently ignored (colour is its only lever), so the title could never be
       given weight while Qt was drawing it. Hence a real QLabel, INSIDE the card, at the top.
    2. **The title had no presence** -- ``$muted`` at the same 13px as the body it labelled. Now the
       11px/600/+1px-tracking overline role, which reads as a marker rather than as weak body text.
    3. **No horizontal padding** (``style.py``: "NB: no left/right padding") -- content ran to the edge.
       That amputation was defending against an h-scroll bug that never existed at the claimed magnitude
       (the offscreen QPA inflates text advances 2-3x; the widest real control is 642px against ~1080px
       of pane). Padding restored.

    NOT changed: the fill. ``surface_2`` on ``bg`` measures 1.31 in DARK -- a *stronger* step than
    GitHub's dark card (1.09). The elevation was fine; the research's "the fills do nothing" measured
    ``surface -> surface_2`` (1.17), which is not the pair a card on a page is seen against.

    Call shape mirrors :func:`disclosure` (the established idiom here)::

        st = widgets.section("Status")      # was: st = QGroupBox("Status")
        sv = st.content_layout              # was: sv = QVBoxLayout(st)
        sv.addWidget(...)                   # unchanged
        v.addWidget(st)                     # unchanged

    The title is upper-cased at the call site because Qt has no ``text-transform``.

    **Pair every adoption with a name.** Qt derives an unnamed control's screen-reader name from its
    enclosing QGroupBox TITLE; a card has no title for it to find, so any control that was leaning on the
    box goes silent. Give each one a ``setBuddy(label)`` (better names than the box gave anyway).
    """
    box = QFrame(parent)
    box.setProperty("role", "card")                  # $surface_2 + $radius_lg + a 1px $border edge
    v = QVBoxLayout(box)
    v.setContentsMargins(16, 12, 16, 16)             # the padding the fieldset never had
    v.setSpacing(10)                                 # title -> its rows
    # RUBRIC: the body rung, 600, $text -- a real size step AND a colour step over the hint text inside the
    # card. Was role="overline" (the caption rung, $muted), which made a card's title exactly the size and
    # colour of its own footnotes. See style.py's cardtitle rule for the full receipt.
    #
    # The .upper() goes with it, and the two are coupled rather than a separate taste call: uppercase +
    # letter-spacing is an EYEBROW convention, and it works because it is small. At the body rung it reads
    # as a shout. Measured, dropping it also makes the six longest real titles 12.7-16.2% NARROWER, so the
    # size bump costs no width -- it pays for itself. setAccessibleName stays: it is now redundant with the
    # visible text, which is the point -- a screen reader and the screen finally say the same thing.
    lab = role_label(title, "cardtitle")
    lab.setAccessibleName(title)
    v.addWidget(lab)
    # The content host is a LAYOUT, never a wrapper QWidget. The stylesheet opens with a universal
    # `QWidget { background-color: $bg; }`, so a bare QWidget in here paints the PAGE colour on top of the
    # card's fill -- a visible darker rectangle inside every card, i.e. the exact box-in-box this is meant
    # to kill. It hides on a borderless section (bg on bg) and only surfaces once the card has a fill.
    body_lay = QVBoxLayout()
    body_lay.setContentsMargins(0, 0, 0, 0)
    body_lay.setSpacing(8)
    v.addLayout(body_lay)
    box.content_layout = body_lay
    box.title_label = lab
    return box


def status_chip(text, kind="info", *, parent=None):
    """A small pill label. ``kind`` (info / good / warn / crit) is stamped as a property for later
    per-kind tinting; the accessible name names the kind, so status never rides on colour alone."""
    lab = role_label(text, "chip", parent=parent)
    lab.setProperty("kind", kind)
    if text:
        lab.setAccessibleName(f"{kind}: {text}")
    return lab


def empty_state(glyph, purpose, *, teach=None, actions=(), parent=None, icon_pixmap=None):
    """A centered TEACHING empty-state -- the antidote to a black void / a bare "nothing loaded" panel:
    a large decorative icon/glyph, a one-line purpose, an optional teaching sentence, and optional
    primary-action button(s). ``actions`` is an iterable of ``(label, callback)`` (falsy entries are
    skipped, so a caller can gate one on availability); the first surviving action is accented as the
    primary. ``icon_pixmap`` (Phase 8) shows an SVG icon instead of the text ``glyph``; either way the
    mark is decorative (no accessible name) -- the purpose + teach lines carry the meaning for a screen
    reader. Returns a QWidget ready to drop into any empty host layout."""
    w = QWidget(parent)
    v = QVBoxLayout(w)
    v.setContentsMargins(24, 24, 24, 24)
    v.setSpacing(8)
    v.addStretch(1)
    g = role_label("", "empty_glyph") if icon_pixmap is not None else role_label(glyph, "empty_glyph")
    if icon_pixmap is not None:
        g.setPixmap(icon_pixmap)
    g.setAlignment(Qt.AlignmentFlag.AlignCenter)
    g.setAccessibleName("")                             # decorative -- don't announce the glyph/icon
    v.addWidget(g)
    p = role_label(purpose, "empty_title")
    p.setAlignment(Qt.AlignmentFlag.AlignCenter)
    p.setWordWrap(True)
    v.addWidget(p)
    if teach:
        t = caption(teach)
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setWordWrap(True)
        t.setMinimumWidth(380)                          # a word-wrapped label between stretches collapses to
        t.setMaximumWidth(460)                          # its hint width -- pin a readable measure (~2 lines)
        trow = QHBoxLayout()
        trow.addStretch(1)
        trow.addWidget(t)
        trow.addStretch(1)
        v.addLayout(trow)
    acts = [a for a in actions if a]
    if acts:
        brow = QHBoxLayout()
        brow.addStretch(1)
        for i, (label, cb) in enumerate(acts):
            b = QPushButton(label)
            if i == 0:                                  # the first action is the primary -> accented
                b.setObjectName("accent")
            if cb is not None:
                b.clicked.connect(lambda _=False, c=cb: c())
            brow.addWidget(b)
        brow.addStretch(1)
        v.addLayout(brow)
    v.addStretch(1)
    return w


def attach_shadow(widget, *, blur=32, dy=8, alpha=110):
    """Give a FLOATING layer (a Ctrl-K palette card, a frameless popover) real depth via a
    QGraphicsDropShadowEffect. Apply to a ROUNDED card that sits inside a transparent, margined host so the
    blur has room to spill and the rounded corners don't bleed a hard rectangle (Report F-§2). No-op-safe:
    returns the widget. Not for native top-level menus/dialogs -- those already get an OS shadow on Windows."""
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(blur)
    eff.setXOffset(0)
    eff.setYOffset(dy)
    eff.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(eff)
    return widget


def disclosure(title, *, expanded=False, parent=None):
    """A collapsible 'advanced' section (progressive disclosure): a flat toggle header (▸/▾ + ``title``) over
    a hidden-by-default content area. The caller fills ``box.content_layout``; ``box.toggle_button`` is the
    header. Reusable for the Import secondary jobs + the Build advanced drawer -- keeps the routine path front
    and centre while the power-user controls stay one click away."""
    box = QWidget(parent)
    v = QVBoxLayout(box)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(0)
    btn = QToolButton()
    btn.setObjectName("disclosureToggle")
    btn.setCheckable(True)
    btn.setChecked(expanded)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setText(("▾  " if expanded else "▸  ") + title)
    btn.setAccessibleName(title)
    body = QWidget()
    body_lay = QVBoxLayout(body)
    body_lay.setContentsMargins(2, 6, 0, 0)
    body_lay.setSpacing(8)
    body.setVisible(expanded)

    def _toggle(on):
        btn.setText(("▾  " if on else "▸  ") + title)
        if on:                                          # expand: reveal, then grow 0 -> content height,
            body.setVisible(True)                       # then release the pin so it tracks content again
            target = max(body.sizeHint().height(), 1)
            anim.animate_height(body, 0, target, on_finished=lambda: body.setMaximumHeight(_QWIDGETSIZE_MAX))
        else:                                           # collapse: shrink current -> 0, THEN hide
            anim.animate_height(body, body.height(), 0, on_finished=lambda: body.setVisible(False))
    btn.toggled.connect(_toggle)
    v.addWidget(btn)
    v.addWidget(body)
    box.content_layout = body_lay
    box.toggle_button = btn
    return box


def repolish(widget):
    """Re-evaluate ``widget``'s QSS after a dynamic property (role / state / kind) changed -- Qt does NOT
    restyle automatically on a setProperty. Cheap; call it right after flipping a selector-affecting
    property (e.g. a form hint toggling state='error')."""
    st = widget.style()
    st.unpolish(widget)
    st.polish(widget)
    widget.update()


def tabular(widget):
    """Turn ON tabular (fixed-width) figures on ``widget``'s font so ids / coordinates / byte offsets line
    up in columns. Uses the Qt 6.7+ font-feature API; a silent no-op on older Qt. Returns the widget."""
    try:
        font = widget.font()
        font.setFeature(QFont.Tag("tnum"), 1)
        widget.setFont(font)
    except Exception:       # noqa: BLE001  (older Qt lacks setFeature/Tag -> skip, non-fatal)
        pass
    return widget


def install_wheel_guard(app=None):
    """Install the shared :class:`WheelGuard` on the running QApplication (idempotent; parented to the app
    so it outlives every widget). No-op returning ``None`` if there is no QApplication yet."""
    app = app or QApplication.instance()
    if app is None:
        return None
    guard = app.findChild(WheelGuard)              # already installed (e.g. a second window)? reuse it
    if guard is None:
        guard = WheelGuard(app)
        app.installEventFilter(guard)
    return guard
