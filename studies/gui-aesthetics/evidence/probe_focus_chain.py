"""WCAG 2.4.7 -- walk the REAL Workspace's focus chain and find every tab stop that shows NOTHING.

`* { outline: 0 }` (style.py) kills Fusion's native focus rect APP-WIDE, and style.py claims the QSS then
gives "every interactive control ONE deliberate accent ring". Round 6 fenced that claim for the seven
id-scoped BUTTONS and stopped there. The adversarial review counted the rest: 14 of 115 visible+enabled
tab stops with a 0px focus delta, INCLUDING THE MAIN OUTPUT CONSOLE.

WHAT THIS MEASURES AND WHAT IT CANNOT. A focus ring is a COLOUR/geometry change on a widget that already
exists, so offscreen is honest here -- this study's offscreen burns are all about TEXT-DERIVED WIDTHS, and
none of these numbers are. (The delta counts changed pixels; it says nothing about how wide anything is.)
Still: the sheet is a WIDGET stylesheet on the Workspace, so this walks the real window rather than
building bare widgets, and it CLEARS FOCUS before every baseline -- Qt focuses the first tab-chain widget
on show(), which already produced one false "no focus ring" finding this round.

Run:  py studies/gui-aesthetics/evidence/probe_focus_chain.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ["LOCALAPPDATA"] = tempfile.mkdtemp(prefix="ff9fc_")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["FF9MAPKIT_NO_THUMBS"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "ff9mapkit"))

from PySide6.QtCore import Qt                                                # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget                          # noqa: E402

from ff9mapkit.editor.theme import pick_palette                              # noqa: E402
from ff9mapkit.workspace.shell import Workspace, _apply_app_theme            # noqa: E402


def delta(app, w) -> int:
    """Pixels that change when `w` takes focus, measured from a KNOWN-UNFOCUSED baseline."""
    w.clearFocus()
    app.processEvents()
    if w.hasFocus():                       # something re-took it; not measurable
        return -1
    rest = w.grab().toImage()
    w.setFocus(Qt.FocusReason.TabFocusReason)
    app.processEvents()
    if not w.hasFocus():                   # refused focus -- not a tab stop after all
        return -2
    after = w.grab().toImage()
    w.clearFocus()
    app.processEvents()
    if rest.size() != after.size():
        return -3                          # the box MOVED: a ring that reflows is its own defect
    return sum(rest.pixelColor(x, y) != after.pixelColor(x, y)
               for y in range(rest.height()) for x in range(rest.width()))


def main() -> int:
    app = QApplication.instance() or QApplication([])
    pal = pick_palette("dark")
    _apply_app_theme(app, pal)
    win = Workspace(pal)
    win.resize(1280, 820)
    win.show()
    app.processEvents()
    assert win.isVisible(), "never shown -- every number would be a fiction"
    # THE CONSOLE IS COLLAPSED BY DEFAULT, so a plain walk never sees the app's biggest read-only surface.
    # The first cut of this probe reported 6 dead stops and the main Output console was NOT among them --
    # not because it has a ring, but because `isVisible()` was False. Open it, or measure a smaller app.
    win._toggle_console()
    app.processEvents()
    assert win.output.isVisible(), "the console did not open -- the console rows below would be missing"

    # A TAB STOP IS WHAT TAB REACHES -- not what claims to be reachable. Two filters were tried here and
    # both over-counted, each in a way that manufactures a defect:
    #   * `focusPolicy != NoFocus` swept in a ClickFocus (2) QLabel a Tab walk can never land on;
    #   * `focusPolicy & TabFocus` swept in QAbstractScrollArea's VIEWPORT, which reports StrongFocus and
    #     is NOT in Qt's chain. (The adversarial review that prompted this work counted "CampaignMap + its
    #     viewport" -- the same widget twice, by the same mistake. Reproducing someone's number does not
    #     make it right; reproducing their METHOD reproduces their error.)
    # `focusNextChild()` IS what Qt does on Tab, so it is the only honest census.
    seen, dead, reflow = {}, [], []
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
            if not w.isVisible() or not w.isEnabled():
                continue
            if w.objectName().startswith("qt_"):        # Qt's own internals
                continue
            key = (type(w).__name__, w.objectName(), w.accessibleName())
            if key in seen:
                continue
            d = delta(app, w)
            seen[key] = d
            if d == 0:
                dead.append((key, w.width(), w.height()))
            elif d == -3:
                reflow.append(key)

    print(f"  {len(seen)} distinct visible+enabled tab stops walked\n")
    print(f"  DEAD (0 px on focus): {len(dead)}")
    for (cls, oid, acc), ww, hh in sorted(dead):
        print(f"      {cls:<22} #{oid or '-':<12} {acc or '-':<22} {ww}x{hh}")
    if reflow:
        print(f"\n  RING REFLOWS THE BOX: {len(reflow)}")
        for k in reflow:
            print(f"      {k}")

    print("\n  Does the sheet even mention them?")
    from ff9mapkit.workspace.style import qss
    css = qss(pal)
    for sel in ("QPlainTextEdit:focus", "QTextEdit:focus", "QScrollArea:focus",
                "QAbstractScrollArea:focus", "QTreeWidget:focus", "QGraphicsView:focus"):
        print(f"      {sel:<28} {'yes' if sel in css else 'NO'}")
    return 0 if not dead else 1


if __name__ == "__main__":
    raise SystemExit(main())
