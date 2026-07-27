# W6 — THE TEXEL REPAINT (rung W6a: creature pages, indexed lane)

> **Lever #2.** W4 shipped a per-index **colour function** over a stock summon's own CLUTs. It can
> rotate a hue; it structurally cannot move a texel from one index to another, so it can never change
> a **shape, an edge or a silhouette**. This rung rewrites the **indices**. `summon-reskin` grows a
> second table (`[[reskin.texel]]`) and a second reading verb (`export-art`); the two levers compose
> into ONE container with ONE ledger and ONE revert, and their byte-disjointness is **proven by
> rebuilding the sibling and intersecting the changed-offset sets**, not asserted.

**STATUS: ★ BUILT, offline-proven, CAST PENDING.** 7/7 W6 gates, 250 kit tests, 358/1 tier-w suite,
w4_gates 8/8, w5_gates 9/9. The deploy artifact is staged under `C:\gd\SCRATCH\summon-format\repaint-w6\ef227\`.
**Nothing was deployed and nothing was committed by the build round.**

| | |
|---|---|
| stock ef227 | `fe590d00a01d95c6dc473cee9fea9096b9ded63c3daae3aab693099c6d0ed167` |
| composition base (W4 spectral mist) | `7fef205ffbe547545374de9d1017613448777f0251d9d425b55f7796f688b89a` — 4,832 CLUT bytes |
| **the composed W6a artifact** | **`813a7ea4c461a06beec6bfe62ec47b61f7e81589d6d94cc17bad5489e18a8682`** — + 1,032 texel bytes |
| total delta vs stock | 5,864 of 823,296 bytes (0.712 %) — the two halves **disjoint**, everything else byte-identical |

---

## 1. The measured laws this rung stands on

Recon: R1 (regions + the writer census), R2 (sampling truth + the round-trip design), R3 (product
surface + the gate list). Every number below is a measurement, and where a later sweep **corrected**
an earlier one the correction is stated in place rather than the earlier number quietly replaced.

### 1.1 The texel surface, by class (R1)

**44,908,544 B = 62.3 % of the 372-container corpus** is texel data, in exactly **four** classes, all
in resource ids {0, 1, 4, 9}. ef227 alone carries 458,752 B = 55.7 % of its own container.

| class | files | units | bytes | writer posture |
|---|---:|---|---:|---|
| **id-4 creature pages** | 24 | 93 pages | 1,523,712 | **SINGLE-WRITER, 24/24** — this rung's whole scope |
| id-0 pageBlock stream | 372 | 1,317 rects → 2,531 engine pages | 41,467,904 | multi-writer possible |
| id-0 inline rects | — | 490 rects | 758,272 | **no pixel payload beyond CLUT** — answered NO |
| id-9 alternate pages | 28 | 117 pages (37 resources) | 1,916,928 | participates in collisions |

*(The 44,908,544 headline is the three classes that carry texels; the 758,272 B of inline rects are
counted in the inventory and excluded from the total, which is why the column does not add up to it.)*

Two negatives worth keeping, because both close a question rather than defer it. **(a)** All 490
inline rects sit at `x = 0`, `w = 256`, `h ∈ 0..6`, and **every row of every rect is named by a
clutWord of its own chunk (490/490)**; independently, **all 340 `so` bindings corpus-wide have tpage
page-y = 256**, so no model samples the CLUT band as texels. **(b)** id-2 / id-6 / id-8 / id-10 carry
**zero** texture: every derived texel/CLUT byte lies in id ∈ {0,1,4,9}, and all **1,005** GEOM blocks
live in ids 2/6/5/8/3/10 — **none** in 0/1/4/9. A2's phrasing "VRAM pages in chunk archives" does not
survive.

### 1.2 THE IN-PLACE CONSTRAINT — confirmed for every class

Same-length pseudo-random splices over **every** region of every class (ef227, ef381, ef447, ef038,
ef498, ef390, ef211, ef435 × classes a/b/c/d) — **3,404,288 B rewritten; every derivation the kit
makes came back byte-identical in every case, and zero phantom GEOM blocks appeared.** No class needs
a directory or header rewrite. The whole lever is same-length splices, exactly like W2/W3/W4/W5.

### 1.3 ★ CO-TRANSFORM == MULTI-CHUNK (R1) — the corpus's whole hazard, in one predicate

2,665 unique VRAM page cells are declared corpus-wide. **34 are multi-writer, in exactly 5
containers:**

| effect | chunks | cells | max writers | pairs | byte-identical | different |
|---|---:|---:|---:|---:|---:|---|
| ef225 | 2 | 4 | 2 | 4 | **0** | 4 (96.89–99.91 %) |
| ef227 | 2 | 6 | 2 | 6 | **0** | 6 (81.05–99.95 %) |
| ef251 | 2 | 6 | 2 | 6 | **0** | 6 (51.75–95.97 %) |
| ef381 | 9 | 16 | **5** | 138 | **0** | 138 (1.03–99.98 %) |
| ef447 | 3 | 2 | 2 | 2 | **0** | 2 (99.97, 100.0 %) |

Three findings fall out of that table and they are the reason the scenery lane is deferred:

1. **NOT ONE of the 156 writer pairs is byte-identical.** There is no "repaint once, copy twice" case
   anywhere in the corpus — every collision is genuinely time-shared, authored art at two cast
   phases, and must be CO-TRANSFORMED (art supplied for every writer) or refused.
2. **All 156 pairs are cross-chunk; 0 are same-chunk.** Only **5 containers in the corpus have more
   than one chunk** (ef225/227/251 = 2, ef447 = 3, ef381 = 9) — **all five collide, and all 367
   single-chunk containers structurally cannot.** So the CO-TRANSFORM LAW *is* the multi-chunk law
   and the predicate is one line: `len(chunks) > 1`.
3. **6 of the 34 cells involve an id-9 writer** (ef227 ×2, ef251 ×2, ef381 ×2), so the collision is
   not id-0-vs-id-0 only.

⚠ **The CLUT lane's hazard map is NOT reusable as the texel gate.** The same pass measured 3,140 CLUT
cells with only **20** multi-writer (ef381 19, ef447 1) and **1** dual-depth. ef225/ef227/ef251 are
*clean* at CLUT level and *hazardous* at texel level — `reskin.PaletteMap.hazards` would report no
danger on exactly the containers this rung most has to gate.

**How the kit encodes it.** `repaint._gate_collisions` deliberately tests the **cells and the file
spans**, not the chunk count — because ef227 IS a two-chunk container, so a chunk-count refusal would
refuse the one effect this rung is proven on. The near miss is real and one header field away: six
corpus effects (ef179/186/210/226/276/435) park **id-9 slots at x = 320**, precisely the ladder rungs
their own `partCount` leaves unused.

### 1.4 ★ SAME-BYTES-TWO-BINDINGS (R2) — supersedes "dual-depth" as the general gate

Dual-depth is real and is a **6-effect class**: ef203, ef227, ef381, ef424, ef447, ef498 — **65
mixed-depth binder pairs, all 65 overlapping**, none disjoint. ef227 has **three** dual-read columns,
not the one A1 named, and column 576 is **triple**-depth:

| col | pair | shared halfwords |
|---:|---|---:|
| 448 | `0x0bb0e8` 4bpp clut(192,244) × `0x0c2264` 8bpp clut(0,246) | 3,294 |
| 448 | `0x08d888` 4bpp × `0x0c2264` 8bpp | 2,729 |
| 448 | `0x08fc20` 4bpp × `0x0c2264` 8bpp | 2,750 |
| **576** | `0x029e14` 8bpp clut(0,249) × `0x02ba28` 4bpp clut(0,244) | 2,444 |
| **576/640** | `0x0be030` **15bpp DIRECT** × `0x029e14` 8bpp | **11,710** |
| 832 | `0x08c418` 8bpp clut(0,248) × `0x0bc30c` 8bpp clut(0,251) | 4,064 |

**But bit depth is the wrong discriminator.** ef211's column 640 shares **1,659 halfwords** between
`0x02d344` (4bpp, clut **(80,244)**) and `0x02ed7c` (4bpp, clut **(96,244)**) — **same depth,
different palettes, same bytes**, rows 321..383. A depth-only test misses it entirely. The law is
therefore **SAME-BYTES-TWO-BINDINGS**: *any two `so` bindings whose UV-covered halfword sets
intersect are two readings of one byte region and no single edit is coherent under both.*

Note A2's "4,032 halfwords" for the col-448 cloud-band × rings pair is the **rect product**
(63 rows × 64 hw); the polygon-level number is **3,294**.

### 1.5 ★ THE U-SPILL LAW (R2) — a template must be keyed on the MODEL, never the column

A model's `u` is 8-bit but an 8bpp page is only 128 texels wide, so `u > 127` addresses the **next
64-halfword column**. Corpus: **41 of 316 so-bound textured models (13.0 %) sample past their own
column.** ef227's sky dome `0x08dccc` (u 0..254) spans columns 704 + 768 — and those two columns come
from **different resources** (`c0 id-0 @0x11470` and `id-9 @0x32000/0x36000`). A per-column paint
template silently cuts a picture in half.

### 1.6 ★ THE MARGIN LAW — generalises, but WEAKER than R2 measured, and this rung is the correction

R2 measured the law on two effects: ef227's interior holes per part `0,0,62,0,12,33` = 107 of 33,037
dead texels (0.32 %), ef211's `0,2,2,40,0,0` = 44 of 46,442 (0.09 %) — and stated *">99.6 % of a
creature page's dead texels form a single border-connected pad."*

**This rung swept all 93 pages (`w6_gates` G6) and the corpus number is 98.767 %, not 99.6 %:**
6,765 interior-hole texels of 548,510 dead. Per effect the spread is real —

| | sampled | dead | interior holes | pad share |
|---|---:|---:|---:|---:|
| ef227 | 65,267 | 33,037 | 107 | **99.68 %** |
| ef211 | 51,862 | 46,442 | 44 | **99.91 %** |
| ef251 | 63,677 | 34,627 | 536 | 98.45 % |
| worst effect **ef381** | — | 31,178 | 1,357 | **95.65 %** |
| worst page **ef261 part 1** | — | 4,831 | 625 | **87.06 %** |

**The law survives in the form that matters** — the dead region is overwhelmingly ONE outer pad, so
*"paint inside the island"* is still a complete instruction — but the **interior-hole class is real**
on some effects, which is precisely why the coverage overlay hatches pad **green** and interior hole
**red** rather than one colour. Two effects are not a corpus; R2's number was honest for its sample
and is superseded here rather than deleted.

### 1.7 ★ THE 64 % COVERAGE CORRECTION of A2 — a bbox is not a coverage

`w4-recon/A2-ATTRIBUTION.md:171-174` says *"Every part's UVs span U[1,127] V[0,127], i.e. each part
uses **100 %** of its own page block."* **The bbox is exactly right; the inference is wrong.** Polygon
coverage at texel centres (with corner-OR so a one-texel-thin face lights its own texels) measures:

```
corpus, 24 packages / 93 pages:  975,202 of 1,523,712 texels sampled = 64.00 %   (548,510 dead, 36.00 %)
per effect: 52.8 % (ef211, ef225)  ...  71.9 % (ef261)
ef227 66.4 %   ef211 52.8 %   ef251 64.8 %
```

Reproduced **exactly** by `w6_gates` G6 this round, independently of R2's script. **~1/3 of every
summon's texture budget is never sampled by any face** — a tool that hands a painter a bare 128×128
page hands them a third of a canvas that does nothing.

And the pad is **not identifiable from the pixels**: ef227's dominant pad *index* differs per part
(`138/111/109/164/80/104`) while all six decode to the same word `0xa10e`, and the pad index also
occurs *inside* the sampled island. **Coverage can only come from the uv pools** — which is the whole
argument for shipping `<name>.coverage.png` beside every exported page.

### 1.8 THE CUTOUT LAW at texel level

`texture.bgr555_rgba` maps `0x0000 → (0,0,0,0)`: transparency is by VALUE. Corpus: **49,746 index-0
texels (3.26 %)**, of which **20,293 are UV-sampled (2.08 % of the sampled area)** — real silhouette
holes, not pad. Exactly **one** zero entry per row and it is always **entry 0**: **93 STP-clear
entries across 93 pages vs 23,715 STP-set (99.61 %)** — entry 0 is the only STP-clear entry in the
whole corpus. Separately, **0 of 38,861 creature faces** carry the semi-transparent flag, so STP is
inert for creature pages corpus-wide (A2 proved this for ef227's 2,416 faces; it now generalises).

⇒ A texel edit controls the **silhouette**, which a palette edit never could. So the kit counts
boundary crossings **in both directions** — `punch` (opaque → hole) and `fill` (hole → opaque) — and
any non-zero count **REFUSES** unless the row says `acknowledge_cutout_reshape = true`. The
transparent index set is **DERIVED from the active palette**, never assumed to be `{0}`: a gate that
hard-coded index 0 would be asserting the corpus rather than reading the palette in front of it, and
under a composed CLUT edit the palette in front of it is not the stock one.

### 1.9 TEXANIM — the gate is right, and its reason is now stateable

**5 armed packages**: `ef038` 116 B @`0x6dfc4..0x6e038`, and `ef177/ef493/ef494/ef495` 364 B each —
the four are **byte-identical** (sha `3884b4eb…`), one creature family. The region lives in the id-5
model image, provably disjoint from the id-4 texel span. Only ef038 actually **arms** it (op 12, 2
sites).

R1 decoded the outer format, so the refusal is no longer "unread ⇒ refuse": `u32 count; count ×
20-byte record; payload arena`, with **`4 + 20*count` == the first record's pointer exactly** (ef038
count=3 → 0x40; ef177 count=9 → 0xb8), every pointer landing inside the region, and each target's
first four fields reading as a texel **rect that fits a 128×128 page in 100 % of cases** — ef038
`(27,62,11×12)`; the ef177 family `(33,78,9×14)` and `(24,102,8×14)`. **Both surviving readings hurt
a repaint of that window**: a frame blit overwrites repainted texels mid-cast, or a moving sample
window shows frames the author never previewed. Refusal stands, unconditional, no key lifts it.

⚠ **The predicate had to be re-implemented, not inherited.** `reskin._gate_texanim` selects creature
targets with `t.pal.slot < 0` — it keys on a **Palette** object. A texel target has no palette, so an
inherited gate would simply never fire and would be a comment. `repaint._gate_texanim` keys on the
texel targets themselves; `w6_gates` G4 fires it on all five.

### 1.10 THE 15bpp-DIRECT INVENTORY and THE PROGRAM-VRAM REFUSAL LIST

**15bpp direct: 24 bindings across 12 effects**, all `tpage & 0x180 == 0x100` — ef390 ×10, ef150 ×2,
ef424 ×2, ef427 ×2, and ef082 / ef203 / ef227 / ef381 / ef405 / ef429 / ef446 / ef447 ×1 each. There
is **no CLUT at all**, so the indexed lane is inapplicable by construction. Two structural notes:
ef227's 15bpp panel resolves to the **multi-writer** column 576 — its only lever is also its worst
hazard — and **ef390's 10 bindings have NO writer in the container at all** (330 of 340 bindings
corpus-wide do have one; these 10 are the whole exception set), so there is nothing there to repaint.
`reskin.attribution` drops every 15bpp binder at `reskin.py:396`, so all 24 are invisible to the
toolkit today.

**The program-VRAM refusal list** — containers whose *program or loader script* may write VRAM from a
source R1 could not resolve, enumerated by op group:

* loader-script op `0x07` (the LoadImage-owning sequence opcode), 1 site each —
  **ef087, ef125, ef134, ef143, ef223, ef224, ef308, ef381, ef415**
* HLE op 0 `LoadImage` — **ef149, ef435**
* HLE op 1 `StoreImage` — **ef007, ef072, ef149, ef211, ef214, ef276, ef390 (×3)**
* HLE op 166 `MoveImage` — **ef001, ef142, ef144, ef149, ef274**
* HLE op 12 (2 sites, the one that arms ef038's texanim) — **ef038**

⚠ **R1's headline calls this "15 containers touched"; its own enumeration unions to 22 distinct ids.**
The count and the list disagree and **the LIST is what a refusal must be built from.** Left visible
rather than silently reconciled — argument resolution (which VRAM region each call writes) is out of
reach without a tracker, which is exactly why these are a refusal list and not a supported surface.
Of them, ef211/ef276/ef435 carry creatures; ef211 is W5's cast-proven scenery effect, so this is not
hypothetical for W6b.

---

## 2. THE FORMAT DECISION — an indexed (P-mode) PNG, and the gate that settles it

```
decode -> P-mode PNG (palette = the CLUT row, pixels = the indices, tRNS = the transparent entry)
       -> reload -> indices

INDEXED-PNG ROUND-TRIP byte-identical:  93 / 93 creature pages, 24 / 24 packages, fails = []
```

Reproduced this round by `w6_gates` G1 through the **kit's own codec** (`repaint.encode_indexed_png`
→ `repaint._read_indices`), not R2's prototype. A real edit round-trips exactly too: a 113-texel
index stamp moved **exactly 113 bytes** on ef227 p0, 58 on p2, 113 on ef211 p0, 31 on ef251 p0.

**Why RGBA cannot be the spine — measured on NO-OP round trips, before anyone paints:**

| page | exact-colour recovery | after a MEDIANCUT re-quantize | colour-ambiguous entries |
|---|---:|---:|---:|
| ef227 p0 | 98.96 % | 96.20 % | 4 |
| ef227 p2 | 96.63 % | 96.20 % | 32 |
| ef211 p3 | 99.24 % | 96.98 % | 2 |
| **ef251 p0** | **88.75 %** | **72.41 %** | **62** |

Corpus-wide **1,979 of 23,808 palette entries (8.31 %)** are duplicates of the **full 16-bit word,
STP included** (both counts are 1,979) — so an index swap among them is inert in colour *and* blend;
the damage is that **byte-identity dies, and with it the gate this whole lane rests on**. On ef251 p0
an identity RGBA round trip flips **1,844 of 16,384 texels**. A lane whose no-op is not a no-op cannot
carry a byte-identity gate. It is therefore **refused by name**, with that measurement in the refusal
text, rather than silently not existing.

4bpp packing is solved but unshipped: expand two-per-byte → repack is **byte-identical** on ef227 col
448 and ef211 col 640, and the **low-nibble = even-`u`** order is empirically confirmed. Do **not**
use `bits=4` PNG — Pillow writes it, but the semantics needed is the *PSX* nibble order, which you
only control by owning the pack.

---

## 3. THE W6a / W6b SPLIT — what shipped, what refuses, and why

**W6a (shipped): id-4 creature pages, indexed lane, and nothing else.** It is the one texel class
measurably free of every known hazard: single-writer 24/24, disjoint-from-everything 24/24, uniform
8bpp 128×128 decodable 24/24, and VRAM `x ∈ [192,384)` on all 93 pages with no scenery rect or id-9
block declaring a cell inside the band (`w6_gates` G6: **0 collisions by VRAM cell, 0 by file span**).

**W6b (deferred, refuses by name).** Every out-of-scope surface quotes one string,
`repaint.W6B_REASON` — *"the scenery texel lane is W6b: co-transform / same-bytes-two-bindings /
u-spill / 15bpp unhandled"* — so a report line names the rung that owns the surface instead of reading
like a bug. What W6b owes, each with its measurement: the co-transform remedy (34 cells, 5 containers,
0 of 156 pairs identical); SAME-BYTES-TWO-BINDINGS (§1.4, catches ef227 cols 448/576/832 *and* ef211
col 640); U-SPILL (41/316 models, sometimes across two resources); 15bpp-direct (24 bindings, no CLUT
to index against); the RGBA / quantize / mint-CLUT lanes (§2); and the program-VRAM list (§1.10).

**Why split at all**, and why this is not caution for its own sake:

1. **It repeats the tier's own twice-validated method.** W4 shipped the CLUT lever on one effect and
   cast-proved it; W5 generalised second, and *that* is when the multi-writer / dual-depth / texanim
   classes surfaced — classes a single-effect cast could not have exposed.
2. **The easy slice is measurably free of every known hazard and the hard slice touches all of them
   at once.** Stacking three unproven remedies into one cast makes a failure undiagnosable: which
   remedy was wrong? That is the house rule (**one change per in-game test**) applied at rung scale.
3. **W5's Phoenix cast-A miss is the live precedent.** A scenery-half assumption was wrong and it was
   only diagnosable because the creature half was isolated from it. W6 isolates them from the start.

---

## 4. Where the engine landed, and the ONE seam it opened in `reskin.py`

**`ff9mapkit/ff9mapkit/summons/repaint.py`** — a sibling module, not more `reskin.py` (which is 2,589
lines and whose docstring earmarks itself lever-#1-only). It **consumes** `reskin.py`'s shipped
derivations (`creature_pages`, `PaletteMap`, `texanim_region`, `scenery_pages`, `id9_pages`,
`_regions`) and `rescore.py`'s infrastructure hub (`drift_guard`, `EXPECTED_STOCK_SHA`,
`_refuse_repo_path`, `_refuse_install_path`, `Ledger`, `modfilelist_refusal`) rather than re-deriving
either, and defines its own `TexelPage` / `TexelTarget` / `TexelBuild` / `SelfCheck`.

**CLI:** `summon-reskin export-art --ef N [--out DIR] [--art-lane indexed|rgba] [--no-coverage]`, plus
`plan/build/verify/deploy/revert` resolving `[[reskin.texel]]` alongside `[[reskin.target]]` in ONE
spec. Names are `tex.partN`; guards are `expect_page_offset` / `expect_page_bytes` /
`expect_page_wh`; `palette_from` is a checked cross-reference (a page's palette is a **header fact**,
not a choice — naming another row refuses).

### ★ THE REGION PARTITION IS INVERTED, NOT COPIED

`reskin._regions` gated *"the id-4 header + all N texel pages"* byte-identical — correct for a
CLUT-only lane and exactly backwards for this one. It now takes a **`partition` argument**: `"clut"`
licenses the CLUT strip and gates the header + every page; `"texel"` licenses the pages and gates the
header, the CLUT strip and the sector pad. **One function, two partitions — never a second copy that
drifts.** `w6_gates` G3 proves the shape rather than trusting it, on the real ef227:

```
id-4 resource 0x4a000..0x63000 (102,400 B)
regions outside id-4 are IDENTICAL region-for-region ......... True  (23 each)
TEXEL partition LICENSES the pages    (gated n pages == 0) ... True
TEXEL partition GATES  the CLUT strip (strip subset gated) ... True
CLUT  partition GATES  the pages      (pages subset gated) ... True
CLUT  partition LICENSES the CLUT strip (gated n strip == 0) . True
the two partitions cover the WHOLE id-4 resource ............. True (union 102,400 / 102,400, gap 0, self-overlap 0)
an unknown partition name .................................... REFUSES
```

**That is the only load-bearing change to `reskin.py`.** `w6_gates` G5 says so in bytes: all three
cast-proven CLUT artifacts still build their exact shas — `bahamut_reskin.toml` → `7fef205f…` (4,832
B), `phoenix_reskin.toml` → `4daab8ad…` (2,374 B), `madeen_reskin.toml` → `78b395f8…` (3,054 B).

### Hot reload — stronger here than for the CLUT lane

`SFX.Play()` re-reads the container from disc every cast **and** calls `PSXTextureMgr.Reset()`
unconditionally, wiping the whole 50-slot managed cache. A1's caveat *"the decoded-texture cache is
invalidated by page uploads, not by CLUT uploads"* was a **CLUT-lever** caveat: **a page edit IS the
invalidating event.** Recast to see it — no `~` reload, no warp, no relaunch.

---

## 5. THE PROOF — the ef227 part-0 EMBLEM

### 5.1 Why an emblem, and why composed rather than alone

A recolour is a colour function, so **a hard-edged geometric brand on an opaque hide cannot be
produced by any palette map at all** — where a "different flame pattern" on additively-composited fire
is exactly the sort of change a sceptical observer could attribute to a hue shift (and W5's ADDITIVE-
COMPOSITING COROLLARY says the blend washes flame cores toward white anyway).

The artifact is **W4's spectral-mist recolour REBUILT + the emblem composed on top**, one container.
The kit does the composition itself: `[reskin.orthogonality] compose = true` rebuilds the sibling CLUT
spec and hands its patched bytes over as the splice base, so the palette half keeps exactly one source
of truth instead of being copied into a second file that can drift.

### 5.2 Every parameter, derived

`emblem_stamp.py` (committed) re-derives all of it from the user's own container:

```
ef227 tex.part0                page 0x04a1a0..0x04e1a0   128x128 8bpp   CLUT row @0x0621a0
coverage       11,563 / 16,384 texels sampled (70.6%), 4,821 dead, 0 interior holes, 468 faces
ink   idx 255  stock 0xef9c L=229   composed 0xf79c L=231
edge  idx   1  stock 0x8401 L=3     composed 0x8020 L=5
glyph          sampled-island centroid (63.8, 59.8); largest fully-sampled disc r = 26; ring at 0.80 R
stamped        1,037 texels = 9.0% of the sampled island, 6.3% of the page
MEASURED       1,032 texels actually DIFFER   |  dead-pad bytes moved 0  |  index-0 cutout flips 0
CLUT bytes this glyph needs: 0
```

The ink maximises `min(luma_stock, luma_composed)` over the indices the geometry **samples**, so it
reads under the stock violet palette *and* under the W4 spectral-mist palette the cast will actually
run — and because both chosen indices are already-live entries of the row, the brand costs **zero CLUT
bytes**, which is what lets it compose with a recolour *of that very row* without the two levers
meeting on a byte. The placement comes from the coverage mask, which is why `dead-pad 0` and `cutout
flips 0` are **measurements, not intentions**: the glyph provably cannot leave the geometry or touch
the silhouette. (`1,037` stamped vs `1,032` changed: five of the stamped texels already carried the
index being written.)

**Deterministic, and identical on both entry paths.** Re-running the generator reproduces the PNG
byte-for-byte (`8144063c…`), and running it against the extracted corpus container
(`--from ef227.bytes --root <tmp>`) produces **the same PNG as reading the install** — a law that held
on only one of two entry paths would not be one, and the whole gate/guard pipeline is therefore
exercisable with no install at all.

**The art is not in this repo and cannot be.** A decoded texture page is Square-Enix content. What
ships is the **generator**; `bahamut_emblem.toml` points at the PNG it writes into SCRATCH. The
byte-literal scan (`w6_gates` G7) covers all six new committable files — `emblem_stamp.py`,
`w6_gates.py`, `bahamut_emblem.toml`, `W6-TEXEL.md`, `summons/repaint.py`,
`tests/test_summon_repaint.py`, the four `.py` ones parsed for literals — and finds **one** literal of
≥6 non-uniform bytes — the ASCII word `b'tampered'` in a test fixture — and **0** of them appear
anywhere in the 372-file corpus.

### 5.3 ★ INDEPENDENT VERIFICATION (not the kit's self-report)

Four files read as raw bytes — the stock corpus container, W4's **frozen** staging artifact, the
staged composed container, and the emblem PNG re-opened through PIL — and every claim re-derived with
plain `struct` / set arithmetic:

```
stock  (corpus)      823,296  fe590d00a01d95c6dc473cee9fea9096b9ded63c3daae3aab693099c6d0ed167
W4 ref (reskin-w4)   823,296  7fef205ffbe547545374de9d1017613448777f0251d9d425b55f7796f688b89a
staged (composed)    823,296  813a7ea4c461a06beec6bfe62ec47b61f7e81589d6d94cc17bad5489e18a8682

(1) W4 CLUT SET = diff(stock, W4 ref) -> 4,832 bytes
      creature_clut_strip  0x0621a0 +3072   3,039 changed
      c0_clut_band0        0x000870 +3072   1,455 changed
      c1_clut_band0        0x0a2048 +1024       0 changed
      c1_clut_band1        0x0a2450 +1024     338 changed
      inside the four spans bahamut_reskin.toml guards: 4,832 of 4,832  (outside: 0)
(2) EMBLEM PNG  mode=P size=(128,128) 256 palette entries; max index 255
      diff(stock page 0, the PNG's indices) -> 1,032 bytes, all inside 0x4a1a0..0x4e1a0
      transparent palette indices (word == 0x0000): [0]     cutout flips: punch 0 / fill 0
(3) COMPOSED    diff(stock, staged) -> 5,864 bytes
      CLUT set n texel set = 0  (DISJOINT)
      CLUT set u texel set = 5,864 == the composed delta   (equal: True)
(4) EVERYTHING ELSE
      817,432 of 823,296 bytes byte-identical to stock (99.2877%)
      staged == W4 ref outside the page block ......... True
      staged page block == the PNG's indices .......... True
      CLUT strip 0x621a0..0x62da0 staged == W4 ref .... True
(5) MANIFEST vs BYTES: stock / base / patched sha256 all MATCH
```

**VERDICT: PASS.** The changed-vs-stock set is exactly *(the W4 CLUT set) ∪ (the emblem texel set)*,
the two are disjoint, and every other byte in the container is identical to stock.

> ⚠ **One deviation from the brief, and it is a fact about the machine, not the artifact.** The brief
> assumed the W4 CLUT set would be re-derived from the **live install override**. It cannot be: see
> §7. The frozen W4 staging artifact (`reskin-w4/mod/.../ef227`, written 2026-07-26 09:04, sha
> `7fef205f…`) was used instead — it is the file the W4 cast actually ran from, and it is independent
> of anything this session rebuilt.

---

## 6. THE CAST PROTOCOL

### 6.1 Preflight — `[SfxHybrid]` MUST be disarmed

W4's cast 1 minted THE HYBRID MASK law: with `[SfxHybrid]` armed, the managed model (Thomas) is posed
from the native skeleton and **the native creature is never drawn** — so the texture page under test
is not on screen at all and the cast reads "nothing changed". Disarm it before casting. This rung is
*more* exposed than W4 was, not less: the whole claim is about texels of the native creature's own
page.

### 6.2 Deploy — staged, NOT run

```
py C:\gd\SCRATCH\summon-format\repaint-w6\ef227\deploy_repaint.py            # --root defaults to FF9CustomMap
py C:\gd\SCRATCH\summon-format\repaint-w6\ef227\deploy_repaint.py --root D   # anywhere else
```

Writes `FF9_Data/SpecialEffects/ef227` (extensionless — `LoadFromDisc` reads the raw path). It refuses
a mod folder carrying a `ModFileList.txt` that does not already list `ef227` (THE SILENT-FALLBACK
LAW), and takes a **first-deploy snapshot** of whatever the folder holds, once per root, before
writing. **No relaunch** (§4).

### 6.3 How to cast

Bench field **30301**, ability row **196 "Stock Bahamut"** (`vfx1 = vfx2 = 227`, `type = 0`,
`studies/custom-summons/rung8-epic/bench/rung8.field.toml:124`). `~` → Warp to field → **30301** →
start the bench battle → **Iviv → *Spark* → Stock Bahamut**. Any save where Garnet summons Bahamut
normally plays the same override with no bench wiring.

### 6.4 What you should SEE if it worked

**A hard-edged white ring on the wing membrane, in the live spectral-mist key, on both wings** (part 0
is shared, so the brand appears twice in frame). Concretely, from the staged preview: a thick stroked
white circle, its interior divided into **three equal sectors by thin radial spokes** meeting at the
centre — a wheel, not a disc — outlined dark against the green membrane, about a quarter of the
membrane's width across. It should read as **drawn on the hide**: sharp-edged, opaque, following the
wing as it moves. Everything else about the cast — camera, timing, the spectral-mist colours, the
effect's own sky/ground/fire — is exactly what W4's cast already showed.

**Anything soft, anything hue-only, anything sitting on the mauve pad rather than on the wing ⇒ the
wrong file landed.** Those are the three things the build provably cannot produce.

### 6.5 Failure table

| symptom | likely cause |
|---|---|
| Thomas / a managed model instead of the dragon | `[SfxHybrid]` still armed — §6.1. This hid W4's cast 1 |
| Nothing changed at all | the W2/W3/W4 delivery checklist: wrong ability row (must point at 227), wrong mod folder, an extension on the filename, a `ModFileList.txt` that does not list it, or another `FolderNames` entry shipping its own `ef227` earlier in priority. **Nothing logs either way** — `suppressMissingError` is on |
| The brand appears but the colours are STOCK violet | the composition base did not land — the container is stock + emblem, not W4 + emblem. Check the deployed file's sha against `813a7ea4…` |
| The colours are spectral-mist but there is NO brand | a stale W4 container is live rather than this one; same sha check |
| The brand is soft / blurry / colour-shifted | not producible by this build (indices are written, not colours) — report it as a finding, not operator error |
| The wing silhouette changed | not producible by this build (`cutout flips 0`, gated) — same |

---

## 7. ⚠ THE LIVE RESTING STATE CHANGED UNDER THIS RUNG — read before deploying

R2 measured the install earlier this same session (its scripts carry 2026-07-27 08:25–08:35 mtimes)
and found `FF9CustomMap/FF9_Data/SpecialEffects/`
holding **ef211 (`17b6dcb6…`), ef227 (`7fef205f…`), ef251 (`78b395f8…`)** — W4/W5's cast-proven
resting state. **At the time of this report that directory does not exist.** Every file in
`FF9CustomMap` carries an mtime of **2026-07-27 08:55–08:56**, and `FF9_Data` now holds only
`embeddedasset/text` — the signature of a **wholesale campaign deploy by another concurrent session**
(CLAUDE.md §5: *"every `deploy_campaign` wholesale-replace WIPES it"*). The shared-install hazard,
observed live.

**Three consequences, all material to the cast:**

1. **ef227 currently reads STOCK in game.** The observer's "before" is no longer the spectral-mist
   Bahamut; it is stock Bahamut.
2. **The staged plan's `expect_live_sha256` is `null`** — correct, because the file was genuinely
   absent when the artifact was staged. The revert does **not** depend on it: it is snapshot-based.
3. **W5's ef211 and ef251 overrides are gone too**, so the Phoenix and Madeen casts are no longer
   resting in their proven state either. That is a W5 record item, not a W6 one, but a reader
   comparing casts needs to know.

**Two honest cast postures — pick one, do not mix them.**

* **(a) One-change-per-test, restored baseline (recommended).** Re-run W4's own deploy first —
  `py C:\gd\SCRATCH\summon-format\reskin-w4\deploy_reskin.py` — confirm the spectral-mist cast still
  reads as W4 proved, *then* deploy W6a. The single delta on screen is the brand. Cost: one extra
  deploy and one extra cast.
* **(b) Composed against stock, disclosed.** Deploy W6a straight onto the current (override-free)
  folder. The cast then shows **two** deltas at once — the recolour *and* the brand — but the recolour
  half is already `★★ CAST-PROVEN` from W4 and its bytes are pinned identical (`w6_gates` G5), so the
  only **unproven** thing on screen is still the brand. Acceptable; just say so in the verdict.

---

## 8. THE REVERT LADDER

| what | how | restores |
|---|---|---|
| **W6a** | `py C:\gd\SCRATCH\summon-format\repaint-w6\ef227\revert_summon_repaint_227.py [--root D]` | whatever the mod folder held at the moment of the **first** W6a deploy to that root. Snapshot written once and never overwritten, so a re-deploy still reverts all the way back. Idempotent |
| under posture (a) | the same script | W4's `7fef205f…` |
| under posture (b) | the same script | **deletes** the override — ef227 falls back to stock `resources.assets` |
| **W4** (if it was re-deployed) | `py C:\gd\SCRATCH\summon-format\reskin-w4\revert_summon_reskin_227.py` | that lane's own pre-deploy snapshot |
| the whole texel edit, in the spec | `enabled = false` on the `[[reskin.texel]]` row and rebuild | the composition base, byte-exact — an unedited re-pack is a byte-exact no-op |

The generated deploy/revert pair is the same plan-rendered template `reskin.stage` uses — one
implementation, a plan injected into it, never a second copy of a snapshot scheme that can drift from
the one that is proven. *(Cosmetic consequence, noted so nobody reads it as the wrong file: the shared
template's own docstring still says "summon reskin" and names itself `deploy_reskin.py` /
`revert_summon_reskin_<effect>.py` inside the text. The **filenames on disc** are
`deploy_repaint.py` / `revert_summon_repaint_227.py`, the baked plan says `bahamut-w6a-emblem`, and
the target sha is `813a7ea4…`. One template, two lanes — worth a prose pass, not worth a second
copy.)*

---

## 9. GATES AND SUITES

`py w6_gates.py` — **7/7**:

| gate | what it proves | headline number |
|---|---|---|
| **G1** | the indexed round trip is this lane's X0-class gate | **93/93** pages, 24/24 packages, byte-identical |
| **G2** | the emblem artifact rebuilds to the sha B2 verified independently | `813a7ea4…`, base `7fef205f…`, 1,032 texel B, halves disjoint, **20/20** kit gates |
| **G3** | one `_regions` function, two partitions, no overlap and no gap | 23 identical regions outside id-4; union 102,400/102,400, gap 0 |
| **G4** | the refusal matrix | **26 refusals**, each with its own reason, + 1 positive control |
| **G5** | the CLUT lane is byte-compatible | ef227 `7fef205f…` / ef211 `4daab8ad…` / ef251 `78b395f8…` |
| **G6** | the corpus census | 24 pkg / 93 pages, 64.00 % coverage, MARGIN LAW 98.767 %, **0** collisions |
| **G7** | provenance | 1 byte literal (`b'tampered'`, a test fixture) in 6 committable files, **0** of them in 372 corpus containers; art + staging outside the checkout; the repo and StreamingAssets destinations refuse |

**G4's matrix, in full** — W6b surfaces (a scenery page name; the `rgba` export lane; an unknown
lane; a container with no creature package) · format (an RGBA source; a 64×64 source for a 128×128
page; an index past the row; a missing source file) · **THE CUTOUT LAW** in both directions, plus
`acknowledge_cutout_reshape = "true"` as a **string** refusing while the literal `true` builds
(punch 1 / fill 0) · **TEXANIM ARMED** on all five of ef038/177/493/494/495, re-measured each run ·
**CO-TRANSFORM** in both forms (a shared VRAM cell and an overlapping file span, both against a
*derived* foreign cell, not a fabricated one) · guards (an unknown key; a mis-stated
`expect_page_offset`; a mis-stated `expect_page_wh`; `palette_from` naming another part's row; no
drift guard at all; the same target twice; a spec with neither table; **ART DRIFT** — art exported
from a different container).

> A note the gate itself records: **ef227 omitting `expect_sha256` correctly does NOT refuse**,
> because ef227 is registered in `rescore.EXPECTED_STOCK_SHA`. The unguarded refusal has to be probed
> on an effect the registry does not know (ef211), or the gate would be asserting the registry rather
> than the refusal.

**Suites, this round:**

| suite | result |
|---|---|
| `ff9mapkit/tests/test_summon_{repaint,reskin,rescore}.py` | **250 passed** (17.0 s) — repaint **73** / reskin 84 / rescore 93; the 73 are new this rung |
| tier-w study suite, single process (`test_{reskin,rescore,retime,retime_derive,summon_camera,w_survey}.py`) | **358 passed, 1 skipped** (58.7 s) — identical to W5's recorded baseline |
| `w5_gates.py` | **9/9** |
| `w4_gates.py` | **8/8** (X0 re-runs r1/r2/r3 + w1/w2/w3 and every tier-r/tier-w test module; X7 re-confirms ef227's artifact `7fef205f…` and the 372-container sweep) |
| `w6_gates.py` | **7/7** |

---

## 10. WHAT W6b OWES, and what is genuinely still open

* **The scenery texel lane** — the co-transform remedy (name and supply art for every writer of a
  shared cell), a per-VRAM-cell page map (today `reskin.scenery_pages` keys `(tag, x)` — uniqueness is
  a **measured coincidence, not a construction** — and collapses an `h=256` rect into one entry, so
  the lower cell `(x, y+128)` is not addressable; `repaint.other_page_writers` splits it for the
  collision census, but the *edit* surface still needs it), a `w != 64` refusal (`nbytes = w*h*2` as
  the cursor advance is right only because `w == 64` on 1,317/1,317, and that is unenforced), and the
  4bpp nibble pack (proven byte-identical, unshipped).
* **The 15bpp lane** — needs an RGBA path with an explicit **STP sidecar**; bit15 *is* STP there and
  has nowhere to live in an RGBA8 pixel that also carries cutout alpha (ef227 col 576 measures
  23.32 % / 28.27 % of halfwords with bit15 set). The 5:5:5 RGB itself round-trips exactly.
* **`--quantize --mint-clut`** — the one thing the CLUT lever can *never* do: re-derive the 256-entry
  row **from** the painted image (median-cut on the **UV-covered texels only** — weighting by the
  whole page is dominated by a pad that is 33–47 % of it), reserving entry 0 = `0x0000` and setting
  STP on every other entry. Must be **mutually exclusive** with a `[[reskin.target]]` on the same
  palette: that is a genuine two-writers conflict, unlike texels-vs-palettes.
* **Which texels are "the wing"** — the overlay answers *which texels are live*, and only that. Bone
  labelling was measured and does not answer it: only **31/77** (ef227) and **30/59** (ef211) bones
  bind to exactly one part, so a page is not one anatomical piece, and summon skeletons carry no
  semantic names. The honest instrument for "where is the wing" remains the existing `summon-export`
  glTF opened in Blender.
* **Page SHARING at one depth** — **65 shared pages across 38 effects** (ef381 8, ef447 6, ef498 6,
  ef179/226/227 3): a repaint there changes two models' look with no depth trap at all. Not a hazard
  the creature lane can hit, but a disclosure W6b owes an author.
* **The texanim field semantics** — the structure, the pointer closure and the rect bounds are
  measured; what the `(value, duration)`-shaped pairs *do* is still `[I]`. The refusal does not depend
  on settling it.
