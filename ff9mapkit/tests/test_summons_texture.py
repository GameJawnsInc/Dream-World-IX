"""``summons.texture`` -- the id-4 texture-page / CLUT decode + the textured ``build.adapt_model`` path.

Two lanes (the suite's game-gated pattern, cf. test_summons_build.py / test_summons_export.py):
  * OFFLINE (always runs) -- the CLUT/page/UV math on hand-built synthetic data: the BGR555 + STP colour
    rule, the TPAGE/CLUT word arithmetic, the V-offset bake law, every :func:`texture_check` refusal, a
    synthetic 2-page package decoded end to end, and the per-face-per-part mesh build (material grouping,
    UV-value welding, seam splitting, the unbound-part fallback). No install, no stock bytes.
  * GAME-GATED -- the real Bahamut (``ef227``): the 6 pages / 6 CLUT rows resolve to the offsets the
    study's disassembly predicts, every textured face's UV lands inside its page, and a CALIBRATED
    falsification (correct UVs sample ZERO transparent texels where a v-flip / u-flip / u<->v swap /
    page misbinding each sample dozens) -- so a future drift in the decode fails LOUD instead of
    shipping a wrong-coloured dragon. Skips cleanly when the local ``C:/gd/SCRATCH/summon-format/`` blob is absent.
"""
from __future__ import annotations

import os
import struct

import pytest

from ff9mapkit.summons import build as B
from ff9mapkit.summons import container as C
from ff9mapkit.summons import export as X
from ff9mapkit.summons import texture as T

_SCRATCH = r"C:/gd/SCRATCH/summon-format"


def _ef(effid: int) -> str:
    return os.path.join(_SCRATCH, f"ef{effid:03d}.bytes")


def _have(effid: int) -> bool:
    return os.path.exists(_ef(effid))


def _blob227() -> bytes:
    with open(_ef(227), "rb") as fh:
        return fh.read()


# =========================================================== OFFLINE: the colour + word arithmetic
def test_bgr555_zero_is_the_transparent_texel():
    # PSX transparency is by VALUE: 0x0000 (black, STP clear) is the transparent entry. Stock uses exactly
    # that (entry 0 of every ef227 CLUT row).
    assert T.bgr555_rgba(0x0000) == (0, 0, 0, 0)


def test_bgr555_channel_order_is_r_low_b_high():
    assert T.bgr555_rgba(0x001F) == (255, 0, 0, 255)          # bits 0-4  = R
    assert T.bgr555_rgba(0x03E0) == (0, 255, 0, 255)          # bits 5-9  = G
    assert T.bgr555_rgba(0x7C00) == (0, 0, 255, 255)          # bits 10-14 = B
    assert T.bgr555_rgba(0x7FFF) == (255, 255, 255, 255)


def test_bgr555_stp_bit_does_not_make_a_texel_transparent():
    # bit15 selects the BLEND EQUATION for a primitive that is itself flagged semi-transparent; it is not
    # an alpha. Every non-zero entry in all six ef227 rows carries it, and those texels are opaque.
    assert T.bgr555_rgba(0x8000 | 0x001F) == (255, 0, 0, 255)
    assert T.bgr555_rgba(0x8000) == (0, 0, 0, 255)            # STP black: opaque black, NOT transparent


def test_tpage_mode_and_origin():
    assert T.tpage_mode(0x93) == T.MODE_8BPP                  # ef227's own value
    assert T.tpage_mode(0x13) == T.MODE_4BPP
    assert T.tpage_mode(0x113) == T.MODE_16BPP
    assert T.tpage_origin(0x93, 128) == (192, 384)            # (tpage&0xf)*64 , ((tpage&0x10)<<4)+vOff
    assert T.tpage_origin(0x93, 0) == (192, 256)
    assert T.tpage_origin(0x03, 0) == (192, 0)                # bit4 clear -> the upper VRAM half


def test_clut_word_arithmetic():
    assert (T.clut_row(0x3990), T.clut_entry0(0x3990)) == (0, 0)     # ef227 part0: strip row 0, entry 0
    assert (T.clut_row(0x3AD0), T.clut_entry0(0x3AD0)) == (5, 0)     # ef227 part5: strip row 5
    assert T.clut_row(0x3990 + 0x40) == 1                            # +0x40 == +1 VRAM line
    assert T.clut_entry0(0x3990 + 0x01) == 16                        # +1 in x == +16 entries


def test_the_v_offset_bake_law():
    # FORMAT.md 2.3 / M4 5.4: the load-time bake adds the part's V-offset to every v byte, and the part's
    # own 128-line block was UPLOADED at that same page line -- so the two cancel and a PRE-BAKE v indexes
    # the decoded page row directly. Asserted for both stock V-offsets (0 and 128).
    for voff in (0, 128):
        assert T.page_row(0, voff) == 0
        assert T.page_row(77, voff) == 77
        assert T.page_row(127, voff) == 127


def test_uv_texcoord_samples_the_texel_centre():
    word = 10 | (20 << 8)                                     # the pool entry is u | v<<8
    u, v = T.uv_texcoord(word, 128)
    assert u == pytest.approx(10.5 / 128) and v == pytest.approx(20.5 / 128)
    assert T.uv_texcoord(word, 0) == T.uv_texcoord(word, 128)  # the bake cancels either way


# =========================================================== OFFLINE: a synthetic 2-page package
def _mp(*, parts=2, clut_rows=2, tpage=(0x93, 0x93), clut=(0x3990, 0x39D0), v_offset=(128, 0),
        tex_file_offset=0x1000, tex_bytes=None, clut_bytes=None) -> C.ModelPackage:
    """A hand-built ModelPackage carrying only the fields the texture decode reads."""
    return C.ModelPackage(
        tex_offset=0x180, motion_count=0, part_count=parts, clut_rows=clut_rows,
        tex_bytes=parts * T.PAGE_BYTES if tex_bytes is None else tex_bytes,
        clut_bytes=clut_rows * T.CLUT_ROW_BYTES if clut_bytes is None else clut_bytes,
        model_bytes=0, first_block=0, motion_offsets=[], tpage=list(tpage), clut=list(clut),
        v_offset=list(v_offset), header_offset=tex_file_offset - 0x180,
        tex_file_offset=tex_file_offset, model_file_offset=0, model_bytes_total=0)


def _synthetic_texture_blob(mp: C.ModelPackage, page_fill, palettes) -> bytes:
    """``page_fill(part) -> 0x4000 index bytes``; ``palettes[row] -> 256 u16 entries``."""
    buf = bytearray(mp.tex_file_offset)
    for i in range(mp.part_count):
        buf += bytes(page_fill(i))
    for row in range(mp.clut_rows):
        buf += struct.pack("<256H", *palettes[row])
    return bytes(buf)


def _ramp_palette(base_r: int):
    # entry 0 = transparent (the stock convention), entries 1..255 = a red ramp offset per row
    return [0] + [0x8000 | (((base_r + i) % 32)) for i in range(1, 256)]


def test_part_textures_resolves_file_offsets():
    mp = _mp()
    parts = T.part_textures(mp)
    assert [p.page_offset for p in parts] == [0x1000, 0x1000 + T.PAGE_BYTES]
    clut_base = 0x1000 + 2 * T.PAGE_BYTES
    assert [p.clut_offset for p in parts] == [clut_base, clut_base + T.CLUT_ROW_BYTES]
    assert [p.vram for p in parts] == [(192, 384), (192, 256)]


def test_texture_check_accepts_a_well_formed_package():
    mp = _mp()
    blob = _synthetic_texture_blob(mp, lambda i: bytes([i]) * T.PAGE_BYTES,
                                   [_ramp_palette(0), _ramp_palette(8)])
    chk = T.texture_check(blob, mp)
    assert chk["decodable"] and chk["reasons"] == []


@pytest.mark.parametrize("kw,needle", [
    (dict(tpage=(0x13, 0x93)), "colour mode 0"),                     # 4bpp page
    (dict(tpage=(0x113, 0x93)), "colour mode 2"),                    # 16bpp page
    (dict(tex_bytes=0x1000), "texBytes"),                            # size law broken
    (dict(clut_bytes=0x100), "clutBytes"),
    (dict(clut=(0x3990, 0x3D90)), "outside the"),                    # CLUT row past the strip
    (dict(clut=(0x3990, 0x39D8)), "do not fit"),                     # 256 entries overflow the row
])
def test_texture_check_refuses_and_explains(kw, needle):
    mp = _mp(**kw)
    blob = _synthetic_texture_blob(_mp(), lambda i: bytes([i]) * T.PAGE_BYTES,
                                   [_ramp_palette(0), _ramp_palette(8)])
    chk = T.texture_check(blob, mp)
    assert not chk["decodable"]
    assert any(needle in r for r in chk["reasons"]), chk["reasons"]


def test_texture_check_refuses_a_truncated_blob():
    mp = _mp()
    chk = T.texture_check(b"\x00" * 0x2000, mp)
    assert not chk["decodable"] and any("past the" in r for r in chk["reasons"])


def test_decode_page_rgba_is_pure_and_bounds_checked():
    pal = [(0, 0, 0, 0), (10, 20, 30, 255), (40, 50, 60, 255)]
    px = bytes([0, 1, 2, 1])
    assert T.decode_page_rgba(px, pal, page_w=2, page_h=2) == [pal[0], pal[1], pal[2], pal[1]]
    with pytest.raises(T.TextureError):
        T.decode_page_rgba(bytes([0, 1]), pal, page_w=2, page_h=2)


def test_decode_pages_end_to_end_on_a_synthetic_package():
    mp = _mp()

    def fill(part):                                        # page p: index (x+p) % 256 along each row
        return bytes(((x + part) % 256) for _y in range(T.PAGE_H) for x in range(T.PAGE_W))

    pals = [_ramp_palette(0), _ramp_palette(8)]
    blob = _synthetic_texture_blob(mp, fill, pals)
    imgs = T.decode_pages(blob, mp)
    assert sorted(imgs) == [0, 1]
    for part, img in imgs.items():
        assert img.size == (T.PAGE_W, T.PAGE_H) and img.mode == "RGBA"
        assert img.getpixel((0, 0)) == T.bgr555_rgba(pals[part][(0 + part) % 256])
        assert img.getpixel((5, 3)) == T.bgr555_rgba(pals[part][(5 + part) % 256])
    assert imgs[0].getpixel((0, 0)) == (0, 0, 0, 0)         # index 0 -> the transparent entry


def test_decode_pages_raises_on_an_undecodable_package():
    mp = _mp(tpage=(0x13, 0x93))
    blob = _synthetic_texture_blob(_mp(), lambda i: bytes([i]) * T.PAGE_BYTES,
                                   [_ramp_palette(0), _ramp_palette(8)])
    with pytest.raises(T.TextureError) as ei:
        T.decode_pages(blob, mp)
    assert "8bpp" in str(ei.value)


# =========================================================== OFFLINE: the textured mesh build
# A 2-bone / 1-mesh geom with TWO FT3 faces on DIFFERENT parts, sharing all three pool vertices. Vertex 0
# carries the SAME uv value in both faces (it must weld); vertices 1+2 carry different ones (they must
# split) -- so one synthetic block exercises grouping, welding and seam splitting at once.
_P_MESH2 = 0x18 + 1 * 4                      # the pMeshTable law for boneCount=2 (one BoneLink row)
# the five pools, each at the 4-aligned end of the previous, after the 0x28-byte MeshDesc (ends 0x44)
_V_VPB, _V_POS, _V_PRIM, _V_UV, _V_COL = 0x44, 0x48, 0x60, 0x88, 0x94


def _two_part_geom():
    header = struct.pack("<BBBB", 0, 0, 2, 1) + struct.pack("<II", 0, 0)
    header += struct.pack("<III", 0x14, _P_MESH2, 0)
    bonelink = struct.pack("<HBB", 100, 0, 0)                       # node1: length 100, parent 0
    counts = [0, 2, 0, 0, 0, 0, 0, 0]                               # two FT3 faces
    meshdesc = struct.pack("<H", 0) + b"".join(struct.pack("<H", c) for c in counts)
    meshdesc += struct.pack("<Bb", 0, 0)
    meshdesc += struct.pack("<IIIII", _V_VPB, _V_POS, _V_PRIM, _V_UV, _V_COL)

    vpb = struct.pack("<HH", 2, 1)                                  # bone0 owns v0,v1; bone1 owns v2
    positions = b"".join(struct.pack("<4h", *p) for p in
                         ((10, 0, 0, 1), (0, 10, 0, 1), (0, 0, 10, 1)))

    def ft3(part, uv_idx):
        r = struct.pack("<HHH", 0, 1, 2)                             # v0,v1,v2
        r += struct.pack("<BB", part, 0)                             # part @+0x06
        r += struct.pack("<BBBB", 128, 128, 128, 0)                  # rgb @+0x08
        r += struct.pack("<HHH", *uv_idx)                            # uv @+0x0c
        r += struct.pack("<BB", 0, 0)                                # flag @+0x12
        assert len(r) == 0x14
        return r

    prim = ft3(0, (0, 1, 2)) + ft3(1, (3, 4, 5))
    # pool: face A (10,20) (30,40) (50,60) ; face B (10,20) [same value as A@v0] (11,21) (12,22)
    uvpool = struct.pack("<6H", 10 | (20 << 8), 30 | (40 << 8), 50 | (60 << 8),
                         10 | (20 << 8), 11 | (21 << 8), 12 | (22 << 8))
    blob = bytearray(_V_COL)
    blob[0:len(header)] = header
    blob[0x18:0x18 + len(bonelink)] = bonelink
    blob[_P_MESH2:_P_MESH2 + len(meshdesc)] = meshdesc
    blob[_V_VPB:_V_VPB + len(vpb)] = vpb
    blob[_V_POS:_V_POS + len(positions)] = positions
    blob[_V_PRIM:_V_PRIM + len(prim)] = prim
    blob[_V_UV:_V_UV + len(uvpool)] = uvpool
    blob = bytes(blob)
    g = C.parse_geom(blob, base=0, block_end=_V_COL)
    chk = C.geom_checks(blob, g, limit=_V_COL)
    assert all(chk[k] for k in ("pMeshTable_law", "chain_vertsPerBone_to_positions",
                                "chain_positions_to_primitives", "chain_primitives_to_uv",
                                "chain_uv_to_colors")), chk
    return blob, g


def _fake_image(tag):
    from PIL import Image
    return Image.new("RGBA", (T.PAGE_W, T.PAGE_H), (tag, tag, tag, 255))


def test_untextured_adapt_is_unchanged_by_the_texture_rung():
    # The default path must stay exactly what it was: one material per MESH, texture None, one welded
    # vertex per pool entry, raw /255 UVs, no embedded images.
    blob, g = _two_part_geom()
    model = B.adapt_model(blob, g, geo="TC")
    assert model["materials"] == [{"name": "TC_mesh0", "texture": None}]
    assert model["textures"] == {}
    assert len(model["meshes"][0]["verts"]) == 3
    assert model["meshes"][0]["uvs"][0] == [10 / 255.0, 20 / 255.0]
    assert len(model["meshes"][0]["submeshes"]) == 1


def test_textured_adapt_groups_by_part_and_splits_only_real_seams():
    blob, g = _two_part_geom()
    imgs = {0: _fake_image(11), 1: _fake_image(22)}
    model = B.adapt_model(blob, g, geo="TC", part_images=imgs, v_offsets=[128, 0])

    assert [m["name"] for m in model["materials"]] == ["TC_part0", "TC_part1"]
    assert [m["texture"] for m in model["materials"]] == ["TC_page0", "TC_page1"]
    assert sorted(model["textures"]) == ["TC_page0", "TC_page1"]
    me = model["meshes"][0]
    # one submesh per part, each 1 tri
    assert [s["material_idx"] for s in me["submeshes"]] == [0, 1]
    assert [len(s["tris"]) for s in me["submeshes"]] == [1, 1]
    # vertex 0 welds (same UV value in both faces); vertices 1+2 split -> 3 + 2 = 5
    assert len(me["verts"]) == 5 and len(me["uvs"]) == 5 and len(me["weights"]) == 5
    assert me["submeshes"][0]["tris"][0][0] == me["submeshes"][1]["tris"][0][0]   # the welded corner
    assert me["submeshes"][0]["tris"][0][1] != me["submeshes"][1]["tris"][0][1]   # a split corner
    # UVs: page-normalised, texel-centred, and pre-flipped for models/gltf.py's own V flip
    assert me["uvs"][0] == [pytest.approx(10.5 / 128), pytest.approx(1.0 - 20.5 / 128)]
    # rigid run-length skin survives the split: v0,v1 -> bone0, v2 -> bone1
    assert [w[0][0] for w in me["weights"]] == [0, 0, 1, 0, 1]


def test_textured_adapt_falls_back_for_a_part_with_no_page():
    # D3 3.3: 6 of the 24 stock packages carry `part` bytes past partCount; the engine renders those with
    # tpage=clut=0. Exporting them UNTEXTURED is the honest reading -- never invent a page for them.
    blob, g = _two_part_geom()
    model = B.adapt_model(blob, g, geo="TC", part_images={0: _fake_image(11)}, v_offsets=[128, 0])
    assert [m["name"] for m in model["materials"]] == ["TC_untextured", "TC_part0"]
    assert [m["texture"] for m in model["materials"]] == [None, "TC_page0"]
    assert sorted(model["textures"]) == ["TC_page0"]
    unbound = model["meshes"][0]["submeshes"][0]
    assert unbound["material_idx"] == 0 and len(unbound["tris"]) == 1


def test_resolve_textures_honours_the_off_knob_and_reports_a_refusal():
    mp = _mp()
    blob = _synthetic_texture_blob(mp, lambda i: bytes([i]) * T.PAGE_BYTES,
                                   [_ramp_palette(0), _ramp_palette(8)])
    assert X.resolve_textures(blob, mp, False) == (None, [])           # explicit off: no decode, no note
    imgs, notes = X.resolve_textures(blob, mp, True)
    assert notes == [] and sorted(imgs) == [0, 1]
    imgs, notes = X.resolve_textures(blob, _mp(tpage=(0x13, 0x93)), True)
    assert imgs is None and len(notes) == 1 and "UNTEXTURED" in notes[0] and "8bpp" in notes[0]


# =========================================================== GAME-GATED: the real Bahamut
@pytest.mark.skipif(not _have(227), reason="needs local C:/gd/SCRATCH/summon-format/ef227.bytes")
def test_ef227_texture_block_matches_the_disassembled_layout():
    blob = _blob227()
    mp = C.creature_package(blob)
    chk = T.texture_check(blob, mp)
    assert chk["decodable"], chk["reasons"]
    assert (mp.part_count, mp.clut_rows) == (6, 6)
    assert mp.tex_bytes == 6 * T.PAGE_BYTES and mp.clut_bytes == 6 * T.CLUT_ROW_BYTES
    parts = chk["parts"]
    # D3 3.2's byte evidence: tpage 147,147,148,148,149,149 / vOff 128,0,... -> a clean 3x2 VRAM tiling
    assert [p.tpage for p in parts] == [0x93, 0x93, 0x94, 0x94, 0x95, 0x95]
    assert [p.v_offset for p in parts] == [128, 0, 128, 0, 128, 0]
    assert [p.vram for p in parts] == [(192, 384), (192, 256), (256, 384), (256, 256),
                                       (320, 384), (320, 256)]
    assert [p.clut_row for p in parts] == [0, 1, 2, 3, 4, 5]        # one full 256-entry row per part
    assert parts[0].page_offset == mp.tex_file_offset == 0x4A1A0
    assert parts[0].clut_offset == 0x621A0


@pytest.mark.skipif(not _have(227), reason="needs local C:/gd/SCRATCH/summon-format/ef227.bytes")
def test_ef227_pages_decode_to_six_populated_images():
    blob = _blob227()
    mp = C.creature_package(blob)
    imgs = T.decode_pages(blob, mp)
    assert sorted(imgs) == [0, 1, 2, 3, 4, 5]
    for img in imgs.values():
        assert img.size == (128, 128) and img.mode == "RGBA"
        alpha = img.tobytes()[3::4]
        assert set(alpha) == {0, 255}                              # binary alpha: entry 0 vs the rest
        assert sum(1 for a in alpha if a) > 0.9 * 128 * 128         # the pages are near-fully painted


@pytest.mark.skipif(not _have(227), reason="needs local C:/gd/SCRATCH/summon-format/ef227.bytes")
def test_ef227_every_uv_lands_inside_its_own_page():
    # The whole V-offset-bake argument in one assertion: the PRE-BAKE pool bytes must address the decoded
    # 128x128 page directly. If they ever exceeded it the bake would NOT be cancelling.
    blob = _blob227()
    mp = C.creature_package(blob)
    g = C.creature_geom(blob, mp)
    n = 0
    for mesh in g.meshes:
        pool = g.base + mesh.p_uv
        for prim in C.iter_primitives(blob, g, mesh):
            for ui in prim.get("uv", []):
                word = struct.unpack_from("<H", blob, pool + 2 * ui)[0]
                row = T.page_row((word >> 8) & 0xFF, mp.v_offset[prim["part"]])
                assert 0 <= (word & 0xFF) < T.PAGE_W and 0 <= row < T.PAGE_H
                n += 1
    assert n == 7331                                               # the two meshes' whole UV pool


@pytest.mark.skipif(not _have(227), reason="needs local C:/gd/SCRATCH/summon-format/ef227.bytes")
def test_ef227_uvs_beat_every_wrong_hypothesis_on_transparent_hits():
    """THE FALSIFICATION: sample each textured face's INTERIOR (its UV centroid + the midpoints to each
    corner) and count the samples that land on the page's TRANSPARENT entry. Stock art paints the region
    the model samples, so a correct decode should hit none -- and it hits exactly ZERO of 9,747 samples,
    while a v-flip / u-flip / u<->v swap / a page misbinding each hit dozens. (Face CORNERS do NOT
    discriminate: they sit on the boundary of the painted region, where the correct decode scores WORSE
    than a swap -- an uncalibrated instrument would have "refuted" the right answer. Sample interiors.)"""
    blob = _blob227()
    mp = C.creature_package(blob)
    g = C.creature_geom(blob, mp)
    opaque = {}
    for p in T.part_textures(mp):
        pal = T.read_palette(blob, p.clut_offset)
        px = blob[p.page_offset:p.page_offset + T.PAGE_BYTES]
        opaque[p.index] = [pal[i][3] > 0 for i in px]

    faces = []
    for mesh in g.meshes:
        pool = g.base + mesh.p_uv
        for prim in C.iter_primitives(blob, g, mesh):
            if "uv" in prim:
                faces.append((prim["part"], [struct.unpack_from("<H", blob, pool + 2 * i)[0]
                                             for i in prim["uv"]]))

    def bad_samples(fn, page_shift=0):
        bad = tot = 0
        for part, words in faces:
            mask = opaque[(part + page_shift) % len(opaque)]
            pts = [fn(w & 0xFF, (w >> 8) & 0xFF) for w in words]
            cx = sum(p[0] for p in pts) / len(pts)
            cy = sum(p[1] for p in pts) / len(pts)
            for (u, v) in [(cx, cy)] + [((cx + p[0]) / 2, (cy + p[1]) / 2) for p in pts]:
                tot += 1
                bad += not mask[(int(v) % 128) * 128 + (int(u) % 128)]
        return bad, tot

    correct, total = bad_samples(lambda u, v: (u, v))
    assert total == 9747                                           # 2416 faces x (centroid + one midpoint per corner)
    assert correct == 0, f"the correct decode sampled {correct}/{total} TRANSPARENT texels"
    for name, fn, shift in (("v flipped", lambda u, v: (u, 127 - v), 0),
                            ("u flipped", lambda u, v: (127 - u, v), 0),
                            ("u<->v swapped", lambda u, v: (v, u), 0),
                            ("page misbound", lambda u, v: (u, v), 1)):
        bad, _ = bad_samples(fn, shift)
        assert bad >= 20, f"{name} only misses {bad} samples -- the instrument stopped discriminating"


@pytest.mark.skipif(not _have(227), reason="needs local C:/gd/SCRATCH/summon-format/ef227.bytes")
def test_ef227_export_embeds_the_pages_and_the_off_knob_reverts_to_untextured(tmp_path):
    import json

    def _gltf(path):
        b = open(path, "rb").read()
        jlen = struct.unpack_from("<I", b, 12)[0]
        return json.loads(b[20:20 + jlen].decode("utf-8"))

    on = tmp_path / "tex.glb"
    man = X.export_summon_glb(_ef(227), str(on), geo="BAHA", anims="none")
    assert man["textures"] == 6 and man["creature"]["textured"] is True and not man["warnings"]
    gl = _gltf(on)
    assert len(gl["images"]) == 6 and len(gl["textures"]) == 6
    assert [m["name"] for m in gl["materials"]] == [f"BAHA_part{i}" for i in range(6)]
    assert all("baseColorTexture" in m["pbrMetallicRoughness"] for m in gl["materials"])
    # texture binding is per FACE-PART, so a mesh carries one primitive per part it uses (4 + 3 for ef227)
    assert sorted(len(m["primitives"]) for m in gl["meshes"]) == [3, 4]

    off = tmp_path / "plain.glb"
    man2 = X.export_summon_glb(_ef(227), str(off), geo="BAHA", anims="none", textures=False)
    assert man2["textures"] == 0 and man2["creature"]["textured"] is False
    gl2 = _gltf(off)
    assert "images" not in gl2 and len(gl2["materials"]) == 2
