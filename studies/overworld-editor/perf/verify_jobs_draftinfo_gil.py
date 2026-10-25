"""SKEPTIC side-measure for lane jobs: the card's draft-line read (CarryTool._refresh_draft_label's worker:
draft.edited_blocks + draft.stale + draft.last_promote) runs on a worker thread, yet the real-card freeze probes put a
0.4-0.7 s GUI gap on it during a Check. Does the worker hold the GIL? Each function is run on a threading.Thread while
the main thread beats every 10 ms (as verify_jobs_a1_gil.py); longest gap per function, N runs, on the lane's draft
(out/perf/jobs/drafts; read only), then the same with the function inline for its wall.

    py studies/overworld-editor/perf/verify_jobs_draftinfo_gil.py N   -> out/perf/jobs/verify/draftinfo_gil.json
"""
import json
import statistics
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobs_common as J  # noqa: E402

VOUT = J.OUT / "verify"


def on_worker(fn):
    beats = [time.perf_counter()]
    th = threading.Thread(target=fn)
    th.start()
    while th.is_alive():
        time.sleep(0.01)
        beats.append(time.perf_counter())
    gaps = [b - a for a, b in zip(beats, beats[1:])] or [0.0]
    return beats[-1] - beats[0], max(gaps)


def main():
    from ff9mapkit.world import draft as D
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    d = J.draft()
    fns = {"edited_blocks": lambda: D.edited_blocks(d), "stale": lambda: D.stale(d),
           "last_promote": lambda: D.last_promote(d),
           "all_three": lambda: (D.edited_blocks(d), D.stale(d), D.last_promote(d))}
    res = {}
    for name, fn in fns.items():
        walls, gaps = [], []
        for _ in range(n):
            w, g = on_worker(fn)
            walls.append(w)
            gaps.append(g)
        res[name] = {"wall_min": round(min(walls), 3), "wall_med": round(statistics.median(walls), 3),
                     "longest_gap_min": round(min(gaps), 3), "longest_gap_med": round(statistics.median(gaps), 3),
                     "longest_gap_max": round(max(gaps), 3)}
        print(name, res[name], flush=True)
    (VOUT / "draftinfo_gil.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
