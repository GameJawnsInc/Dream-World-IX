# V-C9 — ADVERSARIAL VERIFICATION: the sequence stream @0x400 + the native opcode validity map

**Claim under test (C9, from `M2-container-format.md` §7):** the sequence stream is at file offset
`0x400` (inside sector 0) as 3-byte `(code, arg1, arg2)` records; validity map = `0x00-0x0F`+`0x14`
valid (table @0x31f58) · `0x10-0x1F` assert · `0x20-0x2F` valid (qword table @0x4aff0, 16 real
entries) · `0x30-0x4F` **ILLEGAL** (indexes past table A into `.rdata` strings, no assert) ·
`0x50-0x7F` valid where the qword table @0x4ab80 entry is non-NULL · `>=0x80` valid via fn 0x49170.
All 11,807 opcodes in the 372-file corpus are VALID.

**VERDICT: CONFIRMED.** Every element re-derived independently — fresh refkit disassembly at the cited
RVAs, fresh table dumps, an **x86 cross-build** check, an independent corpus scanner that does *not*
import `ef_container.py`, and an independent UnityPy re-extraction proving the corpus is complete and
genuine. Zero contradictions. Three refinements are recorded in §7 (none refute C9).

Reproduction scripts (this directory, no game bytes): `vc9_a.py` `vc9_b.py` `vc9_c.py` `vc9_d.py`
`vc9_e.py` `vc9_f.py` `vc9_g.py` `vc9_h.py` `vc9_i.py` `vc9_j.py` `vc9_k.py` `vc9_l.py` `vc9_m.py`
`vc9_n.py` `vc9_o.py` `vc9_p.py` `vc9_corpus.py` `vc9_x86.py` `vc9_x86b.py` `vc9_extract_check.py`.

---

## 1. The fetch — 3-byte records, `code/arg1/arg2` order (fn 0x315f1)

`refkit.func_of` puts 0x315f1 in its own `.pdata` range **0x315f1..0x31ce4** (a real body, not a cold
error funclet — it contains the jump-table dispatch and 20+ handler bodies).

```
0x31617  lea  r8, [rip-0x3161e]              ; r8 = IMAGE BASE 0x180000000
0x315f6  lea  r12d,[rcx+3]                   ; r12 = 3   (the record stride)
0x31647  mov  rax,[rip+0x2f1b4a]             ; -> rva 323198   = seqPtr
0x3164e  movzx ecx, byte [rax]               ; code
0x31651  movzx edx, byte [rax+1]             ; arg1
0x31655  movzx ebx, byte [rax+2]             ; arg2
0x31659  add  qword [rip+0x2f1b38], r12      ; -> rva 323198 ; seqPtr += 3
0x31660  cmp  cx, 0x20
0x31664  jge  0x31a69                        ; >= 0x20 -> the "big" path
0x3166a  movsx rax, cx
0x3166e  cmp  eax, 0x14
0x31671  ja   0x316da                        ; 0x15..0x1F -> ASSERT
0x31673  mov  ecx,[r8+rax*4+0x31f58]         ; RVA-relative jump table @0x31f58
0x3167b  add  rcx, r8
0x3167e  jmp  rcx
```

Record size **3**, field order **code, arg1, arg2** — confirmed. The assert stub:

```
0x316da  lea rdx,[rip+0x18cff]   ; -> rva 04a3e0 = "..\..\SpecialEffectCode\psx\source\psx_compatibility.cpp"
0x316e1  lea rcx,[rip+0x18b98]   ; -> rva 04a280
0x316e8  mov r8d, 0x312          ; = line 786
0x316ee  call qword [rip+0x18a7c]; _wassert
```

Matches the cited `psx_compatibility.cpp:786` exactly.

## 2. Jump table @0x31f58 — 21 entries, 0x10-0x13 are the assert (`vc9_b.py`)

Raw dump (RVA-relative dwords, `+imageBase`):

| idx | 00 | 01 | 02 | 03 | 04 | 05 | 06 | 07 | 08 | 09 | 0a | 0b | 0c | 0d | 0e | 0f |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rva | 31aad | 31680 | 316af | 316c0 | 316f9 | 31712 | 3172d | 318a2 | 317b0 | 3181a | 3184b | 31cc5 | 3186f | 31d0d | 31966 | 3198d |

| idx | 10 | 11 | 12 | 13 | 14 | 15 (past end) |
|---|---|---|---|---|---|---|
| rva | **316da** | **316da** | **316da** | **316da** | 31894 | `0xcccccccc` (padding) |

So **0x00-0x0F distinct handlers + 0x14 a distinct handler; 0x10-0x13 = the `_wassert` stub**; entry
0x15 onward is `int3` padding then code, unreachable because of the `ja 0x14` guard. Exactly as claimed.

## 3. The `>= 0x20` path and fn 0x48b10 (`vc9_c.py`, `vc9_d.py`)

```
0x31a69  movsx r8d, dx                       ; arg1
0x31a6d  movsx edx,[rip+0x2f1704]            ; -> rva 323178 = current chunk slot
0x31a74  cmp  cx, si                         ; si = 0x80  (set @0x3160e)
0x31a7a  movsx r9d, bx                       ; arg2
0x31a7e  jge  0x31a83                        ; >= 0x80 : keep the raw code
0x31a80  sub  ecx, 0x20                      ; else    : rebase to code-0x20
0x31a83  call 0x48b10
```

fn **0x48b10** (own `.pdata` range 0x48b10..0x48e66 — a real body):

```
0x48b9e  cmp  ebp, 0x80
0x48ba4  jl   0x48bb5
0x48ba6  lea  eax,[rbp-0x80]
0x48ba9  mov  [rbx+0x14], eax                ; program index = code-0x80
0x48bac  lea  rax,[rip+0x5bd]                ; -> 0x49170
0x48bb3  jmp  0x48bd3
0x48bb5  lea  rcx,[rip-0x48bbc]              ; rcx = IMAGE BASE
0x48bbc  cmp  ebp, 0x30
0x48bbf  jge  0x48bcb
0x48bc1  mov  rax,[rcx+rbp*8+0x4aff0]        ; TABLE A
0x48bc9  jmp  0x48bd3
0x48bcb  mov  rax,[rcx+rbp*8+0x4ab80]        ; TABLE B
0x48bd3  ...
0x48bda  mov  [rbx+0x18], rax
0x48bf8  call qword [rbx+0x18]               ; <-- the indirect call; NO bounds check anywhere
```

`ebp` is the **rebased** code. Therefore raw code → table:

| raw code | ebp | table | index used |
|---|---|---|---|
| 0x20-0x2F | 0x00-0x0F | A @0x4aff0 | 0x00-0x0F |
| 0x30-0x4F | 0x10-0x2F | A @0x4aff0 | **0x10-0x2F — past the table** |
| 0x50-0x7F | 0x30-0x5F | B @0x4ab80 | 0x30-0x5F |
| >= 0x80 | raw | — | fn 0x49170 |

**There is no bounds check on `ebp`.** The only `_wassert` inside 0x48b10 (@0x48b66-0x48b7a) guards an
unrelated 11-slot handle search (`cmp edi,0xb`), not the opcode value. C9's "no assert" is correct.

## 4. Table A @0x4aff0 — exactly 16 entries, then `.rdata` STRINGS (`vc9_e.py`, `vc9_i.py`, `vc9_j.py`)

`_section_for_rva(0x4aff0)` = **`.rdata`** (section `.rdata` = 0x4a000, vsz 0x4794).

| i (raw code) | qword | i (raw code) | qword |
|---|---|---|---|
| 00 (0x20) | 0x…39d60 | 08 (0x28) | 0x…3b0d0 |
| 01 (0x21) | 0x…3b480 | 09 (0x29) | 0x…3bbd0 |
| 02 (0x22) | 0x…3b3e0 | 0a (0x2a) | 0x…3bd10 |
| 03 (0x23) | 0x…3bb80 | 0b (0x2b) | 0x…39e10 |
| 04 (0x24) | 0x…3be40 | 0c (0x2c) | 0x…39dc0 |
| 05 (0x25) | 0x…3bab0 | 0d (0x2d) | 0x…3bf00 |
| 06 (0x26) | 0x…39d90 | 0e (0x2e) | 0x…3bf60 |
| 07 (0x27) | 0x…3a690 | 0f (0x2f) | 0x…3b410 |
| **10 (0x30)** | `0x0000000000001109` | **11 (0x31)** | `0x4948534941524948` = `"HIRAISHI"` |

`read_rva(0x4b070, 64)` = `\t\x11\x00…"HIRAISHI ERROR:\n\n%s\n\x00…Hi_DebugPSGData()\nid:%d cannot u"`.
Index 0x10 and beyond really is the DLL's leftover error-string block. **Table A = 16 entries. Confirmed.**

*Sub-check (the `.pdata`-leaf blindspot):* 5 of the 16 targets (0x39d60, 0x3b3e0, 0x3bb80, 0x39d90,
0x3b410) have no `.pdata` range. `vc9_j.py` disassembles each: all begin with the same handler prologue
`cmp ecx,1 / jne …` as their `.pdata`-covered siblings and are preceded by `cc` padding — genuine leaf
function starts, not mid-function. All 16 entries are real handlers.

## 5. Table B @0x4ab80 — the NULL set, exactly as claimed (`vc9_f.py`)

Real storage runs i = 0x30..0x5F (raw codes 0x50..0x7F), i.e. **0x4ad00..0x4ae7f**. Below 0x4ad00 the
bytes are unrelated data (`fee4f40e…`, not VAs); at i=0x60 (raw 0x80) it is again non-VA data.

NULL raw codes found: **52 53 54 58 59 5d 60 66 67 68 74 75 76 77 78 7d 7e** (17 of them) — **identical**
to the claim's list. Every non-NULL entry lands in `.text`.

Failure mode of a NULL slot: `mov [rbx+0x18], 0` then `call qword [rbx+0x18]` @0x48bf8 → a **null-pointer
indirect call** (crash), not an assert. Same fatal class as the 0x30-0x4F garbage-call.

## 6. `>= 0x80` → fn 0x49170 is a real body (`vc9_i.py`)

`.pdata` range **0x49170..0x4919f** (its own entry; followed by `int3` padding):

```
0x49189  mov  edx,[r10+0x14]      ; the program index stored @0x48ba9
0x49195  call 0x1800d820          ; the ChunkRec->programOffset[] runner
0x4919e  ret
```

Confirmed — a real function, not a cold funclet, and it consumes exactly the `code-0x80` value.

## 7. The stream really is at file offset 0x400

Three independent legs:

**(a) The pointer.** fn 0x31d31 (`.pdata` 0x31d31..0x31f03) @**0x31edb**:
`lea rax,[rip+0x2eedee]` → **rva 0x320cd0**; @0x31ef7 `mov [rip+0x2f129a], rax` → **rva 0x323198** —
the same global fn 0x315f1 dereferences @0x31647.

**(b) The header-sector copy.** fn **0x490d0** @0x490fa-0x49160: `rcx = 0x3208d0`, `rax = 0x3678f0`
(the static blob `SFX_Play` memcpys the caller's `ef###.bytes` into), `edx = 0x10`, loop body copies
`0x80` bytes per iteration (8 × `movups`, `lea rcx,[rcx+0x80]`, `lea rax,[rax+0x80]`, `dec rdx; jne`) —
**0x10 × 0x80 = 0x800 bytes**. So `0x3208d0` = blob[0x000..0x800] and
`0x320cd0 − 0x3208d0 = 0x400` = **file offset 0x400, inside sector 0**. Confirmed.

**(c) No collision with the resource table.** My independent table walker (transcribed from fn 0xd390,
not from `ef_container.py`) over all 372 files: **max table end offset = 0x198**, and the running
sector cursor lands exactly on the file length for **372/372**. The stream at 0x400 never overlaps.

## 8. Corpus scan — independent, complete, genuine (`vc9_corpus.py`, `vc9_extract_check.py`)

The validity map was **built at runtime from the DLL's own three tables** (not hard-coded), then applied:

```
validity map (derived from tables):
  0x00-0x14  {'VALID': 17, 'ASSERT': 4}     ASSERT codes: 10 11 12 13
  0x15-0x1F  {'ASSERT': 11}
  0x20-0x2F  {'VALID': 16}
  0x30-0x4F  {'ILLEGAL': 32}
  0x50-0x7F  {'VALID': 31, 'NULLPTR': 17}
  >=0x80     {'VALID': 128}

corpus: 372 files
total opcodes: 11807   distinct: 56   max ops/file: 216
termination: {'END': 372}
NON-VALID occurrences: 0
distinct codes: 00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0f | 23 24 25 28 29 2a 2b 2c 2d 2e |
                50 51 57 5a 5b 5c 5e 5f 61 62 64 65 6a 6b 6c 6d 6e 6f 70 71 72 73 79 | 80 81 82 83 84 85 86 87
```

**11,807 / 56 distinct / 216 max — all three numbers reproduce to the digit**, the distinct-code list is
character-for-character the one in M2 §7.2, and every file terminates on a real `END` (0x00) *inside
sector 0*. Zero opcodes in the assert holes, zero in the illegal 0x30-0x4F band, zero on a NULL table-B
slot. The claim's own refutation condition is **not met**.

**Corpus integrity (the overfitting / cherry-pick guard).** `vc9_extract_check.py` re-enumerated the
install's `resources.assets` with UnityPy from scratch: **exactly 372 `ef###` TextAssets exist**, so the
corpus is the complete population, not a sample. Three files re-extracted and hashed:

| file | asset size / sha256[:16] | on-disk size / sha256[:16] | |
|---|---|---|---|
| ef000 | 217088 / `419473fc183dcde9` | 217088 / `419473fc183dcde9` | MATCH |
| ef038 | 555008 / `8f71a91b5ea8761c` | 555008 / `8f71a91b5ea8761c` | MATCH |
| ef227 | 823296 / `fe590d00a01d95c6` | 823296 / `fe590d00a01d95c6` | MATCH |

## 9. x86 CROSS-BUILD CORROBORATION (`vc9_x86.py`, `vc9_x86b.py`)

Same source, different codegen — the strongest available independent check.

- **Table A**: the 32-bit DLL's `"HIRAISHI ERROR"` string is at rva 0x36d5c; immediately preceding it
  are **exactly 16** dword `.text` pointers at **0x36d10..0x36d4c** (0x36d50/0x36d54 hold the same
  `0x0c0b0e0d`/`0x12` neighbour constants seen next to the x64 table), then NULLs before that. The
  entry ordering is isomorphic to x64's (entries 0/6/11/12 cluster low, 13/14 highest).
- **Table B**: an exhaustive `.rdata` scan for a 48-dword window whose NULL positions equal the x64 NULL
  set **and** whose non-NULL entries are all `.text` returns **exactly one hit: rva 0x36ae0**
  (`10014be0, 10014c10, 0, 0, 0, 10014c40, …`). Same 48-slot length, **same 17 NULLs at the same
  indices**, in a completely different compilation.

Two independently compiled builds agreeing on both table lengths and on the exact NULL pattern makes an
accidental/overfit reading essentially impossible.

---

## 10. Refinements found while trying to refute (none contradict C9)

1. **There is a SECOND way the sequence pointer gets set — and it does not point at file 0x400.**
   fn 0x31d31 @0x31d6f-0x31d7b: `movsx ecx, word [0x323172]; call 0x31470; mov [0x323198], rax`.
   fn **0x31470** (`.pdata` 0x31470..0x314e5) linear-searches a table based at **rva 0x2208d0** whose
   entries are `{u8 idLow, u8 dl}` followed by `(dl & 0x7f)` records, advancing
   `rbx += (dl & 0x7f)*3 + 2` (@0x3149e-0x314aa) — the id is `idLow + 0x100` when `dl` is negative —
   and returns `rbx+2`, i.e. the first record. **The `*3` stride independently corroborates the 3-byte
   record size** from a completely separate function. It also means C9's phrase should be read as
   "*the boot/primary* sequence stream is at 0x400": the interpreter can be re-pointed at sub-sequences
   held in memory. C9 as written does not claim exclusivity, so this is an addition, not a refutation.
2. **Where those sub-sequences live is NOT yet known — and one obvious hypothesis is REFUTED.**
   `0x2208d0` is **uninitialized `.data`** (`.data` rva 0x4f000, rawSize 0x1a000, virtSize 0x5d3440 →
   0x2208d0 is *past raw* ⇒ zero on disk) — runtime scratch, not a static table. Note
   `0x2258d0 − 0x2208d0 = 0x5000`, the exact `ChunkRec.psxBase` stride (`0x801E7700 + ordinal*0x5000`),
   so these are the two host-side PSX-RAM windows. I tested the natural hypothesis "the sub-sequence
   table is the head of the id-3 payload" by running the fn-0x31470 walker over ef227/ef038/ef000's
   id-3 payloads (`vc9_p.py`): **garbage** (117 / 77 / 28 invalid opcodes). **Refuted — do not build on
   it.** Likewise `0x4f860` (the source of a 0x4200-byte seed copy into 0x2208d0 @0x31b99) is a
   fixed-point-looking table, not a sequence table. Open question, flagged for a later slice.
3. **Two adjacent M2 claims got free confirmation** while I was locating payloads: ef227 chunk 0's id-3
   payload begins `20 a8 1e 80` = PSX pointer `0x801EA820`; `0x801EA820 − 0x801E7700 = 0x3120` — exactly
   M2 §6.2's stated `headerRel` for that chunk. And ef000's id-3 payload word 1 is `0x27bdffd8` =
   `addiu $sp,$sp,-0x28`, the canonical **MIPS R3000A** function prologue — the "it really is MIPS"
   claim survives a spot check.

## 11. Consequences for the roadmap

- The **R3 sequence linter is safe to build exactly as specified**: refuse `0x10-0x1F`, refuse
  `0x30-0x4F`, refuse the 17 NULL table-B codes, allow `0x00-0x0F`/`0x14`/`0x20-0x2F`/non-NULL
  `0x50-0x7F`/`>=0x80`. Both rejection bands fail as *silent indirect calls to garbage or NULL* — a
  crash, not an assert — so the linter is the only thing standing between a hand-authored stream and a
  hard game crash. That is a real, load-bearing deliverable.
- The `>=0x80` band should be linted **against the chunk's live program table**, not accepted blanket:
  fn 0x49170 → 0xd820 returns −1 for an absent program, so a bad `0x80+N` is a silent no-op rather than
  a crash — a worse failure mode for authoring (looks fine, does nothing).
- Any writer must place the stream at **0x400** and keep the resource table under it (stock max 0x198,
  so ~0x268 bytes of headroom) and must terminate with a `0x00`.

## 12. Provenance

Static, read-only analysis of the user's own installed `FF9SpecialEffectPlugin.dll` (x64 and x86); no
DLL was modified. Stock `ef###.bytes` were read only from `C:/gd/SCRATCH/summon-format/` (and
re-extracted there for the hash check); **no game bytes were written into the repo**. All numbers quoted
are structural (offsets, counts, opcode ids).
