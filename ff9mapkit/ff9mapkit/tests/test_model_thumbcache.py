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
