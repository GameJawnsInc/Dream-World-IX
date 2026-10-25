"""verify_reads_gc: how much of a card's island soup read (CarryTool._read_soup, the real method via reads_soup.card_read)
is the cyclic garbage collector, and how long its single pauses are (a collection holds the GIL: on a worker thread it
is a GUI freeze of that length). The reads lane put the GUI-stall floor on SoupIndex's np.asarray; this checks the
other candidate.

In one process, holding two SoupIndexes (as an open card holds both frames) plus the lane's import set:
  gc_on    card_read east, 5 runs, every collection timed through gc.callbacks (count, total, longest, by generation)
  gc_off   the same 5 runs under gc.disable() (collections cannot run; wall only)
  freeze   gc.freeze() after the held soups are built (they leave the collector's generations), gc on, 5 runs
The result of each read is compared with the first (reads_soup.ix_equal): the collector never changes a value.

    py studies/overworld-editor/perf/verify_reads_gc.py
Evidence: out/perf/reads/verify/verify_reads_gc.json"""
from __future__ import annotations

import gc
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reads_common as RC  # noqa: E402

VOUT = RC.WT / "studies" / "overworld-editor" / "out" / "perf" / "reads" / "verify"
RC.OUT, RC.DRAFTS = VOUT, VOUT / "drafts"
import reads_soup as RS  # noqa: E402

pauses = []
_t = {}


def cb(phase, info):
    if phase == "start":
        _t["t"] = time.perf_counter()
    else:
        pauses.append((info.get("generation"), time.perf_counter() - _t.pop("t", time.perf_counter())))


def main():
    d = RC.lane_draft()
    held = [RS.card_read(d, False), RS.card_read(d, True)]      # an open card's two frames
    ref = RS.card_read(d, False)
    res = {"python": sys.version, "threshold": gc.get_threshold(), "tracked_objects": len(gc.get_objects())}
    gc.callbacks.append(cb)

    def runs(label):
        ts, out = [], []
        for _ in range(5):
            pauses.clear()
            t0 = time.perf_counter()
            ix = RS.card_read(d, False)
            ts.append(time.perf_counter() - t0)
            p = list(pauses)
            out.append({"collections": len(p), "gc_total_ms": round(sum(x for _g, x in p) * 1000, 1),
                        "gc_longest_ms": round(max((x for _g, x in p), default=0) * 1000, 1),
                        "by_gen": {g: sum(1 for gg, _x in p if gg == g) for g in sorted({gg for gg, _x in p})}})
            assert RS.ix_equal(ix, ref) is None
            del ix
        res[label] = {"wall": RC.stat(ts), "gc": out}
    runs("gc_on")
    gc.disable()
    try:
        runs("gc_off")
    finally:
        gc.enable()
    gc.collect()
    gc.freeze()
    res["frozen_objects"] = gc.get_freeze_count()
    runs("freeze_held")
    gc.unfreeze()
    gc.callbacks.remove(cb)
    del held
    RC.dump("verify_reads_gc.json", res)
    for k, v in res.items():
        print(k, v if not isinstance(v, dict) else {"wall": (v["wall"]["min_s"], v["wall"]["median_s"]),
                                                   "gc": [(g["collections"], g["gc_total_ms"], g["gc_longest_ms"])
                                                          for g in v["gc"]]})


if __name__ == "__main__":
    main()
