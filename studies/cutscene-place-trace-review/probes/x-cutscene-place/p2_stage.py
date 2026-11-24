import sys; sys.path.insert(0, r"<SCRATCH>/review/x-cutscene-place")
import h
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtTest import QTest
from ff9mapkit.workspace import cutscenescan
from ff9mapkit.workspace.behaviordoc import _WORLD

with h.gs._no_modals():
    win, toml = h.cut_win()
    d = win.cutscene_doc
    cv = d.canvas
    vp = cv.viewport()
    h.settle(6)

    def vpt(x, z):
        return cv.mapFromScene(QPointF(x * _WORLD, -z * _WORLD))

    def world(p):
        s = cv.mapToScene(p)
        return s.x() / _WORLD, -s.y() / _WORLD

    print("viewport", vp.size().toTuple(), "edit", cv._edit, "sim", cv._sim_mode)
    # --- 1) Pick on the stage for walk step 0
    d._edit_step(0); h.settle(4)
    print("editor kind", d.editor.current_kind(), "value", d.editor.value_line.text(),
          "pick visible", d.editor.pick_btn.isVisible())
    print("handles", cv._handles)
    print("cursor before arm", cv.viewport().cursor().shape(), "hint", cv._hint.text())
    QTest.mouseClick(d.editor.pick_btn, Qt.MouseButton.LeftButton); h.settle(2)
    print("armed sim", cv._sim_mode, "cursor after arm", cv.viewport().cursor().shape(),
          "hint", cv._hint.text(), "problems", d.problems_lbl.text()[:60])
    p = vpt(123.4, 456.6)
    QTest.mouseClick(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p); h.settle(2)
    print("picked ->", repr(d.editor.value_line.text()), "true world at click", world(p))
    # off-mesh pick (the mesh is x[-300,1000] z[-300,600])
    QTest.mouseClick(d.editor.pick_btn, Qt.MouseButton.LeftButton); h.settle(2)
    p = vpt(3000, 3000)
    QTest.mouseClick(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p); h.settle(2)
    print("off-mesh picked ->", repr(d.editor.value_line.text()), "note", repr(d.editor.note.text()))
    d.editor.apply_btn.click(); h.settle(4)
    print("after apply step0 =", d._steps()[0], "note", repr(d.editor.note.text()),
          "problems:", d.problems_lbl.text()[:120])
    win._undo(); h.settle(4)
    print("after undo step0 =", d._steps()[0])
    # --- 2) drag the walk target handle with real mouse events
    d._close_editor(); d._selected_step=None; d._render(); h.settle(2)
    d._on_step_select(0); h.settle(4)
    print("handles after select", cv._handles)
    hd = cv._handles[0]
    p0 = vpt(hd["x"], hd["z"])
    print("handle vp", p0.toTuple(), "itemAt", cv._resolve_grab(cv.itemAt(p0)))
    QTest.mousePress(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p0)
    for k in range(1, 6):
        QTest.mouseMove(vp, p0 + QPoint(k * 6, k * 4)); h.settle(1)
    QTest.mouseRelease(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p0 + QPoint(30, 20))
    h.settle(4)
    print("after drag step0 =", d._steps()[0], "undo", len(win._undo_stack), "sel", d._selected_step,
          "handles", cv._handles)
    win._undo(); h.settle(4)
    print("after undo step0 =", d._steps()[0], "sel", d._selected_step, "handles", cv._handles)
    # --- 3) teleport pick with storyboard open
    d.board_btn.setChecked(True); h.settle(3)
    d._steps()[0] if False else None
    d._edit_step(1); h.settle(3)
    d.editor.kind.setCurrentIndex(list(__import__('ff9mapkit.editor.forms', fromlist=['x']).STEP_KIND).index("teleport")); h.settle(2)
    print("kind now", d.editor.current_kind(), "pick vis", d.editor.pick_btn.isVisible())
    QTest.mouseClick(d.editor.pick_btn, Qt.MouseButton.LeftButton); h.settle(2)
    p = vpt(-100.2, 100.5)
    QTest.mouseClick(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p); h.settle(2)
    print("teleport picked", repr(d.editor.value_line.text()), "world", world(p))
    d.editor.apply_btn.click(); h.settle(3)
    print("step1 =", d._steps()[1], "note", repr(d.editor.note.text()))
    print("board_say", repr(d.board_say.text()), "pos", d.board_pos.text())
    h.gs._close(win)
