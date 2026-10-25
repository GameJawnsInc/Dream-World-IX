"""reads_gil_memo: reads_gil's GUI-thread stall instrument (2 ms PreciseTimer on the main Qt loop) around the bytes-keyed
soup memo prototype (reads_soup.SoupMemo) on a worker thread: an unchanged re-read, and a re-read after one block
file changed (the lane draft's; put back after), each 3 runs; the unpatched read beside it for the same instrument.
    py studies/overworld-editor/perf/reads_gil_memo.py"""
import os, sys, threading, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from reads_common import dump, lane_draft  # noqa: E402
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtCore import QEventLoop, Qt, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
import reads_soup as RS  # noqa: E402
app = QApplication([])
d = lane_draft()
gaps, last = [], [None]
def tick():
    now = time.perf_counter()
    if last[0] is not None:
        gaps.append(now - last[0])
    last[0] = now
mon = QTimer(); mon.setTimerType(Qt.TimerType.PreciseTimer); mon.setInterval(2); mon.timeout.connect(tick)
def measure(fn):
    gaps.clear(); last[0] = None
    th = threading.Thread(target=fn, daemon=True)
    loop = QEventLoop(); poll = QTimer(); poll.setInterval(5)
    poll.timeout.connect(lambda: loop.quit() if not th.is_alive() else None)
    mon.start(); poll.start(); t0 = time.perf_counter(); th.start(); loop.exec(); dt = time.perf_counter() - t0
    poll.stop(); mon.stop(); g = sorted(gaps)
    return {"s": round(dt, 3), "worst_gap_ms": round(g[-1] * 1000, 1) if g else 0,
            "p99_gap_ms": round(g[int(len(g) * .99)] * 1000, 1) if g else 0, "gaps_over_50ms": sum(1 for x in g if x > .05)}
memo = RS.SoupMemo()
memo.soup(d, False)
res = {"unpatched_east": [measure(lambda: RS.card_read(d, False)) for _ in range(3)],
       "memo_unchanged_east": [measure(lambda: memo.soup(d, False)) for _ in range(3)]}
terr = sorted((d / "FF9_Data" / "WorldMap" / "Disc1" / "0_1").rglob("*Terrain.ff9mesh"))
a, b = terr[0], terr[1]
keep, other = b.read_bytes(), a.read_bytes()
out = []
try:
    for i in range(3):
        b.write_bytes(other if i % 2 == 0 else keep)      # alternate: each run sees a changed block
        out.append(measure(lambda: memo.soup(d, False)))
finally:
    b.write_bytes(keep)
res["memo_one_block_changed_east"] = out
res["draft_restored"] = RS.ix_equal(RS.card_read(d, False), memo.soup(d, False)[0]) or "identical"
for k, v in res.items(): print(k, v)
dump("reads_gil_memo.json", res)
