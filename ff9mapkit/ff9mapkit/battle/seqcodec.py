"""Lossless codec for the raw17 ``btlseq`` attack-SEQUENCE body -- parse -> model -> re-serialize, the
foundation the disassembler (``seqdis``) and the same-length patcher (``seqpatch``) read from. The raw17
opening-CAMERA block (``[camOffset:]``) is a SEPARATE, already-solved codec (``camera_codec``); this module
owns the choreography BODY (``[bodyStart, camOffset)``) the camera codec slices verbatim.

PROVEN against the engine source (``btlseq.cs``: ``ReadBattleSequence`` :32-68, the ``Sequencer`` interpreter
:177-243, the 34-entry ``gSeqProg[]`` delegate table :1223-1259, the ``AdvanceSeqCode`` operand-width table
:1165-1218, and every ``SeqExec*``/``SeqInit*`` handler) and a 562-file / 3814-sequence corpus sweep:
``serialize(parse(b)) == b`` byte-exact on 562/562 real donors (the raw16/camera-codec golden analog).

Format facts (all little-endian, all offsets absolute file positions):

* Header (8 fixed bytes + 3 variable tables): ``seqBlockOffset i16 @0`` (constant 4; read but unused -- kept
  verbatim), ``camOffset i16 @2`` (start of the camera block), ``seqCount i16 @4``, ``animCount i16 @6``,
  then ``seqOffset[seqCount] i16``, ``animList[animCount] i32``, ``seqBaseAnim[seqCount] u8``.
* ``bodyStart = 8 + 3*seqCount + 4*animCount`` (always even). Sequence body region = ``[bodyStart, camOffset)``.
* THE +4 SKEW: a ``seqOffset[i]`` value is the file position MINUS 4 -- sequence i's bytes start at
  ``seqOffset[i] + 4``. ``0`` is a "no sequence" sentinel (absent in the corpus, supported defensively).
* Each sequence is a flat opcode stream: ``[op u8][operands...]``, terminated by ``0x00`` End or ``0x18``
  FastEnd. Several ``seqOffset`` slots may ALIAS one body (a verbatim duplicate offset -- attacks that share
  choreography); bodies never partially overlap. Inter-body + trailing padding is NOT a derivable alignment
  rule (0/1-byte gaps that can land on odd boundaries; 5 scenes carry a 4-byte trailing pad) -> captured VERBATIM.
* The interpreter coerces ``op > 34`` to End, so an opcode byte of exactly ``34`` (0x22) indexes ``gSeqProg[34]``
  out of bounds -- a latent engine crash. Valid opcodes are 0..33; this codec rejects a body byte of 34.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field as _field


class SeqCodecError(ValueError):
    pass


# ----------------------------------------------------------------- the 34-opcode table (gSeqProg[] @1223-1259)
# Each entry: name, [ (operand_name, rel_offset_from_opcode, width, signed, kind) ... ]. The instruction TOTAL
# size = 1 + sum(widths) (every byte is covered, incl. the 0x19 discarded-but-present pad). ``kind`` drives the
# disassembler rendering + the patch-site taxonomy. Widths/signedness transcribed from each SeqExec*/SeqInit*
# handler's Read* calls AND cross-checked against the AdvanceSeqCode skip table (skip+1 == size for all 34).
_OPS = {
    0x00: ("End", []),
    0x01: ("Wait", [("frames", 1, 1, False, "frames")]),
    0x02: ("Calc", []),
    0x03: ("MoveToTarget", [("frames", 1, 1, False, "frames"), ("distance", 2, 2, True, "distance")]),
    0x04: ("MoveToTurn", [("frames", 1, 1, False, "frames")]),
    0x05: ("Anim", [("anim_code", 1, 1, False, "anim_code")]),
    0x06: ("SVfx", [("svfx_no", 1, 2, False, "svfx"), ("param", 3, 1, False, "param"),
                    ("time", 4, 1, False, "frames")]),
    0x07: ("WaitAnim", []),
    0x08: ("Vfx", [("fx_no", 1, 2, False, "vfx"), ("a0", 3, 2, True, "coord"),
                   ("a1", 5, 2, True, "coord"), ("a2", 7, 2, True, "coord")]),
    0x09: ("WaitLoadVfx", []),
    0x0A: ("StartVfx", []),
    0x0B: ("WaitVfx", []),
    0x0C: ("Scale", [("factor", 1, 2, True, "scale"), ("frames", 3, 1, False, "frames")]),
    0x0D: ("MeshHide", [("mask", 1, 2, False, "mesh_mask")]),
    0x0E: ("Message", [("mess_id", 1, 1, False, "message")]),
    0x0F: ("MeshShow", [("mask", 1, 2, False, "mesh_mask")]),
    0x10: ("SetCamera", [("cam", 1, 1, False, "camera")]),
    0x11: ("DefaultIdle", [("on_off", 1, 1, False, "flag")]),
    0x12: ("RunCamera", [("cam", 1, 1, False, "camera")]),   # cam read inside a predicate; layout stable
    0x13: ("MoveToPoint", [("frames", 1, 1, False, "frames"), ("x", 2, 2, True, "coord"),
                           ("y", 4, 2, True, "coord"), ("z", 6, 2, True, "coord")]),
    0x14: ("Turn", [("dir", 1, 2, True, "dir"), ("add", 3, 2, True, "angle"), ("time", 5, 1, False, "frames")]),
    0x15: ("TexAnimPlay", [("tex", 1, 1, False, "tex")]),
    0x16: ("TexAnimOnce", [("tex", 1, 1, False, "tex")]),
    0x17: ("TexAnimStop", [("tex", 1, 1, False, "tex")]),
    0x18: ("FastEnd", []),
    0x19: ("Sfx", [("sfx_no", 1, 2, False, "sfx"), ("time", 3, 1, False, "frames"),
                   ("_pad", 4, 1, False, "pad"), ("vol", 5, 1, False, "param")]),  # +4 is a discarded HOLE
    0x1A: ("VfxContact", [("fx_no", 1, 2, False, "vfx"), ("a0", 3, 2, True, "coord"),
                          ("a1", 5, 2, True, "coord"), ("a2", 7, 2, True, "coord")]),
    0x1B: ("MoveToOffset", [("frames", 1, 1, False, "frames"), ("dx", 2, 2, True, "coord"),
                            ("dy", 4, 2, True, "coord"), ("dz", 6, 2, True, "coord")]),
    0x1C: ("TargetBone", [("bone", 1, 1, False, "bone")]),
    0x1D: ("FadeOut", [("frames", 1, 1, False, "fade")]),
    0x1E: ("MoveToTargetZ", [("frames", 1, 1, False, "frames"), ("distance", 2, 2, True, "distance")]),
    0x1F: ("Shadow", [("on_off", 1, 1, False, "flag")]),
    0x20: ("RunCameraForced", [("cam", 1, 1, False, "camera")]),
    0x21: ("MessageTitle", [("mess_id", 1, 1, False, "message")]),
}
TERMINATORS = (0x00, 0x18)
MAX_OPCODE = 0x21                                   # 33; a body byte of 34 is the latent gSeqProg[34] crash


def _size(op: int) -> int:
    fields = _OPS[op][1]
    return 1 + sum(w for _n, _o, w, _s, _k in fields)


SIZE = {op: _size(op) for op in _OPS}               # opcode -> total instruction size (incl. opcode byte)
OP_NAME = {op: nm for op, (nm, _f) in _OPS.items()}


# ----------------------------------------------------------------- the in-memory model
@dataclass
class Instr:
    op: int
    offset: int                # absolute file offset of the opcode byte (in the source raw17)
    operands: list             # decoded ints, parallel to _OPS[op][1] field descriptors

    @property
    def name(self) -> str:
        return OP_NAME[self.op]

    @property
    def fields(self):
        return _OPS[self.op][1]


@dataclass
class Body:
    offset: int                # the seqOffset VALUE (file-pos - 4); absolute start = offset + 4
    gap_before: bytes          # alignment padding immediately before this body (verbatim)
    instrs: list               # [Instr]


@dataclass
class Raw17:
    seq_block_offset: int
    cam_offset: int
    seq_count: int
    anim_count: int
    seq_offset: list           # [int] per sub_no (the seqOffset table; 0 = sentinel)
    anim_list: list            # [int] global anim ids (i32)
    seq_base_anim: list        # [int] per sub_no
    bodies: list               # [Body] in file (ascending-abs-start) order, distinct offsets only
    final_pad: bytes           # padding between the last body end and cam_offset (verbatim)
    camera_block: bytes        # raw17[cam_offset:] verbatim (the separate camera codec owns it)
    seq_block_raw: bytes = _field(default=b"", repr=False)   # original header tables region (unused; reserved)

    @property
    def body_start(self) -> int:
        return 8 + 3 * self.seq_count + 4 * self.anim_count

    def body_for(self, sub_no: int):
        """The Body a sub_no's seqOffset points at (None for the 0 sentinel / out of range)."""
        if not 0 <= sub_no < self.seq_count:
            return None
        off = self.seq_offset[sub_no]
        if off == 0:
            return None
        for b in self.bodies:
            if b.offset == off:
                return b
        return None


# ----------------------------------------------------------------- parse
def _decode_instr(raw: bytes, pos: int) -> Instr:
    op = raw[pos]
    if op > MAX_OPCODE:
        raise SeqCodecError(f"opcode {op} (0x{op:02x}) at offset {pos} is out of range 0..{MAX_OPCODE} "
                            f"(34 would crash the engine's gSeqProg[34] index)")
    operands = []
    for _name, rel, w, signed, _kind in _OPS[op][1]:
        operands.append(int.from_bytes(raw[pos + rel:pos + rel + w], "little", signed=signed))
    return Instr(op, pos, operands)


def _decode_body(raw: bytes, abs_start: int, limit: int) -> tuple:
    """Decode one sequence from ``abs_start`` to its terminator. ``limit`` (== cam_offset) bounds the walk.
    Returns (instrs, end_pos)."""
    pos = abs_start
    instrs = []
    guard = 0
    while pos < limit:
        guard += 1
        if guard > 100000:
            raise SeqCodecError(f"sequence at {abs_start} runs away (no terminator before offset {limit})")
        ins = _decode_instr(raw, pos)
        sz = SIZE[ins.op]
        if pos + sz > limit:
            raise SeqCodecError(f"instruction {ins.name} at {pos} overruns the body region (end {pos + sz} "
                                f"> camOffset {limit})")
        instrs.append(ins)
        pos += sz
        if ins.op in TERMINATORS:
            return instrs, pos
    raise SeqCodecError(f"sequence at {abs_start} reached camOffset {limit} with no terminator")


def parse(raw17: bytes) -> Raw17:
    """Parse a raw17 into a lossless :class:`Raw17` model (header + per-body decoded instructions + the verbatim
    camera block). ``serialize(parse(b)) == b`` byte-exact for valid donors."""
    if len(raw17) < 8:
        raise SeqCodecError(f"raw17 too short ({len(raw17)} bytes)")
    seq_block_offset, cam_offset, seq_count, anim_count = struct.unpack_from("<hhhh", raw17, 0)
    if seq_count < 0 or anim_count < 0:
        raise SeqCodecError(f"bad header (seqCount={seq_count}, animCount={anim_count})")
    if not 0 < cam_offset <= len(raw17):
        raise SeqCodecError(f"bad camOffset {cam_offset} (file {len(raw17)} bytes)")
    table_end = 8 + 2 * seq_count + 4 * anim_count + seq_count   # seqOffset[] + animList[] + seqBaseAnim[]
    if table_end > len(raw17):                                   # bound BEFORE the unpacks so a malformed header
        raise SeqCodecError(f"header tables (end {table_end}) run past EOF (file {len(raw17)} bytes) -- "
                            f"seqCount={seq_count}, animCount={anim_count}")   # raises cleanly, never a struct.error
    off = 8
    seq_offset = list(struct.unpack_from(f"<{seq_count}h", raw17, off)); off += 2 * seq_count
    anim_list = list(struct.unpack_from(f"<{anim_count}i", raw17, off)); off += 4 * anim_count
    seq_base_anim = list(raw17[off:off + seq_count]); off += seq_count
    body_start = off
    if body_start != 8 + 3 * seq_count + 4 * anim_count:
        raise SeqCodecError("header table region length mismatch (internal)")
    if body_start > cam_offset:
        raise SeqCodecError(f"header tables (end {body_start}) overrun camOffset {cam_offset}")

    # distinct, nonzero offsets, decoded once in ascending abs-start order (aliases share a body)
    distinct = sorted(set(o for o in seq_offset if o != 0))
    bodies = []
    prev_end = body_start
    for o in distinct:
        abs_start = o + 4
        if abs_start < body_start or abs_start >= cam_offset:
            raise SeqCodecError(f"seqOffset {o} (abs {abs_start}) outside the body region "
                                f"[{body_start}, {cam_offset})")
        gap = bytes(raw17[prev_end:abs_start])
        instrs, end = _decode_body(raw17, abs_start, cam_offset)
        bodies.append(Body(o, gap, instrs))
        prev_end = max(prev_end, end)
    final_pad = bytes(raw17[prev_end:cam_offset])
    return Raw17(seq_block_offset, cam_offset, seq_count, anim_count, seq_offset, anim_list,
                 seq_base_anim, bodies, final_pad, bytes(raw17[cam_offset:]))


# ----------------------------------------------------------------- serialize
def emit_instr(ins: Instr) -> bytes:
    """One instruction's bytes (opcode + operands), byte-exact (covers the 0x19 discarded-pad byte)."""
    buf = bytearray(SIZE[ins.op])
    buf[0] = ins.op
    for (_name, rel, w, signed, _kind), val in zip(_OPS[ins.op][1], ins.operands):
        buf[rel:rel + w] = int(val).to_bytes(w, "little", signed=signed)
    return bytes(buf)


def serialize(model: Raw17) -> bytes:
    """Re-serialize the model. GOLDEN PATH (no body length change): header + tables verbatim + each body's
    captured gap_before + its instruction bytes + final_pad + the verbatim camera block == the original file."""
    out = bytearray()
    out += struct.pack("<hhhh", model.seq_block_offset, model.cam_offset, model.seq_count, model.anim_count)
    out += struct.pack(f"<{model.seq_count}h", *model.seq_offset)
    out += struct.pack(f"<{model.anim_count}i", *model.anim_list)
    out += bytes(model.seq_base_anim)
    if len(out) != model.body_start:
        raise SeqCodecError("serialized header length mismatch (internal)")
    for b in model.bodies:
        out += b.gap_before
        for ins in b.instrs:
            out += emit_instr(ins)
    out += model.final_pad
    out += model.camera_block
    return bytes(out)
