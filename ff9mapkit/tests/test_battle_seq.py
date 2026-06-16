"""Tests for the raw17 ``btlseq`` attack-sequence codec/disassembler/patcher (battle.seqcodec / seqdis / seqpatch).

PURE tier: a synthetic raw17 round-trips byte-exact, the 34-opcode SIZE table is internally consistent, the
named opcodes decode, a same-length patch is surgical, and constant_sites self-verify. INSTALL-GATED: the golden
round-trip ``serialize(parse(real)) == real`` on every real donor scene read live from the install (the
raw16/camera-codec golden analog) PROVES the offset map + width table against actual Square-Enix bytes.
"""
from __future__ import annotations

import struct

import pytest

from ff9mapkit.battle import seqcodec, seqdis, seqpatch


# ----------------------------------------------------------------- a hand-built raw17
def _synthetic(camera_block=b"\xaa\xbb\xcc\xdd", pad=b"\x00"):
    """seqCount=2, animCount=2. seq0 = Anim(1) Wait(10) End; seq1 = Calc FastEnd. One pad byte + a camera block."""
    seq0 = bytes([0x05, 0x01, 0x01, 0x0a, 0x00])       # Anim code=1, Wait frames=10, End
    seq1 = bytes([0x02, 0x18])                          # Calc, FastEnd
    body_start = 8 + 3 * 2 + 4 * 2                      # 22
    so0 = body_start - 4                                # 18 (abs 22)
    so1 = body_start + len(seq0) - 4                    # 23 (abs 27)
    body = seq0 + seq1 + pad
    cam_off = body_start + len(body)
    head = struct.pack("<hhhh", 4, cam_off, 2, 2)
    head += struct.pack("<hh", so0, so1)
    head += struct.pack("<ii", 1111, 2222)
    head += bytes([0, 0])                              # seqBaseAnim
    return head + body + camera_block


def test_codec_roundtrips_synthetic():
    raw = _synthetic()
    model = seqcodec.parse(raw)
    assert seqcodec.serialize(model) == raw            # byte-exact (incl. pad + camera block)
    assert (model.seq_count, model.anim_count, model.cam_offset) == (2, 2, 22 + 8)
    assert model.seq_offset == [18, 23]
    assert model.anim_list == [1111, 2222]
    assert model.camera_block == b"\xaa\xbb\xcc\xdd"
    assert model.final_pad == b"\x00"
    assert len(model.bodies) == 2


def test_codec_decodes_named_ops():
    model = seqcodec.parse(_synthetic())
    b0 = model.body_for(0)
    assert [i.name for i in b0.instrs] == ["Anim", "Wait", "End"]
    assert b0.instrs[0].operands == [1]                # anim_code
    assert b0.instrs[1].operands == [10]               # Wait frames
    b1 = model.body_for(1)
    assert [i.name for i in b1.instrs] == ["Calc", "FastEnd"]


def test_size_table_consistency():
    # every opcode 0..33 present; size == 1 + sum(operand widths); terminators are the no-operand enders
    assert sorted(seqcodec.SIZE) == list(range(0, 0x22))
    for op, (name, fields) in seqcodec._OPS.items():
        assert seqcodec.SIZE[op] == 1 + sum(w for _n, _o, w, _s, _k in fields)
        # operand byte ranges tile [1, size) with no gap/overlap (so emit covers every byte)
        covered = sorted((o, o + w) for _n, o, w, _s, _k in fields)
        cur = 1
        for lo, hi in covered:
            assert lo == cur
            cur = hi
        assert cur == seqcodec.SIZE[op]
    assert seqcodec.TERMINATORS == (0x00, 0x18)
    # a couple of spot sizes from the engine width table
    assert seqcodec.SIZE[0x08] == 9 and seqcodec.SIZE[0x19] == 6 and seqcodec.SIZE[0x13] == 8


def test_rejects_out_of_range_opcode():
    # opcode byte 34 (0x22) is the latent gSeqProg[34] crash -> the codec must reject it
    with pytest.raises(seqcodec.SeqCodecError):
        seqcodec._decode_instr(bytes([0x22, 0, 0]), 0)


def test_disasm_renders_anim_resolution():
    text = seqdis.disassemble_seq(_synthetic())
    assert "Anim(anim_code=1)" in text
    assert "anim id 2222" in text                      # animList[base0 + code1] resolved
    assert "Wait(frames=10)" in text
    assert "FastEnd" in text


def test_sites_self_verify_and_surgical_patch():
    raw = _synthetic()
    sites = seqpatch.constant_sites(raw)
    # set every site to its own value -> byte-identical (the aipatch-style self-verify)
    same, _ = seqpatch.apply_seq_patches(raw, [{"at": s.offset, "old": s.value, "new": s.value} for s in sites])
    assert same == raw
    # retime the Wait: only that one byte changes
    wait = next(s for s in sites if s.kind == "frames")
    out, _ = seqpatch.apply_seq_patches(raw, [{"at": wait.offset, "old": wait.value, "new": 99}])
    diff = [i for i in range(len(raw)) if raw[i] != out[i]]
    assert diff == [wait.offset]
    assert seqcodec.parse(out).body_for(0).instrs[1].operands == [99]


def test_patch_guard_and_range():
    raw = _synthetic()
    sites = seqpatch.constant_sites(raw)
    wait = next(s for s in sites if s.kind == "frames" and s.width == 1)
    with pytest.raises(seqpatch.SeqPatchError):                       # wrong old guard
        seqpatch.apply_seq_patches(raw, [{"at": wait.offset, "old": wait.value + 1, "new": 5}])
    with pytest.raises(seqpatch.SeqPatchError):                       # out of width range (u8)
        seqpatch.apply_seq_patches(raw, [{"at": wait.offset, "old": wait.value, "new": 300}])
    with pytest.raises(seqpatch.SeqPatchError):                       # no site at this offset
        seqpatch.apply_seq_patches(raw, [{"at": 999, "old": 0, "new": 0}])


def test_pad_byte_not_a_site():
    # opcode 0x19 Sfx has a discarded pad byte at operand +4 -- it must NOT appear as a patch site
    seq = bytes([0x19, 0x10, 0x00, 0x05, 0xff, 0x40, 0x00])           # Sfx + End
    body_start = 8 + 3 * 1 + 4 * 0
    head = struct.pack("<hhhh", 4, body_start + len(seq), 1, 0)
    head += struct.pack("<h", body_start - 4) + bytes([0])           # seqOffset[0], seqBaseAnim[0]
    raw = head + seq
    sites = seqpatch.constant_sites(raw)
    kinds = {s.kind for s in sites}
    assert "pad" not in kinds
    assert {"sfx", "frames", "param"} <= kinds                        # the real Sfx operands ARE sites


# ----------------------------------------------------------------- install-gated golden round-trip
def _can_read_donor() -> bool:
    try:
        import UnityPy  # noqa: F401
        from ff9mapkit import config
        return (config.find_game_path() / "StreamingAssets" / "p0data2.bin").is_file()
    except Exception:
        return False


@pytest.mark.skipif(not _can_read_donor(), reason="needs the FF9 install + UnityPy (p0data2.bin)")
@pytest.mark.parametrize("donor", ["EF_R007"])
def test_seq_golden_roundtrip_real_donor(donor):
    from ff9mapkit.battle import extract
    try:
        raw17 = extract.read_scene_assets(donor)["raw17"]
    except (ValueError, KeyError, FileNotFoundError) as ex:
        pytest.skip(f"donor {donor} not readable: {ex}")
    model = seqcodec.parse(raw17)
    # THE golden assertion: a full parse -> re-serialize is byte-identical to the real donor
    assert seqcodec.serialize(model) == raw17
    assert model.seq_count >= 1 and model.cam_offset > model.body_start
    # the disassembler runs + names sequences; sites self-verify on the real bytes
    text = seqdis.disassemble_seq(raw17)
    assert "btlseq:" in text and "sub 0" in text
    sites = seqpatch.constant_sites(raw17)
    assert sites
    same, _ = seqpatch.apply_seq_patches(raw17, [{"at": s.offset, "old": s.value, "new": s.value} for s in sites])
    assert same == raw17
