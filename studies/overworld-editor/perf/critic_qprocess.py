"""critic probe: what QProcessRunner.start and .kill cost the GUI THREAD, over many calls (no lane measured them; the
gui and jobs verifiers each saw an unattributed ~1 s inside card._run_job, once or twice).

    py studies/overworld-editor/perf/critic_qprocess.py [n]

The package's own QProcessRunner (workspace/worldforest.py), unpatched, on a QCoreApplication in this process. Env as
the user's (bytecode on, cached under out/perf/gui/pycache via gui_common). Two series, n each, interleaved:
  A  start() of a real forest CHECK argv (--dry-run, --mod-folder = the critic draft, --game given), pump 0.8 s, then
     kill() -- what a moved handle does to a running Check (_handles_changed -> runner.kill -> waitForFinished(2000)).
  B  start() of `python -c pass`, then the time until done() runs.
Only dry runs: nothing is written but a temp report path. Evidence: out/perf/critic/critic_qprocess.json
"""
from __future__ import annotations

import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gui_common as C                                                # noqa: E402
import os                                                             # noqa: E402

OUT = C.WT / "studies" / "overworld-editor" / "out" / "perf" / "critic"


def st(v):
    return {"n": len(v), "min": round(min(v), 4), "median": round(statistics.median(v), 4), "max": round(max(v), 4),
            "over_100ms": sum(1 for x in v if x >= 0.1), "all": [round(x, 4) for x in v]}


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    os.environ.pop("PYTHONDONTWRITEBYTECODE", None)
    os.environ["PYTHONPYCACHEPREFIX"] = sys.pycache_prefix
    from PySide6.QtCore import QCoreApplication
    app = QCoreApplication.instance() or QCoreApplication([])
    from ff9mapkit.workspace import worldforest as WF
    from ff9mapkit.world import draft as D
    draft = D.draft_path(C.SOURCE, root=OUT / "drafts_chainreload")
    assert D.read_meta(draft) is not None and draft.resolve().is_relative_to(OUT.resolve()), draft
    rep = Path(tempfile.mkdtemp(prefix="critic_qp_")) / "verdict.json"
    check = [sys.executable, "-m", "ff9mapkit", "--game", str(C.GAME), "world-forest", "--mod-folder", str(draft),
             "--center", "1400,-460", "--donor", "13,15", "--dry-run", "--report-json", str(rep)]
    cwd = WF.kit_cwd()

    def pump(sec, until=lambda: False):
        t = time.perf_counter()
        while time.perf_counter() - t < sec:
            app.processEvents()
            if until():
                return time.perf_counter() - t
            time.sleep(0.002)
        return None

    out = {"A_start_s": [], "A_kill_s": [], "B_start_s": [], "B_until_done_s": []}
    r = WF.QProcessRunner()
    for _ in range(n):
        t = time.perf_counter()
        r.start(check, cwd, lambda code, text: None)
        out["A_start_s"].append(time.perf_counter() - t)
        pump(0.8)
        t = time.perf_counter()
        r.kill()
        out["A_kill_s"].append(time.perf_counter() - t)
        done = []
        t = time.perf_counter()
        r.start([sys.executable, "-c", "pass"], cwd, lambda code, text: done.append(code))
        out["B_start_s"].append(time.perf_counter() - t)
        waited = pump(30, lambda: bool(done))
        out["B_until_done_s"].append((time.perf_counter() - t) if waited is not None else 30.0)
    out = {k: st(v) for k, v in out.items()}
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "all"} for k, v in out.items()}, indent=1))
    p = OUT / "critic_qprocess.json"
    p.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("wrote", p)


if __name__ == "__main__":
    main()
