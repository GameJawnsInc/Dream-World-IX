"""Review-6 probe, the World tab (WorldDoc + RecipeBar, offscreen, the tests' in-process runner): a Delete of step 1
of three placed steps, its put-back done, and finish_edit's history write refused by the disk (a reader holding
history.json). _put_back does not catch it: the error leaves the slot (sys.excepthook), the bar keeps its edit with
nothing to put back. Its only offered way on -- Cancel edit -- or simply the next launch (the refresh's automatic
cancel of an edit the Workspace did not open) then destroys every step from the deleted one on.

Run from ff9mapkit/:
  py -m pytest ../studies/overworld-editor/perf/review6_gui_finish_edit_refused.py -q -s -p no:cacheprovider
      --basetemp=../studies/overworld-editor/out/perf/review6/gui_finish_edit_refused"""
from __future__ import annotations

import sys

from ff9mapkit.world import draft as D
from tests.test_world_forestedit import _no_real_install  # noqa: F401
from tests.test_worldedit import _hit, _placed
from tests.test_worldrecipe import _doc, _tree, app  # noqa: F401


def _h(draft):
    h = D.history(draft)
    return f"cursor {h['cursor']} of {[s['label'] for s in h['steps']]}, edit open {bool(h['edit'])}"


def _arm(monkeypatch):
    real_finish, real_write = D.finish_edit, D._write_history

    def finish(d):
        monkeypatch.setattr(D, "_write_history",
                            lambda *a: (_ for _ in ()).throw(PermissionError(13, "a reader holds history.json")))
        try:
            return real_finish(d)
        finally:
            monkeypatch.setattr(D, "_write_history", real_write)
    monkeypatch.setattr(D, "finish_edit", finish)
    return real_finish


def test_a_delete_whose_close_is_refused_then_the_next_launch(monkeypatch, tmp_path, app):  # noqa: F811
    game, doc, run, draft = _placed(app, monkeypatch, tmp_path)
    bar = doc._recipe
    raised = []
    monkeypatch.setattr(sys, "excepthook", lambda *a: raised.append(a[1]))
    print(f"\n[placed] {_h(draft)}")
    real_finish = _arm(monkeypatch)
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    bar.delete_btn.click()                                                 # Delete step 1: its 2 steps go back on
    monkeypatch.setattr(D, "finish_edit", real_finish)
    print(f"[Delete, its close refused] raised out of the slot: {raised!r}\n   {_h(draft)}"
          f"\n   bar: edit kept {bar._edit is not None}, holding {bar.holding()}, Cancel edit shown "
          f"{not bar.cancel_btn.isHidden()}\n   bar says: {bar.status_lbl.text()!r}")
    after_delete = _tree(draft)
    doc2, _run2 = _doc(app, game, tmp_path, tmp_path / "saved.toml")      # the next launch, on the same draft
    doc2.set_view_mode("3d", sync=True)
    print(f"[the next launch] {_h(draft)}\n   draft == the recipe as deleted: {_tree(draft) == after_delete}"
          f"\n   bar says: {doc2._recipe.status_lbl.text()!r}")


def test_a_delete_whose_close_is_refused_then_cancel_edit(monkeypatch, tmp_path, app):  # noqa: F811
    game, doc, run, draft = _placed(app, monkeypatch, tmp_path)
    bar = doc._recipe
    monkeypatch.setattr(sys, "excepthook", lambda *a: None)
    real_finish = _arm(monkeypatch)
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    bar.delete_btn.click()
    monkeypatch.setattr(D, "finish_edit", real_finish)
    bar.cancel_btn.click()                                                 # the bar's own way on
    print(f"\n[Cancel edit after the refused close] {_h(draft)}\n   bar: holding {bar.holding()}, Cancel edit shown "
          f"{not bar.cancel_btn.isHidden()}\n   bar says: {bar.status_lbl.text()!r}")
