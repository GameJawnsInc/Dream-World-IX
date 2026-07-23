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


def test_build_thumb_corrupt_png_raises_and_service_records_a_miss(cache):
    import time
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    proj = cache / "CORRUPT"
    proj.mkdir()
    toml = proj / "C.field.toml"
    toml.write_text("[field]\nid = 3\n", encoding="utf-8")
    (proj / "background.png").write_bytes(b"not a png at all")
    with pytest.raises(Exception):                      # the pure builder raises (PIL can't identify it)...
        thumbs.build_thumb(toml, None)
    svc = thumbs.ThumbService()                         # ...and the service swallows it into a MISS
    svc.request("C", toml, None)
    deadline = time.monotonic() + 10
    while "C" not in svc._miss and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.02)
    assert "C" in svc._miss and svc.cached("C") is None


def test_hold_defers_the_worker_and_release_drains(cache):
    """The open-quiet gate: a request during hold() ENQUEUES but must not start the worker (the whole
    point -- no GIL-heavy build racing a journey open), and release() starts it and the build lands.
    Holds are COUNTED: one release of two is not enough."""
    import time
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    svc = thumbs.ThumbService()
    toml = _project(cache)
    svc.hold()
    svc.hold()                                          # nested (construction + an open) -- counted
    assert svc.request("IC_ENT", toml, None) is None
    assert svc._worker is None and svc._q.qsize() == 1  # queued, but NO worker while held
    svc.release()
    assert svc._worker is None                          # still one hold outstanding
    svc.release()
    deadline = time.monotonic() + 10
    while svc.cached("IC_ENT") is None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.02)
    assert svc.cached("IC_ENT"), "release() never drained the held queue"


def test_hold_pauses_a_running_worker_between_builds(cache, monkeypatch):
    """A later open must pause an ALREADY-CHURNING worker: an in-flight build finishes (the documented
    one-build bound), but the NEXT dequeued item waits at the gate until release(). Deterministic via a
    stub that blocks build A until the test has taken the hold."""
    import time
    import threading as _t
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    toml_a = _project(cache)
    proj_b = cache / "IC_B"
    proj_b.mkdir()
    toml_b = proj_b / "IC_B.field.toml"
    toml_b.write_text('[field]\nid = 30101\nname = "IC_B"\narea = 11\n', encoding="utf-8")
    Image.new("RGB", (300, 200), (40, 40, 120)).save(proj_b / "background.png")
    a_entered, a_go = _t.Event(), _t.Event()
    real_build = thumbs.build_thumb

    def gated_build(t, rid):
        if t and "IC_ENT" in str(t):                    # build A parks until the test holds the service
            a_entered.set()
            assert a_go.wait(timeout=10)
        return real_build(t, rid)
    monkeypatch.setattr(thumbs, "build_thumb", gated_build)
    svc = thumbs.ThumbService()
    svc.request("IC_ENT", toml_a, None)                 # worker starts, enters build A, parks
    svc.request("IC_B", toml_b, None)
    assert a_entered.wait(timeout=10)
    svc.hold()                                          # 'an open begins' while A is in flight
    a_go.set()                                          # A finishes + lands (the one-build bound)...
    deadline = time.monotonic() + 10
    while svc.cached("IC_ENT") is None and time.monotonic() < deadline:
        time.sleep(0.01)
    assert svc.cached("IC_ENT")
    time.sleep(0.3)                                     # ...but B must WAIT at the gate, not build
    assert svc.cached("IC_B") is None, "a held worker started the next build anyway"
    svc.release()
    deadline = time.monotonic() + 10
    while svc.cached("IC_B") is None and time.monotonic() < deadline:
        time.sleep(0.02)
    assert svc.cached("IC_B"), "the paused worker never resumed after release()"


def test_model_service_hold_defers_the_worker(cache, monkeypatch):
    """Same contract on ModelThumbService -- the service whose construction-time batch was measured
    racing the startup open. build_model_thumb is stubbed (no install in CI)."""
    import time
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    out = cache / "fake_model.png"
    Image.new("RGB", (8, 8), (10, 10, 10)).save(out)
    monkeypatch.setattr(thumbs, "build_model_thumb", lambda name, ctx: str(out))
    svc = thumbs.ModelThumbService()
    svc.hold()
    assert svc.request("GEO_TEST_HOLD") is None
    assert svc._worker is None and svc._q.qsize() == 1  # queued, but NO worker while held
    svc.release()
    deadline = time.monotonic() + 10
    while svc.cached("GEO_TEST_HOLD") is None and time.monotonic() < deadline:
        time.sleep(0.02)
    assert svc.cached("GEO_TEST_HOLD") == str(out)


def test_invalidate_drops_an_in_flight_stale_build(cache):
    """The generation counter: a result whose build STARTED before invalidate() must not land (it may
    have read pre-refresh art). Simulated by monkeypatching build_thumb to wait for the bump."""
    import time
    import threading as _t
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    toml = _project(cache)
    svc = thumbs.ThumbService()
    bumped = _t.Event()
    real_build = thumbs.build_thumb

    def slow_build(t, rid):
        bumped.wait(timeout=10)                         # hold the in-flight build until F5 fires
        return real_build(t, rid)
    thumbs.build_thumb = slow_build
    try:
        svc.request("IC_ENT", toml, None)
        worker = svc._worker
        time.sleep(0.2)                                 # the worker is now inside slow_build
        svc.invalidate()                                # F5 while in flight
        bumped.set()
        worker.join(timeout=15)                         # let the worker COMMIT (i.e. drop) + retire
        app.processEvents()
        assert svc.cached("IC_ENT") is None, "a stale in-flight result landed after invalidate()"
    finally:
        thumbs.build_thumb = real_build
