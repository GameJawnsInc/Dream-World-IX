"""Fences for the Models tab's ANIMATION PREVIEW -- the AnimFrameService + the clip list + the
player strip (Stage B of the animation-preview arc).

Three mechanisms, each fenced against the no-op:

  * the SERVICE -- ``AnimFrameService`` answers a warm disk clip SYNCHRONOUSLY (no worker, no
    signal), remembers a miss with its reason, and ``supersede()`` really cancels: the running
    build's ``should_abort()`` reads the generation it bumps;
  * the STRIP -- the transport is wired (play starts the timer, reset restores the STILL, a model or
    clip switch supersedes), playback loops the CONTIGUOUS cached prefix and never gates on "all
    frames", and a frameReady for a clip the strip did not arm paints NOTHING (the identity fence
    lives at the slot, because a queued emit can outrun any counter);
  * the CLIP LIST -- ``catalog.clip_inventory`` rows carry the id they fill in and mark cross-form
    clips, and the one "Copy anims= snippet" button writes a TOML inline table.

Headless (offscreen); EVERY cache read is pinned to a scratch ``FF9MAPKIT_DATA`` (it moves BOTH the
cache dir and the templates dir) and the doc tests use a service double, so nothing here can reach
this machine's install or its real preview cache even if a guard regresses.
"""
from __future__ import annotations

import json
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")
pytest.importorskip("PySide6")

from PySide6.QtCore import QObject, Qt, Signal                        # noqa: E402
from PySide6.QtGui import QPixmap                                     # noqa: E402
from PySide6.QtWidgets import QApplication                            # noqa: E402

from ff9mapkit import catalog                                         # noqa: E402
from ff9mapkit.editor.theme import pick_palette                       # noqa: E402
from ff9mapkit.models import thumbcache                               # noqa: E402
from ff9mapkit.workspace import animframes, style                     # noqa: E402
from ff9mapkit.workspace.modelsdoc import ModelsDoc                   # noqa: E402

_VIV = "GEO_MAIN_F0_VIV"                                              # model id 8 -- the anchor
_VIV_ID = 8
_STAND = 148                                                          # its canonical stand clip


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pin_cache(tmp_path, monkeypatch):
    """Every provision.cache_dir() read/write lands in a scratch dir -- never the developer's."""
    monkeypatch.setenv("FF9MAPKIT_DATA", str(tmp_path))
    return tmp_path


@pytest.fixture
def thumbs_on(monkeypatch):
    monkeypatch.setenv("FF9MAPKIT_NO_THUMBS", "0")


def _seed_clip(cache_root, geo_id=_VIV_ID, anim=_STAND, frames=(0, 1, 2), *, stride=1,
               frame_count=3, rate=30.0):
    """Write a WARM clip into the pinned cache: one PNG per rendered frame + the meta sidecar."""
    d = cache_root / "anim_frames"
    d.mkdir(parents=True, exist_ok=True)
    for f in frames:
        pm = QPixmap(8, 8)
        pm.fill(Qt.GlobalColor.white)
        pm.save(str(thumbcache.anim_frame_path(geo_id, anim, f)), "PNG")
    meta = {"geo": _VIV, "id": geo_id, "anim": anim, "frame_count": frame_count,
            "sample_rate": rate, "stride": stride, "fps": rate / stride, "fit": [0, 1, 0, 1],
            "label": "stand", "rendered_frames": list(frames)}
    thumbcache.anim_meta_path(geo_id, anim).write_text(json.dumps(meta), encoding="utf-8")
    return meta


def _seed_still(cache_root, geo_id=_VIV_ID):
    png, _meta = thumbcache.model_thumb_paths(geo_id)
    png.parent.mkdir(parents=True, exist_ok=True)
    pm = QPixmap(8, 8)
    pm.fill(Qt.GlobalColor.black)
    pm.save(str(png), "PNG")
    return str(png)


# ---------------------------------------------------------------------------- the service doubles
class _StubAnimFrames(QObject):
    """The FULL service surface with NO worker and NO install reach. Kept in lockstep with
    :class:`~ff9mapkit.workspace.animframes.AnimFrameService` by
    ``test_the_stub_double_covers_the_whole_service_surface`` below -- a double that drifts off the
    real surface is how a GUI fence starts passing against a service that no longer exists."""

    frameReady = Signal(str, int, int, str)
    clipDone = Signal(str, int)
    clipMissed = Signal(str, int, str)

    def __init__(self):
        super().__init__()
        self.requests = []
        self.supersedes = 0
        self.holds = 0
        self.warm = {}                            # (geo, anim) -> meta dict
        self.frames = {}                          # (geo, anim, frame) -> png path
        self.misses = {}                          # (geo, anim) -> reason

    def cached_frame(self, geo, anim, frame):
        return self.frames.get((str(geo), int(anim), int(frame)))

    def cached_meta(self, geo, anim):
        return self.warm.get((str(geo), int(anim)))

    def missed_reason(self, geo, anim):
        return self.misses.get((str(geo), int(anim)))

    def request_clip(self, geo, anim):
        self.requests.append((str(geo), int(anim)))
        return self.warm.get((str(geo), int(anim)))

    def supersede(self):
        self.supersedes += 1

    def hold(self):
        self.holds += 1

    def release(self):
        self.holds -= 1


class _StubThumbs(QObject):
    ready = Signal(str, str)
    missed = Signal(str)

    def __init__(self):
        super().__init__()
        self.requests = []
        self._cached = {}

    def cached(self, name):
        return self._cached.get(name)

    def request(self, name):
        self.requests.append(name)
        return self._cached.get(name)


def test_the_stub_double_covers_the_whole_service_surface():
    """THE CALL-SITE LAW's mirror: every public member the real service ships must exist on the
    double, or a doc fence proves nothing about the shipped service."""
    real = {n for n in dir(animframes.AnimFrameService)
            if not n.startswith("_") and n not in dir(QObject)}
    stub = {n for n in dir(_StubAnimFrames) if not n.startswith("_")}
    assert real <= stub, f"the double is missing {sorted(real - stub)}"


# ------------------------------------------------------------------------------------ the service
def test_a_warm_clip_answers_from_disk_with_no_worker_and_no_signal(app, pin_cache, thumbs_on,
                                                                    monkeypatch):
    """A broken fast path must FAIL here, not fall through to a real render on this machine."""
    monkeypatch.setattr(thumbcache, "build_anim_clip",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("worker path taken")))
    meta = _seed_clip(pin_cache)
    svc = animframes.AnimFrameService()
    seen = []
    svc.frameReady.connect(lambda *a: seen.append(a))
    svc.clipDone.connect(lambda *a: seen.append(a))
    got = svc.request_clip(_VIV, _STAND)
    assert got == meta, "the RETURN VALUE is the warm answer"
    assert svc._worker is None, "a warm cache read must not spawn the worker"
    app.processEvents()
    assert seen == [], "a warm hit emits NOTHING -- a caller waiting on a signal would wait forever"
    assert svc.cached_frame(_VIV, _STAND, 1) == str(thumbcache.anim_frame_path(_VIV_ID, _STAND, 1))


def test_a_half_written_clip_is_not_warm(app, pin_cache, thumbs_on, monkeypatch):
    """Meta on disk with a frame missing is a COLD clip: the sidecar alone must never be trusted."""
    _seed_clip(pin_cache, frames=(0, 1, 2))
    thumbcache.anim_frame_path(_VIV_ID, _STAND, 2).unlink()
    enqueued = []
    svc = animframes.AnimFrameService()
    monkeypatch.setattr(svc, "_start_worker", lambda: enqueued.append(True))
    assert svc.request_clip(_VIV, _STAND) is None
    assert enqueued, "a missing frame must fall through to the worker"


def test_the_service_is_gated_by_the_no_thumbs_flag(app, pin_cache):
    _seed_clip(pin_cache)
    svc = animframes.AnimFrameService()
    assert svc.request_clip(_VIV, _STAND) is None, "NO_THUMBS gates the disk read too"
    assert svc._worker is None


def test_supersede_clears_the_queue_and_aborts_the_running_build(app, pin_cache, thumbs_on,
                                                                 monkeypatch):
    """The reason the queue is clip-shaped: a mis-click must not cost the whole fill."""
    svc = animframes.AnimFrameService()
    monkeypatch.setattr(svc, "_start_worker", lambda: None)      # no thread -- inspect the queue
    svc.request_clip(_VIV, _STAND)
    assert svc._q.qsize() == 1 and (_VIV, _STAND) in svc._pending
    gen = svc._gen
    svc.supersede()
    assert svc._q.empty() and svc._pending == set()
    assert svc._stale(gen), "the in-flight build's should_abort() must now answer True"
    assert not svc._stale(svc._gen), "a clip armed AFTER the supersede must run"


def test_a_missed_clip_is_remembered_with_its_reason(app, pin_cache, thumbs_on, monkeypatch):
    """A miss must never retry-storm, and must still be ANSWERABLE the second time it is armed --
    a remembered miss enqueues nothing, so no second clipMissed would ever arrive."""
    monkeypatch.setattr(thumbcache, "build_anim_clip", lambda *a, **k: None)
    svc = animframes.AnimFrameService()
    missed = []
    svc.clipMissed.connect(lambda *a: missed.append(a))
    svc.request_clip(_VIV, _STAND)
    svc._worker.join(timeout=10)
    app.processEvents()
    assert missed and missed[0][0] == _VIV and missed[0][1] == _STAND and missed[0][2]
    assert svc.missed_reason(_VIV, _STAND), "the reason survives for the next arm"
    svc.request_clip(_VIV, _STAND)
    assert svc._q.empty(), "a remembered miss must not re-enqueue"


def test_the_worker_streams_every_frame_with_the_full_identity(app, pin_cache, thumbs_on,
                                                               monkeypatch):
    """frameReady carries (geo, anim, frame, path) so the consumer can drop what it did not arm."""
    def _fake_build(token, anim_id, ctx=None, *, on_frame=None, should_abort=None):
        for f in (0, 1):
            on_frame(f, f"frame{f}.png")
        return {"rendered_frames": [0, 1], "fps": 30.0, "stride": 1, "frame_count": 2}
    monkeypatch.setattr(thumbcache, "build_anim_clip", _fake_build)
    svc = animframes.AnimFrameService()
    got, done = [], []
    svc.frameReady.connect(lambda *a: got.append(a))
    svc.clipDone.connect(lambda *a: done.append(a))
    svc.request_clip(_VIV, _STAND)
    svc._worker.join(timeout=10)
    app.processEvents()
    assert got == [(_VIV, _STAND, 0, "frame0.png"), (_VIV, _STAND, 1, "frame1.png")]
    assert done == [(_VIV, _STAND)]


def test_hold_parks_the_fill_until_release(app, pin_cache, thumbs_on, monkeypatch):
    svc = animframes.AnimFrameService()
    started = []
    monkeypatch.setattr(svc, "_start_worker", lambda: started.append(True))
    svc.hold()
    svc.request_clip(_VIV, _STAND)
    assert not started, "a held service must not start the worker"
    svc.release()
    assert started, "release() picks up what queued while held"


# --------------------------------------------------------------------------------- the clip list
@pytest.fixture
def doc(app, pin_cache, monkeypatch):
    from ff9mapkit.editor import jobs
    monkeypatch.setattr(jobs, "detect_game_mod", lambda: None)   # never read this machine's install
    svc, anims = _StubThumbs(), _StubAnimFrames()
    d = ModelsDoc(pick_palette("dark"), ".", run=lambda *a, **k: True,
                  model_thumbs=svc, anim_frames=anims)
    d._svc, d._anim_svc = svc, anims
    return d


def _select_vivi(doc):
    doc.search.setText(_VIV)
    doc.listw.setCurrentRow(0)
    assert doc._current is not None and doc._current.id == _VIV_ID


def test_the_clip_list_replaces_the_blob_and_carries_the_ids(doc):
    _select_vivi(doc)
    rows = [doc.clip_list.item(i).text() for i in range(doc.clip_list.count())]
    assert len(rows) == len(catalog.clip_inventory(_VIV_ID)) > 5
    assert rows[0].startswith("stand") and f"id {_STAND}" in rows[0]
    assert doc.clip_list.item(0).data(Qt.ItemDataRole.UserRole) == _STAND
    assert doc.clip_list.maximumHeight() > 0, \
        "an uncapped QListWidget hints 256x192 whatever its rows -- it would shove the pane"
    assert not hasattr(doc, "d_anims"), "the comma-blob label is gone, not merely unused"


def test_a_cross_form_clip_is_marked_in_the_row(doc):
    """THE CROSS-FORM CLIP TRAP is a different SKELETON -- a row that plays one must say so."""
    rows = catalog.clip_inventory(_VIV_ID)
    doc._current = catalog.model(_VIV_ID)
    doc._refill_clips(doc._current)
    marked = [doc.clip_list.item(i).text() for i, r in enumerate(rows) if not r["own_form"]]
    clean = [doc.clip_list.item(i).text() for i, r in enumerate(rows) if r["own_form"]]
    assert all("other form" in t for t in marked)
    assert all("other form" not in t for t in clean)


def test_a_refill_does_not_arm_the_player(doc):
    _select_vivi(doc)
    assert doc._armed is None, "picking a MODEL must not start rendering a clip nobody asked for"
    assert doc._anim_svc.requests == []


def test_copying_the_anims_snippet_writes_a_toml_inline_table(doc, app):
    _select_vivi(doc)
    doc._copy_anims()
    text = QApplication.clipboard().text()
    assert text.startswith("anims = { stand = 148,")
    assert text.rstrip().endswith("}")
    for slot in catalog.NPC_SLOT_ACTION:
        assert f"{slot} = " in text


# ------------------------------------------------------------------------------- the player strip
def test_arming_a_warm_clip_paints_from_disk_and_enables_the_transport(doc, monkeypatch, thumbs_on):
    _select_vivi(doc)
    doc._anim_svc.warm[(_VIV, _STAND)] = {"rendered_frames": [0, 1, 2], "fps": 30.0, "stride": 1,
                                          "frame_count": 3, "sample_rate": 30.0}
    for f in (0, 1, 2):
        doc._anim_svc.frames[(_VIV, _STAND, f)] = f"f{f}.png"
    doc.clip_list.setCurrentRow(0)
    assert doc._armed == (_VIV, _STAND)
    assert [f for f, _p in doc._seq] == [0, 1, 2]
    assert doc.anim_slider.maximum() == 2
    assert doc.anim_play.isEnabled() and doc.anim_slider.isEnabled()
    assert "f 1/3" in doc.anim_count.fullText() and "30fps" in doc.anim_count.fullText()


def test_arming_a_new_clip_supersedes_the_last(doc, thumbs_on):
    _select_vivi(doc)
    before = doc._anim_svc.supersedes
    doc.clip_list.setCurrentRow(0)
    doc.clip_list.setCurrentRow(1)
    assert doc._anim_svc.supersedes >= before + 2, "each arm cancels the fill before it"
    assert doc._armed[1] == doc.clip_list.item(1).data(Qt.ItemDataRole.UserRole)


def test_a_frame_for_a_clip_nobody_armed_paints_nothing(doc, thumbs_on):
    """The identity fence lives at the SLOT: a queued emit can outrun any generation counter."""
    _select_vivi(doc)
    doc.clip_list.setCurrentRow(0)
    doc._anim_svc.frameReady.emit("GEO_MAIN_F0_ZDN", 999, 0, "wrong.png")
    doc._anim_svc.frameReady.emit(_VIV, _STAND + 1, 0, "wrong.png")
    assert doc._seq == [], "a non-matching identity must be dropped, not painted"
    doc._anim_svc.frameReady.emit(_VIV, _STAND, 0, "right.png")
    assert [p for _f, p in doc._seq] == ["right.png"]


def test_playback_loops_the_contiguous_prefix_as_it_grows(doc, thumbs_on):
    """Never gate on 'all frames': two landed frames are already a loop, and the loop EXTENDS."""
    _select_vivi(doc)
    doc.clip_list.setCurrentRow(0)
    doc._anim_svc.frameReady.emit(_VIV, _STAND, 0, "f0.png")
    assert not doc.anim_play.isEnabled(), "one frame is not a loop"
    doc._anim_svc.frameReady.emit(_VIV, _STAND, 1, "f1.png")
    assert doc.anim_play.isEnabled()
    doc.anim_play.setChecked(True)
    assert doc._play_timer.isActive(), "play must start the clock"
    doc._advance()
    assert doc.anim_slider.value() == 1
    doc._advance()
    assert doc.anim_slider.value() == 0, "the prefix LOOPS"
    doc._anim_svc.frameReady.emit(_VIV, _STAND, 2, "f2.png")
    assert doc.anim_slider.maximum() == 2, "a late frame extends the loop without a re-arm"
    doc.anim_play.setChecked(False)
    assert not doc._play_timer.isActive()


def test_a_single_frame_clip_disables_the_transport_with_a_reason(doc, thumbs_on):
    _select_vivi(doc)
    doc._anim_svc.warm[(_VIV, _STAND)] = {"rendered_frames": [0], "fps": 30.0, "stride": 1,
                                          "frame_count": 1, "sample_rate": 30.0}
    doc._anim_svc.frames[(_VIV, _STAND, 0)] = "only.png"
    doc.clip_list.setCurrentRow(0)
    assert not doc.anim_play.isEnabled()
    assert "single-frame" in doc.anim_note.text()


def test_a_strided_clip_says_the_honest_rate(doc, thumbs_on):
    _select_vivi(doc)
    doc._anim_svc.warm[(_VIV, _STAND)] = {"rendered_frames": [0, 2], "fps": 15.0, "stride": 2,
                                          "frame_count": 4, "sample_rate": 30.0}
    doc._anim_svc.frames.update({(_VIV, _STAND, 0): "a.png", (_VIV, _STAND, 2): "b.png"})
    doc.clip_list.setCurrentRow(0)
    assert "preview 15fps" in doc.anim_count.fullText(), \
        "a strided clip plays SLOWER than its sample rate -- the counter must not claim 30"
    assert doc._play_interval() == 67
    assert "15fps" in doc.anim_note.text() and "every 2" in doc.anim_note.text(), \
        "the counter can elide at the wide CALIBRE rungs -- the rate must also live in the prose"


def test_reset_stops_and_restores_the_still(doc, thumbs_on):
    _select_vivi(doc)
    doc._svc._cached[_VIV] = "still.png"
    doc.clip_list.setCurrentRow(0)
    doc._anim_svc.frameReady.emit(_VIV, _STAND, 0, "f0.png")
    doc._anim_svc.frameReady.emit(_VIV, _STAND, 1, "f1.png")
    doc.anim_play.setChecked(True)
    painted = []
    doc._set_detail_image = lambda png: painted.append(png)
    doc.reset_player()
    assert not doc._play_timer.isActive() and not doc.anim_play.isChecked()
    assert painted == ["still.png"], "Reset puts the STILL back, not frame 0"


def test_a_remembered_miss_is_answered_on_the_spot(doc, thumbs_on):
    """Re-arming a known-unrenderable clip enqueues nothing, so waiting for a signal would hang the
    strip on 'rendering…' forever."""
    _select_vivi(doc)
    doc._anim_svc.misses[(_VIV, _STAND)] = "no p0data5 on this machine"
    doc.clip_list.setCurrentRow(0)
    assert "no p0data5" in doc.anim_note.text()
    assert not doc.anim_play.isEnabled()


def test_leaving_the_tab_stops_the_clock_and_cancels_the_fill(doc, app, thumbs_on):
    _select_vivi(doc)
    doc.clip_list.setCurrentRow(0)
    doc._anim_svc.frameReady.emit(_VIV, _STAND, 0, "f0.png")
    doc._anim_svc.frameReady.emit(_VIV, _STAND, 1, "f1.png")
    doc.anim_play.setChecked(True)
    before = doc._anim_svc.supersedes
    doc.show()
    app.processEvents()
    doc.hide()
    app.processEvents()
    assert not doc._play_timer.isActive(), "a hidden tab must not keep a timer running"
    assert doc._anim_svc.supersedes > before, "a background clip must not outlive the surface"


def test_previews_off_hides_the_strip_and_keeps_the_list(app, pin_cache, monkeypatch):
    """NO_THUMBS is the headless/no-install gate: the ids are still browsable (they paste into
    anims=), but nothing renders and the strip does not pretend otherwise."""
    from ff9mapkit.editor import jobs
    monkeypatch.setattr(jobs, "detect_game_mod", lambda: None)
    anims = _StubAnimFrames()
    d = ModelsDoc(pick_palette("dark"), ".", run=lambda *a, **k: True,
                  model_thumbs=_StubThumbs(), anim_frames=anims)
    assert d.anim_strip.isHidden()
    assert "Previews off" in d.anim_note.text()
    d.search.setText(_VIV)
    d.listw.setCurrentRow(0)
    assert d.clip_list.count() > 5, "the clip list is install-free -- it stays"
    d.clip_list.setCurrentRow(0)
    assert anims.requests == [], "NO_THUMBS must never reach the render path"


def test_the_counter_is_budgeted_by_the_layout_not_handed_zero(doc):
    """SNAP-CAUGHT: the counter was laid out at x == the strip's whole width, entirely off the edge.

    ``qGeomCalc``'s SURPLUS branch hands every item its sizeHint and only the SQUEEZE branch consults
    the minimum -- so an item whose hint is SMALLER than its minimum gets 0. ``QSizePolicy.Ignored``
    (what ElideLabel ships, so a caption can yield all the way to '…') makes exactly that shape:
    QWidgetItem zeroes an Ignored item's hint width while qSmartMinSize still honours the explicit
    min_ch minimum. Offscreen font metrics are fiction, but this COMPARISON is not -- both sides are
    measured in the same stubbed font."""
    from PySide6.QtWidgets import QWidgetItem
    doc.anim_count.setText("f 12/31 · preview 15fps")
    item = QWidgetItem(doc.anim_count)
    assert item.minimumSize().width() > 0, "the counter must claim a floor at all"
    assert item.sizeHint().width() >= item.minimumSize().width(), \
        "hint < minimum -- the layout's surplus branch will hand this control zero width"


# ------------------------------------------------------------------------------- a11y + the sheet
def test_every_transport_control_announces_itself(doc):
    for w in (doc.anim_play, doc.anim_reset_btn, doc.anim_slider, doc.clip_list):
        assert w.accessibleName(), f"{type(w).__name__} has no screen-reader name"


def test_the_frame_slider_has_a_focus_ring_in_every_palette():
    """A bare QSlider carries no frame, so the ring must be RESERVED transparent and coloured on
    focus -- and id-scoped, because an app-wide QSlider box rule flips every slider (the CALIBRE
    dial, the sim stepper) off Fusion's native groove painting."""
    from ff9mapkit.editor.theme import derive
    for mode in ("dark", "light", "nord"):
        pal = pick_palette(mode)
        css = style.qss(pal)
        assert "QSlider#animFrameSlider { border: 1px solid transparent" in css
        assert "QSlider#animFrameSlider:focus" in css
        assert derive(pal)["focus"] in css


def test_the_transport_wears_svg_icons_not_unicode_glyphs(doc):
    """U+23F5-class media glyphs fall back to the Windows emoji face and render as colour blobs."""
    for b in (doc.anim_play, doc.anim_reset_btn):
        assert b.text() == "", f"{b.accessibleName()} carries a text glyph"
        assert not b.icon().isNull(), f"{b.accessibleName()} has no icon"
