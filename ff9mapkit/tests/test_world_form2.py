"""FORM 2: world-terrain / world-deploy --form 2 edit a switchable cell's alternate ground (terrain study defect 19).

On the 26 cells that switch with a story place a kit `Terrain` edit is form 1 only: in game (RESULTS section 20) it
vanished the moment Black Mage Village switched, and a `Terrain2` beside it kept the edit. No verb wrote a Terrain2;
`--form 2` does. It reads the cell's deployed Terrain2 (else stock 0_2), pins it to what form 2 renders (the shared
water, Object2 -- never the form-1 Object), holds every cell outside the place at its border, refuses an edit across
two places, writes `Terrain2`, and never copies to disc 4 (disc 4's form 2 differs from disc 1's on 5 of 20 cells):
it replays there for the two flag places and skips the disc-1 places, which never switch on disc 4.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import warnings

import pytest

from ff9mapkit import cli, config
from ff9mapkit.world import discmirror as DM, extract as X, mesh as M, terrain as T

BMV = (22, 14)                                       # Black Mage Village: a disc-1 place; (23,14) does not switch
CHOCO = (16, 14)                                     # Chocobo's Paradise: a flag place, switches on disc 4 too


def _mesh(tris, name, x, y, disc=1):
    from ff9mapkit.world.extract import BlockMesh, CH_POS, CH_NRM, CH_UV, CH_TAN
    pos = [list(c) for t in tris for c in t]
    n = len(pos)
    return BlockMesh(name=name, disc=disc, x=x, y=y, lod="0_1", vcount=n, stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: [[0.0, 1.0, 0.0]] * n, CH_UV: [[0.5, 0.5]] * n,
                                  CH_TAN: [[0.0, 0.0, 0.0, 1.0]] * n},
                     flat_index=list(range(n)), tris=[[i, i + 1, i + 2] for i in range(0, n, 3)],
                     raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


def _terrain(x, y, h, part="Terrain", disc=1):
    tris = []
    for i in range(16):
        for j in range(16):
            x0, x1, z0, z1 = i * 4.0, (i + 1) * 4.0, -j * 4.0, -(j + 1) * 4.0
            for corners in ([(x0, z0), (x0, z1), (x1, z0)], [(x1, z0), (x0, z1), (x1, z1)]):
                tris.append([(px, h(px, pz), pz) for px, pz in corners])
    return _mesh(tris, f"Block[{x}][{y}] {part}", x, y, disc)


def form1_h(px, pz):
    return 3.0


def form2_h(px, pz):                                 # form 2 differs inside; borders match the neighbours' ground
    return 4.0 if 8 <= px <= 56 and -56 <= pz <= -8 else 3.0


def _tri_at(lx, lz, y, x, by, name):                 # a partner triangle whose first corner sits on a terrain vertex
    return _mesh([[(lx, y, lz), (lx + 1.0, y + 2.0, lz), (lx, y + 2.0, lz - 1.0)]], name, x, by)


@pytest.fixture
def world(tmp_path, monkeypatch):
    """(22,14) and (16,14) switchable, (23,14) a plain neighbour; both discs serve the same bytes. The form-1 Object
    of (22,14) touches its form-2 ground at local (36,-32); its Object2 at (28,-32)."""
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)

    def stock(bx, by, disc=1, lod="0_1", part="terrain", **k):
        if part == "terrain" and (bx, by) in (BMV, CHOCO, (23, 14), (15, 14), (17, 14), (16, 13), (16, 15),
                                               (22, 13), (22, 15), (21, 14)):
            return _terrain(bx, by, form2_h if lod == "0_2" and (bx, by) in (BMV, CHOCO) else form1_h, disc=disc)
        if (bx, by) == BMV and part == "object":
            return _tri_at(28.0 if lod == "0_2" else 36.0, -32.0, 4.0, bx, by, f"Block[{bx}][{by}] Object")
        raise ValueError("mesh not found")
    monkeypatch.setattr(X, "read_block", stock)
    written = []
    monkeypatch.setattr(M, "deploy_override", lambda bm, **k: written.append((copy.deepcopy(bm), k))
                        or tmp_path / f"{bm.name}.ff9mesh")

    def no_copy(*a, **k):
        raise AssertionError("a form-2 edit must never go through the disc-4 COPY")
    monkeypatch.setattr(DM, "auto_mirror", no_copy)
    return written


def _y(bm, lx, lz):
    return sorted({round(v[1], 4) for v in bm.verts if abs(v[0] - lx) < 1e-9 and abs(v[2] - lz) < 1e-9})


CENTRE = (BMV[0] * 64.0 + 32.0, -BMV[1] * 64.0 - 32.0)


def test_form2_edits_the_stock_form2_ground_and_writes_terrain2(world):
    s = T.reshape("MOD", at=CENTRE, radius=12.0, amount=3.0, form=2, seam_taper=0.0, skip_mirror=True)
    assert s["form"] == 2 and s["place"] == "BlackMageVillage" and [b["block"] for b in s["blocks"]] == [list(BMV)]
    (bm, k), = world
    assert k["part"] == "Terrain2" and k["disc"] == 1 and bm.name.endswith("Terrain2")
    assert _y(bm, 32.0, -32.0) == [7.0]                       # stock form 2 (4.0) + 3, not form 1's 3.0 + 3
    assert _y(bm, 60.0, -60.0) == [3.0]                       # outside the radius: untouched


def test_form2_pins_follow_the_form(world):
    """Object2 is welded to form 2 at (28,-32) and holds it; the form-1 Object at (36,-32) does not render in form
    2, so it must not hold anything."""
    T.reshape("MOD", at=CENTRE, radius=12.0, amount=3.0, form=2, seam_taper=0.0, skip_mirror=True)
    (bm, _k), = world
    assert _y(bm, 28.0, -32.0) == [4.0]                       # held by Object2
    assert _y(bm, 36.0, -32.0)[0] > 4.5                       # free: the form-1 Object is not a form-2 partner


def test_form2_holds_the_cells_outside_the_place_at_their_border(world):
    at = ((BMV[0] + 1) * 64.0, -BMV[1] * 64.0 - 32.0)        # on the (22,14)|(23,14) border
    s = T.reshape("MOD", at=at, radius=12.0, amount=3.0, form=2, seam_taper=0.0, skip_mirror=True)
    assert [b["block"] for b in s["blocks"]] == [list(BMV)] and s["stitch"]["torn"] == 0
    (bm, _k), = world
    assert _y(bm, 64.0, -32.0) == [3.0]                       # the shared border stays on (23,14)'s ground
    assert _y(bm, 60.0, -32.0)[0] > 3.5                       # one step in, the edit rises


def test_form2_reads_a_deployed_terrain2_first(world, monkeypatch, tmp_path):
    dep = tmp_path / "Block[22][14] Terrain2.ff9mesh"
    monkeypatch.setattr(M, "deployed_override", lambda mod, x, y, *, part="Terrain", **k:
                        dep if ((x, y), part) == (BMV, "Terrain2") else None)
    monkeypatch.setattr(M, "blockmesh_from_ff9mesh", lambda p, **k: _terrain(BMV[0], BMV[1], lambda a, b: 7.0,
                                                                             part="Terrain2"))
    s = T.reshape("MOD", at=CENTRE, radius=12.0, amount=1.0, form=2, seam_taper=0.0, skip_mirror=True)
    (bm, _k), = world
    assert _y(bm, 32.0, -32.0) == [8.0] and s["stacked_on"] == [str(dep)]


def test_form2_refuses_off_the_places_across_two_places_and_off_disc(world):
    with pytest.raises(ValueError, match="no such cell is within the radius"):
        T.reshape("MOD", at=(5 * 64.0 + 32, -5 * 64.0 - 32), radius=12.0, amount=1.0, form=2)
    with pytest.raises(ValueError, match="switch independently"):           # Fire Shrine (14,15) | Lindblum (14,16)
        T.reshape("MOD", at=(14 * 64.0 + 32, -16 * 64.0), radius=12.0, amount=1.0, form=2)
    with pytest.raises(ValueError, match="CLONE mode"):
        T.reshape("MOD", at=CENTRE, radius=12.0, amount=1.0, form=2, target_disc=9)
    with pytest.raises(ValueError, match="form must be 1"):
        T.reshape("MOD", at=CENTRE, radius=12.0, amount=1.0, form=3)
    assert world == []


def test_disc4_replays_a_flag_place_and_skips_a_disc1_place(world, capsys):
    T.reshape("MOD", at=CENTRE, radius=12.0, amount=1.0, form=2)
    assert [k["disc"] for _bm, k in world] == [1]
    assert "not needed -- BlackMageVillage switches on disc 1 only" in capsys.readouterr().out
    world.clear()
    at = (CHOCO[0] * 64.0 + 32.0, -CHOCO[1] * 64.0 - 32.0)
    T.reshape("MOD", at=at, radius=12.0, amount=1.0, form=2)
    assert [(k["disc"], k["part"]) for _bm, k in world] == [(1, "Terrain2"), (4, "Terrain2")]
    assert "ChocoboParadise switches on disc 4 too -- REPLAYING" in capsys.readouterr().out


def test_world_terrain_and_world_deploy_carry_form_2(world, monkeypatch, capsys):
    ns = cli.build_parser().parse_args(["world-terrain", "--mod-folder", "MOD", "--radius", "12", "--at",
                                        str(CENTRE[0]), str(CENTRE[1]), "--raise", "2", "--form", "2",
                                        "--skip-mirror"])
    assert ns.form == 2 and cli._cmd_world_terrain(ns) == 0
    out = capsys.readouterr().out
    assert "reshaped BlackMageVillage's FORM-2 ground (Terrain2)" in out and "form 2 shows only while" in out
    seen = {}
    monkeypatch.setattr(T, "reshape", lambda mod, **k: seen.update(k) or
                        {"op": "raise", "radius": k["radius"], "blocks": [{"block": list(BMV), "moved": 1}],
                         "skipped_sea": [], "form": 2, "place": "BlackMageVillage"})
    dns = cli.build_parser().parse_args(["world-deploy", "--mod-folder", "MOD", "--block", "22", "14", "--hill", "3",
                                         "--radius", "12", "--form", "2"])
    assert cli._cmd_world_deploy(dns) == 0
    assert seen["form"] == 2 and seen["at"] == CENTRE and seen["amount"] == 3.0 and seen["flatten"] is False
    bad = cli.build_parser().parse_args(["world-deploy", "--mod-folder", "MOD", "--block", "22", "14", "--lift", "2",
                                         "--form", "2"])
    assert cli._cmd_world_deploy(bad) == 2 and "--form 2 reshapes a place's alternate ground" in capsys.readouterr().err
    lod = cli.build_parser().parse_args(["world-deploy", "--mod-folder", "MOD", "--block", "22", "14", "--hill", "3",
                                         "--lod", "0_2"])
    assert cli._cmd_world_deploy(lod) == 2 and "use --form 2" in capsys.readouterr().err


def _need_install() -> None:
    try:
        import UnityPy  # noqa: F401
        ok = (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        ok = False
    if not ok:
        warnings.warn("FORM 2 went unchecked on real data in this run: no FF9 install + UnityPy. Re-run in the MAIN "
                      "repo (C:/gd/Dream-World-IX/ff9mapkit).", UserWarning)
        pytest.skip("needs the FF9 install + UnityPy (see the warnings summary)")


def test_real_bmv_form2_flatten_is_the_terrain2_walked_in_game(monkeypatch):
    """The kit's form-2 flatten at Black Mage Village is byte-equal to the Terrain2 terrain study round 1 built by hand
    (stock 0_2 + flatten_region) and rounds 1 and 5 walked in game."""
    _need_install()
    got = []
    monkeypatch.setattr(M, "deploy_override", lambda bm, **k: got.append((bm, k)) or None)
    s = T.reshape("FF9CustomMap_test_nonexistent", at=(1440.0, -928.0), radius=12.0, flatten=True, height=26.0,
                  form=2, skip_mirror=True)
    assert s["stitch"]["torn"] == 0 and [b["block"] for b in s["blocks"]] == [[22, 14]]
    (bm, k), = got
    ref = X.read_block(22, 14, disc=1, lod="0_2", part="terrain")
    M.flatten_region(ref, radius=12.0, center=(1440.0, -928.0), height=26.0, world_origin=X.block_world_origin(22, 14))
    assert k["part"] == "Terrain2"
    assert hashlib.sha256(M.ff9mesh_bytes(bm)).digest() == hashlib.sha256(M.ff9mesh_bytes(ref)).digest()
