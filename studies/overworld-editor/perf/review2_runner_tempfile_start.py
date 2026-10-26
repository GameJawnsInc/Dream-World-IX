"""review2 (runner slice): a JobRunner job whose output file cannot be made never ends.

c2c7623a moved the job's output to tempfile.TemporaryFile(), made OUTSIDE the try that turns any failed start
into a failed job (J4). A TemporaryFile that raises (a full disk, a TEMP that was cleaned away, a denied temp
dir) kills the worker with no result: done never runs, busy() stays True, and wait() still says the job ended.
Run from ff9mapkit/:  py ../studies/overworld-editor/perf/review2_runner_tempfile_start.py
"""
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "ff9mapkit"))
from PySide6.QtWidgets import QApplication  # noqa: E402
import ff9mapkit.workspace.worldforest as WF  # noqa: E402

print("package:", WF.__file__)
app = QApplication.instance() or QApplication([])
seen = []
threading.excepthook = lambda a: seen.append(a.exc_type.__name__)   # where a worker's error goes (lost under pythonw)


def full(*_a, **_k):
    raise OSError(28, "No space left on device")


real = tempfile.TemporaryFile
tempfile.TemporaryFile = full
try:
    r, got = WF.JobRunner(), []
    r.start([sys.executable, "-c", "print('hi')"], ".", lambda code, text: got.append((code, text)))
    ended = r.wait(5000)
    for _ in range(20):
        app.processEvents()
finally:
    tempfile.TemporaryFile = real
print("wait() says ended:", ended)
print("busy() after:", r.busy())
print("done ran:", got)
print("worker died with:", seen)
print("DEFECT" if ended and r.busy() and not got else "ok")


def shutdown_shape(runner):                  # WorldDoc.shutdown's loop, its closing_runner() = the busy runner
    for _ in range(256):
        busy = [runner] if runner.busy() else []
        if busy:
            if not busy[0].wait():
                return "returned: a job never ended"
            continue
        return "close_in_game_edit reached"
    return "fell off the 256 bound: close_in_game_edit never ran"


print("WorldDoc.shutdown's loop over this runner:", shutdown_shape(r))
