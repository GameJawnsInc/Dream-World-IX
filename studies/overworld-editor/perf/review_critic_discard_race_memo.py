"""Completeness critic probe (c658f78f), the 3D view's memo cadence: after a draw-box switch the panel's CellMemo
re-reads only the cells whose files moved -- during a discard, exactly the cells rmtree is deleting (a file gone
moves the fingerprint; the rest of that cell's files are then read). Modelled here: per cell in the load's order,
the cell's files listed (the memo's scandir), and read only when one of them is gone. How often does the discard
stop half way? Same hermetic tree as review_critic_discard_race.py."""
from __future__ import annotations

import os
import random
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent))
import review_critic_discard_race as R  # noqa: E402

D = R.D


def one(rng):
    game, src, d = R.setup()
    tree = d / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
    out = {}

    def gc():
        try:
            D.discard(d, root=R.OUT / "drafts")
        except Exception as e:                       # noqa: BLE001
            out["err"] = e
    w = threading.Thread(target=gc)
    w.start()
    time.sleep(rng.uniform(0.0, 0.3))
    reads = 0
    for by in range(20):
        row = tree / f"r{by}"
        try:
            names = {e.name for e in os.scandir(row)}
        except OSError:
            names = set()
        for bx in range(24):
            mine = [f"Block[{bx}][{by}] {p}.ff9mesh" for p in ("Terrain", "Object")]
            have = [n for n in mine if n in names]
            if len(have) == len(mine):
                continue                              # fingerprint stands: the memo's batches, no read
            for n in have:                            # a file of the cell went: the cell is drawn again
                try:
                    (row / n).read_bytes()
                    reads += 1
                except OSError:
                    pass
    w.join()
    return out.get("err"), reads


if __name__ == "__main__":
    rng = random.Random(11)
    res = [one(rng) for _ in range(30)]
    bad = [e for e, _ in res if e is not None]
    print(f"memo-cadence load: {len(bad)}/30 discards stopped half way; reads per pass "
          f"{min(r for _, r in res)}-{max(r for _, r in res)}")
