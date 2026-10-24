"""The overworld editor across the world's x seam (rung C10). The relief verbs already read and write across x = 0
(`interior.read_deployed_blocks`' unwrapped window); the editor did not: its cards read the island in [0, 1536), so a
shape at x = 0 met no ground under its west half, and the 3D view drew column 23 at the far end of the map. Now a
centre near the seam is judged in a second soup read across it (`worldforest.SEAM_MAP`), the command names the folded
centre, and the view draws the seam twice (`worldview3d.seam_copies`), the ghost and its marks with it."""
from __future__ import annotations

import shutil

import numpy as np
import pytest

from ff9mapkit.world import draft as D
from ff9mapkit.world import mesh as M
from ff9mapkit.world import recipe as RC
from ff9mapkit.workspace import worldview3d as V
from ff9mapkit.workspace.worldforest import frame_x, seam_frame

from .test_world_forestedit import _game, _no_real_install  # noqa: F401
from .test_world_interior import _canopy_dome, _mains_grid, _patch_donor
from .test_worldrecipe import InProcess, _tree, app  # noqa: F401
from .test_worldview3d import _mouse


# ---------------------------------------------------------------- the frames and the view (pure)
def test_a_centre_near_the_seam_is_judged_in_the_seam_frame():
    assert seam_frame(0.0) and seam_frame(383.9) and not seam_frame(384.0) and not seam_frame(1151.9)
    assert seam_frame(1152.0) and seam_frame(1535.9)
    assert frame_x(1530.0) == -6.0 and frame_x(10.0) == 10.0 and frame_x(900.0) == 900.0


def test_the_seam_is_drawn_twice_and_a_drawing_there_gets_its_twin():
    verts = np.array([[10, 0, -5], [20, 0, -5], [10, 0, -15], [1530, 1, -5], [1534, 1, -5], [1530, 1, -15],
                      [700, 2, -5], [710, 2, -5], [700, 2, -15]], dtype=np.float64)
    uvs = np.arange(18, dtype=np.float64).reshape(9, 2)
    out = V.seam_copies([("Terrain", verts, uvs, np.array([(0, 1, 2), (3, 4, 5), (6, 7, 8)]))])
    assert len(out) == 3                                 # the batch, its east copy, its west copy
    _part, ev, euv, et = out[1]
    wv = out[2][1]
    assert ev[:, 0].tolist() == [1546.0, 1556.0, 1546.0] and np.array_equal(euv, uvs[:3]) and et.tolist() == [[0, 1, 2]]
    assert wv[:, 0].tolist() == [-6.0, -2.0, -6.0] and np.array_equal(wv[:, 1:], verts[3:6, 1:])
    assert V.pack(out).tris == 5                         # the middle triangle is drawn once
    assert V.seam_shifts([-6.0, 10.0]) == [0.0, 1536.0]
    assert V.seam_shifts([1300.0, 1340.0]) == [0.0]
    assert V.seam_shifts([1400.0, 1530.0]) == [0.0, -1536.0]


def test_the_ghost_drags_from_its_twin_across_the_seam(app):
    """Through QApplication.sendEvent: the ghost stands at x -6 (the seam frame), the camera looks at its twin at
    x 1530; a press there drags it, and the positions come in the twin's frame (the card folds them)."""
    w = V.WorldView3D()
    w.resize(320, 200)
    w.camera = V.OrbitCamera(target=(1530.0, 0.0, -32.0), yaw=0.0, pitch=60.0, dist=80.0)
    cx, cz = -6.0, -32.0
    w.set_ghost({"center": (cx, cz), "y": 0.0, "poly": np.array([(cx - 8, cz - 8), (cx + 8, cz - 8),
                                                                (cx + 8, cz + 8), (cx - 8, cz + 8)])})
    moved = []
    w.ghost_moved.connect(lambda x, z: moved.append((x, z)))
    yaw0 = w.camera.yaw
    _mouse(w, "press", (160, 100))
    _mouse(w, "move", (180, 100))
    _mouse(w, "move", (200, 100))
    _mouse(w, "release", (200, 100))
    assert moved and w.camera.yaw == yaw0 and all(1500.0 < x < 1560.0 for x, _z in moved)


# ---------------------------------------------------------------- the cards on an island across x = 0
def _seam_island(monkeypatch, tmp_path):
    """FF9CustomMap-world: lawn filling blocks (23,0) and (0,0) whole, one island across x = 0 (x 1472-1536 and
    0-64); the canopy dome is the forest donor at (15,15)."""
    _patch_donor(monkeypatch, {(15, 15): _canopy_dome()})
    game = _game(tmp_path)
    for bx in (23, 0):
        g = _mains_grid(n=16)
        g.name, g.x = f"Block[{bx}][0] Terrain", bx
        M.deploy_override(g, mod_folder="FF9CustomMap-world", game=game, part="Terrain", disc=1)
    shutil.copytree(game / "FF9CustomMap-world", game / "Hand")
    return game


def _doc(game, tmp_path):
    from types import SimpleNamespace
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worlddoc import WorldDoc
    run = InProcess()
    doc = WorldDoc(pick_palette("dark"), game_path_fn=lambda: game, drafts_root=tmp_path / "drafts",
                   forest_runner=run, forest_seams={"sync": True}, hill_runner=run, hill_seams={"sync": True},
                   recipe_runner=run, recipe_seams={"ask": lambda t, x: True})
    doc._census, doc._game = SimpleNamespace(root=game / "FF9CustomMap-world"), game
    doc.set_view_mode("3d", sync=True)
    return doc, run


def _hand(game, argv):
    from ff9mapkit import cli
    assert cli.main(["--game", str(game)] + argv) == 0
    return _tree(game / "Hand")


@pytest.mark.parametrize("table,at,handles", [("hill", (-6.0, -32.0), {}), ("forest", (-4.0, -32.0), {})])
def test_a_shape_across_the_seam_previews_checks_and_writes_the_hand_typed_bytes(monkeypatch, tmp_path, app, table,
                                                                                  at, handles):
    """THE C10 ACCEPTANCE, hermetic: a shape centred just west of x = 0 (a click on the view's west copy) is judged
    in the seam frame, its ghost stands across x = 0 on both blocks, Check passes, and Accept writes what the
    command typed by hand -- spelled with the unfolded centre -- writes."""
    game = _seam_island(monkeypatch, tmp_path)
    doc, run = _doc(game, tmp_path)
    tool = getattr(doc, f"open_{table}")(sync=True)
    if table == "forest":
        tool.donor_box.setCurrentIndex(tool.donor_box.findData("15,15"))
    tool.place(*at, 3.2)
    folded = (at[0] + 1536.0, at[1])
    assert tool.center == folded and tool._seam and tool.fcenter() == at
    assert tool._preview["ok"], tool._preview
    poly = np.asarray(doc._view3d._ghost["poly"])
    assert poly[:, 0].min() < 0.0 < poly[:, 0].max()     # the ghost stands across x = 0, in the seam frame
    tool._timer.stop()
    tool._check()
    assert tool.accept_btn.isEnabled(), tool.verdict_lbl.text()
    argv = run.argvs[-1]
    assert argv[argv.index("--center") + 1] == f"{folded[0]:g},{folded[1]:g}"
    tool.accept_btn.click()
    draft = tmp_path / "drafts" / "FF9CustomMap-world.draft"
    edited = _tree(draft)
    changed = sorted(k for k in edited if edited[k] != _tree(game / "FF9CustomMap-world").get(k))
    assert any("Block[23][0]" in k for k in changed) and any("Block[0][0]" in k for k in changed), changed
    hand_argv = [a for a in argv[5:] if a != "--dry-run"]
    i = hand_argv.index("--report-json")
    hand_argv = hand_argv[:i] + hand_argv[i + 2:]
    hand_argv[hand_argv.index("--mod-folder") + 1] = "Hand"
    hand_argv[hand_argv.index("--center") + 1] = f"{at[0]:g},{at[1]:g}"     # the other spelling of the same point
    assert _hand(game, hand_argv) == edited
    steps = D.history(draft)["steps"]
    assert [s["row"]["center"] for s in steps] == [[folded[0], folded[1]]]
    assert RC.step_at(steps, *folded) == 0               # and a click there picks it (rung C9)


def test_without_the_seam_frame_the_ghost_finds_no_ground_west_of_the_seam(monkeypatch, tmp_path, app):
    """The break-it: the seam soup read like the east one (the editor before C10) and the same click is refused."""
    game = _seam_island(monkeypatch, tmp_path)
    doc, _run = _doc(game, tmp_path)
    tool = doc.open_hill(sync=True)
    tool._seam_soup_fn = tool._soup_fn
    tool._drop_soups()
    tool._load_soup()
    tool.place(-6.0, -32.0, 3.2)
    assert not tool._preview["ok"]


def test_a_pick_on_the_seam_copy_and_a_drag_across_the_seam_fold(monkeypatch, tmp_path, app):
    game = _seam_island(monkeypatch, tmp_path)
    doc, _run = _doc(game, tmp_path)
    tool = doc.open_hill(sync=True)
    doc._on_pick(((1546.0, 3.2, -32.0), "Terrain"), sync=True)     # the east copy of block (0,0)
    assert tool.center == (10.0, -32.0) and tool._seam and doc.sel_title.text() == "Point x 10.00, z -32.00"
    tool.drag_to(-2.0, -32.0)                            # dragged west over the seam
    assert tool.center == (1534.0, -32.0) and tool.fcenter() == (-2.0, -32.0) and tool._preview["ok"]
    tool.drop_at(700.0, -32.0)                           # off the seam: the east frame (no island there)
    assert not tool._seam and tool.fcenter() == (700.0, -32.0)


def test_a_card_given_one_soup_keeps_to_the_east_frame(app, tmp_path):
    """An injected soup (the tests', the snaps') is in one frame only: without a seam soup of its own the card never
    judges in the seam frame, so a bench at x 1214 (the snaps') is read as it always was."""
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.world.forestedit import SoupIndex
    from ff9mapkit.world import interior as IN
    from ff9mapkit.workspace.worldhill import HillTool
    from .test_world_forestedit import _mod
    game = _game(tmp_path)
    src = _mod(game, "FF9CustomMap-world", ((0, 0),))
    ix = SoupIndex(IN.soup_from_blocks({(0, 0): _mains_grid()}))
    tool = HillTool(pick_palette("dark"), V.WorldView3DPanel(pick_palette("dark")), game_fn=lambda: game,
                    source_fn=lambda: src, drafts_root=tmp_path / "drafts", sync=True, soup_fn=lambda folder: ix)
    tool.open_tool()
    tool.place(1214.0, -32.0, 3.2)
    assert not tool._seam and tool.fcenter() == (1214.0, -32.0)
    tool.place(24.0, -24.0, 3.2)
    assert not tool._seam and tool._preview["ok"]


def test_one_point_has_one_spelling_in_the_verbs_and_the_recipe():
    """THE ONE SPELLING: the relief verbs and world-fuse's rows fold a centre into the mapped window before they read
    round it. Unfolded, x -2 read the island in a frame 1536u from x 1534's and wrote other bytes at the seam
    (c10_lab, real bytes: one Terrain file of six)."""
    from ff9mapkit import cli
    from ff9mapkit.world import fuse as FU
    for verb in ("world-hill", "world-forest", "world-mountain"):
        a = cli.build_parser().parse_args([verb, "--mod-folder", "m", "--center", "-2,-500"])
        assert cli._parse_world_point(a) == ((1534.0, -500.0), True), verb
        a = cli.build_parser().parse_args([verb, "--mod-folder", "m", "--near", "1538,-500"])
        assert cli._parse_world_point(a) == ((2.0, -500.0), False), verb
    assert FU._row_point("hill", {"center": [-2.0, -500.0]}) == ((1534.0, -500.0), True)
    assert FU._row_point("forest", {"near": [1540.0, -500.0]}) == ((4.0, -500.0), False)
    assert cli._parse_world_point(cli.build_parser().parse_args(
        ["world-hill", "--mod-folder", "m", "--center", "700,-500"])) == ((700.0, -500.0), True)   # in range: as is
