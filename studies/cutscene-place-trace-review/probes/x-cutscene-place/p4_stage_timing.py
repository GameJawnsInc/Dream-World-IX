import sys, time, threading, shutil; sys.path.insert(0, r"<SCRATCH>/review/x-cutscene-place")
import h
from ff9mapkit.workspace import cutscenescan
orig = cutscenescan.load_walkmesh
def slow(*a, **k):
    time.sleep(1.2)
    return orig(*a, **k)
cutscenescan.load_walkmesh = slow
excs = []
sys.excepthook = lambda *a: (excs.append(a), print("EXC", a[1]))
threading.excepthook = lambda a: (excs.append(a), print("THREAD EXC", a.exc_value))

def wait(s):
    t = time.time()
    while time.time() - t < s:
        h.settle(1); time.sleep(0.03)

with h.gs._no_modals():
    win, toml = h.cut_win()
    d = win.cutscene_doc
    # A) scene switch mid-flight
    d.stage_btn.click(); wait(0.2)
    print("A in-flight: btn", d.stage_btn.text(), d.stage_btn.isEnabled())
    d.rail.setCurrentRow(1); wait(2.0)
    print("A done: btn", d.stage_btn.text(), "note", d.stage_note.text()[:90], "scene", d._scene,
          "verdict rows", len(d.canvas._verdicts or []))
    # B) close the project mid-flight (reset warm mesh first so it reloads slowly)
    d._reset_stage(); d.rail.setCurrentRow(0); wait(0.2)
    d.stage_btn.click(); wait(0.2)
    win._close_project() if hasattr(win, "_close_project") else d.show_none()
    wait(2.0)
    print("B after close: btn", d.stage_btn.text(), d.stage_btn.isEnabled(), "note", repr(d.stage_note.text()[:80]),
          "wmesh", d._wmesh is not None, "verdicts", d.canvas._verdicts)
    # C) reopen the field, start, then open a DIFFERENT project whose member has the SAME name
    assert win.open_field(toml); win.tabs.setCurrentWidget(d); wait(0.3)
    root2 = h.OUT / "work" / "cut2"
    shutil.rmtree(root2, ignore_errors=True)
    t2 = h.gs._load_cutscene_demo().make_cutscene_field(root2)
    txt = t2.read_text(encoding="utf-8").replace('{ walk = "altar", actor = "Cid" }', '{ walk = [2000, 2000], actor = "Cid" }')
    t2.write_text(txt, encoding="utf-8")
    d.stage_btn.click(); wait(0.2)
    assert win.open_field(t2); win.tabs.setCurrentWidget(d); wait(2.0)
    print("C other project: member", d._member, "path", d._path, "btn", d.stage_btn.text(),
          "note", d.stage_note.text()[:120], "armed", d._stage_armed)
    h.gs._close(win)
    wait(0.5)
print("exceptions:", len(excs))
