"""SKEPTIC side-measure for lane jobs (a cost the lane's A1/A2 leave in place): the sink Accept snapshots ALL 480 cells
(SinkTool._step_cells = draft.all_cells(), "the disc-4 island's blocks are not known in advance"), yet the sink Check's
own report already names the blocks of the disc-4 run (its report JSON is the disc-4 preview's, "blocks"), and the
committed step keeps 1 cell (verify_jobs_step.py: s1/s2_kept_cells). What would a narrow snapshot plus a cheap
"nothing else moved" guard cost? Measured, on a FRESH draft (out/perf/jobs/verify/sc<r>/, deleted after):

  * begin_step on the Check's named blocks only (the narrow snapshot),
  * a stat-only sweep of every world file at all 480 cells (os.stat of each file found by one listing per row: the
    guard that would catch a write outside the snapshot by (size, mtime_ns)), first and second pass,
  * for scale, begin_step(all_cells) on the same fresh draft afterwards (today's snapshot).

    py studies/overworld-editor/perf/verify_jobs_sinkcells.py N    -> out/perf/jobs/verify/sinkcells.json
"""
import json
import os
import shutil
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobs_common as J  # noqa: E402
import jobs_step_proto as SP  # noqa: E402

VOUT = J.OUT / "verify"


def main():
    from ff9mapkit.world import draft as D
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    v = json.loads((VOUT / "sink_check_verdict.json").read_text(encoding="utf-8"))
    cells = [tuple(b) for b in v["blocks"]]
    _, p_cf, _, _ = SP.install(D)                       # P3: one listing per (disc, lod, row) -- same dict
    D._cell_files = D._cell_files                        # (install returns the patched fn; the module keeps its own)
    res = {"check_blocks": cells, "runs": []}
    for r in range(n):
        root = VOUT / f"sc{r}"
        if root.exists():
            shutil.rmtree(root)
        d = D.ensure_draft(J.SOURCE, game=J.GAME, root=root)
        rec = {}
        t = time.perf_counter()
        D.begin_step(d, cells)
        rec["narrow_begin_s"] = time.perf_counter() - t
        D.abort_step(d)
        for k in (1, 2):
            t = time.perf_counter()
            files = p_cf(d, D.all_cells())
            sig = {rel: (st.st_size, st.st_mtime_ns) for rel, st in ((rel, os.stat(p)) for rel, p in files.items())}
            rec[f"stat_sweep{k}_s"] = time.perf_counter() - t
            rec["stat_files"] = len(sig)
        t = time.perf_counter()
        D.begin_step(d, D.all_cells())
        rec["all_begin_s"] = time.perf_counter() - t
        D.abort_step(d)
        print(json.dumps(rec), flush=True)
        res["runs"].append(rec)
        shutil.rmtree(root, ignore_errors=True)
    res["summary"] = {k: {"min": round(min(x[k] for x in res["runs"]), 4),
                          "median": round(statistics.median(x[k] for x in res["runs"]), 4)}
                      for k in res["runs"][0] if k.endswith("_s")}
    print(json.dumps(res["summary"], indent=1))
    (VOUT / "sinkcells.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
