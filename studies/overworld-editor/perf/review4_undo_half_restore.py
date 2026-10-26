"""Review-4 probe (6bb54f32, 9ed89e54): undo's _restore is not whole or nothing -- it writes the step's cells back file
by file and raises at the first file the disk refuses, the cursor unmoved. begin_edit's new rollback redoes the steps
it undid and assumes the half-undone one is untouched; the bar's new OSError branch says "Not undone".

The refusal is real: a reader holds open a file the step CREATED (Python open(): Windows refuses the unlink while it
is open), for the whole of _retry's 3 s.

Part 1: begin_edit(0) over [forest A at (0,0); B at (0,0)+(1,0), writing A's block again and creating an Object file
at (1,0); C at (0,0)]. Undo C goes through; undo B writes (0,0) back, then the unlink of B's Object is refused. The
rollback's redo of C refuses ((0,0) is no longer C's before), so the open raises -- with C undone, B half undone and
the history calling B applied.
Part 2: the bar's Undo of the same B: "Not undone: ..." over a half undo.

Hermetic: studies/overworld-editor/out/perf/review4/undo_half_restore/.
Run: py studies/overworld-editor/perf/review4_undo_half_restore.py   (from the worktree root)"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
WT = HERE.parents[3]
sys.path.insert(0, str(WT / "ff9mapkit"))
from ff9mapkit.world import draft as D  # noqa: E402

assert Path(D.__file__).resolve().is_relative_to(WT), D.__file__
OUT = WT / "studies" / "overworld-editor" / "out" / "perf" / "review4" / "undo_half_restore"
ROW = {"table": "forest", "center": [1.0, -1.0], "donor": "15,15"}
T00 = "FF9_Data/WorldMap/Disc1/0_1/r0/Block[0][0] Terrain.ff9mesh"
O10 = "FF9_Data/WorldMap/Disc1/0_1/r0/Block[1][0] Object.ff9mesh"


def _fresh(name):
    game = OUT / name / "GAME"
    src = game / "Src"
    row = src / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / "r0"
    row.mkdir(parents=True)
    for bx in range(2):
        (row / f"Block[{bx}][0] Terrain.ff9mesh").write_bytes(b"stock %d" % bx)
    return game, D.ensure_draft(src, game=game, root=OUT / name / "drafts")


def _step(d, cells, writes, label):
    D.begin_step(d, cells)
    for rel, data in writes.items():
        (d / rel).write_bytes(data)
    D.commit_step(d, ROW, label)


def _state(d, tag):
    h = D.history(d)
    print(f"  [{tag}] (0,0)={(d / T00).read_bytes()!r} Object(1,0) exists={(d / O10).is_file()} | cursor "
          f"{h['cursor']} of {[s['label'] for s in h['steps']]}")


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    print("PART 1: begin_edit's rollback over a half undo")
    game, d = _fresh("edit")
    _step(d, [(0, 0)], {T00: b"A"}, "A")
    _step(d, [(0, 0), (1, 0)], {T00: b"B", O10: b"B's object"}, "B")
    _step(d, [(0, 0)], {T00: b"C"}, "C")
    _state(d, "before the Edit")
    held = open(d / O10, "rb")
    try:
        D.begin_edit(d, 0)
        print("  begin_edit went through (unexpected)")
    except (ValueError, OSError) as e:
        print(f"  begin_edit raised {type(e).__name__}: {e}")
        print(f"    (during: {type(e.__context__).__name__}: {e.__context__})")
        print(f"  the bar says: Not opened: {e}.")
    finally:
        held.close()
    _state(d, "after the failed open, handle gone")
    for name, fn in (("Undo", D.undo), ("Redo", D.redo)):
        try:
            print(f"  {name}: went through: {fn(d)['label']}")
        except ValueError as e:
            print(f"  {name}: {e}")
    print(f"  a Promote (the C19 chain's _closed -> _repromote) would write: "
          f"{D.promote(d, game=game, dry_run=True, log=lambda *a: None)['promoted']}")

    print("PART 2: the bar's Undo over a half undo")
    game, d = _fresh("undo")
    _step(d, [(0, 0)], {T00: b"A"}, "A")
    _step(d, [(0, 0), (1, 0)], {T00: b"B", O10: b"B's object"}, "B")
    held = open(d / O10, "rb")
    try:
        D.undo(d)
        print("  undo went through (unexpected)")
    except OSError as e:
        print(f"  the bar says: Not undone: {e}.")
    finally:
        held.close()
    _state(d, "after 'Not undone', handle gone")
    try:
        D.undo(d)
        print("  the next Undo went through")
    except ValueError as e:
        print(f"  the next Undo: {e}")

    print("PART 3: the bar's Undo while a reader holds history.json (the bytes move, the history write is refused)")
    game, d = _fresh("undo_history")
    _step(d, [(0, 0)], {T00: b"A"}, "A")
    held = open(d / D.HISTORY, "rb")
    try:
        D.undo(d)
        print("  undo went through (unexpected)")
    except OSError as e:
        print(f"  the bar says: Not undone: {e}.")
    finally:
        held.close()
    _state(d, "after 'Not undone', handle gone")
    for name, fn in (("Undo", D.undo), ("Redo", D.redo)):
        try:
            print(f"  {name}: went through: {fn(d)['label']}")
        except ValueError as e:
            print(f"  {name}: {e}")


if __name__ == "__main__":
    main()
