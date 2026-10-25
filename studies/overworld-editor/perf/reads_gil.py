"""reads_gil: how far a card's background soup read stalls the GUI thread's event loop (the window freezing), and what
would stop it. The cards read on threading.Thread workers in the Workspace's own process, so a read's pure-Python
work and its long GIL-holding C calls (np.asarray over a 92k-row nested list) take the GIL from the GUI thread.

A 2 ms PreciseTimer on the main thread's Qt event loop records every gap between ticks while the read runs. Variants
(each 3 runs, fresh state; the idle loop is measured first as the instrument's floor):

  idle          nothing running (calibration)
  one           one worker: the card's east read (CarryTool._read_soup, unpatched)
  two           two workers at once: east + seam (what open_tool / island_changed start)
  two_si1ms     'two' with sys.setswitchinterval(0.001)
  one_fast      'one' with the numpy decode of mesh.blockmesh_from_ff9mesh (reads_soup.fast_blockmesh_from_ff9mesh)
  proc          the read in a warm child process (multiprocessing, started beforehand), its SoupIndex pickled back

    py studies/overworld-editor/perf/reads_gil.py
"""
from __future__ import annotations

import multiprocessing as mp
import os
import pickle
import statistics
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reads_common import GAME, dump, lane_draft  # noqa: E402


def _child_read(args):
    folder, seam = args
    import reads_soup as RS
    t0 = time.perf_counter()
    ix = RS.card_read(folder, seam)
    t1 = time.perf_counter()
    blob = pickle.dumps(ix, protocol=pickle.HIGHEST_PROTOCOL)
    return blob, t1 - t0, time.perf_counter() - t1


def main():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtCore import QEventLoop, Qt, QTimer
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    import reads_soup as RS
    from ff9mapkit.world import mesh as M
    draft = lane_draft()
    RS.card_read(draft, False)                           # imports + OS file cache warm

    gaps = []
    last = [None]

    def tick():
        now = time.perf_counter()
        if last[0] is not None:
            gaps.append(now - last[0])
        last[0] = now
    mon = QTimer()
    mon.setTimerType(Qt.TimerType.PreciseTimer)
    mon.setInterval(2)
    mon.timeout.connect(tick)

    def run_loop(done, sec=120):
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

    def threads(seams):
        th = [threading.Thread(target=RS.card_read, args=(draft, s), daemon=True) for s in seams]
        for t in th:
            t.start()
        return lambda: not any(t.is_alive() for t in th)

    res = {"cmd": "py studies/overworld-editor/perf/reads_gil.py", "switchinterval_default": sys.getswitchinterval()}
    t_idle = [None]

    def idle_done():
        return time.perf_counter() - t_idle[0] > 1.0
    out = []
    for _ in range(3):
        t_idle[0] = time.perf_counter()
        out.append(run_loop(idle_done))
    res["idle"] = out
    for name, seams in (("one", (False,)), ("two", (False, True))):
        res[name] = [run_loop(threads(seams)) for _ in range(3)]
    old = sys.getswitchinterval()
    sys.setswitchinterval(0.001)
    try:
        res["two_si1ms"] = [run_loop(threads((False, True))) for _ in range(3)]
    finally:
        sys.setswitchinterval(old)
    M.blockmesh_from_ff9mesh = RS.fast_blockmesh_from_ff9mesh
    try:
        res["one_fast"] = [run_loop(threads((False,))) for _ in range(3)]
        res["two_fast"] = [run_loop(threads((False, True))) for _ in range(3)]
    finally:
        M.blockmesh_from_ff9mesh = RS._orig_bfm
    # a warm child process (spawned and imported beforehand: a long-lived worker, as B3 would be)
    ctx = mp.get_context("spawn")
    with ctx.Pool(2) as pool:
        pool.map(_child_read, [(str(draft), False), (str(draft), True)])     # warm both workers
        res["proc"] = []
        for _ in range(3):
            box = {}

            def go():
                box["r"] = pool.map(_child_read, [(str(draft), False), (str(draft), True)])
                t0 = time.perf_counter()
                box["ix"] = [pickle.loads(b) for b, _r, _p in box["r"]]
                box["unpickle_s"] = time.perf_counter() - t0
            th = threading.Thread(target=go, daemon=True)
            th.start()
            r = run_loop(lambda: not th.is_alive())
            r["child_read_s"] = [round(x[1], 3) for x in box["r"]]
            r["child_pickle_s"] = [round(x[2], 3) for x in box["r"]]
            r["pickle_bytes"] = [len(x[0]) for x in box["r"]]
            r["unpickle_gui_side_s"] = round(box["unpickle_s"], 3)
            res["proc"].append(r)
        ref_e, ref_s = RS.card_read(draft, False), RS.card_read(draft, True)
        res["proc_identity"] = [RS.ix_equal(box["ix"][0], ref_e) or "identical",
                                RS.ix_equal(box["ix"][1], ref_s) or "identical"]
    for k, v in res.items():
        if isinstance(v, list) and v and isinstance(v[0], dict):
            print(k, "worst_ms", [r["worst_gap_ms"] for r in v], "p99", [r["p99_gap_ms"] for r in v],
                  "s", [r["s"] for r in v])
        else:
            print(k, v)
    dump("reads_gil.json", res)


if __name__ == "__main__":
    main()
