"""SKEPTIC re-run for lane jobs: the lane's per-part Accept timer (jobs_accept.py: fresh draft, Check, begin_step, the
card's Accept call(s), commit_step, the draft-line read) run UNCHANGED, with its drafts and output redirected under
out/perf/jobs/verify/ (the lane's accept.json is not touched).

    py studies/overworld-editor/perf/verify_jobs_accept.py N verb [verb ...]   -> out/perf/jobs/verify/accept.json
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobs_common as J  # noqa: E402
import jobs_accept as A  # noqa: E402

VOUT = J.OUT / "verify"
VOUT.mkdir(parents=True, exist_ok=True)
shutil.copy2(J.OUT / "spots.json", VOUT / "spots.json")
J.OUT = VOUT                                             # drafts -> verify/acc/, output -> verify/accept.json
sys.argv = [A.__file__] + sys.argv[1:]
A.main()
