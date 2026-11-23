import sys; sys.path.insert(0, r"<SCRATCH>/review/x-cutscene-place")
import h
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QLabel
from ff9mapkit.editor import forms
from ff9mapkit.workspace import animpicker
from ff9mapkit.workspace.behaviordoc import _WORLD

MODE = {"act": "cancel"}
def fake_exec(dlg):
    labels = [l.text() for l in dlg.findChildren(QLabel) if l.text()][:3]
    n = dlg.listw.count() if hasattr(dlg, "listw") else -1
    print(f"   [picker] model={getattr(dlg.model,'name',None)} rows={n} labels={labels}")
    if MODE["act"] == "pick" and n > 0:
        dlg.listw.setCurrentRow(min(3, n - 1))
        dlg._ok()
        print("   [picker] picked", dlg.result)
    else:
        dlg.reject()
    return 0
animpicker.AnimPickerDialog.exec = fake_exec

with h.gs._no_modals():
    win, toml = h.cut_win()
    d = win.cutscene_doc
    ed = d.editor
    d._edit_step(1); h.settle(3)                     # Mira's turn step
    ed.kind.setCurrentIndex(list(forms.STEP_KIND).index("animation")); h.settle(2)
    print("kind", ed.current_kind(), "browse visible", ed.anim_browse.isVisible(), "actor", ed.actor.currentText())
    ed.value_line.setText("idle_custom")
    MODE["act"] = "cancel"; ed.anim_browse.click(); h.settle(2)
    print("after cancel value", repr(ed.value_line.text()))
    MODE["act"] = "pick"; ed.anim_browse.click(); h.settle(2)
    print("after pick value", repr(ed.value_line.text()))
    ed.actor.setEditText(""); MODE["act"] = "cancel"; ed.anim_browse.click(); h.settle(2)
    ed.actor.setEditText("player"); ed.anim_browse.click(); h.settle(2)
    ed.actor.setEditText("Ghost"); ed.anim_browse.click(); h.settle(2)
    ed.actor.setEditText("Mira"); MODE["act"] = "pick"; ed.anim_browse.click(); h.settle(2)
    ed.apply_btn.click(); h.settle(3)
    print("applied step1", d._steps()[1], "note", repr(ed.note.text()))

    # ---- sticky / invisible pick arm
    cv = d.canvas; vp = cv.viewport()
    def vpt(x, z): return cv.mapFromScene(QPointF(x * _WORLD, -z * _WORLD))
    d._close_editor(); d._selected_step = None; d._render(); h.settle(2)
    d._edit_step(0); h.settle(3)
    QTest.mouseClick(ed.pick_btn, Qt.MouseButton.LeftButton); h.settle(2)
    ed.apply_btn.click(); h.settle(3)                # Apply without picking
    print("after Apply: sim armed?", cv._sim_mode, "editor open", ed.scene is not None, "step_i", ed.step_i)
    hd = cv._handles[0]; p0 = vpt(hd["x"], hd["z"])
    before = dict(d._steps()[0])
    QTest.mousePress(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p0)
    for k in range(1, 6):
        QTest.mouseMove(vp, p0 + QPoint(-k * 8, k * 4)); h.settle(1)
    QTest.mouseRelease(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p0 + QPoint(-40, 20)); h.settle(3)
    print("handle drag while armed: step0 before", before, "after", d._steps()[0],
          "editor value now", repr(ed.value_line.text()), "armed", cv._sim_mode)
    # arm, then Edit another walk-free row: does the arm survive?
    QTest.mouseClick(ed.pick_btn, Qt.MouseButton.LeftButton); h.settle(2)
    d._edit_step(2); h.settle(3)
    print("after Edit row 2 (say): armed", cv._sim_mode, "kind", ed.current_kind())
    QTest.mouseClick(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, vpt(0, 0)); h.settle(2)
    print("clicked stage: value_line", repr(ed.value_line.text()), "value_text", repr(ed.value_text.toPlainText()))
    ed.kind.setCurrentIndex(list(forms.STEP_KIND).index("walk")); h.settle(2)
    print("switch say->walk: value_line", repr(ed.value_line.text()))
    h.gs._close(win)
