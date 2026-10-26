"""Completeness critic probe: commit_step's _write_history (tmp.replace onto history.json) now runs on the card's
StepWorker (1dce6836) and the recipe bar's (c658f78f), while the window's thread may read history.json at the same
moment (RecipeBar.refresh -> D.history: the bar's Undo/Redo refusal while a card writes, Save, the view toggle).
On Windows os.replace onto a file another handle holds open (Python opens without FILE_SHARE_DELETE) is refused.

Part A: the mechanism -- one thread replaying draft._write_history, another reading draft.history, real draft.py.
Part B: the real commit_step on a worker, with a reader calling D.history in a loop as the GUI thread would.
Hermetic: everything under studies/overworld-editor/out/perf/review/critic/. Worktree package asserted."""
from __future__ import annotations

import json
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
OUT = WT / "studies" / "overworld-editor" / "out" / "perf" / "review" / "critic" / "history_race"


def fresh_draft(n_steps=40):
    if OUT.exists():
        shutil.rmtree(OUT)
    d = OUT / "M.draft"
    cell = d / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / "r0"
    cell.mkdir(parents=True)
    (cell / "Block[0][0] Terrain.ff9mesh").write_bytes(b"x" * 64)
    (d / D.DRAFT_FILE).write_text(json.dumps({"source": str(OUT / "M"), "manifest": {}}), encoding="utf-8")
    # a history of realistic size: each step's before/after hashes
    steps = [{"row": {"table": "forest", "center": [i, -i]}, "label": f"forest {i}", "cells": [[0, 0]],
              "before": {f"FF9_Data/WorldMap/Disc1/0_1/r0/Block[0][0] P{k}.ff9mesh": "a" * 64 for k in range(40)},
              "after": {f"FF9_Data/WorldMap/Disc1/0_1/r0/Block[0][0] P{k}.ff9mesh": "b" * 64 for k in range(40)},
              "dir": f"history/{i:04d}"} for i in range(n_steps)]
    D._write_history(d, {"steps": steps, "cursor": n_steps, "promoted": 0})
    return d


def part_a(seconds=3.0):
    d = fresh_draft()
    stop, reads = threading.Event(), [0]

    def reader():
        while not stop.is_set():
            D.history(d)
            reads[0] += 1
    t = threading.Thread(target=reader, daemon=True)
    t.start()
    h = D.history(d)
    ok = refused = 0
    first = None
    end = time.time() + seconds
    while time.time() < end:
        try:
            D._write_history(d, h)
            ok += 1
        except PermissionError as e:
            refused += 1
            first = first or e
    stop.set()
    t.join()
    print(f"A: {ok + refused} _write_history calls while a reader looped D.history ({reads[0]} reads): "
          f"{refused} refused" + (f" -- first: {type(first).__name__}: {first}" if first else ""))


def part_b(trials=60):
    lost = 0
    example = None
    for i in range(trials):
        d = fresh_draft(n_steps=40)
        D.begin_step(d, [(0, 0)])
        (d / "FF9_Data/WorldMap/Disc1/0_1/r0/Block[0][0] Terrain.ff9mesh").write_bytes(b"the accept's bytes" * 4)
        stop = threading.Event()

        def gui_thread():                                 # the window's thread: refresh -> D.history, repeatedly
            while not stop.is_set():
                D.history(d)
        g = threading.Thread(target=gui_thread, daemon=True)
        g.start()
        err = None
        try:
            D.commit_step(d, {"table": "forest", "center": [1.0, -1.0], "donor": "15,15"}, "forest X")
        except Exception as e:                            # noqa: BLE001 -- what StepWorker hands to _recorded
            err = e
        stop.set()
        g.join()
        if err is not None:
            lost += 1
            h = D.history(d)
            example = example or (err, h["cursor"], (d / "history" / "0040").is_dir(),
                                  (d / "FF9_Data/WorldMap/Disc1/0_1/r0/Block[0][0] Terrain.ff9mesh").read_bytes()[:18])
    print(f"B: {trials} real commit_steps with a concurrent D.history reader: {lost} raised")
    if example:
        e, cur, moved, data = example
        print(f"   e.g. {type(e).__name__}: {e}")
        print(f"   history cursor after: {cur} (40 before: the step is not recorded); history/0040 renamed into "
              f"place: {moved}; the draft holds the accept's bytes: {data!r}")


if __name__ == "__main__":
    part_a()
    part_b()
