"""The overworld editor's edit of a placed step (rung C9), the kit half: ``draft.begin_edit`` undoes back to a step and
lifts it and the steps after it out, ``replay`` puts a lifted step back from its record, ``dirty_after`` says which
blocks may differ, ``finish_edit`` keeps the result and ``cancel_edit`` puts the draft back exactly; and the pick
(``recipe.step_at``) that chooses a step from a click."""
from __future__ import annotations

import pytest

from ff9mapkit.world import draft as D
from ff9mapkit.world import recipe as RC

from .test_world_forestedit import _fake_mirror, _game, _mod, _no_real_install  # noqa: F401
from .test_worldrecipe import T00, T10, _tree

FAR = "FF9_Data/WorldMap/Disc1/0_1/r5/Block[10][5] Terrain.ff9mesh"


def _row(x, z, table="forest"):
    return {"table": table, "center": [float(x), float(z)], "donor": "15,15"}


def _draft(tmp_path):
    game = _game(tmp_path)
    src = _mod(game, "Src", ((0, 0), (1, 0), (10, 5)))
    return game, src, D.ensure_draft(src, game=game, root=tmp_path / "drafts")


def _step(d, cells, writes, row, label):
    D.begin_step(d, cells)
    for rel, data in writes.items():
        (d / rel).write_bytes(data)
    with open(d / D.LEDGER, "a", encoding="utf-8") as f:   # a verb ledgers what it wrote
        f.write(f'{{"label": "{label}"}}\n')
    return D.commit_step(d, row, label)


def _three(d):
    """A forest in block (0,0), a mountain beside it in (1,0) (its read window reaches (0,0)), and a forest far off in
    (10,5) (its window does not)."""
    _step(d, [(0, 0)], {T00: b"forest one"}, _row(26, -26), "forest one")
    _step(d, [(1, 0)], {T10: b"mountain two"}, _row(90, -26, "mountain"), "mountain two")
    _step(d, [(10, 5)], {FAR: b"forest three"}, _row(672, -352), "forest three")


def test_cancel_puts_the_draft_back_exactly(tmp_path):
    _g, _s, d = _draft(tmp_path)
    _three(d)
    D.undo(d)                                           # the third undone: still redoable after the cancel
    whole, ledger, h0 = _tree(d), (d / D.LEDGER).read_bytes(), D.history(d)
    e = D.begin_edit(d, 0)
    assert e["at"] == 0 and e["applied"] == 2 and [s["label"] for s in e["lifted"]] == \
        ["forest one", "mountain two", "forest three"]
    h = D.history(d)
    assert h["cursor"] == 0 and h["steps"] == [] and h["edit"] == e
    assert (d / T00).read_bytes() != b"forest one"      # back before the step
    with pytest.raises(ValueError, match="already open"):
        D.begin_edit(d, 0)
    _step(d, [(0, 0)], {T00: b"forest moved"}, _row(30, -30), "forest moved")
    D.begin_step(d, [(1, 0)])                           # a half-run step: cancel aborts it too
    (d / T10).write_bytes(b"half")
    D.cancel_edit(d)
    h = D.history(d)
    assert _tree(d) == whole and (d / D.LEDGER).read_bytes() == ledger
    assert [s["label"] for s in h["steps"]] == [s["label"] for s in h0["steps"]] and h["cursor"] == 2
    assert h["edit"] is None and not (d / D.HISTORY_DIR / D.EDIT_DIR).exists()
    D.redo(d)                                           # the undone step's record came back whole
    assert (d / FAR).read_bytes() == b"forest three"


def test_an_edit_replays_the_steps_it_cannot_have_touched_and_re_runs_the_rest(tmp_path):
    _g, _s, d = _draft(tmp_path)
    _three(d)
    e = D.begin_edit(d, 0)
    old, mountain, far = e["lifted"]
    new = _step(d, [(0, 0)], {T00: b"forest moved"}, _row(30, -30), "forest moved")
    dirty = D.dirty_after(set(), old, new)
    assert dirty == {(0, 0)}
    assert RC.replay_window(mountain) & dirty           # the mountain read (0,0): it must run again
    assert not RC.replay_window(far) & dirty            # the far forest read nothing that changed
    rerun = _step(d, [(1, 0)], {T10: b"mountain two"}, mountain["row"], "mountain two")   # its re-run, same bytes
    dirty = D.dirty_after(dirty, mountain, rerun)
    assert dirty == {(0, 0)}                            # (1,0) came out alike: clean
    assert D.replay(d, far)
    D.finish_edit(d)
    h = D.history(d)
    assert [s["label"] for s in h["steps"]] == ["forest moved", "mountain two", "forest three"] and h["cursor"] == 3
    assert (d / T00).read_bytes() == b"forest moved" and (d / FAR).read_bytes() == b"forest three"
    assert (d / D.LEDGER).read_text().splitlines()[-1] == '{"label": "forest three"}'   # its ledger row came too
    assert h["edit"] is None
    D.undo(d)                                           # a replayed step is an ordinary step: it undoes
    assert (d / FAR).read_bytes() != b"forest three"


def test_replay_refuses_when_its_files_or_its_ledger_moved(tmp_path):
    _g, _s, d = _draft(tmp_path)
    _three(d)
    e = D.begin_edit(d, 0)
    far = e["lifted"][2]
    (d / FAR).write_bytes(b"someone else")
    assert not D.replay(d, far) and (d / FAR).read_bytes() == b"someone else"   # nothing written
    (d / FAR).write_bytes((d / far["dir"] / "before" / FAR).read_bytes())
    (d / far["dir"] / "after" / D.LEDGER).write_bytes(b"a ledger that is not the one before it plus rows\n")
    assert not D.replay(d, far) and D.history(d)["cursor"] == 0


def test_the_dirty_set():
    def rec(cells, after):
        return {"cells": [list(c) for c in cells], "after": after}
    a = rec([(0, 0)], {T00: "aa"})
    assert D.dirty_after(set(), a, rec([(0, 0)], {T00: "aa"})) == set()            # alike: clean
    assert D.dirty_after({(0, 0)}, a, rec([(0, 0)], {T00: "aa"})) == set()         # alike again: clean again
    assert D.dirty_after(set(), a, rec([(0, 0)], {T00: "bb"})) == {(0, 0)}
    assert D.dirty_after(set(), a, None) == {(0, 0)}                               # a delete
    assert D.dirty_after({(5, 5)}, a, rec([(1, 0)], {T10: "cc"})) == {(5, 5), (0, 0), (1, 0)}


def test_an_edit_refuses_a_promoted_step_and_promote_refuses_an_open_edit(monkeypatch, tmp_path):
    _fake_mirror(monkeypatch)
    game, _s, d = _draft(tmp_path)
    _step(d, [(0, 0)], {T00: b"forest one"}, _row(26, -26), "forest one")
    D.promote(d, game=game, log=lambda *a: None)
    _step(d, [(1, 0)], {T10: b"mountain two"}, _row(90, -26, "mountain"), "mountain two")
    with pytest.raises(ValueError, match="Revert promote first"):
        D.begin_edit(d, 0)
    with pytest.raises(ValueError, match="not an applied step"):
        D.begin_edit(d, 2)
    D.begin_edit(d, 1)
    with pytest.raises(ValueError, match="accept or cancel it first"):
        D.promote(d, game=game, log=lambda *a: None)
    D.cancel_edit(d)
    assert (d / T10).read_bytes() == b"mountain two"


def test_an_undo_that_refuses_on_the_way_down_leaves_the_draft_as_it_was(tmp_path):
    _g, _s, d = _draft(tmp_path)
    _three(d)
    (d / T00).write_bytes(b"someone else")              # step one's files moved: the walk down stops there
    with pytest.raises(ValueError, match="changed since it was applied"):
        D.begin_edit(d, 0)
    h = D.history(d)
    assert h["cursor"] == 3 and h["edit"] is None and (d / FAR).read_bytes() == b"forest three"


def test_a_click_picks_the_step_placed_nearest_it_on_the_block_it_changed():
    steps = [{"row": _row(26, -26, "mountain"), "cells": [[0, 0]]},
             {"row": _row(40, -40), "cells": [[0, 0]]},
             {"row": {"table": "transplant", "cell": [20, 0], "donor": [9, 5], "size": [2, 3], "rot": 90},
              "cells": [[20, 0], [21, 0], [22, 0], [20, 1], [21, 1], [22, 1]]},
             {"row": {"table": "sink", "at": [700.0, -300.0]}, "cells": [[10, 4]]}]
    assert RC.step_at(steps, 27.0, -27.0) == 0
    assert RC.step_at(steps, 41.0, -41.0) == 1
    assert RC.step_at(steps, 1400.0, -100.0) == 2       # anywhere on the carried rect
    assert RC.anchor(steps[2]["row"]) == (64.0 * 20 + 96.0, -64.0)    # turned 90: 3 x 2, its middle
    assert RC.step_at(steps, 700.0, -300.0) == 3        # the sea where the sunk island was
    assert RC.step_at(steps, 400.0, -400.0) is None
    assert RC.step_at(steps, 26.0 + 1536.0, -26.0) == 0     # the world wraps


# ---------------------------------------------------------------- the World tab: pick, edit, delete (THE C9 ACCEPTANCE)
from .test_worldrecipe import _doc, _place, _two_islands, app  # noqa: E402,F401


def _three_islands(monkeypatch, tmp_path):
    """_two_islands, plus a second forest bench far off in block (6,0): a step there reads nothing an edit at (0,0)
    changes."""
    from ff9mapkit.world import mesh as M
    from .test_world_interior import _mains_grid
    game = _two_islands(monkeypatch, tmp_path)
    far = _mains_grid()
    far.name, far.x = "Block[6][0] Terrain", 6
    M.deploy_override(far, mod_folder="FF9CustomMap-world", game=game, part="Terrain", disc=1)
    return game


def _placed(app, monkeypatch, tmp_path):
    import shutil
    game = _three_islands(monkeypatch, tmp_path)
    shutil.copytree(game / "FF9CustomMap-world", game / "Hand")
    doc, run = _doc(app, game, tmp_path, tmp_path / "saved.toml")
    doc.set_view_mode("3d", sync=True)
    forest = doc.open_forest(sync=True)
    forest.donor_box.setCurrentIndex(forest.donor_box.findData("15,15"))
    _place(forest, 26.0, -26.0)
    mountain = doc.open_mountain(sync=True)
    _place(mountain, 90.0, -26.0, angle=30)
    forest = doc.open_forest(sync=True)
    _place(forest, 410.0, -26.0)
    forest.close_tool()
    return game, doc, run, tmp_path / "drafts" / "FF9CustomMap-world.draft"


def _hit(x, z):
    return ((x, 3.2, z), "Terrain")


def _compose(game, rows, folder):
    """THE ORACLE: world-fuse of ``rows`` onto a copy of the folder the draft was made from."""
    from ff9mapkit import cli
    path = game / f"{folder}.toml"
    path.write_text(RC.dumps(rows), encoding="utf-8")
    assert cli.main(["--game", str(game), "world-fuse", str(path), "--mod-folder", folder]) == 0
    return _tree(game / folder)


def test_a_picked_forest_moved_in_its_card_is_the_recipe_with_the_move(monkeypatch, tmp_path, app):
    """THE C9 ACCEPTANCE: three steps placed through the World tab; a click picks the first, Edit opens its card on
    its own handles (the same row back), the forest moves; the mountain beside it is composed again, the far forest
    replayed; the draft is byte for byte the edited recipe composed by world-fuse onto the folder."""
    game, doc, run, draft = _placed(app, monkeypatch, tmp_path)
    bar = doc._recipe
    rows0 = D.recipe_rows(draft)
    doc._on_pick(_hit(27.0, -25.0), sync=True)
    assert bar._sel == 0 and bar.status_lbl.text() == "Step 1 of 3: forest forest-blob at 26, -26."
    assert not bar.edit_btn.isHidden() and bar.edit_btn.isEnabled() and bar.delete_btn.isEnabled()
    bar.edit_btn.click()
    forest = doc._forest
    assert not forest.isHidden() and forest.editing() and forest.accept_btn.text() == "Accept the edit"
    assert forest.row() == rows0[0]                     # the card opened on the step's own handles
    assert D.history(draft)["cursor"] == 0 and D.history(draft)["edit"]["at"] == 0
    assert bar.undo_btn.isHidden() and bar.save_btn.isHidden() and not bar.undo_btn.isEnabled()
    assert bar.edit_btn.isHidden() and bar.cancel_btn.isHidden() and forest.promote_btn.isHidden()
    assert bar.status_lbl.text() == ("Editing step 1, forest forest-blob at 26, -26, in its card below. The 2 steps "
                                     "after it come back on top when you accept.")
    n_fuse = sum(a[5] == "world-fuse" for a in run.argvs)
    forest.drop_at(30.0, -30.0)
    forest._timer.stop()
    forest._check()
    assert forest.accept_btn.isEnabled(), forest.verdict_lbl.text()
    forest.accept_btn.click()
    assert forest.isHidden() and not forest.editing()
    assert sum(a[5] == "world-fuse" for a in run.argvs) == n_fuse + 1     # the mountain again; the far forest replayed
    assert bar.status_lbl.text() == ("Edited step 1: forest forest-blob at 26, -26 is now forest forest-blob at 30, "
                                     "-30. The 2 steps after it are back on top (1 as they were, 1 composed again on "
                                     "the new ground).")
    rows = D.recipe_rows(draft)
    assert rows == [{**rows0[0], "center": [30.0, -30.0]}] + rows0[1:]
    h = D.history(draft)
    assert h["cursor"] == 3 and h["edit"] is None and bar._sel == 0
    assert _tree(draft) == _compose(game, rows, "Hand") != _tree(game / "FF9CustomMap-world")
    bar.undo_btn.click()                                # the put-back steps are ordinary steps
    assert D.history(draft)["cursor"] == 2


def test_a_deleted_step_leaves_the_recipe_without_it(monkeypatch, tmp_path, app):
    game, doc, _run, draft = _placed(app, monkeypatch, tmp_path)
    bar = doc._recipe
    rows0 = D.recipe_rows(draft)
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    bar.delete_btn.click()
    assert D.recipe_rows(draft) == rows0[1:] and bar.edit_btn.isHidden() and bar._sel is None
    assert bar.status_lbl.text().startswith("Deleted step 1, forest forest-blob at 26, -26. The 2 steps after it")
    assert _tree(draft) == _compose(game, rows0[1:], "Hand")


def test_a_step_that_refuses_on_the_new_ground_leaves_the_draft_as_it_was(monkeypatch, tmp_path, app):
    game, doc, run, draft = _placed(app, monkeypatch, tmp_path)
    bar = doc._recipe
    whole, h0 = _tree(draft), D.history(draft)

    class Refuses:
        def start(self, argv, cwd, done):
            run.argvs.append([str(a) for a in argv])
            done(1, "world-fuse: the mountain's rim found no plain grass to anchor against")

        def kill(self):
            pass
    bar._runner = Refuses()
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    bar.delete_btn.click()
    assert _tree(draft) == whole
    h = D.history(draft)
    assert [s["label"] for s in h["steps"]] == [s["label"] for s in h0["steps"]] and h["cursor"] == 3
    assert h["edit"] is None and bar.status_lbl.property("state") == "error"
    assert "on the new ground, mountain uaho at 90, -26 (a step after it) refuses: world-fuse: the mountain's rim" \
           in bar.status_lbl.text() and "exactly as it was" in bar.status_lbl.text()


def test_closing_the_card_cancels_the_edit_and_a_promoted_step_is_not_edited(monkeypatch, tmp_path, app):
    _fake_mirror(monkeypatch)
    game, doc, _run, draft = _placed(app, monkeypatch, tmp_path)
    bar = doc._recipe
    whole = _tree(draft)
    doc._on_pick(_hit(90.0, -26.0), sync=True)
    assert bar._sel == 1 and "mountain uaho at 90, -26" in bar.status_lbl.text()
    bar.edit_btn.click()
    mountain = doc._mountain
    assert mountain.editing() and mountain.angle.value() == 30
    mountain.close_btn.click()                          # Cancel edit
    assert _tree(draft) == whole and D.history(draft)["edit"] is None and D.history(draft)["cursor"] == 3
    assert "Edit cancelled" in bar.status_lbl.text()
    D.promote(draft, game=game, log=lambda *a: None)
    bar.refresh()
    bar.select(0)
    assert not bar.edit_btn.isEnabled() and not bar.delete_btn.isEnabled() and "in the game" in bar.status_lbl.text()


def test_every_editable_card_opens_on_its_row_and_says_it_back(monkeypatch, tmp_path, app):
    """load_row is the inverse of row(): a card set from a step's row builds the same row (no edit = no change)."""
    game = _two_islands(monkeypatch, tmp_path)
    doc, _run = _doc(app, game, tmp_path, tmp_path / "saved.toml")
    doc.set_view_mode("3d", sync=True)
    rows = {"forest": {"table": "forest", "center": [26.0, -26.0], "donor": "15,15", "rot": 45.0, "spread": 1.25},
            "mountain": {"table": "mountain", "center": [90.0, -26.0], "donor": "0,0", "rot": 300.0},
            "hill": {"table": "hill", "center": [26.0, -26.0], "height": 3.5, "radius": 20.0}}
    for table, row in rows.items():
        tool = getattr(doc, f"open_{table}")(sync=True)
        tool.load_row(row)
        assert tool.row() == row, table
        tool.close_tool()
    with pytest.raises(ValueError, match="not one the card lists"):
        doc.open_forest(sync=True).load_row({"table": "forest", "center": [0.0, 0.0], "donor": "99,99"})
    assert set(RC.EDITABLE_TABLES) == set(doc.EDIT_CARDS)


def test_a_second_draft_promotes_after_another_draft_of_the_folder_promoted_and_reverted(monkeypatch, tmp_path):
    """THE RELABEL CRASH (c9_lab, 2026-10-24): two drafts of one folder; the first promoted and reverted there, so the
    live ledger moved on past the second draft's copy. An inherited ledger row naming no writer (an old argv-less
    row) then read as a relabel with no tag, and promote crashed after writing half its files. A draft relabels only
    rows it wrote itself."""
    import json
    import shutil
    _fake_mirror(monkeypatch)
    game, src, edited = _draft(tmp_path)
    with open(src / D.LEDGER, "a", encoding="utf-8") as f:     # the old row: bytes recorded, no writer named
        f.write(json.dumps({"cell": [1, 0], "part": "Terrain", "write_disc": 1, "read_disc": 1,
                            "sha256": D._sha(src / T10), "argv": []}) + "\n")
    shutil.copy2(src / D.LEDGER, edited / D.LEDGER)            # the draft's copy holds it too
    _step(edited, [(0, 0)], {T00: b"the edit"}, _row(26, -26), "the edit")
    other = D.ensure_draft(src, game=game, root=tmp_path / "other")
    _step(other, [(1, 0)], {T10: b"another draft's edit"}, _row(90, -26), "another")
    D.promote(other, game=game, log=lambda *a: None)
    D.revert(other, game=game, log=lambda *a: None)
    rec = D.promote(edited, game=game, log=lambda *a: None)
    assert rec["promoted"] == [T00] and rec["relabelled"] == []
    assert (src / T00).read_bytes() == b"the edit"
