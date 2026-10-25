"""SKEPTIC re-run for lane jobs: the lane's real-card GUI-freeze probe (jobs_gui_freeze.py: the REAL ForestTool /
SinkTool, offscreen, real QProcessRunner, 10 ms QTimer heartbeat, gap attribution) run UNCHANGED, with its output and
its card's drafts redirected under out/perf/jobs/verify/ (the lane's evidence is not touched).

    py studies/overworld-editor/perf/verify_jobs_gui_freeze.py sink|forest TAG  -> out/perf/jobs/verify/gui_freeze_<verb>_<TAG>.json
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
verb, tag = sys.argv[1], sys.argv[2]
import jobs_gui_freeze as G  # noqa: E402  (module setup: warm-bytecode env, temp prefs, QApplication offscreen)

J = G.J
VOUT = J.OUT / "verify"
VOUT.mkdir(parents=True, exist_ok=True)
J.OUT = VOUT
sys.argv = [G.__file__, verb]
G.main()
shutil.move(str(VOUT / f"gui_freeze_{verb}.json"), str(VOUT / f"gui_freeze_{verb}_{tag}.json"))
