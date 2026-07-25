"""Region-count + emitted-size census over a random sample of REAL FF9 fields."""
from __future__ import annotations

import json
import random
import sys
import time
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/unruffled-moser-861897/ff9mapkit")


def one(path_s):
    import emit
    import roadmap
    from ff9mapkit.scene.bgi import BgiWalkmesh
    p = Path(path_s)
    t0 = time.time()
    try:
        m = BgiWalkmesh.from_bytes(p.read_bytes())
        if len(m.tris) < 2:
            return None
        ro, regs, portals, fo = roadmap.decompose(m)
        R = len(regs)
        NEXT = roadmap.next_hop_table(R, portals)
        cells = sum(1 for r in NEXT for v in r if v >= 0)
        try:
            nb = len(emit.emit_next_chain(NEXT))
            wb = len(emit.emit_waypoint_chain(portals))
            over = False
        except Exception:
            nb = wb = -1
            over = True
        return {"field": p.stem, "tris": len(m.tris), "floors": len(m.floors),
                "regions": R, "portals": len(portals), "cells": cells,
                "next_bytes": nb, "wp_bytes": wb, "jump_overflow": over,
                "overlap": roadmap.floors_overlap_in_xz(m),
                "secs": round(time.time() - t0, 1)}
    except Exception as ex:
        return {"field": p.stem, "error": f"{type(ex).__name__}: {ex}"}


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    files = sorted((HERE / "bgi").glob("*.bgi"))
    random.seed(1009)
    pick = random.sample(files, min(n, len(files)))
    with Pool(8) as pool:
        rows = [r for r in pool.map(one, [str(p) for p in pick]) if r]
    (HERE / "census.json").write_text(json.dumps(rows, indent=1))
    ok = [r for r in rows if "regions" in r]
    ok.sort(key=lambda r: r["regions"])
    print(f"{len(ok)} fields")
    for q, lbl in ((0, "min"), (0.25, "p25"), (0.5, "median"), (0.75, "p75"),
                   (0.9, "p90"), (0.99, "p99"), (1.0, "max")):
        r = ok[min(len(ok) - 1, int(q * (len(ok) - 1)))]
        print(f"  {lbl:7s} regions={r['regions']:4d} tris={r['tris']:4d} "
              f"cells={r['cells']:6d} next={r['next_bytes']:8d}B field={r['field'][:40]}")
    print("jump overflow (>32KB chain):", sum(1 for r in ok if r["jump_overflow"]))
    print("floors overlap in XZ:", sum(1 for r in ok if r["overlap"]), "/", len(ok))
