"""The custom-outline mint (``island.build_landmass(outline=, rim_at=, shore_origin=)``, world-river rung 1) and
the identity net that keeps every blob mint byte-identical through it.

THE IDENTITY NET: digests of ``build_landmass`` frozen from the code BEFORE the custom outline existed, over every
path the blob mint takes -- one lobe, island E's three, two lobes, rolling relief, desert ground, the big-mint
refinement, the seam wrap into column -1 and (install-gated) a beach mint. Each hashes every block's tris and
POS/NRM/UV/TAN channels as f64, plus the outline and the rim. A miss means a blob mint changed."""
from __future__ import annotations

import hashlib
import math
import warnings

import numpy as np
import pytest

from ff9mapkit import config
from ff9mapkit.world import island as I
from ff9mapkit.world.extract import CH_NRM, CH_POS, CH_TAN, CH_UV

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
def test_blob_mints_are_byte_identical(name):
    kw, sha = BLOB_MINTS[name]
    assert mint_digest(I.build_landmass(**kw)) == sha, f"the {name} blob mint moved"


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
    no crack, no open edge, no hole, nothing wound down, nothing the engine's walk filter drops."""
    ring = wobbly_ring(ccw=ccw)
    built = I.build_landmass(center=(672.0, -608.0), outline=ring, n_patches=0)
    assert built["outline"] == ring
    assert all(I._pip(x, z, ring) for x, z in built["rim"])
    assert all(abs(math.dist(o, r) - 1.0) < 1e-9 for o, r in zip(ring, built["rim"]))   # rim_run 1, exactly
    rep = I.verify_landmass(built)
    assert (rep["cracks"], rep["open_edges"], rep["holes"], rep["down_facing"], rep["walk_filter_fails"],
            rep["grass_over_8u"], rep["missing_faces"]) == (0, 0, 0, 0, 0, 0, 0), rep


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
