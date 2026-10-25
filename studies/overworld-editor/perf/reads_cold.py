"""reads_cold: the cards' stock reads ("outline_fn") cold, each in FRESH processes (a Workspace's first open of that
card), and again in the same process (a second block / donor / open; the read_block decode memo and the UnityPy env
are process-wide), plus how far each stalls a GUI thread when it runs on a worker thread as the cards run it.

  coast <bx> <by>   coastedit.windows (coastscan.scan_block) with its cache file pointed at an empty temp dir
                    (coastedit._cache_file monkeypatched: the shared cache is neither read nor written); identity:
                    the windows == the shared cache's json for that block (read only)
  river             riveredit.shape (the river card's outline)
  island            islandedit.stock_land (the island card's outline)
  transplant <d>    transplantedit.donor_land(d) + stock_land (the transplant card's outline)
  mountain <d>      mountainedit.outline(d)
  forest <d>        forestedit.outline(d)

    py studies/overworld-editor/perf/reads_cold.py all [runs=3]
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reads_common import GAME, OUT, dump, stat  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="reads_coastcache_"))


def reader(kind, args):
    from ff9mapkit.world import coastedit as CE
    if kind == "coast":
        cell = (int(args[0]), int(args[1]))
        CE._cache_file = lambda game, disc, c: TMP / f"w-{disc}-{c[0]}_{c[1]}-{time.perf_counter_ns()}.json"
        return lambda: CE.windows(GAME, cell)
    if kind == "river":
        from ff9mapkit.world import riveredit as RE
        return lambda: RE.shape(game=GAME)
    if kind == "island":
        from ff9mapkit.world import islandedit as IE
        return lambda: IE.stock_land(game=GAME)
    if kind == "transplant":
        from ff9mapkit.world import transplantedit as TE
        d = tuple(int(v) for v in args[0].split(","))
        return lambda: (TE.donor_land(d, game=GAME), TE.stock_land(game=GAME))
    if kind == "mountain":
        from ff9mapkit.world import mountainedit as ME
        return lambda: ME.outline(args[0], game=GAME)
    if kind == "forest":
        from ff9mapkit.world import forestedit as FE
        d = tuple(int(v) for v in args[0].split(","))
        return lambda: FE.outline(d, game=GAME)
    raise SystemExit(kind)


def child(kind, args):
    t0 = time.perf_counter()
    fn = reader(kind, args)
    from ff9mapkit.world import extract as X
    t_imp = time.perf_counter() - t0
    t0 = time.perf_counter()
    X._worldmap_env(1, GAME)
    t_env = time.perf_counter() - t0
    t0 = time.perf_counter()
    out = fn()
    first = time.perf_counter() - t0
    t0 = time.perf_counter()
    out2 = fn()
    again = time.perf_counter() - t0
    rec = {"kind": kind, "args": args, "import_s": round(t_imp, 3), "env_s": round(t_env, 3),
           "first_s": round(first, 3), "again_same_process_s": round(again, 3)}
    if kind == "coast":
        from ff9mapkit.world import coastedit as CE
        import importlib
        patched = CE._cache_file
        real = importlib.reload(CE)._cache_file(GAME, 1, (int(args[0]), int(args[1])))
        CE._cache_file = patched                         # the worker-thread run below must scan too, not hit the cache
        try:
            ref = json.loads(real.read_text(encoding="utf-8"))["windows"]
            rt = json.loads(json.dumps(out))             # a cold scan hands back tuples inside (_jsonable is shallow)
            rec["identical_to_shared_cache"] = rt == ref and json.loads(json.dumps(out2)) == ref
            rec["cold_equals_cache_without_json_roundtrip"] = out == ref
        except OSError:
            rec["identical_to_shared_cache"] = "no cache"
        rec["windows"] = len(out)
    # the GUI-thread stall while the read runs on a worker (a fresh read: the same fn again, memo warm)
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtCore import QEventLoop, Qt, QTimer
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
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
    th = threading.Thread(target=fn, daemon=True)
    loop = QEventLoop()
    poll = QTimer()
    poll.setInterval(5)
    poll.timeout.connect(lambda: loop.quit() if not th.is_alive() else None)
    mon.start()
    poll.start()
    th.start()
    loop.exec()
    g = sorted(gaps)
    rec["on_worker_thread"] = {"worst_gui_gap_ms": round(g[-1] * 1000, 1) if g else 0,
                               "p99_gui_gap_ms": round(g[int(len(g) * 0.99)] * 1000, 1) if g else 0,
                               "gaps_over_50ms": sum(1 for x in g if x > 0.05)}
    print("RESULT " + json.dumps(rec))


JOBS = [("coast", ["2", "7"]), ("coast", ["5", "15"]), ("coast", ["14", "1"]), ("river", []), ("island", []),
        ("transplant", ["9,3"]), ("mountain", ["13,6-7"]), ("forest", ["13,15"])]


def main():
    runs = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    from ff9mapkit.world import mountainedit as ME, transplantedit as TE
    res = {"cmd": f"py studies/overworld-editor/perf/reads_cold.py all {runs}", "jobs": {}}
    for kind, args in JOBS:
        if kind == "transplant":
            args = ["{},{}".format(*TE.donors()[0]["donor"])]
        if kind == "mountain":
            args = [ME.massif_donors()[0]["donor"]]
        key = " ".join([kind] + args)
        rs = []
        for i in range(runs):
            r = subprocess.run([sys.executable, __file__, "--child", kind, *args], capture_output=True, text=True,
                               timeout=1800)
            line = [ln for ln in r.stdout.splitlines() if ln.startswith("RESULT ")]
            if not line:
                print(r.stdout[-2000:], r.stderr[-3000:])
                rs.append({"failed": r.stderr[-500:]})
                break
            rs.append(json.loads(line[0][7:]))
            print(key, i, rs[-1], flush=True)
        ok = [r for r in rs if "first_s" in r]
        res["jobs"][key] = {"runs": rs,
                            "first": stat([r["first_s"] for r in ok]) if ok else None,
                            "again": stat([r["again_same_process_s"] for r in ok]) if ok else None}
        dump("reads_cold.json", res)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--child":
        child(sys.argv[2], sys.argv[3:])
    else:
        main()
