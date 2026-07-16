"""Round 6b -- verify every fix the adversarial review forced, on the review's own terms.

THE REVIEW'S HEADLINE LESSON, and the reason this file exists at all: `probe_doc_pane.py` repointed
LOCALAPPDATA at an empty tempdir, which makes `prefs.text_scale()` fall through to `os_text_scale()` --
THE DEVELOPER'S WINDOWS SLIDER. So the probe that justified `setMinimumWidth(700)` measured exactly one
text scale: this machine's. An empty tempdir is not a clean room; it is a hole the OS falls through.

    EVERY PROBE MUST PIN prefs.text_scale EXPLICITLY AND SWEEP ALL FOUR RUNGS.

So: native (widths are text-derived), Fusion forced, scale PINNED per rung, every resize read back.

Run:  py studies/gui-aesthetics/evidence/verify_review_fixes.py     (NO offscreen)
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ["LOCALAPPDATA"] = tempfile.mkdtemp(prefix="ff9vr_")
os.environ.pop("QT_QPA_PLATFORM", None)
os.environ["FF9MAPKIT_NO_THUMBS"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "ff9mapkit"))

from PySide6.QtGui import QFont, QFontInfo                                   # noqa: E402
from PySide6.QtWidgets import QApplication                                   # noqa: E402

from ff9mapkit import prefs                                                  # noqa: E402
from ff9mapkit.editor import theme                                           # noqa: E402
from ff9mapkit.editor.theme import pick_palette                              # noqa: E402
from ff9mapkit.workspace.shell import Workspace, _apply_app_theme            # noqa: E402


def _lum(h):
    h = h.lstrip("#")
    ch = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in ch]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def con(a, b):
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def main() -> int:
    app = QApplication.instance() or QApplication([])
    assert app.platformName() != "offscreen", "native only -- widths here are text-derived"
    _f = QFont("Segoe UI")
    _f.setPixelSize(14)
    assert QFontInfo(_f).pixelSize() == 14, "font DB not resolving"
    pal = pick_palette("dark")
    _apply_app_theme(app, pal)
    ok = True

    print("=== 1. THE WINDOW CAN BE NARROW AGAIN (the pin is gone)\n")
    print("   The floor GROWS with the dial, and that is correct -- the CONTENT grows. What the pin did,")
    print("   measured both ways, is the opposite of what its comment claimed:")
    print("       with pin:  844  848  856  868      <- nearly FLAT")
    print("       reverted:  686  723  841  964      <- follows the content")
    print("   It cost 158px at 100% (720 unreachable, and 720 is what the toolbar a11y test asks for),")
    print("   and 'helped' at 150% only by letting the document sit BELOW its own 796 content minimum --")
    print("   i.e. permission to clip, not a floor. Both halves are why the line is gone.\n")
    print(f"   {'scale':>6} | {'asked 720 -> got':>17} | {'mid_col pin':>12} | verdict")
    for pct in prefs.TEXT_SCALES:
        w = Workspace(pal)
        w._apply_text_scale(pct)          # PINNED. never prefs.text_scale() -- that reads the OS slider.
        w.show()
        app.processEvents()
        w.resize(720, 600)
        app.processEvents()
        got, pin = w.width(), w._central_split.widget(1).minimumWidth()
        # THE ASSERTION IS "NOTHING IS PINNED", not "720 always fits". At 110%+ the content itself needs
        # more than 720 and Qt is right to refuse -- a 21px body genuinely does not fit a 720px three-pane
        # window. 720 must be reachable at the DEFAULT scale, which is what the a11y suite exercises.
        good = pin == 0 and (got <= 720 or pct > 100)
        ok &= good
        note = "ok" if good else ("STILL PINNED" if pin else "720 unreachable at the default scale")
        extra = "  (content-derived, not a pin)" if got > 720 and pin == 0 else ""
        print(f"   {pct:>5}% | {got:>17} | {pin:>12} | {note}{extra}")
        w.close()

    print("\n=== 2. THE TWO SUB-AA :pressed RULES (bar 4.5 -- both are text)\n")
    print(f"   {'palette':<16} {'hub help_fg/help':>17} {'badge accent_fg/accent':>23}")
    worst_h = worst_b = 99.0
    for n in theme.THEMES:
        d = theme.derive(dict(theme.THEMES[n]))
        h, b = con(d["help_fg"], d["help"]), con(d["accent_fg"], d["accent"])
        worst_h, worst_b = min(worst_h, h), min(worst_b, b)
        print(f"   {n:<16} {h:>17.2f} {b:>23.2f}")
    ok &= worst_h >= 4.5 and worst_b >= 4.5
    print(f"\n   worst: hub {worst_h:.2f} (was 2.23 on solarized-dark, 7/8 sub-AA)")
    print(f"          badge {worst_b:.2f} (was 1.59 on nord, 7/8 sub-AA)")

    print("\n=== 3. THE MAP GLYPH IS BACK ON THE TREE'S TIER (bar 3.0 -- a drawing)\n")
    worst_m = min(con(theme.derive(dict(theme.THEMES[n]))["muted"],
                      theme.derive(dict(theme.THEMES[n]))["surface"]) for n in theme.THEMES)
    ok &= worst_m >= 3.0
    print(f"   muted on surface, worst {worst_m:.2f}   (text_subtle was 3.06 -- the exact number KEYLINE")
    print("   moved the TREE off, one file over, citing 'muted is the same tier's honest value')")

    print("\n=== 4. THE ACTIVE RAIL SEGMENT REACTS (the :pressed/:checked tie)\n")
    from PySide6.QtWidgets import QToolButton, QVBoxLayout, QWidget
    from ff9mapkit.workspace.style import qss
    host = QWidget()
    host.setStyleSheet(qss(pal))
    lay = QVBoxLayout(host)
    seg = QToolButton()
    seg.setObjectName("railSeg")
    seg.setText("Sample")
    seg.setCheckable(True)
    seg.setChecked(True)                  # THE state the old fence never entered
    lay.addWidget(seg)
    host.resize(320, 80)
    host.show()
    app.processEvents()
    seg.clearFocus()
    app.processEvents()
    rest = seg.grab().toImage()
    seg.setDown(True)
    app.processEvents()
    after = seg.grab().toImage()
    seg.setDown(False)
    n = sum(rest.pixelColor(x, y) != after.pixelColor(x, y)
            for y in range(rest.height()) for x in range(rest.width()))
    ok &= n > 0
    print(f"   CHECKED railSeg, rest -> pressed: {n} px changed   (was 0 -- :pressed tied :checked at")
    print("   (0,1,1,1) and lost on source order, so the segment you are ON was dead)")

    print("\n" + "=" * 74)
    print("  ALL REVIEW FIXES VERIFIED" if ok else "  SOMETHING IS STILL WRONG")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
