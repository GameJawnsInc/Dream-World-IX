"""AUDIT: what does the app CLIP at each text scale?

CALIBRE ships a text-size dial. The type is the easy half -- QUARTO P3 put all eight sizes in one table
and `qss(pal, density, scale)` reaches every one. The hard half is GEOMETRY: ~75 setFixed*/setMinimum*/
setMaximum* sites pin boxes around text, and `setFixedSize` CLIPS rather than grows. A dial that silently
cuts the "?" out of a help badge at 125% is worse than no dial.

So: do not guess, and do not trust the "75 unaudited sites" figure either -- most pins are panel geometry
that has nothing to do with the font. Walk the REAL widget tree at each scale and report every widget
whose content outgrows the box someone pinned for it.

METHOD. For each scale, build the real Workspace, apply the scaled sheet, and for every widget compare
sizeHint() against a FIXED pin (minimumSize == maximumSize on an axis). A widget whose hint exceeds its
pin is clipped -- the pin wins, the content loses, and nothing raises.

THE CRITERION IS INK, NOT sizeHint. sizeHint bakes in padding, so comparing it to a pin reports padding
COMPRESSION as clipping -- cosmetic, not a defect. The first cut did exactly that and flagged a button
whose label renders fine. What breaks is the font's line box (plus borders) exceeding its pinned box.

WHAT THIS CANNOT SEE, stated so nobody reads a clean run as proof of safety:
  * layouts that overflow their PARENT without any widget being individually over-pinned
  * the toolbar (it chevrons rather than clips -- that is a discoverability cost, measured separately by
    probe_toolbar_budget.py, and the honest number is that 14px already costs an item at 1280)
  * hero.py, which paints with QPainter at hard pixel sizes and no QSS reaches it (that is PLINTH)
  * anything only built on demand (dialogs, menus, the concept badge's What's-This bubble)

NATIVE ONLY -- offscreen stubs the font DB, so every sizeHint under it is fiction. Style is forced to
Fusion because the app forces Fusion (shell.py:129).

Run:  py studies/gui-aesthetics/evidence/audit_text_scale.py
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))
os.environ["FF9MAPKIT_NO_THUMBS"] = "1"

from PySide6.QtWidgets import QApplication, QWidget                        # noqa: E402

app = QApplication.instance() or QApplication([])
assert app.platformName() != "offscreen", "native only: offscreen stubs the font DB"
app.setStyle("fusion")

from ff9mapkit import prefs                                                # noqa: E402
from ff9mapkit.editor import theme                                         # noqa: E402
from ff9mapkit.workspace import shell as S                                 # noqa: E402
from ff9mapkit.workspace import style                                      # noqa: E402

PAL = theme.derive(dict(theme.THEMES["mist"]))


def label_for(w):
    txt = ""
    for attr in ("text", "windowTitle", "accessibleName"):
        try:
            v = getattr(w, attr, lambda: "")()
            if v:
                txt = str(v)[:28]
                break
        except Exception:
            pass
    name = w.objectName() or w.__class__.__name__
    return f"{name}{' ' + txt!r}" if txt else name


def clipped_at(scale):
    win = S.Workspace(PAL)
    win.setStyleSheet(style.qss(PAL, "comfortable", scale))
    win.resize(1280, 860)
    win.show()
    for _ in range(3):
        app.processEvents()

    # ALSO build the surfaces that only exist once a project is open -- the form doc owns BOTH known
    # type-dependent pins (the caption note's setFixedHeight, the "?" badge's setFixedSize circle) and
    # neither is in the tree at startup. The first cut of this audit reported them clean, which was the
    # audit not looking rather than the app not breaking.
    extra = []
    try:
        from ff9mapkit.workspace import forms_qt
        b = forms_qt._concept_badge("walkmesh", PAL)
        if b:
            b[0].setStyleSheet(style.qss(PAL, "comfortable", scale))
            b[0].ensurePolished()
            extra.append(b[0])
    except Exception as e:                                     # never let coverage silently shrink
        print(f"      !! could not build the concept badge: {e}")

    hits = []
    for w in list(win.findChildren(QWidget)) + extra:
        if w in extra:
            pass
        elif not w.isVisible():
            continue
        mn, mx = w.minimumSize(), w.maximumSize()
        # THE CRITERION IS THE TEXT, NOT THE sizeHint. sizeHint bakes in padding, so comparing it to a pin
        # reports PADDING COMPRESSION as clipping -- which is cosmetic, not a defect, and made the first
        # cut of this audit flag a button that renders its label perfectly well. What actually breaks is
        # ink: the font's line box (plus borders) exceeding the box someone pinned around it.
        txt = ""
        try:
            txt = w.text() if hasattr(w, "text") else ""
        except Exception:
            txt = ""
        if not txt:
            continue
        line = w.fontMetrics().height()
        border = 2                                             # 1px each side; the sheet's controls
        need = line + border
        if mn.height() == mx.height() and 0 < mx.height() < 16777215 and need > mx.height():
            hits.append((label_for(w), "H", need, mx.height()))
        adv = w.fontMetrics().horizontalAdvance(txt) + border
        if mn.width() == mx.width() and 0 < mx.width() < 16777215 and adv > mx.width():
            hits.append((label_for(w), "W", adv, mx.width()))
    for w in extra:
        w.deleteLater()
    win.close()
    win.deleteLater()
    app.processEvents()
    # dedupe: the same pinned widget class recurs (e.g. one note per form field)
    seen, out = set(), []
    for lab, axis, h, pin in hits:
        key = (lab.split(" ")[0], axis, h, pin)
        if key not in seen:
            seen.add(key)
            out.append((lab, axis, h, pin))
    return out


print("THE TYPE TABLE AT EACH SCALE (half-up; Python's round() is banker's and would break ties to even)")
print(f"  {'rung':14} " + "".join(f"{p:>7}%" for p in prefs.TEXT_SCALES))
for k in style._TYPE:
    row = "".join(f"{style.type_px(k, p):>8}" for p in prefs.TEXT_SCALES)
    print(f"  {k:14} {row}")

print()
print("WIDGETS WHOSE CONTENT OUTGROWS A FIXED PIN (setFixedSize/-Height clips; it never grows)")
for pct in prefs.TEXT_SCALES:
    hits = clipped_at(pct)
    print(f"\n  --- {pct}% ---")
    if not hits:
        print("      nothing clipped")
    for lab, axis, h, pin in hits[:12]:
        print(f"      {lab:44} {axis} hint {h:>3} vs pin {pin:>3}   (-{h - pin}px)")
    if len(hits) > 12:
        print(f"      ... and {len(hits) - 12} more")

print()
print("100% MUST be empty. Anything there is a defect that exists TODAY, at the shipped setting,")
print("and is not CALIBRE's to fix. Anything at 110+ is CALIBRE's price of admission.")
