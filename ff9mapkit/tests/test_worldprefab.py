"""Placing a landmass prefab from the World tab (overworld editor rung P3): the catalog picker, the anchor under the
click, the ghost (the prefab's own land, moved by whole blocks), ``world-prefab``'s first laws as the preview, the
command and its ``[[prefab]]`` recipe row (``world-fuse`` runs the same pipeline), the verdict ``--report-json``
writes in the shape every card reads, and the card end to end against a scripted runner: Check, Accept as ONE draft
step, a refusal named by its gate."""
from __future__ import annotations

import json
import os

import numpy as np
import pytest

from ff9mapkit import cli
from ff9mapkit.world import draft as D
from ff9mapkit.world import fuse as FU
from ff9mapkit.world import islandedit as IE
from ff9mapkit.world import prefab as PF
from ff9mapkit.world import prefabedit as PE
from ff9mapkit.world import recipe as RC

from .test_world_forestedit import _game, _mod
from .test_worldcoast import REAL_GAME, _pin  # noqa: F401  (the autouse install guard; the install resolved first)

FOOT = [[-1, -1], [-1, 0], [-1, 1], [0, -1], [0, 0], [0, 1], [1, -1], [1, 0], [1, 1]]
UNIT = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1]]
CATALOG = f'''
[[prefab]]
name = "isle"
status = "qualified"
walked = "test walk"
fingerprint = "{"f" * 64}"
fingerprint_cell = [1, 14]
footprint = {FOOT}

[[prefab.rows]]
table = "island"
center = [32.0, 32.0]
radius = 40.0
seed = 5.0

[[prefab.rows]]
table = "hill"
center = [10.0, 30.0]
radius = 14.0

[[prefab]]
name = "unit"
status = "candidate"
fingerprint = "{"e" * 64}"
footprint = {UNIT}

[[prefab.rows]]
table = "transplant"
cell = [0, 0]
donor = [9, 5]
size = [2, 3]
rot = 90
'''


@pytest.fixture
def catalog(tmp_path):
    p = tmp_path / "prefabs.toml"
    p.write_text(CATALOG, encoding="utf-8")
    return p


# ---------------------------------------------------------------- the edit module
def test_the_picker_lists_the_walked_first(catalog):
    assert [p["name"] for p in PE.prefabs(catalog)] == ["isle", "unit"]
    shipped = [p["status"] for p in PE.prefabs()]
    assert shipped == sorted(shipped, key=lambda s: s != "qualified") and "desert-peak-isle" in \
        [p["name"] for p in PE.prefabs()]


def test_the_anchor_centres_the_footprint_on_the_click_wraps_and_stays_on_the_map(catalog):
    isle, unit = PE.get("isle", catalog), PE.get("unit", catalog)
    assert PE.anchor_for(64 * 10 + 5.0, -64 * 9 - 60.0, isle) == (10, 9)          # anywhere in the middle block
    assert PE.anchor_for(64 * 10 + 5.0, -64 * 9 - 60.0, unit) == (9, 9)           # a 3x2 rect: rows 9-10 (click 9.94)
    assert PE.anchor_for(3.0, -64 * 5 - 30.0, isle) == (0, 5)
    assert PE.anchor_for(-3.0, -64 * 5 - 30.0, isle) == (23, 5)                    # across x = 0: the column wraps
    assert PE.anchor_for(64 * 4.0, -5.0, isle) == (4, 1)                           # the top row stays on the map
    assert PE.anchor_for(64 * 4.2, -64 * 20 + 5.0, unit) == (3, 18)                # the bottom too
    assert PE.cells((23, 5), isle)[:3] == [(0, 4), (0, 5), (0, 6)]                 # labels wrap
    assert PE.center((10, 9), isle) == (672.0, -608.0) == PF.footprint_center(isle, (10, 9))
    assert np.allclose(PE.rim((10, 9), isle)[[0, 2]], [[576.0, 0.4, -512.0], [768.0, 0.4, -704.0]])


def test_the_ghost_is_the_mint_s_own_coast_moved_by_whole_blocks(catalog):
    isle = PE.get("isle", catalog)
    g = PE.ghost(isle)                                   # an island base + a hill: no stock read at all
    want = IE.ghost(IE.outline((32.0, -32.0), radius=40.0, seed=5.0), height=3.2)[0]
    assert np.allclose(g, want)
    moved = PE.at(g, (10, 9))
    assert np.allclose(moved[..., 0] - g[..., 0], 640.0) and np.allclose(moved[..., 2] - g[..., 2], -576.0)
    assert np.allclose(moved[..., 1], g[..., 1])


def test_the_preview_runs_world_prefab_s_first_laws(catalog):
    isle = PE.get("isle", catalog)
    free = dict(land=set(), occupied=lambda bs: {}, occupied_target=lambda bs: {})
    assert PE.preview((10, 9), isle, **free)["ok"]
    assert "off the top" in PE.preview((10, 0), isle, **free)["why"]
    pv = PE.preview((10, 9), isle, **{**free, "land": {(11, 10)}})
    assert not pv["ok"] and "real land or coast" in pv["why"] and pv["where"] == [(64 * 11 + 32.0, -(64 * 10 + 32.0))]
    pv = PE.preview((10, 9), isle, **{**free, "occupied": lambda bs: {(12, 11): ["Other"]} if (12, 11) in bs else {}})
    assert not pv["ok"] and "beside its footprint" in pv["why"] and "Other" in pv["why"]        # the ring counts
    reads = PE.preview((10, 9), {**isle, "rows": isle["rows"][:1] + [{"table": "forest", "center": [32.0, 32.0],
                                                                       "reach": 200.0}]},
                       **{**free, "occupied_target": lambda bs: {(13, 9): ["D"]} if (13, 9) in bs else {}})
    assert not reads["ok"] and "read" in reads["why"]                               # a carry's read window, target only


def test_the_command_and_its_row():
    argv = PE.command("D", "desert-peak-isle", (10, 9), dry_run=False)
    assert argv == ["world-prefab", "desert-peak-isle", "--cell", "10,9", "--mod-folder", "D"]
    assert PE.command("D", "x", (1, 2), dry_run=True, report="r.json")[-3:] == ["--dry-run", "--report-json", "r.json"]
    row = RC.row_for(argv)
    assert row == {"table": "prefab", "name": "desert-peak-isle", "cell": [10, 9]}
    assert RC.label(row) == "prefab desert-peak-isle on block (10, 9)"
    assert RC.anchor(row) == (672.0, -608.0)
    assert set(RC.row_cells(row)) == {(bx, by) for bx in (9, 10, 11) for by in (8, 9, 10)}
    assert RC.loads(RC.dumps([row])) == [row]
    for bad in (["--fingerprint"], ["--recipe-out", "x.toml"], ["--skip-mirror"]):
        with pytest.raises(ValueError, match="one placement"):
            RC.row_for(argv + bad)
    assert "prefab" in RC.EDITOR_TABLES and "prefab" in RC.EDITABLE_TABLES
    assert "prefab" in FU.COMPOSE_TIERS[0]                     # a base: relief rows after it may stand on it


def test_the_prefab_row_runs_world_prefab_s_own_pipeline(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(PF, "place", lambda name, cell, mod_folder, **kw: calls.append((name, cell, kw["dry_run"])))
    out = FU.compose_layout(str(tmp_path), {"prefab": [{"name": "desert-peak-isle", "cell": [10, 9]}]},
                            game=tmp_path, dry_run=True)
    assert out["clean"] and calls == [("desert-peak-isle", (10, 9), True)]
    out = FU.compose_layout(str(tmp_path), {"prefab": [{"name": "x", "cell": [1, 1], "rot": 90}]}, game=tmp_path,
                            dry_run=True)
    assert "unknown key(s) ['rot']" in out["gates"][-1]["error"]

    def refuse(*a, **k):
        raise PF.PrefabRefused("the window is busy", gate="window")
    monkeypatch.setattr(PF, "place", refuse)
    out = FU.compose_layout(str(tmp_path), {"prefab": [{"name": "x", "cell": [1, 1]}]}, game=tmp_path, dry_run=True)
    assert "the window is busy" in out["gates"][-1]["error"]


def test_report_json_is_the_verdict_every_card_reads(monkeypatch, tmp_path):
    rep = tmp_path / "v.json"

    def refuse(*a, **k):
        raise PF.PrefabRefused("busy", where=[(3, 5)], gate="window")
    monkeypatch.setattr(PF, "place", refuse)
    assert cli.main(["world-prefab", "terminus-pair", "--cell", "3,5", "--mod-folder", "D", "--dry-run",
                     "--report-json", str(rep)]) == 1
    v = json.loads(rep.read_text(encoding="utf-8"))
    assert v["ok"] is False and v["dry_run"] is True
    assert v["refused"]["gate"] == "window" and v["refused"]["message"] == "busy"
    assert v["refused"]["where"] == [[64 * 3 + 32.0, -(64 * 5 + 32.0)]]               # world points, for the pins
    monkeypatch.setattr(PF, "place", lambda *a, **k: {"name": "x", "dry_run": True, "blocks": [[3, 5]],
                                                      "center": [224.0, -352.0], "identity": "clean site"})
    assert cli.main(["world-prefab", "terminus-pair", "--cell", "3,5", "--mod-folder", "D", "--dry-run",
                     "--report-json", str(rep)]) == 0
    v = json.loads(rep.read_text(encoding="utf-8"))
    assert v["ok"] is True and v["refused"] is None and v["blocks"] == [[3, 5]] and v["center"] == [224.0, -352.0]
    assert cli.main(["world-prefab", "nope", "--cell", "3,5", "--mod-folder", "D", "--report-json", str(rep)]) == 1
    assert json.loads(rep.read_text(encoding="utf-8"))["refused"]["gate"] == "catalog"


def test_a_draft_s_own_source_is_not_another_folder_in_the_stack(monkeypatch, tmp_path):
    """A draft stands in for its source (world/draft.py): the stack check must not refuse the draft over the very
    folder it was copied from (every card's occupancy read skips it too)."""
    from ff9mapkit import config
    from ff9mapkit.world import render
    game = _game(tmp_path)
    monkeypatch.setattr(config, "find_game_path", lambda g=None: game)
    src = _mod(game, "Src", ((10, 9),))                               # the source holds land in the footprint
    draft = D.ensure_draft(src, game=game, root=tmp_path / "drafts")
    monkeypatch.setattr(render, "game_stack", lambda g: (src,))
    seen = []
    monkeypatch.setattr(PF, "window_blockers", lambda p, c, root, stack=None: seen.append(tuple(stack)) or
                        {"target": set(), "stack": {}})
    monkeypatch.setattr(PF, "_draft_laws", lambda *a, **k: None)
    monkeypatch.setattr(PF, "stage", lambda *a, **k: (_ for _ in ()).throw(PF.PrefabRefused("stop", gate="x")))
    cat = tmp_path / "c.toml"
    cat.write_text(CATALOG, encoding="utf-8")
    with pytest.raises(PF.PrefabRefused, match="stop"):
        PF.place("isle", (10, 9), str(draft), catalog=cat, log=lambda *a: None)
    assert seen[-1] == ()                                              # Src skipped: the draft stands in for it
    with pytest.raises(PF.PrefabRefused, match="stop"):
        PF.place("isle", (10, 9), "Other", catalog=cat, log=lambda *a: None)
    assert [p.name for p in seen[-1]] == ["Src"]                       # a live target keeps the whole stack


# ---------------------------------------------------------------- the card
@pytest.fixture(scope="module")
def app():
    pytest.importorskip("PySide6", reason="GUI extra not installed")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _card(app, tmp_path, catalog, answer, *, ocean=frozenset(), stack=()):
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldprefab import PrefabTool
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    from .test_worldforest import Scripted
    run = Scripted(answer)
    game = _game(tmp_path)
    src = _mod(game, "FF9CustomMap-world", ((0, 0),))
    panel = WorldView3DPanel(pick_palette("dark"))
    land = np.array([[[10.0, 3.2, -10.0], [20.0, 3.2, -10.0], [10.0, 3.2, -20.0]]])
    tool = PrefabTool(pick_palette("dark"), panel, game_fn=lambda: game, source_fn=lambda: src, runner=run,
                      drafts_root=tmp_path / "drafts", sync=True, stack_fn=lambda: list(stack),
                      ghost_fn=lambda p: land, ocean_fn=lambda: set(ocean), catalog=catalog)
    return tool, run, panel, land


def test_the_card_picks_an_anchor_draws_the_prefab_checks_and_places_it_as_one_step(app, tmp_path, catalog):
    def answer(kind, argv):
        cell = [int(v) for v in argv[argv.index("--cell") + 1].split(",")]
        return {"ok": True, "dry_run": kind == "check", "refused": None, "identity": "clean site: the full fingerprint",
                "blocks": [[cell[0] + dx, cell[1] + dy] for dx, dy in FOOT], "center": [672.0, -608.0],
                "written_fingerprint": "f" * 64, "written_disc4": "deferred: Promote makes it"}   # the CLI's real shape
    tool, run, panel, land = _card(app, tmp_path, catalog, answer)
    tool.open_tool()
    assert [tool.prefab_box.itemText(i) for i in range(tool.prefab_box.count())] == ["isle 3x3", "unit 3x2 · new"]
    tool.place(64 * 10 + 40.0, -64 * 9 - 20.0)
    assert tool.cell() == (10, 9) and tool.center == (672.0, -608.0)
    assert np.allclose(panel._overlays[0][0].reshape(-1, 3), PE.at(land, (10, 9)).reshape(-1, 3))
    tool._timer.stop()
    tool._check()
    (argv,) = run.argvs
    assert argv[5:] == PE.command(tool.draft(), "isle", (10, 9), dry_run=True, report=argv[-1])
    assert "Passes" in tool.verdict_lbl.text() and "walked in game" in tool.verdict_lbl.text()
    tool.accept_btn.click()
    assert D.recipe_rows(tool.draft()) == [{"table": "prefab", "name": "isle", "cell": [10, 9]}]   # ONE step
    assert "In the draft: 9 blocks" in tool.verdict_lbl.text()


def test_the_card_refuses_land_before_any_job_and_names_a_refusing_gate(app, tmp_path, catalog):
    def answer(kind, argv):
        return {"ok": False, "dry_run": True, "refused": {"gate": "identity", "message": "a regression to find",
                                                          "where": [[672.0, -608.0]]}}
    tool, run, _panel, _land = _card(app, tmp_path, catalog, answer, ocean={(11, 10)})
    tool.open_tool()
    tool.place(64 * 10 + 40.0, -64 * 9 - 20.0)
    assert "real land or coast" in tool.verdict_lbl.text() and not run.argvs
    tool.place(64 * 15 + 40.0, -64 * 9 - 20.0)
    tool._timer.stop()
    tool._check()
    assert "Refused by the identity check" in tool.verdict_lbl.text() and not tool.accept_btn.isEnabled()


def test_a_new_prefab_refits_the_anchor_and_a_placed_step_says_its_row_back(app, tmp_path, catalog):
    tool, _run, _panel, _land = _card(app, tmp_path, catalog, lambda k, a: None)
    tool.open_tool()
    tool.place(64 * 10 + 5.0, -64 * 9 - 60.0)
    assert tool.cell() == (10, 9)
    tool.prefab_box.setCurrentIndex(tool.prefab_box.findData("unit"))
    assert tool.cell() == (9, 9)                                        # the 3x2 rect centred on the same click
    for row in ({"table": "prefab", "name": "isle", "cell": [23, 5]}, {"table": "prefab", "name": "unit",
                                                                         "cell": [4, 18]}):
        tool.load_row(row)
        assert tool.row() == row                                       # THE SAID-BACK LAW
    with pytest.raises(ValueError, match="not one the catalog lists"):
        tool.load_row({"table": "prefab", "name": "nope", "cell": [1, 1]})


def test_the_world_tab_menu_opens_the_prefab_card_one_card_at_a_time(app, monkeypatch, tmp_path):
    """The World tab's "Add a prefab" entry builds the card on its first click (rung P3), over the doc's own seams,
    and opening another card puts it away (one card at a time, as every carry card)."""
    from ff9mapkit.workspace.worldprefab import PrefabTool
    from .test_worldmountain import _doc
    doc, _g = _doc(app, monkeypatch, tmp_path)
    doc._prefab_seams = {"ghost_fn": lambda p: np.zeros((0, 3, 3)), "ocean_fn": lambda: set(),
                         "soup_fn": doc._mountain_seams["soup_fn"], "stack_fn": lambda: [], "sync": True}
    doc.set_view_mode("3d", sync=True)
    assert "prefab" in doc.tool_actions and doc.EDIT_CARDS["prefab"] == "prefab"
    doc.tool_actions["prefab"].trigger()
    assert isinstance(doc._prefab, PrefabTool) and not doc._prefab.isHidden()
    doc.tool_actions["mountain"].trigger()
    assert doc._prefab.isHidden() and not doc._mountain.isHidden()



def test_the_review_s_card_findings(app, tmp_path, catalog):
    """Review P3: the picker's labels are never clipped (sized from its own text, not a fixed 16); an error verdict
    is world-prefab's, not "the carve"; a closed card forgets its click (no half-minute check without a new one)."""
    tool, run, _panel, _land = _card(app, tmp_path, catalog, lambda k, a: {
        "ok": False, "dry_run": True, "refused": {"gate": "error", "message": "boom", "where": []}})
    shipped, _r, _p, _l = _card(app, tmp_path / "shipped", None, lambda k, a: None)   # the real catalog's labels
    texts = [shipped.prefab_box.itemText(i) for i in range(shipped.prefab_box.count())]
    assert max(len(t) for t in texts) > 16                               # (a fixed 16 would clip these)
    assert shipped.prefab_box.minimumContentsLength() >= max(len(t) for t in texts)
    tool.open_tool()
    tool.place(64 * 15 + 40.0, -64 * 9 - 20.0)
    tool._timer.stop()
    tool._check()
    assert "Refused by world-prefab: boom" in tool.verdict_lbl.text() and "carve" not in tool.verdict_lbl.text()
    n = len(run.argvs)
    tool.close_tool()
    tool.open_tool()
    assert tool.cell() is None and tool.cell_lbl.text() == "Click open ocean."
    tool.prefab_box.setCurrentIndex(tool.prefab_box.findData("unit"))
    tool._timer.stop()
    tool._check()
    assert len(run.argvs) == n                                           # nothing re-placed, nothing checked


def test_the_card_works_on_a_folder_with_no_deployed_land(app, tmp_path, catalog):
    """Review P3: the soup read refuses a folder with no deployed Terrain, and the card waited forever on it; a prefab
    goes onto open ocean, so an empty folder is a fine place to start."""
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldprefab import PrefabTool
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    from .test_worldforest import Scripted
    game = _game(tmp_path)
    src = game / "Empty"                                   # world files (a sea override), but no deployed Terrain
    (src / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / "r0").mkdir(parents=True)
    (src / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / "r0" / "Block[0][0] Sea4.ff9mesh").write_bytes(b"sea")
    run = Scripted(lambda k, a: {"ok": True, "dry_run": True, "refused": None, "blocks": [[10, 9]],
                                 "center": [672.0, -608.0]})
    tool = PrefabTool(pick_palette("dark"), WorldView3DPanel(pick_palette("dark")), game_fn=lambda: game,
                      source_fn=lambda: src, runner=run, drafts_root=tmp_path / "drafts", sync=True,
                      stack_fn=lambda: [], ghost_fn=lambda p: np.zeros((0, 3, 3)), ocean_fn=lambda: set(),
                      catalog=catalog)
    tool.open_tool()
    tool.place(64 * 10 + 40.0, -64 * 9 - 20.0)
    tool._timer.stop()
    tool._check()
    assert run.argvs and "Passes" in tool.verdict_lbl.text()


# ---------------------------------------------------------------- the turn (rung P5)
TURN_CATALOG = (CATALOG.replace("fingerprint_cell = [1, 14]\n", "fingerprint_cell = [1, 14]\nturns = [0, 90, 180, 270]\n", 1)
                .replace('fingerprint = "' + "e" * 64 + '"\n', 'fingerprint = "' + "e" * 64 + '"\nfingerprint_cell = [3, 3]\n'
                         'turns = [0, 90]\n', 1))


def test_the_turn_picker_offers_only_the_catalog_s_turns_and_hides_for_turn_0_alone(app, tmp_path, catalog):
    tool, *_ = _card(app, tmp_path, catalog, lambda k, a: None)
    assert tool.turn_box.isHidden() and tool.turn() == 0                # the shipped shape: no turns, no picker
    p = tmp_path / "turns.toml"
    p.write_text(TURN_CATALOG, encoding="utf-8")
    tool, *_ = _card(app, tmp_path / "b", p, lambda k, a: None)
    assert not tool.turn_box.isHidden()
    assert [tool.turn_box.itemData(i) for i in range(tool.turn_box.count())] == [0, 90, 180, 270]
    tool.turn_box.setCurrentIndex(tool.turn_box.findData(180))
    tool.prefab_box.setCurrentIndex(tool.prefab_box.findData("unit"))
    assert [tool.turn_box.itemData(i) for i in range(tool.turn_box.count())] == [0, 90] and tool.turn() == 0


def test_a_turned_prefab_ghosts_turned_refits_its_anchor_checks_with_turn_and_lands_as_a_turned_row(app, tmp_path):
    p = tmp_path / "turns.toml"
    p.write_text(TURN_CATALOG, encoding="utf-8")

    def answer(kind, argv):
        cell = [int(v) for v in argv[argv.index("--cell") + 1].split(",")]
        return {"ok": True, "dry_run": kind == "check", "refused": None, "turn": 90,
                "identity": "clean site: the catalog's land turned 90, the full fingerprint",
                "blocks": [[cell[0] + dx, cell[1] + dy] for dx, dy in FOOT], "center": [672.0, -608.0],
                "written_fingerprint": "f" * 64, "written_disc4": "deferred: Promote makes it"}
    tool, run, panel, land = _card(app, tmp_path, p, answer)
    tool.open_tool()
    tool.place(64 * 10 + 40.0, -64 * 9 - 20.0)
    tool.turn_box.setCurrentIndex(tool.turn_box.findData(90))
    assert tool.cell() == (10, 9)                                       # a square turns onto its own blocks
    got = panel._overlays[0][0].reshape(-1, 3)
    assert np.allclose(got, PE.at(PE.turn(land, tool.prefab()), (10, 9)).reshape(-1, 3))
    assert not np.allclose(got, PE.at(land, (10, 9)).reshape(-1, 3))   # and it IS turned
    tool._timer.stop()
    tool._check()
    (argv,) = run.argvs
    assert argv[argv.index("--turn") + 1] == "90"
    assert "turned 90" in tool.verdict_lbl.text()
    tool.accept_btn.click()
    assert D.recipe_rows(tool.draft()) == [{"table": "prefab", "name": "isle", "cell": [10, 9], "turn": 90}]
    tool.load_row({"table": "prefab", "name": "unit", "cell": [4, 10], "turn": 90})
    assert tool.turn() == 90 and tool.cell() == (4, 10)
    assert tool.blocks() == PF.footprint_labels(PF.turned(PE.get("unit", p), 90), (4, 10))
    with pytest.raises(ValueError, match="turn 180"):
        tool.load_row({"table": "prefab", "name": "unit", "cell": [4, 10], "turn": 180})


def test_the_turned_ghost_is_the_files_rigid_map():
    unit = {"name": "u", "footprint": UNIT, "rows": [{"table": "transplant", "cell": [0, 0], "donor": [9, 5]}]}
    land = np.array([[[10.0, 3.0, -10.0], [70.0, 4.0, -10.0], [10.0, 5.0, -100.0]]])
    for t in (90, 180, 270):
        v = PF.turned(unit, t)
        g = PE.turn(land, v)
        for a, b in zip(land.reshape(-1, 3), g.reshape(-1, 3)):
            assert (b[0], b[2]) == pytest.approx(PF.turn_point(a[0], a[2], v, (0, 0), t)) and b[1] == a[1]
    assert np.allclose(PE.turn(land, unit), land)
