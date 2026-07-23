"""CampaignMap rendering laws.

* Node art must render at the screen's device pixel ratio, the same idiom icons.pixmap() uses -- a
  DPR=1 pixmap stretched over a HiDPI logical footprint is visibly blurrier than the vector nodes/text
  around it. Headless-safe: devicePixelRatioF() is monkeypatched rather than relying on offscreen
  actually reporting a scaled screen.
* A two-way connection (A->B plus B->A, the overwhelmingly common shape -- rooms connect both
  directions) is ONE ribbon with a head at each end, not two stacked lines with four heads.
* A rerender (thumb arrivals, highlight, retheme all funnel there) must NOT yank the user's zoom;
  opening a DIFFERENT campaign must reset it.
* The CALIBRE text dial reaches the map (it is a QGraphicsScene -- no QSS role can): node geometry
  re-derives from the dial. Offscreen-safe because the width is pure arithmetic, not font metrics.

Colour/geometry assertions only -- offscreen width-from-TEXT numbers are fiction (the study's law);
nothing here reads a text item's metrics."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("PIL")

from PIL import Image                                   # noqa: E402
from PySide6.QtCore import Qt                            # noqa: E402
from PySide6.QtWidgets import (QApplication, QGraphicsPathItem,   # noqa: E402
                               QGraphicsPolygonItem)

from ff9mapkit import campaign                           # noqa: E402
from ff9mapkit.editor.graphview import LaidNode          # noqa: E402
from ff9mapkit.workspace import mapview                  # noqa: E402

_PAL = {"surface": "#1c1f26", "surface_btn": "#262b35", "accent": "#7aa2f7", "accent_fg": "#0b0e14",
        "text": "#c7ccd6", "muted": "#7d8493", "border": "#3a3f4b", "error": "#e05252",
        "warn": "#e0af68", "success": "#6ab96a"}


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _node():
    return LaidNode(name="ROOM", new_id=4003, mode="borrow", x=0, y=0, w=176, h=138,
                     is_entry=True, reachable=True, dead_end=False, needs_export=False)


def _two_room_graph(edges):
    M = campaign.Member
    members = [M(300, 30100, "ENT", "borrow", 11, "", "ENT/ent.field.toml", False),
               M(301, 30101, "COR", "borrow", 11, "", "COR/cor.field.toml", False)]
    plan = campaign.CampaignPlan(name="ICE", mod_folder="M", id_base=30100,
                                 flag_base=campaign.FIRST_SAFE_FLAG, flags_per_field=64,
                                 entry_name="ENT", entry_entrance=0, members=members,
                                 edges=edges, seams=[])
    return campaign.campaign_graph(plan)


def _ribbons(mv):
    """The scene's EDGE paths, by their tag (the node ring is pen-only too -- style heuristics lie)."""
    return [it for it in mv._scene.items()
            if isinstance(it, QGraphicsPathItem) and it.data(0) == "ribbon"]


def test_a_two_way_pair_is_one_ribbon_with_a_head_at_each_end(app):
    g = _two_room_graph([{"frm": "ENT", "to": "COR", "entrance": 2},
                         {"frm": "COR", "to": "ENT", "entrance": 0}])
    mv = mapview.CampaignMap(dict(_PAL))
    mv.render(g)
    assert len(_ribbons(mv)) == 1, "A->B plus B->A must merge into ONE two-headed ribbon"
    heads = [it for it in mv._scene.items() if isinstance(it, QGraphicsPolygonItem)]
    assert len(heads) == 2, "the merged ribbon carries an arrowhead at EACH end"


def test_a_one_way_edge_is_one_ribbon_with_one_head(app):
    g = _two_room_graph([{"frm": "ENT", "to": "COR", "entrance": 2}])
    mv = mapview.CampaignMap(dict(_PAL))
    mv.render(g)
    assert len(_ribbons(mv)) == 1
    heads = [it for it in mv._scene.items() if isinstance(it, QGraphicsPolygonItem)]
    assert len(heads) == 1, "a one-way gateway points one way"


def test_a_rerender_keeps_the_zoom_but_a_new_campaign_resets_it(app):
    g = _two_room_graph([{"frm": "ENT", "to": "COR", "entrance": 2}])
    mv = mapview.CampaignMap(dict(_PAL))
    mv.render(g)
    mv.scale(1.5, 1.5)                                  # the user zoomed (Ctrl+scroll lands here)
    mv._zoom = 1.5
    mv.rerender()                                       # a thumbnail arrival redraw...
    assert mv.transform().m11() == pytest.approx(1.5), \
        "a rerender of the SAME campaign must not yank the user's zoom"
    mv.render(_two_room_graph([{"frm": "ENT", "to": "COR", "entrance": 2}]))
    assert mv.transform().m11() == pytest.approx(1.0), "a different campaign starts at 1:1"


def test_the_text_dial_reaches_the_map(app):
    g = _two_room_graph([{"frm": "ENT", "to": "COR", "entrance": 2}])
    mv = mapview.CampaignMap(dict(_PAL), scale=100)
    mv.render(g)
    w100 = mv._layout.nodes[0].w
    mv.set_scale(150)
    assert mv._layout is not None and mv._layout.nodes[0].w > w100, \
        "the CALIBRE dial must re-derive the map's node geometry (no QSS reaches a QGraphicsScene)"


def test_thumbnail_pixmap_is_tagged_at_the_screen_dpr(app, tmp_path, monkeypatch):
    png = tmp_path / "thumb.png"
    Image.new("RGB", (360, 480), (80, 90, 140)).save(png)
    mv = mapview.CampaignMap(dict(_PAL), thumbs=lambda name: str(png))
    mv._scene.clear()                                   # drop the constructor's empty-state placeholder
    mv._use_thumbs = True
    monkeypatch.setattr(mv, "devicePixelRatioF", lambda: 2.0)
    n = _node()
    mv._node(n)
    pixmap_items = [it for it in mv._scene.items() if hasattr(it, "pixmap") and not it.pixmap().isNull()]
    assert pixmap_items, "no thumbnail pixmap item was added to the scene"
    pm = pixmap_items[0].pixmap()
    assert pm.devicePixelRatio() == 2.0, "thumbnail pixmap wasn't rendered/tagged at the screen's DPR"
    logical_w = round(pm.width() / pm.devicePixelRatio())
    assert logical_w == int(n.w), "the DPR tag must not change the on-screen (logical) size -- the " \
                                  "poster art covers the full card"


def test_a_seam_heavy_node_gets_one_chip_not_a_label_per_seam(app):
    """The user-reported clutter: a real-zone fork carries up to ~20 scripted exits per field, and the
    old view drew one dotted stub + one label ROW for every one of them."""
    M = campaign.Member
    members = [M(300, 30100, "ENT", "borrow", 11, "", "ENT/ent.field.toml", False)]
    seams = [{"frm": "ENT", "to_real": str(500 + i), "kind": "scripted", "note": "", "to_member": None}
             for i in range(20)]
    plan = campaign.CampaignPlan(name="ICE", mod_folder="M", id_base=30100,
                                 flag_base=campaign.FIRST_SAFE_FLAG, flags_per_field=64,
                                 entry_name="ENT", entry_entrance=0, members=members,
                                 edges=[], seams=seams)
    mv = mapview.CampaignMap(dict(_PAL))
    mv.render(campaign.campaign_graph(plan))
    import re
    texts = [it.text() for it in mv._scene.items() if hasattr(it, "text")]
    chips = [t for t in texts if re.fullmatch(r"⇢ \d+", t)]    # the legend's "⇢ leads elsewhere" is prose
    assert chips == ["⇢ 20"], f"20 seams must collapse into ONE counted chip (got {chips})"
    assert not any("-> 5" in t for t in texts), "no per-seam label rows may remain on the canvas"
