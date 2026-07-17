"""CampaignMap node art: the thumbnail band must render at the screen's device pixel ratio, the same
idiom icons.pixmap() uses -- a DPR=1 pixmap stretched over a HiDPI logical footprint is visibly blurrier
than the vector nodes/text around it. Headless-safe: devicePixelRatioF() is monkeypatched rather than
relying on offscreen actually reporting a scaled screen."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("PIL")

from PIL import Image                                   # noqa: E402
from PySide6.QtWidgets import QApplication               # noqa: E402

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
    assert logical_w == int(n.w - 12), "the DPR fix must not change the on-screen (logical) size"
