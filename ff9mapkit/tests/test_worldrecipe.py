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


def _aged(d, seconds=60):
    """Every draft file last written ``seconds`` ago (a draft in use: its files were not written this instant)."""
    import time
    then = time.time_ns() - seconds * 10 ** 9
    for p in (d / "FF9_Data").rglob("*"):
        if p.is_file():
            os.utime(p, ns=(then, then))


def test_a_step_reads_and_writes_back_only_the_files_that_moved(monkeypatch, tmp_path):
    """A whole-map step (a sink Accept, a recipe's island or carry row) snapshots 480 cells and 2,088 files, and its
    commit read every one again and its abort wrote every one back: 10-36 s frozen per sink Accept, and an abort
    moved every file's time, so the 3D view drew the whole map again (PERF.md 3). A file whose size and time stand
    since begin_step is the bytes it snapshotted: commit reads only what moved, abort writes back only what moved."""
    _game_, _src, d = _draft(tmp_path)
    _aged(d)
    reads, real = [], Path.read_bytes
    monkeypatch.setattr(Path, "read_bytes", lambda p: reads.append(p.relative_to(d).as_posix()
                                                                   if p.is_relative_to(d) else str(p)) or real(p))
    D.begin_step(d, D.all_cells())
    (d / T00).write_bytes(b"forest")
    reads.clear()
    rec = D.commit_step(d, {"table": "forest", "center": [1.0, -1.0], "donor": "15,15"}, "forest one")
    assert rec["cells"] == [[0, 0]] and set(rec["after"]) == {T00}
    assert T10 not in reads                                               # it did not move: not read again
    _aged(d)                                                              # (T00 was just written: racy, hashed)
    D.begin_step(d, D.all_cells())
    (d / T10).write_bytes(b"half a write")
    t00 = os.stat(d / T00).st_mtime_ns
    D.abort_step(d)
    assert (d / T10).read_bytes() == real(_src / T10) and os.stat(d / T00).st_mtime_ns == t00   # T00 not rewritten


def test_a_file_written_the_instant_before_a_step_is_read_again(tmp_path):
    """THE RACY-CLEAN RULE (git's): a file written in the same clock tick as begin_step's stat can be written again
    at the same size and time. Only a file older than the window is trusted by its stat; a younger one is hashed."""
    _game_, _src, d = _draft(tmp_path)                                    # ensure_draft wrote its files just now
    st = os.stat(d / T00)
    D.begin_step(d, [(0, 0)])
    same = bytes(b ^ 0xFF for b in (d / T00).read_bytes())                # other bytes, the same size...
    (d / T00).write_bytes(same)
    os.utime(d / T00, ns=(st.st_atime_ns, st.st_mtime_ns))                # ...and the same time (one clock tick)
    rec = D.commit_step(d, {"table": "forest", "center": [1.0, -1.0], "donor": "15,15"}, "forest one")
    assert set(rec["after"]) == {T00}                                     # still seen: the step holds the change
    D.undo(d)
    assert (d / T00).read_bytes() == (_src / T00).read_bytes()


def test_cell_files_lists_what_one_glob_per_cell_lists(tmp_path):
    """_cell_files reads one listing per row directory (it globbed once per cell and disc: 960 globs a whole-map
    step). The same files: every part and sidecar of the cells, no backups, no promote leftovers, no neighbours."""
    root = tmp_path / "F"
    names = ["Block[1][1] Terrain.ff9mesh", "Block[1][1] Donor.txt", "Block[1][1] Sea4.ff9mesh.bak-2026",
             "Block[1][1] Object.ff9mesh.promoting", "Block[11][1] Terrain.ff9mesh", "Block[1][11] Terrain.ff9mesh",
             "Block[2][1] Terrain.ff9mesh", "Block[1][1]Terrain.ff9mesh"]
    for disc in (1, 4):
        for lod in ("0_1", "1_1"):
            for row, ns in ((1, names), (11, ["Block[1][11] Terrain.ff9mesh"])):
                for n in ns:
                    if f"][{row}]" in n:
                        p = root / "FF9_Data" / "WorldMap" / f"Disc{disc}" / lod / f"r{row}" / n
                        p.parent.mkdir(parents=True, exist_ok=True)
                        p.write_bytes(b"x")

    def by_glob(folder, cells):                                           # the rule as it was written
        out = {}
        for disc in D.DISCS:
            tree = folder / "FF9_Data" / "WorldMap" / f"Disc{disc}"
            for bx, by in cells:
                for p in tree.glob(f"*/r{by}/Block[[]{bx}[]][[]{by}[]] *"):
                    if p.is_file() and ".bak-" not in p.name and not p.name.endswith(".promoting"):
                        out[p.relative_to(folder).as_posix()] = p
        return out
    for cells in ([(1, 1)], [(1, 1), (1, 11), (2, 1)], D.all_cells(), [(5, 5)]):
        assert D._cell_files(root, cells) == by_glob(root, cells)


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


def test_asking_whether_a_draft_exists_parses_its_meta_once_per_write(tmp_path, monkeypatch):
    """The cards, the recipe bar and the tab asked "is there a draft?" by parsing its 423 KB draft.json: 14-16
    parses an Accept, 8 an undo, one per ghost drag frame, 2.5-4.7 ms each on the GUI thread (PERF.md 7, c3).
    draft.is_draft answers read_meta's question again only when draft.json's stat moved; every such check spends it."""
    import time
    _game_, _src, d = _draft(tmp_path)
    parsed, real = [], D.read_meta
    monkeypatch.setattr(D, "read_meta", lambda p: parsed.append(p) or real(p))
    assert all(D.is_draft(d) for _ in range(20)) and len(parsed) == 1
    then = time.time_ns() - 10 ** 9
    (d / D.DRAFT_FILE).write_text("{ not json", encoding="utf-8")      # rewritten (and broken): asked again
    os.utime(d / D.DRAFT_FILE, ns=(then, then))
    assert not D.is_draft(d) and len(parsed) == 2
    assert not D.is_draft(tmp_path / "nowhere")
    import ff9mapkit.workspace.worlddoc as WD
    import ff9mapkit.workspace.worldforest as WF
    import ff9mapkit.workspace.worldrecipe as WR
    import inspect
    for fn in (WF.CarryTool.draft, WD.WorldDoc._draft, WR.RecipeBar.draft):   # THE CALL SITES
        src = inspect.getsource(fn)
        assert "is_draft(" in src and "read_meta(" not in src, fn


def test_opening_a_recipe_makes_its_draft_and_steps_off_the_window_s_thread(monkeypatch, tmp_path, app):
    """Open... discarded the draft, copied a fresh one (2-10 s) and snapshotted each row's cells (a whole-map step
    for an island, carry or sink row) on the window's thread: its click froze the window 13-23 s (PERF.md 7, K8).
    They run on a worker; the bar holds the draft from the click to the last row, as before."""
    import threading
    import time
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldrecipe import RecipeBar
    game = _two_islands(monkeypatch, tmp_path)
    saved = tmp_path / "one.toml"
    saved.write_text(RC.dumps([{"table": "forest", "center": [26.0, -26.0], "donor": "15,15"}]), encoding="utf-8")
    where = {}

    def seen(name, real):
        def fn(*a, **k):
            if any(str(tmp_path) in str(v) for v in list(a) + list(k.values())):   # this test's drafts only (a
                where.setdefault(name, threading.current_thread() is threading.main_thread())   # card left alive
            return real(*a, **k)                                                  # by an earlier test may fire)
        return fn
    for name in ("discard", "ensure_draft", "begin_step", "commit_step"):
        monkeypatch.setattr(D, name, seen(name, getattr(D, name)))
    D.ensure_draft(game / "FF9CustomMap-world", game=game, root=tmp_path / "drafts")   # a draft to replace
    where.clear()
    holds = []
    bar = RecipeBar(pick_palette("dark"), game_fn=lambda: game, source_fn=lambda: game / "FF9CustomMap-world",
                    runner=InProcess(), drafts_root=tmp_path / "drafts", open_path_fn=lambda: str(saved),
                    ask=lambda *a: True, on_hold=holds.append, sync=False)
    bar.open_btn.click()
    assert bar.holding() and holds[-1] is True                            # held from the click
    t = time.time()
    while bar.holding():
        assert time.time() - t < 60
        app.processEvents()
        time.sleep(0.01)
    assert where == {"discard": False, "ensure_draft": False, "begin_step": False, "commit_step": False}
    assert D.history(tmp_path / "drafts" / "FF9CustomMap-world.draft")["cursor"] == 1 and holds[-1] is False
    assert "Composed one.toml: 1 row" in bar.status_lbl.text()


def test_a_discard_is_whole_or_nothing(tmp_path, monkeypatch):
    """Open... discards the draft on a worker while the window stays live, and the 3D view can read the draft's
    files meanwhile. A bare rmtree stopped at the first file a reader held (deleting bottom-up, draft.json last): a
    gutted folder that is still a draft, drawn, its missing files read as edits, a Promote deleting them from the
    live folder (review of the perf commits, CR-1). A discard renames the draft aside first -- refused, whole, while
    a file in it is open -- and then deletes the renamed copy."""
    import shutil
    _game_, _src, d = _draft(tmp_path)
    before = _tree(d)
    held = open(d / T10, "rb")                                          # a reader holds a file of the draft
    monkeypatch.setattr(D, "_retry", lambda fn, **k: fn())              # (no waiting out the reader here)
    try:
        with pytest.raises(OSError):
            D.discard(d, root=tmp_path / "drafts")
    finally:
        held.close()
    assert D.is_draft(d) and _tree(d) == before                         # untouched: the discard did nothing
    real = shutil.rmtree
    gone = []
    monkeypatch.setattr(shutil, "rmtree", lambda p, **k: gone.append(Path(p).name) or real(p, **k))
    D.discard(d, root=tmp_path / "drafts")
    assert not d.exists() and gone and gone[0] != d.name               # the renamed copy is what is deleted
    assert not [p for p in (tmp_path / "drafts").iterdir() if p.name.startswith(d.name)]


def test_a_step_is_recorded_while_the_window_reads_the_history(tmp_path):
    """commit_step now runs on a worker (a card's Accept, an opened recipe's row) while the window's thread reads
    history.json (the recipe bar's refresh, Undo's refusal, Save). Windows refuses the replace onto a file another
    handle holds open, so the step's record was lost: its bytes in the draft, Undo unable to take them back (review
    of the perf commits, CR-2). The history and meta writes wait such a reader out."""
    import threading
    _game_, _src, d = _draft(tmp_path)
    stop, errors = threading.Event(), []

    def reader():
        while not stop.is_set():
            D.history(d)
    t = threading.Thread(target=reader, daemon=True)
    t.start()
    try:
        for i in range(80):
            D.begin_step(d, [(0, 0)])
            (d / T00).write_bytes(b"step %d" % i)
            try:
                D.commit_step(d, {"table": "forest", "center": [1.0, -1.0], "donor": "15,15"}, f"step {i}")
            except OSError as e:
                errors.append(e)
                D.abort_step(d)
    finally:
        stop.set()
        t.join(5)
    assert errors == [] and D.history(d)["cursor"] == 80


def test_an_abort_that_failed_is_finished_by_the_next_step_or_edit(tmp_path, monkeypatch):
    """An abort that failed (a reader holding a file past _retry) left its pending snapshot -- the before-images of
    the half-written step -- and the next begin_step deleted it, leaving the half step in the draft unrecorded, or
    a later cancel_edit wrote it back over the edit's cells (review of the perf commits, F2). The next begin_step or
    begin_edit finishes that abort first: the draft is back as it was before the failed step."""
    _game_, _src, d = _draft(tmp_path)
    _step(d, [(1, 0)], {T10: b"mountain"}, "mountain one")
    before = _tree(d)
    for opener in ("step", "edit"):
        D.begin_step(d, [(0, 0)])
        (d / T00).write_bytes(b"half a forest")                           # the step half wrote its cell...
        real = D._restore
        monkeypatch.setattr(D, "_restore", lambda *a, **k: (_ for _ in ()).throw(PermissionError(13, "held")))
        with pytest.raises(PermissionError):
            D.abort_step(d)                                               # ...and its abort failed
        monkeypatch.setattr(D, "_restore", real)
        if opener == "step":
            D.begin_step(d, [(1, 0)])
            assert _tree(d) == before                                     # the half forest is gone
            D.abort_step(d)
        else:
            D.begin_edit(d, 0)
            D.cancel_edit(d)
            assert _tree(d) == before and D.history(d)["cursor"] == 1


def test_an_opened_recipe_says_when_a_row_s_abort_fails(monkeypatch, tmp_path, app):
    """A row that failed and whose abort then failed was reported with the verb's last line only: its half writes
    stayed in the draft unrecorded, said nowhere (review of the perf commits, F2)."""
    game = _two_islands(monkeypatch, tmp_path)
    saved = tmp_path / "bad.toml"
    saved.write_text(RC.dumps([{"table": "forest", "center": [26.0, -26.0], "donor": "15,15"},
                               {"table": "mountain", "center": [300.0, -300.0], "donor": "0,0"}]), encoding="utf-8")
    doc, _run = _doc(app, game, tmp_path, saved)
    doc.set_view_mode("3d", sync=True)
    real = D.abort_step

    def fails(d):                                                         # a real abort (a pending step) fails
        if (Path(d) / D.HISTORY_DIR / D._PENDING / "step.json").is_file():
            raise PermissionError(13, "a reader holds it")
        return real(d)
    monkeypatch.setattr(D, "abort_step", fails)
    doc._recipe.open_btn.click()
    monkeypatch.setattr(D, "abort_step", real)
    text = doc._recipe.status_lbl.text()
    assert "Stopped at mountain" in text and "could not be taken back" in text and "a reader holds it" in text


def test_a_closing_workspace_starts_no_row_whose_snapshot_was_still_running(monkeypatch, tmp_path, app):
    """Closing the Workspace stops an opened recipe after the row that RUNS. With the snapshot on a worker, a close
    landing while a row's begin_step ran still started that row's world-fuse once the snapshot ended -- up to a
    15-26 s sink row the user had not seen start (review of the perf commits). A row not yet started is not."""
    import threading
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldrecipe import RecipeBar
    game = _two_islands(monkeypatch, tmp_path)
    saved = tmp_path / "one.toml"
    saved.write_text(RC.dumps([{"table": "forest", "center": [26.0, -26.0], "donor": "15,15"}]), encoding="utf-8")
    go, real = threading.Event(), D.begin_step
    monkeypatch.setattr(D, "begin_step", lambda *a, **k: go.wait(30) and real(*a, **k))
    run = InProcess()
    bar = RecipeBar(pick_palette("dark"), game_fn=lambda: game, source_fn=lambda: game / "FF9CustomMap-world",
                    runner=run, drafts_root=tmp_path / "drafts", open_path_fn=lambda: str(saved),
                    ask=lambda *a: True, sync=False)
    bar.open_btn.click()
    bar._steps.wait()                                                     # the fresh draft is made
    waiter = bar.closing_runner()                                         # the close lands mid-snapshot
    assert waiter is bar._steps
    threading.Timer(0.2, go.set).start()
    for _ in range(16):                                                   # as WorldDoc.shutdown loops
        w = bar.closing_runner()
        if w is None:
            break
        assert w.wait()
    assert run.argvs == [] and not bar.holding()                          # the row never started
    assert "Stopped one.toml as the Workspace closed" in bar.status_lbl.text()
    assert not (tmp_path / "drafts" / "FF9CustomMap-world.draft" / D.HISTORY_DIR / D._PENDING).exists()


def _failed_abort(d, monkeypatch, cells, writes):
    """A step that half wrote and whose abort failed: its pending snapshot left in the draft."""
    D.begin_step(d, cells)
    for rel, data in writes.items():
        (d / rel).write_bytes(data)
    real = D._restore
    monkeypatch.setattr(D, "_restore", lambda *a, **k: (_ for _ in ()).throw(PermissionError(13, "held")))
    with pytest.raises(PermissionError):
        D.abort_step(d)
    monkeypatch.setattr(D, "_restore", real)


def test_a_pending_abort_is_finished_before_an_undo_or_redo_rewrites_its_cells(tmp_path, monkeypatch):
    """A failed abort's snapshot was finished at the NEXT begin_step, after an Undo or Redo had rewritten its cells:
    it wrote the undone step's bytes back while the history said undone (review round 2, H1). Undo, Redo and
    Promote finish a pending abort first, so the history stays exact."""
    _game_, _src, d = _draft(tmp_path)
    _step(d, [(1, 0)], {T10: b"mountain"}, "mountain one")
    stock = (_src / T10).read_bytes()
    _failed_abort(d, monkeypatch, [(0, 0), (1, 0)], {T00: b"half a forest"})
    D.undo(d)                                                             # takes the mountain back out
    assert (d / T10).read_bytes() == stock and (d / T00).read_bytes() == (_src / T00).read_bytes()
    D.begin_step(d, [(0, 0)])
    assert (d / T10).read_bytes() == stock                                # not written back by a late abort
    D.abort_step(d)
    D.redo(d)
    assert (d / T10).read_bytes() == b"mountain" and D.history(d)["cursor"] == 1
