"""Skeptic probe (jobs slice, J1): how wide is JobRunner's inheritable-pipe window, and does ONE QProcess start at a
given delay after JobRunner.start (the realistic case: one shell job, not a hammer) hold the job's done?

    py studies/overworld-editor/perf/review_jobs_skeptic_window.py [trials]

Part 1 times subprocess.Popen inside the worker (the window during which c2pwrite is an inheritable handle) for the
real argv shape of a card job (python -m ff9mapkit --help from kit_cwd), N times.
Part 2: for each delay d, JobRunner.start(`python -c pass`), sleep d, ONE QProcess.start(sleep HOLD); the job's done
latency is read before that child is killed. Nothing is written anywhere.
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

HOLD = 2.0


def main():
    trials = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    from PySide6.QtCore import QProcess
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    import ff9mapkit
    assert Path(ff9mapkit.__file__).resolve().is_relative_to(KIT.resolve())
    from ff9mapkit.workspace import worldforest as WF

    durs = []
    real = subprocess.Popen

    class Timed(real):
        def __init__(self, *a, **k):
            t = time.perf_counter()
            super().__init__(*a, **k)
            durs.append(time.perf_counter() - t)
    WF.subprocess.Popen = Timed                   # (this probe's process only; restored below)
    try:
        r = WF.JobRunner()
        for _ in range(trials * 3):
            got = []
            r.start([sys.executable, "-m", "ff9mapkit", "--version"], WF.kit_cwd(), lambda c, t: got.append(c))
            r.wait()
    finally:
        WF.subprocess.Popen = real
    durs.sort()
    print(f"Popen window (ms) over {len(durs)} starts: min {durs[0]*1e3:.1f}, median {durs[len(durs)//2]*1e3:.1f}, "
          f"max {durs[-1]*1e3:.1f}")

    for d in (0.0, 0.002, 0.005, 0.010, 0.020, 0.050, 0.200):
        held, lats = 0, []
        for _ in range(trials):
            r, got = WF.JobRunner(), []
            t0 = time.perf_counter()
            r.start([sys.executable, "-c", "pass"], ".", lambda c, t: got.append(time.perf_counter()))
            time.sleep(d)
            p = QProcess()
            p.start(sys.executable, ["-c", f"import time; time.sleep({HOLD})"])
            while not got and time.perf_counter() - t0 < HOLD + 3:
                app.processEvents()
                time.sleep(0.002)
            lat = (got[0] - t0) if got else None
            lats.append(None if lat is None else round(lat, 2))
            held += lat is None or lat >= HOLD * 0.9
            p.kill()
            p.waitForFinished(3000)
            r.wait()
            app.processEvents()
        print(f"one QProcess.start {d*1e3:.0f} ms after JobRunner.start: held {held}/{trials}; latencies {lats}")


if __name__ == "__main__":
    main()
