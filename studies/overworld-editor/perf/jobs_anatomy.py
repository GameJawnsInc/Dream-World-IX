"""Lane jobs, step 3: the anatomy of ONE card Check, inside a fresh process exactly like the card's job (spawned by
the driver mode below with the job's env), split into: import of ff9mapkit.cli, the UnityPy import, each UnityPy
bundle load (count, seconds, which bundle), the deployed-mesh reads, and the verb's own compute (cProfile).

    py studies/overworld-editor/perf/jobs_anatomy.py drive N verb [verb ...]   # N fresh child runs per verb
    (child) py jobs_anatomy.py child <verb> <out_prefix> [--profile]

The child times wall with perf_counter around each phase, wrapping (not replacing) the functions, so the verb runs
its real code. --profile adds cProfile around cli.main (inflates call-heavy code: use it for shares, not totals).
"""
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

T_START = time.perf_counter()
sys.path.insert(0, str(Path(__file__).resolve().parent))


def child(verb, out_prefix, profile):
    import jobs_common as J                   # pins the worktree package (asserts its __file__)
    t_pin = time.perf_counter()
    rec = {"verb": verb, "phases": {}, "unitypy_loads": [], "deployed_reads": 0, "deployed_read_s": 0.0}
    t = time.perf_counter()
    from ff9mapkit import cli
    rec["phases"]["import_cli"] = time.perf_counter() - t
    t = time.perf_counter()
    import numpy  # noqa: F401
    rec["phases"]["import_numpy"] = time.perf_counter() - t
    t = time.perf_counter()
    import UnityPy
    rec["phases"]["import_unitypy"] = time.perf_counter() - t
    real_load = UnityPy.load

    def load(*a, **k):
        t1 = time.perf_counter()
        env = real_load(*a, **k)
        rec["unitypy_loads"].append([str(a[0])[-40:] if a else "?", round(time.perf_counter() - t1, 4)])
        return env
    UnityPy.load = load
    from ff9mapkit.world import mesh as M
    real_bm = M.blockmesh_from_ff9mesh

    def bm(*a, **k):
        t1 = time.perf_counter()
        try:
            return real_bm(*a, **k)
        finally:
            rec["deployed_reads"] += 1
            rec["deployed_read_s"] += time.perf_counter() - t1
    M.blockmesh_from_ff9mesh = bm
    d = J.draft()
    tmp = Path(tempfile.mkdtemp(prefix=f"jobs_an_{verb}_"))
    argv = J.check_argv(verb, d, tmp / "verdict.json")[3:]      # what cli.main receives (after -m ff9mapkit)
    import contextlib
    import io
    buf = io.StringIO()
    t = time.perf_counter()
    if profile:
        import cProfile
        pr = cProfile.Profile()
        with contextlib.redirect_stdout(buf):
            pr.enable()
            try:
                code = cli.main(argv)
            except SystemExit as e:
                code = e.code
            pr.disable()
        pr.dump_stats(out_prefix + ".pstats")
    else:
        with contextlib.redirect_stdout(buf):
            try:
                code = cli.main(argv)
            except SystemExit as e:
                code = e.code
    rec["phases"]["cli_main"] = time.perf_counter() - t
    rec["phases"]["pin+jobs_common"] = t_pin - T_START
    rec["code"] = code
    try:
        v = json.loads((tmp / "verdict.json").read_text(encoding="utf-8"))
        rec["ok"] = v.get("ok")
        rec["gate"] = (v.get("refused") or {}).get("gate")
    except (OSError, ValueError):
        rec["ok"] = None
    rec["unitypy_load_s"] = sum(s for _n, s in rec["unitypy_loads"])
    rec["in_process_total"] = time.perf_counter() - T_START
    Path(out_prefix + ".json").write_text(json.dumps(rec, indent=1), encoding="utf-8")


def drive(n, verbs):
    import jobs_common as J
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from jobs_wall import job_env
    out = J.OUT / "anatomy"
    out.mkdir(parents=True, exist_ok=True)
    summary = {}
    for verb in verbs:
        runs = []
        for i in range(n):
            pre = str(out / f"{verb}_{i}")
            t = time.perf_counter()
            r = subprocess.run([sys.executable, __file__, "child", verb, pre] + (["--profile"] if i == n else []),
                               cwd=str(J.kit_cwd()), env=job_env(), capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            wall = time.perf_counter() - t
            if r.returncode:
                print(r.stderr[-3000:])
            rec = json.loads(Path(pre + ".json").read_text(encoding="utf-8"))
            rec["wall"] = wall
            runs.append(rec)
            p = rec["phases"]
            print(f"{verb:9s} {i}: wall {wall:6.2f}  cli import {p['import_cli']:.2f}  UnityPy import "
                  f"{p.get('import_unitypy', 0):.2f}  loads {len(rec['unitypy_loads'])}x {rec['unitypy_load_s']:.2f}s  "
                  f"deployed reads {rec['deployed_reads']}x {rec['deployed_read_s']:.2f}s  cli.main "
                  f"{p['cli_main']:.2f}  ok={rec['ok']}", flush=True)
        keys = ["wall", "import_cli", "import_unitypy", "unitypy_load_s", "deployed_read_s", "cli_main"]

        def col(k):
            return [r["wall"] if k == "wall" else r.get(k, r["phases"].get(k, 0.0)) for r in runs]
        summary[verb] = {k: {"min": round(min(col(k)), 3), "median": round(statistics.median(col(k)), 3)}
                         for k in keys}
        summary[verb]["loads"] = runs[0]["unitypy_loads"]
        summary[verb]["ok"] = runs[0]["ok"]
    (out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "child":
        child(sys.argv[2], sys.argv[3], "--profile" in sys.argv)
    elif sys.argv[1] == "drive":
        drive(int(sys.argv[2]), sys.argv[3:])
    elif sys.argv[1] == "profile":          # one profiled child per verb
        import jobs_common as J
        from jobs_wall import job_env
        out = J.OUT / "anatomy"
        out.mkdir(parents=True, exist_ok=True)
        for verb in sys.argv[2:]:
            pre = str(out / f"{verb}_prof")
            r = subprocess.run([sys.executable, __file__, "child", verb, pre, "--profile"], cwd=str(J.kit_cwd()),
                               env=job_env(), capture_output=True, text=True, encoding="utf-8", errors="replace")
            print(verb, r.returncode, r.stderr[-1500:] if r.returncode else "", flush=True)
