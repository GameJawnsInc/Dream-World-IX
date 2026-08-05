"""Cross-donor FUSE (world/fuse.py): compose several verbatim transplants into ONE
contiguous custom region. The land never knits (coastlines are components); the WATER does
(sea4 is the anti-tiling quadrant band -- a sea4-vs-sea4 block border is always legal, it is
why a carried island already sits clean next to prefab ocean). fuse_layout closes the gap no
single-placement gate covers: two adjacent deploys' shared border, certified row-by-row from
the frame_profile each transplant_region summary now emits."""
from __future__ import annotations

import pytest

from ff9mapkit.world import fuse as FU, transplant as TR

NRM = (0.0, 1.0, 0.0)


def _game_ready() -> bool:
    from ff9mapkit import config
    try:
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


def _v(x, y, z, uv=(0.5, 0.5), idall=12800.0):
    return ((float(x), float(y), float(z)), NRM, tuple(uv), (float(idall), 0.0, 0.0, 1.0))


def _quad(x0, x1, z0, z1, *, y=0.0, idall=12800.0, uv=(0.5, 0.5)):
    a, b = _v(x0, y, z1, uv, idall), _v(x1, y, z1, uv, idall)
    c, d = _v(x1, y, z0, uv, idall), _v(x0, y, z0, uv, idall)
    return [[a, b, d], [b, c, d]]


def _fake_world(blocks):
    def fake(bx, by, part, **_k):
        return [list(t) for t in blocks.get((bx, by, part), [])]
    return fake


def _mini_donor(border_part="sea4"):
    """Donor (1,1): a 16x16 land pad centred in a full-cell sea, the EAST border column
    speaking ``border_part`` (world frame x 64..128, z -128..-64), all 4u lattice tiles."""
    tiles = {"terrain": [], "sea4": [], "sea1": [], "sea3": []}
    for xi in range(16):
        for zi in range(16):
            x0, z0 = 64.0 + 4.0 * xi, -128.0 + 4.0 * zi
            part = "terrain" if (6 <= xi < 10 and 6 <= zi < 10) else \
                (border_part if xi == 15 else "sea4")
            tiles[part] += _quad(x0, x0 + 4.0, z0, z0 + 4.0,
                                 idall=(12800.0 if part == "terrain" else 228.0))
    return {(1, 1, p): t for p, t in tiles.items() if t}


def test_frame_profile_emission(monkeypatch):
    """The summary's frame_profile: per-edge deployed border cells + per-4u-row on-plane
    parts + lattice flags; an undeployed border cell contributes no rows."""
    monkeypatch.setattr(TR, "world_tris", _fake_world(_mini_donor()))
    s = TR.transplant_region("UNUSED", cell=(5, 5), donor=(1, 1), size=(1, 1),
                             shift=(0.0, 0.0), land_margin=0.0, dry_run=True)
    fp = s["frame_profile"]
    assert set(fp) == {"W", "E", "N", "S"}
    assert fp["E"]["plane"] == 64.0 and fp["E"]["deployed"] == [0]
    assert len(fp["E"]["rows"]) == 16
    assert all(r["parts"] == ["sea4"] and r["lattice"] for r in fp["E"]["rows"].values())
    # 2x1 rect with an EMPTY east cell: the E edge is prefab (no deployed cells, no rows)
    s2 = TR.transplant_region("UNUSED", cell=(5, 5), donor=(1, 1), size=(2, 1),
                              shift=(0.0, 0.0), land_margin=0.0, dry_run=True)
    fe = s2["frame_profile"]["E"]
    assert fe["deployed"] == [] and fe["rows"] == {}


def test_fuse_layout_water_border_certifies(monkeypatch):
    """Two mini islands stacked vertically: the shared border (A.S vs B.N) is pure sea4 on
    both sides -> the whole layout certifies; the border gate names the plane and covers
    every 4u row of the overlap."""
    monkeypatch.setattr(TR, "world_tris", _fake_world(_mini_donor()))
    out = FU.fuse_layout("UNUSED", [
        {"cell": (5, 5), "donor": (1, 1), "size": (1, 1)},
        {"cell": (5, 6), "donor": (1, 1), "size": (1, 1)},
    ], dry_run=True)
    assert out["clean"] is True
    fg = next(g for g in out["fuse_gates"] if g["gate"].startswith("fuse["))
    assert fg["ok"] and fg["rows"] == 16 and fg["plane"] == -64.0 * 6
    assert fg["n_bad"] == 0 and fg["grade_jumps"] == 0


def test_fuse_layout_shallow_at_border_refuses(monkeypatch):
    """A donor whose east border column speaks sea1 (a shore-bound SHALLOW system) may not
    fuse against another placement -- every row flags blocked:sea1."""
    monkeypatch.setattr(TR, "world_tris", _fake_world(_mini_donor(border_part="sea1")))
    out = FU.fuse_layout("UNUSED", [
        {"cell": (5, 5), "donor": (1, 1), "size": (1, 1)},
        {"cell": (6, 5), "donor": (1, 1), "size": (1, 1)},   # B.W faces A's sea1 E column
    ], dry_run=True)
    assert out["clean"] is False
    fg = next(g for g in out["fuse_gates"] if g["gate"].startswith("fuse["))
    assert not fg["ok"] and fg["n_bad"] == 16
    assert fg["bad"][0]["a"] == "blocked:sea1"


def test_fuse_layout_grade_jump_reported_not_failed(monkeypatch):
    """A sea3 border column facing sea4 (skipping the sea5 blend) is an adjacency real data
    never shows -- REPORTED as grade_jumps, but the border still certifies (open water)."""
    monkeypatch.setattr(TR, "world_tris", _fake_world(_mini_donor(border_part="sea3")))
    out = FU.fuse_layout("UNUSED", [
        {"cell": (5, 5), "donor": (1, 1), "size": (1, 1)},
        {"cell": (6, 5), "donor": (1, 1), "size": (1, 1)},
    ], dry_run=True)
    assert out["clean"] is True
    fg = next(g for g in out["fuse_gates"] if g["gate"].startswith("fuse["))
    assert fg["ok"] and fg["grade_jumps"] == 16


def _offlat_donor(border_part="sea3"):
    """The mini donor with ONE border tile's frame edge split by a mid-edge vert (2u off
    the 4u lattice) -- the conforming-vert class the Iron Gate's reef carries on its
    channel frame."""
    blocks = _mini_donor(border_part=border_part)
    tiles = blocks[(1, 1, border_part)]
    # the border column tile at zi == 5: x 124..128, z -108..-104
    x0, x1, z0, z1 = 124.0, 128.0, -108.0, -104.0
    idall = 228.0
    def kx(t3):
        xs = [v[0][0] for v in t3]
        zs = [v[0][2] for v in t3]
        return min(xs) == x0 and min(zs) == z0
    kept = [t for t in tiles if not kx(t)]
    assert len(kept) == len(tiles) - 2, "fixture tile not found"
    a, b = _v(x0, 0, z1, idall=idall), _v(x1, 0, z1, idall=idall)
    c, d = _v(x1, 0, z0, idall=idall), _v(x0, 0, z0, idall=idall)
    m = _v(x1, 0, z0 + 2.0, idall=idall)          # mid-edge vert ON the frame, off-lattice
    blocks[(1, 1, border_part)] = kept + [[a, b, m], [a, m, c], [a, c, d]]
    return blocks


def test_fuse_offlattice_water_row_certifies(monkeypatch):
    """THE STRAIT UNLOCK (study 3): an off-lattice vert on a PURE open-water row is a
    conforming vert of the donor's own sheet -- it cannot tear land, so the row fuses
    against another placement's water."""
    monkeypatch.setattr(TR, "world_tris", _fake_world(_offlat_donor("sea3")))
    out = FU.fuse_layout("UNUSED", [
        {"cell": (5, 5), "donor": (1, 1), "size": (1, 1)},
        {"cell": (6, 5), "donor": (1, 1), "size": (1, 1)},
    ], dry_run=True)
    fg = next(g for g in out["fuse_gates"] if g["gate"].startswith("fuse["))
    assert fg["ok"] and fg["n_bad"] == 0, fg["bad"]


def test_fuse_offlattice_shallow_row_still_refuses(monkeypatch):
    """FAIL-CLOSED (F-3): the same off-lattice vert on a SHALLOW (sea1) row keeps the hard
    refusal -- the wash is shore-bound copy-only; only pure open water earns the tolerance."""
    monkeypatch.setattr(TR, "world_tris", _fake_world(_offlat_donor("sea1")))
    out = FU.fuse_layout("UNUSED", [
        {"cell": (5, 5), "donor": (1, 1), "size": (1, 1)},
        {"cell": (6, 5), "donor": (1, 1), "size": (1, 1)},
    ], dry_run=True)
    fg = next(g for g in out["fuse_gates"] if g["gate"].startswith("fuse["))
    assert not fg["ok"]
    states = {b["a"] for b in fg["bad"]}
    assert "off-lattice" in states, states


def test_fuse_layout_rect_overlap_refuses(monkeypatch):
    monkeypatch.setattr(TR, "world_tris", _fake_world(_mini_donor()))
    out = FU.fuse_layout("UNUSED", [
        {"cell": (5, 5), "donor": (1, 1), "size": (1, 1)},
        {"cell": (5, 5), "donor": (1, 1), "size": (1, 1)},
    ], dry_run=True)
    assert out["clean"] is False
    ov = next(g for g in out["fuse_gates"] if g["gate"] == "rect-overlap")
    assert not ov["ok"] and ov["pairs"] == [[0, 1]]


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_fuse_real_two_island_layout():
    """THE FIRST CROSS-DONOR FUSE (real data): (9,5)+2x3 stacked on (10,17)+2x2 in the free
    ocean columns 0-1 rows 7-11 -- the shared border at z=-640 is pure sea4 / prefab on
    every row (the (10,17) donor's N edge deploys only its data column; the empty column
    faces prefab). The same donor pair fused E|W instead REFUSES: (10,17)'s WEST frame
    carries its live sea1 shore system (it continues into the real neighbour in situ), so
    that edge can only ever face prefab."""
    out = FU.fuse_layout("UNUSED", [
        {"cell": (0, 7), "donor": (9, 5), "size": (2, 3)},
        {"cell": (0, 10), "donor": (10, 17), "size": (2, 2)},
    ], dry_run=True)
    assert out["clean"] is True, out["fuse_gates"]
    fg = next(g for g in out["fuse_gates"] if g["gate"].startswith("fuse["))
    assert fg["gate"] == "fuse[0.S|1.N]" and fg["plane"] == -640.0
    assert fg["rows"] == 32 and fg["n_bad"] == 0 and fg["grade_jumps"] == 0
    # the negative: rot=270 turns (10,17)'s shore-bearing W edge into its N edge
    out2 = FU.fuse_layout("UNUSED", [
        {"cell": (0, 7), "donor": (9, 5), "size": (2, 3)},
        {"cell": (0, 10), "donor": (10, 17), "size": (2, 2), "rot": 270},
    ], dry_run=True)
    assert out2["clean"] is False
    fg2 = next(g for g in out2["fuse_gates"] if g["gate"].startswith("fuse["))
    assert not fg2["ok"] and any(b["b"].startswith("blocked:sea1") for b in fg2["bad"])
