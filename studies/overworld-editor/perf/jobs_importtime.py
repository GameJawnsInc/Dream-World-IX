"""Lane jobs: what each card Check IMPORTS, measured on the real job (its exact argv with `-X importtime` after the
interpreter, the user's warm-bytecode env from jobs_wall.job_env). Sums the importtime tree: total import time (the
top-level entries' cumulative), and the cumulative of the heavy roots (UnityPy, numpy, PIL, scipy, ff9mapkit.*).

    py studies/overworld-editor/perf/jobs_importtime.py N verb [verb ...]   -> out/perf/jobs/importtime.json
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

LINE = re.compile(r"import time:\s+(\d+) \|\s+(\d+) \|( *)(\S+)")
ROOTS = ("UnityPy", "numpy", "PIL", "scipy", "ff9mapkit")


def parse(text):
    rows = []
    for ln in text.splitlines():
        m = LINE.match(ln)
        if m:
            rows.append((int(m[1]), int(m[2]), (len(m[3]) - 1) // 2, m[4]))
    total = sum(c for _s, c, lvl, _n in rows if lvl == 0) / 1e6
    roots = {}
    for _s, c, lvl, name in rows:
        top = name.split(".")[0]
        if top in ROOTS:
            # a root's own cumulative, counted once per first appearance at its shallowest level (an import of
            # UnityPy nested under ff9mapkit.world.extract is UnityPy's cost, and ALSO inside ff9mapkit's)
            key = top if top != "ff9mapkit" else "ff9mapkit(self)"
            if top == "ff9mapkit":
                roots[key] = roots.get(key, 0.0) + _s / 1e6
            elif name == top:
                roots[key] = roots.get(key, 0.0) + c / 1e6
    return total, roots, len(rows)


def main():
    n = int(sys.argv[1])
    verbs = sys.argv[2:]
    d = J.draft()
    res = {}
    for verb in verbs:
        runs = []
        for _ in range(n):
            tmp = Path(tempfile.mkdtemp(prefix=f"jobs_it_{verb}_"))
            argv = J.check_argv(verb, d, tmp / "verdict.json")
            argv = [argv[0], "-X", "importtime"] + argv[1:]
            t = time.perf_counter()
            r = subprocess.run(argv, cwd=str(J.kit_cwd()), env=job_env(), capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            wall = time.perf_counter() - t
            total, roots, nmod = parse(r.stderr)
            runs.append({"wall": wall, "import_total": total, "roots": roots, "modules": nmod, "code": r.returncode})
            print(f"{verb:9s} wall {wall:6.2f}  imports {total:5.2f}s over {nmod} modules  "
                  + "  ".join(f"{k} {v:.2f}" for k, v in sorted(roots.items())), flush=True)
        res[verb] = {"runs": runs,
                     "import_total_min": min(r["import_total"] for r in runs),
                     "import_total_median": statistics.median(r["import_total"] for r in runs)}
    (J.OUT / "importtime.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
