"""SKEPTIC re-measure for lane jobs, operation "floor": `python -c pass` and `python -c "import ff9mapkit.cli"`,
cwd = the kit dir, N interleaved runs, warm bytecode in MY prefix tree (out/perf/jobs/verify/pycache, already filled by
verify_jobs_wall.py's warm-up), plus the LANE's prefix tree (out/perf/jobs/pycache) as a second arm, and one
`-X importtime` capture of every import_cli run slower than 1 s (top self-time modules), to see what a slow one pays.

    py studies/overworld-editor/perf/verify_jobs_floor.py N     -> out/perf/jobs/verify/floor.json
"""
import json
import os
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobs_common as J  # noqa: E402

VOUT = J.OUT / "verify"


def env(prefix):
    e = dict(os.environ)
    e.pop("PYTHONDONTWRITEBYTECODE", None)
    e["PYTHONPYCACHEPREFIX"] = str(prefix)
    return e


def t(argv, e):
    s = time.perf_counter()
    r = subprocess.run(argv, cwd=str(J.kit_cwd()), env=e, capture_output=True, text=True)
    return time.perf_counter() - s, r


def top_self(stderr, k=8):
    rows = []
    for ln in stderr.splitlines():
        m = re.match(r"import time:\s+(\d+) \|\s+(\d+) \|(\s*)(.+)$", ln)
        if m:
            rows.append((int(m.group(1)), int(m.group(2)), m.group(4).strip()))
    rows.sort(reverse=True)
    return [(name, round(s / 1e6, 3), round(c / 1e6, 3)) for s, c, name in rows[:k]], \
        round(sum(r[0] for r in rows) / 1e6, 3)


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    arms = {"mine": VOUT / "pycache", "lane": J.OUT / "pycache"}
    res = {a: {"interp": [], "import_cli": []} for a in arms}
    slow = []
    for i in range(n):
        for a, pre in (arms.items() if i % 2 == 0 else reversed(list(arms.items()))):
            e = env(pre)
            w0, _ = t([sys.executable, "-c", "pass"], e)
            w1, _ = t([sys.executable, "-c", "import ff9mapkit.cli"], e)
            res[a]["interp"].append(w0)
            res[a]["import_cli"].append(w1)
            print(a, i, round(w0, 3), round(w1, 3), flush=True)
            if w1 > 1.0 and len(slow) < 3:
                w2, r = t([sys.executable, "-X", "importtime", "-c", "import ff9mapkit.cli"], e)
                tops, tot = top_self(r.stderr)
                slow.append({"arm": a, "run": i, "wall_again_importtime": round(w2, 3), "sum_self_s": tot,
                             "top_self": tops})
                print("  slow ->", json.dumps(slow[-1]), flush=True)
    summ = {a: {k: {"min": round(min(v), 3), "median": round(statistics.median(v), 3)} for k, v in d.items()}
            for a, d in res.items()}
    out = {"n": n, "summary": summ, "runs": res, "slow_importtime": slow}
    print(json.dumps(summ, indent=1))
    (VOUT / "floor.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
