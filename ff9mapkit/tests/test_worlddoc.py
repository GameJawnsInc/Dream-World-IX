"""Fences for the World tab (:mod:`ff9mapkit.workspace.worlddoc`).

The two laws this surface exists to keep are fenced FIRST, and both are the study's recurring
diseases: construction/tab-show must do NO filesystem work (the startup-spend law), and nothing here
may ever resolve the developer's real install (the round-9 isolation law) -- every game path in this
file is a pinned tmp tree, and the doc's ``game_path_fn`` seam is how tests, snaps, and production
share one code path. Width constants are never asserted (offscreen lies about width); counts, colours,
states, and relationships only.
"""

from __future__ import annotations

import os
import struct

import pytest

pytest.importorskip("PySide6", reason="GUI extra not installed")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")

from PySide6.QtWidgets import QApplication, QPushButton                        # noqa: E402

from ff9mapkit import config                                                   # noqa: E402
from ff9mapkit.editor.theme import pick_palette                                # noqa: E402
from ff9mapkit.workspace import worldscan                                      # noqa: E402
from ff9mapkit.workspace.worlddoc import AtlasCanvas, WorldDoc                 # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _isolate_data_dir(tmp_path, monkeypatch):
    """Every refresh() consults the stock-context cache under provision.cache_dir(), which honours
    $FF9MAPKIT_DATA -- pin it per-test so no test ever reads (or seeds) the developer's real cache
    (the round-9 isolation law; the review's recurring best find is exactly this class)."""
    monkeypatch.setenv("FF9MAPKIT_DATA", str(tmp_path / "data"))


def _mesh_bytes(vcount=12, icount=12, *, salt=0):
    out = bytearray(b"F9WM")
    out += struct.pack("<iiii", 1, vcount, icount, 0)
    for i in range(vcount):
        out += struct.pack("<3f", float(i + salt), 0.0, float(i))
    out += struct.pack("<%di" % icount, *([0] * icount))
    return bytes(out)


def _put(mod, bx, by, name, data, disc=1):
    d = mod / "FF9_Data" / "WorldMap" / f"Disc{disc}" / "0_1" / f"r{by}"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"Block[{bx}][{by}] {name}"
    p.write_bytes(data) if isinstance(data, bytes) else p.write_text(data, encoding="utf-8")
    return p


def _fake_game(tmp_path):
    """A pinned install: FF9CustomMap-world with two adjacent land blocks (one donor'd, one with a
    stale Disc4 mirror) and one water-carry cell -- every visual state the atlas encodes, in three cells."""
    game = tmp_path / "game"
    mod = game / "FF9CustomMap-world"
    t1 = _mesh_bytes(vcount=300, icount=2139)
    _put(mod, 3, 17, "Terrain.ff9mesh", t1)
    _put(mod, 3, 17, "Object.ff9mesh", _mesh_bytes(vcount=40, icount=366))
    _put(mod, 3, 17, "Donor.txt", b"0,0")
    _put(mod, 3, 17, "Terrain.ff9mesh", t1, disc=4)
    _put(mod, 3, 17, "Object.ff9mesh", _mesh_bytes(vcount=40, icount=366), disc=4)
    t2 = _mesh_bytes(vcount=200, icount=900, salt=5)
    _put(mod, 4, 17, "Terrain.ff9mesh", t2)
    stale = bytearray(t2)
    stale[-1] ^= 0xFF                                        # same size, different bytes: the real trap
    _put(mod, 4, 17, "Terrain.ff9mesh", bytes(stale), disc=4)
    _put(mod, 11, 19, "Terrain.ff9mesh", _mesh_bytes(vcount=3, icount=3))     # the arming stub
    _put(mod, 11, 19, "Sea4.ff9mesh", _mesh_bytes(vcount=8, icount=12))
    _put(mod, 11, 19, "Sea4.ff9mesh", _mesh_bytes(vcount=8, icount=12), disc=4)
    _put(mod, 11, 19, "Terrain.ff9mesh", _mesh_bytes(vcount=3, icount=3), disc=4)
    return game


def _cells_in_scene(canvas):
    return [it for it in canvas.scene().items() if it.data(0) == "cell"]


def _seed_stock(game, stock):
    """Write a stock-context cache for the pinned install under the pinned FF9MAPKIT_DATA (see
    _isolate_data_dir) -- the same file a real derive would leave behind."""
    import json
    from ff9mapkit import provision
    from ff9mapkit.workspace import worldscan as ws
    root = provision.cache_dir()
    root.mkdir(parents=True, exist_ok=True)
    (root / ws.STOCK_CACHE_NAME).write_text(json.dumps(
        {"version": 1, "game": str(game), "disc": 1, "rows": ws._rows_encode(stock)}),
        encoding="utf-8")


def test_construction_touches_no_filesystem_and_no_game_path(app, monkeypatch):
    """THE STARTUP-SPEND LAW + THE ISOLATION LAW, fenced with tripwires a no-op satisfies and any
    eager scan FAILS: building the doc (as the Workspace does at construction) must resolve no game
    path and census no tree."""
    def _boom(*a, **k):
        raise AssertionError("WorldDoc touched the machine at construction")
    monkeypatch.setattr(config, "find_game_path", _boom)
    monkeypatch.setattr(worldscan, "scan_tree", _boom)
    monkeypatch.setattr(worldscan, "find_world_trees", _boom)
    doc = WorldDoc(pick_palette("dark"))
    assert doc._stack.currentWidget() is doc._guide_page     # the front door, not the atlas


def test_refresh_with_no_game_teaches_the_locate_path(app, tmp_path):
    def _raise(explicit=None):
        raise config.ConfigError("FF9 install not found (pinned)")
    opened = []
    doc = WorldDoc(pick_palette("dark"), on_setup=lambda: opened.append(1), game_path_fn=_raise)
    doc.refresh(sync=True)
    assert doc._guide_state[0] == "nogame"
    btns = [b for b in doc._guide_page.findChildren(QPushButton)
            if b.objectName() == "accent"]
    assert btns and "Setup" in btns[0].text(), "the accent action is the Setup door"
    btns[0].click()
    assert opened == [1]


def test_a_game_with_no_world_tree_says_so(app, tmp_path):
    (tmp_path / "game" / "FF9CustomMap").mkdir(parents=True)   # a mod folder, but no WorldMap tree
    doc = WorldDoc(pick_palette("dark"), game_path_fn=lambda explicit=None: tmp_path / "game")
    doc.refresh(sync=True)
    assert doc._guide_state[0] == "notrees"


def test_scan_renders_cells_summary_and_crumb(app, tmp_path):
    game = _fake_game(tmp_path)
    doc = WorldDoc(pick_palette("dark"), game_path_fn=lambda explicit=None: game)
    doc.refresh(sync=True)
    assert doc._stack.currentWidget() is doc._atlas_page
    assert len(_cells_in_scene(doc.canvas)) == 3
    s = doc.summary_lbl.text()
    assert "3 blocks" in s and "2 landmasses" in s
    assert "1 stale" in s, "the stale mirror is named in the summary, not hidden in a tooltip"
    assert doc.crumb_label() == "World — FF9CustomMap-world"
    assert doc.folder_box.count() == 1 and doc.folder_box.currentText() == "FF9CustomMap-world"


def test_select_fills_details_and_copy_hands_the_debug_menu_its_coords(app, tmp_path):
    game = _fake_game(tmp_path)
    doc = WorldDoc(pick_palette("dark"), game_path_fn=lambda explicit=None: game)
    doc.refresh(sync=True)
    assert not doc.copy_btn.isEnabled(), "no selection yet -> nothing to copy"
    doc.canvas.select((3, 17))
    assert "Block[3][17]" in doc.sel_title.text() and "land" in doc.sel_title.text()
    assert "centre x 224, z -1120" in doc.sel_facts.text()   # island F's documented placement
    assert "donor 0,0" in doc.sel_facts.text()
    assert "Terrain 713 tris" in doc.sel_parts.text()
    assert doc.copy_btn.isEnabled()
    doc._copy_coords()
    assert QApplication.clipboard().text() == "224 -1120"


def test_the_stale_mirror_wears_warn_in_the_details(app, tmp_path):
    game = _fake_game(tmp_path)
    doc = WorldDoc(pick_palette("dark"), game_path_fn=lambda explicit=None: game)
    doc.refresh(sync=True)
    doc.canvas.select((4, 17))
    assert "stale" in doc.sel_chip.text() and "world-mirror" in doc.sel_chip.text()
    assert doc.sel_chip.property("kind") == "warn" and doc.sel_chip.isVisibleTo(doc)
    doc.canvas.select((3, 17))
    assert "current" in doc.sel_chip.text()
    assert doc.sel_chip.property("kind") == "good"           # the warn kind is LEFT, not latched


def test_the_water_carry_names_its_arming_stub(app, tmp_path):
    game = _fake_game(tmp_path)
    doc = WorldDoc(pick_palette("dark"), game_path_fn=lambda explicit=None: game)
    doc.refresh(sync=True)
    doc.canvas.select((11, 19))
    assert "water" in doc.sel_title.text()
    assert "arming stub" in doc.sel_parts.text()


def test_the_dial_reaches_the_painted_canvas(app, tmp_path):
    """CALIBRE: drive the REAL dial (doc.set_scale, the shell's own call) and read the derived font +
    geometry -- a relationship between two readings of the same lever, offscreen-safe."""
    game = _fake_game(tmp_path)
    doc = WorldDoc(pick_palette("dark"), game_path_fn=lambda explicit=None: game)
    doc.refresh(sync=True)
    f100, c100 = doc.canvas._font(8).pointSize(), doc.canvas.cell_px()
    doc.set_scale(150)
    assert doc.canvas._font(8).pointSize() > f100
    assert doc.canvas.cell_px() > c100
    assert len(_cells_in_scene(doc.canvas)) == 3             # the redraw survives the dial


def test_arrow_keys_walk_the_grid_one_block_at_a_time(app, tmp_path):
    """Plain chart-cursor steps (every block answers now), clamped at the map edge."""
    game = _fake_game(tmp_path)
    doc = WorldDoc(pick_palette("dark"), game_path_fn=lambda explicit=None: game)
    doc.refresh(sync=True)
    doc.canvas.select((3, 17))
    doc.canvas._step_selection((1, 0))
    assert doc._selected == (4, 17)                          # onto the neighbouring deployed block
    doc.canvas._step_selection((0, 1))
    assert doc._selected == (4, 18)                          # onto an EMPTY block -- also selectable
    assert "Block[4][18]" in doc.sel_title.text()
    doc.canvas.select((0, 19))
    doc.canvas._step_selection((0, 1))
    assert doc._selected == (0, 19), "the map edge clamps"


def test_an_empty_ocean_block_is_a_free_site_with_a_paste_ready_command(app, tmp_path):
    """The siting ENHANCEMENT: a clean open-ocean block (stock says nothing, the folder says nothing)
    earns the free-site chip + a runnable world-island command; the selection ring draws even though
    no census cell exists there."""
    game = _fake_game(tmp_path)
    _seed_stock(game, {(12, 12): "L", (13, 12): "~"})
    doc = WorldDoc(pick_palette("dark"), game_path_fn=lambda explicit=None: game)
    doc.refresh(sync=True)
    doc.canvas.select((3, 17))                               # deployed first: measure the strip
    strip = doc.site_btn.parentWidget()
    h_deployed = strip.sizeHint().height()
    doc.canvas.select((2, 2))                                # not stock, not deployed -> clean ocean
    assert "open ocean" in doc.sel_title.text()
    assert doc.sel_chip.text() == "free site" and doc.sel_chip.property("kind") == "good"
    assert doc.site_btn.isVisibleTo(doc._atlas_page)
    assert not doc.open_btn.isVisibleTo(doc._atlas_page), "the site button REPLACES the folder slot"
    assert strip.sizeHint().height() == h_deployed, \
        "a strip that grows on selection shrinks the canvas out from under its own fit"
    assert doc.copy_btn.isEnabled()
    assert [it for it in doc.canvas.scene().items() if it.data(0) == "sel"], \
        "an empty block's selection draws its own ring"
    doc._copy_site_cmd()
    assert QApplication.clipboard().text() == \
        "py -m ff9mapkit world-island --mod-folder FF9CustomMap-world --cell 2,2"
    doc._copy_coords()                                       # centre coords work for ANY block
    assert QApplication.clipboard().text() == "160 -160"


def test_stock_land_and_coastal_water_never_offer_the_command(app, tmp_path):
    game = _fake_game(tmp_path)
    _seed_stock(game, {(12, 12): "L", (13, 12): "~"})
    doc = WorldDoc(pick_palette("dark"), game_path_fn=lambda explicit=None: game)
    doc.refresh(sync=True)
    doc.canvas.select((12, 12))
    assert "stock land" in doc.sel_title.text()
    assert not doc.site_btn.isVisibleTo(doc._atlas_page)
    doc.canvas.select((13, 12))
    assert "coastal water" in doc.sel_title.text()
    assert not doc.site_btn.isVisibleTo(doc._atlas_page)
    doc.canvas.select((3, 17))                               # a deployed block hides it too
    assert not doc.site_btn.isVisibleTo(doc._atlas_page)


def test_unknown_geography_never_certifies_a_free_site(app, tmp_path):
    """No stock cache and an underivable install: the honest answer is 'unknown', never 'free' --
    a siting affordance that guesses is worse than none."""
    game = _fake_game(tmp_path)                              # no seeded stock -> derive fails -> None
    doc = WorldDoc(pick_palette("dark"), game_path_fn=lambda explicit=None: game)
    doc.refresh(sync=True)
    doc.canvas.select((2, 2))
    assert "stock world" in doc.sel_title.text()
    assert "unknown" in doc.sel_parts.text()
    assert not doc.site_btn.isVisibleTo(doc._atlas_page)


def test_a_rescan_keeps_the_selection_when_the_cell_survives(app, tmp_path):
    game = _fake_game(tmp_path)
    doc = WorldDoc(pick_palette("dark"), game_path_fn=lambda explicit=None: game)
    doc.refresh(sync=True)
    doc.canvas.select((3, 17))
    doc.refresh(sync=True)
    assert doc._selected == (3, 17)
    assert "Block[3][17]" in doc.sel_title.text()


def test_the_stock_layer_grounds_the_atlas_but_never_a_deployed_block(app, tmp_path):
    """Seed a stock-context cache for the pinned install: stock land paints as the quiet ground layer,
    EXCEPT under deployed blocks (an override owns its pixel -- no tint bleeding through), and the
    legend names the new fill."""
    game = _fake_game(tmp_path)
    _seed_stock(game, {(0, 0): "L", (1, 0): "L", (3, 17): "L", (11, 19): "~", (12, 12): "L"})
    doc = WorldDoc(pick_palette("dark"), game_path_fn=lambda explicit=None: game)
    doc.refresh(sync=True)
    stock_items = [it for it in doc.canvas.scene().items() if it.data(0) == "stock"]
    # (0,0), (1,0), (12,12) paint; (3,17) is DEPLOYED so it must not; (11,19) is "~" -> never drawn.
    assert len(stock_items) == 3
    assert len(_cells_in_scene(doc.canvas)) == 3             # the override cells are untouched by it
    caps = [w.text() for w in doc._legend_host.findChildren(type(doc.summary_lbl))]
    assert any("stock land" in t for t in caps)


def test_no_stock_cache_means_no_layer_and_no_failure(app, tmp_path):
    game = _fake_game(tmp_path)                              # tmp install: underivable -> None
    doc = WorldDoc(pick_palette("dark"), game_path_fn=lambda explicit=None: game)
    doc.refresh(sync=True)
    assert doc._stack.currentWidget() is doc._atlas_page
    assert not [it for it in doc.canvas.scene().items() if it.data(0) == "stock"]


def test_retheme_redraws_the_canvas_in_the_new_palette(app, tmp_path):
    game = _fake_game(tmp_path)
    doc = WorldDoc(pick_palette("dark"), game_path_fn=lambda explicit=None: game)
    doc.refresh(sync=True)
    light = pick_palette("light")
    doc.retheme(light)
    assert doc.canvas.pal is light
    assert len(_cells_in_scene(doc.canvas)) == 3


def test_the_async_lane_lands_on_the_gui_thread(app, tmp_path):
    """The worker-thread scan (production's lane) must deliver through the signal and finish exactly
    like the sync lane -- polled with real event processing, no sleep-and-hope."""
    import time
    game = _fake_game(tmp_path)
    doc = WorldDoc(pick_palette("dark"), game_path_fn=lambda explicit=None: game)
    doc.refresh()                                            # async: thread + signal
    deadline = time.monotonic() + 10.0
    while doc._busy and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    assert not doc._busy, "the scan never delivered"
    assert doc._stack.currentWidget() is doc._atlas_page
    assert len(_cells_in_scene(doc.canvas)) == 3
    assert doc.rescan_btn.isEnabled() and doc.rescan_btn.text() == "Rescan"
