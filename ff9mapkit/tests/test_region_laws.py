"""The region-law pure layer — click-authoring Rung 4 (studies/click-authoring/PLAN.md).

Pins the three judges the canvas renders and the hosts surface, Qt-free:

* ``imagefield.click_to_plane`` — THE PLANE LAW's one-parameter generalization
  (``s = (h - C.y)/ray.y``), used for zone corners hanging OFF the walkmesh.
* ``imagefield.fan_triangles`` / ``zone_fan_audit`` — the engine's IsInQuad fan vs the drawn
  outline, BOTH directions: a dead zone (drawn but never fires — the hand-authored
  collinear-strip class) and an over-trigger spill (fires outside the drawn outline — the
  non-convex/self-crossing class). A convex quad in either winding scores 0/0.
* ``build.region_overlap_pairs`` — the TREADQUAD starvation judge, extracted so the live
  canvas and ``lint_region_overlaps`` share ONE owner (the lint's message fence lives in
  ``test_coop_gate.py``).
"""

from __future__ import annotations

import math

import pytest

from ff9mapkit import build, imagefield as IF
from ff9mapkit.scene import cam as C
from ff9mapkit.scene import guide

CAM = guide.make_camera(26.0, 3000.0, fov_x_deg=42.0)


# ------------------------------------------------------------------- click_to_plane
def test_plane_at_zero_matches_click_to_world():
    pt = (192.0, 380.0)
    assert IF.click_to_plane(CAM, pt, 0.0) == IF.click_to_world(CAM, pt)


def test_plane_at_height_round_trips_exactly():
    for h in (-300.0, -60.0, 120.0):
        x, z = IF.click_to_plane(CAM, (150.0, 400.0), h)
        cx, cy = C.to_canvas((x, h, z), CAM)
        assert math.hypot(cx - 150.0, cy - 400.0) < IF.CLICK_ROUNDTRIP_TOL


def test_plane_refuses_at_and_above_its_horizon():
    with pytest.raises(IF.ImageFieldError):
        IF.click_to_plane(CAM, (192.0, -3000.0), 0.0)


# ------------------------------------------------------------------- the IsInQuad fan
CONVEX = [(0, 0), (100, 0), (100, 100), (0, 100)]


def test_fan_doubles_a_quad_and_takes_five_points_verbatim():
    assert len(IF.fan_triangles(CONVEX)) == 3            # doubled: 2 of 5 triplets degenerate
    five = [(0, 0), (50, 0), (100, 0), (100, 40), (0, 40)]
    assert len(IF.fan_triangles(five)) == 4              # verbatim: only the collinear one drops


def test_convex_quads_are_faithful_in_either_winding():
    for q in (CONVEX, list(reversed(CONVEX)), CONVEX + [CONVEX[-1]]):
        audit = IF.zone_fan_audit(q)
        assert audit == {"gap": 0.0, "spill": 0.0}


def test_a_notch_inside_the_hull_spills_past_the_drawn_outline():
    """The dart whose reflex corner sits INSIDE the other three's hull: the fan's (q1 q2 q3)
    IS that hull, so the engine fires all over the notch the author carved out."""
    audit = IF.zone_fan_audit([(70, 60), (100, 0), (100, 100), (0, 100)])
    assert audit["gap"] < 0.02 and audit["spill"] > 0.25


def test_a_bowtie_fires_across_its_whole_hull():
    audit = IF.zone_fan_audit([(0, 0), (100, 0), (0, 100), (100, 100)])
    assert audit["spill"] > 0.3                          # the un-drawn middle fires too


def test_the_collinear_strip_has_a_true_dead_zone():
    """The classic hand-authored 5-point strip whose far edge is collinear: its centre is in
    NO fan triangle — the trigger silently never fires there (the in-game lesson that minted
    quad_zone's doubled form)."""
    audit = IF.zone_fan_audit([(0, 0), (50, 0), (100, 0), (100, 40), (0, 40)])
    assert audit["gap"] > 0.05 and audit["spill"] < 0.02


def test_a_degenerate_sliver_judges_clean():
    assert IF.zone_fan_audit([(0, 0), (100, 0), (200, 0), (300, 0)]) == \
        {"gap": 0.0, "spill": 0.0}


# ------------------------------------------------------------------- overlap pairs
def test_overlap_pairs_key_the_exact_rows():
    raw = {"gateway": [{"to": 5, "zone": [[0, 0], [10, 0], [10, 10], [0, 10]]}],
           "event": [{"name": "msg", "zone": [[5, 5], [15, 5], [15, 15], [5, 15]]},
                     {"name": "abut", "zone": [[10, 0], [20, 0], [20, 10], [10, 10]]}]}
    pairs = build.region_overlap_pairs(raw)
    assert [(a[:2], b[:2]) for a, b in pairs] == [(("gateway", 0), ("event", 0)),
                                                  (("event", 0), ("event", 1))]
    labels = {k[2] for pair in pairs for k in pair}
    assert "gateway -> 5" in labels and "event 'msg'" in labels


def test_abutting_zones_do_not_pair():
    raw = {"gateway": [{"to": 5, "zone": [[0, 0], [10, 0], [10, 10], [0, 10]]}],
           "event": [{"name": "next-door", "zone": [[10, 0], [20, 0], [20, 10], [10, 10]]}]}
    assert build.region_overlap_pairs(raw) == []


def test_malformed_zones_never_crash_the_judge():
    raw = {"gateway": [{"to": 5, "zone": "oops"}, {"to": 6}],
           "event": [{"name": "e", "zone": [["x", 0], [1, 1], [2, 2], [3, 3]]}]}
    assert build.region_overlap_pairs(raw) == []


# ------------------------------------------------------------------- the photo-lane generator
def test_build_image_field_emits_drawn_regions(tmp_path):
    """The CLI passthrough: canvas-px zone specs un-project through the build's own camera into
    [[gateway]]/[[event]] rows — the photo lane's regions survive every in-place regenerate."""
    pytest.importorskip("PIL")
    import tomllib

    from PIL import Image
    img = tmp_path / "photo.png"
    Image.new("RGB", (768, 896), (90, 80, 70)).save(img)
    man = IF.build_image_field(
        img, [(60, 440), (330, 440), (330, 300), (60, 300)], tmp_path / "proj",
        gateways=["4005,2@60,300;140,300;140,330;60,330"],
        events=[{"message": 'say "hi" @ the door', "zone_px":
                 [(200, 340), (300, 340), (300, 380), (200, 380)]}])
    data = tomllib.loads((tmp_path / "proj" / "PICTURE.field.toml").read_text(encoding="utf-8"))
    (gw,) = data["gateway"]
    assert gw["to"] == 4005 and gw["entrance"] == 2 and gw["name"] == "door0"
    assert len(gw["zone"]) == 4 and all(len(p) == 2 for p in gw["zone"])
    (ev,) = data["event"]
    assert ev["message"] == 'say "hi" @ the door'     # escaped through the writer, verbatim back
    assert man["gateways"][0]["to"] == 4005 and man["events"][0]["zone_px"][0] == (200.0, 340.0)
    # the zone rode the same camera as the floor: corner 0 un-projects to the emitted int pair
    from ff9mapkit.scene import guide
    cam = guide.make_camera(26.0, 3000.0, fov_x_deg=42.0)
    (wx, wz), = IF.unproject_floor(cam, [(60.0, 300.0)])
    assert gw["zone"][0] == [round(wx), round(wz)]


def test_region_spec_parse_refusals():
    for bad in ("4005", "x@1,2;3,4;5,6;7,8", "4005@1,2;3,4", "4005@1,2;3,4;5,6;7"):
        with pytest.raises(IF.ImageFieldError):
            IF.parse_gateway_spec(bad)
    with pytest.raises(IF.ImageFieldError):
        IF.parse_event_spec("@1,2;3,4;5,6;7,8")       # an empty message is a mistake, refused
    ev = IF.parse_event_spec("watch @ the ledge@1,2;3,4;5,6;7,8")
    assert ev["message"] == "watch @ the ledge"       # the LAST @ splits


# ------------------------------------------------------------------- the Field(0) softlock
def test_validate_refuses_a_targetless_door(tmp_path):
    """to = 0 compiled to Field(0) and BLACK-SCREEN softlocked the 2026-07-29 playtest — now a
    build-blocking error, not a warp into nothing."""
    from ff9mapkit.build import FieldProject, validate
    toml = tmp_path / "door0.field.toml"

    def _problems(to_line):
        toml.write_text('[field]\nname = "D0"\nid = 30095\narea = 10\n\n'
                        f'[[gateway]]\n{to_line}entrance = 0\n'
                        'zone = [[50, 50], [150, 50], [150, 150], [50, 150]]\n',
                        encoding="utf-8")
        return validate(FieldProject.load(toml))

    assert any("BLACK-SCREEN" in p for p in _problems("to = 0\n"))
    assert any("BLACK-SCREEN" in p for p in _problems("to = -5\n"))
    assert any("needs a 'to'" in p for p in _problems(""))
    ok = _problems("to = 301\n")                           # a real target passes this check
    assert not any("BLACK-SCREEN" in p or "needs a 'to'" in p for p in ok)


def test_region_rows_flag_a_targetless_door():
    pytest.importorskip("PySide6")            # placedoc imports Qt at module level
    from ff9mapkit.workspace import placedoc as P
    data = {"gateway": [{"name": "door0", "to": 0,
                         "zone": [[0, 0], [100, 0], [100, 100], [0, 100]]}]}
    (row,) = P.region_rows(data)
    assert row["warn"] and "NO TARGET" in row["warn"] and "black" in row["warn"].lower()
    data["gateway"][0]["to"] = 301
    (row,) = P.region_rows(data)
    assert row["warn"] is None


def test_set_gateway_target_op():
    pytest.importorskip("PySide6")            # placedoc imports Qt at module level
    from ff9mapkit.workspace import placedoc as P
    data = {"gateway": [{"name": "door0", "to": 0,
                         "zone": [[0, 0], [100, 0], [100, 100], [0, 100]]}]}
    label = P.set_gateway_target(data, 0, 301)
    assert data["gateway"][0]["to"] == 301 and "301" in label and "door0" in label


def test_flag_index_aliasing_is_refused_on_both_lanes(tmp_path):
    """Two [[flag]] names on ONE index alias a single save bit. FieldProject.load refuses the
    table outright (resolve_project_flags raises); a dict-built project reaches validate, which
    now SPENDS collect_flag_defs directly (the mechanism existed; no call site reported it)."""
    import pytest as _pytest

    from ff9mapkit.build import FieldProject, validate
    raw = {"field": {"id": 30095, "name": "A", "area": 10},
           "flag": [{"name": "a", "index": 8712}, {"name": "b", "index": 8712}]}
    assert any("both use index 8712" in m for m in validate(FieldProject(raw, tmp_path)))
    toml = tmp_path / "alias.field.toml"
    toml.write_text("""[field]
name = "A"
id = 30095
area = 10

[[flag]]
name = "a"
index = 8712

[[flag]]
name = "b"
index = 8712
""", encoding="utf-8")
    with _pytest.raises(ValueError, match="both use index 8712"):
        FieldProject.load(toml)


def test_lint_flags_the_placeholder_event_message(tmp_path):
    from ff9mapkit.build import FieldProject, lint_logic
    toml = tmp_path / "ph.field.toml"
    toml.write_text("""[field]
name = "P"
id = 30095
area = 10

[[event]]
name = "z"
message = "..."
zone = [[0, 0], [10, 0], [10, 10], [0, 10]]
""", encoding="utf-8")
    warns = lint_logic(FieldProject.load(toml))
    assert any("placeholder" in m and "'...'" in m for m in warns)
    # a received item box IGNORES the placeholder -> no warn
    toml.write_text("""[field]
name = "P"
id = 30095
area = 10

[[event]]
name = "z"
message = "..."
give_item = [100, 1]
received = true
zone = [[0, 0], [10, 0], [10, 10], [0, 10]]
""", encoding="utf-8")
    assert not any("placeholder" in m for m in lint_logic(FieldProject.load(toml)))
