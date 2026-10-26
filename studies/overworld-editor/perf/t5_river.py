"""c5 re-measure + identity: the river card's shape read, fresh against the kit cache (PERF.md 7).

    py studies/overworld-editor/perf/t5_river.py

The real install: riveredit.shape (fresh, timed), cached_shape(refresh=True) (writes this install's cache entry in
the worktree's kit cache), cached_shape (the load, timed 5x) -- the loaded shape == the fresh one: tris and ring
np.array_equal with their dtype, blocks / cells / cells_shift / shifts ==.
Evidence: out/perf/t5/t5_river.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import jobs_common as J                                               # noqa: E402  (pins the worktree package)

OUT = HERE.parent / "out" / "perf" / "t5"


def main():
    import numpy as np
    from ff9mapkit.world import riveredit as RE
    t = time.perf_counter()
    fresh = RE.shape(game=J.GAME)
    fresh_s = time.perf_counter() - t
    RE.cached_shape(J.GAME, refresh=True, read=lambda game=None: fresh)
    loads = []
    for _ in range(5):
        t = time.perf_counter()
        got = RE.cached_shape(J.GAME, read=lambda game=None: (_ for _ in ()).throw(AssertionError("not cached")))
        loads.append(round(time.perf_counter() - t, 4))
    same = (np.array_equal(got.tris, fresh.tris) and got.tris.dtype == fresh.tris.dtype
            and np.array_equal(got.ring, fresh.ring) and got.ring.dtype == fresh.ring.dtype
            and (got.blocks, got.cells, got.cells_shift, got.shifts) ==
            (fresh.blocks, fresh.cells, fresh.cells_shift, fresh.shifts))
    out = {"fresh_s": round(fresh_s, 2), "cached_load_s": loads, "identical": same, "tris": int(len(fresh.tris)),
           "shifts": len(fresh.shifts)}
    print(json.dumps(out))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "t5_river.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
