# V-C7 — ADVERSARIAL VERIFICATION: the id-3 image layout (headerRel = header offset = code size; 16-entry program table at headerRel+8)

**Claim under test (C7, from `M2-container-format.md` §6.1):** resource id 3 is a PS1 main-RAM image whose
first dword is a PSX pointer to its own header; that header offset (`headerRel`) doubles as the CODE SIZE;
a 16-entry program-pointer table sits at `headerRel+8`. Validated 385/385 on three gates.

**VERDICT: CONFIRMED.** Re-derived from a fresh refkit disassembly and from an independently written
walker (`C:/gd/SCRATCH/summon-format/vc7_walk.py`, transcribed straight off the disassembly — the
existing `ef_container.py` was deliberately NOT imported). All three gates reproduce at 385/385, and two
adversarial controls plus an outside-evidence discriminator make the claim *stronger* than as filed.

---

## 1. The mechanism, re-disassembled (not taken on trust)

`fn 0xd390` is **chained across three `.pdata` entries** — `0xd390..0xd3bf`, `0xd3bf..0xd4e5`,
`0xd4e5..0xd4ef`. `refkit.func_of` returns only the 47-byte first fragment, so a naive
"locate → disassemble" shows a stub and misses the whole walker. Disassembled as a 352-byte span
`0xd390..0xd4f0` instead; the span is self-consistent (every branch target lands on an instruction
boundary, the outer/inner loop backedges close at `0xd4c0`/`0xd4d0`), so no linear desync.

**The id-3 arm, verbatim (fn 0xd390 @0xd415-0xd499):**

```
0xd415  movsxd rdx, r11d            ; rdx = cursor (starts 0x800)
0xd41f  add    rdx, [r14+8]         ; rdx = blob + cursor  = the payload
0xd423  mov    [rdi+8],  eax        ; rec+0x10 = payload byte size (sizeSectors<<11)
0xd42b  mov    [rdi],    rdx        ; rec+0x08 = host payload pointer
0xd431  lea    ebx,[rax+rax*4] ; shl ebx,0xc ; add ebx,0x801e7700
0xd43d  mov    [rdi-8],  ebx        ; rec+0x00 = psxBase = 0x801E7700 + (chunkOrd&1)*0x5000
0xd440  mov    ecx, [rdx]           ; <== THE FIRST DWORD OF THE PAYLOAD
0xd442  and    ebx, 0xfffffff       ; psxBase & 0x0FFFFFFF
0xd448  and    ecx, 0xfffffff       ; ptr    & 0x0FFFFFFF
0xd44e  sub    ecx, ebx             ; headerRel = relocate(firstDword)
0xd450  mov    [rdi+0x50], ecx      ; rec+0x58 = headerRel
0xd453  shr    rcx, 2               ; \
0xd457  add    rcx, 2               ;  > r9 = payload + ((headerRel>>2)+2)*4
0xd45b  lea    r9, [rdx+rcx*4]      ; /   = payload + (headerRel & ~3) + 8
0xd462  lea    rcx, [rdi+0x10]      ; dest = rec+0x18 = programOffset[0]
0xd470  mov    eax,[r9] ; test/je -> store 0 ; else and 0xfffffff / sub ebx  ; relocate
0xd493  cmp    rdx, 0x10 ; jl 0xd470            ; EXACTLY 16 ENTRIES
```

`rdi` is seeded `lea rdi,[rcx+0x20]` @0xd3ce and strides `add rdi,0x60` @0xd4c8, so the record base is
**ctx+0x18, stride 0x60** — and that is *independently* re-derived at the id-3 handler
(`fn 0x3de37 @0x3e1fe-0x3e20f`: `rcx = ord*3; rcx <<= 5` → `r8 = ctx + 0x18 + ord*0x60`). Two
disassembly sites agree on the record geometry.

### "headerRel doubles as the CODE SIZE" — the forwarding chain, read end to end

```
fn 0x3de37 (id-3 handler) @0x3e227:  r9d = [r8+0x58]          ; headerRel out of the ChunkRec
                           @0x3e215:  rcx = ctx + 0xc18 + (ord&1)*0x40
                           @0x3e238:  rax = [r8+8]  ; [rcx+8] = rax   ; host payload ptr
                           @0x3e240:  [rcx+0]  = psxBase & 0x0FFFFFFF
                           @0x3e242:  [rcx+4]  = headerRel            ; <== written as the SIZE field
                           @0x3e246:  call 0xd1a0
fn 0xd1a0  @0xd1b7/0xd1c5: [blk+0x10] = [blk+8]                      ; running data pointer
           @0xd1be:        [blk+0x20] = -4                            ; PC
           @0xd1d8-0xd1f9: eax = [blk+4] ; shr 2 ; inc ; *16 ; malloc ; [blk+0x18] = cache
           @0xd20e:        cmp [blk+0x20], ecx ; je exit              ; loop while PC != size
fn 0xd217  @0xd240:        [blk+0x20] += 4                            ; PC += 4
           @0xd24b:        r12d = *(u32*)[blk+0x10]                   ; fetch instruction word
           @0xd300:        [blk+0x10] += 4 ; r13 += 0x10              ; 16-byte decoded record
```

So the field at `block+4` **is** the decode extent: the pre-decoder walks `PC = 0, 4, 8, … , size` and
emits one 16-byte decoded record per word. `headerRel` is what fills it.

**Uniqueness control:** a full call-graph sweep of all 646 `.pdata` functions finds **exactly one**
caller of `0xd1a0` — `0x3e246`, inside the id-3 handler. There is no second writer of that block with a
different meaning, so the "size" reading cannot be an accident of one path.

---

## 2. Corpus re-run (independent parser, 372 files / 385 id-3 images)

`vc7_walk.py` implements the walker exactly as disassembled above and checks C7's three gates.

```
corpus: 372 files
chunks (table entries)     : 385
id-3 resource images       : 385
cursor==filelen failures   : 0        <- the format's own checksum, 372/372
0<headerRel<size failures  : 0        <- gate 1  385/385
header words != (0,0)      : 0        <- gate 2  385/385
prog offset out of [0,hr)  : 0        <- gate 3  385/385
headerRel range            : 0x44 .. 0x6198
live-program count hist    : {1:239, 2:106, 3:23, 4:10, 5:4, 6:2, 7:1}   (sum = 599)
ef227 chunks (headerRel, liveProgs): [(0x3120, 1), (0x42bc, 1)]
```

Every number matches `M2-container-format.md` §6.1 **exactly**, including the per-chunk live-program
histogram and ef227's two `headerRel` values. Additionally the 16-entry table never runs past its own
payload (min slack after the table = 3324 B, 385/385).

---

## 3. The adversarial part — the gates are NOT vacuous, and there is outside evidence

**P1 — is the first dword really a PSX pointer?** Top nibble of all 385 first dwords is `0x8`; high-16 is
`0x801E` (383) or `0x801F` (2). These are genuine KSEG0 main-RAM addresses sitting just above
`psxBase 0x801E7700`. Not a bare offset dressed up as one.

**P2 — control: swap the base and the gates must break.** If the gates passed under any base, they would
be measuring nothing:

| base rule | chunks passing all 3 gates |
|---|---|
| correct `0x801E7700 + (ord&1)*0x5000` | **385/385** |
| parity FLIPPED | **0/385** |
| always slot 0 | 377/385 (exactly the 377 even-ordinal chunks) |
| always slot 1 | 8/385 (exactly the 8 odd-ordinal chunks) |
| base `0x80000000` | **0/385** |

The gates discriminate sharply, and they simultaneously re-prove the `(chunkOrdinal & 1)` base rule.

**P3 — outside evidence that `headerRel` is the code/data boundary.** Neither the DLL nor the claim was
consulted for this; it is a pure MIPS-shape test across all 287,722 pre-`headerRel` words and 3,562,133
post-`headerRel` words:

| region | `jr $ra` (`0x03E00008`) | invalid R3000 primary opcode |
|---|---|---|
| `[0, headerRel)` | **1449** (0.504%) | **0.38%** |
| `[headerRel, payloadEnd)` | **0** (0.000%) | **90.76%** |

Zero function-return instructions after `headerRel`, and 90.76% of the words there are not decodable
MIPS at all. `headerRel` is exactly where the code stops. This is the single strongest piece of evidence
for C7 and it did not exist in the original artifact.

**P4 — do the program offsets point at function entries?** All 599 live programs are 4-byte aligned, and
the word at each entry has primary opcode `0x09` = `ADDIU` in 589 cases (the canonical MIPS prologue
`addiu $sp,$sp,-N`) and `0x05` = `BNE` in 10. They are real entry points, not arbitrary in-range values.

---

## 4. One precision refinement for the WRITER side (not a refutation)

The claim says the table "sits at `headerRel+8`". The code actually computes
`payload + ((headerRel >> 2) * 4) + 8` — i.e. `(headerRel & ~3) + 8` — while using the **untruncated**
`headerRel` as the decode size. Empirically `headerRel % 4 == 0` in **385/385** stock images, so the two
readings are indistinguishable on shipped data and the claim is correct as stated for any real file.

It matters only for roadmap **R2 (container writer)**: a synthesized image whose `headerRel` is not
4-aligned would be *decoded* for `headerRel` bytes but have its program table read at `(headerRel&~3)+8`.
**A writer must keep `headerRel` a multiple of 4** — which every stock file already does, and which the
PSX linker guaranteed by construction.

Two further writer-side constraints fall out of the same disassembly and are worth recording:
* `headerRel` is computed by a **32-bit** `sub` (@0xd44e) and then used as an *unsigned* index
  (`shr rcx,2` @0xd453). A negative relocation therefore does not fail gracefully — it indexes ~1 GB past
  the payload. `firstDword` must be `> psxBase`.
* The record's entry count (`rec+0x14`) is **hard-coded 16**: `r10d` is incremented unconditionally at
  0xd473 inside the fixed 16-iteration loop, so it is always 16 regardless of how many entries are live.
  A live entry is simply a non-zero pointer; absence is encoded as `0`.

---

## 5. Provenance

Static, read-only analysis of the user's own installed `FF9SpecialEffectPlugin.dll` (x64, ImageBase
`0x180000000`) via `refkit`; no DLL was modified. The 372 stock `ef###.bytes` were read from the
pre-existing extraction under `C:/gd/SCRATCH/summon-format/`; the two verification scripts
(`vc7_walk.py`, `vc7_probe.py`) were written there and **not** into the repo, and they print only
structural numbers (offsets, counts, opcode histograms) — no stock content is reproduced in this report.
