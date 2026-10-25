"""Lane jobs: where the river card's Check spends its ~25 s (unprofiled perf_counter wrappers, a fresh child per run).
The river card's argv is a MOVE (--at NEW --move-from OLD); on the live folder no placement is free (the card's own
free_shifts is empty), so the lab's move is measured -- a refusal (R1) that still composes BOTH placements before it
refuses. Wrapped: river.compose (each call, tagged probe = the old placement's no-folder composition, or main),
island._delaunay (inside the mint), river.deploy_ownership, river.red_gates, river.stack_occupancy.

    py studies/overworld-editor/perf/jobs_river_split.py N      -> out/perf/jobs/river_split.json
"""
import contextlib
import io
import json
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobs_common as J  # noqa: E402


def child(out):
    from ff9mapkit import cli
    from ff9mapkit.world import island as IS
    from ff9mapkit.world import river as R
    rec = {"compose": [], "delaunay_s": 0.0, "delaunay_calls": 0, "delaunay_pts": []}

    def wrap(mod, name, key):
        f = getattr(mod, name)

        def w(*a, **k):
            t = time.perf_counter()
            try:
                return f(*a, **k)
            finally:
                rec[key] = rec.get(key, 0.0) + time.perf_counter() - t
        setattr(mod, name, w)
    oc = R.compose

    def compose(*a, **k):
        t = time.perf_counter()
        try:
            return oc(*a, **k)
        finally:
            rec["compose"].append({"kind": "main" if k.get("mod_folder") else "probe",
                                   "s": time.perf_counter() - t})
    R.compose = compose
    od = IS._delaunay

    def delaunay(pts):
        t = time.perf_counter()
        try:
            return od(pts)
        finally:
            rec["delaunay_s"] += time.perf_counter() - t
            rec["delaunay_calls"] += 1
            rec["delaunay_pts"].append(len(pts))
    IS._delaunay = delaunay
    for name in ("deploy_ownership", "red_gates", "stack_occupancy", "read_window", "build_fragment", "outline"):
        wrap(R, name, name + "_s")
    d = J.draft()
    rep = Path(tempfile.mkdtemp(prefix="jobs_rs_")) / "verdict.json"
    argv = J.check_argv("river", d, rep)[3:]
    t = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            cli.main(argv)
        except SystemExit:
            pass
    rec["cli_main_s"] = time.perf_counter() - t
    v = json.loads(rep.read_text(encoding="utf-8"))
    rec["ok"], rec["gate"] = v.get("ok"), [g.get("gate") for g in (v.get("gates") or []) if g.get("verdict") == "RED"]
    Path(out).write_text(json.dumps(rec), encoding="utf-8")


def main():
    from jobs_wall import job_env
    n = int(sys.argv[1])
    runs = []
    for _ in range(n):
        out = Path(tempfile.mkdtemp(prefix="jobs_rsx_")) / "r.json"
        subprocess.run([sys.executable, __file__, "child", str(out)], cwd=str(J.kit_cwd()), env=job_env(), check=True)
        r = json.loads(out.read_text(encoding="utf-8"))
        runs.append(r)
        print(f"cli.main {r['cli_main_s']:5.2f} | compose " + ", ".join(f"{c['kind']} {c['s']:.2f}" for c in r["compose"])
              + f" | delaunay {r['delaunay_s']:.2f} ({r['delaunay_calls']} calls, pts {r['delaunay_pts']}) | "
              + " ".join(f"{k} {v:.2f}" for k, v in r.items() if k.endswith("_s") and k not in ("cli_main_s",
                                                                                              "delaunay_s")),
              flush=True)
    summ = {"cli_main_s": {"min": min(r["cli_main_s"] for r in runs),
                           "median": statistics.median(r["cli_main_s"] for r in runs)},
            "probe_compose_s": {"min": min(c["s"] for r in runs for c in r["compose"] if c["kind"] == "probe"),
                                "median": statistics.median(c["s"] for r in runs for c in r["compose"]
                                                            if c["kind"] == "probe")},
            "main_compose_s": {"min": min(c["s"] for r in runs for c in r["compose"] if c["kind"] == "main"),
                               "median": statistics.median(c["s"] for r in runs for c in r["compose"]
                                                           if c["kind"] == "main")},
            "delaunay_s": {"min": min(r["delaunay_s"] for r in runs),
                           "median": statistics.median(r["delaunay_s"] for r in runs)}}
    print(json.dumps(summ))
    (J.OUT / "river_split.json").write_text(json.dumps({"summary": summ, "runs": runs}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    if sys.argv[1] == "child":
        child(sys.argv[2])
    else:
        main()
