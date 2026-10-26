"""Skeptic probe (3D-view slice, finding 3D-1 on 5b552547): is the CellMemo racy-clean rule's clock the wrong one?

Independent of review_3d_racy.py: here the second write is a GENUINE same-tick rewrite (no os.utime forging) --
write W1, load L1 through the memo, write W2 at once with other bytes of the same size, and keep only the tries
where the filesystem gave W2 the same mtime as W1 (one clock tick). Then wait past RACY_NS and load L2.

It also asks the counterfactual: had the entry been tested against the clock of the load that RECORDED it (as
draft._unmoved tests against its begin stat's ``at``), would L2 have drawn again?

Hermetic: tmp folders under studies/overworld-editor/out/perf/review/, extract.block_parts pinned (no install read).
Run: py studies/overworld-editor/perf/review_3d_skeptic_racy.py
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
from ff9mapkit.world.draft import RACY_NS  # noqa: E402
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


class RecordingClock(R.CellMemo):
    """The counterfactual rule: each entry keeps the clock of the load that recorded it."""

    def batches(self, site, bx, by, ox, oz, stock):
        key = (bx, by, bool(stock), site.disc, str(site.game), tuple(site.parts))
        fp = self._fingerprint(site, bx, by)
        hit = self._cells.get(key)
        if hit is not None and hit[0] == fp and all(f[4] < hit[2] - RACY_NS for f in fp):
            return hit[1]
        out = R._cell_batches(site, bx, by, ox, oz, None, stock, None)
        self._cells[key] = (fp, out, self._at)
        return out


def y_of(b):
    return float(b[0][1][0][1])


def main():
    root = WT / "studies" / "overworld-editor" / "out" / "perf" / "review" / "skeptic_racy"
    shutil.rmtree(root, ignore_errors=True)
    game, lo = root / "game", root / "LOW"
    p = lo / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / "r1" / "Block[1][1] Terrain.ff9mesh"
    p.parent.mkdir(parents=True)
    game.mkdir()
    site = R.RenderSite(cells=((1, 1),), disc=1, game=game, stack=(lo,), parts=("Terrain",))
    a, b = tri(1.0), tri(6.0)
    assert len(a) == len(b) and a != b
    def record():
        """W1, then L1 through the SHIPPED memo, then W2 at once; returns the memo, its recording-clock twin, tries."""
        tries = 0
        while True:
            tries += 1
            p.write_bytes(a)                                    # W1
            m1 = p.stat()
            memo = R.CellMemo()
            t_rec = time.time_ns()                              # the clock load_batches gives this load (use._at)
            l1 = R.load_batches(site, stock=True, memo=memo)    # L1: the file is young -> drawn, recorded y=1
            p.write_bytes(b)                                    # W2: other bytes, same size, NO utime
            m2 = p.stat()
            if (m2.st_mtime_ns, m2.st_size, m2.st_ino) == (m1.st_mtime_ns, m1.st_size, m1.st_ino):
                alt = RecordingClock()
                alt._cells = {k: (v[0], v[1], t_rec) for k, v in memo._cells.items()}
                return memo, alt, tries, m1, l1
            if tries > 5000:
                raise SystemExit("no same-tick rewrite in 5000 tries")
            time.sleep(0.002)

    memo, alt, tries, m1, l1 = record()
    print(f"genuine same-tick rewrite after {tries} tries: W1 and W2 share mtime {m1.st_mtime_ns}, "
          f"size {m1.st_size}, file id {m1.st_ino}; L1 drew y={y_of(l1)}")
    print(f"L2 at once (the commit's test): shipped memo y={y_of(R.load_batches(site, stock=True, memo=memo))}"
          f"  (disk holds y=6.0)")
    memo, alt, tries, m1, l1 = record()
    print(f"re-recorded after {tries} tries; waiting {RACY_NS / 1e9 + 0.1:.1f}s")
    time.sleep(RACY_NS / 1e9 + 0.1)
    late, late_alt = R.load_batches(site, stock=True, memo=memo), R.load_batches(site, stock=True, memo=alt)
    plain = R.load_batches(site, stock=True)
    print(f"L2 {RACY_NS / 1e9 + 0.1:.1f}s later: shipped memo y={y_of(late)}  recording-clock memo y={y_of(late_alt)}"
          f"  plain y={y_of(plain)}  -> shipped {'STALE' if y_of(late) != y_of(plain) else 'ok'}, "
          f"recording-clock {'STALE' if y_of(late_alt) != y_of(plain) else 'ok'}")
    shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    main()
