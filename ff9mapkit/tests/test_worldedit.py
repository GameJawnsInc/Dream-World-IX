"""The overworld editor's edit of a placed step (rung C9), the kit half: ``draft.begin_edit`` undoes back to a step and
lifts it and the steps after it out, ``replay`` puts a lifted step back from its record, ``dirty_after`` says which
blocks may differ, ``finish_edit`` keeps the result and ``cancel_edit`` puts the draft back exactly; and the pick
(``recipe.step_at``) that chooses a step from a click."""
from __future__ import annotations

import pytest

from ff9mapkit.world import draft as D
from ff9mapkit.world import recipe as RC

from .test_world_forestedit import _fake_mirror, _game, _mod, _no_real_install  # noqa: F401
from .test_worldcoast import REAL_GAME  # noqa: E402  (resolved at import, before the install guard closes)
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
    river = {"row": {"table": "river", "at": [512.0, 192.0], "move_from": [512.0, 128.0]}, "cells": [[0, 10], [23, 11]]}
    assert RC.anchor(river["row"]) is None              # its at is the carry's translation, not a place on the map
    assert RC.step_at(steps + [river], 20.0, -650.0) == 4 and RC.step_at(steps + [river], 1500.0, -720.0) == 4


def test_a_step_placed_on_the_river_s_blocks_is_still_picked():
    """A river has no anchor (its at is a translation), so it scored 0 on every block it changed and won every click
    there, before or after another step: a hill on the river's island could not be picked, so not edited or deleted
    (review of C12). A step with a place wins its block over one without; the river is picked where nothing else is."""
    river = {"row": {"table": "river", "at": [512.0, 128.0]}, "cells": [[8, 3], [9, 3], [8, 4], [9, 4]]}
    hill = {"row": {"table": "hill", "center": [560.0, -230.0]}, "cells": [[8, 3]]}
    for steps, h in (([river, hill], 1), ([hill, river], 0)):
        assert RC.step_at(steps, 561.0, -231.0) == h and RC.step_at(steps, 560.0, -230.0) == h
        assert RC.step_at(steps, 600.0, -300.0) == 1 - h                  # (9, 4): the river's alone


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


def test_closing_the_card_cancels_the_edit_and_a_promoted_step_says_it_is_in_the_game(monkeypatch, tmp_path, app):
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
    assert bar.edit_btn.isEnabled() and bar.delete_btn.isEnabled() and "in the game" in bar.status_lbl.text()
    assert "comes out of the game while you edit" in bar.edit_btn.toolTip()        # rung C19


# ---------------------------------------------------------------- a step that is in the game (rung C19)
def _promoted(app, monkeypatch, tmp_path):
    """_placed's three steps, promoted into the live folder (the fake disc-4 mirror), and the live folder's world
    files before any edit."""
    _fake_mirror(monkeypatch)
    game, doc, run, draft = _placed(app, monkeypatch, tmp_path)
    D.promote(draft, game=game, log=lambda *a: None)
    doc._recipe.refresh()
    return game, doc, run, draft, _tree(game / "FF9CustomMap-world")


def test_an_in_game_step_edited_comes_out_of_the_game_and_goes_back_in_edited(monkeypatch, tmp_path, app):
    """THE C19 ACCEPTANCE: a step that is in the game opens anyway -- its promote reverted (world-promote --revert),
    the edit as C9's, then the recipe promoted again -- and the live folder ends as the edited recipe composed onto
    the folder as it was before the draft: the ledger's own promote and revert carry every byte."""
    game, doc, run, draft, live0 = _promoted(app, monkeypatch, tmp_path)
    bar = doc._recipe
    rows0 = D.recipe_rows(draft)
    asked = []
    bar._ask = lambda title, text: asked.append(title) or True
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    bar.edit_btn.click()
    assert asked == ["Edit a step that is in the game?"]
    verbs = [a[5:7] for a in run.argvs if a[5] == "world-promote"]
    assert verbs == [["world-promote", str(draft)]] and "--revert" in run.argvs[-1]
    forest = doc._forest
    assert forest.editing() and forest.row() == rows0[0] and D.history(draft)["promoted"] == 0
    assert _tree(game / "FF9CustomMap-world") != live0                       # out of the game while it is open
    forest.drop_at(30.0, -30.0)
    forest._timer.stop()
    forest._check()
    forest.accept_btn.click()
    rows = D.recipe_rows(draft)
    assert rows == [{**rows0[0], "center": [30.0, -30.0]}] + rows0[1:]
    assert "--revert" not in run.argvs[-1] and run.argvs[-1][5] == "world-promote"      # promoted again, last
    h = D.history(draft)
    assert h["promoted"] == 3 and h["edit"] is None and D.edits(draft) == []
    assert "Promoted into FF9CustomMap-world again" in bar.status_lbl.text(), bar.status_lbl.text()
    assert _tree(game / "FF9CustomMap-world") == _compose(game, rows, "Hand")


def test_an_in_game_step_whose_edit_is_cancelled_goes_back_into_the_game_as_it_was(monkeypatch, tmp_path, app):
    game, doc, run, draft, live0 = _promoted(app, monkeypatch, tmp_path)
    bar = doc._recipe
    bar._ask = lambda title, text: True
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    bar.edit_btn.click()
    doc._forest.close_btn.click()                                          # Cancel edit
    assert _tree(game / "FF9CustomMap-world") == live0                      # the game exactly as it was
    assert D.history(draft)["promoted"] == 3 and "Edit cancelled" in bar.status_lbl.text()
    assert "again" in bar.status_lbl.text()


def test_an_in_game_step_deleted_leaves_the_game_without_it(monkeypatch, tmp_path, app):
    game, doc, run, draft, _live0 = _promoted(app, monkeypatch, tmp_path)
    bar = doc._recipe
    asked = []
    bar._ask = lambda title, text: asked.append(text) or True
    rows0 = D.recipe_rows(draft)
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    bar.delete_btn.click()
    assert "It is in the game" in asked[0]
    assert D.recipe_rows(draft) == rows0[1:] and D.history(draft)["promoted"] == 2
    assert _tree(game / "FF9CustomMap-world") == _compose(game, rows0[1:], "Hand")


def test_an_in_game_step_whose_promote_cannot_come_out_stays_as_it_was(monkeypatch, tmp_path, app):
    """Revert refuses over later work at its blocks: the edit does not open, and the game and the draft stay."""
    game, doc, run, draft, live0 = _promoted(app, monkeypatch, tmp_path)
    bar = doc._recipe
    bar._ask = lambda title, text: True
    live = game / "FF9CustomMap-world"
    (live / T00).write_bytes(b"another session's edit")                    # later work at a promoted block
    h0, after0 = D.history(draft), _tree(live)
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    bar.edit_btn.click()
    assert not doc._forest.editing() and bar.status_lbl.property("state") == "error"
    assert "could not be taken back out of the game" in bar.status_lbl.text(), bar.status_lbl.text()
    assert _tree(live) == after0 and D.history(draft) == h0


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
    # THE SAID-BACK LAW (rung C12): an edit opens only on a row its card builds again, key for key -- a hand-written
    # centre off the editor's 0.1u grid would otherwise move the shape before the author touched a handle
    with pytest.raises(ValueError, match="would not say its center back as the step has it"):
        doc.open_hill(sync=True).edit_row({"table": "hill", "center": [26.04, -26.0]}, label="hill",
                                          on_accepted=lambda: None, on_cancel=lambda note=None: None)
    assert set(RC.EDITABLE_TABLES) == set(doc.EDIT_CARDS) == set(RC.EDITOR_TABLES)    # every table the editor writes


def test_a_row_that_spells_a_default_opens_in_its_card(monkeypatch, tmp_path, app):
    """An opened recipe keeps each row as written, and a hand-written row may spell a default the editor leaves out
    (rot = 0.0, spread = 1.0) or turn a full circle (rot = 360). The said-back law compared the raw rows key for key
    and refused these, though the card writes the same bytes (review of C12); it compares rows as the editor writes
    them (recipe.canon). A row the handles cannot say still refuses."""
    game = _two_islands(monkeypatch, tmp_path)
    doc, _run = _doc(app, game, tmp_path, tmp_path / "saved.toml")
    doc.set_view_mode("3d", sync=True)
    base = {"table": "forest", "center": [26.0, -26.0], "donor": "15,15"}
    for extra in ({"rot": 0.0}, {"spread": 1.0}, {"rot": 360.0}, {"rot": 405.0, "spread": 1.0}):
        tool = doc.open_forest(sync=True)
        tool.edit_row({**base, **extra}, label="forest", on_accepted=lambda: None, on_cancel=lambda note=None: None)
        assert tool.editing(), extra
        tool._end_edit()
        tool.close_tool()
    assert RC.canon({**base, "rot": 405.0, "spread": 1.0}) == {**base, "rot": 45.0}
    assert RC.canon({"table": "sink", "at": [1.0, 2.0], "cluster": False, "allow_entrances": False}) == \
        {"table": "sink", "at": [1.0, 2.0]}
    assert RC.canon({"table": "transplant", "cell": [3, 5], "donor": [7, 17], "rot": 360, "size": [1, 1]}) == \
        {"table": "transplant", "cell": [3, 5], "donor": [7, 17]}
    with pytest.raises(ValueError, match="would not say its center back"):              # off the 0.1u grid
        doc.open_forest(sync=True).edit_row({**base, "rot": 0.0, "center": [26.04, -26.0]}, label="forest",
                                            on_accepted=lambda: None, on_cancel=lambda note=None: None)


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


def test_an_opened_recipe_can_be_edited_the_manifest_does_not_refuse_the_put_back(monkeypatch, tmp_path, app):
    """world-fuse refuses to compose over files its world_manifest.json recorded and that have since changed (THE
    MANIFEST DRIFT GATE, for a live folder another session may have written). In a draft they change by design: an
    edit undoes the steps and the card writes the moved shape. So after Open recipe (every row a world-fuse job,
    every file recorded), an edit's put-back refused on its own draft until the editor's world-fuse jobs waived
    that gate there (the ownership refusal at the write seam still stands)."""
    game, doc, _run, draft = _placed(app, monkeypatch, tmp_path)
    bar = doc._recipe
    rows0 = D.recipe_rows(draft)
    saved = tmp_path / "three.toml"
    saved.write_text(RC.dumps(rows0), encoding="utf-8")
    bar._open_path_fn = lambda: saved
    bar.open_btn.click()                                # a fresh draft, one world-fuse job per row
    assert D.recipe_rows(draft) == rows0 and (draft / "FF9_Data" / "WorldMap" / "world_manifest.json").is_file()
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    bar.edit_btn.click()
    forest = doc._forest
    forest.drop_at(30.0, -30.0)
    forest._timer.stop()
    forest._check()
    forest.accept_btn.click()
    assert bar.status_lbl.property("state") == "ok", bar.status_lbl.text()
    rows = D.recipe_rows(draft)
    assert rows == [{**rows0[0], "center": [30.0, -30.0]}] + rows0[1:]
    assert _tree(draft) == _compose(game, rows, "Hand")


# ---------------------------------------------------------------- the read windows (rung C11)
def test_each_table_s_read_window():
    """An island's footprint and its ring, a carry's turned rect and its ring, a sink's own cells and their ring --
    wrapping at x = 0 -- and the whole world for the tables not measured."""
    from ff9mapkit.world import islandedit as IE
    isl = {"table": "island", "center": [32.0, -160.0], "seed": 5.0}
    foot = {(bx % 24, by) for bx, by in IE.footprint(IE.outline((32.0, -160.0), radius=24.0, seed=5.0))}
    w = RC.replay_window({"row": isl, "cells": [[0, 2]]})
    assert foot <= w and (23, 2) in w and (1, 3) in w and len(w) < 30
    carry = {"table": "transplant", "cell": [20, 0], "donor": [9, 5], "size": [2, 3], "rot": 90}
    w = RC.replay_window({"row": carry, "cells": [[20, 0]]})
    assert {(x, y) for x in range(19, 24) for y in range(0, 3)} == w          # 3x2 turned, its ring, row 0 the edge
    w = RC.replay_window({"row": {"table": "transplant", "cell": [0, 5], "donor": [7, 17]}, "cells": [[0, 5]]})
    assert w == {((0 + dx) % 24, 5 + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)} and (23, 4) in w
    w = RC.replay_window({"row": {"table": "sink", "at": [679.0, -386.7]}, "cells": [[10, 5], [10, 6]]})
    assert w == {(x, y) for x in (9, 10, 11) for y in (4, 5, 6, 7)}
    # rung C13: a coast morph its own block (no ring: it keeps the block's frame); a river the blocks it changed
    assert RC.replay_window({"row": {"table": "morph", "cell": [3, 4]}, "cells": [[3, 4]]}) == {(3, 4)}
    assert RC.replay_window({"row": {"table": "morph", "cell": [3, 4]}, "cells": []}) == {(3, 4)}
    mv = [[0, 10], [0, 11], [23, 11], [1, 14]]
    assert RC.replay_window({"row": {"table": "river", "at": [512.0, 128.0], "move_from": [512.0, 192.0]},
                             "cells": mv}) == {tuple(c) for c in mv}
    assert len(RC.replay_window({"row": {"table": "river", "at": [512.0, 128.0]}, "cells": []})) == 480  # unknown


# ---------------------------------------------------------------- the windows hold what the verbs read (real bytes)
def _reads(monkeypatch, root):
    """Every file opened, every existence check, every listing and every glob under ``root``, as the blocks they
    name (a listing names none: a row directory)."""
    import builtins
    import io
    import os
    import pathlib
    import re
    seen = []
    low = str(root).lower()

    def note(p):
        try:
            s = os.fsdecode(p)
        except TypeError:
            return
        if low in s.lower().replace("/", "\\"):
            seen.append(s)
    for mod, name in ((builtins, "open"), (io, "open"), (os, "stat"), (os, "lstat"), (os, "scandir"),
                      (os, "listdir"), (os.path, "exists"), (os.path, "isfile"), (os.path, "isdir")):
        real = getattr(mod, name)

        def wrap(p=None, *a, _real=real, **k):
            if p is not None:
                note(p)
            return _real(p, *a, **k) if p is not None else _real(*a, **k)
        monkeypatch.setattr(mod, name, wrap)
    for name in ("glob", "rglob"):
        real = getattr(pathlib.Path, name)

        def gwrap(self, pattern, *a, _real=real, **k):
            note(str(self) + "/" + pattern)
            return _real(self, pattern, *a, **k)
        monkeypatch.setattr(pathlib.Path, name, gwrap)
    blk = re.compile(r"Block\[\[?\]?(\d+)\[?\]?\]\[\[?\]?(\d+)")

    def blocks():
        out = set()
        for s in seen:
            m = blk.search(s.replace("[[]", "[").replace("[]]", "]"))
            if m:
                out.add((int(m.group(1)), int(m.group(2))))
        return out
    return seen, blocks


def test_on_real_bytes_an_island_a_carry_a_sink_a_morph_and_a_river_read_only_their_window(monkeypatch, tmp_path):
    """THE C11 FENCE (C13: the morph and the river too): each verb, run for real on its own draft of the real FF9CustomMap-world at a target its card
    calls lawful, reads no block of that draft outside ``recipe.replay_window`` -- so a step whose window no edit
    touched may replay from its record. A verb that starts reading wider goes red here."""
    if REAL_GAME is None or not (REAL_GAME / "FF9CustomMap-world").is_dir():
        import warnings
        warnings.warn("the read windows went unchecked on real bytes: no FF9 install + UnityPy + FF9CustomMap-world. "
                      "Re-run in the MAIN repo (C:/gd/Dream-World-IX/ff9mapkit).", UserWarning)
        pytest.skip("needs the FF9 install + UnityPy + FF9CustomMap-world")
    import json
    from pathlib import Path
    from ff9mapkit import cli
    from ff9mapkit.world import islandedit as IE
    from ff9mapkit.world import mesh as M
    from ff9mapkit.world import river as RV
    from ff9mapkit.world import sinkedit as SE
    from ff9mapkit.world import transplantedit as TE
    src = REAL_GAME / "FF9CustomMap-world"
    land = IE.stock_land(game=REAL_GAME)
    probe = D.ensure_draft(src, game=REAL_GAME, root=tmp_path / "probe")
    stack = [str(probe)] + [str(REAL_GAME / f) for f in RV.stack_folders(REAL_GAME) if f != src.name]

    def occupied(blocks):
        return {tuple(b): ["x"] for b in blocks
                if any(M.existing_overrides([tuple(b)], fo, disc=d, game=REAL_GAME) for fo in stack for d in (1, 4))}
    cases = []
    c = next(((64.0 * bx + 32.0, -(64.0 * by + 32.0)) for by in range(2, 18) for bx in range(24)
              if IE.preview(IE.outline((64.0 * bx + 32.0, -(64.0 * by + 32.0)), radius=24.0, seed=5.0),
                            land=land, occupied=occupied)["ok"]), None)
    if c is not None:
        cases.append(("island", IE.command("D", c, seed=5.0, dry_run=False)))
    cell = next(((bx, by) for by in range(2, 18) for bx in range(24)
                 if TE.preview((bx, by), land=land, occupied=occupied)["ok"]), None)
    if cell is not None:
        cases.append(("transplant", TE.command("D", cell, (7, 17), dry_run=False)))
    unit = next(((bx, by) for by in range(2, 17) for bx in range(24)
                 if TE.preview((bx, by), land=land, occupied=occupied, size=(1, 2))["ok"]), None)
    if unit is not None:
        cases.append(("unit", TE.command("D", unit, (10, 17), size=(1, 2), dry_run=False)))
    row = next((r for r in SE.candidates(REAL_GAME) if SE.verdict(r)["ok"]), None)
    if row is not None:
        cases.append(("sink", SE.command("D", tuple(row["at"]), disc=1, dry_run=False)))
    # rung C13: a coast morph (both its calls, disc 1 then disc 4) on a coastal block no folder holds ...
    from ff9mapkit.world import coastedit as CE
    from ff9mapkit.world import riveredit as RE
    morph, scanned = None, 0
    for r in SE.candidates(REAL_GAME):
        for b in r.get("blocks") or []:
            if morph or scanned >= 16 or occupied([b]):
                continue
            scanned += 1
            morph = next(((tuple(b), w, v) for w in CE.windows(REAL_GAME, tuple(b)) for v in CE.lawful(w)), None)
    if morph is not None:
        b, w, verb = morph
        lo, hi = CE.lawful(w)[verb]
        cases.append(("morph", CE.commands("D", b, verb, CE.spec(w, verb, hi if hi > 0 else lo))))
    # ... and the river moved to the first placement no folder holds (its own files left out)
    rs = RE.shape(game=REAL_GAME)
    here = RE.placements(rs, str(probe), game=REAL_GAME)
    if here:
        at, mine = here[0][0], {Path(p) for p in here[0][1]}

        def held(cells):
            return any(Path(p) not in mine for fo in stack for d in (1, 4)
                       for p in M.existing_overrides(cells, fo, disc=d, game=REAL_GAME))
        to = next((s for s in rs.shifts if not RE.same_shift(s, at) and not held(rs.cells_at(s))), None)
        if to is not None:
            cases.append(("river", [RE.command("D", to, move_from=at, dry_run=False)]))
    if not any(k == "river" for k, _a in cases):        # the live folder holds every placement (it changes under us)
        import warnings
        warnings.warn("the river's read window went unchecked on real bytes: the live folder holds every placement "
                      "it could move to", UserWarning)
    assert [k for k, _a in cases if k != "river"] == ["island", "transplant", "unit", "sink", "morph"], cases
    unheld = []
    for name, calls in cases:
        calls = calls if isinstance(calls[0], list) else [calls]
        d = D.ensure_draft(src, game=REAL_GAME, root=tmp_path / name)
        calls = [[str(d) if a == "D" else a for a in argv] for argv in calls]
        rep = tmp_path / f"{name}.json"
        with monkeypatch.context() as mp:
            seen, blocks = _reads(mp, d)
            for argv in calls:
                assert cli.main(["--game", str(REAL_GAME)] + argv + ["--report-json", str(rep)]) == 0, name
            read = blocks()
        v = json.loads(rep.read_text(encoding="utf-8"))
        step = {"row": RC.row_for([a if a != str(d) else "-" for a in calls[0]]),
                "cells": [list(b[1:]) for b in D.edited_blocks(d) if b[0] == 1] or v.get("blocks") or []}
        window = RC.replay_window(step)
        assert read, (name, seen[:5])                     # the recorder saw the verb's reads at all
        assert read <= window, (name, sorted(read - window), sorted(window))
        if name in ("morph", "river"):                    # a ringless window means something only where a ring is held
            cells = {tuple(c) for c in step["cells"]}
            if not any(occupied([c]) for c in RC._ring(cells) - cells):
                unheld.append(name)
    if unheld:
        import warnings
        warnings.warn(f"no neighbour of the {', '.join(unheld)} step is held on the real folder: its ringless window "
                      "was not put to the test", UserWarning)


@pytest.mark.skipif(__import__("os").name != "nt", reason="the sharing violation is Windows'")
def test_an_undo_waits_for_a_reader_that_holds_a_file_open(tmp_path):
    """An Edit clicked while a card still reads the island it just accepted (a worker thread holds a draft file
    open) raced its own undo: Windows refuses to delete an open file. The undo waits for it (c11_lab)."""
    import threading
    _g, _s, d = _draft(tmp_path)
    new = "FF9_Data/WorldMap/Disc1/0_1/r0/Block[0][0] Object.ff9mesh"
    _step(d, [(0, 0)], {new: b"an object the step made"}, _row(26, -26), "forest one")
    f = open(d / new, "rb")                             # the reader
    threading.Timer(0.4, f.close).start()
    D.undo(d)                                           # it must delete the file the step made
    assert not (d / new).exists() and D.history(d)["cursor"] == 0


def test_a_second_revert_refusing_puts_the_first_back_into_the_game(monkeypatch, tmp_path, app):
    """Two promotes stand over step 1: the newer reverts, the older refuses (later work at its block). The bar promotes
    straight back, so the game is never left half reverted: the live folder ends exactly as it was."""
    game, doc, run, draft, _live0 = _promoted(app, monkeypatch, tmp_path)
    bar = doc._recipe
    bar._ask = lambda title, text: True
    (draft / FAR).parent.mkdir(parents=True, exist_ok=True)               # a block of open sea: a new file
    _step(draft, [(10, 5)], {FAR: b"a fourth step"}, _row(672, -352), "a fourth step")
    D.promote(draft, game=game, log=lambda *a: None)                       # the newer promote: step 4 only
    live = game / "FF9CustomMap-world"
    (live / T00).write_bytes(b"another session's edit")                    # later work at the older promote's block
    after0 = _tree(live)
    bar.refresh()
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    bar.edit_btn.click()
    reverts = [a for a in run.argvs if a[5] == "world-promote" and "--revert" in a]
    assert len(reverts) == 2 and run.argvs[-1][5] == "world-promote" and "--revert" not in run.argvs[-1]
    assert not doc._forest.editing() and "could not be taken back" in bar.status_lbl.text()
    assert "again" in bar.status_lbl.text(), bar.status_lbl.text()
    assert _tree(live) == after0 and D.history(draft)["promoted"] == 4


class _Held:
    """A runner that holds each job until :meth:`wait`: a job still running when the Workspace closes."""

    def __init__(self, argvs):
        self.argvs, self.held = argvs, None

    def start(self, argv, cwd, done):
        self.argvs.append([str(a) for a in argv])
        self.held = (argv, done)

    def busy(self):
        return self.held is not None

    def wait(self, msecs=-1):
        from ff9mapkit import cli
        argv, done = self.held
        self.held = None
        done(cli.main([str(a) for a in argv[3:]]), "")     # (its done may start the next job, as a real one does)
        return True

    def kill(self):
        self.held = None


def test_closing_the_workspace_mid_in_game_edit_puts_the_game_back(monkeypatch, tmp_path, app):
    """The Workspace closes with an in-game step's edit open: the edit is cancelled and the steps that were in the
    game go back into it before the window goes (``WorldDoc.shutdown``, from the shell's closeEvent)."""
    game, doc, run, draft, live0 = _promoted(app, monkeypatch, tmp_path)
    bar = doc._recipe
    bar._ask = lambda title, text: True
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    bar.edit_btn.click()
    assert doc._forest.editing() and _tree(game / "FF9CustomMap-world") != live0
    doc.shutdown()
    assert _tree(game / "FF9CustomMap-world") == live0
    h = D.history(draft)
    assert h["edit"] is None and h["promoted"] == 3 and h["cursor"] == 3 and D.promote_owed(draft) is None


def test_closing_the_workspace_mid_revert_finishes_the_chain(monkeypatch, tmp_path, app):
    """A revert job still running when the Workspace closes is waited for, never killed half way, and the chain it
    began closes with the game as it was."""
    game, doc, run, draft, live0 = _promoted(app, monkeypatch, tmp_path)
    bar = doc._recipe
    bar._ask = lambda title, text: True
    bar._runner = held = _Held(run.argvs)
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    bar.edit_btn.click()
    assert held.busy() and "--revert" in held.argvs[-1]
    doc.shutdown()
    assert not held.busy() and _tree(game / "FF9CustomMap-world") == live0
    assert D.history(draft)["promoted"] == 3 and D.promote_owed(draft) is None


def test_closing_the_workspace_waits_for_every_job_of_the_chain(monkeypatch, tmp_path, app):
    """Two promotes stand over step 1: the first revert's end starts the second. shutdown took a job running after a
    wait for one that never ended, and returned with that revert running: the window closed on a live-folder write
    (review of the C19 fixes). It waits each job, the next one too, and the chain closes with the game as it was."""
    game, doc, run, draft, live0 = _promoted(app, monkeypatch, tmp_path)
    bar = doc._recipe
    bar._ask = lambda title, text: True
    _unpromoted_fourth(draft)
    D.promote(draft, game=game, log=lambda *a: None)                       # P2: step 4, in the game too
    live1 = _tree(game / "FF9CustomMap-world")
    bar.refresh()
    bar._runner = held = _Held(run.argvs)
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    bar.edit_btn.click()
    assert held.busy() and "--revert" in held.argvs[-1]
    doc.shutdown()
    assert not held.busy() and sum("--revert" in a for a in held.argvs) == 2
    assert _tree(game / "FF9CustomMap-world") == live1
    assert D.history(draft)["promoted"] == 4 and D.promote_owed(draft) is None


def test_closing_the_workspace_while_an_in_game_edit_s_accept_runs_lets_it_finish(monkeypatch, tmp_path, app):
    """The card's own Accept is writing the draft when the window closes: shutdown cancelled the edit under it (its
    pending step aborted, then the game promoted from a draft the job was still writing). Every job that writes runs
    to its end first -- the card's Accept, then the put-back and the promote back it leads to (review of the C19
    fixes)."""
    game, doc, run, draft, live0 = _promoted(app, monkeypatch, tmp_path)
    bar = doc._recipe
    bar._ask = lambda title, text: True
    rows0 = D.recipe_rows(draft)
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    bar.edit_btn.click()
    forest = doc._forest
    forest._runner = held = _Held([])
    forest.drop_at(30.0, -30.0)
    forest._timer.stop()
    forest._check()
    held.wait()                                                            # the check, in
    assert forest.accept_btn.isEnabled(), forest.verdict_lbl.text()
    forest.accept_btn.click()
    assert held.busy()                                                     # its Accept writing the draft
    doc.shutdown()
    assert not held.busy() and D.history(draft)["edit"] is None
    rows = D.recipe_rows(draft)
    assert rows == [{**rows0[0], "center": [30.0, -30.0]}] + rows0[1:]
    assert _tree(game / "FF9CustomMap-world") == _compose(game, rows, "Hand")
    assert D.history(draft)["promoted"] == 3 and D.promote_owed(draft) is None


def test_closing_the_workspace_while_a_recipe_composes_stops_after_the_running_row(monkeypatch, tmp_path, app):
    """Each row's end starts the next, and shutdown waits for every job that writes: it composed the whole rest of an
    opened recipe inside closeEvent, minutes with the window frozen (review of the C19 fixes, third round). A row is
    its own step and an opened recipe owes the game nothing, so the running row ends and the rest waits."""
    game, doc, run, draft = _placed(app, monkeypatch, tmp_path)
    bar = doc._recipe
    bar.save_btn.click()                                                   # the recipe, three rows
    bar._runner = held = _Held(run.argvs)
    bar.open_btn.click()                                                   # composed again, a row at a time
    assert held.busy() and bar._queue is not None
    doc.shutdown()
    assert not held.busy() and bar._queue is None and D.history(draft)["cursor"] == 1
    assert "1 row" in bar.status_lbl.text() and "closed" in bar.status_lbl.text(), bar.status_lbl.text()


def test_an_in_game_edit_a_dead_workspace_left_open_is_put_right_on_the_next_launch(monkeypatch, tmp_path, app):
    """The Workspace dies with an in-game edit open (no shutdown): what the game is owed is on disk, so the next
    launch puts the draft back and promotes the game's steps again, and says so."""
    game, doc, run, draft, live0 = _promoted(app, monkeypatch, tmp_path)
    bar = doc._recipe
    bar._ask = lambda title, text: True
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    bar.edit_btn.click()
    assert _tree(game / "FF9CustomMap-world") != live0
    doc2, _run2 = _doc(app, game, tmp_path, tmp_path / "saved.toml")      # the next launch, on the same draft
    doc2.set_view_mode("3d", sync=True)
    assert _tree(game / "FF9CustomMap-world") == live0
    h = D.history(draft)
    assert h["edit"] is None and h["promoted"] == 3 and h["cursor"] == 3 and D.promote_owed(draft) is None
    text = doc2._recipe.status_lbl.text()
    assert "The Workspace closed with a step that is in the game taken out of it" in text and "again" in text, text


def test_the_folder_cannot_change_under_an_open_edit(monkeypatch, tmp_path, app):
    """While the recipe bar holds the draft (an edit open), the folder box and Rescan wait: a switch closed the card,
    and its cancel went to the NEW folder's draft, so the first folder's game stayed reverted."""
    game, doc, run, draft, live0 = _promoted(app, monkeypatch, tmp_path)
    bar = doc._recipe
    bar._ask = lambda title, text: True
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    bar.edit_btn.click()
    assert doc._forest.editing()
    assert not doc.folder_box.isEnabled() and not doc.rescan_btn.isEnabled()
    census = doc._census
    doc.refresh(sync=True)                                                  # a Rescan asked for anyway waits too
    assert doc._census is census and doc._forest.editing()
    doc._forest.close_btn.click()                                          # Cancel edit
    assert doc.folder_box.isEnabled() and doc.rescan_btn.isEnabled()
    assert _tree(game / "FF9CustomMap-world") == live0


def test_a_scan_that_lands_under_an_open_edit_cancels_it_in_its_own_folder(monkeypatch, tmp_path, app):
    """A scan begun before the edit (another folder picked) lands while it is open: the card closes, and the cancel
    goes to the draft the edit is in, so its game gets its promote back."""
    from ff9mapkit.workspace import worldscan
    game, doc, run, draft, live0 = _promoted(app, monkeypatch, tmp_path)
    bar = doc._recipe
    bar._ask = lambda title, text: True
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    bar.edit_btn.click()
    doc._finish(worldscan.scan_tree(game / "Hand"), None, None)           # the scan lands: Hand is shown now
    h = D.history(draft)
    assert h["edit"] is None and h["promoted"] == 3 and D.promote_owed(draft) is None
    assert _tree(game / "FF9CustomMap-world") == live0


def test_the_folder_waits_for_the_chain_s_revert_and_a_scan_landing_mid_chain_opens_nothing(monkeypatch, tmp_path,
                                                                                            app):
    """The chain's revert job runs for seconds: the folder box and Rescan wait for it too. A scan begun before it that
    lands meanwhile moves the tab off the chain's folder, and the chain does not open its edit on the wrong one: it
    promotes its folder's steps back and says why."""
    from ff9mapkit.workspace import worldscan
    game, doc, run, draft, live0 = _promoted(app, monkeypatch, tmp_path)
    bar = doc._recipe
    bar._ask = lambda title, text: True
    bar._runner = held = _Held(run.argvs)
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    bar.edit_btn.click()
    assert held.busy() and not doc.folder_box.isEnabled() and not doc.rescan_btn.isEnabled()
    census = doc._census
    doc.refresh(sync=True)
    assert doc._census is census
    doc._finish(worldscan.scan_tree(game / "Hand"), None, None)           # a scan begun before the chain lands
    held.wait()                                                            # the revert ends
    assert held.busy() and "--revert" not in held.argvs[-1]                # ...and the promote back runs, no edit
    held.wait()
    assert not doc._forest or not doc._forest.editing()
    assert _tree(game / "FF9CustomMap-world") == live0
    h = D.history(draft)
    assert h["edit"] is None and h["promoted"] == 3 and D.promote_owed(draft) is None
    assert "another folder" in bar.status_lbl.text(), bar.status_lbl.text()


def test_a_scan_tells_every_card_the_folder_moved(monkeypatch, tmp_path, app):
    """THE CALL SITE: a folder pick or a Rescan only closed the open cards, and each card keeps per-folder reads (the
    coast's and the island's block holders, where the river stands): reopened on another folder they judged it by the
    old one's -- the river card built --move-from from the first folder's river (review of the C12 fixes). The scan
    is the one place the folder changes, and it tells every card, open or not."""
    from ff9mapkit.workspace import worldscan
    game, doc, run, draft = _placed(app, monkeypatch, tmp_path)
    doc.open_mountain(sync=True).close_tool()
    told = []
    for tool in doc._carry_tools():
        monkeypatch.setattr(tool, "island_changed", lambda t=tool: told.append(type(t).__name__))
    doc._finish(worldscan.scan_tree(game / "Hand"), None, None)
    assert sorted(told) == sorted(type(t).__name__ for t in doc._carry_tools()) and len(told) >= 2


def test_a_folder_shown_again_gets_the_promote_it_is_owed(monkeypatch, tmp_path, app):
    """A Workspace died with an in-game edit open in FF9CustomMap-world; the next one opens on another folder first.
    Showing FF9CustomMap-world settles what its game is owed."""
    from types import SimpleNamespace
    from ff9mapkit.workspace import worldscan
    game, doc, run, draft, live0 = _promoted(app, monkeypatch, tmp_path)
    bar = doc._recipe
    bar._ask = lambda title, text: True
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    bar.edit_btn.click()                                                   # ...and the Workspace dies
    doc2, _run2 = _doc(app, game, tmp_path, tmp_path / "saved.toml")
    doc2._census = SimpleNamespace(root=game / "Hand")
    doc2.set_view_mode("3d", sync=True)
    assert _tree(game / "FF9CustomMap-world") != live0                     # Hand owes nothing
    doc2._finish(worldscan.scan_tree(game / "FF9CustomMap-world"), None, None)
    assert _tree(game / "FF9CustomMap-world") == live0 and D.promote_owed(draft) is None


def test_the_qprocess_runner_waits_for_its_job(app):
    import sys
    from ff9mapkit.workspace.worldforest import QProcessRunner
    r, got = QProcessRunner(), []
    r.start([sys.executable, "-c", "import time; time.sleep(0.3); print('done')"], ".",
            lambda code, text: got.append((code, text.strip())))
    assert r.busy()
    r.wait()
    assert not r.busy() and got == [(0, "done")]


def test_a_job_that_cannot_start_ends_as_a_failed_job(app, tmp_path):
    """QProcess sends no finished signal when its program cannot start (a missing interpreter, a blocked one): the
    runner stayed busy and its done never ran, so a card's write never ended -- its Close, off while it writes, the
    menu, the folder box all locked for the session, and a landing scan's wait spun for good (review of the C19
    fixes, fifth round). A start that fails ends the job, as a failed one."""
    from ff9mapkit.workspace.worldforest import QProcessRunner
    r, got = QProcessRunner(), []
    r.start([str(tmp_path / "no-such-python.exe"), "-c", "print(1)"], ".", lambda code, text: got.append((code, text)))
    app.processEvents()
    r.wait()
    assert not r.busy() and len(got) == 1 and got[0][0] != 0 and "could not start" in got[0][1], got


def test_a_card_starts_its_jobs_off_the_window_s_thread(app, tmp_path, monkeypatch):
    """Starting a process on the GUI thread froze the window 0.5-1.2 s in bursts, inside the process start itself
    (QProcess.start: card._run_job held the thread 1.2-1.5 s an Accept, PERF.md tier 2). The cards' and the recipe
    bar's default runner starts its process on a worker thread and hands ``done`` back to the window's thread."""
    import subprocess
    import sys
    import threading
    from ff9mapkit.workspace import worldforest as WF
    from ff9mapkit.workspace.worldrecipe import RecipeBar
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    seen, real = [], subprocess.Popen

    def popen(*a, **k):
        seen.append(threading.current_thread() is threading.main_thread())
        return real(*a, **k)
    monkeypatch.setattr(subprocess, "Popen", popen)
    card = WF.ForestTool(pick_palette("dark"), WorldView3DPanel(pick_palette("dark")), game_fn=lambda: tmp_path,
                         source_fn=lambda: tmp_path / "F", drafts_root=tmp_path / "d", sync=True)
    bar = RecipeBar(pick_palette("dark"), game_fn=lambda: tmp_path, source_fn=lambda: tmp_path / "F",
                    on_changed=lambda d: None, drafts_root=tmp_path / "d")
    for r in (card._runner, bar._runner):
        got = []
        r.start([sys.executable, "-c", "print('done')"], ".", lambda code, text: got.append((code, text.strip())))
        assert r.busy()
        assert r.wait() and not r.busy() and got == [(0, "done")]
    assert seen == [False, False]                                          # each process started on a worker


def test_the_job_runner_keeps_the_runner_s_contract(app, tmp_path):
    """JobRunner: ``done`` runs on the window's thread when the job ends (or inside ``wait``, which says whether it
    ended); ``kill`` ends a job without its done; a program that cannot start ends as a failed job."""
    import sys
    import time
    from ff9mapkit.workspace.worldforest import JobRunner
    r, got = JobRunner(), []
    r.start([sys.executable, "-c", "import time; time.sleep(0.3); print('slow')"], ".",
            lambda code, text: got.append((code, text.strip())))
    t = time.time()
    while not got and time.time() - t < 30:
        app.processEvents()
        time.sleep(0.01)
    assert got == [(0, "slow")] and not r.busy()                           # delivered by the event loop
    got.clear()
    r.start([sys.executable, "-c", "import time; time.sleep(5)"], ".", lambda code, text: got.append(code))
    r.kill()
    assert not r.busy() and r.wait()
    app.processEvents()
    assert got == []                                                       # a killed job's done never runs
    r.start([str(tmp_path / "no-such-python.exe"), "-c", "print(1)"], ".", lambda code, text: got.append((code, text)))
    assert r.wait() and not r.busy() and len(got) == 1 and got[0][0] != 0 and "could not start" in got[0][1]
    r.start([sys.executable, "-c", "raise SystemExit(3)"], ".", lambda code, text: got.append(code))
    r.start([sys.executable, "-c", "print('second')"], ".", lambda code, text: got.append(text.strip()))
    assert r.wait() and got[-1] == "second" and 3 not in got               # a new start kills the running job


def test_the_workspace_closing_shuts_the_world_tab_down(monkeypatch, app):
    """THE CALL SITE: the window's closeEvent is what spends ``WorldDoc.shutdown``."""
    from ff9mapkit import config as cfg
    from ff9mapkit.workspace import shell as S
    monkeypatch.setattr(cfg, "find_game_path",
                        lambda *_a, **_k: (_ for _ in ()).throw(cfg.ConfigError("pinned: no game")))
    win = S.Workspace(S.pick_palette("dark"))
    calls = []
    monkeypatch.setattr(win.world_doc, "shutdown", lambda: calls.append("shutdown"))
    win.close()
    win.deleteLater()
    assert calls == ["shutdown"]


def test_deleting_the_newest_in_game_step_says_the_game_holds_the_rest(monkeypatch, tmp_path, app):
    """A promote after each step; delete the newest. Its promote comes out and the step goes, and the older promotes
    still stand: the game holds the recipe, so there is nothing to promote again -- not an error."""
    import shutil
    _fake_mirror(monkeypatch)
    game = _three_islands(monkeypatch, tmp_path)
    shutil.copytree(game / "FF9CustomMap-world", game / "Hand")
    doc, run = _doc(app, game, tmp_path, tmp_path / "saved.toml")
    doc.set_view_mode("3d", sync=True)
    draft = tmp_path / "drafts" / "FF9CustomMap-world.draft"
    forest = doc.open_forest(sync=True)
    forest.donor_box.setCurrentIndex(forest.donor_box.findData("15,15"))
    _place(forest, 26.0, -26.0)
    forest.close_tool()
    D.promote(draft, game=game, log=lambda *a: None)
    rows1 = D.recipe_rows(draft)
    forest = doc.open_forest(sync=True)
    _place(forest, 410.0, -26.0)
    forest.close_tool()
    D.promote(draft, game=game, log=lambda *a: None)
    bar = doc._recipe
    bar._ask = lambda title, text: True
    bar.refresh()
    doc._on_pick(_hit(410.0, -26.0), sync=True)
    assert bar._sel == 1
    bar.delete_btn.click()
    assert bar.status_lbl.property("state") != "error", bar.status_lbl.text()
    assert "nothing to promote again" in bar.status_lbl.text(), bar.status_lbl.text()
    h = D.history(draft)
    assert h["cursor"] == 1 and h["promoted"] == 1 and D.edits(draft) == [] and D.promote_owed(draft) is None
    assert _tree(game / "FF9CustomMap-world") == _compose(game, rows1, "Hand")


def test_no_card_writes_while_the_chain_writes_the_game(monkeypatch, tmp_path, app):
    """The chain's revert and promote back write the live folder and the draft's records: while they run no card is
    open (its Promote, Revert promote, Discard or Accept would write the same folder or draft at the same moment) and
    none can be opened."""
    game, doc, run, draft, live0 = _promoted(app, monkeypatch, tmp_path)
    bar = doc._recipe
    bar._ask = lambda title, text: True
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    forest = doc.open_forest(sync=True)                                    # a card open, the step still picked
    assert not forest.isHidden() and not bar.delete_btn.isHidden()
    bar._runner = held = _Held(run.argvs)
    bar.delete_btn.click()
    assert held.busy() and "--revert" in held.argvs[-1]
    assert forest.isHidden() and not doc.tools_btn.isEnabled()
    assert doc.open_forest(sync=True) is None and forest.isHidden()
    while held.busy():
        held.wait()
    assert doc.tools_btn.isEnabled() and doc.open_forest(sync=True) is not None
    assert D.history(draft)["promoted"] == 2 and D.promote_owed(draft) is None


def test_an_open_card_is_put_away_when_the_bar_starts_holding_and_the_bar_waits_for_a_writing_card(monkeypatch,
                                                                                                    tmp_path, app):
    """The hold law was kept only at a card's opening: a card already open when the bar began holding -- a Delete's
    put-back, an opened recipe composing -- kept its Accept and Discard, and its Accept swept the bar's pending
    snapshot (the bar then locked the tab for good on a FileNotFoundError) (review of the C19 fixes, fourth round).
    The bar puts every idle card away as it starts holding; and none of its writes (Delete, Edit, Undo, Redo, Open)
    starts while a card writes."""
    game, doc, run, draft = _placed(app, monkeypatch, tmp_path)
    bar = doc._recipe
    bar._ask = lambda title, text: True
    bar.save_btn.click()                                                   # (a recipe for Open)
    doc._on_pick(_hit(26.0, -26.0), sync=True)                             # a step not in the game
    forest = doc.open_forest(sync=True)
    assert not forest.isHidden() and not bar.delete_btn.isHidden()
    bar._runner = held = _Held(run.argvs)
    bar.delete_btn.click()                                                 # its put-back (the mountain composed again)
    assert held.busy() and bar.holding() and forest.isHidden()
    while held.busy():
        held.wait()
    forest = doc.open_forest(sync=True)
    bar.open_btn.click()                                                   # an opened recipe composing
    assert held.busy() and bar.holding() and forest.isHidden()
    while held.busy():
        held.wait()
    forest = doc.open_forest(sync=True)
    forest._ask = lambda title, text: True
    forest._runner = card = _Held([])
    forest._revert() if D.last_promote(draft) else forest._promote()      # the card writes
    assert card.busy() and forest.writing()
    for act, what in ((bar.undo, "undone"), (bar.redo, "redone"), (bar.open_recipe, "opened")):
        act()
        assert "still writing" in bar.status_lbl.text(), (what, bar.status_lbl.text())
    card.wait()


def test_a_scan_that_lands_during_a_card_s_accept_lets_it_commit_to_its_own_folder(monkeypatch, tmp_path, app):
    """A folder pick made just before an Accept lands while it writes: _finish moved the tab to the new folder before
    closing the card, so the Accept's end committed to the new folder's draft (or raised on none), and the draft it
    wrote kept the shape with no record (review of the C19 fixes, fourth round). A landing scan waits for the cards'
    writes first. And an edit's Cancel is not offered while its Accept writes: waiting turned a cancel into an accept."""
    import shutil
    from ff9mapkit.workspace import worldscan
    game = _three_islands(monkeypatch, tmp_path)
    shutil.copytree(game / "FF9CustomMap-world", game / "Hand")
    doc, run = _doc(app, game, tmp_path, tmp_path / "saved.toml")
    doc.set_view_mode("3d", sync=True)
    forest = doc.open_forest(sync=True)
    forest.donor_box.setCurrentIndex(forest.donor_box.findData("15,15"))
    forest._runner = held = _Held([])
    forest.place(26.0, -26.0, 3.2)
    forest._timer.stop()
    forest._check()
    held.wait()                                                            # the check
    forest.accept_btn.click()
    assert held.busy() and not forest.close_btn.isEnabled()
    doc._finish(worldscan.scan_tree(game / "Hand"), None, None)           # the scan lands: Hand is shown now
    draft = tmp_path / "drafts" / "FF9CustomMap-world.draft"
    assert not held.busy() and D.history(draft)["cursor"] == 1
    assert not (tmp_path / "drafts" / "Hand.draft").exists()


def test_a_refusal_of_the_bar_s_tells_no_one_the_draft_moved(monkeypatch, tmp_path, app):
    """The bar's refusals (a card still writing, steps after the game's out of it) went through the draft-moved
    path: every card's island re-read, the draw box set to the draft, the 3D view reloaded from a draft mid-write --
    whose own reload, when the write ended, the busy view then dropped (review of the C19 fixes, fifth round). A
    refusal moves nothing, and says so to no one but the bar."""
    game, doc, run, draft = _placed(app, monkeypatch, tmp_path)
    bar = doc._recipe
    moved = []
    bar._on_changed = moved.append
    forest = doc.open_forest(sync=True)
    forest._ask = lambda title, text: True
    forest._runner = held = _Held([])
    forest._promote()                                                      # the card writes
    for act in (bar.undo, bar.redo, bar.open_recipe):
        act()
    bar.select(0)
    bar.edit()
    assert "still writing" in bar.status_lbl.text() and moved == []
    held.wait()


def test_a_card_that_writes_is_never_closed_under_its_job(monkeypatch, tmp_path, app):
    """Closing a card kills its job, and the view toggle, the menu (one card at a time), a Rescan and a folder pick all
    close cards: a card's Promote or Revert promote cut off half way left the live folder half written with no
    record to revert from (review of the C19 fixes, third round). While a card writes, those controls wait; and a
    card closed anyway (a scan landing, a call from code) waits for its write to end instead of killing it."""
    _fake_mirror(monkeypatch)
    game, doc, run, draft = _placed(app, monkeypatch, tmp_path)
    forest = doc.open_forest(sync=True)
    forest._ask = lambda title, text: True
    forest._runner = held = _Held([])
    forest._promote()                                                      # the card's Promote, running
    assert held.busy() and forest.writing()
    for w in (doc.tools_btn, doc.view3d_btn, doc.folder_box, doc.rescan_btn):
        assert not w.isEnabled(), w.text() if hasattr(w, "text") else w
    doc.set_view_mode("2d", sync=True)                                    # closed anyway, from code
    assert not held.busy() and forest.isHidden()                           # its promote ran to its end
    assert D.last_promote(draft) is not None and D.history(draft)["promoted"] == 3
    for w in (doc.tools_btn, doc.view3d_btn, doc.folder_box, doc.rescan_btn):
        assert w.isEnabled()


def test_no_other_card_opens_while_the_bar_holds_the_draft(monkeypatch, tmp_path, app):
    """While an edit is open or its steps go back on top, another card could be opened from the menu: opening it
    closed the editing card (whose cancel then started the promote back under the new card), or, during the
    put-back, the new card's Accept or Discard wrote the draft under the open edit -- a Discard deleted the draft
    and what the game was owed, leaving the game reverted for good (review of the C19 fixes, third round). While the
    bar holds the draft, the menu waits, and no card opens but the edit's own."""
    game, doc, run, draft, live0 = _promoted(app, monkeypatch, tmp_path)
    bar = doc._recipe
    bar._ask = lambda title, text: True
    rows0 = D.recipe_rows(draft)
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    bar.edit_btn.click()                                                   # the in-game edit, open
    forest = doc._forest
    assert forest.editing() and not doc.tools_btn.isEnabled()
    n = len(run.argvs)
    assert doc.open_mountain(sync=True) is None and forest.editing() and run.argvs[n:] == []
    bar._runner = held = _Held(run.argvs)                                  # the put-back's world-fuse, held
    forest.drop_at(30.0, -30.0)
    forest._timer.stop()
    forest._check()
    forest.accept_btn.click()
    assert held.busy() and bar.holding() and not doc.tools_btn.isEnabled()
    assert doc.open_mountain(sync=True) is None
    while held.busy():
        held.wait()
    assert doc.tools_btn.isEnabled() and not bar.holding()
    rows = D.recipe_rows(draft)
    assert rows == [{**rows0[0], "center": [30.0, -30.0]}] + rows0[1:]
    assert _tree(game / "FF9CustomMap-world") == _compose(game, rows, "Hand")
    assert doc.open_mountain(sync=True) is not None


def test_no_edit_or_delete_starts_while_a_card_writes(monkeypatch, tmp_path, app):
    """Starting the chain closed every open card, and closing a card kills its job: a card's Revert promote (a
    world-promote on the live folder) was cut off half way, and the chain reverted over the result (review of the
    C19 fixes). While a card writes -- its Accept, Promote or Revert promote -- the bar's Edit and Delete refuse, and
    the card and its job are left alone; once it is done they run."""
    game, doc, run, draft, live0 = _promoted(app, monkeypatch, tmp_path)
    bar = doc._recipe
    bar._ask = lambda title, text: True
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    forest = doc.open_forest(sync=True)
    forest._ask = lambda title, text: True
    forest._runner = held = _Held([])
    forest._revert()                                                      # the card's Revert promote, running
    assert held.busy() and "--revert" in held.argvs[-1]
    n = len(run.argvs)
    for act in (bar.edit, bar.delete):
        act()
        assert "still writing" in bar.status_lbl.text() and bar.status_lbl.property("state") == "error"
    assert run.argvs[n:] == [] and not forest.isHidden() and held.busy() and bar._edit is None
    held.wait()                                                            # the card's revert ends
    bar.select(0)
    bar.delete()
    assert "still writing" not in bar.status_lbl.text()


# ---- each recovery branch of the chain, driven (each was broken on purpose, in memory, and its test went red)
def _promotes_after(run, n):
    return [a for a in run.argvs[n:] if a[5] == "world-promote"]


def test_a_cancel_that_cannot_undo_the_draft_never_promotes_it(monkeypatch, tmp_path, app):
    """THE GUARD: an in-game step's edit whose cancel fails leaves a draft not known to be as it was, and such a draft
    is never promoted into the game: the bar says so, and nothing is left owed (it would retry at every launch)."""
    game, doc, run, draft, live0 = _promoted(app, monkeypatch, tmp_path)
    bar = doc._recipe
    bar._ask = lambda title, text: True
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    bar.edit_btn.click()
    n = len(run.argvs)

    def fails(_d):
        raise ValueError("a file of the draft could not be written back")
    monkeypatch.setattr(D, "cancel_edit", fails)
    doc._forest.close_btn.click()                                          # Cancel edit
    assert _promotes_after(run, n) == []
    assert bar.status_lbl.property("state") == "error" and "could not be undone" in bar.status_lbl.text()
    assert D.promote_owed(draft) is None


def test_a_promote_back_that_refuses_says_the_game_lacks_the_recipe(monkeypatch, tmp_path, app):
    """Another session wrote the live folder at the edited step's block while the edit was open: the promote back
    refuses (it would overwrite that work), the bar says the game does not have the recipe, and nothing is left owed
    (it would retry at every launch)."""
    game, doc, run, draft, live0 = _promoted(app, monkeypatch, tmp_path)
    bar = doc._recipe
    bar._ask = lambda title, text: True
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    bar.edit_btn.click()
    (game / "FF9CustomMap-world" / T00).write_bytes(b"another session's edit")
    doc._forest.close_btn.click()                                          # Cancel edit
    text = bar.status_lbl.text()
    assert bar.status_lbl.property("state") == "error" and "Promoting it again did not run" in text, text
    assert "does not have the recipe" in text
    h = D.history(draft)
    assert h["cursor"] == 3 and h["promoted"] == 0 and D.promote_owed(draft) is None


def test_a_step_marked_in_the_game_with_no_promote_record_refuses_and_changes_nothing(monkeypatch, tmp_path, app):
    game, doc, run, draft, live0 = _promoted(app, monkeypatch, tmp_path)
    bar = doc._recipe
    bar._ask = lambda title, text: True
    for rec in (draft / D.PROMOTES).glob("*/promote.json"):
        rec.unlink()                                                       # the record gone, the mark still there
    h0 = D.history(draft)
    n = len(run.argvs)
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    bar.edit_btn.click()
    text = bar.status_lbl.text()
    assert "holds no promote to revert" in text and "as they were" in text, text
    assert _promotes_after(run, n) == [] and D.history(draft) == h0 and D.promote_owed(draft) is None
    assert _tree(game / "FF9CustomMap-world") == live0


def test_an_edit_that_will_not_open_after_the_reverts_promotes_the_game_back(monkeypatch, tmp_path, app):
    game, doc, run, draft, live0 = _promoted(app, monkeypatch, tmp_path)
    bar = doc._recipe
    bar._ask = lambda title, text: True

    def refuses(_d, _k):
        raise ValueError("an edit is already open in the draft")
    monkeypatch.setattr(D, "begin_edit", refuses)
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    bar.edit_btn.click()
    text = bar.status_lbl.text()
    assert "Not opened: an edit is already open" in text and "again" in text, text
    assert _tree(game / "FF9CustomMap-world") == live0
    assert D.history(draft)["promoted"] == 3 and D.promote_owed(draft) is None


def _unpromoted_fourth(draft):
    """A fourth step in the draft that was never promoted."""
    (draft / FAR).parent.mkdir(parents=True, exist_ok=True)
    _step(draft, [(10, 5)], {FAR: b"a fourth step, never promoted"}, _row(672, -352), "a fourth step")


@pytest.mark.parametrize("second_promote", [False, True])
def test_an_in_game_step_does_not_open_while_steps_after_the_game_s_are_out_of_it(monkeypatch, tmp_path, app,
                                                                                   second_promote):
    """A step placed after the last promote is not in the game. The chain's promote back writes the whole draft, so
    with such a step on top it pushed that step into the game (even on Cancel); setting it aside by undo and redo
    instead broke where its blocks met a promote's (review of C19, twice). So an in-game step opens (or is deleted)
    only with nothing after the game's on top: the bar says so, and runs nothing. Undo or Promote them, and it opens."""
    game, doc, run, draft, _live0 = _promoted(app, monkeypatch, tmp_path)
    bar = doc._recipe
    bar._ask = lambda title, text: True
    if second_promote:                                                     # P1 = steps 1-3, P2 = step 4, then 5
        _unpromoted_fourth(draft)
        D.promote(draft, game=game, log=lambda *a: None)
        far2 = "FF9_Data/WorldMap/Disc1/0_1/r6/Block[12][6] Terrain.ff9mesh"
        (draft / far2).parent.mkdir(parents=True, exist_ok=True)
        _step(draft, [(12, 6)], {far2: b"a fifth step, never promoted"}, _row(800, -416), "a fifth step")
    else:
        _unpromoted_fourth(draft)
    bar.refresh()
    live, h0, n = _tree(game / "FF9CustomMap-world"), D.history(draft), len(run.argvs)
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    assert bar._sel == 0 and not bar.edit_btn.isEnabled() and not bar.delete_btn.isEnabled()
    assert "not in the game" in bar.edit_btn.toolTip() and "not in the game" in bar.status_lbl.text()
    for act in (bar.edit, bar.delete):                                     # (the law at the call site too)
        act()
        assert "not in the game" in bar.status_lbl.text() and bar.status_lbl.property("state") == "error"
    assert run.argvs[n:] == [] and D.history(draft) == h0 and D.promote_owed(draft) is None
    assert _tree(game / "FF9CustomMap-world") == live and not (doc._forest and doc._forest.editing())
    bar.undo_btn.click()                                                   # the step after the game's: undone
    doc._on_pick(_hit(26.0, -26.0), sync=True)
    assert bar.edit_btn.isEnabled()
    bar.edit_btn.click()
    assert doc._forest.editing()


def test_a_job_s_done_follows_its_exit_not_its_pipe(app):
    """JobRunner's done waited for pipe EOF (communicate): a process that inherited the job's output pipe -- a
    QProcess the shell started in the Popen window, or a child the job left running -- held the done, and with it
    the card's writing(), its Close and the tab's locks, for that other process's whole life (review of the perf
    commits, J1). The done follows the job's own exit, its output read from a file."""
    import sys
    import time
    from ff9mapkit.workspace.worldforest import JobRunner
    r, got = JobRunner(), []
    leaves = ("import subprocess, sys; subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(8)']); "
              "print('parent done')")                                     # a child that outlives the job, our stdout
    t = time.time()
    r.start([sys.executable, "-c", leaves], ".", lambda code, text: got.append((code, text.strip())))
    assert r.wait(30000) and got == [(0, "parent done")]
    assert time.time() - t < 6                                             # not the 8 s the left child lives


def test_a_done_that_raises_does_not_leave_the_wait(app, monkeypatch):
    """JobRunner.wait and StepWorker.wait ran a done straight from Python, so a done that raised (a commit_step's
    PermissionError, a settle write) left wait() -- and WorldDoc.shutdown's loop, which waits every writing job one
    after another, with the bar's job never waited for (review of the perf commits, J2). As QProcessRunner's done
    did inside Qt's emission, the error is reported and the wait goes on."""
    import sys
    from ff9mapkit.workspace.worldforest import JobRunner, StepWorker
    seen = []
    monkeypatch.setattr(sys, "excepthook", lambda *exc: seen.append(exc[0]))

    def boom(*_a):
        raise PermissionError(13, "a reader holds it")
    r = JobRunner()
    r.start([sys.executable, "-c", "pass"], ".", boom)
    assert r.wait() and not r.busy()
    s = StepWorker()
    s.start(lambda: None, boom)
    assert s.wait() and not s.busy()
    assert seen == [PermissionError, PermissionError]


def test_any_failed_start_ends_the_job(app):
    """Only an OSError from the start ended a JobRunner job as a failed one; any other (a ValueError for a NUL in an
    argument) killed the worker with no result: busy for good, done never run, and wait() saying it ended (review of
    the perf commits, J4). A job always ends."""
    import sys
    from ff9mapkit.workspace.worldforest import JobRunner
    r, got = JobRunner(), []
    r.start([sys.executable, "-c", "print('a\x00b')"], ".", lambda code, text: got.append((code, text)))
    assert r.wait() and not r.busy() and len(got) == 1 and got[0][0] == -1 and "could not start" in got[0][1]

