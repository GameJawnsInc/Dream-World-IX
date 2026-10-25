"""SKEPTIC re-run for lane jobs: the floor and each card's Check wall, independently of jobs_wall.py.

Same argv the lane cites (jobs_common.check_argv: the real card's captured argv at the lane's spot, against the
lane's own draft under out/perf/jobs/drafts -- a dry run, nothing written), but:
  * my OWN pycache prefix (out/perf/jobs/verify/pycache), one discarded warm-up pass first, so "warm" is warm;
  * ROUND-ROBIN order across verbs (run i of every verb before run i+1), so a burst of load from another lane does
    not land on one verb's runs only;
  * mode "nopyc": PYTHONDONTWRITEBYTECODE=1 kept and no prefix, i.e. the worktree's own (stale) __pycache__.

    py studies/overworld-editor/perf/verify_jobs_wall.py N warm|nopyc verb...   -> out/perf/jobs/verify/wall_<mode>.json
"""
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobs_common as J  # noqa: E402

VOUT = J.OUT / "verify"
VOUT.mkdir(parents=True, exist_ok=True)


def env_for(mode):
    env = dict(os.environ)
    if mode == "warm":
        env.pop("PYTHONDONTWRITEBYTECODE", None)
        env["PYTHONPYCACHEPREFIX"] = str(VOUT / "pycache")
    else:
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env.pop("PYTHONPYCACHEPREFIX", None)
    return env


def run(argv, env):
    t = time.perf_counter()
    r = subprocess.run(argv, cwd=str(J.kit_cwd()), capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env)
    return time.perf_counter() - t, r


def one(verb, d, env):
    if verb == "floor":
        out = {}
        for k, a in {"interp": [sys.executable, "-c", "pass"],
                     "import_cli": [sys.executable, "-c", "import ff9mapkit.cli"]}.items():
            out[k] = run(a, env)[0]
        return out, None
    tmp = Path(tempfile.mkdtemp(prefix=f"vjobs_{verb}_"))
    rep = tmp / "verdict.json"
    argv = J.check_argv(verb, d, rep)
    assert str(d) in argv, argv
    w, r = run(argv, env)
    try:
        v = json.loads(rep.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        v = None
    return w, {"code": r.returncode, "ok": None if v is None else v.get("ok"),
               "gate": None if v is None else (v.get("refused") or {}).get("gate"),
               "disc": None if v is None else v.get("disc")}


def main():
    n = int(sys.argv[1])
    mode = sys.argv[2]
    verbs = sys.argv[3:]
    d = J.draft()
    env = env_for(mode)
    if mode == "warm":                                   # one discarded pass: fill my prefix tree
        for verb in verbs:
            one(verb, d, env)
    res = {"mode": mode, "n": n, "draft": str(d), "runs": {v: [] for v in verbs}}
    for i in range(n):
        for verb in verbs:
            w, v = one(verb, d, env)
            res["runs"][verb].append({"wall": w, "verdict": v})
            print(verb, i, json.dumps(w) if isinstance(w, dict) else round(w, 3), v, flush=True)
    summ = {}
    for verb, rs in res["runs"].items():
        if verb == "floor":
            for k in ("interp", "import_cli"):
                xs = [r["wall"][k] for r in rs]
                summ[f"floor.{k}"] = {"min": round(min(xs), 3), "median": round(statistics.median(xs), 3)}
        else:
            xs = [r["wall"] for r in rs]
            summ[verb] = {"min": round(min(xs), 3), "median": round(statistics.median(xs), 3),
                          "verdicts": sorted({json.dumps(r["verdict"], sort_keys=True) for r in rs})}
    res["summary"] = summ
    print(json.dumps(summ, indent=1))
    (VOUT / f"wall_{mode}.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
