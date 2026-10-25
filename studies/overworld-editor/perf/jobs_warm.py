"""Lane jobs: how much of each card Check a RESIDENT process removes (PLAN.md B3, deferred).

Two instruments, both on the card's exact Check argv against the lane's draft, the user's warm-bytecode env:
  A. tools/warm_run.py (the kit's own instrument): one process, Enter piped N-1 times; every iteration PURGES and
     re-imports every first-party module (so it is what a safe-by-default worker pays), keeps UnityPy + the p0data
     envs (+ their mesh index). Its "=== iteration n -- X s" line is the number.
  B. a resident loop with NO purge (the upper bound: modules, the env cache, the block decode memo all kept): one
     child calls cli.main(argv) N times, perf_counter around each.
Every iteration's --report-json verdict is compared with the cold subprocess run's (identity of the protocol on a
dry run: same verdict bytes).

    py studies/overworld-editor/perf/jobs_warm.py N verb [verb ...]     -> out/perf/jobs/warm.json
"""
import json
import re
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobs_common as J  # noqa: E402
from jobs_wall import job_env  # noqa: E402

WARM_RUN = J.WT / "tools" / "warm_run.py"
IT = re.compile(r"=== iteration (\d+) -- ([0-9.]+)s")


def canon(path):
    v = json.loads(Path(path).read_text(encoding="utf-8"))
    return json.dumps(v, sort_keys=True)


def resident_child(verb, n, out):
    import contextlib
    import io
    from ff9mapkit import cli
    d = J.draft()
    rec = []
    for i in range(n):
        rep = Path(tempfile.mkdtemp(prefix=f"jobs_res_{verb}_")) / "verdict.json"
        argv = J.check_argv(verb, d, rep)[3:]
        t = time.perf_counter()
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                cli.main(argv)
            except SystemExit:
                pass
        rec.append({"s": time.perf_counter() - t, "verdict": canon(rep)})
    Path(out).write_text(json.dumps(rec), encoding="utf-8")


def main():
    n = int(sys.argv[1])
    verbs = sys.argv[2:]
    d = J.draft()
    res = {}
    for verb in verbs:
        # the cold reference: one subprocess Check, as the card runs it
        rep0 = Path(tempfile.mkdtemp(prefix=f"jobs_cold_{verb}_")) / "verdict.json"
        argv = J.check_argv(verb, d, rep0)
        t = time.perf_counter()
        subprocess.run(argv, cwd=str(J.kit_cwd()), env=job_env(), capture_output=True)
        cold = time.perf_counter() - t
        ref = canon(rep0)
        # A: warm_run, the same argv (its report path is fixed for every iteration)
        repA = Path(tempfile.mkdtemp(prefix=f"jobs_wr_{verb}_")) / "verdict.json"
        argvA = J.check_argv(verb, d, repA)
        t = time.perf_counter()
        r = subprocess.run([sys.executable, str(WARM_RUN), "-m", "ff9mapkit"] + argvA[3:],
                           input="\n" * (n - 1) + "q\n", cwd=str(J.WT), env=job_env(), capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        whole = time.perf_counter() - t
        its = [float(m[2]) for m in IT.finditer(r.stdout)]
        same_a = canon(repA) == ref                      # the LAST iteration's verdict (the file is rewritten each)
        # B: resident, no purge
        outB = Path(tempfile.mkdtemp(prefix=f"jobs_resB_{verb}_")) / "res.json"
        subprocess.run([sys.executable, __file__, "child", verb, str(n), str(outB)], cwd=str(J.kit_cwd()),
                       env=job_env(), capture_output=True)
        b = json.loads(outB.read_text(encoding="utf-8"))
        same_b = all(x["verdict"] == ref for x in b)
        res[verb] = {"cold_subprocess_s": cold, "warm_run_iterations_s": its, "warm_run_process_s": whole,
                     "warm_run_last_verdict_identical": same_a,
                     "resident_nopurge_s": [x["s"] for x in b], "resident_verdicts_identical": same_b,
                     "warm_run_tail": r.stdout.strip().splitlines()[-3:]}
        warm = its[1:] or [float("nan")]
        print(f"{verb:9s} cold subprocess {cold:5.2f}s | warm_run it1 {its[0] if its else float('nan'):5.2f} then "
              f"min {min(warm):5.2f} med {statistics.median(warm):5.2f} (verdict same {same_a}) | resident no-purge "
              f"it1 {b[0]['s']:5.2f} then min {min(x['s'] for x in b[1:]):5.2f} med "
              f"{statistics.median(x['s'] for x in b[1:]):5.2f} (verdicts same {same_b})", flush=True)
    (J.OUT / "warm.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    if sys.argv[1] == "child":
        resident_child(sys.argv[2], int(sys.argv[3]), sys.argv[4])
    else:
        main()
