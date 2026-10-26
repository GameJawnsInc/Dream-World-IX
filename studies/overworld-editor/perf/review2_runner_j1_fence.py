"""review2 (runner slice): does test_a_job_s_done_follows_its_exit_not_its_pipe fail against the PIPE runner?

Runs the fence's own scenario twice: on the current JobRunner._run (the temp file) and on the pre-c2c7623a _run
(stdout=PIPE + communicate), restored by monkeypatching. Also runs the J1 scenario the commit names: a child
that is started WHILE the job's handles are inheritable (here: a bInheritHandles child started from another
thread, like a QProcess), and a job child whose own child inherits stdout (Popen(close_fds=False)).
Run from ff9mapkit/:  py ../studies/overworld-editor/perf/review2_runner_j1_fence.py
"""
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "ff9mapkit"))
from PySide6.QtWidgets import QApplication  # noqa: E402
import ff9mapkit.workspace.worldforest as WF  # noqa: E402

app = QApplication.instance() or QApplication([])
new_run = WF.JobRunner._run


def old_run(self, job):
    try:
        proc = subprocess.Popen(job["argv"], cwd=job["cwd"], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, creationflags=WF._no_window())
    except OSError as e:
        job["result"] = (-1, f"the job could not start: {e}")
    else:
        job["proc"] = proc
        if job["killed"]:
            proc.kill()
        out, _ = proc.communicate()
        job["result"] = (proc.returncode, out.decode("utf-8", "replace"))
    try:
        self._ended.emit(job)
    except RuntimeError:
        pass


FENCE = ("import subprocess, sys; subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(8)']); "
         "print('parent done')")
INHERIT = ("import subprocess, sys; subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(8)'], "
           "close_fds=False); print('parent done')")


def run(label, script):
    r, got = WF.JobRunner(), []
    t = time.time()
    r.start([sys.executable, "-c", script], ".", lambda code, text: got.append((code, text.strip())))
    ok = r.wait(30000)
    dt = time.time() - t
    print(f"  {label}: wait={ok} got={got} took {dt:.1f}s -> fence {'PASSES' if ok and got == [(0, 'parent done')] and dt < 6 else 'FAILS'}")


for name, fn in (("current (temp file)", new_run), ("pre-fix (pipe)", old_run)):
    WF.JobRunner._run = fn
    print(name)
    run("the fence's scenario (grandchild, default close_fds)", FENCE)
    run("a grandchild that inherits stdout (close_fds=False)", INHERIT)
WF.JobRunner._run = new_run
