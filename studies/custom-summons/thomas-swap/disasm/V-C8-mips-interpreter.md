# V-C8 — ADVERSARIAL VERIFICATION: "the id-3 image is MIPS R3000A machine code, pre-decoded and interpreted"

**Claim C8** (source `M2-container-format.md` §6.2). **Verdict: CONFIRMED** — and strengthened.
Re-derived from scratch with fresh `refkit` disassembly at the cited RVAs, plus an independent
re-implementation of the resource walker and an empirical decode of all 385 stock id-3 images.

Scripts (this dir, committable — pure analysis, zero game bytes):
`c8_a.py c8_b.py c8_c.py c8_d.py c8_e.py c8_f.py c8_g.py c8_h.py c8_i.py c8_mips.py c8_ctrl.py c8_dis227.py c8_final.py c8_ep.py`.
All RVAs are x64 `FF9SpecialEffectPlugin.dll`, ImageBase `0x180000000`.

---

## 0. Verdict table (each sub-claim independently reproduced)

| # | sub-claim | verdict | my evidence |
|---|---|---|---|
| 1 | fn 0xd1a0 allocates `(size/4 + 1) * 16` | **CONFIRMED** (allocator mis-named) | 0xd1d8-0xd1f9 |
| 2 | it pre-decodes one 32-bit word per 4 bytes into 16-byte records | **CONFIRMED** | 0xd240-0xd24b loop head + 0xd300-0xd342 write-back |
| 3 | fn 0xe210 interprets against a 32-dword register file at `ctx+0xc98+slot*0x80` | **CONFIRMED** | 0xe228-0xe249 |
| 4 | dispatch through a **0x5A-entry** opcode table @0xed18 | **CONFIRMED** (index = `op − 1`) | 0xe270-0xe28b; table size measured 0x168 B = 90×4 |
| 5 | handlers read `s32 rd@+4, rs@+8, rt@+0xc`, implement ADD/AND with the `rd==0` guard | **CONFIRMED** | 0xe28d (ADD), 0xe2b3 (AND), 0xe2d9 (XOR), 0xe2ff (SUB) |
| 6 | register file memset 32 dwords at fn 0xd5d0 @0xd6ab | **CONFIRMED** | 0xd690-0xd6b2 |
| 7 | **the ISA is MIPS R3000A** | **CONFIRMED — decisively** | the DLL's own 99-entry mask/match ISA table @**0x66c70** (§2) + corpus decode (§4) + real prologues (§5) |

**Nothing in C8 is refuted.** Three precision corrections and one strengthening are in §6.

---

## 1. The pre-decoder, fn 0xd1a0 — re-read verbatim

`.pdata` splits this function: entries `0d1a0..0d217` and `0d217..0d36c` (that is why the cited
0xd240 sits "outside" the first range — chained region, not a cold funclet).

```
0d1b7  mov  rax,[rcx+8]                 ; ctxSlot->src (image data pointer)
0d1be  mov  dword [rcx+0x20],0xfffffffc ; PC = -4  (so the first `+=4` yields 0)
0d1c5  mov  [rcx+0x10],rax              ; running source cursor
0d1c9  mov  rcx,[rcx+0x18]              ; previous decode cache
0d1d2  call [operator delete[]]         ; MSVCR120 ??_V@YAXPEAX@Z
0d1d8  mov  eax,[rdi+4]                 ; size  (= headerRel, the code-region length)
0d1db  shr  eax,2                       ; size / 4          <-- ONE RECORD PER 32-BIT WORD
0d1de  inc  eax                         ; + 1
0d1e0  movsxd rcx,eax
0d1e3  mov  eax,0x10                    ; 16 bytes per record
0d1e8  mul  rcx
0d1f2  cmovo rax,-1                     ; overflow guard
0d1f9  call [operator new[]]            ; MSVCR120 ??_U@YAPEAX_K@Z
0d20a  mov  [rdi+0x18],rax              ; decode cache base
0d20e  cmp  dword [rdi+0x20],ecx / je 0d36c   ; empty-image early out
```

Loop body:

```
0d240  add  dword [rdi+0x20],4          ; PC += 4
0d244  mov  rax,[rdi+0x10]
0d24b  mov  r12d,[rax]                  ; fetch ONE 32-bit instruction word
0d24e  mov  eax,[rip+0x59a1c]           ; -> 0x66c70   (first table mask)
0d259  lea  rsi,[rip+0x59a10]           ; -> 0x66c70   (ISA TABLE BASE)
0d268  and  eax,r12d                    ; word & mask
0d26b  cmp  eax,[rsi+4]                 ; == match ?
0d270  mov  eax,[rsi+0x38] / add rsi,0x38 / inc r15d   ; next entry (stride 0x38), index++
0d285  mov  word [rdi+0x30],r15w        ; op id  := matched entry INDEX
0d28a  movzx eax,byte [rsi+0x30] / mov word [rdi+0x32],ax   ; flag byte
...
0d300  add  qword [rdi+0x10],4          ; source cursor += 4
0d317  mov eax,[rdi+0x30] ; add r13,0x10 ; mov [r13-0x10],eax  ; record[0x0] = op|flag
0d322  mov eax,[rdi+0x34] ;              mov [r13-0x0c],eax    ; record[0x4] = operand0
0d32e  mov eax,[rdi+0x38] ;              mov [r13-0x08],eax    ; record[0x8] = operand1
0d335  mov eax,[rdi+0x3c] ;              mov [r13-0x04],eax    ; record[0xc] = operand2
0d33c  cmp [rdi+0x20],[rdi+4] / jne 0d240 ; until PC == size
```

**Sub-claims 1 and 2 confirmed exactly**, including the record layout: `u16 op · u16 flag · s32 op0 ·
s32 op1 · s32 op2` = 16 bytes, `r13 += 0x10` per source word.

---

## 2. ⭐ THE SMOKING GUN — the DLL carries its own ISA decode table @0x66c70

`lea rsi,[rip+0x59a10]` @0xd259 resolves to **RVA 0x66c70**: **99 entries, stride 0x38**, each
`{u32 mask, u32 match, …, u8 flag@+0x30}`, terminated by `mask == 0`. Greedy first match; the matched
**entry index becomes the op id**. Dumped straight out of the file (`c8_f.py`, `c8_i.py`):

| idx | mask / match | this is |
|---|---|---|
| 0 | `ffffffff / 00000000` | **NOP** |
| 1,3,2 | `ffe0003f / 00,02,03` | SLL, SRL, SRA |
| 4 | `ffe007ff / 21` | `move` (ADDU with rs=0) |
| 5,6 | `fc1f07ff / 09`, `fc1fffff / 08` | JALR, JR |
| 7-10 | `ffff07ff / 10,11,12,13` | MFHI, MTHI, MFLO, MTLO |
| 11-14 | `fc00ffff / 18,19,1a,1b` | MULT, MULTU, DIV, DIVU |
| 15-27 | `fc0007ff / 20,21,24,26,06,22,23,27,25,04,2a,2b,07` | ADD, ADDU, AND, XOR, SRLV, SUB, SUBU, NOR, OR, SLLV, SLT, SLTU, SRAV |
| 28-37 | `fc000000 / 20,24,28,2c,30,34,38…` + `ffe00000` | ADDI, ADDIU, SLTI, SLTIU, ANDI, ORI, XORI, `li`×2, LUI |
| 38-49 | `fc000000 / 80,84,88,8c,90,94,98 / a0,a4,a8,ac,b8` | LB LH LWL LW LBU LHU LWR / SB SH SWL SW SWR |
| 50-60 | `08,0c` / `10,14` / `fc1f0000 04010000,04000000,04100000,04110000,18,1c` / `ffff0000 10000000` | J, JAL, BEQ, BNE, BGEZ, BLTZ, BLTZAL, BGEZAL, BLEZ, BGTZ, `b` |
| 61,62 | `fc000000 / e8000000, c8000000` | **SWC2, LWC2** |
| 63,64 | `ffe007ff / 48400000, 48c00000` | **CFC2, CTC2** |
| 65 | `fe000000 / 4a000000` | **COP2 cofun — the GTE command** |
| 66 | `fc00003f / 0d` | BREAK |
| 67-80 | LWCz/SWCz z∈{0,1,3}; `ffff0000` BC0F..BC3T | coprocessor 0/1/3 |
| 81-94 | `ffe007ff / 40,4040,4080,40c0,44…,48000000,48800000,4c…` | MFC0/CFC0/MTC0/CTC0, COP1 moves, **MFC2 (89), MTC2 (90)**, COP3 moves |
| 95-97 | `fe000000 / 42,46,4e` | COP0/COP1/COP3 cofun |
| 98 | `ffffffff / 0000000c` | SYSCALL |

This is a **complete, correctly-masked MIPS R3000A instruction set including the PlayStation GTE
(COP2)**. Nothing else has this shape. Sub-claim 7 is not merely confirmed; it is nailed to the ISA.

---

## 3. The interpreter, fn 0xe210 — re-read verbatim

```
0e228  movsxd rcx,[rcx+0xda0]           ; slot index
0e22f  lea    r15,[rip-0xe236]          ; r15 = 0x180000000 (image base)
0e239  lea    r14,[rsi+0xc98]
0e245  shl    rax,7                     ; slot * 0x80  (= 32 dwords)
0e249  add    r14,rax                   ; R14 = GPR file @ ctx+0xc98+slot*0x80   <-- sub-claim 3 ✔
0e250  shl    rcx,6                     ; slot * 0x40  (per-slot MIPS state block)
0e254  mov    rbx,[rcx+rsi+0xc40]       ; decoded-record pointer
0e25c  add    dword [rcx+rsi+0xc38],4   ; PC += 4
0e264  lea    rax,[rbx+0x10] / mov [rcx+rsi+0xc40],rax   ; record += 0x10   <-- 16-byte stride ✔
0e270  movzx  eax,word [rbx]            ; u16 op
0e273  dec    eax
0e275  cmp    eax,0x59
0e278  ja     0x0ebfb                   ; out of range -> next instruction
0e280  mov    ecx,[r15+rax*4+0xed18]    ; TABLE @0xed18, 4-byte RVA entries, index = op-1
0e288  add    rcx,r15 / jmp rcx
```

`0xed18` measures **0xee80 − 0xed18 = 0x168 = 90 × 4 = 0x5A entries** (it even owns its own `.pdata`
row `0ed18..0ee80`). Every entry read out of the file is an RVA in `0xe28d..0xebfb`, i.e. inside the
handler region — **it is opcode-indexed, sub-claim 4 confirmed**. `0xebfb` is the "next instruction"
continuation; entries `0x42..0x57` all point there = deliberately unimplemented ops.

Handlers, read fresh:

```
0e28d ADD/ADDU : r8=s32[rbx+4] ; test r8d,r8d ; je 0ebfb     <-- the rd==0 ($zero) guard ✔
                 rax=s32[rbx+0xc] ; rcx=s32[rbx+8]
                 edx=[r14+rax*4] ; add edx,[r14+rcx*4] ; [r14+r8*4]=edx
0e2b3 AND      : same shape, `and edx,[r14+rcx*4]`          (claim cited 0xe2c8 = that line) ✔
0e2d9 XOR      : `xor`
0e2ff SUB/SUBU : `sub`, operand order +8 minus +0xc
```

**Cross-check that closes the loop** (independent of any prior artifact): the decode table's index IS
the op id, and the jump table is indexed by `op − 1`, so `table[i] ↔ decode entry i+1`:

| decode entry | instruction | ⇒ jump-table index | value read from file | handler |
|---|---|---|---|---|
| 15 | ADD | 0x0E | `0000e28d` | the add handler |
| 16 | ADDU | 0x0F | `0000e28d` | same (correct: ADD/ADDU differ only in overflow trap) |
| 17 | AND | 0x10 | `0000e2b3` | the and handler |
| 18 | XOR | 0x11 | `0000e2d9` | the xor handler |
| 20 | SUB | 0x13 | `0000e2ff` | the sub handler |
| 21 | SUBU | 0x14 | `0000e2ff` | same |

Six-for-six. Two tables in two different sections agree on MIPS semantics.

Register-file zeroing, fn 0xd5d0 (`c8_g.py`):

```
0d690  mov eax,ebp ; and eax,1 ; movsxd rbx,eax   ; slot = counter & 1
0d69b  shl rsi,7                                   ; slot * 0x80
0d69f  lea rdi,[r14+0xc98] ; add rdi,rsi
0d6a9  xor eax,eax
0d6ab  mov ecx,0x20
0d6b0  rep stosd                                   ; 32 dwords zeroed   <-- sub-claim 6 ✔
```

---

## 4. EMPIRICAL TEST on real files — and the controls that make it mean something

I re-implemented the resource walker from my own reading of fn 0xd390 (`c8_h.py`; the walk hits the
exact file length on **372/372** stock files, so the walk is sound), pulled every **id-3** payload,
computed `headerRel = (payload[0] & 0x0FFFFFFF) − (psxBase & 0x0FFFFFFF)` with
`psxBase = 0x801E7700 + (chunkOrdinal & 1) * 0x5000` (fn 0xd390 @0xd431-0xd44e), and ran **the DLL's
own table** over the code region `[4, headerRel)`:

| population | words | accepted as MIPS |
|---|---|---|
| **id-3 code regions, all 385 images** | 287,337 | **97.95 %** — and **272/385 images at exactly 100.00 %** |
| control: uniform random 32-bit words (n=200k) | 200,000 | 51.83 % |
| control: id-0 VRAM pixel payloads (60 files) | 245,760 | 71.11 % |

`headerRel` was in range for **385/385** images with the ordinal-keyed `psxBase` (using ordinal 0 for
every chunk fails on exactly the 8 second-chunk images — which independently re-confirms the
`+ (ordinal & 1) * 0x5000` rule). The 97.95 % residual is concentrated, not scattered: 272 images are
perfect and two outliers (`ef508` 50.3 %, `ef210` 62.0 %) sit at the random-noise rate, i.e. those
images carry a large embedded **data** blob below `headerRel`. Chance cannot produce 272 whole images
of thousands of consecutive words at 100 %.

---

## 5. The decisive semantic test — real MIPS prologues at the program entry points

Decoding `ef227` (Bahamut) chunk 0, `headerRel = 0x3120`, header words `(0,0)`, one live program at
`+0x9d4` (`c8_dis227.py`):

```
+09d4  27bdfe70  addiu  sp,sp,-400
+09d8  8fa301a0  lw     v1,416(sp)
+09dc  afb30174  sw     s3,372(sp)
+09e0  afbf018c  sw     ra,396(sp)
+09e4  afbe0188  sw     fp,392(sp)
+09e8..0a00      sw     s7,s6,s5,s4,s2,s1,s0  (388,384,380,376,368,364,360)
+0a04  afa60198  sw     a2,408(sp)
+0a08  afa7019c  sw     a3,412(sp)
+0a0c  8cd20010  lw     s2,16(a2)
+0a10  1480000b  bne    a0,zero,+11        <- dispatch on arg0
+0a28  3c02801e  lui    v0,0x801e
+0a2c  24427f48  addiu  v0,v0,0x7f48       -> PSX 0x801E7F48  (inside chunk 0's mapped window)
+0a38  0807a9ed  j      0x801EA7B4         (inside chunk 0's mapped window)
+0a68  0040f809  jalr   v0                 (delay slot filled with the following sw)
```

A textbook MIPS O32 prologue — descending `addiu sp,sp,-N`, an ordered callee-saved spill of
`s0..s7/fp/ra`, argument spills, branch-delay slots filled — and the absolute constants it
materialises land **inside the psxBase window this very image is mapped at**. Chunk 1's program
(`+0x108c`, `addiu sp,sp,-704`) is the same shape.

Corpus-wide: **599** live program entry points across 385 images; **589** begin with
`addiu sp,sp,-N`; the other **10** all begin with `0x14800004` = `bne a0,zero,+4` — a frameless leaf
that dispatches on arg0, exactly the idiom seen at `+0x0a10` above. **599/599 are valid MIPS function
entries.**

---

## 6. Corrections and one strengthening

1. **"mallocs" is imprecise.** The allocator is MSVCR120 `operator new[]` (`??_U@YAPEAX_K@Z`) at
   0xd1f9, and 0xd1d2 releases the previous cache with `operator delete[]` (`??_V@YAXPEAX@Z`). The
   size arithmetic `(size>>2 + 1) * 0x10` is exactly as claimed.
2. **The jump-table index is `op − 1`, not `op`** (`dec eax` @0xe273). So `table[0]` serves op 1, and
   op 0 — which is decode entry 0 = **NOP** (`word == 0`) — is intentionally rejected by the `ja` and
   costs nothing. Any re-implementation must carry the bias.
3. **The decode table has 99 entries but the interpreter only implements 90.** Ops `> 0x5A` (decode
   indices 91-98: COP3 moves, COP0/1/3 cofun, SYSCALL) fall through the `ja`, and jump-table entries
   `0x42..0x57` (decode indices 67-88: LWCz/SWCz and BCzF/T for z∈{0,1,3}) point at the
   next-instruction stub `0xebfb`. **The implemented ISA is MIPS R3000A integer + COP0 moves + the
   full COP2/GTE surface.** That is the real ISA a future authoring path must target.
4. **STRENGTHENING — it is not "MIPS" generically, it is MIPS + the PS1 GTE.** Entries 61-65 and
   89-90 are `SWC2 / LWC2 / CFC2 / CTC2 / MFC2 / MTC2 / COP2-cofun`. The creature's per-frame
   transform is therefore computed **on the emulated Geometry Transformation Engine**, inside the
   effect's own program. That is the mechanical reason the s52 ROOT probe's managed-side transform
   never matched the picture, and it tells R6/R7 exactly what to decode: a GTE-aware disassembler
   plus the COP2 register semantics, not just integer MIPS.
5. **Caveat for R6:** `[0, headerRel)` is **code + embedded data**, not pure code (`ef508`, `ef210`).
   A disassembler must be reachability-driven from the 16 program offsets, not a linear sweep — the
   same linear-desync trap this study already learned on x86.

---

## 7. Provenance

Static, read-only analysis of the user's own installed `FF9SpecialEffectPlugin.dll` (never modified,
never redistributed). The 383 stock `ef###.bytes` were read in place from
`C:/gd/SCRATCH/summon-format/`; **no game bytes were written into the repo** — this report quotes only
structural facts (masks, offsets, counts) and ~50 instruction words of *reverse-engineered* PS1 code
shown as disassembly for the purpose of proving the ISA. The `c8_*.py` scripts are pure analysis code.
