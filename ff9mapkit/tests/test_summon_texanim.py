r"""Tests for the TEXANIM READER -- the W7 rung's decoder for the id-5 model image's clip table.

    py -m pytest tests/test_summon_texanim.py -q

Two halves, and the corpus half is the one that can be skipped:

* **the reader's own laws**, on regions THIS FILE GENERATES and splices into the synthetic container
  ``tests/test_summon_reskin.py`` already builds -- no install, no corpus, no game bytes.  Every
  refusal in :mod:`ff9mapkit.summons.texanim` has a test here, and so does the fallback contract that
  the whole W7 lift is conditional on (an armed region that does not decode is *armed and unread*, and
  every consumer must degrade to the pre-W7 refusal).
* **the corpus gates T1-T4** (SYNTHESIS sec 5.3), which run against the read-only stock dumps at
  ``C:/gd/SCRATCH/summon-format`` when that lane is on the machine and skip when it is not -- the same
  ``needs_corpus`` pattern ``test_summon_repaint.py`` already uses.  Every census number they check is
  RE-MEASURED from the corpus in the test body; nothing is compared against a hard-coded table except
  the four counts the rung exists to pin.

PROVENANCE: the synthetic regions below are emitted by :func:`synth_region` from computed values --
never a byte run copied from a stock table.  The corpus tests read the user's own extracted dumps in
place, assert on counts and coordinates, and write nothing.
"""
from __future__ import annotations

import struct
from pathlib import Path

import pytest

from ff9mapkit.summons import container as KC
from ff9mapkit.summons import reskin as RS
from ff9mapkit.summons import texanim as TA
from ff9mapkit.summons import texture as KT
from tests.test_summon_reskin import build_synth_container, build_synth_creatureless_container

CORPUS = Path(r"C:/gd/SCRATCH/summon-format")

needs_corpus = pytest.mark.skipif(
    not (CORPUS / "ef227.bytes").is_file(),
    reason="needs-corpus: the extracted ef###.bytes corpus is not on this machine")

#: the corpus census this rung pins.  Measured every run by :func:`test_the_decoded_census_...` --
#: quoted here only so a drift shows up as a diff against a stated expectation.
CENSUS = {"ef038": (3, 1), "ef177": (9, 2), "ef493": (9, 2), "ef494": (9, 2), "ef495": (9, 2)}


# ============================================================ (0) the synthetic region generator
def synth_region(clips) -> bytes:
    """Emit ONE texanim region from ``[(part, rate, pa, pb, unk1, (x,y,w,h) halfwords, [(sx,sy), ...])]``.

    Laid out exactly as the format demands and nothing more: ``u32 count``; the 20-byte clip records
    packed at ``+4``; the 12-byte windows packed immediately after them; the 4-byte frame entries
    packed after those in clip order.  Every value is a computed argument -- this is a generator, not a
    transcription of a stock table.
    """
    n = len(clips)
    win_base = TA.COUNT_BYTES + TA.CLIP_STRIDE * n
    leaf_base = win_base + TA.WINDOW_STRIDE * n
    total = leaf_base + TA.FRAME_STRIDE * sum(len(c[6]) for c in clips)
    buf = bytearray(total)
    struct.pack_into("<I", buf, 0, n)
    leaf = leaf_base
    for i, (part, rate, pa, pb, unk1, win, frames) in enumerate(clips):
        node = win_base + TA.WINDOW_STRIDE * i
        struct.pack_into("<BBHHHIBBHI", buf, TA.COUNT_BYTES + TA.CLIP_STRIDE * i,
                         0, len(frames), rate, pa, pb, 0, unk1, part, 0, node)
        struct.pack_into("<HHHHI", buf, node, win[0], win[1], win[2], win[3], leaf)
        for j, (sx, sy) in enumerate(frames):
            struct.pack_into("<HH", buf, leaf + TA.FRAME_STRIDE * j, sx, sy)
        leaf += TA.FRAME_STRIDE * len(frames)
    return bytes(buf)


def synth_116() -> bytes:
    """The ef038 SHAPE -- 3 clips, 4 frames, ``4 + 60 + 36 + 16 == 116`` -- with our own geometry."""
    win = (13, 40, 7, 9)                       # halfwords -> texel (26, 40, 14, 9)
    return synth_region([
        (1, 0x1000, 0, 0, 1, win, [(3, 5)]),
        (1, 0x1000, 0, 0, 1, win, [(11, 5)]),
        (0, 0x0800, 7, 33, 1, (2, 2, 4, 6), [(20, 70), (24, 70)]),
    ])


def synth_364() -> bytes:
    """The ef177-family SHAPE -- 9 clips, 18 frames, ``4 + 180 + 108 + 72 == 364``."""
    counts = (1, 1, 2, 3, 3, 1, 1, 3, 3)
    clips = []
    for i, k in enumerate(counts):
        clips.append((i % 2, 0x1000 if k == 1 else 0x0800, 0, 0, 1,
                      (2 + 3 * i, 10 + 5 * i, 5, 8),
                      [(1 + i, 60 + 2 * j) for j in range(k)]))
    return synth_region(clips)


def armed_blob(region: bytes, npart: int = 2, nbytes: int = None) -> bytes:
    """The synthetic container with ``region`` spliced into its texanim span.

    ``nbytes`` overrides the ARMED length the id-4 header declares, which is how a truncation (a span
    shorter than the table) and a slack case (a span longer) are staged without touching any real file.
    """
    n = len(region) if nbytes is None else nbytes
    blob = bytearray(build_synth_container(npart=npart, texanim=n))
    ta = RS.texanim_region(bytes(blob))
    assert ta.armed and ta.nbytes == n
    blob[ta.lo:ta.lo + min(n, len(region))] = region[:n]
    return bytes(blob)


def test_the_synthetic_fixtures_reproduce_the_two_corpus_region_SIZES_by_arithmetic():
    """116 and 364 are not magic numbers: they are ``4 + 20N + 12N + 4*sum(frameCount)``.  The
    generator hits them from the clip/frame counts alone, which is the arithmetic that proved the
    three strides in the first place."""
    assert len(synth_116()) == 4 + 20 * 3 + 12 * 3 + 4 * 4 == 116
    assert len(synth_364()) == 4 + 20 * 9 + 12 * 9 + 4 * 18 == 364


# ============================================================ (1) T1 -- the byte-identity round trip
def test_the_round_trip_is_byte_identical_on_the_synthetic_116_and_364_fixtures():
    """T1, offline half.  ``encode(parse(region)) == region`` is the proof that the reader claimed
    every byte for the right reason -- including the four OPEN fields it refuses to interpret."""
    for region in (synth_116(), synth_364()):
        t = TA.parse_region(region, part_count=2)
        assert TA.encode(t) == region
        assert t.trailing == b"" and t.nbytes == len(region)


@needs_corpus
def test_the_round_trip_is_byte_identical_on_every_real_armed_region():
    """T1, on real bytes: all five armed packages, region in -> table -> region out, unchanged."""
    seen = {}
    for p in sorted(CORPUS.glob("ef*.bytes")):
        blob = p.read_bytes()
        table = TA.parse(blob)
        if table is None:
            continue
        region = blob[table.region.lo:table.region.hi]
        assert TA.encode(table) == region, "%s does not round-trip" % p.stem
        seen[p.stem] = len(region)
    assert sorted(seen) == sorted(CENSUS), "the armed set moved: %s" % sorted(seen)
    assert set(seen.values()) == {116, 364}


# ============================================================ (2) T2 -- None, and never a raise
def test_parse_returns_None_when_there_is_no_creature_package_and_when_the_region_is_empty():
    assert TA.parse(build_synth_creatureless_container()) is None
    assert TA.parse(build_synth_container(npart=1)) is None
    assert TA.protected_rects(build_synth_container(npart=1)) == {}


@needs_corpus
def test_parse_is_None_on_every_unarmed_creature_package_and_never_raises_on_the_corpus():
    """T2, the whole 372-container sweep.  The reader must be safe to call unconditionally: 348
    containers carry no creature at all, 19 creature packages carry an EMPTY region, and the 5 that
    are armed all decode.  A reader that raised on any of those could not sit in a gate."""
    containers = creature = armed = empty = 0
    for p in sorted(CORPUS.glob("ef*.bytes")):
        containers += 1
        blob = p.read_bytes()
        if KC.creature_package(blob) is not None:
            creature += 1
        table = TA.parse(blob)                     # must not raise, on any of the 372
        res = TA.read(blob)
        if table is None:
            empty += 1 if res.present else 0
            assert not res.armed and not res.unparseable and res.table is None
        else:
            armed += 1
            assert res.parsed and not res.unparseable and res.error is None
            assert res.table.count == table.count and res.table.clips == table.clips
    assert (containers, creature, armed) == (372, 24, 5)
    assert empty == creature - armed == 19


# ============================================================ (3) T3 -- the census, re-measured
@needs_corpus
def test_the_decoded_census_is_measured_from_the_corpus_and_the_four_364_regions_are_identical():
    """T3.  ``{ef038: 3 clips / part 1, ef177/493/494/495: 9 clips / part 2}``, plus the finding that
    there are only TWO distinct tables in the whole corpus, not five -- one Carbuncle shipped as four
    ability rows.  Measured here, never asserted from a constant."""
    got, blobs = {}, {}
    for p in sorted(CORPUS.glob("ef*.bytes")):
        blob = p.read_bytes()
        table = TA.parse(blob)
        if table is None:
            continue
        got[p.stem] = (table.count, table.parts[0])
        blobs[p.stem] = blob[table.region.lo:table.region.hi]
        assert len(table.parts) == 1, "%s animates more than one part" % p.stem
        assert len(table.clips) == table.count
    assert got == CENSUS

    family = [blobs[k] for k in ("ef177", "ef493", "ef494", "ef495")]
    assert len(set(family)) == 1, "the four 364-byte regions are no longer byte-identical"
    assert len(set(blobs.values())) == 2, "there should be exactly TWO distinct tables corpus-wide"


@needs_corpus
def test_the_frame_count_byte_still_equals_the_frame_list_length_on_every_corpus_clip():
    """The 39/39 arithmetic identity that decided ``clip+0x01`` (frameCount, not a mode enum).  It is
    a parse invariant now, so this measures that the corpus still satisfies the thing we enforce."""
    nclip = 0
    for p in sorted(CORPUS.glob("ef*.bytes")):
        table = TA.parse(p.read_bytes())
        if table is None:
            continue
        for c in table.clips:
            nclip += 1
            assert c.frames == len(c.sources)
            assert c.window.x2 <= KT.PAGE_W and c.unk1 == 1
            assert (c.flags, c.timer, c.scale) == (0, 0, 0)
    assert nclip == 39


# ============================================================ (4) T4 -- the malformed refusals
def test_a_truncated_region_refuses_and_reports_ARMED_UNPARSEABLE():
    """T4a.  The header declares a shorter span than the table needs, so a pointer leaves the region.
    The refusal has to reach the GATE contract, not just the parser: an armed region that does not
    decode is the pre-W7 state and every consumer must degrade to the pre-W7 refusal."""
    blob = armed_blob(synth_116(), nbytes=100)
    with pytest.raises(TA.TexAnimError, match="LEAVES the"):
        TA.parse(blob)
    res = TA.read(blob)
    assert res.armed and res.unparseable and not res.parsed and res.table is None
    assert "LEAVES the" in res.error
    with pytest.raises(TA.TexAnimError, match="does NOT decode"):
        TA.protected_rects(blob)


def test_a_poisoned_nodeOff_that_leaves_the_region_refuses_and_reports_ARMED_UNPARSEABLE():
    """T4b, the out-of-region flavour."""
    region = bytearray(synth_116())
    struct.pack_into("<I", region, TA.COUNT_BYTES + 0x10, 0x4000)          # clip 0's nodeOff
    blob = armed_blob(bytes(region))
    with pytest.raises(TA.TexAnimError, match="LEAVES the"):
        TA.parse(blob)
    assert TA.read(blob).unparseable


def test_a_poisoned_nodeOff_that_lands_on_another_record_refuses_as_a_DOUBLE_COVER():
    """T4b, the subtler flavour -- a pointer that stays inside the region but claims bytes another
    record already owns.  Only the exact-tiling law catches this one; a bounds check does not."""
    region = bytearray(synth_116())
    struct.pack_into("<I", region, TA.COUNT_BYTES + 0x10, TA.COUNT_BYTES)  # -> onto clip 0 itself
    with pytest.raises(TA.TexAnimError, match="already claimed"):
        TA.parse_region(bytes(region), part_count=2)
    assert TA.read(armed_blob(bytes(region))).unparseable


def test_a_partIndex_at_or_past_partCount_refuses_and_reports_ARMED_UNPARSEABLE():
    """T4c.  A clip that names a page the package does not have cannot be read, and guessing which
    page was meant is exactly the class of guess this reader exists not to make."""
    region = synth_116()
    with pytest.raises(TA.TexAnimError, match="partCount"):
        TA.parse_region(region, part_count=1)                    # the fixture names parts 0 and 1
    blob = armed_blob(region, npart=1, nbytes=len(region))
    assert TA.read(blob).unparseable
    assert TA.parse_region(region, part_count=2).count == 3      # ...and 2 parts is fine


def test_region_slack_refuses_because_the_three_sub_arrays_must_tile_the_region_EXACTLY():
    """The zero-slack half of the tiling law.  A region 8 bytes longer than the table needs leaves 8
    bytes unexplained -- and an unexplained byte means this is not the format we think it is."""
    blob = armed_blob(synth_116(), nbytes=124)
    with pytest.raises(TA.TexAnimError, match="unclaimed"):
        TA.parse(blob)
    assert TA.read(blob).unparseable


def test_a_window_wider_than_one_texture_page_refuses():
    """``x + w <= 64`` halfwords holds on 39/39 stock clips: the rect is page-local by construction.
    A window that reaches past the page edge is not a clip this format can express."""
    region = bytearray(synth_116())
    win = TA.COUNT_BYTES + TA.CLIP_STRIDE * 3
    struct.pack_into("<HH", region, win, 60, 40)                 # x=60 halfwords, w stays 7 -> 67
    with pytest.raises(TA.TexAnimError, match="leaves the part's own"):
        TA.parse_region(bytes(region), part_count=2)


def test_a_zero_clipCount_and_a_zero_frameCount_both_refuse():
    """An all-zero armed region is the shape a half-written patch leaves behind.  It must refuse, not
    decode to an empty table that would read as 'nothing to protect'."""
    with pytest.raises(TA.TexAnimError, match="at least one clip"):
        TA.parse_region(bytes(116), part_count=2)
    region = bytearray(synth_116())
    region[TA.COUNT_BYTES + 1] = 0                               # clip 0's frameCount
    with pytest.raises(TA.TexAnimError, match="no frame list"):
        TA.parse_region(bytes(region), part_count=2)


def test_a_region_too_short_for_its_own_clip_count_refuses():
    with pytest.raises(TA.TexAnimError, match="too short"):
        TA.parse_region(b"\x03", part_count=2)
    with pytest.raises(TA.TexAnimError, match="clipCount 9 needs"):
        TA.parse_region(struct.pack("<I", 9) + bytes(40), part_count=2)


def test_an_armed_region_of_zeroes_degrades_to_armed_and_unread_rather_than_to_an_empty_table():
    """THE FALLBACK CONTRACT, stated as its own test because it is what the whole W7 lift is
    conditional on.  ``read()`` must distinguish armed+parsed from armed+unparseable, and a consumer
    that only checked ``armed`` would be reading a pre-W7 world -- which is exactly the safe answer."""
    blob = build_synth_container(npart=1, texanim=116)            # armed, contents all zero
    res = TA.read(blob)
    assert res.present and res.armed and res.unparseable and res.table is None and res.error
    assert not TA.read(build_synth_container(npart=1)).armed
    assert TA.read(build_synth_creatureless_container()).region.present is False


# ============================================================ (5) runtime state: assert, never fix
def test_non_zero_runtime_state_is_reported_as_a_WARNING_and_carried_verbatim():
    """``flags``/``timer``/``scale`` are zero on disk in 24/24 stock records.  A non-zero one is the
    cheapest corruption detector we have for a container someone already patched -- so it warns, and
    the bytes still round-trip unchanged.  A reader that silently normalised them would erase the
    evidence and change the file it claims to only read."""
    region = bytearray(synth_116())
    off = TA.COUNT_BYTES
    region[off] = 0x03                                            # flags  |= 3, as Start writes
    struct.pack_into("<I", region, off + 8, 0x11)                 # timer
    struct.pack_into("<H", region, off + 0x0E, 0x1000)            # scale, as Start writes
    t = TA.parse_region(bytes(region), part_count=2)
    assert (t.clips[0].flags, t.clips[0].timer, t.clips[0].scale) == (3, 0x11, 0x1000)
    assert len(t.warnings) == 3 and all("NOT normalised" in w for w in t.warnings)
    assert TA.encode(t) == bytes(region), "the reader must not 'fix' runtime state"

    lines = TA.describe(armed_blob(bytes(region)))
    assert any("WARNING" in l and "flags" in l for l in lines)


def test_an_unknown_partCount_warns_rather_than_skipping_the_check_silently():
    t = TA.parse_region(synth_116(), part_count=None)
    assert any("partIndex bound check was SKIPPED" in w for w in t.warnings)


# ============================================================ (6) the protected rect set
def test_protected_rects_and_their_overlap_groups_on_the_synthetic_fixture():
    """Offline: the set is the union of every clip's live window and every source it blits from, per
    part, de-duplicated -- the Shiva shape (two clips sharing one window, three distinct rects)."""
    blob = armed_blob(synth_116())
    prot = TA.protected_rects(blob)
    assert {p: [r.as_tuple() for r in rs] for p, rs in prot.items()} == {
        0: [(4, 2, 8, 6), (40, 70, 8, 6), (48, 70, 8, 6)],
        1: [(6, 5, 14, 9), (22, 5, 14, 9), (26, 40, 14, 9)]}
    assert all(len(g) == 1 for gs in TA.protected_groups(blob).values() for g in gs)
    mp = KC.creature_package(blob)
    assert TA.page_file_offset(blob, 1) == mp.tex_file_offset + KT.PAGE_BYTES


def test_overlap_groups_keep_touching_rects_apart_and_fuse_transitively_overlapping_ones():
    """THE CO-TRANSFORM UNIT.  Two rects that share a texel must be transformed as one pass; two that
    merely touch along an edge share nothing.  Grouped rather than merged into a bounding box, because
    the box of an overlapping group sweeps in texels that are not protected at all."""
    a, b = TA.Rect(0, 0, 10, 10), TA.Rect(10, 0, 10, 10)          # touching
    c, d = TA.Rect(5, 5, 10, 10), TA.Rect(14, 14, 4, 4)           # c overlaps both a and d
    assert not a.intersects(b) and a.intersects(c) and c.intersects(d)
    assert [[r.as_tuple() for r in g] for g in TA.overlap_groups([a, b])] == [
        [(0, 0, 10, 10)], [(10, 0, 10, 10)]]
    assert len(TA.overlap_groups([a, b, c, d])) == 1              # transitively, through c


@needs_corpus
def test_protected_rects_on_ef038_are_the_three_Shiva_eye_rects():
    """The sec 4.3 pin, on real bytes: the live eye window and the two spare frames it blits from."""
    prot = TA.protected_rects((CORPUS / "ef038.bytes").read_bytes())
    assert {p: [r.as_tuple() for r in rs] for p, rs in prot.items()} == {
        1: [(54, 62, 22, 12), (56, 0, 22, 12), (78, 0, 22, 12)]}


@needs_corpus
def test_protected_rects_on_the_carbuncle_family_are_the_nine_eye_and_mouth_rects():
    """The sec 4.3 pin for the other table -- identical on all four packages, as their bytes are.

    The co-transform note is pinned too, and measured rather than quoted: the two mouth-closed frames
    one row apart DO overlap, and so does the eye-closed frame that abuts them, so the three form ONE
    co-transform group of the seven this part carries."""
    expect = [(2, 100, 16, 14), (2, 114, 18, 14), (18, 100, 16, 14), (20, 114, 18, 14),
              (24, 50, 16, 14), (24, 51, 16, 14), (34, 64, 18, 14), (48, 102, 16, 14),
              (66, 78, 18, 14)]
    for name in ("ef177", "ef493", "ef494", "ef495"):
        blob = (CORPUS / (name + ".bytes")).read_bytes()
        prot = TA.protected_rects(blob)
        assert {p: [r.as_tuple() for r in rs] for p, rs in prot.items()} == {2: expect}, name
        groups = [[r.as_tuple() for r in g] for g in TA.protected_groups(blob)[2]]
        assert len(groups) == 7 and [g for g in groups if len(g) > 1] == [
            [(24, 50, 16, 14), (24, 51, 16, 14), (34, 64, 18, 14)]], name


# ============================================================ (7) the readout (L6) + the hard rule
def test_describe_covers_all_four_container_shapes_and_never_raises():
    creatureless = TA.describe(build_synth_creatureless_container())
    assert any("no id-4 creature package" in l for l in creatureless)

    unarmed = TA.describe(build_synth_container(npart=1))
    assert any("region is EMPTY" in l for l in unarmed)

    unparseable = TA.describe(build_synth_container(npart=1, texanim=116))
    assert any("UNPARSEABLE" in l and "armed-and-unread" in l for l in unparseable)
    assert any(TA.REGION_RULE in l for l in unparseable)

    parsed = TA.describe(armed_blob(synth_116()))
    assert any("3 clip(s) over part(s) 0, 1 of 2" in l for l in parsed)
    assert any("THE PROTECTED RECT SET" in l for l in parsed)
    assert any("OPEN -- carried verbatim" in l for l in parsed)
    assert any(TA.REGION_RULE in l for l in parsed)


def test_the_region_rule_names_firstBlock_and_the_predicate_it_protects():
    """R1 lives in exactly one string so a gate quoting it cannot drift from the rule it enforces."""
    assert "firstBlock" in TA.REGION_RULE and "motionOffsets[0]" in TA.REGION_RULE
    assert "Hi_RegisterSummonModel" in TA.REGION_RULE


# ============================================================ (8) encode is a proof, not a writer
def test_encode_refuses_a_rect_that_cannot_be_expressed_in_VRAM_HALFWORDS():
    """The file stores window/source x and w in halfwords, so an odd TEXEL x cannot round-trip.  The
    law is enforced where the bytes are written, not merely described in the docstring."""
    t = TA.parse_region(synth_116(), part_count=2)
    bad = t.clips[0].__class__(**{**t.clips[0].__dict__, "window": TA.Rect(3, 4, 14, 9)})
    table = TA.TexAnimTable(count=t.count, clips=(bad,) + t.clips[1:], region=t.region,
                            nbytes=t.nbytes, part_count=t.part_count)
    with pytest.raises(TA.TexAnimError, match="odd texel x or w"):
        TA.encode(table)


def test_encode_refuses_a_table_whose_declared_counts_disagree_with_what_it_carries():
    t = TA.parse_region(synth_116(), part_count=2)
    with pytest.raises(TA.TexAnimError, match="declares 3 clips but carries 2"):
        TA.encode(TA.TexAnimTable(count=3, clips=t.clips[:2], region=t.region, nbytes=t.nbytes,
                                  part_count=2))
    bad = t.clips[2].__class__(**{**t.clips[2].__dict__, "sources": t.clips[2].sources[:1]})
    with pytest.raises(TA.TexAnimError, match="declares 2 frames but carries 1"):
        TA.encode(TA.TexAnimTable(count=3, clips=t.clips[:2] + (bad,), region=t.region,
                                  nbytes=t.nbytes, part_count=2))


def test_no_writer_verb_is_exported_from_this_module():
    """R2, pinned: W7 ships a READER.  ``encode`` exists for the round trip and nothing in the module
    writes a container, so a future rung cannot grow a writer here by accident and call it W7."""
    assert not [n for n in TA.__all__ if n.startswith(("write", "patch", "splice", "apply", "stage",
                                                       "build", "deploy"))]
