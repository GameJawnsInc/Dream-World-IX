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
    assert npcs[0]["preset"] and npcs[0]["dialogue"]                       # a buildable default


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
    return {"donor": 351, "cam_index": 0, "n_cams": 1,
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


def test_no_donor_refuses_honestly(app):
    d, _ = _doc(app)
    d.show_field("NOVEL", {"field": {"id": 30058}}, Path("C:/somewhere/NOVEL.field.toml"))
    assert d._blocked and "donor" in d._blocked
    assert not d.load_btn.isEnabled()


def test_verbatim_refuses_spawn_and_arrival_but_places_npc(app):
    d, calls = _doc(app)
    data = {"verbatim_eb": {"donor": 351}}
    d.show_field("FORK", data, Path("C:/somewhere/FORK.field.toml"))
    assert d._blocked is None and d._donor == 351
    d._bundles[(351, 0)] = _bundle()
    d._apply_bundle(d._bundles[(351, 0)], refit=True)
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
    d._bundles[(351, 0)] = _bundle()
    d._apply_bundle(d._bundles[(351, 0)], refit=True)
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
    d._bundles[(351, 0)] = _bundle()
    d._apply_bundle(d._bundles[(351, 0)], refit=True)
    assert len(d.canvas._markers) == 1 and d.canvas._markers[0]["label"] == "A"
    data["npc"].append({"name": "B", "pos": [100, 900]})
    d.show_field("FORK", data, path)                      # the shell's re-feed after an edit
    assert {m["label"] for m in d.canvas._markers} == {"A", "B"}


def test_stacked_hits_route_through_the_chooser(app, monkeypatch):
    d, calls = _doc(app)
    data = {"field": {"source_field": 351}}
    d.show_field("FORK", data, Path("C:/somewhere/FORK.field.toml"))
    d._bundles[(351, 0)] = _bundle()
    d._apply_bundle(d._bundles[(351, 0)], refit=True)
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
