r"""Tests for the TIER W rung-1 camera read-out.

Runs WITHOUT the extracted corpus and WITHOUT the game install: every unit test SYNTHESISES a
container (header + sequence stream + id-2 archive + camera blocks) with the builders below, so the
extractor, the codec adapter, the clock arithmetic and the provenance guard are all exercised on
bytes this file wrote.  Corpus tests skip on absence, exactly as tier-r's do.

    py -m pytest studies/custom-summons/tier-w/test_summon_camera.py -q
"""
from __future__ import annotations

import glob
import os
import struct
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import summon_camera as W                                     # noqa: E402

CORPUS = W.SCRATCH_CORPUS
have_corpus = bool(glob.glob(os.path.join(CORPUS, "ef*.bytes")))
needs_corpus = pytest.mark.skipif(not have_corpus,
                                  reason="extracted ef###.bytes corpus not present at %s" % CORPUS)


# ============================================================ synthetic containers
def code(frame, flags, block=b""):
    return struct.pack("<HH", frame, flags) + block


def camera_block(sequences, selector=b"\x01\x00\x00\x00", anchors=None, extra_flag_bits=0):
    """Assemble a real-grammar SFX camera block: Flags + one u16 offset per present group + blocks.

    Mirrors the native parser fn 0x13030 (D4 sec 2.2) and therefore ``camera_codec``'s own layout:
    the first offset entry is the table's own end and the groups follow in canonical order.
    """
    flags = extra_flag_bits
    blocks = []
    for i, seq in enumerate(sequences):
        flags |= (1 << i)
        blocks.append(b"".join(seq) + struct.pack("<H", 0))
    if selector is not None:
        flags |= 0x08
        blocks.append(selector)
    if anchors:
        flags |= sum(1 << (4 + i) for i in range(len(anchors)))     # one SET bit per 6-byte record
        blocks.append(b"".join(struct.pack("<3h", *a) for a in anchors))
    n = len(blocks)
    cur = 2 + 2 * n
    table = b""
    for b in blocks:
        table += struct.pack("<H", cur)
        cur += len(b)
    return struct.pack("<H", flags) + table + b"".join(blocks)


def sequence_stream(ops):
    """``[(code, arg1, arg2), ...]`` -> the 3-byte record stream, END-terminated."""
    out = bytearray()
    for c, a1, a2 in ops:
        out += bytes((c, a1, a2))
    out += bytes((W.OP_END, 0, 0))
    return bytes(out)


def synth(subfiles, ops, extra_sectors=0, chunks=1):
    """A whole ef###.bytes-shaped container: sector 0 (header + sequence @0x400) then, per chunk,
    ``extra_sectors`` of filler followed by the id-2 archive (directory + sub-files)."""
    per = []
    for ci in range(chunks):
        subs = subfiles[ci] if isinstance(subfiles[0], list) else subfiles
        n = len(subs)
        table = bytearray()
        body = bytearray()
        cur = 4 * n
        offs = []
        for s in subs:
            offs.append(cur)
            body += s
            cur += len(s)
        for o in offs:
            table += struct.pack("<i", o)
        payload = bytes(table) + bytes(body)
        sectors = max(1, (len(payload) + W.SECTOR - 1) // W.SECTOR)
        payload = payload.ljust(sectors * W.SECTOR, b"\x00")
        per.append((sectors, payload))

    head = bytearray(struct.pack("<h", chunks))
    for ci, (sectors, _payload) in enumerate(per):
        head += struct.pack("<hh", ci, 1)                          # chunkIndex, resourceCount
        head += struct.pack("<bbh", 2, 1 if extra_sectors else 0, sectors)
        if extra_sectors:
            head += struct.pack("<h", extra_sectors)
    blob = bytearray(head.ljust(W.SECTOR, b"\x00"))
    blob[0x400:0x400 + len(sequence_stream(ops))] = sequence_stream(ops)
    for _sectors, payload in per:
        blob += b"\x00" * (extra_sectors * W.SECTOR)
        blob += payload
    return bytes(blob)


# Deliberately AUTHORED field values -- not copied from any stock block.  W1e proves no byte run in
# this file appears anywhere in the corpus, so the tests demonstrate the grammar without carrying data.
CAMPOS = b"\x2a\x40\x33\x0d\x11\x1f"        # code, flags, pitch, orientation, roll, distance
TGTPOS = b"\x2a\x40\x07\x03\x01\x02"
FOCAL = b"\x07\x03\x2c\x01"                  # duration 7, flags 3, H = 300
FOCAL2 = b"\x07\x03\x90\x01"                 # ...        H = 400
MARKER = b"\x11\x22\x33\x44"

ESTABLISH = code(1, 0x0809, CAMPOS + TGTPOS + FOCAL)
MOVE = code(30, 0x0002, b"\x2a\x40\x30\x0c\x10\x1e" + struct.pack("<HBB", 24, 2, 0))
TAIL = code(60, 0x8000, MARKER)


# ============================================================ the frame word
def test_frame_word_splits_into_number_and_marks():
    assert W.frame_number(1) == 1 and W.frame_marks(1) == 0
    assert W.frame_number(0x2001) == 1 and W.frame_marks(0x2001) == 0x2000
    assert W.frame_number(0x4001) == 1 and W.frame_marks(0x4001) == 0x4000
    assert W.frame_number(0x6060) == 0x60 and W.frame_marks(0x6060) == 0x6000
    # read as a bare number a marked first keyframe looks like the shot runs BACKWARDS
    assert 0x4001 > 30 and W.frame_number(0x4001) < 30


def test_marked_frames_survive_the_roundtrip_verbatim():
    blk = camera_block([[code(0x4001, 0x0002, CAMPOS + struct.pack("<HBB", 30, 2, 0))]])
    cam = W.parse_camera_block(blk)
    assert W.serialize_camera_block(cam) == blk
    (kf,) = W.keyframes(cam)
    assert (kf.local_frame, kf.marks) == (1, 0x4000)


# ============================================================ (B) the codec adapter
def test_battle_codec_roundtrips_a_synthetic_sfx_block():
    blk = camera_block([[ESTABLISH, MOVE, TAIL]])
    cam = W.parse_camera_block(blk)
    assert cam["flags"] == 0x09
    assert len(cam["sequences"]) == 1 and cam["unknown"] == b"\x01\x00\x00\x00"
    assert W.serialize_camera_block(cam) == blk


def test_roundtrip_survives_three_sequences_and_anchors():
    seq = [ESTABLISH, MOVE, TAIL]
    blk = camera_block([seq, seq, seq], anchors=[(1, -2, 3), (-4, 5, -6)])
    cam = W.parse_camera_block(blk)
    assert len(cam["sequences"]) == 3
    assert cam["position"] is not None and len(cam["position"]) == 12
    assert W.serialize_camera_block(cam) == blk


def test_block_layout_is_the_offset_table_read_literally():
    blk = camera_block([[ESTABLISH, TAIL]])
    lay = W.block_layout(blk)
    assert [n for n, _lo, _hi in lay] == ["sequence0", "selector"]
    assert lay[0][1] == 2 + 2 * len(lay)                # first offset == the table's own end
    assert [lo for _n, lo, _hi in lay] == sorted(lo for _n, lo, _hi in lay)
    assert lay[-1][2] == len(blk)


def test_a_too_short_block_is_refused_not_guessed():
    with pytest.raises(W.SummonCameraError):
        W.parse_camera_block(b"\x09\x00")


def test_outer_groups_names_every_present_group():
    assert W.outer_groups(0x09) == ["sequence0", "selector"]
    assert W.outer_groups(0x0F) == ["sequence0", "sequence1", "sequence2", "selector"]
    assert W.outer_groups(0xC9)[-1] == "anchors x2"


# ============================================================ (A) the extractor
def _one_camera_container(**kw):
    blk = camera_block([[ESTABLISH, MOVE, TAIL]])
    subs = [b"\x00" * 8, b"\x00" * 8, blk, b"\x00" * 8]
    ops = [(W.OP_LOAD_CHUNK, 0, 0), (W.OP_WAIT, 0, 10), (W.OP_PLAY_CAMERA, 2, 0),
           (W.OP_WAIT, 0, 5), (W.OP_RUN_PROGRAM, 0, 0)]
    return synth(subs, ops, **kw), blk


def test_extractor_finds_the_shot_and_its_bytes():
    blob, blk = _one_camera_container()
    ex = W.extract_shots(blob, "synth")
    assert len(ex.shots) == 1
    s = ex.shots[0]
    assert s.block == blk and s.size == len(blk) and s.key == (0, 2)
    assert s.op.seq_tick == 10 and s.op.kind == "PLAY_CAMERA"
    ok, out = s.roundtrip()
    assert ok and out == blk


def test_extractor_records_the_program_start_tick():
    blob, _ = _one_camera_container()
    w = W.walk_camera_ops(blob)
    assert w.program_starts == {(0, 0): 15}                 # 0x80 fires after WAIT 10 + WAIT 5
    assert w.total_ticks == 15


def test_setup_camera_resolves_a_block_too():
    """713 of the corpus's 798 blocks are reached by 0x23, not 0x29 -- a 0x29-only walk sees 11 %."""
    blk = camera_block([[ESTABLISH, TAIL]])
    blob = synth([b"\x00" * 8, blk, b"\x00" * 8], [(W.OP_SETUP_CAMERA, 1, 0)])
    ex = W.extract_shots(blob, "synth")
    assert len(ex.shots) == 1 and ex.shots[0].op.kind == "SETUP_CAMERA"
    assert ex.shots[0].block == blk


def test_setup_camera_ff_names_no_block():
    blob = synth([b"\x00" * 8], [(W.OP_SETUP_CAMERA, W.SETUP_NONE, 0)])
    ex = W.extract_shots(blob, "synth")
    assert not ex.shots and [w for _o, w in ex.skipped] == ["none"]


@pytest.mark.parametrize("arg2", [W.ARG2_LAST, W.ARG2_RANDOM, W.ARG2_TABLE])
def test_dynamic_play_camera_is_marked_not_guessed(arg2):
    """arg2 != 0 picks the shot at RUNTIME (last-used / LCG-random / table lookup).  Offline
    decoding cannot name it, and inventing one would be a silent lie in the read-out."""
    blk = camera_block([[ESTABLISH, TAIL]])
    blob = synth([b"\x00" * 8, blk], [(W.OP_PLAY_CAMERA, 1, arg2)])
    ex = W.extract_shots(blob, "synth")
    assert not ex.shots and ex.dynamic == 1


def test_load_chunk_selects_which_archive_an_index_means():
    blk_a = camera_block([[ESTABLISH, TAIL]])
    blk_b = camera_block([[MOVE, TAIL]])
    blob = synth([[b"\x00" * 8, blk_a, b"\x00" * 8], [b"\x00" * 8, blk_b, b"\x00" * 8]],
                 [(W.OP_LOAD_CHUNK, 1, 0), (W.OP_PLAY_CAMERA, 1, 0)], chunks=2)
    ex = W.extract_shots(blob, "synth")
    assert len(ex.shots) == 1 and ex.shots[0].slot == 1 and ex.shots[0].block == blk_b


def test_out_of_range_index_is_reported_not_read():
    blob = synth([b"\x00" * 8], [(W.OP_PLAY_CAMERA, 9, 0)])
    ex = W.extract_shots(blob, "synth")
    assert not ex.shots and "out of range" in ex.skipped[0][1]


# ---- THE ID-2 EXTRA-SECTOR CORRECTION
def test_extra_sectors_move_the_directory_base():
    """The one corpus file with extra_sectors != 0 (ef251 c0) is unreadable without this."""
    blob, blk = _one_camera_container(extra_sectors=1)
    cont = __import__("ef_container").parse_header(blob)
    arc = W.id2_directory(blob, cont, 0)
    res = cont.chunks[0].resources[0]
    assert res.extra_sectors == 1
    assert arc.base == res.offset + W.SECTOR              # NOT res.offset
    assert arc.base + arc.size == len(blob)               # the region ends exactly where it should
    ex = W.extract_shots(blob, "synth")
    assert len(ex.shots) == 1 and ex.shots[0].block == blk


def test_without_the_correction_the_index_reads_garbage():
    """Guard the correction from a silent regression: parsing at res.offset yields a DIFFERENT
    directory, which is exactly the failure mode on ef251 (a plausible short table, wrong data)."""
    blob, blk = _one_camera_container(extra_sectors=1)
    EC = __import__("ef_container")
    cont = EC.parse_header(blob)
    res = cont.chunks[0].resources[0]
    naive = EC.parse_directory(blob, res.offset)          # the uncorrected read
    good = W.id2_directory(blob, cont, 0).entries
    assert list(naive) != list(good)


# ---- sub-file bounds
def test_bounds_uses_the_next_strictly_greater_entry():
    arc = W.Id2Archive(0, 0x1000, 0x800, (16, 32, 32, 64), 0)
    assert arc.bounds(0) == (0x1010, 0x1020)
    assert arc.bounds(1) == (0x1020, 0x1040)              # entry 2 aliases entry 1 -> skip it
    assert arc.bounds(3) == (0x1040, 0x1800)              # last -> the region end


def test_negative_entry_is_an_external_file_and_is_refused():
    arc = W.Id2Archive(0, 0x1000, 0x800, (16, -40244, 64), 0)
    with pytest.raises(W.SummonCameraError, match="EXTERNAL"):
        arc.bounds(1)


# ============================================================ (C) the read-out + the timeline
def test_keyframes_decode_pose_movement_and_focal():
    cam = W.parse_camera_block(camera_block([[ESTABLISH, MOVE, TAIL]]))
    ks = W.keyframes(cam)
    assert [k.local_frame for k in ks] == [1, 30, 60]
    assert ks[0].pose("campos")["distance"] == 0x1f
    assert ks[0].pose("tgtpos") is not None
    assert ks[0].focal() == {"duration": 7, "flags": 3, "distance": 300}
    assert ks[0].is_cut is True                            # no movement block -> a placement
    assert ks[1].movement("cammove") == {"duration": 24, "type": 2, "ease": "ease-out", "unknown": 0}
    assert ks[1].is_cut is False


def test_unnamed_movement_types_are_labelled_not_invented():
    """Corpus movement ``type`` takes 9 distinct values; only 0/1/2 have a battle-side name."""
    blk = camera_block([[code(5, 0x0002, CAMPOS + struct.pack("<HBB", 8, 10, 0))]])
    (k,) = W.keyframes(W.parse_camera_block(blk))
    assert k.movement("cammove")["ease"] == "type-10"


def test_shot_span_counts_the_trailing_move():
    cam = W.parse_camera_block(camera_block([[ESTABLISH, MOVE]]))
    assert W.shot_span(cam) == 30 + 24


def test_read_out_is_text_and_names_the_roundtrip_verdict():
    blob, _ = _one_camera_container()
    lines = W.read_out(blob, "synth")
    assert any("BYTE-EXACT" in ln for ln in lines)
    assert any("PLAY_CAMERA" in ln for ln in lines)
    assert any("THE PROJECTION DISTANCE" in ln for ln in lines)


class _Phase:
    def __init__(self, state, start_tick, ticks):
        self.state, self.start_tick, self.ticks = state, start_tick, ticks


class _Machine:
    def __init__(self, image, phases):
        self.image, self.phases = image, phases


def test_timeline_places_both_clocks_by_derivation():
    """Camera event = op tick + local frame - 1; phase boundary = the 0x80 op's tick + phase tick.
    Both come out of the SAME sequence walk, so the offset between them is fitted to nothing."""
    blob, _ = _one_camera_container()
    sm = _Machine("synth:c0", [_Phase(0, 0, 20), _Phase(1, 20, None)])
    tl = W.merged_timeline(blob, "synth", [sm])
    assert tl.program_starts[(0, 0)] == 15
    cams = {(r.seq_tick, r.what) for r in tl.cameras()}
    assert (10, "PLAY_CAMERA installs (%d B, 3 keyframes)" % 44) in cams or \
           any(t == 10 for t, _w in cams)                  # the install row sits at the op's tick
    assert any(r.seq_tick == 10 + 30 - 1 for r in tl.cameras())     # local f30 -> tick 39
    assert [(r.seq_tick, r.state) for r in tl.phases()] == [(15, 0), (35, 1)]


def test_h_changes_lists_only_real_transitions():
    blk = camera_block([[code(1, 0x0800, FOCAL),
                         code(10, 0x0800, FOCAL),        # the same H again -> not a change
                         code(20, 0x0800, FOCAL2)]])
    blob = synth([b"\x00" * 8, blk, b"\x00" * 8], [(W.OP_PLAY_CAMERA, 1, 0)])
    tl = W.merged_timeline(blob, "synth")
    assert [(r.seq_tick, r.h) for r in tl.h_changes()] == [(0, 300), (19, 400)]


def test_pairs_reports_the_signed_offset_between_the_two_clocks():
    blk = camera_block([[code(1, 0x0800, FOCAL)]])
    blob = synth([b"\x00" * 8, blk, b"\x00" * 8],
                 [(W.OP_WAIT, 0, 10), (W.OP_PLAY_CAMERA, 1, 0), (W.OP_WAIT, 0, 1),
                  (W.OP_RUN_PROGRAM, 0, 0)])
    sm = _Machine("synth:c0", [_Phase(0, 0, 5)])
    tl = W.merged_timeline(blob, "synth", [sm])
    (cam, phase, d), = tl.pairs(tl.h_changes())
    assert (cam.seq_tick, phase.seq_tick, d) == (10, 11, -1)          # the cut lands 1 tick EARLY


# ============================================================ provenance
def test_dump_refuses_to_write_inside_the_repo(tmp_path):
    with pytest.raises(W.SummonCameraError, match="refusing"):
        W.dump_shots([], os.path.join(W._REPO, "studies", "leak.csv"))
    out = tmp_path / "sub" / "ok.csv"
    assert W.dump_shots([{"effect": "synth", "shot": "A"}], str(out)) == 1
    assert out.is_file()


def test_dump_rows_carry_no_raw_bytes():
    blob, _ = _one_camera_container()
    rows = W.dump_rows(blob, "synth")
    assert rows and all(not isinstance(v, (bytes, bytearray)) for r in rows for v in r.values())


# ============================================================ corpus (skips without it)
@needs_corpus
def test_corpus_ef227_three_shots_460_bytes():
    with open(os.path.join(CORPUS, "ef227.bytes"), "rb") as fh:
        blob = fh.read()
    ex = W.extract_shots(blob, "ef227")
    assert [s.key for s in ex.shots] == [(0, 6), (1, 16), (1, 47)]
    assert sum(s.size for s in ex.shots) == 460                      # D4 sec 2.5.2's own figure
    assert all(s.roundtrip()[0] for s in ex.shots)


@needs_corpus
def test_corpus_ef227_two_clocks_pairs():
    """W1c from data+code only: the three H changes sit at -1, -1, 0 ticks from a phase boundary."""
    with open(os.path.join(CORPUS, "ef227.bytes"), "rb") as fh:
        blob = fh.read()
    tl = W.merged_timeline(blob, "ef227", W.recover_machines(blob, "ef227"))
    got = [(c.seq_tick, p.seq_tick, d) for c, p, d in tl.pairs(tl.h_changes(), window=6)]
    assert got == [(11, 12, -1), (106, 107, -1), (255, 255, 0)]


@needs_corpus
def test_corpus_ef251_needs_the_extra_sector_correction():
    import ef_container as EC
    with open(os.path.join(CORPUS, "ef251.bytes"), "rb") as fh:
        blob = fh.read()
    cont = EC.parse_header(blob)
    res = next(r for r in cont.chunks[0].resources if r.id == 2)
    assert res.extra_sectors == 5
    assert len(EC.parse_directory(blob, res.offset)) == 2              # the uncorrected read
    arc = W.id2_directory(blob, cont, 0)
    assert len(arc.entries) == 33 and arc.base == res.offset + 5 * W.SECTOR
    ex = W.extract_shots(blob, "ef251")
    assert len(ex.shots) == 3 and all(s.roundtrip()[0] for s in ex.shots)


@needs_corpus
def test_corpus_roundtrip_is_byte_exact_everywhere():
    rows = W.census(CORPUS)
    s = W.census_summary(rows)
    assert s["roundtrip_bad"] == []
    assert s["roundtrip_ok"] == s["shots"] > 0


@needs_corpus
def test_corpus_no_camera_block_is_the_last_subfile():
    """Why the round-trip is byte-exact and not merely structure-preserving: a camera's end is
    always a directory delta, so the trailing verbatim group absorbs the <=2 B alignment pad."""
    import ef_container as EC
    for path in W.corpus_paths(CORPUS):
        with open(path, "rb") as fh:
            blob = fh.read()
        cont = EC.parse_header(blob)
        ex = W.extract_shots(blob, os.path.basename(path))
        for s in ex.shots:
            arc = W.id2_directory(blob, cont, s.slot)
            lo = arc.entries[s.index]
            assert any(v > lo for v in arc.entries[s.index + 1:]), \
                "%s c%d idx%d is the last sub-file" % (path, s.slot, s.index)
