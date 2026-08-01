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

import dataclasses
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
from ff9mapkit.summons import depth_attribution as DA
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
        # Z-ORDER, the measured stock convention (v0 v1 over v2 v3) -- a perimeter walk here would
        # make the kit's Z fan read the quad as a bowtie and the island's texel count stop being
        # the rect arithmetic the tests assert.
        for k, (u, v) in enumerate(((x0, y0), (x1, y0), (x0, y1), (x1, y1))):
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
    # the measured coverage census, reproduced through the kit: 65,298 of 98,304 sampled (66.4%).
    # Under the falsified perimeter fan this read 65,267 with holes [.., 33]: the bowtie's uncovered
    # wedges dropped 31 texels and mis-read 31 more as interior holes on part 5.
    assert sum(e["covered_texels"] for e in man["parts"]) == 65298
    assert [e["interior_holes"] for e in man["parts"]] == [0, 0, 62, 0, 12, 2]
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


def _uv_geom(tpage: int, clut: int, uv, second=(0, 0)) -> bytes:
    """One 16-byte ``so`` record + a GEOM block carrying ONE FT4 quad over the uv rect ``uv``.

    ``test_summon_reskin._so_geom`` builds an ``so``-bound GEOM with EMPTY pools, which is all a
    palette-attribution test needs -- but the scenery texel lane joins on UV COVER, so a model with no
    UVs samples nothing and every cell would read as depth-unknown.  This is that fixture plus the one
    thing this lane cannot do without.

    ``second`` is the record's SECOND array pair (W6b-3 iii), DEFAULTING to the ``(0, 0)`` this
    fixture has always written -- so every existing scenery assertion is byte-identical -- and it is a
    parameter only so a test can synthesise a MOVER without a second fixture.
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
    # Z-ORDER (v0 v1 over v2 v3), matching the measured stock convention -- see _creature_geom_payload
    for k, (u, v) in enumerate(((u0, v0), (u1, v0), (u0, v1), (u1, v1))):
        struct.pack_into("<H", g, p_uv + 2 * k, u | (v << 8))
    so = (struct.pack("<HHHH", 0x6F73, 1, 0x10, 0x0C) + struct.pack("<HH", tpage, clut)
          + struct.pack("<HH", second[0], second[1]))
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


def _so_multi_geom(parts, uv=(0, 0, 10, 10), second=None) -> bytes:
    """A **MULTI-PART** ``so`` record (``P = len(parts)``) + a UV-bearing GEOM block -- W6b-3's
    CHANNEL A fixture.

    ★ SYNTHESISED, NEVER COPIED: the header is
    ``struct.pack("<HHHH", 0x6F73, 1, 8 + 8P, 8 + 4P)`` and every pair is invented, so this file
    embeds no run of bytes out of a real ``ef*.bytes``.  The GEOM half is :func:`_uv_geom`'s, reused
    rather than re-typed, so a change to the scanner's acceptance law cannot leave this fixture behind.
    """
    P = len(parts)
    sec = list(second if second is not None else [(0, 0)] * P)
    assert len(sec) == P, "the second array is one pair per part -- that is what `arrayB` asserts"
    so = struct.pack("<HHHH", 0x6F73, 1, 8 + 8 * P, 8 + 4 * P)
    so += b"".join(struct.pack("<HH", tp, cw) for tp, cw in parts)
    so += b"".join(struct.pack("<HH", a, b) for a, b in sec)  # the SECOND array at +arrayB
    assert len(so) == 8 + 8 * P
    return so + _uv_geom(0, 0, uv)[0x10:]


def build_scenery_container(rects=SCEN_RECTS, models=SCEN_MODELS, id9: int = 0,
                            clut4=SCEN_CLUT4, extra_models: bytes = b"") -> bytes:
    """The scenery fixture: a creature-less container with real page rects and real UV-bound models.

    ``id9`` enables the id-9 alternate slot that lands on VRAM ``(320, 256)`` -- the same cell rect 5
    writes -- which is the CO-TRANSFORM shape (two writers, one cell) in miniature.

    ``extra_models`` appends RAW record+GEOM bytes to the id-6 payload, which is how a W6b-3
    MULTI-PART record joins the fixture without giving the ``(label, x, y, bpp, clut, uv)`` table a
    second shape it would then have to carry everywhere.
    """
    res = [(0, 0, _scenery_id0(rects, clut4)), (3, 0, bytes([0x55]) * SECTOR)]
    body = b"".join(_uv_geom(_tpage(x, y, bpp), 0 if cl is None else _clut_word(*cl), uv)
                    for _lbl, x, y, bpp, cl, uv in models) + extra_models
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
    # spelled as "only the last one" rather than a flat 6-element boolean list: a byte-literal
    # provenance scanner coerces `bool` (an `int`) sequences into bytes and false-positives on them.
    assert [m.spills for m in ms] == [False] * 5 + [True]


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
    # W6b-2: the EDIT surface names the SAME cells here, because nothing binds column 448 -- the
    # fixture's dark cell is dark on every channel.  The two are NOT the same objects, and that is the
    # honest part: under CENSUS_CHANNELS the hazard record carries no `page_depths` and no `bpp_hint`,
    # because a channel the caller declined to consult must not appear to have spoken.
    edit = RP.scenery_texel_pages(blob, 999)
    assert [(p.name, p.bpp, p.depth_source) for p in edit] == \
           [(p.name, p.bpp, p.depth_source) for p in pages]
    assert [r.name for r in RP.scenery_cell_refusals(blob, 999)] == [r.name for r in refused]
    assert pages[0].hazards.page_depths == () and pages[0].hazards.bpp_hint is None
    assert edit[0].hazards.page_depths == (8,), "the EDIT surface consulted channel G"
    assert RP.scenery_surface(blob, 999, channels=RP.CENSUS_CHANNELS)[0] == pages
    with pytest.raises(RP.RepaintError, match="unknown depth channel"):
        RP.scenery_surface(blob, 999, channels=("so-uv", "vibes"))


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
    assert RP.ART_LANES == ("indexed", "rgba", "direct15", "paint") == tuple(cli._SUMMON_ART_LANES)
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
    several records and one cell).

    ★ W6b-2 ADDS A SECOND VIEW AND PINS BOTH.  :data:`repaint.CENSUS_CHANNELS` is W6b-1's own set and
    is what ``scenery_surface`` defaults to, so **its numbers are byte-for-byte what they were** (187
    read / 2,385 dark) -- that is what keeps `w6b_gates` G6 and `w6q_gates` G1 measuring the
    population they were written about.  :data:`repaint.LICENSED_CHANNELS` is the EDIT surface, where
    channel G licenses 57 readerless cells and the two dual-depth classes take 22 + 8 out of the dark
    set into refusals with sharper names: ``187 + 2,385`` becomes ``187 + 57 + 2,298 + 22 + 8``.
    Both totals are the same 2,572, which is the only thing that proves nothing fell out of the walk.

    ⚠ AND THE SIX HAZARD POPULATIONS ARE MEASURED ON **BOTH** SURFACES, because they MOVE on one and
    saying so is the point.  ``multi-palette`` is class-C evidence and W6b-2 takes that evidence at the
    same granularity as the depth, so a readerless channel-G cell whose COLUMN is bound with 2-3 CLUTs
    discloses like any other class-C cell.  Pinning only the licensed number would hide the W6b-1
    identity; pinning only 25 was how the class-C cells stayed invisible in the first place.

    ★ **W6b-3 SPLITS THE TWO SURFACES FURTHER, AND ON PURPOSE.** The CENSUS half is still
    **187 / 2,385, byte for byte** -- that is the containment, and if it moves, ``bound_models`` or
    ``page_depth_view`` leaked. The EDIT half MOVES BY -6, because CHANNEL A holds VETO power: 12
    ``array-dual`` cells and the 2 ``array-vs-column`` cells refuse on any path that consults
    ``so-array``, and 6 of those 14 were being SERVED (4 by ``so-uv``, 2 by ``so-page``). ``187 + 57``
    becomes ``183 + 55``, and the 8 in-reach ``array-dual`` cells move out of ``depth-unknown``
    (2,298 -> 2,290) into a refusal with a sharper name. **The closure is what proves nothing fell
    out of the walk**, and it now closes over four hazard classes instead of two.
    """
    cells, read, dark = set(), set(), set()
    c_read, c_dark = set(), set()
    by_source = {s: set() for s in RP.DEPTH_SOURCES}
    dual = {"program-dual-depth": set(), "channel-g-dual-depth": set(),
            "spill-vs-own-page": set(),
            "array-dual-depth": set(), "array-vs-column-depth": set()}
    HZ = ("same-bytes-two-depths", "multi-palette", "shared-read", "spill-in", "spill-out",
          "co-transform")
    hz = {k: set() for k in HZ}
    c_hz = {k: set() for k in HZ}
    depths = {4: set(), 8: set(), 15: set()}
    for ef, blob in _corpus_effects():
        for pc in RS.page_cells(blob).values():
            cells.add((ef, pc.cell))
        # THE CENSUS VIEW -- `scenery_surface`'s own default, i.e. W6b-1 unchanged
        c_pages, c_refused = RP.scenery_surface(blob, ef)
        c_read |= {(ef, p.cell) for p in c_pages}
        c_dark |= {(ef, r.cell) for r in c_refused if r.klass == "depth-unknown"}
        for p in c_pages:
            for n in p.hazards.names:
                if n in c_hz:
                    c_hz[n].add((ef, p.cell))
        # THE EDIT SURFACE -- what an author actually gets
        pages, refused = RP.scenery_surface(blob, ef, channels=RP.LICENSED_CHANNELS)
        for r in refused:
            if r.klass == "depth-unknown":
                dark.add((ef, r.cell))
            elif r.klass in dual:
                dual[r.klass].add((ef, r.cell))
        for p in pages:
            k = (ef, p.cell)
            by_source[p.depth_source].add(k)
            if k in read:
                continue
            read.add(k)
            depths[p.bpp].add(k)
            for n in p.hazards.names:
                if n in hz:
                    hz[n].add(k)
    assert len(cells) == 2572, "the non-creature page-cell population"
    # ★ THE CENSUS DEFAULT IS W6b-1, BYTE FOR BYTE.  If this pair ever moves, three sibling gate
    # files are silently measuring a different population than the one they were written about.
    assert (len(c_read), len(c_dark)) == (187, 2385), "CENSUS_CHANNELS == W6b-1, unchanged"
    assert len(c_read) + len(c_dark) == len(cells)
    assert len(by_source["so-uv"]) == 183, \
        "W6b-1's 187, less the 4 CHANNEL A vetoes (3 array-dual + 1 array-vs-column)"
    assert len(by_source["so-page"]) == 55, \
        "CHANNEL G's 57, less the 2 CHANNEL A vetoes (1 array-dual + 1 array-vs-column)"
    assert len(by_source["so-array"]) == 0, "CHANNEL A stays SHUT without the acknowledgement"
    assert len(by_source["program"]) == 0, "CHANNEL P stays SHUT without the acknowledgement"
    assert len(read) == 238, "cells this lane hands back a picture for (183 + 55) -- 244 less the 6"
    assert len(dark) == 2290, "DEPTH-UNKNOWN after all three attribution channels have spoken"
    assert len(dual["program-dual-depth"]) == 22, "the program names these columns at TWO depths"
    assert len(dual["channel-g-dual-depth"]) == 8, "...and the `so` records name these at two"
    assert len(dual["spill-vs-own-page"]) == 2, "cells that HAD a depth and now have two"
    assert len(dual["array-dual-depth"]) == 12, "6 columns whose NOVEL array entries name TWO depths"
    assert len(dual["array-vs-column-depth"]) == 2, \
        "ef184 x448 -- the ONLY column where the incumbent and novel readings CONTRADICT"
    # ★ THE -6 IS THE ONE NON-ZERO ADDRESSABILITY DECISION IN THE RUNG, and it is stated as an
    # identity rather than trusted: 4 cells leave `so-uv` and 2 leave `so-page`, and every one of
    # them is inside the 14 CHANNEL A refuses.
    assert (187 - len(by_source["so-uv"])) + (57 - len(by_source["so-page"])) == 6
    veto = dual["array-dual-depth"] | dual["array-vs-column-depth"]
    assert (c_read - read) <= veto, "every cell the edit surface stopped serving is one CHANNEL A names"
    assert len(c_read - read) == 4, \
        "4 of the 6 withdrawals are CENSUS cells (`so-uv`); the other 2 were channel-G-only and were " \
        "never in the census surface at all"
    # THE ARITHMETIC CLOSES, and it is the closure -- not any single count -- that proves the walk
    # still visits every cell exactly once.  The 2 spill cells are deliberately NOT in this sum: they
    # are OUTSIDE the depth-unknown population entirely and are already inside `read`.
    assert (len(read) + len(dark) + len(dual["program-dual-depth"])
            + len(dual["channel-g-dual-depth"]) + len(dual["array-dual-depth"])
            + len(dual["array-vs-column-depth"])) == len(cells)
    assert 2385 - 57 - 22 - 8 - 8 == len(dark), \
        "W6b-1's 2,385, split by channel G, the two W6b-2 dual classes, and the 8 array-dual cells " \
        "whose column carried no incumbent depth at all (the other 4 were never in the dark set)"
    assert len(depths[15]) == 17, "the whole 15bpp surface the container states a depth for (14 + 3)"
    # ★ THE SIX W6b-1 HAZARD POPULATIONS, ON THE CENSUS SURFACE: every one of them is still its W6b-1
    # number.  This is the identity `w6b_gates` G6 and `w6q_gates` G1 are written about.
    assert len(c_hz["same-bytes-two-depths"]) == 17
    assert len(c_hz["multi-palette"]) == 25, "class C -- the display-palette rule"
    assert len(c_hz["shared-read"]) == 93, "class E3 -- a disclosure, not a refusal"
    assert len(c_hz["spill-in"]) == 36, "class F1 -- page scope is the wrong edit unit"
    assert len(c_hz["spill-in"] | c_hz["spill-out"]) == 70, "A2's UV-exact spill-touched set"
    assert len(c_hz["co-transform"]) == 24, "of the 34 multi-writer cells, the 24 that are READ"
    # ...and ON THE EDIT SURFACE: five are unmoved, because the 57 channel-G cells flow through every
    # one of those gates exactly as a read cell does.  The SIXTH moves by exactly 7, and that is a fix
    # rather than a drift: class-C evidence is now read at the granularity the DEPTH was read at, so a
    # readerless cell whose column carries 2-3 CLUT keys discloses instead of silently shipping one of
    # them.  A predicate that cannot fire on a whole surface is not a measurement of that surface.
    assert len(hz["same-bytes-two-depths"]) == 17
    assert len(hz["shared-read"]) == 90, \
        "93 less the 3 shared-read cells CHANNEL A vetoes (ef179 x448_y256, ef186 x576_y256/y384)"
    assert len(hz["spill-in"]) == 36
    assert len(hz["spill-in"] | hz["spill-out"]) == 70
    assert len(hz["co-transform"]) == 24
    assert len(hz["multi-palette"]) == 30, \
        "25 + the channel-G cells bound with >1 CLUT, less the one CHANNEL A withdraws"
    assert len(hz["multi-palette"] - c_hz["multi-palette"]) == 6
    assert all(k in by_source["so-page"] for k in hz["multi-palette"] - c_hz["multi-palette"]), \
        "every one of the 6 is a channel-G cell -- no read cell's class-C verdict moved"


@needs_corpus
def test_the_per_cell_map_unlocks_EXACTLY_the_twenty_lower_half_cells():
    """The rung's central claim, as a number.  A1 measured 56 lawful cells and marked 20 more
    UNADDRESSABLE because ``(tag, x)`` cannot name the lower half of a tall rect.  ``page_cells`` names
    them -- and W6b-2's channel G is the class that FILLS that named-but-empty space.

    ⚠ THREE PREDICATES, ALL PINNED, because the channel-G cells land in three buckets and a reader of
    one number alone would call the others a bug:

    * **all but one clear every REFUSAL**; 1 refuses on a program-VRAM write (ef038).  That is
      row 8's own re-spec -- *"the 57 cells build"* is FALSE;
    * **the hazard-CLEAN ones are counted separately from the class-C multi-palette DISCLOSURE**, so
      only the clean ones land in the buckets counted below.  The class-C ones are the cells whose
      COLUMN is bound with two or three CLUT keys: they were invisible while class-C evidence was read
      off READERS a readerless cell does not have, and making them visible is a fix, not a loss;
    * ``lower_half`` is a property of a WRITER's own upload, so a channel-G cell written by an **id-9
      alternate block** -- one whole 0x4000 upload that happens to sit at ``y = 384`` -- is not the
      lower half of anything and scores as ``upper``.  That is 2 of them.

    ★ **W6b-3 MOVES EVERY CHANNEL-G BUCKET BY THE SAME 2**, and only by those 2: ``so-page`` emits
    **55** on the edit surface rather than 57, because ef179 x448_y384 (``array-dual``) and ef184
    x448_y384 (``array-vs-column``) are VETOED by CHANNEL A. One of the two was a class-C cell, so
    the class-C bucket goes 7 -> 6 and the clean bucket 49 -> 48. **The W6b-1 halves (56 / 20) are
    untouched**, because W6b-1's own cells are ``so-uv`` and CHANNEL A vetoes 4 of those separately --
    which is why they are counted here by SUBTRACTING the channel-G sets rather than by a constant.
    """
    upper, lower, spill_out = set(), set(), set()
    g_upper, g_lower, g_all, g_multi = set(), set(), set(), set()
    for ef, blob in _corpus_effects():
        for p in RP.scenery_texel_pages(blob, ef):
            k, h = (ef, p.cell), p.hazards
            if p.depth_source == "so-page":
                g_all.add(k)
                if h.multi_palette:
                    g_multi.add(k)
            if k in upper | lower:
                continue
            if (not h.co_transform and not h.two_depths and not h.multi_palette
                    and not h.shared_read and not h.spill_in and h.program != "write"):
                (lower if h.lower_half else upper).add(k)
                if p.depth_source == "so-page":
                    (g_lower if h.lower_half else g_upper).add(k)
                if h.spill_out and not h.lower_half:
                    spill_out.add(k)
    assert len(spill_out) == 6, "LAWFUL != PAGE-SCOPE-SAFE: 6 of the lawful uppers are model-scope"
    assert len(g_all) == 55, \
        "CHANNEL G's gain on the EDIT surface: 57 named by `page_depth_view`, less the 2 CHANNEL A " \
        "VETOES (ef179 x448_y384 array-dual, ef184 x448_y384 array-vs-column).  The VIEW is unmoved " \
        "at 57 -- what moved is how many of them this lane is willing to EMIT"
    assert len(g_multi) == 6, \
        "...of which 6 sit on a column bound with MORE THAN ONE CLUT and disclose class C (7 before " \
        "CHANNEL A withdrew one of them).  A class-C predicate fed from READERS is False by " \
        "construction on a readerless cell, which would have shipped one of 2-3 renderings with no " \
        "disclosure and no alternate PNG"
    assert len(g_upper) + len(g_lower) == 48, \
        "CHANNEL G: 55 emit a depth, 54 clear every REFUSAL (1 refuses on ef038's program write) " \
        "and 48 of those are hazard-clean -- the other 6 are the class-C cells above"
    assert (len(g_upper), len(g_lower)) == (2, 46), \
        "and the 2 are id-9 alternate blocks at y=384: one whole upload, never a rect's lower half"
    # ★ THE W6b-1 HALVES ARE RE-DERIVED BY SUBTRACTION, NOT BY A CONSTANT -- so a channel-A veto on
    # a `so-uv` cell shows up HERE, in the W6b-1 number, instead of hiding inside a channel-G total.
    assert len(upper) - len(g_upper) == 55, \
        "A1's 56 lawful uppers, less the ONE `so-uv` cell CHANNEL A vetoes that was hazard-clean " \
        "(ef184 x448_y256; the other three `so-uv` vetoes carry `shared-read` and were never in " \
        "this bucket)"
    assert len(lower) - len(g_lower) == 20, "THE CELLS THE PER-VRAM-CELL MAP UNLOCKED IN W6b-1"
    assert (len(upper), len(lower)) == (57, 66), "...and the W6b-3 totals the two sum to"


@needs_corpus
def test_ef211s_cast_cell_derives_the_decision_documents_appendix_exactly():
    """The cast vehicle, cell by cell.  If this table ever stops matching, the artifact staged against
    it is aimed at bytes nobody re-checked."""
    blob = (CORPUS / "ef211.bytes").read_bytes()
    pages = {p.name: p for p in RP.scenery_texel_pages(blob, 211)}
    assert sorted(pages) == ["cell.s0.x576_y256", "cell.s0.x576_y384",
                             "cell.s0.x640_y256", "cell.s0.x640_y384",
                             "cell.s0.x704_y256", "cell.s0.x704_y384"]
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
    # ★ THE DOME, W6b-2's own cast vehicle -- and the one cell in the corpus that is simultaneously
    # depth-attributed by this rung, PROVEN DRAWN in-game (the cast-1c stripes banded the rolling-fire
    # dome through it) and free of every other hazard.  It has ZERO readers, which is exactly why the
    # census had to refuse it; channel G reads its COLUMN's own binding instead, and the depth is
    # INHERITED, never direct.
    dome = pages["cell.s0.x704_y384"]
    assert (dome.bpp, dome.depth_source, dome.depth_inherited) == (8, "so-page", True)
    assert dome.hazards.readers == () and dome.hazards.page_depths == (8,)
    assert dome.hazards.page_binders == (0x2b668,), "the SAME record that gave the fire cell its 8bpp"
    assert dome.palette_name == "pal.s0.x0_y247.e256", "the key comes from that record too"
    assert dome.hazards.names == ("lower-half",) and dome.hazards.program == "read"
    assert dome.hazards.program_depths == (), "ef211's program is SILENT here -- not wrong, silent"
    # ★ AND THE CELL NEXT DOOR, WHICH IS WHY CLASS-C EVIDENCE HAD TO MOVE TO THE COLUMN.  Column 640's
    # UPPER half is a class-C cell -- one index array, two renderings -- and its LOWER half is bound by
    # the SAME two records.  Read off `readers` the lower half reports `multi_palette = False` on
    # identical evidence, i.e. the kit would be LESS honest on the licensed path than on the census
    # one.  Both halves now name both keys, and `export_art` writes the `.as-` view for both.
    up, low = pages["cell.s0.x640_y256"], pages["cell.s0.x640_y384"]
    assert up.hazards.multi_palette and low.hazards.multi_palette
    assert up.hazards.palette_cells == ((80, 244), (96, 244))
    assert low.hazards.palette_cells == up.hazards.palette_cells, "the SAME two keys, one column"
    assert low.hazards.page_clut_cells[0] == (80, 244), "the DISPLAY key is the lowest-GEOM binder's"
    assert low.palette_name == up.palette_name and "multi-palette" in low.hazards.names
    assert [a.clut_cell for a in RP.alternate_palette_rows(blob, low, RS.palette_map(blob))] \
        == [(96, 244)], "a readerless cell still has its alternate rendering, and it is NAMED"
    # ...and the class-C DISCLOSURE names the other key.  Built from `readers` it printed the line and
    # then an EMPTY list -- telling an author a second rendering exists and refusing to say which.
    dis = "  ".join(RP._scenery_disclosures(
        RP.TexelTarget(name=low.name, enabled=True, source="", page=low)))
    assert "MULTI-PALETTE (class C): one index array, 2 renderings" in dis
    assert "CLUT (96, 244) (its `.as-x96_y244.png` view)" in dis
    dark = [r.name for r in RP.scenery_cell_refusals(blob, 211)]
    assert len(dark) == 6 and "cell.s0.x704_y384" not in dark, \
        "channel G moved the DOME and (640,384) out of the dark set; 8 - 2 = 6 remain"
    assert "cell.id9.s0.x768_y256" in dark


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
    assert (n[4], n[8], n[15]) == (76, 166, 17), \
        "the WHOLE round-trippable surface, per writer record -- if this population moves, the pass " \
        "above stopped covering what it used to and the count is the only thing that would say so.  " \
        "W6b-3: was (80, 168, 17); CHANNEL A's VETO withdraws 4 4bpp writer records (ef179 x448 and " \
        "ef184 x448) and 2 8bpp (ef186 x576) -- the same -6 the census pin records, seen from the " \
        "codec's side"
    assert (n[4] - 28, n[8] - 24, n[15] - 3) == (48, 142, 14), \
        "the two channels, still separable inside it: channel G contributes 28 + 24 + 3 = 55 writer " \
        "records and `so-uv` 48 + 142 + 14 = 204.  THE CODEC IS UNTOUCHED -- every one of them " \
        "round-trips at the depth its own channel states"
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


# ============================================================ (9) W6q: THE PAINT / QUANTIZE LANE
# RGBA in, INDICES out, ZERO CLUT bytes.  The three properties this lane is allowed to claim -- the
# no-op is EXACT, determinism is STRUCTURAL, the approximation is DISCLOSED per texel -- each get a
# test, and every refusal gets a NON-OVER-FIRE TWIN, because that is the half that usually goes
# missing.
def _paint_row(name, src, **extra):
    d = {"name": name, "source_paint": str(src), "enabled": True, "acknowledge_quantize": True}
    d.update(extra)
    return d


def _repaint_pixels(src, fn):
    """Rewrite a paint PNG through ``fn(i, (r,g,b,a)) -> (r,g,b,a)``.  Pillow-only, no kit code, so a
    test that fakes an author's edit cannot accidentally exercise the codec twice."""
    from PIL import Image
    with Image.open(str(src)) as im:
        px = list(im.convert("RGBA").tobytes())
        size = im.size
    pts = [tuple(px[4 * i:4 * i + 4]) for i in range(size[0] * size[1])]
    out = Image.new("RGBA", size)
    out.putdata([fn(i, p) for i, p in enumerate(pts)])
    out.save(str(src))


def _dup_entry(blob: bytes, page, keep: int, into: int) -> bytes:
    """Make ``words[into]`` a byte-for-byte DUPLICATE of ``words[keep]`` in the container itself.

    The container is the authority, so the ambiguity a test needs has to be IN the container -- a
    fixture that faked it in a local variable would be testing a different function.
    """
    b = bytearray(blob)
    w = struct.unpack_from("<H", b, page.clut_offset + 2 * keep)[0]
    struct.pack_into("<H", b, page.clut_offset + 2 * into, w)
    return bytes(b)


def test_the_render_read_identity_holds_for_all_32_five_bit_values():
    """THE COMPOSITION THAT MAKES THE LANE POSSIBLE, and it is not a coincidence to rely on quietly:
    the paint file is RENDERED with the SCALE decode (``bgr555_rgba``, white = 255 -- what every
    preview already shows the author) and READ back with the SHIFT (``direct15_word``).  Two
    different maps; their composition must be the identity or the no-op dies."""
    assert all(((v * 255 // 31) >> 3) == v for v in range(32)), "the scale->shift round trip"
    bad = [w for w in range(0x8000)
           if w and KT.direct15_word(*(KT.bgr555_rgba(w)[:3]), 0) != w]
    assert bad == [], "%d of 32,767 non-cutout words failed the render/read round trip" % len(bad)
    # ...and the cutout word is the one deliberate exception: it renders alpha 0, so ALPHA carries it
    assert KT.bgr555_rgba(0) == (0, 0, 0, 0)


def test_export_art_paint_writes_paint_swatch_and_manifest_records(tmp_path):
    """W6q-1.  Both formats ship side by side, per page -- the choice is per ROW, not per export."""
    blob = build_texel_container(nparts=2)
    man = RP.export_art(blob, 999, tmp_path, lane="paint")
    assert man["lane"] == "paint"
    # THE LINE NO DESIGN NAMED: a lane that left `pages =` reading `== "indexed"` would silently
    # export SCENERY ONLY, with no error and no empty directory.
    assert [e["name"] for e in man["parts"]] == ["tex.part0", "tex.part1"]
    for e in man["parts"]:
        assert e["paint_png"] == "%s.paint.png" % e["name"]
        assert e["swatch_png"] == "%s.swatch.png" % e["name"]
        assert e["render_key"] == RP.PAINT_RENDER_KEY == "bgr555_rgba"
        assert (tmp_path / e["png"]).is_file(), "the EXACT indexed file still ships beside it"
        assert (tmp_path / e["paint_png"]).is_file()
        assert (tmp_path / e["swatch_png"]).is_file()
        assert e["page_sha256"] == hashlib.sha256(_page_bytes(blob, e["name"])).hexdigest()
    # the scaffold emits BOTH source lines with exactly one live, so the lane is a one-line switch
    import tomllib
    with open(tmp_path / RP.SCAFFOLD_NAME, "rb") as fh:
        doc = tomllib.load(fh)
    rows = doc["reskin"]["texel"]
    assert all("source_paint" in r and "source" not in r for r in rows)
    assert all(r["acknowledge_quantize"] is False and r["enabled"] is False for r in rows)
    text = (tmp_path / RP.SCAFFOLD_NAME).read_text(encoding="utf-8")
    assert "# source     =" in text and "INCUMBENT LOCK" in text
    assert "# measured:" in text and "distinct colours" in text
    # ...and an indexed export is UNCHANGED by all of it
    man_i = RP.export_art(blob, 999, tmp_path / "i", lane="indexed")
    assert all(not e["paint_png"] and not e["render_key"] for e in man_i["parts"])
    assert not (tmp_path / "i" / "tex.part0.paint.png").exists()


def test_paint_lane_export_round_trips_every_page_it_wrote(tmp_path):
    """THE NO-OP IS EXACT -- the mirror of the indexed lane's own round-trip gate.  Export ->
    paint-lane import -> the container's own bytes, byte for byte, with nothing painted."""
    blob = build_texel_container(nparts=3)
    RP.export_art(blob, 999, tmp_path, lane="paint")
    pmap = RS.palette_map(blob, effect=999)
    for p in RP.creature_texel_pages(blob):
        stock = blob[p.page_offset:p.page_offset + p.page_bytes]
        words = RP.palette_words(blob, p)
        raw, cen = RP.read_paint_png(tmp_path / ("%s.paint.png" % p.name), p, words,
                                     RP.texel_view(p, stock),
                                     RP.alternate_palette_rows(blob, p, pmap))
        assert raw == stock, "%s: an unedited re-import moved bytes" % p.name
        assert cen["approximated"] == 0 and cen["exact"] == cen["opaque"]
        assert cen["cutout_punch"] == 0 and cen["cutout_fill"] == 0


def test_the_incumbent_rule_is_what_makes_the_no_op_exact(tmp_path):
    """THE INCUMBENT LOCK, with its NEGATIVE half stated so the assertion cannot go vacuous: a texel
    sitting on the NON-LOWEST member of a duplicate group keeps its own index, AND a lowest-index
    tie-break would provably have moved it."""
    blob = build_texel_container(nparts=1)
    p0 = RP.texel_page(blob, "tex.part0")
    keep, into = 5, 200
    blob = _dup_entry(blob, p0, keep, into)
    stock = bytearray(_page_bytes(blob, "tex.part0"))
    stock[0] = into                                        # a texel on the NON-lowest member
    b2 = bytearray(blob)
    b2[p0.page_offset:p0.page_offset + p0.page_bytes] = stock
    blob = bytes(b2)
    p = RP.texel_page(blob, "tex.part0")
    words = RP.palette_words(blob, p)
    assert words[keep] == words[into] and keep < into, "the fixture really is ambiguous"
    RP.export_art(blob, 999, tmp_path, lane="paint")
    raw, cen = RP.read_paint_png(tmp_path / "tex.part0.paint.png", p, words,
                                 RP.texel_view(p, bytes(stock)))
    assert raw[0] == into, "the INCUMBENT won, not the lowest index"
    assert raw == bytes(stock)
    # THE NEGATIVE HALF: without the incumbent term the lowest member would have won and the byte
    # would have moved -- which is exactly the 1,844-of-16,384 failure the `rgba` refusal quotes.
    naive = min(i for i in range(len(words)) if words[i] == words[into])
    assert naive == keep != into
    assert cen["ambiguous"] >= 1


def test_quantize_is_deterministic_under_a_permuted_palette_scan(tmp_path):
    """DETERMINISM IS STRUCTURAL: a total order over UNIQUE indices, integer arithmetic only, and no
    set or dict iteration in any decision path.  Two runs of the same art are byte-equal, and every
    texel that moved landed on ONE stated member of the tie."""
    blob = build_texel_container(nparts=1)
    p = RP.texel_page(blob, "tex.part0")
    blob = _dup_entry(_dup_entry(blob, p, 7, 90), p, 7, 180)     # a 3-way tie
    words = RP.palette_words(blob, p)
    stock = _page_bytes(blob, "tex.part0")
    RP.export_art(blob, 999, tmp_path, lane="paint")
    src = tmp_path / "tex.part0.paint.png"
    _repaint_pixels(src, lambda i, c: (KT.bgr555_rgba(words[7])[:3] + (255,)
                                       if 100 <= i < 400 else c))
    a, _ = RP.read_paint_png(src, p, words, RP.texel_view(p, stock))
    b, _ = RP.read_paint_png(src, p, words, RP.texel_view(p, stock))
    assert a == b
    c, _ = RP.read_paint_png(src, p, tuple(words), RP.texel_view(p, stock))
    assert a == c
    moved = {a[i] for i in range(len(a)) if a[i] != stock[i]}
    assert moved <= {7}, "the total order picked one member, deterministically: %s" % moved


def test_quantize_refuses_partial_alpha_naming_the_texel(tmp_path):
    blob = build_texel_container(nparts=1)
    p = RP.texel_page(blob, "tex.part0")
    RP.export_art(blob, 999, tmp_path, lane="paint")
    src = tmp_path / "tex.part0.paint.png"
    _repaint_pixels(src, lambda i, c: (c[0], c[1], c[2], 128) if i in (300, 301) else c)
    with pytest.raises(RP.RepaintError) as e:
        RP.read_paint_png(src, p, RP.palette_words(blob, p),
                          RP.texel_view(p, _page_bytes(blob, "tex.part0")))
    msg = str(e.value)
    assert "(44,2)" in msg, msg                       # texel 300 == (300 % 128, 300 // 128)
    assert "alpha 128" in msg and "2 texel(s)" in msg and "CUTOUT FLAG" in msg


def test_quantize_refuses_when_the_row_has_no_transparent_entry(tmp_path):
    """R12, and it quotes ``MINT_CLUT_REASON`` VERBATIM -- the constant's real call site.  A reason
    nothing quotes is a wish."""
    blob = build_texel_container(nparts=1)
    p0 = RP.texel_page(blob, "tex.part0")
    b = bytearray(blob)
    struct.pack_into("<H", b, p0.clut_offset, 0x1234)          # entry 0 stops being the hole
    blob = bytes(b)
    p = RP.texel_page(blob, "tex.part0")
    words = RP.palette_words(blob, p)
    assert RP.transparent_indices(words) == ()
    RP.export_art(blob, 999, tmp_path, lane="paint")
    src = tmp_path / "tex.part0.paint.png"
    _repaint_pixels(src, lambda i, c: (0, 0, 0, 0) if i == 900 else c)
    with pytest.raises(RP.RepaintError) as e:
        RP.read_paint_png(src, p, words, RP.texel_view(p, _page_bytes(blob, "tex.part0")))
    msg = str(e.value)
    assert "45 of 147" in msg and "0 of 93" in msg
    assert RP.MINT_CLUT_REASON in msg, "the deferral reason is quoted VERBATIM"


def test_quantize_refuses_source_and_source_paint_together(tmp_path):
    blob = build_texel_container(nparts=1)
    src = _write_png(tmp_path, blob, "tex.part0", _page_bytes(blob, "tex.part0"))
    with pytest.raises(RP.RepaintError, match="two formats of record for one page"):
        RP.build(_spec_dict(blob, [{"name": "tex.part0", "source": str(src),
                                    "source_paint": str(src), "acknowledge_quantize": True}]),
                 str(tmp_path / "x_reskin.toml"), blob=blob)


def test_quantize_refuses_on_a_15bpp_cell_and_names_direct15(tmp_path):
    blob = build_scenery_container()
    man = RP.export_art(blob, 999, tmp_path, lane="direct15")
    e = man["scenery"][0]
    assert e["bpp"] == 15
    with pytest.raises(RP.RepaintError) as ex:
        RP.build({"reskin": {"effect": 999, "allow_unguarded": True,
                             "texel": [_paint_row(e["name"], tmp_path / e["png"])]}},
                 str(tmp_path / "x_reskin.toml"), blob=blob)
    msg = str(ex.value)
    assert "65,536/65,536" in msg and "--art-lane direct15" in msg and "indexes NO palette" in msg


def test_quantize_refuses_without_the_literal_boolean_acknowledgement(tmp_path):
    """R3, plus THE ``_ack_bool`` LAW: ``acknowledge_quantize = "true"`` (the STRING) must REFUSE,
    never arm.  A safety acknowledgement is stated, never inferred from a truthy string."""
    blob = build_texel_container(nparts=1)
    RP.export_art(blob, 999, tmp_path, lane="paint")
    src = tmp_path / "tex.part0.paint.png"
    row = _paint_row("tex.part0", src)
    row.pop("acknowledge_quantize")
    with pytest.raises(RP.RepaintError) as e:
        RP.build(_spec_dict(blob, [row]), str(tmp_path / "x_reskin.toml"), blob=blob)
    msg = str(e.value)
    assert "APPROXIMATES" in msg and "acknowledge_quantize = true" in msg
    assert "MEASURED on THIS art" in msg and "worst d^2" in msg
    row["acknowledge_quantize"] = "true"
    with pytest.raises(RP.RepaintError, match="must be a BOOLEAN"):
        RP.build(_spec_dict(blob, [row]), str(tmp_path / "x_reskin.toml"), blob=blob)


def test_quantize_is_not_spelled_quantize(tmp_path):
    """The shipped spelling is ``source_paint``.  ``quantize`` and ``mint_clut`` stay UNKNOWN keys on
    all three tables -- which is what keeps ``w6b_gates.py``'s own assertion green, verbatim."""
    blob = build_texel_container(nparts=1)
    for key in ("quantize", "mint_clut"):
        assert key not in RP._TEXEL_KEYS and key not in RS._TARGET_KEYS
        assert key not in RS._RESKIN_KEYS
        row = {"name": "tex.part0", "source": "x.png"}
        row[key] = True
        with pytest.raises(RP.RepaintError, match="unknown key"):
            RP.build(_spec_dict(blob, [row]), "?", blob=blob)
    for key in ("source_paint", "acknowledge_quantize", "acknowledge_recoloured_palette"):
        assert key in RP._TEXEL_KEYS


def test_dither_refuses_by_name_and_names_the_better_workflow(tmp_path, capsys):
    """R10.  It is DECLARED so it can refuse BY NAME rather than not exist -- and the fix it names is
    strictly better than the thing refused."""
    blob = build_texel_container(nparts=1)
    ef = tmp_path / "ef999.bytes"
    ef.write_bytes(blob)
    rc, cap = _run(["summon-reskin", "export-art", "--ef", "999", "--from", str(ef),
                    "--out", str(tmp_path / "art"), "--art-lane", "paint", "--dither"], capsys)
    assert rc == 2
    assert "BREAKS THE NO-OP" in cap.err and "5-BIT depth" in cap.err and "sparkle" in cap.err
    # ...ON EVERY SUB-VERB, `scaffold` INCLUDED.  `scaffold` returns early, so a refusal placed after
    # its branch would be silently ignored there -- which is precisely the silently-ignored-flag shape
    # W6q-0 exists to eliminate, reintroduced by the flag that exists to refuse.
    rc2, cap2 = _run(["summon-reskin", "scaffold", "--ef", "999", "--from", str(ef),
                      "--out", str(tmp_path / "s.toml"), "--dither"], capsys)
    assert rc2 == 2 and "BREAKS THE NO-OP" in cap2.err
    assert not (tmp_path / "s.toml").exists(), "a refused sub-verb wrote a file"


def test_the_paint_lane_builds_and_writes_zero_clut_bytes(tmp_path):
    """THE WHOLE SHIPPED GATE STACK RUNS UNCHANGED on a paint build, because the lane adds exactly
    ONE branch in front of the existing dispatch and touches no other."""
    blob = build_texel_container(nparts=2)
    RP.export_art(blob, 999, tmp_path, lane="paint")
    p = RP.texel_page(blob, "tex.part0")
    words = RP.palette_words(blob, p)
    src = tmp_path / "tex.part0.paint.png"
    live = [i for i, w in enumerate(words) if w][3]
    _repaint_pixels(src, lambda i, c: (KT.bgr555_rgba(words[live])[:3] + (255,))
                    if (2000 <= i < 2100 and c[3] == 255) else c)
    b = RP.build(_spec_dict(blob, [_paint_row("tex.part0", src)]),
                 str(tmp_path / "x_reskin.toml"), blob=blob)
    b.check = RP.self_check(b)
    assert b.check.ok, [g.detail for g in b.check.gates if not g.ok]
    zero = next(g for g in b.check.rules if "ZERO CLUT bytes" in g.name)
    assert zero.ok and "0 byte(s)" in zero.detail
    t = b.enabled[0]
    assert t.quantized and t.census["opaque"] and t.census["exact"]
    assert 0 < len(t.changed) <= 100
    # the census reaches `plan`'s output and the staged manifest, and stays JSON-safe there
    assert any("QUANTIZE" in ln for ln in RP.describe(b))
    assert "dmap" in t.census and "dmap" not in RP.census_record(t.census)
    json.dumps(RP.census_record(t.census))


def test_the_cutout_law_still_counts_both_directions_under_quantize(tmp_path):
    """ALPHA GOVERNS, so every crossing in the output is one the author DREW -- and the shipped cutout
    gate then counts it exactly as it does for an indexed row, with no change to that gate at all."""
    blob = build_texel_container(nparts=1)
    RP.export_art(blob, 999, tmp_path, lane="paint")
    src = tmp_path / "tex.part0.paint.png"
    _repaint_pixels(src, lambda i, c: (0, 0, 0, 0) if (5000 <= i < 5010) else c)
    with pytest.raises(RP.RepaintError) as e:
        RP.build(_spec_dict(blob, [_paint_row("tex.part0", src)]),
                 str(tmp_path / "x_reskin.toml"), blob=blob)
    assert "THE CUTOUT LAW" in str(e.value) and "10 punched" in str(e.value)
    b = RP.build(_spec_dict(blob, [_paint_row("tex.part0", src,
                                              acknowledge_cutout_reshape=True)]),
                 str(tmp_path / "x_reskin.toml"), blob=blob)
    assert (b.enabled[0].cutout_punch, b.enabled[0].cutout_fill) == (10, 0)
    assert b.enabled[0].census["cutout_punch"] == 10


# ---- W6q-3: the alternate-split refusal and the composed-palette refusal, each with its twin ----
def _class_c(blob):
    """The fixture's class-C cell: ONE index array read through TWO different 16-entry keys."""
    p = RP.texel_page(blob, "cell.s0.x576_y256", 999)
    assert p.bpp == 4 and len({r.clut_cell for r in p.hazards.readers}) == 2
    return p


def test_quantize_refuses_an_alternate_split_tie_by_name(tmp_path):
    """THE BLOCKING GRAFT.  A genuine edit whose surviving candidate set renders as >= 2 DIFFERENT
    words in the cell's other declared key REFUSES, and there is no acknowledge key: an author's own
    index choice is a choice and is disclosed, but the TOOL's choice, in a picture the author was
    never shown, must not be silently wrong."""
    blob = build_scenery_container()
    p = _class_c(blob)
    blob = _dup_entry(blob, p, 3, 9)                  # entries 3 and 9 now carry ONE word...
    p = _class_c(blob)
    words = RP.palette_words(blob, p)
    alts = RP.alternate_palette_rows(blob, p, RS.palette_map(blob, effect=999))
    assert len(alts) == 1 and alts[0].words[3] != alts[0].words[9], "...but SPLIT in the other key"
    stock = blob[p.page_offset:p.page_offset + p.page_bytes]
    idx = list(RP.texel_view(p, stock))
    RP.export_art(blob, 999, tmp_path, lane="paint")
    src = tmp_path / ("%s.paint.png" % p.name)
    victim = next(k for k in range(len(idx)) if idx[k] not in (3, 9) and words[idx[k]])
    _repaint_pixels(src, lambda i, c: (KT.bgr555_rgba(words[3])[:3] + (255,)) if i == victim else c)
    with pytest.raises(RP.RepaintError) as e:
        RP.read_paint_png(src, p, words, idx, alts)
    msg = str(e.value)
    assert "ALTERNATE-SPLIT TIE" in msg and "298 of 365" in msg and "11 of 16" in msg
    assert "no acknowledge key" in msg and "THAT THE CONTAINER DECLARES" in msg
    assert "the swatch marks them" in msg
    # THE TAMPER: with the alternate loop removed the build succeeds -- and the OTHER reader's
    # picture silently changes, which is the whole thing the refusal is protecting.
    raw, _cen = RP.read_paint_png(src, p, words, idx, ())
    nv = RP.texel_view(p, raw)
    assert any(alts[0].words[nv[k]] != alts[0].words[idx[k]] for k in range(len(idx)))
    # EDIT-SCOPED: the same page with nothing painted is exempt, because the incumbent survives
    RP.export_art(blob, 999, tmp_path / "clean", lane="paint")
    back, _ = RP.read_paint_png(tmp_path / "clean" / ("%s.paint.png" % p.name), p, words, idx, alts)
    assert back == stock


def test_quantize_builds_when_the_tie_is_alternate_safe(tmp_path):
    """...AND IT DOES NOT OVER-FIRE.  The same class of edit on a class-C cell with ZERO split
    duplicate groups builds green -- the non-over-fire twin, which is the half that goes missing."""
    blob = build_scenery_container()
    p = _class_c(blob)
    words = RP.palette_words(blob, p)
    assert len(set(words)) == len(words), "this fixture row has no duplicate word at all"
    alts = RP.alternate_palette_rows(blob, p, RS.palette_map(blob, effect=999))
    stock = blob[p.page_offset:p.page_offset + p.page_bytes]
    idx = list(RP.texel_view(p, stock))
    RP.export_art(blob, 999, tmp_path, lane="paint")
    src = tmp_path / ("%s.paint.png" % p.name)
    live = [i for i, w in enumerate(words) if w]
    _repaint_pixels(src, lambda i, c: (KT.bgr555_rgba(words[live[2]])[:3] + (255,))
                    if (1000 <= i < 1200 and c[3] == 255) else c)
    raw, cen = RP.read_paint_png(src, p, words, idx, alts)
    assert raw != stock and cen["alt_checked"] == 0


def _dup_entry_at(blob: bytes, off: int, keep: int, into: int) -> bytes:
    """:func:`_dup_entry` against an ARBITRARY palette offset -- used to duplicate the SAME pair in
    the ALTERNATE row, which is what makes a duplicate group non-split rather than split."""
    b = bytearray(blob)
    struct.pack_into("<H", b, off + 2 * into, struct.unpack_from("<H", b, off + 2 * keep)[0])
    return bytes(b)


def test_quantize_RUNS_the_alternate_split_check_and_PASSES_on_a_non_split_group(tmp_path):
    """★ THE PASS PATH -- the half both non-over-fire proofs leave untouched.

    ``test_quantize_builds_when_the_tie_is_alternate_safe`` and the creature-page test above both
    assert that the check NEVER RAN, so between them they prove the refusal CANNOT fire, not that it
    DISCRIMINATES.  This one puts a real two-member candidate set in front of it -- a duplicate group
    that carries ONE word in the alternate key as well -- and proves the loop ran, found no split, and
    let the edit through.  Without it the whole ``alt_checked`` instrument (the one OPEN RISK 1 asks
    the implementer to report) is only ever observed at 0.
    """
    blob = build_scenery_container()
    p = _class_c(blob)
    pmap = RS.palette_map(blob, effect=999)
    alt0 = RP.alternate_palette_rows(blob, p, pmap)[0]
    apal = pmap.by_name(alt0.palette_name)
    blob = _dup_entry(blob, p, 3, 9)                    # one word in the EDITABLE row...
    blob = _dup_entry_at(blob, apal.off, 3, 9)          # ...and one word in the ALTERNATE row too
    p = _class_c(blob)
    words = RP.palette_words(blob, p)
    alts = RP.alternate_palette_rows(blob, p, RS.palette_map(blob, effect=999))
    assert len(alts) == 1 and words[3] == words[9] and words[3]
    assert alts[0].words[3] == alts[0].words[9], "the group must NOT split, or this is G5's fixture"
    assert sum(1 for w in words if (w & 0x7FFF) == (words[3] & 0x7FFF)) == 2, \
        "exactly the group carries this colour, so the candidate set IS the group"
    stock = blob[p.page_offset:p.page_offset + p.page_bytes]
    idx = list(RP.texel_view(p, stock))
    RP.export_art(blob, 999, tmp_path, lane="paint")
    src = tmp_path / ("%s.paint.png" % p.name)
    victim = next(k for k in range(len(idx)) if idx[k] not in (3, 9) and words[idx[k]])
    _repaint_pixels(src, lambda i, c: (KT.bgr555_rgba(words[3])[:3] + (255,)) if i == victim else c)
    raw, cen = RP.read_paint_png(src, p, words, idx, alts)
    assert cen["alt_checked"] >= 1, "THE CHECK MUST HAVE RUN -- otherwise this proves nothing"
    assert raw != stock and RP.texel_view(p, raw)[victim] == 3
    # ...and the SAME edit against a SPLIT version of that group refuses: one fixture, both verdicts.
    split_blob = _dup_entry_at(blob, apal.off, 0, 9)    # break the alternate's half of the pair
    salts = RP.alternate_palette_rows(split_blob, p, RS.palette_map(split_blob, effect=999))
    assert salts[0].words[3] != salts[0].words[9]
    with pytest.raises(RP.RepaintError, match="ALTERNATE-SPLIT TIE"):
        RP.read_paint_png(src, p, words, idx, salts)


def test_the_alternate_split_branch_is_structurally_unreachable_on_a_creature_page():
    """SCOPING DECISION 3, stated in the code rather than discovered: an id-4 page is uploaded by
    PART index and carries its own row of the id-4 CLUT strip, so it has no alternate key at all --
    93 of the corpus's 240 lawful surfaces are outside this branch by construction."""
    blob = build_texel_container(nparts=2)
    pmap = RS.palette_map(blob, effect=999)
    for p in RP.creature_texel_pages(blob):
        assert p.hazards is None
        assert RP.alternate_palette_rows(blob, p, pmap) == ()


def test_quantize_refuses_a_paint_row_whose_palette_this_spec_recolours(tmp_path):
    """R9.  Under the INDEXED lane the author authored INDICES, so a recoloured row simply recolours
    their picture; under quantize they authored COLOURS, so a recoloured row silently re-decides
    which index each of them becomes."""
    blob = build_texel_container(nparts=2)
    RP.export_art(blob, 999, tmp_path, lane="paint")
    src = tmp_path / "tex.part0.paint.png"
    spec = _spec_dict(blob, [_paint_row("tex.part0", src)],
                      targets=[{"name": "creature.part0", "hue_rotate": 40.0}])
    b0 = RS.build(spec, "?", blob=blob)
    assert b0.patched != blob, "the CLUT target must ACTUALLY move entries, or the gate is vacuous"
    with pytest.raises(RP.RepaintError) as e:
        RP.build(spec, str(tmp_path / "x_reskin.toml"), blob=blob, base=b0.patched)
    msg = str(e.value)
    assert "THE RECOLOURED-PALETTE REFUSAL" in msg and "creature.part0" in msg
    assert "IN THIS SPEC" in msg and "acknowledge_recoloured_palette = true" in msg
    # ...and it is a SEPARATE refusal from the page-sha guard, with its own fix
    assert "re-export with `--art-lane paint --from" in msg
    spec["reskin"]["texel"][0]["acknowledge_recoloured_palette"] = True
    b = RP.build(spec, str(tmp_path / "x_reskin.toml"), blob=blob, base=b0.patched)
    assert any("acknowledge_recoloured_palette = true" in n for n in b.enabled[0].hazard_notes)


def test_the_recoloured_palette_refusal_is_CLEARED_by_its_own_first_named_fix(tmp_path):
    """★ LAW 2 IS NOT "A REFUSAL NAMES A FIX", IT IS "A REFUSAL NAMES A FIX THAT WORKS".

    R9's first named fix is *build the CLUT half first and re-export with
    ``--art-lane paint --from <the staged container>``*.  Taking it literally used to land on the
    ART-DRIFT refusal instead -- the manifest then records the STAGED container's sha, and the drift
    guard compared it against STOCK -- so ``acknowledge_recoloured_palette`` was the only way through
    and the message pointed at a dead end.  The predicate is now *"was the art rendered against the
    row it is being mapped onto"*, measured from the manifest's own whole-container sha256, so the
    named fix clears the gate and the acknowledgement stays the deliberate SECOND answer.
    """
    blob = build_texel_container(nparts=2)
    spec_clut = {"reskin": {"effect": 999, "label": "clut",
                            "expect_sha256": hashlib.sha256(blob).hexdigest(),
                            "target": [{"name": "creature.part0", "hue_rotate": 40.0}]}}
    staged = RS.build(spec_clut, "?", blob=blob)
    assert staged.patched != blob, "the CLUT half must ACTUALLY move entries"

    # (a) art exported from STOCK, mapped onto the recoloured row -> REFUSES, naming the fix
    stock_art = tmp_path / "from-stock"
    RP.export_art(blob, 999, stock_art, lane="paint")
    spec = _spec_dict(blob, [_paint_row("tex.part0", stock_art / "tex.part0.paint.png")],
                      targets=[{"name": "creature.part0", "hue_rotate": 40.0}])
    with pytest.raises(RP.RepaintError) as e:
        RP.build(spec, str(tmp_path / "x_reskin.toml"), blob=blob, base=staged.patched)
    assert "THE RECOLOURED-PALETTE REFUSAL" in str(e.value)
    assert "re-export with `--art-lane paint --from" in str(e.value)

    # (b) THE NAMED FIX, taken literally: re-export --from the staged container and re-point the row
    base_art = tmp_path / "from-base"
    RP.export_art(staged.patched, 999, base_art, lane="paint")
    man = json.loads((base_art / RP.ART_MANIFEST).read_text(encoding="utf-8"))
    assert man["stock_sha256"] == hashlib.sha256(staged.patched).hexdigest()
    spec2 = _spec_dict(blob, [_paint_row("tex.part0", base_art / "tex.part0.paint.png")],
                       targets=[{"name": "creature.part0", "hue_rotate": 40.0}])
    b = RP.build(spec2, str(tmp_path / "x_reskin.toml"), blob=blob, base=staged.patched)
    b.check = RP.self_check(b)
    assert b.check.ok, [g.detail for g in b.check.gates if not g.ok]
    assert not b.enabled[0].changed, "an unedited re-export of the COMPOSED row is still a no-op"
    assert any("RE-EXPORTED against those bytes" in n for n in b.enabled[0].hazard_notes)
    assert not b.enabled[0].ack_recoloured, "the fix cleared it WITHOUT the acknowledgement"

    # ...and the widening is PAINT-SCOPED: the indexed lane still demands the stock sha
    idx_src = _write_png(tmp_path / "from-base", blob, "tex.part0", _page_bytes(blob, "tex.part0"))
    with pytest.raises(RP.RepaintError, match="ART DRIFT"):
        RP.build(_spec_dict(blob, [{"name": "tex.part0", "source": str(idx_src)}]),
                 str(tmp_path / "x_reskin.toml"), blob=blob, base=staged.patched)


def test_the_recoloured_palette_refusal_does_not_over_fire_on_another_palette(tmp_path):
    """The twin: a ``[[reskin.target]]`` on a DIFFERENT palette than the paint page's builds green.
    The verdict is a BYTE comparison of THIS page's own row, never "any CLUT target exists"."""
    blob = build_texel_container(nparts=2)
    RP.export_art(blob, 999, tmp_path, lane="paint")
    spec = _spec_dict(blob, [_paint_row("tex.part0", tmp_path / "tex.part0.paint.png")],
                      targets=[{"name": "creature.part1", "hue_rotate": 40.0}])
    b0 = RS.build(spec, "?", blob=blob)
    assert b0.patched != blob
    b = RP.build(spec, str(tmp_path / "x_reskin.toml"), blob=blob, base=b0.patched)
    b.check = RP.self_check(b)
    assert b.check.ok, [g.detail for g in b.check.gates if not g.ok]
    assert not b.enabled[0].changed, "the no-op survives the composition"
    assert any("BYTE-IDENTICAL to stock" in n for n in b.enabled[0].hazard_notes)


def test_quantize_refuses_when_the_manifest_page_sha_moved(tmp_path):
    """R11.  Under THE INCUMBENT LOCK the container's own indices are an INPUT, so a page that moved
    would silently lock onto different incumbents.  ``page_sha256`` stops being informational."""
    blob = build_texel_container(nparts=1)
    RP.export_art(blob, 999, tmp_path, lane="paint")
    man = json.loads((tmp_path / RP.ART_MANIFEST).read_text(encoding="utf-8"))
    man["parts"][0]["page_sha256"] = "0" * 64
    (tmp_path / RP.ART_MANIFEST).write_text(json.dumps(man), encoding="utf-8")
    with pytest.raises(RP.RepaintError) as e:
        RP.build(_spec_dict(blob, [_paint_row("tex.part0", tmp_path / "tex.part0.paint.png")]),
                 str(tmp_path / "x_reskin.toml"), blob=blob)
    assert "THE INCUMBENT IS NOT THE ONE YOUR ART CAME OUT OF" in str(e.value)
    # ...and the INDEXED lane on the same stale manifest is UNAFFECTED: the guard is paint-scoped
    src = _write_png(tmp_path, blob, "tex.part0", _page_bytes(blob, "tex.part0"))
    RP.build(_spec_dict(blob, [{"name": "tex.part0", "source": str(src)}]),
             str(tmp_path / "x_reskin.toml"), blob=blob)


def test_quantize_refuses_a_paint_record_with_no_render_key(tmp_path):
    """R11b.  A paint file's colours are only invertible under the decode they were RENDERED with, so
    the decode is DATA the export records -- a record without it came from a pre-W6q export."""
    blob = build_texel_container(nparts=1)
    RP.export_art(blob, 999, tmp_path, lane="paint")
    man = json.loads((tmp_path / RP.ART_MANIFEST).read_text(encoding="utf-8"))
    man["parts"][0]["render_key"] = ""
    (tmp_path / RP.ART_MANIFEST).write_text(json.dumps(man), encoding="utf-8")
    with pytest.raises(RP.RepaintError) as e:
        RP.build(_spec_dict(blob, [_paint_row("tex.part0", tmp_path / "tex.part0.paint.png")]),
                 str(tmp_path / "x_reskin.toml"), blob=blob)
    assert "render_key" in str(e.value) and "export-art --art-lane paint" in str(e.value)


def test_verify_names_the_quantize_fact_and_says_so_when_the_source_is_absent(tmp_path):
    """``verify`` ALREADY re-derives (the CLI rebuilds independently and this compares the staged
    bytes against that rebuild), so nothing is re-derived here.  What is added is LEGIBILITY plus the
    one genuinely new behaviour: an ABSENT paint source is reported, never passed."""
    blob = build_texel_container(nparts=1)
    art = tmp_path / "art"
    RP.export_art(blob, 999, art, lane="paint")
    src = art / "tex.part0.paint.png"
    spec_path = tmp_path / "x_reskin.toml"
    b = RP.build(_spec_dict(blob, [_paint_row("tex.part0", src)]), str(spec_path), blob=blob)
    b.check = RP.self_check(b)
    stage = tmp_path / "stage"
    RP.stage(b, root=stage, previews=False)
    res = RP.verify(b, root=stage)
    assert res["ok"], res["lines"]
    assert any("VERIFY quantize" in ln and "re-quantized from" in ln for ln in res["lines"])
    man = json.loads((stage / "build_manifest.json").read_text(encoding="utf-8"))
    assert man["texels"]["tex.part0"]["quantize"]["exact"] > 0
    assert man["texels"]["tex.part0"]["acknowledge_quantize"] is True
    src.unlink()
    res2 = RP.verify(b, root=stage)
    assert not res2["ok"]
    assert any("THE PAINT SOURCE IS ABSENT" in ln for ln in res2["lines"])


def test_the_absent_paint_source_branch_is_REACHABLE_THROUGH_THE_CLI(tmp_path, capsys):
    """★ THE BRANCH AN AUTHOR ACTUALLY REACHES.

    ``verify`` is reached only THROUGH a rebuild, and a rebuild OPENS the art -- so the absent-source
    sentence above was, at the only entry point a user has, dead code: deleting the paint file made
    the CLI print ``build``'s generic *"no such source image"* instead.  A shipped behaviour that no
    shipped caller can reach is not shipped, so ``verify`` pre-flights the paint sources with the SAME
    resolver ``build`` uses, and the sentence prints.  It never turns a failure into a pass.
    """
    blob = build_texel_container(nparts=1)
    ef = tmp_path / "ef999.bytes"
    ef.write_bytes(blob)
    art = tmp_path / "art"
    rc, _cap = _run(["summon-reskin", "export-art", "--ef", "999", "--from", str(ef),
                     "--out", str(art), "--art-lane", "paint"], capsys)
    assert rc == 0
    spec = tmp_path / "x_reskin.toml"
    spec.write_text(
        "[reskin]\neffect = 999\nlabel = \"q\"\nexpect_sha256 = \"%s\"\n\n"
        "[[reskin.texel]]\nname = \"tex.part0\"\nsource_paint = %r\nenabled = true\n"
        "acknowledge_quantize = true\n"
        % (hashlib.sha256(blob).hexdigest(), str(art / "tex.part0.paint.png")), encoding="utf-8")
    stage = tmp_path / "stage"
    rc, _cap = _run(["summon-reskin", "build", str(spec), "--from", str(ef), "--out", str(stage),
                     "--no-previews"], capsys)
    assert rc == 0
    rc, cap = _run(["summon-reskin", "verify", str(spec), "--from", str(ef), "--out", str(stage)],
                   capsys)
    assert rc == 0 and "VERIFY: PASS" in cap.out
    (art / "tex.part0.paint.png").unlink()
    rc, cap = _run(["summon-reskin", "verify", str(spec), "--from", str(ef), "--out", str(stage)],
                   capsys)
    assert rc == 1, "an absent paint source must FAIL verify, and as a verify result not a crash"
    assert "THE PAINT SOURCE IS ABSENT" in cap.out and "VERIFY: FAIL" in cap.out
    assert "no such source image" not in cap.out + cap.err


def test_the_rgba_lane_still_refuses_with_its_own_reason_verbatim(tmp_path):
    """THE G15 TRIPWIRE.  ``INDEXED_RGBA_REASON`` is about EXACT RECOVERY on the INDEXED lane and is
    byte-for-byte untouched by W6q -- the paint lane is not the indexed lane (its format of record is
    TWO files: the painting plus the container's own index page, read as the incumbent).  Softening
    either string reddens this test and two call sites at once."""
    blob = build_texel_container(nparts=1)
    assert RP.INDEXED_RGBA_REASON == (
        "RGBA / quantize / mint-CLUT stay refused on the INDEXED lane and W6b-1 does "
        "not touch that: the refusal is about EXACT RECOVERY, not about scope -- a "
        "lane whose no-op is not a no-op cannot carry a byte-identity gate")
    with pytest.raises(RP.RepaintError) as e:
        RP.export_art(blob, 999, tmp_path / "r", lane="rgba")
    for pin in ("93/93", "1,844", "8.31%", "88.75%..99.24%", RP.INDEXED_RGBA_REASON):
        assert pin in str(e.value)
    assert "`paint`" not in str(e.value) and "source_paint" not in str(e.value), \
        "the rgba refusal is about EXACT RECOVERY and does not advertise the new lane"
    # an RGBA file handed to a `source =` row still raises refusal site A, verbatim
    RP.export_art(blob, 999, tmp_path, lane="paint")
    with pytest.raises(RP.RepaintError) as e2:
        RP.read_indexed_png(tmp_path / "tex.part0.paint.png", 128, 128, 256)
    assert RP.INDEXED_RGBA_REASON in str(e2.value) and "not \"P\"" in str(e2.value)


def test_the_fail_safes_are_labelled_and_not_claimed_as_proofs(tmp_path):
    """G17's shape as a unit test: R5, the STP tie-break component and the opaque-black census line
    are each REPORTED with their population and the words FAIL-SAFE / structurally unreachable."""
    blob = build_texel_container(nparts=1)
    RP.export_art(blob, 999, tmp_path, lane="paint")
    p = RP.texel_page(blob, "tex.part0")
    words = RP.palette_words(blob, p)
    _raw, cen = RP.read_paint_png(tmp_path / "tex.part0.paint.png", p, words,
                                  RP.texel_view(p, _page_bytes(blob, "tex.part0")))
    text = "\n".join(RP.census_lines(cen))
    assert text.count("FAIL-SAFE") >= 2 and "structurally unreachable" in text
    assert "0x0000 is the container's cutout word BY VALUE" in text
    assert "DISCLOSURE" in text and "[[reskin.target]] does it EXACTLY" in text
    # R5's own label, on a row where every entry is the hole
    b = bytearray(blob)
    struct.pack_into("<%dH" % p.clut_entries, b, p.clut_offset, *([0] * p.clut_entries))
    with pytest.raises(RP.RepaintError) as e:
        RP.read_paint_png(tmp_path / "tex.part0.paint.png", RP.texel_page(bytes(b), "tex.part0"),
                          RP.palette_words(bytes(b), p),
                          RP.texel_view(p, _page_bytes(blob, "tex.part0")))
    assert "LABELLED A FAIL-SAFE" in str(e.value) and "population of this class is 0" in str(e.value)


# ============================================================ (14) W6b-2: THE DEPTH-ATTRIBUTION LANE
# W6b-1 refused 2,385 of 2,572 scenery cells by name because no `so` reader declares their depth.
# W6b-2 found the container states 246 of them SOMEWHERE ELSE, on two channels with two different
# postures, and THE LINE is what this section proves is enforced rather than described:
#
#     CHANNEL G LICENSES.  CHANNEL P DISCLOSES, and edits only behind an explicit acknowledgement.
#
# Every test here runs on SYNTHETIC bytes with no corpus and no install: the fixture below is the
# W6b-1 scenery fixture, unchanged, driven at DIFFERENT EFFECT IDS so that the shipped channel-P table
# speaks (or refuses) about its cells.  PROVENANCE: no stock byte -- an effect id and a VRAM cell
# coordinate are the whole of what is borrowed, and both are already in the committable surface.
#
# ⚠ AND THE ONE THING THAT LOOKS ODD AND IS DELIBERATE: these ids are handed to a container that is
# NOT that effect.  Channel P is keyed by EFFECT ID, exactly as `program_class` and the program-VRAM
# lists already are -- that keying IS the property under test, and W6b-1's own fixture makes the same
# move in the other direction (it passes ef999 so the id-keyed lists cannot answer at all).  The
# corpus-scale join between the table and real containers is `w6b2i_gates.py` I2's job, not this
# file's; here the question is only what the GATE LAYER does with a verdict it has been handed.

#: the fixture's readerless cell -- ``(448, 256)``, W6b-1's own depth-unknown vehicle.
DARK_CELL = "cell.s0.x448_y256"
#: an effect whose id-3 program registers ``(448, 256)`` at ONE depth, 15bpp, and whose program is
#: otherwise CLEAN (neither a VRAM writer nor a reader) -- so the ack ladder is the only thing under
#: test and no other gate can supply the refusal.  15bpp on purpose: a direct cell indexes no palette,
#: so channel P's silence about CLUTs is not a second variable.
P_SINGLE_EF, P_SINGLE_BPP = 90, 15
#: ★ AND THE MAJORITY VEHICLE, which the first draft of this section scoped around: an effect whose
#: program registers the same cell at ONE depth that is **INDEXED** (8bpp, 1 site, program CLEAN).
#: 134 of channel P's 189 cells are indexed and NOT ONE of them can be rendered -- the channel states a
#: DEPTH and names no CLUT -- so this is the rung the ack ladder must be tested on, not only the 15bpp
#: one where the question cannot arise.
P_INDEXED_EF, P_INDEXED_BPP = 93, 8
#: an effect whose program registers the SAME cell at TWO depths -- the hazard that outranks the ack.
P_DUAL_EF = 56


def _ack_rows(name=DARK_CELL, **kw):
    row = {"name": name, "enabled": False}
    row.update(kw)
    return [row]


def test_the_shipped_P_table_is_a_cached_measurement_with_its_pins_asserted_at_import():
    """A CONSTANT NOBODY RE-CHECKS IS A CLAIM.  The re-derivation pin itself lives in the study gate
    (it needs the corpus); what ships here is the arithmetic, asserted AT IMPORT so a truncated table
    fails loudly instead of quietly attributing fewer cells than the record says it does."""
    assert len(DA.PROGRAM_DEPTH) == 221, "every census-declared cell a recovered page word covers"
    dual = [v for v in DA.PROGRAM_DEPTH.values() if v.dual]
    assert len(dual) == DA.PROGRAM_DUAL_CELLS == 22
    assert len({v.effect for v in dual}) == DA.PROGRAM_DUAL_CONTAINERS == 10
    assert len(DA.PROGRAM_DEPTH) - len(dual) == DA.GAIN_PROGRAM + 10, \
        "189 depth-unknown GAINS + the 10 cells the `so` census already had -- P's whole ground truth"
    assert DA.GAIN_PROGRAM + DA.GAIN_SO_PAGE == DA.GAIN_EITHER == 246
    assert DA.GAIN_EITHER + DA.RESIDUE_BLIND + DA.RESIDUE_COVERED == DA.DEPTH_UNKNOWN == 2385
    assert DA.RESIDUE == 2139 and DA.REFUSED_AMBIGUOUS == 32
    # the granularity statement, as a per-cell property rather than as prose
    assert DA.PROGRAM_DEPTH[(1, 704, 256)].inherited is False
    assert DA.PROGRAM_DEPTH[(1, 704, 384)].inherited is True, "the LOWER half of the same column"
    assert DA.program_depth(None, (704, 256)) is None, "no effect id is IGNORANCE, not clean"


def test_the_PAGE_view_and_the_UV_view_are_TWO_VIEWS_and_the_kit_keeps_BOTH():
    """ROW 1.  ``attribution`` answers READERSHIP (which model samples which halfwords);
    ``page_depth_view`` answers DEPTH (what mode the whole 256-line page is read in).  Merging them is
    what produced W6b-1's y=384 blind spot, so the two are kept apart and the fixture shows exactly
    where they differ: the reader view names a column nothing BINDS (the spill target), and the page
    view names a stacked cell no reader reaches."""
    blob = build_scenery_container()
    uv = RP.cell_readers(blob)
    page = RS.page_depth_view(blob)
    # the UV view names only cells some model's stored UVs land in...
    assert sorted(uv) == [(320, 256), (384, 256), (512, 256), (576, 256), (704, 256), (704, 384)]
    # ...the PAGE view names both stacked cells of every BOUND column, and NOTHING else: column 384 is
    # READ by a spilling model but no `so` record NAMES it, so the depth channel is silent there even
    # though the reader channel is not.  That asymmetry is the whole point of two views.
    assert sorted(page) == [(320, 256), (512, 256), (576, 256), (704, 256), (704, 384)]
    assert page[(704, 384)].depths == (8,) and page[(704, 384)].inherited is True
    assert page[(704, 256)].inherited is False
    assert [b.geom for b in page[(704, 384)].binders] == [b.geom for b in page[(704, 256)].binders]
    assert (384, 256) in uv and (384, 256) not in page, "READ but never BOUND -- the asymmetry"
    # and the two AGREE wherever both speak -- the calibration, at fixture scale
    for cell, pd in page.items():
        if cell in uv:
            assert pd.depths == tuple(sorted({m.bpp for m in uv[cell]})), cell
    # THE NON-MERGER, as an identity rather than as a comment: the UV view is byte-for-byte what it
    # was and grew no depth-by-page field, so a caller cannot get the page answer out of it by
    # accident.
    a = RS.attribution(blob, include_direct=True)
    assert not hasattr(a, "page_depths") and not hasattr(a.bindings[0], "page_depths")
    assert sorted(b.tpage for b in a.bindings) == sorted(
        b.tpage for b in RS.attribution(blob, include_direct=True).bindings)


def test_CHANNEL_G_LICENSES_a_readerless_cell_and_the_page_records_WHERE_the_depth_came_from():
    """ROW 8.  A cell no model's UVs reach, whose COLUMN the container binds, gains that depth --
    LICENSED, no key, because it is the same record read at the granularity the hardware uses.  And
    the page says so: ``depth_source`` is the marker every disclosure keys on, so an INHERITED depth
    can never be reported as a direct one."""
    # the fixture's tall rect already has a reader in its lower half, so build a variant WITHOUT it:
    # column 704 stays bound (the "fire" model), the lower half loses its own reader.
    models = tuple(m for m in SCEN_MODELS if m[0] != "low")
    blob = build_scenery_container(models=models)
    assert (704, 384) not in RP.cell_readers(blob), "no model's UVs land in the lower half now"
    pages = {p.name: p for p in RP.scenery_texel_pages(blob, 999)}
    low, top = pages["cell.s0.x704_y384"], pages["cell.s0.x704_y256"]
    assert (low.bpp, low.depth_source, low.depth_inherited) == (8, "so-page", True)
    assert low.hazards.readers == () and low.hazards.page_depths == (8,)
    assert low.hazards.page_binders == top.hazards.page_binders, "ONE record, both halves"
    # the KEY comes from the same record as the depth -- one binding, not a depth here and an
    # unrelated palette choice there
    assert low.palette_name == top.palette_name and low.clut_offset == top.clut_offset
    # and the disclosure SAYS INHERITED, in the words the law is written in
    t = RP.TexelTarget(name=low.name, enabled=True, source="", page=low)
    txt = "  ".join(RP._scenery_disclosures(t))
    assert "CHANNEL G" in txt and "INHERITED FROM THE COLUMN, never direct" in txt
    assert "LICENSED" in txt
    # W6b-1's own cells are untouched: a read cell still reports so-uv
    assert top.depth_source == "so-uv" and top.depth_inherited is False
    # ...and the adopted cell round-trips through the SAME codec at the inherited depth
    raw = blob[low.page_offset:low.page_offset + low.page_bytes]
    assert len(raw) == 0x4000 and low.w == RP.cell_texel_w(8)


def test_CHANNEL_P_DISCLOSES_by_default_and_the_reason_carries_the_IN_GAME_REFUTATION():
    """ROWS 6 + 10.  W6b-1's refusal said the container states nothing.  W6b-2 measured that this is
    FALSE for 189 cells -- so the reason now NAMES the program's depth, its call-site count, the
    residue split, and the in-game cast that refuted the whole channel's licence claim."""
    blob = build_scenery_container()
    ref = {r.name: r for r in RP.scenery_cell_refusals(blob, P_SINGLE_EF)}
    r = ref[DARK_CELL]
    assert r.klass == "depth-unknown", "still refused -- DISCLOSE is not a licence"
    assert "no `so` reader samples this cell" in r.reason
    assert "registers this page at %d bpp at 1 call site(s)" % P_SINGLE_BPP in r.reason
    # THE REFUTATION, carried WITH the number rather than in a docstring beside it
    assert "REGISTRATION-IS-NOT-A-DRAW, CONFIRMED IN-GAME" in r.reason
    assert "ef251" in r.reason and "tpage 312" in r.reason and "BUMPER STRIP" in r.reason
    assert "THE DEPTH COROLLARY" in r.reason and "ef446" in r.reason
    # ...and how to proceed, by NAME
    assert RP.ACK_PROGRAM_DEPTH in r.reason and "expect_bpp = %d" % P_SINGLE_BPP in r.reason
    # THE RESIDUE SPLIT, in the reason string, arithmetic closed
    assert "2,139 keep refusing" in r.reason and "1,278" in r.reason and "861" in r.reason
    # and the page is NOT handed back without the ack
    with pytest.raises(RP.RepaintError, match="is REFUSED, not unknown"):
        RP.texel_page(blob, DARK_CELL, P_SINGLE_EF)
    p = RP.texel_page(blob, DARK_CELL, P_SINGLE_EF, allow_program_depth=True)
    assert (p.bpp, p.depth_source) == (P_SINGLE_BPP, "program")
    assert p.hazards.program_depths == (P_SINGLE_BPP,) and p.hazards.program_sites == 1
    assert p.depth_inherited is True, "a REGISTRATION names a page; nothing named this cell"
    # ...and an acknowledged build DISCLOSES the same thing again, at the target level, where an
    # author reads it.  A caveat that lives only in the refusal an author bypassed is a caveat they
    # never see -- so the ack's own warning travels with the page it unlocked.
    t = RP.TexelTarget(name=p.name, enabled=True, source="", page=p, ack_program_depth=True)
    txt = "  ".join(RP._scenery_disclosures(t))
    assert "DEPTH FROM CHANNEL P" in txt and "registers this page at 15bpp at 1 call site(s)" in txt
    assert "REGISTRATION-IS-NOT-A-DRAW" in txt and "THE DEPTH COROLLARY" in txt
    assert "the judgement that this depth is the depth the SCREEN reads is yours" in txt
    assert "LOWER half of its column" not in txt, "this cell is an UPPER half; do not claim otherwise"


def test_the_depth_unknown_reason_says_WHICH_narrowing_when_channel_H_speaks():
    """ROW 10's second half.  *"The container states nothing about this cell"* is FALSE for 334 of the
    residue's cells: their own id-0 header ships only ONE palette class.  That is a NARROWING, not a
    depth -- ``hint = 4`` still leaves 4bpp or 15bpp -- so the cell stays refused and the reason says
    which of the two sentences it means."""
    blob = build_scenery_container()                        # 3 x 16-entry + 1 x 256-entry -> no hint
    assert RP.clut_arity(blob) == (3, 1)
    assert DA.clut_arity_hint(*RP.clut_arity(blob)) is None
    r = {x.name: x for x in RP.scenery_cell_refusals(blob, 999)}[DARK_CELL]
    assert "CHANNEL H" not in r.reason, "no narrowing here, and silence is not invented"
    # THE RULE is what is under test, not one fixture's arity
    assert DA.clut_arity_hint(3, 0) == 4 and DA.clut_arity_hint(0, 1) == 8
    assert DA.clut_arity_hint(0, 0) is None and DA.clut_arity_hint(2, 2) is None
    txt = RP._depth_evidence(4, None, True)
    assert "no 8-entry-per-byte CLUT: 4bpp or 15bpp" in txt and "a NARROWING, not a depth" in txt
    assert "334 of the residue's cells are in the same position" in txt
    assert "8bpp or 15bpp" in RP._depth_evidence(8, None, True)
    # ★ AND THE WHOLE BLOCK IS GATED ON THE CALLER HAVING CONSULTED A W6b-2 CHANNEL.  A channel a
    # caller declined to name must not appear to have spoken -- and the residue split is a W6b-2
    # measurement, so appending it to a CENSUS-scoped refusal would have made `scenery_surface`'s
    # default emit reasons W6b-1 never wrote while every published COUNT stayed identical.
    assert RP._depth_evidence(4, None, False) == ""
    census = {x.name: x for x in RP.scenery_surface(blob, 999)[1]}[DARK_CELL]
    assert census.reason == RP._REFUSAL_TEXT["depth-unknown"], \
        "CENSUS_CHANNELS: the refusal is W6b-1's own string, byte for byte -- not merely its count"
    assert "THE RESIDUE, SPLIT" in {x.name: x for x in
                                    RP.scenery_cell_refusals(blob, 999)}[DARK_CELL].reason
    # and the narrowing is CARRIED on the hazard record, so a report can quote it per cell
    assert RP.scenery_texel_pages(blob, 999)[0].hazards.bpp_hint is None


def test_the_ack_ladder_FAILS_BY_NAME_at_every_rung():
    """ROW 7, the whole ladder.  An ack with no ``expect_bpp`` fails BY NAME; a MISMATCHING
    ``expect_bpp`` fails BY NAME; a string ``"true"`` fails on the literal-boolean law; and a
    PROGRAM-DUAL cell refuses even with a correct-looking ack, because the hazard outranks it."""
    blob = build_scenery_container()

    # (1) the ack ALONE is not a guard -- it is a judgement with nothing to check it against
    with pytest.raises(RP.RepaintError) as e:
        RP.build(_spec_dict(blob, _ack_rows(**{RP.ACK_PROGRAM_DEPTH: True}), effect=P_SINGLE_EF),
                 "t", blob=blob)
    assert "states NO `expect_bpp`" in str(e.value) and RP.ACK_PROGRAM_DEPTH in str(e.value)
    assert "REGISTRATION-IS-NOT-A-DRAW" in str(e.value)

    # (2) a MISMATCHING expect_bpp fails by name, and the message says which CHANNEL it argues with
    with pytest.raises(RP.RepaintError) as e:
        RP.build(_spec_dict(blob, _ack_rows(expect_bpp=8, **{RP.ACK_PROGRAM_DEPTH: True}),
                            effect=P_SINGLE_EF), "t", blob=blob)
    assert "the spec guards 8bpp" in str(e.value) and "CHANNEL P" in str(e.value)
    assert "registration is not a draw" in str(e.value)

    # (3) THE LITERAL-BOOLEAN LAW: a truthy string must REFUSE, never arm
    with pytest.raises(RP.RepaintError, match="must be a BOOLEAN"):
        RP.build(_spec_dict(blob, _ack_rows(expect_bpp=P_SINGLE_BPP,
                                            **{RP.ACK_PROGRAM_DEPTH: "true"}), effect=P_SINGLE_EF),
                 "t", blob=blob)

    # (4) THE HAZARD OUTRANKS THE ACK.  Same cell, an effect whose program names it at TWO depths:
    # there is no single value for the author's judgement to be about, so the ack cannot reach it.
    with pytest.raises(RP.RepaintError) as e:
        RP.build(_spec_dict(blob, _ack_rows(expect_bpp=8, **{RP.ACK_PROGRAM_DEPTH: True}),
                            effect=P_DUAL_EF), "t", blob=blob)
    assert "PROGRAM-DUAL-DEPTH" in str(e.value)
    assert "UNANIMITY IS THE VERDICT RULE" in str(e.value)
    assert "no acknowledgement lifts it" in str(e.value)

    # (5) ...and the pair TOGETHER resolves the page.  The depth is checked against the derivation,
    # never taken from the spec: `expect_bpp` is STATED by the author and CHECKED.
    b = RP.build(_spec_dict(blob, _ack_rows(expect_bpp=P_SINGLE_BPP,
                                            **{RP.ACK_PROGRAM_DEPTH: True}), effect=P_SINGLE_EF),
                 "t", blob=blob)
    t = b.targets[0]
    assert t.ack_program_depth is True and t.page.depth_source == "program"
    assert t.page.bpp == P_SINGLE_BPP and t.enabled is False

    # (6) and WITHOUT the ack the same row cannot even resolve its name -- the refusal is at
    # RESOLUTION, so there is no window in which a page exists and the ack is still being read
    with pytest.raises(RP.RepaintError, match="is REFUSED, not unknown"):
        RP.build(_spec_dict(blob, _ack_rows(expect_bpp=P_SINGLE_BPP), effect=P_SINGLE_EF),
                 "t", blob=blob)


def test_the_unknown_key_gate_still_fails_closed_on_a_MISTYPED_new_ack():
    """The new key joins the fail-closed table rather than a private list: a mistyped acknowledgement
    that were merely ignored would silently drop the guard it is paired with."""
    blob = build_scenery_container()
    with pytest.raises(RP.RepaintError, match="unknown key"):
        RP.build(_spec_dict(blob, _ack_rows(acknowledge_program_derived_dept=True),
                            effect=P_SINGLE_EF), "t", blob=blob)
    assert RP.ACK_PROGRAM_DEPTH in RP._TEXEL_KEYS


def test_the_refusal_matrix_NAMES_all_three_new_classes_and_only_two_are_UNADDRESSABLE():
    """ROWS 2-4, and the one distinction that keeps row 2's gate honest.  All three classes are in the
    refusal matrix by name; only the two DUAL classes make a cell unaddressable, because those are
    sharper names for cells that were already dark.  ``spill-vs-own-page`` protects nothing new -- it
    exists to carry the REASON -- so it is deliberately NOT in the unaddressable set."""
    for k in ("program-dual-depth", "channel-g-dual-depth", "spill-vs-own-page"):
        assert k in RP._REFUSAL_TEXT, k
    assert "program-dual-depth" in RP._UNADDRESSABLE
    assert "channel-g-dual-depth" in RP._UNADDRESSABLE
    assert "spill-vs-own-page" not in RP._UNADDRESSABLE
    assert "spill-vs-own-page" not in RP._EXPORT_BLOCKING, \
        "a class with a lawful remedy must not silently withdraw art W6b-1 exported"
    txt = RP._REFUSAL_TEXT["spill-vs-own-page"]
    assert "BOTH PREDICATES ARE TRUE OF THE SAME BYTES" in txt
    assert "adds ZERO cells to the refused set as PROTECTION" in txt
    assert "NAMED IN NO LANE DOSSIER" in RP._REFUSAL_TEXT["channel-g-dual-depth"]
    assert "22 cells in 10 containers" in RP._REFUSAL_TEXT["program-dual-depth"]


# ============================================================ W6b-3: CHANNEL A (`so-array`)
#: a declared cell no fixture model reads and no INCUMBENT record's column names -- channel A's own
#: surface.  (Same cell as ``DARK_CELL``: the point is that it is dark until a channel speaks.)
ARRAY_CELL = DARK_CELL
#: ONE multi-part record: entry 0 binds column 448 at 8bpp, entry 1 binds column 704 at the depth the
#: incumbent record already states there -- so the fixture exercises the GAIN without also tripping a
#: conflict, and the two are separable.
A_PARTS_CLEAN = ((_tpage(448, 256, 8), _clut_word(0, 245)),
                 (_tpage(704, 256, 8), _clut_word(0, 245)))
#: ...and the HAZARD shapes.  DUAL: one column, two depths across the record's own entries.
A_PARTS_DUAL = ((_tpage(448, 256, 8), _clut_word(0, 245)),
                (_tpage(448, 256, 4), _clut_word(0, 244)))
#: CONFLICT: column 576 carries a UNANIMOUS incumbent 4bpp (palA/palB) and a UNANIMOUS novel 8bpp.
#: That column's cell is served by ``so-uv`` today, which is exactly what makes the veto visible.
A_PARTS_CONFLICT = ((_tpage(576, 256, 8), _clut_word(0, 245)),
                    (_tpage(576, 256, 8), _clut_word(0, 245)))
#: CLASS C: ONE column, ONE depth, TWO CLUT words -- the only shape where the display pick is a live
#: choice.  ``(0, 244)`` is the VALUE-lowest key; ``(16, 244)`` is the one an array-INDEX tie-break
#: would pick under the reversed storage order.  Both resolve to palettes this fixture declares, so an
#: alternate PNG lands on a row the container really uploads.
A_PARTS_TWO_KEYS = ((_tpage(448, 256, 4), _clut_word(0, 244)),
                    (_tpage(448, 256, 4), _clut_word(16, 244)))


def test_bound_models_is_incumbent_only():
    """★ THE CENSUS LANE IS INCUMBENT-ONLY, and it is a property of the OUTPUT, not a promise.

    A multi-part record contributes NO ``BoundModel`` and NO ``CellReader``, so every W6b-1 spill /
    cover / hazard number is untouched by construction.  There is no order-free alternative: routing
    a multi-part model's FACES to their entries needs the primitive ``part`` byte, i.e. the ORDER
    clause nothing has measured.
    """
    blob = build_scenery_container(extra_models=_so_multi_geom(A_PARTS_CLEAN))
    ms = RP.bound_models(blob)
    assert len(ms) == len(SCEN_MODELS), "the novel record produced no BoundModel"
    assert ARRAY_CELL == "cell.s0.x448_y256" and (448, 256) not in RP.cell_readers(blob)
    inc = RS.attribution(blob, include_direct=True, witness=RS.WITNESS_INCUMBENT)
    assert len({b.geom for b in inc.bindings}) == len(inc.bindings), \
        "THE CALL-SITE ASSERTION: incumbent bindings are 1:1 with GEOM blocks, so `by_geom` in " \
        "`bound_models` cannot last-wins-collapse anything"
    allb = RS.attribution(blob, include_direct=True)
    assert len(allb.bindings) == len(inc.bindings) + 2, \
        "...and the TRUE population really does carry the two novel entries -- otherwise this test " \
        "would pass on a fixture that never exercised the narrowing"
    assert RP.cell_readers(blob).keys() == RP.cell_readers(build_scenery_container()).keys()


def test_the_census_scope_gate_keeps_CHANNEL_A_silent():
    """★ A3: the channel-A hazards derive from ``array_depth_view``, and that call is GATED on the
    caller naming ``"so-array"``.  Without the gate the veto would fire under CENSUS scope and W6b-1's
    own 187 / 2,385 headline would move -- a channel a caller declined to consult must be unable to
    say anything at all, including "no"."""
    blob = build_scenery_container(extra_models=_so_multi_geom(A_PARTS_CONFLICT))
    c_pages, c_ref = RP.scenery_surface(blob, 999)                    # CENSUS_CHANNELS
    base_pages, _ = RP.scenery_surface(build_scenery_container(), 999)
    assert {p.name for p in c_pages} == {p.name for p in base_pages}, \
        "the census surface is byte-for-byte what it was, novel record or not"
    assert not any(r.klass.startswith("array-") for r in c_ref)
    assert all(p.hazards.array_depths == () for p in c_pages), \
        "an unconsulted channel contributes NO data, not merely no verdict"
    # ...and the moment the caller names it, the same bytes speak
    l_pages, l_ref = RP.scenery_surface(blob, 999, channels=RP.LICENSED_CHANNELS)
    assert any(r.klass == "array-vs-column-depth" for r in l_ref)


def test_so_array_needs_ack_and_expect_bpp():
    """★ THE ACK LADDER FOR CHANNEL A, rung by rung, with ``enabled = false`` so every one of them is
    decided before a PNG is opened."""
    blob = build_scenery_container(extra_models=_so_multi_geom(A_PARTS_CLEAN))

    # (0) DISCLOSE, do not license: without the ack the cell is still dark -- and the reason NAMES
    # the depth it will not adopt, the record it came off, and how to proceed
    r = {x.name: x for x in RP.scenery_cell_refusals(blob, 999)}[ARRAY_CELL]
    assert r.klass == "depth-unknown"
    assert "CHANNEL A, DISCLOSE" in r.reason and "record 0x" in r.reason
    assert "binds that column at 8 bpp" in r.reason
    assert RP.ACK_ARRAY_DEPTH in r.reason and "expect_bpp = 8" in r.reason
    assert DA.ARRAY_CAVEAT in r.reason and DA.ORDER_UNMEASURED in r.reason
    assert DA.ARRAY_RESIDUE_LINE in r.reason, "the second residue line, never reconciled with the first"
    # ...and NOT under census scope, where the channel was never consulted
    assert "CHANNEL A" not in {x.name: x for x in RP.scenery_surface(blob, 999)[1]}[ARRAY_CELL].reason
    with pytest.raises(RP.RepaintError, match="is REFUSED, not unknown"):
        RP.texel_page(blob, ARRAY_CELL, 999)

    # (1) the ack ALONE is not a guard -- and the refusal names the record and the slot
    with pytest.raises(RP.RepaintError) as e:
        RP.build(_spec_dict(blob, _ack_rows(name=ARRAY_CELL, **{RP.ACK_ARRAY_DEPTH: True})),
                 "t", blob=blob)
    assert "states NO `expect_bpp`" in str(e.value) and RP.ACK_ARRAY_DEPTH in str(e.value)
    assert "record 0x" in str(e.value) and "slot 0" in str(e.value)
    assert "THE ARITY IS MEASURED TWICE; THE ORDER IS NOT" in str(e.value)
    assert "NOTHING ABOUT CHANNEL A IS IN-GAME" in str(e.value)

    # (2) a MISMATCHING expect_bpp fails by name, and says WHICH channel it argues with
    with pytest.raises(RP.RepaintError) as e:
        RP.build(_spec_dict(blob, _ack_rows(name=ARRAY_CELL, expect_bpp=4,
                                            **{RP.ACK_ARRAY_DEPTH: True})), "t", blob=blob)
    assert "the spec guards 4bpp" in str(e.value) and "CHANNEL A" in str(e.value)
    assert "a BINDING is not a DRAW" in str(e.value)

    # (3) THE LITERAL-BOOLEAN LAW
    with pytest.raises(RP.RepaintError, match="must be a BOOLEAN"):
        RP.build(_spec_dict(blob, _ack_rows(name=ARRAY_CELL, expect_bpp=8,
                                            **{RP.ACK_ARRAY_DEPTH: "true"})), "t", blob=blob)

    # (4) THE PAIR resolves it, and the ledger records the judgement beside the depth source
    b = RP.build(_spec_dict(blob, _ack_rows(name=ARRAY_CELL, expect_bpp=8,
                                            **{RP.ACK_ARRAY_DEPTH: True})), "t", blob=blob)
    t = b.targets[0]
    assert t.ack_array_depth is True and t.page.depth_source == "so-array" and t.page.bpp == 8
    assert t.page.depth_inherited is True, "no instrument saw a model sample these bytes"
    assert t.page.hazards.array_records and t.page.hazards.array_binders
    # ...and the disclosure says all four things in one breath
    txt = "  ".join(RP._scenery_disclosures(t))
    assert "DEPTH FROM CHANNEL A" in txt and "record 0x" in txt
    assert "NOTHING ABOUT CHANNEL A IS IN-GAME" in txt
    assert "0 HITS, 4 MISSES and 2 VACUOUS PASSES" in txt
    assert "THE ORDER IS CORROBORATED BY NOTHING" in txt


def test_array_dual_refuses_under_ack():
    """A HAZARD OUTRANKS AN ACKNOWLEDGEMENT: the ack is a judgement about a SINGLE-valued derivation
    and there is no single value here to judge."""
    blob = build_scenery_container(extra_models=_so_multi_geom(A_PARTS_DUAL))
    ref = {x.name: x for x in RP.scenery_cell_refusals(blob, 999)}
    assert ref[ARRAY_CELL].klass == "array-dual-depth"
    assert "UNANIMITY IS THE VERDICT RULE" in ref[ARRAY_CELL].reason
    assert "no acknowledgement lifts it" in ref[ARRAY_CELL].reason
    assert "the column's INCUMBENT depth set is EMPTY" in ref[ARRAY_CELL].reason
    with pytest.raises(RP.RepaintError) as e:
        RP.build(_spec_dict(blob, _ack_rows(name=ARRAY_CELL, expect_bpp=8,
                                            **{RP.ACK_ARRAY_DEPTH: True})), "t", blob=blob)
    assert "ARRAY-DUAL-DEPTH" in str(e.value)


def test_array_dual_refuses_EVEN_WHERE_ANOTHER_CHANNEL_ALREADY_SERVES_THE_CELL():
    """★ A2: ALL 12 corpus ``array-dual`` cells refuse OUTRIGHT, including the 4 whose column carries
    an incumbent depth -- and for those the refusal DISPLACES the ``so-uv`` / ``so-page`` service.

    The softer treatment (state the hazard ALONGSIDE, keep the page) was considered and NOT shipped:
    CHANNEL A holds VETO power and never emission power, so where it can only make the picture LESS
    certain it is allowed to, and where it could only make it MORE certain it is not.  Loosening later
    is cheap; tightening after shipping is not.
    """
    dual_on_read = ((_tpage(704, 256, 8), _clut_word(0, 245)),
                    (_tpage(704, 256, 4), _clut_word(0, 244)))
    blob = build_scenery_container(extra_models=_so_multi_geom(dual_on_read))
    base = {p.name for p in RP.scenery_texel_pages(build_scenery_container(), 999)}
    assert "cell.s0.x704_y256" in base, "the fixture served this cell before CHANNEL A spoke"
    now = {p.name for p in RP.scenery_texel_pages(blob, 999)}
    assert "cell.s0.x704_y256" not in now and "cell.s0.x704_y384" not in now
    ref = {x.name: x for x in RP.scenery_cell_refusals(blob, 999)}
    assert ref["cell.s0.x704_y256"].klass == "array-dual-depth"
    assert "TAKES THAT PAGE AWAY" in ref["cell.s0.x704_y256"].reason
    assert "considered and NOT shipped" in ref["cell.s0.x704_y256"].reason
    # ...and the CENSUS surface still serves it, because it never consulted the channel
    assert "cell.s0.x704_y256" in {p.name for p in RP.scenery_surface(blob, 999)[0]}


def test_the_ONE_resolution_entry_point_is_LICENSED_so_a_CENSUS_pick_can_still_be_VETOED():
    """★ WHERE A2's -6 ACTUALLY BITES, said out loud rather than left as a seam between two scopes.

    The channel-scope law keeps CHANNEL A silent on a census-scoped SURFACE, so every W6b-1 census
    number holds.  But :func:`~ff9mapkit.summons.repaint.texel_page` -- the lane's ONLY resolution
    entry point, and the one every paint/export vehicle goes through -- resolves at
    :data:`~ff9mapkit.summons.repaint.LICENSED_CHANNELS` unconditionally.  So a cell CHOSEN off the
    census surface and then RESOLVED is answered by the veto: the two scopes disagree about the same
    cell, and only one of them can hand back bytes.

    That is the shape of the rung's permissiveness regression at its widest, and it is pinned HERE so
    a later ratification of the softer treatment has a named test to invert rather than a surprise in
    a sibling board.  The refusal is at least honest in both directions: it names its own class, and
    no acknowledgement lifts it.
    """
    dual_on_read = ((_tpage(704, 256, 8), _clut_word(0, 245)),
                    (_tpage(704, 256, 4), _clut_word(0, 244)))
    blob = build_scenery_container(extra_models=_so_multi_geom(dual_on_read))
    census = {p.name: p for p in RP.scenery_surface(blob, 999)[0]}
    assert "cell.s0.x704_y256" in census and census["cell.s0.x704_y256"].bpp == 8, \
        "the CENSUS still answers with a page, and with the depth a reader actually samples"
    for kw in ({}, {"allow_array_depth": True}):
        with pytest.raises(RP.RepaintError, match="ARRAY-DUAL-DEPTH") as e:
            RP.texel_page(blob, "cell.s0.x704_y256", 999, **kw)
        assert "is REFUSED, not unknown" in str(e.value), \
            "a vetoed cell is answered with its own reason, never with 'unknown'"


def test_array_vs_column_refuses_and_is_unaddressable():
    """★ THE RUNG'S ONE DELIBERATE PERMISSIVENESS REGRESSION, at fixture scale (the corpus shape is
    ef184 x448).  A licensed channel's own instrument contradicts itself on one column, so the licence
    is void FOR THAT COLUMN and the page is withdrawn: both predicates are true of the same bytes, and
    the kit states both and picks neither."""
    blob = build_scenery_container(extra_models=_so_multi_geom(A_PARTS_CONFLICT))
    ref = {x.name: x for x in RP.scenery_cell_refusals(blob, 999)}
    r = ref["cell.s0.x576_y256"]
    assert r.klass == "array-vs-column-depth"
    assert "BOTH PREDICATES ARE TRUE OF THE SAME BYTES" in r.reason
    assert "WITHDRAWS A PAGE THE LANE USED TO HAND BACK" in r.reason
    assert "A LICENCE CONTRADICTED BY ITS OWN INSTRUMENT IS VOID FOR THAT COLUMN" in r.reason
    assert "NOTHING ABOUT CHANNEL A IS IN-GAME" in r.reason, "A6: the caveat rides the refusal"
    # BOTH depths are named and NEITHER is picked
    assert "4 bpp" in r.reason and "8 bpp" in r.reason
    # UNADDRESSABLE, and no acknowledgement reaches it
    assert "array-vs-column-depth" in RP._UNADDRESSABLE
    with pytest.raises(RP.RepaintError, match="is REFUSED, not unknown"):
        RP.texel_page(blob, "cell.s0.x576_y256", 999, allow_array_depth=True)
    # THE COUNTERFACTUAL: exactly this cell is lost and nothing else
    before = {p.name for p in RP.scenery_texel_pages(build_scenery_container(), 999)}
    after = {p.name for p in RP.scenery_texel_pages(blob, 999)}
    assert before - after == {"cell.s0.x576_y256"} and not after - before


def test_so_array_without_so_page_fails_CLOSED():
    """★ CHANNEL A DEPENDS ON CHANNEL G, AND THE DEPENDENCY IS A CALL-SITE GUARD.

    Both channel-A hazards are COMPARISONS against the column's incumbent depth, and the incumbent
    side is channel G's ``page_depth_view``.  Asked for ``"so-array"`` with ``"so-page"`` left out,
    ``array_vs_column`` is ``False`` BY CONSTRUCTION -- so the one column whose licensed reading its
    own record class contradicts would come back as an ordinary 4bpp page with the contradiction
    unstated.  That is the silent side-taking channel A exists to refuse, so the combination is
    REFUSED rather than served: *a law not enforced at the call site is not enforced.*
    """
    blob = build_scenery_container(extra_models=_so_multi_geom(A_PARTS_CONFLICT))
    # the guard fires on the SET, before any derivation -- and it names the remedy
    with pytest.raises(RP.RepaintError) as e:
        RP.scenery_surface(blob, 999, channels=("so-uv", "so-array"))
    assert "requires 'so-page'" in str(e.value) and "silently answers" in str(e.value)
    # ...and it is a GUARD, not a blanket ban: both shipped sets still work
    assert RP.scenery_surface(blob, 999, channels=RP.CENSUS_CHANNELS)[0] is not None
    conflict = [r for r in RP.scenery_surface(blob, 999, channels=RP.LICENSED_CHANNELS)[1]
                if r.klass == "array-vs-column-depth"]
    assert len(conflict) == 1, "the licensed set still states the contradiction it was gated for"
    # the W6b-2 scope (the licensed set MINUS channel A) is likewise lawful -- sibling boards roll it
    assert RP.scenery_surface(blob, 999,
                              channels=tuple(c for c in RP.LICENSED_CHANNELS
                                             if c != "so-array"))[0] is not None


def test_depth_attribution_lines_gate_CHANNEL_A_on_the_token():
    """The report block is the one place channel A used to speak without being asked.  It changes no
    verdict -- but *"no line about channel A"* and *"channel A states nothing"* are the same output
    and only one of them is a measurement, so the block says which it means."""
    blob = build_scenery_container(extra_models=_so_multi_geom(A_PARTS_CLEAN))
    pages, _ = RP.scenery_surface(blob, 999, channels=RP.LICENSED_CHANNELS)
    lic = "\n".join(RP.depth_attribution_lines(blob, 999, pages))
    cen = "\n".join(RP.depth_attribution_lines(blob, 999, pages, channels=RP.CENSUS_CHANNELS))
    assert "CHANNEL A here:" in lic and "NOT CONSULTED" not in lic
    assert "CHANNEL A here: NOT CONSULTED" in cen
    assert "must not appear to have spoken" in cen


def test_depth_derived_by_covers_every_source():
    """A missing entry makes ``assert_expect_bpp`` raise ``KeyError`` -- i.e. the guard that is
    supposed to REFUSE would crash.  A guard may only ever fail CLOSED, so the coverage is asserted at
    IMPORT in ``repaint`` itself; this pins that the assertion exists and holds."""
    assert set(RP._DEPTH_DERIVED_BY) == set(RP.DEPTH_SOURCES)
    assert "so-array" in RP.DEPTH_SOURCES and "so-array" in RP.LICENSED_CHANNELS
    assert "so-array" not in RP.CENSUS_CHANNELS, "the census channel set is W6b-1's own, unchanged"
    assert "a BINDING is not a DRAW" in RP._DEPTH_DERIVED_BY["so-array"]
    assert "UNMEASURED" in RP._DEPTH_DERIVED_BY["so-array"]


def test_refusal_text_covers_every_new_class():
    """Both W6b-3 classes have text, both are UNADDRESSABLE, and both quote ``ARRAY_CAVEAT`` -- the
    page-withdrawing verdict is exactly where "nothing about this channel is in-game" carries most."""
    for k in ("array-dual-depth", "array-vs-column-depth"):
        assert k in RP._REFUSAL_TEXT, k
        assert k in RP._UNADDRESSABLE and k in RP._EXPORT_BLOCKING
        assert DA.ARRAY_CAVEAT in RP._REFUSAL_TEXT[k], "A6"
        assert DA.DEPTH_COROLLARY in RP._REFUSAL_TEXT[k]
        assert "** STATED PLAINLY" in RP._REFUSAL_TEXT[k]
    assert "12 corpus cells over 6 columns" in RP._REFUSAL_TEXT["array-dual-depth"]
    assert "ONLY column in the corpus" in RP._REFUSAL_TEXT["array-vs-column-depth"]


def test_ack_array_key_registered():
    """An unregistered spec key fails CLOSED two lines into ``build`` -- correct behaviour that would
    also make the whole feature unreachable.  A capability nobody can spell is not a capability."""
    assert DA.ACK_ARRAY_KEY in RP._TEXEL_KEYS and RP.ACK_ARRAY_DEPTH == DA.ACK_ARRAY_KEY
    blob = build_scenery_container(extra_models=_so_multi_geom(A_PARTS_CLEAN))
    with pytest.raises(RP.RepaintError, match="unknown key"):
        RP.build(_spec_dict(blob, _ack_rows(name=ARRAY_CELL, acknowledge_array_derived_dept=True)),
                 "t", blob=blob)


def test_class_C_evidence_for_a_channel_A_cell_comes_from_the_ARRAY_entries():
    """★ THE CLASS-C EVIDENCE IS TAKEN AT THE SAME GRANULARITY AS THE DEPTH, one channel further.

    65/65 corpus channel-A cells are readerless AND unnamed by any incumbent record, so a class-C
    predicate fed from either older source is False BY CONSTRUCTION there -- the census's clean 0 on
    this surface is VACUOUS, not a clear, and 34 of the 65 sit on a column bound with 2-4 CLUT words.
    """
    # ``A_PARTS_TWO_KEYS``: both keys resolve to declared palettes -- an alternate PNG for a row the
    # container never uploads would be a picture in a key the engine never applies, which is the thing
    # the class-C mechanism exists to avoid.  ONE derivation, shared with the display-pick test below,
    # so the two cannot drift onto different evidence about the same shape.
    blob = build_scenery_container(extra_models=_so_multi_geom(A_PARTS_TWO_KEYS))
    p = RP.texel_page(blob, ARRAY_CELL, 999, allow_array_depth=True)
    assert p.depth_source == "so-array" and p.bpp == 4
    assert len(p.hazards.array_clut_cells) == 2 and p.hazards.page_clut_cells == ()
    assert p.hazards.column_clut_cells == p.hazards.array_clut_cells
    assert p.hazards.multi_palette, "class C, and it is REACHABLE -- not False by construction"
    t = RP.TexelTarget(name=p.name, enabled=True, source="", page=p, ack_array_depth=True)
    assert "MULTI-PALETTE (class C)" in "  ".join(RP._scenery_disclosures(t))
    assert len(RP.alternate_palette_rows(blob, p, RS.palette_map(blob))) == 1, \
        "every OTHER key ships an alternate PNG -- which is what makes the display CONVENTION safe"


def test_the_channel_A_display_pick_ties_on_VALUES_not_on_the_array_index():
    """★ A4, at the PAGE: the CLUT a channel-A cell renders through is a CONVENTION OVER A SET, and
    its key is ``(geom, tpage, clut_word)`` -- the VALUES the display consumes.

    Two entries of one record can now land on one cell, so the old bare-``geom`` key stopped being a
    total order.  Completing it with the array INDEX would make the picture depend on STORAGE ORDER,
    which is the one thing about this format nothing has measured (identity 63.3 / reversed 56.0 /
    permutations 59.4, ~0.9 sigma above chance).  Completing it with the values cannot: permuting the
    record's entries is then invisible to every field of the page.

    Both halves are asserted, because either alone is weak.  A permutation-invariance check alone
    passes on a pick that is symmetric-but-wrong; an equals-the-lowest-key check alone passes on an
    index tie-break that happens to agree on this fixture's storage order.
    """
    fwd = build_scenery_container(extra_models=_so_multi_geom(A_PARTS_TWO_KEYS))
    rev = build_scenery_container(extra_models=_so_multi_geom(tuple(reversed(A_PARTS_TWO_KEYS))))
    a, b = (RP.texel_page(x, ARRAY_CELL, 999, allow_array_depth=True) for x in (fwd, rev))
    assert a.depth_source == "so-array" and a.hazards.multi_palette, \
        "the fixture must put TWO keys on the column or the tie-break is never exercised"
    # (1) THE PICK IS THE VALUE-LOWEST KEY, not entry 0 of the array
    assert (a.clut, a.palette_name) == (_clut_word(0, 244), "pal.s0.x0_y244.e16")
    assert a.hazards.array_clut_cells == ((0, 244), (16, 244))
    # (2) ...and a permutation of the SAME entries is invisible to every field of the page
    assert (b.clut, b.tpage, b.bpp, b.palette_name) == (a.clut, a.tpage, a.bpp, a.palette_name)
    assert b.clut_offset == a.clut_offset and b.clut_entries == a.clut_entries
    assert b.hazards.array_clut_cells == a.hazards.array_clut_cells
    assert b.hazards.array_depths == a.hazards.array_depths
    # (3) and the OTHER key is still named and still ships its own read-only alternate, which is what
    # makes naming ONE of them safe in the first place
    alt_rev = RP.alternate_palette_rows(rev, b, RS.palette_map(rev))
    assert [(r.clut_cell, r.palette_name, r.words) for r in alt_rev] == \
           [(r.clut_cell, r.palette_name, r.words)
            for r in RP.alternate_palette_rows(fwd, a, RS.palette_map(fwd))]
    assert [r.clut_cell for r in alt_rev] == [(16, 244)], "the key NOT picked, named and rendered"


def test_a_readerless_cell_whose_COLUMN_is_bound_at_TWO_depths_REFUSES_by_name():
    """ROW 4, on synthetic bytes: the class the calibration refuter found and NO lane dossier named.
    Two models bind the same column at different depths; the cell neither of them reads inherits an
    ambiguity, not a depth."""
    models = (("a", 704, 256, 8, (0, 245), (0, 0, 100, 60)),
              ("b", 704, 256, 4, (0, 244), (0, 0, 100, 60)))
    blob = build_scenery_container(models=models)
    pages = {p.name: p for p in RP.scenery_texel_pages(blob, 999)}
    ref = {r.name: r for r in RP.scenery_cell_refusals(blob, 999)}
    assert "cell.s0.x704_y384" not in pages, "the LOWER half inherits an ambiguity, not a depth"
    assert ref["cell.s0.x704_y384"].klass == "channel-g-dual-depth"
    assert "its column is bound at 4/8 bpp" in ref["cell.s0.x704_y384"].reason
    # ...while the UPPER half, which BOTH models actually read, is the W6b-1 class and keeps its name
    assert ref["cell.s0.x704_y256"].klass == "same-bytes-two-depths"
    with pytest.raises(RP.RepaintError, match="CHANNEL-G-DUAL-DEPTH"):
        RP.texel_page(blob, "cell.s0.x704_y384", 999, allow_program_depth=True)


def test_SPILL_vs_OWN_PAGE_is_flagged_and_reconciles_NOTHING():
    """ROW 2.  A cell whose every reader binds the NEIGHBOURING page at one depth while its OWN page
    is named at another.  Both predicates are true; the kit prints both and picks neither.  Measured
    on the fixture: the cell keeps its READER-derived depth (that is what a model actually samples)
    and gains a refusal RECORD carrying the reason -- and its addressability does not change."""
    # column 320 is bound at 8bpp and spills into 384; give 384 its own 4bpp binder whose UVs stay
    # OUTSIDE the cell, so the cell's own page is named at a depth no reader of it states.
    models = SCEN_MODELS + (("owner384", 384, 256, 4, (0, 244), (0, 200, 4, 204)),)
    blob = build_scenery_container(models=models)
    pages = {p.name: p for p in RP.scenery_texel_pages(blob, 999)}
    spill = pages["cell.s0.x384_y256"]
    assert spill.hazards.spill_vs_own_page is True
    assert spill.hazards.depths == (8,) and spill.hazards.page_depths == (4,)
    assert spill.bpp == 8, "the READER's depth stands -- it is what something actually samples"
    assert "spill-vs-own-page" in spill.hazards.names
    ref = [r for r in RP.scenery_cell_refusals(blob, 999) if r.klass == "spill-vs-own-page"]
    assert [r.name for r in ref] == ["cell.s0.x384_y256"]
    assert "neither instrument is wrong" in ref[0].reason
    # THE GATE THE RECORD DEMANDS: it protects NOTHING new.  The cell still resolves, exactly as it
    # did before the class existed -- a gate asserting it protects >= 1 new cell would FAIL.
    assert RP.texel_page(blob, "cell.s0.x384_y256", 999).bpp == 8
    t = RP.TexelTarget(name=spill.name, enabled=True, source="", page=spill)
    assert any("FLAGGED rather than reconciled" in n for n in RP._scenery_disclosures(t))


def test_scenery_lines_prints_the_channel_block_even_when_every_channel_is_SILENT():
    """A channel that says nothing has to SAY it says nothing: 'no line about channel P' and 'channel
    P states nothing here' are the same output, and only one of them is a measurement."""
    blob = build_scenery_container()
    L = "\n".join(RP.scenery_lines(blob, 999))
    assert "THE DEPTH CHANNELS (W6b-2, W6b-3)" in L
    assert "DEPTH is a property of the PAGE" in L
    assert "CHANNEL P here: 0 cell(s)" in L, "ef999 is not in the table, and the line still prints"
    assert "CHANNEL H here: nClut4 3 / nClut8 1 -> no narrowing" in L
    assert "REGISTRATION-IS-NOT-A-DRAW, CONFIRMED IN-GAME" in L
    L2 = "\n".join(RP.scenery_lines(blob, P_DUAL_EF))
    # BOTH stacked cells of the column, because one page word names a column of two -- the
    # granularity statement, visible in the count rather than only in the law it is printed beside.
    assert "CHANNEL P here: 2 cell(s)" in L2 and "2 of them at TWO depths" in L2


def test_an_INDEXED_channel_P_cell_refuses_FOR_WANT_OF_A_KEY_and_says_so_in_its_own_words():
    """★ THE MAJORITY OF CHANNEL P, and the rung the first draft of this ladder scoped around.

    A channel-P cell at 4 or 8 bpp is an INDEX ARRAY with no key: the program's registered tpage names
    a DRAW MODE and names no CLUT, and no ``so`` record names one either -- that is the premise of the
    whole channel.  **134 of the 189 cells are in that shape and not one of them can be rendered.**

    Two things are under test and both are about honesty rather than about safety, since the lane
    already failed closed:

    1. it refuses in ITS OWN CLASS.  Reusing ``no-declared-clut`` printed *"the reader's `so` record
       names CLUT cell None at 0 entries"* on a cell that HAS NO READER -- ``None`` and ``0``
       formatted into a sentence written about an instrument that does not exist here, on containers
       that declare a dozen palettes.  **A reason may never drift from the predicate that produced
       it**;
    2. the DISCLOSURE does not promise a remedy that does not exist.  The refusal an author reads
       BEFORE acknowledging says the ack cannot reach this cell, instead of naming necessary
       conditions they would read as sufficient ones.
    """
    blob = build_scenery_container()
    r = {x.name: x for x in RP.scenery_cell_refusals(blob, P_INDEXED_EF)}[DARK_CELL]
    assert r.klass == "depth-unknown"
    assert "registers this page at %d bpp at 1 call site(s)" % P_INDEXED_BPP in r.reason
    assert "THE ACKNOWLEDGEMENT CANNOT REACH THIS CELL" in r.reason, \
        "the remedy sentence is CONDITIONAL -- necessary conditions must not read as sufficient ones"
    assert "134 of channel P's 189 cells are indexed and NONE of them render" in r.reason
    assert "the ack's live surface is the 55 that are 15bpp DIRECT" in r.reason
    assert "To edit it anyway say" not in r.reason, "no promise the kit cannot keep"
    assert "the author carries the judgement, the kit carries the check" not in r.reason
    # the 15bpp cell in the SAME position gets the remedy, because there it is one
    assert "To edit it anyway say" in \
        {x.name: x for x in RP.scenery_cell_refusals(blob, P_SINGLE_EF)}[DARK_CELL].reason

    # ...and WITH the ack and a matching expect_bpp it still refuses -- by its OWN name, saying what
    # is true.  `program-depth-no-palette`, never the reader-shaped `no-declared-clut`.
    ref = {x.name: x for x in RP.scenery_cell_refusals(blob, P_INDEXED_EF, program_depth=True)}
    got = ref[DARK_CELL]
    assert got.klass == "program-depth-no-palette"
    assert "CHANNEL P STATES A DEPTH AND NOTHING ELSE" in got.reason
    assert "the reader's `so` record" not in got.reason, "there IS no reader -- do not quote one"
    assert "None" not in got.reason and " 0 entries" not in got.reason
    assert "this container's own id-0 headers ship 3 16-entry and 1 256-entry palette(s)" in got.reason
    assert "134 of channel P's 189 cells are indexed" in got.reason
    assert "program-depth-no-palette" in RP._UNADDRESSABLE, "there is no picture to hand back"
    with pytest.raises(RP.RepaintError, match="CHANNEL P STATES A DEPTH AND NOTHING ELSE"):
        RP.texel_page(blob, DARK_CELL, P_INDEXED_EF, allow_program_depth=True)
    with pytest.raises(RP.RepaintError, match="CHANNEL P STATES A DEPTH AND NOTHING ELSE"):
        RP.build(_spec_dict(blob, _ack_rows(expect_bpp=P_INDEXED_BPP,
                                            **{RP.ACK_PROGRAM_DEPTH: True}), effect=P_INDEXED_EF),
                 "t", blob=blob)
    # the 15bpp vehicle is the CONTRAST, in the same test, so the split is a measurement here too
    assert RP.texel_page(blob, DARK_CELL, P_SINGLE_EF, allow_program_depth=True).bpp == P_SINGLE_BPP


def test_the_INHERITED_clause_is_gated_on_the_COLUMN_and_not_on_the_writers_rect():
    """A page word names a PAGE, so a depth crossed a CELL BOUNDARY exactly when the cell is the LOWER
    half of its 256-line COLUMN.  ``hazards.lower_half`` answers a different question -- *"is this
    WRITER's rect split?"* -- and the two disagree on the 10 corpus channel-P cells that are **id-9
    alternate blocks at y = 384**: one whole 0x4000 upload, never a rect's lower half, and still the
    bottom of a column whose depth was read off the top.  Gated on the writer, those 10 were told
    their depth was direct while the kit's own ``ProgramDepth.inherited`` said it was inherited.

    Built by moving a REAL resolved page to ``y = 384`` with ``lower_half`` left False -- which is
    exactly the id-9 shape -- so the predicate is tested at the call site rather than restated.
    """
    blob = build_scenery_container()
    upper = RP.texel_page(blob, DARK_CELL, P_SINGLE_EF, allow_program_depth=True)
    assert upper.cell == (448, 256) and upper.hazards.lower_half is False
    up_txt = "  ".join(RP._scenery_disclosures(
        RP.TexelTarget(name=upper.name, enabled=True, source="", page=upper,
                       ack_program_depth=True)))
    assert "LOWER half of its column" not in up_txt, "an UPPER half; do not claim a crossing"

    low = dataclasses.replace(upper, cell=(448, 384))
    assert low.hazards.lower_half is False, "the id-9 shape: at y=384 and not a rect's lower half"
    assert DA.PROGRAM_DEPTH[(P_SINGLE_EF, 448, 384)].inherited is True, "...but the COLUMN says yes"
    low_txt = "  ".join(RP._scenery_disclosures(
        RP.TexelTarget(name=low.name, enabled=True, source="", page=low, ack_program_depth=True)))
    assert "LOWER half of its column" in low_txt and "INHERITED FROM THE COLUMN" in low_txt
    # ...and the same predicate governs channel G, so one rule serves both inherited channels
    g_low = dataclasses.replace(low, depth_source="so-page")
    assert "INHERITED FROM THE COLUMN" in "  ".join(RP._scenery_disclosures(
        RP.TexelTarget(name=g_low.name, enabled=True, source="", page=g_low)))
    g_up = dataclasses.replace(upper, depth_source="so-page")
    assert "INHERITED FROM THE COLUMN" not in "  ".join(RP._scenery_disclosures(
        RP.TexelTarget(name=g_up.name, enabled=True, source="", page=g_up)))


# ======================================== W6b-3 (iii): THE SECOND ARRAY, DISCLOSED (a READERSHIP
# question, never a depth).  The synthetic half proves the SHAPE; the corpus-gated half proves the
# POPULATION.  Nothing in this section may move a page, a name, a depth or a byte.
#: a MOVER on the one declared cell nothing else reads -- so "every reader moves" is reachable with a
#: single model and the granularity twin below can add a zero-pair reader to break it.
MOVER_A = (0x0080, 0x0000)


def _mover_model(x=448, y=256, bpp=8, clut=(0, 245), uv=(0, 0, 100, 60), second=MOVER_A) -> bytes:
    """One extra UV-bound model on cell ``(x, y)`` whose ``so`` record carries ``second``."""
    return _uv_geom(_tpage(x, y, bpp), _clut_word(*clut), uv, second=second)


def test_the_second_array_field_is_CONSULTATION_GATED():
    """★ P1.  The second array lives in the SAME record ``so-uv`` already reads, so nothing but the
    gate stops it being stated under the CENSUS default -- and stating it there would make
    ``scenery_surface``'s census output no longer byte-for-byte W6b-1's, which is the population
    `w6b_gates` G6 / `w6q_gates` G1+G16 / `w6b2i_gates` I5 are written ABOUT.  A channel a caller
    declined to consult must be unable to say anything at all, including "no"."""
    blob = build_scenery_container(extra_models=_mover_model())
    c_pages, c_ref = RP.scenery_surface(blob, 999)                     # CENSUS_CHANNELS
    assert all(p.hazards.second_array == () for p in c_pages), \
        "an unconsulted instrument contributes NO DATA, not merely no verdict"
    assert all(not p.hazards.every_reader_moves for p in c_pages)
    assert not any(r.klass == "second-array-mover" for r in c_ref)
    l_pages, l_ref = RP.scenery_surface(blob, 999, channels=RP.LICENSED_CHANNELS)
    hit = [p for p in l_pages if p.cell == (448, 256)]
    assert len(hit) == 1 and hit[0].depth_source == "so-uv"
    assert len(hit[0].hazards.second_array) == 1 and hit[0].hazards.every_reader_moves
    assert [r.klass for r in l_ref if r.cell == (448, 256)] == ["second-array-mover"]
    # ...and the census page set is EXACTLY what it is without the extra model's second array
    plain = build_scenery_container(extra_models=_mover_model(second=(0, 0)))
    p2, _ = RP.scenery_surface(plain, 999)
    assert [(p.name, p.bpp, p.depth_source) for p in c_pages] == \
           [(p.name, p.bpp, p.depth_source) for p in p2]


def test_the_predicate_is_the_WHOLE_READER_SET_ef038s_20_over_7_in_miniature():
    """★ P2.  THE GRANULARITY IS THE WHOLE READER SET: one reader with a zero pair keeps the cell out
    of the class.  This is ef038 ``cell.s0.x640_y256`` -- 20 movers and SEVEN zero-pair controls, the
    exact split that made U1 cast 1 read ``VISIBLE_UNBANDED`` rather than blank -- reproduced on
    synthetic bytes at arity two."""
    both = build_scenery_container(
        extra_models=_mover_model(uv=(0, 0, 100, 60)) + _mover_model(uv=(0, 60, 100, 100)))
    pages, ref = RP.scenery_surface(both, 999, channels=RP.LICENSED_CHANNELS)
    hz = [p for p in pages if p.cell == (448, 256)][0].hazards
    assert len(hz.readers) == 2 and len(hz.second_array) == 2 and hz.every_reader_moves
    assert any(r.klass == "second-array-mover" for r in ref)

    one_clean = build_scenery_container(
        extra_models=_mover_model(uv=(0, 0, 100, 60))
        + _mover_model(uv=(0, 60, 100, 100), second=(0, 0)))
    pages2, ref2 = RP.scenery_surface(one_clean, 999, channels=RP.LICENSED_CHANNELS)
    hz2 = [p for p in pages2 if p.cell == (448, 256)][0].hazards
    assert len(hz2.readers) == 2 and len(hz2.second_array) == 1, "the mover is still DISCLOSED"
    assert not hz2.every_reader_moves, "...and the cell is NOT in the class"
    assert not any(r.klass == "second-array-mover" for r in ref2)


def test_a_readerless_cell_is_not_VACUOUSLY_in_the_class():
    """P2b.  ``bool(readers)`` is load-bearing: without it every channel-G / A / P cell would satisfy
    'every reader moves' by having none."""
    blob = build_scenery_container()
    pages, _ = RP.scenery_surface(blob, P_SINGLE_EF, channels=RP.LICENSED_CHANNELS,
                                  program_depth=True)
    dark = [p for p in pages if p.depth_source == "program"]
    assert dark, "the fixture must actually produce a readerless page for this to mean anything"
    assert all(not p.hazards.readers and not p.hazards.every_reader_moves for p in dark)


def test_BOTH_candidate_columns_are_stated_and_NEITHER_is_preferred():
    """★ P3.  A column is 64 halfwords, i.e. ``{4bpp: 256, 8bpp: 128, 15bpp: 64}`` texels -- so the
    cast's ``+128`` is HALF a 4bpp column, EXACTLY ONE at 8bpp (640 -> 704) and TWO at 15bpp.  All
    three asserted off the same pair, so the arithmetic is CHECKED rather than typed."""
    per_col = {b: RS.PAGE_CELL_W * KT.TEXELS_PER_HW[b] for b in (4, 8, 15)}
    assert per_col == {4: 256, 8: 128, 15: 64}
    # 8bpp, u 0..127, bound column 448: SWAPPED (A = 0x80) lands on 512, ORIGINAL (B = 0) stays
    got = RP._effective_columns(448, (0, 127), 8, 0x80)
    assert got == (512,) and RP._effective_columns(448, (0, 127), 8, 0) == (448,)
    # the same +128 at the other two depths, from the same table
    assert RP._effective_columns(448, (0, 127), 4, 0x80) == (448,), "half a 4bpp column: no crossing"
    assert RP._effective_columns(448, (0, 63), 15, 0x80) == (576,), "two 15bpp columns"
    # ...and the record carries both readings with the SAME evidence and no preference
    blob = build_scenery_container(extra_models=_mover_model(uv=(0, 0, 127, 60)))
    pages, _ = RP.scenery_surface(blob, 999, channels=RP.LICENSED_CHANNELS)
    n = [p for p in pages if p.cell == (448, 256)][0].hazards.second_array[0]
    assert (n.a, n.b) == MOVER_A and (n.swapped_texels, n.original_texels) == MOVER_A
    assert n.bound_column == 448
    assert n.swapped_columns == (512,) and n.original_columns == (448,)
    assert n.swapped_moved is True and n.original_moved is False


def test_the_page_is_NOT_WITHDRAWN_by_the_new_class():
    """★ P4.  EMISSION SET UNCHANGED, proven rather than asserted: same pages, same names, same
    depths -- and the class is in NEITHER ``_UNADDRESSABLE`` nor ``_EXPORT_BLOCKING``, so
    ``texel_page`` still resolves and ``export_art`` still writes the PNG."""
    assert "second-array-mover" not in RP._UNADDRESSABLE
    assert "second-array-mover" not in RP._EXPORT_BLOCKING
    mover = build_scenery_container(extra_models=_mover_model())
    plain = build_scenery_container(extra_models=_mover_model(second=(0, 0)))
    a = RP.scenery_texel_pages(mover, 999)
    b = RP.scenery_texel_pages(plain, 999)
    assert [(p.name, p.cell, p.bpp, p.depth_source, p.page_offset, p.page_bytes) for p in a] == \
           [(p.name, p.cell, p.bpp, p.depth_source, p.page_offset, p.page_bytes) for p in b], \
        "the mover moves NO page, NO name, NO depth and NO offset"
    assert RP.texel_page(mover, DARK_CELL, 999).cell == (448, 256)


def test_the_refusal_TEXT_is_quotable_and_carries_no_literal_percent():
    """★ P5.  A caveat nothing quotes is a wish -- and a literal ``%`` in a class text is how a
    measurement quietly becomes a typo, because ``_refusal`` formats it with ``txt % detail``."""
    txt = RP._REFUSAL_TEXT["second-array-mover"]
    assert "%" not in txt.replace("%s", ""), "one %s for the detail, and no other percent anywhere"
    assert txt.count("%s") == 1
    assert DA.U_DISPLACEMENT_CAVEAT in txt, "the conditionality travels IN the constant"
    assert DA.ACK_MOVER_KEY in txt
    assert "THE GRANULARITY IS THE WHOLE READER SET" in txt and "cell.s0.x640_y256" in txt
    assert "THE REACH IS THE INCUMBENT RECORDS ONLY" in txt, "the blind spot is stated, not omitted"
    for piece in ("0.84", "0.68", "UNRESOLVED", "cell.s0.x704_y256"):
        assert piece in DA.U_DISPLACEMENT_CAVEAT, piece
    # the three author-facing consumption sites each spend it
    blob = build_scenery_container(extra_models=_mover_model())
    _pages, ref = RP.scenery_surface(blob, 999, channels=RP.LICENSED_CHANNELS)
    got = [r for r in ref if r.klass == "second-array-mover"][0]
    assert DA.U_DISPLACEMENT_CAVEAT in got.reason and "SWAPPED -> column(s) 512" in got.reason
    assert DA.U_DISPLACEMENT_CAVEAT in "\n".join(
        RP.depth_attribution_lines(blob, 999, _pages))


def test_the_second_array_ack_is_a_LITERAL_BOOLEAN_and_fails_closed_when_misspelled():
    """★ P6.  An acknowledgement is stated, never inferred from a truthy string -- and an
    unregistered near-miss spelling fails CLOSED two lines into ``build``."""
    assert DA.ACK_MOVER_KEY in RP._TEXEL_KEYS
    blob = build_scenery_container(extra_models=_mover_model())
    with pytest.raises(RP.RepaintError, match="must be a BOOLEAN"):
        RP.build(_spec_dict(blob, _ack_rows(**{DA.ACK_MOVER_KEY: "true"})), "t", blob=blob)
    with pytest.raises(RP.RepaintError, match="unknown key"):
        RP.build(_spec_dict(blob, _ack_rows(**{"acknowledge_second_array_displacment": True})),
                 "t", blob=blob)
    # ...and stated properly it parses (the row is disabled, so nothing else is under test here)
    b = RP.build(_spec_dict(blob, _ack_rows(**{DA.ACK_MOVER_KEY: True})), "t", blob=blob)
    assert b.targets[0].ack_second_array is True and b.patched == blob


def test_THE_BUILD_GATE_refuses_by_name_and_the_ack_moves_NO_BYTE(tmp_path):
    """★ P7.  The two-layer shape ``u``-spill already has: a refusal CLASS carries the reason and a
    build GATE carries the obligation.  And the emission identity is PROVEN, not asserted -- the
    acknowledged build is compared byte-for-byte against the same build with the gate's own predicate
    stubbed out, i.e. against what this row produced before the class existed."""
    blob = build_scenery_container(extra_models=_mover_model())
    px = _page_bytes(blob, DARK_CELL)
    src = _write_png(tmp_path, blob, DARK_CELL, px)
    row = {"name": DARK_CELL, "enabled": True, "source": str(src), "expect_bpp": 8}
    with pytest.raises(RP.RepaintError, match="THE SECOND-ARRAY GATE"):
        RP.build(_spec_dict(blob, [dict(row)]), str(tmp_path / "s.toml"), blob=blob)
    ok = RP.build(_spec_dict(blob, [dict(row, **{DA.ACK_MOVER_KEY: True})]),
                  str(tmp_path / "s.toml"), blob=blob)
    # THE COUNTERFACTUAL: the same row, with the gate unable to fire -- i.e. the pre-class kit
    was = RP._gate_second_array
    try:
        RP._gate_second_array = lambda targets: {}
        before = RP.build(_spec_dict(blob, [dict(row)]), str(tmp_path / "s.toml"), blob=blob)
    finally:
        RP._gate_second_array = was
    assert ok.patched == before.patched, "the ack buys a DISCLOSURE, never a different byte"
    assert any("SECOND-ARRAY MOVER on every reader" in n for n in ok.targets[0].hazard_notes)
    assert any(DA.U_DISPLACEMENT_ACK_WARNING in n for n in ok.targets[0].hazard_notes), \
        "the ACKNOWLEDGED case still says what was acknowledged"


def test_export_art_PRINTS_the_disclosure_in_the_manifest_and_the_scaffold(tmp_path):
    """★ P8.  The author meets this BEFORE they paint, not after the playtest: both readings in the
    manifest, both in the scaffold, and the ack line only on a firing row."""
    blob = build_scenery_container(extra_models=_mover_model())
    RP.export_art(blob, 999, out_dir=tmp_path, scaffold=True, overlays=False)
    man = json.loads((tmp_path / RP.ART_MANIFEST).read_text(encoding="utf-8"))
    hit = [e for e in man["scenery"] if e["name"] == DARK_CELL][0]
    assert hit["second_array_all_readers"] is True
    n = hit["second_array"][0]
    assert (n["a"], n["b"]) == list(MOVER_A) or (n["a"], n["b"]) == MOVER_A
    assert n["swapped"] == {"texels": 0x80, "columns": [512], "moved": True}
    assert n["original"] == {"texels": 0, "columns": [448], "moved": False}
    assert n["bound_column"] == 448 and n["record_at"] > 0
    others = [e for e in man["scenery"] if e["name"] != DARK_CELL]
    assert others and all(e["second_array_all_readers"] is False for e in others)
    assert any(r["class"] == "second-array-mover" for r in man["refused"])
    txt = (tmp_path / RP.SCAFFOLD_NAME).read_text(encoding="utf-8")
    assert "%s = false" % DA.ACK_MOVER_KEY in txt
    assert txt.count("%s = false" % DA.ACK_MOVER_KEY) == 1, "only on the firing row"
    assert "SECOND-ARRAY MOVER on EVERY reader" in txt
    assert "SWAPPED  reading (pair position 0 moves u): +128 texels -> column(s) 512" in txt
    assert "ORIGINAL reading (pair position 1 moves u): +0 texels -> column(s) 448 (unmoved)" in txt
    assert "NEITHER is preferred" in txt
    assert max(len(ln) for ln in txt.splitlines()) < 120
    import tomllib as _toml
    rows = _toml.loads(txt)["reskin"]["texel"]
    assert all(set(r) <= RP._TEXEL_KEYS for r in rows), "every emitted key is a KNOWN key"
    assert RP.build({"reskin": {"effect": 999, "expect_sha256": hashlib.sha256(blob).hexdigest(),
                                "texel": rows}}, str(tmp_path / "s.toml"),
                    blob=blob).patched == blob


def test_hazard_NAMES_is_untouched_by_the_new_class():
    """P8b.  ``names`` is the W6b HAZARD vocabulary and is an EXACT-TUPLE pin in six shipped places;
    the second array is a DISCLOSURE with its own field, class and key, and adds no slug."""
    blob = build_scenery_container(extra_models=_mover_model())
    pages, _ = RP.scenery_surface(blob, 999, channels=RP.LICENSED_CHANNELS)
    hz = [p for p in pages if p.cell == (448, 256)][0].hazards
    assert hz.every_reader_moves and "second-array-mover" not in hz.names


@needs_corpus
def test_the_firing_set_over_the_WHOLE_CORPUS_reconciles_with_the_impact_scoping():
    """★★ P9 -- THE HEADLINE, derived at call time from the container and never tabled.

    52 cells in 29 containers, 47 of them carrying no export-blocking refusal of any other class.
    The predicate is the CONSERVATIVE all-movers one, so the set is a strict SUPERSET of the impact
    scoping's two per-labelling lost-cell lists (16 SWAPPED / 19 ORIGINAL) and CONTAINS both
    completely -- that is the reconciliation, and it is what says the disclosure reaches every cell
    either live labelling would darken.  ef038 ``x640_y256`` (20 movers, 7 controls) is ABSENT, and
    three of the four shipped cast cells are absent too.
    """
    fire, open_cells = {}, 0
    for ef, blob in _corpus_effects():
        pages, refused = RP.scenery_surface(blob, ef, channels=RP.LICENSED_CHANNELS)
        by_cell = {}
        for r in refused:
            by_cell.setdefault(r.cell, set()).add(r.klass)
        hits = {c for c, ks in by_cell.items() if "second-array-mover" in ks}
        if not hits:
            continue
        fire["ef%03d" % ef] = hits
        for c in hits:
            if not (by_cell[c] - {"second-array-mover"}) & RP._EXPORT_BLOCKING:
                open_cells += 1
        emitted = {p.cell: p.depth_source for p in pages}
        assert all(emitted.get(c) == "so-uv" for c in hits), \
            "every firing cell is a LICENSED so-uv page today -- that is why the class exists"
    n = sum(len(v) for v in fire.values())
    assert (n, len(fire), open_cells) == (DA.SECOND_ARRAY_MOVER_CELLS,
                                          DA.SECOND_ARRAY_MOVER_CONTAINERS,
                                          DA.SECOND_ARRAY_MOVER_OPEN) == (52, 29, 47)
    # the scoping's two per-labelling lists, INCUMBENT scope, contained completely
    swapped = {("ef038", (640, 384)), ("ef061", (640, 256)), ("ef082", (512, 256)),
               ("ef082", (512, 384)), ("ef179", (704, 256)), ("ef226", (576, 256)),
               ("ef381", (384, 384)), ("ef384", (448, 256)), ("ef384", (448, 384)),
               ("ef387", (640, 256)), ("ef407", (640, 384)), ("ef424", (448, 384)),
               ("ef447", (384, 384)), ("ef492", (448, 256)), ("ef492", (448, 384)),
               ("ef499", (448, 256))}
    original = {("ef038", (512, 256)), ("ef082", (640, 256)), ("ef082", (704, 256)),
                ("ef203", (640, 256)), ("ef205", (576, 256)), ("ef206", (512, 256)),
                ("ef225", (640, 256)), ("ef296", (512, 256)), ("ef387", (512, 256)),
                ("ef405", (448, 256)), ("ef405", (576, 256)), ("ef405", (640, 256)),
                ("ef427", (640, 256)), ("ef438", (576, 256)), ("ef446", (448, 256)),
                ("ef446", (512, 256)), ("ef490", (512, 256)), ("ef502", (576, 256)),
                ("ef509", (448, 256))}
    mine = {(c, cell) for c, cells in fire.items() for cell in cells}
    assert len(swapped) == 16 and len(original) == 19 and len(swapped | original) == 35
    assert not (swapped - mine) and not (original - mine), "zero missed, under EITHER labelling"
    assert len(mine - (swapped | original)) == 17, "and 17 conservative extras, by design"
    # THE GRANULARITY, on the cast's own cell, and the shipped casts that stay clean
    assert ("ef038", (640, 256)) not in mine, "20 movers and SEVEN controls: NOT in the class"
    for clean in (("ef211", (704, 384)), ("ef211", (704, 256)), ("ef211", (576, 384)),
                  ("ef211", (640, 256)), ("ef429", (448, 256)), ("ef130", (448, 384)),
                  ("ef424", (704, 384))):
        assert clean not in mine, clean
    assert ("ef424", (448, 384)) in mine, "the ONE shipped-cast cell that does fire -- by name"
