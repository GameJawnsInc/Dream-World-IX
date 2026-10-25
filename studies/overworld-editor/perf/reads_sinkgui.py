"""reads_sinkgui: how far the sink card's cold island-list scan (transplant.sink_candidates, run on a CarryTool._bg
worker thread in the Workspace's own process when the cache is cold) stalls the GUI thread: a 2 ms PreciseTimer on
the main thread's Qt loop, over the scan's first 40 s (the process then exits; nothing is written). Also counts the
disc-1 blocks a precomputed coast-window catalog would cover (blocks with a beach1 part, or any land part).
    py studies/overworld-editor/perf/reads_sinkgui.py"""
import os, sys, threading, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from reads_common import GAME, dump  # noqa: E402
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtCore import QEventLoop, Qt, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from ff9mapkit.world import discmirror as DM, extract as X, transplant as TR  # noqa: E402
app = QApplication([])
X._worldmap_env(1, GAME)
parts = DM._real_parts(1, "0_1", game=GAME)
res = {"blocks_with_any_part": len(parts), "blocks_with_beach1": sum(1 for p in parts.values() if "beach1" in p),
       "blocks_with_terrain": sum(1 for p in parts.values() if "terrain" in p)}
gaps, last = [], [None]
def tick():
    now = time.perf_counter()
    if last[0] is not None:
        gaps.append(now - last[0])
    last[0] = now
mon = QTimer(); mon.setTimerType(Qt.TimerType.PreciseTimer); mon.setInterval(2); mon.timeout.connect(tick)
threading.Thread(target=lambda: TR.sink_candidates(disc=1, game=GAME), daemon=True).start()
loop = QEventLoop(); QTimer.singleShot(40000, loop.quit); mon.start(); loop.exec(); mon.stop()
g = sorted(gaps)
res["sink_scan_first_40s_on_worker"] = {"worst_gui_gap_ms": round(g[-1] * 1000, 1), "p99_gui_gap_ms": round(g[int(len(g) * .99)] * 1000, 1),
    "p90_gui_gap_ms": round(g[int(len(g) * .9)] * 1000, 1), "gaps_over_50ms": sum(1 for x in g if x > .05),
    "gaps_over_100ms": sum(1 for x in g if x > .1), "ticks": len(g), "ideal_ticks": 20000}
print(res)
dump("reads_sinkgui.json", res)
os._exit(0)
