# V-C5 — ADVERSARIAL VERIFICATION: "2 chunk RAM slots, psxBase = 0x801E7700 + (ord&1)*0x5000, reloc = (ptr&0x0FFFFFFF) − (psxBase&0x0FFFFFFF)"

**Verdict: CONFIRMED** (all three sub-claims independently re-derived; the strongest evidence is *new* and
was not in M2 — see §4/§5). Claim source: `M2-container-format.md` §3.2 / §6.1.

Method: fresh `refkit` disassembly of the user's own installed `FF9SpecialEffectPlugin.dll` at the cited
RVAs (x64, ImageBase `0x180000000`), an **independent re-implementation of the fn 0xd390 walker written
straight off the instruction listing** (I did not call `ef_container.py`), a **32-bit-build cross-check**
(different codegen, same source), and a **whole-corpus run** over all 372 stock `ef###.bytes` in
`C:/gd/SCRATCH/summon-format/`. No game bytes were written into the repo.

---

## 1. The cited site reproduces exactly (x64)

`.pdata` splits the walker into `0xd390..0xd3bf` + `0xd3bf..0xd4e5` + `0xd4e5..0xd4ef` (one logical
function; disassembled per-range, no linear sweep, no desync). Verbatim, the load-address arm:

```
d3b4  mov  ebp, r15d              ; chunkOrdinal = 0
...
d3ce  lea  rdi, [rcx + 0x20]      ; &chunkRec[0].hostPtr   (record base = ctx+0x18)
d3d2  movsx eax, word [r8+2]      ; resourceCount  (chunkIndex at [r8+0] is NEVER read)
d415  movsxd rdx, r11d            ; pos (byte cursor)
d41f  add  rdx, [r14+8]           ; host pointer to the id-3 payload
d423  mov  [rdi+8], eax           ; rec+0x10 = payload size
d426  mov  eax, ebp
d428  and  eax, 1                 ; <-- ordinal & 1
d431  lea  ebx, [rax + rax*4]     ; x*5
d434  shl  ebx, 0xc               ; *0x1000  => x*0x5000
d437  add  ebx, 0x801e7700        ; <-- psxBase
d43d  mov  [rdi-8], ebx           ; rec+0x00 = psxBase
d440  mov  ecx, [rdx]             ; first u32 of the image = an ABSOLUTE PSX pointer
d442  and  ebx, 0xfffffff
d448  and  ecx, 0xfffffff
d44e  sub  ecx, ebx               ; <-- reloc = (ptr&0x0FFFFFFF) - (base&0x0FFFFFFF)
d450  mov  [rdi+0x50], ecx        ; rec+0x58 = headerRel
d453  shr  rcx,2 / add rcx,2 / lea r9,[rdx+rcx*4]   ; = payload + headerRel + 8
d470..d497  16x: v=[r9]; if v: [rcx] = (v&0xfffffff) - ebx  else 0   ; rec+0x18 = program[16]
d4c6  inc  ebp
d4c8  add  rdi, 0x60              ; ChunkRec stride 0x60
d4cc  cmp  ebp, [r14+0x14]        ; chunkCount
```

`ebp` is provably the **table ordinal**: initialised to 0 (`0xd3b4`), incremented once per chunk
(`0xd4c6`), bounded by `chunkCount` (`0xd4cc`), never touched inside the resource loop, and the
`chunkIndex` *field* is skipped without a read at `0xd3d2` (`r8+2` then `r8 += 4`). So the parity key is
the ordinal, not the file's `chunkIndex` word. ✔ as claimed.

## 2. "Exactly 2 slots" — three independent static bounds

| # | site | evidence |
|---|---|---|
| a | ctx ctor **0xd5d0 @0xd60b-0xd62c** | `rcx = ctx+0xc18; edx = 0x40; r8d = 2; call 0x4940c` — the MSVC **vector-constructor-iterator** (ptr, elemSize, **count=2**, ctor): the PS1-interpreter slot array is **2 × 0x40** |
| b | ctx ctor **0xd5d0 @0xd690-0xd6eb / @0xd6f0-0xd717** | `eax = ebp & 1` per-slot init of the 0x80-byte MIPS register file at `ctx+0xc98 + slot*0x80` and the 0x1000-stride blocks at `ctx+0xdb8` / `ctx+0x1d68`, loop `cmp ebp,2; jl`; then `cmp rax,2; jl` zeroing `ctx+0xda8[0..1]` (the live-chunk **record-pointer array**) — the cited `@0xd700 loops i<2` ✔ |
| c | **0x30bd0** (LOAD_CHUNK resolver) | `lea rdx,[rip+0x2f263d]` → **0x32321C**, `lea r8,[rip+0x2f263a]` → **0x323220**: a linear search over a **4-byte / 2-entry s16 table**; `cmp ebx,2; jl ok` else `_wassert(psx_compatibility.cpp:786)` ✔ |

An `xref_index(0x32321a..0x323240)` shows the ONLY references to `0x32321c`/`0x323220` are those two
`lea` bounds; the next referenced datum is `0x323228`. The table really is 2 entries wide.

**Runtime confirmation of the same "2"** — the id-3 stream handler, fn 0x3de37 @0x3e1f0 (read fresh):

```
3e1f0  movzx eax, word [0x32320a]        ; chunk counter
3e1fe  lea  rcx, [rax + rax*2]
3e20b  shl  rcx, 5                       ; ordinal * 0x60
3e204  lea  r8, [r10 + 0x18]             ; ChunkRec base = ctx+0x18   (independently confirms M2 §3.2)
3e208  and  edx, 1                       ; slot = ordinal & 1
3e21c  mov  [r10 + rax*8 + 0xda8], r8    ; the 2-entry LIVE record-pointer array
3e215/3e22b/3e235  rcx = ctx+0xc18 + slot*0x40      ; the 2-element interpreter slot
3e224  edx = rec[0x00] & 0x0fffffff      ; psxBase, segment stripped   -> slot+0x00
3e227  r9d = rec[0x58]                   ; headerRel used AS THE CODE SIZE -> slot+0x04
3e238  rax = rec[0x08]                   ; host payload pointer        -> slot+0x08
3e246  call 0xd1a0                       ; the MIPS pre-decoder
3e265  mov word [0x32321c + rcx*2], ax   ; publish "chunk N is resident in this slot"
```

That is the whole mechanism in one place: **two PSX RAM banks, two resident chunks, `LOAD_CHUNK` asks
0x30bd0 which of the two banks holds the chunk it names, and asserts if it is not resident.**

## 3. 32-bit cross-check (different codegen, same source) — decisive

`refkit.load('x86')`, fn **@0x0c070** is the ChunkRec installer, ordinal in `[ebp+8]`:

```
c07b  imul ebx, edx, 0x54          ; record stride 0x54 (32-bit pointers) vs 0x60 on x64
c07e  and  edx, 1                  ; <-- ordinal & 1
c084  imul edi, edx, 0x5000        ; <-- literal 0x5000, an explicit multiply here
c090  add  edi, 0x801e7700         ; <-- psxBase
c099  mov  [ebx+0x10], edi
c0a1  and  edi, 0xfffffff
c0a7  and  eax, 0xfffffff
c0af  sub  eax, edi                ; <-- the same relocation
c0b1  mov  [ebx+0x60], eax         ; headerRel
c0c0..c0e1  16x program pointers, same (v&0xfffffff)-base, 0 kept as 0
```

The x86 build spells `(ord & 1) * 0x5000` as a literal `imul …, 0x5000` where x64 folded it into
`lea/shl` — two independent codegens of the same source expression. The inverse mapping is also present
(x86 @0xc0f0 `and eax,0x0fffffff; or eax,0x80000000`; x64 0xd87e/0xd883 `and 0x0fffffff; bts eax,31`),
which is what makes the mask the right normalisation: it strips the PSX segment bits (KSEG0 `0x8…`,
KSEG1 `0xA…` both fall in the top nibble) and re-adds `0x80000000` on the way back.

**Constant census (both builds, raw byte search):** `0x801E7700` occurs **exactly once** — x64 `.text`
rva `0xd439` (the immediate of `add ebx,0x801e7700`), x86 rva `0xc092`. `0x801EC700` and
`0x801F1700` occur **zero times** anywhere in either DLL. There is no third base literal to find.

## 4. Corpus test (372 files, my own walker, not `ef_container.py`)

Re-implemented the walker from the listing in §1 (`id==2 → +extra u16 iff info!=0`; `id==3 → record`;
else `pos += size`) and ran it over the whole stock corpus:

* **372/372** files: the running cursor lands **exactly** on the file length.
* **385** id-3 resources. Under `psxBase = 0x801E7700 + (ordinal&1)*0x5000`:
  * `0 < headerRel < payloadSize` — **385/385**
  * the two header words at `payload+headerRel+0x00/+0x04` are `(0,0)` — **385/385**
  * every live `program[k]` lands in `(0, headerRel)` — **385/385** (599 live programs)
* **Falsification run.** Hypothesis "base = `0x801E7700 + ordinal*0x5000`" (no `& 1`) is
  indistinguishable for ordinals 0–1 but differs for ordinal ≥ 2. There are 8 such chunks
  (`ef381` ordinals 2–8, `ef447` ordinal 2): **8/8 FAIL** the header test under the no-parity base and
  **8/8 PASS** under the parity base. The `& 1` is load-bearing and empirically forced.
* **Pointer segment check**: the id-3 first u32 has top nibble `8` in **385/385**; all 599 live program
  pointers have top nibble `8`. They really are absolute PSX KSEG0 pointers, as the claim says.

## 5. NEW — the data itself respects the 0x5000 bank partition

Not in M2, and the single most convincing corroboration that "0x5000" is a **RAM bank size**, not a
curve-fit:

| file class | id-3 payload size | count |
|---|---|---|
| single-chunk effects | **exactly 0xA000** | 367/367 |
| multi-chunk effects (`ef225 ef227 ef251 ef381 ef447`) | **exactly 0x5000** | 18/18 |

A one-chunk effect gets the **whole two-bank window** (0xA000 = 2 × 0x5000); the moment a second chunk
must be co-resident, every image shrinks to **exactly one bank**. And the code regions obey it: max
`headerRel` in multi-chunk files is `0x42BC` (< 0x5000, zero violations), while 3 single-chunk effects
run to `0x6198` — spilling into bank 1, which is safe precisely because slot 1 is never occupied for
them. Shipped data has zero bank collisions.

## 6. Caveats / corrections (none refute C5)

1. **"2 chunk RAM slots" ≠ "2 ChunkRecs".** The `ChunkRec` array at `ctx+0x18` (stride 0x60 x64 /
   0x54 x86) is indexed by the **full chunk ordinal** — 0xd4c8 `add rdi,0x60` runs `chunkCount` times
   and 0x3e1fe/0x3e204 index it by the raw counter; `ef381` fills **9** of them (there is room for 32
   before `ctx+0xc18`). What is 2 is the **PSX RAM bank / resident-chunk slot** set:
   `ctx+0xc18[2]` (0x40 each), `ctx+0xda8[2]` (record pointers), `ctx+0xc98 + slot*0x80` (register
   files) and the `[0x32321c,0x323220)` residency table. `M2-container-format.md` §3.2's phrase
   "2 live slots" attached to the ChunkRec row should be sharpened to say exactly this — a wording
   nit in the artifact, not an error in claim C5.
2. **The `0x0FFFFFFF` mask is never exercised by stock data.** All 984 relocated pointers observed are
   KSEG0 (`0x8…`), so on this corpus `(ptr&0x0FFFFFFF) − (base&0x0FFFFFFF)` is numerically identical to
   `ptr − base`. The mask is right *per the instructions* (re-read at 0xd442/0xd448/0xd44e, 0xd47d/0xd482
   and the x86 twin), and it is what makes a KSEG1 (`0xA…`) pointer relocate correctly — but that path
   is code-derived only. A synthesized container should emit KSEG0 pointers regardless.
3. `psxBase` is **never** a host load address. The host pointer is the payload's position inside the
   already-`memcpy`'d blob (`rec+0x08`); `psxBase` exists only for (a) pointer relocation and (b) the
   `PsxVirtualAddrMapper64` window set up at 0xd820 @0xd896-0xd8bf (`[host−0x20000, host+0x200000]`,
   i.e. a 2 MB PS1 main-RAM view). Overlapping PSX addresses across the two banks would therefore be
   harmless anyway — and §5 shows the data never does it.
4. Not verified here (out of scope, flagged for whoever needs it): the writer of the dword at
   `0x3231f8` used as the residency-table index at 0x3e24b was not found as a rip-relative store; it is
   read as a 0/1-style selector at 0x3e142/0x3e154. Treat "the residency table is indexed by the slot"
   as strongly implied by the 2-entry bound + the assert, not as separately proven.

## 7. Reproduce

Scripts used (scratch, not committed): the walker re-implementation and the corpus/parity/bank runs.
Everything above is re-derivable with:

```
refkit.disasm(pe, 0xd390, 0xd3bf) / (0xd3bf, 0xd4ef)      # the walker
refkit.disasm(pe, 0xd540, 0xd5c3) / (0xd5d0, 0xd736)      # the ctx ctor, count=2
refkit.func_of(fns, 0x30bd0)                              # the 2-entry residency table + assert
refkit.func_of(fns, 0x3de37) -> filter rva 0x3e130..0x3e280   # the id-3 stream handler
refkit.load('x86'); refkit.disasm(pe, 0xc070, 0xc0f0)     # the 32-bit twin
refkit.xref_index(pe, 0x32321a, 0x323240)                 # the table's only two references
```
