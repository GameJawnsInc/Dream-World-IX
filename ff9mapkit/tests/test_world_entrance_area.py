"""THE ENTRANCE AREA (terrain study defect 14): ``world-entrance`` gives its trigger tiles the AREA of the ground
around them, as stock does, never ``area := case``.

The case stamp aliased an unrelated stock region onto the trigger: of 151 stampable cases, 3 lock the camera, 70
make the trigger roll battles. It is how the Southern Ring's quays came to roll zone-0 battles inside the area-14
safe road (fixed by hand in southern-ring REVERT.md section 32). Stock's rule, measured over every Terrain entrance
cluster on both discs: the tiles carry the area of the walkable ground within 3u (75/76 on disc 1, 54/55 on disc 4),
and never the dispatch case (``studies/terrain-malleability/gap_area_layer/stock_entrance_area.py``).
"""
from __future__ import annotations

import math

import pytest

from ff9mapkit.world import extract as W, mesh as M
from ff9mapkit.world.placement import WALK_OK


def _game_ready() -> bool:
    try:
        import UnityPy  # noqa: F401
        from ff9mapkit import config
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


def _grid_block(idall_at, step: float = 2.0):
    """A flat 64u block of unindexed, up-facing tris on a ``step`` grid (block-local == world, origin (0, 0));
    each tri's IDALL is ``idall_at(cx, cz)`` at its centroid."""
    pos, tan, tris = [], [], []
    n = int(64 / step)
    for i in range(n):
        for j in range(n):
            x0, z0 = i * step, -64.0 + j * step
            x1, z1 = x0 + step, z0 + step
            for corners in (((x0, z0), (x0, z1), (x1, z0)), ((x1, z0), (x0, z1), (x1, z1))):
                cx = sum(c[0] for c in corners) / 3
                cz = sum(c[1] for c in corners) / 3
                idall = float(idall_at(cx, cz))
                base = len(pos)
                for (x, z) in corners:
                    pos.append([x, 0.0, z])
                    tan.append([idall, 0.0, 0.0, 1.0])
                tris.append([base, base + 1, base + 2])
    nv = len(pos)
    return W.BlockMesh(name="Block[0][0] Terrain", disc=1, x=0, y=0, lod="0_1", vcount=nv, stride=28,
                       channels={W.CH_POS: (0, 3), W.CH_TAN: (12, 4)},
                       chan_arrays={W.CH_POS: pos, W.CH_TAN: tan}, flat_index=list(range(nv)), tris=tris,
                       raw_vbuf=b"", raw_ibuf=b"", use32=False, submeshes=[(0, nv)])


def _areas(bm, tris):
    return sorted({W.decode_id(int(round(bm.tangents[bm.tris[k][0]][0])))["area"] for k in tris})


C = (32.0, -32.0)


def test_host_area_reads_the_ground_around_the_trigger_not_the_trigger():
    # area-14 road with an area-0 patch where the trigger goes (the Ring's quays before the fix)
    bm = _grid_block(lambda x, z: W.encode_id(0, 0 if math.hypot(x - C[0], z - C[1]) < 6 else 14, 0))
    trig = []
    assert M.retarget_tiles(bm, event=1, center=C, radius=6.0, out_tris=trig) == len(trig) > 0
    h = M.host_area(bm, center=C, radius=6.0)
    assert h["area"] == 14 and h["source"] == "ring" and set(h["votes"]) == {14}


def test_host_area_prefers_the_local_ring_over_the_block_majority():
    # the trigger sits in a 22 strip along the west edge; most of the block is 7
    bm = _grid_block(lambda x, z: W.encode_id(0, 22 if x < 24 else 7, 0))
    h = M.host_area(bm, center=(10.0, -32.0), radius=4.0)
    assert h["area"] == 22 and h["source"] == "ring"


def test_host_area_votes_rock_when_no_walkable_ground_rings_the_trigger():
    # a trigger cut into rock (stock's (13,17) case): rock (topograph 49, unwalkable) of area 14 around it,
    # area-7 lawn beyond. The ring's rock wins over the block's lawn.
    def at(x, z):
        r = math.hypot(x - C[0], z - C[1])
        return W.encode_id(0, 14, 49) if r < 16 else W.encode_id(0, 7, 0)
    assert 49 not in WALK_OK
    h = M.host_area(_grid_block(at), center=C, radius=4.0)
    assert h["area"] == 14 and h["source"] == "ring-any"


def test_host_area_block_fallback_skips_canopy_and_events():
    # nothing but event tiles near the trigger; beyond, a bigger canopy (area 9) and a smaller lawn (area 7)
    def at(x, z):
        if math.hypot(x - C[0], z - C[1]) < 20:
            return W.encode_id(1, 30, 0)
        return W.encode_id(0, 9, 37) if x < 40 else W.encode_id(0, 7, 0)
    h = M.host_area(_grid_block(at), center=C, radius=4.0)
    assert h["area"] == 7 and h["source"] == "block"


def test_host_area_is_none_without_event_free_ground():
    h = M.host_area(_grid_block(lambda x, z: W.encode_id(1, 5, 0)), center=C, radius=4.0)
    assert h == {"area": None, "source": None, "votes": {}}


def test_host_area_ignores_walk_skip_tris():
    # a 4078 (walk-skip) stamp over the whole block: the engine raycast passes through it, so it must not vote
    base = _grid_block(lambda x, z: W.encode_id(0, 14, 0))
    skip = _grid_block(lambda x, z: 4078)
    for v in skip.verts:
        v[1] = 1.0
    n = base.vcount
    merged = W.BlockMesh(name=base.name, disc=1, x=0, y=0, lod="0_1", vcount=2 * n, stride=28,
                         channels=base.channels,
                         chan_arrays={W.CH_POS: skip.verts + base.verts, W.CH_TAN: skip.tangents + base.tangents},
                         flat_index=list(range(2 * n)), tris=skip.tris + [[a + n, b + n, c + n] for a, b, c in base.tris],
                         raw_vbuf=b"", raw_ibuf=b"", use32=False, submeshes=[(0, 2 * n)])
    assert W.decode_id(4078)["area"] == 15
    h = M.host_area(merged, center=C, radius=4.0)
    assert h["area"] == 14 and h["source"] == "ring"


def test_area_effects_name_the_engine_channels():
    assert M.area_effects(12) == {"area": 12, "zone": 5, "camera_place": 0, "camera_lock": True,
                                       "weather": True, "beach_search": False}
    assert M.area_effects(14)["zone"] == 6 and not M.area_effects(14)["camera_lock"]
    assert [M.area_camera_place(a) for a in (0, 26, 27, 39, 40, 45, 46, 50, 51, 63)] == [0, 0, 2, 2, 1, 1, 0, 0, 2, 2]
    assert M.area_effects(49)["beach_search"] and M.area_effects(9)["weather"]
    assert M.area_effects(76)["area"] == 12                       # the 6-bit wrap a case >= 64 hits


def test_author_entrance_rejects_a_bad_tile_area_before_any_read(tmp_path):
    from ff9mapkit.world import entrance as EN
    for bad in (64, -1, "bogus", True, 3.0):
        with pytest.raises(ValueError, match="tile_area"):
            EN.author_entrance(cell=(35, 25), mod_folder="X", case=4, game=tmp_path, tile_area=bad, dry_run=True)


def _fake_entrance(captured, **extra):
    def fake(**kw):
        captured.update(kw)
        return {"tag_hex": "0x0000", "field": 300, "dry_run": True, "cell": (19, 21), "case": 4, "dest_note": "",
                "dispatchers_written": [], "dispatchers_skipped": [], "langs": [], "tiles_set": 3, "block": (9, 10),
                "event": 1, "backups": [], "tile_area": [14], "tile_area_mode": kw["tile_area"],
                "tile_area_host": {"area": 14, "source": "ring", "votes": {14: 9}}, **extra}
    return fake


@pytest.mark.parametrize("flags, want", [([], "host"), (["--no-tile-area"], "keep"), (["--tile-area", "case"], "case"),
                                         (["--tile-area", "keep"], "keep"), (["--tile-area", "12"], 12)])
def test_cli_tile_area_flag(flags, want, monkeypatch, capsys):
    from ff9mapkit import cli
    from ff9mapkit.world import entrance as EN
    captured = {}
    monkeypatch.setattr(EN, "author_entrance", _fake_entrance(captured))
    assert cli.main(["world-entrance", "--cell", "19", "21", "--field", "300", "--mod-folder", "X", "--dry-run",
                     *flags]) == 0
    assert captured["tile_area"] == want
    assert "area=14 (" in capsys.readouterr().out


@pytest.mark.parametrize("flags", [["--tile-area", "64"], ["--tile-area", "x"], ["--tile-area", "keep", "--no-tile-area"]])
def test_cli_tile_area_flag_refuses(flags, monkeypatch, capsys):
    from ff9mapkit import cli
    from ff9mapkit.world import entrance as EN
    monkeypatch.setattr(EN, "author_entrance", _fake_entrance({}))
    assert cli.main(["world-entrance", "--cell", "19", "21", "--field", "300", "--mod-folder", "X", "--dry-run",
                     *flags]) == 2
    assert "tile-area" in capsys.readouterr().err


def test_cli_prints_the_tile_area_warning(monkeypatch, capsys):
    from ff9mapkit import cli
    from ff9mapkit.world import entrance as EN
    monkeypatch.setattr(EN, "author_entrance", _fake_entrance({}, tile_area_warning="off the host"))
    assert cli.main(["world-entrance", "--cell", "19", "21", "--field", "300", "--mod-folder", "X", "--dry-run"]) == 0
    assert "!! WARNING: off the host" in capsys.readouterr().out


# ---- against the install --------------------------------------------------------------------------------------

def _stock_clusters(bm, link: float = 4.0):
    """Stock entrance clusters in one Terrain mesh: event tris on a walkable topograph, single-linkage on centroids."""
    pts = []
    for t in bm.tris:
        idall = int(round(bm.tangents[t[0]][0]))
        d = W.decode_id(idall)
        if idall in M.WALK_SKIP_IDS or not d["event"] or d["topograph"] not in WALK_OK:
            continue
        pts.append((sum(bm.verts[i][0] for i in t) / 3, sum(bm.verts[i][2] for i in t) / 3, d["area"], d["event"]))
    groups = []
    for p in pts:
        hit = [g for g in groups if any(math.hypot(p[0] - q[0], p[1] - q[1]) <= link for q in g)]
        groups = [g for g in groups if g not in hit] + [[p] + [q for g in hit for q in g]]
    return groups


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
@pytest.mark.parametrize("disc, total, matched", [(1, 76, 75), (4, 55, 54)])
def test_host_area_recovers_stock_entrance_areas(disc, total, matched):
    """The rule is stock's: over every stock Terrain entrance cluster, host_area returns the tiles' own area. The one
    miss on each disc is the same (2,7) trigger on a 43/44 boundary (same zone and camera place: only the label
    differs). And stock never stamps the dispatch case: no cluster's area is its case & 0x3F."""
    from ff9mapkit.world import entrance as EN
    from ff9mapkit.eb.model import EbScript
    cases = {}
    for data in EN.load_world_dispatchers().values():
        for f in EbScript(data).entry(0).funcs:
            if EN.unpack_cell_tag(f.tag) is not None:
                c = EN.byte39_value(data[f.abs_start:f.abs_end])
                if c is not None:
                    cases.setdefault(f.tag, set()).add(c)
    n = ok = with_case = case_eq = 0
    misses = []
    for bx in range(24):
        for by in range(20):
            try:
                bm = W.read_block(bx, by, disc=disc, lod="0_1", part="terrain")
            except ValueError:
                continue                                       # an open-sea block has no Terrain
            ox, oz = W.block_world_origin(bx, by)
            for g in _stock_clusters(bm):
                areas = {q[2] for q in g}
                assert len(areas) == 1                         # a stock trigger cluster is one area
                own = areas.pop()
                cx, cz = sum(q[0] for q in g) / len(g), sum(q[1] for q in g) / len(g)
                rad = max(math.hypot(q[0] - cx, q[1] - cz) for q in g) + 1.5
                h = M.host_area(bm, center=(cx + ox, cz + oz), radius=rad, world_origin=(ox, oz))
                n += 1
                ok += h["area"] == own
                if h["area"] != own:
                    misses.append(((bx, by), own, h["area"]))
                cs = set()
                for q in g:
                    tag = EN.pack_cell_tag(int((q[0] + ox) // 32), int(-(q[1] + oz) // 32), q[3])
                    cs |= cases.get(tag, set())
                if cs:
                    with_case += 1
                    case_eq += any((c & 0x3F) == own for c in cs)
    assert (n, ok) == (total, matched), misses
    assert misses == [((2, 7), 44, 43)]
    assert with_case > 20 and case_eq == 0


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_author_entrance_stamps_the_host_area_by_default():
    """(35,25) -> Ice Cavern (case 4) on pristine stock: host stamps the ring's area 2 with no warning; the old
    case stamp (4) and keep (stock's 0/2 under the r14 disc) both warn; the same tiles in every mode."""
    from ff9mapkit.world import entrance as EN
    mod = "FF9CustomMap_test_nonexistent"
    host = EN.author_entrance(cell=(35, 25), mod_folder=mod, field=300, dry_run=True)
    assert host["tile_area"] == [2] and host["tile_area_host"]["source"] == "ring"
    assert "tile_area_warning" not in host and host["tile_area_stamped"]
    case = EN.author_entrance(cell=(35, 25), mod_folder=mod, field=300, dry_run=True, tile_area="case")
    assert case["tile_area"] == [4] and "encounter zone 1 -> 2" in case["tile_area_warning"]
    keep = EN.author_entrance(cell=(35, 25), mod_folder=mod, field=300, dry_run=True, set_tile_area=False)
    assert keep["tile_area_mode"] == "keep" and keep["tile_area"] == [0, 2] and not keep["tile_area_stamped"]
    assert "area 0" in keep["tile_area_warning"]
    assert host["tiles_set"] == case["tiles_set"] == keep["tiles_set"] > 0
    with pytest.raises(ValueError, match="needs a dispatch case"):
        EN.author_entrance(cell=(35, 25), mod_folder=mod, direct_field=6601, dry_run=True, tile_area="case")
