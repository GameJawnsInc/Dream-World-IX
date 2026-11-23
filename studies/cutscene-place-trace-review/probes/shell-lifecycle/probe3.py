"""Probe: Trace regenerate-in-place vs an open, dirty Editor buffer of the same project; Trace close guard."""
import os, sys, tempfile, subprocess, tomllib
from pathlib import Path
SCR = Path(tempfile.mkdtemp(prefix="shl_probe3_"))
os.environ["LOCALAPPDATA"] = str(SCR / "la")
os.environ["FF9MAPKIT_NO_THUMBS"] = "1"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PIL import Image
img = SCR / "room.png"
Image.new("RGB", (768, 896), (90, 120, 80)).save(img)
out = SCR / "room-field"
KIT = r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit"
def gen(extra=()):
    r = subprocess.run([sys.executable, "-m", "ff9mapkit", "image-field", str(img), "--floor",
                        "60,300 320,300 360,430 20,430", "--out", str(out), "--name", "ROOM",
                        "--id", "30999", "--force", *extra], cwd=KIT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    print("gen rc", r.returncode, (r.stdout + r.stderr).strip().splitlines()[-1:] )
gen()
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
from ff9mapkit import prefs
prefs._path = lambda: SCR / "prefs.json"
from ff9mapkit.workspace import shell
from ff9mapkit.workspace import placedoc
from ff9mapkit.editor.theme import pick_palette
win = shell.Workspace(pick_palette("dark"))
toml = out / "ROOM.field.toml"
print("open:", win.open_field(toml))
m = win._loose
win.tabs.setCurrentWidget(win.place_doc)
pd = win.place_doc
print("place source:", pd._source[0], "blocked:", pd._blocked)
lab = placedoc.place_npc(pd._data, 0.0, 300.0)
pd.on_edit(pd._member, lab)
print("dirty after a Place drop:", win._dirty_members())
# the Trace tab regenerates IN PLACE (simulated by the same CLI the tab runs), adding a gateway
gen(["--gateway", "4005@100,320;200,320;200,360;100,360"])
disk = tomllib.loads(toml.read_text(encoding="utf-8"))
print("on disk after regenerate: gateways", len(disk.get("gateway", [])), "npcs", len(disk.get("npc", [])))
# the trace tab's own feed of the open doc
td = win.trace_doc
win.tabs.setCurrentWidget(td)
print("trace pristine-auto-loaded the open project:", td._project is not None)
win._save_all()
disk = tomllib.loads(toml.read_text(encoding="utf-8"))
print("on disk after Save All: gateways", len(disk.get("gateway", [])), "npcs", len(disk.get("npc", [])))
# close guard with an unstamped trace gesture
td._on_floor([(10, 300), (200, 300), (200, 400)])
print("trace has an ungenerated gesture; _stamped =", td._stamped,
      "| shell would prompt on close:", not win._maybe_prompt_unsaved.__func__ is None and bool(win._dirty_members()))
from PySide6.QtGui import QCloseEvent
ev = QCloseEvent(); win.closeEvent(ev)
print("closeEvent accepted with an ungenerated trace:", ev.isAccepted())
