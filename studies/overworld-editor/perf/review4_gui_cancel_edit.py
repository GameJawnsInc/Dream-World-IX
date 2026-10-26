"""Review-4 probe, the World tab itself (WorldDoc + RecipeBar + the forest card, offscreen, the tests' in-process
runner and two synthetic islands): an edit of step 1 of a two-row recipe, then the card's Cancel edit while a reader
holds a file in step 2's parked folder (a real Windows refusal of cancel_edit's un-retried rename). RecipeBar.cancel_edit
catches ValueError only: the PermissionError leaves the click after the bar already dropped its edit, and the bar's own
next refresh() runs draft.cancel_edit again on the "edit this Workspace did not open" -- which deletes step 1's record.

Run from ff9mapkit/:
  py -m pytest ../studies/overworld-editor/perf/review4_gui_cancel_edit.py -q -s -p no:cacheprovider
      --basetemp=../studies/overworld-editor/out/perf/review4/gui_cancel_edit"""
from __future__ import annotations

import sys

from ff9mapkit.world import draft as D
from ff9mapkit.world import recipe as RC
from tests.test_world_forestedit import _no_real_install  # noqa: F401
from tests.test_worldrecipe import _doc, _tree, _two_islands, app  # noqa: F401


def test_cancel_edit_the_disk_refuses(monkeypatch, tmp_path, app):  # noqa: F811
    game = _two_islands(monkeypatch, tmp_path)
    saved = tmp_path / "two.toml"
    saved.write_text(RC.dumps([{"table": "forest", "center": [26.0, -26.0], "donor": "15,15"},
                               {"table": "mountain", "center": [90.0, -26.0], "donor": "0,0"}]), encoding="utf-8")
    doc, _run = _doc(app, game, tmp_path, saved)
    doc.set_view_mode("3d", sync=True)
    doc._recipe.open_btn.click()
    draft = tmp_path / "drafts" / "FF9CustomMap-world.draft"
    composed = _tree(draft)
    assert D.history(draft)["cursor"] == 2
    bar = doc._recipe
    bar.select(0)
    bar.edit_btn.click()                                                  # Edit step 1: both steps lifted
    tool = doc._forest
    assert tool is not None and tool.editing() and D.history(draft)["edit"], bar.status_lbl.text()
    raised = []
    monkeypatch.setattr(sys, "excepthook", lambda *a: raised.append(a[1]))
    held = open(draft / D.HISTORY_DIR / D.EDIT_DIR / "0001" / "step.json", "rb")
    try:
        tool.close_btn.click()                                            # Cancel edit
    finally:
        held.close()
    h = D.history(draft)
    print("\nafter Cancel edit: raised", [type(e).__name__ for e in raised], "| card editing:", tool.editing(),
          "| card visible:", not tool.isHidden(), "| bar holds an edit:", bar._edit is not None,
          "| draft edit open:", bool(h["edit"]), "| bar says:", bar.status_lbl.text())
    raised.clear()
    try:
        bar.refresh()                                                     # any later redraw of the bar
        print("refresh went through")
    except Exception as e:                                                # noqa: BLE001
        print("refresh raised", type(e).__name__, e)
    h = D.history(draft)
    print("after refresh: draft edit open:", bool(h["edit"]), "| lifted records on disk:",
          [(s["label"], (draft / s["dir"]).is_dir() or (draft / s["home"]).is_dir()) for s in (h["edit"] or {}).get("lifted", [])],
          "| cursor", h["cursor"], "| draft == composed:", _tree(draft) == composed)
