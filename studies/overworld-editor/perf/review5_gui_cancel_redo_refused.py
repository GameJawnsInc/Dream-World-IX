"""Review-5 probe (5ae20d55 R4-2 + 19a7f90b R4-3 + 62c46571 R4-4), the World tab itself (WorldDoc + RecipeBar + the
forest card, offscreen, the tests' in-process runner and two synthetic islands).

A two-row recipe [forest (0,0), mountain (1,0)]; Edit step 1 (the forest): both steps lifted, applied 2. The card's
Cancel edit: the cancel moves the lifted folders home, writes the history with the edit CLOSED, then redoes the
applied steps. The second redo's history write is refused (a reader holds history.json open through it: the real
Windows refusal of the replace that _write_history waits out for 3 s); R4-3's _step_to puts the mountain back as it
was and raises. The edit is closed on disk already, so neither a second cancel nor the bar's refresh runs it again
(R4-2 / R4-4's 'runs again and finishes'): the mountain stays undone, and the bar says the edit could not be undone.

Run from ff9mapkit/:
  py -m pytest ../studies/overworld-editor/perf/review5_gui_cancel_redo_refused.py -q -s -p no:cacheprovider
      --basetemp=../studies/overworld-editor/out/perf/review5/gui_cancel_redo_refused"""
from __future__ import annotations

from pathlib import Path

from ff9mapkit.world import draft as D
from ff9mapkit.world import recipe as RC
from tests.test_world_forestedit import _no_real_install  # noqa: F401
from tests.test_worldrecipe import _doc, _tree, _two_islands, app  # noqa: F401


def test_cancel_whose_redo_is_refused(monkeypatch, tmp_path, app):  # noqa: F811
    game = _two_islands(monkeypatch, tmp_path)
    saved = tmp_path / "two.toml"
    saved.write_text(RC.dumps([{"table": "forest", "center": [26.0, -26.0], "donor": "15,15"},
                               {"table": "mountain", "center": [90.0, -26.0], "donor": "0,0"}]), encoding="utf-8")
    doc, _run = _doc(app, game, tmp_path, saved)
    doc.set_view_mode("3d", sync=True)
    draft = tmp_path / "drafts" / "FF9CustomMap-world.draft"
    doc._recipe.open_btn.click()
    composed = _tree(draft)
    bar = doc._recipe
    bar.select(0)
    bar.edit_btn.click()                                                  # Edit step 1: both lifted
    tool = doc._forest
    assert tool.editing() and D.history(draft)["edit"]["applied"] == 2
    real, calls = D.redo, []

    def redo(d):                                                          # a reader on history.json through redo 2
        calls.append(1)
        if len(calls) != 2:
            return real(d)
        held = open(Path(d) / D.HISTORY, "rb")
        try:
            return real(d)
        finally:
            held.close()
    monkeypatch.setattr(D, "redo", redo)
    tool.close_btn.click()                                                # Cancel edit
    monkeypatch.setattr(D, "redo", real)
    h = D.history(draft)
    print(f"\n[after Cancel edit] edit open: {bool(h['edit'])} | cursor {h['cursor']} of "
          f"{[s['label'] for s in h['steps']]} | draft == the recipe as it was: {_tree(draft) == composed}"
          f"\n   bar says: {bar.status_lbl.text()[:140]!r}")
    bar.refresh()                                                         # R4-4: 'closed once the disk lets it'
    h = D.history(draft)
    print(f"[after a refresh, the reader gone] edit open: {bool(h['edit'])} | cursor {h['cursor']} | draft == as it "
          f"was: {_tree(draft) == composed} | bar: {bar.status_lbl.text()!r}")
    try:
        D.cancel_edit(draft)                                              # R4-2: 'a cancel run again finishes'
    except ValueError as e:
        print("[cancel run again]", e)
