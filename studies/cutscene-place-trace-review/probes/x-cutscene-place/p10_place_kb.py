import sys, time, faulthandler; sys.path.insert(0, r"<SCRATCH>/review/x-cutscene-place")
faulthandler.dump_traceback_later(80, exit=True)
import h
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractButton, QLineEdit

def desc(w):
    t = w.text() if isinstance(w, (QAbstractButton, QLineEdit)) else ""
    return f"{type(w).__name__}[{w.accessibleName() or w.objectName()}|{t[:22]!r}]"

def walk(win, start, n, owner):
    seen, w = [], start
    for i in range(n):
        seen.append((i, desc(w), "IN" if (owner.isAncestorOf(w) or w is owner) else "out"))
        nxt = w.nextInFocusChain()
        while not ((nxt.focusPolicy() & Qt.FocusPolicy.TabFocus) and nxt.isEnabled()
                   and nxt.isVisibleTo(win) and not nxt.focusProxy()):
            nxt = nxt.nextInFocusChain()
            if nxt is w: break
        w = nxt
    return seen

toml = h.OUT / "work" / "novel" / "A" / "a.field.toml"
with h.gs._no_modals():
    win = h.gs._make_win(h.ctx())
    assert win.open_field(toml)
    pd = win.place_doc; win.tabs.setCurrentWidget(pd); h.settle(3)
    pd.load_btn.click()
    t = time.time()
    while pd._loading is not None and time.time() - t < 30:
        h.settle(1); time.sleep(0.03)
    h.settle(3)
    for row in walk(win, pd.load_btn, 16, pd):
        print(*row)
    print("canvas focusPolicy", pd.canvas.focusPolicy(), "tools buttons", [ (k, pd.tools.button(k).focusPolicy()) for k in ("place","regions")])
    h.gs._close(win)
