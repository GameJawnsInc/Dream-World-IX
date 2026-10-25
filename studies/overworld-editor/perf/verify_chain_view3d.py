"""Skeptic of lane chain (K3, op_undo_click / op_redo_click): the lane times an Undo "until every card's draft line is
right" (2.1 s), but most of those cards are HIDDEN, and the visible wait after any draft change is the 3D view's
reload (WorldDoc._draft_changed -> _load_view3d: a worker runs worldview3d.load_scene over the whole map, the draft in
the stack), which the lane did not measure. This probe measures load_scene on the gold draft (the draft drawn in place
of FF9CustomMap-world in the game's FolderNames stack, as WorldDoc._render_site builds it), in a warm process:

  alone          -- load_scene by itself;
  +4 base        -- concurrently with four unpatched draftinfo readers (edited_blocks + stale + last_promote), one per
                    built card, as an Undo starts them;
  +4 fast        -- with chain_reads' P4/P2 readers instead (the lane's K3 'fast');
  +1 fast        -- one P4/P2 reader (K3 'fast+once': one computation per change).

    py studies/overworld-editor/perf/verify_chain_view3d.py [runs]

Read only: the draft is a fresh copy under OUT/work; the install is only read (stock bundles, Memoria.ini).
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain_common as CC                                             # noqa: E402
import chain_reads as CR                                              # noqa: E402

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from ff9mapkit.world import draft as D                                # noqa: E402
from ff9mapkit.world import mesh as M                                 # noqa: E402
from ff9mapkit.world import render as R                               # noqa: E402
from ff9mapkit.workspace.worldview3d import load_scene               # noqa: E402


def site_for(draft):
    cells = tuple((bx, by) for by in range(M.GRID_ROWS) for bx in range(M.GRID_COLS))
    stack = R.game_stack(CC.GAME)
    assert stack is not None
    here = CC.SOURCE_NAME
    names = [p.name for p in stack]
    roots = [draft if p.name == here else p for p in stack] if here in names else [draft] + list(stack)
    return R.RenderSite(cells=cells, disc=1, game=CC.GAME, stack=tuple(roots))


def base_reader(d):
    return ({(bx, by) for disc, bx, by in D.edited_blocks(d) if disc == 1}, D.stale(d), D.last_promote(d))


def fast_reader(d):
    return ({(bx, by) for disc, bx, by in CR.edited_blocks_once(d) if disc == 1}, CR.stale_fast(d),
            D.last_promote(d))


def timed_load(site, readers, d):
    ends = []

    def run(fn):
        fn(d)
        ends.append(time.perf_counter())
    ths = [threading.Thread(target=run, args=(fn,)) for fn in readers]
    t0 = time.perf_counter()
    for th in ths:
        th.start()
    load_scene(site)
    t_load = time.perf_counter() - t0
    for th in ths:
        th.join()
    return round(t_load, 3), (round(max(ends) - t0, 3) if ends else None)


def main(runs=3):
    root = CC.fresh_copy("vview3d")
    d = D.draft_path(CC.SOURCE, root=root)
    for p in Path(root).rglob("*"):
        if p.is_file():
            p.read_bytes()                                            # warm (no first-open debt)
    site = site_for(d)
    t = time.perf_counter()
    load_scene(site)                                                  # first load: bundles, stock decode memos
    out = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "runs": runs, "first_load_s": round(time.perf_counter() - t, 3)}
    print("first load", out["first_load_s"], flush=True)
    conds = {"alone": [], "+4 base": [base_reader] * 4, "+4 fast": [fast_reader] * 4, "+1 fast": [fast_reader]}
    res = {k: [] for k in conds}
    for r in range(runs):
        for k, readers in conds.items():
            res[k].append(timed_load(site, readers, d))
        print(r, {k: v[-1] for k, v in res.items()}, flush=True)
    for k, v in res.items():
        out[f"{k} load_scene_s"] = CC.stats([x[0] for x in v])
        if v[0][1] is not None:
            out[f"{k} readers_done_s"] = CC.stats([x[1] for x in v])
    for k in conds:
        print(k, out[f"{k} load_scene_s"], out.get(f"{k} readers_done_s"))
    p = CC.OUT / "verify" / "view3d.json"
    p.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("->", p)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
