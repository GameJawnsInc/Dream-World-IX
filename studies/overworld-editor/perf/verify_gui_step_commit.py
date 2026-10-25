"""verify (gui skeptic): the history calls a whole-world step pays ON THE GUI THREAD -- begin_step at the click and
commit_step at the job's end -- for D.all_cells(), which is what SinkTool._step_cells returns for EVERY sink Accept
(workspace/worldsink.py:159-161) and recipe.row_cells for island/transplant/sink/morph/river rows. The lane measured
begin_step + abort_step; this measures begin_step + commit_step (a step that changed nothing: commit keeps no cells),
3 runs, on a draft of our own under out/perf/gui/verify/drafts_commit. The draft's world files are hashed before and
after (unchanged).

    py studies/overworld-editor/perf/verify_gui_step_commit.py [runs]
Evidence: out/perf/gui/verify/verify_gui_step_commit.json
"""
from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gui_common as C                                                # noqa: E402

C.OUT = C.OUT / "verify"
C.OUT.mkdir(parents=True, exist_ok=True)
DRAFTS = C.OUT / "drafts_commit"


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    from ff9mapkit.world import draft as D
    from gui_step_cost import world_hash
    from ff9mapkit.workspace import worldsink as WSK
    import inspect
    src = inspect.getsource(WSK.SinkTool._step_cells)
    assert "all_cells()" in src, src
    if DRAFTS.exists():
        shutil.rmtree(DRAFTS)
    d = D.ensure_draft(C.SOURCE, game=C.GAME, root=DRAFTS)
    before = world_hash(d)
    cells = D.all_cells()
    tb, tc, tg = [], [], []
    for _ in range(runs):
        t = time.perf_counter()
        D._cell_files(d, cells)
        tg.append(time.perf_counter() - t)
        t = time.perf_counter()
        D.begin_step(d, cells)
        tb.append(time.perf_counter() - t)
        t = time.perf_counter()
        rec = D.commit_step(d, {"table": "sink", "near": [700.0, -300.0]}, "verify no-op")
        tc.append(time.perf_counter() - t)
        assert rec["cells"] == [], rec["cells"]
    n = len(D._cell_files(d, cells))
    out = {"cells": len(cells), "files": n, "sink_step_cells_is_all_cells": True,
           "begin_step_all": C.stats(tb), "commit_step_all_noop": C.stats(tc), "_cell_files_glob": C.stats(tg),
           "draft_unchanged": world_hash(d) == before,
           "note": "begin+commit, as a sink Accept that wrote nothing would pay them; other lanes ran concurrently"}
    print(out)
    C.dump("verify_gui_step_commit.json", out)


if __name__ == "__main__":
    main()
