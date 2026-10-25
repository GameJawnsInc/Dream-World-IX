"""reads_river: the river card's shape read (riveredit.shape: a stock-only function of the install, read once per card
per process, ~17 s) -- its cost shares (cProfile) and a prototype per-install disk cache like the sink's island list
(pickle under out/perf/reads/, never the shared cache), with identity: the cached RiverShape == a fresh read.

    py studies/overworld-editor/perf/reads_river.py
"""
from __future__ import annotations

import cProfile
import io
import pickle
import pstats
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reads_common import GAME, OUT, dump, stat  # noqa: E402

import numpy as np  # noqa: E402

from ff9mapkit.world import extract as X  # noqa: E402
from ff9mapkit.world import riveredit as RE  # noqa: E402


def same(a, b):
    return (np.array_equal(a.tris, b.tris) and a.tris.dtype == b.tris.dtype and np.array_equal(a.ring, b.ring)
            and a.blocks == b.blocks and a.cells == b.cells and a.cells_shift == b.cells_shift and a.shifts == b.shifts)


def main():
    X._worldmap_env(1, GAME)
    pr = cProfile.Profile()
    t0 = time.perf_counter()
    pr.enable()
    rs = RE.shape(game=GAME)
    pr.disable()
    prof_s = time.perf_counter() - t0
    pr.dump_stats(str(OUT / "reads_river.pstats"))
    st = pstats.Stats(pr)
    buf = io.StringIO()
    st.stream = buf
    st.sort_stats("cumulative").print_stats(25)
    p = OUT / "river_shape.pkl"
    t0 = time.perf_counter()
    p.write_bytes(pickle.dumps(rs, protocol=pickle.HIGHEST_PROTOCOL))
    write_s = time.perf_counter() - t0
    loads = []
    for _ in range(5):
        t0 = time.perf_counter()
        got = pickle.loads(p.read_bytes())
        loads.append(time.perf_counter() - t0)
    t0 = time.perf_counter()
    fresh = RE.shape(game=GAME)                          # a second, unprofiled read in the same (warm) process
    fresh_s = time.perf_counter() - t0
    res = {"cmd": "py studies/overworld-editor/perf/reads_river.py", "profiled_s": round(prof_s, 2),
           "warm_process_unprofiled_s": round(fresh_s, 2), "pickle_bytes": p.stat().st_size,
           "cache_write_s": round(write_s, 4), "cache_load": stat(loads),
           "identity_cache_vs_fresh": same(got, fresh), "identity_two_fresh_reads": same(rs, fresh),
           "shifts": len(rs.shifts), "tris": int(rs.tris.shape[0]),
           "pstats_top": buf.getvalue().splitlines()[:50]}
    dump("reads_river.json", res)
    for k, v in res.items():
        if k != "pstats_top":
            print(k, v)
    print("\n".join(res["pstats_top"]))


if __name__ == "__main__":
    main()
