"""PlaceDoc — click-authoring Rung 3's placement host (studies/click-authoring/PLAN.md).

Pins the host half of Rung 3 without the game: the pure placement ops (one op per drop, into
the OPEN doc's dict), marker derivation + the plan-view height lookup, the hard refusals
(bundled example / no donor / verbatim spawn-arrival), and the click→op→on_edit round trip
over a synthetic camera + walkmesh. The raycast math itself is pinned in
``test_imagefield.py``; the canvas widget half in ``test_workspace_backdrop.py``.
"""

from __future__ import annotations

import math
import os
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")

from PySide6.QtCore import QPoint, QPointF, Qt           # noqa: E402
from PySide6.QtTest import QTest                         # noqa: E402
from PySide6.QtWidgets import QApplication               # noqa: E402

import ff9mapkit                                         # noqa: E402
from ff9mapkit import imagefield as IF                   # noqa: E402
from ff9mapkit.build import donor_field_id               # noqa: E402
from ff9mapkit.editor import forms                       # noqa: E402
from ff9mapkit.scene import guide                        # noqa: E402
from ff9mapkit.workspace import placedoc as P            # noqa: E402
from ff9mapkit.workspace.shell import pick_palette       # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


# --------------------------------------------------------------------------- pure ops
def test_place_npc_appends_with_a_fresh_name():
    data = {}
    l1 = P.place_npc(data, 10.4, -20.6)
    l2 = P.place_npc(data, 30.0, 40.0)
    npcs = data["npc"]
    assert len(npcs) == 2
    assert npcs[0]["pos"] == [10, -21] and npcs[1]["pos"] == [30, 40]      # ints, rounded
    assert npcs[0]["name"] != npcs[1]["name"]                              # names are load-bearing
    assert npcs[0]["name"] in l1 and npcs[1]["name"] in l2
    assert npcs[0]["preset"]                                               # a buildable default
    assert "dialogue" not in npcs[0]        # THE DEFAULT-VALUE LAW: no "..." placeholder — the
    #                                         build's silent-talk channel owns a wordless NPC


def test_place_prop_appends_a_buildable_default():
    data = {}
    P.place_prop(data, -5.0, 7.0)
    (p,) = data["prop"]
    assert p["pos"] == [-5, 7] and p["prop"] == P._DEFAULT_PROP and p["name"]


def test_set_spawn_preserves_other_player_keys():
    data = {"player": {"face": 128}}
    label = P.set_spawn(data, 1.0, 2.0)
    assert data["player"] == {"face": 128, "spawn": [1, 2]}
    assert "spawn" in label


def test_set_arrival_upserts_by_entrance():
    data = {}
    P.set_arrival(data, 1, 10, 10)
    P.set_arrival(data, 2, 20, 20)
    P.set_arrival(data, 1, 30, 30)                       # same entrance -> moved, not duplicated
    rows = data["player"]["arrival"]
    assert [(r["entrance"], r["pos"]) for r in rows] == [(1, [30, 30]), (2, [20, 20])]


# --------------------------------------------------------------------------- markers + height
def test_content_markers_covers_every_placed_kind():
    data = {"npc": [{"name": "A", "pos": [1, 2]}, {"name": "no-pos"}],
            "prop": [{"prop": "barrel", "pos": [3, 4]}],
            "chest": [{"pos": [5, 6], "item": ["Potion", 1]}],
            "player": {"spawn": [7, 8], "arrival": [{"entrance": 2, "pos": [9, 10]}]}}
    marks = {(m["kind"], m["xz"]) for m in P.content_markers(data)}
    assert marks == {("npc", (1.0, 2.0)), ("prop", (3.0, 4.0)), ("chest", (5.0, 6.0)),
                     ("spawn", (7.0, 8.0)), ("arrival", (9.0, 10.0))}
    labels = [m["label"] for m in P.content_markers(data)]
    assert "A" in labels and "arrival 2" in labels


def _flat_quad(y=0.0, x0=-1000, x1=1000, z0=500, z1=2500):
    a, b, c, d = (x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)
    return [(a, b, c), (a, c, d)]


def test_floor_y_at_interpolates_and_resolves_stacks_toward_the_eye():
    tris = _flat_quad(y=5.0)
    assert abs(P.floor_y_at(tris, 0.0, 1500.0) - 5.0) < 1e-9
    stacked = _flat_quad(y=5.0) + _flat_quad(y=-300.0)   # a bridge over a floor at the same (x, z)
    eye = (0.0, -350.0, -2000.0)                          # the camera sits nearer the y=-300 sheet
    assert abs(P.floor_y_at(stacked, 0.0, 1500.0, eye) - (-300.0)) < 1e-9
    # off-mesh: the nearest VERTEX's height, never a silent None (the author must SEE stray content)
    assert abs(P.floor_y_at(tris, 5000.0, 5000.0) - 5.0) < 1e-9
    assert P.floor_y_at([], 0.0, 0.0) is None


# --------------------------------------------------------------------------- donor resolution
def test_donor_field_id_reads_all_three_forms():
    assert donor_field_id({"verbatim_eb": {"donor": 351}}) == 351
    assert donor_field_id({"field": {"source_field": 116}}) == 116
    assert donor_field_id({"field": {"borrow_field": "1205"}}) == 1205
    assert donor_field_id({"field": {"id": 4003}}) is None
    assert donor_field_id({"verbatim_eb": {"donor": True}}) is None       # a bool is not an id


# --------------------------------------------------------------------------- the doc
def _doc(app, on_edit=None):
    calls = []
    d = P.PlaceDoc(pick_palette("dark"), on_edit=on_edit or (lambda m, lb: calls.append((m, lb))))
    d.resize(700, 640)
    d.show()
    QApplication.processEvents()
    return d, calls


def _bundle(tris=None, cam=None):
    tris = tris if tris is not None else _flat_quad()
    return {"donor": 351, "source": ("real", 351), "cam_index": 0, "n_cams": 1,
            "cam": cam or guide.make_camera(26.0, 3000.0, fov_x_deg=42.0),
            "png": None, "tris": tris, "floors": [0] * len(tris)}


def test_bundled_example_refuses_outright(app):
    d, calls = _doc(app)
    ex = Path(ff9mapkit.__file__).parent.parent / "examples" / "vivi-hut" / "hut_int.field.toml"
    d.show_field("HUT", {"verbatim_eb": {"donor": 351}}, ex)
    assert d._blocked and "example" in d._blocked
    assert not any(rb.isEnabled() for rb in d.mode_btns.values())
    assert not d.load_btn.isEnabled()
    d._on_surface_clicked({"xz": (0.0, 1500.0), "pos": (0, 0, 1500), "floor": 0, "stacked": []})
    assert calls == []                                    # the write channel never fired


def test_a_novel_field_is_served_not_refused(app):
    """★ RUNG 7d. Place used to refuse anything without a donor real room and send the author to
    Blender or the Editor forms. That was a test of PROVENANCE; a surface needs a CAMERA and a
    WALKMESH, and a novel field has both -- a composed room's camera is better known than a forked
    one's, because the composer solved it. One predicate blocked the floorplan composer,
    `ff9mapkit new` and the Trace lane at once."""
    d, _ = _doc(app)
    d.show_field("NOVEL", {"field": {"id": 30058}}, Path("C:/somewhere/NOVEL.field.toml"))
    assert d._blocked is None, f"a novel field was refused: {d._blocked}"
    assert d._source == ("project", "C:/somewhere/NOVEL.field.toml".replace("/", os.sep)) or         d._source[0] == "project"
    assert d.load_btn.isEnabled()


def test_an_editable_fork_places_on_its_own_surface_despite_its_donor(app):
    """`import --editable` records `source_field` (so the build emits its ForkDonorPatch row), but it
    ships its OWN scene -- `[[layers]]` over a walkmesh.obj the author may reshape -- so Place must keep
    serving the project's surface, not the donor's real room. A fork without its own layers (native,
    BG-borrow, verbatim) still places on the donor's real room."""
    d, _ = _doc(app)
    path = Path("C:/somewhere/IPSN_EDIT.field.toml")
    d.show_field("IPSN_EDIT", {"field": {"id": 30990, "source_field": 2507},
                               "layers": [{"image": "layer_01016_1.png", "z": 1016}]}, path)
    assert d._donor == 2507 and d._source == ("project", str(path))
    d.show_field("IPSN_NATIVE", {"field": {"id": 30992, "source_field": 2507}}, path)
    assert d._source == ("real", 2507)


def test_forget_surface_drops_a_projects_cached_room_and_only_that(app, tmp_path):
    """A project surface is read from disk ONCE and then served from the cache for the whole
    session -- Load returns the cached one. When the file's walkmesh or camera is rewritten (a
    Trace regenerate), ``forget_surface`` is what makes the next Load read the new floor
    (review finding T38; the shell calls it from the regenerate hook)."""
    d, _ = _doc(app)
    path = tmp_path / "ROOM.field.toml"
    other = tmp_path / "OTHER.field.toml"
    d.show_field("ROOM", {"field": {"id": 30058}}, path)
    key = (d._source, 0)
    assert key[0] == ("project", str(path))
    d._bundles[key] = dict(_bundle(), source=d._source)
    d._bundles[(d._source, 1)] = dict(_bundle(), source=d._source, cam_index=1)   # every camera
    d._bundles[(("project", str(other)), 0)] = dict(_bundle(), source=("project", str(other)))
    d._bundles[(("real", 351), 0)] = _bundle()
    d.forget_surface(str(path).upper() if os.name == "nt" else path)   # a path, however it is cased
    assert sorted(k[0] for k in d._bundles) == sorted([("project", str(other)), ("real", 351)])
    d.on_load()                                        # ...so Load goes back to disk instead of
    assert d._loading == key                           # handing over the stale cached surface


def test_a_load_in_flight_when_the_file_changed_is_thrown_away(app, tmp_path):
    """The loader started reading BEFORE the regenerate rewrote the files: its result is the old
    room. It must not be cached or applied just because it lands after ``forget_surface``."""
    d, _ = _doc(app)
    path = tmp_path / "ROOM.field.toml"
    d.show_field("ROOM", {"field": {"id": 30058}}, path)
    key = (d._source, 0)
    d._loading = key                                   # a load of this project is in flight
    d.forget_surface(path)
    d._on_loaded(key, dict(_bundle(), source=d._source))   # ...and lands with the OLD files
    assert key not in d._bundles and not d.canvas._surface_tris
    assert "changed on disk" in d.status.text() and d.load_btn.isEnabled()
    d._loader.start = lambda *a: None
    d.load_btn.click()                                 # the load the author then asks for is good
    d._on_loaded(key, dict(_bundle(), source=d._source))
    assert key in d._bundles and d.canvas._surface_tris


def test_a_stale_load_stays_in_flight_so_a_second_load_cannot_race_it(app, tmp_path):
    """After a regenerate the shell re-feeds Place, which used to forget the load still running
    and re-enable Load: a second loader for the same room could then start beside it, and
    whichever of the two landed LAST was cached -- possibly the old room. Also: a stale load that
    FAILS must not poison the next good one."""
    d, _ = _doc(app)
    path = tmp_path / "ROOM.field.toml"
    d.show_field("ROOM", {"field": {"id": 30058}}, path)
    key = (d._source, 0)
    d._loading = key
    d.forget_surface(path)
    d.show_none()
    d.show_field("ROOM", {"field": {"id": 30058}}, path)   # the shell's re-feed after the regenerate
    assert d._loading == key                           # still in flight: on_load() will not start a twin
    started = []
    d._loader.start = lambda *a: started.append(a)
    d.on_load()
    assert started == []
    d._on_load_failed(key, "the stale one died")
    assert d._stale_load is None
    d.on_load()
    d._on_loaded(key, dict(_bundle(), source=d._source))   # the next good load is kept, not thrown away
    assert key in d._bundles


def test_a_field_with_no_file_on_disk_still_refuses(app):
    """The surface is resolved FROM THE FILE, so an unsaved doc has nothing to resolve. The
    refusal moved from provenance to that -- it did not disappear."""
    d, _ = _doc(app)
    d.show_field("NOVEL", {"field": {"id": 30058}}, None)
    assert d._blocked and "saved" in d._blocked
    assert not d.load_btn.isEnabled()


def test_verbatim_refuses_spawn_and_arrival_but_places_npc(app):
    d, calls = _doc(app)
    data = {"verbatim_eb": {"donor": 351}}
    d.show_field("FORK", data, Path("C:/somewhere/FORK.field.toml"))
    assert d._blocked is None and d._donor == 351
    d._bundles[(("real", 351), 0)] = _bundle()
    d._apply_bundle(d._bundles[(("real", 351), 0)], refit=True)
    assert not d.mode_btns["spawn"].isEnabled() and not d.mode_btns["arrival"].isEnabled()
    assert d.mode_btns["npc"].isEnabled() and d.mode_btns["prop"].isEnabled()
    assert "party band" in d.status.text()                # the seating note is surfaced
    d._on_surface_clicked({"xz": (12.0, 900.0), "pos": (12.0, 0.0, 900.0), "floor": 0,
                           "stacked": [{"xz": (12.0, 900.0), "pos": (12.0, 0.0, 900.0),
                                        "floor": 0, "tri": 0, "s": 1.0}]})
    assert len(calls) == 1 and calls[0][0] == "FORK" and "NPC" in calls[0][1]
    assert data["npc"][0]["pos"] == [12, 900]


def test_a_real_canvas_click_places_through_the_raycast(app):
    """End to end over the widget: a mouse click on the loaded surface raycasts the mesh
    (click_to_surface + the round-trip tripwire) and lands ONE op in the open dict."""
    d, calls = _doc(app)
    data = {"field": {"source_field": 351}}
    d.show_field("FORK", data, Path("C:/somewhere/FORK.field.toml"))
    d._bundles[(("real", 351), 0)] = _bundle()
    d._apply_bundle(d._bundles[(("real", 351), 0)], refit=True)
    QApplication.processEvents()
    d.mode_btns["spawn"].setChecked(True)                 # non-verbatim: spawn IS placeable
    wpt = d.canvas.world_to_click((0.0, 1500.0))          # mid-floor, below the horizon
    pos = QPoint(round(wpt.x()), round(wpt.y()))
    QTest.mouseClick(d.canvas.viewport(), Qt.MouseButton.LeftButton, pos=pos)
    assert len(calls) == 1 and "spawn" in calls[0][1]
    sx, sz = data["player"]["spawn"]
    ex, ez = d.canvas.click_to_world(QPointF(pos))        # the same integer pixel the click used
    assert math.hypot(sx - ex, sz - ez) < 1.0             # its own floor point, rounded to ints


def test_markers_follow_the_open_data_on_refeed(app):
    d, _ = _doc(app)
    data = {"field": {"source_field": 351}, "npc": [{"name": "A", "pos": [0, 1500]}]}
    path = Path("C:/somewhere/FORK.field.toml")
    d.show_field("FORK", data, path)
    d._bundles[(("real", 351), 0)] = _bundle()
    d._apply_bundle(d._bundles[(("real", 351), 0)], refit=True)
    assert len(d.canvas._markers) == 1 and d.canvas._markers[0]["label"] == "A"
    data["npc"].append({"name": "B", "pos": [100, 900]})
    d.show_field("FORK", data, path)                      # the shell's re-feed after an edit
    assert {m["label"] for m in d.canvas._markers} == {"A", "B"}


def test_stacked_hits_route_through_the_chooser(app, monkeypatch):
    d, calls = _doc(app)
    data = {"field": {"source_field": 351}}
    d.show_field("FORK", data, Path("C:/somewhere/FORK.field.toml"))
    d._bundles[(("real", 351), 0)] = _bundle()
    d._apply_bundle(d._bundles[(("real", 351), 0)], refit=True)
    rows = [{"xz": (0.0, 1500.0), "pos": (0.0, -300.0, 1500.0), "floor": 1, "tri": 2, "s": 1.0},
            {"xz": (0.0, 1500.0), "pos": (0.0, 0.0, 1500.0), "floor": 0, "tri": 0, "s": 2.0}]
    picked = []
    monkeypatch.setattr(d, "_choose_hit", lambda rr: picked.append(rr) or rr[1])
    payload = dict(rows[0])
    payload["stacked"] = rows
    d._on_surface_clicked(payload)
    assert picked and picked[0] == rows                   # >1 hit ALWAYS asks, never guesses
    assert len(calls) == 1 and data["npc"][0]["pos"] == [0, 1500]


# --------------------------------------------------------------------------- prop form + picker
def test_prop_spec_round_trips():
    e = {"name": "cask", "prop": "barrel", "pos": [120, 150], "face": 64, "collision": False,
         "requires_flag": "lit", "attach_to": "barkeep", "bone": 13}
    assert forms.build_entity(forms.PROP_SPEC, forms.entity_to_values(forms.PROP_SPEC, e)) == e
    lean = {"model": "GEO_ACC_F0_CSK", "pos": [-200, 150]}
    assert forms.build_entity(forms.PROP_SPEC, forms.entity_to_values(forms.PROP_SPEC, lean)) == lean


def test_field_cards_offer_place_for_already_forked_rooms(app):
    from ff9mapkit.workspace.fieldcards import FieldCardPicker, field_entries
    entries = field_entries()
    if not entries:
        pytest.skip("no baked realfield catalog on this machine")
    fid = entries[0].id
    dlg = FieldCardPicker(None, pick_palette("dark"), None, initial=str(fid),
                          place_members={fid: "MYFORK"})
    assert dlg.place_btn is not None
    it = dlg._items.get(fid)
    assert it is not None
    dlg.listw.setCurrentItem(it)
    QApplication.processEvents()
    assert dlg.place_btn.isEnabled()
    assert "MYFORK" in dlg.info.text()
    dlg._place()
    assert dlg.place_member == "MYFORK" and dlg.result is None
    dlg.deleteLater()


def test_picker_without_place_context_has_no_place_button(app):
    from ff9mapkit.workspace.fieldcards import FieldCardPicker, field_entries
    if not field_entries():
        pytest.skip("no baked realfield catalog on this machine")
    dlg = FieldCardPicker(None, pick_palette("dark"), None)
    assert dlg.place_btn is None
    dlg.deleteLater()


# --------------------------------------------------------------------------- rung 4: regions
def test_region_ops_write_and_delete_rows():
    data = {}
    l1 = P.place_gateway(data, [(0.4, 0.6), (100, 0), (100, 100), (0, 100)], 4005, 2)
    l2 = P.place_gateway(data, [(200, 0), (300, 0), (300, 100), (200, 100)], 4007, 0)
    g0, g1 = data["gateway"]
    assert g0["zone"][0] == [0, 1] and g0["to"] == 4005 and g0["entrance"] == 2
    assert "entrance" not in g1                            # 0 = the default, not written
    assert g0["name"] != g1["name"] and g0["name"] in l1 and g1["name"] in l2
    l3 = P.place_event(data, [(500, 0), (600, 0), (600, 100), (500, 100)])
    (ev,) = data["event"]
    assert ev["zone"][2] == [600, 100] and ev["message"] and ev["name"] in l3
    P.move_zone(data, "event", 0, [(510, 0), (610, 0), (610, 100), (510, 100)])
    assert data["event"][0]["zone"][0] == [510, 0]
    lbl = P.delete_region(data, "gateway", 0)
    assert len(data["gateway"]) == 1 and data["gateway"][0]["to"] == 4007
    assert g0["name"] in lbl


def test_region_rows_normalizes_and_judges_both_laws():
    doubled = [[0, 0], [100, 0], [100, 100], [0, 100], [0, 100]]     # the stored safe form
    dart = [[70, 1060], [100, 1000], [100, 1100], [0, 1100]]         # notch inside the hull
    data = {"gateway": [{"name": "door0", "to": 4005, "entrance": 2, "zone": doubled},
                        {"to": 4007, "zone": [[50, 50], [150, 50], [150, 150], [50, 150]]}],
            "event": [{"name": "spiky", "zone": dart},
                      {"name": "no-zone"}]}
    rows = P.region_rows(data)
    assert [(r["kind"], r["index"]) for r in rows] == [("gateway", 0), ("gateway", 1),
                                                       ("event", 0)]
    assert len(rows[0]["quad"]) == 4                       # the doubled 5th point undisplayed
    assert "door0" in rows[0]["label"] and "4005" in rows[0]["label"] and "e2" in rows[0]["label"]
    assert rows[0]["warn"] and "overlaps" in rows[0]["warn"]          # doubled vs the second
    assert rows[1]["warn"] and "overlaps" in rows[1]["warn"]
    assert rows[2]["warn"] and "over-trigger" in rows[2]["warn"]      # the fan audit, live


def test_regions_tool_swaps_clusters_and_canvas_mode(app):
    d, _ = _doc(app)
    data = {"field": {"source_field": 351}}
    d.show_field("FORK", data, Path("C:/somewhere/FORK.field.toml"))
    d._bundles[(("real", 351), 0)] = _bundle()
    d._apply_bundle(d._bundles[(("real", 351), 0)], refit=True)
    assert d.tools.current() == "place"
    assert d.canvas._place_mode and not d.canvas._region_mode
    assert d.mode_btns["npc"].isVisible() and not d.rkind_btns["gateway"].isVisible()
    d.tools.set_current("regions")
    assert d.canvas._region_mode and not d.canvas._place_mode
    assert not d.mode_btns["npc"].isVisible() and d.rkind_btns["gateway"].isVisible()
    assert d.gw_to.isVisible() and d.gw_ent.isVisible()    # the gateway sub-cluster
    d.rkind_btns["event"].setChecked(True)
    assert not d.gw_to.isVisible()                         # events carry no target boxes
    d.tools.set_current("place")
    assert d.canvas._place_mode and d.mode_btns["npc"].isVisible()


def test_the_no_field_row_shows_one_cluster_and_its_width(app):
    """The fresh Place tab (no field fed) shows ONLY the Place tool's cluster, so its minimum
    width is one tool's row, never both clusters' sum. Uncaught, the Regions radios + the two
    gateway spinboxes sat beside the Place radios until a field was fed: PlaceDoc's polished
    minimum went 895 -> 1164px natively and lifted the WHOLE window floor 1165 -> 1434, clipping
    the Inspector at 1280. Widths are relative here (offscreen fonts are fiction)."""
    d, _ = _doc(app)
    assert d.tools.current() == "place"
    assert d.mode_btns["npc"].isVisibleTo(d)
    hidden = [d.rkind_btns["gateway"], d.rkind_btns["event"], d.gw_to_label, d.gw_to,
              d.gw_ent_label, d.gw_ent]
    assert not any(w.isVisibleTo(d) for w in hidden), "the Regions cluster leaks into Place"
    fresh = d.minimumSizeHint().width()
    widths = {}
    for tool in ("regions", "place"):                  # each tool's OWN row, measured live
        d.tools.set_current(tool)
        QApplication.processEvents()
        widths[tool] = d.minimumSizeHint().width()
    assert fresh == widths["place"], (fresh, widths)
    assert fresh <= max(widths.values()), (fresh, widths)


def test_a_drawn_quad_lands_one_gateway_row(app):
    d, calls = _doc(app)
    data = {"field": {"source_field": 351}}
    d.show_field("FORK", data, Path("C:/somewhere/FORK.field.toml"))
    d._bundles[(("real", 351), 0)] = _bundle()
    d._apply_bundle(d._bundles[(("real", 351), 0)], refit=True)
    d.tools.set_current("regions")
    d.gw_to.setValue(4005)
    d.gw_ent.setValue(3)
    quad = [(-200.0, 800.0), (200.0, 800.0), (200.0, 1200.0), (-200.0, 1200.0)]
    d._on_region_drawn(quad)
    assert len(calls) == 1 and "gateway" in calls[0][1]
    (gw,) = data["gateway"]
    assert gw["to"] == 4005 and gw["entrance"] == 3
    assert gw["zone"] == [[-200, 800], [200, 800], [200, 1200], [-200, 1200]]
    assert len(d.canvas._regions) == 1                     # fed straight back to the canvas
    d.rkind_btns["event"].setChecked(True)
    d._on_region_drawn([(500.0, 800.0), (700.0, 800.0), (700.0, 1000.0), (500.0, 1000.0)])
    assert len(calls) == 2 and data["event"][0]["name"]


def test_region_change_and_delete_route_by_row(app):
    d, calls = _doc(app)
    data = {"field": {"source_field": 351},
            "gateway": [{"name": "door0", "to": 4005,
                         "zone": [[0, 500], [100, 500], [100, 600], [0, 600]]}],
            "event": [{"name": "zone0", "message": "hi",
                       "zone": [[300, 500], [400, 500], [400, 600], [300, 600]]}]}
    d.show_field("FORK", data, Path("C:/somewhere/FORK.field.toml"))
    d._bundles[(("real", 351), 0)] = _bundle()
    d._apply_bundle(d._bundles[(("real", 351), 0)], refit=True)
    d.tools.set_current("regions")
    assert len(d.canvas._regions) == 2
    d._on_region_changed(1, [(310, 500), (410, 500), (410, 600), (310, 600)])
    assert data["event"][0]["zone"][0] == [310, 500]       # the EVENT row moved, not the gateway
    assert data["gateway"][0]["zone"][0] == [0, 500]
    d._on_region_deleted(0)
    assert data["gateway"] == [] and len(data["event"]) == 1
    assert len(calls) == 2                                 # one on_edit per gesture


def test_blocked_fields_disable_the_tool_strip(app):
    d, calls = _doc(app)
    ex = Path(ff9mapkit.__file__).parent.parent / "examples" / "vivi-hut" / "hut_int.field.toml"
    d.show_field("HUT", {"verbatim_eb": {"donor": 351}}, ex)
    assert not d.tools.button("place").isEnabled()
    assert not d.tools.button("regions").isEnabled()
    d._on_region_drawn([(0, 0), (10, 0), (10, 10), (0, 10)])
    assert calls == [] and "gateway" not in ({} if d._data is None else d._data)


def test_floor_y_at_stays_importable_from_placedoc():
    assert P.floor_y_at is IF.floor_y_at                   # the moved owner, aliased


def test_place_retarget_routes_by_row(app, monkeypatch):
    d, calls = _doc(app)
    data = {"field": {"source_field": 351},
            "gateway": [{"name": "door0", "to": 0,
                         "zone": [[0, 500], [100, 500], [100, 600], [0, 600]]}]}
    d.show_field("FORK", data, Path("C:/somewhere/FORK.field.toml"))
    d._bundles[(("real", 351), 0)] = _bundle()
    d._apply_bundle(d._bundles[(("real", 351), 0)], refit=True)
    d.tools.set_current("regions")
    assert d.canvas._regions[0]["warn"] and "NO TARGET" in d.canvas._regions[0]["warn"]
    monkeypatch.setattr(d, "_ask_field_id", lambda cur: 301)
    d._on_region_retarget(0)
    assert data["gateway"][0]["to"] == 301 and len(calls) == 1
    assert d.canvas._regions[0]["warn"] is None            # the warn clears with the fix


def test_place_reword_routes_by_row(app, monkeypatch):
    d, calls = _doc(app)
    data = {"field": {"source_field": 351},
            "event": [{"name": "zone0", "message": "...",
                       "zone": [[0, 500], [100, 500], [100, 600], [0, 600]]}]}
    d.show_field("FORK", data, Path("C:/somewhere/FORK.field.toml"))
    d._bundles[(("real", 351), 0)] = _bundle()
    d._apply_bundle(d._bundles[(("real", 351), 0)], refit=True)
    d.tools.set_current("regions")
    assert d.canvas._regions[0]["warn"] and "placeholder" in d.canvas._regions[0]["warn"]
    monkeypatch.setattr(d, "_ask_message", lambda cur: "Watch your step.")
    d._on_region_reword(0)
    assert data["event"][0]["message"] == "Watch your step." and len(calls) == 1
    assert d.canvas._regions[0]["warn"] is None            # the warn clears with the words


@pytest.fixture(autouse=True)
def _deterministic_qt_teardown(qt_drain):
    """Widgets die HERE, not in a forced GC pass (THE GC-CHILD LAW's teardown half)."""
    yield
    qt_drain()


# ------------------------------------------------------------------ Rung 7d: novel fields place

def test_a_composed_room_builds_a_place_surface_with_an_exact_click(tmp_path):
    """★ THE PAYOFF, end to end and Qt-free. Compose a two-room dungeon with the real composer,
    then build a Place surface from one of its rooms and raycast canvas clicks against it.

    The round trip is the thing: `click_to_surface` -> world -> `cam.to_canvas` must land back on
    the pixel that was clicked. A composed room's camera is EXACT (the composer solved it), so this
    is not "close enough" -- it is 1e-14 px, and any drift means the surface and the build disagree
    about where the floor is."""
    from ff9mapkit import floorplan as FP
    from ff9mapkit import imagefield as IF
    from ff9mapkit.scene import cam as CAM
    from ff9mapkit.workspace import placedoc as PD

    plan = {"name": "D", "mod_folder": "FF9CustomMap", "id_base": 30700, "entry": "A",
            "rooms": [{"name": "A", "poly": [[0, 0], [2400, 0], [2400, 1800], [0, 1800]]}],
            "doors": []}
    FP.compose_and_emit(plan, tmp_path, log=None)
    toml = next((tmp_path / "A").glob("*.field.toml"))

    b = PD.build_surface_from_project(toml)
    assert b["donor"] is None and b["source"][0] == "project"
    assert b["tris"] and b["n_cams"] >= 1
    assert b["png"], "the room's own [[layers]] did not composite into a backdrop"

    cam = b["cam"]
    W, H = cam.range
    worst, n = 0.0, 0
    for cx in range(40, W - 40, max(1, (W - 80) // 6)):
        for cy in (int(H * 0.72), int(H * 0.86)):
            try:
                hit = IF.click_to_surface(cam, b["tris"], (cx, cy))
            except Exception:                                   # noqa: BLE001 -- off the mesh
                continue
            back = CAM.to_canvas(hit["pos"], cam)
            worst = max(worst, abs(back[0] - cx), abs(back[1] - cy))
            n += 1
    assert n >= 6, f"only {n} clicks landed on the composed floor"
    assert worst < 1e-6, f"click round-trip drifted {worst:.2e}px"


def test_a_scrolling_room_places_too(tmp_path):
    """A wide room composes with `range = [960, 448]` and `[camera.scroll]`. `resolve_cameras`
    honours both, so the surface Place raycasts against is the WIDE one -- if it silently fell back
    to 384 the author would place content against the wrong frame and never see why."""
    from ff9mapkit import floorplan as FP
    from ff9mapkit.workspace import placedoc as PD

    plan = {"name": "D", "mod_folder": "FF9CustomMap", "id_base": 30700, "entry": "A",
            "rooms": [{"name": "A", "poly": [[0, 0], [9762, 0], [9762, 2200], [0, 2200]]}],
            "doors": []}
    FP.compose_and_emit(plan, tmp_path, log=None)
    toml = next((tmp_path / "A").glob("*.field.toml"))
    b = PD.build_surface_from_project(toml)
    assert list(b["cam"].range) == [960, 448], f"Place resolved {list(b['cam'].range)}, not the scroll range"


# ------------------------------------------------------------------ batch 2: the surface's freshness
def _compose_room(tmp_path, name="A"):
    """One real composed room on disk -> (its field.toml path, its parsed dict)."""
    import tomllib
    from ff9mapkit import floorplan as FP
    plan = {"name": "D", "mod_folder": "FF9CustomMap", "id_base": 30700, "entry": name,
            "rooms": [{"name": name, "poly": [[0, 0], [2400, 0], [2400, 1800], [0, 1800]]}],
            "doors": []}
    FP.compose_and_emit(plan, tmp_path, log=None)
    toml = next((tmp_path / name).glob("*.field.toml"))
    return toml, tomllib.loads(toml.read_text(encoding="utf-8"))


def _wait(pred, ms=20000):
    for _ in range(ms // 20):
        if pred():
            return True
        QTest.qWait(20)
    return pred()


def _x_extent(tris):
    xs = [v[0] for tr in tris for v in tr]
    return round(min(xs)), round(max(xs))


def test_load_rereads_a_project_room_that_changed_on_disk(app, tmp_path):
    """Review finding P4. A PROJECT surface used to be read from disk once and then handed back
    from the cache by every later "Load the room", so a walkmesh re-exported from Blender or
    recomposed in Floorplan never reached Place: clicks kept raycasting the OLD floor. An explicit
    Load of a project room now goes back to disk (it is cheap); a donor room stays cached."""
    toml, data = _compose_room(tmp_path)
    d, _ = _doc(app)
    d.show_field("A", data, toml)
    assert d._source[0] == "project"
    d.load_btn.click()
    assert _wait(lambda: d._bundle() is not None and d.canvas._surface_tris), d.status.text()
    x0, x1 = _x_extent(d.canvas._surface_tris)
    obj = toml.parent / "walkmesh.obj"                  # the floor re-exported at half its width
    lines = []
    for ln in obj.read_text(encoding="utf-8").splitlines():
        if ln.startswith("v "):
            _v, x, rest = ln.split(" ", 2)
            ln = f"v {float(x) / 2} {rest}"
        lines.append(ln)
    obj.write_text("\n".join(lines) + "\n", encoding="utf-8")
    first = d._bundle()
    d.load_btn.click()
    _wait(lambda: d._bundle() is not first and d._loading is None)
    got = _x_extent(d.canvas._surface_tris)
    assert got == (round(x0 / 2), round(x1 / 2)), f"Load kept the old floor {got}, not the re-exported one"


def test_a_same_named_room_in_another_file_does_not_keep_the_old_surface(app, tmp_path):
    """Review finding P5. Every traced project is called PICTURE by default. "Same field" was
    decided by that NAME, so opening another PICTURE kept the previous room's art and walkmesh
    armed, and a click raycast against the OLD room was written into the NEW file's doc."""
    d, calls = _doc(app)
    one, two = tmp_path / "one" / "PICTURE.field.toml", tmp_path / "two" / "PICTURE.field.toml"
    first, second = {"field": {"id": 30058}}, {"field": {"id": 30059}}
    d.show_field("PICTURE", first, one)
    d._bundles[(d._source, 0)] = dict(_bundle(), source=d._source)
    d._apply_bundle(d._bundle(), refit=True)
    QApplication.processEvents()
    wpt = d.canvas.world_to_click((0.0, 1500.0))
    pos = QPoint(round(wpt.x()), round(wpt.y()))
    d.show_field("PICTURE", second, two)                 # the shell's feed for the other project
    assert not d.canvas._place_mode and not d.canvas._surface_tris
    QTest.mouseClick(d.canvas.viewport(), Qt.MouseButton.LeftButton, pos=pos)
    assert calls == [] and "npc" not in second
    d.show_field("PICTURE", second, two)                 # a re-feed of the SAME file keeps its view
    d._bundles[(d._source, 0)] = dict(_bundle(), source=d._source)
    d._apply_bundle(d._bundle(), refit=True)
    d.show_field("PICTURE", second, two)
    assert d.canvas._place_mode and d.canvas._surface_tris


def test_a_fork_that_gains_its_own_art_drops_the_donor_surface(app):
    """Same name, same file, but the surface's SOURCE moved: the fork now ships its own [[layers]]
    (an `import --editable` scene), so the donor's real room it was placed on is not its room."""
    d, _ = _doc(app)
    path = Path("C:/somewhere/FORK.field.toml")
    d.show_field("FORK", {"field": {"source_field": 351}}, path)
    d._bundles[(("real", 351), 0)] = _bundle()
    d._apply_bundle(d._bundle(), refit=True)
    assert d.canvas._place_mode
    d.show_field("FORK", {"field": {"source_field": 351},
                          "layers": [{"image": "back.png", "z": 1000}]}, path)
    assert d._source[0] == "project"
    assert not d.canvas._place_mode and not d.canvas._surface_tris


@pytest.mark.parametrize("a_ends", ["fails", "succeeds"])
def test_a_late_load_of_the_previous_room_does_nothing_visible_here(app, tmp_path, monkeypatch, a_ends):
    """Review finding P6. Load room A, switch to B and Load it, and only then A's load ends: A's
    error used to be painted on B, and either ending re-enabled Load while B was still in flight
    (a second click started a twin loader). Driven through the real loader thread."""
    import threading
    gate_a, gate_b, a_done = threading.Event(), threading.Event(), threading.Event()
    a, b = tmp_path / "A.field.toml", tmp_path / "B.field.toml"

    def fake(ref, ci=0):
        if Path(ref) == a:
            gate_a.wait(10)
            a_done.set()
            if a_ends == "fails":
                raise RuntimeError("A blew up")
        else:
            gate_b.wait(10)
        return dict(_bundle(), source=("project", str(ref)), cam_index=ci)

    monkeypatch.setattr(P, "build_surface_from_project", fake)
    d, _ = _doc(app)
    d.show_field("A", {"field": {"id": 30058}}, a)
    d.load_btn.click()
    d.show_field("B", {"field": {"id": 30059}}, b)
    d.load_btn.click()
    b_key = (("project", str(b)), 0)
    assert d._loading == b_key
    gate_a.set()
    assert a_done.wait(10)
    QTest.qWait(300)                                     # A's queued result is delivered
    assert "blew up" not in d.status.text()
    assert d._loading == b_key and not d.load_btn.isEnabled(), "Load re-enabled while B is in flight"
    assert not d.canvas._surface_tris
    gate_b.set()
    assert _wait(lambda: d._loading is None and d.canvas._surface_tris), d.status.text()
    assert d.load_btn.isEnabled()


def test_a_camera_left_mid_load_does_not_land_over_the_one_shown(app):
    """Pick camera 1 (its load starts), go back to camera 0 (cached, shown at once): camera 1's
    load then lands. It is cached for next time, but the canvas keeps showing camera 0."""
    d, _ = _doc(app)
    d.show_field("FORK", {"field": {"source_field": 351}}, Path("C:/somewhere/FORK.field.toml"))
    cam0 = dict(_bundle(), n_cams=2)
    cam1 = dict(_bundle(tris=_flat_quad(x0=-50, x1=50)), n_cams=2, cam_index=1)
    d._bundles[(("real", 351), 0)] = cam0
    d._loader.start = lambda *a: None
    d.load_btn.click()
    assert d.cam_box.isVisible()
    d.cam_box.setCurrentIndex(1)
    assert d._loading == (("real", 351), 1)
    d.cam_box.setCurrentIndex(0)
    d._loader.loaded.emit((("real", 351), 1), cam1)
    assert d.canvas._surface_tris == cam0["tris"]
    assert d._bundles[(("real", 351), 1)]["tris"] == cam1["tris"] and d._loading is None and d.load_btn.isEnabled()


def test_a_load_ending_after_the_field_closed_leaves_load_off(app, tmp_path):
    d, _ = _doc(app)
    path = tmp_path / "ROOM.field.toml"
    d.show_field("ROOM", {"field": {"id": 30058}}, path)
    d._loader.start = lambda *a: None
    d.load_btn.click()
    key = d._loading
    d.show_none()                                      # the project was closed mid-load
    d._loader.loaded.emit(key, dict(_bundle(), source=key[0]))
    assert not d.load_btn.isEnabled() and not d.canvas._surface_tris


def test_a_stale_load_of_the_previous_room_says_nothing_on_the_next(app, tmp_path):
    """A's load was marked stale (its files were rewritten) and the author moved on to B: when it
    lands, B must not be told that ITS room changed on disk."""
    d, _ = _doc(app)
    a, b = tmp_path / "A.field.toml", tmp_path / "B.field.toml"
    d.show_field("A", {"field": {"id": 30058}}, a)
    d._loader.start = lambda *a: None
    d.load_btn.click()
    key = d._loading
    d.forget_surface(a)
    d.show_field("B", {"field": {"id": 30059}}, b)
    d._loader.loaded.emit(key, dict(_bundle(), source=key[0]))
    assert "changed on disk" not in d.status.text() and d.load_btn.isEnabled()
    assert key not in d._bundles


def _clamping_builder(n_cams_of):
    """A stand-in for build_surface_from_project that clamps the camera like the real one."""
    def fake(ref, ci=0):
        n = n_cams_of[Path(ref).parent.name]
        ci = max(0, min(int(ci), n - 1))
        tris = _flat_quad(x0=-100 * (ci + 1), x1=100 * (ci + 1))
        return dict(_bundle(tris=tris), source=("project", str(ref)), cam_index=ci, n_cams=n)
    return fake


def test_a_camera_picked_in_one_file_is_not_carried_to_another_of_its_name(app, tmp_path, monkeypatch):
    """Review finding P29. The camera pick was remembered per member NAME: camera 1 picked in one
    PICTURE was requested for the next PICTURE, which has one camera. The builder clamped it to 0,
    the result never matched the pick, and "Load the room" never applied -- forever."""
    n_cams = {"one": 2, "two": 1, "three": 2}
    monkeypatch.setattr(P, "build_surface_from_project", _clamping_builder(n_cams))
    d, _ = _doc(app)
    one, two = tmp_path / "one" / "PICTURE.field.toml", tmp_path / "two" / "PICTURE.field.toml"
    d.show_field("PICTURE", {"field": {"id": 30058}}, one)
    d.load_btn.click()
    assert _wait(lambda: d._loading is None and d.cam_box.isVisible()), d.status.text()
    d.cam_box.setCurrentIndex(1)
    assert _wait(lambda: d._loading is None and d.canvas._surface_tris
                 and _x_extent(d.canvas._surface_tris) == (-200, 200)), d.status.text()
    d.show_field("PICTURE", {"field": {"id": 30059}}, two)
    d.load_btn.click()
    assert _wait(lambda: d._loading is None and d.canvas._place_mode), d.status.text()
    assert _x_extent(d.canvas._surface_tris) == (-100, 100)
    three = tmp_path / "three" / "PICTURE.field.toml"   # two cameras too: it opens on ITS camera 0
    d.show_field("PICTURE", {"field": {"id": 30060}}, three)
    d.load_btn.click()
    assert _wait(lambda: d._loading is None and d.canvas._place_mode), d.status.text()
    assert _x_extent(d.canvas._surface_tris) == (-100, 100) and d.cam_box.currentIndex() == 0


def test_a_camera_pick_the_room_no_longer_has_follows_the_clamp(app, tmp_path, monkeypatch):
    """The same file, re-exported with fewer cameras: the pick is clamped with it, not stuck."""
    n_cams = {"one": 2}
    monkeypatch.setattr(P, "build_surface_from_project", _clamping_builder(n_cams))
    d, _ = _doc(app)
    one = tmp_path / "one" / "PICTURE.field.toml"
    d.show_field("PICTURE", {"field": {"id": 30058}}, one)
    d.load_btn.click()
    assert _wait(lambda: d._loading is None and d.cam_box.isVisible()), d.status.text()
    d.cam_box.setCurrentIndex(1)
    assert _wait(lambda: d._loading is None and _x_extent(d.canvas._surface_tris) == (-200, 200))
    n_cams["one"] = 1                                   # camera 1 is gone from the file
    d.load_btn.click()
    assert _wait(lambda: d._loading is None and d.canvas._place_mode
                 and _x_extent(d.canvas._surface_tris) == (-100, 100)), d.status.text()
    assert not d.cam_box.isVisible()
    assert d._bundle()["n_cams"] == 1, "markers and regions still read the vanished camera's surface"


def test_an_auto_walkmesh_under_camera_1_is_the_floor_the_build_ships(tmp_path):
    """Review finding E4. The build frames an AUTO walkmesh with camera 0 (the primary camera
    drives the walkmesh frame), but Place resolved it with the SELECTED camera: under camera 1 it
    accepted clicks on a floor the game will not have. The floor is camera 0's under every
    camera; the selected camera only draws it and casts the clicks."""
    import re
    from ff9mapkit import build as B
    from ff9mapkit.scene import bgi
    toml, _ = _compose_room(tmp_path)
    txt = toml.read_text(encoding="utf-8")
    cams = ('[[camera]]\nentry_settle = "auto"\npitch = 48.0\ndistance = 4482\nfov = 42.2\n\n'
            '[[camera]]\npitch = 30.0\ndistance = 3000\nfov = 42.2\nyaw = 35\n')
    txt = re.sub(r"\[camera\]\n(?:[^\[\n].*\n)*", cams + "\n", txt, count=1)
    txt = txt.replace('[walkmesh]\nobj = "walkmesh.obj"', "[walkmesh]\nauto = true")
    assert "auto = true" in txt and txt.count("[[camera]]") == 2
    toml.write_text(txt, encoding="utf-8")
    proj = B.FieldProject.load(str(toml))
    shipped, _f = IF.mesh_world_tris(bgi.BgiWalkmesh.from_bytes(
        B.resolve_walkmesh(proj, B.resolve_camera(proj))))
    surf = P.build_surface_from_project(toml, 1)
    assert surf["cam_index"] == 1 and surf["cam"].range == B.resolve_cameras(proj)[1].range
    assert surf["tris"] == shipped, "Place's camera-1 floor is not the walkmesh the build ships"


def _halve_walkmesh(toml):
    obj = toml.parent / "walkmesh.obj"
    lines = []
    for ln in obj.read_text(encoding="utf-8").splitlines():
        if ln.startswith("v "):
            _v, x, rest = ln.split(" ", 2)
            ln = f"v {float(x) / 2} {rest}"
        lines.append(ln)
    obj.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_coming_back_to_place_does_not_rearm_a_project_room_changed_on_disk(app, tmp_path):
    """Review finding P4, after review. Only an explicit Load used to re-read a project room: the
    shell's re-feed on coming back to the tab re-armed the CACHED floor, and a click outside the
    re-exported walkmesh was written into the doc. Leaving the tab drops a project surface."""
    toml, data = _compose_room(tmp_path)
    d, calls = _doc(app)
    d.show_field("A", data, toml)
    d.load_btn.click()
    assert _wait(lambda: d._bundle() is not None and d.canvas._surface_tris), d.status.text()
    x0, x1 = _x_extent(d.canvas._surface_tris)
    d.show_field("A", data, toml)                       # an edit re-feed while staying keeps it
    assert d.canvas._place_mode and d.canvas._surface_tris
    d.hide()                                            # the author goes to another tab...
    assert not d.canvas._surface_tris and d._bundle() is None   # (nothing is kept while away)
    _halve_walkmesh(toml)                               # ...and re-exports the floor
    d.show()
    d.show_field("A", data, toml)                       # the shell's re-feed on the way back
    assert not d.canvas._place_mode and not d.canvas._surface_tris   # the OLD floor is never re-armed
    # ...and the room they had loaded comes back by itself, read from disk again (no Load click)
    assert _wait(lambda: d._loading is None and d.canvas._surface_tris), d.status.text()
    assert _x_extent(d.canvas._surface_tris) == (round(x0 / 2), round(x1 / 2))


def test_a_room_is_only_re_read_unasked_when_it_was_loaded_and_the_tab_is_showing(app, tmp_path):
    """The automatic re-read on the way back has three guards, each with a reason: never for a
    room the author did not load (a tab show reads no disk unasked), never while the tab is
    hidden, and never again after a read of it FAILED (that one waits for a real click, or every
    re-feed would retry it)."""
    d, _ = _doc(app)
    path = tmp_path / "ROOM.field.toml"
    started = []
    d._loader.start = lambda *key: started.append(key)
    d.show_field("ROOM", {"field": {"id": 30058}}, path)
    assert started == []                               # never loaded by the author: nothing starts
    d.load_btn.click()
    key = (d._source, 0)
    assert started == [key]
    d._on_loaded(key, dict(_bundle(), source=d._source))
    d.hide()
    d.show_field("ROOM", {"field": {"id": 30058}}, path)   # a re-feed while HIDDEN
    assert started == [key]
    d.show()
    d.show_field("ROOM", {"field": {"id": 30058}}, path)   # back on it, showing: read again
    assert started == [key, key]
    d._on_load_failed(key, "the file is gone")
    d.show_field("ROOM", {"field": {"id": 30058}}, path)
    assert started == [key, key]                       # a failed read is not retried unasked
    assert "Could not load" in d.status.text() or "Load the room" in d.status.text()


def test_leaving_a_project_room_for_another_drops_its_surface(app, tmp_path):
    """The other route of P4: a project opened again (or reselected) after its files changed."""
    d, _ = _doc(app)
    a, b = tmp_path / "A.field.toml", tmp_path / "B.field.toml"
    d.show_field("A", {"field": {"id": 30058}}, a)
    d._bundles[(d._source, 0)] = dict(_bundle(), source=d._source)
    d._bundles[(("real", 351), 0)] = _bundle()          # a donor room stays: the install's
    d.show_field("B", {"field": {"id": 30059}}, b)
    d.show_field("A", {"field": {"id": 30058}}, a)
    assert d._bundle() is None and not d.canvas._place_mode
    assert (("real", 351), 0) in d._bundles


def test_hiding_keeps_a_donor_room_armed(app):
    d, _ = _doc(app)
    d.show_field("FORK", {"field": {"source_field": 351}}, Path("C:/somewhere/FORK.field.toml"))
    d._bundles[(("real", 351), 0)] = _bundle()
    d.load_btn.click()
    d.hide()
    d.show()
    d.show_field("FORK", {"field": {"source_field": 351}}, Path("C:/somewhere/FORK.field.toml"))
    assert d.canvas._place_mode and d.canvas._surface_tris


def test_a_failed_reload_leaves_no_old_floor_armed(app, tmp_path):
    """Review finding P4, after review. A re-Load that failed (a broken re-export) only wrote the
    error: the old floor stayed cached and clickable, and the next re-feed hid the error."""
    toml, data = _compose_room(tmp_path)
    d, _ = _doc(app)
    d.show_field("A", data, toml)
    d.load_btn.click()
    assert _wait(lambda: d._bundle() is not None and d.canvas._surface_tris), d.status.text()
    (toml.parent / "walkmesh.obj").write_text("garbage\nf 1 2 3\n", encoding="utf-8")
    d.load_btn.click()
    assert _wait(lambda: d._loading is None and "Could not load" in d.status.text()), d.status.text()
    assert not d.canvas._place_mode and not d.canvas._surface_tris and d._bundle() is None
    d.show_field("A", data, toml)
    assert not d.canvas._place_mode and not d.canvas._surface_tris


@pytest.mark.parametrize("ends", ["succeeds", "fails"])
def test_a_load_that_lands_after_a_glance_elsewhere_shows_on_its_room(app, tmp_path, ends):
    """Review finding P6, after review. Load A, glance at B, come back to A: the switch forgot the
    wait, and A's own result was then only cached -- the room stayed on "Load the room"."""
    d, _ = _doc(app)
    d.show_field("FORK", {"field": {"source_field": 351}}, Path("C:/somewhere/FORK.field.toml"))
    d._loader.start = lambda *a: None
    d.load_btn.click()
    key = d._loading
    d.show_field("B", {"field": {"id": 30059}}, tmp_path / "B.field.toml")
    d.show_field("FORK", {"field": {"source_field": 351}}, Path("C:/somewhere/FORK.field.toml"))
    assert d._loading is None
    if ends == "succeeds":
        d._loader.loaded.emit(key, _bundle())
        assert d.canvas._place_mode and d.canvas._surface_tris
    else:
        d._loader.failed.emit(key, "RuntimeError: no install")
        assert "no install" in d.status.text()
    assert d.load_btn.isEnabled()


def test_a_late_load_of_the_previous_room_is_not_shown_on_this_one(app, tmp_path):
    """The other half of the P6 rule: a result for a room that is NOT on screen only caches."""
    d, _ = _doc(app)
    d.show_field("FORK", {"field": {"source_field": 351}}, Path("C:/somewhere/FORK.field.toml"))
    d._loader.start = lambda *a: None
    d.load_btn.click()
    key = d._loading
    d.show_field("FORK2", {"field": {"source_field": 352}}, Path("C:/somewhere/FORK2.field.toml"))
    d._loader.loaded.emit(key, _bundle())
    assert not d.canvas._surface_tris and key in d._bundles
    d._loader.failed.emit(key, "RuntimeError: late")
    assert "late" not in d.status.text()


def test_a_load_landing_after_the_field_closed_post_glance_is_not_shown(app, tmp_path):
    """Load A, glance at B, back on A (the wait is forgotten), then close the field: A's result
    must not be painted on the empty doc -- closing forgets the surface source too."""
    d, _ = _doc(app)
    a = tmp_path / "A.field.toml"
    d.show_field("A", {"field": {"id": 30058}}, a)
    d._loader.start = lambda *a: None
    d.load_btn.click()
    key = d._loading
    d.show_field("B", {"field": {"id": 30059}}, tmp_path / "B.field.toml")
    d.show_field("A", {"field": {"id": 30058}}, a)
    d.show_none()
    d._loader.loaded.emit(key, dict(_bundle(), source=key[0]))
    assert not d.canvas._surface_tris and not d.canvas._place_mode and not d.load_btn.isEnabled()


def test_load_of_a_donor_room_is_still_served_from_the_cache(app):
    """The donor's real room comes from the install, which does not change mid-session."""
    d, _ = _doc(app)
    d.show_field("FORK", {"field": {"source_field": 351}}, Path("C:/somewhere/FORK.field.toml"))
    d._bundles[(("real", 351), 0)] = _bundle()
    started = []
    d._loader.start = lambda *a: started.append(a)
    d.load_btn.click()
    assert started == [] and d.canvas._surface_tris


# --------------------------------------------------------------- batch 2, the final review
def _loaded_project_room(app, tmp_path):
    """A project room the author loaded, with the loader replaced by a recorder (no thread)."""
    d, _ = _doc(app)
    path = tmp_path / "ROOM.field.toml"
    started = []
    d._loader.start = lambda *key: started.append(key)
    d.show_field("ROOM", {"field": {"id": 30058}}, path)
    d.load_btn.click()
    key = (d._source, 0)
    d._on_loaded(key, dict(_bundle(), source=d._source))
    assert started == [key] and d.canvas._surface_tris
    return d, path, key, started


def test_coming_back_to_the_tab_re_reads_the_room_without_any_re_feed(app, tmp_path):
    """The shell usually re-feeds on a tab change, but the SHOW itself is what says "the author
    is back": the room is read again on showEvent alone."""
    d, _path, key, started = _loaded_project_room(app, tmp_path)
    d.hide()
    assert not d.canvas._surface_tris and key not in d._bundles
    d.show()
    QApplication.processEvents()                       # the deferred resume
    assert started == [key, key]


def test_a_load_that_lands_while_the_tab_is_hidden_is_not_kept(app, tmp_path):
    """Load, leave before it lands: the result was cached and armed on the hidden tab, so the
    way back found a cached floor and never re-read the files that changed meanwhile."""
    d, _ = _doc(app)
    path = tmp_path / "ROOM.field.toml"
    started = []
    d._loader.start = lambda *key: started.append(key)
    d.show_field("ROOM", {"field": {"id": 30058}}, path)
    d.load_btn.click()
    key = (d._source, 0)
    d.hide()                                           # the author leaves; the read is in flight
    d._on_loaded(key, dict(_bundle(), source=d._source))
    assert key not in d._bundles and not d.canvas._surface_tris and not d.canvas._place_mode
    d.show()
    QApplication.processEvents()
    assert started == [key, key]                       # back on it: read again, from disk


def test_a_room_that_comes_back_keeps_the_view_and_names_itself_plainly(app, tmp_path):
    """A tab round trip is not a new room: the re-read must not reset the author's zoom and pan
    (it did, on every return), and its status must not print a Python tuple."""
    d, path, key, _started = _loaded_project_room(app, tmp_path)
    refits = []
    apply = d._apply_bundle
    d._apply_bundle = lambda bundle, *, refit: (refits.append(refit), apply(bundle, refit=refit))[1]
    d.canvas.repaint()                                 # the first paint runs the room's one fit ...
    assert not d.canvas._fit_pending
    d.canvas.scale(2.0, 2.0)                           # ... and THEN the author zooms in
    d.canvas._zoom = 2.0
    d.hide()
    d.show()
    QApplication.processEvents()
    assert "('project'" not in d.status.text() and "ROOM" in d.status.text(), d.status.text()
    d._on_loaded(key, dict(_bundle(), source=d._source))
    assert refits == [False] and d.canvas._zoom == 2.0
    d.load_btn.click()                                 # an explicit Load still fits the room
    d._on_loaded(key, dict(_bundle(), source=d._source))
    assert refits == [False, True]


def test_minimising_the_window_does_not_drop_the_room(app, tmp_path):
    """A minimised window is a SPONTANEOUS hide: nobody left the tab. Dropping the room there
    threw away a half-drawn region quad and re-read the room for nothing."""
    from PySide6.QtGui import QHideEvent

    class _Minimised(QHideEvent):
        def spontaneous(self):
            return True

    d, _path, key, started = _loaded_project_room(app, tmp_path)
    d.canvas._pending_region = [(0.0, 600.0), (100.0, 600.0)]      # two corners of a quad, mid-draw
    d.hideEvent(_Minimised())
    assert key in d._bundles and d.canvas._surface_tris
    assert d.canvas._pending_region == [(0.0, 600.0), (100.0, 600.0)]
    assert started == [key]
    d.hideEvent(QHideEvent())                          # ...whereas leaving the tab does drop it
    assert key not in d._bundles and not d.canvas._surface_tris


# --------------------------------------------------------------- batch 3
def test_a_prop_placed_after_a_delete_never_reuses_a_live_name():
    """Review finding P13. place_prop named by len(): two props, delete prop0, place again ->
    two rows called prop1, which neither the tree nor the undo label could tell apart."""
    data = {}
    P.place_prop(data, 0, 0)
    P.place_prop(data, 10, 10)
    del data["prop"][0]
    label = P.place_prop(data, 20, 20)
    names = [p["name"] for p in data["prop"]]
    assert len(set(names)) == len(names), names
    assert data["prop"][-1]["name"] in label            # the undo label says WHICH prop
