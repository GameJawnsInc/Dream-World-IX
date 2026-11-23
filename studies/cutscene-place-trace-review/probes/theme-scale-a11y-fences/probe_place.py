import sys, types, importlib.util
R="C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9"
spec=importlib.util.spec_from_file_location("gs",R+"/tools/gui_snap.py"); gs=importlib.util.module_from_spec(spec); sys.modules["gs"]=gs; spec.loader.exec_module(gs)
OUT="<SCRATCH>/review/theme-scale-a11y-fences/snaps"
captured={}
orig=gs._grab
def grab(ctx,name,w):
    if name.startswith("place-") and not name.endswith("canvas"):
        pd=w.place_doc
        print(ctx.scale,name,"win minHint",w.minimumSizeHint().width(),"place_doc minHint",pd.minimumSizeHint().width(),"field_label",pd.field_label.text()[:40])
        for wd in (pd.field_label,pd.load_btn,pd.cam_box,pd.tools,*pd.mode_btns.values(),pd.ent_label,pd.ent_box,*pd.rkind_btns.values(),pd.gw_to_label,pd.gw_to,pd.gw_ent):
            if wd.isVisible(): print("   ",type(wd).__name__,repr(getattr(wd,'text',lambda:'')()) if hasattr(wd,'text') else '', "w",wd.width(),"minHint",wd.minimumSizeHint().width(),"hint",wd.sizeHint().width())
    if name.startswith("trace-") and not name.endswith("canvas"):
        td=w.trace_doc
        print(ctx.scale,name,"win minHint",w.minimumSizeHint().width(),"trace_doc minHint",td.minimumSizeHint().width(), "canvas h", td.canvas.height())
gs._grab=grab
for sc in (100,125,150):
    a=types.SimpleNamespace(theme="mist",scale=sc,guided="guided",width=1280,height=850,out=OUT)
    c=gs._Ctx(a)
    for st in ("fork","regions"):
        gs.snap_place(c,st)
    for st in ("contacts","regions"):
        gs.snap_trace(c,st)
