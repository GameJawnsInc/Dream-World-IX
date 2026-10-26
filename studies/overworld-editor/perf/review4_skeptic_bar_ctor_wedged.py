"""Review-4 skeptic probe (R4-2's reach): after review4_cancel_edit_rename.py has wedged its draft (a lifted record
deleted, the edit open, no promote owed), does a FRESH RecipeBar -- the World tab's next launch on that folder -- even
construct? Its __init__ ends in refresh(), which re-runs draft.cancel_edit on "an edit this Workspace did not open".

Run review4_cancel_edit_rename.py first, then (from the worktree root):
  py studies/overworld-editor/perf/review4_skeptic_bar_ctor_wedged.py"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = Path(__file__).resolve()
WT = HERE.parents[3]
sys.path.insert(0, str(WT / "ff9mapkit"))
from PySide6.QtWidgets import QApplication  # noqa: E402

from ff9mapkit.world import draft as D  # noqa: E402

assert Path(D.__file__).resolve().is_relative_to(WT), D.__file__
OUT = WT / "studies" / "overworld-editor" / "out" / "perf" / "review4" / "cancel_edit_rename"


def main():
    app = QApplication.instance() or QApplication([])  # noqa: F841
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldrecipe import RecipeBar
    game, src = OUT / "GAME", OUT / "GAME" / "Src"
    d = D.draft_path(src, root=OUT / "drafts")
    h = D.history(d)
    print(f"draft {d.name}: is_draft {D.is_draft(d)} | edit open {bool(h['edit'])} | owed {D.promote_owed(d)}")
    for attempt in (1, 2):
        try:
            RecipeBar(pick_palette("dark"), game_fn=lambda: game, source_fn=lambda: src,
                      drafts_root=OUT / "drafts", ask=lambda t, x: True)
            print(f"launch #{attempt}: the RecipeBar was built")
        except Exception as e:                                   # noqa: BLE001
            print(f"launch #{attempt}: RecipeBar() raised {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
