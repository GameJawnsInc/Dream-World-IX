"""Offline tests for the model-preview cache reads (thumbcache) + the Info Hub preview hook.

The contract under test: cache READS are pure + install-free (safe from the tk-free Info Hub and
the GUI thread), and ``infohub.detail`` surfaces a cached preview for every model-backed entry --
but never renders one itself.
"""
import pytest

pytest.importorskip("PIL")
from PIL import Image

from ff9mapkit import infohub, provision
from ff9mapkit.models import thumbcache


@pytest.fixture
def fake_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(provision, "cache_dir", lambda: tmp_path)
    return tmp_path


def _warm(gid: int):
    png, _meta = thumbcache.model_thumb_paths(gid)
    png.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", (8, 8), (255, 0, 0, 255)).save(png)
    return png


def test_cached_png_reads_only(fake_cache):
    assert thumbcache.cached_png(8) is None          # nothing cached -> None, no render attempt
    p = _warm(8)
    assert thumbcache.cached_png(8) == str(p)
    assert thumbcache.cached_png("garbage") is None  # a bad id degrades to None, never raises


def test_meta_sidecar_roundtrip(fake_cache):
    _png, meta = thumbcache.model_thumb_paths(8)
    meta.parent.mkdir(parents=True, exist_ok=True)
    meta.write_text('{"bones": 28}', encoding="utf-8")
    assert thumbcache.model_thumb_meta(8) == {"bones": 28}
    assert thumbcache.model_thumb_meta(9999) is None
    meta.write_text("not json", encoding="utf-8")
    assert thumbcache.model_thumb_meta(8) is None    # a corrupt sidecar degrades to None


def _vivi_entry():
    (e,) = [e for e in infohub.browse("GEO_MAIN_F0_VIV", kinds=("model",)) if e.ident == 8]
    return e


def test_infohub_detail_surfaces_a_cached_preview(fake_cache):
    d = infohub.detail(_vivi_entry())
    assert d.preview_png is None                     # cold cache -> no image, and no render happened
    p = _warm(8)
    d = infohub.detail(_vivi_entry())
    assert d.preview_png == str(p)


# ------------------------------------------------- the clip-frame cache is CAPPED (LRU by play) -----
import os          # noqa: E402
import time        # noqa: E402


def _fake_clip(gid, aid, *, frames=3, size=1000, played=None, sidecar=True):
    """Write a clip's frames (+ sidecar) straight into the cache; ``played`` back-dates its LRU stamp."""
    paths = []
    for f in range(frames):
        p = thumbcache.anim_frame_path(gid, aid, f)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x" * size)
        paths.append(p)
    meta = thumbcache.anim_meta_path(gid, aid)
    if sidecar:
        meta.write_text("{}", encoding="utf-8")
        paths.append(meta)
    if played is not None:
        for p in paths:
            os.utime(p, (played, played))
    return paths


def test_the_clip_cache_evicts_the_least_recently_played_clip_whole(fake_cache):
    now = time.time()
    old = _fake_clip(8, 100, played=now - 3000)
    mid = _fake_clip(8, 200, played=now - 2000)
    new = _fake_clip(8, 300, played=now - 1000)
    freed = thumbcache.prune_anim_cache(budget=6500)        # three ~3 KB clips -> room for two
    assert freed >= 3000
    assert not any(p.exists() for p in old), "the OLDEST-played clip goes, and it goes WHOLE"
    assert all(p.exists() for p in mid + new)


def test_touching_a_clip_moves_it_to_the_back_of_the_line(fake_cache):
    now = time.time()
    a = _fake_clip(8, 100, played=now - 3000)
    b = _fake_clip(8, 200, played=now - 2000)
    thumbcache.touch_anim_clip(8, 100)                      # played again just now
    thumbcache.prune_anim_cache(budget=3500)                # room for one
    assert all(p.exists() for p in a), "a clip that was just played must outlive an idle one"
    assert not any(p.exists() for p in b)


def test_the_clip_that_was_just_built_is_never_the_one_evicted(fake_cache):
    now = time.time()
    built = _fake_clip(8, 100, played=now - 9000)           # oldest stamp, but it is the keep
    other = _fake_clip(8, 200, played=now - 10)
    thumbcache.prune_anim_cache(budget=3500, keep=(8, 100))
    assert all(p.exists() for p in built) and not any(p.exists() for p in other)


def test_an_aborted_fill_with_no_sidecar_is_still_evictable(fake_cache):
    now = time.time()
    orphan = _fake_clip(8, 100, played=now - 5000, sidecar=False)
    live = _fake_clip(8, 200, played=now - 10)
    thumbcache.prune_anim_cache(budget=3500)
    assert not any(p.exists() for p in orphan) and all(p.exists() for p in live)


def test_a_cache_under_budget_and_an_unlimited_budget_delete_nothing(fake_cache, monkeypatch):
    clip = _fake_clip(8, 100)
    assert thumbcache.prune_anim_cache(budget=10 ** 9) == 0
    assert thumbcache.prune_anim_cache(budget=0) == 0, "0 means UNLIMITED, never 'delete everything'"
    monkeypatch.setenv("FF9MAPKIT_ANIM_CACHE_MB", "0")
    assert thumbcache.anim_cache_budget() == 0 and thumbcache.prune_anim_cache() == 0
    assert all(p.exists() for p in clip)
    monkeypatch.setenv("FF9MAPKIT_ANIM_CACHE_MB", "12")
    assert thumbcache.anim_cache_budget() == 12 * 1024 * 1024
    monkeypatch.setenv("FF9MAPKIT_ANIM_CACHE_MB", "banana")
    assert thumbcache.anim_cache_budget() == thumbcache.ANIM_CACHE_MB * 1024 * 1024


def test_the_cache_stats_count_what_is_on_disk(fake_cache):
    assert thumbcache.anim_cache_stats() == {"clips": 0, "files": 0, "bytes": 0}
    assert thumbcache.still_cache_stats() == {"rendered": 0, "absent": 0, "stale": 0, "bytes": 0}
    _fake_clip(8, 100, frames=2, size=10)
    _fake_clip(9, 100, frames=1, size=10)
    st = thumbcache.anim_cache_stats()
    assert st["clips"] == 2 and st["files"] == 5 and st["bytes"] == 30 + 4     # 3 frames + 2 "{}"
    _warm(8)
    png, meta = thumbcache.model_thumb_paths(9)
    meta.write_text('{"id": 9, "absent": true}', encoding="utf-8")
    (png.parent / "7_v1.png").write_bytes(b"old generation")
    st = thumbcache.still_cache_stats()
    assert st["rendered"] == 1 and st["absent"] == 1 and st["stale"] == 1 and st["bytes"] > 0


def test_clearing_the_cache_takes_stills_and_clips_and_nothing_else(fake_cache):
    still = _warm(8)
    clip = _fake_clip(8, 100)
    # the SAME cache root holds real work (extracted cameras, world drafts, DEPLOY BACKUPS) -- and a
    # stray non-preview file inside a preview dir is somebody's, not ours
    bystanders = [fake_cache / "fields" / "100" / "camera.bgx",
                  fake_cache / "deploy" / "backups" / "FF9CustomMap.zip",
                  still.parent / "notes.txt",
                  clip[0].parent / "keep" / "nested.png"]
    for b in bystanders:
        b.parent.mkdir(parents=True, exist_ok=True)
        b.write_bytes(b"not a preview")
    freed = thumbcache.clear_preview_cache()
    assert freed > 0 and not still.exists() and not any(p.exists() for p in clip)
    assert all(b.exists() for b in bystanders),         "the preview clear takes rendered PNGs + sidecars at the top of its two dirs, and nothing else"
    assert thumbcache.clear_preview_cache() == 0
