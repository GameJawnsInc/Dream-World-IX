import sys; sys.path.insert(0, r"<SCRATCH>/review/x-cutscene-place")
import h
from ff9mapkit.workspace import cutscenescan
with h.gs._no_modals():
    win, toml = h.cut_win()
    d = win.cutscene_doc

    def st(tag):
        h.settle(4)
        raw = d._raw
        rows = cutscenescan.scene_rows(raw)
        m = d.canvas._model or {}
        print(f"{tag:28s} scenes={len(rows)} doc._scene={d._scene} rail.cur={d.rail.currentRow()} "
              f"rail.n={d.rail.count()} title={d.scene_title.text()!r} sel_step={d._selected_step} "
              f"ladder_chips={len(d.ladder._idx_chips)} stack_is_content={d._stack.currentWidget() is d._content} "
              f"raw_is_shell_buf={raw is win._docs['GLEN'].data} undo={len(win._undo_stack)} redo={len(win._redo_stack)}")
    st("start")
    d.rail.setCurrentRow(1); st("select scene 1")
    d.dup_scene_btn.click(); st("dup scene1")
    win._undo(); st("undo dup")
    win._redo(); st("redo dup")
    d.rail.setCurrentRow(1); st("select scene 1")
    d.del_scene_btn.click(); st("del scene1")
    win._undo(); st("undo del")
    d.rail.setCurrentRow(0); st("select 0")
    d.add_scene_btn.click(); st("add scene")
    win._undo(); st("undo add")
    win._redo(); st("redo add")
    # delete all scenes then undo
    for _ in range(5):
        if cutscenescan.scene_rows(d._raw):
            d.del_scene_btn.click(); h.settle(2)
    st("deleted all")
    win._undo(); st("undo last delete")
    # step select then undo
    d._on_step_select(0); st("select step0")
    d._del_step(0); st("delete step0")
    win._undo(); st("undo delete step0")
    print("canvas handles after undo", d.canvas._handles)
    h.gs._close(win)
