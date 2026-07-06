"""Field background thumbnails: the pure worker logic (tier-1 project art + cache keying) and the
service's disabled/miss discipline. Headless; the install-side composite tier is exercised manually
(it needs the game) -- these tests prove the game-FREE paths never block or raise."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("PIL")

from PIL import Image                                  # noqa: E402

from ff9mapkit import provision                        # noqa: E402
from ff9mapkit.workspace import thumbs                 # noqa: E402


@pytest.fixture()
def cache(tmp_path, monkeypatch):
    monkeypatch.setattr(provision, "cache_dir", lambda: tmp_path / "cache")
    monkeypatch.delenv("FF9MAPKIT_NO_THUMBS", raising=False)
    return tmp_path


def _project(tmp_path, size=(800, 600)):
    proj = tmp_path / "IC_ENT"
    proj.mkdir()
    toml = proj / "IC_ENT.field.toml"
    toml.write_text('[field]\nid = 30100\nname = "IC_ENT"\narea = 11\n', encoding="utf-8")
    Image.new("RGB", size, (120, 40, 40)).save(proj / "background.png")
    return toml


def test_build_thumb_from_project_art_scales_and_caches(cache):
    toml = _project(cache)
    png = thumbs.build_thumb(toml, None)
    assert png is not None and png.is_file()
    assert Image.open(png).width == thumbs.THUMB_W
    first = png.stat().st_mtime_ns
    assert thumbs.build_thumb(toml, None) == png       # cache hit: same file,
    assert png.stat().st_mtime_ns == first             # not re-written


def test_build_thumb_refreshes_when_the_art_changes(cache):
    toml = _project(cache)
    a = thumbs.build_thumb(toml, None)
    img = toml.parent / "background.png"
    Image.new("RGB", (400, 300), (40, 120, 40)).save(img)
    os.utime(img, (img.stat().st_atime + 5, img.stat().st_mtime + 5))   # a repaint -> new mtime
    b = thumbs.build_thumb(toml, None)
    assert b is not None and b != a                    # a NEW cache entry (key folds in mtime+size)


def test_build_thumb_small_art_is_not_upscaled(cache):
    toml = _project(cache, size=(200, 150))
    png = thumbs.build_thumb(toml, None)
    assert Image.open(png).width == 200


def test_build_thumb_no_source_is_none(cache):
    toml = cache / "bare" / "X.field.toml"
    toml.parent.mkdir()
    toml.write_text("[field]\nid = 1\n", encoding="utf-8")
    assert thumbs.build_thumb(toml, None) is None      # no project art + no real id -> nothing to show
    assert thumbs.build_thumb(None, None) is None


def test_service_disabled_by_env(cache, monkeypatch):
    monkeypatch.setenv("FF9MAPKIT_NO_THUMBS", "1")
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    svc = thumbs.ThumbService()
    toml = _project(cache)
    assert svc.request("IC_ENT", toml, None) is None   # disabled: no result, and crucially...
    assert svc._worker is None                         # ...no worker thread was started


def test_service_resolves_project_art_async(cache):
    import time
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    svc = thumbs.ThumbService()
    toml = _project(cache)
    assert svc.request("IC_ENT", toml, None) is None   # first ask enqueues
    deadline = time.monotonic() + 10
    while svc.cached("IC_ENT") is None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.02)
    assert svc.cached("IC_ENT"), "worker never produced the tier-1 thumbnail"
    assert svc.request("IC_ENT", toml, None) == svc.cached("IC_ENT")   # now instant


def test_service_remembers_a_miss(cache):
    import time
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    svc = thumbs.ThumbService()
    toml = cache / "bare2" / "Y.field.toml"
    toml.parent.mkdir()
    toml.write_text("[field]\nid = 2\n", encoding="utf-8")
    svc.request("Y", toml, None)
    deadline = time.monotonic() + 10
    while "Y" not in svc._miss and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.02)
    assert "Y" in svc._miss                            # remembered: no retry storm on every click
    assert svc.request("Y", toml, None) is None and svc._q.qsize() == 0
    svc.invalidate("Y")                                # F5's analogue re-arms it
    assert "Y" not in svc._miss
