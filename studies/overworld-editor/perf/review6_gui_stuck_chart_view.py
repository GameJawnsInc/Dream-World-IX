"""Review-6 probe (3eb33114 R5-1): the held draft in the chart view. An in-game step's edit is open; the user clicks
Chart view, which closes the cards -- the edit card's close cancels the edit, and the disk refuses it (a reader in
the lifted step's parked folder). The bar holds the draft (stuck), but the chart view hides the bar and its Cancel
edit; the folder box and Rescan stay disabled, their tooltip pointing at the recipe bar.

Run from ff9mapkit/:
  py -m pytest ../studies/overworld-editor/perf/review6_gui_stuck_chart_view.py -q -s -p no:cacheprovider
      --basetemp=../studies/overworld-editor/out/perf/review6/gui_stuck_chart_view"""
from __future__ import annotations

from ff9mapkit.world import draft as D
from tests.test_world_forestedit import _no_real_install  # noqa: F401
from tests.test_worldedit import _hit, _promoted
from tests.test_worldrecipe import _tree, app  # noqa: F401


def test_stuck_in_the_chart_view(monkeypatch, tmp_path, app):  # noqa: F811
    game, doc, run, draft, live0 = _promoted(app, monkeypatch, tmp_path)
    bar = doc._recipe
    bar._ask = lambda title, text: True
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    bar.edit_btn.click()
    assert doc._forest.editing()
    held = open(draft / D.HISTORY_DIR / D.EDIT_DIR / "0000" / "step.json", "rb")
    try:
        doc.set_view_mode("chart", sync=True)                              # the view toggle closes the cards
        print(f"\n[chart view, the cancel refused] edit open {bool(D.history(draft)['edit'])}, owed "
              f"{D.promote_owed(draft)}, live as before {_tree(game / 'FF9CustomMap-world') == live0}"
              f"\n   bar: stuck {bar._stuck is not None}, visible {bar.isVisibleTo(doc)}, Cancel edit visible "
              f"{bar.cancel_btn.isVisibleTo(doc)}"
              f"\n   folder box enabled {doc.folder_box.isEnabled()}, Rescan enabled {doc.rescan_btn.isEnabled()}"
              f"\n   folder box tooltip: {doc.folder_box.toolTip()!r}")
    finally:
        held.close()
    doc.set_view_mode("3d", sync=True)                                     # back: settle() retries it
    h = D.history(draft)
    print(f"[3D again] edit open {bool(h['edit'])}, promoted {h['promoted']}, live as before "
          f"{_tree(game / 'FF9CustomMap-world') == live0}\n   bar says: {bar.status_lbl.text()!r}")


def test_the_workspace_closing_while_stuck(monkeypatch, tmp_path, app):  # noqa: F811
    """The same refused cancel (the card's own Cancel edit this time); the reader then goes and the Workspace closes.
    shutdown's close_in_game_edit looks at _edit only, so the held in-game edit is not tried again: the window goes
    with the game's promote still taken out, and the held bar never said the game lacks it."""
    game, doc, run, draft, live0 = _promoted(app, monkeypatch, tmp_path)
    bar = doc._recipe
    bar._ask = lambda title, text: True
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    bar.edit_btn.click()
    held = open(draft / D.HISTORY_DIR / D.EDIT_DIR / "0000" / "step.json", "rb")
    try:
        doc._forest.close_btn.click()
    finally:
        held.close()
    said = bar.status_lbl.text()
    doc.shutdown()                                                          # the reader is gone by now
    print(f"\n[closed while stuck] edit open {bool(D.history(draft)['edit'])}, owed {D.promote_owed(draft)}, live "
          f"as before {_tree(game / 'FF9CustomMap-world') == live0}\n   the bar said before it closed: {said!r}")
