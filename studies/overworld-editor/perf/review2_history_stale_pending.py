"""Review-2 probe (history slice, f8ca4c76): begin_step now aborts a pending step left by an abort that failed. The
pending's before-images were taken when THAT step began; an Undo (or a Redo) run in between rewrites files at its
cells, and the delayed abort writes the stale before-images back over them -- the undone step's bytes return to the
draft while the history says it is undone.

Hermetic: a fake game root and drafts root under studies/overworld-editor/out/perf/review2/history/stale_pending/.
The real draft.py (worktree package asserted). The failed abort is a real Windows refusal: a reader holds a file
the half step ADDED (the 3D view reading the draft), so abort's unlink is refused; _retry is cut to one try for
that call only (the reader would otherwise just have to outlast 3 s)."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
WT = HERE.parents[3]
sys.path.insert(0, str(WT / "ff9mapkit"))
from ff9mapkit.world import draft as D  # noqa: E402

assert Path(D.__file__).resolve().is_relative_to(WT), D.__file__
OUT = WT / "studies" / "overworld-editor" / "out" / "perf" / "review2" / "history" / "stale_pending"
T00 = "FF9_Data/WorldMap/Disc1/0_1/r0/Block[0][0] Terrain.ff9mesh"
O00 = "FF9_Data/WorldMap/Disc1/0_1/r0/Block[0][0] Object.ff9mesh"
T10 = "FF9_Data/WorldMap/Disc1/0_1/r0/Block[1][0] Terrain.ff9mesh"
ROW = {"table": "forest", "center": [1.0, -1.0], "donor": "15,15"}


def setup():
    if OUT.exists():
        shutil.rmtree(OUT)
    game = OUT / "GAME"
    src = game / "FF9CustomMap-world"
    for disc in (1, 4):
        row = src / "FF9_Data" / "WorldMap" / f"Disc{disc}" / "0_1" / "r0"
        row.mkdir(parents=True)
        for bx in range(2):
            (row / f"Block[{bx}][0] Terrain.ff9mesh").write_bytes(b"stock %d" % bx)
    return D.ensure_draft(src, game=game, root=OUT / "drafts")


def main():
    d = setup()
    stock10 = (d / T10).read_bytes()
    # step 1: a mountain at block (1,0)
    D.begin_step(d, [(1, 0)])
    (d / T10).write_bytes(b"mountain")
    D.commit_step(d, ROW, "mountain one")
    # step 2: a card's Accept snapshots a superset (blocks (0,0) and (1,0)); the verb half writes and fails
    D.begin_step(d, [(0, 0), (1, 0)])
    (d / T00).write_bytes(b"half a forest")
    (d / O00).write_bytes(b"its new object")            # a file the half step added
    held = open(d / O00, "rb")                          # the 3D view reads it
    real_retry = D._retry
    D._retry = lambda fn, **k: fn()
    try:
        D.abort_step(d)
        print("abort did not fail (unexpected)")
    except PermissionError as e:
        print("abort failed as F2 assumes:", e)
    finally:
        D._retry = real_retry
        held.close()
    # the user clicks Undo in the bar (enabled: no card is writing)
    s = D.undo(d)
    print("undo:", s["label"], "| T10 now", (d / T10).read_bytes(), "| cursor", D.history(d)["cursor"])
    # the next Accept begins
    D.begin_step(d, [(0, 0)])
    D.abort_step(d)
    h = D.history(d)
    print("after the next begin_step: T10 =", (d / T10).read_bytes(), "| cursor", h["cursor"],
          "| steps", [x["label"] for x in h["steps"]])
    print("T10 is stock again (history exact)?", (d / T10).read_bytes() == stock10)
    try:
        D.redo(d)
        print("redo ran")
    except ValueError as e:
        print("redo refuses:", e)
    print("edits the draft would promote:", D.edits(d))


if __name__ == "__main__":
    main()
