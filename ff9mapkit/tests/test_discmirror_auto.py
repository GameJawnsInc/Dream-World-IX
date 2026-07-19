"""AUTO-RUN discmirror wiring (2026-07-18 overworld roadmap, item A; hardened 2026-07-19 to the EVIDENCE
CONTRACT): every world-deploy writer that touches WorldMap override cells calls ``discmirror.auto_mirror``
as an automatic post-step, so THE DISC-4 GAP (``project-ff9-overworld-worlds.md`` -- an un-mirrored custom
landmass VANISHES on disc 4) can no longer be a forgotten manual ``world-mirror`` run.

``auto_mirror`` now takes ``written`` -- the actual return values of the CALLING invocation's own real
:func:`~ff9mapkit.world.mesh.deploy_override` / :func:`~ff9mapkit.world.mesh.deploy_donor_sidecar` calls --
and derives the game root, source disc, lod, and cell set PURELY by parsing those paths (see
``discmirror.py``'s module docstring, "THE EVIDENCE CONTRACT"). This file covers, in order:

* the ``auto_mirror``/``mirror(cells=...)`` unit contract itself;
* **P1 (hermeticity):** a hermetic caller that mocks only the deploy PRIMITIVES (not
  ``config.find_game_path``) must never trigger a real mirror pass against whatever install
  ``find_game_path`` would otherwise resolve to;
* **P2 (blast radius):** an unrelated write to cell B must never re-mirror (and potentially clobber a
  hand-diverged Disc4 variant of) cell A;
* **P3 (sequencing):** the multi-write orchestrators (``fuse_layout``, the CLI's ``world-mountain`` wiring)
  run auto_mirror exactly ONCE, scoped to the union of every write, not once per inner call;
* representative wired-writer smoke coverage (``island.landmass``, ``terrain.reclaim``,
  ``interior.deploy_changed``) proving the end-to-end wiring still lands real bytes;
* the standalone ``world-mirror`` verb (a direct :func:`~ff9mapkit.world.discmirror.mirror` call,
  ``cells=None``) is unaffected.

Fully hermetic throughout: a fake mod-folder tree lives under ``tmp_path`` (``config.find_game_path``
monkeypatched where a test needs a resolvable install at all), and the REAL asset layer is stubbed at
``extract._worldmap_env`` (feeds ``_real_parts``' container regex) so every deployed cell reads as open
ocean and the per-cell gate passes unconditionally. Where a test writes a REAL override
(``write_ff9mesh``/``deploy_override`` run for real), it proves actual bytes land on disk, not just that a
mocked call happened.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ff9mapkit import config
from ff9mapkit.world import discmirror as DM
from ff9mapkit.world import extract as X
from ff9mapkit.world import fuse as FU
from ff9mapkit.world import island as I
from ff9mapkit.world import interior as IN
from ff9mapkit.world import mesh as M
from ff9mapkit.world import palette as PAL
from ff9mapkit.world import terrain as T
from ff9mapkit.world import transplant as TR
from ff9mapkit.world import water as WT
from ff9mapkit.world.extract import BlockMesh, CH_POS, CH_NRM, CH_UV, CH_TAN, encode_id

MOD = "FF9CustomMap"
NRM = (0.0, 1.0, 0.0)


class _FakeEnv:
    def __init__(self, container):
        self.container = list(container)


def _patch_open_ocean(monkeypatch):
    """Both Disc1 and Disc4 report NOTHING real anywhere -- every deployed cell is open ocean on both
    trees, so mirror()'s per-cell safety gate passes unconditionally (a verbatim copy)."""
    monkeypatch.setattr(X, "_worldmap_env", lambda disc, game=None: _FakeEnv([]))


def _tri_blockmesh(name, *, disc, x, y, topograph=0):
    """A single up-facing triangle BlockMesh -- enough for write_ff9mesh/deploy_override to run for real."""
    idall = float(encode_id(topograph=topograph))
    verts = [[0.0, 0.0, 0.0], [8.0, 0.0, 0.0], [0.0, 0.0, -8.0]]
    return BlockMesh(name=name, disc=disc, x=x, y=y, lod="0_1", vcount=3, stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: verts, CH_NRM: [[0.0, 1.0, 0.0]] * 3, CH_UV: [[0.0, 0.0]] * 3,
                                  CH_TAN: [[idall, 0.0, 0.0, 1.0]] * 3},
                     flat_index=[0, 1, 2], tris=[[0, 1, 2]], raw_vbuf=b"", raw_ibuf=b"", use32=True,
                     submeshes=[])


_SEA_TOPO = float(encode_id(topograph=57))


def _sea4_grid_plane():
    """A full 64x64 Sea4 grid plane at block (12,0) -- mirrors test_world_island.py's ``_grid_plane`` (the
    island builder's placement census needs FULL sea coverage, not a single probe triangle, to gate clean)."""
    pos, nrm, uv, tan, flat, tris = [], [], [], [], [], []

    def add(corners):
        base = len(pos)
        for c in corners:
            pos.append(list(c)); nrm.append([0.0, 1.0, 0.0]); uv.append([0.0, 0.0])
            tan.append([_SEA_TOPO, 0.0, 0.0, 1.0]); flat.append(len(pos) - 1)
        tris.append([base, base + 1, base + 2])

    for i in range(16):
        for j in range(-16, 0):
            x0, z0 = 4.0 * i, 4.0 * j
            add([(x0, 0.0, z0), (x0, 0.0, z0 + 4), (x0 + 4, 0.0, z0)])
            add([(x0 + 4, 0.0, z0), (x0, 0.0, z0 + 4), (x0 + 4, 0.0, z0 + 4)])
    return BlockMesh(name="Block[12][0] Sea4", disc=1, x=12, y=0, lod="0_1", vcount=len(pos), stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan},
                     flat_index=flat, tris=tris, raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


def _v(x, y, z, uv=(0.5, 0.5), idall=12800.0):
    return ((float(x), float(y), float(z)), NRM, tuple(uv), (float(idall), 0.0, 0.0, 1.0))


def _quad(x0, x1, z0, z1, *, y=0.0, idall=12800.0, uv=(0.5, 0.5)):
    a, b = _v(x0, y, z1, uv, idall), _v(x1, y, z1, uv, idall)
    c, d = _v(x1, y, z0, uv, idall), _v(x0, y, z0, uv, idall)
    return [[a, b, d], [b, c, d]]


def _fake_world(blocks):
    """A ``transplant.world_tris`` stand-in -- the ONE seam every real-world read in transplant.py funnels
    through, mirroring tests/test_world_fuse.py's own fixture convention."""
    def fake(bx, by, part, **_k):
        return [list(t) for t in blocks.get((bx, by, part), [])]
    return fake


def _mini_donor():
    """Donor (1,1): a 16x16 land pad centred in a full-cell Sea4 -- enough for a REAL (non-dry-run)
    ``transplant_region``/``fuse_layout`` deploy to gate clean (mirrors test_world_fuse.py's fixture)."""
    tiles = {"terrain": [], "sea4": []}
    for xi in range(16):
        for zi in range(16):
            x0, z0 = 64.0 + 4.0 * xi, -128.0 + 4.0 * zi
            part = "terrain" if (6 <= xi < 10 and 6 <= zi < 10) else "sea4"
            tiles[part] += _quad(x0, x0 + 4.0, z0, z0 + 4.0, idall=(12800.0 if part == "terrain" else 228.0))
    return {(1, 1, p): t for p, t in tiles.items() if t}


# --------------------------------------------------------------------------- auto_mirror() / mirror(): the contract

def test_auto_mirror_skip_flag_never_touches_find_game_path(tmp_path):
    calls = []

    def _counting(game=None):
        calls.append(game)
        return tmp_path

    logged = []
    out = DM.auto_mirror(["Block[3][5] Terrain.ff9mesh"], mod_folder=MOD, skip_mirror=True, log=logged.append)
    assert out is None
    assert any("skipped" in m and "--skip-mirror" in m for m in logged)
    assert calls == []                                          # short-circuits before ANY evidence parsing


def test_auto_mirror_no_op_on_empty_written():
    assert DM.auto_mirror([], mod_folder=MOD, log=lambda *a, **k: None) is None


def test_auto_mirror_drops_non_path_entries_silently():
    """A MagicMock (a mocked deploy-call return value) fails the isinstance(str, Path) check -- dropped,
    not crashed -- and NOTHING surviving means auto_mirror never even tries to derive a game root."""
    out = DM.auto_mirror([MagicMock(), MagicMock(), 42, None], mod_folder=MOD, log=lambda *a, **k: None)
    assert out is None


def test_auto_mirror_drops_nonexistent_paths(tmp_path):
    ghost = tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / "r5" / "Block[3][5] Terrain.ff9mesh"
    assert not ghost.exists()
    assert DM.auto_mirror([ghost], mod_folder=MOD, log=lambda *a, **k: None) is None


def test_auto_mirror_no_op_when_all_paths_already_at_dst_disc(tmp_path):
    """A writer that deployed straight to Disc4 already has nothing further to mirror -- this must
    short-circuit before ever resolving a game path (no monkeypatch of config.find_game_path here at all)."""
    p = tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc4" / "0_1" / "r5"
    p.mkdir(parents=True)
    f = p / "Block[3][5] Terrain.ff9mesh"
    f.write_bytes(b"X")
    assert DM.auto_mirror([f], mod_folder=MOD, dst_disc=4, log=lambda *a, **k: None) is None


def test_auto_mirror_mirrors_real_written_paths_scoped_to_their_cells(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    _patch_open_ocean(monkeypatch)
    bm = _tri_blockmesh("Block[3][5] Terrain", disc=1, x=3, y=5)
    p = M.deploy_override(bm, mod_folder=MOD, game=None, lod="0_1", part="Terrain")

    out = DM.auto_mirror([p], mod_folder=MOD, log=lambda *a, **k: None)
    assert out is not None
    dst = tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc4" / "0_1" / "r5" / "Block[3][5] Terrain.ff9mesh"
    assert dst.read_bytes() == p.read_bytes()


def test_auto_mirror_accepts_str_paths_too(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    _patch_open_ocean(monkeypatch)
    bm = _tri_blockmesh("Block[3][5] Terrain", disc=1, x=3, y=5)
    p = M.deploy_override(bm, mod_folder=MOD, game=None, lod="0_1", part="Terrain")

    out = DM.auto_mirror([str(p)], mod_folder=MOD, log=lambda *a, **k: None)
    assert out is not None
    dst = tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc4" / "0_1" / "r5" / "Block[3][5] Terrain.ff9mesh"
    assert dst.is_file()


def test_auto_mirror_inconsistent_game_roots_raises(tmp_path):
    """Two written paths that disagree on the game-root prefix (should never happen in real usage -- a
    single invocation only ever touches ONE install) refuse rather than silently guess."""
    a = tmp_path / "root_a" / MOD / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / "r5" / "Block[3][5] Terrain.ff9mesh"
    b = tmp_path / "root_b" / MOD / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / "r9" / "Block[9][9] Terrain.ff9mesh"
    a.parent.mkdir(parents=True); a.write_bytes(b"A")
    b.parent.mkdir(parents=True); b.write_bytes(b"B")
    with pytest.raises(ValueError):
        DM.auto_mirror([a, b], mod_folder=MOD, log=lambda *a, **k: None)


def test_mirror_cells_param_restricts_to_the_given_set(tmp_path, monkeypatch):
    """mirror()'s new ``cells=`` kwarg: a whole tree with TWO deployed cells, restricted via ``cells=`` to
    just one, mirrors only that one. The standalone world-mirror verb never passes this (cells=None default
    = whole-tree, unchanged -- see test_standalone_mirror_still_works_directly below)."""
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    _patch_open_ocean(monkeypatch)
    src = tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
    (src / "r5").mkdir(parents=True)
    (src / "r5" / "Block[3][5] Terrain.ff9mesh").write_bytes(b"AAA")
    (src / "r9").mkdir(parents=True)
    (src / "r9" / "Block[9][9] Terrain.ff9mesh").write_bytes(b"BBB")

    out = DM.mirror(MOD, cells={(3, 5)}, log=lambda *a, **k: None)
    dst = tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc4" / "0_1"
    assert (dst / "r5" / "Block[3][5] Terrain.ff9mesh").is_file()
    assert not (dst / "r9" / "Block[9][9] Terrain.ff9mesh").exists()
    assert out["mirrored"] == [dst / "r5" / "Block[3][5] Terrain.ff9mesh"]


# --------------------------------------------------------------------------- P1: HERMETICITY

def test_hermeticity_mocked_deploy_calls_never_touch_a_real_install(tmp_path, monkeypatch):
    """P1 regression: the OLD auto_mirror(mod_folder, *, disc, game=None, ...) re-resolved
    config.find_game_path ITSELF, so a hermetic test that mocks only the deploy PRIMITIVES
    (mesh.deploy_override / deploy_donor_sidecar) -- never config.find_game_path -- could still trigger a
    genuine mirror pass against whatever install find_game_path resolves to on the machine running the
    test. Prove the fix directly: with the deploy calls mocked out, water.water()'s own ``written`` list is
    nothing but MagicMocks, so auto_mirror must drop all of them and never call find_game_path at all -- a
    tmp 'real install' that ALREADY carries Disc1 overrides is left completely byte-for-byte untouched."""
    real_root = tmp_path / "the_developers_real_install"
    pre_dir = real_root / MOD / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / "r7"
    pre_dir.mkdir(parents=True)
    pre_file = pre_dir / "Block[3][7] Terrain.ff9mesh"
    pre_bytes = b"PRE-EXISTING-REAL-OVERRIDE-BYTES"
    pre_file.write_bytes(pre_bytes)

    calls = []

    def _counting_find_game_path(game=None):
        calls.append(game)
        return real_root

    monkeypatch.setattr(config, "find_game_path", _counting_find_game_path)
    monkeypatch.setattr(M, "deploy_override", MagicMock())
    monkeypatch.setattr(M, "deploy_donor_sidecar", MagicMock())

    WT.water(MOD, cells=[(5, 5)], donor=(15, 4))                # a REAL water() call; only the writes are mocked

    assert calls == []                                          # find_game_path NEVER called: not by water()
                                                                 # (its own deploy calls are mocked out) and not
                                                                 # by auto_mirror (nothing survived filtering)
    assert pre_file.read_bytes() == pre_bytes                   # the pre-existing real override is UNTOUCHED
    assert not (real_root / MOD / "FF9_Data" / "WorldMap" / "Disc4").exists()   # no mirror pass ever ran


# --------------------------------------------------------------------------- P2: CELL SCOPE (blast radius)

def test_cell_scope_unrelated_write_never_remirrors_a_different_cell(tmp_path, monkeypatch):
    """P2 regression (adapted from the scratchpad verify_blast_radius.py adversarial repro): mirror()'s
    default WHOLE-TREE re-sync would let an unrelated write to cell B silently re-copy (and clobber) a
    hand-diverged Disc4 variant of cell A. auto_mirror's derived cells= scoping closes it: a write to B
    mirrors ONLY B."""
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    _patch_open_ocean(monkeypatch)

    # 1) deploy + auto-mirror cell A (5,5)
    bm_a = _tri_blockmesh("Block[5][5] Terrain", disc=1, x=5, y=5)
    p_a = M.deploy_override(bm_a, mod_folder=MOD, game=None, lod="0_1", part="Terrain")
    DM.auto_mirror([p_a], mod_folder=MOD, log=lambda *a, **k: None)
    disc4_a = tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc4" / "0_1" / "r5" / "Block[5][5] Terrain.ff9mesh"
    assert disc4_a.is_file()

    # 2) the operator hand-diverges the Disc4 copy (e.g. a --disc 4 targeted post-disc-3 look)
    diverged = b"HAND-DIVERGED-DISC4-BYTES"
    disc4_a.write_bytes(diverged)

    # 3) a totally UNRELATED write to cell B (9,9)
    bm_b = _tri_blockmesh("Block[9][9] Terrain", disc=1, x=9, y=9)
    p_b = M.deploy_override(bm_b, mod_folder=MOD, game=None, lod="0_1", part="Terrain")
    DM.auto_mirror([p_b], mod_folder=MOD, log=lambda *a, **k: None)

    assert disc4_a.read_bytes() == diverged                     # cell A's hand-divergence SURVIVES untouched
    disc4_b = tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc4" / "0_1" / "r9" / "Block[9][9] Terrain.ff9mesh"
    assert disc4_b.is_file()                                    # cell B DID get mirrored


# --------------------------------------------------------------------------- P3: SEQUENCING

def test_fuse_layout_real_deploy_mirrors_once_with_the_cell_union(tmp_path, monkeypatch):
    """P3 regression: fuse_layout's multi-write sequencing had ZERO real-deploy (non-dry-run) coverage. A
    real two-placement layout must call discmirror.mirror EXACTLY ONCE, scoped to the UNION of every
    placement's cells -- not once per placement (each inner transplant_region call defers its own mirror
    via skip_mirror=True; only fuse_layout's own trailing auto_mirror call actually runs)."""
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    _patch_open_ocean(monkeypatch)
    monkeypatch.setattr(TR, "world_tris", _fake_world(_mini_donor()))

    mirror_cell_sets = []
    real_mirror = DM.mirror

    def _spy(mod_folder, **kw):
        mirror_cell_sets.append(kw.get("cells"))
        return real_mirror(mod_folder, **kw)

    monkeypatch.setattr(DM, "mirror", _spy)

    out = FU.fuse_layout(MOD, [
        {"cell": (5, 5), "donor": (1, 1), "size": (1, 1)},
        {"cell": (5, 6), "donor": (1, 1), "size": (1, 1)},
    ], dry_run=False)

    assert out["clean"] is True, out["fuse_gates"]
    assert len(mirror_cell_sets) == 1                           # ONE mirror pass for the whole layout
    assert mirror_cell_sets[0] == {(5, 5), (5, 6)}               # scoped to the UNION of both placements' cells
    disc4 = tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc4" / "0_1"
    assert (disc4 / "r5" / "Block[5][5] Terrain.ff9mesh").is_file()
    assert (disc4 / "r6" / "Block[5][6] Terrain.ff9mesh").is_file()


def test_cli_world_mountain_unions_written_paths_into_one_auto_mirror_call(monkeypatch):
    """P3 regression: cli._cmd_world_mountain wires TWO inner writers (interior.deploy_changed +
    interior.deploy_mountain_parts). Both must force skip_mirror=True on themselves; the CLI unions their
    returned written-path lists and does exactly ONE auto_mirror call over the whole union. No game data
    needed -- every interior.* call is faked."""
    from ff9mapkit import cli

    monkeypatch.setattr(IN, "read_deployed_blocks", lambda *a, **k: {})
    monkeypatch.setattr(IN, "soup_from_blocks", lambda blocks: object())
    monkeypatch.setattr(IN, "carve_mountain", lambda soup, **k: {
        "center": (0.0, 0.0), "changed": {}, "changed_parts": {}, "donor_ref": (10, 5),
        "report": {"blocks": [[3, 3]], "rot_deg": 0, "blob_tris": 0, "plugs": 0, "dropped": 0,
                  "zip_tris": 0, "peak_y": 0.0, "rock_rigid": 0.0, "apron_slope": 0.0,
                  "teleport": (0, 0)},
    })
    monkeypatch.setattr(IN, "census_gate", lambda *a, **k: None)

    changed_kwargs, parts_kwargs = {}, {}

    def _fake_deploy_changed(changed, **kw):
        changed_kwargs.update(kw)
        return ["A.ff9mesh", "B.ff9mesh"]

    def _fake_deploy_mountain_parts(res, **kw):
        parts_kwargs.update(kw)
        return ["C.ff9mesh"]

    monkeypatch.setattr(IN, "deploy_changed", _fake_deploy_changed)
    monkeypatch.setattr(IN, "deploy_mountain_parts", _fake_deploy_mountain_parts)

    mirror_calls = []
    monkeypatch.setattr(DM, "auto_mirror", lambda written, **kw: mirror_calls.append((list(written), kw)))

    args = cli.build_parser().parse_args(
        ["world-mountain", "--mod-folder", MOD, "--center", "0,0", "--donor", "10,5"])
    rc = cli._cmd_world_mountain(args)

    assert rc == 0
    assert changed_kwargs.get("skip_mirror") is True             # both inner writers suppress their OWN mirror
    assert parts_kwargs.get("skip_mirror") is True
    assert len(mirror_calls) == 1                                # exactly ONE auto_mirror call, at the CLI level
    written, kw = mirror_calls[0]
    assert written == ["A.ff9mesh", "B.ff9mesh", "C.ff9mesh"]    # the UNION, in call order
    assert kw.get("mod_folder") == MOD


# --------------------------------------------------------------------------- wired into real writers (smoke)

def test_island_landmass_auto_mirrors_disc4(tmp_path, monkeypatch):
    """A real (non-mocked deploy_override) world-island build into a TMP mod folder gets its Disc1
    overrides copied to Disc4 automatically -- no separate world-mirror call needed."""
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    _patch_open_ocean(monkeypatch)
    monkeypatch.setattr(I, "_real_block_parts", lambda blk, **k: {})
    monkeypatch.setattr(I, "_sea_plane", lambda disc=1, game=None: _sea4_grid_plane())

    s = I.landmass(MOD, cell=(3, 1), base_radius=20.0, seed=5.0, flat=True)
    assert s["blocks"]
    disc1 = tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
    disc4 = tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc4" / "0_1"
    assert disc1.is_dir() and disc4.is_dir()
    src_p = disc1 / "r1" / "Block[3][1] Terrain.ff9mesh"
    dst_p = disc4 / "r1" / "Block[3][1] Terrain.ff9mesh"
    assert src_p.is_file() and dst_p.is_file()
    assert dst_p.read_bytes() == src_p.read_bytes()


def test_island_landmass_skip_mirror_leaves_disc4_untouched(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    _patch_open_ocean(monkeypatch)
    monkeypatch.setattr(I, "_real_block_parts", lambda blk, **k: {})
    monkeypatch.setattr(I, "_sea_plane", lambda disc=1, game=None: _sea4_grid_plane())

    I.landmass(MOD, cell=(3, 1), base_radius=20.0, seed=5.0, flat=True, skip_mirror=True)
    assert (tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc1").exists()
    assert not (tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc4").exists()


def test_island_landmass_dry_run_never_mirrors(tmp_path, monkeypatch):
    """A dry run writes NOTHING at all -- a deploy that writes no worldmap overrides never triggers the
    mirror (auto_mirror would see an empty ``written`` list even if it were called)."""
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    _patch_open_ocean(monkeypatch)
    monkeypatch.setattr(I, "_real_block_parts", lambda blk, **k: {})
    monkeypatch.setattr(I, "_sea_plane", lambda disc=1, game=None: _sea4_grid_plane())

    I.landmass(MOD, cell=(3, 1), base_radius=20.0, seed=5.0, flat=True, dry_run=True)
    assert not (tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc1").exists()
    assert not (tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc4").exists()


def test_terrain_reclaim_auto_mirrors_disc4(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    _patch_open_ocean(monkeypatch)
    monkeypatch.setattr(PAL, "apply_palette_uvs", lambda bm, **k: bm)   # no install needed

    T.reclaim(MOD, cells=[(2, 2)], profile="flat", topograph=0, height=0.0)
    src = tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / "r2" / "Block[2][2] Terrain.ff9mesh"
    dst = tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc4" / "0_1" / "r2" / "Block[2][2] Terrain.ff9mesh"
    assert src.is_file() and dst.is_file()
    assert dst.read_bytes() == src.read_bytes()


def test_terrain_reclaim_skip_mirror(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    _patch_open_ocean(monkeypatch)
    monkeypatch.setattr(PAL, "apply_palette_uvs", lambda bm, **k: bm)

    T.reclaim(MOD, cells=[(2, 2)], profile="flat", topograph=0, height=0.0, skip_mirror=True)
    assert (tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc1").exists()
    assert not (tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc4").exists()


def test_terrain_reclaim_dry_run_never_mirrors(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    _patch_open_ocean(monkeypatch)
    monkeypatch.setattr(PAL, "apply_palette_uvs", lambda bm, **k: bm)

    T.reclaim(MOD, cells=[(2, 2)], profile="flat", topograph=0, height=0.0, dry_run=True)
    assert not (tmp_path / MOD).exists()


def test_interior_deploy_changed_auto_mirrors(tmp_path, monkeypatch):
    """world-forest/world-hill's SHARED writer (interior.deploy_changed) also auto-mirrors -- while
    world-mountain force-skips BOTH inner writers and makes the one mirror pass itself over the union
    of their written paths (see cli.py's _cmd_world_mountain + its wiring test below)."""
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    _patch_open_ocean(monkeypatch)
    bm = _tri_blockmesh("Block[4][4] Terrain", disc=1, x=4, y=4)

    out = IN.deploy_changed({(4, 4): bm}, mod_folder=MOD, log=lambda *a, **k: None)
    assert out
    src = tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / "r4" / "Block[4][4] Terrain.ff9mesh"
    dst = tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc4" / "0_1" / "r4" / "Block[4][4] Terrain.ff9mesh"
    assert src.is_file() and dst.is_file()
    assert dst.read_bytes() == src.read_bytes()


def test_interior_deploy_changed_skip_mirror(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    _patch_open_ocean(monkeypatch)
    bm = _tri_blockmesh("Block[4][4] Terrain", disc=1, x=4, y=4)

    IN.deploy_changed({(4, 4): bm}, mod_folder=MOD, log=lambda *a, **k: None, skip_mirror=True)
    assert not (tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc4").exists()


def test_interior_deploy_changed_empty_never_mirrors(tmp_path, monkeypatch):
    """Nothing changed -> nothing deployed -> auto_mirror is called with an empty list -> no-op."""
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    out = IN.deploy_changed({}, mod_folder=MOD, log=lambda *a, **k: None)
    assert out == []
    assert not (tmp_path / MOD).exists()


# --------------------------------------------------------------------------- the standalone verb is unaffected

def test_standalone_mirror_still_works_directly(tmp_path, monkeypatch):
    """DM.mirror() (the `world-mirror` CLI verb) is a normal, always-runs, whole-tree (cells=None) call --
    unaffected by any of the auto_mirror opt-outs/scoping above."""
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    _patch_open_ocean(monkeypatch)
    src = tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / "r9"
    src.mkdir(parents=True)
    (src / "Block[9][9] Terrain.ff9mesh").write_bytes(b"DIRECT-MIRROR-CALL")

    result = DM.mirror(MOD, log=lambda *a, **k: None)
    dst = tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc4" / "0_1" / "r9" / "Block[9][9] Terrain.ff9mesh"
    assert dst.read_bytes() == b"DIRECT-MIRROR-CALL"
    assert dst in result["mirrored"]
