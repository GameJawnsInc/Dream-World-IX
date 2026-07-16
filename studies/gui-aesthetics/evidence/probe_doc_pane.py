"""THE DOC PANE -- needs vs gets per tab, at real widths, with a real persisted layout.

=====================================================================================================
THIS PROBE MUST RUN NATIVE, AND THE REASON IS THE WHOLE POINT OF ITS EXISTENCE.
=====================================================================================================
Run under QT_QPA_PLATFORM=offscreen, every number below is FICTION -- and not conservatively wrong,
INVENTIVELY wrong. Measured side by side on this machine:

                            offscreen        native
    window asked 1280 ->      1296            1280
    splitter sizes         [74,1156,64]   [300,738,240]
    mid_col minimum           1156             542
    Story State need          1152             538
    Item & Equip need         1138             486

The stub font DB renders ~14px per character, so an 81-char label reports 1134px instead of ~440. That
inflated two ordinary teaching sentences into a WINDOW-WIDE CONSTRAINT: since QStackedWidget's minimum is
the max over ALL pages, offscreen "proved" that two labels on tabs you may never open pinned the entire
app at a 1296px floor and crushed the tree pane to 74px. A coherent, mechanical, checkable story about a
defect THAT DOES NOT EXIST. I was one step from fixing two innocent labels.

    THE OFFSCREEN LIE, 4th INSTANCE -- and the first that MANUFACTURED a defect rather than hiding one.
    Colour is font-independent and safe offscreen. WIDTH IS NOT. If a number came from text, go native.

HARNESS HONESTY -- the other prior burns this probe is written against:
  * "resize(1280) is a REQUEST, not a fact." Every resize is READ BACK and asserted.
  * "a None baseline that reads the shipped code is not a baseline." The comparison is FRESH DEFAULT vs
    USER-PERSISTED, both stated, neither inferred.
  * a probe that forgot show() reported isVisible() False and printed nothing. Asserted.
  * DO NOT TOUCH THE USER'S PREFS. LOCALAPPDATA is repointed to a temp dir BEFORE importing anything that
    reads it, and the real prefs file's mtime is checked at the end.

Run:  py studies/gui-aesthetics/evidence/probe_doc_pane.py     (NO offscreen -- it needs a real font DB)
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_REAL_PREFS = Path(os.environ.get("LOCALAPPDATA", "")) / "ff9mapkit" / "config" / "prefs.json"
_REAL_MTIME = _REAL_PREFS.stat().st_mtime if _REAL_PREFS.exists() else None

os.environ["LOCALAPPDATA"] = tempfile.mkdtemp(prefix="ff9probe_")   # BEFORE any ff9mapkit import
os.environ.pop("QT_QPA_PLATFORM", None)          # NATIVE. See the header -- offscreen invents widths.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "ff9mapkit"))

from PySide6.QtWidgets import QApplication, QScrollArea          # noqa: E402

from ff9mapkit.editor.theme import pick_palette     # noqa: E402
from ff9mapkit.workspace.shell import Workspace, _apply_app_theme   # noqa: E402

WIDTHS = (1280, 1440, 1600, 1920)
USER_SAVED = [300, 1198, 420]        # the real value read from the user's prefs (saved at 1920)


def main() -> int:
    app = QApplication.instance() or QApplication([])
    # ASSERT the harness, don't hope for it -- this probe is worthless offscreen and the difference is
    # silent. A stubbed font DB reports the SAME KIND of number, just wrong by 2.6x.
    assert app.platformName() != "offscreen", (
        "offscreen stubs the font DB and every width below becomes fiction -- see this file's header")
    from PySide6.QtGui import QFont, QFontInfo
    _f = QFont("Segoe UI")
    _f.setPixelSize(14)
    assert QFontInfo(_f).pixelSize() == 14, "the font DB is not resolving -- widths would be fiction"
    pal = pick_palette("dark")
    _apply_app_theme(app, pal)

    for label, sizes in (("FRESH DEFAULT", None), ("USER PERSISTED [300,1198,420]", USER_SAVED)):
        print(f"\n{'=' * 78}\n=== {label}\n")
        w = Workspace(pal)
        w.show()
        app.processEvents()
        assert w.isVisible(), "never shown -- every number would be a fiction"
        if sizes:
            w._central_split.setSizes(sizes)
            app.processEvents()

        print(f"  {'width':>6} | {'tree':>5} {'doc':>5} {'insp':>5} | {'tab':<16} {'needs':>6} "
              f"{'gets':>6}  scrollbar?")
        for width in WIDTHS:
            w.resize(width, 820)
            app.processEvents()
            assert w.width() == width, f"asked {width}, GOT {w.width()} -- a resize is a request, not a fact"
            got = w._central_split.sizes()
            for i in range(w.tabs.count()):
                name = w.tabs.tabText(i).strip()
                if name not in ("Home", "Import", "Co-op", "Build & Deploy"):
                    continue
                w.tabs.setCurrentIndex(i)
                app.processEvents()
                page = w.tabs.widget(i)
                # ASK THE WIDGET THAT ACTUALLY CARRIES THE CONTENT. A form doc is NOT a QScrollArea -- it
                # is a plain page CONTAINING one, so `page.minimumSizeHint()` reports ~64 (the page can
                # shrink because its scroll area can scroll) which is the answer to a different question.
                # Walk in to the scroll area and ask ITS widget what the cards need. A page with no scroll
                # area (Story State, Item & Equip) answers for itself.
                # ...and the pages come in BOTH shapes, which is why this is four lines and not one:
                # Home IS a QScrollArea; Import/Co-op/Build are plain pages CONTAINING one. findChildren
                # excludes self, so asking only the children reports Home as 64 and asking only the page
                # reports Import as 64 -- each shape answers the other's question.
                sa = page if isinstance(page, QScrollArea) else next(iter(page.findChildren(QScrollArea)), None)
                inner = sa.widget() if sa is not None and sa.widget() else page
                need = inner.minimumSizeHint().width()
                # ground truth: is a horizontal scrollbar actually ON SCREEN? Not "should it be".
                bar = any(s.horizontalScrollBar().isVisible() for s in page.findChildren(QScrollArea)) \
                    or (isinstance(page, QScrollArea) and page.horizontalScrollBar().isVisible())
                print(f"  {width:>6} | {got[0]:>5} {got[1]:>5} {got[2]:>5} | {name:<16} {need:>6} "
                      f"{got[1]:>6}  {'SCROLLBAR' if bar else '-'}")
        w.close()

    print("\n" + "=" * 78)
    if _REAL_MTIME is not None:
        now = _REAL_PREFS.stat().st_mtime if _REAL_PREFS.exists() else None
        print(f"  user's real prefs UNTOUCHED: {now == _REAL_MTIME}  ({_REAL_PREFS})")
    else:
        print("  (no real prefs file on this machine to protect)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
