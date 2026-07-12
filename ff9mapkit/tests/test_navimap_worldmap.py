"""The world-map image compositor (world-minimap) -- game-gated like the other
world proofs (it reads the active map image + the deployed meshes)."""
import pytest


def _game_ready() -> bool:
    from ff9mapkit import config
    try:
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")


def test_projection_puts_anchors_and_probes_where_they_belong():
    """The engine projection (1536x1280 -> the detected art rect): every one of
    the 49 real town anchors lands INSIDE the art rect, and the world's corners
    map to the rect's corners."""
    from ff9mapkit.world.navimap import (WORLD_MAP_EXTENT, _detect_art_rect,
                                         _land_anchors, _load_active_world_map)
    im, _src = _load_active_world_map(None)
    x0, y0, x1, y1 = _detect_art_rect(im)
    assert x1 - x0 > im.width * 0.8 and y1 - y0 > im.height * 0.8
    ex, ez = WORLD_MAP_EXTENT
    assert (ex, ez) == (1536.0, 1280.0)          # w_naviGetPos, engine-pinned
    for wx, wz in _land_anchors():
        px = x0 + (wx / ex) * (x1 - x0)
        py = y0 + ((-wz) / ez) * (y1 - y0)
        assert x0 <= px <= x1 and y0 <= py <= y1
    assert len(_land_anchors()) == 49


def test_composite_dry_run_reports_the_deployed_land():
    """A dry run over the deployed overworld folder reads every Terrain block and
    reports a sane plan without writing."""
    from pathlib import Path
    from ff9mapkit import config
    from ff9mapkit.world.navimap import MAP_SPRITE_REL, composite_world_map
    gp = config.find_game_path(None)
    if not (gp / "FF9CustomMap-world" / "FF9_Data/WorldMap").is_dir():
        pytest.skip("no deployed overworld folder on this machine")
    s = composite_world_map("FF9CustomMap-world", dry_run=True, verbose=False)
    assert s["dry_run"] and s["blocks"] >= 1 and s["tris"] > 100
    assert s["out"].endswith("world_map_full_all.png")
    # the base must never be the folder's own override (no self-compositing)
    assert not s["source"].startswith(str(gp / "FF9CustomMap-world"))
