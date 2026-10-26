"""Review-4 probe (1fd9d1fa on 2f02a533): a commit that fails AFTER its pending rename leaves no pending step, so the
card's / bar's take-back (abort_step) is a no-op that returns cleanly -- and the card then says "the write was taken
back and the draft is as it was" while the write is still in the draft, unrecorded.

The failure is real: a reader holds history.json open (Python open(); Windows refuses the replace while it is open,
the very race _write_history's docstring names). The pending rename goes through (nothing is held in pending), the
trim and step.json go through, then _write_history's replace is refused for its whole retry (3 s).

Hermetic: fake game + draft under studies/overworld-editor/out/perf/review4/commit_after_rename/.
Run: py studies/overworld-editor/perf/review4_commit_after_rename.py   (from the worktree root)"""
from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve()
WT = HERE.parents[3]
sys.path.insert(0, str(WT / "ff9mapkit"))
from ff9mapkit.world import draft as D  # noqa: E402

assert Path(D.__file__).resolve().is_relative_to(WT), D.__file__
OUT = WT / "studies" / "overworld-editor" / "out" / "perf" / "review4" / "commit_after_rename"
ROW = {"table": "forest", "center": [1.0, -1.0], "donor": "15,15"}
T00 = "FF9_Data/WorldMap/Disc1/0_1/r0/Block[0][0] Terrain.ff9mesh"
T10 = "FF9_Data/WorldMap/Disc1/0_1/r0/Block[1][0] Terrain.ff9mesh"


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    game = OUT / "GAME"
    src = game / "Src"
    row = src / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / "r0"
    row.mkdir(parents=True)
    for bx in range(2):
        (row / f"Block[{bx}][0] Terrain.ff9mesh").write_bytes(b"stock %d" % bx)
    d = D.ensure_draft(src, game=game, root=OUT / "drafts")
    D.begin_step(d, [(0, 0)])                                    # step A, recorded: history.json now exists
    (d / T00).write_bytes(b"A: a forest")
    D.commit_step(d, ROW, "forest A")
    D.begin_step(d, [(1, 0)])                                    # step B: the verb wrote, its verdict is ok...
    (d / T10).write_bytes(b"B: a mountain")
    held = open(d / D.HISTORY, "rb")                             # ...and the window's thread is reading the history
    t0 = time.time()
    try:
        D.commit_step(d, ROW, "mountain B")
        print("commit went through (unexpected)")
        return
    except OSError as e:
        err = e
        print(f"B's commit failed after {time.time() - t0:.1f} s: {type(e).__name__}: {e}")
    finally:
        held.close()
    pend = d / D.HISTORY_DIR / D._PENDING
    print(f"pending step left: {(pend / 'step.json').is_file()} | folder history/0001 (not in the history): "
          f"{(d / D.HISTORY_DIR / '0001').is_dir()}")
    try:                                                         # the card's / bar's take-back (round 3, H3)
        D.abort_step(d)
        err2 = None
    except OSError as e:
        err2 = e
    print(f"take-back (abort_step) raised: {err2!r}")
    print("card says: Not written: its history step could not be recorded (%s), so %s" % (
        err, "the write was taken back and the draft is as it was." if err2 is None else "..."))
    print(f"draft now: A={(d / T00).read_bytes()!r} B={(d / T10).read_bytes()!r} | history cursor "
          f"{D.history(d)['cursor']} ({[s['label'] for s in D.history(d)['steps']]})")
    print(f"edits(): {D.edits(d)}")
    plan = D.promote(d, game=game, dry_run=True, log=lambda *a: None)
    print(f"a Promote would write: {plan['promoted']}")
    try:
        D.undo(d)
        print(f"Undo: undid A; draft B={(d / T10).read_bytes()!r} still (no step records it)")
    except ValueError as e:
        print(f"Undo: {e}")


if __name__ == "__main__":
    main()
