# W7 — THE TEXANIM READ (the rung that turned a refusal into a lift)

> **W5 minted a refusal it could not answer.** Five stock creature packages carry a non-empty
> **texanim** region between the id-5 model image's geometry block and its first motion clip, and
> because nobody had read that region's format, both edit levers refused a creature edit on all five —
> the CLUT recolour outright (`reskin`), the texel repaint outright and with no key at all (`repaint`).
> The gate's own words were *"this is not a knob: read the table first."* **W7 read the table.** It is
> a **texel-blit clip table**, it can express no CLUT change at all, and on the PC port nothing runs
> it. The refusals lift; what replaces them is one **obligation** (co-transform the frame strip) and
> one new **hard rule** (never touch the region or `firstBlock`), and the hard rule is worth more than
> the lift.

**STATUS: ★ BUILT, OFFLINE-PROVEN — the cast is pending.** New kit module
`ff9mapkit/ff9mapkit/summons/texanim.py` (a **reader**, no writer) + `test_summon_texanim.py`; both
lanes' gates rewritten in place; `w7_gates.py` 5/5, `w5_gates.py` 9/9 (its G3 **inverted** to
`G3′ THE FIVE TEXANIM LIFTS`), `w6_gates.py` 7/7 (its G4 texanim row replaced by the **L3/L4
matrix**). Nothing was deployed and no game or install byte was written by this rung.

| | |
|---|---|
| armed packages | **ef038** (116 B) · **ef177 / ef493 / ef494 / ef495** (364 B each, **byte-identical** — one creature shipped four times) |
| what the region is | `u32 clipCount` + 20-byte **clip** records + 12-byte destination **window** records + packed 4-byte **frame** lists — three sub-arrays that tile the region exactly |
| what it describes | a **texel blit**: a `w×h` rect of 8-bit palette **indices** copied inside ONE creature part's own 128×128 page |
| what the engine does with it | **three state-byte writes and nothing else** — there is no ticker, no draw-path read, no VRAM write |
| what lifted | creature recolour · scenery recolour · whole-page texel repaint · localised texel repaint once the frame strip is co-transformed |
| what is new and permanent | **THE REGION INVARIANT** — `firstBlock`, `min(motionOffsets)` and the region's own bytes, asserted unchanged after every splice, in both lanes |

**This supersedes [`W6-TEXEL.md`](W6-TEXEL.md) §1.9** (*"TEXANIM — the gate is right, and its reason is
now stateable"*). That section decoded the region's **outer envelope** — `u32 count` + `count` 20-byte
records, pointers closing inside the region — and was right about all of it. Its two conclusions are
what W7 corrects: the records are not one flat array (there are three sub-arrays at strides 20 / 12 /
4), and of the "two surviving readings" only **one** survives (the blit; the *moving sample window*
reading is falsified — every frame rect contains **0** model UV entries on 39/39 clips). W6-TEXEL §1.9
is left standing rather than rewritten, per this tier's own house rule: a superseded reading stays on
the record so a later reader does not re-cite it.

**Recon provenance.** Three parallel lanes, none of which touched the repo: **A1** static
disassembly of the user's own installed `FF9SpecialEffectPlugin.dll` (x64 *and* x86), **A2**
measurement over the 372-container stock dump corpus, **A3** a `file:line` census of this repo plus
`Actions.csv` in the live install. Their dossiers and the decision document are **SCRATCH-only**:

* `C:\gd\SCRATCH\summon-format\texanim-w7\SYNTHESIS.md` — the decision document this record distils
* `C:\gd\SCRATCH\summon-format\texanim-w7\engine\A1-ENGINE.md` · `bytes\A2-BYTES.md` · `kit\A3-KIT.md`
* `C:\gd\SCRATCH\summon-format\texanim-w7\bytes\clips.json` — the machine-readable protected rect set

---

## 1. THE FORMAT

### 1.1 The reconciled spec

Region = `[firstBlock, min(motionOffsets))`, header-relative — **the kit's pre-existing
`reskin.texanim_region()` definition, now confirmed by the loader's own arithmetic** rather than by our
inference. The id-5 loader computes `header[+0x40] = psx(header + firstBlock)`, and
`Hi_RegisterSummonModel` stores that same value into `SummonData+0x70`. **The span the kit measures IS
the object the engine is handed**, which is why that function's signature and semantics are pinned and
must not drift. Every offset below is REGION-RELATIVE:

```c
u32 clipCount;                       /* +0x00 : N. 3 on ef038, 9 on the ef177 family              */

struct Clip {                        /* x N, stride 0x14, packed at region+0x04                   */
  /*+0x00*/ u8  flags;               /* RUNTIME STATE. 0 on disk 24/24. Start |= 3; Stop &= 0xFC  */
  /*+0x01*/ u8  frameCount;          /* == len(frameList)/4, exact on 39/39 clips                 */
  /*+0x02*/ u16 rate;                /* OPEN. 0x1000 or 0x0800 corpus-wide                        */
  /*+0x04*/ u16 paramA;              /* OPEN. non-zero on exactly ONE clip per table              */
  /*+0x06*/ u16 paramB;              /* OPEN. ditto                                               */
  /*+0x08*/ u32 timer;               /* RUNTIME STATE. 0 on disk 24/24. Start sets 0.             */
  /*+0x0c*/ u8  unk1;                /* OPEN. constant 1 on all 39 clips.  UNREAD by anything.    */
  /*+0x0d*/ u8  partIndex;           /* which creature part's page this clip lives in             */
  /*+0x0e*/ u16 scale;               /* RUNTIME STATE. 0 on disk 24/24. Start sets 0x1000.        */
  /*+0x10*/ u32 nodeOff;             /* region-relative -> Window.  IS A POINTER IN THE ENGINE.   */
};

struct Window {                      /* x N, stride 0x0c, packed immediately after the clips      */
  /*+0x00*/ u16 x;                   /* destination, VRAM HALFWORDS  (texel x = 2*x)              */
  /*+0x02*/ u16 y;                   /* destination, page rows                                    */
  /*+0x04*/ u16 w;                   /* width, VRAM HALFWORDS        (texel w = 2*w); x+w <= 64   */
  /*+0x06*/ u16 h;                   /* height, rows                                             */
  /*+0x08*/ u32 leafOff;             /* region-relative -> frame list                             */
};

/* FRAME LIST : frameCount x { u16 srcX (halfwords); u16 srcY (rows) } -- the SOURCE ORIGIN;
   the rect's SIZE is inherited from the clip's own Window. */
```

### 1.2 Field by field, tagged by what actually supports it

`E` = engine-proven (A1, cited RVA) · `B` = bytes-proven (A2, cited measurement) · `E+B` = both.

| field | reading | tag | what decides it |
|---|---|---|---|
| `region+0x00 u32` | clip count N | **E+B** | the x86 arming op indexes `region + 4 + 0x14·p`, the x64 one `region + 8 + 0x18·p` — both skip exactly one leading 4-byte field. And `4 + 20N` == the first `nodeOff` on **both** table shapes (0x40, 0xb8), with exact coverage |
| clip `+0x00 u8` | `flags`, runtime enable bits | **E+B** | `Hi_StartSummonTexAnim` `or byte,3`; `Hi_Stop` `and byte,0xfc`. Zero on disk in 24/24 records |
| clip `+0x01 u8` | **frameCount** | **B**, engine-silent | `value == len(frameList)/4` on 39/39 clips. *A1 read the same byte as a `mode ∈ {1,2,3}` enum — same values, weaker claim; A2's arithmetic identity decides it. Nothing in the engine reads it, which is consistent: nothing ticks.* |
| clip `+0x02 u16` | speed / hold, fixed-point | **OPEN** | only two values corpus-wide (0x1000, 0x0800). A2 reads 8.8 ticks (16.0/8.0); A1 reads 1/4096 (1.0/0.5). Cross-lane tiebreaker, not proof: the engine's own unity constant for this record is `0x1000` (Start stamps it into `scale`), which leans A1 |
| clip `+0x04 / +0x06` | `paramA` / `paramB`, an auto-cycle pair | **OPEN** | non-zero on exactly one clip per table, and it is precisely the self-contained blink clip no program ever starts (ef038 clip 2 = 7/33; Carbuncle clip 2 = 30/30). Neither lane can split (delay, period) from (min, max) |
| clip `+0x08 u32` | `timer`, runtime cursor | **E+B** | Start zeroes it; 0 on disk 24/24 |
| clip `+0x0c u8` | UNREAD, constant 1 | **OPEN** | 1 on all 39 clips; no engine reader; **do not guess** |
| clip `+0x0d u8` | **partIndex** | **B**, engine-silent | window↔frame exact-texel agreement **0.905–0.976** in the part this byte names, vs **0.000–0.076** in every other part of the same package, 5/5 packages |
| clip `+0x0e u16` | `scale`, runtime | **E+B** | Start writes `0x1000`; 0 on disk 24/24 |
| clip `+0x10 u32` | `nodeOff`, region-relative — **and a POINTER in the engine's struct** | **B + E** | bytes: ascending, stride exactly 12, closes in region, exact coverage. engine: it widening to 8 bytes is the *only* member change that explains BOTH x64 deltas (§1.4) |
| window `+0x00..+0x06` | destination rect; x/w in **VRAM halfwords**, y/h in rows | **B + E** | the unit test scores 0.905–0.976 for halfwords vs 0.071–0.341 for texels; `x+w ≤ 64` on 39/39 == exactly one texture page wide; A1 independently read the same 8 bytes as a page rect |
| window `+0x08 u32` | `leafOff` → frame list | **B** | `frameListEnd − frameListStart == 4·frameCount` on 39/39; exact coverage |
| frame `{u16,u16}` | source ORIGIN (halfwords, rows); size inherited from the window | **B** | **0** UV-pool entries inside every frame rect on 39/39 (a scratch strip the model never samples) vs 16–272 inside every window rect; the crops render as recognisable alternate eye/mouth art; the resting window is a **90.5–97.6 %** exact-texel duplicate of one named frame |

**Where the lanes disagreed, and who won.** Two fields only, and in both cases it is *interpretation of
identical bytes*, never a different parse: `+0x01` → A2, on a 39/39 arithmetic identity; `+0x02` →
unresolved, tagged OPEN. **The record boundaries, the three strides, the pointer graph and every
offset are agreed by both lanes.** The OPEN fields are carried verbatim by the reader and are
round-trip exact; nothing in the kit invents a meaning for them.

### 1.3 Why 116, and why 364

Both are `4 + 20·N + 12·N + 4·Σ frameCount`:

| | N | Σ frames | arithmetic | total |
|---|---|---|---|---|
| ef038 | 3 | 4 | `4 + 60 + 36 + 16` | **116** |
| ef177 / ef493 / ef494 / ef495 | 9 | 18 | `4 + 180 + 108 + 72` | **364** |

And **neither divides by `partCount * 0x18`** — the assumption baked into the old gate was wrong three
times over:

1. the region is **not a flat array**: three concatenated sub-arrays at strides 20 / 12 / 4, plus a
   4-byte header;
2. `count` counts **clips**, not parts (ef038 has 5 parts and 3 clips; the ef177 family has 3 parts and
   9 clips) — so HLE op 12's `$a1` argument is a **clip index**, and the affected part is named by
   `clip+0x0d`;
3. `0x18` is the **x64 runtime** struct size. The file record is `0x14`.

**And there are only TWO distinct tables in the whole corpus, not five.** The four 364-byte regions are
byte-identical, and ef493/494/495 additionally share a byte-identical GEOM block: this is **one
Carbuncle shipped four times** (Reflect / Haste / Shell / Vanish). A "diff the five tables for
per-effect parameters" plan returns the empty set — and that null result is itself the finding.

### 1.4 ★ THE x64/x86 STRUCT RECONCILIATION — and the arming-corruption hazard

A2 handed the engine lane an open question: the on-disk record is 20 bytes, but the old gate's
docstring cited stride `0x18`. A1 answered it with a measurement — test both indexings against all 24
records of the five armed packages, scoring *"are the three fields the arming op writes zero on disk,
as runtime state must be?"*

| indexing | records with `flags == timer == scale == 0` |
|---|---|
| **x86**: `region + 4 + 0x14·p`, fields `+0 / +8 / +0xe` | **24 / 24** |
| **x64**: `region + 8 + 0x18·p`, same field offsets | **1 / 24** (one, by luck) |

The mechanism: the engine's `TexAnim` struct is the on-disk record **with `nodeOff` as a real pointer
at `+0x10`**. On 32-bit that is 4 bytes → `sizeof = 0x14`, `alignof = 4`, so the array starts at
`region + 4`. On x64 the pointer is 8 bytes → `sizeof = 0x18`, `alignof = 8`, so the array is padded to
`region + 8` **and** the stride grows to `0x18`. Both observed deltas fall out of one member. **The
serialized form was never converted for the 64-bit recompile.**

⚠ **The hazard this leaves, recorded because it is a live trap for whoever writes the first reader or
writer:** on x64, `Hi_StartSummonTexAnim` writes *past* the record it means to arm. For ef038's two
real calls (clips 0 and 1) it zeroes `region+0x10..0x13` (clip 0's `unk1`/`partIndex`/pad) and
`region+0x28..0x2b` (clip 1's `nodeOff` low half → clip 1 loses its window), and stamps `0x1000` into
`region+0x16` (clip 0's `nodeOff` high half → `0x10000040`) and into `region+0x2e` (clip 2's `rate`,
already `0x1000`). **The arming op corrupts the table it is supposed to arm.** Inert today because
nothing reads it — and hard proof that the feature is unexercised on the build this install runs.

### 1.5 What the tables actually contain

**ef038 = Shiva** — part 1, window texel `(54,62)` 22×12, three clips: *eyes closed*, *eyes open* (the
resting art), *closed→open* — a blink, and that third clip is the one carrying the paramA/B pair.

**ef177 / ef493 / ef494 / ef495 = Carbuncle ×4** — part 2, window A texel `(66,78)` 18×14 (eye), window
B `(48,102)` 16×14 (mouth); nine clips: eye closed / open / blink / opening / closing, mouth closed /
open / opening / closing. **The opening and closing clips are exact frame-order reverses of one
another** — an independent consistency check the decode was not fitted to.

Identity is settled from a primary source rather than inferred: A3 read `Actions.csv` in the live
install — ef038 = Shiva; ef177/493/494/495 are **all four** Carbuncle rows (menu ids 68/70/69/71),
correcting the seed hypothesis that only 493–495 were Carbuncle. A2 reached the same identification
independently, through the duration census and the rendered crops (a blue eye, a red mouth).

---

## 2. THE RUNTIME-WRITE VERDICT — two independent proofs, either one sufficient

### 2.1 Layer 1 — what the DATA can express

A texel blit. Copy a `w×h` rect of 8-bit palette indices from `(srcX, srcY)` to `(x, y)` **inside the
same 128×128 page**, advancing one frame per `rate`. The three branches the old gate was hedging
between are answered at the data level, before the engine is consulted at all:

| branch | verdict | decisive evidence |
|---|---|---|
| (a) cycles the per-part **CLUT binding word** | **FALSIFIED** | no `u16` anywhere in any of the five tables equals a header TPAGE (0x93/94/95) or CLUT (0x3990–0x3a90) word; the largest value in any table is `0x1000` |
| (b) cycles **texels / UV** | **CONFIRMED, narrowed to TEXELS** | every frame rect contains **0** model UV entries (39/39) while every window rect contains 16–272; halfword-x is a DMA-rect unit, meaningless for a UV compare; and the shipped window is a ~95 % exact duplicate of one *named frame* — a spare only a blit design needs (so it can blit the resting state back) and one no UV-retarget design would ever author |
| (c) cycles **CLUT contents** in VRAM | **FALSIFIED** | rects reach row 115 of a 128-row space; the CLUT strip is 3 (Carbuncle) / 5 (Shiva) rows tall. Nothing in the table can address it |
| (d) per-part **`v_offset`** (header `+0x30` — the old gate's suspicion) | **FALSIFIED** | the v_offsets in these packages are exactly `0x80` and `0x00`; **`0x80` appears nowhere in any of the five tables** (count = 0). The header field is read once, at register time, into a stack array handed to model-init, and never re-read |

### 2.2 Layer 2 — what the ENGINE actually does

**Nothing beyond three state bytes.** The complete write set of the feature, image-wide, in *both*
builds:

```
Hi_StartSummonTexAnim :  clip.flags |= 3   (|= 1 when arg3 == 0)
                         clip.timer  = 0
                         clip.scale  = 0x1000
Hi_StopSummonTexAnim  :  clip.flags &= 0xFC
```

Established **by exhaustion**, which is the load-bearing methodology of this rung and deserves quoting
rather than summarising: (a) per-function disassembly of every `.pdata` RUNTIME_FUNCTION, 95.60 % of
`.text` — the only `SummonData+0x70` dereferences are the four Start/Stop sites; (b) linear
disassembly of all 67 `.pdata` gaps ≥ 16 B — one `+0x70` hit, inside CRT code; (c) a raw byte-scan of
the whole `.text` for `REX.W mov r64,[reg+0x70]` in **both** disp8 and disp32 encodings — no further
candidates; (d) the same scan on the **x86** build for `mov r32,[reg+0x50]` — 11 hits, only the 4
Start/Stop sites in the summon band; (e) `imul r,r,0x18` occurs **nowhere in the image**; (f) the draw
path never loads `SummonData+0x70`.

Add the lifecycle: **op 11 `Hi_StopSummonTexAnim` is never called by any of the 372 stock containers /
385 programs**, and op 12 is called from exactly **two sites in one effect** (ef038, `$a1 = 0` and
`$a1 = 1`). And per §1.4, on x64 those two calls do not even land on a record.

> **Therefore, on the PC port, a running texanim mutates nothing observable.** Branch (d) of the
> rung's own question — *"no runtime effect at all"* — is the answer.

**★ THE FALSIFIABLE COROLLARY, stated so it can be shot down in one playtest:** **Shiva's eyes never
close during her cast on the PC port**, and Carbuncle's nine authored eye/mouth clips are dormant
content the shipping PC game never plays. If anyone ever sees Shiva blink, §2.2's exhaustion missed a
path and §6.2 is where to look first.

### 2.3 Where the lanes conflicted, and how it resolves

**The one substantive conflict:** A2 concluded that a texel repaint is **UNSAFE unless the frame strip
is co-transformed**; A1 concluded **both levers are safe, unconditionally**. That is not a factual
disagreement — it is two conclusions from different premises. A2 reasons from *what the table
describes* (assume it runs); A1 from *what the binary does* (it does not run). A1's premise strictly
dominates for the current build, and its evidence is stronger: an exhaustive scan of the actually
shipped code beats an inference about authorial intent.

**The resolution this rung adopted, and shipped:** take A1's verdict as the **licence** (the refusals
lift) and A2's co-transform as the **invariant** (do it anyway). Co-transforming costs one rect list
the decoder computes for free; being wrong costs a mid-cast pop that only a human playtest can catch.
And the negative A1 proves — *"no consumer exists"* — is exactly the class of claim a future engine
change can invalidate silently: a Memoria-side reimplementation, an s58 hybrid-drive path, a 32-bit
build where the indexing *does* land. **Defence in depth at near-zero cost.** The experiment that
would separate the two empirically is §6.1, and it rides along on the cast for free.

---

## 3. THE FOUR SILENT TABLES — read exactly once, for their SIZE, never for their CONTENT

Are ef177/493/494/495's tables read at runtime at all? Both lanes agree on the answer:

1. **No program arms them.** All 372 containers walked through the sanctioned tier-R walker: op 11 = 0
   and op 12 = 0 for all four; **ef038 is the only caller of either op corpus-wide.**
2. **No engine path arms them either** — no auto-start in the model loader, no other HLE op that
   reaches the table, no id-5-handler traversal.
3. **No ticker exists to run them even if armed** (§2.2).
4. **But their EXISTENCE is read.** The loader compares `firstBlock` against `motionOffsets[0]` and
   uses the result to choose `Hi_RegisterSummonModel`'s second argument:

```
mov edx,[rsi+0x40]     ; the texanim pointer
mov rdx, r15           ; r15 = &g_vramPageTable, 8 B per part
cmp rbx, rax           ; motion[0]  vs  firstBlock
cmove rdx, r12         ; r12 == 0  ->  pass NULL when the region is EMPTY
call …                 ; Hi_RegisterSummonModel(header, rdx)
```

With a non-NULL second argument, `Hi_RegisterSummonModel`'s per-part loop copies four `u16` per part
into `summonRecord+0x20+8i` and sets `summonRecord+0x51 = 1`. That table is filled by the id-4
**texture-upload** loop (`rsi += 0x4000` per 64×128 page) — it is the **per-part VRAM placement**.
Semantically coherent: you only need to know *where in VRAM each part landed* if you intend to re-blit
frames into it. **No reader of `summonRecord+0x20..0x4f` could be located** — so even this one
downstream effect is, so far, write-only (flagged OPEN, §6.4).

So the four Carbuncle tables are **dormant authored content**, and the single runtime fact about them
is *a boolean on their emptiness*. Which produces the rung's one new hard rule.

### ★ THE REGION INVARIANT (R1) — the rung's one new HARD RULE

> **Never resize, relocate or zero the `[firstBlock, min(motionOffsets))` region, and never edit
> `firstBlock`.** `firstBlock == motionOffsets[0]` is a **live engine predicate** that changes
> `Hi_RegisterSummonModel`'s arguments, and therefore what `summonRecord+0x20..0x51` holds.

It applies to all five armed packages and is **independent of any gate decision** — it would be worth
pinning even if the lift had been deferred. Recolour and repaint never need to violate it (both are
in-place splices), so honouring it costs nothing. **It is enforced at the call site, not described in
a docstring**: `reskin.assert_region_invariant(stock, patched, where)` runs at the end of *both*
`reskin.build` and `repaint.build`, and states separate comparisons ORDERED so each fires for its own
bug — `firstBlock` first, then `min(motionOffsets)`, then the derived span, then the content (the span
derives from the header fields, so span-first would swallow them into one generic message; V1 F6).
`w7_gates.G4` proves the *function* non-vacuous by tampering with a byte and requiring the check to
catch it; the *call site* was proven live separately, by handing `repaint.build` a composition base
with one region byte flipped (V1 F7). One honest caveat belongs on the record: measured over all 24
creature packages, no texture-page span and no CLUT span overlaps any texanim region — the invariant
is **geometrically unreachable by either shipped lane today**, and earns its keep against a corrupted
composition base or a future lane, not against the current splices.

---

## 4. THE LAWFUL LIFT

### 4.1 What unlocked

| # | lane × class | before W7 | after W7 | basis | new obligation |
|---|---|---|---|---|---|
| **L1** | `summon-reskin` **creature CLUT recolour** × the 5 armed | **REFUSED outright, no key lifted it** | **ALLOWED, no key** | `E+B` — the table cannot express a CLUT change, the blit moves palette **indices** so a recolour survives even if it ran, and nothing runs it | none. The refusal and its test pins are inverted |
| **L2** | `summon-reskin` **scenery recolour** × the 5 armed | allowed only with `acknowledge_texanim = true` | **ALLOWED, no key** (when the table DECODES — every stock container) | `B` — every clip names a **creature** part and every rect is page-local (`x+w ≤ 64`, 39/39); the table cannot reach a scenery page | none. `acknowledge_texanim` becomes a **deprecated no-op where the table decodes** — accepted and ignored for one release so W5-era specs keep building; the scaffold stops emitting it. On an armed-undecodable region the key keeps its ORIGINAL meaning and is still required (R2b) |
| **L3** | `summon-repaint` **creature texel repaint, whole-page** × the 5 armed | **REFUSED outright, no key existed** | **ALLOWED, no key** | `E` for the licence, `B` for the invariant — a dense whole-page repaint reaches the protected set in practice (the gate's predicate is REACH: ≥1 changed texel per rect, so a sparse page-wide remap can honestly miss a rect and refuse; V1 F3) | the gate verifies reach; no author-facing key |
| **L4** | `summon-repaint` **creature texel repaint, LOCALISED** (a sub-page splice intersecting a live window or a frame rect) | REFUSED outright | **ALLOWED once the protected rect set is co-transformed**; otherwise refused with a *specific, actionable* message naming the exact rects | `B` (the rect set is measured); `E` says even this is moot on the current build | the tool computes the protected set and refuses **naming the clip and the sibling rects left stock**. `acknowledge_texanim_frames = true` is the escape hatch for an author who *wants* an asymmetric strip |
| **L5** | either lane × the **19 unarmed** creature packages | allowed | unchanged | — | — |
| **L6** | the authoring readouts (`--scaffold`, `plan`, both lanes' derivation reports, and `export-art`'s report + manifest + emitted texel scaffold — the paint-time surface, added on V1 F4) | reported `TEXANIM ARMED (N bytes)` — an opaque size | **report the DECODED table**: clip count, per-clip part / frames / rect, and the protected rect set | `E+B` | none — pure disclosure. (Two surfaces the plan over-claimed and the record corrects: `summon-rescore read` is the CAMERA lane and never was a texanim surface; the study's `w_survey` keeps its one-line armed-size census — its row struct is blob-free at format time and its self-check is a KEPT-UNCHANGED pin) |

**Why L6 mattered more than it looks.** An opaque byte count is exactly what made the old refusal
*unanswerable*: an author could not tell what the gate was afraid of, so there was nothing to act on.

### 4.2 What STAYS refused

| # | refusal | why it stays |
|---|---|---|
| **R1** | any edit to `firstBlock`, or any resize / relocation / zeroing of the region | `E` — the loader's `cmove` is a live predicate. **The new rule, §3** |
| **R2** | **authoring or editing the texanim table itself** (adding clips, moving windows, retiming) | `E` — there is no consumer, so no edit could be *verified*; and on x64 the arming op already corrupts the record it targets, so any authored table is pre-scrambled the moment ef038 casts. **W7 ships a READER, not a writer.** A writer needs its own rung and a live probe |
| **R2b** | an armed region the reader **cannot DECODE** | the whole lift is conditional on a **successful parse**, never on the absence of an exception — so an unknown future shape degrades to the pre-W7 **posture, per scope** (V1 F1): a creature target refuses outright with no key; a scenery target is back to needing `acknowledge_texanim` in its original meaning (the deprecation applies only where the measurement that earned it actually ran). The refusal messages state the honest present tense — the format IS read, THIS region does not match it — with the parse error appended (V1 F5) |
| **R3** | the dual-depth CLUT cell refusal | unrelated to texanim; untouched |
| **R4** | the stock-sha drift guard / `expect_sha256` / `allow_unguarded` | unrelated; untouched |
| **R5** | treating header `+0x3c` / `+0x40` as data | `E` — both are **loader-computed and zero on disk**. An offline reader that reads them as data concludes *"absent"*, which is wrong on all five armed packages. Documented in `container.py`, never consumed |

### 4.3 THE PROTECTED RECT SET (what L4 co-transforms)

Texel space, per package, in the part the clip names. The page file offset for part *p* is
`mp.tex_file_offset + p*0x4000`; one texel = one byte, one row = 128 bytes. Machine-readable at
`…\texanim-w7\bytes\clips.json`; **re-measured every run** by `w7_gates.G1` rather than trusted.

**ef038 (Shiva), part 1** — `(54,62,22,12)` live window (eye) · `(56,0,22,12)` frame: eye OPEN (the
resting spare) · `(78,0,22,12)` frame: eye CLOSED.

**ef177 / ef493 / ef494 / ef495 (Carbuncle), part 2** — `(66,78,18,14)` window A (eye) ·
`(20,114,18,14)` eye OPEN · `(2,114,18,14)` eye HALF · `(34,64,18,14)` eye CLOSED · `(48,102,16,14)`
window B (mouth) · `(24,51,16,14)` and `(24,50,16,14)` mouth CLOSED (two variants one row apart —
**they overlap, and `(34,64,18,14)` eye CLOSED overlaps them too**: the kit's `overlap_groups`
measures a transitive THREE-rect group, so the Carbuncle set is 7 co-transform groups, not 8
pairs-plus-singletons; V1 F8/B1) · `(18,100,16,14)` mouth HALF · `(2,100,16,14)` mouth OPEN.

⚠ **Co-transform the UNION of an overlapping group, never the rects independently** — applying a
per-texel transform to two overlapping rects in turn applies it **twice** to the shared texels. The
reader ships `overlap_groups()` for exactly this, and it returns **groups, not bounding boxes**: the
box of the Carbuncle mouth group would sweep in 500+ texels nobody asked to repaint.

### 4.4 The docstrings that became false the moment this landed — all fixed

`reskin.TexAnim` ("the internal format is UNREAD … not settled" — all three clauses now settled) ·
`reskin._gate_texanim` ("stride 0x18 **BY PART**" — wrong twice: the index is **by clip**, and `0x18`
is the **x64 runtime** stride) · the reskin refusal prose and scaffold banner · `repaint._gate_texanim`
("both surviving readings hurt a repaint" — one reading survives, and it only hurts a *localised*
repaint) · `container.ModelPackage` (`+0x3c` / `+0x40` documented as loader-computed, zero on disk) ·
`W6-TEXEL.md` §1.9 (superseded here rather than rewritten there).

---

## 5. WHAT SHIPPED

### 5.1 The decoder seam

**`ff9mapkit/ff9mapkit/summons/texanim.py`** — a pure reader. It does **not** disturb
`reskin.texanim_region()`: that function is the measurement the loader predicate mirrors, and it is
pinned by corpus tests in three files. The new module layers on top:

* `Rect` / `Frame` / `Clip` / `TexAnimTable` — the typed table, rects already converted to **texel**
  space (the file's halfwords doubled) because that is the only form a repaint can act on;
* `parse_region` / `parse` / `read` — `read` is the form a GATE consumes: it turns the failure into a
  value, and its `ReadResult` separates **not armed** / **parsed** / **unparseable**, which every
  consumer must handle;
* `encode` — **exists for the round-trip test and nothing else** (R2), reachable from no CLI verb;
* `protected_rects` / `overlap_groups` / `protected_groups` / `page_file_offset` — the co-transform
  units;
* `describe` — the L6 readout lines, which report an undecodable table as ARMED-and-unread rather than
  failing (a readout is what an author reads *before* a gate fires, so it must survive exactly the
  containers the gate is about to refuse);
* `REGION_RULE` — the hard rule as a string, quoted verbatim by every message and gate, so the rule and
  its enforcement can never drift apart.

**The decoder refuses rather than guesses.** It rejects any offset that leaves the region, any
`x+w > 64` halfwords, any `partIndex >= partCount`, any zero clip/frame count, and — the property that
proved the format — **any table whose three sub-arrays plus the 4-byte count do not tile the region
exactly**: zero slack, zero double-cover. Non-zero runtime state (`flags` / `timer` / `scale`) is
surfaced as a **warning**, never silently normalised — it is the cheapest possible corruption detector
for a container someone has already patched.

### 5.2 The consumers

| call site | what it does now |
|---|---|
| `reskin._gate_texanim` | a **disclosure** plus one surviving refusal (armed + unparseable). Returns the note lines `Build.notes` carries and `describe` prints |
| `reskin.assert_region_invariant` | **new** — R1, at the end of `build` |
| `reskin.scaffold` | stops emitting `acknowledge_texanim`; blocks a creature row only when the table does **not** decode; prints the decoded table |
| `repaint._gate_texanim` (pass 1) | returns a `ReadResult`; refuses only armed-and-unparseable, before any art is read |
| `repaint._gate_texanim_frames` (pass 2) | **new** — the co-transform obligation, per target, per clip family: all-untouched → build · all-covered → build · asymmetric → refuse naming the clip and the exact rects left stock, unless `acknowledge_texanim_frames = true` |
| both `derivation_lines` | print `texanim.describe` instead of a byte count (L6) |

`acknowledge_texanim_frames` is a **literal boolean** — a truthy string refuses rather than arms, the
same law every other acknowledgement in this tier obeys, and it is exercised through the texel lane's
own `_ack_bool` rather than assumed to inherit it.

### 5.3 The gates, and the pins that MOVED

**New — `w7_gates.py`, 5/5:**

| gate | claim |
|---|---|
| **G1 THE ROUND TRIP** | `encode(parse(region)) == region` on every armed region in the corpus; `parse` never raises on any of the 372 and returns `None` on all 19 unarmed creature packages; the census (armed set, clip counts, animated part, `4+20N+12N+4F` arithmetic, **2** distinct tables) and the §4.3 rect sets **re-measured**, never compared against a constant |
| **G2 THE LIFT MATRIX** | §4.1 executed on the five real packages — L1/L2/L3 build with no key, L4 refuses naming the sibling and builds with the hatch, L5's 19 unarmed packages carry an empty protected set, L6's three readouts all print the table; plus **R2b** (a poisoned region still refuses with the pre-W7 message) and **R2** (no writer verb is reachable) |
| **G3 THE CO-TRANSFORM** | on **ef038**: repainting the live eye window alone REFUSES, naming clip 0 and the sibling frame left stock; repainting the window **and both frames** BUILDS, with every protected rect carrying the same transform **measured texel by texel** (264/264 each) and the region byte-identical |
| **G4 THE REGION INVARIANT** | after a real **reskin** AND a real **repaint** build on all five armed packages: `firstBlock`, `min(motionOffsets)`, the measured span and every region byte unchanged — **and the check proven non-vacuous** by tampering with one byte and requiring it to be caught. (Read with §3's caveat: G4's tamper proves the FUNCTION; the call site was proven live against a corrupted composition base, and the invariant is geometrically unreachable by the shipped splices themselves — it guards the future, not the present; V1 F7) |
| **G5 PROVENANCE** | a byte-literal scan of every committable W7 file against all 372 corpus containers (0 literals, 0 hits); the four SE-derived dossiers all outside the checkout |

**Pins that moved, in lockstep** (a pin that moves alone is a corpus sweep that fails on the next run):

| where | was | is |
|---|---|---|
| `test_summon_reskin.py` creature refusal | refuses outright | **inverted** — builds, region byte-identical, decode disclosed; a new sibling pins the armed-**unparseable** fallback |
| `test_summon_reskin.py` scenery refusal | needs `acknowledge_texanim` | **inverted** — builds with no key on both shapes; the deprecated key parses and is reported |
| `test_summon_reskin.py` scaffold | asserts `acknowledge_texanim = false` is emitted | asserts it is **not** emitted, and that a decodable table blocks no row |
| `test_summon_reskin.py` texanim-region measurement | — | **KEPT UNCHANGED** — it is the loader predicate and must not drift |
| `test_summon_repaint.py` blanket refusal | one test | **split into the L3/L4 matrix** — 6 tests |
| `test_reskin.py` (study) `:1153-1190`, `:1379-1385`, `:1459-1469` | the study-side duplicates + the corpus-backed parametrised refusal | moved in lockstep; the parametrised one is now **THE FIVE LIFTS** |
| `test_reskin.py` (study) the W5 corpus sweep asserting the exact five-name armed set | — | **KEPT UNCHANGED** — ground truth for every other constant |
| `w5_gates.py` G3 | `THE FIVE TEXANIM REFUSALS` | **G3′ `THE FIVE TEXANIM LIFTS`** — each of the five: a creature recolour BUILDS through the tool's own scaffold, and the region is byte-identical afterwards |
| `w6_gates.py` G4 (d) | the texanim refusal row | **the L3/L4 matrix** on all five, plus the armed-unparseable fallback |
| `w4_gates.py` X7 · `w_survey.self_check` | census gates | **KEPT UNCHANGED** |

---

## 6. THE CAST PROTOCOL — one deploy, two verdicts

**Subject: ef038 = Shiva.** She is the *only* effect that arms op 12, i.e. the maximal-risk member of
the class — proving lever 1 there proves it for all five. She is also the most legible subject: she is
saturated blue, so a magenta/violet recolour reads instantly, which is exactly the shape of the W5
Phoenix scenery proof already cast-proven on this bench.

**The spec:** one `summon-reskin` on ef038, creature scope, whole-creature CLUT recolour to
magenta/violet (the W5 Phoenix `combined-v2` recipe, retargeted), shipped **with the lever-2 marker
below in the same build**. One deploy, two verdicts. The spec is
[`shiva_reskin.toml`](shiva_reskin.toml) and the marker's art is generated by
[`shiva_marker.py`](shiva_marker.py) (the art itself is Square-Enix content and stays in SCRATCH, so
what ships is the **generator** — the same posture W6a took with the emblem); the bench ability row
lives with the rung-8 bench.

### ★ VERDICT 1 — THE ONE-FRAME VERDICT (this is the whole design constraint)

> **Cast Shiva. Capture ONE frame with the creature on screen. Shiva is MAGENTA ⇒ the lift is
> correct.**

Why one frame suffices: branches (a) and (c) — the two the gate was hedging against — would have the
running texanim rebind or rewrite the palette **during** the cast, so the creature would be showing
stock blue in the frames where the animation is live. Magenta at any point where the creature is
on-screen and the animation would be running falsifies both. Nothing about timing, ordering or feel
enters the judgement, and `tools/game_snap.ps1` can capture it — so the agent can read the verdict
directly instead of relying on a description.

### VERDICT 2 — THE DISCRIMINATOR for §2.3 (needs video, not a frame)

In the same build, paint a screaming marker — a single flat index, unmistakable under the recoloured
palette — into the frame-strip rect `(78,0,22,12)` (the spare *eye CLOSED* art) and **leave the live
window `(54,62,22,12)` alone**. Then:

* the eye window **never** changes across the whole cast ⇒ consistent with A1: nothing blits, and
  L4's co-transform stays **prudential**;
* the eye window **ever** shows the marker ⇒ the blitter runs after all, the exhaustion missed a path
  (almost certainly §6.2), and **L4's co-transform becomes MANDATORY**. L1 is unaffected either way —
  which is the whole point of shipping both in one cast.

Ask for a short capture of the full cast for verdict 2 (`feedback-video-for-visual-bugs`); verdict 1 is
the frame. Note that this build deliberately trips L4's own refusal and must state
`acknowledge_texanim_frames = true` — the marker **is** the asymmetric strip the hatch exists for.

**Bench change — RELAUNCH class.** The ability-id allocator walks specs in TOML order, so the new row
must be **appended last** to the bench's existing pool (inserting earlier renumbers already-deployed
ids, which is a live-state break). It follows the `Stock Phoenix` / `Stock Madeen` shape verbatim:
`from = "Bahamut"` (a valid AllEnemy magic row) · `targets = "AllEnemy"` with **both vfx cells equal**
(forces the FULL cast structurally, never the short roll) · `type = 0` (clears the donor's type-4
MP-quadrupling bit — playtest-caught on this very bench) · cheap `power`/`mp`, because the row exists
to be cast repeatedly. **This is an `Actions.csv` / BattlePatch change ⇒ RELAUNCH, not a `~` reload.**
The reskin itself hot-reloads; the row does not.

---

## 7. STILL OPEN — with the cheapest experiment for each

**7.1 — Does anything blit, in fact?** *(the §2.3 discriminator; decides whether L4's co-transform is
mandatory or prudential)* **Cheapest:** the frame-strip marker in §6 — zero extra deploys, zero extra
tooling, one capture. **Cheaper still if a probe is wanted first:** hash the 116 bytes at `region` in
the live process before and after a Shiva cast. On x64 the *arming alone* will change 12 bytes at the
offsets §1.4 predicts; if those are the **only** changed bytes there is no ticker — and it doubles as a
live confirmation of the x64 misalignment.

**7.2 — The MIPS escape hatch.** The plugin interprets each effect's own id-3 MIPS program with full
access to PSX RAM, so in principle a program could implement the missing service itself. Against it:
ef038 reaches **no** VRAM-transfer op (0/1/166 StoreImage/LoadImage/MoveImage) at all, and a MIPS-side
service would make the native op-12 arming pointless. **Cheapest (static, no game):** grep ef038's two
id-3 images for loads/stores based on the model pointer or on `header+firstBlock`. Pure bytes, no
probe — **and it should be done before the cast**, because a hit changes the cast's expected outcome.

**7.3 — `rate` (`clip+0x02`): 8.8 hold-ticks or 1/4096 speed?** Cosmetic today; matters the moment a
writer exists (R2). **Cheapest: none worth running now** — deferred with the writer. If ever needed: a
32-bit build (where the indexing lands) plus a stopwatch on the blink cycle.

**7.4 — Who reads `summonRecord+0x20..0x4f`?** The per-part VRAM page table copied **only** when the
region is non-empty (§3). No reader located; almost certainly the blit destination and therefore
equally dead, but that is not proven — and it is the mechanism by which R1 could bite. **Cheapest:** a
byte-scan for `imul r,r,0x58` sites and a read of each resulting `+0x20..+0x4f` access — **static
first**; a data breakpoint during a Shiva cast only if that comes back empty.

**7.5 — Does the s58 hybrid drive or any managed path see the native texture at all?** For the W lane
this is **moot** — both levers edit the *file*, which the native loader uploads, so a static edit is
upstream of both paths. It matters only for a future texanim writer or a managed reimplementation.
**Deferred**; §6's cast already exercises the real render path for a stock summon.

**7.6 — `clip+0x0c` (constant 1), and the `paramA`/`paramB` pair.** Unread, and unresolvable from five
samples of two distinct tables. **Cheapest: none — do not guess.** The reader carries them through
verbatim and the round-trip gate makes that safe. They become answerable only alongside a writer and a
build where the animation runs.

---

## 8. PROVENANCE

Every claim in this record traces to one of the three lane dossiers: **A1** to `fn@rva` in read-only
static analysis of the user's own installed `FF9SpecialEffectPlugin.dll` (x64 and x86); **A2** to
measurements over the pre-existing read-only stock dumps at `C:\gd\SCRATCH\summon-format\ef*.bytes`;
**A3** to `file:line` in this repo plus `Actions.csv` in the live install (read-only). **No game file
was written, no DLL modified, nothing deployed.** All SE-derived bytes remain under
`C:\gd\SCRATCH\summon-format\texanim-w7\`.

What this rung **commits** is a reader, its tests, a gate runner and this record: structural offsets,
strides, field names, counts and rect coordinates — never a stock byte. `w7_gates.G5` is the gate that
says so, by scanning every committable W7 file's byte literals against all 372 corpus containers
(**0 literals, 0 hits**) and confirming the four dossiers sit outside the checkout.
