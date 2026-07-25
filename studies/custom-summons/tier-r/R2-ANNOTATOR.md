# R2 — THE ANNOTATOR (the HLE dictionary, the data-ref map, the function role table)

**Status: ★ DONE. 6/6 gates pass, 111/111 tests pass (70 new + R1's 41, unchanged).** R1 made the
effect program *decodable*; R2 makes it *readable*. **79 of the 216 HLE ops now carry a name** —
covering **51.8 % of all 14,212 call sites** — every absolute address the corpus builds is resolved
against the image's own PSX address space (**5,981 / 5,981, 100 %**), and the reachable code of all
385 images is segmented into **1,022 functions with zero orphans and zero shared instructions**.

Three findings contradict or extend the existing record (§7), and one of them changes where TIER W
has to point its screwdriver.

---

## 1. What shipped

| file | what it is |
|---|---|
| `tier_r_annot.py` | the annotator: the PSX address-space classifier, the DLL handler-stub decoder, the debug-string name resolver, the corpus census, the dictionary builder, the data-ref pass, the function segmenter, the annotated-listing writer, CLI |
| `hle_ops.json` | **the committable op dictionary** — 216 rows of `{name, confidence, arity, arg_kinds, returns, native_fn, touches, evidence, call_sites, effects}` |
| `test_tier_r_annot.py` | 70 pytest cases. Runs with **no corpus and no game install** (87 passed / 24 skipped in that configuration) |
| `r2_gates.py` | the gate runner — prints H0…H5 with numbers, plus ef227's function graph and the findings list; exit 0/1 |
| `R2-ANNOTATOR.md` | this report |

```
py studies/custom-summons/tier-r/r2_gates.py                        # 6/6, exit 0
py studies/custom-summons/tier-r/tier_r_annot.py --calibrate        # 12/12
py studies/custom-summons/tier-r/tier_r_annot.py --hle-ops          # rebuild hle_ops.json
py -m pytest studies/custom-summons/tier-r/test_tier_r_annot.py -q  # 70 passed
```

Annotated listings of stock images go **only** to `C:\gd\SCRATCH\summon-format\annot-r2\`
(385 files, ~14.9 MB). Nothing from them is committed. → §8.

---

## 2. The gate table

| gate | verdict | headline numbers |
|---|---|---|
| **H0** no regression | **PASS** | `r1_gates.py` **8/8**, exit 0 · `test_tier_r_disasm.py` **41 passed** · `test_tier_r_annot.py` **70 passed**. R2 *imports* `tier_r_disasm` and mutates nothing in it, so every R1 number is still produced by R1's own code |
| **H1** calibration | **PASS** | **12/12** on **both** name and arity; native fn confirmed by a real `call` inside the stub **12/12**. The naive reading scores **4/12** (§3) |
| **H2** naming coverage | **PASS** | **high 42 / medium 27 / low 10 / unnamed 137** of 216 → 79 named (36.6 %), **51.8 % of call-site traffic**. High-confidence contract violations: **0**, enforced in code |
| **H3** ef227 data refs | **PASS** | ef227: 106 absolute addresses, **0** leave their own id-3 image. Corpus: **5,981 / 5,981 resolved (100 %)**, **0 unresolved**. The camera sub-file is **not reachable from the program at all** — loudly, §5 |
| **H4** memory-map cross-check | **PASS** | all **25** map rows carry ≥1 live x64 xref (**0 stale**); `0x68250` still has exactly **1** publisher and no reader; **2 disagreements found and reported as findings** |
| **H5** segmentation | **PASS** | 385 images / 239,956 instructions → **1,022 functions**; orphans **0**, multi-owned instructions **0**, call targets landing mid-function **0** |

---

## 3. H1 — the calibration, and the miss it exists to catch

The 12 ops `M3-opcode-table.json` names are the control group: **the static method must re-derive
them before any unknown op's signature is believed.** It does, 12/12, on name *and* arity *and* the
native-function identity — with the name coming from the DLL's own leftover debug strings and the
signature coming from the dispatcher stub alone.

Two decisions make that work, and both were failures first:

**(a) Arguments arrive in two idioms, not one.** The obvious one is
`mov edx,<i> ; call getArgInt@0x126c0` (or `getArgPtr@0x12740`). The other is the same four context
fields read **inline** — `getArgInt`'s own arms are `[ctx + 0xca8/0xcac/0xcb0/0xcb4]` = `$a0..$a3`,
and `[ctx + 0xd0c]` is the MIPS `$sp` for arguments 4+. Reading only the call form scores **4/12**:
ops 11/12/25/65 come out at arity 0 or 1 instead of 2/3/5/4. A pointer argument is discriminable
too — the raw dword goes to `edx` and then to the PSX→host translator `fn 0x10e0`.

**(b) Function boundaries must come from the UNWIND_INFO chain, not from the nearest preceding
`.pdata` row.** MSVC splits one function across several `RUNTIME_FUNCTION` chunks, and a chunk whose
unwind flags carry `UNW_FLAG_CHAININFO` (0x4) names its primary. Resolving a string xref by nearest
`.pdata` begin instead merges neighbours and puts **two** `Hi_` names on one op. A second rule
finishes the job: the DLL prints assert text through the *callee's* name string and MSVC inlines
those callees, so `Hi_DrawEffModelByBone`'s body also carries the `Hi_GetSummonBoneMatrix` text —
**a name another function owns exclusively is borrowed, not owned.**

The return convention falls out of the same stub. `r12d` is zeroed at the dispatcher's entry
(`0xee92`) and there are exactly two epilogues: `0x122f1` returns `r12d` (so *no* `mov r12d,eax`
means **void**), and `0x11e7a` converts a host pointer back to a PSX address and returns **that**.
Across 216 ops: 137 void, 55 int, 15 pointer, 8 no-op, 1 unrecognised.

---

## 4. H2 — the dictionary, and the confidence contract

**high 42 · medium 27 · low 10 · unnamed 137.** Deliberately conservative: a hedged description is
cheap, a wrong confident name is a defect. Four evidence sources, in decreasing strength.

| source | ops | confidence |
|---|---|---|
| a debug string the DLL itself owns, resolved UNWIND-exactly | 32 | high |
| a CRT import the op is a *thin wrapper* around (`sin` / `cos`) | 2 | high |
| the jump-table slot **is** the return tail — the op executes nothing | 8 | high |
| a documented native function (`fn 0x3d800`, the sub-file walker) | 1 | medium |
| the discriminating globals the native function touches **directly** | 36 | medium / low |
| *(a twin op inheriting a shared named native function)* | 0 | — |

The twin rule is implemented but never fires: once borrowed assert strings are stripped, every
name-carrying native function is claimed by exactly one op. 32 + 2 + 8 = **42 high**;
1 + 36 = **37 medium + low**.

**The contract, enforced by `check_confidence_rule` and gated, not merely documented:** a `high` row
needs a decoded handler stub with a recognised terminator, a name the DLL itself supplies, **and** a
recorded corpus outcome that does not contradict the static signature. The corpus support behind the
42 high rows is `{arity-mode: 28, never-called: 11, noop-called-anyway: 3}`.

**`arity-mode` is the real cross-validation, and it could have failed.** For every HLE call site the
census counts how many of `$a0..$a3` the block sets up, and the *modal* value must equal the stub's
**register**-argument count `min(arity, 4)` — arguments 4+ ride the MIPS stack and are invisible to
the measure, which is why the prediction is capped. It lands: op 26 → 54/58 sites at 2 (static 2),
op 149 → 110/112 at 3 (static 3), op 24 → 550/556 at 4 (static 4), and ops 22/163 sit at 4 against a
static 5/6 exactly because their extra arguments are stacked. **The mode, not the maximum** —
argument registers are caller-saved, so a single block can leave one dirty; what cannot be noise is
where the whole distribution piles up.

Three near-misses worth recording, because each was a wrong name caught before it shipped:

* **The CRT rule leaked.** Matching `cos` at any call depth named ops 74 and 53 `rcos_fixed_point`
  merely because they transitively reach it. Now the import must be reached by the function
  *itself* (import thunks treated as transparent) **and** the op must be a ≤2-function wrapper.
* **A single-global rule matched supersets.** Op 9 touches the GTE translation *and* the vertex
  bank; the ladder happily called it `set_gte_translation`. Single-global rules now must match the
  touch set exactly; two-or-more globals are already a signature and may match as a subset.
* **Role tags went two levels deep.** That makes every `Hi_Register*` op a "primitive emitter",
  because registration shares the geometry parser with the draw path. Global-derived tags are now
  direct-touch only.

**The traffic that matters.** The three highest-volume ops were all anonymous before this rung:

| op | calls | name | confidence | signature |
|---|---|---|---|---|
| 102 | 3,311 | `get_subfile_ptr` | medium | `(int,int) -> ptr` |
| 117 | 1,709 | — | unnamed | `(ptr,ptr) -> ptr` |
| 15 | 746 | `rsin_fixed_point` | high | `(int) -> void` |
| 14 | 710 | `rcos_fixed_point` | high | `(int) -> void` |
| 24 | 556 | `Hi_DrawEffModel` | high | `(ptr,ptr,ptr,int) -> void` |

**Op 102 is the container's own read head**, and it earns its name from a falsifiable corpus test
rather than a hunch: its native function `fn 0x3d800` is the sub-file directory walker
`ef_container` already documents (`entry = base + (Int32)base[idx]`), the stub returns a *pointer*,
and **3,138 / 3,176 statically-known `$a1` values (98.80 %) index a sub-file the chunk's id-2
directory really has** — the 38 misses are concentrated in a single file (`ef251`, whose directory
parses to 2 entries). A control op with a comparable constant-argument population scores 67.7 %.

---

## 5. H3 — the ef227 data-ref verdict, stated loudly

The gate asked whether ef227's camera sub-file and motion clips are reached by real data references
from the program, and said that if they are not, say so loudly.

**They are not — and the camera is not reached by *any* mechanism at all.**

* **Zero of ef227's 106 absolute addresses leave its own id-3 image.** Corpus-wide the number is the
  same shape: **5,981 / 5,981 resolved (100 %), 0 unresolved.** The distribution is
  `image_data 4,848 · image_code 1,131 · scratchpad 2` — and `sibling_image` is **0**, so not one
  chunk's program ever addresses the other chunk's image even though they sit adjacent in PSX RAM
  (`0x801E7700 + (slot&1)*0x5000`).
* **The camera sub-file is driven entirely by the SEQUENCE stream**, opcode `0x29 PLAY_CAMERA`,
  ef227's three shots being sub-file indices **6, 16, 47**. The MIPS program neither points at it
  nor asks for it by index.
* **The motion clips are reached by INDEX, not by pointer** — they live inside the id-5
  `SUMMON_MODEL` package (ef227: 8 clips), selected through `op 26 Hi_SetSummonMotion(modelPtr,
  motionIndex)` (6 sites in chunk 0, 2 in chunk 1) and scrubbed by `op 100 Hi_SetSummonMotFrame`
  with statically-known frames **0, 0, 10, 0, 10, 0**.
* **What *is* reached from the program: the id-2 sub-file archive**, by index through op 102 —
  **55/55** of ef227's constant indices address a real sub-file (13 of 30 in chunk 0, 42 of 54 in
  chunk 1).

**This does not refute the format model; it confirms it, and sharpens it.** The id-3 image is a
self-contained PS1 RAM image; the camera sub-file (resource id-2) and the motion clips (inside id-5)
are never mapped into that address space, so a pointer into them *could not exist*. Every
cross-resource reach is an index — through the HLE boundary or through the sequence.

**The consequence, which is the useful part.** *To rescore a stock summon's camera you edit the
SEQUENCE (opcode `0x29`'s sub-file index) or the camera sub-file bytes. The effect program never
needs to be touched, and patching it could not move the camera.* TIER W's cheap half just got a
smaller and much better-defined target.

---

## 6. H5 — the function role table

Starts are the program entries plus every in-image call target; the flood follows intra-procedural
edges only (fall-through, both branch arms, `j`, and a `switch` table dispatched *inside* the
function) and stops at any other start. Call edges are never followed.

Corpus-wide: **1,022 functions over 239,956 reachable instructions — 0 orphans, 0 instructions owned
by more than one function, 0 call targets landing inside another function's body.** So every
reachable instruction belongs to exactly one function, and there is no tail call into a mid-function
and no shared epilogue anywhere in the corpus.

Roles: `program-entry 599 · leaf-helper 198 · leaf-hle-wrapper 182 · internal 43`.
Tags: `load 555 · gte-globals 246 · trig 232 · draw 174 · gte-code 70 · projection 51 ·
state-machine 50 · summon-slot 34 · motion 29 · bone 20`.

**ef227 (Bahamut), the graph from the two entry points** — and this is the shape R3 needs:

```
ef227:c0  headerRel=0x3120  3,019 instr  4 functions
  prog0   0x09d4  10,004 B  program-entry  switch 1/11 cases  135 HLE calls
          tags: bone,draw,gte-globals,load,motion,projection,summon-slot,trig,state-machine
  L_0030  0x0030   1,040 B  leaf-hle-wrapper  gte-code           (1 HLE call, op 141)
  L_0640  0x0640     520 B  leaf-hle-wrapper  gte-globals,load,trig
  L_0440  0x0440     512 B  leaf-hle-wrapper  gte-globals,load,trig

ef227:c1  headerRel=0x42bc  4,262 instr  8 functions
  prog0   0x108c  12,840 B  program-entry  switch 1/6 cases  224 HLE calls
  L_08e4  0x08e4   1,828 B  leaf-hle-wrapper  gte-globals,trig,gte-code
  ... 6 more leaves
```

**Each entry point is ONE switch-driven state machine**: chunk 0's `prog0` dispatches **11 cases**,
chunk 1's **6**. That is the phase spine R3's CHOREOGRAPHY report has to hang the observed
float / charge / beam / fire-column beats on — and the per-case HLE call lists are already in the
scratch listings. `prog0` calls 24 (c0) / 29 (c1) distinct HLE ops; the named ones include
`Hi_DrawSummonModel`, `Hi_SetSummonMotion`, `Hi_SetSummonMotFrame`, `Hi_GetSummonBoneMatrix`,
`Hi_GetSummonBonePos`, `Hi_ModifySummonModelRGB`, `rsin/rcos`, `get_subfile_ptr` and
`gte_project_vertices`.

---

## 7. FINDINGS — where R2 disagrees with, or extends, the record

1. **The camera sub-file is unreachable from the effect program** (§5). The existing reports treat
   the camera as part of the effect's choreography; it is part of the effect's *sequence*. Camera
   authoring is a sequence edit, not a program edit.
2. **`Hi_DrawEffModelByBone` and `Hi_DrawMorphModelByBone` read `summonModels @0x220830`** — an
   eff-model drawn *by bone* sources its skeleton from the **summon** slot. Two independent signals
   agree: the direct global touch, and the inlined `Hi_GetSummonBoneMatrix` assert string in both
   bodies. This is an addition to A5's map, and a live lead for the transplant lane — it is a second
   route by which non-summon geometry rides a summon's bones.
3. **`B3 279-281`'s OFX/OFY/H "camera triple" is not atomic.** Ops **121, 122, 148** write `gteH`
   (the projection distance) and touch neither OFX nor OFY. Zoom is an independently settable knob,
   and a second camera lever for TIER W alongside the sequence-side one.
4. **`M3-opcode-table.json`'s `arity` column is unreliable for 19 of the 192 ops it fills in.** It
   was derived from the *x86 native function's* `[ebp+N]` frame; R2's is derived from the dispatcher
   stub and calibrates 12/12. Where they differ (ops 3, 59, 60, 62, 64, 66-72, 83, 105, 109, 130,
   133, 180, 215), prefer `hle_ops.json`. The two agree on 173.
5. **The `.data` native-function table `@0x68780` is NOT the dispatch authority.** Eight ops
   (**20, 27, 36, 41, 133, 194, 209, 214**) have their jump-table slot pointing straight at the
   return tail — they execute nothing — yet seven of them still list a function in that table. A
   further 14 ops' stubs inline the work instead of calling the listed function. The dispatcher's
   own jump table `@0x12358` is the authority; `M3`'s table is a hypothesis about it.
6. **Three of those dead ops are still called** — ops **20, 27, 214** with 1 / 1 / 4 sites — and
   their callers still set up arguments for them. Retired entry points whose call sites were never
   re-emitted; the arguments are computed and thrown away.
7. **R1's switch-table placement finding is confirmed from the data side.** ef227:c0's dispatch
   builds `0x801e7704` = **image+4**, exactly the "table sits inside the code region, usually at
   image+4" R1 reported from the recovery side.

---

## 8. Evidence — ten annotated instructions

Structure only, no payload. All from `ef227` (Bahamut). Budget honoured: R1 quoted ten, R2 quotes
ten.

**The HLE boundary, now named, with its constant argument (chunk 0, `prog0`):**

```
  0c4c  0040f809  jalr  $ra, $v0   ; HLE op 100 Hi_SetSummonMotFrame [high] sig(ii)->void  $a1=0x0
  1874  0040f809  jalr  $ra, $v0   ; HLE op 100 Hi_SetSummonMotFrame [high] sig(ii)->void  $a1=0xa
  05d0  0040f809  jalr  $ra, $v0   ; HLE op 102 get_subfile_ptr    [medium] sig(ii)->ptr   $a1=0x8
```

**A data reference resolved against the image's own address space:**

```
  0068  8c48a868  lw    $t0, -22424($v0)  ; load 0x801ea868 -> image+0x3168 (header.sysStructPtr)
```

**The state-machine dispatch — and why a block-local constant fold misses it.** The `lui` lands in
the **delay slot** of the guarding `beq`, so it ends its block and its companion `addiu` starts the
next one; only a fixpoint over the block graph puts the pair back together:

```
  0b48  104007fb  beq   $v0, $zero, 0x2b38
  0b4c  3c02801e  lui   $v0, 0x801e            ; [delay slot]
  0b50  24427704  addiu $v0, $v0, 30468        ; pointer 0x801e7704 -> image+0x4 (switch table)
  0b54  00031880  sll   $v1, $v1, 2
  0b5c  8c620000  lw    $v0, 0($v1)
  0b64  00400008  jr    $v0                    ; -> 11 cases: the choreography's phase spine
```

Making that pass a proper inter-block fixpoint (intersection-on-equal-values, calls as barriers)
raised corpus-wide resolved references from **4,521 to 5,981, +32 %**, with the resolved fraction
staying at 100 %.

---

## 9. Provenance

* **Zero stock bytes committed.** `tier_r_annot.py`, `test_tier_r_annot.py`, `r2_gates.py`,
  `hle_ops.json` and this report contain only names, RVAs, offsets, statistics and mnemonics.
  `hle_ops.json` is structure and evidence prose — no payload, and its schema is gated by a test.
* **Annotated listings of stock PS1 code are derived stock content.** All 385 live under
  `C:\gd\SCRATCH\summon-format\annot-r2\` and are never committed. This report quotes **ten**
  instructions as structural evidence, matching R1's budget.
* **The DLL was never modified**, only read (`pefile` + capstone-x86_64 via `refkit`), including its
  `.pdata` / UNWIND_INFO. No patched `FF9SpecialEffectPlugin.dll` was produced and none ever will be.
* The tests run green with **no DLL and no corpus** (87 passed / 24 skipped), so the committed
  artifact is verifiable by anyone with the repo alone.

---

## 10. What R3 inherits

* **`hle_ops.json`** — for any call site, a name, a confidence, an arity, per-argument int-vs-pointer
  kinds and a return kind. 51.8 % of call-site traffic is named; the remaining 48.2 % is dominated by
  a short list of high-volume unknowns (**117 @1,709 · 136 @510 · 48 @451 · 50 @378 · 64 @366 ·
  206 @339 · 128 @305**). Op 117 is the single best next target: 2 pointer arguments returning a
  pointer, native `fn 0x306f0`, and it is the only unnamed op in the top three.
* **The phase spine.** ef227's two entries are each ONE switch-driven state machine — **11 cases**
  in chunk 0, **6** in chunk 1 — and the annotated listings already carry each case's HLE call
  sequence with its constant arguments. R3's job is to bind those cases to the s53 capture's
  observed beats, not to discover them.
* **The camera is out of scope for program reading** (§5) — R3 should read ef227's camera phases off
  the *sequence* (opcode `0x29`, shots 6/16/47) and the camera sub-file, and should say so rather
  than hunting for camera code that does not exist.
* **The most useful sentence R3 can now write about a cast**: *"at frame N, case K of `prog0`'s
  state machine runs, and it calls `Hi_SetSummonMotFrame(slot, 10)` then `Hi_DrawSummonModel(...)`
  after fetching sub-file 8 — here is the instruction that does it."* Every clause of that is now
  mechanically derivable offline.
