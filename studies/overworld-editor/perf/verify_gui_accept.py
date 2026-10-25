"""verify (gui skeptic): the lane's gui_accept_trace, UNCHANGED, with extra pass-through timers inside the Accept
click (CarryTool._run_job measured 1.5-1.8 s on the GUI thread in 3 of 5 first Accepts, of which begin_step was only
0.5-0.7 s: what is the rest?), and evidence + drafts redirected under out/perf/gui/verify/.

    py studies/overworld-editor/perf/verify_gui_accept.py [base|p1|proto] [cycles] [tag]
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gui_common as C                                                # noqa: E402

C.OUT = C.OUT / "verify"
C.OUT.mkdir(parents=True, exist_ok=True)
import gui_accept_trace as T                                          # noqa: E402
from ff9mapkit.workspace import worldforest as WF                     # noqa: E402
from ff9mapkit.workspace import worlddoc as WD                        # noqa: E402

for owner, name, label in (
        (WF.QProcessRunner, "start", "QProcessRunner.start"),
        (WF.CarryTool, "_say", "card._say"),
        (WF.CarryTool, "_sync_buttons", "card._sync_buttons"),
        (WF.CarryTool, "_accept_calls", "card._accept_calls"),
        (WF.CarryTool, "_step_cells", "card._step_cells"),
        (WF.CarryTool, "handles", "card.handles"),
        (WD.WorldDoc, "_sync_locks", "WorldDoc._sync_locks"),
        (tempfile, "mkdtemp", "tempfile.mkdtemp")):
    T.wrap(owner, name, label)
sys.argv = [sys.argv[0]] + sys.argv[1:]
T.main()
