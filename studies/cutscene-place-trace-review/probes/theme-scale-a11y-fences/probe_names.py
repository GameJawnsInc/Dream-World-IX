import sys, types, importlib.util
R="C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9"
spec=importlib.util.spec_from_file_location("gs",R+"/tools/gui_snap.py"); gs=importlib.util.module_from_spec(spec); sys.modules["gs"]=gs; spec.loader.exec_module(gs)
sys.path.insert(0,R+"/ff9mapkit/tests")
from PySide6.QtWidgets import QWidget, QAbstractButton, QComboBox, QAbstractSpinBox, QLineEdit, QAbstractSlider, QScrollBar, QTextEdit, QPlainTextEdit, QListWidget
from PySide6.QtGui import QAccessible
W=(QAbstractButton,QComboBox,QAbstractSpinBox,QLineEdit,QAbstractSlider,QTextEdit,QPlainTextEdit,QListWidget)
def acc(wd):
    i=QAccessible.queryAccessibleInterface(wd)
    return (i.text(QAccessible.Text.Name) or "").strip() if i else ""
def internal(wd):
    p=wd.parentWidget()
    if wd.objectName().startswith("qt_"): return True
    if isinstance(wd,QLineEdit) and isinstance(p,(QComboBox,QAbstractSpinBox)): return True
    if isinstance(wd,QAbstractButton) and isinstance(p,QLineEdit): return True
    if isinstance(wd,QScrollBar): return True
    return False
OUT="<SCRATCH>/review/theme-scale-a11y-fences/snaps"
def grab(ctx,name,w):
    if name.endswith("canvas") or name.endswith("pane"): return
    doc = getattr(w,"cutscene_doc") if name.startswith("cutscene") else (w.place_doc if name.startswith("place") else w.trace_doc)
    roots=[doc]+([doc.instruments] if hasattr(doc,"instruments") else [])
    holes=[]
    for r in roots:
        for wd in r.findChildren(QWidget):
            if isinstance(wd,W) and wd.isVisible() and not internal(wd) and not acc(wd):
                holes.append(f"{type(wd).__name__} ph={getattr(wd,'placeholderText',lambda:'')()!r} tip={wd.toolTip()[:50]!r} ro={getattr(wd,'isReadOnly',lambda:None)()} parent={type(wd.parentWidget()).__name__}")
    print(name,"unnamed:",holes)
gs._grab=grab
c=gs._Ctx(types.SimpleNamespace(theme="mist",scale=100,guided="guided",width=1280,height=850,out=OUT))
for st in ("editor","settings"): gs.snap_cutscene(c,st)


