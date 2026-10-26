"""Review-4 probe (6bb54f32's mirror, cancel_edit from 515711ca5): begin_edit's lift is now retried and rolled back,
but cancel_edit's put-back of the lifted folders is neither -- one rename, no _retry, and a second call deletes the
folder the first call already moved home (rmtree(home) before the rename), then fails on the missing park folder.

The refusal is real, the one 6bb54f32 names ("a handle open in a step's folder"): a reader holds a file inside the
second parked step's folder (Python open(); Windows refuses the directory rename while it is open).

Hermetic: studies/overworld-editor/out/perf/review4/cancel_edit_rename/.
Run: py studies/overworld-editor/perf/review4_cancel_edit_rename.py   (from the worktree root)"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
WT = HERE.parents[3]
sys.path.insert(0, str(WT / "ff9mapkit"))
from ff9mapkit.world import draft as D  # noqa: E402

assert Path(D.__file__).resolve().is_relative_to(WT), D.__file__
OUT = WT / "studies" / "overworld-editor" / "out" / "perf" / "review4" / "cancel_edit_rename"
ROW = {"table": "forest", "center": [1.0, -1.0], "donor": "15,15"}
T00 = "FF9_Data/WorldMap/Disc1/0_1/r0/Block[0][0] Terrain.ff9mesh"
T10 = "FF9_Data/WorldMap/Disc1/0_1/r0/Block[1][0] Terrain.ff9mesh"


def _step(d, cells, writes, label):
    D.begin_step(d, cells)
    for rel, data in writes.items():
        (d / rel).write_bytes(data)
    D.commit_step(d, ROW, label)


def _state(d, tag):
    h = D.history(d)
    e = h["edit"]
    print(f"  [{tag}] (0,0)={(d / T00).read_bytes()!r} (1,0)={(d / T10).read_bytes()!r} | cursor {h['cursor']} of "
          f"{[s['label'] for s in h['steps']]} | edit open: {bool(e)}"
          + (f" | lifted records on disk: {[(s['label'], (d / s['dir']).is_dir() or (d / s['home']).is_dir()) for s in e['lifted']]}"
             if e else ""))


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
    _step(d, [(0, 0)], {T00: b"A"}, "A")
    _step(d, [(1, 0)], {T10: b"B"}, "B")
    D.begin_edit(d, 0)                                           # Edit A: A and B lifted into history/edit/
    _state(d, "edit open")
    held = open(d / D.HISTORY_DIR / D.EDIT_DIR / "0001" / "step.json", "rb")   # a handle in B's parked folder
    try:
        D.cancel_edit(d)                                         # the card's Cancel edit -> bar.cancel_edit
        print("  cancel_edit went through (unexpected)")
    except OSError as e:
        print(f"  cancel_edit #1 raised {type(e).__name__}: {e}")
    finally:
        held.close()
    _state(d, "after #1, handle gone")
    for i in (2, 3):                                             # bar.refresh() runs it again (edit open, bar's _edit None)
        try:
            D.cancel_edit(d)
            print(f"  cancel_edit #{i} went through")
        except (ValueError, OSError) as e:
            print(f"  cancel_edit #{i} raised {type(e).__name__}: {e}")
        _state(d, f"after #{i}")
    for name, fn in (("begin_edit(0)", lambda: D.begin_edit(d, 0)),
                     ("Promote", lambda: D.promote(d, game=game, dry_run=True, log=lambda *a: None))):
        try:
            fn()
            print(f"  {name}: went through")
        except ValueError as e:
            print(f"  {name}: {e}")


if __name__ == "__main__":
    main()
