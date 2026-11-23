import sys, types, importlib.util
R="C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9"
spec=importlib.util.spec_from_file_location("gs",R+"/tools/gui_snap.py"); gs=importlib.util.module_from_spec(spec); sys.modules["gs"]=gs; spec.loader.exec_module(gs)
from PySide6.QtWidgets import QPushButton, QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
OUT="<SCRATCH>/review/theme-scale-a11y-fences/snaps"
c=gs._Ctx(types.SimpleNamespace(theme="mist",scale=100,guided="guided",width=1280,height=850,out=OUT))
with gs._no_modals():
    win=gs._make_win(c)
    demo=gs._load_cutscene_demo(); toml=demo.make_cutscene_field(gs._SCRATCH/"kb")
    assert win.open_field(toml); win.tabs.setCurrentWidget(win.cutscene_doc); gs._settle(6)
    d=win.cutscene_doc
    btns=[b for b in d.ladder.findChildren(QPushButton) if b.property("role")=="rowtool" and b.isVisible()]
    print("rowtools",len(btns), "sizes", sorted({(b.width(),b.height()) for b in btns}))
    down=[b for b in btns if b.accessibleName().startswith("Move this step down") and b.accessibleName().endswith("step 0")][0]
    up0=[b for b in btns if b.accessibleName().startswith("Move this step up") and b.accessibleName().endswith("step 0")][0]
    print("up on step0 enabled:",up0.isEnabled())
    win.activateWindow(); down.setFocus(Qt.FocusReason.TabFocusReason); gs._settle(2)
    print("focus before:",QApplication.focusWidget() is down, down.accessibleName())
    QTest.keyClick(down, Qt.Key.Key_Space); gs._settle(6)
    fw=QApplication.focusWidget()
    print("focus after:",type(fw).__name__ if fw else None, fw.accessibleName() if fw else None, "steps now:", [list(s.keys())[0] for s in d._steps()])
    print("rows focusable:", [type(w).__name__+":"+str(w.focusPolicy()) for w in d.ladder.children() if w.metaObject().className()=="_StepRow"][:2])
    gs._close(win)
