"""THE SEAM-WRAP GAP closed (island.py, 2026-08-27) -- world-island can mint across the x-seam.

The overworld is an x-torus: WMWorld.Wrap shifts the whole world in 64u steps mod 1536, block
identity is only ever the wrapped InitialX in [0,24), and a Block[-1]/Block[24] override file is
DEAD -- the engine can never build that lookup key. The judged composed-world design named closing
this gap as the unblock for the (48,-240) pocket (164.7u free radius; the r96+ mint's unwrapped x
range crosses 0, so wrapped labels {22,23,0,..} are unavoidable).

THE FIX SHAPE these tests pin: geometry is built AND verified in CONTINUOUS unwrapped world
coordinates (texgates' world-coord round-trip, sea-plan adjacency-by-key-increment, and the
census centre check all need that frame); the LABEL wraps exactly once, at the deploy stage in
``landmass()`` -- and both install-probing gates (OPEN-OCEAN, MOD-OVERWRITE) probe the WRAPPED
labels, because probing an unwrapped (-1, y) returns []/scans a filename that cannot exist and
passes VACUOUSLY on exactly the seam-side blocks.

Hermetic throughout: tmp game roots, the synthetic sea plane, stubbed stock reads. No install.
"""
from __future__ import annotations

import dataclasses
import math

import pytest

from ff9mapkit.world import island as I
from ff9mapkit.world import mesh as M
from ff9mapkit.world import placement as P
from ff9mapkit.world import rimretile as RR
from ff9mapkit.world.extract import CH_POS

# the same synthetic full-cell sea plane the island tests use
from .test_world_island import _synth_plane  # noqa: F401  (shared fixture helper)

SEAM_CENTER = (8.0, -240.0)          # unwrapped x range [-12, 28] at r=20 -> columns {-1, 0}
SEAM_R = 20.0


def _seam_build():
    return I.build_landmass(center=SEAM_CENTER, base_radius=SEAM_R, seed=5.0)


# --------------------------------------------------------------------- build + verify (unwrapped)

def test_seam_build_keys_stay_unwrapped_and_locals_in_block_frame():
    """The split keeps CONTINUOUS unwrapped keys (column -1, not 23) and the block-local
    conversion runs against them -- so every local vert sits in the engine's [0,64]x[-64,0]
    frame. Wrapping any earlier than deploy would push seam-side verts 1536u out."""
    built = _seam_build()
    cols = sorted({bx for bx, by in built["blocks"]})
    assert cols[0] < 0 <= cols[-1], f"expected a seam-straddling footprint, got columns {cols}"
    for (bx, by), bm in built["blocks"].items():
        xs = [v[0] for v in bm.chan_arrays[CH_POS]]
        zs = [v[2] for v in bm.chan_arrays[CH_POS]]
        assert min(xs) >= -1e-6 and max(xs) <= 64.0 + 1e-6, (bx, by, min(xs), max(xs))
        assert min(zs) >= -64.0 - 1e-6 and max(zs) <= 1e-6, (bx, by, min(zs), max(zs))


def test_seam_build_verifies_clean_as_one_continuous_landmass():
    """verify_landmass runs on the unwrapped soup: a seam landmass is contiguous ONLY in that
    frame, so cracks/once-edges at the 0|{-1} boundary are ordinary block-border welds."""
    built = _seam_build()
    rep = I.verify_landmass(built, sea_plane=_synth_plane())
    assert rep["clean"], rep


def test_grid_gate_still_refuses_off_rows():
    """Rows stay EDGED (the 2026-07-21 dunes incident): z wraps engine-side too, but edged-z is
    kit policy, and an override on row >= 20 is a dead file with a vacuously-clean census."""
    with pytest.raises(ValueError, match="rows"):
        I.build_landmass(center=(224.0, -1276.0), base_radius=20.0, seed=5.0)


def test_label_collision_refuses(monkeypatch):
    """Two distinct unwrapped columns landing on ONE wrapped label = a footprint spanning the
    whole 1536u world -- refused before any BlockMesh is built (one Terrain mesh per cell is an
    engine invariant). The gate fires straight off the split, so synthetic keys suffice."""
    monkeypatch.setattr(I, "_split_at_borders",
                        lambda parent: {(-1, 3): [], (23, 3): [], (0, 3): []})
    with pytest.raises(ValueError, match="wraps onto itself"):
        I.build_landmass(center=SEAM_CENTER, base_radius=SEAM_R, seed=5.0)


# --------------------------------------------------------------------- the deploy-stage wrap

def _stub_env(monkeypatch, tmp_path, captured=None):
    monkeypatch.setattr(I, "_sea_plane", lambda disc=1, game=None: _synth_plane())
    monkeypatch.setattr(I, "_real_block_parts", lambda blk, **k: {})
    if captured is not None:
        monkeypatch.setattr(M, "deploy_override",
                            lambda bm, **k: captured.append(("mesh", bm.name, bm.x, bm.y)))
        monkeypatch.setattr(M, "deploy_donor_sidecar",
                            lambda dx, dy, *, x, y, **k: captured.append(("donor", None, x, y)))


def test_deploy_writes_only_wrapped_labels(tmp_path, monkeypatch):
    """Every written identity -- Terrain, the Sea4 cut, the hidden parts, the Donor sidecar --
    carries a wrapped column in [0,24). An unwrapped -1 label would be a DEAD file the engine
    never probes: the mint would 'succeed' and half the island would not exist in-game."""
    captured = []
    _stub_env(monkeypatch, tmp_path, captured)
    I.landmass("MOD", center=SEAM_CENTER, base_radius=SEAM_R, seed=5.0, flat=True,
               game=tmp_path, coastnav=False, skip_mirror=True)
    assert captured, "nothing deployed -- vacuous"
    cols = sorted({x for _, _, x, _ in captured})
    assert all(0 <= x < M.GRID_COLS for x in cols), cols
    assert 23 in cols and 0 in cols, f"expected the seam pair, got {cols}"
    for kind, name, x, y in captured:
        if name is not None:
            assert f"Block[{x}][{y}]" in name, (name, x, y)


def test_wrap_is_a_pure_relabel_of_identical_bytes():
    """.ff9mesh bytes carry no identity (version/vcount/flags header only), so the deploy-stage
    relabel must be byte-neutral -- this is what makes wrap-at-deploy safe at all. If identity
    ever leaks into the serialization, this fails and the whole fix shape must be rethought."""
    built = _seam_build()
    (bx, by), bm = sorted(built["blocks"].items())[0]
    assert bx < 0
    wbx = M.wrap_block_col(bx)
    relabeled = dataclasses.replace(bm, x=wbx, name=f"Block[{wbx}][{by}] Terrain")
    assert M.ff9mesh_bytes(bm) == M.ff9mesh_bytes(relabeled)


def test_open_ocean_gate_probes_wrapped_labels(tmp_path, monkeypatch):
    """The stock-occupancy law must see the WRAPPED label: real-map data lives under (23, y),
    and probing the unwrapped (-1, y) returns {} -- a vacuous pass on exactly the seam blocks."""
    monkeypatch.setattr(I, "_sea_plane", lambda disc=1, game=None: _synth_plane())
    seen = []

    def fake_parts(blk, **k):
        seen.append(blk)
        return {"sea3": 2} if blk == (23, 3) else {}

    monkeypatch.setattr(I, "_real_block_parts", fake_parts)
    with pytest.raises(ValueError, match="REAL world block"):
        I.landmass("MOD", center=SEAM_CENTER, base_radius=SEAM_R, seed=5.0, flat=True,
                   game=tmp_path, coastnav=False, skip_mirror=True)
    assert seen and all(0 <= bx < M.GRID_COLS for bx, by in seen), seen


def test_mod_overwrite_gate_sees_wrapped_labels(tmp_path, monkeypatch):
    """A prior deploy at wrapped (23, 3) must refuse the seam mint even though the mint's own
    key for that block is (-1, 3) -- scanning the unwrapped filename cannot ever hit."""
    _stub_env(monkeypatch, tmp_path)
    d = tmp_path / "MOD" / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / "r3"
    d.mkdir(parents=True)
    (d / "Block[23][3] Terrain.ff9mesh").write_bytes(b"PRIOR-DEPLOY")
    with pytest.raises(ValueError, match="already holds"):
        I.landmass("MOD", center=SEAM_CENTER, base_radius=SEAM_R, seed=5.0, flat=True,
                   game=tmp_path, coastnav=False, skip_mirror=True)


def test_center_canonicalizes_mod_world_width(tmp_path, monkeypatch):
    """cx and cx+1536 name the SAME site but the relief/mains phase runs over unwrapped coords --
    without canonicalization the two spellings mint DIFFERENT terrain and a summary re-run is
    unreproducible. Dry-run summaries must be identical."""
    _stub_env(monkeypatch, tmp_path)
    a = I.landmass("MOD", center=SEAM_CENTER, base_radius=SEAM_R, seed=5.0, flat=True,
                   game=tmp_path, dry_run=True, coastnav=False)
    b = I.landmass("MOD", center=(SEAM_CENTER[0] + 24 * 64.0, SEAM_CENTER[1]),
                   base_radius=SEAM_R, seed=5.0, flat=True,
                   game=tmp_path, dry_run=True, coastnav=False)
    assert a["center"] == b["center"] == list(SEAM_CENTER)
    assert a["blocks"] == b["blocks"]
    assert a["report"]["clean"] and b["report"]["clean"]


# --------------------------------------------------------------------- the dual-frame helpers

def test_cut_plane_dual_frame():
    """The cut-cell arithmetic needs the UNWRAPPED column (it must land in the same continuous
    frame as the beach's sea4_cut cells); the returned identity carries the wrapped label."""
    sea = _synth_plane()
    cut = I._cut_plane(sea, -1, 3, frozenset(), None, label_x=23)
    assert cut.x == 23 and cut.name == "Block[23][3] Sea4"
    default = I._cut_plane(sea, 5, 3, frozenset(), None)
    assert default.x == 5 and default.name == "Block[5][3] Sea4"


def test_part_blockmesh_dual_frame():
    pm = I._part_blockmesh("Sea1", (-1, 3), [], 1, label_x=23)
    assert pm.x == 23 and pm.name == "Block[23][3] Sea1"
    pm2 = I._part_blockmesh("Sea1", (5, 3), [], 1)
    assert pm2.x == 5 and pm2.name == "Block[5][3] Sea1"


# --------------------------------------------------------------------- the instruments

def test_water_shrine_check_wraps_the_column():
    """Number arithmetic is defined on the wrapped label. Unwrapped seam keys like (27,8) or
    (-21,10) satisfy by*24+bx == 219 and would abort a lawful census as 'the Water Shrine'."""
    def bm_at(x, y):
        return dataclasses.replace(_synth_plane(), x=x, y=y, name=f"Block[{x}][{y}] Terrain")

    P.check_order_exceptions([("Terrain", bm_at(27, 8))])          # 8*24+27 == 219 unwrapped
    P.check_order_exceptions([("Terrain", bm_at(-21, 10))])        # 10*24-21 == 219 unwrapped
    with pytest.raises(ValueError, match="Water Shrine"):
        P.check_order_exceptions([("Terrain", bm_at(3, 9))])       # the real shrine


def test_coastnav_toroidal_delta():
    """_tdx is the engine's own ff9.PosDiff shape: shortest signed delta mod 1536. A plain
    difference across the seam reads ~1534u where the engine walks 2u."""
    from ff9mapkit.world.coastnav import _tdx
    assert _tdx(1535.0, 1.0) == -2.0
    assert _tdx(1.0, 1535.0) == 2.0
    assert _tdx(100.0, 40.0) == 60.0
    assert abs(_tdx(768.0, 0.0)) == 768.0                          # the antipode is unambiguous


def test_rimretile_refuses_a_seam_spanning_cell_set():
    with pytest.raises(ValueError, match="wrapped column seam 23"):
        RR.plan_rim({(23, 5): {}, (0, 5): {}})


def test_interior_read_refuses_a_seam_window(tmp_path, monkeypatch):
    from ff9mapkit import config
    from ff9mapkit.world import interior as IN
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    with pytest.raises(ValueError, match="x-seam"):
        IN.read_deployed_blocks("MOD", near=(8.0, -240.0), reach=96.0)
