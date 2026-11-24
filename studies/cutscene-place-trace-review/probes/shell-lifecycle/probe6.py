import os, sys, tempfile
from pathlib import Path
SCR = Path(tempfile.mkdtemp(prefix="shl_probe6_"))
os.environ["LOCALAPPDATA"] = str(SCR / "la"); os.environ["FF9MAPKIT_NO_THUMBS"] = "1"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
from ff9mapkit import prefs
prefs._path = lambda: SCR / "prefs.json"
from ff9mapkit.workspace import shell
from ff9mapkit.editor.theme import pick_palette
win = shell.Workspace(pick_palette("dark"))
win._set_theme("light")
for n in ("cutscene_doc", "place_doc", "trace_doc"):
    d = getattr(win, n)
    print(n, "doc.pal is shell.pal:", d.pal is win.pal or d.pal == win.pal, "| canvas.pal bg:", d.canvas.pal.get("bg"), "shell bg:", win.pal.get("bg"))
win._apply_text_scale(150)
for n in ("cutscene_doc", "place_doc", "trace_doc"):
    print(n, "canvas scale:", getattr(getattr(win, n).canvas, "_scale", "?"))
