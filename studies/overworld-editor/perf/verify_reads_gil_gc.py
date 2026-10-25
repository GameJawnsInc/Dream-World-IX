"""verify_reads_gil_gc: is the GUI-stall floor of a card's soup read the cyclic collector's pauses (not only SoupIndex's
np.asarray, as the reads lane attributed it)? reads_gil's instrument (a 2 ms PreciseTimer on the main Qt loop, offscreen
platform: only the timer loop is needed) around the real CarryTool._read_soup (reads_soup.card_read) on worker threads:

  one / two            gc on (as shipped), one read / east+seam at once
  one_gcoff / two_gcoff gc.disable() for the read's span (a prototype: the collector cannot run in ANY thread then)
The idle loop is measured first (the instrument's floor). Each variant 3 runs, interleaved. Output identity: every read
== the first unpatched read (reads_soup.ix_equal); the collector never changes values.

    py studies/overworld-editor/perf/verify_reads_gil_gc.py
Evidence: out/perf/reads/verify/verify_reads_gil_gc.json"""
from __future__ import annotations

import gc
import os
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reads_common as RC  # noqa: E402

VOUT = RC.WT / "studies" / "overworld-editor" / "out" / "perf" / "reads" / "verify"
RC.OUT, RC.DRAFTS = VOUT, VOUT / "drafts"


def main():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtCore import QEventLoop, Qt, QTimer
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])  # noqa: F841
    import reads_soup as RS
    d = RC.lane_draft()
    held = [RS.card_read(d, False), RS.card_read(d, True)]       # an open card's two frames, as in the Workspace
    ref = {False: held[0], True: held[1]}
    gaps, last = [], [None]

    def tick():
        now = time.perf_counter()
        if last[0] is not None:
            gaps.append(now - last[0])
        last[0] = now
    mon = QTimer()
    mon.setTimerType(Qt.TimerType.PreciseTimer)
    mon.setInterval(2)
    mon.timeout.connect(tick)
    bad = []

    def run_loop(done):
        gaps.clear()
        last[0] = None
        loop = QEventLoop()
        poll = QTimer()
        poll.setInterval(5)
        poll.timeout.connect(lambda: loop.quit() if done() else None)
        mon.start()
        poll.start()
        t0 = time.perf_counter()
        loop.exec()
        dt = time.perf_counter() - t0
        poll.stop()
        mon.stop()
        g = sorted(gaps)
        return {"s": round(dt, 3), "worst_gap_ms": round(g[-1] * 1000, 1) if g else 0,
                "p99_gap_ms": round(g[int(len(g) * 0.99)] * 1000, 1) if g else 0,
                "gaps_over_50ms": sum(1 for x in g if x > 0.05), "ticks": len(g)}

    def threads(seams, gcoff):
        if gcoff:
            gc.disable()
        live = []

        def one(s):
            ix = RS.card_read(d, s)
            if RS.ix_equal(ix, ref[s]) is not None:
                bad.append(s)
        th = [threading.Thread(target=one, args=(s,), daemon=True) for s in seams]
        for t in th:
            t.start()
        live.extend(th)

        def done():
            if any(t.is_alive() for t in live):
                return False
            if gcoff:
                gc.enable()
            return True
        return done

    res = {"cmd": "py studies/overworld-editor/perf/verify_reads_gil_gc.py"}
    t_idle = [0.0]
    res["idle"] = []
    for _ in range(3):
        t_idle[0] = time.perf_counter()
        res["idle"].append(run_loop(lambda: time.perf_counter() - t_idle[0] > 1.0))
    variants = (("one", (False,), False), ("one_gcoff", (False,), True),
                ("two", (False, True), False), ("two_gcoff", (False, True), True))
    for _ in range(3):
        for name, seams, off in variants:
            res.setdefault(name, []).append(run_loop(threads(seams, off)))
    assert gc.isenabled()
    res["identity_failures"] = bad
    for k, v in res.items():
        if isinstance(v, list) and v and isinstance(v[0], dict):
            print(k, "worst_ms", [r["worst_gap_ms"] for r in v], "p99", [r["p99_gap_ms"] for r in v],
                  "over50", [r["gaps_over_50ms"] for r in v], "s", [r["s"] for r in v])
    print("identity failures", bad)
    RC.dump("verify_reads_gil_gc.json", res)


if __name__ == "__main__":
    main()
