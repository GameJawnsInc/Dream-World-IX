"""Probe: cutscene step editor vs shell undo; cross-project same-member staleness (cutscene/place)."""
import os, sys, tempfile, json
from pathlib import Path
SCR = Path(tempfile.mkdtemp(prefix="shl_probe_"))
os.environ["LOCALAPPDATA"] = str(SCR / "la")
os.environ["FF9MAPKIT_NO_THUMBS"] = "1"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit/tests")
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
from ff9mapkit import prefs
prefs._path = lambda: SCR / "prefs.json"
from ff9mapkit.workspace import shell
from ff9mapkit.editor.theme import pick_palette
import test_workspace_cutscene as T

def mk(dirname, body, xs=(-300, 640, 680, 1000)):
    d = SCR / dirname; d.mkdir()
    p = d / "X.field.toml"; p.write_text(body, encoding="utf-8")
    from ff9mapkit.scene import bgi
    verts = [(x, 0, z) for z in (600, 60, -300) for x in xs]
    tris = [(0, 1, 5), (0, 5, 4), (2, 3, 7), (2, 7, 6),
            (4, 5, 9), (4, 9, 8), (5, 6, 10), (5, 10, 9), (6, 7, 11), (6, 11, 10)]
    (d / "walkmesh.bgi").write_bytes(bgi.build(verts, tris).to_bytes())
    return p

win = shell.Workspace(pick_palette("dark"))
TWO = (T._HEAD + '[[cutscene]]\nactors = ["Cid"]\nrequires_scenario = 100\n'
       'steps = [ { say = "A" }, { say = "B" }, { actor = "Cid", walk = [200, 300] } ]\n')
pa = mk("projA", TWO)
win.open_field(pa)
win.tabs.setCurrentWidget(win.cutscene_doc)
doc = win.cutscene_doc
print("== probe 1: step editor survives an undo, Apply writes the stale content ==")
doc._move_step(0, +1)
print("after move:", [s.get("say","walk") for s in doc._raw["cutscene"][0]["steps"]])
doc._edit_step(0)
print("editor open on step", doc.editor.step_i, "showing", repr(doc.editor.value_text.toPlainText()))
win._undo()
print("after undo: ", [s.get("say","walk") for s in win._docs["X"].data["cutscene"][0]["steps"]],
      "| editor.scene/step_i:", doc.editor.scene, doc.editor.step_i,
      "| editor still shows", repr(doc.editor.value_text.toPlainText()))
doc._apply_step()
print("after Apply:", [s.get("say","walk") for s in win._docs["X"].data["cutscene"][0]["steps"]])

print("== probe 2: same member name, different project -> stale staging walkmesh ==")
win2 = win
doc.stage_now(sync=True)
wA = doc._wmesh
print("A staged; wmesh cached:", wA is not None, "armed:", doc._stage_armed, "summary:", doc.stage_note.text()[:80])
# project B: same name X, but walkmesh shifted far away so Cid at (0,400) is OFF-mesh
pb = mk("projB", TWO, xs=(5000, 5640, 5680, 6000))
shell_ok = win.open_field(pb)
print("opened B:", shell_ok, "current tab is Editor:", win.tabs.currentWidget() is win.doc_scroll)
win.tabs.setCurrentWidget(win.cutscene_doc)
print("B fed: member", doc._member, "path", doc._path.parent.name, "| wmesh is A's:", doc._wmesh is wA,
      "armed:", doc._stage_armed)
doc.stage_now(sync=True)
print("B staged summary:", doc.stage_note.text()[:120])
# fresh doc for truth
doc._reset_stage(); doc.stage_now(sync=True)
print("B staged after a forced reset (truth):", doc.stage_note.text()[:120])

print("== probe 3: Place state across same-name reopen ==")
pd = win.place_doc
win.tabs.setCurrentWidget(pd)
print("place source:", pd._source, "cam_pick:", pd._cam_pick)
pd._cam_pick["X"] = 2
win.open_field(pa)
win.tabs.setCurrentWidget(pd)
print("after reopening A, Place cam index carried over from B:", pd._cam_index())
