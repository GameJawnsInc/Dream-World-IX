"""The shipped continent-v1 waystation example -- the central-cache reference pattern's build oracle.

``waystation.field.toml`` references field 2800's extracted camera by the documented central-cache path
(``../../.ff9mapkit-cache/fields/2800/camera.bgx`` -- the ``extract.cache_field`` one-copy pattern), which
the traversal guard must accept via its second trusted root. This regressed once: the guard shipped
confined to the toml's own directory and every cache-referencing toml crashed validate with
PathTraversalError -- and no test built this example, so it went unnoticed.

Offline by construction: the tests run against a tmp MIRROR of the kit layout (the real example file
copied in, a camera the kit's own ``guide.make_camera`` synthesized -- zero SE bytes -- and
``$FF9MAPKIT_DATA`` pinning the cache root into tmp), so they never read or write the shared working
tree's cache. They still need the extracted blank-field TEMPLATES to build, so they SKIP in a fresh
worktree (run ``ff9mapkit extract-templates`` first, or run in the main repo).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from ff9mapkit import provision
from ff9mapkit.build import FieldProject, build_mod, validate
from ff9mapkit.scene import cam as _cam, guide

WAYSTATION = Path(__file__).resolve().parents[1] / "examples" / "continent-v1" / "waystation.field.toml"
_BLANK = provision.blank_dir()          # resolved BEFORE any test pins $FF9MAPKIT_DATA into tmp

pytestmark = pytest.mark.skipif(
    not (_BLANK / "us.eb.bytes").is_file(),
    reason="needs the extracted templates (py -m ff9mapkit extract-templates)")


@pytest.fixture
def mirror(tmp_path, monkeypatch):
    """A tmp mirror of the kit layout the example's `../..` ref resolves against:
    kit/.ff9mapkit-cache/ (= $FF9MAPKIT_DATA: the cache root AND the template data root, seeded with the
    real templates + a synthesized fields/2800/camera.bgx) and kit/examples/continent-v1/ (the real toml,
    copied verbatim). Returns the mirrored toml's path."""
    kit = tmp_path / "kit"
    cache = kit / ".ff9mapkit-cache"
    shutil.copytree(_BLANK, cache / "blank_field")
    shutil.copy2(provision.region_template_path(), cache / "region_template.bin")
    camdir = cache / "fields" / "2800"
    camdir.mkdir(parents=True)
    c = guide.make_camera(25.0, 4500.0, fov_x_deg=42.2)     # kit-synthesized stand-in, zero SE bytes
    (camdir / "camera.bgx").write_text(_cam.format_bgx_camera(c), encoding="utf-8")
    ex = kit / "examples" / "continent-v1"
    ex.mkdir(parents=True)
    shutil.copy2(WAYSTATION, ex / WAYSTATION.name)
    monkeypatch.setenv("FF9MAPKIT_DATA", str(cache))
    return ex / WAYSTATION.name


def test_waystation_example_validates_with_populated_cache(mirror):
    """The cache ref must resolve through the guard's trusted cache root -- validate clean, not a
    PathTraversalError crash."""
    assert validate(FieldProject.load(mirror)) == []


def test_waystation_example_builds_offline(mirror, tmp_path):
    p = FieldProject.load(mirror)
    result = build_mod([p], tmp_path / "out", mod_name="Waystation")
    assert any("FieldScene 6500" in line for line in result["dictionary"])
    # its dialogue is real text -> the field's own .mes lands
    assert (tmp_path / "out" / "FF9_Data/embeddedasset/text/us/field/6500.mes").is_file()


def test_waystation_without_cache_is_a_finding_not_a_crash(tmp_path, monkeypatch):
    """An UNPOPULATED cache degrades to a clean validate problem ("not found"), never a mid-validate
    crash -- lint is the offline front door."""
    kit = tmp_path / "kit"
    cache = kit / ".ff9mapkit-cache"
    cache.mkdir(parents=True)
    ex = kit / "examples" / "continent-v1"
    ex.mkdir(parents=True)
    shutil.copy2(WAYSTATION, ex / WAYSTATION.name)
    monkeypatch.setenv("FF9MAPKIT_DATA", str(cache))
    problems = validate(FieldProject.load(ex / WAYSTATION.name))
    assert any("borrow scene not found" in pr for pr in problems), problems
