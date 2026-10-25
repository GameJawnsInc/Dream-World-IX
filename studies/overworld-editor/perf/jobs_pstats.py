"""Lane jobs: read a verb's cProfile (out/perf/jobs/anatomy/<verb>_prof.pstats): its total, the top functions by
cumulative and by self time (first-party names shortened), and callers of named hot functions.

    py studies/overworld-editor/perf/jobs_pstats.py <verb> [N] [--callers name ...]
"""
import io
import pstats
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobs_common as J  # noqa: E402


def main():
    verb = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 25
    callers = sys.argv[sys.argv.index("--callers") + 1:] if "--callers" in sys.argv else []
    p = pstats.Stats(str(J.OUT / "anatomy" / f"{verb}_prof.pstats"))
    p.strip_dirs()
    print(f"== {verb}: total {p.total_tt:.2f}s (profiled)")
    for key in ("cumulative", "tottime"):
        s = io.StringIO()
        pstats.Stats(str(J.OUT / "anatomy" / f"{verb}_prof.pstats"), stream=s).strip_dirs().sort_stats(key) \
            .print_stats(n)
        print("\n".join(ln for ln in s.getvalue().splitlines()[6:] if ln.strip()))
    for name in callers:
        s = io.StringIO()
        pstats.Stats(str(J.OUT / "anatomy" / f"{verb}_prof.pstats"), stream=s).strip_dirs() \
            .sort_stats("cumulative").print_callers(name)
        print("\n".join(ln for ln in s.getvalue().splitlines()[6:] if ln.strip())[:4000])


if __name__ == "__main__":
    main()
