"""raster.py -- the Memoria managed-renderer port, checked rule by rule on synthetic primitives.

No plugin, no container: every test feeds hand-built prim words through the ported code. The one
install-gated test at the bottom says why it skips.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import raster as R          # noqa: E402
import sfx_host as H        # noqa: E402


# ---------------------------------------------------------------- helpers
def xy(x, y):
    return (x & 0xFFFF) | ((y & 0xFFFF) << 16)


def col(r, g, b, code):
    return r | (g << 8) | (b << 16) | (code << 24)


def uvw(u, v, hi=0):
    return u | (v << 8) | (hi << 16)


def body(*words):
    return struct.pack("<%dI" % len(words), *words)


def tpage(tx=0, ty=0, abr=0, tp=0):
    return tx | (ty << 4) | (abr << 5) | (tp << 7)


def f4(x0, y0, x1, y1, rgb=(255, 255, 255), code=0x28, otz=10):
    """POLY_F4 rectangle (x0,y0)-(x1,y1)."""
    return (code, body(col(*rgb, code), xy(x0, y0), xy(x1, y0), xy(x0, y1), xy(x1, y1)), otz)


def ft4(x0, y0, x1, y1, tp, clut=0, uv=(0, 0, 15, 15), rgb=(128, 128, 128), code=0x2C, otz=10):
    u0, v0, u1, v1 = uv
    return (code, body(col(*rgb, code), xy(x0, y0), uvw(u0, v0, clut), xy(x1, y0), uvw(u1, v0, tp),
                       xy(x0, y1), uvw(u0, v1), xy(x1, y1), uvw(u1, v1)), otz)


def dr_tpage(tp):
    return (0xE1, body((0xE1 << 24) | tp), 0)


DEFAULT_EF = 1        # not in SFX.playParam: default sub order 2, colour x2 (id 0 is C1, x1)


def builder(effnum=DEFAULT_EF):
    return R.FrameBuilder(effnum, R.play_settings(effnum), R.KeyState())


def renderer(vram=None, effnum=DEFAULT_EF, scale=1):
    vram = np.full((512, 1024), 0x00FF, np.uint16) if vram is None else vram
    return R.Renderer(effnum, R.play_settings(effnum), R.TextureCache(vram), scale)


# ---------------------------------------------------------------- SFX.playParam
def test_play_settings_default_and_overrides():
    d = R.play_settings(0x7FFF)                       # an id not in the table
    assert d == {"sub_order": 2, "col_intensity": 2, "col_threshold": 0, "add_order": 0}
    assert R.play_settings(227)["sub_order"] == 0      # Bahamut: S1
    assert R.play_settings(381)["col_intensity"] == 1  # Ark: C2 -> x1.5
    assert R.play_settings(490)["add_order"] == 1      # bit 28 is the ADD order (the code, not the comment)
    assert R.play_settings(86)["col_threshold"] == 1   # bit 29 is the threshold


# ---------------------------------------------------------------- SFXKey
def test_key_bits_and_abr_mapping():
    k = R.KeyState()
    tp = tpage(tx=11, ty=1, abr=2, tp=1)
    key = k.abr_tex(0x2E, clut=0x3DC0, tpage=tp)       # semi-transparent FT4, abr 2 -> SUB
    assert key & R.ABR_SUB and not key & R.ABR_ADD
    assert (key >> 16) & 0xF == 11 and (key >> 20) & 1 == 1 and R.texture_mode(key) == 1
    assert key & 0x7FFF == 0x3DC0 & 0x7FFF
    for abr in (0, 1, 3):
        assert k.abr_tex(0x2E, 0, tpage(abr=abr)) & R.ABR_ADD
    assert not k.abr_tex(0x2C, 0, tpage(abr=1)) & (R.ABR_ADD | R.ABR_SUB)   # opaque: no blend bits


def test_15bpp_key_still_carries_the_clut():
    """SFXKey's ``num >> 5 == 2`` can never hold (the page bits sit at 16+): 15bpp keys keep the clut."""
    k = R.KeyState()
    key = k.abr_tex(0x2C, clut=0x1234, tpage=tpage(tx=8, ty=1, tp=2))
    assert R.texture_mode(key) == 2 and key & 0x7FFF == 0x1234 & 0x7FFF


# ---------------------------------------------------------------- textures
def test_rgba_alpha_rule():
    px = np.array([0x0000, 0x8000, 0x0001, 0x7FFF], np.uint16)
    rgba = R._rgba_of(px)
    assert list(rgba[:, 3]) == [0, 255, 255, 255]      # transparent ONLY for 0x0000
    assert list(rgba[3, :3]) == [248, 248, 248]


def test_decode_4_8_15bpp():
    vram = np.zeros((512, 1024), np.uint16)
    vram[480, 0:16] = [0x8000 | i for i in range(16)]  # a 16-entry clut at (0,480)
    vram[0, 64] = 0x3210                               # 4bpp: texels 0,1,2,3
    vram[256, 128] = 0x0201                            # 8bpp: texels 1,2
    vram[256, 448] = 0x7C00                            # 15bpp: pure blue
    cache = R.TextureCache(vram)
    t4 = cache.decode(0, 0, 1, 480, 0)
    assert [int(t4[0, i, 0]) for i in range(4)] == [0, 8, 16, 24]
    t8 = cache.decode(1, 1, 2, 480, 0)
    assert [int(t8[0, i, 0]) for i in range(2)] == [8, 16]
    t15 = cache.decode(2, 1, 7, 0, 0)
    assert list(t15[0, 0]) == [0, 0, 248, 255]


def test_cache_clears_only_its_own_page():
    vram = np.zeros((512, 1024), np.uint16)
    cache = R.TextureCache(vram)
    key = (1 << 21) | (11 << 16) | (1 << 20) | R.HAS_TEXTURE        # 8bpp at (704,256)
    cache.get(key)
    cache.clear_key(768, 256)                          # second column of the same 8bpp texture
    assert key in cache.entries                        # Memoria keeps the stale decode
    cache.clear_key(704 + 10, 256 + 5)
    assert key not in cache.entries


def test_cache_refuses_past_fifty():
    cache = R.TextureCache(np.zeros((512, 1024), np.uint16))
    for i in range(R.SST_MAX_TEXTURE):
        assert cache.get(R.HAS_TEXTURE | i) is not None
    assert cache.get(R.HAS_TEXTURE | 99) is None and cache.full == 1


# ---------------------------------------------------------------- batching
def test_one_mesh_per_key_and_quad_split():
    b = builder()
    cmds, faults = b.build([f4(0, 0, 10, 10), f4(20, 0, 30, 10)])
    assert not faults
    meshes = [c.mesh for c in cmds if c.kind == "mesh"]
    assert len(meshes) == 1 and meshes[0].prims == 2
    assert meshes[0].tris[:2] == [(0, 1, 2), (2, 1, 3)]


def test_push_order_follows_sub_order():
    prims = [dr_tpage(tpage(abr=2)), f4(0, 0, 1, 1, code=0x2A), f4(0, 0, 1, 1, code=0x28)]
    order = lambda eff: [c.mesh.blend for c in builder(eff).build(prims)[0] if c.kind == "mesh"]
    assert order(227) == [2, 0]                        # subOrder 0: Sub, then Opa
    assert order(DEFAULT_EF) == [0, 2]                 # default subOrder 2: Opa, then Sub


def test_dr_move_splits_the_batch():
    mv = (0xE7, body(0xE7000000, (704 << 16) | 384, (64 << 16) | 128, (704 << 16) | 256), 0)
    cmds, _ = builder().build([f4(0, 0, 1, 1), mv, f4(5, 5, 6, 6)])
    assert [c.kind for c in cmds] == ["mesh", "move", "mesh"]
    assert cmds[1].args == (704, 384, 64, 128, 704, 256)


def test_semi_transparency_alpha_and_shader():
    cmds, _ = builder().build([dr_tpage(tpage(abr=0)), f4(0, 0, 1, 1, code=0x2A)])
    m = cmds[0].mesh
    assert m.alpha == 63 and m.shader == 3 + 1          # untextured ADD at AbrAlphaData[0]


def test_mesh_pool_runs_dry():
    prims = [ft4(0, 0, 1, 1, tp=tpage(tx=6), clut=i) for i in range(R.MESH_MAX + 1)]
    cmds, faults = builder().build(prims)
    assert faults and "pool" in faults[0] and cmds == []          # the C# throws before any push


def test_80x110_tile_right_edge_grows():
    tile = (0x60, body(col(255, 255, 255, 0x60), xy(240, 0), (110 << 16) | 80), 5)
    m = builder().build([tile])[0][0].mesh
    assert m.pos[1][0] - m.pos[0][0] == 81


# ---------------------------------------------------------------- rasterisation
def _draw(prims, effnum=DEFAULT_EF, vram=None):
    r = renderer(vram, effnum)
    cmds, faults = builder(effnum).build(prims)
    assert not faults
    return r.render(cmds, 1, True), r


def test_top_left_rule_no_double_coverage_under_add():
    screen, _ = _draw([dr_tpage(tpage(abr=1)), f4(10, 10, 50, 50, rgb=(100, 100, 100), code=0x2A)])
    vals = np.unique(np.round(screen.color[10:50, 10:50, 0] * 255))
    assert len(vals) == 1                              # the shared diagonal is lit exactly once
    assert screen.color[9, 9, 0] == 0 and screen.color[50, 50, 0] == 0


def test_colour_strength_c1_halves_a_modulated_texel():
    assert R.COLOR_DATA[R.play_settings(0)["col_intensity"]] == 1.0     # id 0 is C1


def test_vertex_colour_saturates():
    screen, _ = _draw([f4(0, 0, 4, 4, rgb=(255, 64, 0))])
    r, g, b = screen.color[1, 1]
    assert r == 1.0                                    # 255 * _Color 2 * a(128/255) clamps to 1
    assert abs(g - round(64 / 255 * 2 * 128 / 255 * 255) / 255) < 1e-6 and b == 0


def test_depth_nearer_otz_wins():
    far = f4(0, 0, 8, 8, rgb=(255, 0, 0), otz=100)
    near = f4(0, 0, 8, 8, rgb=(0, 255, 0), otz=10)
    s1, _ = _draw([near, far])                          # same mesh key: near drawn first, far rejected
    assert s1.color[2, 2, 1] > 0 and s1.color[2, 2, 0] == 0


def test_transparent_texel_is_discarded_on_opaque():
    vram = np.zeros((512, 1024), np.uint16)
    vram[0:16, 384:400] = 0x7FFF                        # a white 15bpp patch...
    vram[0:16, 384:392] = 0x0000                        # ...left half transparent
    screen, _ = _draw([ft4(0, 0, 16, 16, tp=tpage(tx=6, tp=2), uv=(0, 0, 16, 16))], vram=vram)
    assert screen.color[8, 2].max() == 0 and screen.color[8, 12].min() > 0.9


def test_15bpp_routing_blur_vs_generated():
    r = renderer()
    k = R.KeyState()
    blur = R.Mesh(k.abr_tex(0x2C, 0, tpage(tx=3, tp=2)), 0x2C, 0, 0, 0, 0)
    high = R.Mesh(k.abr_tex(0x2C, 0, tpage(tx=8, ty=1, tp=2)), 0x2C, 0, 0, 0, 0)
    assert r.texture_for(blur).kind == R.KIND_BLUR      # x < 384: the previous frame's screen
    assert r.texture_for(high).kind == R.KIND_IMAGE     # VRAM, until the cast renders into DR_AREA
    r.gen_created = True
    assert r.texture_for(high).kind == R.KIND_GENERATED


# ---------------------------------------------------------------- the probe-log reader
def test_read_probe_log_casts_and_dedupe(tmp_path):
    log = tmp_path / "p.log"
    log.write_text("\n".join([
        "# header",
        "STATE,227,11,0,225,DR_TPAGE",                  # the short (pre-tpage-column) STATE row
        "PRIM,227,11,1,98,TILE,0.0000,275,110",
        "MESH,227,11,0,00800000,14000,16,1,2,3,4,5,6",
        "MESH,227,11,0,00800000,14000,16,1,2,3,4,5,6",  # one per game frame -> de-duplicated
        "PRIM,227,12,0,98,TILE,-5.0000,0,0",
        "PRIM,227,3,0,98,TILE,0.0000,0,0",              # frame went back: a new cast
        "PRIM,74,3,0,98,TILE,0.0000,0,0",               # another effect: ignored
    ]) + "\n", encoding="utf-8")
    casts = R.read_probe_log(log, 227)
    assert len(casts) == 2
    f11 = casts[0][11]
    assert f11["states"][0][:2] == (0, 225) and len(f11["meshes"]) == 1
    assert casts[0][12]["prims"][0][2] == 5.0          # GzDepth = -otz, read back as otz


def test_frame_spec_strides():
    assert R.parse_frames("1-9:4,20") == {1, 5, 9, 20}


# ---------------------------------------------------------------- install-gated
def _stock_227():
    blob = H.CORPUS / "ef227.bytes"
    bins = H.staged_bins()
    return (blob, bins[0][0]) if blob.is_file() and bins else (None, None)


@pytest.mark.skipif(_stock_227()[0] is None, reason="needs the SCRATCH corpus ef227.bytes and a staged plugin "
                    "(py -I sfx_host.py stage) -- both are the user's own install, never in the repo")
def test_bahamut_frame_renders_in_a_child():
    import subprocess
    code = ("import sys; sys.path.insert(0, %r); import raster as R, sfx_host as H; from pathlib import Path\n"
            "blob = Path(%r).read_bytes(); got = {}\n"
            "R.run(Path(%r), blob, 227, frames={150}, max_frames=151,"
            " on_frame=lambda f, s, c, st: got.update({f: s}) if s is not None else None)\n"
            "s = got[150]; print('LIT', int((s.color.max(axis=-1) > 0.05).sum()))"
            % (str(Path(R.__file__).parent), str(_stock_227()[0]), str(_stock_227()[1])))
    out = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, timeout=300).stdout
    lit = int(out.split("LIT")[1])
    assert lit > 0.1 * R.SCREEN_W * R.SCREEN_H        # creature + wings: about a sixth of the screen is lit


# ---------------------------------------------------------------- rx_gates scoring (pure)
def test_rx1_rx2_scoring_counts_only_input_matched_frames():
    import rx_gates as G
    rep = {"casts": [{"cast": 0, "frames": 3, "rx1": {"match": 2, "differ": 1},
                      "rx2": {"match": 2, "unscored_differ": 1},
                      "xy_delta": {"[35, 0]": 90, "[36, -1]": 8, "[0, 0]": 2}}]}
    (r1, m1), (r2, m2), lines = G.rx1_rx2([((227, Path("x.log")), rep)])
    assert r1 and "90.0%" in m1 and r2 and m2.startswith("2/2")
    rep["casts"][0]["rx2"]["differ"] = 1
    assert not G.rx1_rx2([((227, Path("x.log")), rep)])[1][0]       # one wrong command buffer fails RX2


def test_rx4_battery_is_well_formed():
    import rx_gates as G
    assert {v for *_, v in G.BATTERY} == {"DRAWN", "NOT_DRAWN"}
    assert len({n for n, *_ in G.BATTERY}) == len(G.BATTERY)
