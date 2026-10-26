"""Review-6 probe (3eb33114 R5-1): a scan that lands under an open in-game edit (the race the suite already pins in
test_a_scan_that_lands_under_an_open_edit_cancels_it_in_its_own_folder) whose cancel the disk refuses -- a reader
holding a file in the lifted step's parked folder (the real Windows refusal: a directory rename with a handle open
inside it).

The card closes, the bar's cancel_edit goes to the edit's own draft and is refused, so _hold_stuck sets _stuck to
that draft -- and its own refresh() at once clears it, because the tab now shows another folder. The edit stays open
in FF9CustomMap-world's draft, the game stays with its promote taken out (owed on disk), and the bar says nothing:
it shows Hand's status in its plain state.

Run from ff9mapkit/:
  py -m pytest ../studies/overworld-editor/perf/review6_gui_scan_refused_cancel.py -q -s -p no:cacheprovider
      --basetemp=../studies/overworld-editor/out/perf/review6/gui_scan_refused_cancel"""
from __future__ import annotations

from ff9mapkit.world import draft as D
from tests.test_world_forestedit import _no_real_install  # noqa: F401
from tests.test_worldedit import _hit, _promoted
from tests.test_worldrecipe import _tree, app  # noqa: F401


def test_scan_lands_on_a_refused_cancel(monkeypatch, tmp_path, app):  # noqa: F811
    from ff9mapkit.workspace import worldscan
    game, doc, run, draft, live0 = _promoted(app, monkeypatch, tmp_path)
    bar = doc._recipe
    bar._ask = lambda title, text: True
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    bar.edit_btn.click()                                                   # in-game step 1: reverted, edit open
    assert doc._forest.editing() and D.history(draft)["edit"]
    held = open(draft / D.HISTORY_DIR / D.EDIT_DIR / "0000" / "step.json", "rb")   # a reader in the parked folder
    try:
        doc._finish(worldscan.scan_tree(game / "Hand"), None, None)       # a scan begun before the Edit lands
        h = D.history(draft)
        print(f"\n[scan landed, cancel refused] tab shows: {doc._census.root.name}"
              f"\n   FF9CustomMap-world draft: edit open {bool(h['edit'])}, cursor {h['cursor']}, promoted "
              f"{h['promoted']}, promote owed {D.promote_owed(draft)}"
              f"\n   live folder == before the edit: {_tree(game / 'FF9CustomMap-world') == live0}"
              f"\n   bar: _stuck {bar._stuck}, holding {bar.holding()}, Cancel edit shown "
              f"{not bar.cancel_btn.isHidden()}, state {bar.status_lbl.property('state')!r}"
              f"\n   bar says: {bar.status_lbl.text()!r}"
              f"\n   folder box enabled: {doc.folder_box.isEnabled()}, tools menu enabled: {doc.tools_btn.isEnabled()}")
    finally:
        held.close()
