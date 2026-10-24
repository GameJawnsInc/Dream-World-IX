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
    # THE SAID-BACK LAW (rung C12): an edit opens only on a row its card builds again, key for key -- a hand-written
    # centre off the editor's 0.1u grid would otherwise move the shape before the author touched a handle
    with pytest.raises(ValueError, match="would not say its center back as the step has it"):
        doc.open_hill(sync=True).edit_row({"table": "hill", "center": [26.04, -26.0]}, label="hill",
                                          on_accepted=lambda: None, on_cancel=lambda note=None: None)
    assert set(RC.EDITABLE_TABLES) == set(doc.EDIT_CARDS) == set(RC.EDITOR_TABLES)    # every table the editor writes


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
    assert len(RC.replay_window({"row": {"table": "morph", "cell": [3, 4]}, "cells": [[3, 4]]})) == 480
    assert len(RC.replay_window({"row": {"table": "river", "at": [512.0, 128.0]}, "cells": []})) == 480


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


def test_on_real_bytes_an_island_a_carry_and_a_sink_read_only_their_window(monkeypatch, tmp_path):
    """THE C11 FENCE: each verb, run for real on its own draft of the real FF9CustomMap-world at a target its card
    calls lawful, reads no block of that draft outside ``recipe.replay_window`` -- so a step whose window no edit
    touched may replay from its record. A verb that starts reading wider goes red here."""
    if REAL_GAME is None or not (REAL_GAME / "FF9CustomMap-world").is_dir():
        import warnings
        warnings.warn("the read windows went unchecked on real bytes: no FF9 install + UnityPy + FF9CustomMap-world. "
                      "Re-run in the MAIN repo (C:/gd/Dream-World-IX/ff9mapkit).", UserWarning)
        pytest.skip("needs the FF9 install + UnityPy + FF9CustomMap-world")
    import json
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
    assert len(cases) == 4, [k for k, _a in cases]
    for name, argv in cases:
        d = D.ensure_draft(src, game=REAL_GAME, root=tmp_path / name)
        argv = [str(d) if a == "D" else a for a in argv]
        rep = tmp_path / f"{name}.json"
        with monkeypatch.context() as mp:
            seen, blocks = _reads(mp, d)
            assert cli.main(["--game", str(REAL_GAME)] + argv + ["--report-json", str(rep)]) == 0, name
            read = blocks()
        v = json.loads(rep.read_text(encoding="utf-8"))
        step = {"row": RC.row_for([a if a != str(d) else "-" for a in argv]),
                "cells": [list(b[1:]) for b in D.edited_blocks(d) if b[0] == 1] or v.get("blocks") or []}
        window = RC.replay_window(step)
        assert read, (name, seen[:5])                     # the recorder saw the verb's reads at all
        assert read <= window, (name, sorted(read - window), sorted(window))


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
