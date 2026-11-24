import sys, types, importlib.util
R="C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9"
spec=importlib.util.spec_from_file_location("gs",R+"/tools/gui_snap.py"); gs=importlib.util.module_from_spec(spec); sys.modules["gs"]=gs; spec.loader.exec_module(gs)
OUT="<SCRATCH>/review/theme-scale-a11y-fences/snaps"
def grab(ctx,name,w):
    if name.startswith("trace-") and not name.endswith("canvas"):
        td=w.trace_doc
        print(ctx.scale,name,"status wrap",td.status.wordWrap(),"status minHint",td.status.minimumSizeHint().width(),"shown w",td.status.width(),"text:",td.status.text())
        print("   fg_box min",td.fg_box.minimumWidth(),"pitch min",td.pitch.minimumWidth(), "canvas",td.canvas.width(),td.canvas.height())
        print("   hint pill geom",td.canvas._hint.geometry().getRect(),"viewport",td.canvas.viewport().size().toTuple())
gs._grab=grab
for sc in (100,150):
    c=gs._Ctx(types.SimpleNamespace(theme="mist",scale=sc,guided="guided",width=1280,height=850,out=OUT))
    for st in ("traced","contacts","regions"): gs.snap_trace(c,st)
