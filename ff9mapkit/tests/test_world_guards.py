"""THE ENTRANCE GUARD, THE MORPH STITCH GATE and COLLISION-PROOF BACKUPS (terrain study defects 6, 10-11, 12).

* Defect 6: only world-deploy refused to move an entrance block's ground (a hill at Dali soft-locked the player at
  the field exit in game, commit 3e388d0d); world-terrain and world-transplant --in-place did it silently (study S8).
  ``mesh.entrance_guard`` is now the one rule for all three, and it judges the blocks the edit actually changes.
* Defects 10-11: VertexDisplace keeps a weld whole only across the parts ``morph_in_place`` loads, so a 1u tear
  against an Object passed every gate (study S10). The morph now runs ``mesh.stitch_gate`` over every part the cell
  carries.
* Defect 12: two parks in one wall-clock second shared a ``.bak-<ts>`` name and the second overwrote the first (5/5
  in the study's S11). ``mesh.park_backup`` adds ``-2``, ``-3``, ... and creates exclusively.

Hermetic: every game root is ``tmp_path``; stock reads are stubbed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta

import pytest

from ff9mapkit import cli, config
from ff9mapkit.world import discmirror as DM, extract as X, mesh as M, terrain as T, transplant as TR

BLK = (16, 14)
AT = (1054.0, -951.0)                      # inside BLK: local (30, -55)
OX, OZ = X.block_world_origin(*BLK)


def _flat_block(y=3.0, event_near=None):
    """Block[16][14] Terrain: a 16x16 grid of 4u cells at height ``y``; tris whose centroid lies within 6u of the
    block-local ``event_near`` carry event 1 (a kit entrance's trigger tiles)."""
    from ff9mapkit.world.extract import BlockMesh, encode_id, CH_POS, CH_NRM, CH_UV, CH_TAN
    pos, nrm, uv, tan, tris = [], [], [], [], []
    for i in range(16):
        for j in range(16):
            x0, x1, z0, z1 = i * 4.0, (i + 1) * 4.0, -j * 4.0, -(j + 1) * 4.0
            for corners in ([(x0, z0), (x0, z1), (x1, z0)], [(x1, z0), (x0, z1), (x1, z1)]):
                cx, cz = sum(c[0] for c in corners) / 3, sum(c[1] for c in corners) / 3
                ev = 1 if event_near and (cx - event_near[0]) ** 2 + (cz - event_near[1]) ** 2 < 36 else 0
                idall = float(X.encode_id(ev, 14, 0))
                base = len(pos)
                for (x, z) in corners:
                    pos.append([x, y, z]); nrm.append([0.0, 1.0, 0.0]); uv.append([0.5, 0.5])
                    tan.append([idall, 0.0, 0.0, 1.0])
                tris.append([base, base + 1, base + 2])
    n = len(pos)
    return BlockMesh(name="Block[16][14] Terrain", disc=1, x=BLK[0], y=BLK[1], lod="0_1", vcount=n, stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan}, flat_index=list(range(n)),
                     tris=tris, raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


@pytest.fixture
def world(tmp_path, monkeypatch):
    """A tmp game root; stock = a flat Block[16][14] Terrain, every other block/part absent; no mirror."""
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)

    def stock(bx, by, part="terrain", **k):
        if (bx, by) != BLK or part != "terrain":
            raise ValueError("mesh not found")
        return _flat_block()
    monkeypatch.setattr(X, "read_block", stock)
    monkeypatch.setattr(DM, "auto_mirror", lambda *a, **k: None)
    return tmp_path


def _deploy(bm):
    return M.deploy_override(bm, mod_folder="MOD", part="Terrain")


# ---- the guard itself ------------------------------------------------------------------------------------------------

def _rows(bm, dy_at=None, dy=2.0):
    pre = M.world_positions(bm, (OX, OZ))
    post = [((p[0], p[1] + dy, p[2]) if dy_at and abs(p[0] - dy_at[0]) < 1e-6 and abs(p[2] - dy_at[1]) < 1e-6
             else p) for p in pre]
    return (BLK, M.bm_tiles(bm, pre, post))


def _tile_corners(bm):
    return [p for i, ps, _q in M.bm_tiles(bm, M.world_positions(bm, (OX, OZ))) if X.decode_id(i)["event"]
            for p in ps]


def test_guard_ignores_a_block_the_edit_leaves_alone():
    bm = _flat_block(event_near=(30.0, -30.0))
    assert M.entrance_guard([_rows(bm)]) == []                      # entrance tiles, but no ground moved


def test_guard_ignores_moved_ground_without_entrance_tiles():
    assert M.entrance_guard([_rows(_flat_block(), dy_at=(OX + 8.0, OZ - 8.0))]) == []


def test_guard_allows_moved_ground_far_from_the_tiles():
    # the same block, 26u from its entrance tiles: where a field exit sets the player down is untouched
    bm = _flat_block(event_near=(30.0, -30.0))
    assert M.entrance_guard([_rows(bm, dy_at=(OX + 4.0, OZ - 4.0))]) == []


def test_guard_refuses_raised_ground_within_the_clearance():
    bm = _flat_block(event_near=(30.0, -30.0))
    corner = min(_tile_corners(bm), key=lambda p: (p[0], -p[2]))   # the tiles' north-west corner
    node = (corner[0] - 4.0, corner[2] + 4.0)                       # one lattice step out on both axes: 5.66u
    rows = _rows(bm, dy_at=node)                                    # raised 2u: past the 1.17u a landing finds
    with pytest.raises(ValueError, match=r"REFUSED: this edit raises the ground where a field exit sets the player "
                                         r"down \(more than 1\.17u within 8u of a place-ENTRANCE\) or drops an "
                                         r"entrance tile -- \[16\]\[14\] ground raised 2u 5\.7u from an entrance "
                                         r"tile \(area\(s\) \[14\]\)"):
        M.entrance_guard([rows])
    hits = M.entrance_guard([rows], allow=True)
    assert hits[0]["block"] == [16, 14] and hits[0]["tiles_moved"] == 0 and not hits[0]["door_arrival"]
    assert hits[0]["max_rise"] == 2.0 and hits[0]["refused"]
    far = (corner[0] - 8.0, corner[2] + 8.0)                        # two steps out: 11.3u, clear
    assert M.entrance_guard([_rows(bm, dy_at=far)]) == []


def test_guard_allows_a_small_raise_and_any_lowering_near_the_tiles():
    bm = _flat_block(event_near=(30.0, -30.0))
    corner = min(_tile_corners(bm), key=lambda p: (p[0], -p[2]))
    node = (corner[0] - 4.0, corner[2] + 4.0)
    assert M.entrance_guard([_rows(bm, dy_at=node, dy=1.0)]) == []          # the landing still finds the ground
    assert M.entrance_guard([_rows(bm, dy_at=node, dy=-6.0)]) == []         # the player drops: legal


def test_guard_reports_a_moved_tile_and_refuses_a_raised_or_dropped_one():
    bm = _flat_block(event_near=(30.0, -30.0))
    tile_node = (OX + 28.0, OZ - 28.0)
    for dy in (0.5, -3.0):                                           # the trigger still fires, the landing still finds
        hits = M.entrance_guard([_rows(bm, dy_at=tile_node, dy=dy)])
        assert hits[0]["tiles_moved"] > 0 and hits[0]["max_rise"] is None and not hits[0]["refused"]
    with pytest.raises(ValueError, match=r"ground raised 2u 0u from an entrance tile"):
        M.entrance_guard([_rows(bm, dy_at=tile_node, dy=2.0)])        # a raised tile is its own landing point
    cell, tris = _rows(bm)
    dropped = [(i, pre, None if X.decode_id(i)["event"] else post) for i, pre, post in tris]
    with pytest.raises(ValueError, match=r"\[16\]\[14\] \d+ entrance tile\(s\) dropped"):
        M.entrance_guard([(cell, dropped)])                          # its trigger would be gone


def test_guard_sees_a_tile_across_the_block_border():
    # the edit's block has no tiles; its neighbour's tile corner sits 4u away (an unchanged row lends it)
    edit = _rows(_flat_block(), dy_at=(OX + 60.0, OZ - 32.0))
    pts = ((OX + 64.0, 3.0, OZ - 32.0), (OX + 68.0, 3.0, OZ - 32.0), (OX + 64.0, 3.0, OZ - 36.0))
    hits = M.entrance_guard([edit, ((17, 14), [(int(X.encode_id(1, 14, 0)), pts, pts)])], allow=True)
    assert [h["block"] for h in hits] == [[16, 14]] and hits[0]["nearest"] == 4.0


def test_guard_refuses_near_a_door_arrival():
    edit = _rows(_flat_block(), dy_at=(OX + 20.0, OZ - 20.0))
    hits = M.entrance_guard([edit], arrivals=[(OX + 23.0, OZ - 24.0)], allow=True)
    assert hits[0]["door_arrival"] and hits[0]["nearest"] == 5.0 and hits[0]["areas"] == []
    with pytest.raises(ValueError, match="from a door arrival"):
        M.entrance_guard([edit], arrivals=[(OX + 23.0, OZ - 24.0)])
    assert M.entrance_guard([edit], arrivals=[(OX + 40.0, OZ - 40.0)]) == []


# ---- world-terrain, world-deploy, the in-place morph ---------------------------------------------------------------

NEAR = (OX + 30.0, OZ - 42.0)              # a hill whose 12u radius reaches the (30, -30) tiles


def test_reshape_refuses_near_an_entrance_and_writes_nothing(world):
    dep = _deploy(_flat_block(event_near=(30.0, -30.0)))
    before = dep.read_bytes()
    with pytest.raises(ValueError, match="place-ENTRANCE"):
        T.reshape("MOD", at=NEAR, radius=12.0, amount=2.0)
    assert dep.read_bytes() == before                                # refused before the first write
    s = T.reshape("MOD", at=NEAR, radius=12.0, amount=2.0, allow_entrances=True)
    assert [h["block"] for h in s["entrances"]] == [[16, 14]] and dep.read_bytes() != before


def test_reshape_away_from_the_entrance_passes(world):
    dep = _deploy(_flat_block(event_near=(8.0, -8.0)))              # the block's tiles, 40u+ from the hill
    s = T.reshape("MOD", at=AT, radius=12.0, amount=2.0)
    assert s["entrances"] == [] and s["blocks"] and _events(dep) > 0


def test_reshape_of_a_plain_block_reports_no_entrances(world):
    s = T.reshape("MOD", at=AT, radius=12.0, amount=2.0)
    assert s["entrances"] == [] and s["blocks"]


def _events(path):
    d = M.read_ff9mesh(path)
    return sum(1 for i in range(0, len(d["indices"]), 3)
               if X.decode_id(int(round(d["tangents"][d["indices"][i]][0])))["event"])


def _deploy_ns(**kw):
    ns = dict(block=None, cluster=None, disc=1, lod="0_1", mod_folder="MOD", hill=2.0, crater=0.0, flatten=False,
              height=None, radius=12.0, center=list(AT), falloff="smooth", no_normals=False, allow_entrances=False,
              spike=0.0, lift=0.0, skip_mirror=True, game=None, fresh=False, allow_overwrite=False)
    ns.update(kw)
    return argparse.Namespace(**ns)


def test_world_deploy_uses_the_shared_guard(world, monkeypatch, capsys):
    monkeypatch.setattr(X, "list_blocks", lambda **k: [BLK])
    dep = _deploy(_flat_block(event_near=(30.0, -30.0)))
    before = dep.read_bytes()
    assert cli._cmd_world_deploy(_deploy_ns(center=list(NEAR))) == 2
    err = capsys.readouterr().err
    assert "REFUSED: this edit raises the ground where a field exit sets the player down" in err
    assert "-- [16][14] " in err
    assert dep.read_bytes() == before
    assert cli._cmd_world_deploy(_deploy_ns(center=list(NEAR), allow_entrances=True)) == 0
    out = capsys.readouterr().out
    assert "in block [16][14] -- --allow-entrances" in out and dep.read_bytes() != before


def test_world_terrain_cli_flag(world, capsys):
    _deploy(_flat_block(event_near=(30.0, -30.0)))
    base = ["world-terrain", "--mod-folder", "MOD", "--at", str(NEAR[0]), str(NEAR[1]), "--radius", "12", "--raise",
            "2", "--skip-mirror"]
    assert cli.main(base) == 2 and "place-ENTRANCE" in capsys.readouterr().err
    assert cli.main(base + ["--allow-entrances"]) == 0
    assert "in block [16][14] -- --allow-entrances" in capsys.readouterr().out


def _soup_quad(x0, z0, y, *, part_idall=0.0, size=4.0):
    """Two world-space tris over the 4u cell at block-local (x0, z0): an Object/beach patch welded to the grid."""
    c = [(x0 + OX, y, z0 + OZ), (x0 + OX, y, z0 - size + OZ), (x0 + size + OX, y, z0 + OZ),
         (x0 + size + OX, y, z0 - size + OZ)]
    v = lambda p: (p, (0.0, 1.0, 0.0), (0.0, 0.0), (part_idall, 0.0, 0.0, 1.0))   # noqa: E731
    return [[v(c[0]), v(c[1]), v(c[2])], [v(c[2]), v(c[1]), v(c[3])]]


@pytest.fixture
def morph_cell(world, monkeypatch):
    """Stock (16,14): the flat Terrain, plus an Object and a Beach1 patch, each welded to Terrain grid nodes."""
    parts = {"terrain": TR._soup(_flat_block(), *BLK), "object": _soup_quad(20.0, -20.0, 3.0),
             "beach1": _soup_quad(40.0, -40.0, 3.0)}
    monkeypatch.setattr(TR, "world_tris", lambda bx, by, part, **k: list(parts.get(part, ()))
                        if (bx, by) == BLK else [])
    return parts


def _displace(local_xz, y=3.0, dy=1.0, expected=6):
    return TR.VertexDisplace(moves={(local_xz[0] + OX, y, local_xz[1] + OZ): (0.0, dy, 0.0)}, expected=expected)


def test_morph_entrance_gate_allows_lowering_near_the_tiles(morph_cell, world):
    _deploy(_flat_block(event_near=(30.0, -30.0)))
    s = TR.morph_in_place("MOD", cell=BLK, tweaks=[_displace((32.0, -40.0), dy=-2.0)], parts=("terrain",),
                          dry_run=True)
    assert not any(g["gate"] == "entrance" for g in s["gates"]) and s["clean"]


def test_morph_stitch_gate_catches_the_object_tear(morph_cell):
    # the study's S10 case: a Terrain node welded to an Object (not a loaded part) moved 1u -- clean pre-fix
    s = TR.morph_in_place("MOD", cell=BLK, tweaks=[_displace((24.0, -24.0))], parts=("terrain",), dry_run=True)
    g = next(g for g in s["gates"] if g["gate"] == "stitch")
    assert not g["ok"] and g["torn"] == 1 and g["max_sep"] == 1.0 and "Block[16][14] Object" in g["by_mesh"]
    assert not s["clean"]


def test_morph_stitch_gate_passes_a_weld_that_moves_as_one(morph_cell):
    # Beach1 IS loaded: VertexDisplace moves every loaded instance of the key together (expected 6 Terrain + 1 Beach1)
    s = TR.morph_in_place("MOD", cell=BLK, tweaks=[_displace((44.0, -44.0), expected=7)],
                          parts=("terrain", "beach1"), dry_run=True)
    g = next(g for g in s["gates"] if g["gate"] == "stitch")
    assert g["ok"] and g["torn"] == 0 and g["welds"] > 0 and s["clean"]


def test_morph_stitch_gate_refuses_the_deploy(morph_cell, world):
    s = TR.morph_in_place("MOD", cell=BLK, tweaks=[_displace((24.0, -24.0))], parts=("terrain",))
    assert not s["clean"] and s["deployed"] == [] and not list(world.rglob("*.ff9mesh"))


def test_morph_entrance_gate(morph_cell, world):
    _deploy(_flat_block(event_near=(30.0, -30.0)))                   # a kit entrance on the cell
    s = TR.morph_in_place("MOD", cell=BLK, tweaks=[_displace((32.0, -40.0), dy=2.0)], parts=("terrain",),
                          dry_run=True)
    g = next(g for g in s["gates"] if g["gate"] == "entrance")
    assert not g["ok"] and g["blocks"][0]["block"] == [16, 14] and not s["clean"]
    s = TR.morph_in_place("MOD", cell=BLK, tweaks=[_displace((32.0, -40.0), dy=2.0)], parts=("terrain",),
                          dry_run=True, allow_entrances=True)
    assert next(g for g in s["gates"] if g["gate"] == "entrance")["ok"] and s["clean"]
    far = TR.morph_in_place("MOD", cell=BLK, tweaks=[_displace((8.0, -56.0), dy=2.0)], parts=("terrain",),
                            dry_run=True)
    assert not any(g["gate"] == "entrance" for g in far["gates"]) and far["clean"]   # 30u+ off: no gate row


def test_morph_entrance_gate_ignores_a_retexture(morph_cell, world):
    _deploy(_flat_block(event_near=(30.0, -30.0)))

    class Retex:                                                     # changes UVs only: the ground stays put
        part = "terrain"

        def apply(self, part, poly):
            return [(p, n, (0.25, 0.25), t) for (p, n, uv, t) in poly] if part == "terrain" else poly

        def emit(self):
            return []

        def gate(self):
            return {"gate": "retex", "ok": True}

        def census_inverse(self, x, z):
            return x, z
    s = TR.morph_in_place("MOD", cell=BLK, tweaks=[Retex()], parts=("terrain",), dry_run=True)
    assert not any(g["gate"] == "entrance" for g in s["gates"]) and s["clean"]


# ---- the carry stitch gate (transplant) -----------------------------------------------------------------------------

def test_stitch_gate_counts_a_deliberate_reweld_apart():
    pre = [(0.0, 0.0, 0.0)]
    rows = [("west", pre, pre), ("east", pre, [(4.0, 0.0, 0.0)])]            # a growth cut splits the weld by 4u
    assert M.stitch_gate(rows)["torn"] == 1
    g = M.stitch_gate(rows, rewelded={(0.0, 0.0, 0.0), (4.0, 0.0, 0.0)})   # its filler lands on both pieces
    assert g["torn"] == 0 and g["rewelded"] == 1
    assert M.stitch_gate(rows, rewelded={(0.0, 0.0, 0.0)})["torn"] == 1      # one piece left open: still torn


def _v(x, y, z, idall=12800.0):
    return ((float(x), float(y), float(z)), (0.0, 1.0, 0.0), (0.5, 0.5), (float(idall), 0.0, 0.0, 1.0))


def _wquad(x0, x1, z0, z1, *, y=0.0, idall=12800.0):
    a, b, c, d = _v(x0, y, z1, idall), _v(x1, y, z1, idall), _v(x1, y, z0, idall), _v(x0, y, z0, idall)
    return [[a, b, d], [b, c, d]]


@pytest.fixture
def carry_donor(monkeypatch):
    """Donor (1,1) (world x 64..128, z -128..-64): a terrain island, a Beach1 strip welded along its east edge, and an
    Object welded to its north-west corner (88, -88)."""
    blocks = {(1, 1, "terrain"): _wquad(88.0, 104.0, -104.0, -88.0),
              (1, 1, "beach1"): _wquad(104.0, 108.0, -104.0, -88.0),
              (1, 1, "sea4"): _wquad(64.0, 128.0, -128.0, -64.0, idall=232.0),
              (1, 1, "object"): _wquad(84.0, 88.0, -92.0, -88.0, idall=3836.0)}
    monkeypatch.setattr(TR, "world_tris", lambda bx, by, part, **k: [list(t) for t in blocks.get((bx, by, part), [])])
    return blocks


def _stitch(s):
    return next(g for g in s["gates"] if g["gate"] == "stitch")


def test_carry_stitch_gate_holds_a_verbatim_carry(carry_donor):
    g = _stitch(TR.transplant("MOD", cell=(4, 2), donor=(1, 1), dry_run=True, census_samples=8))
    assert g["ok"] and g["torn"] == 0 and g["welds"] > 0


def test_carry_stitch_gate_catches_a_one_part_displace(carry_donor):
    # a Terrain-only VertexDisplace on the Terrain|Beach1 weld: weld_audit cannot see a 1u split, the stitch gate can
    tw = TR.VertexDisplace(moves={(104.0, 0.0, -104.0): (0.0, 1.0, 0.0)}, expected=1, part="terrain")
    s = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), tweaks=[tw], dry_run=True, census_samples=8)
    g = _stitch(s)
    assert not g["ok"] and g["torn"] == 1 and g["max_sep"] == 1.0
    assert set(g["by_mesh"]) == {"carried Terrain", "carried Beach1"} and not s["clean"]
    assert [x["gate"] for x in s["gates"] if not x["ok"]] == ["stitch"]            # weld-audit is blind to it
    tw_all = TR.VertexDisplace(moves={(104.0, 0.0, -104.0): (0.0, 1.0, 0.0)}, expected=3)   # every part: one weld
    assert _stitch(TR.transplant("MOD", cell=(4, 2), donor=(1, 1), tweaks=[tw_all], dry_run=True,
                                 census_samples=8))["ok"]


def test_carry_stitch_gate_holds_the_prefab_object_where_it_renders(carry_donor):
    # rotated, the carried ground leaves the Object (the donor prefab renders it unrotated) -- the tear the
    # object-anchor gate refuses too; the stitch gate names the weld
    s = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), rot=90, dry_run=True, census_samples=8)
    g = _stitch(s)
    assert not g["ok"] and "prefab Object" in g["by_mesh"]
    assert not next(x for x in s["gates"] if x["gate"] == "object-anchor")["ok"]


# ---- collision-proof backups ---------------------------------------------------------------------------------------

def test_park_backup_never_reuses_a_name(tmp_path):
    dest = tmp_path / "Block[1][1] Terrain.ff9mesh"
    now = datetime.now()
    taken = []
    for s in (now, now + timedelta(seconds=1)):                      # this second and the next are both taken
        p = tmp_path / (dest.name + ".bak-" + s.strftime("%Y%m%d-%H%M%S"))
        p.write_bytes(b"EARLIER")
        taken.append(p)
    dest.write_bytes(b"V1")
    a = M.park_backup(dest)
    dest.write_bytes(b"V2")
    b = M.park_backup(dest)
    assert a != b and a.read_bytes() == b"V1" and b.read_bytes() == b"V2"
    assert all(p.read_bytes() == b"EARLIER" for p in taken)          # pre-fix: the second park overwrote these
    assert a.name.startswith(dest.name + ".bak-") and b.name.startswith(dest.name + ".bak-")


def test_deploy_override_keeps_every_overwritten_version(world):
    bms = [_flat_block(y=y) for y in (3.0, 4.0, 5.0)]
    dest = _deploy(bms[0])
    first = dest.read_bytes()
    _deploy(bms[1])
    second = dest.read_bytes()
    _deploy(bms[2])                                                  # three writes, usually inside one second
    parks = sorted(p for p in dest.parent.iterdir() if p.name.startswith(dest.name + ".bak-"))
    assert sorted(p.read_bytes() for p in parks) == sorted([first, second])
    assert M.existing_overrides([BLK], "MOD", disc=1) == [str(dest)]   # the parks stay invisible to the gates
