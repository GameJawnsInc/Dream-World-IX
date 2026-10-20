"""THE SEAM-WRAP GAP closed (island.py, 2026-08-27) -- world-island can mint across the x-seam;
the interior relief verbs (world-forest / world-mountain / world-hill) read and write across it
too (interior.py, 2026-10-20) -- see the section at the bottom.

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


# --------------------------------------------------------------------- the interior relief verbs
# world-forest / world-mountain / world-hill (and their world-fuse rows) read a DEPLOYED island
# through interior.read_deployed_blocks, so the same fix shape applies: unwrapped columns in the
# soup, the wrapped label once, at the write seam. Until 2026-10-20 the read refused any window
# that crossed x = 0/1536, so the live world-river island (cells 23/0/1) could not be dressed.
#
# THE FIXTURE: one island minted OFF the seam (columns 3-4), then moved whole RELIEF_SHIFT columns
# west so it straddles x = 0. A BlockMesh is block-local, so the move changes no float -- every
# world coordinate shifts by exactly -256u. The seam copy IS the off-seam island, which lets each
# test compare the seam path against the plain one, byte for byte.

RELIEF_MINT = dict(center=(256.0, -128.0), base_radius=46.0, seed=5.0)    # blocks (3|4, 1|2)
RELIEF_SHIFT = 4                                                           # -> columns -1|0 = 23|0
SEAM_NEAR = (RELIEF_MINT["center"][0] - 64.0 * RELIEF_SHIFT, RELIEF_MINT["center"][1])  # (0, -128)
HILL = dict(height=3.5, radius=14.0)


def _quiet(*a, **k):
    pass


@pytest.fixture(scope="module")
def relief_island():
    return I.build_landmass(**RELIEF_MINT)["blocks"]


def _deploy_tree(game_root, folder, blocks, *, shift=0):
    """Write ``blocks`` as deployed Terrain overrides, ``shift`` columns west, under their WRAPPED
    labels -- what world-island leaves in a mod tree for a seam mint."""
    root = game_root / folder / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
    for (bx, by), bm in blocks.items():
        wbx = M.wrap_block_col(bx - shift)
        M.write_ff9mesh(bm, root / f"r{by}" / f"Block[{wbx}][{by}] Terrain.ff9mesh")


def _plain_and_seam(tmp_path, relief_island):
    """(plain read, seam read) of the one island: the off-seam deploy and the moved copy."""
    from ff9mapkit.world import interior as IN
    _deploy_tree(tmp_path, "PLAIN", relief_island)
    _deploy_tree(tmp_path, "MOD", relief_island, shift=RELIEF_SHIFT)
    plain = IN.read_deployed_blocks("PLAIN", near=RELIEF_MINT["center"], reach=96.0, game=tmp_path)
    seam = IN.read_deployed_blocks("MOD", near=SEAM_NEAR, reach=96.0, game=tmp_path)
    return plain, seam


def _seam_soup_problems(soup, plain_soup) -> list:
    """Why ``soup`` is NOT the plain island moved RELIEF_SHIFT columns west, whole, in one frame
    (empty = it is). Positions must match the plain soup's shifted by exactly -256u (no tri
    missing, none 1536u away), and no once-edge may lie on the seam line: the two sides of x = 0
    weld there exactly as the plain island welds across x = 256."""
    from collections import Counter
    from ff9mapkit.world import interior as IN
    probs = []
    dx = 64.0 * RELIEF_SHIFT
    want = sorted(IN.kk3((p[0] - dx, p[1], p[2])) for p in plain_soup["pos"])
    got = sorted(IN.kk3(p) for p in soup["pos"])
    if got != want:
        probs.append(f"positions: {len(got)} read, {len(want)} expected")
    xs = [p[0] for p in soup["pos"]]
    if xs and max(xs) - min(xs) > 3 * 64.0:
        probs.append(f"x extent {min(xs):.0f}..{max(xs):.0f}: two clumps")
    eu = Counter()
    for t in soup["tris"]:
        ks = [IN.kk3(soup["pos"][i]) for i in t]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            eu[tuple(sorted((ks[a], ks[b])))] += 1
    on_seam = [e for e, n in eu.items() if n == 1
               and all(min(abs(p[0]), abs(p[0] - 1536.0)) < 1e-3 for p in e)]
    if on_seam:
        probs.append(f"{len(on_seam)} once-edges on the seam line")
    return probs


def test_interior_read_keeps_unwrapped_keys_and_reads_wrapped_files(tmp_path, relief_island):
    """The window probes UNWRAPPED columns (-1 and 0) but each reads its WRAPPED label's file
    (Block[23][y] -- a Block[-1] file cannot exist); key and BlockMesh identity stay unwrapped,
    and the bytes are the deployed bytes."""
    plain, seam = _plain_and_seam(tmp_path, relief_island)
    assert sorted(seam) == sorted((bx - RELIEF_SHIFT, by) for bx, by in plain)
    assert {bx for bx, _ in seam} == {-1, 0}
    for (bx, by), bm in seam.items():
        assert (bm.x, bm.y) == (bx, by), "identity must stay on the unwrapped key until the write"
        assert M.ff9mesh_bytes(bm) == M.ff9mesh_bytes(plain[(bx + RELIEF_SHIFT, by)])


def test_seam_soup_comes_back_whole_in_one_contiguous_frame(tmp_path, relief_island, monkeypatch):
    """THE BREAK-IT. A soup straddling the seam must come back WHOLE and in ONE frame: the plain
    island moved -256u, every position present, the two sides welded across x = 0. Both pre-fix
    defects fail the same check -- so the check can fail."""
    from ff9mapkit.world import interior as IN
    plain, seam = _plain_and_seam(tmp_path, relief_island)
    plain_soup = IN.soup_from_blocks(plain)
    assert _seam_soup_problems(IN.soup_from_blocks(seam), plain_soup) == []

    # broken 1: world coords from the WRAPPED labels (labels*64) -> two clumps 1536u apart
    by_label = {(M.wrap_block_col(bx), by): bm for (bx, by), bm in seam.items()}
    probs = _seam_soup_problems(IN.soup_from_blocks(by_label), plain_soup)
    assert any("two clumps" in p for p in probs) and any("once-edges" in p for p in probs), probs

    # broken 2: the old LINEAR probe (no wrap) -> Block[-1][y] does not exist -> read back PARTIAL
    monkeypatch.setattr(M, "wrap_block_col", lambda bx: bx)
    partial = IN.read_deployed_blocks("MOD", near=SEAM_NEAR, reach=96.0, game=tmp_path)
    assert {bx for bx, _ in partial} == {0}
    assert any("positions" in p for p in _seam_soup_problems(IN.soup_from_blocks(partial), plain_soup))


def test_hill_across_the_seam_is_the_plain_hill_moved_and_writes_wrapped_labels(tmp_path, relief_island,
                                                                                monkeypatch):
    """The whole world-hill path on the seam: carve, census, deploy, read back. The carve is the
    plain island's carve moved -256u, byte for byte per block (the hill reads only coordinate
    DIFFERENCES, and the shift is exact); the deploy lands every block at its WRAPPED label; and
    the re-read is the plain carve's deploy, moved."""
    from ff9mapkit.world import interior as IN
    from .test_world_island import _synth_plane as synth
    plain, seam = _plain_and_seam(tmp_path, relief_island)
    h_plain = IN.build_hill(IN.soup_from_blocks(plain), center=RELIEF_MINT["center"], **HILL, log=_quiet)
    h_seam = IN.build_hill(IN.soup_from_blocks(seam), center=SEAM_NEAR, **HILL, log=_quiet)
    assert {bx for bx, _ in h_seam["changed"]} == {-1, 0}, "the hill must span the seam"
    assert sorted(h_seam["changed"]) == sorted((bx - RELIEF_SHIFT, by) for bx, by in h_plain["changed"])
    assert h_seam["report"] == h_plain["report"]
    for (bx, by), bm in h_plain["changed"].items():
        assert M.ff9mesh_bytes(h_seam["changed"][(bx - RELIEF_SHIFT, by)]) == M.ff9mesh_bytes(bm), (bx, by)

    monkeypatch.setattr(I, "_sea_plane", lambda disc=1, game=None: synth())
    IN.census_gate(h_seam["changed"], baseline=seam, log=_quiet)

    written = IN.deploy_changed(h_seam["changed"], mod_folder="MOD", game=tmp_path, skip_mirror=True,
                                log=_quiet)
    assert sorted(p.name for p in written) == sorted(
        f"Block[{M.wrap_block_col(bx)}][{by}] Terrain.ff9mesh" for bx, by in h_seam["changed"])
    assert not list((tmp_path / "MOD").rglob("Block[-*")), "a Block[-1] file is DEAD in game"
    back = IN.read_deployed_blocks("MOD", near=SEAM_NEAR, reach=96.0, game=tmp_path)
    for (bx, by), bm in h_plain["changed"].items():
        assert M.ff9mesh_bytes(back[(bx - RELIEF_SHIFT, by)]) == M.ff9mesh_bytes(bm), (bx, by)
    # and a second deploy of the same carve converges: nothing's bytes change, nothing is written
    assert IN.deploy_changed(h_seam["changed"], mod_folder="MOD", game=tmp_path, skip_mirror=True,
                             log=_quiet) == []


def test_untouched_seam_read_assembles_back_to_the_deployed_bytes(tmp_path, relief_island):
    """read -> soup -> re-emit with nothing dropped is the identity across the seam: the soup's
    unwrapped frame round-trips every kept tri byte-exact into its wrapped file."""
    from ff9mapkit.world import interior as IN
    _, seam = _plain_and_seam(tmp_path, relief_island)
    same = IN._assemble(IN.soup_from_blocks(seam), set(), {})
    assert IN.deploy_changed(same, mod_folder="MOD", game=tmp_path, skip_mirror=True, log=_quiet) == []


def test_mountain_parts_name_probe_and_write_wrapped_labels(tmp_path, monkeypatch):
    """world-mountain's ensemble writer: the span keys are the soup's unwrapped columns; the
    mod-overwrite probe, every carried or blank part, and the Donor.txt all carry the WRAPPED
    label (an unwrapped one is a dead file, or a vacuous probe)."""
    from pathlib import Path
    from ff9mapkit.world import interior as IN
    captured, probed = [], []
    monkeypatch.setattr(M, "existing_overrides", lambda cells, *a, **k: probed.extend(cells) or [])
    monkeypatch.setattr(M, "deploy_override",
                        lambda bm, *, part, **k: captured.append((part, bm.name, bm.x, bm.y)) or Path("x"))
    monkeypatch.setattr(M, "deploy_donor_sidecar",
                        lambda dx, dy, *, x, y, **k: captured.append(("Donor", None, x, y)) or Path("x"))
    obj = dataclasses.replace(_synth_plane(), x=-1, y=1, name="Block[-1][1] Object")
    res = {"donor_ref": (12, 10), "report": {"blocks": [[-1, 1], [0, 1]]},
           "changed_parts": {(-1, 1): {"Object": obj}}}
    IN.deploy_mountain_parts(res, mod_folder="MOD", game=tmp_path, skip_mirror=True, log=_quiet)
    assert probed == [(23, 1), (0, 1)]
    assert sorted({(x, y) for _, _, x, y in captured}) == [(0, 1), (23, 1)]
    for part, name, x, y in captured:
        if name is not None:
            assert name == f"Block[{x}][{y}] {part}", (part, name, x, y)
    assert ("Object", "Block[23][1] Object", 23, 1) in captured        # the carried part, relabeled
    assert len(captured) == 2 * (len(IN.ENSEMBLE_PARTS) + 1)


def test_relief_writer_refuses_two_columns_on_one_wrapped_cell(tmp_path):
    """One Terrain mesh per wrapped cell (the island lane's wraps-onto-itself invariant), at the
    write seam: unwrapped -1 and 23 are the same file."""
    from ff9mapkit.world import interior as IN
    bm = _synth_plane()
    with pytest.raises(ValueError, match="wrapped cell"):
        IN.deploy_changed({(-1, 3): dataclasses.replace(bm, x=-1, y=3),
                           (23, 3): dataclasses.replace(bm, x=23, y=3)},
                          mod_folder="MOD", game=tmp_path, skip_mirror=True, log=_quiet)
    assert not (tmp_path / "MOD").exists()


def test_relief_read_refuses_a_window_wider_than_the_world(tmp_path):
    from ff9mapkit.world import interior as IN
    with pytest.raises(ValueError, match="whole 24-column world"):
        IN.read_deployed_blocks("MOD", near=(8.0, -240.0), reach=800.0, game=tmp_path)


def test_relief_cli_prints_the_wrapped_centre(monkeypatch, capsys):
    """A seam carve's centre is in the soup's frame (x may be < 0); the line the operator teleports
    by and copies into a recipe names the same place inside the world window."""
    from ff9mapkit import cli
    from ff9mapkit.world import interior as IN
    monkeypatch.setattr(IN, "read_deployed_blocks", lambda *a, **k: {})
    monkeypatch.setattr(IN, "soup_from_blocks", lambda blocks: object())
    monkeypatch.setattr(IN, "census_gate", lambda *a, **k: None)
    monkeypatch.setattr(IN, "build_hill", lambda soup, **kw: {
        "center": (-6.0, -128.0), "changed": {},
        "report": {"displaced_tris": 98, "worst_flank": 24.0, "peak_y": 6.7}})
    args = cli.build_parser().parse_args(["world-hill", "--mod-folder", "m", "--near", "0,-128", "--dry-run"])
    assert cli._cmd_world_hill(args) == 0
    assert "a grass hill at world (1530,-128)" in capsys.readouterr().out
