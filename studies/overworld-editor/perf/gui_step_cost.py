"""gui lane, probe: the draft history's snapshot calls that run ON THE GUI THREAD.

    py studies/overworld-editor/perf/gui_step_cost.py [runs]

draft.begin_step runs inside CarryTool._run_job (an Accept's click) and the RecipeBar's _next_row / _put_back (each row
an opened recipe composes, each step an edit's put-back runs again); commit_step in the job's done. begin_step copies
and hashes every file at the step's cells: a forest's are its verdict's blocks (or its read window), but recipe.row_cells
gives every row that is not forest / mountain / hill ALL 480 cells (island, transplant, sink, morph, river), so a
put-back that re-runs one of those -- or an opened recipe's row -- snapshots the whole world tree on the GUI thread.
Measured on a draft of FF9CustomMap-world under out/perf/gui/drafts_step (ours), each begin_step undone by abort_step
(the draft unchanged: its world files' hashes compared before/after).
Evidence: out/perf/gui/gui_step_cost.json, gui_step_cost_all.pstats.
"""
from __future__ import annotations

import cProfile
import hashlib
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gui_common as C                                                # noqa: E402

DRAFTS = C.OUT / "drafts_step"


def world_hash(d: Path) -> str:
    h = hashlib.sha256()
    for p in sorted((d / "FF9_Data" / "WorldMap").rglob("*")):
        if p.is_file():
            h.update(p.relative_to(d).as_posix().encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    from ff9mapkit.world import draft as D
    from ff9mapkit.world import recipe as RC
    d = D.ensure_draft(C.SOURCE, game=C.GAME, root=DRAFTS)
    before = world_hash(d)
    forest_row = {"table": "forest", "center": [1400.0, -460.0], "donor": "13,15"}
    island_row = {"table": "island", "center": [700.0, -300.0]}
    cases = {"forest row_cells": RC.row_cells(forest_row), "island row_cells (all_cells)": RC.row_cells(island_row)}
    out = {"cells": {k: len(v) for k, v in cases.items()}}
    for name, cells in cases.items():
        ts, ta = [], []
        for _ in range(runs):
            t = time.perf_counter()
            D.begin_step(d, cells)
            ts.append(time.perf_counter() - t)
            t = time.perf_counter()
            D.abort_step(d)
            ta.append(time.perf_counter() - t)
        n = len(D._cell_files(d, cells))
        out[name] = {"begin_step": C.stats(ts), "abort_step": C.stats(ta), "files": n}
        print(name, len(cells), "cells", n, "files: begin_step", round(min(ts), 3), "s (median",
              round(sorted(ts)[len(ts) // 2], 3), ") abort", round(min(ta), 3))
    pr = cProfile.Profile()
    pr.enable()
    D.begin_step(d, cases["island row_cells (all_cells)"])
    pr.disable()
    D.abort_step(d)
    pr.dump_stats(str(C.OUT / "gui_step_cost_all.pstats"))
    ts, _ = C.wall(lambda: D._cell_files(d, cases["island row_cells (all_cells)"]), runs)
    out["_cell_files(all_cells) (the glob alone)"] = C.stats(ts)
    out["draft_unchanged"] = world_hash(d) == before
    print("glob alone", round(min(ts), 3), "draft unchanged", out["draft_unchanged"])
    C.dump("gui_step_cost.json", out)


if __name__ == "__main__":
    main()
