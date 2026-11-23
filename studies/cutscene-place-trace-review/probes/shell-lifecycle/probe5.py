"""Probe: a carried-over camera pick beyond the field's camera count -> Load never applies."""
import os, sys, tempfile, subprocess, time
from pathlib import Path
SCR = Path(tempfile.mkdtemp(prefix="shl_probe5_"))
os.environ["LOCALAPPDATA"] = str(SCR / "la")
os.environ["FF9MAPKIT_NO_THUMBS"] = "1"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PIL import Image
img = SCR / "room.png"; Image.new("RGB", (768, 896), (90, 120, 80)).save(img)
out = SCR / "room-field"
KIT = r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit"
subprocess.run([sys.executable, "-m", "ff9mapkit", "image-field", str(img), "--floor",
                "60,300 320,300 360,430 20,430", "--out", str(out), "--name", "ROOM", "--id", "30999"],
               cwd=KIT, capture_output=True)
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
from ff9mapkit import prefs
prefs._path = lambda: SCR / "prefs.json"
from ff9mapkit.workspace import shell
from ff9mapkit.editor.theme import pick_palette
win = shell.Workspace(pick_palette("dark"))
win.open_field(out / "ROOM.field.toml")
pd = win.place_doc
pd._cam_pick["ROOM"] = 1          # what a same-named member with 2 cameras in a prior project leaves
win.tabs.setCurrentWidget(pd)
for attempt in (1, 2):
    pd.on_load()
    t0 = time.time()
    while pd._loading is not None and time.time() - t0 < 20:
        app.processEvents(); time.sleep(0.02)
    print(f"Load #{attempt}: loading={pd._loading} bundles={sorted(k[1] for k in pd._bundles)} "
          f"applied={pd._bundle() is not None} status={pd.status.text()[:90]!r}")
pd._cam_pick["ROOM"] = 0
pd.on_load()
print("with pick reset to 0: applied =", pd._bundle() is not None)
old = pd._bundle()["tris"]
subprocess.run([sys.executable, "-m", "ff9mapkit", "image-field", str(img), "--floor",
                "150,330 250,330 260,380 140,380", "--out", str(out), "--name", "ROOM", "--id", "30999", "--force"],
               cwd=KIT, capture_output=True)
win.open_field(out / "ROOM.field.toml")      # the Trace -> open handoff path
win.tabs.setCurrentWidget(pd)
from ff9mapkit.workspace.placedoc import build_surface_from_project
fresh = build_surface_from_project(str(out / "ROOM.field.toml"), 0)["tris"]
print("after regenerate+reopen: Place shows a surface without Load:", pd._bundle() is not None,
      "| it is the OLD walkmesh:", pd._bundle()["tris"] == old, "| disk walkmesh differs:", fresh != old)
