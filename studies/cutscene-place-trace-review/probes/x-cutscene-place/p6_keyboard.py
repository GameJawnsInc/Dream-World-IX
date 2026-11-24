import sys; sys.path.insert(0, r"<SCRATCH>/review/x-cutscene-place")
import h
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QAbstractButton, QLineEdit

def desc(w):
    if w is None: return "None"
    t = w.text() if isinstance(w, (QAbstractButton, QLineEdit)) and hasattr(w, "text") else ""
    return f"{type(w).__name__}[{w.accessibleName() or w.objectName()}|{t[:22]!r}|pol={int(w.focusPolicy().value)}]"

def walk(win, start, n, owner):
    # Qt's own Tab rule (QWidget::focusNextPrevChild): next in the focus chain that accepts TabFocus,
    # is enabled and visible -- walked by hand because a WA_DontShowOnScreen window never activates.
    seen = []
    w = start
    for i in range(n):
        inside = owner.isAncestorOf(w) or w is owner
        seen.append((i, desc(w), "IN" if inside else "out"))
        nxt = w.nextInFocusChain()
        while not ((nxt.focusPolicy() & Qt.FocusPolicy.TabFocus) and nxt.isEnabled()
                   and nxt.isVisibleTo(win) and not nxt.focusProxy()):
            nxt = nxt.nextInFocusChain()
            if nxt is w: break
        w = nxt
    return seen

with h.gs._no_modals():
    win, toml = h.cut_win()
    d = win.cutscene_doc
    d._edit_step(2); h.settle(4)
    print("== CUTSCENE (editor open on step 2) ==")
    for row in walk(win, d.rail, 45, d):
        print(*row)
    # instruments (docked in the inspector) reachable?
    ins = d.instruments
    print("stage_btn focus policy", d.stage_btn.focusPolicy(), "in inspector", ins.parent() is not None)
    h.gs._close(win)
