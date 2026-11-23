"""Trace flow probe: generate-failure lifecycle, silent loss on re-open, missing-photo reopen, Ctrl+Z routing."""
import sys, importlib.util, json, shutil
from pathlib import Path
REPO = Path(r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9")
OUT = Path(r"<SCRATCH>/review/trace-ux-look")
spec = importlib.util.spec_from_file_location("gui_snap", REPO / "tools" / "gui_snap.py")
gs = importlib.util.module_from_spec(spec); sys.modules["gui_snap"] = gs; spec.loader.exec_module(gs)
spec2 = importlib.util.spec_from_file_location("_tf", REPO / "ff9mapkit" / "tests" / "test_imagefield.py")
tf = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(tf)
root = OUT / "room2"
shutil.rmtree(root, ignore_errors=True); root.mkdir(parents=True)
photo, floor = tf._paint_room(root)
photo2 = root / "other.png"; shutil.copy(photo, photo2)

class A: pass
a = A(); a.theme = "mist"; a.scale = 100; a.guided = "guided"; a.width = 1280; a.height = 850; a.out = str(OUT / "snaps")
ctx = gs._Ctx(a)
win = gs._make_win(ctx)
win.tabs.setCurrentWidget(win.trace_doc); gs._settle(4)
td = win.trace_doc

jobs = []
def fake_run(argv, **kw):
    jobs.append(kw); return True
td._run = fake_run
opened = []
td.on_generated = lambda p: opened.append(p)
td._ask_out = lambda: str(root / "out")

td.load_image(photo)
td.canvas._commit_floor([(float(x), float(y)) for x, y in floor]); gs._settle(2)
print("1 before generate:", td.gen_btn.text(), "|", td.status.text())
td.on_generate()
print("2 after launch   :", td.gen_btn.text(), "|", td.status.text())
jobs[-1]["on_finished"](1)          # the CLI FAILED (e.g. Int16 world bound)
gs._settle(2)
print("3 after FAIL     :", td.gen_btn.text(), "|", td.status.text(), "| project:", td._project, "| stamped:", td._stamped)
print("   sidecar written despite failure?", list((root / "out").glob("*.trace.json")))
td.on_generate()                    # the retry
(root / "out").mkdir(exist_ok=True)
(root / "out" / "PICTURE.field.toml").write_text("[field]\n", encoding="utf-8")
jobs[-1]["on_finished"](0)          # the retry SUCCEEDS
gs._settle(2)
print("4 retry OK       : opened in Editor ->", opened, "| status:", td.status.text())

# silent loss: open another image mid-session (no confirm, no undo)
td.tools.set_current("regions")
cam = td.canvas.camera()
from ff9mapkit import imagefield as IF
td.gw_to.setValue(4005)
td._on_region_drawn([IF.click_to_world(cam, p) for p in [(40.0, 400.0), (150.0, 400.0), (150.0, 430.0), (40.0, 430.0)]])
print("5 mid-session    : floor", len(td._floor), "regions", len(td._regions), "history", len(td._history), "project", bool(td._project))
td._ask_image = lambda: str(photo2)
td.on_open(); gs._settle(2)
print("6 after Open other: floor", len(td._floor), "regions", len(td._regions), "history", len(td._history),
      "undo enabled", td.undo_btn.isEnabled(), "project", td._project, "| status:", td.status.text())

# Ctrl+Z on the Trace tab: does it reach TraceDoc.on_undo?
td.canvas._commit_floor([(float(x), float(y)) for x, y in floor]); gs._settle(2)
td.canvas._commit_floor([(float(x), float(y)) for x, y in floor[:3]]); gs._settle(2)
n0 = len(td._floor)
win._undo_shortcut(); gs._settle(2)
print("7 Ctrl+Z on Trace: floor before", n0, "after", len(td._floor), "(unchanged => shortcut never reaches the trace)")

# reopen a .trace.json whose photo moved
side = root / "moved.trace.json"
side.write_text(json.dumps({"image": str(root / "gone.png"), "pitch": 26, "floor": [], "fg": [], "regions": [],
                            "name": "X", "id": "30058"}), encoding="utf-8")
td._ask_image = lambda: str(side)
td.on_open(); gs._settle(2)
print("8 moved photo    :", td.status.text())

# event message default, bare-state name/id
print("9 defaults: name", td.name_box.text(), "id", td.id_box.text(), "ev_msg", repr(td.ev_msg.text()))
# Clear in Regions mode
td.tools.set_current("regions"); gs._settle(2)
print("10 regions mode clear tooltip:", td.clear_btn.toolTip(), "| undo tip:", td.undo_btn.toolTip())
print("11 hint text in regions mode:", td.canvas._hint.text())
gs._close(win)
