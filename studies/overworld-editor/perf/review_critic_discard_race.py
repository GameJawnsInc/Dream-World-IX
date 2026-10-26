"""Completeness critic probe (c658f78f): Open...'s discard of the old draft now runs on the recipe bar's StepWorker,
so the window's thread is free while it runs -- and the map pick (a point read of the drawn site's block files on a
worker) and the draw box (a 3D load) stay enabled while the bar holds. On Windows a file another handle holds open
cannot be unlinked; shutil.rmtree walks bottom-up and stops at the first refusal, so draft.json (a top-level file,
removed last) survives and the gutted folder is still a draft.

Hermetic: a fake game root and a drafts root under studies/overworld-editor/out/perf/review/critic/discard_race/.
The real draft.py (worktree package asserted); the reader is a thread reading the draft's block files the way a
point read or a 3D load does (plain open/read), started while discard runs."""
from __future__ import annotations

import shutil
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve()
WT = HERE.parents[3]
sys.path.insert(0, str(WT / "ff9mapkit"))
from ff9mapkit.world import draft as D  # noqa: E402

assert Path(D.__file__).resolve().is_relative_to(WT), D.__file__
OUT = WT / "studies" / "overworld-editor" / "out" / "perf" / "review" / "critic" / "discard_race"


def setup():
    if OUT.exists():
        shutil.rmtree(OUT)
    game = OUT / "GAME"
    src = game / "FF9CustomMap-world"
    for disc in (1, 4):
        for by in range(20):
            row = src / "FF9_Data" / "WorldMap" / f"Disc{disc}" / "0_1" / f"r{by}"
            row.mkdir(parents=True)
            for bx in range(24):
                for part in ("Terrain", "Object"):
                    (row / f"Block[{bx}][{by}] {part}.ff9mesh").write_bytes(bytes([bx, by]) * 2048)
    d = D.ensure_draft(src, game=game, root=OUT / "drafts")
    return game, src, d


def trial():
    game, src, d = setup()
    files = sorted((d / "FF9_Data").rglob("*.ff9mesh"))
    stop = threading.Event()

    def reader():                                   # a pick's / a load's reads of the drawn draft, one after another
        while not stop.is_set():
            for p in files:
                if stop.is_set():
                    break
                try:
                    with open(p, "rb") as f:
                        f.read()
                except OSError:
                    pass
    err = None
    t = threading.Thread(target=reader, daemon=True)
    t.start()
    time.sleep(0.01)
    try:
        D.discard(d, root=OUT / "drafts")           # what fresh() runs on the StepWorker
    except Exception as e:                          # noqa: BLE001 -- what _opened gets as err
        err = e
    stop.set()
    t.join()
    return game, src, d, err


if __name__ == "__main__":
    game, src, d, err = trial()
    print("discard:", "completed" if err is None else f"RAISED {type(err).__name__}: {err}")
    if err is not None:
        left = len(list((d / "FF9_Data").rglob("*.ff9mesh"))) if (d / "FF9_Data").exists() else 0
        print(f"draft.json still there: {(d / D.DRAFT_FILE).is_file()} | D.is_draft: {D.is_draft(d)} | "
              f"world files left in it: {left} of 1920")
        gone = D.removals(d)
        print(f"D.removals (what the draft 'deleted'): {len(gone)} files, e.g. {gone[:2]}")
        plan = D.promote(d, game=game, dry_run=True, log=lambda *a: None)
        print(f"D.promote dry run: removes {len(plan['removed'])} live file(s) from {src.name}, "
              f"writes {len(plan['promoted'])}")
