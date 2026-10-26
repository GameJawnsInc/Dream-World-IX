"""review2 (rest slice, 4f85170a): in the tab's ordinary flow (an Accept writes a cell, the view reloads at once, then
later reloads), how many loads re-read the accepted cell? Expect: the reload right after the write (young) and ONE
more, then hits. Run from ff9mapkit/: py ../studies/overworld-editor/perf/review2_rest_memo_flow.py"""
import sys
import tempfile
import types
from pathlib import Path

HERE = Path(__file__).resolve()
PKG = HERE.parents[3] / "ff9mapkit"
sys.path.insert(0, str(PKG))
import ff9mapkit
assert Path(ff9mapkit.__file__).resolve().is_relative_to(PKG), ff9mapkit.__file__
from ff9mapkit.world import extract as X
from ff9mapkit.world import mesh as M
from ff9mapkit.world import render as R
from tests.test_world_render_stack import _put, _tri_mesh

X.block_parts = lambda disc=1, game=None: {}
root = Path(tempfile.mkdtemp())
hi, lo = root / "HIGH", root / "LOW"
hi.mkdir(), lo.mkdir()
_put(lo, "Terrain.ff9mesh", M.ff9mesh_bytes(_tri_mesh(1.0)))
site = R.RenderSite(cells=((1, 1),), disc=1, game=root, stack=(hi, lo), parts=("Terrain",))
memo = R.CellMemo()
reads = []
real = R._cell_batches
R._cell_batches = lambda *a, **k: reads.append(1) or real(*a, **k)
import time as _t
clock = [_t.time_ns()]
R.time = types.SimpleNamespace(time_ns=lambda: clock[0])
for i, step in enumerate([0.1, 0.5, 3.0, 10.0, 20.0, 40.0]):   # seconds after the Accept's write, per reload
    clock[0] = _t.time_ns() + int(step * 1e9)
    n = len(reads)
    R.load_batches(site, stock=True, memo=memo)
    print(f"reload at +{step:>4}s: {'re-read' if len(reads) > n else 'hit'}")
