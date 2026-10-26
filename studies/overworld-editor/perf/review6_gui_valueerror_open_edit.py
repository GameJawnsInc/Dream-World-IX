"""Review-6 probe (3eb33114 R5-1's ValueError branch over 69ce0f7c R5-2): a cancel that the DRAFT refuses (a
ValueError: a file a lifted step will be redone over changed while the edit was open -- the card's Copy command run
by hand on the draft, another session) rather than the disk.

R5-2 keeps the redos owed in the OPEN edit (lifted [], redo_to), so the edit stays open in the draft. The bar's
ValueError branch (cancel_edit, and _close_stuck's alike) keeps the old guard: it drops the hold, settles the owed
promote and says "The edit could not be undone ... Promote it from a card." Then:
  * Cancel edit is hidden (the bar holds nothing), so the bar offers no way out of the open edit;
  * Promote from a card -- the advice -- is refused by draft.promote ("an edit ... is open: accept or cancel it");
  * Edit / Delete of any step is refused by begin_edit ("an edit is already open in the draft");
  * Undo is enabled; its own refresh's automatic cancel re-runs phase 2 and redoes the step just undone, while the
    bar says "Undone: ...".

Run from ff9mapkit/:
  py -m pytest ../studies/overworld-editor/perf/review6_gui_valueerror_open_edit.py -q -s -p no:cacheprovider
      --basetemp=../studies/overworld-editor/out/perf/review6/gui_valueerror_open_edit"""
from __future__ import annotations

from ff9mapkit.world import draft as D
from tests.test_world_forestedit import _no_real_install  # noqa: F401
from tests.test_worldedit import _hit, _promoted
from tests.test_worldrecipe import _tree, app  # noqa: F401

FAR = "FF9_Data/WorldMap/Disc1/0_1/r0/Block[6][0] Terrain.ff9mesh"


def _h(draft):
    h = D.history(draft)
    e = h["edit"]
    return (f"cursor {h['cursor']} of {[s['label'] for s in h['steps']]}, promoted {h['promoted']}, edit open "
            f"{bool(e)}{' (phase 2, redo_to ' + str(e.get('redo_to')) + ')' if e and 'redo_to' in e else ''}")


def test_a_draft_refused_cancel_leaves_an_open_edit_and_no_way_out(monkeypatch, tmp_path, app):  # noqa: F811
    game, doc, run, draft, live0 = _promoted(app, monkeypatch, tmp_path)
    bar = doc._recipe
    bar._ask = lambda title, text: True
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    bar.edit_btn.click()                                                   # in-game step 1: reverted, edit open
    forest = doc._forest
    assert forest.editing()
    (draft / FAR).write_bytes((draft / FAR).read_bytes() + b"\0")         # someone writes the far forest's block
    forest.close_btn.click()                                               # Cancel edit
    print(f"\n[after Cancel edit] {_h(draft)}; promote owed {D.promote_owed(draft)}"
          f"\n   live == before the edit: {_tree(game / 'FF9CustomMap-world') == live0}"
          f"\n   bar: holding {bar.holding()}, Cancel edit shown {not bar.cancel_btn.isHidden()}, Undo enabled "
          f"{bar.undo_btn.isEnabled()}\n   bar says: {bar.status_lbl.text()!r}")
    # the advice: Promote it from a card
    card = doc.open_forest(sync=True)
    card._ask = lambda title, text: True
    card._refresh_draft_label()
    print(f"[a card opens] {card is not None}; its Promote shown {not card.promote_btn.isHidden()}")
    card._promote()
    print(f"   after its Promote: card says {card.verdict_lbl.text()!r}")
    card.close_tool()
    # Edit or Delete any step
    bar.select(0)
    bar.edit_btn.click()
    print(f"[Edit step 1 again] bar says {bar.status_lbl.text()!r}; {_h(draft)}")
    # Undo
    before = D.history(draft)["cursor"]
    bar.undo_btn.click()
    print(f"[Undo] cursor before {before}, after {D.history(draft)['cursor']}; {_h(draft)}"
          f"\n   bar says: {bar.status_lbl.text()!r}")
