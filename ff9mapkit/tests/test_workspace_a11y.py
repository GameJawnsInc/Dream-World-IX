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
from PySide6.QtWidgets import (QAbstractButton, QAbstractSlider, QAbstractSpinBox,  # noqa: E402
                               QApplication, QComboBox, QLineEdit, QListWidget, QPlainTextEdit,
                               QScrollBar, QTextEdit, QTreeWidget, QWidget)

from ff9mapkit.workspace.shell import Workspace, _apply_app_theme             # noqa: E402

# the actionable control types a screen-reader user tabs to / operates. QAbstractSlider joined when
# the Models tab grew a frame scrubber -- and retro-covered the Trace pitch and Behavior sim sliders,
# which had been real Tab stops with no announced name for as long as they had existed.
_WATCH = (QAbstractButton, QLineEdit, QComboBox, QAbstractSpinBox, QPlainTextEdit,
          QTextEdit, QListWidget, QTreeWidget, QAbstractSlider)


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
    # a QScrollBar IS a QAbstractSlider, so it arrived with the slider watch -- but it is a viewport's
    # own Qt-managed affordance: we neither create it nor should name it, the SCROLLED widget is the
    # named thing, and a screen reader announces a scroll bar by ROLE.
    if isinstance(wd, QScrollBar):
        return True
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


def test_the_log_registers_render_and_plain_text_survives(win):
    """Drive all four registers for real -- the tests that only READ the source missed a NameError.

    The `trace` branch calls `derive()`, which was not imported into shell.py. Every source-grepping
    fence passed, the whole suite passed, and the first traceback the console ever streamed would have
    crashed the drain. Only exercising the branch found it.

    The `win` fixture builds from a BASE palette (pick_palette), exactly as main() does -- which is the
    condition that exposes it: a pre-derived dict would have carried error_text and hidden the bug.

    Also asserts the reason appendHtml is banned: a build log is full of `<`, and rich text would eat it.
    """
    from ff9mapkit.editor import theme as th

    w = win
    w.output.clear()
    w._log("[12:34:56] Build & Deploy", "head")
    w._log("$ py -m ff9mapkit build a.toml", "echo")
    w._log("wrote p0data7.bin  <generic>  a < b", "body")
    w._log("Traceback (most recent call last):", "trace")

    txt = w.output.toPlainText()
    assert "<generic>" in txt and "a < b" in txt, "the console must stay PLAIN text"

    d = th.derive(dict(w.pal))
    doc = w.output.document()
    seen = []
    b = doc.begin()
    while b.isValid():
        it = b.begin()
        if not it.atEnd():
            f = it.fragment().charFormat()
            seen.append((int(f.fontWeight()), f.foreground().color().name().lower()))
        b = b.next()
    assert seen[0] == (600, d["text"].lower()), "head: weight 600 in $text"
    assert seen[1] == (600, d["log_fg"].lower()), "echo: weight 600 in $log_fg"
    assert seen[2] == (400, d["log_fg"].lower()), "body: normal weight"
    assert seen[3][1] == d["error_text"].lower(), "trace: the error tint"
    assert doc.maximumBlockCount() == 5000, "the log accumulates now -- it needs a ceiling"


def _ratio(a, b):
    def lum(h):
        h = h.lstrip("#")
        c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        c = [(x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4) for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    l1, l2 = sorted((lum(a), lum(b)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def test_every_tree_icon_tier_is_legible_selected_and_not():
    """KEYLINE. An icon tier can fail in every palette and no audit will ever say so.

    `audit_contrast.py` reads ink via `w.palette().color(w.foregroundRole())` -- a QLabel API. It is
    STRUCTURALLY BLIND to a QPixmap, so the icon tiers have never been covered by anything. That is why
    this is a test and not an audit entry, and why it fences (tint, ground, STATE) rather than just tint.

    The leaf tier shipped `text_subtle`, which is fenced for TEXT against the elevation ramp and was never
    fenced as ink for a DRAWING: 3.06 (light) / 3.12 (solarized-light) on the tree's ground -- a hair over
    the 3.0 non-text floor -- and 2.32-3.07 on a SELECTED row, failing 6 of 8. `muted` is the same tier's
    honest value.

    3.0, not 4.5: an icon is a non-text graphic (WCAG 1.4.11), and it sits beside a label that names it.

    THE SPINE TIER IS `focus`, NOT `accent`, and this fence is what found that: nord's raw accent reads
    2.47 on the tree's own ground. `focus` IS "the accent brightened until it clears 3:1 on the surface",
    so only the failing palettes move (nord 2.47 -> 3.08); the other seven return it unchanged. A separate
    `accent_mark` token would be _focus_token(accent, surface) -- identical by construction.
    """
    from ff9mapkit.editor import theme
    for mode, base in theme.THEMES.items():
        d = theme.derive(dict(base))
        for tier, ink in (("leaf", d["muted"]), ("spine", d["focus"])):
            r = _ratio(ink, d["surface"])
            assert r >= 3.0, f"{mode}: the {tier} icon tier is {r:.2f} on the tree ground -- under 3.0"
        # SELECTED is a different ground and a different ink -- the state is half the fence
        r = _ratio(d["text"], d["selection_bg"])
        assert r >= 3.0, f"{mode}: a selected row's icon is {r:.2f} on selection_bg -- under 3.0"


def test_a_selected_tree_icon_is_explicit_not_qts_guess(win):
    """`QIcon(pm)` hands Qt ONE pixmap and lets QCommonStyle::generatedIconPixmap invent the Selected
    state. Its invention is "tint 30% toward Highlight" -- guaranteed to erase an icon whose colour is
    near the highlight, which is exactly what an accent icon on an accent selection was (measured
    1.00-1.01 in all 8; byte-identically zero differing pixels in two palettes).

    REGISTER P1's tint has since fixed six of those for free -- but an app must not depend on a style
    hook's guess to keep its icons visible. Assert the Selected pixmap is REALLY there and REALLY differs
    from Normal, which is the only thing that proves Qt is not guessing.
    """
    ic = win._type_icon("field")
    from PySide6.QtCore import QSize
    from PySide6.QtGui import QIcon
    normal = ic.pixmap(QSize(16, 16), QIcon.Mode.Normal)
    selected = ic.pixmap(QSize(16, 16), QIcon.Mode.Selected)
    assert not normal.isNull() and not selected.isNull()
    assert normal.toImage() != selected.toImage(), (
        "the Selected pixmap is identical to Normal -- Qt is generating it, and its guess erases an icon "
        "that sits near the highlight colour"
    )


def test_the_unsaved_dot_does_not_eat_the_glyph_it_annotates(app):
    """KEYLINE's sharpest defect, and ONLY A RENDER COULD SEE IT.

    The dot was `r = w * 0.30` -- at w=16 the dot plus its halo spanned 11.6px of a 16px icon: 72% of the
    icon's WIDTH, punched out of the bottom-right corner. `field` became an amber blob with a fragment of
    a frame attached; `hub` lost two of its four squares; `chocobo`'s feather was bisected -- on the row
    you are editing.

    THE OBVIOUS MEASUREMENT CANNOT CATCH IT, and that is worth the fence's existence alone: the punch-out
    CLEARS and the dot then FILLS, so every destroyed pixel comes back at alpha 255. An "is this pixel
    still ink?" test counts the amber dot as surviving glyph and reports 98% kept. This asks the geometry
    instead, which is the thing that was actually wrong.
    """
    from ff9mapkit.workspace import icons
    for w in (16, 24):                      # the two sizes the tree and the crumb actually use
        r = w * icons._DOT_K
        span = 2 * (r + icons._DOT_PAD)     # the dot AND the transparent halo it punches
        assert span / w <= 0.55, (
            f"at w={w} the unsaved dot spans {span:.1f}px = {100 * span / w:.0f}% of the icon -- it is "
            f"eating the glyph it annotates, not annotating it"
        )
        assert 5.0 <= 2 * r <= 8.0 or w != 16, f"at w=16 the dot should read ~6px, got {2 * r:.1f}"


def test_the_dots_geometry_is_float_not_truncated(app):
    """The `int()` was the bug's other half, not a rounding detail.

    `int(cx - r - 1)` truncates the origin and `int((r + 1) * 2)` truncates the extent, so the halo lost
    up to a pixel per side and landed asymmetrically. At k=0.19 the 1px pad IS the whole margin, so
    truncation would eat it outright -- the radius fix alone does not survive it.
    """
    import ast
    import inspect
    from ff9mapkit.workspace import icons
    src = inspect.getsource(icons.with_corner_dot)
    tree = ast.parse(src.strip())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "drawEllipse":
            assert node.args and isinstance(node.args[0], ast.Call), (
                "drawEllipse takes truncated ints -- it must take a QRectF or the halo is eaten"
            )
            assert getattr(node.args[0].func, "id", None) == "QRectF", "the dot's geometry must be QRectF"




# ---------------------------------------------------------------------------------------------------
# PRESS -- the states a SOURCE-reading fence structurally cannot see.
# ---------------------------------------------------------------------------------------------------
# `test_focus_rings_are_defined_for_keyboard_users` above asserts `"QPushButton:focus" in css`. That is a
# real fence and it catches a DELETED rule. It cannot catch a rule that is present, correct, and LOSES:
#
#     #id       -> specificity (0,1,0,1)
#     :pressed  -> specificity (0,0,1,1)
#
# so `QToolButton#railSeg { background: transparent; }` out-ranks `QToolButton:pressed { background:
# $pressed; }` and the press paints nothing. The rule is in the sheet; the sheet is correct; the string is
# present; the fence is green; the button is dead. Only the rendered pixels know.
_ID_BUTTONS = ["search", "hub", "railSeg", "consoleToggle", "disclosureToggle", "conceptBadge", "gear",
               "libraryHelp"]


@pytest.fixture(scope="module")
def themed(app):
    """A shown host carrying the REAL sheet, with test buttons parented under it.

    THE QSS IS A *WIDGET* STYLESHEET IN THIS APP, NOT AN APPLICATION ONE. `_apply_app_theme` sets only the
    Fusion style and the QPalette; the rules live on the Workspace itself (`self.setStyleSheet(qss(...))`)
    and reach controls by INHERITANCE. So a bare top-level QToolButton sees none of them.

    THIS COST ME A VACUOUS FENCE, and it is worth the paragraph. The first cut of the state fences took the
    bare `app` fixture and never applied any sheet -- so they measured FUSION'S OWN native chrome. Fusion
    draws its own pressed state, so all 7 press fences went GREEN while testing nothing whatsoever: they
    would have passed with the bug fully present. The focus half failed loudly, which is the only reason
    the vacuity surfaced at all -- A FENCE THAT IS WRONG IN THE SAFE DIRECTION IS THE ONE THAT SHIPS.

    So the host replicates the real structure (sheet on an ancestor, inherited by the button) and ASSERTS
    the sheet is on it. Scoped to the host -- no app pollution, per the target-size test above.
    """
    from PySide6.QtWidgets import QVBoxLayout                                    # noqa: PLC0415
    from ff9mapkit.editor.theme import pick_palette                              # noqa: PLC0415
    from ff9mapkit.workspace.style import qss                                    # noqa: PLC0415
    pal = pick_palette("dark")
    _apply_app_theme(app, pal)                       # Fusion + the QPalette (what the real app does)
    host = QWidget()
    host.setStyleSheet(qss(pal))                     # ...and the QSS, where the real app puts it
    lay = QVBoxLayout(host)
    made = {}
    for oid in _ID_BUTTONS:
        from PySide6.QtWidgets import QPushButton, QToolButton                   # noqa: PLC0415
        w = (QPushButton if oid in ("search", "libraryHelp") else QToolButton)()
        w.setText("Sample")
        w.setObjectName(oid)
        # CHECKABLE **AND CHECKED**. Checkable-but-unchecked was the hole: `#railSeg:pressed` and
        # `#railSeg:checked` are both (0,1,1,1), so they TIE and source order decides -- and the ACTIVE
        # segment rendered 0px on press while this fence, testing only the UNCHECKED one, stayed green.
        # A state fence that never enters the state is testing the other state.
        w.setCheckable(oid in ("railSeg", "disclosureToggle"))
        if w.isCheckable():
            w.setChecked(True)
        lay.addWidget(w)
        made[oid] = w
    host.resize(360, 60 * len(made))
    host.show()
    app.processEvents()
    assert host.styleSheet(), "no sheet on the host -- these fences would measure Fusion, not the app"
    assert host.isVisible(), "host never shown -- every delta would be a fiction"
    # `host` IS RETURNED SO IT STAYS ALIVE. It is not decoration: PySide reference-counts the Python
    # wrapper, so dropping the only reference to the parent deletes the C++ object AND every child --
    # the buttons then raise "Internal C++ object already deleted" on first touch. The Python objects
    # outlive their C++ selves, which is a lifetime bug that looks exactly like a Qt bug.
    return app, made, host


def _state_delta(app, w, setter) -> int:
    """Pixels that change when `setter` puts `w` into a state.

    THE BASELINE IS FORCED TO REST FIRST, and that is not hygiene -- it is the whole measurement. Qt hands
    focus to the first widget in the tab chain the moment a window shows, so grabbing `rest` without
    clearing focus reads the FIRST control as already-focused and reports it as having NO focus ring. That
    exact artifact produced a false finding while this was being written, in a probe built to catch
    precisely this class of thing.
        A BASELINE YOU DID NOT PUT INTO A KNOWN STATE IS NOT A BASELINE.
    """
    w.clearFocus()
    app.processEvents()
    assert not w.hasFocus(), "not at rest -- the delta would be measured from the wrong image"
    rest = w.grab().toImage()
    setter(w, True)
    app.processEvents()
    after = w.grab().toImage()
    setter(w, False)
    app.processEvents()
    return sum(rest.pixelColor(x, y) != after.pixelColor(x, y)
               for y in range(rest.height()) for x in range(rest.width()))


@pytest.mark.parametrize("oid", _ID_BUTTONS)
def test_an_id_scoped_button_still_reacts_to_a_click(themed, oid):
    """Six of the app's seven id-scoped buttons shipped DEAD ON CLICK -- the Ctrl-K search pill, the nav
    rail, the Info Hub button, every disclosure drawer, every "?" badge. Hover worked; the click did
    nothing. That is the entire custom-chrome layer not acknowledging the mouse.

    style.py documents this trap THREE times (`#accent:disabled`, `#accent:focus`, `[role="quiet"]`), each
    as a hard-won measurement, each fixed at the one site where it was noticed. The lesson never left the
    site it was learned at -- which is the round's whole theme: a law that lives in a comment is a wish.

    `#gear` IS PARAMETRIZED IN DELIBERATELY, as the control: it is the one id-scoped button that does not
    restate `background`, and the one that never broke. Measured 3905 px against the other six at exactly
    0. That is what makes this a cascade shadow rather than a Qt limitation -- and if a refactor ever
    breaks #gear too, this row says so.
    """
    app, made, _host = themed
    n = _state_delta(app, made[oid], lambda b, on: b.setDown(on))
    assert n > 0, (
        f"#{oid} changes NOTHING when pressed -- its id rule restates `background` and so out-ranks the "
        f"generic `:pressed`. Give it its own `#{oid}:pressed`."
    )


@pytest.mark.parametrize("oid", _ID_BUTTONS)
def test_an_id_scoped_button_shows_where_the_keyboard_is(themed, oid):
    """WCAG 2.4.7. `* { outline: 0; }` kills Fusion's native focus rect APP-WIDE, and style.py claims the
    QSS then gives "every interactive control ONE deliberate accent ring". Grepped for violations:
    `#consoleToggle` was the only id-scoped QToolButton with no `:focus` rule at all -- its four siblings
    each had one -- so the console's own toggle was a real tab stop with ZERO focus indication.

    A ring on a `border: 0` control is not free: adding one moves the box 2px per axis, so the control
    JUMPS when you tab to it. The border is reserved TRANSPARENT at rest and only coloured on focus, with
    padding paying the 1px back -- the move `#railSeg` already used. Measured: both boxes unchanged.
    """
    app, made, _host = themed
    n = _state_delta(app, made[oid], lambda b, on: (b.setFocus() if on else b.clearFocus()))
    assert n > 0, f"#{oid} shows nothing on focus -- a keyboard user cannot see where they are"


# ---------------------------------------------------------------------------------------------------
# THE DOC PANE -- structural fences only, and that restraint is the point.
# ---------------------------------------------------------------------------------------------------
# This module sets QT_QPA_PLATFORM=offscreen, where THE FONT DB IS STUBBED AND EVERY TEXT-DERIVED WIDTH
# IS FICTION. Measured side by side while writing these: offscreen puts mid_col's minimum at 1156 and the
# window floor at 1296; native says 542 and 1280. Offscreen renders ~14px per character, so it inflated
# two ordinary 80-char labels into a fake window-wide constraint -- a coherent, checkable story about a
# defect that does not exist.
#
# So NOTHING BELOW ASSERTS A WIDTH IT MEASURED. Both fences assert a STRUCTURAL property that is true
# regardless of the font: "a floor is set" and "the row wraps". The real numbers live in
# studies/gui-aesthetics/evidence/probe_doc_pane.py, which refuses to run offscreen.


def test_no_splitter_pane_pins_a_minimum_width(win):
    """A PANE MINIMUM PROPAGATES TO THE WINDOW, so pinning one takes the app's narrow widths away.

    `mid_col.setMinimumWidth(700)` shipped for one commit to stop a wide SAVED layout squeezing the
    document when replayed narrow. Measured natively, it did two things its own comment denied:
      * the window's hard floor went 686 -> 844, so `resize(720)` returned 844 and a 720px window became
        UNREACHABLE -- while test_toolbar_overflows_gracefully_at_narrow_width kept asking for 720, getting
        844, and passing;
      * 700 was a 100%-scale constant against a layout minimum of 542/575/685/796 across the text dial, so
        at 150% the "floor" sat 96px BELOW the real minimum -- worse than absent.
    Any explicit minimum above the pane's own 542 raises the window floor, so this approach cannot work.
    Clamp the restored SIZES instead.

    STRUCTURAL, NOT A WIDTH, AND THAT IS FORCED: this module is offscreen, where the stub font DB inflates
    text ~2.6x and the window's floor reads ~1296 no matter what is pinned. The first version of this fence
    asserted `win.resize(720); win.width() <= 720` and went red on the harness rather than on the code --
    the offscreen lie, caught for the third time in one round. "Nothing pins a minimum" is the same law and
    is font-independent. The real widths live in studies/gui-aesthetics/evidence/probe_doc_pane.py, which
    refuses to run offscreen.
    """
    for i in range(win._central_split.count()):
        pane = win._central_split.widget(i)
        assert pane.minimumWidth() == 0, (
            f"splitter pane {i} ({type(pane).__name__}) pins minimumWidth={pane.minimumWidth()}. That "
            f"propagates to the WINDOW's minimum and takes narrow widths away from the app (720px is in "
            f"scope for WCAG 1.4.4/1.4.10). Clamp the restored sizes, do not pin the widget."
        )


def test_a_recent_row_never_dictates_home_width(win, app, tmp_path):
    """HOME'S MINIMUM WIDTH MUST NOT DEPEND ON WHAT THE USER HAS OPENED -- and it did.

    A recent row is a rich-text QLabel; un-wrapped, its minimumSizeHint IS the fully-rendered line, and a
    journey's display name is its parent FOLDER's name. Measured natively with a real history: Home needed
    903 and horizontal-scrolled at 1280 AND 1440. Wrapped, its minimum is its longest WORD and Home falls
    back to its own 525 at every width.

    NO TEST COULD HAVE CAUGHT THIS BEFORE, which is why it is worth a fence now: the trigger lived in the
    user's prefs, not in the repo. So this one BUILDS a history rather than hoping for one.

    Asserts `wordWrap()`, not a width: this suite is offscreen and cannot measure text (see the block
    comment above). Wrap is the mechanism, it is font-independent, and it is the thing that was missing.
    """
    import json
    from PySide6.QtWidgets import QLabel                                     # noqa: PLC0415
    from ff9mapkit import prefs                                              # noqa: PLC0415
    proj = tmp_path / "a-project-folder-with-a-comfortably-long-name"
    proj.mkdir()
    entry = proj / "journey.toml"
    entry.write_text(json.dumps({}), encoding="utf-8")
    rows = [{"kind": "journey", "path": str(entry)}]
    real = prefs.recent
    prefs.recent = lambda: rows          # the row is display-filtered on existence, so the path is real
    try:
        win._refresh_recent()
        app.processEvents()
        labs = [x for x in win.findChildren(QLabel) if x.toolTip() == str(entry)]
        assert labs, "the recent row was not built -- this fence is measuring nothing"
        for lab in labs:
            assert lab.wordWrap(), (
                "a recent row does not wrap, so its minimumSizeHint is its whole rendered line and "
                "HOME'S width now depends on the length of the user's project folder name"
            )
    finally:
        prefs.recent = real
        win._refresh_recent()


def test_every_real_tab_stop_shows_where_the_keyboard_is(win, app):
    """WCAG 2.4.7, for the WHOLE focus chain -- not just the buttons.

    `* { outline: 0 }` kills Fusion's native focus rect app-wide, and style.py promises the QSS then gives
    "every interactive control ONE deliberate accent ring". For one round that meant "every BUTTON": the
    round that re-asserted the law fenced the seven id-scoped buttons and left the rest at 0 px --
    including THE MAIN OUTPUT CONSOLE, the app's largest reading surface. A keyboard user tabbed into it
    and nothing said so.

    None of them were special cases. The wells and the map already carry a 1px border, so their ring is the
    same free recolour the buttons got; only the scroll areas needed anything (they are `NoFrame`, so the
    border is reserved transparent and coloured on focus).

    WHY read-only hid it: an EDITABLE QPlainTextEdit shows a text CARET, which looks like feedback and is
    not a focus ring. Suppress the caret -- `setReadOnly(True)` -- and the control goes silent.

    A TAB STOP IS WHAT TAB REACHES. This walks `focusNextChild()`, which is what Qt does on Tab, rather
    than filtering on `focusPolicy`. Both filter attempts over-counted and each would have manufactured
    work: `!= NoFocus` swept in a ClickFocus QLabel a Tab walk can never land on, and `& TabFocus` swept in
    QAbstractScrollArea's VIEWPORT, which reports StrongFocus and is not in the chain. (The review that
    prompted this counted "CampaignMap + its viewport" -- the same widget twice, by that second mistake.
    Reproducing a number does not make it right; reproducing the METHOD reproduces the error.)

    Offscreen is honest here: a focus ring is a colour change on a widget that already exists, and nothing
    below is a text-derived WIDTH -- which is the only thing this harness lies about.
    """
    # ENSURE, DO NOT TOGGLE. `win` is a module-scoped fixture, so by the time this runs another test may
    # already have flipped the console -- and a toggle applied to an unknown state lands in the OTHER one.
    # This failed exactly that way on the first run: `_toggle_console()` CLOSED an already-open console
    # and the fence then reported the console as missing. A toggle is not an instruction, it is a flip.
    # AND THE WINDOW MUST BE THE ACTIVE ONE. Qt paints focus only on the active window, and this module's
    # other fixtures show their own top-levels (the `themed` host, the narrow-toolbar Workspace) -- so by
    # the time this runs, `win` is not active and EVERY setFocus() paints nothing. Run alone it passed; run
    # in the file it reported all 34 tab stops dead, which is not 34 defects, it is one inactive window.
    # A probe that builds a single window never meets this and will never warn you about it.
    #   "A baseline you did not put into a known state is not a baseline" -- and WHICH WINDOW IS ACTIVE is
    #   part of that state.
    win.activateWindow()
    win.raise_()
    app.processEvents()
    was_open = win.output.isVisible()
    if not was_open:
        win._toggle_console()                # collapsed by default; it is the biggest surface at stake
        app.processEvents()
    try:
        assert win.output.isVisible(), "the console did not open -- its row would be silently missing"
        dead = []
        for i in range(win.tabs.count()):
            win.tabs.setCurrentIndex(i)
            app.processEvents()
            chain, guard = [], set()
            for _ in range(400):
                if not win.focusNextChild():
                    break
                f = win.focusWidget()
                if f is None or id(f) in guard:
                    break
                guard.add(id(f))
                chain.append(f)
            for w in chain:
                if not w.isVisible() or not w.isEnabled() or w.objectName().startswith("qt_"):
                    continue
                if _state_delta(app, w, lambda b, on: (b.setFocus() if on else b.clearFocus())) == 0:
                    dead.append(f"{type(w).__name__}"
                                f"#{w.objectName() or '-'} {w.accessibleName() or ''}".strip())
        assert not dead, (
            "these are real Tab stops that show NOTHING when focused -- `* { outline: 0 }` removed "
            f"Fusion's ring and nothing replaced it here: {sorted(set(dead))}"
        )
    finally:
        if not was_open:                     # leave the shared fixture exactly as it was found
            win._toggle_console()
            app.processEvents()
