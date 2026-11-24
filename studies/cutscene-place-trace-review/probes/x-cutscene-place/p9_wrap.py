import sys; sys.path.insert(0, r"<SCRATCH>/review/x-cutscene-place")
import h
from PySide6.QtWidgets import QPlainTextEdit
from ff9mapkit.content import text as T
from ff9mapkit.workspace import cutscenescan

def build_wrap(step, ww):
    # the build's own _add(): with_speaker -> wrap_text (build.py ~9470)
    line = T.with_speaker(step.get("speaker"), step["say"])
    return T.wrap_text(line, ww)[0] if ww is not None else line

CASES = [
    ("narration, markup", {"say": "You obtained the {item}Ancient Mythril Ore of the Lost Northern Kingdom{/} at last, well done."}),
    ("speaker quotes", {"say": "We crossed the whole glen before the dusk light faded out over", "speaker": "Cid"}),
    ("literal \\n", {"say": "First line here\\nSecond line"}),
]
with h.gs._no_modals():
    win, toml = h.cut_win()
    d = win.cutscene_doc
    d.rail.setCurrentRow(1); h.settle(3)                     # the narration scene
    ed = d.editor
    ww = cutscenescan.wrap_width(d._merged())
    d._edit_step(0); h.settle(3)
    box = [b for b in ed.say_preview.findChildren(QPlainTextEdit)][0]
    for name, st in CASES:
        ed.value_text.setPlainText(st["say"]); ed.x_speaker.setText(st.get("speaker", "")); h.settle(2)
        prev = box.toPlainText()
        built_step = ed.read_step()
        real = build_wrap(built_step, ww)
        print(f"--- {name}: preview == build? {prev == real}")
        print("  PREVIEW:", prev.split("\n"))
        print("  BUILD  :", real.split("\n"))
    h.gs._close(win)
