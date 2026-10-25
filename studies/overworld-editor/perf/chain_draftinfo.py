"""Lane chain: the cards' "draftinfo" readers after a draft change (an Undo or Redo click), unpatched against two
prototypes, on the REAL bar + four cards wired as WorldDoc wires them.

    py studies/overworld-editor/perf/chain_draftinfo.py [runs]

After every draft change WorldDoc._draft_changed calls island_changed() on every built card, and each card starts a
worker thread running draft.edited_blocks + draft.stale + draft.last_promote (its draft line's counts): four cards,
four threads, eight walks of ~2,100 files at once, beside the GUI thread.
  base -- unpatched;
  fast -- draft.edited_blocks / draft.stale replaced by chain_reads' P4/P2 (one manifest read and one os.scandir walk,
          the stat from the directory entry);
  fast+once -- fast, and the four cards' identical reads of one draft change computed once (the first thread computes,
          the others wait on a lock and take its answer; the key is the change's generation, which this lab's
          draft_changed bumps before it tells the cards).
Per action: the slot (GUI), the time until every reader thread is done (the cards' draft lines are right then), the
readers' summed worker seconds, the event loop's longest freeze while they ran, and every card's draft line text and
_draft_state -- compared across the variants (identity).
"""
from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain_common as CC                                             # noqa: E402
import chain_ops as CO                                                # noqa: E402
import chain_reads as CR                                              # noqa: E402

from ff9mapkit.world import draft as D                                # noqa: E402

REAL = {"edited_blocks": D.edited_blocks, "stale": D.stale}


class Once:
    """One computation per (function, draft, generation); concurrent callers wait for the first."""

    def __init__(self):
        self.gen = 0
        self.lock = threading.Lock()
        self.memo = {}
        self.events = {}

    def wrap(self, name, fn):
        def w(draft):
            key = (name, str(draft), self.gen)
            with self.lock:
                if key in self.memo:
                    return self.memo[key]
                ev = self.events.get(key)
                first = ev is None
                if first:
                    ev = self.events[key] = threading.Event()
            if not first:
                ev.wait()
                return self.memo[key]
            val = fn(draft)
            with self.lock:
                self.memo[key] = val
            ev.set()
            return val
        return w


def labels(lab):
    return {k: (t.draft_lbl.text(), list(t._draft_state) if isinstance(t._draft_state, tuple) else t._draft_state)
            for k, t in lab.tools.items()}


def main(runs=3):
    import chain_build as CB
    out = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "runs": runs, "rows": []}
    for r in range(runs):
        root = CC.fresh_copy(f"draftinfo{r}")
        CO._warm(root)
        base = threading.active_count()
        lab = CB.Lab(root)
        once = Once()
        real_changed = lab.draft_changed

        def changed(d):
            once.gen += 1
            real_changed(d)
        lab.bar._on_changed = changed
        for t in lab.tools.values():
            t._on_changed = changed
            t.open_tool()
            lab.pump(lambda: threading.active_count() <= base, 120)
            t.close_tool()
        lab.pump(lambda: threading.active_count() <= base, 120)
        calls = CC.Calls(D, ["edited_blocks", "stale", "last_promote"])
        row = {}
        for variant in ("base", "fast", "fast+once"):
            calls.restore()                                           # (first: its restore puts back what it wrapped)
            if variant == "base":
                D.edited_blocks, D.stale = REAL["edited_blocks"], REAL["stale"]
            elif variant == "fast":
                D.edited_blocks, D.stale = CR.edited_blocks_once, CR.stale_fast
            else:
                D.edited_blocks = once.wrap("edited_blocks", CR.edited_blocks_once)
                D.stale = once.wrap("stale", CR.stale_fast)
            calls = CC.Calls(D, ["edited_blocks", "stale", "last_promote"])
            row[f"{variant} patched"] = [getattr(D.edited_blocks, "__wrapped__", None) is not None and
                                         getattr(D.edited_blocks.__wrapped__, "__name__", "?"),
                                         getattr(D.stale.__wrapped__, "__name__", "?")]
            for action in ("undo", "redo"):
                m0 = calls.mark()
                t0 = time.perf_counter()
                getattr(lab.bar, action)()
                slot = time.perf_counter() - t0
                # done = every reader thread ended AND its answer delivered to its card (the queued signal ran:
                # the line carries its count again); the first cut sampled between the two and read a stale line
                lp = lab.pump(lambda: threading.active_count() <= base
                              and all("edited" in t.draft_lbl.text() for t in lab.tools.values()), 120)
                done = time.perf_counter() - t0
                wrk = sum(x["s"] for x in calls.rows[m0:] if not x["gui"] and x["depth"] == 0)
                row[f"{variant} {action}"] = {"slot_s": round(slot, 3), "readers_done_s": round(done, 3),
                                              "worker_s": round(wrk, 3), "max_gap": lp["max_gap"],
                                              "labels": labels(lab)}
        calls.restore()
        D.edited_blocks, D.stale = REAL["edited_blocks"], REAL["stale"]
        for v in ("fast", "fast+once"):
            for a in ("undo", "redo"):
                row[f"identical {v} {a}"] = row[f"{v} {a}"]["labels"] == row[f"base {a}"]["labels"]
        out["rows"].append(row)
        print(json.dumps({k: ({kk: vv for kk, vv in v.items() if kk != "labels"} if isinstance(v, dict) else v)
                          for k, v in row.items()}))
        for t in lab.tools.values():
            t.close_tool()
    for v in ("base", "fast", "fast+once"):
        for a in ("undo", "redo"):
            for k in ("slot_s", "readers_done_s", "worker_s", "max_gap"):
                out[f"{v} {a} {k}"] = CC.stats([row[f"{v} {a}"][k] for row in out["rows"]])
    out["sample_labels"] = out["rows"][0]["base undo"]["labels"]
    CC.save("draftinfo.json", out)
    for v in ("base", "fast", "fast+once"):
        print(v, {a: (out[f"{v} {a} readers_done_s"]["min"], out[f"{v} {a} worker_s"]["min"]) for a in ("undo", "redo")})


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
