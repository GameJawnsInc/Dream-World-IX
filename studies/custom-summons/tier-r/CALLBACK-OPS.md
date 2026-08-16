# THE MANAGED-ABI EVIDENCE CLASS — naming the VRAM cluster

**Status: ★ DONE. 6/6 CB gates, 20 new tests (tier-r 162 total), R1 8/8 · R2 6/6 · R3 5/5 unchanged.**

R2 named 79 of the 216 HLE ops and stopped because its four static evidence sources ran dry. This
round adds a fifth, and it is not more inference — it is **the other side of the same ABI, in
source, with Square's own symbols**. **28 ops named, 79 → 107.**

---

## 1. What shipped

| file | what it is |
|---|---|
| `callback_ops.py` | the evidence class: the `SFX.COMMAND` parser, the managed-handler signature reader, the callback-site code extractor, the op→command reachability, the cross-check, the cluster report, CLI |
| `cb_gates.py` | the gate board — C1…C6 with numbers; exit 0/1 |
| `test_callback_ops.py` | 20 pytest cases; the managed-parser tests run against an inline fixture so a Memoria update cannot turn a parser regression into a skip |
| `tier_r_annot.py` | `build_hle_ops(callback=…)` + **`rebuild_hle_ops`, the single writer** (§8) |
| `hle_ops.json` | +3 fields (`callback_command` / `callback_code` / `callback_submode`), 28 new names |

```
py studies/custom-summons/tier-r/cb_gates.py                        # 6/6, exit 0
py studies/custom-summons/tier-r/callback_ops.py --calibrate        # the A1 control
py studies/custom-summons/tier-r/callback_ops.py --cluster          # names + refusals
py studies/custom-summons/tier-r/tier_r_annot.py --hle-ops hle_ops.json
```

---

## 2. The gate table

| gate | verdict | headline |
|---|---|---|
| **C1** A1 reproduction | **PASS** | `A1-TEXTURES.md` §5.2's 10-site / 3-code issuer table reproduced **site for site**, after reconciling 5 of its 10 addresses as chained `.pdata` chunks (§4) |
| **C2** managed authority | **PASS** | `SFX.COMMAND` **parsed** (52 rows) from Memoria's source, never transcribed; every named code has a parsed handler |
| **C3** site resolution | **PASS** | **204/204** callback sites resolve, 0 unresolved. Encodings `mov` 144 · `or` 53 · `bts` 7 |
| **C4** disjointness null | **PASS** | **0** overlap with R2's 42 debug-string `high` names; **0** of the 12 calibration ops reach the callback (§5) |
| **C5** cross-check | **PASS** | **27/29** agree with the managed handler's own shape; the 2 survivors are disclosed by name, and the gate pins the set so a third cannot appear unnoticed |
| **C6** dictionary | **PASS** | 29 rows carry a `callback_command`, 28 named from it, **0** confidence-rule violations |

---

## 3. The evidence class

R2 recorded two globals as **diffuse** — too broad to prove anything — and kept them out of the
discriminating evidence (`tier_r_annot.DIFFUSE_GLOBALS`):

```
0x1C1DE8  vramUploadCallback    the host callback slot
0x576A10  psxBankTable          the host<->PSX address bank table
```

**That exclusion is what left the VRAM cluster anonymous, and it is right about the touch and wrong
about what rides it.** Reaching the slot proves nothing — 166 xref sites across the DLL reach it.
But every call through it passes a *command code*, and the managed side of that boundary is open
source:

```
SFX.BattleCallback(Int32 fullCode, arg0..arg3, void* p)     SFX.cs:833
code = fullCode >> 24 ; btlid = fullCode & 255              SFX.cs:837, :958
enum SFX.COMMAND { COMMAND_LOAD_IMAGE = 100, … }            SFX.cs:2330-2384
```

So the name does not come from our inference about a function body. It comes from **Square's own
enumerator**, reached across an ABI whose other half we can read.

### 3.1 ★ THE COMMAND WORD HAS THREE ENCODINGS

The single most consequential mechanical finding, because modelling one of them is not conservative
— it drops sites silently:

```
mov   ecx, 0x64000000                  the code alone, btlid 0
movzx ecx, word ptr [rbx + 0x18]       the btlid …
or    ecx, 0x16000000                  … then the code OR'd over it
bts   ecx, 0x19                        … or one bit set (1 << 25 == code 2)
```

`mov` covers **144 of 204** sites. A mov-only scan — the obvious first implementation, and the one
this round started with — resolves 70% and **loses the very `LoadImage` site A1 published**.

The `or`/`bts` forms are *exact* rather than inferred because of the instruction in front of them:
`movzx` from a word zero-extends, so bits 16..31 are provably clear and the OR/BTS **is** the whole
code. That is why the tracker follows the code byte, not the register.

---

## 4. C1 — the calibration, and the function-model trap it caught

`A1-TEXTURES.md` §5.2 published the VRAM issuer table months earlier, from a direct-call graph over
all 646 functions — an independent method, which is what makes it a control rather than a
restatement. Reproducing it exactly is what licenses everything else.

It did not reproduce at first, and **both failures were mine, not A1's**:

1. **5 of A1's 10 addresses are chained `.pdata` chunks**, not function starts (`0x315f1`,
   `0x31d31`, `0x31f03` → `0x31520`; `0x3dc85` → `0x3dc50`; `0x3de37` → `0x3de20`). This is the trap
   R2 already documented for *names* — and the fix here runs the other way: at UNWIND-primary
   granularity, `0x31520` issues LOAD_IMAGE **and** STORE_IMAGE, so the primary is **coarser** than
   A1's model. Calibrating on primaries would have hidden a real disagreement. **The gate runs on
   chunks, which is the unit that locates a call site.**
2. **Chunk-boundary state.** The page streamer `0x3dc50` loads the callback pointer at `0x3dc7e` and
   calls it inside the *next* chunk. Clearing tracked state at every boundary lost that site; only a
   **non-adjacent** chunk warrants a reset, because adjacent chunks are straight-line continuation.

---

## 5. C4 — the disjointness null

The round's most reassuring number is a zero:

* **0** of R2's 42 debug-string `high` names reach the callback;
* **0** of the 12 independently-known calibration ops reach it.

A noisy method would have collided with some of them. It collides with none. The structural reading:
**the `Hi_*` summon-model family is the DLL's own work and never crosses to managed; the ops that
cross are the battle-unit and VRAM family.** R2's sources ran dry exactly where this one begins —
the two lanes partition the surface. It is also why a callback name can never overwrite a
debug-string name.

R2's own 12-op calibration standard therefore **cannot be run on this evidence class** — there is no
overlap to calibrate against. That is stated, not worked around; C1's A1 control is the substitute,
and it is the only outside claim that speaks about these functions at all.

---

## 6. The names

29 ops resolve to exactly one command; 28 are new (op 174 already had a name, §7). `[n]` is the
sub-mode where the DLL pins `arg0` at every site — several commands multiplex on it, so
`COMMAND_GET_MATRIX` alone covers Get Bone Position / Height / Orientation.

| op | command | calls | conf | signature | named from it |
|---|---|---|---|---|---|
| 32 | COMMAND_GET_MATRIX[0] | 85 | high | `(iip)->void` | yes |
| 131 | COMMAND_GET_ROTATE | 74 | high | `(ip)->void` | yes |
| 177 | COMMAND_GET_MATRIX | 65 | high | `(iip)->void` | yes |
| 33 | COMMAND_GET_MATRIX[0] | 61 | high | `(iip)->void` | yes |
| 203 | COMMAND_CHECK_STATUS[0] | 18 | medium | `(i)->int` | yes |
| 174 | COMMAND_GET_MATRIX[0] | 13 | medium | `(iip)->void` | no — R2 name kept |
| 189 | COMMAND_CREATE_TEXTURE[0] | 13 | high | `(iiiipiii)->int` | yes |
| 1 | COMMAND_STORE_IMAGE | 9 | medium | `(pp)->int` | yes |
| 34 | COMMAND_SET_MOTION | 9 | high | `(ip)->void` | yes |
| 38 | COMMAND_SET_MOTION_FRAME | 9 | high | `(ii)->void` | yes |
| 39 | COMMAND_GET_MOTION_FRAME[0] | 8 | high | `(i)->int` | yes |
| 202 | COMMAND_GET_MOTION_FRAME_MAX[0] | 8 | high | `(i)->int` | yes |
| 211 | COMMAND_LBOSS_FLAG_ENABLE[0] | 7 | high | `()->void` | yes |
| 213 | COMMAND_CHECK_STATUS | 6 | high | `(i)->void` | yes |
| 166 | COMMAND_MOVE_IMAGE | 5 | high | `(pii)->int` | yes |
| 161 | COMMAND_STOP_MOTION | 3 | high | `(i)->int` | yes |
| 0 | COMMAND_LOAD_IMAGE | 2 | high | `(pp)->int` | yes |
| 152 | COMMAND_SHOW_WEAPON | 2 | high | `(ii)->void` | yes |
| 187 | COMMAND_SET_DISAPPEAR | 2 | high | `(ii)->void` | yes |
| 210 | COMMAND_SFX_PLAY[0] | 2 | medium | `(iiii)->int` | yes |
| 138 | COMMAND_EXEC_VFX[0] | 1 | high | `(i)->void` | yes |
| 160 | COMMAND_STOP_MOTION | 1 | high | `(ii)->void` | yes |
| 178 | COMMAND_GET_MATRIX | 1 | high | `(iip)->void` | yes |
| 4 | COMMAND_SET_FPS[0] | 0 | high | `(i)->void` | yes |
| 40 | COMMAND_SET_MOTION | 0 | medium | `(ii)->void` | yes |
| 140 | COMMAND_BTL_2D_REQ[0] | 0 | high | `(i)->void` | yes |
| 176 | COMMAND_EYE_BLINK | 0 | high | `(iii)->void` | yes |
| 197 | COMMAND_GET_MESH_COUNT[0] | 0 | high | `(i)->int` | yes |
| 212 | COMMAND_SFX_PLAY | 0 | high | `(i)->void` | yes |

### 6.1 ★ The three VRAM ops carry the PlayStation prototypes verbatim

An independent confirmation nobody asked for. The op signatures are the **libgpu prototypes**:

| op | command | stub signature | PS1 libgpu |
|---|---|---|---|
| 0 | LOAD_IMAGE | `(ptr, ptr) -> int` | `LoadImage(RECT*, u_long*)` |
| 1 | STORE_IMAGE | `(ptr, ptr) -> int` | `StoreImage(RECT*, u_long*)` |
| 166 | MOVE_IMAGE | `(ptr, int, int) -> int` | `MoveImage(RECT*, int, int)` |

The native function expands the `RECT*` into the callback's four scalar `arg0..arg3`. Consistent
with the DLL's leftover `sonoda\Geo\*.cpp` / `PsxEmulator.cpp` symbols: this is ported PS1 code, and
the HLE boundary preserves the original API shape.

---

## 7. C5 — the cross-check, and the two it flags

Each name is tested against the managed handler's own shape, parsed from C# — an independent source
in a different language. Three contradictions are checked: a handler that returns a value the op
cannot deliver; a handler that delivers through `void* p` where the op passes no pointer; a handler
that reads a selector where the op has arity 0.

**27/29 agree.** The two survivors are **disclosed, not suppressed**:

* **op 160** `COMMAND_STOP_MOTION` `(ii)->void` and **op 213** `COMMAND_CHECK_STATUS` `(i)->void` —
  the managed handlers return the *previous* value (`return stop_anim`) and these wrappers discard
  it. The set-and-discard shape. Their query-shaped twins (op 161 `(i)->int`, op 203 `(i)->int`)
  agree, which is what makes the pair reading credible.

Two flags found during development were **my own parser bugs**, and both are now regression tests:
`COMMAND_LOAD_IMAGE` is an `if (code == 100)` **fast path ahead of the switch** (SFX.cs:840), not a
`case`; and a case body's terminator tested a `"    }"` prefix that never matches the switch's own
8-space `"        }"`, so the last case swallowed the trailing
`return BattleCallbackWithBtl(… p …)` and invented both a `p` use and a return for `SET_FPS`.

### 7.1 The op 174 "conflict" is not one

R2 names op 174 `gte_transform_vertices` (medium, global-derived); the callback says
`COMMAND_GET_MATRIX[0]`. **Both are true at different levels, and the round does not resolve it by
overwriting.**

> **A callback code names the BOUNDARY CROSSING an op performs — a lower bound on its semantics, not
> the whole of them.** Op 174 reads a bone matrix across the ABI *and* transforms vertices with it
> inside the DLL. Where a more specific name already exists, it stands, and the command rides as
> additional evidence.

The same law explains why ops 32, 33, 174 all cross at `GET_MATRIX[0]` with identical signatures:
this evidence class does not separate them. Their DLL-side difference is **unresolved and said so**.

---

## 8. ★ THE DICTIONARY HAD TWO WRITERS — found by this round, in R2's own board

`r2_gates.py:388` rebuilds and **rewrites** `hle_ops.json` as part of its H-board. With the
managed-ABI source wired into the CLI alone, **running the R2 gate board silently reverted all 28
names to null** — and it did, mid-round, which is how it was found.

Fix: `tier_r_annot.rebuild_hle_ops` is now **the single writer**, used by both the CLI and the gate
board, with the managed source optional and loud when absent (Memoria's clone is gitignored and
shared between worktrees). A tripwire test pins it: any file that calls `write_hle_ops` must also go
through `rebuild_hle_ops`.

A second ordering bug was caught by R2's own confidence contract rather than by review: the callback
name was assigned *after* the corpus-disagreement demotion, so ops 1 and 203 kept `high` while the
census disagreed with their stub arity. The fold-in now happens **before** the demotion, and both
sit at `medium`.

---

## 9. What this does NOT do — the honest half

* **The bank cluster barely moved: 24 unnamed ops touch `psxBankTable`, and 2 are now named.**
  `psxBankTable` is host↔PSX address translation, not a callback path — this lever does not reach
  it, and no amount of running it further will. Naming those needs handler-body reading, which is a
  different rung.
* **19 ops reach the callback and are REFUSED**, carrying **832 call sites** — more traffic than the
  round named. They cross at several commands and this evidence class cannot say which is the op:

  | op | calls | commands crossed |
  |---|---|---|
  | 128 | 305 | GET_POSITION, GET_MATRIX, CHECK_STATUS, GET_SLAVE |
  | 127 | 211 | GET_POSITION, GET_MATRIX, GET_SLAVE |
  | 129 | 89 | SET_POSITION, GET_SLAVE |
  | 126 | 61 | GET_POSITION, GET_SLAVE |
  | 182 | 57 | GET_POSITION, GET_MATRIX, GET_SLAVE, SFX_PLAY |
  | 175 | 38 | GET_DISAPPEAR, SET_DISAPPEAR, CHECK_STATUS, GET_SLAVE, SHOW_MESH |
  | 170 / 169 / 168 | 25 / 23 / 18 | SET_ROTATE·GET_SLAVE / SET_SCALE·GET_SLAVE / GET_SCALE·GET_GEO_FLAG |
  | 183, 130, 186, 42, 107, 110, 134, 135, 137, 156 | ≤3 each | (110 crosses 19 commands — a dispatcher) |

  **A resolver rule was measured and REJECTED.** `COMMAND_GET_SLAVE` looked like a target-resolution
  query issued before the payload command (it is issued first in 7 of 8 such functions, and appears
  alone in 3 small helpers). Promoting that to a law would have named ~8 of these ops — and
  `0x148f0` issues `GET_ROTATE` **before** `GET_SLAVE`, so the ordering does not hold. The rule was
  dropped rather than shipped with one exception.
* **The traffic gain is modest and should not be oversold: 51.8% → 54.5% of call sites.** The
  genuinely high-volume unknowns (op 117 @ 1,709, op 136 @ 510, op 48 @ 451, op 50 @ 378, op 64 @
  366, op 206 @ 339) **do not reach the callback at all** and are untouched by this round.
* **The H2 contract's "a name the DLL itself supplies" clause is documented but not enforced** —
  `check_confidence_rule` checks evidence *structure*, not name source, so a managed-ABI name passes
  it structurally. Recorded here rather than exploited; tightening it is a change to R2's frozen
  board and belongs to whoever owns that decision.

---

## 10. Coverage

| | before | after |
|---|---|---|
| named ops | 79 / 216 | **107 / 216** |
| confidence | high 42 · med 27 · low 10 · unnamed 137 | **high 66 · med 31 · low 10 · unnamed 109** |
| call-site traffic named | 7,361 / 14,212 (51.8%) | **7,752 / 14,212 (54.5%)** |
| VRAM cluster (39 unnamed touching the callback slot) | 0 named | **26 named**, 389 call sites |
| bank cluster (24 unnamed touching `psxBankTable`) | 0 named | **2 named**, 1 call site |

---

## 11. Provenance

* **Zero stock bytes.** `callback_ops.py`, `cb_gates.py`, `test_callback_ops.py` and this report
  contain names, RVAs, offsets, mnemonics and statistics only. The `SFX.COMMAND` enum is **parsed at
  runtime** from the user's own Memoria clone, never transcribed into the repo — a hardcoded copy of
  another project's enum is a fact with no owner, and this one is the whole naming authority.
* **The DLL was never modified**, only read (`pefile` + capstone via `refkit`), including `.pdata` /
  UNWIND_INFO. No patched `FF9SpecialEffectPlugin.dll` was produced and none ever will be.
* The tests run green without the DLL and without Memoria's source (the managed-parser cases use an
  inline fixture), so the committed artifact stays verifiable from the repo alone.

---

# ADDENDUM — op 117, the handler-body lane

**Status: ★ DONE. `body_gates.py` 5/5, 13 new tests (tier-r 175). Named ops 107 → 108; call-site
traffic 54.5% → 66.6%.**

§9 named op 117 as the best remaining target and said naming it needed a different rung: it does not
touch the callback, so neither R2's sources nor the managed-ABI class reaches it. At **1,709 call
sites it is the single most-called op in the corpus** — 12% of all HLE traffic in one op.

## What the body says

`op 117`'s native function `0x306f0` is a **thin forwarder**: it shuffles the two arguments into
`r8`/`r9` and **tail-jumps** to `0x34380`, passing a pool descriptor and a context object.
`0x34380` is an **allocator + relocator**:

1. scans a pool of **`0x6C`-byte records** (descriptor `0x3210d0`: count `+0`, high-water `+8`,
   array `+0x10`) for one whose `+0x30` is zero, and **returns 0 when the pool is full**;
2. zeroes it, marks `+0x30 = 1`, binds a **`0x1FE0`-byte work buffer** carved by slot index from the
   static array at `0x587520`;
3. converts the caller's blob pointer to a PSX address (`fn 0x12940` against `psxBankTable`) → `+0x00`;
4. **relocates the blob** — header `0x10` if `blob[0] == 0xff` else `0x28`; `u16` count at `+0x04`;
   a **`0x28`-stride entry array at `+0x14`**; per entry, `byte+0x00 != 9` promotes `u32 +0x1c` and
   `byte+0x01 != 0xff` promotes `u32 +0x20` from a blob-relative offset (`<= 0x27ff`) to an absolute
   PSX address;
5. stores the table's start/end at `+0x18`/`+0x24`, the second argument at **`+0x28` and `+0x2c`**
   (a cursor and its base), and returns the record.

**The family.** `0x3210d0` and the context object `0x211e68` are referenced by exactly the same six
functions — four of which are **consecutive ops on consecutive addresses**: `116` (`()->void`, a pool
reset), `117` (open), `118` (`(pp)->void`), `119` (`(p)->void`, which marks `+0x30 = -1` and walks a
second table restoring a saved byte on every slot bound to the handle). Open / operate / close.

**The real call idiom**, straight out of ef227's annotated listing:

```
jalr  get_subfile_ptr          ; op 102, $a1 = 0x83  (& 0x7F -> sub-file 3)
addu  $a0, $v0, $zero          ; a0 = the sub-file pointer
jalr  op 117                   ; op117(subfile, $s3+64)
addu  $v1, $v0, $zero
beq   $v1, $zero, skip         ; NULL-CHECKED -- exactly the pool-full return
sh    $v0, 34($v1)             ; handle->[0x22] = 128
```

## The corpus tests — each could have refuted it

| gate | result |
|---|---|
| **B3** op-117 sites immediately preceded by a constant-index `op 102` | **1,680 / 1,709 = 98.3%** |
| **B4** the relocator's reading validates on the sub-files actually fed to op 117 | **986 / 1,584 = 62.2%** |
| **B4** …versus every other sub-file in the same chunks (the control) | **383 / 5,978 = 6.4%** |
| **B5** overlap with the **759** camera sub-files across 356 containers | **0** |

A ~10× separation on B4 — the same shape of evidence that named op 102 (98.80% vs a 67.7% control).
B5 rules out the camera lane by measurement rather than by argument.

## What is deliberately NOT claimed

**38% of the fed sub-files do not satisfy the reading, and relaxing the sub-file bound to the region
end does not recover a single one (62.2% either way).** So this is not a bounds artifact — there is
real structure here that this pass does not model, most likely more header variants than the one
`blob[0] == 0xff` discriminator. Accordingly:

* the name describes the **mechanism, not the content domain**:
  **`op 117 = subfile_instance_open`** — *open a pooled runtime instance of a sub-file, relocating
  its internal offset table to absolute PSX addresses; returns the record, or NULL when the pool is
  full*;
* it ships at **`medium`**, never `high` — **no symbol anywhere in the chain supplies a name**, and
  R2's contract reserves `high` for a name a source actually states;
* ops 116/118/119 are **identified as the family but not named**: the A/B test was run for 117, and
  a family argument is not a measurement.

## ★ A second gap in R2's name resolver

R2 resolves a name from debug strings **owned by an op's own function**, so a tail-call forwarder
hides its callee's symbol. Op 117's chain has no symbol either way, so it does not benefit — but the
sweep found one op that does:

> **op 206** (339 call sites) tail-jumps to functions owning **`Hi_RegisterTexListModel`** and
> **`Hi_RegisterGouEffModel`**.

Two names, so R2's exclusivity rule would refuse it, and it is **left unnamed here** rather than
guessed — but it is now a *bounded* question rather than a blank, and it is the natural next target.
`body_ops.tailjump_name_gap()` computes the whole gap (2 ops today), and a test pins it.

## Coverage

| | after the callback round | after op 117 |
|---|---|---|
| named ops | 107 / 216 | **108 / 216** |
| confidence | high 66 · med 31 · low 10 · unnamed 109 | **high 66 · med 32 · low 10 · unnamed 108** |
| call-site traffic named | 7,752 / 14,212 (54.5%) | **9,461 / 14,212 (66.6%)** |

One op, **+12.1 points** of traffic — the whole point of ranking the remaining work by call sites.

---

# ADDENDUM 2 — op 206, the variant dispatcher

**Status: ★ DONE. `body_gates.py` 8/8, 11 more tests (tier-r 183). Named 108 → 109; traffic
66.6% → 69.0%. Ships at `high` — the DLL supplies the name, twice.**

The op-117 round left op 206 (339 sites) as "a bounded question rather than a blank": its function
tail-jumps to two functions owning **`Hi_RegisterTexListModel`** and **`Hi_RegisterGouEffModel`**, and
R2's exclusivity rule refuses two names. Reading the body resolves it — **it is not ambiguous, it is
a dispatcher, and the selector is a field in the operand.**

## The body — and prior art reproduced exactly

`fn 0x47290` (source `..\..\SpecialEffectCode\psx\source\psx_compatibility.cpp`, line 786):

```
eax = 0x6f73 ; cmp word[rcx], ax ; je ok        ; assert the 'so' magic  -> else _wassert
ok: cmp word[rbx+2], 0                          ; THE VARIANT SELECTOR
    eax = word[rbx+4]                           ; record length
    je  gouraud                                 ; variant == 0 -> no bindings to touch
    r10 = (eax - 8) >> 3                        ; entries = (len - 8) / 8
    di  = (arg1 & 3) << 5                       ; the PSX TPAGE ABR field
    loop: or word[rbx + 8 + 4*i], di            ; OR -- never assign
    jmp 0x15d30                                 ; -> Hi_RegisterTexListModel
gouraud:
    jmp 0x15b70                                 ; -> Hi_RegisterGouEffModel
```

**This reproduces `A1-TEXTURES.md` §3.5 exactly** — the `(arg & 3) << 5`, the `+8 + 4*i` stride, the
`(u16[+4] - 8)/8` count — a claim derived months earlier by a different method, on which the whole
`so_record` / scenery-attribution pillar rests. **A1 was right and complete about the ABR half; what
it did not have is the tail — the branch and the two registrars.** Both targets are `.pdata`
primaries owning exactly one debug string each, so this is a real tail call, not a jump into a body.

## The corpus tests

| gate | result |
|---|---|
| **B6** op 206's body + both tail-call names re-derive from the installed DLL | **PASS** |
| **B7** the `'so'` magic on heuristically-paired operands vs the control | **184/274 = 67.2%** vs **71/1,905 = 3.7%** (18×) |
| **B7** variant split among validated operands | **168 tex-list / 16 gouraud** |
| **B8** misses carrying the magic at *any* nonzero offset | **0** |
| corpus `$a1` values | **339/339** ∈ {0,1,2,3,255} — every one a valid ABR selector under `&3` |

**B8 is the one that matters, and it inverts the usual reading of a shortfall.** The DLL *asserts*
the magic, so a real operand cannot lack it — and the 90 misses contain `'so'` at no offset at all.
Combined with only **2 of 339** sites passing a constant `$a0`, the 33% gap measures **my pairing
heuristic's error rate, not the claim**. The op's own assert is what proves that.

The `$a1` distribution is its own corroboration: **1 (additive) dominates at 222/339**, exactly what
a VFX system reaches for, and `255 & 3 == 3` so even the odd value is a legal mode.

## The name

**`op 206 = Hi_RegisterTexListModel|Hi_RegisterGouEffModel`**, at **`high`** — the disjunction is not
hedging, it is what the op *is*: a dispatcher whose two arms the DLL names itself, with the selector
(`u16[operand+2]`) decoded and the split measured. Contrast op 117, which ships `medium` because no
symbol anywhere in its chain supplies a name.

## ★ A new string class: `_wassert` source files

The assert that pinned op 206 also opened a resource R2 could not see. `_wassert` takes **UTF-16**
strings and R2's name resolver scans **ASCII** runs, so every `file:line` in the DLL was invisible.
`body_ops.wassert_sources()` now recovers them:

```
..\..\SpecialEffectCode\psx\source\psx_compatibility.cpp
..\..\SpecialEffectCode\sonoda\Geo\geo.cpp
..\..\SpecialEffectCode\sonoda\Geo\geomorph.cpp
..\..\SpecialEffectCode\sonoda\Geo\geosfxrender.cpp
..\..\SpecialEffectCode\sonoda\Geo\geoslice.cpp
..\..\SpecialEffectCode\sonoda\PsxEmulator.cpp
```

**Reach measured, and modest: 6 files over 20 functions, 9 of which are an op's own native
function.** So this is an attribution aid — it tells you which module an op lives in — **not a naming
lane**, and it is reported as such rather than as a new rung.

## Coverage

| | after op 117 | after op 206 |
|---|---|---|
| named ops | 108 / 216 | **109 / 216** |
| confidence | high 66 · med 32 · low 10 · unnamed 108 | **high 67 · med 32 · low 10 · unnamed 107** |
| call-site traffic named | 9,461 / 14,212 (66.6%) | **9,800 / 14,212 (69.0%)** |

Across the three rounds: **79 → 109 named, 51.8% → 69.0% of traffic.**

---

# ADDENDUM 3 — op 136, and a guess corrected by looking

**Status: ★ DONE. `body_gates.py` 9/9, 4 more tests (tier-r 187). Named 109 → 110; traffic
69.0% → 72.5%.**

op 136 (510 sites, `(int,int)->int`) is **four instructions of work**, and the body alone does not
name it. What names it is **where the result goes**.

## The body

```
mov  ebx, edx                  ; base  = arg1
call 0x44a60                   ; actor = lookup(arg0)
mov  eax, 0xaaaaaaab
mul  dword [rcx + 0x38]        ; unsigned magic divide...
shr  edx, 2                    ; ...by 6
lea  eax, [rbx + rdx]          ; return base + actor[+0x38] / 6
```

**The actor lookup `0x44a60` is worth having on its own** — it is the DLL's actor table, and it
states its own index space through two `_wassert`s:

| index | meaning |
|---|---|
| `0 .. 7` | party members, count at `ctx+0x24` |
| `8 .. 15` | enemies, count at `ctx+0x27` |
| `0x10`, `0x11` | two singleton slots (`ctx+0x50`, `ctx+0xb8`) |

op 136's `$a0` is only ever **0** (×340) or **16** (×120) — party member 0, and the `+0x50`
singleton. Its `$a1` is **always a power of two**: 128 (×237), 32 (×153), 64 (×46), 256 (×18),
16 (×14), 512 (×13).

## What names it — the destination

**436 of op 136's 510 sites sit beside op 117**, and the corpus idiom is exact:

```
jalr op117                      ; handle = op117(subfile, ...)
sw   $v0, 4($s2)                ; save it
jalr op136  ($a0=0, $a1=0x20)
sh   $v0, 34($v1)               ; handle->[0x22] = op136(...)
```

`+0x22` is the field op 117's allocator explicitly zeroes, and the field **ef227 sets to the literal
128** — itself one of op 136's own `$a1` values. So op 136 computes a per-instance property that is
otherwise a constant.

**And then I was wrong about which property, and looking is what fixed it.** A signed (`movsx`) read
of `+0x22` in a model-registration neighbourhood reads like an ordering-table bias, and that was the
working hypothesis. The per-tick function `0x34860` refutes it:

```
movsx ecx, word [rbx + 0x22]
movsx eax, word [rbx + 0x20]      ; loaded TOGETHER, as a pair
mov   [0x211fe4], eax             ; GTE input slots
mov   [0x211f94], ecx
call  0x4930                      ; project
```

`+0x20` and `+0x22` go into GTE input registers together and are projected; a parallel branch feeds
the same two globals from another record's `+0x18`/`+0x1a`. **`+0x22` is a coordinate component, not
a sort key.**

## The name

**`op 136 = actor_relative_coord`**, at **`medium`** — *a coordinate component placed relative to an
actor: `base + actor[+0x38] / 6`.*

## What is deliberately NOT claimed

**`actor[+0x38]` is not identified**, and there is a specific reason to say so loudly: it is
tempting to reach for Memoria's open-source `BTL_DATA_INIT`, which carries exactly the plausible
fields (`enemy_radius`, `geo_radius`, `geo_height`). Tracing `SFX_InitBattle`'s copy shows **all 17
of its fields land, in order, on other offsets**:

| BTL_DATA_INIT | → runtime | | BTL_DATA_INIT | → runtime |
|---|---|---|---|---|
| `bi_player` | `+0x00` | | `enemy_radius` | `+0x18` |
| `bi_slot_no` | `+0x01` | | `geo_radius` | `+0x28` |
| `bi_line_no` | `+0x02` | | `geo_height` | `+0x2c` |
| `tar_bone` | `+0x0a` | | `btl_id` | `+0x08` |
| `player_serial_no` | `+0x10` | | `enemy_cam_bone0..2` | `+0x1d..+0x1f` |

**`+0x38` is not among them** — it is a DLL-computed runtime field. Neither the axis (which of the
GTE pair is X vs Y) nor the divisor's meaning is pinned, so the name says *coordinate component*
and stops. Sibling **op 124** exposes the same pair as an HLE getter (`+0x28` normally, `+0x38` when
bit 8 of its argument is set — its `$a0` constants are exactly `0` and `256`), so a future rung has a
second handle on the same field.

## Coverage

| | after op 206 | after op 136 |
|---|---|---|
| named ops | 109 / 216 | **110 / 216** |
| confidence | high 67 · med 32 · low 10 · unnamed 107 | **high 67 · med 33 · low 10 · unnamed 106** |
| call-site traffic named | 9,800 / 14,212 (69.0%) | **10,310 / 14,212 (72.5%)** |

Across R4–R7: **79 → 110 named, 51.8% → 72.5% of traffic.**

---

# ADDENDUM 4 — ops 48 / 49 / 50: one algorithm, and a decoder bug

**Status: ★ DONE. `body_gates.py` 10/10, 5 more tests (tier-r 191). Named 110 → 113; traffic
72.5% → 78.9%.**

The brief was ops 48 and 50. They turned out to be **two thirds of one algorithm**, so op 49 came
with them — leaving it unnamed would have been arbitrary, since it is named by identical evidence.

## The algorithm names itself

All three drive the same LCG on the shared state at `0x3231dc`:

```
seed = seed * 0x41C64E6D + 0x3039 ;  value = seed >> 16
```

`0x41C64E6D` = **1103515245** and `0x3039` = **12345** — the multiplier/increment pair of the
**ANSI C `rand()` LCG**, the one from the C standard's own example implementation. That is a
published external prior, not an inference about purpose: the constants identify the algorithm the
way an import name would.

| op | name | what it computes | sites |
|---|---|---|---|
| 48 | **`rand`** | the raw draw, `seed >> 16` | 451 |
| 49 | **`rand_range`** | `lo + rand() % (hi - lo)`; returns `lo` when `lo == hi`, **without advancing the seed** | 78 |
| 50 | **`rand_centered`** | `rand() % n - n/2`, a jitter centred on zero; `n == 0` guarded to 1 | 378 |

**The corpus argument distributions confirm each shape independently:**

* op 49's `$a0` constants are **negative** — `-256`, `-32`, `-64`, `-96`, `-128` — and its `$a1` the
  positive counterparts (`256`, `32`, `64`, `96`, `128`). A `(lo, hi)` range, symmetric.
* op 50's `$a0` is **always a power of two or a multiple**: 256 (×78), 128 (×35), 512 (×30), 32
  (×17), 1024 (×15), 384 (×14) — i.e. jitters of ±128, ±64, ±256, ±16, ±512, ±192.
* op 48 takes no argument at all, and its top co-call is **op 15 `rsin_fixed_point`** (×52) — random
  values feeding trig, exactly what scatter/jitter work looks like.

## Why `medium` and not `high`

R2's contract rates **a thin CRT wrapper `high`** — that is precisely how `rsin`/`rcos` got their
names, because the DLL *imports* `sin`/`cos`. These ops are the C library's `rand()` too, just
**inlined rather than imported**, and inlining is a codegen choice rather than a semantic one. The
asymmetry is real and worth recording — but they still ship `medium`, because **no source in the
binary states a name**, and inflating that is exactly the confident-wrong-name defect the contract
exists to prevent.

## ★ A decoder bug in R2's stub reader — three ops were wrongly VOID

op 50's stub inlines the LCG and ends:

```
mov r12d, edx          ; <- the return value IS delivered
jmp 0x122f1            ; the int tail-return
```

R2's stub decoder matched only the literal `mov r12d, eax`, so it read op 50 — **378 call sites** —
as returning `void` when it plainly returns a value. Swept across all 216 stubs, the r12d source
register is `eax` 55 times and something else **3** times, and all three were mis-typed:

| op | stub sets r12d from | was | now | sites |
|---|---|---|---|---|
| **50** | `edx` | `void` | `int` | **378** |
| 43 | `ecx` | `void` | `int` | 0 |
| 16 | `0x400` (a constant) | `void` | `int` | 3 |

Fixed by matching **any** write to `r12d` before the tail return — the register a value happens to
arrive in is a codegen detail, not part of the ABI. Bounded, measured, and pinned by a test. The
confidence board is unaffected (`check_confidence_rule` still returns 0 violations) and R1/R2/R3/CB
all still pass.

## Coverage

| | after op 136 | after 48/49/50 |
|---|---|---|
| named ops | 110 / 216 | **113 / 216** |
| confidence | high 67 · med 33 · low 10 · unnamed 106 | **high 67 · med 36 · low 10 · unnamed 103** |
| call-site traffic named | 10,310 / 14,212 (72.5%) | **11,217 / 14,212 (78.9%)** |

Across R4–R8: **79 → 113 named, 51.8% → 78.9% of traffic.**

---

# ADDENDUM 5 -- op 64: the full-screen colour fill (and a second decoder blind spot)

**Status: * DONE. `body_gates.py` 12/12, 6 more tests (tier-r 197). Named 113 -> 114;
traffic 78.9% -> 81.5%.**

## What it does

`fn 0x3f180` carves `0x80` bytes off the arena cursor at `sysCtx+0x24` and fills the block with
**eight 0x10-byte PS1 `TILE` primitives** -- `{u32 tag; u8 r,g,b,code; u16 x,y; u16 w,h}` -- then
hands each to `fn 0x3edb0`.

The eight tiles are laid out `x = (i & 3) * 80`, `y = (i >> 2) * 110`, each `80 x 110`. That is a
**4x2 grid**, and:

> **4 x 80 = 320 . 2 x 110 = 220** -- the PS1 screen. (This project already pins
> `FieldMap.PsxScreenHeightNative = 220`.)

So the op paints the **whole screen** one flat colour: `op 64 = draw_fullscreen_fill`.

`fn 0x3edb0` is libgpu **`AddPrim`**: it moves the length into the tag's top byte (`shr ecx, 0x18`)
and XOR-splices the primitive into the ordering table through a **24-bit** link (`and 0xffffff`) --
the standard PS1 OT insert. **`op 143`'s own native function IS `0x3edb0`**, so the corpus has a
directly-exposed `AddPrim` too (an unclaimed lead).

`arg1` does double duty: it is the OT depth handed to `AddPrim`, **and** `== 0xFF` selects the
opaque rectangle code `0x60` while anything else selects `0x62`, its semi-transparent twin (bit 1 is
the PS1 rectangle ABE flag). `AddPrim` special-cases `0xFF` again internally, so it is a sentinel
depth rather than a real one.

## The corpus tests, including the one that could have refuted it

* **412 / 412 (100%)** of op 64's `$a2`/`$a3` constants are colour bytes `<= 255`, against
  **987 / 1609 (61.3%)** for the control (every other op with at least three integer arguments).
* `$a1` corpus-wide is **exactly `{0, 1, 2, 255}`** -- a tiny depth set plus the sentinel.
* A real call site (`ef004_c0` @ `0d5c`) builds the three colour channels as **three shifts of one
  animated scalar**: `sra $a2, $v0, 4` / `sra $a3, $v0, 3` / `sra $v0, $v0, 2` -> `sw $v0, 16($sp)`
  -- i.e. `r = v/16, g = v/8, b = v/4`, a blue-dominant tinted wash driven by one fade level.
  **Coordinates or ids could not look like that.**

Ships **`medium`**: no symbol anywhere on the chain states a name.

## * A SECOND DECODER BLIND SPOT -- an undercounted arity

That same call site ends `sw $v0, 16($sp)` immediately before the `jalr`: **O32's first stacked
argument slot, arg index 4.** op 64 takes **five** arguments, not four.

R2 detects stacked arguments, but only while the translated MIPS `$sp` still lives in `rax`:

```
mov  edx, [rdi+r13+0xd0c]   ; the MIPS $sp
call 0x10e0                 ; -> rax = host($sp)
mov  rbx, rax               ; <-- stashed, because the next call clobbers rax
call 0x12740                ; getArgPtr(0)
mov  eax, [rbx + 0x10]      ; arg 4 -- invisible to a decoder watching rax
```

Fixed by following the value through the register move. **Bounded and measured: exactly two ops
gain an argument** -- `op 64` (4 -> 5) and `op 70` (4 -> 5) -- and R2's 12-op calibration still
re-derives on name **and** arity, 12/12.

**Independent corroboration:** `M3-opcode-table.json`, derived from the **x86** build's `[ebp+N]`
stack frame -- a different binary, a different method -- says **arity 5 for both**. Both ops are in
R2 finding 4's own disagreement list, so that finding's blanket *"prefer `hle_ops.json`"* was too
broad: **on stacked-argument arity, M3 was right and the x64 stub decoder had the blind spot.**
The disagreement set shrinks from 19 ops to 17.

## Coverage

| | after 48/49/50 | after op 64 |
|---|---|---|
| named ops | 113 / 216 | **114 / 216** |
| confidence | high 67 . med 36 . low 10 . unnamed 103 | **high 67 . med 37 . low 10 . unnamed 102** |
| traffic named | 11,217 / 14,212 (78.9%) | **11,583 / 14,212 (81.5%)** |

Across R4-R9: **79 -> 114 named, 51.8% -> 81.5% of traffic.**

---

# ADDENDUM 6 -- op 143: AddPrim with a blend prefix (and it CORRECTS op 64)

**Status: * DONE. `body_gates.py` 14/14, 5 more tests (tier-r 202). Named 114 -> 115;
traffic 81.5% -> 81.6%.** The traffic gain is trivial -- 9 call sites -- but this rung was worth
running for what it says about the op it shares a function with.

## Two halves

`fn 0x3edb0` is libgpu's **`addPrim`**, and op 143 exposes it directly (op 64 reaches the same
function eight times per call).

**1. The splice.** Length out of the tag's top byte (`shr ecx, 0x18`; `mov [r8+3], cl`), then the
standard PS1 ordering-table insert -- XOR-swapping only the low **24 bits** of `*ot` and
`prim->tag`, so each word keeps its own top byte. The `and 0xffffff` pair is the giveaway.

**2. The blend prefix.** Unless `arg3 == 0xFF`, it carves **8 more bytes** off the same arena cursor
op 64 uses, builds a 2-word primitive (length 1) whose single payload word is:

```
0xE1000200 | ((arg3 & 3) << 5)
```

`0xE1` is the PS1 GPU **GP0 Draw Mode** command: **bits 5-6 are the ABR semi-transparency mode**,
bit 9 is dither. That is a **`DR_TPAGE`** -- the state primitive the s76 probe already logs, and the
same ABR field `op 206` ORs into `so` bindings by a different route. Because `addPrim` inserts at
the **head**, the prefix is drawn **first**: set the blend, then draw.

## ** It corrects op 64

op 64 hands its `arg1` straight into this parameter (`mov r9d, esi`). So:

> **op 64's `arg1` is a BLEND MODE, not an OT depth.** ADDENDUM 5 read it as a depth; that was wrong.

The corpus fits a blend mode far better. `$a1` is `1(x254) 2(x72) 255(x13) 0(x4)`:

| value | as an ABR mode | sites |
|---|---|---|
| **1** | **B+F -- additive** | **254** |
| 2 | B-F, subtractive | 72 |
| 255 | opaque; emit no draw-mode primitive at all | 13 |
| 0 | B/2 + F/2, 50/50 | 4 |

Additive dominating at 254/366 is exactly what a full-screen VFX flash wants; "OT depth 1" explained
nothing. And **there is no depth argument anywhere in either op** -- the OT *pointer* is the depth,
the way PS1 code always does it (`&ot[z]`).

The evidence string, the module docstring and the B12 gate label are all corrected; a test pins the
corrected reading so a silent revert fails loud.

## The corpus test

`arg0` should be a primitive **tag**: length in the top byte, 24-bit link field zeroed.

* **op 143: 9 / 9 (100%)** -- `0x04000000` x4 and `0x08000000` x5, i.e. 5-word and 9-word primitives.
* control (every other op whose `arg0` is an int): **73 / 2086 (3.5%)** -- a ~29x separation.

Ships **`medium`**: `fn 0x3edb0` owns no debug string. Same posture as the RNG family -- a
universally documented external shape (libgpu `addPrim`, GP0(E1h)) but no name stated in the binary.

## Coverage

| | after op 64 | after op 143 |
|---|---|---|
| named ops | 114 / 216 | **115 / 216** |
| confidence | high 67 . med 37 . low 10 . unnamed 102 | **high 67 . med 38 . low 10 . unnamed 101** |
| traffic named | 11,583 / 14,212 (81.5%) | **11,592 / 14,212 (81.6%)** |

Across R4-R10: **79 -> 115 named, 51.8% -> 81.6% of traffic.**

---

# ADDENDUM 7 -- op 128: the actor anchor point, and why "multi-command" was never ambiguity

**Status: * DONE. `body_gates.py` 16/16, 5 more tests (tier-r 207). Named 115 -> 116;
traffic 81.6% -> 83.7%.**

## The refusal this rung lifted

The callback lane **refused** op 128 for reaching **four** commands -- `GET_POSITION(1)`,
`GET_MATRIX(14)`, `CHECK_STATUS(20)`, `GET_SLAVE(22)` -- on the rule that a multi-command op cannot
be named by its command. Reading the body shows the rule, not the op, was the problem:

> **The four commands are four routes to ONE answer: *where is this actor's anchor point?***

**A multi-command op is only ambiguous when the commands are unrelated.** That correction is the
reusable part of this rung, and it is what makes the remaining refusals worth revisiting.

## What it does

`fn 0x450c0` is a thin forwarder: it resolves the actor through `fn 0x44a60` -- **the same index
space op 136 uses** (`<8` party, `8..15` enemy, `0x10`/`0x11` the two special slots) -- and
**tail-jumps** to `fn 0x44f80`, hiding the work from R2's name resolver exactly as op 206's did.
There:

| step | command | what it settles |
|---|---|---|
| 1 | `GET_SLAVE(22)` | is this unit attached to another? |
| 2a | `GET_MATRIX(14)` | a slave takes its bone `byte[actor+0x1a]` |
| 2b | `GET_POSITION(1)` (`bts ecx, 0x18`) | an ordinary unit takes its own position |
| 3 | -- | height from `actor+0x3c`, **halved when the mode argument is 0** |
| 4 | `CHECK_STATUS(20)` sub-mode 1, mask `0x200000` | **`BattleStatus.Float`** -> take `0x80` back off |

then `word[out+2] -= height` -- so **`out` is an i16 `x/y/z` triple and `+2` is Y**.

**The Float correction is the detail that proves the reading.** `0x200000` is `1 << 21` =
`BattleStatus.Float` in Memoria's open-source enum, and a floating unit's *reported position is
already raised* -- so the anchor correction has to subtract that lift back out or it would
double-count it. Nothing but a body-anchor calculation needs that fix.

So: **`op 128 = get_actor_anchor`** -- body centre at mode 0, a second bone (`byte[actor+0x2f]`) at
mode 1. 305 sites across **223 of 385 images**: nearly every effect needs to know where its target
is. It is the natural sibling of op 136 `actor_relative_coord`, and they share a lookup.

## The corpus test

`arg2` is an **out-pointer**, so every constant should land in the PSX address space:

* **op 128: 11 / 11 (100%)** are PSX RAM pointers.
* control (every other op whose own `arg2` the decoder typed as an int): **0 / 928 (0.0%)**.

A clean separation. Supporting: `$a0` is only ever `{0, 16}` -- op 136's actor indices -- and `$a1`
only `{0 x289, 1 x15}`, the two height modes.

Ships **`medium`**: nothing on the chain owns a debug string.

## Coverage

| | after op 143 | after op 128 |
|---|---|---|
| named ops | 115 / 216 | **116 / 216** |
| confidence | high 67 . med 38 . low 10 . unnamed 101 | **high 67 . med 39 . low 10 . unnamed 100** |
| traffic named | 11,592 / 14,212 (81.6%) | **11,897 / 14,212 (83.7%)** |

Across R4-R11: **79 -> 116 named, 51.8% -> 83.7% of traffic.** The unnamed count is now under 100.
