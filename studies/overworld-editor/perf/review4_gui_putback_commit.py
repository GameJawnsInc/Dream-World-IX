"""Review-4 probe (1fd9d1fa's scope): the round-3 H3 take-back covers the card's Accept and the opened recipe's rows,
not an edit's put-back. Edit step 1 of a two-row recipe and Accept it; the put-back of step 2 (composed again by
world-fuse) has its commit refused. _put_back_done calls commit_step on the window's thread with no guard: the error
leaves the job's done, the pending step stays whole, and the bar keeps saying the steps are going back on top.

Run from ff9mapkit/:
  py -m pytest ../studies/overworld-editor/perf/review4_gui_putback_commit.py -q -s -p no:cacheprovider
      --basetemp=../studies/overworld-editor/out/perf/review4/gui_putback_commit"""
from __future__ import annotations

import sys

from ff9mapkit.world import draft as D
from ff9mapkit.world import recipe as RC
from tests.test_world_forestedit import _no_real_install  # noqa: F401
from tests.test_worldrecipe import _doc, _two_islands, app  # noqa: F401


def test_a_put_back_whose_commit_is_refused(monkeypatch, tmp_path, app):  # noqa: F811
    game = _two_islands(monkeypatch, tmp_path)
    saved = tmp_path / "two.toml"
    saved.write_text(RC.dumps([{"table": "forest", "center": [26.0, -26.0], "donor": "15,15"},
                               {"table": "mountain", "center": [90.0, -26.0], "donor": "0,0"}]), encoding="utf-8")
    doc, run = _doc(app, game, tmp_path, saved)
    doc.set_view_mode("3d", sync=True)
    doc._recipe.open_btn.click()
    draft = tmp_path / "drafts" / "FF9CustomMap-world.draft"
    bar = doc._recipe
    bar.select(0)
    bar.edit_btn.click()
    forest = doc._forest
    assert forest.editing()
    forest.drop_at(30.0, -30.0)
    forest._timer.stop()
    forest._check()
    assert forest.accept_btn.isEnabled(), forest.verdict_lbl.text()
    real, calls = D.commit_step, []

    def second_fails(*a, **k):
        calls.append(1)
        if len(calls) == 2:                                           # the put-back's commit (or its replay's)
            raise PermissionError(5, "a handle is open")
        return real(*a, **k)
    monkeypatch.setattr(D, "commit_step", second_fails)
    raised = []
    monkeypatch.setattr(sys, "excepthook", lambda *a: raised.append(a[1]))
    forest.accept_btn.click()
    h = D.history(draft)
    print("\nraised:", [f"{type(e).__name__}: {e}" for e in raised], "| commits tried:", len(calls))
    print("BAR:", bar.status_lbl.text(), "| bar edit open:", bar._edit is not None, "| runner busy:", run.busy())
    print("draft: cursor", h["cursor"], [s["label"] for s in h["steps"]], "| edit open:", bool(h["edit"]),
          "| pending whole:", (draft / D.HISTORY_DIR / D._PENDING / "step.json").is_file())
