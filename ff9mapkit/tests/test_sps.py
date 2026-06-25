"""Tests for the FF9 field ``.sps`` (Special Particle System) codec (sps.codec).

PURE tier: a from-scratch ``build`` emits a known-good 42-byte effect, every model round-trips byte-exact
through serialize -> parse, the texpos/tpage/clut bit helpers self-verify, and the &0x7FFF flag bit + tail
padding are preserved. INSTALL-GATED: the golden ``serialize(parse(real)) == real`` over the Ice-Cavern fire
``.sps`` bins pulled live from the install (the kit ships no SE bytes) PROVES the offset map + width table
against actual Square-Enix bytes. -> [[project-ff9-sps-authoring]].
"""
from __future__ import annotations

import pytest

from ff9mapkit.sps import codec, edit, lint


# A minimal 1-frame, 3-quad effect authored entirely from high-level fields. The exact bytes are the
# canonical layout (header -> frame table -> rgb_offset -> UV table -> 0x0010 separator -> RGB table ->
# frame block). Same page/clut as the real Ice-Cavern field 242 (tpage 0x0018, clut 0x3ED1).
_KNOWN = bytes.fromhex(
    "0100"          # header0: 1 frame
    "1800"          # tpage_raw 0x0018 (TP0/TY1/TX8)
    "d13e"          # clut_raw  0x3ED1 (ClutY251/ClutX17)
    "0909"          # h_raw=9, w_raw=9  -> half-size 16 world / 8 px uv
    "2000"          # frame table: frame0 @ offset 32
    "0300"          # rgb_offset = 3 (== UV-table entry count)
    "006020604060"  # UV table: (0,96) (32,96) (64,96)
    "1000"          # separator
    "ffffff00"      # RGB ramp 0: white  (pad 0)
    "80808000"      # RGB ramp 1: grey
    "40404000"      # RGB ramp 2: dark
    "03"            # frame0 prim_count = 3
    "000000"        # prim (0,0)   texpos 0x00 -> uv0 rgb0
    "14f811"        # prim (20,-8) texpos 0x11 -> uv1 rgb1
    "ec0822"        # prim (-20,8) texpos 0x22 -> uv2 rgb2
)


def _synthetic() -> codec.Sps:
    return codec.build(
        tpage_raw=codec.make_tpage(tp=0, ty=1, tx=8),
        clut_raw=codec.make_clut(cluty=251, clutx=17),
        h_raw=9, w_raw=9,
        uv_table=[(0, 96), (32, 96), (64, 96)],
        rgb_table=[(255, 255, 255, 0), (128, 128, 128, 0), (64, 64, 64, 0)],
        frames=[[codec.prim(0, 0, 0, 0), codec.prim(20, -8, 1, 1), codec.prim(-20, 8, 2, 2)]],
    )


def test_build_matches_known_bytes():
    # the from-scratch builder recomputes every offset -> the exact canonical 42-byte effect
    assert codec.serialize(_synthetic()) == _KNOWN
    assert len(_KNOWN) == 42


def test_make_tpage_clut_pack_the_known_words():
    assert codec.make_tpage(tp=0, ty=1, tx=8) == 0x0018
    assert codec.make_clut(cluty=251, clutx=17) == 0x3ED1


def test_roundtrip_and_decoded_fields():
    s = codec.parse(_KNOWN)
    assert codec.serialize(s) == _KNOWN                      # byte-exact inverse
    assert s.frame_count == 1 and s.flag_bit15 == 0
    assert s.half_w == 16 and s.half_h == 16                 # (9-1)*2
    assert s.tpage == {"TP": 0, "ABR": 0, "TY": 1, "TX": 8}
    assert s.clut == {"ClutY": 251, "ClutX": 17}
    assert s.separator == 0x0010
    assert s.uv_table == [(0, 96), (32, 96), (64, 96)]
    assert s.rgb_table == [(255, 255, 255, 0), (128, 128, 128, 0), (64, 64, 64, 0)]
    prims = s.frames[0]
    assert [(p.pos_x, p.pos_y, p.uv_index, p.rgb_index) for p in prims] == [
        (0, 0, 0, 0), (20, -8, 1, 1), (-20, 8, 2, 2)]


def test_texpos_packs_and_rejects_out_of_range():
    assert codec.pack_texpos(0x3, 0xA) == 0xA3
    p = codec.prim(1, 2, uv_index=5, rgb_index=12)
    assert (p.uv_index, p.rgb_index, p.texpos) == (5, 12, 0xC5)
    with pytest.raises(codec.SpsCodecError):
        codec.pack_texpos(16, 0)
    with pytest.raises(codec.SpsCodecError):
        codec.pack_texpos(0, -1)


def test_flag_bit15_preserved_and_masked_off_frame_count():
    s = _synthetic()
    s.flag_bit15 = 1
    raw = codec.serialize(s)
    assert raw[1] & 0x80                                     # header0 top bit set
    back = codec.parse(raw)
    assert back.flag_bit15 == 1 and back.frame_count == 1    # count still masks &0x7FFF
    assert codec.serialize(back) == raw


def test_tail_padding_preserved():
    # the real field 2273 carries a stray 0x01 tail byte -- a model with a tail must round-trip it
    s = _synthetic()
    s.tail = b"\x01"
    raw = codec.serialize(s)
    assert raw == _KNOWN + b"\x01"
    assert codec.parse(raw).tail == b"\x01"


def test_serialize_rejects_out_of_range_position():
    s = codec.build(
        tpage_raw=0, clut_raw=0, h_raw=2, w_raw=2,
        uv_table=[(0, 0)], rgb_table=[(0, 0, 0, 0)],
        frames=[[codec.Prim(200, 0, 0)]],                   # 200 > i8 max
    )
    with pytest.raises(codec.SpsCodecError):
        codec.serialize(s)


def test_parse_rejects_truncated():
    with pytest.raises(codec.SpsCodecError):
        codec.parse(b"\x01\x00\x00")                         # frame table overruns


# ----------------------------------------------------------------- lint (sps.lint)
def test_lint_clean():
    assert lint.lint_sps(_synthetic()) == []
    assert lint.lint_sps_bytes(_KNOWN) == []


def test_lint_catches_bad_index_and_empty_tables():
    s = _synthetic()
    s.frames[0][0].texpos = codec.pack_texpos(9, 0)          # uv_index 9 but only 3 uv cells
    probs = lint.lint_sps(s)
    assert any("uv_index 9 out of range" in p for p in probs)
    empty = codec.build(tpage_raw=0, clut_raw=0, h_raw=9, w_raw=9, uv_table=[], rgb_table=[], frames=[[]])
    assert any("uv_table is empty" in p for p in lint.lint_sps(empty))


def test_lint_bytes_degrades_on_unparseable():
    msgs = lint.lint_sps_bytes(b"\x01\x00\x00")              # frame table overruns -> a message, no raise
    assert len(msgs) == 1 and msgs[0].startswith("unparseable .sps:")


# ----------------------------------------------------------------- [[sps_edit]] re-skin (sps.edit)
def _raw() -> bytes:
    return codec.serialize(_synthetic())


def test_edit_recolor_ramp_with_old_guard():
    out = edit.apply_sps_edits(_raw(), [{"kind": "recolor_ramp", "sps": 242, "index": 1,
                                         "old": [128, 128, 128], "new": [200, 40, 40]}], sps_id=242)
    assert codec.parse(out).rgb_table[1] == (200, 40, 40, 0)
    # drifted old-guard -> refuse
    with pytest.raises(edit.SpsEditError):
        edit.apply_sps_edits(_raw(), [{"kind": "recolor_ramp", "sps": 242, "index": 1,
                                       "old": [1, 2, 3], "new": [200, 40, 40]}], sps_id=242)


def test_edit_tint_makes_grey_ramp_blue():
    out = edit.apply_sps_edits(_raw(), [{"kind": "tint", "sps": 242, "mul": [0, 0, 512]}], sps_id=242)
    ramp = codec.parse(out).rgb_table                        # (r, g, b, pad) tuples
    assert ramp == [(0, 0, 255, 0), (0, 0, 255, 0), (0, 0, 128, 0)]  # white/grey/dark grey -> blue ramp


def test_edit_scale_and_reposition():
    out = edit.apply_sps_edits(_raw(), [{"kind": "scale", "sps": 242, "old_size": [9, 9], "new_size": [13, 13]}],
                               sps_id=242)
    s = codec.parse(out)
    assert (s.h_raw, s.w_raw, s.half_w) == (13, 13, 24)
    out = edit.apply_sps_edits(_raw(), [{"kind": "reposition", "sps": 242, "dx": 4, "dy": -2}], sps_id=242)
    assert [(p.pos_x, p.pos_y) for p in codec.parse(out).frames[0]] == [(4, -2), (24, -10), (-16, 6)]


def test_edit_reposition_out_of_i8_refused():
    with pytest.raises(edit.SpsEditError):
        edit.apply_sps_edits(_raw(), [{"kind": "reposition", "sps": 242, "dx": 120, "dy": 0}], sps_id=242)


def test_edit_no_match_is_byte_identical():
    raw = _raw()
    assert edit.apply_sps_edits(raw, [{"kind": "tint", "sps": 999, "mul": [0, 0, 256]}], sps_id=242) == raw
    assert edit.apply_sps_edits(raw, [], sps_id=242) == raw


def test_edit_guards_unknown_key_kind_and_container():
    with pytest.raises(edit.SpsEditError):                    # unknown key (typo guard)
        edit.apply_sps_edits(_raw(), [{"kind": "tint", "sps": 242, "mul": [256, 256, 256], "bogus": 1}], sps_id=242)
    with pytest.raises(edit.SpsEditError):                    # unknown kind
        edit.apply_sps_edits(_raw(), [{"kind": "explode", "sps": 242}], sps_id=242)
    with pytest.raises(edit.SpsEditError):                    # [sps_edit] (table) not [[sps_edit]] (array)
        edit.apply_sps_edits(_raw(), {"kind": "tint", "sps": 242, "mul": [1, 1, 1]}, sps_id=242)


def test_validate_sps_edits_never_raises():
    assert edit.validate_sps_edits(_raw(), [{"kind": "scale", "sps": 242, "old_size": [9, 9],
                                             "new_size": [13, 13]}], sps_id=242) == []
    msgs = edit.validate_sps_edits(_raw(), [{"kind": "recolor_ramp", "sps": 242, "index": 99,
                                             "old": [0, 0, 0], "new": [1, 1, 1]}], sps_id=242)
    assert msgs and "out of range" in msgs[0]


def test_build_validate_sps_edits_wiring(tmp_path):
    # exercise build._validate_sps_edits against a stub project (native scene + a staged sps/ sidecar)
    from ff9mapkit import build
    (tmp_path / "sps").mkdir()
    (tmp_path / "sps" / "242.sps.bytes").write_bytes(_raw())

    class _Stub:
        field = {"bgs": "scene.bgs.bytes"}
        def __init__(self, edits): self._e = edits
        def sps_edits(self): return self._e
        def path(self, p): return tmp_path / p

    good, bad = [], []
    build._validate_sps_edits(_Stub([{"kind": "tint", "sps": 242, "mul": [0, 0, 512]}]), good)
    build._validate_sps_edits(_Stub([{"kind": "recolor_ramp", "sps": 242, "index": 9,
                                      "old": [0, 0, 0], "new": [1, 1, 1]}]), bad)
    build._validate_sps_edits(_Stub([{"kind": "tint", "sps": 7, "mul": [1, 1, 1]}]), miss := [])
    assert good == []
    assert bad and "out of range" in bad[0]
    assert miss and "no 7.sps.bytes" in miss[0]


# ----------------------------------------------------------------- install-gated golden round-trip
def _can_read_donor() -> bool:
    try:
        import UnityPy  # noqa: F401
        from ff9mapkit import config
        return (config.find_game_path() / "StreamingAssets" / "p0data2.bin").is_file()
    except Exception:
        return False


@pytest.mark.skipif(not _can_read_donor(), reason="needs the FF9 install + UnityPy (p0data2.bin)")
def test_sps_golden_roundtrip_real_donors(tmp_path):
    # Ice Cavern "ic_jmp" (field 303) loads the fire SPS 2266-2269; write_native_project stages the donor's
    # sps/ sidecar (bins + spt.tcb). THE golden assertion: a full parse -> serialize is byte-identical to
    # each real .sps, proving the offset map + width table against actual Square-Enix bytes.
    from ff9mapkit import extract
    try:
        meta, _toml = extract.write_native_project(
            "fbg_n05_iccv_map088_ic_jmp_0", tmp_path / "m", name="ICJ", verbatim=True)
    except (ValueError, KeyError, FileNotFoundError) as ex:
        pytest.skip(f"donor not readable: {ex}")
    bins = sorted((tmp_path / "m" / "sps").glob("*.sps.bytes"))
    assert bins, "donor staged no .sps bins"
    for path in bins:
        raw = path.read_bytes()
        model = codec.parse(raw)
        assert codec.serialize(model) == raw, f"{path.name} did not round-trip byte-exact"
        # decode sanity: at least one frame, every prim indexes a real UV cell + ramp color
        assert model.frame_count >= 1
        for frame in model.frames:
            for p in frame:
                assert p.uv_index < len(model.uv_table)
                assert p.rgb_index < len(model.rgb_table)


@pytest.mark.skipif(not _can_read_donor(), reason="needs the FF9 install + UnityPy (p0data2.bin)")
def test_catalog_lists_and_loads_real_effects():
    # Tier-0 LIVE catalog: enumerate a field's effects, load one to its model + facts, decode its shared tcb.
    from ff9mapkit.sps import catalog
    rows = catalog.list_field_sps("fbg_n05_iccv_map088_ic_jmp_0")
    if not rows:
        pytest.skip("field has no SPS effects / not readable")
    assert {2266, 2267, 2268, 2269} & {e.sps_id for e in rows}   # the Ice Cavern fire bins
    sps = catalog.load_sps(rows[0])
    facts = dict(catalog.effect_facts(sps))
    assert facts["kind"] == "SPS field effect" and int(facts["frames"]) >= 1
    assert catalog.load_tcb("fbg_n05_iccv_map088_ic_jmp_0") is not None  # the shared texture


@pytest.mark.skipif(not _can_read_donor(), reason="needs the FF9 install + UnityPy (p0data2.bin)")
def test_render_real_effect_to_image():
    # Tier-0 previewer: a real effect renders to a non-empty RGBA image over its decoded spt.tcb.
    pytest.importorskip("PIL")
    from ff9mapkit.sps import catalog, render
    rows = catalog.list_field_sps("fbg_n05_iccv_map088_ic_jmp_0")
    if not rows:
        pytest.skip("field has no SPS effects / not readable")
    tcb = catalog.load_tcb("fbg_n05_iccv_map088_ic_jmp_0")
    sps = catalog.load_sps(rows[0])
    img = render.render_frame(sps, tcb, 0, scale=2)
    assert img.mode == "RGBA" and img.size[0] > 0 and img.size[1] > 0
    assert img.getbbox() is not None                        # something was actually drawn (non-empty)
