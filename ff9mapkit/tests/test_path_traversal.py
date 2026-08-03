"""Security: ``FieldProject.path()`` confines every field.toml-supplied asset reference to its trusted
roots. Without this, an untrusted/shared field.toml could point an asset ref (portrait/image/obj/bin/...)
at an absolute path or ``..``-escape and make the build read an arbitrary file off the builder's disk -- then
bake its bytes into the mod the builder shares back. Two roots are trusted: the toml's own directory, and the
workspace extract cache's ``fields/`` subtree (``provision.cache_dir()`` -- the documented central-copy home
of ``extract-field`` cameras/walkmeshes; env/install-controlled, never toml-controlled). These tests are
self-contained (a temp base_dir + an env-pinned cache), so they run without the extracted FF9 template cache.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ff9mapkit.build import FieldProject, PathTraversalError


def _proj(base):
    """A bare FieldProject rooted at ``base`` -- enough to exercise .path() (no toml load / templates)."""
    return FieldProject(raw={}, base_dir=base)


# --- legitimate refs stay inside and resolve unchanged ---------------------------------------------------

def test_plain_relative_ref_is_allowed(tmp_path):
    base = tmp_path / "field"
    base.mkdir()
    assert _proj(base).path("walkmesh.obj") == (base / "walkmesh.obj").resolve()


def test_subdir_literal_is_allowed(tmp_path):
    base = tmp_path / "field"
    base.mkdir()
    assert _proj(base).path("layers/bg0.png") == (base / "layers" / "bg0.png").resolve()


def test_empty_ref_resolves_to_base(tmp_path):
    base = tmp_path / "field"
    base.mkdir()
    assert _proj(base).path("") == base.resolve()


def test_dotdot_that_stays_inside_is_allowed(tmp_path):
    """A `..` that never leaves base is fine -- containment is about the RESOLVED target, not the literal."""
    base = tmp_path / "field"
    base.mkdir()
    assert _proj(base).path("a/../b.png") == (base / "b.png").resolve()


def test_absolute_ref_inside_base_is_allowed(tmp_path):
    """An absolute path is fine *as long as it lands under base* -- we confine, we don't ban absolutes."""
    base = tmp_path / "field"
    base.mkdir()
    inside = base / "ok.png"
    assert _proj(base).path(str(inside)) == inside.resolve()


def test_relative_base_dir_is_resolved_before_the_check(tmp_path, monkeypatch):
    """base_dir may be RELATIVE (toml loaded by a relative path); the guard resolves both sides, so a normal
    ref still passes rather than falsely tripping."""
    base = tmp_path / "field"
    base.mkdir()
    monkeypatch.chdir(tmp_path)
    assert _proj(Path("field")).path("art.png") == (base / "art.png").resolve()


# --- escapes are rejected --------------------------------------------------------------------------------

def test_absolute_ref_outside_base_is_rejected(tmp_path):
    base = tmp_path / "field"
    base.mkdir()
    outside = tmp_path / "outside.png"          # absolute, sibling of base -> escapes
    with pytest.raises(PathTraversalError):
        _proj(base).path(str(outside))


def test_dotdot_escape_is_rejected(tmp_path):
    base = tmp_path / "field"
    base.mkdir()
    with pytest.raises(PathTraversalError):
        _proj(base).path("../secret.txt")


def test_deep_dotdot_escape_is_rejected(tmp_path):
    base = tmp_path / "field"
    base.mkdir()
    with pytest.raises(PathTraversalError):
        _proj(base).path("../../../../../../Windows/win.ini")


def test_sibling_prefix_is_not_containment(tmp_path):
    """`field_evil` shares the `field` string prefix but is NOT inside `field` -- guards must compare path
    PARTS (is_relative_to), never str.startswith, or this leaks."""
    base = tmp_path / "field"
    base.mkdir()
    (tmp_path / "field_evil").mkdir()
    with pytest.raises(PathTraversalError):
        _proj(base).path("../field_evil/loot.png")


# --- the second trusted root: the extract cache's fields/ subtree ----------------------------------------

def _pin_cache(tmp_path, monkeypatch):
    """Pin the workspace cache root into tmp via the documented $FF9MAPKIT_DATA seam; return it."""
    root = tmp_path / "kit-cache"
    monkeypatch.setenv("FF9MAPKIT_DATA", str(root))
    return root


def test_relative_ref_into_cache_fields_is_allowed(tmp_path, monkeypatch):
    """The documented central-cache pattern (extract.cache_field): ONE extracted camera.bgx in
    cache_dir()/fields/<id>/, referenced by any number of tomls via a `..` relpath. The root's LOCATION is
    env/install-controlled -- the toml can point INTO the builder's extract cache but can't choose where
    that cache is, so the untrusted-toml threat model survives."""
    root = _pin_cache(tmp_path, monkeypatch)
    cam = root / "fields" / "2800" / "camera.bgx"
    cam.parent.mkdir(parents=True)
    cam.touch()
    base = tmp_path / "proj" / "field"
    base.mkdir(parents=True)
    assert _proj(base).path("../../kit-cache/fields/2800/camera.bgx") == cam.resolve()


def test_absolute_ref_into_cache_fields_is_allowed(tmp_path, monkeypatch):
    """A wheel install's cache lives under %LOCALAPPDATA%, possibly on another drive -- the emitted ref can
    only be absolute there. Absolute is fine when the resolved target lands under the cache fields root."""
    root = _pin_cache(tmp_path, monkeypatch)
    cam = root / "fields" / "950" / "camera.bgx"
    cam.parent.mkdir(parents=True)
    base = tmp_path / "field"
    base.mkdir()
    assert _proj(base).path(str(cam)) == cam.resolve()


def test_cache_outside_fields_is_rejected(tmp_path, monkeypatch):
    """Only the fields/ extract subtree is trusted -- the cache also holds deploy BACKUPS (snapshots of the
    live mod folders, i.e. other mods' content); a toml must not be able to bake those into a shared mod."""
    root = _pin_cache(tmp_path, monkeypatch)
    (root / "deploy" / "backups").mkdir(parents=True)
    base = tmp_path / "field"
    base.mkdir()
    with pytest.raises(PathTraversalError):
        _proj(base).path("../kit-cache/deploy/backups/loot.bin")


def test_cache_fields_prefix_sibling_is_rejected(tmp_path, monkeypatch):
    """`fields_evil` shares the `fields` string prefix but is NOT the trusted subtree -- containment must
    compare path PARTS here too."""
    root = _pin_cache(tmp_path, monkeypatch)
    (root / "fields_evil").mkdir(parents=True)
    base = tmp_path / "field"
    base.mkdir()
    with pytest.raises(PathTraversalError):
        _proj(base).path("../kit-cache/fields_evil/loot.png")


# --- the error contract ----------------------------------------------------------------------------------

def test_error_is_a_valueerror_subclass_naming_the_ref(tmp_path):
    """PathTraversalError subclasses ValueError (existing `except ValueError` handlers still catch it) and the
    message names the offending ref so an author who typoed a `..` gets an actionable error."""
    base = tmp_path / "field"
    base.mkdir()
    assert issubclass(PathTraversalError, ValueError)
    with pytest.raises(ValueError) as ei:
        _proj(base).path("../../etc/passwd")
    assert "etc/passwd" in str(ei.value) or "../../etc/passwd" in str(ei.value)
