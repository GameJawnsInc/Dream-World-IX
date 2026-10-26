"""review2 (runner slice): how often does the kill fence's delay-1.0 kill land after Popen (the only case that
fences kill()'s own proc.kill())? Times the worker's Popen too. Mutant: kill() without its proc.kill().
Run from ff9mapkit/:  py ../studies/overworld-editor/perf/review2_runner_kill_fence_rate.py [N]
"""
import inspect
import subprocess
import sys
import textwrap
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "ff9mapkit"))
from PySide6.QtWidgets import QApplication  # noqa: E402
import ff9mapkit.workspace.worldforest as WF  # noqa: E402

app = QApplication.instance() or QApplication([])
src = textwrap.dedent(inspect.getsource(WF.JobRunner.kill)).replace("proc.kill()", "pass")
ns = dict(vars(WF))
exec(compile(src, "<mut>", "exec"), ns)
WF.JobRunner.kill = ns["kill"]
real_popen = subprocess.Popen
times = []


class TimedPopen(real_popen):
    def __init__(self, *a, **k):
        t = time.perf_counter()
        super().__init__(*a, **k)
        times.append(time.perf_counter() - t)


WF.subprocess.Popen = TimedPopen
N = int(sys.argv[1]) if len(sys.argv) > 1 else 8
green = 0
for i in range(N):
    ok = True
    for delay in (0.0, 1.0):
        r = WF.JobRunner()
        r.start([sys.executable, "-c", "import time; time.sleep(30)"], ".", lambda code, text: None)
        time.sleep(delay)
        job = r._job
        r.kill()
        job["thread"].join(10)
        if not (job["proc"] is not None and job["proc"].poll() is not None):
            ok = False
        if job["proc"] is not None and job["proc"].poll() is None:
            job["proc"].kill()
    green += ok
print(f"mutant (kill() never kills) passed the fence {green}/{N} times; Popen took "
      f"{min(times):.3f}-{max(times):.3f}s")
