# V-C10 — ADVERSARIAL VERIFICATION: sequence opcode `0x80+N` = "run chunk program N"

**Claim under test (C10, from `M2-container-format.md` §7.3).** `0x80+N` means *run program N of the
currently loaded chunk's 16-entry program table*: `0x48b10` stores `code−0x80` and dispatches to
`0x49170`, which reads `ChunkRec->programOffset[N]`, seeds the MIPS PC + decode-cache pointer, returns
−1 when the slot is 0, else calls the interpreter `0xe210`. Zero violations across all 372 stock files.

**VERDICT: CONFIRMED.** Every cited RVA re-disassembled from scratch and every number re-derived from
the stock corpus by an independently written walker. The x86 build — different codegen, same source —
reproduces the *entire* chain at different structure offsets, which rules out a coincidental x64 read.
Two immaterial corrections and two caveats are recorded in §5/§6.

Instruments (this directory): `v_c10_a.py` (per-`.pdata` disassembly of a target), `v_c10_b.py`
(arbitrary RVA range — for the chained/split `.pdata` entries), `v_c10_c.py` (operand-text grep over the
whole per-function disassembly), `v_c10_corpus.py` (independent container walk + `0x80+N` check),
`v_c10_power.py` (discriminating power of the 0-failure result), `v_c10_x86.py` (x86 anchor).
Everything reads the user's own installed DLL / the already-extracted `C:/gd/SCRATCH/summon-format/`
files. Nothing was written outside the scratch dir; no DLL was modified.

---

## 1. The dispatch chain, re-disassembled (x64, ImageBase 0x180000000)

### 1.1 `0x315f1` — the sequence interpreter's fetch (context, not part of C10 but needed for "N")

```
0x3160e  mov  esi, 0x80                     ; the threshold literal
0x31647  mov  rax, [rip+0x2f1b4a]           ; -> 0x323198  seqPtr
0x3164e  movzx ecx, byte [rax]              ; code
0x31651  movzx edx, byte [rax+1]            ; arg1
0x31655  movzx ebx, byte [rax+2]            ; arg2
0x31659  add  [rip+0x2f1b38], r12           ; seqPtr += 3      (r12 = 3, set @0x315f6)
0x31660  cmp  cx, 0x20 ; jge 0x31a69        ; the >= 0x20 path
```
`.pdata` covers `0x315c0..` (the function is entered mid-body by a `dec ecx` chain); the fetch site
is exactly as cited. The seq pointer is armed at `0x31edb`: `lea rax,[rip+0x2eedee]` → **0x320cd0**,
stored to **0x323198** @0x31ef7. `0x490d0` @0x49110 copies `blob[0..0x800]` (16 × 0x80 SSE) to
**0x3208d0**, so `0x320cd0 = 0x3208d0 + 0x400` ⇒ **the sequence stream really is at file offset 0x400.**

### 1.2 `0x31a69` — the `>= 0x20` router

```
0x31a69  movsx r8d, dx                      ; arg1
0x31a6d  movsx edx, word [rip+0x2f1704]     ; -> 0x323178  curChunkSlot
0x31a74  cmp   cx, si                       ; si = 0x80
0x31a7a  movsx r9d, bx                      ; arg2
0x31a7e  jge   0x31a83
0x31a80  sub   ecx, 0x20                    ; only for code < 0x80
0x31a83  call  0x48b10
```
⇒ `0x48b10(code>=0x80 ? code : code−0x20, curChunkSlot, arg1, arg2)`. Cited form reproduced verbatim.

### 1.3 `0x48b10` @0x48b9e-0x48bb3 — the `0x80` strip and the handler pick

```
0x48b43  lea   rbx, [rip+0x2da72e]          ; -> 0x323278  task slots, stride 0x20, 11 entries
...      (linear search for a free slot: cmp word [rbx+4], si / add rbx,0x20 / cmp edi,0xb)
0x48b99  mov   word [rbx+8], r14w           ; = curChunkSlot   (arg2 of 0x48b10)
0x48b9e  cmp   ebp, 0x80                    ; ebp = movsxd(code)
0x48ba4  jl    0x48bb5
0x48ba6  lea   eax, [rbp-0x80]              ; N = code - 0x80
0x48ba9  mov   dword [rbx+0x14], eax        ; slot->N
0x48bac  lea   rax, [rip+0x5bd]             ; 0x48bb3 + 0x5bd = 0x49170   <-- the handler
0x48bb3  jmp   0x48bd3
0x48bda  mov   [rbx+0x18], rax              ; slot->handler
0x48bf8  call  qword [rbx+0x18]
```
**Cited site exact.** The `< 0x80` arm below it (`cmp ebp,0x30` → table `0x4aff0` or `0x4ab80`) is
§7.2's business, untouched here.

### 1.4 `0x49170` — 47 bytes, a real body (not a cold funclet); `.pdata [0x49170..0x4919f)`

```
0x49174  mov  rax, [rsp+0x70]      ; 5th arg
0x49179  mov  r10, r9              ; r9 = the task slot
0x4917c  mov  [rsp+0x30], rax
0x49181  mov  [rsp+0x28], r9       ; slot -> 6th param of 0xd820
0x49186  mov  r9, rdx
0x49189  mov  edx, dword [r10+0x14]  ; <-- N, from the slot
0x4918d  mov  [rsp+0x20], r8
0x49192  mov  r8d, ecx
0x49195  call 0xd820
0x4919e  ret
```
**Cited site exact.** (It is a `call`+`ret`, not literally a tail-`jmp`; immaterial.)

### 1.5 `0xd820` @0xd906-0xd93f — the launcher

```
0xd841  mov   rbx, [rsp+0x68]            ; 6th param = the task slot
0xd849  movsx eax, word [rbx+8]          ; curChunkSlot
0xd854  movsxd rbp, edx                  ; N
0xd857  and   eax, 1                     ; -> 0/1
0xd85d  mov   [r14+0xda0], eax           ; ctx->curSlot     (r14 = *(void**)0x3678e0)
0xd866  mov   rcx, [r14+rax*8+0xda8]     ; ChunkRec* for that slot
...
0xd8f3  movsxd rdx, dword [r14+0xda0]
0xd8fa  mov   rax, [r14+rdx*8+0xda8]     ; ChunkRec*
0xd902  shl   rdx, 6                     ; per-slot block stride 0x40
0xd906  mov   r8d, dword [rax+rbp*4+0x18]   ; <-- programOffset[N]   (base +0x18, stride 4)
0xd90b  mov   eax, r8d ; shr rax,2 ; shl rax,4   ; (off/4)*16 = decoded-record index
0xd916  add   rax, [rdx+r14+0xc30]       ; + decode-cache base
0xd91e  mov   [rdx+r14+0xc40], rax       ; cache pointer
0xd926  lea   eax, [r8-4]
0xd92a  mov   [rdx+r14+0xc38], eax       ; PC = off - 4
0xd932  test  r8d, r8d
0xd935  jne   0xd93c
0xd937  or    eax, 0xffffffff            ; RETURN -1 when the slot is 0
0xd93a  jmp   0xd957
0xd93c  mov   rcx, r14
0xd93f  call  0xe210                     ; the interpreter
```
**Every clause of the cited evidence reproduced, byte for byte.** `0xe210` independently checked
(@0xe250-0xe288): it consumes exactly the two fields `0xd820` seeds — cache ptr `ctx+0xc40`, PC
`ctx+0xc38` — advances `PC += 4` / `cache += 0x10`, reads `u16 op = [rbx]`, bounds-checks `op−1 <= 0x59`
and jumps through the 0x5A-entry table @0xed18 over the register file at `ctx+0xc98`. Consistent.

### 1.6 "16-entry program table" — from the builder, not from a guess

`0xd390` (the resource-table walker; its `.pdata` entry stops at 0xd3bf — the known split-entry
blind spot — so the body was disassembled as a raw range) id-3 arm @0xd415-0xd499:

```
0xd431  lea ebx,[rax+rax*4] ; shl ebx,0xc ; add ebx,0x801e7700   ; psxBase = +(ord&1)*0x5000
0xd440  mov ecx,[rdx]      ; the image's first u32 (a PSX pointer)
0xd442/0xd448/0xd44e  headerRel = (ptr & 0xfffffff) − (psxBase & 0xfffffff)
0xd450  mov [rdi+0x50], ecx                     ; ChunkRec+0x58
0xd453  shr rcx,2 ; add rcx,2 ; lea r9,[rdx+rcx*4]   ; = payload + headerRel + 8
0xd462  lea rcx,[rdi+0x10]                      ; ChunkRec+0x18  <- programOffset[]
0xd470..0xd497  16 iterations (cmp rdx,0x10; jl), 0 -> 0, else (p & 0xfffffff) − psxBaseLow
```
So the table is **exactly 16 u32 at ChunkRec+0x18**, sourced from `headerRel+8` in the id-3 payload.

### 1.7 "currently loaded chunk" — the selector really is LOAD_CHUNK's

* `0x05` handler @0x31712: `movsx ecx,dx` (arg1) → `call 0x30bd0` → `mov word [rip+0x2f1a50], ax` = **0x323178**.
* `0x30bd0`: linear search of the **2-entry** u16 table at **0x32321c** (`lea rdx,[rip+0x2f263d]`→0x32321c,
  `lea r8,[rip+0x2f263a]`→0x323220), returns the matching **index**; `cmp ebx,2 / jl` else `_wassert`.
* `0x3de37` @0x3e1f0-0x3e265 fills that table with the **id-3 load counter** (`[0x32320a]`), and
  @0x3e21c sets `[ctx + (counter&1)*8 + 0xda8] = ctx + 0x18 + counter*0x60` — i.e. the pointer array
  `0xd820` indexes points at `ChunkRec[loadCounter]`. `0xd5d0` @0xd6f0-0xd717 nulls both entries at init.

⇒ the "currently loaded chunk" is the chunk whose **id-3 load ordinal** equals LOAD_CHUNK's `arg1`,
resident in one of **two** record slots (`ordinal & 1`). C10's wording is right; §3 below shows the
static "table ordinal" model is exactly equivalent on stock data.

---

## 2. x86 CROSS-CHECK — same source, different codegen, same semantics

Anchored on the only occurrence of the immediate `0x801E7700` in the 32-bit build (`.text` @0xc092).

| element | x64 | x86 | agreement |
|---|---|---|---|
| id-3 record builder | inlined in `0xd390` @0xd415 | **its own fn `0xc070`** | same math |
| ChunkRec stride | 0x60 | **0x54** | different — irrelevant |
| `programOffset[]` | rec+0x18 | rec+0x20 (`lea ecx,[ebx+0x20]` @0xc0ac) | different offset |
| table length | `cmp rdx,0x10` @0xd493 | `cmp edx,0x10` @0xc0de | **16 = 16** |
| table source | payload+headerRel+8 | `lea esi,[ecx+8]`+`lea esi,[esi+eax*4]` (eax=headerRel>>2) | identical |
| relocation | `(p&0xfffffff)−psxBaseLow`, 0→0 | @0xc0c7-0xc0d2 identical | identical |
| id-2 extra gate | `info != 0` @0xd4ab | `test ecx,ecx; je` @0xc047 (ecx = `s8[esi+1]`) | identical |
| **`code−0x80` + handler pick** | @0x48ba6-0x48bac | **@0x34f35-0x34f46**: `cmp eax,0x80 / jl / add eax,-0x80 / [esi+0x18]=0x10035360 / [esi+0x14]=eax` | **same slot offsets +0x14/+0x18** |
| handler | `0x49170` reads `[r10+0x14]` | `0x35360` pushes `[eax+0x14]` then `call 0xc3f0` | **same +0x14** |
| launcher | `0xd820` @0xd906 `[rax+rbp*4+0x18]` | `0xc3f0` @0xc459 `[ecx+eax*4+0x10]` (N = `[ebp+8]`) | same read |
| PC / cache seed | PC=off−4 @0xd926; cache=(off>>2)<<4 + base @0xd90e | `lea eax,[esi-4]` @0xc476; `shr 2 / shl 4 / add` @0xc462 | identical |
| −1 on empty slot | `or eax,0xffffffff` @0xd937 | `or eax,0xffffffff` @0xc484 | identical |
| interpreter call | `0xe210` @0xd93f | `0xcb70` @0xc491 | identical shape |

An accidental misread of the x64 stream would not survive this. **The mechanism is real.**

---

## 3. INDEPENDENT CORPUS RE-DERIVATION (`v_c10_corpus.py`)

A parser written only from §1's disassembly (not from `ef_container.py`), over all
`C:/gd/SCRATCH/summon-format/ef*.bytes`:

```
files: 372
cursor==filelen:                     372/372
chunks total: 385      chunks with >1 id-3 resource: 0
sequences terminating in END(0x00):  372/372
id-3 header words (0,0) violations:  0
live program offsets outside code:   0
live-program-count histogram: {1:239, 2:106, 3:23, 4:10, 5:4, 6:2, 7:1}
total opcodes 11807, distinct 56
0x80+ histogram: 0x80:427 0x81:148 0x82:44 0x83:55 0x84:18 0x85:9 0x86:2 0x87:20   (723 total)
0x80+N VIOLATIONS keyed by TABLE ORDINAL:  0        <-- the falsifiable test
0x80+N before any LOAD_CHUNK: 0
ef431 chunk0 headerRel=0x800  live programs=[0,3,7]; sequence 0x80+ codes = 0x80,0x83,0x87
ef227 chunk0 headerRel=0x3120 live=[0]; chunk1 headerRel=0x42bc live=[0]; LOAD_CHUNK args [0,1]
```
Independently reproduces §6.1's live-program histogram, §7.2's 11,807 / 56 / `0x84..0x87`-are-used,
§2's `ef227` headerRels, and the `ef431` worked example **exactly**.

**Residency check.** Across the whole corpus, `LOAD_CHUNK` args are `0,1,2,…` strictly monotone with no
gaps (histogram `{0:372, 1:5, 2:2, 3:1, 4:1, 5:1, 6:1, 7:1, 8:1}`; 0 non-monotone cases), so the
requested chunk is always one of the two most-recently-loaded ⇒ the static "all chunks resident" model
used above is exactly equivalent to the runtime 2-slot model on stock data. (For a *writer*, that is a
constraint to honour, not a freedom: see §6.)

---

## 4. DISCRIMINATING POWER — is 0-failure meaningful? (`v_c10_power.py`)

A 0-failure result is worthless if any mapping scores 0. It is not:

```
0x80+N opcodes: 723   (with N>0: 296)      chunks with a program table: 385
identity   N -> N          failures =   0
shift +1   N -> (N+1)%16   failures = 513
shift -1   N -> (N-1)%16   failures = 489
reverse    N -> 15-N       failures = 723
collapse   N -> 0          failures =  21
200 random permutations of 0..15: min 102, median 666, max 717; ZERO scored 0
chunks referenced by 0x80+N: 385   used-N set == live-program set: 377   used ⊂ live: 8   neither: 0
```

The bijection line is the strongest single result: for **377 of 385** stock chunks the set of `N` values
the sequence uses is *exactly* the set of non-zero slots in that chunk's 16-entry table (the other 8 use
a strict subset). That is not a fit — it is the same object seen from two independent sides of the file.

---

## 5. CORRECTIONS TO THE SOURCE ARTIFACT (neither refutes C10)

1. **"13 failures under the `chunkIndex` field key" did not reproduce.** I measured **3** under my
   handling of an unmatched arg. `ef381`'s `LOAD_CHUNK` args run `0..8` while its `chunkIndex` fields are
   only `{0,1}`, so most args match *no* chunk and the failure count is whatever the modeller decides an
   unmatched arg means (11 if unmatched counts as a failure, 3 with a fall-back-to-chunk-0). **The
   direction and the conclusion reproduce exactly**: ordinal key 0 failures, field key non-zero, all in
   `ef381`. This is a §3.3 side-number, not part of C10's statement.
2. **`0x49170` ends `call 0xd820; add rsp,0x48; ret`, not a tail-`jmp`.** Cosmetic.

## 6. CAVEATS FOR ANYONE BUILDING ON THIS (open, unverified here)

* **The handler is invoked TWICE per opcode.** `0x48b10` calls `qword [rbx+0x18]` at **0x48bf8**
  (`ecx = 0`) and again at **0x48d1a** (`ecx = 1`, `edi` set to 1 @0x48b8a), with a PSX-memory
  allocation in between gated on the first call's return. `0x49170` never reads that phase argument
  (`rcx` is dead on entry to `0xd820` — it is overwritten @0xd874 before any use); `0xd820` forwards it
  only as `edx` to `0xde90`. Read literally, a single `0x80+N` opcode enters `0xe210` twice. **Not
  investigated.** Anyone modelling execution order (R3/R8 in the M2 roadmap) must resolve this before
  trusting a per-opcode "runs once" mental model.
* **Only two chunk records are resident.** `psxBase` alternates on `ordinal & 1`, the pointer array at
  `ctx+0xda8` has 2 entries, and `0x30bd0` `_wassert`s if the arg matches neither. A synthesized
  container that emits `LOAD_CHUNK` out of load order — or references a chunk more than one load in the
  past — will assert or silently run the wrong program. Stock data never does (§3).
* `0x80+N` is bounded by the table at **16**, but stock data only ever exercises `N ≤ 7`. Slots 8..15
  are code-legal and completely unexercised.

## 7. PROVENANCE

Read-only static analysis of the user's own installed `FF9SpecialEffectPlugin.dll` (x64 and x86) and of
`ef###.bytes` already extracted to `C:/gd/SCRATCH/summon-format/`. No DLL was modified or produced. No
stock bytes were written into the repo — the committable artifacts are the six `v_c10_*.py` analysis
scripts and this report, which quote only structure (RVAs, offsets, counts).
