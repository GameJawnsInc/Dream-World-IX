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

W = HERE / "p5"
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
    td.name_box.setText("HALL"); td.id_box.setText("30130")
    td._ask_out = lambda: str(W)
    td.on_generate(); wait_job(win)
    L("1. first Generate: editor tab =", win.tabs.tabText(win.tabs.currentIndex()), "| member_paths",
      list(getattr(win, "member_paths", {}).keys()))
    toml = W / "hall-field" / "HALL.field.toml"
    # 2. Place on it
    win.tabs.setCurrentWidget(win.place_doc); G._settle()
    pd = win.place_doc
    L("2. Place member", pd._member, "blocked", pd._blocked, "source", pd._source, "status", pd.status.text()[:120] if hasattr(pd, "status") else "")
    pd.on_load()
    for _ in range(200):
        G._settle(1)
        if pd._loading is None:
            break
        time.sleep(0.05)
    L("   loaded: surface tris", len(pd.canvas._surface_tris or []), "status", pd.status.text()[:120] if hasattr(pd, "status") else "")
    tri = pd.canvas._surface_tris[0]
    cx = sum(v[0] for v in tri) / 3; cz = sum(v[2] for v in tri) / 3
    pd._on_surface_clicked({"xz": (cx, cz), "pos": (cx, 0.0, cz), "floor": 0,
                            "stacked": [{"xz": (cx, cz), "pos": (cx, 0.0, cz), "floor": 0, "tri": 0, "s": 1.0}]})
    G._settle()
    data = win._doc("HALL").data
    L("   NPCs in open doc", [n.get("name") for n in data.get("npc", [])])
    from ff9mapkit.workspace import placedoc as P
    L("   door", P.place_gateway(data, [(cx - 100, cz - 50), (cx + 100, cz - 50), (cx + 100, cz + 50), (cx - 100, cz + 50)], 4005))
    win._on_place_edit("HALL", "door"); G._settle()
    win._save_all(); G._settle()
    on_disk = tomllib.loads(toml.read_text(encoding="utf-8"))
    L("   after Save All: gateways", [g["name"] for g in on_disk.get("gateway", [])], "npc", [n.get("name") for n in on_disk.get("npc", [])])
    # 3. back to Trace: what does the canvas show? then edit + Regenerate
    win.tabs.setCurrentWidget(td); G._settle()
    L("3. Trace regions on canvas", len(td.canvas._regions), "session regions", len(td._regions), "| offer btn", td.offer_btn.isVisible(), td.offer_btn.text())
    td.canvas._commit_floor([(60.0, 430.0), (330.0, 430.0), (250.0, 240.0), (130.0, 240.0)])
    td.on_generate(); wait_job(win)
    after = tomllib.loads(toml.read_text(encoding="utf-8"))
    L("   after Regenerate: gateways", [g["name"] for g in after.get("gateway", [])], "npc", [n.get("name") for n in after.get("npc", [])])
    L("   console tail:", win.console.toPlainText()[-700:] if hasattr(win, "console") else "")
    # 4. Place again
    win.tabs.setCurrentWidget(pd); G._settle()
    L("4. Place markers", len(pd.canvas._markers), "regions", len(pd.canvas._regions), "dirty", "HALL" in set(win._dirty_members()))
    G._close(win)
