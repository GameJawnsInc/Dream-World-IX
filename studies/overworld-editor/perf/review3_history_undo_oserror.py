"""Review-3 probe (history slice, 972cab25): Undo and Redo now finish a pending abort first, so they raise what that
abort raises -- an OSError (a reader still holding a file the failed step created) -- where they raised ValueError
only before. 7efe9a47 widened Edit's and Delete's catch to OSError for exactly this; RecipeBar.undo / redo still catch
ValueError only: the click raises out of the slot after the abort's 3 s _retry, and the bar says nothing.

Drives the REAL RecipeBar (offscreen Qt). Hermetic: fake game + drafts under
studies/overworld-editor/out/perf/review3/undo_oserror/. The refusal is a real Windows one (a held read handle)."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = Path(__file__).resolve()
WT = HERE.parents[3]
sys.path.insert(0, str(WT / "ff9mapkit"))
from ff9mapkit.world import draft as D  # noqa: E402

assert Path(D.__file__).resolve().is_relative_to(WT), D.__file__
OUT = WT / "studies" / "overworld-editor" / "out" / "perf" / "review3" / "undo_oserror"
ROW = {"table": "forest", "center": [1.0, -1.0], "donor": "15,15"}
T00 = "FF9_Data/WorldMap/Disc1/0_1/r0/Block[0][0] Terrain.ff9mesh"
O10 = "FF9_Data/WorldMap/Disc1/0_1/r0/Block[1][0] Object.ff9mesh"


class NoJobs:
    def start(self, *a):
        raise AssertionError("no job expected")

    def kill(self):
        pass

    def busy(self):
        return False


def main():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])  # noqa: F841
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldrecipe import RecipeBar
    if OUT.exists():
        shutil.rmtree(OUT)
    game = OUT / "GAME"
    src = game / "Src"
    row = src / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / "r0"
    row.mkdir(parents=True)
    for bx in range(2):
        (row / f"Block[{bx}][0] Terrain.ff9mesh").write_bytes(b"stock %d" % bx)
    drafts = OUT / "drafts"
    d = D.ensure_draft(src, game=game, root=drafts)
    D.begin_step(d, [(0, 0)])
    (d / T00).write_bytes(b"A")
    D.commit_step(d, ROW, "forest A")
    D.begin_step(d, [(1, 0)])                                    # a step that made a file, then refused...
    (d / O10).write_bytes(b"half")
    held = open(d / O10, "rb")                                   # ...and a reader holds that file
    try:
        try:
            D.abort_step(d)
        except OSError as e:
            print("the card's abort failed:", type(e).__name__, "-> 'taken back when the next step begins'")
        bar = RecipeBar(pick_palette("dark"), game_fn=lambda: game, source_fn=lambda: src, runner=NoJobs(),
                        drafts_root=drafts, ask=lambda *a: True)
        before = bar.status_lbl.text()
        try:
            bar.undo()                                           # the Undo button's slot
            print("undo: returned; bar says:", bar.status_lbl.text())
        except Exception as e:                                   # noqa: BLE001
            print(f"undo: {type(e).__name__} out of the slot ({e.strerror}); bar still says: "
                  f"{bar.status_lbl.text()!r} (was {before!r})")
    finally:
        held.close()


if __name__ == "__main__":
    main()
