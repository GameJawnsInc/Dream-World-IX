"""Tier 1 re-measure: the 3D view's reload after a real edit, with the shipped render.CellMemo (PERF.md 1).

    py studies/overworld-editor/perf/t1_reload.py [runs]

The draft is the gui lane's (out/perf/gui/drafts_proto: a real `world-forest` at c1_lab's spot, made by
gui_proto_reload.py). Its edited files are swapped between before (the live folder's bytes, read only) and after (the
CLI's bytes), so each timed load follows a real change of exactly the cells the Accept wrote. Each run:
  memo:  the panel's path -- load_scene(site, memo) after the memo drew the before-state;
  plain: load_scene(site) with no memo, the same after-state;
and the two Packed / texture sets compared byte for byte. Then the undo direction (after -> before).
Evidence: out/perf/t1/t1_reload.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gui_common as C                                                # noqa: E402  (pins the worktree package)
from gui_proto_reload import DRAFTS, same_packed, same_tex            # noqa: E402

OUT = HERE.parent / "out" / "perf" / "t1"


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    from ff9mapkit.workspace import worldview3d as V
    from ff9mapkit.world import draft as D
    from ff9mapkit.world import mesh as M
    from ff9mapkit.world import render as R
    draft = D.draft_path(C.SOURCE, root=DRAFTS)
    assert draft.is_dir(), f"run gui_proto_reload.py first: {draft}"
    edits = D.edits(draft)
    after = {rel: (draft / rel).read_bytes() for rel in edits}
    before = {rel: ((C.SOURCE / rel).read_bytes() if (C.SOURCE / rel).is_file() else None) for rel in edits}

    def put(state):
        for rel, data in state.items():
            p = draft / rel
            if data is None:
                p.unlink(missing_ok=True)
            else:
                p.write_bytes(data)

    stack = R.game_stack(C.GAME)
    roots = tuple(draft if p.name == C.SOURCE.name else p for p in stack)
    allcells = tuple((bx, by) for by in range(M.GRID_ROWS) for bx in range(M.GRID_COLS))
    site = R.RenderSite(cells=allcells, disc=1, game=C.GAME, stack=roots)
    drawn = []
    real = R._cell_batches
    R._cell_batches = lambda *a: drawn.append(a[1:3]) or real(*a)
    out = {"edited_files": len(edits), "memo_s": [], "plain_s": [], "cells_drawn": [], "identical": []}
    memo = R.CellMemo()
    try:
        put(before)
        V.load_scene(site, memo=memo)                                 # the view as it stands before the Accept
        for i in range(runs):
            put(after)                                                # the Accept writes its cells
            drawn.clear()
            t = time.perf_counter()
            pm, tm = V.load_scene(site, memo=memo)
            out["memo_s"].append(round(time.perf_counter() - t, 3))
            out["cells_drawn"].append(sorted(set(drawn)))
            t = time.perf_counter()
            pp, tp = V.load_scene(site)
            out["plain_s"].append(round(time.perf_counter() - t, 3))
            out["identical"].append(same_packed(pm, pp) and same_tex(tm, tp))
            put(before)                                               # the undo
            pu, tu = V.load_scene(site, memo=memo)
            p0, t0 = V.load_scene(site)
            out["identical"].append(same_packed(pu, p0) and same_tex(tu, t0))
            print(i, out["memo_s"][-1], "s memo vs", out["plain_s"][-1], "s plain; drawn", out["cells_drawn"][-1],
                  "identical", out["identical"][-2:])
    finally:
        R._cell_batches = real
        put(after)                                                    # leave the draft as the CLI wrote it
    out["memo_min_s"], out["plain_min_s"] = min(out["memo_s"]), min(out["plain_s"])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "t1_reload.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("memo_min_s", "plain_min_s", "identical")}))


if __name__ == "__main__":
    main()
