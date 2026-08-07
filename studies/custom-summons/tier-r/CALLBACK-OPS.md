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
