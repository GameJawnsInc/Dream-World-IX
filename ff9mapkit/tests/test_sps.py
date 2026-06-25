"""Tests for the FF9 field ``.sps`` (Special Particle System) codec (sps.codec).

PURE tier: a from-scratch ``build`` emits a known-good 42-byte effect, every model round-trips byte-exact
through serialize -> parse, the texpos/tpage/clut bit helpers self-verify, and the &0x7FFF flag bit + tail
padding are preserved. INSTALL-GATED: the golden ``serialize(parse(real)) == real`` over the Ice-Cavern fire
``.sps`` bins pulled live from the install (the kit ships no SE bytes) PROVES the offset map + width table
against actual Square-Enix bytes. -> [[project-ff9-sps-authoring]].
"""
from __future__ import annotations

from pathlib import Path

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


# ----------------------------------------------------------------- Info Hub SPS layer (infohub, pure)
def test_infohub_sps_entries_detail_snippet_pure(tmp_path):
    from ff9mapkit import infohub
    d = tmp_path / "sps"
    d.mkdir()
    (d / "242.sps.bytes").write_bytes(_raw())
    ctx = {"ICEC": d}
    ents = infohub.browse("", kinds=["sps"], sps_context=ctx)
    assert [e.ident for e in ents] == [242] and ents[0].kind == "sps"
    det = infohub.detail(ents[0], sps_context=ctx)
    facts = dict(det.facts)
    assert facts["kind"] == "SPS field effect" and facts["frames"] == "1"
    snip = infohub.snippet(ents[0])
    assert "[[sps_edit]]" in snip and "sps = 242" in snip


def test_infohub_sps_absent_without_context():
    from ff9mapkit import infohub
    assert infohub.browse("", kinds=["sps"]) == []          # no context -> no sps entries
    assert "sps" not in infohub.KINDS                       # stays out of the install-free static cache


def test_sps_spec_form_roundtrips():
    # the Editor "Effects" form spec round-trips an [[sps]] block (build_entity . entity_to_values == identity)
    from ff9mapkit.editor import forms
    full = {"id": 5000, "template": "fire", "pos": [100, -200], "slot": 14, "abr": 1, "framerate": 16}
    assert forms.build_entity(forms.SPS_SPEC, forms.entity_to_values(forms.SPS_SPEC, full)) == full
    minimal = {"id": 5000, "template": "fire", "pos": [0, 0]}    # optionals omitted when blank
    assert forms.build_entity(forms.SPS_SPEC, forms.entity_to_values(forms.SPS_SPEC, minimal)) == minimal


def test_infohub_sps_templates_browse_detail_snippet():
    # the curated templates are a STATIC, install-free Info Hub kind (the listing); detail/snippet too.
    from ff9mapkit import infohub
    from ff9mapkit.sps import templates
    ents = infohub.browse("", kinds=["sps_template"])
    assert {e.name for e in ents} == set(templates.TEMPLATES) and all(e.kind == "sps_template" for e in ents)
    snip = infohub.snippet(ents[0])
    assert "[[sps]]" in snip and f'template = "{ents[0].name}"' in snip
    facts = dict(infohub.detail(next(e for e in ents if e.name == "fire")).facts)
    assert facts["kind"] == "SPS effect template" and "clones" in facts


# ----------------------------------------------------------------- Tier 2: from-scratch creator (sps.author)
def test_author_inline_builds_and_tcb_source():
    from ff9mapkit.sps import author
    blk = {"id": 5001, "texture": {"borrow_tcb": "303", "tpage": {"tp": 0, "tx": 8, "ty": 1},
                                   "clut": {"cluty": 251, "clutx": 20}},
           "size": [9, 9], "uv": [[0, 96], [32, 96]], "rgb": [[255, 200, 80], [255, 120, 0]],
           "frames": [[{"pos": [0, 0], "uv": 0, "rgb": 0}], [{"pos": [2, -1], "uv": 1, "rgb": 1}]]}
    m = author.build_sps_from_block(blk)
    assert m.frame_count == 2 and m.tpage == {"TP": 0, "ABR": 0, "TY": 1, "TX": 8}
    assert m.uv_table == [(0, 96), (32, 96)] and m.rgb_table == [(255, 200, 80, 0), (255, 120, 0, 0)]
    assert author.tcb_source(blk) == ("borrow", "303")
    assert lint.lint_sps(m) == []


def test_author_copy_from_clone_with_geometry_override():
    from ff9mapkit.sps import author
    donor = _synthetic()
    blk = {"id": 5000, "copy_from": {"field": "X", "sps": 1},
           "frames": [[{"pos": [5, 5], "uv": 0, "rgb": 1}]]}
    m = author.build_sps_from_block(blk, donor_loader=lambda field, sid: donor)
    assert m.rgb_table == donor.rgb_table and m.uv_table == donor.uv_table   # texture/colours cloned
    assert [(p.pos_x, p.pos_y, p.uv_index, p.rgb_index) for p in m.frames[0]] == [(5, 5, 0, 1)]  # geometry re-authored
    assert author.tcb_source(blk) == ("borrow", "X")


def test_author_template_resolves_to_donor():
    from ff9mapkit.sps import author, templates
    donor = _synthetic()
    seen = {}
    def loader(field, sid):
        seen["args"] = (field, sid)
        return donor
    blk = {"id": 5000, "template": "fire"}
    m = author.build_sps_from_block(blk, donor_loader=loader)
    t = templates.TEMPLATES["fire"]
    assert seen["args"] == (t.field, t.sps)                  # template -> its donor (field, sps)
    assert m.rgb_table == donor.rgb_table                    # cloned the donor's texture/colours
    assert author.tcb_source(blk) == ("borrow", t.field)     # tcb borrowed from the template's donor


def test_author_template_errors():
    from ff9mapkit.sps import author
    with pytest.raises(author.SpsAuthorError):                # unknown template
        author.build_sps_from_block({"id": 5000, "template": "nope"}, donor_loader=lambda f, s: _synthetic())
    with pytest.raises(author.SpsAuthorError):                # template + copy_from both
        author.build_sps_from_block({"id": 5000, "template": "fire", "copy_from": {"field": "x", "sps": 1}},
                                    donor_loader=lambda f, s: _synthetic())


def test_author_rejects_png_route_b_and_bad_blocks():
    from ff9mapkit.sps import author
    with pytest.raises(author.SpsAuthorError):
        author.build_sps_from_block({"id": 5000, "texture": {"png": "x.png"}})    # Route B needs an engine patch
    msgs = author.validate_sps_block({"id": 5000})                                # no geometry source
    assert msgs and "inline effect needs" in msgs[0]


def test_trigger_spec_pos_slot_and_raw_y():
    from ff9mapkit.sps import author
    assert author.trigger_spec({"id": 5000, "pos": [10, 20, -30], "slot": 8, "abr": 1}) == {
        "slot": 8, "sps_id": 5000, "pos": (10, 20, -30), "abr": 1}
    s2 = author.trigger_spec({"id": 5001, "pos": [10, -30], "y": 20})            # [x,z] + separate y
    assert s2["pos"] == (10, 20, -30) and s2["slot"] == author.DEFAULT_SLOT      # default high slot
    with pytest.raises(author.SpsAuthorError):
        author.trigger_spec({"id": 5002, "slot": 99})                            # slot out of 0..15


def test_sps_trigger_ops_emit_load_pos_abr_framerate():
    from ff9mapkit.content import sps_trigger
    from ff9mapkit.eb import opcodes
    ops = sps_trigger.sps_trigger_ops(slot=14, sps_id=5000, pos=(10, 20, -30), abr=1, framerate=16)
    assert opcodes.encode(0xB3, 14, 130, 5000, 0, 0) in ops     # LOAD
    assert opcodes.encode(0xB3, 14, 135, 10, 20, -30) in ops    # POS -- raw +Y (engine negates it)
    assert opcodes.encode(0xB3, 14, 156, 1, 0, 0) in ops        # ABR additive
    assert opcodes.encode(0xB3, 14, 160, 16, 0, 0) in ops       # FRAMERATE 1x


def test_validate_sps_blocks_wiring(tmp_path):
    from ff9mapkit import build
    inline = {"id": 5000, "texture": {"tpage": 0x18, "clut": 0x3ED1}, "size": [9, 9],
              "uv": [[0, 96]], "rgb": [[255, 255, 255]], "frames": [[{"pos": [0, 0], "uv": 0, "rgb": 0}]]}

    class _Stub:
        field = {}
        def __init__(self, blocks): self._b = blocks
        def sps_blocks(self): return self._b
        def path(self, p): return tmp_path / p

    good = []
    build._validate_sps_blocks(_Stub([inline]), good)
    assert good == []
    dup = []
    build._validate_sps_blocks(_Stub([inline, dict(inline)]), dup)
    assert any("duplicate" in m for m in dup)
    png = []
    build._validate_sps_blocks(_Stub([{"id": 5000, "texture": {"png": "x.png"}}]), png)
    assert any("Route B" in m for m in png)


_SPS_FIELD_TOML = """
[field]
id = 4003
name = "SPSROOM"
area = 11
text_block = 1073

[camera]
pitch = 45

[walkmesh]
quad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]

[player]
spawn = [0, -300]

[[sps]]
id = 5000
texture = { borrow_tcb = "303", tpage = { tp = 0, tx = 8, ty = 1 }, clut = { cluty = 251, clutx = 20 } }
size = [9, 9]
uv = [[0, 96], [32, 96]]
rgb = [[255, 200, 80], [255, 120, 0]]
frames = [ [ {pos = [0, 0], uv = 0, rgb = 0} ], [ {pos = [2, -1], uv = 1, rgb = 1} ] ]
pos = [0, 40, -200]
slot = 14
abr = 1
framerate = 16
"""


def test_autoground_sps_fills_floor_y():
    # pos = [x, z] (no y) -> the kit fills y = +floorY from the walkmesh (the in-game-proven SPS sign);
    # an explicit y / a 3-element pos is respected; off-mesh warns.
    from ff9mapkit import build

    class _WM:
        def height_at(self, x, z):
            return 1909 if (x, z) == (2354, -3372) else None

    class _Proj:
        def __init__(self, blocks): self.raw = {"sps": blocks}

    blocks = [
        {"id": 5000, "pos": [2354, -3372]},               # 2-list, no y -> auto-ground
        {"id": 5001, "pos": [100, 200]},                  # off-mesh -> warn, no y
        {"id": 5002, "pos": [2354, -3372], "y": 50},      # explicit y -> respected
        {"id": 5003, "pos": [2354, 0, -3372]},            # full [x,y,z] -> respected
    ]
    warns = []
    build._autoground_sps(_Proj(blocks), _WM(), warns)
    assert blocks[0]["y"] == 1909                          # +floorY filled
    assert "y" not in blocks[1] and any("off the walkmesh" in w for w in warns)
    assert blocks[2]["y"] == 50                            # explicit respected
    assert "y" not in blocks[3] and blocks[3]["pos"] == [2354, 0, -3372]


def test_build_synth_field_with_authored_sps(tmp_path):
    # End-to-end (no install needed -- inline geometry; the tcb borrow only warns offline): the authored
    # <id>.sps.bytes lands in the FBG folder and the .eb carries the armed RunSPSCode create+place trigger.
    from ff9mapkit.build import FieldProject, build_mod, validate
    from ff9mapkit.config import ModLayout
    from ff9mapkit.eb import EbScript, opcodes
    p = tmp_path / "f.field.toml"
    p.write_text(_SPS_FIELD_TOML, encoding="utf-8")
    assert validate(FieldProject.load(p)) == []             # inline [[sps]] validates with no install
    out = tmp_path / "mod"
    build_mod([FieldProject.load(p)], out, mod_name="FF9CustomMap")
    fm = next(d for d in out.rglob("FieldMaps/*") if d.is_dir() and "SPSROOM" in d.name)
    binp = fm / "5000.sps.bytes"
    assert binp.is_file()
    m = codec.parse(binp.read_bytes())
    assert m.frame_count == 2 and lint.lint_sps(m) == []
    eb = ModLayout(out).eb_path("us", "EVT_SPSROOM.eb.bytes").read_bytes()
    assert opcodes.encode(0xB3, 14, 130, 5000, 0, 0) in eb   # LOAD effect 5000 into slot 14
    assert opcodes.encode(0xB3, 14, 135, 0, 40, -200) in eb  # POS -- raw +Y
    assert EbScript.from_bytes(eb) is not None               # the injected .eb still parses


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


@pytest.mark.skipif(not _can_read_donor(), reason="needs the FF9 install + UnityPy (p0data2.bin)")
def test_infohub_sps_preview_from_real_sidecar(tmp_path):
    # end-to-end: a staged native fork's sps/ sidecar -> Info Hub facts + a rendered preview PNG on disk.
    pytest.importorskip("PIL")
    from ff9mapkit import extract, infohub
    try:
        extract.write_native_project("fbg_n05_iccv_map088_ic_jmp_0", tmp_path / "m", name="ICJ", verbatim=True)
    except (ValueError, KeyError, FileNotFoundError) as ex:
        pytest.skip(f"donor not readable: {ex}")
    d = tmp_path / "m" / "sps"
    if not d.is_dir():
        pytest.skip("donor staged no sps/ sidecar")
    ents = infohub.browse("", kinds=["sps"], sps_context={"ICJ": d})
    assert ents and all(e.kind == "sps" for e in ents)
    det = infohub.detail(ents[0], sps_context={"ICJ": d})
    assert dict(det.facts)["kind"] == "SPS field effect"
    assert det.preview_png and Path(det.preview_png).is_file()   # the preview actually rendered


@pytest.mark.skipif(not _can_read_donor(), reason="needs the FF9 install + UnityPy (p0data2.bin)")
def test_author_copy_from_real_donor():
    # Tier-2 copy_from with the LIVE loader: clone Ice-Cavern fire 2266 -> a valid, lint-clean from-scratch model.
    from ff9mapkit.sps import author
    blk = {"id": 5000, "copy_from": {"field": "fbg_n05_iccv_map088_ic_jmp_0", "sps": 2266}, "pos": [0, 0, 0]}
    m = author.build_sps_from_block(blk)
    assert m.frame_count >= 1 and m.tpage["TP"] == 0
    assert author.tcb_source(blk) == ("borrow", "fbg_n05_iccv_map088_ic_jmp_0")


@pytest.mark.skipif(not _can_read_donor(), reason="needs the FF9 install + UnityPy (p0data2.bin)")
def test_all_templates_build_from_install():
    # every curated template's donor (field token + sps id) must resolve + build a valid effect.
    from ff9mapkit.sps import author, templates
    for name in templates.TEMPLATES:
        m = author.build_sps_from_block({"id": 5000, "template": name})
        assert m.frame_count >= 1 and lint.lint_sps(m) == [], f"template {name!r} did not build clean"
