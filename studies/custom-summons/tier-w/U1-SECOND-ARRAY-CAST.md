# W6b-3 (iii) — THE U1 SECOND-ARRAY CAST. ef038 `Shiva`, bench row 200, both halves of column 640

> ★ **STATE — CAST 1 RAN 2026-07-30 AND WAS READ: `VISIBLE_UNBANDED` (0.88), §6's THIRD OUTCOME.
> The cast is UNINTERPRETABLE FOR U1 IN EITHER DIRECTION, and the probe is REVERTED — the install is
> back to stock** (`ef038` deleted, `ef211` untouched `cbcc9fde…`, rows 192–204 stay). Column-640
> geometry demonstrably DREW (61–69 % of the whole column-640 prim pool per frame in the disc window)
> yet **no surface carried EITHER mark and the C1 control failed on the `nothing` branch**. The
> mechanism lead: **641 `DR_MOVE` VRAM-move packets on ef038 where the static census records ZERO**,
> the first block completing before any scored surface appears — §6's "runtime write hiding in the
> unwalked program bytes", observed in the capture rather than in theory. **Read §9**; full record +
> the critic's addendum: `…\u1-second-array\castread\REPORT-U1.md`.
>
> **This cast answers a question the offline round could not.** `second-array-lead/REPORT.md`
> refuted H_V (halfword A as a universal per-slot texture V-offset) at 0.85 and left R_FLAGS (a
> depth-keyed render-state bit) as the best-supported positive reading. **U1 — does the engine apply
> A at all? — is explicitly listed there as undecidable offline.** §5 of that report sketched the
> cast; this is that sketch, re-derived and re-sized at the machine, with the sketch's own vehicle
> choice and stripe counts both **changed** for measured reasons (§4, §8).

**WHAT IS BEING MEASURED.** Mark the UPPER and LOWER halves of one column with two DIFFERENT
gratings. A reader whose v is confined to `1..127` then names the half the engine sampled, by COUNT
and by THICKNESS:

| | question | instrument | answer shape |
|---|---|---|---|
| **THE CAST** | does the engine apply second-array halfword A? | `u1_cell_probe.py` — 12 thin stripes upstairs, 4 fat bands downstairs | 12 THIN → not applied · 4 FAT → applied |
| **THE CONTROL** | did the override load and does the column DRAW? | the same cast's 7 A=0x0000 readers | they must show 12 THIN under *every* reading of A |
| **THE RIDER** | which engine model, if applied? | the one wrap reader `0x79168` | WRAP / CLAMP / OFF-PAGE differ on its tip |

**BINDING-IS-NOT-A-DRAW still gates everything**, and this vehicle was chosen because it passes that
gate **in-cast**: because `0 + anything = identity`, the A=0x0000 family reads the UPPER cell under
every live reading of A, so if it bands, the upload landed and column-640 surfaces draw — no
cross-cast comparison, no prior probe, same frame.

**AND NO CONSTANT MOVES.** `ORDER_UNMEASURED` and every kit constant ship exactly as they are.
Whatever the screen shows, write it in the study. A FAT result is *not* "H_V confirmed" (§4, the
confound).

---

## 1. PREFLIGHT — W6b-1 §5.5, adapted, in this order

Everything here is **verify, never assume**. The values are what this session measured read-only; the
folder is shared mutable state and 18+ sessions run concurrently, so **re-measure at deploy time**.
`u1_cell_probe.py --deploy` prints its own reading of items 2, 3 and 5 before it writes anything.

1. **`Memoria.ini [SfxHybrid] Enabled = 0`.** Observed `:451 Enabled = 0`, `:452 EffectId = 227`.
   Pinned to 227, so even armed it would mask nothing on ef038 — **which is the worst kind of wrong**,
   because the cast would look fine while the hybrid drive posed a model nobody asked about. Check the
   number, not the section.
2. **No `ModFileList.txt` — THE SILENT-FALLBACK LAW.** `TryFindAssetInModOnDisc` TRUSTS that list and
   never calls `File.Exists`, so an unlisted override is INVISIBLE and this cast would read as a clean
   negative for a reason that has nothing to do with drawing. Observed ABSENT at the game root, in
   `FF9CustomMap` and in `FF9CustomMap-world`. `--deploy` REFUSES by name if one appears (exercised,
   exit 1, zero files written).
3. **The override slot's state, once per root.** Observed `FF9CustomMap\FF9_Data\SpecialEffects\`
   holds exactly **`ef211` as a FILE**, 530,432 B, sha `cbcc9fde…`, mtime 2026-07-28 23:35. **`ef038`
   is ABSENT** → first deploy CREATES it and revert DELETES it. `FF9CustomMap-world` has no
   `FF9_Data\SpecialEffects` at all, so no shadowing. `FolderNames = "FF9CustomMap",
   "FF9CustomMap-world", "MoguriMain", "MoguriVideo"` (`:6`); `UseFileList = 1` (`:8`) = *use a list if
   one exists, do not generate one* → live filesystem lookup, no relaunch.
4. **`[SfxProbe]` armed, and its log ARCHIVED TO SCRATCH THE SAME SESSION.** Observed `:440 Enabled = 1`
   with `:446 CapturePrims = 1`. Copy the log into `…\repaint-w6b\capture-logs\` before the next cast,
   not after — a campaign deploy wiped a probe mid-ladder once already.
5. **The live stock ef038 == the corpus copy.** `rescore.read_stock_effect(38)` reads
   `x64\FF9_Data\resources.assets` and returns **555,008 bytes byte-equal** to
   `C:\gd\SCRATCH\summon-format\ef038.bytes`, sha
   `8f71a91b5ea8761cb072d0c5aa53fdd6cd926ec03a77634a99bf582fec4eb2a2`. This is a base-container check
   (Steam / Moguri drift), not a mod-folder check — item 3 owns the override's absence. `--deploy`
   re-runs it and REFUSES on mismatch.
6. **Bench row 200 is live.** `FF9CustomMap\StreamingAssets\Data\Battle\Actions.csv` **line 12**:
   `Stock Shiva;200;None(0);AllEnemy(8);0;0;0;0;38;38;85;30;0;0;22;0;8;0;159`. animationId1 =
   animationId2 = **38**, so the short-summon roll cannot substitute (Shiva's short id 407 is
   unreachable from this row by construction). Rows 192–204 all present. **No `Actions.csv` change is
   needed and therefore no relaunch.**
7. **REHEARSE THE DEPLOY PATH FIRST — calibrate the instrument before judging with it.**

       py u1_cell_probe.py --deploy --mod-folder <temp>\FF9CustomMap --root <temp>\probe-root

   It prints `*** REHEARSAL`, exercises both ledger branches, verifies the readback sha and emits the
   revert — against a folder the game never reads. **This is not ceremony. It caught a real defect
   this round** (§8, the stale-snapshot order).

---

## 2. THE DEPLOY SEQUENCE — and THE LEDGER TRAP

```
  0.  (nothing)  rows 192-204 are already live; NO RELAUNCH is needed for this cast
  1.  cast       cd studies\custom-summons\tier-w
                 py u1_cell_probe.py --deploy      <- snapshots, writes, prints the readback sha
  2.  READ IT    (section 5).  Archive the [SfxProbe] log.
  3.  *** py C:\gd\SCRATCH\summon-format\repaint-w6b\u1-second-array\cellprobe\revert_probe.py ***
```

### ⚠ THE LEDGER TRAP — step 3 is not housekeeping

`summon-reskin deploy` takes a **FIRST-DEPLOY SNAPSHOT per root, once, and never overwrites it**.
Deploy any kit spec into this root while the probe container is still live and that snapshot records
**THE PROBE** as the pre-state — and the kit's revert then restores the probe, *forever*, as the
resting state of a mod folder nobody is looking at any more. No error, no warning, no symptom until
somebody casts Shiva months later and finds her striped. **Revert the probe first.** The emitted
revert script says so in its own docstring, and `--deploy` prints the same line after it writes.

The same trap in the other direction is why this probe never uses the kit's ledger: it keeps its own
`pre.ABSENT` / `deploy.ledger.json` under its SCRATCH root, so the two instruments can never consume
each other's snapshot.

---

## 3. WHAT IS STAGED, AND WHERE

| artifact | path |
|---|---|
| bench row 200 | `studies\custom-summons\rung8-epic\bench\rung8.field.toml` (committed, already deployed) |
| the instrument | `studies\custom-summons\tier-w\u1_cell_probe.py` |
| marked container + protocol + derivation + revert | `…\repaint-w6b\u1-second-array\cellprobe\` (SCRATCH) |
| prediction panels (5 PNGs) | `…\u1-second-array\predict\` (SCRATCH) |
| vehicle-selection artifacts (prior round) | `…\u1-second-array\vehicle\` (SCRATCH) |
| build/test harness — **not part of the shipped file** | `…\u1-second-array\build\` (SCRATCH) |

Regenerate from the committed source. **`u1_cell_probe.py` runs from `studies\custom-summons\tier-w\`**;
the harness scripts run from the SCRATCH `build\` dir.

```
py u1_cell_probe.py                 # stages the container + PROTOCOL.txt + probe.derivation.json
py <scratch>\build\verify_bytes.py  # the INDEPENDENT byte proof (does not import the probe)
py <scratch>\build\predict_u1.py    # the five prediction panels
py <scratch>\build\wrap_analysis.py # the wrap reader's per-end feature counts
```

**Location independence is proven, not asserted.** The file resolves the kit and the tier-w sibling by
PROBING for files that must exist, so it runs identically from tier-w or from SCRATCH. Verified by
building a simulated tier-w layout (temp dir + a directory junction to the real kit) and running the
identical file from there: container sha `1f20d798…` from tier-w == `1f20d798…` from SCRATCH == the
canonical staged copy, and the two `PROTOCOL.txt` bodies diff clean.

**Staged sha:** `1f20d79810d1123e90461ee8493223e7361acba7f5971ad784e15d0d386cc168`, 555,008 B.

---

## 4. THE PREDICTION TABLE

### 4.1 The vehicle is the COLUMN, not a record

27 of ef038's 28 non-creature `so` records bind column 640 — all P=1 slot 0, all `tpage 0x009a`
(column 640, page_y 256, 8bpp, semi 0). Independently re-walked from the bytes (magic `'so'`,
`recLen == 8+8P`, `arrayB == 8+4P`, `rec+recLen == geom_base` asserted on every record; creature GEOM
`0x5c800` excluded). The 28th (`0x86700`) binds column 512 and is unusable as a control — the region
it samples is all-zero stock under a transparent entry 0, so it draws nothing there.

| family | slots | clut | what it is |
|---|---|---|---|
| **A = 0x0080** | **20** | `0x3dc0` | the answer-carrying class; the bright 100 %-opaque solid pass |
| **A = 0x0000** | **7** | `0x3d40` | **THE IN-CAST NEGATIVE CONTROL**; the faint 71–76 % cut-out additive pass |

★ **A is perfectly confounded with CLUT here (20/20 and 7/7), and with blend mode.** That is R_FLAGS'
headline correlation reproduced inside one container — and it is why a FAT result may not be reported
as "H_V confirmed" (§4.4).

★ **SIX GEOMETRIC TWIN PAIRS** — the same mesh drawn twice with OPPOSITE A: byte-identical positions
AND byte-identical UV pools, differing in exactly ONE byte per face (the flag):
`0x3114c↔0x7b150` · `0x31a48↔0x7c838` · `0x32344↔0x7df20` · `0x32c40↔0x7f778` · `0x3353c↔0x80bc4` ·
`0x33e38↔0x85de0`. Base pass and additive glow pass drawn at the same place. (`0x79168↔0x79ae8` is
bbox-twinned but its UV POOLS DIFFER in 94 of 102 entries — roughly v_B ≈ v_A/2 — so its gratings
cannot coincide: **excluded by name** from scoring question 2.) ⚠ **The six pairs straddle container
resources: every A=0x0080 half sits in id-2, every A=0x0000 half in id-6 — and whether both resources
draw in the SAME cast is unverified offline. ALL SEVEN control surfaces live in id-6 while the
headline disc S1 is the only uniquely-shaped id-2 record, so C1 does not control S1's resource.** If
the pairs never appear together, question 2 has no instance — fall back to question 1, which needs
only id-2.

### 4.2 The two marks

Both cells are halves of **ONE id-0 page rect** `(x=640, y=256, w=64, h=256) @0x1946c`, uploaded by ONE
`LoadImage`. `reskin.page_cells` splits it into two `0x4000` cells purely for naming. **There is no
second upload to fail** — so if the upper mark is visible, the lower mark is in VRAM, and "no FAT
anywhere" can never be explained away as a failed lower upload.

Placement is **imported** from `odin_band_stamp.evenly_spaced_tops` with each cell's own
`odin_band_stamp.cover_span`; nothing is restated.

| cell | file | cover | mark | tops | duty | bytes |
|---|---|---|---|---|---|---|
| `cell.s0.x640_y256` **UPPER** | `0x1946c` | `(1,127)` | **12 THIN × 4 rows** | 4, 14, 25, 36, 46, 57, 67, 78, 88, 99, 110, 120 | 48/128 = 37.5 % | 6,144 |
| `cell.s0.x640_y384` **LOWER** | `0x1d46c` | `(0,127)` | **4 FAT × 8 rows** | 12, 44, 76, 108 | 32/128 = 25 % | 4,096 |

The discriminator is **two-dimensional**: COUNT 12 vs 4 (3:1) **and** THICKNESS 4 vs 8 rows (1:2), at
near-equal duty — so the read is structural, "many thin" vs "few fat", never "it got darker", which is
exactly the threshold this arc keeps paying for.

**Why the sketch's k=10 / k=2 was rejected**: the encoding is *k evenly-spaced stripes*, not *period k*.
At k=2 the lower cell's stripes sit 64 rows apart while the readers' UV patches are small (median
per-face v-span 22 texels on the headline disc), so only **71 of that disc's 140 faces** would be
crossed by any band — half the answer-carrying surface showing nothing, indistinguishable from "not
drawn". Measured coverage under the chosen split, every reader: **UPPER** 140/140 disc, 70/72 shards,
36/38 icicles, 27/27 and 26/27 orbs; **LOWER** 132/140, 70/72, 35/38, 26/27. Nothing is starved.

### 4.3 The table — every surface × every hypothesis

The chain, before the table. On the SCENERY lane A appears **nowhere in the upload path** (the rect's
VRAM destination is in the rect header), so the id-4 "bake and placement cancel" objection
(`texture.page_row` = `(raw_v+off)-off`) has no placement half to cancel against. If A is applied here
at all it can only be at sample time (`baked_v = raw_v + A`) or as a page-half select — and at A=0x0080
both land on the LOWER cell. **That is why this cast is a real test and not algebraically inert.** All
26 non-wrap readers have v ≤ 127, so OFFSET and SELECT make the same prediction.

Feature counts below are **derived over each whole surface**, not assumed — and they are
**texture-space totals, not what the eye counts on screen** (no face shows more than a few); the
on-screen read is pitch and thickness, per §5's scoring warning:

| # | surface | records | A | appearance | **(i) APPLIED** | **(ii) NOT APPLIED** | **(iii) NOT DRAWN** |
|---|---|---|---|---|---|---|---|
| **S1** | **the flat 5-point snowflake disc** — 140 faces, y-extent 57 vs ±2,081 in x and z; **the only wide-flat surface in the container** | `0x29dbc` | 0080 | `0x3dc0`, abr=1 additive | **0 THIN + 4 FAT** | **12 THIN + 0 FAT** | uniform stock, no banding |
| **S2** | 3-point shard bursts (y to 2,866), solid bright layer, 72 faces each | 12 records | 0080 | `0x3dc0`, abr=0 half-blend → dark navy bands | **0 THIN + 4 FAT** | **12 THIN + 0 FAT** | no banding |
| **S3** | shard bursts **bbox-identical to six of S2**, faint cut-out additive layer | 6 records | **0000** | `0x3d40` → transparent **HOLES** | **12 THIN + 0 FAT** | **12 THIN + 0 FAT** | no banding |
| **S4** | narrow icicle spikes, 38 faces each | 6 records | 0080 | `0x3dc0` → dark bands | **0 THIN + 4 FAT** | **12 THIN + 0 FAT** | no banding |
| **S5** | orb + tapered tail, v 1..255 — **THE WRAP READER** | `0x79168` | 0080 | `0x3dc0` → dark bands | **12 THIN + 4 FAT** | **12 THIN + 4 FAT** | no banding |
| **S6** | same geometry, additive twin of S5 | `0x79ae8` | **0000** | `0x3d40` → holes | **12 THIN** | **12 THIN** | no banding |
| **S7** | tall fan, column 512+576, v 65..127 | `0x86700` | 0000 | `0x3e00` | **invisible under all three** — samples all-zero stock texels under a transparent entry 0 | same | same |

⚠ **S5 IS NOT A WHOLE-SURFACE DISCRIMINATOR, and the design sketch was wrong to call it "the sharpest
single-surface discriminator in the cast".** Its v runs past 127, so it samples BOTH halves under both
hypotheses and shows 12 THIN + 4 FAT either way. **Only its BASE discriminates** — the 9 faces with
v 1..62 (model z −5..118, the compact near end):

| S5 BASE | THIN features | FAT features |
|---|---|---|
| (ii) NOT APPLIED | **49** | 0 |
| (i) APPLIED / WRAP | 0 | **16** |
| (i) APPLIED / CLAMP | 0 | **16** |
| (i) APPLIED / OFF-PAGE | 0 | **16** |

Categorical on the base under all three engine models; **mixed on the tip under (ii) and under WRAP
alike**. Score the base, never the tip, and treat S5 as corroboration only. (The tip *does* separate the
applied models from each other: WRAP marks 18/18 tip faces, CLAMP and OFF-PAGE only 6/18, and OFF-PAGE
additionally samples VRAM y ≥ 512.)

### 4.4 What each result buys, stated honestly

* **FAT** closes U1 positively and refutes R_FLAGS as a complete account — **but** A is perfectly
  confounded with CLUT and blend in this container, so the reportable claim is *"something in the second
  array moves the sampled cell"*, not *"H_V confirmed"*. The confound does not weaken the test, because
  the null being tested is *"nothing in the second array moves the sampled cell"*.
* **THIN** closes U1 in the negative direction only. Per the report's own caveat it is consistent with
  BOTH "A is a render-state flag" and "A is declared and ignored"; only the second leg (flip A on one
  record, look for a BLEND-STATE change) or a disassembly of the id-3 program / SFX loader separates
  those. **Do not bundle the flip with this leg** — it is a container write needing a backup and an
  explicit owner decision, and one change per in-game test.

### 4.5 The offline panels — read these before the video

`…\u1-second-array\predict\` — rendered from the user's own container with **real UV interpolation off
each reader's own GEOM primitive stream**, so the video is scored against a picture rather than a
memory. (The arc's protocol exists because a recalled prediction table was once drafted inverted; a
picture cannot be drafted inverted.)

| panel | what it shows |
|---|---|
| `u1-predict-texture.png` | both cells, stock vs marked, through both CLUTs — dark bands vs transparent holes |
| `u1-predict-surfaces.png` | S1–S6, stock \| (ii) \| (i) |
| `u1-predict-twins.png` | **scoring question 2**: the twin pairs superimposed — score only the SIX valid pairs (§4.1) |
| `u1-predict-wrap-models.png` | S5 under all four models, with derived per-end feature counts in the labels |
| `u1-predict-all-readers.png` | **all 27 readers**, (ii) vs (i) side by side — no surface in the cast is unpredicted |

---

## 5. THE CAST PROTOCOL

**Warp `30301` → STEINIV → `Rune` → "Stock Shiva"** (row 200). `Rune` is Steiniv's minted command 35,
not Vivi's `Spark` — the 192+ rows seat on Steiniv's learn list by construction.

**Cast it FIRST and ALONE in the encounter.** VRAM is shared: another effect loaded earlier in the same
battle could overwrite column 640. If a prior action's SFX has loaded, start a fresh encounter.

**Video, not stills** — every read is a COUNT and a THICKNESS on a moving surface. ~15 s, 60 fps; the
SFX layer updates every 4th frame. Archive the `[SfxProbe]` log the same session.

### ⚠ DO NOT SCORE THIS BY COUNTING BANDS ON SCREEN

The marks are 12 and 4 stripes ACROSS THE TEXTURE CELL, and no surface in this cast maps that cell to
one continuous chart: the disc's median face spans ~23 of the 128 texel rows, so a face shows ~2 thin
lines or ~1 fat line — never 12 or 4. Measured per face on the disc: under the upper mark **125/140
faces cross ≥2 stripes (median 2)**; under the lower **122/140 cross exactly ONE (median 1)**. The
read is PITCH and THICKNESS — **FINE/DENSE thin lines → A NOT applied · COARSE lines ~2× thicker →
A APPLIED** (1:2 thickness, ~3:1 density, near-equal duty — it is never "it got darker"). Score
against the §4.5 panels; they are ORTHOGRAPHIC model-space views and the battle camera compresses the
on-screen pitch.

### Three questions, in order

1. **THE BIG FLAT SNOWFLAKE DISC.** **FINE/DENSE banding → A is NOT applied. COARSE banding → A IS
   APPLIED.** This one surface decides U1 and needs no other. 38.5 % of its drawn pixels change between
   the hypotheses.
2. **A TWINNED SHARD** (the SIX valid pairs — §4.1; the seventh excluded by name). Fine → not applied;
   coarse → applied. In principle the applied case superimposes the faint A=0x0000 fine grating on the
   coarse one, but that cut-out additive layer is dim: **do NOT require seeing two gratings — the
   pitch of the BRIGHT layer is the read.** If the id-2/id-6 halves never draw together this question
   has no instance (§4.1) — fall back to question 1.
3. **S5's BASE** (the compact near end of the orb-and-tail). Coarse → applied; fine → not applied.
   Corroboration only — the smallest surface in the cast.

### ⚠ THE READ DIFFERS BY FAMILY — carry both, or the control scores as blank

Derived every run and printed into `PROTOCOL.txt`:

* **clut `0x3dc0`** (`pal.s0.x0_y247.e256` @`0xe6c`, the 20 A=0x0080 readers): entry 0 = `0x9041` →
  **rgba(8,16,32,255), OPAQUE**, luma 15 — the darkest entry the palette has. **0/256** entries are
  `0x0000`, **0/256** are `0x8000`, so there is no transparent-vs-opaque-black ambiguity on the
  answer-carrying family. Both cells 100.0 % opaque, mean luma 101.2 / 104.8. ⇒ **COUNT DARK NAVY
  BANDS**, ~6.7:1.
* **clut `0x3d40`** (`pal.s0.x0_y245.e256` @`0xa6c`, the 7 A=0x0000 controls): entry 0 = `0x0000` →
  **fully TRANSPARENT** (61/256 are). Cells 71.2 % / 76.4 % opaque; mean luma ~31 **all-texel**
  (transparent texels counted as 0 — the opaque-only means are **43.6 / 42.7**). ⇒ **COUNT HOLES.**

### Controls, and what each null means

* **C1 — the A=0x0000 family (7 surfaces).** They read the UPPER cell under **every** live reading of A,
  so they **must** show 12 THIN. If they do, the override loaded, the upload landed, and column-640
  surfaces DRAW — the BINDING-IS-NOT-A-DRAW gate passed in-cast. If they show 4 FAT instead, the
  prediction table is wrong somewhere: **discard the cast, do not interpret it.**
* **C2 — the lower-cell upload.** Cannot fail independently: one rect, one `LoadImage`. C1 visible ⇒ the
  lower mark is in VRAM.
* **C3 — S5.** Under (ii) its high-v faces show the LOWER mark no matter what A does — the lower mark on
  screen with the question held open.
* **C4 — shape attribution, offline.** `vehicle\ef038-col640-shapes.png` plus the five predict panels.
  Only one surface is a wide flat sheet, and it is A=0x0080.

---

## 6. THE FAILURE LADDER

**Nothing bands on ANY surface = BOUND-NEVER-DRAWN for the whole column. That is a RESULT, not a
failure** — and with **27 readers** a genuine total null is itself a substantial finding and must be
reported as one, not buried. Before recording it:

1. **Verify the file reached disk** — the probe's own post-write readback sha (printed, and in
   `deploy.ledger.json`).
2. **One relaunch-and-recast retry.** This closes the single assumption that could not be shut
   read-only: `UseFileList = 1` with no `ModFileList.txt` *should* mean live filesystem lookup and no
   relaunch for a first deploy into an absent slot. It fails safe — straight into this branch.
3. Only then record BOUND-NEVER-DRAWN and fall to §6.2.

**Record TWO things separately, per surface class: (a) is it VISIBLE at all? (b) does it BAND?**
Conflating them is how a cast gets mis-read. And **VISIBLE but UNBANDED is a distinct THIRD outcome**,
not a null and not bound-never-drawn: the surface drew but sampled *neither* marked cell — a displaced
upload, a different page, a cached decode, or a mid-cast wipe from the unwalked program bytes (below).
File it as its own finding under neither hypothesis.

**Null on S1 alone** (the disc absent, others banded): `0x29dbc` is bound-but-not-drawn in this cast —
a RESULT. Fall to scoring question 2 and to S5; **the cast still answers.**

**Null on the A=0x0080 family while C1 shows THIN**: this is not a null, it is the `(iii)` row for those
records specifically — and it is the one genuinely under-determined outcome, because "shows nothing" and
"shows the upper mark on a surface I could not resolve" look alike at video resolution. **Re-score on
stills at the disc.**

**Null on S5 only**: expected-ish. It is the smallest surface in the cast (27 faces on a ±38 orb) and it
is corroboration, never the verdict.

**What CANNOT explain a null, checked rather than listed:**

* **Runtime program VRAM writes — NOT OBSERVED, not excluded.** ef038's only entries in the W6b
  direction-law census (`texel-w6b\census\program_vram.json`, `errors: []`) are **two
  `Hi_StartSummonTexAnim` (op 12) calls, sites 2148 and 3144**, and ef038 appears in **no**
  `LoadImage`, `MoveImage`, `StoreImage` or seq-op-0x07 list — but that census is a STATIC walk, and
  ef038's walk reached only **44.98 % of its program image (5,752 of 12,404 bytes — the 19th-lowest
  coverage of 385 images; corpus mean 0.905, median 0.986)**. `unresolved_calls: 0` means every call
  *that was reached* resolved, not that every call was seen. A `LoadImage` into column 640 hiding in
  the unwalked 6,652 bytes would wipe the stripes mid-cast — one more reason a null goes through the
  relaunch-and-recast retry and the VISIBLE-but-UNBANDED branch above before it is believed.
* **Texanim reach — DISJOINT.** ef038 IS W7's texanim vehicle, so the table was decoded rather than
  trusted: present/armed/parsed, 116 B, **3 clips, all on part 1**, window `(54,62,22,12)` ←
  `(78,0,22,12)` / `(56,0,22,12)`. `creature_package.tpage = [147,147,148,148,149]` with
  `v_offset = [128,0,128,0,128]` → `vram_rect` puts the five parts at **columns 192, 256, 320**; part 1
  specifically at `(192,256,64,128)`. **Zero intersection with column 640.** (W7's finding that nothing
  runs texanim on PC makes this doubly safe, but the disjointness does not depend on it.)
* **A failed lower upload — impossible.** §4.2, C2.

### 6.2 Fallback vehicles, ordered by cost

Everything below ef038 is **relaunch-class**: it needs a new `Actions.csv` row plus a relaunch, because
rows 192–204 are the whole live bench roster and none names these effects.

1. **ef407 — THE FIRST FALLBACK, and the prediction table transfers essentially verbatim.** Re-walked
   this round: 286,720 B, no creature package, **27 column-640 slots, A `{0x0080: 20, 0x0000: 7}`, clut
   `{0x3dc0: 20, 0x3d40: 7}`, and the same cell offsets `0x1946c`/`0x1d46c` with the same cover spans
   `(1,127)`/`(0,127)`** — a structural near-clone of ef038 (it is Shiva's other cast variant). One wrap
   reader, `0x452b4`. Identical controls, so nothing needs re-deriving beyond re-running the walker and
   the two CLUTs' entry-0 decode. **Cost:** one new `Actions.csv` row (e.g. id 205, animationId 407),
   one relaunch, one fresh battle.
2. **ef498 `0x57620`** (column 512) — 4 column-512 slots, A `{0x0080: 1, 0x0000: 3}`, **four different
   CLUTs**. One answer-carrying surface, three controls, **no wrap reader** (C3 is gone) and four entry-0
   decodes to derive before the read is scoreable.
3. **ef179** (column 704) — 3 slots, all A=0x0080, all clut `0x3d80`. Three large clean surfaces, trivial
   attribution, **but NO in-cast control of any kind**: a "12 THIN" and a "nothing at all" would be
   separated only by eyeballing whether the art changed. Needs a second, prior load-proof cast — two
   relaunch-class casts instead of one.
4. **ef381 `0x80820`** (column 576) — 28 slots, A `{0x0000: 21, 0x0080: 7}` across **six** CLUTs, two wrap
   readers, and the piped multi-writer cell names the census flagged. Controls exist; attribution is the
   worst of the four. Last resort.
5. **If all of them return a genuine total null**, BINDING-IS-NOT-A-DRAW bites on every candidate, the
   vehicle lane is exhausted, and that is itself reportable. U1 then falls to the report's §5 second leg
   (flip A, watch BLEND STATE, not texels) or to a disassembly of the id-3 program / SFX loader.

⚠ **`--from <other>.bytes` IS NOT THE RE-PIN, AND ON ITS OWN IT IS DESTRUCTIVE.** `EFFECT`, `COLUMN`,
the cell names, `MARKS` and `GAME_OVERRIDE` are module constants pinned to ef038; `--from` moves the
SOURCE and nothing else, so a foreign container would be staged as `ef038.cellprobe` and written over
`…\SpecialEffects\ef038`. **`pin_source` refuses on four independent axes** — the file name, the stock
sha, both cells' derived depth/channel/offset/cover, and the whole column-640 census including the wrap
record. ★ **ef407 is exactly why the last two axes exist**: it passes the cell pins *and* the A
histogram, and is caught only by the sha and by the wrap-record identity. Running a fallback means
**editing the constants** — `EFFECT`, `COLUMN`, `MARKS`, `EXPECT_STOCK_SHA256` and every `SOURCE_PIN_*`
entry — not just passing `--from`.

---

## 7. THE REVERT LADDER

```
  py C:\gd\SCRATCH\summon-format\repaint-w6b\u1-second-array\cellprobe\revert_probe.py
     -> "deleted <install>\FF9CustomMap\FF9_Data\SpecialEffects\ef038"    (pre.ABSENT: there was none)
     -> run it again: "already reverted (absent): ..."  exit 0            (idempotent)
```

**FIRST-DEPLOY DELETE SEMANTICS.** `ef038` is ABSENT before this cast, so the ledger records
`pre.existed = false`, the revert **DELETES**, and the resting state afterwards is **stock**. If the
folder is observed PRESENT at deploy time instead, `--deploy` says so loudly ("somebody else's cast is
underneath this one"), snapshots those bytes into the root, and the revert **RESTORES them byte for
byte**. Both branches, and both *orders*, were rehearsed (§8).

**THE RE-TARGETING LAW.** A revert's destination is a HISTORICAL FACT, not a preference: the emitted
script bakes in the exact path its write landed in, as two literals. Rebased onto a folder this probe
never wrote to, a delete would remove somebody else's perfectly good override.

**Revert BEFORE any `summon-reskin deploy` touches this root** — §2, THE LEDGER TRAP.

**What does NOT get reverted:** bench rows 192–204 stay. They are allocated ids on a live CSV; removing
one renumbers nothing but strands the next.

**Resting state after the ladder:** ef038 override DELETED (= stock), `ef211` untouched, rows 192–204 on
the bench, every artifact and every video under `…\repaint-w6b\u1-second-array\`, and the `[SfxProbe]`
log archived beside them.

---

## 8. What the build round corrected — recorded, because an unrecorded correction repeats

1. **The sketch's k=10 / k=2 was rejected on measurement, not taste.** At k=2 only 71 of the headline
   disc's 140 faces would be crossed by any band. The chosen 12×4 / 4×8 gives 140/140 and 132/140 while
   keeping the discriminator threshold-free. §4.2.
2. **A LEDGER DEFECT, inherited from `odin_cell_probe.py`, found by rehearsing and fixed.** The emitted
   revert decides by `pre.exists()`. A root already deployed into keeps whichever marker that run left,
   so a **PRESENT run followed by an ABSENT run** would leave the stale `pre` snapshot beside the new
   `pre.ABSENT` — and the revert would **restore somebody else's container into a slot that should be
   deleted**. Silent, with no symptom until an unrelated session casts the effect. The two markers are
   now mutually exclusive by construction and the clearing is printed. The fix has since been **ported
   back to `odin_cell_probe.py` and `phoenix_cell_probe.py`** (exclusive markers + printed clearing +
   the idempotent three-branch revert; phoenix also gained the `--mod-folder` rehearsal seam it
   lacked), with both deploy orders rehearsed against a temp mod folder on each — PRESENT-then-ABSENT,
   the reproducing order, now deletes; ABSENT-then-PRESENT restores byte-identically. Both historical
   ledger roots were left untouched and rest consistent (ef424: `pre.ABSENT` only; ef211: `pre.ef211`
   only).
3. **A PREDICTION-PANEL DEFECT, found by the panel itself.** The first renderer applied a flat +128
   under hypothesis (i) to *every* reader, which drew the A=0x0000 negative control **moving** — and the
   whole cast rests on that control **not** moving. Hypothesis (i) is `baked_v = raw_v + A`, so `A` is a
   parameter, not the constant 128. Fixed and verified numerically: the control surfaces now render
   **pixel-identical** across both hypothesis panes (diff 0), while the disc changes 38.5 % of its drawn
   pixels.
4. **S5 demoted from "the sharpest single-surface discriminator" to corroboration.** Derived over the
   whole surface it shows 12 THIN + 4 FAT under **both** hypotheses. Only its base discriminates. §4.3.
5. **ef407 is a structural near-clone of ef038 on column 640** — same cell offsets, same cover spans,
   same slot count, same A and CLUT histograms. Good news for the fallback (the table transfers); bad
   news for any pin weaker than sha + wrap-record identity. §6.2.
6. **The byte proof is run by a second program that does not import the first**, and restates `MARKS` on
   purpose, so a drift between the probe's constants and this study's is a loud disagreement rather than
   a silent agreement.

---

## 9. ★ CAST 1 — RAN 2026-07-30, AND THE READ IS THE THIRD OUTCOME: **`VISIBLE_UNBANDED` (0.88)**

Owner video `shiva_u1.cast1.2026-07-30.mkv` (941 unique frames), scored by two independent lenses, an
adversarial third read that re-measured everything, and a completeness critic whose findings are
appended to the record: `…\u1-second-array\castread\REPORT-U1.md`. Owner-facing annotated figures in
`castread\annotated\` (`03-disc-real-vs-both-marks.png` is the one to look at).

* **The column DRAWS — BOUND-NEVER-DRAWN is refuted by counting, not by attribution.** During the disc
  window ef038 submits a median of 1,048–1,183 textured prims per frame = **61–69 % of the whole
  column-640 pool**; the disc itself is on screen at 147k px, mean luma 190, across 14 clean frames.
  (Per-record attribution FAILED by two methods — IoU ≈ 0.70 for every candidate — so "the star IS
  `0x29dbc`" was never established; the verdict does not need it.)
* **NOTHING BANDS, on either family.** The decisive instrument is pitch-, chirp- and orientation-free
  (the near-black fraction of the surface's own added light): captured disc **0.50 %** vs **37.24 %**
  predicted under the fine mark (74×) and **24.78 %** under the fat (50×), cross-validated against the
  pure texture-space decode to 1.5 points. The live container carried the marks (byte-verified at cast
  time). Per §6's discipline: **neither marked cell was sampled. C1 failed on the `nothing` branch, so
  the cast is uninterpretable for U1 in EITHER direction** — not a FINE result, not a COARSE result,
  and neither H_V nor R_FLAGS gains anything. The read scores §6's relaunch-and-recast retry as SPENT
  (its R7).
* **⚠ THE MECHANISM LEAD — `DR_MOVE` where the census says ZERO.** The probe log carries **641
  VRAM-move-class packets** on ef038 in two contiguous blocks (effect frames 86–138 and 237–380); the
  static direction-law census records NONE for ef038, and its walk reached only 44.98 % of the program
  image. **The first block completes BEFORE any scored surface appears** — an early VRAM blit over the
  (640,256) page rect would wipe both marks and produce exactly this cast. It also voids the
  texanim-disjointness argument's premise (not its conclusion). `DR_TPAGE` is logged with no payload
  word (41,539 bare rows), which is why record-level segmentation and the twin-pair co-draw question
  stay open.
* **Instrument lessons, kept:** both first-pass scorers used flat matched filters that a 5:1 chirped
  mark defeats outright (injected: scored 0.64 vs the real frame's 2.57) — their negatives were right,
  their reasoning was not safe; the area-fraction statistic honors the §5 "do not count bands" clause
  by construction. The critic's pitch-clamp finding (H=240) invalidates the adversarial pass's own
  secondary corroboration and one figure caption, not the verdict. The §5 "cast it FIRST" condition was
  violated on its face (the capture opens mid-battle); mitigation recorded in the report.
* **The control family is structurally weak without a stock reference**: the `0x3d40` cell is already
  28.8 % transparent, so its hole-comb moves a statistic ~1.9× against a baseline this arc has never
  captured. What carries the control read instead: C2 (one rect, one upload — the 20 answer readers are
  decisively unmarked) and optical suppression by the bright twins.

### 9.1 Next steps, in cost order — the first one changed

1. **⚠ ENGINE (owner GO/NO-GO — DLL rebuild): log the `DR_MOVE`/`MoveImage` payload rects** (source +
   destination) in the SfxMeshProbe patch, and the `DR_TPAGE` code word in the same edit (free, and it
   settles the twin-pair co-draw question). One log field; it discriminates the leading mechanism
   directly — did something blit over (640,256) before the surfaces drew?
2. **Dump the emulated VRAM page at (640,256) at cast time** and diff against the two marked cells —
   separates a wrong cells→VRAM mapping from a runtime overwrite from a cached decode.
3. **A STOCK reference cast of ef038** (probe already reverted; recast + capture) — the only thing that
   ever makes the A=0x0000 control family scoreable on its own pixels.
4. **Only then** the §6.2 fallback vehicles (ef407 first) — every one inherits the same unproven
   cells→VRAM→sampler link this cast just exposed.
5. **Do NOT bundle the §4.4 second leg** (flip A, watch blend state). One change per in-game test; this
   cast has not earned that step.

**Resting state:** ef038 override DELETED (= stock, verified), `ef211` untouched, rows 192–204 on the
bench, video + frames + all analysis under `…\repaint-w6b\u1-second-array\`, the `[SfxProbe]` log
archived in `capture-logs\`. **No constant moved; `ORDER_UNMEASURED` ships exactly as it was.**