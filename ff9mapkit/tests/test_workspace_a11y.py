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
