"""Status-line clipping of the appended warnings, busy-Generate silence, floor polygon in Regions mode."""
import sys, importlib.util, shutil
from pathlib import Path
REPO = Path(r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9")
OUT = Path(r"<SCRATCH>/review/trace-ux-look")
spec = importlib.util.spec_from_file_location("gui_snap", REPO / "tools" / "gui_snap.py")
gs = importlib.util.module_from_spec(spec); sys.modules["gui_snap"] = gs; spec.loader.exec_module(gs)
spec2 = importlib.util.spec_from_file_location("_tf", REPO / "ff9mapkit" / "tests" / "test_imagefield.py")
tf = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(tf)
from ff9mapkit import imagefield as IF
root = OUT / "room3"; shutil.rmtree(root, ignore_errors=True); root.mkdir(parents=True)
photo, floor = tf._paint_room(root)

class A: pass
for scale in (100, 150):
    a = A(); a.theme = "mist"; a.scale = scale; a.guided = "guided"; a.width = 1280; a.height = 850; a.out = str(OUT / "snaps")
    win = gs._make_win(gs._Ctx(a)); win.tabs.setCurrentWidget(win.trace_doc); gs._settle(4)
    td = win.trace_doc
    td._run = lambda argv, **kw: True
    td._ask_out = lambda: str(root / "out")
    td.load_image(photo)
    td.canvas._commit_floor([(float(x), float(y)) for x, y in floor]); gs._settle(2)
    td.on_generate()                                 # now a project exists
    td.tools.set_current("regions"); gs._settle(2)
    cam = td.canvas.camera()
    td.gw_to.setValue(0)
    td._on_region_drawn([IF.click_to_world(cam, p) for p in [(40.0, 400.0), (150.0, 400.0), (150.0, 430.0), (40.0, 430.0)]])
    td._refresh(); gs._settle(2)
    fm = td.status.fontMetrics()
    txt = td.status.text()
    need = fm.horizontalAdvance(txt)
    print(f"scale {scale}: status label width {td.status.width()} text needs {need} -> clipped {need > td.status.width()}")
    print("   text:", txt)
    # how much survives
    vis = ""
    for ch in txt:
        if fm.horizontalAdvance(vis + ch) > td.status.width():
            break
        vis += ch
    print("   visible:", vis)
    kinds = [it.data(0) for it in td.canvas.scene().items()]
    print("   regions tool: traceline items", kinds.count("traceline"), "tracept", kinds.count("tracept"), "outset", kinds.count("outset"))
    # Generate while another job is busy
    before = td.status.text()
    td._run = lambda argv, **kw: False
    td.gw_to.setValue(4005)
    td._regions[0]["to"] = 4005; td._refresh(); gs._settle(1)
    s0 = td.status.text()
    td.on_generate(); gs._settle(1)
    print("   busy Generate: status changed?", td.status.text() != s0)
    gs._close(win)
