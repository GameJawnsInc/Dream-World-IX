"""Review-3 probe (history slice, 2f02a533 + 972cab25): a commit whose rename is still refused after _retry now
leaves its pending step WHOLE, and the next undo, redo, step, edit or promote aborts it -- the accepted write is
taken back. The callers were not told: the card says "The draft was written but its history step was not recorded
(...): Undo cannot take it back." (worldforest.py _recorded), the opened recipe "...Undo cannot take it back."
(worldrecipe.py _row_recorded). The user, told the edit is in the draft, clicks Undo: it takes back the failed step
AND the step before it -- one click, two steps, the second the user never asked to undo (it is redo-able), the first
gone for good.

Hermetic: fake game + drafts under studies/overworld-editor/out/perf/review3/failed_commit_undo/. The refused rename
is a real Windows refusal: a reader holds a before-copy inside pending while commit_step runs."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
WT = HERE.parents[3]
sys.path.insert(0, str(WT / "ff9mapkit"))
from ff9mapkit.world import draft as D  # noqa: E402

assert Path(D.__file__).resolve().is_relative_to(WT), D.__file__
OUT = WT / "studies" / "overworld-editor" / "out" / "perf" / "review3" / "failed_commit_undo"
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
    D.begin_step(d, [(0, 0)])                                    # step A, recorded
    (d / T00).write_bytes(b"A: a forest")
    D.commit_step(d, ROW, "forest A")
    D.begin_step(d, [(1, 0)])                                    # step B: the verb wrote, its verdict is ok...
    (d / T10).write_bytes(b"B: a mountain")
    held = open(d / D.HISTORY_DIR / D._PENDING / "before" / T10, "rb")   # ...a reader inside pending
    try:
        D.commit_step(d, ROW, "mountain B")
        print("commit went through (unexpected)")
    except OSError as e:
        print(f"B's commit refused at the rename: {type(e).__name__}: {e.strerror}")
        print(f"  the card says: The draft was written but its history step was not recorded ({e}): Undo cannot "
              "take it back.")
    finally:
        held.close()
    print(f"draft now: A={(d / T00).read_bytes()!r} B={(d / T10).read_bytes()!r} | history cursor "
          f"{D.history(d)['cursor']} | pending whole: {(d / D.HISTORY_DIR / D._PENDING / 'step.json').is_file()}")
    s = D.undo(d)                                                # one Undo click
    print(f"one Undo -> the bar says 'Undone: {s['label']}.'")
    print(f"draft now: A={(d / T00).read_bytes()!r} B={(d / T10).read_bytes()!r} | history cursor "
          f"{D.history(d)['cursor']} of {len(D.history(d)['steps'])} steps")


if __name__ == "__main__":
    main()
