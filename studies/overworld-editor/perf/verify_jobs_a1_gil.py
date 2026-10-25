"""SKEPTIC check for lane jobs, candidate A1 (move draft.begin_step / commit_step off the GUI thread). The lane did not
prototype A1; its gain claim assumes a worker thread frees the window. Under the GIL that holds only if the step's
work releases the GIL often enough. Measured here without Qt: a 10 ms "heartbeat" loop on the MAIN thread (what the
GUI thread would do: wake every 10 ms), while begin_step(all 480 cells) + commit_step run

  arm inline: on the main thread itself (today: the heartbeat cannot run at all -> one gap = the whole step),
  arm worker: on a threading.Thread (A1), the main thread keeps beating.

Each arm on its own fresh draft (out/perf/jobs/verify/gil_<arm><r>/, deleted after), so both meet the first-open cost;
then a second begin/commit on the same draft (files read once). No job runs between begin and commit (commit then
keeps no cell: the same file walk, fewer kept copies than a real sink's 1 cell).

    py studies/overworld-editor/perf/verify_jobs_a1_gil.py N    -> out/perf/jobs/verify/a1_gil.json
"""
import json
import shutil
import statistics
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobs_common as J  # noqa: E402

VOUT = J.OUT / "verify"


def step(D, d):
    D.begin_step(d, D.all_cells())
    D.commit_step(d, {"perf": "gil"}, "perf gil")


def beat_while(fn, *, worker):
    beats = [time.perf_counter()]
    if worker:
        th = threading.Thread(target=fn)
        th.start()
        while th.is_alive():
            time.sleep(0.01)
            beats.append(time.perf_counter())
        th.join()
    else:
        fn()                                             # the heartbeat cannot run until fn returns
    beats.append(time.perf_counter())
    gaps = [b - a for a, b in zip(beats, beats[1:])]
    return {"wall_s": round(beats[-1] - beats[0], 3), "longest_gap_s": round(max(gaps), 3),
            "gaps_over_100ms_s": round(sum(g for g in gaps if g > 0.1), 3),
            "n_gaps_over_50ms": sum(1 for g in gaps if g > 0.05), "beats": len(beats)}


def main():
    from ff9mapkit.world import draft as D
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    res = {"runs": []}
    for r in range(n):
        for arm in (("inline", "worker") if r % 2 == 0 else ("worker", "inline")):
            root = VOUT / f"gil_{arm}{r}"
            if root.exists():
                shutil.rmtree(root)
            d = D.ensure_draft(J.SOURCE, game=J.GAME, root=root)
            first = beat_while(lambda: step(D, d), worker=arm == "worker")
            again = beat_while(lambda: step(D, d), worker=arm == "worker")
            rec = {"run": r, "arm": arm, "first": first, "again": again}
            print(json.dumps(rec), flush=True)
            res["runs"].append(rec)
            shutil.rmtree(root, ignore_errors=True)
    summ = {}
    for arm in ("inline", "worker"):
        for ph in ("first", "again"):
            rs = [x[ph] for x in res["runs"] if x["arm"] == arm]
            summ[f"{arm}.{ph}"] = {k: {"min": min(x[k] for x in rs), "median": statistics.median(x[k] for x in rs)}
                                   for k in ("wall_s", "longest_gap_s", "gaps_over_100ms_s")}
    res["summary"] = summ
    print(json.dumps(summ, indent=1))
    (VOUT / "a1_gil.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
