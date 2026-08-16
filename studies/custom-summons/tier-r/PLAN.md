# TIER R — THE DECODE LADDER (the effect PROGRAM becomes readable)

> **The strategy line this executes** (custom-summons memory, minted at the transplant close):
> *"invest in TIER R (probe → inspector → MIPS disassembler = 'decodable')"*. The probes exist
> (s52/s53, permanent instruments). This study builds the other two thirds.

**THE TARGET.** THE FORMAT ROUND (`../thomas-swap/disasm/FORMAT.md`) decoded every layer of the ef
container except one: **resource id-3, the effect PROGRAM** — raw little-endian **MIPS R3000A + full
PlayStation GTE (COP2)** machine code inside PS1 main-RAM images. 385 images corpus-wide; ~7,400
instructions for Bahamut (ef227), organized as entry-point programs (ef227: chunk 0 prog 0 @ image
`0x9d4`, chunk 1 prog 0 @ `0x108c`). **This is the choreography** — the code that drives the bones,
emits the primitives, moves the native camera, and re-points the view matrix mid-cast. Reading it is
the difference between *watching* a stock summon through probes and *understanding* it.

**WHY (what "decodable" buys).** TIER W's cheap half (edit stock summons in place — rescore camera,
retime, reskin) needs to know what the program does before any byte of it is patched. The transplant
lane's next beauty pass (a designed creature on Bahamut's real cinematic) needs the phase structure.
And every falsified flight hypothesis (v1→v10.1) died for want of exactly this readability.

---

## The ladder

| Rung | Deliverable | Gate (falsifiable) |
|---|---|---|
| **R0** | The recon brief — priors consolidated (execution model, the 16 program offsets, what C8 built, the HLE/global boundary, GTE surface, corpus layout, validation instruments) | every claim carries a FORMAT-round citation |
| **R1** | **THE DISASSEMBLER** — committable, reachability-driven R3000A+GTE decoder over the PS1-RAM image model (capstone-MIPS for the integer ISA; custom GTE command-word decode) | **385/385 corpus walk from the program offsets; 0 invalid instructions in reachable code; closure stats reported**; a linear sweep is the documented ANTI-pattern (code/data interleave) |
| **R2** | **THE ANNOTATOR** — names the boundary: HLE stubs / memory-mapped globals (OFX `0x211fa0`, view matrix `0x1C1DC8`, the PSX-RAM cursor, …), data refs into the already-decoded resources (camera sub-file, motion clips, model tables), per-function role table | ef227's known functions land where the probes said (`SFX_Update` work body, the GTE RTPS body); every annotated global cross-checks the FORMAT memory map |
| **R3** | **THE INSPECTOR** — `summon-inspect <ef>`: an annotated choreography report | **ef227 CHOREOGRAPHY.md explains the OBSERVED phases (float / charge / beam / fire-column; creature window 82–412) from the code**, validated against the archived s53 capture — the calibrated instrument, not a narrative |

**Done = "decodable":** a person (or agent) can open the inspector's report for a stock summon and
answer "what happens at frame N and which code does it" without a debugger. **★ REACHED for the 34
switch-driven programs** (`EF227-CHOREOGRAPHY.md` §0 is that table for ef227, frame by frame). For
the 342 single-body effects the question is degenerate rather than answered: they do the same thing
every tick, and this rung says so rather than inventing a spine for them.

---

## Provenance (the FORMAT round's posture, unchanged)

- **Committable:** the disassembler, the annotator, the inspector, this study's docs — parsers and
  tools, zero SE bytes.
- **SCRATCH-only, never committed:** the extracted `ef###.bytes` images, disassembly LISTINGS of
  stock code, capture logs — all under `C:\gd\SCRATCH\summon-format\` / `C:\gd\SCRATCH\summon-transplant\`.
- RE-to-understand is sanctioned; never ship a patched DLL; probes stay default-OFF.

## R0 — RATIFIED 2026-07-25 (the recon's load-bearing findings)

1. **Execution = a table-driven MIPS interpreter inside `FF9SpecialEffectPlugin.dll`** (pre-decoder
   `fn 0xd1a0` matches words against the DLL's own **99-entry mask/match ISA table @RVA `0x66c70`**;
   interpreter `fn 0xe210`, 90-entry dispatch @`0xed18`). **No recompiled x64 twin exists** — but the
   ISA table is a BETTER ground truth: R1's decoder is validated against the interpreter's own
   accepted encodings, not a spec's opinion of them.
2. **Reachability seeds already exist**: per-image 16-entry program table at `headerRel+8`, exposed by
   `../thomas-swap/disasm/ef_container.py` `parse_chunk_image → ChunkImage.program_offsets`. Corpus:
   **385 id-3 images / 599 live entries** (1–7 per image), 372 `ef###.bytes` at `C:\gd\SCRATCH\summon-format\`.
3. **The C8 seed is validation-only** — linear-sweep, format-unaware, capstone-MIPS never wired.
   Reuse: the `0x66c70` table extraction (`c8_a.py`/`c8_final.py`) + the 589/599 prologue census
   (`c8_ep.py`). The printer is throwaway.
4. **HLE boundary**: the MIPS program JALRs through a DLL-synthesized 216-sentinel table
   (`0xFF000000|i`, .data RVA `0x68250`); trap at `fn 0xec31`. **The table's PSX base constant is
   UNREAD** (`0x21FF78` vs `0x21FF7C`, published at `0x30d2e/0x30d39`) — resolve STATICALLY in R1 by
   disassembling the two publisher stores; only 12 of 216 HLE ops are named (`M3-opcode-table.json`).
5. **GTE cofun field decode does not exist anywhere in-repo** — author from the PS1 GTE spec, validate
   against the DLL's own COP2-cofun handler body (which fields the shipping implementation extracts).
6. **Validation instruments**: the s53 capture rows (PSXCAM/MODEL/BONES in the archived probe logs),
   creature window **f82–417** (corrected from 82–412), FORMAT §5.4's 35–45% PRIM-AABB prediction, the
   PsxCtx tamper check, `hasMotion==1`-only-on-`kind=S`. `fn[0x13c4..]`/`fn[0x3e80..]` are DLL x64
   RVAs, NOT MIPS offsets — never conflate the two address spaces.

## Status

- R0 — ★ DONE (above).
- R1 — ★ DONE → **`R1-DISASSEMBLER.md`** (`tier_r_disasm.py` + `test_tier_r_disasm.py` + `r1_gates.py`).
  8/8 gates, 41/41 tests. 385/385 images × 599 entries walk, **0 invalid reachable instructions, 0
  unresolved call targets** (1,015 in-image / 14,190 HLE / 11 polymorphic-HLE); coverage median 98.6 %;
  the ef508/ef210 canary holds. Two R0 unknowns closed statically:
  * **HLE base = RVA `0x21FF78`** (camera struct `0x21FF7C`, `0x21FF70` excluded) — and the runtime probe
    D2 §4.5 budgeted is **not needed**: an HLE call is `lw $vX,(4*op)($table)` + `jalr`, so the op index
    falls out of the load offset alone.
  * **The GTE surface is SIX cofun words** (RTPS/RTPT/MVMVA/DPCS/NCLIP/AVSZ3). The DLL's COP2 handler
    whole-word-matches exactly those and asserts on anything else; the corpus set is **equal** to it.
- R2 — ★ DONE → **`R2-ANNOTATOR.md`** (`tier_r_annot.py` + `test_tier_r_annot.py` + `r2_gates.py` +
  the committable **`hle_ops.json`**). 6/6 gates, 111/111 tests (70 new, R1's 41 unchanged).
  * **THE OP DICTIONARY** — 79/216 ops named (**high 42 / medium 27 / low 10 / unnamed 137**),
    covering **51.8 % of all 14,212 call sites**. Calibration on the 12 known ops: **12/12** on name,
    arity AND native-fn identity. Every high name carries both a DLL-supplied symbol and a corpus
    check (`arity-mode` 28 / `never-called` 11 / `noop-called-anyway` 3), enforced in code.
  * **THE DATA-REF MAP** — **5,981/5,981 absolute addresses resolved (100 %), 0 unresolved**; every
    one lands inside its own id-3 image. **The camera sub-file is unreachable from the program** —
    it is 100 % sequence-driven (opcode `0x29`, ef227 shots 6/16/47), and the motion clips are
    reached by INDEX (op 26 / op 100), never by pointer. Confirms the format model rather than
    refuting it, and **relocates TIER W's camera work from the program to the sequence**.
  * **THE FUNCTION TABLE** — 1,022 functions over 385 images, **0 orphans / 0 shared / 0
    mid-function call targets**. ef227's two entries are each ONE switch-driven state machine,
    **11 and 6 cases** — the phase spine R3 binds to the s53 capture.
  * Findings against the record: the OFX/OFY/H "camera triple" is not atomic (H is an independent
    zoom knob, ops 121/122/148); `Hi_Draw*ByBone` reads `summonModels`; `M3-opcode-table.json`'s
    arity column is wrong for 19 ops and its `.data` fn table is not the dispatch authority (8 ops
    are no-ops).
- R3 — ★ DONE → **`EF227-CHOREOGRAPHY.md`** (`summon_inspect.py` + `test_summon_inspect.py` +
  `r3_gates.py`). 5/5 gates, 142/142 tests (31 new; R1's 41 and R2's 70 unchanged).
  * **THE EXECUTION MODEL, recovered not assumed.** An effect program is a **per-tick callback**,
    not a script: its first branch dispatches on `$a0` — 0 *describe* (report the state block's
    size: ef227 **168 B** / **228 B**), 1 *init*, anything else one **tick**. State lives in the
    caller's block (`arg1+0`); the **clock is the caller's cell `*(arg3)`**, and a transition
    writes **-1** to it. That one store fixes the frame model: -1 is only coherent if the host
    increments before the next read, so a case guarded by `clock < N` occupies **N+1 ticks**.
  * **ef227's phase spine, both entries.** c0: `0 →(70) 10 →(25) 1 →(25) 2 →(27) 4 →(31) 5·term`;
    c1: `0 →(36) 1 →(49) 2 →(29) 3 →(3) 4 →(15) 5·term`. Every slot reachable, every transition
    target real, **0 unreachable targets**; c0 carries **5 dead slots (3,6,7,8,9)** that land on
    the per-tick TAIL — the same body every case's "not yet" branch falls into.
  * **VALIDATED against the archived s53 capture, and it REPLICATES.** One fitted parameter per
    program (the frame the sequence starts that chunk: **f57** and **f300**). c0: **5/5** phase
    boundaries land on observed motion-counter restarts **and 5/5 on the motion-frame constant the
    transition writes** (0,0,0,**10**,0). First draw predicted f81 (gate `clock >= 24`, derived by
    dominance) vs observed f82; c1's last draw predicted f413 vs bone-pose-valid-through f415.
    **15 checks agree, 0 disagree**, identically across all **3** archived captures.
  * **Corpus census (385 images): clean 16 · frame-dispatch 18 · trivial 342 · defeated 9.**
    `frame-dispatch` is a second shape, not a failure — the switch index is the host's frame
    counter and nothing writes it, so slot k IS frame k. Only **43** images have a switch-driven
    entry at all: multi-phase choreography is the exception in FF9's effect corpus.
  * Findings: the cast's **end is a sequence event** (both programs end terminal, neither stops
    itself or the other); the camera's three shots change `gteH` at f58/f153/f302 — **1, 1 and 2
    frames after a phase boundary**, so sequence and program are two clocks kept aligned by
    construction (rescoring one without retiming the other will drift).
  * Next: **op 117** (1,709 calls, `(ptr,ptr)->ptr`, `fn 0x306f0`) is still the best naming target;
    and the 9 defeated images split 4 computed-dispatch / 4 stack-local inner switch / 1 degenerate
    chain.

---

## R4 (the VRAM cluster) — ★ DONE 2026-08-07: THE MANAGED-ABI EVIDENCE CLASS

Full record: **[`CALLBACK-OPS.md`](CALLBACK-OPS.md)**. Gates `cb_gates.py` 6/6; 20 new tests
(tier-r 162); R1 8/8 · R2 6/6 · R3 5/5 unchanged.

**79 → 107 named ops (+28), 51.8% → 54.5% of call-site traffic.** R2 recorded the host callback slot
`0x1C1DE8` as a *diffuse* global and kept it out of the evidence — right about the touch, wrong about
what rides it. Every call through it passes a command code, and the managed side is open source, so
the name comes from **Square's own `SFX.COMMAND` enumerator** rather than from our inference.

* **★ THE COMMAND WORD HAS THREE ENCODINGS** — `mov ecx,imm` (144 sites) · `or ecx,imm` (53) ·
  `bts ecx,25` (7). The `or`/`bts` forms are exact because the preceding `movzx` from a word
  provably zeroes bits 16..31. **A mov-only scan resolves 70% and loses the `LoadImage` site
  `A1-TEXTURES` published** — modelling one form is not conservative, it is wrong.
* **★ THE BOUNDARY-CROSSING LAW** — a callback code names the crossing an op performs, a **lower
  bound** on its semantics, not the whole of them. Op 174 both reads a bone matrix across the ABI and
  transforms vertices inside the DLL; the existing R2 name stands and the command rides as evidence.
  Same law: ops 32/33/174 all cross at `GET_MATRIX[0]` and this class does not separate them.
* **★ THE TWO LANES ARE DISJOINT (the null that could have failed)** — 0 overlap with R2's 42
  debug-string `high` names, 0 of the 12 calibration ops reach the callback. The `Hi_*` summon-model
  family never crosses to managed. R2's 12/12 standard therefore **cannot** calibrate this class;
  `A1-TEXTURES` §5.2's independently-derived issuer table is the control instead, reproduced site
  for site after 5 of its 10 addresses reconcile as chained `.pdata` chunks.
* **★ THE DICTIONARY HAD TWO WRITERS** — `r2_gates.py` rebuilds and rewrites `hle_ops.json`, so
  running the R2 board silently reverted all 28 names to null. `tier_r_annot.rebuild_hle_ops` is now
  the single writer, pinned by a tripwire test.
* **REFUSED, by name: 19 ops / 832 call sites** cross at several commands. A `GET_SLAVE`-resolver
  rule would have named ~8 of them and was **measured and rejected** — `0x148f0` issues `GET_ROTATE`
  before `GET_SLAVE`, so the ordering does not hold.
* **The bank half barely moved: 2 of 24.** `psxBankTable` is address translation, not a callback
  path; this lever does not reach it. Ditto the high-volume unknowns — **op 117 (1,709 calls) does
  not touch the callback at all and remains the best target for a handler-body rung.**

## R5 (op 117) — ★ DONE 2026-08-07: THE HANDLER-BODY LANE

Record: `CALLBACK-OPS.md` §ADDENDUM. `body_gates.py` 5/5; 13 new tests (tier-r 175).
**Named 107 → 108; call-site traffic 54.5% → 66.6% — +12.1 points from ONE op.**

R4 named op 117 the best remaining target and it was: **1,709 call sites, 12% of all HLE traffic**,
and it never touches the callback, so only a body read reaches it.

* **op 117 = `subfile_instance_open`** (medium) — its native fn `0x306f0` is a thin forwarder that
  TAIL-JUMPS to `0x34380`, which allocates a `0x6C`-byte record from the pool at `0x3210d0`
  (**returning NULL when full**), binds a `0x1FE0` work buffer, and **relocates the blob's
  `0x28`-stride entry table** (count u16 at +4, pointers +0x1c/+0x20 gated by kind bytes, offsets
  ≤ `0x27ff`) to absolute PSX addresses via `psxBankTable`.
* **THE FAMILY:** ops **116/117/118/119** are consecutive ops on consecutive functions sharing one
  pool and context — reset / open / operate / close. Identified, **not named**: the A/B ran for 117.
* **CORPUS, each test refutable:** 1,680/1,709 sites (**98.3%**) take a sub-file pointer from op 102 ·
  the reading validates **62.2%** on fed sub-files vs **6.4%** on the control (~10×) · **0 of 759**
  camera sub-files are ever fed, so this is not the camera lane.
* **NOT CLAIMED:** 38% of fed sub-files fail the reading and relaxing the bound recovers none of them
  (62.2% either way) — real unmodelled structure, so the name describes the MECHANISM not the content
  domain, and ships `medium`: **no symbol in the chain supplies a name.**
* **★ A SECOND R2 RESOLVER GAP:** names are resolved on an op's OWN function, so a tail-call
  forwarder hides its callee's symbol. **op 206** (339 calls) tail-jumps to `Hi_RegisterTexListModel`
  and `Hi_RegisterGouEffModel` — two names, so it stays unnamed, but it is now a bounded question and
  the natural next target. `body_ops.tailjump_name_gap()` computes the gap; a test pins it.

## R6 (op 206) — ★ DONE 2026-08-07: THE VARIANT DISPATCHER

Record: `CALLBACK-OPS.md` §ADDENDUM 2. `body_gates.py` 8/8; 11 more tests (tier-r 183).
**Named 108 → 109; traffic 66.6% → 69.0%. Across R4-R6: 79 → 109 named, 51.8% → 69.0%.**

R5 left op 206 (339 sites) as a bounded question: its fn tail-jumps to TWO named functions and R2's
exclusivity rule refuses two names. The body resolves it — **it is a dispatcher, not an ambiguity.**

* **op 206 = `Hi_RegisterTexListModel|Hi_RegisterGouEffModel` (high)** — `fn 0x47290` asserts the
  `'so'` magic, **branches on `u16[operand+2]`**, and on the non-zero arm ORs `(arg1 & 3) << 5` (the
  PSX TPAGE **ABR** field) into `u16[+8 + 4*i]` for `i < (u16[+4]-8)/8` before tail-calling
  `Hi_RegisterTexListModel`; the zero arm tail-calls `Hi_RegisterGouEffModel` untouched. Both
  targets are `.pdata` primaries owning exactly one debug string. **HIGH is earned: the disjunction
  is what the op IS**, both halves DLL-supplied, selector decoded.
* **★ A1-TEXTURES §3.5 REPRODUCED EXACTLY** — the `(arg&3)<<5`, the `+8+4*i` stride, the
  `(u16[+4]-8)/8` count, derived months earlier by a different method (the `so_record` pillar rests
  on it). A1 was right and complete about the ABR half; **what it lacked was the tail** — the branch
  and the two registrars.
* **CORPUS:** `'so'` magic **67.2% on paired operands vs 3.7% control** (18×); split **168 tex-list /
  16 gouraud**; **339/339 `$a1` values ∈ {0,1,2,3,255}**, every one a valid ABR mode under `&3`,
  with **1 (additive) dominant at 222/339**.
* **★ THE ASSERT INVERTS THE SHORTFALL:** the DLL *asserts* the magic, so a real operand cannot lack
  it — and the 90 misses carry `'so'` at **no offset at all**, while only 2/339 sites pass a constant
  `$a0`. So the 33% gap measures **the pairing heuristic's error rate, not the claim**.
* **★ A NEW STRING CLASS — `_wassert` SOURCE FILES:** `_wassert` takes **UTF-16** strings and R2's
  resolver scans **ASCII**, so every `file:line` was invisible. `body_ops.wassert_sources()` recovers
  6 files (`sonoda\Geo\{geo,geoslice,geosfxrender,geomorph}.cpp`, `sonoda\PsxEmulator.cpp`,
  `psx\source\psx_compatibility.cpp`). **Reach measured and modest — 20 functions, 9 of them an op's
  own native fn — an attribution aid, NOT a naming lane.**

## R7 (op 136) — ★ DONE 2026-08-07: NAMED BY ITS DESTINATION

Record: `CALLBACK-OPS.md` §ADDENDUM 3. `body_gates.py` 9/9; 4 more tests (tier-r 187).
**Named 109 → 110; traffic 69.0% → 72.5%. Across R4-R7: 79 → 110 named, 51.8% → 72.5%.**

* **op 136 = `actor_relative_coord` (medium)** — `fn 0x45a80` is four instructions:
  `base + actor[+0x38] / 6` (the `0xAAAAAAAB` + `shr 2` unsigned magic divide). **The body alone
  does not name it; the DESTINATION does.**
* **★ THE ACTOR TABLE, from its own asserts** (`fn 0x44a60`, reusable): **`0..7` party (count
  `ctx+0x24`) · `8..15` enemies (`ctx+0x27`) · `0x10`/`0x11` two singleton slots**. op 136's `$a0` is
  only ever **0 or 16**; `$a1` is **always a power of two** (128×237, 32×153, 64×46, 256×18, 16×14,
  512×13).
* **THE IDIOM:** 436 of 510 sites sit beside op 117 — `handle = op117(...)` then
  `handle->[0x22] = op136(...)`, the field op 117's allocator zeroes and **ef227 sets to the literal
  128** (one of op 136's own `$a1` values).
* **★ A GUESS CORRECTED BY LOOKING:** a signed (`movsx`) read of `+0x22` next to the model
  registrars reads like an **ordering-table bias**, and that was the working hypothesis. The
  per-tick fn `0x34860` refutes it — **`+0x20` and `+0x22` are loaded TOGETHER into GTE input slots
  and projected**, so `+0x22` is a **coordinate component, not a sort key**.
* **NOT CLAIMED — and the trap is named:** `actor[+0x38]` is **not** a `BTL_DATA_INIT` field.
  Tracing `SFX_InitBattle` shows **all 17 of them land, in order, on other offsets**
  (`enemy_radius`→`+0x18`, `geo_radius`→`+0x28`, `geo_height`→`+0x2c`, `btl_id`→`+0x08`), so
  reaching for the open-source struct here gives the WRONG field. Neither the axis nor the divisor's
  meaning is pinned. **Sibling op 124 exposes the same pair** (`+0x28` normally, `+0x38` when bit 8
  of its arg is set — `$a0` constants exactly `0` and `256`) = a second handle for a future rung.

## R8 (ops 48/49/50) — ★ DONE 2026-08-07: THE RNG FAMILY, AND A DECODER BUG

Record: `CALLBACK-OPS.md` §ADDENDUM 4. `body_gates.py` 10/10; 5 more tests (tier-r 191).
**Named 110 → 113; traffic 72.5% → 78.9%. Across R4-R8: 79 → 113 named, 51.8% → 78.9%.**

The brief was 48 and 50; they are two thirds of ONE algorithm, so 49 came with them.

* **★ ALL THREE DRIVE THE SAME LCG** on the shared state `0x3231dc`:
  `seed = seed*0x41C64E6D + 0x3039 ; value = seed >> 16`. **`0x41C64E6D` = 1103515245 and
  `0x3039` = 12345 are the ANSI C `rand()` constants** — a published external prior; the numbers
  identify the algorithm the way an import name would.
  - **op 48 = `rand`** (451 sites) — the raw draw; top co-call is op 15 `rsin_fixed_point` (×52).
  - **op 49 = `rand_range`** (78) — `lo + rand() % (hi-lo)`; returns `lo` when `lo == hi` **without
    advancing the seed**. Corpus: `$a0` NEGATIVE (−256/−32/−64/−96/−128), `$a1` the positive twin.
  - **op 50 = `rand_centered`** (378) — `rand() % n - n/2`; `n == 0` guarded to 1. Corpus `$a0` =
    256/128/512/32/1024/384 ⇒ jitters of ±128/±64/±256/±16/±512/±192.
* **MEDIUM not high, and the asymmetry is recorded:** R2 rates a thin CRT wrapper `high` (that is how
  `rsin`/`rcos` got named, because the DLL IMPORTS `sin`/`cos`). These are the same library function
  **INLINED**, and inlining is a codegen choice — but no source in the binary states a name, so they
  stay `medium` rather than inflating.
* **★ A DECODER BUG IN R2'S STUB READER — 3 ops were wrongly VOID.** The reader matched only the
  literal `mov r12d, eax`; op 50's stub ends `mov r12d, edx`, so **378 call sites** read as returning
  nothing. Swept over all 216 stubs the r12d source is `eax` 55× and something else **3**× — **op 50
  (`edx`), op 43 (`ecx`), op 16 (a constant `0x400`)** — all three mis-typed, all three now `int`.
  Fixed by matching ANY write to `r12d` before the tail return: the register a value arrives in is a
  codegen detail, not part of the ABI. Confidence board unaffected (0 violations); R1/R2/R3/CB green.

## R9 (op 64) -- * DONE 2026-08-07: THE FULL-SCREEN FILL, AND AN UNDERCOUNTED ARITY

Record: `CALLBACK-OPS.md` SS ADDENDUM 5. `body_gates.py` 12/12; 6 more tests (tier-r 197).
**Named 113 -> 114; traffic 78.9% -> 81.5%. Across R4-R9: 79 -> 114 named, 51.8% -> 81.5%.**

* **op 64 = `draw_fullscreen_fill`** (366 sites, medium). `fn 0x3f180` carves `0x80` bytes off the
  arena cursor and builds **8 PS1 `TILE` primitives** `{u32 tag; u8 r,g,b,code; u16 x,y; u16 w,h}`
  at `x=(i&3)*80`, `y=(i>>2)*110`, each `80x110` -- a 4x2 grid, and **4*80 = 320, 2*110 = 220 = THE
  PS1 SCREEN**. Colour is `(arg2,arg3,arg4)`; code `0x60` opaque when `arg1 == 0xff` else `0x62`
  (the rectangle ABE bit). Each tile goes to **`fn 0x3edb0` = libgpu `AddPrim`** (length into the
  tag's top byte, 24-bit OT XOR-splice) at depth `arg1`, which `AddPrim` itself special-cases at
  `0xff` -- so `0xff` is a sentinel, not a depth.
* **LEAD: `op 143`'s own native fn IS `0x3edb0`** -- the corpus exposes `AddPrim` directly, unclaimed.
* **CORPUS (the refutable part): 412/412 (100%)** of `$a2`/`$a3` constants are colour bytes `<=255`
  vs **987/1609 (61.3%)** control (every other op with >=3 int args); `$a1` corpus-wide is exactly
  `{0,1,2,255}`; and a real site builds the channels as **three shifts of ONE animated scalar**
  (`r=v>>4, g=v>>3, b=v>>2`) -- coordinates could not look like that.
* ** A SECOND DECODER BLIND SPOT -- op 64 takes FIVE arguments, not four.** R2 tracks the
  translated MIPS `$sp` only while it lives in `rax`; op 64's stub does `mov rbx, rax` before
  another call, then reads arg 4 as `[rbx+0x10]`. Fixed by following the value through the register
  move. **Bounded: exactly 2 ops gain an argument (64 and 70, both 4 -> 5); calibration still
  12/12 on name AND arity.**
* **INDEPENDENT CORROBORATION: `M3-opcode-table.json` (from the x86 build's `[ebp+N]` frame) says
  arity 5 for BOTH.** Both are in R2 finding 4's disagreement list, so that finding's blanket
  *"prefer `hle_ops.json`"* was too broad -- **on stacked-argument arity M3 was right**. The
  disagreement set shrinks 19 -> 17.

## R10 (op 143) -- * DONE 2026-08-07: AddPrim + A CORRECTION TO OP 64

Record: `CALLBACK-OPS.md` SS ADDENDUM 6. `body_gates.py` 14/14; 5 more tests (tier-r 202).
**Named 114 -> 115; traffic 81.5% -> 81.6%. Across R4-R10: 79 -> 115 named, 51.8% -> 81.6%.**

Only 9 call sites, so the traffic gain is trivial -- the rung earned its place by correcting the op
it shares a function with.

* **op 143 = `add_prim_blended`** (9 sites, medium). `fn 0x3edb0` is libgpu **`addPrim`**: length
  out of the tag's top byte, then the PS1 OT insert XOR-swapping only the low **24 bits** so each
  word keeps its top byte. **Then, unless `arg3 == 0xff`, it carves 8 more bytes off the arena
  cursor for a 2-word primitive whose payload is `0xE1000200 | ((arg3 & 3) << 5)`** -- GP0(E1h)
  Draw Mode, bits 5-6 the **ABR** semi-transparency mode, bit 9 dither: a **`DR_TPAGE`** (the same
  state primitive the s76 probe logs, and the same ABR field op 206 ORs into `so` bindings).
  `addPrim` inserts at the HEAD, so the prefix draws FIRST -- set the blend, then draw.
* ** THE CORRECTION: op 64's `arg1` is a BLEND MODE, not an OT depth.** op 64 passes it straight
  into this parameter (`mov r9d, esi`), which masks it to 2 bits. R9/ADDENDUM 5 called it a depth;
  wrong. The corpus fits the corrected reading far better -- `1(x254)` is **ABR 1, additive**,
  what a full-screen VFX flash wants; `2` subtractive, `0` 50/50, `255` opaque-and-emit-nothing.
  **Neither op has a depth argument at all: the OT POINTER is the depth (`&ot[z]`).** Evidence
  string, docstring and the B12 gate label all corrected; a test pins it so a revert fails loud.
* **CORPUS: `arg0` is a primitive TAG** (length in the top byte, 24-bit link zeroed) -- **9/9
  (100%)**, values `0x04000000` x4 / `0x08000000` x5, vs **73/2086 (3.5%)** for every other
  int-arg0 op, a ~29x separation.
* MEDIUM: `fn 0x3edb0` owns no debug string -- same posture as the RNG family (a documented external
  shape, no name stated in the binary).

## R11 (op 128) -- * DONE 2026-08-07: THE ACTOR ANCHOR, AND A REFUSAL RULE CORRECTED

Record: `CALLBACK-OPS.md` SS ADDENDUM 7. `body_gates.py` 16/16; 5 more tests (tier-r 207).
**Named 115 -> 116; traffic 81.6% -> 83.7%. Across R4-R11: 79 -> 116 named, 51.8% -> 83.7%.**
Unnamed is now under 100.

* ** THE REUSABLE CORRECTION: multi-command != ambiguous.** The callback lane refused op 128 for
  reaching FOUR commands. The body shows they are **four routes to ONE answer** -- *where is this
  actor's anchor point?* A multi-command op is only ambiguous when the commands are **unrelated**;
  that is what makes the remaining callback-lane refusals worth revisiting.
* **op 128 = `get_actor_anchor`** (305 sites, medium). `fn 0x450c0` resolves the actor through
  `fn 0x44a60` -- **op 136's index space** -- and TAIL-JUMPS to `fn 0x44f80` (the op-206 gap again).
  `GET_SLAVE(22)` asks whether the unit is attached; a slave takes `GET_MATRIX(14)` on bone
  `byte[actor+0x1a]`, an ordinary unit `GET_POSITION(1)` (`bts ecx, 0x18`); height comes from
  `actor+0x3c` **halved at mode 0**; and `CHECK_STATUS(20)` sub-mode 1, mask `0x200000` =
  **`BattleStatus.Float`**, takes `0x80` back off it. Then `word[out+2] -= height` -> **out is an
  i16 x/y/z triple, +2 is Y**.
* ** THE FLOAT FIX IS WHAT PROVES THE READING**: a floating unit's reported position is ALREADY
  raised, so the anchor correction must subtract that lift back out or double-count it. Nothing but
  a body-anchor calculation needs that.
* **CORPUS: `arg2` is an OUT-POINTER -- 11/11 (100%)** are PSX RAM pointers vs **0/928 (0.0%)** for
  every other op whose arg2 is typed int. A clean separation. `$a0` only `{0,16}` (op 136's actor
  indices); `$a1` only `{0 x289, 1 x15}`, the two height modes.
* Natural sibling of op 136 `actor_relative_coord` -- same lookup, same anchoring job.
