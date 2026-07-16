"""PROBE: what IS the app's prose rate -- and is PROSE_W already out of band?

Two numbers disagree and both are mine:

    my earlier probe   PROSE_W = 420px -> 61.9 ch   (rate 6.78 px/char)
    round 5's verifier the B&D crown note at 420px -> 77.5 ch  (rate 5.42 px/char)

The gap is 25%, and it decides GAUGE: 61.9ch is comfortably inside the 45-75 band and needs nothing;
77.5ch is ALREADY out of band at 100%, before the text-size dial touches it.

My rate is the suspect. I measured `'abcdefghijklmnopqrstuvwxyz '` -- ONE space in 27 characters, where
English runs about one in six. The space is the narrowest glyph in the face, so a string with almost none
of them overstates px/char, which understates chars/line. A synthetic rate is not a measurement of prose;
it is a measurement of the alphabet.

So: measure the REAL strings this app puts through `Prose`, at the REAL body rung, and at every rung the
text-size dial can produce. And check the shipped fence, which hard-codes WORST_13PX = 5.72 -- a constant
divided by a constant cannot see a live defect.

NATIVE ONLY -- offscreen stubs the font DB. Fusion, because the app forces Fusion (shell.py:129).

Run:  py studies/gui-aesthetics/evidence/probe_measure_rate.py
"""
import ast
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
KIT = REPO / "ff9mapkit"
sys.path.insert(0, str(KIT))
os.environ["FF9MAPKIT_NO_THUMBS"] = "1"

from PySide6.QtGui import QFont, QFontMetricsF                              # noqa: E402
from PySide6.QtWidgets import QApplication                                  # noqa: E402

app = QApplication.instance() or QApplication([])
assert app.platformName() != "offscreen", "native only: offscreen stubs the font DB"
app.setStyle("fusion")

from ff9mapkit import prefs                                                 # noqa: E402
from ff9mapkit.workspace import style, widgets                              # noqa: E402

ALPHA = "abcdefghijklmnopqrstuvwxyz "


def harvest():
    """Every string literal handed to prose() / Prose() / nameplate()'s note / option()'s description."""
    out = []
    for py in sorted((KIT / "ff9mapkit" / "workspace").glob("*.py")):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None)
            if name not in ("prose", "Prose", "nameplate", "option"):
                continue
            for a in node.args:
                if isinstance(a, ast.Constant) and isinstance(a.value, str) and len(a.value) > 40:
                    out.append((py.name, node.lineno, name, a.value))
    return out


def rate(s, px):
    f = QFont("Segoe UI")
    f.setPixelSize(px)
    return QFontMetricsF(f).horizontalAdvance(s) / len(s)


body = style.type_px("type_body", 100)
strings = harvest()

print(f"THE APP'S REAL PROSE, at the body rung ({body}px):")
print(f"  {'file':14} {'line':>5} {'chars':>6} {'px/char':>8} {'ch @420px':>10}")
print("  " + "-" * 52)
rates = []
for fname, lineno, fn, s in strings:
    r = rate(s, body)
    rates.append(r)
    ch = widgets.PROSE_W / r
    flag = "" if ch <= 75 else "  <-- OVER 75"
    print(f"  {fname:14} {lineno:>5} {len(s):>6} {r:>8.3f} {ch:>10.1f}{flag}")

print("  " + "-" * 52)
if rates:
    lo, hi = min(rates), max(rates)
    print(f"  real-prose rate band at {body}px: {lo:.3f} - {hi:.3f} px/char")
    print(f"  -> PROSE_W = {widgets.PROSE_W}px is {widgets.PROSE_W / hi:.1f} - {widgets.PROSE_W / lo:.1f} ch")
    a = rate(ALPHA, body)
    print(f"\n  MY SYNTHETIC RATE was {a:.3f} px/char (the bare alphabet) = {widgets.PROSE_W / a:.1f} ch.")
    print(f"  That is {100 * (a / hi - 1):+.0f}% off the WIDEST real string -- the alphabet has 1 space in 27,")
    print("  English has ~1 in 6, and the space is the narrowest glyph in the face. The synthetic rate")
    print("  overstates px/char, which understates chars/line, which is why it said 'comfortably fine'.")

print()
print("=" * 72)
print("THE SHIPPED FENCE: a constant divided by a constant")
print("=" * 72)
print("  test_prose_w_is_a_real_measure hard-codes WORST_13PX = 5.72 and asserts PROSE_W / 5.72 <= 75.")
print(f"  It still passes: {widgets.PROSE_W} / 5.72 = {widgets.PROSE_W / 5.72:.1f} ch.")
print("  But 5.72 was measured at 13px, and QUARTO P1 moved the body to 14. The fence's divisor is now")
print("  a number from a font size the app no longer sets, and it cannot see anything the app does.")

print()
print("=" * 72)
print("AND IT DECAYS UNDER THE DIAL  (the defect CALIBRE created)")
print("=" * 72)
worst = max(rates) if rates else rate(ALPHA, body)
worst_s = max(strings, key=lambda t: rate(t[3], body))[3] if strings else ALPHA
print(f"  measured on the WIDEST real string ({len(worst_s)} chars)")
print(f"  {'scale':>6} {'body':>5} {'px/char':>8} {'PROSE_W reads':>14}")
for pct in prefs.TEXT_SCALES:
    px = style.type_px("type_body", pct)
    r = rate(worst_s, px)
    ch = widgets.PROSE_W / r
    band = "ok" if 45 <= ch <= 75 else ("OVER 75" if ch > 75 else "*** UNDER THE 45 FLOOR ***")
    print(f"  {pct:>5}% {px:>5} {r:>8.3f} {ch:>11.1f} ch  {band}")
print()
print("  A px cap is a measure for exactly ONE font size -- widgets.py says so, at length, and then")
print("  defines two px constants. The dial made that comment's own point for it.")
