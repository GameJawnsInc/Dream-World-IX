"""ef_container -- a NATIVE-GROUNDED parser for FF9's ``ef###.bytes`` special-effect container.

Committable: pure format-parser code. It reads a caller-supplied blob (extracted from the user's own
install) and emits offsets/ids/opcodes. It NEVER writes game bytes anywhere.

Provenance of every rule below is the disassembly of the user's own installed
``FF9SpecialEffectPlugin.dll`` (x64, ImageBase 0x180000000), not the (dead, unvalidated) managed
``SFXBinaryFile.cs``. Divergences from that C# draft are called out in ``M2-container-format.md``.

THE NATIVE CHAIN (fn@rva):
  SFX_Play export @0x1e50 -> body @0x2880: memcpy(staticBlob@0x3678f0, bin, size); effnum -> 0x3678e8.
  0x490d0: copies blob[0x000..0x800] (sector 0 = the HEADER SECTOR) to 0x3208d0, then calls 0xd740.
  0xd740 -> 0xd390 = THE RESOURCE-TABLE WALKER (the authority for ``parse_header`` below).
  0x3de37 = the sector-feed state machine; its state-5 handler dispatches on the resource ID byte
    through the 10-entry jump table @0x3ed54 (the authority for ``RESOURCE_IDS``).
  0x31d31 @0x31edb: seqPtr(0x323198) = 0x320cd0 = headerSector+0x400 -> the SEQUENCE STREAM lives at
    file offset 0x400 (inside sector 0).
  0x315f1 = THE SEQUENCE INTERPRETER: reads (code,arg1,arg2) bytes, advances +3, dispatches:
      code <  0x20 : jump table @0x31f58, indices 0x00..0x14 (0x10..0x13 -> _wassert = INVALID)
      code in 0x15..0x1F : _wassert (INVALID)
      code >= 0x20 : 0x48b10(code>=0x80 ? code : code-0x20, curChunkSlot, arg1, arg2)
  0x48b10 picks the handler: >=0x80 -> 0x49170 (sub-index = code-0x80);
      rebased <0x30 -> qword table @0x4aff0 (VALID only for rebased 0x00..0x0F = raw 0x20..0x2F --
      the table's own storage ends there); rebased >=0x30 -> qword table @0x4ab80 (entry i at
      0x4ab80+i*8, i.e. raw 0x50..0x7F), NULL entry = unimplemented opcode.
      => raw codes 0x30..0x4F index PAST table A into .rdata string bytes: ILLEGAL, no assert.
  0x7120 = THE GEOMETRY PARSER, shared by Hi_RegisterSummonModel@0x15ee0 and the whole
    Hi_Register*EffModel family; it decodes DATA+0x08 into the GEOM block (see the geometry section).

VALIDATION: every rule here was re-run against all 372 stock files -- results, the invariant/overfit
ledger and the corrections to M2/M4 are in ``D3-container-validate.md``.  Load-bearing corrections
already folded in: sub-blocks are 4-BYTE ALIGNED (not exactly adjacent), the model header's
addresses are HEADER-relative (``file = id5.offset + headerRel - texOffset``), and ``listHead``/
``part < partCount``/``firstBlock == motion[0]`` are NOT invariants and must not be gated on.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import List, Optional

SECTOR = 0x800
SEQ_OFFSET = 0x400  # inside sector 0; fn 0x31d31@0x31edb

# --------------------------------------------------------------------------- resource ids
# Authority: the 10-entry dispatch table @0x3ed54 reached from fn 0x3de37's state-5 handler @0x3df3d.
# `yields` = the state machine returns to the caller after this resource (bitmask 0x213 @0x3e632),
# i.e. ids {0,1,4,9} are streamed one-per-tick; the rest are consumed inline.
RESOURCE_IDS = {
    0: ("VRAM_IMAGE_LIST", 0x3E01C, "rect-list image upload: {u16 x,y,w,h} records + 16bpp pixels; "
                                    "callback 0x64000000 (LoadImage) via [0x1c1de8]"),
    1: ("VRAM_IMAGE_CONT", 0x3E11A, "continuation upload reusing the previous record's rect"),
    2: ("SOUND_AKAO", 0x3DF78, "resolved through the chunk directory entries 0 and 1 "
                               "(base/end) then handed to 0x3d670"),
    3: ("CHUNK_IMAGE", 0x3E13A, "the PSX RAM image: installs ctx->chunkRec[slot] and runs 0xd1a0"),
    4: ("VRAM_TEXPAGE", 0x3E272, "CLUT at (0x100 wide, y=0xe6) + N 64x128 16bpp texture pages "
                                 "(0x4000 bytes each)"),
    5: ("SUMMON_MODEL", 0x3E373, "relocated model record; ends in Hi_RegisterSummonModel@0x15ee0"),
    6: ("MARK_6", 0x3E46A, "sets byte[0x323242]=2 (a load-state marker only)"),
    7: ("MARK_7", 0x3E476, "sets byte[0x323254]=2 / [0x323256]; the state machine re-enters it "
                           "(0x3e66c) alternating states 6/7"),
    8: ("MARK_8", 0x3E49F, "sets byte[0x323258]=2 (a load-state marker only)"),
    9: ("VRAM_TEXPAGE_ALT", 0x3E4AB, "second texture-page path; source table 0x171dc0 or [0x69720]"),
}
STREAMED_IDS = {0, 1, 4, 9}  # bitmask 0x213 @0x3e632

# --------------------------------------------------------------------------- sequence opcodes
# Authority: the jump table @0x31f58 (low) and the qword tables @0x4aff0 / @0x4ab80 (high).
_LOW_TABLE = {  # raw code -> handler rva inside fn 0x315f1 (0x316da == _wassert stub)
    0x00: 0x31AAD, 0x01: 0x31680, 0x02: 0x316AF, 0x03: 0x316C0, 0x04: 0x316F9,
    0x05: 0x31712, 0x06: 0x3172D, 0x07: 0x318A2, 0x08: 0x317B0, 0x09: 0x3181A,
    0x0A: 0x3184B, 0x0B: 0x31CC5, 0x0C: 0x3186F, 0x0D: 0x31D0D, 0x0E: 0x31966,
    0x0F: 0x3198D, 0x10: 0x316DA, 0x11: 0x316DA, 0x12: 0x316DA, 0x13: 0x316DA,
    0x14: 0x31894,
}
_ASSERT_STUB = 0x316DA
# table A @0x4aff0, rebased 0x00..0x0F only (raw 0x20..0x2F) -- storage past 0x0F is string data
_TABLE_A = {
    0x20: 0x39D60, 0x21: 0x3B480, 0x22: 0x3B3E0, 0x23: 0x3BB80, 0x24: 0x3BE40, 0x25: 0x3BAB0,
    0x26: 0x39D90, 0x27: 0x3A690, 0x28: 0x3B0D0, 0x29: 0x3BBD0, 0x2A: 0x3BD10, 0x2B: 0x39E10,
    0x2C: 0x39DC0, 0x2D: 0x3BF00, 0x2E: 0x3BF60, 0x2F: 0x3B410,
}
# table B @0x4ab80 indexed by rebased code (raw-0x20); 0 => unimplemented
_TABLE_B = {
    0x50: 0x18FD0, 0x51: 0x19000, 0x52: 0, 0x53: 0, 0x54: 0, 0x55: 0x19030, 0x56: 0x190A0,
    0x57: 0x19130, 0x58: 0, 0x59: 0, 0x5A: 0x19170, 0x5B: 0x191F0, 0x5C: 0x19230, 0x5D: 0,
    0x5E: 0x19280, 0x5F: 0x192C0, 0x60: 0, 0x61: 0x19310, 0x62: 0x19350, 0x63: 0x193E0,
    0x64: 0x19430, 0x65: 0x19470, 0x66: 0, 0x67: 0, 0x68: 0, 0x69: 0x194F0, 0x6A: 0x195A0,
    0x6B: 0x195E0, 0x6C: 0x196F0, 0x6D: 0x197A0, 0x6E: 0x19830, 0x6F: 0x19880, 0x70: 0x19990,
    0x71: 0x19A90, 0x72: 0x19B80, 0x73: 0x19C20, 0x74: 0, 0x75: 0, 0x76: 0, 0x77: 0, 0x78: 0,
    0x79: 0x19C80, 0x7A: 0x19D70, 0x7B: 0x19E50, 0x7C: 0x19F30, 0x7D: 0, 0x7E: 0, 0x7F: 0x19FC0,
}

# Names: only where the native handler was read directly. Everything else stays UNNAMED on purpose --
# SFXBinaryFile.cs's enum is a hypothesis, not an authority (see M2-container-format.md).
OPCODE_NAMES = {
    0x00: "END_HOLD",        # 0x31aad: rewinds the pointer 3 (re-executes) + notifies host 0x73000000
    0x01: "WAIT",            # arg1==0: wait arg2 ticks; arg1!=0: wait until channel-flag[arg2]==0
    0x02: "SET_CHANNEL_FLAG",# byte[0x323180 + arg1] = arg2
    0x05: "LOAD_CHUNK",      # slot = 0x30bd0(arg1); stored at [0x323178] = implicit arg of every >=0x20 op
}


def opcode_status(code: int):
    """('VALID'|'INVALID_ASSERT'|'ILLEGAL_OOB'|'UNIMPLEMENTED', handler_rva_or_None)."""
    if code < 0x20:
        h = _LOW_TABLE.get(code)
        if h is None:
            return "INVALID_ASSERT", None          # 0x15..0x1F -> _wassert @0x316da
        return ("INVALID_ASSERT", None) if h == _ASSERT_STUB else ("VALID", h)
    if code < 0x30:
        return "VALID", _TABLE_A[code]
    if code < 0x50:
        return "ILLEGAL_OOB", None                  # indexes past table A into .rdata strings
    if code < 0x80:
        h = _TABLE_B[code]
        return ("UNIMPLEMENTED", None) if h == 0 else ("VALID", h)
    return "VALID", 0x49170                          # sub-index = code - 0x80


# --------------------------------------------------------------------------- structures
@dataclass
class Resource:
    index: int
    id: int
    info: int
    size_sectors: int
    offset: int          # absolute file offset of the payload
    nbytes: int
    extra_sectors: Optional[int] = None   # id==2 && info!=0 only

    @property
    def kind(self) -> str:
        return RESOURCE_IDS.get(self.id, (f"UNKNOWN_{self.id}", 0, ""))[0]


@dataclass
class Chunk:
    slot: int             # position in the table -- the psx-base parity key
    chunk_index: int
    resources: List[Resource] = field(default_factory=list)

    @property
    def psx_base(self) -> int:
        """fn 0xd390@0xd431: 0x801E7700 + (slot & 1) * 0x5000."""
        return 0x801E7700 + (self.slot & 1) * 0x5000


@dataclass
class Container:
    size: int
    chunks: List[Chunk]
    table_end: int        # file offset just past the resource table
    cursor_end: int       # the walker's final resourcePosition -- MUST equal size


class ContainerError(RuntimeError):
    pass


def _s16(b, o): return struct.unpack_from("<h", b, o)[0]
def _u16(b, o): return struct.unpack_from("<H", b, o)[0]
def _u32(b, o): return struct.unpack_from("<I", b, o)[0]
def _s32(b, o): return struct.unpack_from("<i", b, o)[0]
def _a4(v): return (v + 3) & ~3


def parse_header(blob: bytes, strict: bool = True) -> Container:
    """Port of fn 0xd390 (the native resource-table walker). Every field width/signedness matches
    the disassembly: chunkCount/chunkIndex/resourceCount/size are read with MOVSX (signed 16),
    id/info with MOVSX (signed 8)."""
    off = 0
    chunk_count = _s16(blob, off); off += 2
    pos = SECTOR                                    # r11d = 0x800 @0xd3ab
    chunks: List[Chunk] = []
    for i in range(chunk_count):
        ci = _s16(blob, off); rc = _s16(blob, off + 2); off += 4
        ch = Chunk(slot=i, chunk_index=ci)
        for j in range(rc):
            rid = struct.unpack_from("<b", blob, off)[0]
            info = struct.unpack_from("<b", blob, off + 1)[0]
            size = _s16(blob, off + 2)
            nbytes = size << 11
            r = Resource(index=j, id=rid, info=info, size_sectors=size, offset=pos, nbytes=nbytes)
            off += 4
            pos += nbytes                            # every path adds size<<11 (0xd409/0xd418/0xd4a4)
            if rid == 2 and info != 0:               # 0xd49f: the ONLY conditional extra field
                r.extra_sectors = _s16(blob, off); off += 2
                pos += r.extra_sectors << 11
            ch.resources.append(r)
        chunks.append(ch)
    c = Container(size=len(blob), chunks=chunks, table_end=off, cursor_end=pos)
    if strict and pos != len(blob):
        raise ContainerError(
            f"resource table sums to {pos:#x} but the file is {len(blob):#x} -- parser drift")
    return c


# --------------------------------------------------------------------------- id-3 chunk image
@dataclass
class ChunkImage:
    psx_base: int
    header_rel: int
    program_offsets: List[int]     # 16 slots; 0 == absent


def parse_chunk_image(blob: bytes, res: Resource, psx_base: int) -> ChunkImage:
    """Port of fn 0xd390's id==3 arm (@0xd415..0xd499).

    The id-3 payload is a PS1 main-RAM image mapped at ``psx_base`` and still carrying ABSOLUTE
    PSX pointers. Relocation = ``(ptr & 0x0FFFFFFF) - (psx_base & 0x0FFFFFFF)``.
      * dword @ +0x00       -> headerRel (a pointer to the image's own header)
      * 16 dwords @ headerRel+8 -> the chunk's program/entry-point table (ctx chunkRec+0x18[])
    """
    base = psx_base & 0x0FFFFFFF
    d = res.offset
    header_rel = (_u32(blob, d) & 0x0FFFFFFF) - base
    if not (0 <= header_rel < res.nbytes):
        raise ContainerError(f"id3 headerRel {header_rel:#x} outside the {res.nbytes:#x}-byte image")
    tbl = d + header_rel + 8
    progs = []
    for k in range(16):
        v = _u32(blob, tbl + 4 * k)
        progs.append(0 if v == 0 else (v & 0x0FFFFFFF) - base)
    return ChunkImage(psx_base=psx_base, header_rel=header_rel, program_offsets=progs)


def parse_directory(blob: bytes, base_off: int, count: Optional[int] = None) -> List[int]:
    """The sub-resource directory: fn 0x3d800's tail @0x3da87 computes
    ``entry = base + (Int32)base[idx]`` -- a table of SIGNED 32-bit offsets RELATIVE TO THE TABLE.
    Self-describing: entry[0] points just past the table, so count == entry[0] // 4.
    (NOTE: SFXBinaryFile.cs reads these same bytes as u16 offset + u16 flags pairs; a 'flags==0xFFFF
    external file' in that model is simply a NEGATIVE relative offset here.)"""
    first = _s32(blob, base_off)
    n = count if count is not None else (first // 4 if first > 0 else 0)
    return [_s32(blob, base_off + 4 * i) for i in range(n)]


# --------------------------------------------------------------------------- id4+id5 model package
@dataclass
class ModelPackage:
    """THE CREATURE MODEL HEADER. One struct, at the START OF THE id-4 PAYLOAD, read by the id-4
    handler @0x3e272 (textures), the id-5 handler @0x3e373 (model/motions) and finally handed to
    ``Hi_RegisterSummonModel`` @0x15ee0 as ``rcx`` (@0x3e447 ``mov rcx,rsi``).  M2 called it "the
    package header" and M4 "the model header": D3 proved they are the SAME struct.

    THE STAGING RULE (D3 -- this is what reconciles M2 §8.1 with M4 §1/§2).  The header and the
    payloads are streamed into ONE arena (``0x50000`` bytes -- @0x3e40d ``mov eax,0x50000`` /
    ``sub eax,[rsi+0x10]`` = free space).  The header occupies ``arena[0 .. texOffset)``; everything
    after it is a SHARED staging area at ``arena + texOffset``:

      * the id-4 payload lands there first -> the texture pages + CLUT are DMA'd to VRAM
        (@0x3e302-0x3e34b, rect ``x=(tpage&0xf)*64, y=((tpage&0x10)<<4)+vOffset, w=64, h=128``);
      * the id-5 payload then OVERWRITES the same address with the MODEL IMAGE.

    So ``header+texOffset`` is the texture blob at id-4 time and the GEOMETRY BLOCK afterwards, and
    ``model[+0x3c] = psx(header + texOffset)`` (@0x3e39c) -> ``DATA+0x08`` (@0x15f3f) -> the geom
    pointer fn 0x7120 decodes (@0x7130 ``mov r9d,[rcx+8]``).  **M4's "DATA+0x08 is the geometry
    handle" is right and M2 §8.1's "it is a pointer to the texture blob" is wrong** -- they are the
    same address at different times.  Consequence for an offline reader: every header field that
    addresses the model image is HEADER-relative, so
        ``file offset = id5.offset + headerRelative - texOffset``.

      +0x00  s16  texOffset   == 0x180 + 4*motionCount (24/24) -- header size == model-image base
      +0x02  s16  motionCount N
      +0x04  s16  partCount   -- materials AND 64x128 texture pages (one page per part; max 6, the
                                three u16[] tables tile 0x18/0x24/0x30 -> 0x3c exactly)
      +0x06  u16  clutRows    -- CLUT strip, w=0x100, VRAM y=0xe6 (@0x3e286 rect 0xe60100)
      +0x08  u32  texBytes    == partCount * 0x4000 (24/24)
      +0x0c  u32  clutBytes   == clutRows  * 0x200  (24/24)
      +0x10  u32  modelBytes  -- END of the model image, header-relative (@0x3e3dc -> model[+0x44])
      +0x14  u32  firstBlock  -- END of the GEOMETRY block == start of the texanim table
                                 (@0x3e393 -> model[+0x40] -> DATA+0x70); 24/24 exact in D3
      +0x18  u16[partCount]  TPAGE   (@0x16000 -> rec+0x08+4i)
      +0x24  u16[partCount]  CLUT    (@0x1600f -> rec+0x0a+4i)
      +0x30  u16[partCount]  texture V-offset (@0x16016; also the VRAM y offset @0x3e31c)
      +0x3c  u32  <- psx(header+texOffset)  = the GEOMETRY handle  (written at load; 0 on disk)
      +0x40  u32  <- psx(header+firstBlock) = the TEXANIM table    (written at load; 0 on disk)
      +0x90       block handed to fn 0x15a20(ptr, 1)
      +0x180 u32[N] MOTION TABLE, header-relative (relocated in place @0x3e3c0-0x3e3d1)
    """
    tex_offset: int
    motion_count: int
    part_count: int
    clut_rows: int
    tex_bytes: int
    clut_bytes: int
    model_bytes: int
    first_block: int
    motion_offsets: List[int]        # header-relative, as stored
    tpage: List[int]
    clut: List[int]
    v_offset: List[int]
    header_offset: int               # = the id-4 payload offset
    tex_file_offset: int             # absolute file offset of the texture pages (id-4 time)
    model_file_offset: int           # absolute file offset of the model image = the id-5 payload
    model_bytes_total: int           # the model image's own size (modelBytes - texOffset)

    def to_file(self, header_rel: int) -> int:
        """Header-relative model-image address -> absolute file offset."""
        return self.model_file_offset + header_rel - self.tex_offset

    @property
    def geom_offset(self) -> int:
        return self.model_file_offset                      # geometry starts the model image

    @property
    def geom_end(self) -> int:
        return self.to_file(self.first_block)

    @property
    def motion_file_offsets(self) -> List[int]:
        return [self.to_file(m) for m in self.motion_offsets]


def parse_model_package(blob: bytes, chunk: Chunk) -> Optional[ModelPackage]:
    """Requires the chunk to carry both an id-4 and an id-5 resource (24 effects in the stock set)."""
    r4 = next((r for r in chunk.resources if r.id == 4), None)
    r5 = next((r for r in chunk.resources if r.id == 5), None)
    if r4 is None or r5 is None:
        return None
    a = r4.offset
    n = _s16(blob, a + 2)
    npart = _s16(blob, a + 4)
    tex_off = _s16(blob, a)
    return ModelPackage(
        tex_offset=tex_off, motion_count=n, part_count=npart, clut_rows=_u16(blob, a + 6),
        tex_bytes=_u32(blob, a + 8), clut_bytes=_u32(blob, a + 0xC),
        model_bytes=_u32(blob, a + 0x10), first_block=_u32(blob, a + 0x14),
        motion_offsets=[_u32(blob, a + 0x180 + 4 * i) for i in range(n)],
        tpage=[_u16(blob, a + 0x18 + 2 * i) for i in range(npart)],
        clut=[_u16(blob, a + 0x24 + 2 * i) for i in range(npart)],
        v_offset=[_u16(blob, a + 0x30 + 2 * i) for i in range(npart)],
        header_offset=a, tex_file_offset=a + tex_off, model_file_offset=r5.offset,
        model_bytes_total=_u32(blob, a + 0x10) - tex_off,
    )


def vram_rect(tpage: int, v_offset: int) -> tuple:
    """The 64x128 16bpp page rect the id-4 handler uploads (@0x3e302-0x3e34b)."""
    return ((tpage & 0x0F) * 64, ((tpage & 0x10) << 4) + v_offset, 64, 128)


# --------------------------------------------------------------------------- geometry (GEOM block)
# Authority: fn 0x7120 (the shared parser used by BOTH Hi_RegisterSummonModel@0x15ee0 and the whole
# Hi_Register*EffModel family), its relocate/bake continuation 0x7233..0x780e, the per-mesh vertex pass
# 0x4eb0 and the primitive emit engine 0x56c0/0x58f9.  See M4-mesh-payload.md; every claim below was
# re-validated against the stock corpus in D3-container-validate.md.
#
# ON DISK every sub-block pointer is an offset RELATIVE TO THE GEOM BLOCK BASE; fn 0x7120 rewrites them
# in place into PSX addresses (`mov edx,[rsi+0xc]; add rdx,rsi; call 0x12b00; mov [rsi+0xc],eax`
# @0x7233-0x7256), fenced by `flags` bit0 so it happens exactly once.

#            name    code  stride  cnt_off  nvert  nuv  ncol  inline_rgb
PRIM_TYPES = (
    ("FT4", 0x2C, 0x18, 0x02, 4, 4, 0, True),
    ("FT3", 0x24, 0x14, 0x04, 3, 3, 0, True),
    ("GT4", 0x3C, 0x20, 0x06, 4, 4, 4, False),
    ("GT3", 0x34, 0x18, 0x08, 3, 3, 3, False),
    ("G4",  0x38, 0x18, 0x0A, 4, 0, 4, False),
    ("G3",  0x30, 0x14, 0x0C, 3, 0, 3, False),
    ("F4",  0x28, 0x10, 0x0E, 4, 0, 0, True),
    ("F3",  0x20, 0x0C, 0x10, 3, 0, 0, True),
)
# per-type field offsets inside a record (M4 §5.1, each cited to its builder)
PRIM_FIELDS = {
    "FT4": dict(v=(0x00, 0x02, 0x04, 0x06), uv=(0x08, 0x0A, 0x0C, 0x0E), rgb=0x10, part=0x13, flg=0x15),
    "FT3": dict(v=(0x00, 0x02, 0x04), uv=(0x0C, 0x0E, 0x10), rgb=0x08, part=0x06, flg=0x12),
    "GT4": dict(v=(0x00, 0x02, 0x04, 0x06), uv=(0x08, 0x0A, 0x0C, 0x0E),
                col=(0x10, 0x12, 0x14, 0x16), part=0x1D, flg=0x1C),
    "GT3": dict(v=(0x00, 0x02, 0x04), uv=(0x06, 0x08, 0x0A),
                col=(0x10, 0x12, 0x14), part=0x16, flg=0x0F),
    "G4":  dict(v=(0x00, 0x02, 0x04, 0x06), col=(0x08, 0x0A, 0x0C, 0x0E), flg=0x14),
    "G3":  dict(v=(0x00, 0x02, 0x04), col=(0x08, 0x0A, 0x0C), flg=0x13),
    "F4":  dict(v=(0x00, 0x02, 0x04, 0x06), rgb=0x08, flg=0x0D),
    "F3":  dict(v=(0x00, 0x02, 0x04), rgb=0x08, flg=0x0B),
}
MAX_VERTS_PER_MESH = 0x1B58   # `cmp idx,0x1b58` @0x50b3 and in every emit loop


@dataclass
class BoneLink:
    """4 bytes: {u16 len; u8 zero; u8 parentBone} -- fn 0x7de7 @0x81aa reads byte+3 as the parent and
    indexes boneMatrix[parent] with `shl rdi,5` (stride 0x20 = the PSX MATRIX)."""
    length: int
    zero: int
    parent: int


@dataclass
class Mesh:
    index: int
    unknown0: int                 # MeshDesc+0x00 -- OPAQUE (NOT nVert; falsified corpus-wide)
    counts: List[int]             # the eight bucket counts, in emission order (PRIM_TYPES)
    zero: int                     # +0x12
    ot_bias: int                  # +0x13 (signed): OT base = otBase + (8 - otBias)*4  @0x5af7
    p_verts_per_bone: int         # +0x14  (geom-relative on disk)
    p_positions: int              # +0x18
    p_primitives: int             # +0x1c
    p_uv: int                     # +0x20
    p_colors: int                 # +0x24
    verts_per_bone: List[int]
    col_count: Optional[int] = None   # derived by chain closure, not stored in the file

    @property
    def n_vert(self) -> int:
        """Sum of the per-bone runs: skinning is RIGID + RUN-LENGTH (fn 0x4eb0 @0x509d)."""
        return sum(self.verts_per_bone)

    @property
    def uv_count(self) -> int:
        """Only the four TEXTURED buckets carry UV indices (4/3/4/3 per face)."""
        return sum(self.counts[i] * PRIM_TYPES[i][5] for i in range(8))

    @property
    def prim_bytes(self) -> int:
        return sum(self.counts[i] * PRIM_TYPES[i][2] for i in range(8))

    @property
    def face_count(self) -> int:
        return sum(self.counts)


@dataclass
class Geom:
    base: int                     # absolute file offset of the block
    flags: int
    zero1: int
    bone_count: int
    mesh_count: int
    unknown_a: int                # +0x04 OPAQUE
    unknown_b: int                # +0x08 OPAQUE
    p_bone_table: int             # +0x0c (on disk 0x14; bone rows live at decode(+0xc)+4 == +0x18)
    p_mesh_table: int             # +0x10 (on disk == 0x18 + (boneCount-1)*4)
    list_head: int                # +0x14
    bones: List[BoneLink]
    meshes: List[Mesh]

    @property
    def end(self) -> int:
        """Block end = the last mesh's colour pool end (chain closure)."""
        m = self.meshes[-1]
        return self.base + m.p_colors + 4 * (m.col_count or 0)


def parse_geom(blob: bytes, base: int, block_end: Optional[int] = None) -> Geom:
    """Decode a GEOM block at absolute file offset ``base`` (pre-relocation, i.e. as it sits on disk).

    ``block_end`` bounds the last mesh's colour pool; when omitted the pool is assumed to run to the
    next sub-block or, for the final mesh, is left as ``None`` (``col_count`` unresolved).
    """
    flags = blob[base]
    zero1 = blob[base + 1]
    bone_count = blob[base + 2]
    mesh_count = blob[base + 3]
    unk_a = _u32(blob, base + 4)
    unk_b = _u32(blob, base + 8)
    p_bone = _u32(blob, base + 0x0C)
    p_mesh = _u32(blob, base + 0x10)
    list_head = _u32(blob, base + 0x14)
    if bone_count == 0 or mesh_count == 0:
        raise ContainerError("geom: boneCount/meshCount == 0")
    bones = [BoneLink(_u16(blob, base + 0x18 + 4 * i), blob[base + 0x18 + 4 * i + 2],
                      blob[base + 0x18 + 4 * i + 3]) for i in range(bone_count - 1)]
    meshes: List[Mesh] = []
    for i in range(mesh_count):
        d = base + p_mesh + 0x28 * i          # `lea rcx,[rax+rax*4]; lea r8,[rdx+rcx*8]` @0x58fe
        counts = [_u16(blob, d + PRIM_TYPES[k][3]) for k in range(8)]
        vpb_off = _u32(blob, d + 0x14)
        vpb = [_u16(blob, base + vpb_off + 2 * b) for b in range(bone_count)]
        meshes.append(Mesh(
            index=i, unknown0=_u16(blob, d), counts=counts, zero=blob[d + 0x12],
            ot_bias=struct.unpack_from("<b", blob, d + 0x13)[0],
            p_verts_per_bone=vpb_off, p_positions=_u32(blob, d + 0x18),
            p_primitives=_u32(blob, d + 0x1C), p_uv=_u32(blob, d + 0x20),
            p_colors=_u32(blob, d + 0x24), verts_per_bone=vpb))
    # Chain closure fixes each colour pool's length -- it is the ONE sub-block whose size the file
    # never states. The pool runs to the next sub-block start anywhere in the model (mesh order in the
    # table need not be layout order), or to ``block_end`` for the last one.
    layout = sorted(meshes, key=lambda m: m.p_verts_per_bone)
    for i, m in enumerate(layout):
        nxt = (layout[i + 1].p_verts_per_bone if i + 1 < len(layout)
               else (block_end - base if block_end is not None else None))
        if nxt is not None and nxt >= m.p_colors:
            m.col_count = (nxt - m.p_colors) // 4
    return Geom(base, flags, zero1, bone_count, mesh_count, unk_a, unk_b,
                p_bone, p_mesh, list_head, bones, meshes)


def geom_checks(blob: bytes, g: Geom, limit: Optional[int] = None) -> dict:
    """Every structural identity M4 asserts, evaluated on one block. All are pass/fail booleans, so a
    corpus sweep tells invariant from coincidence. ``limit`` = the enclosing payload's end offset."""
    r = {
        "flags_bit0_clear": (g.flags & 1) == 0,
        "byte1_zero": g.zero1 == 0,
        "pBoneTable_is_0x14": g.p_bone_table == 0x14,
        "pMeshTable_law": g.p_mesh_table == 0x18 + (g.bone_count - 1) * 4,
        "listHead_zero": g.list_head == 0,
    }
    ok_uv = ok_vpb = ok_pos = ok_prim = ok_mz = True
    for i, m in enumerate(g.meshes):
        ok_mz &= (m.zero == 0)
        # The five sub-blocks are contiguous, in this order, per mesh -- each one starting at the
        # 4-BYTE-ALIGNED end of the previous (D3 correction to M4, which asserted exact adjacency:
        # ef227 mesh1's UV pool is 3197 u16 = 6394 B and its colour pool starts 2 bytes later).
        ok_vpb &= (_a4(m.p_verts_per_bone + 2 * g.bone_count) == m.p_positions)
        ok_pos &= (_a4(m.p_positions + 8 * m.n_vert) == m.p_primitives)
        ok_prim &= (_a4(m.p_primitives + m.prim_bytes) == m.p_uv)
        ok_uv &= (_a4(m.p_uv + 2 * m.uv_count) == m.p_colors)
    r["mesh_byte0x12_zero"] = ok_mz
    r["chain_vertsPerBone_to_positions"] = ok_vpb
    r["chain_positions_to_primitives"] = ok_pos      # proves the 8-byte vertex + Sum(vertsPerBone)
    r["chain_primitives_to_uv"] = ok_prim            # proves all 8 counts AND all 8 strides
    r["chain_uv_to_colors"] = ok_uv                  # proves u16 UV entries + the 4/3/4/3 UV-per-face
    if limit is not None:
        last = g.meshes[-1]
        r["in_bounds"] = g.base + last.p_colors <= limit
    return r


def iter_primitives(blob: bytes, g: Geom, mesh: Mesh):
    """Yield every face of one mesh as a dict. ``uv``/``col``/``rgb``/``part``/``flag`` are present
    only for the types that carry them. Indices are into the mesh's own pools."""
    off = g.base + mesh.p_primitives
    for k, (name, code, stride, _c, nv, nuv, ncol, has_rgb) in enumerate(PRIM_TYPES):
        f = PRIM_FIELDS[name]
        for _ in range(mesh.counts[k]):
            rec = {"type": name, "code": code,
                   "v": [_u16(blob, off + o) for o in f["v"]],
                   "flag": blob[off + f["flg"]]}
            if nuv:
                rec["uv"] = [_u16(blob, off + o) for o in f["uv"]]
            if ncol:
                rec["col"] = [_u16(blob, off + o) for o in f["col"]]
            if has_rgb:
                rec["rgb"] = tuple(blob[off + f["rgb"] + i] for i in range(3))
            if "part" in f:
                rec["part"] = blob[off + f["part"]]
            # flag byte: bit0 = semi-transparent, bit1 = SKIP the backface test, bits5..7 = ABR mode
            rec["no_cull"] = bool(rec["flag"] & 2)
            rec["abr"] = (rec["flag"] >> 5) & 3
            yield rec
            off += stride


def vertices(blob: bytes, g: Geom, mesh: Mesh):
    """Yield (x, y, z, w) s16 quads. Skinning is implied by position: vertex n belongs to the bone
    whose run contains it (``verts_per_bone``); ``w`` is loaded into the GTE but never read."""
    o = g.base + mesh.p_positions
    for i in range(mesh.n_vert):
        yield struct.unpack_from("<4h", blob, o + 8 * i)


def bone_of_vertex(mesh: Mesh) -> List[int]:
    out: List[int] = []
    for b, n in enumerate(mesh.verts_per_bone):
        out.extend([b] * n)
    return out


def creature_geom(blob: bytes, mp: ModelPackage) -> Geom:
    """TYPED lookup -- closes M4 §7 item 7.  The creature's GEOM block is at offset 0 of the id-5
    payload (24/24 stock model packages), and the header states its exact end (``firstBlock``), so
    the last mesh's colour pool -- the one length the block never stores -- is determined too."""
    return parse_geom(blob, mp.geom_offset, block_end=mp.geom_end)


# GEOM blocks also exist OUTSIDE the summon lane (the Eff-model family shares fn 0x7120).  In the
# stock corpus 1005 blocks live in resources id 2 (658), 6 (282), 5 (24, the creatures), 8 (20),
# 3 (12) and 10 (9); only the id-5 ones sit at their resource's offset 0, so the rest need this scan.
_GEOM_NEEDLE = b"\x14\x00\x00\x00"          # geom+0x0c == 0x14, on disk, 1005/1005


def scan_geom(blob: bytes, start: int = 0, end: Optional[int] = None):
    """Yield every GEOM block in ``blob[start:end]``.  Acceptance = the cheap header law
    (``pBoneTable == 0x14`` and ``pMeshTable == 0x18+(boneCount-1)*4``) plus the four chain
    identities; in the stock corpus that pair is already 100% selective (zero candidates passed the
    header law and then failed a chain check)."""
    end = len(blob) if end is None else end
    pos = start
    while True:
        k = blob.find(_GEOM_NEEDLE, pos, end)
        if k < 0:
            return
        pos = k + 4
        base = k - 0x0C
        if base < start or blob[base] & 1 or blob[base + 1] != 0:
            continue
        bc, mc = blob[base + 2], blob[base + 3]
        if bc == 0 or mc == 0 or _u32(blob, base + 0x10) != 0x18 + (bc - 1) * 4:
            continue
        try:
            g = parse_geom(blob, base)
        except (ContainerError, struct.error, IndexError):
            continue
        chk = geom_checks(blob, g)
        # listHead is NOT an invariant (7/1005 non-zero) and in_bounds needs the caller's extent
        if all(v for kk, v in chk.items() if kk not in ("listHead_zero", "in_bounds")):
            yield g


# --------------------------------------------------------------------------- sequence stream
@dataclass
class Op:
    at: int
    code: int
    arg1: int
    arg2: int
    status: str
    handler: Optional[int]

    @property
    def name(self) -> str:
        return OPCODE_NAMES.get(self.code, f"op_{self.code:02X}")


def parse_sequence(blob: bytes, off: int = SEQ_OFFSET, limit: int = 200_000) -> List[Op]:
    """Port of fn 0x315f1's fetch/dispatch head (@0x31647..0x3167e). 3-byte (code,arg1,arg2)
    records; the interpreter stops advancing on code 0x00 (END_HOLD rewinds the pointer)."""
    ops: List[Op] = []
    for _ in range(limit):
        code, a1, a2 = blob[off], blob[off + 1], blob[off + 2]
        st, h = opcode_status(code)
        ops.append(Op(off, code, a1, a2, st, h))
        off += 3
        if code == 0x00:
            return ops
    raise ContainerError("sequence stream never reached END within the limit")


# --------------------------------------------------------------------------- convenience
def describe(blob: bytes) -> str:
    c = parse_header(blob, strict=False)
    out = [f"size={c.size:#x} chunks={len(c.chunks)} tableEnd={c.table_end:#x} "
           f"cursorEnd={c.cursor_end:#x} lenMatch={c.cursor_end == c.size}"]
    for ch in c.chunks:
        out.append(f"  chunk[{ch.slot}] index={ch.chunk_index} psxBase={ch.psx_base:#x} "
                   f"resources={len(ch.resources)}")
        for r in ch.resources:
            ex = f" extra={r.extra_sectors}" if r.extra_sectors is not None else ""
            out.append(f"    [{r.index}] id={r.id} info={r.info} sectors={r.size_sectors} "
                       f"@{r.offset:#x} ({r.nbytes:#x}) {r.kind}{ex}")
            if r.id == 3:
                try:
                    img = parse_chunk_image(blob, r, ch.psx_base)
                    live = [(k, f"{v:#x}") for k, v in enumerate(img.program_offsets) if v]
                    out.append(f"        headerRel={img.header_rel:#x} programs={live}")
                except ContainerError as e:
                    out.append(f"        !! {e}")
            if r.id == 2:
                try:
                    d = parse_directory(blob, r.offset)
                    out.append(f"        sub-file directory: {len(d)} entries "
                               f"(entry0={d[0]:#x}, last={d[-1]:#x})")
                except Exception as e:                      # noqa: BLE001
                    out.append(f"        !! directory: {e}")
        mp = parse_model_package(blob, ch)
        if mp:
            out.append(f"    MODEL HEADER @{mp.header_offset:#x}: parts={mp.part_count} "
                       f"motions={mp.motion_count} clutRows={mp.clut_rows} "
                       f"texBytes={mp.tex_bytes:#x} clutBytes={mp.clut_bytes:#x}")
            out.append(f"      tpage={mp.tpage} clut={[hex(c) for c in mp.clut]} "
                       f"vOffset={mp.v_offset}")
            out.append(f"      texture pages @{mp.tex_file_offset:#x} -> VRAM "
                       f"{[vram_rect(t, v) for t, v in zip(mp.tpage, mp.v_offset)]}")
            out.append(f"      MODEL IMAGE @{mp.model_file_offset:#x} ({mp.model_bytes_total:#x} B): "
                       f"geom [{mp.geom_offset:#x}..{mp.geom_end:#x}) then texanim, then "
                       f"{mp.motion_count} motion clips at "
                       f"{[hex(x) for x in mp.motion_file_offsets]}")
            try:
                g = creature_geom(blob, mp)
                out.append(f"      GEOM: bones={g.bone_count} meshes={g.mesh_count} "
                           f"verts={sum(m.n_vert for m in g.meshes)} "
                           f"faces={sum(m.face_count for m in g.meshes)}")
                for m in g.meshes:
                    used = {PRIM_TYPES[i][0]: m.counts[i] for i in range(8) if m.counts[i]}
                    out.append(f"        mesh{m.index}: verts={m.n_vert} uv={m.uv_count} "
                               f"col={m.col_count} {used}")
            except (ContainerError, struct.error, IndexError) as e:
                out.append(f"      !! geometry: {e}")
    ops = parse_sequence(blob)
    bad = [o for o in ops if o.status != "VALID"]
    ticks = sum(o.arg2 for o in ops if o.code == 0x01 and o.arg1 == 0)
    out.append(f"  sequence: {len(ops)} ops, {len(bad)} non-VALID, {ticks} waited ticks")
    return "\n".join(out)


if __name__ == "__main__":
    import sys
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    scan = "--scan-geom" in sys.argv
    for p in args:
        blob = open(p, "rb").read()
        print("=" * 72)
        print(p)
        print(describe(blob))
        if scan:
            for g in scan_geom(blob):
                print(f"  GEOM @{g.base:#x}: bones={g.bone_count} meshes={g.mesh_count} "
                      f"verts={sum(m.n_vert for m in g.meshes)} "
                      f"faces={sum(m.face_count for m in g.meshes)}")
