"""Where a card job's start spends its GUI-thread second (the tier-1 trace: card._run_job 1.24-1.52 s, of which
draft.begin_step 0.21-0.49 s; the rest is QProcessRunner.start).

    py studies/overworld-editor/perf/t2_start.py [n]

Times, on the GUI thread of a native QApplication: QProcessRunner.start (the package's runner) of a trivial child and
of the argv a forest Check builds (cwd = kit_cwd, as the card), QProcess.start bare, and subprocess.Popen; each n
times, waiting for the child to end between starts. Nothing is written but the evidence.
Evidence: out/perf/t2/t2_start.json
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gui_common as C                                                # noqa: E402

OUT = HERE.parent / "out" / "perf" / "t2"


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    app = C.native_app()
    from PySide6.QtCore import QProcess
    from ff9mapkit.workspace.worldforest import QProcessRunner, kit_cwd
    trivial = [sys.executable, "-c", "pass"]
    check = [sys.executable, "-m", "ff9mapkit", "--help"]
    out = {}

    def runner_case(argv, label):
        times = []
        for _ in range(n):
            r = QProcessRunner()
            done = []
            t = time.perf_counter()
            r.start(argv, kit_cwd(), lambda code, text: done.append(code))
            times.append(round(time.perf_counter() - t, 4))
            while not done:
                app.processEvents()
                time.sleep(0.005)
        out[label] = times
        print(label, times)

    def bare_case(argv, label):
        times = []
        for _ in range(n):
            p = QProcess()
            p.setWorkingDirectory(str(kit_cwd()))
            t = time.perf_counter()
            p.start(argv[0], argv[1:])
            times.append(round(time.perf_counter() - t, 4))
            p.waitForFinished(60000)
        out[label] = times
        print(label, times)

    def popen_case(argv, label):
        times = []
        for _ in range(n):
            t = time.perf_counter()
            p = subprocess.Popen(argv, cwd=str(kit_cwd()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            times.append(round(time.perf_counter() - t, 4))
            p.communicate()
        out[label] = times
        print(label, times)

    runner_case(trivial, "runner_trivial")
    runner_case(check, "runner_cli_help")
    bare_case(trivial, "qprocess_bare_trivial")
    popen_case(trivial, "popen_trivial")
    out["env_bytes"] = sum(len(k) + len(v) + 2 for k, v in os.environ.items())
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "t2_start.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
