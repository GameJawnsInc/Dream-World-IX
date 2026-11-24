"""T38 without --force: open generated project -> Trace regenerate in place (+gateway) -> THEN a Place drop -> Save All."""
import os, sys, tempfile, subprocess, tomllib, shutil
from pathlib import Path
SCR = Path(r"<SCRATCH>/review/v-trace-backend/t38")
shutil.rmtree(SCR, ignore_errors=True); SCR.mkdir(parents=True)
os.environ["LOCALAPPDATA"] = str(SCR / "la")
os.environ["FF9MAPKIT_NO_THUMBS"] = "1"
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PIL import Image
img = SCR / "room.png"; Image.new("RGB", (768, 896), (90, 120, 80)).save(img)
out = SCR / "room-field"
KIT = r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit"
def gen(extra=()):
    r = subprocess.run([sys.executable, "-m", "ff9mapkit", "image-field", str(img), "--floor",
                        "60,300 320,300 360,430 20,430", "--out", str(out), "--name", "ROOM",
                        "--id", "30999", *extra], cwd=KIT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    print("gen rc", r.returncode)
gen()
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
from ff9mapkit import prefs
prefs._path = lambda: SCR / "prefs.json"
from ff9mapkit.workspace import shell, placedoc
from ff9mapkit.editor.theme import pick_palette
win = shell.Workspace(pick_palette("dark"))
toml = out / "ROOM.field.toml"
print("open:", win.open_field(toml))
gen(["--gateway", "4005@100,320;200,320;200,360;100,360"])     # the tab's in-place regenerate (no --force)
d = tomllib.loads(toml.read_text(encoding="utf-8"))
print("disk after regen: gateways", len(d.get("gateway", [])))
win.tabs.setCurrentWidget(win.place_doc); app.processEvents()
pd = win.place_doc
print("place buffer gateways:", len(pd._data.get("gateway", [])))
lab = placedoc.place_npc(pd._data, 0.0, 300.0); pd.on_edit(pd._member, lab)
win._save_all()
d = tomllib.loads(toml.read_text(encoding="utf-8"))
print("disk after Place drop + Save All: gateways", len(d.get("gateway", [])), "npcs", len(d.get("npc", [])))
