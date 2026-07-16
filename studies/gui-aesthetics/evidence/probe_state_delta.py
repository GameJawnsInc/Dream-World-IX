"""PRESS -- does a control actually CHANGE when you press it, or focus it? Measured in pixels.

WHY NO EXISTING FENCE COULD SEE THIS. `test_hover_and_pressed_give_real_feedback` asserts the TOKENS are
distinct -- `pressed` vs `hover` vs `surface_btn`, all 8 palettes, and it is a good fence that caught four
palettes shipping a byte-identical hover. `test_qss_has_no_malformed_subcontrol_selectors` reads the
sheet's TEXT. Neither can see a rule that is present, correct, well-tested -- AND LOSES THE CASCADE.

    #id          -> specificity (0,1,0,1)
    :pressed     -> specificity (0,0,1,1)

So `QToolButton#railSeg { background: transparent; }` OUT-RANKS `QToolButton:pressed { background:
$pressed; }` and the press paints nothing. style.py documents this exact trap THREE times (#accent:disabled
at :254, #accent:focus at :257, [role=quiet] at :274) -- each time as a hard-won measurement, each time
fixed at that one site. Seven more id-scoped rules shipped with the same shape.

The only instrument that can see it is the pixels. So: build the real widget under the real sheet, grab it,
toggle the state, grab again, count what changed.

HARNESS HONESTY:
  * offscreen stubs the font DB, so this measures COLOUR/geometry deltas, not text metrics. Colour is what
    the question is about.
  * the app really runs FUSION (`shell.py` `_apply_app_theme` calls `app.setStyle("fusion")`), so a probe
    that let Qt pick a native style would be measuring a different app. Forced and asserted below.
  * a widget that was never shown reports nothing and prints an empty list -- which this study nearly
    concluded from once. show() + isVisible() are asserted.

Run:  py studies/gui-aesthetics/evidence/probe_state_delta.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "ff9mapkit"))

from PySide6.QtWidgets import (QApplication, QPushButton, QToolButton,  # noqa: E402
                               QVBoxLayout, QWidget)

from ff9mapkit.editor import theme          # noqa: E402
from ff9mapkit.workspace import style       # noqa: E402


def _delta(img_a, img_b) -> int:
    n = 0
    for y in range(img_a.height()):
        for x in range(img_a.width()):
            if img_a.pixelColor(x, y) != img_b.pixelColor(x, y):
                n += 1
    return n


# (label, factory, object-name, role) -- every id-scoped chrome button in the app, plus the controls
IDS = [
    ("QToolButton (generic)", QToolButton, None, None),
    ("QPushButton (generic)", QPushButton, None, None),
    ("QPushButton#accent", QPushButton, "accent", None),
    ("QPushButton[role=quiet]", QPushButton, None, "quiet"),
    ("QToolButton#gear", QToolButton, "gear", None),               # THE CONTROL: no background restated
    ("QPushButton#search", QPushButton, "search", None),
    ("QToolButton#hub", QToolButton, "hub", None),
    ("QToolButton#railSeg", QToolButton, "railSeg", None),
    ("QToolButton#consoleToggle", QToolButton, "consoleToggle", None),
    ("QToolButton#disclosureToggle", QToolButton, "disclosureToggle", None),
    ("QToolButton#conceptBadge", QToolButton, "conceptBadge", None),
]


def main() -> int:
    app = QApplication.instance() or QApplication([])
    app.setStyle("fusion")
    # ASSERT the style, don't hope for it -- the app calls setStyle("fusion") at startup, so a probe that
    # let Qt pick the native windows11 style would be measuring a different app's chrome. QStyle.name()
    # is the Qt6 accessor; objectName() is empty on a QStyle, so a check against THAT would pass
    # vacuously in every direction -- the exact shape of fence this study keeps catching itself writing.
    sname = app.style().name() if hasattr(app.style(), "name") else type(app.style()).__name__
    assert "fusion" in sname.lower(), f"style is {sname!r}, not Fusion -- measuring a different app"
    pal = theme.derive(dict(theme.THEMES["dark"]))
    app.setStyleSheet(style.qss(theme.THEMES["dark"]))

    host = QWidget()
    lay = QVBoxLayout(host)
    made = []
    for label, cls, oid, role in IDS:
        w = cls()                       # QToolButton takes no text arg -- setText for both, uniformly
        w.setText("Sample")
        if oid:
            w.setObjectName(oid)
        if role:
            w.setProperty("role", role)
        w.setCheckable(oid in ("railSeg", "disclosureToggle"))
        lay.addWidget(w)
        made.append((label, w))
    host.resize(320, 60 * len(made))
    host.show()
    app.processEvents()
    assert host.isVisible(), "never shown -- every number below would be a fiction"

    print(f"  {'entity':<32} {'pressed dpx':>12} {'focus dpx':>10}   verdict")
    dead_press, dead_focus = [], []
    for label, w in made:
        assert w.isVisible(), f"{label} not visible"
        # THE BASELINE MUST BE AT REST, AND MINE WAS NOT. Qt hands focus to the first widget in the tab
        # chain the moment the window shows -- so this probe's FIRST entity grabbed a "rest" image that
        # was already wearing its focus ring, setFocus() then changed nothing, and it reported the generic
        # QToolButton as having NO FOCUS RING. That finding was false: an artifact of an uncontrolled
        # baseline, in a probe written to find exactly this kind of thing. Verified by printing hasFocus()
        # straight after show(): widget 0 True, widgets 1..n False.
        #   A BASELINE YOU DID NOT PUT INTO A KNOWN STATE IS NOT A BASELINE.
        for _, other in made:
            other.clearFocus()
        app.processEvents()
        assert not w.hasFocus(), f"{label}: still focused at rest -- the delta below would be a fiction"
        rest = w.grab().toImage()
        w.setDown(True)
        app.processEvents()
        dp = _delta(rest, w.grab().toImage())
        w.setDown(False)
        app.processEvents()
        w.setFocus()
        app.processEvents()
        df = _delta(rest, w.grab().toImage())
        w.clearFocus()
        app.processEvents()
        bad = []
        if dp == 0:
            dead_press.append(label)
            bad.append("DEAD ON CLICK")
        if df == 0:
            dead_focus.append(label)
            bad.append("NO FOCUS RING")
        print(f"  {label:<32} {dp:>12} {df:>10}   {' + '.join(bad) if bad else 'ok'}")

    print(f"\n  dead on click : {len(dead_press)}/{len(made)}")
    for x in dead_press:
        print(f"      {x}")
    print(f"  no focus ring : {len(dead_focus)}/{len(made)}")
    for x in dead_focus:
        print(f"      {x}")
    print("\n  #gear is THE CONTROL: it is the one id-scoped button that does not restate `background`,")
    print("  and it is the one that still reacts. That makes this a cascade shadow, not a Qt limitation.")

    # ---- the claim the FIX makes in its own comment, measured ------------------------------------------
    # #consoleToggle and #disclosureToggle had `border: 0/none` and so had nowhere to put a focus ring.
    # Reserving it transparent costs 1px per side; the fix pays that back out of padding and CLAIMS the
    # rendered box is unchanged. A claim in a comment is a wish -- so it gets measured here, or it goes.
    print("\n=== THE RING MUST COST NO LAYOUT (the fix's own claim, measured)")
    OLD = {                       # what shipped before PRESS, verbatim
        "consoleToggle": "QToolButton#consoleToggle { background: transparent; border: 0; "
                         "padding: 5px 6px; color: %(muted)s; font-weight: 600; }",
        "disclosureToggle": "QToolButton#disclosureToggle { background: transparent; border: none; "
                            "color: %(muted)s; font-weight: 600; padding: 6px 2px; text-align: left; }",
    }
    ok = True
    for oid, old_rule in OLD.items():
        probe = QToolButton()
        probe.setObjectName(oid)
        probe.setText("Console")
        lay.addWidget(probe)
        app.processEvents()
        now = probe.sizeHint()
        # re-render the app with ONLY that rule reverted to its pre-PRESS text
        app.setStyleSheet(style.qss(theme.THEMES["dark"]) + "\n" + old_rule % {"muted": pal["muted"]})
        probe.style().unpolish(probe)
        probe.style().polish(probe)
        app.processEvents()
        before = probe.sizeHint()
        app.setStyleSheet(style.qss(theme.THEMES["dark"]))
        probe.style().unpolish(probe)
        probe.style().polish(probe)
        app.processEvents()
        same = (before.width(), before.height()) == (now.width(), now.height())
        ok &= same
        print(f"  #{oid:<18} was {before.width()}x{before.height()}  now {now.width()}x{now.height()}   "
              f"{'unchanged' if same else 'THE BOX MOVED -- the comment is lying'}")
    if not ok:
        print("\n  ^ fix the padding or delete the claim. A law in a comment is a wish.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
