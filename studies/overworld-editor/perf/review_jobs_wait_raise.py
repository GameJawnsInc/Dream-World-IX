"""Review probe (jobs slice): a done that raises inside JobRunner.wait() leaves WorldDoc.shutdown half way.

    py studies/overworld-editor/perf/review_jobs_wait_raise.py

QProcessRunner.wait() ran a job's done inside Qt's finished emission, so an exception in it was printed and wait still
returned True; JobRunner.wait() calls done from Python (``self._deliver(job)``), so the exception propagates out of
wait, out of WorldDoc.shutdown's loop, and out of the shell's closeEvent. WorldDoc.shutdown is run on a stand-in self:
a card whose writing job's done raises (an OSError: a file the done writes held open), and the recipe bar running a
second writing job (2 s). Nothing is written anywhere.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2] / "ff9mapkit"
sys.path.insert(0, str(KIT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def main():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    import ff9mapkit
    assert Path(ff9mapkit.__file__).resolve().is_relative_to(KIT.resolve())
    from ff9mapkit.workspace.worlddoc import WorldDoc
    from ff9mapkit.workspace.worldforest import JobRunner, QProcessRunner

    for R in (QProcessRunner, JobRunner):
        card_r, bar_r, ran = R(), R(), []

        def card_done(code, text):
            ran.append("card")
            raise PermissionError(13, "the draft's history.json is held open by another reader")
        card_r.start([sys.executable, "-c", "print('accept')"], ".", card_done)
        bar_r.start([sys.executable, "-c", "import time; time.sleep(2); print('promote back')"], ".",
                    lambda code, text: ran.append("bar"))

        class Card:
            def closing_runner(self):
                return card_r if card_r.busy() else None

        class Bar:
            def closing_runner(self):
                return bar_r if bar_r.busy() else None

            def close_in_game_edit(self):
                ran.append("close_in_game_edit")
                return False

        class Doc:
            _recipe = Bar()

            def _carry_tools(self):
                return [Card()]
        t = time.perf_counter()
        try:
            WorldDoc.shutdown(Doc())
            out = "returned"
        except Exception as e:                                       # noqa: BLE001
            out = f"RAISED {e!r}"
        print(f"{R.__name__}: shutdown {out} after {time.perf_counter() - t:.2f} s; dones run {ran}; "
              f"the bar's writing job still running: {bar_r.busy()}")
        bar_r.wait()
        app.processEvents()


if __name__ == "__main__":
    main()
