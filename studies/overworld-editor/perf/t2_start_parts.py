"""Which part of QProcessRunner.start stalls (t2_start.py: 0.55-1.18 s in pairs, never for a bare QProcess).

    py studies/overworld-editor/perf/t2_start_parts.py [n]

Each iteration builds the runner's QProcess step by step and times each step on the GUI thread; with gc on and with
gc frozen (gc.disable for the loop), and with MergedChannels on and off. Evidence: out/perf/t2/t2_start_parts.json
"""
from __future__ import annotations

import gc
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gui_common as C                                                # noqa: E402

OUT = HERE.parent / "out" / "perf" / "t2"


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    app = C.native_app()
    from PySide6.QtCore import QProcess
    from ff9mapkit.workspace.worldforest import kit_cwd
    argv = [sys.executable, "-c", "pass"]
    out = {}

    def case(label, merged=True, gc_off=False, keep=False):
        rows, held = [], []
        if gc_off:
            gc.disable()
        try:
            for _ in range(n):
                t = [time.perf_counter()]
                proc = QProcess()
                t.append(time.perf_counter())
                if merged:
                    proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
                proc.setWorkingDirectory(str(kit_cwd()))
                got = []
                proc.readyReadStandardOutput.connect(lambda: got.append(bytes(proc.readAllStandardOutput())))
                proc.finished.connect(lambda code, st: got.append(code))
                t.append(time.perf_counter())
                proc.start(argv[0], argv[1:])
                t.append(time.perf_counter())
                while proc.state() != QProcess.ProcessState.NotRunning:
                    app.processEvents()
                    time.sleep(0.005)
                app.processEvents()
                rows.append([round(b - a, 4) for a, b in zip(t, t[1:])])
                if keep:
                    held.append(proc)
        finally:
            if gc_off:
                gc.enable()
        out[label] = rows
        print(label, [r for r in rows if max(r) > 0.05] or "no step over 50 ms", "starts:", [r[2] for r in rows])

    case("merged_gc_on")
    case("merged_gc_off", gc_off=True)
    case("unmerged_gc_on", merged=False)
    case("merged_gc_on_keep", keep=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "t2_start_parts.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
