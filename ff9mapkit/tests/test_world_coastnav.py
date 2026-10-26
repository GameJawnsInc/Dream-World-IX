"""Coast-nav stamp plumbing: the synthetic-namespace loader guard + the worldmap-env negative memo.

THE 928-LOAD PROFILE (2026-07-30): a coast-nav stamp on Disc9 spent 97% of its 169s/cell inside
UnityPy, because ``_Loader.parts`` fell through ``read_block_stacked``'s stock fallback on a disc no
bundle serves, and ``_worldmap_env`` memoized only WINNERS -- every miss rescanned all ~50 p0data
bundles. Two guards fixed it (169s/cell -> ~0.2s/cell, results byte-identical per the Disc9 gate
probe); these tests pin both so neither silently regresses.
"""
from __future__ import annotations

import struct

import pytest

from ff9mapkit.world import coastnav as CN
from ff9mapkit.world import discmirror as DM
from ff9mapkit.world import extract as WX


def _mesh_bytes(topo: int = 57) -> bytes:
    """A minimal F9WM sea mesh: 3 verts, 1 tri, tangents present (flags=4)."""
    verts = [(0.0, 0.0, 0.0), (8.0, 0.0, 0.0), (0.0, 0.0, -8.0)]
    out = bytearray()
    out += b"F9WM" + struct.pack("<iiii", 1, 3, 3, 4)
    for v in verts:
        out += struct.pack("<3f", *v)
    for _ in verts:
        out += struct.pack("<4f", float(topo << 2), 0.0, 0.0, 0.0)
    out += struct.pack("<3i", 0, 1, 2)
    return bytes(out)


def test_synthetic_loader_never_touches_the_stock_fallback(monkeypatch, tmp_path):
    """On a synthetic disc the loader reads deployed overrides ONLY -- the stacked read's stock
    fallback (a full p0data rescan per missing part) must be unreachable."""
    from ff9mapkit import config
    from ff9mapkit.world import entrance as EN
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)

    def _boom(*a, **k):
        raise AssertionError("stock fallback reached on a synthetic namespace")

    monkeypatch.setattr(EN, "read_block_stacked", _boom)
    monkeypatch.setattr(WX, "read_block", _boom)
    p = tmp_path / "MOD" / "FF9_Data" / "WorldMap" / "Disc9" / "0_1" / "r10" / "Block[12][10] Sea4.ff9mesh"
    p.parent.mkdir(parents=True)
    p.write_bytes(_mesh_bytes())
    loader = CN._Loader("MOD", 9)
    parts = loader.parts(12, 10)
    assert [nm for nm, _, _ in parts] == ["Sea4"], "the deployed override must load, nothing else"
    assert loader.parts(11, 10) == [], "a cell with no override is empty, not a stock read"


def test_real_disc_loader_still_uses_the_stacked_read(monkeypatch):
    """Disc 1/4 keep the override-over-stock stacked semantics -- and scan exactly the
    engine's one registration order (audit rec 11: the local PARTS_ORDER copy is gone)."""
    from ff9mapkit.world import entrance as EN
    from ff9mapkit.world import placement as P
    calls = []
    monkeypatch.setattr(EN, "read_block_stacked",
                        lambda mod, x, y, **k: calls.append((x, y, k["part"], k["disc"])) or None)
    assert CN._Loader("MOD", 1).parts(5, 5) == []
    assert [c[2] for c in calls] == [p.lower() for p in P.REGISTRATION_ORDER]
    assert all(c[3] == 1 for c in calls)


def test_worldmap_env_memoizes_the_negative(monkeypatch, tmp_path):
    """A disc with no winning bundle pays the full bundle scan ONCE per process, not per call."""
    (tmp_path / "p0data3.bin").write_bytes(b"")     # a bundle the listing sees, so the miss is the full scan's
    monkeypatch.setattr(WX, "_streaming_assets", lambda game=None: tmp_path)
    monkeypatch.setattr(WX, "_unitypy", lambda: None)
    scans = []
    monkeypatch.setattr(WX, "_bundles", lambda game=None: scans.append(1) or [])
    WX._WM_ENV_MEMO.clear()
    with pytest.raises(ValueError):
        WX._worldmap_env(disc=9)
    with pytest.raises(ValueError):
        WX._worldmap_env(disc=9)
    assert len(scans) == 1, "the second miss must come from the memo, not another rescan"
    WX._WM_ENV_MEMO.clear()


# --------------------------------------------------------------------------- THE DISC-4 MIRROR (operators F6)
# world-coastnav restamped the disc it was given and copied to Disc4 only under --mirror-disc (opt-in because the
# verb was built for Path D's Disc9, not because disc 4's water differs), and the [[coastnav]] fuse row never
# passed it -- so sealing disc 1's cliffs left disc 4 sailable. These run the REAL stamp over a deployed cell
# under a tmp game root: a 16u land pad (y 3, high) over a full-cell Sea4 plane. Stock reads are stubbed empty
# and both discs read as open ocean for the mirror's cell gate.

CN_BLK = (20, 1)
CN_SEA = f"Block[{CN_BLK[0]}][{CN_BLK[1]}] Sea4.ff9mesh"
CN_LAND = f"Block[{CN_BLK[0]}][{CN_BLK[1]}] Terrain.ff9mesh"


def _tiles(name, tiles, *, y, topo, disc):
    """Two UP-FACING tris per 4u tile (the ground query drops a down-facing one)."""
    from ff9mapkit.world import rimretile as RR
    from ff9mapkit.world.extract import encode_id
    t = (float(encode_id(topograph=topo)), 0.0, 0.0, 1.0)
    tris = []
    for (i, j) in tiles:
        x0, x1, z0, z1 = i * 4.0, i * 4.0 + 4, -j * 4.0, -j * 4.0 - 4
        for corners in (((x0, z0), (x1, z0), (x0, z1)), ((x1, z0), (x1, z1), (x0, z1))):
            tris.append([((x, y, z), (0.0, 1.0, 0.0), (0.5, 0.5), t) for (x, z) in corners])
    return RR.build_part(tris, name, *CN_BLK, disc)


def _deploy_coast(wm, disc):
    from ff9mapkit.world import mesh as M
    d = wm / f"Disc{disc}" / "0_1" / f"r{CN_BLK[1]}"
    M.write_ff9mesh(_tiles("Terrain", [(i, j) for i in range(6, 10) for j in range(6, 10)],
                           y=3.0, topo=0, disc=disc), d / CN_LAND)
    M.write_ff9mesh(_tiles("Sea4", [(i, j) for i in range(16) for j in range(16)],
                           y=0.0, topo=57, disc=disc), d / CN_SEA)
    return d


@pytest.fixture
def coast(tmp_path, monkeypatch):
    """The coast on Disc1 plus the byte-identical Disc4 copy its writer's auto-mirror left. Returns
    ``(disc1_dir, disc4_dir, pre_bytes, backup_dir)``."""
    from ff9mapkit import config

    def _no_stock(*a, **k):
        raise ValueError("mesh not found")
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    monkeypatch.setattr(WX, "read_block", _no_stock)
    monkeypatch.setattr(DM, "_real_parts", lambda disc, lod="0_1", game=None: {})
    wm = tmp_path / "MOD" / "FF9_Data" / "WorldMap"
    d1 = _deploy_coast(wm, 1)
    d4 = wm / "Disc4" / "0_1" / f"r{CN_BLK[1]}"
    d4.mkdir(parents=True)
    pre = {}
    for name in (CN_LAND, CN_SEA):
        pre[name] = (d1 / name).read_bytes()
        (d4 / name).write_bytes(pre[name])
    return d1, d4, pre, tmp_path / "bk"


@pytest.mark.parametrize("mirror_disc", [None, 4], ids=["auto", "legacy-lockstep"])
def test_stamp_mirrors_the_restamped_cell_to_disc4(coast, mirror_disc):
    """THE BREAK-IT: before the wiring, a plain stamp sealed Disc1 and left Disc4's water unstamped (sailable)."""
    d1, d4, pre, bk = coast
    s = CN.stamp("MOD", cells=[CN_BLK], deploy=True, backup_dir=bk, mirror_disc=mirror_disc)
    assert s["totals"].get(CN.KEEL), s["totals"]                  # the pad keeled the water under it
    assert (d1 / CN_SEA).read_bytes() != pre[CN_SEA], "the stamp changed nothing -- the check is void"
    assert (d4 / CN_SEA).read_bytes() == (d1 / CN_SEA).read_bytes(), "Disc4's water was left unstamped"
    assert (d1 / CN_LAND).read_bytes() == pre[CN_LAND] == (d4 / CN_LAND).read_bytes()
    assert str(d1 / CN_SEA) in s["written"] and s["mirror"]["skipped"] == []


@pytest.mark.parametrize("skip", [True, DM.DEFERRED], ids=["skip-mirror", "deferred"])
def test_stamp_skip_mirror_leaves_disc4_alone(coast, skip):
    """``--skip-mirror``, and DEFERRED (world-island's emitter: the island runs the one pass over its writes)."""
    d1, d4, pre, bk = coast
    s = CN.stamp("MOD", cells=[CN_BLK], deploy=True, backup_dir=bk, skip_mirror=skip)
    assert s["written"] and s["mirror"] is None
    assert (d1 / CN_SEA).read_bytes() != pre[CN_SEA]
    assert (d4 / CN_SEA).read_bytes() == pre[CN_SEA]


def test_stamp_dry_run_writes_nothing(coast):
    d1, d4, pre, bk = coast
    s = CN.stamp("MOD", cells=[CN_BLK], deploy=False, backup_dir=bk)
    assert s["cells"] and "written" not in s and "mirror" not in s     # it measured, it wrote nothing
    for name, data in pre.items():
        assert (d1 / name).read_bytes() == data == (d4 / name).read_bytes()
    assert not bk.exists()


def test_stamp_on_a_synthetic_disc_never_reaches_disc4(tmp_path, monkeypatch, capsys):
    """Why --mirror-disc was opt-in: Path D's Disc9 must have no path into a real disc. The auto-mirror keeps that
    -- it refuses a synthetic namespace by itself, before any bundle read."""
    from ff9mapkit import config

    def _boom(*a, **k):
        raise AssertionError("a real-disc read on a synthetic-namespace stamp")
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    monkeypatch.setattr(WX, "read_block", _boom)
    monkeypatch.setattr(DM, "_real_parts", _boom)
    wm = tmp_path / "MOD" / "FF9_Data" / "WorldMap"
    d9 = _deploy_coast(wm, 9)
    pre = (d9 / CN_SEA).read_bytes()
    s = CN.stamp("MOD", disc=9, cells=[CN_BLK], deploy=True, backup_dir=tmp_path / "bk")
    assert s["written"] and (d9 / CN_SEA).read_bytes() != pre
    assert sorted(p.name for p in wm.iterdir()) == ["Disc9"]
    assert "refused for Disc9" in capsys.readouterr().out


def test_world_coastnav_cli_threads_skip_mirror(monkeypatch):
    from ff9mapkit import cli
    seen = []
    monkeypatch.setattr(CN, "stamp", lambda mf, **k: seen.append(k) or {"cells": [], "disc": k["disc"]})
    for argv, want in ((["--skip-mirror"], True), ([], False)):
        assert cli.main(["world-coastnav", "--mod-folder", "MOD", *argv]) == 0
        assert seen[-1]["skip_mirror"] is want and seen[-1]["mirror_disc"] is None
