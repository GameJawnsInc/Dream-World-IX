"""review2 (runner slice): the committed JobRunner, the kill fence's delay-1.0 case: where does the kill land, and
how long did the worker's Popen take? (No mutation.)
Run from ff9mapkit/:  py ../studies/overworld-editor/perf/review2_runner_popen_time.py [N]
"""
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "ff9mapkit"))
from PySide6.QtWidgets import QApplication  # noqa: E402
import ff9mapkit.workspace.worldforest as WF  # noqa: E402

app = QApplication.instance() or QApplication([])
real_popen = subprocess.Popen
times = []


class TimedPopen(real_popen):
    def __init__(self, *a, **k):
        t = time.perf_counter()
        super().__init__(*a, **k)
        times.append(time.perf_counter() - t)


WF.subprocess.Popen = TimedPopen
N = int(sys.argv[1]) if len(sys.argv) > 1 else 10
rows = []
for i in range(N):
    for delay in (0.0, 1.0):
        r = WF.JobRunner()
        n0 = len(times)
        r.start([sys.executable, "-c", "import time; time.sleep(30)"], ".", lambda code, text: None)
        time.sleep(delay)
        job = r._job
        inside = job["proc"] is None
        r.kill()
        job["thread"].join(10)
        rows.append((delay, "inside" if inside else "after", round(times[n0], 3) if len(times) > n0 else None))
print(rows)
print("delay-1.0 kills that landed inside Popen:", sum(1 for d, w, _ in rows if d == 1.0 and w == "inside"), "/", N)
