"""verify (gui skeptic): re-run one of the gui lane's probes UNCHANGED, but with its evidence and drafts redirected
under out/perf/gui/verify/ so the lane's own evidence files are not overwritten.

    py studies/overworld-editor/perf/verify_gui_run.py <probe name without .py> [its args...]
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gui_common as C                                                # noqa: E402  (pins the worktree package)

C.OUT = C.OUT / "verify"
C.OUT.mkdir(parents=True, exist_ok=True)
probe = sys.argv[1]
assert probe.startswith("gui_"), probe
sys.argv = [str(HERE / f"{probe}.py")] + sys.argv[2:]
runpy.run_path(str(HERE / f"{probe}.py"), run_name="__main__")
