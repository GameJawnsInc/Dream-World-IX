"""Shared probe harness: imports tools/gui_snap.py (native Qt, pinned prefs under a scratch
LOCALAPPDATA, hidden WA_DontShowOnScreen windows) and exposes helpers."""
import sys, types, importlib.util, shutil
from pathlib import Path
REPO = Path(r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9")
OUT = Path(r"<SCRATCH>/review/x-cutscene-place")
sys.path.insert(0, str(REPO / "tools"))
spec = importlib.util.spec_from_file_location("gui_snap", REPO / "tools" / "gui_snap.py")
gs = importlib.util.module_from_spec(spec)
sys.modules["gui_snap"] = gs
spec.loader.exec_module(gs)
import ff9mapkit
assert REPO.as_posix() in ff9mapkit.__file__.replace("\\", "/"), ff9mapkit.__file__

def ctx(theme="dark", scale=100, w=1440, h=900):
    a = types.SimpleNamespace(theme=theme, scale=scale, guided="full", width=w, height=h,
                              out=str(OUT / "snaps"))
    return gs._Ctx(a)

settle = gs._settle
app = gs.app

def cut_win(c=None, root_name="cut"):
    c = c or ctx()
    win = gs._make_win(c)
    demo = gs._load_cutscene_demo()
    root = OUT / "work" / root_name
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    toml = demo.make_cutscene_field(root)
    assert win.open_field(toml)
    win.tabs.setCurrentWidget(win.cutscene_doc)
    settle(6)
    return win, toml
