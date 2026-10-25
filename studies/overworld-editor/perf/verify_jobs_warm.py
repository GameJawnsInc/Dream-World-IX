"""SKEPTIC re-run for lane jobs, candidate B3: the lane's jobs_warm.py (tools/warm_run.py purge iterations + a
no-purge resident loop, each against the cold subprocess verdict) run UNCHANGED, its output redirected to
out/perf/jobs/verify/warm.json (the lane's evidence files are not touched).

    py studies/overworld-editor/perf/verify_jobs_warm.py N verb [verb ...]
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobs_common as J  # noqa: E402
import jobs_warm as W  # noqa: E402

VOUT = J.OUT / "verify"
VOUT.mkdir(parents=True, exist_ok=True)
shutil.copy2(J.OUT / "spots.json", VOUT / "spots.json")
J.OUT = VOUT
sys.argv = [W.__file__] + sys.argv[1:]
W.main()
