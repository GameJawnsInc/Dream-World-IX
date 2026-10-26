"""Review probe (jobs slice): does a QProcess started on the window's thread while JobRunner's worker is inside
subprocess.Popen inherit that job's pipe, so the job's done waits for the OTHER process to end?

    py studies/overworld-editor/perf/review_jobs_inherit.py [trials]

The shell's run_job (Teleport game here, Show in game, Build, Deploy, lint) and the setup dialog start a QProcess on the
window's thread; QProcess calls CreateProcess with bInheritHandles=TRUE and no handle list. Popen makes its child's
pipe ends inheritable for the length of its own CreateProcess. Before 4ce239ed both starts ran on the window's thread
(serialised); now the card's start runs on a worker, concurrently.

Each trial: a JobRunner job of `python -c pass` (ends in ~50 ms); while its worker is still inside Popen, the window's
thread starts QProcess children that sleep HOLD seconds (the shell's job stand-in). The job's done latency is
measured BEFORE those children are killed. A latency near HOLD = the job's pipe was inherited by an unrelated child.
Control: QProcessRunner under the same hammer. Nothing is written anywhere.
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

HOLD = 3.0


def main():
    trials = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    from PySide6.QtCore import QProcess
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    import ff9mapkit
    assert Path(ff9mapkit.__file__).resolve().is_relative_to(KIT.resolve())
    from ff9mapkit.workspace.worldforest import JobRunner, QProcessRunner

    def trial(make):
        r = make()
        got = []
        t0 = time.perf_counter()
        r.start([sys.executable, "-c", "pass"], ".", lambda c, t: got.append(time.perf_counter()))
        others = []

        def in_popen():
            j = getattr(r, "_job", None)
            return isinstance(j, dict) and j["proc"] is None and j["result"] is None
        while (in_popen() if isinstance(r, JobRunner) else len(others) < 3) and len(others) < 40:
            p = QProcess()
            p.start(sys.executable, ["-c", f"import time; time.sleep({HOLD})"])
            others.append(p)
        while not got and time.perf_counter() - t0 < HOLD + 5:
            app.processEvents()
            time.sleep(0.002)
        lat = (got[0] - t0) if got else None
        if not got and isinstance(r, JobRunner):           # (why: the worker's state, then how long it took)
            j = r._job
            print("  no done in", HOLD + 5, "s: thread alive", j and j["thread"].is_alive(), "result",
                  j and j["result"], "children alive", sum(p.state() != QProcess.ProcessState.NotRunning
                                                           for p in others))
            while not got and time.perf_counter() - t0 < 60:
                app.processEvents()
                time.sleep(0.01)
            print("  its done came at", round(got[0] - t0, 2) if got else None, "s")
        for p in others:
            p.kill()
            p.waitForFinished(3000)
        return len(others), lat

    for label, make in (("JobRunner", JobRunner), ("QProcessRunner", QProcessRunner)):
        rows = [trial(make) for _ in range(trials)]
        held = [r for r in rows if r[1] is not None and r[1] >= HOLD * 0.9]
        print(f"{label}: {len(held)}/{trials} jobs whose done waited for an unrelated child "
              f"(latencies s: {[round(r[1], 2) if r[1] is not None else None for r in rows]}; "
              f"children started during the start: {[r[0] for r in rows]})")


if __name__ == "__main__":
    main()
