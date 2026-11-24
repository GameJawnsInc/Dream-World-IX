"""Real Ctrl+Z key event (through QShortcut map) on the Trace canvas, with an open field holding one shell undo."""
import os, sys, tempfile
from pathlib import Path
SCR = Path(tempfile.mkdtemp(prefix="vtt_ctrlz_"))
os.environ["LOCALAPPDATA"] = str(SCR / "la"); os.environ["APPDATA"] = str(SCR / "ad")
os.environ["FF9MAPKIT_NO_THUMBS"] = "1"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit/tests")
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
app = QApplication.instance() or QApplication([])
from ff9mapkit import prefs
prefs._path = lambda: SCR / "prefs.json"
from ff9mapkit.workspace import shell
from ff9mapkit.editor.theme import pick_palette
import test_workspace_cutscene as T
from PIL import Image
d = SCR / "p"; d.mkdir()
p = d / "X.field.toml"; p.write_text(T._HEAD, encoding="utf-8")
(d / "walkmesh.bgi").write_bytes(T._mesh_bytes())
win = shell.Workspace(pick_palette("dark"))
win.show(); win.activateWindow(); app.processEvents()
win.open_field(p)
win.tabs.setCurrentWidget(win.cutscene_doc); app.processEvents()
win.cutscene_doc._add_scene(); app.processEvents()
print("shell undo stack:", [r.label for r in win._undo_stack][-2:])
win.tabs.setCurrentWidget(win.trace_doc); app.processEvents()
td = win.trace_doc
ph = SCR / "ph.png"; Image.new("RGB", (800, 600), (90, 80, 70)).save(ph)
# offer may have rejected X; use explicit image load (as Open does)
td.load_image(ph)
td._on_floor([(60, 420), (330, 420), (300, 250)])
td.canvas.set_floor(td._floor)
td.canvas.setFocus(); app.processEvents()
print("focus:", type(QApplication.focusWidget()).__name__, "| trace floor", len(td._floor), "hist", len(td._history))
QTest.keyClick(td.canvas.viewport() if hasattr(td.canvas, "viewport") else td.canvas, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
app.processEvents()
print("after real Ctrl+Z: tab =", win.tabs.tabText(win.tabs.currentIndex()), "| trace floor", len(td._floor),
      "| shell undo stack:", [r.label for r in win._undo_stack][-2:], "| redo:", [r.label for r in win._redo_stack])
print("closeEvent dirty members:", win._dirty_members())
