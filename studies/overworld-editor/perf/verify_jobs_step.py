"""SKEPTIC re-measure for lane jobs, candidates A1/A2: the SinkTool Accept's draft bookkeeping, timed directly.

The card (workspace/worldforest.CarryTool) calls draft.begin_step in _run_job and draft.commit_step in _job_done; both
run on the GUI thread (from _on_bg, a queued Qt slot, and from the QProcess finished callback). Neither yields to the
event loop, so each call's wall time IS a window freeze. This probe times the two calls in-process, around the REAL
sink Accept (the card's two calls, run as subprocesses as the card's QProcessRunner runs them), on a draft this probe
makes fresh (out/perf/jobs/verify/step<r>/, deleted after):

  step 1: the first sink Accept of the fresh draft (495.116,-293.767; nothing pre-read: the card's real order),
  step 2: a second sink Accept in the same draft (763.212,-841.227),
  plus, per run, a raw first read and a repeat read of a SECOND fresh draft's 2088 snapshot files (first-open cost).

    py studies/overworld-editor/perf/verify_jobs_step.py N     -> out/perf/jobs/verify/step.json
"""
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobs_common as J  # noqa: E402

VOUT = J.OUT / "verify"


def env():
    e = dict(os.environ)
    e.pop("PYTHONDONTWRITEBYTECODE", None)
    e["PYTHONPYCACHEPREFIX"] = str(VOUT / "pycache")
    return e


def sink_accept(d, at):
    from ff9mapkit.world import sinkedit as SE
    tmp = Path(tempfile.mkdtemp(prefix="vjobs_step_"))
    calls = SE.commands(d, at, report=tmp / "verdict.json", report4=tmp / "verdict4.json")
    oks = []
    t = time.perf_counter()
    for k, c in enumerate(calls):
        r = subprocess.run(J.prefix() + c, cwd=str(J.kit_cwd()), env=env(), capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        rep = tmp / ("verdict.json" if k == 0 else "verdict4.json")
        try:
            v = json.loads(rep.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            v = None
        oks.append(None if v is None else v.get("ok"))
        if k == 0 and not (v and v.get("ok")):
            break
    return time.perf_counter() - t, oks


def main():
    from ff9mapkit.world import draft as D
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    res = {"runs": []}
    for r in range(n):
        rec = {}
        root = VOUT / f"step{r}"
        if root.exists():
            shutil.rmtree(root)
        t = time.perf_counter()
        d = D.ensure_draft(J.SOURCE, game=J.GAME, root=root)
        rec["ensure_draft_s"] = time.perf_counter() - t
        for k, at in enumerate(((495.116, -293.767), (763.212, -841.227)), 1):
            t = time.perf_counter()
            D.begin_step(d, D.all_cells())
            rec[f"s{k}_begin_s"] = time.perf_counter() - t
            rec[f"s{k}_job_s"], rec[f"s{k}_oks"] = sink_accept(d, at)
            t = time.perf_counter()
            if rec[f"s{k}_oks"] and rec[f"s{k}_oks"][0]:
                st = D.commit_step(d, {"perf": "sink", "at": list(at)}, f"perf sink {k}")
                rec[f"s{k}_kept_cells"] = len(st["cells"])
            else:
                D.abort_step(d)
            rec[f"s{k}_commit_s"] = time.perf_counter() - t
            rec[f"s{k}_gui_s"] = rec[f"s{k}_begin_s"] + rec[f"s{k}_commit_s"]
        # the first-open cost, separately: a second fresh draft, its snapshot files read twice
        root2 = VOUT / f"fr{r}"
        if root2.exists():
            shutil.rmtree(root2)
        d2 = D.ensure_draft(J.SOURCE, game=J.GAME, root=root2)
        files = D._cell_files(d2, D.all_cells())
        rec["fr_files"] = len(files)
        for p_ in (1, 2):
            t = time.perf_counter()
            for p in files.values():
                p.read_bytes()
            rec[f"fr_read{p_}_s"] = time.perf_counter() - t
        print(json.dumps(rec), flush=True)
        res["runs"].append(rec)
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(root2, ignore_errors=True)
    keys = [k for k in res["runs"][0] if k.endswith("_s")]
    res["summary"] = {k: {"min": round(min(x[k] for x in res["runs"]), 3),
                          "median": round(statistics.median(x[k] for x in res["runs"]), 3)} for k in keys}
    print(json.dumps(res["summary"], indent=1))
    (VOUT / "step.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
