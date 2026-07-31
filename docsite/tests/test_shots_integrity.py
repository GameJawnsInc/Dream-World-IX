"""The shot pipeline's Qt-free gates: manifest <-> committed assets <-> the pages that embed them.

Rendering itself is Windows+native-Qt (gui_snap's law) and runs locally via `py docsite/shots.py
--check`; THESE tests are the half CI can always run -- and they FAIL when assets are missing,
never skip (the worktree-skip trap: a green run that verified nothing).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import shots as S  # noqa: E402

ASSETS = S.ASSETS
PAIR = list(S.THEME_PAIR.values())


@pytest.fixture(scope="module")
def manifest():
    return S.load_manifest()


def test_manifest_is_not_empty(manifest):
    assert manifest, "shots.toml declares no figures"


def test_every_shot_has_both_theme_assets_and_sidecars(manifest):
    for name, shot in manifest.items():
        for theme in shot.get("themes", PAIR):
            png = ASSETS / f"{name}_{theme}.png"
            sidecar = png.with_suffix(".json")
            assert png.is_file(), f"{png.name} missing -- run: py docsite/shots.py {name}"
            assert sidecar.is_file(), f"{sidecar.name} missing"


def test_sidecar_schema_and_rect_containment(manifest):
    for name, shot in manifest.items():
        for theme in shot.get("themes", PAIR):
            meta = json.loads((ASSETS / f"{name}_{theme}.json").read_text(encoding="utf-8"))
            for key in ("shot", "surface", "theme", "size", "kit_version", "annotations"):
                assert key in meta, f"{name}_{theme}: sidecar lost its {key!r}"
            w, h = meta["size"]
            assert w > 100 and h > 100
            for a in meta["annotations"]:
                x, y, rw, rh = a["rect"]
                assert 0 <= x and 0 <= y and x + rw <= w and y + rh <= h, \
                    f"{name}_{theme}: annotation {a['widget']} escapes the image"


def test_every_used_by_page_embeds_the_figure(manifest):
    repo = HERE.parent.parent
    for name, shot in manifest.items():
        for rel in shot.get("used_by", []):
            page = repo / rel
            assert page.is_file(), f"{name}: used_by names a missing page {rel}"
            assert f"docsite/assets/shots/{name}_light.png" in page.read_text(encoding="utf-8"), \
                f"{rel} no longer embeds {name} -- update shots.toml's used_by or the page"


def test_no_orphan_assets(manifest):
    owned = {f"{name}_{theme}" for name, shot in manifest.items()
             for theme in shot.get("themes", PAIR)}
    for f in ASSETS.glob("*.png"):
        assert f.stem in owned, f"{f.name} is committed but no shot in shots.toml owns it"
    for f in ASSETS.glob("*.json"):
        assert f.stem in owned, f"{f.name} is committed but no shot in shots.toml owns it"


def test_provenance_allowlist_has_teeth(tmp_path):
    bad = tmp_path / "shots.toml"
    bad.write_text('[shot.sneaky]\nsurface = "map:art"\n', encoding="utf-8")
    with pytest.raises(SystemExit):
        S.load_manifest(bad)


def test_annotations_refused_on_blackbox_surfaces(tmp_path):
    bad = tmp_path / "shots.toml"
    bad.write_text('[shot.x]\nsurface = "form:npc"\n'
                   'annotate = [ { widget = "a.b", label = "1" } ]\n', encoding="utf-8")
    with pytest.raises(SystemExit):
        S.load_manifest(bad)
