"""world-mirror (ff9mapkit/world/discmirror.py) -- THE DISC-4 GAP closer: copy a mod's Disc1 WorldMap block
overrides into Disc4 verbatim, gated per-cell against the REAL map's own per-disc parts, plus THE FREE-RIDE PIN
(a sidecar donor's un-overridden real parts get pinned into the destination tree with SOURCE-disc bytes, so a
mirrored cell never silently borrows the destination disc's own variant of a part it didn't explicitly override).

Fully hermetic: a fake mod-folder tree lives under tmp_path (config.find_game_path monkeypatched), and the REAL
map's asset layer is stubbed at its two seams -- extract._worldmap_env (feeds ._real_parts' container regex) and
extract.read_block (feeds ._parts_identical's byte comparison AND the free-ride pin's donor reads) -- via synthetic
tables. write_ff9mesh/read_ff9mesh run for REAL on the pin path (a genuine BlockMesh is built + serialized +
re-parsed), so this pins the on-disk .ff9mesh format too, not just the gating logic.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from ff9mapkit import config
from ff9mapkit.world import discmirror as DM
from ff9mapkit.world import extract as X
from ff9mapkit.world import mesh as M
from ff9mapkit.world.extract import BlockMesh, CH_POS, CH_NRM, CH_UV, CH_TAN, encode_id

MOD = "FF9CustomMap"

# a reference triangle + a variant differing at ONE vertex -- the same shape used throughout to distinguish
# "identical across discs" from "differs across discs" fixtures.
_TRI_A = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]
_TRI_B = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 2.0]]


# --------------------------------------------------------------------------- synthetic fixture builders

def _mk_blockmesh(name, *, disc, x, y, verts, topograph=0):
    """A genuinely valid BlockMesh (real position/normal/uv/tangent channels for every vertex) so
    write_ff9mesh/read_ff9mesh run for real on it. ``verts`` length must be a multiple of 3 (one flat/unindexed
    triangle per 3 verts, mirroring the real world-block layout: vcount == indexCount)."""
    n = len(verts)
    assert n % 3 == 0
    idall = float(encode_id(topograph=topograph))
    normals = [[0.0, 1.0, 0.0] for _ in range(n)]
    uvs = [[0.25 * i, 0.5 * i] for i in range(n)]
    tangents = [[idall, 0.0, 0.0, 1.0] for _ in range(n)]
    flat = list(range(n))
    tris = [flat[i:i + 3] for i in range(0, n, 3)]
    return BlockMesh(name=name, disc=disc, x=x, y=y, lod="0_1", vcount=n, stride=48,
                      channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                      chan_arrays={CH_POS: [list(v) for v in verts], CH_NRM: normals, CH_UV: uvs, CH_TAN: tangents},
                      flat_index=flat, tris=tris, raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


def _variant_channel(bm: BlockMesh, channel: int, new_values: list) -> BlockMesh:
    """Copy of ``bm`` with exactly ONE vertex channel swapped -- verts/vcount/flat_index (and every OTHER
    channel) stay byte-identical. Used to build ``_parts_identical`` fixtures that isolate a single ANDed
    comparison (see the uv/normal/tangent/vcount/flat_index-only mismatch tests below)."""
    arrays = dict(bm.chan_arrays)
    arrays[channel] = new_values
    return dataclasses.replace(bm, chan_arrays=arrays)


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


class _FakeEnv:
    """Stands in for the UnityPy bundle env -_worldmap_env returns: only ``.container`` is read."""
    def __init__(self, container):
        self.container = list(container)


def _cont(disc, x, y, part, *, r=None):
    """One synthetic REAL-map container path, shaped to match ``_real_parts``' own regex."""
    ry = r if r is not None else y
    return f"assets/resources/worldmap/disc{disc}/0_1/r{ry}/block[{x}][{y}] {part}.asset"


def _patch_real_layer(monkeypatch, *, containers: dict, blocks: dict):
    """``containers`` = {disc: [container path strings]} feeds _worldmap_env (-> ._real_parts).
    ``blocks`` = {(disc, x, y, part_lower): BlockMesh} feeds read_block (-> ._parts_identical + the free-ride pin)."""
    def fake_worldmap_env(disc, game=None):
        return _FakeEnv(containers.get(disc, []))

    def fake_read_block(x, y, *, disc=1, lod="0_1", part="terrain", game=None):
        key = (disc, x, y, part.lower())
        if key not in blocks:
            raise ValueError(f"no fake block for {key}")
        return blocks[key]

    monkeypatch.setattr(X, "_worldmap_env", fake_worldmap_env)
    monkeypatch.setattr(X, "read_block", fake_read_block)


def _setup_world(tmp_path, monkeypatch):
    """The shared world for the mirror() tests: 6 deployed cells exercising every per-cell gate outcome +
    the free-ride pin + a bad Donor.txt, plus the REAL map's per-disc part inventory + block bytes that gate
    them. Returns ``(src_root, dst_root)``.

    Cells:
      (2,3)   -- real part sets match AND bytes match  -> mirrored
      (4,5)   -- real part sets DIFFER across discs      -> skipped, nothing written
      (6,7)   -- real part sets match, bytes DIFFER      -> skipped, nothing written
      (8,9)   -- open ocean at dst (no real parts at all) -> mirrored unconditionally
      (10,11) -- open ocean at dst + a Donor.txt -> (20,21)  -> mirrored + THE FREE-RIDE PIN (object, riverjoint)
      (12,13) -- open ocean at dst + an UNPARSEABLE Donor.txt -> mirrored, but also lands in `skipped`
    """
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    src_root = tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
    dst_root = tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc4" / "0_1"

    _write(src_root / "r3" / "Block[2][3] Terrain.ff9mesh", b"TERRAIN-2-3-IDENTICAL")
    _write(src_root / "r5" / "Block[4][5] Terrain.ff9mesh", b"TERRAIN-4-5-SETSDIFFER")
    _write(src_root / "r7" / "Block[6][7] Terrain.ff9mesh", b"TERRAIN-6-7-BYTESDIFFER")
    _write(src_root / "r9" / "Block[8][9] Terrain.ff9mesh", b"TERRAIN-8-9-OPENOCEAN")
    _write(src_root / "r11" / "Block[10][11] Terrain.ff9mesh", b"TERRAIN-10-11-FREERIDE")
    _write(src_root / "r11" / "Block[10][11] Donor.txt", b"20,21")
    _write(src_root / "r13" / "Block[12][13] Terrain.ff9mesh", b"TERRAIN-12-13-BADDONOR")
    _write(src_root / "r13" / "Block[12][13] Donor.txt", b"not-a-coordinate-pair")

    containers = {
        1: [_cont(1, 2, 3, "terrain"), _cont(1, 4, 5, "terrain"), _cont(1, 6, 7, "terrain"),
            _cont(1, 20, 21, "terrain"), _cont(1, 20, 21, "object"), _cont(1, 20, 21, "riverjoint")],
        4: [_cont(4, 2, 3, "terrain"),                                    # same set as src -> gate checks bytes
            _cont(4, 4, 5, "terrain"), _cont(4, 4, 5, "object"),          # an EXTRA real part -> sets differ
            _cont(4, 6, 7, "terrain")],                                   # same set as src -> bytes will differ
        # (8,9), (10,11), (12,13) intentionally absent from disc4 -> open ocean at dst for all three
    }
    blocks = {
        (1, 2, 3, "terrain"): _mk_blockmesh("Block[2][3] Terrain", disc=1, x=2, y=3, verts=_TRI_A),
        (4, 2, 3, "terrain"): _mk_blockmesh("Block[2][3] Terrain", disc=4, x=2, y=3, verts=_TRI_A),
        (1, 6, 7, "terrain"): _mk_blockmesh("Block[6][7] Terrain", disc=1, x=6, y=7, verts=_TRI_A),
        (4, 6, 7, "terrain"): _mk_blockmesh("Block[6][7] Terrain", disc=4, x=6, y=7, verts=_TRI_B),
        (1, 20, 21, "object"): _mk_blockmesh("Block[20][21] Object", disc=1, x=20, y=21, verts=_TRI_A),
        (1, 20, 21, "riverjoint"): _mk_blockmesh("Block[20][21] RiverJoint", disc=1, x=20, y=21,
                                                  verts=_TRI_A + _TRI_B),   # 6 verts -> a distinct vcount from Object
    }
    _patch_real_layer(monkeypatch, containers=containers, blocks=blocks)
    return src_root, dst_root


def _run_mirror(tmp_path, monkeypatch, *, log=None, **mirror_kwargs):
    src_root, dst_root = _setup_world(tmp_path, monkeypatch)
    result = DM.mirror(MOD, log=(log or (lambda *a, **k: None)), **mirror_kwargs)
    return result, src_root, dst_root


# --------------------------------------------------------------------------- _real_parts (direct)

def test_real_parts_keys_by_cell_and_filters_by_disc(monkeypatch):
    # BOTH discs' _worldmap_env return the SAME mixed listing (disc1 and disc4 entries together) -- this proves
    # the per-disc scoping comes from ._real_parts' own regex, not merely from a different env per disc.
    mixed = [_cont(1, 3, 4, "terrain"), _cont(1, 3, 4, "object"), _cont(1, 5, 6, "terrain"),
             _cont(4, 3, 4, "terrain"), _cont(4, 7, 8, "beach1")]
    monkeypatch.setattr(X, "_worldmap_env", lambda disc, game=None: _FakeEnv(mixed))
    assert DM._real_parts(1) == {(3, 4): {"terrain", "object"}, (5, 6): {"terrain"}}
    assert DM._real_parts(4) == {(3, 4): {"terrain"}, (7, 8): {"beach1"}}


def test_real_parts_ignores_non_matching_container_entries(monkeypatch):
    """Entries that don't match the container-path shape (wrong disc number embedded, or a non-.asset/non-mesh
    name) are simply not counted -- a real fence against ._real_parts over-matching. Also proves the regex's
    trailing ``.asset`` is genuinely OPTIONAL: every OTHER fixture in this file appends it (via ``_cont()``), so
    without this case a regression that made ``.asset`` MANDATORY would be invisible."""
    mixed = [_cont(1, 1, 1, "terrain"),
             "assets/resources/worldmap/disc1/0_1/r2/block[2][2] object",   # no ".asset" suffix at all -- still real
             "assets/resources/worldmap/disc1/0_1/r1/block[1][1] readme.txt",
             "assets/resources/something/unrelated.asset"]
    monkeypatch.setattr(X, "_worldmap_env", lambda disc, game=None: _FakeEnv(mixed))
    assert DM._real_parts(1) == {(1, 1): {"terrain"}, (2, 2): {"object"}}


def test_real_parts_ignores_lod_and_always_reads_0_1_pattern(monkeypatch):
    """SUSPECTED BUG (pinned as current behavior, NOT fixed): ``_real_parts`` takes no ``lod`` parameter -- its
    container regex is hard-coded to the "0_1" LOD path segment regardless of which LOD ``mirror()`` is asked to
    mirror. A real container entry that lives under a different LOD (e.g. "2_4") is invisible to it, so
    ``mirror(lod="2_4")``'s per-cell gate always consults 0_1's real geometry, never the LOD actually being
    mirrored."""
    containers = {1: [_cont(1, 5, 5, "terrain")],                                     # a real "0_1" entry
                  4: ["assets/resources/worldmap/disc4/2_4/r5/block[5][5] terrain.asset"]}   # real, but under 2_4
    monkeypatch.setattr(X, "_worldmap_env", lambda disc, game=None: _FakeEnv(containers.get(disc, [])))
    assert DM._real_parts(1) == {(5, 5): {"terrain"}}
    assert DM._real_parts(4) == {}          # the 2_4 entry is invisible to the (hard-coded 0_1) regex


# --------------------------------------------------------------------------- _parts_identical (direct)

def test_parts_identical_true_and_false_on_vert_mismatch(monkeypatch):
    blocks = {
        (1, 9, 9, "terrain"): _mk_blockmesh("Block[9][9] Terrain", disc=1, x=9, y=9, verts=_TRI_A),
        (4, 9, 9, "terrain"): _mk_blockmesh("Block[9][9] Terrain", disc=4, x=9, y=9, verts=_TRI_A),
        (1, 9, 9, "object"): _mk_blockmesh("Block[9][9] Object", disc=1, x=9, y=9, verts=_TRI_A),
        (4, 9, 9, "object"): _mk_blockmesh("Block[9][9] Object", disc=4, x=9, y=9, verts=_TRI_B),
    }

    def fake_read_block(x, y, *, disc=1, lod="0_1", part="terrain", game=None):
        return blocks[(disc, x, y, part.lower())]

    monkeypatch.setattr(X, "read_block", fake_read_block)
    assert DM._parts_identical((9, 9), "terrain", 1, 4) is True
    assert DM._parts_identical((9, 9), "object", 1, 4) is False


# `_parts_identical` ANDs six fields (vcount/verts/flat_index/uvs/tangents/normals). Every "differs" fixture
# above (and every mirror()-level "bytes differ" fixture in the file) varies ONLY `verts` -- so a regression
# that silently dropped any of the OTHER five comparisons from the AND-chain would be invisible to this suite.
# Each test below holds every field but ONE byte-identical across "discs" and varies only the named field, so
# each ANDed clause has its own falsifying fixture.

def _patch_single_block(monkeypatch, a: BlockMesh, b: BlockMesh):
    blocks = {(1, 9, 9, "terrain"): a, (4, 9, 9, "terrain"): b}
    monkeypatch.setattr(X, "read_block",
                         lambda x, y, *, disc=1, lod="0_1", part="terrain", game=None: blocks[(disc, x, y, part.lower())])


def test_parts_identical_false_on_uv_mismatch_alone(monkeypatch):
    a = _mk_blockmesh("Block[9][9] Terrain", disc=1, x=9, y=9, verts=_TRI_A)
    b = _variant_channel(a, CH_UV, [[9.0, 9.0] for _ in a.uvs])
    b = dataclasses.replace(b, disc=4)
    # sanity: only uvs differ between these two fixtures
    assert a.verts == b.verts and a.vcount == b.vcount and a.flat_index == b.flat_index
    assert a.tangents == b.tangents and a.normals == b.normals
    assert a.uvs != b.uvs

    _patch_single_block(monkeypatch, a, b)
    assert DM._parts_identical((9, 9), "terrain", 1, 4) is False


def test_parts_identical_false_on_normal_mismatch_alone(monkeypatch):
    a = _mk_blockmesh("Block[9][9] Terrain", disc=1, x=9, y=9, verts=_TRI_A)
    b = _variant_channel(a, CH_NRM, [[0.0, -1.0, 0.0] for _ in a.normals])
    b = dataclasses.replace(b, disc=4)
    # sanity: only normals differ between these two fixtures
    assert a.verts == b.verts and a.vcount == b.vcount and a.flat_index == b.flat_index
    assert a.uvs == b.uvs and a.tangents == b.tangents
    assert a.normals != b.normals

    _patch_single_block(monkeypatch, a, b)
    assert DM._parts_identical((9, 9), "terrain", 1, 4) is False


def test_parts_identical_false_on_tangent_mismatch_alone(monkeypatch):
    """The tangent channel carries the encoded IDALL (event/area/TOPOGRAPH/flags) -- the walkability payload
    the module's own docstring says this gate exists to protect. A different ``topograph`` changes ONLY the
    tangent float; verts/uvs/normals/vcount/flat_index (all derived from vertex position/index, not from
    topograph) stay identical."""
    a = _mk_blockmesh("Block[9][9] Terrain", disc=1, x=9, y=9, verts=_TRI_A, topograph=0)
    b = _mk_blockmesh("Block[9][9] Terrain", disc=4, x=9, y=9, verts=_TRI_A, topograph=7)
    # sanity: only tangents differ between these two fixtures
    assert a.verts == b.verts and a.vcount == b.vcount and a.flat_index == b.flat_index
    assert a.uvs == b.uvs and a.normals == b.normals
    assert a.tangents != b.tangents

    _patch_single_block(monkeypatch, a, b)
    assert DM._parts_identical((9, 9), "terrain", 1, 4) is False


def test_parts_identical_false_on_vcount_mismatch_alone(monkeypatch):
    """A corrupt/mismatched recorded ``vcount`` vs. the actual vertex array length -- every channel array is
    byte-identical, only the ``vcount`` field itself differs."""
    a = _mk_blockmesh("Block[9][9] Terrain", disc=1, x=9, y=9, verts=_TRI_A)
    b = dataclasses.replace(a, disc=4, vcount=a.vcount + 1)
    # sanity: only vcount differs between these two fixtures
    assert a.verts == b.verts and a.flat_index == b.flat_index
    assert a.uvs == b.uvs and a.tangents == b.tangents and a.normals == b.normals
    assert a.vcount != b.vcount

    _patch_single_block(monkeypatch, a, b)
    assert DM._parts_identical((9, 9), "terrain", 1, 4) is False


def test_parts_identical_false_on_flat_index_mismatch_alone(monkeypatch):
    """Same 3 verts, wound the other way -- the index buffer order differs while every vertex channel (and
    vcount) stays byte-identical."""
    a = _mk_blockmesh("Block[9][9] Terrain", disc=1, x=9, y=9, verts=_TRI_A)
    reversed_idx = list(reversed(a.flat_index))
    b = dataclasses.replace(a, disc=4, flat_index=reversed_idx, tris=[reversed_idx])
    # sanity: only flat_index differs between these two fixtures
    assert a.verts == b.verts and a.vcount == b.vcount
    assert a.uvs == b.uvs and a.tangents == b.tangents and a.normals == b.normals
    assert a.flat_index != b.flat_index

    _patch_single_block(monkeypatch, a, b)
    assert DM._parts_identical((9, 9), "terrain", 1, 4) is False


# --------------------------------------------------------------------------- mirror() -- the per-cell gate

def test_mirror_copies_open_ocean_cell_verbatim(tmp_path, monkeypatch):
    result, src_root, dst_root = _run_mirror(tmp_path, monkeypatch)
    assert "Block[8][9] Terrain.ff9mesh" in {p.name for p in result["mirrored"]}
    dst = dst_root / "r9" / "Block[8][9] Terrain.ff9mesh"
    assert dst.read_bytes() == b"TERRAIN-8-9-OPENOCEAN"
    assert (8, 9) not in dict(result["skipped"])


def test_mirror_gate_skips_when_real_part_sets_differ(tmp_path, monkeypatch):
    result, src_root, dst_root = _run_mirror(tmp_path, monkeypatch)
    skipped = dict(result["skipped"])
    assert (4, 5) in skipped and "sets differ" in skipped[(4, 5)]
    assert "Block[4][5] Terrain.ff9mesh" not in {p.name for p in result["mirrored"]}
    assert not (dst_root / "r5" / "Block[4][5] Terrain.ff9mesh").exists()


def test_mirror_gate_skips_when_real_bytes_differ(tmp_path, monkeypatch):
    result, src_root, dst_root = _run_mirror(tmp_path, monkeypatch)
    skipped = dict(result["skipped"])
    assert (6, 7) in skipped and "differs across discs" in skipped[(6, 7)]
    assert "Block[6][7] Terrain.ff9mesh" not in {p.name for p in result["mirrored"]}
    assert not (dst_root / "r7" / "Block[6][7] Terrain.ff9mesh").exists()


def test_mirror_gate_mirrors_when_real_sets_and_bytes_match(tmp_path, monkeypatch):
    result, src_root, dst_root = _run_mirror(tmp_path, monkeypatch)
    assert "Block[2][3] Terrain.ff9mesh" in {p.name for p in result["mirrored"]}
    dst = dst_root / "r3" / "Block[2][3] Terrain.ff9mesh"
    assert dst.read_bytes() == b"TERRAIN-2-3-IDENTICAL"
    assert (2, 3) not in dict(result["skipped"])


def test_mirror_gate_names_only_the_differing_part_in_a_multi_part_set(tmp_path, monkeypatch):
    """``diff = [pt for pt in sorted(dst_real) if not _parts_identical(...)]`` iterates EVERY part in the real
    set -- every other gate test in this file uses a single-part set ({"terrain"}), so a regression that only
    checked the FIRST part (an early-exit/`any()` rewrite that loses per-part detail) would be invisible. Real
    set = {terrain, object} on both discs; terrain matches, object doesn't -- the skip reason must name ONLY
    "object", not "terrain"."""
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    src_root = tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
    dst_root = tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc4" / "0_1"
    _write(src_root / "r17" / "Block[16][17] Terrain.ff9mesh", b"TERRAIN-16-17")

    containers = {1: [_cont(1, 16, 17, "terrain"), _cont(1, 16, 17, "object")],
                  4: [_cont(4, 16, 17, "terrain"), _cont(4, 16, 17, "object")]}
    blocks = {
        (1, 16, 17, "terrain"): _mk_blockmesh("Block[16][17] Terrain", disc=1, x=16, y=17, verts=_TRI_A),
        (4, 16, 17, "terrain"): _mk_blockmesh("Block[16][17] Terrain", disc=4, x=16, y=17, verts=_TRI_A),
        (1, 16, 17, "object"): _mk_blockmesh("Block[16][17] Object", disc=1, x=16, y=17, verts=_TRI_A),
        (4, 16, 17, "object"): _mk_blockmesh("Block[16][17] Object", disc=4, x=16, y=17, verts=_TRI_B),
    }
    _patch_real_layer(monkeypatch, containers=containers, blocks=blocks)

    result = DM.mirror(MOD, log=lambda *a, **k: None)

    skipped = dict(result["skipped"])
    reason = skipped[(16, 17)]
    assert "object" in reason and "terrain" not in reason
    assert not (dst_root / "r17" / "Block[16][17] Terrain.ff9mesh").exists()


# --------------------------------------------------------------------------- mirror() -- the free-ride pin

def test_mirror_free_ride_pin_writes_donor_extras(tmp_path, monkeypatch):
    result, src_root, dst_root = _run_mirror(tmp_path, monkeypatch)
    pinned_names = {p.name for p in result["pinned"]}
    assert pinned_names == {"Block[10][11] Object.ff9mesh", "Block[10][11] RiverJoint.ff9mesh"}

    obj_path = dst_root / "r11" / "Block[10][11] Object.ff9mesh"
    assert obj_path in result["pinned"]
    obj = M.read_ff9mesh(obj_path)                        # write_ff9mesh really ran -- re-parse for real
    assert obj["vcount"] == 3 and obj["indices"] == [0, 1, 2]

    rj = M.read_ff9mesh(dst_root / "r11" / "Block[10][11] RiverJoint.ff9mesh")
    assert rj["vcount"] == 6                               # RiverJoint's donor mesh had 2 triangles, Object 1

    # the cell's OWN deployed files (terrain override + the donor sidecar itself) mirror too, byte-verbatim
    mirrored_names = {p.name for p in result["mirrored"]}
    assert {"Block[10][11] Terrain.ff9mesh", "Block[10][11] Donor.txt"} <= mirrored_names
    assert (dst_root / "r11" / "Block[10][11] Donor.txt").read_bytes() == b"20,21"

    assert (10, 11) not in dict(result["skipped"])


def test_mirror_free_ride_pin_skips_when_donor_reals_are_subset_of_overridden(tmp_path, monkeypatch):
    """Distinct from the sibling test above (where the donor has EXTRA un-overridden parts): here the donor's
    ONLY real part ("terrain") is a STRICT SUBSET of what this cell already overrides itself (terrain + object
    both deployed) -- ``extras`` must come out empty and NOTHING pinned for the cell. ``blocks={}`` doubles as
    a fence that ``read_block`` is never even called for the (would-be) donor parts."""
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    src_root = tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
    dst_root = tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc4" / "0_1"
    _write(src_root / "r15" / "Block[14][15] Terrain.ff9mesh", b"TERRAIN-14-15")
    _write(src_root / "r15" / "Block[14][15] Object.ff9mesh", b"OBJECT-14-15")
    _write(src_root / "r15" / "Block[14][15] Donor.txt", b"22,23")

    containers = {1: [_cont(1, 22, 23, "terrain")], 4: []}   # donor's ONLY real part is terrain -- already overridden
    _patch_real_layer(monkeypatch, containers=containers, blocks={})

    result = DM.mirror(MOD, log=lambda *a, **k: None)

    assert result["pinned"] == []
    mirrored_names = {p.name for p in result["mirrored"]}
    assert {"Block[14][15] Terrain.ff9mesh", "Block[14][15] Object.ff9mesh",
            "Block[14][15] Donor.txt"} <= mirrored_names
    assert (14, 15) not in dict(result["skipped"])


# --------------------------------------------------------------------------- mirror() -- bad Donor.txt

def test_mirror_bad_donor_txt_still_copies_but_is_skipped(tmp_path, monkeypatch):
    result, src_root, dst_root = _run_mirror(tmp_path, monkeypatch)
    mirrored_names = {p.name for p in result["mirrored"]}
    # current (pinned) behavior: the copy loop runs BEFORE the Donor.txt is parsed, so a cell with an
    # unparseable sidecar still gets its deployed files mirrored -- it is not fully "skipped".
    assert {"Block[12][13] Terrain.ff9mesh", "Block[12][13] Donor.txt"} <= mirrored_names
    assert (dst_root / "r13" / "Block[12][13] Terrain.ff9mesh").read_bytes() == b"TERRAIN-12-13-BADDONOR"

    skipped = dict(result["skipped"])
    assert skipped.get((12, 13)) == "bad Donor.txt"
    # no pin was (or could be) attempted for this cell -- its donor coords never parsed
    assert not any(p.parent.name == "r13" for p in result["pinned"])


# --------------------------------------------------------------------------- mirror() -- lod parameter

def test_mirror_reads_and_writes_the_requested_lod(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    src_root = tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc1" / "2_4"
    dst_root = tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc4" / "2_4"
    _write(src_root / "r1" / "Block[1][1] Terrain.ff9mesh", b"LOD-2-4-BYTES")
    monkeypatch.setattr(X, "_worldmap_env", lambda disc, game=None: _FakeEnv([]))   # no real parts on either disc

    result = DM.mirror(MOD, lod="2_4", log=lambda *a, **k: None)

    assert {p.name for p in result["mirrored"]} == {"Block[1][1] Terrain.ff9mesh"}
    dst = dst_root / "r1" / "Block[1][1] Terrain.ff9mesh"
    assert dst.is_file() and dst.read_bytes() == b"LOD-2-4-BYTES"
    # the default-lod tree was never touched
    assert not (tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc4" / "0_1").exists()


# --------------------------------------------------------------------------- mirror() -- dry_run

def test_mirror_dry_run_reports_without_writing(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    src_root = tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
    dst_root = tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc4" / "0_1"
    _write(src_root / "r30" / "Block[30][30] Terrain.ff9mesh", b"DRYRUN-BYTES")
    _write(src_root / "r30" / "Block[30][30] Donor.txt", b"40,41")
    blocks = {(1, 40, 41, "object"): _mk_blockmesh("Block[40][41] Object", disc=1, x=40, y=41, verts=_TRI_A)}
    containers = {1: [_cont(1, 40, 41, "terrain"), _cont(1, 40, 41, "object")], 4: []}
    _patch_real_layer(monkeypatch, containers=containers, blocks=blocks)

    result = DM.mirror(MOD, dry_run=True, log=lambda *a, **k: None)

    assert {p.name for p in result["mirrored"]} == {"Block[30][30] Terrain.ff9mesh", "Block[30][30] Donor.txt"}
    assert {p.name for p in result["pinned"]} == {"Block[30][30] Object.ff9mesh"}
    # dry_run means NOTHING actually lands on disk, despite the report describing what would happen
    assert not dst_root.exists()


# --------------------------------------------------------------------------- mirror() -- error paths

def test_mirror_raises_when_disc_tree_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    (tmp_path / MOD).mkdir(parents=True)                      # mod folder exists, but no WorldMap/Disc1 tree at all
    with pytest.raises(ValueError, match="no Disc1 WorldMap overrides"):
        DM.mirror(MOD, log=lambda *a, **k: None)


def test_mirror_raises_when_no_deployed_blocks(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    src_root = tmp_path / MOD / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
    src_root.mkdir(parents=True)
    (src_root / "readme.txt").write_text("not a Block override", encoding="utf-8")   # tree exists, but no matches
    with pytest.raises(ValueError, match="no deployed Block overrides"):
        DM.mirror(MOD, log=lambda *a, **k: None)


# --------------------------------------------------------------------------- log output

def test_mirror_logs_pin_and_summary_lines(tmp_path, monkeypatch):
    logged = []
    result, _, _ = _run_mirror(tmp_path, monkeypatch, log=logged.append)
    assert any("PIN" in m and "(10, 11)" in m for m in logged)
    assert any("SKIP" in m and "(4, 5)" in m for m in logged)
    summary = logged[-1]
    assert f"mirrored {len(result['mirrored'])}" in summary and f"pinned {len(result['pinned'])}" in summary
