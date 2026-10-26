"""Review probe (3D-view slice): does render.CellMemo's racy-clean rule (5b552547) hold for a LATER load?

The rule tests each file's age against the CURRENT load's clock (``self._at``), not the clock of the load that
recorded the cell's batches. So a cell recorded while its file was young (the racy window) is trusted by any load
more than RACY_NS after the write -- exactly the stale case the rule exists to catch.

Scenario: a file is written; load L1 (the file is young, so the cell is drawn, and recorded); the file is rewritten
within the same clock tick at the same size (simulated with os.utime back to the first write's time, as the commit's
own test does); then L2 runs 2.1 s later. L2 should draw the new bytes.

Hermetic: tmp folders under studies/overworld-editor/out/perf/review/, extract.block_parts pinned (no install read).
Run: py studies/overworld-editor/perf/review_3d_racy.py
"""
from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve()
WT = HERE.parents[3]
sys.path.insert(0, str(WT / "ff9mapkit"))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(WT / "ff9mapkit"), ff9mapkit.__file__

from ff9mapkit.world import extract as X  # noqa: E402
from ff9mapkit.world import mesh as M  # noqa: E402
from ff9mapkit.world import render as R  # noqa: E402
from ff9mapkit.world.extract import CH_NRM, CH_POS, CH_TAN, CH_UV, BlockMesh, encode_id  # noqa: E402

X.block_parts = lambda disc=1, lod="0_1", game=None: {}       # sea everywhere: no stock read, no install


def tri(y):
    pos = [[0.0, y, 0.0], [8.0, y, 0.0], [0.0, y, -8.0]]
    return M.ff9mesh_bytes(BlockMesh(
        name="Block[1][1] Terrain", disc=1, x=1, y=1, lod="0_1", vcount=3, stride=48,
        channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
        chan_arrays={CH_POS: pos, CH_NRM: [[0.0, 1.0, 0.0]] * 3, CH_UV: [[0.0, 0.0]] * 3,
                     CH_TAN: [[float(encode_id(topograph=0)), 0.0, 0.0, 1.0]] * 3},
        flat_index=[0, 1, 2], tris=[[0, 1, 2]], raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[]))


def run(gap_s):
    root = WT / "studies" / "overworld-editor" / "out" / "perf" / "review" / f"racy_{int(gap_s * 10)}"
    shutil.rmtree(root, ignore_errors=True)
    game, lo = root / "game", root / "LOW"
    p = lo / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / "r1" / "Block[1][1] Terrain.ff9mesh"
    p.parent.mkdir(parents=True)
    game.mkdir()
    p.write_bytes(tri(1.0))                                     # written just now
    site = R.RenderSite(cells=((1, 1),), disc=1, game=game, stack=(lo,), parts=("Terrain",))
    memo = R.CellMemo()
    R.load_batches(site, stock=True, memo=memo)                 # L1: young file -> drawn and RECORDED
    st = p.stat()
    p.write_bytes(tri(6.0))                                     # other bytes, the same size...
    os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))            # ...the same time (one clock tick), same file id
    assert p.stat().st_size == st.st_size and p.stat().st_ino == st.st_ino
    time.sleep(gap_s)
    got = R.load_batches(site, stock=True, memo=memo)           # L2
    plain = R.load_batches(site, stock=True)                    # what a load without the memo draws
    print(f"L2 {gap_s:.1f}s after the write: memo y={got[0][1][0][1]}  plain y={plain[0][1][0][1]}  "
          f"{'SAME' if got[0][1][0][1] == plain[0][1][0][1] else 'STALE (memo hands back the bytes L1 read)'}")
    shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    run(0.0)                                                    # the commit's own test: the next load at once
    run(2.1)                                                    # the same, the next load 2.1 s later
