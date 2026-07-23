# M2 — THE `ef###.bytes` CONTAINER, DECODED

**Slice M2 of the summon-cutscene disasm round.** Goal: the container the native `SFX_Play` is handed —
chunk/section table, counts, offsets, section TYPES — decoded from the **native loader** (authoritative)
and validated against **real files** (all 372 stock `ef###.bytes`, extracted from the user's own install).

All RVAs are image-base-relative for the x64 `FF9SpecialEffectPlugin.dll` (`ImageBase 0x180000000`).
Extracted stock bytes live ONLY under `C:/gd/SCRATCH/summon-format/` — nothing game-derived is written
into the repo. The committable artifact is the parser **`ef_container.py`** (this directory) plus
`m2_dis.py` (a refkit disassembly helper).

---

## 0. HEADLINE — three results that change the pillar

1. **The container is fully decoded and the parser round-trips the whole stock corpus.** 372/372 files
   walk to their exact byte length; 385/385 chunk images relocate; 372/372 sequence streams decode to
   `END` with **zero** invalid opcodes; every `run-program` opcode targets a program that exists.
   The header/table/section layer is **no longer opaque**.

2. **`SFXBinaryFile.cs` is right about the shape and wrong about two rules.** It survives on stock data
   only because its wrong gate happens to correlate perfectly with the real one in every shipped file
   (§3.3), and its "small file directory of u16 offset+flags pairs" is really a table of **signed 32-bit
   relative offsets** (§5) — its `flags == 0xFFFF` "external file" is simply a negative offset.

3. **The genuinely opaque section is not a data format at all — it is PS1 code.** Resource **id 3** is a
   PlayStation main-RAM image mapped at a fixed PSX address, carrying **MIPS R3000A machine code**, which
   the DLL **pre-decodes and interprets** (§6). Sequence opcode `0x80+N` *calls program N of that image*.
   That is the mechanical reason the creature's per-frame transform is neither static nor visible to
   managed code: **it is computed by the effect's own PS1 program.** Any "author a new summon" plan has to
   answer this (§9).

---

## 1. THE LOAD CHAIN (native, fn@rva)

| step | fn | what it does |
|---|---|---|
| export | `SFX_Play` @**0x1e50** | `jmp` thunk |
| body | **0x2880** | `memcpy(staticBlob@0x3678f0, bin, size)` (@0x289e); stores `effNum` → **0x3678e8** (@0x28b7); zeroes 0x697a8; then 0x2910, 0x30c20, 0x12940, 0x12bc0; tail-`jmp` **0x313f0** |
| arm | **0x313f0** | resets the effect state block @0x323170…; sets state=4 |
| header sector | **0x490d0** | copies **blob[0x000 .. 0x800]** (16 × 0x80 SSE, @0x49110) → **0x3208d0**; then calls 0xd740 |
| table walk | **0xd740** → **0xd390** | THE RESOURCE-TABLE WALKER (§3) |
| sequence arm | **0x31d31** @0x31edb | `seqPtr(0x323198) = 0x320cd0` = headerSector **+0x400** → the sequence stream is at **file offset 0x400**, inside sector 0 |
| sector feed | **0x3de37** | the streaming state machine; state-5 (@0x3df3d) dispatches on the resource **id** byte through the 10-entry table @**0x3ed54** (§4) |
| sequence run | **0x315f1** | the opcode interpreter (§7) |

The effect number at `0x3678e8` is compared against literals **inside** the interpreter and elsewhere
(`0x12d`=301, `0x7e`=126, `0xb8`=184, `0x95`=149 — e.g. @0xf5f8, @0x104b4, @0x112a9): the port carries
**per-effect special cases in native code**. A custom effect id will NOT inherit them.

Source-path strings left in `.rdata` name the original tree:
`..\..\SpecialEffectCode\psx\source\psx_compatibility.cpp` (@0x4a3e0),
`..\..\SpecialEffectCode\sonoda\PsxEmulator.cpp` (@0x4a820),
`sonoda\Geo\{geo,geomorph,geosfxrender,geoslice}.cpp` (@0x4a460/0x4a620/0x4a680/0x4a770).
Assert text `Registering NULL address in PsxVirtualAddrMapper64.` (@0x4a880) confirms the PSX-pointer
mapping layer that every `id 3` field relies on.

---

## 2. FILE SHAPE

```
0x0000  u16  chunkCount                       <- fn 0xd390 @0xd3a3 (MOVSX = signed)
0x0002  per chunk: u16 chunkIndex, u16 resourceCount,
        then resourceCount x { u8 id, u8 info, u16 sizeSectors [, u16 extraSectors] }
0x0400  the SEQUENCE STREAM: 3-byte (code, arg1, arg2) records, until code 0x00
0x0800  first resource payload; every payload is 0x800-sector aligned and sized
```

Sector = **0x800** (PS1 CD sector). The walker's running cursor starts at 0x800 and must land exactly on
the file length — that equality is the format's own checksum, and it holds for **372/372** stock files.

`ef227` (Bahamut, 823,296 B = 0xc9000, sha256 `fe590d…d167` — matches the study's recorded read):
table ends at **0x54**, 2 chunks, 18 resources, sequence = **93 ops / 511 ticks**.

---

## 3. THE RESOURCE TABLE — the native rule (fn 0xd390)

### 3.1 The walker, verbatim

```c
r8 = ctx->blob;                       // 0xd399
chunkCount = *(s16*)r8; r8 += 2;      // 0xd3a3   (MOVSX, signed 16)
pos = 0x800;                          // 0xd3ab
for (i = 0; i < chunkCount; i++) {
    chunkIndex    = *(s16*)(r8+0);
    resourceCount = *(s16*)(r8+2);  r8 += 4;      // 0xd3d2
    for (j = 0; j < resourceCount; j++) {
        id   = *(s8*)(r8+0);                      // 0xd3f5  (MOVSX, signed 8)
        info = *(s8*)(r8+1);
        n    = *(s16*)(r8+2) << 11;               // 0xd3f0/0xd3f9  size * 0x800
        r8 += 4;
        pos += n;                                  // every arm adds it (0xd409/0xd418/0xd4a4)
        if (id == 2 && info != 0) {                // 0xd49f — the ONLY conditional extra field
            pos += (*(s16*)r8) << 11;  r8 += 2;    // 0xd4af
        }
        if (id == 3) { /* build the chunk record — see §6.1 */ }
    }
    /* chunk record stride 0x60, array base ctx+0x18 (0xd4c8) */
}
```

### 3.2 Chunk records (runtime, but the layout is what the parser mirrors)

`ChunkRec` — array base `ctx+0x18`, **stride 0x60** (`add rdi,0x60` @0xd4c8), 2 live slots.
Independently re-derived at fn 0xd820 @0xd866/0xd906 and fn 0x3de37 @0x3e21c (same offsets):

| off | field |
|---|---|
| +0x00 | `psxBase` = **0x801E7700 + (chunkOrdinal & 1) * 0x5000** (@0xd431) |
| +0x08 | host pointer to the id-3 payload |
| +0x10 | payload byte size |
| +0x14 | entry count (hard-coded **16**) |
| +0x18 | `programOffset[16]` — relocated (see §6.1) |
| +0x58 | `headerRel` — the id-3 header offset **and the code size** (§6.2) |

### 3.3 ⚠ The C# gate is a correlate, not the rule

`SFXBinaryFile.cs:64` reads the extra `u16` when **`chunkIndex == 0`**. The native reads it when
**`info != 0`**. Census over all 385 stock chunks:

| (chunkIndex == 0, info != 0) | count |
|---|---|
| (True, True) | 372 |
| (False, False) | 13 |

The two conditions are **perfectly correlated in shipped data and nowhere contradicted** — which is why
both walkers hit the exact file length on 372/372 files, and why the C# was never caught. On a
**synthesized** container (our use case) they diverge and the C# rule silently corrupts every offset
after that point. **Use `info != 0`.**

Also: `chunkIndex` is **not an ordinal**. It is 0 for the first chunk and **1 for every later chunk**
(proved by the two multi-chunk files where they differ — `ef381`, chunks `[0,1,1,1,1,1,1,1,1]`, and
`ef447`, `[0,1,1]`). The value that `LOAD_CHUNK` matches is the chunk's **position in the table** — fn
0x30bd0 linear-searches the 2-word table @0x32321c, which fn 0x3de37 fills @0x3e265 with the chunk
*counter*, not the `chunkIndex` field. Verified empirically in §7.3.

---

## 4. SECTION TYPES — the resource id

Authority: the 10-entry jump table @**0x3ed54** reached from fn 0x3de37's state-5 handler @0x3df3d.
Ids **{0,1,4,9}** make the loader yield for a tick (bitmask `0x213` @0x3e632) — they are the bulk
streaming payloads. `id > 9` falls through the `cmp eax,9; ja` guard @0x3e628 and is **silently
skipped** (id 10 exists in 4 places — `ef381` ×3, `ef447` ×1 — and is dead in the PC port).

| id | handler | meaning | corpus |
|---|---|---|---|
| **0** | 0x3e01c | **VRAM image list** — records `{u16 x,y,w,h}` + 16bpp pixels, uploaded via the host callback `[0x1c1de8]` with `0x64000000`; cursor advances `w*h*2` | 385 |
| **1** | 0x3e11a | **VRAM image continuation** — reuses the previous record's rect (multi-sector-run continuation) | 316 |
| **2** | 0x3df78 | **sub-file archive + AKAO sound** — sub-files 0/1 give base/end and are handed to 0x3d670; the payload starts with the sub-file directory (§5) | 385 |
| **3** | 0x3e13a | **PSX RAM image (MIPS code + data)** — installs `ChunkRec`, calls the pre-decoder 0xd1a0 (§6) | 385 |
| **4** | 0x3e272 | **creature texture pages** — CLUT strip (w=0x100, y=0xe6) + N × 64×128 16bpp pages (0x4000 each). **Its payload also carries the MODEL PACKAGE HEADER** (§8) | 24 |
| **5** | 0x3e373 | **summon model image** — relocated, ends in `Hi_RegisterSummonModel`@0x15ee0 | 24 |
| **6** | 0x3e46a | load-state marker only (`byte[0x323242] = 2`) | 24 |
| **7** | 0x3e476 | load-state marker; the state machine re-enters it alternating states 6/7 (@0x3e66c) | 13 |
| **8** | 0x3e49f | load-state marker only (`byte[0x323258] = 2`) | 1 (`ef407`) |
| **9** | 0x3e4ab | **second texture-page path** — 64×128 pages from `0x171dc0` or `*(void**)0x69720` | 37 |
| 10 | — | **ignored** (no dispatch slot) | 4 |

**24 effects carry a creature** (ids 4+5+6 always travel together):
`ef038 ef177 ef179 ef184 ef186 ef210 ef211 ef225 ef226 ef227 ef251 ef261 ef276 ef381 ef431 ef432
ef435 ef438 ef439 ef447 ef493 ef494 ef495 ef498`. `ef227` has the largest model image (78 sectors).

`info` is NOT a size or a type; per id it takes small values (id 0: 1–5; id 1: 1–5; id 2: 0/1 = the extra
gate; id 9: 1,2,3,48,51,52,55,63 — a bit-field, `bit 0..3` is tested @0x3df46). Undecoded except for id 2.

---

## 5. THE SUB-FILE DIRECTORY (what C# calls "small files")

fn **0x3d800** is the sub-resource resolver; its tail @0x3da87 is the whole story:

```asm
0x3da87  movsxd rax, edx              ; idx
0x3da8a  movsxd rax, dword [rcx+rax*4]; s32 relative offset
0x3da8e  add    rax, rcx              ; base + offset
```

So a chunk's sub-files are a **self-describing table of SIGNED 32-bit offsets relative to the table
itself**; `entry[0]` points just past the table, hence `count == entry[0] / 4`.

Handle ranges (fn 0x3d800 head): `<0x40` = the chunk's own directory · `0x40..0x7F` → base 0x22a8d0,
idx−0x40 · `0x80..0xBF` → a second runtime base, idx−0x80 · `>=0xC0` → base 0x171dc0, idx−0xC0.

**Empirical location: the directory is the start of the id-2 payload.** Parsing every id-2 payload as
such a table: **381/385 clean** (count = entry0/4, monotone, in-bounds). The 4 exceptions (`ef381`
chunks 2/4/7, `ef447` chunk 2 — only ever in **multi-chunk** effects) contain **negative** entries, i.e.
they point *backwards* out of the region into earlier-loaded data. That is exactly the case
`SFXBinaryFile.cs:92` calls an "external file" via `flags == 0xFFFF`: a u16 offset with a 0xFFFF high
half **is** a small negative s32. The C# model is a lossy re-reading of the same bytes.

`ef227`: chunk 0 → 30 sub-files (`entry0 = 0x78`), chunk 1 → 54 (`entry0 = 0xd8`). Sub-file 0 of each
chunk is the AKAO/SPU blob (id-2 handler DMAs `[0]..[1]`). Camera resources and sounds are indexed out of
this same table by the sequence's `PLAY_CAMERA`/`PLAY_SOUND` args — consistent with the prior round's
`ef_camera_decode.py`, which parsed ef227's camera tracks out of this region and recovered a
three-way-validated shot clock.

---

## 6. RESOURCE id 3 — the PS1 code image (THE opaque section, now named)

### 6.1 Layout (fn 0xd390 @0xd415, validated 385/385)

The payload is a **PS1 main-RAM image** mapped at `psxBase` and still carrying **absolute PSX pointers**.
Relocation is `rel = (ptr & 0x0FFFFFFF) − (psxBase & 0x0FFFFFFF)` (@0xd442/0xd47d).

```
+0x0000                 u32 psxPtr  -> headerRel        (the image's header; ALSO the code size)
+0x0000 .. headerRel    MIPS R3000A code (+ literals)
 headerRel + 0x00       u32 0        (0 in 385/385)
 headerRel + 0x04       u32 0        (0 in 385/385)
 headerRel + 0x08       u32 psxPtr program[16]          <- ChunkRec+0x18; 0 = absent
 headerRel + ...        data
```

Corpus checks: `0 < headerRel < payloadSize` **385/385**; every live `program[k]` lands **inside the code
region** (`0 < off < headerRel`) **385/385**; the two header words are `(0,0)` **385/385**. Live-program
counts per chunk: 1 (239), 2 (106), 3 (23), 4 (10), 5 (4), 6 (2), 7 (1).

`ef227`: chunk 0 → `headerRel = 0x3120` (12,576 B of code = 3,144 instructions), one program at
`0x9d4`; chunk 1 → `headerRel = 0x42bc`, one program at `0x108c`.

### 6.2 It really is MIPS, interpreted

- **Pre-decoder** fn **0xd1a0**: reads the image pointer/size from the per-slot block
  `ctx+0xc18+slot*0x40` (filled by the id-3 handler @0x3e238 with `psxBase`, `headerRel` as the SIZE, and
  the data pointer), `malloc((size/4 + 1) * 16)` (@0xd1db-0xd1f9), then walks `PC += 4` reading a 32-bit
  instruction word per step (@0xd240-0xd24b) into **16-byte decoded records**.
- **Interpreter** fn **0xe210**: per step it takes the decoded record `rbx`, advances `PC += 4` and the
  cache pointer `+= 0x10` (@0xe25c/0xe264), reads `u16 op = [rbx]`, bounds-checks `op-1 <= 0x59`
  (@0xe275) and jumps through the **0x5A-entry** table @**0xed18**. Handlers read the operands as
  `s32 rd @+4, rs @+8, rt @+0xc` and operate on a **32-dword register file** at
  `ctx + 0xc98 + slot*0x80` (memset to zero at load, @0xd6ab `rep stosd ecx=0x20`):
  `0xe28d: GPR[rd] = GPR[rs] + GPR[rt]` (ADD/ADDU, with the `rd == 0` guard), `0xe2c8: … & …` (AND).
- The **library-call surface** is the 200-entry dispatch @**0x12358** inside fn 0xeea4 — the round's
  earlier "mega-interpreter". It is the **HLE'd PS1 SFX library**, which is why every `Hi_*Summon*`
  function has exactly one call site inside it. (Prior-round finding, re-read consistently here.)

**Consequence.** The effect's per-frame logic — including whatever positions and animates the creature —
is compiled PS1 code inside `ef###.bytes`. It is recoverable *as code* (a MIPS disassembly of a bounded,
few-thousand-instruction program), never as a declarative track.

---

## 7. THE SEQUENCE STREAM (file offset 0x400)

### 7.1 Fetch/dispatch (fn 0x315f1 @0x31647)

```asm
rax = [0x323198]; code = rax[0]; arg1 = rax[1]; arg2 = rax[2]; [0x323198] += 3
if (code >= 0x20) -> 0x31a69 : 0x48b10(code>=0x80 ? code : code-0x20, curChunkSlot, arg1, arg2)
if (code >  0x14) -> _wassert(psx_compatibility.cpp:786)
jump table @0x31f58 [code]
```

### 7.2 The complete validity map (dispatch tables, read directly)

| range | source | verdict |
|---|---|---|
| `0x00..0x0F`, `0x14` | jump table @0x31f58 | **VALID** |
| `0x10..0x13` | table entries all point at the `_wassert` stub 0x316da | **INVALID (asserts)** |
| `0x15..0x1F` | `ja 0x316da` @0x31671 | **INVALID (asserts)** |
| `0x20..0x2F` | qword table @**0x4aff0** (16 entries; storage past index 0x0F is `.rdata` string data) | **VALID** |
| `0x30..0x4F` | rebases to table-A index 0x10..0x2F = **past the table** | **ILLEGAL — jumps into string bytes, no assert** |
| `0x50..0x7F` | qword table @**0x4ab80** (entry i at `0x4ab80 + i*8`, i = code−0x20) | VALID where non-NULL; NULL at `0x52 0x53 0x54 0x58 0x59 0x5D 0x60 0x66 0x67 0x68 0x74..0x78 0x7D 0x7E` |
| `>= 0x80` | fn **0x49170** | **VALID** — see 7.3 |

**Corpus validation:** all 372 files decode to a real `END`, **216 ops max**, and **every one of the
11,807 opcodes across the corpus is VALID** under this map — zero in the assert holes, zero in the
illegal 0x30..0x4F band. 56 distinct codes appear:
`00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0F | 23 24 25 28 29 2A 2B 2C 2D 2E | 50 51 57 5A 5B 5C 5E 5F
61 62 64 65 6A 6B 6C 6D 6E 6F 70 71 72 73 79 | 80 81 82 83 84 85 86 87`.

Note `0x84..0x87` are used in stock data — `SFXBinaryFile.cs` stops its `PLAY_MODEL_ON_TARGET` family at
`0x83`; the family is at least 8 wide (§7.3 explains why it is exactly `program index`).

### 7.3 `0x80+N` = **run chunk program N** (the key opcode)

`0x48b10` @0x48b9e: for `code >= 0x80` it stores `code − 0x80` at slot`+0x14` and picks handler
**0x49170**, which @0x49189 loads `edx = slot[+0x14]` and tail-calls **0xd820** — the function that reads
`ChunkRec->programOffset[edx]` (@0xd906), seeds the MIPS PC/decode-cache pointer (@0xd91e/0xd92a),
returns −1 if the slot is 0, and otherwise calls the interpreter 0xe210.

**Validation (this is the falsifiable one):** for every `0x80+N` in every file, is program N live in the
chunk that the last `LOAD_CHUNK` selected?
* keyed by the `chunkIndex` **field**: **13 failures** (all in `ef381`)
* keyed by the chunk's **table ordinal**: **0 failures across all 372 files**

That simultaneously proves the opcode meaning, the program-table decode, and the `LOAD_CHUNK` key.
Worked example: `ef431`'s single chunk has live programs at **indices 0, 3 and 7** — and its sequence
uses exactly `0x80`, `0x83` and `0x87`.

### 7.4 Low opcodes read directly (the rest keep their C# names as *hypotheses*)

| code | handler | native behaviour |
|---|---|---|
| `0x00` | 0x31aad | **END/HOLD** — rewinds the pointer by 3 (re-executes forever) and notifies the host with `0x73000000` |
| `0x01` | 0x31680 | **WAIT** — `arg1 == 0`: wait `arg2` ticks (`[0x323174] = arg2`); `arg1 != 0`: block while `channelFlag[arg2] != 0` |
| `0x02` | 0x316af | **SET_CHANNEL_FLAG** — `byte[0x323180 + arg1] = arg2` (the array `0x01` waits on) |
| `0x05` | 0x31712 | **LOAD_CHUNK** — `[0x323178] = 0x30bd0(arg1)`; that slot is the implicit 2nd argument of *every* `>= 0x20` opcode |
| `0x29` | 0x3bbd0 | **PLAY_CAMERA** — resolves a camera sub-file through `0x3d800(slot, idx)`; `arg2` selects fixed / random (LCG `0x41c64e6d`, @0x3bc51) / repeat-last |
| `0x2D` | 0x3bf00 | PLAY_SOUND (C# name; sub-file index in `arg1`) |

`SFXBinaryFile.cs`'s other names (e.g. `0x02 = PLAY_CASTER_ANIMATION`) are **not** what the native handler
does and should be treated as unverified until each handler is read.

---

## 8. THE CREATURE PACKAGE (ids 4 + 5) — one header, two payloads

The id-4 and id-5 handlers both read a struct at the **same** pointer `[0x323244]`. Anchoring that struct
at the **start of the id-4 payload** makes every field cohere; anchoring at the id-5 payload yields
garbage. Header (native field reads at 0x3e272 / 0x3e373):

| off | field | corpus check (24 model packages) |
|---|---|---|
| +0x00 s16 | `texOffset` — start of the texture blob | `== 0x180 + 4*motionCount` **24/24** |
| +0x02 s16 | `motionCount` N | 1 … 12 |
| +0x04 s16 | `pageCount` (64×128 16bpp VRAM pages) | |
| +0x06 u16 | `clutRows` (CLUT strip, w = 0x100, VRAM y = 0xe6) | |
| +0x08 u32 | `texBytes` | `== pageCount * 0x4000` **24/24** |
| +0x0c u32 | `clutBytes` | `== clutRows * 0x200` **24/24**; and `texOffset+texBytes+clutBytes <= id4 payload` **24/24** |
| +0x10 u32 | `modelBytes` — size of the id-5 image; DLL keeps `0x50000 − modelBytes` as free space (@0x3e40d) | within one sector of the id-5 payload size **24/24** (`>= max(motionOffset)` 24/24) |
| +0x14 u32 | `firstBlock` — offset into the id-5 image, becomes `Register` arg `[+0x40]` | `== motionOffsets[0]` in **19/24** (the other 5 point slightly earlier) |
| +0x18 | `u16[pageCount]` VRAM page/row selector | |
| +0x30 | `u16[pageCount]` VRAM x word | |
| +0x90 | block handed to `0x15a20(ptr, 1)` | undecoded |
| +0x180 | **`u32[N]` MOTION TABLE** — offsets into the id-5 image, relocated in place (@0x3e3c0) | all in-bounds 23/24 |

`ef227`: `motions = 8`, `pages = 6`, `clutRows = 6`, `texBytes = 0x18000`, `clutBytes = 0xc00`,
textures at file **0x4a1a0**, model image at file **0x63000** (0x27000 B), `modelBytes = 0x26c74`,
motion offsets `0x1293c 0x139ac 0x14c88 0x16204 0x19578 0x1b588 0x1f798 0x24c24`.
**So Bahamut ships 8 animation clips and 6 texture pages, and both are addressable offline.**

### 8.1 A correction to `FINDINGS.md` §2.2

`Hi_RegisterSummonModel` @0x15f32 loads `eax = model[+0x3c]` and stores it at **`SummonData+0x08`**
(@0x15f3f). The id-5 loader sets `model[+0x3c] = psx(header + texOffset)` (@0x3e384-0x3e39c). Therefore
`SummonData+0x08` is a **pointer to the texture blob**, *not* a "modelId … ← managed model arg[+0x3c]"
as FINDINGS states. Likewise `SummonData+0x10` (motion) is initially `resolve(model[+0x180])` = motion
clip 0 (@0x15f42) — consistent with the motion table above.

---

## 9. WHAT IS DECODED / WHAT REMAINS OPAQUE

**Decoded and machine-checked (this round):** the header sector; the chunk/resource table and its exact
walker rule; all 10 resource types + the dead id 10; the sub-file directory; the id-3 image layout,
relocation and program table; the complete sequence-opcode validity map and the `0x80+N` semantics; the
creature package header, texture geometry and motion table.

**Still opaque, in priority order:**

1. **The MIPS program (id 3).** Named, bounded and located — not read. This is where the creature's
   staging lives. Tractable: a 0x5A-opcode decoder already exists in the DLL to check a disassembler
   against, and the HLE library table @0x12358 names the 200 calls the program can make.
2. **Motion-clip and geometry byte formats** (inside the id-5 image). The prior round has the *runtime*
   consumers (`Hi_SetSummonMotion` @0x17a10 reads `frameCount = u16[motion+2]`; the bone pass fn 0x7820),
   so the clip header is one short read away.
3. **The `info` byte** for ids 0/1/9 (a bit-field; `bit 0..3` gated @0x3df46).
4. **The remaining ~50 sequence opcodes' operand semantics** (handlers located, not read).
5. **Header fields +0x0c/+0x90** of the creature package.
6. Per-effect-id special cases hard-coded in native code (§1) — a custom id inherits none of them.

---

## 10. STAGED ROADMAP TO "SUMMONS ARE RE-IMPORTABLE"

| rung | deliverable | gated on | effort |
|---|---|---|---|
| **R1** | **Ship the container parser** (`ef_container.py`) + a `summon-inspect` CLI: table, sections, sub-files, programs, sequence listing | done here | **LOW** |
| **R2** | **Container WRITER** — rebuild a byte-identical `ef###.bytes` from parsed parts (sector re-pack, cursor invariant, `info != 0` rule). Prove by round-tripping all 372 files to byte-identity | R1 | LOW–MED |
| **R3** | **Sequence authoring** — emit/patch the 0x400 stream with the validated opcode map (a linter that refuses the 0x30..0x4F illegal band and the NULL table-B slots is free) | R2 | LOW |
| **R4** | **Texture + CLUT swap** — the creature's 6 texture pages are plain 64×128 16bpp blocks at a known file offset with an exact size formula: a reskin needs no code | R2 | LOW |
| **R5** | **Camera-track authoring** in the sub-file directory (the prior round already parses it, and the clock is validated) | R2 | MED |
| **R6** | **MIPS disassembler for the id-3 image** + a symbol map of the 200 HLE library calls. This turns "opaque" into "readable"; it is also the only honest way to *see* how a stock summon stages its creature | — | MED |
| **R7** | **Geometry/motion decode** in the id-5 image (offsets already known) → export a stock creature to the kit's model pipeline / import a custom one | R6 or R2 | MED–HIGH |
| **R8** | **A minimal hand-written MIPS program** (or a reusable stock program driven by patched data) for a genuinely new summon | R6 | HIGH |

The cheap prize is **R2+R3+R4**: repack + re-sequence + reskin buys real authoring without touching a
single instruction of PS1 code. The pillar's true gate is **R6**.

---

## 11. PROVENANCE

- Every native claim cites `fn@rva` from **read-only** static analysis of the user's own installed
  `FF9SpecialEffectPlugin.dll`. **No DLL was modified or redistributed.**
- The 372 stock `ef###.bytes` were extracted (via the study's own UnityPy recipe) **only** to
  `C:/gd/SCRATCH/summon-format/`; the derived `ef227_sequence.txt` dump also lives there. **No stock
  bytes — geometry, animation, textures, raw container — were written into the repo.**
- Committable artifacts from this slice: **`ef_container.py`** (format parser, no game bytes),
  **`m2_dis.py`** (disassembly helper), and this report. All numbers quoted here are structural
  (offsets, counts, sizes, opcode ids), not content.
