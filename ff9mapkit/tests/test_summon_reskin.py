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


def _so_geom(tpage: int, clut: int) -> bytes:
    """One 16-byte ``so`` binding record + the smallest GEOM block :func:`KC.scan_geom` accepts.

    Degenerate on purpose -- 1 bone, 1 mesh, every primitive bucket empty -- but it satisfies the
    scanner's whole acceptance law: the ``pBoneTable == 0x14`` needle, ``pMeshTable == 0x18 +
    (boneCount-1)*4``, and all four chain identities (each pool starts at the 4-byte-aligned end of
    the previous, which for empty pools means they coincide).
    """
    so = struct.pack("<HHHH", 0x6F73, 1, 0x10, 0x0C) + struct.pack("<HHHH", tpage, clut, 0, 0)
    g = bytearray(0x48)
    g[0:4] = bytes([0x00, 0x00, 1, 1])                        # flags, zero, boneCount, meshCount
    struct.pack_into("<II", g, 0x04, 0, 0)
    struct.pack_into("<I", g, 0x0C, 0x14)                     # pBoneTable -- the needle
    struct.pack_into("<I", g, 0x10, 0x18)                     # pMeshTable == 0x18+(1-1)*4
    struct.pack_into("<I", g, 0x14, 0)                        # listHead
    struct.pack_into("<IIIII", g, 0x18 + 0x14, 0x40, 0x44, 0x44, 0x44, 0x44)
    struct.pack_into("<H", g, 0x40, 0)                        # vertsPerBone[0] = 0 vertices
    return so + bytes(g)


def _build_models_id6(bindings) -> bytes:
    return b"".join(_so_geom(tp, cw) for tp, cw in bindings)


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
