# R1 — THE DISASSEMBLER (reachability-driven MIPS R3000A + GTE over resource id-3)

**Status: ★ DONE. 8/8 gates pass, 41/41 tests pass.** The effect PROGRAM — the last opaque layer of the
`ef###.bytes` container, and the layer that actually drives a summon's choreography — is now readable
offline. `385/385` id-3 images walk from their `599` live program entries with **zero invalid
instructions in reachable code** and **zero unresolved call targets**.

Two unknowns R0 flagged as risks were closed **statically**, and one of them turned out not to need the
runtime probe D2 budgeted for it at all (§4).

---

## 1. What shipped

| file | what it is |
|---|---|
| `tier_r_disasm.py` | the disassembler: ISA mirror + decoder + reachability walker + constant tracker + call classifier + switch-table recovery + listing writer + CLI |
| `test_tier_r_disasm.py` | 41 pytest cases. Runs with **no corpus and no game install** (synthesises tiny id-3 images with a small MIPS encoder); corpus/DLL cases skip on absence |
| `r1_gates.py` | the gate runner — prints G0…G7 with numbers and PASS/FAIL, exit code 0/1 |
| `R1-DISASSEMBLER.md` | this report |

Listings of stock images are written **only** to `C:\gd\SCRATCH\summon-format\disasm-r1\`
(386 files, ~15 MB). Nothing from them is committed. → §9.

```
py studies/custom-summons/tier-r/r1_gates.py                      # 8/8, exit 0
py -m pytest studies/custom-summons/tier-r/test_tier_r_disasm.py -q   # 41 passed
py studies/custom-summons/tier-r/tier_r_disasm.py --isa-check     # mirror vs the live DLL, 99/99
py studies/custom-summons/tier-r/tier_r_disasm.py --corpus --listing C:\gd\SCRATCH\summon-format\disasm-r1
```

---

## 2. The design, as built

**The ISA is the DLL's, not a spec's.** `tier_r_disasm.ISA` is a 99-row mirror of the decode table at
x64 RVA `0x66c70` (stride `0x38`), in table order, and `--isa-check` re-reads the live table and
compares — mask, match, **operand-extractor list**, and flag — 99/99. Greedy first match; the matched
index *is* the interpreter's opcode id (`fn 0xd1a0` @`0xd24e`-`0xd285`).

**Operands are the DLL's too.** Each table row carries up to four function pointers at `+0x10`; they are
eleven six-byte thunks at `0xd0d0..0xd180`, transcribed verbatim into `Ex`:

| thunk | body | meaning |
|---|---|---|
| `0xd0d0` / `0xd0e0` / `0xd0f0` | `shr 0x15/0x10/0x0b ; and 0x1f` | `rs` / `rt` / `rd` |
| `0xd100` / `0xd110` | `shr 6 ; and 0x1f` / `and 0xfffff` | `shamt` / 20-bit `code` |
| `0xd120` / `0xd130` | `movzx dx` (+ sign-extend) / `movzx dx` | signed / unsigned imm16 |
| `0xd140` | `and 0x3ffffff ; shl 2` — then the caller's `sub eax,[rdi]` @`0xd2d0` | **J target, relocated to an image offset** |
| `0xd150` | `and 0x1ffffff` | **the 25-bit COP2 cofun** |
| `0xd160` | `sign-extend imm16 ; inc ; lea eax,[rcx+rax*4]` | **branch target = PC + 4·(simm+1)**, image-relative |
| `0xd180` | `sign-extend imm16 ; sar 0x15 ; and 0x1f -> *r8` | load/store `offset(base)` — **two** operand slots |

That is why the decoder emits image-relative branch/jump targets directly: the shipping pre-decoder does
the relocation itself, and the interpreter consumes exactly those numbers.

**Delay slots are a column of that table, not our opinion.** `flag == 1` on exactly
`{jalr, jr, j, jal, beq, bne, bgez, bltz, bltzal, bgezal, blez, bgtz, b, bc0f…bc3t}` (indices
5,6,50-60,73-80). The interpreter reads that flag at `0xebfb` (`cmp word [rbx+2],0 / jne 0xecdf`): when
it is set, the pending branch is **not** consumed, so the next instruction retires first. The branch
handlers only *park* the target (`0xe892`: `[ctx+rax+0x2dc8]=1`, `[ctx+rax*4+0x2dcc]=target`). The walk
models that literally.

**Reachability, never a linear sweep** (FORMAT §2.6's own law). Seeded from
`ef_container.ChunkImage.program_offsets`; follows fall-through, both branch arms, in-image `J`/`JAL`,
the `off+8` return of a call, and the delay slot of every transfer; terminates a path at `jr` (a `$ra`
return, or an indirect whose target pass 2 classifies). Everything never entered is reported as data, not
decoded.

**Two passes that feed each other.** Pass 2 is an intra-procedural constant tracker over a basic-block
CFG (call edges cut, ⊥ distinguished from ⊤). It resolves HLE call targets, HLE argument constants, and
compiled `switch` jump tables — and any table targets it recovers are folded back in as new seeds and the
walk repeats to a fixpoint. That single feedback loop is what takes `ef227` chunk 0 from **27.2 % to
96.0 %** coverage and chunk 1 from **12.0 % to 99.8 %**.

---

## 3. The gate table

| gate | verdict | headline numbers |
|---|---|---|
| **G0** ISA mirror == the DLL's live table | **PASS** | 99 live / 99 mirror / **0 mismatches**, including the extractor lists and the flag column |
| **G1** walk completes, 0 invalid in reachable code | **PASS** | **372 files · 385 images · 599 live programs**; 239,956 instructions decoded; **0** invalid words; 0 transfers landing outside `[0,headerRel)`; 0 walker anomalies |
| **G2** coverage + the embedded-data canary | **PASS** | coverage min 23.1 % / **median 98.6 %** / max 100 %; 252/385 images ≥ 95 %. `ef508` reachable 28.1 % with a linear score of 50.3 %; `ef210` 45.0 % vs 62.0 % — and their unreached mass is **13,380 B / 13,500 B data-shaped** against 252 B code-shaped each, with **0 invalid in reachable code** |
| **G3** call-target classification | **PASS** | in-image **1,015** · HLE **14,190** · polymorphic-HLE **11** · **UNRESOLVED 0**; 138 distinct HLE ops spanning **0…215**, the dispatcher's exact bound |
| **G4** prologue census | **PASS** | **589 / 599** entries are `addiu sp,sp,-N` — `c8_ep.py` reproduced exactly; the other **10** are all `bne $a0,$zero,+4/+5` |
| **G5** delay-slot modelling | **PASS** | 30,482 transfers in reachable code, **30,482** delay slots decoded, 0 failures; unit tests on synthesised MIPS + a corpus spot proof |
| **G6** GTE cofun layout validated against the DLL | **PASS** | the DLL implements **exactly 6** cofun words; the corpus uses **exactly the same 6** (261 `cop2` instructions) — set **equality**, not merely subset |
| **G7** the HLE sentinel-table base | **PASS** | **`0x21FF78` = the sentinel table**, `0x21FF7C` = the camera struct, `0x21FF70` excluded; confirmed independently from the program side |

---

## 4. G7 — the HLE base, settled statically (and the probe it made unnecessary)

D2 §1.2 left this open with an explicit warning ("an off-by-one reading would put the table at
`0x21FF70`… Cost: one probe row. Do not guess"). It is decidable from the DLL alone.

`fn 0x30c20` publishes five host pointers as PSX addresses through `call 0x12940(bankTable 0x576a10,
hostPtr)`. The block is a software pipeline — each group loads the **next** pointer, stores the
**previous** call's result, then calls — and it **ends on a store with no trailing call**, which pins the
phase with nothing left to reason about:

```
0x30cb5 lea rdx,->0x323170 ; 0x30cd0 call            (no store before the first call)
0x30cd5 lea rdx,->0x3231f0 ; 0x30ce3 mov [0x21FF68] ; 0x30ce9 call
0x30cee lea rdx,->0x323270 ; 0x30cfc mov [0x21FF6C] ; 0x30d02 call
0x30d07 lea rdx,->0x68250  ; 0x30d15 mov [0x21FF70] ; 0x30d1b call     <- 0x68250 = the sentinel table
0x30d20 lea rdx,->0x69730  ; 0x30d2e mov [0x21FF78] ; 0x30d34 call     <- stores psx(0x68250)
                             0x30d39 mov [0x21FF7C]                    <- stores psx(0x69730)
```

Instruction bytes, read back from the user's own installed DLL by `r1_gates.py` (x64, ImageBase
`0x180000000`):

```
030d07  488d1542750300   lea  rdx, [rip + 0x37542]      -> RVA 0x68250   (216 dwords 0xFF000000|i)
030d1b  e8201cfeff       call 0x180012940               -> eax = psx(0x68250)
030d20  488d15098a0300   lea  rdx, [rip + 0x38a09]      -> RVA 0x69730   (the camera struct)
030d2e  890544f21e00     mov  dword ptr [rip+0x1ef244], eax  -> RVA 0x21FF78
030d34  e8071cfeff       call 0x180012940               -> eax = psx(0x69730)
030d39  89053df21e00     mov  dword ptr [rip+0x1ef23d], eax  -> RVA 0x21FF7C
```

**VERDICT — `0x21FF78` holds the HLE sentinel table's PSX base; `0x21FF7C` holds the camera struct's.**
The off-by-one alternative is not merely unlikely, it is **excluded**: `0x21FF70` is written at `0x30d15`
with `psx(0x323270)`, a third object entirely.

**And the program side confirms it independently.** An xref sweep over the whole image finds **five
writers and zero readers** of `0x21FF68..0x21FF7C` in x64 code — so that range is *emulated PSX RAM*, and
its consumer is the MIPS program. The five fields sit at `+0x00, +0x04, +0x08, +0x10, +0x14`, and every
effect program loads its call table with **`lw $rX, 0x10($sysStruct)`** — precisely the field
`0x21FF78 = 0x21FF68 + 0x10` this disassembly assigns to the sentinel table. Two independent sides of the
boundary agree. **No runtime probe row is required** (D2 §4.5 item 3 is closed at zero cost).

---

## 5. The HLE call idiom — the op index is recoverable without the base at all

D2 assumed naming a native call needed the table's runtime base. It does not. The programs reach a host
routine through a **function-pointer table**, and the *load offset* carries the op:

```
lw   $t8, 0x10($sysStruct)     ; the sentinel table's PSX base
...
lw   $v0, (4*op)($t8)          ; the word loaded IS 0xFF000000|op
jalr $v0                       ; the interpreter traps it at fn 0xec31 -> fn 0xee80(ctx, op)
```

So `op = loadOffset / 4`, statically, forever. Discrimination evidence that this is not a coincidence:

* **Range closure.** Every one of the 14,190 recognised sites has a 4-aligned offset in
  `[0, 216·4)`; the observed op range is exactly **0…215**, the dispatcher's own bound
  (`0xee98: cmp edx,0xd7 / ja`). Not one site falls outside.
* **A falsifiable semantic test.** The 12 ops `M3-opcode-table.json` names are all summon-creature
  routines. Effects carrying a creature model package: **24 / 372 = 6.5 %** of the corpus. Effects whose
  program calls *any* named summon op: **20, of which 17 carry a creature — 85 %**, against a 6.5 %
  chance level. If `op = loadOffset/4` were wrong, the named ops would scatter uniformly.
* **A prediction that had to hold and does.** `op 23 Hi_RegisterSummonModel` is called by **zero**
  programs — correct, because the *host* registers the model (the id-5 handler hands the package to it at
  `fn 0x3de37` @`0x3e447`). A mis-keyed mapping would have sprayed op 23 across the corpus.

**11 sites are polymorphic** — one `jalr` two paths reach with two different table slots. They are not
failures and are not left unnamed: the lattice keeps both, e.g. `ef211:c0 +0x1720` is
`Hi_SetSummonMotFrame | Hi_ModifySummonModelAbr`. Unresolved: **0**.

`$a0-$a3` are statically known at **19.5 %** of HLE argument slots (11,069 / 56,804) — the rest come from
memory or from a caller's frame, which is R2's business.

---

## 6. G6 — the GTE, and what FF9's GTE surface actually is

The COP2-cofun handler is dispatch-table slot 64 (decode index 65, biased by the interpreter's
`dec eax`) → `fn 0xeacd`. **It does not field-decode.** It compares the whole 25-bit cofun against six
whole-word constants and `_wassert`s at `0xeb3c` (→ `0x4a170`, line `0x4e7`) on anything else:

| cofun | our field decode | the handler does |
|---|---|---|
| `0x0180001` | RTPS, sf=1 | `xor ecx,ecx ; call 0x3e80` — one vertex |
| `0x0280030` | RTPT, sf=1 | `call 0x3e80` **three times**, `ecx = 0,1,2` — three vertices |
| `0x0480012` | MVMVA, sf=1 mx=Rot v=V0 cv=TR lm=0 | `call 0x3d60` |
| `0x0780010` | DPCS, sf=1 | `call 0x4b50` |
| `0x1400006` | NCLIP, sf=0 | an **inlined** cross product over SXY0/1/2 (`0x211ff0..0x211ffa`) → MAC0 `0x212020` |
| `0x158002D` | AVSZ3, sf=1 | `call 0x48d0` |

**Layout validation:** the field layout `[5:0]=op · [19]=sf · [18:17]=mx · [16:15]=v · [14:13]=cv ·
[10]=lm · [24:20]=fake` turns those six words into exactly the six canonical PS1 GTE commands, and each
name matches what the handler's body does — a wrong `[5:0]` would not turn `0x0280030` into the
three-vertex call, nor `0x1400006` into a cross product. The GTE register file is visible in the same
region (`mfc2/mtc2` at `[r15+rax*4+0x211f40]`, control regs at `+0x211fc0`), which anchors the operand
side too.

**Corpus histogram (the bonus gate): 261 `cop2` instructions in reachable code, `6` distinct words —
and the set is EQUAL to the DLL-implemented set, not merely a subset.**

```
0x0480012 MVMVA 69 | 0x0180001 RTPS 66 | 0x0780010 DPCS 42
0x0280030 RTPT  38 | 0x158002d AVSZ3 29 | 0x1400006 NCLIP 17
```

**That is the finding: FF9's entire GTE surface, across 385 shipped effect programs, is six command
words.** No NCDS/NCCS/CDP/GPF/GPL/SQR/OP/INTPL anywhere — and the interpreter would have asserted on
them. `MVMVA` exists in exactly one configuration (rotate V0 by R, add TR, sf=1, lm=0). Anyone emitting
GTE code into a *new* effect program is bound to those six.

---

## 7. Coverage, honestly

Corpus-wide over the whole `[0, headerRel)` code region (1,150,888 B):

| slice | bytes | share |
|---|---|---|
| reachable, decoded | 959,824 | **83.4 %** |
| unreached, **data-shaped** (the walk correctly refused it) | 38,764 | 3.4 % |
| unreached, **code-shaped** (linked but never called) | 152,300 | 13.2 % |

Per image: mean 90.5 %, median 98.6 %, 252/385 ≥ 95 %, 21 below 50 %.

The 13.2 % is not a decoder failure and is characterised rather than waved: **112,860 B of it (74 %) lies
*below the first program entry*** — the block a PS1 linker places ahead of the entry points — and of the
207 unreached runs ≥ 64 B, **181 (87 %) contain a `jr $ra`**, i.e. they are complete, self-contained
functions nobody calls. That is the signature of linked-but-unreferenced library objects, which is
exactly what one expects from a PS1 link. The alternative hypothesis (functions reached through code
pointers handed to the host) was tested and is small: constant-tracked code-pointer arguments across the
corpus land in *data*, not on function prologues.

**The canary behaved.** `ef508` and `ef210` — V-C8's two embedded-data outliers — keep their low
whole-image linear score (50.3 % / 62.0 %), decode their reachable code with **0** invalid instructions,
and their unreached mass is overwhelmingly data-shaped (13,380 B vs 252 B; 13,500 B vs 252 B). Data
excluded, not swallowed.

---

## 8. Evidence — ten annotated instructions

Structure only; no payload. All from `ef227` (Bahamut) unless noted.

**The HLE boundary, end to end (chunk 0, the function at `+0x30`):**

```
  0054  3c02801f  lui     $v0, 0x801f
  0068  8c48a868  lw      $t0, -22424($v0)   ; PSX 0x801EA868 = image+0x3168: the BSS sysStruct slot
  0090  8d180010  lw      $t8, 16($t0)       ; sysStruct+0x10  == RVA 0x21FF78 == the sentinel table
  0354  8f020234  lw      $v0, 564($t8)      ; table[141]      -> the word is 0xFF00008D
  036c  0040f809  jalr    $ra, $v0           ; HLE op 141  (trapped at fn 0xec31)
```

**Named choreography calls (the point of the whole rung):**

```
  0c28  0040f809  jalr    $ra, $v0           ; HLE Hi_SetSummonMotion (op 26)
  0dd8  0040f809  jalr    $ra, $v0           ; HLE Hi_DrawSummonModel (op 25)
  027c  4a280030  cop2    0x0280030          ; GTE RTPT sf=1 lm=0
```

**The delay-slot spot proof (`ef000:c0`) — a terminal `jr $ra` still executes its slot:**

```
  019c  03e00008  jr      $ra
  01a0  27bd0028  addiu   $sp, $sp, 40       ; [delay slot] -- decoded, not skipped
```

---

## 9. Corpus findings worth carrying forward

1. **Three effects drive a creature they never ship.** `ef094`, `ef154`, `ef237` carry **no id-4/id-5
   model package at all** — their resource lists are `{0,1,2,3}` — yet their programs call
   `Hi_DrawSummonModel`, `Hi_SetSummonMotion`, `Hi_ModifySummonModelRGB`, `Hi_SetSummonMotFrame` and
   `Hi_GetSummonBoneMatrix`. **The summon slot survives across containers**: one effect registers a
   creature and a *different* effect animates and draws it. That is a live lead for the transplant lane —
   a second container can drive a donor's creature without re-shipping it.
2. **FF9's GTE surface is six command words** (§6). Small enough to hand-implement, and it bounds any
   future emission.
3. **The switch idiom is uniform.** 50 compiled `switch` dispatches recovered corpus-wide, giving 1,331
   case targets, always `sltiu N / beq default / lui+addiu tableBase / sll 2 / addu / lw / jr`, with the
   table sitting **inside the code region** (usually at image `+4`, right after the header pointer). Any
   writer must preserve that placement.
4. **The 10 non-prologue program entries are frameless leaves**, all `bne $a0,$zero,+4/+5` — a dispatch
   on arg0 that returns via `jr $ra` without ever touching `$sp`. Each decodes, walks and terminates
   cleanly. Not tail-calls, not data.
5. **`ef227`'s two programs are 3,019 + 4,262 reachable instructions** (96.0 % / 99.8 % of their code
   regions) — FORMAT §2.6's "≈7,400 instructions" estimate for Bahamut lands almost exactly on the
   reachable total (7,281).

---

## 10. Provenance

* **Zero stock bytes committed.** `tier_r_disasm.py`, `test_tier_r_disasm.py`, `r1_gates.py` and this
  report contain only masks, RVAs, offsets, counts and mnemonics. The ISA mirror is the public MIPS
  R3000A + PS1 GTE encoding (already published in `V-C8` §2 in-repo); the extractor semantics and the
  flag column are *descriptions* of DLL code, read at runtime and re-verified by `--isa-check`.
* **Disassembly listings of stock PS1 code are derived stock content.** All 385 listings live under
  `C:\gd\SCRATCH\summon-format\disasm-r1\` and are never committed. This report quotes **ten**
  instructions as structural evidence, per the FORMAT round's posture.
* **The DLL was never modified**, only read (`pefile` + capstone-x86_64 via `refkit`). No patched
  `FF9SpecialEffectPlugin.dll` was produced and none ever will be.
* The tests run green with **no** corpus and **no** game install (34 passed / 7 skipped), so the
  committed artifact is verifiable by anyone.

---

## 11. What R2 inherits

* Every call site is already classified and 14,190 of them carry an op number; **204 of the 216 ops are
  still unnamed** (`M3-opcode-table.json` names 12). R2's naming job now has a complete, per-image call
  census to work against — and the highest-traffic ops corpus-wide are **102 (3,311 calls), 117
  (1,709), 15 (743), 14 (707), 24 (552), 136 (510)**, which is where naming effort pays.
* The `sysStruct` at image `headerRel + 0x48` (BSS) is the program's window onto the host: field `+0x10`
  is the HLE table, and the other fields (`0x21FF68/6C/70` ← `psx(0x323170/0x3231f0/0x323270)`,
  `+0x14` ← the camera struct `0x69730`) are the next things to name. `0x21FF7C` being the camera struct
  is directly on the path to R3's camera-phase story.
* `$a0-$a3` resolve at 19.5 %; lifting that needs a stack/frame model (`sw`/`lw` on `$sp`) and
  inter-procedural argument flow — the obvious next increment, and the one that turns "op 25 called here"
  into "Draw slot 0 with this rotation".
