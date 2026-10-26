"""Completeness critic probe (c658f78f) with the REAL 3D-view read: render.load_batches with the panel's CellMemo,
warmed on "As the game loads it" (the live folder), then the draw box switched to "With the draft" while Open...'s
discard runs on the StepWorker (the draw box is not locked while the bar holds). The draft-mode roots move every
cell's fingerprint, so the load reads the draft's files as rmtree deletes them.
Hermetic: fake game root + drafts root under out/perf/review/critic/discard_race_real/, extract.block_parts pinned to
{} (sea: no stock read), the worktree package asserted."""
from __future__ import annotations

import random
import shutil
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve()
WT = HERE.parents[3]
sys.path.insert(0, str(WT / "ff9mapkit"))
from ff9mapkit.world import draft as D  # noqa: E402
from ff9mapkit.world import extract as X  # noqa: E402
from ff9mapkit.world import mesh as M  # noqa: E402
from ff9mapkit.world import render as R  # noqa: E402
from tests.test_world_render_stack import _tri_mesh  # noqa: E402

assert Path(R.__file__).resolve().is_relative_to(WT), R.__file__
OUT = WT / "studies" / "overworld-editor" / "out" / "perf" / "review" / "critic" / "discard_race_real"
X.block_parts = lambda disc=1, game=None: {}
CELLS = tuple((bx, by) for by in range(20) for bx in range(24))


def setup():
    if OUT.exists():
        shutil.rmtree(OUT)
    game = OUT / "GAME"
    src = game / "FF9CustomMap-world"
    for disc in (1, 4):
        for by in range(20):
            row = src / "FF9_Data" / "WorldMap" / f"Disc{disc}" / "0_1" / f"r{by}"
            row.mkdir(parents=True)
            for bx in range(24):
                (row / f"Block[{bx}][{by}] Terrain.ff9mesh").write_bytes(M.ff9mesh_bytes(_tri_mesh(1.0, bx=bx, by=by)))
    d = D.ensure_draft(src, game=game, root=OUT / "drafts")
    return game, src, d


def one(rng):
    game, src, d = setup()
    memo = R.CellMemo()
    R.load_batches(R.RenderSite(cells=CELLS, disc=1, game=game, stack=(src,), parts=("Terrain",)), stock=True,
                   memo=memo)                                         # the view as it was, warm
    out = {}

    def gc():
        try:
            D.discard(d, root=OUT / "drafts")
        except Exception as e:                       # noqa: BLE001
            out["err"] = e
    w = threading.Thread(target=gc)
    w.start()
    time.sleep(rng.uniform(0.0, 0.2))
    try:                                             # the draw box: "With the draft"
        R.load_batches(R.RenderSite(cells=CELLS, disc=1, game=game, stack=(d, src), parts=("Terrain",)),
                       stock=True, memo=memo)
    except Exception as e:                           # noqa: BLE001 -- the view's own error path
        out["load"] = e
    w.join()
    return out


if __name__ == "__main__":
    rng = random.Random(5)
    res = [one(rng) for _ in range(20)]
    bad = [r["err"] for r in res if "err" in r]
    print(f"real load_batches during discard: {len(bad)}/20 discards stopped half way"
          + (f" (e.g. {type(bad[0]).__name__}: {str(bad[0])[:100]}...)" if bad else ""))
    if bad:
        game, src, d = setup()
