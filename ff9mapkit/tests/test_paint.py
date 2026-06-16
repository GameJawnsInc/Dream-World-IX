"""Phase B: content projection for the paint template (ff9mapkit.scene.paint)."""

from __future__ import annotations

import json
import os

from ff9mapkit.scene import guide, paint


def _cam():
    # the calibration-scene camera (proven to frame this content on-canvas)
    return guide.make_camera(42.0, 4500, fov_x_deg=42.2)


# --- height resolution -------------------------------------------------------------------
def test_resolve_height_precedence():
    # explicit height wins over everything
    assert paint.resolve_height({"type": "npc", "height": 123, "subtype": "moogle"}) == 123
    # name (archetype/prop) beats the type fallback
    assert paint.resolve_height({"type": "npc", "subtype": "moogle"}) == 440
    assert paint.resolve_height({"type": "prop", "subtype": "tent"}) == 680
    # a plain human NPC falls back to the type default (the calibrated anchor)
    assert paint.resolve_height({"type": "npc", "subtype": "townsman"}) == paint.HUMAN_HEIGHT
    assert paint.resolve_height({"type": "npc", "subtype": None}) == paint.HUMAN_HEIGHT
    # flat zones get no pole
    assert paint.resolve_height({"type": "gateway"}) == 0
    assert paint.resolve_height({"type": "event"}) == 0


# --- normalize_content -------------------------------------------------------------------
def _field():
    return {
        "player": {"spawn": [0, -861]},
        "npc": [{"name": "Human", "archetype": "townsman", "pos": [-820, -861]},
                {"name": "Kupo", "archetype": "moogle", "pos": [820, -861]}],
        "prop": [{"prop": "chest", "pos": [-820, -1500]},
                 {"prop": "tent", "pos": [-450, -300], "height": 999}],
        "marker": [{"name": "wp1", "pos": [100, -500]}],
        "gateway": [{"to": 4002, "zone": [[-100, 0], [100, 0], [100, 200], [-100, 200]]}],
        "event": [{"name": "chest_ev", "zone": [[0, 0], [50, 0], [50, 50], [0, 50]]}],
        "camera_zone": [{"to_camera": 1, "zone": [[0, 0], [10, 0], [10, 10], [0, 10]]}],
        "savepoint": [{"zone": [[-50, -50], [50, -50], [50, 50], [-50, 50]]}],
    }


def test_normalize_extracts_every_type():
    items = paint.normalize_content(_field())
    by_type = {}
    for it in items:
        by_type.setdefault(it["type"], []).append(it)
    assert set(by_type) == {"npc", "prop", "waypoint", "spawn", "gateway", "event",
                            "camzone", "savepoint"}
    assert len(by_type["npc"]) == 2 and len(by_type["prop"]) == 2
    # subtype carries the archetype/prop name for the height lookup
    assert by_type["npc"][1]["subtype"] == "moogle"
    assert by_type["prop"][0]["subtype"] == "chest"
    # an explicit per-block height is preserved through normalization
    tent = next(p for p in by_type["prop"] if p["subtype"] == "tent")
    assert tent["height"] == 999
    # spawn comes from [player]
    assert by_type["spawn"][0]["pos"] == (0, -861)
    # zone footprints carry their corner list
    assert by_type["gateway"][0]["footprint"] == "zone"
    assert len(by_type["gateway"][0]["zone"]) == 4


def test_normalize_merges_scene_positions_by_name():
    # the two-file split: logic in field.toml, positions in scene.toml, joined by name
    field = {"npc": [{"name": "Vivi", "preset": "vivi", "dialogue": "hi"}],
             "gateway": [{"name": "door", "to": 100}]}
    scene = {"npc": [{"name": "Vivi", "pos": [10, 20]}],
             "gateway": [{"name": "door", "zone": [[0, 0], [1, 0], [1, 1], [0, 1]]}]}
    items = paint.normalize_content(field, scene)
    npc = next(i for i in items if i["type"] == "npc")
    gw = next(i for i in items if i["type"] == "gateway")
    assert npc["pos"] == (10, 20) and npc["subtype"] == "vivi"
    assert len(gw["zone"]) == 4


def test_normalize_skips_positionless_entries():
    # an NPC with neither inline pos nor a scene twin is dropped (nothing to project)
    items = paint.normalize_content({"npc": [{"name": "ghost", "preset": "vivi"}]})
    assert items == []


# --- project_content ---------------------------------------------------------------------
def test_project_point_has_footprint_and_pole():
    cam = _cam()
    items = paint.normalize_content(_field())
    proj = paint.project_content(items, cam, scale=4)
    assert proj["size"] == (384 * 4, 448 * 4)
    npc = proj["types"]["npc"]
    assert len(npc["footprints"]) == 2 and len(npc["poles"]) == 2   # a human pole per NPC
    # a pole runs from feet (y=0) UP to the head (smaller canvas-y, higher on screen)
    (fx, fy), (hx, hy) = npc["poles"][0]
    assert hy < fy
    # the moogle (subtype height 440) is shorter than the human (560): a shorter pole span
    spans = sorted(abs(p[0][1] - p[1][1]) for p in npc["poles"])
    assert spans[0] < spans[1]


def test_project_zone_is_a_closed_outline():
    cam = _cam()
    items = paint.normalize_content(_field())
    proj = paint.project_content(items, cam, scale=4)
    gw = proj["types"]["gateway"]
    assert len(gw["zones"]) == 1 and len(gw["zones"][0]) == 4   # 4 projected corners
    assert not gw["poles"]                                      # a gateway is flat (no pole)


def test_project_savepoint_zone_gets_a_moogle_pole():
    cam = _cam()
    items = paint.normalize_content(_field())
    proj = paint.project_content(items, cam, scale=4)
    sp = proj["types"]["savepoint"]
    assert len(sp["zones"]) == 1 and len(sp["poles"]) == 1     # zone outline + a centroid pole


def test_legend_numbers_pins_and_flags_off_canvas():
    cam = _cam()
    items = paint.normalize_content(_field())
    proj = paint.project_content(items, cam, scale=4)
    # one legend entry per item, pins numbered 1..N in order
    assert len(proj["legend"]) == len(items)
    assert [e["pin"] for e in proj["legend"]] == list(range(1, len(items) + 1))
    for e in proj["legend"]:
        assert set(e) >= {"pin", "type", "label", "subtype", "height", "canvas", "off_canvas"}
    # on-canvas content is not flagged off
    assert any(not e["off_canvas"] for e in proj["legend"])


def test_far_offscreen_content_flagged_off_canvas():
    cam = _cam()
    items = paint.normalize_content({"npc": [{"name": "far", "archetype": "townsman",
                                              "pos": [99999, 99999]}]})
    proj = paint.project_content(items, cam, scale=4)
    assert proj["legend"][0]["off_canvas"] is True


# --- render_full_template (PNGs + legend + manifest) -------------------------------------
def test_render_full_template_writes_layers_legend_manifest(tmp_path):
    cam = _cam()
    fr = guide.frame_floor(cam, back_canvas_y=205, front_canvas_y=432)
    items = paint.normalize_content(_field())
    files = paint.render_full_template(cam, fr, items, str(tmp_path), basename="pt")
    names = {os.path.basename(f) for f in files}
    # floor layers + every content type present in _field() + legend + manifest
    assert {"pt_grid.png", "pt_outline.png", "pt_height.png"} <= names
    assert {"pt_npc.png", "pt_prop.png", "pt_waypoint.png", "pt_spawn.png", "pt_gateway.png",
            "pt_event.png", "pt_camzone.png", "pt_savepoint.png"} <= names
    assert {"pt.legend.json", "pt.manifest.json"} <= names
    # no empty layers: types absent from _field() get no PNG
    assert not (names & {"pt_jump.png", "pt_ladder.png", "pt_choice.png"})
    man = json.load(open(tmp_path / "pt.manifest.json"))
    assert man["legend"] == "pt.legend.json"
    assert [l["type"] for l in man["layers"]][:3] == ["grid", "outline", "height"]  # floor underneath


def test_render_full_template_content_only_when_no_frame(tmp_path):
    cam = _cam()
    items = paint.normalize_content(_field())
    files = paint.render_full_template(cam, None, items, str(tmp_path), basename="pt")
    names = {os.path.basename(f) for f in files}
    assert not (names & {"pt_grid.png", "pt_outline.png", "pt_height.png"})   # no floor without a frame
    assert "pt_npc.png" in names and "pt.manifest.json" in names
