import sys, time, shutil; sys.path.insert(0, r"<SCRATCH>/review/x-cutscene-place")
import h
from ff9mapkit.workspace import cutscenescan

def wait_idle(d, cap=30):
    t = time.time()
    while d._stage_busy and time.time() - t < cap:
        h.settle(1); time.sleep(0.03)
    return time.time() - t

with h.gs._no_modals():
    win, toml = h.cut_win()
    d = win.cutscene_doc
    d.stage_btn.click(); print("async check took %.2fs" % wait_idle(d))
    print("P1 verdict:", d.stage_note.text())
    win._close_project(); h.settle(3)
    print("after close: doc member", d._member, "raw None?", d._raw is None, "wmesh kept", d._wmesh is not None,
          "note", d.stage_note.text())
    root2 = h.OUT / "work" / "cut2b"
    shutil.rmtree(root2, ignore_errors=True)
    t2 = h.gs._load_cutscene_demo().make_cutscene_field(root2)
    t2.write_text(t2.read_text(encoding="utf-8").replace('{ walk = "altar", actor = "Cid" }',
                                                         '{ walk = [2000, 2000], actor = "Cid" }'), encoding="utf-8")
    assert win.open_field(t2); win.tabs.setCurrentWidget(d); h.settle(4)
    print("P2 opened (blocked walk), no Check pressed: path", d._path.parent.name, "| note:", d.stage_note.text(),
          "| verdict rows", len(d.canvas._verdicts or []))
    d._stage_gen += 0
    d.stage_now(sync=True); h.settle(2)
    print("P2 after pressing Check (warm mesh reused):", d.stage_note.text())
    # what the TRUE verdict is with P2's own mesh
    d._wmesh = None; d.stage_now(sync=True)
    print("P2 cold truth:", d.stage_note.text())
    h.gs._close(win)
