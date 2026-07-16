"""PROBE: the uncapped hint tier -- how wide does it really get, and how many sites?

COLUMN's claim, from round 5's audit: `CAPTION_W = 620` governs exactly ONE code path (`option()`'s radio
descriptions) and has never once fired; every OTHER caption is a raw QLabel + setWordWrap with NO cap,
wrapping to whatever the pane hands it -- 125ch at a 1280 window, 257 at 1920, 388 at 2560, growing 1:1
with the monitor.

Not inherited. This round has now had FOUR numbers arrive as fact and turn out wrong (the OS text slider,
`em`, "the app runs windows11", and my own 61.9/41.3ch measure). So: build the REAL app, at REAL window
widths, and read `label.width()` off the REAL labels -- with a rate measured on THEIR OWN TEXT, never on
the alphabet (one space in 27 vs English's ~1 in 6 understates the measure by ~9%; that is exactly how
GAUGE's first answer was wrong).

NATIVE ONLY -- offscreen stubs the font DB. Fusion, because the app forces Fusion (shell.py:129).

Run:  py studies/gui-aesthetics/evidence/probe_column.py
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

from PySide6.QtGui import QFontMetricsF                                     # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel                          # noqa: E402

app = QApplication.instance() or QApplication([])
assert app.platformName() != "offscreen", "native only: offscreen stubs the font DB"
app.setStyle("fusion")

from ff9mapkit.editor import theme                                          # noqa: E402
from ff9mapkit.workspace import shell as S                                  # noqa: E402
from ff9mapkit.workspace import style, widgets                              # noqa: E402

print("=" * 84)
print("1  THE CENSUS -- who is capped, who is loose?")
print("=" * 84)
capped = loose = 0
per_file = {}
for py in sorted((KIT / "ff9mapkit" / "workspace").glob("*.py")):
    src = py.read_text(encoding="utf-8")
    tree = ast.parse(src)
    # every `<x>.setProperty("role", "caption")` -- is <x> a Prose, or a bare QLabel?
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if getattr(fn, "attr", None) != "setProperty" or len(node.args) != 2:
            continue
        a0, a1 = node.args
        if not (isinstance(a1, ast.Constant) and a1.value == "caption"):
            continue
        per_file[py.name] = per_file.get(py.name, 0) + 1
print(f"  role=\"caption\" assignment sites: {sum(per_file.values())}")
for f, n in sorted(per_file.items(), key=lambda kv: -kv[1]):
    print(f"    {f:16} {n:>3}")

print()
print("=" * 84)
print("2  THE LIVE MEASURE -- the REAL labels, in the REAL app, at REAL widths")
print("=" * 84)
pal = theme.derive(dict(theme.THEMES["mist"]))
win = S.Workspace(pal)
win.show()
for _ in range(3):
    app.processEvents()

# aim at the two docs the user actually looks at
win.tabs.setCurrentWidget(win.import_field)
for _ in range(3):
    app.processEvents()


def sample(width):
    win.setFixedWidth(width)
    for _ in range(5):
        app.processEvents()
    assert win.width() == width, f"asked {width}, got {win.width()} -- run void"
    rows = []
    for doc, tag in ((win.import_field, "import"), (win.build_deploy, "build")):
        for lab in doc.findChildren(QLabel):
            if lab.property("role") != "caption" or not lab.isVisible():
                continue
            t = lab.text()
            if len(t) < 40:
                continue
            m = QFontMetricsF(lab.font())
            rate = m.horizontalAdvance(t) / len(t)          # ITS OWN text -- never the alphabet
            rows.append((tag, lab.width(), len(t), lab.width() / rate,
                         isinstance(lab, widgets.Prose), t))
    return rows


print(f"  {'window':>7}  {'labels':>7}  {'widest px':>10}  {'worst ch/line':>14}  {'over 75':>8}")
for wpx in (1280, 1600, 1920, 2560):
    rows = sample(wpx)
    if not rows:
        print(f"  {wpx:>7}  (none visible)")
        continue
    widest = max(r[1] for r in rows)
    worst = max(r[3] for r in rows)
    over = sum(1 for r in rows if r[3] > 75)
    print(f"  {wpx:>7}  {len(rows):>7}  {widest:>10.0f}  {worst:>14.1f}  {over:>4}/{len(rows)}")

print()
rows = sample(1920)
rows.sort(key=lambda r: -r[3])
print("  THE WORST OFFENDERS at a 1920 window:")
print(f"  {'doc':>7} {'px':>6} {'chars':>6} {'ch/line':>8} {'Prose?':>7}")
for tag, w, n, ch, is_prose, t in rows[:6]:
    print(f"  {tag:>7} {w:>6} {n:>6} {ch:>8.1f} {str(is_prose):>7}   {t[:44].encode("ascii","replace").decode()!r}")

print()
capped_n = sum(1 for r in rows if r[4])
print(f"  Prose-capped: {capped_n}/{len(rows)}   loose: {len(rows) - capped_n}/{len(rows)}")

print()
print("=" * 84)
print("3  WHAT A CAP WOULD DO  (the caption rung is 12px now -- QUARTO P1 moved it)")
print("=" * 84)
cap_px = style.type_px("type_caption", 100)
if rows:
    rates = [QFontMetricsF(QLabel().font()).horizontalAdvance(r[5]) / len(r[5]) for r in rows[:1]]
worst_s = rows[0][5] if rows else ""
lab = QLabel(worst_s)
lab.setStyleSheet(f"font-size: {cap_px}px;")
lab.ensurePolished()
rate = QFontMetricsF(lab.font()).horizontalAdvance(worst_s) / len(worst_s)
print(f"  the widest real caption, {len(worst_s)} chars, at the {cap_px}px rung -> {rate:.3f} px/char")
for cap in (620, 560, 480, 440, 420, 380):
    ch = cap / rate
    band = "ok" if 45 <= ch <= 75 else ("OVER 75" if ch > 75 else "under 45")
    lines = max(1, -(-int(QFontMetricsF(lab.font()).horizontalAdvance(worst_s)) // cap))
    print(f"    cap {cap:>3}px -> {ch:>5.1f} ch/line   {band:>7}   that string wraps to {lines} lines")

win.close()
app.processEvents()
print()
print("A cap is only half of it: the OTHER half is that these are raw QLabels. widgets.Prose already")
print("exists, already scales with the dial (GAUGE), and already fixes the silent-clip trap a raw")
print("setMaximumWidth has -- QBoxLayout asks heightForWidth at the CELL width, then lays out at the cap.")
