"""Probe: Ctrl+Z on Trace; Editor tree after Cutscene-tab structural edits; place region edit; palette."""
import os, sys, tempfile
from pathlib import Path
SCR = Path(tempfile.mkdtemp(prefix="shl_probe4_"))
os.environ["LOCALAPPDATA"] = str(SCR / "la")
os.environ["FF9MAPKIT_NO_THUMBS"] = "1"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit/tests")
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
from ff9mapkit import prefs
prefs._path = lambda: SCR / "prefs.json"
from ff9mapkit.workspace import shell, placedoc
from ff9mapkit.editor.theme import pick_palette
import test_workspace_cutscene as T

d = SCR / "p"; d.mkdir()
p = d / "X.field.toml"; p.write_text(T._HEAD, encoding="utf-8")
(d / "walkmesh.bgi").write_bytes(T._mesh_bytes())
win = shell.Workspace(pick_palette("dark"))
win.open_field(p)

def tree_rows(member):
    mi = win._member_items[member]
    win.tree.expandItem(mi)
    return [win._payload(mi.child(i))[0:3:2] for i in range(mi.childCount())]

print("== tree before:", [r for r in tree_rows("X") if r and r[1] and "cutscene" in str(r[1])])
win.tabs.setCurrentWidget(win.cutscene_doc)
cd = win.cutscene_doc
cd._add_scene()
print("after Cutscene-tab '+ Scene': data has cutscene:", "cutscene" in win._docs["X"].data,
      "| tree has a cutscene row:", any(r and "cutscene" in str(r[1]) for r in tree_rows("X")))
cd._del_scene()
print("after '- Scene' (last): data has cutscene:", "cutscene" in win._docs["X"].data,
      "| tree still has a cutscene row:", any(r and "cutscene" in str(r[1]) for r in tree_rows("X")))

print("== Ctrl+Z while Trace is the active tab ==")
cd._add_scene()        # one undoable cutscene edit on the open field
win.tabs.setCurrentWidget(win.trace_doc)
td = win.trace_doc
td._on_floor([(10, 300), (200, 300), (200, 400)])
print("trace history:", len(td._history), "| shell undo stack:", [r.label for r in win._undo_stack][-2:])
win._undo_shortcut()
print("after Ctrl+Z: current tab =", win.tabs.tabText(win.tabs.currentIndex()),
      "| trace history:", len(td._history), "| trace floor pts:", len(td._floor),
      "| cutscene scenes:", len((win._docs['X'].data.get('cutscene') or [])) if isinstance(win._docs['X'].data.get('cutscene'), list) else win._docs['X'].data.get('cutscene'))

print("== theme switch reaches the three docs ==")
seen = {}
for nm in ("cutscene_doc", "place_doc", "trace_doc"):
    doc = getattr(win, nm)
    orig = doc.retheme
    def wrap(pal, _n=nm, _o=orig):
        seen.setdefault(_n, 0); seen[_n] += 1; return _o(pal)
    doc.retheme = wrap
    o2 = doc.set_scale
    def wrap2(pct, _n=nm, _o=o2):
        seen.setdefault(_n + ".scale", 0); seen[_n + ".scale"] += 1; return _o(pct)
    doc.set_scale = wrap2
for name in ("_apply_theme", "_set_theme", "_on_theme", "set_theme"):
    if hasattr(win, name):
        print("theme entry:", name)
import inspect
src = inspect.getsource(shell.Workspace)
