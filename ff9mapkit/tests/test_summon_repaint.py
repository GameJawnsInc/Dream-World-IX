r"""Tests for the summon TEXEL REPAINT lane (``summons/repaint.py``) and its CLI ladder.

    py -m pytest tests/test_summon_repaint.py -q

Three halves, deliberately unequal:

* **the lane's own laws** (sections 0-6), run on containers THIS FILE WROTE -- no install, no
  extracted corpus, no game bytes.  Every refusal the rung establishes has a test here, because a
  refusal that shipped untested is a refusal nobody would notice losing;
* **the CLI contract** (section 7): ``export-art`` is registered on the reskin lane and only there,
  the whole ladder resolves a ``[[reskin.texel]]`` spec offline through ``--from``, and the 0 / 1 / 2
  exit codes mean what the lane says they mean;
* **the install/corpus-gated acceptance bar** (section 8): the 93/93 indexed round trip over the real
  creature corpus, ``export-art`` on ef227 end to end, and the emblem-class COMPOSED build -- the
  CLUT lane and the texel lane in one container, with the three cast-proven CLUT shas still holding.

THE SYNTHETIC CONTAINER (section 0) adapts ``test_summon_reskin``'s fixture and adds the two things a
texel test needs and a palette test does not: PAGE CONTENT that is not all-zero, and a real creature
GEOM in the id-5 payload carrying FT4 faces with a UV pool -- so the coverage rasteriser has genuine
uv data to read instead of being skipped on the one lane that depends on it.  The per-part TPAGE
ladder reproduces the stock ``(192,384)(192,256)(256,384)...`` rungs so VRAM cells are distinct and
the collision gate has something real to test against.

PROVENANCE: every palette word and every texel index in this file is COMPUTED by a small arithmetic
generator -- never a byte run copied from the corpus or from an install.  The install/corpus-gated
tests compare HASHES of bytes they rebuild locally and commit no data; the PNGs they write land in
pytest's own tmp dir.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import struct
from pathlib import Path

import pytest

from ff9mapkit import cli
from ff9mapkit import config
from ff9mapkit.summons import container as KC
from ff9mapkit.summons import export as KE
from ff9mapkit.summons import repaint as RP
from ff9mapkit.summons import reskin as RS
from ff9mapkit.summons import texanim as TA
from ff9mapkit.summons import texture as KT
from tests.test_summon_reskin import (_assemble, _build_scenery_id0, _words, synth_clut16,
                                      synth_clut256, build_synth_container,
                                      build_synth_creatureless_container)
from tests.test_summon_texanim import synth_region

SECTOR = KC.SECTOR
CORPUS = Path(r"C:/gd/SCRATCH/summon-format")
_STUDY = Path(__file__).resolve().parents[2] / "studies" / "custom-summons" / "tier-w"


def _has_install() -> bool:
    try:
        return bool(config.find_game_path(None))
    except Exception:
        return False


needs_install = pytest.mark.skipif(not _has_install(), reason="no FF9 install resolvable")
needs_corpus = pytest.mark.skipif(
    not (CORPUS / "ef227.bytes").is_file(),
    reason="needs-corpus: the extracted ef###.bytes corpus is not on this machine")
needs_study_specs = pytest.mark.skipif(
    not (_STUDY / "bahamut_reskin.toml").is_file(),
    reason="the tier-w study specs are not in this tree (installed wheel / trimmed checkout)")


# ============================================================ (0) the synthetic TEXEL container
#: the sampled island every synthetic part declares: one quad over this inclusive uv rect, leaving a
#: 4-texel dead margin all the way round -- so "covered", "dead pad" and "interior hole" are all
#: reachable and all COUNTABLE by hand.
ISLAND = (4, 4, 123, 123)
#: a deliberate index-0 patch INSIDE the island, so the cutout law has real transparent texels to
#: punch and fill rather than a corpus assumption.
CUTOUT = (10, 10, 15, 15)


def synth_page(part: int) -> bytes:
    """One 128x128 page of COMPUTED indices.

    Never index 0 except inside :data:`CUTOUT` -- so a cutout crossing is something a test DOES, not
    something the generator sprinkles at random and a later assertion has to work around.
    """
    px = bytearray(KT.PAGE_W * KT.PAGE_H)
    for y in range(KT.PAGE_H):
        for x in range(KT.PAGE_W):
            px[y * KT.PAGE_W + x] = 1 + ((x * 5 + y * 11 + part * 37) % 255)
    x0, y0, x1, y1 = CUTOUT
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            px[y * KT.PAGE_W + x] = 0
    return bytes(px)


def _a4(n: int) -> int:
    return (n + 3) & ~3


#: the FT4 face-record stride, taken from the shipped table rather than typed: ``PRIM_TYPES``' second
#: field is the OPCODE (0x2C) and its third is the stride (0x18), and confusing the two produces a
#: block the scanner silently rejects -- which reads exactly like a missing GEOM.
FT4_STRIDE = KC.PRIM_TYPES[0][2]
assert KC.PRIM_TYPES[0][0] == "FT4" and FT4_STRIDE == 0x18


def _creature_geom_payload(nparts: int) -> bytes:
    """A real GEOM block: 1 bone, 1 mesh, one FT4 quad PER PART over :data:`ISLAND`, with the uv pool
    the coverage rasteriser reads.  Every chain identity ``container.geom_checks`` asserts holds, so
    it is a block the shipped parser accepts rather than a shape only this test believes in."""
    nf = nparts
    nv = 4 * nf
    p_vpb = 0x40                                          # right after the 0x28 MeshDesc at 0x18
    p_pos = _a4(p_vpb + 2 * 1)                            # boneCount == 1
    p_prim = _a4(p_pos + 8 * nv)
    p_uv = _a4(p_prim + nf * FT4_STRIDE)
    p_col = _a4(p_uv + 2 * 4 * nf)                        # 4 uv indices per quad
    end = p_col                                           # col_count == 0

    g = bytearray(end)
    g[0:4] = bytes([0x00, 0x00, 1, 1])                    # flags, zero, boneCount, meshCount
    struct.pack_into("<II", g, 0x04, 0, 0)
    struct.pack_into("<I", g, 0x0C, 0x14)                 # pBoneTable -- the scanner's needle
    struct.pack_into("<I", g, 0x10, 0x18)                 # pMeshTable == 0x18 + (1-1)*4
    struct.pack_into("<I", g, 0x14, 0)                    # listHead
    d = 0x18
    struct.pack_into("<H", g, d + 0x00, 0)                # unknown0
    struct.pack_into("<H", g, d + 0x02, nf)               # FT4 count
    struct.pack_into("<BB", g, d + 0x12, 0, 0)            # zero, otBias
    struct.pack_into("<IIIII", g, d + 0x14, p_vpb, p_pos, p_prim, p_uv, p_col)
    struct.pack_into("<H", g, p_vpb, nv)                  # vertsPerBone[0]
    x0, y0, x1, y1 = ISLAND
    for f in range(nf):
        o = p_prim + f * FT4_STRIDE
        for k in range(4):
            struct.pack_into("<H", g, o + 2 * k, 4 * f + k)          # vertex indices
            struct.pack_into("<H", g, o + 0x08 + 2 * k, 4 * f + k)   # uv-pool indices
        g[o + 0x13] = f                                              # part byte
        g[o + 0x15] = 0                                              # flag
        pool = p_uv + 8 * f
        for k, (u, v) in enumerate(((x0, y0), (x1, y0), (x1, y1), (x0, y1))):
            struct.pack_into("<H", g, pool + 2 * k, u | (v << 8))
    return bytes(g)


def _texel_id4(nparts: int, pal256_list, geom_len: int, texanim: int = 0) -> bytes:
    """The id-4 payload: header + ``nparts`` pages WITH CONTENT + ``nparts`` CLUT rows.

    ``firstBlock`` is set to the GEOM block's real end so ``creature_geom``'s ``block_end`` closes the
    last colour pool, and so ``texanim_region`` measures exactly ``texanim`` bytes past it.
    """
    nmotion = 1 if texanim else 0
    tex_off = 0x180 + 4 * nmotion
    header = bytearray(tex_off)
    struct.pack_into("<hhhH", header, 0, tex_off, nmotion, nparts, nparts)
    struct.pack_into("<II", header, 8, nparts * KT.PAGE_BYTES, nparts * 0x200)
    # modelBytes = the model image's end; firstBlock = the GEOM block's end (both header-relative)
    struct.pack_into("<II", header, 0x10, tex_off + geom_len + texanim + 0x100, tex_off + geom_len)
    for i in range(nparts):
        # the stock L3 ladder: x = (3 + i//2)*64, y = 256 + (128 if i even else 0)
        struct.pack_into("<H", header, 0x18 + 2 * i, 0x80 | 0x10 | (3 + i // 2))
        struct.pack_into("<H", header, 0x24 + 2 * i, ((KT.CLUT_STRIP_Y + i) << 6) | 0x10)
        struct.pack_into("<H", header, 0x30 + 2 * i, 128 if i % 2 == 0 else 0)
    if nmotion:
        struct.pack_into("<I", header, 0x180, tex_off + geom_len + texanim)
    pages = b"".join(synth_page(i) for i in range(nparts))
    cluts = b"".join(_words(w) for w in pal256_list)
    return bytes(header) + pages + cluts


def _collide_id0(pal16, pal256, cell=(192, 384)) -> bytes:
    """An id-0 payload that ALSO declares a streamed page rect at ``cell``.

    The default fixture's id-0 declares none, so the collision gate has nothing to hit; this variant
    is the CO-TRANSFORM fixture -- a second writer of a cell the creature already owns, which is the
    corpus's 34-cell / 5-container hazard in miniature (and, for a creature page, one that stock
    never produces: 0 collisions over 24 packages / 93 pages).
    """
    x, y = cell
    body = bytearray(0x42C)
    struct.pack_into("<iii", body, 0x00, 0x14, 0x24, 1)     # pageBlockRel, inlineRel, nInline
    struct.pack_into("<HH", body, 0x0C, 1, 1)               # nClut4, nClut8
    struct.pack_into("<HH", body, 0x10, 0x3D00, 0x3D40)     # VRAM (0,244) 4bpp + (0,245) 8bpp
    struct.pack_into("<ii", body, 0x14, 0x42C, 1)           # pixelDataRel, nPageRects = 1
    struct.pack_into("<HHHH", body, 0x1C, x, y, 64, 128)    # THE COLLIDING page rect
    struct.pack_into("<HHHH", body, 0x24, 0, 244, 256, 2)   # the inline CLUT rect
    row = bytearray(512)
    row[0:32] = _words(pal16)
    body[0x2C:0x2C + 512] = row
    body[0x22C:0x22C + 512] = _words(pal256)
    return bytes(body) + bytes(0x4000)                      # the page rect's own pixel stream


def build_texel_container(nparts: int = 2, texanim: int = 0, collide=None) -> bytes:
    """A whole ``ef###``-shaped container with repaintable creature pages."""
    geom = _creature_geom_payload(nparts)
    id0 = (_collide_id0(synth_clut16(), synth_clut256(seed=3), collide) if collide else
           _build_scenery_id0(synth_clut16(), synth_clut256(seed=3)))
    id4 = _texel_id4(nparts, [synth_clut256(seed=5 + i) for i in range(nparts)], len(geom),
                     texanim=texanim)
    id5 = geom + bytes(texanim) + bytes(0x100)
    return _assemble([(0, [(0, id0), (3, bytes([0x55]) * SECTOR), (4, id4), (5, id5)])])


def _spec_dict(blob: bytes, rows, effect: int = 999, orth=None, targets=None) -> dict:
    r = {"effect": effect, "label": "texeltest",
         "expect_sha256": hashlib.sha256(blob).hexdigest(), "texel": rows}
    if targets is not None:
        r["target"] = targets
    if orth:
        r["orthogonality"] = orth
    return {"reskin": r}


def _write_png(tmp_path, blob: bytes, name: str, px: bytes) -> Path:
    page = RP.texel_page(blob, name)
    p = tmp_path / ("%s.png" % name)
    RP.write_indexed_png(px, RP.palette_words(blob, page), page.w, page.h, p)
    return p


def _page_bytes(blob: bytes, name: str) -> bytes:
    p = RP.texel_page(blob, name)
    return blob[p.page_offset:p.page_offset + p.page_bytes]


# ---- the W7 texanim fixtures ---------------------------------------------------------------------
#: TWO clip families on part 0, each a live window plus ONE source frame it blits from -- the ef038
#: shape (a window and its spare art), at coordinates this file chose.  The window/source x and w are
#: VRAM HALFWORDS in the file, so the TEXEL rects below are doubled: window (20,30,10,8) <- source
#: (60,30,10,8), and window (20,50,10,8) <- source (60,50,10,8).  All four sit clear of :data:`CUTOUT`
#: so a whole-page repaint covers every one of their texels and the cutout law never enters the test.
TEXANIM_CLIPS = [(0, 0x1000, 0, 0, 1, (10, 30, 5, 8), [(30, 30)]),
                 (0, 0x1000, 0, 0, 1, (10, 50, 5, 8), [(30, 50)])]
#: the same rects in TEXEL space, as the gate reports them -- window, source, per clip.
TEXANIM_RECTS = [((20, 30, 10, 8), (60, 30, 10, 8)), ((20, 50, 10, 8), (60, 50, 10, 8))]


def armed_texel_blob(nparts: int = 1, region: bytes = None) -> bytes:
    """The texel fixture with a texanim region that actually DECODES spliced into its armed span.

    ``build_texel_container(texanim=N)`` arms N bytes of filler, which the reader refuses -- correct,
    and exactly the armed-and-unread case, but useless for proving a lift.  The region generator lives
    with the reader's own tests and is imported rather than copied.
    """
    region = synth_region(TEXANIM_CLIPS) if region is None else region
    blob = bytearray(build_texel_container(nparts=nparts, texanim=len(region)))
    ta = RS.texanim_region(bytes(blob))
    assert ta.armed and ta.nbytes == len(region)
    blob[ta.lo:ta.hi] = region
    return bytes(blob)


def _bump(v: int) -> int:
    """Move one index without ever crossing the transparent boundary in either direction: 0 stays 0,
    and every other value maps to a DIFFERENT non-zero index.  So these edits exercise the texanim
    gate alone, never the cutout law as well."""
    return v if v == 0 else 1 + (v % 255)


def _repaint_all(px: bytes) -> bytes:
    return bytes(_bump(v) for v in px)


def _repaint_rect(px: bytes, x: int, y: int, w: int, h: int) -> bytes:
    out = bytearray(px)
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            out[yy * KT.PAGE_W + xx] = _bump(out[yy * KT.PAGE_W + xx])
    return bytes(out)


# ============================================================ (1) the fixture + the derivations
def test_the_synthetic_texel_container_is_well_formed():
    """Sanity-checks the FIXTURE, so a later failure cannot be a synthetic-container bug wearing a
    repaint bug's clothes.  The phantom-GEOM assertion matters specifically here: ``_regions`` gates
    every scanned GEOM block, so a phantom one INSIDE a texel page would make the region gate fire on
    this lane's own licensed edit."""
    blob = build_texel_container(nparts=3)
    c = KC.parse_header(blob, strict=True)
    assert c.cursor_end == len(blob)
    mp = KC.creature_package(blob)
    assert KT.texture_check(blob, mp)["decodable"]
    geoms = [g.base for g in KC.scan_geom(blob)]
    assert geoms == [mp.geom_offset], "exactly one GEOM, and it is the creature's -- no phantoms"
    g = KC.creature_geom(blob, mp)
    assert g.mesh_count == 1 and sum(m.face_count for m in g.meshes) == 3
    assert not RS.texanim_region(blob).armed


def test_creature_texel_pages_are_derived_off_the_id4_header():
    blob = build_texel_container(nparts=4)
    pages = RP.creature_texel_pages(blob)
    assert [p.name for p in pages] == ["tex.part%d" % i for i in range(4)]
    mp = KC.creature_package(blob)
    for i, p in enumerate(pages):
        assert p.page_offset == mp.tex_file_offset + i * KT.PAGE_BYTES
        assert (p.w, p.h, p.bpp, p.page_bytes) == (128, 128, 8, 0x4000)
        assert p.palette_name == "creature.part%d" % i
    # the stock L3 VRAM ladder, reproduced -- distinct cells, all inside the creature band
    assert [p.vram for p in pages] == [(192, 384), (192, 256), (256, 384), (256, 256)]
    assert all(RP.CREATURE_VRAM_X[0] <= p.vram[0] < RP.CREATURE_VRAM_X[1] for p in pages)


def test_texel_page_refuses_an_unknown_name_and_names_the_addressable_set():
    blob = build_texel_container(nparts=2)
    with pytest.raises(RP.RepaintError, match="no texel page named"):
        RP.texel_page(blob, "tex.part9")


def test_a_scenery_style_texel_name_refuses_with_the_W6b_REASON():
    """THE OUT-OF-SCOPE REFUSAL.  A ``page.*`` name must not resolve to nothing quietly -- a build
    that silently matched no page would report success having spliced nothing, which is the exact
    silent failure this lane cannot afford."""
    blob = build_texel_container(nparts=2)
    with pytest.raises(RP.RepaintError) as e:
        RP.texel_page(blob, "page.s0.x576_y256.h256")
    assert RP.W6B_REASON in str(e.value)


def test_a_creatureless_container_exposes_no_texel_surface_and_says_why():
    blob = build_synth_creatureless_container()
    assert RP.creature_texel_pages(blob) == []
    assert RP.W6B_REASON in RP.creature_refusal(blob)
    with pytest.raises(RP.RepaintError, match="no id-4"):
        RP.export_art(blob, 999, None)


def test_other_page_writers_splits_an_h256_rect_into_its_two_stacked_cells():
    """Collapsing an ``h == 256`` rect into one entry would make the LOWER VRAM cell unaddressable,
    and a cell nothing can address is a cell the collision gate cannot see."""
    blob = build_texel_container(nparts=1, collide=(192, 384))
    cells = RP.other_page_writers(blob)
    assert (192, 384) in cells
    tall = build_texel_container(nparts=1, collide=(576, 256))
    # the fixture's rect is h=128, so exactly one cell; the SPLIT law is exercised by h=256 rects,
    # which the corpus supplies -- here we pin that a 128-line rect yields exactly one.
    assert len(RP.other_page_writers(tall)) == 1


# ============================================================ (2) the UV coverage rasteriser
def test_coverage_is_rasterised_from_the_containers_own_uv_pools():
    """The island is ONE quad over an inclusive uv rect, so its texel count is arithmetic, not a
    measurement -- which is what makes this a test of the rasteriser rather than of itself."""
    blob = build_texel_container(nparts=2)
    x0, y0, x1, y1 = ISLAND
    cov = RP.coverage(blob, 0)
    assert cov.available and cov.faces == 1
    assert cov.covered == (x1 - x0 + 1) * (y1 - y0 + 1)
    assert cov.dead == KT.PAGE_W * KT.PAGE_H - cov.covered
    assert cov.interior_holes == 0, "the dead set is one border-connected margin"
    assert cov.u_range == (x0, x1) and cov.v_range == (y0, y1)
    mask = cov.mask
    assert mask[y0 * 128 + x0] and mask[y1 * 128 + x1]
    assert not mask[(y0 - 1) * 128 + x0] and not mask[0]


def test_the_corner_OR_lights_a_face_too_thin_to_hold_a_texel_centre():
    """A one-texel-thin face has NO centre inside it, so a pure centre test reports its texels dead
    and the overlay tells a painter to leave live geometry alone.  The corner-OR is the fix and this
    is the case that proves it is doing something."""
    mask = bytearray(128 * 128)
    RP._fill_tri(mask, 128, 128, ((10.5, 10.5), (20.5, 10.5), (10.5, 10.5)))
    assert sum(mask) == 0, "a degenerate sliver lights nothing by centre test alone"
    for u in range(10, 21):
        mask[10 * 128 + u] = 1
    assert sum(mask) == 11


def test_coverage_reports_UNAVAILABLE_rather_than_zero_when_the_geometry_will_not_parse():
    """A container whose GEOM will not parse still has repaintable pages; it just cannot be told
    which texels are live.  Reporting zero coverage there would claim every texel is dead."""
    blob = build_synth_container(npart=1)          # the reskin fixture's id-5 is filler, not a GEOM
    cov = RP.coverage(blob, 0)
    assert not cov.available and cov.reason


def test_border_flood_separates_the_outer_pad_from_an_interior_hole():
    w = h = 16
    mask = bytearray(w * h)
    for y in range(2, 14):
        for x in range(2, 14):
            mask[y * w + x] = 1
    mask[8 * w + 8] = 0                                   # one enclosed hole
    pad = RP.border_flood(mask, w, h)
    dead = w * h - sum(mask)
    assert dead - sum(pad) == 1


# ============================================================ (3) the indexed codec
def test_the_indexed_round_trip_is_byte_identical_on_every_synthetic_page():
    """THE X0-CLASS GATE of this lane, on bytes this file wrote.  Measured 93/93 on the real corpus
    (section 8); asserted here so it runs on every machine with no corpus at all."""
    blob = build_texel_container(nparts=4)
    for p in RP.creature_texel_pages(blob):
        words = RP.palette_words(blob, p)
        px = blob[p.page_offset:p.page_offset + p.page_bytes]
        back = RP._read_indices(io.BytesIO(RP.encode_indexed_png(px, words, p.w, p.h)),
                                "rt", p.w, p.h, len(words))
        assert back == px, p.name


def test_transparent_indices_is_derived_from_the_palette_not_assumed_to_be_zero():
    words = list(synth_clut256(seed=5))
    assert RP.transparent_indices(words) == (0,)
    words[7] = 0
    assert RP.transparent_indices(words) == (0, 7)
    words[0] = 0x1234
    assert RP.transparent_indices(words) == (7,)


def test_the_import_refuses_a_png_that_is_not_indexed(tmp_path):
    from PIL import Image
    p = tmp_path / "rgba.png"
    Image.new("RGBA", (128, 128), (1, 2, 3, 255)).save(p)
    with pytest.raises(RP.RepaintError) as e:
        RP.read_indexed_png(p, 128, 128, 256)
    assert "not \"P\"" in str(e.value) and RP.W6B_REASON in str(e.value)


def test_the_import_refuses_a_png_of_the_wrong_size_rather_than_rescaling(tmp_path):
    blob = build_texel_container(nparts=1)
    page = RP.texel_page(blob, "tex.part0")
    words = RP.palette_words(blob, page)
    p = tmp_path / "small.png"
    RP.write_indexed_png(bytes(64 * 64), words, 64, 64, p)
    with pytest.raises(RP.RepaintError, match="no meaningful resample"):
        RP.read_indexed_png(p, 128, 128, 256)


def test_the_import_refuses_an_index_past_the_end_of_the_clut_row(tmp_path):
    from PIL import Image
    p = tmp_path / "hi.png"
    im = Image.frombytes("P", (128, 128), bytes([200]) * (128 * 128))
    im.putpalette(bytes(768))
    im.save(p)
    with pytest.raises(RP.RepaintError, match="palette index 200"):
        RP.read_indexed_png(p, 128, 128, 16)


def test_a_missing_source_image_refuses_by_name(tmp_path):
    with pytest.raises(RP.RepaintError, match="no such source image"):
        RP.read_indexed_png(tmp_path / "nope.png", 128, 128, 256)


# ============================================================ (4) export-art
def test_export_art_writes_a_page_an_overlay_a_manifest_and_a_guarded_scaffold(tmp_path):
    blob = build_texel_container(nparts=2)
    man = RP.export_art(blob, 999, tmp_path, source="(synthetic)")
    assert man["lane"] == "indexed" and man["effect"] == 999
    assert man["stock_sha256"] == hashlib.sha256(blob).hexdigest()
    for i in range(2):
        assert (tmp_path / ("tex.part%d.png" % i)).is_file()
        assert (tmp_path / ("tex.part%d.coverage.png" % i)).is_file()
    on_disc = json.loads((tmp_path / RP.ART_MANIFEST).read_text(encoding="utf-8"))
    x0, y0, x1, y1 = ISLAND
    for e in on_disc["parts"]:
        assert e["covered_texels"] == (x1 - x0 + 1) * (y1 - y0 + 1)
        assert e["wh"] == [128, 128] and e["page_bytes"] == 0x4000
        assert e["transparent_indices"] == [0]
    # the scaffold is EMITTED from the derivation, pre-seeded off, and re-loads as a real spec
    import tomllib
    with open(tmp_path / RP.SCAFFOLD_NAME, "rb") as fh:
        doc = tomllib.load(fh)
    rows = doc["reskin"]["texel"]
    assert len(rows) == 2 and all(r["enabled"] is False for r in rows)
    assert all(r["acknowledge_cutout_reshape"] is False for r in rows)
    for r, p in zip(rows, RP.creature_texel_pages(blob)):
        assert r["expect_page_offset"] == p.page_offset and r["expect_page_wh"] == [128, 128]


def test_export_art_round_trips_every_page_it_wrote(tmp_path):
    """The export IS the import's contract: an unedited re-import must be a byte-exact no-op, which
    is the property that makes a re-pack idempotent."""
    blob = build_texel_container(nparts=3)
    RP.export_art(blob, 999, tmp_path)
    for p in RP.creature_texel_pages(blob):
        back = RP.read_indexed_png(tmp_path / ("%s.png" % p.name), p.w, p.h, p.clut_entries)
        assert back == blob[p.page_offset:p.page_offset + p.page_bytes]


def test_export_art_refuses_the_rgba_lane_with_the_measurement_that_rules_it_out(tmp_path):
    blob = build_texel_container(nparts=1)
    with pytest.raises(RP.RepaintError) as e:
        RP.export_art(blob, 999, tmp_path, lane="rgba")
    assert RP.W6B_REASON in str(e.value) and "93/93" in str(e.value)


def test_export_art_refuses_a_destination_inside_the_repo():
    """Decoded pages are Square-Enix content.  The guard is the same one the glTF export uses, with
    no ``--force``: this is a provenance rule, not a safety prompt."""
    blob = build_texel_container(nparts=1)
    with pytest.raises(KE.SummonExportError, match="git repo"):
        RP.export_art(blob, 999, Path(__file__).resolve().parent / "_never_written")
    assert not (Path(__file__).resolve().parent / "_never_written").exists()


# ============================================================ (5) build()-level refusals
def _identity_build(blob, tmp_path, **row):
    src = _write_png(tmp_path, blob, "tex.part0", _page_bytes(blob, "tex.part0"))
    r = {"name": "tex.part0", "source": str(src)}
    r.update(row)
    return RP.build(_spec_dict(blob, [r]), str(tmp_path / "x_reskin.toml"), blob=blob)


def test_an_unedited_re_export_builds_zero_changed_bytes(tmp_path):
    blob = build_texel_container(nparts=2)
    b = _identity_build(blob, tmp_path)
    b.check = RP.self_check(b)
    assert b.patched == b.orig and not b.check.changed
    assert b.check.ok, [g.name for g in b.check.gates if not g.ok]


def test_a_real_stamp_moves_exactly_the_stamped_bytes(tmp_path):
    blob = build_texel_container(nparts=2)
    px = bytearray(_page_bytes(blob, "tex.part0"))
    ink = px[50 * 128 + 50]
    n = 0
    for y in range(40, 60):
        for x in range(40, 60):
            if px[y * 128 + x] != ink:
                px[y * 128 + x] = ink
                n += 1
    src = _write_png(tmp_path, blob, "tex.part0", bytes(px))
    b = RP.build(_spec_dict(blob, [{"name": "tex.part0", "source": str(src)}]),
                 str(tmp_path / "x_reskin.toml"), blob=blob)
    b.check = RP.self_check(b)
    assert len(b.check.changed) == n and b.check.per_target["tex.part0"] == n
    assert b.check.ok, [g.detail for g in b.check.gates if not g.ok]
    page = RP.texel_page(blob, "tex.part0")
    assert all(page.page_offset <= o < page.page_offset + page.page_bytes for o in b.check.changed)


def test_build_refuses_a_container_with_no_drift_guard_at_all(tmp_path):
    blob = build_texel_container(nparts=1)
    src = _write_png(tmp_path, blob, "tex.part0", _page_bytes(blob, "tex.part0"))
    spec = _spec_dict(blob, [{"name": "tex.part0", "source": str(src)}])
    del spec["reskin"]["expect_sha256"]
    with pytest.raises(RP.RepaintError, match="NO drift guard"):
        RP.build(spec, "t", blob=blob)
    spec["reskin"]["allow_unguarded"] = True
    assert RP.build(spec, "t", blob=blob).guard.startswith("none")


def test_build_refuses_a_spec_with_no_texel_rows(tmp_path):
    blob = build_texel_container(nparts=1)
    with pytest.raises(RP.RepaintError, match="no \\[\\[reskin.texel\\]\\]"):
        RP.build(_spec_dict(blob, []), "t", blob=blob)


def test_load_spec_refuses_a_spec_that_declares_neither_lever(tmp_path):
    p = tmp_path / "x_reskin.toml"
    p.write_text("[reskin]\neffect = 999\n", encoding="utf-8")
    with pytest.raises(RP.RepaintError, match="neither"):
        RP.load_spec(p)


def test_build_refuses_a_duplicate_texel_row(tmp_path):
    blob = build_texel_container(nparts=1)
    src = _write_png(tmp_path, blob, "tex.part0", _page_bytes(blob, "tex.part0"))
    rows = [{"name": "tex.part0", "source": str(src)}] * 2
    with pytest.raises(RP.RepaintError, match="declared twice"):
        RP.build(_spec_dict(blob, rows), "t", blob=blob)


def test_build_refuses_an_unknown_key_rather_than_ignoring_it(tmp_path):
    """A mistyped ``expect_page_offset`` would silently drop the guard, and a guard may only ever
    fail CLOSED."""
    blob = build_texel_container(nparts=1)
    src = _write_png(tmp_path, blob, "tex.part0", _page_bytes(blob, "tex.part0"))
    rows = [{"name": "tex.part0", "source": str(src), "expct_page_offset": 0}]
    with pytest.raises(RP.RepaintError, match="unknown key"):
        RP.build(_spec_dict(blob, rows), "t", blob=blob)


@pytest.mark.parametrize("key,value", [
    ("expect_page_offset", 0x1234),
    ("expect_page_bytes", 1),
    ("expect_page_wh", [64, 64]),
])
def test_every_page_guard_refuses_when_it_disagrees_with_the_derivation(key, value, tmp_path):
    blob = build_texel_container(nparts=1)
    with pytest.raises(RP.RepaintError, match="the spec guards"):
        _identity_build(blob, tmp_path, **{key: value})


def test_the_page_guards_pass_when_they_agree(tmp_path):
    blob = build_texel_container(nparts=1)
    p = RP.texel_page(blob, "tex.part0")
    b = _identity_build(blob, tmp_path, expect_page_offset=p.page_offset,
                        expect_page_bytes=p.page_bytes, expect_page_wh=list(p.wh))
    assert b.targets[0].page.page_offset == p.page_offset


def test_palette_from_must_name_the_pages_own_clut_row(tmp_path):
    """A page's palette is a HEADER FACT (its own CLUT word), not a choice: naming another row would
    mean authoring indices against colours the engine will never apply here."""
    blob = build_texel_container(nparts=2)
    with pytest.raises(RP.RepaintError, match="indexes into creature.part0"):
        _identity_build(blob, tmp_path, palette_from="creature.part1")
    b = _identity_build(blob, tmp_path, palette_from="creature.part0")
    assert b.targets[0].palette_from == "creature.part0"


def test_palette_from_refuses_a_name_no_palette_carries(tmp_path):
    blob = build_texel_container(nparts=1)
    with pytest.raises(RP.RepaintError, match="palette_from"):
        _identity_build(blob, tmp_path, palette_from="scenery.nope")


def test_a_truthy_string_acknowledge_refuses_rather_than_arming(tmp_path):
    """W5's own minted law, applied to this lane's one escape hatch."""
    blob = build_texel_container(nparts=1)
    with pytest.raises(RP.RepaintError, match="must be a BOOLEAN"):
        _identity_build(blob, tmp_path, acknowledge_cutout_reshape="true")


# ---- THE CUTOUT LAW ------------------------------------------------------------------------------
def _cutout_edit(blob, punch: int, fill: int) -> bytes:
    """Move ``punch`` opaque texels to index 0 and ``fill`` transparent ones off it."""
    px = bytearray(_page_bytes(blob, "tex.part0"))
    x0, y0, x1, y1 = CUTOUT
    done = 0
    for y in range(60, 128):
        for x in range(60, 128):
            if done >= punch:
                break
            if px[y * 128 + x] != 0:
                px[y * 128 + x] = 0
                done += 1
    done = 0
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if done >= fill:
                break
            if px[y * 128 + x] == 0:
                px[y * 128 + x] = 9
                done += 1
    return bytes(px)


@pytest.mark.parametrize("punch,fill", [(5, 0), (0, 5), (3, 4)])
def test_the_cutout_law_refuses_an_unacknowledged_crossing_in_either_direction(punch, fill,
                                                                              tmp_path):
    blob = build_texel_container(nparts=1)
    src = _write_png(tmp_path, blob, "tex.part0", _cutout_edit(blob, punch, fill))
    with pytest.raises(RP.RepaintError) as e:
        RP.build(_spec_dict(blob, [{"name": "tex.part0", "source": str(src)}]),
                 str(tmp_path / "x_reskin.toml"), blob=blob)
    msg = str(e.value)
    assert "THE CUTOUT LAW" in msg
    assert "%d punched" % punch in msg and "%d filled" % fill in msg


def test_the_cutout_law_passes_with_the_literal_acknowledgement_and_counts_both_ways(tmp_path):
    blob = build_texel_container(nparts=1)
    src = _write_png(tmp_path, blob, "tex.part0", _cutout_edit(blob, 3, 4))
    b = RP.build(_spec_dict(blob, [{"name": "tex.part0", "source": str(src),
                                    "acknowledge_cutout_reshape": True}]),
                 str(tmp_path / "x_reskin.toml"), blob=blob)
    b.check = RP.self_check(b)
    t = b.targets[0]
    assert (t.cutout_punch, t.cutout_fill) == (3, 4)
    assert b.check.ok
    g = [x for x in b.check.rules if "CUTOUT LAW" in x.name][0]
    assert g.ok and "ACKNOWLEDGED" in g.detail


def test_the_cutout_census_uses_the_DERIVED_transparent_set(tmp_path):
    """Not "index 0" hard-coded: the corpus law is 93/93 but the gate reads the palette in front of
    it, because under a composed CLUT edit that palette is not the stock one."""
    blob = bytearray(build_texel_container(nparts=1))
    page = RP.texel_page(bytes(blob), "tex.part0")
    struct.pack_into("<H", blob, page.clut_offset + 2 * 9, 0)      # make index 9 transparent too
    blob = bytes(blob)
    px = bytearray(_page_bytes(blob, "tex.part0"))
    px[70 * 128 + 70] = 9                                          # opaque -> a NEW transparent idx
    src = _write_png(tmp_path, blob, "tex.part0", bytes(px))
    with pytest.raises(RP.RepaintError, match="1 punched"):
        RP.build(_spec_dict(blob, [{"name": "tex.part0", "source": str(src)}]),
                 str(tmp_path / "x_reskin.toml"), blob=blob)


# ---- the scope refusals --------------------------------------------------------------------------
def test_an_armed_texanim_whose_table_does_NOT_decode_refuses_a_creature_repaint_outright(tmp_path):
    """THE FALLBACK CONTRACT.  W7 lifted the blanket refusal, but the lift is conditional on a
    successful PARSE -- never on the absence of an exception -- so an armed region the reader cannot
    decode still refuses exactly as it did pre-W7, with no key able to lift it."""
    blob = build_texel_container(nparts=1, texanim=116)      # armed, contents are filler
    assert RS.texanim_region(blob).armed and TA.read(blob).unparseable
    src = _write_png(tmp_path, blob, "tex.part0", _page_bytes(blob, "tex.part0"))
    rows = [{"name": "tex.part0", "source": str(src)}]
    with pytest.raises(RP.RepaintError, match="TEXANIM ARMED"):
        RP.build(_spec_dict(blob, rows), str(tmp_path / "x_reskin.toml"), blob=blob)
    rows[0]["acknowledge_texanim_frames"] = True             # ...and the L4 hatch does not open it
    with pytest.raises(RP.RepaintError, match="does not decode"):
        RP.build(_spec_dict(blob, rows), str(tmp_path / "x_reskin.toml"), blob=blob)


def test_a_repaint_that_touches_no_protected_rect_builds_under_an_armed_texanim(tmp_path):
    """W7 L4, the clear case.  The protected set is the union of every clip's live window and every
    source it blits from; an edit that stays out of all of them cannot be disturbed by the animation
    and needs no key."""
    blob = armed_texel_blob()
    assert TA.read(blob).parsed
    px = _repaint_rect(_page_bytes(blob, "tex.part0"), 90, 90, 10, 8)
    src = _write_png(tmp_path, blob, "tex.part0", px)
    b = RP.build(_spec_dict(blob, [{"name": "tex.part0", "source": str(src)}]),
                 str(tmp_path / "x_reskin.toml"), blob=blob)
    assert len(b.enabled) == 1 and b.patched != b.orig
    assert "stays clear of every protected rect" in b.targets[0].texanim_note


def test_a_whole_page_repaint_builds_under_an_armed_texanim_and_co_transforms_by_construction(
        tmp_path):
    """W7 L3.  A whole-page repaint (a global recolour or filter) reaches every rect of every clip
    family, so it co-transforms the protected set BY CONSTRUCTION -- which is why this needs no
    author-facing key.  The region itself must still come out byte-identical (R1)."""
    blob = armed_texel_blob()
    ta = RS.texanim_region(blob)
    src = _write_png(tmp_path, blob, "tex.part0", _repaint_all(_page_bytes(blob, "tex.part0")))
    b = RP.build(_spec_dict(blob, [{"name": "tex.part0", "source": str(src)}]),
                 str(tmp_path / "x_reskin.toml"), blob=blob)
    b.check = RP.self_check(b)
    assert b.check.ok
    note = b.targets[0].texanim_note
    assert "every protected rect reached" in note, \
        "the note states what is MEASURED (reach), not a consistency the tool cannot verify (V1 F2)"
    assert "clip 0: 2/2" in note and "clip 1: 2/2" in note
    assert b.patched[ta.lo:ta.hi] == blob[ta.lo:ta.hi], "THE REGION INVARIANT: region bytes moved"
    assert "byte-identical" in b.region_invariant


def test_an_asymmetric_repaint_refuses_naming_the_clip_and_the_sibling_rects_left_stock(tmp_path):
    """W7 L4, THE CO-TRANSFORM REFUSAL.  Repainting a clip's live window and leaving the frame it
    blits from stock means the window pops back to untouched art the first time the clip runs -- a
    mid-cast flicker only a playtest catches.  The refusal has to be a WORK ORDER, so it names the
    clip and the exact rects left stock rather than saying "texanim armed"."""
    blob = armed_texel_blob()
    win = TEXANIM_RECTS[0][0]
    px = _repaint_rect(_page_bytes(blob, "tex.part0"), *win)
    src = _write_png(tmp_path, blob, "tex.part0", px)
    with pytest.raises(RP.RepaintError) as e:
        RP.build(_spec_dict(blob, [{"name": "tex.part0", "source": str(src)}]),
                 str(tmp_path / "x_reskin.toml"), blob=blob)
    msg = str(e.value)
    assert "THE TEXANIM CO-TRANSFORM" in msg and "clip 0" in msg
    assert "LEFT STOCK: (%d,%d,%d,%d)" % TEXANIM_RECTS[0][1] in msg
    assert "Repainted: (%d,%d,%d,%d)" % win in msg
    assert "acknowledge_texanim_frames = true" in msg
    assert "clip 1: 0/2" in msg, "the untouched sibling family is disclosed, not hidden"


def test_the_asymmetric_repaint_builds_once_the_asymmetry_is_acknowledged(tmp_path):
    """The escape hatch -- a DELIBERATELY asymmetric strip is a legitimate authoring move, exactly as
    reshaping a torn wing edge is for the cutout law.  It is stated on the row, never inferred."""
    blob = armed_texel_blob()
    px = _repaint_rect(_page_bytes(blob, "tex.part0"), *TEXANIM_RECTS[0][0])
    src = _write_png(tmp_path, blob, "tex.part0", px)
    b = RP.build(_spec_dict(blob, [{"name": "tex.part0", "source": str(src),
                                    "acknowledge_texanim_frames": True}]),
                 str(tmp_path / "x_reskin.toml"), blob=blob)
    assert b.targets[0].ack_texanim_frames
    assert "ASYMMETRIC, acknowledged" in b.targets[0].texanim_note
    assert "byte-identical" in b.region_invariant


def test_a_page_no_clip_names_is_untouched_by_the_gate_and_the_readout_prints_the_table(tmp_path):
    """The per-PART half of the rule: the table names part 0, so part 1 carries no protected rect at
    all and a repaint of it is unconstrained.  And L6 -- the read-out prints the DECODED table, not
    the opaque "TEXANIM ARMED (N bytes)" line that made the old refusal unanswerable."""
    blob = armed_texel_blob(nparts=2)
    src = _write_png(tmp_path, blob, "tex.part1", _repaint_all(_page_bytes(blob, "tex.part1")))
    b = RP.build(_spec_dict(blob, [{"name": "tex.part1", "source": str(src)}]),
                 str(tmp_path / "x_reskin.toml"), blob=blob)
    assert "not named by any clip" in b.targets[0].texanim_note
    lines = RP.derivation_lines(blob, b.pages)
    assert any("THE TEXANIM TABLE" in l for l in lines)
    assert any("THE PROTECTED RECT SET" in l for l in lines)
    assert any("2 clip(s) over part(s) 0" in l for l in lines)
    assert any("creature texel scope is OPEN" in l for l in lines)


def test_a_disabled_row_does_not_trip_the_texanim_gate(tmp_path):
    """A disabled row splices nothing, so it states an intent rather than an edit -- and its refusals
    become live the moment it is switched on."""
    blob = build_texel_container(nparts=1, texanim=116)
    spec = _spec_dict(blob, [{"name": "tex.part0", "source": "unused.png", "enabled": False}])
    b = RP.build(spec, "t", blob=blob)
    assert b.patched == b.orig


def test_a_second_writer_of_the_pages_own_vram_cell_refuses_as_a_co_transform(tmp_path):
    """THE CO-TRANSFORM REFUSAL.  Stock never produces this for a creature page (0 collisions over 24
    packages / 93 pages), which is exactly why it is checked rather than assumed: six corpus effects
    park id-9 slots at x = 320, the ladder rung their own partCount leaves unused."""
    blob = build_texel_container(nparts=1, collide=(192, 384))
    src = _write_png(tmp_path, blob, "tex.part0", _page_bytes(blob, "tex.part0"))
    with pytest.raises(RP.RepaintError) as e:
        RP.build(_spec_dict(blob, [{"name": "tex.part0", "source": str(src)}]),
                 str(tmp_path / "x_reskin.toml"), blob=blob)
    assert "CO-TRANSFORM REFUSAL" in str(e.value) and RP.W6B_REASON in str(e.value)


def test_a_15bpp_or_4bpp_creature_package_is_not_addressable_at_all(tmp_path):
    """``texture_check`` refuses anything that is not the 8bpp 128x128 layout, and this lane inherits
    that verdict rather than inventing a second decoder for it."""
    blob = bytearray(build_texel_container(nparts=1))
    mp = KC.creature_package(bytes(blob))
    struct.pack_into("<H", blob, mp.header_offset + 0x18, 0x100)   # tpage colour mode 2 = 16bpp
    blob = bytes(blob)
    assert RP.creature_texel_pages(blob) == []
    assert "16bpp" in RP.creature_refusal(blob) and RP.W6B_REASON in RP.creature_refusal(blob)


# ---- the ART drift guard -------------------------------------------------------------------------
def test_the_art_manifest_stock_sha_refuses_art_from_another_container(tmp_path):
    """Without it a re-exported page from a patched install would pack cleanly into a container it
    never came out of -- the silent failure with no symptom."""
    blob = build_texel_container(nparts=1)
    art = tmp_path / "art"
    RP.export_art(blob, 999, art)
    man = json.loads((art / RP.ART_MANIFEST).read_text(encoding="utf-8"))
    man["stock_sha256"] = "0" * 64
    (art / RP.ART_MANIFEST).write_text(json.dumps(man), encoding="utf-8")
    rows = [{"name": "tex.part0", "source": str(art / "tex.part0.png")}]
    with pytest.raises(RP.RepaintError, match="ART DRIFT"):
        RP.build(_spec_dict(blob, rows), str(tmp_path / "x_reskin.toml"), blob=blob)


def test_the_art_manifest_page_record_must_agree_with_the_header(tmp_path):
    blob = build_texel_container(nparts=1)
    art = tmp_path / "art"
    RP.export_art(blob, 999, art)
    man = json.loads((art / RP.ART_MANIFEST).read_text(encoding="utf-8"))
    man["parts"][0]["page_offset"] += 4
    (art / RP.ART_MANIFEST).write_text(json.dumps(man), encoding="utf-8")
    rows = [{"name": "tex.part0", "source": str(art / "tex.part0.png")}]
    with pytest.raises(RP.RepaintError, match="ART DRIFT"):
        RP.build(_spec_dict(blob, rows), str(tmp_path / "x_reskin.toml"), blob=blob)


def test_no_manifest_beside_the_art_is_stated_rather_than_fabricated(tmp_path):
    blob = build_texel_container(nparts=1)
    b = _identity_build(blob, tmp_path)
    assert "no art.manifest.json" in b.targets[0].manifest_note


# ============================================================ (6) the self-check + staging
def test_the_region_partition_is_INVERTED_for_this_lane():
    """One function, two partitions.  The CLUT lane gates the pages and licenses the strip; the texel
    lane gates the strip and licenses the pages -- and they agree about every other byte."""
    blob = build_texel_container(nparts=2)
    mp = KC.creature_package(blob)
    lo, hi = mp.tex_file_offset, mp.tex_file_offset + mp.tex_bytes
    clut_lo, clut_hi = hi, hi + mp.clut_bytes

    def covers(regions, off):
        return any(a <= off < b for _n, a, b in regions)

    clut_part = RS._regions(blob, 999, partition="clut")
    tex_part = RS._regions(blob, 999, partition="texel")
    assert covers(clut_part, lo) and not covers(tex_part, lo), "the pages swap sides"
    assert not covers(clut_part, clut_lo) and covers(tex_part, clut_lo), "so does the CLUT strip"
    # ...and everything else is identical under both
    common = {(n, a, b) for n, a, b in clut_part if not (a <= lo < b)}
    assert common <= {(n, a, b) for n, a, b in tex_part} | {
        (n, a, b) for n, a, b in tex_part if clut_lo <= a}
    assert RS._regions(blob, 999) == clut_part, "the default partition is unchanged"
    with pytest.raises(RS.ReskinError, match="unknown region partition"):
        RS._regions(blob, 999, partition="nonsense")


def test_a_clut_byte_moved_by_this_lane_FAILS_the_region_gate(tmp_path):
    """The gate has to be able to fail.  A texel build that also moved a palette byte must be caught
    by the inverted partition, not merely by the accounting."""
    blob = build_texel_container(nparts=1)
    b = _identity_build(blob, tmp_path)
    page = RP.texel_page(blob, "tex.part0")
    tampered = bytearray(b.patched)
    tampered[page.clut_offset + 4] ^= 0xFF
    b.patched = bytes(tampered)
    chk = RP.self_check(b)
    bad = [g for g in chk.regions if "BYTE-IDENTICAL" in g.name][0]
    assert not bad.ok and "CLUT strip" in bad.detail
    assert not chk.ok


def test_an_edit_in_the_dead_pad_is_REPORTED_not_fatal(tmp_path):
    """The pad is 36% of the corpus's creature texels and painting it is inert -- exactly as a hue
    rotation is inert on an achromatic palette.  Name it, do not hide it, do not fail the build."""
    blob = build_texel_container(nparts=1)
    px = bytearray(_page_bytes(blob, "tex.part0"))
    for x in range(0, 4):
        px[x] = (px[x] + 1) % 255 + 1                     # row 0 is outside ISLAND by construction
    src = _write_png(tmp_path, blob, "tex.part0", bytes(px))
    b = RP.build(_spec_dict(blob, [{"name": "tex.part0", "source": str(src)}]),
                 str(tmp_path / "x_reskin.toml"), blob=blob)
    b.check = RP.self_check(b)
    assert b.targets[0].dead_changed == 4 and b.targets[0].live_changed == 0
    g = [x for x in b.check.quality if "never samples" in x.name][0]
    assert g.ok and "4 of 4 edited texels" in g.detail
    assert b.check.ok


def test_staging_refuses_the_repo_and_the_install(tmp_path):
    blob = build_texel_container(nparts=1)
    b = _identity_build(blob, tmp_path)
    with pytest.raises(RS.R.RescoreError, match="under the repo"):
        RP.stage(b, root=Path(__file__).resolve().parent, previews=False)
    game = tmp_path / "FINAL FANTASY IX"
    (game / "FF9CustomMap").mkdir(parents=True)
    with pytest.raises(RS.R.RescoreError, match="game install"):
        RP.stage(b, root=game / "FF9CustomMap", game_root=str(game), previews=False)


def test_staging_refuses_a_mod_folder_carrying_a_modfilelist(tmp_path):
    """THE SILENT-FALLBACK LAW: a folder with a list makes every unlisted override INVISIBLE and
    ``SFX.Play`` suppresses the error, so "nothing changed" would be the only symptom."""
    blob = build_texel_container(nparts=1)
    b = _identity_build(blob, tmp_path)
    mod = tmp_path / "mod"
    mod.mkdir()
    (mod / "ModFileList.txt").write_text("x\n", encoding="utf-8")
    with pytest.raises(RP.RepaintError, match="ModFileList"):
        RP.stage(b, root=tmp_path / "stage", mod_root=mod, allow_install=True, previews=False,
                 refuse_modfilelist=True)


def test_stage_writes_the_container_the_scripts_and_a_rebasable_ledger_revert(tmp_path):
    blob = build_texel_container(nparts=1)
    b = _identity_build(blob, tmp_path)
    b.check = RP.self_check(b)
    root, mod = tmp_path / "stage", tmp_path / "mod"
    man = RP.stage(b, root=root, mod_root=mod, allow_install=True, previews=False)
    dest = mod / "FF9_Data" / "SpecialEffects" / "ef999"
    assert dest.is_file() and dest.suffix == "", "the override must be EXTENSIONLESS"
    assert dest.read_bytes() == b.patched
    assert Path(man["scripts"]["deploy"]).is_file()
    assert Path(man["scripts"]["revert"]).is_file()
    led = Path(man["scripts"]["ledger_revert"])
    assert led.is_file() and led.name == "revert_summon_repaint_ledger_999.py"
    assert "--root" in led.read_text(encoding="utf-8")
    assert RP.verify(b, root=root)["ok"]
    dest.write_bytes(b"tampered")
    v = RP.verify(b, root=root)
    assert not v["ok"] and any("DIVERGES" in l for l in v["lines"])


def test_verify_refuses_a_manifest_built_against_another_stock_container(tmp_path):
    blob = build_texel_container(nparts=1)
    b = _identity_build(blob, tmp_path)
    b.check = RP.self_check(b)
    root = tmp_path / "stage"
    RP.stage(b, root=root, previews=False)
    man = json.loads((root / "build_manifest.json").read_text(encoding="utf-8"))
    man["stock_sha256"] = "0" * 64
    (root / "build_manifest.json").write_text(json.dumps(man), encoding="utf-8")
    v = RP.verify(b, root=root)
    assert not v["ok"] and any("the manifest was built against" in l for l in v["lines"])


# ---- composition + orthogonality -----------------------------------------------------------------
def test_the_two_levers_compose_into_one_container_with_disjoint_halves(tmp_path):
    """ONE container, ONE ledger, ONE revert -- and the disjointness is PROVED by intersecting the
    two changed-offset sets, never asserted."""
    blob = build_texel_container(nparts=2)
    px = bytearray(_page_bytes(blob, "tex.part0"))
    for x in range(40, 60):
        px[50 * 128 + x] = 200
    src = _write_png(tmp_path, blob, "tex.part0", bytes(px))
    b1 = RS.build({"reskin": {"effect": 999, "expect_sha256": hashlib.sha256(blob).hexdigest(),
                              "target": [{"name": "creature.part0", "hue_rotate": 40.0}]}},
                  "t", blob=blob)
    b1.check = RS.self_check(b1)
    assert b1.check.ok and b1.check.changed
    b2 = RP.build(_spec_dict(blob, [{"name": "tex.part0", "source": str(src)}]),
                  str(tmp_path / "x_reskin.toml"), blob=blob, base=b1.patched)
    b2.check = RP.self_check(b2)
    assert b2.check.ok, [g.detail for g in b2.check.gates if not g.ok]
    assert b2.composed and set(b2.base_changed) == set(b1.check.changed)
    g = [x for x in b2.check.orthogonality if "COMPOSED HALVES" in x.name][0]
    assert g.ok and "intersection 0" in g.detail
    # the composed container carries BOTH edits and nothing else
    union = set(b1.check.changed) | set(b2.check.changed)
    assert {i for i in range(len(blob)) if blob[i] != b2.patched[i]} == union


def test_compose_true_with_no_named_sibling_refuses(tmp_path):
    blob = build_texel_container(nparts=1)
    src = _write_png(tmp_path, blob, "tex.part0", _page_bytes(blob, "tex.part0"))
    spec = _spec_dict(blob, [{"name": "tex.part0", "source": str(src)}], orth={"compose": True})
    with pytest.raises(RP.RepaintError, match="names no `reskin` sibling"):
        RP.build(spec, str(tmp_path / "x_reskin.toml"), blob=blob)


def test_compose_refuses_a_sibling_that_is_not_there(tmp_path):
    blob = build_texel_container(nparts=1)
    src = _write_png(tmp_path, blob, "tex.part0", _page_bytes(blob, "tex.part0"))
    spec = _spec_dict(blob, [{"name": "tex.part0", "source": str(src)}],
                      orth={"compose": True, "reskin": "nope.toml"})
    with pytest.raises(RP.RepaintError, match="no reskin sibling at"):
        RP.build(spec, str(tmp_path / "x_reskin.toml"), blob=blob)


def test_repaints_orthogonality_gate_skips_an_unnamed_sibling_as_UNPROVEN(tmp_path):
    blob = build_texel_container(nparts=1)
    b = _identity_build(blob, tmp_path)
    gates = RP._orthogonality(b, set())
    assert len(gates) == 1 and gates[0].ok
    assert "UNPROVEN" in gates[0].detail and "SKIPPED" in gates[0].detail


def test_repaints_orthogonality_gate_FAILS_on_a_sibling_it_was_told_about_but_cannot_find(tmp_path):
    blob = build_texel_container(nparts=1)
    b = _identity_build(blob, tmp_path)
    b.orth_specs = {"reskin": "no_such.toml"}
    g = RP._orthogonality(b, set())[0]
    assert not g.ok and "NAMED it" in g.detail


def test_the_reskin_lane_registers_a_repaint_rebuilder_and_grows_a_gate_only_when_named(tmp_path,
                                                                                        monkeypatch):
    """THE SEAM.  ``reskin.py`` gains the registration and nothing else: a spec that names no repaint
    sibling still emits exactly the two W2/W3 gates the study record cites by position.

    ``reskin``'s registry keeps its shipped ``(path, mine)`` signature -- a study that registered its
    own retime rebuilder against it must keep working -- so the sibling rebuild reads the install
    exactly the way ``_rebuild_rescore`` already does, and the install read is what is stubbed here.
    """
    assert "repaint" in RS.ORTH_REBUILDERS and "retime" not in RS.ORTH_REBUILDERS
    blob = build_texel_container(nparts=1)
    monkeypatch.setattr(RS.R, "read_stock_effect", lambda ef, game=None: (blob, "(synthetic)"))
    spec = {"reskin": {"effect": 999, "expect_sha256": hashlib.sha256(blob).hexdigest(),
                       "target": [{"name": "creature.part0", "hue_rotate": 10.0}]}}
    b = RS.build(spec, str(tmp_path / "x_reskin.toml"), blob=blob)
    assert len(RS._orthogonality(b, set())) == 2

    # ...and a NAMED repaint sibling turns into a real intersection proof.  The sibling's effect id
    # is read from its `[reskin]` table -- a repaint spec IS a `[reskin]` spec.
    src = _write_png(tmp_path, blob, "tex.part0", _page_bytes(blob, "tex.part0"))
    sib = tmp_path / "sib_texel.toml"
    sib.write_text("\n".join([
        "[reskin]", "effect = 999", 'expect_sha256 = "%s"' % hashlib.sha256(blob).hexdigest(),
        "[[reskin.texel]]", 'name = "tex.part0"', 'source = "%s"' % src.as_posix()]) + "\n",
        encoding="utf-8")
    spec["reskin"]["orthogonality"] = {"repaint": "sib_texel.toml"}
    b = RS.build(spec, str(tmp_path / "x_reskin.toml"), blob=blob)
    assert b.orth_extra == {"repaint": "sib_texel.toml"}
    gates = RS._orthogonality(b, set(range(len(blob))))
    assert len(gates) == 3
    g = [x for x in gates if "repaint" in x.name][0]
    assert g.ok and "W6 changes 0 TEXEL bytes" in g.detail


# ============================================================ (7) the CLI ladder, offline
def _parse(argv):
    return cli.build_parser().parse_args(argv)


def _run(argv, capsys):
    rc = cli.main(argv)
    return rc, capsys.readouterr()


def test_export_art_is_registered_on_the_reskin_lane_and_only_there():
    a = _parse(["summon-reskin", "export-art", "--ef", "227"])
    assert a.action == "export-art" and a.art_lane == "indexed" and callable(a.func)
    with pytest.raises(SystemExit):
        _parse(["summon-rescore", "export-art", "--ef", "227"])
    with pytest.raises(SystemExit):
        _parse(["summon-reskin", "read", "--ef", "227"])


def test_the_cli_art_lane_choices_are_pinned_to_the_modules_own_tuple():
    """The parser is built before any summon module is imported, so the ``choices=`` list is stated
    literally -- and a literal that drifted would refuse a lane that works or offer one that does
    not."""
    assert tuple(cli._SUMMON_ART_LANES) == RP.ART_LANES


def test_export_art_without_ef_is_a_refusal_exit_2(capsys):
    rc, cap = _run(["summon-reskin", "export-art"], capsys)
    assert rc == 2 and "needs --ef" in cap.err


def test_the_cli_export_art_rgba_lane_refuses_exit_2(tmp_path, capsys):
    blob = build_texel_container(nparts=1)
    ef = tmp_path / "ef999.bytes"
    ef.write_bytes(blob)
    rc, cap = _run(["summon-reskin", "export-art", "--ef", "999", "--from", str(ef),
                    "--out", str(tmp_path / "art"), "--art-lane", "rgba"], capsys)
    assert rc == 2 and RP.W6B_REASON in cap.err


def test_the_whole_texel_ladder_runs_offline_through_from(tmp_path, capsys):
    """export-art -> paint -> plan -> build -> verify -> revert, with no install anywhere: the same
    gate stack runs on caller-supplied bytes, because a law that held on only one of two entry paths
    would not be one."""
    blob = build_texel_container(nparts=2)
    ef = tmp_path / "ef999.bytes"
    ef.write_bytes(blob)
    art = tmp_path / "art"
    rc, cap = _run(["summon-reskin", "export-art", "--ef", "999", "--from", str(ef),
                    "--out", str(art)], capsys)
    assert rc == 0, cap.out + cap.err
    assert "6 page" not in cap.out and "2 page(s) exported" in cap.out

    # paint: a hard-edged bar inside the sampled island, in INDEX space
    page = RP.texel_page(blob, "tex.part0")
    px = bytearray(RP.read_indexed_png(art / "tex.part0.png", page.w, page.h, page.clut_entries))
    for x in range(40, 60):
        px[50 * 128 + x] = 200
    RP.write_indexed_png(bytes(px), RP.palette_words(blob, page), page.w, page.h,
                         art / "tex.part0.png")

    spec = tmp_path / "ef999_reskin.toml"
    spec.write_text("\n".join([
        "[reskin]", "effect = 999", 'label = "texelcli"',
        'expect_sha256 = "%s"' % hashlib.sha256(blob).hexdigest(),
        "[[reskin.texel]]", 'name = "tex.part0"',
        'source = "%s"' % (art / "tex.part0.png").as_posix(),
        "expect_page_offset = %#08x" % page.page_offset,
        "expect_page_bytes  = %d" % page.page_bytes,
        "expect_page_wh     = [128, 128]"]) + "\n", encoding="utf-8")

    stage = tmp_path / "stage"
    rc, cap = _run(["summon-reskin", "plan", str(spec), "--from", str(ef)], capsys)
    assert rc == 0, cap.out + cap.err
    assert "TEXEL REPAINT -- lever #2" in cap.out and "plan only -- nothing written" in cap.out

    rc, cap = _run(["summon-reskin", "build", str(spec), "--from", str(ef), "--out", str(stage),
                    "--no-previews"], capsys)
    assert rc == 0, cap.out + cap.err
    man = json.loads((stage / "build_manifest.json").read_text(encoding="utf-8"))
    assert man["changed_bytes"] > 0 and man["lane"] == "texel/indexed"
    dest = Path(man["container"])
    assert dest.is_file() and dest.suffix == ""

    rc, cap = _run(["summon-reskin", "verify", str(spec), "--from", str(ef), "--out", str(stage)],
                   capsys)
    assert rc == 0 and "VERIFY: PASS" in cap.out

    # a texel spec's revert resolves the REPAINT staging root, not the reskin one
    rc, cap = _run(["summon-reskin", "deploy", str(spec), "--from", str(ef), "--out", str(stage),
                    "--dry-run", "--no-previews"], capsys)
    assert rc == 0, cap.out + cap.err
    mirror = stage / "dry-run-mod" / "FF9_Data" / "SpecialEffects" / "ef999"
    assert mirror.is_file()
    rc, cap = _run(["summon-reskin", "revert", str(spec), "--out", str(stage)], capsys)
    assert rc == 0, cap.out + cap.err
    assert not mirror.exists()


def test_a_refused_texel_build_exits_2_and_a_failed_gate_exits_1(tmp_path, capsys, monkeypatch):
    blob = build_texel_container(nparts=1)
    ef = tmp_path / "ef999.bytes"
    ef.write_bytes(blob)
    art = tmp_path / "art"
    assert _run(["summon-reskin", "export-art", "--ef", "999", "--from", str(ef),
                 "--out", str(art)], capsys)[0] == 0
    spec = tmp_path / "ef999_reskin.toml"
    spec.write_text("\n".join([
        "[reskin]", "effect = 999",
        'expect_sha256 = "%s"' % hashlib.sha256(blob).hexdigest(),
        "[[reskin.texel]]", 'name = "tex.part0"',
        'source = "%s"' % (art / "tex.part0.png").as_posix(),
        "expect_page_offset = 0x1234"]) + "\n", encoding="utf-8")
    rc, cap = _run(["summon-reskin", "plan", str(spec), "--from", str(ef)], capsys)
    assert rc == 2 and "REFUSED (RepaintError)" in cap.err and "the spec guards" in cap.err

    # a build whose SELF-CHECK fails (not a refusal) is exit 1 and stages nothing
    spec.write_text(spec.read_text(encoding="utf-8").replace("expect_page_offset = 0x1234", ""),
                    encoding="utf-8")

    def _break(b):
        chk = _real(b)
        chk.rules.append(RP.Gate(False, "an injected failing gate", "for the exit-code contract"))
        return chk

    _real = RP.self_check
    monkeypatch.setattr(RP, "self_check", _break)
    stage = tmp_path / "stage2"
    rc, cap = _run(["summon-reskin", "build", str(spec), "--from", str(ef), "--out", str(stage),
                    "--no-previews"], capsys)
    assert rc == 1 and "REFUSING TO STAGE" in cap.err
    assert not (stage / "build_manifest.json").exists()


def test_a_spec_with_both_levers_builds_ONE_composed_container_through_the_cli(tmp_path, capsys):
    blob = build_texel_container(nparts=2)
    ef = tmp_path / "ef999.bytes"
    ef.write_bytes(blob)
    art = tmp_path / "art"
    assert _run(["summon-reskin", "export-art", "--ef", "999", "--from", str(ef),
                 "--out", str(art)], capsys)[0] == 0
    page = RP.texel_page(blob, "tex.part0")
    px = bytearray(RP.read_indexed_png(art / "tex.part0.png", page.w, page.h, page.clut_entries))
    for x in range(40, 60):
        px[50 * 128 + x] = 200
    RP.write_indexed_png(bytes(px), RP.palette_words(blob, page), page.w, page.h,
                         art / "tex.part0.png")
    spec = tmp_path / "ef999_reskin.toml"
    spec.write_text("\n".join([
        "[reskin]", "effect = 999", 'label = "both-levers"',
        'expect_sha256 = "%s"' % hashlib.sha256(blob).hexdigest(),
        "[[reskin.target]]", 'name = "creature.part0"', "hue_rotate = 40.0",
        "[[reskin.texel]]", 'name = "tex.part0"',
        'source = "%s"' % (art / "tex.part0.png").as_posix()]) + "\n", encoding="utf-8")
    stage = tmp_path / "stage"
    rc, cap = _run(["summon-reskin", "build", str(spec), "--from", str(ef), "--out", str(stage),
                    "--no-previews"], capsys)
    assert rc == 0, cap.out + cap.err
    assert "COMPOSING" in cap.out and "THE COMPOSED HALVES ARE DISJOINT" in cap.out
    man = json.loads((stage / "build_manifest.json").read_text(encoding="utf-8"))
    assert man["composed"] and man["composed_base_bytes"] > 0
    staged = Path(man["container"]).read_bytes()
    # exactly ONE container was written -- the CLUT lane never staged a second file
    assert len(list((stage / "mod").rglob("ef999"))) == 1
    assert hashlib.sha256(staged).hexdigest() == man["patched_sha256"]
    mp = KC.creature_package(blob)
    moved = [i for i in range(len(blob)) if blob[i] != staged[i]]
    assert any(i >= mp.tex_file_offset + mp.tex_bytes for i in moved), "the CLUT half landed"
    assert any(mp.tex_file_offset <= i < mp.tex_file_offset + mp.tex_bytes for i in moved), \
        "the texel half landed"


# ============================================================ (8) corpus / install-gated
@needs_corpus
def test_the_indexed_round_trip_is_byte_identical_on_every_page_of_the_real_corpus():
    """THE LANE'S ACCEPTANCE GATE, on real bytes: 93 creature pages across 24 packages, decoded to a
    P-mode PNG and re-read as the same indices.  This is the measurement that makes the indexed lane
    the format of record and the RGBA lane W6b -- an identity RGBA round trip already moves 1,844 of
    16,384 texels on ef251 part 0.  Nothing is committed: the PNGs are encoded in memory."""
    npkg = npage = ok = 0
    fails = []
    for p in sorted(CORPUS.glob("ef*.bytes")):
        blob = p.read_bytes()
        pages = RP.creature_texel_pages(blob)
        if not pages:
            continue
        npkg += 1
        for pg in pages:
            npage += 1
            words = RP.palette_words(blob, pg)
            px = blob[pg.page_offset:pg.page_offset + pg.page_bytes]
            back = RP._read_indices(io.BytesIO(RP.encode_indexed_png(px, words, pg.w, pg.h)),
                                    "rt", pg.w, pg.h, len(words))
            if back == px:
                ok += 1
            else:
                fails.append((p.stem, pg.name))
    assert (npkg, npage) == (24, 93), "the corpus's own creature census moved"
    assert ok == 93 and not fails


@needs_corpus
def test_no_creature_page_in_the_corpus_collides_with_another_writer():
    """THE CO-TRANSFORM LAW, measured rather than assumed: the whole multi-writer page census is 34
    cells in 5 containers and every one of them is SCENERY, so the creature band is clean -- 0 VRAM
    cell collisions and 0 file-span collisions over 24 packages / 93 pages."""
    npart = 0
    for p in sorted(CORPUS.glob("ef*.bytes")):
        blob = p.read_bytes()
        for page in RP.creature_texel_pages(blob):
            npart += 1
            RP._gate_collisions(blob, page)                 # raises on a hit
            assert RP.CREATURE_VRAM_X[0] <= page.vram[0] < RP.CREATURE_VRAM_X[1]
    assert npart == 93


@needs_install
def test_export_art_on_ef227_runs_end_to_end_against_the_real_install(tmp_path, capsys):
    """The whole read -> decode -> PNG -> overlay -> manifest -> scaffold path on the install's own
    bytes.  The art lands in pytest's tmp dir, which is local-only by construction."""
    rc, cap = _run(["summon-reskin", "export-art", "--ef", "227", "--out", str(tmp_path)], capsys)
    assert rc == 0, cap.out + cap.err
    man = json.loads((tmp_path / RP.ART_MANIFEST).read_text(encoding="utf-8"))
    assert man["effect"] == 227 and len(man["parts"]) == 6
    assert man["stock_sha256"] == RS.R.EXPECTED_STOCK_SHA[227]
    # the measured coverage census, reproduced through the kit: 65,267 of 98,304 sampled (66.4%)
    assert sum(e["covered_texels"] for e in man["parts"]) == 65267
    assert [e["interior_holes"] for e in man["parts"]] == [0, 0, 62, 0, 12, 33]
    blob, _src = RS.R.read_stock_effect(227, None)
    for pg in RP.creature_texel_pages(blob):
        back = RP.read_indexed_png(tmp_path / ("%s.png" % pg.name), pg.w, pg.h, pg.clut_entries)
        assert back == blob[pg.page_offset:pg.page_offset + pg.page_bytes]
        assert (tmp_path / ("%s.coverage.png" % pg.name)).is_file()


#: the CLUT lane's three cast-proven artifacts, as HASHES.  Re-pinned HERE as well as in
#: ``test_summon_reskin.py`` because the texel lane composes onto the first of them: if this rung
#: moved a byte of the CLUT lane, the composed base would silently stop being the container the owner
#: already judged in game, and the composed cast would be testing two changes at once.
CLUT_PINS = {
    227: "7fef205ffbe547545374de9d1017613448777f0251d9d425b55f7796f688b89a",
    211: "4daab8ade69315e6452a96e5af1092c1bb943e1cec78968f3d9dc20e4d276790",
    251: "78b395f89e6114f0639e4463819460eafe9952b4707769ca6ea5b92d474a373b",
}


@needs_install
@needs_study_specs
@pytest.mark.parametrize("name,effect", [("bahamut_reskin.toml", 227),
                                         ("phoenix_reskin.toml", 211),
                                         ("madeen_reskin.toml", 251)])
def test_the_clut_lane_still_rebuilds_its_cast_proven_bytes_after_this_rung(name, effect):
    spec = _STUDY / name
    b = RS.build(RS.load_spec(spec), str(spec))
    b.check = RS.self_check(b)
    assert b.check.ok, [g.name for g in b.check.gates if not g.ok]
    assert b.sha_out == CLUT_PINS[effect]


def _emblem(blob: bytes, part: int, art_png: Path) -> tuple:
    """A procedural brand in INDEX space, confined to the sampled island BY CONSTRUCTION.

    The mask is the placement constraint, so the edit is provably on live geometry and provably
    preserves the silhouette -- which is why it can carry the cutout law's zero.
    """
    page = RP.texel_page(blob, "tex.part%d" % part)
    words = RP.palette_words(blob, page)
    px = RP.read_indexed_png(art_png, page.w, page.h, len(words))
    cov = RP.coverage(blob, part)
    mask = cov.mask
    zeros = set(RP.transparent_indices(words))

    def lum(w):
        r, g, b, _a = KT.bgr555_rgba(w)
        return 0.299 * r + 0.587 * g + 0.114 * b

    live = {px[i] for i in range(len(mask)) if mask[i]} - zeros
    ink, edge = max(live, key=lambda i: lum(words[i])), min(live, key=lambda i: lum(words[i]))
    xs = [i % 128 for i in range(len(mask)) if mask[i]]
    ys = [i // 128 for i in range(len(mask)) if mask[i]]
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    R = 0
    for r in range(4, 60):
        pts = [(int(cy + r * math.sin(a / 40 * math.pi)), int(cx + r * math.cos(a / 40 * math.pi)))
               for a in range(80)]
        if all(mask[y * 128 + x] for y, x in pts if 0 <= y < 128 and 0 <= x < 128):
            R = r
        else:
            break
    out = bytearray(px)
    n = 0
    for y in range(128):
        for x in range(128):
            if not mask[y * 128 + x]:
                continue
            d = math.hypot(x - cx, y - cy)
            th = math.atan2(y - cy, x - cx)
            ring = abs(d - R * 0.80) <= 2.2
            bar = d <= R * 0.80 and abs(((th * 3 / math.pi) % 2) - 1) > 0.90
            rim = abs(d - R * 0.80) <= 3.6 and not ring
            if ring or bar:
                out[y * 128 + x] = ink
                n += 1
            elif rim:
                out[y * 128 + x] = edge
                n += 1
    RP.write_indexed_png(bytes(out), words, page.w, page.h, art_png)
    # STAMPED is not MOVED: a stamped texel that already carried the ink index moves no byte, and
    # the build's own accounting counts bytes.  Returning both keeps the assertion honest.
    moved = sum(1 for i in range(len(px)) if out[i] != px[i])
    return page, n, moved, R


@needs_install
@needs_study_specs
def test_the_emblem_class_composition_smoke_on_ef227(tmp_path, capsys):
    """THE PROOF, offline: the W4 spectral-mist reskin REBUILT and a procedural brand on part 0's
    wing membrane composed on top -- one container, one ledger, one revert.  The cast's single delta
    is the brand, because the CLUT half is the baseline the owner has already judged in game."""
    blob, src = RS.R.read_stock_effect(227, None)
    art = tmp_path / "art"
    RP.export_art(blob, 227, art, source=src)
    page, stamped, moved, radius = _emblem(blob, 0, art / "tex.part0.png")
    assert stamped > 500 and radius >= 20

    spec = tmp_path / "bahamut_emblem.toml"
    spec.write_text("\n".join([
        "[reskin]", "effect = 227", 'label = "bahamut-w6a-emblem"',
        'expect_sha256 = "%s"' % RS.R.EXPECTED_STOCK_SHA[227],
        "[reskin.orthogonality]",
        'reskin  = "%s"' % (_STUDY / "bahamut_reskin.toml").as_posix(),
        'rescore = "%s"' % (_STUDY / "bahamut_rescore.toml").as_posix(),
        "compose = true",
        "[[reskin.texel]]", 'name = "tex.part0"',
        'source = "%s"' % (art / "tex.part0.png").as_posix(),
        "expect_page_offset = %#08x" % page.page_offset,
        "expect_page_bytes  = %d" % page.page_bytes,
        "expect_page_wh     = [128, 128]",
        'palette_from = "creature.part0"']) + "\n", encoding="utf-8")

    b = RP.build(RP.load_spec(spec), str(spec))
    b.check = RP.self_check(b)
    assert b.check.ok, [g.detail for g in b.check.gates if not g.ok]
    assert b.composed and b.sha_in == CLUT_PINS[227], "the composed base IS the cast-proven reskin"
    assert len(b.base_changed) == 4832
    t = b.targets[0]
    assert (t.cutout_punch, t.cutout_fill, t.dead_changed) == (0, 0, 0), \
        "the coverage mask is the placement constraint: no silhouette change, no inert paint"
    assert len(b.check.changed) == moved
    assert set(b.base_changed) & set(b.check.changed) == set()
    # the whole delta vs STOCK is the union of the two lanes and nothing else
    assert {i for i in range(len(blob)) if blob[i] != b.patched[i]} \
        == set(b.base_changed) | set(b.check.changed)
    man = RP.stage(b, root=tmp_path / "stage", previews=True)
    assert man["patched_sha256"] == b.sha_out
    assert RP.verify(b, root=tmp_path / "stage")["ok"]
    print("COMPOSED ef227 sha256 %s (%d CLUT + %d texel bytes)"
          % (b.sha_out, len(b.base_changed), len(b.check.changed)))
