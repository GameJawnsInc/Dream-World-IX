"""Import spawn placement: keep a forked field's spawn OFF every trigger zone.

A real field's stored charPos is usually right at the MAIN door -- the exit that warps you back out --
so a naive spawn lands inside that gateway and instant-warps the moment you arrive (the empty-screen
"got gatewayed to the next zone" symptom). The fix: the spawn cascade rejects any point inside a
SetRegion trigger quad. The geometry helpers are pure (tested here); the full extract_field cascade
needs the game install (a guarded fork test asserts the chosen spawn clears every zone)."""
from __future__ import annotations

from pathlib import Path

import pytest

from ff9mapkit import eventscan, extract

FIX = Path(__file__).parent / "fixtures"
ALEX = (FIX / "alex100-us.eb.bytes").read_bytes()


# --- pure geometry ------------------------------------------------------------------------
def test_pt_in_quad():
    q = [[0, 0], [100, 0], [100, 100], [0, 100]]
    assert extract._pt_in_quad(50, 50, q)            # interior
    assert extract._pt_in_quad(0, 0, q)              # corner (inclusive)
    assert extract._pt_in_quad(100, 50, q)           # edge
    assert not extract._pt_in_quad(150, 50, q)       # right of it
    assert not extract._pt_in_quad(-1, 50, q)        # left of it
    assert not extract._pt_in_quad(50, 150, q)       # above it
    assert not extract._pt_in_quad(50, 50, [[0, 0], [1, 0]])   # degenerate (< 3 corners)


def test_scan_region_zones_recovers_trigger_quads():
    zones = eventscan.scan_region_zones(ALEX)
    assert zones                                     # field 100 has exit/door regions
    door = [[-700, 2200], [200, 2200], [200, 3400], [-700, 3400]]   # the injected Alexandria door
    assert any({tuple(p) for p in z} == {tuple(p) for p in door} for z in zones)
    assert any(extract._pt_in_quad(-250, 2800, z) for z in zones)   # a point inside that door is caught


# --- the cascade (full extract_field needs the game install) ------------------------------
def _game_ready():
    try:
        import UnityPy  # noqa: F401
        from ff9mapkit import config
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_forked_spawn_clears_every_trigger_zone(tmp_path):
    # GTRE (field 1014) is the field whose charPos sat inside an exit gateway -> instant warp on arrival.
    field = "fbg_n18_gtre_map374_gt_dun_b"
    meta = extract.extract_field(field, tmp_path)
    sx, sz = meta["player_start"]
    zones = eventscan.scan_region_zones(extract.extract_event_script(field))
    assert zones                                                   # the field does have trigger zones
    assert not any(extract._pt_in_quad(sx, sz, z) for z in zones)  # spawn is clear of all of them
