r"""``summons.camera`` -- the summon-camera extractor, the codec adapter and the merged timeline.

EVERY test here runs UNCONDITIONALLY: no FF9 install, no extracted corpus, no stock bytes. Each one
SYNTHESISES its own container (header + sequence stream + id-2 archive + camera blocks) with the
builders below, so the extractor, the clock arithmetic, the id-2 extra-sector correction and every
refusal are exercised on bytes this file wrote. That is the same posture the study's own
``test_summon_camera.py`` takes, minus its corpus half -- a kit test that needs a 372-file local
corpus is a kit test that silently skips, and a silent skip is how a black screen once reached a
playtest.

The field values below (``CAMPOS``/``TGTPOS``/``FOCAL``/...) are AUTHORED, not copied: they are the
same literals W1e swept the whole stock corpus for and found nowhere in it. They demonstrate the
grammar without carrying data.
"""
from __future__ import annotations

import struct

import pytest

from ff9mapkit.battle import camera_codec as CC
from ff9mapkit.summons import camera as W
from ff9mapkit.summons import container as C


# ============================================================ synthetic containers
def code(frame, flags, block=b""):
    return struct.pack("<HH", frame, flags) + block


def camera_block(sequences, selector=b"\x01\x00\x00\x00", anchors=None, extra_flag_bits=0):
    """Assemble a real-grammar SFX camera block: Flags + one u16 offset per present group + blocks.

    Mirrors the native parser the battle codec already implements: the first offset entry is the
    table's own end and the groups follow in canonical order.
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


CAMPOS = b"\x2a\x40\x33\x0d\x11\x1f"        # code, flags, pitch, orientation, roll, distance
TGTPOS = b"\x2a\x40\x07\x03\x01\x02"
FOCAL = b"\x07\x03\x2c\x01"                  # duration 7, flags 3, H = 300
FOCAL2 = b"\x07\x03\x90\x01"                 # ...        H = 400
MARKER = b"\x11\x22\x33\x44"

ESTABLISH = code(1, 0x0809, CAMPOS + TGTPOS + FOCAL)
MOVE = code(30, 0x0002, b"\x2a\x40\x30\x0c\x10\x1e" + struct.pack("<HBB", 24, 2, 0))
TAIL = code(60, 0x8000, MARKER)


def _one_camera_container(**kw):
    blk = camera_block([[ESTABLISH, MOVE, TAIL]])
    subs = [b"\x00" * 8, b"\x00" * 8, blk, b"\x00" * 8]
    ops = [(W.OP_LOAD_CHUNK, 0, 0), (W.OP_WAIT, 0, 10), (W.OP_PLAY_CAMERA, 2, 0),
           (W.OP_WAIT, 0, 5), (W.OP_RUN_PROGRAM, 0, 0)]
    return synth(subs, ops, **kw), blk


class _Phase:
    def __init__(self, state, start_tick, ticks):
        self.state, self.start_tick, self.ticks = state, start_tick, ticks


class _Machine:
    def __init__(self, image, phases):
        self.image, self.phases = image, phases


# ============================================================ (0) THE PUBLIC CODEC ALIASES
# The promotion published ``camera_codec``'s three per-camera functions. Before it, this module would
# have had to reach into another package's PRIVATES -- a coupling nobody can see when they change the
# private. These tests pin that the alias IS the function (not a copy that can drift) and that the
# round-trip it implements is the one this lane depends on.
def test_the_public_codec_aliases_are_the_same_functions_not_copies():
    assert CC.parse_camera is CC._parse_camera
    assert CC.serialize_camera is CC._serialize_camera
    assert CC.split_code is CC._split_code
    for name in ("parse_camera", "serialize_camera", "split_code"):
        assert name in CC.__all__, name


def test_the_public_aliases_round_trip_a_synthetic_camera_block():
    blk = camera_block([[ESTABLISH, MOVE, TAIL]])
    cam = CC.parse_camera(blk, 0, len(blk))
    assert CC.serialize_camera(cam) == blk
    # split_code slices the Code's payload the way this lane then SPLICES it
    c = cam["sequences"][0][0]
    fields = CC.split_code(c["flags"], c["block"])
    assert fields["campos"] == CAMPOS and fields["tgtpos"] == TGTPOS and fields["focal"] == FOCAL


def test_the_underscored_names_still_work_so_battle_call_sites_are_unbroken():
    """Publishing was a RENAME, not a move: nothing that already called the private may break."""
    blk = camera_block([[ESTABLISH, TAIL]])
    assert CC._serialize_camera(CC._parse_camera(blk, 0, len(blk))) == blk


# ============================================================ (1) the frame word
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


# ============================================================ (2) the codec adapter
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
    with pytest.raises(W.SummonCameraError, match="too short"):
        W.parse_camera_block(b"\x09\x00")


def test_outer_groups_names_every_present_group():
    assert W.outer_groups(0x09) == ["sequence0", "selector"]
    assert W.outer_groups(0x0F) == ["sequence0", "sequence1", "sequence2", "selector"]
    assert W.outer_groups(0xC9)[-1] == "anchors x2"


# ============================================================ (3) the extractor
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


def test_a_blocking_wait_is_counted_not_summed():
    """``WAIT arg1 != 0`` blocks on a channel flag -- a duration nothing static supplies. Summing its
    arg2 would add a channel INDEX to a tick count."""
    blk = camera_block([[ESTABLISH, TAIL]])
    blob = synth([b"\x00" * 8, blk], [(W.OP_WAIT, 0, 4), (W.OP_WAIT, 1, 9),
                                      (W.OP_PLAY_CAMERA, 1, 0)])
    w = W.walk_camera_ops(blob)
    assert w.total_ticks == 4 and w.blocking_waits == 1
    assert w.ops[0].seq_tick == 4                            # NOT 13


def test_setup_camera_resolves_a_block_too():
    """0x23 reaches roughly nine tenths of the statically-resolvable camera blocks -- a 0x29-only
    walk sees about a tenth of the camera data that is there."""
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
    """arg2 != 0 picks the shot at RUNTIME (last-used / LCG-random / table lookup). Offline decoding
    cannot name it, and inventing one would be a silent lie in the read-out."""
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


def test_a_subfile_that_is_not_a_camera_block_is_skipped_with_a_reason():
    """An index that resolves to real bytes which are not a camera is a SKIP with a named reason --
    never a crash, and never a shot the caller then edits."""
    blob = synth([b"\x00" * 8, b"\xff" * 4, b"\x00" * 8], [(W.OP_PLAY_CAMERA, 1, 0)])
    ex = W.extract_shots(blob, "synth")
    assert not ex.shots and "did not parse" in ex.skipped[0][1]


# ---- THE ID-2 EXTRA-SECTOR CORRECTION
def test_extra_sectors_move_the_directory_base():
    """The stock container that carries ``extra_sectors != 0`` is unreadable without this."""
    blob, blk = _one_camera_container(extra_sectors=1)
    cont = C.parse_header(blob)
    arc = W.id2_directory(blob, cont, 0)
    res = cont.chunks[0].resources[0]
    assert res.extra_sectors == 1
    assert arc.base == res.offset + W.SECTOR              # NOT res.offset
    assert arc.base + arc.size == len(blob)               # the region ends exactly where it should
    ex = W.extract_shots(blob, "synth")
    assert len(ex.shots) == 1 and ex.shots[0].block == blk


def test_without_the_correction_the_index_reads_garbage():
    """Guard the correction from a silent regression: parsing at ``res.offset`` yields a DIFFERENT
    directory -- a plausible short table with wrong data, not an error."""
    blob, _blk = _one_camera_container(extra_sectors=1)
    cont = C.parse_header(blob)
    res = cont.chunks[0].resources[0]
    naive = C.parse_directory(blob, res.offset)           # the uncorrected read
    good = W.id2_directory(blob, cont, 0).entries
    assert list(naive) != list(good)


def test_a_chunk_with_no_id2_resource_is_none_not_an_error():
    header = struct.pack("<h", 1) + struct.pack("<hh", 0, 1) + struct.pack("<bbh", 4, 0, 1)
    blob = header + b"\x00" * (0x1000 - len(header))
    cont = C.parse_header(blob)
    assert W.id2_directory(blob, cont, 0) is None         # id-4 only
    assert W.id2_directory(blob, cont, 9) is None         # slot out of range


def test_an_unreadable_directory_is_refused_not_guessed():
    """A directory base past the end of the blob is a REFUSAL. Returning an empty/partial table there
    would let the extractor report "no shots" for a container it simply failed to read."""
    blob, _ = _one_camera_container()
    cont = C.parse_header(blob)
    bad = C.Container(size=cont.size, chunks=[C.Chunk(slot=0, chunk_index=0, resources=[
        C.Resource(index=0, id=2, info=0, size_sectors=1, offset=len(blob) + 0x800, nbytes=0x800)])],
        table_end=cont.table_end, cursor_end=cont.cursor_end)
    with pytest.raises(W.SummonCameraError, match="unreadable"):
        W.id2_directory(blob, bad, 0)


# ---- sub-file bounds
def test_bounds_uses_the_next_strictly_greater_entry():
    arc = W.Id2Archive(0, 0x1000, 0x800, (16, 32, 32, 64), 0)
    assert arc.bounds(0) == (0x1010, 0x1020)
    assert arc.bounds(1) == (0x1020, 0x1040)              # entry 2 aliases entry 1 -> skip it
    assert arc.bounds(3) == (0x1040, 0x1800)              # last -> the region end


def test_an_out_of_range_subfile_index_is_refused():
    arc = W.Id2Archive(0, 0x1000, 0x800, (16, 32), 0)
    with pytest.raises(W.SummonCameraError, match="out of range"):
        arc.bounds(7)


def test_negative_entry_is_an_external_file_and_is_refused():
    """``parse_directory`` returns a negative entry VERBATIM -- refusing it is this layer's job, and
    it is done rather than clamped, because the bytes it points at are not in this region at all."""
    arc = W.Id2Archive(0, 0x1000, 0x800, (16, -40244, 64), 0)
    with pytest.raises(W.SummonCameraError, match="EXTERNAL"):
        arc.bounds(1)


# ============================================================ (4) the read-out + the timeline
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
    """Corpus movement ``type`` takes nine distinct values; only 0/1/2 have a battle-side name."""
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


def test_timeline_places_both_clocks_by_derivation():
    """Camera event = op tick + local frame - 1; phase boundary = the 0x80 op's tick + phase tick.
    Both come out of the SAME sequence walk, so the offset between them is fitted to nothing."""
    blob, blk = _one_camera_container()
    sm = _Machine("synth:c0", [_Phase(0, 0, 20), _Phase(1, 20, None)])
    tl = W.merged_timeline(blob, "synth", [sm])
    assert tl.program_starts[(0, 0)] == 15
    installs = [r for r in tl.cameras() if "installs" in r.what]
    assert installs and installs[0].seq_tick == 10
    assert "%d B, 3 keyframes" % len(blk) in installs[0].what
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


def test_an_identical_alternate_track_is_reported_once():
    blk = camera_block([[ESTABLISH, TAIL]] * 3, selector=b"\x02\x00\x00\x00")
    blob = synth([b"\x00" * 8, blk, b"\x00" * 8], [(W.OP_PLAY_CAMERA, 1, 0)])
    tl = W.merged_timeline(blob, "synth")
    assert not any("[alt seq" in r.who for r in tl.cameras())


def test_a_differing_alternate_track_is_labelled_as_one():
    other = [code(1, 0x0809, CAMPOS + TGTPOS + FOCAL2), TAIL]
    blk = camera_block([[ESTABLISH, TAIL], other, list(other)], selector=b"\x02\x00\x00\x00")
    blob = synth([b"\x00" * 8, blk, b"\x00" * 8], [(W.OP_PLAY_CAMERA, 1, 0)])
    tl = W.merged_timeline(blob, "synth")
    assert any("[alt seq1]" in r.who for r in tl.cameras())


# ============================================================ (5) THE KIT'S REDUCED READ-OUT
# The kit ships no MIPS disassembler, so it recovers no program state machines and ``machines``
# defaults to none. That must be a REDUCED read-out, not a wrong one -- every camera row identical,
# only the phase spine absent. These tests are the promotion's own, with no study counterpart.
def test_with_no_machines_the_camera_column_is_byte_for_byte_the_same():
    blob, _ = _one_camera_container()
    sm = _Machine("synth:c0", [_Phase(0, 0, 20), _Phase(1, 20, None)])
    with_m = W.merged_timeline(blob, "synth", [sm])
    without = W.merged_timeline(blob, "synth")
    assert [(r.seq_tick, r.who, r.what, r.h) for r in without.cameras()] == \
           [(r.seq_tick, r.who, r.what, r.h) for r in with_m.cameras()]
    assert without.phases() == [] and with_m.phases()
    assert without.machines == ()


def test_pairs_is_empty_rather_than_faking_a_neighbour_when_no_phases_exist():
    blob, _ = _one_camera_container()
    tl = W.merged_timeline(blob, "synth")
    assert tl.pairs() == [] and tl.pairs(tl.h_changes()) == []


def test_timeline_lines_print_the_camera_column_alone_without_empty_phase_headers():
    blob, _ = _one_camera_container()
    text = "\n".join(W.timeline_lines(W.merged_timeline(blob, "synth")))
    assert "camera shots on ONE clock" in text
    assert "and program phases" not in text
    assert "THE TWO CLOCKS" not in text                   # no header for a comparison nobody made


def test_read_out_takes_machines_for_signature_parity_and_is_unchanged_by_them():
    blob, _ = _one_camera_container()
    sm = _Machine("synth:c0", [_Phase(0, 0, 20)])
    assert W.read_out(blob, "synth", [sm]) == W.read_out(blob, "synth")


# ============================================================ promotion follow-ups (orchestrator)
def test_a_too_short_camera_sub_file_is_a_named_skip_not_a_crash():
    """A <4-byte block cannot hold Flags + one offset, so ``parse_camera_block`` raises
    SummonCameraError -- and ``extract_shots`` must catch it into ``Extract.skipped`` like every
    other unresolvable case.  The promotion found the study version let exactly this one escape and
    crash the whole read (A3's finding; the fix is SummonCameraError in the except tuple)."""
    subs = [b"\x00" * 8, b"\xAB\xCD", b"\x00" * 8]
    ops = [(W.OP_LOAD_CHUNK, 0, 0), (W.OP_PLAY_CAMERA, 1, 0)]
    ex = W.extract_shots(synth(subs, ops), "synth")
    assert not ex.shots
    assert len(ex.skipped) == 1
    assert "too short" in ex.skipped[0][1]


def test_the_read_sub_verb_prints_the_read_out_offline_and_needs_ef(tmp_path, capsys):
    """``summon-rescore read`` is W1's READ-OUT productized -- the reference every scaffolded spec
    points at.  Offline via --from; refuses without --ef (exit 2, a usage refusal)."""
    from ff9mapkit import cli
    blob, _ = _one_camera_container()
    ef = tmp_path / "ef999"
    ef.write_bytes(blob)
    rc = cli.main(["summon-rescore", "read", "--ef", "999", "--from", str(ef)])
    out = capsys.readouterr()
    assert rc == 0
    assert "shot A" in out.out
    rc = cli.main(["summon-rescore", "read", "--from", str(ef)])
    err = capsys.readouterr()
    assert rc == 2 and "--ef" in err.err
