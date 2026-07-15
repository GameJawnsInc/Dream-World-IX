"""Prove/refute: does `style.py:126` paint an unconditional border on EVERY radio + checkbox?

The claim
---------
`style.py:126` reads::

    QCheckBox:focus::indicator, QRadioButton:focus::indicator { border: 1px solid $focus; }

The pseudo-CLASS (`:focus`) is written before the pseudo-ELEMENT (`::indicator`); a pseudo-element must
come last. Qt's parser does not reject this. `Selector::pseudoElement()` returns "" (the first pseudo,
`focus`, is a KNOWN class, so it is not read as an element), and `pseudoClass()` returns 0 on the
unrecognised `indicator`. The match test `(0 & state) == 0` is then true in EVERY state, so the rule
degenerates to an unconditional::

    QRadioButton, QCheckBox { border: 1px solid $focus; }

Two consequences, both shipped:
  1. every radio/checkbox in the app wears a permanent accent-coloured rectangle, and
  2. radios/checkboxes have had NO focus indication at all since the rule landed
     (`test_focus_rings_are_defined_for_keyboard_users` greps selector strings and passes regardless).

Consequence (1) is the "cards don't read well" screenshot: the three blue rects around the
Build to (field) radios are this bug, not a design decision.

Result (2026-07-15, PySide6 6.11.1, DARK)
-----------------------------------------
    UNFOCUSED radio, edges painted $focus (#4c8dff):
      BEFORE : 4/4  ['top-mid', 'left-mid', 'bottom-mid', 'right-mid']
      AFTER  : 0/4  []
    VERDICT: CONFIRMED - the border is unconditional and the fix removes it

Side effect, checked because it touches a WCAG fence: the radio's sizeHint().height() goes 28 -> 26
when the phantom border stops adding 1px per edge. Still >= 24 (WCAG 2.5.8), in both densities.

Harness note -- READ BEFORE EXTENDING THIS FILE
-----------------------------------------------
`QT_QPA_PLATFORM=offscreen` stubs the Qt font database, which inflates every text advance 2-3x
(`studies/gui-makeover/README.md` records the same trap as "that gives tofu boxes"). This script is
offscreen-safe ONLY because it measures COLOUR, which is font-independent. Do NOT add a width/geometry
assertion here: it would be fiction. For metrics use the native platform + WA_DontShowOnScreen recipe.

Run:  py studies/gui-aesthetics/evidence/prove_radio_border.py
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")   # colour-only -- see the harness note above

from PySide6.QtGui import QPixmap                                             # noqa: E402
from PySide6.QtWidgets import (                                               # noqa: E402
    QApplication, QLineEdit, QRadioButton, QVBoxLayout, QWidget,
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "ff9mapkit"))
from ff9mapkit.editor.theme import DARK, derive                               # noqa: E402
from ff9mapkit.workspace.style import qss                                     # noqa: E402

BROKEN_T = "QCheckBox:focus::indicator, QRadioButton:focus::indicator { border: 1px solid %s; }"
FIXED_T = "QCheckBox::indicator:focus, QRadioButton::indicator:focus { border: 1px solid %s; }"

app = QApplication.instance() or QApplication([])


def render(sheet, label):
    """Render an UNFOCUSED, UNCHECKED radio under `sheet` and sample its outer edge pixels."""
    host = QWidget()
    host.setStyleSheet(sheet)
    lay = QVBoxLayout(host)
    rb = QRadioButton("Test slot 4003 - quick + reversible")
    rb.setChecked(False)
    lay.addWidget(rb)
    sink = QLineEdit()                  # a focus sink: the radio would otherwise take focus as the
    lay.addWidget(sink)                 # only focusable widget, and the test would prove nothing
    host.resize(420, 90)
    host.show()
    sink.setFocus()
    app.processEvents()
    assert not rb.hasFocus(), "radio must be UNFOCUSED for this test to mean anything"

    pm = QPixmap(rb.size())
    rb.render(pm)
    img = pm.toImage()
    w, h = img.width(), img.height()
    edges = {
        "top-mid": img.pixelColor(w // 2, 0).name(),
        "left-mid": img.pixelColor(0, h // 2).name(),
        "bottom-mid": img.pixelColor(w // 2, h - 1).name(),
        "right-mid": img.pixelColor(w - 1, h // 2).name(),
    }
    print(f"\n=== {label} ===")
    print(f"  sizeHint h: {rb.sizeHint().height()}   focused: {rb.hasFocus()}")
    for k, v in edges.items():
        print(f"  {k:12s} {v}")
    host.deleteLater()
    return edges


pal = derive(DARK)
focus = pal.get("focus", pal["accent"])
print(f"DARK accent = {pal['accent']}   focus = {focus}   bg = {pal['bg']}")

base = qss(DARK)
broken, fixed = BROKEN_T % focus, FIXED_T % focus
assert broken in base, "the shipped QSS no longer contains the broken selector -- has it been fixed?"

before = render(base, "CURRENT (style.py:126 as shipped)")
after = render(base.replace(broken, fixed), "FIXED (::indicator:focus)")

hit_before = [k for k, v in before.items() if v.lower() == focus.lower()]
hit_after = [k for k, v in after.items() if v.lower() == focus.lower()]

print("\n" + "=" * 62)
print(f"UNFOCUSED radio, edges painted $focus ({focus}):")
print(f"  BEFORE : {len(hit_before)}/4  {hit_before}")
print(f"  AFTER  : {len(hit_after)}/4  {hit_after}")
ok = len(hit_before) == 4 and len(hit_after) == 0
print("VERDICT:", "CONFIRMED - the border is unconditional and the fix removes it" if ok
      else "NOT REPRODUCED as described")
sys.exit(0 if ok else 1)
