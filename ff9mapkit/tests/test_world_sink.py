"""THE ISLAND SINK (`world-sink`; `transplant.sink_plan` / `sink`): a whole REAL island turned into open water, in
place, the way disc 4 removed Shimmering Island (terrain study, land -> sea), re-banded to the water it stands in.

A synthetic world: block (5,5) is a sheet of stock water tiles (two tris per 4u tile, negative winding, the stock
normal; deep sea4 topograph 57 unless a test lays mid-water sea3 and sea5 transition tiles drawn for their deep edges)
with islands cut into it; each island's coast welds to the tile corners at y=0.
"""
from __future__ import annotations

import math
import warnings

import pytest

from ff9mapkit import cli, config
from ff9mapkit.world import coastmorph as CM, discmirror as DM, extract as X, transplant as TR

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


def btile(i, j, part, es=frozenset(), idall=None):
    """A stock lattice tile of water band ``part``: a sea5 transition tile's uv drawn for its deep edges ``es`` (so it
    decodes as them), sea3/sea4 plain."""
    x0, z0 = 4.0 * i, 4.0 * j
    ida = idall if idall is not None else X.encode_id(topograph={"sea1": 53, "sea2": 53, "sea3": 54, "sea5": 54,
                                                                 "sea4": 57}[part])
    uvf = CM._strip_uvf((i, j), frozenset(es)) if part == "sea5" else (lambda x, z: (0.0, 0.0))

    def P(x, z):
        return ((float(x), 0.0, float(z)), NRM, tuple(uvf(x, z)), (float(ida), 0.0, 0.0, 1.0))
    p = [P(x0, z0), P(x0 + 4, z0), P(x0 + 4, z0 + 4), P(x0, z0 + 4)]
    return [neg(p[0], p[1], p[2]), neg(p[0], p[2], p[3])]


def topo(t):
    return X.decode_id(int(t[0][3][0]))["topograph"]


BELT = X.encode_id(topograph=55)


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

    def bands(self, b, fn):
        """Lay block ``b`` with water tiles: ``fn(i, j)`` gives ``(part, deep_edges, idall)`` or None (no water)."""
        bx, by = b
        for i in range(bx * 16, bx * 16 + 16):
            for j in range(-by * 16 - 16, -by * 16):
                got = fn(i, j)
                if got:
                    part, es, ida = got
                    self.add(b, part, btile(i, j, part, es, ida))

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
    assert "4 4u tiles re-tiled as open water -- sea4 4 tiles" in out and "24 near-shore tris turned open water" in out
    assert "the deploy re-runs this sink on disc 4's own ground" in out
    assert "disc 4: the replay passes its gates -- the deploy edits both discs" in out
    seen = {}
    monkeypatch.setattr(TR, "sink", lambda mod, at, **k: seen.update(k) or {
        "land_tris": 4, "land_u2": 64.0, "max_y": 3.0, "blocks": [[5, 5]], "tiles": 4, "fill_tris": 8,
        "fill_area": 0, "sea_replaced": 0, "edge_welds": 0, "keel_to_open": 0, "entrance_tris": 0,
        "bands": {"sea3": 0, "sea5": 0, "sea4": 4}, "shore_tris": 0,
        "per_block": {}, "clean": True, "deployed": []})
    args = cli.build_parser().parse_args(["world-sink", "--mod-folder", "MOD", "--at", "344", "-360"])
    assert cli._cmd_world_sink(args) == 0
    runs = []
    monkeypatch.setattr(cli, "_cmd_world_sink", lambda a: runs.append(a) or 2)
    with pytest.raises(ValueError, match="world-sink --disc 4 refused the same island"):
        seen["replay"](4)
    assert runs[0].disc == 4 and runs[0].skip_mirror == DM.REPLAY and runs[0].at == [344.0, -360.0]


ISLE = {(85, -91), (86, -91), (85, -90), (86, -90)}       # pyramid(85, -91, 2)'s tiles


def _lagoon(world, belt=True):
    """Island A in mid water: sea3 all round, its ring the standoff belt (topograph 55)."""
    r = ring(85, -91, 2)
    world.bands(B, lambda i, j: None if (i, j) in ISLE else ("sea3", (), BELT if belt and (i, j) in r else None))
    world.add(B, "terrain", pyramid(85, -91, 2))
    return (344.0, -360.0)


def test_an_island_in_mid_water_sinks_into_mid_water(world):
    """A lagoon island: every rim edge is mid water, so its tiles re-band as sea3 (the open class 54), and the belt
    ring only it explained turns 54 too."""
    at = _lagoon(world)
    plan, rep = TR.sink_plan(at)
    assert rep["bands"] == {"sea3": 4, "sea5": 0, "sea4": 0} and rep["band_flips"] == 0 and rep["miss"] == 0
    fill = next(tw for tw in plan[B] if isinstance(tw, TR.EmitTris))
    assert fill.part == "sea3" and len(fill.emit()) == 8 and {topo(t) for t in fill.emit()} == {54}
    retopo = next(tw for tw in plan[B] if isinstance(tw, TR.RetopoTris))
    assert (retopo.part, retopo.topograph, retopo.expected, rep["keel_to_open"]) == ("sea3", 54, 24, 24)
    s = TR.morph_in_place("MOD", cell=B, tweaks=plan[B], dry_run=True, frame_across_parts=True)
    assert s["clean"], s["gates"]


def test_an_island_on_the_shelf_edge_carries_the_transition_across(world):
    """Mid water west, deep east, a sea5 column (deep edge E) between, the island across the column: its west tiles
    re-band as sea3, its east tiles as sea5 transition tiles deep to the east, each drawn to decode as its edges."""
    world.bands(B, lambda i, j: None if (i, j) in ISLE else
                ("sea3", (), None) if i < 86 else ("sea5", "E", None) if i == 86 else ("sea4", (), None))
    world.add(B, "terrain", pyramid(85, -91, 2))
    plan, rep = TR.sink_plan((344.0, -360.0))
    assert rep["bands"] == {"sea3": 2, "sea5": 2, "sea4": 0}
    fills = {tw.part: tw.emit() for tw in plan[B] if isinstance(tw, TR.EmitTris)}
    assert {math.floor(TR._plan_centroid(t)[0] / 4) for t in fills["sea3"]} == {85}
    assert {math.floor(TR._plan_centroid(t)[0] / 4) for t in fills["sea5"]} == {86}
    assert all("E" in TR.strip_edge_set(t) for t in fills["sea5"])
    # the navigation class as stock's (sh_q7): these two are corner tiles (deep east and, between them, the
    # interpolated edge), split on the diagonal that cuts off the deep corner -- 57 there, 54 on the other tri
    assert {frozenset(TR.strip_edge_set(t)) for t in fills["sea5"]} == {frozenset("EN"), frozenset("ES")}
    for z in (-362.0, -358.0):
        east = next(t for t in fills["sea5"] if TR._tri_has(t, (347.7, z)))
        west = next(t for t in fills["sea5"] if TR._tri_has(t, (344.3, z)))
        assert (topo(east), topo(west)) == (57, 54)
    s = TR.morph_in_place("MOD", cell=B, tweaks=plan[B], dry_run=True, frame_across_parts=True)
    assert s["clean"], s["gates"]


def test_a_transition_tile_across_the_rim_keeps_its_deep_edge(world):
    """The island on the deep side of a sea5 column: the column's tiles are deep to the east, toward the island, so
    the island's west edges stay deep and its tiles re-band as deep sea, leaving the column's tiles unchanged."""
    isle = {(87, -91), (88, -91), (87, -90), (88, -90)}
    world.bands(B, lambda i, j: None if (i, j) in isle else
                ("sea3", (), None) if i < 86 else ("sea5", "E", None) if i == 86 else ("sea4", (), None))
    world.add(B, "terrain", pyramid(87, -91, 2))
    _plan, rep = TR.sink_plan((352.0, -360.0))
    assert rep["bands"] == {"sea3": 0, "sea5": 0, "sea4": 4}


def test_new_water_beside_remaining_land_takes_its_shore_class(world):
    """A fill tri within SINK_BELT_REACH of land that stays (an islet just east of the island, not welded to it)
    takes its band's shore class: sea3's standoff belt, 55."""
    at = _lagoon(world, belt=False)
    world.parts[(B, "sea3")] = [t for t in world.parts[(B, "sea3")]
                                if (math.floor(TR._plan_centroid(t)[0] / 4), math.floor(TR._plan_centroid(t)[1] / 4))
                                != (87, -91)]
    c = V(350, 1, -362, LAND)
    sq = [V(348.5, 0, -363.5, LAND), V(351.5, 0, -363.5, LAND), V(351.5, 0, -360.5, LAND), V(348.5, 0, -360.5, LAND)]
    islet = [[sq[k], sq[(k + 1) % 4], c] for k in range(4)]
    world.add(B, "terrain", islet)
    plan, _rep = TR.sink_plan(at)
    fill = next(tw for tw in plan[B] if isinstance(tw, TR.EmitTris)).emit()
    near = [t for t in fill if TR._plan_dist(TR._plan_centroid(t), islet) < TR.SINK_BELT_REACH]
    assert near and {topo(t) for t in near} == {55} and 54 in {topo(t) for t in fill}


def test_the_keel_reaches_across_a_block_border(world):
    """An island on the top row of block (5,5): the keel ring tiles north of it lie in block (5,4), which the sink
    otherwise leaves alone -- they still turn open water (one more block in the plan, retopo only)."""
    up = (5, 4)
    isle = {(85, -82), (86, -82), (85, -81), (86, -81)}
    r = ring(85, -82, 2)
    world.sea(B, skip=isle, keel=r)
    world.sea(up, keel=r)
    world.add(B, "terrain", pyramid(85, -82, 2))
    plan, rep = TR.sink_plan((344.0, -324.0))
    assert rep["keel_to_open"] == 24 and sorted(plan) == [up, B]
    assert [type(tw).__name__ for tw in plan[up]] == ["RetopoTris"] and plan[up][0].expected == 8


def test_mid_water_spanning_tiles_pulls_its_tiles_in(world):
    """THE FRINGE CLOSURE over every band: a thin island in a lagoon, one sea3 rect over the east half of its tile and
    the whole of the next, welded at x 342 -- both tiles re-band as sea3."""
    mid = X.encode_id(topograph=54)
    world.bands(B, lambda i, j: None if (i, j) in {(85, -91), (86, -91)} else ("sea3", (), None))
    world.add(B, "terrain", [[V(340, 0, -364, LAND), V(342, 0, -364, LAND), V(341, 2, -362, LAND)],
                             [V(342, 0, -364, LAND), V(342, 0, -360, LAND), V(341, 2, -362, LAND)],
                             [V(342, 0, -360, LAND), V(340, 0, -360, LAND), V(341, 2, -362, LAND)],
                             [V(340, 0, -360, LAND), V(340, 0, -364, LAND), V(341, 2, -362, LAND)]])
    world.add(B, "sea3", [neg(V(342, 0, -364, mid), V(348, 0, -364, mid), V(348, 0, -360, mid)),
                          neg(V(342, 0, -364, mid), V(348, 0, -360, mid), V(342, 0, -360, mid))])
    _plan, rep = TR.sink_plan((341.0, -362.5))
    assert rep["tiles"] == 2 and rep["sea_replaced"] == 2 and rep["bands"]["sea3"] == 2 and rep["miss"] == 0


def test_the_island_takes_its_own_beach_water_and_refuses_a_shared_one(world):
    """THE SHORE: the sea1 strip east of the island is nearer it than any other land, so it goes with it (its tiles
    re-band as sea3). Run it on to another island and it is that coast's too: refused."""
    shore = {(87, -91), (87, -90)}
    world.bands(B, lambda i, j: None if (i, j) in ISLE else ("sea1", "W", None) if (i, j) in shore
                else ("sea3", (), None))
    world.add(B, "terrain", pyramid(85, -91, 2))
    plan, rep = TR.sink_plan((344.0, -360.0))
    assert rep["shore_tris"] == 4 and rep["tiles"] == 6 and rep["bands"]["sea3"] == 6
    assert ("sea1", 4) in [(tw.part, tw.expected) for tw in plan[B] if isinstance(tw, TR.DropTris)]
    # the strip runs on east, along the coast of island B at (90..91, -91..-90)
    for i in (88, 89):
        for j in (-91, -90):
            world.parts[(B, "sea3")] = [t for t in world.parts[(B, "sea3")]
                                        if (math.floor(TR._plan_centroid(t)[0] / 4),
                                            math.floor(TR._plan_centroid(t)[1] / 4)) != (i, j)]
            world.add(B, "sea1", btile(i, j, "sea1", "N"))
    world.parts[(B, "sea3")] = [t for t in world.parts[(B, "sea3")]
                                if (math.floor(TR._plan_centroid(t)[0] / 4), math.floor(TR._plan_centroid(t)[1] / 4))
                                not in {(90, -91), (91, -91), (90, -90), (91, -90)}]
    world.add(B, "terrain", pyramid(90, -91, 2))
    with pytest.raises(ValueError, match="shore water .* runs on into another coast's"):
        TR.sink_plan((344.0, -360.0))


def test_another_coasts_wash_beside_the_island_refuses(world):
    """A sea2 wash tile across the rim that is nearer other land (an islet just east of it) than the island (a thin
    one on the west half of its tile): re-banded water would meet that wash, which only ever meets its own shore."""
    world.bands(B, lambda i, j: None if (i, j) in {(85, -91), (86, -91), (87, -91)} else ("sea3", (), None))
    mid = X.encode_id(topograph=54)
    world.add(B, "terrain", [[V(340, 0, -364, LAND), V(342, 0, -364, LAND), V(341, 2, -362, LAND)],
                             [V(342, 0, -364, LAND), V(342, 0, -360, LAND), V(341, 2, -362, LAND)],
                             [V(342, 0, -360, LAND), V(340, 0, -360, LAND), V(341, 2, -362, LAND)],
                             [V(340, 0, -360, LAND), V(340, 0, -364, LAND), V(341, 2, -362, LAND)]]
              + pyramid(87, -91, 1))
    world.add(B, "sea3", [neg(V(342, 0, -364, mid), V(344, 0, -364, mid), V(344, 0, -360, mid)),
                          neg(V(342, 0, -364, mid), V(344, 0, -360, mid), V(342, 0, -360, mid))])
    world.add(B, "sea2", btile(86, -91, "sea2"))
    with pytest.raises(ValueError, match="wash .* borders a tile the sink re-bands"):
        TR.sink_plan((341.0, -362.5))


def test_a_band_the_block_has_no_part_for_refuses(world):
    """THE ABSENT-PART GATE: mid water west, deep east, no sea5 anywhere in the block -- the transition the island's
    east tiles need has no transform to render on."""
    world.bands(B, lambda i, j: None if (i, j) in ISLE else ("sea3", (), None) if i < 87 else ("sea4", (), None))
    world.add(B, "terrain", pyramid(85, -91, 2))
    with pytest.raises(ValueError, match="has no sea5 part"):
        TR.sink_plan((344.0, -360.0))


def test_a_channel_flips_its_free_edge_and_refuses_when_none_is_free(world):
    """A two-tile island: deep west of its west tile and all round its east tile, mid water north and south of the west
    tile. The edge between them interpolates deep, leaving the west tile deep on two opposite sides (a channel no tile
    draws): that free edge flips. A one-tile island with deep east and west and mid water north and south has no free
    edge: refused."""
    two = {(85, -91), (86, -91)}
    world.bands(B, lambda i, j: None if (i, j) in two else
                ("sea3", (), None) if (i, j) in {(85, -90), (85, -92)} else ("sea4", (), None) if
                (i, j) in {(84, -91), (86, -90), (86, -92), (87, -91)} else ("sea5", "S", None))
    world.add(B, "terrain", pyramid(85, -91, 1) + pyramid(86, -91, 1))
    plan, rep = TR.sink_plan((342.0, -362.0))
    assert rep["band_flips"] == 1 and rep["bands"] == {"sea3": 0, "sea5": 2, "sea4": 0}
    # the west tile is left deep to the west only (stock's class 54 on both tris), the east one deep on three sides (57)
    fill = next(tw for tw in plan[B] if isinstance(tw, TR.EmitTris)).emit()
    cls = {}
    for t in fill:
        cls.setdefault(math.floor(TR._plan_centroid(t)[0] / 4), set()).add(topo(t))
    assert cls == {85: {54}, 86: {57}}
    world.parts.clear()
    world.bands(B, lambda i, j: None if (i, j) == (85, -91) else
                ("sea3", (), None) if (i, j) in {(85, -90), (85, -92)} else ("sea4", (), None) if
                (i, j) in {(84, -91), (86, -91)} else ("sea5", "S", None))
    world.add(B, "terrain", pyramid(85, -91, 1))
    with pytest.raises(ValueError, match="channel"):
        TR.sink_plan((342.0, -362.0))


def test_the_band_and_decode_gates_are_live(world, monkeypatch):
    """THE BAND GATE refuses a pair stock never lays side by side; THE DECODE GATE a transition tile drawn for other
    edges than its own (here every tile drawn as if deep to the north)."""
    at = _lagoon(world, belt=False)
    lawful = CM._LAWFUL_ADJ
    monkeypatch.setattr(CM, "_LAWFUL_ADJ", lawful - {frozenset(("sea3",))})
    with pytest.raises(ValueError, match="stock never lays side by side"):
        TR.sink_plan(at)
    monkeypatch.setattr(CM, "_LAWFUL_ADJ", lawful)
    world.parts.clear()
    world.bands(B, lambda i, j: None if (i, j) in ISLE else
                ("sea3", (), None) if i < 86 else ("sea5", "E", None) if i == 86 else ("sea4", (), None))
    world.add(B, "terrain", pyramid(85, -91, 2))
    real = CM._strip_uvf
    monkeypatch.setattr(CM, "_strip_uvf", lambda cell, es: real(cell, frozenset("N")))
    with pytest.raises(ValueError, match="does not decode as those edges"):
        TR.sink_plan((344.0, -360.0))


def _diamond(world, keel=True):
    """A diamond island inside tiles (85..86, -91..-90), its coast at (344,-363) (347,-360) (344,-357) (341,-360), in
    a sea4 sheet; the 2x2 tiles round it hold twelve coast-conforming water tris (no tile of them is whole water),
    topograph 56 (the keel) when ``keel``. Returns a point on it."""
    world.sea(B, skip=ISLE)
    w = KEEL if keel else SEA
    S = [V(340, 0, -364, w), V(348, 0, -364, w), V(348, 0, -356, w), V(340, 0, -356, w)]       # SW SE NE NW
    M = [V(344, 0, -364, w), V(348, 0, -360, w), V(344, 0, -356, w), V(340, 0, -360, w)]       # S E N W
    D = [V(344, 0, -363, w), V(347, 0, -360, w), V(344, 0, -357, w), V(341, 0, -360, w)]       # S E N W
    water = [(S[0], M[0], D[0]), (S[0], D[0], D[3]), (S[0], D[3], M[3]),
             (S[1], M[1], D[1]), (S[1], D[1], D[0]), (S[1], D[0], M[0]),
             (S[2], M[2], D[2]), (S[2], D[2], D[1]), (S[2], D[1], M[1]),
             (S[3], M[3], D[3]), (S[3], D[3], D[2]), (S[3], D[2], M[2])]
    world.add(B, "sea4", [neg(*t) for t in water])
    top = V(344, 2.5, -360, LAND)
    L = [V(*v[0], LAND) for v in D]
    world.add(B, "terrain", [[L[k], L[(k + 1) % 4], top] for k in range(4)])
    return (344.0, -360.0)


def _open_edges(world, plan):
    """The new tris' edges no other tri shares, after the plan, round block B (none: watertight)."""
    soup = {k: list(v) for k, v in world.parts.items()}
    new = []
    for b, tws in plan.items():
        for tw in tws:
            if isinstance(tw, TR.DropTris):
                soup[(b, tw.part)] = [t for t in soup.get((b, tw.part), []) if tw._key_set(t) not in tw.keys]
            elif isinstance(tw, TR.EmitTris):
                em = tw.emit()
                soup.setdefault((b, tw.part), []).extend(em)
                new += em

    def k(v):
        return (round(v[0][0], 4), round(v[0][2], 4))
    ec = {}
    for ts in soup.values():
        for t in ts:
            for i in range(3):
                e = tuple(sorted((k(t[i]), k(t[(i + 1) % 3]))))
                ec[e] = ec.get(e, 0) + 1
    rim = (320.0, 384.0, -384.0, -320.0)
    out = []
    for t in new:
        for i in range(3):
            e = tuple(sorted((k(t[i]), k(t[(i + 1) % 3]))))
            if ec[e] == 1 and not all(p[0] in rim[:2] or p[1] in rim[2:] for p in e):
                out.append(e)
    return out


def _t_junctions(world, plan):
    """Vertices (any tri, after the plan) lying part-way along a new tri's edge round block B (none: no T-junction)."""
    soup = {k: list(v) for k, v in world.parts.items()}
    new = []
    for b, tws in plan.items():
        for tw in tws:
            if isinstance(tw, TR.DropTris):
                soup[(b, tw.part)] = [t for t in soup.get((b, tw.part), []) if tw._key_set(t) not in tw.keys]
            elif isinstance(tw, TR.EmitTris):
                em = tw.emit()
                soup.setdefault((b, tw.part), []).extend(em)
                new += em
    verts = {(round(v[0][0], 5), round(v[0][2], 5)) for ts in soup.values() for t in ts for v in t if v[0][1] == 0.0}
    out = set()
    for t in new:
        if TR._plan_clip_area([(v[0][0], v[0][2]) for v in t], -1e9, 1e9, -1e9, 1e9) < 1e-9:
            continue
        for i in range(3):
            a, b = (t[i][0][0], t[i][0][2]), (t[(i + 1) % 3][0][0], t[(i + 1) % 3][0][2])
            for q in verts:
                ends = ((round(a[0], 5), round(a[1], 5)), (round(b[0], 5), round(b[1], 5)))
                if q not in ends and TR._seg_dist(q, a, b) < 1e-5:
                    out.add(q)
    return sorted(out)


def test_the_footprint_sink_fills_only_the_island_and_keeps_the_water_round_it(world):
    """THE FOOTPRINT SINK: only the island's land goes; each cell's piece of its footprint continues the kept water
    beside it (band, uv map); nothing else is dropped, the coverage is exact and the result is watertight. The keel
    round it, which only the island explained, turns open water."""
    at = _diamond(world)
    plan, rep = TR.sink_footprint_plan(at)
    assert rep["fill"] == "footprint" and rep["cells_whole"] == 0 and rep["cells_partial"] == 4
    assert rep["footprint_u2"] == 18.0 and rep["fill_u2"] == 18.0 and rep["miss"] == rep["overlap"] == 0
    drops = [(tw.part, tw.expected) for tw in plan[B] if isinstance(tw, TR.DropTris)]
    assert drops == [("terrain", 4)]
    fill = [t for tw in plan[B] if isinstance(tw, TR.EmitTris) for t in tw.emit()]
    assert len(fill) == 4 and all(v[0][1] == 0.0 for t in fill for v in t)
    assert {topo(t) for t in fill} == {57} and rep["keel_to_open"] == 12
    assert _open_edges(world, plan) == [] and _t_junctions(world, plan) == []
    s = TR.morph_in_place("MOD", cell=B, tweaks=plan[B], dry_run=True, frame_across_parts=True)
    assert s["clean"], s["gates"]


def test_the_footprint_sink_carries_the_kept_water_uv_on_over_the_old_coast(world):
    """A part-cell's piece takes the affine uv map of the kept water across its old coast edge (here a distinctive one
    on the tri across the diamond's south-west edge), so the water runs on over the old coastline with no seam."""
    at = _diamond(world, keel=False)
    sw = next(t for t in world.parts[(B, "sea4")] if {(v[0][0], v[0][2]) for v in t} ==
              {(340.0, -364.0), (344.0, -363.0), (341.0, -360.0)})
    shifted = [(v[0], v[1], (v[0][0] * 0.01, v[0][2] * 0.02), v[3]) for v in sw]   # a distinctive affine map
    world.parts[(B, "sea4")] = [shifted if t is sw else t for t in world.parts[(B, "sea4")]]
    plan, _rep = TR.sink_footprint_plan(at)
    piece = next(t for tw in plan[B] if isinstance(tw, TR.EmitTris) for t in tw.emit()
                 if TR._tri_has(t, (343.0, -361.0)))
    for v in piece:
        assert abs(v[2][0] - v[0][0] * 0.01) < 1e-6 and abs(v[2][1] - v[0][2] * 0.02) < 1e-6


def test_the_footprint_sink_splits_kept_water_where_a_tile_line_crosses_the_old_coast(world):
    """Move the diamond's north corner to (345.715, -357.221): its north-west coast edge now crosses x 344 (where the
    crossing rounds differently by the order its ends are taken in). The kept water tri across it is split there, the
    result stays watertight, and the crossing is one and the same float in the fill and in the split water (computed
    from the edge's ends in one canonical order -- either winding of the land)."""
    for reverse in (False, True):
        world.parts.clear()
        at = _diamond(world)

        def mv(v):
            p = {(344.0, -357.0): (345.715, 0.0, -357.221)}.get((v[0][0], v[0][2]))
            return (p, v[1], v[2], v[3]) if p else v
        for part in ("terrain", "sea4"):
            world.parts[(B, part)] = [[mv(v) for v in t] for t in world.parts[(B, part)]]
        if reverse:
            world.parts[(B, "terrain")] = [list(reversed(t)) for t in world.parts[(B, "terrain")]]
        plan, rep = TR.sink_footprint_plan(at)
        assert rep["split_tris"] >= 1 and rep["miss"] == rep["overlap"] == 0
        assert _open_edges(world, plan) == [] and _t_junctions(world, plan) == []
        xs = {v[0] for tw in plan[B] if isinstance(tw, TR.EmitTris) for t in tw.emit() for v in t
              if v[0][0] == 344.0 and -357.221 > v[0][2] > -360.0}
        assert len(xs) == 1, xs


def test_the_footprint_sink_meets_stock_s_coast_t_junction_vertices(world):
    """Stock's coast T-junction: a zero-area water sliver along the diamond's south-east coast puts a kept vertex at
    (345.5, -361.5), part-way along that coast edge, and the water beside it meets the land there. The fill takes that
    vertex: no T-junction."""
    at = _diamond(world)
    w = KEEL
    S10, Ds, De, Mid = V(348, 0, -364, w), V(344, 0, -363, w), V(347, 0, -360, w), V(345.5, 0, -361.5, w)
    old = next(t for t in world.parts[(B, "sea4")] if {(v[0][0], v[0][2]) for v in t} ==
               {(348.0, -364.0), (347.0, -360.0), (344.0, -363.0)})
    world.parts[(B, "sea4")].remove(old)
    world.add(B, "sea4", [neg(S10, De, Mid), neg(S10, Mid, Ds), [Ds, Mid, De]])
    plan, rep = TR.sink_footprint_plan(at)
    fill = [t for tw in plan[B] if isinstance(tw, TR.EmitTris) for t in tw.emit()]
    assert (345.5, 0.0, -361.5) in {v[0] for t in fill for v in t}
    assert _t_junctions(world, plan) == [] and rep["miss"] == rep["overlap"] == 0


def test_the_footprint_sink_takes_a_loose_piece_over_the_island_with_it(world):
    at = _diamond(world)
    world.add(B, "terrain", [[V(343, 3, -361, LAND), V(345, 3, -361, LAND), V(344, 3, -359, LAND)]])
    _plan, rep = TR.sink_footprint_plan(at)
    assert rep["fragment_tris"] == 1 and rep["land_tris"] == 5


def test_the_footprint_sink_refusals(world):
    at = _diamond(world)
    world.add(B, "object", [[V(344, 0, -363, LAND), V(344, 1, -362, LAND), V(345, 1, -362, LAND)]])
    with pytest.raises(ValueError, match="a building stands on the island"):
        TR.sink_footprint_plan(at)
    world.parts.pop((B, "object"))
    gone = next(t for t in world.parts[(B, "sea4")] if {(v[0][0], v[0][2]) for v in t} ==
                {(340.0, -364.0), (344.0, -363.0), (341.0, -360.0)})
    world.parts[(B, "sea4")].remove(gone)
    with pytest.raises(ValueError, match="meet no water"):
        TR.sink_footprint_plan(at)
    world.parts.clear()
    at = _diamond(world)
    up = {(341.0, -360.0)}
    for part in ("terrain", "sea4"):
        world.parts[(B, part)] = [[(((v[0][0], 0.5, v[0][2]) if (v[0][0], v[0][2]) in up else v[0]),) + v[1:]
                                   for v in t] for t in world.parts[(B, part)]]
    with pytest.raises(ValueError, match="leaves the waterline"):
        TR.sink_footprint_plan(at)


def test_the_footprint_coverage_gate_is_live(world, monkeypatch):
    at = _diamond(world)
    from ff9mapkit.world import meshedit as ME
    real = ME.earclip
    monkeypatch.setattr(ME, "earclip", lambda lp, **k: real(lp, **k)[1:])
    with pytest.raises(ValueError, match="does not cover the island's footprint exactly once"):
        TR.sink_footprint_plan(at)


def test_the_whole_tile_sink_splits_a_kept_tri_running_past_a_tile_corner(world):
    """THE SPLIT WELD: west of the island, one kept coastal tri runs the whole of x 340 from -364 to -356, past the
    re-tiled tiles' corner at (340, -360): it is split there, so the two meet vertex to vertex (no T-junction)."""
    at = _island(world, keel=False, other=False)
    west = [t for t in world.parts[(B, "sea4")] if 336 <= TR._plan_centroid(t)[0] <= 340
            and -364 <= TR._plan_centroid(t)[1] <= -356]
    for t in west:
        world.parts[(B, "sea4")].remove(t)
    world.add(B, "sea4", [neg(V(336, 0, -364, KEEL), V(340, 0, -364, KEEL), V(340, 0, -356, KEEL)),
                          neg(V(336, 0, -364, SEA), V(340, 0, -356, SEA), V(336, 0, -356, SEA))])
    plan, rep = TR.sink_plan(at)
    assert rep["split_tris"] == 1 and _open_edges(world, plan) == []
    # the split tri was keel only the island explained: its pieces carry the open class, no retopo looks for it
    assert not any(isinstance(tw, TR.RetopoTris) and tw.expected for tw in plan[B])
    pieces = [t for tw in plan[B] if isinstance(tw, TR.EmitTris) for t in tw.emit()
              if TR._plan_centroid(t)[0] < 340]
    assert len(pieces) == 2 and all((340.0, 0.0, -360.0) in {v[0] for v in t} for t in pieces)
    assert {topo(t) for t in pieces} == {57}


def test_a_joined_island_sinks_alone_by_its_footprint_and_cluster_sinks_them_together(world, monkeypatch):
    """sink_auto_plan: the whole-tile sink first; refused at another coast (SinkJoined) or by a building in its tiles
    (SinkCrowded), the island alone by its footprint; ``cluster`` sinks the island and the land the refusal names."""
    at = _diamond(world)
    calls = []
    real_plan = TR.sink_plan

    def joined(pts, **k):
        calls.append(pts)
        raise TR.SinkJoined("the coastal sea round the island runs on into another coast's (test)", (360.0, -340.0))
    monkeypatch.setattr(TR, "sink_plan", joined)
    plan, rep = TR.sink_auto_plan(at)
    assert rep["fill"] == "footprint" and rep["joined"].startswith("the coastal sea round the island runs on")
    monkeypatch.setattr(TR, "sink_plan", lambda pts, **k: (_ for _ in ()).throw(TR.SinkCrowded("a 'object' tri")))
    assert TR.sink_auto_plan(at)[1]["fill"] == "footprint"
    # the cluster: island B (88..89, -91..-90) joins; the second plan closes
    world.add(B, "terrain", pyramid(88, -86, 2))

    def cluster(pts, **k):
        on_b = len(pts) > 1 and any(TR._tri_has(t, tuple(pts[1])) for t in pyramid(88, -86, 2))
        if not on_b:            # a refusal nearer the island than the other land: the cluster must skip its own
            raise TR.SinkJoined("runs on into another coast's", (349.0, -352.0))
        return real_plan(pts[:1], **k)
    monkeypatch.setattr(TR, "sink_plan", cluster)
    _plan, rep = TR.sink_auto_plan(at, cluster=True)
    assert len(rep["members"]) == 2 and TR._tri_has(pyramid(88, -86, 2)[0], tuple(rep["members"][1])) or \
        any(TR._tri_has(t, tuple(rep["members"][1])) for t in pyramid(88, -86, 2))
    # no land within reach of the refusal: the cluster does not close
    monkeypatch.setattr(TR, "sink_plan", lambda pts, **k: (_ for _ in ()).throw(
        TR.SinkJoined("runs on into another coast's", (500.0, -500.0))))
    with pytest.raises(ValueError, match="no island there closes the cluster"):
        TR.sink_cluster_plan(at)


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


def test_real_islands_in_shallow_water_sink_and_a_shared_beach_is_refused():
    """(17,16): a 502u2 lagoon island re-bands as mid water with seven transition tiles; (16,16)+(17,16): a beach island
    takes its own beach water with it; (14,1)-(15,1): an island whose beach water runs on to the next coast is
    refused."""
    _need_install()
    s = TR.sink("FF9CustomMap_test_nonexistent", (1177.333, -1065.824), dry_run=True)
    assert s["clean"] and s["bands"] == {"sea3": 72, "sea5": 7, "sea4": 0} and s["miss"] == 0
    s = TR.sink("FF9CustomMap_test_nonexistent", (1082.667, -1057.732), dry_run=True)
    assert s["clean"] and s["shore_tris"] == 32 and s["bands"]["sea3"] == 64
    with pytest.raises(ValueError, match="shore water .* runs on into another coast's"):
        TR.sink_plan((1089.672, -106.59))


def test_cli_cluster_flag_and_the_footprint_report(world, monkeypatch, capsys):
    seen = {}
    monkeypatch.setattr(TR, "sink", lambda mod, at, **k: seen.update(k) or {
        "land_tris": 489, "land_u2": 1861.3, "max_y": 11.3, "blocks": [[6, 4]], "tiles": 160, "fill_tris": 360,
        "fill_area": 0, "sea_replaced": 0, "edge_welds": 0, "keel_to_open": 100, "entrance_tris": 0,
        "bands": {"sea3": 0, "sea5": 0, "sea4": 86}, "shore_tris": 0, "fill": "footprint", "cells_whole": 86,
        "cells_partial": 74, "split_tris": 47, "joined": "the coastal sea ...", "per_block": {}, "clean": True,
        "deployed": []})
    args = cli.build_parser().parse_args(["world-sink", "--mod-folder", "MOD", "--at", "441.992", "-311.975",
                                          "--cluster"])
    assert cli._cmd_world_sink(args) == 0 and seen["cluster"] is True
    out = capsys.readouterr().out
    assert "the island alone goes" in out and "86 whole cells re-tiled (sea4 86), 74 part-cells" in out
    assert "47 kept water tris split" in out


def test_real_shimmering_sinks_alone_its_islets_kept_and_as_a_cluster():
    """Shimmering Island (disc 4 removes it itself and keeps its seven islets): its coastal sea runs on into its
    islets', so it sinks alone by its footprint, exact; --cluster sinks it with the two islets its water joins. The
    (0,0) island carries a building and is refused."""
    _need_install()
    _plan, rep = TR.sink_auto_plan((441.992, -311.975))
    assert rep["fill"] == "footprint" and rep["land_tris"] == 489 and rep["miss"] == rep["overlap"] == 0
    assert (rep["cells_whole"], rep["cells_partial"], rep["split_tris"]) == (86, 74, 47)
    assert rep["footprint_u2"] == rep["fill_u2"] and sorted(map(tuple, rep["blocks"])) == [(6, 4), (6, 5), (7, 4),
                                                                                             (7, 5)]
    _plan, rep = TR.sink_cluster_plan((441.992, -311.975))
    assert len(rep["members"]) == 3
    with pytest.raises(ValueError, match="a building stands on the island"):
        TR.sink_auto_plan((9.909, -22.582))
