"""PROBE: how long is the hint tier's line, REALLY?

widgets.py pins CAPTION_W = 620 and its fence justifies the number two ways:

    "the reviewed-and-approved value"                          <- approved for PROSE at 13px, not this
    "at 11px the real captions are ~107-112 chars, so the cap  <- offered as a reason NOT to act
     does not even bind: they render as single lines and
     lowering it would re-wrap every one of them"

If that second claim is TRUE it is not a defence -- it is the indictment. "The cap does not bind"
means the captions are running as ~110-character SINGLE LINES and the 620 is protecting nothing.
"Lowering it would re-wrap them" names the benefit as though it were the cost: re-wrapping a
110-char line down to ~70 is what a measure is FOR.

So: measure the real strings. Every `option(rb, "...")` description actually shipped, rendered at
11px Segoe on a native font DB.

NATIVE ONLY -- offscreen stubs the font DB and every advance is fiction.

Run:  py studies/gui-aesthetics/evidence/probe_caption_measure.py
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

from PySide6.QtGui import QFont, QFontMetricsF                    # noqa: E402
from PySide6.QtWidgets import QApplication                        # noqa: E402

app = QApplication.instance() or QApplication([])
assert app.platformName() != "offscreen", "native only: offscreen stubs the font DB"

from ff9mapkit.workspace import widgets                           # noqa: E402

F11 = QFont("Segoe UI"); F11.setPixelSize(11)
M11 = QFontMetricsF(F11)


def harvest():
    """Every string literal passed as option()'s `description` arg, across the workspace."""
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
            if name != "option" or len(node.args) < 2:
                continue
            desc = node.args[1]
            # a plain literal, or an implicitly-concatenated one -> ast.Constant of str
            if isinstance(desc, ast.Constant) and isinstance(desc.value, str) and desc.value:
                out.append((py.name, node.lineno, desc.value))
    return out


caps = harvest()
print(f"CAPTION_W = {widgets.CAPTION_W}px   capacity at 11px = "
      f"~{widgets.CAPTION_W / (M11.horizontalAdvance('abcdefghijklmnopqrstuvwxyz ') / 27):.0f} chars\n")
print(f"{'file':16} {'line':>5} {'chars':>6} {'px':>7} {'wraps?':>7}  {'lines@620':>9}  {'lines@380':>9}")
print("-" * 88)

over, total = 0, 0
widths = []
for fname, lineno, s in caps:
    w = M11.horizontalAdvance(s)
    widths.append(w)
    total += 1
    wraps = "WRAPS" if w > widgets.CAPTION_W else "1 line"
    if w <= widgets.CAPTION_W:
        over += 1
    n620 = max(1, -(-int(w) // widgets.CAPTION_W))
    n380 = max(1, -(-int(w) // 380))
    print(f"{fname:16} {lineno:>5} {len(s):>6} {w:>7.0f} {wraps:>7}  {n620:>9}  {n380:>9}")

print("-" * 88)
if widths:
    ch = M11.horizontalAdvance("abcdefghijklmnopqrstuvwxyz ") / 27
    longest = max(widths)
    print(f"\n{total} option captions found.")
    print(f"  {over}/{total} fit inside the 620 cap -> render as SINGLE LINES.")
    print(f"  longest = {longest:.0f}px = ~{longest / ch:.0f} chars on ONE line.")
    print(f"  mean    = {sum(widths) / len(widths):.0f}px = ~{sum(widths) / len(widths) / ch:.0f} chars.")
    print()
    print("  THE FENCE'S CLAIM, TESTED:")
    print(f'    "the cap does not even bind" -> {"TRUE" if over == total else "PARTLY: " + str(total - over) + " do wrap"}.')
    print("    But that is the indictment, not the defence: a cap that never binds is not a measure.")
    print(f"    These lines are running at ~{sum(widths) / len(widths) / ch:.0f} chars average, against a 45-75 band.")
    print()
    for cap_try in (620, 460, 420, 380, 340):
        n = sum(max(1, -(-int(w) // cap_try)) for w in widths)
        worst = max(min(w, cap_try) for w in widths) / ch
        print(f"    cap {cap_try:>3}px -> {n:>2} total lines across {total} captions, "
              f"worst line ~{worst:.0f}ch")
else:
    print("\nNo literal option() descriptions found -- they may all be f-strings/variables.")
    print("That itself is worth knowing: this probe can only see literals.")
