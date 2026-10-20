"""world.render -- the offline overworld renderer, promoted from the Path D render gate.

Hermetic: synthetic geometry + injected textures only, no game install and no extracted
templates, so these actually RUN in a fresh worktree rather than skipping (the worktree
skip trap). The engine-faithful raster laws each get a test that FAILS when the law is
removed: determinism (the P-E gate), the GAME-EYE backface cull, alpha-0 -> white
(blank-tile law), NEAREST sampling, and the auto rig's two committed vantage classes.
"""
from __future__ import annotations

import math

import pytest

np = pytest.importorskip("numpy")

from ff9mapkit.world import render as R


# a tiny site: textures injected, geometry synthetic, nothing touches disk
SITE = R.RenderSite(cells=((0, 0),), game="X:/nonexistent", water_texdir="X:/nonexistent",
                    res=(64, 48))

# one CCW-on-screen triangle spanning most of the ortho box, at y=0
TOP = dict(kind="ortho", x0=0.0, x1=8.0, z0=-8.0, z1=0.0)


def _tri_batch(part="Terrain", flip=False, uvs=None):
    verts = np.array([[1.0, 0.0, -1.0], [7.0, 0.0, -1.0], [4.0, 0.0, -7.0]])
    tris = np.array([[0, 2, 1] if flip else [0, 1, 2]])
    uv = np.array(uvs if uvs is not None else [[0.1, 0.1], [0.9, 0.1], [0.5, 0.9]])
    return [(part, verts, uv, tris)]


def _solid_tex(rgb, alpha=255, size=4):
    t = np.zeros((size, size, 4), dtype=np.uint8)
    t[:, :, :3] = rgb
    t[:, :, 3] = alpha
    return t


def _raster(batches, tex, view=TOP, **kw):
    return R.raster(view, batches, "t", site=SITE, out_dir=None,
                    tex_lookup=lambda part: tex, verbose=False, **kw)


# ------------------------------------------------------------------ determinism
def test_determinism_identical_inputs_zero_px():
    """The P-E gate: two rasters of the same inputs differ by zero pixels."""
    tex = _solid_tex((10, 200, 30))
    a = _raster(_tri_batch(), tex)
    b = _raster(_tri_batch(), tex)
    assert (a == b).all()


def test_diff_reports_and_never_raises():
    tex = _solid_tex((10, 200, 30))
    a = _raster(_tri_batch(), tex)
    n, box = R.diff(a, a, "same", out_dir=None, thresh=0, verbose=False)
    assert n == 0 and box is None
    b = a.copy()
    b[5, 5] = (255, 0, 0)
    n, box = R.diff(a, b, "one", out_dir=None, thresh=0, verbose=False)
    assert n == 1 and box == (5, 5, 5, 5)


# ------------------------------------------------------------------ cull law
def test_backface_cull_flipped_winding_renders_sky():
    """THE GAME-EYE PASS: the ortho eye sits at +inf y, so a triangle wound the
    wrong way is culled -- the pixels stay SKY. Removing the cull breaks this."""
    tex = _solid_tex((10, 200, 30))
    up = _raster(_tri_batch(), tex)
    down = _raster(_tri_batch(flip=True), tex)
    center = (24, 32)                                        # inside the triangle
    assert tuple(up[center]) == (10, 200, 30)
    assert tuple(down[center]) == R.SKY
    nocull = _raster(_tri_batch(flip=True), tex, cull=False)
    assert tuple(nocull[center]) == (10, 200, 30)


# ------------------------------------------------------------------ texture laws
def test_alpha0_samples_white():
    """The blank-tile law: alpha-0 texels render WHITE in-game, and the raster
    must reproduce that -- not the texel's RGB, not transparency."""
    tex = _solid_tex((10, 200, 30), alpha=0)
    img = _raster(_tri_batch(), tex)
    assert tuple(img[24, 32]) == R.BLANK_WHITE


def test_missing_texture_renders_magenta():
    img = _raster(_tri_batch(), None)
    assert tuple(img[24, 32]) == (200, 60, 200)


def test_nearest_sampling_no_interpolation():
    """Vanilla samples NEAREST: a 2x2 quadrant texture must produce only the
    four exact texel colors, never a blend."""
    tex = np.zeros((2, 2, 4), dtype=np.uint8)
    tex[:, :, 3] = 255
    tex[0, 0, :3] = (255, 0, 0)
    tex[0, 1, :3] = (0, 255, 0)
    tex[1, 0, :3] = (0, 0, 255)
    tex[1, 1, :3] = (255, 255, 0)
    img = _raster(_tri_batch(uvs=[[0.0, 0.0], [1.0, 0.0], [0.5, 1.0]]), tex)
    allowed = {(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), R.SKY}
    seen = {tuple(px) for row in img for px in row}
    assert seen <= allowed and len(seen) >= 3


def test_sample_wraps_uv():
    tex = _solid_tex((7, 8, 9))
    rgb = R.sample(tex, np.array([1.25, -0.25]), np.array([0.5, 0.5]))
    assert (rgb == (7, 8, 9)).all()


# ------------------------------------------------------------------ owner buffer
def test_want_ids_owner_buffer():
    """The seam-forensics hook: rendered pixels carry batch*2^20+tri, sky is -1."""
    tex = _solid_tex((10, 200, 30))
    img, ids = _raster(_tri_batch(), tex, want_ids=True)
    assert ids[24, 32] == 0                                  # batch 0, tri 0
    assert ids[0, 0] == -1                                   # sky corner


# ------------------------------------------------------------------ projection
def test_ortho_maps_bbox_to_screen():
    verts = np.array([[0.0, 0.0, -8.0], [8.0, 2.0, 0.0]])
    sx, sy, dep = R.project(TOP, verts, SITE.res)
    assert sx[0] == 0.0 and sy[0] == 0.0                     # (x0, z0) -> top-left
    assert sx[1] == SITE.res[0] - 1 and sy[1] == SITE.res[1] - 1
    assert dep[1] == -2.0                                    # ortho depth = -y


# ------------------------------------------------------------------ the auto rig
def test_views_around_reproduces_the_two_vantage_classes():
    """The rig must produce the two committed close-range classes BY
    CONSTRUCTION (RENDER-GATE.md: the mid-range four missed both playtest-8
    residuals): near-top-down ~60 deg pitch at ~11.5u, and a low graze with
    the eye ~2u above the waterline at ~19u -- each from all four azimuth
    quadrants, all aimed at the target."""
    wx, wz, gy = 380.0, -513.0, 1.4
    views = R.views_around(wx, wz, ground_y=gy)
    closes = {n: v for n, v in views.items() if n.startswith("close_")}
    grazes = {n: v for n, v in views.items() if n.startswith("graze_")}
    assert len(closes) == 4 and len(grazes) == 4 and "top" in views

    def offsets(vs):
        return [(v["eye"][0] - wx, v["eye"][1], v["eye"][2] - wz, v) for v in vs.values()]

    for dx, ey, dz, v in offsets(closes):
        horiz = math.hypot(dx, dz)
        pitch = math.degrees(math.atan2(ey - v["at"][1], horiz))
        assert horiz == pytest.approx(11.5, abs=0.1)
        assert 55.0 <= pitch <= 65.0                         # the ~60-deg class
        assert v["at"] == (wx, gy + 0.5, wz)
    for dx, ey, dz, v in offsets(grazes):
        horiz = math.hypot(dx, dz)
        pitch = math.degrees(math.atan2(ey - v["at"][1], horiz))
        assert horiz == pytest.approx(19.0, abs=0.1)
        assert pitch <= 10.0                                 # near edge-on
        assert ey == pytest.approx(gy + 3.0, abs=0.01)       # eye ~2u over waterline
    # the four azimuths cover all quadrant sign pairs, for both classes
    for group in (closes, grazes):
        quads = {(dx > 0, dz > 0) for dx, _, dz, _ in offsets(group)}
        assert len(quads) == 4


def test_ground_y_near_median_and_fallback():
    batches = _tri_batch()
    batches[0][1][:, 1] = (2.0, 4.0, 6.0)
    assert R.ground_y_near(batches, 4.0, -3.0, radius=10.0) == 4.0
    assert R.ground_y_near(batches, 500.0, -500.0, radius=1.0, fallback=9.9) == 9.9
    assert R.ground_y_near([("Sea4", batches[0][1], None, None)], 4.0, -3.0) == 0.0


def test_cells_around_covers_the_target_block():
    cells = R.cells_around(380.0, -513.0, radius=96.0)
    assert (5, 8) in cells                                   # the V-shore corner block
    assert all(0 <= bx <= 23 and 0 <= by <= 19 for bx, by in cells)
    tight = R.cells_around(32.0, -32.0, radius=1.0)
    assert tight == ((0, 0),)


# ------------------------------------------------------------------ the effective prefab + stock mode
# What the engine BINDS at a cell (WMWorld.cs:525-573): its own prefab, or an IsSea cell's Donor.txt divert, or the
# SeaBlockPrefab. A carried river that is not an override free-rides from the donor prefab, so an eye that drew only
# the deployed files could not see it (watercarry/RECON.md section 5, R0).

def _blockmesh(x, y, part, height):
    from ff9mapkit.world.extract import BlockMesh, CH_POS, CH_NRM, CH_UV, CH_TAN
    pos = [[1.0, height, -1.0], [7.0, height, -1.0], [4.0, height, -7.0]]
    return BlockMesh(name=f"Block[{x}][{y}] {part}", disc=1, x=x, y=y, lod="0_1", vcount=3, stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: [[0.0, 1.0, 0.0]] * 3, CH_UV: [[0.1, 0.1]] * 3,
                                  CH_TAN: [[0.0, 0.0, 0.0, 1.0]] * 3},
                     flat_index=[0, 1, 2], tris=[[0, 1, 2]], raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


@pytest.fixture
def stock_world(monkeypatch, tmp_path):
    """Three stock prefabs -- a stream block (5,5), the land donor (12,10), the sea prefab (12,0) -- each stock part
    a triangle at height = 10*x + y, so a batch names the block it came from; overrides go under tmp/MOD."""
    from ff9mapkit.world import extract as X
    prefabs = {(5, 5): {"terrain", "stream"}, (12, 10): {"terrain"}, (12, 0): {"sea4", "sea4f"}}
    monkeypatch.setattr(X, "block_parts", lambda disc=1, lod="0_1", game=None:
                        {k: frozenset(v) for k, v in prefabs.items()})

    def read_block(x, y, *, disc=1, lod="0_1", part="terrain", game=None):
        if part not in prefabs.get((x, y), ()):
            raise ValueError(f"block[{x}][{y}] {part} not found")
        return _blockmesh(x, y, part, 10.0 * x + y)
    monkeypatch.setattr(X, "read_block", read_block)

    def deploy(bx, by, part, height=99.0, donor=None):
        from ff9mapkit.world import mesh as M
        d = tmp_path / "MOD" / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / f"r{by}"
        d.mkdir(parents=True, exist_ok=True)
        M.write_ff9mesh(_blockmesh(bx, by, part, height), d / f"Block[{bx}][{by}] {part}.ff9mesh")
        if donor is not None:
            (d / f"Block[{bx}][{by}] Donor.txt").write_text(donor, encoding="utf-8")
    return tmp_path, deploy


def _site(game, cells, disc=1):
    return R.RenderSite(cells=cells, disc=disc, mod_folder="MOD", game=game, water_texdir=game / "tex")


def test_effective_prefab_follows_the_engine(stock_world):
    game, deploy = stock_world
    s = _site(game, ())
    assert R.effective_prefab(s, 5, 5) == ((5, 5), "own prefab")
    assert R.effective_prefab(s, 7, 7)[0] is None                       # open sea: the SeaBlockPrefab
    deploy(7, 7, "Terrain", donor="5,5")
    assert R.effective_prefab(s, 7, 7)[0] == (5, 5)                     # the divert
    deploy(8, 8, "Terrain", donor="9,9")                                # a donor with no prefab
    assert R.effective_prefab(s, 8, 8)[0] == (12, 10)
    deploy(9, 9, "Terrain")                                             # no Donor.txt at all
    assert R.effective_prefab(s, 9, 9)[0] == (12, 10)
    deploy(5, 5, "Terrain", donor="12,10")                              # a stock block's Donor.txt is dead
    assert R.effective_prefab(s, 5, 5) == ((5, 5), "own prefab")
    s9 = _site(game, (), disc=9)                                        # Path D: every cell is IsSea
    assert R.effective_prefab(s9, 5, 5)[0] is None                      # even where disc 1 has a prefab


def test_stock_mode_draws_the_donors_free_riding_stream_at_the_target(stock_world):
    game, deploy = stock_world
    deploy(7, 7, "Terrain", height=3.2, donor="5,5")                    # a carried cell: Terrain override only
    site = _site(game, ((7, 7), (8, 8)))
    plain = R.load_batches(site)
    assert [b[0] for b in plain] == ["Terrain"]                         # the deployed files only, as before
    got = {b[0]: b[1] for b in R.load_batches(site, stock=True)}
    assert sorted(got) == ["Sea4", "Stream", "Terrain"]
    ox, oz = 7 * 64.0, -7 * 64.0
    assert np.allclose(got["Terrain"][:, 1], 3.2)                       # the override (float32) wins over the prefab
    assert got["Stream"][:, 1].tolist() == [55.0] * 3                   # the DONOR (5,5)'s stream ...
    assert got["Stream"][0].tolist() == [ox + 1.0, 55.0, oz - 1.0]      # ... at the TARGET cell's origin
    assert got["Sea4"][:, 1].tolist() == [120.0] * 3                    # (8,8) open sea: (12,0)'s sea4f


def test_water_parts_take_their_engine_textures(tmp_path):
    from PIL import Image
    tex = tmp_path / "worldmap" / "textures"
    (tmp_path / "worldmap" / "materials").mkdir(parents=True)
    tex.mkdir(parents=True)
    Image.new("RGBA", (4, 4), (10, 20, 30, 255)).save(tex / "11_128_0_0.png")                 # River, frame 0
    Image.new("RGBA", (4, 4), (40, 50, 60, 255)).save(tmp_path / "worldmap" / "materials" / "11_64_192.png")
    site = R.RenderSite(cells=(), game=tmp_path, water_texdir=tex)
    cache: dict = {}
    assert R.tex_for("River", site, cache)[0, 0].tolist() == [10, 20, 30, 255]
    assert R.tex_for("Stream", site, cache)[0, 0].tolist() == [40, 50, 60, 255]
    assert R.tex_for("Falls", site, cache) is None                      # absent -> magenta in the raster
    assert {"Stream", "River", "RiverJoint", "Falls"} <= set(R.PARTS)
