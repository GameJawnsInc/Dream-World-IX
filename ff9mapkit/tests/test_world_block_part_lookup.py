#!/usr/bin/env python3
"""``extract.read_block`` resolves a block PART by its exact container, never by substring (D4-17).

Part names prefix one another on the same block -- ``sea4``/``sea4f`` at disc-4 (12,0), ``river``/
``riverjoint`` at (19,11), (5,16) and (16,15) -- and the old ``target in container`` rule handed back
whichever container came first in ``env.objects`` order: disc-4 (12,0) ``sea4`` decoded Sea4f, a (19,11)
donor's ``river`` decoded RiverJoint, and (16,15), which has NO River, answered ``river`` with RiverJoint.
Evidence: ``studies/terrain-malleability/disc4/verify_prefix_collision.py``.

Hermetic half: the matching rule, and read_block's own lookup through a fake env in BOTH container orders
(the collision only bit when the longer name came first). Install-gated half: the real collisions, plus a
sweep proving every real block container resolves to itself.
"""
from __future__ import annotations

import re

import pytest

from ff9mapkit.world import extract as X
from ff9mapkit.world.extract import BlockMesh, CH_POS

_PFX = "assets/resources/worldmap"


def _game_ready():
    try:
        import UnityPy  # noqa: F401
        from ff9mapkit import config
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


# --------------------------------------------------------------------------- the matching rule
_D4_12_0 = (4, "0_1", 12, 0)
_D1_19_11 = (1, "0_1", 19, 11)


@pytest.mark.parametrize("container, query, part, hit", [
    (f"{_PFX}/disc4/0_1/r0/block[12][0] sea4.asset", _D4_12_0, "sea4", True),
    (f"{_PFX}/disc4/0_1/r0/block[12][0] sea4f.asset", _D4_12_0, "sea4", False),   # the D4-17 collision
    (f"{_PFX}/disc4/0_1/r0/block[12][0] sea4f.asset", _D4_12_0, "sea4f", True),
    (f"{_PFX}/disc1/0_1/r11/block[19][11] river.asset", _D1_19_11, "river", True),
    (f"{_PFX}/disc1/0_1/r11/block[19][11] riverjoint.asset", _D1_19_11, "river", False),
    (f"{_PFX}/disc1/0_1/r11/block[19][11] riverjoint.asset", _D1_19_11, "riverjoint", True),
    (f"{_PFX}/disc1/0_1/r11/block[19][11] riverjoint.asset", _D1_19_11, "RiverJoint", True),  # case-insensitive
    ("worldmap/disc1/0_1/r11/block[19][11] river", _D1_19_11, "river", True),     # bare: no prefix/extension
    ("worldmap/disc1/0_1/r11/block[19][11] river.fbx", _D1_19_11, "river", True),  # any one extension drops
    (f"{_PFX}/disc1/0_1/r11/block[19][11] river.asset", _D1_19_11, "rive", False),  # a shorter part
    (f"{_PFX}/disc1/0_1/r11/block[19][11] river.asset", _D1_19_11, "river.asset", False),
    (f"{_PFX}/disc1/0_2/r11/block[19][11] river.asset", _D1_19_11, "river", False),   # other lod
    (f"{_PFX}/disc4/0_1/r11/block[19][11] river.asset", _D1_19_11, "river", False),   # other disc
    (f"{_PFX}/disc1/0_1/r11/block[9][11] river.asset", _D1_19_11, "river", False),    # other block
    ("assets/resources/otherworldmap/disc1/0_1/r11/block[19][11] river.asset", _D1_19_11, "river", False),
])
def test_part_match_is_exact(container, query, part, hit):
    assert X._is_block_part_container(container.lower(), X._block_part_target(*query, part)) is hit


def test_target_is_lowercase_and_extensionless():
    assert X._block_part_target(4, "0_1", 12, 0, "Sea4") == "worldmap/disc4/0_1/r0/block[12][0] sea4"


# --------------------------------------------------------------------------- read_block through a fake env
class _Obj:
    """One Mesh-typed ``env.objects`` entry: ``.type`` + ``.container`` are all ``_mesh_index`` reads."""

    def __init__(self, container, mesh_type):
        self.container = container
        self.type = mesh_type


class _Env:
    def __init__(self, containers, mesh_type):
        self.objects = [_Obj(c, mesh_type) for c in containers]
        self.container = list(containers)


def _part_of(container):
    return re.search(r"\] ([a-z0-9_]+)(?:\.\w+)?$", container.lower()).group(1)


@pytest.fixture
def fake_layer(monkeypatch):
    """Stub the asset layer: ``_worldmap_env`` -> a fake env, ``_decode_world_mesh`` -> a one-vertex mesh
    named after the container it was handed (and counted), ``_class_id_mesh`` -> a sentinel, so no
    UnityPy and no install are needed. Returns ``install(containers)`` and the decode log."""
    mesh_type = object()
    decoded = []
    state = {}

    def decode(o, *, disc, x, y, lod):
        decoded.append(o.container)
        return BlockMesh(name=f"Block[{x}][{y}] {_part_of(o.container)}", disc=disc, x=x, y=y, lod=lod,
                         vcount=1, stride=12, channels={CH_POS: (0, 3)},
                         chan_arrays={CH_POS: [[0.0, 0.0, 0.0]]}, flat_index=[], tris=[],
                         raw_vbuf=b"", raw_ibuf=b"", use32=False, submeshes=[])

    def install(containers):
        state["env"] = _Env(containers, mesh_type)
        return state["env"]

    monkeypatch.setattr(X, "_class_id_mesh", lambda: mesh_type)
    monkeypatch.setattr(X, "_decode_world_mesh", decode)
    monkeypatch.setattr(X, "_worldmap_env", lambda disc=1, game=None: state["env"])
    return install, decoded


_SEA4 = f"{_PFX}/disc4/0_1/r0/block[12][0] sea4.asset"
_SEA4F = f"{_PFX}/disc4/0_1/r0/block[12][0] sea4f.asset"
_RIVER = f"{_PFX}/disc1/0_1/r11/block[19][11] river.asset"
_JOINT = f"{_PFX}/disc1/0_1/r11/block[19][11] riverjoint.asset"


@pytest.mark.parametrize("order", ["longer_first", "shorter_first"])
def test_read_block_resolves_exact_part_in_either_order(fake_layer, order):
    install, decoded = fake_layer
    pairs = [(_SEA4F, _SEA4), (_JOINT, _RIVER)]
    install([c for p in pairs for c in (p if order == "longer_first" else p[::-1])])
    assert X.read_block(12, 0, disc=4, part="sea4").name == "Block[12][0] sea4"
    assert X.read_block(12, 0, disc=4, part="sea4f").name == "Block[12][0] sea4f"
    assert X.read_block(19, 11, disc=1, part="river").name == "Block[19][11] river"
    assert X.read_block(19, 11, disc=1, part="RiverJoint").name == "Block[19][11] riverjoint"
    assert sorted(decoded) == sorted([_SEA4, _SEA4F, _RIVER, _JOINT])   # each decoded once, from its OWN container


def test_read_block_missing_part_raises_not_its_prefix_sibling(fake_layer):
    """(16,15): RiverJoint but no River. The old rule answered ``river`` with RiverJoint; every caller's
    "block lacks this part" path keys on ValueError("mesh not found") (transplant.world_tris matches the
    message text), so that is what an absent part must raise."""
    install, decoded = fake_layer
    install([f"{_PFX}/disc1/0_1/r15/block[16][15] riverjoint.asset"])
    with pytest.raises(ValueError, match="mesh not found"):
        X.read_block(16, 15, disc=1, part="river")
    assert decoded == []
    assert X.read_block(16, 15, disc=1, part="riverjoint").name == "Block[16][15] riverjoint"


def test_read_block_memo_and_copy_semantics_survive(fake_layer):
    """The per-env decode memo still keys on the requested part: a repeat read is a memo hit (no second
    decode) and hands back an independent copy; sibling parts never share a memo slot."""
    install, decoded = fake_layer
    install([_SEA4F, _SEA4])
    a = X.read_block(12, 0, disc=4, part="sea4")
    a.verts[0][1] = 99.0                                     # mutate the returned copy in place
    b = X.read_block(12, 0, disc=4, part="sea4")
    assert decoded == [_SEA4]                                # memo hit: decoded once
    assert b.verts[0][1] == 0.0 and b is not a               # the master was not poisoned
    assert X.read_block(12, 0, disc=4, part="sea4f").name == "Block[12][0] sea4f"
    assert decoded == [_SEA4, _SEA4F]


def test_duplicate_container_still_resolves_first_in_objects_order(fake_layer):
    install, _decoded = fake_layer
    env = install([_SEA4, _SEA4F, _SEA4])
    from ff9mapkit.extract import env_lock
    with env_lock:
        assert X._find_block_part(env, 4, "0_1", 12, 0, "sea4") is env.objects[0]


# --------------------------------------------------------------------------- the real install
_needs_install = pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")


@_needs_install
@pytest.mark.parametrize("disc, xy", [(1, (19, 11)), (4, (5, 16))])
def test_real_river_is_river_not_riverjoint(disc, xy):
    river = X.read_block(*xy, disc=disc, part="river")
    assert "River" in river.name and "RiverJoint" not in river.name, river.name
    assert X.read_block(*xy, disc=disc, part="riverjoint").name.endswith("RiverJoint")


@_needs_install
def test_real_disc4_sea4_is_not_sea4f():
    sea4 = X.read_block(12, 0, disc=4, part="sea4")
    assert sea4.name == "Block[12][0] Sea4", sea4.name
    assert X.read_block(12, 0, disc=4, part="sea4f").name == "Block[12][0] Sea4f"


@_needs_install
@pytest.mark.parametrize("disc", [1, 4])
def test_real_block_without_river_raises(disc):
    with pytest.raises(ValueError, match="mesh not found"):
        X.read_block(16, 15, disc=disc, part="river")


@_needs_install
def test_every_real_block_container_resolves_to_itself():
    """Sweep: each worldmap block container in the bundle is the one read_block's lookup picks for its own
    (disc, lod, x, y, part) -- the property D4-17 broke at 3 of 2178. Lookup only, no decode."""
    from ff9mapkit.extract import env_lock
    pat = re.compile(r"worldmap/disc(\d+)/([0-9_]+)/r(\d+)/block\[(\d+)\]\[(\d+)\] ([a-z0-9_]+)\.asset$")
    env = X._worldmap_env(1)
    with env_lock:
        idx = X._mesh_index(env)
        swept, wrong = 0, []
        for c, o in idx.items():
            m = pat.search(c)
            if not m:
                continue
            d, lod, _r, x, y, part = m.groups()
            swept += 1
            if X._find_block_part(env, int(d), lod, int(x), int(y), part) is not o:
                wrong.append(c)
    assert swept > 2000 and wrong == []
