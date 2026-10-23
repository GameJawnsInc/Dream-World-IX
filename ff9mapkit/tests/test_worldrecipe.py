"""The overworld editor's recipe (rung C3): the draft's history (undo and redo byte for byte), the recipe rows the
editor writes, their order through ``world-fuse`` (``step``), the ``[[sink]]`` row, the World tab's recipe bar, and
THE C3 ACCEPTANCE: a recipe the editor saved, composed by the CLI onto the folder the draft was made from, writes the
editor's bytes."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from ff9mapkit.world import draft as D
from ff9mapkit.world import fuse as FU
from ff9mapkit.world import interior as IN
from ff9mapkit.world import mesh as M
from ff9mapkit.world import recipe as RC

from .test_world_forestedit import _fake_mirror, _game, _mod, _no_real_install  # noqa: F401
from .test_world_interior import _canopy_dome, _mains_grid, _mountain_bench, _patch_donor, _pyramid_donor

T00 = "FF9_Data/WorldMap/Disc1/0_1/r0/Block[0][0] Terrain.ff9mesh"
T10 = "FF9_Data/WorldMap/Disc1/0_1/r0/Block[1][0] Terrain.ff9mesh"


def _tree(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in (root / "FF9_Data" / "WorldMap").rglob("*.ff9mesh") if ".bak-" not in p.name}


# ---------------------------------------------------------------- the history
def _draft(tmp_path):
    game = _game(tmp_path)
    src = _mod(game, "Src", ((0, 0), (1, 0)))
    return game, src, D.ensure_draft(src, game=game, root=tmp_path / "drafts")


def _step(d, cells, writes, label):
    D.begin_step(d, cells)
    for rel, data in writes.items():
        (d / rel).parent.mkdir(parents=True, exist_ok=True)
        if data is None:
            (d / rel).unlink()
        else:
            (d / rel).write_bytes(data)
    return D.commit_step(d, {"table": "forest", "center": [1.0, -1.0], "donor": "15,15"}, label)


def test_undo_and_redo_walk_the_steps_byte_for_byte(tmp_path):
    _game_, _src, d = _draft(tmp_path)
    orig = _tree(d)
    new = "FF9_Data/WorldMap/Disc1/0_1/r0/Block[1][0] Object.ff9mesh"
    s1 = _step(d, [(0, 0), (5, 5)], {T00: b"forest"}, "forest one")
    assert s1["cells"] == [[0, 0]] and set(s1["after"]) == {T00}      # only the cells it changed are kept
    _step(d, [(1, 0)], {T10: b"mountain", new: b"its object"}, "mountain two")
    after2 = _tree(d)
    assert D.recipe_rows(d) == [{"table": "forest", "center": [1.0, -1.0], "donor": "15,15"}] * 2
    assert D.undo(d)["label"] == "mountain two"
    assert _tree(d) == {**orig, T00: b"forest"} and not (d / new).exists()    # the file it made is gone again
    assert D.undo(d)["label"] == "forest one" and _tree(d) == orig
    with pytest.raises(ValueError, match="nothing to undo"):
        D.undo(d)
    D.redo(d)
    D.redo(d)
    assert _tree(d) == after2
    with pytest.raises(ValueError, match="nothing to redo"):
        D.redo(d)
    D.undo(d)                                           # an edit after an undo drops the undone step
    _step(d, [(1, 0)], {T10: b"another"}, "mountain three")
    h = D.history(d)
    assert [s["label"] for s in h["steps"]] == ["forest one", "mountain three"] and h["cursor"] == 2
    assert D.edits(d) == [T00, T10]


def test_undo_refuses_a_step_whose_files_moved_and_abort_puts_the_cells_back(tmp_path):
    _game_, _src, d = _draft(tmp_path)
    _step(d, [(0, 0)], {T00: b"forest"}, "forest one")
    (d / T00).write_bytes(b"someone else")
    with pytest.raises(ValueError, match="changed since it was applied"):
        D.undo(d)
    before = _tree(d)
    D.begin_step(d, [(1, 0)])
    (d / T10).write_bytes(b"half a write")
    D.abort_step(d)
    assert _tree(d) == before and D.history(d)["cursor"] == 1


def test_a_promote_fences_undo_and_its_revert_lifts_the_fence(monkeypatch, tmp_path):
    _fake_mirror(monkeypatch)
    game, src, d = _draft(tmp_path)
    _step(d, [(0, 0)], {T00: b"forest"}, "forest one")
    D.promote(d, game=game, log=lambda *a: None)
    assert D.history(d)["promoted"] == 1
    with pytest.raises(ValueError, match="Revert promote first"):
        D.undo(d)
    _step(d, [(1, 0)], {T10: b"mountain"}, "mountain two")
    D.undo(d)                                           # above the fence: fine
    D.revert(d, game=game, log=lambda *a: None)
    assert D.history(d)["promoted"] == 0
    D.undo(d)
    assert (d / T00).read_bytes() == (src / T00).read_bytes()


# ---------------------------------------------------------------- the rows and the document
def test_a_row_is_the_command_it_was_built_from():
    from ff9mapkit.world import forestedit as FE
    from ff9mapkit.world import mountainedit as ME
    assert RC.row_for(FE.command("-", (26.0, -26.0), (15, 15), dry_run=False)) == \
        {"table": "forest", "center": [26.0, -26.0], "donor": "15,15"}
    assert RC.row_for(FE.command("-", (26.0, -26.0), (3, 12), spread=1.25, rot_deg=90, dry_run=False)) == \
        {"table": "forest", "center": [26.0, -26.0], "donor": "3,12", "rot": 90.0, "spread": 1.25}
    assert RC.row_for(ME.command("-", (190.0, -1228.0), "5-6,15-16", rot_deg=300, spread=1.1, rock_height=1.5,
                                 ground="desert", reach=112.0, dry_run=False)) == \
        {"table": "mountain", "center": [190.0, -1228.0], "donor": "5-6,15-16", "rot": 300.0, "spread": 1.1,
         "reach": 112.0, "rock_height": 1.5, "ground": "desert"}
    with pytest.raises(ValueError, match="exact placement"):
        RC.row_for(["world-forest", "--mod-folder", "-", "--near", "1,2"])
    assert RC.label({"table": "mountain", "center": [190.0, -1228.0], "donor": "0,0"}) == \
        "mountain uaho at 190, -1228"


def test_a_recipe_keeps_the_order_its_rows_were_made_in():
    rows = [{"table": "forest", "center": [26.0, -26.0], "donor": "15,15"},
            {"table": "mountain", "center": [90.5, -26.0], "donor": "0,0", "rot": 30.0, "ground": "snow"},
            {"table": "forest", "center": [40.0, -40.0], "donor": "15,15", "spread": 1.2}]
    text = RC.dumps(rows, base="Src")
    assert "world-fuse <this file> --mod-folder <folder>" in text and "# Made on Src" in text
    assert RC.loads(text) == rows                       # forest, mountain, forest: not mountains first
    import tomllib
    plain = {k: [{kk: vv for kk, vv in r.items() if kk != "step"} for r in v]
             for k, v in tomllib.loads(text).items()}
    assert [t for t, _i, _r in FU.ordered_rows(plain)] == ["mountain", "forest", "forest"]   # without steps: tiers
    with pytest.raises(ValueError, match="whole number"):
        FU.ordered_rows({"forest": [{"center": [0, 0], "step": 1.5}]})
    with pytest.raises(ValueError, match="placement"):
        RC.loads('[[placement]]\ncell = [1, 2]\ndonor = [3, 4]\nsize = [1, 1]\n')


def test_a_relief_row_s_cells_are_its_read_window():
    cells = RC.row_cells({"table": "forest", "center": [26.0, -26.0]})
    assert (0, 0) in cells and (1, 0) in cells and (23, 0) in cells     # 96u west of x 26 wraps to column 23
    assert all(0 <= by <= 19 for _bx, by in cells)
    assert len(RC.row_cells({"table": "island", "center": [26.0, -26.0]})) == 480


# ---------------------------------------------------------------- [[sink]]
def test_the_sink_row_is_world_sink_with_its_disc4_replay(monkeypatch, tmp_path):
    """A [[sink]] row calls transplant.sink as `world-sink` does, with the replay that re-runs the same sink on
    disc 4 (skip_mirror REPLAY), and refuses an unclean sink by naming its gates."""
    from ff9mapkit import cli
    from ff9mapkit.world import discmirror as DM
    from ff9mapkit.world import transplant as TR
    game = _game(tmp_path)
    (game / "MOD").mkdir()
    calls = []

    def fake_sink(mod_folder, at, *, disc=1, replay=None, **kw):
        calls.append((mod_folder, at, disc, {k: v for k, v in kw.items()}))
        if disc == 1 and replay is not None:
            replay(4)
        return {"clean": True, "land_tris": 1, "land_u2": 2.0, "max_y": 1.0, "blocks": [(3, 4)], "per_block": {},
                "tiles": 1, "bands": {}, "fill_tris": 1, "fill_area": 1.0, "sea_replaced": 0, "edge_welds": 0,
                "keel_to_open": 0, "shore_tris": 0, "entrance_tris": 0, "deployed": []}
    monkeypatch.setattr(TR, "sink", fake_sink)
    FU.compose_layout("MOD", {"sink": [{"at": [510.0, -300.0], "cluster": True}]}, game=game)
    by_row = list(calls)
    calls.clear()
    assert cli.main(["--game", str(game), "world-sink", "--mod-folder", "MOD", "--at", "510", "-300",
                     "--cluster"]) == 0
    assert [(c[1], c[2]) for c in by_row] == [(c[1], c[2]) for c in calls] == [((510.0, -300.0), 1),
                                                                               ((510.0, -300.0), 4)]
    for row_kw, cli_kw in zip((c[3] for c in by_row), (c[3] for c in calls)):
        keys = ("dry_run", "fresh", "allow_overwrite", "allow_entrances", "cluster", "skip_mirror")
        assert {k: row_kw.get(k) for k in keys} == {k: cli_kw.get(k) for k in keys}
    assert by_row[1][3]["skip_mirror"] == DM.REPLAY
    monkeypatch.setattr(TR, "sink", lambda *a, **k: {"clean": False, "per_block": {
        (3, 4): {"gates": [{"gate": "census", "ok": False}]}}})
    out = FU.compose_layout("MOD", {"sink": [{"at": [510.0, -300.0]}]}, game=game)
    assert not out["clean"] and "census" in out["gates"][-1]["error"]


# ---------------------------------------------------------------- the World tab: the bar, and THE C3 ACCEPTANCE
@pytest.fixture(scope="module")
def app():
    pytest.importorskip("PySide6", reason="GUI extra not installed")    # the GUI half only: the kit half runs anyway
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


class InProcess:
    """What the subprocess runs, run here (the same argv, cli.main in this process)."""

    def __init__(self):
        self.argvs = []

    def start(self, argv, cwd, done):
        from ff9mapkit import cli
        self.argvs.append([str(a) for a in argv])
        done(cli.main([str(a) for a in argv[3:]]), "")

    def kill(self):
        pass

    def busy(self):
        return False


def _two_islands(monkeypatch, tmp_path):
    """FF9CustomMap-world: a forest bench in block (0,0) and a mountain bench in block (1,0); the canopy dome is the
    donor at (15,15), the rock pyramid at (0,0)."""
    _patch_donor(monkeypatch, {(15, 15): _canopy_dome(), (0, 0): _pyramid_donor()})
    game = _game(tmp_path)
    M.deploy_override(_mains_grid(), mod_folder="FF9CustomMap-world", game=game, part="Terrain", disc=1)
    bench = _mountain_bench()
    bench.name, bench.x = "Block[1][0] Terrain", 1
    M.deploy_override(bench, mod_folder="FF9CustomMap-world", game=game, part="Terrain", disc=1)
    return game


def _doc(app, game, tmp_path, saved):
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worlddoc import WorldDoc
    run = InProcess()
    doc = WorldDoc(pick_palette("dark"), game_path_fn=lambda: game, drafts_root=tmp_path / "drafts",
                   forest_runner=run, forest_seams={"sync": True}, mountain_runner=run, mountain_seams={"sync": True},
                   recipe_runner=run, recipe_seams={"ask": lambda t, x: True, "save_path_fn": lambda d: saved,
                                                    "open_path_fn": lambda: saved})
    doc._census, doc._game = SimpleNamespace(root=game / "FF9CustomMap-world"), game
    return doc, run


def _place(tool, x, z, **handles):
    for name, value in handles.items():
        getattr(tool, name).setValue(value)
    tool.place(x, z, 3.2)
    tool._timer.stop()
    tool._check()
    assert tool.accept_btn.isEnabled(), tool.verdict_lbl.text()
    tool.accept_btn.click()


def test_the_recipe_the_editor_saves_composes_to_the_editor_s_bytes(monkeypatch, tmp_path, app):
    """THE C3 ACCEPTANCE: a forest, then a turned and heightened mountain, placed through the World tab; the
    mountain undone and redone; the recipe saved. `world-fuse` on a copy of the folder the draft was made from
    writes the draft's world files byte for byte, and the recipe, opened again, composes the same draft, one
    undoable step per row."""
    from ff9mapkit import cli
    game = _two_islands(monkeypatch, tmp_path)
    shutil.copytree(game / "FF9CustomMap-world", game / "Hand")
    saved = tmp_path / "saved-recipe.toml"
    doc, run = _doc(app, game, tmp_path, saved)
    doc.set_view_mode("3d", sync=True)
    bar = doc._recipe
    assert not bar.isHidden() and not bar.undo_btn.isEnabled() and "No edits yet" in bar.status_lbl.text()
    forest = doc.open_forest(sync=True)
    forest.donor_box.setCurrentIndex(forest.donor_box.findData("15,15"))
    _place(forest, 26.0, -26.0)
    mountain = doc.open_mountain(sync=True)
    _place(mountain, 90.0, -26.0, angle=30, rock_height=1.5)
    draft = tmp_path / "drafts" / "FF9CustomMap-world.draft"
    edited = _tree(draft)
    assert "2 steps, the last mountain uaho at 90, -26" in bar.status_lbl.text()
    assert bar.undo_btn.toolTip() == "Undo: mountain uaho at 90, -26"
    bar.undo_btn.click()
    assert _tree(draft) != edited and "Undone: mountain uaho" in bar.status_lbl.text()
    assert bar.redo_btn.isEnabled() and mountain._verdict is None             # the tools read the draft again
    bar.redo_btn.click()
    assert _tree(draft) == edited
    bar.save_btn.click()
    text = saved.read_text(encoding="utf-8")
    assert RC.loads(text) == [{"table": "forest", "center": [26.0, -26.0], "donor": "15,15"},
                              {"table": "mountain", "center": [90.0, -26.0], "donor": "0,0", "rot": 30.0,
                               "rock_height": 1.5}]

    assert cli.main(["--game", str(game), "world-fuse", str(saved), "--mod-folder", "Hand"]) == 0
    hand = _tree(game / "Hand")
    assert hand == edited and hand != _tree(game / "FF9CustomMap-world")        # the recipe IS the draft
    assert not (game / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / FU._MANIFEST_NAME).exists()

    bar.open_btn.click()                                # the recipe again, into a fresh draft, a job per row
    assert [a[5] for a in run.argvs[-2:]] == ["world-fuse", "world-fuse"]
    assert _tree(draft) == edited
    h = D.history(draft)
    assert [s["label"] for s in h["steps"]] == [RC.label(r) for r in RC.loads(text)]
    assert h["cursor"] == 2 and "Composed saved-recipe.toml: 2 rows" in bar.status_lbl.text()
    bar.undo_btn.click()
    bar.undo_btn.click()
    assert _tree(draft) == _tree(game / "FF9CustomMap-world")                   # all the way back to the folder


def test_a_recipe_row_that_refuses_stops_the_open_and_keeps_the_rows_before_it(monkeypatch, tmp_path, app):
    game = _two_islands(monkeypatch, tmp_path)
    saved = tmp_path / "bad.toml"
    saved.write_text(RC.dumps([{"table": "forest", "center": [26.0, -26.0], "donor": "15,15"},
                               {"table": "mountain", "center": [300.0, -300.0], "donor": "0,0"}]), encoding="utf-8")
    doc, _run = _doc(app, game, tmp_path, saved)
    doc.set_view_mode("3d", sync=True)
    doc._recipe.open_btn.click()
    draft = tmp_path / "drafts" / "FF9CustomMap-world.draft"
    assert D.history(draft)["cursor"] == 1 and "Stopped at mountain uaho at 300, -300" in \
        doc._recipe.status_lbl.text()
    assert doc._recipe.status_lbl.property("state") == "error"
    assert json.loads((draft / D.HISTORY).read_text())["steps"][0]["row"]["table"] == "forest"
