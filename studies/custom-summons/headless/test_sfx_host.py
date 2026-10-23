"""Tests for the headless effect host.

Runs WITHOUT the game install, the plugin or the SCRATCH corpus: the struct layouts, the callback's
byte-exact writes, the VRAM model, the prim decoder and the parent's verdicts are all exercised on
synthetic data. One integration test plays ef227 and skips (saying so) when the staged plugin or the
corpus is absent -- ``hx_gates.py`` is the authoritative check, and it never skips (exit 2 instead).

    py -m pytest studies/custom-summons/headless/test_sfx_host.py -q
"""
from __future__ import annotations

import ctypes as C
import os
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sfx_host as H                            # noqa: E402
import hx_gates as G                            # noqa: E402


def buf(n: int, fill: int = 0xAB):
    b = (C.c_ubyte * n)(*([fill] * n))
    return b, C.addressof(b)


def code(c: int, btl: int = 0) -> int:
    return (c << 24) | btl


# --------------------------------------------------------------------------- the plugin's structs
def test_init_param_is_the_debug_room_recipe():
    p = H.build_init_param()
    assert len(p) == H.INIT_PARAM_BUF
    for i in range(8):
        off = H.INIT_ACTORS_OFF + 32 * i
        assert struct.unpack_from("<H", p, off + 20)[0] == 1 << i
        assert p[off] == (1 if i < 4 else 0)
        assert p[off + 1] == i
    assert H.INIT_ACTORS_OFF + 8 * H.BTL_DATA_INIT_SIZE + 18 + 2 + 12 + 4 <= H.INIT_PARAM_BUF


def test_request_is_set_debug():
    r = H.build_request()
    assert len(r) >= H.REQ_SIZE
    assert struct.unpack_from("<H", r, 0)[0] == 1
    assert struct.unpack_from("<H", r, H.REQ_TRG0_OFF)[0] == 16
    assert r[H.REQ_TRGNO_OFF] == 1


# --------------------------------------------------------------------------- VRAM
def test_vram_round_trip_clips_and_moves():
    v = H.Vram()
    data = bytes(range(16)) * 2                                 # 4x4 halfwords
    v.load(1020, 510, 4, 4, data)                               # clipped to 4x2 at the corner
    got = v.store(1020, 510, 4, 4)
    assert got[:8] == data[:8] and got[8:16] == data[8:16]
    assert got[16:] == b"\0" * 16                               # rows past y=511 read as zero
    v.load(0, 0, 2, 2, b"\x01\x00\x02\x00\x03\x00\x04\x00")
    v.move(0, 0, 2, 2, 10, 10)
    assert v.store(10, 10, 2, 2) == b"\x01\x00\x02\x00\x03\x00\x04\x00"


# --------------------------------------------------------------------------- the callback, rework mode
def test_rework_animation_answers_are_the_dummys_literals():
    h = H.Host()
    assert h.callback(code(9, 1), 0, 0, 0, 0, None) == 1
    assert h.callback(code(10, 1), 0, 0, 0, 0, None) == 1
    assert h.callback(code(13, 1), 7, 0, 0, 0, None) == 7       # Stop Animation echoes its argument
    assert h.callback(code(15, 1), 0, 0, 0, 0, None) == 1


def test_rework_set_calls_are_no_ops():
    h = H.Host()
    b, p = buf(6, 0)
    struct.pack_into("<3h", b, 0, 100, 200, 300)
    assert h.callback(code(2, 1), 0, 0, 0, 0, p) == 0           # Set Position ...
    out, q = buf(6)
    h.callback(code(1, 1), 0, 0, 0, 0, q)                       # ... does not move the unit
    assert struct.unpack("<3h", bytes(out)) == (0, 0, 0)


def test_get_position_writes_exactly_its_width():
    h = H.Host()
    h.actors[1].pos = [5, -6, 7]
    b, p = buf(10)
    h.callback(code(1, 1), 0, 0, 0, 0, p)                       # mode 0: three s16
    assert struct.unpack_from("<3h", b) == (5, -6, 7) and bytes(b)[6:] == b"\xab" * 4
    b, p = buf(10)
    h.callback(code(1, 1), 2, 0, 0, 0, p)                       # mode 2: x and z only
    assert struct.unpack_from("<h", b, 0)[0] == 5 and struct.unpack_from("<h", b, 4)[0] == 7
    assert bytes(b)[2:4] == b"\xab\xab" and bytes(b)[6:] == b"\xab" * 4


def test_get_size_is_three_s32():
    h = H.Host()
    b, p = buf(16)
    h.callback(code(5, 2), 0, 0, 0, 0, p)
    assert struct.unpack_from("<3i", b) == (4096, 4096, 4096) and bytes(b)[12:] == b"\xab" * 4


def test_bone_stance_modes():
    h = H.Host()
    h.actors[16].pos = [10, -20, 30]
    b, p = buf(40)
    h.callback(code(14, 16), 2, 3, 0, 0, p)                     # mode 2: a 32-byte PSXMAT
    r = struct.unpack_from("<9hh3i", b)
    assert r[:9] == (-4096, 0, 0, 0, 4096, 0, 0, 0, 4096) and r[9] == 0 and r[10:] == (10, -20, 30)
    assert bytes(b)[32:] == b"\xab" * 8
    b, p = buf(8)
    assert h.callback(code(14, 16), 1, 0, 0, 0, p) == -20       # mode 1: height is a RETURN value
    assert bytes(b) == b"\xab" * 8
    b, p = buf(8)
    h.callback(code(14, 16), 0, 0, 0, 0, p)                     # mode 0: three s16
    assert struct.unpack_from("<3h", b) == (10, -20, 30) and bytes(b)[6:] == b"\xab\xab"


def test_unknown_unit_falls_back_like_the_engine():
    h = H.Host()
    assert h.callback(code(9, 0x77), 0, 0, 0, 0, None) == 1
    assert h.callback(code(1, 0x77), 0, 0, 0, 0, None) == 0


def test_vram_traffic_through_the_callback():
    h = H.Host()
    src, sp = buf(8, 0)
    C.memmove(sp, b"\x11\x00\x22\x00\x33\x00\x44\x00", 8)
    h.callback(code(100), 64, 32, 2, 2, sp)                     # LOAD_IMAGE
    out, op = buf(8, 0)
    h.callback(code(101), 64, 32, 2, 2, op)                     # STORE_IMAGE
    assert bytes(out) == b"\x11\x00\x22\x00\x33\x00\x44\x00"
    rect, rp = buf(8, 0)
    struct.pack_into("<4h", rect, 0, 64, 32, 2, 2)
    h.callback(code(102), 128, 0, 0, 0, rp)                     # MOVE_IMAGE p=[sx,sy,w,h] -> (a0,a1)
    assert h.vram.store(128, 0, 2, 2) == b"\x11\x00\x22\x00\x33\x00\x44\x00"
    assert [k for _, k, _ in h.vram_ops] == ["load", "store", "move"]


def test_callback_never_raises_into_native_code():
    class Broken(H.Host):
        def _dispatch(self, *a):
            raise ValueError("boom")
    h = Broken()
    assert h.callback(code(1, 1), 0, 0, 0, 0, None) == 0 and "boom" in h.errors[0]


# --------------------------------------------------------------------------- the callback, legacy mode
def test_legacy_is_stateful():
    h = H.Host(mode="legacy", motion_frames=5)
    b, p = buf(6, 0)
    struct.pack_into("<3h", b, 0, 1, 2, 3)
    h.callback(code(2, 1), 0, 0, 0, 0, p)
    out, q = buf(6)
    h.callback(code(1, 1), 0, 0, 0, 0, q)
    assert struct.unpack("<3h", bytes(out)) == (1, 2, 3)
    assert h.callback(code(9, 1), 0, 0, 0, 0, None) == 5
    h.callback(code(13, 1), 9, 0, 0, 0, None)
    assert h.callback(code(13, 1), 0, 0, 0, 0, None) == 9       # returns the PREVIOUS value
    h.tick(); h.tick()
    assert h.callback(code(10, 1), 0, 0, 0, 0, None) == 2
    with pytest.raises(ValueError):
        H.Host(mode="other")


# --------------------------------------------------------------------------- prim decoding
def test_tpage_and_clut_fields():
    assert H.tpage_fields(0x138) == (512, 256, 1, 15)           # "tpage 312": page (512,256), 15bpp
    assert H.tpage_fields(0x0BB) == (704, 256, 1, 8)
    assert H.tpage_fields(0x03A) == (640, 256, 1, 4)
    assert H.clut_fields((247 << 6) | 0) == (0, 247)


def test_sampled_rect_obeys_the_page_span_rule():
    assert H.sampled_rect(0x03A, 0, 255, 0, 127)[:4] == (640, 256, 703, 383)   # 4bpp: 1 column
    assert H.sampled_rect(0x0BA, 0, 255, 0, 127)[:4] == (640, 256, 767, 383)   # 8bpp: 2 columns
    assert H.sampled_rect(0x13A, 0, 255, 0, 0)[:4] == (640, 256, 895, 256)     # 15bpp: 4 columns
    assert H.cells_of((640, 256, 767, 383)) == [(640, 256), (704, 256)]
    assert H.cells_of((700, 380, 704, 390)) == [(640, 256), (640, 384), (704, 256), (704, 384)]


def _ft3(tpage, clut, uvs, xys, semi=False):
    c = H.POLY_FT3 | (2 if semi else 0)
    w = [0x00808080 | (c << 24),
         xys[0], uvs[0] | clut << 16, xys[1], uvs[1] | tpage << 16, xys[2], uvs[2]]
    return c, struct.pack("<7I", *w)


def xy(x, y):
    return (y & 0xFFFF) << 16 | (x & 0xFFFF)


def uv(u, v):
    return v << 8 | u


def test_textured_poly_samples_and_screen_test():
    s = H.PrimStats()
    c, body = _ft3(0x0BB, (247 << 6), [uv(0, 0), uv(127, 0), uv(0, 127)], [xy(10, 10), xy(50, 10), xy(10, 50)])
    s.add(100, c, body, 0)
    c, body = _ft3(0x0BB, (247 << 6), [uv(0, 0), uv(127, 0), uv(0, 127)], [xy(-900, 10), xy(-800, 10), xy(-900, 50)])
    s.add(101, c, body, 0)
    cells = s.sampled_cells()
    assert set(cells) == {"x704_y256@8"}
    assert cells["x704_y256@8"]["prims"] == 2 and cells["x704_y256@8"]["on_screen"] == 1
    assert cells["x704_y256@8"]["frames"] == [100, 101] and cells["x704_y256@8"]["cluts"] == ["0,247"]


def test_sprites_use_the_drawing_mode_state():
    s = H.PrimStats()
    s.add(1, H.DR_TPAGE, struct.pack("<I", 0xE1000000 | 0x03A), 0)
    w = [(H.SPRT_16 << 24) | 0x808080, xy(5, 5), uv(16, 32) | (244 << 6) << 16]
    s.add(2, H.SPRT_16, struct.pack("<3I", *w), 0)
    assert set(s.sampled_cells()) == {"x640_y256@4"}


def test_dr_move_cells_skip_screenshots():
    s = H.PrimStats()
    move = lambda sx, sy, w, h, dx, dy: struct.pack(
        "<5I", 0x01000000 | H.DR_MOVE << 24, sx << 16 | sy, w << 16 | h, dx << 16 | dy, 0)
    s.add(85, H.DR_MOVE, move(704, 256, 64, 128, 704, 384), 0)
    s.add(86, H.DR_MOVE, move(704, 256, 64, 128, 704, 384), 0)
    s.add(87, H.DR_MOVE, move(0, 0, 64, 64, 640, 0), 0)         # a screen-area source = SFXScreenShot
    d = s.dr_move_cells()
    assert set(d) == {"x704_y384"}
    assert d["x704_y384"] == {"blits": 2, "from": ["x704_y256"], "frames": [85, 86]}


def test_stream_hash_is_order_and_content_sensitive():
    a, b = H.PrimStats(), H.PrimStats()
    c, x = _ft3(0x0BB, 0, [uv(0, 0)] * 3, [xy(0, 0)] * 3)
    _, y = _ft3(0x0BB, 0, [uv(1, 0)] * 3, [xy(0, 0)] * 3)
    a.add(1, c, x, 0); a.add(1, c, y, 0)
    b.add(1, c, y, 0); b.add(1, c, x, 0)
    assert a.sha.hexdigest() != b.sha.hexdigest()


# --------------------------------------------------------------------------- run bookkeeping
def test_h_changes_and_creature_window_key_on_frame_index():
    rows = [{"n": i, "frame": i + 1, "H": h, "active": a, "bones": a, "t0": (0, 0, t)}
            for i, (h, a, t) in enumerate([(300, 0, 0), (300, 1, 5), (256, 1, 5), (256, 1, 1 << 25), (415, 0, 0)])]
    assert H.h_changes(rows) == [(3, 256), (5, 415)]
    assert H.creature_window(rows) == (2, 3, 2)                  # the garbage-arena frame is excluded


def test_classify():
    assert H.classify(0, "", False, True) == "ok"
    assert H.classify(None, "", True, False) == "timeout"
    assert H.classify(3, "Assertion failed: 0, file x.cpp, line 786", False, False) == "assert"
    assert H.classify(3221225477, "", False, False) == "crash"
    assert H.classify(1, "Traceback", False, False) == "error"


def test_outputs_never_land_in_the_repository(tmp_path):
    with pytest.raises(SystemExit):
        H._refuse_repo_path(Path(H.__file__).parent / "out.json")
    assert H._refuse_repo_path(tmp_path / "x.json") == (tmp_path / "x.json").resolve()


def test_gate_parsers(tmp_path):
    cap = tmp_path / "ef227.rows.csv"
    m = ",".join(["1"] * 12)
    cap.write_text("PSXCAM,227,57,%s,160,120,300,0\nPSXCAM,227,57,%s,160,120,300,0\n"
                   "PSXCAM,227,58,%s,160,120,256,0\nMODEL,227,58,S\n" % (m, m, m))
    rows = G.capture_rows(cap)
    assert sorted(rows) == [57, 58] and rows[58][1] == 256 and rows[57][0] == (1,) * 12
    assert G.capture_h_changes(rows) == [(58, 256)]
    fcsv = tmp_path / "f.csv"
    fcsv.write_text("n,frame,M,H\n0,1,(1  2  3  4  5  6  7  8  9  10  11  12),300\n")
    assert G.frames_table(fcsv)[1] == {"M": tuple(range(1, 13)), "H": 300}
    assert G.from_58([(25, 320), (58, 256), (553, 300)]) == [(58, 256)]
    assert G.from_58([(58, 256), (577, 490)], upto=None) == [(58, 256), (577, 490)]


# --------------------------------------------------------------------------- integration (install-gated)
_staged = H.staged_bins()
needs_plugin = pytest.mark.skipif(
    not (_staged and (H.CORPUS / "ef227.bytes").is_file()),
    reason="needs the staged plugin (sfx_host.py stage) and the SCRATCH corpus -- hx_gates.py is the "
           "authoritative check and reports this as MISSING rather than skipping")


@needs_plugin
def test_bahamut_matches_the_archived_cast():
    r = H.run_effect(227)
    assert r["outcome"] == "ok"
    assert G.from_58(r["h_changes"]) == G.INGAME_H_FROM_58
    assert r["creature_window"][0] == G.INGAME_CREATURE_FIRST
    assert r["native_frame_index"] == G.INGAME_LAST_FRAME
