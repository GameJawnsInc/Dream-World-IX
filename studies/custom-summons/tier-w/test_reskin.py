r"""Tests for TIER W rung 4 -- THE RESKIN (``reskin.py``).

Runs WITHOUT the extracted corpus: most tests synthesise their own ``ef###``-shaped container (a
minimal id-0 scenery CLUT resource + an id-4/id-5 creature package, following
``test_retime.py``'s posture of building a container BY HAND rather than trusting the real install),
so the transform, the five hard rules, the build-time refusals and the ledger/revert round-trip are
all exercised on bytes this file wrote.  A handful of tests need the user's own FF9 install (the real
ef227 container) or the extracted corpus and are skipped when absent, exactly as ``test_rescore.py``
and ``test_retime.py`` do.

    py -m pytest studies/custom-summons/tier-w/test_reskin.py -q

THE SYNTHETIC CONTAINER (section 0) is deliberately minimal: ONE chunk carrying an id-0 scenery
resource (one inline CLUT rect spanning VRAM rows 244-245, declaring a 16-entry palette at
``(0,244)`` and a 256-entry one at ``(0,245)``), an id-3 filler resource (a stand-in "program
image", any bytes), an id-4/id-5 creature package (N parts, each an 8bpp page + a whole 256-entry
CLUT row, laid out exactly as ``ff9mapkit.summons.texture.texture_check`` requires) and an id-6
payload of ``so``+GEOM pairs so the DERIVED attribution has real bindings to read.  No camera
archive (id-2) is included -- the all-zero sequence stream decodes to a single immediate END op, so
``summon_camera.extract_shots`` resolves zero shots, which is a legitimate (if unusually quiet)
container rather than an error.

W5 -- THE GENERALISATION -- widened the fixture rather than the assertions.  W4's version leaned on
``reskin.ATTRIBUTION``, a hand table keyed on bare VRAM cells, to make ``(0,244)`` come back SHARED;
that table is gone, so the fixture now WRITES the ``so`` records that make the sharing true and the
tests read the derivation's answer.  A two-chunk variant (``build_synth_multiwriter_container``)
carries a multi-writer cell and a dual-depth cell -- synthetic stand-ins for ef381 and ef447 -- and
a texanim-armed variant stands in for the ef038/ef177/ef493-495 class, so every W5 refusal has a
test that runs with no corpus and no install at all.

Every CLUT word in this file is COMPUTED (a small arithmetic generator), never a byte run copied from
the corpus or the install -- ``ff9mapkit``'s provenance rule applies to this file exactly as it does
to ``reskin.py`` itself.
"""
from __future__ import annotations

import dataclasses
import glob
import hashlib
import os
import struct
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import reskin as RS                                             # noqa: E402  (sets up sys.path)
import ef_container as EC                                        # noqa: E402
import summon_camera as W                                        # noqa: E402
from ff9mapkit.summons import container as KC                    # noqa: E402
from ff9mapkit.summons import texanim as TA                       # noqa: E402
from ff9mapkit.summons import texture as KT                       # noqa: E402

#: this module has no corpus-only test (its install-gated tests already exercise the real ef227 data
#: the corpus was extracted from) -- kept for parity with test_rescore.py's / test_retime.py's own
#: posture, in case a future addition here needs it.
CORPUS = W.SCRATCH_CORPUS
have_corpus = bool(glob.glob(os.path.join(CORPUS, "ef*.bytes")))
needs_corpus = pytest.mark.skipif(not have_corpus, reason="no extracted corpus at %s" % CORPUS)


def _has_install() -> bool:
    try:
        from ff9mapkit import config
        return bool(config.find_game_path(None))
    except Exception:
        return False


needs_install = pytest.mark.skipif(not _has_install(), reason="no FF9 install resolvable")

SPEC = os.path.join(_HERE, "bahamut_reskin.toml")
SECTOR = W.SECTOR

#: THE FROZEN ARTIFACT.  ef227's reskin is deployed and cast-proven, so W5's generalisation is only
#: allowed if `bahamut_reskin.toml` still builds THESE bytes.  A hash, not data.
W4_PATCHED_SHA256 = "7fef205ffbe547545374de9d1017613448777f0251d9d425b55f7796f688b89a"

try:                                                          # py3.11+ stdlib, else the backport
    import tomllib as _toml
except ModuleNotFoundError:                                   # pragma: no cover
    import tomli as _toml                                     # type: ignore


def _load_toml_text(text: str) -> dict:
    """Parse a scaffold's emitted TOML -- proving it is real TOML, not just a string that looks it."""
    return _toml.loads(text)


# ============================================================ (0) the synthetic container
#: the two VRAM cells the fixture declares.  W4's fixture leaned on ``reskin.ATTRIBUTION`` to give
#: them English names and a SHARED flag; W5 DERIVES both from the container's own ``so`` bindings,
#: so the fixture now writes real ``so`` records and real (degenerate) GEOM blocks and the names
#: come back as the slot-keyed auto-names.
_CELL_4BPP = 0x3D00            # VRAM (0, 244), 16-entry 4bpp  -> ONE binder  => derived PRIVATE
_CELL_8BPP = 0x3D40            # VRAM (0, 245), 256-entry 8bpp -> TWO binders => derived SHARED
#: the derived names those two cells resolve to (chunk slot 0)
PAL_4BPP = "pal.s0.x0_y244.e16"
PAL_8BPP = "pal.s0.x0_y245.e256"


def _pad_sector(payload: bytes):
    n = max(1, (len(payload) + SECTOR - 1) // SECTOR)
    return payload.ljust(n * SECTOR, b"\x00"), n


def synth_clut16(zero_first: bool = True):
    """16 COMPUTED BGR555 words (never a byte run copied from anywhere).

    Channels are taken mod 25, so this palette's peak lands BELOW the 5-bit ceiling and it can serve
    as the fixture's headroom-positive row -- the counterpart to the 256-entry rows, which sweep the
    whole 0..31 range and peak at 31 like 46 of the corpus's 93 creature rows do."""
    out = []
    for i in range(16):
        if i == 0 and zero_first:
            out.append(0)
            continue
        r, g, b = (i * 3 + 1) % 25, (i * 7 + 2) % 25, (i * 11 + 5) % 25
        stp = 0x8000 if i % 4 == 0 else 0
        out.append(stp | r | (g << 5) | (b << 10))
    return out


def synth_clut256_warm(seed: int = 1):
    """256 COMPUTED words with a deliberate RED CAST.

    ``synth_clut256`` sweeps the whole hue wheel, so its saturation-weighted mean hue comes out at
    the same angle for every seed -- useless for proving that ``hue_to`` lands two writers with
    DIFFERENT stock means on the same absolute hue.  This one has a mean nowhere near it."""
    out = [0]
    for i in range(1, 256):
        r = 18 + (i * seed) % 10
        g = (i * seed * 3) % 7
        b = (i * seed * 5) % 5
        out.append((0x8000 if i % 6 == 0 else 0) | r | (g << 5) | (b << 10))
    return out


def synth_clut256(seed: int = 1, zero_first: bool = True):
    out = []
    for i in range(256):
        if i == 0 and zero_first:
            out.append(0)
            continue
        r = (i * seed + 1) & 0x1F
        g = (i * seed * 3 + 2) & 0x1F
        b = (i * seed * 5 + 7) & 0x1F
        stp = 0x8000 if i % 6 == 0 else 0
        out.append(stp | r | (g << 5) | (b << 10))
    return out


def _words(ws):
    return struct.pack("<%dH" % len(ws), *ws)


def _build_scenery_id0(pal16, pal256) -> bytes:
    """One id-0 payload: a single inline rect covering VRAM rows 244-245 (w=256, h=2), with a
    16-entry CLUT at row 244 x=0 and a 256-entry CLUT at row 245 x=0 -- exactly the layout
    ``reskin.id0_palettes`` decodes (module docstring section (1))."""
    buf = bytearray(0x424)
    struct.pack_into("<iii", buf, 0x00, 0x14, 0x1C, 1)      # pageBlockRel, inlineRel, nInline=1
    struct.pack_into("<HH", buf, 0x0C, 1, 1)                 # nClut4=1, nClut8=1
    struct.pack_into("<HH", buf, 0x10, _CELL_4BPP, _CELL_8BPP)
    struct.pack_into("<ii", buf, 0x14, 0x424, 0)             # pixelDataRel, nPageRects=0
    struct.pack_into("<HHHH", buf, 0x1C, 0, 244, 256, 2)     # inline rect: x=0 y=244 w=256 h=2
    row244 = bytearray(512)
    row244[0:32] = _words(pal16)
    buf[0x24:0x24 + 512] = row244
    buf[0x224:0x224 + 512] = _words(pal256)
    return bytes(buf)


def _build_creature_id4(npart: int, pal256_list, texanim: int = 0) -> bytes:
    """One id-4 payload: a header (``texOffset == 0x180 + 4*motionCount``) + ``npart`` 8bpp pages
    (zero pixel data -- the palette tests never sample the pixels) + ``npart`` 256-entry CLUT rows,
    one per part, at consecutive strip rows starting ``KT.CLUT_STRIP_Y`` (matching
    ``texture_check``'s decodable layout exactly: mode-1 tpage, entry0 == 0, row in range).

    ``texanim > 0`` ARMS the texanim region (D3): it declares one motion clip and puts
    ``motionOffsets[0]`` that many bytes past ``firstBlock``, which is exactly the shape the five
    corpus effects have (ef038 = 116 B, ef177/493/494/495 = 364 B each) and exactly what
    ``reskin.texanim_region`` measures.
    """
    nmotion = 1 if texanim else 0
    tex_off = 0x180 + 4 * nmotion
    tex_bytes = npart * KT.PAGE_BYTES
    clut_rows = npart
    clut_bytes = clut_rows * 0x200
    header = bytearray(tex_off)
    struct.pack_into("<hhhH", header, 0, tex_off, nmotion, npart, clut_rows)
    struct.pack_into("<II", header, 8, tex_bytes, clut_bytes)
    # modelBytes / firstBlock: firstBlock == texOffset means the GEOM block ends where the model
    # image starts, so the texanim region begins at the id-5 payload's own first byte.
    struct.pack_into("<II", header, 0x10, tex_off + 0x1000, tex_off)
    for i in range(npart):
        struct.pack_into("<H", header, 0x18 + 2 * i, 0x80)    # tpage: mode 1 (8bpp)
        clutword = ((KT.CLUT_STRIP_Y + i) << 6) | 0x10        # row i, entry0 == 0
        struct.pack_into("<H", header, 0x24 + 2 * i, clutword)
        struct.pack_into("<H", header, 0x30 + 2 * i, 0)       # v_offset
    if nmotion:
        struct.pack_into("<I", header, 0x180, tex_off + texanim)
    pages = bytes(npart * KT.PAGE_BYTES)
    cluts = b"".join(_words(w) for w in pal256_list)
    return bytes(header) + pages + cluts


def _so_geom(tpage: int, clut: int) -> bytes:
    """One 16-byte ``so`` binding record + the smallest GEOM block ``ef_container.scan_geom`` accepts.

    This is what lets the fixture exercise the DERIVED attribution (D5) on bytes this file wrote,
    instead of leaning on a hard-coded table.  The GEOM is degenerate on purpose -- 1 bone, 1 mesh,
    every primitive bucket empty -- but it satisfies the scanner's whole acceptance law: the
    ``pBoneTable == 0x14`` needle, ``pMeshTable == 0x18 + (boneCount-1)*4``, and all four chain
    identities (each pool starts at the 4-byte-aligned end of the previous, which for empty pools
    means they all coincide).

    Layout, geom-relative::

        0x00  flags(bit0 clear) / 0 / boneCount=1 / meshCount=1
        0x0c  pBoneTable = 0x14      <- the scanner's needle
        0x10  pMeshTable = 0x18
        0x18  MeshDesc[0], 0x28 bytes: eight zero counts, then the five pool pointers
        0x40  vertsPerBone[1] = {0}
        0x44  positions == primitives == uv == colours (all empty, all coincident)
    """
    so = struct.pack("<HHHH", 0x6F73, 1, 0x10, 0x0C) + struct.pack("<HHHH", tpage, clut, 0, 0)
    g = bytearray(0x48)
    g[0:4] = bytes([0x00, 0x00, 1, 1])                        # flags, zero, boneCount, meshCount
    struct.pack_into("<II", g, 0x04, 0, 0)                    # +0x04/+0x08 OPAQUE
    struct.pack_into("<I", g, 0x0C, 0x14)                     # pBoneTable -- the needle
    struct.pack_into("<I", g, 0x10, 0x18)                     # pMeshTable == 0x18+(1-1)*4
    struct.pack_into("<I", g, 0x14, 0)                        # listHead
    # MeshDesc[0] at 0x18: unknown0, the eight counts (all 0 by construction), +0x12 zero byte,
    # +0x13 otBias, then vertsPerBone / positions / primitives / uv / colours.
    struct.pack_into("<IIIII", g, 0x18 + 0x14, 0x40, 0x44, 0x44, 0x44, 0x44)
    struct.pack_into("<H", g, 0x40, 0)                        # vertsPerBone[0] = 0 vertices
    return so + bytes(g)


def _build_models_id6(bindings) -> bytes:
    """An id-6 (``MARK_6``) payload carrying one ``so``+GEOM pair per binding."""
    return b"".join(_so_geom(tp, cw) for tp, cw in bindings)


#: the fixture's default model list -- TWO models on the 8bpp cell (so it derives SHARED) and ONE on
#: the 4bpp cell (so it derives PRIVATE), at COMPLETE `so` coverage (3 of 3 GEOM blocks bound).
DEFAULT_BINDINGS = ((0x88, _CELL_8BPP), (0x89, _CELL_8BPP), (0x08, _CELL_4BPP))


def _assemble(chunks) -> bytes:
    """``[(chunkIndex, [(resourceId, payload), ...]), ...]`` -> a whole container, header included."""
    head = bytearray(struct.pack("<h", len(chunks)))
    body = bytearray()
    for ci, resources in chunks:
        padded = [(rid,) + _pad_sector(p) for rid, p in resources]
        head += struct.pack("<hh", ci, len(padded))
        for rid, _p, n in padded:
            head += struct.pack("<bbh", rid, 0, n)
        for _rid, p, _n in padded:
            body += p
    assert len(head) <= SECTOR
    return bytes(bytearray(head.ljust(SECTOR, b"\x00")) + body)


def build_synth_container(npart: int = 2, id3_size: int = 1, bindings=DEFAULT_BINDINGS,
                          texanim: int = 0) -> bytes:
    """A whole ``ef###.bytes``-shaped container: one chunk with id-0 (scenery), id-3 (a filler
    "program image"), id-4+id-5 (the creature) and id-6 (the ``so``-bound scenery models).  No id-2
    camera archive -- the all-zero sequence stream decodes to a single immediate END op, so
    ``extract_shots`` resolves zero shots.

    Pass ``bindings=()`` for the OTHER attribution regime: a container with no GEOM models at all,
    where coverage is NO EVIDENCE and every scenery palette is SHARED-UNKNOWN.  Pass ``texanim=N``
    to arm the texanim region with an N-byte table.
    """
    id0 = _build_scenery_id0(synth_clut16(), synth_clut256(seed=3))
    id3 = bytes([0x55]) * (id3_size * SECTOR)
    id4 = _build_creature_id4(npart, [synth_clut256(seed=5 + i) for i in range(npart)],
                              texanim=texanim)
    id5 = bytes([0x66]) * SECTOR
    resources = [(0, id0), (3, id3), (4, id4), (5, id5)]
    if bindings:
        resources.append((6, _build_models_id6(bindings)))
    return _assemble([(0, resources)])


def build_synth_creatureless_container(bindings=DEFAULT_BINDINGS) -> bytes:
    """D9's fixture: the 348-of-372 shape -- scenery palettes, no id-4/id-5 creature package at all."""
    id0 = _build_scenery_id0(synth_clut16(), synth_clut256(seed=3))
    resources = [(0, id0), (3, bytes([0x55]) * SECTOR)]
    if bindings:
        resources.append((6, _build_models_id6(bindings)))
    return _assemble([(0, resources)])


def _build_second_chunk_id0(pal256_a, pal256_b) -> bytes:
    """A SECOND chunk's id-0, declaring TWO 256-entry palettes over the same VRAM rows chunk 0 used:
    ``(0,245)`` again -- a MULTI-WRITER cell (two file offsets, one depth) -- and ``(0,244)`` at
    256 entries where chunk 0 declared 16 -- a DUAL-DEPTH cell.  This is ef381's and ef447's shape
    in miniature, written by hand so both refusals have a corpus-free test.

    ``pal256_a`` lands on VRAM row 244 and ``pal256_b`` on row 245 (the rect starts at 244, so the
    second 512-byte row is 245) -- the second writer of ``(0,245)`` is deliberately given a mean hue
    far from chunk 0's, which is what the ``hue_to`` co-transform test needs."""
    buf = bytearray(0x424)
    struct.pack_into("<iii", buf, 0x00, 0x14, 0x1C, 1)       # pageBlockRel, inlineRel, nInline=1
    struct.pack_into("<HH", buf, 0x0C, 0, 2)                 # nClut4=0, nClut8=2
    struct.pack_into("<HH", buf, 0x10, _CELL_8BPP, _CELL_4BPP)
    struct.pack_into("<ii", buf, 0x14, 0x424, 0)             # pixelDataRel, nPageRects=0
    struct.pack_into("<HHHH", buf, 0x1C, 0, 244, 256, 2)     # inline rect: x=0 y=244 w=256 h=2
    buf[0x24:0x24 + 512] = _words(pal256_a)
    buf[0x224:0x224 + 512] = _words(pal256_b)
    return bytes(buf)


def build_synth_multiwriter_container(chunk_indices=(0, 1)) -> bytes:
    """Two chunks that both upload VRAM rows 244-245 -- the D2 fixture.

    * ``(0,245)``: 256 entries from BOTH chunks at different file offsets => MULTI-WRITER.
    * ``(0,244)``: 16 entries from chunk slot 0, 256 from chunk slot 1  => MULTI-WRITER + DUAL-DEPTH.

    ``chunk_indices`` exists to test the legacy alias map's own precondition: W4's ``c{chunk_index}``
    tag is only unambiguous when those indices are distinct, so ``(0, 0)`` must suppress the aliases
    rather than resolve one of two spans arbitrarily.
    """
    c0 = [(0, _build_scenery_id0(synth_clut16(), synth_clut256(seed=3))),
          (3, bytes([0x55]) * SECTOR)]
    c1 = [(0, _build_second_chunk_id0(synth_clut256(seed=7), synth_clut256_warm(seed=3)))]
    return _assemble([(chunk_indices[0], c0), (chunk_indices[1], c1)])


def _spec(blob: bytes, targets, effect: int = 999, spans=None) -> dict:
    r = {"effect": effect, "label": "synthtest", "expect_sha256": hashlib.sha256(blob).hexdigest(),
        "target": targets}
    if spans:
        r["spans"] = spans
    return {"reskin": r}


def test_synth_container_is_well_formed_and_resolves_the_expected_palettes():
    """Sanity-checks the fixture ITSELF (section 0) so a later test failure cannot be a synthetic
    container bug masquerading as a ``reskin.py`` bug."""
    blob = build_synth_container(npart=2)
    c = EC.parse_header(blob, strict=True)
    assert c.cursor_end == len(blob)
    mp = KC.creature_package(blob)
    assert mp is not None
    chk = KT.texture_check(blob, mp)
    assert chk["decodable"], chk["reasons"]
    pmap = RS.palette_map(blob)
    names = sorted(p.name for p in pmap.palettes)
    assert names == ["creature.part0", "creature.part1", PAL_4BPP, PAL_8BPP]
    shared = {p.name: p.shared for p in pmap.palettes}
    assert shared[PAL_8BPP] is True                            # two `so` binders -> DERIVED shared
    assert shared[PAL_4BPP] is False                           # one binder      -> DERIVED private
    assert shared["creature.part0"] is False
    assert pmap.envelope == sum(s.size for s in pmap.spans)


def test_slot_keyed_auto_names_and_the_derived_envelope():
    """D1: names are keyed on (chunk SLOT, VRAM cell, entry count), never on ``chunk_index``, and
    the whole-set envelope is DERIVED (``sum(span.size)``) rather than the ef227 constant."""
    blob = build_synth_container(npart=1)
    pmap = RS.palette_map(blob)
    assert RS.palette_auto_name(3, 192, 244, 16) == "pal.s3.x192_y244.e16"
    assert RS.span_auto_name(7, 2) == "s7_clut_band2"
    # one creature row (0x200) + one 2-row 256-halfword inline band (0x400)
    assert pmap.envelope == 0x200 + 0x400
    assert [s.name for s in pmap.spans] == ["creature_clut_strip", "s0_clut_band0"]


def test_attribution_is_derived_from_the_containers_own_so_records():
    """D5: the ``so`` scan (magic 0x6F73) is committable code now, and the SHARED flag is its
    output -- not a hand table keyed on bare VRAM cells."""
    blob = build_synth_container(npart=1)
    a = RS.attribution(blob)
    assert (a.geom_with_so, a.geom_total) == (3, 3) and a.complete
    assert len(a.binders((0, 245), 256)) == 2
    assert len(a.binders((0, 244), 16)) == 1
    assert a.binders((0, 999), 256) == []


def test_incomplete_so_coverage_makes_every_unattributed_palette_shared_unknown():
    """The honest half of D5.  With no models at all there is NO EVIDENCE, not 100% coverage, so a
    palette nothing binds is SHARED-UNKNOWN and the spec must acknowledge it -- which is the guard
    W4's table defeated by construction on every effect but ef227."""
    blob = build_synth_container(npart=1, bindings=())
    a = RS.attribution(blob)
    assert (a.geom_total, a.geom_with_so) == (0, 0)
    assert not a.complete and a.coverage == 0.0
    pmap = RS.palette_map(blob)
    for name in (PAL_4BPP, PAL_8BPP):
        p = pmap.by_name(name)
        assert p.shared is True
        assert "SHARED-UNKNOWN" in p.shared_reason
    spec = _spec(blob, [{"name": PAL_4BPP, "hue_rotate": 30.0}])
    with pytest.raises(RS.ReskinError, match="SHARED palette"):
        RS.build(spec, "t", blob=blob)


# ============================================================ (1) BGR555 decode/encode round-trip
def test_apply_word_identity_transform_round_trips_every_16bit_word_including_stp():
    """The identity ``Transform()`` (hue 0, sat 1, val 1) must be BYTE-EXACT on EVERY possible
    16-bit word -- both STP states and all 32768 RGB combinations -- proving decode-then-encode is
    lossless before any hue/sat/val math is layered on top."""
    bad = []
    for w in range(65536):
        nw, clip = RS.apply_word(w, RS.Transform())
        if nw != w or clip:
            bad.append((w, nw, clip))
    assert not bad, bad[:10]


def test_apply_word_reconstructs_the_five_bit_channels_exactly_for_a_pure_hue_rotation():
    """A hue-only rotation (sat=val=1) must be an EXACT permutation of the 5-bit wheel: rotating by
    +120 degrees three times must return to the original word for every non-achromatic sample (an
    achromatic S=0 entry is invariant under hue rotation by construction, so it is excluded)."""
    for w in range(1, 65536, 37):
        r, g, b = w & 0x1F, (w >> 5) & 0x1F, (w >> 10) & 0x1F
        if r == g == b:                                        # achromatic: hue is undefined/inert
            continue
        cur = w
        for _ in range(3):
            cur, _clamped = RS.apply_word(cur, RS.Transform(hue=120.0))
        # 3 x 120deg == a full turn: same STP, same-ish colour (allow the 5-bit re-quantisation's
        # own rounding to differ by at most 1 per channel after three round-trips)
        assert (cur & 0x8000) == (w & 0x8000)
        for shift in (0, 5, 10):
            a, bch = (w >> shift) & 0x1F, (cur >> shift) & 0x1F
            assert abs(a - bch) <= 1, (hex(w), hex(cur))


# ============================================================ (2) the STP-preservation refusal
def test_apply_word_carries_stp_bit_never_recomputes_it():
    """Sweep a broad range of transforms (including ones no spec would ever declare) against words
    with STP both set and clear: bit 15 of the output must ALWAYS equal bit 15 of the input --
    ``apply_word`` slices it off before the HSV math and ORs it back after, so this cannot fail by
    construction; the sweep is the proof, not a hope."""
    hues = (0, 30, 90, 137.5, 182, 270, 359.9)
    sats = (0, 0.01, 0.5, 1.0, 2.0, 4.0)
    vals = (0, 0.01, 0.5, 1.0, 2.0, 4.0)
    checked = 0
    for w in range(1, 65536, 101):                            # word 0 is covered separately below
        for h in hues:
            for s in sats:
                for v in vals:
                    nw, _c = RS.apply_word(w, RS.Transform(hue=h, sat=s, val=v))
                    assert (nw & 0x8000) == (w & 0x8000), (hex(w), h, s, v, hex(nw))
                    checked += 1
    assert checked > 20000


def test_palette_result_ok_is_true_when_stp_populations_match():
    """The REAL check path: ``apply_palette`` on a genuine (small) CLUT, then ``.ok`` reads True
    because ``apply_word`` really did carry every STP bit."""
    blob = build_synth_container(npart=1)
    pmap = RS.palette_map(blob)
    pal = pmap.by_name("creature.part0")
    res = RS.apply_palette(blob, pal, RS.Transform(hue=77.0, sat=0.6, val=1.1))
    assert res.stp_stock == res.stp_new
    assert res.ok


def test_palette_result_ok_fires_false_on_a_crafted_stp_mismatch():
    """Prove the GUARD fires, not just that the honest path passes: take a real, good result and
    corrupt exactly the field the rule reads (``stp_new``) to simulate a hypothetical STP-flipping
    bug -- ``.ok`` must flip to False on that alone, with nothing else touched."""
    blob = build_synth_container(npart=1)
    pmap = RS.palette_map(blob)
    pal = pmap.by_name("creature.part0")
    good = RS.apply_palette(blob, pal, RS.Transform(hue=10.0))
    assert good.ok
    bad = dataclasses.replace(good, stp_new=good.stp_new + 1)
    assert not bad.ok
    # and the self_check-level expression (the one `self_check` itself evaluates per palette) agrees
    assert bad.stp_stock != bad.stp_new


# ============================================================ (3) entry-0 immutability
def test_apply_word_zero_entry_is_invariant_under_any_transform():
    """``0x0000`` must return ``0x0000`` under EVERY transform this sweep can construct -- rule 1
    is checked FIRST in ``apply_word``, before any HSV math runs at all."""
    hues = range(0, 360, 15)
    sats = (0, 0.5, 1.0, 2.0, 4.0, 1000.0)
    vals = (0, 0.5, 1.0, 2.0, 4.0, 1000.0)
    for h in hues:
        for s in sats:
            for v in vals:
                assert RS.apply_word(0, RS.Transform(hue=h, sat=s, val=v)) == (0, 0)


def test_entry0_guard_fires_on_a_crafted_non_zero_entry0():
    """Stock entry 0 of ``creature.part0`` is ``0x0000`` (by our fixture's own construction).  A
    genuine hue rotation cannot move it (previous test).  Here we simulate what WOULD happen if a
    hypothetical bug did move it -- corrupt ``result.new``'s own bytes so entry 0 reads non-zero --
    and confirm the exact boolean ``self_check`` evaluates per target
    (``_u16(stock,0)==0 and _u16(new,0)!=0``) reports it as a violation."""
    blob = build_synth_container(npart=1)
    pmap = RS.palette_map(blob)
    pal = pmap.by_name("creature.part0")
    good = RS.apply_palette(blob, pal, RS.Transform(hue=25.0))
    assert RS._u16(good.stock, 0) == 0                        # the fixture's own precondition
    assert RS._u16(good.new, 0) == 0                          # rule 1 held for real

    corrupted_new = bytearray(good.new)
    struct.pack_into("<H", corrupted_new, 0, 0x1234)          # simulate a broken transform
    bad = dataclasses.replace(good, new=bytes(corrupted_new))
    assert RS._u16(bad.stock, 0) == 0 and RS._u16(bad.new, 0) != 0, "the guard failed to fire"


def test_zero_positions_held_guard_fires_when_a_cutout_entry_moves():
    """The broader rule ("no 0x0000 moved, and no entry became one") is its own field
    (``zero_positions_held``); prove ``.ok`` reads it independently of the STP check by flipping
    ONLY this field on an otherwise-good result."""
    blob = build_synth_container(npart=1)
    pmap = RS.palette_map(blob)
    pal = pmap.by_name("creature.part0")
    good = RS.apply_palette(blob, pal, RS.Transform(hue=200.0))
    assert good.ok
    bad = dataclasses.replace(good, zero_positions_held=False)
    assert not bad.ok


# ============================================================ (4) channel clamping at 0/31
def test_clamp01_boundaries():
    assert RS._clamp01(-0.5) == 0.0
    assert RS._clamp01(1.5) == 1.0
    assert RS._clamp01(0.37) == 0.37
    assert RS._clamp01(0.0) == 0.0
    assert RS._clamp01(1.0) == 1.0


def test_apply_word_output_channels_always_land_in_0_31_even_at_extreme_scales():
    """``_clamp01`` bounds ``s``/``v`` into ``[0,1]`` BEFORE ``colorsys.hsv_to_rgb`` runs, and HSV's
    own algebra guarantees ``max(r,g,b) == v`` -- so no legal channel value can ever exceed 31,
    however large ``saturation``/``value`` are asked to go (the 4x ceiling is enforced by the SPEC
    layer, ``_transform_of``, not by ``apply_word`` itself).  This sweeps well past that ceiling to
    prove the OUTPUT stays in range regardless."""
    hues = (0, 45, 137.5, 271.3)
    extreme = (0, 0.01, 1.0, 4.0, 1000.0, 1_000_000.0)
    n = 0
    for w in range(1, 65536, 251):
        for h in hues:
            for s in extreme:
                for v in extreme:
                    nw, _c = RS.apply_word(w, RS.Transform(hue=h, sat=s, val=v))
                    r, g, b = nw & 0x1F, (nw >> 5) & 0x1F, (nw >> 10) & 0x1F
                    assert 0 <= r <= 31 and 0 <= g <= 31 and 0 <= b <= 31
                    n += 1
    assert n > 2000


def test_apply_word_channel_clamp_bit_is_structurally_unreachable():
    """``CLIP_CHANNEL`` can never fire through this path: ``_clamp01`` caps ``s``/``v`` to ``[0,1]``
    before the HSV math, and ``hsv_to_rgb``'s largest component is exactly ``v``, so
    ``int(f * 31.0 + 0.5)`` tops out at ``int(31.5) == 31``.

    This is pinned because it is exactly WHY the channel clamp must not be the reported instrument:
    a counter that cannot count reports "all clear" for every input, including a ruinous one.  The
    reachable clip -- the HSV one -- is what ``reskin`` counts and gates, and the two tests below
    prove THAT one fires."""
    hit = 0
    for w in range(0, 65536, 97):
        for h in (0, 90, 180, 270):
            for s in (0.0, 1.0, 4.0, 1e6):
                for v in (0.0, 1.0, 4.0, 1e6):
                    _nw, clip = RS.apply_word(w, RS.Transform(hue=h, sat=s, val=v))
                    hit |= clip & RS.CLIP_CHANNEL
    assert hit == 0


def test_apply_word_flags_a_value_knob_that_pushes_an_entry_past_the_cube():
    """THE REGRESSION TEST for the dead-instrument defect.  A bright entry under ``value > 1`` must
    set ``CLIP_VAL`` -- this is the case the old ``clamped`` counter reported as zero."""
    bright = 28 | (28 << 5) | (28 << 10)                        # V = 28/31 = 0.9032, ef227's own peak
    _nw, clip = RS.apply_word(bright, RS.Transform(val=1.12))   # 0.9032 * 1.12 = 1.0116 -> clipped
    assert clip & RS.CLIP_VAL
    assert not clip & RS.CLIP_SAT                               # achromatic: S = 0, nothing to clip
    assert not clip & RS.CLIP_CHANNEL                           # ...and the belt still never fires
    # ...and the SAME entry under a value that fits reports nothing
    _nw2, clip2 = RS.apply_word(bright, RS.Transform(val=1.10))  # 0.9032 * 1.10 = 0.9935 -> fits
    assert clip2 == 0


def test_apply_word_flags_a_saturation_knob_that_pushes_an_entry_past_the_cube():
    """The other half: a fully-saturated entry under ``saturation > 1`` sets ``CLIP_SAT``."""
    saturated = 31 | (0 << 5) | (0 << 10)                       # pure red: S = 1.00, V = 1.00
    _nw, clip = RS.apply_word(saturated, RS.Transform(sat=1.30))
    assert clip & RS.CLIP_SAT
    assert not clip & RS.CLIP_VAL                               # V = 1.00 * 1.00 fits exactly
    _nw2, clip2 = RS.apply_word(saturated, RS.Transform(sat=1.0))
    assert clip2 == 0


def test_apply_palette_counts_the_clip_per_palette_and_splits_saturation_from_value():
    """The counter has to survive the aggregation step too: ``apply_palette`` must report a non-zero
    ``clipped`` with the sat/value split and a ``worst_*`` overshoot above 1.0, and must report zero
    for a transform that fits."""
    blob = build_synth_container(npart=1)
    pmap = RS.palette_map(blob)
    pal = pmap.by_name("creature.part0")

    hot = RS.apply_palette(blob, pal, RS.Transform(val=3.0))
    assert hot.clipped > 0
    assert hot.val_clipped == hot.clipped and hot.sat_clipped == 0
    assert hot.worst_val > 1.0
    assert hot.chan_clamped == 0                                # the belt, still inert
    assert 0.0 < hot.clip_fraction <= 1.0

    calm = RS.apply_palette(blob, pal, RS.Transform(hue=90.0))
    assert calm.clipped == 0 and calm.sat_clipped == 0 and calm.val_clipped == 0
    assert calm.worst_val <= 1.0 and calm.clip_fraction == 0.0


def test_self_check_blowout_gate_FAILS_on_an_over_bright_knob_and_refuses_the_stage():
    """THE GATE, not the counter: a ``value`` large enough to flatten most of a palette onto the
    ceiling must make ``self_check`` report NOT ok, which is what stops ``reskin.py build`` from
    staging it.  This is the failure the old always-True gate would have printed as PASS."""
    blob = build_synth_container(npart=1)
    spec = _spec(blob, [{"name": "creature.part0", "hue_rotate": 0.0, "value": 3.0,
                         "acknowledge_headroom": True}])   # the fixture peaks at 31 (D4)
    b = RS.build(spec, "t", blob=blob)
    c = RS.self_check(b)
    blow = [g for g in c.rules if "flattens more than" in g.name]
    assert len(blow) == 1
    assert not blow[0].ok, blow[0].detail
    assert "BLOWN OUT" in blow[0].detail and "creature.part0" in blow[0].detail
    assert not c.ok                                             # -> `build` refuses to stage


def test_self_check_blowout_gate_PASSES_when_only_a_few_ceiling_entries_clip():
    """The gate must not be a tripwire on any clip at all: a handful of already-at-the-ceiling
    entries is normal (they cannot go further) and must still pass, with the census REPORTED."""
    blob = build_synth_container(npart=1)
    pmap = RS.palette_map(blob)
    pal = pmap.by_name("creature.part0")
    # find a value scale that clips a small, non-zero share of this fixture's own palette
    knob = next((v for v in [1.0 + i / 200.0 for i in range(1, 60)]
                 if 0 < RS.apply_palette(blob, pal, RS.Transform(val=v)).clip_fraction
                 <= RS.BLOWOUT_FRACTION), None)
    assert knob is not None, "the fixture palette admits no small-clip value knob"
    spec = _spec(blob, [{"name": "creature.part0", "value": knob,
                         "acknowledge_headroom": True}])   # the fixture peaks at 31 (D4)
    b = RS.build(spec, "t", blob=blob)
    c = RS.self_check(b)
    blow = [g for g in c.rules if "flattens more than" in g.name][0]
    assert blow.ok
    assert "clipped" in blow.detail and "creature.part0" in blow.detail    # reported, not hidden
    assert "BLOWN OUT" not in blow.detail


def test_self_check_channel_belt_gate_is_reported_separately_from_the_hsv_census():
    """The structural belt gets its OWN gate so the two are never confused again: it passes with a
    zero count, and its detail says WHY zero is expected rather than implying nothing clipped."""
    blob = build_synth_container(npart=1)
    spec = _spec(blob, [{"name": "creature.part0", "hue_rotate": 30.0}])
    b = RS.build(spec, "t", blob=blob)
    c = RS.self_check(b)
    belt = [g for g in c.rules if "channel clamp never had to fire" in g.name]
    assert len(belt) == 1 and belt[0].ok
    assert "0 entries clamped" in belt[0].detail
    assert "_clamp01" in belt[0].detail


# ============================================================ (5) build()-level refusals (7 kinds,
#     matching the B1 report's "7/7 negative tests refuse")
def test_build_refuses_a_shared_clut_named_without_acknowledgment():
    blob = build_synth_container(npart=1)
    spec = _spec(blob, [{"name": PAL_8BPP, "hue_rotate": 30.0}])
    with pytest.raises(RS.ReskinError, match="SHARED palette"):
        RS.build(spec, "t", blob=blob)


def test_build_accepts_a_shared_clut_named_with_acknowledgment():
    blob = build_synth_container(npart=1)
    spec = _spec(blob, [{"name": PAL_8BPP, "hue_rotate": 30.0,
                         "acknowledge_shared": True}])
    b = RS.build(spec, "t", blob=blob)
    assert b.targets[0].enabled and b.targets[0].result is not None
    assert len(b.patched) == len(b.orig)


def test_build_refuses_an_unknown_target_name():
    blob = build_synth_container(npart=1)
    spec = _spec(blob, [{"name": "creature.part99", "hue_rotate": 30.0}])
    with pytest.raises(RS.ReskinError, match="no palette named"):
        RS.build(spec, "t", blob=blob)


def test_build_refuses_a_drifted_stock_hash():
    blob = build_synth_container(npart=1)
    spec = _spec(blob, [{"name": "creature.part0", "hue_rotate": 30.0}])
    spec["reskin"]["expect_sha256"] = "0" * 64
    with pytest.raises(RS.R.StockDriftError):
        RS.build(spec, "t", blob=blob)


def test_build_refuses_a_saturation_scale_past_the_4x_clip_ceiling():
    blob = build_synth_container(npart=1)
    spec = _spec(blob, [{"name": "creature.part0", "hue_rotate": 30.0, "saturation": 4.01}])
    with pytest.raises(RS.ReskinError, match="above 4x"):
        RS.build(spec, "t", blob=blob)


def test_build_refuses_a_disagreeing_per_target_offset_guard():
    blob = build_synth_container(npart=1)
    spec = _spec(blob, [{"name": "creature.part0", "hue_rotate": 30.0, "expect_offset": 0x1234}])
    with pytest.raises(RS.ReskinError, match="the derivation says"):
        RS.build(spec, "t", blob=blob)


def test_build_refuses_a_disagreeing_vram_guard():
    blob = build_synth_container(npart=1)
    spec = _spec(blob, [{"name": "creature.part0", "hue_rotate": 30.0, "expect_vram": [1, 2]}])
    with pytest.raises(RS.ReskinError, match="the header declares"):
        RS.build(spec, "t", blob=blob)


def test_build_refuses_a_disagreeing_span_guard():
    blob = build_synth_container(npart=1)
    spec = _spec(blob, [{"name": "creature.part0", "hue_rotate": 30.0}],
                 spans={"creature_clut_strip": {"offset": 0x1234, "length": 999}})
    with pytest.raises(RS.ReskinError, match="refusing to splice"):
        RS.build(spec, "t", blob=blob)


# ============================================================ (6) span containment + orthogonality
#     falsifiability (the "regions" self-check, which reskin.py's own docstring files under
#     ORTHOGONALITY: "on top of that it gates whole regions byte-identical")
def test_self_check_flags_a_byte_changed_outside_every_named_span_and_region():
    """Plant a single byte diff INSIDE the creature's texture PAGES -- outside the
    ``creature_clut_strip`` span, outside the scenery span, and with zero enabled targets (so no
    target owns it either).  Every one of the following must independently notice:
      * accounting: the byte is unexplained (`in owner`) AND outside every derived span
      * regions: the id-4 header+texel region is no longer byte-identical
      * the dedicated "texel region untouched" gate also fails
    This is the falsifiability half of ORTHOGONALITY (reskin.py's own docstring: the self-check
    "gates whole regions byte-identical" IS the orthogonality proof's other leg, on top of the
    W2/W3 rebuild-intersection check)."""
    blob = build_synth_container(npart=2)
    pmap = RS.palette_map(blob)
    mp = KC.creature_package(blob)
    flip_off = mp.tex_file_offset + 100                       # well inside part0's page, not a CLUT
    patched = bytearray(blob)
    patched[flip_off] ^= 0xFF
    patched = bytes(patched)

    b = RS.Build(effect=999, label="synth", spec_path="t.toml", source="(synthetic)",
                orig=blob, patched=patched, sha_in=hashlib.sha256(blob).hexdigest(),
                sha_out=hashlib.sha256(patched).hexdigest(), pmap=pmap, targets=[])
    chk = RS.self_check(b)
    assert not chk.ok

    acc_by_name = {g.name: g for g in chk.accounting}
    assert acc_by_name["every changed byte belongs to a named target"].ok is False
    assert acc_by_name["every changed byte lands inside a derived CLUT span"].ok is False

    reg_by_name = {g.name: g for g in chk.regions}
    region_gate = reg_by_name["every geometry / program / camera / sequence region is "
                              "BYTE-IDENTICAL"]
    assert region_gate.ok is False
    assert "texel pages" in region_gate.detail

    texel_gate = reg_by_name["the id-4 TEXEL region is untouched and still decodes"]
    assert texel_gate.ok is False


def test_region_gate_fires_on_a_planted_diff_inside_the_id3_program_image():
    """The most literal reading of the falsifiability requirement: plant the diff inside the id-3
    resource itself -- ``_regions`` names it "id-3 effect program image" -- and confirm the regions
    gate catches exactly that hit, by name, while a build that never touches id-3 stays clean."""
    blob = build_synth_container(npart=1)
    pmap = RS.palette_map(blob)
    id3 = next(r for r in EC.parse_header(blob).chunks[0].resources if r.id == 3)
    patched = bytearray(blob)
    patched[id3.offset + 5] ^= 0xFF
    patched = bytes(patched)

    b = RS.Build(effect=999, label="synth", spec_path="t.toml", source="(synthetic)",
                orig=blob, patched=patched, sha_in=hashlib.sha256(blob).hexdigest(),
                sha_out=hashlib.sha256(patched).hexdigest(), pmap=pmap, targets=[])
    chk = RS.self_check(b)
    assert not chk.ok
    reg_by_name = {g.name: g for g in chk.regions}
    region_gate = reg_by_name["every geometry / program / camera / sequence region is "
                              "BYTE-IDENTICAL"]
    assert region_gate.ok is False
    assert "id-3 effect program image" in region_gate.detail


def test_self_check_passes_accounting_and_regions_for_a_real_target_driven_build():
    """The positive control: a build that only ever spliced bytes through a real, enabled target
    must report every accounting/region/rule gate clean (quality is NOT asserted here -- our
    synthetic CLUT is arithmetic noise, not a real palette, so the luminance-ordering quality gate
    is not expected to hold on it; that gate is about REAL art, not about this fixture).

    The saturation knob here is a REDUCTION for the same fixture reason: this synthetic CLUT is a
    modular arithmetic ramp, so an unnaturally large share of its entries sit at S = 1.00 and any
    saturation LIFT clips them (measured: ``1.2`` clips 63 of 510, 12.4%, past ``BLOWOUT_FRACTION``).
    That is a property of the fixture, not a defect -- the blow-out gate's own behaviour on a lift is
    asserted directly in section (4), on both sides."""
    blob = build_synth_container(npart=2)
    spec = _spec(blob, [{"name": "creature.part0", "hue_rotate": 90.0},
                        {"name": PAL_8BPP, "hue_rotate": 45.0, "saturation": 0.8,
                         "acknowledge_shared": True}])
    b = RS.build(spec, "t", blob=blob)
    chk = RS.self_check(b)
    for g in chk.accounting + chk.rules:
        assert g.ok, (g.name, g.detail)
    for g in chk.regions:
        assert g.ok, (g.name, g.detail)


def test_orthogonality_rebuild_gates_are_present_and_named():
    """``_orthogonality`` always emits exactly two named gates (W2 disjoint, W3 disjoint), whether
    or not the real specs/install are available -- a missing install turns them FAIL, not absent."""
    blob = build_synth_container(npart=1)
    pmap = RS.palette_map(blob)
    b = RS.Build(effect=999, label="synth", spec_path="t.toml", source="(synthetic)",
                orig=blob, patched=blob, sha_in=hashlib.sha256(blob).hexdigest(),
                sha_out=hashlib.sha256(blob).hexdigest(), pmap=pmap, targets=[])
    chk = RS.self_check(b)
    names = [g.name for g in chk.orthogonality]
    assert any("W2's rescore" in n for n in names)
    assert any("W3's retime" in n for n in names)


# ============================================================ (7) the ledger / revert round-trip,
#     in temp dirs, including --root
def _manifest(root) -> dict:
    out = {}
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            p = os.path.join(dirpath, f)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, root).replace("\\", "/")] = \
                    hashlib.sha256(fh.read()).hexdigest()
    return out


def _minimal_build(effect: int = 999, npart: int = 1) -> RS.Build:
    blob = build_synth_container(npart=npart)
    pmap = RS.palette_map(blob)
    patched = bytearray(blob)
    patched[EC.parse_header(blob).chunks[0].resources[1].offset] ^= 0xFF   # id-3 filler, any change
    patched = bytes(patched)
    return RS.Build(effect=effect, label="synth", spec_path="t.toml", source="(synthetic)",
                    orig=blob, patched=patched, sha_in=hashlib.sha256(blob).hexdigest(),
                    sha_out=hashlib.sha256(patched).hexdigest(), pmap=pmap, targets=[])


@pytest.mark.parametrize("seed_existing", [False, True])
def test_deploy_and_revert_round_trip_on_a_fake_mod_folder(tmp_path, seed_existing):
    """Proven against a MOCK live tree, never the install -- both the fresh-folder and the
    already-carrying-an-override cases, plus idempotent re-deploy and re-revert."""
    b = _minimal_build()
    game_root = tmp_path / "FAKE_GAME"
    mod = game_root / "FF9CustomMap"
    dest_dir = mod / "FF9_Data" / "SpecialEffects"
    dest_dir.mkdir(parents=True)
    prior = b"a pre-existing override that must come back byte-for-byte" if seed_existing else None
    if prior is not None:
        (dest_dir / "ef999").write_bytes(prior)
    before = _manifest(mod)

    out = RS.stage(b, root=tmp_path / "stage", game_root=str(game_root), previews=False)
    p = subprocess.run([sys.executable, out["scripts"]["deploy"]], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    assert (dest_dir / "ef999").read_bytes() == b.patched

    # re-deploy is idempotent (the snapshot is taken once and reused)
    p2 = subprocess.run([sys.executable, out["scripts"]["deploy"]], capture_output=True, text=True)
    assert p2.returncode == 0
    assert (dest_dir / "ef999").read_bytes() == b.patched

    p3 = subprocess.run([sys.executable, out["scripts"]["revert"]], capture_output=True, text=True)
    assert p3.returncode == 0, p3.stdout + p3.stderr
    after = _manifest(mod)
    assert after == before
    if seed_existing:
        assert (dest_dir / "ef999").read_bytes() == prior
    else:
        assert not (dest_dir / "ef999").exists()

    # a second revert is idempotent
    p4 = subprocess.run([sys.executable, out["scripts"]["revert"]], capture_output=True, text=True)
    assert p4.returncode == 0
    assert _manifest(mod) == before


def test_deploy_script_refuses_with_no_root_and_succeeds_with_an_explicit_root_flag(tmp_path):
    """The W3-verifier-incident rule: a plan with no baked default mod folder (``game_root=None``
    at stage time) must REFUSE outright rather than guess, and must accept ``--root`` explicitly."""
    b = _minimal_build()
    out = RS.stage(b, root=tmp_path / "stage", game_root=None, previews=False)

    p = subprocess.run([sys.executable, out["scripts"]["deploy"]], capture_output=True, text=True)
    assert p.returncode != 0
    assert "no mod root" in p.stdout

    mod = tmp_path / "FAKE_GAME2" / "FF9CustomMap"
    (mod / "FF9_Data" / "SpecialEffects").mkdir(parents=True)
    p2 = subprocess.run([sys.executable, out["scripts"]["deploy"], "--root", str(mod)],
                        capture_output=True, text=True)
    assert p2.returncode == 0, p2.stdout + p2.stderr
    dest = mod / "FF9_Data" / "SpecialEffects" / "ef999"
    assert dest.read_bytes() == b.patched

    p3 = subprocess.run([sys.executable, out["scripts"]["revert"], "--root", str(mod)],
                        capture_output=True, text=True)
    assert p3.returncode == 0
    assert not dest.exists()


def test_deploy_refuses_a_mod_folder_carrying_a_modfilelist(tmp_path):
    """``TryFindAssetInModOnDisc`` TRUSTS an existing ``ModFileList.txt`` and never calls
    ``File.Exists``, so an unlisted override would be silently invisible -- the generated deploy
    script refuses outright rather than writing a file the engine will never find."""
    b = _minimal_build()
    mod = tmp_path / "FAKE_GAME" / "FF9CustomMap"
    mod.mkdir(parents=True)
    (mod / "ModFileList.txt").write_text("something/else\n", encoding="utf-8")
    out = RS.stage(b, root=tmp_path / "stage", game_root=str(tmp_path / "FAKE_GAME"), previews=False)
    p = subprocess.run([sys.executable, out["scripts"]["deploy"]], capture_output=True, text=True)
    assert p.returncode != 0
    assert "ModFileList.txt" in p.stdout


# ============================================================ (8) staging refusals (provenance)
def test_staging_refuses_the_repo():
    _repo = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
    with pytest.raises(RS.R.RescoreError, match="repo"):
        RS.R._refuse_repo_path(os.path.join(_repo, "studies", "x"))


def test_staging_refuses_the_install_unless_allow_install(tmp_path):
    game = tmp_path / "FINAL FANTASY IX"
    (game / "FF9CustomMap").mkdir(parents=True)
    b = _minimal_build()
    with pytest.raises(RS.R.RescoreError, match="game install"):
        RS.stage(b, root=game / "FF9CustomMap", game_root=str(game), previews=False)


# ============================================================ (9) the real install + corpus (skipped
#     when absent) -- exercises the ACTUAL shipped bahamut_reskin.toml against ef227
@needs_install
def test_the_shipped_spec_builds_and_self_checks_against_this_install():
    spec = RS.load_spec(SPEC)
    b = RS.build(spec, SPEC)
    b.check = RS.self_check(b)
    assert len(b.patched) == len(b.orig)
    assert b.check.ok, "\n".join("%s: %s" % (g.name, g.detail) for g in b.check.gates if not g.ok)


@needs_install
def test_every_reskin_spec_beside_this_tool_builds_and_self_checks():
    """THE SPEC-REGISTRY GATE (W5 reconcile).

    ``w4_gates`` builds ONE spec -- ``bahamut_reskin.toml``, its hardcoded ``SPEC`` -- while W5 added
    ``phoenix_reskin.toml`` and ``madeen_reskin.toml`` beside it.  A committable spec that no runner
    ever builds is a file that can rot silently through the next refactor, which is exactly the hole
    ``rescore.discover_specs`` closed on the camera lane.  Here every ``*_reskin.toml`` in this
    directory must load, build, keep its length and pass its own self-check; ef227's is additionally
    pinned to the deployed artifact's sha."""
    specs = sorted(glob.glob(os.path.join(os.path.dirname(SPEC), "*_reskin.toml")))
    assert len(specs) >= 3, specs                       # bahamut + phoenix + madeen at minimum
    seen = {}
    for path in specs:
        b = RS.build(RS.load_spec(path), path)
        b.check = RS.self_check(b)
        assert len(b.patched) == len(b.orig), path
        assert b.check.ok, "%s:\n%s" % (path, "\n".join("%s: %s" % (g.name, g.detail)
                                                        for g in b.check.gates if not g.ok))
        assert b.guard != "none -- UNGUARDED (allow_unguarded = true)", \
            "%s ships without a drift guard" % path
        seen[b.effect] = b.sha_out
    assert seen.get(227) == W4_PATCHED_SHA256
    assert len(seen) == len(specs), "two specs target the same effect: %s" % seen


@needs_install
def test_the_install_still_matches_the_registered_drift_hash():
    import rescore as R
    blob, src = R.read_stock_effect(227)
    assert R.drift_guard(227, blob) == RS.R.EXPECTED_STOCK_SHA[227]
    assert "resources.assets" in src


@needs_install
def test_the_shipped_ef227_artifact_is_still_byte_identical_after_the_generalisation():
    """THE W5 BYTE-COMPAT GATE, at the unit level.  W5 renamed every derived span and palette, moved
    attribution from a table to a derivation, and added five refusals -- and the artifact ef227's own
    spec produces must not have moved by ONE BYTE, because it is deployed and cast-proven."""
    b = RS.build(RS.load_spec(SPEC), SPEC)
    assert b.sha_out == W4_PATCHED_SHA256
    assert b.pmap.envelope == 8192                          # A2's edit menu (c), now DERIVED
    assert len(b.pmap.spans) == 4


@needs_install
def test_ef227s_legacy_span_and_target_names_still_resolve_through_the_alias_map():
    """D1's compatibility half.  The shipped spec says ``c1_clut_band0`` and ``scenery.sky_dome``;
    the derivation now says ``s1_clut_band0`` and ``pal.s0.x0_y245.e256``.  Both must resolve, and
    the ef227 overlay must be an ALIAS on the derived palette -- never a second palette."""
    import rescore as R
    blob, _src = R.read_stock_effect(227)
    pmap = RS.palette_map(blob, effect=227)
    assert pmap.span("c1_clut_band0") is pmap.span("s1_clut_band0")
    assert pmap.span("creature_clut_strip").size == 3072
    sky = pmap.by_name("scenery.sky_dome")
    assert sky.name == "pal.s0.x0_y245.e256" and sky.alias == "scenery.sky_dome"
    assert pmap.by_name("spare.c1_x0_y242").name == "pal.s1.x0_y242.e256"
    # ...and WITHOUT the overlay the English names are simply not there
    plain = RS.palette_map(blob)
    with pytest.raises(RS.ReskinError, match="no palette named"):
        plain.by_name("scenery.sky_dome")


@needs_install
def test_the_derived_shared_flags_reproduce_ef227s_hand_table_exactly():
    """The claim D5 rests on: the ``so``-record derivation is not a NEW answer, it is the SAME answer
    W4 typed out by hand -- on the one effect where the hand answer was checked.  ef227 has COMPLETE
    coverage (15 of 15 non-creature GEOM blocks bound), ``(0,244)`` comes back with 2 binders and
    ``(192,244)`` with 3 (both SHARED, exactly the two rows the shipped spec acknowledges), and the
    other five attributed cells come back single-bound."""
    import rescore as R
    blob, _src = R.read_stock_effect(227)
    pmap = RS.palette_map(blob, effect=227)
    assert pmap.attrib.complete and (pmap.attrib.geom_with_so, pmap.attrib.geom_total) == (15, 15)
    shared = {p.alias for p in pmap.palettes if p.shared and p.alias}
    assert shared == {"scenery.water_and_sky_gradient", "scenery.cloud_bands"}
    for alias in ("scenery.sky_dome", "scenery.energy_rings", "scenery.cloud_sheet",
                  "scenery.aerial_ground", "scenery.fire_column"):
        p = pmap.by_name(alias)
        assert p.shared is False and len(p.binders) == 1, (alias, p.shared_reason)


@needs_install
def test_ef227s_preview_page_columns_are_derived_and_match_the_hand_table():
    """D5 (iii) / D6.  W4 hard-coded ``PREVIEW_PAGE`` (5 rows) and ``ID9_SLOT_FILE`` (2 offsets);
    both are now derived from the ``so`` binding's own TPAGE plus the id-9 ``info`` bitmask, and the
    derivation reproduces every one -- including the two that disagree with the naive reading."""
    import rescore as R
    blob, _src = R.read_stock_effect(227)
    pmap = RS.palette_map(blob, effect=227)
    want = {"scenery.sky_dome": ("s0", 704), "scenery.energy_rings": ("s0", 448),
            "scenery.aerial_ground": ("s0", 576), "scenery.cloud_sheet": ("id9.s0", 832),
            "scenery.fire_column": ("s1", 832)}
    for alias, (src, x) in want.items():
        rects = RS.preview_source(blob, pmap.by_name(alias), pmap.attrib)
        assert rects and (rects[0].source, rects[0].x) == (src, x), alias
        assert sum(r.nbytes for r in rects) == 0x8000
    # the id-9 slot arithmetic, against the two offsets W4 measured by hand
    assert [r.off for r in RS.id9_pages(blob)[("s0", 832)]] == [0x03A000, 0x03E000]


# ============================================================ (10) W5 -- THE GENERALISATION
# Every refusal this rung added, on bytes this file wrote (no corpus, no install), plus the corpus
# sweep as a corpus-gated test.  The naming/derivation half lives in section (0)'s own sanity tests.
def test_id9_slot_vram_is_the_loops_own_arithmetic():
    """D6: ``fn 0x3E4AB``'s destination math, read off ``0x3e50d..0x3e553``.  A1 states the eight
    landing sites for ef227's ``info = 51``; this pins the FORMULA that produces them."""
    assert [RS.id9_slot_vram(i) for i in range(8)] == [
        (768, 256), (768, 384), (832, 256), (832, 384),
        (320, 256), (320, 384), (384, 256), (384, 384)]
    assert RS.ID9_SLOT_BIT == (0, 0, 1, 1, 2, 3, 4, 5)


def test_the_multiwriter_and_dual_depth_detectors_fire_on_a_hand_built_container():
    """D2's detector, before its refusals: two chunks writing the same VRAM cells."""
    blob = build_synth_multiwriter_container()
    pmap = RS.palette_map(blob)
    haz = pmap.hazards
    assert set(haz) == {(0, 244), (0, 245)}
    assert haz[(0, 245)].multi_writer and not haz[(0, 245)].dual_depth
    assert haz[(0, 244)].multi_writer and haz[(0, 244)].dual_depth
    assert len(set(haz[(0, 245)].offsets)) == 2
    # a single-chunk container has none of this
    assert RS.palette_map(build_synth_container(npart=1)).hazards == {}


def test_build_refuses_a_dual_depth_cell_outright():
    """D2: the 16-entry and 256-entry readings of one cell are two pictures over the same bytes.
    No acknowledgement lifts this -- there is no evidence either way (ef447's (0,242))."""
    blob = build_synth_multiwriter_container()
    spec = _spec(blob, [{"name": "pal.s0.x0_y244.e16", "hue_to": 200.0,
                         "acknowledge_shared": True}])
    with pytest.raises(RS.ReskinError, match="DUAL-DEPTH"):
        RS.build(spec, "t", blob=blob)


def test_build_refuses_a_multiwriter_cell_when_only_some_writers_are_named():
    blob = build_synth_multiwriter_container()
    spec = _spec(blob, [{"name": "pal.s0.x0_y245.e256", "hue_to": 200.0,
                         "acknowledge_shared": True}])
    with pytest.raises(RS.ReskinError, match="MULTI-WRITER"):
        RS.build(spec, "t", blob=blob)


def test_build_refuses_a_multiwriter_co_transform_authored_as_a_hue_rotate_delta():
    """The subtle half of D2: naming every writer is not enough.  Each writer has its OWN mean hue,
    so one shared ``hue_rotate`` delta lands them on different hues -- the exact flicker the gate
    exists to stop.  Only the absolute ``hue_to`` form is coherent."""
    blob = build_synth_multiwriter_container()
    rows = [{"name": n, "hue_rotate": 40.0, "acknowledge_shared": True}
            for n in ("pal.s0.x0_y245.e256", "pal.s1.x0_y245.e256")]
    with pytest.raises(RS.ReskinError, match="ABSOLUTE `hue_to`"):
        RS.build(_spec(blob, rows), "t", blob=blob)


def test_build_accepts_a_multiwriter_co_transform_authored_with_hue_to():
    """...and with ``hue_to`` it builds, with both writers landing on the SAME absolute hue even
    though their stock means differ -- which is the whole point."""
    blob = build_synth_multiwriter_container()
    names = ("pal.s0.x0_y245.e256", "pal.s1.x0_y245.e256")
    rows = [{"name": n, "hue_to": 200.0, "acknowledge_shared": True} for n in names]
    b = RS.build(_spec(blob, rows), "t", blob=blob)
    assert len(b.enabled) == 2
    means = [RS.palette_mean_hue(blob, t.pal) for t in b.enabled]
    assert abs(means[0] - means[1]) > 1e-6, "the fixture's two writers must differ to prove this"
    for t in b.enabled:
        assert abs(((t.result.hue_after - 200.0 + 180.0) % 360.0) - 180.0) < 12.0


def test_hue_to_is_hue_rotate_minus_the_measured_mean_and_they_cannot_both_be_declared():
    """D8, at the arithmetic."""
    blob = build_synth_container(npart=1)
    pmap = RS.palette_map(blob)
    pal = pmap.by_name("creature.part0")
    mean = RS.palette_mean_hue(blob, pal)
    b = RS.build(_spec(blob, [{"name": "creature.part0", "hue_to": 210.0}]), "t", blob=blob)
    t = b.targets[0].t
    assert t.hue_to == 210.0
    assert abs(((t.hue - (210.0 - mean) + 180.0) % 360.0) - 180.0) < 1e-9
    with pytest.raises(RS.ReskinError, match="BOTH `hue_to` and `hue_rotate`"):
        RS.build(_spec(blob, [{"name": "creature.part0", "hue_to": 1.0, "hue_rotate": 2.0}]),
                 "t", blob=blob)


def test_a_row_level_hue_to_beats_an_inherited_default_hue_rotate():
    """``[reskin.defaults] hue_rotate = 0.0`` is what every shipped spec writes, so an absolute row
    has to win over it rather than colliding with it."""
    blob = build_synth_container(npart=1)
    spec = _spec(blob, [{"name": "creature.part0", "hue_to": 90.0}])
    spec["reskin"]["defaults"] = {"hue_rotate": 0.0, "saturation": 1.0, "value": 1.0}
    b = RS.build(spec, "t", blob=blob)
    assert b.targets[0].t.hue_to == 90.0 and b.targets[0].t.hue != 0.0


def test_texanim_region_is_measured_from_the_id4_header():
    """D3's instrument: ``firstBlock`` vs ``motionOffsets[0]``, both header-relative."""
    assert not RS.texanim_region(build_synth_container(npart=1)).armed
    ta = RS.texanim_region(build_synth_container(npart=1, texanim=364))
    assert ta.present and ta.armed and ta.nbytes == 364 and ta.hi - ta.lo == 364
    none = RS.texanim_region(build_synth_creatureless_container())
    assert not none.present and not none.armed


def _armed_parsed_blob(npart: int = 2) -> bytes:
    """The synthetic container with a texanim region that actually DECODES -- W7's lift fixture.

    ``build_synth_container(texanim=N)`` arms N bytes of FILLER, which the reader refuses; that is a
    real case (it is the armed-and-unread one), but it cannot prove a lift.  The region generator
    lives with the kit reader's own tests and is IMPORTED rather than copied -- one generator, so a
    study pin and a kit pin can never drift into testing two different formats.  Deferred, because
    that module imports the kit's container fixture and a module-level import here would drag the
    whole kit test package in at collection time.
    """
    from tests.test_summon_texanim import armed_blob, synth_116
    return armed_blob(synth_116(), npart=npart)


def test_a_creature_recolour_builds_under_an_armed_texanim():
    """W7 L1, THE LIFT -- this pin is INVERTED from the W5 refusal it replaces, in lockstep with the
    kit's own ``test_a_creature_recolour_builds_under_an_armed_texanim``.

    W5 refused a creature recolour on the five armed packages because the table's format was unread
    and one branch it might have implemented (cycling the per-part CLUT WORD) would have made a static
    recolour pointless.  W7 read it: the table blits 8-bit palette INDICES inside ONE creature part's
    own 128x128 page, binds no CLUT word and writes no CLUT contents -- so a recolour survives it by
    construction, under both the "it runs" and the "it does not run" reading.  What replaces the
    refusal is THE REGION INVARIANT, and that is what this test actually pins: the region comes back
    byte-identical.
    """
    blob = _armed_parsed_blob()
    ta = RS.texanim_region(blob)
    assert ta.armed and TA.read(blob).parsed, "the fixture must be armed AND decodable"
    b = RS.build(_spec(blob, [{"name": "creature.part0", "hue_rotate": 30.0}]), "t", blob=blob)
    assert len(b.enabled) == 1 and b.patched != b.orig
    assert b.patched[ta.lo:ta.hi] == b.orig[ta.lo:ta.hi], "THE REGION INVARIANT: region bytes moved"
    assert "byte-identical" in b.region_invariant
    assert any("DECODED" in n for n in b.notes), "the lift DISCLOSES the decode, it is never silent"


def test_an_armed_texanim_that_does_NOT_decode_still_refuses_a_creature_recolour():
    """THE FALLBACK CONTRACT, and the reason the lift is safe to ship: it is conditional on a
    successful PARSE, never on the absence of an exception.  An armed region the reader cannot decode
    is the pre-W7 state, so the pre-W7 refusal is exactly what an author gets -- verbatim, and with no
    key able to lift it."""
    blob = build_synth_container(npart=1, texanim=116)        # armed, contents are filler
    assert RS.texanim_region(blob).armed and TA.read(blob).unparseable
    spec = _spec(blob, [{"name": "creature.part0", "hue_rotate": 30.0}])
    with pytest.raises(RS.ReskinError, match="TEXANIM ARMED"):
        RS.build(spec, "t", blob=blob)
    # ...and the deprecated key does NOT lift it either
    spec["reskin"]["acknowledge_texanim"] = True
    with pytest.raises(RS.ReskinError, match="recolours the CREATURE"):
        RS.build(spec, "t", blob=blob)


def test_scenery_builds_under_an_armed_PARSED_texanim_with_no_key_and_the_old_key_is_a_deprecated_noop():
    """W7 L2, INVERTED -- for a table that DECODES.  W5's scenery hedge said "orthogonality assumed,
    not proven"; it is a MEASUREMENT now -- every clip in every armed table names a CREATURE part and
    every rect is local to that part's own page (``x+w <= 64`` halfwords, 39/39 stock clips), so the
    table cannot reach a scenery page at all.  ``acknowledge_texanim`` survives as a parseable NO-OP
    on this path, so a W5-era scaffold's own output keeps building, and the report says so."""
    rows = [{"name": PAL_4BPP, "hue_rotate": 30.0}]
    blob = _armed_parsed_blob()
    assert RS.texanim_region(blob).armed and TA.read(blob).parsed
    assert len(RS.build(_spec(blob, rows), "t", blob=blob).enabled) == 1, \
        "scenery needs no key when the table decodes -- it is out of the table's measured reach"
    spec = _spec(blob, rows)
    spec["reskin"]["acknowledge_texanim"] = True
    b = RS.build(spec, "t", blob=blob)
    assert len(b.enabled) == 1 and b.check is None
    assert any("DEPRECATED KEY `acknowledge_texanim`" in n for n in b.notes)


def test_scenery_under_an_armed_UNPARSEABLE_texanim_needs_the_old_key_in_its_original_meaning():
    """THE FALLBACK CONTRACT, scenery half (V1 F1).  The measurement that deprecated the key never
    ran on a table the reader cannot decode -- so the pre-W7 posture stands verbatim: scenery
    REFUSES without ``acknowledge_texanim``, builds WITH it, and the note calls the table
    UNDECODABLE rather than the key deprecated."""
    rows = [{"name": PAL_4BPP, "hue_rotate": 30.0}]
    blob = build_synth_container(npart=1, texanim=116)        # armed, contents are filler
    assert RS.texanim_region(blob).armed and TA.read(blob).unparseable
    with pytest.raises(RS.ReskinError, match="does not DECODE"):
        RS.build(_spec(blob, rows), "t", blob=blob)
    spec = _spec(blob, rows)
    spec["reskin"]["acknowledge_texanim"] = True
    b = RS.build(spec, "t", blob=blob)
    assert len(b.enabled) == 1
    assert any("UNDECODABLE" in n and "ORIGINAL, pre-W7 meaning" in n for n in b.notes)
    assert not any("DEPRECATED KEY" in n for n in b.notes)


def test_a_disabled_target_does_not_trip_the_texanim_or_shared_gates():
    """A row that splices nothing states an INTENT; its acknowledgements become mandatory the moment
    it is switched on.  This is what lets a scaffold ship every declared palette, pre-seeded off."""
    blob = build_synth_container(npart=1, texanim=116)
    spec = _spec(blob, [{"name": "creature.part0", "hue_rotate": 30.0, "enabled": False},
                        {"name": PAL_8BPP, "hue_rotate": 30.0, "enabled": False}])
    b = RS.build(spec, "t", blob=blob)
    assert b.enabled == [] and b.patched == b.orig


def test_headroom_is_derived_per_target_and_a_zero_headroom_value_lift_refuses():
    """D4.  A palette already on the 5-bit ceiling has NO headroom, so a ``value > 1`` can only
    flatten -- and 46 of the corpus's 93 creature rows are in that class, where ef227's six are not.
    The refusal is answerable with ``acknowledge_headroom``, and a ``value <= 1`` never trips it."""
    blob = build_synth_container(npart=1)
    pmap = RS.palette_map(blob)
    pal = pmap.by_name("creature.part0")
    assert RS.palette_peak(blob, pal) == 31                  # the fixture's own precondition
    res = RS.apply_palette(blob, pal, RS.Transform())
    assert res.peak_stock == 31 and res.headroom == 0 and res.value_ceiling == 1.0

    with pytest.raises(RS.ReskinError, match="ZERO HEADROOM"):
        RS.build(_spec(blob, [{"name": "creature.part0", "value": 1.05}]), "t", blob=blob)
    ack = RS.build(_spec(blob, [{"name": "creature.part0", "value": 1.05,
                                 "acknowledge_headroom": True}]), "t", blob=blob)
    assert ack.enabled[0].result.clipped > 0
    calm = RS.build(_spec(blob, [{"name": "creature.part0", "value": 1.0,
                                  "saturation": 0.8}]), "t", blob=blob)
    assert calm.enabled[0].result.peak_stock == 31


def test_a_palette_with_real_headroom_is_not_refused():
    """The other side of D4: the gate is about ZERO headroom, not about `value > 1` in general --
    otherwise it would refuse ef227's own shipped spec, whose worst row peaks at 28 of 31."""
    blob = build_synth_container(npart=1)
    pmap = RS.palette_map(blob)
    pal = pmap.by_name(PAL_4BPP)
    peak = RS.palette_peak(blob, pal)
    assert peak < 31, "the fixture's 4bpp row must have headroom for this test to mean anything"
    b = RS.build(_spec(blob, [{"name": PAL_4BPP, "value": 1.05,
                               "acknowledge_shared": True}]), "t", blob=blob)
    assert b.enabled[0].result.headroom == 31 - peak


def test_build_refuses_an_effect_with_no_drift_guard_at_all():
    """Refusal 2 of the gate list.  W4 merely PRINTED "unguarded" here, so a patched install could
    move a span under the edit and nothing would notice."""
    blob = build_synth_container(npart=1)
    spec = {"reskin": {"effect": 999, "target": [{"name": "creature.part0"}]}}
    with pytest.raises(RS.ReskinError, match="NO drift guard"):
        RS.build(spec, "t", blob=blob)
    spec["reskin"]["allow_unguarded"] = True
    assert RS.build(spec, "t", blob=blob).sha_in


def test_describe_names_the_drift_guard_that_actually_applied():
    """B5 defect 4.  `describe` decided "guarded" from ``effect in rescore.EXPECTED_STOCK_SHA``
    alone, so every generalised effect -- the normal case on this tool -- printed
    "(drift guard none -- unguarded)" even while :func:`build` was ENFORCING the spec's own
    ``expect_sha256`` (proven by the StockDriftError tests).  A report that says "unguarded" about a
    guarded build is a lie in the one direction that gets a guard deleted."""
    blob = build_synth_container(npart=1)
    sha = hashlib.sha256(blob).hexdigest()

    guarded = {"reskin": {"effect": 999, "expect_sha256": sha,
                          "target": [{"name": "creature.part0"}]}}
    b = RS.build(guarded, "t", blob=blob)
    assert b.guard == "the spec's own expect_sha256 -- MATCHES"
    line = next(l for l in RS.describe(b) if "drift guard" in l)
    assert "expect_sha256" in line and "unguarded" not in line.lower()

    bare = {"reskin": {"effect": 999, "allow_unguarded": True,
                       "target": [{"name": "creature.part0"}]}}
    b2 = RS.build(bare, "t", blob=blob)
    assert "UNGUARDED" in b2.guard
    assert "UNGUARDED" in next(l for l in RS.describe(b2) if "drift guard" in l)

    # ...and a REGISTERED effect (no spec hash) still reports the registry
    registered = {"reskin": {"effect": 227, "target": [{"name": "creature.part0"}]}}
    monkey = dict(RS.R.EXPECTED_STOCK_SHA)
    monkey[227] = sha
    old, RS.R.EXPECTED_STOCK_SHA = RS.R.EXPECTED_STOCK_SHA, monkey
    try:
        b3 = RS.build(registered, "t", blob=blob)
        assert b3.guard.startswith("REGISTERED in rescore.EXPECTED_STOCK_SHA")
    finally:
        RS.R.EXPECTED_STOCK_SHA = old


def test_two_target_rows_naming_the_same_derived_palette_refuse():
    """The alias map makes two spellings of one palette possible, so the duplicate check has to run
    on the DERIVED name, not on the spelling."""
    blob = build_synth_container(npart=1)
    rows = [{"name": PAL_4BPP, "hue_rotate": 10.0, "acknowledge_shared": True},
            {"name": "spare.c0_x0_y244", "hue_rotate": 20.0, "acknowledge_shared": True}]
    with pytest.raises(RS.ReskinError, match="both resolve to the derived palette"):
        RS.build(_spec(blob, rows), "t", blob=blob)


def test_legacy_chunk_index_aliases_are_suppressed_when_chunk_index_is_ambiguous():
    """D1's precondition, enforced.  ef381's nine chunks all carry ``chunk_index`` 1 except the
    first, so a ``c1_...`` name cannot mean anything -- and the alias map must be EMPTY rather than
    resolve one of eight spans arbitrarily (which is what W4's ``span()`` did: it returned the
    first match, so a TOML guard silently validated the wrong span)."""
    ok = RS.palette_map(build_synth_multiwriter_container((0, 1)))
    assert ok.span_aliases and ok.span("c1_clut_band0").name == "s1_clut_band0"
    ambiguous = RS.palette_map(build_synth_multiwriter_container((0, 0)))
    assert ambiguous.aliases == {} and ambiguous.span_aliases == {}
    with pytest.raises(RS.ReskinError, match="no span named"):
        ambiguous.span("c1_clut_band0")


def test_scenery_only_reskin_of_a_creature_less_container(tmp_path):
    """D9.  348 of the 372 corpus containers have no id-4 at all; W4 raised on all of them."""
    blob = build_synth_creatureless_container()
    pmap = RS.palette_map(blob)
    assert pmap.creature_error and not any(p.name.startswith("creature.") for p in pmap.palettes)
    b = RS.build(_spec(blob, [{"name": PAL_8BPP, "hue_rotate": 40.0,
                               "acknowledge_shared": True}]), "t", blob=blob)
    b.check = RS.self_check(b)
    for g in b.check.accounting + b.check.rules + b.check.regions:
        assert g.ok, (g.name, g.detail)
    texel = [g for g in b.check.regions if "TEXEL region" in g.name][0]
    assert "NOT APPLICABLE" in texel.detail
    with pytest.raises(RS.ReskinError, match="creature scope is unavailable"):
        RS.build(_spec(blob, [{"name": "creature.part0"}]), "t", blob=blob)


def test_orthogonality_skips_a_sibling_spec_that_targets_another_effect():
    """D10.  Rebuilding *Bahamut's* camera and clocks proves nothing about a reskin of ef211, so the
    gate must SKIP with the reason stated rather than pass or fail silently."""
    blob = build_synth_container(npart=1)
    b = RS.build(_spec(blob, [{"name": "creature.part0", "hue_rotate": 10.0}]), "t", blob=blob)
    gates = RS._orthogonality(b, set())
    assert len(gates) == 2 and all(g.ok for g in gates)
    assert all("SKIPPED" in g.detail and "ef227" in g.detail for g in gates)


def test_orthogonality_fails_loudly_when_the_spec_names_a_sibling_that_does_not_exist():
    """...but a spec that NAMES a sibling and is wrong about it must not be quietly skipped."""
    blob = build_synth_container(npart=1)
    spec = _spec(blob, [{"name": "creature.part0", "hue_rotate": 10.0}])
    spec["reskin"]["orthogonality"] = {"rescore": "no_such_spec.toml"}
    b = RS.build(spec, "t", blob=blob)
    gates = {g.name: g for g in RS._orthogonality(b, set())}
    bad = [g for g in gates.values() if "rescore" in g.name][0]
    assert not bad.ok and "NAMED it" in bad.detail


def test_staging_root_is_per_effect_and_ef227_keeps_w4s_layout():
    """D11.  W4 had ONE root, so two effects staged in one session overwrote each other."""
    assert RS.staging_root(227) == RS.SCRATCH_W4_ROOT
    assert RS.staging_root(211) == os.path.join(RS.SCRATCH_W5_BASE, "ef211")
    assert RS.staging_root(211) != RS.staging_root(251)
    assert RS.SCRATCH_ROOT == RS.SCRATCH_W4_ROOT             # the W4 gate runner's own name


def test_stage_defaults_to_the_per_effect_root(tmp_path, monkeypatch):
    monkeypatch.setattr(RS, "SCRATCH_W5_BASE", str(tmp_path / "w5"))
    b = _minimal_build(effect=998)
    out = RS.stage(b, game_root=None, previews=False)
    assert out["staging_root"] == str(tmp_path / "w5" / "ef998")
    assert os.path.isfile(out["container"])


def test_scaffold_emits_a_toml_that_parses_builds_and_changes_nothing(tmp_path):
    """D7.  A scaffold is only useful if it is COMPLETE and INERT: every guard emitted, every knob at
    identity, every acknowledgement pre-seeded false -- so the first build is provably a no-op and
    the author moves one number at a time."""
    blob = build_synth_container(npart=2)
    text, pmap = RS.scaffold(999, blob=blob, source="(fixture)")
    doc = _load_toml_text(text)
    assert doc["reskin"]["effect"] == 999
    assert doc["reskin"]["expect_sha256"] == hashlib.sha256(blob).hexdigest()
    assert len(doc["reskin"]["target"]) == len(pmap.palettes)
    assert set(doc["reskin"]["spans"]) == {s.name for s in pmap.spans}
    for row in doc["reskin"]["target"]:
        p = pmap.by_name(row["name"])
        assert row["expect_offset"] == p.off and row["expect_entries"] == p.entries
        assert tuple(row["expect_vram"]) == p.vram
        assert (row["hue_rotate"], row["saturation"], row["value"]) == (0.0, 1.0, 1.0)
        assert row.get("acknowledge_shared", False) is False
    b = RS.build(doc, "scaffold", blob=blob)
    assert b.patched == b.orig                               # identity: not one byte moved


def test_scaffold_pre_disables_every_row_a_refusal_would_stop():
    """The scaffold has to be buildable OUT OF THE BOX on a hazardous effect too -- which means the
    rows that would refuse arrive switched off, with the reason on the line."""
    text, _pm = RS.scaffold(999, blob=build_synth_multiwriter_container(), source="(fixture)")
    doc = _load_toml_text(text)
    for row in doc["reskin"]["target"]:
        assert row.get("enabled") is False, row["name"]
    assert "DUAL-DEPTH" in text and "MULTI-WRITER" in text

    # W7 L2/L6: the scaffold no longer seeds `acknowledge_texanim` -- a key that does nothing is a key
    # an author can only get wrong -- and an ARMED container gets the DECODED table instead of the
    # opaque "TEXANIM ARMED (116 bytes)" line that made the old refusal unanswerable.  Both texanim
    # shapes still scaffold to an INERT spec, which is the property this test actually owns.
    armed = build_synth_container(npart=1, texanim=116)        # armed, does NOT decode
    parsed = _armed_parsed_blob()                              # armed, DOES decode
    for blob, decodes in ((armed, False), (parsed, True)):
        text2, _pm2 = RS.scaffold(999, blob=blob, source="(fixture)")
        # A DECODED table emits no key at all; an UNDECODABLE one mentions `acknowledge_texanim`
        # as the pre-W7 requirement it degraded back to (V1 F1) -- comment prose, never a seeded key.
        assert ("acknowledge_texanim" not in text2) is decodes
        assert not any(l.strip().startswith("acknowledge_texanim") for l in text2.splitlines()), \
            "the scaffold never SEEDS the key as TOML, it only names the requirement in a comment"
        assert "THE TEXANIM TABLE" in text2
        assert ("REFUSED outright" not in text2) is decodes
        doc2 = _load_toml_text(text2)
        # ...and THE LIFT, read off the scaffold itself: a table that DECODES blocks no row FOR A
        # TEXANIM REASON (rows may still sit off for unrelated hazards, e.g. SHARED), so the
        # creature rows arrive switched ON.  On an UNDECODABLE table the pre-W7 posture seeds BOTH
        # scopes off (creature: refused outright; scenery: needs the old key), reason on the line.
        creature2 = [r for r in doc2["reskin"]["target"] if r["name"].startswith("creature.")]
        assert creature2 and all(r.get("enabled", True) is decodes for r in creature2)
        if not decodes:
            for r in doc2["reskin"]["target"]:
                assert r.get("enabled", True) is False, r["name"]
        b = RS.build(doc2, "scaffold", blob=blob)
        assert b.patched == b.orig


def test_scaffold_refuses_a_container_that_declares_no_palettes_at_all():
    """3 of the 372 corpus containers (ef252, ef253, ef302) declare an id-0 with an inline rect and
    ZERO CLUT words.  Emitting a target-less toml would hand back a file that cannot even load, so
    the scaffold says what is actually true: lever #1 has no surface on this effect."""
    blob = build_synth_creatureless_container(bindings=())
    # strip the id-0's CLUT words: nClut4 = nClut8 = 0
    head = EC.parse_header(blob).chunks[0].resources[0].offset
    stripped = bytearray(blob)
    struct.pack_into("<HH", stripped, head + 0x0C, 0, 0)
    stripped = bytes(stripped)
    assert RS.palette_map(stripped).palettes == []
    with pytest.raises(RS.ReskinError, match="NO CLUT palettes at all"):
        RS.scaffold(999, blob=stripped, source="(fixture)")


def test_scaffold_of_a_creature_less_container_emits_only_scenery():
    text, pmap = RS.scaffold(999, blob=build_synth_creatureless_container(), source="(fixture)")
    doc = _load_toml_text(text)
    assert doc["reskin"]["target"] and not any(r["name"].startswith("creature.")
                                               for r in doc["reskin"]["target"])
    assert "no id-4 creature package" in text


@needs_corpus
def test_palette_map_resolves_every_container_in_the_corpus_without_crashing():
    """THE W5 SWEEP.  W4's ``palette_map`` refused 348 of 372 containers outright (no creature) and
    refused ef381 with an opaque duplicate-name error that was really a multi-writer hazard.  All
    372 must now resolve, and the two hazard fixtures must be the ONLY ones flagged."""
    multi, dual, texanim, scenery_only, resolved = [], [], [], 0, 0
    for path in sorted(glob.glob(os.path.join(CORPUS, "ef*.bytes"))):
        with open(path, "rb") as fh:
            blob = fh.read()
        pmap = RS.palette_map(blob)                          # must not raise, for any of them
        resolved += 1
        name = os.path.basename(path)
        scenery_only += 1 if pmap.creature_error else 0
        for _vram, cell in pmap.hazards.items():
            if cell.multi_writer:
                multi.append(name)
            if cell.dual_depth:
                dual.append(name)
        if pmap.texanim and pmap.texanim.armed:
            texanim.append(name)
    assert resolved == 372
    assert scenery_only == 348
    assert sorted(set(multi)) == ["ef381.bytes", "ef447.bytes"]
    assert sorted(set(dual)) == ["ef447.bytes"]
    assert multi.count("ef381.bytes") == 19                  # 19 cells, the recon's own count
    assert sorted(texanim) == ["ef038.bytes", "ef177.bytes", "ef493.bytes", "ef494.bytes",
                               "ef495.bytes"]


@needs_corpus
def test_ef381_and_ef447_are_the_corpus_fixtures_the_detectors_were_written_against():
    """The measured shape, pinned: ef381 streams up to FIVE different palettes into one cell per
    phase; ef447 declares one cell at two bit depths."""
    with open(os.path.join(CORPUS, "ef381.bytes"), "rb") as fh:
        p381 = RS.palette_map(fh.read())
    mw = {k: c for k, c in p381.hazards.items() if c.multi_writer}
    assert len(mw) == 19
    assert max(len(set(c.offsets)) for c in mw.values()) == 5
    assert not any(c.dual_depth for c in p381.hazards.values())

    with open(os.path.join(CORPUS, "ef447.bytes"), "rb") as fh:
        p447 = RS.palette_map(fh.read())
    assert [k for k, c in p447.hazards.items() if c.dual_depth] == [(0, 242)]
    cell = p447.cells[(0, 242)]
    assert sorted(set(cell.depths)) == [16, 256]
    assert set(cell.names) == {"pal.s0.x0_y242.e16", "pal.s2.x0_y242.e256"}


@needs_corpus
@pytest.mark.parametrize("effect", [38, 177, 493, 494, 495])
def test_the_texanim_LIFT_holds_on_every_effect_in_the_corpus_class(effect):
    """W7's corpus-backed pin, INVERTED from W5's parametrised refusal (SYNTHESIS sec 5.3).  On each
    of the five real armed packages a creature recolour BUILDS, its table DECODES, and -- the half
    that is worth more than the lift -- the region comes back byte-identical with ``firstBlock`` and
    ``min(motionOffsets)`` unmoved.  ``w5_gates.G3'`` runs the same claim through the scaffold."""
    path = os.path.join(CORPUS, "ef%03d.bytes" % effect)
    with open(path, "rb") as fh:
        blob = fh.read()
    ta = RS.texanim_region(blob)
    assert ta.armed and ta.nbytes in (116, 364)
    res = TA.read(blob)
    assert res.parsed and res.table.count in (3, 9)
    part = res.table.parts[0]
    spec = _spec(blob, [{"name": "creature.part%d" % part, "hue_rotate": 30.0}], effect=effect)
    spec["reskin"]["acknowledge_texanim"] = True             # a NO-OP now, and it must still parse
    b = RS.build(spec, "t", blob=blob)
    assert len(b.enabled) == 1 and b.patched != blob
    assert b.patched[ta.lo:ta.hi] == blob[ta.lo:ta.hi], "THE REGION INVARIANT: region bytes moved"
    mp, mp2 = KC.creature_package(blob), KC.creature_package(b.patched)
    assert (mp2.first_block, min(mp2.motion_offsets)) == (mp.first_block, min(mp.motion_offsets))
    assert RS.texanim_region(b.patched) == ta
    assert any("DEPRECATED KEY `acknowledge_texanim`" in n for n in b.notes)


@needs_corpus
def test_ef211s_six_creature_rows_all_have_zero_headroom():
    """W5's second-proof target is the corpus's L5 counter-example: where ef227 peaks at
    28/28/24/22/28/27, ef211 peaks at 31 on every part."""
    with open(os.path.join(CORPUS, "ef211.bytes"), "rb") as fh:
        blob = fh.read()
    pmap = RS.palette_map(blob)
    peaks = [RS.palette_peak(blob, pmap.by_name("creature.part%d" % i)) for i in range(6)]
    assert peaks == [31] * 6
    spec = _spec(blob, [{"name": "creature.part0", "hue_to": 200.0, "value": 1.02}], effect=211)
    with pytest.raises(RS.ReskinError, match="ZERO HEADROOM"):
        RS.build(spec, "t", blob=blob)


@needs_corpus
def test_scaffold_round_trips_on_the_whole_corpus():
    """The strongest single statement W5 can make offline: for EVERY container in the corpus the
    scaffold emits a toml that PARSES, BUILDS and changes ZERO bytes -- creature or not, hazardous
    or not, texanim-armed or not.  The only exceptions are the three containers that declare no CLUT
    palette at all, and those REFUSE with that stated rather than emitting an unloadable file."""
    ok, creature, refused = 0, 0, []
    for path in sorted(glob.glob(os.path.join(CORPUS, "ef*.bytes"))):
        with open(path, "rb") as fh:
            blob = fh.read()
        effect = int(os.path.basename(path)[2:5])
        pmap = RS.palette_map(blob)
        creature += 0 if pmap.creature_error else 1
        try:
            text, _pm = RS.scaffold(effect, blob=blob, source=path)
        except RS.ReskinError as exc:
            assert "NO CLUT palettes at all" in str(exc), path
            refused.append(os.path.basename(path))
            continue
        b = RS.build(_load_toml_text(text), "scaffold", blob=blob)
        assert b.patched == b.orig, path
        ok += 1
    assert creature == 24
    assert refused == ["ef252.bytes", "ef253.bytes", "ef302.bytes"]
    assert ok == 369
