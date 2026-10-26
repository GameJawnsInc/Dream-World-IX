"""review2 (runner slice): can test_a_killed_job_s_process_ends fail? Remove each kill site in turn and run the
fence's own body; also count, over N tries, where the delay-0 kill actually lands (inside Popen or after it).
Run from ff9mapkit/:  py ../studies/overworld-editor/perf/review2_runner_kill_fence.py
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
real_run, real_kill = WF.JobRunner._run, WF.JobRunner.kill


def mutate(fn, old, new):
    src = textwrap.dedent(inspect.getsource(fn))
    assert old in src, old
    ns = dict(vars(WF))
    exec(compile(src.replace(old, new), "<mut>", "exec"), ns)
    return ns[fn.__name__]


run_nokill = mutate(real_run, "if job[\"killed\"]:", "if False:")
kill_nokill = mutate(real_kill, "proc.kill()", "pass")


def fence():
    out = []
    for delay in (0.0, 1.0):
        r = WF.JobRunner()
        r.start([sys.executable, "-c", "import time; time.sleep(30)"], ".", lambda code, text: None)
        time.sleep(delay)
        job = r._job
        inside = job["proc"] is None
        r.kill()
        job["thread"].join(10)
        ended = job["proc"] is not None and job["proc"].poll() is not None
        out.append((delay, "inside Popen" if inside else "after Popen", "ended" if ended else "STILL RUNNING"))
        if job["proc"] is not None and job["proc"].poll() is None:
            job["proc"].kill()
    return out


for label, run, kill in (("as committed", real_run, real_kill), ("no kill in _run", run_nokill, real_kill),
                         ("no kill in kill()", real_run, kill_nokill)):
    WF.JobRunner._run, WF.JobRunner.kill = run, kill
    print(label, fence())
WF.JobRunner._run, WF.JobRunner.kill = real_run, real_kill
