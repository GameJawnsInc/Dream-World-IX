"""Completeness critic probe (c658f78f), the realistic cadence: ONE reader pass started while Open...'s discard runs
on the StepWorker -- (a) a 3D load's pass (the draw box switched: disc 1's cells in the load's order, each cell's
files read once), (b) one map pick (one block's two files). How often does the discard stop half way?
Same hermetic tree as review_critic_discard_race.py."""
from __future__ import annotations

import random
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent))
import review_critic_discard_race as R  # noqa: E402

D = R.D


def one(kind, rng):
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
    time.sleep(rng.uniform(0.0, 0.4))               # the click lands somewhere in the discard
    if kind == "load":
        for by in range(20):
            for bx in range(24):
                for part in ("Terrain", "Object"):
                    p = tree / f"r{by}" / f"Block[{bx}][{by}] {part}.ff9mesh"
                    try:
                        p.read_bytes()
                    except OSError:
                        pass
    else:
        bx, by = rng.randrange(24), rng.randrange(20)
        for part in ("Terrain", "Object"):
            try:
                (tree / f"r{by}" / f"Block[{bx}][{by}] {part}.ff9mesh").read_bytes()
            except OSError:
                pass
    w.join()
    return out.get("err")


if __name__ == "__main__":
    rng = random.Random(7)
    for kind, n in (("load", 20), ("pick", 40)):
        errs = [one(kind, rng) for _ in range(n)]
        bad = [e for e in errs if e is not None]
        print(f"{kind}: {len(bad)}/{n} discards stopped half way" +
              (f" (e.g. {type(bad[0]).__name__}: {str(bad[0])[:90]}...)" if bad else ""))
