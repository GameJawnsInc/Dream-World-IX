# W6b-1 — THE SCENERY TEXEL LANE (rung W6b-1: page-cells, three depths, four remedies)

> **Status: BUILT, offline-proven, CAST PENDING.** The lane ships; the vehicle (ef211 `(704,256)`,
> the Phoenix fire field) is chosen and its every parameter derived; no byte has reached a screen.
> The rung does not close until the cast is judged. Ladder → §5.
>
> **Record under extension:** `W6-TEXEL.md` §1.4 / §1.5 / §1.10 / §2 / §10 (W6a's laws, corrected
> here where this rung's measurements sharpen them), `W7-TEXANIM.md` §4.3, `PLAN.md`.
> **Recon this document distils** — all outside the checkout, all Square-Enix-derived, never in the
> repo: `C:\gd\SCRATCH\summon-format\texel-w6b\SYNTHESIS.md` (the decision document; its section
> numbers are cited below as *SYN §N*) · `census\A1-SCENERY-SURFACE-CENSUS.md` +
> `census\pages.json` (2,665 page-cell records with hazard flags) + `census\classes.json` ·
> `formats\A2-FORMATS.md` + the working prototypes `w6b_fmt.py` / `p1_indexed.py` /
> `p3_nibble_order.py` / `p5_uspill.json` / `p7_demo.py` / `p8_palette_view.py` ·
> `prior\A3-PRIOR.md`.
>
> **Every number below is re-measured by `w6b_gates.py` on each run.** Where a number here disagrees
> with a dossier, the disagreement is stated with both predicates rather than reconciled away — §7
> collects them.

---

## 0. THE FOUR THINGS THIS RUNG DECIDED

1. **The lane is not codec-limited; it is ATTRIBUTION-limited.** Both indexed depths and the direct
   depth round-trip byte-identically over the *entire* corpus. The wall is that **2,385 of 2,572
   scenery cells (92.7 %) have no `so` reader**, so their bit depth is not a fact the container
   states — and the coherence probe built to guess it was **falsified at 54.5 % on a 3-way choice**.
   W6b-1 ships a codec that never fails and a gate that refuses 93 % of the surface by name, and that
   asymmetry is the honest shape of the rung.
2. **The per-VRAM-cell page map converts refusals into lawful edits — it is not a tidy-up.**
   `scenery_pages` is keyed `(tag, x)` and therefore cannot name the lower half of an `h = 256` rect
   at all. On ef211 column 576 the TOP cell is a two-palette same-bytes hazard and the BOTTOM one is
   clean single-reader single-writer 4bpp, and the rect key can only reach the hazardous half.
   **1,179 cells corpus-wide had no name; 20 of them are otherwise lawful.**
3. **The program-VRAM refusal narrows BY DIRECTION, and that is what makes a cast possible.**
   `StoreImage` is VRAM → main RAM, a **READ**, and a read cannot clobber a static repaint.
   **113 cells across 12 containers move from REFUSE to DISCLOSE**, and ef211's fire field — the one
   cell in the corpus whose upload path is already cast-proven live — becomes reachable at all.
4. **The cast vehicle is ef211 `(704,256)` and it needs no new bench row, no relaunch and no
   composition.** §5.

---

# 1. THE PAGE-CELL CLASSIFICATION

## 1.1 The unit

The addressable unit is the **VRAM page-cell**: 64 halfwords × 128 lines = `0x4000` bytes, the quantum
the engine uploads. It is *not* `PageRect`: 1,214 of 1,317 corpus page rects are `h = 256` and cover
**two stacked cells**. `reskin.page_cells()` splits them, keyed `(writer tag, x, y)` — the writer is
in the key **by construction**, so the corpus's 34 multi-writer cells appear as the several records
they are instead of one silently replacing another.

| | measured | note |
|---|---:|---|
| page-cells corpus-wide | **2,665** | 2,572 scenery + 93 id-4 creature |
| cell-WRITER records | **2,648** | a co-transform cell is several records |
| `w == 64` on every record | **2,648 / 2,648** | so the `w != 64` refusal is a TRIPWIRE, not a code path |
| cells the `(tag, x)` rect key can never name | **1,179** | what the per-cell map unlocks |
| duplicate `(tag, x, y)` keys | **0** | asserted, not assumed |

A1 and A2 derived 2,665 independently, on independent rasterisers, and agree to the cell; A1
additionally re-derived all seven of `W6-TEXEL.md` §1.4's published shared-halfword counts exactly.
**The instrument is calibrated.**

## 1.2 The classes, with corpus counts

Non-creature cells only (2,572). Overlapping — this is a per-hazard rollup, not a partition.

| # | class | cells | **remedy or refusal** |
|---:|---|---:|---|
| **A0** | id-4 CREATURE page | **93** | **SHIPPED** by W6a (93/93 byte-identical, cast-proven) |
| **B1a** | LAWFUL, page-scope-safe | **50** | **SHIP** — 46 program-clean + 4 `read-storeimage` disclosure |
| **B1b** | LAWFUL, but the reader SPILLS out | **6** | **SHIP behind NAME-EVERY-COLUMN** |
| **B2** | otherwise-lawful, LOWER HALF only | **20** | **the per-cell map makes these B1** |
| **C** | **DEPTH-UNKNOWN** — no `so` reader | **2,385** | **REFUSE BY NAME.** The guessing probe is FALSIFIED (54.5 %) |
| **D** | CO-TRANSFORM — ≥2 writers of one cell | **34** | **16 remediable** / 8 refuse (two depths) / 10 refuse (unread) |
| **E1** | SAME-BYTES-TWO-**DEPTHS** | **17** | **REFUSE, separately and EARLIER than the palette logic** |
| **E2** | SAME-BYTES-TWO-**PALETTES** | **42** | **DISPLAY-PALETTE RULE** (§2.4) — not a refusal |
| **E3** | SHARED-READ (any multi-binding) | **93** | **DISCLOSURE**, naming the other models |
| **F1** | SPILL-IN — a foreign model reads here | **36** | **REFUSE page scope**; the edit unit is the MODEL |
| **F2** | spill-touched, UV-exact | **70** | **NAME-EVERY-COLUMN gate** |
| **G1** | PROGRAM WRITE | **175** | **REFUSE** — 15 containers |
| **G2** | program write, DESTINATION RESOLVED | **3** | **HARD REFUSE by cell** (`ef001/ef142/ef144 . x704_y256`) |
| **G3** | `StoreImage` = a READ | **113** | **DISCLOSE, do not refuse** (12 containers) |
| **H** | TEXANIM ARMED | **12** | unchanged from W6a/W7 |

### ★ THE ONE CORRECTION TO A1's HEADLINE — LAWFUL ≠ PAGE-SCOPE-SAFE

A1 reports **56** lawful cells. That predicate admits **6 cells whose reader spills out of them**, and
those are not page-scope-safe: the median spilling picture is 224 texels against a 128-texel page, and
**0 of 58** spills are ≤ 2 %. There is no marginal spill case to wave through.

> **LAWFUL 56 = 50 PAGE-SCOPE-SAFE + 6 MODEL-SCOPE.** The edit permission is the 50; the 6 are
> admitted only through the name-every-column gate. **Plus the 20 class-B2 lower halves the per-cell
> map unlocks = 76 addressable-and-lawful cells** — and *that* difference is the map's whole return.

## 1.3 CO-TRANSFORM — A1's 34 reconciled with A2's 16

A1 measures the CLASS (34 cells, 5 containers, 156 writer pairs, **0 byte-identical**); A2 classifies
the same 34 by whether an edit is even *expressible*. Re-derived here by counting distinct reader
depths per cell: **16 single-depth-read / 8 multi-depth / 10 unread** — **A2 is right and A1's remedy
table overstates by 18.**

| ef | shared cells | co-transformable | two-depth (refuse) | unread (refuse) |
|---|---:|---:|---:|---:|
| ef225 | 4 | **4** | 0 | 0 |
| ef227 | 6 | **2** | 2 | 2 |
| ef251 | 6 | **0** | 0 | **6** |
| ef381 | 16 | **8** | 5 | 3 |
| ef447 | 2 | **1** | 1 | 0 |
| **total** | **34** | **16** | **8** | **10** |

* **ef251 (Madeen) has ZERO addressable shared cells** — 6 of its 16 page-cells are multi-writer and
  all 6 are unread. A Madeen shared-column repaint is out of reach at any depth, for a reason no
  remedy touches. (`w6b_gates` G4 measures the 6-of-16 and the 6-of-6.)
* **ef227's two remediable cells are `x832 y256/384`** — writers `s1` (an id-0 page rect) and
  `id9.s0` (an id-9 ALTERNATE block), differing in 99.95 % and 92.94 % of their bytes. `(832,256)` is
  *also* class E2, so its export owes an alternate view on top of the co-transform pair; `(832,384)`
  carries **no other hazard at all**, which is why the gate uses it as the remedy's fixture — a
  refusal there can only be the co-transform one.

**The remedy shape:** name every writer, art for each, `acknowledge_cotransform` a **literal boolean**,
mirroring the CLUT lane's `reskin._gate_cells`. **There is deliberately no "same art for all writers"
shorthand** — the closest pair in the corpus (ef381 x512 y384, `s2` vs `s4`) still differs in 1.03 % =
168 bytes, so a broadcast key would be the tool asserting an interchangeability the corpus denies on
156 of 156 pairs. Two rows MAY name the same file; that is an authored decision to unify the flicker,
and it is **disclosed** rather than silently accepted.

## 1.4 SAME-BYTES-TWO-BINDINGS — the gate is the halfword set, not the page

A1's binding-pair sweep is the sharpest new measurement in the rung:

```
1,083 overlapping binding pairs in 36 effects
   mixed-depth  79  (6 effects)  <- 65 share a tpage PAGE; 14 do NOT (they overlap by SPILL)
   same-depth   1,004 (35 effects)  ... different palette 390 (11) / same palette 614 (33)
```

1. **`W6-TEXEL.md` §1.4's "65 mixed-depth pairs" is the SAME-PAGE SUBSET.** 14 further mixed-depth
   overlaps cross columns by spill (ef381 ×8, ef447 ×6). **A page-keyed dual-depth test misses all 14;
   a halfword-set test does not** — which is the strongest evidence yet that §1.4 named the law
   correctly: SAME-BYTES-TWO-BINDINGS, never "dual-depth".
2. **Same-depth-different-palette is 390 pairs in 11 effects**, not the single ef211 curiosity §1.4
   used to illustrate it. ef211 col 640 is the *smallest* instance of the class.
3. **614 same-depth same-palette overlaps in 33 effects** are a hazard the record did not name at
   all: one edit changes two models with no depth *or* palette signal. That is class E3 — a
   **disclosure**, 93 cells over 38 effects.

Per-effect, the 17 SAME-BYTES-TWO-DEPTHS cells are ef203 ×1, ef227 ×3, ef381 ×5, ef424 ×1, ef447 ×4,
ef498 ×3 (three are triple-depth). **They refuse EARLIER than the palette logic and with their own
message**, because a 4bpp view and an 8bpp view of one cell are two different *index arrays* over one
byte block and no PNG's edit is coherent under both.

## 1.5 U-SPILL — where the two recon lanes disagreed, and the settlement

**The disagreement:** A1 reports 36 spill-in and 49 spill-out cells (union **83**); A2 reports **70**
spill-touched. Settled by intersecting the probes' own cell sets:

```
A2-style UV-exact set (58 spillers, columns x v-range)      : 78 cells
   ... that are WRITER cells                                : 70   <- A2's number, exactly
   ... with NO writer at all (nothing uploads them)         :  8   <- all ef390
A2 \ A1 : 0        A1 \ A2 : 13   (all y=384 lower halves)
```

**A2 ⊂ A1, with ZERO contradictions.** The 13-cell delta is entirely lower-half cells the spilling
model's own `v` range never reaches.

> **RULING:** the gate uses **A2's UV-exact 70**. Naming a cell the model does not read would be a
> FALSE obligation, and an obligation an author cannot discharge honestly is worse than no gate.

⚠ **The rect-conservative superset is CONSTRUCTION-DEPENDENT and this rung does not pin it.** A1's
probe records 83; `w6b_gates`' own rect expansion (every stacked cell of every writer rect of a
spill-touched cell) measures **94**. Both are supersets of the same 70 and neither is a fact about
what a model *reads*, which is why the pinned property is the SUBSET relation (0 contradictions) and
not a number. → §7.

The rest of the spill census is agreed and load-bearing:

| fact | value |
|---|---|
| spilling bindings | **58** — 41 at 8bpp, **17 at 15bpp**, **0 at 4bpp** |
| 4bpp cannot spill | **STRUCTURAL**: `u ≤ 255` at 4 texels/halfword ⇒ column offset ≤ 63 |
| 8bpp spill distance | exactly one column on 41/41 — never further |
| 15bpp spill distance | up to **3 columns** (ef390 ×3) — one halfword is one texel |
| picture wider than one page | **58 / 58**; median 224 texels vs a 128-texel page |
| spill ≤ 2 % of covered halfwords | **0 / 58** — no marginal case exists |
| spills into a column with a DIFFERENT writer set | **6** (ef227 ×1, ef381 ×3, ef447 ×2) |
| spills into a column NO writer uploads | **10 bindings / 8 cells** (all ef390, all 15bpp) |

**The 15bpp spill population is NEW and `W6-TEXEL.md` §1.5 could not have seen it**: `reskin.attribution`
dropped every 15bpp binder, so the recorded "41 of 316" was measured over a population that excludes 24
bindings by construction. **The record is INCOMPLETE, not wrong** — the 41 is still the 8bpp answer.

## 1.6 ★ PROGRAM-VRAM — the list, corrected in four ways

A1 re-derived the whole list from the bytes with tier-r's const-folding `ImageWalker` and reproduced
`W6-TEXEL.md` §1.10's enumeration **exactly** (9 seq-op-`0x07` + 2 `LoadImage` + 9 `StoreImage` +
5 `MoveImage` + 2 texanim). Four corrections:

### ★ 1. THE DIRECTION LAW

> `LoadImage(RECT*, u_long*)` is main RAM → VRAM: a **WRITE**.
> `MoveImage(RECT*, x, y)` is VRAM → VRAM: a **WRITE**.
> **`StoreImage(RECT*, u_long*)` is VRAM → main RAM: a READ — and a read cannot clobber a repaint.**

Corroborated by the DLL's own HLE stub arities, and by the study's own W5 discriminator
(`PLAN.md`: *"ef211's program does NO VRAM re-upload (one StoreImage = a read; 0 LoadImage/MoveImage)"*).
**113 cells over 12 containers move from refuse to DISCLOSE.** A3 had treated ef211 as a
whole-container refusal; that was the pre-direction-law reading, and it is the correction that makes
this rung's cast exist at all.

### ★ 2. ef435 is a FALSE POSITIVE — REFUTED, and it matters beyond this lane

Its `@0x2dd8` is a **switch dispatch through the image's own pointer table** (`lw $v0, 0($v0)` with no
`base = *(sysStruct + 0x10)` sentinel chain; the image's words `0x00..0x38` are 15 PSX addresses inside
itself). The walker read offset 0 as HLE op 0. **ef435 comes OFF the list** — and it is
creature-bearing, so W6a's surface is affected too.

`w6b_gates` G6 re-derives the refutation rather than restating it: the walk's MIPS writer set is
`{1, 142, 144, 149, 274, 435}`; the independent linear scan for the HLE call SHAPE the format
guarantees reproduces `{1, 142, 144, 149, 274}`. **ef435 is the only unreproduced id.**

### ★ 3. Six containers go ON as READ-only

`ef151, ef152, ef225, ef445, ef460, ef510` — found by the linear call-shape scan the reachability walk
never reached (mean reachability 0.905), each adjudicated by disassembly. `ef225@0x57c`, `ef151@0x584`
and the walk-confirmed `ef211@0x584` are **byte-identical `StoreImage(&rect_on_stack, buf)`
boilerplate**. **ef225 is one of the five co-transform containers and the record did not mention it.**

### ★ 4. The 15-vs-22 count flag is SETTLED, arithmetically

`W6-TEXEL.md` §1.10 recorded that R1's headline ("15 containers touched") disagreed with its own
enumeration (22 distinct ids) and left the flag visible. Re-measured:

```
walk LoadImage u MoveImage u loader-op-0x07        = 15 ids   <- the HEADLINE
   u walk StoreImage (6 store-ONLY) u ef038's arm  = 22 ids   <- the ENUMERATION
```

**Neither was wrong; they described different sets, and the 7 ids the enumeration adds are READS.**
The correction is that the *corrected* 15 is a **different** 15: **ef435 out, ef038 in** (its HLE op 12
texanim arm is a genuine program VRAM write, and already an unconditional W6a/W7 refusal).

### The one per-cell verdict in the corpus

`MoveImage`'s destination const-folds to `$a1 = 704, $a2 = 256` on **3 of its 5 sites**, and all three
containers declare that cell → hard refuse `ef001.x704_y256`, `ef142.x704_y256`, `ef144.x704_y256`.
**0 of 18 `RECT*` arguments resolve**, exactly as §1.10 predicted.

> ⚠ **SHARPER, NOT NARROWER — and the shipped message said the opposite until B2g corrected it.**
> All 30 non-creature cells of ef001/ef142/ef144 carry the program-write hazard anyway, so those
> containers refuse wholesale. What the per-cell verdict adds is that on ONE cell the destination is
> RESOLVED rather than unresolvable.
>
> ⚠ **It is a TRIPWIRE that no real spec can reach today** — all 30 of those cells are also
> depth-unknown, so none of them is ever emitted. `w6b_gates` G4 fires it directly on the gate
> function, with a real page wearing the hazard record those three containers carry, because a
> tripwire nobody tested is a comment. The same is true of the UNWRITTEN-COLUMN refusal (§1.5): the
> 10 bindings are all ef390's and the cells they read have no writer, so the gate is fired with a
> real spilling model given one synthetic cover cell.

## 1.7 W7 / TEXANIM — a disjointness, MEASURED rather than assumed

All **39** protected clip rects plus the texanim region itself, intersected against all **378** scenery
cell-writer spans across the five armed containers:

```
file-span intersections : 0 / 378        shared VRAM cells : 0
creature x in {192, 256, 320}   scenery x >= 384   on all five armed containers
```

**The line the lane may cite:** *a scenery texel edit cannot reach the protected set, so W7's L4
co-transform obligation does not extend to this lane.* ⚠ **Conditional on the table DECODING** — on an
armed region the reader cannot parse, the honest report is *"the table did not decode, so this
disjointness was not measured for this container"*, and `_gate_texanim`'s undecodable refusal now says
so in those words. All five stock armed containers decode.

---

# 2. THE FORMAT VERDICTS

## 2.1 Indexed 8bpp — SHIP

| pass | scope | byte-identical |
|---|---|---:|
| A | every writer cell, ramp palette | **2,648 / 2,648** records over 2,572 distinct cells |
| B | cells an `so` binding samples, at its own depth + CLUT | **298 / 298** cell × binding views |

Zero mismatches, zero raised exceptions. W6a's contract (`repaint.write_indexed_png` →
`_read_indices`) transfers to scenery **unchanged**.

## 2.2 Indexed 4bpp nibble pack — SHIP

| pass | scope | byte-identical |
|---|---|---:|
| A | every writer cell, 256×128, 16-entry row | **2,648 / 2,648** |
| B | cells a 4bpp binding samples | **125 / 125** cell × binding views |

```
unpack4:  out[2i] = raw[i] & 0x0F     (even u -> LOW nibble)    out[2i+1] = raw[i] >> 4
pack4:    raw[i]  = out[2i] | (out[2i+1] << 4)   + REFUSE any index > 15
```

**The PNG carries one byte per texel with values 0..15 — never Pillow's `bits=4`.** The nibble packing
is ours end to end, so no PNG bit-order convention can reach the container. This honours
`W6-TEXEL.md` §2's warning **by construction** rather than by care.

### ★ THE NIBBLE ORDER IS NOW MEASURED — and the prior proof has NO SURVIVING ARTIFACT

`W6-TEXEL.md` §2 recorded low-nibble-first as *"empirically confirmed"* on two cells. A2 searched both
study trees and SCRATCH: **nothing survives** but that sentence. So it was re-proved, and generalised
from 2 cells to the corpus.

* **Byte identity is BLIND to the question.** `pack4(unpack4(b)) == b` *and*
  `pack4_swapped(unpack4_swapped(b)) == b`, both `True`. A discriminator was required.
* **The discriminator:** vertical neighbour disagreement `V` is invariant under *any within-row
  permutation*, and the nibble order is exactly a within-row permutation — so `V` is a **free control**
  for horizontal disagreement `H`.
* **Calibration on the cast-proven 8bpp answer** (byte *i* = texel *i*, which W6a's emblem read
  correctly on screen): `H_shipped 0.6529 < H_swapped 0.7103`, `V 0.6389`, **93/93 pages agree,
  unanimously.** An instrument that cannot re-find a known answer is not an instrument.
* **The 4bpp question:** canonical wins **44 / 48**; with a signal floor of `|ΔH| > 0.003` it wins
  **36 / 36, no dissent** (the 4 dissenters separate by ≤ 0.00273 against a mean winning margin of
  0.075). They are **diagnosed, not averaged away**: ef184 / ef447 / ef498 read `H ≈ 0.92–0.95` with a
  far lower `V` — a **depth** signature (ef447 x576 is in the measured dual-depth set) — and ef405
  x704 is 98.8 % one index with `ΔH = 0.00000`.
* **The load-bearing argument is not statistical.** The PSX rule is ONE rule at every depth —
  *lower-order bits hold the lower `u`* — and its 8bpp instance is cast-proven on screen.
  Low-nibble-first is that same rule one level finer.

## 2.3 15bpp direct — SHIP as **RGBA + an explicit STP sidecar**, alpha display-only-but-CHECKED

```
encode  r8 = r5<<3   g8 = g5<<3   b8 = b5<<3        stp -> a separate 1-bit sidecar
decode  r5 = r8>>3   g5 = g8>>3   b5 = b8>>3        word = stp<<15 | b5<<10 | g5<<5 | r5

word -> (RGB, alpha, STP) -> word  over ALL 65,536 halfwords : 0 mismatches
alpha == 0  <=>  word == 0x0000                             : 0 violations
sidecar bit == bit15                                        : 0 violations
real writer-backed cells                                    : 14 / 14 byte-identical (26 views)
```

### ★ WHY THE SHIFT AND NOT `v * 255 // 31`

The scale form is what `texture.bgr555_rgba` uses for glTF display, and it is right there — it puts
white at 255. Measured beside it, **the scale form is lossless only under a ROUNDING inverse; with a
flooring inverse it fails 30 of 32 channel values.** This lane's whole gate is byte identity, and
*a rounding rule is a place for the no-op to stop being a no-op* — the same argument `W6-TEXEL.md` §2
used to refuse RGBA for the indexed lane. Cost: white renders 248 instead of 255 (3 % of display
brightness) in exchange for an inverse that cannot be got wrong. The shift form is also **TOTAL**: any
8-bit colour an author paints floors cleanly, so the codec never refuses a colour — only an
inconsistent alpha.

### ★ SIDECAR vs ALPHA — decided, and the competing design is UNIMPLEMENTABLE

`0x8000` (STP set, RGB 0) and `0x0000` (the cutout) are **different words that both render black**. One
alpha channel cannot carry both *"this is a hole"* and *"this blends"* without collapsing that pair.
Therefore:

| file | mode | carries | authority on import |
|---|---|---|---|
| `<cell>.png` | RGBA8 | 5:5:5 colour in RGB; **cutout in alpha** | RGB **yes**; alpha **checked, not read** |
| `<cell>.stp.png` | L (0 or 255) | bit 15, per texel | **yes** |

Four refusals, each naming its fix: `a ∉ {0,255}`; `a == 0` but the word ≠ `0x0000` (name the word);
`a == 255` but the word encodes to `0x0000` (*"the hardware reads this as a CUTOUT; nudge one channel
to 8, or set STP"*); a sidecar value ∉ {0,255}. A **missing** sidecar refuses too — it is
authoritative, so defaulting it to zero would clear the blend flag on every texel of a 100 %-STP panel
and report success.

> **THE EXACT MIRROR OF THE INDEXED LANE.** There the *palette* is display-only and the import reads
> only indices; here the *alpha* is display-only and the import reads only RGB + STP.
> **One law, two lanes: the container stays the authority; the PNG carries what the author must SEE.**

**The sidecar is load-bearing, measured:** the STP share ranges **0 %** (ef405, both cells) to **100 %**
(ef150 col 576), and the cutout share reaches **63 %** (ef429 x448 y384). A lane that dropped bit 15
would flatten ef150's whole panel and set the blend flag on every texel of ef405's.

**But size the lane honestly.** Of the 2,572 scenery cells only **14** have a derivable 15bpp depth and
only **4 are lawful** — `ef082.x640_y256`, `ef405.x576_y256`, `ef446.x448_y256` (all three spill) and
`ef429.x448_y256` (no spill); with the per-cell map `ef429.x448_y384` joins them. **The 15bpp WRITE
surface is 4–5 cells, of which 2 are page-scope-safe.** The codec is proven; the surface is tiny, and
it ships **UNCAST** — no lawful 15bpp cell sits in a container reachable from an existing bench row.

## 2.4 The display-palette rule for multi-binding cells

All 187 read cells, classified:

| class | cells | share | **rule** |
|---|---:|---:|---|
| **A** one binding | 94 | 50.3 % | carry the one CLUT, as W6a does |
| **B** N bindings, same depth, same CLUT | 51 | 27.3 % | same as A |
| **C** N bindings, same depth, **different CLUT** | **25** | 13.4 % | editable PNG in the **lowest-addressed** binding's CLUT + every other palette as a **read-only alternate view of the SAME index bytes**, both NAMED in the manifest |
| **D** N bindings, **different depths** | **17** | 9.1 % | **REFUSE** (§1.4) |

**Class C is forced, not chosen.** The import already reads *only the indices* and ignores whatever
palette the returning PNG carries. One byte array, N renderings. The manifest **must name both** — an
author who never learns the second key will tune a colour they cannot see. Concretely for ef211's
`(640,256)`: editable `cell.640_256.png` in CLUT `(80,244)` plus read-only
`cell.640_256.as-x96_y244.png`. Widest case: ef038/ef407 `(640,256)`, 27 bindings over 2 CLUT cells.

## 2.5 The cutout law and the in-place constraint transfer to ALL THREE depths

Export → edit → import → splice, one clean cell per depth:

| cell | no-op delta | punch / fill | container bytes changed | inside the cell | length |
|---|---:|---:|---:|---|---|
| ef007 (512,256) 4bpp | **0** | 0 / **114** | **72** | True | unchanged |
| ef038 (512,256) 8bpp | **0** | 0 / **54** | **144** | True | unchanged |
| ef082 (640,256) 15bpp | **0** | 0 / 0 | **288** | True | unchanged |

144 texels → 72 / 144 / 288 bytes **is** the depth, exactly. At 15bpp the transparent set is
`{word == 0}` — §1.8's rule (*"DERIVED from the active palette, never assumed to be `{0}`"*) in its
palette-less form: derived from the **values**.

---

# 3. WHAT SHIPS AND WHAT REFUSES

## 3.1 SHIPPED

| # | deliverable | what it unlocks |
|---:|---|---|
| 1 | **the per-VRAM-cell page map** `reskin.page_cells`, keyed `(tag, x, y)` | names **1,179** previously-unnameable cells; **+20** immediately lawful |
| 2 | **`w != 64` ENFORCEMENT** at both the rect view and the cell map | 0 cells today — free now, silently catastrophic the day it is not |
| 3 | the indexed scenery lane at **4 AND 8 bpp** | 2,648/2,648 + 423/423 views |
| 4 | **`expect_bpp`** — stated by the author, CHECKED against the `so` derivation, never chosen | guarded a second time against the chunk's own `nClut4`/`nClut8` |
| 5 | **`expect_cell`** — the same discipline for the VRAM cell | refuses on a creature page, whose unit is the PART |
| 6 | **the CO-TRANSFORM remedy** | **16** cells |
| 7 | **the NAME-EVERY-COLUMN gate** | **70** UV-exact cells; refuses page scope on the 36 spill-in; the unwritten-column branch is a FAIL-SAFE (corpus-unreachable today — §1.5's caveat) |
| 8 | **per-model stitched `spill.<geom>.png` preview** (read-only) | the author *sees* the whole picture, *edits* the cells it is made of |
| 9 | **SAME-BYTES-TWO-DEPTHS refusal, separate and earlier** | **17** cells / 6 effects |
| 10 | **the display-palette rule** (class C alternates) + **shared-read disclosure** | **25** + **93** cells |
| 11 | **the program-VRAM refusal from the CORRECTED list** + 3 named cells + the READ disclosure | refuse 175, **disclose 113**; the 3 by-cell MoveImage refusals are FAIL-SAFES (those containers emit 0 pages — §1.5's caveat) |
| 12 | **the 15bpp codec + lane, gated, UNCAST** | 4–5 cells; exhaustive 65,536/65,536 |
| 13 | **the id-0 REGION PARTITION** + the page-cell derivation-identity gate | §4 |
| 14 | **the W7 disjointness disclosure** (0/378, conditional on the table decoding) | no new mechanism |

## 3.2 REFUSED, by name, each carrying its measurement

| refusal | measurement | why no remedy exists |
|---|---:|---|
| **DEPTH-UNKNOWN cells** | **2,385 / 2,572 (92.7 %)** | The container declares no model that samples the cell, so its bit depth is not a fact it states. The probe built to guess it is **FALSIFIED at 54.5 % on a 3-way choice**. It must not ship, **not even as a disclosure**. |
| **SAME-BYTES-TWO-DEPTHS** | **17 cells, 6 effects, 3 triple-depth** | Two index arrays over one byte block. No art is coherent under both. |
| **PROGRAM-VRAM WRITE containers** | **175 cells / 15 containers**; **3 by cell name** | 0 of 18 `RECT*` arguments resolve; the walk is a lower bound (mean reachability 0.905). |
| **PROGRAM-VRAM UNKNOWN** | — | The lists are keyed by effect id, so silence is **ignorance, not safety**. Refused as a WRITE. |
| **ef038 window-only texel edits** without `acknowledge_texanim_frames` | 12 cells | unchanged from W6a/W7 |
| **an UNWRITTEN column** | **10 bindings / 8 cells** (all ef390, all 15bpp) — a FAIL-SAFE: ef390's cells are all depth-unknown too, so no real spec reaches this branch today (§1.5's caveat) | nothing uploads them — there is nothing to repaint |
| **ef251's 6 shared cells** | 6/6 unread | a Madeen shared-column repaint is out of reach at any depth |
| **RGBA for the INDEXED lane** | 88.75–99.24 % exact recovery *before* anyone paints; 8.31 % duplicate CLUT words | unchanged — and it now quotes **its own** reason string, not the scope one |
| **`--quantize` / `--mint-clut`** | — | **DEFERRED.** A palette *writer*, mutually exclusive with a `[[reskin.target]]` on the same palette — a genuine two-writers conflict, unlike texels-vs-palettes. |

> ★ **The two refusal strings were SPLIT.** `W6B_REASON` used to carry four clauses — co-transform,
> same-bytes-two-bindings, u-spill, 15bpp — and **three of them are now shipped mechanisms**. Leaving
> it in place would have made every refusal quote three capabilities as excuses. The successor names
> only what remains (depth-unknown / same-bytes-two-depths / program-VRAM write / unwritten-column
> spill); the indexed lane's RGBA refusal moved to its own `INDEXED_RGBA_REASON`, because that one is
> about EXACT RECOVERY and would still hold if every cell in the corpus were lawful. **Splitting them
> is what stops a SCOPE change from quietly rewriting an IDENTITY argument.**

---

# 4. THE ENGINE SEAMS

**`reskin.py`** (derivation) — `page_cells` + `PageCell` beside the rect view; `assert_page_cells_identical`;
`attribution(include_direct=True)` (a parameter, never a second scanner — the `_regions(partition=)`
precedent); `Id0Split` / `id0_splits`; `_regions` gains its **second** inversion.
**`repaint.py`** (edit) — `TexelPage` grows `kind` / `cell` / `hazards`; `scenery_surface` emits pages
AND refusals from ONE walk; the three codecs; the four gates; the disclosures; `export_art` /
`scaffold_text` learn the scenery namespace. **`texture.py`** owns `direct15_split` / `direct15_word`,
because ONE module owns BGR555.

## ★ THE REGION-PARTITION GAP — the highest-value new gate in the rung

`_regions` listed sector 0, both id-3 images, the id-5 image, the id-4 split, camera blocks and GEOM
blocks. **The id-0 resource was in the list under NEITHER partition.** For the CLUT lane that is
correct — it *writes* id-0 inline palettes. For the texel lane it meant a scenery splice would run with
`page_rel`, the rect count and the `(x, y, w, h)` **rect table ungated**, and a mis-seek there re-aims
the whole page map silently.

What was *already* covered: the inline CLUT payload (by the self-check's *"every DERIVED palette
re-derives and is byte-exact"* gate, and by `id0_palettes`' own stream-end assertion). What was **not**:
the rect table — read by `scenery_pages`, and by nothing that check runs.

```
partition="texel" :  gate   [P, P + pixelDataRel)   # header + clutWord table + the inline CLUT stream
                     license[P + pixelDataRel, ...) # the page PIXEL stream (and the id-9 payloads)
partition="clut"  :  the exact inverse
```

**Plus a DERIVATION-IDENTITY gate**: `page_cells(patched) == page_cells(orig)`, enforced at the build
call site — *a law in a docstring is a wish*. The two are different instruments on purpose: `_regions`
compares BYTES, `assert_page_cells_identical` **RE-DERIVES the map**, so a rect-table edit that
happened to land outside a gated span is still caught.

⚠ **`id0_splits` carries a measurement of its own**: on **248 of the 385** corpus id-0 resources the
page pixel stream runs past the id-0 payload's sector-padded end and continues into the **id-1 resource
of the same chunk** — 248 of 248 unanimously, never into another chunk or resource id. So the bound is
the streamed **id-0 [+ id-1] RUN**, never the id-0 resource's size, which would refuse 64 % of the
corpus.

**SEC 6 Q7 — "does the id-0 rect-table gate have anything to CATCH?"** It is a fail-safe with zero known
violations, so `w6b_gates` G3 manufactures one: a synthetically perturbed rect table (rect 0's VRAM
`y + 128`) is **CAUGHT by name**, and a write inside the pixel stream is **LICENSED**. ⛳ **The gate is
not a comment.**

---

# 5. THE CAST

> ## ⚠ THE CAST RECORD (running) — 1a and 1b both NEGATIVE; the vehicle premise is FALSIFIED
>
> **Cast 1a (the ink wheel, sha `d09f8c78…`)**: not legible — owner video + full-resolution frame
> sweep agree. The §6-Q6 outcome: brighter-on-bright under additive stacking adds nothing a moving
> fire does not already add.
> **Cast 1b (the punch wheel, sha `913a60c4…`, `--mode punch`)**: **the gaps do not show either** —
> owner video + a 48-frame full-segment sweep at every fire surface (dome, sea, pillar, ground
> burn). A punched annulus covering ~25 % of the texture cannot hide, so this is not legibility:
> **cell (704,256)'s bytes are not what the on-screen fire samples.** Both deploys were
> byte-verified live, so the file path is not in question.
> **THE LAW THIS MINTS — AN `so` READER IS A BINDING, NOT A DRAW.** The so-record proves a model
> *can* sample a cell, not that the model is ever drawn or visible. §5.1's "cast-proven upload
> path" premise below inherited W5's magenta proof — but that proof went through the **palette**
> (shared by every binding on CLUT (0,247)), so it proved the palette path, never this cell's. The
> visible fire is very plausibly the id-3 program's own primitives sampling the DEPTH-UNKNOWN
> cells — recon Q1 exactly. §5.1 is kept below as written: it was the correct inference from the
> evidence the census could produce offline, and its failure is the finding.
> **Cast 1c (deployed, verdict pending): THE STRIPED CELL CENSUS** (`phoenix_cell_probe.py`, sha
> `eabee19a…`) — zero-writing is depth-invariant (0x00 is the transparent value at 4/8/15bpp), so
> every one of ef211's 12 cells is lawfully marked with k stripes (k = its number, legend in the
> script's output). Whatever fire goes banded names its cell by COUNT; scrolling moves bands,
> never counts. Revert chain: probe → 1b punch → 1a ink → stock.

## 5.1 The vehicle — ef211 (Phoenix), cell `(704, 256)`, the fire field

```
id                ef211.x704_y256   ->  cell.s0.x704_y256
writer            s0 id-0 page rect 2  @0x11678, 16,384 B      (SINGLE writer)
reader            GEOM 0x2b668, 8bpp, tpage 155, CLUT cell (0,247)   (SINGLE reader)
                  = pal.s0.x0_y247.e256 -- "a full-screen roiling flame texture and the single most
                  visible thing in the cast" (phoenix_reskin.toml)
coverage          8,128 of 8,192 halfwords -- 99.2 % of the cell is live art
hazards           co-transform NO . dual-depth NO . multi-palette NO . shared-read NO
                  spill-in NO . spill-out NO . lower-half NO . texanim NO
program           read-storeimage -> A READ.  Disclose, do not refuse.
addressable       TODAY, with no new key
```

| candidate | disqualifier |
|---|---|
| ef227 `aerial_ground` (576) | worst cell in the corpus: co-transform **and** triple-depth **and** 15bpp, stacked |
| ef227 `energy_rings` (448) | 3 same-bytes-two-bindings pairs |
| ef227 `sky_dome` (704) | lawful, but the reader spills **cross-resource** into 768 — composes on three live levers |
| a fresh unrelated effect | no bench row, and no proven upload path |
| **ef211 (704,256)** | **none** |

> **And the decisive argument is not hazard arithmetic — it is that the upload path for this exact cell
> is ALREADY CAST-PROVEN.** W5's magenta probe recoloured all 315 live entries of the five bound
> palettes and the owner reported *"magenta showed up in the flames"*. **The id-0 scenery path reaches
> the screen on ef211, on this palette, in this cell.** Given that W6a spent four confirmations proving
> *nothing blits* on a different surface and W7 spent a rung establishing that nothing runs the texanim
> table, choosing the one cell whose pixels are KNOWN to arrive is the difference between a verdict and
> another negative result.

## 5.2 COMPOSE vs CLEAN — resolved to CLEAN, on a live-state fact

ef211's W5 override was **wiped** from `FF9CustomMap` by another session's campaign deploy, so the
container on disc is stock and the clean option costs nothing. Ship the texel repaint **alone, onto
stock ef211** — one lever, one change, one verdict. **Do not re-apply the W5 violet recolour in the
same artifact:** it targets `pal.s0.x0_y247.e256`, which is *exactly this cell's palette*, so a composed
artifact would put both levers on the same 8,128 halfwords and make a stock-vs-new read ambiguous.
Compose later, as W6a did on ef227, once the texel lever is proven alone.

⚠ **Re-verify before staging.** The install is shared mutable state and 18+ sessions run concurrently:
read the live `ef211`'s sha and confirm it is stock (or absent) at deploy time.

## 5.3 THE VERDICT STATEMENT — read this to the owner before the cast

> Cast **Stock Phoenix** (bench **30301**, ability row **198**, STEINIV → **Rune** → Stock Phoenix).
> **PASS:** the full-screen roiling flame field carries a **hard-edged bright ring with three radial
> spokes** — a straight-edged, unmistakably drawn figure that holds its shape while the fire moves
> around it. **FAIL:** the fire field looks entirely stock.
> **CONTROL, and it is part of the proof:** the **fire bird itself must be UNCHANGED**. The creature is
> an id-4 page and this lane never touches it — a changed bird means the wrong bytes were written,
> which is a louder failure than a missing ring.

**The stamp must be legible under ADDITIVE compositing.** W5 cast A missed because a blue-leaning,
×0.85-desaturated key washed out where stock flame cores go to white: *for VFX textures the in-game
read keeps the channel the blend favours.* Under additive blending a *darker* stamp subtracts nothing,
it merely fails to add. So the ink is **the live palette entry with the HIGHEST luminance, measured at
build time, never chosen by eye** (the texel lane writes zero CLUT bytes, so the shape's colour is
whatever entry we point at), and the shape is W6a's precedent figure — *"a wheel, not a disc"* is a
phrase that survives a moving texture.

⚠ **SEC 5.3 EXPECTED THE CUTOUT GATE TO FIRE, AND ON THE GATE'S OWN RING IT DOES NOT.** At r = 40..48
the ring lands entirely on live texels: punch 0 / fill 0, **nothing acknowledged away**. That is a
measurement the cast's own stamp must RE-TAKE, not inherit — and if its shape does cross the
transparent boundary, `acknowledge_cutout_reshape = true` is the ack's legitimate use and the
punch/fill counts belong in the staging report.

## 5.4 The ladder — what each cast proves, and what waits

| cast | vehicle | proves | needs |
|---|---|---|---|
| **1 (this rung)** | **ef211 `(704,256)` 8bpp**, row 198 | the scenery texel lane reaches the screen; the per-cell map, the depth guard, the id-0 region partition and the `read-storeimage` disclosure are all correct **in one frame** | nothing new — row 198 exists |
| **2** | **ef211 `(576,384)` 4bpp** — same container, same row, same deploy script | the **4bpp nibble pack** AND **lower-half addressing** in one change: this cell is unreachable through `(tag,x)` today, and its *upper* half is a two-palette refusal | cast 1 green |
| **3** | ef227 `x832 y256/384`, row 196 | the **co-transform remedy** (2 cells, 4 PNGs) | casts 1–2 green |
| **4** | ef227 `x704` + `x768` (sky dome), row 196 | the **name-every-column gate** across two *resources* | cast 3 green |
| **—** | 15bpp | **stays UNCAST.** No lawful 15bpp cell sits in a container reachable from an existing bench row; the codec ships proven-offline, like retime's writer | honest, stated |

**Cast 2 is the single most valuable follow-up and it costs nothing extra**: `ef211.x576_y384` (writer
`s0` id-0 page rect 4 `@0x25678`, single reader GEOM `0x33960` 4bpp CLUT `(208,244)`, 2,688 halfwords
covered, no spill, no co-transform, no shared read) is in the **same container, same bench row, same
deploy script** as cast 1. **The rung's central new mechanism proves itself on the vehicle it already
has.**

## 5.5 Bench + deploy posture

| requirement | status |
|---|---|
| ability row | **row 198 "Stock Phoenix" already exists** on STEINIV's Rune menu — **no `Actions.csv` edit** |
| bench field | 30301, already deployed |
| relaunch | **NOT needed** — no new row, no BattlePatch change |
| `~` reload | **NOT needed** — a page upload is itself the cache-invalidating event; the container is re-read per cast |
| cast 2 | same row, same container, same deploy script — **no bench work at all** |

Stage to `C:\gd\SCRATCH\summon-format\repaint-w6b\ef211\` with its own `deploy_repaint.py`.
**Do not deploy.** Preflight, in this order: (1) `Memoria.ini [SfxHybrid] Enabled = 0` — **verify, do
not assume** (it pins `EffectId = 227`, so even armed it would mask nothing here, which is the worst
kind of wrong); (2) no `ModFileList.txt` in `FF9CustomMap` omitting `ef211` — THE SILENT-FALLBACK LAW;
(3) a first-deploy snapshot of whatever the folder holds, once per root; (4) `[SfxProbe]` armed, and
**archive its log to SCRATCH the same session**; (5) re-read the live `ef211` sha and confirm the stock
baseline.

---

# 6. GATES AND SUITES

`py w6b_gates.py` — **7/7**, corpus only (no install read, no deploy, no install write):

| gate | what it proves | headline |
|---|---|---|
| **G1** | the format identity, per class | 8bpp **2,648/2,648** + 298 views · 4bpp **2,648/2,648** + 125 views · 15bpp **65,536/65,536 exhaustive** + 14 cells / 26 views · nibble order **44/48**, **36/36 with signal**, 8bpp control **93/93** |
| **G2** | the cast artifact | ef211 `(704,256)`: no-op **0**, delta entirely inside `0x11678..0x15678`, length + strict re-parse unchanged, punch/fill **0** with nothing acknowledged, region invariant + page-cell identity, kit self-check **21/21** |
| **G3** | the id-0 region partition, and its fail-safe | both halves gated the right way in both partitions; a **synthetically perturbed rect table is CAUGHT**, a pixel-stream write is **LICENSED** |
| **G4** | the refusal matrix + the three remedies + the moved pins | **27 rows**: every §3.2 refusal by name, the co-transform remedy refusing then BUILDING, the spill gate in three forms, `page.*.h256` naming both halves it splits into |
| **G5** | CLUT-lane byte compatibility | a scenery texel build and a scenery recolour **of the same container and the same palette** touch **0** common bytes — and the id-0 split explains it structurally (every CLUT byte below `pixelDataRel`, every texel byte above) |
| **G6** | the corpus census + **THE RE-DERIVATION PIN** | every number this document quotes, re-measured; the program-VRAM lists **re-walked from 385 id-3 images** and compared, ef435 refutation included |
| **G7** | provenance | byte-literal scan of 8 committable sources against 372 containers; the dossiers all outside the checkout |

**The re-derivation pin is the one that matters most for the future.** `PROGRAM_VRAM_WRITE_IDS`,
`PROGRAM_VRAM_READ_IDS` and `MOVEIMAGE_HARD_CELLS` are the ONLY place `repaint.py` carries a corpus
list rather than a derivation, because the derivation is a MIPS reachability walk over 385 program
images that a build cannot afford per target. **A constant that is a cache of a measurement has to be
re-measured somewhere**, and G6 is that somewhere — two instruments (the const-folding walk and an
independent linear scan for the HLE call shape), the ef435 refutation reproduced rather than restated,
and the 15-vs-22 arithmetic re-derived from the op families themselves.

---

# 7. WHAT THIS RUNG SHARPENED, AND WHAT IS STILL OPEN

## 7.1 Sharpenings — measurements that disagree with a dossier, both predicates named

| # | claim as recorded | as re-measured here | verdict |
|---:|---|---|---|
| 1 | **SAME-BYTES-TWO-PALETTES = 42** | 42 counting distinct palette KEYS with *"no CLUT at all"* (a 15bpp binder) counting as one; **38** counting only DECLARED CLUT cells | **both right, different predicates.** The 4-cell delta is exactly the cells that are ALSO same-bytes-two-depths and refuse earlier. Class C (25) is unaffected. |
| 2 | **rect-conservative spill superset = 83** | **94** under this gate's own rect expansion | **construction-dependent, so NOT pinned.** What is pinned is the SUBSET relation: the UV-exact 70 has **0** cells outside either superset. |
| 3 | **the 15-vs-22 program count** | the WALK's four-family union is 22; its writer union alone is 15 | **neither was wrong** — different sets, and the 7 extra ids are READS. |
| 4 | *"the by-cell MoveImage refusal narrows the container's refusal"* | all 30 cells of ef001/ef142/ef144 refuse as program-writes anyway | **SHARPER, not narrower** — the shipped message said the opposite and was corrected. |
| 5 | *"a creature-less container now exposes a surface — inverted for 65 effects"* | **65** containers expose ≥ 1 editable cell; **51** of them are creature-less | the inverted pin's real population is 51. |
| 6 | the 4bpp nibble population | **48** cells under A2's predicate (single writer, ≥1 4bpp reader); **40** under the kit's stricter emitted-page predicate (which also excludes dual-depth), where it wins 37/40 and **31/31 with signal** | the verdict is identical under both; the gate reports A2's population so the published 44/48 and 36/36 are re-measured rather than replaced. |
| 7 | `W6-TEXEL.md` §1.5's u-spill rate **41 of 316** | 41 of **315** textured `so` records; ef226 GEOM `0x9c804` has a live-looking tpage/clut but `textured == 0` and **0 UV-bearing faces** | **incomplete, not wrong** — and the 41 was always the 8bpp answer; the 17 15bpp spillers were invisible to the kit by construction. |
| 8 | the SYNTHESIS appendix (and this record's first draft, and `phoenix_field.toml`'s copy) marked ef211's two class-C cells **REFUSE multi-palette + shared-read**, covers 3,136/4,064 | the shipped kit **BUILDS both**, with the class-C display-palette disclosure and the `.as-*` alternate views; measured covers **3,584 / 5,737** | **the code was right and the prose wrong** (V1 F4): E2/C is a disclosure, not a refusal — REFUSE belongs to the two-DEPTHS law. ef211's editable share is 4/12, and the "representative" framing is corrected in the appendix. |

## 7.2 Open questions, with the cheapest experiment for each

| # | question | cheapest experiment | what it would unlock |
|---:|---|---|---|
| 1 | **Can the 2,385 depth-unknown cells be attributed AT ALL?** `so` records are the only evidence, and 222 of 372 containers declare zero non-creature GEOM blocks — they draw with sprites and particles, which set a tpage somewhere the container does not declare. | Re-run the const-folding `ImageWalker` over the 385 id-3 images looking for **GPU primitive tpage constants** and the args of `Hi_DrawEffModel` (op 24) / `Hi_DrawSliceEffModel` (op 199). One constant tpage per container narrows depth for every cell it owns. | up to **2,385 cells** — two orders of magnitude more than any other lever |
| 2 | **Is the walk missing WRITES, not just reads?** 6 real `StoreImage` sites the reachability walk never reached; 384/385 images carry unreached code-shaped space. Only the READ op was byte-scanned. | Run the nearest-`lw` shape scan for **op 0 and op 166** across all 385 images and adjudicate every hit by disassembly. | either hardens the refusal list or grows it — a silent lost edit either way |
| 3 | **Does a lawful cell whose LOWER half is unread contain live art?** ef211 `(704,384)` has a real 16 KB writer and no reader at all. | **The cast itself** — cast 1 changes only `(704,256)`; a seam or a half-height stamp means the lower cell is live and something reads it without an `so` record. | evidence for #1, free |
| 4 | **Where do ef390's 10 writerless 15bpp bindings sample from?** | Check whether ef390 is ever cast in isolation; if it always follows another effect, the residual-VRAM hypothesis is the answer and the refusal is permanent. | closes the only *"refuse because the art is not in the file"* class |
| 5 | **Is the class-C alternate-view rule enough, or do authors need a merged preview?** | Export ef038 `(640,256)` both ways and look at them. | UX only — does not gate the ship |
| 6 | **Does the additive stamp read at all?** | **The cast.** If a max-luminance ring is invisible, the next probe is a **cutout** stamp (punch holes in the fire) — additive's one unambiguous negative signal. | the verdict, and a fallback that needs no new code |
| 7 | ~~Does the id-0 rect-table gate have anything to catch?~~ | **CLOSED** — `w6b_gates` G3 perturbs a rect table and the gate fires by name. | ⛳ |

## 7.3 Still deferred, with reasons unchanged

* **`--quantize` / `--mint-clut`** — a palette WRITER, mutually exclusive with a `[[reskin.target]]`
  on the same palette. A genuine two-writers conflict, unlike texels-vs-palettes.
* **Authoring the texanim table** — W7 ships a READER; nothing consumes the table, so no edit could be
  verified, and on x64 the arming op already writes past the record it means to arm.
* **"Which texels are the wing"** — the overlay answers *which texels are live*, and only that. The
  honest instrument remains the `summon-export` glTF opened in Blender.

---

## APPENDIX — ef211's complete non-creature cell table, the rung in miniature

```
cell             writer off   bpp   cov      status
x448_y256        0x01678      -     -        REFUSE  depth-unknown
x448_y384        0x05678      -     -        REFUSE  depth-unknown + lower-half
x512_y256        0x09678      -     -        REFUSE  depth-unknown
x512_y384        0x0d678      -     -        REFUSE  depth-unknown + lower-half
x576_y256        0x21678      4     3,584    EDITABLE + DISCLOSURE  (multi-palette class C + shared-read)
                                             readers 0x30340 clut(128,244) / 0x33960 clut(208,244)
x576_y384        0x25678      4     2,688    * CAST 2 -- lawful once the per-cell map lands
                                             single reader 0x33960 clut(208,244)
x640_y256        0x19678      4     5,737    EDITABLE + DISCLOSURE  (same class C pair
                                             = W6-TEXEL sec 1.4's ef211 example, exactly)
x640_y384        0x1d678      -     -        REFUSE  depth-unknown + lower-half
x704_y256        0x11678      8     8,128    ** CAST 1 -- LAWFUL, ZERO hazards, the fire field
x704_y384        0x15678      -     -        REFUSE  depth-unknown + lower-half
x768_y256        0x3f000      -     -        REFUSE  depth-unknown (id-9)
x768_y384        0x43000      -     -        REFUSE  depth-unknown (id-9)
```

Twelve cells: **four editable — one with ZERO hazards (cast 1), one owed to the per-cell map (cast
2), and two class-C multi-palette cells that build WITH the display-palette disclosure — and eight
refused because the container never says what depth they are.** ⚠ An earlier draft of this table
(and of `phoenix_field.toml`'s copy) marked the two class-C cells REFUSE with covers 3,136/4,064 —
that conflated multi-PALETTE (class E2/C: one index array, N renderings, editable with named
alternates) with the same-bytes-two-DEPTHS law (which does refuse), and carried stale covers; the
shipped kit builds both cells, measured covers 3,584/5,737 (V1 F4). So ef211's editable share (4/12
= 33 %) is RICHER than the corpus-wide shape (~7 % of scenery cells are editable, 93 % depth-unknown)
— **the vehicle was chosen for its cast-proven upload path and its zero-hazard cell, not as a
statistical average.** What IS representative is the refusal texture: two-thirds of its cells fail
for exactly the reason two-thirds of the corpus does.
