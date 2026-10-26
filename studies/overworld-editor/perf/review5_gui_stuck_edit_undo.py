"""Review-5 probe (62c46571 R4-4 over 5ae20d55 R4-2), the World tab itself (WorldDoc + RecipeBar + the forest card,
offscreen, the tests' in-process runner and two synthetic islands).

A two-row recipe [mountain (1,0), forest (0,0)]; Edit step 2 (the forest), then the card's Cancel edit while a reader
holds a file in the forest's parked folder (the real Windows refusal R4-2 names: a directory rename with a handle open
inside it). R4-4 now catches the OSError: the bar drops its edit and says "The edit could not be undone", while the
draft's history still holds the edit open (cursor 1, the forest lifted). The bar is idle, so Undo is shown and enabled.
The user clicks Undo once the reader is gone: draft.undo does not refuse an open edit and takes step 1 (the mountain)
out; the bar's own refresh then runs the auto-cancel, which puts the lifted forest back with cursor = edit.at = 1 --
the history now says the mountain is applied, the draft's bytes do not have it.

Run from ff9mapkit/:
  py -m pytest ../studies/overworld-editor/perf/review5_gui_stuck_edit_undo.py -q -s -p no:cacheprovider
      --basetemp=../studies/overworld-editor/out/perf/review5/gui_stuck_edit_undo"""
from __future__ import annotations

import sys
from pathlib import Path

from ff9mapkit.world import draft as D
from ff9mapkit.world import recipe as RC
from tests.test_world_forestedit import _no_real_install  # noqa: F401
from tests.test_worldrecipe import _doc, _tree, _two_islands, app  # noqa: F401


def _say(tag, bar, draft, composed, stock):
    h = D.history(draft)
    t = _tree(draft)
    blocks = sorted({k.split("/")[-1].split(" ")[0] for k in set(t) | set(composed) if t.get(k) != composed.get(k)})
    print(f"\n[{tag}] history: cursor {h['cursor']} of {[s['label'] for s in h['steps']]}, edit open: {bool(h['edit'])}"
          f"\n   draft == composed recipe: {t == composed}; blocks that differ from it: {blocks}"
          f"\n   draft == stock (nothing applied): {t == stock}"
          f"\n   bar: edit held {bar._edit is not None}; Undo visible {bar.undo_btn.isVisibleTo(bar)} enabled "
          f"{bar.undo_btn.isEnabled()}; says: {bar.status_lbl.text()!r}")


def test_stuck_edit_then_undo(monkeypatch, tmp_path, app):  # noqa: F811
    game = _two_islands(monkeypatch, tmp_path)
    saved = tmp_path / "two.toml"
    saved.write_text(RC.dumps([{"table": "mountain", "center": [90.0, -26.0], "donor": "0,0"},
                               {"table": "forest", "center": [26.0, -26.0], "donor": "15,15"}]), encoding="utf-8")
    doc, _run = _doc(app, game, tmp_path, saved)
    doc.set_view_mode("3d", sync=True)
    draft = tmp_path / "drafts" / "FF9CustomMap-world.draft"
    stock = None
    doc._recipe.open_btn.click()
    composed = _tree(draft)
    h = D.history(draft)
    assert h["cursor"] == 2, h
    bar = doc._recipe
    # the draft with nothing applied, for the comparison (undo both, read, redo both)
    D.undo(draft); D.undo(draft); stock = _tree(draft); D.redo(draft); D.redo(draft)   # noqa: E702
    assert _tree(draft) == composed
    bar.refresh()
    bar.select(1)
    bar.edit_btn.click()                                                  # Edit step 2 (the forest): it is lifted
    tool = doc._forest
    assert tool is not None and tool.editing() and D.history(draft)["edit"], bar.status_lbl.text()
    raised = []
    monkeypatch.setattr(sys, "excepthook", lambda *a: raised.append(a[1]))
    held = open(draft / D.HISTORY_DIR / D.EDIT_DIR / "0000" / "step.json", "rb")   # a reader in the parked folder
    try:
        tool.close_btn.click()                                            # Cancel edit: refused (and the refresh's)
        _say("after Cancel edit, the reader still there", bar, draft, composed, stock)
    finally:
        held.close()
    assert raised == [], raised
    bar.undo_btn.click()                                                  # the user's next click: Undo
    _say("after Undo (its refresh ran the auto-cancel)", bar, draft, composed, stock)
    pv = D.promote(draft, game=game, dry_run=True, log=lambda *a: None)
    print("\npromote (dry run) now: cells", pv["cells"], "-- it would mark promoted =", D.history(draft)["cursor"],
          "(both steps 'in the game'), the mountain's block never written")
    for i in (1, 2):
        bar.undo_btn.click()
        _say(f"Undo again #{i}", bar, draft, composed, stock)


def _stuck(monkeypatch, tmp_path, app):  # noqa: F811
    """[mountain, forest] composed; Edit step 2 (the forest); its Cancel edit refused by a reader in the parked
    folder (the refresh's own retry too); the reader then gone."""
    game = _two_islands(monkeypatch, tmp_path)
    saved = tmp_path / "two.toml"
    saved.write_text(RC.dumps([{"table": "mountain", "center": [90.0, -26.0], "donor": "0,0"},
                               {"table": "forest", "center": [26.0, -26.0], "donor": "15,15"}]), encoding="utf-8")
    doc, _run = _doc(app, game, tmp_path, saved)
    doc.set_view_mode("3d", sync=True)
    draft = tmp_path / "drafts" / "FF9CustomMap-world.draft"
    doc._recipe.open_btn.click()
    composed = _tree(draft)
    bar = doc._recipe
    bar.select(1)
    bar.edit_btn.click()
    tool = doc._forest
    assert tool.editing() and D.history(draft)["edit"]
    held = open(draft / D.HISTORY_DIR / D.EDIT_DIR / "0000" / "step.json", "rb")
    try:
        tool.close_btn.click()
    finally:
        held.close()
    assert D.history(draft)["edit"] and bar._edit is None
    return game, doc, bar, draft, composed


def test_stuck_edit_then_a_card_accept(monkeypatch, tmp_path, app):  # noqa: F811
    """The same refused cancel; then a fresh forest card (the bar holds nothing, so the menu opens one) and its Accept
    at another spot. The card records its step on top of the open edit; the tab's refresh of the bar runs the
    auto-cancel, which takes that step for one the edit put back: undone, dropped from the history, its folder
    deleted. The card says the forest is in the draft."""
    _game, doc, bar, draft, composed = _stuck(monkeypatch, tmp_path, app)
    card = doc.open_forest(sync=True)
    print("\n[stuck] menu opened a card:", card is not None, "| bar holding:", bar.holding())
    card.donor_box.setCurrentIndex(card.donor_box.findData("15,15"))
    card.place(30.0, -30.0, 3.2)
    card._timer.stop()
    card._check()
    assert card.accept_btn.isEnabled(), card.verdict_lbl.text()
    seen = []
    real = D.commit_step
    monkeypatch.setattr(D, "commit_step", lambda *a, **k: seen.append(real(*a, **k)) or seen[-1])
    card.accept_btn.click()
    h = D.history(draft)
    print("[after the card's Accept] card says:", repr(card.verdict_lbl.text() or card.status_lbl.text()
                                                       if hasattr(card, "status_lbl") else card.verdict_lbl.text()))
    print("   the card recorded:", [r["label"] for r in seen], "in", [r["dir"] for r in seen],
          "| its folder still there:", [(draft / r["dir"]).is_dir() for r in seen])
    print("   history now:", h["cursor"], [s["label"] for s in h["steps"]], "edit open:", bool(h["edit"]),
          "| draft == the recipe before the Accept:", _tree(draft) == composed)
    print("   bar says:", repr(bar.status_lbl.text()))


def test_a_refused_cancel_the_refresh_then_finishes(monkeypatch, tmp_path, app):  # noqa: F811
    """A reader holds the parked folder through the bar's own cancel only: R4-4's note is set after the refresh, which
    runs the auto-cancel at once and closes the edit -- the bar says the edit could not be undone over a draft that is
    exactly as it was, the edit closed."""
    game = _two_islands(monkeypatch, tmp_path)
    saved = tmp_path / "two.toml"
    saved.write_text(RC.dumps([{"table": "mountain", "center": [90.0, -26.0], "donor": "0,0"},
                               {"table": "forest", "center": [26.0, -26.0], "donor": "15,15"}]), encoding="utf-8")
    doc, _run = _doc(app, game, tmp_path, saved)
    doc.set_view_mode("3d", sync=True)
    draft = tmp_path / "drafts" / "FF9CustomMap-world.draft"
    doc._recipe.open_btn.click()
    composed = _tree(draft)
    bar = doc._recipe
    bar.select(1)
    bar.edit_btn.click()
    tool = doc._forest
    real, calls = D.cancel_edit, []

    def once_held(d):
        calls.append(1)
        if len(calls) > 1:
            return real(d)
        held = open(Path(d) / D.HISTORY_DIR / D.EDIT_DIR / "0000" / "step.json", "rb")
        try:
            return real(d)
        finally:
            held.close()
    monkeypatch.setattr(D, "cancel_edit", once_held)
    tool.close_btn.click()
    h = D.history(draft)
    print(f"\n[cancel refused once] draft.cancel_edit ran {len(calls)}x | edit open: {bool(h['edit'])} | cursor "
          f"{h['cursor']} | draft == as it was: {_tree(draft) == composed}\n   bar says: {bar.status_lbl.text()[:90]!r}")
