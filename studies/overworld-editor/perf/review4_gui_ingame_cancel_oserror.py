"""Review-4 probe (1fd9d1fa's refused take-back + 9ed89e54's missed sibling), the World tab itself: an edit of a step
that is IN THE GAME (the C19 chain reverted its promote), its Accept's commit refused and the take-back refused too --
the card then says "the next step, Undo, Redo or Promote takes it back first". In an edit Undo and Redo are hidden and
Promote waits for the edit; the user clicks Cancel edit. draft.cancel_edit's own abort_step raises the same OSError,
and RecipeBar.cancel_edit catches ValueError only: the bar has already dropped its edit, _closed (the promote back) never
runs, the card stays up out of edit mode, and the game is left with the recipe's promote taken out of it.

The refusals are monkeypatched as the round-3 H3 test does (commit_step raises; abort_step raises while a pending step
exists). Run from ff9mapkit/:
  py -m pytest ../studies/overworld-editor/perf/review4_gui_ingame_cancel_oserror.py -q -s -p no:cacheprovider
      --basetemp=../studies/overworld-editor/out/perf/review4/gui_ingame_cancel"""
from __future__ import annotations

import sys
from pathlib import Path

from ff9mapkit.world import draft as D
from tests.test_world_forestedit import _no_real_install  # noqa: F401
from tests.test_worldedit import _hit, _promoted
from tests.test_worldrecipe import _tree, app  # noqa: F401


def test_in_game_cancel_edit_over_a_refused_take_back(monkeypatch, tmp_path, app):  # noqa: F811
    game, doc, run, draft, live0 = _promoted(app, monkeypatch, tmp_path)
    bar = doc._recipe
    bar._ask = lambda title, text: True
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    bar.edit_btn.click()                                                  # the chain: revert, then the edit opens
    forest = doc._forest
    assert forest.editing() and D.promote_owed(draft) == 3 and D.history(draft)["promoted"] == 0
    forest.drop_at(30.0, -30.0)
    forest._timer.stop()
    forest._check()
    assert forest.accept_btn.isEnabled(), forest.verdict_lbl.text()
    real_abort = D.abort_step

    def abort_fails(d):
        if (Path(d) / D.HISTORY_DIR / D._PENDING / "step.json").is_file():
            raise PermissionError(13, "a reader holds it")
        return real_abort(d)
    monkeypatch.setattr(D, "commit_step", lambda *a, **k: (_ for _ in ()).throw(PermissionError(5, "a handle is open")))
    monkeypatch.setattr(D, "abort_step", abort_fails)
    forest.accept_btn.click()                                             # Accept the edit
    print("\nCARD after Accept:", forest.verdict_lbl.text())
    print("bar buttons visible: Undo", bar.undo_btn.isVisible(), "Redo", bar.redo_btn.isVisible(),
          "| card editing:", forest.editing())
    raised = []
    monkeypatch.setattr(sys, "excepthook", lambda *a: raised.append(a[1]))
    n = len(run.argvs)
    forest.close_btn.click()                                              # Cancel edit
    h = D.history(draft)
    print("after Cancel edit: raised", [f"{type(e).__name__}: {e}" for e in raised])
    print("  bar holds an edit:", bar._edit is not None, "| bar says:", bar.status_lbl.text())
    print("  card visible:", not forest.isHidden(), "| card editing:", forest.editing())
    print("  draft: edit open", bool(h["edit"]), "| promoted", h["promoted"], "| owed", D.promote_owed(draft))
    print("  jobs after the click:", [a[5:7] for a in run.argvs[n:]])
    print("  live folder as before the chain:", _tree(game / "FF9CustomMap-world") == live0)
    monkeypatch.setattr(D, "abort_step", real_abort)                      # the handle goes
    bar.refresh()
    print("after the handle goes and the bar redraws: edit open", bool(D.history(draft)["edit"]),
          "| live folder as before the chain:", _tree(game / "FF9CustomMap-world") == live0,
          "| bar says:", bar.status_lbl.text())
