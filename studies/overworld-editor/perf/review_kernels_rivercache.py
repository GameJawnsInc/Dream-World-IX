"""Review probe (kernels slice): riveredit.cached_shape (eb964b68).

1. THE WRITE IS NOT BEST-EFFORT. cached_shape computes the shape (17-24 s on the real install), then writes the cache
   with no guard: any OSError there (Windows: another process -- a second Workspace, a scanner -- holding the cache
   JSON open, so os.replace onto it is refused; an unwritable $FF9MAPKIT_DATA) discards the computed shape and the
   river card's read fails, where RE.shape() returned it.
2. THE STOCK BYTES ARE NOT IN THE KEY. The docstring says the shape is "a function of the install's stock bytes and
   the code alone"; the key is the install's PATH and the stamp is world/*.py only, so an install whose bytes changed
   at the same path keeps answering the old shape.

Hermetic: the read seam stands in for RE.shape; the cache lives under studies/overworld-editor/out/perf/review/.
Run from the worktree's ff9mapkit/:  py ../studies/overworld-editor/perf/review_kernels_rivercache.py
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _P
_KIT = _P(__file__).resolve().parents[3] / "ff9mapkit"
_sys.path.insert(0, str(_KIT))
import ff9mapkit as _fk
assert _P(_fk.__file__).resolve().is_relative_to(_KIT), _fk.__file__

import shutil
from pathlib import Path

import numpy as np

from ff9mapkit.world import riveredit as RE

OUT = Path(__file__).resolve().parents[1] / "out" / "perf" / "review" / "rivercache"


def shape(tag: float):
    return RE.RiverShape(tris=np.full((1, 3, 3), tag), ring=np.zeros((3, 2)) + tag, blocks=[(1, 2)],
                         cells=[(1, 2)], cells_shift=(0, 0), shifts=[(0, 0)])


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    RE._cache_dir = lambda: OUT / "cache"
    game = OUT / "game"
    game.mkdir()
    calls = []

    def read_a(game=None):
        calls.append("A")
        return shape(1.0)

    def read_b(game=None):
        calls.append("B")
        return shape(2.0)

    RE.cached_shape(game, read=read_a)                                   # first open: computed + cached
    # (2) the install's bytes change, same path, same kit: the old answer comes back, the new bytes never read
    got = RE.cached_shape(game, read=read_b)
    print("(2) after the install changed: reads", calls, "-> tris", float(got.tris[0, 0, 0]), "(the fresh read says 2.0)")
    # (1) a kit change forces a recompute; another process holds the cache JSON open while it is replaced
    real_stamp = RE._code_stamp
    RE._code_stamp = lambda: real_stamp() + "-next-kit"
    (json_path,) = (OUT / "cache" / "world-river").glob("*.json")
    with open(json_path, encoding="utf-8") as _held:                   # a concurrent reader (Windows share mode)
        try:
            rs = RE.cached_shape(game, read=read_b)
            print("(1) with the cache held open: returned tris", float(rs.tris[0, 0, 0]))
        except OSError as e:
            print("(1) with the cache held open: the shape WAS computed (reads", calls, ") and cached_shape raised",
                  type(e).__name__, "-", e)


if __name__ == "__main__":
    main()
