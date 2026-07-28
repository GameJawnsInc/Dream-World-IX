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
from tests.test_summon_reskin import (ID9_INFO, _assemble, _assemble_i, _build_scenery_id0, _words,
                                      synth_clut16, synth_clut256, build_synth_container,
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
    """THE OUT-OF-SCOPE REFUSAL, and A MOVED PIN.  A ``page.*`` name must not resolve to nothing
    quietly -- a build that silently matched no page would report success having spliced nothing.
    W6b-1 keeps the refusal (an ``h = 256`` rect is still not an addressable unit) and adds the two
    cell names it splits into, and the SUCCESSOR reason string: the old wording named co-transform,
    u-spill and 15bpp as scope, and all three now have shipped mechanisms."""
    blob = build_texel_container(nparts=2)
    with pytest.raises(RP.RepaintError) as e:
        RP.texel_page(blob, "page.s0.x576_y256.h256")
    msg = str(e.value)
    assert RP.W6B_REASON in msg
    assert "cell.s0.x576_y256" in msg and "cell.s0.x576_y384" in msg
    assert "DEPTH-UNKNOWN" in msg and "SAME-BYTES-TWO-DEPTHS" in msg
    assert "co-transform" not in msg and "u-spill" not in msg, \
        "three of the old string's four clauses are shipped remedies now, not excuses"


def test_a_creatureless_container_exposes_no_texel_surface_and_says_why():
    """AN INVERTED PIN.  A creature-less container used to expose NOTHING -- and 348 of the corpus's
    372 are creature-less, so that was the whole surface for most of it.  W6b-1 inverts the verdict
    for any of them that declares a readable scenery cell, and KEEPS the refusal, with its own reason,
    for the ones that do not."""
    blob = build_synth_creatureless_container()
    assert RP.creature_texel_pages(blob) == []
    assert RP.W6B_REASON in RP.creature_refusal(blob)
    with pytest.raises(RP.RepaintError, match="no id-4"):
        RP.export_art(blob, 999, None)
    # ...and the inversion: a creature-less container WITH a lawful scenery cell now exposes one
    scen = build_scenery_container()
    assert RP.creature_texel_pages(scen) == [] and RP.W6B_REASON in RP.creature_refusal(scen)
    assert [p.name for p in RP.scenery_texel_pages(scen, 999)]
    assert RP.texel_page(scen, "cell.s0.x704_y256", 999).kind == "scenery"


def test_other_page_writers_splits_an_h256_rect_into_its_two_stacked_cells():
    """A STRENGTHENED PIN.  Collapsing an ``h == 256`` rect into one entry would make the LOWER VRAM
    cell unaddressable, and a cell nothing can address is a cell the collision gate cannot see.  W6b-1
    consumes ``reskin.page_cells``, so the pin is no longer "the split happened somewhere" -- it is
    that BOTH HALVES are named, at file offsets exactly 0x4000 apart."""
    blob = build_texel_container(nparts=1, collide=(192, 384))
    cells = RP.other_page_writers(blob)
    assert (192, 384) in cells
    tall = build_texel_container(nparts=1, collide=(576, 256))
    # the fixture's rect is h=128, so exactly one cell; the SPLIT law is exercised by h=256 rects,
    # which the scenery fixture supplies -- and the pin below is that both halves get a NAME.
    assert len(RP.other_page_writers(tall)) == 1
    scen = build_scenery_container()                      # SCEN_RECTS[0] is (704, 256, 64, 256)
    ws = RP.other_page_writers(scen)
    assert (704, 256) in ws and (704, 384) in ws
    assert ws[(704, 384)][0][1] - ws[(704, 256)][0][1] == RS.PAGE_CELL_BYTES
    assert sorted(pc.name for pc in RS.page_cells(scen).values() if pc.x == 704) == [
        "cell.s0.x704_y256", "cell.s0.x704_y384"]


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
    # the THIRD indexed-lane RGBA site, and the same one-symbol move as the two export pins: this
    # refusal is about EXACT RECOVERY, so it quotes the reason that is about exact recovery.
    assert "not \"P\"" in str(e.value) and RP.INDEXED_RGBA_REASON in str(e.value)


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
    # UNCHANGED BY W6b-1, and the one symbol that moved says why: the refusal quotes
    # INDEXED_RGBA_REASON, not W6B_REASON.  The first is about EXACT RECOVERY on the indexed lane and
    # would still hold if every cell in the corpus were lawful; the second is about which SCENERY
    # cells remain out of scope.  They were one string only because there was only one string, and
    # splitting them is what stops a scope change from quietly rewriting an identity argument.
    assert RP.INDEXED_RGBA_REASON in str(e.value) and "93/93" in str(e.value)
    assert "1,844" in str(e.value) and "8.31%" in str(e.value), "the measurement is verbatim"


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
    assert rc == 2 and RP.INDEXED_RGBA_REASON in cap.err


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


# ============================================================ (9) W6b-1: THE SCENERY TEXEL SURFACE
# The addressable unit here is the VRAM PAGE-CELL, not the id-4 part: 64 halfwords x 128 lines =
# 0x4000 bytes, read as 256 / 128 / 64 texels wide at 4 / 8 / 15 bpp.  The fixture below is ef211's
# shape generalised -- a TALL rect whose lower half only `page_cells` can name, a class-C cell read in
# two palettes, a 15bpp direct cell, a cell nothing reads (depth-unknown), and a model whose picture
# spills across a column boundary into a cell it does not own.
#
# PROVENANCE: every palette word and every texel word below is COMPUTED.  The corpus-gated pins at the
# end compare COUNTS derived from the user's own ef###.bytes; no stock byte enters this file.

#: the page rects the scenery fixture declares, and what each cell is FOR.
SCEN_RECTS = ((704, 256, 64, 256),      # the tall rect: (704,256) lawful 8bpp + (704,384) LOWER HALF
              (576, 256, 64, 128),      # class C: two 4bpp readers, two different CLUT cells
              (512, 256, 64, 128),      # 15bpp DIRECT
              (448, 256, 64, 128),      # nothing reads it -> DEPTH-UNKNOWN, refused by name
              (384, 256, 64, 128),      # SPILL-IN: a model whose own column is 320 reads here
              (320, 256, 64, 128))      # SPILL-OUT: that model's own column

#: the CLUT cells the fixture's id-0 declares -- three 16-entry rows and one 256-entry row.
SCEN_CLUT4 = ((0, 244), (16, 244), (32, 244))
SCEN_CLUT8 = ((0, 245),)


def _clut_word(x: int, y: int) -> int:
    """``(x entries, y line)`` -> the PSX CLUT word, inverting ``reskin.clut_word_xy`` rather than
    typing a magic constant -- so a fixture cell and the derivation can never disagree."""
    assert x % 16 == 0 and 0 <= x // 16 < 64
    w = (y << 6) | (x // 16)
    assert RS.clut_word_xy(w) == (x, y)
    return w


def _tpage(x: int, y: int, bpp: int) -> int:
    """``(vram x halfwords, vram y lines, bpp)`` -> the PSX TPAGE word.  Derived through the SAME
    expression ``reskin.attribution`` decodes with, and asserted round-trip, so a hand-typed tpage can
    never quietly bind a different column."""
    tp = ({4: 0, 8: 1, 15: 2}[bpp] << 7) | ((y // 256) << 4) | (x // 64)
    assert ((tp & 0x0F) * 64, ((tp >> 4) & 1) * 256) == (x, y)
    assert RS.SO_BPP[(tp >> 7) & 3] == bpp
    return tp


def _pal16(k: int):
    """16 COMPUTED words, ROTATED by ``k`` -- so the class-C alternate views of one index array are
    visibly different pictures and a test can tell one key from the other."""
    base = synth_clut16()
    return [base[0]] + [base[1 + ((i - 1 + k) % 15)] for i in range(1, 16)]


def _cell_fill(n: int) -> bytes:
    """One cell's 0x4000 COMPUTED bytes, distinct per cell and meaningful at every depth.

    Written as halfwords so one generator serves all three codecs: at 15bpp the words carry both
    STP-set and STP-clear texels, at 8bpp every byte is a valid 256-entry index, at 4bpp every nibble
    is a valid 16-entry index -- and one word in every 137 is forced to ``0x0000`` so the CUTOUT law
    has real holes to punch and fill instead of a generator that happened to avoid them.
    """
    b = bytearray(RS.PAGE_CELL_BYTES)
    for i in range(RS.PAGE_CELL_BYTES // 2):
        struct.pack_into("<H", b, 2 * i, 0 if i % 137 == 0 else ((i * 7 + n * 13) & 0xFFFF))
    return bytes(b)


def _scenery_id0(rects=SCEN_RECTS, clut4=SCEN_CLUT4, clut8=SCEN_CLUT8) -> bytes:
    """An id-0 payload declaring ``rects`` page rects over an inline CLUT rect of rows 244-245.

    Laid out exactly as ``reskin.id0_palettes`` decodes it -- the inline stream ends at precisely
    ``P + pixelDataRel``, which is the derivation's own self-check -- and the ``clutWord`` table lists
    the 16-entry palettes FIRST, because ``nClut4`` is what says where that boundary is.
    """
    words = [_clut_word(*c) for c in clut4] + [_clut_word(*c) for c in clut8]
    page_rel = 0x10 + 2 * len(words)
    page_rel += page_rel % 4
    inline_rel = page_rel + 8 + 8 * len(rects)
    inline_data = inline_rel + 8
    pix_rel = inline_data + 2 * 256 * 2                      # w=256 entries, h=2 rows
    buf = bytearray(pix_rel)
    struct.pack_into("<iii", buf, 0x00, page_rel, inline_rel, 1)
    struct.pack_into("<HH", buf, 0x0C, len(clut4), len(clut8))
    for i, w in enumerate(words):
        struct.pack_into("<H", buf, 0x10 + 2 * i, w)
    struct.pack_into("<ii", buf, page_rel, pix_rel, len(rects))
    for k, (x, y, w, h) in enumerate(rects):
        struct.pack_into("<HHHH", buf, page_rel + 8 + 8 * k, x, y, w, h)
    struct.pack_into("<HHHH", buf, inline_rel, 0, 244, 256, 2)
    row244 = bytearray(512)
    for i, (cx, _cy) in enumerate(clut4):
        row244[2 * cx:2 * cx + 32] = _words(_pal16(i))
    buf[inline_data:inline_data + 512] = row244
    buf[inline_data + 512:inline_data + 1024] = _words(synth_clut256(seed=3))
    stream = bytearray()
    n = 0
    for (_x, _y, w, h) in rects:
        for _j in range(max(1, h // RS.PAGE_CELL_LINES)):
            stream += _cell_fill(n)
            n += 1
    return bytes(buf) + bytes(stream)


def _uv_geom(tpage: int, clut: int, uv) -> bytes:
    """One 16-byte ``so`` record + a GEOM block carrying ONE FT4 quad over the uv rect ``uv``.

    ``test_summon_reskin._so_geom`` builds an ``so``-bound GEOM with EMPTY pools, which is all a
    palette-attribution test needs -- but the scenery texel lane joins on UV COVER, so a model with no
    UVs samples nothing and every cell would read as depth-unknown.  This is that fixture plus the one
    thing this lane cannot do without.
    """
    u0, v0, u1, v1 = uv
    nf, nv = 1, 4
    p_vpb = 0x40
    p_pos = _a4(p_vpb + 2 * 1)
    p_prim = _a4(p_pos + 8 * nv)
    p_uv = _a4(p_prim + nf * FT4_STRIDE)
    p_col = _a4(p_uv + 2 * 4 * nf)
    g = bytearray(p_col)
    g[0:4] = bytes([0x00, 0x00, 1, 1])
    struct.pack_into("<II", g, 0x04, 0, 0)
    struct.pack_into("<I", g, 0x0C, 0x14)                     # pBoneTable -- the scanner's needle
    struct.pack_into("<I", g, 0x10, 0x18)                     # pMeshTable == 0x18 + (1-1)*4
    struct.pack_into("<I", g, 0x14, 0)
    d = 0x18
    struct.pack_into("<H", g, d + 0x02, nf)                   # FT4 count
    struct.pack_into("<IIIII", g, d + 0x14, p_vpb, p_pos, p_prim, p_uv, p_col)
    struct.pack_into("<H", g, p_vpb, nv)
    for k in range(4):
        struct.pack_into("<H", g, p_prim + 2 * k, k)
        struct.pack_into("<H", g, p_prim + 0x08 + 2 * k, k)
    for k, (u, v) in enumerate(((u0, v0), (u1, v0), (u1, v1), (u0, v1))):
        struct.pack_into("<H", g, p_uv + 2 * k, u | (v << 8))
    so = struct.pack("<HHHH", 0x6F73, 1, 0x10, 0x0C) + struct.pack("<HHHH", tpage, clut, 0, 0)
    return so + bytes(g)


#: the fixture's models, each named for the hazard it exists to produce.
#: ``(label, vram x, vram y, bpp, clut cell, uv rect)``
SCEN_MODELS = (
    ("fire",   704, 256, 8,  (0, 245),  (0, 0, 100, 60)),     # the lawful single-reader cell
    ("low",    704, 256, 8,  (0, 245),  (0, 130, 100, 190)),  # the LOWER HALF of the tall rect
    ("palA",   576, 256, 4,  (0, 244),  (0, 0, 200, 60)),     # class C, key 1
    ("palB",   576, 256, 4,  (16, 244), (0, 0, 200, 60)),     # class C, key 2 -- same index bytes
    ("direct", 512, 256, 15, None,      (0, 0, 60, 60)),      # 15bpp DIRECT: no palette at all
    ("spill",  320, 256, 8,  (0, 245),  (0, 0, 255, 60)),     # u 255 at 8bpp == halfword 127: 2 cols
)


def build_scenery_container(rects=SCEN_RECTS, models=SCEN_MODELS, id9: int = 0,
                            clut4=SCEN_CLUT4) -> bytes:
    """The scenery fixture: a creature-less container with real page rects and real UV-bound models.

    ``id9`` enables the id-9 alternate slot that lands on VRAM ``(320, 256)`` -- the same cell rect 5
    writes -- which is the CO-TRANSFORM shape (two writers, one cell) in miniature.
    """
    res = [(0, 0, _scenery_id0(rects, clut4)), (3, 0, bytes([0x55]) * SECTOR)]
    body = b"".join(_uv_geom(_tpage(x, y, bpp), 0 if cl is None else _clut_word(*cl), uv)
                    for _lbl, x, y, bpp, cl, uv in models)
    if body:
        res.append((6, 0, body))
    for i in range(int(id9)):
        res.append((9, ID9_INFO, bytes([0x77 + i]) * RS.PAGE_CELL_BYTES))
    return _assemble_i([(0, res)])


def _cell(blob, x, y, tag="s0", effect=999):
    """Resolve one fixture cell.  ``effect`` defaults to a CLEAN id, so the hazard assertions below
    read the container's own hazards and not the program-VRAM lists' verdict on a made-up id."""
    return RP.texel_page(blob, "cell.%s.x%d_y%d" % (tag, x, y), effect)


def test_the_scenery_fixture_is_well_formed_and_its_models_really_bind():
    """Sanity-checks the FIXTURE first, so a later failure cannot be a fixture bug wearing a
    derivation bug's clothes.  Both halves must hold: the container parses strict AND every model the
    fixture declares comes back out of ``bound_models`` with the depth and column it was built with --
    a GEOM whose uv pool the scanner never reached would make every cell depth-unknown and every
    assertion below vacuous."""
    blob = build_scenery_container()
    c = KC.parse_header(blob, strict=True)
    assert c.cursor_end == len(blob)
    RS.palette_map(blob)                                     # the id-0 self-check passes
    assert sorted(RS.page_cells(blob)) == [
        ("s0", 320, 256), ("s0", 384, 256), ("s0", 448, 256), ("s0", 512, 256),
        ("s0", 576, 256), ("s0", 704, 256), ("s0", 704, 384)]
    ms = RP.bound_models(blob)
    assert len(ms) == len(SCEN_MODELS)
    assert [m.bpp for m in ms] == [8, 8, 4, 4, 15, 8]
    assert all(m.faces == 1 for m in ms), "every fixture model rasterised its one quad"
    assert [m.columns for m in ms] == [(704,), (704,), (576,), (576,), (512,), (320, 384)]
    # THE U-SPILL LAW in the fixture's own arithmetic: u 255 reaches halfword 127 at 8bpp (two
    # columns) and halfword 63 at 4bpp (exactly one -- which is why 4bpp structurally cannot spill)
    assert ms[5].u == (0, 255) and ms[2].u == (0, 200)
    assert [m.spills for m in ms] == [False, False, False, False, False, True]


def test_scenery_texel_pages_emits_ONLY_cells_whose_DEPTH_the_container_states():
    """THE ATTRIBUTION LIMIT, which is the honest shape of this rung.  A cell nothing declares a
    reader for has no bit depth as a container FACT -- the same 0x4000 bytes are 256, 128 or 64 texels
    wide -- so it is refused BY NAME rather than guessed at.  Corpus-wide that is 2,385 of 2,572."""
    blob = build_scenery_container()
    pages, refused = RP.scenery_surface(blob, 999)
    assert [p.name for p in pages] == [
        "cell.s0.x320_y256", "cell.s0.x384_y256", "cell.s0.x512_y256",
        "cell.s0.x576_y256", "cell.s0.x704_y256", "cell.s0.x704_y384"]
    assert [p.bpp for p in pages] == [8, 8, 15, 4, 8, 8]
    assert [p.wh for p in pages] == [(128, 128), (128, 128), (64, 128), (256, 128),
                                     (128, 128), (128, 128)]
    # ...and the one cell nothing reads is REFUSED BY NAME, not absent
    assert [(r.name, r.klass) for r in refused] == [("cell.s0.x448_y256", "depth-unknown")]
    assert "2,385" in refused[0].reason and "54.5%" in refused[0].reason
    assert RP.scenery_texel_pages(blob, 999) == pages
    assert RP.scenery_cell_refusals(blob, 999) == refused


def test_the_same_0x4000_bytes_are_three_different_pictures_and_the_map_says_which():
    """Why ``expect_bpp`` has to exist: every cell is the same 0x4000 bytes and only the ``so`` record
    says how wide the picture is."""
    blob = build_scenery_container()
    for p in RP.scenery_texel_pages(blob, 999):
        assert p.page_bytes == RS.PAGE_CELL_BYTES == 0x4000
        assert p.w * p.h * {4: 1, 8: 2, 15: 4}[p.bpp] == 2 * p.page_bytes
        assert p.w == RP.cell_texel_w(p.bpp)
    assert (RP.cell_texel_w(4), RP.cell_texel_w(8), RP.cell_texel_w(15)) == (256, 128, 64)
    with pytest.raises(RP.RepaintError, match="states 4, 8 or 15"):
        RP.cell_texel_w(16)


def test_the_LOWER_HALF_of_a_tall_rect_is_addressable_and_the_rect_view_cannot_name_it():
    """* THE RUNG'S CENTRAL NEW MECHANISM, on the edit layer.  ``scenery_pages`` is keyed ``(tag, x)``
    and can only ever reach the TOP cell of an ``h == 256`` rect -- on ef211 that is a two-palette
    refusal sitting on top of a clean single-reader 4bpp picture.  Corpus-wide the per-cell map turns
    exactly 20 otherwise-lawful cells from unnameable into editable."""
    blob = build_scenery_container()
    top, bot = _cell(blob, 704, 256), _cell(blob, 704, 384)
    assert bot.page_offset - top.page_offset == RS.PAGE_CELL_BYTES
    assert top.hazards.lower_half is False and bot.hazards.lower_half is True
    assert blob[top.page_offset:top.page_offset + 0x4000] != \
        blob[bot.page_offset:bot.page_offset + 0x4000]
    # the RECT view names ONE key for both halves, and its offset is the TOP one's
    rects = RS.scenery_pages(blob)
    assert rects[("s0", 704)].h == 256 and rects[("s0", 704)].off == top.page_offset
    assert len([k for k in rects if k[1] == 704]) == 1


def test_the_page_RECT_spelling_still_REFUSES_and_now_names_the_two_cells_it_splits_into():
    """A MOVED PIN.  The W6a refusal of ``page.s0.x576_y256.h256`` survives W6b-1 intact -- an
    ``h = 256`` rect is not an addressable unit -- but it stops being a dead end: it now says what the
    rect splits into.  A moved pin that still fires is the cheapest possible proof the rename was
    deliberate rather than a namespace that drifted."""
    blob = build_scenery_container()
    with pytest.raises(RP.RepaintError) as e:
        RP.texel_page(blob, "page.s0.x576_y256.h256")
    msg = str(e.value)
    assert RP.W6B_REASON in msg
    assert "cell.s0.x576_y256" in msg and "cell.s0.x576_y384" in msg
    assert "NOT an addressable unit" in msg


def test_a_REFUSED_cell_answers_with_its_OWN_reason_rather_than_reading_as_unknown():
    """"Unknown name" and "known name, refused" are different facts and an author acts on them
    differently.  Collapsing the second into the first is how a measured refusal reads like a typo."""
    blob = build_scenery_container()
    with pytest.raises(RP.RepaintError) as e:
        RP.texel_page(blob, "cell.s0.x448_y256", 999)
    assert "REFUSED, not unknown" in str(e.value) and "DEPTH-UNKNOWN" in str(e.value)
    with pytest.raises(RP.RepaintError) as e:
        RP.texel_page(blob, "cell.s0.x999_y256", 999)
    assert "no texel page named" in str(e.value) and "cell.s0.x704_y256" in str(e.value)


def test_texel_page_resolves_BOTH_namespaces_off_one_container():
    """One resolver, two surfaces -- so a spec can carry a creature part and a scenery cell in the
    same table and neither has to know the other exists."""
    cb = build_texel_container(nparts=2)
    assert RP.texel_page(cb, "tex.part0").kind == "creature"
    assert RP.texel_page(cb, "tex.part0").cell is None
    assert RP.texel_page(cb, "tex.part0").hazards is None
    p = _cell(build_scenery_container(), 704, 256)
    assert (p.kind, p.cell, p.index, p.name) == ("scenery", (704, 256), -1,
                                                 "cell.s0.x704_y256")
    assert p.scenery and not p.direct and not p.depth_ambiguous


def test_other_page_writers_consumes_page_cells_and_folds_the_id9_alternates_in():
    """The duplicated ``h // 128`` split this used to carry advanced by a flat ``k * 0x4000`` -- right
    on 2,648 of 2,648 corpus records and silently catastrophic on the first that is not ``w == 64``.
    One derivation, one place the arithmetic is enforced."""
    blob = build_scenery_container(id9=1)
    ws = RP.other_page_writers(blob)
    assert (704, 256) in ws and (704, 384) in ws
    assert sorted(s for s, _o, _n in ws[(320, 256)]) == ["id9.s0 alternate block",
                                                         "s0 id-0 page rect"]
    for _cellkey, entries in ws.items():
        for _src, _off, nb in entries:
            assert nb == RS.PAGE_CELL_BYTES
    assert set(ws) == {pc.cell for pc in RS.page_cells(blob).values()}


def test_a_CO_TRANSFORM_cell_appears_once_per_WRITER_and_each_names_the_others():
    """Two writers of one VRAM cell are two DIFFERENT pictures shown at different cast phases (0 of
    the corpus's 156 writer pairs is byte-identical), so the edit unit is the WRITER and the remedy is
    art for every one of them.  One record per cell would make the second upload invisible."""
    blob = build_scenery_container(id9=1)
    a, b = _cell(blob, 320, 256, "s0"), _cell(blob, 320, 256, "id9.s0")
    assert a.page_offset != b.page_offset
    assert a.hazards.co_transform and b.hazards.co_transform
    assert {w.tag for w in a.hazards.writers} == {"s0", "id9.s0"} == {w.tag for w in b.hazards.writers}
    assert (a.hazards.writer, b.hazards.writer) == ("s0", "id9.s0")
    assert "co-transform" in a.hazards.names and "co-transform" in b.hazards.names
    # ...and with ONE writer it is not a co-transform at all
    assert not _cell(build_scenery_container(), 320, 256).hazards.co_transform


def test_a_class_C_cell_carries_EVERY_palette_and_the_display_key_is_the_LOWEST_ADDRESSED_binding():
    """One index array, N renderings.  The import already reads ONLY the indices, so this is not a
    contradiction -- it is the format -- but both keys have to be NAMED, because an author who never
    learns the second one will tune a colour they cannot see."""
    blob = build_scenery_container()
    hz = _cell(blob, 576, 256).hazards
    assert hz.multi_palette and hz.shared_read and not hz.two_depths
    assert hz.palette_cells == ((0, 244), (16, 244))
    assert [r.palette_name for r in hz.readers] == ["pal.s0.x0_y244.e16", "pal.s0.x16_y244.e16"]
    assert hz.readers[0].geom < hz.readers[1].geom, "readers are ordered by ADDRESS"
    p = _cell(blob, 576, 256)
    assert p.palette_name == hz.readers[0].palette_name
    assert p.clut_offset == hz.readers[0].palette_offset and p.clut_entries == 16


def test_SPILL_OUT_and_SPILL_IN_are_UV_exact_and_name_the_columns():
    """A picture wider than a page is the corpus norm, not an edge case: 58 of 58 spilling models are
    wider than one page, median 224 texels against 128, and 0 of 58 spill by <= 2%.  The cell the
    model does not own sees it as SPILL-IN, which is exactly why page scope is the wrong edit unit."""
    blob = build_scenery_container()
    own, foreign = _cell(blob, 320, 256), _cell(blob, 384, 256)
    assert own.hazards.spill_out == (384,) and not own.hazards.spill_in
    assert not foreign.hazards.spill_out and len(foreign.hazards.spill_in) == 1
    assert foreign.hazards.spill_in[0].geom == own.hazards.readers[0].geom
    assert foreign.hazards.readers[0].own_column is False and own.hazards.readers[0].own_column
    assert own.hazards.readers[0].columns == (320, 384) == foreign.hazards.readers[0].columns
    # 4bpp CANNOT spill -- structural, not measured: u <= 255 at 4 texels/halfword is offset <= 63
    assert _cell(blob, 576, 256).hazards.spill_out == ()


def test_a_15bpp_DIRECT_cell_indexes_no_palette_and_SAYS_so_rather_than_returning_nothing():
    blob = build_scenery_container()
    p = _cell(blob, 512, 256)
    assert p.direct and p.bpp == 15 and p.wh == (64, 128)
    assert p.clut_offset is None and p.clut_entries is None and p.palette_name == ""
    with pytest.raises(RP.RepaintError, match="indexes NO palette"):
        RP.palette_words(blob, p)


def test_the_coverage_number_is_the_halfwords_a_model_actually_SAMPLES():
    """UV-exact, per cell -- the number ef211's fire field reads 8,128 of 8,192 on, which is what
    makes it a full-screen picture rather than a corner of one."""
    blob = build_scenery_container()
    hz = _cell(blob, 704, 256).hazards
    assert 0 < hz.covered_halfwords <= RS.PAGE_CELL_W * RS.PAGE_CELL_LINES
    # the quad is u 0..100 (halfwords 0..50 at 8bpp) x v 0..60 -> 51 * 61
    assert hz.covered_halfwords == 51 * 61 == hz.readers[0].halfwords_here


def test_program_class_is_derived_from_the_CORRECTED_lists_and_UNKNOWN_is_not_CLEAN():
    """THE DIRECTION LAW is what makes the write list 15 and not 22: StoreImage is VRAM -> main RAM, a
    READ, and a read cannot clobber a repaint.  ef435 is OFF (a switch dispatch through the image's
    own pointer table, misread as HLE op 0) and ef211 -- the cast vehicle -- is a READ, which is what
    makes it reachable at all."""
    assert RP.program_class(211)[0] == "read" and "StoreImage" in RP.program_class(211)[1]
    assert RP.program_class(1)[0] == "write" and RP.program_class(38)[0] == "write"
    assert RP.program_class(227)[0] == "clean"
    assert 435 not in RP.PROGRAM_VRAM_WRITE_IDS and 435 not in RP.PROGRAM_VRAM_READ_IDS
    assert len(RP.PROGRAM_VRAM_WRITE_IDS) == 15 and len(RP.PROGRAM_VRAM_READ_IDS) == 12
    assert RP.PROGRAM_VRAM_WRITE_IDS & RP.PROGRAM_VRAM_READ_IDS == frozenset()
    # ...and silence is IGNORANCE, never safety
    assert RP.program_class(None)[0] == "unknown"
    blob = build_scenery_container()
    assert _cell(blob, 704, 256, effect=None).hazards.program == "unknown"
    assert "program-vram-unknown" in _cell(blob, 704, 256, effect=None).hazards.names
    assert _cell(blob, 704, 256).hazards.names == ()


def test_a_program_WRITE_container_refuses_every_cell_and_the_MOVEIMAGE_cell_refuses_BY_CELL():
    """0 of 18 ``RECT*`` arguments const-fold, so the ONE per-cell verdict in the corpus is
    ``MoveImage``'s destination -- a different, sharper refusal than the container-wide one.  Every
    other cell in those three containers is untouched by the program."""
    blob = build_scenery_container()
    assert RP.MOVEIMAGE_HARD_CELLS == {1: (704, 256), 142: (704, 256), 144: (704, 256)}
    ref = {r.name: r for r in RP.scenery_cell_refusals(blob, 142)}
    assert ref["cell.s0.x704_y256"].klass == "program-moveimage-cell"
    assert "ONE per-cell program verdict" in ref["cell.s0.x704_y256"].reason
    assert ref["cell.s0.x576_y256"].klass == "program-vram-write"
    assert [r.klass for r in RP.scenery_cell_refusals(blob, 227)] == ["depth-unknown"]


def test_SAME_BYTES_TWO_DEPTHS_refuses_and_carries_no_single_depth_to_guard():
    """Two index arrays over one byte block.  No PNG's edit is coherent under both, so it refuses
    EARLIER than the palette logic and with its own message -- 17 corpus cells over 6 effects."""
    blob = build_scenery_container(models=SCEN_MODELS + (("dual", 576, 256, 8, (0, 245),
                                                          (0, 0, 100, 60)),))
    pages = {p.name: p for p in RP.scenery_texel_pages(blob, 227)}
    p = pages["cell.s0.x576_y256"]
    assert p.depth_ambiguous and p.hazards.depths == (4, 8) and not p.hazards.multi_palette
    assert "same-bytes-two-depths" in p.hazards.names
    r = next(r for r in RP.scenery_cell_refusals(blob, 227) if r.name == p.name)
    assert r.klass == "same-bytes-two-depths" and "no PNG's edit is coherent under both" in r.reason
    with pytest.raises(RP.RepaintError, match="NO single depth to guard"):
        RP.assert_expect_bpp(blob, p, 4, "row 0")
    with pytest.raises(RP.RepaintError, match="REFUSED, not unknown"):
        RP.texel_page(blob, p.name, 227)


def test_expect_bpp_is_CHECKED_against_the_so_derivation_and_cross_checked_against_nClut():
    """STATED by the author, CHECKED against the container, never chosen.  A wrong depth packs to
    exactly the right byte count and paints the wrong picture -- the one class of error a
    byte-identity gate cannot see."""
    blob = build_scenery_container()
    p8, p4 = _cell(blob, 704, 256), _cell(blob, 576, 256)
    assert "MATCHES" in RP.assert_expect_bpp(blob, p8, 8, "row 0")
    assert "MATCHES" in RP.assert_expect_bpp(blob, p4, 4, "row 1")
    with pytest.raises(RP.RepaintError) as e:
        RP.assert_expect_bpp(blob, p8, 4, "row 0")
    assert "256 texels wide" in str(e.value) and "128" in str(e.value)
    assert "packs to exactly the right byte count" in str(e.value)
    with pytest.raises(RP.RepaintError, match="states 4, 8 or 15"):
        RP.assert_expect_bpp(blob, p8, 16, "row 0")
    # the SECOND, INDEPENDENT header: a chunk that declares no 16-entry palette has nothing for a
    # 4bpp index to point at, and two headers disagreeing is not a restatement of the first
    no4 = build_scenery_container(models=(SCEN_MODELS[2],), clut4=())
    q = next(p for p in RP.scenery_texel_pages(no4, 999) if p.bpp == 4)
    assert q.clut_offset is None
    with pytest.raises(RP.RepaintError, match="nClut4 == 0"):
        RP.assert_expect_bpp(no4, q, 4, "row 0")
    # ...and that same cell is refused for the reason it cannot be rendered
    assert next(r for r in RP.scenery_cell_refusals(no4, 999)
                if r.name == q.name).klass == "no-declared-clut"


def test_a_texel_row_can_GUARD_the_cell_it_names_and_a_creature_part_refuses_that_guard():
    """A guard may only ever fail CLOSED, so both new keys run at the row-resolution site rather than
    living in a docstring."""
    blob = build_scenery_container()
    p = _cell(blob, 704, 256)
    RP.build(_spec_dict(blob, [{"name": p.name, "enabled": False, "expect_cell": [704, 256],
                                "expect_bpp": 8}]), "?", blob=blob)
    with pytest.raises(RP.RepaintError, match="guards VRAM cell"):
        RP.build(_spec_dict(blob, [{"name": p.name, "enabled": False,
                                    "expect_cell": [704, 384]}]), "?", blob=blob)
    with pytest.raises(RP.RepaintError, match="the container's own `so` record derives"):
        RP.build(_spec_dict(blob, [{"name": p.name, "enabled": False,
                                    "expect_bpp": 4}]), "?", blob=blob)
    cb = build_texel_container(nparts=1)
    with pytest.raises(RP.RepaintError, match="CREATURE page"):
        RP.build(_spec_dict(cb, [{"name": "tex.part0", "enabled": False,
                                  "expect_cell": [192, 384]}]), "?", blob=cb)


# ============================================================ (10) W6b-1: THE CODECS
def test_pack4_unpack4_are_byte_identical_and_the_ORDER_is_the_measured_one():
    """``out[2i] = raw[i] & 0x0F`` -- even u in the LOW nibble.  Byte identity is BLIND to this
    question (the swapped convention round-trips just as well), so the order was settled by a
    discriminator and by the PSX rule that lower-order bits hold the lower u -- whose 8bpp instance is
    cast-proven on screen.  This pin is the ORDER, not the identity."""
    raw = bytes(range(256))
    assert RP.pack4(RP.unpack4(raw)) == raw
    assert RP.unpack4(b"\x12\xf0") == b"\x02\x01\x00\x0f"
    assert RP.pack4([0x02, 0x01, 0x00, 0x0F]) == b"\x12\xf0"
    swapped = bytes((b >> 4) | ((b & 0x0F) << 4) for b in raw)
    assert RP.pack4(RP.unpack4(swapped)) == swapped, "identity cannot discriminate -- hence the pin"


def test_pack4_REFUSES_an_index_past_the_16_entry_row_rather_than_masking_it():
    with pytest.raises(RP.RepaintError) as e:
        RP.pack4([0, 16])
    assert "outside 0..15" in str(e.value) and "masked" in str(e.value)
    with pytest.raises(RP.RepaintError, match="even number of texels"):
        RP.pack4([1, 2, 3])


def test_the_4bpp_PNG_pair_is_byte_identical_on_a_real_cell(tmp_path):
    """One byte per texel, values 0..15 -- never Pillow's ``bits=4``.  The nibble packing is ours end
    to end, so no PNG bit-order convention can reach the container."""
    blob = build_scenery_container()
    p = _cell(blob, 576, 256)
    raw = blob[p.page_offset:p.page_offset + p.page_bytes]
    words = RP.palette_words(blob, p)
    png = tmp_path / "c.png"
    RP.write_indexed4_png(raw, words, p.w, p.h, png)
    assert RP.read_indexed4_png(png, p.w, p.h, 16) == raw
    with pytest.raises(RP.RepaintError, match="packed bytes"):
        RP.write_indexed4_png(raw[:-2], words, p.w, p.h, png)


def test_the_15bpp_shift_codec_round_trips_ALL_65536_words_exhaustively():
    """Not a corpus proof -- an EXHAUSTIVE one.  Every halfword the format can hold, both directions,
    plus the two laws the sidecar design rests on."""
    assert [w for w in range(0x10000) if KT.direct15_word(*KT.direct15_split(w)) != w] == []
    assert [w for w in range(0x10000) if KT.direct15_split(w)[3] != (w >> 15)] == []
    assert KT.direct15_split(0) == (0, 0, 0, 0) and KT.direct15_split(0x8000) == (0, 0, 0, 1)
    assert KT.direct15_word(255, 255, 255, 0) == 0x7FFF, "white floors to 248, by design"
    for bad in ((256, 0, 0, 0), (0, -1, 0, 0), (0, 0, 0, 2)):
        with pytest.raises(KT.TextureError):
            KT.direct15_word(*bad)


def test_write_and_read_direct_png_round_trip_a_real_cell_through_BOTH_files(tmp_path):
    blob = build_scenery_container()
    p = _cell(blob, 512, 256)
    raw = blob[p.page_offset:p.page_offset + p.page_bytes]
    png = tmp_path / "d.png"
    _f, s = RP.write_direct_png(raw, p.w, p.h, png)
    assert Path(s) == RP.stp_sidecar_path(png) == tmp_path / "d.stp.png"
    assert RP.read_direct_png(png, p.w, p.h) == raw
    # the sidecar is LOAD-BEARING: it is authoritative and its absence REFUSES rather than defaulting
    Path(s).unlink()
    with pytest.raises(RP.RepaintError, match="no STP sidecar"):
        RP.read_direct_png(png, p.w, p.h)


def test_the_FOUR_direct15_refusals_each_name_their_own_fix(tmp_path):
    """Alpha is display-only-but-CHECKED: the import reads RGB + STP, and every way the picture can
    disagree with the bytes it would write is a refusal that names the one-line remedy.  A silent
    correction here would be the tool choosing a colour."""
    Image = RP._need_pil()
    words = [0x1234, 0x0000, 0x8000, 0x7FFF]
    base = [KT.direct15_split(x)[:3] + (0 if x == 0 else 255,) for x in words]
    p = tmp_path / "r.png"

    def _write(px=base, stp=None):
        im = Image.new("RGBA", (4, 1))
        im.putdata(px)
        im.save(str(p))
        stp = bytes(255 if x >> 15 else 0 for x in words) if stp is None else bytes(stp)
        Image.frombytes("L", (4, 1), stp).save(str(RP.stp_sidecar_path(p)))

    _write()
    assert RP.read_direct_png(p, 4, 1) == struct.pack("<4H", *words)
    # 1. alpha is a FLAG, not a blend
    _write(px=[base[0][:3] + (128,)] + base[1:])
    with pytest.raises(RP.RepaintError, match="CUTOUT FLAG, not a blend"):
        RP.read_direct_png(p, 4, 1)
    # 2. transparent in the picture, paint in the bytes
    _write(px=[(32, 0, 0, 0)] + base[1:])
    with pytest.raises(RP.RepaintError, match="but its colour encodes"):
        RP.read_direct_png(p, 4, 1)
    # 3. opaque in the picture, 0x0000 in the bytes -- the hardware reads it as a hole regardless
    _write(px=[(0, 0, 0, 255)] + base[1:])
    with pytest.raises(RP.RepaintError) as e:
        RP.read_direct_png(p, 4, 1)
    assert "READS 0x0000 AS A CUTOUT" in str(e.value) and "Nudge one channel to 8" in str(e.value)
    # 4. the sidecar is ONE BIT
    _write(stp=[0, 0, 77, 0])
    with pytest.raises(RP.RepaintError, match="ONE BIT per texel"):
        RP.read_direct_png(p, 4, 1)


def test_the_CUTOUT_LAW_holds_at_all_three_depths_and_is_DERIVED_from_what_is_in_front_of_it():
    """The indexed lane derives its transparent set from the ACTIVE PALETTE and never assumes {0}; at
    direct colour there is no palette, so the same law lands in its palette-less form -- derived from
    the VALUES.  Punch and fill stay countable in both directions at every depth."""
    blob = build_scenery_container()
    for x, bpp in ((704, 8), (576, 4), (512, 15)):
        p = _cell(blob, x, 256)
        raw = blob[p.page_offset:p.page_offset + p.page_bytes]
        if bpp == 15:
            zeros = set(RP.direct_transparent(raw))
            live = [i for i in range(p.w * p.h) if i not in zeros]
        else:
            zeros = set(RP.transparent_indices(RP.palette_words(blob, p)))
            idx = RP.unpack4(raw) if bpp == 4 else raw
            live = [i for i, v in enumerate(idx) if v not in zeros]
        assert zeros, "the fixture puts real holes in every cell, at every depth"
        assert live, "and real paint beside them"
    p = _cell(blob, 512, 256)
    raw = blob[p.page_offset:p.page_offset + p.page_bytes]
    ws = struct.unpack_from("<%dH" % (p.w * p.h), raw, 0)
    assert set(RP.direct_transparent(raw)) == {i for i, w in enumerate(ws) if w == 0}


# ============================================================ (11) W6b-1: THE EXPORT SURFACE
def test_export_art_writes_a_per_cell_PNG_and_NAMES_every_refusal(tmp_path):
    blob = build_scenery_container()
    man = RP.export_art(blob, 999, tmp_path)
    assert {e["name"] for e in man["scenery"]} == {
        "cell.s0.x320_y256", "cell.s0.x384_y256", "cell.s0.x576_y256",
        "cell.s0.x704_y256", "cell.s0.x704_y384"}, "the 15bpp cell is a DIFFERENT lane"
    for e in man["scenery"]:
        assert (tmp_path / e["png"]).is_file()
        assert e["bpp"] in (4, 8) and e["page_bytes"] == 0x4000
        assert e["hazards"] == [] or set(e["hazards"]) <= {
            "shared-read", "multi-palette", "spill-in", "spill-out", "lower-half", "co-transform"}
    assert [r["name"] for r in man["refused"]] == ["cell.s0.x448_y256"]
    assert man["program"]["class"] == "clean" and man["program"]["moveimage_cell"] is None


def test_export_art_round_trips_every_exported_indexed_cell_byte_identically(tmp_path):
    blob = build_scenery_container()
    man = RP.export_art(blob, 999, tmp_path)
    for e in man["scenery"]:
        raw = blob[e["page_offset"]:e["page_offset"] + e["page_bytes"]]
        w, h = e["wh"]
        back = (RP.read_indexed4_png(tmp_path / e["png"], w, h, 16) if e["bpp"] == 4 else
                RP.read_indexed_png(tmp_path / e["png"], w, h, e["clut_entries"]))
        assert back == raw, e["name"]
        assert e["page_sha256"] == hashlib.sha256(raw).hexdigest()


def test_the_class_C_alternates_are_READ_ONLY_views_of_THE_SAME_index_bytes(tmp_path):
    """25 corpus cells are read at one depth through more than one CLUT.  The editable file is in the
    lowest-addressed binding's key and every other key ships as a NAMED alternate -- forced, not
    chosen, because the import reads only the indices and one byte array genuinely has N renderings."""
    blob = build_scenery_container()
    man = RP.export_art(blob, 999, tmp_path)
    e = next(x for x in man["scenery"] if x["name"] == "cell.s0.x576_y256")
    assert e["palette_name"] == "pal.s0.x0_y244.e16"
    assert [a["clut_cell"] for a in e["alternates"]] == [[16, 244]]
    alt = e["alternates"][0]
    assert alt["read_only"] and alt["png"] == "cell.s0.x576_y256.as-x16_y244.png"
    raw = blob[e["page_offset"]:e["page_offset"] + e["page_bytes"]]
    w, h = e["wh"]
    assert RP.read_indexed4_png(tmp_path / alt["png"], w, h, 16) == raw, "the SAME index bytes"
    # ...and they really are two different PICTURES, which is why the second key must be named
    assert (tmp_path / alt["png"]).read_bytes() != (tmp_path / e["png"]).read_bytes()
    assert not [a for x in man["scenery"] if x["name"] != e["name"] for a in x["alternates"]]


def test_export_art_stitches_a_spill_preview_and_names_the_column_no_writer_uploads(tmp_path):
    blob = build_scenery_container()
    man = RP.export_art(blob, 999, tmp_path)
    sp = [m for m in man["models"] if m["spills"]]
    assert len(sp) == 1 and sp[0]["columns"] == [320, 384]
    assert sorted(sp[0]["cells"]) == ["cell.s0.x320_y256", "cell.s0.x384_y256"]
    assert (tmp_path / sp[0]["spill_png"]).is_file()
    Image = RP._need_pil()
    with Image.open(str(tmp_path / sp[0]["spill_png"])) as im:
        assert im.size == (2 * RP.cell_texel_w(8), RP.CELL_LINES), "two columns, stitched"
    # a model that spills into a column NOTHING uploads is named as such -- nothing there to repaint
    lonely = build_scenery_container(rects=SCEN_RECTS[:5], models=(SCEN_MODELS[5],))
    m2 = RP.export_art(lonely, 999, tmp_path / "b")["models"][0]
    assert m2["cells_no_writer"] == ["x320_y256"] and m2["cells"] == ["cell.s0.x384_y256"]


def test_the_manifest_names_BOTH_directions_of_every_join(tmp_path):
    """Which cells a model reads AND which models read a cell.  A one-way index makes the second
    question a re-derivation, and the second question is the one a co-transform author asks."""
    blob = build_scenery_container()
    man = RP.export_art(blob, 999, tmp_path)
    for e in man["scenery"]:
        assert e["writers"] and all(w["bytes"] == 0x4000 for w in e["writers"])
        for r in e["readers"]:
            m = next(m for m in man["models"] if m["geom"] == r["geom"])
            assert e["name"] in m["cells"], "cell -> model -> cell closes"
    for m in man["models"]:
        for nm in m["cells"]:
            e = next((x for x in man["scenery"] if x["name"] == nm), None)
            if e is not None:
                assert m["geom"] in [r["geom"] for r in e["readers"]]
    # a CO-TRANSFORM cell is SEVERAL writer records, and the model side must name every one of them:
    # naming only the first would make the second upload invisible from this direction too
    m = next(m for m in RP.export_art(build_scenery_container(id9=1), 999,
                                      tmp_path / "c")["models"] if m["spills"])
    assert {"cell.s0.x320_y256", "cell.id9.s0.x320_y256"} <= set(m["cells"])


def test_the_direct15_LANE_is_a_real_lane_and_the_RGBA_refusal_does_not_swallow_it(tmp_path):
    """``rgba`` refuses because ITS NO-OP IS NOT A NO-OP; ``direct15`` is a different question with a
    different answer (exhaustive 65,536/65,536), so the two must not share a refusal branch."""
    blob = build_scenery_container()
    assert RP.ART_LANES == ("indexed", "rgba", "direct15") == tuple(cli._SUMMON_ART_LANES)
    with pytest.raises(RP.RepaintError) as e:
        RP.export_art(blob, 999, tmp_path, lane="rgba")
    assert "93/93" in str(e.value) and "direct15" in str(e.value)
    man = RP.export_art(blob, 999, tmp_path / "d", lane="direct15")
    assert [e["name"] for e in man["scenery"]] == ["cell.s0.x512_y256"]
    e = man["scenery"][0]
    assert e["bpp"] == 15 and e["stp_png"] == "cell.s0.x512_y256.stp.png"
    assert (tmp_path / "d" / e["stp_png"]).is_file() and e["stp_share"] is not None
    raw = blob[e["page_offset"]:e["page_offset"] + e["page_bytes"]]
    assert RP.read_direct_png(tmp_path / "d" / e["png"], *e["wh"]) == raw
    assert man["parts"] == [], "the creature lane is INDEXED and does not ride along"
    with pytest.raises(RP.RepaintError, match="unknown art lane"):
        RP.export_art(blob, 999, tmp_path / "z", lane="direct16")


def test_export_art_refuses_a_container_with_no_surface_in_the_lane_and_says_which(tmp_path):
    """The W6a refusal survives -- a creature-less container with no readable scenery still exposes
    nothing -- but it now reports BOTH surfaces instead of only the missing creature package."""
    blob = build_synth_creatureless_container()
    with pytest.raises(RP.RepaintError) as e:
        RP.export_art(blob, 999, tmp_path)
    assert "no id-4" in str(e.value) and "0 refused by name" in str(e.value)


def test_the_scaffold_carries_expect_bpp_expect_cell_and_a_COMMENTED_refusal_block(tmp_path):
    """The scaffold is where a refusal teaches.  On this surface the refused block is the larger half
    by two orders of magnitude, so a cell that merely failed to appear would teach nothing at all."""
    import tomllib as _toml
    blob = build_scenery_container(id9=1)
    RP.export_art(blob, 999, tmp_path)
    txt = (tmp_path / RP.SCAFFOLD_NAME).read_text(encoding="utf-8")
    assert "expect_bpp         = 8" in txt and "expect_cell        = [704, 256]" in txt
    assert "expect_bpp         = 4" in txt and "expect_cell        = [576, 256]" in txt
    assert "CO-TRANSFORM: 2 writers upload this VRAM cell" in txt
    assert "SHARED READ" in txt and "SPILL-OUT" in txt
    assert "THE NAME-EVERY-COLUMN GATE" in txt
    assert "REFUSED CELLS" in txt and "[depth-unknown]" in txt and "cell.s0.x448_y256" in txt
    assert max(len(ln) for ln in txt.splitlines()) < 120, "a 400-char comment is one nobody reads"
    rows = _toml.loads(txt)["reskin"]["texel"]
    assert {r["name"] for r in rows} >= {"cell.s0.x704_y256", "cell.s0.x704_y384"}
    assert all(set(r) <= RP._TEXEL_KEYS for r in rows), "every emitted key is a KNOWN key"
    assert all(r["enabled"] is False for r in rows), "the first build is provably a no-op"
    # and the whole emitted table RESOLVES through the guard stack it was emitted from
    b = RP.build({"reskin": {"effect": 999, "expect_sha256": hashlib.sha256(blob).hexdigest(),
                             "texel": rows}}, str(tmp_path / "s.toml"), blob=blob)
    assert b.patched == blob


def test_the_scenery_derivation_lines_DISCLOSE_the_program_class_and_the_refusal_tally():
    blob = build_scenery_container()
    L = "\n".join(RP.scenery_lines(blob, 211))
    assert "program-VRAM: READ" in L and "cannot clobber a repaint" in L
    assert "cell.s0.x704_y256" in L and "REFUSED 1 cell(s): depth-unknown 1" in L
    # a derivation that REFUSES is printed, never swallowed into an empty census
    broken = bytearray(build_scenery_container())
    off = KC.parse_header(bytes(broken), strict=True).chunks[0].resources[0].offset
    page_rel = struct.unpack_from("<i", broken, off)[0]
    struct.pack_into("<H", broken, off + page_rel + 8 + 4, 32)   # rect 0: w = 32, not 64
    assert "THE DERIVATION REFUSED" in "\n".join(RP.scenery_lines(bytes(broken), 211))


# ============================================================ (12) W6b-1: THE CORPUS CENSUS PINS
_W6B_CENSUS = Path(r"C:/gd/SCRATCH/summon-format/texel-w6b/census/pages.json")
needs_w6b_census = pytest.mark.skipif(
    not _W6B_CENSUS.is_file(),
    reason="needs-corpus: the W6b page-cell census (texel-w6b/census/pages.json) is not on this "
           "machine")


def _corpus_effects():
    for p in sorted(CORPUS.glob("ef*.bytes")):
        if len(p.name) == 11 and p.name[2:5].isdigit():
            yield int(p.name[2:5]), p.read_bytes()


@needs_corpus
def test_the_shipped_derivation_reproduces_THE_WHOLE_SCENERY_CENSUS():
    """CALIBRATE THE INSTRUMENT BEFORE JUDGING WITH IT.  Every number this rung is allowed to quote,
    re-measured by the code that ships rather than read off a dossier -- and measured in CELLS, which
    is the unit the census counts in (``page_cells`` is keyed by WRITER, so a co-transform cell is
    several records and one cell)."""
    cells, read, dark = set(), set(), set()
    hz = {k: set() for k in ("same-bytes-two-depths", "multi-palette", "shared-read",
                             "spill-in", "spill-out", "co-transform")}
    depths = {4: set(), 8: set(), 15: set()}
    for ef, blob in _corpus_effects():
        for pc in RS.page_cells(blob).values():
            cells.add((ef, pc.cell))
        pages, refused = RP.scenery_surface(blob, ef)
        for r in refused:
            if r.klass == "depth-unknown":
                dark.add((ef, r.cell))
        for p in pages:
            k = (ef, p.cell)
            if k in read:
                continue
            read.add(k)
            depths[p.bpp].add(k)
            for n in p.hazards.names:
                if n in hz:
                    hz[n].add(k)
    assert len(cells) == 2572, "the non-creature page-cell population"
    assert len(read) == 187, "cells with at least one `so` reader"
    assert len(dark) == 2385, "DEPTH-UNKNOWN -- 92.7% of the surface, refused by name"
    assert len(read) + len(dark) == len(cells), "every cell is in exactly one of the two"
    assert len(depths[15]) == 14, "the whole 15bpp surface the container states a depth for"
    assert len(hz["same-bytes-two-depths"]) == 17
    assert len(hz["multi-palette"]) == 25, "class C -- the display-palette rule"
    assert len(hz["shared-read"]) == 93, "class E3 -- a disclosure, not a refusal"
    assert len(hz["spill-in"]) == 36, "class F1 -- page scope is the wrong edit unit"
    assert len(hz["spill-in"] | hz["spill-out"]) == 70, "A2's UV-exact spill-touched set"
    assert len(hz["co-transform"]) == 24, "of the 34 multi-writer cells, the 24 that are READ"


@needs_corpus
def test_the_per_cell_map_unlocks_EXACTLY_the_twenty_lower_half_cells():
    """The rung's central claim, as a number.  A1 measured 56 lawful cells and marked 20 more
    UNADDRESSABLE because ``(tag, x)`` cannot name the lower half of a tall rect.  ``page_cells`` names
    them, and the count is exactly 20 -- not 19 and not 21."""
    upper, lower, spill_out = set(), set(), set()
    for ef, blob in _corpus_effects():
        for p in RP.scenery_texel_pages(blob, ef):
            k, h = (ef, p.cell), p.hazards
            if k in upper | lower:
                continue
            if (not h.co_transform and not h.two_depths and not h.multi_palette
                    and not h.shared_read and not h.spill_in and h.program != "write"):
                (lower if h.lower_half else upper).add(k)
                if h.spill_out and not h.lower_half:
                    spill_out.add(k)
    assert len(upper) == 56, "A1's lawful count, re-derived by the shipped code"
    assert len(spill_out) == 6, "LAWFUL != PAGE-SCOPE-SAFE: 56 = 50 page-scope-safe + 6 model-scope"
    assert len(upper) - len(spill_out) == 50
    assert len(lower) == 20, "THE CELLS THE PER-VRAM-CELL MAP UNLOCKS"


@needs_corpus
def test_ef211s_cast_cell_derives_the_decision_documents_appendix_exactly():
    """The cast vehicle, cell by cell.  If this table ever stops matching, the artifact staged against
    it is aimed at bytes nobody re-checked."""
    blob = (CORPUS / "ef211.bytes").read_bytes()
    pages = {p.name: p for p in RP.scenery_texel_pages(blob, 211)}
    assert sorted(pages) == ["cell.s0.x576_y256", "cell.s0.x576_y384",
                             "cell.s0.x640_y256", "cell.s0.x704_y256"]
    fire = pages["cell.s0.x704_y256"]
    assert (fire.bpp, fire.page_offset, fire.tpage) == (8, 0x11678, 155)
    assert fire.palette_name == "pal.s0.x0_y247.e256" and fire.hazards.readers[0].geom == 0x2b668
    assert fire.hazards.covered_halfwords == 8128, "99.2% of the cell is live art"
    assert fire.hazards.names == (), "no co-transform, no dual depth, no shared read, no spill"
    assert fire.hazards.program == "read", "StoreImage is a READ -- disclose, do not refuse"
    # CAST 2: the LOWER HALF the rect view cannot name, clean 4bpp under a two-palette refusal
    cast2 = pages["cell.s0.x576_y384"]
    assert (cast2.bpp, cast2.page_offset) == (4, 0x25678)
    assert cast2.hazards.names == ("lower-half",) and cast2.hazards.covered_halfwords == 2688
    assert cast2.palette_name == "pal.s0.x208_y244.e16"
    assert pages["cell.s0.x576_y256"].hazards.multi_palette, "...and its UPPER half is refused"
    dark = [r.name for r in RP.scenery_cell_refusals(blob, 211)]
    assert len(dark) == 8 and "cell.s0.x704_y384" in dark and "cell.id9.s0.x768_y256" in dark


@needs_corpus
def test_every_readable_corpus_cell_round_trips_BYTE_IDENTICALLY_at_its_own_depth(tmp_path):
    """PASS B, the one that matters: not a ramp palette over anonymous bytes but every cell an ``so``
    binding samples, encoded at ITS OWN declared depth and in ITS OWN CLUT, and re-read."""
    n = {4: 0, 8: 0, 15: 0}
    for ef, blob in _corpus_effects():
        for p in RP.scenery_texel_pages(blob, ef):
            if p.depth_ambiguous or (p.bpp != 15 and p.clut_offset is None):
                continue
            raw = blob[p.page_offset:p.page_offset + p.page_bytes]
            png = tmp_path / "x.png"
            if p.bpp == 15:
                RP.write_direct_png(raw, p.w, p.h, png)
                assert RP.read_direct_png(png, p.w, p.h) == raw, p.name
            elif p.bpp == 4:
                RP.write_indexed4_png(raw, RP.palette_words(blob, p), p.w, p.h, png)
                assert RP.read_indexed4_png(png, p.w, p.h, 16) == raw, p.name
            else:
                RP.write_indexed_png(raw, RP.palette_words(blob, p), p.w, p.h, png)
                assert RP.read_indexed_png(png, p.w, p.h, 256) == raw, p.name
            n[p.bpp] += 1
    assert (n[4], n[8], n[15]) == (50, 144, 14), \
        "the WHOLE round-trippable surface, per writer record -- if this population moves, the pass " \
        "above stopped covering what it used to and the count is the only thing that would say so"
    print("W6b identity: %d 4bpp + %d 8bpp + %d 15bpp cell views, 0 mismatches"
          % (n[4], n[8], n[15]))


@needs_corpus
def test_the_nibble_pack_is_byte_identical_over_EVERY_corpus_writer_cell():
    """The pure-arithmetic half, run over the whole surface rather than the readable 187: 2,648 cell
    writer records, every one of them ``pack4(unpack4(b)) == b`` and every unpacked value <= 15."""
    n = 0
    for _ef, blob in _corpus_effects():
        for pc in RS.page_cells(blob).values():
            raw = blob[pc.off:pc.off + pc.nbytes]
            idx = RP.unpack4(raw)
            assert max(idx) <= 15 and RP.pack4(idx) == raw
            n += 1
    assert n == 2648, "the corpus's whole cell-writer population"


@needs_w6b_census
def test_the_program_VRAM_lists_are_RE_DERIVATION_PINNED_to_the_census():
    """The one place this module caches a MEASUREMENT rather than deriving it -- so the cache is
    compared against the measurement's own output.  A constant nobody re-checks is a claim."""
    recs = json.loads(_W6B_CENSUS.read_text(encoding="utf-8"))
    scen = [r for r in recs if r["addressable_via"] != ["repaint.creature_texel_pages()"]]
    assert len(scen) == 2572
    assert RP.PROGRAM_VRAM_WRITE_IDS == frozenset(r["ef"] for r in scen if r["hz_program_write"])
    assert RP.PROGRAM_VRAM_READ_IDS == frozenset(r["ef"] for r in scen
                                                 if r["program_verdict"] == "read-storeimage")
    assert sum(1 for r in scen if r["hz_program_write"]) == 175
    assert sum(1 for r in scen if r["program_verdict"] == "read-storeimage") == 113
    hard = {r["ef"]: (r["vram_x"], r["vram_y"]) for r in scen if r["hz_program_write_here"]}
    assert RP.MOVEIMAGE_HARD_CELLS == hard


@needs_w6b_census
def test_the_hazard_record_agrees_with_the_census_CELL_BY_CELL():
    """Not a count -- an identity, over every cell the census and the kit both name.  A tally can
    agree by coincidence; a per-cell join cannot."""
    recs = {(r["ef"], (r["vram_x"], r["vram_y"])): r for r in json.loads(
        _W6B_CENSUS.read_text(encoding="utf-8"))}
    checked = 0
    #: cells the RECT-conservative census calls spill-touched and the UV-exact derivation does not.
    rect_only = set()
    for ef, blob in _corpus_effects():
        for p in RP.scenery_texel_pages(blob, ef):
            r = recs.get((ef, p.cell))
            if r is None or r["bpp"] is None:
                continue
            assert p.bpp == r["bpp"] or p.depth_ambiguous, p.name
            assert p.hazards.two_depths == r["hz_dual_depth"], p.name
            assert p.hazards.shared_read == r["hz_shared_read"], p.name
            assert p.hazards.co_transform == r["hz_co_transform"], p.name
            assert bool(p.hazards.spill_in) == bool(r["hz_spill_in"]), p.name
            # the census records a spill as {geom, into, cross_resource}; the kit records the COLUMNS
            census_out = {c for s in r["spill_out"] for c in s["into"]}
            assert set(p.hazards.spill_out) <= census_out, p.name
            if set(p.hazards.spill_out) != census_out:
                # THE SETTLED DISAGREEMENT, proved on the shipping code rather than quoted.  The
                # census is RECT-conservative -- it marks every stacked cell of a spilling rect --
                # while the kit is UV-EXACT, so a LOWER HALF the model's own `v` range never reaches
                # is not spill-touched.  The ruling is to gate on the UV-exact set (naming a cell the
                # model does not read would be a false obligation), and the delta is entirely lower
                # halves: the assertion below is what makes that a measurement and not a claim.
                assert p.hazards.lower_half, p.name
                rect_only.add((ef, p.cell))
            if p.hazards.writer.startswith("id9."):
                # A MEASURED DIVERGENCE, pinned rather than skipped.  An id-9 alternate block is one
                # whole 0x4000 upload, so it is never the lower half of a tall rect -- the census
                # flags the CELL (a DIFFERENT writer's h=256 rect makes it one), and a per-WRITER
                # record must describe its own upload.  Both facts are true of different objects.
                assert p.hazards.lower_half is False, p.name
            else:
                assert p.hazards.lower_half == r["hz_unaddressable_lower_half"], p.name
            assert {r2.geom for r2 in p.hazards.readers} == {x["geom"] for x in r["readers"]}, p.name
            checked += 1
    assert checked > 180, "the join actually ran over the readable surface"
    # THE DELTA, scoped honestly.  The published rect-vs-UV-exact disagreement is 13 cells (83 - 70),
    # but that is measured over the WHOLE surface, and this join can only visit the 187 cells whose
    # depth the container states -- the rest are depth-unknown and have no page to join against.  So
    # what is pinned here is the readable slice of it (2 cells), not the headline number: comparing
    # the two would be comparing different predicates and calling the difference a contradiction.
    assert rect_only == {(381, (384, 384)), (447, (384, 384))}, \
        "the readable slice of the rect-vs-UV-exact delta -- both lower halves, both cells whose " \
        "spilling model's own v range never reaches them"


# ============================================================ (13) W6b-1: THE HAZARD GATES
# Section 9 proved the DERIVATION states every hazard.  This section proves the GATE LAYER acts on it:
# what refuses, what refuses WITH A REMEDY, and what merely discloses.  That split is the rung's whole
# posture -- 2,385 of 2,572 cells refuse, 16 co-transform cells and 70 spill-touched cells have a
# lawful remedy, and 93 shared-read + 25 multi-palette + 113 program-READ cells are DISCLOSURES that
# would be dishonest as refusals and dangerous as silence.
#
# THE ONE RECONCILIATION THIS FILE MAKES EXPLICIT.  SYNTHESIS sec 1.1's remedy column is the authority
# here -- it is the row that says what the tool DOES: class E2 (multi-palette) is "editable + named
# read-only alternates, NOT a refusal" and class E3 (shared read) is "DISCLOSURE".  The document's own
# appendix labels ef211 (576,256) "REFUSE  multi-palette + shared-read"; that column is A1's `lawful`
# PREDICATE (which excludes multi-palette from its count of 56), not a gate verdict, and the two are
# different questions about one cell.  The gates implement sec 1.1, and the corpus test at the end of
# this section pins that reading on ef211 itself so the choice is visible rather than assumed.


def _page_at(blob, page):
    return blob[page.page_offset:page.page_offset + page.page_bytes]


def _write_cell_png(tmp_path, blob, page, raw=None, name=None):
    """One scenery cell -> the PNG(s) of record at ITS OWN depth.  Dispatching on the DERIVED depth is
    the rule the build itself uses, so a test cannot hand the lane a picture of a shape the derivation
    never claimed."""
    raw = _page_at(blob, page) if raw is None else raw
    p = tmp_path / ("%s.png" % (name or page.name))
    if page.direct:
        RP.write_direct_png(raw, page.w, page.h, p)
    elif page.bpp == 4:
        RP.write_indexed4_png(raw, RP.palette_words(blob, page), page.w, page.h, p)
    else:
        RP.write_indexed_png(raw, RP.palette_words(blob, page), page.w, page.h, p)
    return p


def _bump_cell(page, raw):
    """Move EVERY live texel of a cell without ever crossing the transparent boundary, at any depth.

    A cutout crossing is a different law with a different acknowledgement, so an edit generator that
    tripped it by accident would make every gate test below assert two things at once."""
    vals = list(RP.texel_view(page, raw))
    if page.direct:
        out = [v if v == KT.DIRECT15_CUTOUT else ((v ^ 0x0421) | 0x0001) for v in vals]
        return struct.pack("<%dH" % len(out), *out)
    top = 16 if page.bpp == 4 else 256
    out = bytes(v if v == 0 else 1 + (v % (top - 1)) for v in vals)
    return RP.pack4(out) if page.bpp == 4 else bytes(out)


#: the fixture's models with the SPILLER replaced by one that stays inside its own column, so a
#: co-transform test is about co-transform alone.  u 100 at 8bpp reaches halfword 50 -- one column.
NOSPILL_MODELS = SCEN_MODELS[:5] + (("only", 320, 256, 8, (0, 245), (0, 0, 100, 60)),)


def _row(page, src, **kw):
    d = {"name": page.name, "source": str(src)}
    d.update(kw)
    return d


def test_the_edit_generator_and_the_cell_writer_are_themselves_sound(tmp_path):
    """THE FIXTURE FIRST.  Every gate test below asserts that a specific refusal fired; if the art
    round trip or the bump were broken, they would all pass for the wrong reason."""
    blob = build_scenery_container()
    for x, bpp in ((704, 8), (576, 4), (512, 15)):
        p = _cell(blob, x, 256)
        assert p.bpp == bpp
        raw = _page_at(blob, p)
        src = _write_cell_png(tmp_path, blob, p)
        back = (RP.read_direct_png(src, p.w, p.h) if p.direct else
                RP.read_indexed4_png(src, p.w, p.h, 16) if p.bpp == 4 else
                RP.read_indexed_png(src, p.w, p.h, 256))
        assert back == raw, "an unedited re-export is a byte-exact no-op at every depth"
        new = _bump_cell(p, raw)
        assert len(new) == len(raw) and new != raw
        zeros = set(RP.transparent_values(blob, p)[0])
        st, nw = RP.texel_view(p, raw), RP.texel_view(p, new)
        assert not [i for i in range(len(st)) if (st[i] in zeros) != (nw[i] in zeros)], \
            "the bump never crosses the transparent boundary, at any depth"
        assert [i for i in range(len(st)) if st[i] != nw[i]]


# ---- THE PROGRAM-VRAM GATE (THE DIRECTION LAW) ---------------------------------------------------
def test_a_program_VRAM_WRITE_container_REFUSES_the_build_with_its_measurement(tmp_path):
    """175 cells over 15 containers.  0 of the 18 corpus ``RECT*`` arguments const-fold, so WHERE the
    program lands is unresolvable at this layer, and a repaint there is a LOST EDIT with no symptom --
    the container on disc still holds the new art."""
    blob = build_scenery_container()
    p = _cell(blob, 704, 256)
    src = _write_cell_png(tmp_path, blob, p, _bump_cell(p, _page_at(blob, p)))
    with pytest.raises(RP.RepaintError) as e:
        RP.build(_spec_dict(blob, [_row(p, src)], effect=38), "?", blob=blob)
    assert "PROGRAM-VRAM WRITE" in str(e.value) and "175 cells over 15" in str(e.value)
    assert "LOST EDIT" in str(e.value)


def test_the_MOVEIMAGE_destination_refuses_BY_CELL_which_is_SHARPER_not_NARROWER(tmp_path):
    """The ONE per-cell program verdict in the corpus: ``MoveImage``'s destination const-folds to
    (704, 256) on 3 of its 5 sites.

    A CORRECTION THIS TEST EXISTS TO PIN.  It is tempting to read that as "so the rest of ef001 /
    ef142 / ef144 is editable" -- the shipped refusal text said exactly that -- and the census says
    otherwise: all 30 non-creature cells of those three containers carry ``hz_program_write`` with
    ``program_verdict == "write-moveimage-dest-known"``.  The three containers refuse WHOLESALE; what
    the per-cell verdict adds is that on ONE cell the destination is RESOLVED instead of merely
    unresolvable.  Both refusals fire, the sharper one first, and neither is a narrowing."""
    blob = build_scenery_container()
    hot, cold = _cell(blob, 704, 256), _cell(blob, 704, 384)
    s1 = _write_cell_png(tmp_path, blob, hot, _bump_cell(hot, _page_at(blob, hot)))
    with pytest.raises(RP.RepaintError) as e:
        RP.build(_spec_dict(blob, [_row(hot, s1)], effect=142), "?", blob=blob)
    assert "PROGRAM-VRAM WRITE, BY CELL" in str(e.value)
    assert "ONE per-cell program verdict" in str(e.value)
    assert "SHARPER, NOT NARROWER" in str(e.value)
    s2 = _write_cell_png(tmp_path, blob, cold, _bump_cell(cold, _page_at(blob, cold)))
    with pytest.raises(RP.RepaintError) as e2:
        RP.build(_spec_dict(blob, [_row(cold, s2)], effect=142), "?", blob=blob)
    assert "PROGRAM-VRAM WRITE" in str(e2.value) and "BY CELL" not in str(e2.value), \
        "the sibling cell gets the container-wide verdict, not the by-cell one"
    # ...and the sharpness IS real: on a container with no program at all, the same cell builds
    b = RP.build(_spec_dict(blob, [_row(hot, s1)], effect=227), "?", blob=blob)
    assert b.enabled[0].changed and "program-VRAM CLEAN" in "  ".join(b.enabled[0].hazard_notes)


def test_a_program_READ_container_BUILDS_and_DISCLOSES_the_direction_law(tmp_path):
    """THE CORRECTION THE CAST RESTS ON.  ``StoreImage`` is VRAM -> main RAM and a read cannot clobber
    a repaint -- 113 cells over 12 containers move from refuse to disclose on it, ef211's fire field
    among them.  A DISCLOSURE, not silence: the author is still told the program touches VRAM."""
    blob = build_scenery_container()
    p = _cell(blob, 704, 256)
    src = _write_cell_png(tmp_path, blob, p, _bump_cell(p, _page_at(blob, p)))
    b = RP.build(_spec_dict(blob, [_row(p, src)], effect=211), "?", blob=blob)
    b.check = RP.self_check(b)
    assert b.check.ok, [g.detail for g in b.check.gates if not g.ok]
    note = "  ".join(b.enabled[0].hazard_notes)
    assert "program-VRAM READ" in note and "StoreImage" in note and "cannot clobber" in note


def test_an_effect_id_the_lists_cannot_see_is_refused_as_a_WRITE_not_waved_through():
    """Silence is IGNORANCE, never safety.  The lists are keyed by effect id, so a derivation handed
    bare bytes with no id genuinely does not know -- and reading that as clean is how a refusal turns
    into a comment."""
    blob = build_scenery_container()
    p = RP.texel_page(blob, "cell.s0.x704_y256", None)
    assert p.hazards.program == "unknown"
    with pytest.raises(RP.RepaintError) as e:
        RP._gate_program_vram(p, "row 0")
    assert "PROGRAM-VRAM UNKNOWN" in str(e.value) and "silence here is ignorance" in str(e.value)


# ---- THE CO-TRANSFORM REMEDY ---------------------------------------------------------------------
def _cotransform_blob():
    return build_scenery_container(models=NOSPILL_MODELS, id9=1)


def test_a_CO_TRANSFORM_cell_refuses_until_EVERY_writer_is_named_with_its_own_art(tmp_path):
    """0 of the corpus's 156 multi-writer pairs is byte-identical (the closest still differs in 1.03%
    of its bytes), so repainting one upload and leaving the other stock makes the cast flicker between
    two pictures -- a mid-cast symptom only a playtest catches."""
    blob = _cotransform_blob()
    a, b = _cell(blob, 320, 256, "s0"), _cell(blob, 320, 256, "id9.s0")
    assert a.hazards.co_transform and a.page_offset != b.page_offset
    sa = _write_cell_png(tmp_path, blob, a, _bump_cell(a, _page_at(blob, a)))
    with pytest.raises(RP.RepaintError) as e:
        RP.build(_spec_dict(blob, [_row(a, sa, acknowledge_cotransform=True)]), "?", blob=blob)
    msg = str(e.value)
    assert "THE CO-TRANSFORM REMEDY" in msg and "LEFT STOCK" in msg
    assert "cell.id9.s0.x320_y256" in msg, "the work order NAMES the row to add"
    assert 'no "same art for all writers" shorthand' in msg


def test_the_CO_TRANSFORM_remedy_needs_the_WORD_even_once_every_writer_is_named(tmp_path):
    """Naming every writer is the hard half and not the whole of it: repainting N uploads of one cell
    is a deliberate, coordinated edit, and this lane makes an author state it -- the same shape the
    CLUT lane's own multi-writer gate has."""
    blob = _cotransform_blob()
    a, b = _cell(blob, 320, 256, "s0"), _cell(blob, 320, 256, "id9.s0")
    sa = _write_cell_png(tmp_path, blob, a, _bump_cell(a, _page_at(blob, a)))
    sb = _write_cell_png(tmp_path, blob, b, _bump_cell(b, _page_at(blob, b)), name="id9")
    with pytest.raises(RP.RepaintError, match="acknowledge_cotransform"):
        RP.build(_spec_dict(blob, [_row(a, sa), _row(b, sb)]), "?", blob=blob)
    # ...and a TRUTHY STRING is not the word
    with pytest.raises(RP.RepaintError, match="must be a BOOLEAN"):
        RP.build(_spec_dict(blob, [_row(a, sa, acknowledge_cotransform="true"),
                                   _row(b, sb, acknowledge_cotransform=True)]), "?", blob=blob)


def test_the_CO_TRANSFORM_remedy_BUILDS_both_writers_and_the_self_check_RE_MEASURES_it(tmp_path):
    blob = _cotransform_blob()
    a, b = _cell(blob, 320, 256, "s0"), _cell(blob, 320, 256, "id9.s0")
    sa = _write_cell_png(tmp_path, blob, a, _bump_cell(a, _page_at(blob, a)))
    sb = _write_cell_png(tmp_path, blob, b, _bump_cell(b, _page_at(blob, b)), name="id9")
    build = RP.build(_spec_dict(blob, [_row(a, sa, acknowledge_cotransform=True),
                                       _row(b, sb, acknowledge_cotransform=True)]), "?", blob=blob)
    build.check = RP.self_check(build)
    assert build.check.ok, [g.detail for g in build.check.gates if not g.ok]
    assert len(build.enabled) == 2 and all(t.changed for t in build.enabled)
    g = [x for x in build.check.quality if "hazard this cell carries" in x.name][0]
    assert g.ok and "CO-TRANSFORM: 2 writers" in g.detail and "acknowledged" in g.detail
    assert set(build.check.per_target) == {a.name, b.name}


def test_two_writers_sharing_ONE_source_file_is_disclosed_rather_than_silently_accepted(tmp_path):
    """There is no shorthand that broadcasts one PNG to N writers -- that would be the TOOL asserting
    the uploads are interchangeable, which 156 of 156 corpus pairs deny.  An AUTHOR may still decide
    to unify them, and then it is said out loud."""
    blob = _cotransform_blob()
    a, b = _cell(blob, 320, 256, "s0"), _cell(blob, 320, 256, "id9.s0")
    one = _write_cell_png(tmp_path, blob, a, _bump_cell(a, _page_at(blob, a)))
    # ...and note what it costs, measured rather than argued: the two uploads are DIFFERENT pictures,
    # so one file over both punches 177 holes in the second one's silhouette.  The cutout law catches
    # that on its own, which is why the shared-source note is a disclosure and not a second gate.
    with pytest.raises(RP.RepaintError, match="THE CUTOUT LAW"):
        RP.build(_spec_dict(blob, [_row(a, one, acknowledge_cotransform=True),
                                   _row(b, one, acknowledge_cotransform=True)]), "?", blob=blob)
    build = RP.build(_spec_dict(blob, [
        _row(a, one, acknowledge_cotransform=True, acknowledge_cutout_reshape=True),
        _row(b, one, acknowledge_cotransform=True, acknowledge_cutout_reshape=True)]), "?", blob=blob)
    note = "  ".join(build.enabled[0].hazard_notes)
    assert "two writers share one source file" in note
    assert "an authored decision, not a default" in note


# ---- THE NAME-EVERY-COLUMN GATE ------------------------------------------------------------------
def test_a_SPILLING_models_cell_refuses_PAGE_scope_and_names_the_column_left_out(tmp_path):
    """58 of 58 spilling corpus pictures are wider than one page (median 224 texels against 128) and
    0 of 58 spill by <= 2%, so there is no marginal case to wave through: a page-scope edit hands the
    author half a picture."""
    blob = build_scenery_container()
    own = _cell(blob, 320, 256)
    src = _write_cell_png(tmp_path, blob, own, _bump_cell(own, _page_at(blob, own)))
    with pytest.raises(RP.RepaintError) as e:
        RP.build(_spec_dict(blob, [_row(own, src, acknowledge_spill=True)]), "?", blob=blob)
    msg = str(e.value)
    assert "THE NAME-EVERY-COLUMN GATE" in msg and "NOT NAMED: x384_y256" in msg
    assert "spills OUT of it" in msg and "cell.s0.x384_y256" in msg
    assert "0 of 58 spill by <= 2%" in msg


def test_a_SPILL_IN_cell_refuses_page_scope_and_NAMES_THE_FOREIGN_MODEL(tmp_path):
    """36 corpus cells are read by a model whose own tpage column is elsewhere (6 of them across two
    resources).  A page-scope edit there silently changes a model the cell does not name, which is
    exactly why the edit unit is the MODEL."""
    blob = build_scenery_container()
    foreign = _cell(blob, 384, 256)
    assert foreign.hazards.spill_in and not foreign.hazards.readers[0].own_column
    src = _write_cell_png(tmp_path, blob, foreign, _bump_cell(foreign, _page_at(blob, foreign)))
    with pytest.raises(RP.RepaintError) as e:
        RP.build(_spec_dict(blob, [_row(foreign, src, acknowledge_spill=True)]), "?", blob=blob)
    msg = str(e.value)
    assert "SPILLS IN here" in msg and "own column is 320" in msg
    assert ("GEOM %#x" % foreign.hazards.readers[0].geom) in msg


def test_the_NAME_EVERY_COLUMN_remedy_BUILDS_once_every_covered_cell_is_named(tmp_path):
    """The remedy is the co-transform shape with ``writer`` -> ``cell``: name them all, art for each,
    say the word.  The edit unit is the CELL; the judgement unit is the picture."""
    blob = build_scenery_container()
    own, far = _cell(blob, 320, 256), _cell(blob, 384, 256)
    s1 = _write_cell_png(tmp_path, blob, own, _bump_cell(own, _page_at(blob, own)))
    s2 = _write_cell_png(tmp_path, blob, far, _bump_cell(far, _page_at(blob, far)))
    rows = [_row(own, s1, acknowledge_spill=True), _row(far, s2, acknowledge_spill=True)]
    b = RP.build(_spec_dict(blob, rows), "?", blob=blob)
    b.check = RP.self_check(b)
    assert b.check.ok, [g.detail for g in b.check.gates if not g.ok]
    assert "SPILL:" in "  ".join(b.enabled[0].hazard_notes)
    with pytest.raises(RP.RepaintError, match="acknowledge_spill"):
        RP.build(_spec_dict(blob, [_row(own, s1), _row(far, s2)]), "?", blob=blob)


def test_the_spill_ack_and_disclosure_reach_EVERY_writer_of_a_shared_cell_in_any_row_order(tmp_path):
    """V1 F1.  The spill gate used to key ``{cell: target}`` -- last-wins -- so on a cell that is
    both CO-TRANSFORM and covered by a spilling picture, N writer rows collapsed to one: the
    acknowledgement was enforced on whichever row survived and the verdict flipped with TOML row
    order.  Same spec content must refuse in BOTH orders; and once every row says the word, the
    SPILL disclosure must land on BOTH writers of the shared cell.  ``_gate_cotransform`` keys
    lists; the two mirrored gates must not diverge."""
    blob = build_scenery_container(id9=1)
    a, b = _cell(blob, 320, 256, "s0"), _cell(blob, 320, 256, "id9.s0")
    far = _cell(blob, 384, 256)
    assert a.hazards.co_transform and a.hazards.spills, "the fixture must stack both hazards"
    sa = _write_cell_png(tmp_path, blob, a, _bump_cell(a, _page_at(blob, a)))
    sb = _write_cell_png(tmp_path, blob, b, _bump_cell(b, _page_at(blob, b)), name="id9")
    sf = _write_cell_png(tmp_path, blob, far, _bump_cell(far, _page_at(blob, far)), name="far")
    base = [_row(a, sa, acknowledge_cotransform=True),                    # NO acknowledge_spill
            _row(b, sb, acknowledge_cotransform=True, acknowledge_spill=True),
            _row(far, sf, acknowledge_spill=True)]
    for rows in (base, list(reversed(base))):
        with pytest.raises(RP.RepaintError, match="acknowledge_spill"):
            RP.build(_spec_dict(blob, rows), "?", blob=blob)
    full = [_row(a, sa, acknowledge_cotransform=True, acknowledge_spill=True),
            _row(b, sb, acknowledge_cotransform=True, acknowledge_spill=True),
            _row(far, sf, acknowledge_spill=True)]
    build = RP.build(_spec_dict(blob, full), "?", blob=blob)
    noted = {t.name for t in build.enabled if any("SPILL:" in n for n in t.hazard_notes)}
    assert {a.name, b.name} <= noted, "the disclosure reaches every writer row, not the last one"


def test_a_column_NO_WRITER_uploads_refuses_because_there_is_nothing_there_to_repaint(tmp_path):
    """ef390's 10 writerless 15bpp bindings, in miniature.  The obligation is *name every column*, and
    a column nothing uploads cannot be named -- there are no bytes in this container to put art in."""
    blob = build_scenery_container(rects=SCEN_RECTS[:5], models=(SCEN_MODELS[5],))
    far = _cell(blob, 384, 256)
    src = _write_cell_png(tmp_path, blob, far, _bump_cell(far, _page_at(blob, far)))
    with pytest.raises(RP.RepaintError) as e:
        RP.build(_spec_dict(blob, [_row(far, src, acknowledge_spill=True)]), "?", blob=blob)
    msg = str(e.value)
    assert "NO WRITER in this container uploads" in msg and "x320_y256" in msg
    assert "nothing to repaint" in msg and "ef390" in msg


# ---- THE DISCLOSURES -----------------------------------------------------------------------------
def test_a_SHARED_READ_multi_palette_cell_BUILDS_and_DISCLOSES_both(tmp_path):
    """SYNTHESIS sec 1.1's remedy column, implemented.  Class E2 (multi-palette) is the DISPLAY-PALETTE
    RULE, not a refusal -- one index array with N renderings IS the format, because the import already
    reads only the indices -- and class E3 (shared read) is a disclosure naming the other models.
    Refusing either would refuse a coherent edit; saying nothing would let an author tune a colour they
    cannot see."""
    blob = build_scenery_container()
    p = _cell(blob, 576, 256)
    assert p.hazards.multi_palette and p.hazards.shared_read
    src = _write_cell_png(tmp_path, blob, p, _bump_cell(p, _page_at(blob, p)))
    b = RP.build(_spec_dict(blob, [_row(p, src)]), "?", blob=blob)
    b.check = RP.self_check(b)
    assert b.check.ok, [g.detail for g in b.check.gates if not g.ok]
    note = "  ".join(b.enabled[0].hazard_notes)
    assert "SHARED READ (2 models)" in note and "GEOM" in note
    assert "MULTI-PALETTE (class C)" in note and "pal.s0.x0_y244.e16" in note
    assert "pal.s0.x16_y244.e16" in note, "the OTHER key is named -- that is the whole point"
    assert "as-x{X}_y{Y}.png" in note
    assert "COVER:" in note and str(p.hazards.covered_halfwords) in note


def test_a_LOWER_HALF_cell_says_so_because_the_rect_view_cannot_name_it(tmp_path):
    blob = build_scenery_container()
    p = _cell(blob, 704, 384)
    src = _write_cell_png(tmp_path, blob, p, _bump_cell(p, _page_at(blob, p)))
    b = RP.build(_spec_dict(blob, [_row(p, src)]), "?", blob=blob)
    note = "  ".join(b.enabled[0].hazard_notes)
    assert "LOWER HALF" in note and "20 " in note
    assert "(tag, x) key can only ever reach the top half" in note


def test_the_W7_DISJOINTNESS_line_is_stated_only_where_the_table_actually_DECODED():
    """0 of 378 cell-writer file-span intersections over the five armed containers, so a scenery edit
    cannot reach the protected set and W7's L4 obligation does not extend to this lane.  It is a
    statement ABOUT A DECODED TABLE: on a region nobody could parse the honest report is that the
    disjointness was NOT MEASURED here, and pass 1 refuses instead of quoting the corpus."""
    blob = build_scenery_container()
    p = _cell(blob, 704, 256)
    t = RP.TexelTarget(name=p.name, enabled=True, source="", page=p)
    ok = TA.read(armed_texel_blob(nparts=1))
    assert ok.armed and ok.table is not None
    note = RP._gate_texanim_frames(ok, t)
    assert "DISJOINT" in note and "0 of 378" in note
    assert "conditional on the table DECODING -- which it did here" in note
    unread = build_texel_container(nparts=1, texanim=64)
    with pytest.raises(RP.RepaintError) as e:
        RP._gate_texanim(unread, [t])
    msg = str(e.value)
    assert "TEXANIM ARMED" in msg and "SCENERY cells" in msg
    assert "restating a result instead of checking one" in msg


# ---- THE BUILD / SELF-CHECK WIRING ---------------------------------------------------------------
@pytest.mark.parametrize("x,bpp", [(704, 8), (576, 4), (512, 15)])
def test_a_scenery_cell_BUILDS_AT_ITS_OWN_DEPTH_and_splices_only_its_own_0x4000(x, bpp, tmp_path):
    """One dispatch, three codecs, and the depth comes from the DERIVATION rather than from the file's
    shape: the same 0x4000 bytes are 256 / 128 / 64 texels wide, so a wrong depth packs to exactly the
    right byte count and paints the wrong picture with no gate firing."""
    blob = build_scenery_container()
    p = _cell(blob, x, 256)
    assert p.bpp == bpp
    src = _write_cell_png(tmp_path, blob, p, _bump_cell(p, _page_at(blob, p)))
    b = RP.build(_spec_dict(blob, [_row(p, src, expect_bpp=bpp, expect_cell=[x, 256])]),
                 "?", blob=blob)
    b.check = RP.self_check(b)
    assert b.check.ok, [g.detail for g in b.check.gates if not g.ok]
    assert len(b.patched) == len(blob)
    moved = [i for i in range(len(blob)) if blob[i] != b.patched[i]]
    assert moved and min(moved) >= p.page_offset and max(moved) < p.page_offset + p.page_bytes
    assert b.enabled[0].round_trip
    assert b.enabled[0].covered_halfwords == p.hazards.covered_halfwords


def test_an_unedited_scenery_re_export_is_a_byte_exact_no_op_at_every_depth(tmp_path):
    """The property that makes a re-pack idempotent -- and the one a lane whose no-op is not a no-op
    cannot have, which is the whole reason the indexed lane refuses RGBA."""
    blob = build_scenery_container()
    rows = []
    for x in (704, 576, 512):
        p = _cell(blob, x, 256)
        rows.append(_row(p, _write_cell_png(tmp_path, blob, p)))
    b = RP.build(_spec_dict(blob, rows), "?", blob=blob)
    assert b.patched == blob and not [t for t in b.enabled if t.changed]
    b.check = RP.self_check(b)
    assert b.check.ok, [g.detail for g in b.check.gates if not g.ok]


@pytest.mark.parametrize("x", [576, 512])
def test_THE_CUTOUT_LAW_fires_on_a_scenery_cell_at_4bpp_and_at_15bpp(x, tmp_path):
    """The silhouette is the one thing a texel edit can change and a palette edit structurally cannot,
    so it is said out loud at EVERY depth -- and the transparent set is DERIVED both times: from the
    active palette where there is one, from the values where there is not."""
    blob = build_scenery_container()
    p = _cell(blob, x, 256)
    vals = list(RP.texel_view(p, _page_at(blob, p)))
    zeros = set(RP.transparent_values(blob, p)[0])
    hole = next(i for i, v in enumerate(vals) if v in zeros)
    vals[hole] = 0x1234 if p.direct else 1                   # FILL: hole -> opaque
    new = (struct.pack("<%dH" % len(vals), *vals) if p.direct else
           RP.pack4(vals) if p.bpp == 4 else bytes(vals))
    src = _write_cell_png(tmp_path, blob, p, new)
    with pytest.raises(RP.RepaintError) as e:
        RP.build(_spec_dict(blob, [_row(p, src)]), "?", blob=blob)
    msg = str(e.value)
    assert "THE CUTOUT LAW" in msg and "1 filled hole->opaque" in msg
    assert ("the word 0x0000" in msg) if p.direct else ("palette index 0" in msg)
    b = RP.build(_spec_dict(blob, [_row(p, src, acknowledge_cutout_reshape=True)]), "?", blob=blob)
    assert (b.enabled[0].cutout_fill, b.enabled[0].cutout_punch) == (1, 0)


def test_the_SELF_CHECK_gates_the_id0_header_and_RE_DERIVES_the_page_cell_map(tmp_path):
    """THE HIGHEST-VALUE NEW GATE IN THE RUNG.  The page map is read out of the id-0 page-block header
    and the (x, y, w, h) rect table, which this lane licenses NOTHING of -- and a splice that moved one
    of them would re-aim the whole map while the container still parsed, the length still matched and
    every palette still re-derived."""
    blob = build_scenery_container()
    p = _cell(blob, 704, 256)
    src = _write_cell_png(tmp_path, blob, p, _bump_cell(p, _page_at(blob, p)))
    b = RP.build(_spec_dict(blob, [_row(p, src)]), "?", blob=blob)
    b.check = RP.self_check(b)
    ident = [g for g in b.check.regions if "RE-DERIVES identically" in g.name][0]
    split = [g for g in b.check.regions if "page-block header" in g.name][0]
    assert ident.ok and "page-cell(s) re-derive identically" in ident.detail
    assert split.ok and "0 changed byte(s) below the pixelDataRel boundary" in split.detail
    assert "licensed PIXEL stream" in split.detail
    # ...and the gate is not a comment: perturb the RECT TABLE in the patched bytes and both fire
    off = KC.parse_header(blob, strict=True).chunks[0].resources[0].offset
    page_rel = struct.unpack_from("<i", blob, off)[0]
    bad = bytearray(b.patched)
    struct.pack_into("<H", bad, off + page_rel + 8 + 2, 384)      # rect 0: y 256 -> 384
    b.patched = bytes(bad)
    chk = RP.self_check(b)
    g2 = [g for g in chk.regions if "RE-DERIVES identically" in g.name][0]
    assert not g2.ok and "DERIVATION MOVED" in g2.detail
    assert not [g for g in chk.regions if "page-block header" in g.name][0].ok


def test_the_id4_decode_gate_INVERTS_for_a_creature_less_container(tmp_path):
    """An inverted pin, in the self-check.  348 of the corpus's 372 containers declare no creature
    package and now have a real texel surface, so "the patched id-4 package still DECODES" has to
    report that there is none rather than fail on it -- while still checking the half a splice could
    break, namely that the PATCHED container declares none either."""
    blob = build_scenery_container()
    p = _cell(blob, 704, 256)
    src = _write_cell_png(tmp_path, blob, p, _bump_cell(p, _page_at(blob, p)))
    b = RP.build(_spec_dict(blob, [_row(p, src)]), "?", blob=blob)
    b.check = RP.self_check(b)
    g = [x for x in b.check.regions if "id-4 package still DECODES" in x.name][0]
    assert g.ok and "SKIPPED" in g.detail and "348 of the corpus's 372" in g.detail
    env = [x for x in b.check.accounting if "envelope" in x.name][0]
    assert env.ok and "0 creature page(s)" in env.detail
    assert "16384 scenery cell byte(s)" in env.detail


def test_two_enabled_targets_may_not_write_the_same_file_bytes(tmp_path):
    """A last-one-wins splice with no complaint is exactly the silent failure this lane is built
    against, and the derivation is what would have to be wrong for it to happen -- which is the class
    of thing a gate exists for."""
    blob = build_scenery_container()
    p = _cell(blob, 704, 256)
    src = str(_write_cell_png(tmp_path, blob, p))
    with pytest.raises(RP.RepaintError, match="OVERLAPPING TARGETS"):
        RP._gate_spans(blob, [RP.TexelTarget(name=p.name, enabled=True, source=src, page=p),
                              RP.TexelTarget(name="twin", enabled=True, source=src, page=p)])


def test_a_DISABLED_scenery_row_trips_no_hazard_gate_at_all(tmp_path):
    """A row that states an intent must not be a row that refuses: every gate keys on ENABLED, so an
    author can leave a hazardous cell in the file switched off and still build."""
    blob = build_scenery_container()
    p = _cell(blob, 320, 256)                                # spills, and would refuse if enabled
    b = RP.build(_spec_dict(blob, [{"name": p.name, "enabled": False}]), "?", blob=blob)
    assert b.patched == blob and not b.enabled


def test_the_STAGED_manifest_carries_the_hazard_verdicts_and_both_acknowledgements(tmp_path):
    """A cast report that cannot say which disclosures were live is a report nobody can audit after
    the fact -- and this lane's whole posture is that a refusal, a remedy and a disclosure are three
    different things."""
    blob = build_scenery_container()
    p = _cell(blob, 576, 256)
    src = _write_cell_png(tmp_path, blob, p, _bump_cell(p, _page_at(blob, p)))
    b = RP.build(_spec_dict(blob, [_row(p, src)]), str(tmp_path / "s.toml"), blob=blob)
    b.check = RP.self_check(b)
    man = RP.stage(b, root=tmp_path / "stage")
    rec = man["texels"][p.name]
    assert rec["kind"] == "scenery" and rec["bpp"] == 4 and rec["cell"] == [576, 256]
    assert set(rec["hazards"]) == {"multi-palette", "shared-read"}
    assert any("MULTI-PALETTE" in n for n in rec["hazard_notes"])
    assert rec["acknowledge_cotransform"] is False and rec["acknowledge_spill"] is False
    assert rec["covered_halfwords"] == p.hazards.covered_halfwords
    assert Path(man["previews"][0]).is_file(), "the preview renders at the cell's own depth"


def test_describe_DISCLOSES_the_per_target_hazard_verdicts(tmp_path):
    blob = build_scenery_container()
    p = _cell(blob, 704, 384)
    src = _write_cell_png(tmp_path, blob, p, _bump_cell(p, _page_at(blob, p)))
    b = RP.build(_spec_dict(blob, [_row(p, src)], effect=211), "?", blob=blob)
    b.check = RP.self_check(b)
    txt = "\n".join(RP.describe(b) + RP.check_lines(b))
    assert "hazard   : program-VRAM READ" in txt and "hazard   : LOWER HALF" in txt
    assert "(scenery, 8bpp)" in txt and "halfwords sampled" in txt
    assert "every hazard this cell carries is REFUSED, remedied or DISCLOSED" in txt
    assert "the page-cell map RE-DERIVES identically after the splice" in txt


# ---- the corpus-gated cases ----------------------------------------------------------------------
@needs_corpus
def test_ef211s_CAST_CELL_builds_clean_with_the_read_storeimage_disclosure(tmp_path):
    """THE CAST VEHICLE, through the whole gate stack.  ef211 (704,256) -- the Phoenix fire field, the
    one cell in the corpus whose upload path is already cast-proven on screen -- carries no hazard at
    all except the program-VRAM READ, and the direction law is what makes that a disclosure."""
    blob = (CORPUS / "ef211.bytes").read_bytes()
    p = RP.texel_page(blob, "cell.s0.x704_y256", 211)
    assert p.hazards.names == () and p.bpp == 8
    src = _write_cell_png(tmp_path, blob, p, _bump_cell(p, _page_at(blob, p)))
    b = RP.build({"reskin": {"effect": 211, "expect_sha256": hashlib.sha256(blob).hexdigest(),
                             "texel": [_row(p, src, expect_bpp=8, expect_cell=[704, 256])]}},
                 "?", blob=blob)
    b.check = RP.self_check(b)
    assert b.check.ok, [g.detail for g in b.check.gates if not g.ok]
    moved = [i for i in range(len(blob)) if blob[i] != b.patched[i]]
    assert min(moved) >= 0x11678 and max(moved) < 0x15678, "inside the cast cell, and nowhere else"
    note = "  ".join(b.enabled[0].hazard_notes)
    assert "program-VRAM READ" in note and "COVER: 8128 of 8192" in note
    assert not [n for n in b.enabled[0].hazard_notes if "SHARED READ" in n or "SPILL" in n]


@needs_corpus
def test_ef211s_CAST_2_lower_half_builds_and_its_UPPER_half_is_a_DISCLOSURE_not_a_refusal(tmp_path):
    """CAST 2, AND THE RECONCILIATION.  (576,384) is the clean 4bpp picture only the per-cell map can
    name.  Its upper half (576,256) is class C + class E3, which SYNTHESIS sec 1.1's remedy column
    makes EDITABLE WITH DISCLOSURE -- the document's appendix labels that cell "REFUSE", but that
    column is A1's `lawful` PREDICATE (which excludes multi-palette from its count of 56), not a gate
    verdict.  sec 1.1 is the row that says what the tool DOES, so the tool does that, and this is
    where the choice is visible instead of assumed."""
    blob = (CORPUS / "ef211.bytes").read_bytes()
    low = RP.texel_page(blob, "cell.s0.x576_y384", 211)
    assert (low.bpp, low.page_offset) == (4, 0x25678) and low.hazards.names == ("lower-half",)
    src = _write_cell_png(tmp_path, blob, low, _bump_cell(low, _page_at(blob, low)))
    b = RP.build({"reskin": {"effect": 211, "expect_sha256": hashlib.sha256(blob).hexdigest(),
                             "texel": [_row(low, src, expect_bpp=4, expect_cell=[576, 384])]}},
                 "?", blob=blob)
    b.check = RP.self_check(b)
    assert b.check.ok, [g.detail for g in b.check.gates if not g.ok]
    up = RP.texel_page(blob, "cell.s0.x576_y256", 211)
    assert up.hazards.multi_palette and up.hazards.shared_read
    src2 = _write_cell_png(tmp_path, blob, up, _bump_cell(up, _page_at(blob, up)), name="upper")
    b2 = RP.build({"reskin": {"effect": 211, "expect_sha256": hashlib.sha256(blob).hexdigest(),
                              "texel": [_row(up, src2, expect_bpp=4)]}}, "?", blob=blob)
    b2.check = RP.self_check(b2)
    assert b2.check.ok, [g.detail for g in b2.check.gates if not g.ok]
    note = "  ".join(b2.enabled[0].hazard_notes)
    assert "MULTI-PALETTE (class C)" in note and "SHARED READ" in note


@needs_corpus
def test_every_program_WRITE_container_in_the_corpus_refuses_EVERY_readable_cell():
    """The refusal, SWEPT rather than sampled: over all 15 write containers, every cell whose depth the
    container states is refused by the gate, and the three MoveImage cells are refused BY NAME."""
    seen, hard = 0, 0
    for ef, blob in _corpus_effects():
        if ef not in RP.PROGRAM_VRAM_WRITE_IDS:
            continue
        for p in RP.scenery_texel_pages(blob, ef):
            with pytest.raises(RP.RepaintError) as e:
                RP._gate_program_vram(p, "sweep")
            assert "PROGRAM-VRAM WRITE" in str(e.value)
            if "BY CELL" in str(e.value):
                hard += 1
                assert p.cell == RP.MOVEIMAGE_HARD_CELLS[ef]
            seen += 1
    assert seen, "the sweep actually visited the write containers"
    print("W6b program-VRAM sweep: %d readable cell(s) refused, %d BY CELL" % (seen, hard))
