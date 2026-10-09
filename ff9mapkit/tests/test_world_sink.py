"""THE ISLAND SINK (`world-sink`; `transplant.sink_plan` / `sink`): a whole bare-coast REAL island turned into open sea,
in place, the way disc 4 removed Shimmering Island (terrain study, land -> sea).

A synthetic world: block (5,5) is a sheet of stock deep-sea tiles (two tris per 4u tile, sea4 topograph 57, negative
winding, the stock normal) with islands cut into it; each island's coast welds to the tile corners at y=0.
"""
from __future__ import annotations

import math
import warnings

import pytest

from ff9mapkit import cli, config
from ff9mapkit.world import discmirror as DM, extract as X, transplant as TR

NRM = (-0.1211, 0.9785, 0.1665)
SEA = 228                                         # topograph 57, area 0
KEEL = X.encode_id(topograph=56)
LAND = X.encode_id(topograph=0, area=14)
B = (5, 5)                                        # x 320..384, z -384..-320; tiles i 80..95, j -96..-81


def V(x, y, z, idall):
    return ((float(x), float(y), float(z)), NRM, (0.0, 0.0), (float(idall), 0.0, 0.0, 1.0))


def neg(a, b, c):
    """The tri (a, b, c) wound negative in plan (stock sea4's winding)."""
    cross = (b[0][0] - a[0][0]) * (c[0][2] - a[0][2]) - (c[0][0] - a[0][0]) * (b[0][2] - a[0][2])
    return [a, b, c] if cross < 0 else [a, c, b]


def tile(i, j, idall=SEA):
    x0, z0 = 4.0 * i, 4.0 * j
    p = [V(x0, 0, z0, idall), V(x0 + 4, 0, z0, idall), V(x0 + 4, 0, z0 + 4, idall), V(x0, 0, z0 + 4, idall)]
    return [neg(p[0], p[1], p[2]), neg(p[0], p[2], p[3])]


def pyramid(i0, j0, n, h=3.0, idall=LAND):
    """An n x n tile island: four tris from the square's edges up to an apex (coast at y=0 on lattice points)."""
    x0, z0, s = 4.0 * i0, 4.0 * j0, 4.0 * n
    c = V(x0 + s / 2, h, z0 + s / 2, idall)
    sq = [V(x0, 0, z0, idall), V(x0 + s, 0, z0, idall), V(x0 + s, 0, z0 + s, idall), V(x0, 0, z0 + s, idall)]
    return [[sq[k], sq[(k + 1) % 4], c] for k in range(4)]


class World:
    def __init__(self):
        self.parts = {}

    def add(self, b, part, tris):
        self.parts.setdefault((b, part), []).extend(tris)

    def sea(self, b, skip=(), keel=()):
        bx, by = b
        for i in range(bx * 16, bx * 16 + 16):
            for j in range(-by * 16 - 16, -by * 16):
                if (i, j) not in skip:
                    self.add(b, "sea4", tile(i, j, KEEL if (i, j) in keel else SEA))

    def real(self, disc, lod="0_1", game=None):
        out = {}
        for (b, p) in self.parts:
            out.setdefault(b, set()).add(p)
        return out

    def tris(self, bx, by, part, disc=1, lod="0_1", game=None):
        return [list(t) for t in self.parts.get(((bx, by), part), [])]


def ring(i0, j0, n):
    return {(i, j) for i in range(i0 - 1, i0 + n + 1) for j in range(j0 - 1, j0 + n + 1)} - \
        {(i, j) for i in range(i0, i0 + n) for j in range(j0, j0 + n)}


@pytest.fixture
def world(monkeypatch):
    w = World()
    monkeypatch.setattr(DM, "_real_parts", w.real)
    monkeypatch.setattr(TR, "world_tris", w.tris)
    monkeypatch.setattr(TR, "world_tris_stacked", lambda mod, bx, by, p, **k: (w.tris(bx, by, p), None))
    return w


def _island(w, keel=True, other=True):
    """Island A: tiles (85..86, -91..-90) with a keel ring; island B (90..91, -85..-84), keel ring too."""
    a, b = (85, -91), (90, -85)
    skip = {(a[0] + di, a[1] + dj) for di in (0, 1) for dj in (0, 1)}
    k = ring(*a, 2) if keel else set()
    if other:
        skip |= {(b[0] + di, b[1] + dj) for di in (0, 1) for dj in (0, 1)}
        k |= ring(*b, 2) if keel else set()
    w.sea(B, skip=skip, keel=k)
    w.add(B, "terrain", pyramid(*a, 2))
    if other:
        w.add(B, "terrain", pyramid(*b, 2))
    return (344.0, -360.0)


def test_sinks_the_island_its_tiles_and_its_keel_ring(world):
    at = _island(world)
    plan, rep = TR.sink_plan(at)
    assert list(plan) == [B] and rep["tiles"] == 4 and rep["land_tris"] == 4 and rep["fill_tris"] == 8
    assert rep["sea_replaced"] == 0 and rep["edge_welds"] == 0 and rep["miss"] == rep["overlap"] == 0
    assert rep["keel_to_open"] == 24                    # island A's ring (12 tiles); island B's ring stays keel
    retopo = next(tw for tw in plan[B] if isinstance(tw, TR.RetopoTris))
    flipped = [TR._plan_centroid(t) for t in world.parts[(B, "sea4")] if retopo._key_set(t) in retopo.keys]
    assert len(flipped) == 24 and all(math.dist(c, (344.0, -360.0)) < math.dist(c, (364.0, -336.0)) for c in flipped)
    drop = [tw for tw in plan[B] if isinstance(tw, TR.DropTris)]
    assert [(d.part, d.expected) for d in drop] == [("terrain", 4)]
    fill = next(tw for tw in plan[B] if isinstance(tw, TR.EmitTris)).emit()
    assert {X.decode_id(int(t[0][3][0]))["topograph"] for t in fill} == {57}
    assert all(v[0][1] == 0.0 for t in fill for v in t)
    for t in fill:                                      # the sheet's own winding and normal
        a, b, c = (v[0] for v in t)
        assert (b[0] - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (b[2] - a[2]) < 0 and t[0][1] == NRM
    s = TR.morph_in_place("MOD", cell=B, tweaks=plan[B], dry_run=True, frame_across_parts=True)
    assert s["clean"], s["gates"]


def test_the_keel_rule_keeps_a_coastal_tile_another_island_explains(world):
    at = _island(world)
    # island B moves next to A's ring: the tile between them is keel for B too
    world.parts[(B, "terrain")] = world.parts[(B, "terrain")][:4]
    world.add(B, "terrain", pyramid(88, -91, 1))
    keep = [t for t in world.parts[(B, "sea4")] if TR._plan_centroid(t)[0] < 352 or TR._plan_centroid(t)[1] > -352]
    world.parts[(B, "sea4")] = [t for t in keep if not (352 <= TR._plan_centroid(t)[0] <= 356
                                                       and -364 <= TR._plan_centroid(t)[1] <= -360)]
    _plan, rep = TR.sink_plan(at)
    assert rep["keel_to_open"] < 24


def test_a_near_vertical_island_tri_on_a_tile_line_sinks_too(world):
    """In-game round 10, launch 2: two hillside strips of the island, welded to it but standing exactly on 4u tile lines
    (no plan area: they touch no tile), were kept and floated in the sky over the new sea. Every island tri goes."""
    at = _island(world, keel=False, other=False)
    world.add(B, "terrain", [[V(344, 3, -360, LAND), V(344, 0, -364, LAND), V(344, 1.5, -362, LAND)]])
    plan, rep = TR.sink_plan(at)
    drop = next(tw for tw in plan[B] if isinstance(tw, TR.DropTris) and tw.part == "terrain")
    assert rep["land_tris"] == 5 and drop.expected == 5


def test_a_loose_piece_inside_the_island_sinks_with_it_and_kept_land_inside_is_refused(world):
    """THE FRAGMENTS: land welded to nothing, wholly within the island's tiles, goes with it. THE FLOATING GATE: land
    joined to something outside that still reaches inside the tiles is refused (it would stand over open sea)."""
    at = _island(world, keel=False, other=False)
    world.add(B, "terrain", [[V(341, 1, -363, LAND), V(342, 1, -363, LAND), V(341, 1, -362.5, LAND)]])
    _plan, rep = TR.sink_plan(at)
    assert rep["fragment_tris"] == 1 and rep["land_tris"] == 5
    world.parts[(B, "terrain")].pop()
    # a vertical sliver on the line x 344 from the island's centre out past its edge, welded to land outside
    world.add(B, "terrain", [[V(344, 0, -360, LAND), V(344, 2, -360, LAND), V(344, 0, -352, LAND)],
                             [V(344, 0, -352, LAND), V(345, 0, -350, LAND), V(343, 0, -350, LAND)]])
    with pytest.raises(ValueError, match="would stand over the new sea"):
        TR.sink_plan(at)


def test_refusals(world):
    _island(world)
    with pytest.raises(ValueError, match="no land lies under"):
        TR.sink_plan((330.0, -330.0))
    world.add(B, "sea3", [[V(348, 0, -364, SEA), V(352, 0, -364, SEA), V(348, 0, -360, SEA)]])
    with pytest.raises(ValueError, match="owns shallow water"):
        TR.sink_plan((344.0, -360.0))


def test_a_building_or_other_land_in_its_tiles_refuses(world):
    at = _island(world, keel=False, other=False)
    world.add(B, "object", [[V(341, 1, -363, LAND), V(342, 1, -363, LAND), V(341, 1, -362, LAND)]])
    with pytest.raises(ValueError, match="'object' tri .* shares a 4u tile"):
        TR.sink_plan(at)


def test_entrance_bits_on_the_sea_it_would_replace_refuse(world):
    at = _island(world, keel=False, other=False)
    # a coastal sea tri inside an island tile, carrying event bits
    world.parts[(B, "terrain")] = [t for t in world.parts[(B, "terrain")]]
    ev = X.encode_id(event=1, topograph=57)
    world.add(B, "sea4", [[V(340, 0, -364, ev), V(340.5, 0, -364, ev), V(340, 0, -363.5, ev)]])
    with pytest.raises(ValueError, match="entrance bits"):
        TR.sink_plan(at)


def test_a_coastal_sea_tri_spanning_tiles_pulls_its_tiles_in(world):
    """THE FRINGE CLOSURE: a thin island on the west half of tile (85,-91); one sea rect over its east half and the
    whole of tile (86,-91), welded at x 342 -- both tiles are re-tiled whole."""
    world.sea(B, skip={(85, -91), (86, -91)})
    world.add(B, "terrain", [[V(340, 0, -364, LAND), V(342, 0, -364, LAND), V(341, 2, -362, LAND)],
                             [V(342, 0, -364, LAND), V(342, 0, -360, LAND), V(341, 2, -362, LAND)],
                             [V(342, 0, -360, LAND), V(340, 0, -360, LAND), V(341, 2, -362, LAND)],
                             [V(340, 0, -360, LAND), V(340, 0, -364, LAND), V(341, 2, -362, LAND)]])
    world.add(B, "sea4", [neg(V(342, 0, -364, SEA), V(348, 0, -364, SEA), V(348, 0, -360, SEA)),
                          neg(V(342, 0, -364, SEA), V(348, 0, -360, SEA), V(342, 0, -360, SEA))])
    plan, rep = TR.sink_plan((341.0, -362.5))
    assert rep["tiles"] == 2 and rep["sea_replaced"] == 2 and rep["fill_tris"] == 4 and rep["miss"] == 0


def test_the_fill_keeps_the_area_of_the_sea_it_replaces(world):
    """The sea's AREA drives its encounter zone and camera: the fill takes the replaced sea's own (here 9)."""
    sea9 = X.encode_id(area=9, topograph=57)
    world.sea(B, skip={(85, -91), (86, -91)})
    world.parts[(B, "sea4")] = [[(v[0], v[1], v[2], (float(sea9),) + v[3][1:]) for v in t]
                                for t in world.parts[(B, "sea4")]]
    world.add(B, "terrain", [[V(340, 0, -364, LAND), V(342, 0, -364, LAND), V(341, 2, -362, LAND)],
                             [V(342, 0, -364, LAND), V(342, 0, -360, LAND), V(341, 2, -362, LAND)],
                             [V(342, 0, -360, LAND), V(340, 0, -360, LAND), V(341, 2, -362, LAND)],
                             [V(340, 0, -360, LAND), V(340, 0, -364, LAND), V(341, 2, -362, LAND)]])
    world.add(B, "sea4", [neg(V(342, 0, -364, sea9), V(348, 0, -364, sea9), V(348, 0, -360, sea9)),
                          neg(V(342, 0, -364, sea9), V(348, 0, -360, sea9), V(342, 0, -360, sea9))])
    plan, rep = TR.sink_plan((341.0, -362.5))
    fill = next(tw for tw in plan[B] if isinstance(tw, TR.EmitTris)).emit()
    assert rep["fill_area"] == 9 and {X.decode_id(int(t[0][3][0]))["area"] for t in fill} == {9}


def test_a_kept_vertex_part_way_along_a_tile_edge_joins_the_fill(world):
    """THE EDGE WELD: the kept tile west of the island is split with a vertex at the middle of the shared edge; the
    re-tiled tile takes that vertex, so the seam has no T-junction."""
    at = _island(world, keel=False, other=False)
    west = [t for t in world.parts[(B, "sea4")] if 336 <= TR._plan_centroid(t)[0] <= 340
            and -364 <= TR._plan_centroid(t)[1] <= -360]
    for t in west:
        world.parts[(B, "sea4")].remove(t)
    m = V(340, 0, -362, SEA)
    world.add(B, "sea4", [neg(V(336, 0, -364, SEA), V(340, 0, -364, SEA), m),
                          neg(V(336, 0, -364, SEA), m, V(336, 0, -360, SEA)),
                          neg(V(336, 0, -360, SEA), m, V(340, 0, -360, SEA))])
    plan, rep = TR.sink_plan(at)
    assert rep["edge_welds"] == 1
    fill = next(tw for tw in plan[B] if isinstance(tw, TR.EmitTris)).emit()
    assert (340.0, 0.0, -362.0) in {v[0] for t in fill for v in t}
    # a kept LAND vertex there (above the waterline) cannot be welded to: refused
    world.parts[(B, "sea4")].remove(world.parts[(B, "sea4")][-1])
    world.add(B, "terrain", [[V(336, 0, -360, LAND), V(340, 1.5, -362, LAND), V(340, 0, -360, LAND)]])
    with pytest.raises(ValueError, match="above the waterline"):
        TR.sink_plan(at)


def test_an_island_across_a_block_border_sinks_in_both_blocks_with_the_border_exempt(world):
    """Island 2x2 tiles straddling x = 384 (blocks (5,5) and (6,5)); the in-place frame gate exempts their shared
    border and compares frame positions across parts on the others."""
    b2 = (6, 5)
    skip = {(95, -91), (95, -90), (96, -91), (96, -90)}
    world.sea(B, skip=skip)
    world.sea(b2, skip=skip)
    for b, x0 in ((B, 380.0), (b2, 384.0)):
        world.add(b, "terrain", [[V(x0, 0, -364, LAND), V(x0 + 4, 0 if x0 == 384 else 2, -364, LAND),
                                  V(x0 + 4 if x0 == 380 else x0, 2, -360, LAND)]])
    # a ridge welded across the border: two tris per block sharing (384, 2, -360) / (384, 2, -364)... keep it simple:
    world.parts[(B, "terrain")] = [[V(380, 0, -364, LAND), V(384, 2, -362, LAND), V(380, 0, -356, LAND)],
                                   [V(380, 0, -364, LAND), V(384, 0, -364, LAND), V(384, 2, -362, LAND)],
                                   [V(384, 2, -362, LAND), V(384, 0, -356, LAND), V(380, 0, -356, LAND)]]
    world.parts[(b2, "terrain")] = [[V(388, 0, -364, LAND), V(388, 0, -356, LAND), V(384, 2, -362, LAND)],
                                    [V(384, 0, -364, LAND), V(388, 0, -364, LAND), V(384, 2, -362, LAND)],
                                    [V(384, 2, -362, LAND), V(388, 0, -356, LAND), V(384, 0, -356, LAND)]]
    plan, rep = TR.sink_plan((382.0, -360.0))
    assert sorted(plan) == [B, b2] and rep["tiles"] == 4
    s = TR.sink("MOD", (382.0, -360.0), dry_run=True)
    assert s["clean"], {k: v["gates"] for k, v in s["per_block"].items()}
    frame = {k: next(g for g in v["gates"] if g["gate"] == "in-place-frame") for k, v in s["per_block"].items()}
    assert frame["5,5"]["exempt"] == "E" and frame["6,5"]["exempt"] == "W"
    # without the exemption the dropped ridge vertex on the border is a frame change
    s1 = TR.morph_in_place("MOD", cell=B, tweaks=TR.sink_plan((382.0, -360.0))[0][B], dry_run=True,
                           frame_across_parts=True)
    assert not s1["clean"]


def test_sink_writes_every_block_then_one_mirror_with_the_replay(world, monkeypatch):
    from pathlib import Path
    at = _island(world, keel=False, other=False)
    written, seen = [], {}
    from ff9mapkit.world import mesh as M
    meshes = {}
    monkeypatch.setattr(M, "deploy_override", lambda bm, **k: written.append(bm.name) or meshes.update({bm.name: bm})
                        or Path(bm.name))
    monkeypatch.setattr(DM, "auto_mirror", lambda w, **k: seen.update(k, written=list(w)))

    def hook(d):
        return None
    s = TR.sink("MOD", at, replay=hook)
    assert s["clean"] and written == ["Block[5][5] Sea4", "Block[5][5] Terrain"]
    assert seen["replay"] is hook and len(seen["written"]) == 2 and seen["skip_mirror"] is False
    # the island was the block's only land: its Terrain is the hidden blanking stub, never a 0-vert mesh
    stub = meshes["Block[5][5] Terrain"]
    assert stub.vcount == 3 and {round(v[1], 1) for v in stub.verts} == {-80.0}
    # a refused gate on ANY block writes nothing: no morph runs for real
    calls = []
    monkeypatch.setattr(TR, "morph_in_place", lambda *a, **k: calls.append(k.get("dry_run", False)) or
                        {"clean": False, "gates": [], "deployed": []})
    s = TR.sink("MOD", at)
    assert not s["clean"] and calls == [True]


def test_the_coverage_gate_refuses_a_fill_with_a_hole(world, monkeypatch):
    """THE COVERAGE GATE is live: a fill that leaves part of the island's tiles uncovered (here one tri short) is
    refused, never planned."""
    at = _island(world, keel=False, other=False)
    from ff9mapkit.world import meshedit as ME
    real = ME.lattice_patch
    monkeypatch.setattr(ME, "lattice_patch", lambda ring, **k: real(ring, **k)[1:])
    with pytest.raises(ValueError, match="does not cover the island's tiles exactly once"):
        TR.sink_plan(at)


def test_cli_dry_run_previews_disc4_and_the_replay_reruns_the_sink(world, monkeypatch, capsys):
    at = _island(world)
    monkeypatch.setattr(DM, "copy_refusal", lambda blk, **k: "real cell differs across discs in ['terrain']")
    args = cli.build_parser().parse_args(["world-sink", "--mod-folder", "MOD", "--at", "344", "-360", "--dry-run"])
    assert cli._cmd_world_sink(args) == 0
    out = capsys.readouterr().out
    assert "4 4u tiles re-tiled as open sea" in out and "24 near-shore tris turned open water" in out
    assert "the deploy re-runs this sink on disc 4's own ground" in out
    assert "disc 4: the replay passes its gates -- the deploy edits both discs" in out
    seen = {}
    monkeypatch.setattr(TR, "sink", lambda mod, at, **k: seen.update(k) or {
        "land_tris": 4, "land_u2": 64.0, "max_y": 3.0, "blocks": [[5, 5]], "tiles": 4, "fill_tris": 8,
        "fill_area": 0, "sea_replaced": 0, "edge_welds": 0, "keel_to_open": 0, "entrance_tris": 0,
        "per_block": {}, "clean": True, "deployed": []})
    args = cli.build_parser().parse_args(["world-sink", "--mod-folder", "MOD", "--at", "344", "-360"])
    assert cli._cmd_world_sink(args) == 0
    runs = []
    monkeypatch.setattr(cli, "_cmd_world_sink", lambda a: runs.append(a) or 2)
    with pytest.raises(ValueError, match="world-sink --disc 4 refused the same island"):
        seen["replay"](4)
    assert runs[0].disc == 4 and runs[0].skip_mirror == DM.REPLAY and runs[0].at == [344.0, -360.0]


def _need_install() -> None:
    try:
        import UnityPy  # noqa: F401
        ok = (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        ok = False
    if not ok:
        warnings.warn("the island sink went unchecked on real data in this run: no FF9 install + UnityPy. Re-run in "
                      "the MAIN repo (C:/gd/Dream-World-IX/ff9mapkit).", UserWarning)
        pytest.skip("needs the FF9 install + UnityPy (see the warnings summary)")


def test_real_two_block_island_sinks_and_shimmering_is_refused():
    """(20,9)+(21,9): a 322u2 bare-coast island across a block border; Shimmering Island (disc 4 sinks it itself) is
    refused: its own islets share its coastal sea."""
    _need_install()
    s = TR.sink("FF9CustomMap_test_nonexistent", (1347.254, -605.225), dry_run=True)
    assert s["clean"] and s["blocks"] == [[20, 9], [21, 9]] and s["land_tris"] == 76 and s["miss"] == 0
    with pytest.raises(ValueError, match="another coast's"):
        TR.sink_plan((441.992, -311.975))
