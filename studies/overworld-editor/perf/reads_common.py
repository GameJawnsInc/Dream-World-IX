"""Shared setup for the reads_ lane's probes: pin the worktree package, the install (READ ONLY), the lane's own draft.

Every probe imports this first. Nothing here writes outside OUT (studies/overworld-editor/out/perf/reads/)."""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

WT = Path(r"C:\gd\Dream-World-IX\.claude\worktrees\terrain-shaping-continue-4647b2")
sys.path.insert(0, str(WT / "ff9mapkit"))
import ff9mapkit  # noqa: E402

assert Path(ff9mapkit.__file__).resolve().is_relative_to(WT / "ff9mapkit"), ff9mapkit.__file__

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
SOURCE = GAME / "FF9CustomMap-world"                      # read only: the draft is a copy of its world files
OUT = WT / "studies" / "overworld-editor" / "out" / "perf" / "reads"
OUT.mkdir(parents=True, exist_ok=True)
DRAFTS = OUT / "drafts"


def lane_draft():
    """The lane's own draft of the live world folder (copied once; reads only from the install)."""
    from ff9mapkit.world import draft as D
    d = D.ensure_draft(SOURCE, game=GAME, root=DRAFTS)
    assert d.resolve().is_relative_to(OUT.resolve()), d
    return d


def timeit(fn, runs=5, warm=0):
    """Wall times (s) of ``fn()`` over ``runs`` runs after ``warm`` untimed ones; returns (times, last result)."""
    out = None
    for _ in range(warm):
        out = fn()
    ts = []
    for _ in range(runs):
        t0 = time.perf_counter()
        out = fn()
        ts.append(time.perf_counter() - t0)
    return ts, out


def stat(ts):
    return {"runs": len(ts), "min_s": round(min(ts), 4), "median_s": round(statistics.median(ts), 4),
            "max_s": round(max(ts), 4), "all_s": [round(t, 4) for t in ts]}


def dump(name, doc):
    p = OUT / name
    p.write_text(json.dumps(doc, indent=1, default=str), encoding="utf-8")
    print("wrote", p)
    return p
