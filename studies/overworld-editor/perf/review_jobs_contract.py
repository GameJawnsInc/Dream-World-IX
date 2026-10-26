"""Review probe (jobs slice): two edges of JobRunner's contract the new test cannot see.

    py studies/overworld-editor/perf/review_jobs_contract.py

A. "kill ends a job": test_the_job_runner_keeps_the_runner_s_contract kills a 5 s sleeper right after its start
   (while the worker is still inside Popen) and checks only that its done never runs -- which _deliver's identity check
   guarantees by itself. A mutant JobRunner without the worker's ``if job["killed"]: proc.kill()`` (the only kill on
   that path) runs the test's own steps green while the process it "killed" keeps running.
B. "a program that cannot start ends as a failed job": _run catches OSError only; a start that raises anything else
   (here ValueError, an argument holding a NUL) ends no job: busy() stays True, done never runs, and wait() returns
   True all the same.
Nothing is written anywhere.
"""
from __future__ import annotations

import os
import subprocess
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
    from ff9mapkit.workspace import worldforest as WF

    class Mutant(WF.JobRunner):
        def _run(self, job):                             # JobRunner._run without the kill-after-start line
            try:
                proc = subprocess.Popen(job["argv"], cwd=job["cwd"], stdin=subprocess.DEVNULL,
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        creationflags=WF._no_window())
            except OSError as e:
                job["result"] = (-1, f"the job could not start: {e}")
            else:
                job["proc"] = proc
                out, _ = proc.communicate()
                job["result"] = (proc.returncode, out.decode("utf-8", "replace"))
            try:
                self._ended.emit(job)
            except RuntimeError:
                pass

    for R in (WF.JobRunner, Mutant):
        r, got = R(), []
        r.start([sys.executable, "-c", "import time; time.sleep(5)"], ".", lambda code, text: got.append(code))
        job = r._job
        r.kill()
        test_green = (not r.busy()) and r.wait()
        app.processEvents()
        test_green = test_green and got == []
        p = job["proc"]
        alive = p is not None and p.poll() is None
        print(f"A {R.__name__}: the test's kill steps green={test_green}; the killed sleeper still running={alive}")
        if p is not None:
            p.kill()
            p.wait()

    r, got = WF.JobRunner(), []
    r.start([sys.executable, "-c", "print('a\x00b')"], ".", lambda code, text: got.append((code, text)))
    ok = r.wait()
    t = time.time()
    while time.time() - t < 1:
        app.processEvents()
        time.sleep(0.01)
    print(f"B: wait()={ok}, busy()={r.busy()} after 1 s, done ran={got != []} "
          f"(worker alive={r._job['thread'].is_alive() if r._job else None})")


if __name__ == "__main__":
    main()
