"""The custom-outline mint (``island.build_landmass(outline=, rim_at=, shore_origin=)``, world-river rung 1), THE
CELL-CLIPPED LIP (the lip-streak fix), and the identity nets that hold every blob mint byte for byte through both.

THE IDENTITY NETS hash every block's tris and POS/NRM/UV/TAN channels as f64, plus the outline and the rim, over every
path the blob mint takes -- one lobe, island E's three, two lobes, rolling relief, desert ground, the big-mint
refinement, the seam wrap into column -1 and (install-gated) a beach mint. A miss means a blob mint changed.

* BLOB_MINTS' digests (LEGACY) -- frozen from the code BEFORE the custom outline existed; ``cell_lip=False`` must
  still give them bit for bit (the pre-fix mint the July world-forest / world-hill / world-mountain benches were
  proven on).
* CELL_LIP_DIGESTS -- the default mint, RE-FROZEN when the cell-clipped lip landed. Why they moved: the streaked
  grass band along every kit cliff lip (a lip tri spanning two 4u cells wore its centroid cell's CLAMPED mains map,
  near rank 1). The crest is now snapped onto and cut at the lattice lines and the grass clipped per cell, so the lip
  tris, the crest and the wall beside each cut changed; the interior (the mains field, the stamps, every tri over 6u
  from the rim) did not -- ``test_cell_lip_changes_only_the_lip`` holds that.
* The beach mint keeps the old lip by design (THE LADDER MINT is falsified and superseded): one digest."""
from __future__ import annotations

import hashlib
import math
import warnings

import numpy as np
import pytest

from ff9mapkit import config
from ff9mapkit.world import island as I
from ff9mapkit.world.extract import CH_NRM, CH_POS, CH_TAN, CH_UV

#: the blob mints and their LEGACY (pre-fix, ``cell_lip=False``) digests
BLOB_MINTS = {
    "r20-seed5": (dict(center=(224.0, -96.0), base_radius=20.0, seed=5.0),
                  "2f411c55b041f59a861d73589b86b2251728bcd50032fa5acfbd57b4dd143789"),
    "island-E": (dict(center=(344.0, -1152.0), base_radius=46.0, seed=55.0, lobes=3, n_patches=2),
                 "dbbeb80d4df9900ac5c551270a54b5f0146c1f5ca7b39a394aa530349747e64b"),
    "uaho-bench": (dict(center=(160.0, -1246.0), base_radius=31.0, seed=42.0, lobes=1, n_patches=0),
                   "f7cf8efcaa1877c922921e68dff30fc4fdd047d4a79febb0ffe061e85338c14b"),
    "relief": (dict(center=(672.0, -608.0), base_radius=44.0, seed=None, lobes=1, relief_amp=1.3),
               "db76acaab789499f193fa7585f98219894ebb6373df5ffc3af65201ce5720238"),
    "desert": (dict(center=(224.0, -96.0), base_radius=20.0, seed=5.0, ground="desert"),
               "650b0712cdade32069603edd8730643a17541df3dced0dd169a69c3f728c8045"),
    "big-r69": (dict(center=(800.0, -640.0), base_radius=69.0, seed=2.0),
                "9cd6702d80a195ef089fd83ace51cf6c06fc426b7ea9cc7c064dcfbfca614cc6"),
    "seam-wrap": (dict(center=(8.0, -300.0), base_radius=24.0, seed=3.0),
                  "45c73cca82ea74beec2d23f4e2e6b1b1dbf489f03c7785d16d6d9d74e12c1690"),
    "lobes2": (dict(center=(500.0, -400.0), base_radius=30.0, seed=11.0, lobes=2),
               "0ec1fadb7bf20983421ed7a2116fd13c6b19c76916b5d4f6e73968f9a47923e2"),
}
BEACH_MINT = (dict(center=(672.0, -608.0), base_radius=18.0, seed=9.0, beach={"bearing": (110.0, 160.0)}),
              "651c111fe957e448a6256c84ca2bc3780e39c7aef6c4b31a955168daa25436a4")
#: the same blob mints, DEFAULT path (the cell-clipped lip) -- re-frozen with the lip-streak fix (module docstring)
CELL_LIP_DIGESTS = {
    "big-r69": "8a19a89372b47509c2c0cca4eade2fa22387705915d001b1bbbd90e3a0af3f34",
    "desert": "c7f7c5182ca97aa539f2a024995ad0b6b4b739ba1585979f22525c7677a8c817",
    "island-E": "2b41b3b234495b227e3ec47474bc23f4b96775d8eb53391e628708d438dd3693",
    "lobes2": "15fca2d0f37e2681a2fce538a69bd4d450e4e97c5adf45a15fa89db1609b9ed4",
    "r20-seed5": "5bcee48a2423492309140ff5a07e32c45cbaf3273ebe979efcc0a4362d34ac30",
    "relief": "2ba3333d9bd244091f83491d0b285fe8793a1372ed85ac551fa9b38fead87b8e",
    "seam-wrap": "fce38ac484377f256c82970064356d4e91c104cd67185241a37433acfc9f0cfb",
    "uaho-bench": "27699d8068a788bff7bb581728ad0560c91b3eb03657d5cb13203441a7dc9ccb",
}
#: blob mints whose PRE-FIX lip streaks: the detector's count on ``cell_lip=False`` (found by a 60-mint sweep)
STREAKY_MINTS = {
    "r40-seed7": (dict(center=(672.0, -608.0), base_radius=40.0, seed=7.0, n_patches=0), 2),
    "r40-seed1": (dict(center=(672.0, -608.0), base_radius=40.0, seed=1.0, n_patches=0), 1),
    "r46-seed1": (dict(center=(672.0, -608.0), base_radius=46.0, seed=1.0, n_patches=0), 2),
    "r18-seed42-lobes3": (dict(center=(672.0, -608.0), base_radius=18.0, seed=42.0, lobes=3, n_patches=0), 1),
}


def mint_digest(built) -> str:
    h = hashlib.sha256()
    for blk in sorted(built["blocks"]):
        bm = built["blocks"][blk]
        h.update(repr(blk).encode())
        h.update(np.asarray(bm.tris, dtype="<i4").tobytes())
        for ch in (CH_POS, CH_NRM, CH_UV, CH_TAN):
            h.update(np.asarray(bm.chan_arrays[ch], dtype="<f8").tobytes())
    h.update(np.asarray(built["outline"], dtype="<f8").tobytes())
    h.update(np.asarray(built["rim"], dtype="<f8").tobytes())
    return h.hexdigest()


@pytest.mark.parametrize("name", sorted(BLOB_MINTS))
def test_legacy_blob_mints_are_byte_identical(name):
    kw, sha = BLOB_MINTS[name]
    assert mint_digest(I.build_landmass(**kw, cell_lip=False)) == sha, f"the {name} pre-fix (cell_lip=False) mint moved"


@pytest.mark.parametrize("name", sorted(BLOB_MINTS))
def test_blob_mints_are_byte_identical(name):
    kw, _legacy = BLOB_MINTS[name]
    assert mint_digest(I.build_landmass(**kw)) == CELL_LIP_DIGESTS[name], f"the {name} blob mint moved"


# ---- THE LIP-STREAK DETECTOR + THE CELL-CLIPPED LIP ---------------------------------------------------------------

def test_uv_streak_reads_the_jacobian_in_the_tris_own_plane():
    """The instrument, calibrated: the mains map (4u -> one quadrant, 0.0605 u x 0.0303 v) reads its own 2:1; a map
    with two corners clamped together reads rank 1; a tilted tri is judged in its own plane, not in plan; walls and
    tiny tris are not judged."""
    sq = [(0.0, 3.2, 0.0), (4.0, 3.2, 0.0), (0.0, 3.2, 4.0)]
    mains = [(0.0, 0.0), (0.0605, 0.0), (0.0, 0.0303)]
    assert I.uv_streak(sq, mains, ratio=0.0) == pytest.approx(0.0605 / 0.0303)
    assert I.uv_streak(sq, mains) is None
    assert I.uv_streak(sq, [(0.0, 0.0), (0.0605, 0.0), (0.0605, 1e-9)]) > 1e6
    assert I.uv_streak(sq, [(0.0, 0.0), (0.0605, 0.0), (0.0605, 0.0)]) == math.inf
    tilt = [(0.0, 0.0, 0.0), (4.0, 2.0, 0.0), (0.0, 0.0, 4.0)]          # its x edge is sqrt(20) long in its plane
    assert I.uv_streak(tilt, [(0.0, 0.0), (math.sqrt(20.0), 0.0), (0.0, 4.0)], ratio=0.0) == pytest.approx(1.0)
    assert I.uv_streak([(0.0, 0.0, 0.0), (4.0, 0.0, 0.0), (0.0, 3.2, 1.0)], mains, ratio=0.0) is None   # a wall
    assert I.uv_streak([(0.0, 3.2, 0.0), (0.3, 3.2, 0.0), (0.0, 3.2, 0.3)], mains, ratio=0.0) is None  # 0.045 u^2


@pytest.mark.parametrize("name", sorted(STREAKY_MINTS))
def test_the_cell_lip_mints_no_lip_streak(name):
    """THE DETECTOR, red on the old mint and green on the new: these mints' lips wore streaked grass before the fix
    (a lip tri spanning two cells, two corners clamped onto one edge); the cell-clipped lip mints none."""
    kw, n_old = STREAKY_MINTS[name]
    legacy = I.build_landmass(**kw, cell_lip=False)
    old = I.lip_streak_tris(legacy)
    assert len(old) == n_old and all(fam == "main" for *_x, fam in old)
    assert I.verify_landmass(legacy)["lip_streaks"] == n_old
    built = I.build_landmass(**kw)
    assert I.lip_streak_tris(built) == []
    rep, rep0 = I.verify_landmass(built), I.verify_landmass(legacy)
    assert rep["lip_streaks"] == 0
    assert (rep["cracks"], rep["open_edges"], rep["holes"], rep["down_facing"], rep["grass_over_8u"],
            rep["missing_faces"]) == (0,) * 6, rep
    assert rep["walk_filter_fails"] == rep0["walk_filter_fails"]   # the wider sweep's acute corners, as before


@pytest.mark.parametrize("name", sorted(BLOB_MINTS))
def test_every_frozen_blob_mint_is_streak_free_and_clean(name):
    kw, _legacy = BLOB_MINTS[name]
    built = I.build_landmass(**kw)
    assert I.lip_streak_tris(built) == []
    rep = I.verify_landmass(built)
    assert (rep["cracks"], rep["open_edges"], rep["holes"], rep["down_facing"], rep["walk_filter_fails"],
            rep["grass_over_8u"], rep["missing_faces"], rep["lip_streaks"]) == (0,) * 8 and rep["clean"], rep


@pytest.mark.parametrize("name", ["island-E", "uaho-bench", "big-r69"])
def test_cell_lip_changes_only_the_lip(name):
    """THE LIP-ONLY CHANGE: against the pre-fix mint, the mains field holds on every pre-fix cell, the stamps land
    where they did, and no tri more than 6u from the rim differs -- a re-mint keeps its interior, so every
    world-forest / world-hill / world-mountain site stays lawful."""
    kw, _legacy = BLOB_MINTS[name]
    old, new = I.build_landmass(**kw, cell_lip=False), I.build_landmass(**kw)
    assert all(new["mains_field"][c] == qo for c, qo in old["mains_field"].items())
    assert new["placements"] == old["placements"]

    def tris(b):
        gpos, gtris, gmeta = b["world"]["pos"], b["world"]["tris"], b["world"]["meta"]
        return {frozenset((tuple(gpos[v]), tuple(uv)) for v, uv in zip(t, m[3])) for t, m in zip(gtris, gmeta)}
    rim = np.asarray(old["rim"])
    gone = tris(old) - tris(new)
    assert gone
    far = [t for t in gone if min(float(np.hypot(rim[:, 0] - p[0], rim[:, 1] - p[2]).min()) for p, _uv in t) > 6.0]
    assert far == []


def test_lip_grass_wears_its_own_cells_map_exactly():
    """THE CELL-CLIPPED LIP's mechanism: every grass tri lies inside ONE 4u cell and its UVs are that cell's minted
    map, unclamped -- so every flat grass tri, the lip included, reads the mains map's own 2:1."""
    from ff9mapkit.world import grassland as G
    built = I.build_landmass(center=(672.0, -608.0), base_radius=40.0, seed=7.0, n_patches=0)
    gpos, gtris, gmeta = built["world"]["pos"], built["world"]["tris"], built["world"]["meta"]
    field = built["mains_field"]
    judged = 0
    for tri, (_blk, _idall, fam, uvv) in zip(gtris, gmeta):
        if fam != "main":
            continue
        pts = [gpos[v] for v in tri]
        cell = (math.floor(sum(p[0] for p in pts) / 12.0), math.floor(sum(p[2] for p in pts) / 12.0))
        assert all(4 * cell[0] <= p[0] <= 4 * cell[0] + 4 and 4 * cell[1] <= p[2] <= 4 * cell[1] + 4 for p in pts), pts
        assert all(abs(a - b) < 1e-12 for p, uv in zip(pts, uvv)
                   for a, b in zip(G.ground_uv(p[0], p[2], cell, *field[cell]), uv))
        r = I.uv_streak(pts, uvv, ratio=0.0)
        if r is not None:
            judged += 1
            assert r == pytest.approx(0.0605 / 0.0303, abs=0.01), (pts, uvv)
    assert judged > 100


def test_the_wall_keeps_its_own_rock_texture_through_the_cuts():
    """THE CREST CUTS on the wall must not re-map the rock (in game 2026-10-20, the first cell-lip build: thin diagonal
    seams down the rock under every cut lip). A cut has no base vertex of its own, so the wall stays seamless only as
    its quad's own split cut up in its own plane: per crest segment, every piece holding two crest corners fans from
    ONE base vertex, and every crest corner it holds lies ON that segment's crest edge -- then each piece wears the
    very affine rock map the uncut tri did."""
    built = I.build_landmass(center=(672.0, -608.0), base_radius=40.0, seed=7.0, n_patches=0)
    assert built["crest_cuts"] > 40
    gpos, gtris, gmeta = built["world"]["pos"], built["world"]["tris"], built["world"]["meta"]
    outline, rim, n = built["outline"], built["rim"], len(built["outline"])
    at = {o: k for k, o in enumerate(outline)}

    def on_edge(c, a, b):
        ex, ez = b[0] - a[0], b[1] - a[1]
        cx, cz = c[0] - a[0], c[2] - a[1]
        return abs(ex * cz - ez * cx) <= 1e-9 * math.hypot(ex, ez) and -1e-12 <= ex * cx + ez * cz <= ex * ex + ez * ez

    fans = {}
    for tri, (_b, _i, fam, _uv) in zip(gtris, gmeta):
        pts = [tuple(gpos[v]) for v in tri]
        base = [p for p in pts if p[1] == 0.0]
        crest = [p for p in pts if p[1] == 3.2]
        if fam != "rock" or len(base) != 1 or len(crest) != 2:
            continue                                         # a switch tri, or a block-border clip piece
        k = at[(base[0][0], base[0][2])]
        seg = next((i for i in ((k - 1) % n, k) if all(on_edge(c, rim[i], rim[(i + 1) % n]) for c in crest)), None)
        assert seg is not None, f"a wall piece's crest corners lie off its crest edge: {crest}"
        fans.setdefault(seg, set()).add(base[0])
    assert len(fans) > 50 and all(len(b) == 1 for b in fans.values()), {s: b for s, b in fans.items() if len(b) > 1}


@pytest.mark.parametrize("name", ["r40-seed7", "r46-seed1"])
def test_the_cut_wall_wears_the_uncut_walls_rock(name):
    """The pieces' UVs are the uncut tri's own map (in game 2026-10-20, the second cell-lip build: a seam where the
    rock strip wraps -- the uncut tri was window-translated as ONE, its pieces each on their own). Every cell-lip rock
    tri lying in a pre-fix rock tri's plane wears that tri's affine U at its corners (to 0.003, the visibility line;
    modulo the strip, whose two ends tile), V on the same rows. A snapped crest moved its tris off plane: not judged."""
    kw, _n = STREAKY_MINTS[name]
    old, new = I.build_landmass(**kw, cell_lip=False), I.build_landmass(**kw)

    def rock(b):
        gpos, gtris, gmeta = b["world"]["pos"], b["world"]["tris"], b["world"]["meta"]
        return [(np.array([gpos[v] for v in t]), np.array(m[3])) for t, m in zip(gtris, gmeta) if m[2] == "rock"]
    old_r, new_r = rock(old), rock(new)
    centres = np.array([P.mean(axis=0) for P, _ in old_r])
    strip = I.ROCK_U[1] - I.ROCK_U[0]

    def bary(P, q):
        v0, v1, v2 = P[1] - P[0], P[2] - P[0], q - P[0]
        d00, d01, d11, d20, d21 = v0 @ v0, v0 @ v1, v1 @ v1, v2 @ v0, v2 @ v1
        den = d00 * d11 - d01 * d01
        v, w = (d11 * d20 - d01 * d21) / den, (d00 * d21 - d01 * d20) / den
        return np.array([1.0 - v - w, v, w])
    judged, off = 0, []
    for P, UV in new_r:
        c = P.mean(axis=0)
        best = None
        for k in np.argsort(np.linalg.norm(centres - c, axis=1))[:8]:
            Q, W = old_r[k]
            n = np.cross(Q[1] - Q[0], Q[2] - Q[0])
            if np.linalg.norm(n) < 1e-9 or bary(Q, c).min() < -0.02:
                continue
            d = abs((c - Q[0]) @ (n / np.linalg.norm(n)))
            if best is None or d < best[0]:
                best = (d, Q, W)
        if best is None or best[0] > 0.05:
            continue
        judged += 1
        _d, Q, W = best
        for q, (u, v) in zip(P, UV):
            b = bary(Q, q)
            du = abs(float(b @ W[:, 0]) - u) % strip
            if min(du, strip - du) > 0.003 or abs(float(b @ W[:, 1]) - v) > 0.003:
                off.append(tuple(np.round(q, 2)))
    assert judged > 100 and off == [], off[:6]


def test_the_crest_is_cut_on_the_lattice_and_the_wall_fans_to_it():
    """The crest half: no crest edge strictly crosses a 4u lattice line (each cut sits exactly on one), and the rock
    band welds to every cut as a crest corner, V on the language's top row."""
    built = I.build_landmass(center=(672.0, -608.0), base_radius=40.0, seed=7.0, n_patches=0)
    assert built["crest_cuts"] > 40
    gpos, gtris, gmeta = built["world"]["pos"], built["world"]["tris"], built["world"]["meta"]
    crest = {}
    top_v = I.ROCK_V[0] + (I.ROCK_V[1] - I.ROCK_V[0])
    for t, (_b, _i, fam, uvv) in zip(gtris, gmeta):
        if fam == "rock":
            for v, (_u, vv) in zip(t, uvv):
                if gpos[v][1] in (0.0, 3.2):                   # a block-border clip point mid-face lerps its V
                    assert vv == (top_v if gpos[v][1] > 0.0 else I.ROCK_V[0])
            hi = [tuple(gpos[v]) for v in t if gpos[v][1] == 3.2]
            for a, b in zip(hi, hi[1:]):                       # a crest edge of the band
                for k in (0, 2):
                    lo, up = sorted((a[k], b[k]))
                    assert math.floor(lo / 4.0) == math.floor(up / 4.0) or up % 4.0 == 0.0, (a, b)
            crest.update((p, None) for p in hi)
    assert sum(1 for p in crest if p[0] % 4.0 == 0.0 or p[2] % 4.0 == 0.0) >= built["crest_cuts"]


def test_beach_mint_is_byte_identical():
    try:
        import UnityPy  # noqa: F401
        ok = (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        ok = False
    if not ok:
        warnings.warn("the beach mint's identity went unchecked in this run: no FF9 install + UnityPy (its pins read "
                      "the stock beach). Re-run in the MAIN repo.", UserWarning)
        pytest.skip("needs the FF9 install + UnityPy (see the warnings summary)")
    kw, sha = BEACH_MINT
    assert mint_digest(I.build_landmass(**kw)) == sha


# ---- the custom outline -------------------------------------------------------------------------------------------

def wobbly_ring(cx=672.37, cz=-608.21, r=26.0, n=30, ccw=True):
    """A closed ring off the 4u lattice, gently wobbling (no blob generator involved)."""
    pts = [(cx + (r + 2.0 * math.sin(3 * a)) * math.cos(a), cz + (r + 2.0 * math.sin(3 * a)) * math.sin(a))
           for a in np.linspace(0.0, 2 * math.pi, n, endpoint=False)]
    return pts if ccw else pts[::-1]


@pytest.mark.parametrize("ccw", [True, False])
def test_custom_outline_mints_a_closed_wall(ccw):
    """Either winding: the ring is the coast verbatim, the rim insets INSIDE it, and every geometry gate is clean --
    no crack, no open edge, no hole, nothing wound down, nothing the engine's walk filter drops, no lip streak. The
    rim is the exact rim_run inset, bar THE CELL-CLIPPED LIP's snap: a crest coordinate within LATTICE_SNAP of a
    lattice line sits on it (the pre-fix mint keeps the inset exactly)."""
    ring = wobbly_ring(ccw=ccw)
    built = I.build_landmass(center=(672.0, -608.0), outline=ring, n_patches=0)
    assert built["outline"] == ring
    assert all(I._pip(x, z, ring) for x, z in built["rim"])
    legacy = I.build_landmass(center=(672.0, -608.0), outline=ring, n_patches=0, cell_lip=False)
    assert all(abs(math.dist(o, r) - 1.0) < 1e-9 for o, r in zip(ring, legacy["rim"]))   # rim_run 1, exactly
    snapped = 0
    for (rx, rz), (ex, ez) in zip(built["rim"], legacy["rim"]):
        for got, want in ((rx, ex), (rz, ez)):
            if got != want:
                assert got % 4.0 == 0.0 and abs(got - want) < I.LATTICE_SNAP, (got, want)
                snapped += 1
    assert 0 < snapped < len(ring)
    rep = I.verify_landmass(built)
    assert (rep["cracks"], rep["open_edges"], rep["holes"], rep["down_facing"], rep["walk_filter_fails"],
            rep["grass_over_8u"], rep["missing_faces"], rep["lip_streaks"]) == (0, 0, 0, 0, 0, 0, 0, 0), rep


def test_rim_at_pins_a_crest_exactly_and_the_grass_meets_it():
    ring = wobbly_ring()
    crest = (ring[5][0] - 0.31, 3.2890625, ring[5][1] + 0.97)
    built = I.build_landmass(center=(672.0, -608.0), outline=ring, rim_at={5: crest}, n_patches=0)
    assert built["rim"][5] == (crest[0], crest[2]) and built["rim_y"] == {5: crest[1]}
    gpos, gtris, gmeta = built["world"]["pos"], built["world"]["tris"], built["world"]["meta"]
    fams = {fam for tri, (_b, _i, fam, _uv) in zip(gtris, gmeta) if crest in [tuple(gpos[v]) for v in tri]}
    assert fams == {"rock", "main"}                           # the wall and the grass both weld to the stock crest
    rep = I.verify_landmass(built)
    assert rep["cracks"] == 0 and rep["open_edges"] == 0


def test_v_rows_go_by_corner_role():
    """THE WALL V CORNER-ROLE LAW: a crest pinned at a stock height BELOW the kit's (cluster C's E column stands at
    3.109, not 3.2) still takes the top row, the very float every blob crest gets -- by height it would take 0.894."""
    ring = wobbly_ring()
    crest = (ring[5][0] - 0.31, 3.109375, ring[5][1] + 0.97)
    built = I.build_landmass(center=(672.0, -608.0), outline=ring, rim_at={5: crest}, n_patches=0)
    gpos, gtris, gmeta = built["world"]["pos"], built["world"]["tris"], built["world"]["meta"]
    v_by_y = {}
    for tri, (_b, _i, fam, uvv) in zip(gtris, gmeta):
        if fam == "rock":
            for vid, (_u, v) in zip(tri, uvv):
                v_by_y.setdefault(round(gpos[vid][1], 6), set()).add(v)
    top = I.ROCK_V[0] + (I.ROCK_V[1] - I.ROCK_V[0])
    assert v_by_y[3.109375] == v_by_y[3.2] == {top} and v_by_y[0.0] == {I.ROCK_V[0]}


def test_shore_origin_moves_the_band_by_its_density():
    ring = wobbly_ring()
    a = I.build_landmass(center=(672.0, -608.0), outline=ring, n_patches=0)
    b = I.build_landmass(center=(672.0, -608.0), outline=ring, shore_origin=3.0, n_patches=0)
    strip = I.ROCK_U[1] - I.ROCK_U[0]
    o0 = (ring[0][0], 0.0, ring[0][1])

    def u_at_vertex0(built):
        gpos, gtris, gmeta = built["world"]["pos"], built["world"]["tris"], built["world"]["meta"]
        for tri, (_b, _i, fam, uvv) in zip(gtris, gmeta):
            if fam == "rock" and o0 in [tuple(gpos[v]) for v in tri]:
                return uvv[[tuple(gpos[v]) for v in tri].index(o0)][0]
    du = (u_at_vertex0(b) - u_at_vertex0(a)) % strip
    assert abs(du - 3.0 * I.ROCK_DENSITY) < 1e-12


def test_custom_outline_refuses_what_does_not_apply():
    ring = wobbly_ring()
    with pytest.raises(ValueError, match="lobes and beach do not apply"):
        I.build_landmass(center=(672.0, -608.0), outline=ring, lobes=2)
    with pytest.raises(ValueError, match="lobes and beach do not apply"):
        I.build_landmass(center=(672.0, -608.0), outline=ring, beach={"bearing": (0.0, 40.0)})
    with pytest.raises(ValueError, match="rim_at index 30 is not on the 30-point outline"):
        I.build_landmass(center=(672.0, -608.0), outline=ring, rim_at={30: (0.0, 3.2, 0.0)})
    with pytest.raises(ValueError, match="at least 3 points"):
        I.build_landmass(center=(672.0, -608.0), outline=ring[:2])
