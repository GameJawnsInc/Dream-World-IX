"""Probe 5: the whole shell -- Trace first Generate (real QProcess run_job) -> open_field -> Place
(load the project's surface, drop an NPC, draw a door, Save All) -> back to Trace -> Regenerate."""
import os, sys, shutil, tomllib, time, argparse
from pathlib import Path
REPO = Path(r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9")
HERE = Path(__file__).parent
sys.path.insert(0, str(REPO / "tools"))
os.environ.pop("PYTHONIOENCODING", None); os.environ.pop("PYTHONUTF8", None)   # the user's child env
import gui_snap as G                                          # native platform, prefs pinned to scratch
from PySide6.QtCore import QProcess
sys.path.insert(0, str(HERE))

W = HERE / "p6"
shutil.rmtree(W, ignore_errors=True); W.mkdir()
def L(*a):
    print(" ".join(str(x) for x in a), flush=True)

def wait_job(win, t=60):
    end = time.time() + t
    while getattr(win, "proc", None) and win.proc.state() != QProcess.ProcessState.NotRunning and time.time() < end:
        G._settle(1); time.sleep(0.05)
    G._settle(6)

ctx = G._Ctx(argparse.Namespace(theme="mist", scale=100, guided="full", width=1600, height=1000,
                                out=str(W / "snaps")))
with G._no_modals():
    win = G._make_win(ctx)
    td = win.trace_doc
    win.tabs.setCurrentWidget(td); G._settle()
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (800, 600), (38, 42, 58)); d = ImageDraw.Draw(img)
    d.polygon([(272, 186), (528, 186), (760, 588), (40, 588)], fill=(158, 132, 96)); img.save(W / "hall.png")
    td.load_image(W / "hall.png"); G._settle()
    td.canvas._commit_floor([(60.0, 430.0), (320.0, 430.0), (250.0, 240.0), (130.0, 240.0)])
    from ff9mapkit import imagefield as IF
    td.tools.set_current("regions"); G._settle()
    td.rkind_btns["event"].setChecked(True); td.ev_msg.setText("Go → north")
    cam = td.canvas.camera()
    td._on_region_drawn([IF.click_to_world(cam, p) for p in [(200.0, 400.0), (280.0, 400.0), (280.0, 370.0), (200.0, 370.0)]])
    td.name_box.setText("HALL"); td.id_box.setText("30130")
    td._ask_out = lambda: str(W)
    td.on_generate(); wait_job(win)
    L("files", sorted(p.name for p in (W / "hall-field").rglob("*")))
    L("trace status:", td.status.text(), "| project armed:", td._project, "| gen btn:", td.gen_btn.text())
    L("console tail:", win.console.toPlainText()[-500:] if hasattr(win, "console") else [n for n in dir(win) if "console" in n.lower()][:8])
    L("problems:", [w.text() for w in win.findChildren(type(td.status)) if "failed" in w.text().lower() or "Image" in w.text()][:6])
    L("1. first Generate: editor tab =", win.tabs.tabText(win.tabs.currentIndex()), "| member_paths",
      list(getattr(win, "member_paths", {}).keys()))
    G._close(win)
