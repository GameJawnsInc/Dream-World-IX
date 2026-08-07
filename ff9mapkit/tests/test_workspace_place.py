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
