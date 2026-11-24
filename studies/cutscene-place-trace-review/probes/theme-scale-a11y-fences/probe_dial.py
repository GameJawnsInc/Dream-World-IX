import sys, types, importlib.util
R="C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9"
spec=importlib.util.spec_from_file_location("gs",R+"/tools/gui_snap.py"); gs=importlib.util.module_from_spec(spec); sys.modules["gs"]=gs; spec.loader.exec_module(gs)
OUT="<SCRATCH>/review/theme-scale-a11y-fences/snaps"
def ctx(scale,w=1280,h=850,theme="mist"):
    a=types.SimpleNamespace(theme=theme,scale=scale,guided="guided",width=w,height=h,out=OUT); return gs._Ctx(a)
for sc in (100,125,150):
    c=ctx(sc)
    # cutscene doc
    win=gs._make_win(c)
    demo=gs._load_cutscene_demo(); root=gs._SCRATCH/"cd"; 
    toml=demo.make_cutscene_field(root); assert win.open_field(toml)
    win.tabs.setCurrentWidget(win.cutscene_doc); gs._settle(6)
    d=win.cutscene_doc
    for b in (d.add_step_btn,d.settings_btn,d.dup_scene_btn,d.del_scene_btn,d.board_btn):
        print(sc,"cut",repr(b.accessibleName()),"shown",repr(b.text()),"w",b.width(),"hint",b.sizeHint().width())
    print(sc,"cutscene_doc minHint",d.minimumSizeHint().width(),"win minHint",win.minimumSizeHint().width())
    # canvas fonts after scale switch
    gs._close(win)
