r"""Tests for the summon RESKIN lane and for BOTH container-edit CLI verbs.

Two halves, deliberately unequal in size:

* **the reskin lane's own laws** (sections 0-4), run on containers THIS FILE WROTE -- no install,
  no extracted corpus, no game bytes.  Every refusal TIER W rung 4/5 established has a test here,
  because a refusal that survived the promotion untested is a refusal nobody would notice losing.
* **the CLI contract** (section 5) for ``summon-reskin`` AND ``summon-rescore``: that the two verbs
  are registered with the whole sub-verb ladder, that the ROOT parser's ``--game``/``--mod-folder``
  SURVIVE into them, and that the 0 / 1 / 2 exit codes mean what the lane says they mean.

    py -m pytest tests/test_summon_reskin.py -q

THE SYNTHETIC CONTAINER (section 0) is the same fixture the study built, ported: ONE chunk carrying
an id-0 scenery resource (one inline CLUT rect over VRAM rows 244-245, a 16-entry palette at
``(0,244)`` and a 256-entry one at ``(0,245)``), an id-3 filler standing in for the effect program
image, an id-4/id-5 creature package laid out exactly as
:func:`ff9mapkit.summons.texture.texture_check` requires, and an id-6 payload of ``so``+GEOM pairs so
the DERIVED attribution has real bindings to read.  A two-chunk variant carries a multi-writer cell
and a dual-depth cell (synthetic stand-ins for ef381 and ef447) and a texanim-armed variant stands in
for the ef038/ef177/ef493-495 class, so every W5 refusal runs with nothing installed.

PROVENANCE: every CLUT word in this file is COMPUTED by a small arithmetic generator -- never a byte
run copied from the corpus or from an install.  The kit's provenance rule applies to a test file
exactly as it does to the module it tests.  The one install-gated test (section 6) compares HASHES of
bytes it rebuilds locally and commits no data.
"""
from __future__ import annotations

import hashlib
import json
import os
import struct
import subprocess
import sys
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

SECTOR = KC.SECTOR

#: the study dir holding the three cast-proven specs.  Present in a checkout, absent in a wheel --
#: section 6 skips rather than failing, exactly as the M1b acceptance gate does.
_STUDY = Path(__file__).resolve().parents[2] / "studies" / "custom-summons" / "tier-w"
#: the read-only stock dumps.  Same ``needs_corpus`` house pattern the repaint and texanim test files
#: use: the corpus-backed pins RUN where the lane is extracted and SKIP where it is not.
CORPUS = Path(r"C:/gd/SCRATCH/summon-format")


def _has_install() -> bool:
    try:
        return bool(config.find_game_path(None))
    except Exception:
        return False


needs_install = pytest.mark.skipif(not _has_install(), reason="no FF9 install resolvable")
needs_corpus = pytest.mark.skipif(
    not (CORPUS / "ef038.bytes").is_file(),
    reason="needs-corpus: the extracted ef###.bytes corpus is not on this machine")
needs_study_specs = pytest.mark.skipif(
    not (_STUDY / "bahamut_reskin.toml").is_file(),
    reason="the tier-w study specs are not in this tree (installed wheel / trimmed checkout)")


# ============================================================ (0) the synthetic container
#: the two VRAM cells the fixture declares.  Both the names and the SHARED flag are DERIVED from the
#: container's own ``so`` bindings, so the fixture writes real records and the tests read the
#: derivation's answer rather than a hand table.
_CELL_4BPP = 0x3D00            # VRAM (0, 244), 16-entry 4bpp  -> ONE binder  => derived PRIVATE
_CELL_8BPP = 0x3D40            # VRAM (0, 245), 256-entry 8bpp -> TWO binders => derived SHARED
PAL_4BPP = "pal.s0.x0_y244.e16"
PAL_8BPP = "pal.s0.x0_y245.e256"


def _pad_sector(payload: bytes):
    n = max(1, (len(payload) + SECTOR - 1) // SECTOR)
    return payload.ljust(n * SECTOR, b"\x00"), n


def synth_clut16(zero_first: bool = True):
    """16 COMPUTED BGR555 words.  Channels are taken mod 25 so this palette's peak lands BELOW the
    5-bit ceiling and it can serve as the fixture's headroom-POSITIVE row -- the counterpart to the
    256-entry rows, which sweep the whole 0..31 range and peak at 31."""
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

    ``synth_clut256`` sweeps the whole hue wheel, so its saturation-weighted mean comes out at the
    same angle for every seed -- useless for proving that ``hue_to`` lands two writers with DIFFERENT
    stock means on one absolute hue.  This one's mean is nowhere near it.
    """
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
    16-entry CLUT at row 244 x=0 and a 256-entry CLUT at row 245 x=0."""
    buf = bytearray(0x424)
    struct.pack_into("<iii", buf, 0x00, 0x14, 0x1C, 1)       # pageBlockRel, inlineRel, nInline=1
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
    """One id-4 payload: a header (``texOffset == 0x180 + 4*motionCount``) + ``npart`` 8bpp pages +
    ``npart`` 256-entry CLUT rows at consecutive strip rows from ``KT.CLUT_STRIP_Y``.

    ``texanim > 0`` ARMS the texanim region: one motion clip whose ``motionOffsets[0]`` sits that many
    bytes past ``firstBlock`` -- the shape the five corpus effects have (ef038 = 116 B, ef177/493/494
    /495 = 364 B each) and exactly what :func:`ff9mapkit.summons.reskin.texanim_region` measures.
    """
    nmotion = 1 if texanim else 0
    tex_off = 0x180 + 4 * nmotion
    tex_bytes = npart * KT.PAGE_BYTES
    clut_rows = npart
    clut_bytes = clut_rows * 0x200
    header = bytearray(tex_off)
    struct.pack_into("<hhhH", header, 0, tex_off, nmotion, npart, clut_rows)
    struct.pack_into("<II", header, 8, tex_bytes, clut_bytes)
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


def _so_geom(tpage: int, clut: int, second=(0, 0)) -> bytes:
    """One 16-byte ``so`` binding record + the smallest GEOM block :func:`KC.scan_geom` accepts.

    Degenerate on purpose -- 1 bone, 1 mesh, every primitive bucket empty -- but it satisfies the
    scanner's whole acceptance law: the ``pBoneTable == 0x14`` needle, ``pMeshTable == 0x18 +
    (boneCount-1)*4``, and all four chain identities (each pool starts at the 4-byte-aligned end of
    the previous, which for empty pools means they coincide).

    ``second`` is the record's SECOND array pair at ``+arrayB`` (W6b-3 iii). It DEFAULTS to ``(0, 0)``
    -- the value this fixture always wrote -- so every existing decode is byte-identical, and it is a
    parameter only so a test can build a MOVER without a second fixture.
    """
    so = (struct.pack("<HHHH", 0x6F73, 1, 0x10, 0x0C) + struct.pack("<HH", tpage, clut)
          + struct.pack("<HH", second[0], second[1]))
    g = bytearray(0x48)
    g[0:4] = bytes([0x00, 0x00, 1, 1])                        # flags, zero, boneCount, meshCount
    struct.pack_into("<II", g, 0x04, 0, 0)
    struct.pack_into("<I", g, 0x0C, 0x14)                     # pBoneTable -- the needle
    struct.pack_into("<I", g, 0x10, 0x18)                     # pMeshTable == 0x18+(1-1)*4
    struct.pack_into("<I", g, 0x14, 0)                        # listHead
    struct.pack_into("<IIIII", g, 0x18 + 0x14, 0x40, 0x44, 0x44, 0x44, 0x44)
    struct.pack_into("<H", g, 0x40, 0)                        # vertsPerBone[0] = 0 vertices
    return so + bytes(g)


def _so_geom_multi(parts, second=None) -> bytes:
    """A **MULTI-PART** ``so`` record (``P = len(parts)``) plus the same degenerate GEOM block.

    ★ SYNTHESISED, NEVER COPIED.  The header is
    ``struct.pack("<HHHH", 0x6F73, 1, 8 + 8P, 8 + 4P)`` and every pair is invented, so nothing in this
    file is a run of bytes lifted out of a real ``ef*.bytes`` -- the provenance rule the whole summon
    lane is held to.  ``P == 0`` yields the 8-byte record, which is a RECORD and not an absence.

    ``second`` is the SECOND array (W6b-3 iii), one ``(u16, u16)`` per part; ``None`` writes the
    all-zero array this fixture always wrote, so every existing decode is byte-identical.
    """
    P = len(parts)
    sec = list(second if second is not None else [(0, 0)] * P)
    assert len(sec) == P, "the second array is one pair per part -- that is what `arrayB` asserts"
    so = struct.pack("<HHHH", 0x6F73, 1 if P else 0, 8 + 8 * P, 8 + 4 * P)
    so += b"".join(struct.pack("<HH", tp, cw) for tp, cw in parts)
    so += b"".join(struct.pack("<HH", a, b) for a, b in sec)  # the SECOND array at +arrayB
    assert len(so) == 8 + 8 * P
    return so + _so_geom(0, 0)[0x10:]                         # the GEOM block, one derivation


def _build_models_id6(bindings) -> bytes:
    """``(tpage, clut)`` builds an INCUMBENT (``P == 1``) record; a SEQUENCE of such pairs builds a
    MULTI-PART one, and the empty sequence builds the ``P == 0`` record."""
    out = []
    for b in bindings:
        if isinstance(b, (list, tuple)) and (not b or isinstance(b[0], (list, tuple))):
            out.append(_so_geom_multi(tuple(b)))
        else:
            out.append(_so_geom(*b))
    return b"".join(out)


#: TWO models on the 8bpp cell (so it derives SHARED) and ONE on the 4bpp cell (so it derives
#: PRIVATE), at COMPLETE ``so`` coverage -- 3 of 3 GEOM blocks bound.
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
    """A whole ``ef###``-shaped container.  No id-2 camera archive: the all-zero sequence stream
    decodes to a single immediate END op, so ``extract_shots`` resolves zero shots -- a legitimate
    (if unusually quiet) container rather than an error."""
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
    """The 348-of-372 shape: scenery palettes, no id-4/id-5 creature package at all."""
    id0 = _build_scenery_id0(synth_clut16(), synth_clut256(seed=3))
    resources = [(0, id0), (3, bytes([0x55]) * SECTOR)]
    if bindings:
        resources.append((6, _build_models_id6(bindings)))
    return _assemble([(0, resources)])


def _build_second_chunk_id0(pal256_a, pal256_b) -> bytes:
    """A SECOND chunk's id-0 declaring TWO 256-entry palettes over the rows chunk 0 used: ``(0,245)``
    again (a MULTI-WRITER cell) and ``(0,244)`` at 256 entries where chunk 0 declared 16 (a DUAL-DEPTH
    cell) -- ef381's and ef447's shapes in miniature."""
    buf = bytearray(0x424)
    struct.pack_into("<iii", buf, 0x00, 0x14, 0x1C, 1)
    struct.pack_into("<HH", buf, 0x0C, 0, 2)                 # nClut4=0, nClut8=2
    struct.pack_into("<HH", buf, 0x10, _CELL_8BPP, _CELL_4BPP)
    struct.pack_into("<ii", buf, 0x14, 0x424, 0)
    struct.pack_into("<HHHH", buf, 0x1C, 0, 244, 256, 2)
    buf[0x24:0x24 + 512] = _words(pal256_a)
    buf[0x224:0x224 + 512] = _words(pal256_b)
    return bytes(buf)


def build_synth_multiwriter_container(chunk_indices=(0, 1)) -> bytes:
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


def _write_spec(tmp_path, blob: bytes, targets, effect: int = 999, name="x_reskin.toml") -> Path:
    """A spec ON DISC, so the CLI's own load/resolve path is what runs (never a dict shortcut)."""
    lines = ["[reskin]", "effect = %d" % effect, 'label = "synthtest"',
             'expect_sha256 = "%s"' % hashlib.sha256(blob).hexdigest()]
    for t in targets:
        lines.append("[[reskin.target]]")
        for k, v in t.items():
            lines.append("%s = %s" % (k, json.dumps(v)))
    p = tmp_path / name
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def test_synth_container_is_well_formed_and_resolves_the_expected_palettes():
    """Sanity-checks the FIXTURE, so a later failure cannot be a synthetic-container bug wearing a
    reskin bug's clothes."""
    blob = build_synth_container(npart=2)
    c = KC.parse_header(blob, strict=True)
    assert c.cursor_end == len(blob)
    pmap = RS.palette_map(blob)
    names = {p.name for p in pmap.palettes}
    assert {PAL_4BPP, PAL_8BPP, "creature.part0", "creature.part1"} <= names
    assert pmap.by_name(PAL_4BPP).entries == 16 and pmap.by_name(PAL_4BPP).bpp == 4
    assert pmap.by_name(PAL_8BPP).entries == 256 and pmap.by_name(PAL_8BPP).bpp == 8
    assert pmap.envelope == sum(s.size for s in pmap.spans)


def test_attribution_is_derived_from_the_containers_own_so_records():
    """The SHARED flag is a DERIVATION, not a table: the 8bpp cell has two ``so`` binders in the
    fixture's own id-6 payload and the 4bpp cell has one, and that is the whole reason one comes back
    shared and the other private."""
    blob = build_synth_container(npart=1)
    pmap = RS.palette_map(blob)
    assert pmap.by_name(PAL_8BPP).shared
    assert not pmap.by_name(PAL_4BPP).shared
    bare = RS.palette_map(build_synth_container(npart=1, bindings=()))
    assert bare.by_name(PAL_8BPP).shared and bare.by_name(PAL_4BPP).shared, \
        "no so coverage is NO EVIDENCE -- every scenery palette must come back shared-unknown"


# ============================================================ (1) build()-level refusals
def test_build_refuses_a_shared_clut_named_without_acknowledgment():
    blob = build_synth_container(npart=1)
    with pytest.raises(RS.ReskinError, match="SHARED palette"):
        RS.build(_spec(blob, [{"name": PAL_8BPP, "hue_rotate": 30.0}]), "t", blob=blob)


def test_build_accepts_a_shared_clut_named_with_acknowledgment():
    blob = build_synth_container(npart=1)
    b = RS.build(_spec(blob, [{"name": PAL_8BPP, "hue_rotate": 30.0,
                               "acknowledge_shared": True}]), "t", blob=blob)
    assert b.targets[0].enabled and b.targets[0].result is not None
    assert len(b.patched) == len(b.orig)


def test_build_refuses_an_unknown_target_name():
    blob = build_synth_container(npart=1)
    with pytest.raises(RS.ReskinError, match="no palette named"):
        RS.build(_spec(blob, [{"name": "creature.part99", "hue_rotate": 30.0}]), "t", blob=blob)


def test_build_refuses_a_drifted_stock_hash():
    blob = build_synth_container(npart=1)
    spec = _spec(blob, [{"name": "creature.part0", "hue_rotate": 30.0}])
    spec["reskin"]["expect_sha256"] = "0" * 64
    with pytest.raises(RS.R.StockDriftError):
        RS.build(spec, "t", blob=blob)


def test_build_refuses_a_saturation_scale_past_the_4x_clip_ceiling():
    blob = build_synth_container(npart=1)
    with pytest.raises(RS.ReskinError, match="above 4x"):
        RS.build(_spec(blob, [{"name": "creature.part0", "saturation": 4.01}]), "t", blob=blob)


def test_build_refuses_a_disagreeing_per_target_offset_guard():
    blob = build_synth_container(npart=1)
    with pytest.raises(RS.ReskinError, match="the derivation says"):
        RS.build(_spec(blob, [{"name": "creature.part0", "expect_offset": 0x1234}]), "t", blob=blob)


def test_build_refuses_a_disagreeing_vram_guard():
    blob = build_synth_container(npart=1)
    with pytest.raises(RS.ReskinError, match="the header declares"):
        RS.build(_spec(blob, [{"name": "creature.part0", "expect_vram": [1, 2]}]), "t", blob=blob)


def test_build_refuses_a_disagreeing_span_guard():
    blob = build_synth_container(npart=1)
    with pytest.raises(RS.ReskinError, match="refusing to splice"):
        RS.build(_spec(blob, [{"name": "creature.part0"}],
                       spans={"creature_clut_strip": {"offset": 0x1234, "length": 999}}),
                 "t", blob=blob)


def test_build_refuses_an_effect_with_no_drift_guard_at_all():
    """Merely PRINTING "unguarded" would let a Steam/Moguri patch move a span under the edit with
    nothing noticing."""
    blob = build_synth_container(npart=1)
    spec = {"reskin": {"effect": 999, "target": [{"name": "creature.part0"}]}}
    with pytest.raises(RS.ReskinError, match="NO drift guard"):
        RS.build(spec, "t", blob=blob)
    spec["reskin"]["allow_unguarded"] = True
    assert RS.build(spec, "t", blob=blob).sha_in


def test_two_target_rows_naming_the_same_derived_palette_refuse():
    """The alias map makes two spellings of one palette possible, so the duplicate check runs on the
    DERIVED name, not on the spelling."""
    blob = build_synth_container(npart=1)
    rows = [{"name": PAL_4BPP, "hue_rotate": 10.0, "acknowledge_shared": True},
            {"name": "spare.c0_x0_y244", "hue_rotate": 20.0, "acknowledge_shared": True}]
    with pytest.raises(RS.ReskinError, match="both resolve to the derived palette"):
        RS.build(_spec(blob, rows), "t", blob=blob)


def test_describe_names_the_drift_guard_that_actually_applied():
    """A report that says "unguarded" about a guarded build is a lie in the one direction that gets a
    guard deleted -- so the guard string is set where ``sha_in`` is computed, not inferred later."""
    blob = build_synth_container(npart=1)
    sha = hashlib.sha256(blob).hexdigest()
    b = RS.build({"reskin": {"effect": 999, "expect_sha256": sha,
                             "target": [{"name": "creature.part0"}]}}, "t", blob=blob)
    assert b.guard == "the spec's own expect_sha256 -- MATCHES"
    line = next(l for l in RS.describe(b) if "drift guard" in l)
    assert "expect_sha256" in line and "unguarded" not in line.lower()
    b2 = RS.build({"reskin": {"effect": 999, "allow_unguarded": True,
                              "target": [{"name": "creature.part0"}]}}, "t", blob=blob)
    assert "UNGUARDED" in b2.guard
    assert "UNGUARDED" in next(l for l in RS.describe(b2) if "drift guard" in l)


# ---- W6q-0: THE UNKNOWN-KEY GATES, the asymmetry closed --------------------------------------
# Before this rung the fail-closed property existed on ``[[reskin.texel]]`` ONLY.  This table and the
# top-level ``[reskin]`` read every key through ``d.get``, so a mistyped guard was silently dropped
# and a mistyped acknowledgement armed nothing while reading like consent.  Three tests: it fires on
# each table, and -- the half that usually goes missing -- every spec the tree already ships still
# loads, ENUMERATED BY GLOB rather than by hand.
def test_a_target_row_refuses_an_unknown_key():
    blob = build_synth_container(npart=1)
    with pytest.raises(RS.ReskinError) as e:
        RS.build(_spec(blob, [{"name": "creature.part0", "acknowledge_shard": True}]), "t",
                 blob=blob)
    msg = str(e.value)
    assert "[[reskin.target]] #0" in msg and "'acknowledge_shard'" in msg
    assert "fail CLOSED" in msg and "Known keys:" in msg
    # THE POINT, stated as an assertion: the dropped guard, not the dropped acknowledgement, is what
    # this exists for -- a mistyped `expect_offset` silently un-guards the derivation.
    with pytest.raises(RS.ReskinError, match="expct_offset"):
        RS.build(_spec(blob, [{"name": "creature.part0", "expct_offset": 0x1234}]), "t", blob=blob)


def test_the_reskin_table_refuses_an_unknown_key(tmp_path):
    """Both loaders, one key set: a key lawful on the path that happened to open the file and
    unknown on the other would be a refusal that depends on the caller."""
    p = tmp_path / "x_reskin.toml"
    p.write_text('[reskin]\neffect = 999\nmint_clut = true\n\n[[reskin.target]]\n'
                 'name = "creature.part0"\n', encoding="utf-8")
    with pytest.raises(RS.ReskinError) as e:
        RS.load_spec(p)
    assert "[reskin]" in str(e.value) and "'mint_clut'" in str(e.value)
    with pytest.raises(RP.RepaintError, match="mint_clut"):
        RP.load_spec(p)                      # the texel loader, same set, its own error class
    assert RS._RESKIN_KEYS is not None and "texel" in RS._RESKIN_KEYS


def test_every_shipped_spec_still_loads_under_the_new_key_gates():
    """THE REGRESSION NET, ENUMERATED FROM THE TREE.  W6q-0 is the one rung of this feature that can
    refuse a spec that builds today, so the population it must not break is globbed, never listed:
    every example, every study spec, and every scaffold BOTH lanes emit (including the deprecated
    ``acknowledge_texanim``, which is why it is in ``_TARGET_KEYS``)."""
    import tomllib
    root = Path(__file__).resolve().parents[2]
    seen = 0
    for p in sorted(root.rglob("*.toml")):
        if ".git" in p.parts or "site-packages" in p.parts:
            continue
        try:
            doc = tomllib.load(open(p, "rb"))
        except Exception:
            continue
        r = doc.get("reskin")
        if not isinstance(r, dict):
            continue
        seen += 1
        assert not (set(r) - RS._RESKIN_KEYS), "%s: unknown [reskin] key(s)" % p
        for i, row in enumerate(r.get("target") or []):
            assert not (set(row) - RS._TARGET_KEYS), "%s [[reskin.target]] #%d" % (p, i)
        for i, row in enumerate(r.get("texel") or []):
            assert not (set(row) - RP._TEXEL_KEYS), "%s [[reskin.texel]] #%d" % (p, i)
    assert seen >= 1, "the enumeration found no [reskin] spec at all -- a vacuous net"
    # the emitted SCAFFOLDS are the other half of the population, and they are generated here rather
    # than trusted: a scaffold that emits a key its own loader refuses is the worst possible shape.
    blob = build_synth_container(npart=1)
    text, _pm = RS.scaffold(999, blob=blob)
    doc = tomllib.loads(text)
    assert not (set(doc["reskin"]) - RS._RESKIN_KEYS)
    for row in doc["reskin"]["target"]:
        assert not (set(row) - RS._TARGET_KEYS)


def test_the_deprecated_texanim_acknowledgement_is_still_a_known_key():
    """``acknowledge_texanim`` is a parsed no-op kept alive for one release.  Omitting it from the
    key set would turn "your spec still builds" into "your spec refuses" for exactly the population
    W6q-0 exists to protect."""
    assert "acknowledge_texanim" in RS._TARGET_KEYS and "acknowledge_texanim" in RS._RESKIN_KEYS
    blob = build_synth_container(npart=1)
    spec = _spec(blob, [{"name": "creature.part0", "acknowledge_texanim": False}])
    spec["reskin"]["acknowledge_texanim"] = False
    assert RS.build(spec, "t", blob=blob).sha_in


# ============================================================ (2) the W5 refusal matrix
def test_the_multiwriter_and_dual_depth_detectors_fire_on_a_hand_built_container():
    blob = build_synth_multiwriter_container()
    haz = RS.palette_map(blob).hazards
    assert set(haz) == {(0, 244), (0, 245)}
    assert haz[(0, 245)].multi_writer and not haz[(0, 245)].dual_depth
    assert haz[(0, 244)].multi_writer and haz[(0, 244)].dual_depth
    assert len(set(haz[(0, 245)].offsets)) == 2
    assert RS.palette_map(build_synth_container(npart=1)).hazards == {}


def test_build_refuses_a_dual_depth_cell_outright():
    """The 16-entry and 256-entry readings of one cell are two pictures over the same bytes.  NO
    acknowledgement lifts this -- there is no evidence either way."""
    blob = build_synth_multiwriter_container()
    with pytest.raises(RS.ReskinError, match="DUAL-DEPTH"):
        RS.build(_spec(blob, [{"name": PAL_4BPP, "hue_to": 200.0,
                               "acknowledge_shared": True}]), "t", blob=blob)


def test_build_refuses_a_multiwriter_cell_when_only_some_writers_are_named():
    blob = build_synth_multiwriter_container()
    with pytest.raises(RS.ReskinError, match="MULTI-WRITER"):
        RS.build(_spec(blob, [{"name": PAL_8BPP, "hue_to": 200.0,
                               "acknowledge_shared": True}]), "t", blob=blob)


def test_build_refuses_a_multiwriter_co_transform_authored_as_a_hue_rotate_delta():
    """The subtle half: naming every writer is not enough.  Each writer has its OWN mean hue, so one
    shared ``hue_rotate`` DELTA lands them on different hues -- the exact flicker the gate exists for.
    Only the absolute ``hue_to`` form is coherent."""
    blob = build_synth_multiwriter_container()
    rows = [{"name": n, "hue_rotate": 40.0, "acknowledge_shared": True}
            for n in ("pal.s0.x0_y245.e256", "pal.s1.x0_y245.e256")]
    with pytest.raises(RS.ReskinError, match="ABSOLUTE `hue_to`"):
        RS.build(_spec(blob, rows), "t", blob=blob)


def test_build_accepts_a_multiwriter_co_transform_authored_with_hue_to():
    blob = build_synth_multiwriter_container()
    names = ("pal.s0.x0_y245.e256", "pal.s1.x0_y245.e256")
    b = RS.build(_spec(blob, [{"name": n, "hue_to": 200.0, "acknowledge_shared": True}
                              for n in names]), "t", blob=blob)
    assert len(b.enabled) == 2
    means = [RS.palette_mean_hue(blob, t.pal) for t in b.enabled]
    assert abs(means[0] - means[1]) > 1e-6, "the fixture's two writers must differ to prove this"
    for t in b.enabled:
        assert abs(((t.result.hue_after - 200.0 + 180.0) % 360.0) - 180.0) < 12.0


def test_hue_to_is_hue_rotate_minus_the_measured_mean_and_they_cannot_both_be_declared():
    blob = build_synth_container(npart=1)
    mean = RS.palette_mean_hue(blob, RS.palette_map(blob).by_name("creature.part0"))
    b = RS.build(_spec(blob, [{"name": "creature.part0", "hue_to": 210.0}]), "t", blob=blob)
    t = b.targets[0].t
    assert t.hue_to == 210.0
    assert abs(((t.hue - (210.0 - mean) + 180.0) % 360.0) - 180.0) < 1e-9
    with pytest.raises(RS.ReskinError, match="BOTH `hue_to` and `hue_rotate`"):
        RS.build(_spec(blob, [{"name": "creature.part0", "hue_to": 1.0, "hue_rotate": 2.0}]),
                 "t", blob=blob)


def test_a_row_level_hue_to_beats_an_inherited_default_hue_rotate():
    """``[reskin.defaults] hue_rotate = 0.0`` is what every scaffolded spec writes, so an absolute row
    has to WIN over it rather than collide with it."""
    blob = build_synth_container(npart=1)
    spec = _spec(blob, [{"name": "creature.part0", "hue_to": 90.0}])
    spec["reskin"]["defaults"] = {"hue_rotate": 0.0, "saturation": 1.0, "value": 1.0}
    b = RS.build(spec, "t", blob=blob)
    assert b.targets[0].t.hue_to == 90.0 and b.targets[0].t.hue != 0.0


def test_texanim_region_is_measured_from_the_id4_header():
    assert not RS.texanim_region(build_synth_container(npart=1)).armed
    ta = RS.texanim_region(build_synth_container(npart=1, texanim=364))
    assert ta.present and ta.armed and ta.nbytes == 364 and ta.hi - ta.lo == 364
    none = RS.texanim_region(build_synth_creatureless_container())
    assert not none.present and not none.armed


def _armed_parsed_blob(npart: int = 2) -> bytes:
    """The synthetic container with a VALID texanim table spliced in -- W7's lift fixture.

    ``build_synth_container(texanim=N)`` arms a region of filler, which the reader (correctly) refuses:
    on THAT container the lift is not available and the gate falls back to the pre-W7 refusal.  Proving
    the lift needs a region that actually DECODES, so the generator lives with the reader's own tests
    and is imported here rather than copied.  The import is deferred because the texanim test module
    imports THIS one for its container fixture, and a module-level import would close the loop.
    """
    from tests.test_summon_texanim import armed_blob, synth_116
    return armed_blob(synth_116(), npart=npart)


def test_a_creature_recolour_builds_under_an_armed_texanim():
    """W7 L1, THE LIFT -- inverted from the pre-W7 pin that refused this outright.

    The table blits 8-bit palette INDICES inside one creature part's own page: it binds no CLUT word
    and writes no CLUT contents, so a recolour survives the cast whether or not the animation runs.
    The refusal is replaced by an OBLIGATION, and the obligation is checked here as bytes: the region
    itself must come out of the build byte-identical (THE REGION INVARIANT, W7 R1).
    """
    blob = _armed_parsed_blob()
    ta = RS.texanim_region(blob)
    assert ta.armed and TA.read(blob).parsed, "the fixture must be armed AND decodable"
    b = RS.build(_spec(blob, [{"name": "creature.part0", "hue_rotate": 30.0}]), "t", blob=blob)
    assert len(b.enabled) == 1 and b.patched != b.orig, "the recolour actually spliced"
    assert b.patched[ta.lo:ta.hi] == b.orig[ta.lo:ta.hi], "THE REGION INVARIANT: region bytes moved"
    assert "byte-identical" in b.region_invariant
    assert any("DECODED" in n for n in b.notes), "the lift must DISCLOSE the decode, not be silent"


def test_an_armed_texanim_whose_table_does_NOT_decode_still_refuses_a_creature_recolour():
    """THE FALLBACK CONTRACT, and the reason the lift is safe: it is conditional on a successful
    PARSE, never on the absence of an exception.  An armed region the reader cannot decode is the
    pre-W7 state, so the pre-W7 refusal is what an author gets -- with no key able to lift it."""
    blob = build_synth_container(npart=1, texanim=116)         # armed, contents are filler
    assert RS.texanim_region(blob).armed and TA.read(blob).unparseable
    spec = _spec(blob, [{"name": "creature.part0", "hue_rotate": 30.0}])
    with pytest.raises(RS.ReskinError, match="TEXANIM ARMED"):
        RS.build(spec, "t", blob=blob)
    spec["reskin"]["acknowledge_texanim"] = True
    with pytest.raises(RS.ReskinError, match="recolours the CREATURE"):
        RS.build(spec, "t", blob=blob)


def test_scenery_builds_under_an_armed_PARSED_texanim_with_no_key_and_the_old_key_is_a_deprecated_noop():
    """W7 L2, inverted -- FOR A TABLE THAT DECODES.  The scenery hedge ("orthogonality assumed, not
    proven") is a MEASUREMENT now: every clip names a CREATURE part and every rect is local to that
    part's own page, so the table cannot reach a scenery page at all.  ``acknowledge_texanim``
    survives as a parseable NO-OP on this path -- specs written against the old gate keep building --
    and says so in the report."""
    rows = [{"name": PAL_4BPP, "hue_rotate": 30.0}]
    blob = _armed_parsed_blob()
    assert RS.texanim_region(blob).armed and not TA.read(blob).unparseable
    assert len(RS.build(_spec(blob, rows), "t", blob=blob).enabled) == 1, \
        "scenery needs no key when the table decodes -- it is out of the table's measured reach"
    spec = _spec(blob, rows)
    spec["reskin"]["acknowledge_texanim"] = True
    b = RS.build(spec, "t", blob=blob)
    assert len(b.enabled) == 1
    assert any("DEPRECATED KEY `acknowledge_texanim`" in n for n in b.notes)
    assert any("DEPRECATED" in l for l in RS.describe(b))


def test_scenery_under_an_armed_UNPARSEABLE_texanim_degrades_to_the_preW7_posture():
    """THE FALLBACK CONTRACT, scenery half (V1 F1).  On an armed region the reader cannot decode, the
    measurement that deprecated ``acknowledge_texanim`` never ran -- so the pre-W7 posture stands:
    scenery REFUSES without the key, builds WITH it, and the key is doing its original job (the note
    says UNDECODABLE, not DEPRECATED)."""
    rows = [{"name": PAL_4BPP, "hue_rotate": 30.0}]
    blob = build_synth_container(npart=1, texanim=116)         # armed, contents are filler
    assert RS.texanim_region(blob).armed and TA.read(blob).unparseable
    with pytest.raises(RS.ReskinError, match="does not DECODE"):
        RS.build(_spec(blob, rows), "t", blob=blob)
    spec = _spec(blob, rows)
    spec["reskin"]["acknowledge_texanim"] = True
    b = RS.build(spec, "t", blob=blob)
    assert len(b.enabled) == 1
    assert any("UNDECODABLE" in n and "ORIGINAL, pre-W7 meaning" in n for n in b.notes), \
        "the degraded path must DISCLOSE, and must not call the key deprecated"
    assert not any("DEPRECATED KEY" in n for n in b.notes)


def test_the_region_invariant_names_firstBlock_when_firstBlock_is_what_moved():
    """V1 F6: the header-field comparisons fire BEFORE the derived-span comparison, so a moved
    ``firstBlock`` is reported as such, not as a generic MOVED-or-RESIZED."""
    from ff9mapkit.summons import container as EC
    blob = _armed_parsed_blob()
    mp = EC.creature_package(blob)
    patched = bytearray(blob)
    off = mp.header_offset + 0x14                          # u32 firstBlock, header +0x14
    import struct
    struct.pack_into("<I", patched, off, mp.first_block + 4)
    with pytest.raises(RS.ReskinError, match=r"firstBlock moved 0x"):
        RS.assert_region_invariant(blob, bytes(patched), "the F6 probe")


def test_the_scaffold_stops_emitting_acknowledge_texanim_and_prints_the_decoded_table():
    """W7 L2/L6.  A scaffold must not seed a key that does nothing, and an author reading it should
    see the CLIP TABLE -- not "TEXANIM ARMED (116 bytes)", which is exactly the opaque line that made
    the old refusal unanswerable."""
    blob = _armed_parsed_blob()
    text, _pmap = RS.scaffold(999, blob=blob, source="(synthetic)")
    assert "acknowledge_texanim" not in text
    assert "THE TEXANIM TABLE" in text and "THE PROTECTED RECT SET" in text
    assert "clip 0 " in text and "window" in text
    assert "REFUSED outright" not in text, "a decodable table blocks nothing"
    unread, _p2 = RS.scaffold(999, blob=build_synth_container(npart=1, texanim=116),
                              source="(synthetic)")
    # V1 F1: an UNDECODABLE table degrades scenery to the pre-W7 posture, so the scaffold NAMES the
    # key as the requirement -- in comment prose only, never seeded as TOML.
    assert "acknowledge_texanim" in unread
    assert not any(l.strip().startswith("acknowledge_texanim") for l in unread.splitlines())
    assert "does NOT decode" in unread and "REFUSED outright" in unread


@needs_corpus
def test_the_region_invariant_survives_a_real_recolour_of_ef038():
    """W7 G4, on REAL bytes -- ef038 is Shiva, the only effect in the corpus that arms op 12 and so
    the maximal-risk member of the class.  A creature recolour BUILDS, and ``firstBlock``,
    ``min(motionOffsets)`` and all 116 region bytes come out untouched.  This is the pin on the rung's
    one new hard rule, and it is worth more than the lift it accompanies."""
    blob = (CORPUS / "ef038.bytes").read_bytes()
    ta = RS.texanim_region(blob)
    assert ta.armed and ta.nbytes == 116 and TA.read(blob).parsed
    mp = KC.creature_package(blob)
    b = RS.build(_spec(blob, [{"name": "creature.part1", "hue_rotate": 120.0}], effect=38),
                 "t", blob=blob)
    assert len(b.enabled) == 1 and b.patched != b.orig
    assert b.patched[ta.lo:ta.hi] == blob[ta.lo:ta.hi], "the 116 region bytes must be untouched"
    mp2 = KC.creature_package(b.patched)
    assert mp2.first_block == mp.first_block
    assert min(mp2.motion_offsets) == min(mp.motion_offsets)
    assert RS.texanim_region(b.patched) == ta
    assert "byte-identical" in b.region_invariant


def test_a_disabled_target_does_not_trip_the_texanim_or_shared_gates():
    """A row that splices nothing states an INTENT; its acknowledgements become mandatory the moment
    it is switched on.  This is what lets a scaffold ship every declared palette, pre-seeded off."""
    blob = build_synth_container(npart=1, texanim=116)
    b = RS.build(_spec(blob, [{"name": "creature.part0", "hue_rotate": 30.0, "enabled": False},
                              {"name": PAL_8BPP, "hue_rotate": 30.0, "enabled": False}]),
                 "t", blob=blob)
    assert b.enabled == [] and b.patched == b.orig


def test_headroom_is_derived_per_target_and_a_zero_headroom_value_lift_refuses():
    """A palette already on the 5-bit ceiling has NO headroom, so a ``value > 1`` can only flatten --
    and 46 of the corpus's 93 creature rows are in that class.  Answerable with
    ``acknowledge_headroom``; a ``value <= 1`` never trips it."""
    blob = build_synth_container(npart=1)
    pal = RS.palette_map(blob).by_name("creature.part0")
    assert RS.palette_peak(blob, pal) == 31                   # the fixture's own precondition
    res = RS.apply_palette(blob, pal, RS.Transform())
    assert res.peak_stock == 31 and res.headroom == 0 and res.value_ceiling == 1.0
    with pytest.raises(RS.ReskinError, match="ZERO HEADROOM"):
        RS.build(_spec(blob, [{"name": "creature.part0", "value": 1.05}]), "t", blob=blob)
    ack = RS.build(_spec(blob, [{"name": "creature.part0", "value": 1.05,
                                 "acknowledge_headroom": True}]), "t", blob=blob)
    assert ack.enabled[0].result.clipped > 0
    calm = RS.build(_spec(blob, [{"name": "creature.part0", "value": 1.0, "saturation": 0.8}]),
                    "t", blob=blob)
    assert calm.enabled[0].result.peak_stock == 31


def test_a_palette_with_real_headroom_is_not_refused():
    """The other side: the gate is about ZERO headroom, not about ``value > 1`` in general."""
    blob = build_synth_container(npart=1)
    pal = RS.palette_map(blob).by_name(PAL_4BPP)
    peak = RS.palette_peak(blob, pal)
    assert peak < 31, "the fixture's 4bpp row must have headroom for this test to mean anything"
    b = RS.build(_spec(blob, [{"name": PAL_4BPP, "value": 1.05,
                               "acknowledge_shared": True}]), "t", blob=blob)
    assert b.enabled[0].result.headroom == 31 - peak


def test_self_check_blowout_gate_FAILS_on_an_over_bright_knob_and_refuses_the_stage():
    """THE GATE, not the counter: a ``value`` large enough to flatten most of a palette onto the
    ceiling must make ``self_check`` report NOT ok, which is what stops ``build`` from staging it."""
    blob = build_synth_container(npart=1)
    b = RS.build(_spec(blob, [{"name": "creature.part0", "value": 3.0,
                               "acknowledge_headroom": True}]), "t", blob=blob)
    c = RS.self_check(b)
    blow = [g for g in c.rules if "flattens more than" in g.name]
    assert len(blow) == 1 and not blow[0].ok
    assert "BLOWN OUT" in blow[0].detail and "creature.part0" in blow[0].detail
    assert not c.ok


def test_self_check_blowout_gate_PASSES_when_only_a_few_ceiling_entries_clip():
    """Not a tripwire on ANY clip: a handful of already-at-the-ceiling entries is normal and must
    still pass, with the census REPORTED rather than hidden."""
    blob = build_synth_container(npart=1)
    pal = RS.palette_map(blob).by_name("creature.part0")
    knob = next((v for v in [1.0 + i / 200.0 for i in range(1, 60)]
                 if 0 < RS.apply_palette(blob, pal, RS.Transform(val=v)).clip_fraction
                 <= RS.BLOWOUT_FRACTION), None)
    assert knob is not None, "the fixture palette admits no small-clip value knob"
    b = RS.build(_spec(blob, [{"name": "creature.part0", "value": knob,
                               "acknowledge_headroom": True}]), "t", blob=blob)
    blow = [g for g in RS.self_check(b).rules if "flattens more than" in g.name][0]
    assert blow.ok and "clipped" in blow.detail and "BLOWN OUT" not in blow.detail


def test_scenery_only_reskin_of_a_creature_less_container():
    """348 of the 372 corpus containers have no id-4 at all."""
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


# ============================================================ (3) the region gate (the fail-OPEN trap)
def test_region_gate_spans_whole_geom_blocks_not_a_sixteen_byte_stub():
    """THE ``Geom.end`` TRAP, pinned as a property of the derived regions.

    The study reached ``Geom.end`` through a bare ``except`` that fell back to ``base + 0x10``; on the
    kit's ``Geom`` that fallback would have made every GEOM region 16 bytes and the byte-identical
    gate would have gone green while gating almost nothing.  A GEOM region here must span the whole
    block the scanner found -- which for this fixture's degenerate blocks is 0x48 bytes, not 0x10.
    """
    blob = build_synth_container(npart=1)
    geoms = [(n, lo, hi) for n, lo, hi in RS._regions(blob, 999) if "GEOM" in n or "geom" in n]
    assert geoms, "the fixture's id-6 so+GEOM pairs must produce GEOM regions"
    assert all(hi - lo > 0x10 for _n, lo, hi in geoms), geoms


def test_region_gate_fires_on_a_planted_diff_inside_the_id3_program_image():
    """Plant the diff inside the id-3 resource -- ``_regions`` names it "id-3 effect program image"
    -- and confirm the regions gate catches exactly that hit, by name."""
    blob = build_synth_container(npart=1)
    pmap = RS.palette_map(blob)
    id3 = next(r for r in KC.parse_header(blob).chunks[0].resources if r.id == 3)
    patched = bytearray(blob)
    patched[id3.offset + 5] ^= 0xFF
    patched = bytes(patched)
    b = RS.Build(effect=999, label="synth", spec_path="t.toml", source="(synthetic)",
                 orig=blob, patched=patched, sha_in=hashlib.sha256(blob).hexdigest(),
                 sha_out=hashlib.sha256(patched).hexdigest(), pmap=pmap, targets=[])
    chk = RS.self_check(b)
    assert not chk.ok
    gate = next(g for g in chk.regions if "BYTE-IDENTICAL" in g.name)
    assert gate.ok is False and "id-3 effect program image" in gate.detail


def test_self_check_flags_a_byte_changed_outside_every_named_span_and_region():
    """A single planted byte inside the creature's texture PAGES: outside every derived span, owned by
    no target.  Accounting, the region gate and the dedicated texel gate must EACH notice."""
    blob = build_synth_container(npart=2)
    pmap = RS.palette_map(blob)
    mp = KC.creature_package(blob)
    patched = bytearray(blob)
    patched[mp.tex_file_offset + 100] ^= 0xFF
    patched = bytes(patched)
    b = RS.Build(effect=999, label="synth", spec_path="t.toml", source="(synthetic)",
                 orig=blob, patched=patched, sha_in=hashlib.sha256(blob).hexdigest(),
                 sha_out=hashlib.sha256(patched).hexdigest(), pmap=pmap, targets=[])
    chk = RS.self_check(b)
    assert not chk.ok
    acc = {g.name: g for g in chk.accounting}
    assert acc["every changed byte belongs to a named target"].ok is False
    assert acc["every changed byte lands inside a derived CLUT span"].ok is False
    reg = {g.name: g for g in chk.regions}
    assert next(g for n, g in reg.items() if "BYTE-IDENTICAL" in n).ok is False
    assert next(g for n, g in reg.items() if "TEXEL region" in n).ok is False


def test_self_check_passes_every_accounting_and_region_gate_for_a_real_build():
    """The positive control (quality is NOT asserted -- the synthetic CLUT is arithmetic noise, and
    the luminance-ordering gate is about REAL art)."""
    blob = build_synth_container(npart=2)
    b = RS.build(_spec(blob, [{"name": "creature.part0", "hue_rotate": 90.0},
                              {"name": PAL_8BPP, "hue_rotate": 45.0, "saturation": 0.8,
                               "acknowledge_shared": True}]), "t", blob=blob)
    chk = RS.self_check(b)
    for g in chk.accounting + chk.rules + chk.regions:
        assert g.ok, (g.name, g.detail)


# ============================================================ (4) orthogonality (the OTHER fail-open)
def test_orthogonality_with_no_sibling_declared_skips_and_says_UNPROVEN():
    """Two gates always, never absent -- and a skip must read as UNPROVEN, never as a proof."""
    blob = build_synth_container(npart=1)
    b = RS.build(_spec(blob, [{"name": "creature.part0", "hue_rotate": 10.0}]), "t", blob=blob)
    gates = RS._orthogonality(b, set())
    assert len(gates) == 2 and all(g.ok for g in gates)
    assert all("SKIPPED" in g.detail and "UNPROVEN" in g.detail for g in gates)
    assert any("W2's rescore" in g.name for g in gates)
    assert any("W3's retime" in g.name for g in gates)


def test_orthogonality_fails_loudly_when_the_spec_names_a_sibling_that_does_not_exist():
    """Being wrong about a file you NAMED is not the same as not naming one."""
    blob = build_synth_container(npart=1)
    spec = _spec(blob, [{"name": "creature.part0", "hue_rotate": 10.0}])
    spec["reskin"]["orthogonality"] = {"rescore": "no_such_spec.toml"}
    b = RS.build(spec, "t", blob=blob)
    bad = [g for g in RS._orthogonality(b, set()) if "rescore" in g.name][0]
    assert not bad.ok and "NAMED it" in bad.detail


def test_orthogonality_resolves_a_sibling_against_the_SPEC_dir_not_the_module_dir(tmp_path):
    """THE MODULE-RELATIVE TRAP.  The study resolved siblings against its own directory; in a package
    that directory holds no toml, so every declared sibling would resolve to nothing, every gate would
    report SKIPPED and the orthogonality proof would evaporate for every user while still printing as
    a pass.  Relative names resolve against the SPEC file."""
    blob = build_synth_container(npart=1)
    (tmp_path / "sib_rescore.toml").write_text("[rescore]\neffect = 999\n", encoding="utf-8")
    spec = _spec(blob, [{"name": "creature.part0", "hue_rotate": 10.0}])
    spec["reskin"]["orthogonality"] = {"rescore": "sib_rescore.toml"}
    b = RS.build(spec, str(tmp_path / "x_reskin.toml"), blob=blob)
    g = [x for x in RS._orthogonality(b, set()) if "rescore" in x.name][0]
    assert "SKIPPED: no rescore spec at" not in g.detail, \
        "a relative sibling beside the spec must RESOLVE, not read as missing"


def test_orthogonality_skips_a_sibling_that_targets_another_effect(tmp_path):
    """Rebuilding another effect's edits proves nothing about this one, so the gate SKIPS with that
    stated rather than passing or failing silently."""
    blob = build_synth_container(npart=1)
    (tmp_path / "other_rescore.toml").write_text("[rescore]\neffect = 227\n", encoding="utf-8")
    spec = _spec(blob, [{"name": "creature.part0", "hue_rotate": 10.0}])
    spec["reskin"]["orthogonality"] = {"rescore": "other_rescore.toml"}
    b = RS.build(spec, str(tmp_path / "x_reskin.toml"), blob=blob)
    g = [x for x in RS._orthogonality(b, set()) if "rescore" in x.name][0]
    assert g.ok and "targets ef227" in g.detail and "this reskin targets ef999" in g.detail


def test_a_declared_retime_sibling_skips_with_the_reason_named_and_never_crashes(tmp_path):
    """THE RETIME LANE IS STUDY-ONLY.  A spec that names one must get an explicit skip saying the lane
    is not part of this package -- never a ``ModuleNotFoundError`` dressed as a failed rebuild, and
    never a silent pass that reads like a proof."""
    blob = build_synth_container(npart=1)
    (tmp_path / "x_retime.toml").write_text("[retime]\neffect = 999\n", encoding="utf-8")
    spec = _spec(blob, [{"name": "creature.part0", "hue_rotate": 10.0}])
    spec["reskin"]["orthogonality"] = {"retime": "x_retime.toml"}
    b = RS.build(spec, str(tmp_path / "x_reskin.toml"), blob=blob)
    g = [x for x in RS._orthogonality(b, set()) if "retime" in x.name][0]
    assert g.ok, "a study-only lane is a SKIP, not a failure"
    assert "STUDY-ONLY LANE" in g.detail and "UNPROVEN" in g.detail
    # the registration seam the skip message names: a caller that owns a retime implementation puts
    # it here and the gate becomes a real intersection proof again.
    assert "rescore" in RS.ORTH_REBUILDERS and "retime" not in RS.ORTH_REBUILDERS


# ============================================================ (5) staging, the ledger and the revert
def _manifest(root) -> dict:
    out = {}
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            p = os.path.join(dirpath, f)
            out[os.path.relpath(p, root).replace("\\", "/")] = \
                hashlib.sha256(Path(p).read_bytes()).hexdigest()
    return out


def _minimal_build(effect: int = 999, npart: int = 1) -> RS.Build:
    blob = build_synth_container(npart=npart)
    patched = bytearray(blob)
    patched[KC.parse_header(blob).chunks[0].resources[1].offset] ^= 0xFF   # id-3 filler, any change
    patched = bytes(patched)
    return RS.Build(effect=effect, label="synth", spec_path="t.toml", source="(synthetic)",
                    orig=blob, patched=patched, sha_in=hashlib.sha256(blob).hexdigest(),
                    sha_out=hashlib.sha256(patched).hexdigest(),
                    pmap=RS.palette_map(blob), targets=[])


def test_staging_refuses_the_repo():
    """The provenance guard, re-pointed at ``export.assert_local_only`` semantics in the promotion --
    a git checkout ANYWHERE up the ancestry, so it catches this worktree without hardcoding a root.
    The message keeps the phrase the study's own tests match on."""
    with pytest.raises(RS.R.RescoreError, match="under the repo"):
        RS.R._refuse_repo_path(Path(__file__).resolve().parent)


def test_staging_refuses_a_streamingassets_tree(tmp_path):
    d = tmp_path / "SomeMod" / "StreamingAssets" / "Data"
    d.mkdir(parents=True)
    with pytest.raises(RS.R.RescoreError, match="StreamingAssets"):
        RS.R._refuse_repo_path(d)


def test_staging_refuses_the_install_unless_allow_install(tmp_path):
    game = tmp_path / "FINAL FANTASY IX"
    (game / "FF9CustomMap").mkdir(parents=True)
    b = _minimal_build()
    with pytest.raises(RS.R.RescoreError, match="game install"):
        RS.stage(b, root=game / "FF9CustomMap", game_root=str(game), previews=False)


def test_staging_root_is_per_effect_so_two_effects_can_never_share_a_kit():
    """With ONE root, a second summon staged in the same session overwrites the first one's
    container, previews, manifest and REVERT SCRIPT -- the artifact whose loss is unrecoverable."""
    assert RS.staging_root(211) != RS.staging_root(251)
    assert RS.staging_root(227) == os.path.join(str(RS.STAGING_BASE), "ef227")
    assert RS.LEGACY_STAGING == {}, "the kit ships no per-installation staging pins"


def test_stage_defaults_to_the_per_effect_root_under_the_local_only_base(tmp_path, monkeypatch):
    monkeypatch.setattr(RS, "STAGING_BASE", tmp_path / "out")
    b = _minimal_build(effect=998)
    out = RS.stage(b, game_root=None, previews=False)
    assert out["staging_root"] == str(tmp_path / "out" / "ef998")
    assert Path(out["container"]).is_file()


def test_the_default_staging_base_is_local_only():
    """The default destination is the one this module CHOOSES rather than accepts, so it is held to
    the full guard -- if it ever became a repo or install path, every build would ship stock bytes
    somewhere committable."""
    assert KE.assert_local_only(RS.STAGING_BASE)


@pytest.mark.parametrize("seed_existing", [False, True])
def test_deploy_and_revert_round_trip_on_a_fake_mod_folder(tmp_path, seed_existing):
    """Against a MOCK live tree, never the install -- fresh-folder and already-carrying-an-override,
    plus idempotent re-deploy and re-revert."""
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

    p2 = subprocess.run([sys.executable, out["scripts"]["deploy"]], capture_output=True, text=True)
    assert p2.returncode == 0 and (dest_dir / "ef999").read_bytes() == b.patched

    p3 = subprocess.run([sys.executable, out["scripts"]["revert"]], capture_output=True, text=True)
    assert p3.returncode == 0, p3.stdout + p3.stderr
    assert _manifest(mod) == before
    if seed_existing:
        assert (dest_dir / "ef999").read_bytes() == prior
    else:
        assert not (dest_dir / "ef999").exists()

    p4 = subprocess.run([sys.executable, out["scripts"]["revert"]], capture_output=True, text=True)
    assert p4.returncode == 0 and _manifest(mod) == before


def test_deploy_script_refuses_with_no_root_and_succeeds_with_an_explicit_root_flag(tmp_path):
    """A plan with no baked default mod folder must REFUSE rather than guess, and must accept
    ``--root`` -- a script that can only run where it was born is un-rehearsable."""
    b = _minimal_build()
    out = RS.stage(b, root=tmp_path / "stage", game_root=None, previews=False)
    p = subprocess.run([sys.executable, out["scripts"]["deploy"]], capture_output=True, text=True)
    assert p.returncode != 0 and "no mod root" in p.stdout

    mod = tmp_path / "FAKE_GAME2" / "FF9CustomMap"
    (mod / "FF9_Data" / "SpecialEffects").mkdir(parents=True)
    p2 = subprocess.run([sys.executable, out["scripts"]["deploy"], "--root", str(mod)],
                        capture_output=True, text=True)
    assert p2.returncode == 0, p2.stdout + p2.stderr
    dest = mod / "FF9_Data" / "SpecialEffects" / "ef999"
    assert dest.read_bytes() == b.patched
    p3 = subprocess.run([sys.executable, out["scripts"]["revert"], "--root", str(mod)],
                        capture_output=True, text=True)
    assert p3.returncode == 0 and not dest.exists()


def test_stage_refuses_a_mod_folder_carrying_a_modfilelist(tmp_path):
    """THE SILENT-FALLBACK LAW: ``TryFindAssetInModOnDisc`` TRUSTS an existing ``ModFileList.txt`` and
    never calls ``File.Exists``, so an unlisted override is INVISIBLE -- and ``SFX.Play`` suppresses
    the missing-asset error, so "nothing changed" is the only symptom you would ever see."""
    b = _minimal_build()
    mod = tmp_path / "mod"
    mod.mkdir()
    (mod / "ModFileList.txt").write_text("something/else\n", encoding="utf-8")
    assert "REFUSING to deploy" in RS.modfilelist_refusal(mod)
    with pytest.raises(RS.ReskinError, match="ModFileList.txt"):
        RS.stage(b, root=tmp_path / "stage", mod_root=mod, refuse_modfilelist=True, previews=False)
    assert RS.modfilelist_refusal(tmp_path / "no-list") is None


def test_the_generated_deploy_script_also_refuses_a_modfilelist(tmp_path):
    """The offline handoff artifact carries the same refusal, so a user who never runs the CLI again
    still cannot write an invisible override."""
    b = _minimal_build()
    mod = tmp_path / "FAKE_GAME" / "FF9CustomMap"
    mod.mkdir(parents=True)
    (mod / "ModFileList.txt").write_text("something/else\n", encoding="utf-8")
    out = RS.stage(b, root=tmp_path / "stage", game_root=str(tmp_path / "FAKE_GAME"),
                   previews=False)
    p = subprocess.run([sys.executable, out["scripts"]["deploy"]], capture_output=True, text=True)
    assert p.returncode != 0 and "ModFileList.txt" in p.stdout


# ============================================================ (6) THE CLI CONTRACT (both verbs)
VERBS = ("summon-reskin", "summon-rescore")


def _parse(argv):
    return cli.build_parser().parse_args(argv)


@pytest.mark.parametrize("verb", VERBS)
def test_both_edit_verbs_are_registered_with_the_whole_sub_verb_ladder(verb):
    """Nothing in the suite enumerates ``build_parser()``'s verb list, so a missing registration
    would otherwise break nothing and be caught by nobody."""
    for action in ("scaffold", "plan", "build", "verify", "deploy", "revert"):
        a = _parse([verb, action, "x.toml"])
        assert a.action == action and a.spec == "x.toml"
        assert callable(a.func)
    with pytest.raises(SystemExit):
        _parse([verb, "not-a-sub-verb"])


@pytest.mark.parametrize("verb", VERBS)
def test_the_ROOT_game_and_mod_folder_flags_SURVIVE_into_the_new_verbs(verb):
    """THE CLOBBER TRAP, pinned.

    A subparser option carrying a literal default OVERWRITES the value the root parser already
    parsed, so ``ff9mapkit --mod-folder X <verb> deploy`` would silently deploy into FF9CustomMap.
    Both new verbs declare ``--game``/``--mod-folder`` with ``default=argparse.SUPPRESS`` precisely
    so this cannot happen; this test is what keeps that decision from being "simplified" away.
    """
    a = _parse(["--game", "G:/FF9", "--mod-folder", "FF9CustomMap-XX", verb, "plan", "x.toml"])
    assert a.game == "G:/FF9"
    assert a.mod_folder == "FF9CustomMap-XX"


@pytest.mark.parametrize("verb", VERBS)
def test_a_sub_verb_level_game_and_mod_folder_still_win(verb):
    """SUPPRESS must not mean "the flag does nothing here" -- naming it AFTER the sub-verb still
    wins, which is the form every example in the help uses."""
    a = _parse([verb, "deploy", "x.toml", "--game", "H:/X", "--mod-folder", "MF2"])
    assert a.game == "H:/X" and a.mod_folder == "MF2"


@pytest.mark.parametrize("verb", VERBS)
def test_with_neither_level_supplying_them_the_ROOT_defaults_are_what_land(verb):
    """SUPPRESS means the SUBPARSER contributes nothing, so what survives is exactly what the root
    parser parsed -- here its own defaults.  (Which is also why the handlers read both through
    ``getattr(..., None)``: whether the attribute exists at all is the root parser's business, not
    theirs, and depending on another parser's defaults is a bug waiting for the day they change.)"""
    a = _parse([verb, "plan", "x.toml"])
    assert getattr(a, "game", "MISSING") is None              # the ROOT default
    assert getattr(a, "mod_folder", None) == config.DEFAULT_MOD_FOLDER


def test_an_existing_summon_verb_still_clobbers_documented_as_is():
    """``summon-import``/``summon-deploy`` carry the clobber today.  Retro-fitting them changes where
    they DEPLOY, which is a separate decision from adding two verbs -- so the behaviour is pinned
    here as it stands, and this test is the tripwire for the day somebody fixes it deliberately."""
    a = _parse(["--game", "G:/FF9", "--mod-folder", "FF9CustomMap-XX", "summon-deploy"])
    assert a.game is None, "summon-deploy still discards a root --game (known, unfixed)"
    assert a.mod_folder == "FF9CustomMap", "summon-deploy still discards a root --mod-folder"


def test_the_mod_root_helper_prefers_root_then_the_documented_resolver(tmp_path, monkeypatch):
    """``--root`` names a folder unconditionally.  Below it the resolver's order applies, and the
    ROOT parser's literal ``FF9CustomMap`` default is read as UNSET -- otherwise a checkout that
    pinned its own folder would be overruled by a default nobody typed."""
    a = _parse(["summon-reskin", "revert", "--ef", "999", "--root", str(tmp_path / "MF")])
    assert cli._summon_edit_mod_root(a) == tmp_path / "MF"

    monkeypatch.setenv("FF9_MOD_FOLDER", "FF9CustomMap-ENV")
    monkeypatch.setattr(config, "find_game_path", lambda explicit=None: tmp_path / "GAME")
    bare = _parse(["summon-reskin", "revert", "--ef", "999"])
    assert cli._summon_edit_mod_root(bare) == (tmp_path / "GAME" / "FF9CustomMap-ENV")
    explicit = _parse(["--mod-folder", "FF9CustomMap-XX", "summon-reskin", "revert", "--ef", "999"])
    assert cli._summon_edit_mod_root(explicit) == (tmp_path / "GAME" / "FF9CustomMap-XX")


def _run(argv, capsys):
    rc = cli.main(argv)
    return rc, capsys.readouterr()


@pytest.mark.parametrize("verb", VERBS)
def test_scaffold_without_ef_is_a_refusal_exit_2(verb, capsys):
    rc, cap = _run([verb, "scaffold"], capsys)
    assert rc == 2 and "needs --ef" in cap.err


@pytest.mark.parametrize("verb,suffix", [("summon-reskin", "reskin"), ("summon-rescore", "rescore")])
def test_a_spec_that_cannot_be_resolved_is_a_refusal_exit_2(verb, suffix, capsys):
    rc, cap = _run([verb, "plan"], capsys)
    assert rc == 2 and ("needs a spec file" in cap.err or "REFUSED" in cap.err)
    assert suffix in cap.err


def test_reskin_cli_round_trip_scaffold_plan_build_verify_offline(tmp_path, capsys):
    """The whole ladder through ``cli.main`` on a container this file wrote -- no install, no corpus.

    Exercised end to end because ``--from`` is honoured on every reading sub-verb, not just
    ``scaffold``: an author (and this suite) can drive the lane from an extracted container, and the
    drift guard, every span/target guard and the whole self-check run on those bytes unchanged.
    """
    blob = build_synth_container(npart=1)
    ef = (tmp_path / "ef999.bytes")
    ef.write_bytes(blob)
    spec = tmp_path / "ef999_reskin.toml"
    stage = tmp_path / "stage"

    rc, cap = _run(["summon-reskin", "scaffold", "--ef", "999", "--from", str(ef),
                    "--out", str(spec)], capsys)
    assert rc == 0 and spec.is_file() and "IDENTITY" in cap.out

    # a scaffold is an IDENTITY spec: it must plan clean and change zero bytes
    rc, cap = _run(["summon-reskin", "plan", str(spec), "--from", str(ef)], capsys)
    assert rc == 0, cap.out + cap.err
    assert "TOTAL 0 bytes" in cap.out

    # ...and it refuses to overwrite itself without --force
    rc, cap = _run(["summon-reskin", "scaffold", "--ef", "999", "--from", str(ef),
                    "--out", str(spec)], capsys)
    assert rc == 2 and "refuses to overwrite" in cap.err
    rc, _cap = _run(["summon-reskin", "scaffold", "--ef", "999", "--from", str(ef),
                     "--out", str(spec), "--force"], capsys)
    assert rc == 0

    rc, cap = _run(["summon-reskin", "build", str(spec), "--from", str(ef), "--out", str(stage)],
                   capsys)
    assert rc == 0, cap.out + cap.err
    assert "STAGED" in cap.out
    assert (stage / "build_manifest.json").is_file()

    rc, cap = _run(["summon-reskin", "verify", str(spec), "--from", str(ef), "--out", str(stage)],
                   capsys)
    assert rc == 0 and "VERIFY: PASS" in cap.out


def test_reskin_cli_verify_with_nothing_staged_is_a_VERDICT_exit_1(tmp_path, capsys):
    """Exit 1 is the verdict code and exit 2 is the refusal code: "I looked and it is wrong" must not
    be reported the same way as "I declined to look"."""
    blob = build_synth_container(npart=1)
    ef = tmp_path / "ef999.bytes"
    ef.write_bytes(blob)
    spec = _write_spec(tmp_path, blob, [{"name": "creature.part0", "hue_rotate": 30.0}])
    rc, cap = _run(["summon-reskin", "verify", str(spec), "--from", str(ef),
                    "--out", str(tmp_path / "nowhere")], capsys)
    assert rc == 1 and "VERIFY: FAIL" in cap.out


def test_reskin_cli_build_refuses_to_stage_a_failing_self_check_exit_1(tmp_path, capsys):
    """A blown-out knob makes the self-check fail, and ``build`` must REFUSE TO STAGE rather than
    write a container the gate already said no to."""
    blob = build_synth_container(npart=1)
    ef = tmp_path / "ef999.bytes"
    ef.write_bytes(blob)
    spec = _write_spec(tmp_path, blob, [{"name": "creature.part0", "value": 3.0,
                                         "acknowledge_headroom": True}])
    stage = tmp_path / "stage"
    rc, cap = _run(["summon-reskin", "build", str(spec), "--from", str(ef), "--out", str(stage)],
                   capsys)
    assert rc == 1 and "REFUSING TO STAGE" in cap.err
    assert not (stage / "build_manifest.json").exists()


def test_reskin_cli_build_refusal_from_the_gate_stack_is_exit_2(tmp_path, capsys):
    """A gate that raises (here: a SHARED palette named with no acknowledgement) is a REFUSAL -- the
    tool declined -- and comes back as 2, with the paragraph the author is meant to read, not a
    traceback."""
    blob = build_synth_container(npart=1)
    ef = tmp_path / "ef999.bytes"
    ef.write_bytes(blob)
    spec = _write_spec(tmp_path, blob, [{"name": PAL_8BPP, "hue_rotate": 30.0}])
    rc, cap = _run(["summon-reskin", "plan", str(spec), "--from", str(ef)], capsys)
    assert rc == 2 and "REFUSED" in cap.err and "SHARED palette" in cap.err
    assert "Traceback" not in cap.err


def test_reskin_cli_deploy_dry_run_stages_a_mirror_and_revert_dry_run_reads_it(tmp_path, capsys):
    """``deploy --dry-run`` exercises the LEDGER path (not just the plan scripts) against a local
    mirror, so the ledger revert script exists to be rehearsed -- and ``revert --dry-run`` then reads
    that plan and writes nothing."""
    blob = build_synth_container(npart=1)
    ef = tmp_path / "ef999.bytes"
    ef.write_bytes(blob)
    spec = _write_spec(tmp_path, blob, [{"name": "creature.part0", "hue_rotate": 30.0}])
    stage = tmp_path / "stage"

    rc, cap = _run(["summon-reskin", "deploy", str(spec), "--from", str(ef), "--out", str(stage),
                    "--dry-run"], capsys)
    assert rc == 0, cap.out + cap.err
    assert "DRY RUN" in cap.out
    mirror = stage / "dry-run-mod" / "FF9_Data" / "SpecialEffects" / "ef999"
    assert mirror.is_file() and mirror.suffix == "", "the override must be EXTENSIONLESS"
    ledger_revert = stage / "revert_summon_reskin_ledger_999.py"
    assert ledger_revert.is_file()

    rc, cap = _run(["summon-reskin", "revert", "--ef", "999", "--out", str(stage),
                    "--root", str(stage / "dry-run-mod"), "--dry-run"], capsys)
    assert rc == 0, cap.out + cap.err
    assert mirror.is_file(), "a dry-run revert must not delete anything"

    rc, cap = _run(["summon-reskin", "revert", "--ef", "999", "--out", str(stage),
                    "--root", str(stage / "dry-run-mod")], capsys)
    assert rc == 0, cap.out + cap.err
    assert not mirror.exists(), "the ledger revert deletes a file the build newly created"


def test_plan_previews_into_the_repo_is_refused_at_the_CLI_seam(tmp_path, capsys):
    """``plan --previews`` is the one sub-verb that WRITES without going through ``stage``, and what
    it writes is DECODED STOCK ART.  The provenance guard has to bite on that path too, or the one
    command that never looked like a write would be the one that leaks stock pixels into a checkout.
    """
    blob = build_synth_container(npart=1)
    ef = tmp_path / "ef999.bytes"
    ef.write_bytes(blob)
    spec = _write_spec(tmp_path, blob, [{"name": "creature.part0", "hue_rotate": 30.0}])
    repo_dir = Path(__file__).resolve().parent          # inside this checkout, by construction
    rc, cap = _run(["summon-reskin", "plan", str(spec), "--from", str(ef), "--previews",
                    "--out", str(repo_dir / "_never_written")], capsys)
    assert rc == 2 and "under the repo" in cap.err
    assert not (repo_dir / "_never_written").exists()


def test_a_dry_run_deploy_needs_no_install_at_all(tmp_path, capsys, monkeypatch):
    """A rehearsal that cannot run without the thing it is rehearsing not-touching is not a
    rehearsal.  Only a REAL deploy resolves the install; ``--dry-run`` must complete on a machine
    that has none (a CI box, a fresh checkout, a colleague's laptop)."""
    def _no_install(explicit=None):
        raise config.ConfigError("no FF9 install (simulated)")
    monkeypatch.setattr(config, "find_game_path", _no_install)

    blob = build_synth_container(npart=1)
    ef = tmp_path / "ef999.bytes"
    ef.write_bytes(blob)
    spec = _write_spec(tmp_path, blob, [{"name": "creature.part0", "hue_rotate": 30.0}])
    stage = tmp_path / "stage"
    rc, cap = _run(["summon-reskin", "deploy", str(spec), "--from", str(ef), "--out", str(stage),
                    "--dry-run"], capsys)
    assert rc == 0, cap.out + cap.err
    assert (stage / "dry-run-mod" / "FF9_Data" / "SpecialEffects" / "ef999").is_file()

    # ...and a REAL deploy on the same machine refuses, naming the install, rather than guessing
    rc, cap = _run(["summon-reskin", "deploy", str(spec), "--from", str(ef), "--out", str(stage)],
                   capsys)
    assert rc == 2 and "simulated" in cap.err


def test_revert_does_not_rebase_onto_the_resolved_folder_unless_told_to(tmp_path, capsys,
                                                                       monkeypatch):
    """THE RE-TARGETING LAW, and the destructive bug it exists to stop.

    A ledger entry for a file the build newly CREATED records no backup, so the revert DELETES it.
    Rebase that plan onto "whatever mod folder resolves right now" and it deletes a file this plan
    never wrote -- somebody else's perfectly good override, with no warning anywhere.  So a bare
    ``revert`` runs where the plan recorded its writes, and only an explicit ``--root`` /
    ``--mod-folder`` re-targets it.
    """
    blob = build_synth_container(npart=1)
    ef = tmp_path / "ef999.bytes"
    ef.write_bytes(blob)
    spec = _write_spec(tmp_path, blob, [{"name": "creature.part0", "hue_rotate": 30.0}])
    stage = tmp_path / "stage"
    assert _run(["summon-reskin", "deploy", str(spec), "--from", str(ef), "--out", str(stage),
                 "--dry-run"], capsys)[0] == 0

    # an INNOCENT bystander: a real override in the folder the resolver happens to point at today
    game = tmp_path / "GAME"
    bystander = game / "FF9CustomMap" / "FF9_Data" / "SpecialEffects" / "ef999"
    bystander.parent.mkdir(parents=True)
    bystander.write_bytes(b"somebody else's perfectly good override")
    monkeypatch.setattr(config, "find_game_path", lambda explicit=None: game)

    mirror = stage / "dry-run-mod" / "FF9_Data" / "SpecialEffects" / "ef999"
    rc, cap = _run(["summon-reskin", "revert", "--ef", "999", "--out", str(stage)], capsys)
    assert rc == 0, cap.out + cap.err
    assert bystander.is_file(), "a bare revert must NEVER touch a folder this plan never wrote to"
    assert not mirror.exists(), "...and it must still undo its own writes, where they actually are"

    # ...and naming the folder explicitly DOES re-target, because then the user said so
    assert "RE-TARGETED" in _run(["summon-reskin", "revert", "--ef", "999", "--out", str(stage),
                                  "--root", str(game / "FF9CustomMap"), "--dry-run"],
                                 capsys)[1].out


@pytest.mark.parametrize("verb,table", [("summon-reskin", "reskin"), ("summon-rescore", "rescore")])
def test_revert_reads_the_effect_id_out_of_the_spec_when_ef_is_omitted(verb, table, tmp_path,
                                                                      capsys):
    """``revert <spec>`` is the documented form, so the effect has to come out of the spec's own
    ``[<table>] effect`` -- WITHOUT building anything.  ``revert`` must work on a machine whose
    install has moved or gone; a revert that needs the install to read a number is a revert you
    cannot run on the day you need it."""
    spec = tmp_path / ("x_%s.toml" % table)
    spec.write_text("[%s]\neffect = 641\n" % table, encoding="utf-8")
    a = _parse([verb, "revert", str(spec)])
    assert cli._summon_edit_effect(a, table, table) == 641
    # ...and the refusal it produces names the SPEC's effect, i.e. the id really was resolved
    rc, cap = _run([verb, "revert", str(spec), "--out", str(tmp_path / "empty"),
                    "--root", str(tmp_path / "mod")], capsys)
    assert rc == 2 and "641" in cap.err


@pytest.mark.parametrize("verb", VERBS)
def test_revert_with_no_ledger_script_refuses_rather_than_reporting_success(verb, tmp_path, capsys):
    """"Nothing to revert" must never be reported as a successful revert: a user who believes a
    revert ran is worse off than one told it did not."""
    rc, cap = _run([verb, "revert", "--ef", "999", "--out", str(tmp_path / "empty"),
                    "--root", str(tmp_path / "mod")], capsys)
    assert rc == 2 and "no ledger revert script" in cap.err


def test_rescore_cli_refuses_an_unknown_spec_key_exit_2(tmp_path, capsys):
    """The camera lane refuses a key its reader would ignore -- most dangerously a mistyped
    ``expect_sha256``, which would silently drop the drift guard."""
    spec = tmp_path / "ef999_rescore.toml"
    spec.write_text("[rescore]\neffect = 999\nexpct_sha256 = \"deadbeef\"\n", encoding="utf-8")
    rc, cap = _run(["summon-rescore", "plan", str(spec)], capsys)
    assert rc == 2 and "unknown key" in cap.err


# ============================================================ (7) INSTALL-GATED BYTE IDENTITY
#: the three cast-proven artifacts, as HASHES.  W4 deployed the ef227 reskin and W5 cast-proved the
#: ef211 (scenery) and ef251 (creature) ones on a SECOND summon each; the promotion is only allowed
#: if the kit's own CLI build path regenerates all three from the committed study specs, byte for
#: byte.  A hash is not stock data -- no container byte is committed anywhere in this repo.
CAST_PROVEN = {
    "bahamut_reskin.toml": (227,
                            "7fef205ffbe547545374de9d1017613448777f0251d9d425b55f7796f688b89a"),
    "phoenix_reskin.toml": (211,
                            "4daab8ade69315e6452a96e5af1092c1bb943e1cec78968f3d9dc20e4d276790"),
    "madeen_reskin.toml": (251,
                           "78b395f89e6114f0639e4463819460eafe9952b4707769ca6ea5b92d474a373b"),
}


@needs_install
@needs_study_specs
@pytest.mark.parametrize("spec_name", sorted(CAST_PROVEN))
def test_the_cast_proven_artifacts_regenerate_byte_for_byte_through_the_CLI(spec_name, tmp_path,
                                                                            capsys):
    """THE ACCEPTANCE BAR.  Not "the port compiles" -- the promoted CLI must produce the exact bytes
    that are (or were) LIVE in the user's install, from the committed spec and this install's own
    stock container.  Anything less and the promotion silently forked the lane."""
    effect, want = CAST_PROVEN[spec_name]
    spec = _STUDY / spec_name
    stage = tmp_path / "stage"
    rc = cli.main(["summon-reskin", "build", str(spec), "--out", str(stage), "--no-previews"])
    out = capsys.readouterr()
    assert rc == 0, out.out + out.err
    man = json.loads((stage / "build_manifest.json").read_text(encoding="utf-8"))
    assert man["effect"] == effect
    assert man["patched_sha256"] == want, (
        "ef%03d rebuilt to %s, not the cast-proven %s" % (effect, man["patched_sha256"], want))
    dest = Path(man["container"])
    assert hashlib.sha256(dest.read_bytes()).hexdigest() == want
    assert dest.suffix == "", "the override must be EXTENSIONLESS (LoadFromDisc reads the raw path)"


#: the camera lane's own cast-proven artifact, staged through ``summon-rescore build``.  Pinned here
#: because this is the only place the SECOND verb's whole read -> build -> splice -> stage path runs
#: against real bytes; the module-level laws are `test_summon_rescore.py`'s.
EF211_RESCORE_SHA = "7979566f916ebf3bded37f705dc52a842c5fe874d40389827f22b2dbe24fefd7"


@needs_install
@needs_study_specs
def test_the_cast_proven_rescore_regenerates_byte_for_byte_through_the_CLI(tmp_path, capsys):
    """The camera half of the acceptance bar: ef211's H-pull, rebuilt from the committed spec through
    ``summon-rescore build``, must be the bytes that were cast-proven in game."""
    spec = _STUDY / "phoenix_rescore.toml"
    if not spec.is_file():
        pytest.skip("phoenix_rescore.toml is not in this tree")
    stage = tmp_path / "stage"
    rc = cli.main(["summon-rescore", "build", str(spec), "--out", str(stage)])
    out = capsys.readouterr()
    assert rc == 0, out.out + out.err
    dest = stage / "mod" / "FF9_Data" / "SpecialEffects" / "ef211"
    assert dest.is_file() and dest.suffix == ""
    assert hashlib.sha256(dest.read_bytes()).hexdigest() == EF211_RESCORE_SHA
    assert (stage / "revert_summon_camera_211.py").is_file(), \
        "the ledger's own revert script is written beside the staged kit, never inside it"
    assert cli.main(["summon-rescore", "verify", str(spec), "--out", str(stage)]) == 0


@needs_install
@needs_study_specs
def test_the_cli_verify_agrees_with_the_build_it_just_staged(tmp_path, capsys):
    """``verify`` re-reads the staged bytes and re-derives from the install rather than trusting a
    recorded hash, so it is a real second opinion and not an echo."""
    stage = tmp_path / "stage"
    assert cli.main(["summon-reskin", "build", str(_STUDY / "bahamut_reskin.toml"),
                     "--out", str(stage), "--no-previews"]) == 0
    capsys.readouterr()
    rc = cli.main(["summon-reskin", "verify", str(_STUDY / "bahamut_reskin.toml"),
                   "--out", str(stage)])
    out = capsys.readouterr()
    assert rc == 0, out.out + out.err
    assert "VERIFY: PASS" in out.out


# ============================================================ promotion follow-up (orchestrator)
@pytest.mark.parametrize("key,where", [
    ("acknowledge_shared", "target"),
    ("acknowledge_headroom", "target"),
    ("acknowledge_texanim", "top"),
    ("acknowledge_texanim_frames", "texel"),
])
def test_a_truthy_string_acknowledge_refuses_rather_than_arming(key, where):
    """W5's own law, applied symmetrically after V1 found reskin still coerced: a TOML author
    writing `acknowledge_* = "false"` must be refused, never silently ARMED (the rescore lane
    already enforced this -- its R3 rule; the asymmetry was the finding).

    ``acknowledge_texanim`` is on this list even though W7 made it a NO-OP: a key that does nothing
    is still a key an author can type wrong, and coercing ``"false"`` to true on a dead key would
    train the habit that kills a live one.  ``acknowledge_texanim_frames`` is W7's NEW acknowledgement
    and lives on the sibling TEXEL lane, so it is exercised through that lane's own ``_ack_bool``
    rather than being assumed to inherit the law.
    """
    blob = build_synth_container(npart=1)
    if where == "texel":
        spec = {"reskin": {"effect": 999, "expect_sha256": hashlib.sha256(blob).hexdigest(),
                           "texel": [{"name": "tex.part0", "source": "unused.png", key: "false"}]}}
        with pytest.raises(RP.RepaintError, match="must be a BOOLEAN"):
            RP.build(spec, "t", blob=blob)
        return
    row = {"name": PAL_8BPP, "hue_rotate": 30.0}
    spec = _spec(blob, [row])
    if where == "target":
        row[key] = "false"
    else:
        spec["reskin"][key] = "false"
    with pytest.raises(RS.ReskinError, match="must be a BOOLEAN"):
        RS.build(spec, "t", blob=blob)


# ============================================================ (7) W6b-1: the PER-VRAM-CELL page map
# The addressable unit of the scenery texel lane is the VRAM PAGE-CELL (64 halfwords x 128 lines =
# 0x4000 B), not the id-0 page RECT: 1,214 of the corpus's 1,317 rects are h=256 and cover TWO
# stacked cells, and `scenery_pages`' (tag, x) key can only ever name the top one.  The fixtures
# below build that shape by hand -- a tall rect, a short one, an id-9 alternate block that lands on
# the same VRAM cell as an id-0 rect, and a deliberately mis-sized rect for the width tripwire.

#: the page rects the paged fixture declares: ef211's own shape in miniature -- one TALL rect (two
#: stacked cells, the lower of which no (tag, x) key can reach), one SHORT rect (exactly one cell),
#: and one at the VRAM cell the id-9 block below also writes (the co-transform shape).
PAGED_RECTS = ((704, 256, 64, 256), (576, 256, 64, 128), (320, 256, 64, 128))
#: resource-table ``info`` enabling id-9 slot 4 -> ``id9_slot_vram(4)`` == (320, 256), which is
#: PAGED_RECTS[2]'s cell exactly.  DERIVED at import so a change to the slot map fails loudly here
#: rather than making this fixture quietly stop testing the collision it exists for.
ID9_INFO = 1 << RS.ID9_SLOT_BIT[4]
assert RS.id9_slot_vram(4) == (320, 256) and PAGED_RECTS[2][:2] == (320, 256)


def _assemble_i(chunks) -> bytes:
    """``[(chunkIndex, [(resourceId, info, payload), ...]), ...]`` -> a whole container.

    :func:`_assemble` hard-codes the resource-table ``info`` byte to 0, and ``info`` is the ONLY
    thing that enables an id-9 slot -- so an id-9 fixture cannot be built through it.  Same table
    layout, one more settable field.
    """
    head = bytearray(struct.pack("<h", len(chunks)))
    body = bytearray()
    for ci, resources in chunks:
        padded = [(rid, info) + _pad_sector(p) for rid, info, p in resources]
        head += struct.pack("<hh", ci, len(padded))
        for rid, info, _p, n in padded:
            head += struct.pack("<bbh", rid, info, n)
        for _rid, _info, p, _n in padded:
            body += p
    assert len(head) <= SECTOR
    return bytes(bytearray(head.ljust(SECTOR, b"\x00")) + body)


def _build_paged_id0(rects=PAGED_RECTS, pal16=None, pal256=None) -> bytes:
    """An id-0 payload that declares REAL page rects on top of the inline CLUT rect.

    Laid out exactly as :func:`ff9mapkit.summons.reskin.id0_palettes` decodes it, so the inline CLUT
    stream ends at precisely ``P + pixelDataRel`` and the derivation's own self-check passes::

        +0x00 pageBlockRel -> the page block   +0x04 inlineRel -> the inline CLUT rect
        page block: { pixelDataRel, nPageRects, Rect[nPageRects] }
        then the inline rect (VRAM rows 244-245), then the page PIXEL stream

    The pixel bytes are COMPUTED per cell (never a corpus run) and are distinct cell to cell, so a
    test can tell which cell an offset landed in.
    """
    pal16 = synth_clut16() if pal16 is None else pal16
    pal256 = synth_clut256(seed=3) if pal256 is None else pal256
    page_rel, page_len = 0x14, 8 + 8 * len(rects)
    inline_rel = page_rel + page_len
    inline_data = inline_rel + 8
    pix_rel = inline_data + 2 * 256 * 2                      # w=256 h=2 rows of CLUT
    buf = bytearray(pix_rel)
    struct.pack_into("<iii", buf, 0x00, page_rel, inline_rel, 1)
    struct.pack_into("<HH", buf, 0x0C, 1, 1)                 # nClut4, nClut8
    struct.pack_into("<HH", buf, 0x10, _CELL_4BPP, _CELL_8BPP)
    struct.pack_into("<ii", buf, page_rel, pix_rel, len(rects))
    for k, (x, y, w, h) in enumerate(rects):
        struct.pack_into("<HHHH", buf, page_rel + 8 + 8 * k, x, y, w, h)
    struct.pack_into("<HHHH", buf, inline_rel, 0, 244, 256, 2)
    row244 = bytearray(512)
    row244[0:32] = _words(pal16)
    buf[inline_data:inline_data + 512] = row244
    buf[inline_data + 512:inline_data + 1024] = _words(pal256)
    stream = bytearray()
    for k, (_x, _y, w, h) in enumerate(rects):               # one COMPUTED byte value per cell
        for j in range(max(1, h // 128)):
            stream += bytes([1 + ((k * 7 + j * 3) % 250)]) * (w * 128 * 2)
    return bytes(buf) + bytes(stream)


def build_synth_paged_container(rects=PAGED_RECTS, id9: int = 0, bindings=DEFAULT_BINDINGS,
                                chunk_index: int = 0) -> bytes:
    """The paged fixture: a creature-less container whose id-0 declares real page rects.

    ``id9`` is a COUNT: 1 gives the co-transform shape (an id-9 block on the same VRAM cell an id-0
    rect writes) and 2 gives the same slot enabled twice, which is the only way to make two writers
    collide on one page-cell KEY.
    """
    res = [(0, 0, _build_paged_id0(rects)), (3, 0, bytes([0x55]) * SECTOR)]
    if bindings:
        res.append((6, 0, _build_models_id6(bindings)))
    for i in range(int(id9)):
        res.append((9, ID9_INFO, bytes([0x77 + i]) * 0x4000))
    return _assemble_i([(chunk_index, res)])


def test_the_paged_fixture_is_well_formed_and_its_rects_decode():
    """Sanity-checks the FIXTURE, so a later failure cannot be a fixture bug wearing a page-map bug's
    clothes.  Both derivations must agree with the rect table this file wrote, byte for byte."""
    blob = build_synth_paged_container()
    c = KC.parse_header(blob, strict=True)
    assert c.cursor_end == len(blob)
    RS.palette_map(blob)                                     # the id-0 self-check passes
    rects = RS.scenery_pages(blob)
    assert sorted(rects) == [("s0", 320), ("s0", 576), ("s0", 704)]
    assert [(r.x, r.y, r.w, r.h) for _k, r in sorted(rects.items())] == \
        [(320, 256, 64, 128), (576, 256, 64, 128), (704, 256, 64, 256)]
    # the id-0 stream cursor advances by the RECT's own w*h*2, in TABLE order
    sp = RS.id0_splits(blob)[0]
    assert rects[("s0", 704)].off == sp.boundary                       # rect 0, 0x8000 B
    assert rects[("s0", 576)].off == sp.boundary + 0x8000              # rect 1
    assert rects[("s0", 320)].off == sp.boundary + 0xC000              # rect 2


def test_page_cells_names_the_LOWER_HALF_that_the_rect_view_cannot_reach():
    """* THE RUNG'S CENTRAL NEW MECHANISM.  ``scenery_pages`` is keyed ``(tag, x)``, so the bottom
    128 lines of an ``h == 256`` rect have no name at all -- on ef211 the top half of column 576 is a
    two-palette refusal and the bottom half is clean single-reader 4bpp, and only the hazardous half
    was addressable.  ``page_cells`` splits the rect and names both, 0x4000 apart."""
    blob = build_synth_paged_container()
    cells = RS.page_cells(blob)
    assert ("s0", 704, 256) in cells and ("s0", 704, 384) in cells
    top, bot = cells[("s0", 704, 256)], cells[("s0", 704, 384)]
    assert bot.off - top.off == RS.PAGE_CELL_BYTES == 0x4000
    assert (top.split, bot.split) == (True, True) and (top.split_index, bot.split_index) == (0, 1)
    assert top.rect_key == bot.rect_key == ("s0", 704) and top.rect_h == bot.rect_h == 256
    assert (top.name, bot.name) == ("cell.s0.x704_y256", "cell.s0.x704_y384")
    # ...and the bytes each names really are that cell's own COMPUTED fill, not the other's
    assert len(set(blob[top.off:top.off + top.nbytes])) == 1
    assert blob[top.off] != blob[bot.off]
    # a SHORT rect is one cell and says so, rather than inventing a phantom lower half
    short = cells[("s0", 576, 256)]
    assert not short.split and short.rect_h == 128 and ("s0", 576, 384) not in cells


def test_every_page_cell_is_the_0x4000_upload_quantum_and_the_key_carries_the_WRITER():
    """Uniqueness BY CONSTRUCTION: the key's first element is the writer, so a cell two resources
    upload appears as the two records it is instead of one silently replacing the other."""
    blob = build_synth_paged_container(id9=1)
    cells = RS.page_cells(blob)
    assert all(c.nbytes == RS.PAGE_CELL_BYTES and c.w == RS.PAGE_CELL_W for c in cells.values())
    assert all(k == c.key for k, c in cells.items())
    assert len(cells) == len({(c.tag, c.x, c.y) for c in cells.values()})
    # THE CO-TRANSFORM SHAPE: one VRAM cell, two writers, two keys, two distinct file offsets
    at_320 = sorted((c for c in cells.values() if c.cell == (320, 256)), key=lambda c: c.tag)
    assert [c.tag for c in at_320] == ["id9.s0", "s0"]
    assert [c.kind for c in at_320] == ["id9", "id0"]
    assert len({c.off for c in at_320}) == 2
    assert blob[at_320[0].off] != blob[at_320[1].off], "genuinely different bytes, as in stock"
    # the id-9 block is folded in under its OWN tag but keeps its owning chunk
    assert all(c.chunk == "s0" and c.slot == 0 for c in cells.values())


def test_page_cells_REFUSES_a_rect_that_is_not_64_halfwords_wide_at_both_derivations():
    """THE ``w != 64`` TRIPWIRE.  Zero live instances -- 2,648 / 2,648 stock cell-writer records are
    w = 64 -- which is exactly why it must exist: a cell is ``w*128*2`` bytes and every consumer
    advances by a flat 0x4000, so the first narrower rect would splice into a neighbour's texels with
    no gate firing anywhere.  It refuses at the RECT view and at the CELL map, because a rule enforced
    at one of two call sites is a rule the other one routes around."""
    blob = build_synth_paged_container(rects=((704, 256, 32, 256),))
    for fn in (RS.scenery_pages, RS.page_cells):
        with pytest.raises(RS.ReskinError) as e:
            fn(blob)
        assert "PAGE-RECT WIDTH" in str(e.value)
        assert "w is 32 halfwords" in str(e.value) and "2,648" in str(e.value)
    assert RS.page_cells(build_synth_paged_container()), "the 64-wide fixture is unaffected"


def test_page_cells_REFUSES_a_rect_whose_height_is_not_a_positive_multiple_of_128_lines():
    """V1 F2 -- the same law as the width tripwire, one axis later.  The cell split is ``h // 128``,
    FLOORING: at ``h = 64`` the one derived cell claims 0x4000 bytes of a rect that holds 0x2000 and
    the splice overlaps the next rect's stream; at ``h = 200`` the trailing 9,216 declared bytes are
    silently stranded.  The corpus is exactly {128, 256} on all 1,317 rects, so this refusal has
    zero live instances -- which is the point."""
    for h in (64, 200):
        blob = build_synth_paged_container(rects=((704, 256, 64, h),))
        for fn in (RS.scenery_pages, RS.page_cells):
            with pytest.raises(RS.ReskinError) as e:
                fn(blob)
            assert "PAGE-RECT HEIGHT" in str(e.value)
            assert ("h=%d" % h) in str(e.value) and "{128, 256}" in str(e.value)
    assert RS.page_cells(build_synth_paged_container()), "the {128,256} fixture is unaffected"


def test_scenery_pages_REFUSES_a_duplicate_column_rather_than_dropping_one_silently():
    """The rect view is a dict keyed ``(tag, x)``: a chunk declaring one column twice used to keep
    only the LAST upload, hiding the first from every consumer including the collision gate.  0 of
    the 1,317 stock rects do it, so this is a tripwire too -- but a silent drop is the one failure
    mode a page map cannot have."""
    blob = build_synth_paged_container(rects=((704, 256, 64, 128), (704, 384, 64, 128)))
    with pytest.raises(RS.ReskinError) as e:
        RS.scenery_pages(blob)
    assert "DUPLICATE PAGE RECT" in str(e.value) and "x=704 twice" in str(e.value)


def test_page_cells_is_a_pure_derivation_of_the_containers_own_bytes():
    """Same bytes in, same map out -- and a map derived off a DIFFERENT container differs.  The
    property the derivation-identity gate below rests on."""
    a, b = build_synth_paged_container(), build_synth_paged_container()
    assert RS.page_cells(a) == RS.page_cells(b)
    assert RS.page_cells(a) != RS.page_cells(build_synth_paged_container(id9=1))


def test_page_cells_REFUSES_two_writers_that_resolve_to_the_SAME_key():
    """"Unique by construction" has to be enforced, or it is only a claim.  A co-transform is several
    DIFFERENT keys over one VRAM cell and is lawful; one WRITER declared twice is one record silently
    replacing another, and there is no honest map of that -- so it refuses.  0 of the 2,648 stock
    cell-writer records collide, which is why the fixture has to manufacture the collision."""
    blob = build_synth_paged_container(id9=2)                # the same id-9 slot enabled twice
    with pytest.raises(RS.ReskinError) as e:
        RS.page_cells(blob)
    assert "DUPLICATE PAGE CELL" in str(e.value) and "('id9.s0', 320, 256)" in str(e.value)
    assert "not a co-transform" in str(e.value)


# ---- the derivation-identity gate ----------------------------------------------------------------
def test_assert_page_cells_identical_PASSES_a_pixel_write_and_CATCHES_a_moved_rect_table():
    """The gate the id-0 region partition is paired with.  A texel splice may move pixels; if it ever
    moved ``pixelDataRel``, the rect count or a rect's shape, the container would still parse, still
    be the same length and still re-derive every palette -- and the whole page map would silently
    name different bytes.  Re-deriving the MAP is what catches that; comparing bytes is not."""
    blob = build_synth_paged_container()
    sp = RS.id0_splits(blob)[0]
    ok = bytearray(blob)
    ok[sp.boundary + 100] ^= 0xFF                            # a licensed pixel edit
    assert "4 page-cell(s) re-derive identically" in \
        RS.assert_page_cells_identical(blob, bytes(ok), "the texel splice")

    rect0_y = sp.lo + 0x14 + 8 + 2                           # rect 0's VRAM y field
    moved = bytearray(blob)
    struct.pack_into("<H", moved, rect0_y, 384)
    with pytest.raises(RS.ReskinError) as e:
        RS.assert_page_cells_identical(blob, bytes(moved), "the texel splice")
    assert "THE PAGE-CELL DERIVATION MOVED" in str(e.value)
    assert "vanished" in str(e.value) and "appeared" in str(e.value)

    rect0_w = sp.lo + 0x14 + 8 + 4                           # rect 0's w field -> trips the width law
    widened = bytearray(blob)
    struct.pack_into("<H", widened, rect0_w, 128)
    with pytest.raises(RS.ReskinError) as e:
        RS.assert_page_cells_identical(blob, bytes(widened), "the texel splice")
    assert "THE PAGE-CELL DERIVATION FAILED on the PATCHED container" in str(e.value)
    assert "PAGE-RECT WIDTH" in str(e.value)


# ============================================================ (8) W6b-1: attribution include_direct
#: a 15bpp DIRECT-colour binding: tpage colour-mode field (bits 7-8) == 2.  DERIVED through the
#: shipped table so a change to ``SO_BPP`` fails here rather than making this fixture test nothing.
TPAGE_15BPP = 0x100
assert RS.SO_BPP[(TPAGE_15BPP >> 7) & 3] == 15
DIRECT_BINDINGS = DEFAULT_BINDINGS + ((TPAGE_15BPP, 0),)


def test_attribution_DROPS_15bpp_direct_binders_by_default_and_include_direct_admits_them():
    """``include_direct`` is a PARAMETER, never a second scanner -- the ``_regions(partition=)``
    precedent.  15bpp binders index no palette, so the CLUT lane has always dropped them; the texel
    lane needs them for the DEPTH derivation (15bpp is a depth the container STATES) and for the
    u-spill census (one halfword is one texel at that depth)."""
    blob = build_synth_paged_container(bindings=DIRECT_BINDINGS)
    off, on = RS.attribution(blob), RS.attribution(blob, include_direct=True)
    assert not off.include_direct and on.include_direct
    assert off.direct == [] and len(on.direct) == 1
    assert [b for b in on.bindings if not b.direct] == off.bindings, \
        "the default population is unchanged, binding for binding -- only the direct set is added"
    d = on.direct[0]
    assert d.bpp == 15 and d.entries == 0 and d.cell == RS.NO_CLUT_CELL and d.direct


def test_include_direct_moves_neither_the_so_COVERAGE_nor_the_derived_SHARED_flags():
    """Coverage is counted BEFORE the depth filter, and a direct binder answers no palette question --
    so admitting them must not widen ``binders()``, ``shared``, or the completeness verdict.  If it
    did, a texel-lane call would silently change what the CLUT lane refuses."""
    blob = build_synth_paged_container(bindings=DIRECT_BINDINGS)
    off, on = RS.attribution(blob), RS.attribution(blob, include_direct=True)
    assert (off.geom_total, off.geom_with_so) == (on.geom_total, on.geom_with_so)
    assert (off.coverage, off.complete) == (on.coverage, on.complete)
    for pal in RS.palette_map(blob).palettes:
        assert off.binders(pal.vram, pal.entries) == on.binders(pal.vram, pal.entries)
    a = [(p.name, p.shared, p.binders) for p in RS.palette_map(blob, attrib=off).palettes]
    b = [(p.name, p.shared, p.binders) for p in RS.palette_map(blob, attrib=on).palettes]
    assert a == b
    assert on.binders(RS.NO_CLUT_CELL, 0) == [], "a direct binder is unreachable through binders()"


# ============================================================ (8b) W6b-3: THE MULTI-PART `so` RECORD
#: tpage words that land on the PAGED fixture's own declared columns, derived from the bit layout
#: rather than guessed: bits 0-3 = column/64, bit 4 = the 256-line half, bits 7-8 = the colour mode.
_TP8_704 = 0x080 | 0x10 | (704 // 64)      # 8bpp, page origin (704, 256)
_TP8_576 = 0x080 | 0x10 | (576 // 64)      # 8bpp, page origin (576, 256)
_TP4_576 = 0x000 | 0x10 | (576 // 64)      # 4bpp, page origin (576, 256)
assert RS.SO_BPP[(_TP8_704 >> 7) & 3] == 8 and (_TP8_704 & 0x0F) * 64 == 704
assert RS.SO_BPP[(_TP4_576 >> 7) & 3] == 4 and (_TP4_576 & 0x0F) * 64 == 576

#: a synthetic multi-part model: ONE GEOM block whose record's array binds the 8bpp cell TWICE,
#: naming TWO DIFFERENT COLUMNS -- the shape 2 of the 3 corpus self-shared palettes actually have,
#: and the reason no order-free column pick exists.  Nothing here is a corpus byte.
_SELF_SHARED = (((_TP8_704, _CELL_8BPP), (_TP8_576, _CELL_8BPP)),)


class _NoBinders:
    """A stand-in for "this view names no binder here" -- so a union can be written without a branch."""
    binders = ()


_EMPTY = _NoBinders()


def test_so_record_multipart_synthetic():
    """★ THE READER FIX, on bytes this file wrote.  ``P = 3`` decodes to three pairs, ``len == 0x20``,
    ``witness == "novel"``, and ``tpage``/``clut`` are the COMPATIBILITY VIEW of entry 0 -- present,
    documented as one entry of an array, and detectable as under-reading through ``nparts``."""
    parts = ((0x88, 0x1234), (0x89, 0x5678), (0x08, 0x9ABC))
    blob = _so_geom_multi(parts)
    rec = RS.so_record(blob, 8 + 8 * len(parts))
    assert rec["nparts"] == 3 and rec["len"] == 0x20 and rec["at"] == 0
    assert rec["parts"] == list(parts)
    assert rec["witness"] == RS.WITNESS_NOVEL
    assert (rec["tpage"], rec["clut"]) == parts[0], "the compat view is ENTRY 0, never a summary"


def test_so_record_arrayb_is_load_bearing():
    """★ THE ACCEPTANCE RESTS ON ``+0x06``.  ``recLen == 8 + 8P`` is near-tautological given
    ``P := (recLen - 8) // 8``; ``arrayB == 8 + 4P`` is the INDEPENDENT halfword, and 126 of 126
    corpus multi-part records take it outside the two values a ``P <= 1`` corpus could supply.  A
    record with the right magic and the right length but a WRONG ``arrayB`` must be REJECTED."""
    parts = ((0x88, 0x1234), (0x89, 0x5678))
    good = bytearray(_so_geom_multi(parts))
    base = 8 + 8 * len(parts)
    assert RS.so_record(bytes(good), base) is not None
    for wrong in (0x08, 0x0C, 0x14, 0xFFFF):
        bad = bytearray(good)
        struct.pack_into("<H", bad, 6, wrong)
        assert RS.so_record(bytes(bad), base) is None, wrong


def test_so_record_incumbent_bytes_unchanged():
    """The existing ``P == 1`` fixture decodes EXACTLY as it did: the containment is a property of the
    reader's OUTPUT on incumbent bytes, not a promise about its input."""
    blob = _so_geom(0x88, _CELL_8BPP)
    rec = RS.so_record(blob, 0x10)
    assert (rec["len"], rec["nparts"], rec["witness"]) == (0x10, 1, RS.WITNESS_INCUMBENT)
    assert (rec["tpage"], rec["clut"]) == (0x88, _CELL_8BPP)
    assert rec["parts"] == [(0x88, _CELL_8BPP)]


def test_so_record_p0_still_counts_as_coverage():
    """★ THE P = 0 INVARIANT -- the hole in the OPPOSITE direction.  A record with zero pairs is still
    a RECORD: it returns a dict with ``parts == []`` and NO ``tpage`` key, and :func:`attribution`
    counts it in ``geom_with_so`` BEFORE any tpage check.  "No pairs, return None" would shrink the
    coverage DENOMINATOR, flip ``complete`` on containers that read UNBOUND today, and demand
    ``acknowledge_shared`` on palettes that never needed it.  Unsafe-by-omission is still unsafe."""
    raw = _so_geom_multi(())
    rec = RS.so_record(raw, 8)
    assert rec is not None and rec["nparts"] == 0 and rec["parts"] == [] and rec["len"] == 8
    assert "tpage" not in rec and "clut" not in rec
    assert rec["witness"] == RS.WITNESS_INCUMBENT, "P == 0 is a length the old reader accepted"

    with_p0 = build_synth_creatureless_container(bindings=DEFAULT_BINDINGS + ((),))
    a = RS.attribution(with_p0)
    assert (a.geom_total, a.geom_with_so) == (4, 4), "the P=0 block is COVERED, it just binds nothing"
    assert a.complete, "and coverage stays COMPLETE, so no palette gains a spurious obligation"
    assert len(a.bindings) == len(RS.attribution(
        build_synth_creatureless_container()).bindings), "it contributes no BINDING"


def test_so_record_terminates_on_hostile_blob():
    """``MAX_SO_PARTS`` is a BOUND, not a fact (the corpus max is P = 7, pinned separately).  The
    probe must terminate on a blob built to keep it walking."""
    biggest = tuple((0x88, 0x100 + i) for i in range(RS.MAX_SO_PARTS))
    ok = _so_geom_multi(biggest)
    assert RS.so_record(ok, 8 + 8 * RS.MAX_SO_PARTS)["nparts"] == RS.MAX_SO_PARTS
    over = tuple((0x88, 0x100 + i) for i in range(RS.MAX_SO_PARTS + 1))
    assert RS.so_record(_so_geom_multi(over), 8 + 8 * (RS.MAX_SO_PARTS + 1)) is None
    assert RS.so_record(b"\x00" * 4096, 4096) is None, "no magic anywhere: terminates, does not raise"
    assert RS.so_record(b"\x73\x6f", 2) is None, "geom_base under the smallest record: no read below 0"


# ============================================ W6b-3 (iii): THE SECOND ARRAY, READ AND NOT INTERPRETED
def test_so_record_returns_the_SECOND_ARRAY_at_the_offsets_arrayB_asserts():
    """R1.  The pairs come out of ``at + 8 + 4P + 4k`` -- the offset the acceptance test just proved
    -- and the whole walk stays INSIDE ``at + len``.  Asserted at ``P == 1`` and at ``P == 7``, where
    an off-by-one in the base would silently return the TPAGE array a second time."""
    one = _so_geom(0x88, _CELL_8BPP, second=(0x0080, 0x0000))
    rec = RS.so_record(one, 0x10)
    assert rec["second"] == [(0x0080, 0x0000)]
    assert rec["parts"] == [(0x88, _CELL_8BPP)], "and the FIRST array is untouched"

    pairs = tuple((0x88, 0x100 + k) for k in range(7))
    sec = tuple((0x10 * (k + 1), 0x20 * (k + 1)) for k in range(7))
    raw = _so_geom_multi(pairs, second=sec)
    rec7 = RS.so_record(raw, 8 + 8 * 7)
    assert rec7["second"] == list(sec) and rec7["parts"] == list(pairs)
    # every pair is inside the record the acceptance test accepted -- 8 + 4P .. 8 + 8P
    for P, r in ((1, rec), (7, rec7)):
        assert len(r["second"]) == P
        assert r["at"] + 8 + 4 * P + 4 * P == r["at"] + r["len"]


def test_so_record_P0_invariant_survives_the_second_array():
    """R2.  A ``P == 0`` record is still a RECORD and now also has an EMPTY second array: no
    ``tpage``/``clut`` keys, ``parts == []``, ``second == []``, and ``attribution``'s coverage
    counters are exactly what :func:`test_so_record_p0_still_counts_as_coverage` pins."""
    rec = RS.so_record(_so_geom_multi(()), 8)
    assert rec["parts"] == [] and rec["second"] == []
    assert "tpage" not in rec and "clut" not in rec
    with_p0 = build_synth_creatureless_container(bindings=DEFAULT_BINDINGS + ((),))
    a = RS.attribution(with_p0)
    assert (a.geom_total, a.geom_with_so) == (4, 4) and a.complete


def test_Binding_mover_REFUSES_TO_INDEX_a_multi_part_second_array():
    """★ R3 -- THE ORDER LAW, ENFORCED AT THE CALL SITE RATHER THAN DESCRIBED.

    Pairing second-array entry *k* with binding slot *k* is exactly the claim ``ORDER_UNMEASURED``
    says nothing corroborates, so :attr:`reskin.Binding.mover` answers ``None`` on a NOVEL binding NO
    MATTER what the array holds -- a positional read is UNAVAILABLE, not merely discouraged.
    ``second_pairs`` still carries the WHOLE array on every slot, for identification.
    """
    mixed = ((0x08, _CELL_4BPP), ((0x88, _CELL_8BPP), (0x89, _CELL_8BPP)))
    blob = build_synth_creatureless_container(bindings=mixed)
    inc = RS.attribution(blob, witness=RS.WITNESS_INCUMBENT).bindings
    nov = RS.attribution(blob, witness=RS.WITNESS_NOVEL).bindings
    assert len(inc) == 1 and len(nov) == 2
    assert inc[0].mover == (0, 0), "an INCUMBENT record's array is arity 1: the pick is order-free"
    assert all(b.mover is None for b in nov), "a NOVEL record's array may not be read positionally"
    assert all(len(b.second_pairs) == 2 for b in nov), "...and it is still CARRIED for identification"
    assert nov[0].second_pairs == nov[1].second_pairs, "the WHOLE array on every slot, never a pick"


def test_Binding_mover_carries_a_real_pair_on_an_incumbent_record():
    """R3b.  The other half of the order law: where the arity makes the pick free, the pick is made
    and the value is the bytes -- otherwise the accessor would be a refusal that never answers."""
    blob = build_synth_creatureless_container()
    base = RS.attribution(blob, witness=RS.WITNESS_INCUMBENT).bindings
    assert base and all(b.mover == (0, 0) for b in base), "the default fixture writes a zero array"
    one = _so_geom(0x88, _CELL_8BPP, second=(0x0080, 0x0040))
    rec = RS.so_record(one, 0x10)
    b = RS.Binding(geom=0x10, slot=0, record_at=rec["at"], chunk_slot=0, tpage=0x88,
                   page=(0, 0), bpp=8, clut_word=_CELL_8BPP, cell=(0, 0), entries=256,
                   witness=RS.WITNESS_INCUMBENT, second_pairs=tuple(rec["second"]))
    assert b.mover == (0x0080, 0x0040)


@needs_corpus
def test_the_second_array_moves_NOTHING_ELSE_on_a_real_container():
    """★ R4.  On a real corpus container every OTHER field of every binding is field-for-field what
    it was, and the two new ones are the only difference.  The field list is spelled out rather than
    compared with ``==`` on the dataclass, so a future field cannot slip through unasserted."""
    blob = (CORPUS / "ef424.bytes").read_bytes()
    a = RS.attribution(blob, include_direct=True)
    assert a.bindings, "the fixture for this assertion has to have bindings"
    old = ("geom", "slot", "record_at", "chunk_slot", "tpage", "page", "bpp", "clut_word", "cell",
           "entries", "witness")
    new = ("second_pairs",)
    from dataclasses import fields
    assert tuple(f.name for f in fields(RS.Binding)) == old + new, \
        "W6b-3 (iii) adds exactly ONE field, at the end, with a default"
    # ...and the OLD ones still decode to what a pre-change reader saw: re-derived here from the
    # record's FIRST array alone, which is the only thing the old reader ever read.
    for b in a.bindings:
        rec = RS.so_record(blob, b.geom)
        assert rec is not None and rec["parts"][b.slot] == (b.tpage, b.clut_word)
        assert b.page == ((b.tpage & 0x0F) * 64, ((b.tpage >> 4) & 1) * 256)
        assert b.record_at + rec["len"] == b.geom


def test_witness_class_fails_closed():
    """A guard may only ever fail CLOSED -- the precedent is ``scenery_surface``'s unknown-channel
    raise.  A witness class that fell back to "everything" would silently hand CHANNEL A the census's
    authority the first time somebody typo'd it."""
    blob = build_synth_creatureless_container()
    for bad in ("everything", "INCUMBENT", "", None, 0):
        with pytest.raises(RS.ReskinError):
            RS.attribution(blob, witness=bad)
    with pytest.raises(RS.ReskinError):
        RS.page_depth_view(build_synth_paged_container(), witness="nope")


def test_attribution_witness_partition():
    """★ THE WITNESS PARTITION, on a fixture with one incumbent record and one multi-part one.

    ``WITNESS_ALL`` is the union; ``INCUMBENT`` and ``NOVEL`` are the two halves; and the coverage
    counters stay PER GEOM BLOCK under all three -- a multi-part record is ONE block's coverage
    however many entries it carries."""
    mixed = ((0x08, _CELL_4BPP), ((0x88, _CELL_8BPP), (0x89, _CELL_8BPP)))
    blob = build_synth_creatureless_container(bindings=mixed)
    a_all = RS.attribution(blob)
    a_inc = RS.attribution(blob, witness=RS.WITNESS_INCUMBENT)
    a_nov = RS.attribution(blob, witness=RS.WITNESS_NOVEL)
    assert (a_all.witness, a_inc.witness, a_nov.witness) == (
        RS.WITNESS_ALL, RS.WITNESS_INCUMBENT, RS.WITNESS_NOVEL)
    assert len(a_all.bindings) == 3 and len(a_inc.bindings) == 1 and len(a_nov.bindings) == 2
    assert a_inc.bindings + a_nov.bindings == a_all.bindings, "the halves partition the union"
    assert all(b.witness == RS.WITNESS_INCUMBENT and b.slot == 0 for b in a_inc.bindings)
    assert [b.slot for b in a_nov.bindings] == [0, 1], "slot 0 of a P>=2 record is NOVEL too"
    assert all(b.record_at == a_nov.bindings[0].record_at for b in a_nov.bindings)
    # coverage is PER GEOM BLOCK, never per slot
    assert a_all.geom_total == a_inc.geom_total == a_nov.geom_total == 2
    assert (a_all.geom_with_so, a_inc.geom_with_so, a_nov.geom_with_so) == (2, 1, 1)
    assert (a_all.geom_with_so_novel, a_inc.geom_with_so_novel) == (1, 0)
    assert a_all.complete and not a_inc.complete and not a_nov.complete
    assert a_all.complete_is_novel_dependent, "this container is COMPLETE only via the novel record"


def test_shared_verdict_counts_models_not_slots():
    """★ THE DEDUPE LAW.  One model binding one palette through TWO entries of its OWN array is
    **DERIVED PRIVATE**, and the reason says how many entries -- never "2 GEOM models", which is a
    false statement in the safest-sounding direction and would arm ``acknowledge_shared`` on a palette
    exactly one model reads.  3 corpus palettes are in this class."""
    blob = build_synth_creatureless_container(bindings=_SELF_SHARED)
    pmap = RS.palette_map(blob)
    pal = next(p for p in pmap.palettes if p.entries == 256 and p.slot >= 0)
    assert len(RS.attribution(blob).binders(pal.vram, pal.entries)) == 2, "TWO binding SLOTS..."
    assert pal.shared is False, "...but ONE model"
    assert pal.shared_reason.startswith("DERIVED PRIVATE")
    assert "through 2 entries of its own binding array" in pal.shared_reason
    assert "GEOM models" not in pal.shared_reason
    assert len(pal.binders) == 1
    # ★ AND THE SLOT LIST CARRIES THE SAME QUALIFIER ITS `DERIVED SHARED` SIBLING DOES.  This is the
    # ONE branch where an author reads a slot index next to a PRIVATE verdict, so it is the branch
    # where "record N slot k" is most readable as an ordering claim -- and the order is unmeasured.
    assert "record 0x" in pal.shared_reason and "slot " in pal.shared_reason
    assert "identification only" in pal.shared_reason
    assert "ORDER inside a record's array is UNMEASURED" in pal.shared_reason


def test_shared_verdict_count_matches_its_noun():
    """The COUNT-ONLY half of the same law: where a second model really is there, the verdict stays
    SHARED and the printed number is the number of MODELS.  2 corpus palettes would otherwise print
    one model too many."""
    mixed = (((0x88, _CELL_8BPP), (0x89, _CELL_8BPP)), (0x88, _CELL_8BPP))
    blob = build_synth_creatureless_container(bindings=mixed)
    pmap = RS.palette_map(blob)
    pal = next(p for p in pmap.palettes if p.entries == 256 and p.slot >= 0)
    assert len(RS.attribution(blob).binders(pal.vram, pal.entries)) == 3, "THREE binding SLOTS..."
    assert pal.shared is True and pal.shared_reason.startswith("DERIVED SHARED: 2 GEOM models")
    assert len(pal.binders) == 2 and len(set(pal.binders)) == 2
    assert "MULTI-PART record the kit did not read before W6b-3" in pal.shared_reason


def test_palette_map_and_the_preview_path_ask_for_the_SAME_population():
    """★ ONE DEFAULT, TWO CALL SITES.  ``palette_map``'s own ``attrib = attribution(blob)`` and
    ``render_previews``' ``b.pmap.attrib or attribution(b.orig)`` must resolve to the SAME scan, or a
    palette's VERDICT and the picture the author is shown would be derived from different populations
    -- the exact split that let a false ``DERIVED PRIVATE`` ship in the first place."""
    mixed = ((0x08, _CELL_4BPP), ((0x88, _CELL_8BPP), (0x89, _CELL_8BPP)))
    blob = build_synth_creatureless_container(bindings=mixed)
    pm = RS.palette_map(blob)
    assert pm.attrib is not None and pm.attrib.witness == RS.WITNESS_ALL
    assert pm.attrib.bindings == RS.attribution(blob).bindings
    assert [(p.name, p.shared, p.binders, p.shared_reason) for p in pm.palettes] == \
           [(p.name, p.shared, p.binders, p.shared_reason)
            for p in RS.palette_map(blob, attrib=RS.attribution(blob)).palettes]


def test_page_depth_view_defaults_to_incumbent_and_array_view_is_its_novel_half():
    """★ THE CONTAINMENT, as a default.  ``page_depth_view`` answers a **LICENSE** -- a paintable page
    with no acknowledgement anywhere on the path -- so it defaults to the INCUMBENT witness and
    CHANNEL A is reached by NAME, through :func:`array_depth_view`."""
    mixed = ((_TP4_576, _CELL_4BPP), ((_TP8_704, _CELL_8BPP), (_TP8_576, _CELL_8BPP)))
    blob = build_synth_paged_container(bindings=mixed)
    g = RS.page_depth_view(blob)
    a = RS.array_depth_view(blob)
    assert g and a, "the fixture must exercise BOTH halves or this test proves nothing"
    for cell, pd in g.items():
        assert all(b.witness == RS.WITNESS_INCUMBENT for b in pd.binders), cell
    for cell, pd in a.items():
        assert all(b.witness == RS.WITNESS_NOVEL for b in pd.binders), cell
    both = RS.page_depth_view(blob, witness=RS.WITNESS_ALL)
    for cell in set(g) | set(a):
        want = tuple(sorted({b.bpp for b in list(g.get(cell, _EMPTY).binders)
                             + list(a.get(cell, _EMPTY).binders)}))
        assert both[cell].depths == want, cell


def test_page_depth_view_display_binder_ties_on_VALUES_not_on_the_array_index():
    """★ A4: the display pick is a CONVENTION OVER A SET, and its key is ``(geom, tpage, clut_word)``.

    Two bindings can now share a ``geom``, so the old bare-``geom`` key stopped being a total order.
    Completing it with the array INDEX would make the DISPLAY depend on storage order -- the one thing
    about this format nothing has measured -- so it is completed with the VALUES the display consumes.
    Permuting a record's entries must therefore leave the pick bit-identical."""
    # ONE model, TWO entries, SAME column -- so both land on the same cell and the tie-break is live.
    mixed = (((_TP8_704, _CELL_8BPP), (_TP8_704, _CELL_4BPP)),)
    blob = build_synth_paged_container(bindings=mixed)
    view = RS.array_depth_view(blob)
    assert view, "the fixture must bind a declared page-cell"
    assert any(len(pd.binders) > 1 for pd in view.values()), \
        "the fixture must put TWO bindings on ONE cell or the tie-break is never exercised"
    for cell, pd in view.items():
        keys = [(b.geom, b.tpage, b.clut_word) for b in pd.binders]
        assert keys == sorted(keys), cell
        assert pd.binding is pd.binders[0]
    flipped = (((_TP8_704, _CELL_4BPP), (_TP8_704, _CELL_8BPP)),)
    other = RS.array_depth_view(build_synth_paged_container(bindings=flipped))
    assert sorted(other) == sorted(view)
    for cell in view:
        assert [(b.geom, b.tpage, b.clut_word) for b in other[cell].binders] == \
               [(b.geom, b.tpage, b.clut_word) for b in view[cell].binders], \
            "the display order is a function of the VALUES, so a storage permutation cannot move it"
        assert other[cell].depths == view[cell].depths


def test_preview_source_refuses_with_a_reason():
    """★ A MISSING PREVIEW CARRIES ITS CAUSE.  Under W6b-3 a preview can vanish because a SECOND
    binder became visible -- and on 2 of the 3 corpus self-shared palettes that second binder is the
    SAME MODEL naming a DIFFERENT column, so there is no order-free way to pick which upload to draw.
    The refusal therefore stands (do NOT widen ``!= 1``, do NOT dedupe here) and says why."""
    blob = build_synth_paged_container(bindings=_SELF_SHARED)
    attrib = RS.attribution(blob)
    pal = next(p for p in RS.palette_map(blob, attrib=attrib).palettes
               if p.entries == 256 and p.slot >= 0)
    reasons = []
    assert RS.preview_source(blob, pal, attrib, reasons=reasons) is None
    why = reasons[0]
    assert "NO PREVIEW" in why and "ONE model, 2 entries of its own binding array" in why
    assert "576, 704" in why, "BOTH columns are named -- that is why no column can be picked"
    assert "ORDER" in why and "UNMEASURED" in why
    assert "became visible only at W6b-3" in why

    # ★ AND THE DIRECTION THAT ACTUALLY LOSES A PICTURE: one incumbent binder plus a NOVEL one on a
    # SECOND model.  The incumbent view previews it; the true population cannot, and says so.
    vanish = ((_TP8_704, _CELL_8BPP), ((_TP8_576, _CELL_8BPP), (_TP4_576, _CELL_4BPP)))
    blob2 = build_synth_paged_container(bindings=vanish)
    a_all = RS.attribution(blob2)
    a_inc = RS.attribution(blob2, witness=RS.WITNESS_INCUMBENT)
    pal2 = next(p for p in RS.palette_map(blob2, attrib=a_all).palettes
                if p.entries == 256 and p.slot >= 0)
    assert RS.preview_source(blob2, pal2, a_inc) is not None, "the pre-W6b-3 kit rendered this"
    r2 = []
    assert RS.preview_source(blob2, pal2, a_all, reasons=r2) is None
    assert "2 GEOM models" in r2[0] and "became visible only at W6b-3" in r2[0]


#: a CLUT cell NO id-0 header in this file's fixtures declares.  A record that binds it still COUNTS
#: toward ``so`` coverage (a GEOM block with a record is covered whatever it points at) while leaving
#: every declared palette UNBOUND -- which is the only shape that reaches the two COMPLETE branches.
#: Computed from the word layout (``(y << 6) | (x >> 4)``), never picked.
_CELL_UNDECLARED = (250 << 6) | 0
#: 2 GEOM blocks: one INCUMBENT record and one MULTI-PART one, so coverage is 2/2 -- but only 1/2
#: WITHOUT the reader fix.  ★ That is the exact predicate ``complete_is_novel_dependent`` names.
_NOVEL_DEPENDENT_BINDINGS = ((0x88, _CELL_UNDECLARED),
                             ((0x88, _CELL_UNDECLARED), (0x89, _CELL_UNDECLARED)))
#: the same container with the multi-part block removed: coverage 1/1, honestly, on records the kit
#: could always read.  The CONTRAST that keeps the test above from passing on a tautology.
_INCUMBENT_COMPLETE_BINDINGS = ((0x88, _CELL_UNDECLARED),)


def test_a_NOVEL_DEPENDENT_completeness_keeps_the_shared_guard_ARMED():
    """★ A1: THE 122-PALETTE RELEASE DOES NOT SHIP -- coverage tells the truth, the guard stays armed.

    The reader fix flips ``complete`` to True on 19 corpus containers, and a bare boolean would then
    release 122 palettes from ``acknowledge_shared`` **with no binder naming any of them** -- 24x the
    population of the 5 false PRIVATE verdicts the fix exists to repair, and moving in the PERMISSIVE
    direction.  A loosening produced by a safety fix is still a loosening.

    So the denominator stays HONEST (the container's own bytes say 2 of 2) and the OBLIGATION is
    decided by a second predicate: where completeness would not hold without the multi-part records,
    the verdict is ``UNBOUND at COMPLETE so-coverage (NOVEL-DEPENDENT)`` and ``shared`` stays **True**.
    Nothing about that reading is in-game, so the release awaits an owner-ratified decision instead of
    arriving as a side effect of a bug fix.
    """
    blob = build_synth_creatureless_container(bindings=_NOVEL_DEPENDENT_BINDINGS)
    a = RS.attribution(blob)
    assert (a.geom_total, a.geom_with_so, a.geom_with_so_novel) == (2, 2, 1)
    assert a.complete, "the denominator is HONEST -- the bytes really do carry 2 of 2"
    assert a.complete_is_novel_dependent, "...and it is exactly the reader fix that bought the 2nd"
    assert not RS.attribution(blob, witness=RS.WITNESS_INCUMBENT).complete, \
        "the predicate's whole content: WITHOUT the novel record this container is INCOMPLETE"

    pmap = RS.palette_map(blob)
    for pal in pmap.palettes:
        assert pal.shared is True, pal.name
        assert pal.shared_reason.startswith("UNBOUND at COMPLETE so-coverage (NOVEL-DEPENDENT) (2/2)")
        assert "1 of those 2 GEOM blocks were read ONLY by W6b-3's multi-part reader" \
            in pal.shared_reason
        assert RS._NOVEL_DEPENDENT_CAVEAT in pal.shared_reason, \
            "the caveat travels WITH the verdict -- one that travels separately is one nobody reads"
        assert "awaits owner ratification" not in pal.note, "the note is short; the reason carries it"

    # ★ AND THE GUARD IS LIVE, not merely a flag: `_gate_shared` refuses through `build`
    with pytest.raises(RS.ReskinError, match="SHARED palette") as e:
        RS.build(_spec(blob, [{"name": PAL_8BPP, "hue_rotate": 30.0}]), "t", blob=blob)
    assert "NOVEL-DEPENDENT" in str(e.value), \
        "the refusal quotes the verdict, so an author reads WHY it is armed rather than only THAT"
    assert RS.build(_spec(blob, [{"name": PAL_8BPP, "hue_rotate": 30.0,
                                  "acknowledge_shared": True}]), "t", blob=blob).targets[0].enabled

    # ★ THE OBLIGATION IS THE SAME ONE THE PRE-FIX KIT IMPOSED.  Read with the incumbent witness this
    # container is INCOMPLETE and every palette is SHARED-UNKNOWN -- also `shared = True`.  So the fix
    # changed the REASON and never the answer: no palette here is released BY the fix.
    inc = RS.palette_map(blob, attrib=RS.attribution(blob, witness=RS.WITNESS_INCUMBENT))
    assert all(p.shared and p.shared_reason.startswith("SHARED-UNKNOWN") for p in inc.palettes)

    # ...and the CONTRAST, or the assertions above would hold on a branch nothing can leave: a
    # container COMPLETE on records the kit could always read still releases, exactly as it did.
    plain = build_synth_creatureless_container(bindings=_INCUMBENT_COMPLETE_BINDINGS)
    ap = RS.attribution(plain)
    assert ap.complete and not ap.complete_is_novel_dependent and ap.geom_with_so_novel == 0
    for pal in RS.palette_map(plain).palettes:
        assert pal.shared is False and pal.shared_reason.startswith(
            "UNBOUND at COMPLETE so-coverage (1/1)")
        assert "NOVEL-DEPENDENT" not in pal.shared_reason
    assert RS.build(_spec(plain, [{"name": PAL_8BPP, "hue_rotate": 30.0}]),
                    "t", blob=plain).targets[0].enabled, "no ack needed, and none is demanded"


# ============================================================ (9) W6b-1: THE ID-0 REGION PARTITION
def _covering(regions, off):
    return [n for n, lo, hi in regions if lo <= off < hi]


def test_the_id0_split_is_derived_exactly_as_id0_palettes_derives_it():
    """``page_rel = s32(P)``, ``pix_rel = s32(P + page_rel)`` -- the same two reads, so the region
    gate and the palette derivation cannot drift apart about where the CLUT stream ends."""
    blob = build_synth_paged_container()
    sp, = RS.id0_splits(blob)
    P = next(r for r in KC.parse_header(blob).chunks[0].resources if r.id == 0).offset
    page_rel = struct.unpack_from("<i", blob, P)[0]
    assert (sp.lo, sp.tag, sp.slot, sp.n_rects) == (P, "s0", 0, len(PAGED_RECTS))
    assert sp.boundary == P + struct.unpack_from("<i", blob, P + page_rel)[0]
    assert sp.hi == sp.boundary + sum(r.nbytes for r in RS.scenery_pages(blob).values())
    assert sp.lo < sp.boundary < sp.hi <= sp.run_hi
    # every page cell lives on the PIXEL side; every palette lives on the CLUT side
    assert all(sp.boundary <= c.off and c.off + c.nbytes <= sp.hi
               for c in RS.page_cells(blob).values())
    assert all(sp.lo <= p.off and p.off + p.nbytes <= sp.boundary
               for p in RS.palette_map(blob).palettes)


def test_a_write_to_the_id0_RECT_TABLE_is_CAUGHT_under_the_texel_partition():
    """* THE GAP THIS RUNG CLOSES.  ``_regions`` listed the id-0 resource under NEITHER partition, so
    a scenery splice would have run with ``page_rel``, the rect count and the ``(x, y, w, h)`` rect
    table ungated -- and a mis-seek there re-aims the whole page map with every other gate green."""
    blob = build_synth_paged_container()
    sp, = RS.id0_splits(blob)
    tex = RS._regions(blob, 999, partition="texel")
    for off, what in ((sp.lo, "pageBlockRel"), (sp.lo + 0x14, "pixelDataRel"),
                      (sp.lo + 0x14 + 4, "nPageRects"), (sp.lo + 0x14 + 8, "the rect table"),
                      (sp.boundary - 1, "the last inline CLUT byte")):
        hits = _covering(tex, off)
        assert len(hits) == 1 and "id-0 page-block header" in hits[0], (what, hits)


def test_a_write_to_the_id0_PIXEL_STREAM_is_LICENSED_under_texel_and_GATED_under_clut():
    """The inversion, stated on the bytes.  The texel lane's whole edit surface must be licensed or
    it could never build; the CLUT lane must not be able to touch it by accident."""
    blob = build_synth_paged_container()
    sp, = RS.id0_splits(blob)
    tex = RS._regions(blob, 999, partition="texel")
    clut = RS._regions(blob, 999, partition="clut")
    for off in (sp.boundary, sp.boundary + 0x4000, sp.hi - 1):
        assert _covering(tex, off) == [], "the pixel stream is this lane's licensed surface"
        hits = _covering(clut, off)
        assert len(hits) == 1 and "id-0 page PIXEL stream" in hits[0]
    # ...and the CLUT lane's own palette bytes stay licensed under its own partition
    for p in RS.palette_map(blob).palettes:
        assert _covering(clut, p.off) == []


def test_the_two_id0_halves_TILE_the_declared_extent_with_no_gap_and_no_overlap():
    """The parameter's whole design intent: the partitions disagree about exactly one more boundary
    and agree about every other byte.  Asserted as a tiling, so a future edit that widened one half
    without narrowing the other fails here rather than at a cast."""
    blob = build_synth_paged_container(id9=1)
    sp, = RS.id0_splits(blob)
    assert sp.clut_side[1] == sp.pixel_side[0] == sp.boundary       # they meet, exactly once
    assert sp.clut_side[0] == sp.lo and sp.pixel_side[1] == sp.hi   # and cover the declared extent
    tex = {(n, lo, hi) for n, lo, hi in RS._regions(blob, 999, partition="texel")}
    clut = {(n, lo, hi) for n, lo, hi in RS._regions(blob, 999, partition="clut")}
    only_tex = sorted(tex - clut)
    only_clut = sorted(clut - tex)
    assert [(lo, hi) for _n, lo, hi in only_tex] == [sp.clut_side]
    assert [(lo, hi) for _n, lo, hi in only_clut] == [sp.pixel_side]
    assert RS._regions(blob, 999) == RS._regions(blob, 999, partition="clut"), "default unchanged"
    # the id-9 payload is licensed under BOTH: it is a texel payload the CLUT lane never writes and
    # this rung's split is the id-0 one.  Named here so the omission is a decision, not an oversight.
    id9 = list(RS.id9_pages(blob).values())[0][0]
    assert _covering(tex, id9.off) == [] and _covering(clut, id9.off) == []


def test_a_container_with_no_page_rects_emits_no_EMPTY_pixel_region():
    """A zero-length region gates nothing, so it is omitted rather than emitted -- and the CLUT half
    is still gated under the texel partition, because a header always exists."""
    blob = build_synth_creatureless_container()
    sp, = RS.id0_splits(blob)
    assert sp.n_rects == 0 and sp.pixel_side[0] == sp.pixel_side[1]
    clut = RS._regions(blob, 999, partition="clut")
    tex = RS._regions(blob, 999, partition="texel")
    assert not [n for n, _lo, _hi in clut if "id-0" in n]
    assert [n for n, _lo, _hi in tex if "id-0" in n] == \
        ["s0 id-0 page-block header + clutWord table + inline CLUT stream"]


def test_id0_splits_refuses_a_pixelDataRel_that_points_outside_its_own_resource():
    """Refuse, do not guess.  A header this tool cannot decode must not silently produce a region
    that gates the wrong bytes -- that is a gate reading as a proof."""
    blob = bytearray(build_synth_paged_container())
    sp = RS.id0_splits(bytes(blob))[0]
    struct.pack_into("<i", blob, sp.lo + 0x14, 1 << 24)
    with pytest.raises(RS.ReskinError, match="pixelDataRel"):
        RS.id0_splits(bytes(blob))


def test_a_reskin_and_a_texel_edit_stay_on_their_own_side_of_the_id0_boundary():
    """THE COMPOSITION PROPERTY the two levers already have for creature pages, restated for scenery:
    every byte a CLUT recolour can move is below ``pixelDataRel`` and every byte a texel splice can
    move is above it, so the id-0 halves are disjoint by construction rather than by measurement."""
    blob = build_synth_paged_container()
    sp, = RS.id0_splits(blob)
    b = RS.build(_spec(blob, [{"name": PAL_8BPP, "hue_rotate": 40.0,
                               "acknowledge_shared": True}]), "t", blob=blob)
    changed = {i for i in range(len(blob)) if blob[i] != b.patched[i]}
    assert changed and all(sp.lo <= o < sp.boundary for o in changed)
    b.check = RS.self_check(b)
    for g in b.check.accounting + b.check.rules + b.check.regions:
        assert g.ok, (g.name, g.detail)
    # the map the texel lane addresses through is untouched by the recolour
    assert RS.assert_page_cells_identical(blob, b.patched, "the recolour")


# ============================================================ (10) W6b-1: the corpus census pins
def _corpus_blobs():
    out = []
    for p in sorted(CORPUS.glob("ef*.bytes")):
        if len(p.name) == 11 and p.name[2:5].isdigit():
            out.append((int(p.name[2:5]), p.read_bytes()))
    return out


@needs_corpus
def test_page_cells_reproduces_the_whole_corpus_cell_writer_census():
    """RE-MEASURED, never compared against a prose constant.  The published census (A1's independent
    rasteriser and A2's ``w6b_fmt.writer_cells``, which agree exactly) is 2,648 cell-writer records
    over 372 containers, every one of them 64 halfwords wide and 0x4000 bytes, with 2,648 distinct
    keys -- so uniqueness is a property of the corpus, not a hope."""
    total = id0 = id9 = split = 0
    keys = set()
    for ef, blob in _corpus_blobs():
        for k, c in RS.page_cells(blob).items():
            keys.add((ef,) + k)
            total += 1
            id0 += c.kind == "id0"
            id9 += c.kind == "id9"
            split += c.split
            assert c.w == RS.PAGE_CELL_W and c.nbytes == RS.PAGE_CELL_BYTES
            assert len(blob[c.off:c.off + c.nbytes]) == c.nbytes, "resolves to real file bytes"
    assert (total, id0, id9) == (2648, 2531, 117)
    assert len(keys) == total, "2,648 records, 2,648 distinct keys -- 0 collisions"
    assert split == 2428, "the halves of h=256 rects -- the surface the rect key could not name"


@needs_corpus
def test_the_id0_pixel_stream_runs_into_the_chunks_id1_payload_on_two_thirds_of_the_corpus():
    """A MEASURED format fact, not a tolerance.  The page pixel stream is NOT confined to the id-0
    resource: on 248 of 385 id-0 resources it continues into the id-1 payload of the SAME chunk, and
    id-0 / id-1 are both streamed ids.  Bounding the stream by the id-0 resource's own size would
    have refused 64% of the corpus, which is how this was found."""
    n = past = 0
    for _ef, blob in _corpus_blobs():
        for sp in RS.id0_splits(blob):
            n += 1
            past += sp.hi > sp.res_hi
            assert sp.lo < sp.boundary <= sp.res_hi <= sp.run_hi <= len(blob)
            assert sp.hi <= sp.run_hi
    assert (n, past) == (385, 248)


@needs_corpus
def test_the_so_record_docstring_names_the_ONE_outlier_it_used_to_round_away():
    """RE-MEASURED at W6b-3: **502 accepted records**, 466 carrying a tpage/clut pair, 465 declaring
    ``textured == 1``.  The docstring once said 340 textured against 340 tpage-bearing; the one record
    between the two predicates is ef226 GEOM 0x9c804, and it is NAMED rather than renumbered -- an
    outlier absorbed into a round number is an outlier nobody can look up.

    ★ **AND THE INCUMBENT TRIPLE IS KEPT AS THE CONTAINMENT RUNG.**  ``len10`` (``rec["len"] ==
    0x10``, i.e. ``P == 1``) is **INVARIANT at 340** across the reader fix, and the records the
    pre-W6b-3 reader accepted are still exactly 376 -- so this test pins the NEW population and the
    OLD one side by side, and a regression in either direction has a number that says so.
    """
    total = len10 = textured = tpage_bearing = 0
    inc_total = inc_len10 = inc_textured = 0
    odd = []
    for ef, blob in _corpus_blobs():
        mp = KC.creature_package(blob)
        cg = mp.geom_offset if mp is not None else None
        for g in KC.scan_geom(blob):
            if cg is not None and g.base == cg:
                continue
            rec = RS.so_record(blob, g.base)
            if rec is None:
                continue
            total += 1
            len10 += rec["len"] == 0x10
            textured += bool(rec["textured"])
            tpage_bearing += "tpage" in rec
            if rec["witness"] == RS.WITNESS_INCUMBENT:
                inc_total += 1
                inc_len10 += rec["len"] == 0x10
                inc_textured += bool(rec["textured"])
            if rec["len"] == 0x10 and not rec["textured"]:
                odd.append((ef, g.base))
    assert (total, len10, textured) == (502, 340, 465)
    assert tpage_bearing == 466, "466 records carry at least one pair; 465 of them SAY they do"
    assert (inc_total, inc_len10, inc_textured) == (376, 340, 339), \
        "THE CONTAINMENT RUNG: the incumbent witness reproduces the pre-W6b-3 population exactly"
    assert odd == [(226, 0x9C804)]
    doc = RS.so_record.__doc__.lower()
    assert "465" in doc and "0x9c804" in doc and "ef226" in doc


@needs_corpus
def test_the_direct_binder_population_is_the_only_thing_include_direct_adds_corpus_wide():
    """``include_direct`` adds the direct binders and NOTHING else -- the structural invariant, which
    survives W6b-3 unchanged: ``[b for b in on if not b.direct] == off``, container for container.

    The POPULATION moved with the reader fix (580 / 649 over 69 direct binders in 17 effects, up from
    316 / 340 / 24 / 12), because ``attribution`` now answers the TRUE binding population by default.
    ★ **The INCUMBENT witness reproduces the old numbers exactly**, and pinning both is what makes
    "the census does not move" a statement about this function's OUTPUT rather than a hope.
    """
    off_n = on_n = direct = 0
    i_off_n = i_on_n = i_direct = 0
    effects, i_effects = set(), set()
    for ef, blob in _corpus_blobs():
        a0, a1 = RS.attribution(blob), RS.attribution(blob, include_direct=True)
        assert [b for b in a1.bindings if not b.direct] == a0.bindings
        assert a0.direct == [] and (a0.coverage, a0.complete) == (a1.coverage, a1.complete)
        off_n += len(a0.bindings)
        on_n += len(a1.bindings)
        direct += len(a1.direct)
        if a1.direct:
            effects.add(ef)
        assert all(b.entries == 0 and b.cell == RS.NO_CLUT_CELL for b in a1.direct)
        i0 = RS.attribution(blob, witness=RS.WITNESS_INCUMBENT)
        i1 = RS.attribution(blob, include_direct=True, witness=RS.WITNESS_INCUMBENT)
        assert [b for b in i1.bindings if not b.direct] == i0.bindings
        assert all(b.witness == RS.WITNESS_INCUMBENT and b.slot == 0 for b in i1.bindings), \
            "an incumbent record is P <= 1, so every incumbent binding is entry 0 of its own record"
        i_off_n += len(i0.bindings)
        i_on_n += len(i1.bindings)
        i_direct += len(i1.direct)
        if i1.direct:
            i_effects.add(ef)
    assert off_n == 580 and on_n == 649
    assert (direct, len(effects)) == (69, 17)
    assert i_off_n == 316 and i_on_n == 340, \
        "THE CONTAINMENT RUNG: the incumbent binding population is byte-for-byte pre-W6b-3"
    assert (i_direct, len(i_effects)) == (24, 12)


@needs_corpus
def test_the_previews_the_reader_fix_ADDS_and_the_ones_it_TAKES_are_both_measured():
    """★ A7.m3: THE PREVIEW POPULATION MOVED IN **BOTH** DIRECTIONS, AND BOTH ARE MEASURED.

    ``render_previews`` draws a scenery palette only where exactly one binder resolves it, so the
    reader fix moves that population two ways and only one of them is comfortable:

    * **APPEARING -- 30 palettes.** Every one of them goes 0 -> 1 binder and that single binder is
      NOVEL: a palette the pre-W6b-3 kit could name no reader for now has exactly one, so the author
      gets a picture where they used to get silence.  Single-slot, no set to choose from, no order
      consumed -- the safe direction, and it SHIPS.
    * **VANISHING -- 4 palettes**, named here, where a SECOND binder became visible and the refusal
      (with its reason) is the honest answer.  ``ef381 pal.s0.x0_y248.e256`` is the flagship: 1 -> 7.

    Measured through the SHIPPED :func:`~ff9mapkit.summons.reskin.preview_source` on both witnesses,
    never through a re-implementation, and the three numbers CLOSE: ``57 - 4 + 30 == 83``.  A count
    that closes against its own before-and-after cannot be a coincidence of the instrument.
    """
    appearing, vanishing = [], []
    n_inc = n_all = 0
    for ef, blob in _corpus_blobs():
        a_all = RS.attribution(blob)
        a_inc = RS.attribution(blob, witness=RS.WITNESS_INCUMBENT)
        for pal in RS.palette_map(blob, attrib=a_all).palettes:
            if pal.slot < 0 or pal.entries != 256:            # `render_previews`' own predicate
                continue
            pre = RS.preview_source(blob, pal, a_inc)
            post = RS.preview_source(blob, pal, a_all)
            n_inc += pre is not None
            n_all += post is not None
            if pre is None and post is not None:
                bind = a_all.binders(pal.vram, pal.entries)
                assert not a_inc.binders(pal.vram, pal.entries) and len(bind) == 1 and bind[0].novel, \
                    "a preview may only APPEAR by the 0 -> 1 route, on a single NOVEL binder"
                appearing.append((ef, pal.name))
            if pre is not None and post is None:
                vanishing.append((ef, pal.name))
    assert len(appearing) == 30, "the APPEARING population, pinned"
    assert [(ef, n) for ef, n in vanishing] == [
        (179, "pal.s0.x0_y248.e256"), (381, "pal.s0.x0_y248.e256"),
        (438, "pal.s0.x0_y242.e256"), (438, "pal.s0.x0_y248.e256")], \
        "the four that lose a picture, BY NAME -- a vanished preview counted but not named is a " \
        "number the next rung cannot look up"
    assert (n_inc, n_all) == (57, 83)
    assert n_inc - len(vanishing) + len(appearing) == n_all, "and the three close on each other"


@needs_corpus
def test_the_derivation_identity_gate_is_a_no_op_on_every_stock_container():
    """A gate that cannot pass is as useless as one that cannot fail: stock-vs-stock must be silent
    on all 372 containers before it is allowed to refuse anything."""
    for ef, blob in _corpus_blobs():
        assert "re-derive identically" in RS.assert_page_cells_identical(blob, blob, "ef%03d" % ef)
