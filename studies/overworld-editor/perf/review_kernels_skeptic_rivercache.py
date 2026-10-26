"""Skeptic probe (kernels slice, K1): riveredit.cached_shape's unguarded cache write (eb964b68).

(b) the REAL provision.cache_dir, $FF9MAPKIT_DATA pointing where no directory can be made (its parent is a file):
    cached_shape computes the shape, then mkdir raises and the shape is thrown away -- through the river CARD itself
    (sync lane), every open. The sibling stock cache (worldscan.stock_context) guards the same write ("a read-only
    cache dir costs the cache, not the layer"); RE.shape alone returns.
(c) two in-process reads (the card spawns one per click while the shape is unread) finishing together: both write
    the same .tmp and replace it.

Hermetic: the read seam / RE.shape stand in for the 17-24 s read; nothing under the game install is touched; the cache
lives under studies/overworld-editor/out/perf/review/.
Run from the worktree's ff9mapkit/:  py ../studies/overworld-editor/perf/review_kernels_skeptic_rivercache.py
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _P
_KIT = _P(__file__).resolve().parents[3] / "ff9mapkit"
_sys.path.insert(0, str(_KIT))
import ff9mapkit as _fk
assert _P(_fk.__file__).resolve().is_relative_to(_KIT), _fk.__file__

import os
import shutil
import threading
from pathlib import Path

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from ff9mapkit.world import riveredit as RE

OUT = Path(__file__).resolve().parents[1] / "out" / "perf" / "review" / "skeptic_rivercache"


def fake():
    return RE.RiverShape(tris=np.array([[[1000.0, 3.0, -900.0], [1010.0, 3.0, -900.0], [1000.0, 3.0, -910.0]]]),
                         ring=np.array([[970.0, -860.0], [1060.0, -860.0], [1060.0, -950.0], [970.0, -950.0]]),
                         blocks=[(15, 13), (16, 13), (15, 14), (16, 14)], cells=[(23, 12), (0, 11), (0, 12)],
                         cells_shift=(8, -2), shifts=[(8, -2), (8, -3), (9, 0), (10, 1)])


def part_b():
    blocker = OUT / "blocker"
    blocker.write_text("a file where the cache dir's parent should be")
    os.environ["FF9MAPKIT_DATA"] = str(blocker / "cache")
    game = OUT / "game"
    game.mkdir()
    reads = []
    RE.shape = lambda *, game=None: reads.append(game) or fake()           # the 17-24 s read, stood in
    print("(b) provision.cache_dir() ->", RE._cache_dir())
    try:
        RE.cached_shape(game)
        print("(b) cached_shape returned")
    except OSError as e:
        print("(b) cached_shape: shape computed", len(reads), "time(s), then raised", type(e).__name__, "-", e)
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldriver import RiverTool
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    tool = RiverTool(pick_palette("dark"), WorldView3DPanel(pick_palette("dark")), game_fn=lambda: game,
                     source_fn=lambda: OUT / "F", drafts_root=OUT / "d", sync=True)
    for n in (1, 2):
        tool._load_outline(tool.donor())
        print(f"(b) card open #{n}: reads so far {len(reads)} | shape held: {tool._rs() is not None} | label: "
              f"{tool.verdict_lbl.text()!r}")
    print("(b) the pre-commit default, RE.shape(game=...), returns cells:", RE.shape(game=game).cells)
    del os.environ["FF9MAPKIT_DATA"]


def part_c(trials=40, stagger=0.0):
    RE._cache_dir = lambda: OUT / "cache_c"
    game = OUT / "game"
    fails = []
    for t in range(trials):
        shutil.rmtree(OUT / "cache_c", ignore_errors=True)
        bar = threading.Barrier(2)

        def read(game=None):
            bar.wait()                                  # both reads land at the same moment
            return fake()

        def run(delay):
            import time
            time.sleep(delay)
            try:
                RE.cached_shape(game, read=read)
            except OSError as e:
                fails.append(f"{type(e).__name__}: {e.strerror if hasattr(e, 'strerror') else e}")
        th = [threading.Thread(target=run, args=(d,)) for d in (0.0, stagger)]
        for x in th:
            x.start()
        for x in th:
            x.join()
    kinds = sorted(set(fails))
    print(f"(c) {trials} trials, two reads finishing together: {len(fails)} read(s) raised", kinds)


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    real_shape = RE.shape
    part_b()
    RE.shape = real_shape
    part_c()


if __name__ == "__main__":
    main()
