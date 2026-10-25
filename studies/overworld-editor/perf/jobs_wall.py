"""Lane jobs, step 2: the wall time of each card's Check job, run exactly as the card runs it (the argv from the card's
command() builder, cwd = the kit dir, a fresh subprocess per run), N runs each, plus two floors: the bare interpreter
and `python -c "import ff9mapkit.cli"` (what every job pays before its verb starts).

    py studies/overworld-editor/perf/jobs_wall.py N [verb ...]      -> out/perf/jobs/wall_<tag>.json
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


def job_env():
    """JOBS_PYC=warm (the default): the user's Workspace environment -- bytecode written and read, but into a pycache
    PREFIX tree under out/perf/jobs (so nothing is written under the package). JOBS_PYC=none: this agent shell's own
    PYTHONDONTWRITEBYTECODE=1 with the worktree's stale __pycache__ (a Workspace launched from an agent session)."""
    env = dict(os.environ)
    if os.environ.get("JOBS_PYC", "warm") == "warm":
        env.pop("PYTHONDONTWRITEBYTECODE", None)
        env["PYTHONPYCACHEPREFIX"] = str(J.OUT / "pycache")
    return env


def run(argv, cwd):
    t = time.perf_counter()
    r = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=job_env())
    return time.perf_counter() - t, r


def main():
    n = int(sys.argv[1])
    verbs = sys.argv[2:] or ["floor"] + J.VERBS
    d = J.draft()
    cwd = J.kit_cwd()
    res = {}
    for verb in verbs:
        walls, verdicts = [], []
        for i in range(n):
            if verb == "floor":
                argvs = {"interp": [sys.executable, "-c", "pass"],
                         "import_cli": [sys.executable, "-c", "import ff9mapkit.cli"],
                         "cli_help": [sys.executable, "-m", "ff9mapkit", "--help"]}
                for k, a in argvs.items():
                    w, r = run(a, cwd)
                    res.setdefault(f"floor.{k}", {"walls": [], "argv": a})["walls"].append(round(w, 3))
                continue
            tmp = Path(tempfile.mkdtemp(prefix=f"jobs_{verb}_"))
            rep = tmp / "verdict.json"
            argv = J.check_argv(verb, d, rep)
            w, r = run(argv, cwd)
            try:
                v = json.loads(rep.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                v = None
            walls.append(round(w, 3))
            verdicts.append({"code": r.returncode, "ok": None if v is None else v.get("ok"),
                             "gate": None if v is None else (v.get("refused") or {}).get("gate"),
                             "msg": None if v is None else ((v.get("refused") or {}).get("message") or "")[:200],
                             "tail": r.stdout.strip().splitlines()[-2:] + r.stderr.strip().splitlines()[-2:]})
            print(f"{verb:9s} run {i}: {w:6.2f}s code={r.returncode} ok={verdicts[-1]['ok']} "
                  f"gate={verdicts[-1]['gate']} {verdicts[-1]['msg'][:100] if verdicts[-1]['msg'] else ''}",
                  flush=True)
        if verb != "floor":
            res[verb] = {"argv": argv, "walls": walls, "verdicts": verdicts}
    for k, e in res.items():
        if k.startswith("_"):
            continue
        e["min"] = min(e["walls"])
        e["median"] = statistics.median(e["walls"])
        print(f"{k:18s} min {e['min']:6.2f}  median {e['median']:6.2f}  runs {e['walls']}")
    tag = os.environ.get("JOBS_TAG", "_".join(verbs) if len(verbs) < 3 else "all")
    res["_env"] = {"JOBS_PYC": os.environ.get("JOBS_PYC", "warm"), "n": n}
    (J.OUT / f"wall_{tag}.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
